import tempfile
import unittest
from pathlib import Path

from zankode import storage


class DatabaseSmokeTest(unittest.TestCase):
    def test_schema_initializes_and_passes_integrity_checks(self):
        old_path = storage.DB_PATH
        try:
            with tempfile.TemporaryDirectory() as tmp:
                storage.DB_PATH = Path(tmp) / "config_shop.db"
                storage.init_db()
                storage.database_integrity_check()
                with storage.db() as conn:
                    users = conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
                    ).fetchone()
                    self.assertIsNotNone(users)
        finally:
            storage.DB_PATH = old_path

    def test_completed_purchase_keeps_exact_buyer_and_plan_mapping(self):
        old_path = storage.DB_PATH
        try:
            with tempfile.TemporaryDirectory() as tmp:
                storage.DB_PATH = Path(tmp) / "config_shop.db"
                storage.init_db()
                with storage.db() as conn:
                    conn.execute(
                        "INSERT INTO users(user_id,username,full_name,created_at,last_seen) VALUES(?,?,?,?,?)",
                        (101, "buyer101", "Buyer One", storage.now(), storage.now())
                    )
                    plan = conn.execute("SELECT * FROM plans ORDER BY id LIMIT 1").fetchone()
                oid = storage.create_order(
                    101,
                    plan,
                    storage.iran_now(),
                    "test",
                )
                storage.update_status(oid, storage.COMPLETED, completed=True)
                orders = storage.buyer_orders(101, 0)
                self.assertEqual(len(orders), 1)
                self.assertEqual(orders[0]["user_id"], 101)
                self.assertEqual(orders[0]["plan_title"], plan["title"])
                buyers = storage.buyer_rows(0)
                self.assertEqual(buyers[0]["user_id"], 101)
                self.assertEqual(buyers[0]["purchase_count"], 1)
        finally:
            storage.DB_PATH = old_path

    def test_crash_interrupted_gift_redemption_is_recovered_for_same_recipient(self):
        old_path = storage.DB_PATH
        try:
            with tempfile.TemporaryDirectory() as tmp:
                storage.DB_PATH = Path(tmp) / "config_shop.db"
                storage.init_db()
                with storage.db() as conn:
                    n = storage.now()
                    conn.executemany(
                        "INSERT INTO users(user_id,username,full_name,created_at,last_seen) VALUES(?,?,?,?,?)",
                        [
                            (201, "buyer", "Buyer", n, n),
                            (202, "recipient", "Recipient", n, n),
                        ],
                    )
                    plan = conn.execute("SELECT * FROM plans ORDER BY id LIMIT 1").fetchone()
                oid = storage.create_order(201, plan, storage.iran_now(), "test", is_gift=True)
                with storage.db() as conn:
                    conn.execute(
                        "UPDATE orders SET status=?,delivered_config=?,completed_at=?,updated_at=? WHERE id=?",
                        (storage.COMPLETED, "vless://gift", storage.now(), storage.now(), oid),
                    )
                code = storage.ensure_gift_code(oid)
                reserved = storage.reserve_gift_redeem(202, code)
                self.assertIsNotNone(reserved)
                recovered = storage.recover_incomplete_gift_redemptions()
                self.assertEqual(recovered, 1)
                gift = storage.gift_for_order(oid)
                self.assertEqual(gift["status"], "redeemed")
                self.assertEqual(gift["recipient_user_id"], 202)
                self.assertEqual(len(storage.received_gifts(202)), 1)
        finally:
            storage.DB_PATH = old_path

    def test_old_default_brand_migrates_without_overwriting_custom_name(self):
        old_path = storage.DB_PATH
        try:
            with tempfile.TemporaryDirectory() as tmp:
                storage.DB_PATH = Path(tmp) / "config_shop.db"
                storage.init_db()
                storage.set_setting("shop_name", "ZabKode VPN")
                storage.init_db()
                self.assertEqual(storage.setting("shop_name"), "Zankode VPN")
                storage.set_setting("shop_name", "My Custom Shop")
                storage.init_db()
                self.assertEqual(storage.setting("shop_name"), "My Custom Shop")
        finally:
            storage.DB_PATH = old_path


if __name__ == "__main__":
    unittest.main()
