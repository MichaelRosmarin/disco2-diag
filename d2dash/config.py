"""Runtime configuration from environment variables (see deploy/install.sh for the file)."""
from __future__ import annotations

import os
from dataclasses import dataclass


def _env_bool(name: str, default: bool) -> bool:
    v = os.environ.get(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Config:
    port: str                 # serial port, or "auto" to find the FTDI cable
    http_host: str
    http_port: int
    log_dir: str              # where session CSVs go
    simulate: bool            # run against the built-in simulator instead of the car
    default_module: str       # module polled at boot: "td5" or "slabs"
    td5_interval: float       # seconds between Td5 polls
    slabs_interval: float     # seconds between SLABS polls (the ECU tolerates ~1 Hz)
    raw_log_dir: str | None   # optional raw K-line capture dir (for mapping work)
    sensors_port: str = "auto"  # ESP32 sensor board: serial port, "auto", or "none"

    @classmethod
    def from_env(cls) -> "Config":
        log_dir = os.environ.get("D2DASH_LOG_DIR", os.path.expanduser("~/d2dash-logs"))
        return cls(
            port=os.environ.get("D2DASH_PORT", "auto"),
            http_host=os.environ.get("D2DASH_HTTP_HOST", "0.0.0.0"),
            http_port=int(os.environ.get("D2DASH_HTTP_PORT", "8080")),
            log_dir=log_dir,
            simulate=_env_bool("D2DASH_SIMULATE", False),
            default_module=os.environ.get("D2DASH_DEFAULT_MODULE", "td5"),
            td5_interval=float(os.environ.get("D2DASH_TD5_INTERVAL", "0.5")),
            slabs_interval=float(os.environ.get("D2DASH_SLABS_INTERVAL", "1.0")),
            raw_log_dir=os.environ.get("D2DASH_RAW_LOG_DIR") or None,
            sensors_port=os.environ.get("D2DASH_SENSORS_PORT", "auto"),
        )
