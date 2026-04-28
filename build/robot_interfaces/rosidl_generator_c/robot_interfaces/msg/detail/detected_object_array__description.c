// generated from rosidl_generator_c/resource/idl__description.c.em
// with input from robot_interfaces:msg/DetectedObjectArray.idl
// generated code does not contain a copyright notice

#include "robot_interfaces/msg/detail/detected_object_array__functions.h"

ROSIDL_GENERATOR_C_PUBLIC_robot_interfaces
const rosidl_type_hash_t *
robot_interfaces__msg__DetectedObjectArray__get_type_hash(
  const rosidl_message_type_support_t * type_support)
{
  (void)type_support;
  static rosidl_type_hash_t hash = {1, {
      0x31, 0x36, 0xf7, 0x66, 0x00, 0x11, 0x80, 0x6f,
      0x4b, 0x85, 0xea, 0x3a, 0x3a, 0x21, 0x64, 0xfc,
      0xb7, 0xd4, 0x8f, 0xa7, 0x82, 0x38, 0xda, 0x7b,
      0xbb, 0xec, 0xf9, 0xfc, 0xcd, 0x97, 0x90, 0x6f,
    }};
  return &hash;
}

#include <assert.h>
#include <string.h>

// Include directives for referenced types
#include "builtin_interfaces/msg/detail/time__functions.h"
#include "std_msgs/msg/detail/header__functions.h"
#include "robot_interfaces/msg/detail/detected_object__functions.h"

// Hashes for external referenced types
#ifndef NDEBUG
static const rosidl_type_hash_t builtin_interfaces__msg__Time__EXPECTED_HASH = {1, {
    0xb1, 0x06, 0x23, 0x5e, 0x25, 0xa4, 0xc5, 0xed,
    0x35, 0x09, 0x8a, 0xa0, 0xa6, 0x1a, 0x3e, 0xe9,
    0xc9, 0xb1, 0x8d, 0x19, 0x7f, 0x39, 0x8b, 0x0e,
    0x42, 0x06, 0xce, 0xa9, 0xac, 0xf9, 0xc1, 0x97,
  }};
static const rosidl_type_hash_t robot_interfaces__msg__DetectedObject__EXPECTED_HASH = {1, {
    0x88, 0x5d, 0xfc, 0xc4, 0x5e, 0x32, 0x85, 0x0e,
    0xdd, 0xad, 0x0f, 0x92, 0x9d, 0x18, 0xaa, 0x3a,
    0x17, 0x4e, 0xe2, 0x1d, 0x35, 0xc8, 0x1d, 0x03,
    0xe4, 0xad, 0x17, 0x05, 0x54, 0xf1, 0x91, 0x70,
  }};
static const rosidl_type_hash_t std_msgs__msg__Header__EXPECTED_HASH = {1, {
    0xf4, 0x9f, 0xb3, 0xae, 0x2c, 0xf0, 0x70, 0xf7,
    0x93, 0x64, 0x5f, 0xf7, 0x49, 0x68, 0x3a, 0xc6,
    0xb0, 0x62, 0x03, 0xe4, 0x1c, 0x89, 0x1e, 0x17,
    0x70, 0x1b, 0x1c, 0xb5, 0x97, 0xce, 0x6a, 0x01,
  }};
#endif

static char robot_interfaces__msg__DetectedObjectArray__TYPE_NAME[] = "robot_interfaces/msg/DetectedObjectArray";
static char builtin_interfaces__msg__Time__TYPE_NAME[] = "builtin_interfaces/msg/Time";
static char robot_interfaces__msg__DetectedObject__TYPE_NAME[] = "robot_interfaces/msg/DetectedObject";
static char std_msgs__msg__Header__TYPE_NAME[] = "std_msgs/msg/Header";

// Define type names, field names, and default values
static char robot_interfaces__msg__DetectedObjectArray__FIELD_NAME__header[] = "header";
static char robot_interfaces__msg__DetectedObjectArray__FIELD_NAME__objects[] = "objects";

static rosidl_runtime_c__type_description__Field robot_interfaces__msg__DetectedObjectArray__FIELDS[] = {
  {
    {robot_interfaces__msg__DetectedObjectArray__FIELD_NAME__header, 6, 6},
    {
      rosidl_runtime_c__type_description__FieldType__FIELD_TYPE_NESTED_TYPE,
      0,
      0,
      {std_msgs__msg__Header__TYPE_NAME, 19, 19},
    },
    {NULL, 0, 0},
  },
  {
    {robot_interfaces__msg__DetectedObjectArray__FIELD_NAME__objects, 7, 7},
    {
      rosidl_runtime_c__type_description__FieldType__FIELD_TYPE_NESTED_TYPE_UNBOUNDED_SEQUENCE,
      0,
      0,
      {robot_interfaces__msg__DetectedObject__TYPE_NAME, 35, 35},
    },
    {NULL, 0, 0},
  },
};

static rosidl_runtime_c__type_description__IndividualTypeDescription robot_interfaces__msg__DetectedObjectArray__REFERENCED_TYPE_DESCRIPTIONS[] = {
  {
    {builtin_interfaces__msg__Time__TYPE_NAME, 27, 27},
    {NULL, 0, 0},
  },
  {
    {robot_interfaces__msg__DetectedObject__TYPE_NAME, 35, 35},
    {NULL, 0, 0},
  },
  {
    {std_msgs__msg__Header__TYPE_NAME, 19, 19},
    {NULL, 0, 0},
  },
};

const rosidl_runtime_c__type_description__TypeDescription *
robot_interfaces__msg__DetectedObjectArray__get_type_description(
  const rosidl_message_type_support_t * type_support)
{
  (void)type_support;
  static bool constructed = false;
  static const rosidl_runtime_c__type_description__TypeDescription description = {
    {
      {robot_interfaces__msg__DetectedObjectArray__TYPE_NAME, 40, 40},
      {robot_interfaces__msg__DetectedObjectArray__FIELDS, 2, 2},
    },
    {robot_interfaces__msg__DetectedObjectArray__REFERENCED_TYPE_DESCRIPTIONS, 3, 3},
  };
  if (!constructed) {
    assert(0 == memcmp(&builtin_interfaces__msg__Time__EXPECTED_HASH, builtin_interfaces__msg__Time__get_type_hash(NULL), sizeof(rosidl_type_hash_t)));
    description.referenced_type_descriptions.data[0].fields = builtin_interfaces__msg__Time__get_type_description(NULL)->type_description.fields;
    assert(0 == memcmp(&robot_interfaces__msg__DetectedObject__EXPECTED_HASH, robot_interfaces__msg__DetectedObject__get_type_hash(NULL), sizeof(rosidl_type_hash_t)));
    description.referenced_type_descriptions.data[1].fields = robot_interfaces__msg__DetectedObject__get_type_description(NULL)->type_description.fields;
    assert(0 == memcmp(&std_msgs__msg__Header__EXPECTED_HASH, std_msgs__msg__Header__get_type_hash(NULL), sizeof(rosidl_type_hash_t)));
    description.referenced_type_descriptions.data[2].fields = std_msgs__msg__Header__get_type_description(NULL)->type_description.fields;
    constructed = true;
  }
  return &description;
}

static char toplevel_type_raw_source[] =
  "std_msgs/Header header\n"
  "robot_interfaces/DetectedObject[] objects";

static char msg_encoding[] = "msg";

// Define all individual source functions

const rosidl_runtime_c__type_description__TypeSource *
robot_interfaces__msg__DetectedObjectArray__get_individual_type_description_source(
  const rosidl_message_type_support_t * type_support)
{
  (void)type_support;
  static const rosidl_runtime_c__type_description__TypeSource source = {
    {robot_interfaces__msg__DetectedObjectArray__TYPE_NAME, 40, 40},
    {msg_encoding, 3, 3},
    {toplevel_type_raw_source, 64, 64},
  };
  return &source;
}

const rosidl_runtime_c__type_description__TypeSource__Sequence *
robot_interfaces__msg__DetectedObjectArray__get_type_description_sources(
  const rosidl_message_type_support_t * type_support)
{
  (void)type_support;
  static rosidl_runtime_c__type_description__TypeSource sources[4];
  static const rosidl_runtime_c__type_description__TypeSource__Sequence source_sequence = {sources, 4, 4};
  static bool constructed = false;
  if (!constructed) {
    sources[0] = *robot_interfaces__msg__DetectedObjectArray__get_individual_type_description_source(NULL),
    sources[1] = *builtin_interfaces__msg__Time__get_individual_type_description_source(NULL);
    sources[2] = *robot_interfaces__msg__DetectedObject__get_individual_type_description_source(NULL);
    sources[3] = *std_msgs__msg__Header__get_individual_type_description_source(NULL);
    constructed = true;
  }
  return &source_sequence;
}
