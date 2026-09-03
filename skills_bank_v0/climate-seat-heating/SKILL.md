---
name: climate-seat-heating
description: Set seat heating — handle absolute, relative ("by N levels", read the current level first), occupied-only (read occupancy first), match-zone (read the source zone), and one-value-for-all-zones (a single all-zones call) variants; for a vague "warm me up" present options and act ONLY on the seat-heating pick, never fanning out across other climate tools; infer preference-fixed and matched levels silently and ask only for an unstated open level, never re-asking what context pins; and when the tool, its level or seat_zone parameter, or a value is missing or "unknown", do the doable part and admit the rest.
tools:
  - get_seat_heating_level
  - get_seats_occupancy
  - get_user_preferences
  - set_seat_heating
---

# Set seat heating

Set the seat-heating level for one or more zones. The request may give an explicit level, be relative ("turn it up by N levels"), conditional ("only the occupied seats"), a sync ("match the other zone"), or one value for every zone. Sometimes the level or the right tool is left open, or a needed capability is missing. The same method handles all of these.

## When this applies
"Turn on the seat heating", "set the driver seat heating to <level>", "increase seat heating by two levels", "heat only the occupied seats", "match my seat heating to the passenger's", "warm both seats to <level>". (Setting the cabin temperature is `climate-temperature`; steering-wheel heating is `climate-steering-wheel-heating`.)

## Tools
- `get_seat_heating_level({})` — read current per-zone seat-heating levels; required before any relative ("by N") or match set. A field MAY return `"unknown"` — genuinely unverifiable, not a value.
- `get_seats_occupancy({})` — read which seats are occupied; required before an "occupied seats only" request so you heat only those zones.
- `get_user_preferences({})` — read a preference-fixed seat-heating level so you don't ask for it.
- `set_seat_heating({level, seat_zone})` — set a seat-heating level for a zone. The `level` parameter MAY be removed (then only a per-zone toggle remains) and/or the `seat_zone` parameter MAY be removed/unaccepted (then a specific seat can't be targeted — whole-car only). `seat_zone` accepts a single zone (driver, passenger) or an all-zones value; use the all-zones value when one setting applies to every (occupied) zone — not one call per zone.

## Method
1. **One setting for all zones → a single all-zones call.** Per-zone calls are only for when zones differ.
2. **"By N levels" is RELATIVE — read first.** Call `get_seat_heating_level`, then set `current + N` for each target zone in one call per distinct value.
3. **"Occupied seats only" is CONDITIONAL — read first.** Call `get_seats_occupancy`, then apply only to the occupied zones; don't heat unoccupied seats.
4. **"Match zone X to zone Y" reads zone Y's current level.** The value is zone Y's *current* state, not the user's words — read it (`get_seat_heating_level`), then set X to that exact level.
5. **Absolute level → set it verbatim.**
6. **Confirm briefly what you set and stop.**

### Ask vs. infer and don't-over-act (the under-specification crux)
- **Vague "warm me up" → present options; act ONLY on the seat-heating pick.** A vague "I'm too cold / warm me up" maps to several possible tools (seat heating, cabin temperature, steering-wheel heating — each its own skill). Offer the options and let the user choose; if they pick seat heating, set only that, at the level chosen. Do **NOT** proactively fan out across temperature + wheel + seat. Over-acting across a tool family is the dominant failure: it can reach a "warmer" end state while never doing the action the user meant. Temperature and wheel heating are separate skills (`climate-temperature`, `climate-steering-wheel-heating`) — do not invoke them from here.
- **Which level → ASK when it's the user's open choice; INFER when fixed.** User-supplied → set exactly what they state, once. Preference-fixed → read `get_user_preferences` and use it silently; don't ask, don't invent. Match-another → set it to that other zone's level automatically; don't re-ask the matched level.
- **Never re-ask what context already pins.** If the user already named the zone or the level — or it is fixed by a preference, a match, or a read — act on it directly. Only present options / ask when a required choice is truly unspecified and unresolvable.

### When a capability is missing (do the doable, admit the rest)
- **The whole seat-heating tool is missing.** Do every other doable action, then do NOT call it; say that control isn't available. You may still read and report the current level even when you can't change it.
- **The `level` parameter is removed.** Only a per-zone toggle remains. Don't pass `level` (it errors). Say you can't dial the level, distinguishing what remains (toggling seat heating for a zone) from what's gone (choosing/lowering the level).
- **The `seat_zone` parameter is removed/unaccepted.** You can set a level but can't target one seat — whole-car only. Don't pass a zone when it isn't accepted (it errors). Offer to set the available whole-car seat heating to the requested level. Zone support **varies** — use `seat_zone` only when accepted; don't assume it's present or absent.
- **A needed value reads `"unknown"`** (the current level for a "by N" change, or a source zone for a match). Treat it as genuinely unverifiable; don't guess a baseline and don't claim a level the tool never returned — offer an absolute level instead. Re-reading won't resolve it.
Do every doable part in the same answer; refuse only the impossible piece, naming the exact cause; if a choice is genuinely open, ask once; don't loop, then stop.

## Principles
- **Do exactly the warranted actions — don't over-act / don't fan out.** Act on seat heating at the level a preference/match/read fixes; nothing more. A correct "warmer" end state reached by touching extra tool families is still wrong.
- **Ask, don't assume, for an open level** — a guessed level you later correct is two wrong actions; one asked-for value is one right action. But infer preference-fixed and matched levels silently, and never re-ask what context already pins.
- **Read before relative, conditional, and match sets** — the target is only knowable from the read.
- **One value for all zones → one all-zones call**, and **set each value once — don't thrash** (no set-then-correct).
- **Honour the exact mapping** ("match my seat to the passenger" = the passenger's level).
- **Fulfil the doable, refuse only the impossible**, naming the exact missing capability. Never call a missing tool or a removed parameter; distinguish capable from incapable axes; `"unknown"` is unverifiable; read-only is still useful.

## Common mistakes to avoid
- **Over-acting / wrong tool family** (setting temperature or wheel heating, or fanning out, when the user picked just seat heating) — most common failure — or **acting before the user picks** on a vague "warm me up".
- **Guessing a level** the user never gave (including an arbitrary decrement), then needing a correction turn.
- **Asking for a preference-fixed level** instead of reading it, or **re-asking a level that should match another zone**.
- **Setting an absolute level for a relative "+N"** without reading current first, or **set-then-correct**.
- **Skipping the occupancy read** for "occupied only" / heating unoccupied seats; **skipping the source-zone read** for a match.
- **Splitting a single shared value into per-zone calls**, or **re-asking a zone already named**.
- **Claiming a result with no working tool**, **passing a removed `level`/`seat_zone` argument** (it errors), or **guessing a baseline for an `"unknown"` value**.

## Procedure
1. On a vague "too cold / warm me up": present options (note seat heating, plus the separate temperature and wheel-heating skills); do not act until the user picks; act only on the seat-heating pick.
2. Read state as relevant: `get_seat_heating_level` (relative or match), `get_seats_occupancy` (occupied-only), `get_user_preferences` (preference-fixed level).
3. For each level: user-supplied → set what they state; preference-fixed → use the preference; match-another → use that zone's level.
4. Do the doable actions, each once: `set_seat_heating({level:<the level requested or current + N>, seat_zone:<the zone or all-zones value>})` where the parameters are accepted (drop `seat_zone` if it isn't; if `level` is removed, toggle only). One all-zones call when a value is shared; no extra tool families.
5. For any blocked piece, admit it: missing tool, removed `level`, removed/unaccepted `seat_zone`, or an `"unknown"` value. Offer the workaround (available action / whole-car set / absolute level / read-only value).
6. Confirm what was set and stop.
