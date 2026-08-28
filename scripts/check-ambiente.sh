#!/usr/bin/env bash
# check-ambiente.sh — confere se seu ambiente está pronto para a disciplina.
# Rode DENTRO do WSL (Ubuntu). NÃO altera nada, só verifica.
# Uso rápido (sem clonar):
#   curl -sSL https://raw.githubusercontent.com/Prof-Dacio-INFNET/PBRoboticos_prof_dacio/main/recursos/check-ambiente.sh | bash
ok(){ printf "  \033[32m✓\033[0m %s\n" "$1"; }
no(){ printf "  \033[31m✗\033[0m %s\n" "$1"; FAIL=1; }
inf(){ printf "  · %s\n" "$1"; }
FAIL=0
echo "== Checagem de ambiente — PB Sistemas Robóticos =="

# 1) Ubuntu jammy
. /etc/os-release 2>/dev/null
[ "$UBUNTU_CODENAME" = "jammy" ] && ok "Ubuntu 22.04 (jammy)" || no "Ubuntu não é 22.04/jammy (é '${UBUNTU_CODENAME:-?}') — use a distro Ubuntu-22.04"

# 2) ROS 2 Humble
[ -f /opt/ros/humble/setup.bash ] && ok "ROS 2 Humble instalado" || no "ROS 2 Humble ausente (tutorial setup, Passos 3–5)"
if command -v ros2 >/dev/null 2>&1; then ok "comando ros2 disponível"; else no "ros2 não encontrado — faltou instalar ou 'source /opt/ros/humble/setup.bash' (adicione no ~/.bashrc)"; fi

# 3) colcon
command -v colcon >/dev/null 2>&1 && ok "colcon" || no "colcon ausente (python3-colcon-common-extensions)"

# 4) git / gh / uv
command -v git >/dev/null 2>&1 && ok "git" || no "git ausente"
if command -v gh >/dev/null 2>&1; then
  gh auth status >/dev/null 2>&1 && ok "gh autenticado" || no "gh instalado mas não autenticado (gh auth login)"
else no "gh (GitHub CLI) ausente"; fi
command -v uv >/dev/null 2>&1 && ok "uv" || inf "uv ausente (opcional agora; necessário nos TPs 2+)"

# 5) ROS_DOMAIN_ID
if [ -z "$ROS_DOMAIN_ID" ] || [ "$ROS_DOMAIN_ID" = "0" ]; then inf "ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-vazio} — defina seu nº de chamada no ~/.bashrc"; else ok "ROS_DOMAIN_ID=$ROS_DOMAIN_ID"; fi

# 6) repositório + branches (se rodado dentro do repo)
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  ok "dentro de um repositório git ($(basename "$(git rev-parse --show-toplevel)"))"
  git show-ref --verify --quiet refs/heads/dev && ok "branch dev existe" || no "branch dev ausente — rode ./scripts/init-branches.sh"
  case "$(git rev-parse --show-toplevel)" in /mnt/c/*) no "repo em /mnt/c (lento) — clone DENTRO do WSL (~)";; *) ok "repo no filesystem do WSL";; esac
else
  inf "rode este script DENTRO do seu repositório clonado para checar as branches"
fi

echo ""
[ "$FAIL" = 0 ] && echo "✅ Tudo pronto!" || echo "⚠️  Há itens pendentes acima — veja os tutoriais e rode de novo."
