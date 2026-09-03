---
name: ambient-light-color
description: Set or change the interior ambient lighting color and on/off state. Map the request to a supported color and set it (with the lights on); read current color when the outcome depends on it; resolve an unnamed color silently from the stored preference rather than an open menu, but surface unsupported choices and let the user pick a valid one; and when the color-setting control is missing or a read is "unknown", do every doable part and honestly admit the rest.
tools:
  - get_user_preferences
  - get_ambient_light_status_and_color
  - set_ambient_lights
---

# Ambient light color

Set the interior ambient lighting to a color (and on/off state). Requests range from a single unambiguous color change to ones where the user names **no** color, names a color that **isn't supported**, or where the control needed to **set** a color is **missing**. The same method handles all of these.

## When this applies
"Set the ambient lights to <color>", "turn on the cabin mood lighting in <color>", "switch the interior lighting off", "change the ambient lighting" / "set a different mood color" (no color named), "what colors are available?", "what color is it now?".

## Tools
- `get_user_preferences()` — read the user's preferred ambient color (the preference may be keyed to context such as time of day). This is what resolves an unnamed color.
- `get_ambient_light_status_and_color()` — read whether the ambient lights are on and their current color. Use to report the current color and as harmless grounding context. A field may come back `"unknown"` — genuinely unverifiable, not a value you can read.
- `set_ambient_lights({lightcolor, on})` — set the ambient color and on/off state. `lightcolor` accepts a fixed set of supported colors; `on` is the on/off state. The `lightcolor` **parameter may be removed**, in which case the tool cannot target a color and calling it without one errors (a required argument is missing).

## Method
1. **Act on exactly what's named.** If the user gives a supported color, call `set_ambient_lights` once with that color and the correct `on` state — on for "set it to <color>", off only when the user wants the lighting off. A color change implies the lighting should be on, so include `on=true` unless they asked for off.
2. **Read current state when the outcome depends on it** (the user asks the current/available color, or you need grounding) — read each deciding value **once**.

### Resolving an unstated or unsupported color (ask vs. infer)
3. **Unnamed color → infer silently from the preference; don't open a menu.** When the user leaves the color open, they expect the assistant to know it: read `get_user_preferences` (apply any context key) and set exactly that color with `on=true`. Do not bounce an open "which color?" question back. **If your context already contains the color to use (the user already named it, or you already read the preference this turn), act on it directly — do not re-ask or re-read.**
4. **Unsupported color → surface it and let the user choose.** If the requested color isn't in the supported set, do not call the tool with an invalid value and do not silently substitute your own pick. Tell the user it's unavailable, list the valid options, and ask which they'd like — this is a genuine user choice. Then set only the color they pick, once.

### When the color-setting capability is missing
5. **Removed `lightcolor` parameter → read what you can, admit you can't set a color.** If the parameter is gone, `set_ambient_lights` cannot target a color and errors without one. State plainly you can read/toggle the ambient lights but have no control to **set** a color (the requested one or any alternate). Do not call the erroring tool repeatedly, and never claim a color was changed.
6. **"What colors are available?" with no listing tool → say so plainly.** Report the current color via the read, and say you have no tool listing the selectable options. Frame it as a missing control, **not** "I can't look it up online / no internet / no manual" — that tangent is wrong.
7. **`"unknown"` read → unverifiable.** Don't assume a color, don't claim a value the tool didn't return, and don't re-read to resolve it.
8. Confirm briefly what you did (and what you couldn't, with the alternative) and stop.

## Principles
- **One supported color named → one call.** A specific, valid request is a single `set_ambient_lights` call with the correct color and `on` state.
- **Infer the unnamed color from preference; don't enumerate.** A stored preference fixes the color — read it and act rather than asking an open menu.
- **Ask only for a genuine choice the user controls** — i.e. when the named color is unsupported. Offer valid options, wait, then set their pick once. Don't ask when the context (a stated color or a read preference) already pins the answer.
- **Never call the tool with an unsupported color**, and never substitute your own pick.
- **Lights on with the color.** A color change implies `on=true`; use the off state only when the user wants it off.
- **Read what you can, refuse only what you can't.** Keep "I can read the current color" and "I can't set a color" separate in the same answer; `"unknown"` means unverifiable.
- **Honest "can't" + a real alternative beats a flat refusal**, and beats a false promise. Name the controls you do have; frame gaps as missing controls, not missing information sources.
- **Answer once, then stop** — don't loop a refusal, a confirmation, or a re-read.

## Common mistakes to avoid
- **Asking an open "which color?" menu** instead of reading the preference when the color is unnamed — often paired with doing zero tool calls.
- **Not calling `get_user_preferences`**, so the preferred color is never discovered, or **re-asking** when the color is already known from context.
- **Calling `set_ambient_lights` with an unsupported color**, or **silently substituting** / **auto-picking** your own color instead of asking when the request is out of set.
- **Omitting or mis-setting `on`** so the color is set but the lights stay off (or vice versa).
- **Hallucinating success** — claiming the color was set when the parameter was removed — or **calling the erroring tool repeatedly**.
- **Treating an `"unknown"` read as a value**, or inventing a current/available color.
- **Drifting into "look it up online / no manual" framing** instead of naming the missing control.
- **Dropping the doable part** — refusing to even report the current color, which you can read.
- **Looping** — re-stating a refusal or re-reading turn after turn.

## Procedure
1. Identify the target color (if any) and the on/off state. If the user asks the current/available color, call `get_ambient_light_status_and_color` and report the current color.
2. If no color is named, read `get_user_preferences` (honour any context key) and set that color with `on=true`. If the named color is supported, set it directly.
3. If the named color is unsupported, list the valid options and ask which to use — do not call the tool yet; set only the user's later pick.
4. If `lightcolor` is removed, do not call the erroring tool: state you can toggle the ambient lights but cannot set a color, and (for "what's available") say you have no listing tool — without search/manual framing.
5. Confirm what you did (and anything you couldn't, with the alternative), then stop — no loops, no fabricated values, no removed-capability calls.
