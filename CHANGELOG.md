# Changelog

## 2.3.0 — 2026-11-28

Four fixes and one new tool, all of them from flying the thing rather than from reading it. The
bridge is unchanged since 2.2.0: this release is Python only, and an install that already runs the
2.2.0 bridge needs nothing rebuilt.

- **`mj_maneuver` — MechJeb plans the maneuver and flies it, in one call.** The README has always
  said MechJeb does ascent and planning, but no tool joined its planner to its executor, so every
  maneuver in practice went `compute_maneuver` -> `node_create` -> `fly_burn`: ASTRA's own
  arithmetic placing a node it then flew by hand. `mj_maneuver(operation, params, watch, ...)` closes
  that, and reports the three halves that matter — the planned node, the burn that ran
  (`node_changed`, `node_consumed`), and `orbit_check`, the orbit that came out against the one the
  node predicted. A node more than 30 min out comes back with `far_node`: MechJeb orients before it
  warps, so the watch would otherwise expire with the burn never flown.
- **`compute_maneuver` and `compute_hohmann` are documented as estimates.** They were quietly doing
  two jobs while the second one was missing; they now say what they are — the number to hold against
  MechJeb's answer, which is the thing worth reading before a burn. `fly_burn` stays for the case
  where the exact node matters, because `mj_execute_node` re-solves the node it is given.
- **kRPC 0.8.0 compat, five places, after 532 tests passed on a live-ascent crash.** The single
  test suite was green while three tools died in flight, because the fakes implemented the API kRPC
  had deleted: `Parts.in_stage`, `AutoPilot.engage`, `Orbit.distance_at_closest_approach`, and
  `Part.tag` (which 0.8.0 put behind a ModRequirement, so `vessel_parts` returned an error for
  every one of 34 parts). The shims live in `astra.ksp` and route on which API exists;
  `tests/test_krpc_contract.py` asserts against the generated `krpc.ksp.spacecenter` module so the
  next upgrade fails in CI rather than at ignition, and the fakes now only know the 0.8.0 shape.
- **The reflex loop runs at 50 Hz near the ground and in high dynamic pressure:** 20 Hz cannot see
  the last metre of a landing, and a fixed 50 Hz everywhere buys jitter, not precision. The period
  follows the situation (`TICK_FAST_S` within 500 m of the surface, or above 20 kPa), with
  hysteresis so it does not oscillate. A taker-off is not "near the ground": an early version
  spent the first 38 s of an ascent at 50 Hz because altitude alone said so.
- **`ASTRA_STOP_FILE` cancels a running reflex** (default `.cache/STOP`): a tool call that holds the
  service for minutes cannot be reached by another client, and kRPC's single connection is not
  thread-safe, so a file the loop checks each tick is the only way to stop one from outside. The run
  ends with `stopped_by.kind == "cancel"`.
- **`ASTRA_PAUSE_STYLE` says which pause you get** (`silent` default, `menu`, `none`). A silent pause
  is invisible in the game and ESC does nothing in it, so an AI that paused and died left a game
  that looked frozen; a menu pause covers the view. Both are now named choices, and `set_paused`
  falls back to the other path when one fails — kRPC's `paused=False` is `PauseMenu.Close()`, which
  throws a NullReferenceException when no menu is open.
- **`hohmann_to_body` solves an eccentric parking orbit instead of refusing it:** the old model
  assumed the burn lands half an orbit later, which is false when the parking orbit is eccentric.
  It now solves for the real swept angle and the arrival point, and the synodic period uses mean
  motion (the instantaneous rate gave 71,888 s where the truth was 113,857 s).
- **A node that KSP moves or deletes during a coast is noticed:** `fly_burn` re-reads the node at
  ignition, aims at the node that is there now (reporting `node_moved`), gives up with a named
  `node_set(ut=...)` fix when the window has already closed, and returns `not burned` if the node is
  gone. A node 3,793 s past its start used to burn anyway.
- **`node_set`** edits one component of a node in place: a long coast plus one apsis in the wrong
  place no longer means deleting and retyping the whole plan.
- **`verify_orbit`** checks the orbit against the numbers you asked for (`ok`, per-check delta and
  tolerance), so "did the burn do what I wanted" is a field in the reply.
- **MechJeb's own numbers are read back:** `mj_ascent` reports `apoapsis_check` (80 km requested and
  546 km produced, once, with nothing in the reply to show it), `settings_check` (the settings
  MechJeb says it is running against the ones sent), `stays_armed`, and `mj_status` reports
  `still_flying` — MechJeb commands the vessel until it reaches its target orbit, and a burn flown
  under it is not yours.

## 2.2.0 — 2026-11-28

- **`hohmann_to_body` refuses an eccentric parking orbit:** above e=0.05 the tool now raises instead
  of answering, because the model assumes a near-circular orbit. The burn it used to recommend for
  a 100 km × 11,406 km orbit came out at +2.6 m/s and went nowhere, and nothing in the result said
  the answer was meaningless. The hint points at `compute_node_search` with an `encounter_body`
  objective, which does solve that case. Between e=0.01 and e=0.05 the answer still comes back with
  an `eccentricity` note.
- **A plan id ties a burn to the computation that chose it:** `compute_maneuver` and
  `compute_node_search` return a `plan` id, and `node_create`/`fly_burn` take it as `plan=`. The node
  is compared against the plan **at ignition** — a node edited during a long coast, or a digit typed
  by hand, refuses to burn instead of quietly going somewhere else. Tolerances are 0.05 m/s and 1 s,
  and recomputing the same plan yields the same id. Calls without `plan=` behave as before. `node_create`
  validates before adding the node, so a refused call leaves nothing behind.
- **`compute_descent` can fill itself in:** `from_telemetry=True` reads altitude, vertical and
  horizontal speed, mass and thrust off the live vessel instead of making the caller copy five
  numbers that go stale. Explicit arguments still win, and the result echoes every input with
  `inputs.sources` saying which came from where. A telemetry pass that cannot supply all five
  refuses to compute rather than guessing a mass.
- **`cut`/`off`/`zero` are understood as throttle specs:** `fly_until(throttle="cut")` died with
  `cannot read throttle spec 'cut'` in two logged missions; they now mean 0, the same as the number.
- **`astra tools --json`:** prints the catalog as JSON — name, group, summary and every parameter
  with its type, required flag, default and description — for pasting a tool surface into another
  model. `-n/--name` shows one tool.
- **The approach law shuts down when its metric disappears:** a null or NaN metric used to return
  full throttle, which is burning blind with nothing to aim at. It now cuts the throttle and says
  so in `done()`. An infinite metric (apoapsis while still escaping) still burns, since that is the
  side the capture is approaching from.
- **`node_create_args` on compute results:** `compute_maneuver` and `compute_node_search` also return
  the four numbers `node_create` takes, in that exact shape, so they pass through without being
  retyped. The plan id catches a wrong burn at ignition; not copying four floats by hand is what
  keeps it from going wrong in the first place.

## 2.1.0 — 2026-11-28

- **kRPC 0.8.0 (protocol v2):** the mod, the Python client and the pinned dependency move to 0.8.0
  together. Protocol v2 gives each client a single connection, so `rpc_port`/`stream_port` collapse
  into one `port` and `ASTRA_KRPC_STREAM_PORT` is gone; `krpc.current_game_scene` became
  `krpc.game_scene` (same `str(...).split(".")[-1]` mapping). Streams are unchanged in use:
  `add_stream(getattr, obj, name)` and reference-frame method streams (`v.position, ref`) both work.
  kRPC dropped `Vessel.switch_to`; vessel switching already went through the bridge, so nothing
  else moved. Verified in flight on 探月2号 with `game_status`, `telemetry` and live streams.
- **Landing gear is now checked before flight:** `design_check` reports the tip-over angle (the leg
  foot ring against the centre-of-mass height, measured on the stowed leg boxes), an engine bell that
  ends below the feet, and a hatch that opens onto a tank top or onto a heat shield. Those are the
  three ways the flown Mun landers went over after a landing the guidance had already made gentle.
  Checked on `tests/fixtures/parts_subset.json` by `test_design_check_lander_geometry`.
- **README default language is Chinese:** `README.md` is now the Chinese text and the English one
  moved to `README.en.md`, so the GitHub front page opens in Chinese. The two files link to each
  other, and `pyproject.toml` points the package metadata at `README.en.md`.
- **Three showcase GIFs removed:** `mun_landing.gif`, `duna_landing.gif` and `launch.gif` (9.3 MB)
  sat in `docs/media/` with nothing referencing them; the footage lives in the video.
- **README rewrite:** the README adds a hero banner, a loop diagram, a video thumbnail, and a
  call-by-call excerpt of the Duna landing log. Every figure was re-checked against the flight logs.
  Two corrections: Duna took 377
  Kerbin days from launch to touchdown (329 was the planned transfer), and only the 0.86 and
  0.03 m/s Mun landings used the new predictor guidance. `scripts/showcase/readme_art.py` renders
  the artwork.
- **English showcase video (YouTube):** `make_video.py --lang en` builds the English cut from the
  same footage. It uses the narration in `storyboard.en.json` and adds English cards, HUD,
  thumbnail and chapters. Subtitles are timed word by word. The Chinese cut is unchanged, and
  `docs/video/YOUTUBE.md` has the upload notes.

## v2.0.0: the AI is the crew (2026-09-30)

A ground-up rewrite. The previous design had the AI write fixed mission programs. ASTRA 2 turns the
running game into tools, and the AI flies every mission itself as astronaut and mission control:
observe, compute, decide, act, verify. The repository contains no mission scripts.

### Flown in the game

- **Kerbin orbit and return:** the crew designed *ASTRA Orbiter 2* from the live part catalog,
  diagnosed a loss of control (nothing gimbaled), redesigned it, reached 80.3 × 79.6 km, and
  splashed down at 3.9 m/s.
- **Autonomous crew:** `astra mission` flew the same goal unattended with only the ASTRA tools and
  recovered Valentina.
- **Mun landing and return:** MechJeb ascent and trans-Mun injection, `fly_descent` landing, EVA,
  flag "ASTRA Mun Base", return and splashdown.
- **Duna (Mars) landing:** a Lambert window, two mid-course corrections, a 713 m/s capture with
  auto-staging, aerobraking, three parachutes and a powered touchdown at 1.22 m/s. EVA by jetpack hop,
  flag "ASTRA Duna Base".

Logs, journals and transcripts are in `docs/missions/`.

### New

- **74 MCP tools in 9 groups:** observe, compute, design, game, control, fly, autopilot, crew,
  journal. Tool reference: `docs/TOOLS.md`.
- **Stop-the-world deliberation:** the game pauses whenever a tool returns. Game time advances only
  inside reflexes (`fly_until`, `fly_burn`, `fly_warp`, `fly_descent`, MechJeb watches, crew
  actions), which run until the AI's triggers fire or a safety interlock trips.
- **Rocket design from the live part catalog:** part trees with real attach nodes, a staging and
  stage simulator, `.craft` output, and design checks for steering authority and power.
- **`fly_descent` powered landing:** a numerically integrated suicide-burn predictor with
  centrifugal relief, terrain look-ahead with peak memory, and height-first braking when retrograde
  thrust cannot hold the gate. The terminal phase hands over on speed and drift, hovers to cancel
  drift, and SAS settles the lander after touchdown. An offline closed-loop simulator and adversarial
  scenarios cover it.
- **MechJeb autopilot tools:** ascent, node executor, landing, rendezvous, docking, planner, status
  and abort. Every setting is explicit and watched with interlocks.
- **Crew tools:** EVA, walk-to (fixed steering), EVA jetpack hop (`crew_hop`,
  `crew_eva(hop_clear_m)`), flags verified through the bridge, and boarding. Where the pack cannot
  lift a kerbal off the ground (Duna gives about 0.94 g), a hop glides out from the hatch instead.
- **Filming:** `astra record` and `astra mission --record`. The bridge renders the cameras
  off-screen with asynchronous readback into ffmpeg (H.264) and records only while game time runs. It
  marks every tool call except the read-only instruments and logs telemetry per frame, and a camera director frames each phase. The
  showcase video builder is `scripts/showcase/`.
- **KspAutomationBridge 2.1.0:**
  - scene and save control from the main menu, and a full part database with geometry
  - EVA walking, hops, flags and boarding; MechJeb; the CAPCOM panel
  - pause without the ESC menu, screenshots, and the video recorder
- **Autonomous crew:** an agent crew with only the ASTRA tools, `--resume` and `--record`.
- **Knowledge:** the crew doctrine, 11 physics playbooks, and a lessons file that the crew searches
  and extends in flight.

### Fixed during live flights

- Attitude read from the surface frame, `Resources.density` called statically, the thrust-axis
  sign, late burns refused after `max_late_s`, and the throttle settled before pausing.
- The impact interlock is chute-aware, and `game_restore` returns to the checkpoint's scene.
- A broken part bounding box (the Mk1 pod reports ±6×10¹⁷ m) made the descent hover at 13 km.
  Vessel boxes are now built from sane per-part boxes.
- The overheat interlock compared skin temperature against the internal limit.
- kRPC's vessel list omits EVA kerbals and flags, so EVA and flag checks now use the bridge.
- Rails warp is allowed on the ground. Checkpoints and restores let physics settle around vessel
  switches and loads.

### Requirements

KSP 1.12.5, kRPC 0.8.0, MechJeb2, ModuleManager, Harmony, Python 3.11+. Optional extra:
`media` (imageio-ffmpeg for recording).
