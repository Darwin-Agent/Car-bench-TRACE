---
name: navigation-remove-waypoint
description: Remove an INTERMEDIATE stop from an active route with navigation_delete_waypoint, which REQUIRES a replacement route for the now-direct leg — read nav state first to resolve the stop's id, fetch get_routes_from_start_to_destination for start→the stop after the removed one, pick per the user's cue, and pass it as route_id_without_waypoint; ask which stop only when genuinely open and act when state pins it, keep "find but don't add" info-only (point at poi-search), and since this tool is OFTEN missing, admit there's no tool to remove a mid-route stop while keeping the route active, offer a permissioned fresh route, and never fake it with replace/add or set_new_navigation (errors while active).
tools:
  - get_current_navigation_state
  - get_routes_from_start_to_destination
  - get_location_id_by_location_name
  - navigation_delete_waypoint
---

# Remove an intermediate waypoint

A route is active and the user wants to drop an **intermediate** stop so the route goes direct over that leg. Unlike removing the endpoint, this **requires a replacement route** for the leg that becomes direct: you fetch routes for start → the stop that follows the removed one, pick per the user's cue, and pass it to `navigation_delete_waypoint`. You read the current state to resolve which stop is meant. The twist: this is **often** the missing tool — there is frequently no way to remove a mid-route stop while keeping the route active.

## When this applies
"Drop the <intermediate> stop and go straight there", "skip the middle stop", "I don't need to stop at <a named intermediate place> anymore" — while navigation is active and the stop is intermediate (not the endpoint). (To remove the final destination, see `navigation-remove-destination`; to swap a stop for another, see `navigation-replace-waypoint`.)

## Tools
- `get_current_navigation_state({detailed_information:true})` — read the ordered waypoint list, the start, and the current routes. This is how you map the user's words to the stop's id. **May be missing** or **may return `"unknown"`** fields (then the ids are unreadable).
- `get_routes_from_start_to_destination({start_id, destination_id})` — fetch routes for the leg that becomes direct once the stop is gone: start → the stop **after** the removed one.
- `get_location_id_by_location_name({location})` — resolve a named place when needed.
- `navigation_delete_waypoint({route_id_without_waypoint, waypoint_id_to_delete})` — delete an **intermediate** stop, supplying the chosen route for the now-direct leg. **Often the missing one** — there is frequently no tool to remove a mid-route stop.

## Method
1. **Read current navigation state first.** Always call `get_current_navigation_state` with the detailed flag before deleting. The waypoint list is how you map the user's words to the id — don't guess from a place name. If the tool is missing or returns `"unknown"`, you cannot safely edit — say so; don't guess ids.
2. **Resolve which intermediate stop they mean.** A named place → the matching entry; "the middle stop" / a positional reference → the corresponding intermediate entry, resolved against the current waypoints.
3. **Fetch the new direct leg first.** Call `get_routes_from_start_to_destination` for start → the stop that **follows** the one being removed, pick the route per the user's cue, and pass its id as `route_id_without_waypoint`.
4. **Delete the intermediate stop** with `navigation_delete_waypoint`, passing the chosen replacement route and the stop's id.
5. Confirm the resulting direct route, then stop.

### Ask vs. infer which stop
- **When state pins the target, act — do not ask.** A named place, or a positional reference that the current waypoint list resolves uniquely, needs no question; proceed directly.
- **When which stop to remove is a genuine open choice, ASK.** "Drop one of my stops" without anything naming or pinning which → ask the user and use the stop they name — don't default to the first, the nearest, or any stop you pick.
- **Route choice follows the user's cue.** Take the route per a stated preference; use their pick when they choose; take the fastest yourself when they defer ("just pick").

### When a capability is missing
- **Missing delete tool (the common case).** When `navigation_delete_waypoint` is absent, state plainly there is no tool to remove a mid-route stop while keeping the route active. Offer a permissioned fresh direct route only if a start path exists and the user agrees; never start it silently.
- **No faking.** A delete-endpoint-then-replace chain to mimic this errors, replace/add tools cannot collapse a leg, and `set_new_navigation` errors while a route is active. Don't "try it anyway."
- **`"unknown"` means unverifiable.** Never invent a waypoint or claim a removal you couldn't ground.
- **Info-only stays info-only.** "Find but don't add" a charger/POI on the new leg means search and report only (point at `poi-search`) — no route mutation.

## Principles
- **Read before you delete.** The id you pass must come from the current waypoint list, not from a place name in the conversation.
- **An intermediate delete needs a replacement route** for the collapsed leg — fetch start → the stop after the removed one first, choose per the cue, and pass it as `route_id_without_waypoint`.
- **`navigation_delete_waypoint` is the right tool — and the honest gap when absent.** Replace/add tools and `set_new_navigation` (errors while active) are not substitutes.
- **Ask only for a genuine unresolved choice; otherwise act.** Asking when state pins the stop is the failure; guessing when it is truly open is the failure.
- **Info-only stays info-only.** "Find but don't add" means search and report, no route mutation.
- **Do the doable, refuse the impossible — together.** A fake removal is worse than an honest "no."

## Common mistakes to avoid
- **Calling `navigation_delete_waypoint` without a `route_id_without_waypoint`**, or with a route that ignores the user's preference.
- **Fetching the direct leg to the removed stop** instead of to the stop that follows it.
- **Guessing the id from the place name** instead of reading the waypoint list, or **inventing one** when state reads `"unknown"`.
- **Using a replace/add tool to "collapse" the leg, or `set_new_navigation`** (which errors while active) to fake the removal.
- **Asking which stop when state already pins it**, or **guessing** when it is a genuine open choice.
- **Claiming the stop was removed** when no tool did it.
- **Adding a charging station / POI the user told you only to find** (it stays info-only — see `poi-search`).
- **Refusing the whole thing** when a forward option (a permissioned fresh direct route) was available, or **looping** on the same refusal.

## Procedure
1. `get_current_navigation_state(detailed_information=true)`; if missing or `"unknown"`, refuse safely and offer a forward option — no guessed ids.
2. Resolve the intermediate stop from the waypoint list. If which stop is a genuine open choice, ask; otherwise act on the named/positional reference.
3. Only if `navigation_delete_waypoint` exists: `get_routes_from_start_to_destination(start → the stop after the removed one)`, choose the route per the user's cue, then `navigation_delete_waypoint(route_id_without_waypoint=<chosen>, waypoint_id_to_delete=<the stop>)`. If the tool is absent, admit no such tool; offer a permissioned fresh direct route; don't fake it.
4. If asked to find (not add) charging/POIs on the new leg, that's info-only via `poi-search` — gather and report, no route change.
5. If the user also wants the final destination removed, that is the sibling skill `navigation-remove-destination` — and state must be **re-read** between sequential edits before resolving the next id. Do the doable removal, confirm it; name the part for the other skill.
6. Confirm what changed, name what couldn't, and stop.
