import sys
if sys.prefix == '/usr':
    sys.real_prefix = sys.prefix
    sys.prefix = sys.exec_prefix = '/home/zuriel_tov/Brazo-Robotico/install/robot_task_manager'
