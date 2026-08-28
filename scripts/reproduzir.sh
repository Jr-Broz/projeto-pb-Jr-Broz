#!/usr/bin/env bash
# Compila, sobe o sistema e gera as evidencias do TP1.
# Uso:  ./scripts/reproduzir.sh [webcam|sintetico]
#
# Sem argumento usa 'webcam'. Se a webcam nao abrir, o no cai
# sozinho para a fonte sintetica — a demo nao quebra.
set -e

FONTE="${1:-webcam}"
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
EVID="$RAIZ/docs/evidencias/tp1"
mkdir -p "$EVID"

source /opt/ros/humble/setup.bash
export ROS_LOCALHOST_ONLY=1   # evita perda de fragmento UDP em imagem crua

echo "[1/5] compilando"
cd "$RAIZ/ros2_ws"
colcon build --packages-select percepcao_aracnideos --symlink-install
source install/setup.bash

echo "[2/5] checagem do ambiente"
{
  echo "=== ros2 doctor ==="
  ros2 doctor --report 2>/dev/null | head -20
  echo
  echo "=== versoes ==="
  echo "ROS_DISTRO=$ROS_DISTRO"
  python3 -c "import sys, cv2; print('python', sys.version.split()[0]); print('opencv', cv2.__version__)"
  lsb_release -a 2>/dev/null
  echo
  echo "=== pacote visivel para o ament ==="
  ros2 pkg list | grep percepcao_aracnideos
  ros2 pkg executables percepcao_aracnideos
} > "$EVID/check-ambiente.txt" 2>&1
echo "    -> $EVID/check-ambiente.txt"

echo "[3/5] subindo o sistema (fonte=$FONTE)"
ros2 launch percepcao_aracnideos tp1.launch.py fonte:="$FONTE" &
LAUNCH_PID=$!
trap 'kill $LAUNCH_PID 2>/dev/null || true' EXIT
sleep 8

echo "[4/5] medindo a taxa em /vision/contagem (regua leve)"
{
  echo "=== ros2 topic hz /vision/contagem (12 s) ==="
  timeout 12 ros2 topic hz /vision/contagem 2>&1 | tail -12
  echo
  echo "=== ros2 topic list ==="
  ros2 topic list
  echo
  echo "=== contagem atual ==="
  timeout 5 ros2 topic echo /vision/contagem --once 2>&1
} > "$EVID/topic-hz.txt" 2>&1
echo "    -> $EVID/topic-hz.txt"

echo "[5/5] chamando o servico /vision/status"
{
  echo "=== ros2 service list ==="
  ros2 service list | grep vision
  echo
  echo "=== ros2 service call /vision/status ==="
  timeout 10 ros2 service call /vision/status std_srvs/srv/Trigger "{}"
} > "$EVID/servico-status.txt" 2>&1
cat "$EVID/servico-status.txt"

echo
echo "Evidencias automaticas geradas em docs/evidencias/tp1/"
echo "Faltam as MANUAIS (precisam de tela):"
echo "  segmentacao.png -> rqt_image_view /vision/anotada"
echo "  rqt_graph.png   -> rqt_graph"
echo
echo "O sistema segue rodando. Ctrl+C para encerrar."
wait $LAUNCH_PID
