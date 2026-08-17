# -*- coding: utf-8 -*-
"""Admin callback-query flows and approval/rejection operations."""

from ..config import *
from ..utils import *
from ..storage import *
from ..ui import *
from ..ui import _user_icon_setting_key
from ..services import *
from .admin_views import *

async def admin_callback(q, context, data: str):
    aid = q.from_user.id

    if data == "a:panel":
        clear_action(aid)
        await edit(
            q,
            "🛡 <b>مرکز مدیریت</b>\n\n"
            "بخش‌های پرکاربرد جلوی دست هستند؛ هیچ قابلیتی حذف نشده.",
            admin_kb()
        )
        return

    if data == "a:more":
        clear_action(aid)
        await edit(
            q,
            "🧰 <b>ابزارهای بیشتر مدیریت</b>\n\n"
            "ابزارهای قبلی اینجا مرتب شده‌اند:",
            admin_more_kb()
        )
        return

    if data == "a:stats":
        s = dashboard_metrics()
        xs = xui_dashboard_metrics()
        await edit(
            q,
            "📊 <b>داشبورد حرفه‌ای فروش</b>\n\n"
            f"👥 کل کاربران: <b>{s['users']}</b>\n"
            f"🛒 کل سفارش‌ها: <b>{s['orders']}</b>\n"
            f"✅ خرید تکمیل‌شده: <b>{s['completed']}</b>\n"
            f"🎯 نرخ تبدیل سفارش به خرید: <b>{s['conversion']:.1f}%</b>\n"
            f"{divider()}\n"
            f"💰 فروش کل: <b>{money(s['revenue'])}</b>\n"
            f"📅 فروش ۷ روز: <b>{money(s['rev7'])}</b>\n"
            f"🗓 فروش ۳۰ روز: <b>{money(s['rev30'])}</b>\n"
            f"🏆 پرفروش‌ترین: <b>{esc(s['top'])}</b>\n"
            f"{divider()}\n"
            f"💎 سرویس فعال: <b>{s['active']}</b>\n"
            f"🔄 تمدید موفق: <b>{s['renewals']}</b>\n"
            f"👤 خریدار یکتا: <b>{s['buyers']}</b>\n"
            f"❤️ مشتری برگشتی: <b>{s['repeat']}</b>\n"
            f"💳 مانده کیف پول کاربران: <b>{money(s['wallet_total'])}</b>\n"
            f"{divider()}\n"
            f"🔌 سرویس‌های ثبت‌شده 3X-UI: <b>{xs['total']}</b>\n"
            f"🟢 فعال در آخرین Sync: <b>{xs['active']}</b>\n"
            f"⚠️ دارای خطای Sync: <b>{xs['errors']}</b>\n"
            f"📡 مصرف ثبت‌شده: <b>{human_bytes(xs['used_bytes'])}</b>",
            InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 بروزرسانی", callback_data="a:stats")],
                [InlineKeyboardButton("👑 سگمنت مشتری‌ها", callback_data="a:segments")],
                [InlineKeyboardButton("🔙 پنل", callback_data="a:panel")],
            ])
        )
        return

    if data == "a:notifications":
        n = notification_counts()
        await edit(
            q,
            "🔔 <b>مرکز اعلان ادمین</b>\n\n"
            f"🧾 فیش‌های منتظر: <b>{n['pending_receipts']}</b>\n"
            f"💳 شارژ کیف پول منتظر: <b>{n['wallet_topups']}</b>\n"
            f"🛡 تست نیازمند بررسی: <b>{n['test_reviews']}</b>\n"
            f"🎫 تیکت باز: <b>{n['tickets']}</b>\n"
            f"🚨 کاربران Flag شده: <b>{n['flagged']}</b>\n"
            f"⏳ سرویس تا ۳ روز آینده: <b>{n['expiring']}</b>\n"
            f"⚡ پلن‌های کم‌موجودی: <b>{n['low_plans']}</b>\n"
            f"🧪 موجودی تست: <b>{n['test_stock']}</b>",
            InlineKeyboardMarkup([
                [InlineKeyboardButton("🧾 فیش‌ها", callback_data="a:pending:0"), InlineKeyboardButton("💳 شارژها", callback_data="a:wtopups:0")],
                [InlineKeyboardButton("🛡 بررسی تست", callback_data="a:testreviews:0"), InlineKeyboardButton("🎫 تیکت‌ها", callback_data="a:tickets:0")],
                [InlineKeyboardButton("🔄 بروزرسانی", callback_data="a:notifications")],
                [InlineKeyboardButton("🔙 پنل", callback_data="a:panel")],
            ])
        )
        return

    if data == "a:fraud":
        with db() as c:
            duplicate_receipts = int(c.execute(
                "SELECT COUNT(*) FROM audit WHERE action IN ('duplicate_receipt_blocked','duplicate_receipt_race_blocked')"
            ).fetchone()[0])
        await edit(
            q,
            "🛡 <b>مرکز ضدتقلب</b>\n\n"
            f"🚫 تلاش فیش تکراری ثبت‌شده: <b>{duplicate_receipts}</b>\n"
            f"🟡 بررسی تست منتظر: <b>{pending_test_review_count()}</b>\n"
            "کاربران مشکوک با ترکیب Flag تست، سفارش‌های لغوشده زیاد و Referral غیرعادی امتیاز می‌گیرند.",
            InlineKeyboardMarkup([
                [InlineKeyboardButton("👥 کاربران مشکوک", callback_data="a:fraudusers:0")],
                [InlineKeyboardButton("🛡 تست‌های منتظر", callback_data="a:testreviews:0")],
                [InlineKeyboardButton("🔙 پنل", callback_data="a:panel")],
            ])
        )
        return

    if data.startswith("a:fraudusers:"):
        page = int(data.rsplit(":", 1)[1])
        await render_fraud_users(q, page)
        return

    if data == "a:target":
        await edit(
            q,
            "🎯 <b>پیام هدفمند</b>\n\nسگمنت را انتخاب کن؛ بعد پیام موردنظر را بفرست:",
            InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ همه خریداران", callback_data="a:targetseg:buyers"), InlineKeyboardButton("🌱 بدون خرید", callback_data="a:targetseg:no_purchase")],
                [InlineKeyboardButton("💎 سرویس فعال", callback_data="a:targetseg:active"), InlineKeyboardButton("⏳ انقضا ۳ روز", callback_data="a:targetseg:expiring3")],
                [InlineKeyboardButton("👑 VIP", callback_data="a:targetseg:vip"), InlineKeyboardButton("❤️ وفادار", callback_data="a:targetseg:loyal")],
                [InlineKeyboardButton("💤 از‌دست‌رفته", callback_data="a:targetseg:lost"), InlineKeyboardButton("🚨 مشکوک", callback_data="a:targetseg:suspicious")],
                [InlineKeyboardButton("📦 بر اساس پلن", callback_data="a:targetplans")],
                [InlineKeyboardButton("🔙 پنل", callback_data="a:panel")],
            ])
        )
        return

    if data == "a:targetplans":
        rows = [[InlineKeyboardButton(p["title"], callback_data=f"a:targetseg:plan_{p['id']}")] for p in all_plans()]
        rows.append([InlineKeyboardButton("↩️ هدفمند", callback_data="a:target")])
        await edit(q, "📦 پلن را انتخاب کن:", InlineKeyboardMarkup(rows))
        return

    if data.startswith("a:targetseg:"):
        segment = data.split(":", 2)[2]
        ids = segment_user_ids(segment)
        if not ids:
            await answer(q, "این سگمنت فعلاً کاربری ندارد.", True)
            return
        set_action(aid, "target_broadcast", segment)
        await edit(
            q,
            f"🎯 این پیام برای <b>{len(ids)}</b> کاربر ارسال می‌شود.\n\nپیام/عکس/فایل را حالا بفرست.",
            InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data="a:panel")]])
        )
        return

    if data == "a:segments":
        await render_segments(q)
        return

    if data.startswith("a:segmentlist:"):
        _, _, kind, spage = data.split(":")
        await render_segment_users(q, kind, int(spage))
        return

    if data == "a:wallets":
        with db() as c:
            total = int(c.execute("SELECT COALESCE(SUM(wallet_balance),0) FROM users").fetchone()[0])
            pending = int(c.execute("SELECT COUNT(*) FROM wallet_topups WHERE status='awaiting_admin'").fetchone()[0])
        await edit(
            q,
            "💳 <b>مدیریت کیف پول</b>\n\n"
            f"💰 مجموع مانده کاربران: <b>{money(total)}</b>\n"
            f"🧾 شارژ منتظر تأیید: <b>{pending}</b>",
            InlineKeyboardMarkup([
                [InlineKeyboardButton("🧾 شارژهای منتظر", callback_data="a:wtopups:0")],
                [InlineKeyboardButton("👥 کاربران", callback_data="a:users")],
                [InlineKeyboardButton("🔙 پنل", callback_data="a:panel")],
            ])
        )
        return

    if data.startswith("a:wtopups:"):
        await render_wallet_topups(q, int(data.rsplit(":", 1)[1]))
        return

    if data.startswith("a:wtopup:"):
        tid = int(data.rsplit(":", 1)[1])
        top = get_wallet_topup(tid)
        if not top:
            await answer(q, "درخواست پیدا نشد.", True)
            return
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ تأیید شارژ", callback_data=f"a:wapprove:{tid}", style="success"), InlineKeyboardButton("❌ رد", callback_data=f"a:wreject:{tid}", style="danger")],
            [InlineKeyboardButton("👤 کاربر", callback_data=f"a:user:{top['user_id']}")],
            [InlineKeyboardButton("↩️ شارژها", callback_data="a:wtopups:0")],
        ])
        if top["receipt_file_id"]:
            try:
                await context.bot.send_photo(
                    ADMIN_USER_ID, top["receipt_file_id"],
                    caption=premium_html(
                        f"💳 <b>شارژ کیف پول #{tid}</b>\n\n👤 {esc(top['full_name'])}\n🆔 <code>{top['user_id']}</code>\n💰 مبلغ: <b>{money(top['amount'])}</b>\n📌 وضعیت: {esc(top['status'])}"
                    ), parse_mode="HTML", reply_markup=kb
                )
                return
            except TelegramError:
                pass
        await edit(q, f"💳 شارژ #{tid} • {money(top['amount'])} • {esc(top['status'])}", kb)
        return

    if data.startswith("a:wapprove:"):
        tid = int(data.rsplit(":", 1)[1])
        ok, top, new_bal = approve_wallet_topup(tid, aid)
        if not ok or not top:
            await answer(q, "قبلاً بررسی شده یا قابل تأیید نیست.", True)
            return
        audit(aid, "wallet_topup_approve", f"topup={tid};user={top['user_id']}")
        try:
            await context.bot.send_message(
                int(top["user_id"]),
                f"✅ شارژ کیف پول #{tid} تأیید شد.\n💳 موجودی جدید: <b>{money(new_bal)}</b>",
                parse_mode="HTML", reply_markup=main_kb(int(top["user_id"]))
            )
        except TelegramError:
            pass
        await answer(q, "شارژ تأیید شد.")
        await render_wallet_topups(q, 0)
        return

    if data.startswith("a:wreject:"):
        tid = int(data.rsplit(":", 1)[1])
        top = get_wallet_topup(tid)
        if not top or top["status"] != "awaiting_admin":
            await answer(q, "قابل رد نیست.", True)
            return
        if reject_wallet_topup(tid, "فیش شارژ تأیید نشد."):
            try:
                await context.bot.send_message(int(top["user_id"]), f"❌ فیش شارژ کیف پول #{tid} تأیید نشد.", reply_markup=main_kb(int(top["user_id"])))
            except TelegramError:
                pass
        await render_wallet_topups(q, 0)
        return

    if data.startswith("a:walletadj:"):
        uid = int(data.rsplit(":", 1)[1])
        set_action(aid, "wallet_adjust", str(uid))
        await context.bot.send_message(
            ADMIN_USER_ID,
            "💳 تغییر موجودی کیف پول:\n<code>مبلغ | توضیح</code>\nمثال افزایش: <code>100000 | جایزه</code>\nمثال کاهش: <code>-50000 | اصلاح</code>",
            parse_mode="HTML"
        )
        return

    if data == "a:exports":
        await edit(
            q,
            "📤 <b>خروجی CSV</b>\n\nنوع فایل را انتخاب کن:",
            InlineKeyboardMarkup([
                [InlineKeyboardButton("👥 کاربران", callback_data="a:export:users"), InlineKeyboardButton("🧾 سفارش‌ها", callback_data="a:export:orders")],
                [InlineKeyboardButton("📜 تحویل‌ها", callback_data="a:export:deliveries"), InlineKeyboardButton("⚡ موجودی", callback_data="a:export:inventory")],
                [InlineKeyboardButton("💳 کیف پول", callback_data="a:export:wallet")],
                [InlineKeyboardButton("🔙 پنل", callback_data="a:panel")],
            ])
        )
        return

    if data.startswith("a:export:"):
        kind = data.rsplit(":", 1)[1]
        await export_csv(context, kind)
        await answer(q, "فایل ارسال شد.")
        return

    if data == "a:globalsearch":
        set_action(aid, "global_search")
        await edit(
            q,
            "🔍 <b>جستجوی سراسری</b>\n\nآیدی کاربر، @username، شماره سفارش، کد تخفیف یا بخشی از کانفیگ را بفرست.",
            InlineKeyboardMarkup([[InlineKeyboardButton("🔙 پنل", callback_data="a:panel")]])
        )
        return

    if data == "a:configsearch":
        set_action(aid, "config_search")
        await edit(
            q,
            "🔎 <b>جستجوی کانفیگ</b>\n\n"
            "حداقل ۴ کاراکتر از لینک/کانفیگ را بفرست.\n"
            "موجودی، فروخته‌شده‌ها، تحویل دستی و تست‌ها جستجو می‌شوند.",
            InlineKeyboardMarkup([[InlineKeyboardButton("🔙 پنل", callback_data="a:panel")]])
        )
        return

    if data == "a:reports":
        await edit(
            q,
            "📈 <b>گزارش‌های فروش</b>\n\nگزارش موردنظر را انتخاب کنید:",
            InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("📅 امروز", callback_data="a:report:today"),
                    InlineKeyboardButton("🗓 ماه جاری", callback_data="a:report:month"),
                ],
                [InlineKeyboardButton("🔙 پنل", callback_data="a:panel")],
            ])
        )
        return

    if data == "a:report:today":
        await edit(q, today_report_text(), InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 بروزرسانی", callback_data="a:report:today")],
            [InlineKeyboardButton("↩️ گزارش‌ها", callback_data="a:reports")],
        ]))
        return

    if data == "a:report:month":
        report, _ = month_report_text(current=True)
        await edit(q, report, InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 بروزرسانی", callback_data="a:report:month")],
            [InlineKeyboardButton("↩️ گزارش‌ها", callback_data="a:reports")],
        ]))
        return

    if data == "a:deliverylog":
        with db() as c:
            sold_n = int(c.execute(
                "SELECT COUNT(*) FROM orders WHERE status=? "
                "AND delivered_config IS NOT NULL AND delivered_config<>''",
                (COMPLETED,)
            ).fetchone()[0])
            test_n = int(c.execute(
                "SELECT COUNT(*) FROM test_claims"
            ).fetchone()[0])

        await edit(
            q,
            "📜 <b>تاریخچه تحویل کانفیگ</b>\n\n"
            f"💎 سرویس‌های تحویل‌شده: <b>{sold_n}</b>\n"
            f"🧪 تست‌های تحویل‌شده: <b>{test_n}</b>\n\n"
            "برای دیدن اینکه دقیقاً چه کانفیگی به چه کاربری داده شده، بخش موردنظر را انتخاب کن:",
            InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "💎 سرویس‌های فروخته‌شده",
                    callback_data="a:deliveryorders:0"
                )],
                [InlineKeyboardButton(
                    "🧪 تست‌های تحویل‌شده",
                    callback_data="a:testdeliveries:0"
                )],
                [InlineKeyboardButton("🔙 پنل", callback_data="a:panel")],
            ])
        )
        return

    if data.startswith("a:deliveryorders:"):
        page = int(data.rsplit(":", 1)[1])
        await render_delivery_history(q, page)
        return

    if data.startswith("a:deliveryitem:"):
        _, _, soid, spage = data.split(":")
        await render_delivery_history_item(q, int(soid), int(spage))
        return

    if data.startswith("a:testdeliveries:"):
        page = int(data.rsplit(":", 1)[1])
        await render_test_delivery_history(q, page)
        return

    if data.startswith("a:testdeliveryitem:"):
        _, _, suid, spage = data.split(":")
        await render_test_delivery_history_item(q, int(suid), int(spage))
        return

    if data.startswith("a:planstats:"):
        pid = int(data.rsplit(":", 1)[1])
        await render_plan_stats(q, pid)
        return

    if data.startswith("a:pending:"):
        page = int(data.rsplit(":",1)[1])
        await render_orders(q, AWAIT_ADMIN, page, "🧾 فیش‌های در انتظار")
        return

    if data == "a:orders":
        await edit(
            q, "🛒 <b>مدیریت سفارش‌ها</b>",
            InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🧾 منتظر", callback_data=f"a:olist:{AWAIT_ADMIN}:0"),
                    InlineKeyboardButton("✅ تأیید", callback_data=f"a:olist:{APPROVED}:0"),
                ],
                [
                    InlineKeyboardButton("🎉 تکمیل", callback_data=f"a:olist:{COMPLETED}:0"),
                    InlineKeyboardButton("❌ رد", callback_data=f"a:olist:{REJECTED}:0"),
                ],
                [InlineKeyboardButton("🕘 همه اخیر", callback_data="a:olist:all:0")],
                [InlineKeyboardButton("👥 خریداران", callback_data="a:buyers:0")],
                [InlineKeyboardButton("🔙 پنل", callback_data="a:panel")],
            ])
        )
        return

    if data.startswith("a:buyers:"):
        page = int(data.rsplit(":", 1)[1])
        await render_buyers(q, page)
        return

    if data.startswith("a:buyerorders:"):
        _, _, suid, spage = data.split(":")
        await render_buyer_orders(q, int(suid), int(spage))
        return

    if data.startswith("a:olist:"):
        _, _, st, pg = data.split(":")
        await render_orders(q, None if st == "all" else st, int(pg), "🛒 سفارش‌ها")
        return

    if data.startswith("a:order:"):
        oid = int(data.rsplit(":",1)[1])
        await render_order_admin(q, context, oid)
        return

    if data.startswith("a:approve:"):
        oid = int(data.rsplit(":",1)[1])
        await approve(q, context, oid)
        return

    if data.startswith("a:reject:"):
        oid = int(data.rsplit(":",1)[1])
        o = get_order(oid)
        if not o or o["status"] != AWAIT_ADMIN:
            await answer(q, "قبلاً بررسی شده.", True)
            return
        await context.bot.send_message(
            ADMIN_USER_ID, f"❌ دلیل رد سفارش #{oid}:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💸 مبلغ اشتباه", callback_data=f"a:rej:{oid}:amount")],
                [InlineKeyboardButton("🧾 فیش نامعتبر", callback_data=f"a:rej:{oid}:receipt")],
                [InlineKeyboardButton("♻️ فیش تکراری", callback_data=f"a:rej:{oid}:duplicate")],
                [InlineKeyboardButton("✍️ دلیل دلخواه", callback_data=f"a:rej:{oid}:custom")],
            ])
        )
        return

    if data.startswith("a:rej:"):
        _, _, soid, reason = data.split(":")
        oid = int(soid)
        reasons = {
            "amount": "مبلغ واریزی با سفارش مطابقت ندارد.",
            "receipt": "فیش ارسالی معتبر یا خوانا نیست.",
            "duplicate": "فیش تکراری است یا قبلاً استفاده شده.",
        }
        if reason == "custom":
            set_action(aid, "reject_custom", str(oid))
            await context.bot.send_message(ADMIN_USER_ID, f"✍️ دلیل رد سفارش #{oid} رو بفرست.")
        else:
            await reject(context, oid, reasons[reason])
            await context.bot.send_message(ADMIN_USER_ID, f"❌ سفارش #{oid} رد شد.", reply_markup=admin_kb())
        return

    if data.startswith("a:deliver:"):
        oid = int(data.rsplit(":",1)[1])
        o = get_order(oid)
        if not o or o["status"] != APPROVED:
            await answer(q, "قابل تحویل نیست.", True)
            return
        set_action(aid, "deliver", str(oid))
        await context.bot.send_message(ADMIN_USER_ID, f"📤 کانفیگ سفارش #{oid} رو به صورت متن بفرست.")
        return

    if data == "a:plans":
        await render_plans_admin(q)
        return

    if data == "a:padd":
        set_action(aid, "plan_add")
        await context.bot.send_message(
            ADMIN_USER_ID,
            "➕ پلن جدید:\n<code>عنوان | قیمت | مدت(روز) | توضیحات</code>\n\n"
            "فرمت قدیمی «عنوان | قیمت | توضیحات» هم پذیرفته می‌شود و مدت آن ۳۰ روز خواهد بود.",
            parse_mode="HTML"
        )
        return

    if data.startswith("a:plan:"):
        pid = int(data.rsplit(":", 1)[1])
        p = get_plan(pid)
        if not p:
            return
        await edit(
            q,
            f"📦 <b>{esc(p['title'])}</b>\n\n"
            f"💰 {money(p['price'])}\n"
            f"📅 اعتبار: <b>{int(p['duration_days'] or 30)} روز</b>\n"
            f"📝 {esc(p['description'])}\n"
            f"🚚 روش تحویل: <b>{'3X-UI خودکار' if plan_is_xui(p) else 'انبار کانفیگ'}</b>\n"
            + (
                f"🛰 Inbound IDs: <code>{esc(p['xui_inbound_ids'] or '—')}</code>\n"
                f"📊 حجم: <b>{int(p['xui_traffic_gb'] or 0)} GB</b> • 📱 IP: <b>{int(p['xui_ip_limit'] or 0)}</b>\n"
                if plan_is_xui(p) else f"⚡ موجودی: <b>{stock_count(pid)}</b>\n"
            )
            + f"📌 {'فعال ✅' if p['is_active'] else 'غیرفعال ⛔'}",
            InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✏️ عنوان", callback_data=f"a:pedit:{pid}:title"),
                    InlineKeyboardButton("💰 قیمت", callback_data=f"a:pedit:{pid}:price"),
                ],
                [
                    InlineKeyboardButton("📝 توضیحات", callback_data=f"a:pedit:{pid}:desc"),
                    InlineKeyboardButton("📅 مدت اعتبار", callback_data=f"a:pedit:{pid}:duration"),
                ],
                [
                    InlineKeyboardButton("🔁 فعال/غیرفعال", callback_data=f"a:ptoggle:{pid}"),
                    InlineKeyboardButton("🚚 حالت تحویل", callback_data=f"a:pmode:{pid}"),
                ],
                [
                    InlineKeyboardButton("🛰 Inbound IDs", callback_data=f"a:pedit:{pid}:xui_inbounds"),
                    InlineKeyboardButton("📊 حجم XUI", callback_data=f"a:pedit:{pid}:xui_traffic"),
                ],
                [
                    InlineKeyboardButton("📱 IP Limit", callback_data=f"a:pedit:{pid}:xui_ip"),
                    InlineKeyboardButton("⚡ موجودی", callback_data=f"a:stockp:{pid}"),
                ],
                [InlineKeyboardButton("📊 آمار دقیق پلن", callback_data=f"a:planstats:{pid}")],
                [InlineKeyboardButton("🗄 بایگانی", callback_data=f"a:pdel:{pid}")],
                [InlineKeyboardButton("↩️ بازگشت به پلن‌ها", callback_data="a:plans")],
            ])
        )
        return

    if data.startswith("a:pedit:"):
        _, _, spid, field = data.split(":")
        set_action(aid, f"plan_edit_{field}", spid)
        labels = {
            "title": "عنوان", "price": "قیمت", "desc": "توضیحات", "duration": "مدت اعتبار به روز",
            "xui_inbounds": "Inbound IDها مثل 1,2,5",
            "xui_traffic": "حجم XUI بر حسب GB (0=نامحدود)",
            "xui_ip": "محدودیت IP (0=بدون محدودیت)",
        }
        await context.bot.send_message(
            ADMIN_USER_ID,
            f"✏️ مقدار جدید {labels.get(field, field)} برای پلن #{spid} رو بفرست."
        )
        return

    if data.startswith("a:pmode:"):
        pid = int(data.rsplit(":", 1)[1])
        mode = "inventory"
        found = False
        with db() as c:
            r = c.execute("SELECT provision_mode FROM plans WHERE id=?", (pid,)).fetchone()
            if r:
                found = True
                mode = "inventory" if str(r["provision_mode"] or "inventory") == "xui" else "xui"
                c.execute("UPDATE plans SET provision_mode=?,updated_at=? WHERE id=?", (mode, now(), pid))
        audit(aid, "plan_provision_mode", f"{pid}:{mode if found else 'missing'}")
        if found and mode == "xui":
            await answer(q, "حالت XUI فعال شد؛ Inbound ID و حجم/IP را تنظیم کن.")
        await render_plans_admin(q)
        return

    if data == "a:xui":
        xui = XUIClient()
        metrics = xui_dashboard_metrics()
        if not xui.configured:
            await edit(
                q,
                "🔌 <b>مرکز 3X-UI</b>\n\n"
                "⛔ اتصال هنوز کامل تنظیم نشده.\n"
                "در <code>.env</code> حداقل XUI_PANEL_URL، XUI_API_TOKEN و XUI_SUB_URL_TEMPLATE را قرار بده.\n\n"
                f"📦 سرویس‌های ثبت‌شده محلی: <b>{metrics['total']}</b>",
                InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ابزارها", callback_data="a:more")]])
            )
            return
        try:
            health = await xui.health()
            inbounds = health.get("obj") if isinstance(health, dict) else []
            inbound_n = len(inbounds) if isinstance(inbounds, list) else 0
            state = "متصل ✅"
        except Exception as exc:
            inbound_n = 0
            state = f"خطا ⛔\n<code>{esc(str(exc))}</code>"
        await edit(
            q,
            "🔌 <b>مرکز 3X-UI</b>\n\n"
            f"وضعیت API: <b>{state}</b>\n"
            f"🛰 Inboundهای قابل مشاهده: <b>{inbound_n}</b>\n"
            f"💎 سرویس‌های XUI ثبت‌شده: <b>{metrics['total']}</b>\n"
            f"🟢 فعال محلی: <b>{metrics['active']}</b> • ⛔ غیرفعال: <b>{metrics['disabled']}</b>\n"
            f"⚠️ دارای خطا: <b>{metrics['errors']}</b>",
            InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 تست دوباره اتصال", callback_data="a:xui")],
                [InlineKeyboardButton("📦 پلن‌ها", callback_data="a:plans")],
                [InlineKeyboardButton("🔙 ابزارها", callback_data="a:more")],
            ])
        )
        return

    if data.startswith("a:xretry:"):
        oid = to_int(data.rsplit(":", 1)[1])
        if oid is None:
            return
        ok = await fulfill_approved_order(context, oid, actor="admin")
        await answer(q, "تحویل XUI انجام شد ✅" if ok else "هنوز تحویل نشد؛ جزئیات خطا ثبت شد.", not ok)
        return

    if data.startswith("a:xsync:"):
        oid = to_int(data.rsplit(":", 1)[1])
        if oid is None:
            return
        try:
            st = await sync_xui_order_status(oid)
            await answer(q, "وضعیت 3X-UI بروزرسانی شد ✅" if st else "سرویس XUI پیدا نشد.", not bool(st))
        except Exception as exc:
            await answer(q, str(exc)[:180], True)
        await render_order_admin(q, context, oid)
        return

    if data.startswith("a:xdelete:"):
        oid = to_int(data.rsplit(":", 1)[1])
        if oid is None:
            return
        await edit(
            q,
            f"⚠️ <b>حذف Client از 3X-UI</b>\n\nسرویس سفارش #{oid} واقعاً از پنل حذف شود؟ این کار اتصال مشتری را قطع می‌کند.",
            InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ بله، حذف کن", callback_data=f"a:xdeleteok:{oid}", style="danger")],
                [InlineKeyboardButton("❌ انصراف", callback_data=f"a:order:{oid}")],
            ])
        )
        return

    if data.startswith("a:xdeleteok:"):
        oid = to_int(data.rsplit(":", 1)[1])
        if oid is None:
            return
        try:
            ok = await delete_xui_service(oid)
            await answer(q, "Client از 3X-UI حذف شد." if ok else "سرویس XUI پیدا نشد.", not ok)
        except Exception as exc:
            await answer(q, str(exc)[:180], True)
        await render_order_admin(q, context, oid)
        return

    if data.startswith("a:ptoggle:"):
        pid = int(data.rsplit(":",1)[1])
        with db() as c:
            r = c.execute("SELECT is_active FROM plans WHERE id=?", (pid,)).fetchone()
            if r:
                c.execute("UPDATE plans SET is_active=?,updated_at=? WHERE id=?",
                          (0 if r["is_active"] else 1, now(), pid))
        audit(aid, "plan_toggle", str(pid))
        await render_plans_admin(q)
        return

    if data.startswith("a:pdel:"):
        pid = int(data.rsplit(":",1)[1])
        await edit(
            q,
            "🗄 <b>بایگانی امن پلن</b>\n\n"
            "برای حفظ تاریخچه فروش و کانفیگ‌ها، پلن از دیتابیس پاک نمی‌شود؛ "
            "فقط غیرفعال می‌شود و هر زمان بخواهی می‌توانی دوباره فعالش کنی.",
            InlineKeyboardMarkup([
                [InlineKeyboardButton("🗄 بایگانی امن", callback_data=f"a:pdelok:{pid}")],
                [InlineKeyboardButton("🔙 انصراف", callback_data=f"a:plan:{pid}")],
            ])
        )
        return

    if data.startswith("a:pdelok:"):
        pid = int(data.rsplit(":",1)[1])
        with db() as c:
            cur = c.execute(
                "UPDATE plans SET is_active=0,updated_at=? WHERE id=?",
                (now(), pid)
            )
        if cur.rowcount:
            audit(aid, "plan_archive", str(pid))
            await answer(q, "پلن بایگانی شد؛ تاریخچه و موجودی حذف نشد.")
        else:
            await answer(q, "پلن پیدا نشد.", True)
        await render_plans_admin(q)
        return

    if data == "a:stock":
        await render_stock(q)
        return

    if data.startswith("a:stockp:"):
        pid = int(data.rsplit(":",1)[1])
        await render_stock_plan(q, pid)
        return

    if data.startswith("a:stocklist:"):
        _, _, spid, spage = data.split(":")
        await render_stock_items(q, int(spid), int(spage))
        return

    if data.startswith("a:stockitem:"):
        _, _, spid, siid, spage = data.split(":")
        await render_stock_item(q, int(spid), int(siid), int(spage))
        return

    if data.startswith("a:stockdelone:"):
        _, _, spid, siid, spage = data.split(":")
        pid, iid, page = int(spid), int(siid), int(spage)
        ok = delete_inventory_item(iid, pid)
        if ok:
            audit(aid, "stock_delete_one", f"plan={pid},item={iid}")
            await answer(q, "کانفیگ حذف شد.")
        else:
            await answer(q, "این کانفیگ دیگر آزاد نیست یا قبلاً حذف شده.", True)
        await render_stock_items(q, pid, page)
        return

    if data.startswith("a:stockadd:"):
        pid = int(data.rsplit(":",1)[1])
        set_action(aid, "stock_add", str(pid))
        await context.bot.send_message(
            ADMIN_USER_ID,
            "⚡ کانفیگ‌ها رو بفرست؛ هر کانفیگ در یک خط. حداکثر ۵۰۰ مورد در هر بار."
        )
        return

    if data.startswith("a:stockclear:"):
        pid = int(data.rsplit(":",1)[1])
        await answer(
            q,
            "حذف گروهی غیرفعال شده؛ کانفیگ‌ها را از لیست به‌صورت تکی حذف کن.",
            True
        )
        await render_stock_plan(q, pid)
        return

    if data == "a:coupons":
        await render_coupons(q)
        return

    if data == "a:cadd":
        set_action(aid, "coupon_add")
        await context.bot.send_message(
            ADMIN_USER_ID,
            "🎟 فرمت ساخت کد:\n"
            "<code>CODE | percent | 20 | 100</code>\n"
            "یا\n<code>OFF50 | fixed | 50000 | 20</code>\n"
            "عدد آخر سقف استفاده است؛ 0 یعنی نامحدود.",
            parse_mode="HTML"
        )
        return

    if data.startswith("a:coupon:"):
        cid = int(data.rsplit(":",1)[1])
        with db() as c: cp = c.execute("SELECT * FROM coupons WHERE id=?", (cid,)).fetchone()
        if not cp: return
        val = f"{cp['value']}%" if cp["kind"] == "percent" else money(cp["value"])
        await edit(
            q,
            f"🎟 <b>{esc(cp['code'])}</b>\n\n"
            f"مقدار: {val}\nاستفاده: {cp['used_count']} / {'∞' if cp['max_uses']==0 else cp['max_uses']}\n"
            f"وضعیت: {'فعال ✅' if cp['is_active'] else 'غیرفعال ⛔'}",
            InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🔁 فعال/غیرفعال", callback_data=f"a:ctoggle:{cid}"),
                    InlineKeyboardButton("🗑 حذف", callback_data=f"a:cdel:{cid}"),
                ],
                [InlineKeyboardButton("🔙 کدها", callback_data="a:coupons")],
            ])
        )
        return

    if data.startswith("a:ctoggle:"):
        cid = int(data.rsplit(":",1)[1])
        with db() as c:
            r = c.execute("SELECT is_active FROM coupons WHERE id=?", (cid,)).fetchone()
            if r: c.execute("UPDATE coupons SET is_active=? WHERE id=?", (0 if r["is_active"] else 1, cid))
        await render_coupons(q)
        return

    if data.startswith("a:cdel:"):
        cid = int(data.rsplit(":",1)[1])
        with db() as c: c.execute("DELETE FROM coupons WHERE id=?", (cid,))
        audit(aid, "coupon_delete", str(cid))
        await render_coupons(q)
        return

    if data == "a:users":
        set_action(aid, "user_search")
        await edit(
            q, "👥 <b>جست‌وجوی کاربر</b>\n\nآیدی عددی، @username یا نام رو بفرست.",
            InlineKeyboardMarkup([[InlineKeyboardButton("🔙 پنل", callback_data="a:panel")]])
        )
        return

    if data.startswith("a:user:"):
        await render_user(q, int(data.rsplit(":",1)[1]))
        return

    if data.startswith("a:ublock:"):
        uid = int(data.rsplit(":",1)[1])
        if uid == ADMIN_USER_ID:
            await answer(q, "ادمین قابل بلاک نیست.", True)
            return
        u = get_user(uid)
        if u: set_block(uid, not bool(u["is_blocked"]))
        audit(aid, "user_block", str(uid))
        await render_user(q, uid)
        return

    if data.startswith("a:unote:"):
        uid = int(data.rsplit(":", 1)[1])
        set_action(aid, "user_note", str(uid))
        note = get_user_note(uid)
        await context.bot.send_message(
            ADMIN_USER_ID,
            "📝 یادداشت خصوصی ادمین را بفرست.\n"
            "برای پاک‌کردن یادداشت، فقط <code>-</code> بفرست."
            + (f"\n\nیادداشت فعلی:\n<code>{esc(note)}</code>" if note else ""),
            parse_mode="HTML"
        )
        return

    if data.startswith("a:unotedel:"):
        uid = int(data.rsplit(":", 1)[1])
        set_user_note(uid, "")
        audit(aid, "user_note_delete", str(uid))
        await answer(q, "یادداشت پاک شد.")
        await render_user(q, uid)
        return

    if data.startswith("a:testreviewreset:"):
        uid = int(data.rsplit(":", 1)[1])
        reset_test_review(uid)
        audit(aid, "test_review_reset", str(uid))
        await answer(q, "وضعیت بررسی تست ریست شد.")
        await render_user(q, uid)
        return

    if data.startswith("a:testsuspect:"):
        uid = int(data.rsplit(":", 1)[1])
        urow = get_user(uid)
        if not urow:
            return
        new_value = not bool(urow["test_review_required"])
        set_test_review_required(
            uid,
            new_value,
            "علامت‌گذاری دستی ادمین به‌عنوان حساب نیازمند بررسی تست" if new_value else ""
        )
        if not new_value:
            reset_test_review(uid)
        audit(aid, "test_suspect_toggle", f"{uid}:{int(new_value)}")
        await answer(
            q,
            "تست این کاربر از این پس نیاز به تأیید دستی دارد."
            if new_value else
            "بررسی اجباری تست برداشته و وضعیت بررسی ریست شد."
        )
        await render_user(q, uid)
        return

    if data.startswith("a:testreviews:"):
        page = int(data.rsplit(":", 1)[1])
        await render_test_reviews(q, page)
        return

    if data.startswith("a:testapprove:"):
        uid = int(data.rsplit(":", 1)[1])
        review = get_test_review(uid)
        if not review or review["status"] != "pending":
            await answer(q, "این درخواست دیگر در انتظار تأیید نیست.", True)
            return

        if get_test_claim(uid):
            finish_test_review(uid, "approved", aid)
            await answer(q, "این کاربر قبلاً تست گرفته.")
            await render_test_reviews(q, 0)
            return

        if test_stock_count() <= 0:
            await answer(q, "موجودی تست صفر است؛ اول تست اضافه کن.", True)
            return

        config = pop_test_stock_for_user(uid)
        if not config:
            await answer(q, "تحویل تست انجام نشد؛ موجودی را بررسی کن.", True)
            return

        finish_test_review(uid, "approved", aid)
        audit(aid, "test_review_approve", str(uid))
        await check_test_low_stock(context.bot)

        try:
            await context.bot.send_message(
                uid,
                premium_html(
                    "✅ <b>اکانت تست شما توسط ادمین تأیید شد.</b>\n\n"
                    "🔐 کانفیگ تست 50MB:\n"
                    f"<code>{esc(config)}</code>"
                ),
                parse_mode="HTML",
                protect_content=True,
                reply_markup=main_kb(uid)
            )
        except TelegramError:
            pass

        await answer(q, "تست تأیید و تحویل شد.")
        await render_test_reviews(q, 0)
        return

    if data.startswith("a:testreject:"):
        uid = int(data.rsplit(":", 1)[1])
        review = get_test_review(uid)
        if not review or review["status"] != "pending":
            await answer(q, "این درخواست دیگر در انتظار بررسی نیست.", True)
            return

        finish_test_review(uid, "rejected", aid)
        audit(aid, "test_review_reject", str(uid))
        try:
            await context.bot.send_message(
                uid,
                premium_html(
                    "⛔ <b>درخواست اکانت تست شما تأیید نشد.</b>\n\n"
                    "این محدودیت فقط مربوط به تست رایگان است."
                ),
                parse_mode="HTML",
                reply_markup=main_kb(uid)
            )
        except TelegramError:
            pass

        await answer(q, "درخواست تست رد شد.")
        await render_test_reviews(q, 0)
        return

    if data.startswith("a:tickets:"):
        await render_tickets(q, int(data.rsplit(":",1)[1]))
        return

    if data.startswith("a:ticket:"):
        tid = int(data.rsplit(":",1)[1])
        t = get_ticket(tid)
        if not t: return
        await edit(
            q,
            f"🎫 <b>تیکت #{tid}</b>\n\n👤 {esc(t['full_name'])}\n"
            f"🆔 <code>{t['user_id']}</code>\n🔗 {esc(username_text(t['username']))}",
            InlineKeyboardMarkup([
                [InlineKeyboardButton("✍️ پاسخ", callback_data=f"a:treply:{tid}")],
                [InlineKeyboardButton("✅ بستن", callback_data=f"a:tclose:{tid}")],
                [InlineKeyboardButton("🔙 تیکت‌ها", callback_data="a:tickets:0")],
            ])
        )
        return

    if data.startswith("a:treply:"):
        tid = int(data.rsplit(":",1)[1])
        set_action(aid, "ticket_reply", str(tid))
        await context.bot.send_message(ADMIN_USER_ID, f"✍️ پاسخ تیکت #{tid} رو بفرست؛ متن، عکس یا فایل.")
        return

    if data.startswith("a:tclose:"):
        tid = int(data.rsplit(":",1)[1])
        t = get_ticket(tid)
        if t:
            with db() as c:
                c.execute("UPDATE tickets SET status='closed',updated_at=?,closed_at=? WHERE id=?",
                          (now(), now(), tid))
            try:
                await context.bot.send_message(t["user_id"], f"✅ تیکت #{tid} بسته شد.", reply_markup=main_kb(t["user_id"]))
            except TelegramError: pass
        await render_tickets(q, 0)
        return

    if data == "a:broadcast":
        set_action(aid, "broadcast")
        await edit(
            q,
            "📢 <b>پیام همگانی</b>\n\nپیام رو بفرست؛ متن، عکس، ویدیو یا فایل قابل قبوله.",
            InlineKeyboardMarkup([[InlineKeyboardButton("🔙 پنل", callback_data="a:panel")]])
        )
        return

    if data == "a:teststock":
        count = test_stock_count()
        with db() as c:
            claimed = int(c.execute("SELECT COUNT(*) FROM test_claims").fetchone()[0])
        reviews_n = pending_test_review_count()

        await edit(
            q,
            "🧪 <b>مدیریت اکانت تست 50MB</b>\n\n"
            f"📦 موجودی آزاد: <b>{count}</b>\n"
            f"✅ تست صادرشده: <b>{claimed}</b>\n"
            f"🛡 در انتظار تأیید: <b>{reviews_n}</b>\n"
            "🔒 هر Telegram ID فقط یک تست می‌گیرد.\n\n"
            "محدودیت واقعی 50MB باید روی خود کانفیگ در پنل VPN اعمال شده باشد.",
            InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "👁 مشاهده کانفیگ‌های تست",
                    callback_data="a:testlist:0",
                    style="primary",
                )],
                [InlineKeyboardButton(
                    "➕ افزودن کانفیگ تست",
                    callback_data="a:teststock:add",
                    style="success",
                )],
                [InlineKeyboardButton(
                    f"🛡 درخواست‌های بررسی ({reviews_n})",
                    callback_data="a:testreviews:0",
                    style="primary",
                )],
                [InlineKeyboardButton(
                    "↩️ تنظیمات",
                    callback_data="a:settings",
                    style="danger",
                )],
            ])
        )
        return

    if data.startswith("a:testlist:"):
        page = int(data.rsplit(":", 1)[1])
        await render_test_items(q, page)
        return

    if data.startswith("a:testitem:"):
        _, _, siid, spage = data.split(":")
        await render_test_item(q, int(siid), int(spage))
        return

    if data.startswith("a:testdelone:"):
        _, _, siid, spage = data.split(":")
        iid, page = int(siid), int(spage)
        ok = delete_test_inventory_item(iid)
        if ok:
            audit(aid, "test_stock_delete_one", f"item={iid}")
            await answer(q, "کانفیگ تست حذف شد.")
        else:
            await answer(q, "این تست دیگر آزاد نیست یا قبلاً حذف شده.", True)
        await render_test_items(q, page)
        return

    if data == "a:teststock:add":
        set_action(aid, "test_stock_add")
        await context.bot.send_message(
            ADMIN_USER_ID,
            "🧪 کانفیگ‌های تست 50MB را بفرست.\n"
            "هر کانفیگ در یک خط جدا باشد.\n\n"
            "ربات فقط تحویل می‌دهد؛ محدودیت 50MB باید روی خود کانفیگ اعمال شده باشد."
        )
        return

    if data == "a:usericons":
        await render_user_icon_settings(q)
        return

    if data.startswith("a:usericon:"):
        slot = data.rsplit(":", 1)[1]
        if slot not in USER_MENU_ICON_SLOTS:
            await answer(q, "بخش نامعتبر است.", True)
            return
        set_action(aid, "user_icon_set", slot)
        await context.bot.send_message(
            ADMIN_USER_ID,
            f"🎨 ایموجی جدید برای «{USER_MENU_ICON_SLOTS[slot][0]}» را بفرست.\n\n"
            "• یک ایموجی معمولی مثل 🔥\n"
            "• یا یک Custom Emoji پریمیوم واقعی\n\n"
            "فقط همان یک ایموجی را ارسال کن."
        )
        return

    if data == "a:usericonsreset":
        for slot in USER_MENU_ICON_SLOTS:
            set_setting(_user_icon_setting_key(slot), "")
        audit(aid, "user_icons_reset_all")
        await answer(q, "همه ایموجی‌های کاربر به پیش‌فرض برگشت.")
        await render_user_icon_settings(q)
        return

    if data == "a:settings":
        await render_settings(q)
        return

    if data.startswith("a:set:"):
        k = data.rsplit(":",1)[1]
        if k == "auto":
            set_setting("auto_delivery", "0" if setting_on("auto_delivery") else "1")
            await render_settings(q); return
        if k == "maint":
            set_setting("maintenance", "0" if setting_on("maintenance") else "1")
            await render_settings(q); return
        mapping = {
            "shop":"shop_name", "card":"card_number", "holder":"card_holder",
            "support":"support_username", "welcome":"welcome_text",
            "unpaidhours":"unpaid_order_expiry_hours",
            "testlow":"test_low_stock_threshold",
            "lostdays":"lost_customer_days",
            "vipmin":"vip_min_purchases",
        }
        if k in mapping:
            set_action(aid, "setting", mapping[k])
            prompts = {
                "unpaidhours": "♻️ چند ساعت بعد سفارش بدون فیش لغو شود؟ ۰ یعنی خاموش.",
                "testlow": "🚨 وقتی موجودی تست به چند عدد رسید هشدار بدهم؟",
                "lostdays": "💤 مشتری بعد از چند روز بدون خرید، از‌دست‌رفته حساب شود؟",
                "vipmin": "👑 حداقل چند خرید موفق برای سطح VIP؟",
            }
            await context.bot.send_message(
                ADMIN_USER_ID,
                prompts.get(k, "⚙️ مقدار جدید رو بفرست.")
            )
        return

    if data == "a:backup":
        await backup_db(context)
        return

def atomic_approve_order(oid: int) -> bool:
    with db() as c:
        cur = c.execute(
            "UPDATE orders SET status=?,updated_at=?,approved_at=? "
            "WHERE id=? AND status=? AND receipt_file_id IS NOT NULL",
            (APPROVED, now(), now(), oid, AWAIT_ADMIN)
        )
        return cur.rowcount == 1

def atomic_reject_order(oid: int, reason: str) -> bool:
    with db() as c:
        cur = c.execute(
            "UPDATE orders SET status=?,updated_at=?,rejection_reason=? "
            "WHERE id=? AND status=?",
            (REJECTED, now(), reason, oid, AWAIT_ADMIN)
        )
        return cur.rowcount == 1

async def approve(q, context, oid: int):
    o = get_order(oid)
    if not o or o["status"] != AWAIT_ADMIN or not o["receipt_file_id"]:
        await answer(q, "سفارش قابل تأیید نیست یا قبلاً بررسی شده.", True)
        return
    if not atomic_approve_order(oid):
        await answer(q, "سفارش هم‌زمان تغییر کرده؛ دوباره بازش کن.", True)
        return
    audit(ADMIN_USER_ID, "approve", str(oid))
    try:
        await q.edit_message_reply_markup(reply_markup=None)
    except TelegramError:
        pass

    delivered = await fulfill_approved_order(context, oid, actor="admin")
    o = get_order(oid)
    if delivered:
        await context.bot.send_message(
            ADMIN_USER_ID,
            f"🎉 سفارش #{oid} تأیید و تحویل شد.",
            reply_markup=admin_kb()
        )
        return

    try:
        await context.bot.send_message(
            int(o["user_id"]),
            f"✅ <b>پرداخت سفارش #{oid} تأیید شد.</b>\nسفارش آماده تحویله.",
            parse_mode="HTML"
        )
    except TelegramError:
        pass

async def reject(context, oid: int, reason: str):
    o = get_order(oid)
    if not o or o["status"] != AWAIT_ADMIN:
        return
    if not atomic_reject_order(oid, reason):
        return
    audit(ADMIN_USER_ID, "reject", f"{oid}:{reason}")
    try:
        await context.bot.send_message(
            o["user_id"],
            f"❌ <b>پرداخت سفارش #{oid} تأیید نشد.</b>\n\nدلیل: {esc(reason)}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📸 ارسال فیش جدید", callback_data=f"u:receipt:{oid}")],
                [InlineKeyboardButton("🎫 پشتیبانی", callback_data="u:support")],
            ])
        )
    except TelegramError: pass

