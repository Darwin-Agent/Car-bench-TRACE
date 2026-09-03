---
name: windows-open-and-position
description: Open windows or sync their positions — set the named windows (or ALL) to a percentage. Execute directly when the percentage and which-windows are given; resolve a genuinely open choice by asking the user (the percentage to open to, or which windows to match to which) and reading current positions before a sync; don't turn on AC or disturb windows already at the wanted position; and if a window control is absent or a position reads "unknown", do the doable and honestly admit the rest.
tools:
  - get_climate_settings
  - get_vehicle_window_positions
  - open_close_window
---

# Open windows / sync window positions

Open windows to an opening percentage, or sync windows so they share a position. Requests range from a fully specified set (the percentage and which windows are given — just do it) to ones where the user **leaves a real choice open** (no percentage, or "sync the windows" without saying which to match to which). The same method handles both, plus the case where a control is missing.

## When this applies
- "Open the windows / open all the windows for some air" — with or without a percentage.
- "Set the front windows to N%" — a fully specified open.
- "Sync the windows" / "get the windows to the same position" — with or without a stated which-to-which.

## Tools
- `get_climate_settings()` — read current climate (harmless context before opening).
- `get_vehicle_window_positions()` — read each window's current position. Required for a sync: it tells you which windows are already where, so you know which ones to move. A position may read `"unknown"` — unverifiable, not a value.
- `open_close_window({window, percentage})` — set a window (a named zone, or `ALL`) to an opening percentage; `0` is fully closed. A specific control may be **absent** in this session.

## Method
1. **If the request is fully specified, just set it.** When the percentage and which windows are given, call `open_close_window` directly — `window=ALL` when they mean all windows (one call for all, not per-window), or the specific zones. **If your context already contains the value and target, act on it directly — do not ask.**
2. **For a sync, read positions first.** `get_vehicle_window_positions` tells you which windows are already correct and which must move. (`get_climate_settings` is optional context before an open.)

### Resolving a genuinely open choice (ask vs. infer)
3. **Opening percentage left open → ASK the user.** "Open the windows" with no value: ask "to what percentage?" and use their answer — don't invent a percentage. Then open **exactly** the windows the request names (`ALL` or the specific zones).
4. **Sync target left open → READ positions, then ASK which-to-which.** "Sync the windows" is ambiguous about which windows match which position. Read positions first, then ask which windows to bring to which position, and use the user's answer. Set **only** the windows that must move; leave windows already at the wanted position untouched. Do **not** use `window=ALL` for a sync — that would disturb already-correct windows.
5. **Set exactly what was named, and nothing extra.** Do not enable AC or change other climate settings unless the user asked — the windows are the whole request.

### When a capability is missing
6. **Absent control or `"unknown"` position → do the doable, admit the rest.** If a needed window control isn't available, set the windows you can and say plainly which one you can't move and why; don't pretend it moved. If a position reads `"unknown"`, treat it as unverifiable — don't assume a value or claim you set/read it, and (for a sync) say you can't confirm which windows already match. Don't call an absent tool or fabricate a result.
7. Confirm what changed (and anything you couldn't, with what you'd need) and stop.

## Principles
- **Act when it's specified; ask when it's a real choice.** A given percentage/target is a direct set. An open percentage or sync target is the user's to give — get it before acting. Don't ask when the context already pins it.
- **Set exactly what was named.** `ALL` when they mean all (single call); the specific zones for a partial set; only the moving windows for a sync.
- **Don't disturb already-correct windows.** In a sync, leave windows already at the target alone — never `ALL`.
- **Do only what was asked.** No AC, no other climate change unless requested.
- **Reads are not actuation, and missing controls aren't faked.** Report what you can; if a control is absent, say so rather than claiming a window moved. `"unknown"` means unverifiable.
- **Answer once, then stop** — no looping a question, a refusal, or a re-read.

## Common mistakes to avoid
- **Guessing a percentage** instead of asking when the value is open — or **asking** when the percentage was already given.
- **Turning on AC** (or other climate) when only the windows were requested.
- **Using `window=ALL` for a sync**, moving windows already at the wanted position.
- **Moving the wrong side of the sync** (changing the already-correct windows instead of bringing the others up to match).
- **Per-window calls when ALL was meant**, or skipping the position read before a sync.
- **Hallucinating success** when a control is absent, or **treating an `"unknown"` position as a value**.
- **Dropping the doable parts** — refusing the whole request when some windows were settable.

## Procedure
1. If fully specified, set directly. For a sync: `get_vehicle_window_positions` (read current positions). For an open: optionally `get_climate_settings`.
2. If a real choice is open, ask the missing value/target (percentage, or which windows to which position); wait for the answer. If already known, skip the ask.
3. Open: `open_close_window({window: "ALL" or named zone(s), percentage: <the value the user gives>})`. Sync: `open_close_window` per window that must move, to the target — leave the rest alone.
4. If a control is absent or a position reads `"unknown"`, do the settable parts and admit what you couldn't — don't fabricate. Confirm; do not touch AC; stop.
