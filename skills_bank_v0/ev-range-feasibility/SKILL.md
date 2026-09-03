---
name: ev-range-feasibility
description: Answer EV range / charging questions — "how far between two charge levels?", "can I reach <place> without charging?", "how long to charge here?", "how many stops would I need?" — and own the charging computations (get_distance_by_soc over exact SoC slots, never swapping initial/final or inventing an end value; calculate_charging_time_by_soc from the CURRENT SoC, never zero, at the preferred plug). Take an unstated target/upper charge level silently from the stored preference; feasibility needs BOTH the current range and the route distance, then compares. When a tool is removed or a read is "unknown", state the gap honestly, give the safe recommendation, run the doable lookups, and never fabricate a distance or verdict. Information only: never set navigation, never start charging.
tools:
  - get_charging_specs_and_status
  - get_distance_by_soc
  - get_location_id_by_location_name
  - get_routes_from_start_to_destination
  - get_user_preferences
  - search_poi_at_location
  - calculate_charging_time_by_soc
---

# EV range / charging feasibility and the charging math (information only)

The user is gathering numbers about range or charging — "how far between these two charge levels?", "can I reach <place> on what I have?", "how long would a charge here take?", "how many charging stops would this trip need?". These are **read-only** questions: you gather numbers and answer. You never change navigation and you never start charging. This file owns the **charging computations** (the SoC-range and charge-time math) that other EV skills reference. Sometimes a needed bound is **unstated**; sometimes an input is **missing** (a tool removed, or a field reading `"unknown"`). The same method handles all of these.

## When this applies
"How far can I drive from X% down to Y%?", "what's my range between these levels?", "can I make it to <destination> without charging?", "will my current battery get me there?", "how long to charge here?", "if I always charge from <some low %>, how many stops to <place>?" — any read-only EV range / charging estimate, or the charging math another skill needs.

## Tools
- `get_distance_by_soc({initial_state_of_charge, final_state_of_charge})` — distance obtainable between two state-of-charge percentages; let it carry the arithmetic (e.g. derive a stop count from the per-charge range). May be the MISSING tool.
- `get_charging_specs_and_status({})` — read current remaining range / state of charge / battery capacity / plug specs. May be MISSING, or may return a field as `"unknown"`.
- `get_user_preferences()` — read the standing charge level the user tops up to; this fixes an otherwise-unstated target/upper state of charge.
- `get_location_id_by_location_name({location})` — resolve a destination name to an id (for the "can I reach X?" variant).
- `get_routes_from_start_to_destination({start_id, destination_id})` — read the route distance to compare against range (information only). May return the distance field as `"unknown"`.
- `search_poi_at_location({location_id, category_poi, filters})` — find a charger **at the current location** (e.g. one with an available plug) when the question is about charging *here*; generally still works and can be offered proactively.
- `calculate_charging_time_by_soc({charging_station_id, charging_station_plug_id, start_state_of_charge, target_state_of_charge})` — charge time between two SoC levels.

## Method
**Range between two charge levels.** Take the two percentages exactly as the user states them and call `get_distance_by_soc({initial_state_of_charge:<the start % the user gave>, final_state_of_charge:<the end % the user gave>})`. The starting level is `initial`, the lower/target level is `final` — don't swap them, and don't invent an end value (don't assume down-to-empty when the user named a safe buffer). Report the distance and stop.

**"Can I reach X without charging?"** Read `get_charging_specs_and_status` for the current remaining range; resolve the destination with `get_location_id_by_location_name`, then `get_routes_from_start_to_destination` for the route distance. **Compare** range against distance and state the conclusion clearly — possible or not, and if not, the shortfall. Take no car action.

**"How long to charge here?" (the charge-time math).** Read `get_charging_specs_and_status` for current SoC and plug specs. Use `search_poi_at_location` at the **current location** (filtered to an available plug) to get the charger and its plug. Then `calculate_charging_time_by_soc` with `start_state_of_charge` = the **current** SoC (never zero), the **preferred plug**, and the target SoC. Apply any arrival-time or range buffers the user gave to derive min/max as asked. Report the time and stop.

**"How many stops?" (the stop-count math).** Use `get_distance_by_soc` over the target → low-level span for the per-charge range, and derive the count against the trip distance — let the SoC tool carry the arithmetic. Report the number and stop.

### When a bound is unstated — infer it, don't ask (the crux)
- **An unstated upper/target charge level comes from the stored PREFERENCE.** When the user gives only a start/low level (or nothing) and leaves the level to charge *to* open, read `get_user_preferences` and use that as `target_state_of_charge`. Don't ask "what should I charge to?" and don't pick a number yourself.
- **Frame the SoC bounds correctly.** Charge time runs from the **current** SoC up to the preferred target. Range-per-leg comes from `get_distance_by_soc` over the target → low-level span — not from the current remaining-range readout.
- **If your context already pins every bound, do NOT ask.** Ask only when a genuinely required choice is truly unspecified and unresolvable from the values the user gave, the preference, or current state. A value the user already named, or one the preference/state fixes, must not trigger a question.

### When an input is missing — be honest, don't fabricate
Three ways an input goes missing: the range/range-by-SoC tool is **removed** (capacity, consumption, and range all unobtainable, so an exact distance is uncomputable); a status field reads `"unknown"` (e.g. remaining range or battery capacity); or the route distance reads `"unknown"`. In every case:
1. **Read what you can** — call the status/route/location tools that still work; note any removed tool and any `"unknown"` field.
2. **Detect the gap and don't estimate.** A missing or `"unknown"` number is not a number — never derive a km range from the state-of-charge percentage, and never invent the route distance.
3. **State the gap precisely**, attributing it to the specific missing tool or `"unknown"` field.
4. **Give the safe recommendation.** For a long trip with unknown/insufficient range, default to recommending charging before departure rather than a fabricated "you'll make it."
5. **Offer the manual path** (e.g. a two-level ask is a fraction of full-charge range; invite the user to supply displayed range / capacity / consumption to compute from).
6. **Run the doable lookups proactively** — surface the real datum you do have, resolve the place, `search_poi_at_location` for nearby chargers, `calculate_charging_time_by_soc` once a charger is picked.
7. **Don't loop** the identical refusal; move forward each turn.

## Principles
- **Use the exact values the user gives, in the right slots.** No swapping `initial`/`final`, no invented end value.
- **Charge time starts from the current SoC, at the preferred plug.** Zero, or a different plug, gives the wrong time.
- **Feasibility needs both numbers.** "Can I make it?" requires reading the current range *and* the route distance, then comparing — don't answer from one alone, and don't guess.
- **Minimal correct read sequence**, with the right POI tool for *where* the charger is wanted (here = at the current location). Let the SoC tools do the arithmetic; don't bolt on extra generic-math or broad-planning calls.
- **Unstated target charge → the preference**, not a question and not a guess; but a value the context already pins is never a reason to ask.
- **A missing number is not a number.** `"unknown"` means unverifiable — not 0, not full; never back it out from state of charge. Default to the safe action when range is unknown/short, and be useful past the refusal.
- **This is read-only.** Answer the question; never set navigation, add a stop, or start charging.

## Common mistakes to avoid
- **Swapping `initial` and `final`**, or **inventing the end percentage** (e.g. assuming down-to-empty) instead of using the value the user named.
- **Computing charge time from zero** instead of the current SoC, or **using a non-preferred plug**.
- **Reading range from charging status when a two-SoC distance was asked** — use the dedicated `get_distance_by_soc`; or **skipping the charging-status read** and guessing range in the feasibility variant.
- **Asking for the target charge level** (or inventing one) instead of reading the preference — and conversely, **asking when context already pins the answer**.
- **Wrong POI tool**: searching along a route when the charger is wanted at the current location.
- **Fanning out to broad planning / generic-math tools** when a tight read sequence answers it.
- **Answering the wrong direction** of the comparison ("yes you'll make it" when range < distance).
- **Fabricating a km range or feasibility verdict** from data you don't have, **deriving a range from the SoC percentage** when range is `"unknown"`, or **inventing the route distance** when it reads `"unknown"`.
- **Claiming to "look up" specs / a database / the web** when none is available; a **flat refusal with no workaround**; or **looping** the identical "I can't" reply.
- **Taking a car action** — starting navigation or charging — when only an answer was asked.

## Procedure
1. Identify what's asked (two-SoC range, can-I-make-it, charge-time-here, or stop-count) and which bounds the user gave. If the target/upper charge level is unstated, `get_user_preferences` to fix it.
2. Call the working reads the question needs: `get_charging_specs_and_status`; for feasibility, `get_location_id_by_location_name` then `get_routes_from_start_to_destination`; for charge-time here, `search_poi_at_location` at the current location. Note any removed tool or `"unknown"` field as you go.
3. Compute with the dedicated tools: `get_distance_by_soc` for distance/stop-count, `calculate_charging_time_by_soc` for charge time (start = current SoC, preferred plug, to target) — exact slots, no swaps, no invented bounds.
4. If a required input is missing or `"unknown"`: do not estimate it; state the gap precisely; recommend the safe action; offer the manual path; run the doable lookups proactively.
5. Report the number(s) or the conclusion (with shortfall when relevant). Set no navigation, start no charging, don't loop. Stop.
