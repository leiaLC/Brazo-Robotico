import cv2
import numpy as np
import time
import math
import random


def generate_simulated_realsense_feed():
    frame_id = 0
    start_time = time.time()

    while True:
        frame_id += 1
        width = 960
        height = 540

        elapsed_time = time.time() - start_time
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

        frame = np.zeros((height, width, 3), dtype=np.uint8)

        # Fondo industrial oscuro con gradiente
        for y in range(height):
            color = 22 + int((y / height) * 28)
            frame[y, :] = (color, color + 6, color + 12)

        # Workspace / mesa
        cv2.rectangle(frame, (100, 255), (860, 500), (72, 76, 82), -1)
        cv2.rectangle(frame, (100, 255), (860, 500), (165, 170, 178), 2)

        # Grid de mesa
        for x in range(120, 860, 60):
            cv2.line(frame, (x, 255), (x, 500), (92, 96, 105), 1)

        for y in range(275, 500, 45):
            cv2.line(frame, (100, y), (860, y), (92, 96, 105), 1)

        # Objeto detectado
        obj_x = int(560 + 95 * math.sin(elapsed_time * 0.65))
        obj_y = int(390 + 25 * math.cos(elapsed_time * 0.55))
        depth_m = 0.72 + 0.08 * math.sin(elapsed_time * 0.4)

        # Sombra
        cv2.ellipse(frame, (obj_x, obj_y + 42), (55, 18), 0, 0, 360, (28, 28, 28), -1)

        # Objeto
        cv2.circle(frame, (obj_x, obj_y), 38, (0, 175, 255), -1)
        cv2.circle(frame, (obj_x, obj_y), 38, (255, 255, 255), 2)

        # Bounding box de detección
        box_color = (0, 230, 255)
        cv2.rectangle(frame, (obj_x - 58, obj_y - 58), (obj_x + 58, obj_y + 58), box_color, 2)
        cv2.putText(
            frame,
            f"object | conf: 0.{random.randint(86, 97)} | z: {depth_m:.2f} m",
            (obj_x - 58, obj_y - 68),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            box_color,
            2
        )

        # Brazo de 7 articulaciones
        base = (230, 215)
        link_lengths = [58, 54, 50, 44, 38, 32, 28]
        joint_angles = [
            -22 + 18 * math.sin(elapsed_time * 0.55),
            32 * math.cos(elapsed_time * 0.45),
            -24 + 18 * math.sin(elapsed_time * 0.60 + 0.4),
            18 * math.cos(elapsed_time * 0.70 + 0.9),
            -15 + 16 * math.sin(elapsed_time * 0.85 + 0.2),
            12 * math.cos(elapsed_time * 1.05 + 0.7),
            16 * math.sin(elapsed_time * 0.65 + 1.0),
        ]

        points = [base]
        total_angle = -0.25

        for i, angle_deg in enumerate(joint_angles):
            total_angle += math.radians(angle_deg) * 0.42
            prev_x, prev_y = points[-1]
            new_x = int(prev_x + link_lengths[i] * math.cos(total_angle))
            new_y = int(prev_y + link_lengths[i] * math.sin(total_angle))
            points.append((new_x, new_y))

        # Sombra del brazo
        for i in range(len(points) - 1):
            shadow_p1 = (points[i][0] + 5, points[i][1] + 7)
            shadow_p2 = (points[i + 1][0] + 5, points[i + 1][1] + 7)
            cv2.line(frame, shadow_p1, shadow_p2, (18, 18, 18), 18)

        # Links del brazo
        thicknesses = [17, 15, 13, 11, 9, 7, 6]
        for i in range(len(points) - 1):
            cv2.line(frame, points[i], points[i + 1], (215, 220, 226), thicknesses[i])
            cv2.line(frame, points[i], points[i + 1], (250, 250, 250), 2)

        # Joints
        for i, p in enumerate(points):
            radius = 15 if i == 0 else 10
            cv2.circle(frame, p, radius, (185, 190, 198), -1)
            cv2.circle(frame, p, radius, (250, 250, 250), 2)
            if i > 0:
                cv2.putText(
                    frame,
                    f"J{i}",
                    (p[0] - 10, p[1] - 15),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.38,
                    (255, 255, 255),
                    1
                )

        # Gripper
        tool = points[-1]
        cv2.line(frame, tool, (tool[0] + 24, tool[1] - 12), (245, 245, 245), 4)
        cv2.line(frame, tool, (tool[0] + 24, tool[1] + 12), (245, 245, 245), 4)

        # Línea de interés hacia objeto
        cv2.line(frame, tool, (obj_x, obj_y), (80, 170, 255), 1)

        # Retícula central
        center = (width // 2, height // 2)
        cv2.line(frame, (center[0] - 22, center[1]), (center[0] + 22, center[1]), (95, 255, 120), 1)
        cv2.line(frame, (center[0], center[1] - 22), (center[0], center[1] + 22), (95, 255, 120), 1)
        cv2.circle(frame, center, 28, (95, 255, 120), 1)

        # Panel superior
        cv2.rectangle(frame, (0, 0), (width, 48), (8, 12, 20), -1)
        cv2.putText(
            frame,
            "ABB IRB 14050 | Intel RealSense RGB Stream | ROS2-ready",
            (18, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (235, 240, 245),
            2
        )

        # Datos técnicos
        cv2.putText(frame, f"Timestamp: {timestamp}", (18, 75),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.52, (230, 230, 230), 1)
        cv2.putText(frame, f"Frame ID: {frame_id}", (18, 99),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.52, (230, 230, 230), 1)
        cv2.putText(frame, "Resolution: 960x540", (18, 123),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.52, (230, 230, 230), 1)
        cv2.putText(frame, "Topic: /camera/color/image_raw", (18, 147),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.52, (120, 255, 180), 1)
        cv2.putText(frame, "Depth source prepared: /camera/depth/image_rect_raw", (18, 171),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.52, (120, 255, 180), 1)

        # Panel derecho
        cv2.rectangle(frame, (720, 62), (940, 165), (14, 23, 36), -1)
        cv2.rectangle(frame, (720, 62), (940, 165), (75, 135, 210), 1)
        cv2.putText(frame, "VISION STATUS", (748, 88),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (95, 180, 255), 2)
        cv2.putText(frame, "Tracking: ACTIVE", (738, 116),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.50, (210, 240, 255), 1)
        cv2.putText(frame, f"Object X,Y: {obj_x}, {obj_y}", (738, 140),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.50, (210, 240, 255), 1)

        # Etiqueta demo discreta
        cv2.rectangle(frame, (750, 485), (940, 522), (18, 30, 45), -1)
        cv2.rectangle(frame, (750, 485), (940, 522), (80, 160, 255), 1)
        cv2.putText(frame, "DEMO STREAM", (785, 509),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.58, (80, 160, 255), 2)

        # Ruido suave tipo cámara
        noise = np.random.normal(0, 3, frame.shape).astype(np.int16)
        noisy_frame = np.clip(frame.astype(np.int16) + noise, 0, 255).astype(np.uint8)

        ret, buffer = cv2.imencode(".jpg", noisy_frame)
        if not ret:
            continue

        frame_bytes = buffer.tobytes()

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
        )