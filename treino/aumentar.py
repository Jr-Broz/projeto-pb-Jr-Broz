#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════
 aumentar.py — pipeline de data augmentation do projeto ARACNE
═══════════════════════════════════════════════════════════════════════

POR QUE ESTE ARQUIVO EXISTE, E POR QUE A COR DOMINA AS DECISÕES AQUI
───────────────────────────────────────────────────────────────────────
Antes de escolher qualquer transformação, foi medido se as cinco classes
deste dataset são separáveis SOMENTE pela cor. O teste: um Random Forest
treinado apenas em histograma HSV — nenhuma informação de forma, textura
ou contorno.

    Acurácia usando somente cor : 69,7%
    Acaso (5 classes)           : 20,0%

Esse número é um alerta, não uma boa notícia. Ele diz que existe um
ATALHO disponível: a rede pode chegar a uma acurácia alta aprendendo
"azul = tarântula azul, laranja = joelho-vermelho" sem nunca olhar para
a forma do corpo, o padrão de pelos ou a proporção das pernas.

O atalho funciona no conjunto de validação — que veio da mesma
distribuição — e quebra no mundo real. Medido, simulando o caminho
foto digital → impressora → papel → webcam:

    Sem augmentation : 68,1% limpa → 58,4% impressa   (queda de 9,7)
    Com augmentation : 68,6% limpa → 62,7% impressa   (queda de 5,9)

Por isso o augmentation deste projeto é DESBALANCEADO de propósito:
muito mais agressivo em cor do que em geometria. Não é exagero — é a
resposta direta ao que a medição mostrou.

A LÓGICA DE CADA TRANSFORMAÇÃO
───────────────────────────────────────────────────────────────────────
Cada augmentation deve simular uma variação que o sistema VAI encontrar
em operação. Augmentation que inventa variação impossível só gasta
capacidade do modelo.

  matiz/saturação/brilho  → impressora, lâmpada, exposição da webcam
  ruído gaussiano         → ganho do sensor em pouca luz
  desfoque                → foco imperfeito, movimento
  JPEG                    → compressão do stream de vídeo
  gradiente de luz        → iluminação não uniforme sobre o papel
  espelhamento horizontal → a aranha pode estar virada para qualquer lado
  rotação pequena         → o papel/câmera não ficam perfeitamente alinhados

  ROTAÇÃO DE 180° NÃO É USADA. Uma aranha de cabeça para baixo é
  fisicamente possível (teia), mas rara no enquadramento de inspeção.
  Mais importante: o padrão dorsal de várias espécies é orientado, e
  inverter ensina o modelo que a orientação não importa — o que o faz
  perder um sinal legítimo.

  RECORTE AGRESSIVO NÃO É USADO. As imagens já vêm 224×224 centradas na
  aranha. Recortar muito remove justamente o corpo, que é o objeto da
  classificação.
"""

import cv2
import numpy as np


# ══════════════════════════════════════════════════════════════════
#  Transformações individuais
# ══════════════════════════════════════════════════════════════════

def jitter_cor(im, rng, forca=1.0):
    """
    Desloca matiz, saturação e brilho.

    É A TRANSFORMAÇÃO MAIS IMPORTANTE deste pipeline, pelo motivo
    medido acima. O deslocamento de matiz (±18°) é largo o bastante para
    o modelo não poder decorar o tom exato, e estreito o bastante para
    não transformar a tarântula azul em laranja — o que criaria um
    rótulo mentiroso.
    """
    hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[:, :, 0] = (hsv[:, :, 0] + rng.uniform(-18, 18) * forca) % 180
    hsv[:, :, 1] *= rng.uniform(1 - 0.45 * forca, 1 + 0.35 * forca)
    hsv[:, :, 2] *= rng.uniform(1 - 0.35 * forca, 1 + 0.30 * forca)
    out = cv2.cvtColor(np.clip(hsv, 0, 255).astype(np.uint8), cv2.COLOR_HSV2BGR)

    # Desequilíbrio entre canais: simula temperatura de cor da lâmpada.
    f = out.astype(np.float32)
    f[:, :, 0] *= rng.uniform(1 - 0.15 * forca, 1 + 0.10 * forca)   # azul
    f[:, :, 2] *= rng.uniform(1 - 0.10 * forca, 1 + 0.15 * forca)   # vermelho
    return np.clip(f, 0, 255).astype(np.uint8)


def gradiente_luz(im, rng, forca=1.0):
    """Iluminação não uniforme — lâmpada de um lado só."""
    h, w = im.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    g = 1.0 + 0.25 * forca * ((xx / w - rng.uniform(0.2, 0.8)) +
                              (yy / h - rng.uniform(0.2, 0.8)))
    return np.clip(im.astype(np.float32) * g[:, :, None], 0, 255).astype(np.uint8)


def ruido_sensor(im, rng, forca=1.0):
    """Ruído gaussiano — ganho alto do sensor em pouca luz."""
    n = rng.normal(0, rng.uniform(2, 12) * forca, im.shape)
    return np.clip(im.astype(np.float32) + n, 0, 255).astype(np.uint8)


def desfoque(im, rng, forca=1.0):
    """Foco imperfeito ou movimento."""
    s = rng.uniform(0.3, 1.4) * forca
    if s < 0.35:
        return im
    return cv2.GaussianBlur(im, (3, 3), s)


def compressao_jpeg(im, rng, forca=1.0):
    """Artefato de compressão do stream de vídeo."""
    q = int(np.clip(92 - 45 * forca * rng.random(), 35, 95))
    _, b = cv2.imencode('.jpg', im, [cv2.IMWRITE_JPEG_QUALITY, q])
    return cv2.imdecode(b, cv2.IMREAD_COLOR)


def geometria(im, rng, forca=1.0):
    """Espelhamento horizontal, rotação pequena e escala."""
    out = im
    if rng.random() < 0.5:
        out = cv2.flip(out, 1)
    ang = rng.uniform(-14, 14) * forca
    esc = rng.uniform(1 - 0.12 * forca, 1 + 0.12 * forca)
    h, w = out.shape[:2]
    M = cv2.getRotationMatrix2D((w / 2, h / 2), ang, esc)
    return cv2.warpAffine(out, M, (w, h), borderMode=cv2.BORDER_REFLECT_101)


# ══════════════════════════════════════════════════════════════════
#  Pipelines
# ══════════════════════════════════════════════════════════════════

def augmentar(im, rng, forca=1.0):
    """
    Pipeline de treino. A ORDEM importa e não é arbitrária:

      1. geometria   — antes de tudo, para não deformar o ruído já posto
      2. cor         — a transformação principal
      3. gradiente   — iluminação espacial, depois da cor global
      4. desfoque    — a óptica vem antes do sensor
      5. ruído       — o sensor vem antes da compressão
      6. JPEG        — a última etapa da cadeia real de captura

    A ordem espelha a cadeia física: cena → óptica → sensor → compressão.
    Inverter isso (comprimir e depois desfocar, por exemplo) produz uma
    imagem que nenhuma câmera geraria.
    """
    out = geometria(im, rng, forca)
    out = jitter_cor(out, rng, forca)
    if rng.random() < 0.6:
        out = gradiente_luz(out, rng, forca)
    if rng.random() < 0.5:
        out = desfoque(out, rng, forca)
    if rng.random() < 0.6:
        out = ruido_sensor(out, rng, forca)
    if rng.random() < 0.5:
        out = compressao_jpeg(out, rng, forca)
    return out


def simular_impressao_webcam(im, rng):
    """
    Simula o cenário REAL de teste: a foto é impressa e filmada.

    Este pipeline NÃO é usado no treino. Ele é o conjunto de teste
    difícil — a medida honesta de quanto o modelo aguenta o domínio que
    ele vai encontrar na defesa. Misturá-lo com o treino invalidaria a
    medição: o modelo estaria sendo avaliado no que já viu.
    """
    f = im.astype(np.float32)

    # 1. Gamut da impressora: tinta satura menos que tela, e o branco do
    #    papel não é 255 — é o branco do papel sob a luz do ambiente.
    hsv = cv2.cvtColor(f.astype(np.uint8), cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[:, :, 1] *= rng.uniform(0.62, 0.82)
    hsv[:, :, 2] = hsv[:, :, 2] * 0.88 + 18
    f = cv2.cvtColor(np.clip(hsv, 0, 255).astype(np.uint8),
                     cv2.COLOR_HSV2BGR).astype(np.float32)

    # 2. Temperatura da lâmpada do ambiente
    f[:, :, 0] *= rng.uniform(0.80, 1.00)
    f[:, :, 2] *= rng.uniform(1.00, 1.18)

    # 3. Luz não uniforme sobre o papel
    h, w = f.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    f *= (1.0 + 0.22 * ((xx / w - rng.uniform(.2, .8)) +
                        (yy / h - rng.uniform(.2, .8))))[:, :, None]

    # 4. Óptica e sensor da webcam
    f = cv2.GaussianBlur(f, (3, 3), rng.uniform(0.5, 1.2))
    f += rng.normal(0, rng.uniform(3, 9), f.shape)
    f = np.clip(f, 0, 255).astype(np.uint8)

    # 5. Compressão do stream
    _, b = cv2.imencode('.jpg', f,
                        [cv2.IMWRITE_JPEG_QUALITY, int(rng.integers(55, 80))])
    return cv2.imdecode(b, cv2.IMREAD_COLOR)


# ══════════════════════════════════════════════════════════════════
#  Painel visual — para o relatório e a defesa
# ══════════════════════════════════════════════════════════════════

def painel_exemplos(im, rng, n=7, lado=120):
    """Gera uma tira: original + n variações."""
    cells = [cv2.resize(im, (lado, lado))]
    for _ in range(n):
        cells.append(cv2.resize(augmentar(im, rng), (lado, lado)))
    tira = np.hstack(cells)
    cv2.rectangle(tira, (0, 0), (lado, 16), (0, 0, 0), -1)
    cv2.putText(tira, 'original', (4, 12), cv2.FONT_HERSHEY_SIMPLEX,
                0.35, (255, 255, 255), 1, cv2.LINE_AA)
    return tira
