cmake_minimum_required(VERSION 3.8)
project(abb_irb14050_egm)

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)

ament_python_install_package(${PROJECT_NAME})

install(PROGRAMS
  abb_irb14050_egm/egm_bridge_node.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME egm_bridge
)

install(PROGRAMS
  abb_irb14050_egm/egm_moveit_executor.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME egm_moveit_executor
)

install(PROGRAMS
  abb_irb14050_egm/egm_move_joint_action_server.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME egm_move_joint_action_server
)

install(PROGRAMS
  abb_irb14050_egm/egm_joint_jog_servo.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME egm_joint_jog_servo
)

install(PROGRAMS
  abb_irb14050_egm/gripper_node.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME gripper_node
)

install(PROGRAMS
  abb_irb14050_egm/joint_commander_node.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME joint_commander
)

install(PROGRAMS
  abb_irb14050_egm/joint_state_listener_node.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME joint_listener
)

install(PROGRAMS
  abb_irb14050_egm/teach_node.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME teach
)

install(PROGRAMS
  abb_irb14050_egm/waypoint_player_node.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME waypoint_player
)

install(PROGRAMS
  abb_irb14050_egm/routine_teach.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME routine_teach
)

install(PROGRAMS
  abb_irb14050_egm/routine_player.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME routine_player
)

install(PROGRAMS
  abb_irb14050_egm/moveit_sequence_player.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME moveit_sequence_player
)

install(DIRECTORY launch sequences
  DESTINATION share/${PROJECT_NAME}
)

install(FILES package.xml README.md
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
