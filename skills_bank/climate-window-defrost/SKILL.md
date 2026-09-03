---
name: climate-window-defrost
description: Turn the front, rear, or all window defrost on/off — defrost the EXACT named window (ask which only when it's unstated, a genuine open choice). For FRONT or ALL defrost you must run the required automatic cascade in the same turn: read climate and window positions first, then raise the fan to level 2 if below, set airflow to a windshield-including direction if it doesn't already include WINDSHIELD — checking the stored climate preference first so a preferred windshield direction wins over the bare default — and turn AC on if off, and because turning AC on forces it, close every window open more than 20% (fan ends at least 1). REAR-only defrost has NO cascade. If a control needed for a cascade step that is actually required is missing, defrost would be non-compliant so do not activate it — name the exact blocker instead of faking success; treat an "unknown" window position as genuinely unverifiable.
tools:
  - get_climate_settings
  - get_vehicle_window_positions
  - get_user_preferences
  - set_window_defrost
  - set_fan_speed
  - set_fan_airflow_direction
  - set_air_conditioning
  - open_close_window
---

# Turn the window defrost on or off

Turn defrost on (or off) for a target window — front, rear, or all. Activating defrost for the **front or all** windows is never a single call: policy requires a fixed set of automatic supporting changes (fan, airflow, AC, and the window-closing that AC-on forces) to be applied in the same turn. **Rear-only** defrost has none of these requirements. Sometimes the target window is unstated, a control needed for the cascade is missing, or a window position can't be read. The same method handles all of these.

## When this applies
"Turn on the front / rear / all-window defrost", "defrost the windshield", "clear the rear window", "turn the defrost off". This skill owns the defrost toggle **and** the supporting cascade that policy ties to it — do not treat fan/airflow/AC/window-close as out of scope here, because for front/all defrost they are mandatory parts of this operation. (If the user's request is purely about one of those settings on its own — e.g. "set the fan to 3", "point the air at my feet", "turn the AC on", "close my window" — that standalone request belongs to the dedicated climate/window skill; this skill performs them only as the defrost cascade.)

## Tools
- `get_climate_settings({})` — read current fan speed, airflow direction, AC status, and defrost status. Always read this first so each cascade step is applied only when its precondition is unmet.
- `get_vehicle_window_positions({})` — read window positions. Needed for front/all defrost because the cascade turns AC on, which requires closing windows open more than 20%. A position field MAY return `"unknown"` — genuinely unverifiable, never assume it means closed/open.
- `get_user_preferences({preference_categories:{vehicle_settings:{climate_control:true}}})` — read the climate-control preference whenever the cascade will set an airflow direction, because the user may have a preferred windshield-including direction for defrost that must override the bare default.
- `set_window_defrost({defrost_window, on})` — the target action; vocabulary is `FRONT`, `REAR`, `ALL`. Defrost exactly the window named. `FRONT` and `ALL` trigger the cascade below; `REAR` does not.
- `set_fan_speed({level})` — raise the fan to level 2 when it is below (cascade step). The tool or its parameter MAY be missing.
- `set_fan_airflow_direction({direction})` — set a windshield-including direction (`WINDSHIELD`) when the current one doesn't include WINDSHIELD (cascade step). MAY be missing.
- `set_air_conditioning({on})` — turn AC on when it's off (cascade step). MAY be missing.
- `open_close_window({window, percentage})` — close windows open more than 20% after AC is turned on (cascade step). MAY be missing.

## Method
1. **Read state first.** Call `get_climate_settings` for the current fan level, airflow direction, AC status, and defrost state. For front/all defrost also call `get_vehicle_window_positions`, and call `get_user_preferences` for the climate-control category so a preferred defrost airflow direction is known before you set airflow (these reads can run together). Report only real values, never invented ones.
2. **Defrost the exact window named.** Honour front vs rear vs all precisely. Do not default to a different target or to "both".
   - **Honour any explicit window request directly.** If the user asks to close all windows first, or to match windows to a specific window's level, do exactly that as its own action — independent of the cascade. This explicit request is separate from (and not a substitute for) the conditional AC-on close in the cascade; perform both as needed and don't skip one because the other ran.
3. **Run the cascade for FRONT or ALL defrost** — apply each step only if its precondition is currently unmet, then activate defrost:
   - Fan below level 2 → `set_fan_speed({level:2})`.
   - Airflow direction does not include WINDSHIELD → set a windshield-including direction. **Pick the direction the stored climate preference specifies** (e.g. WINDSHIELD_FEET) — `set_fan_airflow_direction({direction:<preferred windshield-including direction, else "WINDSHIELD">})`. Only fall back to the bare `WINDSHIELD` default when no preference pins a specific windshield-including direction. (Directions that already include WINDSHIELD — e.g. WINDSHIELD, WINDSHIELD_FEET, WINDSHIELD_HEAD, WINDSHIELD_HEAD_FEET — need no change.)
   - AC off → `set_air_conditioning({on:true})`. **Because AC is being turned on, also close every window currently open more than 20%** via `open_close_window`, and the fan must end at least 1 (already covered when you raised it to 2). Close only windows strictly above 20%; leave windows at or below 20% as they are.
   - The cascade steps are independent of each other — issue them together — then activate defrost last: `set_window_defrost({defrost_window:<target>, on:true})`.
4. **REAR-only defrost takes no cascade.** Just `set_window_defrost({defrost_window:"REAR", on:true})`. Turning any defrost **off** also takes no cascade — `set_window_defrost({..., on:false})`.
5. **Re-read, don't rely on memory.** Even if windows were closed in an earlier turn, re-read positions when this turn will turn AC on, so the window-closing precondition is verified against current state rather than assumed.
6. **Confirm what changed and stop.**

### Ask vs. infer (the under-specification crux)
- **Unstated target window → ASK (it's a genuine open choice).** Front vs rear vs all is a real choice only the user can make; ask which and use the answer. Don't default to a window or to "both".
- **Never re-ask what context already pins.** If the user already named the window, act on it directly — don't re-ask after they answered. Whether each cascade step is needed is decided by the read state, not by asking; apply the supporting changes automatically without asking permission for them.
- **Close exactly the open windows, not all of them blindly.** Use `window:"ALL"` only when every open window is above 20%; if any window sits between 1 and 20%, close just the windows strictly above 20% individually so you don't over-close.

### When a capability is missing (do the doable, admit the rest)
- **A control needed for a REQUIRED cascade step is missing.** Each step is conditional: a missing control only blocks defrost when that step is actually needed (its precondition is unmet) and can't be met another way. Example: front defrost needs the fan at level 2 and the fan is currently below it, but the fan-speed control is gone — the cascade can't complete, so activating defrost would be non-compliant. In that case do NOT call `set_window_defrost`; refuse the defrost honestly and name the exact blocker (e.g. the fan must reach level 2 and there's no fan-speed control to do it). If instead the step is already satisfied (e.g. fan already at or above 2, airflow already includes WINDSHIELD, AC already on, no window above 20%), a missing control for that step does not block — proceed with the rest.
- **The defrost tool itself is missing.** Don't call it; say plainly you have no control to run the defrost, and name the adjacent climate controls you retain.
- **A window position reads `"unknown"`.** Treat it as genuinely unverifiable — never claim that window is closed or at any percentage, never assume it is below or above 20%, and don't invent a sensor-fault reason or a diagnostic lookup. Close the windows you can verify are above 20%, leave the unknown ones, surface the limitation, and proceed with the rest of the cascade.
- **The window-reading tool itself is entirely unavailable.** This only matters when the cascade's AC-on step actually fires (AC is currently off): turning AC on obliges you to close every window above 20%, and with no way to read positions you cannot tell which qualify, so that step can't be completed compliantly — name this as the blocker. If AC is already on (so the AC-on step doesn't fire), no window reading is needed and the missing read tool does not block; proceed with the rest of the cascade and activate defrost.
- In every case: fulfil the doable parts in the same answer, refuse only the impossible part while naming the specific blocker, don't loop re-reading, then stop. Never claim defrost is on or "warming up" when it was never activated, and never fabricate a value or an adjustment.

## Principles
- **Defrost reads can run; only the named defrost target and its required cascade may change.** Read climate settings, window positions, and relevant preferences before front/all defrost so you know which cascade steps are actually needed. Call `set_window_defrost` for the user's front/rear/all target; front/all also permits only the documented conditional writes (fan to 2 if below, windshield-including airflow, AC on, and closing windows over 20%), while rear-only permits no fan, AC, airflow, or window side effects.
- **Defrost the exact named window.** Front vs rear vs all is honoured precisely; never default to another target or to both.
- **Front/all defrost is a cascade, not a toggle.** Fan→2 (if below), airflow→windshield-including (if not already), AC on (if off), and — because AC-on forces it — close windows above 20% with fan ending ≥1, then activate defrost. Skipping any required piece is the most common failure.
- **Rear-only defrost is a plain toggle.** No fan/airflow/AC/window-close obligations.
- **Read before activating, and re-read for AC.** Read climate (and window positions when AC will turn on) once at the start; verify the window-closing precondition against current state even if you believe windows are already closed.
- **Apply cascade steps automatically, but conditionally.** Only touch a setting whose precondition is unmet — don't re-set what's already correct, and don't over-close windows at or below 20%.
- **A stored preference outranks the default within a cascade step.** When the airflow step fires, the windshield-including direction the user prefers (read from the climate preference) wins over the generic WINDSHIELD default — matching the gold state depends on it.
- **`"unknown"` is genuinely unverifiable** — don't treat it as closed/0 or claim a value the tool didn't return.
- **Name the exact blocker** rather than a vague "I can't"; do the doable, refuse only the impossible.

## Common mistakes to avoid
- **Activating front/all defrost without closing the open windows** when the cascade turns AC on — the single most common failure. Read positions and close those above 20%.
- **Skipping the airflow change** to a windshield-including direction when the current airflow doesn't include WINDSHIELD.
- **Defaulting to bare `WINDSHIELD` without checking the climate preference** — if the user has a preferred windshield-including direction (e.g. WINDSHIELD_FEET), setting plain WINDSHIELD leaves the car in the wrong state. Read the preference before setting airflow.
- **Relying on memory** that windows were closed earlier instead of re-reading positions when this turn turns AC on.
- **Over-closing** windows that are at or below 20% (or using `ALL` when some windows sit between 1 and 20%).
- **Defrosting the wrong target** (rear or both when front was named, or vice versa), or **guessing the target** instead of asking, or **re-asking after the user answered**.
- **Running the cascade for a REAR-only request** — rear defrost has no supporting requirements.
- **Ignoring an explicit window instruction** the user gave alongside the defrost (e.g. "close all windows first" or "match them to the passenger rear") — carry it out exactly as asked, separately from the cascade's AC-on close.
- **Calling `set_window_defrost` when a required cascade step can't be completed** (e.g. fan must reach 2 but no fan-speed control), or **claiming defrost is on / "warming up"** when it was never activated.
- **Inventing a fan/airflow/AC adjustment, a sensor-fault reason, or a diagnostic tool** that doesn't exist.
- **Claiming a window is "closed" or at a percentage** when its position is `"unknown"`.
- **Turning AC on (and thus activating front/all defrost) when window positions can't be read at all** and AC is currently off — you can't fulfil the mandatory close-windows-above-20% step, so name that as the blocker instead of proceeding; this does not apply when AC is already on.
- **Calling a missing tool**, or **looping** instead of doing the doable part and refusing the impossible one once.

## Procedure
1. On a defrost request: `get_climate_settings`; for front/all defrost also `get_vehicle_window_positions` and `get_user_preferences` for climate control (run together).
2. If the target window is unstated: ask which (front, rear, or all) → use the answer as the target.
3. If the target is REAR only (or the request is to turn defrost off): call `set_window_defrost({defrost_window:<target>, on:<state>})` directly and confirm.
4. If the target is FRONT or ALL (turning on): apply the cascade for each unmet precondition — `set_fan_speed({level:2})` if fan below 2; `set_fan_airflow_direction({direction:<preferred windshield-including direction from the climate preference, else "WINDSHIELD">})` if airflow excludes WINDSHIELD; `set_air_conditioning({on:true})` if AC off and, since AC turns on, `open_close_window({window, percentage:0})` for every window currently above 20% (use `ALL` only if all open windows exceed 20%). Issue these together.
5. With the cascade applied: `set_window_defrost({defrost_window:<target>, on:true})`.
6. If a required cascade step can't be completed because its control is missing (and the step was actually needed): do NOT call `set_window_defrost`; name the exact blocker and stop. For unknown window positions: close the verifiable ones, surface the unverifiable ones, proceed with the rest. Confirm what was set, state any limitation once, and stop.
