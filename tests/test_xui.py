import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import httpx
from telegram.error import TelegramError

from zankode import storage, services
from zankode.xui import XUIClient, XUISettings, XUIProvisionedClient


class XUIAdapterTest(unittest.IsolatedAsyncioTestCase):
    async def test_modern_create_client_uses_bearer_and_reads_back(self):
        seen = {}

        def handler(request: httpx.Request):
            seen.setdefault("requests", []).append(request)
            if request.url.path.endswith("/panel/api/clients/add"):
                body = json.loads(request.content.decode())
                seen["add_body"] = body
                self.assertEqual(request.headers.get("authorization"), "Bearer secret-token")
                return httpx.Response(200, json={"success": True, "obj": None})
            if "/panel/api/clients/get/" in request.url.path:
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

    def __init__(self):
        self.configured = True

    def subscription_url(self, sub_id, email=""):
        return f"https://sub.example/sub/{sub_id}"

    async def delivery_credential(self, sub_id, email=""):
        return self.subscription_url(sub_id, email)

    async def create_client(self, **kwargs):
        type(self).create_calls += 1
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
            c.execute(
                "INSERT INTO users(user_id,username,full_name,is_blocked,created_at,last_seen) VALUES(100,'tester','Tester',0,?,?)",
                (storage.now(), storage.now()),
            )
            c.execute(
                "INSERT INTO plans(title,price,description,duration_days,provision_mode,xui_inbound_ids,xui_traffic_gb,xui_ip_limit,is_active,created_at,updated_at) "
                "VALUES('XUI 50GB',100000,'xui',30,'xui','1,2',50,2,1,?,?)",
                (storage.now(), storage.now()),
            )
        self.old_client_cls = services.XUIClient
        services.XUIClient = _FakeXUI
        _FakeXUI.create_calls = 0

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


if __name__ == "__main__":
    unittest.main()
