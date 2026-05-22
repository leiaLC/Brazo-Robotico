cmake_minimum_required(VERSION 3.8)
project(robot_arm_control)

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)

ament_python_install_package(${PROJECT_NAME})

install(PROGRAMS
  robot_arm_control/mock_arm_action_server.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME mock_arm_action_server
)

install(PROGRAMS
  robot_arm_control/mock_gripper_node.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME mock_gripper_node
)

install(PROGRAMS
  robot_arm_control/mock_servo_node.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME mock_servo_node
)

install(DIRECTORY launch config
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
