# Sensor board (stage 2)

An ESP32 DevKit V1 that reads what the Td5 ECU cannot tell you and streams it to the Pi over
its USB cable as JSON lines. The Pi's `d2dash` picks the port up automatically (any CP210x /
CH340 / native-USB ESP32; the FTDI K-line cable is never mistaken for it) and the values appear
on the Drive tab and in the session CSVs.

## Wiring

| Sensor | Part | Board connection |
|---|---|---|
| EGT, pre-turbo | MCP9600 breakout (Adafruit 4101) + K-type probe in the manifold | I2C: SDA 21, SCL 22, 3V3, GND. Address 0x67 |
| Oil pressure | 0.5-4.5 V transducer (0-150 psi), tee'd off the oil pressure switch port | 5 V + GND from the UBEC; signal through a 10k/10k divider into ADS1115 A0 |
| Oil temperature | 10k NTC in the sump plug or a sandwich plate | 10k pull-up to 3V3, NTC to GND, junction to ADS1115 A1 |
| Gearbox oil temperature | 10k NTC on the cooler line (hose clamp + thermal paste, or an inline fitting) | same divider, ADS1115 A2 |
| Fuel level | tap off the sender wire at the instrument pack | 100 Ω pull-up to 3V3, sender to GND, junction to ADS1115 A3 |
| Supply voltage | ignition-switched 12 V | 47k/10k divider into GPIO 34 (optional) |
| Buzzer | 5 V active buzzer | GPIO 25 → 1k → NPN base, buzzer between 5 V and collector |

ADS1115 sits on the same I2C bus at 0x48. Keep the thermocouple leads away from the injector
harness and twist the NTC pairs; the alternator makes this a noisy car.

## Calibration

Everything to tune is at the top of `sensor-board.ino`:

- `OILP_BAR_MAX`: 10.3 for a 150 psi transducer, 6.9 for a 100 psi one.
- `NTC_R25` / `NTC_BETA`: from the thermistor's datasheet. Check against a kettle: the NTC in
  boiling water should read 98-100 °C at Franschhoek altitude.
- `FUEL_R_FULL` / `FUEL_R_EMPTY`: measure the sender with the tank full and when the gauge
  shows reserve; the Discovery 2 sender is roughly 10 Ω full, 180 Ω empty.
- Alarm thresholds: the board beeps on its own above `EGT_ALARM_C`, `OILT_ALARM_C`,
  `GBT_ALARM_C`, and below `OILP_ALARM_BAR` once the oil is warm. The dashboard's amber/red
  bands are separate (`G` in `d2dash/static/index.html`); keep the board's a little above the
  dashboard's red so the phone speaks first.

## Flashing

Arduino IDE 2.x: install the ESP32 board package (Espressif), then libraries
*Adafruit MCP9600*, *Adafruit ADS1X15*, *Adafruit BusIO*. Board "DOIT ESP32 DEVKIT V1",
upload at 115200. Serial Monitor shows the JSON lines; `{}` means no sensor answered on I2C.

## Testing without the car

`python -m d2dash --simulate` includes a simulated board. With a real board on the bench, run
`python -m d2dash --simulate --sensors-port /dev/ttyUSB0` (simulated ECUs, real board) and warm
the EGT probe with a lighter: the EGT dial should move within a second. On the Pi the board is
found automatically; `D2DASH_SENSORS_PORT=none` in `/etc/d2dash/d2dash.env` switches it off.
