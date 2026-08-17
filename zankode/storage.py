# -*- coding: utf-8 -*-
"""SQLite schema, migrations, repositories, and transactional domain operations."""

from .config import *
from .utils import *


class _ManagedSQLiteConnection(sqlite3.Connection):
    """Commit/rollback like sqlite3.Connection, then actually close after `with`."""

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


def db() -> sqlite3.Connection:
    c = sqlite3.connect(DB_PATH, timeout=20, factory=_ManagedSQLiteConnection)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    c.execute("PRAGMA busy_timeout=20000")
    c.execute("PRAGMA synchronous=FULL")
    c.execute("PRAGMA secure_delete=ON")
    c.execute("PRAGMA temp_store=MEMORY")
    return c

def ensure_column(c: sqlite3.Connection, table: str, column: str, ddl: str):
    cols = {r["name"] for r in c.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in cols:
        c.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")

def init_db():
    with db() as c:
        c.execute("PRAGMA journal_mode=WAL")
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users(
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT NOT NULL,
            is_blocked INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            last_seen TEXT NOT NULL,
            test_review_required INTEGER NOT NULL DEFAULT 0,
            test_review_reason TEXT,
            wallet_balance INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS settings(
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS plans(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            price INTEGER NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            duration_days INTEGER NOT NULL DEFAULT 30,
            provision_mode TEXT NOT NULL DEFAULT 'inventory',
            xui_inbound_ids TEXT NOT NULL DEFAULT '',
            xui_traffic_gb INTEGER NOT NULL DEFAULT 0,
            xui_ip_limit INTEGER NOT NULL DEFAULT 1,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS inventory(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id INTEGER NOT NULL,
            config_text TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'available',
            order_id INTEGER,
            created_at TEXT NOT NULL,
            used_at TEXT,
            FOREIGN KEY(plan_id) REFERENCES plans(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS coupons(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE COLLATE NOCASE,
            kind TEXT NOT NULL,
            value INTEGER NOT NULL,
            max_uses INTEGER NOT NULL DEFAULT 0,
            used_count INTEGER NOT NULL DEFAULT 0,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS coupon_uses(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            coupon_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            order_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(coupon_id,user_id),
            FOREIGN KEY(coupon_id) REFERENCES coupons(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS orders(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            plan_id INTEGER,
            plan_title TEXT NOT NULL,
            base_amount INTEGER NOT NULL,
            discount_amount INTEGER NOT NULL DEFAULT 0,
            final_amount INTEGER NOT NULL,
            coupon_code TEXT,
            status TEXT NOT NULL,
            receipt_file_id TEXT,
            rejection_reason TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            approved_at TEXT,
            completed_at TEXT,
            duration_days INTEGER NOT NULL DEFAULT 30,
            purchased_at TEXT,
            expires_at TEXT,
            time_source TEXT,
            renew_parent_order_id INTEGER,
            expiry_warned_at TEXT,
            expired_notified_at TEXT,
            receipt_unique_id TEXT,
            delivered_config TEXT,
            is_gift INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        );
        CREATE TABLE IF NOT EXISTS tickets(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            closed_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        );
        CREATE TABLE IF NOT EXISTS actions(
            user_id INTEGER PRIMARY KEY,
            action TEXT NOT NULL,
            payload TEXT,
            created_ts INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS audit(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            actor_id INTEGER,
            action TEXT NOT NULL,
            details TEXT,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS referrals(
            referred_user_id INTEGER PRIMARY KEY,
            referrer_user_id INTEGER NOT NULL,
            joined_at TEXT NOT NULL,
            qualified_at TEXT,
            FOREIGN KEY(referred_user_id) REFERENCES users(user_id),
            FOREIGN KEY(referrer_user_id) REFERENCES users(user_id)
        );
        CREATE TABLE IF NOT EXISTS referral_rewards(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_user_id INTEGER NOT NULL,
            milestone INTEGER NOT NULL,
            coupon_code TEXT NOT NULL UNIQUE COLLATE NOCASE,
            created_at TEXT NOT NULL,
            used_at TEXT,
            UNIQUE(owner_user_id, milestone),
            FOREIGN KEY(owner_user_id) REFERENCES users(user_id)
        );
        CREATE TABLE IF NOT EXISTS referral_commissions(
            order_id INTEGER PRIMARY KEY,
            referrer_user_id INTEGER NOT NULL,
            referred_user_id INTEGER NOT NULL,
            purchase_amount INTEGER NOT NULL,
            commission_amount INTEGER NOT NULL,
            buyer_bonus_amount INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY(order_id) REFERENCES orders(id),
            FOREIGN KEY(referrer_user_id) REFERENCES users(user_id),
            FOREIGN KEY(referred_user_id) REFERENCES users(user_id)
        );
        CREATE TABLE IF NOT EXISTS stock_alerts(
            plan_id INTEGER PRIMARY KEY,
            last_level INTEGER NOT NULL,
            alerted_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS test_inventory(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            config_text TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'available',
            claimed_by INTEGER,
            created_at TEXT NOT NULL,
            claimed_at TEXT,
            FOREIGN KEY(claimed_by) REFERENCES users(user_id)
        );
        CREATE TABLE IF NOT EXISTS test_claims(
            user_id INTEGER PRIMARY KEY,
            inventory_id INTEGER NOT NULL,
            config_text TEXT NOT NULL,
            claimed_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(user_id),
            FOREIGN KEY(inventory_id) REFERENCES test_inventory(id)
        );
        CREATE TABLE IF NOT EXISTS user_notes(
            user_id INTEGER PRIMARY KEY,
            note TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS test_reviews(
            user_id INTEGER PRIMARY KEY,
            status TEXT NOT NULL DEFAULT 'pending',
            reason TEXT,
            requested_at TEXT NOT NULL,
            reviewed_at TEXT,
            reviewed_by INTEGER,
            FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS wallet_transactions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            tx_type TEXT NOT NULL,
            reference_type TEXT,
            reference_id INTEGER,
            note TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS wallet_topups(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'awaiting_receipt',
            receipt_file_id TEXT,
            receipt_unique_id TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            approved_at TEXT,
            rejection_reason TEXT,
            FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS gift_codes(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL UNIQUE,
            buyer_user_id INTEGER NOT NULL,
            code TEXT NOT NULL UNIQUE COLLATE NOCASE,
            status TEXT NOT NULL DEFAULT 'active',
            recipient_user_id INTEGER,
            created_at TEXT NOT NULL,
            redeemed_at TEXT,
            FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE,
            FOREIGN KEY(buyer_user_id) REFERENCES users(user_id),
            FOREIGN KEY(recipient_user_id) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS xui_services(
            order_id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            plan_id INTEGER,
            client_email TEXT NOT NULL,
            client_uuid TEXT,
            sub_id TEXT,
            inbound_ids TEXT NOT NULL DEFAULT '',
            total_bytes INTEGER NOT NULL DEFAULT 0,
            expiry_ms INTEGER NOT NULL DEFAULT 0,
            ip_limit INTEGER NOT NULL DEFAULT 0,
            remote_status TEXT NOT NULL DEFAULT 'active',
            last_used_bytes INTEGER NOT NULL DEFAULT 0,
            last_sync_at TEXT,
            last_error TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE,
            FOREIGN KEY(user_id) REFERENCES users(user_id),
            FOREIGN KEY(plan_id) REFERENCES plans(id)
        );
        CREATE INDEX IF NOT EXISTS idx_xui_services_user ON xui_services(user_id,updated_at);
        CREATE INDEX IF NOT EXISTS idx_xui_services_email ON xui_services(client_email);

        CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
        CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id);
        CREATE INDEX IF NOT EXISTS idx_stock ON inventory(plan_id,status);
        CREATE INDEX IF NOT EXISTS idx_tickets ON tickets(status);
        CREATE INDEX IF NOT EXISTS idx_referrals_referrer ON referrals(referrer_user_id);
        CREATE INDEX IF NOT EXISTS idx_referral_rewards_owner ON referral_rewards(owner_user_id);
        CREATE INDEX IF NOT EXISTS idx_referral_commissions_referrer ON referral_commissions(referrer_user_id,created_at);
        CREATE INDEX IF NOT EXISTS idx_referral_commissions_referred ON referral_commissions(referred_user_id,created_at);
        """)

        # Safe migrations for existing config_shop.db
        ensure_column(c, "plans", "duration_days", "INTEGER NOT NULL DEFAULT 30")
        ensure_column(c, "plans", "provision_mode", "TEXT NOT NULL DEFAULT 'inventory'")
        ensure_column(c, "plans", "xui_inbound_ids", "TEXT NOT NULL DEFAULT ''")
        ensure_column(c, "plans", "xui_traffic_gb", "INTEGER NOT NULL DEFAULT 0")
        ensure_column(c, "plans", "xui_ip_limit", "INTEGER NOT NULL DEFAULT 1")
        ensure_column(c, "orders", "duration_days", "INTEGER NOT NULL DEFAULT 30")
        ensure_column(c, "orders", "purchased_at", "TEXT")
        ensure_column(c, "orders", "expires_at", "TEXT")
        ensure_column(c, "orders", "time_source", "TEXT")
        ensure_column(c, "orders", "renew_parent_order_id", "INTEGER")
        ensure_column(c, "orders", "expiry_warned_at", "TEXT")
        ensure_column(c, "orders", "expired_notified_at", "TEXT")
        ensure_column(c, "orders", "receipt_unique_id", "TEXT")
        ensure_column(c, "orders", "delivered_config", "TEXT")
        ensure_column(c, "users", "test_review_required", "INTEGER NOT NULL DEFAULT 0")
        ensure_column(c, "users", "test_review_reason", "TEXT")
        ensure_column(c, "users", "wallet_balance", "INTEGER NOT NULL DEFAULT 0")
        ensure_column(c, "orders", "is_gift", "INTEGER NOT NULL DEFAULT 0")
        c.execute("CREATE INDEX IF NOT EXISTS idx_orders_expiry ON orders(status,expires_at)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_wallet_tx_user ON wallet_transactions(user_id,created_at)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_wallet_topup_status ON wallet_topups(status,created_at)")
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_wallet_topup_receipt ON wallet_topups(receipt_unique_id) WHERE receipt_unique_id IS NOT NULL")
        c.execute("CREATE INDEX IF NOT EXISTS idx_gift_status ON gift_codes(status,created_at)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_receipt_unique ON orders(receipt_unique_id)")

        duplicate_receipts = c.execute(
            "SELECT receipt_unique_id,MIN(id) keep_id FROM orders "
            "WHERE receipt_unique_id IS NOT NULL AND receipt_unique_id<>'' "
            "GROUP BY receipt_unique_id HAVING COUNT(*)>1"
        ).fetchall()
        for d in duplicate_receipts:
            c.execute(
                "UPDATE orders SET receipt_unique_id=NULL "
                "WHERE receipt_unique_id=? AND id<>?",
                (d["receipt_unique_id"], d["keep_id"])
            )
        c.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_orders_receipt_unique "
            "ON orders(receipt_unique_id) WHERE receipt_unique_id IS NOT NULL"
        )

        c.execute(
            "DELETE FROM inventory WHERE status='available' AND id NOT IN ("
            "SELECT MIN(id) FROM inventory WHERE status='available' GROUP BY plan_id,config_text"
            ")"
        )
        c.execute(
            "DELETE FROM test_inventory WHERE status='available' AND id NOT IN ("
            "SELECT MIN(id) FROM test_inventory WHERE status='available' GROUP BY config_text"
            ")"
        )

        for k, v in DEFAULTS.items():
            c.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)", (k, v))
        c.execute(
            "UPDATE settings SET value='Zankode VPN' "
            "WHERE key='shop_name' AND value IN ('⚡ فروشگاه کانفیگ','ZabKode VPN')"
        )
        c.execute(
            "UPDATE settings SET value=? WHERE key='welcome_text' AND value=?",
            (
                'لطفاً سرویس مدنظرتون رو انتخاب کنید، پس از پرداخت و ارسال فیش، سفارش شما سریعاً بررسی و تحویل داده میشه 🚀',
                'سرویس رو انتخاب کن، پرداخت کن و فیش رو بفرست؛ نتیجه همینجا اعلام می‌شه.'
            )
        )

        if c.execute("SELECT COUNT(*) FROM plans").fetchone()[0] == 0:
            n = now()
            c.executemany(
                "INSERT INTO plans(title,price,description,duration_days,created_at,updated_at) VALUES(?,?,?,?,?,?)",
                [
                    ("پلن اقتصادی ۱ ماهه", 100000, "۳۰ روز اعتبار • مناسب مصرف روزمره", 30, n, n),
                    ("پلن حرفه‌ای ۲ ماهه", 180000, "۶۰ روز اعتبار • اقتصادی‌تر", 60, n, n),
                    ("پلن ویژه ۳ ماهه", 250000, "۹۰ روز اعتبار • پیشنهاد محبوب", 90, n, n),
                ],
            )

        # Backfill known old plans.
        c.execute(
            "UPDATE plans SET duration_days=60 WHERE duration_days=30 "
            "AND (title LIKE '%۲ ماه%' OR title LIKE '%2 ماه%' OR description LIKE '%۶۰ روز%' OR description LIKE '%60 روز%')"
        )
        c.execute(
            "UPDATE plans SET duration_days=90 WHERE duration_days=30 "
            "AND (title LIKE '%۳ ماه%' OR title LIKE '%3 ماه%' OR description LIKE '%۹۰ روز%' OR description LIKE '%90 روز%')"
        )
        c.execute(
            "UPDATE orders SET duration_days=COALESCE((SELECT duration_days FROM plans WHERE plans.id=orders.plan_id),30) "
            "WHERE duration_days IS NULL OR duration_days<=0"
        )

        # Recover configs for legacy orders that were fulfilled from automatic inventory.
        c.execute(
            "UPDATE orders SET delivered_config=("
            "SELECT inventory.config_text FROM inventory "
            "WHERE inventory.order_id=orders.id "
            "ORDER BY inventory.id DESC LIMIT 1"
            ") WHERE delivered_config IS NULL AND EXISTS("
            "SELECT 1 FROM inventory WHERE inventory.order_id=orders.id"
            ")"
        )

        old_rows = c.execute(
            "SELECT id,created_at,duration_days FROM orders WHERE purchased_at IS NULL"
        ).fetchall()
        for row in old_rows:
            pdt = parse_db_dt(row["created_at"])
            if not pdt:
                continue
            exp = pdt + timedelta(days=max(1, int(row["duration_days"] or 30)))
            c.execute(
                "UPDATE orders SET purchased_at=?,expires_at=?,time_source=? WHERE id=?",
                (db_dt(pdt), db_dt(exp), "legacy", row["id"])
            )

    try:
        if os.name != "nt":
            for path in (DB_PATH, Path(str(DB_PATH) + "-wal"), Path(str(DB_PATH) + "-shm")):
                if path.exists():
                    os.chmod(path, 0o600)
    except OSError:
        pass

def database_integrity_check():
    with db() as c:
        quick = c.execute("PRAGMA quick_check").fetchone()[0]
        if str(quick).lower() != "ok":
            raise RuntimeError(f"SQLite quick_check failed: {quick}")
        fk_errors = c.execute("PRAGMA foreign_key_check").fetchall()
        if fk_errors:
            raise RuntimeError(f"SQLite foreign_key_check failed: {len(fk_errors)} issue(s)")

def audit(actor: Optional[int], action: str, details: str = ""):
    with db() as c:
        c.execute(
            "INSERT INTO audit(actor_id,action,details,created_at) VALUES(?,?,?,?)",
            (actor, action[:100], details[:1000], now())
        )

def setting(k: str, default: str = "") -> str:
    with db() as c:
        r = c.execute("SELECT value FROM settings WHERE key=?", (k,)).fetchone()
    return r["value"] if r else default

def set_setting(k: str, v: str):
    with db() as c:
        c.execute(
            "INSERT INTO settings(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (k, v)
        )

def setting_on(k: str) -> bool:
    return setting(k, "0") == "1"

def upsert_user(u):
    if not u:
        return
    with db() as c:
        c.execute("""
            INSERT INTO users(user_id,username,full_name,created_at,last_seen)
            VALUES(?,?,?,?,?)
            ON CONFLICT(user_id) DO UPDATE SET
                username=excluded.username,
                full_name=excluded.full_name,
                last_seen=excluded.last_seen
        """, (u.id, u.username or "", u.full_name or str(u.id), now(), now()))

def get_user(uid: int):
    with db() as c:
        return c.execute("SELECT * FROM users WHERE user_id=?", (uid,)).fetchone()

def blocked(uid: int) -> bool:
    r = get_user(uid)
    return bool(r and r["is_blocked"])

def set_block(uid: int, value: bool):
    with db() as c:
        c.execute("UPDATE users SET is_blocked=? WHERE user_id=?", (1 if value else 0, uid))

def find_user(q: str):
    q = q.strip()
    with db() as c:
        if q.startswith("@"):
            return c.execute("SELECT * FROM users WHERE username=? COLLATE NOCASE", (q[1:],)).fetchone()
        n = to_int(q)
        if n is not None:
            return c.execute("SELECT * FROM users WHERE user_id=?", (n,)).fetchone()
        return c.execute(
            "SELECT * FROM users WHERE full_name LIKE ? OR username LIKE ? COLLATE NOCASE "
            "ORDER BY last_seen DESC LIMIT 1",
            (f"%{q}%", f"%{q}%")
        ).fetchone()

def get_user_note(uid: int) -> str:
    with db() as c:
        row = c.execute(
            "SELECT note FROM user_notes WHERE user_id=?",
            (uid,)
        ).fetchone()
    return str(row["note"]) if row else ""

def set_user_note(uid: int, note: str):
    note = str(note or "").strip()[:1200]
    with db() as c:
        if not note:
            c.execute("DELETE FROM user_notes WHERE user_id=?", (uid,))
            return
        c.execute(
            "INSERT INTO user_notes(user_id,note,updated_at) VALUES(?,?,?) "
            "ON CONFLICT(user_id) DO UPDATE SET note=excluded.note,updated_at=excluded.updated_at",
            (uid, note, now())
        )

def set_test_review_required(uid: int, required: bool, reason: str = ""):
    with db() as c:
        c.execute(
            "UPDATE users SET test_review_required=?,test_review_reason=? WHERE user_id=?",
            (1 if required else 0, reason.strip()[:500] if required else None, uid)
        )

def get_test_review(uid: int):
    with db() as c:
        return c.execute(
            "SELECT * FROM test_reviews WHERE user_id=?",
            (uid,)
        ).fetchone()

def pending_test_review_count() -> int:
    with db() as c:
        return int(c.execute(
            "SELECT COUNT(*) FROM test_reviews WHERE status='pending'"
        ).fetchone()[0])

def pending_test_reviews(page: int, per_page: int = 10):
    off = max(0, page) * per_page
    with db() as c:
        return c.execute(
            "SELECT tr.*,u.full_name,u.username "
            "FROM test_reviews tr JOIN users u ON u.user_id=tr.user_id "
            "WHERE tr.status='pending' ORDER BY tr.requested_at ASC "
            "LIMIT ? OFFSET ?",
            (per_page + 1, off)
        ).fetchall()

def ensure_test_review(uid: int, reason: str) -> bool:
    with db() as c:
        old = c.execute(
            "SELECT status FROM test_reviews WHERE user_id=?",
            (uid,)
        ).fetchone()
        if old and old["status"] == "pending":
            return False
        c.execute(
            "INSERT INTO test_reviews(user_id,status,reason,requested_at,reviewed_at,reviewed_by) "
            "VALUES(?,'pending',?,?,NULL,NULL) "
            "ON CONFLICT(user_id) DO UPDATE SET "
            "status='pending',reason=excluded.reason,requested_at=excluded.requested_at,"
            "reviewed_at=NULL,reviewed_by=NULL",
            (uid, reason[:500], now())
        )
        return True

def finish_test_review(uid: int, status: str, reviewer: int):
    with db() as c:
        c.execute(
            "UPDATE test_reviews SET status=?,reviewed_at=?,reviewed_by=? WHERE user_id=?",
            (status, now(), reviewer, uid)
        )

def reset_test_review(uid: int):
    with db() as c:
        c.execute("DELETE FROM test_reviews WHERE user_id=?", (uid,))

def _normalized_person_name(value: str) -> str:
    return " ".join(str(value or "").strip().casefold().split())

def automatic_test_risk_reason(uid: int) -> str:
    """
    Conservative heuristic: never auto-rejects; only sends to manual review.
    Device ID/IP is not available here, so false positives must stay review-only.
    """
    u = get_user(uid)
    if not u:
        return ""

    if int(u["test_review_required"] or 0):
        return str(u["test_review_reason"] or "علامت‌گذاری دستی ادمین برای بررسی تست")

    name = _normalized_person_name(u["full_name"])
    if len(name) < 6 or " " not in name:
        return ""

    with db() as c:
        claimed = c.execute(
            "SELECT u.user_id,u.full_name FROM test_claims tc "
            "JOIN users u ON u.user_id=tc.user_id "
            "WHERE u.user_id<>? ORDER BY tc.claimed_at DESC LIMIT 500",
            (uid,)
        ).fetchall()
        pending = c.execute(
            "SELECT u.user_id,u.full_name FROM test_reviews tr "
            "JOIN users u ON u.user_id=tr.user_id "
            "WHERE tr.status='pending' AND u.user_id<>? LIMIT 200",
            (uid,)
        ).fetchall()

    for row in list(claimed) + list(pending):
        if _normalized_person_name(row["full_name"]) == name:
            return (
                "نام نمایشی این حساب با حساب دیگری که قبلاً تست گرفته "
                "یا در صف بررسی تست است یکسان است."
            )
    return ""

def wallet_balance(uid: int) -> int:
    with db() as c:
        row = c.execute("SELECT wallet_balance FROM users WHERE user_id=?", (uid,)).fetchone()
    return int(row["wallet_balance"] or 0) if row else 0

def wallet_transactions(uid: int, limit: int = 12):
    with db() as c:
        return c.execute(
            "SELECT * FROM wallet_transactions WHERE user_id=? ORDER BY id DESC LIMIT ?",
            (uid, max(1, min(limit, 50)))
        ).fetchall()

def change_wallet(
    uid: int,
    amount: int,
    tx_type: str,
    *,
    reference_type: str = "",
    reference_id: Optional[int] = None,
    note: str = "",
    allow_negative: bool = False,
) -> tuple[bool, int]:
    amount = int(amount)
    c = db()
    try:
        c.execute("BEGIN IMMEDIATE")
        row = c.execute("SELECT wallet_balance FROM users WHERE user_id=?", (uid,)).fetchone()
        if not row:
            c.rollback()
            return False, 0
        old = int(row["wallet_balance"] or 0)
        new = old + amount
        if new < 0 and not allow_negative:
            c.rollback()
            return False, old
        c.execute("UPDATE users SET wallet_balance=? WHERE user_id=?", (new, uid))
        c.execute(
            "INSERT INTO wallet_transactions(user_id,amount,tx_type,reference_type,reference_id,note,created_at) "
            "VALUES(?,?,?,?,?,?,?)",
            (uid, amount, tx_type[:50], reference_type[:50], reference_id, note[:500], now())
        )
        c.commit()
        return True, new
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()

def create_wallet_topup(uid: int, amount: int) -> int:
    n = now()
    with db() as c:
        cur = c.execute(
            "INSERT INTO wallet_topups(user_id,amount,status,created_at,updated_at) VALUES(?,?, 'awaiting_receipt', ?, ?)",
            (uid, int(amount), n, n)
        )
        return int(cur.lastrowid)

def open_wallet_topup(uid: int):
    with db() as c:
        return c.execute(
            "SELECT * FROM wallet_topups WHERE user_id=? AND status IN ('awaiting_receipt','awaiting_admin') ORDER BY id DESC LIMIT 1",
            (uid,)
        ).fetchone()

def wallet_topup_open_count(uid: int) -> int:
    with db() as c:
        return int(c.execute(
            "SELECT COUNT(*) FROM wallet_topups WHERE user_id=? AND status IN ('awaiting_receipt','awaiting_admin')",
            (uid,)
        ).fetchone()[0])

def get_wallet_topup(tid: int):
    with db() as c:
        return c.execute(
            "SELECT wt.*,u.full_name,u.username FROM wallet_topups wt "
            "JOIN users u ON u.user_id=wt.user_id WHERE wt.id=?", (tid,)
        ).fetchone()

def pending_wallet_topups(page: int = 0, per_page: int = 10):
    off = max(0, page) * per_page
    with db() as c:
        return c.execute(
            "SELECT wt.*,u.full_name,u.username FROM wallet_topups wt "
            "JOIN users u ON u.user_id=wt.user_id WHERE wt.status='awaiting_admin' "
            "ORDER BY wt.id LIMIT ? OFFSET ?", (per_page + 1, off)
        ).fetchall()

def approve_wallet_topup(tid: int, actor: int) -> tuple[bool, Optional[sqlite3.Row], int]:
    c = db()
    try:
        c.execute("BEGIN IMMEDIATE")
        top = c.execute("SELECT * FROM wallet_topups WHERE id=?", (tid,)).fetchone()
        if not top or top["status"] != "awaiting_admin" or not top["receipt_file_id"]:
            c.rollback()
            return False, top, 0
        uid, amount = int(top["user_id"]), int(top["amount"])
        row = c.execute("SELECT wallet_balance FROM users WHERE user_id=?", (uid,)).fetchone()
        if not row:
            c.rollback()
            return False, top, 0
        new = int(row["wallet_balance"] or 0) + amount
        c.execute("UPDATE users SET wallet_balance=? WHERE user_id=?", (new, uid))
        c.execute(
            "INSERT INTO wallet_transactions(user_id,amount,tx_type,reference_type,reference_id,note,created_at) "
            "VALUES(?,?,?,?,?,?,?)",
            (uid, amount, "topup", "wallet_topup", tid, f"تأیید شارژ توسط ادمین {actor}", now())
        )
        c.execute(
            "UPDATE wallet_topups SET status='approved',approved_at=?,updated_at=? WHERE id=? AND status='awaiting_admin'",
            (now(), now(), tid)
        )
        c.commit()
        return True, top, new
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()

def reject_wallet_topup(tid: int, reason: str) -> bool:
    with db() as c:
        cur = c.execute(
            "UPDATE wallet_topups SET status='rejected',rejection_reason=?,updated_at=? "
            "WHERE id=? AND status='awaiting_admin'",
            (reason[:500], now(), tid)
        )
        return cur.rowcount == 1

def vip_tier(uid: int) -> tuple[str, int, int]:
    with db() as c:
        n = int(c.execute(
            "SELECT COUNT(*) FROM orders WHERE user_id=? AND status=?", (uid, COMPLETED)
        ).fetchone()[0])
    vip_min = max(1, to_int(setting("vip_min_purchases", "8")) or 8)
    special_min = max(1, to_int(setting("special_min_purchases", "4")) or 4)
    if n >= vip_min:
        return "👑 VIP", n, vip_min
    if n >= special_min:
        return "💎 ویژه", n, vip_min
    if n >= 1:
        return "🟢 مشتری", n, special_min
    return "🌱 تازه‌وارد", n, 1

def vip_progress_text(uid: int) -> str:
    tier, purchases, next_goal = vip_tier(uid)
    if tier.startswith("👑"):
        return f"{tier}\n✅ شما در بالاترین سطح باشگاه هستید.\n🛒 خریدهای موفق: {purchases}"
    left = max(0, next_goal - purchases)
    return f"{tier}\n🛒 خرید موفق: {purchases}\n🎯 تا سطح بعدی: {left} خرید"

def generate_gift_code() -> str:
    for _ in range(20):
        code = "ZKG-" + secrets.token_hex(8).upper()
        with db() as c:
            if not c.execute("SELECT 1 FROM gift_codes WHERE code=?", (code,)).fetchone():
                return code
    raise RuntimeError("gift code generation failed")

def ensure_gift_code(oid: int) -> str:
    o = get_order(oid)
    if not o:
        raise ValueError("order not found")
    with db() as c:
        old = c.execute("SELECT code FROM gift_codes WHERE order_id=?", (oid,)).fetchone()
        if old:
            return str(old["code"])
    code = generate_gift_code()
    with db() as c:
        c.execute(
            "INSERT INTO gift_codes(order_id,buyer_user_id,code,status,created_at) VALUES(?,?,?,'active',?)",
            (oid, int(o["user_id"]), code, now())
        )
    return code

def gift_for_order(oid: int):
    with db() as c:
        return c.execute("SELECT * FROM gift_codes WHERE order_id=?", (oid,)).fetchone()

def reserve_gift_redeem(uid: int, code: str):
    c = db()
    try:
        c.execute("BEGIN IMMEDIATE")
        g = c.execute(
            "SELECT g.*,o.delivered_config,o.plan_title,o.status order_status "
            "FROM gift_codes g JOIN orders o ON o.id=g.order_id "
            "WHERE g.code=? COLLATE NOCASE", (code.strip(),)
        ).fetchone()
        if not g or g["status"] != "active" or g["order_status"] != COMPLETED or not g["delivered_config"]:
            c.rollback()
            return None
        cur = c.execute(
            "UPDATE gift_codes SET status='redeeming',recipient_user_id=? WHERE id=? AND status='active'",
            (uid, g["id"])
        )
        if cur.rowcount != 1:
            c.rollback()
            return None
        c.commit()
        return g
    except Exception:
        c.rollback(); raise
    finally:
        c.close()

def finish_gift_redeem(gid: int, success: bool):
    with db() as c:
        if success:
            c.execute(
                "UPDATE gift_codes SET status='redeemed',redeemed_at=? WHERE id=? AND status='redeeming'",
                (now(), gid)
            )
        else:
            c.execute(
                "UPDATE gift_codes SET status='active',recipient_user_id=NULL WHERE id=? AND status='redeeming'",
                (gid,)
            )

def recover_incomplete_gift_redemptions() -> int:
    """Finalize crash-interrupted gift claims for the already reserved recipient."""
    with db() as c:
        cur = c.execute(
            "UPDATE gift_codes SET status='redeemed',redeemed_at=COALESCE(redeemed_at,?) "
            "WHERE status='redeeming' AND recipient_user_id IS NOT NULL",
            (now(),)
        )
        return int(cur.rowcount or 0)


def received_gifts(uid: int):
    with db() as c:
        return c.execute(
            "SELECT g.*,o.plan_title,o.expires_at,o.delivered_config,o.id order_id "
            "FROM gift_codes g JOIN orders o ON o.id=g.order_id "
            "WHERE g.recipient_user_id=? AND g.status='redeemed' ORDER BY g.redeemed_at DESC",
            (uid,)
        ).fetchall()

def received_gift(gid: int, uid: int):
    with db() as c:
        return c.execute(
            "SELECT g.*,o.plan_title,o.expires_at,o.delivered_config,o.id order_id "
            "FROM gift_codes g JOIN orders o ON o.id=g.order_id "
            "WHERE g.id=? AND g.recipient_user_id=? AND g.status='redeemed'",
            (gid,uid)
        ).fetchone()

def segment_user_ids(segment: str) -> list[int]:
    lost_days = max(1, to_int(setting("lost_customer_days", "60")) or 60)
    cutoff_lost = db_dt(iran_now() - timedelta(days=lost_days))
    soon = db_dt(iran_now() + timedelta(days=3))
    n = now()
    with db() as c:
        if segment == "all":
            rows = c.execute("SELECT user_id FROM users WHERE is_blocked=0").fetchall()
        elif segment == "buyers":
            rows = c.execute(
                "SELECT DISTINCT u.user_id FROM users u JOIN orders o ON o.user_id=u.user_id "
                "WHERE u.is_blocked=0 AND o.status=?", (COMPLETED,)
            ).fetchall()
        elif segment == "no_purchase":
            rows = c.execute(
                "SELECT u.user_id FROM users u WHERE u.is_blocked=0 AND NOT EXISTS("
                "SELECT 1 FROM orders o WHERE o.user_id=u.user_id AND o.status=?)", (COMPLETED,)
            ).fetchall()
        elif segment == "active":
            rows = c.execute(
                "SELECT DISTINCT u.user_id FROM users u JOIN orders o ON o.user_id=u.user_id "
                "WHERE u.is_blocked=0 AND o.status=? AND o.expires_at>?", (COMPLETED, n)
            ).fetchall()
        elif segment == "expiring3":
            rows = c.execute(
                "SELECT DISTINCT u.user_id FROM users u JOIN orders o ON o.user_id=u.user_id "
                "WHERE u.is_blocked=0 AND o.status=? AND o.expires_at>? AND o.expires_at<=?",
                (COMPLETED, n, soon)
            ).fetchall()
        elif segment == "vip":
            vip_min = max(1, to_int(setting("vip_min_purchases", "8")) or 8)
            rows = c.execute(
                "SELECT u.user_id FROM users u JOIN orders o ON o.user_id=u.user_id "
                "WHERE u.is_blocked=0 AND o.status=? GROUP BY u.user_id HAVING COUNT(o.id)>=?",
                (COMPLETED, vip_min)
            ).fetchall()
        elif segment == "loyal":
            rows = c.execute(
                "SELECT u.user_id FROM users u JOIN orders o ON o.user_id=u.user_id "
                "WHERE u.is_blocked=0 AND o.status=? GROUP BY u.user_id HAVING COUNT(o.id)>=3",
                (COMPLETED,)
            ).fetchall()
        elif segment == "lost":
            rows = c.execute(
                "SELECT u.user_id FROM users u JOIN orders o ON o.user_id=u.user_id "
                "WHERE u.is_blocked=0 AND o.status=? GROUP BY u.user_id HAVING MAX(o.completed_at)<=?",
                (COMPLETED, cutoff_lost)
            ).fetchall()
        elif segment == "suspicious":
            rows = c.execute(
                "SELECT user_id FROM users WHERE is_blocked=0 AND test_review_required=1"
            ).fetchall()
        elif segment.startswith("plan_"):
            pid = to_int(segment[5:])
            rows = c.execute(
                "SELECT DISTINCT u.user_id FROM users u JOIN orders o ON o.user_id=u.user_id "
                "WHERE u.is_blocked=0 AND o.status=? AND o.plan_id=?", (COMPLETED, pid)
            ).fetchall() if pid else []
        else:
            rows = []
    return [int(r["user_id"]) for r in rows]

def segment_rows(kind: str, page: int, per_page: int = 10):
    ids = segment_user_ids(kind)
    start = max(0, page) * per_page
    chosen = ids[start:start + per_page + 1]
    if not chosen:
        return []
    placeholders = ",".join("?" for _ in chosen)
    with db() as c:
        rows = c.execute(
            f"SELECT user_id,full_name,username FROM users WHERE user_id IN ({placeholders})",
            chosen
        ).fetchall()
    order = {uid: i for i, uid in enumerate(chosen)}
    return sorted(rows, key=lambda r: order.get(int(r["user_id"]), 99999))

def notification_counts() -> dict[str, int]:
    soon = db_dt(iran_now() + timedelta(days=3))
    n = now()
    threshold_raw = to_int(setting("low_stock_threshold", "3"))
    threshold = max(0, threshold_raw if threshold_raw is not None else 3)
    with db() as c:
        return {
            "pending_receipts": int(c.execute("SELECT COUNT(*) FROM orders WHERE status=?", (AWAIT_ADMIN,)).fetchone()[0]),
            "wallet_topups": int(c.execute("SELECT COUNT(*) FROM wallet_topups WHERE status='awaiting_admin'").fetchone()[0]),
            "test_reviews": int(c.execute("SELECT COUNT(*) FROM test_reviews WHERE status='pending'").fetchone()[0]),
            "tickets": int(c.execute("SELECT COUNT(*) FROM tickets WHERE status='open'").fetchone()[0]),
            "flagged": int(c.execute("SELECT COUNT(*) FROM users WHERE test_review_required=1").fetchone()[0]),
            "expiring": int(c.execute(
                "SELECT COUNT(*) FROM orders WHERE status=? AND expires_at>? AND expires_at<=?", (COMPLETED, n, soon)
            ).fetchone()[0]),
            "low_plans": int(c.execute(
                "SELECT COUNT(*) FROM plans p WHERE p.is_active=1 AND COALESCE(p.provision_mode,'inventory')<>'xui' AND (SELECT COUNT(*) FROM inventory i WHERE i.plan_id=p.id AND i.status='available')<=?",
                (threshold,)
            ).fetchone()[0]),
            "test_stock": int(c.execute("SELECT COUNT(*) FROM test_inventory WHERE status='available'").fetchone()[0]),
        }

def fraud_candidates(page: int, per_page: int = 10):
    off = max(0, page) * per_page
    cutoff = db_dt(iran_now() - timedelta(days=7))
    with db() as c:
        return c.execute(
            "SELECT u.user_id,u.full_name,u.username,u.test_review_required,"
            "(SELECT COUNT(*) FROM orders o WHERE o.user_id=u.user_id AND o.status=? AND o.updated_at>=?) cancelled7,"
            "(SELECT COUNT(*) FROM referrals r WHERE r.referrer_user_id=u.user_id) refs,"
            "EXISTS(SELECT 1 FROM test_reviews tr WHERE tr.user_id=u.user_id AND tr.status='pending') pending_test "
            "FROM users u WHERE u.test_review_required=1 "
            "OR EXISTS(SELECT 1 FROM test_reviews tr WHERE tr.user_id=u.user_id AND tr.status='pending') "
            "OR (SELECT COUNT(*) FROM orders o WHERE o.user_id=u.user_id AND o.status=? AND o.updated_at>=?)>=3 "
            "OR (SELECT COUNT(*) FROM referrals r WHERE r.referrer_user_id=u.user_id)>=15 "
            "ORDER BY pending_test DESC,u.test_review_required DESC,cancelled7 DESC,refs DESC "
            "LIMIT ? OFFSET ?",
            (CANCELLED, cutoff, CANCELLED, cutoff, per_page + 1, off)
        ).fetchall()

def dashboard_metrics() -> dict[str, Any]:
    n = iran_now()
    d7 = db_dt(n - timedelta(days=7))
    d30 = db_dt(n - timedelta(days=30))
    now_s = db_dt(n)
    with db() as c:
        users = int(c.execute("SELECT COUNT(*) FROM users").fetchone()[0])
        orders = int(c.execute("SELECT COUNT(*) FROM orders").fetchone()[0])
        completed = int(c.execute("SELECT COUNT(*) FROM orders WHERE status=?", (COMPLETED,)).fetchone()[0])
        revenue = int(c.execute("SELECT COALESCE(SUM(final_amount),0) FROM orders WHERE status=?", (COMPLETED,)).fetchone()[0])
        rev7 = int(c.execute("SELECT COALESCE(SUM(final_amount),0) FROM orders WHERE status=? AND completed_at>=?", (COMPLETED, d7)).fetchone()[0])
        rev30 = int(c.execute("SELECT COALESCE(SUM(final_amount),0) FROM orders WHERE status=? AND completed_at>=?", (COMPLETED, d30)).fetchone()[0])
        repeat = int(c.execute(
            "SELECT COUNT(*) FROM (SELECT user_id FROM orders WHERE status=? GROUP BY user_id HAVING COUNT(*)>=2)", (COMPLETED,)
        ).fetchone()[0])
        buyers = int(c.execute("SELECT COUNT(DISTINCT user_id) FROM orders WHERE status=?", (COMPLETED,)).fetchone()[0])
        active = int(c.execute("SELECT COUNT(*) FROM orders WHERE status=? AND expires_at>?", (COMPLETED, now_s)).fetchone()[0])
        renewals = int(c.execute("SELECT COUNT(*) FROM orders WHERE status=? AND renew_parent_order_id IS NOT NULL", (COMPLETED,)).fetchone()[0])
        wallet_total = int(c.execute("SELECT COALESCE(SUM(wallet_balance),0) FROM users").fetchone()[0])
        top = c.execute(
            "SELECT plan_title,COUNT(*) n FROM orders WHERE status=? GROUP BY plan_title ORDER BY n DESC LIMIT 1", (COMPLETED,)
        ).fetchone()
    conversion = (completed / orders * 100.0) if orders else 0.0
    return {
        "users": users, "orders": orders, "completed": completed, "revenue": revenue,
        "rev7": rev7, "rev30": rev30, "repeat": repeat, "buyers": buyers,
        "active": active, "renewals": renewals, "wallet_total": wallet_total,
        "conversion": conversion, "top": f"{top['plan_title']} ({top['n']})" if top else "—",
    }

def global_search(term: str) -> dict[str, list[Any]]:
    term = term.strip()
    out: dict[str, list[Any]] = {"users": [], "orders": [], "coupons": [], "configs": []}
    if not term:
        return out
    n = to_int(term.lstrip("#"))
    with db() as c:
        if n is not None:
            u = c.execute("SELECT * FROM users WHERE user_id=?", (n,)).fetchone()
            if u: out["users"].append(u)
            o = c.execute("SELECT * FROM orders WHERE id=?", (n,)).fetchone()
            if o: out["orders"].append(o)
        if term.startswith("@"):
            rows = c.execute("SELECT * FROM users WHERE username=? COLLATE NOCASE LIMIT 5", (term[1:],)).fetchall()
        else:
            like = f"%{term[:100]}%"
            rows = c.execute(
                "SELECT * FROM users WHERE full_name LIKE ? OR username LIKE ? COLLATE NOCASE LIMIT 5", (like, like)
            ).fetchall()
        for r in rows:
            if not any(int(x["user_id"]) == int(r["user_id"]) for x in out["users"]): out["users"].append(r)
        cps = c.execute("SELECT * FROM coupons WHERE code LIKE ? COLLATE NOCASE LIMIT 5", (f"%{term}%",)).fetchall()
        out["coupons"].extend(cps)
    if len(term) >= 4:
        out["configs"] = search_config_records(term, limit=5)
    return out

def set_action(uid: int, action: str, payload: str = ""):
    with db() as c:
        c.execute("""
            INSERT INTO actions(user_id,action,payload,created_ts) VALUES(?,?,?,?)
            ON CONFLICT(user_id) DO UPDATE SET
                action=excluded.action,payload=excluded.payload,created_ts=excluded.created_ts
        """, (uid, action, payload, ts()))

def clear_action(uid: int):
    with db() as c:
        c.execute("DELETE FROM actions WHERE user_id=?", (uid,))

def get_action(uid: int):
    with db() as c:
        r = c.execute("SELECT * FROM actions WHERE user_id=?", (uid,)).fetchone()
    if r and ts() - int(r["created_ts"]) > ACTION_TTL:
        clear_action(uid)
        return None
    return r

def active_plans():
    with db() as c:
        return c.execute("SELECT * FROM plans WHERE is_active=1 ORDER BY id").fetchall()

def all_plans():
    with db() as c:
        return c.execute("SELECT * FROM plans ORDER BY id").fetchall()

def get_plan(pid: int):
    with db() as c:
        return c.execute("SELECT * FROM plans WHERE id=?", (pid,)).fetchone()

def parse_inbound_ids(value: str) -> list[int]:
    out: list[int] = []
    for part in str(value or "").replace(";", ",").split(","):
        n = to_int(part.strip())
        if n is not None and n > 0 and n not in out:
            out.append(n)
    return out[:50]

def plan_is_xui(plan) -> bool:
    return bool(plan and str(plan["provision_mode"] or "inventory").lower() == "xui")

def xui_service_for_order(oid: int):
    with db() as c:
        return c.execute("SELECT * FROM xui_services WHERE order_id=?", (oid,)).fetchone()

def xui_parent_service(oid: int):
    with db() as c:
        return c.execute(
            "SELECT xs.* FROM orders o JOIN xui_services xs ON xs.order_id=o.renew_parent_order_id "
            "WHERE o.id=? AND o.renew_parent_order_id IS NOT NULL",
            (oid,)
        ).fetchone()

def upsert_xui_service(
    oid: int, uid: int, plan_id: Optional[int], client_email: str, client_uuid: str,
    sub_id: str, inbound_ids: list[int], total_bytes: int, expiry_ms: int, ip_limit: int,
    *, remote_status: str = "active", used_bytes: int = 0, last_error: str = ""
):
    n = now()
    inbound_text = ",".join(str(int(x)) for x in inbound_ids if int(x) > 0)
    with db() as c:
        c.execute(
            """INSERT INTO xui_services(
                order_id,user_id,plan_id,client_email,client_uuid,sub_id,inbound_ids,total_bytes,
                expiry_ms,ip_limit,remote_status,last_used_bytes,last_sync_at,last_error,created_at,updated_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(order_id) DO UPDATE SET
                client_email=excluded.client_email,client_uuid=excluded.client_uuid,sub_id=excluded.sub_id,
                inbound_ids=excluded.inbound_ids,total_bytes=excluded.total_bytes,expiry_ms=excluded.expiry_ms,
                ip_limit=excluded.ip_limit,remote_status=excluded.remote_status,
                last_used_bytes=excluded.last_used_bytes,last_sync_at=excluded.last_sync_at,
                last_error=excluded.last_error,updated_at=excluded.updated_at""",
            (oid,uid,plan_id,client_email,client_uuid,sub_id,inbound_text,int(total_bytes),int(expiry_ms),
             int(ip_limit),remote_status,int(used_bytes),n,last_error[:500],n,n)
        )

def update_xui_service_sync(oid: int, *, total_bytes: int, expiry_ms: int, ip_limit: int, used_bytes: int, enabled: bool, last_error: str = ""):
    with db() as c:
        c.execute(
            "UPDATE xui_services SET total_bytes=?,expiry_ms=?,ip_limit=?,last_used_bytes=?,remote_status=?,last_sync_at=?,last_error=?,updated_at=? WHERE order_id=?",
            (int(total_bytes),int(expiry_ms),int(ip_limit),int(used_bytes),"active" if enabled else "disabled",now(),last_error[:500],now(),oid)
        )

def xui_services_for_user(uid: int):
    with db() as c:
        return c.execute(
            "SELECT xs.*,o.plan_title,o.status,o.expires_at FROM xui_services xs JOIN orders o ON o.id=xs.order_id "
            "WHERE xs.user_id=? ORDER BY xs.order_id DESC LIMIT 30", (uid,)
        ).fetchall()

def xui_dashboard_metrics() -> dict[str, int]:
    with db() as c:
        total = int(c.execute("SELECT COUNT(*) FROM xui_services").fetchone()[0])
        active = int(c.execute("SELECT COUNT(*) FROM xui_services WHERE remote_status='active'").fetchone()[0])
        disabled = int(c.execute("SELECT COUNT(*) FROM xui_services WHERE remote_status='disabled'").fetchone()[0])
        errors = int(c.execute("SELECT COUNT(*) FROM xui_services WHERE last_error IS NOT NULL AND last_error<>''").fetchone()[0])
        traffic = int(c.execute("SELECT COALESCE(SUM(last_used_bytes),0) FROM xui_services").fetchone()[0])
    return {"total": total, "active": active, "disabled": disabled, "errors": errors, "used_bytes": traffic}

def stock_count(pid: int) -> int:
    with db() as c:
        return c.execute(
            "SELECT COUNT(*) FROM inventory WHERE plan_id=? AND status='available'", (pid,)
        ).fetchone()[0]

def add_stock(pid: int, configs: list[str]) -> int:
    clean = list(dict.fromkeys(x.strip() for x in configs if x.strip()))[:500]
    if not clean:
        return 0

    added = 0
    with db() as c:
        for cfg in clean:
            exists = c.execute(
                "SELECT 1 FROM inventory WHERE config_text=? LIMIT 1",
                (cfg,)
            ).fetchone()
            if exists:
                continue
            c.execute(
                "INSERT INTO inventory(plan_id,config_text,status,created_at) "
                "VALUES(?,?,'available',?)",
                (pid, cfg, now())
            )
            added += 1
    return added

def pop_stock(pid: int, oid: int) -> Optional[str]:
    """Atomically reserve one config. Mark used only after successful Telegram delivery."""
    c = db()
    try:
        c.execute("BEGIN IMMEDIATE")
        r = c.execute(
            "SELECT id,config_text FROM inventory "
            "WHERE plan_id=? AND status='available' ORDER BY id LIMIT 1",
            (pid,)
        ).fetchone()
        if not r:
            c.rollback()
            return None

        cur = c.execute(
            "UPDATE inventory SET status='reserved',order_id=?,used_at=? "
            "WHERE id=? AND status='available'",
            (oid, now(), r["id"])
        )
        if cur.rowcount != 1:
            c.rollback()
            return None

        c.commit()
        return r["config_text"]
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()

def commit_stock_for_order(oid: int):
    with db() as c:
        c.execute(
            "UPDATE inventory SET status='used',used_at=? "
            "WHERE order_id=? AND status='reserved'",
            (now(), oid)
        )

def release_stock_for_order(oid: int):
    """
    Release only a genuinely undelivered reservation.
    Completed orders or orders with delivered_config must never make their
    credential available for sale again.
    """
    with db() as c:
        c.execute(
            "UPDATE inventory SET status='available',order_id=NULL,used_at=NULL "
            "WHERE order_id=? AND status='reserved' "
            "AND NOT EXISTS("
            "SELECT 1 FROM orders o WHERE o.id=? "
            "AND (o.status=? OR COALESCE(o.delivered_config,'')<>'')"
            ")",
            (oid, oid, COMPLETED)
        )

def recover_stale_reservations():
    cutoff = db_dt(iran_now() - timedelta(minutes=RESERVATION_STALE_MINUTES))
    with db() as c:
        rows = c.execute(
            "SELECT i.id,i.order_id,i.used_at,o.status,o.delivered_config "
            "FROM inventory i LEFT JOIN orders o ON o.id=i.order_id "
            "WHERE i.status='reserved' AND (i.used_at IS NULL OR i.used_at<=?)",
            (cutoff,)
        ).fetchall()

        for r in rows:
            if r["order_id"] and r["delivered_config"]:
                c.execute(
                    "UPDATE inventory SET status='used',used_at=? WHERE id=?",
                    (now(), r["id"])
                )
                if r["status"] == APPROVED:
                    c.execute(
                        "UPDATE orders SET status=?,completed_at=COALESCE(completed_at,?),updated_at=? "
                        "WHERE id=? AND status=?",
                        (COMPLETED, now(), now(), r["order_id"], APPROVED)
                    )
            elif r["order_id"] and r["status"] == COMPLETED:
                c.execute(
                    "UPDATE inventory SET status='used',used_at=? WHERE id=?",
                    (now(), r["id"])
                )
            else:
                c.execute(
                    "UPDATE inventory SET status='available',order_id=NULL,used_at=NULL WHERE id=?",
                    (r["id"],)
                )

def test_stock_count() -> int:
    with db() as c:
        return int(c.execute(
            "SELECT COUNT(*) FROM test_inventory WHERE status='available'"
        ).fetchone()[0])

def add_test_stock(configs: list[str]) -> int:
    clean = list(dict.fromkeys(x.strip() for x in configs if x.strip()))[:500]
    if not clean:
        return 0

    added = 0
    with db() as c:
        for cfg in clean:
            exists = c.execute(
                "SELECT 1 FROM test_inventory WHERE config_text=? LIMIT 1",
                (cfg,)
            ).fetchone()
            if exists:
                continue
            c.execute(
                "INSERT INTO test_inventory(config_text,status,created_at) "
                "VALUES(?,'available',?)",
                (cfg, now())
            )
            added += 1
    return added

def clear_test_stock() -> int:
    with db() as c:
        n = int(c.execute(
            "SELECT COUNT(*) FROM test_inventory WHERE status='available'"
        ).fetchone()[0])
        c.execute("DELETE FROM test_inventory WHERE status='available'")
        return n

def test_referral_count(uid: int) -> int:
    """Distinct, non-blocked referrals that are at least N hours old."""
    cutoff = db_dt(iran_now() - timedelta(hours=TEST_REFERRAL_MATURITY_HOURS))
    with db() as c:
        return int(c.execute(
            "SELECT COUNT(DISTINCT r.referred_user_id) "
            "FROM referrals r JOIN users u ON u.user_id=r.referred_user_id "
            "WHERE r.referrer_user_id=? AND r.joined_at<=? AND u.is_blocked=0",
            (uid, cutoff)
        ).fetchone()[0])

def get_test_claim(uid: int):
    with db() as c:
        return c.execute(
            "SELECT * FROM test_claims WHERE user_id=?",
            (uid,)
        ).fetchone()

def pop_test_stock_for_user(uid: int) -> Optional[str]:
    """
    Issue a free test immediately. No referral or purchase is required.
    Permanent limit: one free test per Telegram user ID.
    """
    c = db()
    try:
        c.execute("BEGIN IMMEDIATE")

        old = c.execute(
            "SELECT config_text FROM test_claims WHERE user_id=?",
            (uid,)
        ).fetchone()
        if old:
            c.rollback()
            return old["config_text"]

        row = c.execute(
            "SELECT id,config_text FROM test_inventory "
            "WHERE status='available' ORDER BY id LIMIT 1"
        ).fetchone()
        if not row:
            c.rollback()
            return None

        n = now()
        cur = c.execute(
            "UPDATE test_inventory SET status='used',claimed_by=?,claimed_at=? "
            "WHERE id=? AND status='available'",
            (uid, n, row["id"])
        )
        if cur.rowcount != 1:
            c.rollback()
            return None

        c.execute(
            "INSERT INTO test_claims(user_id,inventory_id,config_text,claimed_at) "
            "VALUES(?,?,?,?)",
            (uid, row["id"], row["config_text"], n)
        )
        c.commit()
        return row["config_text"]
    except sqlite3.IntegrityError:
        c.rollback()
        old = get_test_claim(uid)
        return old["config_text"] if old else None
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()

def count_open_orders(uid: int) -> int:
    with db() as c:
        return int(c.execute(
            "SELECT COUNT(*) FROM orders WHERE user_id=? AND status IN (?,?,?)",
            (uid, AWAIT_RECEIPT, AWAIT_ADMIN, APPROVED)
        ).fetchone()[0])

def reusable_open_order(uid: int, pid: int):
    with db() as c:
        return c.execute(
            "SELECT * FROM orders WHERE user_id=? AND plan_id=? "
            "AND renew_parent_order_id IS NULL AND COALESCE(is_gift,0)=0 AND status IN (?,?,?) "
            "ORDER BY id DESC LIMIT 1",
            (uid, pid, AWAIT_RECEIPT, AWAIT_ADMIN, APPROVED)
        ).fetchone()

def inventory_available_rows(pid: int, page: int, per_page: int = 10):
    off = max(0, page) * per_page
    with db() as c:
        return c.execute(
            "SELECT id,plan_id,config_text,status,created_at "
            "FROM inventory WHERE plan_id=? AND status='available' "
            "ORDER BY id ASC LIMIT ? OFFSET ?",
            (pid, per_page + 1, off)
        ).fetchall()

def inventory_item(iid: int):
    with db() as c:
        return c.execute(
            "SELECT i.*,p.title plan_title FROM inventory i "
            "LEFT JOIN plans p ON p.id=i.plan_id WHERE i.id=?",
            (iid,)
        ).fetchone()

def delete_inventory_item(iid: int, pid: int) -> bool:
    with db() as c:
        cur = c.execute(
            "DELETE FROM inventory WHERE id=? AND plan_id=? AND status='available'",
            (iid, pid)
        )
        return cur.rowcount == 1

def test_inventory_rows(page: int, per_page: int = 10):
    off = max(0, page) * per_page
    with db() as c:
        return c.execute(
            "SELECT id,config_text,status,created_at FROM test_inventory "
            "WHERE status='available' ORDER BY id ASC LIMIT ? OFFSET ?",
            (per_page + 1, off)
        ).fetchall()

def test_inventory_item(iid: int):
    with db() as c:
        return c.execute(
            "SELECT * FROM test_inventory WHERE id=?",
            (iid,)
        ).fetchone()

def delete_test_inventory_item(iid: int) -> bool:
    with db() as c:
        cur = c.execute(
            "DELETE FROM test_inventory WHERE id=? AND status='available'",
            (iid,)
        )
        return cur.rowcount == 1

def _like_contains(value: str) -> str:
    value = str(value or "").replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{value}%"

def search_config_records(term: str, limit: int = 20) -> list[dict[str, Any]]:
    term = term.strip()
    if len(term) < 4:
        return []

    pat = _like_contains(term)
    results: list[dict[str, Any]] = []

    with db() as c:
        normal = c.execute(
            "SELECT i.id inventory_id,i.plan_id,i.config_text,i.status,i.order_id,"
            "p.title plan_title,o.user_id,u.full_name,u.username "
            "FROM inventory i "
            "LEFT JOIN plans p ON p.id=i.plan_id "
            "LEFT JOIN orders o ON o.id=i.order_id "
            "LEFT JOIN users u ON u.user_id=o.user_id "
            "WHERE i.config_text LIKE ? ESCAPE '\\' "
            "ORDER BY i.id DESC LIMIT ?",
            (pat, limit)
        ).fetchall()

        for r in normal:
            results.append({
                "kind": "normal",
                "inventory_id": int(r["inventory_id"]),
                "plan_id": int(r["plan_id"]),
                "config": r["config_text"],
                "status": r["status"],
                "order_id": r["order_id"],
                "user_id": r["user_id"],
                "full_name": r["full_name"],
                "username": r["username"],
                "plan_title": r["plan_title"],
            })

        manual = c.execute(
            "SELECT o.id order_id,o.user_id,o.plan_id,o.plan_title,o.delivered_config,"
            "u.full_name,u.username "
            "FROM orders o JOIN users u ON u.user_id=o.user_id "
            "WHERE o.status=? AND o.delivered_config LIKE ? ESCAPE '\\' "
            "AND NOT EXISTS(SELECT 1 FROM inventory i WHERE i.order_id=o.id) "
            "ORDER BY o.id DESC LIMIT ?",
            (COMPLETED, pat, limit)
        ).fetchall()

        for r in manual:
            results.append({
                "kind": "manual",
                "inventory_id": None,
                "plan_id": r["plan_id"],
                "config": r["delivered_config"],
                "status": "used",
                "order_id": int(r["order_id"]),
                "user_id": int(r["user_id"]),
                "full_name": r["full_name"],
                "username": r["username"],
                "plan_title": r["plan_title"],
            })

        tests = c.execute(
            "SELECT ti.id inventory_id,ti.config_text,ti.status,ti.claimed_by,"
            "u.full_name,u.username "
            "FROM test_inventory ti "
            "LEFT JOIN users u ON u.user_id=ti.claimed_by "
            "WHERE ti.config_text LIKE ? ESCAPE '\\' "
            "ORDER BY ti.id DESC LIMIT ?",
            (pat, limit)
        ).fetchall()

        for r in tests:
            results.append({
                "kind": "test",
                "inventory_id": int(r["inventory_id"]),
                "plan_id": None,
                "config": r["config_text"],
                "status": r["status"],
                "order_id": None,
                "user_id": r["claimed_by"],
                "full_name": r["full_name"],
                "username": r["username"],
                "plan_title": "Test 50MB",
            })

    return results[:limit]

def plan_detailed_stats(pid: int):
    with db() as c:
        return c.execute(
            "SELECT p.id,p.title,p.price,p.duration_days,"
            "(SELECT COUNT(*) FROM inventory i WHERE i.plan_id=p.id AND i.status='available') available_n,"
            "(SELECT COUNT(*) FROM inventory i WHERE i.plan_id=p.id AND i.status='reserved') reserved_n,"
            "(SELECT COUNT(*) FROM inventory i WHERE i.plan_id=p.id AND i.status='used') used_n,"
            "(SELECT COUNT(*) FROM orders o WHERE o.plan_id=p.id AND o.status=?) completed_n,"
            "(SELECT COUNT(DISTINCT o.user_id) FROM orders o WHERE o.plan_id=p.id AND o.status=?) buyers_n,"
            "(SELECT COALESCE(SUM(o.final_amount),0) FROM orders o WHERE o.plan_id=p.id AND o.status=?) revenue,"
            "(SELECT COUNT(*) FROM orders o WHERE o.plan_id=p.id AND o.status=? AND o.renew_parent_order_id IS NOT NULL) renewals_n,"
            "(SELECT MAX(o.completed_at) FROM orders o WHERE o.plan_id=p.id AND o.status=?) last_sale "
            "FROM plans p WHERE p.id=?",
            (COMPLETED, COMPLETED, COMPLETED, COMPLETED, COMPLETED, pid)
        ).fetchone()

def delivery_history_rows(page: int, per_page: int = 10):
    """Normal delivered services, newest first."""
    off = max(0, page) * per_page
    with db() as c:
        return c.execute(
            "SELECT o.id order_id,o.user_id,o.plan_id,o.plan_title,o.delivered_config,"
            "o.completed_at,o.updated_at,u.full_name,u.username,"
            "EXISTS(SELECT 1 FROM inventory i WHERE i.order_id=o.id AND i.status='used') auto_delivery "
            "FROM orders o JOIN users u ON u.user_id=o.user_id "
            "WHERE o.status=? AND o.delivered_config IS NOT NULL AND o.delivered_config<>'' "
            "ORDER BY COALESCE(o.completed_at,o.updated_at) DESC,o.id DESC "
            "LIMIT ? OFFSET ?",
            (COMPLETED, per_page + 1, off)
        ).fetchall()

def delivery_history_item(oid: int):
    with db() as c:
        return c.execute(
            "SELECT o.id order_id,o.user_id,o.plan_id,o.plan_title,o.delivered_config,"
            "o.completed_at,o.updated_at,o.final_amount,u.full_name,u.username,"
            "EXISTS(SELECT 1 FROM inventory i WHERE i.order_id=o.id AND i.status='used') auto_delivery "
            "FROM orders o JOIN users u ON u.user_id=o.user_id "
            "WHERE o.id=? AND o.status=? AND o.delivered_config IS NOT NULL AND o.delivered_config<>''",
            (oid, COMPLETED)
        ).fetchone()

def test_delivery_history_rows(page: int, per_page: int = 10):
    """Issued test accounts, newest first."""
    off = max(0, page) * per_page
    with db() as c:
        return c.execute(
            "SELECT tc.user_id,tc.inventory_id,tc.config_text,tc.claimed_at,"
            "u.full_name,u.username "
            "FROM test_claims tc JOIN users u ON u.user_id=tc.user_id "
            "ORDER BY tc.claimed_at DESC,tc.inventory_id DESC "
            "LIMIT ? OFFSET ?",
            (per_page + 1, off)
        ).fetchall()

def test_delivery_history_item(uid: int):
    with db() as c:
        return c.execute(
            "SELECT tc.user_id,tc.inventory_id,tc.config_text,tc.claimed_at,"
            "u.full_name,u.username "
            "FROM test_claims tc JOIN users u ON u.user_id=tc.user_id "
            "WHERE tc.user_id=?",
            (uid,)
        ).fetchone()

def buyer_rows(page: int, per_page: int = 10):
    off = max(0, page) * per_page
    with db() as c:
        return c.execute(
            "SELECT u.user_id,u.full_name,u.username,"
            "COUNT(o.id) purchase_count,COALESCE(SUM(o.final_amount),0) spent,"
            "MAX(o.completed_at) last_purchase "
            "FROM orders o JOIN users u ON u.user_id=o.user_id "
            "WHERE o.status=? "
            "GROUP BY u.user_id,u.full_name,u.username "
            "ORDER BY last_purchase DESC LIMIT ? OFFSET ?",
            (COMPLETED, per_page + 1, off)
        ).fetchall()

def buyer_orders(uid: int, page: int, per_page: int = 10):
    off = max(0, page) * per_page
    with db() as c:
        return c.execute(
            "SELECT * FROM orders WHERE user_id=? AND status=? "
            "ORDER BY completed_at DESC,id DESC LIMIT ? OFFSET ?",
            (uid, COMPLETED, per_page + 1, off)
        ).fetchall()

def create_order(
    uid: int,
    plan,
    purchase_dt: datetime,
    time_source: str,
    renew_parent_order_id: Optional[int] = None,
    is_gift: bool = False,
) -> int:
    duration = max(1, int(plan["duration_days"] or 30))
    expiry_base = purchase_dt
    if renew_parent_order_id:
        parent = get_order(renew_parent_order_id)
        parent_exp = parse_db_dt(parent["expires_at"]) if parent else None
        if parent_exp and parent_exp > expiry_base:
            expiry_base = parent_exp
    expires_dt = expiry_base + timedelta(days=duration)
    n = now()
    with db() as c:
        cur = c.execute("""
            INSERT INTO orders(
                user_id,plan_id,plan_title,base_amount,discount_amount,final_amount,
                status,created_at,updated_at,duration_days,purchased_at,expires_at,
                time_source,renew_parent_order_id,is_gift
            ) VALUES(?,?,?,?,0,?,?,?,?,?,?,?,?,?,?)
        """, (
            uid, plan["id"], plan["title"], plan["price"], plan["price"],
            AWAIT_RECEIPT, n, n, duration, db_dt(purchase_dt), db_dt(expires_dt),
            time_source, renew_parent_order_id, 1 if is_gift else 0
        ))
        return int(cur.lastrowid)

def pending_renewal(uid: int, parent_oid: int):
    with db() as c:
        return c.execute(
            "SELECT * FROM orders WHERE user_id=? AND renew_parent_order_id=? "
            "AND status IN (?,?,?) ORDER BY id DESC LIMIT 1",
            (uid, parent_oid, AWAIT_RECEIPT, AWAIT_ADMIN, APPROVED)
        ).fetchone()

def get_order(oid: int):
    with db() as c:
        return c.execute("""
            SELECT o.*,u.username,u.full_name,u.is_blocked
            FROM orders o JOIN users u ON u.user_id=o.user_id
            WHERE o.id=?
        """, (oid,)).fetchone()

def update_status(oid: int, status: str, reason: Optional[str] = None,
                  approved: bool = False, completed: bool = False):
    fields = ["status=?", "updated_at=?"]
    vals: list[Any] = [status, now()]
    if reason is not None:
        fields.append("rejection_reason=?")
        vals.append(reason)
    if approved:
        fields.append("approved_at=?")
        vals.append(now())
    if completed:
        fields.append("completed_at=?")
        vals.append(now())
    vals.append(oid)
    with db() as c:
        c.execute(f"UPDATE orders SET {','.join(fields)} WHERE id=?", vals)

def user_orders(uid: int):
    with db() as c:
        return c.execute(
            "SELECT * FROM orders WHERE user_id=? ORDER BY id DESC LIMIT 15", (uid,)
        ).fetchall()

def account_stats(uid: int) -> dict[str, Any]:
    with db() as c:
        total_orders = c.execute(
            "SELECT COUNT(*) FROM orders WHERE user_id=?", (uid,)
        ).fetchone()[0]
        successful = c.execute(
            "SELECT COUNT(*) FROM orders WHERE user_id=? AND status=?",
            (uid, COMPLETED)
        ).fetchone()[0]
        delivered = c.execute(
            "SELECT COUNT(*) FROM orders WHERE user_id=? AND status=? AND expires_at IS NOT NULL AND expires_at>?",
            (uid, COMPLETED, now())
        ).fetchone()[0]
        pending = c.execute(
            "SELECT COUNT(*) FROM orders WHERE user_id=? AND status IN (?,?,?)",
            (uid, AWAIT_RECEIPT, AWAIT_ADMIN, APPROVED)
        ).fetchone()[0]
        spent = c.execute(
            "SELECT COALESCE(SUM(final_amount),0) FROM orders WHERE user_id=? AND status=?",
            (uid, COMPLETED)
        ).fetchone()[0]
        last_order = c.execute(
            "SELECT * FROM orders WHERE user_id=? ORDER BY id DESC LIMIT 1", (uid,)
        ).fetchone()
    return {
        "total_orders": int(total_orders),
        "successful": int(successful),
        "delivered": int(delivered),
        "pending": int(pending),
        "spent": int(spent or 0),
        "last_order": last_order,
    }

def delivered_services(uid: int):
    with db() as c:
        return c.execute(
            "SELECT * FROM orders WHERE user_id=? AND status=? "
            "ORDER BY COALESCE(expires_at,completed_at) DESC, id DESC LIMIT 20",
            (uid, COMPLETED)
        ).fetchall()

def service_remaining_days(o) -> int:
    exp = parse_db_dt(o["expires_at"])
    if not exp:
        return 0
    seconds = (exp - iran_now()).total_seconds()
    if seconds <= 0:
        return 0
    return max(1, int((seconds + 86399) // 86400))

def service_state(o) -> str:
    exp = parse_db_dt(o["expires_at"])
    if not exp:
        return "تحویل‌شده"
    return "فعال ✅" if exp > iran_now() else "منقضی ⛔"

def customer_level(successful: int) -> str:
    if successful >= 8:
        return "👑 مشتری VIP"
    if successful >= 4:
        return "💎 مشتری ویژه"
    if successful >= 1:
        return "🟢 مشتری"
    return "🌱 تازه‌وارد"

def list_orders(status: Optional[str], page: int):
    off = max(0, page) * PAGE_SIZE
    with db() as c:
        if status is None:
            return c.execute("""
                SELECT o.*,u.full_name,u.username FROM orders o
                JOIN users u ON u.user_id=o.user_id
                ORDER BY o.id DESC LIMIT ? OFFSET ?
            """, (PAGE_SIZE + 1, off)).fetchall()
        return c.execute("""
            SELECT o.*,u.full_name,u.username FROM orders o
            JOIN users u ON u.user_id=o.user_id
            WHERE o.status=? ORDER BY o.id DESC LIMIT ? OFFSET ?
        """, (status, PAGE_SIZE + 1, off)).fetchall()

def register_referral(referred_uid: int, referrer_uid: int) -> bool:
    """
    Register referrals only for new users. Each user can have one referrer,
    and self-referrals are rejected.
    """
    if referred_uid == referrer_uid:
        return False
    referrer = get_user(referrer_uid)
    if not referrer or referrer["is_blocked"]:
        return False
    try:
        with db() as c:
            c.execute(
                "INSERT INTO referrals(referred_user_id,referrer_user_id,joined_at) VALUES(?,?,?)",
                (referred_uid, referrer_uid, now())
            )
        audit(referred_uid, "referral_join", f"referrer={referrer_uid}")
        return True
    except sqlite3.IntegrityError:
        return False

def referral_wallet_stats(uid: int) -> dict[str, int]:
    with db() as c:
        invited = int(c.execute(
            "SELECT COUNT(*) FROM referrals WHERE referrer_user_id=?",
            (uid,)
        ).fetchone()[0])
        buyers = int(c.execute(
            "SELECT COUNT(DISTINCT referred_user_id) FROM referral_commissions "
            "WHERE referrer_user_id=?",
            (uid,)
        ).fetchone()[0])
        orders = int(c.execute(
            "SELECT COUNT(*) FROM referral_commissions WHERE referrer_user_id=?",
            (uid,)
        ).fetchone()[0])
        earned = int(c.execute(
            "SELECT COALESCE(SUM(commission_amount),0) FROM referral_commissions "
            "WHERE referrer_user_id=?",
            (uid,)
        ).fetchone()[0])
    return {
        "invited": invited,
        "buyers": buyers,
        "orders": orders,
        "earned": earned,
    }

def apply_referral_wallet_rewards(order_id: int) -> Optional[dict[str, int]]:
    """
    Idempotent per completed order:
      - inviter gets X% of every successful referred purchase.
      - referred buyer gets a one-time wallet bonus on their first successful purchase.
    """
    c = db()
    try:
        c.execute("BEGIN IMMEDIATE")

        order = c.execute(
            "SELECT id,user_id,final_amount,status FROM orders WHERE id=?",
            (order_id,)
        ).fetchone()
        if not order or order["status"] != COMPLETED or int(order["final_amount"] or 0) <= 0:
            c.rollback()
            return None

        referred_uid = int(order["user_id"])
        rel = c.execute(
            "SELECT referrer_user_id,qualified_at FROM referrals WHERE referred_user_id=?",
            (referred_uid,)
        ).fetchone()
        if not rel:
            c.rollback()
            return None

        referrer_uid = int(rel["referrer_user_id"])
        if referrer_uid == referred_uid:
            c.rollback()
            return None

        existing = c.execute(
            "SELECT 1 FROM referral_commissions WHERE order_id=?",
            (order_id,)
        ).fetchone()
        if existing:
            c.rollback()
            return None

        referrer = c.execute(
            "SELECT is_blocked,wallet_balance FROM users WHERE user_id=?",
            (referrer_uid,)
        ).fetchone()
        buyer = c.execute(
            "SELECT wallet_balance FROM users WHERE user_id=?",
            (referred_uid,)
        ).fetchone()
        if not referrer or not buyer or int(referrer["is_blocked"] or 0):
            c.rollback()
            return None

        pct = to_int(setting("referral_commission_percent", "10"))
        pct = min(100, max(0, pct if pct is not None else 10))
        purchase_amount = int(order["final_amount"])
        commission = (purchase_amount * pct) // 100

        # Buyer bonus is only for their actual first successful paid purchase.
        prior_paid = c.execute(
            "SELECT 1 FROM orders WHERE user_id=? AND status=? AND final_amount>0 AND id<>? LIMIT 1",
            (referred_uid, COMPLETED, order_id)
        ).fetchone()
        buyer_bonus = 0
        if not prior_paid:
            bonus_setting = to_int(setting("referral_buyer_bonus", "10000"))
            buyer_bonus = max(0, bonus_setting if bonus_setting is not None else 10000)

        if commission > 0:
            new_ref_bal = int(referrer["wallet_balance"] or 0) + commission
            c.execute(
                "UPDATE users SET wallet_balance=? WHERE user_id=?",
                (new_ref_bal, referrer_uid)
            )
            c.execute(
                "INSERT INTO wallet_transactions("
                "user_id,amount,tx_type,reference_type,reference_id,note,created_at"
                ") VALUES(?,?,?,?,?,?,?)",
                (
                    referrer_uid, commission, "referral_commission",
                    "order", order_id,
                    f"{pct}% کمیسیون خرید کاربر معرفی‌شده {referred_uid}",
                    now()
                )
            )
        else:
            new_ref_bal = int(referrer["wallet_balance"] or 0)

        if buyer_bonus > 0:
            new_buyer_bal = int(buyer["wallet_balance"] or 0) + buyer_bonus
            c.execute(
                "UPDATE users SET wallet_balance=? WHERE user_id=?",
                (new_buyer_bal, referred_uid)
            )
            c.execute(
                "INSERT INTO wallet_transactions("
                "user_id,amount,tx_type,reference_type,reference_id,note,created_at"
                ") VALUES(?,?,?,?,?,?,?)",
                (
                    referred_uid, buyer_bonus, "referral_welcome_bonus",
                    "order", order_id,
                    "هدیه اولین خرید از طریق لینک دعوت",
                    now()
                )
            )
        else:
            new_buyer_bal = int(buyer["wallet_balance"] or 0)

        c.execute(
            "INSERT INTO referral_commissions("
            "order_id,referrer_user_id,referred_user_id,purchase_amount,"
            "commission_amount,buyer_bonus_amount,created_at"
            ") VALUES(?,?,?,?,?,?,?)",
            (
                order_id, referrer_uid, referred_uid, purchase_amount,
                commission, buyer_bonus, now()
            )
        )
        c.execute(
            "UPDATE referrals SET qualified_at=COALESCE(qualified_at,?) "
            "WHERE referred_user_id=?",
            (now(), referred_uid)
        )

        c.commit()
        return {
            "referrer_uid": referrer_uid,
            "referred_uid": referred_uid,
            "purchase_amount": purchase_amount,
            "commission": commission,
            "buyer_bonus": buyer_bonus,
            "referrer_balance": new_ref_bal,
            "buyer_balance": new_buyer_bal,
            "percent": pct,
        }
    except sqlite3.IntegrityError:
        c.rollback()
        return None
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()

def referral_stats(uid: int) -> dict[str, Any]:
    cutoff = db_dt(iran_now() - timedelta(hours=REFERRAL_MATURITY_HOURS))
    with db() as c:
        total_joined = c.execute(
            "SELECT COUNT(*) FROM referrals WHERE referrer_user_id=?", (uid,)
        ).fetchone()[0]
        joined = c.execute(
            "SELECT COUNT(*) FROM referrals WHERE referrer_user_id=? AND (joined_at<=? OR qualified_at IS NOT NULL)",
            (uid, cutoff)
        ).fetchone()[0]
        qualified = c.execute(
            "SELECT COUNT(*) FROM referrals WHERE referrer_user_id=? AND qualified_at IS NOT NULL",
            (uid,)
        ).fetchone()[0]
        rewards = c.execute(
            "SELECT COUNT(*) FROM referral_rewards WHERE owner_user_id=?", (uid,)
        ).fetchone()[0]
    next_milestone = int(rewards) + 1
    join_goal = next_milestone * REFERRAL_JOIN_TARGET
    buy_goal = next_milestone * REFERRAL_BUY_TARGET
    claimable = int(joined) >= join_goal and int(qualified) >= buy_goal
    return {
        "joined": int(joined),
        "total_joined": int(total_joined),
        "qualified": int(qualified),
        "rewards": int(rewards),
        "next_milestone": next_milestone,
        "join_goal": join_goal,
        "buy_goal": buy_goal,
        "claimable": claimable,
    }

def mark_referral_qualified(referred_uid: int) -> Optional[int]:
    c = db()
    try:
        c.execute("BEGIN IMMEDIATE")
        paid = c.execute(
            "SELECT 1 FROM orders WHERE user_id=? AND status=? AND final_amount>0 LIMIT 1",
            (referred_uid, COMPLETED)
        ).fetchone()
        if not paid:
            c.rollback()
            return None

        row = c.execute(
            "SELECT referrer_user_id,qualified_at FROM referrals WHERE referred_user_id=?",
            (referred_uid,)
        ).fetchone()
        if not row or row["qualified_at"]:
            c.rollback()
            return None

        cur = c.execute(
            "UPDATE referrals SET qualified_at=? "
            "WHERE referred_user_id=? AND qualified_at IS NULL",
            (now(), referred_uid)
        )
        if cur.rowcount != 1:
            c.rollback()
            return None

        referrer_uid = int(row["referrer_user_id"])
        c.commit()
        return referrer_uid
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()

def referral_reward_rows(uid: int):
    with db() as c:
        return c.execute(
            "SELECT * FROM referral_rewards WHERE owner_user_id=? ORDER BY milestone DESC",
            (uid,)
        ).fetchall()

def claim_referral_reward(uid: int) -> tuple[bool, str]:
    stats = referral_stats(uid)
    if not stats["claimable"]:
        return False, (
            f"هنوز جایزه مرحله {stats['next_milestone']} آماده نیست.\n"
            f"معرفی: {stats['joined']}/{stats['join_goal']}\n"
            f"خرید تکمیل‌شده معرفی‌ها: {stats['qualified']}/{stats['buy_goal']}"
        )

    milestone = stats["next_milestone"]
    code = f"REF{str(uid)[-5:]}M{milestone}{secrets.token_hex(2).upper()}"

    c = db()
    try:
        c.execute("BEGIN IMMEDIATE")

        # Re-check inside the transaction so the reward cannot be issued twice.
        existing = c.execute(
            "SELECT 1 FROM referral_rewards WHERE owner_user_id=? AND milestone=?",
            (uid, milestone)
        ).fetchone()
        if existing:
            c.rollback()
            return False, "این جایزه قبلاً صادر شده."

        cutoff = db_dt(iran_now() - timedelta(hours=REFERRAL_MATURITY_HOURS))
        joined = c.execute(
            "SELECT COUNT(*) FROM referrals WHERE referrer_user_id=? AND (joined_at<=? OR qualified_at IS NOT NULL)",
            (uid, cutoff)
        ).fetchone()[0]
        qualified = c.execute(
            "SELECT COUNT(*) FROM referrals WHERE referrer_user_id=? AND qualified_at IS NOT NULL",
            (uid,)
        ).fetchone()[0]
        if joined < milestone * REFERRAL_JOIN_TARGET or qualified < milestone * REFERRAL_BUY_TARGET:
            c.rollback()
            return False, "شرایط جایزه هنوز کامل نشده."

        c.execute(
            "INSERT INTO coupons(code,kind,value,max_uses,used_count,is_active,created_at) "
            "VALUES(?,'percent',?,1,0,1,?)",
            (code, REFERRAL_REWARD_PERCENT, now())
        )
        c.execute(
            "INSERT INTO referral_rewards(owner_user_id,milestone,coupon_code,created_at) "
            "VALUES(?,?,?,?)",
            (uid, milestone, code, now())
        )
        c.commit()
    except sqlite3.IntegrityError:
        c.rollback()
        return False, "ساخت کد جایزه تکراری شد؛ دوباره تلاش کن."
    finally:
        c.close()

    audit(uid, "referral_reward_claim", f"milestone={milestone},code={code}")
    return True, code

def referral_reward_owner(code: str):
    with db() as c:
        return c.execute(
            "SELECT * FROM referral_rewards WHERE coupon_code=? COLLATE NOCASE",
            (code.strip(),)
        ).fetchone()

def mark_referral_reward_used(code: str):
    with db() as c:
        c.execute(
            "UPDATE referral_rewards SET used_at=? WHERE coupon_code=? COLLATE NOCASE AND used_at IS NULL",
            (now(), code.strip())
        )

def sales_report(start_dt: datetime, end_dt: datetime, title: str) -> str:
    start_s, end_s = db_dt(start_dt), db_dt(end_dt)
    with db() as c:
        completed_n = c.execute(
            "SELECT COUNT(*) FROM orders WHERE status=? AND completed_at>=? AND completed_at<?",
            (COMPLETED, start_s, end_s)
        ).fetchone()[0]
        revenue = c.execute(
            "SELECT COALESCE(SUM(final_amount),0) FROM orders WHERE status=? AND completed_at>=? AND completed_at<?",
            (COMPLETED, start_s, end_s)
        ).fetchone()[0]
        buyers = c.execute(
            "SELECT COUNT(DISTINCT user_id) FROM orders WHERE status=? AND completed_at>=? AND completed_at<?",
            (COMPLETED, start_s, end_s)
        ).fetchone()[0]
        renewals = c.execute(
            "SELECT COUNT(*) FROM orders WHERE status=? AND renew_parent_order_id IS NOT NULL AND completed_at>=? AND completed_at<?",
            (COMPLETED, start_s, end_s)
        ).fetchone()[0]
        top = c.execute(
            "SELECT plan_title,COUNT(*) n FROM orders WHERE status=? AND completed_at>=? AND completed_at<? "
            "GROUP BY plan_title ORDER BY n DESC LIMIT 1",
            (COMPLETED, start_s, end_s)
        ).fetchone()
    top_text = f"{top['plan_title']} ({top['n']} فروش)" if top else "—"
    return (
        f"📈 <b>{esc(title)}</b>\n\n"
        f"🧾 سفارش تکمیل‌شده: <b>{completed_n}</b>\n"
        f"👥 خریدار یکتا: <b>{buyers}</b>\n"
        f"🔄 تمدید موفق: <b>{renewals}</b>\n"
        f"💰 فروش: <b>{money(revenue)}</b>\n"
        f"🏆 پرفروش‌ترین: <b>{esc(top_text)}</b>"
    )

def today_report_text() -> str:
    n = iran_now()
    start = n.replace(hour=0, minute=0, second=0, microsecond=0)
    return sales_report(start, start + timedelta(days=1), f"گزارش فروش امروز • {jalali_date(start)}")

def month_report_text(current: bool = True) -> tuple[str, str]:
    n = iran_now()
    current_start, current_end, current_key = jalali_month_bounds(n)
    if current:
        return sales_report(
            current_start, current_end,
            f"گزارش ماه جاری • {jalali_date(current_start)} تا {jalali_date(current_end - timedelta(days=1))}"
        ), current_key
    previous_point = current_start - timedelta(days=1)
    prev_start, prev_end, prev_key = jalali_month_bounds(previous_point)
    return sales_report(
        prev_start, prev_end,
        f"گزارش ماه قبل • {jalali_date(prev_start)} تا {jalali_date(prev_end - timedelta(days=1))}"
    ), prev_key

def cancel_old_unpaid_orders() -> list[dict[str, Any]]:
    hours = to_int(setting("unpaid_order_expiry_hours", "24"))
    if hours is None or hours <= 0:
        return []

    cutoff = db_dt(iran_now() - timedelta(hours=min(hours, 24 * 365)))
    c = db()
    cancelled: list[dict[str, Any]] = []
    try:
        c.execute("BEGIN IMMEDIATE")
        rows = c.execute(
            "SELECT id,user_id,coupon_code FROM orders "
            "WHERE status=? AND created_at<=? ORDER BY id",
            (AWAIT_RECEIPT, cutoff)
        ).fetchall()

        for row in rows:
            if row["coupon_code"]:
                cp = c.execute(
                    "SELECT id FROM coupons WHERE code=? COLLATE NOCASE",
                    (row["coupon_code"],)
                ).fetchone()
                if cp:
                    deleted = c.execute(
                        "DELETE FROM coupon_uses WHERE coupon_id=? AND user_id=? AND order_id=?",
                        (cp["id"], row["user_id"], row["id"])
                    ).rowcount
                    if deleted:
                        c.execute(
                            "UPDATE coupons SET used_count=MAX(used_count-1,0) WHERE id=?",
                            (cp["id"],)
                        )
                    c.execute(
                        "UPDATE referral_rewards SET used_at=NULL "
                        "WHERE coupon_code=? COLLATE NOCASE",
                        (row["coupon_code"],)
                    )

            cur = c.execute(
                "UPDATE orders SET status=?,updated_at=?,rejection_reason=? "
                "WHERE id=? AND status=?",
                (
                    CANCELLED, now(),
                    f"لغو خودکار: فیش تا {hours} ساعت ارسال نشد.",
                    row["id"], AWAIT_RECEIPT
                )
            )
            if cur.rowcount == 1:
                cancelled.append({
                    "id": int(row["id"]),
                    "user_id": int(row["user_id"]),
                    "hours": hours,
                })

        c.commit()
        return cancelled
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()

def create_ticket(uid: int) -> int:
    with db() as c:
        r = c.execute(
            "SELECT id FROM tickets WHERE user_id=? AND status='open' ORDER BY id DESC LIMIT 1",
            (uid,)
        ).fetchone()
        if r:
            return int(r["id"])
        n = now()
        return int(c.execute(
            "INSERT INTO tickets(user_id,status,created_at,updated_at) VALUES(?,'open',?,?)",
            (uid, n, n)
        ).lastrowid)

def get_ticket(tid: int):
    with db() as c:
        return c.execute("""
            SELECT t.*,u.full_name,u.username FROM tickets t
            JOIN users u ON u.user_id=t.user_id WHERE t.id=?
        """, (tid,)).fetchone()

def list_tickets(page: int):
    with db() as c:
        return c.execute("""
            SELECT t.*,u.full_name,u.username FROM tickets t
            JOIN users u ON u.user_id=t.user_id
            WHERE t.status='open' ORDER BY t.updated_at DESC
            LIMIT ? OFFSET ?
        """, (PAGE_SIZE + 1, max(0,page)*PAGE_SIZE)).fetchall()

def coupon_by_code(code: str):
    with db() as c:
        return c.execute(
            "SELECT * FROM coupons WHERE code=? COLLATE NOCASE", (code.strip(),)
        ).fetchone()

def apply_coupon(uid: int, oid: int, code: str) -> tuple[bool, str]:
    code = code.strip()
    c = db()
    try:
        c.execute("BEGIN IMMEDIATE")

        order = c.execute(
            "SELECT * FROM orders WHERE id=? AND user_id=?",
            (oid, uid)
        ).fetchone()
        if not order or order["status"] != AWAIT_RECEIPT:
            c.rollback()
            return False, "سفارش قابل تخفیف نیست."
        if order["coupon_code"]:
            c.rollback()
            return False, "قبلاً روی این سفارش تخفیف اعمال شده."

        cp = c.execute(
            "SELECT * FROM coupons WHERE code=? COLLATE NOCASE",
            (code,)
        ).fetchone()
        if not cp or not cp["is_active"]:
            c.rollback()
            return False, "کد تخفیف معتبر نیست."

        rr = c.execute(
            "SELECT * FROM referral_rewards WHERE coupon_code=? COLLATE NOCASE",
            (cp["code"],)
        ).fetchone()
        if rr and int(rr["owner_user_id"]) != int(uid):
            c.rollback()
            return False, "این کد جایزه شخصی است و برای حساب شما صادر نشده."
        if rr and rr["used_at"]:
            c.rollback()
            return False, "این کد جایزه قبلاً استفاده شده."

        if cp["max_uses"] > 0 and cp["used_count"] >= cp["max_uses"]:
            c.rollback()
            return False, "ظرفیت کد تخفیف تمام شده."

        previous = c.execute(
            "SELECT 1 FROM coupon_uses WHERE coupon_id=? AND user_id=?",
            (cp["id"], uid)
        ).fetchone()
        if previous:
            c.rollback()
            return False, "قبلاً از این کد استفاده کردی."

        base = int(order["base_amount"])
        if cp["kind"] == "percent":
            discount = int(base * min(max(int(cp["value"]), 0), 100) / 100)
        elif cp["kind"] == "fixed":
            discount = min(max(int(cp["value"]), 0), base)
        else:
            c.rollback()
            return False, "نوع کد تخفیف معتبر نیست."

        final = max(0, base - discount)

        cur = c.execute(
            "UPDATE orders SET discount_amount=?,final_amount=?,coupon_code=?,updated_at=? "
            "WHERE id=? AND user_id=? AND status=? AND coupon_code IS NULL",
            (discount, final, cp["code"], now(), oid, uid, AWAIT_RECEIPT)
        )
        if cur.rowcount != 1:
            c.rollback()
            return False, "وضعیت سفارش تغییر کرده؛ دوباره تلاش کن."

        c.execute(
            "INSERT INTO coupon_uses(coupon_id,user_id,order_id,created_at) VALUES(?,?,?,?)",
            (cp["id"], uid, oid, now())
        )
        c.execute(
            "UPDATE coupons SET used_count=used_count+1 WHERE id=?",
            (cp["id"],)
        )

        if rr:
            c.execute(
                "UPDATE referral_rewards SET used_at=? "
                "WHERE coupon_code=? COLLATE NOCASE AND used_at IS NULL",
                (now(), cp["code"])
            )

        c.commit()
        return True, f"{money(discount)} تخفیف اعمال شد."

    except sqlite3.IntegrityError:
        c.rollback()
        return False, "این کد قبلاً استفاده یا رزرو شده."
    except Exception:
        c.rollback()
        log.exception("coupon apply failed uid=%s order=%s", uid, oid)
        return False, "خطای موقت در اعمال کد؛ دوباره تلاش کن."
    finally:
        c.close()

