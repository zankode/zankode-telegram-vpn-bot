# -*- coding: utf-8 -*-
"""Application configuration, Telegram UI primitives, and logging setup."""


from __future__ import annotations

import asyncio
import csv
import html
import logging
import os
import re
import secrets
import sqlite3
import tempfile
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
from urllib.parse import quote
from typing import Any, Optional

from telegram import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import BadRequest, Forbidden, NetworkError, RetryAfter, TelegramError
from telegram.ext import (
    Application, CallbackQueryHandler, CommandHandler, ContextTypes,
    MessageHandler, filters
)

# ======================== Core configuration ========================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    # Environment variables still work even when python-dotenv is unavailable.
    pass

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
try:
    ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0") or 0)
except ValueError:
    ADMIN_USER_ID = 0

DEFAULTS = {
    "shop_name": "Zankode VPN",
    "card_number": "6037-XXXX-XXXX-XXXX",
    "card_holder": "نام صاحب کارت",
    "support_username": "@YourSupport",
    "welcome_text": "لطفاً سرویس مدنظرتون رو انتخاب کنید، پس از پرداخت و ارسال فیش، سفارش شما سریعاً بررسی و تحویل داده میشه 🚀",
    "auto_delivery": "1",
    "maintenance": "0",
    "premium_emoji_pool": "",
    "low_stock_threshold": "3",
    "last_daily_report": "",
    "last_monthly_report": "",
    "unpaid_order_expiry_hours": "24",
    "test_low_stock_threshold": "3",
    "test_low_stock_alerted": "0",
    "lost_customer_days": "60",
    "vip_min_purchases": "8",
    "special_min_purchases": "4",
    "wallet_min_topup": "50000",
    "referral_commission_percent": "10",
    "referral_buyer_bonus": "10000",
    "user_icon_shop": "",
    "user_icon_account": "",
    "user_icon_services": "",
    "user_icon_wallet": "",
    "user_icon_gift": "",
    "user_icon_orders": "",
    "user_icon_support": "",
    "user_icon_referral": "",
    "user_icon_test": "",
    "user_icon_home": "",
}

# ======================== User-facing Premium UI ========================
# Optional: configure real Telegram Premium Custom Emoji IDs.
# If IDs are unavailable, the bot safely falls back to Unicode emoji.
# Example format: "5368324170671202286" (use your own valid ID).
CUSTOM_EMOJI_SHOP_ID = "5312016608254762256"
CUSTOM_EMOJI_ACCOUNT_ID = "5312486108309757006"
CUSTOM_EMOJI_SERVICE_ID = "5309958691854754293"
CUSTOM_EMOJI_ORDERS_ID = "5373251851074415873"
CUSTOM_EMOJI_SUPPORT_ID = "5377316857231450742"
CUSTOM_EMOJI_RECEIPT_ID = "5309929258443874898"
CUSTOM_EMOJI_COUPON_ID = "5310228579009699834"

USER_MENU_ICON_SLOTS = {
    "shop": ("خرید سرویس", "🛍️", CUSTOM_EMOJI_SHOP_ID),
    "account": ("حساب من", "👤", CUSTOM_EMOJI_ACCOUNT_ID),
    "services": ("سرویس‌های من", "💎", CUSTOM_EMOJI_SERVICE_ID),
    "wallet": ("کیف پول / شارژ حساب", "💳", CUSTOM_EMOJI_RECEIPT_ID),
    "gift": ("دریافت هدیه", "🎁", CUSTOM_EMOJI_COUPON_ID),
    "orders": ("سفارش‌ها", "🧾", CUSTOM_EMOJI_ORDERS_ID),
    "support": ("پشتیبانی", "🆘", CUSTOM_EMOJI_SUPPORT_ID),
    "referral": ("دعوت دوستان", "🎁", CUSTOM_EMOJI_COUPON_ID),
    "test": ("اکانت تست", "🧪", CUSTOM_EMOJI_SERVICE_ID),
    "home": ("منوی اصلی", "🏠", CUSTOM_EMOJI_ACCOUNT_ID),
}

# IDs are validated against the Telegram Bot API during startup.
# Invalid IDs fall back to another validated Premium Emoji.

# ======================== PREMIUM EVERYTHING MODE ========================
# True enables Premium Custom Emoji for buttons and HTML messages when possible.
USE_CUSTOM_EMOJI = True

# Valid animated/video Custom Emoji IDs are preferred.
VALID_CUSTOM_EMOJI_IDS: set[str] = set()
ANIMATED_CUSTOM_EMOJI_IDS: set[str] = set()
PREMIUM_EMOJI_POOL: list[str] = []

# Helper aliases reuse the configured core icon set.
CUSTOM_EMOJI_HOME_ID = CUSTOM_EMOJI_ACCOUNT_ID
CUSTOM_EMOJI_BACK_ID = CUSTOM_EMOJI_ORDERS_ID
CUSTOM_EMOJI_CONFIRM_ID = CUSTOM_EMOJI_RECEIPT_ID
CUSTOM_EMOJI_ADMIN_ID = CUSTOM_EMOJI_SUPPORT_ID
BASE_DIR = PROJECT_ROOT
DB_PATH = PROJECT_ROOT / os.getenv("DB_FILE", "config_shop.db")

PAGE_SIZE = 8
ACTION_TTL = 1800
CB_COOLDOWN = 0.30
MSG_COOLDOWN = 0.65

# Security / abuse controls
ORDER_CREATE_COOLDOWN = 4.0
MAX_OPEN_ORDERS_PER_USER = 3
TEST_REFERRAL_MATURITY_HOURS = 1
RESERVATION_STALE_MINUTES = 20

# ======================== Referral configuration ========================
# Legacy milestone settings are kept for backward database compatibility.
# Existing issued legacy reward coupons remain valid.
REFERRAL_JOIN_TARGET = 10
REFERRAL_BUY_TARGET = 3
REFERRAL_REWARD_PERCENT = 10
REFERRAL_MATURITY_HOURS = 24
TEST_REFERRAL_TARGET = 2
TEST_TRAFFIC_LABEL = "50MB"

IRAN_TZ = ZoneInfo("Asia/Tehran")
EXPIRY_WARNING_DAYS = 3
OPERATIONS_CHECK_SECONDS = 15 * 60

# Preserve PTB's original class before wrapping it with the UI factory.
_TelegramInlineKeyboardButton = InlineKeyboardButton

def _first_premium_id() -> str:
    if PREMIUM_EMOJI_POOL:
        return PREMIUM_EMOJI_POOL[0]
    pool = ANIMATED_CUSTOM_EMOJI_IDS or VALID_CUSTOM_EMOJI_IDS
    return next(iter(pool), "")

def _valid_premium_id(preferred: str) -> str:
    pool = ANIMATED_CUSTOM_EMOJI_IDS or VALID_CUSTOM_EMOJI_IDS
    if preferred and preferred in pool:
        return preferred
    if PREMIUM_EMOJI_POOL:
        return PREMIUM_EMOJI_POOL[0]
    return next(iter(pool), "")

def _premium_pool_pick(slot: int) -> str:
    if PREMIUM_EMOJI_POOL:
        return PREMIUM_EMOJI_POOL[slot % len(PREMIUM_EMOJI_POOL)]
    return _first_premium_id()

def _premium_icon_for_text(text_value: str) -> str:
    """Pick a Premium Custom Emoji that matches the button semantics."""
    t = str(text_value or "").lower()

    groups = [
        (0, ("خرید", "فروش", "قیمت", "جدید", "افزودن", "🛒", "🛍", "⚡", "💰")),
        (1, ("حساب", "کاربر", "عضو", "خانه", "منوی اصلی", "منوی کاربر", "👤", "👥", "🏠", "🆔")),
        (2, ("سرویس", "کانفیگ", "موجودی", "انبار", "پلن", "💎", "📦")),
        (3, ("سفارش", "داشبورد", "آمار", "جزئیات", "بازگشت", "تاریخچه", "🧾", "📊", "🔎", "↩")),
        (4, ("پشتیبانی", "تیکت", "رد", "حذف", "مسدود", "بلاک", "خطا", "❌", "🆘", "⛔", "🗑", "⚠")),
        (5, ("فیش", "واریز", "پرداخت", "تأیید", "ثبت", "ذخیره", "ارسال", "✅", "💸", "💳", "📸")),
        (6, ("تخفیف", "جایزه", "دعوت", "باشگاه", "کوپن", "coupon", "🎁", "🎟", "🏆", "🎉")),
    ]

    for slot, words in groups:
        if any(w.lower() in t for w in words):
            chosen = _premium_pool_pick(slot)
            if chosen:
                return chosen

    return _first_premium_id()

def _premium_style_for_button(text_value: str, callback_data: str = "") -> str:
    """Choose a Telegram button style from its semantics."""
    t = f"{text_value or ''} {callback_data or ''}".lower()

    if any(x in t for x in (
        "رد", "حذف", "مسدود", "بلاک", "پاک", "لغو",
        "بازگشت", "خانه", "منوی اصلی", "danger",
        "reject", "delete", "clear", "block", "❌", "🗑", "⛔"
    )):
        return "danger"

    if any(x in t for x in (
        "تأیید", "ثبت", "ارسال فیش", "دریافت", "ذخیره", "فعال",
        "جایزه", "دعوت", "تحویل", "approve", "save", "add",
        "✅", "🎁", "💸"
    )):
        return "success"

    return "primary"

_LEADING_EMOJI_RE = re.compile(
    r"^\s*(?:"
    r"[\U0001F1E6-\U0001F1FF]"
    r"|[\U0001F300-\U0001FAFF]"
    r"|[\u2600-\u27BF]"
    r"|[\u2190-\u21FF]"
    r"|[\u2300-\u23FF]"
    r"|[\u2B00-\u2BFF]"
    r"|[\uFE0F\u200D]"
    r"|[0-9#*]\uFE0F?\u20E3"
    r")+\s*"
)

def _strip_leading_unicode_emoji(value: str) -> str:
    clean = _LEADING_EMOJI_RE.sub("", str(value or ""), count=1).strip()
    return clean or str(value or "").strip()

def InlineKeyboardButton(text: str, *args, **kwargs):
    """
    Factory سراسری همه دکمه‌ها:
    Premium Custom Emoji + رنگ خودکار + حذف Emoji معمولی ابتدای متن.
    """
    original_text = str(text or "")

    if USE_CUSTOM_EMOJI:
        current_icon = str(kwargs.get("icon_custom_emoji_id") or "")
        valid_pool = ANIMATED_CUSTOM_EMOJI_IDS or VALID_CUSTOM_EMOJI_IDS
        if current_icon and current_icon in valid_pool:
            resolved_icon = current_icon
        else:
            resolved_icon = _premium_icon_for_text(original_text)

        if resolved_icon:
            kwargs["icon_custom_emoji_id"] = resolved_icon
            text = _strip_leading_unicode_emoji(original_text)

    if not kwargs.get("style"):
        kwargs["style"] = _premium_style_for_button(
            original_text,
            str(kwargs.get("callback_data") or "")
        )

    if not kwargs.get("icon_custom_emoji_id"):
        kwargs.pop("icon_custom_emoji_id", None)

    return _TelegramInlineKeyboardButton(text, *args, **kwargs)

_PREMIUM_TEXT_EMOJIS = {
    "🛍️": CUSTOM_EMOJI_SHOP_ID,
    "🛍": CUSTOM_EMOJI_SHOP_ID,
    "🛒": CUSTOM_EMOJI_SHOP_ID,
    "⚡": CUSTOM_EMOJI_SHOP_ID,
    "🚀": CUSTOM_EMOJI_SHOP_ID,
    "💰": CUSTOM_EMOJI_SHOP_ID,
    "💵": CUSTOM_EMOJI_SHOP_ID,

    "👤": CUSTOM_EMOJI_ACCOUNT_ID,
    "👥": CUSTOM_EMOJI_ACCOUNT_ID,
    "🆔": CUSTOM_EMOJI_ACCOUNT_ID,
    "👋": CUSTOM_EMOJI_ACCOUNT_ID,
    "🏅": CUSTOM_EMOJI_ACCOUNT_ID,
    "📅": CUSTOM_EMOJI_ACCOUNT_ID,
    "🔗": CUSTOM_EMOJI_ACCOUNT_ID,

    "💎": CUSTOM_EMOJI_SERVICE_ID,
    "📦": CUSTOM_EMOJI_SERVICE_ID,
    "✨": CUSTOM_EMOJI_SERVICE_ID,
    "🌐": CUSTOM_EMOJI_SERVICE_ID,

    "🧾": CUSTOM_EMOJI_ORDERS_ID,
    "📝": CUSTOM_EMOJI_ORDERS_ID,
    "📊": CUSTOM_EMOJI_ORDERS_ID,
    "⏳": CUSTOM_EMOJI_ORDERS_ID,
    "🕘": CUSTOM_EMOJI_ORDERS_ID,
    "📌": CUSTOM_EMOJI_ORDERS_ID,
    "🔎": CUSTOM_EMOJI_ORDERS_ID,
    "↩️": CUSTOM_EMOJI_ORDERS_ID,
    "↩": CUSTOM_EMOJI_ORDERS_ID,

    "🆘": CUSTOM_EMOJI_SUPPORT_ID,
    "🎫": CUSTOM_EMOJI_SUPPORT_ID,
    "❗": CUSTOM_EMOJI_SUPPORT_ID,
    "❌": CUSTOM_EMOJI_SUPPORT_ID,
    "⛔": CUSTOM_EMOJI_SUPPORT_ID,
    "⚠️": CUSTOM_EMOJI_SUPPORT_ID,
    "⚠": CUSTOM_EMOJI_SUPPORT_ID,
    "🛡️": CUSTOM_EMOJI_SUPPORT_ID,
    "🛡": CUSTOM_EMOJI_SUPPORT_ID,

    "💸": CUSTOM_EMOJI_RECEIPT_ID,
    "💳": CUSTOM_EMOJI_RECEIPT_ID,
    "📸": CUSTOM_EMOJI_RECEIPT_ID,
    "✅": CUSTOM_EMOJI_RECEIPT_ID,

    "🎁": CUSTOM_EMOJI_COUPON_ID,
    "🎟️": CUSTOM_EMOJI_COUPON_ID,
    "🎟": CUSTOM_EMOJI_COUPON_ID,
    "🏆": CUSTOM_EMOJI_COUPON_ID,
    "🎉": CUSTOM_EMOJI_COUPON_ID,
    "💚": CUSTOM_EMOJI_COUPON_ID,
    "📭": CUSTOM_EMOJI_SERVICE_ID,
    "📨": CUSTOM_EMOJI_ORDERS_ID,
    "📤": CUSTOM_EMOJI_RECEIPT_ID,
    "✍️": CUSTOM_EMOJI_SUPPORT_ID,
    "✍": CUSTOM_EMOJI_SUPPORT_ID,
    "⚙️": CUSTOM_EMOJI_ACCOUNT_ID,
    "⚙": CUSTOM_EMOJI_ACCOUNT_ID,
    "💾": CUSTOM_EMOJI_SERVICE_ID,
    "📢": CUSTOM_EMOJI_ORDERS_ID,
    "➕": CUSTOM_EMOJI_SHOP_ID,
    "🔴": CUSTOM_EMOJI_SUPPORT_ID,
    "🟢": CUSTOM_EMOJI_RECEIPT_ID,
    "🔵": CUSTOM_EMOJI_ORDERS_ID,
    "🙏": CUSTOM_EMOJI_ACCOUNT_ID,
    "🔥": CUSTOM_EMOJI_SHOP_ID,
    "⭐": CUSTOM_EMOJI_COUPON_ID,
    "❤️": CUSTOM_EMOJI_COUPON_ID,
    "❤": CUSTOM_EMOJI_COUPON_ID,
}

def premium_html(value: Any) -> str:
    """
    ایموجی‌های معمولی متن HTML را به Telegram Premium Custom Emoji تبدیل می‌کند.
    اگر ID موردنظر معتبر نبود، از یک Custom Emoji متحرک معتبر دیگر استفاده می‌شود.
    """
    s = str(value if value is not None else "")
    if not USE_CUSTOM_EMOJI:
        return s

    # Before post_init validates IDs, keep the original Unicode text.
    if not (ANIMATED_CUSTOM_EMOJI_IDS or VALID_CUSTOM_EMOJI_IDS):
        return s

    # Avoid wrapping text that has already been converted.
    if "<tg-emoji " in s:
        return s

    # Process longer graphemes first so variation selectors remain intact.
    for symbol in sorted(_PREMIUM_TEXT_EMOJIS, key=len, reverse=True):
        preferred = _PREMIUM_TEXT_EMOJIS[symbol]
        eid = _valid_premium_id(preferred)
        if eid and symbol in s:
            s = s.replace(
                symbol,
                f'<tg-emoji emoji-id="{eid}">{symbol}</tg-emoji>'
            )
    return s

AWAIT_RECEIPT = "awaiting_receipt"
AWAIT_ADMIN = "awaiting_admin"
APPROVED = "approved"
REJECTED = "rejected"
COMPLETED = "completed"
CANCELLED = "cancelled"

STATUS = {
    AWAIT_RECEIPT: "🧾 منتظر فیش",
    AWAIT_ADMIN: "⏳ در انتظار بررسی",
    APPROVED: "✅ تأیید شده",
    REJECTED: "❌ رد شده",
    COMPLETED: "🎉 تکمیل شده",
    CANCELLED: "🚫 لغو شده",
}

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)

# Avoid logging Telegram HTTP request URLs at INFO level.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("telegram.request").setLevel(logging.WARNING)

class _SecretRedactionFilter(logging.Filter):
    _BOT_URL_RE = re.compile(r"(https://api\.telegram\.org/bot)[^/\s]+", re.I)

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
            secrets_to_redact = {
                "BOT_TOKEN": str(BOT_TOKEN or "").strip(),
                "XUI_API_TOKEN": os.getenv("XUI_API_TOKEN", "").strip(),
                "XUI_PASSWORD": os.getenv("XUI_PASSWORD", "").strip(),
            }
            for label, secret in secrets_to_redact.items():
                if secret:
                    msg = msg.replace(secret, f"<{label}_REDACTED>")
            msg = self._BOT_URL_RE.sub(r"\1<BOT_TOKEN_REDACTED>", msg)
            record.msg = msg
            record.args = ()
        except Exception:
            pass
        return True

for _handler in logging.getLogger().handlers:
    _handler.addFilter(_SecretRedactionFilter())

log = logging.getLogger("zankode-vpn")


