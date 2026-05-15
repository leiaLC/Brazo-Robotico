std_msgs/Header header
int32   class_id
string  label
float32 confidence

float32 bbox_x1
float32 bbox_y1
float32 bbox_x2
float32 bbox_y2

# Centroide 3D en frame de la cámara (metros)
float32 centroid_x
float32 centroid_y
float32 centroid_z
bool centroid_valid

# Dimensiones del bounding box 3D del objeto (metros)
float32 size_x
float32 size_y
float32 size_z