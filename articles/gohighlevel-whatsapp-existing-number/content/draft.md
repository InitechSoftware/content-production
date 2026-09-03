---
title: "Use Your Existing WhatsApp Number with GoHighLevel: QR vs Coexistence"
slug: "gohighlevel-whatsapp-existing-number"
meta_title: "Use an Existing WhatsApp Number with GoHighLevel"
meta_description: "Keep your WhatsApp number when connecting GoHighLevel. Compare QR and WABA Coexistence, history limits, setup steps, and agency rollout checks."
primary_keyword: "GoHighLevel WhatsApp existing number"
status: "draft"
linear_issue: "MRKT-5192"
author: "Viktor, TimelinesAI SEO"
published_date: "2026-09-03"
---

# Use your existing WhatsApp number with GoHighLevel

Yes—you can use an existing WhatsApp number with GoHighLevel through TimelinesAI. First connect the number to a TimelinesAI workspace, then connect one selected GoHighLevel sub-account to that workspace. Choose QR/multidevice for a familiar linked-device setup, or eligible WABA Coexistence when you need Meta’s API and template-message model while keeping the WhatsApp Business App on your phone.

*By Viktor, TimelinesAI SEO · September 3, 2026*

The choice is not simply “old number or new number.” It is a choice between connection methods, operating rules, and rollout risks. This guide helps you decide without duplicating the full [GoHighLevel setup guide](https://timelines.ai/connect-whatsapp-to-gohighlevel) or [pricing breakdown](https://timelines.ai/gohighlevel-whatsapp-pricing).

## The short decision

Choose **QR/multidevice** when your team wants a connection that works like WhatsApp Web, needs group-chat sync in TimelinesAI, and can keep the phone online and properly linked. TimelinesAI’s official [connection guide](https://help.timelines.ai/en/articles/12383599-connect-whatsapp-to-timelinesai) describes generating a QR code in the workspace and scanning it from the WhatsApp account on the phone.

Choose **WABA Coexistence** when an eligible business number should remain active in the WhatsApp Business App while TimelinesAI also connects through Meta’s Cloud API. The official [Coexistence guide](https://help.timelines.ai/en/articles/14337362-whatsapp-coexistence-using-your-whatsapp-business-app-number-with-timelinesai-waba) documents its prerequisites, API messaging window, template requirements, app-feature restrictions, and linked-device effects.

In both cases, GoHighLevel connects to the TimelinesAI workspace. The current connector is not an agency-wide switch for every client location. Install and verify one target sub-account at a time.

## How the number reaches GoHighLevel

The phone number is connected to TimelinesAI first. GoHighLevel then connects one selected sub-account to that TimelinesAI workspace. This distinction explains what each system owns:

1. **WhatsApp owns the phone identity and messaging account.**
2. **TimelinesAI owns the connected workspace, shared inbox, and available sender accounts.**
3. **GoHighLevel owns the contact, workflow, and contact-note records created by the integration.**

Inside a GoHighLevel workflow, the TimelinesAI action can use a listed sender account. New inbound and workflow-sent 1:1 messages can be written as contact notes, while the full WhatsApp thread remains in TimelinesAI. See the [GoHighLevel WhatsApp integration overview](https://timelines.ai/gohighlevel-whatsapp-integration) for the exact CRM boundary.

Do not choose a connection method based only on the fact that both use the same number. Test sender visibility, contact matching, notes, replies, reconnect behavior, and user access in the target sub-account.

## Option 1: connect the existing number by QR code

TimelinesAI’s official [multidevice guide](https://help.timelines.ai/en/articles/12383602-using-whatsapp-multidevice) describes the familiar flow: create a workspace, generate a QR code on the WhatsApp tab, and scan it with the WhatsApp app on the phone.

This route is a practical fit when:

- the number already operates in regular WhatsApp or the WhatsApp Business App;
- the team wants TimelinesAI to work as a linked device;
- group-chat synchronization matters;
- the organization does not need to move this workflow into Meta’s WABA template model;
- someone owns phone access and reconnect procedures.

Treat the phone as operational infrastructure. Record who controls it, who can scan a replacement QR code, and how the team handles a disconnected account. Do not put the QR image, pairing code, or unmasked phone number in a public ticket or shared screenshot.

After the number is online in TimelinesAI, connect the intended GoHighLevel sub-account and run one inbound and one outbound test. Confirm that the workflow sender is the expected account—not merely a similarly named number.

## Option 2: use WABA Coexistence

WhatsApp Coexistence is for eligible WhatsApp Business App numbers. The official TimelinesAI guide says the same number can remain usable in the phone app while TimelinesAI connects through the WhatsApp Cloud API.

That continuity comes with specific conditions. At the time of the cited guide, Coexistence requires a supported WhatsApp Business App version, a configured Meta Business account, Meta eligibility, and a supported country. Meta—not TimelinesAI—determines some eligibility rules.

Coexistence also changes the operating model:

- the last platform to reply can determine whether the conversation is app-owned or API-owned;
- freeform API replies follow Meta’s 24-hour service window;
- an approved template is needed to restart API messaging outside that window;
- messages sent from the phone app can be echoed into TimelinesAI but do not open the API window;
- group chats are not synced through the Cloud API;
- linked companion devices are unlinked during onboarding and must be reconnected;
- some WhatsApp Business App features are disabled or restricted.

Read the current Coexistence article before onboarding because these rules can change. For campaigns or workflow recipes, use the separate [GoHighLevel WhatsApp automation guide](https://timelines.ai/gohighlevel-whatsapp-automation).

## QR vs Coexistence: which should you choose?

| Decision point | QR / multidevice | WABA Coexistence |
|---|---|---|
| Keep using the existing phone number | Yes, as a linked-device connection | Yes, for an eligible WhatsApp Business App number |
| Continue using the phone app | Yes | Yes, with documented feature restrictions |
| Group chats in TimelinesAI | Supported by the regular connection model | Not through the Cloud API; the guide recommends QR when group sync is needed |
| API templates and WABA rules | Not the purpose of this route | Yes; Meta template and 24-hour-window rules apply |
| Meta Business setup | Not part of the QR flow | Required |
| Reconnection owner needed | Yes | Yes; also plan for linked-device resets and eligibility |
| Best fit | Familiar team inbox and group-chat operations | Governed API messaging while retaining the Business App |

If your organization needs both Cloud API behavior and group sync, the official guide documents using WABA Coexistence and QR together. That design needs careful webhook and reconnect testing; do not treat dual connection as the default.

## Will my old WhatsApp history transfer to GoHighLevel?

Do not plan on a historical backfill. TimelinesAI’s public GoHighLevel pages describe **new** 1:1 WhatsApp activity being added to GoHighLevel contact notes. They do not promise that every old message on the phone will be copied into GoHighLevel after installation.

Separate three questions during migration:

- **Can the existing number connect?** Yes, through a supported TimelinesAI connection method.
- **Can the team still see its WhatsApp operation?** That depends on QR or Coexistence behavior and the TimelinesAI workspace.
- **Will old conversations become GHL contact notes?** Do not assume so; verify only new controlled messages after connection.

If historical context is important, keep the existing system available during validation and define where staff should read pre-connection conversations.

## Migration checklist for an existing number

### 1. Record the current setup

Capture the number owner, WhatsApp account type, phone custodian, linked devices, groups, broadcast use, automation, and any current CRM connection. Use masked numbers in non-operational documents.

### 2. Choose QR or Coexistence

Use the decision table above. Confirm Coexistence eligibility before designing around it. If group chats are essential, account for the Cloud API limitation.

### 3. Define the GoHighLevel boundary

Choose one pilot sub-account. Do not start from an agency shell and assume every location will inherit the connection. Agencies should use the controls in the [sub-account rollout guide](https://timelines.ai/gohighlevel-whatsapp-for-agencies).

### 4. Connect the number to TimelinesAI

Follow the official QR or WABA onboarding flow. Confirm the account is online before opening the GoHighLevel installation.

### 5. Connect the target GoHighLevel sub-account

Authorize the app for the intended client location. Stop if the wrong location appears or if the flow is ambiguous.

### 6. Test inbound matching

Send a message from a known internal test number. Confirm it reaches the expected WhatsApp account, matches the correct GoHighLevel contact, and creates the expected note.

### 7. Test an unknown sender

Use a controlled number that is not already in the CRM. Check phone normalization and the resulting contact before testing at scale.

### 8. Test one workflow message

Choose the intended sender in the TimelinesAI workflow action. Verify rendered text, recipient phone, delivery, and the corresponding contact note.

### 9. Exercise the reconnect plan

Confirm who can access the phone, TimelinesAI workspace, Meta Business settings if applicable, and GoHighLevel sub-account. A setup is not production-ready if only one unavailable person can restore it.

### 10. Roll out gradually

Start with internal recipients and a low-risk workflow. Add clients or senders only after the pilot passes. Compare commercial options in the [GoHighLevel WhatsApp pricing guide](https://timelines.ai/gohighlevel-whatsapp-pricing).

## What agencies should document per client

Agencies should keep a one-row register for each client sub-account:

- masked WhatsApp number;
- connection method: QR, Coexistence, or deliberately tested dual setup;
- TimelinesAI workspace;
- GoHighLevel sub-account;
- workflow sender label;
- phone and reconnect owner;
- Meta Business owner when WABA is used;
- last inbound/outbound test date;
- rollback and suppression owner.

This avoids a common failure: a workflow cloned into a new client location while still pointing to the original client’s sender or operating rules.

## FAQ

### Can I connect my current WhatsApp number to GoHighLevel?

Yes. Connect the number to TimelinesAI through a supported method, then connect the intended GoHighLevel sub-account to that workspace. Test the exact sender and location before production use.

### Do I need a new phone number?

Not necessarily. QR/multidevice can link an existing WhatsApp account, and eligible WABA Coexistence can keep an existing WhatsApp Business App number active on the phone. Each route has different prerequisites and limits.

### Can I keep using WhatsApp on my phone?

Yes for the cited QR and eligible Coexistence models, but the behavior is not identical. Coexistence restricts some Business App features and unlinks companion devices during onboarding.

### Will all previous chats appear in GoHighLevel?

Do not assume historical backfill. Public GHL documentation describes new activity as contact notes. Use controlled post-connection messages for acceptance testing.

### Can one agency installation cover every sub-account?

No in the current connector. Select, connect, and verify each target sub-account separately.

### Which option is best for groups?

The official Coexistence guide says group chats are not synced through the Cloud API and recommends the regular QR connection when group synchronization in TimelinesAI is required.

## Next step

Choose one internal test number and one GoHighLevel pilot sub-account. Complete the [setup guide](https://timelines.ai/connect-whatsapp-to-gohighlevel), test one inbound note and one workflow send, and record the result before moving another client or sender.
