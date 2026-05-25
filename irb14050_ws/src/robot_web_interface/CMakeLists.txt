cmake_minimum_required(VERSION 3.8)
project(robot_web_interface)

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)

ament_python_install_package(${PROJECT_NAME})

install(PROGRAMS
  robot_web_interface/web_command_bridge.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME web_command_bridge
)

install(DIRECTORY launch
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
