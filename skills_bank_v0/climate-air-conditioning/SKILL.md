---
name: climate-air-conditioning
description: Turn the air conditioning on or off and own the AC safety/efficiency policy — before AC-on, verify all windows are closed and the fan is engaged (if the fan reads 0, raise it to the lowest non-zero level first), with closing the open windows and the fan bump pre-authorised by the AC-on request; act on the clear on/off request and never re-ask what context already pins; and when a control or a parameter is missing or a window position reads "unknown", do every doable part and honestly admit the rest, naming the exact blocker.
tools:
  - get_climate_settings
  - get_vehicle_window_positions
  - get_temperature_inside_car
  - set_air_conditioning
  - set_fan_speed
  - open_close_window
---

# Turn the air conditioning on or off

Switch the AC on or off. AC-off is a single toggle. AC-on is gated by a safety/efficiency policy: the windows must be verified closed and the fan must be engaged, so an AC-on request quietly carries two supporting steps — closing any open windows and, if the fan is at 0, bumping it to the lowest non-zero level. Sometimes a needed control is missing or a window position can't be read. The same method handles all of these.

## When this applies
"Turn on the AC", "switch the air conditioning off", "put the AC on" — the request names the AC on/off state and nothing more. (Setting the air-circulation mode is `climate-air-circulation`; setting a target temperature is `climate-temperature`; an explicit or relative fan-speed change is `climate-fan-speed`; opening/positioning windows for their own sake is `windows-open-and-position`.)

## Tools
- `get_climate_settings({})` — read current fan speed, AC on/off, circulation mode, defrost. Use it to learn the current fan level for the AC-on policy.
- `get_vehicle_window_positions({})` — read which windows are open and by how much; required for the AC-on policy. A position field MAY return `"unknown"` — genuinely unverifiable, not a value.
- `get_temperature_inside_car({})` — read current cabin temperature; optional, only if the user asks you to report it.
- `set_air_conditioning({on})` — turn AC on/off. AC-on is gated by the windows-closed + fan-engaged policy.
- `set_fan_speed({level})` — set the absolute fan level. Used here ONLY for the zero-fan bump precondition of AC-on (raise to the lowest non-zero level). The tool, or its level **parameter**, MAY be **missing** — see `climate-fan-speed` for the full fan-speed method.
- `open_close_window({window, percentage})` — set one window (or the `ALL` group) to a percentage; `0` is fully closed. Used here ONLY for the pre-authorised close of windows that block AC-on. MAY be **missing** — see `windows-open-and-position` for the full window method.

## The AC safety/efficiency policy
Turning AC on requires that **all windows are verified closed** and that **the fan is engaged**. If a window is open, close it (the close is pre-authorised by the AC-on request). If the fan reads 0, raise it to the lowest non-zero level first so the AC air actually flows (this bump is likewise pre-authorised). These two supporting adjustments are part of fulfilling an AC-on request — do them without a separate prompt. If you cannot verify the windows are closed, cannot close an open window, or cannot raise the fan from 0, the AC turn-on cannot be completed safely and must be refused.

## Method
1. **AC-off is a single toggle.** If the user wants AC off, call `set_air_conditioning({on:false})` and stop — no window or fan checks.
2. **Before AC-on, read the state the policy depends on.** Call `get_climate_settings` (for the fan level) and `get_vehicle_window_positions` (for window positions). Report real values, never invented ones.
3. **Close any open windows (pre-authorised).** Close exactly the windows the read shows open — one `open_close_window` call per window at `0` (or the `ALL` group when every window is open / the request means all). Don't add a blanket `ALL` sweep on top of needed individual closes, and don't collapse needed individual closes into one `ALL`.
4. **If the fan reads 0, bump it once to the lowest non-zero level** via `set_fan_speed`. If the fan is already non-zero, leave it as-is.
5. **Then turn AC on** with `set_air_conditioning({on:true})` — only once the windows are verifiably closed and the fan is engaged.
6. **Confirm what changed and stop.** Don't loop a confirmation on a direct, unambiguous on/off command.

### Ask vs. infer (the under-specification crux)
- **The on/off state is the whole request — act on it directly.** "Turn on the AC" fully specifies the operation; the supporting window-close and fan-bump are pre-authorised, not separate choices to ask about. Do not ask "should I close the windows / raise the fan?" — just do them as part of AC-on.
- **Never re-ask what context already pins.** The window set comes from the read (close only what's open); the fan bump is decided by whether the current level is 0. Read each deciding value once, then act — don't loop on re-reads or "couldn't verify" cycles.
- There is no genuine open user choice in a bare AC on/off request; if the user later declines a supporting step (e.g. "no, leave the fan"), honour the refusal rather than pushing it.

### When a capability is missing (do the doable, admit the rest)
A capability can be absent three ways, and each blocks AC-on differently:
- **A whole tool is missing.** If `open_close_window` is missing you can't close an open window; if `set_fan_speed` is missing you can't bump a zero fan. Either way the AC-on precondition can't be met — do the reads, then do NOT call `set_air_conditioning`; say plainly the AC turn-on is blocked because that precondition (window close / fan engage) has no control. Point at the sibling skill (`windows-open-and-position`, `climate-fan-speed`) as where that capability lives.
- **A required parameter is removed** (e.g. the fan tool exists but its `level` argument is gone), so you cannot raise the fan from 0 to satisfy the policy. Do NOT call it (it errors); name the exact cause — the fan-engage step needed for safe AC-on can't be performed.
- **A window position reads `"unknown"`.** Treat it as genuinely unverifiable — never assume it means closed/0. Refuse the AC turn-on, NAME the unknown window, AND surface the windows known to be open and offer to close them, so the limitation is tied to what would unblock it. Re-reading won't resolve it.
Do the doable parts in the same answer; refuse only the impossible part, naming the specific blocker; don't loop; never claim AC is on or "cooling is on its way" while it is off.

## Principles
- **AC-on is gated, AC-off is not.** Run the windows-closed + fan-engaged policy only for AC-on.
- **The supporting steps are pre-authorised, not optional extras.** Closing open windows and bumping a zero fan are part of doing AC-on right — but only those; don't touch temperature, circulation, or anything unasked.
- **Read before the policy check.** Window positions and the fan level must be read once before deciding what to close and whether to bump.
- **Close only what's open; bump only if zero.** No reflexive `ALL` sweep, no fan change when the fan is already running.
- **Honour refusals.** The user's "no" to a supporting step beats your offer.
- **Fulfil the doable, refuse only the impossible**, naming the specific blocker. `"unknown"` is unverifiable; never call a missing or parameter-stripped tool; no optimistic phrasing while AC is off.

## Common mistakes to avoid
- **Turning AC on but leaving the fan at zero**, so no air moves.
- **Turning AC on with a window open or unverifiable**, instead of closing it / refusing.
- **Adding an `ALL`-windows close on top of individual closes** (over-acting), or collapsing needed individual closes into one `ALL`.
- **Asking whether to close the windows / raise the fan** when those steps are pre-authorised by the AC-on request.
- **Pushing a fan or window change the user explicitly declined**, or looping on confirmation.
- **Touching temperature, circulation, or airflow** that AC-on didn't ask for.
- **Hallucinating success** (claiming AC on when no working tool could meet the precondition), **calling an erroring/missing tool**, or **treating `"unknown"` as a value**.
- **Bare/vague refusal** without the specific cause, or naming only the unknown window without surfacing the known-open ones and the unblock path.

## Procedure
1. AC-off: `set_air_conditioning({on:false})` → confirm → stop.
2. AC-on: read `get_climate_settings` (fan level) and `get_vehicle_window_positions` (window positions); read `get_temperature_inside_car` only if asked to report it.
3. If any window position is `"unknown"`: do NOT turn AC on; name the unknown window, surface the known-open windows, offer to close them, and stop.
4. Close each open window (`open_close_window` at `0`, one per window, or `ALL` when meant) — if the window control is missing, the AC-on is blocked; name it and point at `windows-open-and-position`.
5. If the fan reads 0, `set_fan_speed` to the lowest non-zero level — if the fan tool/level parameter is missing, the AC-on is blocked; name it and point at `climate-fan-speed`.
6. Once windows are verifiably closed and the fan is engaged: `set_air_conditioning({on:true})`.
7. Confirm what you did and stop — no loops, no fabricated values, no optimistic phrasing while AC is off.
