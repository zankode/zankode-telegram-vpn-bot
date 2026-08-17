# -*- coding: utf-8 -*-
"""Receipt, generic message, admin text/media actions, and broadcast handlers."""

from ..config import *
from .. import config as cfg
from ..utils import *
from ..storage import *
from ..ui import *
from ..ui import _user_icon_setting_key
from ..services import *
from .admin_views import *
from .admin_views import _config_preview, _broadcast_lock
from .admin import reject

async def receipt_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    upsert_user(u)
    if not await access_ok(update):
        return
    a = get_action(u.id)

    if a and (
        a["action"] == "support"
        or (is_admin(u.id) and a["action"] in {"broadcast", "ticket_reply", "target_broadcast"})
    ):
        await messages(update, context)
        return

    if a and a["action"] == "wallet_receipt":
        tid = to_int(a["payload"] or "")
        top = get_wallet_topup(tid) if tid is not None else None
        if not top or int(top["user_id"]) != u.id or top["status"] not in {"awaiting_receipt", "rejected"}:
            clear_action(u.id)
            return
        photo = update.effective_message.photo[-1]
        fid, funiq = photo.file_id, photo.file_unique_id
        with db() as c:
            dup_order = c.execute("SELECT 1 FROM orders WHERE receipt_unique_id=? LIMIT 1", (funiq,)).fetchone()
            dup_top = c.execute("SELECT 1 FROM wallet_topups WHERE receipt_unique_id=? AND id<>? LIMIT 1", (funiq, tid)).fetchone()
        if dup_order or dup_top:
            await update.effective_message.reply_text("🚫 این فیش قبلاً در سیستم استفاده شده است.", reply_markup=main_kb(u.id))
            return
        try:
            with db() as c:
                cur = c.execute(
                    "UPDATE wallet_topups SET receipt_file_id=?,receipt_unique_id=?,status='awaiting_admin',updated_at=?,rejection_reason=NULL "
                    "WHERE id=? AND user_id=? AND status IN ('awaiting_receipt','rejected')",
                    (fid, funiq, now(), tid, u.id)
                )
                if cur.rowcount != 1:
                    return
        except sqlite3.IntegrityError:
            await update.effective_message.reply_text("🚫 این فیش تکراری است.")
            return
        clear_action(u.id)
        audit(u.id, "wallet_receipt", str(tid))
        await update.effective_message.reply_text("✅ فیش شارژ کیف پول دریافت شد و برای ادمین رفت.", reply_markup=main_kb(u.id))
        await send_wallet_topup_admin(context, tid)
        return

    if rate_limit(context, u.id, "msg", MSG_COOLDOWN):
        return
    if not a or a["action"] != "receipt":
        await update.effective_message.reply_text(
            "📸 اول از داخل سفارش روی «ارسال فیش» بزن.", reply_markup=main_kb(u.id)
        )
        return

    oid = to_int(a["payload"] or "")
    o = get_order(oid) if oid is not None else None
    if not o or o["user_id"] != u.id:
        clear_action(u.id)
        return
    if o["status"] not in (AWAIT_RECEIPT, REJECTED):
        clear_action(u.id)
        return

    photo = update.effective_message.photo[-1]
    fid = photo.file_id
    funiq = photo.file_unique_id
    # Exact Telegram-file duplicate detection. A re-screenshot/crop can get a new unique ID,
    # therefore the admin must still verify bank-payment details manually.
    with db() as c:
        duplicate = c.execute(
            "SELECT id,user_id FROM orders WHERE receipt_unique_id=? AND id<>? LIMIT 1",
            (funiq, oid)
        ).fetchone()
        duplicate_wallet = c.execute(
            "SELECT id,user_id FROM wallet_topups WHERE receipt_unique_id=? LIMIT 1",
            (funiq,)
        ).fetchone()
    if duplicate or duplicate_wallet:
        prev = duplicate["id"] if duplicate else f"wallet:{duplicate_wallet['id']}"
        audit(u.id, "duplicate_receipt_blocked", f"order={oid},previous={prev}")
        await update.effective_message.reply_text(
            "🚫 <b>این فیش قبلاً برای یک سفارش دیگر ارسال شده است.</b>\n\n"
            "برای امنیت سیستم، یک فیش تکراری روی چند سفارش پذیرفته نمی‌شود.",
            parse_mode="HTML", reply_markup=main_kb(u.id)
        )
        return

    try:
        with db() as c:
            cur = c.execute(
                "UPDATE orders SET receipt_file_id=?,receipt_unique_id=?,status=?,"
                "rejection_reason=NULL,updated_at=? "
                "WHERE id=? AND user_id=? AND status IN (?,?)",
                (fid, funiq, AWAIT_ADMIN, now(), oid, u.id, AWAIT_RECEIPT, REJECTED)
            )
            if cur.rowcount != 1:
                clear_action(u.id)
                await update.effective_message.reply_text(
                    "⚠️ وضعیت سفارش تغییر کرده؛ دوباره سفارش را باز کن.",
                    reply_markup=main_kb(u.id)
                )
                return
    except sqlite3.IntegrityError:
        audit(u.id, "duplicate_receipt_race_blocked", f"order={oid}")
        await update.effective_message.reply_text(
            "🚫 این فیش قبلاً برای سفارش دیگری ثبت شده است.",
            reply_markup=main_kb(u.id)
        )
        return

    clear_action(u.id)
    audit(u.id, "receipt", str(oid))
    await update.effective_message.reply_text(
        f"✅ فیش سفارش #{oid} دریافت شد و برای ادمین رفت.",
        reply_markup=main_kb(u.id)
    )
    await send_receipt_admin(context, oid)

async def messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    m = update.effective_message
    if not u or not m: return
    upsert_user(u)
    if not await access_ok(update): return
    if rate_limit(context, u.id, "msg", MSG_COOLDOWN): return

    a = get_action(u.id)

    # Regular users may only send text or photos.
    if not is_admin(u.id) and not (m.text or m.photo):
        await m.reply_text(
            "🚫 <b>این نوع فایل قابل ارسال نیست.</b>\n\n"
            "برای جلوگیری از مصرف بی‌مورد منابع، فقط <b>متن</b> و <b>عکس</b> پذیرفته می‌شود.",
            parse_mode="HTML",
            reply_markup=main_kb(u.id),
        )
        return

    if is_admin(u.id) and a:
        if await admin_action(update, context, a):
            return

    if a and a["action"] == "wallet_topup_amount":
        if not m.text:
            await m.reply_text("مبلغ شارژ را فقط به صورت عددی بفرست.")
            return

        amount = to_int(m.text.strip())
        minimum = max(1000, to_int(setting("wallet_min_topup", "50000")) or 50000)
        if amount is None or amount < minimum or amount > 100_000_000:
            await m.reply_text(
                f"❌ مبلغ معتبر نیست. مبلغی بین {money(minimum)} تا {money(100_000_000)} بفرست."
            )
            return

        existing_topup = open_wallet_topup(u.id)
        if existing_topup:
            clear_action(u.id)
            if existing_topup["status"] == "awaiting_receipt":
                set_action(u.id, "wallet_receipt", str(existing_topup["id"]))
                await m.reply_text(
                    f"💳 یک درخواست شارژ باز داری: <b>#{existing_topup['id']}</b>\n"
                    f"مبلغ: <b>{money(existing_topup['amount'])}</b>\n\n"
                    "عکس فیش همان درخواست را ارسال کن.",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup([
                        [user_button("❌ انصراف", callback_data="u:cancel", style="danger")]
                    ])
                )
            else:
                await m.reply_text(
                    f"⏳ درخواست شارژ #{existing_topup['id']} در انتظار تأیید ادمین است.",
                    reply_markup=main_kb(u.id)
                )
            return

        tid = create_wallet_topup(u.id, amount)
        clear_action(u.id)
        set_action(u.id, "wallet_receipt", str(tid))
        await m.reply_text(
            f"💳 <b>شارژ حساب #{tid}</b>\n\n"
            f"💰 مبلغ: <b>{money(amount)}</b>\n"
            f"💳 کارت: <code>{esc(setting('card_number'))}</code>\n"
            f"👤 به نام: <b>{esc(setting('card_holder'))}</b>\n\n"
            "بعد از واریز، عکس فیش را همینجا ارسال کن.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [user_button("❌ انصراف", callback_data="u:cancel", style="danger")]
            ])
        )
        return

    if a and a["action"] == "gift_redeem":
        if not m.text:
            await m.reply_text("کد هدیه را به صورت متن بفرست.")
            return
        code = m.text.strip().upper()
        g = reserve_gift_redeem(u.id, code)
        if not g:
            await m.reply_text("❌ کد هدیه معتبر نیست، قبلاً استفاده شده یا برای کاربر دیگری در حال فعال‌سازی است.")
            return
        ok = await redeem_gift_service(context, g, u.id)
        if ok:
            clear_action(u.id)
            await m.reply_text("✅ هدیه فعال شد و داخل «سرویس‌های من» قابل مشاهده است.", reply_markup=main_kb(u.id))
        else:
            await m.reply_text("❌ فعال‌سازی هدیه کامل نشد. همان کد را دوباره ارسال کن؛ مالکیت رزرو برای خودت حفظ شده است.")
        return

    if a and a["action"] == "coupon":
        if not m.text:
            await m.reply_text("🎟 کد رو به صورت متن بفرست."); return
        oid = to_int(a["payload"] or "")
        if oid is None: clear_action(u.id); return
        ok, msg = apply_coupon(u.id, oid, m.text.strip())
        if ok:
            clear_action(u.id)
            o = get_order(oid)
            await m.reply_text(
                f"✅ {esc(msg)}\n\n{payment_text(o)}",
                parse_mode="HTML", reply_markup=payment_kb(oid)
            )
            audit(u.id, "coupon_use", str(oid))
        else:
            await m.reply_text(f"❌ {msg}\nکد دیگری بفرست یا از دکمه انصراف استفاده کن.")
        return

    if a and a["action"] == "support":
        tid = to_int(a["payload"] or "")
        t = get_ticket(tid) if tid is not None else None
        if not t or t["status"] != "open":
            clear_action(u.id); return
        try:
            await context.bot.send_message(
                ADMIN_USER_ID,
                f"🎫 <b>پیام تیکت #{tid}</b>\n"
                f"👤 {esc(u.full_name)}\n🆔 <code>{u.id}</code>\n"
                f"🔗 {esc(username_text(u.username))}",
                parse_mode="HTML"
            )
            await context.bot.copy_message(
                chat_id=ADMIN_USER_ID, from_chat_id=m.chat_id, message_id=m.message_id
            )
            await context.bot.send_message(
                ADMIN_USER_ID, "مدیریت:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✍️ پاسخ", callback_data=f"a:treply:{tid}")],
                    [InlineKeyboardButton("✅ بستن", callback_data=f"a:tclose:{tid}")],
                ])
            )
            with db() as c:
                c.execute("UPDATE tickets SET updated_at=? WHERE id=?", (now(), tid))
            clear_action(u.id)
            await m.reply_text(f"✅ پیام تیکت #{tid} ارسال شد.", reply_markup=main_kb(u.id))
        except TelegramError:
            await m.reply_text("❌ ارسال پیام پشتیبانی ناموفق بود.")
        return

    if a and a["action"] in {"receipt", "wallet_receipt"}:
        await m.reply_text("📸 عکس فیش رو ارسال کن.")
        return

    await m.reply_text("از دکمه‌های منو استفاده کن 👇", reply_markup=main_kb(u.id))

async def admin_action(update, context, a) -> bool:
    m = update.effective_message
    aid = update.effective_user.id
    name = a["action"]
    payload = a["payload"] or ""

    if name == "user_icon_set":
        slot = payload.strip()
        if slot not in USER_MENU_ICON_SLOTS:
            clear_action(aid)
            await m.reply_text("❌ بخش ایموجی معتبر نیست.")
            return True

        entities = list(m.entities or []) + list(m.caption_entities or [])
        custom_ids = []
        for ent in entities:
            eid = getattr(ent, "custom_emoji_id", None)
            if eid and str(eid) not in custom_ids:
                custom_ids.append(str(eid))

        if custom_ids:
            eid = custom_ids[0]
            try:
                stickers = await context.bot.get_custom_emoji_stickers([eid])
            except TelegramError:
                await m.reply_text("❌ بررسی Custom Emoji ناموفق بود؛ دوباره بفرست.")
                return True
            if not stickers:
                await m.reply_text("❌ این Custom Emoji معتبر نیست.")
                return True
            set_setting(_user_icon_setting_key(slot), f"custom:{eid}")
        else:
            if not m.text:
                await m.reply_text("فقط یک ایموجی معمولی یا Premium Custom Emoji بفرست.")
                return True
            raw = m.text.strip()
            if not raw or len(raw) > 16 or any(ch.isalnum() for ch in raw):
                await m.reply_text("❌ فقط خود ایموجی را بفرست؛ متن یا عدد نفرست.")
                return True
            set_setting(_user_icon_setting_key(slot), f"unicode:{raw}")

        clear_action(aid)
        audit(aid, "user_icon_set", slot)
        await m.reply_text(
            f"✅ ایموجی «{USER_MENU_ICON_SLOTS[slot][0]}» تغییر کرد.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎨 ادامه تنظیم ایموجی‌ها", callback_data="a:usericons")],
                [InlineKeyboardButton("🛡 پنل", callback_data="a:panel")],
            ])
        )
        return True

    if name == "emoji_setup":
        entities = list(m.entities or []) + list(m.caption_entities or [])
        ids = []
        for ent in entities:
            eid = getattr(ent, "custom_emoji_id", None)
            if eid and str(eid) not in ids:
                ids.append(str(eid))

        if not ids:
            await m.reply_text(
                "❌ Custom Emoji پیدا نکردم.\n"
                "از پنل ایموجی تلگرام یک Custom Emoji پریمیوم واقعی بفرست."
            )
            return True

        try:
            stickers = await context.bot.get_custom_emoji_stickers(ids)
        except TelegramError:
            await m.reply_text("❌ بررسی ایموجی‌ها از تلگرام ناموفق بود؛ دوباره امتحان کن.")
            return True

        valid = []
        animated = []
        for st in stickers:
            eid = str(getattr(st, "custom_emoji_id", "") or "")
            if not eid:
                continue
            if eid not in valid:
                valid.append(eid)
            if (
                bool(getattr(st, "is_animated", False))
                or bool(getattr(st, "is_video", False))
            ) and eid not in animated:
                animated.append(eid)

        selected = animated or valid
        if not selected:
            await m.reply_text("❌ هیچ Custom Emoji معتبر و قابل استفاده‌ای پیدا نشد.")
            return True

        set_setting("premium_emoji_pool", ",".join(selected))

        # config.py owns the live Premium Emoji state used by UI validation.
        # Mutate that module explicitly; rebinding wildcard-imported names here would
        # leave config.py unchanged until the next restart.
        cfg.VALID_CUSTOM_EMOJI_IDS.clear()
        cfg.VALID_CUSTOM_EMOJI_IDS.update(valid)
        cfg.ANIMATED_CUSTOM_EMOJI_IDS.clear()
        cfg.ANIMATED_CUSTOM_EMOJI_IDS.update(animated)
        cfg.PREMIUM_EMOJI_POOL[:] = selected

        clear_action(aid)
        audit(aid, "premium_emoji_setup", f"{len(selected)} emojis")

        if animated:
            msg = (
                f"✅ {len(selected)} Custom Emoji متحرک/ویدیویی ذخیره شد.\n"
                "از همین الان کل دکمه‌های ربات از این مجموعه استفاده می‌کنند."
            )
        else:
            msg = (
                f"✅ {len(selected)} Custom Emoji معتبر ذخیره شد.\n"
                "این مجموعه متحرک تشخیص داده نشد، ولی Premium است."
            )

        await m.reply_text(msg, reply_markup=admin_kb())
        return True

    if name == "deliver":
        if not m.text:
            await m.reply_text("کانفیگ رو به صورت متن بفرست."); return True
        oid = to_int(payload)
        o = get_order(oid) if oid is not None else None
        if not o or o["status"] != APPROVED:
            clear_action(aid); await m.reply_text("سفارش قابل تحویل نیست."); return True
        if int(o["is_gift"] or 0):
            ok = await complete_gift_with_config(context, oid, m.text.strip())
        else:
            ok = await send_config(context, o["user_id"], oid, o["plan_title"], m.text.strip())
        if ok:
            await notify_referral_qualified(context, int(o["user_id"]), oid)
            if o["plan_id"]:
                await check_low_stock(context.bot, int(o["plan_id"]))
            clear_action(aid); audit(aid, "manual_deliver", f"{oid}:expires={o['expires_at']}")
            await m.reply_text(f"🎉 سفارش #{oid} تحویل شد.", reply_markup=admin_kb())
        else:
            await m.reply_text("❌ ارسال نشد؛ شاید کاربر ربات رو بلاک کرده.")
        return True

    if name == "reject_custom":
        if not m.text: await m.reply_text("دلیل رو به صورت متن بفرست."); return True
        oid = to_int(payload)
        if oid is not None:
            await reject(context, oid, m.text.strip()[:500])
        clear_action(aid)
        await m.reply_text("❌ سفارش رد شد.", reply_markup=admin_kb())
        return True

    if name == "plan_add":
        if not m.text:
            return True
        parts = [x.strip() for x in m.text.split("|")]
        if len(parts) == 3:
            title, price_s, desc = parts
            duration_s = "30"
        elif len(parts) == 4:
            title, price_s, duration_s, desc = parts
        else:
            await m.reply_text("فرمت: عنوان | قیمت | مدت(روز) | توضیحات")
            return True
        price = to_int(price_s)
        duration = to_int(duration_s)
        if not title or price is None or price < 0 or duration is None or not (1 <= duration <= 3650) or not desc:
            await m.reply_text("اطلاعات معتبر نیست؛ مدت اعتبار باید بین ۱ تا ۳۶۵۰ روز باشد.")
            return True
        n = now()
        with db() as c:
            c.execute(
                "INSERT INTO plans(title,price,description,duration_days,created_at,updated_at) VALUES(?,?,?,?,?,?)",
                (title[:100], price, desc[:1000], duration, n, n)
            )
        clear_action(aid)
        audit(aid, "plan_add", f"{title}:{duration}d")
        await m.reply_text("✅ پلن ساخته شد.", reply_markup=admin_kb())
        return True

    if name.startswith("plan_edit_"):
        pid = to_int(payload)
        if pid is None or not m.text: return True
        field = name.replace("plan_edit_","")
        if field == "price":
            v = to_int(m.text)
            if v is None or v < 0:
                await m.reply_text("قیمت فقط عدد مثبت."); return True
            col, val = "price", v
        elif field == "title":
            col, val = "title", m.text.strip()[:100]
        elif field == "desc":
            col, val = "description", m.text.strip()[:1000]
        elif field == "duration":
            v = to_int(m.text)
            if v is None or not (1 <= v <= 3650):
                await m.reply_text("مدت اعتبار باید عددی بین ۱ تا ۳۶۵۰ روز باشد.")
                return True
            col, val = "duration_days", v
        elif field == "xui_inbounds":
            ids = parse_inbound_ids(m.text)
            if not ids:
                await m.reply_text("حداقل یک Inbound ID معتبر بفرست؛ مثال: 1,2,5")
                return True
            col, val = "xui_inbound_ids", ",".join(str(x) for x in ids)
        elif field == "xui_traffic":
            v = to_int(m.text)
            if v is None or not (0 <= v <= 1000000):
                await m.reply_text("حجم باید عددی بین ۰ تا ۱,۰۰۰,۰۰۰ GB باشد؛ صفر یعنی نامحدود.")
                return True
            col, val = "xui_traffic_gb", v
        elif field == "xui_ip":
            v = to_int(m.text)
            if v is None or not (0 <= v <= 1000):
                await m.reply_text("IP Limit باید بین ۰ تا ۱۰۰۰ باشد؛ صفر یعنی بدون محدودیت.")
                return True
            col, val = "xui_ip_limit", v
        else:
            clear_action(aid); return True
        with db() as c:
            c.execute(f"UPDATE plans SET {col}=?,updated_at=? WHERE id=?", (val, now(), pid))
        clear_action(aid); audit(aid, "plan_edit", f"{pid}:{field}")
        await m.reply_text("✅ پلن ویرایش شد.", reply_markup=admin_kb()); return True

    if name == "test_stock_add":
        if not m.text:
            await m.reply_text("کانفیگ‌ها را به صورت متن بفرست؛ هر خط یک کانفیگ.")
            return True

        configs = [x.strip() for x in m.text.splitlines() if x.strip()]
        n = add_test_stock(configs)
        set_setting("test_low_stock_alerted", "0")
        await check_test_low_stock(context.bot)
        clear_action(aid)
        audit(aid, "test_stock_add", str(n))
        await m.reply_text(
            f"✅ {n} کانفیگ تست اضافه شد.\n"
            f"📦 موجودی فعلی تست: {test_stock_count()}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🧪 مدیریت تست", callback_data="a:teststock")],
                [InlineKeyboardButton("🛡 پنل مدیریت", callback_data="a:panel")],
            ])
        )
        return True

    if name == "stock_add":
        pid = to_int(payload)
        if pid is None or not m.text: return True
        configs = [x.strip() for x in m.text.splitlines() if x.strip()]
        n = add_stock(pid, configs)
        await check_low_stock(context.bot, pid)
        clear_action(aid); audit(aid, "stock_add", f"{pid}:{n}")
        await m.reply_text(
            f"⚡ {n} کانفیگ اضافه شد. موجودی فعلی: {stock_count(pid)}",
            reply_markup=admin_kb()
        ); return True

    if name == "coupon_add":
        if not m.text: return True
        p = [x.strip() for x in m.text.split("|")]
        if len(p) != 4:
            await m.reply_text("فرمت: CODE | percent/fixed | value | max_uses"); return True
        code, kind, val_s, max_s = p
        code = code.upper().replace(" ","")[:30]
        val, maxu = to_int(val_s), to_int(max_s)
        if not re.fullmatch(r"[A-Z0-9_-]{2,30}", code):
            await m.reply_text("کد نامعتبر."); return True
        if kind not in {"percent","fixed"} or val is None or val <= 0 or maxu is None or maxu < 0:
            await m.reply_text("مقادیر نامعتبر."); return True
        if kind == "percent" and val > 100:
            await m.reply_text("درصد حداکثر 100."); return True
        try:
            with db() as c:
                c.execute(
                    "INSERT INTO coupons(code,kind,value,max_uses,created_at) VALUES(?,?,?,?,?)",
                    (code, kind, val, maxu, now())
                )
        except sqlite3.IntegrityError:
            await m.reply_text("این کد قبلاً هست."); return True
        clear_action(aid); audit(aid, "coupon_add", code)
        await m.reply_text("✅ کد ساخته شد.", reply_markup=admin_kb()); return True

    if name == "target_broadcast":
        segment = payload
        ids = segment_user_ids(segment)
        clear_action(aid)
        if not ids:
            await m.reply_text("این سگمنت دیگر کاربری ندارد.", reply_markup=admin_kb())
            return True
        context.application.create_task(
            broadcast_to_ids(update, context, ids, segment),
            update=update,
            name=f"target-broadcast-{segment}",
        )
        await m.reply_text("✅ ارسال در پس‌زمینه شروع شد؛ می‌تونی هم‌زمان از ربات استفاده کنی.", reply_markup=admin_kb())
        return True

    if name == "wallet_adjust":
        uid = to_int(payload)
        if uid is None or not get_user(uid) or not m.text:
            return True
        parts = [x.strip() for x in m.text.split("|", 1)]
        amount = to_int(parts[0])
        note = parts[1] if len(parts)>1 else "تغییر دستی ادمین"
        if amount is None or amount == 0 or abs(amount)>100_000_000:
            await m.reply_text("مبلغ معتبر نیست.")
            return True
        ok,new=change_wallet(uid,amount,"admin_adjust",reference_type="admin",reference_id=aid,note=note,allow_negative=False)
        if not ok:
            await m.reply_text("موجودی برای این کاهش کافی نیست یا کاربر پیدا نشد.")
            return True
        clear_action(aid); audit(aid,"wallet_adjust",f"user={uid};amount={amount}")
        await m.reply_text(f"✅ کیف پول تغییر کرد. موجودی جدید: {money(new)}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("👤 پروفایل",callback_data=f"a:user:{uid}")]]))
        try: await context.bot.send_message(uid,f"💳 موجودی کیف پول شما تغییر کرد.\nموجودی جدید: <b>{money(new)}</b>",parse_mode="HTML")
        except TelegramError: pass
        return True

    if name == "global_search":
        if not m.text:
            await m.reply_text("عبارت جستجو را بفرست.")
            return True
        term=m.text.strip()
        result=global_search(term)
        clear_action(aid)
        lines=[f"🔍 <b>جستجوی سراسری:</b> <code>{esc(term[:100])}</code>\n"]
        buttons=[]
        for urow in result["users"][:5]:
            lines.append(f"\n👤 {esc(urow['full_name'])} • <code>{urow['user_id']}</code> • {esc(username_text(urow['username']))}")
            buttons.append([InlineKeyboardButton(f"👤 {urow['full_name']}",callback_data=f"a:user:{urow['user_id']}")])
        for o in result["orders"][:5]:
            lines.append(f"\n🧾 سفارش #{o['id']} • کاربر <code>{o['user_id']}</code> • {esc(o['plan_title'])} • {STATUS.get(o['status'],o['status'])}")
            buttons.append([InlineKeyboardButton(f"🧾 سفارش #{o['id']}",callback_data=f"a:order:{o['id']}")])
        for cp in result["coupons"][:5]:
            lines.append(f"\n🎟 کد: <code>{esc(cp['code'])}</code> • استفاده {cp['used_count']}/{cp['max_uses'] or '∞'}")
            buttons.append([InlineKeyboardButton(f"🎟 {cp['code']}",callback_data=f"a:coupon:{cp['id']}")])
        for cfg in result["configs"][:5]:
            lines.append(f"\n🔐 {esc(cfg['plan_title'] or 'کانفیگ')} • {esc(cfg['status'])} • <code>{esc(_config_preview(cfg['config'],70))}</code>")
        if len(lines)==1: lines.append("\nنتیجه‌ای پیدا نشد.")
        buttons.append([InlineKeyboardButton("🛡 پنل",callback_data="a:panel")])
        await m.reply_text(premium_html("\n".join(lines)),parse_mode="HTML",reply_markup=InlineKeyboardMarkup(buttons[:16]))
        return True

    if name == "config_search":
        if not m.text:
            await m.reply_text("حداقل ۴ کاراکتر از کانفیگ را بفرست.")
            return True

        term = m.text.strip()
        if len(term) < 4:
            await m.reply_text("عبارت جستجو باید حداقل ۴ کاراکتر باشد.")
            return True

        results = search_config_records(term)
        clear_action(aid)

        if not results:
            await m.reply_text("🔎 نتیجه‌ای پیدا نشد.", reply_markup=admin_kb())
            return True

        lines = [f"🔎 <b>نتیجه جستجو:</b> <code>{esc(term[:80])}</code>\n"]
        buttons = []

        for idx, r in enumerate(results[:15], 1):
            status_map = {
                "available": "🟢 آزاد",
                "reserved": "🟡 رزرو",
                "used": "🔐 مصرف‌شده",
            }
            status = status_map.get(str(r["status"]), esc(r["status"]))
            lines.append(
                f"\n<b>{idx}.</b> {status} • {esc(r['plan_title'] or '—')}\n"
                f"👤 {esc(r['full_name'] or '—')}"
                + (f" • <code>{r['user_id']}</code>" if r["user_id"] else "")
                + f"\n<code>{esc(_config_preview(r['config'], 90))}</code>"
            )

            if r["kind"] == "normal" and r["status"] == "available":
                buttons.append([InlineKeyboardButton(
                    f"🔐 نتیجه {idx}",
                    callback_data=f"a:stockitem:{r['plan_id']}:{r['inventory_id']}:0"
                )])
            elif r["kind"] in {"normal", "manual"} and r["order_id"]:
                buttons.append([InlineKeyboardButton(
                    f"🧾 نتیجه {idx} • سفارش #{r['order_id']}",
                    callback_data=f"a:deliveryitem:{r['order_id']}:0"
                )])
            elif r["kind"] == "test" and r["status"] == "available":
                buttons.append([InlineKeyboardButton(
                    f"🧪 نتیجه {idx}",
                    callback_data=f"a:testitem:{r['inventory_id']}:0"
                )])
            elif r["kind"] == "test" and r["user_id"]:
                buttons.append([InlineKeyboardButton(
                    f"🧪 نتیجه {idx} • تحویل تست",
                    callback_data=f"a:testdeliveryitem:{r['user_id']}:0"
                )])

        buttons.append([InlineKeyboardButton("🛡 پنل مدیریت", callback_data="a:panel")])
        await m.reply_text(
            premium_html("\n".join(lines)),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(buttons[:16])
        )
        return True

    if name == "user_note":
        uid = to_int(payload)
        if uid is None or not get_user(uid):
            clear_action(aid)
            await m.reply_text("کاربر پیدا نشد.")
            return True

        if not m.text:
            await m.reply_text("یادداشت را به صورت متن بفرست.")
            return True

        value = m.text.strip()
        if value == "-":
            value = ""

        set_user_note(uid, value)
        clear_action(aid)
        audit(aid, "user_note_set", f"{uid}:{'saved' if value else 'deleted'}")

        await m.reply_text(
            "✅ یادداشت ذخیره شد." if value else "🗑 یادداشت پاک شد.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("👤 پروفایل کاربر", callback_data=f"a:user:{uid}")],
                [InlineKeyboardButton("🛡 پنل", callback_data="a:panel")],
            ])
        )
        return True

    if name == "user_search":
        if not m.text: return True
        u = find_user(m.text)
        if not u:
            await m.reply_text("❌ کاربر پیدا نشد. دوباره بفرست یا /cancel."); return True
        clear_action(aid)
        await m.reply_text(
            "✅ پیدا شد:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(f"👤 {u['full_name']} • {u['user_id']}", callback_data=f"a:user:{u['user_id']}")
            ]])
        ); return True

    if name == "setting":
        if not m.text or not m.text.strip():
            return True

        allowed = {
            "shop_name", "card_number", "card_holder", "support_username", "welcome_text",
            "unpaid_order_expiry_hours", "test_low_stock_threshold",
            "lost_customer_days", "vip_min_purchases",
        }
        if payload not in allowed:
            clear_action(aid)
            return True

        raw = m.text.strip()

        if payload == "unpaid_order_expiry_hours":
            value = to_int(raw)
            if value is None or not (0 <= value <= 8760):
                await m.reply_text("عدد بین ۰ تا ۸۷۶۰ بفرست. ۰ یعنی خاموش.")
                return True
            raw = str(value)

        if payload in {"lost_customer_days", "vip_min_purchases"}:
            value = to_int(raw)
            if value is None or not (1 <= value <= 3650):
                await m.reply_text("یک عدد معتبر بین ۱ تا ۳۶۵۰ بفرست.")
                return True
            raw = str(value)

        if payload == "test_low_stock_threshold":
            value = to_int(raw)
            if value is None or not (0 <= value <= 10000):
                await m.reply_text("حد هشدار باید عددی بین ۰ تا ۱۰۰۰۰ باشد.")
                return True
            raw = str(value)
            set_setting("test_low_stock_alerted", "0")

        set_setting(payload, raw[:1500])
        clear_action(aid)
        audit(aid, "setting", payload)
        await m.reply_text("✅ تنظیم ذخیره شد.", reply_markup=admin_kb())
        return True

    if name == "ticket_reply":
        tid = to_int(payload)
        t = get_ticket(tid) if tid is not None else None
        if not t or t["status"] != "open":
            clear_action(aid); await m.reply_text("تیکت بسته است."); return True
        try:
            await context.bot.send_message(t["user_id"], f"💬 <b>پاسخ پشتیبانی • تیکت #{tid}</b>", parse_mode="HTML")
            await context.bot.copy_message(
                chat_id=t["user_id"], from_chat_id=m.chat_id, message_id=m.message_id
            )
            await context.bot.send_message(t["user_id"], "برای پیام جدید دوباره وارد پشتیبانی شو.", reply_markup=main_kb(t["user_id"]))
        except TelegramError:
            await m.reply_text("❌ ارسال پاسخ ناموفق بود."); return True
        with db() as c:
            c.execute("UPDATE tickets SET updated_at=? WHERE id=?", (now(), tid))
        clear_action(aid); audit(aid, "ticket_reply", str(tid))
        await m.reply_text("✅ پاسخ ارسال شد.", reply_markup=admin_kb()); return True

    if name == "broadcast":
        clear_action(aid)
        context.application.create_task(
            broadcast(update, context),
            update=update,
            name="admin-broadcast",
        )
        await m.reply_text("✅ ارسال همگانی در پس‌زمینه شروع شد؛ پنل قفل نمی‌شود.", reply_markup=admin_kb())
        return True

    return False

async def broadcast(update, context):
    async with _broadcast_lock(context):
        m = update.effective_message
        with db() as c:
            ids = [
                r["user_id"] for r in c.execute(
                    "SELECT user_id FROM users WHERE is_blocked=0 ORDER BY user_id"
                ).fetchall()
            ]

        status = await m.reply_text(f"📢 ارسال به {len(ids)} کاربر شروع شد...")
        ok = fail = 0

        for i, uid in enumerate(ids, 1):
            sent = await copy_message_with_retry(
                context.bot,
                chat_id=uid,
                from_chat_id=m.chat_id,
                message_id=m.message_id,
            )
            if sent:
                ok += 1
            else:
                fail += 1

            await asyncio.sleep(0.08)

            if i % 50 == 0:
                try:
                    await status.edit_text(f"📢 {i}/{len(ids)}\n✅ {ok} • ❌ {fail}")
                except TelegramError:
                    pass

        try:
            await status.edit_text(f"✅ تمام شد.\nموفق: {ok}\nناموفق: {fail}")
        except TelegramError:
            pass

        audit(ADMIN_USER_ID, "broadcast", f"{ok}/{fail}")
        await m.reply_text("🛡 پنل مدیریت", reply_markup=admin_kb())

