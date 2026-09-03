---
name: climate-steering-wheel-heating
description: Set the steering-wheel heating level — set an absolute level verbatim, infer a preference-fixed level silently, and for "match the wheel to my seat" read the seat's current level and set the wheel to that level; never re-ask what context already pins; and when the wheel-heating tool is missing, say so plainly (you may still read the seat level even when you can't change the wheel), naming the exact blocker.
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
2. **"Match the wheel to my seat" → read the seat level, then set the wheel to it.** The value is the seat's *current* level, not the user's words — read it (`get_seat_heating_level`), then set the wheel to that exact level. Don't substitute a different number.
3. **Preference-fixed level → read the preference, then set it.** "My usual" is fixed by `get_user_preferences`; read it and set that level.
4. **Confirm what changed and stop.**

### Ask vs. infer (the under-specification crux)
- **Absolute / preference / match levels are all determined — do NOT ask.** An absolute value is given; a preference value is fixed by `get_user_preferences`; a matched value is fixed by the seat's reading. Read the deciding value once, then act.
- **Match-to-seat → set the wheel to the seat's level automatically; do NOT re-ask the matched level.**
- **Never re-ask what context already pins.** A level the user gave, or one fixed by preference or a match, is acted on directly. Ask only if the user wants a level but gives none and no preference/match determines it.

### When a capability is missing (do the doable, admit the rest)
- **The steering-wheel-heating tool is missing.** Do not call `set_steering_wheel_heating` (it errors / doesn't exist). For a match request you may still READ and report the seat's current level even though you can't apply it to the wheel — then say plainly you have no control to change the steering-wheel heating, naming the exact blocker. Never claim the wheel heating changed when no working tool could do it.
- **A needed value reads `"unknown"`** (the seat level for a match). Treat it as genuinely unverifiable; don't guess a baseline and don't claim a level the tool never returned — offer an absolute level instead.
Do the doable part in the same answer; refuse only the impossible part, naming the specific blocker; don't loop.

## Principles
- **Read before a match.** The wheel's target for "match the seat" is only knowable from the seat reading — read it once.
- **Honour the exact mapping.** "Match the wheel to the seat" = the seat's level, not a different number.
- **Absolute / preference beat assumed.** An explicit or preference-fixed level is used exactly; nothing is invented.
- **Do only what was asked.** Touch only the steering-wheel heating.
- **Fulfil the doable, refuse only the impossible**, naming the exact missing capability. Never call a missing tool; read-only is still useful ("I can read the seat level but can't change the wheel").

## Common mistakes to avoid
- **Setting a different number for "match the seat"** instead of reading the seat's current level.
- **Asking for a preference-fixed level** instead of reading it, or **re-asking the matched level**.
- **Guessing a level** the user never gave.
- **Claiming the wheel heating changed when no control exists**, **calling a missing tool**, or **guessing a baseline for an `"unknown"` seat level**.

## Procedure
1. Absolute level → `set_steering_wheel_heating({level:<the level the user gives>})` if the tool exists.
2. Match the seat → `get_seat_heating_level`, then `set_steering_wheel_heating({level:<the seat's current level>})`.
3. Preference-fixed → `get_user_preferences`, then set that level.
4. If the wheel-heating tool is missing: for a match, read and report the seat level; then say plainly you can't change the steering-wheel heating, naming the blocker, and stop. If the seat reading is `"unknown"`, don't guess — offer an absolute level instead.
5. Confirm what changed and stop — no loops, no invented level.
