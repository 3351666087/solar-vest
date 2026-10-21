// Content for the Solar Vest Explorer: parts, board components, simulation results, flow graph and the guided tour.
// Every number here comes from the design files (pmbh.py, libb.py, 仿真报告.md, 接线表.md, 制造与装配指南.md).

export const CATS = {
  energy:   { label: "Energy",      color: "#f5b544" },
  printed:  { label: "3D-printed",  color: "#b69cff" },
  elec:     { label: "Electronics", color: "#3ddc97" },
  sensor:   { label: "Sensing",     color: "#ff6b8b" },
  device:   { label: "Device",      color: "#67c7ff" },
  textile:  { label: "Textile",     color: "#e2c99a" },
  wiring:   { label: "Wiring",      color: "#f28cc2" },
  rig:      { label: "Test rig",    color: "#9fb2c8" },
};

// ---------------------------------------------------------------- parts of the worn system and the bench rig
// what = what it is; why = the problem it solves; specs = short facts; flow = flow-diagram nodes it belongs to
export const PARTS = {
  panel: { name: "Solar panel", sub: "6 V · 6 W rigid, 12 cells", cat: "energy", flow: ["panel"],
    what: "A 262 × 171 mm glass panel carried on the upper back, tilted 6° so the glass faces slightly skyward.",
    why: "Harvests light where the body is most exposed and least folded, so the wearable can top up its battery during the day.",
    specs: [["Max power", "≈ 4.7 W hot · 5.3 W at 25 °C"], ["Open-circuit", "8.0 V (≈ 8.8 V cold)"], ["Mounting", "6 printed shoes, 18–53 mm air gap"]] },
  shoes: { name: "Panel mounts ×6", sub: "printed standoff shoes", cat: "printed", flow: ["panel"],
    what: "Six shoes in ASA/PETG. Each foot angle is computed from the scanned back curve, so no two are interchangeable.",
    why: "Holds the panel off the body with an air gap, so the hot glass (up to ~55 °C in sun) never sits on the skin and air can flow behind it.",
    specs: [["Air gap", "18–53 mm"], ["Material", "ASA (UV-stable) or PETG"], ["Attachment", "bar-tacked webbing rows"]] },
  ref_cells: { name: "Reference cells", sub: "REF1 panel plane · REF2 shoulder", cat: "sensor", flow: ["refs"],
    what: "Two small solar cells read as light meters: REF1 lies in the panel plane, REF2 stays horizontal on the left shoulder.",
    why: "Separates 'less light' from 'worse harvesting'. Comparing panel output with the reference cells shows how much is lost to angle, shading and heat.",
    specs: [["Cell", "AK epoxy 40 × 28 mm, 3.5 V / 30 mA"], ["Read by", "INA226 0x44 / 0x45"], ["Shunt", "0.47 Ω → ~14 mV at full sun"]] },
  screws: { name: "M2 screws", sub: "22 × PA pan-head self-tapping, 304 steel", cat: "printed", flow: [],
    what: "Self-tapping screws that hold the boards on their bosses and close the three printed enclosures.",
    why: "PA threads cut their own way into 1.7 mm pilots in PETG: no inserts, no nuts, and every lid can be opened again on the bench.",
    specs: [["M2 × 6", "10 — PMB-H 4, webbing hooks 4, LIB 2"], ["M2 × 8", "12 — back, chest and C lids, 4 each"]] },
  ref_holders: { name: "Reference-cell holders", sub: "printed", cat: "printed", flow: ["refs"],
    what: "Printed holders that fix REF1 flush with the panel plane and REF2 level on the shoulder.",
    why: "Repeatable geometry: a reference cell is only useful if its angle is known and does not drift during a walk.",
    specs: [["Material", "ASA / PETG"]] },
  thermocouples: { name: "Thermocouples TC1 · TC2", sub: "panel back · air gap", cat: "sensor", flow: ["panel"],
    what: "Two K-type thermocouples: TC1 taped to the panel back, TC2 in the air gap between panel and vest.",
    why: "Panel voltage drops as it heats. Knowing panel and gap temperature explains output changes and checks that the body side stays comfortable.",
    specs: [["Type", "K, read on a handheld meter"], ["Leads", "W14 · W15, 0.7 m"]] },
  back_pod: { name: "Back unit", sub: "printed enclosure + webbing hooks", cat: "printed", flow: ["mppt", "batt"],
    what: "PETG enclosure hung on webbing row C below the panel. Holds the power board, the 2500 mAh battery and the XIAO logger. An HP600 thermal pad links the board to the enclosure floor.",
    why: "Keeps the charger, battery and logger together next to the panel, so the high-current wires stay short and everything heavy sits low on the back.",
    specs: [["Hangs at", "1.205 m, webbing row C"], ["Interference check", "boolean overlap = 0"], ["Screws", "M2 self-tapping"]] },
  back_pod_lid: { name: "Back unit lid", sub: "printed", cat: "printed", flow: ["mppt"],
    what: "Screw-on lid of the back unit with the PANEL cable port on the left side.",
    why: "Protects the electronics while keeping the J1 panel terminal reachable from the side port.",
    specs: [["Material", "PETG, white or light grey"]] },
  pmbh: { name: "PMB-H power & measurement board", sub: "86 × 60 mm, JLC-assembled", cat: "elec", flow: ["prot", "mppt", "loadsw", "ina"], board: "pmbh",
    what: "The heart of the system: input protection, the CN3791 MPPT charger, a soft-start load switch to the chest, and six INA226 power meters.",
    why: "Turns the panel's unstable output into safe battery charge, and measures every energy flow (panel, battery, load, two reference cells) so the benefit of solar can be proven, not assumed.",
    specs: [["MPPT set point", "5.93 V"], ["Charge limit", "1.2 A"], ["Self-use", "≈ 8 mA"], ["Simulation", "22 / 22 checks pass"]] },
  battery: { name: "Li-Po battery", sub: "1S · 2500 mAh with protection", cat: "energy", flow: ["batt"],
    what: "Single-cell lithium-polymer battery with its own protection circuit, in the back unit.",
    why: "Stores the day's harvest for night, indoor use and the current bursts of Bluetooth streaming.",
    specs: [["Capacity", "2500 mAh · 9.25 Wh"], ["Charge", "up to 1.2 A"], ["Check before use", "red wire to J2 '+'"]] },
  xiao: { name: "XIAO nRF52840 Sense", sub: "logger · BLE", cat: "elec", flow: ["xiao"],
    what: "Small Bluetooth microcontroller plugged into sockets J4/J5 on the power board.",
    why: "Reads the six power meters, controls the switches (night cut-off, charge inhibit, current range, load enable) and streams the energy log to the phone.",
    specs: [["Bus", "I²C to 6 × INA226"], ["Controls", "PV_EN · INH · RANGE · LOAD_EN · SYNC"]] },
  chest_pod: { name: "Chest unit", sub: "printed enclosure", cat: "printed", flow: ["lib", "coreb"],
    what: "Right-chest enclosure holding the hold-up board (below) and BITalino B (above). It has no USB opening.",
    why: "Keeps the ECG unit under test close to its electrodes, and makes it physically impossible to plug in mains-powered USB while electrodes are on the skin.",
    specs: [["Pocket", "right chest"], ["Safety", "no USB while worn"]] },
  chest_pod_lid: { name: "Chest unit lid", sub: "printed", cat: "printed", flow: ["coreb"],
    what: "Lid of the chest unit.", why: "Closes the unit while leaving the cable ports open.", specs: [["Material", "PETG"]] },
  lib: { name: "LIB hold-up board", sub: "ideal diode + 2 × 10 F supercaps", cat: "elec", flow: ["lib"], board: "libb",
    what: "Feeds BITalino B from the back unit through an LM66100 ideal diode. Two 10 F supercaps take over if the supply disappears.",
    why: "A tug on the chest cable or a connector glitch would otherwise reset the ECG unit and break the recording. The supercaps bridge the gap.",
    specs: [["Hold-up", "17–60 s at 65 mA (sim TB5)"], ["Precharge", "≈ 7 min to 90 %"], ["Sync", "back-unit pulse → BITalino I1"]] },
  core_b: { name: "BITalino B", sub: "ECG unit under test", cat: "device", flow: ["coreb"],
    what: "BITalino Core BLE, powered from the solar system instead of its own battery. It records ECG and streams it to the phone.",
    why: "This is the device whose runtime the vest is meant to extend. It is the experiment's subject.",
    specs: [["Link", "Bluetooth Low Energy"], ["Load", "assumed 65 mA, measured in TC-01"]] },
  ecg_b: { name: "HeartBIT ECG sensor + electrodes", sub: "lead I for unit B", cat: "sensor", flow: ["ecg"],
    what: "ECG sensor in an inner pocket on the sternum. Snap electrodes sit on the collarbones (±85 mm), with REF on the lower ribs.",
    why: "Gives unit B a clinical-style lead-I ECG, so the recording quality of the solar-powered unit can be judged.",
    specs: [["IN+ / IN−", "collarbones ±85 mm"], ["REF", "lower ribs ±100 mm"], ["Leads", "W10a/b/c"]] },
  ecg_c: { name: "Electrodes for unit C", sub: "50 mm below B", cat: "sensor", flow: ["unitc"],
    what: "A second lead-I electrode set placed 50 mm below unit B's, mirrored.",
    why: "Lets the battery-powered control unit record the same heart at nearly the same position, so differences come from the power source and not the placement.",
    specs: [["Leads", "W11a/b/c, 30 cm kit leads"]] },
  c_board: { name: "BITalino C", sub: "control unit, own battery", cat: "device", flow: ["unitc"],
    what: "BITalino (r)evolution Board BLE with its own 523450 battery, in the left chest pocket.",
    why: "Signal-quality control: the same ECG recorded without any solar electronics in the loop.",
    specs: [["Battery", "523450, 1000 mAh"], ["Pocket", "left chest"]] },
  c_case: { name: "Case for unit C", sub: "printed", cat: "printed", flow: ["unitc"],
    what: "Two-part PETG case. A flexible key in the lid presses the board's button to mark events during an experiment.",
    why: "Protects the bare board and gives a tactile event marker without opening the case.",
    specs: [["USB", "for charging only when not worn"]] },
  unit_a: { name: "HeartBIT A", sub: "PPG reference", cat: "device", flow: ["unita"],
    what: "BITalino HeartBIT in the lower-left front pocket, with a PulseSensor clipped to the left earlobe.",
    why: "Independent heart-rate reference from a different sensing method (light, not electrodes) to validate the ECG beats.",
    specs: [["Sensor", "PulseSensor on printed ear clip"], ["Link", "Bluetooth"]] },
  ppg: { name: "Ear-clip PulseSensor", sub: "printed clip", cat: "sensor", flow: ["unita"],
    what: "Optical pulse sensor on a printed ear clip lined with 0.5 mm foam.",
    why: "Gives a stable pulse signal on the earlobe while walking.", specs: [["Cable", "W13, 0.6 m"]] },
  phone: { name: "Android phone", sub: "receives all three units", cat: "device", flow: ["phone"],
    what: "One phone in the lower-right front pocket receives B, C, A and the power log.",
    why: "A single time base for every stream, so ECG, PPG and energy data line up.", specs: [["Streams", "B · C · A · XIAO"]] },
  vest: { name: "Custom-fitted vest", sub: "500D Cordura + 3D mesh lining", cat: "textile", flow: [],
    what: "A 10-piece vest cut from a body scan, with yokes and princess seams.",
    why: "Carries about 1 kg of panel and electronics without shifting, and holds the electrodes and units in fixed, repeatable positions.",
    specs: [["Pattern", "10 pieces, seams match ±1.1 mm"], ["Maker", "bag / outdoor-gear sample studio"]] },
  webbing: { name: "Webbing rows A · B · C", sub: "25 mm, bar-tacked", cat: "textile", flow: [],
    what: "Three rows of webbing across the back carry the panel shoes and the back unit hooks.",
    why: "Spreads the load over the back and gives fixed attachment points, so the panel cannot slide or twist.",
    specs: [["Rows", "1.480 · 1.349 · 1.243 m"], ["Joints", "bar tacks"]] },
  pockets: { name: "Instrument pockets", sub: "bellows pockets with flaps", cat: "textile", flow: [],
    what: "Five bellows pockets: chest unit, unit C, HeartBIT A, phone and the thermocouple pouch.",
    why: "Every device has one known place, so experiments can be repeated with the same geometry.", specs: [["Count", "5"]] },
  tunnels: { name: "Cable tunnels", sub: "inside the lining", cat: "textile", flow: [],
    what: "Sewn channels that route the panel lead, the chest cable and the reference-cell leads.",
    why: "No loose wires to snag, and cable length is fixed by the route rather than by chance.", specs: [] },
  W01: { name: "W01 panel lead", sub: "panel → PMB-H J1", cat: "wiring", flow: ["panel", "prot"],
    what: "The panel's own cable, entering the back unit through the side PANEL port to the J1 screw terminal.",
    why: "Carries up to ~0.8 A from the panel. Shortening it removes 3.8 m of coiled cable from the back.", specs: [["Route", "221 mm"], ["Decision", "cut or coil, needs approval"]] },
  W06: { name: "W06 chest cable", sub: "back unit → chest unit", cat: "wiring", flow: ["j6"],
    what: "Five-wire PH2.0 cable: supply, ground, sync and a spare, along the right waist tunnel.",
    why: "Brings solar-backed power and the sync pulse to the chest. It is the link the hold-up board protects.", specs: [["Length", "0.7 m (route 531 mm)"]] },
  W_misc: { name: "Internal wiring", sub: "PH2.0 harness", cat: "wiring", flow: [],
    what: "Battery, NTC, reference-cell, sync and sensor leads (W02–W15).",
    why: "Every wire is specified pin-to-pin with a measured route length.", specs: [["Count", "20 wires"]] },
  // bench
  bench_table: { name: "Bench", sub: "test table", cat: "rig", flow: [], what: "Work surface for the panel tests.", why: "Repeatable indoor and outdoor test setup.", specs: [] },
  bench_stand: { name: "Tilt stand", sub: "printed, 0–90° in 15° steps", cat: "printed", flow: [],
    what: "Two printed cradles with pivot bolts that hold the panel at a set tilt.",
    why: "Measures how output changes with angle (TC-02) without a person in the loop.", specs: [["Steps", "every 15°"]] },
  bench_cover: { name: "Shading cover", sub: "ND mesh", cat: "rig", flow: [],
    what: "Mesh covers that cut light by a known fraction.",
    why: "Simulates cloud or indoor light on demand, and covers the panel completely for the runtime-gain test (TC-24).", specs: [] },
};

// node name → part key
export function partOf(name, group) {
  if (/^shoe_/.test(name)) return "shoes";
  if (/^ref\d_cell/.test(name)) return "ref_cells";
  if (/^ref\d_holder/.test(name)) return "ref_holders";
  if (/^(W14_tip|W15_tip|TC1_tip)/.test(name)) return "thermocouples";
  if (/^back_pod_lid/.test(name)) return "back_pod_lid";
  if (/^back_pod/.test(name)) return "back_pod";
  if (name === "PMB-H") return "pmbh";
  if (/^xiao_/.test(name)) return "xiao";
  if (/^battery_/.test(name)) return "battery";
  if (name === "LIB") return "lib";
  if (/^BITalino_Core_B/.test(name)) return "core_b";
  if (/^chest_pod_lid/.test(name)) return "chest_pod_lid";
  if (/^chest_pod/.test(name)) return "chest_pod";
  if (/^c_case/.test(name)) return "c_case";
  if (/^C_/.test(name)) return "c_board";
  if (/^A_heartbit/.test(name)) return "unit_a";
  if (/^(ear_clip|pulsesensor)/.test(name)) return "ppg";
  if (name === "phone") return "phone";
  if (/^(electrode_B|ecg_sensor_B|W10)/.test(name)) return "ecg_b";
  if (/^(electrode_C|W11)/.test(name)) return "ecg_c";
  if (/^W01/.test(name)) return "W01";
  if (/^W06/.test(name)) return "W06";
  if (/^W\d/.test(name)) return "W_misc";
  if (/^vest\/(webbing|tack|ladderlock|adjuster)/.test(name)) return "webbing";
  if (/^vest\/pocket/.test(name)) return "pockets";
  if (/^vest\/(tunnel|eyelet|ppg_guide|inner_pocket)/.test(name)) return "tunnels";
  if (/^vest/.test(name)) return "vest";
  if (/^panel/.test(name)) return "panel";
  if (name === "table") return "bench_table";
  if (/^(stand_|bolt_)/.test(name)) return "bench_stand";
  if (/^cover/.test(name)) return "bench_cover";
  return group || "vest";
}

// which parts are shells in X-ray mode
export const SHELLS = new Set(["vest", "webbing", "pockets", "tunnels", "back_pod", "back_pod_lid", "chest_pod", "chest_pod_lid", "c_case"]);

// labels shown in the worn scene
export const LABELS_WORN = ["panel", "shoes", "ref_cells", "back_pod", "pmbh", "battery", "xiao", "chest_pod", "lib", "core_b",
  "ecg_b", "c_board", "unit_a", "ppg", "phone", "W06", "thermocouples"];
export const LABELS_BENCH = ["panel", "bench_stand", "bench_cover", "ref_cells", "back_pod", "thermocouples"];

// explode offsets (metres, world space) per part; "out" = away from the body along ±z
export const EXPLODE = {
  panel: [0, 0.06, -0.30], shoes: [0, 0.03, -0.15], ref_cells: [0, 0.06, -0.30], ref_holders: [0, 0.06, -0.27], thermocouples: [0, 0.05, -0.24],
  back_pod: [0, -0.02, -0.06], battery: [0, -0.04, -0.12], pmbh: [0, -0.02, -0.18], xiao: [0, 0, -0.24], back_pod_lid: [0, 0, -0.32],
  chest_pod: [0, 0, 0.05], lib: [0, -0.01, 0.10], core_b: [0, 0.01, 0.15], chest_pod_lid: [0, 0.02, 0.22],
  c_case: [0, 0, 0.05], c_board: [0, 0, 0.10], c_case_lid: [0, 0, 0.17], unit_a: [0, 0, 0.08], phone: [0, 0, 0.10], ppg: [0.03, 0.02, 0.03],
  ecg_b: [0, 0, 0.03], ecg_c: [0, 0, 0.03], vest: [0, 0, 0], webbing: [0, 0, -0.03], pockets: [0, 0, 0.02], tunnels: [0, 0, 0],
};

// ---------------------------------------------------------------- board components (PMB-H and LIB)
export const COMP = {
  pmbh: {
    U1: ["MPPT charger CN3791", "Holds the panel at its maximum-power voltage (5.93 V, set by R5/R6) and charges the battery at up to 1.2 A.", "A panel's voltage collapses if pulled too hard. Holding it at the knee captures 98–99.8 % of the available power in simulation."],
    M1: ["Buck switch AO3401A", "High-side P-MOSFET switched by the CN3791.", "Converts the panel's ~6 V down to battery voltage efficiently (88–94 % in simulation)."],
    D5: ["Freewheel diode SS34", "Carries inductor current while M1 is off.", "Completes the buck converter; dissipates 0.13 W at full sun."],
    L1: ["Inductor 22 µH", "Energy store of the buck converter.", "Smooths the charge current (1.0–1.2 A ripple band at full sun)."],
    R8: ["Charge-current sense 0.1 Ω", "120 mV across it sets the 1.2 A charge limit.", "Protects the battery and the cable from overcurrent."],
    C15: ["Damping capacitor 100 µF", "Electrolytic on the panel input; its resistance damps a ~5 kHz LC resonance.", "Simulation found the MPPT loop could oscillate without it (gain margin ≈ 0 dB). With C15 the margin is unconditional."],
    F1: ["Resettable fuse 1.5 A", "PPTC in the panel line.", "A short in the panel lead heats and trips the fuse instead of the cable."],
    Q1: ["Reverse-polarity switch", "P-MOSFET in the panel line.", "A panel connected backwards does nothing harmful. At night the MCU turns it off with Q8."],
    Q8: ["Night cut-off (PV_EN)", "Lets the MCU switch Q1 off in the dark.", "Stops the battery leaking back into the panel: 1.1 mA → 51 µA in simulation."],
    D1: ["Gate clamp 10 V", "Zener on Q1's gate.", "Keeps the gate voltage under the transistor's 12 V limit."],
    D2: ["Surge clamp SMAJ10A", "TVS diode across the panel input.", "Absorbs spikes; a cold panel can exceed 8.8 V open-circuit."],
    Q2: ["Range switch", "Shorts the 0.22 Ω indoor shunt in daylight.", "One meter covers both 1 A sunshine and milliamp indoor light."],
    Q3: ["Range select", "MCU control for Q2.", "Switches the panel-current meter to its indoor range."],
    D3: ["Gate clamp", "Protects Q2's gate.", "Keeps the gate inside its rating."],
    D4: ["Input clamp", "Schottky from ground to PV_IN−.", "Keeps the meter input above −0.4 V if light jumps while in the indoor range (INA226 limit −0.3 V)."],
    RS1A: ["Panel shunt 0.05 Ω", "Daylight current shunt.", "Measures up to ~1 A with little loss."],
    RS1B: ["Panel shunt 0.22 Ω", "Indoor-range shunt.", "Resolves milliamp currents under office light."],
    U2: ["Power meter 0x40", "INA226: panel current, high range.", "Measures harvested power in daylight."],
    U3: ["Power meter 0x43", "INA226: panel current, indoor range.", "Measures harvested power under room light."],
    U4: ["Power meter 0x41", "INA226: battery current, both directions.", "Shows whether the battery is gaining or losing charge."],
    U5: ["Power meter 0x42", "INA226: load current to the chest.", "Measures what BITalino B actually consumes."],
    U6: ["Power meter 0x44", "INA226: reference cell 1.", "Light level in the panel plane."],
    U7: ["Power meter 0x45", "INA226: reference cell 2.", "Ambient light, horizontal."],
    RS2: ["Battery shunt 0.05 Ω", "Read by U4.", "Bidirectional battery current."],
    RS3: ["Load shunt 0.1 Ω", "Read by U5.", "Current to the chest unit."],
    RS4: ["REF1 shunt 0.47 Ω", "Loads reference cell 1 near short circuit.", "Short-circuit current is proportional to light."],
    RS5: ["REF2 shunt 0.47 Ω", "Loads reference cell 2 near short circuit.", "Short-circuit current is proportional to light."],
    Q4: ["Charge inhibit", "MCU can pull the MPPT pin low.", "Stops charging, for example if the battery NTC reads hot."],
    Q5: ["Load switch", "P-MOSFET feeding the chest cable.", "The MCU decides when the chest unit gets power."],
    Q6: ["Load enable", "Driven by the XIAO.", "Turns the load switch on and off."],
    C10: ["Soft-start capacitor 1 µF", "Slows Q5's turn-on (τ ≈ 9 ms).", "Keeps the inrush under 1 A, found and fixed in simulation."],
    D6: ["Load surge clamp SMF5.0A", "TVS on the chest supply.", "Protects BITalino from spikes on the cable."],
    U8: ["3.3 V regulator ME6211", "LDO for the XIAO and the meters.", "Clean supply for measurement and logic."],
    J1: ["Panel terminal", "Screw terminal, wire entry facing the board edge.", "The panel lead goes straight in through the PANEL port."],
    J2: ["Battery connector", "PH2.0, pin 1 = +.", "No reverse protection here: check the battery's wire colours first."],
    J3: ["NTC connector", "10 kΩ thermistor taped to the battery.", "Lets the MCU stop charging if the cell gets hot."],
    J4: ["XIAO socket A", "Pins D0–D6.", "The logger plugs in; no soldering needed."],
    J5: ["XIAO socket B", "5V, GND, 3V3, D7–D10.", "The logger plugs in; no soldering needed."],
    J6: ["Chest connector", "PH2.0 5-pin: supply, ground, sync, spare, ground.", "Power and sync to the chest unit."],
    J7: ["REF1 connector", "Reference cell 1.", ""],
    J8: ["REF2 connector", "Reference cell 2.", ""],
    R5: ["MPPT divider (top) 200 kΩ", "With R6 sets 5.93 V.", "Chosen in simulation: 98 % of ideal daily energy for a hot worn panel."],
    R6: ["MPPT divider (bottom) 51 kΩ", "With R5 sets 5.93 V.", ""],
  },
  libb: {
    U1: ["Ideal diode LM66100", "Feeds BITalino from the chest cable with a tiny voltage drop.", "When the cable supply disappears it hands over to the supercaps through Q1."],
    Q1: ["Backup switch AO3401A", "P-MOSFET from the supercap stack.", "Turns on automatically when the main supply fails."],
    SC1: ["Supercap 10 F (top)", "2.7 V, in series with SC2.", "Stores energy to ride through a cable glitch: 17–60 s at 65 mA."],
    SC2: ["Supercap 10 F (bottom)", "2.7 V, in series with SC1.", "Stores energy to ride through a cable glitch."],
    D2: ["Precharge diode B5819W", "Charges the stack from the supply.", "With R2, fills the stack to 90 % in about 7 minutes."],
    R2: ["Precharge resistor 33 Ω", "Limits the precharge current.", "The supercaps never pull a large inrush from the back unit."],
    R3: ["Balancing resistor", "Across SC1.", "Keeps both supercaps at equal voltage."],
    R4: ["Balancing resistor", "Across SC2.", "Keeps both supercaps at equal voltage."],
    D1: ["Surge clamp SMF5.0A", "TVS on the incoming supply.", "Protects the board and BITalino."],
    D3: ["Sync clamp BAT54S", "Clamps the sync line into BITalino input I1.", "The sync pulse can never exceed BITalino's input range."],
    R5: ["Sync resistor 1 kΩ", "In series with the sync line.", "Limits clamp current."],
    J1: ["From back unit", "PH2.0 5-pin.", ""],
    J2: ["To BITalino battery socket", "PH2.0, pin 1 = +.", ""],
    J3: ["Sync to BITalino I1", "Via the UC-E6 adapter.", "Puts power-log time marks into the ECG recording."],
    R1: ["Pull-up 100 kΩ", "On the LM66100 status pin.", ""],
  },
};
export const BOARD_OVERVIEW = { pmbh: ["U1", "L1", "F1", "U4", "U8", "J1", "J2", "J4", "J6"], libb: ["U1", "SC1", "J1", "J3"] };
export const BOARD_LABELS = { pmbh: ["U1", "C15", "Q1", "Q8", "D2", "F1", "L1", "U2", "U4", "U5", "U8", "J1", "J2", "J6", "J4"], libb: ["U1", "SC1", "Q1", "D2", "J1", "J2", "J3"] };

// ---------------------------------------------------------------- simulation: CN3791 board at 3.70 V battery (仿真报告 §3)
// [irradiance W/m², panel power into charger W, battery current mA (after the board's ~8 mA self-use), capture %]
export const SIM = [[0, 0, -8, 0], [10, 0.032, -8, 99.8], [30, 0.110, 19, 91.0], [60, 0.259, 57, 98.5], [120, 0.555, 133, 100.0],
  [200, 0.950, 231, 99.9], [400, 1.941, 471, 99.6], [700, 3.401, 805, 99.9], [1000, 4.735, 1094, 99.8]];
export const SELF_MA = 8, BATT_MAH = 2500;

export const MODES = {
  sun:    { label: "Full sun",     g: 1000, note: "Panel at 55 °C on the back. The charger holds 5.93 V and captures 99.8 % of the panel's maximum." },
  cloud:  { label: "Cloudy",       g: 200,  note: "Diffuse daylight. Still about 0.95 W into the charger." },
  office: { label: "Office light", g: 30,   note: "Indoor light. The charger still starts and adds a few tens of milliamps." },
  night:  { label: "Night",        g: 0,    note: "No light. The MCU opens Q1 through PV_EN, so the battery does not leak back into the panel (51 µA instead of 1.1 mA)." },
  glitch: { label: "Cable pulled", g: 200,  note: "The chest cable is disconnected. The hold-up board keeps BITalino B running on its supercaps for 17–60 s." },
};

// ---------------------------------------------------------------- flow graph (SVG units)
export const FLOW_NODES = {
  sun:    { x: 70,   y: 58,  t: "Light",           s: "sun / room",            kind: "src" },
  panel:  { x: 210,  y: 58,  t: "Solar panel",     s: "6 V · 6 W",             part: "panel" },
  prot:   { x: 350,  y: 58,  t: "Protection",      s: "fuse · polarity · TVS", part: "pmbh", comp: "Q1" },
  mppt:   { x: 490,  y: 58,  t: "MPPT charger",    s: "CN3791 · 5.93 V",       part: "pmbh", comp: "U1" },
  batt:   { x: 630,  y: 58,  t: "Li-Po battery",   s: "2500 mAh",              part: "battery" },
  loadsw: { x: 770,  y: 58,  t: "Load switch",     s: "soft start",            part: "pmbh", comp: "Q5" },
  j6:     { x: 910,  y: 58,  t: "Chest cable",     s: "W06",                   part: "W06" },
  lib:    { x: 1050, y: 58,  t: "Hold-up board",   s: "ideal diode · 2×10 F",  part: "lib" },
  coreb:  { x: 1190, y: 58,  t: "BITalino B",      s: "ECG under test",        part: "core_b" },
  phone:  { x: 1330, y: 118, t: "Phone",           s: "all streams",           part: "phone" },
  refs:   { x: 210,  y: 178, t: "Reference cells", s: "light meters",          part: "ref_cells" },
  ina:    { x: 490,  y: 178, t: "6 × INA226",      s: "power meters",          part: "pmbh", comp: "U4" },
  xiao:   { x: 700,  y: 178, t: "XIAO nRF52840",   s: "logger · control",      part: "xiao" },
  unita:  { x: 910,  y: 178, t: "HeartBIT A",      s: "PPG reference",         part: "unit_a" },
  unitc:  { x: 1050, y: 178, t: "BITalino C",      s: "control unit",          part: "c_board" },
  ecg:    { x: 1190, y: 178, t: "ECG electrodes",  s: "lead I",                part: "ecg_b" },
};
// kind: e = energy, s = signal, d = data (BLE / I²C), c = control
export const FLOW_EDGES = [
  ["sun", "panel", "e"], ["panel", "prot", "e"], ["prot", "mppt", "e"], ["mppt", "batt", "e"], ["batt", "loadsw", "e"],
  ["loadsw", "j6", "e"], ["j6", "lib", "e"], ["lib", "coreb", "e"],
  ["ecg", "coreb", "s"], ["refs", "ina", "s"], ["ina", "xiao", "d"],
  ["coreb", "phone", "d"], ["xiao", "phone", "d"], ["unitc", "phone", "d"], ["unita", "phone", "d"],
  ["xiao", "prot", "c"], ["xiao", "mppt", "c"], ["xiao", "loadsw", "c"], ["xiao", "lib", "c"],
];

// ---------------------------------------------------------------- guided tour
export const TOUR = [
  { title: "A self-powered, solar-harvesting wearable", scene: "worn", view: "iso", mode: "sun", xray: false, explode: 0, labels: true,
    text: "A 6 V panel on the back charges a battery that runs BITalino B, the ECG unit under test. Following the brief, the solar power extends the runtime; it is not presented as removing the need to charge." },
  { title: "The panel rides on the back", scene: "worn", view: "back", mode: "sun", xray: false, explode: 0, labels: true, focus: "panel",
    text: "Six printed shoes hold the panel 18–53 mm off the vest at a 6° tilt. Each shoe's foot angle comes from the body scan, and the air gap keeps hot glass away from the skin." },
  { title: "Inside the back unit", scene: "worn", view: "pod", mode: "sun", xray: true, explode: 0.7, labels: true, focus: "pmbh",
    text: "The back unit holds the PMB-H board, the 2500 mAh battery and the XIAO logger. Click any part to see what it does and which problem it solves." },
  { title: "Where the energy goes", scene: "worn", view: "iso", mode: "sun", xray: true, explode: 0, labels: false, flow: true,
    text: "Light → panel → protection → MPPT charger → battery → load switch → chest cable → hold-up board → BITalino B. At full sun about 4.7 W reaches the charger and the battery takes 1.09 A." },
  { title: "Indoors, the gain shrinks", scene: "worn", view: "iso", mode: "office", xray: true, explode: 0, labels: false, flow: true,
    text: "Under office light the charger still runs and adds about 19 mA. In dim rooms the panel no longer covers the board's own use, which is why the design claims extended runtime, not energy independence." },
  { title: "At night nothing leaks", scene: "worn", view: "pod", mode: "night", xray: true, explode: 0.4, labels: true, focus: "pmbh",
    text: "In the dark the XIAO opens the panel switch through PV_EN. Back-feed into the panel falls from 1.1 mA to 51 µA (simulation)." },
  { title: "A tug on the cable does not reset the ECG", scene: "worn", view: "chest", mode: "glitch", xray: true, explode: 0.5, labels: true, focus: "lib",
    text: "If the chest cable is pulled, the LM66100 ideal diode hands over to two 10 F supercaps. BITalino B keeps recording for 17–60 s, enough to reconnect." },
  { title: "Three units, one phone", scene: "worn", view: "front", mode: "sun", xray: true, explode: 0, labels: true, flow: true,
    text: "B records ECG on solar power. C records the same lead from 50 mm lower on its own battery, as the control. HeartBIT A adds an earlobe PPG reference. All three stream to one phone, together with the power log." },
  { title: "Inside the boards", scene: "boards", view: "boards", mode: "sun", xray: false, explode: 0.5, labels: true,
    text: "Both boards are assembled by JLCPCB. Every placement was checked against the design; both DFM reviews passed with 0 errors. Hover a chip to see its job." },
  { title: "The bench rig", scene: "bench", view: "iso", mode: "sun", xray: false, explode: 0, labels: true,
    text: "Before wearing it: an I-V curve at fixed angles on the printed tilt stand (TC-02), then the runtime-gain test with the panel uncovered vs fully covered (TC-24)." },
  { title: "Status and decisions", scene: "worn", view: "iso", mode: "sun", xray: false, explode: 0, labels: false, finale: true,
    text: "Both boards are being assembled at JLCPCB and ship 16–19 October. 22 / 22 simulation checks pass. 18 printed parts are ready. Three decisions are open: the overall design, shortening the panel cable (or coiling it), and having the vest made by an outside studio." },
];
