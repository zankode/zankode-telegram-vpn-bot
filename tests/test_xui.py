import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import httpx
from telegram.error import TelegramError

from zankode import storage, services
from zankode.xui import XUIClient, XUISettings, XUIProvisionedClient, XUIClientStatus, bytes_from_gb


class XUIAdapterTest(unittest.IsolatedAsyncioTestCase):
    async def test_modern_create_client_uses_bearer_and_reads_back(self):
        seen = {}

        get_count = {"n": 0}

        def handler(request: httpx.Request):
            seen.setdefault("requests", []).append(request)
            if request.url.path.endswith("/panel/api/clients/add"):
                body = json.loads(request.content.decode())
                seen["add_body"] = body
                self.assertEqual(request.headers.get("authorization"), "Bearer secret-token")
                return httpx.Response(200, json={"success": True, "obj": None})
            if "/panel/api/clients/get/" in request.url.path:
                get_count["n"] += 1
                if get_count["n"] == 1:
                    return httpx.Response(404, text="not found")
                email = request.url.path.rsplit("/", 1)[1]
                return httpx.Response(200, json={
                    "success": True,
                    "obj": {
                        "client": {
                            "email": email,
                            "uuid": "remote-uuid",
                            "subId": "remote-sub",
                            "totalGB": 50 * 1024**3,
                            "expiryTime": 1800000000000,
                            "limitIp": 2,
                            "tgId": 100,
                            "comment": "order #1",
                            "enable": True,
                        },
                        "inboundIds": [1, 2],
                    },
                })
            return httpx.Response(404, text="unexpected")

        settings = XUISettings(
            base_url="https://panel.example/secret",
            api_token="secret-token",
            verify_tls=True,
            api_mode="modern",
            sub_url_template="https://sub.example/sub/{sub_id}",
        )
        xui = XUIClient(settings, transport=httpx.MockTransport(handler))
        out = await xui.create_client(
            email="zk_100_1",
            inbound_ids=[1, 2],
            total_bytes=50 * 1024**3,
            expiry_ms=1800000000000,
            limit_ip=2,
            tg_id=100,
            comment="order #1",
        )
        self.assertEqual(out.email, "zk_100_1")
        self.assertEqual(out.sub_id, "remote-sub")
        self.assertEqual(out.inbound_ids, [1, 2])
        self.assertEqual(out.subscription_url, "https://sub.example/sub/remote-sub")
        self.assertEqual(seen["add_body"]["inboundIds"], [1, 2])
        self.assertEqual(seen["add_body"]["client"]["totalGB"], 50 * 1024**3)
        self.assertEqual(seen["add_body"]["client"]["limitIp"], 2)
        self.assertNotIn("uuid", seen["add_body"]["client"], "modern 3X-UI should generate protocol credentials")


class XUIRuntimeApiTest(unittest.IsolatedAsyncioTestCase):
    async def test_delivery_falls_back_to_panel_generated_client_links(self):
        def handler(request: httpx.Request):
            if "/panel/api/clients/links/" in request.url.path:
                return httpx.Response(200, json={
                    "success": True,
                    "obj": [
                        "vless://uuid@example.com:443?type=tcp#Zankode",
                        "trojan://secret@example.com:443#Backup",
                    ],
                })
            return httpx.Response(404, text="unexpected")

        xui = XUIClient(XUISettings(
            base_url="https://panel.example",
            api_token="token",
            api_mode="modern",
            sub_url_template="",
        ), transport=httpx.MockTransport(handler))
        credential = await xui.delivery_credential("sub-1", "zk_1_1")
        self.assertIn("vless://", credential)
        self.assertIn("trojan://", credential)

    async def test_status_uses_dedicated_traffic_endpoint(self):
        def handler(request: httpx.Request):
            path = request.url.path
            if "/panel/api/clients/get/" in path:
                return httpx.Response(200, json={"success": True, "obj": {
                    "client": {"email": "zk_1_1", "subId": "sub", "totalGB": 10_000,
                               "expiryTime": 1800000000000, "limitIp": 2, "enable": True},
                    "inboundIds": [7],
                }})
            if path.endswith("/panel/api/clients/list/paged"):
                return httpx.Response(200, json={"success": True, "obj": {"items": []}})
            if "/panel/api/clients/traffic/" in path:
                return httpx.Response(200, json={"success": True, "obj": {"up": 1200, "down": 2300}})
            return httpx.Response(404, text="unexpected")

        xui = XUIClient(XUISettings(
            base_url="https://panel.example", api_token="token", api_mode="modern"
        ), transport=httpx.MockTransport(handler))
        status = await xui.status("zk_1_1")
        self.assertEqual(status.used_bytes, 3500)
        self.assertEqual(status.inbound_ids, [7])
        self.assertTrue(status.enabled)

    async def test_renewal_preserves_client_payload_updates_expiry_and_resets_traffic(self):
        calls = []
        state = {
            "client": {"email": "zk_1_1", "uuid": "u-1", "subId": "sub-1", "totalGB": 1000,
                       "expiryTime": 1800000000000, "limitIp": 1, "enable": True, "comment": "keep"},
            "inboundIds": [1],
            "up": 500,
            "down": 250,
        }

        def handler(request: httpx.Request):
            path = request.url.path
            calls.append((request.method, path))
            if "/panel/api/clients/get/" in path:
                return httpx.Response(200, json={"success": True, "obj": {
                    "client": dict(state["client"]), "inboundIds": state["inboundIds"]}})
            if path.endswith("/panel/api/clients/list/paged"):
                return httpx.Response(200, json={"success": True, "obj": {"items": []}})
            if "/panel/api/clients/traffic/" in path:
                return httpx.Response(200, json={"success": True, "obj": {"up": state["up"], "down": state["down"]}})
            if "/panel/api/clients/update/" in path:
                body = json.loads(request.content.decode())
                self.assertEqual(body["uuid"], "u-1")
                self.assertEqual(body["comment"], "keep")
                self.assertEqual(body["totalGB"], 5000)
                self.assertEqual(body["limitIp"], 3)
                self.assertGreater(body["expiryTime"], 1800000000000)
                state["client"].update(body)
                return httpx.Response(200, json={"success": True, "obj": None})
            if "/panel/api/clients/resetTraffic/" in path:
                state["up"] = state["down"] = 0
                return httpx.Response(200, json={"success": True, "obj": None})
            return httpx.Response(404, text="unexpected")

        xui = XUIClient(XUISettings(
            base_url="https://panel.example", api_token="token", api_mode="modern"
        ), transport=httpx.MockTransport(handler))
        out = await xui.renew_client("zk_1_1", duration_days=30, total_bytes=5000, limit_ip=3)
        self.assertEqual(out.total_bytes, 5000)
        self.assertEqual(out.limit_ip, 3)
        self.assertEqual(out.used_bytes, 0)
        self.assertIn(("POST", "/panel/api/clients/resetTraffic/zk_1_1"), calls)

    async def test_modern_delete_client_uses_clients_api(self):
        seen = []

        def handler(request: httpx.Request):
            seen.append((request.method, request.url.path, request.headers.get("authorization")))
            if request.url.path.endswith("/panel/api/clients/del/zk_1_1"):
                return httpx.Response(200, json={"success": True, "obj": None})
            return httpx.Response(404, text="unexpected")

        xui = XUIClient(XUISettings(
            base_url="https://panel.example", api_token="token", api_mode="modern"
        ), transport=httpx.MockTransport(handler))
        out = await xui.delete_client("zk_1_1")
        self.assertTrue(out["success"])
        self.assertIn(("POST", "/panel/api/clients/del/zk_1_1", "Bearer token"), seen)


class _FlakyBot:
    def __init__(self):
        self.fail_delivery_once = True
        self.messages = []

    async def send_message(self, chat_id, text, **kwargs):
        # The first protected credential delivery fails; later UI messages succeed.
        if kwargs.get("protect_content") and self.fail_delivery_once:
            self.fail_delivery_once = False
            raise TelegramError("simulated Telegram delivery failure")
        self.messages.append((chat_id, text, kwargs))
        return SimpleNamespace()

    async def send_document(self, *args, **kwargs):
        if self.fail_delivery_once:
            self.fail_delivery_once = False
            raise TelegramError("simulated Telegram delivery failure")
        return SimpleNamespace()


class _FakeXUI:
    create_calls = 0
    renew_calls = 0
    last_client = None

    def __init__(self):
        self.configured = True

    def subscription_url(self, sub_id, email=""):
        return f"https://sub.example/sub/{sub_id}"

    async def delivery_credential(self, sub_id, email=""):
        return self.subscription_url(sub_id, email)

    async def create_client(self, **kwargs):
        type(self).create_calls += 1
        type(self).last_client = dict(kwargs)
        return XUIProvisionedClient(
            email=kwargs["email"],
            uuid="uuid-1",
            sub_id="sub-1",
            inbound_ids=list(kwargs["inbound_ids"]),
            total_bytes=int(kwargs["total_bytes"]),
            expiry_ms=int(kwargs["expiry_ms"]),
            limit_ip=int(kwargs["limit_ip"]),
            subscription_url="https://sub.example/sub/sub-1",
            raw={"success": True},
        )

    async def status(self, email):
        data = type(self).last_client or {}
        return XUIClientStatus(
            email=email, enabled=True, total_bytes=int(data.get("total_bytes", 0)),
            used_bytes=0, expiry_ms=int(data.get("expiry_ms", 0)),
            limit_ip=int(data.get("limit_ip", 0)), inbound_ids=list(data.get("inbound_ids", [])),
            sub_id="sub-1", online=None, raw={},
        )

    async def renew_client(self, email, *, target_expiry_ms=None, total_bytes=None, limit_ip=None, reset_traffic=True, tg_id=None, comment=None, **kwargs):
        type(self).renew_calls += 1
        data = dict(type(self).last_client or {})
        data["email"] = email
        if target_expiry_ms is not None:
            data["expiry_ms"] = int(target_expiry_ms)
        if total_bytes is not None:
            data["total_bytes"] = int(total_bytes)
        if limit_ip is not None:
            data["limit_ip"] = int(limit_ip)
        type(self).last_client = data
        return await self.status(email)

    async def delete_client(self, email):
        return {"success": True}


class XUIProvisioningReliabilityTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_db = storage.DB_PATH
        self.old_svc_db = services.DB_PATH
        self.db_path = Path(self.tmp.name) / "xui_test.db"
        storage.DB_PATH = self.db_path
        services.DB_PATH = self.db_path
        storage.init_db()
        with storage.db() as c:
            c.execute("DELETE FROM plans")
            n = storage.now()
            c.executemany(
                "INSERT INTO users(user_id,username,full_name,is_blocked,created_at,last_seen) VALUES(?,?,?,?,?,?)",
                [(100,'tester','Tester',0,n,n),(101,'recipient','Recipient',0,n,n)],
            )
            c.execute(
                "INSERT INTO plans(title,price,description,duration_days,provision_mode,xui_inbound_ids,xui_traffic_gb,xui_ip_limit,is_active,created_at,updated_at) "
                "VALUES('XUI 50GB',100000,'xui',30,'xui','1,2',50,2,1,?,?)",
                (storage.now(), storage.now()),
            )
        self.old_client_cls = services.XUIClient
        services.XUIClient = _FakeXUI
        _FakeXUI.create_calls = 0
        _FakeXUI.renew_calls = 0
        _FakeXUI.last_client = None

    async def asyncTearDown(self):
        services.XUIClient = self.old_client_cls
        storage.DB_PATH = self.old_db
        services.DB_PATH = self.old_svc_db
        self.tmp.cleanup()

    async def test_retry_after_telegram_failure_does_not_create_duplicate_xui_client(self):
        plan = storage.active_plans()[0]
        oid = storage.create_order(100, plan, storage.iran_now(), "test")
        storage.update_status(oid, storage.APPROVED, approved=True)
        bot = _FlakyBot()
        context = SimpleNamespace(bot=bot)

        first = await services.fulfill_approved_order(context, oid, actor="test")
        self.assertFalse(first)
        self.assertEqual(_FakeXUI.create_calls, 1)
        self.assertEqual(storage.get_order(oid)["status"], storage.APPROVED)
        self.assertIsNotNone(storage.xui_service_for_order(oid))

        second = await services.fulfill_approved_order(context, oid, actor="test")
        self.assertTrue(second)
        self.assertEqual(_FakeXUI.create_calls, 1, "retry must reuse the already-created remote client")
        self.assertEqual(storage.get_order(oid)["status"], storage.COMPLETED)
        self.assertEqual(storage.get_order(oid)["delivered_config"], "https://sub.example/sub/sub-1")

    async def test_renewal_retry_reuses_staged_credential_and_never_double_extends_remote(self):
        plan = storage.active_plans()[0]
        root = storage.create_order(100, plan)
        storage.update_status(root, storage.APPROVED, approved=True)
        root_bot = _FlakyBot()
        root_bot.fail_delivery_once = False
        self.assertTrue(await services.fulfill_approved_order(SimpleNamespace(bot=root_bot), root, actor="test"))
        root_before = storage.get_order(root)

        renewal = storage.create_order(100, plan, renew_parent_order_id=root)
        storage.update_status(renewal, storage.APPROVED, approved=True)
        flaky = _FlakyBot()
        first = await services.fulfill_approved_order(SimpleNamespace(bot=flaky), renewal, actor="test")
        self.assertFalse(first)
        self.assertEqual(_FakeXUI.renew_calls, 1)
        staged = storage.get_order(renewal)["delivered_config"]
        self.assertTrue(staged)
        target_expiry = storage.get_order(renewal)["expires_at"]

        second = await services.fulfill_approved_order(SimpleNamespace(bot=flaky), renewal, actor="test")
        self.assertTrue(second)
        self.assertEqual(_FakeXUI.renew_calls, 1, "delivery retry must not re-apply remote renewal")
        self.assertEqual(storage.get_order(root)["expires_at"], target_expiry)
        self.assertGreater(storage.parse_db_dt(target_expiry), storage.parse_db_dt(root_before["expires_at"]))
        self.assertEqual(len(storage.delivered_services(100)), 1)

    async def test_renewal_recovers_remote_success_before_local_marker_without_second_reset(self):
        plan = storage.active_plans()[0]
        root = storage.create_order(100, plan)
        storage.update_status(root, storage.APPROVED, approved=True)
        storage.finalize_service_delivery(root, "https://sub.example/sub/sub-1", owner_uid=100)
        root_order = storage.get_order(root)
        root_expiry_ms = int(storage.parse_db_dt(root_order["expires_at"]).timestamp() * 1000)
        total_bytes = bytes_from_gb(storage.order_xui_traffic_gb(root_order))
        storage.upsert_xui_service(
            root, 100, int(plan["id"]), "zk_100_root", "uuid-1", "sub-1", [1, 2],
            total_bytes, root_expiry_ms, 2,
        )

        renewal = storage.create_order(100, plan, renew_parent_order_id=root)
        storage.update_status(renewal, storage.APPROVED, approved=True)
        _, target = storage.prepare_service_activation(renewal, owner_uid=100)
        target_ms = int(target.timestamp() * 1000)

        # Simulate: the remote panel already accepted the renewal, but the process
        # crashed before remote_applied_at was persisted locally.
        _FakeXUI.last_client = {
            "email": "zk_100_root",
            "inbound_ids": [1, 2],
            "total_bytes": total_bytes,
            "expiry_ms": target_ms,
            "limit_ip": 2,
        }
        _FakeXUI.renew_calls = 0

        email, sub_id = await services._ensure_xui_for_order(
            _FakeXUI(), storage.get_order(renewal), owner_uid=100
        )
        self.assertEqual(email, "zk_100_root")
        self.assertEqual(sub_id, "sub-1")
        self.assertEqual(_FakeXUI.renew_calls, 0, "already-applied renewal must be recovered, not replayed")
        self.assertIsNotNone(storage.get_order(renewal)["remote_applied_at"])

    async def test_xui_gift_is_created_only_when_recipient_redeems(self):
        plan = storage.active_plans()[0]
        gift_order = storage.create_order(100, plan, is_gift=True)
        storage.update_status(gift_order, storage.APPROVED, approved=True)
        bot = _FlakyBot()
        bot.fail_delivery_once = False
        ctx = SimpleNamespace(bot=bot)
        self.assertTrue(await services.fulfill_approved_order(ctx, gift_order, actor="test"))
        self.assertEqual(_FakeXUI.create_calls, 0, "buyer purchase must not start XUI gift validity")
        order = storage.get_order(gift_order)
        self.assertEqual(order["status"], storage.COMPLETED)
        self.assertIsNone(order["expires_at"])
        gift = storage.gift_for_order(gift_order)
        reserved = storage.reserve_gift_redeem(101, gift["code"])
        self.assertIsNotNone(reserved)
        self.assertTrue(await services.redeem_gift_service(ctx, reserved, 101))
        self.assertEqual(_FakeXUI.create_calls, 1)
        activated = storage.get_order(gift_order)
        self.assertEqual(int(activated["service_owner_user_id"]), 101)
        self.assertIsNotNone(activated["expires_at"])
        self.assertEqual(storage.gift_for_order(gift_order)["status"], "redeemed")


if __name__ == "__main__":
    unittest.main()
