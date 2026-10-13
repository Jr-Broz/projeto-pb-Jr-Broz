#!/usr/bin/env bash
# Compila o workspace, sobe o sistema e gera as evidencias do TP2.
#
# Uso:
#   ./scripts/reproduzir.sh                 # webcam, com fallback automatico
#   ./scripts/reproduzir.sh sintetico       # forca a cena gerada em codigo
#
# Gera em docs/evidencias/tp2/:
#   interfaces-list.txt   item 1  (ros2 interface list/show)
#   acao-completa.txt     item 2  (goal -> feedback -> result)
#   acao-cancelada.txt    item 2  (cancelamento no meio)
#   deteccoes-topico.txt  item 3  (ListaDeteccoes com id de rastreio)
#   params-dinamicos.txt  item 4  (ros2 param set em execucao)
#   urdf-check.txt        item 4  (arvore de links e juntas)
#
# As evidencias visuais (imagem anotada, rqt_graph, RViz) exigem tela e
# estao listadas no fim.
set -e

FONTE="${1:-webcam}"
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
EVID="$RAIZ/docs/evidencias/tp2"
MODELO="$RAIZ/models/yolov8n.onnx"
mkdir -p "$EVID"

source /opt/ros/humble/setup.bash
export ROS_LOCALHOST_ONLY=1

[ -f "$MODELO" ] || MODELO=""
[ -n "$MODELO" ] && echo "[info] YOLO: $MODELO" || echo "[info] sem modelo — detector cai para HSV"

echo "[1/7] compilando (interfaces primeiro)"
cd "$RAIZ/ros2_ws"
colcon build --packages-select percepcao_aracnideos_interfaces
source install/setup.bash
colcon build --packages-select percepcao_aracnideos --symlink-install
source install/setup.bash

echo "[2/7] evidencia das interfaces customizadas"
{
  echo "=== ros2 interface list | grep percepcao ==="
  ros2 interface list | grep percepcao_aracnideos_interfaces || true
  echo
  for i in msg/DeteccaoAracnideo msg/ListaDeteccoes srv/ConfigurarDeteccao action/VarrerCena; do
    echo "=== ros2 interface show percepcao_aracnideos_interfaces/$i ==="
    ros2 interface show "percepcao_aracnideos_interfaces/$i"
    echo
  done
} > "$EVID/interfaces-list.txt" 2>&1
echo "    -> $EVID/interfaces-list.txt"

echo "[3/7] validando o URDF"
{
  echo "=== estrutura do URDF ==="
  python3 - "$RAIZ/ros2_ws/src/percepcao_aracnideos/urdf/aracne_bot.urdf" <<'PY'
import sys, xml.etree.ElementTree as ET
r = ET.parse(sys.argv[1]).getroot()
links = [l.get('name') for l in r.findall('link')]
joints = [(j.get('name'), j.get('type'), j.find('parent').get('link'),
           j.find('child').get('link')) for j in r.findall('joint')]
print(f"robo   : {r.get('name')}")
print(f"links  : {len(links)}")
print(f"joints : {len(joints)}")
print(f"sensores gazebo: {len(r.findall('.//sensor'))}")
print()
print("--- arvore ---")
filhos = [c for _, _, _, c in joints]
raiz = [l for l in links if l not in filhos][0]
adj = {}
for n, t, p, c in joints:
    adj.setdefault(p, []).append((c, n, t))
def desenha(no, nivel=0):
    print("  " * nivel + ("+- " if nivel else "") + no)
    for c, jn, jt in adj.get(no, []):
        print("  " * (nivel + 1) + f"|  [{jn} : {jt}]")
        desenha(c, nivel + 1)
desenha(raiz)
PY
  echo
  if command -v check_urdf >/dev/null 2>&1; then
    echo "=== check_urdf ==="
    check_urdf "$RAIZ/ros2_ws/src/percepcao_aracnideos/urdf/aracne_bot.urdf"
  fi
} > "$EVID/urdf-check.txt" 2>&1
echo "    -> $EVID/urdf-check.txt"

echo "[4/7] subindo o sistema (fonte=$FONTE)"
LARGS=(fonte:="$FONTE")
[ -n "$MODELO" ] && LARGS+=(modelo:="$MODELO")
ros2 launch percepcao_aracnideos tp2.launch.py "${LARGS[@]}" \
  > "$EVID/launch.log" 2>&1 &
LAUNCH_PID=$!
trap 'kill $LAUNCH_PID 2>/dev/null || true' EXIT
sleep 12

echo "[5/7] evidencia do topico de deteccoes e dos parametros"
{
  echo "=== ros2 node list ==="; ros2 node list
  echo; echo "=== ros2 topic list ==="; ros2 topic list
  echo; echo "=== ros2 action list ==="; ros2 action list
  echo; echo "=== ros2 service list | grep aracne ==="
  ros2 service list | grep -i aracne || true
  echo; echo "=== /aracne/deteccoes (uma amostra) ==="
  timeout 10 ros2 topic echo /aracne/deteccoes --once 2>&1 || true
  echo; echo "=== taxa em /aracne/deteccoes (regua leve, 10 s) ==="
  timeout 10 ros2 topic hz /aracne/deteccoes 2>&1 | tail -8 || true
} > "$EVID/deteccoes-topico.txt" 2>&1
echo "    -> $EVID/deteccoes-topico.txt"

{
  echo "=== parametros declarados ==="
  ros2 param list /deteccao_node
  echo; echo "=== valor inicial ==="
  ros2 param get /deteccao_node limiar_confianca
  echo; echo "=== alterando em tempo de execucao ==="
  ros2 param set /deteccao_node limiar_confianca 0.70
  ros2 param get /deteccao_node limiar_confianca
  echo; echo "=== alterando o tamanho da trilha ==="
  ros2 param set /deteccao_node tamanho_trilha 120
  ros2 param get /deteccao_node tamanho_trilha
  echo; echo "=== o mesmo efeito pelo servico customizado ==="
  ros2 service call /aracne/configurar_deteccao \
    percepcao_aracnideos_interfaces/srv/ConfigurarDeteccao \
    "{limiar_confianca: 0.35, tamanho_trilha: 60, desenhar_trilha: 1}"
  echo; echo "=== de volta ao valor de projeto ==="
  ros2 param set /deteccao_node limiar_confianca 0.45
  ros2 param get /deteccao_node limiar_confianca
} > "$EVID/params-dinamicos.txt" 2>&1
echo "    -> $EVID/params-dinamicos.txt"

echo "[6/7] acao completa (goal -> feedback -> result)"
timeout 40 ros2 run percepcao_aracnideos varredura_action_client --ros-args \
  -p duracao_s:=12.0 > "$EVID/acao-completa.txt" 2>&1 || true
echo "    -> $EVID/acao-completa.txt"

echo "[7/7] acao cancelada no meio"
timeout 40 ros2 run percepcao_aracnideos varredura_action_client --ros-args \
  -p duracao_s:=25.0 -p cancelar_apos_s:=6.0 > "$EVID/acao-cancelada.txt" 2>&1 || true
echo "    -> $EVID/acao-cancelada.txt"

echo
echo "==================================================================="
echo "Evidencias automaticas geradas em docs/evidencias/tp2/"
echo
echo "Faltam as MANUAIS (precisam de tela):"
echo "  rastreamento.png -> ros2 run rqt_image_view rqt_image_view"
echo "                      (escolha /aracne/imagem_anotada)"
echo "  rqt_graph.png    -> rqt_graph"
echo "  urdf_rviz.png    -> ros2 launch percepcao_aracnideos urdf.launch.py"
echo "                      (no RViz: Add > RobotModel, Fixed Frame=base_footprint)"
echo "  acao_simultanea.png -> servidor e cliente lado a lado, com feedback"
echo
echo "O sistema segue rodando. Ctrl+C para encerrar."
echo "==================================================================="
wait $LAUNCH_PID
