---
name: climate-temperature
description: Set a zone's target climate temperature — execute an absolute value verbatim, treat "reduce/raise by N" as relative (read the current cabin temperature once, then set current±N in ONE call), and treat "match another zone" as a read of the source zone first; apply the whole-car group vs a single zone correctly; after a single-zone set, warn if the resulting gap to other zones exceeds 3°C; when the user only states a feeling ("too warm/cold", "warm up the car") rather than a value or control, surface the available climate options instead of silently narrowing to temperature; infer a preference-fixed temperature silently and ask only for a genuine open target, never re-asking what context already pins; and when a value can't be read it returns "unknown", do the doable part and admit the rest.
tools:
  - get_temperature_inside_car
  - get_user_preferences
  - set_climate_temperature
  - get_climate_settings
  - get_seat_heating_level
---

# Set the climate temperature

Set a zone's target temperature. The value may be absolute ("set it to <T>"), relative ("reduce by <N> degrees", "a few degrees warmer"), matched to another zone ("match my side to the passenger"), or fixed by a stored preference. The target may be the whole car or a single zone. Sometimes a needed reading is missing. The same method handles all of these.

## When this applies
"Set the temperature to <value>", "reduce the temperature by <N> degrees", "make it a couple degrees warmer", "match my side to the passenger's", "set the whole car to <value>", "set it to my usual temperature". Also vague comfort statements that imply a temperature change ("I'm too warm", "it's chilly in here", "warm up the car") — but see "Ask vs. infer" for how to handle these, since they usually call for surfacing options rather than silently setting a number. (Turning AC on is `climate-air-conditioning`; seat heating is `climate-seat-heating`; steering-wheel heating is `climate-steering-wheel-heating`.)

## Tools
- `get_temperature_inside_car({})` — read current per-zone cabin temperature; required before any relative ("by N") or match-another-zone set, and to check the cross-zone gap after a single-zone set. A field MAY return `"unknown"` — genuinely unverifiable, not a value.
- `get_user_preferences({})` — read a preference-fixed temperature (the temperature the user likes) so you don't ask for it.
- `set_climate_temperature({temperature, seat_zone})` — set a zone's target temperature. `seat_zone` accepts a single zone (driver, passenger) or a whole-car group value; use the group value when the setting applies to the whole car — not one call per zone. This tool (or its `seat_zone` argument) MAY be absent for a task — verify it is callable before relying on it.
- `get_climate_settings({})` / `get_seat_heating_level({})` — read current climate state and seat-heating level. Use these to ground the options you offer when the user only voices a feeling, so you surface what is actually active (e.g. a heater running while they're too warm) rather than a generic menu.

## Method
1. **Absolute value → set it verbatim.** If the user gives an explicit target, set exactly that value — do not round, substitute, or assume a different one.
2. **Relative "by N" is read-then-compute, in ONE call.** "Reduce/raise by <N>" / "a few degrees cooler-or-warmer" is relative: first `get_temperature_inside_car` to read the current temperature **once**, then issue a **single** `set_climate_temperature` at `current ± N`. Compute off the actual current value; never set an absolute guess for a relative request, and never step per turn or overshoot.
3. **Match-another-zone → read the source zone first.** "Match my side to zone Y" uses zone Y's *current* temperature, not the user's words — read it (`get_temperature_inside_car`), then set the target zone to that exact value.
4. **Apply the right zone.** Use the whole-car group value when the user means the whole car, a single zone when they name one.
5. **Preference-fixed temperature → read the preference, then set it.** "My usual temperature" is fixed by `get_user_preferences`; read it and set that value.
6. **After setting a SINGLE zone, check the cross-zone gap.** When you set one zone (driver or passenger) rather than the whole car, the other zone is unchanged. Read the per-zone temperatures (the same `get_temperature_inside_car` you may already have) and, if the resulting difference between the set zone and any other zone exceeds 3°C, tell the user about it in your confirmation. This is a required notification, not optional chatter — a single-zone set that leaves a >3°C gap and says nothing is incomplete. It is a heads-up only; do not change the other zone to close the gap unless asked.
7. **Confirm what changed and stop.** Don't loop on a direct, unambiguous command.

### Ask vs. infer (the under-specification crux)
- **Absolute / relative / match / preference targets are all determined — do NOT ask.** An absolute value is given; a relative value is fixed by the read current temperature; a matched value is fixed by the source zone's reading; a preference value is fixed by `get_user_preferences`. Read the deciding value once, then act.
- **Ask only for a genuine open target.** If the user wants a specific temperature but never gives one and no preference, current state, or relative "by N" instruction determines it, ask — don't invent a number.
- **A bare feeling ("I'm too warm", "warm up the car", "it's chilly") is not a temperature request — surface options, don't silently jump to one.** The user has named a problem, not a control. There are several legitimate ways to address it (target temperature, AC, fan, seat heating, windows), and the right one is a genuine user choice you can't pin from state or preference alone. So briefly present the available options and let the user pick, rather than narrowing straight to "what temperature should I set?" — collapsing a comfort complaint into a single control, or asking only for a number, is the failure here. Only once the user selects a control and (if needed) a value do you act, applying the determined-value rules above. Do not proactively fire a state-changing call off a mere feeling.
- **Ground the offered options in the car's actual current state — don't recite a generic menu.** Before offering cooling/warming options, read the current climate state (and seat-heating level when relevant) so the options you list are real and on-point. The single most relevant lever is often the one that is currently working against the user: if the user is too warm and a heater (seat or steering-wheel heating) is currently on, offering to turn that down is a primary option, not an afterthought; if they are cold and AC is running, offering to turn it off matters. Keep the list short and relevant to what is actually active rather than dumping every conceivable action (and avoid offering controls hedged by heavy preconditions, like the sunroof, unless they are genuinely apt). An options reply that omits the obvious state-relevant lever is incomplete even though it "offered options".
- **Once the user picks an action, do exactly that — don't fan out.** After you offer options and the user selects one (e.g. "turn on AC and lower by 4 degrees"), execute that chosen action and stop. Offering an adjacent lever earlier is fine, but proactively *executing* extra state changes the user didn't choose — turning off seat heaters, opening windows, switching circulation — beyond what they asked for or confirmed is over-acting and a failure, even when it would also help. Surface a further suggestion at most; let the user confirm before acting on it.
- **Never re-ask what context already pins.** A value the user gave, or one fixed by preference/state/match, is acted on directly. A relative change is fully determined by the read; don't ask. Don't loop on reads or "couldn't verify" cycles.
- **An explicit new value overrides a preference you just applied — and requires a real tool call.** If you set the preferred temperature and the user then says "actually make it <T> instead", the user's stated number wins over the preference (explicit request outranks a learned preference). Issue a fresh `set_climate_temperature` call with the new value; never reply "done, set to <T>" without actually calling the tool. Narrating a change you never executed is a hallucinated success and a failure.

### When a capability is missing (do the doable, admit the rest)
- **The temperature control is missing.** Do not call `set_climate_temperature` (it errors / doesn't exist). Read and report the current temperature if useful, then say plainly you have no control to change the target temperature, and name adjacent climate capabilities you retain. Never claim a temperature was set.
- **A needed reading returns `"unknown"`** (the current cabin temperature for a relative change, or a source zone for a match). Treat it as genuinely unverifiable — never guess a baseline and never claim a value the tool didn't return. A relative `current ± N` or a match can't be grounded without it: report that the reading is unavailable so the relative/matched change can't be computed, and offer to set an absolute value from the user instead. Re-reading won't resolve it.
Do the doable part in the same answer; refuse only the impossible part, naming the specific blocker; don't loop.

## Principles
- **Temperature and climate-state reads can run; temperature writes need a pinned value and zone.** Read per-zone temperature for relative/match requests and gap checks, preferences for "my usual temperature", and current climate/seat heat to ground options for vague discomfort. Call `set_climate_temperature` only when the target value and zone are explicit, preference-fixed, or computed from a valid read; do not convert a bare "too hot/cold" feeling into an automatic temperature, AC, fan, seat-heater, window, or circulation change without the user choosing that lever.
- **Read before relative and match sets.** You cannot compute `current ± N`, or mirror another zone, without reading the relevant current value first — read it once.
- **Absolute beats assumed.** Every explicit value the user states is used exactly; nothing is invented.
- **Right zone.** Whole-car group when the whole car is meant; a single zone when one is named. One value for the whole car → one group call, not per-zone calls.
- **Single-zone sets can create a comfort gap — surface it.** Setting one zone leaves the others as-is; if that opens a difference of more than 3°C between zones, the user must hear about it. Reading the per-zone temperatures (which you often already do for the set itself) lets you check and report this.
- **A feeling is an invitation to offer options, not a cue to guess.** When the user only describes discomfort, the deciding choice of which control to use is theirs; present the options and wait, don't auto-select one and don't fire a state change.
- **Hold the computed value, but honour an explicit override.** Once `current ± N` is computed correctly, a vague pushback is not a reason to re-set to a different value. But when the user names a concrete new target (overriding a preference or an earlier value), that explicit value wins — apply it with a real tool call.
- **A confirmation must reflect an actual call.** Only state that a temperature was set after the corresponding `set_climate_temperature` call returned success. Never report a value you didn't call for.
- **Fulfil the doable, refuse only the impossible**, naming the specific blocker. `"unknown"` is unverifiable; never call a missing tool; offer an absolute value when a relative/matched one can't be grounded.

## Common mistakes to avoid
- **Setting an absolute temperature for a relative request** (a guessed number instead of `current ± N`), or skipping the temperature read so the delta can't be computed.
- **Setting an absolute or worded value for a match** instead of reading the source zone's current temperature.
- **Applying the temperature to the wrong zone** (a single zone when the whole car was meant, or vice versa), or splitting a whole-car value into per-zone calls.
- **Setting a single zone and staying silent when the resulting cross-zone difference exceeds 3°C** — the user must be told about the gap.
- **Treating a bare comfort statement ("too warm", "warm up the car") as a direct temperature request** — narrowing straight to "what temperature?" or auto-setting a value instead of surfacing the available climate options for the user to choose from.
- **Offering a generic, exhaustive options menu without reading current state** — reciting every conceivable lever (including ill-fitting ones like the sunroof) while omitting the obviously state-relevant one, e.g. failing to offer to turn down a heater that is currently on when the user is too warm. Read the relevant current state first and keep the offered options real and short.
- **Over-acting after the user chooses an option** — once they pick the action (e.g. AC plus a relative temperature drop), executing extra unrequested state changes (turning off seat heaters, opening windows, changing circulation) on your own initiative instead of doing only the chosen action and at most suggesting more.
- **Inventing a target the user didn't give / re-asking one they already supplied or that preference fixes.**
- **Confirming a new value without calling the tool** — after applying a preference, the user asks for a different explicit value and you reply "done, set to <T>" but never issue the `set_climate_temperature` call. An explicit new value overrides the preference and must be applied with a real call before you confirm it.
- **Hallucinating success** (claiming a temperature set when no working tool could do it), **calling a missing tool**, or **treating `"unknown"` as a value / guessing a baseline**.

## Procedure
1. Absolute value → `set_climate_temperature({temperature:<the value the user gives>, seat_zone:<the zone or the whole-car group>})`.
2. Relative "by N" → `get_temperature_inside_car`, then a single `set_climate_temperature({temperature:<current ± N>, seat_zone:<the zone>})`.
3. Match another zone → `get_temperature_inside_car` for the source zone, then set the target zone to that value.
4. Preference-fixed → `get_user_preferences`, then set that value.
5. If the control is missing or a needed reading is `"unknown"`: do not call a missing tool and don't proceed on an unverifiable reading; name the specific cause, report known values, and offer to set an absolute value instead.
6. After a single-zone set, check per-zone temperatures; if the gap to another zone now exceeds 3°C, include that heads-up in your confirmation.
7. If the user only voiced a feeling (no value, no chosen control), read the relevant current climate state (e.g. `get_climate_settings`, `get_seat_heating_level`), then surface a short list of state-relevant options — including turning down whatever is currently working against them (a running heater when they're too warm, AC when they're cold) — and wait for the user to pick before any state-changing call.
8. Confirm what changed and stop — no loops, no invented value.
