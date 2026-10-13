#!/usr/bin/env python3
"""
varredura_action_client — cliente da acao /aracne/varrer_cena.

Envia o goal, imprime CADA feedback recebido e registra o result final.
Opcionalmente cancela sozinho depois de N segundos, o que e a forma
pratica de demonstrar cancelamento no video sem depender de digitar
Ctrl+C no momento certo.

Uso:
  ros2 run percepcao_aracnideos varredura_action_client
  ros2 run percepcao_aracnideos varredura_action_client --ros-args \\
      -p duracao_s:=20.0 -p cancelar_apos_s:=6.0
  ros2 run percepcao_aracnideos varredura_action_client --ros-args \\
      -p classe_alvo:=person -p limiar_confianca:=0.5
"""

import sys

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node

from percepcao_aracnideos_interfaces.action import VarrerCena


class VarreduraActionClient(Node):

    def __init__(self):
        super().__init__('varredura_action_client')

        self.declare_parameter('duracao_s', 15.0)
        self.declare_parameter('classe_alvo', '')
        self.declare_parameter('limiar_confianca', -1.0)
        self.declare_parameter('cancelar_apos_s', -1.0)   # <0 = nao cancelar

        self._cliente = ActionClient(self, VarrerCena, '/aracne/varrer_cena')
        self._goal_handle = None
        self._n_feedback = 0
        self._timer_cancel = None
        self.codigo_saida = 0

    # ------------------------------------------------------------------
    def enviar(self):
        self.get_logger().info('aguardando o action server...')
        if not self._cliente.wait_for_server(timeout_sec=15.0):
            self.get_logger().error(
                'action server /aracne/varrer_cena nao apareceu em 15s. '
                'O varredura_action_server esta rodando?')
            self.codigo_saida = 1
            rclpy.shutdown()
            return

        goal = VarrerCena.Goal()
        goal.duracao_s = float(self.get_parameter('duracao_s').value)
        goal.classe_alvo = str(self.get_parameter('classe_alvo').value)
        goal.limiar_confianca = float(self.get_parameter('limiar_confianca').value)

        self.get_logger().info(
            f'enviando goal | duracao={goal.duracao_s:.1f}s | '
            f'classe_alvo="{goal.classe_alvo or "qualquer"}" | '
            f'limiar={goal.limiar_confianca}')

        fut = self._cliente.send_goal_async(goal, feedback_callback=self._on_feedback)
        fut.add_done_callback(self._on_resposta_goal)

    # ------------------------------------------------------------------
    def _on_resposta_goal(self, future):
        gh = future.result()
        if not gh.accepted:
            self.get_logger().error('goal REJEITADO pelo servidor')
            self.codigo_saida = 2
            rclpy.shutdown()
            return

        self._goal_handle = gh
        self.get_logger().info('goal ACEITO — acompanhando feedback')

        t = float(self.get_parameter('cancelar_apos_s').value)
        if t > 0.0:
            self.get_logger().warn(f'cancelamento automatico agendado para {t:.1f}s')
            self._timer_cancel = self.create_timer(t, self._cancelar)

        gh.get_result_async().add_done_callback(self._on_result)

    # ------------------------------------------------------------------
    def _on_feedback(self, msg):
        fb = msg.feedback
        self._n_feedback += 1
        barra_n = int(fb.progresso * 24)
        barra = '#' * barra_n + '.' * (24 - barra_n)
        self.get_logger().info(
            f'[{self._n_feedback:02d}] [{barra}] {fb.progresso*100:5.1f}% | '
            f't={fb.tempo_decorrido_s:5.1f}s | frames={fb.frames_processados:4d} | '
            f'no frame={fb.deteccoes_no_frame} | acumulado={fb.deteccoes_acumuladas} | '
            f'melhor={fb.melhor_confianca:.2f} | {fb.estado}')

    # ------------------------------------------------------------------
    def _cancelar(self):
        if self._timer_cancel is not None:
            self._timer_cancel.cancel()
            self._timer_cancel = None
        if self._goal_handle is not None:
            self.get_logger().warn('>>> ENVIANDO PEDIDO DE CANCELAMENTO <<<')
            self._goal_handle.cancel_goal_async()

    # ------------------------------------------------------------------
    def _on_result(self, future):
        r = future.result().result
        st = future.result().status

        self.get_logger().info('=' * 62)
        self.get_logger().info('RESULT FINAL')
        self.get_logger().info(f'  status codigo      : {st}')
        self.get_logger().info(f'  sucesso            : {r.sucesso}')
        self.get_logger().info(f'  mensagem           : {r.mensagem}')
        self.get_logger().info(f'  frames processados : {r.frames_processados}')
        self.get_logger().info(f'  deteccoes totais   : {r.deteccoes_totais}')
        self.get_logger().info(f'  alvos unicos       : {r.alvos_unicos}')
        self.get_logger().info(f'  confianca media    : {r.confianca_media:.3f}')
        self.get_logger().info(f'  confianca maxima   : {r.confianca_maxima:.3f}')
        self.get_logger().info(f'  duracao real       : {r.duracao_real_s:.2f} s')
        self.get_logger().info(f'  fps medio          : {r.fps_medio:.2f}')
        for c, n in zip(r.classes_vistas, r.contagem_por_classe):
            self.get_logger().info(f'    classe {c:<18} {n}')
        self.get_logger().info(f'  feedbacks recebidos: {self._n_feedback}')
        self.get_logger().info('=' * 62)

        rclpy.shutdown()


def main():
    rclpy.init()
    no = VarreduraActionClient()
    no.enviar()
    try:
        rclpy.spin(no)
    except KeyboardInterrupt:
        pass
    finally:
        cod = no.codigo_saida
        no.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    sys.exit(cod)


if __name__ == '__main__':
    main()
