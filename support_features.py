#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Support and extra player features module.

Provides:
- Tech support tickets with admin feedback and admin panel
- Simple and epic daily quests with secret reward (Yeti)

Expose entry points:
- extend_main_menu_buttons(user_id) -> list[InlineKeyboardButton]
- setup_support_features(app, conn, cur, helpers_dict)
- quest_progress_hook(cur, user_id, key, inc=1)
"""
from __future__ import annotations

import time
import sqlite3
from typing import Any, Dict, List, Tuple, Callable, Optional

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)


# -----------------------------
# Public API for main.py
# -----------------------------
def extend_main_menu_buttons(user_id: int) -> List[InlineKeyboardButton]:
    """Return extra main menu buttons to be appended by the host app."""
    return [
        InlineKeyboardButton("🆘 Техподдержка", callback_data="support"),
        InlineKeyboardButton("🎯 Квесты", callback_data="quests"),
        InlineKeyboardButton("🛡️ Админ: Тикеты", callback_data="support_admin"),
    ]


def setup_support_features(
    app: Application,
    conn: sqlite3.Connection,
    cur: sqlite3.Cursor,
    helpers: Dict[str, Callable[..., Any]],
) -> None:
    """Register handlers and ensure local tables.

    helpers must include: get_user, update_user, log_user_action, format_num
    Optional helpers: grant_pet(user_id, pet_key)
    """
    _ensure_tables(conn, cur)

    # Store references in closure for handlers
    state = {
        "conn": conn,
        "cur": cur,
        "get_user": helpers["get_user"],
        "update_user": helpers["update_user"],
        "log_user_action": helpers["log_user_action"],
        "format_num": helpers["format_num"],
        "grant_pet": helpers.get("grant_pet") or helpers.get("grant_secret_pet"),
    }

    # Our routers BEFORE host generic callback
    app.add_handler(CallbackQueryHandler(lambda u, c: _support_router(u, c, state), pattern=r"^(support|support_).*$"))
    app.add_handler(CallbackQueryHandler(lambda u, c: _quests_router(u, c, state), pattern=r"^(quests|quest_).*$"))

    # Message handler for awaiting states (support replies / new ticket text / quest claims via text)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, lambda u, c: _message_router(u, c, state)))

    # Admin buttons
    register_admin_reply_handler(app, state)
    _register_admin_panel_handlers(app, state)

    # Quest sync job from admin_logs
    try:
        app.job_queue.run_repeating(lambda ctx: _quest_log_cron(state), interval=60, first=20)
    except Exception:
        pass


# -----------------------------
# DB
# -----------------------------
def _execute(conn: sqlite3.Connection, cur: sqlite3.Cursor, sql: str, params: Tuple = ()) -> None:
    cur.execute(sql, params)
    conn.commit()


def _ensure_tables(conn: sqlite3.Connection, cur: sqlite3.Cursor) -> None:
    _execute(
        conn,
        cur,
        """
        CREATE TABLE IF NOT EXISTS support_tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT DEFAULT '',
            status TEXT DEFAULT 'open',
            created_at INTEGER,
            updated_at INTEGER
        );
        """,
    )
    # Attempt to backfill username column for older installs
    try:
        cur.execute("ALTER TABLE support_tickets ADD COLUMN username TEXT DEFAULT ''")
        conn.commit()
    except Exception:
        pass

    _execute(
        conn,
        cur,
        """
        CREATE TABLE IF NOT EXISTS support_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER,
            sender_id INTEGER,
            text TEXT,
            ts INTEGER,
            side TEXT CHECK(side IN ('user','admin')),
            FOREIGN KEY(ticket_id) REFERENCES support_tickets(id)
        );
        """,
    )
    _execute(
        conn,
        cur,
        """
        CREATE TABLE IF NOT EXISTS daily_quests (
            user_id INTEGER,
            quest_key TEXT,
            progress INTEGER DEFAULT 0,
            goal INTEGER DEFAULT 1,
            claimed INTEGER DEFAULT 0,
            day INTEGER,
            PRIMARY KEY (user_id, quest_key, day)
        );
        """,
    )
    _execute(
        conn,
        cur,
        """
        CREATE TABLE IF NOT EXISTS support_state (
            id INTEGER PRIMARY KEY CHECK(id=1),
            last_admin_log_id INTEGER DEFAULT 0
        );
        """,
    )
    cur.execute("SELECT 1 FROM support_state WHERE id = 1")
    if cur.fetchone() is None:
        _execute(conn, cur, "INSERT INTO support_state (id, last_admin_log_id) VALUES (1, 0)")

    _execute(
        conn,
        cur,
        """
        CREATE TABLE IF NOT EXISTS secret_rewards (
            user_id INTEGER,
            reward_key TEXT,
            day INTEGER,
            PRIMARY KEY (user_id, reward_key)
        );
        """,
    )


# -----------------------------
# Support flows
# -----------------------------
async def _support_router(update: Update, context: ContextTypes.DEFAULT_TYPE, s: Dict[str, Any]) -> None:
    query = update.callback_query
    await _safe_answer(query)
    data = query.data
    if data == "support":
        await _support_menu(query)
        return
    if data == "support_new":
        # Step 1: ask username, then message
        context.user_data.pop("support_username", None)
        context.user_data["awaiting_support_username"] = True
        await query.edit_message_caption(
            caption="🆘 Укажите ваш @юзернейм одним сообщением (пример: @nickname).",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="support")]]),
        )
        return
    if data == "support_my":
        await _support_list_my(query, s)
        return
    if data.startswith("support_view_"):
        ticket_id = int(data.split("_")[-1])
        await _support_view_ticket(query, s, ticket_id)
        return
    if data.startswith("support_user_reply_"):
        ticket_id = int(data.split("_")[-1])
        context.user_data["awaiting_support_user_reply_ticket"] = ticket_id
        await query.edit_message_caption(
            caption=f"✍️ Введите сообщение для тикета #{ticket_id} одним сообщением.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data=f"support_view_{ticket_id}")]]),
        )
        return


async def _message_router(update: Update, context: ContextTypes.DEFAULT_TYPE, s: Dict[str, Any]) -> None:
    # New ticket flow: username -> message
    if context.user_data.get("awaiting_support_username"):
        username = (update.message.text or "").strip()
        if not username.startswith("@") or len(username) < 3:
            await update.message.reply_text("❌ Укажите корректный @юзернейм (пример: @nickname).")
            return
        context.user_data["awaiting_support_username"] = False
        context.user_data["support_username"] = username
        context.user_data["awaiting_support_text"] = True
        await update.message.reply_text("✍️ Теперь опишите ваш вопрос/жалобу одним сообщением.")
        return
    if context.user_data.get("awaiting_support_text"):
        context.user_data["awaiting_support_text"] = False
        provided_username = context.user_data.get("support_username") or ""
        await _support_create_ticket(update, context, s, provided_username)
        return
    # Admin reply flow
    if context.user_data.get("awaiting_support_reply_ticket"):
        ticket_id = context.user_data.pop("awaiting_support_reply_ticket")
        await _support_admin_reply(update, s, int(ticket_id))
        return
    # User reply to existing ticket
    if context.user_data.get("awaiting_support_user_reply_ticket"):
        ticket_id = int(context.user_data.pop("awaiting_support_user_reply_ticket"))
        await _support_user_reply(update, s, ticket_id)
        return


async def _support_menu(query) -> None:
    btns = [
        InlineKeyboardButton("📝 Новая заявка", callback_data="support_new"),
        InlineKeyboardButton("📂 Мои заявки", callback_data="support_my"),
        InlineKeyboardButton("⬅️ Назад", callback_data="back"),
    ]
    kb = InlineKeyboardMarkup([btns[:2], [btns[2]]])
    await query.edit_message_caption(caption="🆘 Техподдержка", reply_markup=kb)


async def _support_create_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE, s: Dict[str, Any], provided_username: str) -> None:
    user = update.effective_user
    text = (update.message.text or "").strip()
    now = int(time.time())
    username = provided_username or (user.username and f"@{user.username}") or "@unknown"
    _execute(
        s["conn"],
        s["cur"],
        "INSERT INTO support_tickets (user_id, username, status, created_at, updated_at) VALUES (?,?,?,?,?)",
        (user.id, username, "open", now, now),
    )
    ticket_id = s["cur"].lastrowid
    _execute(
        s["conn"], s["cur"],
        "INSERT INTO support_messages (ticket_id, sender_id, text, ts, side) VALUES (?,?,?,?,?)",
        (ticket_id, user.id, text, now, "user"),
    )
    s["log_user_action"](user.id, f"Создал тикет #{ticket_id}")
    await update.message.reply_text(f"✅ Заявка #{ticket_id} создана. Ожидайте ответа администратора.")
    # Notify admins
    try:
        s["cur"].execute("SELECT user_id FROM admin_users")
        for (admin_id,) in s["cur"].fetchall():
            try:
                await update.get_bot().send_message(
                    admin_id,
                    f"🆘 Новая заявка #{ticket_id} от {username} (ID{user.id}):\n{text}",
                    reply_markup=InlineKeyboardMarkup(
                        [[InlineKeyboardButton("✉️ Ответить", callback_data=f"support_reply_{ticket_id}")]]
                    ),
                )
            except Exception:
                pass
    except Exception:
        pass


async def _support_list_my(query, s: Dict[str, Any]) -> None:
    uid = query.from_user.id
    s["cur"].execute(
        "SELECT id, status, updated_at FROM support_tickets WHERE user_id = ? ORDER BY updated_at DESC LIMIT 10",
        (uid,),
    )
    rows = s["cur"].fetchall()
    if not rows:
        await query.edit_message_caption(
            caption="❌ У вас нет заявок.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="support")]]),
        )
        return
    lines = ["📂 Ваши заявки:"]
    btns: List[List[InlineKeyboardButton]] = []
    for r in rows:
        t = time.strftime("%d.%m %H:%M", time.localtime(r[2]))
        lines.append(f"• #{r[0]} — {r[1]} (обновлено {t})")
        btns.append([InlineKeyboardButton(f"Открыть #{r[0]}", callback_data=f"support_view_{r[0]}")])
    btns.append([InlineKeyboardButton("⬅️ Назад", callback_data="support")])
    await query.edit_message_caption(caption="\n".join(lines), reply_markup=InlineKeyboardMarkup(btns))


async def _support_view_ticket(query, s: Dict[str, Any], ticket_id: int) -> None:
    s["cur"].execute("SELECT id, status FROM support_tickets WHERE id = ?", (ticket_id,))
    t = s["cur"].fetchone()
    if not t:
        await query.edit_message_caption(caption="❌ Тикет не найден.")
        return
    s["cur"].execute(
        "SELECT side, text, ts FROM support_messages WHERE ticket_id = ? ORDER BY id ASC",
        (ticket_id,),
    )
    msgs = s["cur"].fetchall()
    lines = [f"🗂️ Тикет #{ticket_id} — {t[1]}"]
    for side, text, ts in msgs:
        who = "👤 Вы" if side == "user" else "🛡️ Админ"
        lines.append(f"[{time.strftime('%d.%m %H:%M', time.localtime(ts))}] {who}: {text}")
    btns: List[List[InlineKeyboardButton]] = []
    if t[1] == "open":
        btns.append([InlineKeyboardButton("✍️ Написать", callback_data=f"support_user_reply_{ticket_id}")])
    btns.append([InlineKeyboardButton("⬅️ Назад", callback_data="support_my")])
    kb = InlineKeyboardMarkup(btns)
    await query.edit_message_caption(caption="\n".join(lines[-50:]), reply_markup=kb)


async def _quests_router(update: Update, context: ContextTypes.DEFAULT_TYPE, s: Dict[str, Any]) -> None:
    query = update.callback_query
    await _safe_answer(query)
    data = query.data
    if data == "quests":
        await _quests_menu(query, s)
        return
    if data.startswith("quest_claim_"):
        key = data.split("_", 2)[2]
        await _quest_claim(query, s, key)
        return


async def _support_admin_gate(update: Update, s: Dict[str, Any]) -> bool:
    uid = update.effective_user.id
    s["cur"].execute("SELECT 1 FROM admin_users WHERE user_id = ?", (uid,))
    return s["cur"].fetchone() is not None


async def _support_admin_reply(update: Update, s: Dict[str, Any], ticket_id: int) -> None:
    if not await _support_admin_gate(update, s):
        return
    text = (update.message.text or "").strip()
    now = int(time.time())
    # Find ticket owner
    s["cur"].execute("SELECT user_id FROM support_tickets WHERE id = ?", (ticket_id,))
    row = s["cur"].fetchone()
    if not row:
        await update.message.reply_text("❌ Тикет не найден.")
        return
    user_id = row[0]
    _execute(
        s["conn"],
        s["cur"],
        "INSERT INTO support_messages (ticket_id, sender_id, text, ts, side) VALUES (?,?,?,?,?)",
        (ticket_id, update.effective_user.id, text, now, "admin"),
    )
    _execute(s["conn"], s["cur"], "UPDATE support_tickets SET updated_at = ? WHERE id = ?", (now, ticket_id))
    try:
        await update.get_bot().send_message(user_id, f"🛡️ Ответ админа по заявке #{ticket_id}:\n{text}")
    except Exception:
        pass
    await update.message.reply_text(f"✅ Ответ отправлен пользователю (тикет #{ticket_id}).")


async def _support_user_reply(update: Update, s: Dict[str, Any], ticket_id: int) -> None:
    text = (update.message.text or "").strip()
    now = int(time.time())
    s["cur"].execute("SELECT status FROM support_tickets WHERE id = ? AND user_id = ?", (ticket_id, update.effective_user.id))
    row = s["cur"].fetchone()
    if not row:
        await update.message.reply_text("❌ Тикет не найден.")
        return
    if row[0] != "open":
        await update.message.reply_text("🔒 Диалог закрыт. Создайте новую заявку при необходимости.")
        return
    _execute(
        s["conn"], s["cur"],
        "INSERT INTO support_messages (ticket_id, sender_id, text, ts, side) VALUES (?,?,?,?,?)",
        (ticket_id, update.effective_user.id, text, now, "user"),
    )
    _execute(s["conn"], s["cur"], "UPDATE support_tickets SET updated_at = ? WHERE id = ?", (now, ticket_id))
    await update.message.reply_text(f"✅ Сообщение добавлено в тикет #{ticket_id}.")


# -----------------------------
# Daily quests
# -----------------------------
def _today_daynum() -> int:
    return int(time.time() // 86400)


def ensure_daily_quests_for_user(cur: sqlite3.Cursor, user_id: int) -> None:
    day = _today_daynum()
    base = [
        ("buy_any", 1),
        ("feed_any", 1),
        ("casino_try", 1),
        # Epic tasks
        ("buy_3", 3),
        ("feed_5", 5),
        ("casino_win", 1),
        ("rich_100k", 1),
    ]
    for key, goal in base:
        cur.execute(
            "INSERT OR IGNORE INTO daily_quests (user_id, quest_key, progress, goal, claimed, day) VALUES (?,?,?,?,0,?)",
            (user_id, key, 0, goal, day),
        )


async def _quests_menu(query, s: Dict[str, Any]) -> None:
    uid = query.from_user.id
    ensure_daily_quests_for_user(s["cur"], uid)
    s["cur"].execute(
        "SELECT quest_key, progress, goal, claimed FROM daily_quests WHERE user_id = ? AND day = ?",
        (uid, _today_daynum()),
    )
    rows = s["cur"].fetchall()
    names = {
        "buy_any": "Купить любого питомца",
        "feed_any": "Покормить питомца",
        "casino_try": "Сыграть в казино",
        "buy_3": "Купить 3 питомцев",
        "feed_5": "Покормить 5 раз",
        "casino_win": "Выиграть в казино",
        "rich_100k": "Достигнуть баланса 100 000🪙",
    }
    lines = ["🎯 Ежедневные квесты:", "После выполнения всех эпик-квестов вы получите секретного питомца: Йети!"]
    btns: List[List[InlineKeyboardButton]] = []
    for key, progress, goal, claimed in rows:
        status = "✅ Выполнено" if progress >= goal else f"{progress}/{goal}"
        lines.append(f"• {names.get(key, key)} — {status}")
        if progress >= goal and not claimed:
            btns.append([InlineKeyboardButton(f"Получить награду ({key})", callback_data=f"quest_claim_{key}")])
    btns.append([InlineKeyboardButton("⬅️ Назад", callback_data="back")])
    await query.edit_message_caption(caption="\n".join(lines), reply_markup=InlineKeyboardMarkup(btns))


async def _quest_claim(query, s: Dict[str, Any], key: str) -> None:
    uid = query.from_user.id
    s["cur"].execute(
        "SELECT progress, goal, claimed FROM daily_quests WHERE user_id = ? AND quest_key = ? AND day = ?",
        (uid, key, _today_daynum()),
    )
    row = s["cur"].fetchone()
    if not row:
        await query.edit_message_caption(caption="❌ Квест не найден.")
        return
    progress, goal, claimed = row
    if progress < goal or claimed:
        await _quests_menu(query, s)
        return
    # Simple reward: 500 coins per quest
    reward = 500
    user = s["get_user"](uid)
    s["update_user"](uid, coins=user["coins"] + reward, weekly_coins=user["weekly_coins"] + reward)
    _execute(s["conn"], s["cur"],
             "UPDATE daily_quests SET claimed = 1 WHERE user_id = ? AND quest_key = ? AND day = ?",
             (uid, key, _today_daynum()))
    s["log_user_action"](uid, f"Получил награду за квест {key}: {reward}🪙")
    await _maybe_grant_yeti_after_epics(uid, s)
    await query.edit_message_caption(caption=f"✅ Награда за квест получена: {s['format_num'](reward)}🪙",
                                     reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="quests")]]))


# -----------------------------
# Utilities
# -----------------------------
async def _safe_answer(query) -> None:
    try:
        await query.answer()
    except Exception:
        pass


# Exposed helper to be called by host actions to increment quest progress
def quest_progress_hook(cur: sqlite3.Cursor, user_id: int, key: str, inc: int = 1) -> None:
    day = _today_daynum()
    cur.execute(
        "UPDATE daily_quests SET progress = MIN(goal, progress + ?) WHERE user_id = ? AND quest_key = ? AND day = ?",
        (inc, user_id, key, day),
    )


# Admin-only callback entry for replying
def register_admin_reply_handler(app: Application, state: Dict[str, Any]) -> None:
    async def on_support_admin_reply_press(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        await _safe_answer(query)
        if not await _support_admin_gate(update, state):
            await query.edit_message_caption(caption="❌ Доступ запрещён.")
            return
        ticket_id = int(query.data.split("_")[-1])
        context.user_data["awaiting_support_reply_ticket"] = ticket_id
        await query.edit_message_caption(caption=f"✍️ Введите ответ для заявки #{ticket_id} одним сообщением.")

    app.add_handler(CallbackQueryHandler(on_support_admin_reply_press, pattern=r"^support_reply_\d+$"))


def _register_admin_panel_handlers(app: Application, state: Dict[str, Any]) -> None:
    async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        await _safe_answer(query)
        if not await _support_admin_gate(update, state):
            await query.edit_message_caption(caption="❌ Доступ запрещён.")
            return
        # List last 20 open tickets
        state["cur"].execute(
            "SELECT id, user_id, username, updated_at FROM support_tickets WHERE status = 'open' ORDER BY updated_at DESC LIMIT 20"
        )
        rows = state["cur"].fetchall()
        if not rows:
            await query.edit_message_caption(
                caption="🛡️ Открытых тикетов нет.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Обновить", callback_data="support_admin")]]),
            )
            return
        lines = ["🛡️ Админ панель — открытые тикеты:"]
        btns: List[List[InlineKeyboardButton]] = []
        for tid, uid, uname, ts in rows:
            t = time.strftime("%d.%m %H:%M", time.localtime(ts))
            lines.append(f"• #{tid} от {uname or 'ID'+str(uid)} (обновл. {t})")
            btns.append([
                InlineKeyboardButton(f"Открыть #{tid}", callback_data=f"support_view_{tid}"),
                InlineKeyboardButton("✉️ Ответить", callback_data=f"support_reply_{tid}"),
                InlineKeyboardButton("🔒 Закрыть", callback_data=f"support_close_{tid}"),
            ])
        btns.append([InlineKeyboardButton("🔄 Обновить", callback_data="support_admin")])
        await query.edit_message_caption(caption="\n".join(lines), reply_markup=InlineKeyboardMarkup(btns))

    async def admin_close(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        await _safe_answer(query)
        if not await _support_admin_gate(update, state):
            await query.edit_message_caption(caption="❌ Доступ запрещён.")
            return
        ticket_id = int(query.data.split("_")[-1])
        _execute(state["conn"], state["cur"], "UPDATE support_tickets SET status='closed' WHERE id = ?", (ticket_id,))
        await query.edit_message_caption(caption=f"🔒 Тикет #{ticket_id} закрыт.",
                                         reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ К списку", callback_data="support_admin")]]))

    app.add_handler(CallbackQueryHandler(admin_panel, pattern=r"^support_admin$"))
    app.add_handler(CallbackQueryHandler(admin_close, pattern=r"^support_close_\d+$"))


# -----------------------------
# Quest progress via admin_logs scanner
# -----------------------------
def _quest_log_cron(s: Dict[str, Any]) -> None:
    cur = s["cur"]
    conn = s["conn"]
    cur.execute("SELECT last_admin_log_id FROM support_state WHERE id = 1")
    row = cur.fetchone()
    last_id = row[0] if row else 0
    cur.execute(
        "SELECT id, user_id, action FROM admin_logs WHERE id > ? ORDER BY id ASC LIMIT 200",
        (last_id,),
    )
    logs = cur.fetchall()
    if not logs:
        return
    today = _today_daynum()
    for log_id, user_id, action in logs:
        key: Optional[str] = None
        a = action.lower()
        if a.startswith("купил "):
            key = "buy_any"
            cur.execute(
                "INSERT OR IGNORE INTO daily_quests (user_id, quest_key, progress, goal, claimed, day) VALUES (?,?,?,?,0,?)",
                (user_id, "buy_3", 0, 3, today),
            )
            cur.execute(
                "UPDATE daily_quests SET progress = MIN(goal, progress + 1) WHERE user_id = ? AND quest_key = ? AND day = ?",
                (user_id, "buy_3", today),
            )
        elif a.startswith("кормил "):
            key = "feed_any"
            cur.execute(
                "INSERT OR IGNORE INTO daily_quests (user_id, quest_key, progress, goal, claimed, day) VALUES (?,?,?,?,0,?)",
                (user_id, "feed_5", 0, 5, today),
            )
            cur.execute(
                "UPDATE daily_quests SET progress = MIN(goal, progress + 1) WHERE user_id = ? AND quest_key = ? AND day = ?",
                (user_id, "feed_5", today),
            )
        elif "казино" in a:
            key = "casino_try"
            if "выиграл" in a or "победа" in a or "win" in a:
                cur.execute(
                    "INSERT OR IGNORE INTO daily_quests (user_id, quest_key, progress, goal, claimed, day) VALUES (?,?,?,?,0,?)",
                    (user_id, "casino_win", 0, 1, today),
                )
                cur.execute(
                    "UPDATE daily_quests SET progress = 1 WHERE user_id = ? AND quest_key = ? AND day = ?",
                    (user_id, "casino_win", today),
                )
        elif "баланс" in a or "balance" in a:
            for token in ["100000", "100 000", "100k"]:
                if token in a:
                    cur.execute(
                        "INSERT OR IGNORE INTO daily_quests (user_id, quest_key, progress, goal, claimed, day) VALUES (?,?,?,?,0,?)",
                        (user_id, "rich_100k", 0, 1, today),
                    )
                    cur.execute(
                        "UPDATE daily_quests SET progress = 1 WHERE user_id = ? AND quest_key = ? AND day = ?",
                        (user_id, "rich_100k", today),
                    )
                    break
        if key:
            cur.execute(
                "INSERT OR IGNORE INTO daily_quests (user_id, quest_key, progress, goal, claimed, day) VALUES (?,?,?,?,0,?)",
                (user_id, key, 0, 1, today),
            )
            cur.execute(
                "UPDATE daily_quests SET progress = MIN(goal, progress + 1) WHERE user_id = ? AND quest_key = ? AND day = ?",
                (user_id, key, today),
            )
        last_id = log_id
    _execute(conn, cur, "UPDATE support_state SET last_admin_log_id = ? WHERE id = 1", (last_id,))


# -----------------------------
# Epic completion reward: Yeti
# -----------------------------
async def _maybe_grant_yeti_after_epics(user_id: int, s: Dict[str, Any]) -> None:
    epic_keys = {"buy_3", "feed_5", "casino_win", "rich_100k"}
    day = _today_daynum()
    s["cur"].execute(
        "SELECT quest_key, claimed FROM daily_quests WHERE user_id = ? AND day = ? AND quest_key IN (?,?,?,?)",
        (user_id, day, *list(epic_keys)),
    )
    rows = s["cur"].fetchall()
    have = {k for k, claimed in rows if claimed}
    if not epic_keys.issubset(have):
        return
    s["cur"].execute("SELECT 1 FROM secret_rewards WHERE user_id = ? AND reward_key = 'yeti'", (user_id,))
    if s["cur"].fetchone():
        return
    grant = s.get("grant_pet")
    try:
        if callable(grant):
            grant(user_id, pet_key="yeti")  # provided by host if available
            s["log_user_action"](user_id, "Получил секретного питомца: Йети")
        else:
            user = s["get_user"](user_id)
            bonus = 100_000
            s["update_user"](user_id, coins=user["coins"] + bonus, weekly_coins=user["weekly_coins"] + bonus)
            s["log_user_action"](user_id, f"Секретная награда за эпик-квесты: {bonus}🪙 (Йети)")
    finally:
        _execute(s["conn"], s["cur"], "INSERT OR REPLACE INTO secret_rewards (user_id, reward_key, day) VALUES (?,?,?)", (user_id, "yeti", day))

