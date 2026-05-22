cmake_minimum_required(VERSION 3.8)
project(robot_task_manager)

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)

ament_python_install_package(${PROJECT_NAME})

install(PROGRAMS
  robot_task_manager/task_tree_node.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME robot_task_tree
)

install(PROGRAMS
  robot_task_manager/object_cloud_bridge.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME object_cloud_bridge
)

install(PROGRAMS
  robot_task_manager/gripper_joint_state_publisher.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME gripper_joint_state_publisher
)

install(DIRECTORY launch config
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
