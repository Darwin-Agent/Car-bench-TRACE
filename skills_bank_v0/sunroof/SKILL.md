---
name: sunroof
description: Open, close, or position the sunroof (open_close_sunroof takes an opening percentage). Resolve an unstated percentage by reading get_user_preferences when it's a standing default or by asking when it's a genuine user choice (do one, not both; act directly if already known); evaluate a conditional open ("if warm enough / unless raining") from a single weather read; honour the hard precondition that the sunshade must be fully open first — see the `sunshade` skill — and if that control is gone the open is blocked; and if the sunroof actuator is absent or a position reads "unknown", do the doable and honestly admit the rest.
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
- Any sunroof open, which carries the sunshade-fully-open precondition.

## Tools
- `get_user_preferences()` — read the default opening percentage **only when** the percentage is meant to come from a standing preference.
- `get_sunroof_and_sunshade_position()` — read the current sunroof and sunshade positions; use to learn the sunshade state before an open. A field may read `"unknown"` — unverifiable, not a value.
- `get_weather(...)` — read weather for the relevant place/time when a condition gates the open.
- `open_close_sunroof({percentage})` — set the sunroof opening percentage; `0` is fully closed. May be **missing** in this session.
- `open_close_sunshade({percentage})` — used **only** to satisfy/name the sunshade-open precondition below. The full sunshade method lives in the `sunshade` skill; do not re-teach it here.

## Method
1. **Act on the sunroof, with the correct argument.** Open vs. close, and the right `percentage` value — don't close when an open was asked, and don't omit the value.
2. **Honour the hard precondition, in order: the sunshade must be fully open before the sunroof opens.** Bring the sunshade fully open first (the `sunshade` skill owns how), then open the sunroof. The user implicitly accepts this prerequisite — perform it as part of fulfilling the request; don't ask about it separately.
3. **Read state/weather only when the outcome depends on it, once.** Read positions to learn the sunshade state before an open; read weather one time if a condition gates the open.

### Resolving an unstated percentage and a conditional open (ask vs. infer)
4. **Pick the percentage source from the request — don't loop on it.**
   - If the request implies a *standing default* (e.g. "open the sunroof" with no value), the percentage is internal: read it from `get_user_preferences` and use that value. Don't ask.
   - If the value is a *genuine user choice* and no preference applies, **ask** the percentage and use their answer — and do **not** call `get_user_preferences` at all. Do one, not both.
   - **If your context already contains the percentage (the user stated it, or you already read the preference this turn), act on it directly — do not re-ask or re-read.**
5. **A conditional open → evaluate it ONCE from a real reading.** When the open is conditional ("if warm enough", "unless it's raining"), read weather one time, evaluate, and follow the branch it selects. Both branches are real: if the condition fails, don't open (say so); if it holds, open. Don't re-verify in a loop.

### When a capability is missing
6. **Detect the gap and admit it honestly.**
   - **The sunroof actuator is missing:** the read may still work — report the position, then say plainly you have no control to open or close the sunroof.
   - **The precondition is unsatisfiable:** if the sunshade must be fully open first and the sunshade control is gone, the sunroof open is genuinely **blocked**. Name the precondition and name the missing sunshade control as the blocker; do not open the sunroof anyway and do not pretend it opened. (The sunshade control lives in the `sunshade` skill.)
   - **A position reads `"unknown"`:** treat it as unverifiable; never assume it means zero/closed, never claim a value the tool didn't return, and don't take an action whose safety depends on it. Re-reading won't resolve it.
   Do the doable parts in the same answer; refuse only the impossible part, and name the adjacent capability you keep.
7. Confirm what you did (and what you couldn't, with what you'd need to proceed) and stop.

## Principles
- **Preconditions are part of the job, in order.** Open the sunshade fully first, then the sunroof — no separate confirmation for the prerequisite.
- **Percentage source matches the request.** Preference-driven → read the preference and don't ask; user-choice → ask and don't read preferences; already-known → just act.
- **Read once, then act.** Read the percentage source, weather, and position a single time; acting is the goal, not re-verifying.
- **A conditional open has two real branches.** Evaluate from one reading and follow it; failing the condition means not opening, not looping.
- **Touch the correct component**, with the correct argument (open vs. close, the right value).
- **Reads are not actuation.** Reporting a position doesn't mean you can move it; keep the two capabilities separate.
- **Never call a missing tool**, and never claim the sunroof moved when it didn't. `"unknown"` means unverifiable.
- **A workaround beats a flat refusal.** Prefer "I can read X / here's the blocker / tell me Z" over a bare "I can't."

## Common mistakes to avoid
- **Skipping or reordering the precondition** — opening the sunroof without the sunshade fully open first.
- **Asking for the percentage when a preference fixes it**, or guessing a value when it's the user's choice — or **reading the preference when the user already gave the value**.
- **Doing both** — reading the preference *and* asking the user — for one percentage.
- **Spamming preference reads / weather reads / "I couldn't verify" turn after turn** instead of reading once and acting.
- **Collapsing a conditional open to one branch** — always opening, or always refusing, regardless of the reading.
- **Moving the wrong component**, or a **wrong actuator argument** (close when open was asked, omitting the value).
- **Bypassing the precondition when the sunshade control is missing** instead of naming the blocker.
- **Hallucinating success** — claiming the sunroof opened or reached a position when no working tool could do it.
- **Treating `"unknown"` as a known value**, or **dropping the doable parts** by refusing the whole request when some reads/actions were achievable.

## Procedure
1. Identify the target: an explicit percentage, an unstated percentage, or a conditional open.
2. Read the deciding values once: `get_sunroof_and_sunshade_position()` to learn the sunshade state; `get_weather(<place/time>)` if a condition gates the open; `get_user_preferences()` only if the percentage is preference-driven.
3. Resolve the percentage (preference value, or ask the user — not both; act directly if already known). Evaluate any condition from the single reading; if it fails, don't open.
4. Work out the precondition and order: sunshade fully open first (see the `sunshade` skill), then the sunroof. Spot any gap: a missing sunroof actuator, an unsatisfiable precondition (sunshade control gone), or an `"unknown"` field.
5. Issue the calls you genuinely can, in order — sunshade fully open first, then `open_close_sunroof({percentage})`. Do not call a missing tool.
6. Confirm what you did, state plainly anything you couldn't and why (name the blocker and what you'd need), then stop — no loops, no fabricated values.
