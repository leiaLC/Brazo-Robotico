from glob import glob
from setuptools import find_packages, setup

package_name = "robot_voice_interface"

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
    description="Text-based Spanish voice command parser for robot tasks.",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "voice_command_parser = robot_voice_interface.voice_command_parser:main",
        ],
    },
)
