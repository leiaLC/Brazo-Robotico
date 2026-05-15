from setuptools import find_packages, setup

package_name = 'abb_irb14050_egm'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch',
            ['launch/egm_bridge.launch.py']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Ives',
    maintainer_email='ives@example.com',
    description='ROS2 bridge to ABB IRB 14050 via EGM protocol.',
    license='MIT',
    entry_points={
        'console_scripts': [
            'egm_bridge = abb_irb14050_egm.egm_bridge_node:main',
            'joint_commander = '
                'abb_irb14050_egm.joint_commander_node:main',
            'joint_listener = '
                'abb_irb14050_egm.joint_state_listener_node:main',
            'teach = abb_irb14050_egm.teach_node:main',
            'egm_moveit_executor = abb_irb14050_egm.egm_moveit_executor:main',
            'waypoint_player = '
                'abb_irb14050_egm.waypoint_player_node:main',
        ],
    },
)
