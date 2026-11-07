# Roadmap and build notes

What the Nanocom does and how far each item is: `nanocom-parity.md`.

## Stage 1: Pi talks to the car (current)

1. ~~Bench: `python -m d2dash --simulate`, check the page on a phone.~~
2. ~~Pi: `deploy/install.sh` on the home WiFi, service up.~~
3. Car, engine off, ignition on: `sudo journalctl -u d2dash -f`. Expect "fast init", then
   "connected". If the Td5 never answers: `lsusb` must show `0403:6001` (FTDI), `/dev/kline`
   must exist, the K+DCAN switch must be in the K-line position.
4. Engine running: dials move. Compare revs and coolant against the instrument cluster; note
   the warm idle coolant figure and adjust the amber/red thresholds in `index.html` (`G`).
5. Tap *Connect SLABS*, wait for it. Heights should sit in the green band on level ground.
6. First fault read with real codes: check the cause text makes sense; report undecoded
   `byte.bit` faults upstream.
7. Wire the UBEC to an ignition-switched fuse tap; mount the Pi. Dash panel: HDMI + USB for the
   screen, RJ45 for the laptop (`deploy/remote.sh terminal`).
8. Logs onto a USB stick (`deploy/datapart.sh /dev/sda`), then the read-only overlay
   (`deploy/readonly.sh enable`). Not before: with the overlay on and logs on the root
   filesystem, every drive's CSV is lost at key-off.

## Stage 2: sensor board

Firmware and wiring: `esp32/sensor-board/`. Order of build: EGT first (most value, one
breakout), then oil pressure, then the two NTCs, then fuel. Each appears on Drive as soon as
the board sends it; nothing on the Pi changes. Calibrate the NTCs in a kettle and the oil
transducer against the gauge on a compressor before trusting the red line.

## Stage 3: displays

- 7" HDMI touchscreen on a panel-mount socket: `sudo bash deploy/kiosk.sh`. The Drive layout
  was checked at 1024×600. Untested on the Pi itself: cage + Chromium on Trixie Lite is the
  expected combination; if cage refuses the display, `journalctl -u d2dash-kiosk` says why.
- Round ESP32-S3 1.28" gauges: the Pi pushes a compact line (`rpm,coolant,boost,egt,oilp,...`)
  over serial/RS485 at 10 Hz; each gauge draws what it is configured for. Not started.

## Stage 4: the other ECUs

BCU (EKA, key fobs), auto box, airbag, ACE: the library has partial stacks. Same five-section
page per ECU. Waits on upstream decoding; nothing to build here yet.

## Known limits of the upstream pack (as of Nov 2026)

- Td5 output tests and injector pulses are decoded from sniffs but never run from this code.
- Td5 settings (injector codes, tune IDs, feature flags) are not decoded; the Settings page lists
  them as pending.
- SLABS wheel-speed scaling is unconfirmed; 65 SLABS fault bits are named, the rest show as
  `unknown (byte, bit)`.
- SLABS target-height write and height calibration are not confirmed (buttons disabled).
- The BCU's EKA code is behind an unbroken seed/key; no EKA read, by design.
- SLABS drops the session above roughly 8-20 km/h and locks you out for ~28 s if polled too fast.
