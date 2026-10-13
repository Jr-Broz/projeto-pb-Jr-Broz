#!/usr/bin/env bash
# Dependencias alem do padrao da disciplina.
# O professor roda este script num clone limpo, antes do reproduzir.sh.
set -e

echo "[setup] dependencias do projeto ARACNE"

sudo apt update
sudo apt install -y \
    python3-opencv \
    python3-numpy \
    ros-humble-cv-bridge \
    ros-humble-rqt-graph \
    ros-humble-rqt-image-view \
    ros-humble-rqt-common-plugins \
    ros-humble-robot-state-publisher \
    ros-humble-joint-state-publisher-gui \
    ros-humble-rviz2 \
    ros-humble-xacro \
    python3-colcon-common-extensions \
    v4l-utils

if command -v rosdep >/dev/null 2>&1; then
    rosdep install --from-paths ros2_ws/src --ignore-src -r -y || true
fi

# Peso do YOLO (13 MB). Opcional: sem ele o detector cai para HSV.
bash "$(dirname "$0")/baixar_modelo.sh" || true

echo "[setup] concluido"
