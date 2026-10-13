#!/usr/bin/env python3
"""
Pre-processamento e avaliacao de qualidade de imagem.

POR QUE ISSO EXISTE
-------------------
A camera de um robo de inspecao nao opera em estudio. A imagem chega
subexposta em sombra, estourada contra a luz, com dominante de cor da
lampada, borrada por movimento e ruidosa em ganho alto. Um pipeline que
so funciona com imagem boa nao e um pipeline de percepcao — e uma demo.

Dois mecanismos independentes aqui:

1. NORMALIZACAO  — aproxima a imagem ruim da faixa em que o detector
                   foi treinado. CLAHE, balanco de branco e gama.

2. INSTRUMENTACAO — mede a qualidade da imagem e reporta. Um sistema que
                   SABE que nao esta enxergando vale mais que um que
                   devolve silencio. As metricas viram campo de
                   mensagem, nao print de depuracao.

UMA RESSALVA HONESTA
--------------------
Normalizar nao e universalmente bom. Um modelo aprendido ja viu variacao
de iluminacao no treino; pre-processar demais pode empurrar a imagem
para fora da distribuicao que ele conhece. Por isso tudo aqui e
parametrizavel e desligavel, e o relatorio traz a medicao com e sem —
nao a suposicao de que ajuda.
"""

import cv2
import numpy as np


# ══════════════════════════════════════════════════════════════════
#  Metricas de qualidade
# ══════════════════════════════════════════════════════════════════

def nitidez(frame):
    """
    Variancia do Laplaciano — metrica classica de foco.

    O Laplaciano realca bordas. Imagem nitida tem muitas bordas fortes,
    logo variancia alta. Imagem borrada tem bordas suaves, variancia
    baixa. Valores tipicos: < 40 muito borrada, 40-120 aceitavel,
    > 120 nitida. A escala depende da cena, entao o limiar e parametro.
    """
    cinza = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(cinza, cv2.CV_64F).var())


def brilho_contraste(frame):
    """Media e desvio padrao da luminancia (canal L do LAB)."""
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    L = lab[:, :, 0]
    return float(L.mean()), float(L.std())


def pixels_estourados(frame):
    """
    Fracao de pixels grudados em 0 ou 255.

    Pixel estourado perdeu a informacao: nenhum filtro recupera o que
    o sensor saturou. E o unico defeito desta lista que e irreversivel,
    e por isso vale medir separado.
    """
    cinza = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    total = cinza.size
    return float(((cinza <= 2) | (cinza >= 253)).sum()) / total


def dominante_cor(frame):
    """
    Quanto os canais BGR se afastam entre si.

    Sob a hipotese do mundo cinza (a media de uma cena variada tende ao
    cinza), desvio grande indica dominante de cor — lampada amarela,
    LED azulado, luz de sodio.
    """
    medias = frame.reshape(-1, 3).mean(axis=0)
    return float(medias.std() / (medias.mean() + 1e-6))


def avaliar(frame):
    """Devolve as metricas e um veredito legivel."""
    b, c = brilho_contraste(frame)
    n = nitidez(frame)
    e = pixels_estourados(frame)
    d = dominante_cor(frame)

    problemas = []
    if b < 55:
        problemas.append('subexposta')
    elif b > 200:
        problemas.append('superexposta')
    if c < 28:
        problemas.append('baixo contraste')
    if n < 40:
        problemas.append('desfocada')
    if e > 0.06:
        problemas.append('pixels estourados')
    if d > 0.16:
        problemas.append('dominante de cor')

    # Score 0-1: 1 = imagem limpa. Serve para o operador e para o
    # relatorio, nao para decidir nada sozinho.
    score = 1.0
    score *= np.clip(1.0 - abs(b - 128) / 128.0, 0.2, 1.0)
    score *= np.clip(c / 50.0, 0.2, 1.0)
    score *= np.clip(n / 120.0, 0.2, 1.0)
    score *= np.clip(1.0 - e * 4, 0.2, 1.0)

    return {
        'brilho': b,
        'contraste': c,
        'nitidez': n,
        'estourados': e,
        'dominante': d,
        'score': float(np.clip(score, 0.0, 1.0)),
        'problemas': problemas,
    }


# ══════════════════════════════════════════════════════════════════
#  Normalizacao
# ══════════════════════════════════════════════════════════════════

def clahe(frame, clip=2.5, grade=8):
    """
    Equalizacao adaptativa de histograma com limite de contraste.

    A equalizacao global classica pega o histograma da imagem inteira, o
    que arruina cenas de iluminacao mista: clareia a sombra e estoura a
    parte que ja estava clara. O CLAHE divide a imagem em blocos e
    equaliza cada um, com um teto de amplificacao que impede o ruido de
    virar textura.

    Aplicado so no canal L do LAB. Equalizar B, G e R separadamente
    desloca o matiz — e o matiz e justamente o que a segmentacao HSV e a
    identificacao de especie usam.
    """
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    op = cv2.createCLAHE(clipLimit=float(clip),
                         tileGridSize=(int(grade), int(grade)))
    lab[:, :, 0] = op.apply(lab[:, :, 0])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


def balanco_branco(frame, forca=1.0):
    """
    Balanco de branco pelo mundo cinza.

    Escala cada canal para que as tres medias se igualem. Corrige
    dominante de lampada. 'forca' interpola entre original (0) e
    correcao total (1) — correcao agressiva em cena legitimamente
    monocromatica (mato, parede) introduz cor que nao existe.
    """
    f = frame.astype(np.float32)
    medias = f.reshape(-1, 3).mean(axis=0)
    alvo = medias.mean()
    ganhos = np.clip(alvo / (medias + 1e-6), 0.5, 2.0)
    ganhos = 1.0 + (ganhos - 1.0) * float(forca)
    return np.clip(f * ganhos, 0, 255).astype(np.uint8)


def gama_adaptativa(frame, alvo=118.0, limite=(0.4, 2.5)):
    """
    Gama calculada a partir do brilho medido, nao fixa.

    gama = log(alvo/255) / log(medido/255)

    Imagem escura recebe gama < 1 e clareia; clara recebe gama > 1 e
    escurece. Tabela de consulta de 256 entradas: custo desprezivel.
    """
    cinza = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    medio = float(cinza.mean())
    if medio < 3 or medio > 252:
        return frame          # estourada dos dois lados: gama nao ajuda
    g = np.log(alvo / 255.0) / np.log(medio / 255.0)
    g = float(np.clip(g, limite[0], limite[1]))
    if abs(g - 1.0) < 0.05:
        return frame
    inv = 1.0 / g
    lut = np.array([((i / 255.0) ** inv) * 255 for i in range(256)],
                   dtype=np.uint8)
    return cv2.LUT(frame, lut)


def reduzir_ruido(frame, forca=5):
    """
    Filtro bilateral: suaviza area plana e preserva borda.

    Um blur gaussiano tiraria o ruido e a borda junto — e borda e
    exatamente o que o detector usa. O bilateral pondera pela diferenca
    de intensidade, entao nao atravessa contorno.
    """
    return cv2.bilateralFilter(frame, d=5,
                               sigmaColor=float(forca) * 12,
                               sigmaSpace=float(forca) * 2)


# ══════════════════════════════════════════════════════════════════
#  Pipeline
# ══════════════════════════════════════════════════════════════════

class PreProcessador:
    """
    Normalizacao condicional: cada etapa so roda se a metrica
    correspondente indicar que ela e necessaria.

    Aplicar tudo sempre e pior do que nao aplicar nada. CLAHE em imagem
    ja bem exposta amplifica ruido; balanco de branco em cena
    legitimamente monocromatica inventa cor. A decisao vem da medicao.
    """

    def __init__(self, ativo=True, modo='auto',
                 clahe_clip=2.5, clahe_grade=8,
                 wb_forca=0.8, ruido_forca=5,
                 limiar_escuro=75.0, limiar_claro=185.0,
                 limiar_contraste=32.0, limiar_dominante=0.12,
                 limiar_ruido_nitidez=25.0):
        self.ativo = bool(ativo)
        self.modo = modo                       # 'auto' | 'sempre' | 'off'
        self.clahe_clip = clahe_clip
        self.clahe_grade = clahe_grade
        self.wb_forca = wb_forca
        self.ruido_forca = ruido_forca
        self.lim_escuro = limiar_escuro
        self.lim_claro = limiar_claro
        self.lim_contraste = limiar_contraste
        self.lim_dominante = limiar_dominante
        self.lim_ruido = limiar_ruido_nitidez

    def processar(self, frame):
        """Retorna (frame_tratado, metricas, lista_de_etapas_aplicadas)."""
        m = avaliar(frame)

        if not self.ativo or self.modo == 'off':
            return frame, m, []

        img = frame
        etapas = []
        sempre = (self.modo == 'sempre')

        # 1. Gama primeiro: corrige o nivel global antes de mexer no local.
        if sempre or m['brilho'] < self.lim_escuro or m['brilho'] > self.lim_claro:
            img = gama_adaptativa(img)
            etapas.append('gama')

        # 2. CLAHE: recupera detalhe local em sombra e alta luz.
        if sempre or m['contraste'] < self.lim_contraste or 'subexposta' in m['problemas']:
            img = clahe(img, self.clahe_clip, self.clahe_grade)
            etapas.append('clahe')

        # 3. Balanco de branco: so quando ha dominante medida.
        if sempre or m['dominante'] > self.lim_dominante:
            img = balanco_branco(img, self.wb_forca)
            etapas.append('wb')

        # 4. Ruido por ultimo: os passos acima amplificam o que havia.
        #    Roda so quando a nitidez baixa sugere granulacao, porque o
        #    bilateral e a etapa mais cara do conjunto.
        if m['nitidez'] < self.lim_ruido and m['contraste'] > 20:
            img = reduzir_ruido(img, self.ruido_forca)
            etapas.append('ruido')

        return img, m, etapas


# ══════════════════════════════════════════════════════════════════
#  Degradacoes — para o experimento controlado do relatorio
# ══════════════════════════════════════════════════════════════════

def degradar(frame, tipo, intensidade=1.0):
    """
    Aplica uma degradacao conhecida. Existe para o experimento de
    robustez: sem uma degradacao controlada nao ha como medir ganho,
    so impressao.
    """
    f = frame.copy()

    if tipo == 'escuro':
        g = 1.0 + 2.2 * intensidade
        lut = np.array([((i / 255.0) ** g) * 255 for i in range(256)], np.uint8)
        return cv2.LUT(f, lut)

    if tipo == 'claro':
        g = 1.0 / (1.0 + 1.6 * intensidade)
        lut = np.array([((i / 255.0) ** g) * 255 for i in range(256)], np.uint8)
        return cv2.LUT(f, lut)

    if tipo == 'baixo_contraste':
        a = 1.0 - 0.68 * intensidade
        return np.clip(f.astype(np.float32) * a + 128 * (1 - a), 0, 255).astype(np.uint8)

    if tipo == 'ruido':
        n = np.random.normal(0, 26 * intensidade, f.shape)
        return np.clip(f.astype(np.float32) + n, 0, 255).astype(np.uint8)

    if tipo == 'blur':
        k = int(3 + 6 * intensidade) | 1
        return cv2.GaussianBlur(f, (k, k), 0)

    if tipo == 'dominante_amarela':
        f = f.astype(np.float32)
        f[:, :, 0] *= (1.0 - 0.45 * intensidade)   # tira azul
        f[:, :, 2] *= (1.0 + 0.16 * intensidade)   # reforca vermelho
        return np.clip(f, 0, 255).astype(np.uint8)

    if tipo == 'jpeg':
        q = int(np.clip(92 - 80 * intensidade, 5, 95))
        _, buf = cv2.imencode('.jpg', f, [cv2.IMWRITE_JPEG_QUALITY, q])
        return cv2.imdecode(buf, cv2.IMREAD_COLOR)

    raise ValueError(f'degradacao desconhecida: {tipo}')


DEGRADACOES = ['escuro', 'claro', 'baixo_contraste', 'ruido',
               'blur', 'dominante_amarela', 'jpeg']
