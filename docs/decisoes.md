# Registro de decisões

Cada mudança relevante: data, o que mudou, onde, por quê, impacto.

---

## 2026-08-28 — Escolha do domínio: percepção de aracnídeos

**O que mudou:** definição do domínio do projeto.
**Onde:** `PROJETO.md`.
**Por quê:** identificação de aranhas é um problema real de percepção visual
em ambiente não controlado, com quatro classes visualmente separáveis e
acervo público de imagens com licença aberta. Exercita o pipeline completo
(aquisição → segmentação → features → classificação) que a disciplina cobre.
**Impacto:** define as classes percebidas de todos os TPs seguintes.

---

## 2026-08-28 — Ambiente: VirtualBox com o appliance da disciplina

**O que mudou:** adoção do VirtualBox no host Fedora Linux, com o
appliance `Ubuntu22.04ROS2Humble.ova` fornecido pela disciplina, em vez
da rota WSL2 descrita nos tutoriais.
**Onde:** `TUTORIAL-VIRTUALBOX.md`, `scripts/setup.sh`.
**Por quê:** o host é Fedora, e WSL2 só existe no Windows. O appliance
oficial dá paridade exata com o laboratório — mesmo Ubuntu 22.04, mesmo
ROS 2 Humble, mesmas versões de biblioteca — o que elimina a classe de
problema "funciona na minha máquina".
**Impacto:** nenhum desvio técnico a declarar. Custo: Secure Boot exigiu
inscrição de chave MOK para carregar o módulo `vboxdrv`, e a webcam USB
exigiu o Extension Pack. Ambos documentados no tutorial.

---

## 2026-08-28 — Taxonomia resolvida por tabela, não pelo modelo

**O que mudou:** o classificador prediz apenas a espécie; a linhagem
taxonômica vem de `config/taxonomy.json`.
**Onde:** `PROJETO.md`, `ros2_ws/src/percepcao_aracnideos/config/taxonomy.json`.
**Por quê:** dada a espécie, reino/filo/subfilo/classe/ordem/família/gênero
são consequência lógica, não inferência. Uma rede com oito saídas
correlacionadas desperdiça capacidade e permite predições internamente
inconsistentes.
**Impacto:** simplifica a cabeça de classificação e garante coerência
taxonômica por construção.

---

## 2026-09-28 — YOLO via OpenCV DNN em vez de Ultralytics

**O que mudou:** a inferência YOLO passa pelo módulo `dnn` do OpenCV
lendo um peso ONNX, em vez do pacote `ultralytics` com PyTorch.
**Onde:** `ros2_ws/src/percepcao_aracnideos/percepcao_aracnideos/detector.py`,
`scripts/baixar_modelo.sh`.
**Por quê:** `pip install ultralytics` arrasta o PyTorch (2 a 3 GB). A VM
tem espaço apertado e a inferência roda em CPU, onde o PyTorch não traz
ganho. O OpenCV já está instalado; o peso ONNX tem 13 MB. Mesma
arquitetura, mesmos pesos, mesma saída.
**Impacto:** ambiente leve e reproduzível. O caminho do modelo vem do
YAML, então trocar para os pesos próprios no TP4 é mudar configuração,
não código.

---

## 2026-09-28 — Rastreamento com filtro de Kalman

**O que mudou:** as detecções passam por um rastreador multi-alvo com
filtro de Kalman de velocidade constante antes de serem publicadas.
**Onde:** `percepcao_aracnideos/rastreador.py`.
**Por quê:** a bbox do detector treme e falha em frames isolados. Sem
filtro, a trilha fica serrilhada e a contagem de indivíduos não existe —
só há contagem por frame. O filtro dá identidade estável a cada alvo.
**Impacto:** tremor da trilha reduzido em 54–61% e erro de posição em
13–36% (medido em cenário sintético com verdade conhecida). Resolve a
limitação de oclusão documentada no relatório do TP1: dois alvos que se
cruzam mantêm ids distintos.

---

## 2026-09-28 — MultiThreadedExecutor no action server

**O que mudou:** o `varredura_action_server` usa `ReentrantCallbackGroup`
com `MultiThreadedExecutor`.
**Onde:** `percepcao_aracnideos/varredura_action_server.py`.
**Por quê:** com o executor padrão de thread única, o laço de execução do
goal bloqueia a subscrição de `/aracne/deteccoes` e o callback de
cancelamento. O servidor "varre" sem receber detecção e não responde ao
cancelamento — falha silenciosa, sem mensagem de erro.
**Impacto:** feedback com dados reais e cancelamento funcional.

---

## 2026-09-28 — URDF com frame óptico separado e plugins de Gazebo

**O que mudou:** criado `urdf/aracne_bot.urdf` com 11 links e 10 juntas,
incluindo `camera_optical_frame` separado de `camera_link` e plugins de
câmera, LiDAR, IMU e tração diferencial.
**Onde:** `ros2_ws/src/percepcao_aracnideos/urdf/`.
**Por quê:** `sensor_msgs/Image` assume convenção óptica (z para frente),
diferente da mecânica (x para frente). Misturar os dois é a causa mais
comum de nuvem de pontos girada no RViz, e o sintoma só aparece no TP3.
Os plugins de Gazebo ficam escritos desde já para que a migração do TP3
seja spawnar o mesmo URDF.
**Impacto:** árvore TF correta desde o início; menos retrabalho no TP3.

---

## 2026-09-28 — Peso do modelo fora do git

**O que mudou:** `models/` entra no `.gitignore`; o peso é obtido por
`scripts/baixar_modelo.sh`.
**Onde:** `scripts/baixar_modelo.sh`, `.gitignore`.
**Por quê:** regra da disciplina — arquivo grande não entra no git, e
todo artefato derivado tem fonte versionada. O script É a fonte.
**Impacto:** repositório leve; `setup.sh` obtém o peso num clone limpo.
Se o download falhar, o detector degrada para HSV e o sistema continua
demonstrável.

---

## 2026-09-28 — Histerese de limiar no rastreamento

**O que mudou:** o rastreador passou a usar dois limiares de confiança —
`limiar_confianca` (0,45) para criar uma trilha e `limiar_manutencao`
(0,25) para mantê-la.
**Onde:** `percepcao_aracnideos/rastreador.py`, `config/aracne_params.yaml`.
**Por quê:** a confiança do detector oscila com a cena. Um alvo que entra
na sombra cai de 0,62 para 0,32 sem ter se movido; com limiar único a
trilha morre e renasce com id novo, inflando a contagem de indivíduos.
É o mesmo princípio do limiar duplo do detector de bordas de Canny.
**Impacto:** medido em cena com sombra e falsos positivos — limiar único
alto gera 3 ids, limiar único baixo gera 14 (13 fantasmas), histerese
gera 1 id sem fantasma, com o alvo presente em 150/150 frames.

---

## 2026-09-28 — Pré-processamento implementado e desativado por padrão

**O que mudou:** criado `preprocessamento.py` com CLAHE, balanço de
branco, gama adaptativa e filtro bilateral, mais quatro métricas de
qualidade de imagem. O parâmetro `preproc_ativo` tem padrão `false`.
**Onde:** `percepcao_aracnideos/preprocessamento.py`,
`scripts/experimento_robustez.py`.
**Por quê:** a hipótese era que normalizar a imagem aumentaria a
tolerância a iluminação ruim. O experimento de ponto de ruptura mediu
7 degradações e **não confirmou**: 2 melhoras, 2 pioras, 3 empates na
cena sintética; nenhuma melhora e uma piora significativa em fotografia
real. A causa é que o YOLOv8 foi treinado com augmentation e já viu
essa variação — normalizar empurra a entrada para fora da distribuição
de treino.
**Impacto:** o módulo fica disponível e parametrizável (ajuda o detector
clássico e a inspeção visual), mas desligado por padrão. A robustez do
pipeline vem da histerese e do filtro de Kalman, não do filtro de
imagem. Decisão tomada pela medição, não pela intuição.

---

## 2026-09-28 — Instrumentação de qualidade de imagem

**O que mudou:** cada frame é avaliado (brilho, contraste, nitidez por
variância do Laplaciano, pixels saturados) e o veredito viaja em
`ListaDeteccoes` e aparece no HUD do frame anotado.
**Onde:** `preprocessamento.py`, `msg/ListaDeteccoes.msg`, `anotacao.py`.
**Por quê:** um sistema que sabe que não está enxergando vale mais que um
que devolve silêncio. Permite distinguir "não há alvo" de "não dá para
ver" — distinção que nenhum detector faz sozinho.
**Impacto:** custo de ~1 ms por frame. Pixels saturados são o único
defeito irreversível medido: nenhum filtro recupera o que o sensor
perdeu.

---

## 2026-10-07 — Classificador de espécies: MobileNetV3-Small com ajuste fino em duas fases

**O que mudou:** treino do classificador de 5 espécies, antecipado em
relação ao TP4.
**Onde:** `treino/treinar.py`, `treino/aumentar.py`,
`docs/evidencias/modelo/`.
**Por quê:** 740 imagens não bastam para treinar uma rede do zero —
seriam poucos exemplos por classe para aprender bordas e texturas.
Transfer learning reaproveita um backbone já treinado na ImageNet e
aprende só a última camada. Duas fases porque descongelar tudo de uma
vez com a cabeça aleatória propaga gradientes grandes para trás e apaga
o que o backbone já sabia (esquecimento catastrófico): primeiro
congela-se o backbone e treina-se só a cabeça, depois libera-se os
últimos blocos com taxa de aprendizado 10x menor. MobileNetV3-Small
porque a inferência é em CPU na VM.
**Impacto:** 98,65% em validação limpa, 6,1 MB, ~8 ms por imagem em CPU.
Deixa ~92 ms livres do orçamento de 100 ms a 10 Hz.

---

## 2026-10-07 — Exportação em ONNX com opset 12 forçado

**O que mudou:** `torch.onnx.export(..., dynamo=False)` no `treinar.py`.
**Onde:** `treino/treinar.py`.
**Por quê:** a partir do PyTorch 2.9 o exportador novo é o padrão e
**ignora** o `opset_version` pedido, emitindo opset 18. O OpenCV do
Ubuntu 22.04 não lê opset 18 — e a falha só aparece na VM, depois do
treino, com um erro de parsing que não menciona opset. `dynamo=False`
mantém o exportador antigo, que respeita o parâmetro.
**Impacto:** o `.onnx` carrega no `cv2.dnn` da VM. Verificado:
`docs/evidencias/modelo/verificacao-onnx.txt` mostra que o ONNX
reproduz o PyTorch exatamente (mesma acurácia, matriz idêntica).

---

## 2026-10-07 — Limiar de rejeição em 0,70 e label smoothing 0,1

**O que mudou:** predições abaixo de 70% de confiança são respondidas
como "não sei" em vez de retornarem a classe mais provável.
**Onde:** `treino/treinar.py` (label smoothing), consumo no
`deteccao_node`.
**Por quê:** a softmax sempre soma 1 — a rede não tem a opção de se
calar, e responde "aranha" para um sapato. O limiar dá essa opção. O
valor 0,70 não é arbitrário: medido nas 148 imagens de validação, os
dois erros saíram com 65% e 58% de confiança, contra 91,3% de média nos
acertos; 0,70 cai na folga entre as duas populações. O label smoothing
0,1 é o que torna isso possível — sem ele a rede satura em 99,9% para
tudo, inclusive quando erra, e a confiança deixa de separar nada.
**Impacto:** 100% de acerto no que o sistema aceita responder, cobrindo
94% das imagens. Troca explícita de cobertura por precisão, defensável
num sistema que identifica aranha peçonhenta.

---

## 2026-10-07 — Augmentation: efeito nulo na comparação direta, medido sob severidade crescente

**O que mudou:** a comparação com/sem augmentation foi refeita variando
a severidade da degradação, em vez de um único par de treinos.
**Onde:** `docs/evidencias/modelo/comparativo-augmentation.txt`,
`curva-augmentation.png`.
**Por quê:** o par direto deu diferença de **1 imagem em 148**, com
matrizes de confusão idênticas em validação limpa. Reportar "+0,68
ponto" seria reportar ruído. A hipótese foi efeito de teto: a simulação
de impressão estava branda demais para separar os dois modelos. Com a
severidade varrida em 5 sementes, o efeito aparece entre 2 e 4 e atinge
**+7,84 pontos em severidade 3,0, vencendo em 5 de 5 sementes**
(separação 7,84 contra desvio combinado 5,52).
**Impacto:** o augmentation fica ativado, com a justificativa correta —
ele não melhora o caso fácil, ele impede o colapso no caso difícil. E o
resultado negativo inicial fica registrado em vez de escondido.
