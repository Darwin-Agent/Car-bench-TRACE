---
name: navigation-remove-waypoint
description: Remove a stop OR the final destination from an active route. First read get_current_navigation_state(detailed) to map the user's words to a waypoint id — never guess from a place name — then branch on the target's position. Removing the FINAL destination uses navigation_delete_destination (no replacement route; the last intermediate stop becomes the new destination, and a multi-stop route must still exist or policy blocks it). Removing an INTERMEDIATE stop uses navigation_delete_waypoint and REQUIRES a replacement route for the now-direct leg: fetch get_routes_from_start_to_destination for start→the stop AFTER the removed one, then choose — a stated/stored route preference wins; if other stops still follow take the fastest segment by default AND in the confirmation say you took the fastest and offer details on the alternatives (flag tolls); if only start+destination remain present fastest and shortest and ASK when they differ. Ask which stop only when genuinely open, act when state pins it; keep "find but don't add" info-only; and when the delete tool you need isn't callable, verify that BEFORE fetching routes or asking, admit plainly you can't remove that stop while keeping the route active, offer a permissioned fresh route, and never fake it with replace/add or set_new_navigation (errors while active).
tools:
  - get_current_navigation_state
  - get_routes_from_start_to_destination
  - get_location_id_by_location_name
  - navigation_delete_waypoint
  - navigation_delete_destination
---

# Remove a stop or destination from a route

A route is active and the user wants to drop one of its waypoints. The same method handles the clear case, the under-specified one (which stop?), and the missing-capability one (no delete tool callable). The first decision after reading the state is **which kind of waypoint** the target is, because the two cases use different tools and have different preconditions:

- **The final destination** (the user wants the trip to *end earlier* — "make X my last stop", "I don't want to continue to Y", "cancel the destination") → `navigation_delete_destination`. No replacement route is needed: the last intermediate stop simply becomes the new destination.
- **An intermediate stop** (the user wants to *skip the middle* and go direct over that leg) → `navigation_delete_waypoint`, which **requires a replacement route** for the leg that becomes direct.

You always read the current navigation state first to resolve which waypoint is meant and where it sits. The recurring twist in this operation: the specific delete tool you need is **often the missing one** — frequently there is no way to remove that waypoint while keeping the route active, and the honest answer is then a clear "no" plus a forward offer.

## When this applies
"Drop the middle stop and go straight there", "skip the intermediate stop", "I don't need to stop at <a named place> anymore", "remove <place> from my route", "cancel <the final place>", "make <place> my final destination / last stop", "I don't want to continue to <endpoint>" — while navigation is active. It covers removing an intermediate stop *and* removing the final endpoint, because both are "take a waypoint out of my active route". (To *swap* a stop or destination for a different place, that is `navigation-change-destination` / a replace skill, not this one — removal shortens the route, replacement keeps the same number of stops.)

## Tools
- `get_current_navigation_state({detailed_information:true})` — read the ordered waypoint list (index 0 is the start, last index is the destination, anything between is intermediate), the start, and the current routes. This is how you map the user's words to the right id. **May be missing**, or **may return `"unknown"`** for the waypoint/route fields (then the ids are unreadable and you cannot safely edit).
- `get_routes_from_start_to_destination({start_id, destination_id})` — fetch route alternatives for the leg that becomes direct once an **intermediate** stop is gone: start → the stop **after** the removed one. Not needed when removing the final destination.
- `get_location_id_by_location_name({location})` — resolve a named place to an id when needed (use the city main name only).
- `navigation_delete_waypoint({route_id_without_waypoint, waypoint_id_to_delete})` — delete an **intermediate** stop, supplying the chosen route for the now-direct leg. Only works while navigation is active and a multi-stop route is set.
- `navigation_delete_destination({destination_id_to_delete})` — delete the **final destination**; the previous waypoint becomes the new destination. Only works while active and a multi-stop route is set — a route must always keep at least a start and a destination, so this is blocked when there is no intermediate stop left to promote.

Either delete tool **may be absent** for a given request — verify the one you actually need is callable before relying on it.

## Method
1. **Read current navigation state first.** Always call `get_current_navigation_state` with the detailed flag before deleting. The waypoint list is how you map the user's words to the id — don't guess from a place name in the conversation. If the tool is missing or returns `"unknown"` for the waypoints/routes, you cannot safely edit — say so plainly and offer a permissioned fresh route; don't invent ids.
2. **Resolve which waypoint they mean and classify its position.** A named place → the matching entry; "the middle/intermediate stop" or a positional reference → the corresponding entry, resolved against the current list. Then classify: index 0 is the start (cannot be removed); the **last** entry is the final destination (→ delete-destination branch); anything strictly between is intermediate (→ delete-waypoint branch). Get this right — feeding a final destination to `navigation_delete_waypoint`, or an intermediate stop to `navigation_delete_destination`, is wrong.
3. **Confirm the tool for that branch is callable before going further.** If you are removing the final destination, check `navigation_delete_destination` is present; if an intermediate stop, check `navigation_delete_waypoint`. Do this *before* fetching any replacement route or asking the user a route-selection question — if the needed tool is absent there is nothing to do with the answer, so go straight to the missing-capability response below.
4. **Destination branch:** call `navigation_delete_destination({destination_id_to_delete})` directly — no replacement route, no route-choice question. (A multi-stop route must remain afterward; if the route is already just start+destination, deleting the destination is not allowed.)
5. **Intermediate branch:** call `get_routes_from_start_to_destination` for start → the stop that **follows** the one being removed, choose the route by what the route becomes after removal (see "Choosing the replacement route"), then call `navigation_delete_waypoint({route_id_without_waypoint:<chosen>, waypoint_id_to_delete:<the stop>})`.
6. Confirm the resulting route, then stop. For multiple sequential removals, re-read the state between each edit before resolving the next id.

### Ask vs. infer which waypoint
- **When state pins the target, act — do not ask.** A named place, or a positional reference that the current waypoint list resolves uniquely, needs no clarification; proceed directly. If the user already said which stop, never re-ask it.
- **When which waypoint to remove is a genuine open choice, ASK.** "Drop one of my stops" with nothing naming or pinning which → ask the user; don't default to the first, the nearest, or any stop you pick.

### Choosing the replacement route (intermediate branch only)
The collapsed leg may return several alternatives. How you pick depends on **what the route becomes after the removal**, not just on whether the user "deferred":
- **A stated request or stored route preference always wins** (e.g. "the one via A11/A51", "the shortest", "always fastest"). Match the named via-roads / shortest / fastest alias to the returned alternative and use it. Reading a `route_selection` preference once when no explicit cue is given is fine; don't loop or re-ask if it comes back empty.
- **The removal still leaves other stops after the destination of this leg (route stays multi-stop):** take the **fastest** alternative for this segment by default, and in your confirmation do BOTH: tell the user you took the fastest alternative AND ask whether they want more information on the other route alternatives — this mirrors the multi-stop policy and a confirmation that omits the offer of alternatives is incomplete. Still flag a toll road if the chosen segment has one. (Do not list the other alternatives' details unprompted — just note there are others and offer them.)
- **The removal leaves only a start and a single destination (the leg becomes the entire route):** treat it like presenting a fresh route. If the fastest and shortest **coincide**, use that one and proceed without asking. If they **differ**, present both the fastest and the shortest with their distance/duration and **ask which to use** — do NOT silently grab the fastest. Inform about tolls on any route you present in detail. Only an explicit user cue or stored preference lets you skip the question.

### When a capability is missing
- **The needed delete tool is absent (the common case).** Detect this *before* fetching the replacement leg or asking the user to choose a route — pulling alternatives and asking "fastest or shortest?" for a removal you cannot perform wastes the user's decision and is itself a failure. State plainly there is no tool to remove that waypoint while keeping the route active (name it as the final destination or the mid-route stop, as applicable). Pair the honest "no" with a forward offer: a permissioned fresh route reflecting what they wanted, set only if the user agrees — never start it silently, and don't refuse with no alternative.
- **No faking.** A delete-then-replace chain to mimic the operation errors, replace/add tools cannot collapse a leg or drop an endpoint, and `set_new_navigation` errors while a route is active. Don't "try it anyway."
- **`"unknown"` means unverifiable.** If the state read returns `"unknown"` for the waypoints/routes, treat it as genuinely unreadable — never invent a waypoint or claim a removal you couldn't ground, and don't re-read in a loop expecting a value.
- **Info-only stays info-only.** "Find but don't add" a charger/POI on the new leg means search and report only (see `poi-search`) — no route mutation. Ground the search point too: derive *where* to look from the battery range (the distance until a sensible low-charge buffer, e.g. via `get_distance_by_soc`) or ask the user which buffer to use — don't invent an arbitrary `at_kilometer`, which yields an unfounded result.
- **Do the doable, refuse the impossible — together.** If the user asks for two removals and only one tool is present, perform the one you can, confirm it, and clearly name the part you could not do and why, in one answer.

## Principles
- **Waypoint-removal reads can run; deletion needs a classified live route target.** Read current navigation, resolve names when helpful, and fetch a replacement route only for an intermediate stop whose removal collapses a leg. Call `navigation_delete_waypoint` or `navigation_delete_destination` only after the target is identified from the live waypoint list, classified as intermediate vs final, and any needed route choice is settled; never fake removal with add/replace/new-navigation tools.
- **Read before you delete.** The id you pass must come from the current waypoint list, not from a place name in the conversation.
- **Classify the waypoint, then pick the matching tool.** Final destination → `navigation_delete_destination` (no replacement route). Intermediate stop → `navigation_delete_waypoint` (replacement route required). Misclassifying sends the right intent to the wrong tool.
- **An intermediate delete needs a replacement route** for the collapsed leg — fetch start → the stop after the removed one first, choose per the rule above, and pass it as `route_id_without_waypoint`. A destination delete needs none.
- **The replacement choice is not always "just take the fastest."** When the deletion turns the route into a bare start→destination and the fastest and shortest differ, surfacing both and asking is correct; auto-picking the fastest there is a real failure. When other stops remain (still multi-stop), the fastest segment by default is correct — but you must still tell the user you took the fastest and offer the alternatives. A stated request or stored preference overrides both.
- **The delete tools are the right tools — and the honest gap when one is absent.** Replace/add tools and `set_new_navigation` (which errors while active) are not substitutes.
- **Ask only for a genuine unresolved choice; otherwise act.** Asking when state pins the waypoint is the failure; guessing when it is truly open is the failure.
- **Do the doable, refuse the impossible — together.** A fake removal is worse than an honest "no."

## Common mistakes to avoid
- **Treating the final destination as an intermediate stop, or vice versa.** If the target is the last waypoint, use `navigation_delete_destination` (no replacement route); if it is between start and destination, use `navigation_delete_waypoint` with a replacement leg. Don't feed one to the other's tool.
- **Calling `navigation_delete_waypoint` without a `route_id_without_waypoint`**, or with a route that ignores the user's stated/stored preference.
- **Fetching or asking about a replacement route when removing the final destination** — the destination delete needs no leg and no route choice.
- **Silently grabbing the fastest replacement when the route collapses to a bare start→destination and the fastest and shortest differ** — present both and ask there. (When the route stays multi-stop, the default-fastest segment is fine.)
- **Taking the fastest segment for a still-multi-stop route but not telling the user you chose it, or not offering the other alternatives.** When you default to the fastest, your confirmation must say you took the fastest AND ask if they want details on the alternatives; a bare "done, removed it" is incomplete.
- **Re-asking or ignoring a route the user already named** (a specific via, "shortest", "fastest") — match it to the returned alternative and use it.
- **Fetching the direct leg to the removed stop** instead of to the stop that follows it.
- **Guessing the id from the place name** instead of reading the waypoint list, or **inventing one** when state reads `"unknown"`.
- **Using a replace/add tool to "collapse" the leg or "drop" the endpoint, or `set_new_navigation`** (which errors while active) to fake the removal.
- **Asking which waypoint when state already pins it**, or **guessing** when it is a genuine open choice.
- **Claiming a waypoint was removed** when no tool did it.
- **Adding a charging station / POI the user told you only to find** (it stays info-only — see `poi-search`), or **searching at a made-up `at_kilometer`** instead of grounding the point in battery range (`get_distance_by_soc`) or a user-chosen buffer.
- **Fetching replacement routes and asking "fastest or shortest?" when the needed delete tool is absent** — confirm the tool is callable before involving the user in any route choice.
- **Refusing without a forward offer.** Honest "no" alone is weaker than the same "no" paired with a permissioned fresh-route alternative — always offer the way forward.
- **Not re-reading the state between two sequential edits**, which lets stale ids slip into the second call.

## Procedure
1. `get_current_navigation_state(detailed_information=true)`; if missing or `"unknown"`, refuse safely and offer a forward option — no guessed ids.
2. Resolve the target from the waypoint list and classify it: start (index 0, cannot remove), final destination (last entry), or intermediate (between). If which waypoint is a genuine open choice, ask; otherwise act on the named/positional reference.
3. **If the target is the final destination:** check `navigation_delete_destination` is callable. If absent, stop here — admit there's no tool to remove only the final destination while keeping the route active, offer a permissioned fresh route, and don't fetch routes. If present, call `navigation_delete_destination(destination_id_to_delete=<the destination>)` (no replacement route).
4. **If the target is an intermediate stop:** check `navigation_delete_waypoint` is callable. If absent, stop here — admit there's no tool to remove a mid-route stop while keeping the route active, offer a permissioned fresh direct route, and don't fetch routes or ask a route-choice question. If present, `get_routes_from_start_to_destination(start → the stop after the removed one)`, choose the route (stated/stored preference wins; else if stops still follow take the fastest segment by default and in the confirmation say you took the fastest and offer details on the alternatives; else when the route becomes bare start→destination use the route if fastest and shortest coincide, otherwise present both and ask which), then `navigation_delete_waypoint(route_id_without_waypoint=<chosen>, waypoint_id_to_delete=<the stop>)`.
5. If asked to find (not add) charging/POIs on the new leg, that's info-only via `poi-search` — gather and report, no route change.
6. For multiple removals in one turn, re-read the state between edits before resolving the next id; do every doable removal, then confirm what changed and clearly name any part no available tool could do.
