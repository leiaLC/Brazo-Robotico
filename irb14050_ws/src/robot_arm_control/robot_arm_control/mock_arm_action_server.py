#!/usr/bin/env python3
"""Mock MoveJoint action server for simulation and integration tests."""

import asyncio

import rclpy
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node

from robot_task_msgs.action import MoveJoint


class MockArmActionServer(Node):
    """Simulate a robot arm joint move action with progress feedback."""

    def __init__(self) -> None:
        super().__init__("mock_arm_action_server")
        self.declare_parameter("simulation_mode", True)
        self.declare_parameter("action_name", "/arm/move_joint")
        self.declare_parameter("execution_duration_s", 2.0)
        self.simulation_mode = bool(self.get_parameter("simulation_mode").value)
        self.action_name = str(self.get_parameter("action_name").value)
        self.execution_duration_s = max(0.1, float(self.get_parameter("execution_duration_s").value))

        self.action_server = ActionServer(
            self,
            MoveJoint,
            self.action_name,
            execute_callback=self._execute_callback,
            goal_callback=self._goal_callback,
            cancel_callback=self._cancel_callback,
        )
        self.get_logger().info(
            f"mock_arm_action_server ready on {self.action_name} "
            f"(simulation_mode={self.simulation_mode})"
        )

    def _goal_callback(self, goal_request) -> GoalResponse:
        self.get_logger().info(f"Accepted mock joint goal: {list(goal_request.joint_values)}")
        return GoalResponse.ACCEPT

    def _cancel_callback(self, _goal_handle) -> CancelResponse:
        self.get_logger().warn("Mock joint goal cancel requested")
        return CancelResponse.ACCEPT

    async def _execute_callback(self, goal_handle):
        steps = 20
        sleep_s = self.execution_duration_s / steps
        for index in range(steps + 1):
            if goal_handle.is_cancel_requested:
                goal_handle.canceled()
                result = MoveJoint.Result()
                result.success = False
                result.message = "Mock joint goal cancelled"
                return result

            feedback = MoveJoint.Feedback()
            feedback.progress = float(index / steps)
            feedback.current_state = f"mock moving {index}/{steps}"
            goal_handle.publish_feedback(feedback)
            await asyncio.sleep(sleep_s)

        goal_handle.succeed()
        result = MoveJoint.Result()
        result.success = True
        result.message = "Mock joint goal complete"
        self.get_logger().info("Mock joint goal complete")
        return result


def main(args=None) -> None:
    rclpy.init(args=args)
    node = MockArmActionServer()
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        executor.shutdown()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
