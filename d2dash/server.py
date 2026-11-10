"""Tiny HTTP server: the dashboard page, a JSON API and a Server-Sent-Events live feed.

Standard library only, so it runs on a stock Raspberry Pi OS Lite with nothing installed.
Routes:
    GET  /                      dashboard page
    GET  /api/status            engine status + modules + uptime
    GET  /api/snapshot          current snapshot of the active module
    GET  /api/events            SSE stream of snapshots (one event per poll)
    POST /api/module            {"module": "td5"|"slabs"}  switch the active ECU
    POST /api/command           {"action": "...", "params": {}, "confirm": true}
    GET  /api/faults/reference  {module: {fault name: likely cause}}
    GET  /api/faults/library    {module: {fault name: full write-up}} (see faultkb.py)
    GET  /api/vehicle           tyre sizes and the speed factor;  POST {factory, fitted} to change
    GET  /api/logs              list session CSVs
    GET  /api/logs/<name>       download one
    DELETE /api/logs/<name>     remove one
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import __version__
from .engine import Engine

log = logging.getLogger("d2dash.server")
STATIC = os.path.join(os.path.dirname(__file__), "static")
DATA = os.path.join(os.path.dirname(__file__), "data")
_SAFE_NAME = re.compile(r"^[A-Za-z0-9._-]+\.csv$")
_fault_ref_cache: dict | None = None


def fault_reference() -> dict:
    """{module: {fault name: cause}} from d2diag's dictionaries when installed, else the
    vendored copies in d2dash/data (same data, CC BY-SA, see data/README.md)."""
    global _fault_ref_cache
    if _fault_ref_cache is not None:
        return _fault_ref_cache
    out: dict = {}
    for mod in ("td5", "slabs"):
        rows = None
        try:
            from importlib import resources
            rows = json.loads((resources.files("d2diag") / "dtc" / f"{mod}.json").read_text("utf-8"))
        except Exception:  # noqa: BLE001 - d2diag absent (simulator) or layout changed
            try:
                with open(os.path.join(DATA, f"dtc-{mod}.json"), encoding="utf-8") as fh:
                    rows = json.load(fh)
            except OSError:
                rows = []
        out[mod] = {r["name"]: r.get("cause", "") for r in rows if r.get("name")}
    _fault_ref_cache = out
    return out


_fault_lib_cache: dict | None = None


def fault_library() -> dict:
    """{module: {fault name: write-up}} for every fault the dictionaries name."""
    global _fault_lib_cache
    if _fault_lib_cache is None:
        from . import faultkb
        ref = fault_reference()
        _fault_lib_cache = {mod: faultkb.library(mod, list(names)) for mod, names in ref.items()}
    return _fault_lib_cache


_SIGNAL = re.compile(r"^[a-z][a-z0-9_]{0,40}$")


def _thresholds_path(log_dir: str) -> str:
    return os.path.join(log_dir, "state", "thresholds.json")


def load_thresholds(log_dir: str) -> dict:
    """User overrides of the dashboard's alarm limits: {signal: {"warn": [lo, hi], "alarm": [lo, hi]}}.
    Values may be null (no limit on that side). The page merges them over its defaults."""
    try:
        with open(_thresholds_path(log_dir), encoding="utf-8") as fh:
            return validate_thresholds(json.load(fh))
    except (OSError, ValueError):
        return {}


def validate_thresholds(ov: dict) -> dict:
    if not isinstance(ov, dict):
        raise ValueError("overrides must be an object")
    out: dict = {}
    for sig, spec in ov.items():
        if not _SIGNAL.match(str(sig)) or not isinstance(spec, dict):
            raise ValueError(f"bad signal {sig!r}")
        clean: dict = {}
        for level in ("warn", "alarm"):
            if level not in spec:
                continue
            pair = spec[level]
            if not (isinstance(pair, list) and len(pair) == 2):
                raise ValueError(f"{sig}.{level} must be [low, high]")
            vals = []
            for v in pair:
                if v is None or v == "":
                    vals.append(None)
                else:
                    try:
                        vals.append(float(v))
                    except (TypeError, ValueError):
                        raise ValueError(f"{sig}.{level}: {v!r} is not a number") from None
            if vals[0] is not None and vals[1] is not None and vals[0] >= vals[1]:
                raise ValueError(f"{sig}.{level}: low must be below high")
            clean[level] = vals
        w, a = clean.get("warn"), clean.get("alarm")
        if w and a:
            if w[1] is not None and a[1] is not None and a[1] < w[1]:
                raise ValueError(f"{sig}: red high must be at or above amber high")
            if w[0] is not None and a[0] is not None and a[0] > w[0]:
                raise ValueError(f"{sig}: red low must be at or below amber low")
        if clean:
            out[sig] = clean
    return out


def save_thresholds(log_dir: str, ov: dict) -> None:
    p = _thresholds_path(log_dir)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(ov, fh, indent=1)
    os.replace(tmp, p)


def _vehicle_path(log_dir: str) -> str:
    return os.path.join(log_dir, "state", "vehicle.json")


def load_vehicle(log_dir: str) -> dict:
    """Vehicle settings that change how values are shown (tyre sizes → speed factor)."""
    from . import tyres
    try:
        with open(_vehicle_path(log_dir), encoding="utf-8") as fh:
            return tyres.validate(json.load(fh))
    except (OSError, ValueError):
        return dict(tyres.DEFAULT)


def save_vehicle(log_dir: str, v: dict) -> None:
    p = _vehicle_path(log_dir)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p + ".tmp", "w", encoding="utf-8") as fh:
        json.dump(v, fh, indent=1)
    os.replace(p + ".tmp", p)


def speed_factor(log_dir: str) -> float:
    from . import tyres
    v = load_vehicle(log_dir)
    return tyres.factor(v["factory"], v["fitted"])


def make_handler(engine: Engine):
    class Handler(BaseHTTPRequestHandler):
        server_version = f"d2dash/{__version__}"
        protocol_version = "HTTP/1.1"

        # ---- helpers ------------------------------------------------------------
        def log_message(self, fmt, *args):  # quieter than the default
            log.debug("%s " + fmt, self.address_string(), *args)

        def _json(self, obj, status=HTTPStatus.OK) -> None:
            body = json.dumps(obj).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _file(self, path: str, ctype: str, download: str | None = None) -> None:
            try:
                with open(path, "rb") as fh:
                    body = fh.read()
            except OSError:
                return self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            if download:
                self.send_header("Content-Disposition", f'attachment; filename="{download}"')
            self.send_header("Cache-Control", "max-age=86400" if ctype.startswith("font/") else "no-cache")
            self.end_headers()
            self.wfile.write(body)

        def _body(self) -> dict:
            n = int(self.headers.get("Content-Length") or 0)
            if n == 0:
                return {}
            try:
                return json.loads(self.rfile.read(n) or b"{}")
            except json.JSONDecodeError:
                return {}

        def _log_path(self, name: str) -> str | None:
            if not _SAFE_NAME.match(name):
                return None
            p = os.path.join(engine.cfg.log_dir, name)
            return p if os.path.isfile(p) else None

        # ---- GET ----------------------------------------------------------------
        def do_GET(self) -> None:  # noqa: N802
            path = self.path.split("?", 1)[0]
            if path in ("/", "/index.html"):
                return self._file(os.path.join(STATIC, "index.html"), "text/html; charset=utf-8")
            if path == "/api/status":
                return self._json({
                    "version": __version__,
                    "modules": engine.modules(),
                    "active": engine.snapshot()["module"],
                    "simulate": engine.cfg.simulate,
                    "port": engine.cfg.port,
                    "uptime": round(time.time() - engine.started),
                    "log_dir": engine.cfg.log_dir,
                })
            if path == "/api/snapshot":
                return self._json(engine.snapshot())
            if path == "/api/events":
                return self._sse()
            if path == "/api/faults/reference":
                return self._json(fault_reference())
            if path == "/api/faults/library":
                return self._json(fault_library())
            if path == "/api/thresholds":
                return self._json({"overrides": load_thresholds(engine.cfg.log_dir)})
            if path == "/api/vehicle":
                from . import tyres
                return self._json(tyres.describe(load_vehicle(engine.cfg.log_dir)))
            if path == "/api/trips":
                from . import trips as T
                sessions = T.list_sessions(engine.cfg.log_dir)
                out = []
                for t in reversed(T.group_trips(sessions)):
                    rows = T.load_trip(engine.cfg.log_dir, t)
                    s = T.summarize(rows, speed_factor(engine.cfg.log_dir))
                    if s:
                        out.append({"id": t["id"], "sessions": t["sessions"], "slabs": t["slabs"], **s})
                return self._json({"trips": out})
            if path.startswith("/api/trips/"):
                from . import trips as T
                tid = path[len("/api/trips/"):]
                if not re.fullmatch(r"\d{8}-\d{6}", tid):
                    return self._json({"error": "bad trip id"}, 404)
                trip = next((t for t in T.group_trips(T.list_sessions(engine.cfg.log_dir)) if t["id"] == tid), None)
                if trip is None:
                    return self._json({"error": "no such trip"}, 404)
                rows = T.load_trip(engine.cfg.log_dir, trip)
                sf = speed_factor(engine.cfg.log_dir)
                return self._json({"id": tid, "summary": T.summarize(rows, sf), "replay": T.replay(rows, speed_factor=sf),
                                   "fingerprint": T.fingerprint(rows)})
            if path == "/api/health":
                from . import trips as T
                return self._json(T.health(engine.cfg.log_dir))
            if path == "/api/logs":
                return self._json({"logs": self._list_logs()})
            if path.startswith("/api/logs/"):
                p = self._log_path(path[len("/api/logs/"):])
                if not p:
                    return self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)
                return self._file(p, "text/csv", download=os.path.basename(p))
            if path.startswith("/static/"):
                rel = path[len("/static/"):].lstrip("/")
                p = os.path.realpath(os.path.join(STATIC, rel))
                if p.startswith(os.path.realpath(STATIC) + os.sep) and os.path.isfile(p):
                    ctype = {"css": "text/css", "js": "application/javascript", "svg": "image/svg+xml",
                             "woff": "font/woff", "woff2": "font/woff2",
                             "png": "image/png"}.get(rel.rsplit(".", 1)[-1], "application/octet-stream")
                    return self._file(p, ctype)
            self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)

        def _list_logs(self) -> list[dict]:
            out = []
            d = engine.cfg.log_dir
            if os.path.isdir(d):
                for name in sorted(os.listdir(d), reverse=True):
                    if _SAFE_NAME.match(name):
                        st = os.stat(os.path.join(d, name))
                        out.append({"name": name, "size": st.st_size, "mtime": int(st.st_mtime)})
            return out[:200]

        def _sse(self) -> None:
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("X-Accel-Buffering", "no")
            self.end_headers()
            seq = -1
            try:
                while True:
                    snap = engine.wait_for_change(seq, timeout=15.0)
                    if snap["seq"] == seq:
                        self.wfile.write(b": keepalive\n\n")
                    else:
                        seq = snap["seq"]
                        self.wfile.write(f"data: {json.dumps(snap)}\n\n".encode())
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass

        # ---- POST / DELETE ------------------------------------------------------
        def do_POST(self) -> None:  # noqa: N802
            path = self.path.split("?", 1)[0]
            body = self._body()
            if path == "/api/module":
                return self._json(engine.request_module(str(body.get("module", ""))))
            if path == "/api/command":
                action = str(body.get("action", ""))
                res = engine.command(action, body.get("params") or {},
                                     confirm=bool(body.get("confirm", False)))
                return self._json(res, HTTPStatus.OK if res.get("ok") else HTTPStatus.BAD_REQUEST)
            if path == "/api/vehicle":
                from . import tyres
                try:
                    v = tyres.validate(body)
                except ValueError as exc:
                    return self._json({"ok": False, "error": str(exc)}, HTTPStatus.BAD_REQUEST)
                save_vehicle(engine.cfg.log_dir, v)
                return self._json({"ok": True, **tyres.describe(v)})
            if path == "/api/thresholds":
                try:
                    ov = validate_thresholds(body.get("overrides") or {})
                except ValueError as exc:
                    return self._json({"ok": False, "error": str(exc)}, HTTPStatus.BAD_REQUEST)
                save_thresholds(engine.cfg.log_dir, ov)
                return self._json({"ok": True, "overrides": ov})
            self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)

        def do_DELETE(self) -> None:  # noqa: N802
            path = self.path.split("?", 1)[0]
            if path == "/api/thresholds":
                save_thresholds(engine.cfg.log_dir, {})
                return self._json({"ok": True, "overrides": {}})
            if path.startswith("/api/logs/"):
                p = self._log_path(path[len("/api/logs/"):])
                if not p:
                    return self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)
                os.remove(p)
                return self._json({"ok": True})
            self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)

    return Handler


def serve(engine: Engine, host: str, port: int) -> None:
    httpd = ThreadingHTTPServer((host, port), make_handler(engine))
    httpd.daemon_threads = True
    log.info("dashboard on http://%s:%d/", host or "0.0.0.0", port)
    try:
        httpd.serve_forever()
    finally:
        httpd.server_close()
