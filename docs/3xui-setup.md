# Zankode VPN — 3X-UI Setup

This guide configures the optional direct 3X-UI delivery mode in Zankode VPN v2.2.1.

## Recommended panel generation

Zankode's modern adapter targets the current 3X-UI **Clients API**. Keep the panel on a current stable release and create a dedicated API token for the bot. Do not place the token in Git, README screenshots, logs, or support messages.

## 1. Environment

Copy `.env.example` to `.env` and fill the private values:

```env
BOT_TOKEN=...
ADMIN_USER_ID=...
DB_FILE=config_shop.db

XUI_PANEL_URL=https://panel.example.com/your-panel-base-path
XUI_API_TOKEN=...
XUI_API_MODE=modern
XUI_VERIFY_TLS=1
XUI_TIMEOUT=15

# Optional. If this is empty, Zankode asks the 3X-UI Clients API for raw client links.
XUI_SUB_URL_TEMPLATE=https://sub.example.com/sub/{sub_id}
```

`XUI_PANEL_URL` must include the panel base path if your installation uses one. Keep TLS verification enabled in production.

## 2. Configure a plan in Telegram

Open the admin panel and edit the target plan:

1. Change the delivery mode from **Inventory** to **3X-UI**.
2. Set one or more **Inbound IDs**, for example `1,2`.
3. Set the traffic quota in GB. `0` means unlimited.
4. Set the IP limit. `0` means no client IP limit.
5. Keep the plan duration set to the number of days you want the remote expiry to use.

Each plan can use Inventory or 3X-UI independently.

## 3. Health check

Open **Admin → More tools → 3X-UI Center**. The bot performs a live API request when the environment is configured and shows whether the panel is reachable.

## 4. Provisioning behavior

After an order is approved, an XUI-mode plan follows this sequence:

1. Zankode derives a deterministic client identity for the canonical service.
2. The Clients API attaches the client to the configured inbound IDs.
3. 3X-UI generates protocol-specific credentials for modern panels.
4. Zankode immediately reads the client back and stores a local mapping.
5. A configured subscription URL is delivered; otherwise Zankode requests the panel-generated client links.
6. Service validity is activated at delivery time; only after Telegram delivery succeeds is the normal order marked completed.

The local mapping is written before Telegram delivery. If Telegram fails after the remote client was created, a retry reuses the existing client instead of creating a duplicate. If the process crashes after the remote action but before the local marker, Zankode reconciles the deterministic remote state before applying another mutation.

## 5. Renewal

A renewal order linked to an existing XUI service updates that same client to a deterministic target expiry, applies the renewal plan's quota/IP limit, requests a traffic reset when the renewal is first applied, and re-delivers the existing service credential. Renewal transactions stay linked to one canonical active service.

## 6. Gifts

For an XUI-mode gift, purchasing the gift creates the voucher only. The remote client and its expiry are created when the recipient redeems the Gift Code, so the recipient receives the full purchased duration and becomes the operational service owner.

## 7. Status and deletion

Users can refresh the live status of their own XUI service. Admin order views expose sync and remote-delete controls. Deleting a remote client is a destructive action and requires the explicit admin confirmation button.

## Legacy mode

`XUI_API_MODE=legacy` is provided for older X-UI style deployments using username/password session login. Modern token-based mode is preferred. Legacy behavior is best-effort because old panel forks differ in endpoint behavior.

## Production boundary

The automated test suite validates database migrations, Telegram-delivery failure recovery and the 3X-UI HTTP contract with a mocked HTTP transport. A real deployment still depends on the exact panel URL, token permissions, reverse proxy/TLS configuration, inbound protocol and network reachability of the production server.
