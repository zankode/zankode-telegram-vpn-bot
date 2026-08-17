import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

from telegram.error import TelegramError

from zankode import services, storage


class _FakeBot:
    def __init__(self, fail_first=False):
        self.fail_first = fail_first
        self.calls = 0
        self.messages = []
        self.documents = []

    async def _maybe_fail(self):
        self.calls += 1
        if self.fail_first and self.calls == 1:
            raise TelegramError("simulated Telegram failure")

    async def send_message(self, *args, **kwargs):
        await self._maybe_fail()
        self.messages.append((args, kwargs))
        return object()

    async def send_document(self, *args, **kwargs):
        await self._maybe_fail()
        self.documents.append((args, kwargs))
        return object()


class ServiceReliabilityTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self._old_db_path = storage.DB_PATH
        self._tmp = tempfile.TemporaryDirectory()
        storage.DB_PATH = Path(self._tmp.name) / "config_shop.db"
        storage.init_db()

        class User:
            id = 501
            username = "buyer501"
            full_name = "Buyer 501"

        storage.upsert_user(User())
        with storage.db() as conn:
            self.plan = conn.execute("SELECT * FROM plans ORDER BY id LIMIT 1").fetchone()

    async def asyncTearDown(self):
        storage.DB_PATH = self._old_db_path
        self._tmp.cleanup()

    async def test_low_stock_failure_is_retried_instead_of_suppressed(self):
        pid = int(self.plan["id"])
        with self.assertLogs("zankode-vpn", level="WARNING"):
            await services.check_low_stock(_FakeBot(fail_first=True), pid)
        with storage.db() as conn:
            alert = conn.execute(
                "SELECT * FROM stock_alerts WHERE plan_id=?", (pid,)
            ).fetchone()
        self.assertIsNone(alert)

        await services.check_low_stock(_FakeBot(), pid)
        with storage.db() as conn:
            alert = conn.execute(
                "SELECT * FROM stock_alerts WHERE plan_id=?", (pid,)
            ).fetchone()
        self.assertIsNotNone(alert)

    async def test_expiry_marker_is_written_only_after_successful_notification(self):
        oid = storage.create_order(501, self.plan, storage.iran_now(), "test")
        storage.update_status(oid, storage.COMPLETED, completed=True)
        with storage.db() as conn:
            conn.execute(
                "UPDATE orders SET expires_at=?,expired_notified_at=NULL,expiry_warned_at=NULL WHERE id=?",
                (storage.db_dt(storage.iran_now() - timedelta(days=1)), oid),
            )

        with self.assertLogs("zankode-vpn", level="WARNING"):
            await services.process_expiry_notifications(_FakeBot(fail_first=True))
        with storage.db() as conn:
            row = conn.execute(
                "SELECT expired_notified_at FROM orders WHERE id=?", (oid,)
            ).fetchone()
        self.assertIsNone(row["expired_notified_at"])

        await services.process_expiry_notifications(_FakeBot())
        with storage.db() as conn:
            row = conn.execute(
                "SELECT expired_notified_at FROM orders WHERE id=?", (oid,)
            ).fetchone()
        self.assertIsNotNone(row["expired_notified_at"])

    async def test_long_config_uses_single_document_delivery(self):
        oid = storage.create_order(501, self.plan, storage.iran_now(), "test")
        bot = _FakeBot()
        config = "x" * 5000
        ok = await services.send_config(
            SimpleNamespace(bot=bot), 501, oid, self.plan["title"], config
        )
        self.assertTrue(ok)
        self.assertEqual(len(bot.documents), 1)
        self.assertEqual(len(bot.messages), 1)  # final confirmation only
        with storage.db() as conn:
            row = conn.execute(
                "SELECT delivered_config FROM orders WHERE id=?", (oid,)
            ).fetchone()
        self.assertEqual(row["delivered_config"], config)

    async def test_failed_config_delivery_does_not_mark_order_delivered(self):
        oid = storage.create_order(501, self.plan, storage.iran_now(), "test")
        with self.assertLogs("zankode-vpn", level="ERROR"):
            ok = await services.send_config(
                SimpleNamespace(bot=_FakeBot(fail_first=True)),
                501,
                oid,
                self.plan["title"],
                "vless://example",
            )
        self.assertFalse(ok)
        with storage.db() as conn:
            row = conn.execute(
                "SELECT delivered_config FROM orders WHERE id=?", (oid,)
            ).fetchone()
        self.assertIsNone(row["delivered_config"])


if __name__ == "__main__":
    unittest.main()
