#!/usr/bin/env python3
"""
deteccao_node — o no de percepcao do TP2.

Consome  : /camera/image_raw            (sensor_msgs/Image)
Publica  : /aracne/deteccoes            (ListaDeteccoes)   <- regua leve
           /aracne/imagem_anotada       (Image)            <- bbox + trilha
Serve    : /aracne/configurar_deteccao  (ConfigurarDeteccao)

Todos os parametros sao declarados com descritor e aceitam alteracao em
tempo de execucao via `ros2 param set` — ver `_on_parametros`.

ROBUSTEZ — as tres camadas, e o que a medicao mostrou sobre cada uma
-------------------------------------------------------------------
1. HISTERESE DE LIMIAR (ligada por padrao).
   Dois limiares: um alto para criar trilha, um baixo para manter.
   Medido: com limiar unico alto, um alvo que entra na sombra gera 3
   ids; com limiar unico baixo, 14 ids (13 fantasmas de falso
   positivo); com histerese, 1 id e nenhum fantasma. E o mecanismo de
   robustez que efetivamente funciona neste pipeline.

2. RASTREAMENTO POR KALMAN (ligado por padrao).
   Sobrevive a 12 frames sem deteccao mantendo o id, e reduz o tremor
   da trilha em 54-61%.

3. PRE-PROCESSAMENTO (DESLIGADO por padrao — e proposital).
   Medido em 7 degradacoes x 2 intensidades: normalizar a imagem nunca
   melhorou o ponto de ruptura do YOLO, e em 'escuro' o piorou (o
   detector aguentava ate intensidade 2.2 sem tratamento, e so 1.2
   com). A razao: o YOLOv8 foi treinado com augmentation forte e ja viu
   essa variacao; normalizar empurra a imagem para fora da
   distribuicao que ele conhece.
   Fica disponivel e parametrizavel porque e util para o detector
   classico e para inspecao visual, mas o padrao e nao aplicar. Ligar
   por reflexo o que a medicao desaconselha seria o oposto de
   engenharia.
"""

import time

import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from rcl_interfaces.msg import (ParameterDescriptor, FloatingPointRange,
                                IntegerRange, SetParametersResult)
from sensor_msgs.msg import Image
from cv_bridge import CvBridge

from percepcao_aracnideos_interfaces.msg import (DeteccaoAracnideo,
                                                 ListaDeteccoes)
from percepcao_aracnideos_interfaces.srv import ConfigurarDeteccao

from percepcao_aracnideos.detector import DetectorYOLO
from percepcao_aracnideos.rastreador import RastreadorMultiAlvo
from percepcao_aracnideos.anotacao import anotar
from percepcao_aracnideos.preprocessamento import PreProcessador


def faixa_float(desc, minimo, maximo, passo=0.0):
    return ParameterDescriptor(
        description=desc,
        floating_point_range=[FloatingPointRange(
            from_value=float(minimo), to_value=float(maximo), step=float(passo))])


def faixa_int(desc, minimo, maximo, passo=1):
    return ParameterDescriptor(
        description=desc,
        integer_range=[IntegerRange(
            from_value=int(minimo), to_value=int(maximo), step=int(passo))])


class DeteccaoNode(Node):

    def __init__(self):
        super().__init__('deteccao_node')

        # ---------------- modelo e inferencia ----------------
        self.declare_parameter(
            'modelo_path', '',
            ParameterDescriptor(description='caminho do .onnx do YOLO; '
                                            'vazio = segmentacao HSV'))
        self.declare_parameter('tamanho_entrada', 640,
                               faixa_int('lado da entrada do YOLO', 320, 1280, 32))
        self.declare_parameter('limiar_nms', 0.45,
                               faixa_float('IoU da supressao nao-maxima', 0.1, 0.9))
        self.declare_parameter('frequencia_hz', 10.0,
                               faixa_float('taxa de inferencia', 1.0, 30.0))
        self.declare_parameter('classes_interesse', [''],
                               ParameterDescriptor(description='lista branca de '
                                                               'classes; vazia = todas'))

        # ---------------- histerese de limiar ----------------
        self.declare_parameter('limiar_confianca', 0.45,
                               faixa_float('confianca para CRIAR uma trilha nova '
                                           '(limiar de nascimento)', 0.01, 0.99))
        self.declare_parameter('limiar_manutencao', 0.25,
                               faixa_float('confianca para MANTER uma trilha '
                                           'existente (histerese)', 0.01, 0.99))

        # ---------------- rastreamento ----------------
        self.declare_parameter('desenhar_trilha', True,
                               ParameterDescriptor(description='desenhar a trilha'))
        self.declare_parameter('tamanho_trilha', 48,
                               faixa_int('pontos guardados por trilha', 2, 300))
        self.declare_parameter('rastreio_dist_max', 90.0,
                               faixa_float('raio de associacao em px', 10.0, 400.0))
        self.declare_parameter('rastreio_max_sumido', 12,
                               faixa_int('frames tolerados sem medicao', 0, 90))
        self.declare_parameter('kalman_aceleracao_std', 400.0,
                               faixa_float('aceleracao esperada px/s^2', 10.0, 3000.0))
        self.declare_parameter('kalman_medicao_std', 10.0,
                               faixa_float('tremor da bbox em px', 1.0, 100.0))

        # ---------------- pre-processamento ----------------
        self.declare_parameter('preproc_ativo', False,
                               ParameterDescriptor(
                                   description='normalizar a imagem antes de '
                                               'inferir. Padrao FALSE: a medicao '
                                               'mostrou que nao ajuda o YOLO'))
        self.declare_parameter('preproc_modo', 'auto',
                               ParameterDescriptor(description='auto | sempre | off'))
        self.declare_parameter('preproc_clahe_clip', 2.5,
                               faixa_float('teto de amplificacao do CLAHE', 1.0, 8.0))
        self.declare_parameter('preproc_wb_forca', 0.8,
                               faixa_float('forca do balanco de branco', 0.0, 1.0))
        self.declare_parameter('avaliar_qualidade', True,
                               ParameterDescriptor(
                                   description='medir e publicar a qualidade da '
                                               'imagem (barato, sempre util)'))

        p = self.get_parameter
        modelo = p('modelo_path').value
        freq = float(p('frequencia_hz').value)
        classes_int = [c for c in p('classes_interesse').value if c]
        nasc = float(p('limiar_confianca').value)
        manut = min(float(p('limiar_manutencao').value), nasc)

        # ---------------- componentes ----------------
        self.bridge = CvBridge()

        # O detector filtra no limiar de MANUTENCAO (o mais baixo) para
        # que as deteccoes fracas cheguem ao rastreador. E ele quem
        # decide, com os dois limiares, o que vira trilha.
        self.detector = DetectorYOLO(
            caminho_modelo=modelo,
            tamanho_entrada=int(p('tamanho_entrada').value),
            limiar_confianca=manut,
            limiar_nms=float(p('limiar_nms').value),
            classes_interesse=classes_int,
            logger=self.get_logger())

        self.rastreador = RastreadorMultiAlvo(
            dist_max=float(p('rastreio_dist_max').value),
            max_sumido=int(p('rastreio_max_sumido').value),
            dt=1.0 / max(freq, 1e-3),
            max_trilha=int(p('tamanho_trilha').value),
            aceleracao_std=float(p('kalman_aceleracao_std').value),
            medicao_std=float(p('kalman_medicao_std').value),
            limiar_nascimento=nasc,
            limiar_manutencao=manut)

        self.pre = PreProcessador(
            ativo=bool(p('preproc_ativo').value),
            modo=str(p('preproc_modo').value),
            clahe_clip=float(p('preproc_clahe_clip').value),
            wb_forca=float(p('preproc_wb_forca').value))

        # ---------------- interfaces ROS ----------------
        self.pub_det = self.create_publisher(ListaDeteccoes, '/aracne/deteccoes', 10)
        self.pub_img = self.create_publisher(Image, '/aracne/imagem_anotada', 10)
        self.create_subscription(Image, '/camera/image_raw', self._on_frame, 10)
        self.create_service(ConfigurarDeteccao, '/aracne/configurar_deteccao',
                            self._on_configurar)
        self.add_on_set_parameters_callback(self._on_parametros)

        # ---------------- estado ----------------
        self._intervalo = 1.0 / max(freq, 1e-3)
        self._t_ultimo = 0.0
        self._fps = 0.0
        self._ms = 0.0
        self.estado_externo = ''      # a acao escreve aqui para aparecer no HUD

        self.get_logger().info(
            f'deteccao_node pronto | modelo={self.detector.nome_modelo} | '
            f'{freq:.0f} Hz | histerese: nasce>={nasc:.2f} mantem>={manut:.2f} | '
            f'preproc={"on" if self.pre.ativo else "off"}')

    # ------------------------------------------------------------------
    def _on_frame(self, msg):
        """Guarda o frame mais recente; a inferencia roda no ritmo do no.

        Desacoplar recepcao de inferencia e o que impede a fila de crescer
        quando a camera publica mais rapido do que o YOLO consegue
        processar — sem isso, o no atrasa cada vez mais e nunca recupera.
        """
        agora = time.perf_counter()
        if agora - self._t_ultimo < self._intervalo:
            return
        self._t_ultimo = agora

        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')

        # --- qualidade e normalizacao ---
        metricas, etapas = {}, []
        entrada = frame
        if self.pre.ativo:
            entrada, metricas, etapas = self.pre.processar(frame)
        elif bool(self.get_parameter('avaliar_qualidade').value):
            from percepcao_aracnideos.preprocessamento import avaliar
            metricas = avaliar(frame)

        # --- deteccao e rastreamento ---
        res_antes = self.rastreador.n_resgatadas
        rej_antes = self.rastreador.n_rejeitadas
        deteccoes, ms = self.detector.detectar(entrada)
        deteccoes = self.rastreador.atualizar(deteccoes)

        self._ms = ms
        self._fps = 1000.0 / ms if ms > 0 else 0.0

        # ---- publica a lista estruturada ----
        lista = ListaDeteccoes()
        lista.header = msg.header
        lista.total = len(deteccoes)
        lista.limiar_confianca_usado = float(self.rastreador.limiar_nascimento)
        lista.modelo = self.detector.nome_modelo
        lista.tempo_inferencia_ms = float(ms)
        lista.qualidade_score = float(metricas.get('score', -1.0))
        lista.brilho_medio = float(metricas.get('brilho', -1.0))
        lista.contraste = float(metricas.get('contraste', -1.0))
        lista.nitidez = float(metricas.get('nitidez', -1.0))
        lista.problemas_imagem = ','.join(metricas.get('problemas', []))
        lista.preproc_aplicado = ','.join(etapas)
        lista.resgatadas_histerese = int(self.rastreador.n_resgatadas - res_antes)
        lista.rejeitadas_histerese = int(self.rastreador.n_rejeitadas - rej_antes)

        for d in deteccoes:
            m = DeteccaoAracnideo()
            m.classe = str(d['classe'])
            m.confianca = float(d['confianca'])
            m.x, m.y, m.w, m.h = int(d['x']), int(d['y']), int(d['w']), int(d['h'])
            m.id_rastreio = int(d.get('id_rastreio', -1))
            m.cx_suavizado = int(d.get('cx_suavizado', d['x'] + d['w'] // 2))
            m.cy_suavizado = int(d.get('cy_suavizado', d['y'] + d['h'] // 2))
            m.velocidade_px_s = float(d.get('velocidade_px_s', 0.0))
            lista.deteccoes.append(m)
        self.pub_det.publish(lista)

        # ---- publica o frame anotado ----
        # Anota sobre o frame ORIGINAL, nao sobre o tratado: o operador
        # precisa ver o que a camera viu, nao o que o filtro produziu.
        img = anotar(
            frame, deteccoes, self.rastreador.trilhas_para_desenhar(),
            info={'modelo': self.detector.nome_modelo,
                  'limiar': self.rastreador.limiar_nascimento,
                  'limiar_manut': self.rastreador.limiar_manutencao,
                  'ms': ms, 'fps': self._fps,
                  'qualidade': metricas.get('score', -1.0),
                  'problemas': metricas.get('problemas', []),
                  'preproc': ','.join(etapas),
                  'estado': self.estado_externo},
            desenhar_trilhas=bool(self.get_parameter('desenhar_trilha').value))
        out = self.bridge.cv2_to_imgmsg(img, encoding='bgr8')
        out.header = msg.header
        self.pub_img.publish(out)

    # ------------------------------------------------------------------
    def _on_configurar(self, req, resp):
        """Servico de controle. Valores sentinela significam 'nao alterar'."""
        mudou = []

        if req.limiar_confianca >= 0.0:
            novo = float(req.limiar_confianca)
            self.set_parameters([Parameter('limiar_confianca',
                                           Parameter.Type.DOUBLE, novo)])
            mudou.append(f'limiar_nascimento={novo:.2f}')

        if req.tamanho_trilha >= 0:
            n = max(2, min(300, int(req.tamanho_trilha)))
            self.set_parameters([Parameter('tamanho_trilha',
                                           Parameter.Type.INTEGER, n)])
            mudou.append(f'trilha={n}')

        if req.desenhar_trilha in (0, 1):
            v = bool(req.desenhar_trilha)
            self.set_parameters([Parameter('desenhar_trilha',
                                           Parameter.Type.BOOL, v)])
            mudou.append(f'desenhar={v}')

        resp.sucesso = True
        resp.mensagem = ('sem alteracao (todos os campos vieram com sentinela)'
                         if not mudou else 'aplicado: ' + ', '.join(mudou))
        resp.limiar_atual = float(self.rastreador.limiar_nascimento)
        resp.tamanho_trilha_atual = int(self.get_parameter('tamanho_trilha').value)
        resp.trilha_ativa = bool(self.get_parameter('desenhar_trilha').value)
        self.get_logger().info(f'/aracne/configurar_deteccao -> {resp.mensagem}')
        return resp

    # ------------------------------------------------------------------
    def _on_parametros(self, params):
        """
        Callback de alteracao dinamica. E aqui que `ros2 param set` vira
        efeito real: sem isso o valor muda na tabela de parametros e o no
        continua usando o antigo — falha silenciosa classica.
        """
        for p in params:
            try:
                if p.name == 'limiar_confianca':
                    v = float(p.value)
                    self.rastreador.limiar_nascimento = v
                    # O limiar de manutencao nunca pode passar o de
                    # nascimento: isso inverteria a histerese e faria a
                    # trilha exigir MAIS evidencia para continuar do que
                    # para nascer.
                    if self.rastreador.limiar_manutencao > v:
                        self.rastreador.limiar_manutencao = v
                        self.detector.set_limiar(v)
                        self.get_logger().warn(
                            f'limiar_manutencao reduzido para {v:.2f} '
                            'para preservar a histerese')
                elif p.name == 'limiar_manutencao':
                    v = min(float(p.value), self.rastreador.limiar_nascimento)
                    self.rastreador.limiar_manutencao = v
                    self.detector.set_limiar(v)
                elif p.name == 'limiar_nms':
                    self.detector.nms = float(p.value)
                elif p.name == 'tamanho_trilha':
                    self.rastreador.set_max_trilha(int(p.value))
                elif p.name == 'rastreio_dist_max':
                    self.rastreador.dist_max = float(p.value)
                elif p.name == 'rastreio_max_sumido':
                    self.rastreador.max_sumido = int(p.value)
                elif p.name == 'kalman_aceleracao_std':
                    self.rastreador.aceleracao_std = float(p.value)
                elif p.name == 'kalman_medicao_std':
                    self.rastreador.medicao_std = float(p.value)
                elif p.name == 'frequencia_hz':
                    f = max(float(p.value), 1e-3)
                    self._intervalo = 1.0 / f
                    self.rastreador.dt = 1.0 / f
                elif p.name == 'classes_interesse':
                    self.detector.classes_interesse = {c for c in p.value if c}
                elif p.name == 'preproc_ativo':
                    self.pre.ativo = bool(p.value)
                elif p.name == 'preproc_modo':
                    self.pre.modo = str(p.value)
                elif p.name == 'preproc_clahe_clip':
                    self.pre.clahe_clip = float(p.value)
                elif p.name == 'preproc_wb_forca':
                    self.pre.wb_forca = float(p.value)
                self.get_logger().info(f'parametro alterado: {p.name} = {p.value}')
            except (ValueError, TypeError) as e:
                return SetParametersResult(successful=False, reason=str(e))
        return SetParametersResult(successful=True)


def main():
    rclpy.init()
    no = DeteccaoNode()
    try:
        rclpy.spin(no)
    except KeyboardInterrupt:
        pass
    finally:
        no.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
