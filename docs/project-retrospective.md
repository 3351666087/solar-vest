# Project Retrospective: From Zero to Now

2026-10-18

Project: solar self-powered wearable device (assigned by the supervisor)

---

## 0. One-paragraph summary

On 7 September I received the supervisor's requirements email. Over the following ~6 weeks, with the help of AI (Claude), a "solar-powered ECG vest worn on the body" went from requirements to production:

- two custom circuit boards are in production at JLCPCB;
- the second revision of the 18 types of 3D-printed parts is out;
- the 10 vest pattern pieces are complete;
- 20 cables are defined down to each pin;
- the remaining components are in a JD.com shopping cart, awaiting checkout;
- an interactive 3D web page was built for the supervisor.

Division of labour: I set the direction, provide physical-object information, make decisions, pay, and do acceptance; the AI researches, produces the designs, generates files with code, and runs numerical verification.

The biggest gap right now is that not a single board has been powered up yet. Next step: write the firmware, then do bench bring-up.

---

## 1. Timeline

| Date | What happened | Result / output |
|---|---|---|
| 9/7 | The supervisor sent the requirements email "Project Info": a panel mounted on a wearable device, charging a 3.7 V Li-ion battery through MPPT, to power low-power BLE sensors | The sole basis for the research goal |
| 9/15 | Panel changed from the 5–6 V small flexible panel in the email to an 18 V 30 W rigid panel | First change of direction |
| 9/23 | Panel fixed as a 6 V 6 W rigid panel; confirmed that the first email defines the research goal | The EVK10941 on hand has a 5 V input limit and cannot take this panel, so the plan switched to a custom charger board |
| Early Oct | Photogrammetry from a video shot by my roommate, reconstructing my body shape | Parametric torso model (published with the repository with my consent) |
| 10/8 | Based on the 6 photos of the boards I sent, the roles of the three BITalinos were fixed (A = HeartBIT Core BT, B = Core BLE, C = Board Kit). Toolchain chosen: KiCad + SKiDL, JLCPCB assembly. Emailed PLUX asking for the Core STEP | v3.1 plan. Rule established: "only do what I must do" |
| 10/11 | First complete set of drawings for the whole system | PMB-H and LIB boards (ERC/DRC pass), 13 printed parts, 10 vest pattern pieces, panel layout |
| 10/12 | I felt it was "not detailed enough, not complete", so a second round:<br>• line-by-line reconciliation against the component list<br>• all three BITalinos worn on the body<br>• 20 cables detailed down to pins<br>• safety design added<br>In parallel, ngspice circuit simulation | Simulation found three problems:<br>• a missing input electrolytic capacitor, loop unstable<br>• night-time back-feed<br>• INA226 input out of range<br>The PCBs were modified and re-routed as a result |
| 10/13 | Ordered and paid at JLCPCB. I pressed "are you sure it's all fine?", which uncovered 25 parts with wrong placement orientation; cancelled and re-ordered (net extra cost ¥0). Sent the plan and 3D package to the supervisor, asking for approval on three items | Both SMT orders re-placed. The supervisor scheduled an in-person meeting for 10/16 |
| 10/14 | All 78 SMT designators on PMB-H checked one by one; I clicked the final confirmation | Both boards in production (LIB ships ~10/16, PMB-H ~10/19) |
| 10/15 | Built the interactive 3D web page Solar Vest Explorer for the meeting: exploded view, X-ray, guided-tour mode | Web page v1; fixed flickering in Edge |
| 10/16 | I raised issue after issue:<br>• not realistic enough<br>• boards don't look like the real ones<br>• HeartBIT colour scheme wrong<br>• the clip was made up<br>• C board layout changed without asking<br>• "don't fob me off"<br>Morning in the supervisor's office; the web package was sent to the supervisor. Afternoon: chose components on JD.com and added them to the cart | Numerical verification added: all 17 cable plugs matched one by one, 0 % enclosure interpenetration, every socket cut-out checked individually. 15 items added to the cart, about ¥226 |
| 10/16–17 | The supervisor asked to hold off on the vest and first verify the circuit on the bench. The web page gained the REF2 cell and the 22 screws | Direction changed to "bench bring-up first, vest later" |
| 10/17 | I pointed out the boards would rattle around inside the pods and asked for changes based on the components just bought and official dimensions | Printed parts v2, 8 parts changed, free play reduced from up to 14 mm to ≤ 0.4 mm. Dimensions now follow the official PLUX manual |
| 10/18 | Retrospective | This document |

---

## 2. How we worked together

### 2.1 Division of labour

| Me (project lead) | AI (Claude) |
|---|---|
| Set direction, make decisions, relay the supervisor's decisions | Research; produce all circuit, mechanical, vest and harness designs |
| Provide physical-object information: photos, component list, scan video, HeartBIT kit | Generate files with code (CAD, PCB, patterns, harness) and write verification scripts |
| Pay, log in, click irreversible buttons (DFM confirmation, checkout) | Prepare orders, check every placement orientation, select parts and add them to the cart |
| Acceptance: pressing "really?", "you changed it on your own again" | Answer with numbers and control experiments; admit mistakes and fix them |
| Communicate with the supervisor in person | Produce communication material: 3D web page, email drafts, checklists, PDFs |

### 2.2 A typical iteration

1. The AI delivers a version.
2. I spot a problem on the physical object or the page (often one the AI did not catch itself).
3. The AI fixes it and adds a numerical check that automatically catches the same class of problem.
4. The lesson is written into long-term memory and becomes a rule from then on.

---

## 3. Working rules and where they came from

| Rule | Origin |
|---|---|
| Leave me only the work that only I can do: check official documents and photos first, don't make me measure repeatedly with calipers, absorb measurement error with ≥ 1 mm design margin | 10/8, my words: "I only want to do the work I have to do" |
| Check item by item before paying: verify pin 1 of every polarised part on JLCPCB's original placement image; report checked and unchecked items separately; never say "it's fine" while anything is unchecked | 10/13, 25 placement-orientation errors that only surfaced when I pressed after payment |
| Speak with numbers, no fobbing off: every conclusion needs a verification script and a control experiment, e.g. "deliberately push 1 mm into a wall and confirm it is detected" | 10/16, "strengthen the verification, don't fob me off" |
| Follow the physical objects and official documentation; no improvising | 10/16, the AI made up a clip and changed the C board layout without asking; 10/17, "there are official parameters, stop scanning my photos over and over" |
| Bottom lines:<br>• whether body-scan data is published is my decision<br>• the project is not called "wireless power transfer"<br>• I make the payments<br>• emails are sent only with my consent<br>• cutting the panel lead needs the supervisor's consent | Set from the start of the project and followed throughout |

---

## 4. Mistakes and lessons

| Problem | Found by | Fix | Practice since |
|---|---|---|---|
| Placement orientations derived by applying rules to footprint names; 25 were wrong | Me (pressing after payment) | Compared pads one by one, cancelled and re-ordered | Check the original placement image item by item before paying |
| Web page flashing black blocks in Edge | Me | Removed frosted-glass and similar effects, fixed NaN pixels | Added a #nan debug mode |
| HeartBIT drawn all red, and a belt clip made up | Me (comparing with photos) | Changed to a white box with a red lid; the clip is just the snap on the lid | Follow the real object, no improvising |
| C board layout changed by the AI according to its own rules | Me | Rebuilt position by position from photos (rotated 180°) | Follow the real object, no improvising |
| Cable plugs did not line up with sockets | Me ("where do all the cables actually go?") | Automatic check of all 17 cables, one by one | Re-run the checks after every change |
| Printed parts not updated to match the components actually bought; boards would rattle | Me | 8 parts changed, play reduced from 14 mm to ≤ 0.4 mm | Once purchases are settled, immediately go back and check the structural parts |
| JD.com search rate-limited | — | Switched to one query every 10 minutes, adding to the cart slowly | Never bypass the platform's anti-abuse controls |

---

## 5. Toolchain (all code, run from the command line)

| Stage | Tools |
|---|---|
| Printed parts | build123d (Python parametric CAD, OpenCascade kernel) → STEP / STL / 3MF |
| Meshes, interference, assembly | trimesh, manifold3d |
| Body and vest | Photogrammetry → parametric torso model; shapely 2D patterns → 3D |
| PCB | KiCad 10 + SKiDL; pcbnew scripting for placement; kicad-cli for ERC/DRC/Gerbers; easyeda2kicad to fetch footprints; custom scripts to generate the JLCPCB BOM/CPL and check orientations |
| Circuit simulation | ngspice (via the libngspice bundled with KiCad) |
| Demo web page | three.js + esbuild; gltf-transform + meshoptimizer for model compression; three-mesh-bvh for verification |

SolidWorks was not used: it does not run natively on the Mac, and its automation interface is not suited to being driven by AI. All files are exported as standard STEP, which SolidWorks opens without problems.

---

## 6. Where the outputs are (paths relative to the repository root)

| Content | Location |
|---|---|
| Build and assembly steps | `docs/build-and-assembly-guide.md` |
| BOM cross-reference, on-body positions, safety | `docs/bom-and-system-overview.md` |
| PCBs (KiCad projects, Gerbers, BOM, CPL, final placement images) | `hardware/pcb/pmbh/`, `hardware/pcb/libb/` |
| 3D-printed parts v2 (18 types, 21 pieces, with README) | `hardware/enclosures/`, packaged as `SolarVest_3DPrint.zip` (available for download from the GitHub Release) |
| Vest patterns (DXF, 1:1 PDF, A4 tiled) | `hardware/vest/` |
| Wiring table, cable lengths, system wiring diagram | `hardware/wiring/` |
| Circuit simulation report | `simulation/simulation-report.md` |
| Interactive 3D web page (double-click index.html to open) | `explorer/`, already sent to the supervisor |
| Tailor / sampling-studio survey | `docs/tailoring/tailor-survey.md` |
| Official manual (basis for BITalino dimensions) | [PLUX user manual](https://support.pluxbiosignals.com/wp-content/uploads/2021/11/bitalino-revolution-user-manual.pdf) (not redistributed with the repository for copyright reasons) |
| All source code, verification scripts and reports | `tools/cad/` |

---

## 7. Status and next steps

**Status**

- Both PCBs are at JLCPCB: LIB expected to ship 10/16, PMB-H expected 10/19 (see the order page's tracking for the actual dates).
- The JD.com cart holds 15 items (about ¥226), awaiting my checkout.
- Printed parts v2 are drawn and ready to print.
- The supervisor asked for bench bring-up first; the vest is on hold.

**Next steps**

1. Check out the JD.com order. On delivery: solder a PH2.0 plug onto the battery (2 joints), solder headers onto the XIAO (14 joints), and confirm the battery has a protection board.
2. Print the pods and install PMB-H, LIB, Core B and the Board Kit.
3. Write the XIAO firmware (critical path): PV_EN switching, 6-channel INA226 acquisition, NTC temperature protection, BLE reporting.
4. Bench bring-up. First agree acceptance criteria in writing with the supervisor, for example:
   - the panel can charge the battery;
   - night-time back-feed < 0.1 mA;
   - B and C both stream ECG to the phone simultaneously for 30 minutes continuously;
   - INA226 readings within 5 % of the multimeter.
5. Once bring-up passes, get the supervisor's written approval, then outsource the vest.

---

## 8. Candid assessment

**What went well**

- One person, in about 6 weeks, covered the workload of a small team.
- Most critical errors were stopped by numerical verification before money was spent or hands got busy, e.g. the stability problem found in simulation and the orientation check before payment.
- The communication material for the supervisor was intuitive and effective.

**What needs work**

- The design ran too far ahead of the hardware. Not a single board has been powered up, and many key numbers are still estimates: the panel's open-circuit voltage, BITalino power consumption, the CN3791 transconductance.
- Many problems surfaced because I pressed, not because the AI found them itself. Acceptance depends on me; at the bench stage, it will depend on the multimeter and the oscilloscope.
- I need to fully understand three things myself to debug and defend the work: the power path, the LIB switch-over logic, and the firmware state machine.
