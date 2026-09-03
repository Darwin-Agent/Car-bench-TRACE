---
name: sunroof
description: Open, close, or position the sunroof (open_close_sunroof takes an opening percentage 0–100). Before any open always read the current sunshade position and the weather: the sunshade must be fully open first (the open is blocked if that control is unavailable), and if the weather is not clear (sunny/cloudy/partly_cloudy) you must obtain the user's explicit "yes" before opening. Resolve an unstated percentage from get_user_preferences when it's a standing default or by asking when it's a genuine user choice (do one, not both; act directly if already known); evaluate any user condition ("if warm enough / unless raining") from that same single weather read; and if the sunroof actuator is absent or a position reads "unknown", do the doable and honestly admit the rest.
tools:
  - get_user_preferences
  - get_sunroof_and_sunshade_position
  - get_weather
  - open_close_sunroof
  - open_close_sunshade
---

# Open / close / position the sunroof

Open, close, or set the sunroof to an opening percentage. Requests range from a fully specified open to ones with an unstated percentage, a weather-conditional open, the mandatory sunshade-open precondition, or a missing control. The same method handles all of these.

## When this applies
- "Open the sunroof to N%" / "close the sunroof" — a fully specified move.
- "Open the sunroof for some fresh air" — no percentage given.
- "Open the sunroof if it's warm enough / unless it's raining" — a conditional open.
- Any sunroof open, which carries the sunshade-fully-open precondition **and** the weather-confirmation gate.

## Tools
- `get_user_preferences()` — read the default opening percentage **only when** the percentage is meant to come from a standing preference.
- `get_sunroof_and_sunshade_position()` — read the current sunroof and sunshade positions; **always read this before any open** to learn whether the sunshade precondition is already met. A field may read `"unknown"` — unverifiable, not a value.
- `get_weather(...)` — read weather for the current location at the current day/time. **Always read it before any open**: it both decides the weather-confirmation gate (see Method step 3) and evaluates any user "if warm/unless raining" condition. Pass only the documented arguments (location id, month, day, hour, optional minutes) — adding an unsupported argument like `year` makes the call error and forces a wasteful retry.
- `open_close_sunroof({percentage})` — set the sunroof opening percentage; `0` is fully closed. May be **missing** in this session.
- `open_close_sunshade({percentage})` — used **only** to satisfy/name the sunshade-open precondition below. The full sunshade method lives in the `sunshade` skill; do not re-teach it here.

## Method
1. **Before opening, gather state once, in parallel:** `get_sunroof_and_sunshade_position()` (always — to learn the sunshade state) and `get_weather(<current location, current day/time>)` (always — for the confirmation gate and any user condition). If the percentage is preference-driven, fetch `get_user_preferences()` in the same batch. Closing the sunroof needs none of this — just close it.
2. **Apply the weather-confirmation gate.** If the weather condition is **not** one of sunny, cloudy, or partly_cloudy (e.g. rain, snow, fog, thunderstorm, hail), opening the sunroof requires the user's **explicit expressive "yes"** first. State the condition, lay out exactly what you'll do (open the sunshade fully, then the sunroof to N%), and wait for confirmation — do not open on this turn. If the weather is clear, no weather confirmation is needed; proceed. This gate is the most common reason an open must pause, so never skip the weather read.
3. **Honour the hard precondition, in order: the sunshade must be fully open before the sunroof opens.** Once cleared to act, bring the sunshade fully open (to 100%) first (the `sunshade` skill owns how), then open the sunroof. The user implicitly accepts this prerequisite — perform it as part of fulfilling the request; don't ask about it separately. Issue the two opens in sequence, sunshade then sunroof, not in parallel.
4. **Act on the sunroof, with the correct argument.** Open vs. close, and the right `percentage` value — don't close when an open was asked, and don't omit the value.

### Resolving an unstated percentage and a conditional open (ask vs. infer)
5. **Pick the percentage source from the request — don't loop on it.**
   - If the request implies a *standing default* (e.g. "open the sunroof" with no value), the percentage is internal: read it from `get_user_preferences` and use that value. Don't ask. (If the preference comes back empty, then it becomes a genuine user choice — ask the percentage.)
   - If the value is a *genuine user choice* and no preference applies, **ask** the percentage and use their answer. Do one, not both.
   - **If your context already contains the percentage (the user stated it, or you already read the preference this turn), act on it directly — do not re-ask or re-read.**
6. **A conditional open → evaluate it ONCE from the weather you already read.** When the open is conditional ("if warm enough", "unless it's raining"), evaluate against the single weather reading and follow the branch it selects. Both branches are real: if the condition fails, don't open (say so plainly); if it holds, continue (and still apply the weather-confirmation gate and the sunshade precondition). Don't re-verify in a loop.

### When a capability is missing
7. **Detect the gap and admit it honestly.**
   - **The sunroof actuator is missing:** the read may still work — report the position, then say plainly you have no control to open or close the sunroof.
   - **The precondition is unsatisfiable:** if the sunshade must be fully open first and the sunshade control is gone, the sunroof open is genuinely **blocked**. Name the precondition and name the missing sunshade control as the blocker; do not open the sunroof anyway and do not pretend it opened. (The sunshade control lives in the `sunshade` skill.)
   - **A position reads `"unknown"`:** treat it as unverifiable; never assume it means zero/closed, never claim a value the tool didn't return, and don't take an action whose safety depends on it. Re-reading won't resolve it.
Do the doable parts in the same answer; refuse only the impossible part, and name the adjacent capability you keep. Note you can still report the weather and the current positions even when you cannot move the sunroof.
8. Confirm what you did (and what you couldn't, with what you'd need to proceed) and stop.

## Principles
- **Sunroof reads can run; opening changes need percentage, weather gate, and sunshade precondition.** Read preferences only when the percentage should come from preference, and always read sunroof/sunshade position plus weather before opening. Call `open_close_sunroof` only when the percentage is explicit, preference-fixed, or chosen; opening the sunshade to 100% is allowed only as the documented prerequisite to an approved sunroof open, while bad weather requires the user's clear confirmation of the full plan before either actuator moves.
- **Always read weather and sunshade position before opening.** These two reads decide the confirmation gate and the precondition; opening without them is the main failure. Closing needs neither.
- **Bad weather gates the open behind an explicit yes.** If the weather isn't sunny, cloudy, or partly_cloudy, get the user's clear confirmation before opening — describe the full plan (sunshade fully open, then sunroof to N%) and wait. A user's later "yes, go ahead anyway" is exactly the confirmation that unblocks it; then proceed in full.
- **Preconditions are part of the job, in order.** Open the sunshade fully first (100%), then the sunroof — no separate confirmation for the prerequisite, and never in parallel.
- **Percentage source matches the request.** Preference-driven → read the preference and don't ask; user-choice → ask and don't read preferences; already-known → just act.
- **Read once, then act.** Read the percentage source, weather, and position a single time; acting is the goal, not re-verifying.
- **A conditional open has two real branches.** Evaluate from one reading and follow it; failing the condition means not opening, not looping.
- **Touch the correct component**, with the correct argument (open vs. close, the right value).
- **Reads are not actuation.** Reporting a position doesn't mean you can move it; keep the two capabilities separate.
- **Never call a missing tool**, and never claim the sunroof moved when it didn't. `"unknown"` means unverifiable.
- **A workaround beats a flat refusal.** Prefer "I can read X / here's the blocker / tell me Z" over a bare "I can't."

## Common mistakes to avoid
- **Skipping the weather read before an open**, or opening in bad weather without first getting the user's explicit yes.
- **Skipping the sunshade-position read** and assuming the precondition is already met.
- **Skipping or reordering the precondition** — opening the sunroof without the sunshade fully open first, or firing both opens in parallel.
- **Asking for the percentage when a preference fixes it**, or guessing a value when it's the user's choice — or **reading the preference when the user already gave the value**.
- **Doing both** — reading the preference *and* asking the user — for one percentage.
- **Spamming preference reads / weather reads / "I couldn't verify" turn after turn** instead of reading once and acting.
- **Collapsing a conditional open to one branch** — always opening, or always refusing, regardless of the reading.
- **Moving the wrong component**, or a **wrong actuator argument** (close when open was asked, omitting the value).
- **Bypassing the precondition when the sunshade control is missing** instead of naming the blocker.
- **Hallucinating success** — claiming the sunroof opened or reached a position when no working tool could do it.
- **Treating `"unknown"` as a known value**, or **dropping the doable parts** by refusing the whole request when some reads/actions were achievable.

## Procedure
1. Identify the target: an explicit percentage, an unstated percentage, or a conditional open. (For a pure close, just call `open_close_sunroof({0})`.)
2. For any open, read in one batch: `get_sunroof_and_sunshade_position()` (always), `get_weather(<current location, current day/time>)` (always), and `get_user_preferences()` only if the percentage is preference-driven.
3. Evaluate any user condition from the weather reading; if it fails, don't open and say so. Resolve the percentage (preference value, or ask the user — not both; act directly if already known).
4. Apply the weather-confirmation gate: if the weather isn't sunny/cloudy/partly_cloudy, present the full plan and get the user's explicit yes before opening; if clear, proceed.
5. Work out the precondition and order: sunshade fully open first (100%, see the `sunshade` skill), then the sunroof. Spot any gap: a missing sunroof actuator, an unsatisfiable precondition (sunshade control gone), or an `"unknown"` field.
6. Issue the opens you genuinely can, in sequence — sunshade fully open first, then `open_close_sunroof({percentage})`. Do not call a missing tool.
7. Confirm what you did, state plainly anything you couldn't and why (name the blocker and what you'd need), then stop — no loops, no fabricated values.
