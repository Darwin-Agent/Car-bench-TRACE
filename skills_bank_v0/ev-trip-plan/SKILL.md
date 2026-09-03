---
name: ev-trip-plan
description: Gather an EV trip + charging plan (route, travel time, a charger, charge time) as information ONLY — the single most important rule is that you NEVER set navigation and NEVER add a waypoint. Read the charger specs/status, get routes and a charger for information, and compute charge time and any further-stop check via the `ev-range-feasibility` math (charge time from the current SoC at the preferred plug; get_distance_by_soc to test whether another stop is needed — report it, don't plan it). Resolve genuine choices (which route, which charger) from what the user states. The assembled plan is typically emailed via `send-email` (recipient resolved via `contacts-lookup`) or driven via `navigation-start` — reference those, don't re-teach them.
tools:
  - planning_tool
  - get_location_id_by_location_name
  - get_charging_specs_and_status
  - get_routes_from_start_to_destination
  - search_poi_at_location
  - search_poi_along_the_route
  - calculate_charging_time_by_soc
  - get_distance_by_soc
---

# Gather an EV trip + charging plan (do NOT set navigation)

The user wants a trip and charging plan worked out — routes, travel time, a charger, charge time — **as information**. You fetch routes, read the battery, find a charger, and reason about charging, but this is information-gathering only. **You never set navigation and you never add a waypoint.** Routing and POI tools are used purely to read distances, times, and charger details. The assembled plan is then emailed (the `send-email` skill, with the recipient resolved via `contacts-lookup`) or driven (`navigation-start`) — but those are separate skills. Some requests leave genuine choices open (which route, which charger). The same method handles them.

## When this applies
"Plan my trip to <place> and email <person> the route and charging details", "work out where I'd need to charge and send it to <contact>", "give me the travel time including a charger near <a point on the route>." The defining feature: the deliverable is a **plan** to be read/emailed/handed off, and the user is **not** asking you to navigate now.

## Tools
- `planning_tool({...})` — optional scaffold of the steps; a malformed dependency index returns a recoverable error — just continue with the real lookups.
- `get_location_id_by_location_name({location})` — resolve the destination (or a named point) to an id.
- `get_charging_specs_and_status({})` — read current state of charge / range / charging specs. The plan depends on this.
- `get_routes_from_start_to_destination({start_id, destination_id})` — read route options (distance / travel time). **For information only here.**
- `search_poi_at_location({location_id, category_poi, filters})` / `search_poi_along_the_route({at_kilometer, route_id, category_poi, filters})` — find a charger (at a place, or along the route at a kilometre mark) **as info**, when the plan needs one.
- `calculate_charging_time_by_soc({charging_station_id, charging_station_plug_id, start_state_of_charge, target_state_of_charge})` — charge time from the current SoC (the `ev-range-feasibility` math).
- `get_distance_by_soc({initial_state_of_charge, final_state_of_charge})` — to test whether a *further* stop would be needed (the `ev-range-feasibility` math).

## Method
1. **HEADLINE: never set navigation, never add a waypoint.** Do **not** call any set-navigation or add/replace-waypoint tool at any point — even though you fetch routes and find chargers. The user wants the plan assembled, not activated. When the user explicitly says "don't set the charger in navigation, just include it in the plan/mail", honour that literally. This is the single rule that most separates a good outcome from a bad one.
2. **Resolve the destination.** `get_location_id_by_location_name` for the place (or a named point on the route).
3. **Read the charging specs/status.** `get_charging_specs_and_status` — do not skip; a complete plan depends on it.
4. **Get routes for information.** `get_routes_from_start_to_destination`; honour the user's route preference (e.g. fastest). Read distance/time — activate nothing.
5. **Find / reason about the charger.** If the plan needs a charger, search one (at a place, or along the route at the requested kilometre mark, as the user framed it — info only) and pick per the user's stated preference (e.g. the fastest-charging one / a fast DC plug). Compute charge time from the **current** SoC to the target with `calculate_charging_time_by_soc` at the preferred plug, and use `get_distance_by_soc` to test whether even after that charge a **further** stop would be needed. The charge-time and further-stop computations are the `ev-range-feasibility` math.
6. **Report extra stops; don't plan them.** If a further stop would be needed, say so in the plan. Mention it, but do not add it as a stop.
7. **Hand the plan off.** Assemble the plan — route, travel time, charger details, charge time, any "another stop needed" note. Emailing it is the `send-email` skill (recipient resolved via `contacts-lookup`); driving it is `navigation-start`. Reference those; don't re-teach send or navigation mechanics here.

### Resolving the choices — by what's stated, or by asking
The route and the charger are **genuine user choices** — resolve them from what the user states, disambiguating to the specific option, and asking only when truly unresolved. Do **not** guess.
- **Which route → the user's stated preference** (e.g. fastest), not a default.
- **Which charger → the user's stated preference** (e.g. fastest-charging) near the requested point. Properties the user didn't mention don't decide the pick.
- **If your context already pins the choice, do NOT ask** — a qualifier the user gave, or a single matching route/charger, settles it. Ask only when a required choice is genuinely unspecified and can't be resolved from what's stated.

### When a capability is missing
- **The plan's lookups are doable but a downstream action (send / navigate) isn't.** Those downstream actions belong to other skills; this skill still assembles the full plan. Do all the doable lookups — route, charger, charge time, the further-stop check — and deliver the complete assembled plan. Surface any gap in the plan-gathering itself honestly (e.g. a removed routing/charger tool), never fabricate a distance, charge time, or charger, and don't loop. (How a missing send tool is handled lives in `send-email`; a missing start-navigation tool in `navigation-start`.)

## Principles
- **Info-only means no car action.** Fetching routes and finding chargers is for reading numbers and details; it is never a licence to set navigation or add a stop. This is the headline rule.
- **Read the charging specs the plan needs** — `get_charging_specs_and_status` is part of producing a complete plan, not optional. **Charge time starts from the current SoC**, at the preferred plug (the `ev-range-feasibility` math).
- **Resolve the choices, don't guess** — route and charger are the user's calls; use what they stated and disambiguate to the specific option. But a choice the context already pins is never a reason to ask.
- **Do only what was asked.** Mention a needed extra stop, but don't plan it; don't over-build the itinerary.
- **Hand off the plan; don't absorb the sibling.** Sending is `send-email` (recipient via `contacts-lookup`); driving is `navigation-start`. Reference them by name.

## Common mistakes to avoid
- **Setting navigation or adding/replacing a waypoint** — routing through the charger or activating the trip. This is the primary failure mode; the task is plan-only.
- **Skipping `get_charging_specs_and_status`** — going straight from routes to the charger search — leaving the plan incomplete.
- **Computing charge time from zero** instead of the current SoC, or **using a non-preferred plug/route/charger**.
- **Skipping the further-stop check**, or **actually planning** that extra stop instead of only mentioning it.
- **Asking when the context already pins** the route/charger, or **guessing** when it's genuinely open.
- **Re-teaching send or navigation mechanics here** instead of referencing `send-email` / `navigation-start`; **fabricating** a charger, distance, or charge time; or **looping**.

## Procedure
1. (Optional) `planning_tool`; continue past any recoverable error. Never set navigation or add a waypoint at any point.
2. Resolve the destination id with `get_location_id_by_location_name`.
3. `get_charging_specs_and_status` — do not skip.
4. `get_routes_from_start_to_destination(start → destination)`; select the preferred route; note distance/time. (Info only — set nothing.)
5. If a charger is needed: search it (at-location or along-route near the requested km, as framed — info only); pick per preference; `calculate_charging_time_by_soc` from the current SoC to target at the preferred plug; `get_distance_by_soc` to check whether a further stop is needed (the `ev-range-feasibility` math) — report it, don't plan it.
6. Assemble the plan: route + travel time + charger details + charge time + any "further stop needed" note. To email it, see `send-email` (recipient via `contacts-lookup`); to drive it, see `navigation-start`. Set no navigation, add no waypoint. Stop.
