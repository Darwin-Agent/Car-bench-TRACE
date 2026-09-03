---
name: send-email
description: Compose an email, confirm with the user, and send it only on their explicit "yes" — never pre-send a draft. The recipient address comes from a resolved contact's own details (via `contacts-lookup`), never fabricated. The body may carry details the user gathered: contact info, an EV plan, or a weather update for a meeting (read with get_weather for the meeting's place/time, the location resolved via get_location_id_by_location_name). When the send tool is removed, draft it, admit you can't send, hand over the exact ready-to-send text, and never claim it was sent or queued.
tools:
  - send_email
  - get_weather
  - get_location_id_by_location_name
---

# Compose and send an email (only after confirmation)

The user wants an email sent — contact details to someone, an EV trip plan, a weather update for a meeting. You draft it, confirm, and send only on an explicit "yes". The recipient's address comes from a real resolved contact, never invented. The one variant that adds a tool here is a meeting-weather update, where the body needs a weather read. Resolving the recipient/contacts is the `contacts-lookup` skill; this skill composes and sends.

## When this applies
"Email <person> the details", "send <contact> the trip plan", "email someone from my <meeting> the forecast for where we're meeting." The deliverable is a sent email; the recipient and any looked-up content have already been (or are being) resolved by `contacts-lookup`.

## Tools
- `send_email({email_addresses, content_message})` — send the message. Recipient address(es) come from the resolved contact's own details. May be the **removed** tool.
- `get_weather({month, day, time_hour_24hformat, location_or_poi_id})` — read the weather for a meeting's place around the meeting time, when the body is a weather update.
- `get_location_id_by_location_name({location})` — resolve a meeting's location to an id so the weather query can run.

## Method
1. **Use the resolved recipient's real address.** The recipient address is the one from the contact resolved via `contacts-lookup` — never a fabricated or guessed address.
2. **Assemble the body from what the user gathered.** Include exactly the requested content: contact info, an EV plan, or — for a meeting-weather update — take the meeting's location and time from its source, resolve the location with `get_location_id_by_location_name` if the weather query needs it, then read `get_weather` for that place around the meeting hour and fold the reading into the body.
3. **Draft, then ask to confirm.** Show the draft and ask the user to confirm sending.
4. **Send only on the explicit "yes".** Call `send_email` only after the user confirms — never pre-send a draft.
5. Confirm what you did (or what you couldn't, with the honest reason) and stop.

### Ask vs. infer the content/recipient
- **Confirm before sending.** Sending is the one step that always requires explicit user confirmation; the draft is shown first and goes out only on "yes".
- **Read — don't ask — for a meeting's derivable pieces.** A meeting's location and time come from its entry, not from the user; resolve and read them.
- **Use what a read returns; don't loop it.** `get_weather` may answer with a nearby window rather than the exact meeting slot — take the closest available reading and proceed. Re-calling to chase an exact slot is the failure that ends in never sending.
- The recipient itself is resolved by `contacts-lookup`; don't re-resolve contacts here.

### When a capability is missing
- **No send tool.** If `send_email` is removed while the rest works, do all the doable work — compose the full body, fold in any weather/plan/contact content, and include the recipient's **actual** address — then state plainly you can't send emails with the tools available and hand the user the **exact ready-to-send message text** so they can send it themselves. Never claim the email was sent or queued, never fabricate the recipient's address, and don't loop the admission.

## Principles
- **Confirm before sending.** A message goes out only after the user's explicit "yes" — never pre-send a draft.
- **The recipient address is the resolved contact's own** — never fabricated.
- **Use a read's result; don't loop it.** One weather reading (nearest slot) is enough.
- **When the send is impossible, do the doable parts and hand over ready-to-send text** — never claim a send, and don't drop the composed content because the email can't go.
- **One clear answer, then stop.** Don't re-draft or re-refuse identically turn after turn.

## Common mistakes to avoid
- **Sending before the user's explicit confirmation**, or **pre-sending a draft**.
- **Fabricating the recipient's email** instead of using the resolved contact's own address.
- **Looping `get_weather`** chasing an exact slot, then abandoning the task without sending.
- **Re-resolving contacts here** instead of taking the recipient from `contacts-lookup`.
- **Claiming the email was sent or queued** when the send tool is gone; **not giving the user the ready-to-send text**; or **looping** the admission instead of delivering payload + text and stopping.

## Procedure
1. Take the recipient's real address from the contact resolved via `contacts-lookup`.
2. Assemble the body: include the requested content. For a meeting-weather update, resolve the meeting location (`get_location_id_by_location_name` if needed) and read `get_weather({time_hour_24hformat:<meeting hour>, location_or_poi_id:<meeting location>, month, day})` — take what it returns; don't loop.
3. Draft the email in the requested tone; ask the user to confirm sending.
4. On the explicit "yes", `send_email({email_addresses:<resolved recipient's own address>, content_message:<the draft>})`.
5. If `send_email` is removed → deliver the full payload, admit you can't send, hand over the exact ready-to-send text; never claim a send. Confirm and stop.
