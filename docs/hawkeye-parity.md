# Bearmach / Britpart Hawkeye on the Discovery 2 (Td5 + SLABS): what is public, and how it compares with disco2-diag

Researched 2026-11-08 with web search and page fetches only. Nothing here was verified on a Hawkeye unit.
Anything marked **[unverified]** or **[inferred]** is exactly that. Project files read for the comparison:
`README.md`, `docs/nanocom-parity.md`, `d2dash/data/README.md`, `d2dash/data/dtc-td5.json` (211 entries),
`d2dash/data/dtc-slabs.json` (65 entries). No project file was modified.

Product lineage, for orientation: the original **Hawkeye** (Bearmach, manual 04/2010 v1.0, software V4/V5, licensed per model with
paid "dongles"/unlock codes), **Hawkeye Pro** (manual 02/2012 v1.0, 84 pp), **Hawkeye Total** (BA5068, all Land Rover models
unlocked, "tested on vehicles up to 2014", manual 04/2014 v3.0). Rimmer Bros lists BA5068 as superseded by DA3600 (Britpart);
Bearmach stopped software support years ago (forum statement, JUKE179r 2024). The Discovery 2 menus are identical across the
2010 and 2014 manuals except where noted below.

---

## 1. Sources

### Official / vendor documents
| # | What | URL |
|---|---|---|
| S1 | Bearmach HawkEye Instruction Manual, 04/2010 EN(1.0), 64 pp, Appendix A "Menus" (Discovery II pp. 34, 43, 47, 50, 55, 58-59) | https://www.fullfatrr.com/gallery/albums/userpics/14187/Hawkeye_manual.pdf |
| S2 | HawkEye Instruction Manual, 04/2014 EN(3.0), ~141 pp (Hawkeye Total era), Appendix A Discovery 2 pp. 69, 88, 97, 102, 110, 120-122 | https://rimmerbros.com/ItemFiles/Manuals/hawkeye-manual.pdf |
| S3 | Hawkeye Version 5 Application List (vehicle/function matrix) | https://landroverforums.com/forum/attachments/discovery-ii-18/14841d1362834377-ultra-gauge-hawkeye-v5-application-list.pdf |
| S4 | HawkEye Pro user manual 02/2012 EN(1.0) (menu pages are headings only in the fetched text) | https://manuals.online/bearmach/medical-equipment/hawkeye-pro/user-manual/1si6e |
| S5 | Same manual on Scribd (body text not accessible without login) | https://www.scribd.com/document/694316762/hawkeye-pro |
| S6 | HawkEye Total "NPI" sheet, Jan 2017 (BA 5068) | https://rimmerbros.com/ItemFiles/Manuals/HawkEye_NPI%20Jan%2017%20Fina-2.pdf |
| S7 | Hawkeye 12-page brochure (accessories; no D2 detail) | https://rimmerbros.com/ItemFiles/Manuals/Hawkeye_12pp_pages_d.pdf |
| S8 | Hawkeye Pro leaflet (not fetched; listed by search only) | https://rimmerbros.com/ItemFiles/Manuals/Hawkeye%20Pro%20V_1%20Leaflet.pdf |
| S9 | Rimmer Bros product page BA5068 Hawkeye Total | https://rimmerbros.com/Item--i-BA5068 |
| S10 | Paddock Spares "Hawkeye Pro FAQs" (issuu) | https://issuu.com/paddockspares/docs/hawkeye_pro_faqs_v1 |
| S11 | Hawkeye user group (Google Groups), EAS thread (P38 only) | https://groups.google.com/g/hawkeye-user-group/c/AKwQLcLLfQw |

### Forum threads with Hawkeye screen text for a D2
| # | Thread | URL |
|---|---|---|
| F1 | AULRO "Some help decyphering codes (Hawkeye)" 2010: SLABS 4114, logged 3126/3157; tailslide's list 4016/4111/4113/4114/4035/4075/4167 | https://www.aulro.com/afvb/archive/index.php/t-115518.html |
| F2 | AULRO "OBDII/Hawkeye error codes": 4014, 4035, 4040; OffTrack on the leading-4 = SLABS | https://www.aulro.com/afvb/discovery-2-a/136666-obdii-hawkeye-error-codes.html |
| F3 | AULRO "have you seen these error codes": same codes, Testbook-style 01.4/03.5 mapping | https://www.aulro.com/afvb/electronic-diagnostic-systems/136822-have-you-seen-these-error-codes.html |
| F4 | AULRO "Defender Td5 fault codes": **Td5 "Fault 3069 MI Lamp Drive Open Load Logged", "Fault 3070 Glow Plug Lamp Drive Open Logged"** read with a Bearmach Hawkeye on a 2004 Td5 | https://www.aulro.com/afvb/archive/index.php/t-147442.html?login=1 |
| F5 | AULRO "Hawkeye" (capabilities on D2: live data, injector codes, throttle ways, actuator tests, SLABS bleed/test) | https://www.aulro.com/afvb/electronic-diagnostic-systems/173280-hawkeye.html |
| F6 | AULRO "Hawkeye Td5" (licensing/vehicle selection) | https://www.aulro.com/afvb/electronic-diagnostic-systems/178217-hawkeye-td5.html |
| F7 | AULRO "list fault codes" (Nanocom (x,y) lists for Td5 and SLABS; pointers to RSW Solutions and muddyoval) | https://www.aulro.com/afvb/archive/index.php/t-113075.html |
| F8 | AULRO "10,6 mil lamp drive open load (logged)" (Nanocom numbering of the same fault as F4's 3069) | https://www.aulro.com/afvb/discovery-2-a/204617-10-6-mil-lamp-drive-open-load-logged.html |
| F9 | LandyZone "Hawkeye codes/meanings": 4045, 4085, 4086, 4134 with text | https://www.landyzone.co.uk/land-rover/hawkeye-codes-meanings.246656 |
| F10 | LandyZone "D2 Hill Descent warning light": F4023 "Gear information not plausible"; Hawkeye SLABS programming = ride-height calibration only; coils/air toggle | https://landyzone.co.uk/goto/post?id=4883064 |
| F11 | LandyZone "Adjusting ride height with hawkeye" (V4 vs V5 behaviour) | https://www.landyzone.co.uk/goto/post?id=1533469 |
| F12 | landroverforums "hawkeye shows code 1590": 4114, 4084 text; 1590 (V8 P1590 shown without the P) | https://landroverforums.com/forum/general-tech-help-8/hawkeye-shows-code-1590-what-now-69730/ |
| F13 | landroverforums "abs codes": 4012; "leave the front 4 off" | https://landroverforums.com/forum/discovery-ii-18/abs-codes-43625/ |
| F14 | landroverforums "Hawkeye Diagnostic": "Fault 4114 Historical, Electrically Supervision" | https://landroverforums.com/forum/discovery-ii-18/hawkeye-diagnostic-56275/ |
| F15 | landroverforums "Fault: 108" (Hawkeye transmission menu: "Fault 108 Continuous Power Supply Interruption", "Fault 33 / P1884") | https://landroverforums.com/forum/discovery-ii-18/fault-108-a-80941 |
| F16 | landroverforums "hawkeye tool codes" (start-up screens: EMS, M 5.2.1 / Td5 choice) | https://landroverforums.com/forum/discovery-ii-18/hawkeye-tool-codes-101526/ |
| F17 | landroverforums "LR Disco 2 diagnostic tools shootout 2024" (owner of Hawkeye Total + Nanocom: "Nanocom is the better choice", no detail) | https://landroverforums.com/forum/discovery-ii-18/lr-disco-2-diagnostic-tools-shootout-2024-a-120004/?nojs=1 |
| F18 | landroverforums "new hawkeye total" p3 (codes D2 remotes with the serial tag; DTC text is "the standard explanation", no diagnostics) | https://landroverforums.com/forum/discovery-ii-18/new-hawkeye-total-84979/page3/?nojs=1 |
| F19 | landroverforums "Hawkeye Bearmach diagnostic tool" (for sale: ABS codes, key fobs, DRL/locking settings, ABS power bleed) | https://landroverforums.com/forum/discovery-ii-18/land-rover-discovery-ii-hawkeye-bearmach-diagnostic-tool-111262 |
| F20 | landroverforums "calibrating air suspension" (Hawkeye shows per-side heights, adjusts in test mode, could not write baseline) | https://landroverforums.com/forum/discovery-ii-18/calibrating-air-suspension-90651/ |
| F21 | landroverforums "hawkeye diagnostic tool" p2 (no technical content) | https://landroverforums.com/forum/discovery-ii-18/hawkeye-diagnostic-tool-56206/page2 |
| F22 | defender2.net "2006 TD5 defender driver demand 1 high" (Hawkeye live-data labels "driver demand 1 foot off 0%", "sup") | https://www.defender2.net/forum/post872820.html |
| F23 | defender2.net post 680335 ("Driver Demand Sup reading on my Hawkeye") | https://www.defender2.net/forum/post680335.html |
| F24 | AULRO "calibrating SLS height" (Nanocom only: SLABS/Settings page 3 Target Height L/R) | https://www.aulro.com/afvb/discovery-2-a/162860-calibrating-sls-height.html |
| F25 | AULRO "Help Please - Code Deciphering" (Foxwell NT510 Td5 text; "160,CAN Error") - not Hawkeye, used as cross-check | https://www.aulro.com/afvb/archive/index.php/t-263017.html |
| F26 | landroverforums "ABS codes read what do they ALL mean" (Autologic SLS text) - not Hawkeye | https://landroverforums.com/forum/discovery-ii-18/abs-codes-read-what-do-they-all-mean-22307/ |
| F27 | landroverforums "abs codes 118077" (Autel AL619 SLABS text incl. "Engine speed input signal intermittent or missing") - not Hawkeye | https://landroverforums.com/forum/discovery-ii-18/abs-codes-118077/ |
| F28 | landroverforums "help abs fault codes" (044/046/022 three-digit codes, tool unnamed) | https://landroverforums.com/forum/discovery-ii-18/help-abs-fault-codes-52772 |

Fetched but not useful (no Hawkeye content or fetch blocked): AULRO t-119167, t-124681, 234491-turbo-overboost, 186144; landroverforums 3-amigos-24364;
4x4community.co.za threads 128062, 112972, 100224, 383542 (all returned client errors; they are South African threads and may hold
more Hawkeye Td5 text, worth opening by hand); Scribd "Wabco Abs Fault Codes" (truck ABS, irrelevant).

---

## 2. Fault-code comparison

### 2.1 How the Hawkeye numbers faults on a D2

- **Not P-codes for the Td5 or SLABS.** The manual's only DTC example ("P0100 - Mass or Volume Air Flow 'A' Circuit", "No Text
  Allocated for this Code") describes the DTC-lookup utility, not what the Td5/SLABS screens show (S1, S2, S4).
- **Format on screen: `Fault <4 digits> <text> <Logged|Current|Historical>`.** Examples: "Fault 3069 MI Lamp Drive Open Load Logged"
  (F4), "Fault 4114 Historical, Electrically Supervision" (F14), "F4023 Gear information not plausible" (F10).
- **Leading digit = ECU** [inferred, consistent across every quote found]: **3xxx = Td5 engine**, **4xxx = SLABS**. Forum
  users confirm "the leading 4 appears to designate the SLABS ECU" (F2) and "just leave the front 4 off" (F13). For the V8 and the
  GS8.87 auto box the Hawkeye shows the P-code digits without the P ("1590" = P1590 rough road, F12; "Fault 33 / P1884", F15).
- **SLABS: the last three digits are the Testbook / RSW Solutions code** that `dtc-slabs.json` already keys as `rsw-NNN`.
  Every one of the 16 Hawkeye SLABS codes found maps onto that scheme (table below). Testbook writes the same number as
  two digits + decimal (4014 → "01.4", 4035 → "03.5", F2/F3).
- **Td5: the last three digits are an index, not byte.bit.** Two data points only (F4): 3069 = "MI Lamp Drive Open Load Logged"
  (ours `9.5`, Nanocom (10,6)) and 3070 = "Glow Plug Lamp Drive Open Logged" (ours `9.6`, Nanocom (10,7)). A plain 8-bits-per-byte
  linear index does **not** fit (it would give 8.4 / 8.5). A 7-slots-per-byte, 1-based index (`n = 7*byte + bit + 1`) fits both
  points **[unverified, two samples; could be coincidence]**; alternatively the Hawkeye may number down a Testbook fault table whose
  order we do not have. Treat the Td5 3xxx → byte.bit mapping as unknown until more pairs are collected.
- The Hawkeye's descriptions are "the standard explanation found online for the code", with "no steps for diagnosing" (F18). Our
  dictionary's `cause` text is already richer than what the Hawkeye shows.

### 2.2 Diff result (script: `/tmp/claude-0/-home-claude/1fa10e91-a924-5d57-abdb-7fa7141d07e7/scratchpad/hawkeye_diff.py`)

No machine-readable Hawkeye list exists online; the script holds the hand-transcribed forum quotes with their source URLs and
compares them to the two JSON files. Run: `python3 -I hawkeye_diff.py /home/claude/disco2-diag/d2dash/data`.

**SLABS (Hawkeye 4NNN vs `rsw-NNN`)**

| Hawkeye | Hawkeye text as quoted | Ours | Verdict |
|---|---|---|---|
| 4012 | (no text in thread) | rsw-012 Pump Fail — Monitor Line | match |
| 4014 | "Pump failure 3 pumps sticks" | rsw-014 Pump Fail — Pump Sticking | match |
| 4016 | "Shuttle Valve Switch Long Term Failure" | rsw-016 same | match |
| 4023 | "Gear information not plausible" | rsw-023 Gear Info Not Valid | match (wording only) |
| 4035 | "outlet valve right hand side rear (power amp with..." | rsw-035 Rear Right Out Valve — Open Circuit | match; Hawkeye says "power amp", i.e. the driver stage |
| 4040 | (no text) | rsw-040 Pump Relay — Open Circuit | match |
| 4045 | "rear left sensor, air gap too large" | rsw-045 Rear Left Sensor — Output Low | match; **Hawkeye names the cause (air gap) where ours names the symptom** — worth adding to the `cause` field |
| 4075 | "R/R Outlet Valve Faulty" | rsw-075 Rear Right Out Valve — Short to Supply | match |
| **4084** | "HISTORICAL sensor - right hand front (driving, broken wire)" | — | **missing** |
| **4085** | "Driving sensor n/s/r" (nearside rear = rear left) | — | **missing** |
| **4086** | "intermittent sensor output during driving n/s/f" (front left) | — | **missing** |
| 4111 | "Shuttle Valve Sticking" | rsw-111 same | match |
| 4113 | "Shuttle Valve Switch Dynamic Failure" | rsw-113 same | match |
| 4114 | "Shuttle Valve Switch Electrical Failure" / "Historical, Electrically Supervision" | rsw-114 same | match |
| **4134** | "Motor speed input, short or broken wire" | — | **missing** (probably the engine-speed/PWM input; Autel renders the same ECU's fault as "Engine speed input signal intermittent or missing", F27) |
| **4167** | "Pump Motor Failed" | — | **missing** |

Observations:
- **084–087 is a missing block.** The three quoted codes follow the corner order the ECU uses in 044–047 and 064–067
  (FR, RL, FL, RR): 084 = front right, 085 = rear left, 086 = front left, so **087 = rear right [inferred]**. Meaning: wheel-speed
  signal lost/intermittent while driving ("driving" fault, as opposed to the static "output low" 044–047 and "electrical fail" 064–067).
  Autel's text for the same ECU ("Front right sensor signal erratic", F27) and the Testbook-style list in F3 ("6-12 … no output or an
  air gap with right hand front wheel speed sensor") corroborate the family, not the exact numbers.
- Our `rsw-012/013/014/015` "Pump Fail" entries are all marked `candidate`; the Hawkeye quote "Pump failure 3 pumps sticks" for 014
  and the Testbook list "01.3 Pump not running when activated / 01.4 Pump failure" (F3) support the existing names.
- Our two `byte.bit` SLABS keys (`3.4`, `10.4`) are a different scheme from the rsw codes; nothing in the Hawkeye material tells
  us how byte.bit maps to rsw-NNN, so that join is still open.
- No Hawkeye quote contradicts any existing SLABS name. No wording difference changes meaning.

**Td5 (Hawkeye 3NNN)**

| Hawkeye | Text | Ours (if the 7-per-byte hypothesis holds) |
|---|---|---|
| 3069 | "MI Lamp Drive Open Load Logged" | 9.5 mil lamp drive open load (Logged) — text matches |
| 3070 | "Glow Plug Lamp Drive Open Logged" | 9.6 glow plug lamp drive open load (Logged) — text matches |
| 3126 | logged, no text quoted (F1) | 17.6 under 7-per-byte (not in dictionary); 15.5 under 8-per-byte (not in dictionary) |
| 3157 | logged, no text quoted (F1) | 22.2 "can tx/rx error (Current)" under 7-per-byte; 19.4 under 8-per-byte |

Only two Td5 faults with text were found; both exist in our dictionary with the same meaning. **No Hawkeye Td5 fault was found
that our dictionary lacks, and no wording difference changes meaning.** The sample is far too small to call the dictionary complete
against the Hawkeye.

**Nanocom "Invalid Fault" slots: (26,4) (26,5) (26,6) and (22,4)–(22,6)** (= ours 25.3, 25.4, 25.5 and 21.3, 21.4, 21.5, all absent
from `dtc-td5.json`). **Nothing found.** No forum post quotes a Hawkeye Td5 code that could be placed in those slots, and the Hawkeye
manuals contain no fault table. Under the 7-per-byte hypothesis they would display as 3179–3181 and 3151–3153; under 8-per-byte as
3204–3206 and 3172–3174. Searching those strings turned up nothing. Note the F1 code **3157** sits in the 3151–3181 neighbourhood,
but it has no text and the hypothesis is unverified, so it is not evidence.

---

## 3. Menu / function comparison

### 3.1 ECUs the Hawkeye reaches on a Discovery 2 (S1, S2, S3)

| System | Hawkeye module name | Hawkeye functions (V5 application list, S3) | d2dash today (nanocom-parity.md) |
|---|---|---|---|
| Engine (Td5) | "EMS TD5" / "Diesel Engine - TD5" | Read DTCs, Clear DTCs, Live Data, ECM Data, Actuators (5 of 9 columns) | phase 1, built |
| Engine (V8) | "M 5.2.1" | + Programming ("Reset Adaptions") | out of scope |
| Transmission | "GS 8.87.0/1" | Read/Clear, Live Data, ECM Data, Actuators, Programming, Maintenance ("Reset Adaptions") | phase 4, partial in d2diag |
| ABS | "WABCO 'D'" / "WABCO D ABS/SLABS" | Read/Clear, Live Data, ECM Data, Actuators, Programming, Maintenance ("Brake Bleed") | phase 1, built |
| Air suspension | "WABCO D ABS/SLABS - Suspension" (Chassis) | Read/Clear, Live Data, ECM Data, Actuators, Programming ("Suspension Configuration") | built (heights) / lib (store) |
| Airbag | "TRW Gen 4" | Read DTCs, Clear DTCs, ECM Data (Live Data per S3; manual lists none) | phase 4 |
| Security / body | "BCU" (Valeo) | Live Data, Circuit Tests, Programming (manual); S3 says Read/Clear/Live only | phase 4 |
| Chassis | "ACE (ROCK / ARC)" | Read/Clear, Live Data, Actuators, Calibration, Bleeding, System Test, ECM Data | phase 4 |
| Instrument pack | not listed | — | not planned |
| Cruise / FBH | not listed | — | not planned |

The Hawkeye never uses the Nanocom's "Faults · Inputs · Settings · Outputs · Utilities" vocabulary. Its five sections are
**Read DTCs · Clear DTCs · Live Data · Circuit Tests (or Actuators) · Programming (or Configuration / Calibration / Maintenance)**,
plus **ECM Data** (identity).

### 3.2 Td5 engine: Hawkeye menu vs d2dash

Source: S1 p. 34 and S2 p. 69 (identical item lists).

| Hawkeye item | Hawkeye detail | d2dash status | Note |
|---|---|---|---|
| Read DTCs | "Fault 3NNN text Logged/Current" | built | ours adds cause text and library pages; Hawkeye has none |
| Clear DTCs | | built | |
| Live Data | **no parameter list in any manual**; forum quotes show "driver demand 1 foot off 0%" 0.57 V, "2" 4.48 V, "sup" 0.00 V (F22), "Driver Demand Sup" (F23) | built (13 shown, 22 lib) | Hawkeye shows pedal tracks as raw volts; ours has the volts in "extra" |
| ECM Data | ECU identity | built (ECU identity) | |
| Circuit Tests: Injector 1–5 Test | | built (injector 1–5) | |
| Circuit Tests: CM Check | meaning not documented; probably "Check/MIL lamp"? **[unverified]** | — | not in Nanocom either |
| Circuit Tests: EGR Vacuum Mod | | — | **gap**: our Outputs list has "EGR throttle" but no EGR vacuum modulator pulse test |
| Circuit Tests: EGR Inlet Thrott. | | built (EGR throttle) | |
| Circuit Tests: Turbo Wastegate | | built (wastegate modulator) | |
| Circuit Tests: MI Lamp | | built (MIL lamp) | |
| Circuit Tests: Glow Plug Lamp | | — | **gap**: we have glow plug *relay*; Nanocom has no glow plug lamp test either |
| Circuit Tests: Glow Plug Relay | | built (glow plugs) | |
| Circuit Tests: Tachometer | | built (rev counter) | |
| Circuit Tests: Temperature Gauge | | built (temp gauge) | |
| Circuit Tests: Fuel Pump | | built | |
| Circuit Tests: A/C Clutch Drive | | built | |
| Circuit Tests: Fan(s) Test | | built (A/C fan) | |
| Programming: Immobilisation — "Immob. NOT Fitted" / "Immob. Fitted" | toggles the ECU's immobiliser flag (the thing that lets a Td5 ECU run without a BCU) | — | **gap**: Nanocom calls this "Learn security code"/security status; ours has status read, learn is lib. The Hawkeye's fitted/not-fitted toggle is a different, blunter write |
| Programming: Read Injector | reads 5 injector codes | sniff | same gap as Nanocom parity |
| Programming: Set Injector 1–5 | writes injector codes (Paddock FAQ: "Yes this is supported", S10) | sniff | |
| Programming: Set Throttle — "Throttle 2 Track" / "Throttle 3 Track" | pedal type (2-track vs 3-track) | sniff (listed under Nanocom feature flags) | Hawkeye exposes it as a dedicated item |

Not on the Hawkeye Td5 menu but in d2dash/Nanocom: 21 feature flags, tune IDs, VIN, cylinder balance, fuel-map read/write,
logged-fault freeze data, our "extra" lib values (air mass, torque/smoke limits, injection quantity), sensor-board gauges.

### 3.3 SLABS: Hawkeye menu vs d2dash

Source: S1 p. 47, S2 p. 97, S3, F10, F11, F19, F20.

| Hawkeye item | d2dash status | Note |
|---|---|---|
| Read DTCs ("Fault 4NNN text", current/historical) | built | ours lacks occurrence counts (as does the Hawkeye, from the quotes) |
| Clear DTCs | built | |
| Live Data (no list in manual; F10 shows switch states "Low range", "Diff Lock" Off; F20 shows per-side height values) | built | |
| ECM Data | sniff (identity) | |
| Circuit Tests: Inlet Valve RF/LF/RR/LR, Outlet Valve RF/LF/RR/LR | sniff (×8 valves) | **gap**: Hawkeye fires each ABS solenoid individually |
| Circuit Tests: Wheel Test RF/LF/RR/LR | built (FR/FL/RR/RL test) | |
| Circuit Tests: Hydraulics RF/LF/RR/LR | — | **gap**: per-corner hydraulic test (likely modulator-bleed per corner) **[meaning inferred]**; Nanocom's "modulator bleed" is whole-system |
| Circuit Tests: Supplies / Grounds | — | not on Nanocom either |
| Circuit Tests: ABS Warning Lamp, TC Warning Light, Brake Warn. Lamp, HDC Info. Light, HDC Fault Light (2014 only) | sniff (lamps) | |
| Circuit Tests: Brake Light Relay, Speedometer (2014 only) | sniff | |
| Circuit Tests: Shuttle Valve Sw. | — | **gap**: a shuttle-valve-switch test; Nanocom shows SVS state as an input only |
| Circuit Tests: Valve Relay, Pump Relay | built (pump relay) / — (valve relay) | |
| Maintenance: Brake Bleed (S3; F19 "power bleeds the ABS pump") | built (power bleed, modulator bleed) | |
| Programming: Suspension Configuration (S3) — ride-height calibration; air/coil type toggle (F10) | built heights / lib store / candidate suspension type | F11: V4 could set and hold heights (lights stayed on); V5 adjusts per side but does not store (one user); F20: "could not write new baseline values". Hawkeye's SLS write support is contested in the field; ours is the same "store_heights lib, calibration sniff" position |

Not on the Hawkeye but in d2dash/Nanocom: SLS exhaust valve / compressor / buzzer outputs, raise/lower per side with live
height, wheel-sensor voltages, inlet/outlet valve voltages, chassis view, target-height read, height calibration wizard
(Nanocom), occurrence counts.

### 3.4 BCU, auto box, ACE, airbag (for the phase-4 roadmap)

The Hawkeye's D2 **BCU** menu is the richest thing in the manual and is **not in the Nanocom parity map at that level of detail**:
48 circuit tests (horn, fuel flap, alarm LED, ignition interlock, crank enable, lock/unlock/superlock, single-point entry, windows,
sunroof, wipers, headlamp wash, fogs, indicators, shift interlock, transfer neutral, sounder, every instrument-pack warning lamp
including Check SLS / Check HDC / Traction / ABS / Diff Lock, heated screens, "Transmitters") and 14 programming items
(Gearbox, Front FOG, Shift Interlock, DRL, Wash Wipe, Key In Warning, Electric Seat, Electric Windows, Heated Fr Screen,
Rear Win / Sun Roof, Autographics, **HDC/SLABS**, Courtesy Lamps, Error Warning), plus in the 2014 manual a long list of
alarm/locking settings (Superlock, Unlocking, Alarm Disarm, Inertia Switch, Speed Locking, Volumetric, Passive, Hazards,
Mislock, Bath Robe Lock, Eng. Immobilised, Low Battery Warn, **EKA**) and Configuration → Crash Reset. S1 lists no Read/Clear DTCs
for the BCU (consistent with the D2 BCU holding no retrievable codes, F7); key-fob coding is reported possible with the
serial tag (F18, F19). **GS8.87**: Read/Clear, Live Data, Maintenance → Reset Adaptions, Read VIN, Program VIN, ECM Data.
**ACE**: Actuators (Warning Lamp, Main Relay, Direct. Ctl. Valve 1/2), Calibration (Upper/Lower/Both Lateral Acc), Bleeding
(Front Axle, Rear Axle, Full Bleed), System Test. **TRW Gen 4 airbag**: Read/Clear DTCs, ECM Data; build-mode entry/exit and
crash reset may belong to this or the TRW SPS entry (layout ambiguous in S1).

---

## 4. Recommendations (ranked)

1. **Add the missing SLABS codes to `dtc-slabs.json`** as `candidate`: `rsw-084` front right wheel sensor, signal lost while
   driving (broken wire / intermittent); `rsw-085` rear left, same; `rsw-086` front left, same; `rsw-087` rear right, same
   [inferred from corner order]; `rsw-134` engine speed (PWM) input short/open; `rsw-167` pump motor failed. Cite F9, F12, F1.
   These are the only concrete dictionary gaps this research produced.
2. **Enrich `cause` text with the Hawkeye's wording where it names a cause**: 045 "air gap too large" (apply to 044–047), 035/075
   "power amp" = ECU driver stage, 014 "pump sticks". Zero risk, small value.
3. **Show the Hawkeye/Testbook code alongside the name on SLABS fault pages** ("4045 / 01.4-style") so a user reading an old
   AULRO or landroverforums thread can match it. The data is already in the key.
4. **Record the Td5 numbering question in the dictionary README** and collect pairs: whenever a Hawkeye-equipped friend reads a
   Td5, log "3NNN + text" next to our byte.bit. Two more pairs would confirm or kill the 7-per-byte hypothesis and would let us
   search for the "Invalid Fault" slots by their Hawkeye numbers. Candidate numbers to grep forums for later: 3151–3153,
   3179–3181 (7-per-byte) or 3172–3174, 3204–3206 (8-per-byte).
5. **SLABS outputs**: the Hawkeye's individual Inlet/Outlet valve tests ×8, Shuttle Valve Sw. test, Valve Relay and per-corner
   Hydraulics tests are the main SLABS functions it has that d2dash does not. They are already "sniff" in nanocom-parity; the Hawkeye
   confirms the ECU supports them, which raises their priority a notch for upstream capture work.
6. **Td5 outputs**: add "EGR vacuum modulator" and "glow plug lamp" pulse tests once upstream captures the frames; the Hawkeye proves
   both are addressable.
7. **Td5 Programming**: expose "throttle 2-track / 3-track" as a dedicated setting (not buried in 21 flags) and treat the
   immobiliser fitted/not-fitted flag as a double-confirm write, same class as "learn security code".
8. **Phase 4 BCU**: use the Hawkeye BCU list in 3.4 as the checklist of what a D2 BCU session can do; it is more concrete than the
   Nanocom guide's summary and includes the dealer-configurable items owners actually want (DRL, single-point entry, HDC/SLABS
   flag, EKA, crash reset).
9. **Do not copy Hawkeye fault text wholesale.** It is terse, inconsistent across firmware ("shuttle valve switch failure" vs
   "Electrically Supervision"), carries no causes, and is of unknown copyright. Our CC BY-SA dictionary already says more.

---

## 5. Could not find

- **Any official Hawkeye fault-code list** for the Td5 or SLABS. Bearmach sold code definitions separately as the "Codebreaker"
  manual (S10); no copy is online. The three manuals (2010, 2012, 2014) contain no D2 fault tables.
- **A machine-readable Hawkeye fault list** of any kind. The diff in §2.2 runs on 16 SLABS and 4 Td5 codes transcribed from forums.
- **The Hawkeye's Live Data parameter lists** for the Td5 or SLABS. Every manual prints "Live Data" as a bare heading. Only
  three live-data labels were found in forum quotes (§3.2).
- **Hawkeye text for Nanocom slots (26,4)–(26,6) and (22,4)–(22,6)**, or for any Td5 fault outside bytes 9 (and the unlabelled
  3126/3157).
- **Confirmation of the Td5 3NNN → byte.bit rule**; two samples only.
- **Meaning of the Td5 circuit test "CM Check"** and of the SLABS "Hydraulics RF/LF/RR/LR" test.
- **Whether the Hawkeye can store SLS target heights on a D2** (V4 yes-with-lights-on, V5 no-store, Bearmach "yes" by email,
  one owner "could not write baseline"; see F11, F20). The Hawkeye Total manual (2014) still has no SLS item for the D2 beyond
  the application list's "Suspension Configuration".
- **Any Hawkeye SLABS fault code outside the 012–167 range**, and codes 013, 015, 017, 020–022, 030–034, 036–037, 041, 044, 046–047,
  050–074, 076–083, 090–112 were not seen on a Hawkeye screen in any thread (our dictionary has them from RSW Solutions, not from
  the Hawkeye).
- **Britpart's current Hawkeye (DA3600) documentation**; Britpart's site did not surface in searches, and the Hawkeye Pro leaflet
  (S8) and Hawkeye Total "V8 application list" linked from S9 were not fetched.
- The four **4x4community.co.za** Hawkeye threads (South African forum) could not be fetched (site returned client errors); titles
  suggest Td5 Hawkeye screen text ("TD5 Check Engine Light", "Hawkeye shows turbo issues", "Reset Discovery Fault codes",
  "Hawkeye") and are worth reading manually.
