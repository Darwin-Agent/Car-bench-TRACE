---
name: calendar-read
description: Read the calendar for a given day and report the entries — mapping "today" to the current date (derive month and day; year is implicit) and a named day to that day's month/day. A pure read needs no confirmation. When the calendar tool is removed, reply once, honestly, that there is no calendar tool — never invent appointments and never claim an empty calendar you didn't actually verify (absence of a tool is not an empty schedule).
tools:
  - get_entries_from_calendar
---

# Read the calendar for a day

The user wants to know what's on their calendar for a day — today, this afternoon, or a named day. You map the day to a month/day, read the entries, and report them. This is a read; it needs no confirmation. The only complication is when the calendar tool is missing.

## When this applies
"What's on my calendar today?", "do I have anything left today?", "what's on for <day>?", "do I have meetings this afternoon?", "am I free <day>?" — any request to read the schedule for a specific day.

## Tools
- `get_entries_from_calendar({month, day})` — read a specific day's entries (time, title, location, duration, attendees). Year is implicit; pass month and day. This tool may be **removed** — if so, there is no way to read the schedule.

## Method
1. **Map the day to month + day.** "Today" → convert the provided current date to its month and day. A named day → that day's month and day. The year is implicit; pass month and day.
2. **Read the entries.** `get_entries_from_calendar({month:<resolved month>, day:<resolved day>})`.
3. **Report back** the entries for that day. A pure read needs no confirmation — just answer and stop.

### Ask vs. infer the day
- **Read — don't ask — for the date.** "Today" is the provided current date; derive month/day from it. A named day maps to its own month/day. Don't ask the user for a date they already implied, and don't query a range or a different day than the one asked.
- There is no genuine open choice here to ask about — the day is given or derivable.

### When a capability is missing
- **No calendar tool.** If `get_entries_from_calendar` is removed, make no call and reply once, honestly, that you can't access the calendar because the tool isn't available. Never list meetings, and never claim the calendar is empty — absence of a tool is not an empty schedule. State the limit once; don't loop.

## Principles
- **"Today" is the current date.** Derive month/day from the provided current date; don't query a range or a different day.
- **A pure read needs no confirmation.** Read and report; don't ask to proceed.
- **Report only what the tool returns.** No tool means you cannot assert the schedule; nothing fabricated, no claimed-empty calendar you didn't verify.
- **One clear answer, then stop.** Don't re-read or re-refuse turn after turn.

## Common mistakes to avoid
- **Wrong date arithmetic for "today"**, or querying a range/other day instead of the day asked.
- **Calling a different or unavailable calendar tool** instead of `get_entries_from_calendar`.
- **Inventing appointments**, or **claiming an empty calendar** that was never actually read.
- **Asking the user for the date** when "today" or a named day already fixes it.
- **Looping** the same refusal when the tool is gone instead of stating it once and stopping.

## Procedure
1. If `get_entries_from_calendar` is removed → one honest "I can't access the calendar — no tool available"; no calls; stop.
2. Otherwise resolve the day to month/day: "today" → the current date's month/day; a named day → that day's month/day.
3. `get_entries_from_calendar({month, day})`.
4. Read back the entries; a pure read needs no confirmation. Stop.
