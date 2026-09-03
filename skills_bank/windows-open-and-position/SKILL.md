---
name: windows-open-and-position
description: Open, close, or sync window positions — set the named windows (or ALL) to a percentage. Execute directly when the percentage and which-windows are given; resolve a genuinely open choice by asking the user (the percentage to open to, or which windows to match to which) and read current positions before a sync; before opening windows past 25% check whether AC is on and, if so, warn about energy inefficiency and confirm first; don't turn on AC yourself or disturb windows already at the wanted position; and if a window control is absent or a position reads "unknown", do the doable, surface the unverifiable read to the user, and never narrate a confident "they now match" result you could not actually read.
tools:
  - get_climate_settings
  - get_vehicle_window_positions
  - open_close_window
---

# Open windows / sync window positions

Open or close windows to a position, or sync windows so they share a position. Requests range from a fully specified set (the percentage and which windows are given — just do it) to ones where the user **leaves a real choice open** (no percentage, or "sync the windows" without saying which to match to which). The same method handles both, plus the energy-efficiency check when opening past 25% with AC on, and the case where a control is missing.

## When this applies
- "Open the windows / open all the windows for some air" — with or without a percentage.
- "Close all the windows" / "set the front windows to N%" — a fully specified open or close.
- "Sync the windows" / "get the windows to the same position" — with or without a stated which-to-which.
- "Close/set all windows to the same level as the passenger rear" — a match-to-a-readable-target sync.
- "Close the window that's open / fully open" — a single window identified by its current state; read positions to find which window matches the description and close only that one.
- Note: turning on AC, the front/rear window defrost, fan speed, or airflow direction are separate climate operations with their own skills — this skill only moves windows. Don't fan out into those unless the user asked for them.
- A common pairing is "close all the windows, then turn on the defrost / AC": the closing is squarely this skill — do it correctly here — but the climate side (defrost, fan, airflow, AC) and any auto-adjustments it triggers belong to that operation's skill, including reading and honouring the user's stored preference for those values rather than defaulting them. Don't pick a default airflow or fan value yourself to "help" the defrost or AC; that decision (and its preference lookup) is not part of moving windows.
- Do not add intermediate or temporary actuator changes that the user did not request, even as a "prerequisite" for the paired operation. Setting fan speed to some interim level so AC can be enabled — when the user neither asked for that level nor needs you to choose it — is an unrequested change that often gets immediately overridden by the user's next instruction; that intermediate actuation is a failure even when the final state ends up correct. Move only the windows; leave the paired climate tool to manage its own preconditions.

## Tools
- `get_climate_settings()` — read current climate, in particular whether the AC is on. Read it before opening windows past 25% so you can apply the energy-inefficiency warning rule below.
- `get_vehicle_window_positions()` — read each window's current position. Required for a sync: it tells you which windows are already where, so you know which ones to move. A position may read `"unknown"` — unverifiable, not a value.
- `open_close_window({window, percentage})` — set a window (a named zone, or `ALL`) to an opening percentage; `0` is fully closed. A specific control may be **absent** in this session.

## Method
1. **Establish the percentage and which windows.** If both are given (now or earlier in context), proceed — do not re-ask what was already stated. If a real choice is open, resolve it per "Ask vs. infer" below before acting.
2. **Before opening past 25%, check AC.** If the requested opening percentage is strictly greater than 25% (absolute), read `get_climate_settings` first. If the AC is on, warn the user that opening that far with AC running wastes energy and get **explicit** confirmation before opening. A clear "yes, open it" is the only green light: a hedged or conditional reply ("open them, but it's fine if they stay closed") is **not** a yes and is **not** a no — prompt once more for a plain yes/no instead of unilaterally deciding either to open or to leave them closed. If the AC is off, just open. (Opening to exactly 25% or less, or closing, needs no such check.) This skill's own threshold for *opening* is 25%; do not confuse it with the separate rule that turning AC **on** closes windows over 20% — that one is part of the AC operation, not this one.
3. **Set the windows.** Call `open_close_window` — `window=ALL` when they mean all windows (one call for all, not per-window), or the specific named zones.
4. **For a sync, read positions first.** `get_vehicle_window_positions` tells you which windows are already correct and which must move, then move only the ones that must move.

### Resolving a genuinely open choice (ask vs. infer)
- **Opening percentage left open → ASK the user.** "Open the windows" with no value: ask "to what percentage?" and use their answer — don't invent a percentage. Then open **exactly** the windows the request names (`ALL` or the specific zones).
- **Sync target left open → READ positions, then ASK which-to-which.** "Sync the windows" is ambiguous about which windows match which position. Read positions first, then ask which windows to bring to which position, and use the user's answer. Set **only** the windows that must move; leave windows already at the wanted position untouched. Do **not** use `window=ALL` for a sync — that would disturb already-correct windows.
- **A "match this window" target is readable, not a real choice.** "Close all windows to the same level as the passenger rear" pins the target by a value you can read — get positions, compute the target, and set only the windows that differ. Don't ask for a percentage here; the request already determines it.
- **A window named by its state is readable, not a real choice.** "Close the window that's fully open" identifies the window by its current position — read positions, find the one matching the description (e.g. the one at 100% is "fully open"; a window at 5% is not), and close only that window. If exactly one window fits the description, act on it silently; only ask if two or more genuinely fit. Don't close windows the description doesn't cover.
- **Set exactly what was named, and nothing extra.** Do not enable AC or change other climate settings unless the user asked — the windows are the whole request.

### When a capability is missing
- **Absent control → do the doable, admit the rest.** If a needed window control isn't available, set the windows you can and say plainly which one you can't move and why; don't pretend it moved. Don't call an absent tool or fabricate a result.
- **`"unknown"` position → unverifiable, never narrate it as a confirmed value.** A position that reads `"unknown"` is a masked value, not a real one — don't assume it means closed/zero/some number, and don't re-read in a loop hoping for a number.
  - If the **match source** (the window you're matching *to*) reads `"unknown"`, you cannot compute the target — say you can't read that window's position to match against, and don't guess one.
  - If only the **windows you're setting** read `"unknown"`, you can still issue the set toward a readable target value (the set itself succeeds), but you must **not** report those windows as confirmed to be at that position or claim "they now match" — that is the exact failure to avoid. Describe the command you issued and flag honestly that you can't read those windows back to verify the result.
- Confirm what changed (and anything you couldn't, with what you'd need) and stop.

## Principles
- **Window and climate reads can run; window movement needs resolved windows and percentage.** Read window positions for sync/current-state targeting and read AC status before opening past 25% to apply the energy warning. Call `open_close_window` only for the named or resolved windows and exact percentage; if AC is on and the requested opening is over 25%, get explicit confirmation first, and never change AC, fan, defrost, airflow, or other climate controls as part of a window move.
- **Act when it's specified; ask when it's a real choice.** A given percentage/target is a direct set. An open percentage or sync target is the user's to give — get it before acting. Don't ask when the context (or a readable value like "match the rear window") already pins it.
- **Check AC before a large opening.** Opening past 25% absolute while AC is on is energy-inefficient — read the climate, warn, and confirm before opening; act directly when AC is off or the opening is 25% or less. A precondition read like this is cheap and is what separated the good runs from the bad.
- **Set exactly what was named.** `ALL` when they mean all (single call); the specific zones for a partial set; only the moving windows for a sync.
- **Don't disturb already-correct windows.** In a sync, leave windows already at the target alone — never `ALL`.
- **Do only what was asked, with no interim actuation.** Don't turn on AC or change other climate yourself unless the user asked — the windows are the whole request. (Closing windows is itself fine; it's enabling AC that's out of scope here.) And don't slip in a temporary actuator change (e.g. a stop-gap fan level) to satisfy a paired operation's precondition — preserve the user's intent and let that operation handle its own setup.
- **Reads are not actuation, and missing controls aren't faked.** Report what you can; if a control is absent, say so rather than claiming a window moved. `"unknown"` means unverifiable.
- **Answer once, then stop** — no looping a question, a refusal, or a re-read.

## Common mistakes to avoid
- **Guessing a percentage** instead of asking when the value is open — or **asking** when the percentage was already given (or readable from a "match this window" target).
- **Opening past 25% without checking AC**, skipping the energy-inefficiency warning and confirmation when AC is on — or **confusing the 25% open-warning threshold with the 20% AC-on close threshold** (a different rule that belongs to turning AC on).
- **Treating a hedged reply as a decision.** After warning that opening past 25% with AC on wastes energy, a reply like "open them, but it's fine if they stay closed too" is not a clear yes — don't unilaterally leave them closed (or open them). Ask once more for a plain yes or no and act on that.
- **Turning on AC** (or other climate) when only the windows were requested.
- **Using `window=ALL` for a sync**, moving windows already at the wanted position.
- **Moving the wrong side of the sync** (changing the already-correct windows instead of bringing the others up to match).
- **Per-window calls when ALL was meant**, or skipping the position read before a sync.
- **Hallucinating success** when a control is absent, or **treating an `"unknown"` position as a value**.
- **Reporting a sync/match as confirmed when you couldn't read the target windows.** Saying "both rear windows are now at 25% to match" when those positions came back `"unknown"` is a false confirmation — issue the set if the target value is known, but state you can't verify those windows' positions instead of claiming they match.
- **Computing a match target from an `"unknown"` source.** If the window you're matching *to* is unreadable, you have no target — don't fabricate one; say you can't read it.
- **Dropping the doable parts** — refusing the whole request when some windows were settable.
- **Owning a paired climate adjustment that isn't yours** — when the request also asks for defrost/AC, do the window move here, but don't default a fan speed or airflow direction for it; the paired climate skill must read and apply the user's stored preference for those, and a self-chosen default can silently produce the wrong final state.
- **Inserting an unrequested intermediate actuator change as a "prerequisite."** Bumping fan speed to a self-chosen interim level just so AC can turn on — when the user never asked you to set that level — is an extra, unsolicited action; it counts as a failure even if the user later sets the value themselves and the final state matches. Don't temporarily move actuators the user didn't ask you to touch.

## Procedure
1. Determine the percentage and which windows. If a real choice is open, ask the missing value/target (percentage, or which windows to which position) and wait; if already given or readable (e.g. "match the rear window"), skip the ask.
2. For a sync or "match this window" target: `get_vehicle_window_positions` (read current positions) and compute the target. For an opening above 25%: `get_climate_settings`; if AC is on, warn about energy inefficiency and get explicit confirmation before opening.
3. Open: `open_close_window({window: "ALL" or named zone(s), percentage: <the value the user gives>})`. Sync/match: `open_close_window` per window that must move, to the target — leave the rest alone.
4. If a control is absent or a position reads `"unknown"`, do the settable parts and admit what you couldn't — don't fabricate. Confirm; don't enable AC yourself; stop.
