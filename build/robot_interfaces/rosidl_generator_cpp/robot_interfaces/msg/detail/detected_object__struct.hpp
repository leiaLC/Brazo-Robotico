// generated from rosidl_generator_cpp/resource/idl__struct.hpp.em
// with input from robot_interfaces:msg/DetectedObject.idl
// generated code does not contain a copyright notice

// IWYU pragma: private, include "robot_interfaces/msg/detected_object.hpp"


#ifndef ROBOT_INTERFACES__MSG__DETAIL__DETECTED_OBJECT__STRUCT_HPP_
#define ROBOT_INTERFACES__MSG__DETAIL__DETECTED_OBJECT__STRUCT_HPP_

#include <algorithm>
#include <array>
#include <cstdint>
#include <memory>
#include <string>
#include <vector>

#include "rosidl_runtime_cpp/bounded_vector.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


// Include directives for member types
// Member 'header'
#include "std_msgs/msg/detail/header__struct.hpp"

#ifndef _WIN32
# define DEPRECATED__robot_interfaces__msg__DetectedObject __attribute__((deprecated))
#else
# define DEPRECATED__robot_interfaces__msg__DetectedObject __declspec(deprecated)
#endif

namespace robot_interfaces
{

namespace msg
{

// message struct
template<class ContainerAllocator>
struct DetectedObject_
{
  using Type = DetectedObject_<ContainerAllocator>;

  explicit DetectedObject_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : header(_init)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->class_id = 0l;
      this->label = "";
      this->confidence = 0.0f;
      this->bbox_x1 = 0.0f;
      this->bbox_y1 = 0.0f;
      this->bbox_x2 = 0.0f;
      this->bbox_y2 = 0.0f;
      this->center_u = 0.0f;
      this->center_v = 0.0f;
      this->mask_width = 0l;
      this->mask_height = 0l;
      this->x = 0.0f;
      this->y = 0.0f;
      this->z = 0.0f;
      this->depth_valid = false;
    }
  }

  explicit DetectedObject_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : header(_alloc, _init),
    label(_alloc)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->class_id = 0l;
      this->label = "";
      this->confidence = 0.0f;
      this->bbox_x1 = 0.0f;
      this->bbox_y1 = 0.0f;
      this->bbox_x2 = 0.0f;
      this->bbox_y2 = 0.0f;
      this->center_u = 0.0f;
      this->center_v = 0.0f;
      this->mask_width = 0l;
      this->mask_height = 0l;
      this->x = 0.0f;
      this->y = 0.0f;
      this->z = 0.0f;
      this->depth_valid = false;
    }
  }

  // field types and members
  using _header_type =
    std_msgs::msg::Header_<ContainerAllocator>;
  _header_type header;
  using _class_id_type =
    int32_t;
  _class_id_type class_id;
  using _label_type =
    std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>>;
  _label_type label;
  using _confidence_type =
    float;
  _confidence_type confidence;
  using _bbox_x1_type =
    float;
  _bbox_x1_type bbox_x1;
  using _bbox_y1_type =
    float;
  _bbox_y1_type bbox_y1;
  using _bbox_x2_type =
    float;
  _bbox_x2_type bbox_x2;
  using _bbox_y2_type =
    float;
  _bbox_y2_type bbox_y2;
  using _center_u_type =
    float;
  _center_u_type center_u;
  using _center_v_type =
    float;
  _center_v_type center_v;
  using _mask_type =
    std::vector<float, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<float>>;
  _mask_type mask;
  using _mask_width_type =
    int32_t;
  _mask_width_type mask_width;
  using _mask_height_type =
    int32_t;
  _mask_height_type mask_height;
  using _x_type =
    float;
  _x_type x;
  using _y_type =
    float;
  _y_type y;
  using _z_type =
    float;
  _z_type z;
  using _depth_valid_type =
    bool;
  _depth_valid_type depth_valid;

  // setters for named parameter idiom
  Type & set__header(
    const std_msgs::msg::Header_<ContainerAllocator> & _arg)
  {
    this->header = _arg;
    return *this;
  }
  Type & set__class_id(
    const int32_t & _arg)
  {
    this->class_id = _arg;
    return *this;
  }
  Type & set__label(
    const std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>> & _arg)
  {
    this->label = _arg;
    return *this;
  }
  Type & set__confidence(
    const float & _arg)
  {
    this->confidence = _arg;
    return *this;
  }
  Type & set__bbox_x1(
    const float & _arg)
  {
    this->bbox_x1 = _arg;
    return *this;
  }
  Type & set__bbox_y1(
    const float & _arg)
  {
    this->bbox_y1 = _arg;
    return *this;
  }
  Type & set__bbox_x2(
    const float & _arg)
  {
    this->bbox_x2 = _arg;
    return *this;
  }
  Type & set__bbox_y2(
    const float & _arg)
  {
    this->bbox_y2 = _arg;
    return *this;
  }
  Type & set__center_u(
    const float & _arg)
  {
    this->center_u = _arg;
    return *this;
  }
  Type & set__center_v(
    const float & _arg)
  {
    this->center_v = _arg;
    return *this;
  }
  Type & set__mask(
    const std::vector<float, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<float>> & _arg)
  {
    this->mask = _arg;
    return *this;
  }
  Type & set__mask_width(
    const int32_t & _arg)
  {
    this->mask_width = _arg;
    return *this;
  }
  Type & set__mask_height(
    const int32_t & _arg)
  {
    this->mask_height = _arg;
    return *this;
  }
  Type & set__x(
    const float & _arg)
  {
    this->x = _arg;
    return *this;
  }
  Type & set__y(
    const float & _arg)
  {
    this->y = _arg;
    return *this;
  }
  Type & set__z(
    const float & _arg)
  {
    this->z = _arg;
    return *this;
  }
  Type & set__depth_valid(
    const bool & _arg)
  {
    this->depth_valid = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    robot_interfaces::msg::DetectedObject_<ContainerAllocator> *;
  using ConstRawPtr =
    const robot_interfaces::msg::DetectedObject_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<robot_interfaces::msg::DetectedObject_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<robot_interfaces::msg::DetectedObject_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      robot_interfaces::msg::DetectedObject_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<robot_interfaces::msg::DetectedObject_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      robot_interfaces::msg::DetectedObject_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<robot_interfaces::msg::DetectedObject_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<robot_interfaces::msg::DetectedObject_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<robot_interfaces::msg::DetectedObject_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__robot_interfaces__msg__DetectedObject
    std::shared_ptr<robot_interfaces::msg::DetectedObject_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__robot_interfaces__msg__DetectedObject
    std::shared_ptr<robot_interfaces::msg::DetectedObject_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const DetectedObject_ & other) const
  {
    if (this->header != other.header) {
      return false;
    }
    if (this->class_id != other.class_id) {
      return false;
    }
    if (this->label != other.label) {
      return false;
    }
    if (this->confidence != other.confidence) {
      return false;
    }
    if (this->bbox_x1 != other.bbox_x1) {
      return false;
    }
    if (this->bbox_y1 != other.bbox_y1) {
      return false;
    }
    if (this->bbox_x2 != other.bbox_x2) {
      return false;
    }
    if (this->bbox_y2 != other.bbox_y2) {
      return false;
    }
    if (this->center_u != other.center_u) {
      return false;
    }
    if (this->center_v != other.center_v) {
      return false;
    }
    if (this->mask != other.mask) {
      return false;
    }
    if (this->mask_width != other.mask_width) {
      return false;
    }
    if (this->mask_height != other.mask_height) {
      return false;
    }
    if (this->x != other.x) {
      return false;
    }
    if (this->y != other.y) {
      return false;
    }
    if (this->z != other.z) {
      return false;
    }
    if (this->depth_valid != other.depth_valid) {
      return false;
    }
    return true;
  }
  bool operator!=(const DetectedObject_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct DetectedObject_

// alias to use template instance with default allocator
using DetectedObject =
  robot_interfaces::msg::DetectedObject_<std::allocator<void>>;

// constant definitions

}  // namespace msg

}  // namespace robot_interfaces

#endif  // ROBOT_INTERFACES__MSG__DETAIL__DETECTED_OBJECT__STRUCT_HPP_
