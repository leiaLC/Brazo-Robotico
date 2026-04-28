// NOLINT: This file starts with a BOM since it contain non-ASCII characters
// generated from rosidl_generator_c/resource/idl__struct.h.em
// with input from robot_interfaces:msg/DetectedObject.idl
// generated code does not contain a copyright notice

// IWYU pragma: private, include "robot_interfaces/msg/detected_object.h"


#ifndef ROBOT_INTERFACES__MSG__DETAIL__DETECTED_OBJECT__STRUCT_H_
#define ROBOT_INTERFACES__MSG__DETAIL__DETECTED_OBJECT__STRUCT_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

// Constants defined in the message

// Include directives for member types
// Member 'header'
#include "std_msgs/msg/detail/header__struct.h"
// Member 'label'
#include "rosidl_runtime_c/string.h"
// Member 'mask'
#include "rosidl_runtime_c/primitives_sequence.h"

/// Struct defined in msg/DetectedObject in the package robot_interfaces.
typedef struct robot_interfaces__msg__DetectedObject
{
  std_msgs__msg__Header header;
  int32_t class_id;
  rosidl_runtime_c__String label;
  float confidence;
  float bbox_x1;
  float bbox_y1;
  float bbox_x2;
  float bbox_y2;
  float center_u;
  float center_v;
  /// Máscara de segmentación aplanada (row-major, valores 0.0-1.0)
  /// Reshape a (mask_height, mask_width) para usarla
  rosidl_runtime_c__float__Sequence mask;
  int32_t mask_width;
  int32_t mask_height;
  /// Depth (lo llena depth_estimator, vacío al salir de yolo_node)
  float x;
  float y;
  float z;
  bool depth_valid;
} robot_interfaces__msg__DetectedObject;

// Struct for a sequence of robot_interfaces__msg__DetectedObject.
typedef struct robot_interfaces__msg__DetectedObject__Sequence
{
  robot_interfaces__msg__DetectedObject * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} robot_interfaces__msg__DetectedObject__Sequence;

#ifdef __cplusplus
}
#endif

#endif  // ROBOT_INTERFACES__MSG__DETAIL__DETECTED_OBJECT__STRUCT_H_
