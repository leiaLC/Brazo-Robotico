import random
import time
import math
from collections import deque

start_time = time.time()
emergency_stop_active = False
message_counter = 0

history = deque(maxlen=60)


def get_robot_telemetry():
    global emergency_stop_active, message_counter

    elapsed_time = time.time() - start_time
    message_counter += 1

    if emergency_stop_active:
        controller_state = "EMERGENCY_STOP"
        motion_state = "HALTED"
        robot_mode = "MANUAL_LOCK"
        speed_scale = 0.0
    else:
        controller_state = "CONNECTED"
        motion_state = "TRACKING_TRAJECTORY"
        robot_mode = "AUTO"
        speed_scale = 1.0

    phase = elapsed_time * 0.75 * max(speed_scale, 0.2)

    joint_1 = 32 * math.sin(phase * 0.70)
    joint_2 = -18 + 24 * math.sin(phase * 0.85 + 0.5)
    joint_3 = 40 * math.cos(phase * 0.55 + 0.3)
    joint_4 = 22 * math.sin(phase * 0.95 + 1.1)
    joint_5 = -30 * math.cos(phase * 0.75 + 0.6)
    joint_6 = 18 * math.sin(phase * 1.10 + 0.8)
    joint_7 = 35 * math.cos(phase * 0.65 + 0.2)

    end_effector_x = 0.58 + 0.04 * math.sin(phase * 0.60)
    end_effector_y = 0.12 + 0.03 * math.cos(phase * 0.80)
    end_effector_z = 0.41 + 0.02 * math.sin(phase * 1.00)

    roll = 4.0 * math.sin(phase * 0.8)
    pitch = 8.0 * math.cos(phase * 0.7)
    yaw = 12.0 * math.sin(phase * 0.6)

    cpu_temperature = random.uniform(41.0, 49.5)
    latency_ms = random.uniform(18.0, 42.0)
    update_rate_hz = random.uniform(9.7, 10.2)
    cycle_time_ms = random.uniform(95.0, 104.0)

    gripper_status = "OPEN" if math.sin(phase * 0.9) > 0 else "CLOSED"
    ros2_bridge = "ONLINE"
    camera_status = "READY (DEMO)"
    program_name = "pick_and_place_demo"

    if emergency_stop_active:
        system_alert = "EMERGENCY_ACTIVE"
    elif cpu_temperature > 48.5:
        system_alert = "HIGH_TEMPERATURE"
    elif latency_ms > 38:
        system_alert = "HIGH_LATENCY"
    else:
        system_alert = "NORMAL"

    telemetry = {
        "timestamp": time.strftime("%H:%M:%S"),
        "robot_name": "ABB IRB 14050",
        "controller_state": controller_state,
        "motion_state": motion_state,
        "robot_mode": robot_mode,
        "camera_status": camera_status,
        "ros2_bridge": ros2_bridge,
        "program_name": program_name,
        "gripper_status": gripper_status,
        "joint_1": round(joint_1, 2),
        "joint_2": round(joint_2, 2),
        "joint_3": round(joint_3, 2),
        "joint_4": round(joint_4, 2),
        "joint_5": round(joint_5, 2),
        "joint_6": round(joint_6, 2),
        "joint_7": round(joint_7, 2),
        "end_effector_x": round(end_effector_x, 3),
        "end_effector_y": round(end_effector_y, 3),
        "end_effector_z": round(end_effector_z, 3),
        "roll": round(roll, 2),
        "pitch": round(pitch, 2),
        "yaw": round(yaw, 2),
        "cpu_temperature": round(cpu_temperature, 2),
        "latency_ms": round(latency_ms, 2),
        "update_rate_hz": round(update_rate_hz, 2),
        "cycle_time_ms": round(cycle_time_ms, 2),
        "message_counter": message_counter,
        "system_alert": system_alert,
        "emergency_stop": emergency_stop_active
    }

    history.append({
        "timestamp": telemetry["timestamp"],
        "joint_1": telemetry["joint_1"],
        "joint_2": telemetry["joint_2"],
        "joint_3": telemetry["joint_3"],
        "joint_4": telemetry["joint_4"],
        "joint_5": telemetry["joint_5"],
        "joint_6": telemetry["joint_6"],
        "joint_7": telemetry["joint_7"],
        "temperature": telemetry["cpu_temperature"],
        "latency": telemetry["latency_ms"]
    })

    return telemetry


def get_history():
    return list(history)


def toggle_emergency_stop():
    global emergency_stop_active
    emergency_stop_active = not emergency_stop_active
    return emergency_stop_active