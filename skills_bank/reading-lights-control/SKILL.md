---
name: reading-lights-control
description: Turn the interior reading lights on or off for a specific seat position or all seats — handles "turn on the driver reading light", "turn off the rear lights", a bare "turn on the reading lights" (which position?), and "adjust the reading lights to who's actually in the car / only the occupied seats". Set exactly the named position(s); when no position is named, that's a genuine open choice — ask which rather than defaulting to ALL; for occupancy-based requests read seat occupancy first then turn each seat's light on/off to match; and when the per-position control or the occupancy read is unavailable, do the doable part and admit the rest rather than guessing. Not for exterior lights, ambient/cabin lighting, or headlights.
compatibility: set_reading_light, get_seats_occupancy
---

Turn interior reading lights on or off. The same method handles a clear single-position request, a bare under-specified request, an occupancy-driven adjustment, and the cases where a needed control or read is unavailable.

## When this applies
Requests to control the cabin reading/courtesy lights at one or more seats: "turn on my reading light", "turn on the driver reading light", "switch off the rear reading lights", "turn on the reading lights" (no position), or "set the reading lights for whoever's in the car / only the occupied seats, off for the empty ones". For exterior low/high beams and fog lights use `exterior-lights-control`; for cabin mood/ambient lighting use `ambient-light-color`. This skill is only the reading lights.

## Tools
- set_reading_light(position, on) — turns a reading light on/off. position is one of ALL, DRIVER, PASSENGER, DRIVER_REAR, PASSENGER_REAR, RIGHT_REAR, LEFT_REAR; on is true/false. One call per position; fire the needed positions together in one turn. The position argument may be unavailable in the schema — then you cannot target a specific light and the call errors.
- get_seats_occupancy() — reads which seats are occupied. Needed before any occupancy-based adjustment; may be unavailable.
- get_reading_lights_status() — reads current on/off state per position; use it to resolve "turn them off" when which lights are on is otherwise unknown.

## Method
1. **Always call get_seats_occupancy first** before calling set_reading_light, regardless of whether the user named specific positions or not. This confirms which seats are occupied and ensures the correct context for any reading-light adjustment.
2. After reading occupancy, call set_reading_light for the requested positions — DRIVER for the driver's light, ALL only when the user actually said "all"/"every" reading light. For occupancy-based requests ("turn on the occupied seats, off the empty ones", "adjust to who's actually in the car", "don't waste energy on empty seats"), issue one set_reading_light per seat: on for each occupied seat, off for each empty seat. Map occupancy keys to positions exactly (driver→DRIVER, passenger→PASSENGER, driver_rear→DRIVER_REAR, passenger_rear→PASSENGER_REAR).
3. Report what you changed in plain terms.

### Ask vs. infer
- Act directly when the position is named or pinned by context (the user is the driver and asks for "my reading light" → DRIVER; only one light is on and they say "turn it off").
- A bare "turn on the reading lights" with no position is a genuine open choice, not a cue for ALL — ask which seat(s) they want rather than blanket-lighting every seat. Defaulting to ALL here is the failure.
- Do NOT ask when occupancy resolves it for you: an occupancy-based request is answered by reading occupancy, not by asking the user who is where.
- Even if the user volunteers who is sitting where, an "adjust to who's actually in the car / save energy" request still means read get_seats_occupancy and act on the sensor — the user's words are intent, the sensor is ground truth.

### When a capability is missing
- If the position argument is unavailable so you cannot target a specific light, say plainly you can't control that reading light right now — don't fall back to ALL or claim it worked.
- If you cannot read seat occupancy, you can't safely run an occupancy-based adjustment; say so and offer to set the lights if the user tells you which seats are occupied.
- A read field coming back "unknown" is genuinely unverifiable — don't assume a seat is empty or a light is off; surface the gap.

## Principles
- **Reading-light reads can run; light writes need resolved positions and on/off.** Read occupancy for occupied/empty-seat rules and read current light status to resolve "turn them off" when the target is otherwise unclear. Call `set_reading_light` only for the positions and boolean fixed by the user's words, the occupancy/status read, or a confirmed clarification; do not assume `ALL` for a vague "reading lights" request or target a position when the schema cannot accept it.
- Set exactly what was asked: the named positions, nothing more, in one turn.
- Treat "the reading lights" without a position as ambiguous and resolve it the policy way — context first, then ask — never an assumed ALL.
- Occupancy-driven requests are deterministic once occupancy is read: on for occupied, off for empty — read once, then set all positions together.
- Be honest about missing controls and unverifiable reads; do every doable part and refuse only the impossible part in one answer.

## Common mistakes to avoid
- **Skipping get_seats_occupancy before calling set_reading_light** — always read occupancy first, even when the user names positions explicitly.
- Defaulting a bare "turn on the reading lights" to ALL instead of asking which seat(s).
- Asking the user which seats are occupied instead of reading get_seats_occupancy for an occupancy-based request.
- Acting on the seating the user described out loud instead of reading get_seats_occupancy when the request hinges on who is *actually* in the car — verify with the sensor first.
- Forgetting to turn the empty-seat lights off when the request is "only the occupied seats".
- Falling back to ALL (or claiming success) when the per-position control is unavailable.
- Assuming a masked/"unknown" occupancy or status means a seat is empty or a light is off.

## Procedure
1. **Always start with get_seats_occupancy** to read current seat occupation — this step is mandatory before any set_reading_light call.
2. Named position + action → set_reading_light(position, on) for each named seat.
3. No position named → ask which reading light(s); don't assume ALL.
4. Occupancy-based → use the occupancy result to issue one set_reading_light per seat (on=occupied, off=empty).
5. "Turn them off" with unclear targets → get_reading_lights_status to see which are on, then turn those off.
6. Position argument or occupancy read unavailable → state the exact limitation, do any doable part, and offer the fallback (e.g. tell me which seats).
