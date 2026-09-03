---
name: navigation-start
description: Start fresh navigation when none is active — resolve the destination, fetch route options, resolve the route by the user's cue (their pick, the stored preference for "my usual", fastest when they defer), and activate with set_new_navigation, the activation tool that errors while a route is already running; also commit a multi-leg trip with a charging stop in ONE set_new_navigation carrying every leg's route id in order (charger leg then onward leg), never set-to-charger-then-append, single-leg-only, or set-then-delete-then-reset; ask only for a genuine open route choice, and when the start tool is missing or its route-id input is removed, do every lookup, present the route id(s), and honestly admit you can't activate rather than fabricating a route id or claiming it started.
tools:
  - get_current_navigation_state
  - get_location_id_by_location_name
  - get_routes_from_start_to_destination
  - get_user_preferences
  - set_new_navigation
---

# Start new navigation

No navigation is active and the user wants to begin one. You resolve the destination, fetch real route options from the current start, resolve which route per the user's cue, and **activate** it with `set_new_navigation` — the tool for a fresh start, which errors if a route is already running. A multi-leg trip that includes a charging stop is the same operation with more than one leg: resolve each leg's routes, then commit them all in a **single** `set_new_navigation` call, in order. The twist: the start tool may be missing, or its required route-id parameter removed, so navigation can't actually be activated.

## When this applies
"Navigate to <place>", "take me to <place>, start the fastest route", "set a route to <place> but charge first / where my buffer runs out" — when **no** navigation is currently active. (If a route is already active and the endpoint changes, that is `navigation-change-destination`. Adding/removing a stop on an active route is the other navigation skills.)

## Tools
- `get_current_navigation_state({detailed_information})` — confirm nothing is active before starting. **May be the missing tool** — then you cannot read or verify whether a route is running.
- `get_location_id_by_location_name({location})` — resolve a destination / named place to an id. Returns nothing when the place is not in the database — that is the clarify trigger.
- `get_routes_from_start_to_destination({start_id, destination_id})` — fetch route options (fastest/shortest/alternatives) for each leg, from the current start (or, for an onward leg, from the charger).
- `get_user_preferences()` — read a standing route preference when the user invokes their usual route, instead of asking.
- `set_new_navigation({route_ids})` — **activate** navigation when none is running. Pass every leg's route id in order for a multi-leg trip. **Errors while a route is already active.** **Its required route-id parameter may be removed**, so calling it can't actually activate navigation.

## Method
1. **Read state to confirm nothing is active.** If `get_current_navigation_state` shows a route running, this is not a start (point at `navigation-change-destination`). If the state tool is missing, admit you can't verify, and pivot to the lookups you can still do.
2. **Resolve the destination(s) to ids** with `get_location_id_by_location_name`. A place that doesn't resolve is a clarify, not a silent substitute.
3. **Fetch route options for each leg.** Single trip: current start → destination. Multi-leg with a charging stop: current start → charger, then charger → final destination.
4. **Resolve each leg's route by the cue** (see Ask vs. infer), then **activate with `set_new_navigation`** — passing the chosen route, or **all** legs' route ids in order for a multi-leg trip.
5. Confirm the destination and active route(s), then stop.

### The multi-leg charging trip — ONE call, all legs in order
When the trip is charger-leg + onward-leg, fetch both legs' routes, then issue a **single** `set_new_navigation` carrying both route ids in order (charger leg first, then the onward leg). Do **not** set navigation to the charger and then separately add the final stop, do **not** set only the first leg, and do **not** set-then-delete-then-reset — each split is a wrong action even when the end state looks similar. Picking/finding the charger itself is `poi-search`; the charge-time / state-of-charge math is `ev-range-feasibility`; a reserve phone call is `place-phone-call`, placed **last** after navigation is fully set. Reference those by name — this skill only commits the legs.

### Ask vs. infer the route
- **User names a route, or has a standing preference → use it.** Apply exactly the route they selected; read `get_user_preferences` when they invoke their usual route rather than asking.
- **User defers ("just pick", "fastest is fine") → take the fastest yourself**, don't bounce it back as a question.
- **User will choose → present options and apply their pick.** ASK here only because the choice is genuinely theirs; don't silently commit one. Don't ask when the cue already settles it.
- **Per-leg differences hold:** when a main leg is tied to the user's preference, resolve it silently from `get_user_preferences`; legs the user didn't tie to a preference take the fastest heuristic. Don't ask when context already pins the choice.

### When a capability is missing
- **Missing state tool.** When `get_current_navigation_state` is absent you cannot verify whether a route is running. Don't claim nav is or isn't active; pivot to looking up routes to a destination the user names.
- **Missing start tool / removed route-id parameter.** When `set_new_navigation` is gone, or its required route input is removed, navigation cannot actually be started — while every other tool still works. Do the full lookup (resolve destination(s), fetch every leg's routes honouring each leg's cue), present the **exact route id(s)** and key details the start would need, and plainly admit you can't activate it. Never claim navigation started, never fabricate a route id.
- **Unresolvable place → ask.** If a named place doesn't resolve, tell the user and let them correct it; don't silently pick a similar-sounding place.
- **Reach the resolution, don't loop.** Carry the conversation to the explicit "can't start it, here are the route id(s)" close; re-supply the ids if asked, reiterate you can't activate, then stop.

## Principles
- **`set_new_navigation` is the activation tool when nothing is active** — and the honest gap when its input is missing. Don't reach for a replace/add-stop tool to start from scratch, and never call it while a route is active (it errors).
- **One call, all legs, in order.** A multi-leg charging trip commits in a single `set_new_navigation`; never set-to-charger-then-append, single-leg-only, or set-then-delete-then-reset.
- **Match the route resolution to the cue; ask only for a genuine open choice.** Their pick or standing preference when given; fastest when deferred; an open "which route?" only when truly unspecified.
- **Resolve, don't substitute.** An unresolvable named place is a clarify, never a silent swap.
- **Do the full lookup before the limitation**, and **never claim navigation started** when the start capability is incomplete. Surface the route id(s), not a flat "no".

## Common mistakes to avoid
- **Using a replace/add tool, or calling `set_new_navigation` while a route is active**, to start — the former is the wrong tool, the latter errors.
- **Splitting a multi-leg trip** — set-to-charger-then-append, single-leg-only, or set-then-delete-then-reset — instead of one `set_new_navigation` with all legs in order.
- **Assuming a route** instead of presenting options when the user will choose, or **asking which route when the user deferred or named their usual** instead of resolving it.
- **Picking a route that ignores the user's stated preference**, or asking when context already pins it.
- **Silently substituting an unresolvable place** instead of asking the user.
- **Re-teaching the charger pick, charge math, or reserve call** here instead of pointing at `poi-search` / `ev-range-feasibility` / `place-phone-call`; or placing a reserve call before navigation is set.
- **Fabricating route options / a route id**, or **claiming navigation started/active** when the start tool can't actually activate it.
- **Stopping after listing routes** without the honest "I can't start it" admission, or **not supplying the route id(s)** the start would need.
- **Looping** on the same refusal instead of resolving and stopping.

## Procedure
1. `get_current_navigation_state(detailed_information=true)` to confirm nothing is active; if a route is running, hand off to `navigation-change-destination`; if the tool is missing, admit you can't verify and pivot to the lookups you can do.
2. `get_location_id_by_location_name(<destination(s)>)`; if a place doesn't resolve, ask the user and resolve the correction.
3. `get_routes_from_start_to_destination(current start → destination)` — and, for a charging trip, also `(charger → final destination)`. (Find the charger via `poi-search`; do the charge-time/SoC math via `ev-range-feasibility`.)
4. Resolve each leg's route by the cue (their pick / `get_user_preferences` for a usual route / fastest when deferred); present options when they will choose.
5. If `set_new_navigation` can activate: call it **once** with `route_ids=[<chosen route id>]` for a single trip, or `route_ids=[<charger-leg id>, <onward-leg id>]` in order for a multi-leg trip, and confirm. If its required route input is removed (or the tool is gone): present the exact route id(s) and details, admit nav can't be started, and don't claim it started.
6. If a reserve call is required, place it via `place-phone-call` LAST, after navigation is set. Then stop.
