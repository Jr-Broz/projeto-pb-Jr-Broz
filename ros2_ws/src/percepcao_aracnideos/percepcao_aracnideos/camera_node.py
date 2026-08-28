#!/usr/bin/env python3
"""
camera_node — publica frames em /camera/image_raw.

Parametro 'fonte':
  webcam     -> /dev/videoN (padrao)
  video      -> arquivo, caminho em 'arquivo'
  sintetico  -> cena gerada em codigo, sem hardware nenhum

Degradar, nao quebrar: se a webcam nao abrir, o no cai sozinho para a
fonte sintetica e registra um warning. O grafo continua de pe.
"""

import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge


class CameraNode(Node):

    def __init__(self):
        super().__init__("camera_node")

        self.declare_parameter("fonte", "webcam")
        self.declare_parameter("arquivo", "")
        self.declare_parameter("dispositivo", 0)
        self.declare_parameter("fps", 15.0)
        self.declare_parameter("largura", 640)
        self.declare_parameter("altura", 480)
        self.declare_parameter("fourcc", "MJPG")

        self.fonte = self.get_parameter("fonte").value
        self.largura = self.get_parameter("largura").value
        self.altura = self.get_parameter("altura").value
        fps = self.get_parameter("fps").value

        self.bridge = CvBridge()
        self.pub = self.create_publisher(Image, "/camera/image_raw", 10)
        self.cap = None
        self.t = 0

        if self.fonte == "webcam":
            self.abrir_webcam()
        elif self.fonte == "video":
            self.abrir_video()

        self.get_logger().info(
            f"publicando em /camera/image_raw | fonte={self.fonte} "
            f"| {self.largura}x{self.altura} @{fps:.0f}fps")
        self.create_timer(1.0 / fps, self.tick)

    def abrir_webcam(self):
        dev = self.get_parameter("dispositivo").value
        # Backend explicito: sem isso o OpenCV tenta GStreamer antes do V4L2
        # e devolve False sem explicar por que.
        cap = cv2.VideoCapture(dev, cv2.CAP_V4L2)
        if not cap.isOpened():
            self.get_logger().warn(
                f"nao abriu /dev/video{dev} — caindo para fonte sintetica")
            self.fonte = "sintetico"
            return

        cc = self.get_parameter("fourcc").value
        if cc:
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*cc))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.largura)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.altura)

        ok, _ = cap.read()
        if not ok:
            self.get_logger().warn(
                "dispositivo abriu mas nao entrega frame — fonte sintetica")
            cap.release()
            self.fonte = "sintetico"
            return

        # Imprime o que a camera ACEITOU, nao o que foi pedido.
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        f = int(cap.get(cv2.CAP_PROP_FOURCC))
        nome = "".join([chr((f >> 8 * i) & 0xFF) for i in range(4)]).strip()
        real_fps = cap.get(cv2.CAP_PROP_FPS)
        self.get_logger().info(
            f"webcam negociada: {w}x{h} {nome} @{real_fps:.0f}fps "
            f"(o que a camera ACEITOU, nao o que foi pedido)")
        self.largura, self.altura = w, h
        self.cap = cap

    def abrir_video(self):
        caminho = self.get_parameter("arquivo").value
        cap = cv2.VideoCapture(caminho)
        if not cap.isOpened():
            self.get_logger().warn(f"nao abriu {caminho} — fonte sintetica")
            self.fonte = "sintetico"
            return
        self.cap = cap

    def frame_sintetico(self):
        """Cena controlada: dois alvos que se cruzam sobre fundo neutro.

        O cruzamento e proposital: e o experimento de oclusao do G1.5.
        """
        img = np.full((self.altura, self.largura, 3), 210, dtype=np.uint8)
        cv2.rectangle(img, (0, self.altura - 60), (self.largura, self.altura),
                      (190, 190, 190), -1)

        self.t += 1
        for k, raio in enumerate((34, 24)):
            fase = self.t * 0.035 + k * 2.1
            cx = int(self.largura * (0.5 + 0.30 * np.sin(fase)))
            cy = int(self.altura * (0.5 + 0.18 * np.cos(fase * 1.4)))
            cv2.circle(img, (cx, cy), raio, (30, 30, 205), -1)
            for ang in range(0, 360, 45):
                r = np.deg2rad(ang)
                p2 = (int(cx + np.cos(r) * raio * 2.1),
                      int(cy + np.sin(r) * raio * 1.7))
                cv2.line(img, (cx, cy), p2, (30, 30, 205), 3)
        return img

    def tick(self):
        if self.cap is not None:
            ok, frame = self.cap.read()
            if not ok:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ok, frame = self.cap.read()
                if not ok:
                    return
        else:
            frame = self.frame_sintetico()

        msg = self.bridge.cv2_to_imgmsg(frame, encoding="bgr8")
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "camera_link"
        self.pub.publish(msg)

    def destroy_node(self):
        if self.cap is not None:
            self.cap.release()
        super().destroy_node()


def main():
    rclpy.init()
    no = CameraNode()
    try:
        rclpy.spin(no)
    except KeyboardInterrupt:
        pass
    finally:
        no.destroy_node()
        # Evita o ruido 'rcl_shutdown already called' no Ctrl+C
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
