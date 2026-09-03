---
name: climate-air-circulation
description: Set the air-circulation mode (fresh-air / recirculation / auto) — set exactly the mode named, never substituting a "smarter" default; infer an unnamed mode from the stored preference rather than asking or inventing, and never re-ask what context already pins; and when the circulation control is missing, say so plainly and do nothing it can't do.
tools:
  - get_climate_settings
  - get_user_preferences
  - set_air_circulation
---

# Set the air-circulation mode

Switch how the cabin draws air: fresh-air (outside air), recirculation, or auto. The mode may be named outright, or the user may point at "my preferred" circulation without naming it. Sometimes the control is missing. The same method handles all of these.

## When this applies
"Switch to fresh-air / recirculation / auto", "the air feels stuffy, let some outside air in", "set my preferred air circulation". (Turning AC on/off is `climate-air-conditioning`; setting fan speed is `climate-fan-speed`; setting airflow direction is `climate-airflow-direction`.)

## Tools
- `get_climate_settings({})` — read the current circulation mode (and the rest of the climate state). Use it to report current state or confirm what changed.
- `get_user_preferences({})` — read the user's preferred circulation mode (the mode they like). This is what disambiguates an unnamed mode.
- `set_air_circulation({mode})` — set the circulation mode; use exactly the mode named or preferred. MAY be **missing**.

## Method
1. **Set exactly the mode named.** If the user names fresh-air, recirculation, or auto, set that exact mode — not a "smarter" or default substitute.
2. **Unnamed mode → read the preference, then set it.** When the user says "my preferred" / "the one I like" instead of naming the mode, read `get_user_preferences` and set the mode it specifies.
3. **Confirm what changed and stop.** Don't loop a confirmation on a direct, unambiguous command.

### Ask vs. infer (the under-specification crux)
- **Unnamed circulation mode → INFER from the stored preference; do NOT ask, do NOT invent.** When the user expects you to know their preferred mode, read `get_user_preferences` and set the mode it gives. Offering an open "fresh air or auto?" menu, or guessing a default, is the failure. A single confirmation of the preferred value is tolerable, but the value comes from the preference, not a guess.
- **Never re-ask what context already pins.** If the user already named the mode, or it is fixed by the preference, act on it directly — do not ask again. Read the deciding value once, then act; don't loop on preference reads.
- There is no genuine open user choice here beyond the mode itself, and that is either named or fixed by preference — so asking is almost never warranted.

### When a capability is missing (do the doable, admit the rest)
- **The circulation control is missing.** Do not call `set_air_circulation` (it errors / doesn't exist). Read and report the current circulation mode if asked, then say plainly you have no control to change the air-circulation mode, and name the adjacent climate capabilities you DO retain (e.g. AC on/off, fan speed, temperature) so the answer stays useful. Never claim the mode was switched when no working tool could do it.

## Principles
- **Set the exact named/preferred mode.** Hold the mode the user gave, or the one the preference fixes; do not substitute a default.
- **Infer the mode; don't ask.** An unnamed mode is fixed by preference — read it, don't ask, don't invent.
- **Don't re-ask what's already pinned.** A mode the user gave, or one fixed by preference, is acted on directly.
- **Fulfil the doable, refuse only the impossible**, naming the specific blocker. Never call a missing tool; read-only is still useful ("I can read the current mode but can't change it").

## Common mistakes to avoid
- **Substituting the mode** (auto/recirculation when fresh-air was named, or vice versa).
- **Asking which mode / inventing one** instead of reading the preference for an unnamed mode.
- **Re-asking a mode the user already gave** or one resolvable from preference.
- **Hallucinating success** (claiming the mode switched when no working tool could do it), or **calling a missing tool**.

## Procedure
1. If reporting current state: `get_climate_settings` → report the mode → stop.
2. Named mode → `set_air_circulation({mode:<the mode the user names>})`.
3. Unnamed ("my preferred") mode → `get_user_preferences` → `set_air_circulation({mode:<the preferred mode>})`.
4. If the circulation control is missing: do not call it; report the current mode if asked, name what you can't change and the adjacent controls you still have, and stop.
5. Confirm what changed and stop — no loops, no invented mode.
