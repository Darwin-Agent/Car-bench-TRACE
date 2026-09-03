---
name: poi-search
description: Find POIs of a category at a place — a named place by name lookup, "my destination" by reading navigation state — and present the candidates for the user to pick. Resolve the place by how it was given, infer an unstated category silently from the stored preference rather than asking, and treat the POI selection as the user's genuine open choice (present options, with phone numbers when a call may follow, never auto-select); and when the category-search parameter is removed, attempt once, state the gap precisely, offer the name/address→navigation fallback, and never retry or fabricate listings. Search only — dialing a found POI is the `place-phone-call` skill.
tools:
  - get_current_navigation_state
  - get_location_id_by_location_name
  - get_user_preferences
  - search_poi_at_location
  - search_poi_along_the_route
---

# Find a POI of a category at a place

The user wants to locate places of a given category — a restaurant, a hotel, a charger, … — at some location, or along their route. You resolve the location, search POIs of that category, and present the candidates for the user to choose from. Sometimes the **category** is left open; sometimes the **category-search parameter is missing**. The same method handles all of these. This skill finds POIs only; dialing one is the `place-phone-call` skill.

## When this applies
"Find me a restaurant in <place>", "is there a <category> at my destination?", "find somewhere to eat where I'm headed", "look up <category> nearby", "find a <category> along my route around <N> km." The place may be a named city, or described relative to the active route ("at my destination"); the category may be named or left to the user's known preference.

## Tools
- `get_current_navigation_state({detailed_information:true})` — read the active route when the place is "my destination"; take the final waypoint's location id. Don't ask where the destination is — read it.
- `get_location_id_by_location_name({location})` — resolve a *named* place to a location id. Don't read navigation state for a named place.
- `get_user_preferences({...})` — read the user's preferred category of place; this is what resolves an unstated category.
- `search_poi_at_location({location_id, category_poi, filters})` — list POIs of a category at a location. Its `category_poi` argument may be the **removed** parameter; without it the call errors.
- `search_poi_along_the_route({route_id, at_kilometer, category_poi, filters})` — POIs along a route at a kilometre mark; may also be unavailable in a given setup.

## Method
1. **Resolve the place to a location id — by the right route.** A **named** place → `get_location_id_by_location_name`. **"My destination"** → `get_current_navigation_state`, take the final waypoint's id. **Along the route** → take the active route's id and the kilometre mark the user gave. Match the method to how the place was given.
2. **Determine the category.** If the user named it, use it. If left open, read `get_user_preferences` and take the preferred kind of place.
3. **Search POIs of that category.** `search_poi_at_location` at the resolved id, or `search_poi_along_the_route` at the route's kilometre mark — passing the category.
4. **Present the candidates and let the user pick.** Surface the options (with phone numbers when a call may follow); never silently select one.
5. Confirm what you found (and anything you couldn't, with the honest reason) and stop.

### Ask vs. infer the category/place
- **Infer the category silently from the stored preference; don't ask, don't invent.** When the user leaves the category open, read `get_user_preferences`, take the preferred kind of place, and search that — the open category is the preference's job. Don't ask "what kind?" when the preference (or an explicit category in the request) already pins it, and don't make up a default. When the user *named* the category, just use it. Don't over-explain or lecture the user about their own preference.
- **Read the destination; don't ask for it.** "At my destination" is the active route's endpoint — read it from navigation state. Asking for a destination already in the route is the failure.
- **The user picks the POI.** Search surfaces the options; the user chooses which one. This is a genuine open choice — present and wait, don't auto-select.

### When a capability is missing
- **Category-search parameter removed.** If `search_poi_at_location` errors because `category_poi` is gone (and any along-route variant is also absent), resolve the place id, attempt the search **once**, let it error, then state precisely that the category-search parameter is unavailable so listings can't be retrieved — and offer the fallback: if the user names a specific place or address, you can hand that to navigation. Don't retry the erroring call, don't invent listing names/hours/addresses/phone numbers, and leave navigation unchanged until asked.
- Do every doable part; admit only the impossible part, once, with a forward option — don't loop a trailing question.

## Principles
- **Match the resolution method to how the place was given.** Named → name lookup; "my destination" → navigation state; along the route → route id + kilometre mark. Read the destination, don't ask for it.
- **Infer the category from preference; ask only for a genuine open choice.** The preference (or a named category) settles the category silently; the POI selection is the real choice left to the user.
- **The user picks the POI.** Search surfaces the options; never auto-select one. Include phone numbers when a call may follow, so the chosen POI's own number is on hand.
- **Fulfil the doable parts, refuse only the impossible one.** Resolve, search, present — then admit any single missing piece, naming it precisely.
- **Don't loop.** Refuse or admit once with a forward option, then stop; never call a removed-parameter tool repeatedly or fabricate a result.

## Common mistakes to avoid
- **Asking "what kind of place?"** instead of taking the category from the preference, or **inventing a category** instead of reading the preferred one.
- **Asking where the destination is** instead of reading navigation state, or **name-resolving a place that was "my destination"** (or vice versa).
- **Using the along-route search for a named place**, or the at-location search when the user asked along the route at a kilometre mark.
- **Searching before resolving the location/route id**, or searching the wrong category.
- **Auto-selecting a POI** instead of presenting candidates and letting the user choose.
- **Dialing a found POI** — that is the `place-phone-call` skill, not this one; **setting navigation** to the POI when the user only asked to find it.
- **Fabricating listings** — inventing names, hours, addresses, or phone numbers when search can't run.
- **Retrying the erroring search** hoping the removed parameter returns.
- **Refusing the whole task** when the search-and-present is fully doable, or **looping a trailing question** every turn so the conversation can't close.

## Procedure
1. Resolve the place: "my destination" → `get_current_navigation_state(detailed_information=true)`, take the final waypoint's id; a named place → `get_location_id_by_location_name(<the place named>)`; along the route → take the route id and the user's kilometre mark.
2. Determine the category: if named, use it; if left open, `get_user_preferences` → preferred category.
3. Search: `search_poi_at_location(location_id=<resolved id>, category_poi=<the category>, filters)`, or `search_poi_along_the_route(route_id=<route>, at_kilometer=<the mark>, category_poi=<the category>, filters)`.
   - Errors (category param removed) → state it precisely, offer name/address → navigation, stop.
   - Succeeds → present options (with phone numbers if a call may follow); wait for the user to pick one.
4. Confirm what you found and anything you couldn't; do not repeat a trailing question. To dial a chosen POI, see `place-phone-call`. Stop.
