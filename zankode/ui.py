# -*- coding: utf-8 -*-
"""User/admin keyboards and text rendering helpers."""

from .config import *
from .config import _TelegramInlineKeyboardButton, _premium_icon_for_text, _valid_premium_id
from .utils import *
from .storage import *

def _user_icon_setting_key(slot: str) -> str:
    return f"user_icon_{slot}"

def _user_icon_value(slot: str) -> str:
    return setting(_user_icon_setting_key(slot), "").strip()

def _user_icon_preview(slot: str) -> str:
    raw = _user_icon_value(slot)
    if raw.startswith("custom:"):
        return "Premium ✨"
    if raw.startswith("unicode:"):
        return raw.split(":", 1)[1] or "—"
    fallback = USER_MENU_ICON_SLOTS.get(slot)
    return fallback[1] if fallback else "—"

def user_menu_button(
    slot: str,
    title: str,
    *,
    callback_data: str,
    style: Optional[str] = None,
) -> _TelegramInlineKeyboardButton:
    """
    Only user-side navigation buttons use this.
    Admin buttons remain untouched.
    Supports either a normal Unicode emoji or one exact Premium Custom Emoji per slot.
    """
    meta = USER_MENU_ICON_SLOTS.get(slot)
    fallback_unicode = meta[1] if meta else ""
    fallback_custom = meta[2] if meta else ""

    raw = _user_icon_value(slot)
    custom_id = ""
    prefix = ""

    if raw.startswith("custom:"):
        custom_id = raw.split(":", 1)[1].strip()
    elif raw.startswith("unicode:"):
        prefix = raw.split(":", 1)[1].strip()
    else:
        if USE_CUSTOM_EMOJI:
            custom_id = _valid_premium_id(fallback_custom)
        if not custom_id:
            prefix = fallback_unicode

    kwargs: dict[str, Any] = {"callback_data": callback_data}
    if style:
        kwargs["style"] = style

    display = title
    if custom_id:
        kwargs["icon_custom_emoji_id"] = custom_id
    elif prefix:
        display = f"{prefix} {title}"

    # Direct PTB button: bypasses global auto-icon assignment intentionally.
    return _TelegramInlineKeyboardButton(display, **kwargs)

def user_button(
    text: str,
    *,
    callback_data: str,
    style: Optional[str] = None,
    icon_custom_emoji_id: str = "",
) -> InlineKeyboardButton:
    """Create a user-facing button with Premium icon and style support."""
    kwargs: dict[str, Any] = {
        "callback_data": callback_data,
    }
    if style:
        kwargs["style"] = style

    if USE_CUSTOM_EMOJI:
        resolved = _valid_premium_id(icon_custom_emoji_id) or _premium_icon_for_text(text)
        if resolved:
            kwargs["icon_custom_emoji_id"] = resolved

    return InlineKeyboardButton(text, **kwargs)

def main_kb(uid: int) -> InlineKeyboardMarkup:
    rows = [
        [user_menu_button("shop", "خرید سرویس", callback_data="u:plans", style="primary")],
        [
            user_menu_button("account", "حساب من", callback_data="u:account", style="success"),
            user_menu_button("services", "سرویس‌های من", callback_data="u:services", style="success"),
        ],
        [
            user_menu_button("wallet", "شارژ حساب / کیف پول", callback_data="u:wallet", style="success"),
            user_menu_button("gift", "دریافت هدیه", callback_data="u:gift", style="primary"),
        ],
        [
            user_menu_button("orders", "سفارش‌ها", callback_data="u:orders", style="primary"),
            user_menu_button("support", "پشتیبانی", callback_data="u:support", style="danger"),
        ],
        [user_menu_button("referral", "دعوت دوستان", callback_data="u:referral", style="success")],
        [user_menu_button("test", "اکانت تست 50MB", callback_data="u:test", style="primary")],
    ]

    # Admin panel remains visually/structurally unchanged.
    if is_admin(uid):
        rows.append([
            InlineKeyboardButton(
                "🛡️ پنل مدیریت",
                callback_data="a:panel",
                style="primary",
            )
        ])

    return InlineKeyboardMarkup(rows)

def home_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        user_menu_button("home", "منوی اصلی", callback_data="u:home", style="danger")
    ]])

def account_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [user_menu_button("shop", "خرید جدید", callback_data="u:plans", style="primary")],
        [
            user_menu_button("services", "سرویس‌های من", callback_data="u:services", style="success"),
            user_menu_button("orders", "تاریخچه سفارش‌ها", callback_data="u:orders", style="primary"),
        ],
        [
            user_button(
                "👑 باشگاه VIP",
                callback_data="u:vip",
                style="primary",
                icon_custom_emoji_id=CUSTOM_EMOJI_COUPON_ID,
            ),
            user_menu_button("wallet", "شارژ حساب / کیف پول", callback_data="u:wallet", style="success"),
        ],
        [user_menu_button("referral", "دعوت دوستان", callback_data="u:referral", style="success")],
        [
            user_menu_button("support", "پشتیبانی", callback_data="u:support", style="danger"),
            user_menu_button("home", "منوی اصلی", callback_data="u:home", style="danger"),
        ],
    ])

def admin_kb() -> InlineKeyboardMarkup:
    """
    Main admin page: frequent operations only.
    Nothing is removed; less-frequent tools are grouped under the extra-tools menu.
    """
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🧾 فیش‌ها", callback_data="a:pending:0"),
            InlineKeyboardButton("🛒 سفارش‌ها", callback_data="a:orders"),
        ],
        [
            InlineKeyboardButton("⚡ موجودی", callback_data="a:stock"),
            InlineKeyboardButton("📦 پلن‌ها", callback_data="a:plans"),
        ],
        [
            InlineKeyboardButton("👥 کاربران", callback_data="a:users"),
            InlineKeyboardButton("💳 کیف پول‌ها", callback_data="a:wallets"),
        ],
        [
            InlineKeyboardButton("🔔 اعلان‌ها", callback_data="a:notifications"),
            InlineKeyboardButton("🎫 تیکت‌ها", callback_data="a:tickets:0"),
        ],
        [
            InlineKeyboardButton("🔍 جستجوی سراسری", callback_data="a:globalsearch"),
            InlineKeyboardButton("🔎 جستجوی کانفیگ", callback_data="a:configsearch"),
        ],
        [
            InlineKeyboardButton("🎨 ظاهر منوی کاربر", callback_data="a:usericons"),
            InlineKeyboardButton("⚙️ تنظیمات", callback_data="a:settings"),
        ],
        [
            InlineKeyboardButton("📊 داشبورد", callback_data="a:stats"),
            InlineKeyboardButton("🧰 ابزارهای بیشتر", callback_data="a:more"),
        ],
        [InlineKeyboardButton("🏠 منوی کاربر", callback_data="u:home")],
    ])

def admin_more_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎟 تخفیف", callback_data="a:coupons"),
            InlineKeyboardButton("🎯 پیام هدفمند", callback_data="a:target"),
        ],
        [
            InlineKeyboardButton("🛡 ضدتقلب", callback_data="a:fraud"),
            InlineKeyboardButton("👑 مشتری‌ها", callback_data="a:segments"),
        ],
        [
            InlineKeyboardButton("📤 خروجی CSV", callback_data="a:exports"),
            InlineKeyboardButton("📢 همگانی", callback_data="a:broadcast"),
        ],
        [
            InlineKeyboardButton("📈 گزارش فروش", callback_data="a:reports"),
            InlineKeyboardButton("📜 تاریخچه تحویل", callback_data="a:deliverylog"),
        ],
        [
            InlineKeyboardButton("🔌 مرکز 3X-UI", callback_data="a:xui"),
            InlineKeyboardButton("💾 بکاپ", callback_data="a:backup"),
        ],
        [InlineKeyboardButton("🔙 پنل اصلی", callback_data="a:panel")],
    ])

def plans_kb() -> InlineKeyboardMarkup:
    rows = [[
        user_button(
            f"⚡ {p['title']} • {money(p['price'])}",
            callback_data=f"u:plan:{p['id']}",
            style="primary",
            icon_custom_emoji_id=CUSTOM_EMOJI_SHOP_ID,
        )
    ] for p in active_plans()]
    rows.append([
        user_button("↩️ بازگشت", callback_data="u:home", style="danger", icon_custom_emoji_id=CUSTOM_EMOJI_BACK_ID)
    ])
    return InlineKeyboardMarkup(rows)

def payment_kb(oid: int) -> InlineKeyboardMarkup:
    o = get_order(oid)
    rows = []
    if o and o["status"] == AWAIT_RECEIPT and wallet_balance(int(o["user_id"])) >= int(o["final_amount"]):
        rows.append([
            user_button(
                "⚡ پرداخت فوری از کیف پول",
                callback_data=f"u:walletpay:{oid}",
                style="success",
                icon_custom_emoji_id=CUSTOM_EMOJI_RECEIPT_ID,
            )
        ])
    rows += [
        [user_button(
            "💸 ارسال فیش واریز", callback_data=f"u:receipt:{oid}", style="success",
            icon_custom_emoji_id=CUSTOM_EMOJI_RECEIPT_ID
        )],
        [user_button(
            "🎟️ کد تخفیف", callback_data=f"u:coupon:{oid}", style="primary",
            icon_custom_emoji_id=CUSTOM_EMOJI_COUPON_ID
        )],
        [user_button(
            "📦 سفارش‌های من", callback_data="u:orders", style="primary",
            icon_custom_emoji_id=CUSTOM_EMOJI_ORDERS_ID
        )],
        [user_button("🏠 منوی اصلی", callback_data="u:home", style="danger")],
    ]
    return InlineKeyboardMarkup(rows)

def payment_text(o) -> str:
    return (
        f"✅ <b>سفارش #{o['id']} با موفقیت ثبت شد</b>\n\n"
        f"📦 سرویس انتخابی: {esc(o['plan_title'])}\n"
        f"📅 مدت اعتبار: {int(o['duration_days'] or 30)} روز\n"
        f"🛒 تاریخ خرید: <b>{jalali_date(o['purchased_at'])}</b>\n"
        f"⏳ پایان اعتبار: <b>{jalali_date(o['expires_at'])}</b>\n"
        f"💵 قیمت پایه: {money(o['base_amount'])}\n"
        f"🎟 تخفیف شما: {money(o['discount_amount'])}\n"
        f"💰 مبلغ قابل پرداخت: <b>{money(o['final_amount'])}</b>\n"
        "───────────────────\n"
        "💳 شماره کارت جهت واریز:\n"
        f"<code>{esc(setting('card_number'))}</code>\n"
        f"👤 به نام: <b>{esc(setting('card_holder'))}</b>\n"
        "───────────────────\n"
        "لطفاً پس از واریز، تصویر فیش پرداختتون رو همینجا ارسال کنید تا فرایند فعال‌سازی انجام بشه 🙏"
    )

def user_order_text(o) -> str:
    s = (
        f"📦 <b>سفارش #{o['id']}</b>\n\n"
        f"⚡ {esc(o['plan_title'])}\n"
        f"💵 قیمت پایه: {money(o['base_amount'])}\n"
        f"🎟 تخفیف: {money(o['discount_amount'])}\n"
        f"💰 مبلغ نهایی: <b>{money(o['final_amount'])}</b>\n"
        f"📌 وضعیت: {STATUS.get(o['status'], esc(o['status']))}"
    )
    if o["purchased_at"]:
        s += f"\n🛒 تاریخ خرید: <b>{jalali_date(o['purchased_at'])}</b>"
    if o["expires_at"]:
        s += f"\n📅 پایان اعتبار: <b>{jalali_date(o['expires_at'])}</b>"
        if o["status"] == COMPLETED:
            rem = service_remaining_days(o)
            s += f"\n⏳ وضعیت اعتبار: <b>{service_state(o)}</b>"
            if rem:
                s += f"\n⏱ باقی‌مانده: <b>{rem} روز</b>"
    if o["renew_parent_order_id"]:
        s += f"\n🔄 تمدید سرویس: <code>#{o['renew_parent_order_id']}</code>"

    xsvc = xui_service_for_order(int(o["id"]))
    if xsvc:
        state = {"active": "فعال ✅", "disabled": "غیرفعال ⛔", "deleted": "حذف‌شده 🗑"}.get(str(xsvc["remote_status"]), str(xsvc["remote_status"]))
        s += (
            "\n\n🔌 <b>مدیریت‌شده توسط 3X-UI</b>"
            f"\n🆔 Client: <code>{esc(xsvc['client_email'])}</code>"
            f"\n📡 وضعیت Sync: <b>{esc(state)}</b>"
        )
        if xsvc["last_error"]:
            s += "\n⚠️ آخرین Sync با خطا روبه‌رو شده؛ از دکمه بروزرسانی استفاده کن."

    gift = gift_for_order(int(o["id"])) if int(o["is_gift"] or 0) else None
    if gift:
        state = "دریافت‌شده ✅" if gift["status"] == "redeemed" else "آماده هدیه 🎁"
        s += (
            f"\n\n🎁 <b>سرویس هدیه</b> • {state}"
            f"\nکد هدیه: <code>{esc(gift['code'])}</code>"
        )

    if o["status"] == COMPLETED and o["delivered_config"] and not int(o["is_gift"] or 0):
        cfg = str(o["delivered_config"])
        # Show regular configs/links directly in the order details.
        if len(cfg) <= 1800:
            s += (
                "\n\n🔐 <b>کانفیگ / لینک تحویل‌شده:</b>\n"
                f"<code>{esc(cfg)}</code>"
            )
        else:
            s += "\n\n🔐 <b>کانفیگ تحویل‌شده ثبت شده است.</b>"

    if o["rejection_reason"]:
        s += f"\n\n❗ دلیل رد: {esc(o['rejection_reason'])}"
    return s

def account_text(tg_user) -> str:
    uid = tg_user.id
    user = get_user(uid)
    stats = account_stats(uid)
    level = vip_tier(uid)[0]
    last = stats["last_order"]
    ref_stats = referral_wallet_stats(uid)

    username = username_text(tg_user.username)
    joined = user["created_at"] if user else "—"

    if last:
        last_part = (
            f"#{last['id']} • {esc(last['plan_title'])}\n"
            f"{STATUS.get(last['status'], esc(last['status']))} • {money(last['final_amount'])}"
        )
    else:
        last_part = "هنوز سفارشی ثبت نکرده‌اید."

    return (
        "╭━━━ 👤 <b>حساب کاربری شما</b> ━━━╮\n\n"
        f"👤 نام: <b>{esc(tg_user.full_name)}</b>\n"
        f"🔗 شناسه کاربری: {esc(username)}\n"
        f"🆔 آیدی عددی: <code>{uid}</code>\n"
        f"🏅 سطح حساب شما: {level}\n"
        f"💳 موجودی کیف پول: <b>{money(wallet_balance(uid))}</b>\n"
        f"📅 تاریخ همراهی: {esc(joined)}\n"
        "───────────────────\n"
        f"🛒 کل سفارش‌ها: <b>{stats['total_orders']} عدد</b>\n"
        f"✅ خریدهای موفق: <b>{stats['successful']} عدد</b>\n"
        f"💎 سرویس‌های فعال: <b>{stats['delivered']} عدد</b>\n"
        f"⏳ در حال بررسی: <b>{stats['pending']} عدد</b>\n"
        f"💰 مجموع خریدهای شما: <b>{money(stats['spent'])}</b>\n"
        f"🎁 دوستان دعوت‌شده: <b>{ref_stats['invited']} نفر</b>\n"
        f"💰 درآمد دعوت: <b>{money(ref_stats['earned'])}</b>\n"
        "───────────────────\n"
        "🕘 <b>آخرین سفارش شما:</b>\n"
        f"{last_part}"
    )

def invoice_text(o) -> str:
    invoice_id = f"ZK-{str(o['purchased_at'] or o['created_at'])[:10].replace('-', '')}-{o['id']}"
    return (
        "🧾 <b>فاکتور دیجیتال Zankode VPN</b>\n\n"
        f"شماره فاکتور: <code>{invoice_id}</code>\n"
        f"شماره سفارش: <code>#{o['id']}</code>\n"
        f"📦 سرویس: <b>{esc(o['plan_title'])}</b>\n"
        f"💵 مبلغ پایه: {money(o['base_amount'])}\n"
        f"🎟 تخفیف: {money(o['discount_amount'])}\n"
        f"💰 مبلغ پرداختی: <b>{money(o['final_amount'])}</b>\n"
        f"🛒 تاریخ خرید: <b>{jalali_date(o['purchased_at'])}</b>\n"
        f"📅 پایان اعتبار: <b>{jalali_date(o['expires_at'])}</b>\n"
        f"📌 وضعیت: <b>{STATUS.get(o['status'], esc(o['status']))}</b>"
    )

def admin_order_text(o) -> str:
    xsvc = xui_service_for_order(int(o["id"]))
    xui_part = ""
    if xsvc:
        xui_part = (
            f"\n🔌 3X-UI: <code>{esc(xsvc['client_email'])}</code>"
            f" • <b>{esc(xsvc['remote_status'])}</b>"
        )
        if xsvc["last_sync_at"]:
            xui_part += f"\n🔄 آخرین Sync: <b>{esc(xsvc['last_sync_at'])}</b>"
        if xsvc["last_error"]:
            xui_part += f"\n⚠️ <code>{esc(str(xsvc['last_error'])[:180])}</code>"
    return (
        f"🧾 <b>سفارش #{o['id']}</b>\n\n"
        f"👤 {esc(o['full_name'])}\n"
        f"🆔 <code>{o['user_id']}</code>\n"
        f"🔗 {esc(username_text(o['username']))}\n"
        f"{divider()}\n"
        f"📦 {esc(o['plan_title'])}\n"
        f"💵 پایه: {money(o['base_amount'])}\n"
        f"🎟 تخفیف: {money(o['discount_amount'])}\n"
        f"💰 نهایی: <b>{money(o['final_amount'])}</b>\n"
        f"🗓 خرید: <b>{jalali_date(o['purchased_at'])}</b>\n"
        f"✅ تکمیل: <b>{jalali_date(o['completed_at']) if o['completed_at'] else '—'}</b>\n"
        f"🎁 نوع: <b>{'هدیه' if int(o['is_gift'] or 0) else 'خرید عادی'}</b>\n"
        f"📌 {STATUS.get(o['status'], esc(o['status']))}"
        f"{xui_part}"
    )

def rate_limit(context, uid: int, bucket: str, cool: float) -> bool:
    store = context.application.bot_data.setdefault("_rl", {})
    n = time.monotonic()

    if len(store) > 50000:
        cutoff = n - 3600
        for key in [k for k, value in store.items() if value < cutoff]:
            store.pop(key, None)
        if len(store) > 50000:
            newest = sorted(store.items(), key=lambda kv: kv[1], reverse=True)[:25000]
            store.clear()
            store.update(newest)

    k = (bucket, uid)
    old = store.get(k, 0.0)
    store[k] = n
    return n - old < cool

