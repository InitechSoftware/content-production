# GoHighLevel WhatsApp for agencies

Linear: MRKT-5172
Planned slug: `gohighlevel-whatsapp-for-agencies`

This folder contains the repository-backed source and claim evidence for the published article.

Published URL: https://timelines.ai/gohighlevel-whatsapp-for-agencies  
Sanity document: `post-mrkt-5172-gohighlevel-whatsapp-for-agencies`  
Published and independently verified: 2026-09-03

## Publication and current product gates

- Public marketplace behavior is documented in `evidence/marketplace-audit-2026-09-03.md`.
- The shared GHL demo credentials returned `Invalid email or password` on 2026-09-03.
- Marketplace metadata exposes `isAgencyBulkInstallEnabled=true`, but the current integration handles only one selected location and deliberately errors when a Company token has multiple sub-accounts. Treat this as a marketplace-configuration defect, not a supported feature.
- Shared-workspace behavior across sub-accounts and number isolation still need product confirmation before the copy can make affirmative claims.
- Published to Sanity with explicit approval; production returned HTTP 200 with canonical, BlogPosting, FAQPage, cover image, and sitemap verification.
