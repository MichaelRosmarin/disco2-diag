# Roadmap and build notes

## Stage 1: Pi talks to the car (current)

1. Bench: `python -m d2dash --simulate`, check the page on a phone.
2. Pi: `deploy/install.sh`, power from the official PSU on the bench, confirm the hotspot.
3. Car, engine off, ignition on: watch `journalctl -u d2dash -f`. Expect "fast init", then
   "connected". If the Td5 never answers, check the cable is FTDI (lsusb shows `0403:6001`),
   the K+DCAN switch is in the K-line position, and the port in `/etc/d2dash/d2dash.env`.
4. Engine running: gauges move. Compare rpm and coolant against the instrument cluster.
5. Tap *Connect SLABS*, wait for it. Heights should sit in the green band on level ground.
6. Wire the UBEC to an ignition-switched fuse tap; mount the Pi.
7. Enable the read-only overlay.

## Stage 2: sensor board

ESP32 DevKit V1 reading an MCP9600 (EGT thermocouple) and an ADS1115 (oil pressure 0.5-4.5 V,
oil temp NTC). Firmware streams JSON lines over USB at 115200. `d2dash` gets a third source,
`sensors`, that is NOT on the K-line and so is always live, regardless of which ECU is active.
Alarms (EGT, oil pressure) fire on the ESP32 itself with a buzzer, so a Pi reboot never
silences them.

## Stage 3: displays

- 7" HDMI touchscreen on a panel-mount socket: `deploy/kiosk.sh` (Chromium, boots to the Drive tab).
- Round ESP32-S3 1.28" gauges: the Pi pushes a compact line (`rpm,coolant,boost,egt,oilp,...`)
  over serial/RS485 at 10 Hz; each gauge draws what it is configured for. The display never
  needs WiFi and comes up in two seconds.

## Known limits of the upstream pack (as of Nov 2026)

- Td5 output tests and injector pulses are decoded from sniffs but never run from this code.
- SLABS wheel-speed scaling is unconfirmed; only two SLABS fault bits are decoded, the rest show as
  `unknown (byte, bit)`.
- The BCU's EKA code is behind an unbroken seed/key; no EKA read, by design.
- SLABS drops the session above roughly 8-20 km/h and locks you out for ~28 s if polled too fast.
