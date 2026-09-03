---
name: contacts-lookup
description: Look up contacts by name and fetch their details — resolving the right person when a name matches several people (infer silently when a fuller name, a single match, or a named recipient pins them; ask only when the choice is genuinely open among real candidates) and separating "who's in the body" from "who's the recipient" when relevant. When the detailed-contact tool is removed, surface only the matching names and ids, say plainly you can't retrieve phone or email, and never fabricate those fields. Lookup only — sending an email is the `send-email` skill.
tools:
  - get_contact_id_by_contact_name
  - get_contact_information
---

# Look up contacts and fetch their details

The user wants a contact resolved and their details fetched — a phone number, an email, the info for several people. You find the contact id(s) by name, then fetch the detailed fields. A name may match several people, so the discipline is resolving the right person and reporting only what the tools return. This skill looks up contacts; sending an email is the `send-email` skill.

## When this applies
"Look up <name>", "what's <person>'s number/email?", "get me the contact info for everyone with last name <X>", "find the details for <people>." Often a precursor to an email (`send-email`) or a call (`place-phone-call`).

## Tools
- `get_contact_id_by_contact_name({contact_first_name | contact_last_name})` — find the contact id(s) matching a first or last name. A name may match several people. This typically remains available and returns names + ids.
- `get_contact_information({contact_ids})` — fetch detailed fields (phone, email, …) for the given ids. This tool may be **removed** — if so, only names + ids are obtainable, never phone/email.

## Method
1. **Look up by the name given.** Use `get_contact_id_by_contact_name` with the first or last name supplied; it may return several people.
2. **Resolve the right person.** Pin the individual the user means (see ask-vs-infer below). When the task involves a body-set and a recipient, treat them as two separate resolutions.
3. **Fetch the requested details.** `get_contact_information` for the resolved id(s); include exactly the people and fields asked for.
4. Report the details (or, if a capability is missing, exactly what you can) and stop.

### Ask vs. infer the person
- **Infer silently when context already pins the person.** A fuller name the user gave, the single matching contact, or a recipient already named in the request settles it — act, do not ask.
- **Ask only when the recipient/person is a genuine open choice.** When the request leaves the person truly unspecified among several real candidates and nothing in context selects one, ask which one and use the user's answer. Don't guess, and don't ask when the answer is already determinable.
- **Separate body from recipient.** "Get everyone with last name X to send to person Y" is two resolutions: the set whose info is wanted, and the single recipient — who may themselves be one of the matches; exclude them from their own list when relevant.

### When a capability is missing
- **No detailed-contact tool.** If `get_contact_information` is removed, surface exactly what `get_contact_id_by_contact_name` returns — the matching names and ids — and state plainly you can retrieve only names and ids, not phone numbers or emails. Never fabricate the missing fields. Say it once; don't loop.

## Principles
- **Infer when context decides; ask only for a genuine open choice.** Resolve a shared name or a determinable recipient silently; ask only when the person is truly unspecified and not fixed by context.
- **Separate body from recipient.** Looking up several people's info to send to one has two resolutions; the recipient may be one of those looked up.
- **Report only what the tools returned.** Names + ids if that's all that's readable; nothing fabricated.
- **One clear answer, then stop.** Don't re-ask or re-refuse identically turn after turn.

## Common mistakes to avoid
- **Asking which person** when a fuller name, a single match, or the request already pins them — or **guessing** the person when it is a genuine open choice that should be asked.
- **Conflating the body-set with the recipient**, or including the wrong people/fields.
- **Fabricating phone numbers or emails**, or **calling a removed detailed-contact tool** anyway.
- **Claiming to have details** you never retrieved, or a **vague limitation statement** that leaves the user unsure what's actually available.
- **Sending an email or placing a call here** — those are `send-email` and `place-phone-call`; this skill only looks up.

## Procedure
1. `get_contact_id_by_contact_name(<first or last name given>)` → matching id(s).
2. Resolve the right person: infer silently from a fuller name / single match / named recipient; ask only when the person is a genuine open choice among real candidates. Separate the body-set from the recipient when relevant.
3. If `get_contact_information` is available → fetch the requested details for the resolved id(s). If it's removed → report names + ids only, state phone/email can't be retrieved, and stop.
4. Report what you have; don't loop. To send the details by email, see `send-email`; to dial a looked-up number, see `place-phone-call`.
