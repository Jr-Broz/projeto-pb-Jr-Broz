#!/usr/bin/env python3
"""
exportar.py — reexporta um checkpoint .pth para ONNX.

EXISTE PORQUE O TREINO É CARO E A EXPORTAÇÃO É BARATA.

Se o `treinar.py` terminar o treino e quebrar na exportação (falta de
dependência, versão de ONNX, qualquer coisa), os pesos já estão em
`checkpoint.pth`. Este script pega esse arquivo e produz o .onnx em
segundos, sem retreinar nada.

    pip install onnx onnxscript
    python3 exportar.py --checkpoint modelo/checkpoint.pth

Também serve para reexportar com outro opset, se um dia o OpenCV da VM
mudar de versão:

    python3 exportar.py --checkpoint modelo/checkpoint.pth --opset 11
"""

import argparse
import json
import os
import sys

import numpy as np
import torch
import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from treinar import construir_modelo   # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--checkpoint', required=True)
    ap.add_argument('--saida', default='',
                    help='caminho do .onnx; padrão = ao lado do checkpoint')
    ap.add_argument('--opset', type=int, default=12)
    args = ap.parse_args()

    if not os.path.isfile(args.checkpoint):
        sys.exit(f'checkpoint não encontrado: {args.checkpoint}')

    ck = torch.load(args.checkpoint, map_location='cpu', weights_only=False)
    classes = ck['classes']
    arq = ck.get('arquitetura', 'mobilenet_v3_small')
    print(f'checkpoint: {arq} | {len(classes)} classes')
    for c in classes:
        print(f'  - {c}')

    modelo, _ = construir_modelo(len(classes), arq)
    modelo.load_state_dict(ck['state_dict'])
    modelo.eval()

    saida = args.saida or os.path.join(
        os.path.dirname(args.checkpoint), 'classificador_aranhas.onnx')

    exemplo = torch.randn(1, 3, 224, 224)
    kwargs = dict(input_names=['entrada'], output_names=['logits'],
                  dynamic_axes={'entrada': {0: 'lote'},
                                'logits': {0: 'lote'}},
                  opset_version=args.opset)
    try:
        torch.onnx.export(modelo, exemplo, saida, dynamo=False, **kwargs)
    except TypeError:
        torch.onnx.export(modelo, exemplo, saida, **kwargs)

    # A mesma verificação do treinar.py: o teste que importa é se o
    # OpenCV lê, não se o PyTorch escreveu.
    rede = cv2.dnn.readNetFromONNX(saida)
    rede.setInput(cv2.dnn.blobFromImage(
        np.zeros((224, 224, 3), np.uint8), 1 / 255.0, (224, 224)))
    forma = rede.forward().shape

    print(f'\nONNX: {saida} ({os.path.getsize(saida)/1e6:.1f} MB)')
    print(f'verificação OpenCV DNN: OK, saída {forma}')

    # Mantém a lista de classes ao lado do modelo. O nó ROS precisa dela
    # para traduzir o índice do argmax em nome de espécie — e índice sem
    # a lista é um número sem significado.
    info = os.path.join(os.path.dirname(saida), 'classes.json')
    if not os.path.exists(info):
        with open(info, 'w') as f:
            json.dump({'classes': classes}, f, indent=2, ensure_ascii=False)
        print(f'classes salvas em {info}')


if __name__ == '__main__':
    main()
