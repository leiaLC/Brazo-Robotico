# Yumi Web Control Hub

Industrial dashboard frontend for an ABB IRB14050/YuMi control hub. The app is built with Next.js App Router, TypeScript, Tailwind CSS, mock data, reusable components, `lucide-react` icons, and `recharts` charts.

## Screens

- Dashboard principal: system metrics, energy trend, cycle distribution.
- Panel de control: robot status, operator welcome panel, connection, power, mode, and health cards.
- Teleoperacion: manual joint controls and robot viewport.
- Secuencias: Pick and Place, Sort Items, Scan Surface, and Continuous Loop routines.
- Vision y voz: camera placeholder, detections, voice command panel, and command log.

## Getting Started

Install dependencies:

```bash
npm install
```

Run the development server:

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The initial route redirects to the
Control tab, where the ROS2 node health panel is refreshed automatically.

## Backend Gateway

For production/Vercel usage, the frontend should talk to the local backend gateway, not directly to ROS2 topics. The backend lives in `backend/` and should run on the ROS2/EGM laptop.

Frontend `.env.local`:

```bash
NEXT_PUBLIC_BACKEND_URL=http://<ros2-computer-ip>:8000
```

See `backend/README.md` for ROS2 setup, teleoperation endpoints, and video streaming.

## ROS2 Contract

On the ROS2/EGM computer:

```bash
export ROS_DOMAIN_ID=<your-domain-id>
unset AMENT_PREFIX_PATH COLCON_PREFIX_PATH CMAKE_PREFIX_PATH PYTHONPATH LD_LIBRARY_PATH
source /opt/ros/jazzy/setup.bash
source ~/Brazo-Robotico/irb14050_ws/install/setup.bash
ros2 launch robot_task_manager full_system_abb.launch.py with_viewer:=true launch_object_cloud_bridge:=false controller_ip:=192.168.125.1
```

Configure the frontend with a local `.env.local`:

```bash
cp .env.example .env.local
```

Edit `.env.local`:

```bash
NEXT_PUBLIC_BACKEND_URL=http://<ros2-computer-ip>:8000
```

Restart the Next.js dev server after changing environment variables:

```bash
npm run dev
```

The backend publishes through the behavior-tree contract, not directly to EGM:

```txt
joint targets: /robot_task/command   robot_task_msgs/msg/RobotCommand
sequences:     /web/sequence_id      std_msgs/msg/String
voice trigger: /voice/start_listening std_msgs/msg/Empty
voice status:  /voice/status          std_msgs/msg/String
feedback:      /joint_states         sensor_msgs/msg/JointState
```

The required ROS2 nodes shown in Control can be adjusted in the backend `.env` with
`ROS_REQUIRED_NODES`, using a comma-separated list.

You can verify messages from the ROS2 computer:

```bash
ros2 topic echo /robot_task/command
ros2 topic echo /web/sequence_id
ros2 topic echo /voice/start_listening
ros2 topic echo /voice/status
ros2 topic echo /joint_states
```

The behavior tree validates commands, handles cancellation/status, and is the only component that requests robot motion.

## Useful Commands

```bash
npm run lint
npm run build
```

## Notes

- The UI uses mock data from `src/lib/mock-data.ts`.
- Navigation is implemented with Next.js App Router routes under `src/app`.
- Stitch screenshots in `docs/stitch` were used only as references. They are not used as backgrounds.
