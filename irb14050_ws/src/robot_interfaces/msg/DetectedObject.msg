# Header para timestamp y frame_id
std_msgs/Header header

# Clase detectada
int32 class_id
string label
float32 confidence

# Bounding box 2D (píxeles)
float32 bbox_x1
float32 bbox_y1
float32 bbox_x2
float32 bbox_y2

# Centro del bbox en píxeles
float32 center_u
float32 center_v

# Posición 3D en frame de la cámara (metros)
# x = derecha, y = abajo, z = profundidad
float32 x
float32 y
float32 z

# Flag: False si el depth en ese punto era inválido (0 o NaN)
bool depth_valid