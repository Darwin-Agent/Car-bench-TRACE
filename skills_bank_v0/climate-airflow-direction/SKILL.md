---
name: climate-airflow-direction
description: Set the fan airflow direction — set exactly the named direction (single or compound) verbatim; for a bare "change the direction" with no pointer, ASK which direction; for "the one I like / my usual", infer from the stored preference (and when the preference is a compound direction, set the compound value, not the simpler one); never re-ask what context already pins; and when the airflow-direction control is missing, say so plainly and name the controls you still have.
tools:
  - get_climate_settings
  - get_user_preferences
  - set_fan_airflow_direction
---

# Set the fan airflow direction

Redirect where the cabin air blows. The direction may be named outright (a single target such as feet, head, or windshield, or a compound combination), left as a bare open choice, or pointed at the user's stored preference. Sometimes the control is missing. The same method handles all of these.

## When this applies
"Point the air at my feet / the windshield", "blow toward the feet and the windshield", "change the fan airflow direction", "point the air the way I like it / my usual direction". (Setting fan speed is `climate-fan-speed`; turning AC on is `climate-air-conditioning`; setting the circulation mode is `climate-air-circulation`.)

## Tools
- `get_climate_settings({})` — read the current airflow direction (and the rest of the climate state); use to report state or confirm what changed.
- `get_user_preferences({})` — read the user's liked airflow direction when the request points to a preference ("the direction I like", "my usual"). The preference MAY be a compound direction.
- `set_fan_airflow_direction({direction})` — set the airflow direction; the vocabulary covers single targets and compound combinations (e.g. one that bundles the footwell with the windshield). Use exactly the direction named/preferred. MAY be **missing**.

## Method
1. **Set exactly the named direction.** When the user names one — including a compound combination — set that exact value, not a different single target or a different combination.
2. **Bare request with no pointer → ASK.** "Just change the direction" with no named target and no preference pointer is a genuine open user choice — ask which direction, offer the valid options, and set the value the user supplies.
3. **Request points to a preference → read the preference, then set it.** "The one I like" / "my usual" → read `get_user_preferences` and set the liked direction. When the preference is a *compound* direction, set that compound value — the simpler single-target value is a silent wrong answer.
4. **Confirm what changed and stop.**

### Ask vs. infer (the under-specification crux)
- **Bare request with no pointer → ASK.** Don't guess a direction from a bare request; offer the valid options and act on the answer.
- **Request points to a preference → INFER from `get_user_preferences`.** Read it, then set the liked direction (proposing it for a one-shot confirm is fine). Do NOT ask an open "which direction?" and do NOT pick a different direction yourself — a self-chosen direction the user didn't point to fails. When the preference is compound, set the compound value, not the simpler one.
- **Never re-ask what context already pins.** If the user already named the direction, or the request points to the preference, act on it directly. Only ask when the direction is a genuine open user choice and unresolvable from preference/state.

### When a capability is missing (do the doable, admit the rest)
- **The airflow-direction control is missing.** Do not call `set_fan_airflow_direction` (it errors / doesn't exist). Say plainly you can't change the airflow direction with the controls available, and list the climate controls you DO retain (fan speed, AC, circulation, temperature, defrost) so the answer stays useful. Never claim the direction changed when no working tool could do it.

## Principles
- **Ask vs. infer is decided by the pointer.** "The one I like" / "my usual" = read the preference; a bare "change the direction" = ask. Reading a preference removes the need to ask; never re-ask what context already pins.
- **Never invent the direction.** Whether the source is the user or the preference, the value is supplied — not chosen by you.
- **Honour the exact enum, including compound.** Set the single target or the combination named/preferred; when the enum has a compound variant the user prefers, set that one.
- **Do only what was asked.** Touch only the airflow direction.
- **Fulfil the doable, refuse only the impossible.** Never call a missing tool — it errors; name adjacent controls you still have.

## Common mistakes to avoid
- **Assuming a direction** from a vague bare request instead of asking, or **picking a direction yourself** the user never pointed to.
- **Asking "which direction?"** when the request pointed to the liked/preferred one (read the preference instead).
- **Setting the wrong direction value** — a single target when a combination was named/preferred, or vice versa.
- **Changing fan speed, AC, circulation, or temperature** that was not asked.
- **Claiming the direction changed when no control exists**, or **calling a missing tool "to try it anyway"**.

## Procedure
1. If reporting current state: `get_climate_settings` → report the direction → stop.
2. Named direction (single or compound) → `set_fan_airflow_direction({direction:<the direction the user names>})` if the tool exists.
3. Bare request, no pointer → ask which direction (list options) → `set_fan_airflow_direction({direction:<the answer>})`.
4. "The one I like" / "my usual" → `get_user_preferences` → `set_fan_airflow_direction({direction:<the preferred direction, possibly compound>})`.
5. If the airflow-direction control is missing: do not call it; name what you can't change and the adjacent controls you still have, and stop.
6. Confirm what changed and stop — no loops, no invented direction.
