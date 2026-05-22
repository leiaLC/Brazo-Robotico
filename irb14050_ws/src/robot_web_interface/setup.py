from glob import glob
from setuptools import find_packages, setup

package_name = "robot_web_interface"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/launch", glob("launch/*.launch.py")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Robot Decision Team",
    maintainer_email="robot@example.com",
    description="ROS bridge for web teleoperation and sequence commands.",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "web_command_bridge = robot_web_interface.web_command_bridge:main",
        ],
    },
)
