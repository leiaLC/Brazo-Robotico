std_msgs/Header header

int32   class_id
string  label
float32 confidence

float32 bbox_x1
float32 bbox_y1
float32 bbox_x2
float32 bbox_y2
float32 center_u
float32 center_v

# Máscara de segmentación aplanada (row-major, valores 0.0-1.0)
# Reshape a (mask_height, mask_width) para usarla
float32[] mask
int32     mask_width
int32     mask_height

# Depth (lo llena depth_estimator, vacío al salir de yolo_node)
float32 x
float32 y
float32 z
bool    depth_valid