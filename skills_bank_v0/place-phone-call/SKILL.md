---
name: place-phone-call
description: Dial a phone number with the call tool — the number coming from a real source the context provides (a chosen POI's own search result, or a found station's number for a reservation), never a fabricated or guessed number. In a trip flow a reservation call is placed LAST, after navigation is set (see `navigation-start`). When the call tool is removed, surface the exact number the user needs and admit plainly you can't place calls — never claim you dialed, "checked availability", or "made a reservation". Dial only — finding the POI is `poi-search`; resolving a contact is `contacts-lookup`.
tools:
  - call_phone_by_number
---

# Place a phone call

The user wants a number dialed — a restaurant or hotel found earlier, a charging station to reserve a plug, a contact. This skill does exactly one thing: pass a real phone number to the call tool. The number must already exist in the context — a found POI's own result, a station's reservation number, a resolved contact's detail — it is never invented. Finding the POI is `poi-search`; resolving a contact's number is `contacts-lookup`.

## When this applies
"Call it", "ring them", "phone the one I picked", "reserve the plug", "call the station." A number (or a source that yields one) is already in the conversation: the POI the user chose, the station selected for a reservation, or a contact's looked-up detail.

## Tools
- `call_phone_by_number({phone_number})` — dial. The argument must be the number from the specific source the context provides: the chosen POI's own search result, or the found station's number. This tool may be **removed**, in which case no call can be placed.

## Method
1. **Take the number from its real source.** Use the phone number that belongs to the specific POI the user picked, or the station being reserved — exactly that listing's number, not a different one, and never a guessed or made-up number.
2. **Honour ordering in a trip flow.** A reservation call inside a trip plan is placed **last** — only after navigation has been set (that set is the `navigation-start` skill's job; this skill places the call afterward). Don't dial before the route is committed.
3. **Dial.** `call_phone_by_number({phone_number:<the source's own number>})`.
4. Confirm what you did (or, if you couldn't, the honest reason) and stop.

### Ask vs. infer the number
- **Never guess or fabricate the number.** It must come from a real source the context already provides. If no such number exists in the conversation, you have nothing valid to dial — say so rather than invent one.
- **Don't substitute a different listing's number.** If the user chose a specific POI, dial *that* POI's number, not another candidate's.
- **Don't re-resolve here.** If the POI hasn't been found yet, that's `poi-search`; if a contact's number isn't yet known, that's `contacts-lookup`. This skill dials a number that already exists.

### When a capability is missing
- **Call tool removed.** If `call_phone_by_number` is gone, surface the exact number the user needs to dial themselves and admit plainly that you can't place calls with the tools available. Never claim you dialed, "checked availability", or "made a reservation" — none of those happened. Give the number once and stop; don't loop the admission.

## Principles
- **The number comes from a real source, never a guess.** A chosen POI's own result or a found station's number — never fabricated, never a different listing's.
- **Reserve last.** In a trip flow, place the reservation call after navigation is set (`navigation-start`), not before.
- **Surface the number when you can't dial.** If the call tool is gone, the user still needs the number — hand it over and admit the limit honestly.
- **One action, then stop.** Dial once, or admit once; don't loop.

## Common mistakes to avoid
- **Fabricating or guessing a number** instead of using the one the context provides.
- **Dialing the wrong listing's number** when the user chose a specific POI.
- **Placing a reservation call before navigation is set**, or out of order in the trip flow.
- **Re-searching or re-resolving** here instead of using the number already found (that's `poi-search` / `contacts-lookup`).
- **Claiming you called, "checked availability", or "made a reservation"** when the call tool is gone.
- **Dropping the number the user needs** to dial themselves, or **looping** the admission instead of giving the number once and stopping.

## Procedure
1. Take the number from its real source — the chosen POI's own search result, or the found station's reservation number. Never a guessed number.
2. In a trip flow, ensure navigation is already set (`navigation-start`) before placing a reservation call — reserve calls go **last**.
3. `call_phone_by_number({phone_number:<the source's own number>})`.
4. If the call tool is removed → surface the exact number, admit you can't place the call, and stop. Otherwise confirm the call and stop. Don't loop.
