---
name: exterior-lights-control
description: Turn exterior lights (low beams, high beams, fog lights) on or off. Map the request to exactly the named light(s) and exact actuator. Read current status (and weather) when the outcome depends on it; honour preconditions/conflicts between lights; confirm gated changes once then act; resolve an unstated "which light?" from current state rather than an open menu; and when a control is missing or a status reads "unknown", do every doable part and honestly admit the rest.
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
- Exact actuator map:
  - Low beams / dipped headlights / normal headlights → `set_head_lights_low_beams({on})`.
  - High beams / bright headlights / full beams → `set_head_lights_high_beams({on})`.
  - Fog lights → `set_fog_lights({on})`.
- These actuators are **not interchangeable**. The `tools:` list above is the full skill capability map, but a particular task may expose only some of those tools; availability means the tool is actually callable in the current conversation. Any actuator may be **removed** from the runtime toolset; a removed actuator cannot be called and you must not pretend to. If the exact actuator for the user's named light is missing, that named-light change is impossible from here. Do not substitute another actuator, especially do not call `set_head_lights_low_beams` for a high-beam request.

## Method
1. **Act on exactly the light(s) named.** Map the user's words to the specific actuator before deciding what to do. If they said "low beams", touch only low beams — not high beams, not "all lights". If they said "high beams", the only main actuator that can satisfy the request is `set_head_lights_high_beams`; `set_head_lights_low_beams` is a different light, not a fallback, prerequisite, or approximation.
2. **If the light is unstated, infer it from current state — don't ask an open menu.** Read `get_exterior_lights_status` first:
   - For a *turn-off* request, the light(s) currently on are the only thing the user can mean — act on those.
   - For a *turn-on* request, what's already on tells you the sensible next light (if the basic beams are on, the meaningful upgrade is the stronger/auxiliary light, not re-toggling what's on).
   - Let conditions narrow it further: a light inappropriate for the weather is ruled out.
Propose the single context-correct light in one yes/no question rather than enumerating every light. (When the user *did* name the light, no inference is needed — just act.)
3. **Read state/weather when the outcome depends on it.** A conflict, a precondition, or a visibility-driven decision all require reading first. Read each deciding value **once**. Two turn-on cases *always* depend on a status read, so read `get_exterior_lights_status` before acting on them even when the user named the light explicitly, but only the exact actuator can perform the final change:
   - **Turning high beams on** — high beams and fog lights are mutually exclusive (high beams can't be on while fog lights are on), so you must read status to confirm fog lights are off (or honestly note you couldn't) before switching high beams on. Skipping this read and firing the high-beam call directly is a failure even when the user clearly asked for high beams.
   - **Turning fog lights on** — you need status to apply the low-beam precondition and to detect a high-beam conflict (see steps 4 and 6), plus a weather read (step 5).
4. **Apply preconditions.** Some lights require another first (e.g. fog lights need low beams on). If the precondition light is off, turn it on as part of fulfilling the request — the user implicitly accepts the prerequisite; don't ask about it separately.
5. **Confirmation-gated actions: ask once, then actually fire the exact call.** Two things gate a change behind explicit confirmation: (a) **turning high beams on always requires confirmation** (its actuator is confirmation-gated regardless of state or weather); and (b) **turning fog lights on requires a weather confirmation in nearly every condition** — the only conditions exempt from confirmation are the severe ones (cloudy with thunderstorm or cloudy with hail). This rule is inverted from intuition: ordinary weather like sunny, cloudy, partly-cloudy, rainy, or foggy is **not** exempt, so plain "cloudy" still demands a confirmation. Do not read "cloudy" (or any mild condition) as "allowed, proceed" — that misreading and firing the fog-light call straight away is a real and common failure. Ask once only after the exact main actuator(s) are available, wait for the user's "yes", then execute. Do **not** execute before the "yes", and do **not** re-ask after it. Weather sets whether the confirmation is needed, never a refusal — so when it applies you confirm once, you don't skip it and you don't decline.
   - **The "yes" turn is the execution turn.** Once the user confirms, your very next action is to issue the actuator call(s) — not a bare acknowledgement and not a status claim. Carry the pending action across the confirmation boundary: you decided *which* light(s) and *which actuator(s)* before asking, so on "yes" you fire exactly those calls. Replying to the confirmation with text alone (or an empty turn) and then asserting the light is on is a real failure — the change never happened. **Never claim a light is on or off unless its setter tool was actually called and returned `"status": "SUCCESS"` in this conversation.** If you find yourself about to say "fog lights are on" but no `set_fog_lights` result is in the transcript, stop and make the call instead.
6. **Resolve conflicts as one confirmed batch.** If fulfilling the request requires also changing a conflicting light (e.g. fog lights on while high beams are on, where the high beams must go off), name **every** change in your confirmation prompt, and on the single "yes" fire **all** the changes together in one turn.
7. **When a capability is missing, do the doable and admit the rest — honestly.**
   - **A whole actuator is missing:** state plainly you can't change that light from here, and name the light controls you DO have. Don't stall with a confirmation prompt as if you could then do it, and don't substitute a light the user didn't ask for.
   - **A required side-effect's actuator is missing:** turning one light on may require automatically changing another (e.g. enabling fog lights requires the high beams to be off). If you *can* still perform the main action but the control for the required side-effect is gone, do the main action and the parts you can, then clearly tell the user the specific side-effect you could not perform and offer the manual workaround (e.g. "fog lights are on, but I couldn't switch the high beams off from here — please turn them off manually"). Never silently skip the side-effect, and never promise "I'll switch the blocking light off" when you have no such control. If the main action itself is hard-blocked by a light whose control is gone, say you can't complete it and name the controls you do have.
   - **A status field reads `"unknown"`:** treat it as unverifiable (never assume off/on) and **say so explicitly in your message** — naming which light's status you couldn't read. Silently applying a safe default without telling the user is what fails; the user must hear that you couldn't verify it. There are two distinct cases: (a) if a policy only requires that light to be in a specific state (e.g. high beams must be **off** while fog lights are on), you can still command it into that required state — doing so satisfies the policy whatever the true reading was — but explain you're forcing it off precisely because you can't confirm it; (b) if completing the request needs the actual value to decide (and forcing a state wouldn't satisfy the policy), you cannot complete that part — admit it rather than guessing. Either way, never claim you read the real value, and re-reading won't resolve it.
Do the doable parts in the same answer; refuse only the impossible part.
8. Confirm briefly what you did (and what you couldn't, with the alternative) and stop.

## Principles
- **Light and weather reads can run; each exterior-light actuator needs a pinned light and boolean.** Read current exterior-light status or weather when state/visibility decides the action or confirmation gate. Call the low-beam, high-beam, or fog-light setter only for the specific light and on/off state the user named, the state logic uniquely determines, or the user confirmed; do not switch extra lights, resolve conflicts silently, or claim success for a removed actuator.
- **One named light keeps one target actuator.** A specific, unambiguous request maps to a single actuator with the correct boolean; required reads or confirmation gates do not change that target actuator. No extra lights.
- **Read state before deciding, when state decides.** For a vague request, relative/conflict logic, or a precondition, `get_exterior_lights_status` (and `get_weather` if visibility matters) is what makes the choice — but read each value only **once**, then act.
- **Infer the one sensible light; don't enumerate.** An open "low/high/fog?" menu when current state already pins the answer is the failure. A single proposal the user confirms is fine.
- **Gate then act, exactly once — and the acting is a tool call.** When confirmation is required, the action happens only after the "yes", only once, and *as an actuator call in that same turn*. Re-asking after a "yes" — or answering it with words only — means it never gets done. A success message is earned by a returned setter, never asserted in its place.
- **Keep paired/conflicting changes on the same confirmation.** Both must land after the final "yes", and that final prompt must name both. Their order relative to each other doesn't matter.
- **Never call a removed actuator and never claim a light changed when it didn't.** If the control isn't there, say so; don't fabricate the result. `"unknown"` means unverifiable — and when you act on a light whose status you couldn't read, tell the user that's why, rather than letting a silent default stand in for a real reading.
- **Honest "can't" + a real alternative beats a flat refusal**, and beats a false promise made during confirmation. Name the controls you do have.
- **Answer once, then stop** — don't loop a confirmation, a refusal, or a re-read of an `"unknown"` field.

## Common mistakes to avoid
- **Touching the wrong or a broader light** (e.g. "all lights" when one beam was named).
- **Using low beams as a substitute for high beams** because the high-beam actuator is absent, because low beams are already on, or because the user confirmed with "yes" after a high-beam prompt. Low beams and high beams are distinct controls; this is always a wrong-tool failure.
- **Asking an open "which lights?" menu** instead of reading status and proposing the one sensible light — and worse, doing *zero* tool calls while asking.
- **Skipping the status/weather read** when the decision depends on it, so you guess.
- **Firing the high-beam-on (or fog-light-on) call without first reading `get_exterior_lights_status`** — these toggles depend on the high-beam/fog-light conflict and the low-beam precondition, so they always need the read even when the named light is explicit.
- **Re-toggling what's already on**, or choosing a light the conditions rule out.
- **Executing a confirmation-gated change immediately**, with no "ask first" — especially turning fog lights on after reading mild weather. Seeing "cloudy" (or sunny/partly-cloudy/rainy/foggy) and concluding fog lights are "allowed, proceed" skips the required confirmation; only thunderstorm or hail conditions are exempt, and every other condition still needs the single "yes" first.
- **Splitting a paired change across confirmations**, or a final confirmation that doesn't name every change it will make.
- **Re-asking in a loop** after the user already confirmed, so nothing ever executes.
- **Answering the "yes" with no tool call** — replying with text only (or an empty turn) after the user confirms, then claiming the light changed though the setter was never called. The confirmation turn must contain the actuator call; the change only counts once that call returns SUCCESS.
- **Skipping a required precondition** (e.g. fog lights without enabling low beams first).
- **Hallucinating success** — claiming a light is on/off when its actuator was removed — or **calling a removed/erroring tool** "to try it anyway".
- **Treating `"unknown"` as a known value** (assuming off), or **promising the missing capability during confirmation** before admitting you can't.
- **Asking for confirmation to turn on high beams when `set_head_lights_high_beams` is missing** — that prompt falsely promises a capability. Say you cannot control high beams instead.
- **Silently applying a safe default on an `"unknown"` status** — e.g. forcing high beams off in your confirmation prompt without telling the user *why* (that you couldn't verify them). When you command a light into the required state because you can't read it, say so out loud; an unexplained default is the failure even when the resulting action is correct.
- **Silently skipping a required side-effect whose control is missing** — e.g. turning fog lights on but never telling the user the high beams couldn't be switched off, or promising to switch them off and then not doing it. Do the main action, then state the un-performable side-effect and the manual workaround.
- **Dropping the doable parts** — refusing the whole request when part of it was achievable.

## Procedure
1. Identify the light(s) involved and the target on/off state. If the light is unstated, plan to read status and infer it; map each light to its exact actuator.
2. If the outcome depends on current state or weather (vague request, conflict, precondition, visibility), read `get_exterior_lights_status` and `get_weather(<relevant place/time>)`.
3. Determine any preconditions or conflicts, and (for a vague request) the single sensible light. Spot any gap: a removed actuator, a missing blocking-light control, or an `"unknown"` field a policy needs.
4. If the exact main actuator for a named requested light is missing, state that limitation now and do not ask for confirmation. Otherwise, if the action is confirmation-gated, ask once — naming **all** changes you will make, and without promising a capability you may lack — and wait for "yes".
5. On confirmation (or immediately, if no confirmation is required), issue the exact actuator call(s) you planned and genuinely can; fire paired changes together in one turn; include any required precondition light. Do not swap to a different light at execution time.
6. Confirm what you did, state plainly anything you couldn't do and why (offering the controls you do have), then stop — no loops, no fabricated values, no removed-tool calls.
