"""Sequence loading, validation, and execution behaviours."""

from __future__ import annotations

import copy
from pathlib import Path
import math

import py_trees
import yaml
from geometry_msgs.msg import PoseStamped
from rclpy.action import ActionClient

from robot_task_manager import blackboard_keys as bb_keys
from robot_task_manager.behaviors.common import BlackboardBehavior
from robot_task_manager.behaviors.motion_behaviors import (
    MOVEIT_AVAILABLE,
    Constraints,
    JointConstraint,
    MoveToPerceptionPose,
    MotionPlanRequest,
    MoveGroup,
    MoveItErrorCodes,
)
from robot_task_manager.behaviors.pick_place_subtree import build_grasp_place_subtree
from robot_task_manager.behaviors.yolo_behaviors import base_pose_for_detection
from robot_task_msgs.action import MoveJoint


class LoadSequence(BlackboardBehavior):
    """Load a named sequence from the configured YAML file."""

    def update(self) -> py_trees.common.Status:
        command = self.bb_get(bb_keys.CURRENT_COMMAND)
        if command is None:
            self.set_status(mode="ERROR", message="No sequence command", error_code="NO_COMMAND")
            return py_trees.common.Status.FAILURE

        sequence_path = Path(self.node.sequences_file)
        if not sequence_path.exists():
            self.set_status(
                mode="ERROR",
                message=f"Sequences file not found: {sequence_path}",
                error_code="SEQUENCE_FILE_MISSING",
            )
            return py_trees.common.Status.FAILURE

        data = yaml.safe_load(sequence_path.read_text(encoding="utf-8")) or {}
        entry = data.get(command.sequence_id)
        if entry is None:
            self.set_status(
                mode="ERROR",
                message=f"Unknown sequence: {command.sequence_id}",
                error_code="UNKNOWN_SEQUENCE",
            )
            return py_trees.common.Status.FAILURE

        steps = list(entry.get("steps", []))
        self.bb_set(bb_keys.SEQUENCE_STEPS, steps)
        self.set_status(
            mode="WEB_SEQUENCE",
            message=f"Loaded sequence {command.sequence_id}: {entry.get('description', '')}",
            progress=0.05,
            error_code="",
            current_task=f"sequence {command.sequence_id}",
        )
        return py_trees.common.Status.SUCCESS


class ValidateSequence(BlackboardBehavior):
    """Validate step types and joint values before execution."""

    VALID_STEP_TYPES = {
        "move_joints",
        "gripper",
        "pick_object",
        "detect_objects",
        "classify",
        "perception_pose",
        "give_to_hand",
    }

    def update(self) -> py_trees.common.Status:
        steps = list(self.bb_get(bb_keys.SEQUENCE_STEPS, []))
        if not steps:
            self.set_status(mode="ERROR", message="Sequence has no steps", error_code="EMPTY_SEQUENCE")
            return py_trees.common.Status.FAILURE

        for index, step in enumerate(steps):
            step_type = step.get("type")
            if step_type not in self.VALID_STEP_TYPES:
                self.set_status(
                    mode="ERROR",
                    message=f"Invalid step type at {index}: {step_type}",
                    error_code="INVALID_SEQUENCE_STEP",
                )
                return py_trees.common.Status.FAILURE

            if step_type == "move_joints":
                valid, message = self.node.joint_limits.validate(step.get("joint_values_deg", []))
                if not valid:
                    self.set_status(mode="ERROR", message=message, error_code="SEQUENCE_JOINT_LIMIT")
                    return py_trees.common.Status.FAILURE

            if step_type == "gripper" and step.get("command") not in {"open", "close"}:
                self.set_status(mode="ERROR", message="Invalid gripper command", error_code="INVALID_GRIPPER")
                return py_trees.common.Status.FAILURE

            if (
                step_type == "detect_objects"
                and float(step.get("timeout_s", 0.0)) < 0.0
            ):
                self.set_status(
                    mode="ERROR",
                    message="Invalid detection timeout",
                    error_code="INVALID_DETECTION_TIMEOUT",
                )
                return py_trees.common.Status.FAILURE

        self.set_status(mode="WEB_SEQUENCE", message="Sequence validated", progress=0.10, error_code="")
        return py_trees.common.Status.SUCCESS


class ExecuteSequence(BlackboardBehavior):
    """Execute sequence steps through simulation or the configured motion backend."""

    def __init__(self, name: str, node):
        super().__init__(name, node)
        self._index = 0
        self._step_start: float | None = None
        self._published_step = -1
        self._move_group_client = None
        self._action_client = None
        self._send_future = None
        self._result_future = None
        self._goal_handle = None
        self._wait_error: tuple[str, str] | None = None
        # Estado del paso `classify` (loop de grasp&place con poses fijas).
        self._classify_subtree = None
        self._classify_queue: list | None = None
        self._classify_index = 0
        self._classify_current = -1
        self._classify_started = False
        self._perception_pose_behavior = MoveToPerceptionPose("SequenceMoveToPerceptionPose", node)
        self._give_to_hand_subtree = None
        self._give_to_hand_started = False
        self._give_to_hand_target = ""
        if not self.node.simulation_mode and self.node.motion_backend == "abb_moveit" and MOVEIT_AVAILABLE:
            self._move_group_client = ActionClient(self.node, MoveGroup, self.node.move_group_action_name)
        elif not self.node.simulation_mode:
            self._action_client = ActionClient(self.node, MoveJoint, self.node.arm_action_name)

    def initialise(self) -> None:
        # Si hay un step de "resume", arrancar desde ahí. Si no, desde 0.
        resume_step = self.bb_get(bb_keys.PAUSED_SEQUENCE_STEP, 0)
        self._index = int(resume_step or 0)
        if self._index > 0:
            self.node.get_logger().info(
                f"Resuming sequence from step {self._index}"
            )
        # Limpiamos el step pausado ahora que ya lo consumimos.
        self.bb_set(bb_keys.PAUSED_SEQUENCE_STEP, 0)
        self._step_start = self.now()
        self._published_step = -1
        self._reset_motion_state()
        # Reset del estado de classify para una corrida fresca.
        self._classify_started = False
        self._classify_queue = None
        self._classify_index = 0
        self._classify_current = -1
        self._give_to_hand_started = False
        self._give_to_hand_target = ""
        self.bb_set(bb_keys.PLACE_POSE_OVERRIDE, None)
        self.bb_set(bb_keys.ARM_BUSY, True)
        self.set_status(mode="WEB_SEQUENCE", message="Executing sequence", progress=0.10)

    def update(self) -> py_trees.common.Status:
        steps = list(self.bb_get(bb_keys.SEQUENCE_STEPS, []))
        if not steps:
            self.bb_set(bb_keys.ARM_BUSY, False)
            return py_trees.common.Status.SUCCESS

        if self._index >= len(steps):
            self.bb_set(bb_keys.ARM_BUSY, False)
            # Secuencia terminada: limpiamos el paso pausado para que no quede
            # un valor obsoleto que afecte una corrida futura.
            self.bb_set(bb_keys.PAUSED_SEQUENCE_STEP, 0)
            self.set_status(mode="WEB_SEQUENCE", message="Sequence complete", progress=1.0, error_code="")
            return py_trees.common.Status.SUCCESS

        step = steps[self._index]
        # Publicamos el step actual al blackboard para que un PAUSE pueda capturarlo
        self.bb_set(bb_keys.PAUSED_SEQUENCE_STEP, self._index)
        self._publish_step_start(step)

        if self._uses_real_moveit(step):
            return self._update_real_move_joints(step, len(steps))
        if self._uses_real_action(step):
            return self._update_action_move_joints(step, len(steps))
        if step.get("type") == "detect_objects":
            return self._update_detect_objects(step, len(steps))
        if step.get("type") == "perception_pose":
            return self._update_perception_pose(len(steps))
        if step.get("type") == "classify":
            return self._update_classify(step, len(steps))
        if step.get("type") == "give_to_hand":
            return self._update_give_to_hand(step, len(steps))

        duration = self._step_duration(step)
        elapsed = self.now() - (self._step_start or self.now())
        step_fraction = 1.0 if duration <= 0.0 else min(1.0, elapsed / duration)
        total_progress = (self._index + step_fraction) / max(1, len(steps))
        self.set_status(
            mode="WEB_SEQUENCE",
            message=f"Step {self._index + 1}/{len(steps)}: {step.get('type')}",
            progress=total_progress,
        )

        if step_fraction < 1.0:
            return py_trees.common.Status.RUNNING

        self._finish_step(step)
        self._index += 1
        self._step_start = self.now()
        self._reset_motion_state()
        return py_trees.common.Status.RUNNING

    def _uses_real_moveit(self, step: dict) -> bool:
        return (
            not self.node.simulation_mode
            and self.node.motion_backend == "abb_moveit"
            and step.get("type") == "move_joints"
        )

    def _uses_real_action(self, step: dict) -> bool:
        return (
            not self.node.simulation_mode
            and self.node.motion_backend != "abb_moveit"
            and step.get("type") == "move_joints"
        )

    def _update_real_move_joints(self, step: dict, total_steps: int) -> py_trees.common.Status:
        if not MOVEIT_AVAILABLE or self._move_group_client is None:
            self.bb_set(bb_keys.ARM_BUSY, False)
            self.set_status(
                mode="ERROR",
                message="MoveIt unavailable for real sequence step",
                error_code="MOVEIT_UNAVAILABLE",
            )
            return py_trees.common.Status.FAILURE

        values_deg = [float(value) for value in step.get("joint_values_deg", [])]
        self._set_real_move_status(total_steps)

        if self._send_future is None:
            if not self._wait_for_action_server(self._move_group_client, "move_group"):
                if self._wait_error is not None:
                    message, code = self._wait_error
                    self.bb_set(bb_keys.ARM_BUSY, False)
                    self.set_status(mode="ERROR", message=message, error_code=code)
                    return py_trees.common.Status.FAILURE
                return py_trees.common.Status.RUNNING
            self._send_future = self._move_group_client.send_goal_async(
                self._build_move_group_joint_goal(values_deg)
            )
            return py_trees.common.Status.RUNNING

        if self._goal_handle is None:
            if not self._send_future.done():
                return py_trees.common.Status.RUNNING
            self._goal_handle = self._send_future.result()
            if not self._goal_handle.accepted:
                self.bb_set(bb_keys.ARM_BUSY, False)
                self.set_status(mode="ERROR", message="Sequence MoveGroup goal rejected", error_code="GOAL_REJECTED")
                return py_trees.common.Status.FAILURE
            self._result_future = self._goal_handle.get_result_async()
            return py_trees.common.Status.RUNNING

        if self._result_future is None or not self._result_future.done():
            return py_trees.common.Status.RUNNING

        result = self._result_future.result().result
        if result.error_code.val != MoveItErrorCodes.SUCCESS:
            self.bb_set(bb_keys.ARM_BUSY, False)
            self.set_status(
                mode="ERROR",
                message=f"Sequence MoveGroup failed: {result.error_code.val}",
                error_code="SEQUENCE_MOVEIT_FAILED",
            )
            return py_trees.common.Status.FAILURE

        self.bb_set(bb_keys.JOINT_STATE_DEG, values_deg)
        self._index += 1
        self._step_start = self.now()
        self._reset_motion_state()
        progress = self._index / max(1, total_steps)
        self.set_status(
            mode="WEB_SEQUENCE",
            message=f"Sequence joint step {self._index}/{total_steps} complete",
            progress=progress,
            error_code="",
        )
        return py_trees.common.Status.RUNNING

    def _update_action_move_joints(self, step: dict, total_steps: int) -> py_trees.common.Status:
        if self._action_client is None:
            self.bb_set(bb_keys.ARM_BUSY, False)
            self.set_status(
                mode="ERROR",
                message="MoveJoint action client unavailable",
                error_code="ACTION_CLIENT_UNAVAILABLE",
            )
            return py_trees.common.Status.FAILURE

        values_deg = [float(value) for value in step.get("joint_values_deg", [])]
        self._set_real_move_status(total_steps)

        if self._send_future is None:
            if not self._wait_for_action_server(self._action_client, "move_joint"):
                if self._wait_error is not None:
                    message, code = self._wait_error
                    self.bb_set(bb_keys.ARM_BUSY, False)
                    self.set_status(mode="ERROR", message=message, error_code=code)
                    return py_trees.common.Status.FAILURE
                return py_trees.common.Status.RUNNING

            goal_msg = MoveJoint.Goal()
            goal_msg.joint_values = values_deg
            goal_msg.max_velocity_scaling = float(self.node.velocity_scale)
            goal_msg.max_acceleration_scaling = float(self.node.velocity_scale) * 0.5
            self._send_future = self._action_client.send_goal_async(goal_msg)
            return py_trees.common.Status.RUNNING

        if self._goal_handle is None:
            if not self._send_future.done():
                return py_trees.common.Status.RUNNING
            self._goal_handle = self._send_future.result()
            if not self._goal_handle.accepted:
                self.bb_set(bb_keys.ARM_BUSY, False)
                self.set_status(mode="ERROR", message="Sequence MoveJoint goal rejected", error_code="GOAL_REJECTED")
                return py_trees.common.Status.FAILURE
            self._result_future = self._goal_handle.get_result_async()
            return py_trees.common.Status.RUNNING

        if self._result_future is None or not self._result_future.done():
            return py_trees.common.Status.RUNNING

        result = self._result_future.result().result
        if not result.success:
            self.bb_set(bb_keys.ARM_BUSY, False)
            self.set_status(
                mode="ERROR",
                message=result.message,
                error_code="SEQUENCE_MOVE_JOINT_FAILED",
            )
            return py_trees.common.Status.FAILURE

        self.bb_set(bb_keys.JOINT_STATE_DEG, values_deg)
        self._index += 1
        self._step_start = self.now()
        self._reset_motion_state()
        progress = self._index / max(1, total_steps)
        self.set_status(
            mode="WEB_SEQUENCE",
            message=f"Sequence joint step {self._index}/{total_steps} complete",
            progress=progress,
            error_code="",
        )
        return py_trees.common.Status.RUNNING

    def _set_real_move_status(self, total_steps: int) -> None:
        duration = max(0.1, float(self.node.simulation_motion_duration_s))
        elapsed = self.now() - (self._step_start or self.now())
        step_fraction = min(0.95, elapsed / duration)
        progress = (self._index + step_fraction) / max(1, total_steps)
        self.set_status(
            mode="WEB_SEQUENCE",
            message=f"Executing sequence joint step {self._index + 1}/{total_steps}",
            progress=progress,
        )

    def _update_detect_objects(self, step: dict, total_steps: int) -> py_trees.common.Status:
        detections = list(self.bb_get(bb_keys.YOLO_DETECTIONS, []))
        if detections:
            self._index += 1
            self._step_start = self.now()
            progress = self._index / max(1, total_steps)
            self.set_status(
                mode="WEB_SEQUENCE",
                message=f"Detected/classified {len(detections)} object(s)",
                progress=progress,
                error_code="",
            )
            return py_trees.common.Status.RUNNING

        timeout_s = float(
            step.get("timeout_s", getattr(self.node, "detection_timeout_s", 2.0))
        )
        elapsed = self.now() - (self._step_start or self.now())
        progress = (self._index + min(0.95, elapsed / max(timeout_s, 0.1))) / max(
            1,
            total_steps,
        )
        if elapsed < timeout_s:
            self.set_status(
                mode="WEB_SEQUENCE",
                message="Waiting for object detections",
                progress=progress,
                error_code="",
            )
            return py_trees.common.Status.RUNNING

        self.bb_set(bb_keys.ARM_BUSY, False)
        self.set_status(
            mode="ERROR",
            message="No object detections available",
            error_code="NO_DETECTIONS",
        )
        return py_trees.common.Status.FAILURE

    def _update_perception_pose(self, total_steps: int) -> py_trees.common.Status:
        for _ in self._perception_pose_behavior.tick():
            pass
        status = self._perception_pose_behavior.status

        if status == py_trees.common.Status.RUNNING:
            progress = (self._index + 0.5) / max(1, total_steps)
            self.set_status(
                mode="WEB_SEQUENCE",
                message=f"Moving to perception pose '{self.node.perception_group_state_name}'",
                progress=progress,
                error_code="",
            )
            return py_trees.common.Status.RUNNING

        self._perception_pose_behavior.stop(py_trees.common.Status.INVALID)
        if status == py_trees.common.Status.FAILURE:
            self.bb_set(bb_keys.ARM_BUSY, False)
            return py_trees.common.Status.FAILURE

        self._index += 1
        self._step_start = self.now()
        self._reset_motion_state()
        self.set_status(
            mode="WEB_SEQUENCE",
            message=f"Reached perception pose '{self.node.perception_group_state_name}'",
            progress=self._index / max(1, total_steps),
            error_code="",
        )
        return py_trees.common.Status.RUNNING

    def _snapshot_classifiable(self) -> list:
        """Congela las detecciones clasificables (poses fijas) una sola vez.

        Filtra por las clases con dropzone (node.class_to_zone), confianza y
        profundidad valida; deduplica detecciones del mismo objeto (varios
        frames) por cercania en XY; ordena por cercania para un pick eficiente.
        """
        classifiable = set(getattr(self.node, "class_to_zone", {}).keys())
        threshold = float(self.node.confidence_threshold)
        raw = list(self.bb_get(bb_keys.YOLO_DETECTIONS, []))
        cand = []
        for detection in raw:
            if detection.class_name.lower().strip() not in classifiable:
                continue
            if detection.confidence < threshold:
                continue
            if not getattr(detection, "has_valid_depth", True):
                continue

            pose_base = base_pose_for_detection(self.node, detection)
            if pose_base is None:
                self.node.get_logger().warn(
                    "Classify: descartando deteccion sin pose en base_link "
                    f"({detection.color} {detection.class_name})",
                    throttle_duration_sec=2.0,
                )
                continue

            normalized = copy.deepcopy(detection)
            normalized.pose_base = pose_base
            cand.append(normalized)
        distinct: list = []
        for d in sorted(cand, key=lambda x: -x.confidence):
            p = d.pose_base.pose.position
            dup = any(
                e.class_name == d.class_name
                and math.hypot(
                    p.x - e.pose_base.pose.position.x,
                    p.y - e.pose_base.pose.position.y,
                ) < 0.04
                for e in distinct
            )
            if not dup:
                distinct.append(d)
        distinct.sort(key=lambda d: math.hypot(
            d.pose_base.pose.position.x, d.pose_base.pose.position.y))
        return distinct

    def _normalise_detection_pose(self, detection):
        pose_base = base_pose_for_detection(self.node, detection)
        if pose_base is None:
            return None
        normalized = copy.deepcopy(detection)
        normalized.pose_base = pose_base
        return normalized

    def _find_give_to_hand_targets(self, step: dict) -> tuple[object | None, PoseStamped | None, str]:
        command = self.bb_get(bb_keys.CURRENT_COMMAND)
        target_class = str(step.get("object_class", "")).strip().lower()
        target_color = str(step.get("object_color", "")).strip().lower()
        if command is not None:
            target_class = str(command.object_class or target_class).strip().lower()
            target_color = str(command.object_color or target_color).strip().lower()

        if not target_class:
            return None, None, "GIVE_TO_HAND requires object_class"

        threshold = float(self.node.confidence_threshold)
        hand_classes = set(getattr(self.node, "hand_class_names", {"hand", "mano"}))
        objects = []
        hands = []
        for detection in list(self.bb_get(bb_keys.YOLO_DETECTIONS, [])):
            class_name = detection.class_name.lower().strip()
            if detection.confidence < threshold or not getattr(detection, "has_valid_depth", True):
                continue
            normalized = self._normalise_detection_pose(detection)
            if normalized is None:
                continue
            if class_name in hand_classes:
                hands.append(normalized)
                continue
            color_ok = not target_color or detection.color.lower().strip() == target_color
            if class_name == target_class and color_ok:
                objects.append(normalized)

        if not objects:
            label = f"{target_color} {target_class}".strip()
            return None, None, f"No object found for give_to_hand: {label}"
        if not hands:
            return None, None, "No hand detection found for give_to_hand"

        selected_object = min(
            objects,
            key=lambda d: math.hypot(d.pose_base.pose.position.x, d.pose_base.pose.position.y),
        )
        selected_hand = max(hands, key=lambda d: d.confidence)
        place = copy.deepcopy(selected_hand.pose_base)
        place.header.frame_id = self.node.base_frame
        place.pose.position.z += float(getattr(self.node, "hand_place_offset_z", 0.08))
        return selected_object, place, ""

    def _update_give_to_hand(self, step: dict, total_steps: int) -> py_trees.common.Status:
        if not self._give_to_hand_started:
            self._give_to_hand_started = True
            selected_object, place_pose, error = self._find_give_to_hand_targets(step)
            if error:
                self.bb_set(bb_keys.ARM_BUSY, False)
                self.set_status(mode="ERROR", message=error, error_code="GIVE_TO_HAND_TARGET_MISSING")
                return py_trees.common.Status.FAILURE

            self.bb_set(bb_keys.SELECTED_OBJECT, selected_object)
            self.bb_set(bb_keys.SELECTED_OBJECT_POSE_BASE, copy.deepcopy(selected_object.pose_base))
            self.bb_set(bb_keys.PLACE_POSE_OVERRIDE, place_pose)
            self._give_to_hand_target = selected_object.class_name
            if self._give_to_hand_subtree is None:
                self._give_to_hand_subtree = build_grasp_place_subtree(self.node, "GiveToHandGraspPlace")
                self._give_to_hand_subtree.setup_with_descendants()
            p = place_pose.pose.position
            self.node.get_logger().info(
                f"GiveToHand: {selected_object.color} {selected_object.class_name} "
                f"-> hand centroid ({p.x:.3f}, {p.y:.3f}, {p.z:.3f})"
            )

        for _ in self._give_to_hand_subtree.tick():
            pass
        status = self._give_to_hand_subtree.status

        if status == py_trees.common.Status.RUNNING:
            progress = (self._index + 0.5) / max(1, total_steps)
            self.set_status(
                mode="WEB_SEQUENCE",
                message=f"Entregando {self._give_to_hand_target} a la mano",
                progress=min(0.99, progress),
            )
            return py_trees.common.Status.RUNNING

        self._give_to_hand_subtree.stop(py_trees.common.Status.INVALID)
        self.bb_set(bb_keys.PLACE_POSE_OVERRIDE, None)
        self._give_to_hand_started = False
        if status == py_trees.common.Status.FAILURE:
            self.bb_set(bb_keys.ARM_BUSY, False)
            self.set_status(
                mode="ERROR",
                message=f"Give to hand fallo para {self._give_to_hand_target}",
                error_code="GIVE_TO_HAND_FAILED",
            )
            return py_trees.common.Status.FAILURE

        self._index += 1
        self._step_start = self.now()
        self._reset_motion_state()
        self.set_status(
            mode="WEB_SEQUENCE",
            message=f"Objeto entregado a la mano: {self._give_to_hand_target}",
            progress=self._index / max(1, total_steps),
            error_code="",
        )
        return py_trees.common.Status.RUNNING

    def _update_classify(self, step: dict, total_steps: int) -> py_trees.common.Status:
        """Clasifica todos los objetos detectados (poses fijas, sin re-detectar).

        Snapshot unico de apple/cube; por cada uno fija su pose/clase en el
        blackboard y corre el subarbol grasp&place (routing por clase via
        resolve_place_zone). Termina cuando se procesaron todos.
        """
        if not self._classify_started:
            self._classify_started = True
            self._classify_queue = self._snapshot_classifiable()
            self._classify_index = 0
            self._classify_current = -1
            if self._classify_subtree is None:
                self._classify_subtree = build_grasp_place_subtree(self.node, "ClassifyGraspPlace")
                self._classify_subtree.setup_with_descendants()
            self.node.get_logger().info(
                f"Classify: {len(self._classify_queue)} objeto(s) clasificable(s)"
            )

        queue = self._classify_queue or []
        if self._classify_index >= len(queue):
            self._finish_step(step)
            self._index += 1
            self._step_start = self.now()
            self._reset_motion_state()
            self.set_status(
                mode="WEB_SEQUENCE",
                message=f"Classify completo: {len(queue)} objeto(s)",
                progress=self._index / max(1, total_steps),
                error_code="",
            )
            return py_trees.common.Status.RUNNING

        obj = queue[self._classify_index]
        if self._classify_current != self._classify_index:
            self._classify_current = self._classify_index
            pose_base = copy.deepcopy(obj.pose_base)
            pose_base.header.frame_id = self.node.base_frame
            self.bb_set(bb_keys.SELECTED_OBJECT, obj)
            self.bb_set(bb_keys.SELECTED_OBJECT_POSE_BASE, pose_base)
            self.node.get_logger().info(
                f"Classify {self._classify_index + 1}/{len(queue)}: "
                f"{obj.color} {obj.class_name}"
            )

        for _ in self._classify_subtree.tick():
            pass
        status = self._classify_subtree.status

        if status == py_trees.common.Status.RUNNING:
            prog = (self._index + (self._classify_index + 0.5) / max(1, len(queue))) / max(1, total_steps)
            self.set_status(
                mode="WEB_SEQUENCE",
                message=f"Clasificando {self._classify_index + 1}/{len(queue)}: {obj.class_name}",
                progress=min(0.99, prog),
            )
            return py_trees.common.Status.RUNNING

        # Termino este objeto; reset del subarbol para el siguiente.
        self._classify_subtree.stop(py_trees.common.Status.INVALID)
        if status == py_trees.common.Status.FAILURE:
            self.bb_set(bb_keys.ARM_BUSY, False)
            self.set_status(
                mode="ERROR",
                message=(
                    f"Classify fallo en {obj.class_name} "
                    f"({self._classify_index + 1}/{len(queue)})"
                ),
                error_code="CLASSIFY_PICK_FAILED",
            )
            return py_trees.common.Status.FAILURE

        self._classify_index += 1
        return py_trees.common.Status.RUNNING

    def _step_duration(self, step: dict) -> float:
        step_type = step.get("type")
        if step_type == "detect_objects":
            return 0.0
        if step_type == "gripper":
            return float(self.node.gripper_motion_duration_s)
        if step_type == "pick_object":
            return 1.0
        return float(self.node.simulation_motion_duration_s)

    def _publish_step_start(self, step: dict) -> None:
        if self._published_step == self._index:
            return
        self._published_step = self._index

        step_type = step.get("type")
        if step_type == "gripper":
            command = step.get("command", "open")
            self.node.publish_gripper_command(command)
            self.node.get_logger().info(f"Sequence gripper command: {command}")
        elif step_type == "move_joints":
            self.node.get_logger().info(f"Sequence move_joints: {step.get('joint_values_deg')}")
        elif step_type == "pick_object":
            self.node.get_logger().info(
                "Sequence pick_object: "
                f"{step.get('object_color', '')} {step.get('object_class', '')}"
            )
        elif step_type == "detect_objects":
            self.node.get_logger().info(
                "Sequence detect_objects: waiting for classified detections"
            )
        elif step_type == "perception_pose":
            self.node.get_logger().info(
                f"Sequence perception_pose: moving to '{self.node.perception_group_state_name}'"
            )
        elif step_type == "classify":
            self.node.get_logger().info(
                "Sequence classify: agarrando todos los objetos a su dropzone"
            )
        elif step_type == "give_to_hand":
            self.node.get_logger().info("Sequence give_to_hand: entregando objeto a mano")

    def _finish_step(self, step: dict) -> None:
        if step.get("type") == "move_joints":
            self.bb_set(bb_keys.JOINT_STATE_DEG, [float(v) for v in step.get("joint_values_deg", [])])

    def _build_move_group_joint_goal(self, values_deg: list[float]):
        goal_msg = MoveGroup.Goal()
        request = MotionPlanRequest()
        request.group_name = self.node.planning_group
        request.num_planning_attempts = 5
        request.allowed_planning_time = self.node.planning_time
        request.max_velocity_scaling_factor = self.node.velocity_scale
        request.max_acceleration_scaling_factor = self.node.velocity_scale * 0.5
        request.workspace_parameters.header.frame_id = self.node.base_frame
        request.workspace_parameters.min_corner.x = self.node.workspace_min_x
        request.workspace_parameters.min_corner.y = self.node.workspace_min_y
        request.workspace_parameters.min_corner.z = self.node.workspace_min_z
        request.workspace_parameters.max_corner.x = self.node.workspace_max_x
        request.workspace_parameters.max_corner.y = self.node.workspace_max_y
        request.workspace_parameters.max_corner.z = self.node.workspace_max_z

        constraints = Constraints()
        for name, value_deg in zip(self.node.joint_names, values_deg):
            joint_constraint = JointConstraint()
            joint_constraint.joint_name = name
            joint_constraint.position = math.radians(float(value_deg))
            joint_constraint.tolerance_above = math.radians(1.0)
            joint_constraint.tolerance_below = math.radians(1.0)
            joint_constraint.weight = 1.0
            constraints.joint_constraints.append(joint_constraint)
        request.goal_constraints.append(constraints)

        goal_msg.request = request
        goal_msg.planning_options.plan_only = False
        goal_msg.planning_options.replan = True
        goal_msg.planning_options.replan_attempts = 3
        return goal_msg

    def _wait_for_action_server(self, client, label: str) -> bool:
        if client.server_is_ready():
            return True
        elapsed = self.now() - (self._step_start or self.now())
        if elapsed > self.node.action_server_timeout_s:
            self._wait_error = (f"{label} action server timeout", "ACTION_SERVER_TIMEOUT")
            return False
        self.set_status(mode="WEB_SEQUENCE", message=f"Waiting for {label}", progress=0.10)
        return False

    def _reset_motion_state(self) -> None:
        self._send_future = None
        self._result_future = None
        self._goal_handle = None
        self._wait_error = None

    def terminate(self, new_status: py_trees.common.Status) -> None:
        if new_status == py_trees.common.Status.INVALID:
            if self._goal_handle is not None:
                self._goal_handle.cancel_goal_async()
            # Propaga la invalidacion al subarbol de classify para que sus
            # behaviours cancelen sus goals de MoveIt ante un ESTOP/cancel.
            if self._classify_subtree is not None:
                self._classify_subtree.stop(py_trees.common.Status.INVALID)
            self._perception_pose_behavior.stop(py_trees.common.Status.INVALID)
            if self._give_to_hand_subtree is not None:
                self._give_to_hand_subtree.stop(py_trees.common.Status.INVALID)
            self.bb_set(bb_keys.PLACE_POSE_OVERRIDE, None)
            self.bb_set(bb_keys.ARM_BUSY, False)
