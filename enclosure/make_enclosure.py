#!/usr/bin/env python3
"""Printable enclosure for the Pi 3B+ in the Discovery 2 (no CAD program needed).

    python3 enclosure/make_enclosure.py            # writes enclosure/stl/*.stl and preview.png

Four parts, all printed flat, no supports:
  base.stl        Pi on four standoffs, vents low on the long walls, SD slot, two mounting ears
  lid.stl         screws down through the Pi's own holes into the base standoffs; vents over the SoC
  usb_clamp.stl   plate across the USB/Ethernet plugs so they cannot walk out on corrugations
  power_clamp.stl same for the micro-USB power plug

Coordinates: x along the Pi's 85 mm length (SD card end at x=0, USB end at x=85), y across the
56 mm width (power/HDMI edge at y=0, GPIO edge at y=56), z up with the board's underside at z=0.
Everything is axis-aligned prisms plus screw bosses, which is all a Pi case needs; the slicer
unions the overlapping solids. Material: ASA (first choice) or PETG. Not PLA: a footwell in
summer reaches 60 °C and PLA sags.

Fit-check print first: if the board binds, raise CLEARANCE; if the screws strip, use heat-set
inserts (set INSERT=True, hole sizes below).
"""
from __future__ import annotations

import math
import os
import struct

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stl")

# ---------------- parameters (mm) ----------------
BOARD_L, BOARD_W, BOARD_T = 85.0, 56.0, 1.4
HOLES = [(3.5, 3.5), (61.5, 3.5), (3.5, 52.5), (61.5, 52.5)]   # Pi mounting holes
CLEARANCE = 1.5          # board edge to inner wall
WALL = 2.4
FLOOR = 2.4
LID_T = 2.4
STANDOFF_H = 6.0         # floor top to board underside (SD card and solder side clear)
ABOVE_BOARD = 18.0       # board top to lid underside (USB stacks are 15.6 tall)
INSERT = True            # heat-set M2.5 inserts in the base standoffs (else self-tap)
HOLE_STANDOFF = 3.4 if INSERT else 2.2
HOLE_LID_POST = 2.9      # M2.5 clearance through the lid posts
LID_POST_OD = 5.6        # fits the 6 mm keep-out around the Pi holes
STANDOFF_OD = 6.0
CLAMP_INSERT_HOLE = 4.0  # heat-set M3 inserts in the clamp bosses
CLAMP_SCREW_CLEAR = 3.4
VENT_W = 2.0             # slot width (keeps most dust out, lets convection through)

# derived
X0, X1 = -CLEARANCE, BOARD_L + CLEARANCE                 # inner cavity in x
Y0, Y1 = -CLEARANCE, BOARD_W + CLEARANCE
OX0, OX1 = X0 - WALL, X1 + WALL                          # outer footprint
OY0, OY1 = Y0 - WALL, Y1 + WALL
ZF = -STANDOFF_H - FLOOR                                 # floor underside
ZFT = -STANDOFF_H                                        # floor top
ZB = 0.0                                                 # board underside
ZT = BOARD_T                                             # board top
ZW = ZT + ABOVE_BOARD                                    # wall top / lid underside

# connector openings on the walls, as (along, across) rectangles in each wall's own plane
# x = 85 end wall: Ethernet and the two USB stacks (positions from the Pi 3B+ mechanical drawing)
END_OPENINGS = [  # (y0, y1, z0, z1)
    (1.5, 19.0, ZT - 0.5, ZT + 14.0),       # Ethernet
    (22.0, 36.0, ZT - 0.5, ZT + 16.2),      # USB stack 1 (centre y 29)
    (40.0, 54.0, ZT - 0.5, ZT + 16.2),      # USB stack 2 (centre y 47)
]
# y = 0 edge wall: micro-USB power and HDMI (audio jack left blanked)
BOTTOM_OPENINGS = [  # (x0, x1, z0, z1)
    (5.0, 16.2, ZT - 0.5, ZT + 7.5),        # micro-USB (plug overmold needs ~11 x 7)
    (23.5, 40.5, ZT - 0.5, ZT + 7.5),       # HDMI
]
SD_SLOT = (21.5, 35.5, ZB - 2.0, ZB + 2.5)  # x = 0 end wall: (y0, y1, z0, z1)

# ---------------- mesh primitives ----------------
tris: list[tuple] = []


def box(x0, y0, z0, x1, y1, z1, into=None):
    t = tris if into is None else into
    if x1 <= x0 or y1 <= y0 or z1 <= z0:
        return
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    f = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5), (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)]
    for a, b, c in f:
        t.append((v[a], v[b], v[c]))


def tube(cx, cy, z0, z1, r_out, r_in=0.0, n=40, into=None):
    """Hollow (or solid when r_in=0) cylinder."""
    t = tris if into is None else into
    pts = [(math.cos(2 * math.pi * i / n), math.sin(2 * math.pi * i / n)) for i in range(n)]
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        oa, ob = (cx + r_out * a[0], cy + r_out * a[1]), (cx + r_out * b[0], cy + r_out * b[1])
        # outer wall
        t.append(((*oa, z0), (*ob, z0), (*ob, z1))); t.append(((*oa, z0), (*ob, z1), (*oa, z1)))
        if r_in > 0:
            ia, ib = (cx + r_in * a[0], cy + r_in * a[1]), (cx + r_in * b[0], cy + r_in * b[1])
            t.append(((*ia, z0), (*ib, z1), (*ib, z0))); t.append(((*ia, z0), (*ia, z1), (*ib, z1)))
            # rings
            t.append(((*oa, z1), (*ob, z1), (*ib, z1))); t.append(((*oa, z1), (*ib, z1), (*ia, z1)))
            t.append(((*oa, z0), (*ib, z0), (*ob, z0))); t.append(((*oa, z0), (*ia, z0), (*ib, z0)))
        else:
            t.append(((cx, cy, z1), (*oa, z1), (*ob, z1))); t.append(((cx, cy, z0), (*ob, z0), (*oa, z0)))


def plate_with_holes(u0, u1, v0, v1, holes, place, into=None):
    """A rectangle in (u, v) minus axis-aligned rectangular holes, emitted as boxes through
    `place(u0, u1, v0, v1)` which maps a (u, v) cell to a 3-D box. Grid partition on hole edges."""
    us = sorted({u0, u1, *[h[0] for h in holes], *[h[1] for h in holes]})
    vs = sorted({v0, v1, *[h[2] for h in holes], *[h[3] for h in holes]})
    us = [u for u in us if u0 <= u <= u1]
    vs = [v for v in vs if v0 <= v <= v1]
    for i in range(len(us) - 1):
        for j in range(len(vs) - 1):
            cu, cv = (us[i] + us[i + 1]) / 2, (vs[j] + vs[j + 1]) / 2
            if any(h[0] <= cu <= h[1] and h[2] <= cv <= h[3] for h in holes):
                continue
            place(us[i], us[i + 1], vs[j], vs[j + 1], into)


def vent_slots(along0, along1, across0, across1, n, w=VENT_W):
    """n slots of width w spread evenly along [along0, along1], spanning [across0, across1]."""
    pitch = (along1 - along0) / n
    out = []
    for i in range(n):
        c = along0 + pitch * (i + 0.5)
        out.append((c - w / 2, c + w / 2, across0, across1))
    return out


def write_stl(path, triangles):
    with open(path, "wb") as fh:
        fh.write(b"disco2-diag enclosure".ljust(80, b"\0"))
        fh.write(struct.pack("<I", len(triangles)))
        for a, b, c in triangles:
            ux, uy, uz = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
            vx, vy, vz = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
            nx, ny, nz = (uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx)
            ln = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
            fh.write(struct.pack("<3f", nx / ln, ny / ln, nz / ln))
            for p in (a, b, c):
                fh.write(struct.pack("<3f", *p))
            fh.write(b"\0\0")


# ---------------- parts ----------------
def part_base():
    t: list = []
    # floor
    box(OX0, OY0, ZF, OX1, OY1, ZFT, t)
    # standoffs with insert / screw holes
    for hx, hy in HOLES:
        tube(hx, hy, ZFT, ZB, STANDOFF_OD / 2, HOLE_STANDOFF / 2, into=t)
    # long wall y = 0 edge (power/HDMI) with openings and low vents
    vents_b = vent_slots(44.0, 82.0, ZFT + 1.5, ZFT + 6.0, 8)
    plate_with_holes(OX0, OX1, ZFT, ZW, BOTTOM_OPENINGS + vents_b,
                     lambda a0, a1, c0, c1, tt: box(a0, OY0, c0, a1, Y0, c1, tt), t)
    # long wall y = 56 edge (GPIO side): low vents only
    vents_g = vent_slots(8.0, 78.0, ZFT + 1.5, ZFT + 6.0, 12)
    plate_with_holes(OX0, OX1, ZFT, ZW, vents_g,
                     lambda a0, a1, c0, c1, tt: box(a0, Y1, c0, a1, OY1, c1, tt), t)
    # end wall x = 0 (SD card)
    plate_with_holes(Y0, Y1, ZFT, ZW, [SD_SLOT],
                     lambda a0, a1, c0, c1, tt: box(OX0, a0, c0, X0, a1, c1, tt), t)
    # end wall x = 85 (Ethernet + USB)
    plate_with_holes(Y0, Y1, ZFT, ZW, END_OPENINGS,
                     lambda a0, a1, c0, c1, tt: box(X1, a0, c0, OX1, a1, c1, tt), t)
    # USB clamp bosses on the outside of the x = 85 wall, at the two ends of the wall, with a
    # square pocket in the end face for an M3 heat-set insert (a square pocket heat-sets fine)
    for yc in (OY0 + 2.5, OY1 - 2.5):
        boss_x(OX1, OX1 + CLAMP_STANDOFF, yc - 2.5, yc + 2.5, ZFT, ZW, yc, ZT + 8.0, CLAMP_INSERT_HOLE, 8.0, t)
    # power clamp bosses on the outside of the y = 0 wall, either side of the micro-USB opening
    for xc in (1.5, 19.7):
        boss_y(OY0 - POWER_STANDOFF, OY0, xc - 2.5, xc + 2.5, ZFT, ZT + 11.0, xc, ZT + 8.0, CLAMP_INSERT_HOLE, 8.0, t)
    # mounting ears on the GPIO-side wall (cable ties or 4 mm screws)
    for xc in (12.0, 73.0):
        plate_with_holes(xc - 7.0, xc + 7.0, OY1, OY1 + 12.0, [(xc - 2.5, xc + 2.5, OY1 + 4.5, OY1 + 9.5)],
                         lambda a0, a1, c0, c1, tt: box(a0, c0, ZF, a1, c1, ZF + 3.0, tt), t)
    return t


def boss_x(x0, x1, y0, y1, z0, z1, pc_y, pc_z, d, depth, t):
    """Boss along +x from x0 to x1 with a square pocket (side d, depth) opening in the x1 face,
    centred at (pc_y, pc_z). Built as a solid part plus four walls around the pocket."""
    box(x0, y0, z0, x1 - depth, y1, z1, t)
    s = x1 - depth
    box(s, y0, z0, x1, pc_y - d / 2, z1, t)
    box(s, pc_y + d / 2, z0, x1, y1, z1, t)
    box(s, pc_y - d / 2, z0, x1, pc_y + d / 2, pc_z - d / 2, t)
    box(s, pc_y - d / 2, pc_z + d / 2, x1, pc_y + d / 2, z1, t)


def boss_y(y0, y1, x0, x1, z0, z1, pc_x, pc_z, d, depth, t):
    """Boss along -y from y1 (wall) to y0 (free end) with a square pocket opening in the y0 face."""
    box(x0, y0 + depth, z0, x1, y1, z1, t)
    e = y0 + depth
    box(x0, y0, z0, pc_x - d / 2, e, z1, t)
    box(pc_x + d / 2, y0, z0, x1, e, z1, t)
    box(pc_x - d / 2, y0, z0, pc_x + d / 2, e, pc_z - d / 2, t)
    box(pc_x - d / 2, y0, pc_z + d / 2, pc_x + d / 2, e, z1, t)


CLAMP_STANDOFF = 17.0    # boss length: plate sits 17 mm off the wall, behind the plug overmolds
POWER_STANDOFF = 16.0


def part_lid():
    t: list = []
    # plate
    vents = vent_slots(20.0, 56.0, 14.0, 42.0, 7)          # over the SoC / heatsink
    plate_with_holes(OX0, OX1, OY0, OY1, vents,
                     lambda a0, a1, c0, c1, tt: box(a0, c0, ZW, a1, c1, ZW + LID_T, tt), t)
    # alignment lip just inside the walls
    lip = 1.5
    for (a0, b0, a1, b1) in [(X0 + 0.3, Y0 + 0.3, X1 - 0.3, Y0 + 0.3 + 1.6), (X0 + 0.3, Y1 - 0.3 - 1.6, X1 - 0.3, Y1 - 0.3),
                             (X0 + 0.3, Y0 + 0.3, X0 + 0.3 + 1.6, Y1 - 0.3), (X1 - 0.3 - 1.6, Y0 + 0.3, X1 - 0.3, Y1 - 0.3)]:
        box(a0, b0, ZW - lip, a1, b1, ZW, t)
    # posts down onto the board over the mounting holes; the screw runs through to the base standoff
    for hx, hy in HOLES:
        tube(hx, hy, ZT, ZW + LID_T, LID_POST_OD / 2, HOLE_LID_POST / 2, into=t)
    return t


def part_usb_clamp():
    """Plate 3 mm thick standing in the y-z plane, 17 mm off the end wall. Slots open to the top
    let it drop over the three cables; it then bears on the plug overmolds (wider than the slots)."""
    t: list = []
    y0, y1 = OY0, OY1
    z0, z1 = ZT - 1.0, ZT + 17.0
    slots = [(9.0 - 4.5, 9.0 + 4.5, ZT + 4.0, z1 + 1),      # Ethernet cable (centre y 10.25, boot ~8)
             (29.0 - 4.0, 29.0 + 4.0, ZT + 4.0, z1 + 1),    # USB stack 1 cables
             (47.0 - 4.0, 47.0 + 4.0, ZT + 4.0, z1 + 1),    # USB stack 2 cables
             (OY0 + 2.5 - CLAMP_SCREW_CLEAR / 2, OY0 + 2.5 + CLAMP_SCREW_CLEAR / 2, ZT + 8.0 - CLAMP_SCREW_CLEAR / 2, ZT + 8.0 + CLAMP_SCREW_CLEAR / 2),
             (OY1 - 2.5 - CLAMP_SCREW_CLEAR / 2, OY1 - 2.5 + CLAMP_SCREW_CLEAR / 2, ZT + 8.0 - CLAMP_SCREW_CLEAR / 2, ZT + 8.0 + CLAMP_SCREW_CLEAR / 2)]
    plate_with_holes(y0, y1, z0, z1, slots,
                     lambda a0, a1, c0, c1, tt: box(0.0, a0, c0, 3.0, a1, c1, tt), t)
    return t


def part_power_clamp():
    t: list = []
    x0, x1 = -1.0, 22.2
    z0, z1 = ZT - 3.0, ZT + 10.0
    slots = [(10.6 - 3.0, 10.6 + 3.0, ZT + 2.5, z1 + 1),    # micro-USB cable
             (1.5 - CLAMP_SCREW_CLEAR / 2, 1.5 + CLAMP_SCREW_CLEAR / 2, ZT + 8.0 - CLAMP_SCREW_CLEAR / 2, ZT + 8.0 + CLAMP_SCREW_CLEAR / 2),
             (19.7 - CLAMP_SCREW_CLEAR / 2, 19.7 + CLAMP_SCREW_CLEAR / 2, ZT + 8.0 - CLAMP_SCREW_CLEAR / 2, ZT + 8.0 + CLAMP_SCREW_CLEAR / 2)]
    plate_with_holes(x0, x1, z0, z1, slots,
                     lambda a0, a1, c0, c1, tt: box(a0, 0.0, c0, a1, 3.0, c1, tt), t)
    return t


def preview(parts: dict, path: str):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    fig = plt.figure(figsize=(11, 7), dpi=110)
    ax = fig.add_subplot(111, projection="3d")
    colors = {"base": "#8fa3b5", "lid": "#c9d2da", "usb_clamp": "#e8a93a", "power_clamp": "#e8a93a"}
    offsets = {"base": (0, 0, 0), "lid": (0, 0, 30), "usb_clamp": (OX1 + CLAMP_STANDOFF, 0, 0), "power_clamp": (0, OY0 - POWER_STANDOFF, 0)}
    for name, t in parts.items():
        dx, dy, dz = offsets[name]
        polys = [[(a[0] + dx, a[1] + dy, a[2] + dz) for a in tri] for tri in t]
        ax.add_collection3d(Poly3DCollection(polys, facecolor=colors[name], edgecolor="#1b2129", linewidths=0.15, alpha=0.95))
    ax.set_xlim(-30, 120); ax.set_ylim(-30, 90); ax.set_zlim(-15, 60)
    ax.set_box_aspect((150, 120, 75)); ax.view_init(elev=28, azim=-55); ax.set_axis_off()
    ax.set_title("disco2 Pi 3B+ enclosure: base, lid (lifted), USB clamp (right), power clamp (front)", fontsize=10)
    fig.tight_layout(); fig.savefig(path); plt.close(fig)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    parts = {"base": part_base(), "lid": part_lid(), "usb_clamp": part_usb_clamp(), "power_clamp": part_power_clamp()}
    for name, t in parts.items():
        write_stl(os.path.join(OUT, f"{name}.stl"), t)
        print(f"{name}.stl  {len(t)} triangles")
    preview(parts, os.path.join(OUT, "preview.png"))
    print("outer size: %.1f x %.1f x %.1f mm" % (OX1 - OX0, OY1 - OY0, ZW + LID_T - ZF))
