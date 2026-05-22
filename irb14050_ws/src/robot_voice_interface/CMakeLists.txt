cmake_minimum_required(VERSION 3.8)
project(robot_voice_interface)

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)

ament_python_install_package(${PROJECT_NAME})

install(PROGRAMS
  robot_voice_interface/voice_command_parser.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME voice_command_parser
)

install(DIRECTORY launch
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
