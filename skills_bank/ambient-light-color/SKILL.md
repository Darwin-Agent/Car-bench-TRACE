---
name: ambient-light-color
description: Set or change the interior ambient (cabin "mood"/"surrounding") lighting color and on/off state, including matching it to the car's exterior color. Map the request to a supported color and set it (with the lights on); for "match my car color" read the exterior color first then set the matching ambient color; resolve an unnamed color silently from the stored preference rather than an open menu, but surface unsupported choices and let the user pick a valid one; and when the color-setting control is missing or a needed read is "unknown", do every doable part and honestly admit the rest. Not for reading lights, headlights, or fog lights.
tools:
  - get_user_preferences
  - get_car_color
  - get_ambient_light_status_and_color
  - set_ambient_lights
---

# Ambient light color

Set the interior ambient lighting to a color (and on/off state). Requests range from a single unambiguous color change, to "match the ambient lights to my car's exterior color" (the color is derived from a read, not stated), to ones where the user names **no** color, names a color that **isn't supported**, or where the control needed to **set** a color is **missing**. The same method handles all of these.

## When this applies
"Set the ambient lights to <color>", "turn on the cabin mood lighting in <color>", "match the interior ambient lighting to my car's exterior color", "switch the interior lighting off", "change the ambient lighting" / "set a different mood color" (no color named), "what colors are available?", "what color is it now?". This skill is only for the soft decorative cabin lighting. A bare "adjust the lights" / "it's getting dark" names no specific light — ambient, reading lights, and exterior headlights/fog lights are different controls, so ask which the user means before assuming this one. Seat reading lights and exterior lighting are separate skills.

## Tools
- `get_user_preferences()` — read the user's preferred ambient color (the preference may be keyed to context such as time of day). This is what resolves an unnamed color.
- `get_car_color()` — read the car's **exterior** color. This is what resolves a "match my car color" request. The color field may come back `"unknown"` — genuinely unverifiable, so you cannot derive a matching color from it.
- `get_ambient_light_status_and_color()` — read whether the ambient lights are on and their current color. Use to report the current color and as harmless grounding context. A field may come back `"unknown"` — genuinely unverifiable, not a value you can read.
- `set_ambient_lights({lightcolor, on})` — set the ambient color and on/off state. `lightcolor` accepts a fixed set of supported colors; `on` is the on/off state. Before relying on it to set a color, verify the color argument is actually present in the tool's schema: if it isn't, the tool can only toggle on/off and any attempt to set a color will error on a missing required argument — treat that as no color-setting capability.

## Method
1. **Act on exactly what's named.** If the user gives a supported color, call `set_ambient_lights` once with that color and the correct `on` state — on for "set it to <color>", off only when the user wants the lighting off. A color change implies the lighting should be on, so include `on=true` unless they asked for off.
2. **Read current state when the outcome depends on it** (the user asks the current/available color, or you need grounding) — read each deciding value **once**.

### Matching the car's exterior color
3. **"Match my car color" → read the exterior color first, then set the matching ambient color.** The color is not stated; derive it. Call `get_car_color`, then if the returned color is in the supported ambient set, call `set_ambient_lights` once with that color and `on=true`. Do this silently — don't ask the user what color the car is (the read answers it) and don't ask permission to proceed with the obvious match. If the car's color has no exact ambient equivalent, name the closest/available options and let the user pick rather than guessing.

### Resolving an unstated or unsupported color (ask vs. infer)
4. **Unnamed color → infer silently from the preference; don't open a menu.** When the user leaves the color open, they expect the assistant to know it: read `get_user_preferences` (apply any context key) and set exactly that color with `on=true`. Do not bounce an open "which color?" question back. **If your context already contains the color to use (the user already named it, or you already read the preference this turn), act on it directly — do not re-ask or re-read.**
5. **Unsupported color → surface it and let the user choose.** If the requested color isn't in the supported set, do not call the tool with an invalid value and do not silently substitute your own pick. Tell the user it's unavailable, list the valid options, and ask which they'd like — this is a genuine user choice. Then set only the color they pick, once. **First confirm you actually have a color-setting control:** if that capability is absent (see below), don't offer a "pick another color" menu — any pick would be unfulfillable, and offering one leads to promising a set you can't perform.

### When the color-setting capability is missing
6. **No color-setting control → read what you can, admit you can't set *any* color.** When the tool can only toggle on/off and cannot target a color (the color argument is absent from its schema, so a color call errors), the limitation is global: it blocks the requested color **and** every alternate, so this is not the "pick another supported color" case. Still complete the doable read part (e.g. report the car's exterior color or the current ambient color), then state plainly you can read/toggle the ambient lights but have no control to **set** a color. Do not offer a palette to choose from (a pick can't be honoured), do not promise to set a color the user names, and don't claim the lights were turned on if the call errored. Do not call the erroring tool repeatedly, and never claim a color was changed — even after the user later names one.
7. **"What colors are available?" with no listing tool → say so plainly.** Report the current color via the read, and say you have no tool listing the selectable options. Frame it as a missing control, **not** "I can't look it up online / no internet / no manual" — that tangent is wrong.
8. **`"unknown"` read → unverifiable.** Don't assume a color, don't claim a value the tool didn't return, and don't re-read to resolve it. If the car's exterior color reads `"unknown"`, you cannot derive a match — say so and offer the supported palette for the user to pick from instead.
9. Confirm briefly what you did (and what you couldn't, with the alternative) and stop.

## Principles
- **Ambient-light reads can run; color changes need a pinned color and on/off intent.** Read `get_user_preferences`, `get_car_color`, and `get_ambient_light_status_and_color` directly when they resolve an unnamed color, a "match my car" request, or a status question. Call `set_ambient_lights` only when the requested color is supported, a read pins the color, or the user has chosen from the valid palette; if setting the color would require substituting your own color, toggling lights the user did not mention, or relying on a missing color parameter, ask or refuse instead of acting.
- **One supported color named → one call.** A specific, valid request is a single `set_ambient_lights` call with the correct color and `on` state.
- **Derive, don't ask, when a read pins the color.** For "match my car color", `get_car_color` answers what color to use — read it once and set the match silently; asking the user what color their car is, or asking permission for the obvious match, is the failure. Same for an unnamed color fixed by a preference.
- **Infer the unnamed color from preference; don't enumerate.** A stored preference fixes the color — read it and act rather than asking an open menu.
- **Ask only for a genuine choice the user controls** — i.e. when the named color is unsupported. Offer valid options, wait, then set their pick once. Don't ask when the context (a stated color or a read preference) already pins the answer.
- **Never call the tool with an unsupported color**, and never substitute your own pick.
- **Lights on with the color.** A color change implies `on=true`; use the off state only when the user wants it off.
- **Read what you can, refuse only what you can't.** Keep "I can read the current color" and "I can't set a color" separate in the same answer; `"unknown"` means unverifiable.
- **Honest "can't" + a real alternative beats a flat refusal**, and beats a false promise. Name the controls you do have; frame gaps as missing controls, not missing information sources.
- **Answer once, then stop** — don't loop a refusal, a confirmation, or a re-read.

## Common mistakes to avoid
- **Asking the user what color their car is** for a "match my car" request instead of calling `get_car_color`, or asking permission before setting the obvious match.
- **Asking an open "which color?" menu** instead of reading the preference when the color is unnamed — often paired with doing zero tool calls.
- **Assuming this skill for a vague "adjust the lights"** request — confirm whether they mean ambient, reading, or exterior lights first.
- **Not calling `get_user_preferences`**, so the preferred color is never discovered, or **re-asking** when the color is already known from context.
- **Calling `set_ambient_lights` with an unsupported color**, or **silently substituting** / **auto-picking** your own color instead of asking when the request is out of set.
- **Omitting or mis-setting `on`** so the color is set but the lights stay off (or vice versa).
- **Hallucinating success** — claiming the color was set when there's no color-setting control — or **calling the erroring tool repeatedly**. Especially: offering a "pick another supported color" menu when the control to set a color is missing, then "confirming" the user's pick without a successful call — the gap blocks every color, so admit it instead of routing into a choice you can't fulfil.
- **Treating an `"unknown"` read as a value**, or inventing a current/available/car color — when the exterior color is unverifiable, offer the palette instead of guessing a match.
- **Drifting into "look it up online / no manual" framing** instead of naming the missing control.
- **Dropping the doable part** — refusing to even report the current color, which you can read.
- **Looping** — re-stating a refusal or re-reading turn after turn.

## Procedure
1. Identify the target color (if any) and the on/off state. If the user asks the current/available color, call `get_ambient_light_status_and_color` and report the current color. If the request is a vague "adjust the lights", first confirm they mean the ambient lights.
2. If the request is "match my car color", call `get_car_color`; if the returned color is supported, set it with `on=true`. If it reads `"unknown"`, say you can't verify it and offer the supported palette.
3. If no color is named, read `get_user_preferences` (honour any context key) and set that color with `on=true`. If the named color is supported, set it directly.
4. If the named color is unsupported, list the valid options and ask which to use — do not call the tool yet; set only the user's later pick.
5. If there is no color-setting control, do not claim success and do not offer a palette to pick from (no pick can be honoured): complete any doable read, then state you can toggle the ambient lights but cannot set any color, and (for "what's available") say you have no listing tool — without search/manual framing.
6. Confirm what you did (and anything you couldn't, with the alternative), then stop — no loops, no fabricated values, no removed-capability calls.
