---
name: calendar-read
description: Read the calendar for a given day and report the entries (meetings, appointments, events) — mapping "today" to the current date (derive month and day; year is implicit) and a named day to that day's month/day. Covers "what's on my calendar?", "any meetings left today?", "what's this afternoon?", "when's my next meeting?", "has my <named> meeting started yet?"; when the user asks for remaining/upcoming/next entries, filter the day's entries against the current time, and answer "started/ongoing/over" by comparing the current time to the entry's start time and start+duration. A pure read needs no confirmation. Attendees come back as contact IDs, not names — never invent attendee names; if the attendees value comes back unavailable you cannot enumerate or email "everyone attending", so say so honestly instead of guessing. When you cannot call the calendar tool, say so once honestly — never invent appointments and never claim an empty calendar you didn't actually verify (an unreadable calendar is not an empty schedule).
tools:
  - get_entries_from_calendar
---

# Read the calendar for a day

The user wants to know what's on their calendar for a day — today, this afternoon, the rest of the day, a named day, or whether a specific meeting has started yet. You map the day to a month/day, read the entries, and report them — filtering or comparing against the current time when the request implies it. This is a read; it needs no confirmation. The main complications are honoring a "remaining/next/has-it-started" comparison and being honest when a value (the attendee list) or the whole tool is unavailable.

## When this applies
"What's on my calendar today?", "do I have anything left today?", "what's on for <day>?", "do I have meetings this afternoon?", "what's my next meeting?", "has my <named> meeting started yet?", "am I free <day>?" — any request to read the schedule for a specific day. Note: only the current day can be read; if asked for a past or future day, say only today's calendar is available.

## Tools
- `get_entries_from_calendar({month, day})` — read a specific day's entries (start time, duration, topic, location, attendees). Year is implicit; pass month and day. Attendees are returned as **contact IDs, not names** — resolving them to names or emails is a separate contacts operation, not part of a calendar read. The attendees value may come back as `"unknown"`; treat that as genuinely unavailable (you cannot list or email the attendees), not as an empty list. This tool may itself be **unavailable** — if you cannot call it, there is no way to read the schedule.

## Method
1. **Map the day to month + day.** "Today" → convert the provided current date to its month and day. A named day → that day's month and day. The year is implicit; pass month and day.
2. **Read the entries.** `get_entries_from_calendar({month:<resolved month>, day:<resolved day>})`.
3. **Apply the time comparison the request implies.** If the user asked for *remaining*, *upcoming*, *next*, or *this afternoon/evening* entries, compare each entry's start time to the current time and report only those still ahead (and matching the daypart). For "next meeting", report the single earliest upcoming one. A meeting whose start has passed but is still ongoing (start + duration is still after now) counts as still relevant — don't drop it. If the user asks **whether a named meeting has started / is over**, find that entry by topic and compare: now ≥ start means it has started; now ≥ start + duration means it has ended; report the clear verdict plus the start time. Compare the scheduled start time directly against the current system clock — the entry's start time is the local meeting time, so do **not** adjust for the meeting's city, timezone, or any travel time even when the meeting is in a different location than you are now. A plain "what's on today?" reports the whole day.
4. **Report back** the relevant entries concisely (time, topic, location). A pure read needs no confirmation — just answer and stop.
5. **If the read feeds a downstream step** (plan a charging stop around the next meeting, email an attendee about a meeting), pick the entry that matches the user's stated criteria — the earliest upcoming one for "next/upcoming", or the meeting they named by topic/time/location — and carry that entry forward. Don't re-ask which meeting when the criteria already pin it; do surface the choices if more than one entry genuinely fits.

### Ask vs. infer the day
- **Read — don't ask — for the date.** "Today" is the provided current date; derive month/day from it. A named day maps to its own month/day. Don't ask the user for a date they already implied, and don't query a range or a different day than the one asked.
- The day itself is given or derivable — no open choice to ask about. **Which entry to act on** can be a genuine choice when the read serves a downstream task: if the user's criteria single out one entry (the next upcoming one, or the meeting they named), infer it silently and proceed; only if two or more entries genuinely fit do you list them and ask which.

### When a capability is missing
- **Verify before you refuse.** Only declare the calendar unreadable when the calendar tool is genuinely not callable. If it is present, call it — don't pre-empt with an apology or assume a limit that isn't there. A false "I can't" is as wrong as a fabricated answer.
- **Can't read the calendar.** If you cannot call `get_entries_from_calendar` (the tool isn't available to you), make no call and reply once, honestly, that you can't access the calendar right now. Never list meetings, and never claim the calendar is empty — an unreadable calendar is not an empty schedule. State the limit once; don't loop.
- **Attendees unavailable.** When the request needs the attendee list (e.g. "email everyone attending the <named> meeting") and that field comes back as `"unknown"`, you genuinely cannot resolve who attends. Don't invent attendees or treat it as "no attendees". Complete what you still can — confirm the meeting you found, handle any explicitly named recipients the user gave, and resolve those via contacts — then plainly tell the user the meeting's attendee list isn't available and offer to send to names/addresses they provide. Fulfil the doable parts, refuse only the impossible part, in one answer.

## Principles
- **Calendar reads are safe; downstream actions are not part of this skill.** Call `get_entries_from_calendar` directly for the requested day, "today", or upcoming/remaining filter because this skill only reads schedule data. Do not turn the returned meetings into email recipients, calls, navigation targets, attendee-name lookups, or calendar edits unless the user explicitly asks for that follow-up; attendee IDs and `"unknown"` fields are reportable facts, not permission to act on people or invent missing details.
- **"Today" is the current date.** Derive month/day from the provided current date; don't query a range or a different day.
- **Honor a "remaining/upcoming/next" filter against the clock.** When the user only wants what's still ahead, drop entries whose start time has already passed and report the rest; for "next", report just the earliest upcoming one. This is the difference between a helpful answer and dumping the whole day when they asked what's left.
- **A pure read needs no confirmation.** Read and report; don't ask to proceed.
- **Report only what the tool returns.** Attendees are contact IDs — report the meeting without inventing names; resolve names only if the request actually calls for it (a separate contacts lookup). An attendees value of `"unknown"` means the list is unavailable, not empty — never enumerate or email it as if you knew it. If you couldn't read the calendar, you cannot assert the schedule — nothing fabricated, no claimed-empty calendar you didn't verify.
- **A bare "today's meetings" read needs no preference lookup or downstream fanning-out.** Read and report; only chain into contacts/weather/routes when the user's request actually asks for that follow-up.
- **One clear answer, then stop.** Don't re-read or re-refuse turn after turn.

## Common mistakes to avoid
- **Wrong date arithmetic for "today"**, or querying a range/other day instead of the day asked.
- **Ignoring a "remaining/this afternoon/next" qualifier** and reporting the entire day, or conversely filtering when the user asked for everything.
- **Inventing attendee names** from the returned contact IDs instead of reporting the meeting plainly (or doing a real contacts lookup when names are needed).
- **Treating an `"unknown"` attendees value as an empty list**, or trying to email "everyone attending" anyway — say the list is unavailable instead.
- **Misjudging the started/ongoing/over verdict** — compare now against start and start+duration, don't guess from the start time alone.
- **Inventing appointments**, or **claiming an empty calendar** that was never actually read.
- **Asking the user for the date** when "today" or a named day already fixes it, or **re-asking which meeting** when the user's criteria (next/upcoming, or a named topic/time) already pick one out.
- **Refusing or apologizing without checking** — declaring the calendar unreadable (or any value unavailable) when the tool was actually callable. Verify, then act; only refuse the part that is genuinely impossible.
- **Looping** the same refusal when you can't read the calendar instead of stating it once and stopping.

## Procedure
1. If you cannot call `get_entries_from_calendar` → one honest "I can't access the calendar right now"; no calls; stop.
2. Otherwise resolve the day to month/day: "today" → the current date's month/day; a named day → that day's month/day.
3. `get_entries_from_calendar({month, day})`.
4. If the request asked for remaining/upcoming/next/afternoon entries, filter against the current time. Read back the relevant entries; a pure read needs no confirmation. Stop.
