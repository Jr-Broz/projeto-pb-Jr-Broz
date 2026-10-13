"""
Launch so do URDF — RViz2 + robot_state_publisher + sliders das juntas.

  ros2 launch percepcao_aracnideos urdf.launch.py

Use este para a evidencia do item 4. Ele nao sobe camera nem detector,
entao a janela do RViz abre rapido e sem concorrer por CPU.
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.substitutions import Command
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

PKG = 'percepcao_aracnideos'


def generate_launch_description():
    share = get_package_share_directory(PKG)
    urdf = os.path.join(share, 'urdf', 'aracne_bot.urdf')

    return LaunchDescription([
        Node(package='robot_state_publisher', executable='robot_state_publisher',
             name='robot_state_publisher', output='screen',
             parameters=[{'robot_description': ParameterValue(
                 Command(['cat ', urdf]), value_type=str)}]),

        Node(package='joint_state_publisher_gui',
             executable='joint_state_publisher_gui',
             name='joint_state_publisher_gui', output='screen'),

        Node(package='rviz2', executable='rviz2', name='rviz2', output='screen'),
    ])
