import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from zankode import storage


class V221ReliabilityTest(unittest.TestCase):
    def setUp(self):
        self.old_db = storage.DB_PATH
        self.tmp = tempfile.TemporaryDirectory()
        storage.DB_PATH = Path(self.tmp.name) / "v221.db"
        storage.init_db()

        class Buyer:
            id = 9001
            username = "buyer9001"
            full_name = "Buyer 9001"

        class Recipient:
            id = 9002
            username = "recipient9002"
            full_name = "Recipient 9002"

        storage.upsert_user(Buyer())
        storage.upsert_user(Recipient())
        self.plan = storage.active_plans()[0]

    def tearDown(self):
        storage.DB_PATH = self.old_db
        self.tmp.cleanup()

    def test_pending_order_does_not_start_service_clock(self):
        oid = storage.create_order(9001, self.plan)
        row = storage.get_order(oid)
        self.assertIsNone(row["purchased_at"])
        self.assertIsNone(row["service_activated_at"])
        self.assertIsNone(row["expires_at"])
        self.assertEqual(int(row["service_root_order_id"]), oid)

    def test_plan_technical_snapshot_is_frozen_at_order_creation(self):
        with storage.db() as c:
            c.execute(
                "UPDATE plans SET provision_mode='xui',xui_inbound_ids='7,8',xui_traffic_gb=77,xui_ip_limit=3 WHERE id=?",
                (self.plan["id"],),
            )
        current = storage.get_plan(int(self.plan["id"]))
        oid = storage.create_order(9001, current)
        with storage.db() as c:
            c.execute(
                "UPDATE plans SET provision_mode='inventory',xui_inbound_ids='',xui_traffic_gb=1,xui_ip_limit=1 WHERE id=?",
                (self.plan["id"],),
            )
        order = storage.get_order(oid)
        self.assertEqual(storage.order_provision_mode(order), "xui")
        self.assertEqual(storage.order_xui_inbound_ids(order), [7, 8])
        self.assertEqual(storage.order_xui_traffic_gb(order), 77)
        self.assertEqual(storage.order_xui_ip_limit(order), 3)

    def test_delivery_starts_validity_and_xui_renewal_extends_one_root_service(self):
        with storage.db() as c:
            c.execute("UPDATE plans SET provision_mode='xui',xui_inbound_ids='1' WHERE id=?", (self.plan["id"],))
        plan = storage.get_plan(int(self.plan["id"]))
        root_id = storage.create_order(9001, plan)
        storage.update_status(root_id, storage.APPROVED, approved=True)
        storage.mark_order_paid(root_id)
        self.assertTrue(storage.finalize_service_delivery(root_id, "vless://root", owner_uid=9001))
        root_before = storage.get_order(root_id)
        first_expiry = storage.parse_db_dt(root_before["expires_at"])
        self.assertIsNotNone(first_expiry)

        renewal_id = storage.create_order(9001, plan, renew_parent_order_id=root_id)
        storage.update_status(renewal_id, storage.APPROVED, approved=True)
        storage.mark_order_paid(renewal_id)
        _, target_expiry = storage.prepare_service_activation(renewal_id, owner_uid=9001)
        self.assertGreater(target_expiry, first_expiry)
        self.assertTrue(storage.finalize_service_delivery(renewal_id, "vless://root", owner_uid=9001))

        root_after = storage.get_order(root_id)
        renewal = storage.get_order(renewal_id)
        self.assertEqual(int(renewal["service_root_order_id"]), root_id)
        self.assertEqual(root_after["expires_at"], renewal["expires_at"])
        self.assertEqual(len(storage.delivered_services(9001)), 1)
        self.assertEqual(storage.account_stats(9001)["delivered"], 1)

    def test_repeated_activation_preparation_is_idempotent(self):
        with storage.db() as c:
            c.execute("UPDATE plans SET provision_mode='xui',xui_inbound_ids='1' WHERE id=?", (self.plan["id"],))
        plan = storage.get_plan(int(self.plan["id"]))
        root_id = storage.create_order(9001, plan)
        storage.update_status(root_id, storage.APPROVED, approved=True)
        storage.finalize_service_delivery(root_id, "vless://root", owner_uid=9001)
        renewal_id = storage.create_order(9001, plan, renew_parent_order_id=root_id)
        storage.update_status(renewal_id, storage.APPROVED, approved=True)
        first = storage.prepare_service_activation(renewal_id, owner_uid=9001)
        second = storage.prepare_service_activation(renewal_id, owner_uid=9001)
        self.assertEqual(first, second)

    def test_inventory_renewal_is_a_new_credential_service_not_a_fake_extension(self):
        root_id = storage.create_order(9001, self.plan)
        storage.update_status(root_id, storage.APPROVED, approved=True)
        storage.finalize_service_delivery(root_id, "vless://old", owner_uid=9001)
        old_expiry = storage.get_order(root_id)["expires_at"]

        renewal_id = storage.create_order(9001, self.plan, renew_parent_order_id=root_id)
        storage.update_status(renewal_id, storage.APPROVED, approved=True)
        storage.finalize_service_delivery(renewal_id, "vless://new", owner_uid=9001)
        renewal = storage.get_order(renewal_id)
        self.assertEqual(int(renewal["service_root_order_id"]), renewal_id)
        self.assertEqual(storage.get_order(root_id)["expires_at"], old_expiry)
        self.assertEqual(len(storage.delivered_services(9001)), 2)

    def test_gift_validity_starts_at_redemption_and_owner_becomes_recipient(self):
        gift_order = storage.create_order(9001, self.plan, is_gift=True)
        with storage.db() as c:
            paid = storage.now()
            c.execute(
                "UPDATE orders SET status=?,approved_at=?,purchased_at=?,completed_at=?,delivered_config=?,updated_at=? WHERE id=?",
                (storage.COMPLETED, paid, paid, paid, "vless://gift", paid, gift_order),
            )
        code = storage.ensure_gift_code(gift_order)
        before = storage.get_order(gift_order)
        self.assertIsNone(before["expires_at"])
        reserved = storage.reserve_gift_redeem(9002, code)
        self.assertIsNotNone(reserved)
        storage.finalize_service_delivery(gift_order, "vless://gift", owner_uid=9002)
        storage.finish_gift_redeem(int(reserved["id"]), True)
        after = storage.get_order(gift_order)
        self.assertEqual(int(after["service_owner_user_id"]), 9002)
        self.assertIsNotNone(after["service_activated_at"])
        self.assertIsNotNone(after["expires_at"])
        self.assertEqual(len(storage.received_gifts(9002)), 1)

    def test_xui_dashboard_has_one_row_per_service_root_after_renewal(self):
        with storage.db() as c:
            c.execute("UPDATE plans SET provision_mode='xui',xui_inbound_ids='1' WHERE id=?", (self.plan["id"],))
        plan = storage.get_plan(int(self.plan["id"]))
        root_id = storage.create_order(9001, plan)
        renewal_id = storage.create_order(9001, plan, renew_parent_order_id=root_id)
        storage.upsert_xui_service(
            root_id, 9001, int(self.plan["id"]), "zk_9001_1", "uuid", "sub", [1],
            1000, 1800000000000, 1, used_bytes=250,
        )
        # Calling through the renewal must resolve to the same canonical root.
        svc = storage.xui_service_for_order(renewal_id)
        self.assertIsNotNone(svc)
        self.assertEqual(int(svc["order_id"]), root_id)
        metrics = storage.xui_dashboard_metrics()
        self.assertEqual(metrics["total"], 1)
        self.assertEqual(metrics["used_bytes"], 250)

    def test_v220_migration_collapses_renewal_xui_rows_into_canonical_root(self):
        with storage.db() as c:
            c.execute("UPDATE plans SET provision_mode='xui',xui_inbound_ids='1' WHERE id=?", (self.plan["id"],))
        plan = storage.get_plan(int(self.plan["id"]))
        root_id = storage.create_order(9001, plan)
        renewal_id = storage.create_order(9001, plan, renew_parent_order_id=root_id)

        # Simulate the v2.2.0 shape: no service root/snapshot migration yet and
        # one local XUI row recorded for each renewal transaction.
        with storage.db() as c:
            c.execute("DELETE FROM settings WHERE key='migration_v221_order_snapshots'")
            c.execute("UPDATE orders SET service_root_order_id=NULL,provision_mode_snapshot='inventory'")
        storage.upsert_xui_service(
            root_id, 9001, int(self.plan["id"]), "zk_9001_root", "uuid-a", "sub-a", [1],
            1000, 1800000000000, 1, used_bytes=100,
        )
        storage.upsert_xui_service(
            renewal_id, 9001, int(self.plan["id"]), "zk_9001_root", "uuid-a", "sub-a", [1],
            1000, 1801000000000, 1, used_bytes=200,
        )

        storage.init_db()

        renewal = storage.get_order(renewal_id)
        self.assertEqual(storage.order_provision_mode(renewal), "xui")
        self.assertEqual(int(renewal["service_root_order_id"]), root_id)
        with storage.db() as c:
            rows = c.execute("SELECT order_id,last_used_bytes FROM xui_services ORDER BY order_id").fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(int(rows[0]["order_id"]), root_id)
        self.assertEqual(int(rows[0]["last_used_bytes"]), 200)


if __name__ == "__main__":
    unittest.main()
