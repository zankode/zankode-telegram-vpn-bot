# -*- coding: utf-8 -*-
"""Telegram-facing business services, delivery workflows, notifications, and maintenance jobs."""

import io

from .config import *
from .utils import *
from .storage import *
from .ui import *
from .xui import XUIClient, XUIError, bytes_from_gb

async def notify_referral_qualified(
    context: ContextTypes.DEFAULT_TYPE,
    referred_uid: int,
    order_id: Optional[int] = None,
):
    if order_id is None:
        with db() as c:
            row = c.execute(
                "SELECT o.id FROM orders o "
                "WHERE o.user_id=? AND o.status=? AND o.final_amount>0 "
                "AND NOT EXISTS(SELECT 1 FROM referral_commissions rc WHERE rc.order_id=o.id) "
                "ORDER BY o.id DESC LIMIT 1",
                (referred_uid, COMPLETED)
            ).fetchone()
        if not row:
            return
        order_id = int(row["id"])

    reward = apply_referral_wallet_rewards(int(order_id))
    if not reward:
        return

    audit(
        reward["referrer_uid"],
        "referral_wallet_commission",
        f"order={order_id};buyer={reward['referred_uid']};amount={reward['commission']}"
    )

    try:
        if reward["commission"] > 0:
            await context.bot.send_message(
                reward["referrer_uid"],
                premium_html(
                    "🎉 <b>رفیقت خرید کرد!</b>\n\n"
                    f"💰 <b>{money(reward['commission'])}</b> "
                    f"({reward['percent']}٪ خرید) به کیف پولت اضافه شد.\n"
                    f"💳 موجودی جدید: <b>{money(reward['referrer_balance'])}</b>"
                ),
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [user_menu_button("wallet", "مشاهده کیف پول", callback_data="u:wallet", style="success")],
                    [user_menu_button("referral", "دعوت دوستان", callback_data="u:referral", style="primary")],
                ])
            )
    except TelegramError:
        pass

    if reward["buyer_bonus"] > 0:
        audit(
            reward["referred_uid"],
            "referral_buyer_bonus",
            f"order={order_id};amount={reward['buyer_bonus']}"
        )
        try:
            await context.bot.send_message(
                reward["referred_uid"],
                premium_html(
                    "🎁 <b>هدیه اولین خرید Zankode VPN</b>\n\n"
                    f"چون با لینک دعوت دوستت وارد شدی و اولین خریدت رو انجام دادی، "
                    f"<b>{money(reward['buyer_bonus'])}</b> به کیف پولت اضافه شد.\n"
                    f"💳 موجودی جدید: <b>{money(reward['buyer_balance'])}</b>"
                ),
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [user_menu_button("wallet", "مشاهده کیف پول", callback_data="u:wallet", style="success")]
                ])
            )
        except TelegramError:
            pass

async def check_low_stock(bot, pid: int):
    p = get_plan(pid)
    if not p:
        return
    threshold_raw = to_int(setting("low_stock_threshold", "3"))
    threshold = max(0, threshold_raw if threshold_raw is not None else 3)
    level = stock_count(pid)
    with db() as c:
        alert = c.execute("SELECT * FROM stock_alerts WHERE plan_id=?", (pid,)).fetchone()
        if level > threshold:
            if alert:
                c.execute("DELETE FROM stock_alerts WHERE plan_id=?", (pid,))
            return
        if alert:
            return
    try:
        await bot.send_message(
            ADMIN_USER_ID,
            premium_html(
                f"⚠️ <b>هشدار موجودی کم</b>\n\n"
                f"📦 پلن: <b>{esc(p['title'])}</b>\n"
                f"⚡ موجودی فعلی: <b>{level}</b>\n"
                f"📌 حد هشدار: <b>{threshold}</b>"
            ),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⚡ مدیریت موجودی", callback_data=f"a:stockp:{pid}")],
                [InlineKeyboardButton("🛡 پنل مدیریت", callback_data="a:panel")],
            ])
        )
    except TelegramError:
        log.warning("low-stock alert send failed plan=%s level=%s", pid, level)
        return

    # Record the alert only after Telegram actually accepted it. If sending fails,
    # the next maintenance cycle can retry instead of suppressing the warning forever.
    with db() as c:
        c.execute(
            "INSERT OR REPLACE INTO stock_alerts(plan_id,last_level,alerted_at) VALUES(?,?,?)",
            (pid, level, now())
        )

async def process_expiry_notifications(bot):
    n = iran_now()
    warning_end = n + timedelta(days=EXPIRY_WARNING_DAYS)
    with db() as c:
        rows = c.execute(
            "SELECT * FROM orders WHERE status=? AND id=COALESCE(service_root_order_id,id) "
            "AND expires_at IS NOT NULL AND (expiry_warned_at IS NULL OR expired_notified_at IS NULL)",
            (COMPLETED,)
        ).fetchall()
    for o in rows:
        exp = parse_db_dt(o["expires_at"])
        if not exp:
            continue
        target_uid = int(o["service_owner_user_id"] or o["user_id"])
        gift = gift_for_order(int(o["id"])) if int(o["is_gift"] or 0) else None
        if gift and gift["status"] == "redeemed" and gift["recipient_user_id"]:
            target_uid = int(gift["recipient_user_id"])
        if exp <= n and not o["expired_notified_at"]:
            try:
                await bot.send_message(
                    target_uid,
                    premium_html(
                        f"⛔ <b>اعتبار سرویس #{o['id']} به پایان رسید.</b>\n\n"
                        f"💎 {esc(o['plan_title'])}\n📅 تاریخ پایان: <b>{jalali_date(exp)}</b>\n\n"
                        "برای ادامه سرویس، تمدید سریع را بزن."
                    ),
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup(
                        [[InlineKeyboardButton("🛒 خرید سرویس", callback_data="u:plans")],
                         [InlineKeyboardButton("🏠 منوی اصلی", callback_data="u:home")]]
                        if int(o["is_gift"] or 0) else
                        [[InlineKeyboardButton("🔄 تمدید سریع", callback_data=f"u:renew:{o['id']}")],
                         [InlineKeyboardButton("🏠 منوی اصلی", callback_data="u:home")]]
                    )
                )
            except TelegramError:
                log.warning("expiry notification failed order=%s user=%s", o["id"], target_uid)
            else:
                with db() as c:
                    c.execute("UPDATE orders SET expired_notified_at=? WHERE id=?", (now(), o["id"]))
            continue
        if n < exp <= warning_end and not o["expiry_warned_at"]:
            days = max(1, int(((exp - n).total_seconds() + 86399) // 86400))
            try:
                await bot.send_message(
                    target_uid,
                    premium_html(
                        f"⏳ <b>اعتبار سرویس شما رو به اتمامه</b>\n\n"
                        f"💎 {esc(o['plan_title'])}\n📅 پایان: <b>{jalali_date(exp)}</b>\n"
                        f"⏱ حدود <b>{days} روز</b> باقی مونده."
                    ),
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup(
                        [[InlineKeyboardButton("🛒 خرید سرویس", callback_data="u:plans")],
                         [InlineKeyboardButton("💎 سرویس‌های من", callback_data="u:services")]]
                        if int(o["is_gift"] or 0) else
                        [[InlineKeyboardButton("🔄 تمدید سریع", callback_data=f"u:renew:{o['id']}")],
                         [InlineKeyboardButton("💎 سرویس‌های من", callback_data="u:services")]]
                    )
                )
            except TelegramError:
                log.warning("expiry warning failed order=%s user=%s", o["id"], target_uid)
            else:
                with db() as c:
                    c.execute("UPDATE orders SET expiry_warned_at=? WHERE id=?", (now(), o["id"]))

async def process_old_unpaid_orders(bot):
    for row in cancel_old_unpaid_orders():
        audit(None, "auto_cancel_unpaid", f"order={row['id']}")
        try:
            await bot.send_message(
                row["user_id"],
                premium_html(
                    f"♻️ <b>سفارش #{row['id']} لغو شد.</b>\n\n"
                    f"چون طی {row['hours']} ساعت فیش ارسال نشد، سفارش خودکار بسته شد.\n"
                    "اگر هنوز سرویس می‌خوای، سفارش جدید ثبت کن."
                ),
                parse_mode="HTML",
                reply_markup=main_kb(row["user_id"])
            )
        except TelegramError:
            pass

async def check_test_low_stock(bot):
    threshold = to_int(setting("test_low_stock_threshold", "3"))
    threshold = max(0, threshold if threshold is not None else 3)
    level = test_stock_count()
    alerted = setting_on("test_low_stock_alerted")

    if level <= threshold and not alerted:
        try:
            await bot.send_message(
                ADMIN_USER_ID,
                premium_html(
                    "🚨 <b>هشدار موجودی تست</b>\n\n"
                    f"🧪 موجودی تست 50MB: <b>{level}</b>\n"
                    f"📌 حد هشدار: <b>{threshold}</b>"
                ),
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🧪 مدیریت تست", callback_data="a:teststock")]
                ])
            )
            set_setting("test_low_stock_alerted", "1")
        except TelegramError:
            pass
    elif level > threshold and alerted:
        set_setting("test_low_stock_alerted", "0")

def trim_bot_log_if_needed(
    max_bytes: int = 8 * 1024 * 1024,
    keep_bytes: int = 3 * 1024 * 1024,
):
    """
    Prevent bot.log created by nohup redirection from growing forever.
    Truncates in-place so the already-open append file descriptor remains usable.
    """
    path = BASE_DIR / "bot.log"
    try:
        if not path.exists():
            return
        size = path.stat().st_size
        if size <= max_bytes:
            return

        with path.open("rb") as f:
            f.seek(max(0, size - keep_bytes))
            tail = f.read()

        nl = tail.find(b"\n")
        if nl >= 0:
            tail = tail[nl + 1:]

        with path.open("wb") as f:
            f.write(b"--- bot.log trimmed; newest entries preserved ---\n")
            f.write(tail)

        if os.name != "nt":
            os.chmod(path, 0o600)
    except OSError:
        log.warning("bot.log size maintenance failed")

async def retry_staged_deliveries(app: Application):
    """Retry credentials safely staged before a prior Telegram/crash failure."""
    cutoff = db_dt(iran_now() - timedelta(seconds=30))
    with db() as c:
        rows = c.execute(
            "SELECT id FROM orders WHERE status=? AND COALESCE(is_gift,0)=0 "
            "AND delivered_config IS NOT NULL AND delivered_config<>'' "
            "AND COALESCE(delivery_attempts,0)<5 AND updated_at<=? "
            "ORDER BY updated_at,id LIMIT 10",
            (APPROVED, cutoff),
        ).fetchall()
    for row in rows:
        try:
            await fulfill_approved_order(app, int(row["id"]), actor="recovery")
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("staged delivery retry failed order=%s", row["id"])


async def operations_watch_loop(app: Application):
    while True:
        try:
            trim_bot_log_if_needed()
            await retry_staged_deliveries(app)
            await process_expiry_notifications(app.bot)
            await process_old_unpaid_orders(app.bot)
            await check_test_low_stock(app.bot)
            for p in active_plans():
                await check_low_stock(app.bot, int(p["id"]))

            n = iran_now()
            today_key = n.strftime("%Y-%m-%d")
            if n.hour >= 23 and setting("last_daily_report") != today_key:
                await app.bot.send_message(
                    ADMIN_USER_ID, premium_html(today_report_text()), parse_mode="HTML"
                )
                set_setting("last_daily_report", today_key)

            month_text, prev_key = month_report_text(current=False)
            jy, jm, jd = gregorian_to_jalali(n.year, n.month, n.day)
            if jd == 1 and n.hour >= 9 and setting("last_monthly_report") != prev_key:
                await app.bot.send_message(
                    ADMIN_USER_ID, premium_html(month_text), parse_mode="HTML"
                )
                set_setting("last_monthly_report", prev_key)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("operations_watch_loop error")
        await asyncio.sleep(OPERATIONS_CHECK_SECONDS)

async def answer(q, text: str = "", alert: bool = False):
    try:
        await q.answer(text=text, show_alert=alert)
    except TelegramError:
        pass

async def edit(q, text: str, kb: Optional[InlineKeyboardMarkup] = None):
    text = premium_html(text)
    try:
        await q.edit_message_text(text, parse_mode="HTML", reply_markup=kb)
    except BadRequest as e:
        if "Message is not modified" in str(e):
            return
        try:
            await q.message.reply_text(text, parse_mode="HTML", reply_markup=kb)
        except TelegramError:
            pass

async def access_ok(update: Update) -> bool:
    u = update.effective_user
    chat = update.effective_chat
    if not u:
        return False

    # Sales/account/config data must never be handled in groups/channels.
    if chat and chat.type != "private":
        if update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "🔒 برای امنیت حساب و کانفیگ، ربات فقط در گفت‌وگوی خصوصی قابل استفاده است."
                )
            except TelegramError:
                pass
        return False

    if is_admin(u.id):
        return True
    if blocked(u.id):
        if update.effective_message:
            await update.effective_message.reply_text("⛔ دسترسی شما به ربات مسدود شده.")
        return False
    if setting_on("maintenance"):
        if update.effective_message:
            await update.effective_message.reply_text("🛠 ربات موقتاً در حالت تعمیرات است.")
        return False
    return True

async def send_protected_credential(
    bot,
    uid: int,
    heading_html: str,
    config: str,
    filename: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
):
    """Send one credential atomically as a protected message or protected text file."""
    inline_text = premium_html(f"{heading_html}\n\n<code>{esc(config)}</code>")
    if len(config) <= 3000 and len(inline_text) <= 3900:
        await bot.send_message(
            uid,
            inline_text,
            parse_mode="HTML",
            protect_content=True,
            reply_markup=reply_markup,
        )
        return

    payload = io.BytesIO(config.encode("utf-8"))
    payload.name = filename
    await bot.send_document(
        uid,
        document=payload,
        filename=filename,
        caption=premium_html(
            f"{heading_html}\n\n"
            "به‌دلیل طول زیاد، کانفیگ به‌صورت فایل متنی محافظت‌شده ارسال شد."
        ),
        parse_mode="HTML",
        protect_content=True,
        reply_markup=reply_markup,
    )


async def send_config(context, uid: int, oid: int, plan_title: str, config: str) -> bool:
    """Stage one credential, deliver it, then atomically activate the service."""
    try:
        config = stage_delivery_config(oid, config)
    except Exception:
        log.exception("credential staging failed order=%s", oid)
        return False
    try:
        await send_protected_credential(
            context.bot,
            uid,
            f"🎉 <b>سفارش #{oid} آماده شد</b>\n📦 {esc(plan_title)}",
            config,
            f"zankode_order_{oid}.txt",
        )
    except TelegramError:
        log.exception("config payload delivery failed order=%s", oid)
        attempts = 0
        try:
            with db() as c:
                c.execute(
                    "UPDATE orders SET delivery_attempts=COALESCE(delivery_attempts,0)+1,updated_at=? WHERE id=?",
                    (now(), int(oid)),
                )
                row = c.execute("SELECT delivery_attempts FROM orders WHERE id=?", (int(oid),)).fetchone()
                attempts = int(row["delivery_attempts"] or 0) if row else 0
        except sqlite3.Error:
            log.exception("failed to record delivery attempt order=%s", oid)
        if attempts == 5:
            try:
                await context.bot.send_message(
                    ADMIN_USER_ID,
                    premium_html(
                        f"⚠️ <b>تحویل خودکار سفارش #{oid} متوقف شد</b>\n\n"
                        "پنج تلاش ارسال ناموفق بود. Credential همچنان به همین سفارش قفل است؛ "
                        "بعد از بررسی کاربر/تلگرام، از پنل ادمین Retry دستی بزن."
                    ),
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🧾 سفارش", callback_data=f"a:order:{oid}")
                    ]]),
                )
            except TelegramError:
                pass
        return False

    persisted = False
    for attempt in range(3):
        try:
            persisted = finalize_service_delivery(oid, config, owner_uid=uid)
            if persisted:
                break
        except sqlite3.Error:
            log.exception("delivery persistence failed order=%s attempt=%s", oid, attempt + 1)
            await asyncio.sleep(0.15 * (attempt + 1))
        except Exception:
            log.exception("unexpected delivery persistence failure order=%s", oid)
            break

    if not persisted:
        # The secret already reached Telegram, so never release/reuse the same stock.
        audit(ADMIN_USER_ID, "delivery_persistence_critical", f"order={oid}")
        try:
            await context.bot.send_message(
                ADMIN_USER_ID,
                premium_html(
                    f"⚠️ <b>هشدار ثبت تحویل سفارش #{oid}</b>\n\n"
                    "کانفیگ به کاربر ارسال شد اما ثبت نهایی دیتابیس ناموفق بود. "
                    "این سفارش را دستی بررسی کن و همان کانفیگ را دوباره به موجودی برنگردان."
                ),
                parse_mode="HTML",
            )
        except TelegramError:
            pass

    try:
        await context.bot.send_message(
            uid,
            premium_html("✅ سرویس تحویل شد و داخل «💎 سرویس‌های من» ثبت شد."),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [user_button(
                    "💎 سرویس‌های من",
                    callback_data="u:services",
                    style="success",
                    icon_custom_emoji_id=CUSTOM_EMOJI_SERVICE_ID
                )],
                [user_button(
                    "👤 حساب من",
                    callback_data="u:account",
                    style="primary",
                    icon_custom_emoji_id=CUSTOM_EMOJI_ACCOUNT_ID
                )],
            ])
        )
    except TelegramError:
        log.warning("config delivered; final confirmation failed order=%s", oid)

    return True

def finalize_gift_order(oid: int, config: Optional[str] = None) -> str:
    """Finalize the *purchase* of a gift without starting service validity.

    Inventory gifts may already carry a reserved credential. XUI gifts intentionally
    carry no credential until the recipient redeems the code, so remote expiry starts
    at redemption rather than at the buyer's payment time.
    """
    c = db()
    try:
        c.execute("BEGIN IMMEDIATE")
        o = c.execute(
            "SELECT id,user_id,status,is_gift,approved_at,purchased_at FROM orders WHERE id=?",
            (oid,)
        ).fetchone()
        if not o or not int(o["is_gift"] or 0):
            raise ValueError("gift order not found")

        existing = c.execute(
            "SELECT code FROM gift_codes WHERE order_id=?",
            (oid,)
        ).fetchone()
        if existing:
            code = str(existing["code"])
        else:
            code = ""
            for _ in range(30):
                candidate = "ZKG-" + secrets.token_hex(8).upper()
                cur = c.execute(
                    "INSERT OR IGNORE INTO gift_codes(order_id,buyer_user_id,code,status,created_at) "
                    "VALUES(?,?,?,'active',?)",
                    (oid, int(o["user_id"]), candidate, now())
                )
                if cur.rowcount == 1:
                    code = candidate
                    break
                same = c.execute("SELECT code FROM gift_codes WHERE order_id=?", (oid,)).fetchone()
                if same:
                    code = str(same["code"])
                    break
            if not code:
                raise RuntimeError("gift code generation failed")

        n = now()
        cur = c.execute(
            "UPDATE orders SET delivered_config=CASE WHEN ? IS NULL THEN delivered_config ELSE ? END,"
            "status=?,purchased_at=COALESCE(purchased_at,approved_at,?),completed_at=COALESCE(completed_at,?),updated_at=? "
            "WHERE id=? AND status IN (?,?)",
            (config, config, COMPLETED, n, n, n, oid, APPROVED, COMPLETED)
        )
        if cur.rowcount != 1:
            raise RuntimeError("gift order state changed concurrently")
        c.commit()
        return code
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()

async def complete_gift_with_config(context, oid: int, config: Optional[str] = None) -> bool:
    o = get_order(oid)
    if not o:
        return False
    try:
        code = finalize_gift_order(oid, config)
    except Exception:
        log.exception("gift critical finalization failed order=%s", oid)
        return False

    try:
        await context.bot.send_message(
            int(o["user_id"]),
            premium_html(
                f"🎁 <b>هدیه سفارش #{oid} آماده شد</b>\n\n"
                f"📦 {esc(o['plan_title'])}\n"
                "این کد را برای دریافت‌کننده بفرست:\n"
                f"<code>{esc(code)}</code>\n\n"
                "اعتبار سرویس از زمان دریافت هدیه فعال می‌شود.\n"
                "اگر این پیام پاک شد، کد هدیه داخل جزئیات سفارش شما هم باقی می‌ماند."
            ),
            parse_mode="HTML",
            protect_content=True,
            reply_markup=main_kb(int(o["user_id"]))
        )
    except TelegramError:
        log.warning("gift finalized but notification failed order=%s; code remains recoverable", oid)
    return True


def _xui_expiry_ms(o) -> int:
    exp = parse_db_dt(o["expires_at"])
    if not exp:
        return 0
    return int(exp.timestamp() * 1000)


def _xui_client_email(o, owner_uid: Optional[int] = None) -> str:
    root_id = service_root_id(int(o["id"]))
    if int(o["is_gift"] or 0):
        return f"zk_gift_{root_id}"
    owner = int(owner_uid or o["service_owner_user_id"] or o["user_id"])
    return f"zk_{owner}_{root_id}"


async def _xui_credential(xui: XUIClient, sub_id: str, email: str) -> str:
    return await xui.delivery_credential(sub_id, email)


async def sync_xui_order_status(oid: int):
    root_id = service_root_id(int(oid))
    svc = xui_service_for_order(root_id)
    if not svc:
        return None
    xui = XUIClient()
    if not xui.configured:
        raise XUIError("تنظیمات XUI کامل نیست")
    try:
        status = await xui.status(str(svc["client_email"]))
    except Exception as exc:
        with db() as c:
            c.execute(
                "UPDATE xui_services SET last_error=?,last_sync_at=?,updated_at=? WHERE order_id=?",
                (str(exc)[:500], now(), now(), root_id)
            )
        raise
    update_xui_service_sync(
        root_id,
        total_bytes=status.total_bytes,
        expiry_ms=status.expiry_ms,
        ip_limit=status.limit_ip,
        used_bytes=status.used_bytes,
        enabled=status.enabled,
        last_error="",
    )
    if status.expiry_ms > 0:
        try:
            remote_dt = datetime.fromtimestamp(status.expiry_ms / 1000, tz=timezone.utc).astimezone(IRAN_TZ)
            with db() as c:
                c.execute(
                    "UPDATE orders SET expires_at=?,expiry_warned_at=NULL,expired_notified_at=NULL,updated_at=? WHERE id=?",
                    (db_dt(remote_dt), now(), root_id),
                )
        except Exception:
            log.exception("failed to align local XUI expiry root_order=%s", root_id)
    return status


async def _ensure_xui_for_order(xui: XUIClient, o, *, owner_uid: int):
    """Create/recover/renew the one canonical remote client for an order."""
    oid = int(o["id"])
    root_id = service_root_id(oid)
    _, target_expiry = prepare_service_activation(oid, owner_uid=owner_uid)
    target_ms = int(target_expiry.timestamp() * 1000)
    inbound_ids = order_xui_inbound_ids(o)
    if not inbound_ids:
        raise XUIError("Inbound ID برای این سفارش تعیین نشده است")
    total_bytes = bytes_from_gb(order_xui_traffic_gb(o))
    ip_limit = order_xui_ip_limit(o)
    svc = xui_service_for_order(root_id)

    if int(o["renew_parent_order_id"] or 0):
        if not svc:
            raise XUIError("سرویس اصلی 3X-UI برای تمدید پیدا نشد")
        email = str(svc["client_email"])
        if o["remote_applied_at"]:
            status = await xui.status(email)
            # If an admin manually shortened the client after payment but before
            # delivery retry, restore the deterministic paid target.
            if int(status.expiry_ms or 0) != target_ms or int(status.total_bytes or 0) != total_bytes or int(status.limit_ip or 0) != ip_limit:
                status = await xui.renew_client(
                    email,
                    target_expiry_ms=target_ms,
                    total_bytes=total_bytes,
                    limit_ip=ip_limit,
                    reset_traffic=False,
                    tg_id=owner_uid,
                    comment=f"Zankode renewal #{oid}",
                )
        else:
            # Reconcile before mutating. If the previous process crashed after the
            # remote renewal but before writing remote_applied_at, the exact paid
            # target already proves the renewal reached 3X-UI. In that case we
            # recover state without resetting traffic a second time.
            current = await xui.status(email)
            already_applied = (
                int(current.expiry_ms or 0) == target_ms
                and int(current.total_bytes or 0) == total_bytes
                and int(current.limit_ip or 0) == ip_limit
            )
            if already_applied:
                status = current
            else:
                status = await xui.renew_client(
                    email,
                    target_expiry_ms=target_ms,
                    total_bytes=total_bytes,
                    limit_ip=ip_limit,
                    reset_traffic=True,
                    tg_id=owner_uid,
                    comment=f"Zankode renewal #{oid}",
                )
            stamp = now()
            with db() as c:
                c.execute("UPDATE orders SET remote_applied_at=?,updated_at=? WHERE id=?", (stamp, stamp, oid))
        sub_id = status.sub_id or str(svc["sub_id"] or "")
        inbound_ids = status.inbound_ids or parse_inbound_ids(str(svc["inbound_ids"] or "")) or inbound_ids
        upsert_xui_service(
            root_id, owner_uid, int(o["plan_id"]) if o["plan_id"] else None, email,
            str(svc["client_uuid"] or ""), sub_id, inbound_ids,
            status.total_bytes, status.expiry_ms, status.limit_ip,
            remote_status="active" if status.enabled else "disabled",
            used_bytes=status.used_bytes,
        )
        return email, sub_id

    email = str(svc["client_email"]) if svc else _xui_client_email(o, owner_uid)
    if svc and o["remote_applied_at"]:
        status = await xui.status(email)
        sub_id = status.sub_id or str(svc["sub_id"] or "")
        upsert_xui_service(
            root_id, owner_uid, int(o["plan_id"]) if o["plan_id"] else None, email,
            str(svc["client_uuid"] or ""), sub_id, status.inbound_ids or inbound_ids,
            status.total_bytes, status.expiry_ms, status.limit_ip,
            remote_status="active" if status.enabled else "disabled", used_bytes=status.used_bytes,
        )
        return email, sub_id

    provisioned = await xui.create_client(
        email=email,
        inbound_ids=inbound_ids,
        total_bytes=total_bytes,
        expiry_ms=target_ms,
        limit_ip=ip_limit,
        tg_id=owner_uid,
        comment=f"Zankode VPN service #{root_id} | order #{oid} | {o['plan_title']}",
        flow=os.getenv("XUI_DEFAULT_FLOW", "").strip(),
    )
    upsert_xui_service(
        root_id, owner_uid, int(o["plan_id"]) if o["plan_id"] else None, provisioned.email,
        provisioned.uuid, provisioned.sub_id, provisioned.inbound_ids,
        provisioned.total_bytes, provisioned.expiry_ms, provisioned.limit_ip,
    )
    with db() as c:
        c.execute("UPDATE orders SET remote_applied_at=?,updated_at=? WHERE id=?", (now(), now(), oid))
    return provisioned.email, provisioned.sub_id


async def provision_xui_order(context, oid: int, actor: str = "system") -> bool:
    o = get_order(oid)
    if not o or o["status"] != APPROVED or not order_is_xui(o):
        return False

    # Gift purchase creates only a voucher. The remote client is created when the
    # recipient redeems it so service validity starts at the correct moment.
    if int(o["is_gift"] or 0):
        return await complete_gift_with_config(context, oid, None)

    xui = XUIClient()
    if not xui.configured:
        audit(ADMIN_USER_ID, "xui_not_configured", f"order={oid}")
        try:
            await context.bot.send_message(
                ADMIN_USER_ID,
                premium_html(
                    f"⚠️ <b>سفارش XUI #{oid} آماده ساخت است اما اتصال 3X-UI تنظیم نشده.</b>\n\n"
                    "XUI_PANEL_URL و XUI_API_TOKEN را در .env تنظیم کن. Subscription URL اختیاری است."
                ),
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🧾 سفارش", callback_data=f"a:order:{oid}")]])
            )
        except TelegramError:
            pass
        return False

    try:
        owner_uid = int(o["service_owner_user_id"] or o["user_id"])
        email, sub_id = await _ensure_xui_for_order(xui, o, owner_uid=owner_uid)
        credential = await _xui_credential(xui, sub_id, email)
        delivered = await send_config(context, owner_uid, oid, o["plan_title"], credential)
        if not delivered:
            return False
        audit(
            ADMIN_USER_ID if actor == "admin" else int(o["user_id"]),
            "xui_auto_deliver",
            f"order={oid};root={service_root_id(oid)};client={email};actor={actor}",
        )
        if get_order(oid) and get_order(oid)["status"] == COMPLETED:
            await notify_referral_qualified(context, int(o["user_id"]), oid)
        return True
    except XUIError as exc:
        log.warning("XUI provision failed order=%s: %s", oid, exc)
        root_id = service_root_id(oid)
        with db() as c:
            c.execute(
                "UPDATE xui_services SET last_error=?,updated_at=? WHERE order_id=?",
                (str(exc)[:500], now(), root_id)
            )
        audit(ADMIN_USER_ID, "xui_provision_failed", f"order={oid};error={str(exc)[:200]}")
        try:
            await context.bot.send_message(
                ADMIN_USER_ID,
                premium_html(
                    f"⚠️ <b>تحویل خودکار XUI سفارش #{oid} ناموفق بود</b>\n\n"
                    f"{esc(str(exc))}\n\nسفارش در وضعیت تأییدشده باقی ماند و دوباره قابل تلاش است."
                ),
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 تلاش مجدد XUI", callback_data=f"a:xretry:{oid}")],
                    [InlineKeyboardButton("🧾 سفارش", callback_data=f"a:order:{oid}")],
                ])
            )
        except TelegramError:
            pass
        return False
    except Exception:
        log.exception("unexpected XUI provision failure order=%s", oid)
        audit(ADMIN_USER_ID, "xui_provision_exception", f"order={oid}")
        return False


async def redeem_gift_service(context, gift_row, recipient_uid: int) -> bool:
    """Activate a reserved gift for its recipient with crash-safe ownership."""
    gid = int(gift_row["id"])
    oid = int(gift_row["order_id"])
    o = get_order(oid)
    if not o or o["status"] != COMPLETED or not int(o["is_gift"] or 0):
        return False

    credential = str(o["delivered_config"] or "")
    try:
        if order_is_xui(o):
            xui = XUIClient()
            if not xui.configured:
                raise XUIError("اتصال 3X-UI برای فعال‌سازی هدیه تنظیم نشده است")
            email, sub_id = await _ensure_xui_for_order(xui, o, owner_uid=int(recipient_uid))
            credential = await _xui_credential(xui, sub_id, email)
        if not credential:
            raise RuntimeError("credential for gift is not available")

        # Durable ownership first. If Telegram fails after this point, the recipient
        # can reopen My Services and retrieve the credential without losing the gift.
        finalize_service_delivery(oid, credential, owner_uid=int(recipient_uid))
        finish_gift_redeem(gid, True)
        audit(recipient_uid, "gift_redeem", f"gift={gid};order={oid}")

        try:
            await send_protected_credential(
                context.bot,
                int(recipient_uid),
                "🎉 <b>هدیه شما فعال شد</b>\n" f"📦 {esc(o['plan_title'])}",
                credential,
                f"zankode_gift_{gid}.txt",
                reply_markup=main_kb(int(recipient_uid)),
            )
        except TelegramError:
            log.warning("gift activated but Telegram delivery failed gift=%s user=%s", gid, recipient_uid)
        try:
            await context.bot.send_message(
                int(gift_row["buyer_user_id"]),
                f"🎁 هدیه سفارش #{oid} توسط کاربر <code>{int(recipient_uid)}</code> فعال شد.",
                parse_mode="HTML"
            )
        except TelegramError:
            pass
        return True
    except Exception as exc:
        log.exception("gift activation failed gift=%s order=%s", gid, oid)
        audit(recipient_uid, "gift_redeem_failed", f"gift={gid};order={oid};error={str(exc)[:180]}")
        # Keep `redeeming` for XUI partial failures so only the same recipient can
        # resume the deterministic remote operation with the same gift code.
        if not order_is_xui(o):
            finish_gift_redeem(gid, False)
        return False


async def delete_xui_service(oid: int) -> bool:
    root_id = service_root_id(int(oid))
    svc = xui_service_for_order(root_id)
    if not svc:
        return False
    xui = XUIClient()
    if not xui.configured:
        raise XUIError("تنظیمات XUI کامل نیست")
    await xui.delete_client(str(svc["client_email"]))
    with db() as c:
        c.execute(
            "UPDATE xui_services SET remote_status='deleted',last_sync_at=?,last_error='',updated_at=? WHERE order_id=?",
            (now(), now(), root_id)
        )
    audit(ADMIN_USER_ID, "xui_client_delete", f"order={oid};root={root_id};client={svc['client_email']}")
    return True


async def fulfill_approved_order(context, oid: int, actor: str = "system") -> bool:
    o = get_order(oid)
    if not o or o["status"] != APPROVED:
        return False

    # Crash/retry path: once a credential is staged it is the only credential that
    # may ever be delivered for this order, regardless of later stock/plan changes.
    if o["delivered_config"] and not int(o["is_gift"] or 0):
        delivered = await send_config(context, int(o["service_owner_user_id"] or o["user_id"]), oid, o["plan_title"], str(o["delivered_config"]))
        if delivered:
            commit_stock_for_order(oid)
            await notify_referral_qualified(context, int(o["user_id"]), oid)
        return delivered

    if order_is_xui(o):
        delivered = await provision_xui_order(context, oid, actor=actor)
        if delivered and int(o["is_gift"] or 0):
            await notify_referral_qualified(context, int(o["user_id"]), oid)
        return delivered

    if setting_on("auto_delivery") and o["plan_id"]:
        cfg = pop_stock(int(o["plan_id"]), oid)
        if cfg:
            if int(o["is_gift"] or 0):
                delivered = await complete_gift_with_config(context, oid, cfg)
            else:
                delivered = await send_config(context, int(o["user_id"]), oid, o["plan_title"], cfg)
            if delivered:
                commit_stock_for_order(oid)
                audit(ADMIN_USER_ID if actor == "admin" else int(o["user_id"]), "auto_deliver", f"order={oid};actor={actor}")
                await notify_referral_qualified(context, int(o["user_id"]), oid)
                await check_low_stock(context.bot, int(o["plan_id"]))
                return True
            release_stock_for_order(oid)
            return False

    try:
        await context.bot.send_message(
            ADMIN_USER_ID,
            f"📤 سفارش #{oid} پرداخت شده ولی نیاز به تحویل دستی دارد.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📤 ارسال کانفیگ", callback_data=f"a:deliver:{oid}")],
                [InlineKeyboardButton("🧾 سفارش", callback_data=f"a:order:{oid}")],
            ])
        )
    except TelegramError:
        pass
    return False

async def send_wallet_topup_admin(context, tid: int):
    t = get_wallet_topup(tid)
    if not t or not t["receipt_file_id"]:
        return
    caption = (
        f"💳 <b>شارژ کیف پول #{tid}</b>\n\n"
        f"👤 {esc(t['full_name'])}\n🆔 <code>{t['user_id']}</code>\n"
        f"💰 مبلغ شارژ: <b>{money(t['amount'])}</b>"
    )
    try:
        await context.bot.send_photo(
            ADMIN_USER_ID, t["receipt_file_id"], caption=premium_html(caption), parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ تأیید شارژ", callback_data=f"a:wapprove:{tid}", style="success"),
                InlineKeyboardButton("❌ رد", callback_data=f"a:wreject:{tid}", style="danger"),
            ]])
        )
    except TelegramError:
        log.exception("wallet topup admin send failed")

async def send_receipt_admin(context, oid: int):
    o = get_order(oid)
    if not o:
        return
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ تأیید", callback_data=f"a:approve:{oid}"),
            InlineKeyboardButton("❌ رد", callback_data=f"a:reject:{oid}"),
        ],
        [InlineKeyboardButton("🔎 جزئیات", callback_data=f"a:order:{oid}")],
    ])
    try:
        await context.bot.send_photo(
            ADMIN_USER_ID, o["receipt_file_id"],
            caption=premium_html(admin_order_text(o)), parse_mode="HTML", reply_markup=kb
        )
    except TelegramError:
        log.exception("send receipt admin failed")

async def backup_db(context):
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(prefix="shop_", suffix=".sqlite3", delete=False) as f:
            tmp_path = f.name
        s = sqlite3.connect(DB_PATH)
        t = sqlite3.connect(tmp_path)
        try:
            s.backup(t)
        finally:
            s.close()
            t.close()
        with open(tmp_path, "rb") as f:
            await context.bot.send_document(
                ADMIN_USER_ID, f,
                filename=f"shop_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sqlite3",
                caption="💾 بکاپ دیتابیس",
                protect_content=True,
            )
        audit(ADMIN_USER_ID, "backup")
    except Exception:
        log.exception("backup failed")
        await context.bot.send_message(ADMIN_USER_ID, "❌ بکاپ ناموفق بود.")
    finally:
        if tmp_path:
            try: os.remove(tmp_path)
            except OSError: pass

