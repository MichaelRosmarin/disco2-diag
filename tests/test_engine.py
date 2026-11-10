"""Engine + server tests against the simulator (no hardware, no network beyond localhost)."""
import json
import os
import threading
import time
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from d2dash.config import Config
from d2dash.engine import Engine
from d2dash.server import make_handler
from d2dash.sim import make_sim_sources


@pytest.fixture
def cfg(tmp_path):
    return Config(port="sim", http_host="127.0.0.1", http_port=0, log_dir=str(tmp_path),
                  simulate=True, default_module="td5", td5_interval=0.05,
                  slabs_interval=0.05, raw_log_dir=None)


@pytest.fixture
def engine(cfg):
    e = Engine(cfg, make_sim_sources())
    e.start()
    yield e
    e.stop()


def wait_connected(engine, module, timeout=8.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        s = engine.snapshot()
        if s["module"] == module and s["status"] == "connected":
            return s
        time.sleep(0.05)
    raise AssertionError(f"{module} never connected: {engine.snapshot()}")


def test_td5_polls_and_logs(engine, cfg):
    s = wait_connected(engine, "td5")
    assert "rpm" in s["signals"]
    time.sleep(0.3)
    s = engine.snapshot()
    assert s["polls"] >= 2
    assert os.path.exists(s["log_file"])
    with open(s["log_file"]) as fh:
        header = fh.readline()
    assert header.startswith("time,") and "rpm" in header and header.strip().endswith("faults")


def test_write_needs_confirm(engine):
    wait_connected(engine, "td5")
    r = engine.command("clear_faults")
    assert r["ok"] is False and "confirm" in r["error"]
    r = engine.command("clear_faults", confirm=True)
    assert r["ok"] is True
    time.sleep(0.2)
    assert engine.snapshot()["faults"] == []


def test_unknown_command_rejected(engine):
    wait_connected(engine, "td5")
    assert engine.command("format_ecu", confirm=True)["ok"] is False


def test_module_switch(engine):
    wait_connected(engine, "td5")
    r = engine.request_module("slabs")
    assert r["ok"]
    s = wait_connected(engine, "slabs")
    assert "height_left" in s["signals"]
    # a Td5-only write is refused while SLABS is active
    assert engine.command("output_fuel_pump", confirm=True)["ok"] is False
    assert engine.command("buzzer", confirm=True)["ok"] is True


def test_http_api(engine, cfg):
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(engine))
    httpd.daemon_threads = True
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"
    try:
        wait_connected(engine, "td5")
        page = urllib.request.urlopen(base + "/").read().decode()
        assert "<title>Disco 2</title>" in page
        snap = json.load(urllib.request.urlopen(base + "/api/snapshot"))
        assert snap["status"] == "connected"
        req = urllib.request.Request(base + "/api/command", data=b'{"action":"clear_faults"}',
                                     headers={"Content-Type": "application/json"}, method="POST")
        with pytest.raises(urllib.error.HTTPError) as ei:
            urllib.request.urlopen(req)
        assert ei.value.code == 400
        logs = json.load(urllib.request.urlopen(base + "/api/logs"))["logs"]
        assert logs and logs[0]["name"].endswith("-td5.csv")
        # path traversal is rejected
        with pytest.raises(urllib.error.HTTPError) as ei:
            urllib.request.urlopen(base + "/api/logs/..%2F..%2Fetc%2Fpasswd")
        assert ei.value.code == 404
    finally:
        httpd.shutdown()


def test_sensor_board_merges_into_snapshot_and_log(cfg):
    from d2dash.sensors import SimSensors
    e = Engine(cfg, make_sim_sources(), sensors=SimSensors())
    e.start()
    try:
        s = wait_connected(e, "td5")
        time.sleep(0.6)
        s = e.snapshot()
        assert s["sensors"]["status"] == "connected"
        assert "egt" in s["sensors"]["signals"] and s["sensors"]["signals"]["egt"]["u"] == "°C"
        with open(s["log_file"]) as fh:
            header = fh.readline()
        assert "sensor_egt" in header and "sensor_oil_press" in header
    finally:
        e.stop()


def test_sensor_line_parsing():
    from d2dash.sensors import SerialSensors
    s = SerialSensors(port="none")
    s._ingest({"egt": 512.25, "oil_press": 3.14159, "up": 99, "name": "ignored"})
    out = s.latest()
    assert out["status"] == "connected"
    assert out["signals"]["egt"] == {"v": 512.25, "u": "°C", "s": None, "c": "proven"}
    assert out["signals"]["oil_press"]["v"] == 3.14
    assert "up" not in out["signals"] and "name" not in out["signals"]


def test_fault_reference_endpoint(engine):
    from d2dash.server import fault_reference
    ref = fault_reference()
    assert len(ref["td5"]) > 190 and len(ref["slabs"]) > 50   # 211 bits, 196 distinct names
    assert ref["td5"]["coolant temp. circuit (Logged High)"]
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(engine))
    httpd.daemon_threads = True
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        r = json.load(urllib.request.urlopen(f"http://127.0.0.1:{httpd.server_address[1]}/api/faults/reference"))
        assert r["slabs"]
        font = urllib.request.urlopen(f"http://127.0.0.1:{httpd.server_address[1]}/static/fonts/inter-display-700.woff")
        assert font.headers["Content-Type"] == "font/woff"
    finally:
        httpd.shutdown()


def test_static_route_cannot_escape(engine):
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(engine))
    httpd.daemon_threads = True
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"
    try:
        for bad in ("/static//etc/passwd", "/static/../engine.py", "/static/fonts/../../engine.py",
                    "/static/%2e%2e/engine.py"):
            with pytest.raises(urllib.error.HTTPError) as ei:
                urllib.request.urlopen(base + bad)
            assert ei.value.code == 404, bad
        assert urllib.request.urlopen(base + "/static/fonts/inter-text-500.woff").status == 200
    finally:
        httpd.shutdown()


def test_unplugged_sensor_board_hides_its_values():
    from d2dash.sensors import SerialSensors, STALE_AFTER
    s = SerialSensors(port="none")
    s._ingest({"egt": 500})
    assert s.latest()["signals"]
    s._updated -= STALE_AFTER + 1          # no line for a while
    out = s.latest()
    assert out["status"] == "stale" and out["signals"] == {}
    s._ingest({"egt": 501})
    with s._lock:
        s._status, s._error = "error", "unplugged"
    out = s.latest()
    assert out["status"] == "error" and out["signals"] == {}


def test_command_pinned_to_module(engine):
    wait_connected(engine, "td5")
    engine.request_module("slabs")
    r = engine.command("clear_faults", confirm=True)
    assert r["ok"] is False and "switch" in r["error"]


def test_trips_and_fingerprint(tmp_path):
    """Synthetic drives: three healthy, one with a boost leak and a drifting injector."""
    import csv, math
    from datetime import datetime, timedelta
    from d2dash import trips as T
    cols = ["accel_pedal_pct", "balance_1", "balance_5", "battery", "coolant_temp", "injection_qty",
            "maf_sensor", "manifold_press", "rpm", "speed"]
    for day, boost, inj5 in ((1, 1.0, 0.1), (2, 1.0, 0.1), (3, 1.0, 0.1), (5, 0.85, 0.9)):
        t = datetime(2026, 11, day, 9, 0)
        rows = []
        for i in range(1200):
            s = i / 2
            ped = 95 if (s % 60) < 15 else 0
            rpm = 780 + ped * 32 + (s % 15) * 40 * (ped > 0)
            coolant = min(90, 20 + s * 0.12)
            rows.append({"time": t.isoformat(timespec="milliseconds"), "accel_pedal_pct": ped, "balance_1": 0.1,
                         "balance_5": inj5, "battery": 14.1, "coolant_temp": coolant,
                         "injection_qty": 4 + 45 * ped / 100, "maf_sensor": 60 + 400 * ped / 100,
                         "manifold_press": (1.0 + 1.1 * ped / 100) * boost, "rpm": rpm,
                         "speed": 40 if ped else 0, "faults": ""})
            t += timedelta(milliseconds=500)
        with open(tmp_path / (t.strftime("%Y%m%d-%H%M%S") + "-td5.csv"), "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["time", *cols, "faults"]); w.writeheader(); w.writerows(rows)
    trips = T.group_trips(T.list_sessions(str(tmp_path)))
    assert len(trips) == 4
    s = T.summarize(T.load_trip(str(tmp_path), trips[-1]))
    assert s["duration_s"] in (599, 600) and s["distance_km"] > 1
    h = T.health(str(tmp_path))
    assert h["status"] == "ok" and h["baseline"]["n"] == 3
    warn = {f["what"] for f in h["findings"] if f["level"] == "warn"}
    assert "boost" in warn and "balance" in warn
    assert "injection" not in warn and "charging_v" not in warn
    r = T.replay(T.load_trip(str(tmp_path), trips[-1]))
    assert len(r["t"]) <= 601 and "manifold_press" in r["cols"]


def test_thresholds_roundtrip(engine, cfg):
    from d2dash.server import validate_thresholds
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(engine))
    httpd.daemon_threads = True
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"
    try:
        body = json.dumps({"overrides": {"coolant_temp": {"warn": [None, 98], "alarm": [None, 104]}}}).encode()
        req = urllib.request.Request(base + "/api/thresholds", data=body, headers={"Content-Type": "application/json"}, method="POST")
        r = json.load(urllib.request.urlopen(req))
        assert r["ok"] and r["overrides"]["coolant_temp"]["alarm"] == [None, 104.0]
        assert json.load(urllib.request.urlopen(base + "/api/thresholds"))["overrides"]["coolant_temp"]["warn"] == [None, 98.0]
        bad = json.dumps({"overrides": {"coolant_temp": {"warn": [None, 110], "alarm": [None, 104]}}}).encode()
        req = urllib.request.Request(base + "/api/thresholds", data=bad, headers={"Content-Type": "application/json"}, method="POST")
        with pytest.raises(urllib.error.HTTPError) as ei:
            urllib.request.urlopen(req)
        assert ei.value.code == 400
        urllib.request.urlopen(urllib.request.Request(base + "/api/thresholds", method="DELETE"))
        assert json.load(urllib.request.urlopen(base + "/api/thresholds"))["overrides"] == {}
    finally:
        httpd.shutdown()
    with pytest.raises(ValueError):
        validate_thresholds({"../x": {"warn": [1, 2]}})
    with pytest.raises(ValueError):
        validate_thresholds({"rpm": {"warn": [5000, 4000]}})


def test_fault_library_covers_every_fault(engine):
    from d2dash.server import fault_library, fault_reference
    lib, ref = fault_library(), fault_reference()
    for mod in ("td5", "slabs"):
        assert set(lib[mod]) == set(ref[mod])
        missing = [n for n, v in lib[mod].items() if not v.get("what")]
        assert not missing, missing[:5]
    e = lib["slabs"]["Front Right Sensor — Output Low"]
    assert e["title"].startswith("Front right") and e["severity"] in ("drive", "soon", "now") and e["check"]
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(engine))
    httpd.daemon_threads = True
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        r = json.load(urllib.request.urlopen(f"http://127.0.0.1:{httpd.server_address[1]}/api/faults/library"))
        assert r["td5"]["road speed missing (Logged)"]["state_note"].startswith("Seen on an earlier run")
    finally:
        httpd.shutdown()


def test_tyre_correction(engine, cfg):
    from d2dash import tyres
    assert round(tyres.diameter_mm("235/70R16")) == 735 and round(tyres.diameter_mm("265/70R16")) == 777
    assert abs(tyres.factor("235/70R16", "265/70R16") - 1.0571) < 1e-3
    with pytest.raises(ValueError):
        tyres.parse("265/70/16")
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(engine))
    httpd.daemon_threads = True
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"
    try:
        v = json.load(urllib.request.urlopen(base + "/api/vehicle"))
        assert v["factor"] == 1.0 and "265/70R16" in v["sizes"]["16"]
        req = urllib.request.Request(base + "/api/vehicle", data=json.dumps({"factory": "235/70R16", "fitted": "265/70R16"}).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
        r = json.load(urllib.request.urlopen(req))
        assert r["ok"] and abs(r["factor"] - 1.0571) < 1e-3
        bad = urllib.request.Request(base + "/api/vehicle", data=b'{"fitted":"999/99R99"}', headers={"Content-Type": "application/json"}, method="POST")
        with pytest.raises(urllib.error.HTTPError):
            urllib.request.urlopen(bad)
    finally:
        httpd.shutdown()
    from d2dash import trips as T
    rows = [{"time": i, "speed": 100.0, "faults": ""} for i in range(3601)]
    assert abs(T.summarize(rows)["distance_km"] - 100) < 0.2
    assert abs(T.summarize(rows, 1.0571)["distance_km"] - 105.7) < 0.2


def test_slabs_refused_while_moving(engine):
    wait_connected(engine, "td5")
    engine._sim_moving_ok = False          # behave like the car, not the simulator
    with engine._lock:
        engine._snap.signals = {"speed": {"v": 40.0, "u": "km/h"}}
    r = engine.request_module("slabs")
    assert r["ok"] is False and "Stop the car" in r["error"]
    with engine._lock:
        engine._snap.signals = {"speed": {"v": 0.0, "u": "km/h"}}
    assert engine.request_module("slabs")["ok"]


def test_slabs_quiet_period(cfg):
    import dataclasses
    from d2dash.engine import SLABS_QUIET_S
    e = Engine(dataclasses.replace(cfg, simulate=False), make_sim_sources())
    assert e._slabs_quiet_left() == 0.0                    # never spoken to: try straight away
    e._slabs_last_talk = time.monotonic() - 10
    assert SLABS_QUIET_S - 11 < e._slabs_quiet_left() <= SLABS_QUIET_S - 10
