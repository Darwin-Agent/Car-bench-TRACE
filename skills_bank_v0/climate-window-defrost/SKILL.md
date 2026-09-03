---
name: climate-window-defrost
description: Turn the front or rear window defrost on/off — defrost the EXACT named window (ask which when it's unstated, a genuine open choice); NAME the hard prerequisite that the fan must be at a required level (the full method lives in climate-fan-speed) and if the fan-speed control is missing the prerequisite can't be met so defrost is blocked — do not call the defrost setter, name the exact blocker; do not absorb the airflow/AC/window-close routine (separate skills); and when a window position reads "unknown", treat it as unverifiable and do the doable part.
tools:
  - get_climate_settings
  - get_vehicle_window_positions
  - get_user_preferences
  - set_window_defrost
  - set_fan_speed
---

# Turn the window defrost on or off

Turn defrost on (or off) for a target window — front or rear. Defrost activation has a hard prerequisite: the fan must be at a required level so air moves over the glass. Sometimes the target window is unstated, the fan-speed control is missing, or a window position can't be read. The same method handles all of these.

## When this applies
"Turn on the front / rear defrost", "defrost the windshield", "clear the rear window", "turn the defrost off". (Setting fan speed is `climate-fan-speed`; setting airflow direction is `climate-airflow-direction`; turning AC on is `climate-air-conditioning`; closing windows is `windows-open-and-position`. Clearing fog is commonly done alongside those via their own skills — this skill owns only the defrost toggle and its fan prerequisite.)

## Tools
- `get_climate_settings({})` — read the current fan / AC / defrost state; use it to learn whether the fan is at the required level for the defrost prerequisite.
- `get_vehicle_window_positions({})` — read window positions if a request touches them. A position field MAY return `"unknown"` — genuinely unverifiable, not a value.
- `get_user_preferences({})` — read a preference if the request points to one.
- `set_window_defrost({defrost_window, on})` — turn defrost on/off for a target; the vocabulary distinguishes front vs rear. Defrost exactly the window named. Activation has a policy prerequisite: the fan must be at a required level.
- `set_fan_speed({level})` — set the absolute fan level, used here ONLY to satisfy (or to name) the defrost fan-level prerequisite. The tool, or its level parameter, MAY be **missing** — the full fan-speed method lives in `climate-fan-speed`.

## Method
1. **Read state first.** Call `get_climate_settings` to learn the current fan level (and defrost state) before activating defrost. Report real values, never invented ones.
2. **Defrost the exact window named.** Turn on the defrost target the user identifies — front vs rear. Do not default to the other target or to both.
3. **Satisfy the fan-level prerequisite.** Defrost activation requires the fan at a required level; if the current level is below it, raise the fan via `set_fan_speed` first (the full method is in `climate-fan-speed`), then activate defrost.
4. **Do NOT absorb the wider fogging routine.** Setting airflow direction, turning AC on, and closing windows are separate skills (`climate-airflow-direction`, `climate-air-conditioning`, `windows-open-and-position`); you may briefly note they are commonly done alongside, but do not perform or re-teach them here.
5. **Confirm what changed and stop.**

### Ask vs. infer (the under-specification crux)
- **Unstated target window → ASK (it's a genuine open choice).** The defrost window (front vs rear) is a real choice only the user can make; ask which window and use the answer. Don't default to a window or to "both".
- **Never re-ask what context already pins.** If the user already named the window, act on it directly — don't re-ask after they answered. The fan prerequisite is decided by the read current level, not by asking.

### When a capability is missing (do the doable, admit the rest)
- **The fan-speed control is missing → the defrost prerequisite can't be met.** Defrost activation requires the fan at a required level. With no fan-speed control (the tool or its level parameter is gone) you can't satisfy the prerequisite, so defrost is **blocked**: do NOT call `set_window_defrost`, and refuse the defrost honestly, naming the exact blocker — the fan must reach the required level and there is no fan-speed control to do it (the capability lives in `climate-fan-speed`). Never claim defrost is on or "warming up", and never invent a fan adjustment.
- **The defrost tool itself is missing.** Do not call it; say plainly you have no control to run the defrost, and name the adjacent climate controls you retain.
- **A window position reads `"unknown"`.** Treat it as genuinely unverifiable — never claim a window is closed or at any percentage the tool didn't return, and don't invent a sensor-fault reason or a diagnostic lookup that doesn't exist. Do the doable parts and surface the limitation.
Do the doable parts in the same answer; refuse only the impossible part, naming the specific blocker; don't loop, then stop.

## Principles
- **Defrost the exact named window.** Front vs rear is honoured precisely; never default to the other or to both.
- **The fan-level prerequisite is hard.** Defrost can't be activated unless the fan reaches the required level — satisfy it first via `climate-fan-speed`, or if that control is missing, refuse the defrost and name the blocker.
- **Read before activating.** The fan level (and any window position the request touches) is read once before acting.
- **Stay in scope.** This skill owns the defrost toggle and its fan prerequisite — not the airflow/AC/window-close routine, which are separate skills.
- **Never violate a precondition you can't satisfy**, and **`"unknown"` is genuinely unverifiable** — don't treat it as closed/0 or claim a value the tool didn't return.
- **Name the exact blocker** rather than a vague "I can't"; do the doable, refuse only the impossible.

## Common mistakes to avoid
- **Defrosting the wrong target** (rear or both when front was named, or vice versa).
- **Guessing the defrost window** instead of asking, or **re-asking after the user answered**.
- **Calling `set_window_defrost` when the fan prerequisite is unmet and unfixable** (no fan-speed control), or **claiming defrost is on / "warming up"** when it was never activated.
- **Absorbing the wider routine** — performing airflow/AC/window-close steps that belong to separate skills.
- **Inventing a fan adjustment**, a sensor-fault reason, or a diagnostic tool that doesn't exist.
- **Claiming a window is "closed" or at a percentage** when its position is `"unknown"`.
- **Calling a missing tool**, or **looping** instead of doing the doable part and refusing the impossible one once.

## Procedure
1. On a defrost request: `get_climate_settings` to read the current fan level and defrost state (and `get_vehicle_window_positions` if the request touches window positions).
2. If the target window is unstated: ask which window (front or rear) → use the answer as the defrost target.
3. Check the fan prerequisite: if the current fan level is below the required level, raise it via `set_fan_speed` (full method in `climate-fan-speed`). If the fan-speed control is missing, the prerequisite can't be met — do NOT call `set_window_defrost`; name the blocker and stop.
4. With the prerequisite met: `set_window_defrost({defrost_window:<the named/answered window>, on:true})` (or `on:false` to turn it off).
5. For any blocked part, admit it: fan-speed control missing so the fan prerequisite can't be met, defrost tool missing, or a window position `"unknown"`. Confirm what was set, state the limitation once, and stop.
