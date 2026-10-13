#!/usr/bin/env python3
"""
Desenho do frame de saida: bounding box, rotulo e trilha de rastreamento.

Separado dos nos de proposito: e codigo puro de OpenCV, sem ROS, entao
da para testar e ajustar a aparencia rodando um script comum, sem subir
o grafo inteiro.
"""

import cv2
import numpy as np

# Paleta estavel por id de trilha — o mesmo alvo mantem a mesma cor
# enquanto existir, o que torna a trilha legivel quando ha varios alvos.
PALETA = [
    (66, 135, 245), (76, 201, 122), (245, 176, 66), (200, 98, 220),
    (86, 214, 214), (240, 120, 150), (150, 200, 80), (120, 140, 250),
]


def cor_da_trilha(id_trilha):
    return PALETA[int(id_trilha) % len(PALETA)]


def desenhar_trilha(img, pontos, cor, espessura_max=4):
    """
    Desenha a trilha com espessura e opacidade crescentes: o passado
    aparece fino e apagado, o presente grosso e solido. Isso comunica a
    direcao do movimento sem precisar de seta.
    """
    if len(pontos) < 2:
        return
    n = len(pontos)
    overlay = img.copy()
    for i in range(1, n):
        frac = i / float(n - 1)          # 0 = mais antigo, 1 = mais recente
        esp = max(1, int(round(espessura_max * frac)))
        cv2.line(overlay, pontos[i - 1], pontos[i], cor, esp, cv2.LINE_AA)
    cv2.addWeighted(overlay, 0.85, img, 0.15, 0, img)

    # Marca o ponto atual
    cv2.circle(img, pontos[-1], 4, cor, -1, cv2.LINE_AA)
    cv2.circle(img, pontos[-1], 4, (255, 255, 255), 1, cv2.LINE_AA)


def desenhar_caixa(img, det, cor):
    x, y, w, h = det['x'], det['y'], det['w'], det['h']
    cv2.rectangle(img, (x, y), (x + w, y + h), cor, 2, cv2.LINE_AA)

    rotulo = f"#{det.get('id_rastreio', -1)} {det['classe']} {det['confianca']:.2f}"
    (tw, th), base = cv2.getTextSize(rotulo, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)

    # Se a caixa encosta no topo, o rotulo vai para dentro dela.
    ty = y - 6 if y - th - 8 >= 0 else y + th + 8
    ry = ty - th - 4
    cv2.rectangle(img, (x, ry), (x + tw + 8, ty + base - 2), cor, -1)
    cv2.putText(img, rotulo, (x + 4, ty - 2),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (20, 20, 20), 1, cv2.LINE_AA)


def texto_com_contorno(img, texto, org, escala=0.6, cor=(255, 255, 255)):
    cv2.putText(img, texto, org, cv2.FONT_HERSHEY_SIMPLEX, escala,
                (0, 0, 0), 3, cv2.LINE_AA)
    cv2.putText(img, texto, org, cv2.FONT_HERSHEY_SIMPLEX, escala,
                cor, 1, cv2.LINE_AA)


def anotar(frame, deteccoes, trilhas, info=None, desenhar_trilhas=True):
    """
    frame      : imagem BGR (nao e modificada; devolve uma copia)
    deteccoes  : lista de dicts ja enriquecida pelo rastreador
    trilhas    : lista de (id, classe, [(x,y), ...])
    info       : dict opcional com modelo, limiar, fps, ms, estado
    """
    img = frame.copy()

    if desenhar_trilhas:
        for tid, _classe, pontos in trilhas:
            desenhar_trilha(img, pontos, cor_da_trilha(tid))

    for d in deteccoes:
        desenhar_caixa(img, d, cor_da_trilha(d.get('id_rastreio', 0)))

    if info:
        problemas = info.get('problemas') or []
        q = info.get('qualidade', -1.0)
        alt_faixa = 76 if (problemas or info.get('preproc')) else 54

        # Faixa escura no topo para o texto ficar legivel sobre qualquer cena
        faixa = img.copy()
        cv2.rectangle(faixa, (0, 0), (img.shape[1], alt_faixa), (0, 0, 0), -1)
        cv2.addWeighted(faixa, 0.45, img, 0.55, 0, img)

        # Escala a fonte com a largura do frame: em 640 px o texto que
        # cabia em 1280 sai cortado pela borda.
        esc = float(np.clip(img.shape[1] / 1100.0, 0.42, 0.62))

        l1 = (f"ARACNE | {info.get('modelo', '?')} | "
              f"alvos={len(deteccoes)} | trilhas={len(trilhas)}")
        l2 = (f"conf {info.get('limiar', 0):.2f}/{info.get('limiar_manut', 0):.2f} | "
              f"{info.get('ms', 0):.0f} ms | {info.get('fps', 0):.1f} fps")
        if q >= 0:
            l2 += f" | q {q:.2f}"
        if info.get('estado'):
            l2 += f" | {info['estado']}"

        texto_com_contorno(img, l1, (10, 21), esc)
        texto_com_contorno(img, l2, (10, 43), esc * 0.9, (200, 230, 200))

        # Terceira linha so aparece quando ha algo a dizer. Alerta que
        # esta sempre na tela deixa de ser alerta.
        if problemas or info.get('preproc'):
            partes = []
            if problemas:
                partes.append('IMAGEM: ' + ', '.join(problemas))
            if info.get('preproc'):
                partes.append('tratada: ' + info['preproc'])
            cor = (90, 180, 255) if problemas else (180, 220, 180)
            texto_com_contorno(img, ' | '.join(partes), (10, 65), 0.48, cor)

    return img
