"""Subarbol reutilizable de grasp & place (sin percepcion).

Toma el objeto YA seleccionado en el blackboard (SELECTED_OBJECT con su
class_name + SELECTED_OBJECT_POSE_BASE) y ejecuta: validar workspace ->
planear poses (grasp + dropzone por clase, via resolve_place_zone) ->
abrir -> pre-grasp -> grasp -> cerrar -> retreat -> place -> abrir ->
retreat post-place.

Lo usa el paso `classify` de las secuencias para procesar objeto por objeto
con poses fijas (no re-detecta entre picks).
"""

import py_trees

from robot_task_manager.behaviors.gripper_behaviors import CloseGripper, OpenGripper
from robot_task_manager.behaviors.motion_behaviors import (
    MoveToGrasp,
    MoveToPlacePose,
    MovePostPlaceRetreat,
    MoveToPreGrasp,
    Retreat,
)
from robot_task_manager.behaviors.yolo_behaviors import (
    PlanPreGraspPose,
    ValidateObjectWorkspace,
)


def build_grasp_place_subtree(node, name: str = "GraspPlace") -> py_trees.composites.Sequence:
    """Grasp + place de UN objeto ya fijado en el blackboard.

    Requiere que el llamador deje en el blackboard, antes de tickear:
      - SELECTED_OBJECT            (con .class_name para el routing de dropzone)
      - SELECTED_OBJECT_POSE_BASE  (PoseStamped en base_link del objeto)
    """
    return py_trees.composites.Sequence(
        name=name,
        memory=True,
        children=[
            ValidateObjectWorkspace("ValidateObjectWorkspace", node),
            PlanPreGraspPose("PlanPreGraspPose", node),
            OpenGripper("OpenGripperApproach", node),
            MoveToPreGrasp("MoveToPreGrasp", node),
            MoveToGrasp("MoveToGrasp", node),
            CloseGripper("CloseGripper", node),
            Retreat("Retreat", node),
            MoveToPlacePose("MoveToPlacePose", node),
            OpenGripper("OpenGripperRelease", node),
            MovePostPlaceRetreat("MovePostPlaceRetreat", node),
        ],
    )
