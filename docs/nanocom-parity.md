# Nanocom parity: what the Nanocom Evolution offers on a Discovery 2, and where d2dash stands

Source for the Nanocom side: Blackbox Solutions' own ECU guides (Lucas Td5 guide, WABCO SLABS
guide, Discovery II module list). Source for the "ours" column: `d2diag` menus
(`src/d2diag/td5/menu.py`, `src/d2diag/slabs/menu.py`) and what `d2dash` exposes.

Status key: **built** = in d2dash today · **lib** = decoded and callable in d2diag, not yet on a
d2dash page · **partial** = some items decoded, rest flagged *candidate* (value shown but scaling
unconfirmed) · **sniff** = seen in bus captures, not decoded · **no** = out of scope.

## Nanocom module coverage on a Discovery 2

| Nanocom module | What it does | d2diag stack | d2dash |
|---|---|---|---|
| Lucas Td5 (SM010) | engine faults, live data, settings, output tests, security | yes | phase 1 (now) |
| Lucas Td5 map read/write (SM201) | read/flash fuel maps | no | no, by design |
| WABCO SLABS (SM016) | ABS + air suspension faults, live, outputs, bleed, heights | yes | phase 1 (now) |
| Valeo BCU (SM023) | body faults, EKA, key fobs, alarm/locking settings | partial | phase 4 |
| Bosch auto box GS8.87 (SM030) | gearbox faults, live data, adaptations | partial | phase 4 |
| TRW SPS airbag (SM015) | airbag faults | partial | phase 4 |
| Lucas ACE (SM032) | active cornering faults, live, bleed | partial | phase 4 |
| Hella cruise (SM039), Webasto FBH (SM038), Motronic V8 | n/a or petrol only | no | no |

Everything below is one page per ECU on the Nanocom, in the same five sections every time:
**Faults · Inputs · Settings · Outputs · Utilities**. d2dash adopts the same five sections inside
the Engine and SLABS tabs so the layout is familiar to anyone who has used a Nanocom.

## Td5 engine ECU

### Faults
| Nanocom | Ours |
|---|---|
| Read faults, tagged current / logged | built |
| Clear faults | built |
| Fault reference (display code + likely causes) | lib — d2diag carries the dictionary; show the cause text under each fault |

### Inputs: Fuelling (22 values)
Engine speed, idle speed error, road speed, battery, accel way 1/2/3, accel supply, coolant temp,
fuel temp, air inlet temp, air flow, ambient pressure, manifold pressure, EGR modulator, EGR inlet,
wastegate modulator, cylinder balance 1-5.

All 22: **lib** (decoded). d2dash shows 13 of them today; the rest go on the Engine → Inputs page in
Nanocom order.

### Inputs: Switches (12)
| Item | Ours |
|---|---|
| Brake switch 1, brake switch 2 | lib |
| Cruise control, cruise resume, set/accelerate | lib |
| Clutch switch, transfer ratio, gearbox P/N | sniff |
| AC clutch request/drive, AC fan request/drive | sniff |

### Inputs: extra (not on the Nanocom)
Accelerator pedal %, modelled air mass, sensor voltages (MAF, coolant, intake, fuel), ambient
pressure 2, battery direct, injection quantity, driver demand, smoke limit, torque limit, native EGR
and wastegate position, fuel pump relay. All **lib**. These are a d2diag bonus over the Nanocom.

### Settings
| Nanocom | Ours |
|---|---|
| Injector codes 1-5 (read, write) | sniff: read first, write only once upstream has confirmed the routine |
| Injector type | sniff |
| Config tune ID, fuel tune ID, homologation, VIN | sniff |
| ECU part number | built (ECU identity) |
| 21 feature flags (temp gauge, tacho, SLABS link, road speed, radiator fan, MIL, fuel used, fuel temp, EGR modulator, EGR inlet, cruise lamp, cruise control, clutch switch, CAN bus, aux fan, auto gearbox, A/C, active engine mount, ambient sensor, wastegate modulator, ECU status) | sniff: read-only page first |
| Save settings to file / reload / write back | build on top once reads work |

### Outputs (14 pulse tests)
A/C clutch, A/C fan, MIL lamp, fuel pump, glow plugs, rev counter, wastegate modulator, temp gauge,
EGR throttle, injector 1-5. All **built** behind a confirm prompt. Upstream note: the frames are
decoded from captures and have not yet been fired from this code on a car, so the first use of each
is a test.

### Utilities
| Nanocom | Ours |
|---|---|
| Get security status | built |
| Learn security code (ECU re-learns the BCU mobilisation code) | lib; add behind a double confirm, it can leave the car immobilised if it fails |

## WABCO SLABS (ABS + SLS)

### Faults
Read current / intermittent with occurrence counts, clear: **built** (counts not shown yet; only two
fault bits have names, the rest print as `unknown (byte, bit)` until the dictionary grows).

### Settings
| Nanocom | Ours |
|---|---|
| Test status, ECU calibrated, transport mode, suspension type (SLABS vs ABS-only) | candidate (four raw setting bytes read; meaning unconfirmed) |
| Left/right current height (0-255) | built |
| Left/right target height, store target heights | lib (`store_heights`); calibration sequence still sniff |
| Identity: factory code, bar code, product number, module codes, VIN, engine, gearbox | sniff |

### Inputs: ABS
| Item | Ours |
|---|---|
| Wheel sensor voltage FR/FL/RR/RL | lib |
| Wheel speed FR/FL/RR/RL | built (scaling unconfirmed) |
| Inlet/outlet valve voltages, pump monitor, pump relay, ground reference | candidate |
| Battery, ECU internal supply | built |
| Engine speed, engine torque, throttle position (from the Td5 over the link) | candidate |
| HDC brake, shuttle switch state | candidate / sniff |

### Inputs: SLS
Left/right sensor value: **built**. Sensor supply volts, valve volts, exhaust valve, compressor
relay: **candidate**.

### Inputs: Switches
Neutral, low range, diff lock, reverse, any door, brake signal: **built**. HDC switch, off-road
switch, plip signal: **sniff**.

### Outputs
| Nanocom | Ours |
|---|---|
| SLS exhaust valve, compressor, buzzer; ABS pump relay on/off | built |
| ABS inlet + outlet valves ×8, SLS left/right valves individually | sniff |
| Lamps: TC, ABS, HDC, brake, SLS, off-road, HDC fault, HDC brake; speedometer; brake-light relay | sniff |

### Utilities
| Nanocom | Ours |
|---|---|
| Power bleed, modulator bleed, FR/FL/RR/RL test | built |
| Raise/lower left/right, store heights | built / lib |
| Height calibration wizard | sniff |

Nanocom's own caveat applies to us too: SLS and switch data stop updating above 8 km/h.

## Beyond the Nanocom: the sensor board

Nothing on the K-line reports these; the Nanocom cannot show them. The ESP32 board (stage 2) adds
them as a third source that is always live, whichever ECU holds the bus.

| Sensor | Why | Drive-tab treatment |
|---|---|---|
| EGT, pre-turbo (K-type, MCP9600) | turbo and piston protection under load | hero dial, amber 650 / red 720 °C |
| Oil pressure (0.5-4.5 V transducer) | the Td5 only has a warning switch | bar, red under 0.8 bar above 1200 rpm |
| Oil temperature (NTC) | long tows, sand | bar, amber 120 / red 130 °C |
| Gearbox oil temperature (NTC on the cooler line) | the ZF cooks itself off-road | bar, amber 110 / red 125 °C |
| Fuel level (tap off the sender) | not on the K-line | strip item |
| Alarm buzzer on the board | fires even if the Pi is rebooting | n/a |

## Where this leaves the d2dash layout

- **Drive**: hero dials (coolant, boost, EGT), bars (revs, oil pressure, oil temp, gearbox temp),
  strip (speed, battery, inlet air, fuel rate, injection, fuel temp, fuel level). Alarm band.
- **Engine**: Faults · Inputs (Fuelling / Switches / Extra, Nanocom order) · Settings (read-only
  identity + feature flags, injector codes when confirmed) · Outputs · Utilities.
- **SLABS**: Faults · Inputs (ABS / SLS / Switches) · Settings (heights, target heights) · Outputs ·
  Utilities (bleed, raise/lower, store).
- **More**: alarms, logs, system; later the other ECUs as phase 4 lands.

Build order: Engine and SLABS Inputs pages (all lib items) → fault cause text → Settings read-only →
sensor board source → remaining items as upstream confirms them.
