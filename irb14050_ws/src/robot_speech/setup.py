from glob import glob

from setuptools import find_packages, setup

package_name = "robot_speech"

setup(
    name=package_name,
    version="0.0.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/config", glob("config/*.yaml")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="zuriel_tov",
    maintainer_email="zuriel.tovar.m@gmail.com",
    description="Voice pipeline bridge for RAOR robot task commands",
    license="TODO: License declaration",
    extras_require={
        "test": [
            "pytest",
        ],
    },
    entry_points={
        "console_scripts": [
            "voice_commander_node = robot_speech.voice_commander_node:main",
            "voice_pipeline_node = robot_speech.voice_commander_node:main",
            "voice_command_node = robot_speech.voice_commander_node:main",
            "verify_password = robot_speech.modules.speaker.verify:main",
        ],
    },
)
