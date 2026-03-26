# Robotic Arm with Object Recognition (RAOR) - Proyecto Final de Robótica

## 1. Descripción del Proyecto
Este repositorio contiene el desarrollo del sistema de control y visión para un brazo robótico **ABB IRB 14050**, integrado con un controlador **OmniCore C30**. El objetivo principal es la implementación de un controlador avanzado basado en **ROS 2** que permita la interacción humano-robot (HRI) mediante **lenguaje natural**, permitiendo al brazo ejecutar tareas complejas en un entorno de almacén inteligente compartido con otros agentes autónomos (Rover, Watch Tower y Banda Transportadora).

### Componentes de Hardware
* **Manipulador:** Brazo robótico colaborativo IRB 14050.
* **Controlador:** OmniCore C30.
* **Procesamiento Principal:** NVIDIA Jetson Orin NX.
* **Sensores:** * Cámara RGB-D para percepción 3D y reconocimiento de objetos.
    * Micrófono direccional para la ingesta de comandos de voz.
    * Botón de parada de emergencia y DeadMan Switch (Requisitos de seguridad).

### Software
* **Sistema Operativo:** Ubuntu 24.04 LTS.
* **Framework:** ROS 2 Jazzy Jalisco.
* **Simulación:** Gazebo / Webots / NVIDIA Isaac Sim (POR DEFINIR).
* **Visión:** OpenCV, TensorFlow, YOLOv7 para detección de objetos y gestos.
* **Interfaz de Voz:** Natural Language Interfaces (LUI) para procesamiento de lenguaje natural.

## 3. Características Principales
* **Interacción Humano-Robot (HRI):** Capacidad de recibir y entregar objetos a usuarios humanos mediante comandos de voz y reconocimiento de gestos.
* **Visión Artificial 2D/3D:** Identificación de defectos, anomalías y categorización de productos.
* **Planificación de Trayectorias:** Operaciones seguras de *pick-and-place* en entornos dinámicos con presencia de humanos y otros robots.
* **Árbol de Transformaciones (TF):** Sistema de coordenadas común referenciado a un mapa global para integración multi-robot.

## 4. Estructura de Sprints
El desarrollo se dividió en etapas incrementales de autonomía:
1.  **Sprint 1:** Validación de sensores, teleoperación y seguridad física.
2.  **Sprint 2:** Fundamentos de percepción y respuesta a comandos de voz simples (e.g., "stop", "pick up").
3.  **Sprint 3:** Prensión guiada por visión y coordinación brazo-base.
4.  **Sprint 4:** Comandos basados en categorías (e.g., "agarra una fruta") y recuperación de fallos.
5.  **Final Sprint:** Integración total: el sistema gestiona la ambigüedad y completa tareas complejas de almacenamiento.

## 5. Instalación y Uso
*(Nota: Asegúrate de tener instalado ROS2 Jazzy antes de comenzar)*.

```bash
# Clonar el repositorio
git clone [URL-del-repositorio]

# Compilar el workspace
colcon build 

# Lanzamiento del sistema maestro
source install/setup.bash
//////////////////////////////////
```

## 6. Equipo de Trabajo
* **Integrantes:** Daniel Avendaño Llanos, Paola Arizbeth Mejía Alcantar, Francisco Zuriel Tovar Mendoza, Ariadna Laurent Cienfuegos
* **Institución:** Tecnológico de Monterrey, Escuela de Ingeniería y Ciencias.
* **Socio Formador:** Octopy y Ecuela de Ingeniería Industrial.
* **Profesores:** David Balderas (Coordinador), Oscar Fuentes, Jesús Vázquez, José Ángel Martínez.

---

**Licencia:** Este proyecto se desarrolla bajo fines académicos para el curso de Integración de Robótica y Sistemas Inteligentes 2026.
