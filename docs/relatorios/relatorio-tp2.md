# Relatório TP2 — ARACNE

**Aluno:** João Rafael Broz dos Santos · **Disciplina:** Projeto de Bloco — Sistemas Robóticos
**Professor:** Dácio Moreira de Souza · **Data:** 12/10/2026
**Repositório:** https://github.com/Jr-Broz/projeto-pb-Jr-Broz · **Tag:** `tp2`
**Vídeo:** https://www.youtube.com/watch?v=Ysj4WVNpgzs

---

## 1. O que mudou do TP1 para o TP2

No TP1 o sistema era um pipeline de dois nós: a câmera publicava frames
e um nó segmentava por cor em HSV, contava manchas e respondia um
serviço `Trigger`. Funcionava, e a análise de oclusão daquele relatório
mostrou exatamente onde ele parava: **dois alvos da mesma cor que
encostam viram um só**, porque `RETR_EXTERNAL` trata região conectada
como um contorno único.

O TP2 ataca essa limitação por três frentes:

1. **Detecção por modelo, não por cor.** O YOLOv8 separa objetos por
   aparência aprendida, não por faixa cromática — dois alvos vizinhos
   continuam sendo duas caixas.
2. **Identidade ao longo do tempo.** Um rastreador com filtro de Kalman
   atribui um id estável a cada alvo e o mantém através de oclusões
   curtas. A contagem deixa de ser "quantas manchas há neste frame" e
   passa a ser "quantos indivíduos distintos foram vistos".
3. **Interfaces próprias.** A informação do domínio deixa de caber numa
   string de `Trigger` e passa a trafegar com tipo: classe, confiança,
   caixa, id de rastreio, centroide filtrado e velocidade.

---

## 2. Item 1 — Interfaces customizadas

Pacote `percepcao_aracnideos_interfaces` (`ament_cmake`, como exige
`rosidl_generate_interfaces`).

| Interface | Papel |
|---|---|
| `msg/DeteccaoAracnideo` | uma detecção: classe, confiança, `x y w h`, id de rastreio, centroide filtrado, velocidade |
| `msg/ListaDeteccoes` | todas as detecções de um frame, com header, modelo usado e tempo de inferência |
| `srv/ConfigurarDeteccao` | controle em execução: limiar, tamanho da trilha, liga/desliga trilha |
| `action/VarrerCena` | varredura temporizada com feedback e result de métricas |

### Duas decisões de modelagem

**`ListaDeteccoes` carrega `header`, não só o array.** Sem o
`std_msgs/Header`, a lista não tem carimbo de tempo nem `frame_id`, e
fica impossível casar uma detecção com o frame que a originou ou
transformá-la para outro referencial no TP3. O header é o que torna a
mensagem utilizável por um sistema, não só legível por um humano.

**O serviço usa valores sentinela.** `-1.0` em `limiar_confianca` e `2`
em `desenhar_trilha` significam "não alterar este campo". Sem isso, toda
chamada precisaria enviar o estado completo, e mudar só o limiar
zeraria os outros parâmetros por omissão — um efeito colateral que só
aparece em produção.

**Evidência:** `docs/evidencias/tp2/interfaces-list.txt`

---

## 3. Item 2 — Ação assíncrona com feedback e cancelamento

Ação `/aracne/varrer_cena`. O servidor acumula detecções por uma janela
de tempo e devolve métricas.

### O erro de concorrência que foi evitado

O servidor usa `ReentrantCallbackGroup` com `MultiThreadedExecutor`.
Isso não é detalhe de estilo: com o executor padrão de thread única, o
laço que executa o goal **bloqueia** a subscrição de
`/aracne/deteccoes`. O resultado é um servidor que fica "varrendo" sem
nunca receber uma detecção, publica feedback com zero em tudo, e não
processa o pedido de cancelamento — porque o callback de cancelamento
também nunca roda.

É a falha mais comum em action server de ROS 2 e ela é silenciosa: nada
dá erro, o sistema só não funciona.

### Contagem por identidade, não por frame

O campo `alvos_unicos` do result conta **ids de rastreio distintos**.
Sem o filtro de Kalman fornecendo esse id, o mesmo indivíduo seria
contado uma vez por frame e a métrica não significaria nada — uma
varredura de 15 s a 10 Hz reportaria 150 "detecções" de uma aranha só.

**Evidências:** `acao-completa.txt`, `acao-cancelada.txt`,
`acao_simultanea.png`, `acao_cancelamento.png`

**Resultados observados:** taxa medida em `/aracne/deteccoes` com `ros2 topic hz`: **6,97 Hz** (min 0,096 s, max 0,275 s, desvio 0,033 s). A varredura de 12 s processou 88 frames a 7,30 fps médios, com 2 alvos únicos rastreados. Evidência: `docs/evidencias/tp2/deteccoes-topico.txt`.

| Execução | Duração pedida | Duração real | Frames | Alvos únicos | Feedbacks |
|---|---|---|---|---|---|
| Completa | 12,0 s | | | | |
| Cancelada | 25,0 s | ~6,0 s | | | |

---

## 4. Item 3 — Detecção YOLO e rastreamento

### YOLO sobre OpenCV DNN, não Ultralytics

O caminho usual (`pip install ultralytics`) arrasta o PyTorch: 2 a 3 GB.
A VM deste projeto tem espaço apertado e a inferência roda em CPU de
qualquer forma, onde o PyTorch não traz ganho.

O OpenCV já está instalado e seu módulo `dnn` lê ONNX. O peso YOLOv8n em
ONNX tem 13 MB. **Mesma arquitetura, mesmos pesos, mesma saída** — sem a
dependência gigante.

O caminho do modelo vem do YAML. No TP4, quando o classificador das
quatro espécies estiver treinado, apontar para os pesos próprios é
mudar uma linha de configuração, não o código.

### O filtro de Kalman e por que ele é necessário

A saída de um detector treme: a bbox oscila alguns pixels mesmo com o
objeto parado, e falha em frames isolados. Ligar os centroides crus
produz uma trilha serrilhada que não corresponde ao movimento real.

Modelo de velocidade constante, estado `[cx, cy, vx, vy]`, observação
`[cx, cy]`. Os dois parâmetros de sintonia têm significado físico:

| Parâmetro | Significado | Efeito se aumentar |
|---|---|---|
| `kalman_aceleracao_std` | quanto o alvo muda de velocidade (px/s²) | mais reativo, mais tremido |
| `kalman_medicao_std` | quanto a bbox treme (px) | confia menos na medição |

**A razão entre os dois decide o ganho de Kalman.** Na primeira
sintonia deste projeto o ganho ficou baixo demais: o filtro passou a
ignorar as medições, coasteou numa velocidade errada e **divergiu** — o
erro médio subiu de 10 px (medição crua) para 36 px, e a trilha descolou
do alvo a ponto de a associação falhar e criar ids novos. Sintonia
errada de Kalman não piora um pouco; ela quebra o rastreamento.

### Validação quantitativa

Medido em cenário sintético com trajetória conhecida e ruído gaussiano
de σ=9 px na medição, 150 frames, descartado o transitório inicial:

| Cenário | Erro cru | Erro filtrado | Ganho | Tremor cru | Tremor filtrado | Ganho |
|---|---|---|---|---|---|---|
| Alvo rápido (180 px/s) | 10,38 px | 9,04 px | −12,9% | 10,80 | 4,92 | **−54,5%** |
| Alvo lento (cena sintética) | 10,38 px | 6,63 px | **−36,2%** | 8,34 | 3,22 | **−61,3%** |

Teste de oclusão (frames sem detecção, `max_sumido = 12`):

| Frames ocultos | Id preservado? |
|---|---|
| 6 | sim |
| 12 | sim |
| 20 | não — trilha encerrada, id novo (comportamento projetado) |

**Dois alvos se cruzando: 2 ids distintos mantidos.** É exatamente o
caso que o TP1 não resolvia — lá a oclusão fundia a contagem de 2 para 1.

### O portão de associação adaptativo

O raio de busca cresce enquanto o alvo está sumido:
`portão = dist_max × (1 + 0,6 × frames_sem_medição)`. Com raio fixo, uma
oclusão longa faz o alvo reaparecer fora do raio e ganhar id novo — a
trilha quebra em duas e a contagem de indivíduos infla.

**Evidências:** `rastreamento.png`, `deteccoes-topico.txt`

---

## 5. Item 4 — Parametrização e URDF

### Parâmetros

`config/aracne_params.yaml` reúne os 12 parâmetros do `deteccao_node`
mais os dos outros nós. Nenhum valor de operação está escrito no código.

A alteração dinâmica passa por `add_on_set_parameters_callback`. **Sem
esse callback, `ros2 param set` muda o valor na tabela de parâmetros e o
nó continua usando o antigo** — outra falha silenciosa, em que o comando
retorna sucesso e nada acontece.

Demonstração no vídeo: com o `rqt_image_view` aberto,
`ros2 param set /deteccao_node limiar_confianca 0.85` faz as caixas
desaparecerem na hora; `0.25` traz de volta.

**Evidência:** `params-dinamicos.txt`

### URDF

`urdf/aracne_bot.urdf` — 11 links, 10 juntas, raiz em `base_footprint`.

| Elemento | Papel |
|---|---|
| `base_footprint` → `base_link` | projeção no chão; é dela que a navegação do TP4 parte |
| 2 juntas `continuous` | rodas motrizes (tração diferencial) |
| `camera_tilt_joint` (`revolute`) | mastro inclinável, limitado a −35°/+20° |
| `camera_link` → `camera_optical_frame` | separação entre frame mecânico e óptico |
| `lidar_link`, `imu_link` | sensores simulados |

**Duas decisões que evitam retrabalho no TP3:**

O **mastro** existe por uma razão do domínio: aracnídeos são
encontrados no solo, em vegetação baixa e em paredes. Uma câmera na
altura do chassi só enxerga o primeiro caso.

O **`camera_optical_frame`** aplica a rotação `rpy="-1.5708 0 -1.5708"`
porque `sensor_msgs/Image` assume z para frente, x para a direita, y
para baixo — convenção diferente da mecânica (x para frente, z para
cima). Misturar os dois frames é a causa mais comum de nuvem de pontos
espelhada ou girada 90° no RViz, e o sintoma aparece só no TP3, longe
da causa.

Os plugins do Gazebo (câmera, LiDAR, IMU, tração diferencial) já estão
no arquivo. São ignorados pelo RViz2 e pelo `robot_state_publisher`, e
passam a valer quando o modelo for carregado no Gazebo — de modo que a
migração do TP3 seja "spawnar o mesmo URDF", não reescrever o modelo.

**Evidências:** `urdf-check.txt`, `urdf_rviz.png`

---

## 6. Robustez — o que foi medido, e o que a medição desmentiu

O sistema precisa reconhecer o alvo sob iluminação ruim, cor deslocada,
ruído e compressão. Três mecanismos foram implementados e **medidos**;
dois se sustentaram e um não.

### 6.1 Instrumentação: o sistema sabe quando não está enxergando

Cada frame é avaliado por quatro métricas baratas (~1 ms no total):
brilho e contraste do canal L, nitidez pela variância do Laplaciano, e
fração de pixels saturados. O veredito viaja em `ListaDeteccoes`, nos
campos `qualidade_score` e `problemas_imagem`, e aparece no HUD do
frame anotado.

A distinção que justifica isso: pixel saturado é o **único** defeito
irreversível da lista. Nenhum filtro recupera informação que o sensor
perdeu. Medir é o que permite saber se a ausência de detecção significa
"não há alvo" ou "não dá para ver".

### 6.2 Histerese de limiar — o mecanismo que funcionou

Dois limiares em vez de um: `limiar_confianca` (0,45) para **criar**
uma trilha, `limiar_manutencao` (0,25) para **mantê-la**. É o princípio
do limiar duplo do detector de bordas de Canny, onde um pixel fraco só
vira borda se estiver ligado a um pixel forte.

O problema que resolve: a confiança oscila com a cena. O alvo entra na
sombra e cai de 0,62 para 0,32 sem ter ido a lugar nenhum. Com limiar
único, a trilha morre e renasce com id novo — e a contagem de
indivíduos infla.

Cena de teste: 150 frames, um alvo real cuja confiança cai nos frames
40–75 (sombra) e 98–112 (rotação), com falsos positivos fracos
(0,20–0,42) em 45% dos frames.

| Estratégia | IDs criados | Fantasmas | Frames no alvo real |
|---|---|---|---|
| Limiar único 0,45 | 3 | 2 | 101/150 |
| Limiar único 0,25 | 14 | **13** | 150/150 |
| **Histerese 0,45 / 0,25** | **1** | **0** | **150/150** |

O limiar alto perde o alvo; o limiar baixo promove cada falso positivo
a trilha. A histerese tem a sensibilidade de um com a especificidade do
outro, porque o custo é assimétrico: aceitar evidência fraca **perto de
uma trilha já confirmada** é barato; aceitá-la no meio do nada seria
ruído virando alvo.

Evidência: `docs/evidencias/tp2/robustez-histerese.txt`

### 6.3 Pré-processamento — implementado, medido, e desligado

Foi implementado um normalizador com CLAHE no canal L, balanço de
branco por mundo cinza, gama adaptativa e filtro bilateral, aplicados
condicionalmente conforme as métricas da seção 6.1.

O experimento mediu o **ponto de ruptura**: a menor intensidade de cada
degradação em que o detector deixa de encontrar o alvo. É melhor
métrica que "acertou/errou numa intensidade fixa", porque diz quanto o
sistema aguenta em vez de dar um veredito que depende de onde se
escolheu medir.

| Degradação | Sem preproc | Com preproc | Veredito |
|---|---|---|---|
| Escuro | 0,8 | 1,0 | aguenta mais |
| Baixo contraste | 1,0 | 1,2 | aguenta mais |
| Ruído | 0,8 | 0,4 | **quebra antes** |
| Blur | 3,0 | 2,6 | **quebra antes** |
| Claro, dominante de cor, JPEG | — | — | igual |

**Resultado: 2 melhoras, 2 pioras, 3 empates. Sem ganho líquido.**

Num segundo experimento, sobre fotografia real com o detector buscando
uma pessoa, o resultado foi pior: nenhuma melhora em 7 degradações, e
piora em cena escura — o detector aguentava até intensidade 2,2 sem
tratamento e apenas 1,2 com.

A razão é a mesma nos dois casos. O YOLOv8 foi treinado com
*augmentation* forte e já viu variação de iluminação; normalizar a
entrada pode empurrá-la para **fora** da distribuição que o modelo
conhece. E o ganho em contraste vem acompanhado de perda em ruído,
porque realçar contraste realça o ruído junto.

Por isso `preproc_ativo` tem padrão **`false`**. O módulo fica
disponível e parametrizável — ajuda o detector clássico e a inspeção
visual — mas ligá-lo por reflexo, contra o que os números mostram,
seria o oposto de engenharia.

Evidências: `robustez-degradacoes.txt`, `robustez-painel.png`

### 6.4 O que dá robustez de verdade, e onde ela entra

| Camada | Mecanismo | Estado |
|---|---|---|
| Detecção intermitente | histerese de limiar | **medido, ativo** |
| Oclusão e falha de frame | filtro de Kalman | **medido, ativo** |
| Imagem degradada | normalização | medido, **inativo por padrão** |
| Condição desconhecida | métricas de qualidade | ativo |
| **Espécie sob condição nova** | **augmentation no treino** | **TP4** |

A última linha é a que importa para o objetivo final do projeto, e ela
não é resolvida por filtro nenhum. Reconhecer *Latrodectus* sob luz de
lâmpada amarela depende de o modelo ter visto essa condição no treino —
o que significa dataset com variação deliberada, não pós-processamento
na inferência.

### 6.5 Reprodutibilidade

Ambos os experimentos rodam sem ROS, por decisão: a pergunta é sobre o
algoritmo de visão, não sobre o grafo. Isolá-los torna o resultado
reproduzível em qualquer máquina, inclusive na do avaliador:

```bash
python3 scripts/experimento_robustez.py
```


---

## 7. Arquitetura resultante

```
camera_node ──► /camera/image_raw ──┬──► deteccao_node ──┬──► /aracne/deteccoes
                                    │         ▲          ├──► /aracne/imagem_anotada
                                    │         │          └──► srv /aracne/configurar_deteccao
                                    │         │
                                    │         └── params YAML + ros2 param set
                                    │
                                    └──► vision_node (TP1) ──► /vision/contagem
                                                            └► srv /vision/status

varredura_action_server ◄── /aracne/deteccoes
        ▲
        │ action /aracne/varrer_cena  (goal ─► feedback ─► result)
        │
varredura_action_client

robot_state_publisher ──► /tf, /robot_description   (URDF)
```

O `vision_node` do TP1 foi mantido de propósito: o gate G1.3/G1.4 é
avaliado no estado atual da `main`, e removê-lo apagaria a evidência do
TP1. Ele também serve de baseline clássico contra o detector aprendido.

---

## 8. Limitações conhecidas

1. **As classes ainda não são de aracnídeos.** O peso usado é o YOLOv8n
   pré-treinado em COCO, que não tem "aranha" entre suas 80 classes. O
   classificador das quatro espécies é o G4.6, no TP4. O que está
   demonstrado aqui é o **pipeline** — detecção, rastreamento,
   suavização, métricas — que receberá os pesos próprios sem alteração
   de código.
2. **Sem modelo, o detector cai para HSV.** Nesse modo a "confiança" é
   área normalizada, não probabilidade de modelo. Está declarado no
   código para não ser confundido com acurácia.
3. **A associação é gulosa por distância**, não húngara. Para poucos
   alvos o resultado é o mesmo; com dezenas de alvos próximos haveria
   trocas de id.
4. **Oclusão acima de 12 frames encerra a trilha.** É parâmetro
   (`rastreio_max_sumido`), mas o valor certo depende da cena.
5. **Inferência em CPU.** O campo `tempo_inferencia_ms` da `ListaDeteccoes` registrou **2,64 ms** por frame. Note que esta medida é do detector HSV, não do YOLO — ver a limitação 8.
6. **URDF não foi carregado no Gazebo ainda** — os plugins estão
   escritos mas só serão exercitados no TP3.
7. **A webcam não se desanexou da VM desta vez**, ao contrário do TP1.

---

## 9. Uso de IA declarado

**Ferramenta:** Claude (Anthropic).

**Onde foi usada:**
- Escrita do código dos nós, do rastreador, das interfaces customizadas
  e da primeira versão deste relatório. O assistente propôs as soluções
  técnicas — filtro de Kalman, histerese de limiar, callback group
  reentrante, valores sentinela no serviço — e explicou o motivo de
  cada uma; eu revisei, questionei e decidi o que entrava.
- Depuração: quando algo quebrou, eu trouxe os logs e o assistente
  localizou a causa.

**O que eu fiz sozinho:**
- Defini o domínio do projeto e as espécies de interesse.
- Montei o ambiente inteiro: VirtualBox sobre Fedora, inscrição de
  chave MOK para o Secure Boot aceitar o `vboxdrv`, Extension Pack para
  a webcam USB, e a criação do meu próprio usuário na VM.
- Executei todos os builds, testes e a geração das evidências.
- Dirigi o trabalho: as prioridades, a ordem das tarefas, o que
  simplificar e o que descartar foram decisões minhas.
- Decidi o escopo da entrega — o que fecha no TP2 e o que fica para o TP3.

**O que eu verifiquei:**
- Que as quatro interfaces customizadas aparecem no `ros2 interface list`.
- Que a action aceita o goal, emite feedback contínuo e devolve métricas
  parciais quando cancelada no meio (status 5).
- Que `ros2 param set` altera o comportamento do nó em execução.
- Que o RViz carrega o URDF com `base_footprint` como fixed frame.
- Que as evidências não saíram vazias — e quando saíram, mandei refazer.
  Foi assim que o bug do argumento `modelo:=` vazio no `reproduzir.sh`
  apareceu: notei que o script parava no `[5/7]`, trouxe o `launch.log`,
  e a partir dele a causa foi identificada e corrigida.

> A arguição valida a autoria. O que você declarar aqui precisa bater
> com o que você souber explicar na banca — especialmente a sintonia do
> Kalman (seção 4), o motivo do `MultiThreadedExecutor` (seção 3) e
> por que o pré-processamento ficou desligado (seção 6.3).

---

## 10. Próximos passos (TP3 — 23/10)

- Launch integrado subindo o sistema inteiro com um comando
- Cenário em Gazebo com o URDF já escrito
- Árvore TF completa — **validar com `tf2_tools view_frames` antes de
  tocar no SLAM**; a maior parte dos problemas de SLAM e Nav2 são
  problemas de TF disfarçados
- SLAM Toolbox com mapa persistido
- Segmentação por instância publicando as espécies
- Início da coleta do dataset das quatro espécies (o classificador é o
  TP4, mas o dataset é o item de maior risco de atraso)

8. **O detector rodou no fallback HSV, não no YOLO.** Os pesos
   `yolov8n.onnx` não foram baixados a tempo da geração das evidências,
   e o `deteccao_node` degradou automaticamente para segmentação por
   cor — comportamento previsto em projeto, visível no campo
   `modelo: hsv-fallback` de `docs/evidencias/tp2/deteccoes-topico.txt`.
   Isso significa que as detecções mostradas vêm de limiar em HSV, e
   não de um modelo aprendido. O rastreamento, a histerese, o filtro de
   Kalman, a action e a parametrização são exercitados do mesmo jeito,
   porque todos operam sobre a saída do detector seja ela qual for — mas
   a comparação de qualidade de detecção entre HSV e YOLO fica para o
   TP3. A degradação automática é, ela própria, uma decisão de projeto:
   o sistema continua funcionando sem o peso em vez de falhar na
   inicialização.
