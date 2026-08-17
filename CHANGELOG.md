# Changelog

## 2.2.1 — 2026-08-18

### Reliability & Correctness
- Service validity now starts on actual delivery/activation instead of order creation.
- Gift validity starts when the recipient redeems the Gift Code; 3X-UI gift clients are provisioned for the recipient at redemption time.
- Orders freeze a technical provisioning snapshot (mode, inbound IDs, quota, and IP limit) so later plan edits cannot change an already-created order.
- 3X-UI renewals now keep one canonical service root instead of appearing as duplicate active services.
- Inventory renewals are modeled as new delivered credentials rather than falsely extending the old credential.
- Existing v2.2.0 XUI renewal rows are migrated into a single canonical service mapping.
- 3X-UI create/renew retries reconcile remote state first and use deterministic exact expiry targets to avoid duplicate clients and double renewal after crashes.
- Renewal recovery detects an already-applied remote target before replaying traffic reset.
- Inventory/XUI credentials are durably staged before Telegram delivery, preventing a sent credential from returning to available stock after a crash.
- Failed credential delivery is retried from the exact staged credential, with bounded automatic retries and an admin alert after repeated failures.
- Expiry notifications, active-service counts, customer segments, and XUI dashboard metrics use canonical service ownership/root state.
- Redeemed XUI gifts expose live service status to the recipient.

### Operations & UX
- Broadcasts run as guarded background tasks so large sends do not block the admin interaction handler and overlapping broadcasts cannot run simultaneously.
- Tehran time now uses the server timezone directly; order creation no longer depends on an external time website.
- 3X-UI configuration text correctly treats the subscription URL template as optional.
- Application shutdown now cancels and awaits the background operations task cleanly.
- Secret redaction in logs also covers 3X-UI API tokens and legacy passwords.
- Runtime database ignore rules now cover custom `.db`, `.sqlite`, and `.sqlite3` filenames.

### Testing
- 29 automated tests cover database migrations, activation timing, plan snapshots, inventory/XUI renewal semantics, gift ownership, staged delivery recovery, XUI create/read/status/renew/reset/delete flows, crash-window reconciliation, admin purchase views, and notification reliability.
- Full Python source compilation and SQLite integrity checks pass in the local validation environment.

## 2.2.0 — 2026-08-17

### Added
- Direct 3X-UI Clients API adapter with modern API-token authentication and optional legacy mode.
- Per-plan provisioning mode: internal Inventory or direct 3X-UI.
- Per-plan 3X-UI inbound IDs, traffic quota and IP limit.
- Automatic remote client creation after order approval.
- Remote renewal of the existing client with expiry/quota/IP updates and traffic reset.
- Live service status for users: enabled state, usage, remaining quota, expiry and IP limit.
- Admin 3X-UI Center with health check and local XUI service metrics.
- Admin sync/retry/delete controls for XUI orders.
- Local `Order ↔ User ↔ 3X-UI Client` mapping for idempotent provisioning and crash-safe retries.
- Fallback delivery using panel-generated client links when no public subscription URL template is configured.
- 3X-UI service metrics in the main admin sales dashboard.
- `docs/3xui-setup.md` production setup guide.
- Dedicated automated XUI tests covering add/read-back, traffic status, link fallback, renewal/reset and Telegram-delivery retry safety.

### Reliability / Compatibility
- Modern client creation follows the typed Clients API model and lets 3X-UI generate protocol-specific credentials.
- Remote state is read back immediately after creation before local delivery proceeds.
- A remote client is never recreated merely because Telegram credential delivery failed.
- Existing v2.1 Inventory plans continue to work without requiring 3X-UI configuration.
- Existing databases are migrated in place with new plan fields and the `xui_services` table.

### Testing
- 16 automated tests pass in the local mocked/stubbed test environment.
- Full source compilation passes.
- All Zankode Python modules import successfully under the Telegram test stub.

## 2.1.0 — 2026-08-17

### Added
- Direct buyer-to-purchase visibility in the admin order list.
- Recent completed purchases in each admin user profile.
- One-click access to the full completed-purchase history of a user.
- Buyer identity (`user_id`, `username`, `full_name`) in order CSV exports.
- Protected text-file delivery for long VPN configurations.
- Re-download path for long delivered configurations.
- Startup recovery for crash-interrupted gift redemptions.
- Automated tests for purchase mapping, admin views, delivery reliability, alerts, migrations, and gift recovery.

### Fixed
- Renamed project/package branding from the previous name to **Zankode VPN**.
- SQLite connections used through `with db()` are now actually closed after commit/rollback.
- Failed low-stock notifications are retried instead of being permanently suppressed.
- Expiry notification flags are written only after successful Telegram delivery.
- Premium Emoji changes now update the live runtime configuration immediately.
- Maintenance/background operations start even if optional Telegram startup calls fail.
- Low-stock threshold now correctly accepts `0`.
- Long configurations are no longer split across multiple credential messages.
- Gift-code entropy increased for newly generated gift codes.
- CSV formula-injection risk reduced for user-controlled exported cells.

### Compatibility
- Existing `config_shop.db` files are preserved and migrated in place.
- The old default shop-name value is recognized only for migration to `Zankode VPN`; custom shop names are not overwritten.
