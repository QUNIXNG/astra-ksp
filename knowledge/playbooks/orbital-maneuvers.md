# Orbital maneuvers: changing an orbit you are already in

Keywords: orbit, orbit change, circularize, circularization, apoapsis, periapsis, apsis change, hohmann, bi-elliptic, plane change, inclination, phasing, maneuver node, node, burn, finite burn, burn time, lead time, estimate, fly_burn, mj_maneuver, mj_execute_node, feather

## 1. The relations to compute with

- Vis-viva: v = √(μ(2/r − 1/a)), a = (r_ap + r_pe)/2 (radii from the body's centre = altitude + R).
  `compute_orbit` evaluates speeds, period, and SMA for any apsides.
- A burn changes the orbit on the **opposite** side. Prograde at periapsis raises the apoapsis;
  retrograde at apoapsis lowers the periapsis. The Δv to move the opposite apsis from r_old to r_new
  while burning at radius r: Δv = v(r, a_new) − v(r, a_old).
- **Circularize at an apsis r:** Δv = √(μ/r) − v(r, a). `compute_maneuver(kind="circularize")`.
- **Hohmann between circles r1 → r2:** Δv1 = v(r1, a_t) − √(μ/r1), Δv2 = √(μ/r2) − v(r2, a_t),
  a_t = (r1 + r2)/2, transfer time π√(a_t³/μ). `compute_hohmann`. For r2/r1 above ≈ 11.9 a
  bi-elliptic transfer is cheaper in Δv (and much slower).
- **Plane change** by Δi at speed v: Δv = 2·v·sin(Δi/2), along the orbit normal (normal or
  antinormal), at the ascending or descending node relative to the plane you want. It is cheapest
  where v is smallest (near apoapsis); combine it with another burn there when you can. The burn
  direction is the orbit normal at the node, not the difference of the two planes' normal vectors
  (that vector points nearly along the velocity for small angles, a bug that cost the old code).
  `compute_maneuver(kind="plane_change")`.
- **Period** T = 2π√(a³/μ); **phasing**: to catch up with a target that leads you by an angle θ on
  the same orbit (period T) after k revolutions of your own, fly an orbit with period
  T_ph = T·(1 − θ/(2πk)); to let a target that trails you by θ catch up, T_ph = T·(1 + θ/(2πk))
  (shorter = lower, to gain; longer = higher, to fall back). Then return to the original orbit.
- `compute_calc` for anything not covered, with the formula written out.

## 2. Finite burns

A node is an instantaneous impulse; a real burn takes time.

- Burn time: t_b = (m0·ve/F)(1 − e^(−Δv/ve)), ve = Isp·g0. Start the burn so that half the Δv is
  delivered by the node time: t_half = (m0·ve/F)(1 − e^(−Δv/(2ve))), which is slightly more than
  t_b/2 because the vehicle gets lighter. `compute_rocket` computes both from live mass, thrust, Isp.
- A burn long compared with the time spent near the apsis (a sizeable fraction of the orbital period)
  loses efficiency and lands off target. Split it (e.g. raise the apoapsis over several periapsis
  passes) or accept and correct afterwards.
- Pointing: the autopilot aims the **control part**, not the engines. If the control part is not
  aligned with the thrust axis, a "prograde" burn goes somewhere else. `fly_burn` refuses when the
  offset is large; fix it with `control_part` (control_from) on a part aligned with the engines.
- Align before ignition and burn at full throttle for large burns (a slow, throttled-down ejection lost
  its fuel to gravity loss). Feather at the end: throttle down once the remaining Δv is a couple of
  seconds of full acceleration, so the cut-off does not overshoot. Choose `feather_s`,
  `min_throttle`, and `tolerance_mps` from the stage's acceleration F/m: a high-thrust stage doing a
  small correction needs a low `max_throttle` so the burn lasts long enough to control.
- When precision matters more than the node's Δv (an encounter periapsis, a capture apoapsis), stop on
  the outcome: `fly_burn(stop_when=[{"metric": "next_periapsis_altitude", "op": "<=", "value": ...}])`
  or fly the burn with `fly_until` and an `approach` throttle law on the orbital element.

## 3. The routine

MechJeb flies the maneuver by default (`mj_maneuver`); what you compute is the estimate you check it
against. Two numbers that disagree are worth more than one you trust.

1. Read the orbit (`orbit_info`), mass and thrust of the burning stage (`vessel_stages`).
2. Estimate the move: `compute_maneuver`, `compute_hohmann`, or `compute_node_search` when the result
   depends on patched conics. That is the Δv and burn time you expect to see, not the plan that flies.
3. Journal the decision: expected Δv, expected orbit, abort condition.
4. `mj_maneuver(operation, params, watch=true, max_game_s=...)` — MechJeb's planner places the node and
   its executor flies it; the reply carries the planned node, the burn that ran, and `orbit_check`
   (the orbit that came out against the one the node predicted). Dry-run the plan first with
   `mj_plan(place=false)` when you want to see MechJeb's numbers before anything is placed.
5. Verify and read the residual: `orbit_check` in the reply, then `verify_orbit` against the target
   you actually wanted. If the error matters, correct it with another `mj_maneuver`; if it is large,
   find out why before the next big burn.

When to fly the node yourself instead: `mj_execute_node` re-plans the node with its own solver, so the
number that gets burned is not necessarily the node you placed (the reply names the difference in
`node_changed`). If an exact node matters — an encounter periapsis, a capture apoapsis, a target
inclination — place the node from `compute_*` and fly it with `fly_burn`, which reports the applied Δv
integrated over game time. Evidence from earlier flights: MechJeb's executor drifted ~2° off-axis on a
long burn under game lag (a big out-of-plane error at Duna) and once skipped a node a few minutes
away, while ASTRA's executor once botched a tiny normal-heavy correction that MechJeb flew well.
Whichever you use, verify the orbit afterwards.

## What goes wrong, and how it shows

| Telemetry | Meaning | Response |
|---|---|---|
| Throttle up but thrust 0 for a few seconds right after a warp | KSP's thrust readout lags after rails warp | confirm with orbit change (SMA, apsides) or g-force before aborting |
| Thrust 0 and nothing changing | still in rails warp, engine not active, starved | stop warp, check engines (`vessel_parts`), stage or fix feed |
| A prograde burn lowers the apoapsis | pointing wrong: misaligned start or control part not along thrust | cut, re-align (check the control point), resume gently; never flip the burn vector |
| Remaining Δv grows during the burn | burning the wrong way | cut immediately |
| Burn ends short, engine out | stage empty: propellant sits in the next stage | stage into the fuelled stage and continue (decide, then act) |
| Periapsis dropping toward the atmosphere during a correction | the correction has a retrograde/radial-in part you did not intend | stop and re-plan with a periapsis constraint |

## Sanity checks (not targets)

- Kerbin 80 km circular ≈ 2,279 m/s, period ≈ 31 min. A 1° plane change there ≈ 40 m/s; 10° ≈ 400 m/s.
- Circularizing from a ballistic arc whose apoapsis is at 80 km with a periapsis deep inside the
  atmosphere typically needs several hundred m/s; if a plan says far more or far less, recheck it.
