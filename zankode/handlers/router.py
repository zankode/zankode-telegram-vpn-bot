# -*- coding: utf-8 -*-
"""Callback-query router that delegates user and admin namespaces."""

from ..config import *
from ..utils import is_admin
from ..storage import blocked, setting_on, upsert_user
from ..ui import rate_limit
from ..services import answer
from .user import user_callback
from .admin import admin_callback

async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not q:
        return
    if q.message and q.message.chat.type != "private":
        await answer(q, "🔒 این دکمه فقط در چت خصوصی ربات کار می‌کند.", True)
        return
    upsert_user(q.from_user)
    if rate_limit(context, q.from_user.id, "cb", CB_COOLDOWN):
        await answer(q, "کمی آهسته‌تر 🙂")
        return
    data = q.data or ""

    if data.startswith("a:"):
        if not is_admin(q.from_user.id):
            await answer(q, "⛔ دسترسی ندارید.", True)
            return
        await answer(q)
        await admin_callback(q, context, data)
        return

    if blocked(q.from_user.id):
        await answer(q, "⛔ دسترسی شما مسدود شده.", True)
        return
    if setting_on("maintenance") and not is_admin(q.from_user.id):
        await answer(q, "🛠 حالت تعمیرات فعاله.", True)
        return

    await answer(q)
    await user_callback(q, context, data)

