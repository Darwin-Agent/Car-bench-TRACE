---
name: climate-temperature
description: Set a zone's target climate temperature — execute an absolute value verbatim, treat "reduce/raise by N" as relative (read the current cabin temperature once, then set current±N in ONE call), and treat "match another zone" as a read of the source zone first; apply the whole-car group vs a single zone correctly; infer a preference-fixed temperature silently and ask only for a genuine open target, never re-asking what context already pins; and when a value can't be read it returns "unknown", do the doable part and admit the rest.
tools:
  - get_temperature_inside_car
  - get_user_preferences
  - set_climate_temperature
---

# Set the climate temperature

Set a zone's target temperature. The value may be absolute ("set it to <T>"), relative ("reduce by <N> degrees", "a few degrees warmer"), matched to another zone ("match my side to the passenger"), or fixed by a stored preference. The target may be the whole car or a single zone. Sometimes a needed reading is missing. The same method handles all of these.

## When this applies
"Set the temperature to <value>", "reduce the temperature by <N> degrees", "make it a couple degrees warmer", "match my side to the passenger's", "set the whole car to <value>", "set it to my usual temperature". (Turning AC on is `climate-air-conditioning`; seat heating is `climate-seat-heating`; steering-wheel heating is `climate-steering-wheel-heating`.)

## Tools
- `get_temperature_inside_car({})` — read current per-zone cabin temperature; required before any relative ("by N") or match-another-zone set. A field MAY return `"unknown"` — genuinely unverifiable, not a value.
- `get_user_preferences({})` — read a preference-fixed temperature (the temperature the user likes) so you don't ask for it.
- `set_climate_temperature({temperature, seat_zone})` — set a zone's target temperature. `seat_zone` accepts a single zone (driver, passenger) or a whole-car group value; use the group value when the setting applies to the whole car — not one call per zone.

## Method
1. **Absolute value → set it verbatim.** If the user gives an explicit target, set exactly that value — do not round, substitute, or assume a different one.
2. **Relative "by N" is read-then-compute, in ONE call.** "Reduce/raise by <N>" / "a few degrees cooler-or-warmer" is relative: first `get_temperature_inside_car` to read the current temperature **once**, then issue a **single** `set_climate_temperature` at `current ± N`. Compute off the actual current value; never set an absolute guess for a relative request, and never step per turn or overshoot.
3. **Match-another-zone → read the source zone first.** "Match my side to zone Y" uses zone Y's *current* temperature, not the user's words — read it (`get_temperature_inside_car`), then set the target zone to that exact value.
4. **Apply the right zone.** Use the whole-car group value when the user means the whole car, a single zone when they name one.
5. **Preference-fixed temperature → read the preference, then set it.** "My usual temperature" is fixed by `get_user_preferences`; read it and set that value.
6. **Confirm what changed and stop.** Don't loop on a direct, unambiguous command.

### Ask vs. infer (the under-specification crux)
- **Absolute / relative / match / preference targets are all determined — do NOT ask.** An absolute value is given; a relative value is fixed by the read current temperature; a matched value is fixed by the source zone's reading; a preference value is fixed by `get_user_preferences`. Read the deciding value once, then act.
- **Ask only for a genuine open target.** If the user wants a specific temperature but never gives one and no preference, current state, or relative "by N" instruction determines it, ask — don't invent a number.
- **Never re-ask what context already pins.** A value the user gave, or one fixed by preference/state/match, is acted on directly. A relative change is fully determined by the read; don't ask. Don't loop on reads or "couldn't verify" cycles.

### When a capability is missing (do the doable, admit the rest)
- **The temperature control is missing.** Do not call `set_climate_temperature` (it errors / doesn't exist). Read and report the current temperature if useful, then say plainly you have no control to change the target temperature, and name adjacent climate capabilities you retain. Never claim a temperature was set.
- **A needed reading returns `"unknown"`** (the current cabin temperature for a relative change, or a source zone for a match). Treat it as genuinely unverifiable — never guess a baseline and never claim a value the tool didn't return. A relative `current ± N` or a match can't be grounded without it: report that the reading is unavailable so the relative/matched change can't be computed, and offer to set an absolute value from the user instead. Re-reading won't resolve it.
Do the doable part in the same answer; refuse only the impossible part, naming the specific blocker; don't loop.

## Principles
- **Read before relative and match sets.** You cannot compute `current ± N`, or mirror another zone, without reading the relevant current value first — read it once.
- **Absolute beats assumed.** Every explicit value the user states is used exactly; nothing is invented.
- **Right zone.** Whole-car group when the whole car is meant; a single zone when one is named. One value for the whole car → one group call, not per-zone calls.
- **Hold the computed value.** Once `current ± N` is computed correctly, a vague pushback is not a reason to re-set to a different value.
- **Fulfil the doable, refuse only the impossible**, naming the specific blocker. `"unknown"` is unverifiable; never call a missing tool; offer an absolute value when a relative/matched one can't be grounded.

## Common mistakes to avoid
- **Setting an absolute temperature for a relative request** (a guessed number instead of `current ± N`), or skipping the temperature read so the delta can't be computed.
- **Setting an absolute or worded value for a match** instead of reading the source zone's current temperature.
- **Applying the temperature to the wrong zone** (a single zone when the whole car was meant, or vice versa), or splitting a whole-car value into per-zone calls.
- **Inventing a target the user didn't give / re-asking one they already supplied or that preference fixes.**
- **Hallucinating success** (claiming a temperature set when no working tool could do it), **calling a missing tool**, or **treating `"unknown"` as a value / guessing a baseline**.

## Procedure
1. Absolute value → `set_climate_temperature({temperature:<the value the user gives>, seat_zone:<the zone or the whole-car group>})`.
2. Relative "by N" → `get_temperature_inside_car`, then a single `set_climate_temperature({temperature:<current ± N>, seat_zone:<the zone>})`.
3. Match another zone → `get_temperature_inside_car` for the source zone, then set the target zone to that value.
4. Preference-fixed → `get_user_preferences`, then set that value.
5. If the control is missing or a needed reading is `"unknown"`: do not call a missing tool and don't proceed on an unverifiable reading; name the specific cause, report known values, and offer to set an absolute value instead.
6. Confirm what changed and stop — no loops, no invented value.
