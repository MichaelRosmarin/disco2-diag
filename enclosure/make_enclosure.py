#!/usr/bin/env python3
"""Printable enclosure for the Pi 3B+ in the Discovery 2 (no CAD program needed).

    python3 enclosure/make_enclosure.py            # writes enclosure/stl/*.stl and preview images

Design: every plug lives INSIDE the box. The Pi sits at one end; the other end is a cable bay
where the USB and power plugs sit. The cables leave through clamshell glands on the parting line:
the base carries the lower half of each round exit, the lid the upper half, and the bore is a
fraction under the cable diameter, so screwing the lid down is what clamps the cables. Nothing
outside can be knocked or walk out on corrugations. A cable channel along the power edge brings
the micro-USB lead round to the same end.

Parts (both printed flat, no supports):
  base.stl   Pi standoffs, cable bay, lower gland halves, intake vents, mounting ears, lid posts
  lid.stl    alignment lip, upper gland halves, exhaust vents over the processor, screw holes

Coordinates: x along the Pi's 85 mm length (SD end at x=0, USB end at x=85), y across the 56 mm
width (power/HDMI edge at y=0, GPIO edge at y=56), z up with the board's underside at z=0.
Geometry is axis-aligned prisms plus cylinders; round holes are made by passing a hollow
cylinder through a square cut-out no bigger than its bore, so the slicer's union leaves a true
round hole. Material: ASA first choice, PETG second. Not PLA (a footwell reaches 60 °C).
"""
from __future__ import annotations

import math
import os
import struct

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stl")

# ---------------- parameters (mm) ----------------
BOARD_L, BOARD_W, BOARD_T = 85.0, 56.0, 1.4
HOLES = [(3.5, 3.5), (61.5, 3.5), (3.5, 52.5), (61.5, 52.5)]
CLEARANCE = 1.5
WALL = 2.4
FLOOR = 2.4
LID_T = 2.4
STANDOFF_H = 6.0
ABOVE_BOARD = 18.0          # board top to lid underside (USB stacks are 15.6)
BAY_L = 50.0                # cable bay beyond the USB end: plug + boot (~36) + room for the cable to rise to the lid line
CHANNEL_W = 20.0            # channel along the power edge for the micro-USB plug (~17 incl. boot) and its lead
INSERT = True
HOLE_STANDOFF = 3.4 if INSERT else 2.2
HOLE_LID_POST = 2.9
LID_POST_OD = 5.6
STANDOFF_OD = 6.0
M3_POCKET = 4.0             # square pocket for an M3 heat-set insert
M3_CLEAR = 3.4
VENT_W = 2.0

# cable exits on the parting line of the bay end wall: (y centre, cable OD, label).
# The bore is cable OD minus PINCH, so the closed lid compresses the jacket.
EXITS = [(29.0, 5.0, "K-line cable (FTDI lead in USB stack 1)"),   # straight behind the plug
         (47.0, 4.2, "spare: GPS puck or USB stick in USB stack 2"),
         (-10.0, 4.2, "power lead, coming along the channel")]
PINCH = 0.4
GLAND_WALL = 2.6            # radial wall of the gland halves
GLAND_LEN = 6.0             # how far the glands stand proud of the end wall
GLAND_IN = 8.0              # how far the lid's upper half runs inboard of the wall as a tunnel in the lid
RELIEF = 1.5                # the inboard part of that tunnel is this much wider, so the cable can bend down to its plug

# derived
X0, X1 = -CLEARANCE, BOARD_L + BAY_L                       # cavity in x (bay included)
Y0, Y1 = -CHANNEL_W, BOARD_W + CLEARANCE                   # cavity in y (channel included)
OX0, OX1 = X0 - WALL, X1 + WALL
OY0, OY1 = Y0 - WALL, Y1 + WALL
ZF = -STANDOFF_H - FLOOR
ZFT = -STANDOFF_H
ZB = 0.0
ZT = BOARD_T
ZW = ZT + ABOVE_BOARD
LID_POSTS_EXTRA = [(X1 - 4.5, Y0 + 4.5), (X1 - 4.5, Y1 - 4.5), (X0 + 4.5, Y0 + 4.5)]   # bay + channel corners

SD_SLOT = (21.5, 35.5, ZB - 2.0, ZB + 2.5)   # (y0, y1, z0, z1) in the x = 0 wall

# ---------------- mesh primitives ----------------
def box(x0, y0, z0, x1, y1, z1, t):
    if x1 <= x0 or y1 <= y0 or z1 <= z0:
        return
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    for a, b, c in [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5), (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)]:
        t.append((v[a], v[b], v[c]))


def tube_z(cx, cy, z0, z1, r_out, r_in, t, n=48):
    _tube(t, n, r_out, r_in, z0, z1, lambda u, v, w: (cx + u, cy + v, w))


def tube_x(cy, cz, x0, x1, r_out, r_in, t, n=48):
    _tube(t, n, r_out, r_in, x0, x1, lambda u, v, w: (w, cy + u, cz + v))


def half_tube_x(cy, cz, x0, x1, r_out, r_in, upper, t, n=32):
    """Half of a hollow cylinder along x, cut by the horizontal plane z = cz: the upper or lower
    half, with the two flat cut faces closed so the part is a solid."""
    a0 = 0.0 if upper else math.pi
    pts = [(math.cos(a0 + math.pi * i / n), math.sin(a0 + math.pi * i / n)) for i in range(n + 1)]
    P = lambda r, p, x: (x, cy + r * p[0], cz + r * p[1])  # noqa: E731
    for i in range(n):
        a, b = pts[i], pts[i + 1]
        t.append((P(r_out, a, x0), P(r_out, b, x0), P(r_out, b, x1))); t.append((P(r_out, a, x0), P(r_out, b, x1), P(r_out, a, x1)))
        t.append((P(r_in, a, x0), P(r_in, b, x1), P(r_in, b, x0))); t.append((P(r_in, a, x0), P(r_in, a, x1), P(r_in, b, x1)))
        t.append((P(r_out, a, x1), P(r_out, b, x1), P(r_in, b, x1))); t.append((P(r_out, a, x1), P(r_in, b, x1), P(r_in, a, x1)))
        t.append((P(r_out, a, x0), P(r_in, b, x0), P(r_out, b, x0))); t.append((P(r_out, a, x0), P(r_in, a, x0), P(r_in, b, x0)))
    for sgn in (1, -1):   # flat faces on the cut plane, between r_in and r_out
        q = [(x0, cy + sgn * r_in, cz), (x1, cy + sgn * r_in, cz), (x1, cy + sgn * r_out, cz), (x0, cy + sgn * r_out, cz)]
        t.append((q[0], q[1], q[2])); t.append((q[0], q[2], q[3]))
        t.append((q[0], q[2], q[1])); t.append((q[0], q[3], q[2]))


def _tube(t, n, r_out, r_in, w0, w1, m):
    pts = [(math.cos(2 * math.pi * i / n), math.sin(2 * math.pi * i / n)) for i in range(n)]
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        oa0, ob0, oa1, ob1 = m(r_out * a[0], r_out * a[1], w0), m(r_out * b[0], r_out * b[1], w0), m(r_out * a[0], r_out * a[1], w1), m(r_out * b[0], r_out * b[1], w1)
        t.append((oa0, ob0, ob1)); t.append((oa0, ob1, oa1))
        if r_in > 0:
            ia0, ib0, ia1, ib1 = m(r_in * a[0], r_in * a[1], w0), m(r_in * b[0], r_in * b[1], w0), m(r_in * a[0], r_in * a[1], w1), m(r_in * b[0], r_in * b[1], w1)
            t.append((ia0, ib1, ib0)); t.append((ia0, ia1, ib1))
            t.append((oa1, ob1, ib1)); t.append((oa1, ib1, ia1))
            t.append((oa0, ib0, ob0)); t.append((oa0, ia0, ib0))
        else:
            c0, c1 = m(0, 0, w0), m(0, 0, w1)
            t.append((c1, oa1, ob1)); t.append((c0, ob0, oa0))


def plate_with_holes(u0, u1, v0, v1, holes, place, t):
    """Rectangle in (u, v) minus axis-aligned holes, emitted as boxes via place(u0,u1,v0,v1,t)."""
    us = sorted({u0, u1, *[h[0] for h in holes], *[h[1] for h in holes]})
    vs = sorted({v0, v1, *[h[2] for h in holes], *[h[3] for h in holes]})
    us = [u for u in us if u0 <= u <= u1]
    vs = [v for v in vs if v0 <= v <= v1]
    for i in range(len(us) - 1):
        for j in range(len(vs) - 1):
            cu, cv = (us[i] + us[i + 1]) / 2, (vs[j] + vs[j + 1]) / 2
            if any(h[0] <= cu <= h[1] and h[2] <= cv <= h[3] for h in holes):
                continue
            place(us[i], us[i + 1], vs[j], vs[j + 1], t)


def vent_slots(a0, a1, c0, c1, n, w=VENT_W):
    pitch = (a1 - a0) / n
    return [(a0 + pitch * (i + 0.5) - w / 2, a0 + pitch * (i + 0.5) + w / 2, c0, c1) for i in range(n)]


def sq(c, d):
    return (c - d / 2, c + d / 2)


def post_with_pocket(x0, x1, y0, y1, z0, z1, pocket_d, pocket_depth, t):
    """Vertical post with a square insert pocket opening in its top face."""
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    box(x0, y0, z0, x1, y1, z1 - pocket_depth, t)
    s = z1 - pocket_depth
    px0, px1 = sq(cx, pocket_d); py0, py1 = sq(cy, pocket_d)
    box(x0, y0, s, px0, y1, z1, t); box(px1, y0, s, x1, y1, z1, t)
    box(px0, y0, s, px1, py0, z1, t); box(px0, py1, s, px1, y1, z1, t)


def write_stl(path, triangles):
    with open(path, "wb") as fh:
        fh.write(b"disco2-diag enclosure".ljust(80, b"\0"))
        fh.write(struct.pack("<I", len(triangles)))
        for a, b, c in triangles:
            u = (b[0] - a[0], b[1] - a[1], b[2] - a[2]); v = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
            nrm = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
            ln = math.sqrt(sum(k * k for k in nrm)) or 1.0
            fh.write(struct.pack("<3f", *(k / ln for k in nrm)))
            for p in (a, b, c):
                fh.write(struct.pack("<3f", *p))
            fh.write(b"\0\0")


# ---------------- parts ----------------
def part_base():
    t: list = []
    box(OX0, OY0, ZF, OX1, OY1, ZFT, t)                                   # floor
    for hx, hy in HOLES:                                                   # Pi standoffs
        tube_z(hx, hy, ZFT, ZB, STANDOFF_OD / 2, HOLE_STANDOFF / 2, t)
    for px, py in LID_POSTS_EXTRA:                                         # lid posts in bay/channel corners
        post_with_pocket(px - 3.5, px + 3.5, py - 3.5, py + 3.5, ZFT, ZW, HOLE_STANDOFF, 7.0, t)

    # long wall y = Y0 (power side): low intake vents along the Pi, solid along the bay
    vents_b = vent_slots(4.0, 80.0, ZFT + 1.5, ZFT + 5.5, 14)
    plate_with_holes(OX0, OX1, ZFT, ZW, vents_b, lambda a0, a1, c0, c1, tt: box(a0, OY0, c0, a1, Y0, c1, tt), t)
    # long wall y = Y1 (GPIO side): low intake vents
    vents_g = vent_slots(4.0, 80.0, ZFT + 1.5, ZFT + 5.5, 14)
    plate_with_holes(OX0, OX1, ZFT, ZW, vents_g, lambda a0, a1, c0, c1, tt: box(a0, Y1, c0, a1, OY1, c1, tt), t)
    # end wall x = 0: SD slot
    plate_with_holes(Y0, Y1, ZFT, ZW, [SD_SLOT], lambda a0, a1, c0, c1, tt: box(OX0, a0, c0, X0, a1, c1, tt), t)
    # bay end wall x = X1: a square notch down from the top edge under each cable, no wider than
    # the bore; the lower half-gland fills the corners and leaves a half-round seat
    notches = [(*sq(y, d - PINCH - 0.3), ZW - (d - PINCH) / 2, ZW + 1.0) for y, d, _ in EXITS]
    plate_with_holes(Y0, Y1, ZFT, ZW, notches, lambda a0, a1, c0, c1, tt: box(X1, a0, c0, OX1, a1, c1, tt), t)
    for y, d, _ in EXITS:
        r = (d - PINCH) / 2
        half_tube_x(y, ZW, X1 - 0.5, OX1 + GLAND_LEN, r + GLAND_WALL, r, False, t)

    # mounting ears on the GPIO-side wall
    for xc in (14.0, OX1 - 16.0):
        plate_with_holes(xc - 7.0, xc + 7.0, OY1, OY1 + 12.0, [(xc - 2.5, xc + 2.5, OY1 + 4.5, OY1 + 9.5)],
                         lambda a0, a1, c0, c1, tt: box(a0, c0, ZF, a1, c1, ZF + 3.0, tt), t)
    return t


def part_lid():
    t: list = []
    vents = vent_slots(18.0, 58.0, 12.0, 44.0, 8)                          # over the SoC
    holes = vents + [(*sq(px, M3_CLEAR), *sq(py, M3_CLEAR)) for px, py in LID_POSTS_EXTRA] \
        + [(*sq(hx, HOLE_LID_POST - 0.2), *sq(hy, HOLE_LID_POST - 0.2)) for hx, hy in HOLES] \
        + [(X1 - 3.0, OX1 + 0.1, *sq(y, d - PINCH - 0.3)) for y, d, _ in EXITS] \
        + [(X1 - GLAND_IN, X1 - 3.0, *sq(y, d - PINCH + 2 * RELIEF - 0.3)) for y, d, _ in EXITS]
    # ^ the upper half-bores run through the plate edge and on inboard as a tunnel in the lid, so the
    #   cable sits on the parting line through the wall and then has room to bend down to its plug
    plate_with_holes(OX0, OX1, OY0, OY1, holes, lambda a0, a1, c0, c1, tt: box(a0, c0, ZW, a1, c1, ZW + LID_T, tt), t)
    for y, d, _ in EXITS:                                                  # upper gland halves, matching the base
        r = (d - PINCH) / 2
        half_tube_x(y, ZW, X1 - 3.5, OX1 + GLAND_LEN, r + GLAND_WALL, r, True, t)             # the seat that clamps
        half_tube_x(y, ZW, X1 - GLAND_IN, X1 - 3.0, r + RELIEF + GLAND_WALL, r + RELIEF, True, t)  # relieved tunnel inboard
    lip, g = 1.6, 0.3                                                     # alignment lip inside the walls
    box(X0 + g, Y0 + g, ZW - lip, X1 - g, Y0 + g + 1.6, ZW, t); box(X0 + g, Y1 - g - 1.6, ZW - lip, X1 - g, Y1 - g, ZW, t)
    box(X0 + g, Y0 + g, ZW - lip, X0 + g + 1.6, Y1 - g, ZW, t)
    # on the bay end the lip is interrupted around each exit so the cable can sit in its seat
    plate_with_holes(Y0 + g, Y1 - g, 0, 1, [(*sq(y, d - PINCH + 2 * GLAND_WALL), 0, 1) for y, d, _ in EXITS],
                     lambda a0, a1, c0, c1, tt: box(X1 - g - 1.6, a0, ZW - lip, X1 - g, a1, ZW, tt), t)
    for hx, hy in HOLES:                                                   # posts down onto the Pi holes
        tube_z(hx, hy, ZT, ZW + LID_T, LID_POST_OD / 2, HOLE_LID_POST / 2, t)
    return t


# ---------------- previews ----------------
def render(parts: dict, path: str):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon
    base = parts["base"]
    fig, axs = plt.subplots(2, 2, figsize=(14, 9), dpi=100)

    def flat(tris, keep, proj, ax, title):
        for tri in tris:
            if all(keep(p) for p in tri):
                ax.add_patch(Polygon([proj(p) for p in tri], closed=True, facecolor="#8fa3b5", edgecolor="#8fa3b5", lw=0.3))
        ax.set_aspect("equal"); ax.autoscale(); ax.set_title(title, fontsize=9); ax.grid(True, lw=.3)

    both = base + parts["lid"]
    flat(both, lambda p: p[0] >= X1 - 0.6, lambda p: (p[1], p[2]), axs[0, 0], "cable end, lid closed: three clamshell glands on the parting line (y across, z up)")
    flat(base, lambda p: p[2] > ZFT + 0.01, lambda p: (p[0], p[1]), axs[0, 1], "base interior from above (floor hidden): Pi standoffs, channel, bay, lid posts")
    flat(base, lambda p: p[1] <= Y0 + 0.01, lambda p: (p[0], p[2]), axs[1, 0], "power-side long wall from outside: intake vents under the board")
    flat(parts["lid"], lambda p: p[2] <= ZW + 0.01, lambda p: (p[0], p[1]), axs[1, 1], "lid from below (plate hidden): lip, Pi posts, gland tunnels with relief (7 screw holes)")
    fig.tight_layout(); fig.savefig(path); plt.close(fig)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    parts = {"base": part_base(), "lid": part_lid()}
    for name, tri in parts.items():
        write_stl(os.path.join(OUT, f"{name}.stl"), tri)
        print(f"{name}.stl  {len(tri)} triangles")
    render(parts, os.path.join(OUT, "views.png"))
    print("outer size: %.1f x %.1f x %.1f mm (plus %.0f mm glands and 12 mm ears)" % (OX1 - OX0, OY1 - OY0, ZW + LID_T - ZF, GLAND_LEN))
    for y, d, label in EXITS:
        print(f"exit at y={y}: cable {d} mm, bore {round(d - PINCH, 2)} mm  {label}")
