"""Factory for the robot supervisor behavior tree."""

import py_trees

from robot_task_manager.behaviors.command_conditions import (
    ClearCurrentCommand,
    HasCommandType,
    HasEStopOrCancel,
    PublishIdleStatus,
)
from robot_task_manager.behaviors.gripper_behaviors import CloseGripper, OpenGripper
from robot_task_manager.behaviors.motion_behaviors import (
    BuildJointGoal,
    CancelArmGoals,
    ExecuteJointGoal,
    MoveToGrasp,
    MoveToPerceptionPose,
    MoveToPlacePose,
    MoveToPreGrasp,
    Retreat,
    ValidateJointGoal,
)
from robot_task_manager.behaviors.safety import (
    CheckArmNotInFault,
    CheckEStop,
    CheckRobotReady,
    ReportEmergency,
    UpdateSystemState,
)
from robot_task_manager.behaviors.sequence_behaviors import (
    ExecuteSequence,
    LoadSequence,
    ValidateSequence,
)
from robot_task_manager.behaviors.teleop_behaviors import (
    CheckWebHeartbeat,
    EnableServoMode,
    IsXboxDeadmanPressed,
    StreamWebTeleop,
    StreamXboxTeleop,
)
from robot_task_manager.behaviors.yolo_behaviors import (
    DetectObjectsYOLO,
    EstimateObject3DPose,
    PlanPreGraspPose,
    SelectObjectByClassAndColor,
    TransformPoseToRobotBase,
    ValidateObjectWorkspace,
)


def create_robot_supervisor_tree(node) -> py_trees.behaviour.Behaviour:
    """Build the main supervisor tree requested for the workspace."""

    root = py_trees.composites.Sequence(name="RobotSupervisor", memory=False)

    safety_gate = py_trees.composites.Sequence(
        name="SafetyGate",
        memory=False,
        children=[
            CheckRobotReady("CheckRobotReady", node),
            CheckEStop("CheckEStop", node),
            CheckArmNotInFault("CheckArmNotInFault", node),
        ],
    )

    emergency_branch = py_trees.composites.Sequence(
        name="EmergencyStopBranch",
        memory=False,
        children=[
            HasEStopOrCancel("HasEStopOrCancel", node),
            CancelArmGoals("CancelArmGoals", node),
            StopServo("StopServo", node),
            ReportEmergency("ReportEmergency", node),
        ],
    )

    xbox_branch = py_trees.composites.Sequence(
        name="XboxTeleopBranch",
        memory=False,
        children=[
            HasCommandType('HasCommandType("XBOX_TELEOP")', node, "XBOX_TELEOP"),
            IsXboxDeadmanPressed("IsXboxDeadmanPressed", node),
            EnableServoMode("EnableServoMode", node),
            StreamXboxTeleop("StreamXboxTeleop", node),
        ],
    )

    web_branch = py_trees.composites.Sequence(
        name="WebTeleopBranch",
        memory=False,
        children=[
            HasCommandType('HasCommandType("WEB_TELEOP")', node, "WEB_TELEOP"),
            CheckWebHeartbeat("CheckWebHeartbeat", node),
            EnableServoMode("EnableServoMode", node),
            StreamWebTeleop("StreamWebTeleop", node),
        ],
    )

    voice_joint_branch = py_trees.composites.Sequence(
        name="VoiceJointMoveBranch",
        memory=True,
        children=[
            HasCommandType('HasCommandType("MOVE_JOINT")', node, "MOVE_JOINT"),
            BuildJointGoal("BuildJointGoal", node),
            ValidateJointGoal("ValidateJointGoal", node),
            ExecuteJointGoal("ExecuteJointGoal", node),
            ClearCurrentCommand("ClearCurrentCommand", node),
        ],
    )

    web_sequence_branch = py_trees.composites.Sequence(
        name="WebSequenceBranch",
        memory=True,
        children=[
            HasCommandType('HasCommandType("RUN_SEQUENCE")', node, "RUN_SEQUENCE"),
            LoadSequence("LoadSequence", node),
            ValidateSequence("ValidateSequence", node),
            ExecuteSequence("ExecuteSequence", node),
            ClearCurrentCommand("ClearCurrentCommand", node),
        ],
    )

    voice_pick_place_branch = py_trees.composites.Sequence(
        name="VoicePickPlaceBranch",
        memory=True,
        children=[
            HasCommandType('HasCommandType("PICK_OBJECT")', node, "PICK_OBJECT"),
            MoveToPerceptionPose("MoveToPerceptionPose", node),
            DetectObjectsYOLO("DetectObjectsYOLO", node),
            SelectObjectByClassAndColor("SelectObjectByClassAndColor", node),
            EstimateObject3DPose("EstimateObject3DPose", node),
            TransformPoseToRobotBase("TransformPoseToRobotBase", node),
            ValidateObjectWorkspace("ValidateObjectWorkspace", node),
            PlanPreGraspPose("PlanPreGraspPose", node),
            OpenGripper("OpenGripper", node),
            MoveToPreGrasp("MoveToPreGrasp", node),
            MoveToGrasp("MoveToGrasp", node),
            CloseGripper("CloseGripper", node),
            Retreat("Retreat", node),
            MoveToPlacePose("MoveToPlacePose", node),
            OpenGripper("OpenGripper", node),
            ClearCurrentCommand("ClearCurrentCommand", node),
        ],
    )

    idle_branch = py_trees.composites.Sequence(
        name="IdleBranch",
        memory=False,
        children=[PublishIdleStatus("PublishIdleStatus", node)],
    )

    main_selector = py_trees.composites.Selector(
        name="MainSelector",
        memory=False,
        children=[
            emergency_branch,
            xbox_branch,
            web_branch,
            voice_joint_branch,
            web_sequence_branch,
            voice_pick_place_branch,
            idle_branch,
        ],
    )

    root.add_children(
        [
            UpdateSystemState("UpdateSystemState", node),
            safety_gate,
            main_selector,
        ]
    )
    return root


class StopServo(py_trees.behaviour.Behaviour):
    """Dedicated tree node matching the requested tree layout."""

    def __init__(self, name: str, node):
        super().__init__(name=name)
        self.node = node

    def update(self) -> py_trees.common.Status:
        self.node.publish_zero_twist()
        self.node.get_logger().warn("Servo stopped")
        return py_trees.common.Status.SUCCESS
