"""
gripper_rws.py
SmartGripper control via RWS IO signals.

Key finding (verified from RobotStudio behavior):
  The gripper firmware is a state machine that requires transitioning
  through STANDBY (cmd=10) before accepting the next motion command.
  open() and close() now handle this transition automatically.

Sequence:
    cmd != 10  -->  write 10 (standby)  -->  dwell  -->  write target cmd

Without this dance, going OPEN -> CLOSE directly is silently rejected by
the gripper firmware (which is why earlier tests saw OPEN move the jaws
but CLOSE do nothing — we were jumping straight from cmd=1 to cmd=2).
"""

import time
import urllib3
import requests
from typing import Optional, Dict

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class SmartGripperIO:
    # Command codes for hand_CmdGripper
    CMD_OPEN = 1
    CMD_CLOSE = 2
    CMD_STANDBY = 10

    # Time to dwell in standby before issuing the next motion command (s)
    STANDBY_DWELL = 0.4

    # Signal names
    SIG_CMD       = "hand_CmdGripper"        # GO  - command
    SIG_STATE     = "hand_SysState"          # GI  - system state
    SIG_ERROR     = "hand_SysError"          # GI  - error code
    SIG_POS       = "hand_ActualPosition"    # GI  - jaw position
    SIG_SPEED     = "hand_ActualSpeed"       # GI  - jaw speed
    SIG_PRESS_1   = "hand_ActualPressure1"   # GI
    SIG_PRESS_2   = "hand_ActualPressure2"   # GI
    SIG_CALIBRATED = "hand_StatusCalibrated" # DI  - 1 if calibrated

    def __init__(
        self,
        host: str = "192.168.125.1",
        user: str = "Default User",
        password: str = "robotics",
        timeout: float = 3.0,
    ):
        self.base = f"https://{host}"
        self.timeout = timeout
        self.session = requests.Session()
        self.session.auth = (user, password)
        self.session.verify = False
        self.session.headers.update({
            "Accept": "application/hal+json;v=2.0",
            "Content-Type": "application/x-www-form-urlencoded;v=2.0",
        })

    # ----------------------------------------------------------------
    # Low-level signal read/write
    # ----------------------------------------------------------------

    def get_signal(self, name: str) -> Optional[dict]:
        url = f"{self.base}/rw/iosystem/signals/{name}"
        try:
            r = self.session.get(url, timeout=self.timeout)
        except requests.RequestException:
            return None
        if r.status_code != 200:
            return None
        try:
            return r.json()["_embedded"]["resources"][0]
        except (KeyError, IndexError, ValueError):
            return None

    def get_value(self, name: str) -> Optional[int]:
        info = self.get_signal(name)
        if info is None:
            return None
        try:
            return int(info.get("lvalue"))
        except (TypeError, ValueError):
            return None

    def set_signal(self, name: str, value: int) -> bool:
        url = f"{self.base}/rw/iosystem/signals/{name}/set-value"
        body = {"lvalue": str(value)}
        try:
            r = self.session.post(url, data=body, timeout=self.timeout)
        except requests.RequestException as e:
            print(f"[IO] write {name}={value} error: {e}")
            return False
        if r.status_code in (200, 204):
            return True
        print(f"[IO] write {name}={value} -> {r.status_code} {r.text[:200]}")
        return False

    # ----------------------------------------------------------------
    # High-level API (with standby-transition pattern)
    # ----------------------------------------------------------------

    def _via_standby(self, target: int) -> bool:
        """Transition through STANDBY before sending a motion command.

        Required by the gripper firmware: jumping directly from one motion
        cmd to another (e.g. 1 -> 2) is silently rejected. Going through
        10 'rearms' the state machine.
        """
        current = self.get_value(self.SIG_CMD)
        if current != self.CMD_STANDBY:
            if not self.set_signal(self.SIG_CMD, self.CMD_STANDBY):
                return False
            time.sleep(self.STANDBY_DWELL)
        return self.set_signal(self.SIG_CMD, target)

    def open(self) -> bool:
        return self._via_standby(self.CMD_OPEN)

    def close(self) -> bool:
        return self._via_standby(self.CMD_CLOSE)

    def standby(self) -> bool:
        return self.set_signal(self.SIG_CMD, self.CMD_STANDBY)

    def status(self) -> Dict[str, Optional[int]]:
        return {
            "cmd":        self.get_value(self.SIG_CMD),
            "state":      self.get_value(self.SIG_STATE),
            "error":      self.get_value(self.SIG_ERROR),
            "position":   self.get_value(self.SIG_POS),
            "speed":      self.get_value(self.SIG_SPEED),
            "pressure_1": self.get_value(self.SIG_PRESS_1),
            "pressure_2": self.get_value(self.SIG_PRESS_2),
            "calibrated": self.get_value(self.SIG_CALIBRATED),
        }


# --------------------------------------------------------------------
# Test sequence: standby -> open -> close -> open -> standby
# Should now physically move the jaws each step.
# --------------------------------------------------------------------

def _show(g, prefix=""):
    s = g.status()
    parts = [f"{k}={v}" for k, v in s.items() if v is not None]
    print(f"  {prefix}{', '.join(parts)}")


if __name__ == "__main__":
    g = SmartGripperIO()

    print("=== Initial ===")
    _show(g)

    actions = [
        ("OPEN  #1", g.open),
        ("CLOSE #1", g.close),
        ("OPEN  #2", g.open),
        ("CLOSE #2", g.close),
        ("STANDBY", g.standby),
    ]

    for label, fn in actions:
        print(f"\n--- {label} ---")
        ok = fn()
        print(f"  set returned: {ok}")
        # sample at three time points
        for t in (0.5, 1.5, 3.0):
            time.sleep(t - (0.5 if t == 0.5 else (1.0 if t == 1.5 else 1.5)))
            _show(g, prefix=f"  +{t:>3.1f}s  ")
