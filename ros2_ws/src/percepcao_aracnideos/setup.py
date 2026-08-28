import os
from glob import glob
from setuptools import setup

package_name = 'percepcao_aracnideos'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='SEU NOME',
    maintainer_email='SEU-EMAIL@al.infnet.edu.br',
    description='ARACNE - percepcao de aracnideos por camera com ROS 2',
    license='MIT',
    entry_points={
        'console_scripts': [
            'camera_node = percepcao_aracnideos.camera_node:main',
            'vision_node = percepcao_aracnideos.vision_node:main',
        ],
    },
)
