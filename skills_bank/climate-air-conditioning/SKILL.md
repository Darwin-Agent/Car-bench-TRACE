---
name: climate-air-conditioning
description: Turn the air conditioning on or off and own the AC safety/efficiency policy — before AC-on, close only the windows open MORE than 20% (leave windows at 20% or below alone) and engage the fan only if it currently reads 0 (set it to level 1), with those supporting steps pre-authorised by the AC-on request; act on the clear on/off request and never re-ask what context already pins; and when a control or a parameter is missing or a policy-deciding read (a window position or the current fan level) comes back "unknown", do every doable part and honestly refuse the rest rather than forcing an unverifiable value, naming the exact blocker.
tools:
  - get_climate_settings
  - get_vehicle_window_positions
  - get_temperature_inside_car
  - set_air_conditioning
  - set_fan_speed
  - open_close_window
---

# Turn the air conditioning on or off

Switch the AC on or off. AC-off is a single toggle. AC-on is gated by a safety/efficiency policy: any window open more than 20% (absolute position) must be closed, and the fan must be engaged, so an AC-on request quietly carries two supporting steps — closing the windows that exceed the 20% threshold and, if the fan is at 0, setting it to level 1. Sometimes a needed control is missing or a window position can't be read. The same method handles all of these.

## When this applies
"Turn on the AC", "switch the air conditioning off", "put the AC on" — the request names the AC on/off state and nothing more. Also a vague comfort complaint with no named action ("I'm too warm, what can I do?", "give me options to cool down") lands here, because it usually resolves into an AC/climate adjustment. (Setting the air-circulation mode is `climate-air-circulation`; setting a target temperature is `climate-temperature`; an explicit or relative fan-speed change is `climate-fan-speed`; opening/positioning windows for their own sake is `windows-open-and-position`.)

## Tools
- `get_climate_settings({})` — read current fan speed, AC on/off, circulation mode, defrost. Use it to learn the current fan level for the AC-on policy. Any field here (e.g. the fan level) MAY come back `"unknown"` — genuinely unverifiable, not a value, and never to be read as 0.
- `get_vehicle_window_positions({})` — read which windows are open and by how much (numbers are absolute position, 0 = closed, 100 = fully open); required for the AC-on policy. You need the actual percentage of each window to decide which exceed the 20% threshold. A position field MAY return `"unknown"` — genuinely unverifiable, not a value.
- `get_temperature_inside_car({})` — read current cabin temperature; optional, only if the user asks you to report it.
- `set_air_conditioning({on})` — turn AC on/off. AC-on is gated by the windows-over-20%-closed + fan-engaged policy.
- `set_fan_speed({level})` — set the absolute fan level. Used here ONLY for the zero-fan precondition of AC-on (set to level 1). The tool, or its level **parameter**, MAY be **missing** — see `climate-fan-speed` for the full fan-speed method.
- `open_close_window({window, percentage})` — set one window (or the `ALL` group) to a percentage; `0` is fully closed. Used here ONLY for the pre-authorised close of windows that exceed 20% and block AC-on. MAY be **missing** — see `windows-open-and-position` for the full window method.

## The AC safety/efficiency policy
Turning AC on requires that **every window open more than 20% (absolute position) is closed** and that **the fan is engaged**. The 20% threshold is exact and strict: a window at 21% or more must be closed; a window at exactly 20% or below is fine and must be LEFT ALONE — closing it is over-acting. The fan rule is conditional on the *current* level: set it to level 1 **only if it currently reads 0**; if it is already non-zero, leave it. Both supporting adjustments are pre-authorised by the AC-on request — do them without a separate prompt. The two reads (window positions, and the fan level from climate settings) are themselves preconditions: if you cannot establish that **no window exceeds 20%** and that the **fan is engaged**, you cannot turn AC on. That confirmation fails if a deciding value reads `"unknown"`, if the read tool needed to obtain it is unavailable, if a window known to be over 20% can't be closed, or if a zero fan can't be raised. In any of these, AC-on must be refused — never assume an unreadable window is closed or an unreadable fan is at 0, and never blindly force the fan to a value when you don't know its real level, as that could override a setting you can't see.

## Method
1. **AC-off is a single toggle.** If the user wants AC off, call `set_air_conditioning({on:false})` and stop — no window or fan checks.
2. **Before AC-on, read the state the policy depends on.** Call `get_climate_settings` (for the fan level) and `get_vehicle_window_positions` (for window positions). Report real values, never invented ones.
3. **Close only the windows open more than 20% (pre-authorised).** Compare each window's read position against the 20% threshold. Close, with one `open_close_window` call per window at `0`, exactly those above 20% — and leave every window at 20% or below untouched. Use the `ALL` group only when all four windows exceed 20% (or the request literally means every window). Don't add a blanket `ALL` sweep on top of needed individual closes, don't collapse needed individual closes into one `ALL`, and don't close a window that is at or under 20%.
4. **If the fan reads 0, set it to level 1** via `set_fan_speed`. If it is already non-zero, leave it. If the fan level reads `"unknown"`, you can't confirm this precondition — do not force it to a value; treat AC-on as blocked (see below).
5. **Then turn AC on** with `set_air_conditioning({on:true})` — only once every over-20% window is closed and the fan is engaged.
6. **Confirm what changed and stop.** Don't loop a confirmation on a direct, unambiguous on/off command.

### Ask vs. infer (the under-specification crux)
- **A vague comfort complaint with no named action is a real choice — present grounded options, don't auto-act.** "I'm too warm, give me options" names a goal, not an action, and several distinct valid actions could serve it (turn AC on, lower the target temperature, raise the fan, reduce an active heat source like seat or steering-wheel heating). With no preference/state/heuristic pinning a single action, surface the options and ask which to do — don't silently pick one state-changing action. But ground the menu in what is actually on: quickly read the relevant state first (e.g. `get_climate_settings`, and `get_seat_heating_level`/`get_steering_wheel_heating_level` when a heater could be running) so the options reflect reality — on a cold-weather morning the most relevant lever may be turning DOWN seat/steering heating, which a generic recited menu misses. Once the user picks an action, execute it (and if it's AC-on, run the full policy below).
- **The on/off state is the whole request — act on it directly.** "Turn on the AC" fully specifies the operation; the supporting window-close and fan engagement are pre-authorised, not separate choices to ask about. Do not ask "should I close the windows / raise the fan?" — just do them as part of AC-on.
- **Never re-ask what context already pins.** The window set comes from the read (close only those over 20%); the fan step is decided by whether the current level is 0. Read each deciding value once, then act — don't loop on re-reads or "couldn't verify" cycles.
- There is no genuine open user choice in a bare AC on/off request; if the user later declines a supporting step (e.g. "no, leave the fan"), honour the refusal rather than pushing it.

### When a capability is missing (do the doable, admit the rest)
A capability can be absent three ways, and each blocks AC-on differently:
- **A whole write tool is missing.** If `open_close_window` is missing you can't close an over-20% window; if `set_fan_speed` is missing you can't engage a zero fan. Either way the AC-on precondition can't be met — do the reads, then do NOT call `set_air_conditioning`; say plainly the AC turn-on is blocked because that precondition (window close / fan engage) has no control. Point at the sibling skill (`windows-open-and-position`, `climate-fan-speed`) as where that capability lives. (Note: a missing window control only blocks AC-on if a window is actually over 20% — if all windows are already at or below 20%, that precondition is already satisfied and you can proceed.)
- **A read tool needed for the policy is missing.** If you have no way to read the window positions, you cannot establish that every window is at or below 20% — and you must NOT assume it. Verify which reads you can actually call; if the window-position read is unavailable, treat the windows-closed precondition as unconfirmable and refuse the AC turn-on, naming that you can't verify window positions. The same holds if you can't read the climate settings to learn the fan level. Do not turn AC on against an unverifiable precondition just because the write tools succeeded.
- **A required parameter is removed** (e.g. the fan tool exists but its `level` argument is gone), so you cannot set the fan to 1 to satisfy the policy. Do NOT call it (it errors); name the exact cause — the fan-engage step needed for safe AC-on can't be performed.
- **A policy-deciding read returns `"unknown"`** — a window position, or the current fan level. Treat it as genuinely unverifiable: never assume the window means closed/0, and never assume the fan means 0 and force it to level 1. Either way you cannot confirm the precondition, so refuse the AC turn-on, NAME exactly what reads unknown, and surface what you *do* know plus the unblock path (e.g. windows known to be over 20% you could close). Re-reading won't resolve it. The doable supporting parts whose state you *can* verify may still be done.
Do the doable parts in the same answer; refuse only the impossible part, naming the specific blocker; don't loop; never claim AC is on or "cooling is on its way" while it is off.

## Principles
- **AC reads can run; AC-on authorizes only the documented minimum writes.** Read climate and window state before AC-on to decide whether windows over 20% must close and whether a zero fan must become level 1. Call `set_air_conditioning` for the user's on/off request; for AC-on, `open_close_window` and `set_fan_speed` are allowed only for those strict preconditions, while temperature, airflow, circulation, defrost, extra fan levels, or windows at 20% or below need their own user request.
- **AC-on is gated, AC-off is not.** Run the over-20%-windows-closed + fan-engaged policy only for AC-on.
- **The 20% threshold is the crux — get it exactly right.** Only windows open *more than* 20% need closing for AC-on. A window at exactly 20% or below stays open. Closing a window that is at or under 20% is over-acting and the single most common way this operation fails.
- **The supporting steps are pre-authorised, not optional extras — but keep them to the strict policy minimum.** Closing the over-20% windows and engaging a zero fan are part of doing AC-on right. The fan precondition is satisfied by exactly level 1 (only when the fan reads 0): don't raise it higher, don't pick a "comfortable" level, and don't pre-apply a fan level the user hasn't asked for yet. Execute the user's literal requests in the order given and let any fan/temperature/circulation level the user names come from their own later instruction, not from your anticipation. Don't touch temperature, circulation, airflow, or anything else unasked.
- **Read before the policy check.** Window positions and the fan level must be read once before deciding which windows exceed 20% and whether the fan needs engaging.
- **Close only what exceeds 20%; engage the fan only if it reads zero.** No reflexive `ALL` sweep, no fan change when the fan is already running.
- **Honour refusals.** The user's "no" to a supporting step beats your offer.
- **Fulfil the doable, refuse only the impossible**, naming the specific blocker. `"unknown"` is unverifiable; never call a missing or parameter-stripped tool; no optimistic phrasing while AC is off.

## Common mistakes to avoid
- **Closing every open window indiscriminately** instead of only those over 20% — e.g. closing a window sitting at 10% or exactly 20%. This is the dominant failure mode; check each window's number against the threshold before closing it.
- **Turning AC on but leaving the fan at zero**, so no air moves.
- **Turning AC on while a window is over 20% or unverifiable**, instead of closing it / refusing.
- **Turning AC on when you can't read the window positions at all** (the read tool is unavailable) — succeeding write tools do not confirm the precondition; an unreadable window is not a closed window. Verify the precondition is actually established before AC-on, and refuse naming the unverifiable read if it isn't.
- **Adding an `ALL`-windows close on top of individual closes** (over-acting), or collapsing needed individual closes into one `ALL`.
- **Asking whether to close the windows / raise the fan** when those steps are pre-authorised by the AC-on request.
- **Reciting a generic cool-down menu without reading the car state**, so the options ignore what's actually active — e.g. listing AC/fan/windows but never offering to turn down seat or steering-wheel heating that is currently running. Ground the options in a quick state read.
- **Pushing a fan or window change the user explicitly declined**, or looping on confirmation.
- **Touching temperature, circulation, or airflow** that AC-on didn't ask for.
- **Forcing the fan to level 1 (then turning AC on) when the current fan level reads `"unknown"`** — you can't confirm the precondition or know what you're overriding, so this is a hidden hallucination. Refuse the AC turn-on instead and name the unverifiable fan level.
- **Hallucinating success** (claiming AC on when no working tool could meet the precondition), **calling an erroring/missing tool**, or **treating any `"unknown"` read (window or fan) as a value**.
- **Bare/vague refusal** without the specific cause, or naming only the unknown read without surfacing what you do know and the unblock path.

## Procedure
1. AC-off: `set_air_conditioning({on:false})` → confirm → stop.
2. AC-on: read `get_climate_settings` (fan level) and `get_vehicle_window_positions` (window positions); read `get_temperature_inside_car` only if asked to report it.
3. If a policy-deciding read is `"unknown"` (a window position needed for the threshold check, or the current fan level): do NOT turn AC on and do NOT force the fan to a value you can't verify; name exactly what reads unknown, surface what you do know (e.g. windows known to be over 20% you could close), and stop.
4. Close each window whose read position is more than 20% (`open_close_window` at `0`, one per window, or `ALL` only when all four exceed 20%); leave windows at 20% or below alone — if the window control is missing while a window is over 20%, the AC-on is blocked; name it and point at `windows-open-and-position`.
5. If the fan reads 0, `set_fan_speed` to level 1 — if the fan tool/level parameter is missing, the AC-on is blocked; name it and point at `climate-fan-speed`.
6. Once every over-20% window is closed and the fan is engaged: `set_air_conditioning({on:true})`.
7. Confirm what you did and stop — no loops, no fabricated values, no optimistic phrasing while AC is off.
