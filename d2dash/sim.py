"""Simulated Td5 and SLABS sources for bench testing without the car.

They implement the same contract as d2diag's DataSource classes:
    poll()    -> {"status", "source", "signals": {name: {"v","u","s","c"}}, "faults": [str]}
    command(action, params) -> {"ok", "message" | "error"}
    disconnect()
Values drift realistically so gauges move. Fault lists can be cleared.
"""
from __future__ import annotations

import math
import random
import time


def _sig(v: float, u: str, c: str = "proven", status: str = "ok") -> dict:
    return {"v": round(v, 2), "u": u, "s": status, "c": c}


class SimTd5:
    name = "td5"

    def __init__(self) -> None:
        self._t0 = time.monotonic()
        self._connected_at: float | None = None
        self.on_progress = None
        # real decoder output: names from the dictionary, plus an undecoded bit
        self._faults = ["coolant temp. circuit (Logged High)", "air flow circuit (Current)", "byte12.bit3"]
        self._odo = 0.0

    def is_connected(self) -> bool:
        return self._connected_at is not None

    def disconnect(self) -> None:
        self._connected_at = None

    def poll(self) -> dict:
        if self._connected_at is None:
            # mimic the real 5 s bus idle before fast init
            if self.on_progress:
                self.on_progress("waiting 5 s bus idle before fast init (simulated)")
            time.sleep(1.5)
            self._connected_at = time.monotonic()
        t = time.monotonic() - self._t0
        # a drive cycle: idle, pull away, cruise, slow down
        phase = (t % 60) / 60.0
        rpm = 780 + 2200 * max(0.0, math.sin(phase * math.pi)) + random.uniform(-15, 15)
        speed = max(0.0, 95 * math.sin(phase * math.pi) + random.uniform(-1, 1))
        boost = 1.0 + 0.9 * max(0.0, math.sin(phase * math.pi)) ** 2
        coolant = min(92.0, 20 + t * 0.6) + random.uniform(-0.3, 0.3)
        inj = 4 + 40 * max(0.0, math.sin(phase * math.pi)) ** 1.5
        fuel_rate = rpm * inj * 5 / 2 / 60 / 1000 / 0.84 * 60 / 1000  # L/h, rough
        self._odo += speed / 3600 * 0.5
        return {
            "status": "connected",
            "source": self.name,
            "signals": {
                "rpm": _sig(rpm, "rpm"),
                "speed": _sig(speed, "km/h"),
                "coolant_temp": _sig(coolant, "°C", status="high" if coolant > 105 else "ok"),
                "air_temp": _sig(28 + boost * 12, "°C"),
                "fuel_temp": _sig(35 + t * 0.1 % 15, "°C"),
                "manifold_press": _sig(boost, "bar"),
                "ambient_press_1": _sig(1.0, "bar"),
                "maf_sensor": _sig(40 + boost * 300, "kg/hr"),
                "battery": _sig(14.1 if rpm > 900 else 12.6, "V"),
                "accel_pedal_pct": _sig(100 * max(0.0, math.sin(phase * math.pi)), "%"),
                "injection_qty": _sig(inj, "mg/stroke"),
                "fuel_rate": _sig(fuel_rate, "L/h", "candidate"),
                "economy": _sig(fuel_rate / max(speed, 5) * 100, "L/100km", "candidate"),
                "balance_1": _sig(random.uniform(-0.4, 0.4), "", "proven"),
                "balance_2": _sig(random.uniform(-0.4, 0.4), "", "proven"),
                "balance_3": _sig(random.uniform(-0.4, 0.4), "", "proven"),
                "balance_4": _sig(random.uniform(-0.4, 0.4), "", "proven"),
                "balance_5": _sig(random.uniform(-0.4, 0.4), "", "proven"),
                "brake_switch_2": _sig(1 if speed < 2 else 0, ""),
                "brake_main": _sig(1 if speed < 2 else 0, ""),
                "fuel_pump_relay": _sig(1, ""),
                # the rest of the Nanocom "Inputs" set, as d2diag names them
                "rpm_error": _sig(random.uniform(-12, 12) if rpm < 900 else 0, "rpm"),
                "accel_way1": _sig(0.6 + 3.2 * max(0.0, math.sin(phase * math.pi)), "V"),
                "accel_way2": _sig(0.3 + 1.6 * max(0.0, math.sin(phase * math.pi)), "V"),
                "accel_way3": _sig(0.3 + 1.6 * max(0.0, math.sin(phase * math.pi)), "V"),
                "accel_supply": _sig(4.98, "V"),
                "egr_modulator": _sig(0 if boost > 1.3 else 35.0, "%", "candidate"),
                "egr_inlet": _sig(0 if boost > 1.3 else 20.0, "%", "candidate"),
                "wastegate_modulator": _sig(min(95.0, (boost - 1.0) * 110), "%", "candidate"),
                "cruise_master": _sig(0, ""),
                "cruise_set": _sig(0, ""),
                "cruise_resume": _sig(0, ""),
                "ambient_press_2": _sig(1.0, "bar", "candidate"),
                "battery_direct": _sig(14.05 if rpm > 900 else 12.55, "V", "candidate"),
                "driver_demand": _sig(inj * 1.05, "mg/stroke", "candidate"),
                "smoke_limit": _sig(48.0, "mg/stroke", "candidate"),
                "torque_limit": _sig(52.0, "mg/stroke", "candidate"),
                "maf": _sig(40 + boost * 290, "kg/hr", "candidate"),
                "maf_sensor_v": _sig(1.2 + boost * 1.1, "V", "candidate"),
                "coolant_sensor_v": _sig(3.9 - coolant * 0.025, "V", "candidate"),
                "intake_sensor_v": _sig(2.4, "V", "candidate"),
                "fuel_sensor_v": _sig(2.1, "V", "candidate"),
                "egr_pos": _sig(0 if boost > 1.3 else 34.0, "%", "candidate"),
                "wastegate_pos": _sig(min(95.0, (boost - 1.0) * 110), "%", "candidate"),
                "ext_temp": _sig(24.0, "°C", "candidate"),
            },
            "faults": list(self._faults),
        }

    def command(self, action: str, params: dict | None = None) -> dict:
        if action == "clear_faults":
            self._faults = []
            return {"ok": True, "message": "Fault codes cleared (simulated)"}
        if action == "read_identity":
            return {"ok": True, "message": "ECU identity", "identity": {
                "part_no": "NNN500120", "software_no": "SIM", "build_date": "2002-11"}}
        if action == "security_status":
            return {"ok": True, "message": "Immobiliser: not immobilised (simulated)", "status": 3}
        if action.startswith("output_") or action.startswith("injector_"):
            return {"ok": True, "message": f"{action} (simulated)"}
        return {"ok": False, "error": f"unknown command: {action}"}


class SimSlabs:
    name = "slabs"

    def __init__(self) -> None:
        self._t0 = time.monotonic()
        self._connected = False
        self.on_progress = None
        self._faults = ["unknown (byte 3, bit 4) (Logged)"]
        self._target = 150.0
        self._left = 150.0
        self._right = 148.0

    def is_connected(self) -> bool:
        return self._connected

    def disconnect(self) -> None:
        self._connected = False

    def poll(self) -> dict:
        if not self._connected:
            if self.on_progress:
                self.on_progress("SLABS fast init 0x29, functional (simulated)")
            time.sleep(2.0)
            self._connected = True
        t = time.monotonic() - self._t0
        self._left += (self._target - self._left) * 0.1 + random.uniform(-0.5, 0.5)
        self._right += (self._target - self._right) * 0.1 + random.uniform(-0.5, 0.5)
        batt = 14.0 + 0.1 * math.sin(t)
        return {
            "status": "connected",
            "source": self.name,
            "signals": {
                "height_left": _sig(self._left, "raw"),
                "height_right": _sig(self._right, "raw"),
                "height_left_mm": _sig(self._left * 1.4, "mm"),
                "height_right_mm": _sig(self._right * 1.4, "mm"),
                "battery": _sig(batt, "V"),
                "ecu_supply": _sig(batt - 0.2, "V"),
                "wheel_speed_fl": _sig(0, "", "candidate"),
                "wheel_speed_fr": _sig(0, "", "candidate"),
                "wheel_speed_rl": _sig(0, "", "candidate"),
                "wheel_speed_rr": _sig(0, "", "candidate"),
                "abs_sensor_fl": _sig(0.02, "V", "candidate"),
                "abs_sensor_fr": _sig(0.02, "V", "candidate"),
                "abs_sensor_rl": _sig(0.01, "V", "candidate"),
                "abs_sensor_rr": _sig(0.02, "V", "candidate"),
                "any_door": _sig(0, ""),
                "reverse_gear": _sig(0, ""),
                "neutral_gear": _sig(1, ""),
                "diff_lock": _sig(0, ""),
                "transfer_low": _sig(0, ""),
                "brake_analog": _sig(12, "raw"),
            },
            "faults": list(self._faults),
        }

    def command(self, action: str, params: dict | None = None) -> dict:
        if action == "clear_faults":
            self._faults = []
            return {"ok": True, "message": "Fault codes cleared (simulated)"}
        if action in ("raise_left", "raise_right"):
            self._target = min(190.0, self._target + 10)
            return {"ok": True, "message": f"{action} (simulated)"}
        if action in ("lower_left", "lower_right"):
            self._target = max(110.0, self._target - 10)
            return {"ok": True, "message": f"{action} (simulated)"}
        if action in ("buzzer", "compressor", "exhaust", "pump_on", "pump_off",
                      "wheel_fl", "wheel_fr", "wheel_rl", "wheel_rr",
                      "bleed_power_on", "bleed_power_off", "bleed_module"):
            return {"ok": True, "message": f"{action} (simulated)"}
        return {"ok": False, "error": f"unknown command: {action}"}


def make_sim_sources() -> dict:
    return {"td5": SimTd5(), "slabs": SimSlabs()}
