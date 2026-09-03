---
name: navigation-add-waypoint
description: Insert one new intermediate stop into an ALREADY-ACTIVE route without changing the final destination — read nav state first, resolve positional references against the CURRENT route, resolve the new stop's id (sequentially, never with a guessed id), fetch BOTH adjoining legs (into-leg and away-leg), and wire the four references precisely (never transpose leading-to and leading-away); ask only when which position/stop is a genuine open choice and act directly when state pins it, take fastest legs when route selection is unspecified and then actively ASK whether the user wants details on the other alternatives (a real question, not a passive "if you want" mention), keep info-only sub-questions (battery, charge time, find-a-station) strictly informational and never add or even offer to add a found POI unless the user explicitly asks to add it, treat planning a brand-new whole trip as set_new_navigation rather than pre-activating then adding, and when the add tool is missing or state reads "unknown", do the doable and honestly refuse the rest rather than guessing ids or claiming an insert that didn't happen.
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
"Add a stop at <place> after <stop>", "put <place> in between", "add a stop at <place> before I reach <stop>" — **while a route is already active** and the endpoint stays the same. Often paired with an info-only sub-question ("am I low on battery?", "find me a charging station ~100 km ahead", "how long to charge?"). (To swap a stop for another, remove a stop, or change the endpoint, see the other navigation skills.)

**This skill is only for inserting into an existing active route.** If the user is planning a brand-new trip from scratch and wants the whole multi-stop route set at once, that is `set_new_navigation` with the full ordered leg list — do NOT set the first leg, activate, and then bolt stops on with the add tool. Only use add-waypoint when navigation is already active when the add request arrives. Read the nav state to tell which situation you are in.

## Tools
- `get_current_navigation_state({detailed_information:true})` — read the ordered waypoints, start, and routes so you know the neighbours of the new stop. **May return `"unknown"`** fields, leaving ids unreadable, or **may be missing**.
- `get_location_id_by_location_name({location})` — resolve a **location/city** name to an id. It does NOT resolve points of interest. If the new stop is a POI you already found (a charging station, restaurant, etc.), you already have its POI id from that search — use it directly and skip this call.
- `get_routes_from_start_to_destination({start_id, destination_id})` — fetch routes for each adjoining leg (neighbour-before → new stop, and new stop → neighbour-after).
- `navigation_add_one_waypoint({waypoint_id_to_add, route_id_leading_to_new_waypoint, waypoint_id_after_new_waypoint, route_id_leading_away_from_new_waypoint, waypoint_id_before_new_waypoint})` — insert the new stop. Requires **route-consistent** before/after ids; mismatched ids error. **May be missing.**
- `get_user_preferences()` — read a standing route preference when the user ties a leg's route to it.

## Method
1. **Read current navigation state first.** Get the ordered waypoint list so you can identify the new stop's neighbours (before and after). If fields read `"unknown"` or the tool is missing, you cannot safely edit — say so and offer a permissioned fresh route; don't guess ids.
2. **Interpret positional references against the CURRENT route.** "After my next stop", "before <stop>" resolve against the waypoints you just read — not against the stop you are about to add. Resolve such references before mutating.
3. **Get the new stop's id.** If it's a location/city, resolve it with `get_location_id_by_location_name` and **wait for the real id** before using it — never guess or fabricate an id, and never fire the leg-route lookups in parallel with the name resolution. The resolved id is opaque and is almost never the one you'd guess, so feeding a guessed id into `get_routes_from_start_to_destination` returns a "no routes found" error and burns a turn on recovery. Issue only the name-resolution call, read the returned id, then fetch legs with it. If the new stop is a POI you already found in a prior search (e.g. a charging station the user picked), you already hold its id — use it directly.
4. **Fetch BOTH adjoining legs** before adding: the leg **into** the new stop (neighbour-before → new stop) and the leg **away** (new stop → neighbour-after).
5. **Wire the four references precisely.** `route_id_leading_to_new_waypoint` = the into-leg route; `route_id_leading_away_from_new_waypoint` = the away-leg route; name the before-neighbour, the after-neighbour, and the stop to add. **Never transpose leading-to and leading-away.**
6. Confirm the updated route, then stop.

### Ask vs. infer the position/stop
- **When state pins the position, act — do not ask.** If the user named the place and a position (after/before a stop) that the current route resolves uniquely, proceed silently.
- **When which position/stop is a genuine open choice, ASK.** If nothing in context fixes where the stop goes, ask the user and use what they name — don't default to the first slot, the nearest, or any position you pick.
- **Route choice follows the user's cue.** Take the route per a stated preference (`get_user_preferences`); present each leg's options and apply their pick when they choose; take the fastest yourself when they defer ("just pick"). When you pick the fastest leg yourself for an insert, tell the user you took the fastest alternative per leg, flag any toll road on a chosen leg, and then **actively ask whether they want more information on the other route alternatives** — phrase it as a real question ("Want me to go through the other options?"), not a passive offer like "there are other alternatives if you want details." The policy requires the ask, not just a mention; a statement that alternatives exist without inviting a choice is treated as incomplete. Still don't dump every alternative's details unprompted — name that alternatives exist and ask.

### When a capability is missing
- **Missing add tool.** When `navigation_add_one_waypoint` is absent, state plainly there is no tool to insert an intermediate stop while keeping the route active. Offer a permissioned fresh-route rebuild only if a start path exists and the user agrees; never start it silently.
- **`"unknown"` means unverifiable.** Don't invent the stop or its neighbours, and don't pretend to edit.
- **Do the doable, decline the impossible — in one flow.** Complete every feasible part (lookups, the correct insert) AND deliver the honest decline for the infeasible one.
- **Info-only stays info-only.** "Check my battery / am I low?", "find a charging station ~100 km ahead", "how long to charge to 80%?" are all read-and-report requests. Answer them by reading and reporting — searching a POI, reading charging specs, computing charge time. **Do NOT add the found station as a waypoint, and do NOT volunteer "want me to add it?" off your own initiative.** Inserting a stop is a state change that needs an explicit call-for-action; a request to *find* or *evaluate* a station is not a request to *route* to it. Proactively offering to add it, and especially adding it, is over-action. Only insert when the user explicitly says to add/route-to it.

## Principles
- **Navigation reads and route fetches can run; insertion waits for a fully resolved active-route edit.** Read current navigation, resolve the new stop id, read route preferences, and fetch the two adjoining leg routes to determine whether an add is possible. Call `navigation_add_one_waypoint` only when the route is active, the new stop, before/after neighbours, both route ids, and any route-choice rule are settled; do not start a new trip, insert on top of an unresolved position, or add a POI the user has not chosen.
- **Add only into an active route; build new trips with `set_new_navigation`.** If the user wants the whole multi-stop trip planned and set at once, assemble the full ordered leg list and set it in one call — don't activate a partial route and then patch stops on with the add tool.
- **Resolve the new stop's id, then use it.** Wait for the real id from `get_location_id_by_location_name`; never guess an id or pre-fire route lookups against an unverified one.
- **Add needs two legs.** Fetch routes for the into-leg and the away-leg before inserting, every time.
- **Resolve positional words from the current route**, not against a stop you just inserted.
- **Wire the four references precisely** — a single mis-wired id produces the wrong route; never swap leading-to and leading-away.
- **Ask only for a genuine unresolved choice; otherwise act.** When context names or pins the position, asking is the failure; when it is truly open, guessing is the failure.
- **Do only what was asked.** An informational sub-question gets a read-and-report answer, not a car action; don't search a POI the user said they don't need, and don't add (or offer to add) a POI the user only asked you to find or evaluate.
- **Never call a missing/erroring tool and never claim an insert that didn't happen.** Honest "can't" plus a real alternative beats a fake.

## Common mistakes to avoid
- **Guessing the new stop's id** or firing the leg-route lookups in parallel with `get_location_id_by_location_name` before its result is back — the guessed id is almost always wrong and the lookup errors. Resolve, then fetch. (And don't run `get_location_id_by_location_name` for a stop that's a POI you already found — you already have its id.)
- **Burning turns on a malformed plan.** The insert is a short, fixed sequence; a plan is optional. If you do use `planning_tool`, its `step_dependent_on` and `step_index` values must be plain integers (use `0`, not `0.0`) — a float there errors and wastes calls. Skip the plan and just execute the steps if in doubt.
- **Using add-waypoint to build a fresh trip.** When navigation is inactive and the user wants the whole multi-stop trip set at once, that's `set_new_navigation` with all legs — not activate-then-add. Don't pre-activate a partial route just so the add tool becomes usable.
- **Adding, or even offering to add, a found POI on an info-only request.** "Find a charging station ~100 km ahead" / "how long to charge?" is read-and-report; inserting it (or proactively asking "want me to add it?") is over-action unless the user explicitly says to route to it.
- **Omitting one of the two adjoining legs** before the add call.
- **Swapping leading-to and leading-away routes**, or naming the wrong before/after neighbour.
- **Mis-identifying a positional reference** — acting on a stop you just added when "next stop" meant the current next waypoint.
- **Asking which position when state already pins it**, or **guessing the position** when it is a genuine open choice.
- **Proactively picking the leg routes** when the user said they would choose.
- **Mentioning alternatives without asking.** After taking the fastest leg yourself, closing with "there are other alternatives if you want details" is a passive statement, not the required question — it leaves the user no clear invitation to choose and counts as incomplete. End with an actual question ("Want the details on the other options?").
- **Turning an info-only battery/charging question into a re-route**, or running a POI search the user explicitly waived.
- **Claiming a stop was inserted** when no tool did it, or **inventing a stop/neighbour** when state reads `"unknown"`.
- **Ending after the doable parts** without the honest decline, or **refusing the whole request** when the insert was doable.
- **Skipping the initial state read.**

## Procedure
1. `get_current_navigation_state(detailed_information=true)`; identify the new stop's current before/after neighbours. If navigation is **inactive** and the user wants a whole new trip set at once, switch to `set_new_navigation` (not this skill). If `"unknown"` or the add tool is missing, refuse safely and offer a permissioned fresh route — no guessed ids.
2. If the position/stop is unstated and a genuine open choice, ask; otherwise resolve it from the named/positional reference against this current route.
3. `get_location_id_by_location_name(<new stop>)` and **wait for the returned id** — do not pre-fire leg lookups with a guessed id.
4. `get_routes_from_start_to_destination(neighbour-before → new stop)` and `(new stop → neighbour-after)`; choose each per the user's cue (their pick, a stated preference via `get_user_preferences`, or fastest when deferred).
5. Call `navigation_add_one_waypoint` once, wiring `route_id_leading_to_new_waypoint`, `route_id_leading_away_from_new_waypoint`, the before/after neighbours, and the new stop id — with route-consistent ids. If the add tool is absent, admit there's no tool to insert it; don't fake it.
6. Answer any info-only sub-question (battery, find-a-station, charge time) by reading and reporting only — never add a waypoint or offer to add one unless the user explicitly asks to route to it.
7. Confirm what changed (and, if you chose fastest legs yourself, say so, flag any toll, and **ask whether the user wants details on the other alternatives**), name what couldn't and why, then stop.
