---
name: navigation-replace-waypoint
description: Swap one existing intermediate stop for a different place on an active route without changing the final destination — read nav state first, ASK which stop only when "replace one of my stops" is genuinely open and act when state pins it, resolve the new stop's id, fetch BOTH adjoining legs (the away leg runs to the removed stop's SUCCESSOR, not to the stop being removed), and wire the four references precisely; resolve leg routes by the user's cue, never abuse navigation_add_one_waypoint to fake a replace (mismatched ids error), and when the replace tool is missing or state reads "unknown", do the doable and honestly admit there's no tool to replace in place rather than guessing ids or claiming a swap that didn't happen.
tools:
  - get_current_navigation_state
  - get_location_id_by_location_name
  - get_routes_from_start_to_destination
  - navigation_replace_one_waypoint
  - get_user_preferences
---

# Replace an intermediate waypoint

A multi-stop route is active and the user wants to **swap** one existing intermediate stop for a different place, leaving the final destination unchanged. Replacing splices a different stop into the chain, so it needs the two route legs that touch the swapped position: the leg leading **into** the new stop and the leg leading **away** from it. The away leg goes to the **new stop's successor** — the same neighbour that follows the removed stop — so fetch the away leg to that neighbour, not to the stop being removed. Sometimes the user doesn't say which stop; sometimes the replace tool is missing or state reads back unreadable.

## When this applies
"Swap the <intermediate> stop for <place>", "replace one of my stops with <place>", "instead of <stop>, go via <place>" — while a route is active and the endpoint stays the same. (To insert a new stop, remove a stop, or change the endpoint, see the other navigation skills.)

## Tools
- `get_current_navigation_state({detailed_information:true})` — read the ordered waypoints, start, and routes so you know the swapped stop's neighbours. **May return `"unknown"`** fields, leaving ids unreadable, or **may be missing**.
- `get_location_id_by_location_name({location})` — resolve the new stop's name to an id (safe even for a replace you may ultimately decline).
- `get_routes_from_start_to_destination({start_id, destination_id})` — fetch routes for each adjoining leg (neighbour-before → new stop, and new stop → the removed stop's successor).
- `navigation_replace_one_waypoint({route_id_leading_to_new_waypoint, waypoint_id_to_replace, route_id_leading_away_from_new_waypoint, new_waypoint_id})` — swap an existing stop for a new one. **May be missing** — then an intermediate stop cannot be replaced in place.
- `get_user_preferences()` — read a standing route preference when the user ties a leg's route to it.

## Method
1. **Read current navigation state first.** Get the ordered waypoint list so you can identify the stop being replaced and its neighbours. If fields read `"unknown"` or the tool is missing, you cannot safely edit — say so; don't guess ids.
2. **Resolve which stop they mean against the CURRENT route.** A named stop or a positional reference that the current waypoints resolve uniquely needs no question; resolve it from the state you read.
3. **Resolve the new stop's name to an id** with `get_location_id_by_location_name`.
4. **Fetch BOTH adjoining legs** before replacing: the leg **into** the new stop (neighbour-before → new stop) and the leg **away** (new stop → **the removed stop's successor**). The away-neighbour is the new stop's successor — fetch the away leg to that neighbour, not to the stop being removed.
5. **Wire the four references precisely.** `route_id_leading_to_new_waypoint` = the into-leg route; `route_id_leading_away_from_new_waypoint` = the away-leg route; name the stop being replaced and the new stop. **Never transpose leading-to and leading-away.**
6. Confirm the updated route, then stop.

### Ask vs. infer which stop
- **When state pins the target stop, act — do not ask.** If the user named the stop, or a positional reference plus the current route uniquely identifies it, proceed silently.
- **When which stop to replace is a genuine open choice, ASK.** "Replace one of my stops" does not say which; ask the user and use the stop they name — don't default to the first, the nearest, or any stop you pick.
- **Route choice follows the user's cue.** Take the route per a stated preference (`get_user_preferences`); present each leg's options and apply their pick when they choose; take the fastest yourself when they defer ("just pick").

### When a capability is missing
- **Missing replace tool.** When `navigation_replace_one_waypoint` is absent, state plainly there is no tool to replace an intermediate stop in place.
- **Never abuse the add tool to fake a replace.** Inserting the "replacement" with `navigation_add_one_waypoint` and mismatched before/after ids errors; never repurpose it, and never claim a swap happened. (Inserting a stop is `navigation-add-waypoint`; removing one is `navigation-remove-waypoint`.)
- **`"unknown"` means unverifiable.** Don't invent the stop or pretend to edit.
- **Do the doable, decline the impossible — in one flow.** Complete the feasible lookups AND deliver the honest decline for the infeasible swap. Offer a permissioned fresh-route rebuild only if a start path exists and the user agrees; never start it silently.

## Principles
- **Replace needs two legs.** Fetch routes for the into-leg and the away-leg before swapping, every time — and the away leg runs to the removed stop's successor.
- **Resolve the target stop from the current route**, not from a place name alone.
- **Wire the four references precisely** — a single mis-wired id produces the wrong route; never swap leading-to and leading-away.
- **Replace exactly one, never add on top** when the user asked for a swap.
- **Ask only for a genuine unresolved choice; otherwise act.** When context names or pins the stop, asking is the failure; when it is truly open, guessing is the failure.
- **Never call a missing/erroring tool and never claim a swap that didn't happen.** Honest "can't" plus a real alternative beats faking it with the add tool.

## Common mistakes to avoid
- **Fetching the away leg to the stop being removed** instead of to its successor (the new stop's neighbour-after).
- **Omitting one of the two adjoining legs** before the replace call.
- **Swapping leading-to and leading-away routes**, or naming the wrong stop to replace.
- **Asking which stop when state already pins it**, or **guessing which stop** when it is a genuine open choice.
- **Proactively picking the leg routes** when the user said they would choose.
- **Adding a second waypoint instead of replacing** the named one, or **abusing `navigation_add_one_waypoint` with mismatched ids** to fake a replace — it errors.
- **Claiming an intermediate stop was replaced** when no tool did it, or **inventing a stop** when state reads `"unknown"`.
- **Ending after the doable parts** without the honest decline, or **refusing the whole request** when the swap was doable.
- **Skipping the initial state read.**

## Procedure
1. `get_current_navigation_state(detailed_information=true)`; identify the stop to replace and its current before/after neighbours. If `"unknown"` or the tool is missing, refuse safely — no guessed ids.
2. If which stop to replace is unstated and a genuine open choice, ask; otherwise resolve the target from the named/positional reference against this current route.
3. `get_location_id_by_location_name(<new stop>)`.
4. `get_routes_from_start_to_destination(neighbour-before → new stop)` and `(new stop → the removed stop's successor)`; choose each per the user's cue (their pick, a stated preference via `get_user_preferences`, or fastest when deferred).
5. Call `navigation_replace_one_waypoint` once, wiring `route_id_leading_to_new_waypoint`, `route_id_leading_away_from_new_waypoint`, `waypoint_id_to_replace`, and `new_waypoint_id` — with route-consistent ids. If the replace tool is absent, admit there's no tool to replace it in place; do not fake it with the add tool.
6. Confirm what changed, name what couldn't and why, then stop.
