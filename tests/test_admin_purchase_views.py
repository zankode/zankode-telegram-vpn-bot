import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from zankode import storage
from zankode.handlers import admin_views


class AdminPurchaseViewTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self._old_db_path = storage.DB_PATH
        self._tmp = tempfile.TemporaryDirectory()
        storage.DB_PATH = Path(self._tmp.name) / "config_shop.db"
        storage.init_db()

        class User:
            id = 777
            username = "ali"
            full_name = "Ali Buyer"

        storage.upsert_user(User())
        with storage.db() as conn:
            self.plan = conn.execute("SELECT * FROM plans ORDER BY id LIMIT 1").fetchone()
        self.oid = storage.create_order(777, self.plan, storage.iran_now(), "test")
        storage.update_status(self.oid, storage.COMPLETED, completed=True)

    async def asyncTearDown(self):
        storage.DB_PATH = self._old_db_path
        self._tmp.cleanup()

    async def test_user_profile_shows_recent_purchase_and_all_purchases_button(self):
        edit_mock = AsyncMock()
        with patch.object(admin_views, "edit", edit_mock):
            await admin_views.render_user(object(), 777)

        _, text, keyboard = edit_mock.await_args.args
        self.assertIn("۳ خرید موفق اخیر", text)
        self.assertIn(self.plan["title"], text)
        labels = [button.text for row in keyboard.inline_keyboard for button in row]
        self.assertIn("🛒 همه خریدهای این کاربر", labels)

    async def test_order_list_identifies_buyer_and_plan_without_opening_order(self):
        edit_mock = AsyncMock()
        with patch.object(admin_views, "edit", edit_mock):
            await admin_views.render_orders(object(), storage.COMPLETED, 0, "سفارش‌ها")

        _, _, keyboard = edit_mock.await_args.args
        labels = [button.text for row in keyboard.inline_keyboard for button in row]
        self.assertTrue(
            any("Ali Buyer" in label and self.plan["title"][:10] in label for label in labels)
        )


if __name__ == "__main__":
    unittest.main()
