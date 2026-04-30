# abb_irb14050_description — URDF y meshes del ABB IRB 14050

Paquete con la descripción geométrica y cinemática del brazo IRB 14050: URDF/xacro, meshes STL para visualización y colisiones, y un launch para verlo en RViz.

## Notas sobre el origen del URDF

El IRB 14050 **no tiene URDF público de ABB**. Lo que está aquí es una adaptación del URDF dual-arm del YuMi (IRB 14000), del cual el 14050 deriva mecánicamente — es uno solo de los dos brazos del YuMi, así que dimensiones, cinemática y meshes son los mismos. Por eso varios archivos xacro conservan el prefijo `yumi_*`.

## Archivos

### URDF/Xacro (`urdf/`)

| Archivo | Función |
|---|---|
| `abb_irb14050.urdf` | URDF "plano" final, ya expandido desde xacro. Es el que consumen otros paquetes (MoveIt, Gazebo). |
| `yumi.urdf.xacro` | Macro raíz que ensambla el robot. |
| `yumi.xacro` | Definición de links y joints del cuerpo del brazo. |
| `yumi.urdf` | Versión generada del xacro (referencia). |
| `yumi.transmission.xacro` | Transmisiones para `ros2_control`. |
| `Util/materials.xacro` | Definiciones de colores y materiales. |
| `Util/utilities.xacro` | Macros auxiliares de xacro. |
| `Gazebo/gazebo.urdf.xacro`, `Gazebo/yumi.gazebo.xacro` | Wrappers para usar el robot en Gazebo (no usados por MoveIt directamente). |
| `Grippers/yumi_servo_gripper.*.xacro` | Definición del gripper YuMi. Opcional — el 14050 actual no tiene gripper instalado. |

### Meshes (`meshes/`)

| Carpeta | Función |
|---|---|
| `meshes/*.stl` | Meshes de **visualización** (alta resolución, ~28 MB total). Referenciados como `<visual>` en el URDF. |
| `meshes/coarse/*.stl` | Meshes de **colisión** (baja resolución, ~2 MB total). Referenciados como `<collision>`. Son los que MoveIt usa para detección rápida de colisiones. |

### Otros

| Archivo | Función |
|---|---|
| `launch/display.launch.py` | Levanta `robot_state_publisher` + `joint_state_publisher_gui` + RViz para visualizar el robot. |
| `rviz/display.rviz` | Configuración RViz pre-armada para la visualización. |
| `package.xml`, `CMakeLists.txt` | Metadatos del paquete (build_type `ament_cmake`). |

## Build y uso

```bash
cd ~/brazo_robotico_ws
colcon build --symlink-install --packages-select abb_irb14050_description
source install/setup.bash

# Visualizar el robot con sliders para mover articulaciones
ros2 launch abb_irb14050_description display.launch.py
```

Aparece una ventanita (`joint_state_publisher_gui`) con un slider por articulación; cualquier cambio se refleja en RViz al instante. Útil para verificar el URDF antes de pasarlo a MoveIt o Gazebo.

## Para qué se usa este paquete

Es solo descripción — no controla nada. Lo consumen:

- **`abb_irb14050_moveit_config`** para planificación de trayectorias (ver el README de ese paquete para el flujo completo).
- (futuro) Gazebo + `gz_ros2_control` para simulación dinámica.
- (futuro) El bridge EGM + MoveIt para mover el robot real.
