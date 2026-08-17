# -*- coding: utf-8 -*-
"""Telegram command handlers."""

from ..config import *
from ..utils import *
from ..storage import *
from ..ui import *
from ..services import *

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    was_known = get_user(u.id) is not None
    upsert_user(u)

    if update.effective_chat and update.effective_chat.type != "private":
        await access_ok(update)
        return

    if not was_known and context.args:
        arg = context.args[0].strip()
        if arg.startswith("ref_"):
            referrer_id = to_int(arg[4:])
            if referrer_id is not None:
                register_referral(u.id, referrer_id)

    if not await access_ok(update):
        return

    msg = (
        f"╭━━━ 🛍️ به {esc(setting('shop_name'))} خوش آمدید ━━━╮\n"
        f"سلام <b>{esc(u.first_name)}</b> گرامی 👋 خوشحالیم در خدمتتون هستیم.\n\n"
        f"{esc(setting('welcome_text'))}\n\n"
        "جهت شروع کار می‌توانید از منوی زیر استفاده کنید 👇"
    )
    await update.effective_message.reply_text(
        premium_html(msg),
        parse_mode="HTML",
        reply_markup=main_kb(u.id),
    )

async def cmd_ref(update: Update, context: ContextTypes.DEFAULT_TYPE):
    upsert_user(update.effective_user)
    if not await access_ok(update):
        return

    uid = update.effective_user.id
    bot_username = context.bot.username
    if not bot_username:
        me = await context.bot.get_me()
        bot_username = me.username

    s = referral_wallet_stats(uid)
    percent = min(100, max(0, to_int(setting("referral_commission_percent", "10")) or 10))
    buyer_bonus = max(0, to_int(setting("referral_buyer_bonus", "10000")) or 10000)
    ref_link = f"https://t.me/{bot_username}?start=ref_{uid}"

    msg = (
        "🎁 <b>دعوت دوستان و شارژ کیف پول</b>\n\n"
        f"هر رفیقی با لینک تو وارد ربات بشه و خرید موفق انجام بده، "
        f"<b>{percent}٪ مبلغ خریدش</b> مستقیم به کیف پول تو اضافه می‌شه.\n\n"
        f"🎉 خود رفیقت هم در اولین خرید موفق <b>{money(buyer_bonus)}</b> هدیه می‌گیره.\n\n"
        f"👥 دعوت‌شده‌ها: <b>{s['invited']}</b>\n"
        f"🛒 دوستان خریدار: <b>{s['buyers']}</b>\n"
        f"💰 درآمد دعوت: <b>{money(s['earned'])}</b>\n\n"
        "🔗 لینک اختصاصی شما:\n"
        f"<code>{esc(ref_link)}</code>"
    )
    await update.effective_message.reply_text(
        premium_html(msg),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [user_menu_button("referral", "باز کردن بخش دعوت دوستان", callback_data="u:referral", style="success")],
            [user_menu_button("home", "منوی اصلی", callback_data="u:home", style="danger")],
        ]),
    )

async def cmd_emoji(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if update.effective_chat and update.effective_chat.type != "private":
        return

    clear_action(update.effective_user.id)
    set_action(update.effective_user.id, "emoji_setup")
    await update.effective_message.reply_text(
        "✨ <b>تنظیم Premium Emoji</b>\n\n"
        "یک پیام برای ربات بفرست که داخلش چند Custom Emoji پریمیوم متحرک باشد.\n"
        "بهتره ۷ تا یا بیشتر بفرستی تا برای بخش‌های مختلف تنوع داشته باشیم.\n\n"
        "فقط Custom Emoji واقعی تلگرام را بفرست؛ ایموجی معمولی قبول نمی‌شود.\n"
        "برای انصراف: /cancel",
        parse_mode="HTML",
    )

async def cmd_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    upsert_user(update.effective_user)
    if not await access_ok(update):
        return
    await update.effective_message.reply_text(
        premium_html(account_text(update.effective_user)),
        parse_mode="HTML",
        reply_markup=account_kb(),
    )

async def cmd_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    upsert_user(update.effective_user)
    await update.effective_message.reply_text(
        premium_html(
            f"🆔 آیدی عددی شما:\n<code>{update.effective_user.id}</code>"
        ),
        parse_mode="HTML"
    )

async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    upsert_user(update.effective_user)
    if not is_admin(update.effective_user.id):
        return
    if update.effective_chat and update.effective_chat.type != "private":
        return
    clear_action(update.effective_user.id)
    await update.effective_message.reply_text(
        premium_html(
            "🛡️ <b>مرکز مدیریت فروشگاه</b>\n\nهمه‌چیز از اینجا قابل کنترله 👇"
        ),
        parse_mode="HTML",
        reply_markup=admin_kb()
    )

async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    upsert_user(update.effective_user)
    clear_action(update.effective_user.id)
    await update.effective_message.reply_text(
        premium_html("✅ عملیات لغو شد."),
        parse_mode="HTML",
        reply_markup=main_kb(update.effective_user.id)
    )

async def cmd_backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if (
        is_admin(update.effective_user.id)
        and update.effective_chat
        and update.effective_chat.type == "private"
    ):
        await backup_db(context)

