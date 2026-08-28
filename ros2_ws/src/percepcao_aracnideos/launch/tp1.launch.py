import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

PKG = 'percepcao_aracnideos'


def generate_launch_description():
    cfg = os.path.join(get_package_share_directory(PKG), 'config', 'visao.yaml')

    return LaunchDescription([
        DeclareLaunchArgument('fonte', default_value='webcam',
                              description='webcam | video | sintetico'),
        DeclareLaunchArgument('dispositivo', default_value='0'),
        DeclareLaunchArgument('largura', default_value='640'),
        DeclareLaunchArgument('altura', default_value='480'),
        DeclareLaunchArgument('arquivo', default_value=''),

        Node(package=PKG, executable='camera_node', name='camera_node',
             output='screen',
             parameters=[{
                 'fonte': LaunchConfiguration('fonte'),
                 'dispositivo': LaunchConfiguration('dispositivo'),
                 'largura': LaunchConfiguration('largura'),
                 'altura': LaunchConfiguration('altura'),
                 'arquivo': LaunchConfiguration('arquivo'),
             }]),

        Node(package=PKG, executable='vision_node', name='vision_node',
             output='screen', parameters=[cfg]),
    ])
