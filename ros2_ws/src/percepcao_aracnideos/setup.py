import os
from glob import glob
from setuptools import setup

package_name = 'percepcao_aracnideos'

setup(
    name=package_name,
    version='0.2.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*')),
        (os.path.join('share', package_name, 'urdf'), glob('urdf/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='João Rafael Broz dos Santos',
    maintainer_email='euejaojaoeeu@gmail.com',
    description='ARACNE - percepcao de aracnideos por camera com ROS 2',
    license='MIT',
    entry_points={
        'console_scripts': [
            'camera_node = percepcao_aracnideos.camera_node:main',
            'vision_node = percepcao_aracnideos.vision_node:main',
            'deteccao_node = percepcao_aracnideos.deteccao_node:main',
            'varredura_action_server = percepcao_aracnideos.varredura_action_server:main',
            'varredura_action_client = percepcao_aracnideos.varredura_action_client:main',
        ],
    },
)
