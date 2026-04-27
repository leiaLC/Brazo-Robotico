cmake_minimum_required(VERSION 3.8)
project(abb_irb14050_description)

find_package(ament_cmake REQUIRED)

# Install the four runtime-required directories into share/.
# config/ is kept out until we actually put something in it.
install(DIRECTORY urdf meshes launch rviz
  DESTINATION share/${PROJECT_NAME})

ament_package()
