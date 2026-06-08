"""Perception and pick-pose planning behaviours."""

from __future__ import annotations

import copy
import math

import py_trees
from geometry_msgs.msg import PoseStamped
from rclpy.duration import Duration
from rclpy.time import Time

from robot_task_manager import blackboard_keys as bb_keys
from robot_task_manager.behaviors.common import BlackboardBehavior
from robot_task_msgs.msg import Detection3D


def _pose(frame_id: str, x: float, y: float, z: float) -> PoseStamped:
    pose = PoseStamped()
    pose.header.frame_id = frame_id
    pose.pose.position.x = x
    pose.pose.position.y = y
    pose.pose.position.z = z
    pose.pose.orientation.w = 1.0
    return pose


def base_pose_for_detection(node, detection: Detection3D) -> PoseStamped | None:
    """Return a detection pose in the robot base frame, using TF if needed."""
    pose_base = copy.deepcopy(detection.pose_base)
    if pose_base.header.frame_id:
        pose_base.header.frame_id = node.base_frame
        return pose_base

    pose_camera = copy.deepcopy(detection.pose_camera)
    if not pose_camera.header.frame_id:
        return None

    if node.simulation_mode:
        pose_base = copy.deepcopy(pose_camera)
        pose_base.header.frame_id = node.base_frame
        return pose_base

    if getattr(node, "tf_buffer", None) is None:
        return None

    try:
        stamp = Time()
        if pose_camera.header.stamp.sec != 0 or pose_camera.header.stamp.nanosec != 0:
            stamp = Time.from_msg(pose_camera.header.stamp)
        transform = node.tf_buffer.lookup_transform(
            node.base_frame,
            pose_camera.header.frame_id,
            stamp,
            timeout=Duration(seconds=float(node.tf_timeout_s)),
        )
        from tf2_geometry_msgs import do_transform_pose

        pose_base = PoseStamped()
        pose_base.header.frame_id = node.base_frame
        pose_base.header.stamp = pose_camera.header.stamp
        pose_base.pose = do_transform_pose(pose_camera.pose, transform)
        return pose_base
    except Exception as exc:  # noqa: BLE001 - TF failures are surfaced as status.
        node.get_logger().warn(f"TF transform failed: {exc}", throttle_duration_sec=2.0)
        return None


class DetectObjectsYOLO(BlackboardBehavior):
    """Collect recent YOLO/depth detections or create simulation detections."""

    def update(self) -> py_trees.common.Status:
        detections = list(self.bb_get(bb_keys.YOLO_DETECTIONS, []))
        last_detection_time = getattr(self.node, "_last_detection_time", 0.0)
        if (
            detections
            and not self.node.simulation_mode
            and self.now() - float(last_detection_time) > float(self.node.detection_timeout_s)
        ):
            detections = []
            self.bb_set(bb_keys.YOLO_DETECTIONS, [])

        if not detections and self.node.simulation_mode:
            detections = self._mock_detections()
            self.bb_set(bb_keys.YOLO_DETECTIONS, detections)

        if not detections:
            self.set_status(mode="VOICE_PICK", message="No YOLO detections available", error_code="NO_DETECTIONS")
            return py_trees.common.Status.FAILURE

        self.set_status(
            mode="VOICE_PICK",
            message=f"Received {len(detections)} detections",
            progress=0.20,
            error_code="",
        )
        return py_trees.common.Status.SUCCESS

    def _mock_detections(self) -> list[Detection3D]:
        stamp = self.node.get_clock().now().to_msg()
        cube = Detection3D()
        cube.header.stamp = stamp
        cube.header.frame_id = "camera_depth_frame"
        cube.class_name = "cube"
        cube.color = "blue"
        cube.confidence = 0.92
        cube.bbox_x = 120
        cube.bbox_y = 80
        cube.bbox_width = 70
        cube.bbox_height = 70
        cube.pose_camera = _pose("camera_depth_frame", 0.40, 0.10, 0.20)
        cube.pose_base = _pose("base_link", 0.40, 0.10, 0.20)
        cube.has_valid_depth = True

        bottle = Detection3D()
        bottle.header.stamp = stamp
        bottle.header.frame_id = "camera_depth_frame"
        bottle.class_name = "bottle"
        bottle.color = "red"
        bottle.confidence = 0.88
        bottle.bbox_x = 260
        bottle.bbox_y = 95
        bottle.bbox_width = 45
        bottle.bbox_height = 110
        bottle.pose_camera = _pose("camera_depth_frame", 0.50, -0.10, 0.20)
        bottle.pose_base = _pose("base_link", 0.50, -0.10, 0.20)
        bottle.has_valid_depth = True
        return [cube, bottle]


class SelectObjectByClassAndColor(BlackboardBehavior):
    """Filter detections matching the command class/color.

    The final target is selected after TF, matching the working task2.py
    behaviour that picks the closest object in base_link XY.
    """

    def update(self) -> py_trees.common.Status:
        command = self.bb_get(bb_keys.CURRENT_COMMAND)
        detections = list(self.bb_get(bb_keys.YOLO_DETECTIONS, []))
        if command is None:
            self.set_status(mode="ERROR", message="No pick command", error_code="NO_COMMAND")
            return py_trees.common.Status.FAILURE

        target_class = command.object_class.lower().strip()
        target_color = command.object_color.lower().strip()
        threshold = float(self.node.confidence_threshold)

        candidates = []
        for detection in detections:
            class_ok = detection.class_name.lower() == target_class
            color_ok = not target_color or detection.color.lower() == target_color
            if class_ok and color_ok and detection.confidence >= threshold and detection.has_valid_depth:
                candidates.append(detection)

        if not candidates:
            self.set_status(
                mode="VOICE_PICK",
                message=f"No matching object: {target_class} {target_color}".strip(),
                error_code="OBJECT_NOT_FOUND",
            )
            return py_trees.common.Status.FAILURE

        self.bb_set(bb_keys.CANDIDATE_OBJECTS, candidates)
        selected = max(candidates, key=lambda detection: detection.confidence)
        self.bb_set(bb_keys.SELECTED_OBJECT, selected)
        self.set_status(
            mode="VOICE_PICK",
            message=f"Found {len(candidates)} matching object(s)",
            progress=0.30,
            error_code="",
        )
        return py_trees.common.Status.SUCCESS


class EstimateObject3DPose(BlackboardBehavior):
    """Extract or mock the selected object's camera-frame 3D pose."""

    def update(self) -> py_trees.common.Status:
        selected = self.bb_get(bb_keys.SELECTED_OBJECT)
        if selected is None:
            self.set_status(mode="VOICE_PICK", message="No selected object", error_code="NO_SELECTED_OBJECT")
            return py_trees.common.Status.FAILURE

        pose = copy.deepcopy(selected.pose_camera)
        if not pose.header.frame_id:
            if not self.node.simulation_mode:
                self.set_status(mode="ERROR", message="Missing camera pose", error_code="NO_CAMERA_POSE")
                return py_trees.common.Status.FAILURE
            pose = _pose("camera_depth_frame", 0.40, 0.0, 0.20)

        self.bb_set(bb_keys.SELECTED_OBJECT_POSE_CAMERA, pose)
        self.set_status(mode="VOICE_PICK", message="Estimated object 3D pose", progress=0.40)
        return py_trees.common.Status.SUCCESS


class TransformPoseToRobotBase(BlackboardBehavior):
    """Transform candidates to base_link and select the nearest XY target."""

    def update(self) -> py_trees.common.Status:
        candidates = list(self.bb_get(bb_keys.CANDIDATE_OBJECTS, []))
        if not candidates:
            selected = self.bb_get(bb_keys.SELECTED_OBJECT)
            candidates = [selected] if selected is not None else []

        if not candidates:
            self.set_status(mode="VOICE_PICK", message="No target candidates", error_code="NO_SELECTED_OBJECT")
            return py_trees.common.Status.FAILURE

        transformed = []
        for detection in candidates:
            pose_base = self._base_pose_for_detection(detection)
            if pose_base is not None:
                transformed.append((detection, pose_base))

        if not transformed:
            self.set_status(
                mode="ERROR",
                message="No TF/base pose available",
                error_code="TF_UNAVAILABLE",
            )
            return py_trees.common.Status.FAILURE

        selected, pose_base = min(
            transformed,
            key=lambda item: math.hypot(item[1].pose.position.x, item[1].pose.position.y),
        )

        self.bb_set(bb_keys.SELECTED_OBJECT, selected)
        self.bb_set(bb_keys.SELECTED_OBJECT_POSE_BASE, pose_base)
        p = pose_base.pose.position
        self.set_status(
            mode="VOICE_PICK",
            message=f"Selected {selected.color} {selected.class_name} at ({p.x:.3f}, {p.y:.3f}, {p.z:.3f})",
            progress=0.50,
            error_code="",
        )
        return py_trees.common.Status.SUCCESS

    def _base_pose_for_detection(self, detection: Detection3D) -> PoseStamped | None:
        return base_pose_for_detection(self.node, detection)


class ValidateObjectWorkspace(BlackboardBehavior):
    """Reject object poses outside configured workspace limits."""

    def update(self) -> py_trees.common.Status:
        pose = self.bb_get(bb_keys.SELECTED_OBJECT_POSE_BASE)
        if pose is None:
            self.set_status(mode="VOICE_PICK", message="No base pose to validate", error_code="NO_BASE_POSE")
            return py_trees.common.Status.FAILURE

        p = pose.pose.position
        inside = (
            self.node.workspace_min_x <= p.x <= self.node.workspace_max_x
            and self.node.workspace_min_y <= p.y <= self.node.workspace_max_y
            and self.node.workspace_min_z <= p.z <= self.node.workspace_max_z
        )
        if not inside:
            self.set_status(
                mode="ERROR",
                message=f"Object outside workspace: ({p.x:.2f}, {p.y:.2f}, {p.z:.2f})",
                error_code="WORKSPACE_LIMIT",
            )
            return py_trees.common.Status.FAILURE

        self.set_status(mode="VOICE_PICK", message="Object inside workspace", progress=0.55)
        return py_trees.common.Status.SUCCESS


class PlanPreGraspPose(BlackboardBehavior):
    """Create pre-grasp, grasp, retreat, and place poses."""

    def update(self) -> py_trees.common.Status:
        object_pose = self.bb_get(bb_keys.SELECTED_OBJECT_POSE_BASE)
        command = self.bb_get(bb_keys.CURRENT_COMMAND)
        if object_pose is None:
            self.set_status(mode="ERROR", message="No object pose for grasp planning", error_code="NO_BASE_POSE")
            return py_trees.common.Status.FAILURE

        pre_grasp = copy.deepcopy(object_pose)
        pre_grasp.pose.position.z += float(self.node.pregrasp_offset_z)

        grasp = copy.deepcopy(object_pose)
        grasp.pose.position.z += float(self.node.grasp_offset_z)

        retreat = copy.deepcopy(grasp)
        retreat.pose.position.z += float(self.node.retreat_offset_z)

        selected = self.bb_get(bb_keys.SELECTED_OBJECT)
        object_class = getattr(selected, "class_name", "") if selected is not None else ""
        place_override = self.bb_get(bb_keys.PLACE_POSE_OVERRIDE)
        if place_override is not None:
            place = copy.deepcopy(place_override)
            place.header.frame_id = self.node.base_frame
            p = place.pose.position
            self.node.get_logger().info(
                f"Place de '{object_class or 'desconocido'}' -> override "
                f"({p.x:.2f}, {p.y:.2f}, {p.z:.2f})"
            )
        else:
            # La dropzone se elige por la clase del objeto agarrado:
            # manzana -> hueco, cubo -> caja, lo demas -> default.
            zone, (place_x, place_y, place_z) = self.node.resolve_place_zone(object_class)
            place = _pose("base_link", place_x, place_y, place_z)
            self.node.get_logger().info(
                f"Place de '{object_class or 'desconocido'}' -> dropzone '{zone}' "
                f"({place_x:.2f}, {place_y:.2f}, {place_z:.2f})"
            )
        if command is not None and command.place_target:
            # A real system would look this target up in a scene database.
            self.node.get_logger().info(f"Using configured mock place target: {command.place_target}")

        post_place_retreat = copy.deepcopy(place)
        post_place_retreat.pose.position.z += float(self.node.post_place_retreat_offset_z)

        if self.node.use_top_down_grasp_orientation:
            for pose in (pre_grasp, grasp, retreat, place, post_place_retreat):
                pose.pose.orientation.x = self.node.top_down_qx
                pose.pose.orientation.y = self.node.top_down_qy
                pose.pose.orientation.z = self.node.top_down_qz
                pose.pose.orientation.w = self.node.top_down_qw

        self.bb_set(bb_keys.PRE_GRASP_POSE, pre_grasp)
        self.bb_set(bb_keys.GRASP_POSE, grasp)
        self.bb_set(bb_keys.RETREAT_POSE, retreat)
        self.bb_set(bb_keys.PLACE_POSE, place)
        self.bb_set(bb_keys.POST_PLACE_RETREAT_POSE, post_place_retreat)
        self.set_status(mode="VOICE_PICK", message="Planned grasp and place poses", progress=0.60)
        return py_trees.common.Status.SUCCESS
