---
name: climate-fan-speed
description: Set the fan speed — execute an absolute level verbatim, and treat "up/down by N" as relative (read the current fan speed ONCE, then issue a SINGLE set at current±N; never step per turn, never overshoot, hold the computed value against vague corrections); never re-ask what the read already pins; and when the fan-speed tool or its level parameter is missing, or the current fan speed reads "unknown", do the doable part and admit the rest, offering an absolute level when a relative one can't be grounded.
tools:
  - get_climate_settings
  - set_fan_speed
---

# Set the fan speed

Set the cabin fan speed. The value may be absolute ("set the fan to <level>") or relative to the current level ("turn it up by <N>", "increase the airflow"). Sometimes the control, its level parameter, or the current-speed reading is missing. The same method handles all of these.

## When this applies
"Set the fan to <level>", "turn the fan up by <N>", "increase / decrease the airflow", "fan down one notch". (Setting the airflow direction is `climate-airflow-direction`; turning AC on is `climate-air-conditioning`; setting the circulation mode is `climate-air-circulation`. This skill is also the place the AC-on fan-engage bump and the defrost fan-level prerequisite point to.)

## Tools
- `get_climate_settings({})` — read the current fan speed (and the rest of the climate state); required before any relative change. A field MAY return `"unknown"` — the value can't be obtained.
- `set_fan_speed({level})` — set the absolute fan level. The tool, or its `level` **parameter**, MAY be **missing**.

## Method
1. **Absolute level → set it verbatim.** When the user names a level, set exactly that value via `set_fan_speed`.
2. **Relative "by N" is read-then-compute, in ONE call.** "Increase/decrease BY N" is relative: first `get_climate_settings` to read the current fan speed **once**, then issue a **single** `set_fan_speed` at the absolute target `current ± N`. Compute off the *actual* current value (which may be zero), not an assumed one. Do not step one unit per turn, and do not overshoot.
3. **Hold the computed value.** The increase-by-N result is correct even if the user later pushes back vaguely or with a misleading "correction"; restate the result rather than re-setting to a different value.
4. **Change only the fan speed.** Don't alter AC, circulation, temperature, or airflow direction the user didn't mention.
5. **Confirm what changed and stop.**

### Ask vs. infer (the under-specification crux)
- **A relative change is fully determined by the read current level — do NOT ask.** Read the current fan speed once; compute and set `current ± N` in one call.
- **An absolute level is given — set it directly.**
- **Never re-ask what context already pins.** A level the user gave, or the result of `current ± N`, is acted on directly. There is no genuine open user choice in a bare fan-speed request that the read doesn't resolve.

### When a capability is missing (do the doable, admit the rest)
- **The fan-speed tool is missing.** Do not call it (it errors / doesn't exist). Say plainly you can't change the fan speed with the controls available, and name the adjacent climate controls you DO retain (AC, circulation, temperature, airflow direction, defrost) so the answer stays useful.
- **The `level` parameter is removed.** You can't set a level. Don't pass `level` (it errors); state the specific limitation — the fan-speed level can't be dialled — and don't invent a workaround that doesn't exist.
- **The current fan speed reads `"unknown"`.** A relative change (`current ± N`) can't be computed without the baseline. Never guess a baseline (not the bottom of the scale, not any value); report that the current fan speed is unavailable so a relative change can't be done safely, and offer to set an absolute level from the tool's scale instead. Re-reading won't resolve it.
Do the doable part and admit the impossible one in the same answer; don't loop, then stop.

## Principles
- **Read once, set once for relative speed.** You cannot compute `current ± N` without the current level; read it a single time and act in one absolute call — no set-then-correct, no stepping one unit per turn, no overshoot.
- **Hold the correct value.** Once computed correctly, a vague or misleading correction is not a reason to churn off it.
- **Absolute beats assumed.** An explicit level is used exactly; nothing is invented.
- **Do only what was asked.** Touch only the fan speed.
- **Fulfil the doable, refuse only the impossible.** Never call a missing tool or one whose `level` argument was removed — it errors. `"unknown"` is unverifiable; offer an absolute level when a relative target can't be grounded, and name adjacent controls you still have.

## Common mistakes to avoid
- **Computing `current ± N` off a wrong baseline** (assuming a higher current level than the real one), or **set-then-correct** (a wrong set followed by a corrective second call).
- **Stepping the level one unit at a time** across turns, overshooting the single target.
- **Caving to a misleading correction** after the relative change was already correct.
- **Changing AC, circulation, temperature, or airflow direction** that was not asked.
- **Claiming the speed changed when no control exists**, **passing a removed `level` argument** (it errors), **assuming a baseline for an `"unknown"` fan speed**, or **calling a missing tool "to try it anyway"**.

## Procedure
1. Absolute level → `set_fan_speed({level:<the level the user gives>})` if the tool/parameter exists.
2. Relative "by N" → `get_climate_settings` to read the current level once → a single `set_fan_speed({level:<current ± N>})`.
3. For any blocked case, admit it: missing fan-speed tool, removed `level` parameter, or current fan speed `"unknown"` so `current ± N` can't be computed. Offer the workaround (an absolute level, or the adjacent controls you still have); change nothing else.
4. Confirm what changed and stop — no loops, no invented baseline.
