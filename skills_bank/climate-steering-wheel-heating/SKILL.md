---
name: climate-steering-wheel-heating
description: Set the steering-wheel heating level — set an absolute level verbatim, infer a preference-fixed level silently, and for "match the wheel to my seat" use the seat's level (read it, or the value just being set this turn) and set the wheel to that; "turn on"/"activate" with no level and no preference/match has no default — ask rather than guess a level; never re-ask what context already pins; and when the wheel-heating tool is missing, say so plainly (you may still read the seat level even when you can't change the wheel), naming the exact blocker.
tools:
  - get_seat_heating_level
  - get_user_preferences
  - set_steering_wheel_heating
---

# Set the steering-wheel heating

Set the steering-wheel heating level. The level may be explicit, fixed by a stored preference, or told to match the seat heating. Sometimes the control is missing. The same method handles all of these.

## When this applies
"Turn on the steering-wheel heating", "set the wheel heating to <level>", "set the wheel heating to my usual", "match the wheel heating to my seat". (Seat heating is `climate-seat-heating`; cabin temperature is `climate-temperature`.)

## Tools
- `get_seat_heating_level({})` — read the current seat-heating level; required for "match the wheel to the seat". A field MAY return `"unknown"` — genuinely unverifiable, not a value.
- `get_user_preferences({})` — read a preference-fixed wheel-heating level so you don't ask for it.
- `set_steering_wheel_heating({level})` — set the steering-wheel heating level. The whole tool MAY be **missing**.

## Method
1. **Absolute level → set it verbatim** via `set_steering_wheel_heating`.
2. **"Match the wheel to my seat" → use the seat's level.** The value is the seat's level, not the user's words. If you are setting the seat heating to a known level in the same turn, set the wheel to that same level (you may call both in parallel). Otherwise read the seat's *current* level (`get_seat_heating_level`) and set the wheel to that exact level. Don't substitute a different number. If the seat zones report different levels (e.g. driver and passenger differ), the steering wheel is the driver's, so match the driver seat's level — don't ask which zone.
3. **Preference-fixed level → read the preference, then set it.** "My usual" is fixed by `get_user_preferences`; read it and set that level.
4. **"Turn on"/"activate" with no level, no preference, no match → ask which level.** There is no default on-level for steering-wheel heating; the levels are 1, 2, or 3. Do not pick one yourself (1 is not a safe default). Ask the user, then set the level they give.
5. **Confirm what changed and stop.**

### Ask vs. infer (the under-specification crux)
- **Absolute / preference / match levels are all determined — do NOT ask.** An absolute value is given; a preference value is fixed by `get_user_preferences`; a matched value is fixed by the seat's level. Read the deciding value once, then act.
- **Match-to-seat → set the wheel to the seat's level automatically; do NOT re-ask the matched level.**
- **"Turn on" / "activate" with no level pinned → ASK, do NOT guess.** When the request wants heating on but gives no number, and no preference and no match determine it, the level is a genuine choice only the user can make. Picking a number (e.g. defaulting to 1) is the failure — ask which of levels 1, 2, or 3 they want. Always check `get_user_preferences` first; only ask if nothing pins it.
- **Never re-ask what context already pins.** A level the user gave, or one fixed by preference or a match, is acted on directly.

### When a capability is missing (do the doable, admit the rest)
- **The steering-wheel-heating tool is missing.** Do not call `set_steering_wheel_heating` (it errors / doesn't exist). For a match request you may still READ and report the seat's current level even though you can't apply it to the wheel — then say plainly you have no control to change the steering-wheel heating, naming the exact blocker. Never claim the wheel heating changed when no working tool could do it.
- **A needed value reads `"unknown"`** (the seat level for a match). Treat it as genuinely unverifiable; don't guess a baseline and don't claim a level the tool never returned — offer an absolute level instead.
Do the doable part in the same answer; refuse only the impossible part, naming the specific blocker; don't loop.

## Principles
- **Wheel-heat reads can run; set only the wheel at a pinned level.** Read seat heating for a "match the seat" request and read preferences for the user's usual wheel level. Call `set_steering_wheel_heating` only when the level is explicit, preference-fixed, or read from the seat; do not also change seat heating, cabin temperature, fan, or other warming controls, and do not guess a match if the source level is `"unknown"`.
- **Read before a match.** The wheel's target for "match the seat" is only knowable from the seat reading — read it once.
- **Honour the exact mapping.** "Match the wheel to the seat" = the seat's level, not a different number.
- **Absolute / preference beat assumed.** An explicit or preference-fixed level is used exactly; nothing is invented.
- **Do only what was asked.** Touch only the steering-wheel heating.
- **Fulfil the doable, refuse only the impossible**, naming the exact missing capability. Never call a missing tool; read-only is still useful ("I can read the seat level but can't change the wheel").

## Common mistakes to avoid
- **Setting a different number for "match the seat"** instead of using the seat's level (the one being set this turn, or its current reading).
- **Asking for a preference-fixed level** instead of reading it, or **re-asking the matched level**.
- **Defaulting "turn on"/"activate" to a level (e.g. 1)** when no level, preference, or match pins it — that is a guess, and the wrong one. Ask which level instead.
- **Claiming the wheel heating changed when no control exists**, **calling a missing tool**, or **guessing a baseline for an `"unknown"` seat level**.

## Procedure
1. Absolute level → `set_steering_wheel_heating({level:<the level the user gives>})` if the tool exists.
2. Match the seat → use the seat level being set this turn, or `get_seat_heating_level`, then `set_steering_wheel_heating({level:<the seat's level>})`. If zones differ, use the driver seat's level.
3. Preference-fixed → `get_user_preferences`, then set that level.
4. "Turn on"/"activate" with no level → check `get_user_preferences`; if nothing pins a level, ask which of 1, 2, or 3, then set it. Don't guess.
5. If the wheel-heating tool is missing: for a match, read and report the seat level; then say plainly you can't change the steering-wheel heating, naming the blocker, and stop. If the seat reading is `"unknown"`, don't guess — offer an absolute level instead.
6. Confirm what changed and stop — no loops, no invented level.
