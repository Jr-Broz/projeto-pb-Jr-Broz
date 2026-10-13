#!/usr/bin/env python3
"""
Rastreamento multi-alvo com filtro de Kalman de velocidade constante.

Por que filtro e nao so ligar os centroides: a saida de um detector
treme de frame a frame (a bbox oscila alguns pixels mesmo com o objeto
parado) e falha em frames isolados. Ligar os centroides crus produz uma
trilha serrilhada que nao corresponde ao movimento real.

O filtro de Kalman resolve os dois problemas de uma vez:
  - suaviza, porque pondera a medicao ruidosa contra a predicao do modelo;
  - preenche buracos, porque continua predizendo quando nao ha medicao.

Modelo de estado (4 dimensoes):   x = [cx, cy, vx, vy]
Modelo de observacao (2):         z = [cx, cy]

Nao depende de ROS nem de OpenCV — so numpy. Isso e proposital: da para
testar a matematica isoladamente, sem subir o grafo.
"""

import numpy as np


class FiltroKalman2D:
    """Kalman de velocidade constante para o centroide de um alvo."""

    def __init__(self, cx, cy, dt=1.0 / 15.0,
                 aceleracao_std=220.0, medicao_std=10.0):
        """
        Os dois parametros de sintonia tem significado fisico direto — e
        e por isso que sao expressos assim, e nao como numeros abstratos:

        aceleracao_std : o quanto o alvo consegue mudar de velocidade,
                         em px/s^2. Maior = filtro mais reativo e mais
                         tremido. Menor = mais liso e mais atrasado.
        medicao_std    : o quanto a bbox do detector treme, em pixels.
                         Maior = confia menos na medicao.

        A razao entre os dois e o que decide o ganho de Kalman. Sintonia
        errada aqui nao "piora um pouco": o filtro diverge e passa a
        ignorar as medicoes, arrastando a trilha para longe do alvo.
        """
        self.dt = float(dt)

        # Estado inicial: posicao medida, velocidade desconhecida (zero).
        self.x = np.array([[float(cx)], [float(cy)], [0.0], [0.0]])

        # F: como o estado evolui sozinho de um frame para o outro.
        #    posicao_nova = posicao + velocidade * dt
        self.F = np.array([
            [1.0, 0.0, self.dt, 0.0],
            [0.0, 1.0, 0.0, self.dt],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ])

        # H: o que conseguimos medir — so a posicao, nunca a velocidade.
        self.H = np.array([
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
        ])

        # R: variancia da medicao (desvio padrao ao quadrado).
        r = float(medicao_std) ** 2
        self.R = np.eye(2) * r

        # Q: modelo de ruido branco na aceleracao. q e a variancia da
        #    aceleracao; as potencias de dt vem da integracao dela ate
        #    posicao e velocidade.
        q = float(aceleracao_std) ** 2
        dt = self.dt
        self.Q = np.array([
            [q * dt**4 / 4, 0.0,           q * dt**3 / 2, 0.0],
            [0.0,           q * dt**4 / 4, 0.0,           q * dt**3 / 2],
            [q * dt**3 / 2, 0.0,           q * dt**2,     0.0],
            [0.0,           q * dt**3 / 2, 0.0,           q * dt**2],
        ])

        # P: incerteza inicial. Na posicao, igual a da medicao (foi dela
        #    que o estado veio). Na velocidade, alta — e chute puro.
        self.P = np.eye(4)
        self.P[0, 0] = r
        self.P[1, 1] = r
        self.P[2, 2] = 1000.0
        self.P[3, 3] = 1000.0

    def prever(self):
        """Avanca o estado um frame, sem medicao."""
        self.x = self.F @ self.x
        self.P = self.F @ self.P @ self.F.T + self.Q
        return float(self.x[0, 0]), float(self.x[1, 0])

    def corrigir(self, cx, cy):
        """Incorpora uma medicao nova."""
        z = np.array([[float(cx)], [float(cy)]])
        y = z - self.H @ self.x                      # inovacao
        S = self.H @ self.P @ self.H.T + self.R      # covariancia da inovacao
        K = self.P @ self.H.T @ np.linalg.inv(S)     # ganho de Kalman
        self.x = self.x + K @ y
        self.P = (np.eye(4) - K @ self.H) @ self.P
        return float(self.x[0, 0]), float(self.x[1, 0])

    @property
    def posicao(self):
        return float(self.x[0, 0]), float(self.x[1, 0])

    @property
    def velocidade(self):
        return float(self.x[2, 0]), float(self.x[3, 0])

    @property
    def rapidez(self):
        vx, vy = self.velocidade
        return float(np.hypot(vx, vy))


class Trilha:
    """Um alvo rastreado ao longo do tempo."""

    def __init__(self, id_trilha, cx, cy, classe, confianca, dt,
                 max_trilha=48, aceleracao_std=220.0, medicao_std=10.0):
        self.id = id_trilha
        self.filtro = FiltroKalman2D(cx, cy, dt=dt,
                                     aceleracao_std=aceleracao_std,
                                     medicao_std=medicao_std)
        self.classe = classe
        self.confianca = confianca
        self.historico = [(int(cx), int(cy))]
        self.max_trilha = max_trilha
        self.frames_sem_medicao = 0
        self.frames_vivo = 1
        self.ultima_bbox = None

    def prever(self):
        cx, cy = self.filtro.prever()
        self.frames_sem_medicao += 1
        return cx, cy

    def atualizar(self, cx, cy, classe, confianca, bbox):
        fx, fy = self.filtro.corrigir(cx, cy)
        self.classe = classe
        self.confianca = confianca
        self.ultima_bbox = bbox
        self.frames_sem_medicao = 0
        self.frames_vivo += 1
        self.historico.append((int(round(fx)), int(round(fy))))
        if len(self.historico) > self.max_trilha:
            self.historico = self.historico[-self.max_trilha:]
        return fx, fy

    def registrar_predicao(self):
        """Guarda o ponto predito na trilha mesmo sem medicao (oclusao)."""
        fx, fy = self.filtro.posicao
        self.historico.append((int(round(fx)), int(round(fy))))
        if len(self.historico) > self.max_trilha:
            self.historico = self.historico[-self.max_trilha:]


class RastreadorMultiAlvo:
    """
    Associa deteccoes a trilhas por distancia do centroide e mantem o
    filtro de cada alvo.

    A associacao e guloso-por-distancia (o par mais proximo primeiro).
    Para poucos alvos, como e o caso aqui, isso se comporta igual ao
    algoritmo hungaro e e muito mais simples de explicar na defesa.
    """

    def __init__(self, dist_max=90.0, max_sumido=12, dt=1.0 / 15.0,
                 max_trilha=48, min_frames_para_confirmar=2,
                 aceleracao_std=400.0, medicao_std=10.0,
                 limiar_nascimento=0.45, limiar_manutencao=0.25):
        """
        HISTERESE DE LIMIAR — o mecanismo de robustez deste rastreador.

        Dois limiares em vez de um:
          limiar_nascimento : confianca para CRIAR uma trilha nova
          limiar_manutencao : confianca para MANTER uma ja existente

        E a mesma ideia do detector de bordas de Canny, onde um pixel
        fraco so vira borda se estiver ligado a um pixel forte. Aqui:
        uma deteccao fraca so e aceita se estiver ligada, no espaco e no
        tempo, a uma deteccao que ja foi forte.

        Isso importa porque a confianca oscila com a cena: o alvo entra
        na sombra, gira, e cai de 0,60 para 0,30 sem ter ido a lugar
        nenhum. Com limiar unico em 0,45 a trilha morre e renasce com id
        novo — e a contagem de individuos infla. Com histerese, quem ja
        provou que existe continua existindo com evidencia menor.

        O custo e assimetrico, e e por isso que o mecanismo e seguro:
        aceitar uma deteccao fraca PERTO de uma trilha confirmada e
        barato; aceitar uma deteccao fraca no meio do nada seria ruido
        virando alvo — e e exatamente isso que o limiar de nascimento
        impede.
        """
        self.dist_max = float(dist_max)
        self.max_sumido = int(max_sumido)
        self.dt = float(dt)
        self.max_trilha = int(max_trilha)
        self.min_frames = int(min_frames_para_confirmar)
        self.aceleracao_std = float(aceleracao_std)
        self.medicao_std = float(medicao_std)
        self.limiar_nascimento = float(limiar_nascimento)
        self.limiar_manutencao = float(limiar_manutencao)
        self.trilhas = {}
        self._proximo_id = 1
        # Contadores para o relatorio: quantas deteccoes fracas a
        # histerese resgatou, e quantas ela corretamente descartou.
        self.n_resgatadas = 0
        self.n_rejeitadas = 0

    def set_max_trilha(self, n):
        self.max_trilha = int(n)
        for t in self.trilhas.values():
            t.max_trilha = self.max_trilha
            if len(t.historico) > self.max_trilha:
                t.historico = t.historico[-self.max_trilha:]

    def atualizar(self, deteccoes):
        """
        deteccoes: lista de dicts com chaves
            classe, confianca, x, y, w, h

        Retorna a lista de dicts enriquecida com
            id_rastreio, cx_suavizado, cy_suavizado, velocidade_px_s
        """
        # 1. Toda trilha prediz onde deveria estar agora.
        for t in self.trilhas.values():
            t.prever()

        # 2. Monta todos os pares (trilha, deteccao) viaveis, por distancia.
        centros = []
        for i, d in enumerate(deteccoes):
            cx = d['x'] + d['w'] / 2.0
            cy = d['y'] + d['h'] / 2.0
            centros.append((cx, cy))

        pares = []
        for tid, t in self.trilhas.items():
            tx, ty = t.filtro.posicao
            # O portao de associacao cresce enquanto o alvo esta sumido:
            # quanto mais tempo sem medicao, mais longe ele pode estar da
            # predicao. Sem isso, uma oclusao longa faz o alvo reaparecer
            # fora do raio e ganhar um id novo — trilha quebrada em duas.
            portao = self.dist_max * (1.0 + 0.6 * t.frames_sem_medicao)
            for i, (cx, cy) in enumerate(centros):
                dist = float(np.hypot(tx - cx, ty - cy))
                if dist <= portao:
                    pares.append((dist, tid, i))
        pares.sort(key=lambda p: p[0])

        # 3. Associacao gulosa: cada trilha e cada deteccao entram uma vez.
        trilhas_usadas = set()
        det_usadas = set()
        associacao = {}
        for dist, tid, i in pares:
            if tid in trilhas_usadas or i in det_usadas:
                continue
            trilhas_usadas.add(tid)
            det_usadas.add(i)
            associacao[i] = tid

        # 4. Atualiza as trilhas associadas — aplicando a HISTERESE.
        saida = []
        for i, d in enumerate(deteccoes):
            cx, cy = centros[i]
            bbox = (d['x'], d['y'], d['w'], d['h'])
            conf = float(d['confianca'])

            if i in associacao:
                # Deteccao ligada a uma trilha existente: basta o limiar
                # de manutencao, que e o mais permissivo.
                if conf < self.limiar_manutencao:
                    self.n_rejeitadas += 1
                    trilhas_usadas.discard(associacao[i])
                    continue
                if conf < self.limiar_nascimento:
                    # Fraca demais para nascer, forte o bastante para
                    # continuar: e exatamente o caso que a histerese
                    # existe para resgatar.
                    self.n_resgatadas += 1
                t = self.trilhas[associacao[i]]
                fx, fy = t.atualizar(cx, cy, d['classe'], conf, bbox)
            else:
                # Sem trilha por perto: so nasce com evidencia forte.
                if conf < self.limiar_nascimento:
                    self.n_rejeitadas += 1
                    continue
                tid = self._proximo_id
                self._proximo_id += 1
                t = Trilha(tid, cx, cy, d['classe'], conf,
                           self.dt, self.max_trilha,
                           self.aceleracao_std, self.medicao_std)
                t.ultima_bbox = bbox
                self.trilhas[tid] = t
                trilhas_usadas.add(tid)   # nasceu com medicao: nao e oclusao
                fx, fy = cx, cy

            item = dict(d)
            item['id_rastreio'] = t.id
            item['cx_suavizado'] = int(round(fx))
            item['cy_suavizado'] = int(round(fy))
            # O estado do filtro ja guarda a velocidade em px/s (a matriz
            # F usa dt na transicao), entao aqui NAO se divide por dt de
            # novo — isso inflaria o valor pelo fator 1/dt.
            item['velocidade_px_s'] = t.filtro.rapidez
            saida.append(item)

        # 5. Trilhas sem medicao neste frame: registram a predicao (oclusao)
        #    e sao descartadas se sumirem por tempo demais.
        mortas = []
        for tid, t in self.trilhas.items():
            if tid not in trilhas_usadas:
                if t.frames_sem_medicao <= self.max_sumido:
                    t.registrar_predicao()
                else:
                    mortas.append(tid)
        for tid in mortas:
            del self.trilhas[tid]

        return saida

    def trilhas_para_desenhar(self):
        """[(id, classe, [(x,y), ...]), ...] das trilhas confirmadas."""
        out = []
        for tid, t in self.trilhas.items():
            if t.frames_vivo >= self.min_frames and len(t.historico) >= 2:
                out.append((tid, t.classe, list(t.historico)))
        return out

    @property
    def ids_vistos(self):
        return self._proximo_id - 1
