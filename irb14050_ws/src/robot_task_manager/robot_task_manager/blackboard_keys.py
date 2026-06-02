"""Central names for behavior-tree blackboard keys."""

CURRENT_COMMAND = "current_command"
CURRENT_MODE = "current_mode"

ROBOT_READY = "robot_ready"
ESTOP_ACTIVE = "estop_active"
ARM_BUSY = "arm_busy"
TELEOP_ACTIVE = "teleop_active"

YOLO_DETECTIONS = "yolo_detections"
CANDIDATE_OBJECTS = "candidate_objects"
SELECTED_OBJECT = "selected_object"
SELECTED_OBJECT_POSE_CAMERA = "selected_object_pose_camera"
SELECTED_OBJECT_POSE_BASE = "selected_object_pose_base"

PRE_GRASP_POSE = "pre_grasp_pose"
GRASP_POSE = "grasp_pose"
RETREAT_POSE = "retreat_pose"
PLACE_POSE = "place_pose"

JOINT_GOAL = "joint_goal"
SEQUENCE_STEPS = "sequence_steps"

STATUS_TEXT = "status_text"
ERROR_CODE = "error_code"

# Internal helper keys. They are deliberately kept near the public keys so
# behavior modules do not share string literals.
TASK_PROGRESS = "task_progress"
CURRENT_TASK = "current_task"
JOINT_STATE_DEG = "joint_state_deg"
WEB_LAST_HEARTBEAT_TIME = "web_last_heartbeat_time"
XBOX_DEADMAN_PRESSED = "xbox_deadman_pressed"
XBOX_DEADMAN_LAST_TIME = "xbox_deadman_last_time"

# Paused sequence state — set on PAUSE, consumed on RESUME
PAUSED_SEQUENCE_ID = "paused_sequence_id"
PAUSED_SEQUENCE_STEP = "paused_sequence_step"