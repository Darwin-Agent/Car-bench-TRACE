---
name: trunk-door
description: Open or close the trunk door. Execute directly when the action is given; before a gated open ask once then act on the affirmative reply (never re-ask after "yes"); read weather only when a condition might warrant a warning and treat that warning as a single heads-up, not a refusal; and if the trunk actuator is absent or the position reads "unknown", report what you can read and honestly admit you cannot move it.
tools:
  - get_trunk_door_position
  - get_weather
  - open_close_trunk_door
---

# Open / close the trunk door

Open or close the trunk door, or report its position. Requests range from a plain "close the trunk" to a confirmation-gated open, an open accompanied by a weather heads-up, or a case where the trunk control is **missing**. The same method handles all of these.

## When this applies
- "Open the trunk" / "close the trunk."
- "Open the trunk" when conditions (e.g. poor weather) might warrant a one-time warning.
- "Is the trunk open?" / asking for the trunk door's position.

## Tools
- `get_trunk_door_position()` — read the current trunk door position. A field may read `"unknown"` — unverifiable, not a value.
- `get_weather(...)` — read weather for the relevant place/time **only when** a condition might warrant a warning before opening.
- `open_close_trunk_door({action})` — open or close the trunk door. May be **missing** in this session.

## Method
1. **Act on exactly what was asked — open vs. close.** Use the correct `action`; don't close when an open was requested or vice versa.
2. **Read state/weather only when the outcome depends on it.** Read the position once if the request needs it (a status question, or to confirm before acting). Read weather once **only** if a condition might warrant a heads-up before opening — don't read it for a routine close.
3. **Confirmation-gated open: ask ONCE, then execute on "yes".** An exposed/safety open, or opening in poor conditions, needs one confirmation. Ask once; on the first affirmative reply, issue the actuator call. Do **not** execute before the "yes", and **never re-ask** after it.

### Resolving the request (ask vs. infer)
4. **The action is usually explicit — don't manufacture a choice.** Open and close are stated directly; there is no percentage to resolve for the trunk door. If your context already contains the action and any confirmation, act on it directly — don't re-ask or re-read.
5. **A weather warning is a single heads-up, evaluated ONCE — not a refusal.** If conditions warrant it, read weather one time and surface one warning when you ask for confirmation. On "yes" you still act. Don't re-verify the weather in a loop and don't let the warning cancel the action.

### When a capability is missing
6. **Detect the gap and admit it honestly.**
   - **The actuator is missing:** the read may still work — report the position, then say plainly you have no control to open or close the trunk door.
   - **The position reads `"unknown"`:** treat it as unverifiable; never assume it means closed/open, never claim a value the tool didn't return, and don't take an action whose safety depends on it. Re-reading won't resolve it.
Do the doable parts in the same answer; refuse only the impossible part, and name the adjacent capability you keep (e.g. "I can read the position but can't move it").
7. Confirm what you did (and what you couldn't, with what you'd need to proceed) and stop.

## Principles
- **Trunk reads can run; moving the trunk needs the open/close action and any warning handled.** Read trunk position to answer status or avoid redundant movement, and read weather only when it affects an opening warning or condition. Call `open_close_trunk_door` only for the user's clear open/close action or after their one confirmation following a weather warning; do not loop confirmations, treat bad weather as a refusal, or claim the trunk moved when the actuator is missing.
- **Confirm once, then act — and don't loop.** The dominant failure is re-asking the same confirmation forever and never actuating. One confirmation, then on "yes" execute exactly once.
- **A warning is not a refusal.** Poor weather justifies at most one heads-up; it does not cancel the action once the user confirms.
- **Read once, then act.** Read the position or weather a single time when it matters; acting is the goal, not re-verifying.
- **Touch the correct action** — open vs. close, exactly as asked.
- **Reads are not actuation.** Reporting a position doesn't mean you can move it; keep the two capabilities separate in what you claim.
- **Never call a missing tool**, and never claim the trunk moved when it didn't. `"unknown"` means unverifiable.
- **A workaround beats a flat refusal.** Prefer "I can read the position / tell me when you'd like to retry" over a bare "I can't."

## Common mistakes to avoid
- **Re-asking the confirmation in a loop** after the user said yes, so the trunk never moves.
- **Executing a gated open before asking** for the one confirmation.
- **Treating a weather warning as a refusal** and never acting on the confirmation.
- **Using the wrong action** (closing when open was asked, or vice versa).
- **Reading weather for a routine close** that warrants no warning, or re-verifying weather turn after turn.
- **Hallucinating success** — claiming the trunk opened/closed when no working tool could do it.
- **Treating `"unknown"` as a known value**, or **dropping the doable read** by refusing the whole request when the position was still reportable.

## Procedure
1. Identify the action (open or close) or that it's a status question.
2. Read the deciding values once: `get_trunk_door_position()` if the position matters; `get_weather(<place/time>)` only if a condition might warrant a warning before opening.
3. Spot any gap: a missing actuator or an `"unknown"` position.
4. If confirmation-gated, ask once (with a single weather warning if warranted, and without promising a capability you may lack) and wait for "yes".
5. On confirmation (or immediately if none required), call `open_close_trunk_door({action})` if you genuinely can. Do not call a missing tool.
6. Confirm what you did, state plainly anything you couldn't and why (with the capability you retain and what you'd need), then stop — no loops, no fabricated values.
