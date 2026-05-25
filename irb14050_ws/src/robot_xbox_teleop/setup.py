from glob import glob
from setuptools import find_packages, setup

package_name = "robot_xbox_teleop"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}", ["README.md"]),
        (f"share/{package_name}/launch", glob("launch/*.launch.py")),
        (f"share/{package_name}/config", glob("config/*.yaml")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Robot Decision Team",
    maintainer_email="robot@example.com",
    description="Generic gamepad bridge that publishes safe robot task commands.",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "gamepad_command_bridge = robot_xbox_teleop.gamepad_command_bridge:main",
            "xbox_command_bridge = robot_xbox_teleop.xbox_command_bridge:main",
        ],
    },
)
