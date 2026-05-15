# abb_irb14050_gazebo — Simulación Gazebo Harmonic del ABB IRB 14050

Paquete que integra el ABB IRB 14050 (single-arm YuMi, 7 DOF) con **Gazebo
Harmonic** sobre **ROS 2 Jazzy**, usando `gz_ros2_control` como puente entre
`ros2_control` y la física de Gazebo.

Funciona como pieza de simulación complementaria a `abb_irb14050_moveit_config`.
La pareja de paquetes permite planear trayectorias con MoveIt 2 y ejecutarlas
sobre el robot simulado, exactamente como ocurriría con el robot físico.

---

## Índice

1. [Arquitectura sim-to-real](#1-arquitectura-sim-to-real)
2. [Prerrequisitos](#2-prerrequisitos)
3. [Estructura del paquete](#3-estructura-del-paquete)
4. [Build](#4-build)
5. [Uso](#5-uso)
6. [Cómo encaja con los otros paquetes](#6-cómo-encaja-con-los-otros-paquetes)
7. [Notas de compatibilidad GPU](#7-notas-de-compatibilidad-gpu)
8. [Warnings esperados](#8-warnings-esperados)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. Arquitectura sim-to-real

El stack está diseñado para que la transición simulación ↔ robot real se haga
cambiando **un solo argumento**, no reescribiendo paquetes.

```
                  MoveIt 2 (RViz + move_group)
                            ↓ FollowJointTrajectory action
                  irb14050_arm_controller (joint_trajectory_controller)
                            ↓ command interface "position"
                  ┌─────────┴──────────┐
                  ↓                    ↓
      mock_components/      gz_ros2_control/        (futuro) EGM hardware
      GenericSystem         GazeboSimSystem          interface
      (testing en RViz)     (este paquete)           (robot real)
```

El switch vive en `abb_irb14050_moveit_config/config/abb_irb14050.ros2_control.xacro`,
parametrizado con el argumento `sim_mode`:

| `sim_mode` | Plugin cargado | Para qué |
|---|---|---|
| `mock` (default) | `mock_components/GenericSystem` | Test rápido en RViz, sin física |
| `gazebo` | `gz_ros2_control/GazeboSimSystem` | Simulación dinámica (este paquete) |
| `real` | (placeholder, EGM) | Robot físico vía OmniCore |

---

## 2. Prerrequisitos

| Componente | Versión |
|---|---|
| Ubuntu | 24.04 |
| ROS 2 | Jazzy |
| Gazebo | Harmonic 8.x |

Paquetes ROS necesarios (aparte de los que ya pide el moveit_config):

```bash
sudo apt install -y \
    ros-jazzy-ros-gz-sim \
    ros-jazzy-ros-gz-bridge \
    ros-jazzy-gz-ros2-control
```

Y los paquetes hermanos en el workspace:

- `abb_irb14050_description` (URDF + meshes del robot)
- `abb_irb14050_moveit_config` (MoveIt config + ros2_control.xacro parametrizado)

---

## 3. Estructura del paquete

```
abb_irb14050_gazebo/
├── CMakeLists.txt
├── package.xml
├── README.md
├── config/
│   └── controllers_gazebo.yaml      # Controllers que carga gz_ros2_control
├── launch/
│   ├── spawn_robot.launch.py        # Solo Gazebo + robot + controllers
│   └── gazebo_moveit.launch.py      # Stack completo (incluye spawn_robot)
└── worlds/
    └── empty.world                  # Mundo mínimo: suelo + luz + física
```

### Archivos clave

| Archivo | Función |
|---|---|
| `worlds/empty.world` | World SDF con suelo, sol direccional, y los plugins obligatorios de Gazebo Harmonic (Physics, SceneBroadcaster, UserCommands, Sensors, Imu). Sin bloque `<gui>` custom — Gazebo carga su GUI por defecto. |
| `config/controllers_gazebo.yaml` | Define los dos controllers que `gz_ros2_control` instancia: `joint_state_broadcaster` y `irb14050_arm_controller`. Los nombres coinciden con los que MoveIt espera en su `moveit_controllers.yaml`. |
| `launch/spawn_robot.launch.py` | Levanta Gazebo, hace bridge de `/clock`, procesa el xacro con `sim_mode:=gazebo`, spawnea el robot, y carga los dos controllers en orden (JSB primero). |
| `launch/gazebo_moveit.launch.py` | Incluye `spawn_robot.launch.py` y le suma el nodo `move_group` de MoveIt + RViz con la configuración pre-armada del moveit_config. |

---

## 4. Build

Desde la raíz del workspace:

```bash
cd ~/brazo_robotico_ws
colcon build --symlink-install --packages-select abb_irb14050_gazebo
source install/setup.bash
```

`--symlink-install` permite editar archivos del paquete (launches, world, YAML)
sin recompilar — los cambios se reflejan al relanzar.

---

## 5. Uso

### Solo Gazebo (sin MoveIt)

Útil para verificar que la simulación de física y los controllers están
operativos, aislados del stack de planeación:

```bash
ros2 launch abb_irb14050_gazebo spawn_robot.launch.py
```

Verificación en otra terminal:

```bash
source ~/brazo_robotico_ws/install/setup.bash

# Los dos controllers deben estar 'active'
ros2 control list_controllers

# /joint_states publica los 7 joints a 100 Hz
ros2 topic hz /joint_states
```

### Stack completo (Gazebo + MoveIt + RViz)

Modo de uso normal:

```bash
ros2 launch abb_irb14050_gazebo gazebo_moveit.launch.py
```

Abre dos ventanas: Gazebo (vista 3D del simulador físico) y RViz (panel
MotionPlanning de MoveIt). Para mover el robot:

1. En RViz, panel **MotionPlanning** → tab **Planning**
2. Mueve el marker interactivo del end-effector a la pose deseada
3. **Plan** → MoveIt calcula la trayectoria (la dibuja en RViz)
4. **Execute** → la trayectoria se envía al `irb14050_arm_controller`,
   `gz_ros2_control` la traduce a comandos de joint, y el robot se mueve
   en Gazebo. RViz refleja el estado real porque escucha `/joint_states`.

---

## 6. Cómo encaja con los otros paquetes

```
abb_irb14050_description       (URDF + meshes — geometría)
        ↑ depend
abb_irb14050_moveit_config     (URDF wrapper + ros2_control.xacro + MoveIt config)
        ↑ depend
abb_irb14050_gazebo            (este paquete — world + controllers + launches)
```

Este paquete **no contiene URDF propio**. Reutiliza el del description y el
wrapper xacro del moveit_config, pasándole `sim_mode:=gazebo` para que el bloque
`<gazebo>` con el plugin `gz_ros2_control` se incluya en el árbol final.

---

## 7. Notas de compatibilidad GPU

En laptops híbridas Intel + NVIDIA (Optimus), Gazebo Harmonic falla en renderear
el viewport 3D si OpenGL/EGL no están enrutados explícitamente a la NVIDIA. El
launch ya setea las tres env vars necesarias internamente:

```python
__NV_PRIME_RENDER_OFFLOAD = "1"
__GLX_VENDOR_LIBRARY_NAME = "nvidia"
__EGL_VENDOR_LIBRARY_FILENAMES = "/usr/share/glvnd/egl_vendor.d/10_nvidia.json"
```

Estas variables son **inocuas** en sistemas no híbridos (desktops con una sola
GPU, máquinas con solo Intel, etc.) — el sistema las ignora si no aplican.

Si tu setup usa otra ruta para el `.json` de NVIDIA, edita la línea
correspondiente en `launch/spawn_robot.launch.py`. Para verificar la ruta:

```bash
ls /usr/share/glvnd/egl_vendor.d/
```

---

## 8. Warnings esperados

Estos mensajes aparecen en la terminal y son **inofensivos**. Ignorarlos:

| Mensaje | Por qué aparece |
|---|---|
| `mock_components/GenericSystem ... does not exist. Declared types are gz_ros2_control/GazeboSimSystem ign_ros2_control/IgnitionSystem` | `gz_ros2_control` enumera todos los plugins de tipo `system` registrados en el árbol; el `mock_components` es válido para `ros2_control` pero no es un `GazeboSimSystemInterface`. Tras imprimir este error, carga el plugin correcto y todo funciona. |
| `Desired controller update period (0.01 s) is slower than the gazebo simulation period (0.001 s)` | Informativo. El controller corre a 100 Hz y la física a 1000 Hz. Es la configuración intencional. |
| `Component 'ABB_IRB14050_System' does not have read or write statistics initialized` | Métricas opcionales no configuradas. No afecta operación. |
| `Executor is not available during hardware component initialization` | Limitación conocida del ciclo de vida de los hardware components durante la inicialización de Gazebo. Se reportan al cargar pero ya están operativos cuando MoveIt se conecta. |
| `[QT] ... Binding loop detected for property "implicitHeight"` | Bug cosmético de Qt 5 con los QML default de Gazebo. No afecta funcionamiento. |

---

## 9. Troubleshooting

### Gazebo abre pero el viewport está en blanco/gris

Si las env vars de NVIDIA no resolvieron el problema (sistemas no Optimus pero
con drivers exóticos), prueba bajar a `ogre` (versión clásica) en lugar de
`ogre2`:

```bash
ros2 launch abb_irb14050_gazebo gazebo_moveit.launch.py
# Si falla, en otra terminal:
gz sim --render-engine ogre worlds/empty.world
```

### Robot aparece pero no se mueve al hacer Execute en MoveIt

Verifica que los controllers están activos:

```bash
ros2 control list_controllers
```

Ambos (`joint_state_broadcaster`, `irb14050_arm_controller`) deben estar en
estado `active`. Si están `inactive` o `unconfigured`, revisa el log de Gazebo
buscando errores en la carga del plugin `gz_ros2_control`.

### "Failed to load mesh from [model://abb_irb14050_description/...]"

`GZ_SIM_RESOURCE_PATH` no se está seteando bien. El launch lo hace
automáticamente derivándolo del share del description package. Si el error
persiste, verifica que las STL están instaladas:

```bash
ls ~/brazo_robotico_ws/install/abb_irb14050_description/share/abb_irb14050_description/meshes/coarse/
```

Deben aparecer los `.stl`. Si no, el `CMakeLists.txt` del description package
no las está instalando — fix ahí, no aquí.

---

## Estado y próximos pasos

**Funcional hoy**: simulación dinámica completa con MoveIt planeando y
ejecutando trayectorias en tiempo real.

**Pendiente** (frentes abiertos del proyecto):
- Cámara virtual + objetos en el world para tareas de visión por computadora
- Hardware interface EGM custom para `sim_mode:=real` (el bridge EGM existe
  como nodo Python; falta envolverlo como plugin de `ros2_control`)
- Nodo de NLP que convierte instrucción en lenguaje natural → goal de MoveIt
