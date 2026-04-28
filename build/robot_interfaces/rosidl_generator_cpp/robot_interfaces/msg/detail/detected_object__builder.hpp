// generated from rosidl_generator_cpp/resource/idl__builder.hpp.em
// with input from robot_interfaces:msg/DetectedObject.idl
// generated code does not contain a copyright notice

// IWYU pragma: private, include "robot_interfaces/msg/detected_object.hpp"


#ifndef ROBOT_INTERFACES__MSG__DETAIL__DETECTED_OBJECT__BUILDER_HPP_
#define ROBOT_INTERFACES__MSG__DETAIL__DETECTED_OBJECT__BUILDER_HPP_

#include <algorithm>
#include <utility>

#include "robot_interfaces/msg/detail/detected_object__struct.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


namespace robot_interfaces
{

namespace msg
{

namespace builder
{

class Init_DetectedObject_depth_valid
{
public:
  explicit Init_DetectedObject_depth_valid(::robot_interfaces::msg::DetectedObject & msg)
  : msg_(msg)
  {}
  ::robot_interfaces::msg::DetectedObject depth_valid(::robot_interfaces::msg::DetectedObject::_depth_valid_type arg)
  {
    msg_.depth_valid = std::move(arg);
    return std::move(msg_);
  }

private:
  ::robot_interfaces::msg::DetectedObject msg_;
};

class Init_DetectedObject_z
{
public:
  explicit Init_DetectedObject_z(::robot_interfaces::msg::DetectedObject & msg)
  : msg_(msg)
  {}
  Init_DetectedObject_depth_valid z(::robot_interfaces::msg::DetectedObject::_z_type arg)
  {
    msg_.z = std::move(arg);
    return Init_DetectedObject_depth_valid(msg_);
  }

private:
  ::robot_interfaces::msg::DetectedObject msg_;
};

class Init_DetectedObject_y
{
public:
  explicit Init_DetectedObject_y(::robot_interfaces::msg::DetectedObject & msg)
  : msg_(msg)
  {}
  Init_DetectedObject_z y(::robot_interfaces::msg::DetectedObject::_y_type arg)
  {
    msg_.y = std::move(arg);
    return Init_DetectedObject_z(msg_);
  }

private:
  ::robot_interfaces::msg::DetectedObject msg_;
};

class Init_DetectedObject_x
{
public:
  explicit Init_DetectedObject_x(::robot_interfaces::msg::DetectedObject & msg)
  : msg_(msg)
  {}
  Init_DetectedObject_y x(::robot_interfaces::msg::DetectedObject::_x_type arg)
  {
    msg_.x = std::move(arg);
    return Init_DetectedObject_y(msg_);
  }

private:
  ::robot_interfaces::msg::DetectedObject msg_;
};

class Init_DetectedObject_mask_height
{
public:
  explicit Init_DetectedObject_mask_height(::robot_interfaces::msg::DetectedObject & msg)
  : msg_(msg)
  {}
  Init_DetectedObject_x mask_height(::robot_interfaces::msg::DetectedObject::_mask_height_type arg)
  {
    msg_.mask_height = std::move(arg);
    return Init_DetectedObject_x(msg_);
  }

private:
  ::robot_interfaces::msg::DetectedObject msg_;
};

class Init_DetectedObject_mask_width
{
public:
  explicit Init_DetectedObject_mask_width(::robot_interfaces::msg::DetectedObject & msg)
  : msg_(msg)
  {}
  Init_DetectedObject_mask_height mask_width(::robot_interfaces::msg::DetectedObject::_mask_width_type arg)
  {
    msg_.mask_width = std::move(arg);
    return Init_DetectedObject_mask_height(msg_);
  }

private:
  ::robot_interfaces::msg::DetectedObject msg_;
};

class Init_DetectedObject_mask
{
public:
  explicit Init_DetectedObject_mask(::robot_interfaces::msg::DetectedObject & msg)
  : msg_(msg)
  {}
  Init_DetectedObject_mask_width mask(::robot_interfaces::msg::DetectedObject::_mask_type arg)
  {
    msg_.mask = std::move(arg);
    return Init_DetectedObject_mask_width(msg_);
  }

private:
  ::robot_interfaces::msg::DetectedObject msg_;
};

class Init_DetectedObject_center_v
{
public:
  explicit Init_DetectedObject_center_v(::robot_interfaces::msg::DetectedObject & msg)
  : msg_(msg)
  {}
  Init_DetectedObject_mask center_v(::robot_interfaces::msg::DetectedObject::_center_v_type arg)
  {
    msg_.center_v = std::move(arg);
    return Init_DetectedObject_mask(msg_);
  }

private:
  ::robot_interfaces::msg::DetectedObject msg_;
};

class Init_DetectedObject_center_u
{
public:
  explicit Init_DetectedObject_center_u(::robot_interfaces::msg::DetectedObject & msg)
  : msg_(msg)
  {}
  Init_DetectedObject_center_v center_u(::robot_interfaces::msg::DetectedObject::_center_u_type arg)
  {
    msg_.center_u = std::move(arg);
    return Init_DetectedObject_center_v(msg_);
  }

private:
  ::robot_interfaces::msg::DetectedObject msg_;
};

class Init_DetectedObject_bbox_y2
{
public:
  explicit Init_DetectedObject_bbox_y2(::robot_interfaces::msg::DetectedObject & msg)
  : msg_(msg)
  {}
  Init_DetectedObject_center_u bbox_y2(::robot_interfaces::msg::DetectedObject::_bbox_y2_type arg)
  {
    msg_.bbox_y2 = std::move(arg);
    return Init_DetectedObject_center_u(msg_);
  }

private:
  ::robot_interfaces::msg::DetectedObject msg_;
};

class Init_DetectedObject_bbox_x2
{
public:
  explicit Init_DetectedObject_bbox_x2(::robot_interfaces::msg::DetectedObject & msg)
  : msg_(msg)
  {}
  Init_DetectedObject_bbox_y2 bbox_x2(::robot_interfaces::msg::DetectedObject::_bbox_x2_type arg)
  {
    msg_.bbox_x2 = std::move(arg);
    return Init_DetectedObject_bbox_y2(msg_);
  }

private:
  ::robot_interfaces::msg::DetectedObject msg_;
};

class Init_DetectedObject_bbox_y1
{
public:
  explicit Init_DetectedObject_bbox_y1(::robot_interfaces::msg::DetectedObject & msg)
  : msg_(msg)
  {}
  Init_DetectedObject_bbox_x2 bbox_y1(::robot_interfaces::msg::DetectedObject::_bbox_y1_type arg)
  {
    msg_.bbox_y1 = std::move(arg);
    return Init_DetectedObject_bbox_x2(msg_);
  }

private:
  ::robot_interfaces::msg::DetectedObject msg_;
};

class Init_DetectedObject_bbox_x1
{
public:
  explicit Init_DetectedObject_bbox_x1(::robot_interfaces::msg::DetectedObject & msg)
  : msg_(msg)
  {}
  Init_DetectedObject_bbox_y1 bbox_x1(::robot_interfaces::msg::DetectedObject::_bbox_x1_type arg)
  {
    msg_.bbox_x1 = std::move(arg);
    return Init_DetectedObject_bbox_y1(msg_);
  }

private:
  ::robot_interfaces::msg::DetectedObject msg_;
};

class Init_DetectedObject_confidence
{
public:
  explicit Init_DetectedObject_confidence(::robot_interfaces::msg::DetectedObject & msg)
  : msg_(msg)
  {}
  Init_DetectedObject_bbox_x1 confidence(::robot_interfaces::msg::DetectedObject::_confidence_type arg)
  {
    msg_.confidence = std::move(arg);
    return Init_DetectedObject_bbox_x1(msg_);
  }

private:
  ::robot_interfaces::msg::DetectedObject msg_;
};

class Init_DetectedObject_label
{
public:
  explicit Init_DetectedObject_label(::robot_interfaces::msg::DetectedObject & msg)
  : msg_(msg)
  {}
  Init_DetectedObject_confidence label(::robot_interfaces::msg::DetectedObject::_label_type arg)
  {
    msg_.label = std::move(arg);
    return Init_DetectedObject_confidence(msg_);
  }

private:
  ::robot_interfaces::msg::DetectedObject msg_;
};

class Init_DetectedObject_class_id
{
public:
  explicit Init_DetectedObject_class_id(::robot_interfaces::msg::DetectedObject & msg)
  : msg_(msg)
  {}
  Init_DetectedObject_label class_id(::robot_interfaces::msg::DetectedObject::_class_id_type arg)
  {
    msg_.class_id = std::move(arg);
    return Init_DetectedObject_label(msg_);
  }

private:
  ::robot_interfaces::msg::DetectedObject msg_;
};

class Init_DetectedObject_header
{
public:
  Init_DetectedObject_header()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_DetectedObject_class_id header(::robot_interfaces::msg::DetectedObject::_header_type arg)
  {
    msg_.header = std::move(arg);
    return Init_DetectedObject_class_id(msg_);
  }

private:
  ::robot_interfaces::msg::DetectedObject msg_;
};

}  // namespace builder

}  // namespace msg

template<typename MessageType>
auto build();

template<>
inline
auto build<::robot_interfaces::msg::DetectedObject>()
{
  return robot_interfaces::msg::builder::Init_DetectedObject_header();
}

}  // namespace robot_interfaces

#endif  // ROBOT_INTERFACES__MSG__DETAIL__DETECTED_OBJECT__BUILDER_HPP_
