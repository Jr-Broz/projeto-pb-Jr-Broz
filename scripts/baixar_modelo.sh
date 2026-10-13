#!/usr/bin/env bash
# Baixa o peso YOLOv8n em ONNX para models/.
#
# Por que ONNX e nao o .pt: o .pt exige PyTorch para ser lido (2-3 GB de
# instalacao). O ONNX e lido direto pelo modulo dnn do OpenCV, que ja
# esta instalado. Mesmo modelo, mesmos pesos, 13 MB.
#
# O peso NAO vai para o git (regra da disciplina: arquivo grande fica em
# link publico). Este script e a fonte versionada do artefato.
set -e

RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$RAIZ/models"
ARQ="$DEST/yolov8n.onnx"
mkdir -p "$DEST"

if [ -f "$ARQ" ] && [ "$(stat -c%s "$ARQ")" -gt 5000000 ]; then
  echo "[modelo] ja existe: $ARQ ($(du -h "$ARQ" | cut -f1))"
  exit 0
fi

FONTES=(
  "https://raw.githubusercontent.com/Hyuto/yolov8-onnxruntime-web/master/public/model/yolov8n.onnx"
  "https://huggingface.co/Xenova/yolov8n/resolve/main/onnx/model.onnx"
)

for url in "${FONTES[@]}"; do
  echo "[modelo] tentando $url"
  if curl -fsSL --max-time 300 -o "$ARQ.tmp" "$url"; then
    tam=$(stat -c%s "$ARQ.tmp" 2>/dev/null || echo 0)
    if [ "$tam" -gt 5000000 ]; then
      mv "$ARQ.tmp" "$ARQ"
      echo "[modelo] OK: $ARQ ($(du -h "$ARQ" | cut -f1))"
      python3 - "$ARQ" <<'PY'
import sys, cv2, numpy as np
net = cv2.dnn.readNetFromONNX(sys.argv[1])
net.setInput(cv2.dnn.blobFromImage(np.zeros((640,640,3),np.uint8),
                                   1/255.0,(640,640),swapRB=True,crop=False))
print("[modelo] verificado | saida:", net.forward().shape)
PY
      exit 0
    fi
  fi
  rm -f "$ARQ.tmp"
done

echo "[modelo] AVISO: nenhuma fonte respondeu."
echo "[modelo] O sistema continua funcionando: o deteccao_node degrada"
echo "[modelo] para segmentacao HSV automaticamente. Para habilitar o"
echo "[modelo] YOLO depois, coloque um yolov8n.onnx em $DEST/"
exit 0
