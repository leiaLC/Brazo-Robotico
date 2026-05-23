#!/usr/bin/env python3
"""
routine_teach.py
Interactive recorder for arm+gripper routines.

Run in TEACH mode:
  - EGM NOT running (the FlexPendant joystick controls the arm)
  - Motors on, MANR
  - You move the arm with the FP joystick, then save poses here
  - The gripper can still be commanded over RWS even with EGM off

Reads joint targets via RWS GET /rw/motionsystem/mechunits/ROB_1/jointtarget.
Writes gripper via SmartGripperIO.

Run from the package folder:
    cd ~/brazo_robotico_ws/src/abb_irb14050_egm/abb_irb14050_egm/
    python3 routine_teach.py --output my_routine.yaml --name pick_demo

YAML format:
  name: <name>
  steps:
    - {type: pose,    joints_deg: [j1, j2, j3, j4, j5, j6, j7]}
    - {type: gripper, action: open | close | standby}
    - {type: wait,    seconds: 0.5}
"""

import argparse
import sys
import requests
import urllib3
import yaml

try:
    # When run as part of the installed package
    from .gripper_rws import SmartGripperIO
except ImportError:
    # When run directly from the source folder
    from gripper_rws import SmartGripperIO

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# --------------------------------------------------------------------
# Joint reading via RWS (no ROS dependency — works during teach mode)
# --------------------------------------------------------------------

def _find_dict_with(d, key):
    """Recursive DFS for a dict containing `key`."""
    if isinstance(d, dict):
        if key in d:
            return d
        for v in d.values():
            r = _find_dict_with(v, key)
            if r is not None:
                return r
    elif isinstance(d, list):
        for v in d:
            r = _find_dict_with(v, key)
            if r is not None:
                return r
    return None


def read_joints_deg(host='192.168.125.1',
                    user='Default User',
                    password='robotics',
                    mech_unit='ROB_1'):
    """Read current 7-DOF joint position in degrees: [J1..J7].

    For the IRB 14050 native 7-DOF config, J7 lives in eax_a.
    """
    url = f"https://{host}/rw/motionsystem/mechunits/{mech_unit}/jointtarget"
    r = requests.get(url, auth=(user, password), verify=False, timeout=5,
                     headers={'Accept': 'application/hal+json;v=2.0'})
    r.raise_for_status()
    payload = r.json()

    info = _find_dict_with(payload, 'rax_1')
    if info is None:
        raise RuntimeError(f"rax_1 not found in jointtarget response")

    joints = [float(info[f'rax_{i}']) for i in range(1, 7)]
    joints.append(float(info.get('eax_a', '0')))
    return joints


# --------------------------------------------------------------------
# Interactive recorder
# --------------------------------------------------------------------

HELP = """\
Commands:
  p   capture current arm pose
  o   open gripper (sends command + records step)
  c   close gripper
  s   standby gripper
  w   add timed wait (asks for seconds)
  l   list current steps
  d   delete last step
  h   show this help
  q   save & quit
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('-o', '--output', default='routine.yaml',
                    help='Output YAML file (default: routine.yaml)')
    ap.add_argument('-n', '--name', default='untitled',
                    help='Routine name (default: untitled)')
    ap.add_argument('--host', default='192.168.125.1',
                    help='OmniCore IP (default: 192.168.125.1)')
    args = ap.parse_args()

    g = SmartGripperIO(host=args.host)

    # Sanity check both subsystems
    print(f"Recording '{args.name}' -> {args.output}")
    print()
    try:
        j0 = read_joints_deg(host=args.host)
        print(f"Joint read OK. Current pose (deg): "
              f"{[round(x, 1) for x in j0]}")
    except Exception as e:
        print(f"WARNING: joint read failed ({e}). 'p' will not work.")

    s0 = g.status()
    if s0.get('cmd') is None:
        print(f"WARNING: gripper not responding "
              f"(last_error: {g.last_error}). 'o'/'c'/'s' will not work.")
    else:
        print(f"Gripper OK. cmd={s0['cmd']}, pressure_1={s0['pressure_1']}")
    print()
    print(HELP)

    steps = []

    while True:
        try:
            cmd = input(f"[{len(steps)} step(s)] > ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if cmd in ('q', 'quit', 'exit'):
            break
        elif cmd in ('h', 'help', '?'):
            print(HELP)
        elif cmd == 'p':
            try:
                joints = read_joints_deg(host=args.host)
            except Exception as e:
                print(f"  ERROR: {e}")
                continue
            step = {'type': 'pose',
                    'joints_deg': [round(x, 3) for x in joints]}
            steps.append(step)
            print(f"  pose #{len(steps)} saved: "
                  f"{[round(x, 1) for x in joints]} deg")
        elif cmd == 'o':
            ok = g.open()
            print(f"  gripper OPEN -> {ok}"
                  + (f"  ({g.last_error})" if not ok else ""))
            if ok:
                steps.append({'type': 'gripper', 'action': 'open'})
        elif cmd == 'c':
            ok = g.close()
            print(f"  gripper CLOSE -> {ok}"
                  + (f"  ({g.last_error})" if not ok else ""))
            if ok:
                steps.append({'type': 'gripper', 'action': 'close'})
        elif cmd == 's':
            ok = g.standby()
            print(f"  gripper STANDBY -> {ok}"
                  + (f"  ({g.last_error})" if not ok else ""))
            if ok:
                steps.append({'type': 'gripper', 'action': 'standby'})
        elif cmd == 'w':
            try:
                secs = float(input("  seconds: ").strip())
            except ValueError:
                print("  not a number")
                continue
            steps.append({'type': 'wait', 'seconds': secs})
            print(f"  wait {secs} s recorded")
        elif cmd == 'l':
            if not steps:
                print("  (no steps yet)")
            for i, st in enumerate(steps, 1):
                print(f"  {i:3d}. {st}")
        elif cmd == 'd':
            if steps:
                removed = steps.pop()
                print(f"  removed: {removed}")
            else:
                print("  nothing to remove")
        elif cmd == '':
            pass
        else:
            print(f"  unknown command '{cmd}' (h for help)")

    if not steps:
        print("No steps recorded. Not saving.")
        return 0

    routine = {'name': args.name, 'steps': steps}
    with open(args.output, 'w') as f:
        yaml.dump(routine, f, default_flow_style=None, sort_keys=False)
    print(f"\nSaved {len(steps)} step(s) to {args.output}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
