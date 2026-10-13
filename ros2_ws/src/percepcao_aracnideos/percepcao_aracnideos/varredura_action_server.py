#!/usr/bin/env python3
"""
varredura_action_server — a acao assincrona central do projeto.

Acao : /aracne/varrer_cena   (percepcao_aracnideos_interfaces/action/VarrerCena)

O servidor acumula as deteccoes publicadas em /aracne/deteccoes durante
a janela pedida no goal, publica feedback de progresso enquanto trabalha
e devolve metricas no result.

Sobre concorrencia: o no usa ReentrantCallbackGroup com
MultiThreadedExecutor. Sem isso, o laco de execucao do goal bloquearia a
subscricao de /aracne/deteccoes — o servidor ficaria "varrendo" sem
nunca receber uma deteccao, e o cancelamento nunca seria processado.
Esse e o erro mais comum em action server de ROS 2 e o motivo de o
feedback "travar" em muitos projetos.
"""

import threading
import time

import rclpy
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node

from percepcao_aracnideos_interfaces.action import VarrerCena
from percepcao_aracnideos_interfaces.msg import ListaDeteccoes


class VarreduraActionServer(Node):

    PERIODO_FEEDBACK = 0.5      # segundos entre feedbacks

    def __init__(self):
        super().__init__('varredura_action_server')

        self.declare_parameter('duracao_maxima_s', 300.0)
        self.declare_parameter('duracao_padrao_s', 20.0)

        self.grupo = ReentrantCallbackGroup()

        self._lock = threading.Lock()
        self._ultima_lista = None
        self._contador_frames = 0

        self.create_subscription(
            ListaDeteccoes, '/aracne/deteccoes', self._on_deteccoes, 10,
            callback_group=self.grupo)

        self._servidor = ActionServer(
            self, VarrerCena, '/aracne/varrer_cena',
            execute_callback=self._executar,
            goal_callback=self._aceitar_goal,
            cancel_callback=self._aceitar_cancelamento,
            callback_group=self.grupo)

        self.get_logger().info(
            'varredura_action_server pronto | acao /aracne/varrer_cena')

    # ------------------------------------------------------------------
    def _on_deteccoes(self, msg):
        with self._lock:
            self._ultima_lista = msg
            self._contador_frames += 1

    def _snapshot(self):
        with self._lock:
            return self._ultima_lista, self._contador_frames

    # ------------------------------------------------------------------
    def _aceitar_goal(self, goal_request):
        d = goal_request.duracao_s
        maxima = float(self.get_parameter('duracao_maxima_s').value)
        if d <= 0.0:
            d = float(self.get_parameter('duracao_padrao_s').value)
        if d > maxima:
            self.get_logger().warn(
                f'goal rejeitado: duracao {d:.1f}s acima do maximo {maxima:.1f}s')
            return GoalResponse.REJECT
        self.get_logger().info(
            f'goal aceito | duracao={d:.1f}s | classe_alvo='
            f'"{goal_request.classe_alvo or "qualquer"}"')
        return GoalResponse.ACCEPT

    def _aceitar_cancelamento(self, goal_handle):
        self.get_logger().warn('pedido de cancelamento recebido — encerrando varredura')
        return CancelResponse.ACCEPT

    # ------------------------------------------------------------------
    def _executar(self, goal_handle):
        pedido = goal_handle.request
        duracao = pedido.duracao_s
        if duracao <= 0.0:
            duracao = float(self.get_parameter('duracao_padrao_s').value)
        alvo = (pedido.classe_alvo or '').strip()
        limiar = pedido.limiar_confianca

        t0 = time.time()
        _, frames_inicio = self._snapshot()

        deteccoes_totais = 0
        soma_conf = 0.0
        melhor_conf = 0.0
        ids_vistos = set()
        por_classe = {}
        frames_proc = 0
        ultimo_fb = 0.0
        cancelado = False

        self.get_logger().info(f'>>> varrendo por {duracao:.1f}s')

        while True:
            decorrido = time.time() - t0
            if decorrido >= duracao:
                break

            if goal_handle.is_cancel_requested:
                cancelado = True
                break

            lista, frames_agora = self._snapshot()
            frames_proc = frames_agora - frames_inicio

            det_no_frame = 0
            if lista is not None:
                for d in lista.deteccoes:
                    if alvo and d.classe != alvo:
                        continue
                    if limiar >= 0.0 and d.confianca < limiar:
                        continue
                    det_no_frame += 1
                    if d.id_rastreio >= 0 and d.id_rastreio not in ids_vistos:
                        # Conta cada alvo uma vez so: sem o id de rastreio
                        # do filtro de Kalman, o mesmo individuo seria
                        # contado uma vez por frame e a metrica perderia
                        # qualquer sentido.
                        ids_vistos.add(d.id_rastreio)
                        deteccoes_totais += 1
                        soma_conf += d.confianca
                        melhor_conf = max(melhor_conf, d.confianca)
                        por_classe[d.classe] = por_classe.get(d.classe, 0) + 1

            if decorrido - ultimo_fb >= self.PERIODO_FEEDBACK:
                ultimo_fb = decorrido
                fb = VarrerCena.Feedback()
                fb.progresso = float(min(1.0, decorrido / duracao))
                fb.tempo_decorrido_s = float(decorrido)
                fb.frames_processados = int(frames_proc)
                fb.deteccoes_no_frame = int(det_no_frame)
                fb.deteccoes_acumuladas = int(deteccoes_totais)
                fb.melhor_confianca = float(melhor_conf)
                fb.estado = 'varrendo'
                goal_handle.publish_feedback(fb)

            time.sleep(0.05)

        duracao_real = time.time() - t0
        _, frames_fim = self._snapshot()
        frames_proc = frames_fim - frames_inicio

        res = VarrerCena.Result()
        res.frames_processados = int(frames_proc)
        res.deteccoes_totais = int(deteccoes_totais)
        res.alvos_unicos = int(len(ids_vistos))
        res.confianca_media = float(soma_conf / deteccoes_totais) if deteccoes_totais else 0.0
        res.confianca_maxima = float(melhor_conf)
        res.duracao_real_s = float(duracao_real)
        res.fps_medio = float(frames_proc / duracao_real) if duracao_real > 0 else 0.0
        res.classes_vistas = list(por_classe.keys())
        res.contagem_por_classe = [int(v) for v in por_classe.values()]

        if cancelado:
            fb = VarrerCena.Feedback()
            fb.progresso = float(min(1.0, duracao_real / duracao))
            fb.tempo_decorrido_s = float(duracao_real)
            fb.estado = 'cancelando'
            goal_handle.publish_feedback(fb)

            goal_handle.canceled()
            res.sucesso = False
            res.mensagem = (f'varredura cancelada em {duracao_real:.1f}s de '
                            f'{duracao:.1f}s — metricas parciais preservadas')
            self.get_logger().warn('<<< ' + res.mensagem)
            return res

        goal_handle.succeed()
        res.sucesso = True
        res.mensagem = (f'varredura concluida: {res.alvos_unicos} alvos unicos em '
                        f'{frames_proc} frames ({res.fps_medio:.1f} fps)')
        self.get_logger().info('<<< ' + res.mensagem)
        return res


def main():
    rclpy.init()
    no = VarreduraActionServer()
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(no)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        executor.shutdown()
        no.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
