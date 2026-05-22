"""Teleoperation behavior-tree behaviours."""

import py_trees
from geometry_msgs.msg import Twist

from robot_task_manager import blackboard_keys as bb_keys
from robot_task_manager.behaviors.common import BlackboardBehavior


class CheckWebHeartbeat(BlackboardBehavior):
    """Require a recent web heartbeat before streaming web teleop."""

    def update(self) -> py_trees.common.Status:
        last = self.bb_get(bb_keys.WEB_LAST_HEARTBEAT_TIME)
        if last is None:
            self.publish_zero_twist()
            self.bb_set(bb_keys.TELEOP_ACTIVE, False)
            self.set_status(mode="IDLE", message="Waiting for web heartbeat")
            return py_trees.common.Status.FAILURE

        age = self.now() - float(last)
        if age <= float(self.node.web_heartbeat_timeout_s):
            return py_trees.common.Status.SUCCESS

        self.publish_zero_twist()
        self.bb_set(bb_keys.TELEOP_ACTIVE, False)
        self.set_status(
            mode="IDLE",
            message=f"Web heartbeat timeout ({age:.2f}s)",
            error_code="WEB_HEARTBEAT_TIMEOUT",
        )
        return py_trees.common.Status.FAILURE


class IsXboxDeadmanPressed(BlackboardBehavior):
    """Require a fresh Xbox deadman state before streaming Xbox teleop."""

    def update(self) -> py_trees.common.Status:
        pressed = bool(self.bb_get(bb_keys.XBOX_DEADMAN_PRESSED, False))
        last = self.bb_get(bb_keys.XBOX_DEADMAN_LAST_TIME)
        age_ok = last is not None and (self.now() - float(last)) <= float(self.node.xbox_deadman_timeout_s)

        if pressed and age_ok:
            return py_trees.common.Status.SUCCESS

        self.publish_zero_twist()
        self.bb_set(bb_keys.TELEOP_ACTIVE, False)
        self.set_status(mode="IDLE", message="Xbox deadman released", error_code="")
        return py_trees.common.Status.FAILURE


class EnableServoMode(BlackboardBehavior):
    """Enable servo streaming mode in the blackboard."""

    def update(self) -> py_trees.common.Status:
        self.bb_set(bb_keys.TELEOP_ACTIVE, True)
        self.bb_set(bb_keys.ARM_BUSY, False)
        self.set_status(message="Servo mode enabled", progress=0.0, error_code="")
        return py_trees.common.Status.SUCCESS


class _StreamTeleopBase(BlackboardBehavior):
    mode = "IDLE"
    label = "teleop"

    def update(self) -> py_trees.common.Status:
        command = self.bb_get(bb_keys.CURRENT_COMMAND)
        twist = Twist()
        if command is not None:
            twist = command.teleop_twist

        self.node.servo_pub.publish(twist)
        self.bb_set(bb_keys.TELEOP_ACTIVE, True)
        self.set_status(
            mode=self.mode,
            message=f"Streaming {self.label} teleop",
            progress=0.0,
            error_code="",
            current_task=f"{self.label} teleop",
        )
        return py_trees.common.Status.RUNNING

    def terminate(self, new_status: py_trees.common.Status) -> None:
        if new_status == py_trees.common.Status.INVALID:
            self.publish_zero_twist()
            self.bb_set(bb_keys.TELEOP_ACTIVE, False)


class StreamXboxTeleop(_StreamTeleopBase):
    mode = "XBOX_TELEOP"
    label = "Xbox"


class StreamWebTeleop(_StreamTeleopBase):
    mode = "WEB_TELEOP"
    label = "web"
