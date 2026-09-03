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
- `get_climate_settings({})` — read the current circulation mode (and the rest of the climate state). Use it only to *report* current state; it is NOT a required precondition for setting the mode. Verify it is callable, and read its fields honestly — a field returned as `"unknown"` is unverifiable, not a real value.
- `get_user_preferences({})` — read the user's preferred circulation mode (the mode they like). This is what disambiguates an unnamed mode.
- `set_air_circulation({mode})` — set the circulation mode (FRESH_AIR / RECIRCULATION / AUTO); use exactly the mode named or preferred. Setting it is a direct write with no precondition and is independent of AC / window / fan state — so it does not require reading or changing those first.

## Method
1. **Set exactly the mode named.** If the user names fresh-air, recirculation, or auto, set that exact mode directly — not a "smarter" or default substitute, and without first reading climate state you don't need.
2. **Unnamed mode → read the preference, then set it.** When the user says "my preferred" / "the one I like" instead of naming the mode, read `get_user_preferences` and set the mode it specifies.
3. **Confirm what changed and stop.** Don't loop a confirmation on a direct, unambiguous command.

### Ask vs. infer (the under-specification crux)
- **Unnamed circulation mode → INFER from the stored preference; do NOT ask, do NOT invent.** When the user expects you to know their preferred mode, read `get_user_preferences` and set the mode it gives. Offering an open "fresh air or auto?" menu, or guessing a default, is the failure. A single confirmation of the preferred value is tolerable, but the value comes from the preference, not a guess.
- **Never re-ask what context already pins.** If the user already named the mode, or it is fixed by the preference, act on it directly — do not ask again. Read the deciding value once, then act; don't loop on preference reads.
- **Informational/options questions are NOT a call for action — answer, don't act.** When the user only asks "what's the best way to improve the air?", "the air feels stagnant, what are my options?", or "what's it set to?", present the options (fresh air, auto, raise fan, etc.) and/or report the current state, then stop. Do not proactively call `set_air_circulation` or any state-changing tool — wait for an explicit "do it" ("switch to fresh air", "get some air flowing"). Likewise "prepare to …" is not yet a call to act on that step. Acting on a question is over-acting.
- There is no genuine open user choice here beyond the mode itself, and that is either named or fixed by preference — so asking is almost never warranted.
- **In a combined request, change only what's asked plus what a tool strictly requires.** When setting circulation rides along with another action (e.g. "turn on AC and set fresh air"), perform exactly the circulation change you own and let the other operation handle its own minimal preconditions. Do not pre-emptively nudge fan speed, temperature, or other actuators to a temporary value the user never requested — an unsolicited intermediate change is a failure even when the final state ends up correct, especially since a later turn may set that actuator differently.

### When a capability is missing (do the doable, admit the rest)
A capability can be absent three ways — verify before relying on any of them, and respond honestly to each:
- **No working control to set the mode.** If you cannot call the tool that changes circulation, do not invent a call. Read and report the current mode if asked, then say plainly you have no control to change the air-circulation mode, and name the adjacent climate capabilities you DO retain (e.g. AC on/off, fan speed, temperature) so the answer stays useful. Never claim the mode was switched when no working tool could do it.
- **A read comes back `"unknown"`.** Treat it as genuinely unverifiable — never assume it means a particular mode, off, or zero, and never re-read in a loop expecting a value. Crucially, an `"unknown"` field in the climate read must NOT block simply setting the named or preferred mode, since the write needs no precondition; just set it and, if you were asked to report current state, say that field couldn't be read rather than guessing.
- **A needed argument is unavailable.** If the tool is callable but a required parameter is gone from its schema, don't invoke the erroring call; state the specific limitation and offer what you can still do.

## Principles
- **Circulation reads can run; mode changes must be exactly pinned.** Read `get_climate_settings` to report the current mode and `get_user_preferences` to resolve an unnamed preferred mode without asking. Call `set_air_circulation` only when the user named FRESH_AIR/RECIRCULATION/AUTO or the preference read fixes that exact mode; do not change AC, windows, fan, airflow, temperature, or any other climate setting as a side effect of circulation.
- **Set the exact named/preferred mode.** Hold the mode the user gave, or the one the preference fixes; do not substitute a default.
- **Infer the mode; don't ask.** An unnamed mode is fixed by preference — read it, don't ask, don't invent.
- **Don't re-ask what's already pinned.** A mode the user gave, or one fixed by preference, is acted on directly.
- **Fulfil the doable, refuse only the impossible**, naming the specific blocker. Never call a missing tool; read-only is still useful ("I can read the current mode but can't change it").

## Common mistakes to avoid
- **Substituting the mode** (auto/recirculation when fresh-air was named, or vice versa).
- **Asking which mode / inventing one** instead of reading the preference for an unnamed mode.
- **Re-asking a mode the user already gave** or one resolvable from preference.
- **Over-reading before a direct write** — gathering climate/window/fan state you don't need before setting a plainly named mode. Setting circulation has no precondition; just set it.
- **Acting on an informational or "prepare to" request** — switching circulation (or any setting) when the user only asked what the options are, what the current state is, or to "prepare" a later step. Answer or report, then wait for the explicit call to act.
- **Letting an `"unknown"` read block or distort the action** — assuming what the masked value is, treating it as a real current mode, or refusing to set the mode because a field couldn't be read.
- **Hallucinating success** (claiming the mode switched when no working tool could do it), or **calling a tool/argument that isn't actually available**.
- **Adding an unrequested intermediate actuator change** — bumping fan speed, temperature, or another setting to a temporary value the user never asked for, even as a supposed "prerequisite" for a sibling action. Touch only what the user requested and what a tool strictly requires; preserve the user's intent for everything else.

## Procedure
1. If reporting current state: `get_climate_settings` → report the mode → stop.
2. Named mode → `set_air_circulation({mode:<the mode the user names>})`.
3. Unnamed ("my preferred") mode → `get_user_preferences` → `set_air_circulation({mode:<the preferred mode>})`.
4. If the circulation control is missing: do not call it; report the current mode if asked, name what you can't change and the adjacent controls you still have, and stop.
5. Confirm what changed and stop — no loops, no invented mode.
