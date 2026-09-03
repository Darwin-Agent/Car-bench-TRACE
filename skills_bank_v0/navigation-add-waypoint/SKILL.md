---
name: navigation-add-waypoint
description: Insert one new intermediate stop into an active route without changing the final destination — read nav state first, resolve positional references against the CURRENT route, resolve the new stop's id, fetch BOTH adjoining legs (into-leg and away-leg), and wire the four references precisely (never transpose leading-to and leading-away); ask only when which position/stop is a genuine open choice and act directly when state pins it, resolve the leg routes by the user's cue, keep info-only sub-questions informational, and when the add tool is missing or state reads "unknown", do the doable and honestly refuse the rest rather than guessing ids or claiming an insert that didn't happen.
tools:
  - get_current_navigation_state
  - get_location_id_by_location_name
  - get_routes_from_start_to_destination
  - navigation_add_one_waypoint
  - get_user_preferences
---

# Add an intermediate waypoint

A multi-stop route is active and the user wants to **insert** a new intermediate stop, leaving the final destination unchanged. Inserting splices a stop into the chain, so it needs the two route legs that touch the new stop: the leg leading **into** it (from the neighbour before) and the leg leading **away** from it (to the neighbour after). Sometimes the user doesn't say which position; sometimes the add tool is missing or state reads back unreadable. The same method handles all of these.

## When this applies
"Add a stop at <place> after <stop>", "put <place> in between", "add a stop at <place> before I reach <stop>" — while a route is active and the endpoint stays the same. Often paired with an info-only sub-question ("am I low on battery?"). (To swap a stop for another, remove a stop, or change the endpoint, see the other navigation skills.)

## Tools
- `get_current_navigation_state({detailed_information:true})` — read the ordered waypoints, start, and routes so you know the neighbours of the new stop. **May return `"unknown"`** fields, leaving ids unreadable, or **may be missing**.
- `get_location_id_by_location_name({location})` — resolve the new stop's name to an id.
- `get_routes_from_start_to_destination({start_id, destination_id})` — fetch routes for each adjoining leg (neighbour-before → new stop, and new stop → neighbour-after).
- `navigation_add_one_waypoint({waypoint_id_to_add, route_id_leading_to_new_waypoint, waypoint_id_after_new_waypoint, route_id_leading_away_from_new_waypoint, waypoint_id_before_new_waypoint})` — insert the new stop. Requires **route-consistent** before/after ids; mismatched ids error. **May be missing.**
- `get_user_preferences()` — read a standing route preference when the user ties a leg's route to it.

## Method
1. **Read current navigation state first.** Get the ordered waypoint list so you can identify the new stop's neighbours (before and after). If fields read `"unknown"` or the tool is missing, you cannot safely edit — say so and offer a permissioned fresh route; don't guess ids.
2. **Interpret positional references against the CURRENT route.** "After my next stop", "before <stop>" resolve against the waypoints you just read — not against the stop you are about to add. Resolve such references before mutating.
3. **Resolve the new stop's name to an id** with `get_location_id_by_location_name`.
4. **Fetch BOTH adjoining legs** before adding: the leg **into** the new stop (neighbour-before → new stop) and the leg **away** (new stop → neighbour-after).
5. **Wire the four references precisely.** `route_id_leading_to_new_waypoint` = the into-leg route; `route_id_leading_away_from_new_waypoint` = the away-leg route; name the before-neighbour, the after-neighbour, and the stop to add. **Never transpose leading-to and leading-away.**
6. Confirm the updated route, then stop.

### Ask vs. infer the position/stop
- **When state pins the position, act — do not ask.** If the user named the place and a position (after/before a stop) that the current route resolves uniquely, proceed silently.
- **When which position/stop is a genuine open choice, ASK.** If nothing in context fixes where the stop goes, ask the user and use what they name — don't default to the first slot, the nearest, or any position you pick.
- **Route choice follows the user's cue.** Take the route per a stated preference (`get_user_preferences`); present each leg's options and apply their pick when they choose; take the fastest yourself when they defer ("just pick").

### When a capability is missing
- **Missing add tool.** When `navigation_add_one_waypoint` is absent, state plainly there is no tool to insert an intermediate stop while keeping the route active. Offer a permissioned fresh-route rebuild only if a start path exists and the user agrees; never start it silently.
- **`"unknown"` means unverifiable.** Don't invent the stop or its neighbours, and don't pretend to edit.
- **Do the doable, decline the impossible — in one flow.** Complete every feasible part (lookups, the correct insert) AND deliver the honest decline for the infeasible one.
- **Info-only stays info-only.** A battery/charging question is answered by reading/reporting (point at `ev-range-feasibility` for the math, `poi-search` for finding a station) — it does not, by itself, add a stop or re-route.

## Principles
- **Add needs two legs.** Fetch routes for the into-leg and the away-leg before inserting, every time.
- **Resolve positional words from the current route**, not against a stop you just inserted.
- **Wire the four references precisely** — a single mis-wired id produces the wrong route; never swap leading-to and leading-away.
- **Ask only for a genuine unresolved choice; otherwise act.** When context names or pins the position, asking is the failure; when it is truly open, guessing is the failure.
- **Do only what was asked.** An informational sub-question gets a read-and-report answer, not a car action; don't search a POI the user said they don't need.
- **Never call a missing/erroring tool and never claim an insert that didn't happen.** Honest "can't" plus a real alternative beats a fake.

## Common mistakes to avoid
- **Omitting one of the two adjoining legs** before the add call.
- **Swapping leading-to and leading-away routes**, or naming the wrong before/after neighbour.
- **Mis-identifying a positional reference** — acting on a stop you just added when "next stop" meant the current next waypoint.
- **Asking which position when state already pins it**, or **guessing the position** when it is a genuine open choice.
- **Proactively picking the leg routes** when the user said they would choose.
- **Turning an info-only battery/charging question into a re-route**, or running a POI search the user explicitly waived.
- **Claiming a stop was inserted** when no tool did it, or **inventing a stop/neighbour** when state reads `"unknown"`.
- **Ending after the doable parts** without the honest decline, or **refusing the whole request** when the insert was doable.
- **Skipping the initial state read.**

## Procedure
1. `get_current_navigation_state(detailed_information=true)`; identify the new stop's current before/after neighbours. If `"unknown"` or the tool is missing, refuse safely and offer a permissioned fresh route — no guessed ids.
2. If the position/stop is unstated and a genuine open choice, ask; otherwise resolve it from the named/positional reference against this current route.
3. `get_location_id_by_location_name(<new stop>)`.
4. `get_routes_from_start_to_destination(neighbour-before → new stop)` and `(new stop → neighbour-after)`; choose each per the user's cue (their pick, a stated preference via `get_user_preferences`, or fastest when deferred).
5. Call `navigation_add_one_waypoint` once, wiring `route_id_leading_to_new_waypoint`, `route_id_leading_away_from_new_waypoint`, the before/after neighbours, and the new stop id — with route-consistent ids. If the add tool is absent, admit there's no tool to insert it; don't fake it.
6. Answer any info-only sub-question by reading and reporting only — never add a waypoint.
7. Confirm what changed, name what couldn't and why, then stop.
