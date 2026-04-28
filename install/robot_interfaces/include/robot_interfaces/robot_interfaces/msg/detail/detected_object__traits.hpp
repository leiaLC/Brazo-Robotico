// generated from rosidl_generator_cpp/resource/idl__traits.hpp.em
// with input from robot_interfaces:msg/DetectedObject.idl
// generated code does not contain a copyright notice

// IWYU pragma: private, include "robot_interfaces/msg/detected_object.hpp"


#ifndef ROBOT_INTERFACES__MSG__DETAIL__DETECTED_OBJECT__TRAITS_HPP_
#define ROBOT_INTERFACES__MSG__DETAIL__DETECTED_OBJECT__TRAITS_HPP_

#include <stdint.h>

#include <sstream>
#include <string>
#include <type_traits>

#include "robot_interfaces/msg/detail/detected_object__struct.hpp"
#include "rosidl_runtime_cpp/traits.hpp"

// Include directives for member types
// Member 'header'
#include "std_msgs/msg/detail/header__traits.hpp"

namespace robot_interfaces
{

namespace msg
{

inline void to_flow_style_yaml(
  const DetectedObject & msg,
  std::ostream & out)
{
  out << "{";
  // member: header
  {
    out << "header: ";
    to_flow_style_yaml(msg.header, out);
    out << ", ";
  }

  // member: class_id
  {
    out << "class_id: ";
    rosidl_generator_traits::value_to_yaml(msg.class_id, out);
    out << ", ";
  }

  // member: label
  {
    out << "label: ";
    rosidl_generator_traits::value_to_yaml(msg.label, out);
    out << ", ";
  }

  // member: confidence
  {
    out << "confidence: ";
    rosidl_generator_traits::value_to_yaml(msg.confidence, out);
    out << ", ";
  }

  // member: bbox_x1
  {
    out << "bbox_x1: ";
    rosidl_generator_traits::value_to_yaml(msg.bbox_x1, out);
    out << ", ";
  }

  // member: bbox_y1
  {
    out << "bbox_y1: ";
    rosidl_generator_traits::value_to_yaml(msg.bbox_y1, out);
    out << ", ";
  }

  // member: bbox_x2
  {
    out << "bbox_x2: ";
    rosidl_generator_traits::value_to_yaml(msg.bbox_x2, out);
    out << ", ";
  }

  // member: bbox_y2
  {
    out << "bbox_y2: ";
    rosidl_generator_traits::value_to_yaml(msg.bbox_y2, out);
    out << ", ";
  }

  // member: center_u
  {
    out << "center_u: ";
    rosidl_generator_traits::value_to_yaml(msg.center_u, out);
    out << ", ";
  }

  // member: center_v
  {
    out << "center_v: ";
    rosidl_generator_traits::value_to_yaml(msg.center_v, out);
    out << ", ";
  }

  // member: mask
  {
    if (msg.mask.size() == 0) {
      out << "mask: []";
    } else {
      out << "mask: [";
      size_t pending_items = msg.mask.size();
      for (auto item : msg.mask) {
        rosidl_generator_traits::value_to_yaml(item, out);
        if (--pending_items > 0) {
          out << ", ";
        }
      }
      out << "]";
    }
    out << ", ";
  }

  // member: mask_width
  {
    out << "mask_width: ";
    rosidl_generator_traits::value_to_yaml(msg.mask_width, out);
    out << ", ";
  }

  // member: mask_height
  {
    out << "mask_height: ";
    rosidl_generator_traits::value_to_yaml(msg.mask_height, out);
    out << ", ";
  }

  // member: x
  {
    out << "x: ";
    rosidl_generator_traits::value_to_yaml(msg.x, out);
    out << ", ";
  }

  // member: y
  {
    out << "y: ";
    rosidl_generator_traits::value_to_yaml(msg.y, out);
    out << ", ";
  }

  // member: z
  {
    out << "z: ";
    rosidl_generator_traits::value_to_yaml(msg.z, out);
    out << ", ";
  }

  // member: depth_valid
  {
    out << "depth_valid: ";
    rosidl_generator_traits::value_to_yaml(msg.depth_valid, out);
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const DetectedObject & msg,
  std::ostream & out, size_t indentation = 0)
{
  // member: header
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "header:\n";
    to_block_style_yaml(msg.header, out, indentation + 2);
  }

  // member: class_id
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "class_id: ";
    rosidl_generator_traits::value_to_yaml(msg.class_id, out);
    out << "\n";
  }

  // member: label
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "label: ";
    rosidl_generator_traits::value_to_yaml(msg.label, out);
    out << "\n";
  }

  // member: confidence
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "confidence: ";
    rosidl_generator_traits::value_to_yaml(msg.confidence, out);
    out << "\n";
  }

  // member: bbox_x1
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "bbox_x1: ";
    rosidl_generator_traits::value_to_yaml(msg.bbox_x1, out);
    out << "\n";
  }

  // member: bbox_y1
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "bbox_y1: ";
    rosidl_generator_traits::value_to_yaml(msg.bbox_y1, out);
    out << "\n";
  }

  // member: bbox_x2
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "bbox_x2: ";
    rosidl_generator_traits::value_to_yaml(msg.bbox_x2, out);
    out << "\n";
  }

  // member: bbox_y2
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "bbox_y2: ";
    rosidl_generator_traits::value_to_yaml(msg.bbox_y2, out);
    out << "\n";
  }

  // member: center_u
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "center_u: ";
    rosidl_generator_traits::value_to_yaml(msg.center_u, out);
    out << "\n";
  }

  // member: center_v
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "center_v: ";
    rosidl_generator_traits::value_to_yaml(msg.center_v, out);
    out << "\n";
  }

  // member: mask
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    if (msg.mask.size() == 0) {
      out << "mask: []\n";
    } else {
      out << "mask:\n";
      for (auto item : msg.mask) {
        if (indentation > 0) {
          out << std::string(indentation, ' ');
        }
        out << "- ";
        rosidl_generator_traits::value_to_yaml(item, out);
        out << "\n";
      }
    }
  }

  // member: mask_width
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "mask_width: ";
    rosidl_generator_traits::value_to_yaml(msg.mask_width, out);
    out << "\n";
  }

  // member: mask_height
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "mask_height: ";
    rosidl_generator_traits::value_to_yaml(msg.mask_height, out);
    out << "\n";
  }

  // member: x
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "x: ";
    rosidl_generator_traits::value_to_yaml(msg.x, out);
    out << "\n";
  }

  // member: y
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "y: ";
    rosidl_generator_traits::value_to_yaml(msg.y, out);
    out << "\n";
  }

  // member: z
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "z: ";
    rosidl_generator_traits::value_to_yaml(msg.z, out);
    out << "\n";
  }

  // member: depth_valid
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "depth_valid: ";
    rosidl_generator_traits::value_to_yaml(msg.depth_valid, out);
    out << "\n";
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const DetectedObject & msg, bool use_flow_style = false)
{
  std::ostringstream out;
  if (use_flow_style) {
    to_flow_style_yaml(msg, out);
  } else {
    to_block_style_yaml(msg, out);
  }
  return out.str();
}

}  // namespace msg

}  // namespace robot_interfaces

namespace rosidl_generator_traits
{

[[deprecated("use robot_interfaces::msg::to_block_style_yaml() instead")]]
inline void to_yaml(
  const robot_interfaces::msg::DetectedObject & msg,
  std::ostream & out, size_t indentation = 0)
{
  robot_interfaces::msg::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use robot_interfaces::msg::to_yaml() instead")]]
inline std::string to_yaml(const robot_interfaces::msg::DetectedObject & msg)
{
  return robot_interfaces::msg::to_yaml(msg);
}

template<>
inline const char * data_type<robot_interfaces::msg::DetectedObject>()
{
  return "robot_interfaces::msg::DetectedObject";
}

template<>
inline const char * name<robot_interfaces::msg::DetectedObject>()
{
  return "robot_interfaces/msg/DetectedObject";
}

template<>
struct has_fixed_size<robot_interfaces::msg::DetectedObject>
  : std::integral_constant<bool, false> {};

template<>
struct has_bounded_size<robot_interfaces::msg::DetectedObject>
  : std::integral_constant<bool, false> {};

template<>
struct is_message<robot_interfaces::msg::DetectedObject>
  : std::true_type {};

}  // namespace rosidl_generator_traits

#endif  // ROBOT_INTERFACES__MSG__DETAIL__DETECTED_OBJECT__TRAITS_HPP_
