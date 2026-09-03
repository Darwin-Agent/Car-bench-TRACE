---
name: sunshade
description: Open, close, position, or sync the sunshade (open_close_sunshade takes an opening percentage). Execute directly when a plain percentage is given; resolve an unstated percentage by reading get_user_preferences when it's a standing default or by asking when it's a genuine user choice (do one, not both); for ANY "match/synchronise the sunshade to the sunroof" request — even one that also names a number — read get_sunroof_and_sunshade_position FIRST and set the sunshade to the sunroof's actual read value (the sunshade is the component that moves; the read is mandatory and not skippable just because a number was stated); and if the whole tool is absent, its position parameter is removed (every call errors), or a position reads "unknown", do the doable and honestly admit the rest.
tools:
  - get_user_preferences
  - get_sunroof_and_sunshade_position
  - get_weather
  - open_close_sunshade
---

# Open / close / position / sync the sunshade

Open, close, set the sunshade to a position, or synchronise it to the sunroof. Requests range from a fully specified open to an unstated percentage, a "match the sunroof" sync, or a case where the control — or its position parameter — is **missing**. The same method handles all of these.

## When this applies
- "Open the sunshade to N%" / "close the sunshade" — a fully specified move.
- "Open the sunshade for some shade" — no percentage given.
- "Match / synchronise the sunshade to the sunroof" — set the sunshade to the sunroof's current position.
- Asking for the sunshade's position.

## Tools
- `get_user_preferences()` — read the default opening percentage **only when** the percentage is meant to come from a standing preference.
- `get_sunroof_and_sunshade_position()` — read the current sunroof and sunshade positions; **required before any "match/synchronise to the sunroof" request** — the target number is only knowable from this read. A field may read `"unknown"` — unverifiable, not a value.
- `get_weather(...)` — read weather for the relevant place/time only when a condition or warning applies to the move.
- `open_close_sunshade({percentage})` — set the sunshade opening percentage; `0` is fully closed. The tool, or its position **parameter**, may be **missing** (a missing required parameter makes every call error).

## Method
1. **Act on the sunshade, with the correct argument.** Open vs. close, and the right `percentage` value — don't close when an open was asked, and don't omit the value.
2. **"Match/synchronise the sunshade to the sunroof" → read positions FIRST, then set the sunshade.** Call `get_sunroof_and_sunshade_position` once, take the sunroof's current position as the target, and set the **sunshade** to it — the sunshade is the component that moves. Don't skip the read and don't ask or guess the target; the number comes from the reading. **This holds even if the user also states a number** ("set the sunshade to 60% to match the sunroof") — the "match" framing makes the sunroof the source of truth, so still read and use the read value; the stated number is the user's belief, not the authority. Only a plain positioning request with no "match" framing skips the read.
3. **Read state/weather only when the outcome depends on it, once.** Read positions for a sync; read weather one time only if a condition or warning applies. Read each deciding value once.

### Resolving an unstated percentage (ask vs. infer)
4. **Pick the percentage source from the request — don't loop on it.**
   - If the request implies a *standing default* (e.g. "open the sunshade" with no value), the percentage is internal: read it from `get_user_preferences` and use that value. Don't ask.
   - If the value is a *genuine user choice* and no preference applies, **ask** the percentage and use their answer — and do **not** call `get_user_preferences` at all. Do one, not both.
   - **If your context already contains the percentage (the user stated it for a plain positioning request, you already read the preference this turn, or a sync read pinned it), act on it directly — do not re-ask or re-read.** Exception: a stated number inside a "match the sunroof" request is *not* an already-known percentage — the sync read still decides (step 2).

### When a capability is missing
5. **Detect the gap and admit it honestly — distinguish the three cases.**
   - **The whole tool is missing:** the read may still work — report the position, then say plainly you have no control to open or close the sunshade.
   - **The position parameter is removed:** the actuator now demands an argument that no longer exists, so **every call errors — including a bare call to "just open it fully."** Do **not** invoke it; say you can only trigger the control without a specific position, or cannot position it at all.
   - **A position reads `"unknown"`:** treat it as unverifiable; never assume it means zero/closed, never claim a value the tool didn't return, and (for a sync) say you can't read the target. Re-reading won't resolve it.
Do the doable parts in the same answer; refuse only the impossible part, and name the adjacent capability you keep.
6. Confirm what you did (and what you couldn't, with what you'd need to proceed) and stop.

## Principles
- **Sunshade reads can run; move only the sunshade to a resolved percentage.** Read preferences for a default percentage, sunroof/sunshade position for match/sync targets, and weather only for relevant conditions or warnings. Call `open_close_sunshade` only when the target percentage comes from the user, preference, or the sunroof-position read; do not move the sunroof, reverse a sync direction, or claim movement when the tool or percentage parameter is missing.
- **Touch the correct component, in the correct direction.** For a sync, the **sunshade** moves to the sunroof's value — not the other way around.
- **Read once, then act.** Read the percentage source, weather, and position a single time; for a sync the read is mandatory and gives the target.
- **Percentage source matches the request.** Preference-driven → read the preference and don't ask; user-choice → ask and don't read preferences; already-known (incl. a sync read) → just act.
- **Reads are not actuation.** Reporting a position doesn't mean you can move it; keep the two capabilities separate in what you claim.
- **Never call a missing or parameter-stripped tool**, and never claim the sunshade moved when it didn't. `"unknown"` means unverifiable.
- **Match/synchronise reads first.** The target is only knowable from `get_sunroof_and_sunshade_position`; never ask or guess it.
- **A workaround beats a flat refusal.** Prefer "I can read X / I can only trigger it without a position / tell me Z" over a bare "I can't."

## Common mistakes to avoid
- **Skipping the mandatory position read** for a "match the sunroof" request and asking or guessing instead — **especially trusting a number the user attached to the sync** ("set it to 60% to match") instead of reading the sunroof's real position; the user's number can be stale or wrong, so the read governs.
- **Moving the wrong side of the sync** — changing the sunroof, or claiming the sunroof moved, when the sunshade is the component to set.
- **Asking for the percentage when a preference fixes it**, or guessing a value when it's the user's choice — or **reading the preference when the user already gave the value**.
- **Doing both** — reading the preference *and* asking the user — for one percentage.
- **Calling the erroring tool** whose required position parameter was removed, then spiralling — instead of saying you can only trigger it without a position, or not at all.
- **Hallucinating success** — claiming the sunshade opened/closed or reached a position when no working tool could do it.
- **Treating a missing whole tool as if only the parameter were removed (or vice versa)** — keep the three cases distinct.
- **Treating `"unknown"` as a known value**, or **dropping the doable parts** by refusing the whole request when some reads/actions were achievable.

## Procedure
1. Identify the target: an explicit percentage, an unstated percentage, or "match the sunroof".
2. Read the deciding values once: `get_sunroof_and_sunshade_position()` if state matters — **mandatory for a sync**; `get_weather(<place/time>)` only if a condition or warning applies; `get_user_preferences()` only if the percentage is preference-driven.
3. Resolve the percentage (preference value, the user's answer, or — for a sync — the sunroof's read position). Don't read the preference and ask; act directly if already known.
4. Spot any gap: a missing whole tool, a removed position parameter (every call errors), or an `"unknown"` field.
5. Set the sunshade with `open_close_sunshade({percentage})` if you genuinely can. Do not call a missing or parameter-stripped tool.
6. Confirm what you did, state plainly anything you couldn't and why (with the capability you retain and what you'd need), then stop — no loops, no fabricated values.
