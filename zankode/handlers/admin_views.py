# -*- coding: utf-8 -*-
"""Admin rendering, exports, list views, and broadcast helpers."""

from ..config import *
from ..utils import *
from ..storage import *
from ..ui import *
from ..services import *
from ..ui import _user_icon_preview

async def render_user_icon_settings(q):
    rows = []
    for slot, meta in USER_MENU_ICON_SLOTS.items():
        rows.append([
            InlineKeyboardButton(
                f"{_user_icon_preview(slot)} {meta[0]}",
                callback_data=f"a:usericon:{slot}"
            )
        ])
    rows.append([
        InlineKeyboardButton("♻️ بازگشت همه به پیش‌فرض", callback_data="a:usericonsreset")
    ])
    rows.append([InlineKeyboardButton("↩️ تنظیمات", callback_data="a:settings")])

    await edit(
        q,
        "🎨 <b>ویرایش ایموجی‌های منوی کاربر</b>\n\n"
        "هر گزینه را جداگانه انتخاب کن و فقط ایموجی همان بخش را تغییر بده.\n"
        "می‌توانی یک ایموجی معمولی یا یک Custom Emoji پریمیوم واقعی بفرستی.\n\n"
        "این تنظیم فقط ظاهر بخش کاربر را تغییر می‌دهد؛ پنل ادمین دست‌نخورده است.",
        InlineKeyboardMarkup(rows)
    )

async def render_wallet_topups(q, page: int):
    ds = pending_wallet_topups(page)
    more = len(ds) > 10
    items = ds[:10]
    if not items:
        await edit(q, "💳 <b>شارژهای کیف پول</b>\n\nموردی در انتظار نیست.", InlineKeyboardMarkup([[InlineKeyboardButton("↩️ کیف پول‌ها", callback_data="a:wallets")]]))
        return
    rows = []
    for t in items:
        rows.append([InlineKeyboardButton(
            f"💳 #{t['id']} • {t['full_name']} • {money(t['amount'])}",
            callback_data=f"a:wtopup:{t['id']}"
        )])
    nav = []
    if page > 0: nav.append(InlineKeyboardButton("⬅️ قبلی", callback_data=f"a:wtopups:{page-1}"))
    if more: nav.append(InlineKeyboardButton("بعدی ➡️", callback_data=f"a:wtopups:{page+1}"))
    if nav: rows.append(nav)
    rows.append([InlineKeyboardButton("↩️ کیف پول‌ها", callback_data="a:wallets")])
    await edit(q, f"💳 <b>شارژهای منتظر تأیید</b> • صفحه {page+1}", InlineKeyboardMarkup(rows))

async def render_fraud_users(q, page: int):
    ds = fraud_candidates(page)
    more = len(ds) > 10
    items = ds[:10]
    if not items:
        await edit(q, "🛡 <b>کاربران مشکوک</b>\n\nموردی با معیارهای فعلی پیدا نشد.", InlineKeyboardMarkup([[InlineKeyboardButton("↩️ ضدتقلب", callback_data="a:fraud")]]))
        return
    rows = []
    lines = ["🛡 <b>کاربران نیازمند توجه</b>\n"]
    for r in items:
        flags = []
        if r["test_review_required"]: flags.append("تست Flag")
        if r["pending_test"]: flags.append("تست منتظر")
        if int(r["cancelled7"] or 0) >= 3: flags.append(f"لغو۷روز:{r['cancelled7']}")
        if int(r["refs"] or 0) >= 15: flags.append(f"دعوت:{r['refs']}")
        lines.append(f"\n👤 {esc(r['full_name'])} • <code>{r['user_id']}</code>\n⚠️ {esc('، '.join(flags) or 'بررسی دستی')}")
        rows.append([InlineKeyboardButton(f"👤 {r['full_name']}", callback_data=f"a:user:{r['user_id']}")])
    nav=[]
    if page>0: nav.append(InlineKeyboardButton("⬅️ قبلی", callback_data=f"a:fraudusers:{page-1}"))
    if more: nav.append(InlineKeyboardButton("بعدی ➡️", callback_data=f"a:fraudusers:{page+1}"))
    if nav: rows.append(nav)
    rows.append([InlineKeyboardButton("↩️ ضدتقلب", callback_data="a:fraud")])
    await edit(q, "\n".join(lines), InlineKeyboardMarkup(rows))

async def render_segments(q):
    kinds = [
        ("buyers", "✅ خریداران"), ("no_purchase", "🌱 بدون خرید"),
        ("active", "💎 سرویس فعال"), ("expiring3", "⏳ انقضا ۳ روز"),
        ("vip", "👑 VIP"), ("loyal", "❤️ وفادار"),
        ("lost", "💤 از‌دست‌رفته"), ("suspicious", "🚨 مشکوک"),
    ]
    rows=[]
    lines=["👑 <b>مدیریت سگمنت مشتری‌ها</b>\n"]
    for kind,label in kinds:
        n=len(segment_user_ids(kind))
        lines.append(f"{label}: <b>{n}</b>")
        rows.append([InlineKeyboardButton(f"{label} • {n}", callback_data=f"a:segmentlist:{kind}:0")])
    rows.append([InlineKeyboardButton("🎯 پیام هدفمند", callback_data="a:target")])
    rows.append([InlineKeyboardButton("🔙 پنل", callback_data="a:panel")])
    await edit(q, "\n".join(lines), InlineKeyboardMarkup(rows))

async def render_segment_users(q, kind: str, page: int):
    ds = segment_rows(kind, page)
    more = len(ds)>10
    items=ds[:10]
    rows=[[InlineKeyboardButton(f"👤 {r['full_name']} • {r['user_id']}", callback_data=f"a:user:{r['user_id']}")] for r in items]
    nav=[]
    if page>0: nav.append(InlineKeyboardButton("⬅️ قبلی", callback_data=f"a:segmentlist:{kind}:{page-1}"))
    if more: nav.append(InlineKeyboardButton("بعدی ➡️", callback_data=f"a:segmentlist:{kind}:{page+1}"))
    if nav: rows.append(nav)
    rows.append([InlineKeyboardButton("↩️ سگمنت‌ها", callback_data="a:segments")])
    await edit(q, f"👥 <b>لیست سگمنت {esc(kind)}</b> • صفحه {page+1}\nتعداد کل: <b>{len(segment_user_ids(kind))}</b>", InlineKeyboardMarkup(rows))


def _csv_safe(value):
    """Prevent spreadsheet formula execution from user-controlled CSV cells."""
    if isinstance(value, str) and value[:1] in {"=", "+", "-", "@"}:
        return "'" + value
    return value


def _csv_row(writer, values):
    writer.writerow([_csv_safe(v) for v in values])

async def export_csv(context, kind: str):
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8-sig", newline="", suffix=f"_{kind}.csv", delete=False) as f:
            tmp=f.name
            w=csv.writer(f)
            with db() as c:
                if kind=="users":
                    w.writerow(["user_id","username","full_name","wallet_balance","created_at","last_seen"])
                    for r in c.execute("SELECT user_id,username,full_name,wallet_balance,created_at,last_seen FROM users ORDER BY user_id"):
                        _csv_row(w, list(r))
                elif kind=="orders":
                    w.writerow(["id","user_id","username","full_name","plan","base","discount","final","status","purchased_at","expires_at","completed_at","is_gift"])
                    for r in c.execute(
                        "SELECT o.id,o.user_id,u.username,u.full_name,o.plan_title,o.base_amount,"
                        "o.discount_amount,o.final_amount,o.status,o.purchased_at,o.expires_at,"
                        "o.completed_at,o.is_gift FROM orders o JOIN users u ON u.user_id=o.user_id "
                        "ORDER BY o.id"
                    ):
                        _csv_row(w, list(r))
                elif kind=="deliveries":
                    w.writerow(["order_id","user_id","plan","config","completed_at"])
                    for r in c.execute("SELECT id,user_id,plan_title,delivered_config,completed_at FROM orders WHERE delivered_config IS NOT NULL ORDER BY id"):
                        _csv_row(w, list(r))
                elif kind=="inventory":
                    w.writerow(["id","plan_id","config","status","order_id","created_at","used_at"])
                    for r in c.execute("SELECT id,plan_id,config_text,status,order_id,created_at,used_at FROM inventory ORDER BY id"):
                        _csv_row(w, list(r))
                elif kind=="wallet":
                    w.writerow(["id","user_id","amount","type","reference_type","reference_id","note","created_at"])
                    for r in c.execute("SELECT id,user_id,amount,tx_type,reference_type,reference_id,note,created_at FROM wallet_transactions ORDER BY id"):
                        _csv_row(w, list(r))
                else:
                    w.writerow(["unsupported"])
        with open(tmp,"rb") as fh:
            await context.bot.send_document(ADMIN_USER_ID, fh, filename=f"zankode_{kind}_{iran_now().strftime('%Y%m%d_%H%M')}.csv", protect_content=True)
        audit(ADMIN_USER_ID,"csv_export",kind)
    finally:
        if tmp:
            try: os.remove(tmp)
            except OSError: pass

def _retry_after_seconds(exc: RetryAfter) -> float:
    value = getattr(exc, "retry_after", 1)
    if hasattr(value, "total_seconds"):
        try:
            return max(1.0, float(value.total_seconds()))
        except Exception:
            return 1.0
    try:
        return max(1.0, float(value))
    except Exception:
        return 1.0

async def copy_message_with_retry(
    bot,
    *,
    chat_id: int,
    from_chat_id: int,
    message_id: int,
) -> bool:
    for attempt in range(3):
        try:
            await bot.copy_message(
                chat_id=chat_id,
                from_chat_id=from_chat_id,
                message_id=message_id,
            )
            return True
        except RetryAfter as exc:
            if attempt >= 2:
                return False
            await asyncio.sleep(min(60.0, _retry_after_seconds(exc) + 0.5))
        except NetworkError:
            if attempt >= 2:
                return False
            await asyncio.sleep(1.0 + attempt)
        except (Forbidden, BadRequest):
            return False
        except TelegramError:
            if attempt >= 2:
                return False
            await asyncio.sleep(0.75 + attempt)
    return False

async def broadcast_to_ids(update, context, ids: list[int], label: str):
    m = update.effective_message
    ids = list(dict.fromkeys(int(x) for x in ids))
    status = await m.reply_text(f"🎯 ارسال به {len(ids)} کاربر ({label}) شروع شد...")
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
                await status.edit_text(f"🎯 {i}/{len(ids)} • ✅ {ok} • ❌ {fail}")
            except TelegramError:
                pass

    try:
        await status.edit_text(f"✅ پایان ارسال {label}\nموفق: {ok}\nناموفق: {fail}")
    except TelegramError:
        pass

    audit(ADMIN_USER_ID, "target_broadcast", f"{label}:{ok}/{fail}")

async def render_orders(q, status: Optional[str], page: int, title: str):
    rows_data = list_orders(status, page)
    has_next = len(rows_data) > PAGE_SIZE
    items = rows_data[:PAGE_SIZE]
    if not items:
        await edit(
            q, f"{title}\n\n📭 موردی نیست.",
            InlineKeyboardMarkup([[InlineKeyboardButton("↩️ بازگشت به سفارش‌ها", callback_data="a:orders")]])
        )
        return
    rows = [[InlineKeyboardButton(
        f"💎 #{o['id']} • {str(o['full_name'])[:18]} • {str(o['plan_title'])[:24]}",
        callback_data=f"a:order:{o['id']}"
    )] for o in items]
    nav = []
    st = status or "all"
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ قبلی", callback_data=f"a:olist:{st}:{page-1}"))
    if has_next:
        nav.append(InlineKeyboardButton("بعدی ➡️", callback_data=f"a:olist:{st}:{page+1}"))
    if nav: rows.append(nav)
    rows.append([InlineKeyboardButton("↩️ بازگشت به سفارش‌ها", callback_data="a:orders")])
    await edit(q, f"<b>{esc(title)}</b>\nصفحه {page+1}", InlineKeyboardMarkup(rows))

async def render_order_admin(q, context, oid: int):
    o = get_order(oid)
    if not o:
        await answer(q, "سفارش پیدا نشد.", True)
        return
    rows = []
    plan = get_plan(int(o["plan_id"])) if o["plan_id"] else None
    svc = xui_service_for_order(oid)
    if o["status"] == AWAIT_ADMIN:
        rows.append([
            InlineKeyboardButton("✅ تأیید", callback_data=f"a:approve:{oid}"),
            InlineKeyboardButton("❌ رد", callback_data=f"a:reject:{oid}"),
        ])
    elif o["status"] == APPROVED:
        if plan_is_xui(plan):
            rows.append([InlineKeyboardButton("🔄 تلاش تحویل 3X-UI", callback_data=f"a:xretry:{oid}")])
        rows.append([InlineKeyboardButton("📤 تحویل دستی", callback_data=f"a:deliver:{oid}")])
    if svc and str(svc["remote_status"] or "") != "deleted":
        rows.append([
            InlineKeyboardButton("🔄 Sync 3X-UI", callback_data=f"a:xsync:{oid}"),
            InlineKeyboardButton("🗑 حذف Client", callback_data=f"a:xdelete:{oid}"),
        ])
    rows.append([InlineKeyboardButton("👤 کاربر", callback_data=f"a:user:{o['user_id']}")])
    rows.append([InlineKeyboardButton("↩️ بازگشت به سفارش‌ها", callback_data="a:orders")])
    kb = InlineKeyboardMarkup(rows)
    if o["receipt_file_id"]:
        try:
            await context.bot.send_photo(
                ADMIN_USER_ID, o["receipt_file_id"],
                caption=premium_html(admin_order_text(o)), parse_mode="HTML", reply_markup=kb
            )
            return
        except TelegramError:
            pass
    await edit(q, admin_order_text(o), kb)

async def render_plans_admin(q):
    rows = []
    for p in all_plans():
        rows.append([InlineKeyboardButton(
            f"{'✅' if p['is_active'] else '⛔'} #{p['id']} • {p['title']} • {money(p['price'])}",
            callback_data=f"a:plan:{p['id']}"
        )])
    rows += [
        [InlineKeyboardButton("➕ افزودن پلن", callback_data="a:padd")],
        [InlineKeyboardButton("🔙 پنل", callback_data="a:panel")],
    ]
    await edit(q, "📦 <b>مدیریت پلن‌ها</b>", InlineKeyboardMarkup(rows))

async def render_plan_stats(q, pid: int):
    s = plan_detailed_stats(pid)
    if not s:
        await answer(q, "پلن پیدا نشد.", True)
        return

    await edit(
        q,
        f"📊 <b>آمار پلن {esc(s['title'])}</b>\n\n"
        f"💰 قیمت فعلی: <b>{money(s['price'])}</b>\n"
        f"📅 اعتبار: <b>{s['duration_days']} روز</b>\n"
        f"{divider()}\n"
        f"✅ فروش تکمیل‌شده: <b>{s['completed_n']}</b>\n"
        f"👥 خریدار یکتا: <b>{s['buyers_n']}</b>\n"
        f"🔄 تمدیدها: <b>{s['renewals_n']}</b>\n"
        f"💵 درآمد پلن: <b>{money(s['revenue'])}</b>\n"
        f"🕘 آخرین فروش: <b>{esc(s['last_sale'] or '—')}</b>\n"
        f"{divider()}\n"
        f"🟢 موجودی آزاد: <b>{s['available_n']}</b>\n"
        f"🟡 رزروشده: <b>{s['reserved_n']}</b>\n"
        f"🔐 مصرف‌شده: <b>{s['used_n']}</b>",
        InlineKeyboardMarkup([
            [InlineKeyboardButton("⚡ موجودی پلن", callback_data=f"a:stockp:{pid}")],
            [InlineKeyboardButton("↩️ خود پلن", callback_data=f"a:plan:{pid}")],
        ])
    )

async def render_stock(q):
    rows = []
    total = 0
    xui_n = 0
    for p in all_plans():
        if plan_is_xui(p):
            xui_n += 1
            label = f"🔌 {p['title']} • XUI"
        else:
            n = stock_count(p["id"]); total += n
            label = f"⚡ {p['title']} • {n}"
        rows.append([InlineKeyboardButton(label, callback_data=f"a:stockp:{p['id']}")])
    rows.append([InlineKeyboardButton("🔙 پنل", callback_data="a:panel")])
    await edit(
        q,
        f"⚡ <b>انبار و تأمین سرویس</b>\n\nموجودی کانفیگ دستی: <b>{total}</b>\nپلن XUI خودکار: <b>{xui_n}</b>",
        InlineKeyboardMarkup(rows)
    )

async def render_stock_plan(q, pid: int):
    p = get_plan(pid)
    if not p:
        return
    if plan_is_xui(p):
        await edit(
            q,
            f"🔌 <b>{esc(p['title'])}</b>\n\n"
            "این پلن از انبار دستی استفاده نمی‌کند و سرویس را مستقیم در 3X-UI می‌سازد.\n"
            f"🛰 Inbound IDs: <code>{esc(p['xui_inbound_ids'] or '—')}</code>\n"
            f"📊 حجم: <b>{int(p['xui_traffic_gb'] or 0)} GB</b>\n"
            f"📱 IP Limit: <b>{int(p['xui_ip_limit'] or 0)}</b>",
            InlineKeyboardMarkup([
                [InlineKeyboardButton("🔌 مرکز 3X-UI", callback_data="a:xui")],
                [InlineKeyboardButton("📦 تنظیم پلن", callback_data=f"a:plan:{pid}")],
                [InlineKeyboardButton("🔙 انبار", callback_data="a:stock")],
            ])
        )
        return
    await edit(
        q,
        f"⚡ <b>{esc(p['title'])}</b>\n\n"
        f"موجودی آزاد: <b>{stock_count(pid)}</b>\n"
        f"تحویل خودکار: {'روشن ✅' if setting_on('auto_delivery') else 'خاموش ⛔'}",
        InlineKeyboardMarkup([
            [InlineKeyboardButton("👁 مشاهده کانفیگ‌ها", callback_data=f"a:stocklist:{pid}:0")],
            [InlineKeyboardButton("➕ افزودن موجودی", callback_data=f"a:stockadd:{pid}")],
            [InlineKeyboardButton("🔙 انبار", callback_data="a:stock")],
        ])
    )

def _config_preview(value: str, limit: int = 42) -> str:
    one_line = " ".join(str(value or "").split())
    if len(one_line) <= limit:
        return one_line
    return one_line[:limit - 1] + "…"

async def render_stock_items(q, pid: int, page: int):
    p = get_plan(pid)
    if not p:
        await answer(q, "پلن پیدا نشد.", True)
        return
    rows_data = inventory_available_rows(pid, page)
    more = len(rows_data) > 10
    items = rows_data[:10]
    if not items:
        await edit(
            q,
            f"👁 <b>کانفیگ‌های {esc(p['title'])}</b>\n\n📭 موجودی آزادی وجود ندارد.",
            InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ افزودن موجودی", callback_data=f"a:stockadd:{pid}")],
                [InlineKeyboardButton("↩️ موجودی پلن", callback_data=f"a:stockp:{pid}")],
            ])
        )
        return

    rows = [
        [InlineKeyboardButton(
            f"🔐 #{r['id']} • {_config_preview(r['config_text'])}",
            callback_data=f"a:stockitem:{pid}:{r['id']}:{page}"
        )]
        for r in items
    ]
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ قبلی", callback_data=f"a:stocklist:{pid}:{page-1}"))
    if more:
        nav.append(InlineKeyboardButton("بعدی ➡️", callback_data=f"a:stocklist:{pid}:{page+1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton("↩️ موجودی پلن", callback_data=f"a:stockp:{pid}")])
    await edit(
        q,
        f"👁 <b>کانفیگ‌های آزاد {esc(p['title'])}</b>\n"
        f"صفحه {page+1} • موجودی کل: <b>{stock_count(pid)}</b>\n\n"
        "برای دیدن کامل یا حذف، روی کانفیگ بزن:",
        InlineKeyboardMarkup(rows)
    )

async def render_stock_item(q, pid: int, iid: int, page: int):
    r = inventory_item(iid)
    if not r or int(r["plan_id"]) != int(pid) or r["status"] != "available":
        await answer(q, "کانفیگ آزاد پیدا نشد.", True)
        await render_stock_items(q, pid, page)
        return
    await edit(
        q,
        f"🔐 <b>کانفیگ #{iid}</b>\n"
        f"📦 پلن: {esc(r['plan_title'] or '—')}\n"
        f"📅 اضافه‌شده: {esc(r['created_at'])}\n\n"
        f"<code>{esc(r['config_text'])}</code>",
        InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "🗑 حذف همین کانفیگ",
                callback_data=f"a:stockdelone:{pid}:{iid}:{page}",
                style="danger",
            )],
            [InlineKeyboardButton("↩️ لیست کانفیگ‌ها", callback_data=f"a:stocklist:{pid}:{page}")],
        ])
    )

async def render_test_items(q, page: int):
    rows_data = test_inventory_rows(page)
    more = len(rows_data) > 10
    items = rows_data[:10]
    if not items:
        await edit(
            q,
            "🧪 <b>کانفیگ‌های تست 50MB</b>\n\n📭 فعلاً موجودی تست نداریم.",
            InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ افزودن کانفیگ تست", callback_data="a:teststock:add")],
                [InlineKeyboardButton("↩️ مدیریت تست", callback_data="a:teststock")],
            ])
        )
        return

    rows = [
        [InlineKeyboardButton(
            f"🧪 #{r['id']} • {_config_preview(r['config_text'])}",
            callback_data=f"a:testitem:{r['id']}:{page}"
        )]
        for r in items
    ]
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ قبلی", callback_data=f"a:testlist:{page-1}"))
    if more:
        nav.append(InlineKeyboardButton("بعدی ➡️", callback_data=f"a:testlist:{page+1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton("↩️ مدیریت تست", callback_data="a:teststock")])
    await edit(
        q,
        f"🧪 <b>کانفیگ‌های تست آزاد</b>\n"
        f"صفحه {page+1} • موجودی: <b>{test_stock_count()}</b>\n\n"
        "برای دیدن کامل یا حذف، روی مورد بزن:",
        InlineKeyboardMarkup(rows)
    )

async def render_test_item(q, iid: int, page: int):
    r = test_inventory_item(iid)
    if not r or r["status"] != "available":
        await answer(q, "این کانفیگ تست دیگر آزاد نیست.", True)
        await render_test_items(q, page)
        return
    await edit(
        q,
        f"🧪 <b>کانفیگ تست #{iid}</b>\n"
        f"📅 اضافه‌شده: {esc(r['created_at'])}\n\n"
        f"<code>{esc(r['config_text'])}</code>",
        InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "🗑 حذف همین تست",
                callback_data=f"a:testdelone:{iid}:{page}",
                style="danger",
            )],
            [InlineKeyboardButton("↩️ لیست تست‌ها", callback_data=f"a:testlist:{page}")],
        ])
    )

async def render_delivery_history(q, page: int):
    ds = delivery_history_rows(page)
    more = len(ds) > 10
    items = ds[:10]

    if not items:
        await edit(
            q,
            "💎 <b>سرویس‌های تحویل‌شده</b>\n\n"
            "📭 هنوز کانفیگ تحویل‌شده‌ای با اطلاعات قابل نمایش ثبت نشده.",
            InlineKeyboardMarkup([
                [InlineKeyboardButton("↩️ تاریخچه تحویل", callback_data="a:deliverylog")]
            ])
        )
        return

    rows = []
    for r in items:
        name = str(r["full_name"] or "کاربر")
        preview = _config_preview(r["delivered_config"], 24)
        rows.append([
            InlineKeyboardButton(
                f"🔐 #{r['order_id']} • {name} • {preview}",
                callback_data=f"a:deliveryitem:{r['order_id']}:{page}"
            )
        ])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(
            "⬅️ قبلی",
            callback_data=f"a:deliveryorders:{page-1}"
        ))
    if more:
        nav.append(InlineKeyboardButton(
            "بعدی ➡️",
            callback_data=f"a:deliveryorders:{page+1}"
        ))
    if nav:
        rows.append(nav)

    rows.append([
        InlineKeyboardButton("↩️ تاریخچه تحویل", callback_data="a:deliverylog")
    ])

    await edit(
        q,
        f"💎 <b>سرویس‌های فروخته‌شده</b>\n"
        f"صفحه {page+1}\n\n"
        "هر ردیف: شماره سفارش • کاربر • پیش‌نمایش کانفیگ\n"
        "برای دیدن اطلاعات کامل روی مورد بزن:",
        InlineKeyboardMarkup(rows)
    )

async def render_delivery_history_item(q, oid: int, page: int):
    r = delivery_history_item(oid)
    if not r:
        await answer(q, "این تحویل پیدا نشد.", True)
        await render_delivery_history(q, page)
        return

    delivery_type = "خودکار از موجودی ⚡" if r["auto_delivery"] else "تحویل دستی 📤"
    delivered_at = r["completed_at"] or r["updated_at"] or "—"

    await edit(
        q,
        f"🔐 <b>جزئیات تحویل سفارش #{r['order_id']}</b>\n\n"
        f"👤 کاربر: <b>{esc(r['full_name'] or '—')}</b>\n"
        f"🆔 آیدی: <code>{r['user_id']}</code>\n"
        f"🔗 یوزرنیم: {esc(username_text(r['username']))}\n"
        f"📦 پلن: <b>{esc(r['plan_title'])}</b>\n"
        f"💰 مبلغ: <b>{money(r['final_amount'])}</b>\n"
        f"📤 نوع تحویل: <b>{delivery_type}</b>\n"
        f"🕘 تاریخ تحویل: <b>{esc(delivered_at)}</b>\n"
        f"📅 تاریخ شمسی: <b>{jalali_date(delivered_at)}</b>\n\n"
        "🔐 <b>کانفیگ تحویل‌شده:</b>\n"
        f"<code>{esc(r['delivered_config'])}</code>",
        InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🧾 مشاهده سفارش",
                    callback_data=f"a:order:{r['order_id']}"
                ),
                InlineKeyboardButton(
                    "👤 پروفایل کاربر",
                    callback_data=f"a:user:{r['user_id']}"
                ),
            ],
            [InlineKeyboardButton(
                "↩️ لیست تحویل‌ها",
                callback_data=f"a:deliveryorders:{page}"
            )],
        ])
    )

async def render_test_delivery_history(q, page: int):
    ds = test_delivery_history_rows(page)
    more = len(ds) > 10
    items = ds[:10]

    if not items:
        await edit(
            q,
            "🧪 <b>تست‌های تحویل‌شده</b>\n\n"
            "📭 هنوز اکانت تستی تحویل داده نشده.",
            InlineKeyboardMarkup([
                [InlineKeyboardButton("↩️ تاریخچه تحویل", callback_data="a:deliverylog")]
            ])
        )
        return

    rows = []
    for r in items:
        name = str(r["full_name"] or "کاربر")
        preview = _config_preview(r["config_text"], 24)
        rows.append([
            InlineKeyboardButton(
                f"🧪 {name} • {preview}",
                callback_data=f"a:testdeliveryitem:{r['user_id']}:{page}"
            )
        ])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(
            "⬅️ قبلی",
            callback_data=f"a:testdeliveries:{page-1}"
        ))
    if more:
        nav.append(InlineKeyboardButton(
            "بعدی ➡️",
            callback_data=f"a:testdeliveries:{page+1}"
        ))
    if nav:
        rows.append(nav)

    rows.append([
        InlineKeyboardButton("↩️ تاریخچه تحویل", callback_data="a:deliverylog")
    ])

    await edit(
        q,
        f"🧪 <b>تست‌های تحویل‌شده</b>\n"
        f"صفحه {page+1}\n\n"
        "برای دیدن کاربر و کانفیگ کامل روی مورد بزن:",
        InlineKeyboardMarkup(rows)
    )

async def render_test_delivery_history_item(q, uid: int, page: int):
    r = test_delivery_history_item(uid)
    if not r:
        await answer(q, "این تست پیدا نشد.", True)
        await render_test_delivery_history(q, page)
        return

    await edit(
        q,
        "🧪 <b>جزئیات اکانت تست تحویل‌شده</b>\n\n"
        f"👤 کاربر: <b>{esc(r['full_name'] or '—')}</b>\n"
        f"🆔 آیدی: <code>{r['user_id']}</code>\n"
        f"🔗 یوزرنیم: {esc(username_text(r['username']))}\n"
        f"📦 شناسه موجودی تست: <code>#{r['inventory_id']}</code>\n"
        f"🕘 تاریخ تحویل: <b>{esc(r['claimed_at'])}</b>\n"
        f"📅 تاریخ شمسی: <b>{jalali_date(r['claimed_at'])}</b>\n\n"
        "🔐 <b>کانفیگ تست:</b>\n"
        f"<code>{esc(r['config_text'])}</code>",
        InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "👤 پروفایل کاربر",
                callback_data=f"a:user:{r['user_id']}"
            )],
            [InlineKeyboardButton(
                "↩️ لیست تست‌های تحویل‌شده",
                callback_data=f"a:testdeliveries:{page}"
            )],
        ])
    )

async def render_buyers(q, page: int):
    ds = buyer_rows(page)
    more = len(ds) > 10
    items = ds[:10]
    if not items:
        await edit(
            q,
            "👥 <b>خریداران</b>\n\n📭 هنوز خرید تکمیل‌شده‌ای ثبت نشده.",
            InlineKeyboardMarkup([
                [InlineKeyboardButton("↩️ سفارش‌ها", callback_data="a:orders")]
            ])
        )
        return

    rows = [
        [InlineKeyboardButton(
            f"👤 {r['full_name']} • {r['purchase_count']} خرید • {money(r['spent'])}",
            callback_data=f"a:buyerorders:{r['user_id']}:0"
        )]
        for r in items
    ]
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ قبلی", callback_data=f"a:buyers:{page-1}"))
    if more:
        nav.append(InlineKeyboardButton("بعدی ➡️", callback_data=f"a:buyers:{page+1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton("↩️ سفارش‌ها", callback_data="a:orders")])
    await edit(
        q,
        f"👥 <b>خریداران</b>\nصفحه {page+1}\n\n"
        "فقط کاربرانی که حداقل یک سفارش تکمیل‌شده دارند:",
        InlineKeyboardMarkup(rows)
    )

async def render_buyer_orders(q, uid: int, page: int):
    u = get_user(uid)
    if not u:
        await answer(q, "کاربر پیدا نشد.", True)
        return

    ds = buyer_orders(uid, page)
    more = len(ds) > 10
    items = ds[:10]

    with db() as c:
        stats = c.execute(
            "SELECT COUNT(*) n,COALESCE(SUM(final_amount),0) spent "
            "FROM orders WHERE user_id=? AND status=?",
            (uid, COMPLETED)
        ).fetchone()

    rows = [
        [InlineKeyboardButton(
            f"🧾 #{o['id']} • {str(o['plan_title'])[:24]} • {money(o['final_amount'])} • {jalali_date(o['completed_at'] or o['purchased_at'])}",
            callback_data=f"a:order:{o['id']}"
        )]
        for o in items
    ]
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ قبلی", callback_data=f"a:buyerorders:{uid}:{page-1}"))
    if more:
        nav.append(InlineKeyboardButton("بعدی ➡️", callback_data=f"a:buyerorders:{uid}:{page+1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton("👤 پروفایل کاربر", callback_data=f"a:user:{uid}")])
    rows.append([InlineKeyboardButton("↩️ خریداران", callback_data="a:buyers:0")])

    await edit(
        q,
        f"👤 <b>{esc(u['full_name'])}</b>\n"
        f"🆔 <code>{uid}</code>\n"
        f"🔗 {esc(username_text(u['username']))}\n"
        f"✅ خرید موفق: <b>{stats['n']}</b>\n"
        f"💰 مجموع خرید: <b>{money(stats['spent'])}</b>\n\n"
        f"سفارش‌های تکمیل‌شده • صفحه {page+1}:",
        InlineKeyboardMarkup(rows)
    )

async def render_coupons(q):
    with db() as c:
        cps = c.execute("SELECT * FROM coupons ORDER BY id DESC LIMIT 30").fetchall()
    rows = []
    for cp in cps:
        val = f"{cp['value']}%" if cp["kind"] == "percent" else money(cp["value"])
        rows.append([InlineKeyboardButton(
            f"{'✅' if cp['is_active'] else '⛔'} {cp['code']} • {val}",
            callback_data=f"a:coupon:{cp['id']}"
        )])
    rows += [
        [InlineKeyboardButton("➕ ساخت کد", callback_data="a:cadd")],
        [InlineKeyboardButton("🔙 پنل", callback_data="a:panel")],
    ]
    await edit(q, "🎟 <b>کدهای تخفیف</b>", InlineKeyboardMarkup(rows))

async def render_user(q, uid: int):
    u = get_user(uid)
    if not u:
        await answer(q, "کاربر پیدا نشد.", True)
        return

    with db() as c:
        total_orders = c.execute(
            "SELECT COUNT(*) FROM orders WHERE user_id=?", (uid,)
        ).fetchone()[0]
        successful = c.execute(
            "SELECT COUNT(*) FROM orders WHERE user_id=? AND status=?",
            (uid, COMPLETED)
        ).fetchone()[0]
        spent = c.execute(
            "SELECT COALESCE(SUM(final_amount),0) FROM orders "
            "WHERE user_id=? AND status=?",
            (uid, COMPLETED)
        ).fetchone()[0]

    recent_purchases = list(buyer_orders(uid, 0, 3))[:3]
    if recent_purchases:
        recent_purchase_text = "\n".join(
            f"• #{o['id']} | {esc(o['plan_title'])} | {money(o['final_amount'])} | "
            f"{jalali_date(o['completed_at'] or o['purchased_at'])}"
            for o in recent_purchases
        )
    else:
        recent_purchase_text = "خرید تکمیل‌شده‌ای ندارد."

    note = get_user_note(uid)
    review = get_test_review(uid)
    review_state = "—"
    if review:
        review_state = {
            "pending": "در انتظار تأیید 🟡",
            "approved": "تأییدشده ✅",
            "rejected": "ردشده ⛔",
        }.get(review["status"], str(review["status"]))

    suspicious = bool(u["test_review_required"])
    rows = [
        [InlineKeyboardButton(
            "✅ رفع مسدودی" if u["is_blocked"] else "⛔ مسدود کردن",
            callback_data=f"a:ublock:{uid}"
        )],
        [
            InlineKeyboardButton("📝 ثبت/ویرایش یادداشت", callback_data=f"a:unote:{uid}"),
            InlineKeyboardButton("💳 تغییر کیف پول", callback_data=f"a:walletadj:{uid}"),
        ],
        [
            InlineKeyboardButton(
                "✅ رفع بررسی تست" if suspicious else "🚨 مشکوک برای تست",
                callback_data=f"a:testsuspect:{uid}"
            ),
        ],
    ]

    if successful:
        rows.append([
            InlineKeyboardButton("🛒 همه خریدهای این کاربر", callback_data=f"a:buyerorders:{uid}:0", style="primary")
        ])

    if note:
        rows.append([
            InlineKeyboardButton("🗑 پاک‌کردن یادداشت", callback_data=f"a:unotedel:{uid}")
        ])

    if review and review["status"] == "pending":
        rows.append([
            InlineKeyboardButton("✅ تأیید تست", callback_data=f"a:testapprove:{uid}", style="success"),
            InlineKeyboardButton("❌ رد تست", callback_data=f"a:testreject:{uid}", style="danger"),
        ])

    if review:
        rows.append([
            InlineKeyboardButton("♻️ ریست وضعیت بررسی تست", callback_data=f"a:testreviewreset:{uid}")
        ])

    rows.extend([
        [InlineKeyboardButton("🔎 جست‌وجوی جدید", callback_data="a:users")],
        [InlineKeyboardButton("🔙 پنل", callback_data="a:panel")],
    ])

    await edit(
        q,
        f"👤 <b>پروفایل کاربر</b>\n\n"
        f"نام: {esc(u['full_name'])}\n"
        f"Username: {esc(username_text(u['username']))}\n"
        f"ID: <code>{uid}</code>\n"
        f"وضعیت: {'مسدود ⛔' if u['is_blocked'] else 'فعال ✅'}\n"
        f"{divider()}\n"
        f"🛒 کل سفارش‌ها: <b>{total_orders}</b>\n"
        f"✅ خرید موفق: <b>{successful}</b>\n"
        f"💰 مجموع خرید: <b>{money(spent)}</b>\n"
        f"🧾 <b>۳ خرید موفق اخیر:</b>\n{recent_purchase_text}\n"
        f"💳 کیف پول: <b>{money(wallet_balance(uid))}</b>\n"
        f"👑 سطح: <b>{esc(vip_tier(uid)[0])}</b>\n"
        f"🧪 وضعیت بررسی تست: <b>{review_state}</b>\n"
        f"🚨 بررسی اجباری تست: <b>{'فعال' if suspicious else 'خاموش'}</b>\n"
        f"{divider()}\n"
        f"📝 <b>یادداشت ادمین:</b>\n{esc(note) if note else 'ندارد'}",
        InlineKeyboardMarkup(rows)
    )

async def render_test_reviews(q, page: int):
    ds = pending_test_reviews(page)
    more = len(ds) > 10
    items = ds[:10]

    if not items:
        await edit(
            q,
            "🛡 <b>درخواست‌های بررسی تست</b>\n\n"
            "✅ موردی در انتظار تأیید نیست.",
            InlineKeyboardMarkup([
                [InlineKeyboardButton("↩️ مدیریت تست", callback_data="a:teststock")]
            ])
        )
        return

    rows = []
    for r in items:
        rows.append([
            InlineKeyboardButton(
                f"👤 {r['full_name']} • {r['user_id']}",
                callback_data=f"a:user:{r['user_id']}"
            )
        ])
        rows.append([
            InlineKeyboardButton("✅ تأیید تست", callback_data=f"a:testapprove:{r['user_id']}", style="success"),
            InlineKeyboardButton("❌ رد", callback_data=f"a:testreject:{r['user_id']}", style="danger"),
        ])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ قبلی", callback_data=f"a:testreviews:{page-1}"))
    if more:
        nav.append(InlineKeyboardButton("بعدی ➡️", callback_data=f"a:testreviews:{page+1}"))
    if nav:
        rows.append(nav)

    rows.append([InlineKeyboardButton("↩️ مدیریت تست", callback_data="a:teststock")])
    await edit(
        q,
        f"🛡 <b>درخواست‌های تست نیازمند بررسی</b>\n"
        f"صفحه {page+1}\n\n"
        "این کاربران تا تأیید شما هیچ کانفیگ تستی دریافت نمی‌کنند:",
        InlineKeyboardMarkup(rows)
    )

async def render_tickets(q, page: int):
    ds = list_tickets(page)
    more = len(ds) > PAGE_SIZE
    ds = ds[:PAGE_SIZE]
    rows = [[InlineKeyboardButton(
        f"🎫 #{t['id']} • {t['full_name']}", callback_data=f"a:ticket:{t['id']}"
    )] for t in ds]
    nav = []
    if page > 0: nav.append(InlineKeyboardButton("⬅️ قبلی", callback_data=f"a:tickets:{page-1}"))
    if more: nav.append(InlineKeyboardButton("بعدی ➡️", callback_data=f"a:tickets:{page+1}"))
    if nav: rows.append(nav)
    rows.append([InlineKeyboardButton("🔙 پنل", callback_data="a:panel")])
    await edit(q, f"🎫 <b>تیکت‌های باز</b>\nصفحه {page+1}", InlineKeyboardMarkup(rows))

async def render_settings(q):
    unpaid_h = to_int(setting("unpaid_order_expiry_hours", "24"))
    test_low = to_int(setting("test_low_stock_threshold", "3"))
    unpaid_text = "خاموش" if not unpaid_h else f"{unpaid_h} ساعت"

    await edit(
        q,
        "⚙️ <b>تنظیمات فروشگاه</b>\n\n"
        f"🏪 {esc(setting('shop_name'))}\n"
        f"💳 <code>{esc(setting('card_number'))}</code>\n"
        f"👤 {esc(setting('card_holder'))}\n"
        f"🆘 {esc(setting('support_username'))}\n"
        f"⚡ تحویل خودکار: {'روشن ✅' if setting_on('auto_delivery') else 'خاموش ⛔'}\n"
        f"🛠 تعمیرات: {'روشن ⛔' if setting_on('maintenance') else 'خاموش ✅'}\n"
        f"♻️ لغو سفارش بدون فیش: <b>{unpaid_text}</b>\n"
        f"🚨 حد هشدار موجودی تست: <b>{test_low if test_low is not None else 3}</b>",
        InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🏪 نام فروشگاه", callback_data="a:set:shop"),
                InlineKeyboardButton("💳 شماره کارت", callback_data="a:set:card"),
            ],
            [
                InlineKeyboardButton("👤 صاحب کارت", callback_data="a:set:holder"),
                InlineKeyboardButton("🆘 پشتیبانی", callback_data="a:set:support"),
            ],
            [InlineKeyboardButton("💬 متن خوش‌آمد", callback_data="a:set:welcome")],
            [
                InlineKeyboardButton("⚡ تحویل خودکار", callback_data="a:set:auto"),
                InlineKeyboardButton("🛠 تعمیرات", callback_data="a:set:maint"),
            ],
            [
                InlineKeyboardButton("♻️ زمان لغو سفارش", callback_data="a:set:unpaidhours"),
                InlineKeyboardButton("🚨 حد هشدار تست", callback_data="a:set:testlow"),
            ],
            [
                InlineKeyboardButton("💤 روز مشتری ازدست‌رفته", callback_data="a:set:lostdays"),
                InlineKeyboardButton("👑 حد VIP", callback_data="a:set:vipmin"),
            ],
            [InlineKeyboardButton("🎨 ظاهر منوی کاربر", callback_data="a:usericons")],
            [InlineKeyboardButton("🧪 اکانت تست 50MB", callback_data="a:teststock")],
            [InlineKeyboardButton("🔙 پنل", callback_data="a:panel")],
        ])
    )

