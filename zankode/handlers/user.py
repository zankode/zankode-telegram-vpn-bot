# -*- coding: utf-8 -*-
"""User callback-query flows."""

from ..config import *
from ..utils import *
from ..storage import *
from ..ui import *
from ..services import *

async def user_callback(q, context, data: str):
    uid = q.from_user.id

    if data == "u:home":
        clear_action(uid)
        await edit(q, f"🌐 <b>{esc(setting('shop_name'))}</b>\n\nیکی از گزینه‌ها رو انتخاب کن:", main_kb(uid))
        return

    if data == "u:cancel":
        clear_action(uid)
        await edit(q, "✅ عملیات لغو شد.\n\nاز منوی اصلی ادامه بده:", main_kb(uid))
        return

    if data == "u:wallet":
        bal = wallet_balance(uid)
        txs = wallet_transactions(uid, 8)
        lines = [
            "💳 <b>حساب Zankode VPN</b>",
            f"\n💰 موجودی فعلی: <b>{money(bal)}</b>",
        ]
        if txs:
            lines.append("\n🕘 <b>آخرین تراکنش‌ها:</b>")
            for tx in txs:
                sign = "+" if int(tx["amount"]) >= 0 else ""
                lines.append(
                    f"{sign}{money(tx['amount'])} • {esc(tx['tx_type'])} • {esc(tx['created_at'])}"
                )

        await edit(
            q,
            "\n".join(lines),
            InlineKeyboardMarkup([
                [user_button("➕ شارژ حساب", callback_data="u:wtopupmenu", style="success")],
                [user_menu_button("home", "منوی اصلی", callback_data="u:home", style="danger")],
            ])
        )
        return

    if data == "u:wtopupmenu":
        minimum = max(1000, to_int(setting("wallet_min_topup", "50000")) or 50000)
        await edit(
            q,
            "➕ <b>شارژ حساب</b>\n\n"
            f"حداقل مبلغ شارژ: <b>{money(minimum)}</b>\n"
            "یک مبلغ آماده انتخاب کن یا مبلغ دلخواهت رو وارد کن:",
            InlineKeyboardMarkup([
                [
                    user_button("50 هزار", callback_data="u:wtopup:50000", style="success"),
                    user_button("100 هزار", callback_data="u:wtopup:100000", style="success"),
                ],
                [
                    user_button("200 هزار", callback_data="u:wtopup:200000", style="success"),
                    user_button("500 هزار", callback_data="u:wtopup:500000", style="success"),
                ],
                [user_button("✍️ مبلغ دلخواه", callback_data="u:wtopupcustom", style="primary")],
                [user_menu_button("wallet", "بازگشت به کیف پول", callback_data="u:wallet", style="danger")],
            ])
        )
        return

    if data == "u:wtopupcustom":
        set_action(uid, "wallet_topup_amount")
        minimum = max(1000, to_int(setting("wallet_min_topup", "50000")) or 50000)
        await edit(
            q,
            "✍️ <b>مبلغ دلخواه شارژ</b>\n\n"
            f"مبلغ را فقط به تومان بفرست.\nحداقل: <b>{money(minimum)}</b>\n\n"
            "مثال: <code>350000</code>",
            InlineKeyboardMarkup([
                [user_button("❌ انصراف", callback_data="u:cancel", style="danger")]
            ])
        )
        return

    if data.startswith("u:wtopup:"):
        amount = to_int(data.rsplit(":", 1)[1])
        minimum = max(1000, to_int(setting("wallet_min_topup", "50000")) or 50000)
        if amount is None or amount < minimum or amount > 100_000_000:
            await answer(q, "مبلغ شارژ معتبر نیست.", True)
            return
        existing_topup = open_wallet_topup(uid)
        if existing_topup:
            if existing_topup["status"] == "awaiting_receipt":
                set_action(uid, "wallet_receipt", str(existing_topup["id"]))
                await edit(
                    q,
                    f"💳 <b>درخواست شارژ باز #{existing_topup['id']}</b>\n\n"
                    f"💰 مبلغ: <b>{money(existing_topup['amount'])}</b>\n"
                    f"💳 کارت: <code>{esc(setting('card_number'))}</code>\n\n"
                    "عکس فیش را همینجا ارسال کن.",
                    InlineKeyboardMarkup([[user_button("❌ انصراف", callback_data="u:cancel", style="danger")]])
                )
            else:
                await answer(q, f"درخواست شارژ #{existing_topup['id']} در انتظار تأیید ادمین است.", True)
            return
        if wallet_topup_open_count(uid) >= 2:
            await answer(q, "درخواست شارژ باز زیادی داری.", True)
            return
        tid = create_wallet_topup(uid, amount)
        set_action(uid, "wallet_receipt", str(tid))
        await edit(
            q,
            f"💳 <b>شارژ کیف پول #{tid}</b>\n\n"
            f"💰 مبلغ: <b>{money(amount)}</b>\n"
            f"💳 کارت: <code>{esc(setting('card_number'))}</code>\n"
            f"👤 به نام: <b>{esc(setting('card_holder'))}</b>\n\n"
            "بعد از واریز، عکس فیش را همینجا بفرست.",
            InlineKeyboardMarkup([[user_button("❌ انصراف", callback_data="u:cancel", style="danger")]])
        )
        return

    if data == "u:vip":
        await edit(
            q,
            "👑 <b>باشگاه مشتریان Zankode VPN</b>\n\n" + vip_progress_text(uid) +
            "\n\nسطح‌بندی بر اساس خریدهای موفق شماست. ادمین می‌تواند برای VIPها پیام‌ها، کمپین‌ها و مزایای اختصاصی اجرا کند.",
            InlineKeyboardMarkup([
                [user_button("🛒 خرید سرویس", callback_data="u:plans", style="success")],
                [user_button("🏠 منوی اصلی", callback_data="u:home", style="danger")],
            ])
        )
        return

    if data == "u:gift":
        set_action(uid, "gift_redeem")
        await edit(
            q,
            "🎁 <b>دریافت هدیه</b>\n\nکد هدیه Zankode VPN را ارسال کن.",
            InlineKeyboardMarkup([[user_button("❌ انصراف", callback_data="u:cancel", style="danger")]])
        )
        return

    if data.startswith("u:invoice:"):
        oid = to_int(data.rsplit(":", 1)[1])
        o = get_order(oid) if oid is not None else None
        if not o or int(o["user_id"]) != uid or o["status"] != COMPLETED:
            await answer(q, "فاکتور قابل نمایش نیست.", True)
            return
        await edit(q, invoice_text(o), InlineKeyboardMarkup([
            [user_button("↩️ سفارش", callback_data=f"u:order:{oid}", style="danger")]
        ]))
        return

    if data == "u:test":
        old_claim = get_test_claim(uid)
        if old_claim:
            await edit(
                q,
                "🧪 <b>اکانت تست 50MB شما</b>\n\n"
                "تست قبلاً برای این حساب صادر شده است:\n\n"
                f"<code>{esc(old_claim['config_text'])}</code>\n\n"
                "🔒 هر حساب تلگرام فقط یک بار تست دریافت می‌کند.",
                InlineKeyboardMarkup([
                    [user_button("🛍️ خرید سرویس", callback_data="u:plans", style="success")],
                    [user_button("🏠 منوی اصلی", callback_data="u:home", style="danger")],
                ])
            )
            return

        review = get_test_review(uid)
        if review and review["status"] == "pending":
            await edit(
                q,
                "🛡️ <b>درخواست تست شما در حال بررسی است</b>\n\n"
                "برای جلوگیری از دریافت چندباره تست با چند حساب، "
                "این درخواست نیاز به تأیید دستی ادمین دارد.\n"
                "بعد از تأیید، اکانت تست برای شما ارسال می‌شود.",
                home_kb()
            )
            return

        if review and review["status"] == "rejected":
            await edit(
                q,
                "⛔ <b>درخواست اکانت تست تأیید نشد.</b>\n\n"
                "این محدودیت فقط مربوط به تست رایگان است و روی خرید سرویس اثری ندارد.",
                InlineKeyboardMarkup([
                    [user_button("🆘 پشتیبانی", callback_data="u:support", style="danger")],
                    [user_button("🏠 منوی اصلی", callback_data="u:home", style="danger")],
                ])
            )
            return

        risk_reason = automatic_test_risk_reason(uid)
        if risk_reason:
            created = ensure_test_review(uid, risk_reason)
            urow = get_user(uid)

            if created:
                try:
                    await context.bot.send_message(
                        ADMIN_USER_ID,
                        premium_html(
                            "🚨 <b>درخواست تست نیازمند تأیید</b>\n\n"
                            f"👤 کاربر: <b>{esc(urow['full_name'] if urow else uid)}</b>\n"
                            f"🆔 <code>{uid}</code>\n"
                            f"🔗 {esc(username_text(urow['username'] if urow else ''))}\n\n"
                            f"⚠️ دلیل بررسی: {esc(risk_reason)}\n\n"
                            "هیچ کانفیگ تستی هنوز مصرف نشده است."
                        ),
                        parse_mode="HTML",
                        reply_markup=InlineKeyboardMarkup([
                            [
                                InlineKeyboardButton("✅ تأیید تست", callback_data=f"a:testapprove:{uid}", style="success"),
                                InlineKeyboardButton("❌ رد تست", callback_data=f"a:testreject:{uid}", style="danger"),
                            ],
                            [InlineKeyboardButton("👤 پروفایل کاربر", callback_data=f"a:user:{uid}")],
                        ])
                    )
                except TelegramError:
                    pass

            await edit(
                q,
                "🛡️ <b>اکانت تست شما نیاز به تأیید ادمین دارد</b>\n\n"
                "برای جلوگیری از سوءاستفاده و دریافت تست با چند حساب، "
                "این درخواست برای بررسی دستی ارسال شد.\n"
                "در صورت تأیید، تست برای شما ارسال می‌شود.",
                home_kb()
            )
            return

        if test_stock_count() <= 0:
            await edit(
                q,
                "🧪 <b>اکانت تست 50MB</b>\n\nفعلاً اکانت تست نداریم.",
                InlineKeyboardMarkup([
                    [user_button("🔄 بررسی موجودی", callback_data="u:test", style="primary")],
                    [user_button("🏠 منوی اصلی", callback_data="u:home", style="danger")],
                ])
            )
            return

        config = pop_test_stock_for_user(uid)
        if not config:
            await edit(q, "🧪 <b>اکانت تست 50MB</b>\n\nفعلاً اکانت تست نداریم.", home_kb())
            return

        audit(uid, "test_account_claim", "instant_one_per_telegram_id")
        await check_test_low_stock(context.bot)
        await edit(
            q,
            "🎉 <b>اکانت تست 50MB شما آماده شد</b>\n\n"
            "🔐 کانفیگ تست:\n"
            f"<code>{esc(config)}</code>\n\n"
            "این تست فقط یک‌بار برای هر حساب صادر می‌شود.",
            InlineKeyboardMarkup([
                [user_button("🛍️ خرید سرویس", callback_data="u:plans", style="success")],
                [user_button("🏠 منوی اصلی", callback_data="u:home", style="danger")],
            ])
        )
        return

    if data == "u:account":
        await edit(
            q,
            account_text(q.from_user),
            account_kb(),
        )
        return

    if data == "u:services":
        services = delivered_services(uid)
        gifts = received_gifts(uid)
        if not services and not gifts:
            await edit(
                q,
                "💎 <b>سرویس‌های فعال شما</b>\n\n"
                "در حال حاضر هیچ سرویس تحویل‌شده‌ای در حساب شما ثبت نشده است.",
                InlineKeyboardMarkup([
                    [user_button("🛒 خرید سرویس", callback_data="u:plans", style="primary", icon_custom_emoji_id=CUSTOM_EMOJI_SHOP_ID)],
                    [user_button("🏠 منوی اصلی", callback_data="u:home", style="danger", icon_custom_emoji_id=CUSTOM_EMOJI_HOME_ID)],
                ])
            )
            return
        rows = []
        active_n = 0
        for o in services:
            exp = parse_db_dt(o["expires_at"])
            active = bool(exp and exp > iran_now() and service_state(o) == "فعال ✅")
            active_n += int(active)
            tail = f"تا {jalali_date(exp)}" if exp else "تحویل‌شده"
            rows.append([
                user_button(
                    f"💎 #{o['id']} • {o['plan_title']} • {tail}",
                    callback_data=f"u:order:{o['id']}",
                    style="success" if active else "danger",
                    icon_custom_emoji_id=CUSTOM_EMOJI_SERVICE_ID,
                )
            ])
        for g in gifts:
            exp = parse_db_dt(g["expires_at"])
            remote_ok = str(g["xui_remote_status"] or "active") == "active"
            active = bool(exp and exp > iran_now() and remote_ok)
            active_n += int(active)
            tail = f"تا {jalali_date(exp)}" if exp else "هدیه"
            rows.append([
                user_button(
                    f"🎁 هدیه • {g['plan_title']} • {tail}",
                    callback_data=f"u:giftservice:{g['id']}",
                    style="success" if active else "danger",
                    icon_custom_emoji_id=CUSTOM_EMOJI_COUPON_ID,
                )
            ])
        rows.append([user_button("🏠 منوی اصلی", callback_data="u:home", style="danger", icon_custom_emoji_id=CUSTOM_EMOJI_HOME_ID)])
        await edit(
            q,
            "💎 <b>سرویس‌های شما</b>\n\n"
            f"🟢 فعال: <b>{active_n}</b> • خریدهای خودت: <b>{len(services)}</b> • هدیه دریافتی: <b>{len(gifts)}</b>\n"
            "برای مشاهده جزئیات، سرویس را انتخاب کنید:",
            InlineKeyboardMarkup(rows)
        )
        return

    if data.startswith("u:giftservice:"):
        gid = to_int(data.rsplit(":", 1)[1])
        g = received_gift(gid, uid) if gid is not None else None
        if not g:
            await answer(q, "هدیه پیدا نشد.", True)
            return
        gift_rows = []
        if xui_service_for_order(int(g["order_id"])):
            gift_rows.append([user_button("🔄 وضعیت لحظه‌ای سرویس", callback_data=f"u:xui:{g['order_id']}", style="primary")])
        gift_rows += [
            [user_button("🛒 خرید سرویس", callback_data="u:plans", style="success")],
            [user_button("↩️ سرویس‌های من", callback_data="u:services", style="danger")],
        ]
        gift_kb = InlineKeyboardMarkup(gift_rows)
        gift_config = str(g["delivered_config"] or "")
        if len(gift_config) > 1800:
            try:
                await send_protected_credential(
                    context.bot,
                    uid,
                    "🎁 <b>سرویس هدیه دریافتی</b>\n"
                    f"📦 {esc(g['plan_title'])}\n"
                    f"📅 پایان اعتبار: <b>{jalali_date(g['expires_at'])}</b>",
                    gift_config,
                    f"zankode_gift_{g['id']}.txt",
                    reply_markup=gift_kb,
                )
            except TelegramError:
                await answer(q, "ارسال کانفیگ ناموفق بود؛ دوباره تلاش کن.", True)
            return
        await edit(
            q,
            "🎁 <b>سرویس هدیه دریافتی</b>\n\n"
            f"📦 {esc(g['plan_title'])}\n"
            f"📅 پایان اعتبار: <b>{jalali_date(g['expires_at'])}</b>\n\n"
            "🔐 کانفیگ:\n"
            f"<code>{esc(gift_config)}</code>",
            gift_kb,
        )
        return

    if data == "u:referral":
        s = referral_wallet_stats(uid)
        bot_username = context.bot.username
        if not bot_username:
            me = await context.bot.get_me()
            bot_username = me.username

        percent = min(100, max(0, to_int(setting("referral_commission_percent", "10")) or 10))
        buyer_bonus = max(0, to_int(setting("referral_buyer_bonus", "10000")) or 10000)
        ref_link = f"https://t.me/{bot_username}?start=ref_{uid}"
        share_url = (
            "https://t.me/share/url?url="
            + quote(ref_link, safe="")
            + "&text="
            + quote(
                f"با لینک من بیا Zankode VPN؛ بعد از اولین خرید {buyer_bonus:,} تومان هدیه کیف پول می‌گیری 👇",
                safe=""
            )
        )

        text_ref = (
            "🎁 <b>رفیقات رو دعوت کن، کیف پولت شارژ می‌شه</b>\n\n"
            f"هر رفیقی که با لینک اختصاصی تو وارد Zankode VPN بشه و خرید موفق انجام بده، "
            f"<b>{percent}٪ مبلغ خریدش</b> مستقیم به کیف پول تو اضافه می‌شه. 💳\n\n"
            f"🎉 خود رفیقت هم روی <b>اولین خرید موفق</b> "
            f"<b>{money(buyer_bonus)}</b> هدیه داخل کیف پولش می‌گیره.\n\n"
            f"👥 دعوت‌شده‌ها: <b>{s['invited']}</b>\n"
            f"🛒 دوستان خریدار: <b>{s['buyers']}</b>\n"
            f"✅ خریدهای پورسانت‌دار: <b>{s['orders']}</b>\n"
            f"💰 درآمد دعوت شما: <b>{money(s['earned'])}</b>\n"
            f"💳 موجودی فعلی کیف پول: <b>{money(wallet_balance(uid))}</b>\n\n"
            "🔗 <b>لینک اختصاصی شما:</b>\n"
            f"<code>{esc(ref_link)}</code>"
        )

        await edit(
            q,
            text_ref,
            InlineKeyboardMarkup([
                [InlineKeyboardButton("📨 فرستادن لینک برای رفیق", url=share_url, style="primary")],
                [user_menu_button("wallet", "مشاهده کیف پول", callback_data="u:wallet", style="success")],
                [user_menu_button("home", "منوی اصلی", callback_data="u:home", style="danger")],
            ])
        )
        return

    if data == "u:refclaim":
        await edit(
            q,
            "🎁 <b>سیستم دعوت Zankode VPN تغییر کرده</b>\n\n"
            "از این به بعد جایزه دعوت به‌صورت خودکار داخل کیف پول واریز می‌شود؛ "
            "نیازی به دریافت کد جایزه نیست.",
            InlineKeyboardMarkup([
                [user_menu_button("referral", "دعوت دوستان", callback_data="u:referral", style="success")],
                [user_menu_button("wallet", "کیف پول", callback_data="u:wallet", style="primary")],
            ])
        )
        return

    if data == "u:refrewards":
        rewards = referral_reward_rows(uid)
        if not rewards:
            await edit(
                q,
                "🏆 <b>جایزه‌های من</b>\n\nهنوز کد جایزه‌ای دریافت نکردی.",
                InlineKeyboardMarkup([
                    [user_button("🎁 دعوت دوستان", callback_data="u:referral", style="success")],
                    [user_button("🏠 منوی اصلی", callback_data="u:home", style="danger", icon_custom_emoji_id=CUSTOM_EMOJI_HOME_ID)],
                ])
            )
            return

        lines = ["🏆 <b>جایزه‌های من</b>\n"]
        for r in rewards[:10]:
            state = "✅ استفاده‌شده" if r["used_at"] else "🎟 آماده استفاده"
            lines.append(
                f"\nمرحله {r['milestone']} • {state}\n"
                f"<code>{esc(r['coupon_code'])}</code>"
            )

        await edit(
            q,
            "\n".join(lines),
            InlineKeyboardMarkup([
                [user_button("🎁 دعوت دوستان", callback_data="u:referral", style="success")],
                [user_button("🛒 خرید سرویس", callback_data="u:plans", style="primary")],
                [user_button("🏠 منوی اصلی", callback_data="u:home", style="danger", icon_custom_emoji_id=CUSTOM_EMOJI_HOME_ID)],
            ])
        )
        return

    if data == "u:plans":
        if not active_plans():
            await edit(q, "📭 فعلاً پلن فعالی نداریم.", home_kb())
            return
        await edit(q, "🛒 <b>انتخاب سرویس</b>\n\nپلن موردنظرت رو انتخاب کن:", plans_kb())
        return

    if data.startswith("u:plan:"):
        pid = to_int(data.rsplit(":", 1)[1])
        p = get_plan(pid) if pid is not None else None
        if not p or not p["is_active"]:
            await answer(q, "پلن معتبر نیست.", True)
            return
        instant = stock_count(pid) > 0 and setting_on("auto_delivery")
        await edit(
            q,
            f"💎 <b>{esc(p['title'])}</b>\n\n"
            f"💰 قیمت: <b>{money(p['price'])}</b>\n"
            f"📅 اعتبار: <b>{int(p['duration_days'] or 30)} روز</b>\n"
            f"📝 {esc(p['description'])}\n"
            f"⚡ تحویل: {'فوری بعد از تأیید' if instant else 'پس از تأیید ادمین'}",
            InlineKeyboardMarkup([
                [user_button("✅ ثبت سفارش", callback_data=f"u:buy:{pid}", style="success", icon_custom_emoji_id=CUSTOM_EMOJI_SHOP_ID)],
                [user_button("🎁 خرید این سرویس برای هدیه", callback_data=f"u:giftbuy:{pid}", style="primary")],
                [user_button("↩️ بازگشت به پلن‌ها", callback_data="u:plans", style="danger")],
            ])
        )
        return

    if data.startswith("u:giftbuy:"):
        if rate_limit(context, uid, "order_create", ORDER_CREATE_COOLDOWN):
            await answer(q, "چند ثانیه صبر کن.", True)
            return
        pid = to_int(data.rsplit(":", 1)[1])
        p = get_plan(pid) if pid is not None else None
        if not p or not p["is_active"]:
            await answer(q, "پلن معتبر نیست.", True)
            return
        if count_open_orders(uid) >= MAX_OPEN_ORDERS_PER_USER:
            await answer(q, f"حداکثر {MAX_OPEN_ORDERS_PER_USER} سفارش باز مجاز است.", True)
            return
        purchase_dt, time_source = await time_ir_now()
        oid = create_order(uid, p, purchase_dt, time_source, is_gift=True)
        o = get_order(oid)
        audit(uid, "gift_order_create", f"order={oid}")
        await edit(
            q,
            "🎁 <b>سفارش هدیه ثبت شد</b>\n\nبعد از پرداخت، کانفیگ برای خودت نمایش داده نمی‌شود؛ یک کد هدیه دریافت می‌کنی که به شخص موردنظر می‌فرستی.\n\n" + payment_text(o),
            payment_kb(oid)
        )
        return

    if data.startswith("u:buy:"):
        if rate_limit(context, uid, "order_create", ORDER_CREATE_COOLDOWN):
            await answer(q, "چند ثانیه صبر کن و دوباره تلاش کن.", True)
            return

        pid = to_int(data.rsplit(":", 1)[1])
        p = get_plan(pid) if pid is not None else None
        if not p or not p["is_active"]:
            await answer(q, "پلن معتبر نیست.", True)
            return

        existing = reusable_open_order(uid, int(pid))
        if existing:
            await edit(
                q,
                "🧾 <b>برای همین پلن یک سفارش باز داری.</b>\n\n" + payment_text(existing),
                payment_kb(existing["id"])
            )
            return

        if count_open_orders(uid) >= MAX_OPEN_ORDERS_PER_USER:
            await answer(
                q,
                f"حداکثر {MAX_OPEN_ORDERS_PER_USER} سفارش باز می‌تونی داشته باشی. "
                "اول سفارش‌های قبلی رو تکمیل کن.",
                True
            )
            return

        purchase_dt, time_source = await time_ir_now()
        oid = create_order(uid, p, purchase_dt, time_source)
        o = get_order(oid)
        audit(uid, "order_create", f"order={oid},source={time_source}")
        await edit(q, payment_text(o), payment_kb(oid))
        return

    if data.startswith("u:renewfast:"):
        parent_oid = to_int(data.rsplit(":", 1)[1])
        parent = get_order(parent_oid) if parent_oid is not None else None
        if not parent or int(parent["user_id"]) != uid or parent["status"] != COMPLETED or int(parent["is_gift"] or 0):
            await answer(q, "این سرویس قابل تمدید فوری نیست.", True)
            return
        p_now = get_plan(parent["plan_id"]) if parent["plan_id"] else None
        if not p_now or not p_now["is_active"]:
            await answer(q, "پلن فعلاً فعال نیست.", True)
            return
        if pending_renewal(uid, int(parent["id"])):
            await answer(q, "برای این سرویس تمدید در جریان داری.", True)
            return
        if wallet_balance(uid) < int(p_now["price"]):
            await answer(q, "موجودی کیف پول کافی نیست.", True)
            return
        await edit(
            q,
            f"⚡ <b>تأیید تمدید فوری</b>\n\n"
            f"📦 {esc(p_now['title'])}\n"
            f"💰 مبلغ: <b>{money(p_now['price'])}</b>\n"
            f"💳 موجودی کیف پول: <b>{money(wallet_balance(uid))}</b>\n\n"
            "در صورت تأیید، مبلغ فوراً از کیف پول کم می‌شود.",
            InlineKeyboardMarkup([
                [user_button("✅ تأیید و پرداخت", callback_data=f"u:renewfastok:{parent_oid}", style="success")],
                [user_button("❌ انصراف", callback_data=f"u:order:{parent_oid}", style="danger")],
            ])
        )
        return

    if data.startswith("u:renewfastok:"):
        if rate_limit(context, uid, "fast_renew", 3.0):
            await answer(q, "چند ثانیه صبر کن.", True)
            return
        parent_oid = to_int(data.rsplit(":", 1)[1])
        parent = get_order(parent_oid) if parent_oid is not None else None
        if not parent or int(parent["user_id"]) != uid or parent["status"] != COMPLETED or int(parent["is_gift"] or 0):
            await answer(q, "تمدید معتبر نیست.", True)
            return
        if pending_renewal(uid, int(parent["id"])):
            await answer(q, "تمدید دیگری در جریان است.", True)
            return
        p_now = get_plan(parent["plan_id"]) if parent["plan_id"] else None
        if not p_now or not p_now["is_active"]:
            await answer(q, "پلن غیرفعال است.", True)
            return
        purchase_dt, time_source = await time_ir_now()
        oid = create_order(uid, p_now, purchase_dt, time_source, renew_parent_order_id=int(parent["id"]))
        amount = int(p_now["price"])
        c = db()
        paid = False
        try:
            c.execute("BEGIN IMMEDIATE")
            row = c.execute("SELECT wallet_balance FROM users WHERE user_id=?", (uid,)).fetchone()
            if row and int(row["wallet_balance"] or 0) >= amount:
                new_bal = int(row["wallet_balance"] or 0) - amount
                paid_at = now()
                cur = c.execute(
                    "UPDATE orders SET status=?,approved_at=?,purchased_at=COALESCE(purchased_at,?),"
                    "time_source=COALESCE(time_source,'server-tehran'),updated_at=? "
                    "WHERE id=? AND user_id=? AND status=?",
                    (APPROVED, paid_at, paid_at, paid_at, oid, uid, AWAIT_RECEIPT)
                )
                if cur.rowcount == 1:
                    c.execute("UPDATE users SET wallet_balance=? WHERE user_id=?", (new_bal, uid))
                    c.execute(
                        "INSERT INTO wallet_transactions(user_id,amount,tx_type,reference_type,reference_id,note,created_at) VALUES(?,?,?,?,?,?,?)",
                        (uid, -amount, "fast_renew", "order", oid, f"تمدید فوری سفارش #{parent_oid}", now())
                    )
                    paid = True
            if paid:
                c.commit()
            else:
                c.rollback()
        finally:
            c.close()
        if not paid:
            with db() as c:
                c.execute("UPDATE orders SET status=?,updated_at=?,rejection_reason=? WHERE id=? AND status=?", (CANCELLED, now(), "موجودی کیف پول برای تمدید فوری کافی نبود.", oid, AWAIT_RECEIPT))
            await answer(q, "موجودی کیف پول کافی نیست.", True)
            return
        audit(uid, "fast_wallet_renew", f"parent={parent_oid};order={oid};amount={amount}")
        delivered = await fulfill_approved_order(context, oid, actor="fast_renew")
        await edit(
            q,
            f"✅ <b>تمدید فوری انجام شد</b>\n\n"
            f"🧾 سفارش جدید: <code>#{oid}</code>\n"
            f"💳 موجودی جدید: <b>{money(wallet_balance(uid))}</b>\n"
            + ("⚡ سرویس تحویل شد." if delivered else "📦 سفارش برای تحویل ثبت شد."),
            main_kb(uid)
        )
        return

    if data.startswith("u:renew:"):
        parent_oid = to_int(data.rsplit(":", 1)[1])
        parent = get_order(parent_oid) if parent_oid is not None else None
        if not parent or parent["user_id"] != uid or parent["status"] != COMPLETED:
            await answer(q, "این سرویس قابل تمدید نیست.", True)
            return
        existing = pending_renewal(uid, int(parent["id"]))
        if existing:
            await edit(
                q,
                "🔄 <b>برای این سرویس یک تمدید در جریان داری.</b>\n\n" + payment_text(existing),
                payment_kb(existing["id"])
            )
            return

        if rate_limit(context, uid, "order_create", ORDER_CREATE_COOLDOWN):
            await answer(q, "چند ثانیه صبر کن و دوباره تلاش کن.", True)
            return

        if count_open_orders(uid) >= MAX_OPEN_ORDERS_PER_USER:
            await answer(q, f"حداکثر {MAX_OPEN_ORDERS_PER_USER} سفارش باز می‌تونی داشته باشی.", True)
            return

        p = get_plan(parent["plan_id"]) if parent["plan_id"] else None
        if not p or not p["is_active"]:
            await answer(q, "پلن این سرویس فعلاً برای تمدید فعال نیست.", True)
            return
        purchase_dt, time_source = await time_ir_now()
        oid = create_order(uid, p, purchase_dt, time_source, renew_parent_order_id=int(parent["id"]))
        o = get_order(oid)
        audit(uid, "renew_order_create", f"parent={parent['id']},order={oid},source={time_source}")
        await edit(q, f"🔄 <b>تمدید سرویس #{parent['id']}</b>\n\n" + payment_text(o), payment_kb(oid))
        return

    if data.startswith("u:walletpay:"):
        oid = to_int(data.rsplit(":", 1)[1])
        o = get_order(oid) if oid is not None else None
        if not o or int(o["user_id"]) != uid or o["status"] != AWAIT_RECEIPT:
            await answer(q, "این سفارش قابل پرداخت از کیف پول نیست.", True)
            return
        amount = int(o["final_amount"])
        c = db()
        try:
            c.execute("BEGIN IMMEDIATE")
            row = c.execute("SELECT wallet_balance FROM users WHERE user_id=?", (uid,)).fetchone()
            if not row or int(row["wallet_balance"] or 0) < amount:
                c.rollback()
                await answer(q, "موجودی کیف پول کافی نیست.", True)
                return
            paid_at = now()
            cur = c.execute(
                "UPDATE orders SET status=?,approved_at=?,purchased_at=COALESCE(purchased_at,?),"
                "time_source=COALESCE(time_source,'server-tehran'),updated_at=? "
                "WHERE id=? AND user_id=? AND status=?",
                (APPROVED, paid_at, paid_at, paid_at, oid, uid, AWAIT_RECEIPT)
            )
            if cur.rowcount != 1:
                c.rollback(); await answer(q, "وضعیت سفارش تغییر کرده.", True); return
            new_bal = int(row["wallet_balance"] or 0) - amount
            c.execute("UPDATE users SET wallet_balance=? WHERE user_id=?", (new_bal, uid))
            c.execute(
                "INSERT INTO wallet_transactions(user_id,amount,tx_type,reference_type,reference_id,note,created_at) VALUES(?,?,?,?,?,?,?)",
                (uid, -amount, "purchase", "order", oid, "پرداخت سفارش از کیف پول", now())
            )
            c.commit()
        except Exception:
            c.rollback(); raise
        finally:
            c.close()
        audit(uid, "wallet_order_payment", f"order={oid};amount={amount}")
        delivered = await fulfill_approved_order(context, oid, actor="wallet")
        o = get_order(oid)
        msg = "✅ پرداخت از کیف پول انجام شد."
        if delivered:
            msg += "\n⚡ سرویس هم تحویل شد."
        else:
            msg += "\n📦 سفارش برای تحویل ثبت شد."
        await edit(q, msg + f"\n💳 موجودی جدید: <b>{money(wallet_balance(uid))}</b>", main_kb(uid))
        return

    if data.startswith("u:coupon:"):
        oid = to_int(data.rsplit(":", 1)[1])
        o = get_order(oid) if oid is not None else None
        if not o or o["user_id"] != uid or o["status"] != AWAIT_RECEIPT:
            await answer(q, "این سفارش قابل تخفیف نیست.", True)
            return
        if o["coupon_code"]:
            await answer(q, "قبلاً تخفیف اعمال شده.", True)
            return
        set_action(uid, "coupon", str(oid))
        await edit(
            q,
            f"🎟 <b>کد تخفیف سفارش #{oid}</b>\n\nکد را در یک پیام ارسال کنید.",
            InlineKeyboardMarkup([
                [user_button("❌ انصراف", callback_data="u:cancel", style="danger")],
                [user_button("↩️ بازگشت به سفارش", callback_data=f"u:order:{oid}", style="danger")],
            ])
        )
        return

    if data.startswith("u:receipt:"):
        oid = to_int(data.rsplit(":", 1)[1])
        o = get_order(oid) if oid is not None else None
        if not o or o["user_id"] != uid:
            await answer(q, "سفارش معتبر نیست.", True)
            return
        if o["status"] not in (AWAIT_RECEIPT, REJECTED):
            await answer(q, "فیش جدید قابل ارسال نیست.", True)
            return
        set_action(uid, "receipt", str(oid))
        await edit(
            q,
            f"📸 <b>ارسال فیش واریزی برای سفارش #{oid}</b>\n\n"
            f"💰 مبلغ قابل پرداخت: <b>{money(o['final_amount'])}</b>\n\n"
            "لطفاً تصویر واضح فیش واریزی خود را ارسال کنید.",
            InlineKeyboardMarkup([
                [user_button("❌ انصراف", callback_data="u:cancel", style="danger")],
                [user_button("↩️ بازگشت به سفارش", callback_data=f"u:order:{oid}", style="danger")],
            ])
        )
        return

    if data == "u:orders":
        os_ = user_orders(uid)
        if not os_:
            await edit(q, "📦 هنوز سفارشی نداری.", home_kb())
            return
        rows = [[user_button(
            f"🧾 #{o['id']} • {o['plan_title']} • {STATUS.get(o['status'], o['status'])}",
            callback_data=f"u:order:{o['id']}",
            style="primary",
            icon_custom_emoji_id=CUSTOM_EMOJI_ORDERS_ID,
        )] for o in os_]
        rows.append([user_button("🏠 منوی اصلی", callback_data="u:home", style="danger", icon_custom_emoji_id=CUSTOM_EMOJI_HOME_ID)])
        await edit(q, "📦 <b>سفارش‌های من</b>", InlineKeyboardMarkup(rows))
        return

    if data.startswith("u:xui:"):
        oid = to_int(data.rsplit(":", 1)[1])
        o = get_order(oid) if oid is not None else None
        svc = xui_service_for_order(oid) if oid is not None else None
        owner_uid = int(o["service_owner_user_id"] or o["user_id"]) if o else 0
        if not o or owner_uid != uid or not svc:
            await answer(q, "سرویس 3X-UI پیدا نشد.", True)
            return
        try:
            st = await sync_xui_order_status(int(oid))
        except Exception:
            await edit(
                q,
                "🔌 <b>وضعیت لحظه‌ای 3X-UI</b>\n\n"
                "فعلاً ارتباط با سرور برقرار نشد؛ لینک سرویس و اطلاعات ثبت‌شده شما تغییری نکرده است.",
                InlineKeyboardMarkup([
                    [user_button("🔄 تلاش دوباره", callback_data=f"u:xui:{oid}", style="primary")],
                    [user_button("↩️ سفارش", callback_data=f"u:order:{oid}", style="danger")],
                ])
            )
            return
        if not st:
            await answer(q, "وضعیت قابل دریافت نیست.", True)
            return
        expiry = "نامحدود"
        if st.expiry_ms > 0:
            expiry_dt = datetime.fromtimestamp(st.expiry_ms / 1000, tz=timezone.utc).astimezone(IRAN_TZ)
            expiry = jalali_date(expiry_dt)
        total = human_bytes(st.total_bytes) if st.total_bytes > 0 else "نامحدود"
        remaining = human_bytes(st.remaining_bytes) if st.remaining_bytes >= 0 else "نامحدود"
        online = "آنلاین 🟢" if st.online is True else ("آفلاین ⚪" if st.online is False else "نامشخص")
        live_rows = [[user_button("🔄 بروزرسانی", callback_data=f"u:xui:{oid}", style="primary")]]
        if int(o["is_gift"] or 0):
            gift = gift_for_order(int(o["id"]))
            back_cb = f"u:giftservice:{gift['id']}" if gift else "u:services"
            live_rows.append([user_button("↩️ سرویس هدیه", callback_data=back_cb, style="danger")])
        else:
            live_rows.append([user_button("🔄 تمدید سرویس", callback_data=f"u:renew:{oid}", style="success")])
            live_rows.append([user_button("↩️ سفارش", callback_data=f"u:order:{oid}", style="danger")])
        await edit(
            q,
            "🔌 <b>وضعیت لحظه‌ای سرویس</b>\n\n"
            f"📦 {esc(o['plan_title'])}\n"
            f"🆔 <code>{esc(st.email)}</code>\n"
            f"📌 {'فعال ✅' if st.enabled else 'غیرفعال ⛔'} • {online}\n"
            f"📊 مصرف: <b>{human_bytes(st.used_bytes)}</b> از <b>{total}</b>\n"
            f"📥 باقی‌مانده: <b>{remaining}</b>\n"
            f"📱 IP Limit: <b>{st.limit_ip}</b>\n"
            f"📅 انقضا: <b>{expiry}</b>",
            InlineKeyboardMarkup(live_rows)
        )
        return

    if data.startswith("u:config:"):
        oid = to_int(data.rsplit(":", 1)[1])
        o = get_order(oid) if oid is not None else None
        if not o or int(o["user_id"]) != int(uid) or not o["delivered_config"] or int(o["is_gift"] or 0):
            await answer(q, "کانفیگ قابل دریافت نیست.", True)
            return
        try:
            await send_protected_credential(
                context.bot,
                uid,
                f"🔐 <b>کانفیگ سفارش #{o['id']}</b>\n📦 {esc(o['plan_title'])}",
                str(o["delivered_config"]),
                f"zankode_order_{o['id']}.txt",
                reply_markup=InlineKeyboardMarkup([
                    [user_button("↩️ سفارش‌های من", callback_data="u:orders", style="danger")]
                ]),
            )
        except TelegramError:
            await answer(q, "ارسال کانفیگ ناموفق بود؛ دوباره تلاش کن.", True)
        return

    if data.startswith("u:order:"):
        oid = to_int(data.rsplit(":", 1)[1])
        o = get_order(oid) if oid is not None else None
        if not o or o["user_id"] != uid:
            return
        rows = []
        if o["status"] in (AWAIT_RECEIPT, REJECTED):
            if o["status"] == AWAIT_RECEIPT and wallet_balance(uid) >= int(o["final_amount"]):
                rows.append([user_button("⚡ پرداخت از کیف پول", callback_data=f"u:walletpay:{oid}", style="success")])
            rows.append([user_button("💸 ارسال فیش", callback_data=f"u:receipt:{oid}", style="success", icon_custom_emoji_id=CUSTOM_EMOJI_RECEIPT_ID)])
            if not o["coupon_code"] and o["status"] == AWAIT_RECEIPT:
                rows.append([user_button("🎟️ کد تخفیف", callback_data=f"u:coupon:{oid}", style="primary", icon_custom_emoji_id=CUSTOM_EMOJI_COUPON_ID)])
        if o["status"] == COMPLETED:
            if not int(o["is_gift"] or 0):
                if xui_service_for_order(int(o["id"])):
                    rows.append([user_button("🔌 وضعیت لحظه‌ای سرویس", callback_data=f"u:xui:{oid}", style="primary")])
                if o["delivered_config"] and len(str(o["delivered_config"])) > 1800:
                    rows.append([user_button("🔐 دریافت دوباره کانفیگ", callback_data=f"u:config:{oid}", style="primary")])
                rows.append([user_button("🔄 تمدید سریع سرویس", callback_data=f"u:renew:{oid}", style="success", icon_custom_emoji_id=CUSTOM_EMOJI_SERVICE_ID)])
                p_now = get_plan(o["plan_id"]) if o["plan_id"] else None
                if p_now and p_now["is_active"] and wallet_balance(uid) >= int(p_now["price"]):
                    rows.append([user_button("⚡ تمدید فوری با کیف پول", callback_data=f"u:renewfast:{oid}", style="success")])
            rows.append([user_button("🧾 فاکتور دیجیتال", callback_data=f"u:invoice:{oid}", style="primary")])
        rows.append([user_button("↩️ بازگشت به سفارش‌ها", callback_data="u:orders", style="danger")])
        await edit(q, user_order_text(o), InlineKeyboardMarkup(rows))
        return

    if data == "u:support":
        tid = create_ticket(uid)
        set_action(uid, "support", str(tid))
        await edit(
            q,
            f"🎫 <b>ارتباط با پشتیبانی (تیکت #{tid})</b>\n\n"
            "لطفاً پیام، سوال یا درخواست خود را ارسال فرمایید. فقط متن و عکس پذیرفته می‌شود.",
            InlineKeyboardMarkup([
                [user_button("❌ انصراف", callback_data="u:cancel", style="danger")],
                [user_button("🏠 منوی اصلی", callback_data="u:home", style="danger", icon_custom_emoji_id=CUSTOM_EMOJI_HOME_ID)],
            ])
        )
        return

