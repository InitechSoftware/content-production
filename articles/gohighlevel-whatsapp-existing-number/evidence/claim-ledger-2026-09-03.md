# MRKT-5192 claim ledger — 2026-09-03

Implementation reference: `InitechSoftware/tl-gohighlevel-integration@1594dcac5188ca0f25f6c417f7ae9d17c7a4e694`

| Claim | State | Evidence |
|---|---|---|
| An existing WhatsApp account can connect to TimelinesAI through QR/multidevice | Available | Official `Connect WhatsApp to TimelinesAI` and `Using WhatsApp multidevice` help articles |
| An eligible WhatsApp Business App number can remain usable on the phone while connected through WABA | Conditional | Official Coexistence article; requires supported app version, Meta Business setup, eligibility, and supported country |
| The GHL connector operates against one selected location/sub-account | Available | GHL integration `src/integration.ts`; live GHL money page |
| GHL workflows can choose a TimelinesAI sender account | Available | Public Marketplace description and live GHL money/automation pages |
| New 1:1 messages can appear as GHL contact notes | Available | Live GHL money page and official GHL help article |
| Old WhatsApp history is backfilled into GHL | Unknown / not promised | Public GHL copy says “new 1:1 WhatsApp activity”; no public backfill promise found |
| The same connection method preserves every WhatsApp app feature | Not available | Coexistence article documents group, broadcast, disappearing-message, view-once, call, linked-device, and 24-hour-window limits |
| Agency-wide bulk install covers all sub-accounts | Not available in current connector | Repository at pinned SHA errors on multi-location Company scope and requires a selected Location |

## Public sources retrieved

1. https://help.timelines.ai/en/articles/12383599-connect-whatsapp-to-timelinesai
2. https://help.timelines.ai/en/articles/12383602-using-whatsapp-multidevice
3. https://help.timelines.ai/en/articles/14337362-whatsapp-coexistence-using-your-whatsapp-business-app-number-with-timelinesai-waba
4. https://timelines.ai/gohighlevel-whatsapp-integration
5. https://timelines.ai/connect-whatsapp-to-gohighlevel
6. https://timelines.ai/gohighlevel-whatsapp-pricing
7. https://timelines.ai/gohighlevel-whatsapp-automation
8. https://timelines.ai/gohighlevel-whatsapp-for-agencies

All returned HTTP 200 when checked on 2026-09-03. The Coexistence article was visibly dated July 27, 2026 and contained no editorial placeholders in the rendered article.
