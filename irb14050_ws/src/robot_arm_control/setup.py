from glob import glob
from setuptools import find_packages, setup

package_name = "robot_arm_control"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/launch", glob("launch/*.launch.py")),
        (f"share/{package_name}/config", glob("config/*.yaml")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Robot Decision Team",
    maintainer_email="robot@example.com",
    description="Mock arm, gripper, and servo adapters for robot task execution.",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "mock_arm_action_server = robot_arm_control.mock_arm_action_server:main",
            "mock_gripper_node = robot_arm_control.mock_gripper_node:main",
            "mock_servo_node = robot_arm_control.mock_servo_node:main",
        ],
    },
)
