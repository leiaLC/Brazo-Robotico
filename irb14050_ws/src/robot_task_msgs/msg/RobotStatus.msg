std_msgs/Header header

string mode
# "IDLE"
# "VOICE_PICK"
# "VOICE_JOINT"
# "WEB_TELEOP"
# "WEB_SEQUENCE"
# "XBOX_TELEOP"
# "ERROR"
# "ESTOP"

string current_task
string message

bool robot_ready
bool arm_busy
bool estop_active
bool teleop_active

float32 progress
string error_code
