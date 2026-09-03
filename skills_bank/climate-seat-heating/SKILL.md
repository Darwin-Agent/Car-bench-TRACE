---
name: climate-seat-heating
description: Set seat heating — handle absolute, relative ("by N levels", read the current level first), occupied-only (read occupancy first), match-zone (read the source zone), and one-value-for-all-zones (a single all-zones call) variants; for a vague "warm me up / warm up efficiently" present the FULL warming menu (seat heating, cabin temperature, steering-wheel heating) rather than pre-narrowing to seat heating, then state-change only what the user picks — never proactively firing other climate families; infer preference-fixed and matched levels silently and ask only for an unstated open level, never re-asking what context pins; and when the tool, its level or seat_zone parameter, or a value is missing or "unknown", do the doable part and admit the rest.
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
- `get_seat_heating_level({})` — read current seat-heating levels; required before any relative ("by N") or match set, **and before answering any "is the seat heating on / what level is it" status question** — actually call it to ground your answer rather than asserting the status from assumption. It reports **only front zones (driver, passenger)** — there is no rear-seat reading. A field MAY return `"unknown"` — genuinely unverifiable, not a value; surface it as such, never substitute the level you intend to set.
- `get_seats_occupancy({})` — read which seats are occupied; required before an "occupied seats only" request so you heat only those zones. It can report rear seats as occupied even though seat heating has no rear zone to act on (see capability boundary).
- `get_user_preferences({})` — read a preference-fixed seat-heating level so you don't ask for it.
- `set_seat_heating({level, seat_zone})` — set a seat-heating level for a zone. `seat_zone` accepts only **driver, passenger, or an all-zones value — there is NO rear/child-seat zone**, so a rear seat can be neither read nor heated. Use the all-zones value when one setting applies to every (occupied) front zone — not one call per zone. The `level` parameter MAY be removed (then only a per-zone toggle remains) and/or the `seat_zone` parameter MAY be removed/unaccepted (then a specific seat can't be targeted — whole-car only).

## Method
1. **One setting for all zones → a single all-zones call.** Per-zone calls are only for when zones differ.
2. **"By N levels" is RELATIVE — read first.** Call `get_seat_heating_level`, then set `current + N` for each target zone in one call per distinct value.
3. **"Occupied seats only" is CONDITIONAL — read first.** Call `get_seats_occupancy`, then apply only to the occupied zones; don't heat unoccupied seats.
4. **"Match zone X to zone Y" reads zone Y's current level.** The value is zone Y's *current* state, not the user's words — read it (`get_seat_heating_level`), then set X to that exact level.
5. **Absolute level → set it verbatim.**
6. **Confirm briefly what you actually set and stop.** Only report a seat-heating change after its `set_seat_heating` call returned `"status": "SUCCESS"`.

### Ask vs. infer and don't-over-act (the under-specification crux)
- **Vague "warm me up" → present the FULL warming menu, then act only on what the user picks.** A vague "I'm too cold / warm me up / warm up the car efficiently" maps to several possible tools (seat heating, cabin temperature, steering-wheel heating). When you surface options, span **all** of these dimensions — do **not** silently pre-decide that "seat heating is the best fit" and ask only for its level. Quietly narrowing a comprehensive warming request to one dimension is a real failure: the user who says "optimize my warming" wants temperature *and* seat heating addressed, and asking only "what seat-heating level?" drops the temperature half of what they meant. Present the menu, let the user direct, then carry out each piece they confirm.
- **Surfacing options ≠ state-changing across families.** Naming temperature and wheel heating as options is fine and expected. What you must **not** do is *proactively call* those state-changing tools before the user picks. Once they pick, set only what they chose. Over-acting (firing temperature + wheel + seat without a pick) is the mirror failure: it can reach a "warmer" end state while never doing the action the user meant. Temperature and wheel heating are separate skills (`climate-temperature`, `climate-steering-wheel-heating`) — present them as options here, but invoke their tools only when the user has chosen them.
- **Which level → ASK when it's the user's open choice; INFER when fixed.** User-supplied → set exactly what they state, once. Preference-fixed → read `get_user_preferences` and use it silently; don't ask, don't invent. Match-another → set it to that other zone's level automatically; don't re-ask the matched level.
- **A bare "turn on the seat heating" carries NO level — ask (or read a preference); never default to level 1.** "Turn on / switch on the seat heating" is not an absolute request; the level is an open choice only the user can make. Check `get_user_preferences` first — if a preference pins the level, use it silently; otherwise ask which level. Quietly firing `set_seat_heating` at level 1 (or any invented value) is a guess that usually needs a correction turn — it is a failure even though heating does come on.
- **A bare "increase the seat heating" with NO magnitude is also open — ask how much / to what level.** "Increase" without "by N levels" or a target level does not license picking a step size. Don't read the current level and bump it by an assumed amount; ask for the magnitude (or target). Only once a magnitude is given does this become the relative "+N" path below — and that +N must be applied to the *actual current* level, not to a value you already guessed in an earlier turn.
- **Never re-ask what context already pins.** If the user already named the zone or the level — or it is fixed by a preference, a match, or a read — act on it directly. Only present options / ask when a required choice is truly unspecified and unresolvable.

### When a capability is missing (do the doable, admit the rest)
- **Rear / child / back-seat heating doesn't exist as a zone.** Seat heating reads and sets only front zones (driver, passenger). When occupancy shows a rear seat occupied (e.g. a child in the back), apply the rule to the front seats you *can* control, then state plainly that you cannot read or set rear-seat heating and so cannot confirm whether the back seat is heated. Do not silently ignore the rear request, and do not pretend a front result answers a question asked about the rear.
- **A status the user asked you to check reads `"unknown"`.** When the request is "tell me the seat heating status" and that zone's reading comes back `"unknown"`, report it as genuinely unverifiable. Never present the level you are about to set (or just set) as if it were the seat's known status — answering "your seat is on level N" when N is the value you wrote, not what the tool read, is fabrication. You may still set the seat as requested; just be honest that its prior/actual status is unknown.
- **The whole seat-heating tool is missing.** Do every other doable action, then do NOT call it; say that control isn't available. You may still read and report the current level even when you can't change it.
- **The `level` parameter is removed.** Only a per-zone toggle remains. Don't pass `level` (it errors). Say you can't dial the level, distinguishing what remains (toggling seat heating for a zone) from what's gone (choosing/lowering the level).
- **The `seat_zone` parameter is removed/unaccepted.** You can set a level but can't target one seat — whole-car only. Don't pass a zone when it isn't accepted (it errors). Offer to set the available whole-car seat heating to the requested level. Zone support **varies** — use `seat_zone` only when accepted; don't assume it's present or absent.
- **A needed value reads `"unknown"`** (the current level for a "by N" change, or a source zone for a match). Treat it as genuinely unverifiable; don't guess a baseline and don't claim a level the tool never returned — offer an absolute level instead. Re-reading won't resolve it.
Do every doable part in the same answer; refuse only the impossible piece, naming the exact cause; if a choice is genuinely open, ask once; don't loop, then stop.

## Principles
- **Seat-heating reads can run; heat only the resolved front zones at the resolved level.** Read seat levels, occupancy, and preferences when they determine status, relative/match targets, occupied-seat targets, or a preferred level. Call `set_seat_heating` only when the front zone(s) and level are fixed by the user, a read, or the user's later choice; a vague warming complaint should surface options first, and rear seats, temperature, wheel heat, fan, or AC must not be changed from this skill unless the user chose that separate action.
- **Surface the full menu, then do exactly the warranted actions.** On a vague comprehensive warming request, present every warming dimension (seat heating, temperature, wheel) as options — don't pre-narrow to seat heating. Once the user picks, act on seat heating at the level a preference/match/read fixes; nothing more. A correct "warmer" end state reached by proactively firing extra tool families before a pick is still wrong, and so is silently dropping a dimension the user asked about.
- **Ask, don't assume, for an open level** — a guessed level you later correct is two wrong actions; one asked-for value is one right action. But infer preference-fixed and matched levels silently, and never re-ask what context already pins.
- **Read before relative, conditional, and match sets** — the target is only knowable from the read.
- **One value for all zones → one all-zones call**, and **set each value once — don't thrash** (no set-then-correct).
- **Honour the exact mapping** ("match my seat to the passenger" = the passenger's level).
- **Fulfil the doable, refuse only the impossible**, naming the exact missing capability. Never call a missing tool or a removed parameter; distinguish capable from incapable axes; `"unknown"` is unverifiable; read-only is still useful.

## Common mistakes to avoid
- **Pre-narrowing a comprehensive warming request to seat heating alone** — on "warm up efficiently / optimize my warming", silently deciding seat heating is the answer and asking only for its level, dropping the temperature (and wheel) dimensions the user meant. Present the full menu instead.
- **Over-acting / wrong tool family** (proactively state-changing temperature or wheel heating, or fanning out, before the user picks) — the mirror failure: surface options, but don't fire other families' tools until chosen.
- **Defaulting a bare "turn on the seat heating" to level 1** (or any invented level) instead of reading a preference or asking — heating comes on at the wrong level and a correction turn follows.
- **Treating a bare "increase the seat heating" (no magnitude) as license to bump by an assumed step**, or — worse — letting an earlier guessed level cascade: a later "+N" must be added to the *real current* level, never to a value you fabricated a turn ago.
- **Guessing a level** the user never gave (including an arbitrary decrement), then needing a correction turn.
- **Asking for a preference-fixed level** instead of reading it, or **re-asking a level that should match another zone**.
- **Setting an absolute level for a relative "+N"** without reading current first, or **set-then-correct**.
- **Skipping the occupancy read** for "occupied only" / heating unoccupied seats; **skipping the source-zone read** for a match.
- **Splitting a single shared value into per-zone calls**, or **re-asking a zone already named**.
- **Claiming a result with no working tool**, **passing a removed `level`/`seat_zone` argument** (it errors), or **guessing a baseline for an `"unknown"` value**.
- **Answering a status question without reading first** — when the user asks "is my seat heating on / what level is it / is the child's seat heated", call `get_seat_heating_level` before replying; stating the status from assumption (even to correctly say a zone is uncontrollable) is what separated a passing answer from a failing one.
- **Burying a requested status in a mid-stream message and concluding with only the actions taken** — when a request bundles a status check with changes ("check the status... then turn off / set to level 1"), the *final* answer must explicitly deliver the asked-for status for every named seat: prior levels read, any `"unknown"` reading called out as unverifiable, and the rear/child seat you can't read. Reporting it transiently before acting and ending on "done, I set X" leaves the question half-answered.
- **Treating a question about the rear/child seat as answerable** — there is no rear seat-heating zone; read the front zones, control the front seats, then say plainly you can't read or set the back seat rather than implying a front result covers it.
- **Reporting an `"unknown"` status as a real value** — when asked to check a seat's status and the read is `"unknown"`, never report the level you set (or plan to set) as the seat's known status; call it unverifiable.

## Procedure
1. On a vague "too cold / warm me up / warm up efficiently": present the full warming menu spanning seat heating, cabin temperature, and steering-wheel heating; do not state-change any tool until the user picks; then act only on what they choose.
2. Read state as relevant: `get_seat_heating_level` (relative, match, or any status question about whether/what level a seat is heated), `get_seats_occupancy` (occupied-only), `get_user_preferences` (preference-fixed level).
3. For each level: user-supplied → set what they state; preference-fixed → use the preference; match-another → use that zone's level.
4. Do the doable actions, each once: `set_seat_heating({level:<the level requested or current + N>, seat_zone:<the zone or all-zones value>})` where the parameters are accepted (drop `seat_zone` if it isn't; if `level` is removed, toggle only). One all-zones call when a value is shared; no extra tool families.
5. For any blocked piece, admit it: missing tool, removed `level`, removed/unaccepted `seat_zone`, or an `"unknown"` value. Offer the workaround (available action / whole-car set / absolute level / read-only value).
6. Confirm only the seat-heating changes backed by `set_seat_heating` SUCCESS. If an explicitly requested seat-heating change has no successful setter result, do not fold it into "done"; state that it was not completed and name the blocker.
