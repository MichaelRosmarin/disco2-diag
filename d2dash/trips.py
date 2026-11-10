"""Trips and the engine fingerprint, computed from the session CSVs.

A *session* is one CSV (one ECU connection). A *trip* groups consecutive Td5 sessions that
are less than TRIP_GAP apart, because a dropped connection mid-drive makes a new file.

The fingerprint is a set of curves and numbers that should stay the same drive after drive
on a healthy engine. Each trip gets its own; the baseline is the median over earlier trips.
A new trip is compared bin by bin and anything outside tolerance is reported in words.
"""
from __future__ import annotations

import csv
import math
import os
import re
import statistics
from datetime import datetime

TRIP_GAP_S = 10 * 60
_NAME = re.compile(r"^(\d{8}-\d{6})-(td5|slabs)\.csv$")

# full-load curves: rpm bins, only samples with the pedal well down
RPM_BINS = list(range(1500, 4001, 250))      # bin start values; bin = [start, start+250)
FULL_LOAD_PEDAL = 80.0
MIN_BIN_SAMPLES = 4

# what counts as "warm idle"
IDLE = dict(rpm_lo=650, rpm_hi=900, pedal_max=3.0, speed_max=2.0, coolant_min=75.0)

# curve name -> (signal, unit, tolerance, direction that is bad)
CURVES = {
    "boost":     ("manifold_press", "bar", 0.15, "low"),
    "injection": ("injection_qty",  "mg",  4.0,  "any"),
    "airflow":   ("maf_sensor",     "kg/h", 12.0, "low"),
}
# scalar name -> (label, unit, tolerance, bad direction)
SCALARS = {
    "idle_rpm":        ("Warm idle speed",        "rpm", 40,   "any"),
    "idle_injection":  ("Warm idle fuelling",     "mg",  1.5,  "high"),
    "charging_v":      ("Charging voltage",       "V",   0.4,  "low"),
    "warmup_s":        ("Time to warm (50→80 °C)", "s",  120,  "high"),
    "coolant_max":     ("Coolant peak",           "°C",  6,    "high"),
    "egt_max":         ("EGT peak",               "°C",  60,   "high"),
    "oil_press_hot":   ("Hot oil pressure, 2000 rpm", "bar", 0.4, "low"),
}


def _f(v) -> float | None:
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def _parse_time(s: str) -> float | None:
    try:
        return datetime.fromisoformat(s).timestamp()
    except ValueError:
        return None


def list_sessions(log_dir: str) -> list[dict]:
    out = []
    try:
        names = os.listdir(log_dir)
    except OSError:
        return out
    for n in sorted(names):
        m = _NAME.match(n)
        if not m:
            continue
        p = os.path.join(log_dir, n)
        try:
            st = os.stat(p)
        except OSError:
            continue
        out.append({"name": n, "module": m.group(2), "stamp": m.group(1), "size": st.st_size,
                    "mtime": _last_time(p) or st.st_mtime, "path": p})
    return out


def _last_time(path: str) -> float | None:
    """Timestamp of the last row, read from the tail of the file (files may be copied, so
    mtime is not trustworthy)."""
    try:
        with open(path, "rb") as fh:
            fh.seek(0, os.SEEK_END)
            size = fh.tell()
            fh.seek(max(0, size - 4096))
            tail = fh.read().decode("utf-8", "replace").strip().splitlines()
        for line in reversed(tail):
            t = _parse_time(line.split(",", 1)[0])
            if t is not None:
                return t
    except OSError:
        pass
    return None


def read_rows(path: str) -> list[dict]:
    """Rows as {col: float|None, 'time': epoch, 'faults': str}."""
    rows = []
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            t = _parse_time(r.get("time", ""))
            if t is None:
                continue
            row = {k: _f(v) for k, v in r.items() if k not in ("time", "faults")}
            row["time"] = t
            row["faults"] = r.get("faults", "") or ""
            rows.append(row)
    return rows


def group_trips(sessions: list[dict]) -> list[dict]:
    """Consecutive td5 sessions closer than TRIP_GAP become one trip. SLABS sessions attach
    to the trip they fall inside."""
    trips: list[dict] = []
    for s in sessions:
        start = datetime.strptime(s["stamp"], "%Y%m%d-%H%M%S").timestamp()
        s["start"] = start
        if s["module"] != "td5":
            continue
        if trips and start - trips[-1]["end"] < TRIP_GAP_S:
            trips[-1]["sessions"].append(s["name"])
            trips[-1]["end"] = max(trips[-1]["end"], s["mtime"])
        else:
            trips.append({"id": s["stamp"], "start": start, "end": s["mtime"], "sessions": [s["name"]], "slabs": []})
    for s in sessions:
        if s["module"] == "slabs":
            for t in trips:
                if t["start"] - 60 <= s["start"] <= t["end"] + TRIP_GAP_S:
                    t["slabs"].append(s["name"])
                    break
    return trips


def load_trip(log_dir: str, trip: dict) -> list[dict]:
    rows: list[dict] = []
    for n in trip["sessions"]:
        rows.extend(read_rows(os.path.join(log_dir, n)))
    rows.sort(key=lambda r: r["time"])
    return rows


# ---------------------------------------------------------------- summary + replay

def _col(rows, k):
    return [r[k] for r in rows if r.get(k) is not None]


def summarize(rows: list[dict], speed_factor: float = 1.0) -> dict:
    """speed_factor corrects the ECU's road speed for non-factory tyres (see tyres.py)."""
    if not rows:
        return {}
    t0, t1 = rows[0]["time"], rows[-1]["time"]
    dist = 0.0
    for a, b in zip(rows, rows[1:]):
        v = a.get("speed")
        if v is not None:
            dist += v * speed_factor / 3600.0 * max(0.0, min(5.0, b["time"] - a["time"]))
    fuel = 0.0
    for a, b in zip(rows, rows[1:]):
        v = a.get("fuel_rate")
        if v is not None:
            fuel += v / 3600.0 * max(0.0, min(5.0, b["time"] - a["time"]))
    faults: list[str] = []
    for r in rows:
        for f in r["faults"].split("; "):
            if f and f not in faults:
                faults.append(f)
    mx = lambda k: (max(_col(rows, k)) if _col(rows, k) else None)  # noqa: E731
    return {
        "start": t0, "end": t1, "duration_s": round(t1 - t0), "rows": len(rows),
        "distance_km": round(dist, 1), "fuel_l": round(fuel, 2),
        "l_per_100km": round(fuel / dist * 100, 1) if dist > 1 else None,
        "coolant_max": mx("coolant_temp"), "egt_max": mx("sensor_egt"),
        "boost_max": mx("manifold_press"), "rpm_max": mx("rpm"),
        "speed_max": round(mx("speed") * speed_factor) if mx("speed") is not None else None,
        "faults": faults,
    }


REPLAY_COLS = ["coolant_temp", "manifold_press", "rpm", "speed", "injection_qty", "battery",
               "air_temp", "sensor_egt", "sensor_oil_press", "sensor_oil_temp", "sensor_gearbox_temp"]


def replay(rows: list[dict], max_points: int = 600, speed_factor: float = 1.0) -> dict:
    """Downsampled series for the chart: {t:[...], cols:{name:[...]}} with t in seconds from start."""
    if not rows:
        return {"t": [], "cols": {}}
    step = max(1, len(rows) // max_points)
    t0 = rows[0]["time"]
    picked = rows[::step]
    cols = {}
    for k in REPLAY_COLS:
        f = speed_factor if k == "speed" else 1.0
        vals = [None if r.get(k) is None else r.get(k) * f for r in picked]
        if any(v is not None for v in vals):
            cols[k] = [None if v is None else round(v, 2) for v in vals]
    return {"t": [round(r["time"] - t0) for r in picked], "cols": cols,
            "faults": [(round(r["time"] - t0), r["faults"]) for r in picked if r["faults"]][:50]}


# ---------------------------------------------------------------- fingerprint

def fingerprint(rows: list[dict]) -> dict:
    """Curves at full load and warm-idle/charging scalars for one trip."""
    curves: dict[str, dict] = {name: {} for name in CURVES}
    for name, (sig, _u, _tol, _d) in CURVES.items():
        bins: dict[int, list[float]] = {b: [] for b in RPM_BINS}
        for r in rows:
            rpm, ped, v = r.get("rpm"), r.get("accel_pedal_pct"), r.get(sig)
            if rpm is None or ped is None or v is None or ped < FULL_LOAD_PEDAL:
                continue
            b = int(rpm // 250 * 250)
            if b in bins:
                bins[b].append(v)
        curves[name] = {str(b): round(statistics.median(v), 3) for b, v in bins.items() if len(v) >= MIN_BIN_SAMPLES}

    idle = [r for r in rows if r.get("rpm") is not None and IDLE["rpm_lo"] <= r["rpm"] <= IDLE["rpm_hi"]
            and (r.get("accel_pedal_pct") or 0) <= IDLE["pedal_max"] and (r.get("speed") or 0) <= IDLE["speed_max"]
            and (r.get("coolant_temp") or 0) >= IDLE["coolant_min"]]
    scalars: dict[str, float | None] = {}
    scalars["idle_rpm"] = round(statistics.median(_col(idle, "rpm")), 0) if len(idle) >= 10 else None
    scalars["idle_injection"] = round(statistics.median(_col(idle, "injection_qty")), 2) if len(_col(idle, "injection_qty")) >= 10 else None
    balance = {}
    for i in range(1, 6):
        c = _col(idle, f"balance_{i}")
        if len(c) >= 10:
            balance[str(i)] = round(statistics.median(c), 2)
    chg = [r["battery"] for r in rows if r.get("battery") is not None and (r.get("rpm") or 0) > 1500]
    scalars["charging_v"] = round(statistics.median(chg), 2) if len(chg) >= 10 else None

    # warm-up: first time coolant crosses 50 then 80
    t50 = t80 = None
    for r in rows:
        c = r.get("coolant_temp")
        if c is None:
            continue
        if t50 is None and c >= 50:
            t50 = r["time"]
        if t50 is not None and t80 is None and c >= 80:
            t80 = r["time"]
            break
    scalars["warmup_s"] = round(t80 - t50) if (t50 is not None and t80 is not None and t80 > t50) else None
    scalars["coolant_max"] = max(_col(rows, "coolant_temp")) if _col(rows, "coolant_temp") else None
    scalars["egt_max"] = max(_col(rows, "sensor_egt")) if _col(rows, "sensor_egt") else None
    hot = [r["sensor_oil_press"] for r in rows if r.get("sensor_oil_press") is not None
           and (r.get("sensor_oil_temp") or 0) >= 80 and r.get("rpm") is not None and 1800 <= r["rpm"] <= 2200]
    scalars["oil_press_hot"] = round(statistics.median(hot), 2) if len(hot) >= 5 else None
    return {"curves": curves, "scalars": scalars, "balance": balance}


def baseline(fps: list[dict]) -> dict:
    """Median of earlier trips' fingerprints, bin by bin. Needs >= 2 trips to mean anything."""
    out = {"curves": {}, "scalars": {}, "balance": {}, "n": len(fps)}
    for name in CURVES:
        acc: dict[str, list[float]] = {}
        for fp in fps:
            for b, v in fp["curves"].get(name, {}).items():
                acc.setdefault(b, []).append(v)
        out["curves"][name] = {b: round(statistics.median(v), 3) for b, v in acc.items() if len(v) >= 2}
    for k in SCALARS:
        vals = [fp["scalars"].get(k) for fp in fps if fp["scalars"].get(k) is not None]
        if len(vals) >= 2:
            out["scalars"][k] = round(statistics.median(vals), 2)
    for i in "12345":
        vals = [fp["balance"].get(i) for fp in fps if fp["balance"].get(i) is not None]
        if len(vals) >= 2:
            out["balance"][i] = round(statistics.median(vals), 2)
    return out


def compare(latest: dict, base: dict) -> list[dict]:
    """Findings in words. level: 'warn' (outside tolerance) or 'ok'."""
    findings = []
    for name, (sig, unit, tol, bad) in CURVES.items():
        lb, bb = latest["curves"].get(name, {}), base["curves"].get(name, {})
        worst = None
        for b in sorted(set(lb) & set(bb), key=int):
            d = lb[b] - bb[b]
            if (bad == "low" and d < -tol) or (bad == "high" and d > tol) or (bad == "any" and abs(d) > tol):
                if worst is None or abs(d) > abs(worst[1]):
                    worst = (b, d)
        if worst:
            b, d = worst
            findings.append({"level": "warn", "what": name, "text":
                f"{name.capitalize()} at {b}–{int(b)+250} rpm is {abs(d):.2f} {unit} {'under' if d < 0 else 'over'} the baseline"})
        elif lb and bb:
            findings.append({"level": "ok", "what": name, "text": f"{name.capitalize()} curve matches the baseline"})
    for k, (label, unit, tol, bad) in SCALARS.items():
        lv, bv = latest["scalars"].get(k), base["scalars"].get(k)
        if lv is None or bv is None:
            continue
        d = lv - bv
        flag = (bad == "low" and d < -tol) or (bad == "high" and d > tol) or (bad == "any" and abs(d) > tol)
        dtxt = f"{abs(d):.0f}" if abs(d) >= 10 else f"{abs(d):.2f}"
        findings.append({"level": "warn" if flag else "ok", "what": k, "text":
            f"{label}: {lv:g} {unit}, {dtxt} {unit} {'more' if d >= 0 else 'less'} than baseline" if flag else f"{label} normal ({lv:g} {unit})"})
    for i in "12345":
        lv, bv = latest["balance"].get(i), base["balance"].get(i)
        if lv is not None and bv is not None and abs(lv - bv) > 0.6:
            findings.append({"level": "warn", "what": "balance", "text":
                f"Injector {i} balance moved {lv - bv:+.2f} from its baseline; watch it over the next drives"})
    findings.sort(key=lambda f: f["level"] != "warn")
    return findings


def health(log_dir: str, max_trips: int = 40) -> dict:
    sessions = list_sessions(log_dir)
    trips = group_trips(sessions)[-max_trips:]
    fps = []
    for t in trips:
        rows = load_trip(log_dir, t)
        if len(rows) < 30:
            continue
        fp = fingerprint(rows)
        fp["id"] = t["id"]
        fps.append(fp)
    if not fps:
        return {"status": "no data", "trips": 0}
    latest = fps[-1]
    earlier = fps[:-1]
    if len(earlier) < 2:
        return {"status": "learning", "trips": len(fps), "latest": latest,
                "note": f"Baseline needs 3 trips with full-throttle pulls; {len(fps)} so far."}
    base = baseline(earlier)
    return {"status": "ok", "trips": len(fps), "latest": latest, "baseline": base,
            "findings": compare(latest, base), "bins": RPM_BINS,
            "curves": {k: {"signal": v[0], "unit": v[1]} for k, v in CURVES.items()}}
