// generated from rosidl_generator_c/resource/idl__functions.c.em
// with input from robot_interfaces:msg/DetectedObject.idl
// generated code does not contain a copyright notice
#include "robot_interfaces/msg/detail/detected_object__functions.h"

#include <assert.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>

#include "rcutils/allocator.h"


// Include directives for member types
// Member `header`
#include "std_msgs/msg/detail/header__functions.h"
// Member `label`
#include "rosidl_runtime_c/string_functions.h"
// Member `mask`
#include "rosidl_runtime_c/primitives_sequence_functions.h"

bool
robot_interfaces__msg__DetectedObject__init(robot_interfaces__msg__DetectedObject * msg)
{
  if (!msg) {
    return false;
  }
  // header
  if (!std_msgs__msg__Header__init(&msg->header)) {
    robot_interfaces__msg__DetectedObject__fini(msg);
    return false;
  }
  // class_id
  // label
  if (!rosidl_runtime_c__String__init(&msg->label)) {
    robot_interfaces__msg__DetectedObject__fini(msg);
    return false;
  }
  // confidence
  // bbox_x1
  // bbox_y1
  // bbox_x2
  // bbox_y2
  // center_u
  // center_v
  // mask
  if (!rosidl_runtime_c__float__Sequence__init(&msg->mask, 0)) {
    robot_interfaces__msg__DetectedObject__fini(msg);
    return false;
  }
  // mask_width
  // mask_height
  // x
  // y
  // z
  // depth_valid
  return true;
}

void
robot_interfaces__msg__DetectedObject__fini(robot_interfaces__msg__DetectedObject * msg)
{
  if (!msg) {
    return;
  }
  // header
  std_msgs__msg__Header__fini(&msg->header);
  // class_id
  // label
  rosidl_runtime_c__String__fini(&msg->label);
  // confidence
  // bbox_x1
  // bbox_y1
  // bbox_x2
  // bbox_y2
  // center_u
  // center_v
  // mask
  rosidl_runtime_c__float__Sequence__fini(&msg->mask);
  // mask_width
  // mask_height
  // x
  // y
  // z
  // depth_valid
}

bool
robot_interfaces__msg__DetectedObject__are_equal(const robot_interfaces__msg__DetectedObject * lhs, const robot_interfaces__msg__DetectedObject * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  // header
  if (!std_msgs__msg__Header__are_equal(
      &(lhs->header), &(rhs->header)))
  {
    return false;
  }
  // class_id
  if (lhs->class_id != rhs->class_id) {
    return false;
  }
  // label
  if (!rosidl_runtime_c__String__are_equal(
      &(lhs->label), &(rhs->label)))
  {
    return false;
  }
  // confidence
  if (lhs->confidence != rhs->confidence) {
    return false;
  }
  // bbox_x1
  if (lhs->bbox_x1 != rhs->bbox_x1) {
    return false;
  }
  // bbox_y1
  if (lhs->bbox_y1 != rhs->bbox_y1) {
    return false;
  }
  // bbox_x2
  if (lhs->bbox_x2 != rhs->bbox_x2) {
    return false;
  }
  // bbox_y2
  if (lhs->bbox_y2 != rhs->bbox_y2) {
    return false;
  }
  // center_u
  if (lhs->center_u != rhs->center_u) {
    return false;
  }
  // center_v
  if (lhs->center_v != rhs->center_v) {
    return false;
  }
  // mask
  if (!rosidl_runtime_c__float__Sequence__are_equal(
      &(lhs->mask), &(rhs->mask)))
  {
    return false;
  }
  // mask_width
  if (lhs->mask_width != rhs->mask_width) {
    return false;
  }
  // mask_height
  if (lhs->mask_height != rhs->mask_height) {
    return false;
  }
  // x
  if (lhs->x != rhs->x) {
    return false;
  }
  // y
  if (lhs->y != rhs->y) {
    return false;
  }
  // z
  if (lhs->z != rhs->z) {
    return false;
  }
  // depth_valid
  if (lhs->depth_valid != rhs->depth_valid) {
    return false;
  }
  return true;
}

bool
robot_interfaces__msg__DetectedObject__copy(
  const robot_interfaces__msg__DetectedObject * input,
  robot_interfaces__msg__DetectedObject * output)
{
  if (!input || !output) {
    return false;
  }
  // header
  if (!std_msgs__msg__Header__copy(
      &(input->header), &(output->header)))
  {
    return false;
  }
  // class_id
  output->class_id = input->class_id;
  // label
  if (!rosidl_runtime_c__String__copy(
      &(input->label), &(output->label)))
  {
    return false;
  }
  // confidence
  output->confidence = input->confidence;
  // bbox_x1
  output->bbox_x1 = input->bbox_x1;
  // bbox_y1
  output->bbox_y1 = input->bbox_y1;
  // bbox_x2
  output->bbox_x2 = input->bbox_x2;
  // bbox_y2
  output->bbox_y2 = input->bbox_y2;
  // center_u
  output->center_u = input->center_u;
  // center_v
  output->center_v = input->center_v;
  // mask
  if (!rosidl_runtime_c__float__Sequence__copy(
      &(input->mask), &(output->mask)))
  {
    return false;
  }
  // mask_width
  output->mask_width = input->mask_width;
  // mask_height
  output->mask_height = input->mask_height;
  // x
  output->x = input->x;
  // y
  output->y = input->y;
  // z
  output->z = input->z;
  // depth_valid
  output->depth_valid = input->depth_valid;
  return true;
}

robot_interfaces__msg__DetectedObject *
robot_interfaces__msg__DetectedObject__create(void)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  robot_interfaces__msg__DetectedObject * msg = (robot_interfaces__msg__DetectedObject *)allocator.allocate(sizeof(robot_interfaces__msg__DetectedObject), allocator.state);
  if (!msg) {
    return NULL;
  }
  memset(msg, 0, sizeof(robot_interfaces__msg__DetectedObject));
  bool success = robot_interfaces__msg__DetectedObject__init(msg);
  if (!success) {
    allocator.deallocate(msg, allocator.state);
    return NULL;
  }
  return msg;
}

void
robot_interfaces__msg__DetectedObject__destroy(robot_interfaces__msg__DetectedObject * msg)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (msg) {
    robot_interfaces__msg__DetectedObject__fini(msg);
  }
  allocator.deallocate(msg, allocator.state);
}


bool
robot_interfaces__msg__DetectedObject__Sequence__init(robot_interfaces__msg__DetectedObject__Sequence * array, size_t size)
{
  if (!array) {
    return false;
  }
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  robot_interfaces__msg__DetectedObject * data = NULL;

  if (size) {
    data = (robot_interfaces__msg__DetectedObject *)allocator.zero_allocate(size, sizeof(robot_interfaces__msg__DetectedObject), allocator.state);
    if (!data) {
      return false;
    }
    // initialize all array elements
    size_t i;
    for (i = 0; i < size; ++i) {
      bool success = robot_interfaces__msg__DetectedObject__init(&data[i]);
      if (!success) {
        break;
      }
    }
    if (i < size) {
      // if initialization failed finalize the already initialized array elements
      for (; i > 0; --i) {
        robot_interfaces__msg__DetectedObject__fini(&data[i - 1]);
      }
      allocator.deallocate(data, allocator.state);
      return false;
    }
  }
  array->data = data;
  array->size = size;
  array->capacity = size;
  return true;
}

void
robot_interfaces__msg__DetectedObject__Sequence__fini(robot_interfaces__msg__DetectedObject__Sequence * array)
{
  if (!array) {
    return;
  }
  rcutils_allocator_t allocator = rcutils_get_default_allocator();

  if (array->data) {
    // ensure that data and capacity values are consistent
    assert(array->capacity > 0);
    // finalize all array elements
    for (size_t i = 0; i < array->capacity; ++i) {
      robot_interfaces__msg__DetectedObject__fini(&array->data[i]);
    }
    allocator.deallocate(array->data, allocator.state);
    array->data = NULL;
    array->size = 0;
    array->capacity = 0;
  } else {
    // ensure that data, size, and capacity values are consistent
    assert(0 == array->size);
    assert(0 == array->capacity);
  }
}

robot_interfaces__msg__DetectedObject__Sequence *
robot_interfaces__msg__DetectedObject__Sequence__create(size_t size)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  robot_interfaces__msg__DetectedObject__Sequence * array = (robot_interfaces__msg__DetectedObject__Sequence *)allocator.allocate(sizeof(robot_interfaces__msg__DetectedObject__Sequence), allocator.state);
  if (!array) {
    return NULL;
  }
  bool success = robot_interfaces__msg__DetectedObject__Sequence__init(array, size);
  if (!success) {
    allocator.deallocate(array, allocator.state);
    return NULL;
  }
  return array;
}

void
robot_interfaces__msg__DetectedObject__Sequence__destroy(robot_interfaces__msg__DetectedObject__Sequence * array)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (array) {
    robot_interfaces__msg__DetectedObject__Sequence__fini(array);
  }
  allocator.deallocate(array, allocator.state);
}

bool
robot_interfaces__msg__DetectedObject__Sequence__are_equal(const robot_interfaces__msg__DetectedObject__Sequence * lhs, const robot_interfaces__msg__DetectedObject__Sequence * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  if (lhs->size != rhs->size) {
    return false;
  }
  for (size_t i = 0; i < lhs->size; ++i) {
    if (!robot_interfaces__msg__DetectedObject__are_equal(&(lhs->data[i]), &(rhs->data[i]))) {
      return false;
    }
  }
  return true;
}

bool
robot_interfaces__msg__DetectedObject__Sequence__copy(
  const robot_interfaces__msg__DetectedObject__Sequence * input,
  robot_interfaces__msg__DetectedObject__Sequence * output)
{
  if (!input || !output) {
    return false;
  }
  if (output->capacity < input->size) {
    const size_t allocation_size =
      input->size * sizeof(robot_interfaces__msg__DetectedObject);
    rcutils_allocator_t allocator = rcutils_get_default_allocator();
    robot_interfaces__msg__DetectedObject * data =
      (robot_interfaces__msg__DetectedObject *)allocator.reallocate(
      output->data, allocation_size, allocator.state);
    if (!data) {
      return false;
    }
    // If reallocation succeeded, memory may or may not have been moved
    // to fulfill the allocation request, invalidating output->data.
    output->data = data;
    for (size_t i = output->capacity; i < input->size; ++i) {
      if (!robot_interfaces__msg__DetectedObject__init(&output->data[i])) {
        // If initialization of any new item fails, roll back
        // all previously initialized items. Existing items
        // in output are to be left unmodified.
        for (; i-- > output->capacity; ) {
          robot_interfaces__msg__DetectedObject__fini(&output->data[i]);
        }
        return false;
      }
    }
    output->capacity = input->size;
  }
  output->size = input->size;
  for (size_t i = 0; i < input->size; ++i) {
    if (!robot_interfaces__msg__DetectedObject__copy(
        &(input->data[i]), &(output->data[i])))
    {
      return false;
    }
  }
  return true;
}
