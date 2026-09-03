---
name: navigation-conditional-by-weather
description: Resolve a navigation choice gated on a weather condition ("go to A unless it's raining there, else B") by reading the weather once at the RELEVANT place and time, evaluating the rule literally, taking the branch it actually selects (both then and else are real outcomes), and routing on the axis the user named; only run the selected branch's actions; and when the weather tool is missing so the condition can't be evaluated, admit it and hand the branch choice back to the user — never guess the weather, take a branch on assumption, or fabricate a reading.
tools:
  - get_location_id_by_location_name
  - get_weather
  - get_routes_from_start_to_destination
  - set_new_navigation
  - navigation_replace_final_destination
  - search_poi_at_location
---

# Conditional navigation by weather

The user makes the destination (and/or which route, or whether to stop somewhere) depend on a **weather condition** — for example, "go to A unless it's raining there, otherwise go to B." Getting this right hinges on evaluating the condition at the correct place and time, then taking the branch it dictates and routing per the user's preference. Both branches are real outcomes; querying the wrong time slot or assuming the local outcome flips the branch and sends you to the wrong place. Sometimes the weather tool is **missing**, so the condition cannot be evaluated at all.

## When this applies
"Navigate to <A> if it does/doesn't <weather condition> there, otherwise <B>", "charge in <A> unless it's raining, then drive to <B>", "take me to <A> unless it's raining on arrival, then <B>" — any request where a weather condition selects the destination, the route, or whether to make a stop.

## Tools
- `get_location_id_by_location_name({location})` — resolve the place the condition is about and the branch destinations.
- `get_weather({location_or_poi_id, time_hour_24hformat, month, day, ...})` — read the weather for the **relevant place and time**; set the hour to match the moment the condition is about (arrival hour for an arrival-based rule). This single reading decides the branch. In some cases this is the **MISSING tool** — nothing else can determine the weather.
- `get_routes_from_start_to_destination({start_id, destination_id})` — fetch routes to the destination the selected branch produces.
- `set_new_navigation({route_ids})` — activate navigation on the chosen branch's route.
- `navigation_replace_final_destination(...)` / `search_poi_at_location(...)` — act on or find a POI inside the selected branch, once it is chosen.

## Method
1. **Resolve the candidate destinations** (and the place the condition is about) to ids.
2. **Read the weather once** for that place at the **relevant time** with `get_weather`. If the decision is about conditions on arrival, query the **arrival time**, not the current time — the arrival hour can differ from now and the condition may resolve differently at each.
3. **Evaluate the condition literally and take the branch it selects.** If the "unless" clause holds (e.g. it *is* raining), the **else/fallback** branch fires — go to the other place; do NOT act locally. If it is not met, the local branch fires. Neither branch is the default; the reading decides.
4. **Run only the selected branch's actions.** If the fallback fires, the local branch's work (e.g. searching a charging station at the local place) must NOT be performed.
5. **Fetch routes to the selected destination** and pick the route on the **axis the user named** (e.g. shortest vs fastest). Use exactly the preference stated; default only when the user defers.
6. **Activate once** with `set_new_navigation` (or `navigation_replace_final_destination` when editing an active endpoint) on the chosen route. Confirm the destination and route, and stop.

### Ask vs. infer
The branch is decided by the weather reading, not by asking — read the condition input and follow it; do not bounce the branch choice back when you can evaluate it. The route axis comes from what the user named; default only when they defer. Genuinely open user choices within the selected branch (e.g. picking among POIs) are surfaced for the user.

### When the weather tool is missing
- **The condition is genuinely unverifiable.** When `get_weather` is removed, no other tool can substitute — POI/route tools describe places, not conditions.
- **Admit the gap first, then hand the decision back.** In your first reply, say plainly you have no weather-check tool and therefore can't verify the condition; present the explicit either/or (branch A vs branch B) and ask the user to pick.
- **No premature action.** Make no tool calls to prepare a branch you have no basis to choose: don't resolve locations, fetch routes, or search POIs on assumption, and don't begin executing either branch as if its condition held.
- **Resolve, then stop.** Once the user picks a branch, execute it normally. Don't loop the refusal.

## Principles
- **Right place, right time — then branch.** Evaluate the condition at the time the user's rule refers to (arrival hour for an arrival-based rule), and follow the fallback wherever it leads.
- **Apply the rule literally.** Map the actual reading to the user's if/else exactly; don't shortcut to "probably fine" and act locally.
- **Run only the branch that fired.** Skip the non-selected branch's search/stop entirely.
- **Honour the route axis stated** (shortest vs fastest); convenient default only on deferral.
- **Don't guess the condition.** When you can't read the weather, never assert or assume it to justify a branch — put the choice to the user.
- **Activate after the branch resolves**, once; don't pre-commit and correct.

## Common mistakes to avoid
- **Checking weather at the current time** when the decision is about arrival — the current and arrival conditions can disagree and send you to the wrong destination.
- **Taking the wrong branch** because the weather was read at the wrong slot, or acting locally when the condition required the fallback.
- **Searching/stopping for the local branch** when that branch did not fire.
- **Ignoring the stated route axis** (choosing fastest when shortest was asked).
- **Activating before the branch is correctly resolved**, then having to correct it.
- **Re-reading the weather in a loop** instead of evaluating the single reading and acting.
- **Inventing the weather** ("it's not raining, so I'll route you to A") when no weather tool exists, or **calling POI/route tools to prepare a branch on assumption**, or **pretending you checked**.
- **Looping** the same "I can't check weather" line instead of offering the choice and stopping.

## Procedure
1. If the request is weather-gated and `get_weather` is unavailable: make no tool calls; reply that you have no weather tool so the condition can't be verified; offer the explicit branch choice (A vs B) and ask the user to pick; on their pick, execute that branch normally.
2. Otherwise: `get_location_id_by_location_name` for the condition's place and the branch destinations.
3. `get_weather(<that place>, <relevant time — arrival hour for an arrival rule>)` — once.
4. Evaluate the condition: "unless" clause holds → fallback branch; otherwise → local branch. (No local-branch search/stop when the fallback fires.)
5. `get_routes_from_start_to_destination(start → selected destination)`; pick the route on the **named axis**.
6. `set_new_navigation(route_ids=[<chosen route>])` (or replace the endpoint if active).
7. Confirm and stop.
