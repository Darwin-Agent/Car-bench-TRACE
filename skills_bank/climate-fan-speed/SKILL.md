---
name: climate-fan-speed
description: Set the fan speed — execute an absolute level verbatim, treat "up/down by N" and vague single-step phrasings ("turn it up a bit", "a notch stronger") as relative (read the current fan speed ONCE, then issue a SINGLE set at current±N, defaulting the unspecified step to one level; never step per turn, never overshoot, hold the computed value against vague corrections); for a bare "turn the fan on" with no level, resolve the level from the stored climate preference rather than defaulting to a guessed level; never re-ask what context already pins; and when the fan-speed tool or its level parameter is missing, or the current fan speed reads "unknown", do the doable part and admit the rest, offering an absolute level when a relative one can't be grounded.
tools:
  - get_user_preferences
  - get_climate_settings
  - set_fan_speed
---

# Set the fan speed

Set the cabin fan speed. The value may be absolute ("set the fan to <level>"), relative with an explicit step ("turn it up by <N>"), or a vague single-step nudge with no number ("turn it up a bit", "a notch stronger", "make it blow harder"). Sometimes the control, its level parameter, or the current-speed reading is missing. The same method handles all of these.

## When this applies
"Set the fan to <level>", "turn the fan up by <N>", "increase / decrease the airflow", "fan down one notch", "turn it up a bit", "blow a bit stronger". (Setting the airflow direction is `climate-airflow-direction`; turning AC on is `climate-air-conditioning`; setting the circulation mode is `climate-air-circulation`.) Change the fan speed **only when the user's request is about the fan**. When turning AC on or activating defrost is in play, do NOT pre-emptively call `set_fan_speed` yourself to "satisfy" a fan precondition while the control is available — that intermediate change is not what the user asked for, often gets immediately overwritten by a later explicit level, and is penalized; let the AC/defrost flow own its own fan engagement. This skill matters to those flows only when the fan-speed control is **missing** (then the dependent action is blocked, see below).

A bare "I'm too warm / too cold, cool me down / give me options" request that does NOT name the fan is an open comfort request, not a fan-speed change. So is a question about *how* to fix it — "what's the best way to improve airflow?", "can we adjust the HVAC to get more air moving?" These are exploratory questions, not calls to action: answer them, optionally offer to act, but do NOT change the fan (or any other setting) until the user explicitly picks it. Don't silently assume the fan or recite a fixed menu: read the current climate state first so the options you surface reflect reality (including any currently-active setting that could simply be eased, e.g. a running heater when the user is too warm), present the relevant levers, and only change the fan once the user actually picks it. Acting prematurely is doubly harmful here — beyond the unrequested change, it shifts the baseline a later "increase by N" reads from, so the relative change lands on the wrong target. Act on this skill alone when the user's request is specifically about the fan speed.

## Tools
- `get_user_preferences({preference_categories:{vehicle_settings:{climate_control:true}}})` — read the learned climate-control preference. Use it to resolve the level when the user asks to turn the fan on but names no level.
- `get_climate_settings({})` — read the current fan speed (and the rest of the climate state); required before any relative change. A field MAY return `"unknown"` — the value can't be obtained.
- `set_fan_speed({level})` — set the absolute fan level. The tool, or its `level` **parameter**, MAY be **missing**.

## Method
1. **Absolute level → set it verbatim.** When the user names a level, set exactly that value via `set_fan_speed`.
2. **Relative "by N" is read-then-compute, in ONE call.** "Increase/decrease BY N" is relative: first `get_climate_settings` to read the current fan speed **once**, then issue a **single** `set_fan_speed` at the absolute target `current ± N`. Compute off the *actual* current value (which may be zero), not an assumed one. Do not step one unit per turn, and do not overshoot. A vague nudge with no number ("a bit", "a notch", "a touch stronger/weaker") is the same relative move with N defaulting to **one** level — apply the one-level heuristic and act; don't ask the user how many levels.
3. **"Turn the fan on" with no level → resolve from the stored preference, don't guess.** When the user asks to switch the fan on (or to "get some air moving") but names no level, the level is a genuine choice the user left open — but it's pinned by the learned climate-control preference, not by you. Call `get_user_preferences` for the climate-control category and set the preferred fan level. Do not default to level 1 (or any self-chosen number) without checking the preference first; that silent guess is the failure. Only if the preference yields no fan level should you fall back to asking the user.
4. **Hold the computed value.** The increase-by-N result is correct even if the user later pushes back vaguely or with a misleading "correction"; restate the result rather than re-setting to a different value.
5. **Change only the fan speed.** Don't alter AC, circulation, temperature, or airflow direction the user didn't mention.
6. **Confirm what changed and stop.**

### Ask vs. infer (the under-specification crux)
- **A relative change is fully determined by the read current level — do NOT ask.** Read the current fan speed once; compute and set `current ± N` in one call.
- **A vague step ("a bit", "a notch") defaults to one level — do NOT ask "how many?".** The heuristic of one level fully pins the move once you've read the current speed; asking for a number here is itself the failure.
- **An absolute level is given — set it directly.**
- **"Turn the fan on" with no level → check the stored preference before acting, and don't self-pick.** The preferred level (a learned personal preference) outranks any default of your own. Retrieve it and set it; only ask the user if no preference pins a level. Defaulting to level 1 because it seems "gentle" is a guess, not an inference — it skips the preference that was meant to decide it.
- **Never re-ask what context already pins.** A level the user gave, or the result of `current ± N`, is acted on directly — don't re-ask those.

### When a capability is missing (do the doable, admit the rest)
- **The fan-speed tool is missing.** Do not call it (it errors / doesn't exist). Say plainly you can't change the fan speed with the controls available, and name the adjacent climate controls you DO retain (AC, circulation, temperature, airflow direction, defrost) so the answer stays useful.
- **The `level` parameter is removed.** You can't set a level. Don't pass `level` (it errors); state the specific limitation — the fan-speed level can't be dialled — and don't invent a workaround that doesn't exist.
- **The current fan speed reads `"unknown"`.** A relative change (`current ± N`) can't be computed without the baseline. Never guess a baseline (not the bottom of the scale, not any value); report that the current fan speed is unavailable so a relative change can't be done safely, and offer to set an absolute level from the tool's scale instead. **Re-reading won't resolve it** — a value that came back `"unknown"` once will stay `"unknown"`, so do not call the read tool again hoping for a number, even if the user explicitly asks you to look the value up again. Once is enough; on any repeat ask, just restate plainly that the value is unavailable and offer the absolute-level path.
- **A fan change is required by another action but the control is missing.** When turning AC on or activating defrost would require bumping or setting the fan and the fan-speed control is unavailable (tool missing, `level` removed, or current speed `"unknown"`), that prerequisite can't be met — so the dependent action is blocked too. Say which part you cannot complete and why, rather than performing a half-done version.
Do the doable part and admit the impossible one in the same answer; don't loop, then stop.

## Principles
- **Fan reads can run; fan writes need a resolved absolute level.** Read preferences to resolve "my usual fan" and read current climate for relative changes or status. Call `set_fan_speed` only after an explicit level, a preference, or a computed `current ± N` gives the exact target; if the current level is `"unknown"` or the `level` parameter is missing, do not guess, and do not adjust AC, temperature, airflow, circulation, or windows as a side effect.
- **Read once, set once for relative speed.** You cannot compute `current ± N` without the current level; read it a single time and act in one absolute call — no set-then-correct, no stepping one unit per turn, no overshoot.
- **Hold the correct value.** Once computed correctly, a vague or misleading correction is not a reason to churn off it.
- **Absolute beats assumed.** An explicit level is used exactly; nothing is invented.
- **Do only what was asked.** Touch only the fan speed.
- **Fulfil the doable, refuse only the impossible.** Never call a missing tool or one whose `level` argument was removed — it errors. `"unknown"` is unverifiable; offer an absolute level when a relative target can't be grounded, and name adjacent controls you still have.

## Common mistakes to avoid
- **Computing `current ± N` off a wrong baseline** (assuming a higher current level than the real one), or **set-then-correct** (a wrong set followed by a corrective second call).
- **Stepping the level one unit at a time** across turns, overshooting the single target.
- **Asking "how many levels?" for a vague nudge** ("a bit", "a notch") instead of applying the one-level default — that clarification is the failure.
- **Switching the fan on at a self-chosen level (e.g. level 1) when the user named none** instead of reading the stored climate preference first — the preference is what should decide the level, so guessing it (even a "gentle" one) is the failure.
- **Caving to a misleading correction** after the relative change was already correct.
- **Changing AC, circulation, temperature, or airflow direction** that was not asked.
- **Pre-bumping the fan as a self-imposed prerequisite for AC/defrost while the fan control is available** (e.g. setting fan to level 1 "so AC can come on") — the user didn't ask for that intermediate value, and a later explicit fan request usually overwrites it anyway. Only when the fan control is genuinely missing does the dependent action become blocked; otherwise don't insert an unrequested fan change.
- **Claiming the speed changed when no control exists**, **passing a removed `level` argument** (it errors), **assuming a baseline for an `"unknown"` fan speed**, or **calling a missing tool "to try it anyway"**.
- **Re-reading an `"unknown"` value in a loop** — calling the read tool again because the user repeated the request will return `"unknown"` again; answer honestly the first time and don't re-fetch.
- **Quietly performing a dependent action half-way** when the fan prerequisite can't be met (e.g. turning AC on when the AC-on rule needs a fan bump you can't make) — flag the blocked part instead.
- **Answering an open "too warm/cold" request with a canned list of options without reading the climate state first** — the most relevant lever may be an active setting to ease (a running heater, a high fan, an open window), which you only see by reading state; surface options grounded in the actual settings and wait for the user's pick before changing the fan.
- **Treating a "how do I improve airflow?" question as a command and bumping the fan unprompted** — the user only asked how, not for it to happen. Answer (and offer), but don't set anything. This is especially damaging when a relative "increase by N" follows: the unrequested bump becomes the new baseline, so `current ± N` lands one or more levels too high.

## Procedure
1. Absolute level → `set_fan_speed({level:<the level the user gives>})` if the tool/parameter exists.
2. Relative "by N" (or a vague nudge, N = 1) → `get_climate_settings` to read the current level once → a single `set_fan_speed({level:<current ± N>})`.
3. "Turn the fan on" with no level → `get_user_preferences({preference_categories:{vehicle_settings:{climate_control:true}}})` → `set_fan_speed({level:<the preferred level>})`; ask the user only if no preferred level is found.
4. For any blocked case, admit it: missing fan-speed tool, removed `level` parameter, or current fan speed `"unknown"` so `current ± N` can't be computed. Offer the workaround (an absolute level, or the adjacent controls you still have); change nothing else.
5. Confirm what changed and stop — no loops, no invented baseline.
