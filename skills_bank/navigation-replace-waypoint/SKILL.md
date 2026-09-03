---
name: navigation-replace-waypoint
description: Swap one existing intermediate stop for a different place on an active route without changing the final destination — read nav state first, ASK which stop only when "replace one of my stops" is genuinely open and act when state pins it, resolve the new stop's id, fetch BOTH adjoining legs (the away leg runs to the removed stop's SUCCESSOR, not to the stop being removed), and wire the four references precisely; pick the fastest route per leg when the user hasn't specified one but then inform them you took the fastest alternative, offer details on the other alternatives, and disclose any toll on a presented/chosen leg; never abuse navigation_add_one_waypoint to fake a replace (mismatched ids error), and when the replace tool is missing or state reads "unknown", do the doable and honestly admit there's no tool to replace in place rather than guessing ids or claiming a swap that didn't happen.
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
1. **Read current navigation state first — and re-read it after any prior edit in the same conversation.** Get the ordered waypoint list so you can identify the stop being replaced and its neighbours. If you (or the user) added, removed, or replaced a stop earlier in this conversation, the target stop's neighbours have likely shifted, so re-read the live state before wiring — never reuse stale neighbours or stale route ids from before the last edit. If fields read `"unknown"` or the tool is missing, you cannot safely edit — say so; don't guess ids.
2. **Resolve which stop they mean against the CURRENT route.** A named stop or a positional reference that the current waypoints resolve uniquely needs no question; resolve it from the state you read.
3. **Resolve the new stop's name to an id** with `get_location_id_by_location_name`, and **use the id it returns** — never an id you assumed, remembered, or pattern-matched from another stop. The route fetches in the next step depend on this id, so they must run **after** it comes back, not in the same parallel batch as the resolution call. Firing route lookups with a guessed placeholder id makes them fail (and risks silently wiring the wrong place).
4. **Fetch BOTH adjoining legs** before replacing: the leg **into** the new stop (neighbour-before → new stop) and the leg **away** (new stop → **the removed stop's successor**). The away-neighbour is the new stop's successor — fetch the away leg to that neighbour, not to the stop being removed. The successor is whatever stop currently follows the target in the live route (it may be a stop added earlier in this conversation, not the original final destination), which is exactly why step 1 re-reads state after any prior edit.
5. **Wire the four references precisely.** `route_id_leading_to_new_waypoint` = the into-leg route; `route_id_leading_away_from_new_waypoint` = the away-leg route; name the stop being replaced and the new stop. **Never transpose leading-to and leading-away.**
6. Confirm the updated route, then stop.

### Ask vs. infer which stop
- **When state pins the target stop, act — do not ask.** If the user named the stop, or a positional reference plus the current route uniquely identifies it, proceed silently.
- **When which stop to replace is a genuine open choice, ASK.** "Replace one of my stops" does not say which; ask the user and use the stop they name — don't default to the first, the nearest, or any stop you pick.
- **Route choice follows the user's cue.** Take the route per a stated preference (`get_user_preferences`); present each leg's options and apply their pick when they choose; take the fastest yourself when they defer ("just pick") or say nothing about route selection. When the user names a specific road or via-name for a leg (e.g. "the route via B441"), match it to the corresponding alternative from the fetched routes and use that exact one — don't substitute the fastest if it differs, and confirm back which leg you set to which route.
- **When you pick the fastest per leg yourself, you must say so and open the door to alternatives — do not silently commit.** This is a multi-segment edit, so after choosing fastest legs, tell the user you took the fastest alternative for each new leg and **ask, as an explicit question, whether they want details on the other alternatives** (e.g. "Want details on the other route alternatives?"). State how many further alternatives exist per leg, but no details on them. A passive trailing mention like "there are other alternatives if you want details" does **not** count as asking — phrase it as a genuine question that invites a yes/no answer. This inform-and-offer step is required even though you acted without asking (and even when the user said "take the fastest"); skipping it, or burying it as an aside, is a failure mode even when the wiring is perfect.
- **Disclose tolls on any leg you present in detail or actually use.** If a chosen or detailed leg includes a toll road, say so explicitly. Confirming "no tolls" is fine when true, but never omit a real toll.
- **When the new stop must satisfy a constraint, verify it at the computed arrival before committing.** If the user ties the replacement to a condition — the stop must begin inside an arrival-time window, or it must sit at the same point as an open POI of a specific kind — convert the leg into the new stop to an arrival time (including any detour) and check the condition holds at *that* time (e.g. the co-located place is actually open then, the window actually contains the arrival). Only then wire the swap, and state the figure you verified. If no candidate satisfies the constraint, say so and don't replace with a near-miss while claiming it fits.

### When a capability is missing
- **Missing replace tool.** When `navigation_replace_one_waypoint` is absent, state plainly there is no tool to replace an intermediate stop in place.
- **Never abuse the add tool to fake a replace.** Inserting the "replacement" with `navigation_add_one_waypoint` and mismatched before/after ids errors; never repurpose it, and never claim a swap happened. (Inserting a stop is `navigation-add-waypoint`; removing one is `navigation-remove-waypoint`.)
- **`"unknown"` means unverifiable.** Don't invent the stop or pretend to edit.
- **Do the doable, decline the impossible — in one flow.** Complete the feasible lookups AND deliver the honest decline for the infeasible swap. Offer a permissioned fresh-route rebuild only if a start path exists and the user agrees; never start it silently.

## Principles
- **Waypoint-replace reads can run; the swap waits for both adjoining legs and exact ids.** Read current navigation, resolve the new stop, read route preferences, and fetch the into-leg and away-leg before editing. Call `navigation_replace_one_waypoint` only when the old stop, new stop, predecessor, successor, and both route ids are all live and route-consistent; do not add the replacement as an extra stop or reuse stale neighbours after earlier edits.
- **Replace needs two legs.** Fetch routes for the into-leg and the away-leg before swapping, every time — and the away leg runs to the removed stop's successor.
- **Resolve the target stop from the current route**, not from a place name alone.
- **Wire the four references precisely** — a single mis-wired id produces the wrong route; never swap leading-to and leading-away.
- **Replace exactly one, never add on top** when the user asked for a swap.
- **Ask only for a genuine unresolved choice; otherwise act.** When context names or pins the stop, asking is the failure; when it is truly open, guessing is the failure.
- **Picking fastest legs silently is not enough — close the loop.** A waypoint replace is a multi-segment route edit: after defaulting to the fastest leg routes, tell the user you took the fastest alternative and offer details on the remaining alternatives, and surface any toll. Acting correctly on the wiring but skipping this disclosure still falls short of a good outcome.
- **Never call a missing/erroring tool and never claim a swap that didn't happen.** Honest "can't" plus a real alternative beats faking it with the add tool.

## Common mistakes to avoid
- **Fetching the away leg to the stop being removed** instead of to its successor (the new stop's neighbour-after).
- **Reusing stale neighbours or route ids after an earlier edit in the same conversation** — if a stop was just added/removed/replaced, the target's successor may have changed; re-read state and recompute the legs.
- **Omitting one of the two adjoining legs** before the replace call.
- **Swapping leading-to and leading-away routes**, or naming the wrong stop to replace.
- **Asking which stop when state already pins it**, or **guessing which stop** when it is a genuine open choice.
- **Proactively picking the leg routes** when the user said they would choose.
- **Defaulting to the fastest legs without telling the user and without offering the other alternatives**, or **omitting a toll** on a leg you used or presented. Even a perfectly wired replace is incomplete if you commit to the fastest legs silently.
- **Closing the loop with a passive aside instead of a real question** — ending the turn with "there are other route alternatives if you want details" rather than actually asking "Want details on the other route alternatives?". A statement the user can ignore is not an offer; ask a question that expects an answer.
- **Adding a second waypoint instead of replacing** the named one, or **abusing `navigation_add_one_waypoint` with mismatched ids** to fake a replace — it errors.
- **Claiming an intermediate stop was replaced** when no tool did it, or **inventing a stop** when state reads `"unknown"`.
- **Committing a constrained replacement on an estimate instead of a verified match** — swapping in a stop and asserting it meets an arrival-window or open-co-located-POI condition when the arrival time wasn't actually computed against that condition, or when the only candidate is a near-miss. Verify at the computed arrival time first; if nothing fits, report that rather than forcing a swap.
- **Ending after the doable parts** without the honest decline, or **refusing the whole request** when the swap was doable.
- **Skipping the initial state read.**
- **Fabricating the new stop's id instead of using the one `get_location_id_by_location_name` returns**, or **launching the route lookups in the same parallel batch as the id resolution** so they run against a guessed id — wait for the real id, then fetch the legs.

## Procedure
1. `get_current_navigation_state(detailed_information=true)`; identify the stop to replace and its current before/after neighbours. Re-read it if any nav edit happened earlier in this conversation so the neighbours and route ids are current. If `"unknown"` or the tool is missing, refuse safely — no guessed ids.
2. If which stop to replace is unstated and a genuine open choice, ask; otherwise resolve the target from the named/positional reference against this current route.
3. `get_location_id_by_location_name(<new stop>)`.
4. `get_routes_from_start_to_destination(neighbour-before → new stop)` and `(new stop → the removed stop's successor)`; choose each per the user's cue (their pick, a stated preference via `get_user_preferences`, or fastest when deferred). When you default to fastest, plan to tell the user you took the fastest alternative for the new legs and to offer details on the other alternatives, and to flag any toll on a chosen leg.
5. Call `navigation_replace_one_waypoint` once, wiring `route_id_leading_to_new_waypoint`, `route_id_leading_away_from_new_waypoint`, `waypoint_id_to_replace`, and `new_waypoint_id` — with route-consistent ids. If the replace tool is absent, admit there's no tool to replace it in place; do not fake it with the add tool.
6. Confirm what changed; if you chose the fastest legs yourself, say so, note how many further alternatives exist per leg, and ask an explicit question offering their details (not a passive "if you want" aside), and disclose any toll on a used leg. Name anything that couldn't be done and why, then stop.
