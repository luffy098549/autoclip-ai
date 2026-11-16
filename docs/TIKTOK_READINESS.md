# TikTok review readiness

This checklist is deliberately fail-closed. Never submit placeholder legal pages.

1. Finalize Terms and Privacy Policy with accurate operator identity, contact, jurisdiction, data retention, subprocessors and rights procedures. Obtain appropriate legal review.
2. Deploy the application on a stable public HTTPS origin, with a persistent strong SECRET_KEY and secure cookies.
3. Set AUTOCLIP_PUBLIC_ORIGIN to the deployed HTTPS origin and run `python -m scripts.check_tiktok_readiness`. The command tests the three public pages and rejects legal draft markers. It does **not** verify the legal accuracy of the text.
4. Configure TikTok's exact verification filename and token privately, verify the public response matches the portal, and complete domain ownership verification.
5. Register the exact HTTPS OAuth redirect URI, complete authorization and revocation tests with an authorized test account, and review requested scopes. Never log authorization codes or tokens.
6. Record a genuine demo of the requested integration and submit for platform review only when all requirements are satisfied.

**Do not claim the TikTok integration is approved or ready based solely on a passing readiness command.** The command never performs social publishing.
