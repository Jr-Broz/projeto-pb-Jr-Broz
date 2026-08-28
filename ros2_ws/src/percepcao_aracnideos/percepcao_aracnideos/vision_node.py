#!/usr/bin/env python3
"""
vision_node — consome /camera/image_raw, segmenta por cor em HSV,
conta os alvos e responde /vision/status.

Publica:
  /vision/contagem   std_msgs/Int32     alvos no ultimo frame  <- REGUA LEVE
  /vision/mask       sensor_msgs/Image  mascara binaria
  /vision/anotada    sensor_msgs/Image  frame com contornos e rotulos

Servico:
  /vision/status     std_srvs/srv/Trigger

Meca a taxa em /vision/contagem, nao em /camera/image_raw: o
'ros2 topic hz' desserializa cada mensagem inteira em Python, entao
medir imagem crua mede o instrumento se afogando, nao o pipeline.
"""

import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Int32
from std_srvs.srv import Trigger
from cv_bridge import CvBridge


class VisionNode(Node):

    def __init__(self):
        super().__init__("vision_node")

        # Vermelho cruza o zero do matiz: duas faixas de H, unidas por OR.
        self.declare_parameter("h_min_a", 0)
        self.declare_parameter("h_max_a", 10)
        self.declare_parameter("h_min_b", 170)
        self.declare_parameter("h_max_b", 180)
        self.declare_parameter("s_min", 110)
        self.declare_parameter("v_min", 60)
        self.declare_parameter("area_minima", 700)
        self.declare_parameter("dominio", "aracnideos")

        self.bridge = CvBridge()
        self.contagem = 0
        self.areas = []
        self.frames = 0
        self.ultimo_stamp = None

        self.pub_cont = self.create_publisher(Int32, "/vision/contagem", 10)
        self.pub_mask = self.create_publisher(Image, "/vision/mask", 10)
        self.pub_anot = self.create_publisher(Image, "/vision/anotada", 10)

        self.create_subscription(Image, "/camera/image_raw", self.on_frame, 10)
        self.create_service(Trigger, "/vision/status", self.on_status)

        self.get_logger().info("vision_node pronto | servico /vision/status no ar")

    def p(self, nome):
        return self.get_parameter(nome).value

    def segmentar(self, frame):
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        s_min, v_min = self.p("s_min"), self.p("v_min")
        m1 = cv2.inRange(hsv,
                         np.array([self.p("h_min_a"), s_min, v_min]),
                         np.array([self.p("h_max_a"), 255, 255]))
        m2 = cv2.inRange(hsv,
                         np.array([self.p("h_min_b"), s_min, v_min]),
                         np.array([self.p("h_max_b"), 255, 255]))
        mask = cv2.bitwise_or(m1, m2)

        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k, iterations=1)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k, iterations=2)
        return mask

    def on_frame(self, msg):
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        mask = self.segmentar(frame)

        contornos, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL,
                                        cv2.CHAIN_APPROX_SIMPLE)
        amin = self.p("area_minima")
        validos = [c for c in contornos if cv2.contourArea(c) >= amin]

        anot = frame.copy()
        areas = []
        for i, c in enumerate(validos, 1):
            areas.append(float(cv2.contourArea(c)))
            x, y, w, h = cv2.boundingRect(c)
            cv2.rectangle(anot, (x, y), (x + w, y + h), (0, 200, 0), 2)
            cv2.putText(anot, f"alvo {i}", (x, max(16, y - 6)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 200, 0), 2)

        txt = f"{self.p('dominio')}: {len(validos)}"
        cv2.putText(anot, txt, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 3)
        cv2.putText(anot, txt, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 1)

        self.contagem = len(validos)
        self.areas = areas
        self.frames += 1
        self.ultimo_stamp = msg.header.stamp

        self.pub_cont.publish(Int32(data=self.contagem))
        self.pub_mask.publish(self.bridge.cv2_to_imgmsg(mask, encoding="mono8"))
        self.pub_anot.publish(self.bridge.cv2_to_imgmsg(anot, encoding="bgr8"))

    def on_status(self, req, resp):
        if self.frames == 0:
            resp.success = False
            resp.message = "nenhum frame recebido em /camera/image_raw"
            return resp
        t = self.ultimo_stamp
        maior = max(self.areas) if self.areas else 0.0
        resp.success = True
        resp.message = (
            f"ARACNE | candidatos a aracnideo no ultimo frame: {self.contagem} "
            f"| maior area: {maior:.0f} px "
            f"| frames processados: {self.frames} "
            f"| stamp: {t.sec}.{t.nanosec // 1000000:03d}"
        )
        return resp


def main():
    rclpy.init()
    no = VisionNode()
    try:
        rclpy.spin(no)
    except KeyboardInterrupt:
        pass
    finally:
        no.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
