# Tutorial — Setup do ambiente: WSL2 + Ubuntu 22.04 + ROS 2 Humble

**Disciplina:** PB Sistemas Robóticos · caminho padrão da disciplina (Windows 11). Ubuntu nativo/dual boot também é aceito — pule direto ao Passo 3. Tempo total: ~40–60 min (dependendo da internet).

## Passo 1 — Instalar o WSL2 com Ubuntu 22.04

No **PowerShell como Administrador**:

```powershell
wsl --install -d Ubuntu-22.04
```

Reinicie quando pedido. Na primeira abertura do Ubuntu, crie usuário e senha (a senha não aparece ao digitar — é normal). Depois, atualize o WSL:

```powershell
wsl --update
wsl --version    # confirme WSL versão 2.x e WSLg presente
```

> **Se falhar:** virtualização provavelmente desativada na BIOS/UEFI (procure *Intel VT-x / AMD SVM* e ative) ou recursos do Windows desligados (`Plataforma de Máquina Virtual` e `Subsistema do Windows para Linux` em "Ativar ou desativar recursos do Windows").

### ⚠️ Passo 1.5 — CONFIRA a versão antes de continuar (erro nº 1 da turma)

Se você **já tinha** um Ubuntu no WSL (ou instalou sem o `-d Ubuntu-22.04`), o terminal pode estar abrindo **outra versão** — ex.: Ubuntu 26.04 "Resolute Raccoon", que é o padrão atual do `wsl --install`. **O ROS 2 Humble só existe para o 22.04 (codinome `jammy`)** — em qualquer outro, o Passo 3 falha com `Unable to locate package ros-humble-desktop`.

No PowerShell:

```powershell
wsl --list --verbose              # liste os distros instalados
wsl -d Ubuntu-22.04               # abra especificamente o 22.04
wsl --set-default Ubuntu-22.04    # torne-o o padrão do terminal
```

E dentro do Ubuntu, confirme antes de seguir:

```bash
lsb_release -a    # DEVE mostrar: Ubuntu 22.04.x LTS (jammy)
```

Se mostrar outra versão, volte ao Passo 1 e instale o `Ubuntu-22.04` — não adianta continuar.

> 💼 **Você já usa WSL para trabalho/outras tarefas?** Mantenha uma **distro dedicada ao bloco** (`Ubuntu-22.04`) separada da sua distro de trabalho, e crie o hábito de conferir **em qual distro cada terminal está** antes de rodar qualquer coisa da disciplina (`lsb_release -a` na dúvida; o nome também aparece na aba do Windows Terminal). Misturar contextos é a receita para "funcionava ontem".

## Passo 2 — Preparar o Ubuntu

No terminal do Ubuntu:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y locales curl gnupg software-properties-common
sudo locale-gen pt_BR.UTF-8 en_US.UTF-8
```

## Passo 3 — Instalar o ROS 2 Humble (desktop-full)

Primeiro, a trava de segurança — este bloco só deixa continuar se o Ubuntu for o correto:

```bash
source /etc/os-release
[ "$UBUNTU_CODENAME" = "jammy" ] && echo "OK: Ubuntu 22.04 (jammy) — pode seguir" \
  || echo "PARE: este Ubuntu é '$UBUNTU_CODENAME' ($VERSION). O Humble exige 22.04 (jammy) — volte ao Passo 1.5"
```

Só depois do **OK**, instale (repare que o repositório usa `jammy` fixo, de propósito):

```bash
# habilitar o repositório universe
sudo add-apt-repository universe -y

# chave e repositório do ROS 2 (jammy = Ubuntu 22.04, alvo do Humble)
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
  -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] \
http://packages.ros.org/ros2/ubuntu jammy main" | \
  sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null

sudo apt update
sudo apt install -y ros-humble-desktop ros-dev-tools python3-colcon-common-extensions python3-rosdep
sudo rosdep init && rosdep update
```

## Passo 4 — Configurar o ambiente (faça uma vez)

```bash
echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
echo "export ROS_DOMAIN_ID=SEU_NUMERO" >> ~/.bashrc   # veja o aviso abaixo!
source ~/.bashrc
```

> ⚠️ **ROS_DOMAIN_ID — importante no laboratório:** máquinas na mesma rede com o mesmo domain ID **enxergam os tópicos umas das outras** — na aula, você veria os nós dos colegas misturados aos seus. Use um número único seu (ex.: seu número na lista de chamada, entre 1 e 101) em **todas** as suas máquinas.

## Passo 5 — Reiniciar o WSL e testar

**Antes dos testes gráficos, reinicie o WSL** (evita janelas cinzas/minúsculas com título `[WARN:COPY MODE]` — glitch conhecido do WSLg logo após instalações grandes). No **PowerShell**:

```powershell
wsl --shutdown
```

Reabra o Ubuntu-22.04 e teste:

```bash
ros2 doctor          # deve terminar com "All ... checks passed"
ros2 run demo_nodes_cpp talker    # terminal 1
ros2 run demo_nodes_py listener   # terminal 2 — deve ecoar as mensagens
ros2 run turtlesim turtlesim_node # janela gráfica deve abrir (WSLg)
rqt_graph                         # visualize o grafo — captura útil p/ relatórios!
```

**Capturas do `ros2 doctor` e do talker/listener são evidências do TP1 — guarde-as.**

## Passo 6 — Ferramentas da disciplina

```bash
sudo apt install -y git gh python3-opencv
git config --global user.name "Seu Nome"
git config --global user.email "seu-email@exemplo.com"
gh auth login
```

**Pacotes e ambientes Python: o padrão da disciplina é o [`uv`](https://docs.astral.sh/uv/)** (rápido e sem dor de cabeça de versões — não usaremos `pip` direto). Instale-o agora; ele será usado **sempre via ambientes virtuais**, nos tutoriais que precisarem:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc          # (ou abra um novo terminal)
uv --version
```

**Regras de ouro do Python na disciplina:**

1. **O Python do sistema é território do `apt`** — as bibliotecas base do TP1 já vieram nos passos anteriores (`python3-opencv` inclui o NumPy). Confirme:
   ```bash
   python3 -c "import cv2, numpy; print('OpenCV', cv2.__version__, '| NumPy', numpy.__version__)"
   ```
2. **Nunca `sudo uv ...`** (o uv vive no seu usuário; o root não o encontra) e **nunca `uv pip install --system`** (tentaria escrever nas pastas do sistema — sem permissão, e nem queremos mexer nelas).
3. Pacotes além do apt (YOLO, TensorFlow, MetaDrive — TPs 2+) entram em **ambientes `uv venv --system-site-packages`** (que continuam enxergando o `rclpy` do ROS) — cada tutorial que precisar mostrará o comando exato.

(Gazebo, YOLO, TensorFlow, MetaDrive etc. têm tutoriais próprios, publicados quando cada etapa precisar.)

## Problemas comuns

| Sintoma | Solução |
|---|---|
| `wsl --install` falha / WSL1 | Virtualização na BIOS; recursos do Windows; `wsl --set-default-version 2` |
| **`Unable to locate package ros-humble-desktop`** | Você não está no Ubuntu 22.04 — `lsb_release -a` para conferir (se aparecer 26.04 "resolute" ou outro, é o distro errado). Passo 1.5: abra/instale o `Ubuntu-22.04`. Limpeza no distro errado: `sudo rm /etc/apt/sources.list.d/ros2.list /usr/share/keyrings/ros-archive-keyring.gpg && sudo apt update` |
| `rosdep: command not found` | Consequência do erro acima: o `apt install` abortou e nada foi instalado. Resolva a versão do Ubuntu e repita o Passo 3 |
| `sudo: uv: command not found` | Não use `sudo` com uv — ele é instalado no SEU usuário (`~/.local/bin`), invisível para o root |
| `Permission denied ... dist-packages` (uv/pip) | Você tentou instalar no Python do sistema — não faça: o sistema é do `apt`; pacotes extras vão em `uv venv` (regras de ouro do Passo 6) |
| Janela gráfica não abre (turtlesim/rviz) | `wsl --update` no PowerShell e reinicie o WSL (`wsl --shutdown`); WSLg exige Win11 atualizado |
| Janela abre **cinza/minúscula com `[WARN:COPY MODE]`** | Glitch do WSLg pós-instalação: `wsl --shutdown` no PowerShell e reabra o Ubuntu — resolve |
| `ros2: command not found` | Faltou `source /opt/ros/humble/setup.bash` (confira o `.bashrc`) |
| Vejo tópicos/nós que não criei | Colega na mesma rede com o mesmo `ROS_DOMAIN_ID` — defina o seu (Passo 4) |
| apt muito lento / trava | Rede da instituição pode limitar — tente hotspot ou faça em casa |
| Pouco espaço em disco | A disciplina pede ~50 GB livres. Limpe dentro do Ubuntu: `sudo apt clean` e apague `build/ install/ log/` antigos. **Não use** `--set-sparse true` (o WSL atual desativou por risco de corrupção de dados; forçar com `--allow-unsafe` não vale o risco). Compactar o disco virtual é possível via `diskpart`/`compact vdisk` (avançado, opcional) |
| Webcam no WSL2 | Precisa do `usbipd-win` — **tutorial próprio da disciplina** (necessário a partir da Etapa 2) |

## Checklist final

- [ ] `ros2 doctor` passou · - [ ] talker/listener funcionando · - [ ] turtlesim abriu (GUI ok)
- [ ] `ROS_DOMAIN_ID` único definido · - [ ] git + gh autenticados + `uv` instalado · - [ ] capturas guardadas

**➡️ Próximo passo: tutorial "Workspace Colcon e o seu primeiro pacote ROS 2"** — é lá que você aprende a compilar e cria seu primeiro nó.

Dúvidas: traga na aula ou no Infnet.Online. Referências: docs oficiais ROS 2 Humble (https://docs.ros.org/en/humble/) e bibliografia A/B do bloco (O'Reilly).
