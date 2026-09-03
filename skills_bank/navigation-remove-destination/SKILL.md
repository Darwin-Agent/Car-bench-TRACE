---
name: navigation-remove-destination
description: Drop the FINAL destination of an active route so the stop right before it automatically becomes the new endpoint — handles "remove the last stop", "I don't want to go to <the final place> anymore", "drop/skip/cancel the destination", and "shorten my trip / just end at <the prior stop>" requests. Read the current navigation state first to resolve which waypoint id is the endpoint instead of guessing from a place name, then delete that id with navigation_delete_destination (no replacement route is needed); act when the state pins the endpoint and ask only when which stop is a genuine open choice. If the delete-destination control isn't callable, dropping the final destination cannot be done — say so plainly and offer to set a fresh route to the intended new endpoint; do not try to fake it with a replace or a full reload, and never guess an id or claim a removal that nothing performed.
tools:
  - get_current_navigation_state
  - get_location_id_by_location_name
  - navigation_delete_destination
---

# Remove the final destination

A route is active and the user wants to drop the **final destination** so the previous stop becomes the new end. This needs no replacement route — `navigation_delete_destination` makes the prior stop the endpoint automatically. You read the current state to resolve exactly which id is the endpoint, then delete it. "Shorten my trip / just end at <the prior stop>" is the same operation: the place they want to stop at is already the waypoint before the current endpoint, so removing the endpoint is all that's needed. The same method covers the clear request, the under-specified one, and the case where the control to do it is unavailable.

## When this applies
"Remove the last stop", "I don't want to go to <the final place> anymore", "skip / drop / cancel the destination", "shorten my trip so it ends at <the stop before the end>" — while navigation is active and the endpoint is what's being removed. To *change* the endpoint to a different new place rather than drop it, see `navigation-change-destination`. Removing an *intermediate* stop (one with stops both before and after it) is a different operation, not this one. If the user asks to remove the endpoint AND another stop in the same turn, the endpoint removal is this skill's job done first; the additional stop is then handled separately and sequentially (see Method step 5).

## Tools
- `get_current_navigation_state({detailed_information:true})` — read the ordered waypoint list and start. This is how you map "the last stop" / a named place to the endpoint id, so it is the precondition for any safe edit.
- `get_location_id_by_location_name({location})` — resolve a named place only if you need to confirm it matches the current endpoint.
- `navigation_delete_destination({destination_id_to_delete})` — delete the **endpoint**; the previous stop automatically becomes the new final destination. No replacement route, no other argument needed.

Before acting, confirm `navigation_delete_destination` is actually callable and read every result honestly. If a value you need to identify the endpoint comes back as the literal `"unknown"`, treat it as genuinely unverifiable — not as an empty list or a guessed id.

## Method
1. **Read current navigation state first** with the detailed flag. The waypoint list is how you map the user's words to the endpoint id — never guess the id from a place name in the conversation. If you cannot read the route, or the deciding id is unverifiable, you cannot safely edit — say so; don't guess.
2. **Resolve the endpoint id.** "Final destination" / "the last stop" → the last entry in the waypoint list; a named place → confirm it matches the current endpoint (resolve the name only if needed). The stop the user names as the new end should already be the entry just before that endpoint — a quick sanity check, not a second deletion.
3. **Delete the endpoint** with `navigation_delete_destination`, passing the resolved id. No route lookup or replacement route is required — the prior stop becomes the new end automatically.
4. **Confirm the resulting route** (the new endpoint) and stop. Don't fan out to other navigation edits.
5. **If more stops must also go, do them one at a time, never in parallel.** After deleting the endpoint, re-read the state — the stop that was second-to-last is now the endpoint (or what was an intermediate stop may now sit differently). Removing a stop that is now the *endpoint* repeats this skill (`navigation_delete_destination`); removing one that is still *intermediate* is a different operation that needs a single replacement route from its previous stop to its next stop. Each edit reorders the indexes, so re-read between edits and act sequentially rather than firing edits together. If the tool for one of the removals isn't callable (e.g. the intermediate-stop control is gone), still perform the part you can — delete the endpoint — then in the same answer say plainly which stop you couldn't remove and offer the fresh-route alternative. Fulfil the doable part rather than refusing the whole request.

### Ask vs. infer which stop
- **When state pins the endpoint, act — do not ask.** "The last stop", or a named place that the current waypoint list resolves uniquely to the endpoint, needs no question; proceed directly. Read the deciding state once — don't re-read in a loop.
- **When which stop is a genuine open choice, ASK.** If the words don't pin the endpoint (e.g. they could mean a stop that isn't the end), confirm before deleting — don't assume.

### When a capability is missing
- **Can't read the route.** If you cannot call the tool that reports the navigation state, you cannot resolve the endpoint id — tell the user you can't verify the active route and so can't safely remove the endpoint. Don't invoke a delete with a guessed id even if the delete tool itself is callable.
- **The delete-destination control isn't callable.** Then dropping the final destination simply cannot be done here, and there is no valid substitute. `navigation_replace_final_destination` does NOT achieve it: re-pointing the endpoint onto the prior stop would need a route whose start is that same prior stop (a degenerate stop-to-itself route), so the call just errors. A full reload / delete-current-navigation would wipe the whole route, not drop one endpoint, and errors or over-acts while a route is active. So state plainly you have no control to remove just the final destination here; offer the adjacent thing you *can* do — look up, and with permission set, a fresh route ending at the stop they want as the new endpoint.
- **No faking.** Don't "try replace anyway," don't substitute a tool that errors or lands on a different state, and never claim the destination was removed when nothing performed it. An honest "I can't do that part" beats a fabricated success.

## Principles
- **Endpoint reads can run; deleting the destination needs the live endpoint id.** Read current navigation and, if needed, resolve a named place to verify it matches the final destination. Call `navigation_delete_destination` only when the user is clearly removing the endpoint and the destination id comes from the current route; do not fetch replacement routes, rebuild the trip, replace the endpoint, or delete an intermediate stop as a substitute.
- **Read before you delete.** The id you pass must come from the current waypoint list, not from a place name in the conversation.
- **Endpoint removal needs no replacement route** — the prior stop becomes the end automatically; don't fetch or pass a route.
- **`navigation_delete_destination` is the only tool that does this.** When it's callable, use it directly and stop. When it isn't, removing the final destination is genuinely impossible — name the honest gap and a fresh-route alternative instead of improvising a substitute.
- **Don't reach for replace-final-destination or a full reload to fake a drop.** Replace would error on the degenerate route; reload destroys the whole route. Either is wrong for this operation.
- **Ask only for a genuine unresolved choice; otherwise act.** Asking when state pins the endpoint is the failure; guessing when it is truly open is the failure.

## Common mistakes to avoid
- **Guessing the id from the place name** instead of reading the waypoint list, or **inventing one** when the deciding value is unverifiable.
- **Fetching or passing a replacement route** for an endpoint removal — none is needed.
- **Trying `navigation_replace_final_destination` to drop the endpoint** when the delete tool is gone — it requires a stop-to-itself route and errors; this is the wrong fix, decline honestly instead.
- **Using a full-reload / delete-current-navigation tool to "shorten" the trip** — it wipes everything and errors while active; it does not drop a single endpoint.
- **Asking which stop when state already pins it**, or **guessing** when it is a genuine open choice.
- **Claiming the destination was removed** when no tool actually did it.
- **Looping** on the same refusal or state read instead of answering and offering the fresh-route option.
- **Firing multiple deletions in parallel** when several stops must go — each edit shifts the waypoint indexes, so re-read state and remove them one at a time in sequence.
- **Refusing the whole multi-stop request because one removal isn't possible** — when several stops should go and only some are doable, complete the doable ones (delete the endpoint you can), then name the stop you couldn't remove and offer the fresh-route option in the same answer.

## Procedure
1. `get_current_navigation_state(detailed_information=true)`; if you can't read it or the deciding id is unverifiable, refuse safely and offer a forward option — no guessed ids.
2. Resolve the endpoint id from the waypoint list (the last entry, or a named place confirmed against it). If which stop is a genuine open choice, ask; otherwise act.
3. `navigation_delete_destination(destination_id_to_delete=<that id>)`. If this control isn't callable, say plainly you can't remove just the final destination here; don't fake it with replace-final-destination (it errors) or a full reload (it wipes the route). Offer to set a fresh route ending at the intended new endpoint instead.
4. Confirm the new endpoint, name anything you couldn't do, and stop.
