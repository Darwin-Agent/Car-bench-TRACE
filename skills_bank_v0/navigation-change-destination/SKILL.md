---
name: navigation-change-destination
description: Change the final destination of an active route to a new place — a named city, an indirectly described place, or a POI — resolving the destination and committing the chosen route exactly once; pick the route by the user's actual cue (fastest heuristic when they defer, their selection when they choose, the stored preference when they invoke their usual), never pre-committing a default; and when an edit tool is missing or a follow-on read is gone, do the doable, answer trivia from your own knowledge, and honestly admit what you cannot do rather than starting a route while one is active, fabricating routes, or claiming success.
tools:
  - get_current_navigation_state
  - get_location_id_by_location_name
  - get_user_preferences
  - search_poi_at_location
  - get_routes_from_start_to_destination
  - navigation_replace_final_destination
  - navigation_replace_one_waypoint
  - navigation_delete_waypoint
  - set_new_navigation
  - delete_current_navigation
  - get_charging_specs_and_status
---

# Change the final navigation destination

Navigation is active and the user wants a different endpoint. The new destination may be a city name, described indirectly (a landmark, "the capital of X"), or chosen from POIs in a place. You resolve the destination, fetch route options, commit the right route exactly once with `navigation_replace_final_destination`. Sometimes the route to use is under-specified; sometimes an edit or follow-on tool is missing. The same method handles all of these.

## When this applies
"Change my destination to …", "let's go to … instead", "navigate to …", "swap the end for <that restaurant>", often bundled with a follow-on ("…and do I have enough range?") — while a route is active. (To *start* navigation when none is active, or to *add/remove* a stop without changing the endpoint, see the other navigation skills.)

## Tools
- `get_current_navigation_state({detailed_information:true})` — read the current start so you can request routes from it. Usually still available even when edit tools are gone.
- `get_location_id_by_location_name({location})` — resolve a place name (including one you inferred from an indirect description) to a location id.
- `get_user_preferences()` — read the user's standing route preference when they invoke their usual route. This disambiguates that case — not a question.
- `search_poi_at_location({location_id, category_poi})` — when the destination is a POI, list candidates for the user to pick.
- `get_routes_from_start_to_destination({start_id, destination_id})` — fetch route options to the new endpoint. **Only when you can actually commit the change** — don't fetch and pretend.
- `navigation_replace_final_destination({new_destination_id, route_id_leading_to_new_destination})` — the correct tool when the endpoint changes (one new leg, one route id). **May be the missing one.** When present, use it.
- `set_new_navigation({route_ids})` — activate a fresh route; **errors while navigation is active**. Not a way to switch an active route. Often also removed.
- `navigation_replace_one_waypoint`, `navigation_delete_waypoint`, `delete_current_navigation` — may be stripped/erroring; not substitutes for a final-destination change.
- `get_charging_specs_and_status({})` — read battery/range; a common follow-on that may be missing even when the destination edit works.

## Method
1. **Read navigation state** to get the current start id for the routes query, and to confirm the active route.
2. **Answer embedded trivia from your own knowledge** (e.g. "the capital of X") — state it plainly; this needs no tool and isn't fabrication.
3. **Resolve the destination to an id.** Named city → `get_location_id_by_location_name`; indirect description → infer the place, then resolve that name; a POI → resolve the city, `search_poi_at_location`, present candidates, and act on the user's pick — don't pick for them.
4. **Fetch route options** from the start to the new destination (only when you can commit).
5. **Resolve the route by the cue, then commit once.** Use `navigation_replace_final_destination` a single time with the destination id and chosen route id.

### Ask vs. infer the route
The destination is rarely the hard part; the route among the options is what is often under-specified, and it resolves three different ways depending on what the user said. Read the cue — do not default to one, and do not ask when the cue already resolves it.
- **User defers ("just pick one", "whatever you think is best") → HEURISTIC.** Take the **fastest** route yourself; do NOT bounce the choice back as a question.
- **User invokes their usual route ("the one I usually take") → PREFERENCE.** Read `get_user_preferences`, match the standing preference to the offered options, and set that one silently — do NOT ask, do NOT pick one yourself.
- **User will choose (says "let me pick", or names roads / a specific option) → THEIR PICK.** Present the options and apply exactly the route they select. ASK here only because the choice is genuinely theirs; do NOT proactively pick one — some users end the interaction if you do.

### When a capability is missing
- **Missing edit tool.** When `navigation_replace_final_destination` (and the new-navigation / delete tools) are stripped, there is no way to switch an active route. Confirm the route via state, then honestly say you have no tool to replace the final destination. Do NOT call `set_new_navigation` (errors while active) or any replace/delete tool, do NOT fetch-and-pretend, and do NOT fabricate route options or claim the destination changed.
- **Missing follow-on read.** When the edit works but a downstream read (e.g. battery via `get_charging_specs_and_status`) is gone, do the edit, then admit you can't read that value and ask the user to supply it (e.g. read the dashboard). Never guess SOC, range, charging stops, or a phone number.
- **Unverifiable state.** Treat any unreadable field as genuinely unknown — never assume a value.

## Principles
- **`navigation_replace_final_destination` is the right tool when present — and the honest gap when absent.** Don't substitute a new-navigation or waypoint tool for it.
- **Match the route resolution to the cue.** Deferral → fastest heuristic; "my usual" → preference read; "I'll choose" → their pick. These are not interchangeable, and none is an open "which route?" when the cue already settles it.
- **Never proactively override a user or preference choice**, and never start a route while one is active (`set_new_navigation` errors — don't "try it").
- **Replace once, after the choice.** Don't pre-commit a default route and correct it later.
- **Trivia from knowledge is fine; routes/values from imagination are not.**
- **Do the doable, admit the missing — in one concise answer.** A working edit plus a missing follow-on → do the edit, name the missing read. Early clear honesty beats repeated hedging.

## Common mistakes to avoid
- **Asking which route when the user deferred** ("just pick one") instead of taking the fastest, or **asking/guessing when they invoked their usual route** instead of reading `get_user_preferences`.
- **Proactively choosing a route when the user said they'd pick** or named roads.
- **Pre-committing the fastest/default route then replacing again** once the real choice is known.
- **Using an add/replace-waypoint tool** when the final destination is what's changing.
- **Calling `set_new_navigation` while nav is active** (errors), or any removed/erroring replace/delete tool.
- **Fabricating route options** or claiming the destination changed when no tool did it.
- **Guessing a follow-on value** (battery %, range, charging stops, a phone number) when its read tool is missing, or **promising to "start navigation on the fastest route"** when the switch is impossible.
- **Navigating to a POI when the user meant the city** (or vice versa), or **assuming the POI** instead of letting the user pick.
- **Over-hedging / looping** instead of one concise honest answer plus a forward option.

## Procedure
1. `get_current_navigation_state(detailed_information=true)` for the start.
2. Answer any embedded trivia from your own knowledge.
3. Resolve the new destination to an id (name lookup; infer-then-resolve an indirect place; resolve city → `search_poi_at_location` → user picks a POI).
4. If the edit tool exists: `get_routes_from_start_to_destination(start → new destination)`, then resolve the route by the cue — deferred → fastest; usual route → `get_user_preferences`, match the preferred one; user chooses → present options, use their pick — and call `navigation_replace_final_destination` once. If the edit tool is absent: admit you can't replace the destination; call nothing that mutates or errors; invent nothing.
5. Do any feasible follow-on read; for a missing one, admit it and ask the user for the value.
6. Confirm the destination and route, keep it concise, and stop.
