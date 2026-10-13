"""
Launch do TP2 — sobe o sistema completo de percepcao e a acao.

  ros2 launch percepcao_aracnideos tp2.launch.py
  ros2 launch percepcao_aracnideos tp2.launch.py fonte:=sintetico
  ros2 launch percepcao_aracnideos tp2.launch.py modelo:=/caminho/yolov8n.onnx
  ros2 launch percepcao_aracnideos tp2.launch.py rviz:=true
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, Command
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

PKG = 'percepcao_aracnideos'


def generate_launch_description():
    share = get_package_share_directory(PKG)
    cfg = os.path.join(share, 'config', 'aracne_params.yaml')
    urdf = os.path.join(share, 'urdf', 'aracne_bot.urdf')

    fonte = LaunchConfiguration('fonte')
    modelo = LaunchConfiguration('modelo')
    rviz = LaunchConfiguration('rviz')

    return LaunchDescription([
        DeclareLaunchArgument('fonte', default_value='webcam',
                              description='webcam | video | sintetico'),
        DeclareLaunchArgument('modelo', default_value='',
                              description='caminho do .onnx; vazio = HSV'),
        DeclareLaunchArgument('rviz', default_value='false',
                              description='abrir o RViz2 com o URDF'),

        Node(package=PKG, executable='camera_node', name='camera_node',
             output='screen',
             parameters=[cfg, {'fonte': fonte}]),

        Node(package=PKG, executable='deteccao_node', name='deteccao_node',
             output='screen',
             parameters=[cfg, {'modelo_path': modelo}]),

        Node(package=PKG, executable='varredura_action_server',
             name='varredura_action_server', output='screen',
             parameters=[cfg]),

        # vision_node do TP1: mantido para o gate G1.3/G1.4 continuar
        # demonstravel no estado atual da main.
        Node(package=PKG, executable='vision_node', name='vision_node',
             output='screen', parameters=[cfg]),

        # Publica a TF do URDF. Sem ele o RViz mostra o robo sem
        # transformacoes e tudo aparece empilhado na origem.
        Node(package='robot_state_publisher', executable='robot_state_publisher',
             name='robot_state_publisher', output='screen',
             parameters=[{'robot_description': ParameterValue(
                 Command(['cat ', urdf]), value_type=str)}]),

        Node(package='joint_state_publisher_gui',
             executable='joint_state_publisher_gui',
             name='joint_state_publisher_gui', output='screen',
             condition=IfCondition(rviz)),

        Node(package='rviz2', executable='rviz2', name='rviz2',
             output='screen', condition=IfCondition(rviz)),
    ])
