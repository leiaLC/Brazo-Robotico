#!/usr/bin/env python3
"""
remap_yaml_abb_to_ros2.py

Convierte un YAML de waypoints grabado en orden RWS/ABB plano
[rax_1, rax_2, rax_3, rax_4, rax_5, rax_6, eax_a]
a orden ROS2 kinemático
[joint_1, joint_2, joint_3=eax_a, joint_4, joint_5, joint_6, joint_7]

Razón: el IRB 14050 es 7-DOF nativo donde el axis "J7" de ABB es físicamente
el tercer joint de la cadena cinemática (entre J2 y J3 de ABB). RWS devuelve
los valores como rax_1..rax_6 + eax_a sin reordenar, lo cual NO coincide con
el orden de joint_1..joint_7 que MoveIt espera del URDF.

Uso:
    python3 remap_yaml_abb_to_ros2.py input.yaml output.yaml
"""

import sys
import yaml


def remap_abb_to_ros2(values_abb_order):
    """
    Entrada: [rax_1, rax_2, rax_3, rax_4, rax_5, rax_6, eax_a]  (ABB order)
    Salida:  [j1,    j2,    j3,    j4,    j5,    j6,    j7]     (ROS2 kinematic)

    Mapping:
        j1 = rax_1   (ABB J1)
        j2 = rax_2   (ABB J2)
        j3 = eax_a   (ABB J7 — extra axis, kinematically 3rd)
        j4 = rax_3   (ABB J3)
        j5 = rax_4   (ABB J4)
        j6 = rax_5   (ABB J5)
        j7 = rax_6   (ABB J6)
    """
    if len(values_abb_order) != 7:
        raise ValueError(f"Esperaba 7 valores, recibí {len(values_abb_order)}")
    rax1, rax2, rax3, rax4, rax5, rax6, eax_a = values_abb_order
    return [rax1, rax2, eax_a, rax3, rax4, rax5, rax6]


def remap_yaml(input_path, output_path):
    with open(input_path) as f:
        data = yaml.safe_load(f)

    count = 0
    for step in data.get('steps', []):
        if step.get('type') == 'pose':
            old = step['joints_deg']
            new = remap_abb_to_ros2(old)
            step['joints_deg'] = new
            count += 1
            print(f"  ABB:  {[round(x, 3) for x in old]}")
            print(f"  ROS2: {[round(x, 3) for x in new]}")
            print()

    with open(output_path, 'w') as f:
        yaml.safe_dump(data, f, sort_keys=False, default_flow_style=None)

    print(f"Reordenadas {count} poses → {output_path}")


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Uso: python3 remap_yaml_abb_to_ros2.py input.yaml output.yaml")
        sys.exit(1)
    remap_yaml(sys.argv[1], sys.argv[2])
