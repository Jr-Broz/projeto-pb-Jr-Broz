#!/usr/bin/env python3
"""
Detector YOLO sobre OpenCV DNN, com degradacao para segmentacao HSV.

POR QUE OpenCV DNN E NAO ULTRALYTICS
------------------------------------
O caminho usual (`pip install ultralytics`) arrasta o PyTorch junto: 2 a
3 GB de download e instalacao. A VM deste projeto tem espaco apertado, e
a inferencia roda em CPU de qualquer forma — o PyTorch nao traria ganho
nenhum aqui.

O OpenCV ja esta instalado e ja tem o modulo `dnn`, que le ONNX. O peso
YOLOv8n em ONNX tem cerca de 12 MB. Mesma arquitetura, mesmos pesos,
mesma saida — so sem a dependencia gigante. E YOLO de verdade.

MODELO AGNOSTICO
----------------
O caminho do modelo vem do YAML, nao do codigo. No TP2 o peso e o
YOLOv8n pre-treinado em COCO; no TP4, quando o classificador de especies
estiver treinado, trocar para os pesos proprios e alterar uma linha de
configuracao — nao mexer neste arquivo.

DEGRADAR, NAO QUEBRAR
---------------------
Sem o arquivo do modelo, o detector cai para a segmentacao HSV do TP1 e
continua publicando deteccoes com a mesma interface. O grafo fica de pe,
a acao continua executavel e a demo nao morre. E o mesmo padrao do
`camera_node`.
"""

import os
import time

import cv2
import numpy as np


# Classes do COCO, na ordem que o YOLOv8 pre-treinado usa.
CLASSES_COCO = [
    'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train',
    'truck', 'boat', 'traffic light', 'fire hydrant', 'stop sign',
    'parking meter', 'bench', 'bird', 'cat', 'dog', 'horse', 'sheep', 'cow',
    'elephant', 'bear', 'zebra', 'giraffe', 'backpack', 'umbrella', 'handbag',
    'tie', 'suitcase', 'frisbee', 'skis', 'snowboard', 'sports ball', 'kite',
    'baseball bat', 'baseball glove', 'skateboard', 'surfboard',
    'tennis racket', 'bottle', 'wine glass', 'cup', 'fork', 'knife', 'spoon',
    'bowl', 'banana', 'apple', 'sandwich', 'orange', 'broccoli', 'carrot',
    'hot dog', 'pizza', 'donut', 'cake', 'chair', 'couch', 'potted plant',
    'bed', 'dining table', 'toilet', 'tv', 'laptop', 'mouse', 'remote',
    'keyboard', 'cell phone', 'microwave', 'oven', 'toaster', 'sink',
    'refrigerator', 'book', 'clock', 'vase', 'scissors', 'teddy bear',
    'hair drier', 'toothbrush',
]


class DetectorYOLO:
    """Inferencia YOLOv8 em ONNX via OpenCV DNN."""

    def __init__(self, caminho_modelo, tamanho_entrada=640,
                 limiar_confianca=0.45, limiar_nms=0.45,
                 classes=None, classes_interesse=None, logger=None):
        self.caminho = caminho_modelo
        self.tam = int(tamanho_entrada)
        self.conf = float(limiar_confianca)
        self.nms = float(limiar_nms)
        self.classes = classes if classes else CLASSES_COCO
        self.classes_interesse = set(classes_interesse or [])
        self.log = logger
        self.net = None
        self.nome_modelo = 'hsv-fallback'
        self.disponivel = False
        self._carregar()

    def _msg(self, nivel, texto):
        if self.log is None:
            print(f'[{nivel}] {texto}')
        else:
            getattr(self.log, nivel)(texto)

    def _carregar(self):
        if not self.caminho or not os.path.isfile(self.caminho):
            self._msg('warn',
                      f'modelo nao encontrado em "{self.caminho}" — '
                      'degradando para segmentacao HSV. '
                      'Rode scripts/baixar_modelo.sh para habilitar o YOLO.')
            return
        try:
            self.net = cv2.dnn.readNetFromONNX(self.caminho)
            self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
            self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
            self.nome_modelo = os.path.basename(self.caminho)
            self.disponivel = True
            self._msg('info', f'YOLO carregado: {self.nome_modelo} '
                              f'(entrada {self.tam}x{self.tam}, CPU)')
        except cv2.error as e:
            self._msg('warn', f'falha ao carregar ONNX ({e}) — '
                              'degradando para segmentacao HSV')
            self.net = None

    # ------------------------------------------------------------------
    def detectar(self, frame):
        """Retorna (lista_de_deteccoes, tempo_ms)."""
        t0 = time.perf_counter()
        if self.disponivel:
            dets = self._detectar_yolo(frame)
        else:
            dets = self._detectar_hsv(frame)
        return dets, (time.perf_counter() - t0) * 1000.0

    # ------------------------------------------------------------------
    def _detectar_yolo(self, frame):
        alt, larg = frame.shape[:2]

        # Letterbox: redimensiona mantendo proporcao e preenche o resto.
        # Sem isso, objetos ficam distorcidos e a bbox volta errada.
        escala = min(self.tam / larg, self.tam / alt)
        nl, na = int(round(larg * escala)), int(round(alt * escala))
        pad_x, pad_y = (self.tam - nl) // 2, (self.tam - na) // 2

        canvas = np.full((self.tam, self.tam, 3), 114, dtype=np.uint8)
        canvas[pad_y:pad_y + na, pad_x:pad_x + nl] = cv2.resize(frame, (nl, na))

        blob = cv2.dnn.blobFromImage(canvas, 1 / 255.0, (self.tam, self.tam),
                                     swapRB=True, crop=False)
        self.net.setInput(blob)
        saida = self.net.forward()

        # YOLOv8 devolve [1, 4+num_classes, num_ancoras]. Transpor para
        # [num_ancoras, 4+num_classes] deixa uma linha por candidato.
        # A decisao e feita comparando com o numero esperado de canais,
        # e nao por "qual dimensao e maior": a heuristica de tamanho
        # falha silenciosamente em modelos com poucas ancoras, e o
        # sintoma e zero deteccoes sem nenhuma mensagem de erro.
        pred = np.squeeze(saida)
        if pred.ndim != 2:
            return []
        canais = 4 + len(self.classes)
        if pred.shape[0] == canais and pred.shape[1] != canais:
            pred = pred.T
        elif pred.shape[1] != canais and pred.shape[0] < pred.shape[1]:
            pred = pred.T

        caixas_xywh = pred[:, :4]
        scores_cls = pred[:, 4:]
        ids = np.argmax(scores_cls, axis=1)
        confs = scores_cls[np.arange(scores_cls.shape[0]), ids]

        manter = confs >= self.conf
        if not np.any(manter):
            return []
        caixas_xywh = caixas_xywh[manter]
        ids = ids[manter]
        confs = confs[manter]

        # cx,cy,w,h (na escala do canvas) -> x,y,w,h (na escala do frame)
        cx, cy, bw, bh = (caixas_xywh[:, 0], caixas_xywh[:, 1],
                          caixas_xywh[:, 2], caixas_xywh[:, 3])
        x = (cx - bw / 2 - pad_x) / escala
        y = (cy - bh / 2 - pad_y) / escala
        w = bw / escala
        h = bh / escala

        caixas = np.stack([x, y, w, h], axis=1)
        lista = [[int(round(v)) for v in b] for b in caixas]

        indices = cv2.dnn.NMSBoxes(lista, confs.astype(float).tolist(),
                                   self.conf, self.nms)
        if len(indices) == 0:
            return []
        indices = np.array(indices).flatten()

        dets = []
        for i in indices:
            cid = int(ids[i])
            nome = self.classes[cid] if cid < len(self.classes) else str(cid)
            if self.classes_interesse and nome not in self.classes_interesse:
                continue
            bx, by, bwv, bhv = lista[i]
            bx = max(0, min(bx, larg - 1))
            by = max(0, min(by, alt - 1))
            bwv = max(1, min(bwv, larg - bx))
            bhv = max(1, min(bhv, alt - by))
            dets.append({'classe': nome, 'confianca': float(confs[i]),
                         'x': bx, 'y': by, 'w': bwv, 'h': bhv})
        return dets

    # ------------------------------------------------------------------
    def _detectar_hsv(self, frame, area_minima=700):
        """Plano B: a mesma segmentacao do TP1, com a interface do detector."""
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        m1 = cv2.inRange(hsv, np.array([0, 110, 60]), np.array([10, 255, 255]))
        m2 = cv2.inRange(hsv, np.array([170, 110, 60]), np.array([180, 255, 255]))
        mask = cv2.bitwise_or(m1, m2)

        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k, iterations=1)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k, iterations=2)

        contornos, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL,
                                        cv2.CHAIN_APPROX_SIMPLE)
        dets = []
        for c in contornos:
            area = cv2.contourArea(c)
            if area < area_minima:
                continue
            x, y, w, h = cv2.boundingRect(c)
            # Confianca proxy: area normalizada. Nao e probabilidade de
            # modelo — e so uma medida de quao solida a mancha e. Isso
            # esta declarado no relatorio para nao passar por acuracia.
            conf = float(min(0.99, 0.45 + area / (frame.shape[0] * frame.shape[1]) * 6))
            dets.append({'classe': 'alvo-hsv', 'confianca': conf,
                         'x': int(x), 'y': int(y), 'w': int(w), 'h': int(h)})
        return dets

    def set_limiar(self, novo):
        self.conf = float(np.clip(novo, 0.01, 0.99))
        return self.conf
