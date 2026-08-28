#!/usr/bin/env bash
# Dependencias alem do padrao da disciplina.
# O professor roda este script num clone limpo.
set -e

echo "[setup] instalando dependencias do projeto ARACNE"

sudo apt update
sudo apt install -y \
    python3-opencv \
    ros-humble-cv-bridge \
    ros-humble-rqt-graph \
    ros-humble-rqt-image-view \
    python3-colcon-common-extensions \
    v4l-utils

# Dependencias declaradas nos package.xml
if command -v rosdep >/dev/null 2>&1; then
    rosdep install --from-paths ros2_ws/src --ignore-src -r -y || true
fi

echo "[setup] concluido"
