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
