---
name: place-phone-call
description: Dial a phone number with the call tool — the number coming from a real source the context provides (a chosen POI's own search result, or a found station's number for a reservation), never a fabricated or guessed number. In a trip flow a reservation call is placed LAST, after navigation is set (see `navigation-start`). If you can't actually place a call with the tools you have, surface the exact number the user needs and admit plainly you can't dial — never claim you dialed, "checked availability", or "made a reservation". Dial only — finding the POI is `poi-search`; resolving a contact is `contacts-lookup`.
tools:
  - call_phone_by_number
---

# Place a phone call

The user wants a number dialed — a restaurant or hotel found earlier, a charging station to reserve a plug, a contact. This skill does exactly one thing: pass a real phone number to the call tool. The number must already exist in the context — a found POI's own result, a station's reservation number, a resolved contact's detail — it is never invented. Finding the POI is `poi-search`; resolving a contact's number is `contacts-lookup`.

## When this applies
"Call it", "ring them", "phone the one I picked", "reserve the plug", "call the station." A number (or a source that yields one) is already in the conversation: the POI the user chose, the station selected for a reservation, or a contact's looked-up detail.

## Tools
- `call_phone_by_number({phone_number})` — dial. The argument must be the number from the specific source the context provides: the chosen POI's own search result, or the found station's number. Before relying on it, confirm it is actually callable; if it isn't available to you, no call can be placed and you must handle that honestly (see below).

## Method
1. **Take the number from its real source.** Use the phone number that belongs to the specific POI the user picked, or the station being reserved — exactly that listing's number, not a different one, and never a guessed or made-up number.
2. **Place the call last.** Placing a call ends the conversation automatically, so dial only once every other intent in the turn is already done. In a trip flow this means navigation must be set first (that set is the `navigation-start` skill's job; this skill places the call afterward) and any conditional check the user attached to the call (e.g. "call only if the time is under N minutes") must already be evaluated and satisfied. Don't dial before the route is committed or before a stated condition is met.
3. **Dial with a clean, well-formed tool call.** `call_phone_by_number({phone_number:<the source's own number>})`. Emit the call as an actual tool call, not as narration text that merely describes calling. Do **not** pair the call with a spoken user message in the same turn: per policy, sending a message together with a tool call causes one of them to be dropped, and the call itself ends the conversation anyway, so a co-emitted "Calling them now" confirmation is both unnecessary and risks the call being lost. If you want a brief lead-in, keep it to its own prior turn; when it's time to dial, just issue the call.
4. **Read the result before confirming.** Only say the call was placed if the tool result actually reports it (e.g. the call-placed field is true). If that field comes back as `"unknown"` or the call doesn't return a clear success, treat it as unverified — say you've attempted it but can't confirm it connected, and surface the number; don't assert "done" or "reservation made" on faith. Then stop.

### Ask vs. infer the number
- **Never guess or fabricate the number.** It must come from a real source the context already provides. If no such number exists in the conversation, you have nothing valid to dial — say so rather than invent one.
- **Don't substitute a different listing's number.** If the user chose a specific POI, dial *that* POI's number, not another candidate's.
- **Don't re-resolve here.** If the POI hasn't been found yet, that's `poi-search`; if a contact's number isn't yet known, that's `contacts-lookup`. This skill dials a number that already exists.

### Dial only on an explicit call request
- **Finding or showing a number is not a request to dial.** "Find the number for X", "is there a phone number?", or "show me her details" asks you to surface the number — answer with it and stop. Wait for a distinct call-for-action ("call her", "ring them", "yes, call them now") before placing the call. Dialing proactively the moment a number appears is the failure here, and it's worse because the call ends the conversation.
- **A stated wish to call is still not the dial command.** "Is there a phone number? I want to call them to reserve a spot" or "I'd like to call them" explains *why* the user wants the number — it is not an imperative to dial now. Surface the number, optionally offer to place the call, and wait for the explicit go-ahead ("call that number", "yes, call them"). Treating the explanatory intent as the trigger and dialing immediately is a real, observed failure.
- **Then dial exactly what was asked.** Once the user does say to call, dial the number you just surfaced for that specific contact or POI — no re-confirmation loop, no re-resolving.

### When the call is gated on a condition
- **Evaluate the condition against the value you already established with the user.** When the user attaches a threshold to the call ("call only if the max time is between 30 and 50 minutes"), compare using the exact figure you reported to them earlier — don't silently re-derive a different interpretation of that figure right before deciding. A mismatch here flips the dial/don't-dial outcome.
- **Honor both outcomes.** If the condition is genuinely met, dial; if it genuinely fails, do not dial and say briefly why. Neither dialing-anyway nor skipping-a-met-condition is acceptable.

### When a capability is missing
- **No usable dialing capability.** If you cannot actually place a call with the tools available to you, surface the exact number the user needs to dial themselves and admit plainly that you can't place calls right now. Never claim you dialed, "checked availability", or "made a reservation" — none of those happened. Give the number once and stop; don't loop the admission.

## Principles
- **Dialing is the state change; the number must already be real and chosen.** This skill has no lookup tool of its own, so use only a phone number supplied by prior POI/station/contact context or by the user. Call `call_phone_by_number` only when the user asked to place that call and the exact number belongs to the chosen source; if the recipient or number is ambiguous, ask before dialing, and if dialing is unavailable, surface the number instead of pretending a call happened.
- **The number comes from a real source, never a guess.** A chosen POI's own result or a found station's number — never fabricated, never a different listing's.
- **Reserve last.** In a trip flow, place the reservation call after navigation is set (`navigation-start`), not before.
- **Surface the number when you can't dial.** If you have no usable dialing capability, the user still needs the number — hand it over and admit the limit honestly.
- **One action, then stop.** Dial once, or admit once; don't loop.
- **Issue the call as a real, well-formed tool call alone.** Don't describe dialing in prose instead of calling, and don't bundle a spoken confirmation into the dialing turn — a co-emitted message can cause the call to be dropped, and the call ends the conversation regardless.

## Common mistakes to avoid
- **Fabricating or guessing a number** instead of using the one the context provides.
- **Dialing the wrong listing's number** when the user chose a specific POI.
- **Dialing on a mere "find"/"show me the number" request, or on a stated wish like "I want to call them to reserve"** — surface the number, offer to dial, and wait for the explicit call-for-action; the call ends the conversation, so jumping the gun is costly.
- **Placing a reservation call before navigation is set**, or out of order in the trip flow.
- **Re-searching or re-resolving** here instead of using the number already found (that's `poi-search` / `contacts-lookup`).
- **Claiming you called, "checked availability", or "made a reservation"** when you have no usable dialing capability, or asserting success before reading the tool result — an `"unknown"` or unclear result is not a confirmed call.
- **Dialing too early** — before navigation is committed or before a user-stated condition for the call has been evaluated and met.
- **Misjudging a gating condition** — comparing against a freshly re-derived value instead of the figure you already told the user, then dialing when you shouldn't or skipping a call the condition actually allows.
- **Emitting a malformed call or narrating it as text** instead of a clean tool call, or **bundling a spoken confirmation into the dialing turn** — either can cause the call to be dropped and leave the request unfulfilled.
- **Dropping the number the user needs** to dial themselves, or **looping** the admission instead of giving the number once and stopping.

## Procedure
1. Take the number from its real source — the chosen POI's own search result, or the found station's reservation number. Never a guessed number.
2. Ensure everything else in the turn is done first — in a trip flow, navigation set (`navigation-start`), and any user-stated condition on the call evaluated and met. The call goes **last** because it ends the conversation.
3. `call_phone_by_number({phone_number:<the source's own number>})`.
4. Read the result: confirm the call only if it reports success; if the result is `"unknown"` or unclear, say it's unverified and give the number. If you can't actually place a call → surface the exact number, admit you can't dial, and stop. Don't loop.
