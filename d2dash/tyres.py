"""Tyre sizes and the road-speed correction they need.

The SLABS ECU works out road speed (and each wheel speed) from wheel-sensor pulses and a fixed rolling
circumference for the size the car left the factory on. Fit a taller tyre and every wheel turn covers more
road, so the ECU's speed, the speedometer and anything derived from them read low by the ratio of the
diameters. The dashboard multiplies speeds by that ratio for display and for trip distances; the raw ECU
values in the logs are left untouched.

Factory sizes are from the Discovery II workshop manual (RAVE, General data — Wheels and tyres):
7J x 16 → 235/70 R16, 8J x 16 → 255/65 R16, 8J x 18 → 255/55 R18. The other sizes are common aftermarket
sizes listed for convenience; their diameters are calculated, not a statement that they fit.
"""
from __future__ import annotations

import re

FACTORY = ["235/70R16", "255/65R16", "255/55R18"]
SIZES = {
    16: ["235/70R16", "255/65R16", "235/85R16", "245/70R16", "245/75R16", "255/70R16", "265/70R16",
         "265/75R16", "285/75R16"],
    17: ["235/65R17", "245/70R17", "255/65R17", "265/65R17", "265/70R17", "285/70R17"],
    18: ["255/55R18", "255/60R18", "265/60R18"],
}
DEFAULT = {"factory": "235/70R16", "fitted": "235/70R16"}

_SIZE = re.compile(r"^(\d{3})/(\d{2})R(\d{2})$")


def parse(size: str) -> tuple[int, int, int]:
    m = _SIZE.match(str(size).strip().upper().replace(" ", ""))
    if not m:
        raise ValueError(f"tyre size {size!r} is not in the form 265/70R16")
    w, a, r = (int(x) for x in m.groups())
    if not (175 <= w <= 335 and 40 <= a <= 90 and 14 <= r <= 22):
        raise ValueError(f"tyre size {size!r} is outside the sizes this car could run")
    return w, a, r


def diameter_mm(size: str) -> float:
    """Unloaded geometric diameter: rim plus two sidewalls."""
    w, a, r = parse(size)
    return r * 25.4 + 2 * w * a / 100


def factor(factory: str, fitted: str) -> float:
    """Multiply the ECU's speed by this to get true speed. The rolling radius of a loaded tyre is smaller
    than its geometric radius by a similar proportion for similar tyres, so the ratio of geometric
    diameters is the right correction to about 1 %."""
    return diameter_mm(fitted) / diameter_mm(factory)


def validate(v: dict) -> dict:
    if not isinstance(v, dict):
        raise ValueError("settings must be an object")
    out = dict(DEFAULT)
    for k in ("factory", "fitted"):
        if k in v and v[k]:
            w, a, r = parse(v[k])
            out[k] = f"{w}/{a}R{r}"
    return out


def describe(v: dict) -> dict:
    v = validate(v)
    f = factor(v["factory"], v["fitted"])
    return {**v, "factor": round(f, 4), "factory_mm": round(diameter_mm(v["factory"])),
            "fitted_mm": round(diameter_mm(v["fitted"])), "sizes": SIZES, "factory_sizes": FACTORY}
