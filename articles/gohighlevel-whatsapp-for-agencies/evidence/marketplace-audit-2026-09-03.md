# HighLevel Marketplace evidence

Captured: 2026-09-03 UTC
Source: https://marketplace.gohighlevel.com/integration/69f9c25eab147118be566acd

## Public listing facts

- App title: `WhatsApp Integration by TimelinesAI`.
- Marketplace subtitle: `WhatsApp Gohighlevel Integration`.
- Public count: 20 installs/users.
- Rating displayed in the card/header: 5.0 from 1 review.
- The detailed review section simultaneously says `Be the first to share your thoughts`; treat this as a marketplace rendering inconsistency.
- App scope: `Who is the app for? Sub-account`.
- Install permissions shown: `Agency` and `Sub-Account`.
- Distribution type: `Subaccount`.
- Connection method: OAuth 2.0. The listing says users do not need to copy API tokens.
- Custom workflow action: `Send WhatsApp via TimelinesAI`.
- The action lets users choose a sender number, message type, and merge fields.
- Inbound messages are logged to the matching HighLevel contact as timestamped notes with a link to the source conversation.
- Unknown inbound numbers create new contacts.
- Workflow-sent outbound messages are mirrored to contact notes.

## Marketplace statements that are not present

The public listing does not state that:

- one agency installation covers every sub-account;
- an agency can bulk-install across all locations;
- one TimelinesAI workspace can be shared across multiple HighLevel sub-accounts;
- connected WhatsApp numbers are isolated by sub-account;
- HighLevel contains a native TimelinesAI shared team inbox.

## Authentication check

The credential runbook linked from MRKT-4414 is readable. One bounded login attempt against the documented GHL sub-account returned HTTP 400 and the visible message `Invalid email or password`. No OTP prompt appeared. Temporary browser state was deleted after the check.

## Publication rule

The draft may cite the public listing facts above. It must keep the absent behavior conditional until a working demo account or product owner confirms it.
