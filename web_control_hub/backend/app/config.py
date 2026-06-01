from functools import lru_cache
from os import getenv

from dotenv import load_dotenv
from pydantic import BaseModel


load_dotenv()


class Settings(BaseModel):
    ros_domain_id: str = getenv("ROS_DOMAIN_ID", "0")
    command_topic: str = getenv("ROS_COMMAND_TOPIC", "/robot_task/command")
    state_topic: str = getenv("ROS_STATE_TOPIC", "/joint_states")
    sequence_topic: str = getenv("ROS_SEQUENCE_TOPIC", "/web/sequence_id")
    teleop_twist_topic: str = getenv("ROS_TELEOP_TWIST_TOPIC", "/web/teleop_twist")
    voice_text_topic: str = getenv("ROS_VOICE_TEXT_TOPIC", "/voice/text")
    voice_start_topic: str = getenv("ROS_VOICE_START_TOPIC", "/voice/start_listening")
    image_topic: str = getenv("ROS_IMAGE_TOPIC", "/image_raw")
    image_is_compressed: bool = getenv("ROS_IMAGE_IS_COMPRESSED", "false").lower() == "true"
    backend_host: str = getenv("BACKEND_HOST", "0.0.0.0")
    backend_port: int = int(getenv("BACKEND_PORT", "8000"))
    frontend_origins: list[str] = [
        origin.strip()
        for origin in getenv("FRONTEND_ORIGINS", "http://localhost:3000").split(",")
        if origin.strip()
    ]
    joint_names: list[str] = [
        "joint_1",
        "joint_2",
        "joint_3",
        "joint_4",
        "joint_5",
        "joint_6",
        "joint_7",
    ]
    joint_limits_deg: list[tuple[float, float]] = [
        (-168.5, 168.5),
        (-143.5, 43.5),
        (-168.5, 168.5),
        (-123.5, 80.0),
        (-290.0, 290.0),
        (-88.0, 138.0),
        (-229.0, 229.0),
    ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
