from glob import glob
from setuptools import find_packages, setup

package_name = "robot_task_manager"

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
    install_requires=["setuptools", "PyYAML"],
    zip_safe=True,
    maintainer="Robot Decision Team",
    maintainer_email="robot@example.com",
    description="Central behavior-tree task manager for safe robot command arbitration.",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "robot_task_tree = robot_task_manager.task_tree_node:main",
            "gripper_joint_state_publisher = robot_task_manager.gripper_joint_state_publisher:main",
        ],
    },
)
