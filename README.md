# disco2-diag

In-car diagnostics for a Land Rover Discovery 2 Td5. A Raspberry Pi behind the dash reads
the Td5 engine ECU and the SLABS (ABS + self-levelling air suspension) ECU over the K-line,
serves a dashboard to a phone or a plug-in touchscreen, and logs every drive to CSV.
A Nanocom replacement for the price of a Pi and a cable.

It is a thin layer (`d2dash`) over two open-source projects that did the hard work:

- [openostler/ostler](https://github.com/openostler/ostler): K-line / KWP2000 stack
- [openostler/ostler-pack-lr-d2](https://github.com/openostler/ostler-pack-lr-d2) (`d2diag`): the
  Discovery 2 vehicle pack, with the Td5 seed/key, signal maps and fault decoding

## Hardware

| Part | Notes |
|---|---|
| Raspberry Pi 3B+ (or 4, Zero 2 W for headless) | sealed passive aluminium case, no fan |
| FTDI FT232RL OBD2 cable (VAG KKL 409.1 or BMW K+DCAN with the switch in K-line position) | CH340 cables do not work |
| Hobbywing 5V 3A UBEC off an ignition-switched fuse tap | rides through cranking sag |
| microSD, endurance or industrial grade | root is mounted read-only in the car |
| Optional: 7" HDMI touchscreen on a panel-mount HDMI + USB socket in the dash cubby | |
| Later: ESP32 sensor board (EGT, oil pressure/temp) and ESP32 round gauges | see `docs/roadmap.md` |

## Install on the Pi

Flash Raspberry Pi OS Lite (64-bit), enable SSH, boot, then:

```bash
git clone https://github.com/MichaelRosmarin/disco2-diag.git
cd disco2-diag
sudo HOTSPOT_PSK='choose-a-password' bash deploy/install.sh
```

That installs everything under `/opt/d2dash`, starts the `d2dash` service on port 80, and
brings up a WiFi hotspot called `Disco2`. Join it from a phone and open
`http://10.42.0.1/` (or `http://disco2.local/` if your phone resolves mDNS).

Config lives in `/etc/d2dash/d2dash.env`. Once the install is proven in the car:

```bash
sudo bash deploy/readonly.sh enable && sudo reboot   # power cuts can no longer corrupt the SD
sudo bash deploy/readonly.sh disable && sudo reboot  # before any update
```

## Run on a laptop

```bash
pip install -e .
python -m d2dash --simulate --http-port 8080        # no car needed: simulated Td5 + SLABS
python -m d2dash --port /dev/ttyUSB0 --http-port 8080   # needs openostler + d2diag installed
```

Then open http://localhost:8080/.

## The dashboard

- **Drive**: dials for coolant, boost, EGT and oil pressure with amber/red zones on the face,
  bars for revs, oil and gearbox temperature, a strip of secondaries. An alarm band under the
  tabs goes amber (watch) or red (out of range), beeps on the phone until snoozed, and the
  thresholds are listed under More.
- **Engine** and **SLABS** follow the Nanocom's layout: Faults (with the likely cause under each),
  Inputs (every decoded value, in the Nanocom's order), Settings, Outputs, Utilities. Items the
  library has not decoded yet are listed as pending, so the menu is the full Nanocom menu.
  See `docs/nanocom-parity.md` for the item-by-item status.
- **More**: alarm sound, sensor-board status, session logs, system info.

## How it works

K-line is one shared bus, so only one ECU is active at a time. The poller thread streams the
Td5 at 2 Hz by default (the Drive tab). Tapping *Connect SLABS* releases the engine session and
establishes SLABS, which needs up to about 30 s of bus silence first; SLABS is then polled at
1 Hz, the most it tolerates. *Connect engine* switches back. The ESP32 sensor board is a second
serial device on its own thread, so EGT and oil pressure stay live whichever ECU holds the bus.

Reads happen automatically. Anything that writes to an ECU or moves hardware (clear faults,
output tests, suspension raise/lower, ABS bleed) is refused by the server unless the request
carries `confirm: true`, which the page only sends after an on-screen prompt.

```
Td5 ECU ─┐                                       ┌─ phone / tablet (Safari, Chrome)
         ├─ K-line ─ FTDI (/dev/kline) ─┐        │
SLABS ───┘                              ├─ Pi ─ HTTP + SSE ─┤
ESP32 sensor board ─ USB (/dev/sensors) ┘  (d2diag + d2dash) └─ 7" touchscreen (deploy/kiosk.sh)
```

### API

| Route | |
|---|---|
| `GET /api/snapshot` | latest poll of the active module |
| `GET /api/events` | Server-Sent Events stream, one event per poll |
| `POST /api/module` | `{"module":"td5"\|"slabs"}` |
| `POST /api/command` | `{"action":"clear_faults","confirm":true}` and the other actions in `d2dash/engine.py` |
| `GET /api/faults/reference` | `{module: {fault name: likely cause}}` |
| `GET /api/logs`, `GET /api/logs/<file>` | session CSVs (ECU columns plus `sensor_*`) |

The same feed is what ESP32 gauges will read later (over serial from the Pi, not WiFi).

## Repository layout

```
d2dash/            the service: engine.py (poller), server.py (HTTP/SSE), sensors.py (ESP32 board),
                   sim.py, static/index.html, data/ (fault dictionaries, CC BY-SA)
deploy/            install.sh, systemd unit, udev rules, hotspot.sh, readonly.sh, kiosk.sh
esp32/sensor-board Arduino sketch + wiring notes for the EGT / oil / gearbox / fuel board
tests/             pytest, runs against the simulator
docs/              roadmap and the Nanocom parity map
```

## Status

- [x] Service, dashboard, simulator, Pi install scripts
- [x] Pi flashed, on the network, service running (5 Nov 2026)
- [x] Nanocom-style Engine / SLABS pages with fault causes
- [x] Sensor-board source, firmware and kiosk script written (untested on hardware)
- [ ] First run against the car (Td5 live data, fault read)
- [ ] SLABS in the car
- [ ] Sensor board built and calibrated
- [ ] Touchscreen in the dash
- [ ] ESP32 round gauges over serial/RS485
- [ ] Other ECUs (BCU, auto box, airbag, ACE) as the library decodes them

## Licence

AGPL-3.0-or-later, the same as the Ostler platform it builds on. Hobby project, reverse-engineered
protocols, no warranty: writes to the SLABS and Td5 are experimental. Keep the Nanocom-capable
specialist's number for anything you can't afford to get wrong.
