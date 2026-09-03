---
name: navigation-status
description: Report the current navigation status and route details from ONE read of the navigation state — set detailed_information=true on the first call when details are wanted so a single result answers both "is it running?" and the details follow-up, and never re-call to fetch what the first read already returned; and when the state-read tool is missing, admit you can't read the active route, pivot to what you can do, and fabricate no waypoints, distances, durations, or running/not-running claims.
tools:
  - get_current_navigation_state
---

# Report navigation status

A read-only request: tell the user whether navigation is running and, when asked, the route details (waypoints, distances, durations, ETA). This is answered from a **single** read of the navigation state — set the detailed flag appropriately on that one call and reuse the result. The twist: the state-read tool may be absent, so the active route cannot be read at all.

## When this applies
"Is navigation running?", "what's my current route?", "how far / how long to go?", "where's my next stop?" — a read-only status and details request. (To *start* a route, *change* the destination, or *edit* a stop, see the other navigation skills.)

## Tools
- `get_current_navigation_state({detailed_information})` — read whether navigation is active and, with the detailed flag on, the full route details (waypoints, distances, durations). **May be the missing tool** — then you cannot read or verify the active route.

## Method
1. **Call `get_current_navigation_state` once, with the detailed flag set appropriately.** If the user has already said they want details (or asked a details question), set `detailed_information:true` on the **first** call so a single read covers both "is it running?" and the details.
2. **Answer both questions from that one result** — active/inactive status and any route details — without redundantly re-calling.
3. Report concisely, then stop.

### Ask vs. infer
- **A status request is rarely ambiguous — read and answer.** Don't ask the user to narrow it; the one detailed read gives you everything to answer status and details.
- **Set the detailed flag from the request.** If details are clearly wanted, read with `detailed_information:true` once; don't read with it off and then make a second redundant call to get the details.

### When a capability is missing
- **Missing state tool.** When `get_current_navigation_state` is absent, you cannot read or verify the active route. Don't fabricate waypoints, distances, durations, or an ETA, and don't claim nav is or isn't running. Admit plainly you can't read the active navigation state, then pivot to what you CAN do (e.g. look up routes to a destination the user names). Re-reading won't resolve it.
- **Unverifiable values.** Never assert a status or value you couldn't read; treat any unreadable field as genuinely unknown.

## Principles
- **One detailed read answers status + details.** When details are wanted, read once with the detailed flag on and reuse the result; don't re-call for what the first read already returned.
- **Read, don't ask.** A status question is answered from the state, not by interrogating the user.
- **Admit the unreadable state; never fabricate it.** No invented waypoints, distances, durations, ETAs, or running/not-running claims when the tool is gone.
- **Do the doable, name the missing — concisely.** When the read works, answer; when it doesn't, say so and offer a forward option, then stop.

## Common mistakes to avoid
- **Reading with the detailed flag off** when the user wants details, then making a second redundant read.
- **Re-calling the state read** to fetch detail the first result already carried.
- **Fabricating the active route** or asserting nav is/isn't running when the state tool is gone.
- **Asking the user to clarify** a plain status question instead of reading the state.
- **Looping** on the same read or refusal instead of giving the answer (or the honest "can't read it") and stopping.

## Procedure
1. Call `get_current_navigation_state(detailed_information=true)` once when details are wanted (or with the flag off only for a bare "is it on?" with no details asked).
2. Report active/inactive status and the route details from that single result.
3. If the tool is missing, admit you can't read the active route, offer to look up routes to a destination the user names, fabricate nothing, and stop.
