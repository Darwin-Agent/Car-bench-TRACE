---
name: contacts-lookup
description: Look up contacts by name and fetch their details (phone, email) — resolving the right person when a name matches several people (infer silently when a fuller name, a single match, or a named recipient pins them; ask only when the choice is genuinely open among real candidates) and separating "who's in the body" from "who's the recipient" when relevant (and, when the lookup feeds an email, checking a learned preference for a standing recipient to offer). Skip the name search when you already hold the ids (e.g. calendar attendees). If the detail tool isn't callable or a field reads "unknown", surface what you do have, say plainly what's unavailable, and never fabricate phone or email. Lookup only — sending an email is the `send-email` skill.
tools:
  - get_contact_id_by_contact_name
  - get_contact_information
  - get_user_preferences
---

# Look up contacts and fetch their details

The user wants a contact resolved and their details fetched — a phone number, an email, the info for several people. You find the contact id(s) by name, then fetch the detailed fields. A name may match several people, so the discipline is resolving the right person and reporting only what the tools return. This skill looks up contacts; sending an email is the `send-email` skill.

## When this applies
"Look up <name>", "what's <person>'s number/email?", "get me the contact info for everyone with last name <X>", "find the details for <people>." Often a precursor to an email (`send-email`) or a call (`place-phone-call`). Resolving a meeting attendee's details counts too — but there the ids usually come from the calendar, not a name search (see Method step 1).

## Tools
- `get_contact_id_by_contact_name({contact_first_name | contact_last_name})` — find the contact id(s) matching a first or last name. Either field is optional, so you can search by first name alone, last name alone, or both. A name may match several people. Usually callable and returns names + ids, but verify it is in your tool set — if it is not, you cannot resolve anyone from a name at all (see below).
- `get_contact_information({contact_ids})` — fetch detailed fields (phone, email, …) for the given ids. This tool may not be callable for a given request — if so, only names + ids are obtainable, never phone/email. When it is callable, a returned field may still come back as the literal value `"unknown"`; treat that as genuinely unavailable (see below), never as a real value.
- `get_user_preferences({...email...})` — when the lookup is preparing an outgoing email, the user may have a learned preference to always copy a standing recipient (e.g. a secretary). Check the relevant preference category so you can offer that person; surface and confirm them rather than silently omitting or silently adding.
- Verify before relying on any of these: only call what is actually in your tool set for this request, and read each result honestly rather than assuming it returned what you expected.

## Method
1. **Get the contact id(s).** If you already hold the ids from another source — most commonly calendar attendee ids — skip the name search and go straight to step 3 with those ids. Otherwise use `get_contact_id_by_contact_name`, searching with **as much of the name as the user actually gave**: pass both `contact_first_name` and `contact_last_name` when the user named a specific person (e.g. "Grace Nelson", "Rachel Clark") so you pin them in one call, and search a single field only when that is all the user supplied (e.g. "everyone with last name Scott", or just "Grace"). The fuller the name searched, the fewer spurious candidates to disambiguate — but a name still matches several people sometimes, so read the result rather than assuming one. When the request names both a group to look up and a separate recipient, you can resolve both at once (e.g. one search by last name for the group, one by first name for the recipient) in parallel.
2. **Resolve the right person.** Pin the individual the user means (see ask-vs-infer below). When the task involves a body-set and a recipient, treat them as two separate resolutions.
3. **Fetch the requested details.** `get_contact_information` for the resolved id(s); include exactly the people and fields asked for.
4. Report the details (or, if a capability is missing, exactly what you can) and stop.

### Ask vs. infer the person
- **Infer silently when context already pins the person.** A fuller name the user gave, the single matching contact, or a recipient already named in the request settles it — act, do not ask.
- **Ask only when the recipient/person is a genuine open choice.** When the request leaves the person truly unspecified among several real candidates and nothing in context selects one, ask which one and use the user's answer. Don't guess, and don't ask when the answer is already determinable.
- **Once the person is settled, follow through — never refuse a capability you have.** After the user picks from the candidates (or the name resolved to one), you already hold that contact's id from the name search; go straight to `get_contact_information` with it. Don't answer the user's clarification with a refusal like "I can't access the contact details" when the detail tool is in your set and the call would succeed — that invents a limitation that isn't there. Only claim you can't fetch details when the detail tool is genuinely absent.
- **Disambiguate from the id search, not by bulk-fetching details.** The name search already returns the candidate names + ids — that is enough to ask "which one?". Don't call the detail tool for every candidate just to pose the question; fetch details only for the person(s) the user actually settles on. Bulk-fetching is wasted work and needlessly pulls private numbers/emails for people the user never wanted.
- **Separate body from recipient.** "Get everyone with last name X to send to person Y" is two resolutions: the set whose info is wanted, and the single recipient — who may themselves be one of the matches. Include exactly the people the user named: if the user just says "send all the X contacts to Y", keep Y in the list too; only drop the recipient's own entry when the user explicitly asks to leave it out. Don't auto-exclude or auto-include against what was said.
- **Check for a standing recipient preference when the lookup feeds an email.** When you're resolving a contact in order to send a message, a learned preference may name someone the user always wants copied (e.g. a secretary). That person belongs on the recipient list too — retrieve the email preference and offer to include them for confirmation, rather than resolving only the explicitly named contact and stopping. Don't add them silently and don't make the user think to ask; surface the option.

### When a capability is missing
- **No name-search tool.** If `get_contact_id_by_contact_name` is not callable for this request, you have no way to turn a name into a contact id — say plainly you can't look up contacts by name right now, and note the adjacent capability you DO keep: if the detail tool is present, offer to fetch details when the user supplies a contact id directly. Don't invent an id, don't guess which contact they mean, and don't claim the lookup partly worked. In particular, do not try to route around the gap by passing the person's name into `get_contact_information` as if it were an id — that tool needs a real contact id and a name will simply error.
- **No detailed-contact tool.** If the detailed-contact lookup is not callable for this request, surface exactly what the name search returns — the matching names and ids — and state plainly you can retrieve only names and ids, not phone numbers or emails. Never fabricate the missing fields. Say it once; don't loop.
- **A field comes back unavailable.** If a detail call succeeds but a field reads `"unknown"`, that value is genuinely not retrievable here — don't pass it off as a real number/address, don't invent a plausible one, and don't re-call hoping it resolves. Report the fields you do have and name the one you couldn't get, so the user knows what's missing.
- **The user insists a value the record doesn't contain.** If the user asserts a particular contact has, say, a "work email" or a second number and the lookup returns only one entry with one address, report honestly the single address on file and that you can't find a separate one — don't fabricate an alternative to match their expectation, and don't silently substitute. You may re-search by name to confirm there isn't a second matching contact, but a re-search returning the same single record settles it: state that plainly rather than looping. Let the user supply the value if they have it.
- **Can't do the requested function at all.** If the value the user needs can't be obtained any legitimate way with the tools present, fulfil whatever parts you can and tell the user plainly you can't complete the rest — in one answer, without guessing.

## Principles
- **Contact tools are reads; lookup results are not permission to communicate.** Use contact-id, contact-information, and relevant preference reads directly to answer who/phone/email questions or prepare a draft. Do not send email, place a call, silently add a standing CC, or act on a looked-up person from this skill alone; surface candidates and preference-driven additions for the user to choose or confirm, and report only fields the contact tools actually returned.
- **Infer when context decides; ask only for a genuine open choice.** Resolve a shared name or a determinable recipient silently; ask only when the person is truly unspecified and not fixed by context.
- **Separate body from recipient.** Looking up several people's info to send to one has two resolutions; the recipient may be one of those looked up.
- **Report only what the tools returned.** Names + ids if that's all that's readable; nothing fabricated.
- **One clear answer, then stop.** Don't re-ask or re-refuse identically turn after turn.

## Common mistakes to avoid
- **Searching with less of the name than the user gave** — passing only the first name when they said "Grace Nelson" needlessly surfaces every Grace and forces an avoidable disambiguation; search both fields when the user named a specific person.
- **Asking which person** when a fuller name, a single match, or the request already pins them — or **guessing** the person when it is a genuine open choice that should be asked.
- **Conflating the body-set with the recipient**, or including the wrong people/fields — auto-dropping the recipient from a "send all of them" list they belong in, or auto-including someone the user said to leave out.
- **Ignoring a standing recipient preference** when the lookup is for an outgoing email — resolving only the explicitly named contact and never checking whether the user has a learned preference to copy someone (e.g. a secretary); retrieve the email preference and offer that person for confirmation.
- **Inventing an address or number the user insists on** because the stored record doesn't match their expectation (e.g. a "work email" that isn't in the contact); report the one value on file and that no other matches, and let them supply it.
- **Pretending to resolve a name when the name-search tool isn't callable** — inventing an id, guessing the person, or implying the lookup succeeded; say you can't search by name and offer to use a contact id if the user has one.
- **Refusing after disambiguation** — answering the user's "it's <person>" with "I can't access the contact details right now" when the detail tool is present and the id is already in hand; once the person is settled, just fetch their details.
- **Routing a name into the detail tool as a fake id** when name-search is unavailable — passing `"<First Last>"` as a `contact_id` will error; say you can't search by name instead.
- **Fabricating phone numbers or emails**, or **calling a detail tool that isn't in your tool set** anyway.
- **Treating an `"unknown"` field as a real value**, inventing a plausible substitute, or re-calling in a loop expecting it to resolve.
- **Re-searching by name when you already hold the ids** (calendar attendees) — just fetch their details directly.
- **Bulk-fetching details for every candidate to disambiguate** — when several people match and the user hasn't picked one, ask using the names the search already returned; don't pull phone/email for all of them first.
- **Claiming to have details** you never retrieved, or a **vague limitation statement** that leaves the user unsure what's actually available.
- **Sending an email or placing a call here** — those are `send-email` and `place-phone-call`; this skill only looks up.

## Procedure
1. Already have the ids (e.g. calendar attendees)? Go to step 3. Otherwise `get_contact_id_by_contact_name(...)` with as much of the name as the user gave (both first and last when they named a specific person; a single field when that's all they supplied) → matching id(s); resolve a group and a separate recipient with parallel searches when both are named.
2. Resolve the right person: infer silently from a fuller name / single match / named recipient; ask only when the person is a genuine open choice among real candidates. Separate the body-set from the recipient when relevant.
3. If the detail tool is callable → fetch the requested details for the resolved id(s); if any field reads `"unknown"`, report it as unavailable rather than fabricating. If the detail tool isn't callable → report names + ids only, state phone/email can't be retrieved, and stop.
4. Report what you have; don't loop. To send the details by email, see `send-email`; to dial a looked-up number, see `place-phone-call`.
