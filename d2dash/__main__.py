"""Entry point: `python -m d2dash` or the `d2dash` console script."""
from __future__ import annotations

import argparse
import logging
import os
import signal
import sys

from .config import Config
from .engine import Engine
from .server import serve


def build_sources(cfg: Config) -> dict:
    if cfg.simulate:
        from .sim import make_sim_sources
        return make_sim_sources()
    try:
        from d2diag.sources import make_sources
    except ImportError as exc:  # pragma: no cover - depends on the Pi install
        sys.exit(
            f"d2diag is not installed ({exc}). Run deploy/install.sh, or set D2DASH_SIMULATE=1 "
            "to use the simulator.")
    state_dir = os.path.join(cfg.log_dir, "state")
    os.makedirs(state_dir, exist_ok=True)
    return make_sources(cfg.port, raw_log_dir=cfg.raw_log_dir, state_dir=state_dir,
                        module_ids=["td5", "slabs"])


def build_sensors(cfg: Config):
    """The ESP32 board, the simulator, or nothing (D2DASH_SENSORS_PORT=none).

    With --simulate the board is simulated too, unless a real port is named explicitly:
    `--simulate --sensors-port /dev/ttyUSB1` is how to bench-test a real board without the car.
    """
    if cfg.sensors_port.lower() in ("none", "off", ""):
        return None
    if cfg.simulate and cfg.sensors_port == "auto":
        from .sensors import SimSensors
        return SimSensors()
    from .sensors import SerialSensors
    return SerialSensors(cfg.sensors_port)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="d2dash", description="Discovery 2 Td5/SLABS dashboard")
    ap.add_argument("--simulate", action="store_true", help="use the built-in simulator")
    ap.add_argument("--port", help="serial port (default: $D2DASH_PORT or auto)")
    ap.add_argument("--http-port", type=int, help="HTTP port (default: $D2DASH_HTTP_PORT or 8080)")
    ap.add_argument("--log-dir", help="session CSV directory")
    ap.add_argument("--sensors-port", help="ESP32 sensor board port: auto (default), none, or a device")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)

    if args.simulate:
        os.environ["D2DASH_SIMULATE"] = "1"
    if args.port:
        os.environ["D2DASH_PORT"] = args.port
    if args.http_port:
        os.environ["D2DASH_HTTP_PORT"] = str(args.http_port)
    if args.log_dir:
        os.environ["D2DASH_LOG_DIR"] = args.log_dir
    if args.sensors_port:
        os.environ["D2DASH_SENSORS_PORT"] = args.sensors_port

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    cfg = Config.from_env()
    logging.getLogger("d2dash").info(
        "starting: port=%s http=%s:%d simulate=%s logs=%s",
        cfg.port, cfg.http_host, cfg.http_port, cfg.simulate, cfg.log_dir)

    engine = Engine(cfg, build_sources(cfg), sensors=build_sensors(cfg))
    engine.start()

    def _stop(*_):
        logging.getLogger("d2dash").info("shutting down")
        engine.stop()
        sys.exit(0)

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    serve(engine, cfg.http_host, cfg.http_port)


if __name__ == "__main__":
    main()
