std_msgs/Header header

string source
# "voice", "web", "xbox", "system"

string command_type
# "PICK_OBJECT"
# "MOVE_JOINT"
# "WEB_TELEOP"
# "RUN_SEQUENCE"
# "XBOX_TELEOP"
# "CANCEL"
# "ESTOP"
# "PAUSE"
# "RESUME"

string object_class
string object_color
string place_target

int32 joint_id
float64 joint_delta_deg
float64 joint_target_deg
bool relative

string sequence_id

float64[] joint_values
geometry_msgs/Twist teleop_twist

float64 priority
