# -*- coding: utf-8 -*-
"""
Daily Case mini-game (separate fun feature).
Expose:
- extend_main_menu_buttons_extra() -> buttons list (optional)
- setup_fun_cases(app, conn, cur, helpers)
"""
from __future__ import annotations

import random
import sqlite3
from typing import Any, Dict, List, Callable

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes


def extend_main_menu_buttons_extra() -> List[InlineKeyboardButton]:
    return [InlineKeyboardButton("🎁 Ежедневный кейс", callback_data="fun_case")]


def setup_fun_cases(app: Application, conn: sqlite3.Connection, cur: sqlite3.Cursor, helpers: Dict[str, Callable[..., Any]]) -> None:
    _ensure_tables(conn, cur)
    state = {
        "conn": conn,
        "cur": cur,
        "get_user": helpers["get_user"],
        "update_user": helpers["update_user"],
        "log_user_action": helpers["log_user_action"],
        "format_num": helpers["format_num"],
        "grant_pet": helpers.get("grant_pet"),
    }
    app.add_handler(CallbackQueryHandler(lambda u, c: _router(u, c, state), pattern=r"^(fun_case|fun_case_open)$"))


def _ensure_tables(conn: sqlite3.Connection, cur: sqlite3.Cursor) -> None:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS fun_case_state (
            user_id INTEGER PRIMARY KEY,
            last_open_day INTEGER DEFAULT 0
        )
        """
    )
    conn.commit()


def _today_daynum() -> int:
    import time as _t
    return int(_t.time() // 86400)


async def _router(update: Update, context: ContextTypes.DEFAULT_TYPE, s: Dict[str, Any]) -> None:
    q = update.callback_query
    await _safe_answer(q)
    data = q.data
    if data == "fun_case":
        await q.edit_message_caption(
            caption="🎁 Ежедневный кейс: шанс на монеты или редкий дроп!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Открыть", callback_data="fun_case_open")],
                                               [InlineKeyboardButton("⬅️ Назад", callback_data="back")]]),
        )
        return
    if data == "fun_case_open":
        await _open_case(q, s)


async def _open_case(q, s: Dict[str, Any]) -> None:
    uid = q.from_user.id
    day = _today_daynum()
    s["cur"].execute("SELECT last_open_day FROM fun_case_state WHERE user_id = ?", (uid,))
    row = s["cur"].fetchone()
    if row and row[0] == day:
        await q.edit_message_caption(caption="⏳ Кейс уже открыт сегодня. Возвращайтесь завтра!",
                                     reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="back")]]))
        return
    # Rewards: weighted
    rewards = [
        ("coins", 500, 50),
        ("coins", 1000, 25),
        ("coins", 5000, 10),
        ("pet", "yeti", 1),       # ultra rare
        ("coins", 20000, 3),
        ("coins", 100, 11),
    ]
    population = []
    for kind, val, weight in rewards:
        population.extend([(kind, val)] * weight)
    kind, val = random.choice(population)
    if kind == "coins":
        user = s["get_user"](uid)
        s["update_user"](uid, coins=user["coins"] + int(val), weekly_coins=user["weekly_coins"] + int(val))
        s["log_user_action"](uid, f"Открыл кейс: {val}🪙")
        msg = f"🎉 Вы получили {s['format_num'](int(val))}🪙!"
    else:
        grant = s.get("grant_pet")
        if callable(grant):
            try:
                grant(uid, pet_key=str(val))
                s["log_user_action"](uid, f"Открыл кейс: питомец {val}")
                msg = f"🧊 Невероятно! Вам выпал питомец: {val}!"
            except Exception:
                msg = "😅 Не удалось выдать питомца, но вы получаете 10 000🪙."
                user = s["get_user"](uid)
                s["update_user"](uid, coins=user["coins"] + 10_000, weekly_coins=user["weekly_coins"] + 10_000)
        else:
            msg = "🎊 Почти питомец! Взамен бонус 10 000🪙."
            user = s["get_user"](uid)
            s["update_user"](uid, coins=user["coins"] + 10_000, weekly_coins=user["weekly_coins"] + 10_000)

    s["cur"].execute("INSERT OR REPLACE INTO fun_case_state (user_id, last_open_day) VALUES (?, ?)", (uid, day))
    s["conn"].commit()
    await q.edit_message_caption(caption=f"🎁 Ежедневный кейс\n{msg}",
                                 reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="back")]]))


async def _safe_answer(query) -> None:
    try:
        await query.answer()
    except Exception:
        pass

