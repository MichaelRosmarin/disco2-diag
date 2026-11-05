"""The ESP32 sensor board: a second serial device, independent of the K-line.

The board streams one JSON object per line at 115200 baud, a few times a second:

    {"egt": 412.5, "oil_press": 3.1, "oil_temp": 96.0, "gearbox_temp": 82.5,
     "fuel_level": 61, "aux_temp": 24.1, "alarm": 0, "up": 12345}

Keys are signal names as the dashboard shows them; unknown keys pass straight through,
so adding a sensor to the firmware needs no change here. "alarm" is the board's own
alarm state (it has a buzzer and fires on its own thresholds, so a Pi reboot never
silences it). Reads run on their own thread; `latest()` is what the engine merges into
every snapshot.

Port auto-detection picks a CP210x / CH340 / ESP32-native USB serial device and never an
FTDI (that is the K-line cable).
"""
from __future__ import annotations

import glob
import json
import logging
import os
import random
import threading
import time

log = logging.getLogger("d2dash.sensors")

UNITS = {"egt": "°C", "oil_press": "bar", "oil_temp": "°C", "gearbox_temp": "°C",
         "fuel_level": "%", "aux_temp": "°C", "board_temp": "°C", "vin": "V"}
STALE_AFTER = 3.0   # seconds without a line → stale


def find_port() -> str | None:
    """First serial device that looks like an ESP32 dev board, by USB id or name."""
    for p in sorted(glob.glob("/dev/serial/by-id/*")):
        n = os.path.basename(p).lower()
        if "ftdi" in n or "ft232" in n:
            continue
        if any(k in n for k in ("cp210", "silicon_labs", "ch340", "qinheng", "1a86", "espressif", "esp32", "usb_jtag")):
            return os.path.realpath(p)
    return None


class SerialSensors:
    name = "sensors"

    def __init__(self, port: str = "auto", baud: int = 115200) -> None:
        self._spec = port
        self._baud = baud
        self._lock = threading.Lock()
        self._signals: dict = {}
        self._updated = 0.0
        self._status = "starting"
        self._error = ""
        self._port = ""
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="d2dash-sensors", daemon=True)
        self.on_update = None   # set by the engine: called after each decoded line

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def latest(self) -> dict:
        with self._lock:
            age = time.time() - self._updated if self._updated else None
            stale = age is not None and age > STALE_AFTER
            return {"status": "stale" if (self._status == "connected" and stale) else self._status,
                    "port": self._port, "error": self._error, "age": round(age, 1) if age is not None else None,
                    "signals": dict(self._signals)}

    # ---- worker ----------------------------------------------------------------------

    def _open(self):
        import serial  # pyserial, pulled in by openostler
        port = self._spec
        if port == "auto":
            port = find_port()
            if not port:
                raise FileNotFoundError("no ESP32 serial device found")
        self._port = port
        return serial.Serial(port, self._baud, timeout=1.0)

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                ser = self._open()
            except Exception as exc:  # noqa: BLE001
                with self._lock:
                    self._status, self._error = "error", f"{type(exc).__name__}: {exc}"
                self._stop.wait(5.0)
                continue
            log.info("sensor board on %s", self._port)
            with self._lock:
                self._status, self._error = "connected", ""
            try:
                with ser:
                    ser.reset_input_buffer()
                    while not self._stop.is_set():
                        raw = ser.readline()
                        if not raw:
                            continue
                        line = raw.decode("utf-8", "replace").strip()
                        if not line.startswith("{"):
                            continue
                        try:
                            obj = json.loads(line)
                        except ValueError:
                            continue
                        self._ingest(obj)
            except Exception as exc:  # noqa: BLE001
                log.warning("sensor board lost: %s", exc)
                with self._lock:
                    self._status, self._error = "error", f"{type(exc).__name__}: {exc}"
                self._stop.wait(2.0)

    def _ingest(self, obj: dict) -> None:
        sig = {}
        for k, v in obj.items():
            if k in ("up", "seq") or not isinstance(v, (int, float)):
                continue
            sig[k] = {"v": round(float(v), 2), "u": UNITS.get(k, ""), "s": None, "c": "proven"}
        with self._lock:
            self._signals = sig
            self._updated = time.time()
            self._status = "connected"
        if self.on_update:
            self.on_update()


class SimSensors(SerialSensors):
    """Drifting fake values, same contract. Used with --simulate."""

    def __init__(self) -> None:
        super().__init__(port="sim")
        self._t = random.random() * 100

    def _run(self) -> None:
        import math
        self._port = "sim"
        while not self._stop.is_set():
            self._t += 0.25
            t = self._t
            self._ingest({
                "egt": 380 + 180 * (0.5 + 0.5 * math.sin(t / 7)),
                "oil_press": 2.4 + 1.2 * (0.5 + 0.5 * math.sin(t / 9)),
                "oil_temp": 92 + 6 * math.sin(t / 23),
                "gearbox_temp": 78 + 9 * math.sin(t / 31),
                "fuel_level": 63 - (t % 600) / 60,
                "aux_temp": 27.5 + math.sin(t / 50),
                "alarm": 0,
                "up": int(t * 4),
            })
            self._stop.wait(0.25)
