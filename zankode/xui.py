# -*- coding: utf-8 -*-
"""3X-UI / X-UI API adapter used by Zankode VPN.

The adapter targets the modern 3X-UI Clients API (v3.x) and keeps a small
legacy fallback for older panels.  It is intentionally isolated from Telegram
handlers so panel API changes do not leak into the sales/domain layer.
"""

from __future__ import annotations

import json
import os
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Optional
from urllib.parse import quote

import httpx


class XUIError(RuntimeError):
    """A sanitized operational error raised by the XUI adapter."""


@dataclass(slots=True)
class XUISettings:
    base_url: str
    api_token: str = ""
    username: str = ""
    password: str = ""
    verify_tls: bool = True
    timeout: float = 15.0
    api_mode: str = "modern"
    sub_url_template: str = ""

    @classmethod
    def from_env(cls) -> "XUISettings":
        base = os.getenv("XUI_PANEL_URL", "").strip().rstrip("/")
        token = os.getenv("XUI_API_TOKEN", "").strip()
        user = os.getenv("XUI_USERNAME", "").strip()
        password = os.getenv("XUI_PASSWORD", "").strip()
        verify_raw = os.getenv("XUI_VERIFY_TLS", "1").strip().lower()
        verify = verify_raw not in {"0", "false", "no", "off"}
        try:
            timeout = max(3.0, min(60.0, float(os.getenv("XUI_TIMEOUT", "15") or 15)))
        except ValueError:
            timeout = 15.0
        mode = (os.getenv("XUI_API_MODE", "modern").strip().lower() or "modern")
        if mode not in {"modern", "legacy", "auto"}:
            mode = "modern"
        sub_template = os.getenv("XUI_SUB_URL_TEMPLATE", "").strip()
        sub_base = os.getenv("XUI_SUB_BASE_URL", "").strip().rstrip("/")
        if not sub_template and sub_base:
            sub_template = sub_base + "/sub/{sub_id}"
        return cls(
            base_url=base,
            api_token=token,
            username=user,
            password=password,
            verify_tls=verify,
            timeout=timeout,
            api_mode=mode,
            sub_url_template=sub_template,
        )

    @property
    def configured(self) -> bool:
        if not self.base_url:
            return False
        if self.api_mode == "modern":
            return bool(self.api_token)
        if self.api_mode == "legacy":
            return bool(self.username and self.password)
        return bool(self.api_token or (self.username and self.password))


@dataclass(slots=True)
class XUIProvisionedClient:
    email: str
    uuid: str
    sub_id: str
    inbound_ids: list[int]
    total_bytes: int
    expiry_ms: int
    limit_ip: int
    subscription_url: str
    raw: dict[str, Any]


@dataclass(slots=True)
class XUIClientStatus:
    email: str
    enabled: bool
    total_bytes: int
    used_bytes: int
    expiry_ms: int
    limit_ip: int
    inbound_ids: list[int]
    sub_id: str
    online: Optional[bool] = None
    raw: Optional[dict[str, Any]] = None

    @property
    def remaining_bytes(self) -> int:
        if self.total_bytes <= 0:
            return -1
        return max(0, self.total_bytes - self.used_bytes)


class XUIClient:
    """Small async client for modern 3X-UI and legacy X-UI compatible APIs."""

    def __init__(self, settings: Optional[XUISettings] = None, *, transport=None):
        self.settings = settings or XUISettings.from_env()
        self._transport = transport
        self._legacy_cookies: Optional[httpx.Cookies] = None

    @property
    def configured(self) -> bool:
        return self.settings.configured

    def _url(self, path: str) -> str:
        if not self.settings.base_url:
            raise XUIError("XUI_PANEL_URL تنظیم نشده است")
        return self.settings.base_url + "/" + path.lstrip("/")

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.settings.api_token:
            headers["Authorization"] = f"Bearer {self.settings.api_token}"
        return headers

    async def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            verify=self.settings.verify_tls,
            timeout=self.settings.timeout,
            follow_redirects=False,
            headers=self._headers(),
            transport=self._transport,
        )

    @staticmethod
    def _json_or_error(response: httpx.Response) -> dict[str, Any]:
        if response.status_code >= 400:
            text = (response.text or "").strip().replace("\n", " ")[:300]
            raise XUIError(f"3X-UI HTTP {response.status_code}: {text or 'request failed'}")
        if not response.content:
            # Old X-UI builds occasionally return an empty 2xx body.
            return {"success": True, "obj": None, "msg": ""}
        try:
            payload = response.json()
        except ValueError as exc:
            raise XUIError("پاسخ 3X-UI JSON معتبر نیست") from exc
        if isinstance(payload, dict) and payload.get("success") is False:
            raise XUIError(str(payload.get("msg") or "3X-UI request failed")[:300])
        if not isinstance(payload, dict):
            raise XUIError("فرمت پاسخ 3X-UI پشتیبانی نمی‌شود")
        return payload

    async def _modern_request(self, method: str, path: str, *, json_body=None, params=None) -> dict[str, Any]:
        if not self.settings.api_token:
            raise XUIError("XUI_API_TOKEN برای API جدید 3X-UI تنظیم نشده است")
        async with await self._client() as client:
            try:
                r = await client.request(method, self._url(path), json=json_body, params=params)
            except httpx.HTTPError as exc:
                raise XUIError(f"ارتباط با 3X-UI برقرار نشد: {exc.__class__.__name__}") from exc
        return self._json_or_error(r)

    async def _legacy_login(self, client: httpx.AsyncClient):
        if self._legacy_cookies:
            client.cookies.update(self._legacy_cookies)
            return
        if not (self.settings.username and self.settings.password):
            raise XUIError("XUI_USERNAME/XUI_PASSWORD برای Legacy API تنظیم نشده است")
        try:
            r = await client.post(
                self._url("login"),
                data={"username": self.settings.username, "password": self.settings.password},
            )
        except httpx.HTTPError as exc:
            raise XUIError("ورود به X-UI قدیمی ناموفق بود") from exc
        payload = self._json_or_error(r)
        if payload.get("success") is False:
            raise XUIError(str(payload.get("msg") or "Legacy X-UI login failed"))
        self._legacy_cookies = httpx.Cookies(r.cookies)
        client.cookies.update(r.cookies)

    async def _legacy_request(self, method: str, path: str, *, data=None, json_body=None) -> dict[str, Any]:
        async with await self._client() as client:
            await self._legacy_login(client)
            try:
                r = await client.request(method, self._url(path), data=data, json=json_body)
            except httpx.HTTPError as exc:
                raise XUIError(f"ارتباط با X-UI قدیمی برقرار نشد: {exc.__class__.__name__}") from exc
        return self._json_or_error(r)

    async def health(self) -> dict[str, Any]:
        if not self.configured:
            raise XUIError("تنظیمات XUI کامل نیست")
        if self.settings.api_mode in {"modern", "auto"} and self.settings.api_token:
            return await self._modern_request("GET", "panel/api/inbounds/list")
        return await self._legacy_request("GET", "panel/api/inbounds/list")

    async def list_inbounds(self) -> list[dict[str, Any]]:
        payload = await self.health()
        obj = payload.get("obj")
        if isinstance(obj, list):
            return [x for x in obj if isinstance(x, dict)]
        return []

    def subscription_url(self, sub_id: str, email: str = "") -> str:
        template = self.settings.sub_url_template
        if not template:
            return ""
        try:
            return template.format(
                sub_id=quote(sub_id, safe=""),
                email=quote(email, safe=""),
            )
        except Exception as exc:
            raise XUIError("XUI_SUB_URL_TEMPLATE معتبر نیست") from exc

    async def connection_urls(self, email: str) -> list[str]:
        """Return raw protocol URLs from the modern Clients API when available."""
        if not (self.settings.api_mode in {"modern", "auto"} and self.settings.api_token):
            return []
        payload = await self._modern_request(
            "GET", f"panel/api/clients/links/{quote(email, safe='')}"
        )
        obj = payload.get("obj")
        values: list[Any] = []
        if isinstance(obj, list):
            values = obj
        elif isinstance(obj, dict):
            for key in ("links", "urls", "data", "items"):
                if isinstance(obj.get(key), list):
                    values = obj[key]
                    break
        out: list[str] = []
        for value in values:
            if isinstance(value, str) and "://" in value and value not in out:
                out.append(value.strip())
            elif isinstance(value, dict):
                candidate = value.get("url") or value.get("link")
                if isinstance(candidate, str) and "://" in candidate and candidate not in out:
                    out.append(candidate.strip())
        return out[:50]

    async def delivery_credential(self, sub_id: str, email: str) -> str:
        """Prefer a stable subscription URL; otherwise deliver panel-generated links."""
        sub = self.subscription_url(sub_id, email)
        if sub:
            return sub
        links = await self.connection_urls(email)
        if links:
            return "\n".join(links)
        raise XUIError(
            "آدرس Subscription تنظیم نشده و 3X-UI نیز لینک اتصال قابل تحویل برنگرداند"
        )

    @staticmethod
    def _clean_inbound_ids(inbound_ids: Iterable[int]) -> list[int]:
        out: list[int] = []
        for value in inbound_ids:
            try:
                n = int(value)
            except (TypeError, ValueError):
                continue
            if n > 0 and n not in out:
                out.append(n)
        if not out:
            raise XUIError("برای پلن XUI حداقل یک Inbound ID لازم است")
        return out[:50]

    @staticmethod
    def _client_payload(
        *,
        email: str,
        sub_id: str,
        total_bytes: int,
        expiry_ms: int,
        limit_ip: int,
        tg_id: int,
        comment: str,
        flow: str = "",
    ) -> dict[str, Any]:
        # 3X-UI v3.6+ generates protocol-specific credentials (UUID/password/auth)
        # server-side when omitted. Supplying only universal fields avoids
        # protocol coupling and follows the typed Clients API contract.
        return {
            "email": email,
            "subId": sub_id,
            "totalGB": max(0, int(total_bytes)),
            "expiryTime": max(0, int(expiry_ms)),
            "limitIp": max(0, int(limit_ip)),
            "tgId": max(0, int(tg_id)),
            "comment": comment[:250],
            "flow": flow[:100],
            "reset": 0,
            "enable": True,
        }

    async def create_client(
        self,
        *,
        email: str,
        inbound_ids: Iterable[int],
        total_bytes: int,
        expiry_ms: int,
        limit_ip: int,
        tg_id: int,
        comment: str,
        flow: str = "",
    ) -> XUIProvisionedClient:
        inbound_ids = self._clean_inbound_ids(inbound_ids)
        email = email.strip()[:128]
        if not email:
            raise XUIError("شناسه Client خالی است")
        # Modern 3X-UI generates protocol credentials itself. A UUID is still
        # generated locally for legacy X-UI where the old API requires it.
        client_uuid = str(uuid.uuid4())
        sub_id = secrets.token_urlsafe(12).replace("-", "").replace("_", "")[:20]
        client_data = self._client_payload(
            email=email,
            sub_id=sub_id,
            total_bytes=total_bytes,
            expiry_ms=expiry_ms,
            limit_ip=limit_ip,
            tg_id=tg_id,
            comment=comment,
            flow=flow,
        )

        if self.settings.api_mode in {"modern", "auto"} and self.settings.api_token:
            existing = await self.get_client_optional(email)
            payload: dict[str, Any] = {"recovered": True}
            if existing is None:
                try:
                    payload = await self._modern_request(
                        "POST", "panel/api/clients/add",
                        json_body={"client": client_data, "inboundIds": inbound_ids},
                    )
                except XUIError:
                    existing = await self.get_client_optional(email)
                    if existing is None:
                        raise
            readback = existing or await self.get_client(email)
            await self.reconcile_inbounds(email, inbound_ids)
            current = readback.get("client", {}) if isinstance(readback, dict) else {}
            desired = {
                "totalGB": max(0, int(total_bytes)),
                "expiryTime": max(0, int(expiry_ms)),
                "limitIp": max(0, int(limit_ip)),
                "tgId": max(0, int(tg_id)),
                "comment": comment[:250],
                "enable": True,
            }
            if any(current.get(k) != v for k, v in desired.items()):
                await self.update_client(email, **desired)
                readback = await self.get_client(email)
            actual = readback.get("client", {}) if isinstance(readback, dict) else {}
            actual_uuid = str(actual.get("uuid") or actual.get("id") or "")
            actual_sub = str(actual.get("subId") or actual.get("subid") or sub_id)
            return XUIProvisionedClient(
                email=email,
                uuid=actual_uuid,
                sub_id=actual_sub,
                inbound_ids=[int(x) for x in (readback.get("inboundIds") or inbound_ids) if str(x).isdigit()],
                total_bytes=int(actual.get("totalGB") or total_bytes or 0),
                expiry_ms=int(actual.get("expiryTime") or expiry_ms or 0),
                limit_ip=int(actual.get("limitIp") or limit_ip or 0),
                subscription_url=self.subscription_url(actual_sub, email),
                raw={"add": payload, "get": readback},
            )

        # Legacy v2.x API: one addClient call per inbound.
        for inbound_id in inbound_ids:
            legacy_client = {
                "id": client_uuid,
                "flow": flow,
                "email": email,
                "limitIp": max(0, int(limit_ip)),
                "totalGB": max(0, int(total_bytes)),
                "expiryTime": max(0, int(expiry_ms)),
                "enable": True,
                "tgId": str(max(0, int(tg_id))),
                "subId": sub_id,
                "comment": comment[:250],
                "reset": 0,
            }
            await self._legacy_request(
                "POST",
                "panel/api/inbounds/addClient",
                data={"id": str(inbound_id), "settings": json.dumps({"clients": [legacy_client]})},
            )
        return XUIProvisionedClient(
            email=email,
            uuid=client_uuid,
            sub_id=sub_id,
            inbound_ids=inbound_ids,
            total_bytes=max(0, int(total_bytes)),
            expiry_ms=max(0, int(expiry_ms)),
            limit_ip=max(0, int(limit_ip)),
            subscription_url=self.subscription_url(sub_id, email),
            raw={"legacy": True},
        )

    async def get_client(self, email: str) -> dict[str, Any]:
        email_q = quote(email, safe="")
        if self.settings.api_mode in {"modern", "auto"} and self.settings.api_token:
            payload = await self._modern_request("GET", f"panel/api/clients/get/{email_q}")
            obj = payload.get("obj")
            if not isinstance(obj, dict):
                raise XUIError("Client در 3X-UI پیدا نشد")
            return obj
        # Legacy returns traffic data rather than a canonical client object.
        payload = await self._legacy_request("GET", f"panel/api/inbounds/getClientTraffics/{email_q}")
        obj = payload.get("obj")
        if isinstance(obj, dict):
            return {"client": obj, "inboundIds": [obj.get("inboundId")] if obj.get("inboundId") else []}
        raise XUIError("Client در X-UI پیدا نشد")

    async def get_client_optional(self, email: str) -> Optional[dict[str, Any]]:
        """Return a client when it exists, while preserving transport/auth errors."""
        try:
            return await self.get_client(email)
        except XUIError as exc:
            text = str(exc).lower()
            if "http 404" in text or "not found" in text or "پیدا نشد" in text:
                return None
            raise

    async def reconcile_inbounds(self, email: str, desired_inbound_ids: Iterable[int]) -> list[int]:
        """Make modern 3X-UI inbound membership match the frozen order snapshot."""
        desired = self._clean_inbound_ids(desired_inbound_ids)
        if not (self.settings.api_mode in {"modern", "auto"} and self.settings.api_token):
            return desired
        current = await self.get_client(email)
        current_ids = [int(x) for x in (current.get("inboundIds") or []) if str(x).isdigit()]
        missing = [x for x in desired if x not in current_ids]
        extra = [x for x in current_ids if x not in desired]
        if missing:
            await self._modern_request(
                "POST", f"panel/api/clients/{quote(email, safe='')}/attach",
                json_body={"inboundIds": missing},
            )
        if extra:
            await self._modern_request(
                "POST", f"panel/api/clients/{quote(email, safe='')}/detach",
                json_body={"inboundIds": extra},
            )
        return desired

    async def _paged_client_row(self, email: str) -> Optional[dict[str, Any]]:
        if not (self.settings.api_mode in {"modern", "auto"} and self.settings.api_token):
            return None
        payload = await self._modern_request(
            "GET", "panel/api/clients/list/paged",
            params={"search": email, "page": 1, "pageSize": 20},
        )
        obj = payload.get("obj")
        rows: list[Any] = []
        if isinstance(obj, list):
            rows = obj
        elif isinstance(obj, dict):
            for key in ("clients", "items", "records", "data"):
                if isinstance(obj.get(key), list):
                    rows = obj[key]
                    break
        for row in rows:
            if isinstance(row, dict) and str(row.get("email", "")).lower() == email.lower():
                return row
        return None

    async def status(self, email: str) -> XUIClientStatus:
        obj = await self.get_client(email)
        client = obj.get("client", obj) if isinstance(obj, dict) else {}
        inbound_ids = obj.get("inboundIds", []) if isinstance(obj, dict) else []
        row = await self._paged_client_row(email)
        traffic: dict[str, Any] = {}
        if self.settings.api_mode in {"modern", "auto"} and self.settings.api_token:
            try:
                traffic_payload = await self._modern_request(
                    "GET", f"panel/api/clients/traffic/{quote(email, safe='')}"
                )
                traffic_obj = traffic_payload.get("obj")
                if isinstance(traffic_obj, dict):
                    traffic = traffic_obj.get("traffic", traffic_obj) if isinstance(traffic_obj.get("traffic", traffic_obj), dict) else {}
            except XUIError:
                # Older typed-API builds may not expose the dedicated endpoint.
                traffic = {}
        if not traffic and isinstance(row, dict) and isinstance(row.get("traffic"), dict):
            traffic = row.get("traffic", {})
        used = int(traffic.get("up") or 0) + int(traffic.get("down") or 0)
        # Some builds expose aggregate usage directly.
        if not used and isinstance(row, dict):
            used = int(row.get("usedGB") or row.get("used") or 0)
        return XUIClientStatus(
            email=email,
            enabled=bool(client.get("enable", True)),
            total_bytes=int(client.get("totalGB") or 0),
            used_bytes=max(0, used),
            expiry_ms=int(client.get("expiryTime") or 0),
            limit_ip=int(client.get("limitIp") or 0),
            inbound_ids=[int(x) for x in inbound_ids if str(x).isdigit()],
            sub_id=str(client.get("subId") or client.get("subid") or ""),
            online=(bool(row.get("online")) if isinstance(row, dict) and "online" in row else None),
            raw={"get": obj, "list": row},
        )

    async def update_client(self, email: str, **changes) -> dict[str, Any]:
        if not (self.settings.api_mode in {"modern", "auto"} and self.settings.api_token):
            raise XUIError("ویرایش/تمدید خودکار در این نسخه فقط با 3X-UI API جدید پشتیبانی می‌شود")
        current = await self.get_client(email)
        client = dict(current.get("client") or {})
        if not client:
            raise XUIError("اطلاعات Client برای ویرایش دریافت نشد")
        client.update({k: v for k, v in changes.items() if v is not None})
        # Keep both spellings for compatibility, but do not invent missing secrets.
        if client.get("subid") and not client.get("subId"):
            client["subId"] = client["subid"]
        payload = await self._modern_request(
            "POST", f"panel/api/clients/update/{quote(email, safe='')}", json_body=client
        )
        return payload

    async def renew_client(
        self,
        email: str,
        *,
        duration_days: int = 30,
        target_expiry_ms: Optional[int] = None,
        total_bytes: Optional[int] = None,
        limit_ip: Optional[int] = None,
        reset_traffic: bool = True,
        tg_id: Optional[int] = None,
        comment: Optional[str] = None,
    ) -> XUIClientStatus:
        """Renew to an exact target when supplied, making retries idempotent."""
        status = await self.status(email)
        if target_expiry_ms is None:
            now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
            base = max(now_ms, int(status.expiry_ms or 0))
            expiry_ms = base + max(1, int(duration_days)) * 86400 * 1000
        else:
            expiry_ms = max(0, int(target_expiry_ms))
        await self.update_client(
            email,
            expiryTime=expiry_ms,
            totalGB=(max(0, int(total_bytes)) if total_bytes is not None else status.total_bytes),
            limitIp=(max(0, int(limit_ip)) if limit_ip is not None else status.limit_ip),
            tgId=(max(0, int(tg_id)) if tg_id is not None else None),
            comment=(str(comment)[:250] if comment is not None else None),
            enable=True,
        )
        if reset_traffic:
            try:
                await self.reset_traffic(email)
            except XUIError:
                pass
        return await self.status(email)

    async def reset_traffic(self, email: str) -> dict[str, Any]:
        email_q = quote(email, safe="")
        if self.settings.api_mode in {"modern", "auto"} and self.settings.api_token:
            return await self._modern_request("POST", f"panel/api/clients/resetTraffic/{email_q}")
        # Legacy requires inbound id; status/getClientTraffics commonly returns it.
        obj = await self.get_client(email)
        inbound_ids = obj.get("inboundIds") or []
        if not inbound_ids:
            raise XUIError("Inbound ID برای Reset Traffic پیدا نشد")
        return await self._legacy_request(
            "POST", f"panel/api/inbounds/{int(inbound_ids[0])}/resetClientTraffic/{email_q}"
        )

    async def delete_client(self, email: str) -> dict[str, Any]:
        email_q = quote(email, safe="")
        if self.settings.api_mode in {"modern", "auto"} and self.settings.api_token:
            return await self._modern_request("POST", f"panel/api/clients/del/{email_q}")
        obj = await self.get_client(email)
        client = obj.get("client") or {}
        client_id = client.get("id") or client.get("uuid")
        inbound_ids = obj.get("inboundIds") or []
        if not client_id or not inbound_ids:
            raise XUIError("اطلاعات کافی برای حذف Client قدیمی وجود ندارد")
        result: dict[str, Any] = {"success": True}
        for inbound_id in inbound_ids:
            result = await self._legacy_request(
                "POST", f"panel/api/inbounds/{int(inbound_id)}/delClient/{quote(str(client_id), safe='')}"
            )
        return result


def bytes_from_gb(gb: int | float) -> int:
    try:
        value = float(gb)
    except (TypeError, ValueError):
        return 0
    if value <= 0:
        return 0
    return int(value * 1024 * 1024 * 1024)
