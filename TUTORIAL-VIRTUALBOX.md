# ETAPA 1 (Rota A) — VirtualBox no Fedora

> Substitui a seção "Rota A" do TUTORIAL.md. O comando que estava lá
> (`dnf install VirtualBox` puro) falha: o Fedora não distribui o host do
> VirtualBox nos repositórios padrão, só as guest additions.

---

## 1.1 🖥️ FEDORA — diagnóstico primeiro

```bash
mokutil --sb-state
uname -r
```

| Saída | O que significa | Seu caminho |
|---|---|---|
| `SecureBoot disabled` | Caminho curto | Pule o passo 1.5 |
| `SecureBoot enabled` | Precisa assinar os módulos | Faça o 1.5, com reboot |
| `EFI variables are not supported` | Sistema legacy, sem Secure Boot | Pule o 1.5 |

---

## 1.2 🖥️ FEDORA — habilitar o RPM Fusion Free

```bash
sudo dnf install -y \
  https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm
```

---

## 1.3 🖥️ FEDORA — dependências de compilação

Os módulos do VirtualBox são compilados contra o **kernel que está rodando
agora**. Se o `kernel-devel` não bater com o `uname -r`, a compilação falha
com erro de header incompatível.

```bash
sudo dnf install -y akmods kernel-devel-$(uname -r) kernel-headers \
    gcc make dkms elfutils-libelf-devel
```

Se o `kernel-devel-$(uname -r)` não for encontrado, seu kernel é mais novo
que o pacote disponível. Nesse caso:

```bash
sudo dnf install -y kernel-devel-matched
sudo dnf update -y kernel kernel-devel
sudo reboot        # reinicie para rodar o kernel que tem devel casado
```

---

## 1.4 🖥️ FEDORA — instalar e construir os módulos

```bash
sudo dnf install -y VirtualBox
sudo akmods --force --kernels $(uname -r)
sudo systemctl restart vboxdrv 2>/dev/null || true
sudo usermod -aG vboxusers $USER
```

**Teste se o módulo carregou:**

```bash
sudo modprobe vboxdrv && echo "MODULO OK" || echo "MODULO FALHOU"
lsmod | grep vbox
VBoxManage --version
```

- `MODULO OK` → pule para o 1.6.
- `Key was rejected by service` → é Secure Boot. Vá para o 1.5.
- Outro erro → veja os logs de build:
  `ls /var/cache/akmods/VirtualBox/` e leia o `.log` mais recente.

---

## 1.5 🖥️ FEDORA — Secure Boot (só se o 1.4 falhou com "Key was rejected")

O akmods já assina os módulos com uma chave própria — o que falta é o
firmware **confiar** nela. São três passos, e o do meio exige reboot.

### Passo 1 — gerar e registrar a chave

```bash
sudo kmodgenca -a
sudo mokutil --import /etc/pki/akmods/certs/public_key.der
```

Ele vai pedir uma **senha de uso único**. Escolha algo simples que você
consiga digitar de cabeça (ex.: `12345678`). Você vai usá-la em 2 minutos e
nunca mais.

### Passo 2 — reboot e a tela azul

```bash
sudo reboot
```

Na inicialização aparece uma **tela azul, MOK Management**. Ela **não espera
para sempre** — se você não tocar em nada, o boot segue normal e você perde
a janela. Navegue com as setas do teclado:

1. `Enroll MOK`
2. `Continue`
3. `Yes`
4. Digite **a senha do passo 1**
5. `Reboot`

> O teclado nessa tela pode estar em layout US. Se sua senha tiver
> caracteres especiais e não for aceita, foi isso — por isso a sugestão de
> usar só números.

### Passo 3 — confirmar

```bash
sudo modprobe vboxdrv && echo "MODULO OK"
mokutil --list-enrolled | grep -i akmod
```

> **Isso se repete a cada troca de kernel.** Quando o Fedora atualizar o
> kernel e o VirtualBox parar de funcionar do nada, rode
> `sudo akmods --force --kernels $(uname -r)` — a chave já registrada continua valendo.

### Alternativa mais rápida (mas menos limpa)

Desligar o Secure Boot na BIOS/UEFI. Reinicie, entre no setup (F2, F10, F12
ou Del, depende do fabricante), procure **Security → Secure Boot → Disabled**,
salve e saia. Resolve em 2 minutos, mas reduz a proteção de boot da máquina.

---

## 1.6 🖥️ FEDORA — Extension Pack (é o que faz a webcam funcionar)

Sem ele, **não existe webcam dentro da VM.**

```bash
VBoxManage --version        # anote a versão, ex.: 7.1.4
```

🌐 **NAVEGADOR:** baixe em `virtualbox.org/wiki/Downloads` o **Extension
Pack da MESMA versão** que apareceu acima. Versão diferente é recusada.

```bash
cd ~/Downloads
sudo VBoxManage extpack install --replace Oracle_*.vbox-extpack
VBoxManage list extpacks     # tem que listar o pack
```

Aceite a licença quando ele perguntar.

---

## 1.7 🖥️ FEDORA — relogar

O grupo `vboxusers` só vale em sessão nova.

```bash
groups | grep vboxusers      # se não aparecer, faça logout/login
```

---

## 1.8 🖥️ FEDORA — criar a VM

Abra o VirtualBox e crie a máquina com a ISO `Ubuntu22.04ROS2` do professor.

| Configuração | Valor | Por quê |
|---|---|---|
| Tipo | Linux / Ubuntu (64-bit) | |
| Memória | **4096 MB** | Você tem 8 GB no host. Mais que isso trava o Fedora. |
| Processadores | **2** | Sistema → Processador |
| Disco | **40 GB**, dinamicamente alocado | |
| Vídeo | 128 MB, aceleração 3D **desligada** | 3D em VM dá mais problema que ajuda |
| Rede | NAT (padrão) | |

Instale o Ubuntu normalmente. Escolha **instalação mínima** se ele oferecer —
economiza uns 5 minutos.

---

## 1.9 🐧 UBUNTU — o ROS 2 já está aí?

A ISO do professor se chama `Ubuntu22.04ROS2`, então é bem provável que o
ROS 2 já venha instalado. **Confira antes de instalar de novo:**

```bash
lsb_release -a                    # tem que dizer 22.04 / jammy
ls /opt/ros/                      # tem que listar 'humble'
source /opt/ros/humble/setup.bash
ros2 --version
```

- **Se `ros2 --version` responder:** ROS 2 já está lá. Economizou 30 minutos.
  Pule para o 1.11.
- **Se não:** faça o 1.10.

---

## 1.10 🐧 UBUNTU — instalar o ROS 2 Humble (só se o 1.9 falhou)

```bash
sudo apt update && sudo apt install -y curl gnupg lsb-release software-properties-common
sudo add-apt-repository universe -y

sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
  -o /usr/share/keyrings/ros-archive-keyring.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" \
  | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null

sudo apt update
sudo apt install -y ros-humble-desktop python3-colcon-common-extensions python3-rosdep

sudo rosdep init 2>/dev/null || true
rosdep update

echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
source ~/.bashrc
ros2 --version
```

---

## 1.11 🐧 UBUNTU — Guest Additions (tela cheia e copiar/colar)

Na barra da VM: **Dispositivos → Inserir imagem de CD dos Adicionais para Convidado**

```bash
sudo apt update && sudo apt install -y build-essential dkms linux-headers-$(uname -r)
sudo mkdir -p /mnt/cdrom && sudo mount /dev/cdrom /mnt/cdrom
sudo /mnt/cdrom/VBoxLinuxAdditions.run
sudo usermod -aG vboxsf $USER
sudo reboot
```

Opcional, mas melhora muito a gravação do vídeo. Se estiver com pressa,
pule — não bloqueia nenhum gate.

---

## 1.12 🐧 UBUNTU — a webcam

Com a VM rodando, na barra do VirtualBox:
**Dispositivos → Webcams → [sua Logitech]**

```bash
sudo apt install -y v4l-utils
ls -l /dev/video*
v4l2-ctl --list-devices
v4l2-ctl -d /dev/video0 --list-formats-ext
```

Guarde a saída do `--list-formats-ext`: é o que a câmera **aceita de
verdade**. Pedir resolução fora dessa lista dá 5 fps silenciosos.

### Permissão

```bash
sudo usermod -aG video "$USER"
newgrp video
groups                # tem que listar 'video'
```

### Teste isolado, antes de envolver o ROS

```bash
python3 -c "import cv2; c=cv2.VideoCapture(0, cv2.CAP_V4L2); ok,f=c.read(); print(ok, None if f is None else f.shape)"
```

Esperado: `True (480, 640, 3)`. Se vier `False None`, o problema **não é o
seu nó** — volte para o menu Dispositivos → Webcams e para a permissão.

---

## 1.13 🐧 UBUNTU — checagem final antes de seguir

```bash
lsb_release -a | grep jammy && echo "UBUNTU 22.04 OK"
ros2 --version && echo "ROS 2 OK"
ls /dev/video0 2>/dev/null && echo "CAMERA OK" || echo "camera ausente — use fonte:=sintetico"
```

Se as duas primeiras respondem, **você passou a parte difícil.**
Siga para a ETAPA 2 do TUTORIAL.md.

---

# Quando não coopera

| Sintoma | Cura |
|---|---|
| `No match for argument: VirtualBox` | Faltou o RPM Fusion (1.2) |
| `Key was rejected by service` | Secure Boot — faça o 1.5 |
| `kernel-devel-$(uname -r)` não existe | Kernel mais novo que o pacote — `dnf update kernel` e reboot |
| Módulo compilou e não carrega | `ls /var/cache/akmods/VirtualBox/` e leia o `.log` |
| Perdi a tela azul do MOK | Refaça o `mokutil --import` e reinicie |
| Senha do MOK recusada | Teclado em layout US — use só números |
| Extension Pack recusado | Versão diferente do VirtualBox instalado |
| VM não passa de 2 GB de RAM | Host com pouca memória livre — feche o navegador |
| Sem `/dev/video0` na VM | Dispositivos → Webcams no menu; e o Extension Pack tem que estar instalado |
| VirtualBox parou depois de atualizar o Fedora | Kernel novo: `sudo akmods --force --kernels $(uname -r)` |
| SELinux bloqueando | `sudo setenforce 0` para testar; se resolver, crie a política em vez de deixar desligado |
