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
            "SELECT * FROM orders WHERE status=? AND expires_at IS NOT NULL "
            "AND (expiry_warned_at IS NULL OR expired_notified_at IS NULL)",
            (COMPLETED,)
        ).fetchall()
    for o in rows:
        exp = parse_db_dt(o["expires_at"])
        if not exp:
            continue
        target_uid = int(o["user_id"])
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

async def operations_watch_loop(app: Application):
    while True:
        try:
            trim_bot_log_if_needed()
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
    """Deliver one credential without exposing a partially-sent multi-message payload."""
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
        return False

    # Security boundary: the secret was already delivered. Never re-release this
    # inventory merely because persistence or a follow-up UI message fails.
    try:
        with db() as c:
            c.execute(
                "UPDATE orders SET delivered_config=?,updated_at=? WHERE id=?",
                (config, now(), oid)
            )
    except Exception:
        log.exception("config delivered but DB persistence failed order=%s", oid)

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

def finalize_gift_order(oid: int, config: str) -> str:
    """
    Atomically persist gift credential + gift code + COMPLETED state.
    Once this returns, stock must be committed even if Telegram notification fails.
    """
    c = db()
    try:
        c.execute("BEGIN IMMEDIATE")
        o = c.execute(
            "SELECT id,user_id,status,is_gift FROM orders WHERE id=?",
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
                    "INSERT OR IGNORE INTO gift_codes("
                    "order_id,buyer_user_id,code,status,created_at"
                    ") VALUES(?,?,?,'active',?)",
                    (oid, int(o["user_id"]), candidate, now())
                )
                if cur.rowcount == 1:
                    code = candidate
                    break

                same = c.execute(
                    "SELECT code FROM gift_codes WHERE order_id=?",
                    (oid,)
                ).fetchone()
                if same:
                    code = str(same["code"])
                    break

            if not code:
                raise RuntimeError("gift code generation failed")

        n = now()
        cur = c.execute(
            "UPDATE orders SET delivered_config=?,status=?,"
            "completed_at=COALESCE(completed_at,?),updated_at=? "
            "WHERE id=? AND status IN (?,?)",
            (config, COMPLETED, n, n, oid, APPROVED, COMPLETED)
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

async def complete_gift_with_config(context, oid: int, config: str) -> bool:
    o = get_order(oid)
    if not o:
        return False

    # Critical phase: durable state first.
    try:
        code = finalize_gift_order(oid, config)
    except Exception:
        log.exception("gift critical finalization failed order=%s", oid)
        return False

    # Notification is best-effort only.
    try:
        await context.bot.send_message(
            int(o["user_id"]),
            premium_html(
                f"🎁 <b>هدیه سفارش #{oid} آماده شد</b>\n\n"
                f"📦 {esc(o['plan_title'])}\n"
                "این کد را برای دریافت‌کننده بفرست:\n"
                f"<code>{esc(code)}</code>\n\n"
                "دریافت‌کننده از بخش «🎁 دریافت هدیه» کد را وارد می‌کند.\n"
                "اگر این پیام پاک شد، کد هدیه داخل جزئیات سفارش شما هم باقی می‌ماند."
            ),
            parse_mode="HTML",
            protect_content=True,
            reply_markup=main_kb(int(o["user_id"]))
        )
    except TelegramError:
        log.warning(
            "gift finalized but notification failed order=%s; code remains recoverable",
            oid
        )

    # DB state is already final; caller must commit reserved stock.
    return True

def _xui_expiry_ms(o) -> int:
    exp = parse_db_dt(o["expires_at"])
    if not exp:
        return 0
    return int(exp.timestamp() * 1000)


def _xui_client_email(o) -> str:
    return f"zk_{int(o['user_id'])}_{int(o['id'])}"


async def _xui_credential(xui: XUIClient, sub_id: str, email: str) -> str:
    return await xui.delivery_credential(sub_id, email)


async def sync_xui_order_status(oid: int):
    svc = xui_service_for_order(oid)
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
                (str(exc)[:500], now(), now(), oid)
            )
        raise
    update_xui_service_sync(
        oid,
        total_bytes=status.total_bytes,
        expiry_ms=status.expiry_ms,
        ip_limit=status.limit_ip,
        used_bytes=status.used_bytes,
        enabled=status.enabled,
        last_error="",
    )
    # Keep Zankode's local service expiry aligned with the remote source of truth.
    if status.expiry_ms > 0:
        try:
            remote_dt = datetime.fromtimestamp(status.expiry_ms / 1000, tz=timezone.utc).astimezone(IRAN_TZ)
            with db() as c:
                c.execute("UPDATE orders SET expires_at=?,updated_at=? WHERE id=?", (db_dt(remote_dt), now(), oid))
        except Exception:
            log.exception("failed to align local XUI expiry order=%s", oid)
    return status


async def provision_xui_order(context, oid: int, actor: str = "system") -> bool:
    o = get_order(oid)
    if not o or o["status"] != APPROVED or not o["plan_id"]:
        return False
    plan = get_plan(int(o["plan_id"]))
    if not plan or not plan_is_xui(plan):
        return False

    xui = XUIClient()
    if not xui.configured:
        audit(ADMIN_USER_ID, "xui_not_configured", f"order={oid}")
        try:
            await context.bot.send_message(
                ADMIN_USER_ID,
                premium_html(
                    f"⚠️ <b>سفارش XUI #{oid} آماده ساخت است اما اتصال 3X-UI تنظیم نشده.</b>\n\n"
                    "XUI_PANEL_URL و XUI_API_TOKEN را در .env تنظیم کن. برای Subscription URL هم XUI_SUB_URL_TEMPLATE اختیاری است."
                ),
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🧾 سفارش", callback_data=f"a:order:{oid}")]])
            )
        except TelegramError:
            pass
        return False

    svc = xui_service_for_order(oid)
    parent_svc = xui_parent_service(oid)
    try:
        if svc:
            # Remote provisioning already happened in an earlier attempt. Never create a duplicate.
            email = str(svc["client_email"])
            sub_id = str(svc["sub_id"] or "")
            credential = await _xui_credential(xui, sub_id, email)
        elif parent_svc:
            email = str(parent_svc["client_email"])
            status = await xui.renew_client(
                email,
                duration_days=max(1, int(plan["duration_days"] or 30)),
                total_bytes=bytes_from_gb(int(plan["xui_traffic_gb"] or 0)),
                limit_ip=max(0, int(plan["xui_ip_limit"] or 0)),
                reset_traffic=True,
            )
            sub_id = status.sub_id or str(parent_svc["sub_id"] or "")
            inbound_ids = status.inbound_ids or parse_inbound_ids(str(parent_svc["inbound_ids"] or ""))
            upsert_xui_service(
                oid, int(o["user_id"]), int(o["plan_id"]), email,
                str(parent_svc["client_uuid"] or ""), sub_id, inbound_ids,
                status.total_bytes, status.expiry_ms, status.limit_ip,
                remote_status="active" if status.enabled else "disabled",
                used_bytes=status.used_bytes,
            )
            credential = await _xui_credential(xui, sub_id, email)
            # Align renewal order expiry with remote 3X-UI.
            if status.expiry_ms > 0:
                remote_dt = datetime.fromtimestamp(status.expiry_ms / 1000, tz=timezone.utc).astimezone(IRAN_TZ)
                with db() as c:
                    c.execute("UPDATE orders SET expires_at=?,updated_at=? WHERE id=?", (db_dt(remote_dt), now(), oid))
        else:
            inbound_ids = parse_inbound_ids(str(plan["xui_inbound_ids"] or ""))
            if not inbound_ids:
                raise XUIError("Inbound ID برای این پلن تعیین نشده است")
            provisioned = await xui.create_client(
                email=_xui_client_email(o),
                inbound_ids=inbound_ids,
                total_bytes=bytes_from_gb(int(plan["xui_traffic_gb"] or 0)),
                expiry_ms=_xui_expiry_ms(o),
                limit_ip=max(0, int(plan["xui_ip_limit"] or 0)),
                tg_id=int(o["user_id"]),
                comment=f"Zankode VPN order #{oid} | {o['plan_title']}",
                flow=os.getenv("XUI_DEFAULT_FLOW", "").strip(),
            )
            email, sub_id = provisioned.email, provisioned.sub_id
            try:
                upsert_xui_service(
                    oid, int(o["user_id"]), int(o["plan_id"]), email,
                    provisioned.uuid, sub_id, provisioned.inbound_ids,
                    provisioned.total_bytes, provisioned.expiry_ms, provisioned.limit_ip,
                )
            except Exception:
                # Avoid leaving an untracked paid client in the remote panel.
                try:
                    await xui.delete_client(email)
                except Exception:
                    log.exception("XUI compensation delete failed order=%s client=%s", oid, email)
                raise
            credential = await _xui_credential(xui, sub_id, email)

        if int(o["is_gift"] or 0):
            delivered = await complete_gift_with_config(context, oid, credential)
        else:
            delivered = await send_config(context, int(o["user_id"]), oid, o["plan_title"], credential)
            if delivered:
                update_status(oid, COMPLETED, completed=True)

        if not delivered:
            return False

        audit(
            ADMIN_USER_ID if actor == "admin" else int(o["user_id"]),
            "xui_auto_deliver",
            f"order={oid};client={email};actor={actor}",
        )
        await notify_referral_qualified(context, int(o["user_id"]), oid)
        return True
    except XUIError as exc:
        log.warning("XUI provision failed order=%s: %s", oid, exc)
        with db() as c:
            c.execute(
                "UPDATE xui_services SET last_error=?,updated_at=? WHERE order_id=?",
                (str(exc)[:500], now(), oid)
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


async def delete_xui_service(oid: int) -> bool:
    svc = xui_service_for_order(oid)
    if not svc:
        return False
    xui = XUIClient()
    if not xui.configured:
        raise XUIError("تنظیمات XUI کامل نیست")
    await xui.delete_client(str(svc["client_email"]))
    with db() as c:
        c.execute(
            "UPDATE xui_services SET remote_status='deleted',last_sync_at=?,last_error='',updated_at=? WHERE order_id=?",
            (now(), now(), oid)
        )
    audit(ADMIN_USER_ID, "xui_client_delete", f"order={oid};client={svc['client_email']}")
    return True


async def fulfill_approved_order(context, oid: int, actor: str = "system") -> bool:
    o = get_order(oid)
    if not o or o["status"] != APPROVED:
        return False

    if o["plan_id"]:
        plan = get_plan(int(o["plan_id"]))
        if plan_is_xui(plan):
            return await provision_xui_order(context, oid, actor=actor)

    if setting_on("auto_delivery") and o["plan_id"]:
        cfg = pop_stock(int(o["plan_id"]), oid)
        if cfg:
            if int(o["is_gift"] or 0):
                delivered = await complete_gift_with_config(context, oid, cfg)
            else:
                delivered = await send_config(context, int(o["user_id"]), oid, o["plan_title"], cfg)
                if delivered:
                    update_status(oid, COMPLETED, completed=True)
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

