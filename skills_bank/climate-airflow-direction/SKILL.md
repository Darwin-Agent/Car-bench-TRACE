---
name: climate-airflow-direction
description: Set the fan airflow direction — set exactly the named direction (single or compound) verbatim; when no direction is named (a bare "change the direction" or "the air blowing at me, which I don't like — change it"), read the stored preference FIRST and set it, asking the user only if no preference resolves the choice; never re-ask what context already pins; and when the airflow-direction control is missing, say so plainly and name the controls you still have.
tools:
  - get_climate_settings
  - get_user_preferences
  - set_fan_airflow_direction
---

# Set the fan airflow direction

Redirect where the cabin air blows. The direction may be named outright (a single target such as feet, head, or windshield, or a compound combination), left unnamed (a bare "change the direction", or a complaint about the current direction with no replacement named), or pointed at the user's stored preference. Sometimes the control is missing. The same method handles all of these.

## When this applies
"Point the air at my feet / the windshield", "blow toward the feet and the windshield", "change the fan airflow direction", "the air's blowing at my face and I don't like it — change it", "point the air the way I like it / my usual direction". (Setting fan speed is `climate-fan-speed`; turning AC on is `climate-air-conditioning`; setting the circulation mode is `climate-air-circulation`.)

## Tools
- `get_climate_settings({})` — read the current airflow direction (and the rest of the climate state); use to report state or confirm what changed.
- `get_user_preferences({})` — read the user's liked airflow direction when the request points to a preference ("the direction I like", "my usual"). The preference MAY be a compound direction.
- `set_fan_airflow_direction({direction})` — set the airflow direction; the vocabulary covers single targets and compound combinations (e.g. one that bundles the footwell with the windshield). Use exactly the direction named/preferred. MAY be **missing**.

## Method
1. **Direction named → set it exactly.** When the user names one — including a compound combination — set that exact value, not a different single target or a different combination. No preference read needed.
2. **Direction NOT named → read the stored preference FIRST, before asking.** Whenever the new direction is unnamed — a bare "just change it", or a complaint about the current direction ("the air's at my face, I don't like it, change it") with no replacement named — call `get_user_preferences({vehicle_settings:{climate_control}})` before deciding. If it pins a liked airflow direction, set that (proposing it for a quick confirm is fine). When the preference is *compound*, set the compound value — the simpler single-target value is a silent wrong answer.
3. **Only ask the user if no preference resolves it.** If the preference read returns nothing about airflow direction, then the choice is genuinely the user's — ask which direction and offer the valid options, and set the value the user supplies.
4. **Confirm what changed and stop.**

### Ask vs. infer (the under-specification crux)
- **The disambiguation order is preference THEN ask — never skip step one.** For any unnamed direction, a learned preference outranks a clarifying question. Jumping straight to "which direction?" without first reading the preference is the central failure here: when a liked direction is stored, asking re-litigates a choice the user already settled. Read `get_user_preferences` first; only fall back to asking when it leaves the choice open.
- **A complaint about the current direction is still an unnamed-direction request.** "The air's blowing at my face, I don't like it" is not a named target — it's a request to change to something the user hasn't stated, so the preference governs it exactly like a bare "change the direction". Don't treat the disliked current direction as a reason to ask immediately.
- **Infer, but never invent.** Set the liked direction from the preference, or the value the user gives — do NOT pick a direction yourself that neither the user nor the preference pointed to. A self-chosen direction is a wrong answer even if plausible.
- **Never re-ask what context already pins.** If the user already named the direction, or the preference resolves it, act directly. Only ask when the direction is a genuine open user choice unresolvable from preference/state.

### When a capability is missing (do the doable, admit the rest)
- **The airflow-direction control is missing.** Do not call `set_fan_airflow_direction` (it errors / doesn't exist). Say plainly you can't change the airflow direction with the controls available, and list the climate controls you DO retain (fan speed, AC, circulation, temperature, defrost) so the answer stays useful. Never claim the direction changed when no working tool could do it.
- **A co-requested control is missing while airflow is doable.** When one message bundles the airflow change with another climate change (e.g. "point it at my feet and turn the fan up") and only the *other* control is unavailable, still set the airflow direction — fulfil the doable part — and in the same answer name the part you couldn't do and why. Don't refuse the whole request because one piece is blocked, and don't silently drop the blocked piece.
- **Verify before claiming, not by guessing.** Confirm what actually changed from the tool result you got back; if a call errored or a control wasn't callable, report that honestly rather than narrating success for it.
- **Never announce "done" without the actual call.** Once the user supplies (or the preference pins) the direction, your very next action is the real `set_fan_airflow_direction` call — saying "I've set it to the windshield" without that successful call in the same turn is a fabricated success, even though the tool was available. The spoken confirmation must follow a tool result, never replace it.

## Principles
- **Airflow reads can run; direction changes must name or derive the exact enum.** Read current climate state for status and read preferences when the user asks for their usual/liked direction. Call `set_fan_airflow_direction` only when the direction is explicitly named or preference-fixed, including compound windshield/footwell variants; do not change fan speed, AC, temperature, circulation, or defrost unless another explicit skill rule or user request covers that action.
- **Unnamed direction → preference first, ask last.** Any request that doesn't name the target — whether phrased "the one I like", a bare "change it", or a complaint about the current direction — gets the preference read before any question. The stored preference outranks asking; reading it removes the need to ask. Only ask when the preference leaves the choice open.
- **Never invent the direction.** Whether the source is the user or the preference, the value is supplied — not chosen by you.
- **Honour the exact enum, including compound.** Set the single target or the combination named/preferred; when the enum has a compound variant the user prefers, set that one.
- **Do only what was asked.** Touch only the airflow direction.
- **Fulfil the doable, refuse only the impossible.** Never call a missing tool — it errors; name adjacent controls you still have.

## Common mistakes to avoid
- **Asking "which direction?" without first reading the stored preference** when the direction is unnamed — including when the user only complained about the current direction. The preference outranks the question; skip it and you ask for something the user already settled. Read `get_user_preferences` first, every time the target isn't named.
- **Treating "I don't like the current direction, change it" as a reason to ask** rather than an unnamed-direction request the preference should resolve.
- **Assuming a direction** from a vague request, or **picking a direction yourself** that neither the user nor the preference pointed to.
- **Setting the wrong direction value** — a single target when a combination was named/preferred, or vice versa.
- **Changing fan speed, AC, circulation, or temperature** that was not asked.
- **Saying "done, airflow set" without actually calling `set_fan_airflow_direction`** once the direction is known — the call must succeed before you confirm. The confirmation describes a tool result; it cannot stand in for the call.
- **Claiming the direction changed when no control exists**, or **calling a missing tool "to try it anyway"**.
- **Refusing or stalling the whole request because a co-requested control is unavailable** — set the airflow direction you CAN set, and report only the blocked piece.

## Procedure
1. If reporting current state: `get_climate_settings` → report the direction → stop.
2. Named direction (single or compound) → `set_fan_airflow_direction({direction:<the direction the user names>})` if the tool exists.
3. Direction NOT named (bare "change it", "the one I like", or a complaint with no replacement named) → `get_user_preferences({vehicle_settings:{climate_control}})` FIRST → if it pins a direction, `set_fan_airflow_direction({direction:<the preferred direction, possibly compound>})`.
4. Only if no preference resolves it → ask which direction (list options) → `set_fan_airflow_direction({direction:<the answer>})`.
5. If the airflow-direction control is missing: do not call it; name what you can't change and the adjacent controls you still have, and stop.
6. Confirm what changed and stop — no loops, no invented direction.
