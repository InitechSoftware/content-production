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

## Anonymous marketplace metadata

The listing's public `installationDetails` response reports:

- `userTypes: ["Location"]`;
- `isAgencyBulkInstallEnabled: true`;
- 20 total installations, all 20 recorded as location installations and zero as company installations.

The enabled bulk-install flag conflicts with the shipped connector. It is not evidence that multi-location agency deployment works.

## Implementation evidence

Application revision audited: `1594dcac5188ca0f25f6c417f7ae9d17c7a4e694` in `InitechSoftware/tl-gohighlevel-integration`.

- `src/integration.ts:15-33` defines Location-scoped OAuth and describes the Company-token recovery path.
- `src/integration.ts:90-130` lists company locations, auto-selects only when exactly one location exists, and throws when more than one sub-account exists.
- `test/oauth.test.ts:90-140` verifies the single-location fallback and the multi-location error.
- The repository's `CLAUDE.md` describes one TimelinesAI workspace connected to one GHL location.

Operational conclusion: the supported path is a separate, explicitly selected sub-account installation. The publisher should disable the marketplace bulk-install flag or engineering must implement and live-test true multi-location provisioning before it is advertised.

## Marketplace statements that are not present

The visible public listing does not state that:

- one agency installation covers every sub-account;
- the current connector can successfully bulk-install across all locations;
- one TimelinesAI workspace can be shared across multiple HighLevel sub-accounts;
- connected WhatsApp numbers are isolated by sub-account;
- HighLevel contains a native TimelinesAI shared team inbox.

## Authentication check

The credential runbook linked from MRKT-4414 is readable. One bounded login attempt against the documented GHL sub-account returned HTTP 400 and the visible message `Invalid email or password`. No OTP prompt appeared. Temporary browser state was deleted after the check.

## Publication rule

The draft may cite the public listing facts above. It must keep the absent behavior conditional until a working demo account or product owner confirms it.
