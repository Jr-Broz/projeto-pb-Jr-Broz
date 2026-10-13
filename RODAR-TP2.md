# RODAR — TP2 do ARACNE, do zero até a entrega

Legenda de onde cada comando roda:

| Marcador | Onde |
|---|---|
| 🖥️ **FEDORA** | Terminal do seu Fedora (host) |
| 🐧 **UBUNTU** | Terminal dentro da VM. `lsb_release -a` diz `jammy` |
| 🌐 **NAVEGADOR** | Site |

> **Teste de sanidade:** na dúvida sobre onde você está, rode `lsb_release -a`.

---

# ETAPA 0 — Antes de tudo, dois números

🐧 **UBUNTU:**

```bash
df -h /
free -h
```

O TP2 não instala nada pesado (o YOLO vem em ONNX, 13 MB), mas o
`colcon build` das interfaces gera código C++ e Python e consome uns
300 MB. **Se houver menos de 2 GB livres, limpe antes:**

```bash
sudo apt clean
sudo journalctl --vacuum-size=100M
rm -rf ~/projeto-pb-tp1/ros2_ws/build ~/projeto-pb-tp1/ros2_ws/install ~/projeto-pb-tp1/ros2_ws/log
```

---

# ETAPA 1 — Usuário próprio (opcional, ~25 min)

**Por que vale a pena desta vez:** o vídeo do TP2 é obrigatório e mostra
a tela. Ter `mariopego@UbuntuROS2` em todo terminal da sua defesa é
estranho.

**Por que é barato:** o ROS 2 mora em `/opt/ros/humble`, que é do
sistema. Criar usuário **não** reinstala o ROS.

> ⏱️ **Teto de 40 minutos.** Se passar disso, abandone e trabalhe como
> `mariopego`. O TP2 é 3x o TP1 e você não pode gastar o tempo nisso.

## 1.1 🐧 UBUNTU — criar o usuário

```bash
sudo adduser joao
sudo usermod -aG sudo,video joao
```

Ele pede senha duas vezes e depois nome completo, sala, telefone —
pode dar Enter em tudo.

## 1.2 Sair e entrar como `joao`

Menu do sistema → sair → entre com `joao`.

## 1.3 🐧 UBUNTU (como joao) — ambiente

```bash
echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
echo "export ROS_LOCALHOST_ONLY=1" >> ~/.bashrc
echo "export ROS_DOMAIN_ID=SEU-NUMERO" >> ~/.bashrc
source ~/.bashrc
echo $ROS_DISTRO
```

Troque `SEU-NUMERO` pelo número de chamada (ou qualquer valor 1–101,
mas anote — precisa ser o mesmo em todos os terminais).

## 1.4 🐧 UBUNTU — git e clone

```bash
sudo apt install -y git gh python3-colcon-common-extensions unzip

git config --global user.name "João Rafael Broz dos Santos"
git config --global user.email "euejaojaoeeu@gmail.com"

gh auth login
```

Respostas: `GitHub.com` → `HTTPS` → `Y` → `Login with a web browser`.
Código de 8 caracteres → Firefox → `github.com/login/device`.

```bash
cd ~
gh repo clone Jr-Broz/projeto-pb-Jr-Broz projeto-pb
cd projeto-pb
git checkout dev
ls
```

## 1.5 🐧 UBUNTU — recompilar o TP1

```bash
cd ~/projeto-pb/ros2_ws
colcon build --symlink-install
source install/setup.bash
ros2 pkg list | grep percepcao
```

Se aparecer `percepcao_aracnideos`, o TP1 está de pé no usuário novo.

---

# ETAPA 2 — Instalar o TP2

🐧 **UBUNTU** — baixe o `aracne-tp2.zip` pelo Firefox **dentro da VM** e:

```bash
cd ~/projeto-pb
unzip -o ~/Downloads/aracne-tp2.zip -d .
find ros2_ws/src -maxdepth 2 -type d
ls scripts/
```

Deve aparecer o pacote novo `percepcao_aracnideos_interfaces` ao lado
do `percepcao_aracnideos`.

## 2.1 Dependências e modelo

```bash
chmod +x scripts/*.sh
./scripts/setup.sh
```

Isso instala o que falta (RViz2, robot_state_publisher, joint_state_publisher_gui)
e baixa o `yolov8n.onnx` (13 MB) para `models/`.

**Se o download falhar, siga em frente.** O detector degrada para
segmentação HSV sozinho e todos os itens do TP2 continuam
demonstráveis — só a classe detectada muda.

---

# ETAPA 3 — Compilar (a ORDEM importa)

```bash
cd ~/projeto-pb/ros2_ws
source /opt/ros/humble/setup.bash

# 1º as interfaces — o outro pacote depende delas
colcon build --packages-select percepcao_aracnideos_interfaces
source install/setup.bash

# 2º os nós
colcon build --packages-select percepcao_aracnideos --symlink-install
source install/setup.bash
```

> ⚠️ **Compilar tudo de uma vez costuma falhar na primeira tentativa**
> com `ModuleNotFoundError: percepcao_aracnideos_interfaces`. O colcon
> compila em paralelo e o gerador de interfaces ainda não terminou
> quando o pacote Python é processado. Compilar em dois passos, com
> `source` no meio, resolve de vez. Se já deu erro, rode o segundo
> comando de novo — funciona.

## 3.1 O teste de 20 segundos

```bash
ros2 pkg list | grep percepcao
ros2 interface list | grep percepcao_aracnideos_interfaces
ros2 pkg executables percepcao_aracnideos
```

Esperado:

```
percepcao_aracnideos
percepcao_aracnideos_interfaces
percepcao_aracnideos_interfaces/msg/DeteccaoAracnideo
percepcao_aracnideos_interfaces/msg/ListaDeteccoes
percepcao_aracnideos_interfaces/srv/ConfigurarDeteccao
percepcao_aracnideos_interfaces/action/VarrerCena
percepcao_aracnideos camera_node
percepcao_aracnideos deteccao_node
percepcao_aracnideos varredura_action_client
percepcao_aracnideos varredura_action_server
percepcao_aracnideos vision_node
```

**Se as interfaces não aparecerem, pare aqui e me chame.** Nada
adiante funciona sem elas.

---

# ETAPA 4 — Caminho rápido: um comando gera quase tudo

```bash
cd ~/projeto-pb
./scripts/reproduzir.sh webcam      # ou: ./scripts/reproduzir.sh sintetico
```

Ele compila, sobe o sistema e grava sozinho em `docs/evidencias/tp2/`:

| Arquivo | Item do enunciado |
|---|---|
| `interfaces-list.txt` | 1 — msg, srv, action |
| `urdf-check.txt` | 4 — árvore de links e juntas |
| `deteccoes-topico.txt` | 3 — detecções com id de rastreio |
| `params-dinamicos.txt` | 4 — `ros2 param set` em execução |
| `acao-completa.txt` | 2 — goal → feedback → result |
| `acao-cancelada.txt` | 2 — cancelamento no meio |

**Deixe rodando** e vá para a Etapa 5, que são as evidências visuais.

---

# ETAPA 5 — Evidências que precisam de tela

Abra um **segundo terminal**:

```bash
source /opt/ros/humble/setup.bash
source ~/projeto-pb/ros2_ws/install/setup.bash
export ROS_LOCALHOST_ONLY=1
```

> Confira que `echo $ROS_DOMAIN_ID` e `echo $ROS_LOCALHOST_ONLY` batem
> com o outro terminal. Foi exatamente isso que travou você no TP1.

## 5.1 `rastreamento.png` — item 3

```bash
ros2 run rqt_image_view rqt_image_view
```

Escolha **`/aracne/imagem_anotada`** no dropdown. Você vai ver bounding
box, rótulo com id, e a trilha com espessura crescente.

**Mexa o alvo em círculo por uns segundos** para a trilha ficar visível,
então:

```bash
gnome-screenshot -w -f ~/projeto-pb/docs/evidencias/tp2/rastreamento.png
```

(clique na janela do Image View antes; `-w` captura só a janela ativa)

## 5.2 `rqt_graph.png`

```bash
rqt_graph
```

Dropdown → **Nodes/Topics (all)**, desmarque **Debug**.

```bash
gnome-screenshot -w -f ~/projeto-pb/docs/evidencias/tp2/rqt_graph.png
```

## 5.3 `urdf_rviz.png` — item 4

Pare o `reproduzir.sh` (Ctrl+C) e rode só o URDF:

```bash
cd ~/projeto-pb
source ros2_ws/install/setup.bash
ros2 launch percepcao_aracnideos urdf.launch.py
```

No RViz2:
1. **Fixed Frame** → `base_footprint`
2. **Add** → **RobotModel** → em *Description Topic* escolha `/robot_description`
3. **Add** → **TF** (mostra os eixos de cada frame)
4. Mexa o slider `camera_tilt_joint` na janelinha do joint_state_publisher

```bash
gnome-screenshot -w -f ~/projeto-pb/docs/evidencias/tp2/urdf_rviz.png
```

## 5.4 `acao_simultanea.png` — item 2

O enunciado pede **"operação simultânea de servidor e cliente"**.
Coloque as duas janelas lado a lado.

Terminal A (servidor já sobe no launch — ou solto):
```bash
ros2 run percepcao_aracnideos varredura_action_server
```

Terminal B:
```bash
ros2 run percepcao_aracnideos varredura_action_client --ros-args -p duracao_s:=30.0
```

Com o feedback rolando nos dois, capture a **tela inteira**:

```bash
gnome-screenshot -d 3 -f ~/projeto-pb/docs/evidencias/tp2/acao_simultanea.png
```

## 5.5 `acao_cancelamento.png`

```bash
ros2 run percepcao_aracnideos varredura_action_client --ros-args \
  -p duracao_s:=30.0 -p cancelar_apos_s:=8.0
```

Deixe chegar no cancelamento (o cliente avisa `>>> ENVIANDO PEDIDO DE
CANCELAMENTO <<<` e o servidor responde), depois capture.

## 5.6 Conferir

```bash
ls -la ~/projeto-pb/docs/evidencias/tp2/
```

---

# ETAPA 6 — Comandos soltos, para o vídeo

Estes são os que rendem boa demonstração:

```bash
# item 1 — as interfaces existem e têm os campos certos
ros2 interface list | grep percepcao
ros2 interface show percepcao_aracnideos_interfaces/action/VarrerCena

# item 2 — mandar goal direto pela CLI, sem o cliente
ros2 action send_goal -f /aracne/varrer_cena \
  percepcao_aracnideos_interfaces/action/VarrerCena \
  "{duracao_s: 15.0, classe_alvo: '', limiar_confianca: -1.0}"
# o -f mostra o feedback; Ctrl+C no meio cancela o goal

# item 3 — as detecções com id de rastreio e centroide filtrado
ros2 topic echo /aracne/deteccoes --once
ros2 topic hz /aracne/deteccoes

# item 4 — parâmetro mudando AO VIVO (mostre o rqt_image_view junto!)
ros2 param get /deteccao_node limiar_confianca
ros2 param set /deteccao_node limiar_confianca 0.85    # caixas somem
ros2 param set /deteccao_node limiar_confianca 0.25    # caixas voltam
ros2 param set /deteccao_node tamanho_trilha 200       # trilha estica
ros2 param set /deteccao_node desenhar_trilha false    # trilha some

# item 4 — o mesmo efeito pelo serviço customizado
ros2 service call /aracne/configurar_deteccao \
  percepcao_aracnideos_interfaces/srv/ConfigurarDeteccao \
  "{limiar_confianca: 0.6, tamanho_trilha: 80, desenhar_trilha: 1}"
```

> **A melhor cena do vídeo:** `rqt_image_view` aberto mostrando a
> detecção, e você digitando `ros2 param set ... limiar_confianca 0.85`
> — as caixas desaparecem na hora. Depois `0.25` e voltam. Isso é
> "alteração dinâmica em tempo de execução" demonstrada, não descrita.

---

# ETAPA 6.5 — Robustez (o diferencial da defesa)

## Gerar as evidências quantitativas

```bash
cd ~/projeto-pb
python3 scripts/experimento_robustez.py
```

Roda em ~2 min, sem ROS, e grava três arquivos em `docs/evidencias/tp2/`:
`robustez-degradacoes.txt`, `robustez-histerese.txt` e
`robustez-painel.png`.

## Demonstrar no vídeo

**A histerese ao vivo** — mostre por que dois limiares batem um só:

```bash
# limiar único alto: o alvo some quando a luz piora
ros2 param set /deteccao_node limiar_manutencao 0.45
# histerese: o mesmo alvo sobrevive
ros2 param set /deteccao_node limiar_manutencao 0.25
```

Com o `rqt_image_view` aberto, **escureça a cena** (apague a luz, tampe
parcialmente a câmera). Com limiar único a caixa pisca e o `#id` muda;
com histerese o `#id` fica.

**O alerta de qualidade** — a terceira linha do HUD aparece sozinha
quando a imagem degrada, dizendo `IMAGEM: subexposta, desfocada`.
Apagar a luz durante a gravação faz esse alerta surgir na tela.

**O pré-processamento** — e por que está desligado:

```bash
ros2 param set /deteccao_node preproc_ativo true    # HUD mostra "tratada: clahe,gama"
ros2 param set /deteccao_node preproc_ativo false
```

> Essa é a cena que separa nota **D** de **DL**. A rubrica premia
> "análise crítica e tratamento de caso difícil". Dizer *"implementei,
> medi, e os números não sustentaram — então deixei desligado"* é mais
> forte que qualquer filtro ligado sem justificativa.


---

# ETAPA 7 — Relatório, PDF, vídeo

```bash
gedit ~/projeto-pb/docs/relatorios/relatorio-tp2.md &
```

Preencha os `[COLCHETES]`. Depois:

```bash
cd ~/projeto-pb/docs/relatorios
pandoc relatorio-tp2.md -o relatorio-tp2.html --self-contained
firefox relatorio-tp2.html &
```

Firefox → **Ctrl+P** → **Salvar em PDF** → `relatorio-tp2.pdf` nessa pasta.

> **Role a prévia antes de salvar** e confirme que as imagens aparecem.
> No TP1 uma delas não entrou.

## Vídeo (até 5 min)

🖥️ **FEDORA:** `obs-studio`. Roteiro sugerido:

| Tempo | Conteúdo |
|---|---|
| 0:00–0:25 | Você: nome, projeto, o que mudou do TP1 para o TP2 |
| 0:25–1:05 | `ros2 interface show` das três interfaces (item 1) |
| 1:05–2:05 | Action server + client lado a lado, feedback rolando (item 2) |
| 2:05–2:35 | **Cancelamento** com `cancelar_apos_s` (item 2) |
| 2:35–3:20 | `rqt_image_view`: YOLO, bbox, trilha suavizada (item 3) |
| 3:20–3:50 | `ros2 param set limiar_confianca 0.85` → caixas somem ao vivo (item 4) |
| 3:50–4:20 | **Robustez**: apaga a luz, alerta de qualidade aparece, histerese segura o id |
| 4:20–4:40 | RViz com o URDF, mexendo o `camera_tilt_joint` (item 4) |
| 4:40–5:00 | `rqt_graph`, limitações honestas, o que vem no TP3 |

Suba no YouTube como **não listado**. Cole o link em `ARTEFATOS.md`,
no `README.md` e no relatório. **Teste em aba anônima.**

---

# ETAPA 8 — Entrega

```bash
cd ~/projeto-pb
git add -A
git commit -m "G2.0/G2.1: interfaces customizadas msg, srv e action"
git commit --allow-empty -m "G2.2/G2.3: action server com feedback e cancelamento"
git add -A && git commit -m "G2.4: deteccao YOLO com rastreamento por filtro de Kalman"
git add -A && git commit -m "G2.5: parametrizacao YAML e URDF do robo"
git push origin dev
```

(Faça commits de verdade conforme for avançando — o histórico é critério
de avaliação. Um commit gigante na véspera conta contra.)

Quando **tudo** estiver pronto, inclusive o PDF e o link do vídeo:

```bash
git checkout main && git merge dev && git push
git checkout entrega-tp2 && git merge --ff-only main && git push
git tag tp2 && git push origin tp2
git checkout dev
git tag --list
```

ZIP:

```bash
cd ~/projeto-pb
zip -r ~/tp2-JoaoRafaelBroz.zip . \
  -x "*/build/*" "*/install/*" "*/log/*" ".git/*" "*.pyc" "*__pycache__*" "models/*"
ls -lh ~/tp2-*.zip
unzip -l ~/tp2-*.zip | grep -E "pdf|onnx"
```

> `models/*` fica **fora** do ZIP e fora do git: é arquivo grande, e a
> regra da disciplina manda usar link público. O `baixar_modelo.sh`
> está versionado — essa é a "fonte do artefato derivado" que o
> professor pede.

Pasta de entrega:

```bash
mkdir -p ~/ENTREGA-TP2
cp ~/projeto-pb/docs/relatorios/relatorio-tp2.pdf ~/ENTREGA-TP2/
cp ~/tp2-JoaoRafaelBroz.zip ~/ENTREGA-TP2/
ls -lh ~/ENTREGA-TP2/
```

Moodle: PDF + ZIP + link do repositório + link do vídeo.
**Depois de enviar, baixe e abra os dois.**

---

# Quando não coopera

| Sintoma | Cura |
|---|---|
| `ModuleNotFoundError: percepcao_aracnideos_interfaces` | Compile as interfaces primeiro, `source`, depois o outro pacote |
| `ros2 interface list` não mostra as minhas | O build das interfaces falhou — veja `log/latest_build` |
| `action /aracne/varrer_cena não aparece` | O `varredura_action_server` não subiu; veja `docs/evidencias/tp2/launch.log` |
| Cliente diz "server não apareceu em 15s" | `ROS_DOMAIN_ID` ou `ROS_LOCALHOST_ONLY` diferentes entre terminais |
| Feedback trava e o cancelamento não responde | Seria falta de `MultiThreadedExecutor` — já está no código; confirme que rodou o executável certo |
| `libexec directory does not exist` | `setup.cfg` com nome antigo |
| Mudei o YAML e nada mudou | **Recompile** — `--symlink-install` não linka `config/` |
| YOLO não detecta nada | Baixe o limiar: `ros2 param set /deteccao_node limiar_confianca 0.25` |
| Detector diz `hsv-fallback` | `models/yolov8n.onnx` não existe; rode `./scripts/baixar_modelo.sh` |
| RViz mostra o robô branco/sem forma | Fixed Frame errado — use `base_footprint` |
| RViz: "No transform from [x] to [base_footprint]" | O `robot_state_publisher` não subiu |
| `A message was lost!!!` | `export ROS_LOCALHOST_ONLY=1` em **todos** os terminais |
| Webcam sumiu | 🖥️ FEDORA: `VBoxManage controlvm "Ubuntu22.04ROS2Humble" webcam attach .1` |
