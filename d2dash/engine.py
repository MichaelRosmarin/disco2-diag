"""The poller: one worker thread talks to one ECU at a time over the shared K-line.

K-line is a single bus, so Td5 and SLABS cannot be streamed together. The engine polls
the active module continuously, and switches on request: release the current session,
establish the other one (SLABS needs up to ~30 s of bus silence after Td5 traffic).

Everything the UI needs is in `Engine.snapshot()`; commands go through `Engine.command()`.
Every poll is appended to a per-session CSV so a misbehaving drive can be reviewed later.
"""
from __future__ import annotations

import csv
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

from .config import Config

log = logging.getLogger("d2dash.engine")

MODULES = ("td5", "slabs")

# Actions that write to an ECU or move hardware. The server refuses these unless the
# request carries confirm=true, which the dashboard only sends after an on-screen prompt.
WRITE_ACTIONS = {
    "td5": {"clear_faults", "output_fuel_pump", "output_mil_lamp", "output_ac_clutch",
            "output_ac_fan", "output_glow_plugs", "output_rev_counter", "output_temp_gauge",
            "output_egr_throttle", "output_wastegate",
            "injector_1", "injector_2", "injector_3", "injector_4", "injector_5"},
    "slabs": {"clear_faults", "buzzer", "compressor", "exhaust", "pump_on", "pump_off",
              "raise_left", "raise_right", "lower_left", "lower_right",
              "wheel_fl", "wheel_fr", "wheel_rl", "wheel_rr",
              "bleed_power_on", "bleed_power_off", "bleed_module"},
}
READ_ACTIONS = {
    "td5": {"read_identity", "security_status"},
    "slabs": set(),
}


@dataclass
class Snapshot:
    module: str
    status: str = "starting"          # starting | connecting | connected | error | switching
    progress: str = ""                # live text while an establish is in flight
    error: str = ""
    signals: dict = field(default_factory=dict)
    faults: list = field(default_factory=list)
    stale: bool = False
    updated: float = 0.0              # unix time of the last successful poll
    polls: int = 0
    log_file: str = ""
    seq: int = 0

    def as_dict(self) -> dict:
        d = self.__dict__.copy()
        d["age"] = round(time.time() - self.updated, 1) if self.updated else None
        return d


class SessionLog:
    """One CSV per (module, connection). Columns are fixed from the first row that has data."""

    def __init__(self, log_dir: str, module: str) -> None:
        os.makedirs(log_dir, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.path = os.path.join(log_dir, f"{stamp}-{module}.csv")
        self._fh = None
        self._writer = None
        self._fields: list[str] = []
        self._rows = 0

    def write(self, signals: dict, faults: list) -> None:
        if not signals:
            return
        if self._writer is None:
            self._fields = ["time", *sorted(signals), "faults"]
            self._fh = open(self.path, "a", newline="", buffering=1)
            self._writer = csv.DictWriter(self._fh, fieldnames=self._fields, extrasaction="ignore")
            self._writer.writeheader()
        row = {"time": datetime.now().isoformat(timespec="milliseconds"),
               "faults": "; ".join(faults)}
        for k in self._fields[1:-1]:
            v = signals.get(k)
            row[k] = v.get("v") if isinstance(v, dict) else v
        self._writer.writerow(row)
        self._rows += 1

    def close(self) -> None:
        if self._fh:
            self._fh.close()
            self._fh = None
            if self._rows == 0 and os.path.exists(self.path):
                os.remove(self.path)  # don't litter the log dir with empty sessions


class Engine:
    def __init__(self, cfg: Config, sources: dict[str, Any]) -> None:
        self.cfg = cfg
        self.sources = sources
        self._module = cfg.default_module if cfg.default_module in sources else next(iter(sources))
        self._requested: str | None = None
        self._snap = Snapshot(module=self._module)
        self._lock = threading.Lock()
        self._cv = threading.Condition(self._lock)
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="d2dash-poller", daemon=True)
        self._log: SessionLog | None = None
        self._cmd_queue: list[tuple[str, dict, threading.Event, dict]] = []
        self.started = time.time()

    # ---- public API ------------------------------------------------------------------

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=10)
        self._disconnect_current()

    def snapshot(self) -> dict:
        with self._lock:
            return self._snap.as_dict()

    def wait_for_change(self, seq: int, timeout: float) -> dict:
        with self._cv:
            self._cv.wait_for(lambda: self._snap.seq != seq, timeout=timeout)
            return self._snap.as_dict()

    def modules(self) -> list[str]:
        return list(self.sources)

    def request_module(self, module: str) -> dict:
        if module not in self.sources:
            return {"ok": False, "error": f"unknown module: {module}"}
        with self._lock:
            if module == self._module and self._requested is None:
                return {"ok": True, "message": f"{module} already active"}
            self._requested = module
            self._snap.status = "switching"
            self._snap.progress = f"switching to {module}"
            self._bump()
        return {"ok": True, "message": f"switching to {module}"}

    def command(self, action: str, params: dict | None = None, *, confirm: bool = False) -> dict:
        """Run an ECU command on the poller thread (the serial port is not thread-safe)."""
        params = params or {}
        module = self._module
        if action in WRITE_ACTIONS.get(module, set()):
            if not confirm:
                return {"ok": False, "error": f"'{action}' writes to the {module} ECU; confirm first"}
        elif action not in READ_ACTIONS.get(module, set()):
            return {"ok": False, "error": f"unknown command for {module}: {action}"}
        done = threading.Event()
        result: dict = {}
        with self._lock:
            self._cmd_queue.append((action, params, done, result))
        if not done.wait(timeout=60):
            return {"ok": False, "error": "command timed out"}
        return result

    # ---- worker ----------------------------------------------------------------------

    def _bump(self) -> None:
        """Caller holds the lock."""
        self._snap.seq += 1
        self._cv.notify_all()

    def _set_progress(self, text: str) -> None:
        with self._lock:
            self._snap.progress = text
            self._snap.status = "connecting"
            self._bump()
        log.info("%s: %s", self._module, text)

    def _disconnect_current(self) -> None:
        src = self.sources.get(self._module)
        try:
            if src is not None:
                src.disconnect()
        except Exception as exc:  # noqa: BLE001
            log.warning("disconnect %s failed: %s", self._module, exc)
        if self._log:
            self._log.close()
            self._log = None

    def _interval(self) -> float:
        return self.cfg.slabs_interval if self._module == "slabs" else self.cfg.td5_interval

    def _run(self) -> None:
        log.info("poller started, module=%s", self._module)
        was_connected = False
        while not self._stop.is_set():
            # 1. module switch?
            with self._lock:
                req = self._requested
                self._requested = None
            if req and req != self._module:
                log.info("switching %s -> %s", self._module, req)
                self._disconnect_current()
                self._module = req
                was_connected = False
                with self._lock:
                    self._snap = Snapshot(module=req, status="connecting",
                                          progress="releasing bus, then establishing",
                                          seq=self._snap.seq)
                    self._bump()

            src = self.sources[self._module]
            src.on_progress = self._set_progress

            # 2. queued commands run on this thread, between polls
            with self._lock:
                cmds, self._cmd_queue = self._cmd_queue, []
            for action, params, done, result in cmds:
                try:
                    result.update(src.command(action, params))
                except Exception as exc:  # noqa: BLE001
                    result.update({"ok": False, "error": f"{type(exc).__name__}: {exc}"})
                log.info("command %s on %s -> %s", action, self._module, result)
                done.set()

            # 3. poll
            t0 = time.monotonic()
            try:
                data = src.poll()
            except Exception as exc:  # noqa: BLE001
                data = {"status": "error", "error": f"{type(exc).__name__}: {exc}",
                        "signals": {}, "faults": []}
            connected = data.get("status") == "connected"
            if connected and not was_connected:
                self._log = SessionLog(self.cfg.log_dir, self._module)
                log.info("%s connected; logging to %s", self._module, self._log.path)
            if not connected and was_connected:
                log.warning("%s lost: %s", self._module, data.get("error", ""))
                if self._log:
                    self._log.close()
                    self._log = None
            was_connected = connected
            if connected and self._log:
                try:
                    self._log.write(data.get("signals", {}), data.get("faults", []))
                except Exception as exc:  # noqa: BLE001
                    log.warning("log write failed: %s", exc)

            with self._lock:
                s = self._snap
                s.module = self._module
                s.status = "connected" if connected else "error"
                s.error = "" if connected else str(data.get("error", "")).strip()
                s.progress = "" if connected else s.progress
                s.stale = bool(data.get("stale", False))
                if connected:
                    s.signals = data.get("signals", {})
                    s.faults = list(data.get("faults", []))
                    s.updated = time.time()
                    s.polls += 1
                    s.log_file = self._log.path if self._log else ""
                self._bump()

            # 4. pace. A failed poll means establish just failed (that already slept
            #    inside the library); back off a little before trying again.
            elapsed = time.monotonic() - t0
            wait = (self._interval() - elapsed) if connected else 3.0
            if wait > 0:
                self._stop.wait(wait)
        self._disconnect_current()
        log.info("poller stopped")
