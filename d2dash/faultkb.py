"""Fault knowledge base: what each Td5 and SLABS fault means, likely causes, likely fixes.

Written from the Discovery Series II workshop manual (RAVE) fault tables, the Td5 engine
management overview, and the Td5/SLABS owner community's accumulated experience. Entries are
matched to the ECU's fault names by pattern so one write-up covers all its variants
(cylinder number, wheel position, Logged High / Logged Low / Current).

Each entry: title, what (one paragraph), causes (list, most likely first), fixes (list),
severity: "drive" (carry on, fix when convenient), "soon" (fix soon; limp or protection
likely), "stop" (do not drive / safety), plus optional `check` — dashboard inputs to watch.
"""
from __future__ import annotations

import re

TD5: list[tuple[str, dict]] = [
    # ---------------- sensors ----------------
    (r"^coolant temp", dict(
        title="Coolant temperature sensor circuit",
        what="The engine coolant temperature (ECT) sensor is a thermistor in the cylinder head outlet. "
             "The ECU uses it for cold-start fuelling, glow plug time, the temperature gauge drive and the "
             "radiator fan. Out of range means the ECU is seeing a voltage it cannot believe and has substituted a default (about 80 °C).",
        causes=["Sensor connector corroded or loose (it sits in a hot, damp spot)", "Sensor failed open or shorted",
                "Chafed wiring to the ECU", "Coolant genuinely out of range only if the gauge also reads extreme"],
        fixes=["Compare the live Coolant temp input with a cold engine: it should match ambient", "Unplug and inspect the connector; clean and refit",
               "Check sensor resistance (about 2.5 kΩ at 20 °C, falling as it warms)", "Replace the sensor — cheap and ten minutes"],
        severity="soon", check=["coolant_temp", "coolant_sensor_v"])),
    (r"^fuel temp", dict(
        title="Fuel temperature sensor circuit",
        what="A thermistor in the fuel pressure regulator housing at the back of the head. The ECU trims injection "
             "quantity for fuel density. With the sensor out of range the ECU uses a default and fuelling is slightly off.",
        causes=["Connector or wiring (the regulator housing is a common oil-leak area, so the plug gets oily)",
                "Sensor failed", "Very hot fuel return after long high-load running (reads high but is genuine)"],
        fixes=["Check the live Fuel temp input against coolant and ambient", "Clean the connector", "Replace the sensor, part of the regulator housing on early engines"],
        severity="drive", check=["fuel_temp", "fuel_sensor_v"])),
    (r"^inlet air temp", dict(
        title="Inlet air temperature sensor circuit",
        what="The inlet air temperature sensor is built into the mass air flow meter on the air cleaner outlet. The ECU "
             "uses it to correct air density. Out of range means the signal is implausible, not that the air is hot.",
        causes=["MAF meter connector loose or wet", "The combined MAF/IAT meter failing", "Wiring between MAF and ECU"],
        fixes=["Check the live Air inlet temp: cold engine should read near ambient", "Reseat the MAF connector",
               "If Air flow is also faulty, the MAF meter itself is the suspect"],
        severity="drive", check=["air_temp", "intake_sensor_v"])),
    (r"^ambient air temp", dict(
        title="Ambient air temperature sensor circuit",
        what="Only fitted to vehicles with automatic air conditioning or the ambient display; the ECU reads it for "
             "the fan and A/C strategy. If your vehicle has no such sensor, this fault means the ECU configuration "
             "says one is fitted when it is not.",
        causes=["Sensor behind the front bumper damaged or disconnected", "Configuration mismatch after an ECU swap"],
        fixes=["Check the sensor and its plug behind the grille", "If not fitted, the ECU's ambient-sensor configuration should be off"],
        severity="drive", check=["ext_temp"])),
    (r"^air flow circuit", dict(
        title="Mass air flow meter circuit",
        what="The hot-film MAF meter measures the air entering the engine. The Td5 uses it mainly to control EGR and "
             "to limit smoke; with it faulted the ECU drops to a model, EGR is disabled and power may be reduced. A "
             "lazy MAF (reading low without a fault) is the classic cause of a flat Td5.",
        causes=["MAF meter failed or contaminated (oiled foam filters are a known killer)", "Connector or wiring", "Air leak between MAF and turbo giving an implausible reading"],
        fixes=["Watch Air flow at idle (warm, around 30–60 kg/h) and under full load (should climb well past 400 kg/h)",
               "Unplug the MAF and drive: if the car feels better, the MAF is lazy", "Replace with a genuine or Bosch meter; pattern parts are poor"],
        severity="soon", check=["maf_sensor", "maf_sensor_v", "maf"])),
    (r"^manifold pressure", dict(
        title="Manifold absolute pressure sensor circuit",
        what="The MAP sensor on the inlet manifold tells the ECU the boost pressure, which sets the fuelling limit "
             "(smoke limit) and controls the wastegate. With it faulted the ECU limits fuel heavily — very flat performance.",
        causes=["Sensor contaminated with oil from the breather (very common; the sensor face gets coated)",
                "Connector or wiring", "Sensor failed"],
        fixes=["Compare Manifold pressure to Ambient pressure with the engine off: they should be equal",
               "Remove the sensor and clean it gently with electrical contact cleaner", "Fix the source of oil (breather, turbo seal) or it will recur", "Replace the sensor"],
        severity="soon", check=["manifold_press", "ambient_press_1"])),
    (r"^ambient pressure", dict(
        title="Ambient (barometric) pressure sensor",
        what="A barometric sensor inside the ECU gives altitude compensation. A fault here is in the ECU itself, "
             "or the ECU is comparing it with the MAP sensor and finding them impossibly far apart at key-on.",
        causes=["MAP sensor reading wrong at key-on (ambient should equal manifold with the engine off)", "ECU internal sensor fault"],
        fixes=["Check the MAP sensor first", "If Ambient pressure reads nothing like 0.85–1.03 bar, the ECU needs attention"],
        severity="drive", check=["ambient_press_1", "ambient_press_2", "manifold_press"])),
    (r"^reference voltage", dict(
        title="Sensor reference voltage (5 V supply)",
        what="The ECU supplies a regulated 5 V to the pedal, MAP and other sensors. If it sags or is shorted every "
             "sensor on that supply reads wrong at once, so this fault is usually accompanied by several others.",
        causes=["A sensor or its wiring shorting the 5 V line to earth or battery", "Water in a sensor connector", "ECU regulator fault"],
        fixes=["Look at Accel. supply on the Inputs page: should sit at 5.0 V", "Unplug sensors one at a time (pedal, MAP, MAF) and see which one restores it",
               "Inspect the harness where it crosses the engine for chafe"],
        severity="soon", check=["accel_supply"])),
    (r"^battery volt", dict(
        title="Battery voltage out of range",
        what="The ECU monitors its supply. Too low while running points to charging; too high to a regulator fault. "
             "Low voltage during cranking in cold weather can log this harmlessly on a tired battery.",
        causes=["Weak battery or poor terminals", "Alternator not charging or over-charging", "Corroded engine or body earth straps"],
        fixes=["Battery input should read 13.5–14.4 V with the engine running", "Load-test the battery; clean terminals and earths", "Check alternator output and belt"],
        severity="soon", check=["battery", "battery_direct"])),
    # ---------------- pedal ----------------
    (r"driver demand supply", dict(
        title="Accelerator pedal supply",
        what="The pedal potentiometer's supply from the ECU is out of range. Without a believable pedal signal the "
             "ECU holds the engine at idle or a fixed fast idle — the 'no throttle response' limp.",
        causes=["Pedal connector loose or water-damaged (under the dash, driver's footwell)", "Harness damage to the pedal", "Pedal unit failed"],
        fixes=["Accel. supply input should read about 5 V", "Reseat the pedal connector", "Replace the pedal assembly"],
        severity="soon", check=["accel_supply", "accel_way1", "accel_way2", "accel_way3"])),
    (r"driver demand (problem|\d out of range)|problem detected with driver? demand|inconsistencies found with driver demand", dict(
        title="Accelerator pedal position sensor",
        what="The Td5 pedal has two or three potentiometer tracks that must agree. One track out of range, or the "
             "tracks disagreeing, logs this fault and the ECU limits the engine to idle or a slow response. It is one "
             "of the most common Td5 faults and almost always the pedal itself.",
        causes=["Worn pedal potentiometer track (intermittent at a particular pedal position)", "Pedal connector corrosion or water ingress", "Chafed pedal wiring"],
        fixes=["Watch Accel. way 1/2/3 while pressing the pedal slowly: all should sweep smoothly with no jumps or dropouts",
               "Clean and reseat the connector", "Replace the pedal assembly (verify 2-way or 3-way type first; the ECU setting must match)"],
        severity="soon", check=["accel_way1", "accel_way2", "accel_way3", "accel_pedal_pct"])),
    # ---------------- injectors ----------------
    (r"^inj\. (\d) open circuit", dict(
        title="Injector {n} — open circuit",
        what="The ECU cannot drive current through injector {n}'s solenoid. The cylinder will misfire or be dead and "
             "the engine will run rough with a strong diesel smell.",
        causes=["Injector harness inside the rocker cover broken or oil-soaked (the Td5's well-known weak point)",
                "The red ECU connector or the harness connector on the cover corroded or oily", "Injector solenoid failed"],
        fixes=["Check the injector harness under the rocker cover for cracked insulation and oil",
               "Pull the red ECU plug and look for oil wicked up the loom — if present, clean it and fit a new injector harness",
               "Swap injectors between cylinders to see if the fault follows the injector"],
        severity="soon", check=["balance_{n}"])),
    (r"^inj\. (\d) (partial )?short circuit", dict(
        title="Injector {n} — short circuit",
        what="Injector {n}'s circuit is drawing too much current — a short to earth, to another injector, or inside the "
             "solenoid. The ECU shuts that injector down to protect its driver stage, so the cylinder goes dead.",
        causes=["Oil-damaged injector harness inside the rocker cover letting wires touch", "Chafed loom at the cover exit",
                "Injector solenoid shorted internally", "Oil in the red ECU connector"],
        fixes=["Replace the under-cover injector harness; inspect the ECU red plug and clean any oil",
               "Measure the injector resistance (all five should match)", "Swap injectors to confirm before buying one"],
        severity="soon", check=["balance_{n}"])),
    (r"^inj\. (\d) peak charge (long|short)", dict(
        title="Injector {n} — peak charge timing",
        what="The ECU measures how long injector {n}'s solenoid takes to reach peak current. Too long or too short "
             "means the resistance or inductance of the circuit is off — a degraded connection or a solenoid going down. "
             "Often the first sign of harness trouble before an open or short is logged.",
        causes=["High-resistance joint in the injector harness or its connectors", "Oil contamination of the harness",
                "Injector solenoid ageing"],
        fixes=["Inspect and renew the injector harness and clean the cover connector", "Compare injector resistances",
               "Watch the cylinder's balance value: it will drift as the problem worsens"],
        severity="drive", check=["balance_{n}"])),
    (r"topside switch failed (pre|post) injection", dict(
        title="Injector driver (topside switch) failure",
        what="The 'topside switch' is the high-side transistor inside the ECU that powers the injectors. The ECU tests "
             "it before and after each injection. A failure here is in the ECU's output stage — or the ECU is being "
             "damaged by oil that has crept up the injector harness into its connector.",
        causes=["Engine oil in the red ECU connector shorting pins (check this first)", "ECU output stage failed, often after a shorted injector harness"],
        fixes=["Unplug the red ECU connector: if there is oil, clean both halves thoroughly and fit a new injector harness",
               "If clean and the fault persists, the ECU needs repair (specialist repairers refurbish Td5 ECUs) or replacement"],
        severity="soon")),
    (r"injector trim data corrupted", dict(
        title="Injector codes corrupted",
        what="Each Td5 injector carries a calibration code that is programmed into the ECU. The stored codes have "
             "failed their checksum, so the ECU is running default trims: uneven idle and poor economy until re-entered.",
        causes=["ECU memory corruption, usually after low voltage during programming", "ECU swapped without codes being entered"],
        fixes=["Read the code stamped on each injector (five digits, under the hold-down clamp) and re-enter them with a Nanocom; this tool cannot write them yet"],
        severity="drive", check=["balance_1", "balance_2", "balance_3", "balance_4", "balance_5"])),
    # ---------------- boost / turbo ----------------
    (r"turbocharger over ?boost|over boost has occurred", dict(
        title="Turbo over-boost",
        what="Manifold pressure exceeded the map limit. The ECU cuts fuel to protect the engine, which feels like a sudden "
             "loss of power under hard acceleration that returns after lifting off.",
        causes=["Wastegate actuator sticking or its rod seized", "Wastegate modulator valve or its vacuum hoses faulty",
                "Over-tight actuator adjustment after a turbo rebuild", "Remapped ECU running beyond stock boost"],
        fixes=["Check the wastegate rod moves freely; free off the wastegate flap", "Inspect vacuum hoses to the modulator for splits",
               "Watch Manifold pressure on a hard pull: stock peaks around 2.3 bar absolute"],
        severity="soon", check=["manifold_press", "wastegate_modulator"])),
    (r"turbocharger under ?boost|under boost has occurred", dict(
        title="Turbo under-boost",
        what="Manifold pressure is below what the ECU expects for the fuel being injected. The ECU limits fuelling to "
             "avoid smoke, so the engine feels flat, and the exhaust may smoke on hard acceleration.",
        causes=["Split or blown intercooler hose (listen for a whistle or hiss under load)", "Intercooler leaking at the end tanks",
                "Wastegate stuck open or actuator diaphragm split", "Turbo worn", "MAP sensor reading low (oil on it)"],
        fixes=["Inspect every boost hose and the intercooler; pressure-test the system", "Check the wastegate actuator holds vacuum",
               "Clean the MAP sensor", "Watch Manifold pressure under load"],
        severity="soon", check=["manifold_press", "wastegate_modulator", "maf_sensor"])),
    (r"wastegate (modulator )?(open load|short circuit)", dict(
        title="Wastegate modulator circuit",
        what="The wastegate modulator is a solenoid valve the ECU pulses to control vacuum to the wastegate actuator. "
             "Open load means no solenoid seen; short means too much current. Without it boost control is lost and "
             "the engine will over- or under-boost.",
        causes=["Modulator connector corroded (it lives on the inner wing)", "Solenoid coil failed", "Wiring chafe"],
        fixes=["Check the connector and the coil resistance (about 30 Ω)", "Replace the modulator"],
        severity="soon", check=["wastegate_modulator", "manifold_press"])),
    (r"wastegate diagnostics", dict(
        title="Wastegate control not responding",
        what="The ECU commanded the wastegate and did not see the boost pressure respond as expected — the modulator "
             "circuit is electrically fine but the mechanical side is not doing what it is told.",
        causes=["Vacuum hoses split, kinked or wrongly routed", "Vacuum pump output weak", "Actuator diaphragm leaking", "Wastegate flap seized"],
        fixes=["Apply vacuum to the actuator by hand and watch the rod move", "Check hoses and the vacuum pump", "Free the wastegate"],
        severity="soon", check=["manifold_press", "wastegate_modulator"])),
    # ---------------- EGR ----------------
    (r"egr (vacuum )?modulator (open load|short circuit)|egr vacuum diagnostics", dict(
        title="EGR vacuum modulator circuit",
        what="The EGR modulator is a solenoid that routes vacuum to the EGR valve. Electrical faults here, or the EGR "
             "not responding to it, log this fault. If the EGR has been blanked or removed and the modulator unplugged, "
             "this fault is expected and harmless.",
        causes=["Modulator unplugged (after EGR removal)", "Connector or coil failed", "Split vacuum hoses"],
        fixes=["If the EGR was removed deliberately: leave the modulator plugged in or fit a resistor to keep the ECU happy",
               "Otherwise check the connector, the coil and the hoses"],
        severity="drive", check=["egr_modulator"])),
    (r"egr inlet throttle (open load|short circuit|diagnostics)", dict(
        title="EGR inlet throttle circuit",
        what="Later Td5s have a throttle flap in the inlet (the 'ILT') worked by a second vacuum modulator to help EGR "
             "flow. An electrical fault or a flap that does not respond logs this. Harmless if the EGR system has been "
             "removed and the modulator unplugged.",
        causes=["Modulator unplugged after EGR removal", "Connector or coil failed", "Flap seized with soot", "Vacuum hoses"],
        fixes=["Check the modulator and its hoses", "Free the flap", "If deliberately removed, keep the modulator plugged in"],
        severity="drive", check=["egr_inlet"])),
    (r"egr valve stuck (open|closed)", dict(
        title="EGR valve stuck",
        what="The ECU infers from the air-flow reading that the EGR valve is not moving. Stuck open means exhaust gas "
             "is always recirculating — poor idle, smoke and a flat engine; stuck closed is harmless to driving but "
             "an emissions fault.",
        causes=["Soot-caked EGR valve", "Diaphragm in the valve split", "Vacuum supply problem", "Blanked EGR (stuck closed is expected then)"],
        fixes=["Remove and clean the valve, or replace it", "Many owners blank the EGR and accept the logged fault"],
        severity="drive", check=["maf_sensor", "egr_modulator"])),
    # ---------------- drives ----------------
    (r"^fuel pump drive", dict(
        title="Fuel pump relay drive",
        what="The ECU switches the in-tank fuel pump through a relay. Open load means it sees no relay coil; over "
             "temperature means the output is being overloaded. If the pump does not run the engine will not start.",
        causes=["Fuel pump relay missing or failed", "Relay socket corroded (engine bay fuse box)", "Wiring to the relay"],
        fixes=["Listen for the pump prime at key-on", "Swap the relay with an identical one in the fuse box", "Check the Fuel pump relay input shows on"],
        severity="soon", check=["fuel_pump_relay"])),
    (r"^mil lamp drive", dict(
        title="Engine warning lamp drive",
        what="The ECU drives the engine malfunction indicator lamp in the instrument pack. Open load usually means "
             "the bulb has blown or the instrument pack connection is poor.",
        causes=["Bulb blown", "Instrument pack connector", "Wiring"],
        fixes=["The lamp should light with the key on and go out once running; if it never lights, replace the bulb"],
        severity="drive")),
    (r"glow ?plug relay drive", dict(
        title="Glow plug relay drive",
        what="The ECU controls the glow plug relay for pre-heat and post-heat. Open load means the relay coil is not "
             "seen, so no glow — hard cold starts and white smoke until warm.",
        causes=["Glow plug relay failed (on the inner wing near the battery)", "Relay connector corroded", "Wiring"],
        fixes=["Check for 12 V at the glow plug bus bar for a few seconds at key-on when cold", "Replace the relay"],
        severity="drive")),
    (r"glow ?plug lamp drive", dict(
        title="Glow plug lamp drive",
        what="The glow plug warning lamp in the instrument pack is not drawing current when driven — normally a blown bulb.",
        causes=["Bulb blown", "Instrument pack connector"],
        fixes=["Replace the bulb"],
        severity="drive")),
    (r"radiator fan drive", dict(
        title="Radiator (auxiliary) fan drive",
        what="On vehicles with an electric auxiliary fan the ECU drives its relay. Open load means no relay coil seen. "
             "On vehicles without the electric fan this fault means the ECU is configured for one that is not fitted.",
        causes=["Fan relay failed or unplugged", "Configuration mismatch", "Wiring"],
        fixes=["Check the relay and its socket", "Check the ECU's radiator fan configuration matches the vehicle"],
        severity="drive")),
    (r"air conditioning (clutch|fan) drive|air conditioning clutch", dict(
        title="Air conditioning clutch / fan drive",
        what="The ECU switches the A/C compressor clutch and condenser fan relays so it can trim idle and load. Open "
             "load means the relay coil is not seen; if the vehicle has no A/C this is a configuration mismatch.",
        causes=["Relay failed or unplugged", "A/C system disabled or removed", "Wiring"],
        fixes=["Check the relays in the engine bay fuse box", "If A/C was removed, the ECU air-conditioning setting should be off"],
        severity="drive")),
    (r"tacho(meter)?", dict(
        title="Rev counter drive",
        what="The ECU supplies the engine speed signal to the instrument pack rev counter. Open load means the "
             "instrument pack is not drawing current on that line.",
        causes=["Instrument pack connector", "Wiring", "Instrument pack fault"],
        fixes=["If the rev counter works, clean the pack connector and clear the fault; if not, trace the wire"],
        severity="drive", check=["rpm"])),
    (r"temperature gauge", dict(
        title="Temperature gauge drive",
        what="The ECU drives the coolant temperature gauge with a PWM signal. Faults here are the gauge circuit, not the "
             "coolant sensor. Diagnostics means the ECU is not seeing the gauge load it expects.",
        causes=["Instrument pack connector", "Wiring", "Gauge failed"],
        fixes=["If the gauge still reads sensibly, clean the pack connector and clear the fault"],
        severity="drive", check=["coolant_temp"])),
    (r"fuel used output drive", dict(
        title="Fuel used signal drive",
        what="The ECU outputs a fuel-consumption pulse to the trip computer or instrument pack. Open load means that "
             "line is not connected to anything — normal on vehicles without a trip computer.",
        causes=["No trip computer fitted (configuration mismatch)", "Wiring", "Instrument pack"],
        fixes=["If there is no trip computer, ignore or have the configuration corrected"],
        severity="drive")),
    (r"gearbox/abs drive", dict(
        title="Engine speed / torque signal to SLABS and gearbox",
        what="The ECU sends a PWM engine signal to the ABS (SLABS) ECU and the automatic gearbox ECU over a shared "
             "line. Open load means the line is not loaded as expected. **A fault here can make the SLABS ECU log "
             "'Engine PWM Signal Bad' and bring on the ABS, TC and HDC lamps together**, so check it when chasing the Three Amigos.",
        causes=["Connector at the SLABS ECU or the gearbox ECU loose or corroded", "Wiring between the three ECUs chafed", "SLABS ECU failed"],
        fixes=["Inspect the SLABS ECU multiplug and earths", "Check the wire from the engine ECU to the SLABS ECU for continuity", "Clear and see if it returns"],
        severity="soon")),
    (r"cruise (control )?lamp drive", dict(
        title="Cruise control lamp drive",
        what="The cruise 'on' lamp in the instrument pack is not drawing current — a blown bulb, or no cruise control "
             "fitted while the ECU is configured for it.",
        causes=["Bulb blown", "No cruise fitted", "Instrument pack connector"],
        fixes=["Replace the bulb, or correct the configuration"],
        severity="drive")),
    (r"active engine mount", dict(
        title="Active engine mounting drive",
        what="Some markets had a vacuum-switched engine mount for idle refinement, controlled by the ECU. Open load "
             "means no solenoid seen; if your vehicle has none, the ECU configuration is wrong.",
        causes=["Solenoid or connector", "Not fitted — configuration mismatch"],
        fixes=["Check the mount solenoid on the inner wing, or have the configuration corrected"],
        severity="drive")),
    # ---------------- crank / speed ----------------
    (r"high speed crank", dict(
        title="Crankshaft signal — implausible speed",
        what="The crankshaft position sensor on the flywheel housing reported a speed the ECU considers impossible. "
             "Noise on the sensor wiring, or a damaged reluctor, is the usual cause. Expect stalls or misfires if it is active.",
        causes=["Crank sensor wiring picking up interference (routing near the starter cable)", "Sensor air gap or a damaged flywheel reluctor", "Sensor failing when hot"],
        fixes=["Inspect the sensor plug and wiring on the bell housing", "Replace the sensor if intermittent when hot", "Check the flywheel ring teeth"],
        severity="soon", check=["rpm"])),
    (r"noisy crank signal", dict(
        title="Crankshaft signal noisy",
        what="The ECU is seeing extra or missing pulses from the crankshaft sensor. Mild cases log the fault only; worse "
             "cases cause hesitation, a misfire feel or stalling.",
        causes=["Crank sensor connector corroded or wet", "Sensor cable chafed or routed against the starter feed", "Failing sensor", "Damaged flywheel teeth"],
        fixes=["Clean and reseat the sensor connector", "Re-route the cable away from high current wiring", "Replace the sensor"],
        severity="drive", check=["rpm"])),
    (r"road speed missing", dict(
        title="Road speed signal missing",
        what="The engine ECU receives road speed from the SLABS (ABS) ECU, which derives it from the wheel speed sensors. "
             "If that signal drops out, this is logged and cruise control is disabled. Because it comes from the SLABS, "
             "an intermittent SLABS ECU supply, earth or connector — the same things that bring on the Three Amigos — "
             "will log this fault in the engine ECU too.",
        causes=["SLABS ECU connector, fuse or earth intermittent", "Wire from the SLABS ECU to the engine ECU", "SLABS ECU fault", "Speedometer transducer fault on vehicles so equipped"],
        fixes=["Watch Road speed on the Inputs page while driving: it should track the speedometer",
               "Check for SLABS faults at the same time; if the SLABS has none, suspect the wire between the two ECUs or the SLABS ECU supply"],
        severity="drive", check=["speed"])),
    # ---------------- CAN / gearbox ----------------
    (r"can (rx/tx|tx/rx) error|excessive can bus off|can has had reset|unable to detect remote can", dict(
        title="CAN bus communication fault",
        what="The engine ECU talks to the automatic gearbox ECU over a two-wire CAN bus. Errors here mean messages were "
             "lost or the bus went silent. On a manual vehicle the ECU should be configured without CAN; if it is "
             "configured for an automatic, this fault is permanent and harmless.",
        causes=["Manual vehicle with the ECU configured for an automatic", "CAN wiring or connector at the gearbox ECU", "Gearbox ECU unpowered or faulty", "Low battery voltage during cranking"],
        fixes=["Manual gearbox: have the CAN / auto gearbox configuration set off", "Automatic: check the gearbox ECU fuses and the CAN pair for chafe"],
        severity="drive")),
    (r"problem detected with auto gear ?box", dict(
        title="Automatic gearbox reports a problem",
        what="The gearbox ECU has told the engine ECU over CAN that it has a fault of its own. The gearbox will likely "
             "be in its limp mode (stuck in one gear). The detail is in the gearbox ECU, which this tool does not read yet.",
        causes=["Gearbox ECU fault — see its own fault codes", "Gearbox fluid or sensor issue"],
        fixes=["Read the gearbox ECU with a Nanocom", "Check gearbox oil level and condition"],
        severity="soon")),
    # ---------------- cruise ----------------
    (r"cruise control (set|resume) stuck closed", dict(
        title="Cruise control switch stuck",
        what="The set or resume button on the steering wheel appears permanently pressed, so the ECU disables cruise.",
        causes=["Steering wheel switch stuck or failed", "Rotary coupler (clock spring) in the column shorting the switch line"],
        fixes=["Check the switch moves freely", "Watch the Cruise set / resume inputs: they should be off with nothing pressed"],
        severity="drive", check=["cruise_set", "cruise_resume"])),
    (r"cruise control system problem|vehicle accel\. outside bounds", dict(
        title="Cruise control system problem",
        what="Cruise disengaged because the vehicle accelerated or decelerated outside the limits it is allowed to "
             "control, or the brake and clutch inputs disagreed. Usually a one-off from a steep hill or a brake switch "
             "that is out of adjustment.",
        causes=["Brake pedal switch misadjusted or failing (the brake inputs disagree)", "Steep hill while on cruise", "Road speed signal glitch"],
        fixes=["Check Brake switch 1 and 2 both change together when the pedal is pressed", "Clear and see if it returns"],
        severity="drive", check=["brake_main", "brake_switch_2", "speed"])),
]

SLABS: list[tuple[str, dict]] = [
    (r"^(front|rear) (left|right) sensor — output low|^(right|left) (front|rear) wheel speed sensor — output too low", dict(
        title="{pos} wheel speed sensor — weak signal",
        what="The {posl} wheel speed sensor is producing a signal, but it is too weak or dropping out. The ECU "
             "cannot trust that wheel's speed, so ABS, traction control and hill descent are switched off — the "
             "ABS, TC and HDC lamps come on together (the Three Amigos). Weak signals are usually mechanical, not electrical.",
        causes=["Air gap too large: sensor not fully seated, or rust jacking under its flange", "Reluctor ring on the hub cracked, rusted or packed with mud",
                "Wheel bearing play letting the gap vary (often worse on bends)", "Sensor tip contaminated with metal swarf"],
        fixes=["Compare the four wheel speeds on the chassis graphic while driving slowly: the bad corner reads low or drops to zero",
               "Remove the sensor, clean its seat and tip, refit fully home", "Inspect the reluctor ring through the sensor hole", "Check the wheel bearing for play"],
        severity="soon", check=["wheel_speed_{k}", "abs_sensor_{k}"])),
    (r"^(front|rear) (left|right) sensor — electric fail", dict(
        title="{pos} wheel speed sensor — electrical failure",
        what="The {posl} wheel speed sensor circuit is open or shorted — the ECU sees no sensor at all rather than "
             "a weak one. ABS, TC and HDC are disabled until it is fixed.",
        causes=["Sensor cable chafed or broken where it flexes with the suspension", "Connector corroded (behind the inner wing at the front; on the axle at the rear)",
                "Sensor coil failed", "Rodent damage"],
        fixes=["Measure the sensor resistance at its connector (about 1–2 kΩ); open or short confirms the sensor or its tail",
               "Trace the cable along the axle for damage", "Replace the sensor"],
        severity="soon", check=["wheel_speed_{k}", "abs_sensor_{k}"])),
    (r"^shuttle valve switch(es)? — electrical failure|^shuttle valve switch electrical failure", dict(
        title="Shuttle valve switch — electrical failure",
        what="The two shuttle valve switches on the ABS modulator tell the ECU when brake pressure has moved the shuttle "
             "valves. An electrical failure means the circuit is open or shorted. This is the single most common cause "
             "of the Three Amigos on a Discovery 2.",
        causes=["Shuttle valve switch failed (very common; often intermittent when hot)", "Switch connector corroded",
                "Wiring to the modulator chafed"],
        fixes=["Replace both shuttle valve switches on the modulator — they are cheap and fitted together",
               "Check the connector and wiring at the modulator", "If already replaced and the fault remains, suspect the wiring or the ECU connector"],
        severity="soon")),
    (r"shuttle valve switch long term failure", dict(
        title="Shuttle valve switch — long-term failure",
        what="The ECU has not seen the shuttle valve switches change state over many brake applications. Either the "
             "switches are stuck, or the shuttle valves themselves are not moving — the brake fluid side rather than the electrics.",
        causes=["Shuttle valve seized in the modulator (old fluid, corrosion)", "Switch stuck", "Brake light switch not telling the ECU the pedal is pressed, so it never expects movement"],
        fixes=["Bleed the ABS modulator with fresh fluid using the pump test on the Outputs page", "Check the brake light switch and the Brake signal input",
               "Replace the switches if not already done"],
        severity="soon", check=["brake_analog"])),
    (r"shuttle valve switch dynamic failure", dict(
        title="Shuttle valve switch — dynamic failure",
        what="The switches changed state when the ECU did not expect them to, or failed to change under ABS operation. "
             "Points to a sticking shuttle valve or a switch that is intermittent under vibration.",
        causes=["Shuttle valve sticking", "Switch intermittent", "Air in the modulator"],
        fixes=["Bleed the modulator thoroughly", "Replace the switches", "Clear and test with a few firm stops on gravel"],
        severity="soon")),
    (r"shuttle valve sticking", dict(
        title="Shuttle valve sticking",
        what="The ECU has detected that a shuttle valve in the modulator is slow or stuck. This is hydraulic: the "
             "valve bore is contaminated or corroded. Braking still works, but ABS intervention may be wrong.",
        causes=["Old, moisture-laden brake fluid", "Corrosion in the modulator", "Contamination"],
        fixes=["Flush the system with fresh DOT 4 and cycle the pump via the Outputs page while bleeding", "If it persists, the modulator needs overhaul or replacement"],
        severity="soon")),
    (r"pump fail — monitor line", dict(
        title="ABS pump — monitor line fault",
        what="The pump motor has a monitor wire that tells the ECU it is running. The ECU sees an implausible state on "
             "that wire. Often the wiring rather than the pump.",
        causes=["Monitor wire or connector at the pump corroded", "Pump motor brushes worn", "Pump relay"],
        fixes=["Run Pump on from the Outputs page and listen: if it runs but the fault logs, it is the monitor wire",
               "Check the pump connector"],
        severity="soon")),
    (r"pump fail — pump not running when on", dict(
        title="ABS pump not running when commanded",
        what="The ECU switched the pump on and the monitor line says it did not run. Without the pump there is no ABS "
             "or traction control intervention; normal braking is unaffected.",
        causes=["Pump relay or its fuse", "Pump motor failed (brushes)", "Pump supply or earth"],
        fixes=["Check the ABS pump fuse and relay", "Run Pump on from the Outputs page: silence means the motor or its feed",
               "Check the pump earth strap"],
        severity="soon")),
    (r"pump fail — pump sticking", dict(
        title="ABS pump sticking",
        what="The pump was slow to start or stop. Usually a tired motor or a pump stiff with old fluid.",
        causes=["Pump motor wearing out", "Contaminated fluid", "Low supply voltage"],
        fixes=["Flush the brake fluid", "Check battery and charging voltage", "Pump replacement if it recurs"],
        severity="drive")),
    (r"pump fail — pump running when not on", dict(
        title="ABS pump running uncommanded",
        what="The monitor line says the pump is running when the ECU has not switched it on. Either the relay has stuck "
             "closed or the monitor line is shorted.",
        causes=["Pump relay contacts welded", "Monitor wire shorted to supply", "ECU internal relay"],
        fixes=["Pull the pump relay with the key on: if the pump stops, replace the relay", "Check the monitor wiring"],
        severity="soon")),
    (r"ecu internal valve relay bad", dict(
        title="ECU internal valve relay",
        what="The relay inside the ABS ECU that powers the solenoid valves has failed its self-test. This is inside the "
             "ECU; ABS and TC are disabled. Occasionally logged spuriously on low battery voltage.",
        causes=["Low battery or poor earth during the self-test at key-on", "ABS ECU internal fault"],
        fixes=["Check battery voltage and the ECU earths first, clear, and retest", "If it returns with good voltage, the ECU needs repair or replacement"],
        severity="soon", check=["battery", "ecu_supply"])),
    (r"no batt supply voltage", dict(
        title="No battery supply to the ABS ECU",
        what="The ECU lost its main power feed while running, or saw it far too low. On an intermittent fault this is "
             "the fingerprint of a bad connection in the ECU's supply — and brings on all three lamps at once.",
        causes=["ABS ECU fuse or fuse holder corroded", "ECU multiplug not fully latched or with a spread pin", "Main feed wire chafed", "Battery terminals"],
        fixes=["Check and clean the ABS fuses in the engine bay fuse box", "Unplug and inspect the ECU connector; check each pin's tension", "Wiggle-test the harness with the key on while watching the Battery input"],
        severity="soon", check=["battery", "ecu_supply"])),
    (r"ecu gnd or reference gnd bad", dict(
        title="ABS ECU earth fault",
        what="The ECU's ground or its sensor reference ground is high resistance. Earth faults make every sensor read "
             "oddly and cause intermittent lamps that defy sensor replacement.",
        causes=["Corroded earth stud (the ABS ECU earths to the body near its mounting)", "Loose earth strap", "Corrosion in the ECU connector"],
        fixes=["Find the ECU earth points, remove, clean to bright metal, refit with protection", "Check the battery-to-body and engine-to-body straps"],
        severity="soon", check=["ecu_supply"])),
    (r"engine pwm signal bad", dict(
        title="Engine signal from the engine ECU missing",
        what="The engine ECU sends an engine speed/torque PWM signal to the ABS ECU for traction control. The ABS ECU "
             "is not seeing it. **If the engine ECU has logged 'gearbox/abs drive open load' as well, the wire between "
             "the two is the suspect.** Can also appear harmlessly if the engine is cranked with a very low battery.",
        causes=["Wire or connector between the engine ECU and the ABS ECU", "Engine ECU output fault", "Logged during a low-voltage crank"],
        fixes=["Read the engine faults for a gearbox/abs drive fault", "Check continuity of the signal wire between the two ECUs", "Clear and see if it returns while driving"],
        severity="drive")),
    (r"gear info not valid", dict(
        title="Gearbox information not valid",
        what="The ABS ECU uses the neutral, reverse and low-range switch inputs to decide how to run traction control "
             "and hill descent. It is seeing a combination that makes no sense (for example reverse and neutral at once).",
        causes=["Reverse or neutral switch on the gearbox faulty", "Low range switch on the transfer box faulty or disconnected", "Wiring"],
        fixes=["Watch the Switches inputs while selecting each gear and range: each should change cleanly", "Replace the switch that does not respond"],
        severity="drive", check=["neutral_gear", "reverse_gear", "transfer_low"])),
    (r"(front|rear) (left|right) (in|out) valve — open circuit", dict(
        title="{pos} {io}let valve — open circuit",
        what="The {posl} {io}let solenoid valve in the ABS modulator is not drawing current when driven. ABS and TC are "
             "disabled; normal braking continues. The valves themselves rarely fail; the connector is the usual culprit.",
        causes=["Modulator connector not fully latched or corroded", "Harness to the modulator chafed", "Solenoid coil open"],
        fixes=["Unplug the modulator connector, inspect and clean, refit firmly", "Measure the coil resistance at the modulator pins", "If all valves fault together it is the connector or the ECU relay, not the valves"],
        severity="soon")),
    (r"(front|rear) (left|right) (in|out) valve — (short to gnd|short to supply|drive short to supply)", dict(
        title="{pos} {io}let valve — short circuit",
        what="The {posl} {io}let solenoid valve circuit is shorted — to earth, to supply, or within the driver. The ECU "
             "shuts the valve driver down and disables ABS and TC.",
        causes=["Chafed modulator harness", "Water in the modulator connector", "Solenoid coil shorted", "ECU driver stage (if several valves fault together)"],
        fixes=["Inspect the modulator harness and connector for damage and moisture", "Measure each coil resistance; they should all match", "Several valves at once points to the ECU or connector"],
        severity="soon")),
    (r"pump relay — (open circuit|short to gnd|short to supply|drive short to supply)", dict(
        title="ABS pump relay circuit",
        what="The pump relay coil circuit is open or shorted. Without the relay the pump cannot run, so ABS and TC are off.",
        causes=["Relay failed or missing", "Relay socket corroded", "Wiring to the relay"],
        fixes=["Check the pump relay in the engine bay fuse box; swap with an identical relay", "Clean the socket"],
        severity="soon")),
    (r"brake light relay — (open circuit|short to gnd|short to supply|drive short to supply)", dict(
        title="Brake light relay circuit",
        what="The ABS ECU drives the brake light relay (so hill descent can light the brake lamps). The relay coil "
             "circuit is open or shorted. Brake lights themselves still work from the pedal switch on most variants, but check them.",
        causes=["Relay failed", "Socket or wiring", "Relay not fitted on this variant (configuration)"],
        fixes=["Check the brake lights work", "Check the relay and socket"],
        severity="drive", check=["brake_analog"])),
    (r"sticking throttle detected", dict(
        title="Sticking throttle detected",
        what="The ABS ECU compares engine torque demand with vehicle behaviour and believes the throttle is not "
             "closing when it should. Usually a consequence of a bad engine signal rather than a real stuck throttle.",
        causes=["Engine PWM signal to the ABS ECU corrupt", "Accelerator pedal sensor fault (see engine faults)", "Genuinely sticking pedal or cable on earlier variants"],
        fixes=["Read the engine ECU faults for pedal or gearbox/abs drive faults", "Check the pedal returns freely"],
        severity="drive")),
    (r"internal ecu comms error", dict(
        title="ABS ECU internal communication error",
        what="The two processors inside the ABS ECU disagreed. Can be a one-off from low voltage at key-on; if it "
             "returns with a healthy battery it is the ECU.",
        causes=["Low voltage during start", "ECU internal fault"],
        fixes=["Check battery and earths, clear and retest", "ECU repair or replacement if persistent"],
        severity="soon", check=["battery", "ecu_supply"])),
]

SEVERITY_LABEL = {"drive": "Fix when convenient", "soon": "Fix soon", "stop": "Do not drive"}

_POS = {"front left": "Front left", "front right": "Front right", "rear left": "Rear left", "rear right": "Rear right"}
_KEY = {"front left": "fl", "front right": "fr", "rear left": "rl", "rear right": "rr"}


def _strip_state(name: str) -> tuple[str, str]:
    m = re.search(r"\s*\((Current|Logged[^)]*)\)\s*$", name)
    return (name[: m.start()].strip(), m.group(1)) if m else (name.strip(), "")


def _state_note(state: str) -> str:
    if state == "Current":
        return "Present right now."
    if state == "Logged High":
        return "Seen on an earlier run; the signal was above its plausible range (open circuit or short to supply)."
    if state == "Logged Low":
        return "Seen on an earlier run; the signal was below its plausible range (short to earth or no signal)."
    if state == "Logged":
        return "Seen on an earlier run, not necessarily present now."
    return ""


def describe(module: str, name: str) -> dict | None:
    """Full write-up for one fault name, or None if the knowledge base has nothing for it."""
    base, state = _strip_state(name)
    low = base.lower()
    table = TD5 if module == "td5" else SLABS
    for pat, entry in table:
        m = re.search(pat, low)
        if not m:
            continue
        subs: dict[str, str] = {}
        if module == "td5":
            mn = re.search(r"inj\. (\d)", low)
            if mn:
                subs["n"] = mn.group(1)
        else:
            mp = re.search(r"(front|rear) (left|right)", low) or re.search(r"(right|left) (front|rear)", low)
            if mp:
                a, b = mp.group(1), mp.group(2)
                pos = f"{a} {b}" if a in ("front", "rear") else f"{b} {a}"
                subs["pos"] = _POS.get(pos, pos.title())
                subs["posl"] = pos
                subs["k"] = _KEY.get(pos, "")
            mio = re.search(r" (in|out) valve", low)
            if mio:
                subs["io"] = mio.group(1)

        def fmt(s: str) -> str:
            for k, v in subs.items():
                s = s.replace("{" + k + "}", v)
            return s

        out = {
            "name": name, "base": base, "state": state, "state_note": _state_note(state),
            "title": fmt(entry["title"]), "what": fmt(entry["what"]),
            "causes": [fmt(c) for c in entry["causes"]], "fixes": [fmt(f) for f in entry["fixes"]],
            "severity": entry["severity"], "severity_label": SEVERITY_LABEL[entry["severity"]],
            "check": [fmt(c) for c in entry.get("check", []) if fmt(c)],
        }
        return out
    if re.match(r"^byte\s*\d+[.,]\s*bit\s*\d+|^unknown \(byte", low):
        return {
            "name": name, "base": base, "state": state, "state_note": _state_note(state),
            "title": "Undecoded fault bit", "severity": "drive", "severity_label": "Note it",
            "what": "The ECU has set a fault bit that the dictionary does not yet name. It is a real stored fault; "
                    "only its meaning is unknown. Note the byte and bit — matching it against a Nanocom reading is how the dictionary grows.",
            "causes": [], "fixes": ["Read the same ECU with a Nanocom or Hawkeye and tell the project which fault it shows"], "check": [],
        }
    return None


def library(module: str, names: list[str]) -> dict:
    """Write-ups for every fault name the ECU can report, keyed by name."""
    return {n: (describe(module, n) or {}) for n in names}
