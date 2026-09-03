---
name: exterior-lights-control
description: Turn exterior lights (low beams, high beams, fog lights) on or off. Map the request to exactly the named light(s); read current status (and weather) when the outcome depends on it; honour preconditions/conflicts between lights; confirm gated changes once then act; resolve an unstated "which light?" from current state rather than an open menu; and when a control is missing or a status reads "unknown", do every doable part and honestly admit the rest.
tools:
  - get_exterior_lights_status
  - get_weather
  - set_head_lights_low_beams
  - set_head_lights_high_beams
  - set_fog_lights
---

# Exterior lights control

Turn a named exterior light on or off. Requests range from a single unambiguous toggle to multi-light operations that need a weather check, a confirmation, a precondition light, or the resolution of a conflict between lights. Sometimes the user does not say **which** light; sometimes a needed control is **missing**. The same method handles all of these.

## When this applies
The user asks to turn low beams, high beams, or fog lights on or off — e.g. "turn off the low beams", "switch the high beams on", "put the fog lights on" — or more loosely "turn the lights on/off" / "turn on the headlights" without naming the specific light.

## Tools
- `get_exterior_lights_status()` — read which exterior lights are currently on/off. This is what disambiguates a vague request and what verifies a precondition. A field for a given light may come back `"unknown"` — genuinely unverifiable, not a value you can read.
- `get_weather(...)` — read the weather for the relevant location/time when visibility or conditions affect whether/how to proceed or whether a confirmation is warranted.
- `set_head_lights_low_beams({on})`, `set_head_lights_high_beams({on})`, `set_fog_lights({on})` — the actuators, one boolean each. Any one of these may be **removed** from the toolset; a removed actuator cannot be called and you must not pretend to.

## Method
1. **Act on exactly the light(s) named.** Map the user's words to the specific tool. If they said "low beams", touch only low beams — not high beams, not "all lights".
2. **If the light is unstated, infer it from current state — don't ask an open menu.** Read `get_exterior_lights_status` first:
   - For a *turn-off* request, the light(s) currently on are the only thing the user can mean — act on those.
   - For a *turn-on* request, what's already on tells you the sensible next light (if the basic beams are on, the meaningful upgrade is the stronger/auxiliary light, not re-toggling what's on).
   - Let conditions narrow it further: a light inappropriate for the weather is ruled out.
Propose the single context-correct light in one yes/no question rather than enumerating every light. (When the user *did* name the light, no inference is needed — just act.)
3. **Read state/weather when the outcome depends on it.** A conflict, a precondition, or a visibility-driven decision all require reading first. Read each deciding value **once**.
4. **Apply preconditions.** Some lights require another first (e.g. fog lights need low beams on). If the precondition light is off, turn it on as part of fulfilling the request — the user implicitly accepts the prerequisite; don't ask about it separately.
5. **Confirmation-gated actions: ask once, then act.** Some toggles require explicit confirmation (e.g. turning high beams on, or a weather-flagged change). Ask once, wait for the user's "yes", then execute. Do **not** execute before the "yes", and do **not** re-ask after it. Weather sets the confirmation *level*, not a refusal — mild conditions warrant one confirmation, not skipping it and not declining.
6. **Resolve conflicts as one confirmed batch.** If fulfilling the request requires also changing a conflicting light (e.g. fog lights on while high beams are on, where the high beams must go off), name **every** change in your confirmation prompt, and on the single "yes" fire **all** the changes together in one turn.
7. **When a capability is missing, do the doable and admit the rest — honestly.**
   - **A whole actuator is missing:** state plainly you can't change that light from here, and name the light controls you DO have. Don't stall with a confirmation prompt as if you could then do it, and don't substitute a light the user didn't ask for.
   - **A blocking light's actuator is missing:** if the target light is gated on another light whose control is gone, you can't clear the blocker, so you can't complete the request. Admit it — never promise "I'll switch the blocking light off" when you have no such control.
   - **A status field reads `"unknown"`:** treat it as unverifiable (not off/on), surface it, and don't claim you set or read that light or proceed on a policy that depends on it. Re-reading won't resolve it.
Do the doable parts in the same answer; refuse only the impossible part.
8. Confirm briefly what you did (and what you couldn't, with the alternative) and stop.

## Principles
- **One light named → one call.** A specific, unambiguous request is a single actuator call with the correct boolean. No reads, no extra lights.
- **Read state before deciding, when state decides.** For a vague request, relative/conflict logic, or a precondition, `get_exterior_lights_status` (and `get_weather` if visibility matters) is what makes the choice — but read each value only **once**, then act.
- **Infer the one sensible light; don't enumerate.** An open "low/high/fog?" menu when current state already pins the answer is the failure. A single proposal the user confirms is fine.
- **Gate then act, exactly once.** When confirmation is required, the action happens only after the "yes" — and only once. Re-asking after a "yes" means it never gets done.
- **Keep paired/conflicting changes on the same confirmation.** Both must land after the final "yes", and that final prompt must name both. Their order relative to each other doesn't matter.
- **Never call a removed actuator and never claim a light changed when it didn't.** If the control isn't there, say so; don't fabricate the result. `"unknown"` means unverifiable.
- **Honest "can't" + a real alternative beats a flat refusal**, and beats a false promise made during confirmation. Name the controls you do have.
- **Answer once, then stop** — don't loop a confirmation, a refusal, or a re-read of an `"unknown"` field.

## Common mistakes to avoid
- **Touching the wrong or a broader light** (e.g. "all lights" when one beam was named).
- **Asking an open "which lights?" menu** instead of reading status and proposing the one sensible light — and worse, doing *zero* tool calls while asking.
- **Skipping the status/weather read** when the decision depends on it, so you guess.
- **Re-toggling what's already on**, or choosing a light the conditions rule out.
- **Executing a confirmation-gated change immediately**, with no "ask first".
- **Splitting a paired change across confirmations**, or a final confirmation that doesn't name every change it will make.
- **Re-asking in a loop** after the user already confirmed, so nothing ever executes.
- **Skipping a required precondition** (e.g. fog lights without enabling low beams first).
- **Hallucinating success** — claiming a light is on/off when its actuator was removed — or **calling a removed/erroring tool** "to try it anyway".
- **Treating `"unknown"` as a known value** (assuming off), or **promising the missing capability during confirmation** before admitting you can't.
- **Dropping the doable parts** — refusing the whole request when part of it was achievable.

## Procedure
1. Identify the light(s) involved and the target on/off state. If the light is unstated, plan to read status and infer it; map each light to its actuator.
2. If the outcome depends on current state or weather (vague request, conflict, precondition, visibility), read `get_exterior_lights_status` and `get_weather(<relevant place/time>)`.
3. Determine any preconditions or conflicts, and (for a vague request) the single sensible light. Spot any gap: a removed actuator, a missing blocking-light control, or an `"unknown"` field a policy needs.
4. If the action is confirmation-gated, ask once — naming **all** changes you will make, and without promising a capability you may lack — and wait for "yes".
5. On confirmation (or immediately, if no confirmation is required), issue the actuator call(s) you genuinely can; fire paired changes together in one turn; include any required precondition light.
6. Confirm what you did, state plainly anything you couldn't do and why (offering the controls you do have), then stop — no loops, no fabricated values, no removed-tool calls.
