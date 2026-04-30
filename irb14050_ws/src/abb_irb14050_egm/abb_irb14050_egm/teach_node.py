"""
teach_node.py

Reads current joint positions from an ABB OmniCore controller
(RobotWare 7.x) via RWS 2.0 and saves them as named waypoints in a
YAML file. Meant to run while EGM is OFF and the operator is
jogging the arm manually with the FlexPendant joystick.

RWS 2.0 (OmniCore / RW7) vs RWS 1.0 (IRC5 / RW6):
- HTTPS on port 443 with a self-signed cert (vs HTTP on port 80)
- HTTP Basic authentication (vs Digest)
- Slightly different JSON envelope in the response

Endpoint used:
    GET https://<ip>/rw/motionsystem/mechunits/ROB_1/jointtarget

The parser tolerates several JSON shapes seen across RW7 minor
versions. If yours does not match, run the `raw` command to see
the exact payload and we can tweak the parser.

CLI (same spirit as joint_commander):

    save <n>     - save the current pose under <n>
    list            - list saved poses
    show <n>     - print a saved pose
    delete <n>   - delete a saved pose
    q               - print the current pose (deg)
    raw             - print the raw RWS JSON response (debug)
    help            - show this
    quit

Parameters:
    rws_ip          (str,   default "192.168.125.1")
    rws_scheme      (str,   default "https")        # https for RW7
    rws_port        (int,   default 443)            # 443 for RW7
    rws_user        (str,   default "Default User")
    rws_password    (str,   default "robotics")
    rws_mechunit    (str,   default "ROB_1")
    rws_verify_tls  (bool,  default False)          # self-signed
    waypoints_file  (str,   default "~/irb14050_waypoints.yaml")
    poll_timeout_s  (float, default 3.0)

Typical run order:
    1. FlexPendant -> Manual Reduced Speed, enabling device pressed.
    2. Make sure the EGM RAPID program is NOT running (otherwise
       the stick is ignored by the controller).
    3. ros2 run abb_irb14050_egm teach
    4. Jog the arm to the first pose, type `save pose_1`, repeat.
"""

import json
import os
import threading
import urllib3
from typing import Dict, List

import requests
from requests.auth import HTTPBasicAuth
import yaml

import rclpy
from rclpy.node import Node

# OmniCore ships with a self-signed certificate. Suppress the
# InsecureRequestWarning when verify=False so the console stays
# readable. For a production deployment you would install the
# controller's CA on the ROS host and set rws_verify_tls:=true.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


HELP = """
Commands:
  save <n>     - save current pose (read via RWS) under <n>
  list            - list saved poses
  show <n>     - print a saved pose
  delete <n>   - delete a saved pose
  q               - print the current pose (deg)
  raw             - print the raw RWS JSON response (debug)
  help            - show this
  quit            - exit
"""


class RWSClient:
    """
    Thin HTTP wrapper around the OmniCore RWS 2.0 jointtarget
    endpoint. On RW7 this is HTTPS with Basic Auth.
    """

    def __init__(self,
                 ip: str,
                 user: str,
                 password: str,
                 scheme: str = "https",
                 port: int = 443,
                 mechunit: str = "ROB_1",
                 verify_tls: bool = False,
                 timeout: float = 3.0):
        self.base = f"{scheme}://{ip}:{port}"
        self.mechunit = mechunit
        self.timeout = timeout

        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(user, password)
        self.session.verify = verify_tls
        # Accept: application/hal+json is the RWS 2.0 content type.
        # Some endpoints also accept plain application/json.
        self.session.headers.update({
            "Accept": "application/hal+json;v=2.0",
        })

    # ---- low-level ----

    def get_jointtarget_raw(self) -> dict:
        """Return the raw decoded JSON for the jointtarget endpoint."""
        url = (f"{self.base}/rw/motionsystem/mechunits/"
               f"{self.mechunit}/jointtarget")
        r = self.session.get(url, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    # ---- parsing ----

    def get_jointtarget_deg(self) -> List[float]:
        """
        Fetch current joint target and return 7 floats in degrees,
        EGM order (J1..J6 then J7 elbow as eax_a).
        """
        data = self.get_jointtarget_raw()
        return _extract_joints_deg(data)


# Keys we need, in EGM output order.
_JOINT_KEYS = (
    "rax_1", "rax_2", "rax_3",
    "rax_4", "rax_5", "rax_6",
    "eax_a",  # J7 elbow on the IRB 14050
)


def _extract_joints_deg(data) -> List[float]:
    """
    Walk the RWS jointtarget payload and pull out the 7 joint
    values in degrees. Works with:

    - RW7 flat form (confirmed on this controller):
          {"state": [ {"rax_1": "...", ..., "eax_a": "..."} ]}
    - RW6 nested form:
          {"_embedded": {"_state": [
              {"robax": {"rax_1": ...}, "extax": {"eax_a": ...}}
          ]}}
    - Any other nesting a future RW revision might introduce, as
      long as a single dict somewhere in the tree contains all 7
      required keys.

    RWS returns values as strings; we cast to float here.
    """
    hit = _find_dict_with_keys(data, _JOINT_KEYS)
    if hit is None:
        raise ValueError(
            "Could not find rax_1..rax_6 and eax_a in RWS response. "
            "Run `raw` to inspect the payload. "
            f"Top-level keys: "
            f"{list(data.keys()) if isinstance(data, dict) else type(data)}"
        )
    return [float(hit[k]) for k in _JOINT_KEYS]


def _find_dict_with_keys(node, required_keys):
    """DFS for a dict that contains every key in required_keys."""
    if isinstance(node, dict):
        if all(k in node for k in required_keys):
            return node
        for v in node.values():
            found = _find_dict_with_keys(v, required_keys)
            if found is not None:
                return found
    elif isinstance(node, list):
        for v in node:
            found = _find_dict_with_keys(v, required_keys)
            if found is not None:
                return found
    return None


class TeachNode(Node):

    def __init__(self):
        super().__init__('teach_node')

        self.declare_parameter('rws_ip', '192.168.125.1')
        self.declare_parameter('rws_scheme', 'https')
        self.declare_parameter('rws_port', 443)
        self.declare_parameter('rws_user', 'Default User')
        self.declare_parameter('rws_password', 'robotics')
        self.declare_parameter('rws_mechunit', 'ROB_1')
        self.declare_parameter('rws_verify_tls', False)
        self.declare_parameter(
            'waypoints_file',
            os.path.expanduser('~/irb14050_waypoints.yaml'))
        self.declare_parameter('poll_timeout_s', 3.0)

        self.rws = RWSClient(
            ip=str(self.get_parameter('rws_ip').value),
            scheme=str(self.get_parameter('rws_scheme').value),
            port=int(self.get_parameter('rws_port').value),
            user=str(self.get_parameter('rws_user').value),
            password=str(self.get_parameter('rws_password').value),
            mechunit=str(self.get_parameter('rws_mechunit').value),
            verify_tls=bool(
                self.get_parameter('rws_verify_tls').value),
            timeout=float(
                self.get_parameter('poll_timeout_s').value))

        self.waypoints_file = os.path.expanduser(
            str(self.get_parameter('waypoints_file').value))

        self._waypoints: Dict[str, List[float]] = {}
        self._load_file()

        self.get_logger().info(
            f"teach_node ready.  RWS: {self.rws.base}, "
            f"file: {self.waypoints_file}, "
            f"loaded {len(self._waypoints)} waypoint(s)")

    # ---------- file I/O ----------

    def _load_file(self):
        if not os.path.exists(self.waypoints_file):
            self._waypoints = {}
            return
        try:
            with open(self.waypoints_file, 'r') as f:
                data = yaml.safe_load(f) or {}
        except Exception as e:
            self.get_logger().warning(
                f"Could not read {self.waypoints_file}: {e}. "
                "Starting with an empty set.")
            self._waypoints = {}
            return

        out: Dict[str, List[float]] = {}
        for name, entry in data.items():
            if isinstance(entry, list) and len(entry) == 7:
                out[name] = [float(v) for v in entry]
            elif isinstance(entry, dict) and 'positions_deg' in entry:
                q = entry['positions_deg']
                if len(q) == 7:
                    out[name] = [float(v) for v in q]
        self._waypoints = out

    def _save_file(self):
        serializable = {
            name: {'positions_deg': q}
            for name, q in self._waypoints.items()
        }
        directory = os.path.dirname(self.waypoints_file)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(self.waypoints_file, 'w') as f:
            yaml.safe_dump(serializable, f, sort_keys=True)

    # ---------- commands ----------

    def cmd_save(self, name: str) -> str:
        q = self.rws.get_jointtarget_deg()
        self._waypoints[name] = q
        self._save_file()
        return (f"saved '{name}' = " + self._fmt_q(q)
                + f"  -> {self.waypoints_file}")

    def cmd_list(self) -> str:
        if not self._waypoints:
            return "(no waypoints yet)"
        lines = []
        for name in sorted(self._waypoints.keys()):
            lines.append(f"  {name:16s}  "
                         + self._fmt_q(self._waypoints[name]))
        return "\n".join(lines)

    def cmd_show(self, name: str) -> str:
        if name not in self._waypoints:
            return f"(no such waypoint: '{name}')"
        return f"{name} = " + self._fmt_q(self._waypoints[name])

    def cmd_delete(self, name: str) -> str:
        if name not in self._waypoints:
            return f"(no such waypoint: '{name}')"
        del self._waypoints[name]
        self._save_file()
        return f"deleted '{name}'"

    def cmd_q(self) -> str:
        q = self.rws.get_jointtarget_deg()
        return "current (deg): " + self._fmt_q(q)

    def cmd_raw(self) -> str:
        data = self.rws.get_jointtarget_raw()
        return json.dumps(data, indent=2)

    @staticmethod
    def _fmt_q(q):
        return "[" + ", ".join(f"{v:+7.2f}" for v in q) + "]"


def cli(node: TeachNode):
    print(HELP)
    print("Reminder: FlexPendant in Manual Reduced Speed, "
          "EGM RAPID program NOT running, then jog with the stick.")
    while rclpy.ok():
        try:
            line = input("teach> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not line:
            continue
        parts = line.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        try:
            if cmd == "quit":
                break
            elif cmd == "help":
                print(HELP)
            elif cmd == "save":
                if not arg:
                    print("usage: save <n>")
                    continue
                print(node.cmd_save(arg))
            elif cmd == "list":
                print(node.cmd_list())
            elif cmd == "show":
                if not arg:
                    print("usage: show <n>")
                    continue
                print(node.cmd_show(arg))
            elif cmd == "delete":
                if not arg:
                    print("usage: delete <n>")
                    continue
                print(node.cmd_delete(arg))
            elif cmd == "q":
                print(node.cmd_q())
            elif cmd == "raw":
                print(node.cmd_raw())
            else:
                print(f"unknown command: {cmd}")
        except requests.exceptions.SSLError as e:
            print(f"[TLS error] {e}\n"
                  "Hint: pass rws_verify_tls:=false if using the "
                  "controller's self-signed cert.")
        except requests.exceptions.HTTPError as e:
            print(f"[HTTP error] {e}\n"
                  "Hint: 401 = bad credentials, 404 = wrong "
                  "endpoint path for this RW version.")
        except requests.exceptions.RequestException as e:
            print(f"[RWS error] {e}")
        except Exception as e:
            print(f"[error] {e}")


def main(args=None):
    rclpy.init(args=args)
    node = TeachNode()

    spin_thread = threading.Thread(
        target=rclpy.spin, args=(node,), daemon=True)
    spin_thread.start()

    try:
        cli(node)
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()