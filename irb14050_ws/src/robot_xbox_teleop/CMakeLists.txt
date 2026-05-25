cmake_minimum_required(VERSION 3.8)
project(robot_xbox_teleop)

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)

ament_python_install_package(${PROJECT_NAME})

install(PROGRAMS
  robot_xbox_teleop/gamepad_command_bridge.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME gamepad_command_bridge
)

install(PROGRAMS
  robot_xbox_teleop/xbox_command_bridge.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME xbox_command_bridge
)

install(DIRECTORY launch config
  DESTINATION share/${PROJECT_NAME}
)

install(FILES README.md
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
