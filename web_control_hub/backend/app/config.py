from functools import lru_cache
from os import getenv

from dotenv import load_dotenv
from pydantic import BaseModel


load_dotenv()

DEFAULT_REQUIRED_ROS_NODES = ",".join(
    [
        "robot_state_publisher",
        "move_group",
        "egm_bridge",
        "egm_moveit_executor",
        "gripper_node",
        "gripper_joint_state_publisher",
        "robot_task_tree",
        "voice_pipeline_node",
        "web_command_bridge",
        "gamepad_command_bridge",
    ]
)


class Settings(BaseModel):
    ros_domain_id: str = getenv("ROS_DOMAIN_ID", "0")
    command_topic: str = getenv("ROS_COMMAND_TOPIC", "/robot_task/command")
    state_topic: str = getenv("ROS_STATE_TOPIC", "/joint_states")
    sequence_topic: str = getenv("ROS_SEQUENCE_TOPIC", "/web/sequence_id")
    teleop_twist_topic: str = getenv("ROS_TELEOP_TWIST_TOPIC", "/web/teleop_twist")
    voice_text_topic: str = getenv("ROS_VOICE_TEXT_TOPIC", "/voice/text")
    voice_start_topic: str = getenv("ROS_VOICE_START_TOPIC", "/voice/start_listening")
    voice_status_topic: str = getenv("ROS_VOICE_STATUS_TOPIC", "/voice/status")
    voice_events_topic: str = getenv("ROS_VOICE_EVENTS_TOPIC", "/voice/events")
    jetson_metrics_topic: str = getenv("ROS_JETSON_METRICS_TOPIC", "/system/jetson_metrics")
    jetson_metrics_max_age_sec: float = float(getenv("JETSON_METRICS_MAX_AGE_SEC", "15.0"))
    jetson_metrics_allow_local_fallback: bool = (
        getenv("JETSON_METRICS_ALLOW_LOCAL_FALLBACK", "false").lower() == "true"
    )
    image_topic: str = getenv("ROS_IMAGE_TOPIC", "/perception/yolo/debug_image")
    image_is_compressed: bool = getenv("ROS_IMAGE_IS_COMPRESSED", "false").lower() == "true"
    backend_host: str = getenv("BACKEND_HOST", "0.0.0.0")
    backend_port: int = int(getenv("BACKEND_PORT", "8000"))
    frontend_origins: list[str] = [
        origin.strip()
        for origin in getenv("FRONTEND_ORIGINS", "http://localhost:3000").split(",")
        if origin.strip()
    ]
    required_ros_nodes: list[str] = [
        node.strip()
        for node in getenv("ROS_REQUIRED_NODES", DEFAULT_REQUIRED_ROS_NODES).split(",")
        if node.strip()
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
