---
name: navigation-remove-destination
description: Remove the FINAL destination of an active route with navigation_delete_destination — the previous stop automatically becomes the new endpoint, so no replacement route is needed — after reading nav state first to resolve the endpoint's id from the current waypoint list rather than guessing from a place name; act when state pins which stop is the end and ask only when genuinely open, and when the delete tool is missing or state reads "unknown", admit there's no tool to drop the endpoint while keeping the route active and never fake it with set_new_navigation (errors while active) or a replace tool.
tools:
  - get_current_navigation_state
  - get_location_id_by_location_name
  - navigation_delete_destination
---

# Remove the final destination

A route is active and the user wants to drop the **final destination** so the previous stop becomes the new end. This needs no replacement route — `navigation_delete_destination` makes the prior stop the endpoint automatically. You read the current state to resolve exactly which id is the endpoint, then delete it. The twist: the delete tool may be stripped, or the state may read back as `"unknown"`.

## When this applies
"Remove the last stop", "I don't want to go to <the final place> anymore", "skip the end / drop the destination" — while navigation is active and the endpoint is what's being removed. (To remove an intermediate stop, see `navigation-remove-waypoint`; to *change* the endpoint to a new place, see `navigation-change-destination`.)

## Tools
- `get_current_navigation_state({detailed_information:true})` — read the ordered waypoint list and start. This is how you map "the last stop" / a named place to the endpoint id. **May be missing** (then you cannot verify the route) or **may return `"unknown"`** fields (then the id is unreadable).
- `get_location_id_by_location_name({location})` — resolve a named place when needed to confirm it matches the current endpoint.
- `navigation_delete_destination({destination_id_to_delete})` — delete the **endpoint**; the previous stop automatically becomes the new final destination. No replacement route needed. **May be missing.**

## Method
1. **Read current navigation state first.** Always call `get_current_navigation_state` with the detailed flag before deleting. The waypoint list is how you map the user's words to the endpoint id — don't guess from a place name in the conversation. If the tool is missing or returns `"unknown"`, you cannot safely edit — say so; don't guess the id.
2. **Resolve the endpoint id.** "Final destination" / "the last stop" → the last entry; a named place → confirm it matches the current endpoint (resolve the name if needed).
3. **Delete the endpoint** with `navigation_delete_destination`, passing the resolved id. No route lookup is required — the prior stop becomes the new end automatically.
4. Confirm the resulting route (the new endpoint), then stop.

### Ask vs. infer which stop
- **When state pins the endpoint, act — do not ask.** "The last stop", or a named place that the current waypoint list resolves uniquely to the endpoint, needs no question; proceed directly.
- **When which stop is a genuine open choice, ASK.** If the user's words don't pin the endpoint (and could mean an intermediate stop), confirm before deleting — don't assume.

### When a capability is missing
- **Missing delete tool.** When `navigation_delete_destination` is absent, state plainly there is no tool to remove the final destination while keeping the route active.
- **No faking.** `set_new_navigation` errors while a route is active, and a replace tool changes the endpoint rather than dropping it — neither is a stand-in. Don't "try it anyway."
- **`"unknown"` means unverifiable.** Never invent the endpoint or claim a removal you couldn't ground.
- **Do the doable, refuse the impossible — together.** Offer a forward path (e.g. a permissioned fresh route to the intended new end) only with the user's permission; never call an erroring tool.

## Principles
- **Read before you delete.** The id you pass must come from the current waypoint list, not from a place name in the conversation.
- **Endpoint removal needs no replacement route** — the prior stop becomes the end automatically; don't fetch or pass a route.
- **`navigation_delete_destination` is the right tool — and the honest gap when absent.** Don't fake it with `set_new_navigation` (errors while active) or a replace tool.
- **Ask only for a genuine unresolved choice; otherwise act.** Asking when state pins the endpoint is the failure; guessing when it is truly open is the failure.
- **Do the doable, refuse the impossible — together.** A fake removal is worse than an honest "no."

## Common mistakes to avoid
- **Guessing the id from the place name** instead of reading the waypoint list, or **inventing one** when state reads `"unknown"`.
- **Fetching/passing a replacement route** for an endpoint removal — none is needed.
- **Using a replace tool or `set_new_navigation`** (which errors while active) to fake the removal.
- **Removing an intermediate stop** when the user meant the endpoint, or vice versa.
- **Asking which stop when state already pins it**, or **guessing** when it is a genuine open choice.
- **Claiming the destination was removed** when no tool did it.
- **Doing nothing while refusing** when a forward option (a permissioned fresh route) was available.
- **Looping** on the same refusal or state read instead of answering and offering an option.

## Procedure
1. `get_current_navigation_state(detailed_information=true)`; if missing or `"unknown"`, refuse safely and offer a forward option — no guessed ids.
2. Resolve the endpoint id from the waypoint list (the last entry, or a named place confirmed against it). If which stop is a genuine open choice, ask; otherwise act.
3. `navigation_delete_destination(destination_id_to_delete=<that id>)`. If the tool is absent, admit no such tool; don't fake it with `set_new_navigation` or a replace tool.
4. If the user also wants an intermediate stop removed, that is the sibling skill `navigation-remove-waypoint` — and state must be **re-read** between sequential edits before resolving the next id. Do the doable removal and confirm it; name the part for the other skill.
5. Confirm what changed, name what couldn't, and stop.
