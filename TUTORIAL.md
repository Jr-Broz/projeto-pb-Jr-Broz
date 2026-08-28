# TUTORIAL — do zero até a entrega do TP1

**Leia a legenda antes de começar.** Cada bloco diz **onde** o comando roda.
Rodar no lugar errado é a causa nº 1 de erro que não parece erro de lugar.

| Marcador | Onde você digita |
|---|---|
| 🖥️ **FEDORA** | Terminal do seu Fedora, o sistema que você usa direto no notebook |
| 🐧 **UBUNTU** | Terminal dentro do Ubuntu 22.04 (VM ou container) — `lsb_release -a` tem que dizer `jammy` |
| 🌐 **NAVEGADOR** | Site, no navegador |

> **Teste de sanidade, use sempre que estiver na dúvida:**
> `lsb_release -a`
> Se disser `Ubuntu 22.04` e `jammy`, você está no 🐧 UBUNTU. Se disser
> Fedora ou der erro de comando, você está no 🖥️ FEDORA.

---

# ETAPA 0 — Escolher o ambiente (5 min de decisão, faça agora)

Você tem duas rotas. **Escolha uma e não olhe pra trás.**

## Rota A — VirtualBox (oficial e escolhida)

**Rota adotada.** É a que os professores usam, é rota documentada da
disciplina, e é a que você vai precisar nos TPs com Gazebo e RViz2.

⚠️ **O passo a passo dela está em `TUTORIAL-VIRTUALBOX.md`**, que corrige
duas armadilhas específicas do Fedora: o VirtualBox não está nos
repositórios padrão (precisa de RPM Fusion) e o Secure Boot bloqueia os
módulos de kernel.

Faça o `TUTORIAL-VIRTUALBOX.md` inteiro e volte aqui na ETAPA 2.

## Rota B — Docker (rápida)

**Escolha se:** o tempo é curto hoje.

Prós: ambiente de pé em ~20 min, e o `reproduzir.sh` roda idêntico.
Contras: **não é uma das três rotas oficiais.** Você precisa declarar isso
em `docs/decisoes.md` e no relatório, e migrar antes do TP2.

> A imagem `osrf/ros:humble-desktop` **é** Ubuntu 22.04 com Python 3.10 — a
> mesma base das rotas oficiais. O desvio é de embalagem, não de substância.
> Mas declare mesmo assim: limitação declarada custa pouco, escondida custa caro.

---

# ETAPA 1 — Montar o ambiente

## Rota A: VirtualBox

### 1.1 🖥️ FEDORA — instalar o VirtualBox

```bash
sudo dnf install -y VirtualBox
sudo usermod -aG vboxusers $USER
```

Reinicie a sessão (logout/login) para o grupo valer.

### 1.2 🌐 NAVEGADOR — baixar o Extension Pack

Baixe em `virtualbox.org/wiki/Downloads` o **Oracle VM VirtualBox Extension
Pack**. Ele é o que faz a webcam funcionar dentro da VM — sem ele, não tem
`/dev/video0`.

### 1.3 🖥️ FEDORA — instalar o Extension Pack

Abra o VirtualBox → Arquivo → Preferências → Extensões → botão de adicionar →
selecione o arquivo `.vbox-extpack` baixado.

### 1.4 🖥️ FEDORA — criar a VM

Use a ISO `Ubuntu22.04ROS2` que o professor passou.

| Configuração | Valor | Por quê |
|---|---|---|
| Memória | **4096 MB** | Você tem 8 GB no host. Passar disso trava o Fedora. |
| Processadores | **2** | |
| Disco | **40 GB**, dinamicamente alocado | |
| Rede | **NAT** (padrão) | Bridge só se for usar a Raspberry depois |
| Vídeo | 128 MB, aceleração 3D **desligada** | 3D em VM costuma dar mais problema que ajuda |

Instale o Ubuntu normalmente.

### 1.5 🐧 UBUNTU — ligar a webcam

Com a VM rodando, na barra do VirtualBox:
**Dispositivos → Webcams → [sua Logitech]**

Confira dentro do Ubuntu:

```bash
sudo apt install -y v4l-utils
ls -l /dev/video*
v4l2-ctl --list-devices
v4l2-ctl -d /dev/video0 --list-formats-ext
```

Guarde o que apareceu no `--list-formats-ext`: é a lista do que a câmera
**aceita de verdade**. Pedir resolução fora dessa lista dá 5 fps silenciosos,
e você perde uma hora achando que o problema é o ROS.

### 1.6 🐧 UBUNTU — permissão de câmera

```bash
sudo usermod -aG video "$USER"
newgrp video      # abre um shell novo já com o grupo
groups            # tem que listar 'video'
```

Se `/dev/video0` existe, tem grupo `video`, e mesmo assim dá `Permission
denied`, é porque a sessão atual carrega as credenciais antigas. `newgrp
video` resolve pra testar; logout/login resolve de vez.

**Pule para a ETAPA 2.**

---

## Rota B: Docker

### 1.1 🖥️ FEDORA — instalar e baixar a imagem

```bash
sudo dnf install -y docker
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
newgrp docker

docker pull osrf/ros:humble-desktop     # ~3 GB, deixe baixando
```

### 1.2 🖥️ FEDORA — liberar a tela e subir o container

```bash
xhost +local:docker

docker run -it --name aracne \
  --device=/dev/video0:/dev/video0 \
  --group-add video \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -v $HOME/projeto-pb-SEU-USUARIO:/home/ws \
  --network host \
  osrf/ros:humble-desktop bash
```

Linha por linha:

| Trecho | Para quê |
|---|---|
| `--device=/dev/video0` | passa a webcam pra dentro |
| `--group-add video` | permissão de leitura da câmera |
| `-e DISPLAY` + `-v /tmp/.X11-unix` | deixa `rqt_graph` e `rqt_image_view` abrirem janela |
| `-v $HOME/...:/home/ws` | **seu repositório é compartilhado.** O que você editar de um lado aparece do outro. É o que garante que o `git commit` do 🖥️ FEDORA veja o trabalho. |
| `--network host` | DDS conversa sem NAT no meio |

> **Depois de sair do container**, para voltar: `docker start -ai aracne`
> Para abrir um segundo terminal nele: `docker exec -it aracne bash`

### 1.3 🐧 UBUNTU (dentro do container) — dependências

```bash
apt update && apt install -y git gh v4l-utils nano
source /opt/ros/humble/setup.bash
```

---

# ETAPA 2 — 🌐 NAVEGADOR — GitHub Classroom

Você disse que já está no Classroom. Confirme estes dois pontos, porque o
segundo derruba muita gente:

1. Você **selecionou seu nome no roster** ao aceitar? É isso que vincula sua
   conta a você na correção.
2. Você **aceitou o convite que chegou por e-mail**? Sem ele, o repositório
   dá **404**. Procure "You've been invited to Prof-Dacio-INFNET" no e-mail
   institucional, inclusive no spam. Alternativa:
   `github.com/orgs/Prof-Dacio-INFNET/invitation`

Anote o nome exato do seu repositório: `projeto-pb-SEU-USUARIO`.

---

# ETAPA 3 — 🐧 UBUNTU — Git e clone

**Tudo daqui pra frente é dentro do Ubuntu.**

### 3.1 Configurar

```bash
sudo apt update && sudo apt install -y git gh
git config --global user.name "Seu Nome"
git config --global user.email "seu-email@al.infnet.edu.br"
gh auth login        # GitHub.com → HTTPS → Login with a web browser
```

### 3.2 Clonar — atenção ao lugar

```bash
cd ~                 # a home do Ubuntu, com espaço entre cd e ~
gh repo clone Prof-Dacio-INFNET/projeto-pb-SEU-USUARIO
cd projeto-pb-SEU-USUARIO
```

> **Nunca clone em pasta compartilhada** (`/media/sf_...` no VirtualBox).
> Compilar com colcon lá é muito mais lento, e o `git status` passa a acusar
> arquivos modificados que você nunca tocou, por causa de fim de linha.

### 3.3 Criar as branches

```bash
./scripts/init-branches.sh
git branch -a          # deve listar dev e as entrega-*
```

Isso roda **uma vez só**, no primeiro dia.

### 3.4 Trabalhar na dev

```bash
git checkout dev
```

---

# ETAPA 4 — 🐧 UBUNTU — Instalar o pacote ARACNE

Descompacte o ZIP que eu te mandei e copie o conteúdo **por cima** do
repositório clonado.

```bash
cd ~/projeto-pb-SEU-USUARIO
cp -r /caminho/do/zip/extraido/* .
```

> **Não apague nada que já veio no repositório.** `README.md`, `PROJETO.md`,
> `ARTEFATOS.md`, `scripts/`, `docs/`, `consulta/` e `.github/` são estruturas
> protegidas — um verificador automático marca **X vermelho** no commit se
> alguma sumir. Os meus arquivos preenchem o conteúdo delas, não as substituem.

Se `scripts/setup.sh` ou `scripts/reproduzir.sh` já existirem no repositório
com conteúdo do professor, **abra os dois** e decida: geralmente o template
vem vazio ou com um esqueleto, e o meu preenche. Na dúvida, junte.

### 4.1 Preencher o que é seu

Abra e troque os marcadores:

| Arquivo | Trocar |
|---|---|
| `PROJETO.md` | `[SEU NOME]`, `[SEU-USUARIO]` |
| `ARTEFATOS.md` | link do vídeo (depois de gravar) |
| `docs/relatorios/relatorio-tp1.md` | todos os `[COLCHETES]` |
| `ros2_ws/src/percepcao_aracnideos/package.xml` | `SEU NOME`, `SEU-EMAIL` |
| `ros2_ws/src/percepcao_aracnideos/setup.py` | idem |

### 4.2 Primeiro commit

```bash
git add -A
git commit -m "G1.1: declara projeto ARACNE — domínio, classes, trilha e plano B"
git push
```

---

# ETAPA 5 — 🐧 UBUNTU — Compilar

```bash
cd ~/projeto-pb-SEU-USUARIO/ros2_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select percepcao_aracnideos --symlink-install
source install/setup.bash
```

**Duas regras que evitam 90% das dores:**
1. Compile na raiz do `ros2_ws/`, **nunca** dentro de `src/`.
2. Depois de cada build, `source install/setup.bash`. Terminal novo = source de novo.

### 5.1 O teste de 10 segundos

Antes de rodar o launch, confirme os três lugares do nome:

```bash
ros2 pkg list | grep percepcao_aracnideos
ros2 pkg executables percepcao_aracnideos
ls install/percepcao_aracnideos/lib/percepcao_aracnideos
```

Se as três respondem, o `ros2 launch` vai funcionar. Cada linha testa uma
coisa diferente:

| Linha | Testa | Se falhar |
|---|---|---|
| 1ª | `resource/` + `package.xml` | `Package not found` |
| 2ª | `entry_points` do `setup.py` | `No executable found` |
| 3ª | `setup.cfg` | `libexec directory does not exist` |

---

# ETAPA 6 — 🐧 UBUNTU — Rodar e capturar evidências

## Opção rápida: o script faz quase tudo

```bash
cd ~/projeto-pb-SEU-USUARIO
./scripts/reproduzir.sh webcam
# se a webcam não abrir, ele cai sozinho para sintético
# ou force:  ./scripts/reproduzir.sh sintetico
```

Ele gera sozinho: `check-ambiente.txt` (**G1.0**), `topic-hz.txt` (**G1.2** e
**G1.3**) e `servico-status.txt` (**G1.4**).

## Opção manual, passo a passo

### Terminal A — sobe o sistema

```bash
cd ~/projeto-pb-SEU-USUARIO/ros2_ws
source install/setup.bash
export ROS_LOCALHOST_ONLY=1
ros2 launch percepcao_aracnideos tp1.launch.py fonte:=webcam
```

Olhe a linha que o `camera_node` imprime:
`webcam negociada: 640x480 MJPG @30fps`
Ela mostra o que a câmera **aceitou**, não o que foi pedido.

### Terminal B — mede e inspeciona

Abra outro terminal. **No Docker:** `docker exec -it aracne bash`

```bash
source /opt/ros/humble/setup.bash
source ~/projeto-pb-SEU-USUARIO/ros2_ws/install/setup.bash
export ROS_LOCALHOST_ONLY=1
```

**G1.2 — taxa estável.** Meça em `/vision/contagem`, não na imagem:

```bash
timeout 12 ros2 topic hz /vision/contagem | tee docs/evidencias/tp1/topic-hz.txt
```

> `ros2 topic hz /camera/image_raw` desserializa cada imagem inteira em
> Python. A 15 fps são ~13 MB/s passando por Python — ele mede a si mesmo se
> afogando, não o tópico. `/vision/contagem` são 4 bytes e anda junto do
> pipeline.
>
> Se aparecer `min:` **negativo**, pare: intervalo negativo entre mensagens
> não existe. É o relógio saltando, e ele estraga toda medição.

**G1.3 — contagem e segmentação:**

```bash
ros2 topic echo /vision/contagem --once
rqt_image_view /vision/anotada
```

Print da janela → salve como `docs/evidencias/tp1/segmentacao.png`

**G1.4 — serviço e grafo:**

```bash
ros2 service call /vision/status std_srvs/srv/Trigger "{}"
rqt_graph
```

Print → `docs/evidencias/tp1/rqt_graph.png`

### Ajustar o HSV para a sua cena

Se contar demais ou de menos, edite
`ros2_ws/src/percepcao_aracnideos/config/visao.yaml`:

| Sintoma | Ajuste |
|---|---|
| Conta ruído, respingos | ↑ `area_minima` (700 → 1500) |
| Não vê o alvo | ↓ `s_min` (110 → 80) e ↓ `v_min` |
| Pega coisa do fundo | ↑ `s_min` |
| Alvo não é vermelho | mude `h_min_a`/`h_max_a` (verde ≈ 40–80, azul ≈ 100–130) |

> **Depois de mudar YAML, RECOMPILE.** O `--symlink-install` linka os `.py`,
> mas copia os arquivos de `config/`. Se você mudou o YAML e o nó continua
> com os valores antigos, é isso — não é o código.

```bash
cd ~/projeto-pb-SEU-USUARIO/ros2_ws
colcon build --packages-select percepcao_aracnideos --symlink-install
```

---

# ETAPA 7 — Experimento de oclusão (G1.5)

Com `ros2 topic echo /vision/contagem` rodando, aproxime dois alvos até
encostarem. Anote:

| Situação | Esperado | Obtido |
|---|---|---|
| Separados | 2 | |
| Encostando | 2 | |
| Sobrepostos | 1 | |

Na fonte sintética os dois alvos se cruzam sozinhos — é de propósito, o
experimento acontece sem você fazer nada.

**A análise é o que vale nota:** `RETR_EXTERNAL` trata região conectada como
um contorno só. Dois alvos da mesma cor que encostam viram uma máscara só. É
**limitação estrutural do método**, não erro de parâmetro — nenhuma faixa HSV
separa dois objetos da mesma cor em contato. A separação exige watershed,
convexidade ou segmentação por instância (G3.4, no TP3).

---

# ETAPA 8 — Relatório e PDF

Preencha `docs/relatorios/relatorio-tp1.md`. Depois:

```bash
sudo apt install -y pandoc texlive-latex-recommended texlive-latex-extra
cd ~/projeto-pb-SEU-USUARIO/docs/relatorios
pandoc relatorio-tp1.md -o relatorio-tp1.pdf --pdf-engine=pdflatex \
  -V geometry:margin=2.5cm
```

**Abra o PDF e confira que as imagens apareceram.** Referência quebrada no
Markdown vira espaço em branco no PDF, e o avaliador não vê o que você viu.

Se o pandoc der trabalho, abra o `.md` no VS Code com a extensão
"Markdown PDF", ou cole no Google Docs e exporte. O caminho não importa; o
PDF legível com imagens importa.

---

# ETAPA 9 — Vídeo

🖥️ **FEDORA** (o OBS grava a tela toda, incluindo a janela da VM):

```bash
sudo dnf install -y obs-studio
```

No OBS: **Fontes → +** → *Captura de Tela*, e **+** de novo → *Dispositivo de
Captura de Vídeo* (a Logitech, num canto da tela).

> Se você estiver na Rota A e a webcam estiver **capturada pela VM**, o
> Fedora não a enxerga. Solução: grave a demo primeiro, depois libere a
> webcam da VM (Dispositivos → Webcams, desmarque) e grave sua fala.

Roteiro de 5 minutos:

| Tempo | Conteúdo |
|---|---|
| 0:00–0:30 | Você: nome, projeto, qual família do catálogo derivou |
| 0:30–1:15 | `PROJETO.md`: domínio, 4 espécies, trilha, plano B |
| 1:15–2:00 | `ros2 launch`, os dois nós subindo |
| 2:00–2:45 | `topic hz /vision/contagem` + `rqt_image_view` ao vivo |
| 2:45–3:20 | `service call /vision/status`, mostrando a info do domínio |
| 3:20–3:50 | `rqt_graph`: aponte os nós e o tópico entre eles |
| 3:50–4:30 | **Oclusão ao vivo**: contagem caindo de 2 para 1 |
| 4:30–5:00 | Limitações honestas + o que vem no TP2 |

O bloco de 3:50 é o que separa **D** de **DL**. A rubrica premia análise
crítica e tratamento de caso difícil. Mostrar a falha e explicar por que ela é
estrutural vale mais que uma demo perfeita e muda.

Suba no YouTube como **não listado** (nunca privado). Cole o link em
`ARTEFATOS.md` e no relatório. **Teste em aba anônima.**

---

# ETAPA 10 — Entrega

## 10.1 🐧 UBUNTU — commits por gate

Faça um commit por gate, com a mensagem começando pelo código:

```bash
cd ~/projeto-pb-SEU-USUARIO
git add docs/evidencias/tp1/check-ambiente.txt
git commit -m "G1.0: ambiente ROS 2 Humble operante, workspace compilando"

git add ros2_ws/src/percepcao_aracnideos docs/evidencias/tp1/topic-hz.txt
git commit -m "G1.2: publisher e subscriber com taxa estável em /vision/contagem"

git add docs/evidencias/tp1/segmentacao.png
git commit -m "G1.3: segmentação HSV com contagem de alvos do domínio"

git add docs/evidencias/tp1/rqt_graph.png docs/evidencias/tp1/servico-status.txt
git commit -m "G1.4: serviço /vision/status e grafo completo"

git add docs/relatorios/ ARTEFATOS.md docs/decisoes.md
git commit -m "G1.5: relatório fechado com oclusão e uso de IA declarado"

git push
```

Um commit gigante na véspera conta contra você. Cinco commits com códigos
de gate contam a favor.

## 10.2 🐧 UBUNTU — marcar os gates no PROJETO.md

Abra `PROJETO.md`, seção `<!-- PB:GATES -->`, e marque com honestidade:
`[x]` passou com evidência · `[ ]` ainda não chegou a data · `[!]` venceu sem passar.

Suas datas recomendadas já venceram (07/08 a 26/08). Se você fez tudo hoje,
o certo é `[x]` no que passou, com uma nota no relatório dizendo que a
execução foi concentrada em 28/08. Declarado custa pouco.

## 10.3 🐧 UBUNTU — branch e tag, na ordem certa

```bash
git checkout main && git merge dev && git push
git checkout entrega-tp1 && git merge --ff-only main && git push
git tag tp1 && git push origin tp1
git checkout dev
git tag --list          # tem que listar tp1
```

> As branches `entrega-*` **já existem** (o `init-branches.sh` criou). Não use
> `git checkout -b` — o `-b` cria uma nova e daria erro.
>
> Errou a tag? `git tag -d tp1 && git push origin :refs/tags/tp1`, corrija e
> recrie. **Só antes do prazo.**

## 10.4 🐧 UBUNTU — o ZIP

```bash
cd ~/projeto-pb-SEU-USUARIO
zip -r tp1-SEUNOME.zip . \
  -x "*/build/*" "*/install/*" "*/log/*" ".git/*" "*.pyc" "*__pycache__*"
unzip -l tp1-SEUNOME.zip | tail -5
```

**Confira o tamanho: o Moodle aceita até 4 arquivos de 20 MB cada.** Se
estourou, é imagem de evidência pesada — comprima os PNG ou mova o que for
grande para link, registrado no `ARTEFATOS.md`.

## 10.5 🌐 NAVEGADOR — Moodle

Envie: **PDF do relatório + ZIP do código + link do repositório + link do vídeo.**

> **O Moodle é a fonte da verdade. O que não está no Moodle não foi
> entregue, mesmo que esteja no GitHub.**

Depois de enviar: **baixe o próprio ZIP e o PDF e abra os dois.** Arquivo
errado, corrompido ou incompleto enviado é responsabilidade sua.

---

# Quando algo não coopera

| Sintoma | Onde | Causa e cura |
|---|---|---|
| Repositório dá 404 | 🌐 | Convite pendente no e-mail. `github.com/orgs/Prof-Dacio-INFNET/invitation` |
| `Package not found` | 🐧 | Faltou `source install/setup.bash` neste terminal |
| `No executable found` | 🐧 | `entry_points` do `setup.py` desalinhado |
| `libexec directory does not exist` | 🐧 | `setup.cfg` apontando para nome antigo |
| `ModuleNotFoundError` no import | 🐧 | Pasta do módulo com nome diferente do `package_name` |
| Mudei o YAML e nada mudou | 🐧 | Recompile — `--symlink-install` não linka `config/` |
| Mudei o `.py` e nada mudou | 🐧 | Compilou sem `--symlink-install`, ou não salvou |
| `VideoCapture` devolve `False` | 🐧 | Teste isolado: `python3 -c "import cv2; c=cv2.VideoCapture(0, cv2.CAP_V4L2); print(c.read()[0])"` — se falhar, o problema não é o ROS |
| `/dev/video0` não existe (Rota A) | 🐧 | Dispositivos → Webcams no menu do VirtualBox |
| `Permission denied` na câmera | 🐧 | `newgrp video`, depois `groups` para confirmar |
| `A message was lost!!!` | 🐧 | `export ROS_LOCALHOST_ONLY=1` em **todos** os terminais |
| Taxa ridícula | 🐧 | Meça em `/vision/contagem`. Se estiver boa, quem está lento é o observador |
| `rqt_image_view` não abre janela | 🐧 | Rota B: rode `xhost +local:docker` no 🖥️ FEDORA |
| `No module named 'PyQt5'` no rqt | 🐧 | Você está com um venv ativo. `deactivate` |
| `rcl_shutdown already called` no Ctrl+C | 🐧 | Ruído de encerramento, não quebra nada |
| `rejected: fetch first` no push | 🐧 | `git pull`, resolva, `git push` |
| X vermelho no commit | 🌐 | Você alterou/removeu estrutura protegida — restaure |
