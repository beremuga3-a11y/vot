"""
Админ журнал - модуль для работы с журналом действий администраторов
"""

import time
import sqlite3
from typing import List, Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

# Импорты из основного файла
from main import _execute, cur, edit_section, chunk_buttons, is_admin


async def admin_logs_view(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Просмотр журнала действий администраторов."""
    if not is_admin(query.from_user.id):
        await edit_section(query, caption="❌ Доступ запрещён.", image_key="admin")
        return
    
    cur.execute(
        "SELECT user_id, action, ts FROM admin_logs ORDER BY ts DESC LIMIT 20"
    )
    rows = cur.fetchall()
    
    if not rows:
        txt = "📜 Журнал пуст."
    else:
        txt = "📜 Последние действия игроков:\n"
        for row in rows:
            t = time.strftime("%d.%m %H:%M", time.localtime(row["ts"]))
            txt += f"[{t}] ID {row['user_id']}: {row['action']}\n"
    
    btns = [
        InlineKeyboardButton("🔍 Поиск по ID", callback_data="admin_logs_search"),
        InlineKeyboardButton("📊 Статистика", callback_data="admin_logs_stats"),
        InlineKeyboardButton("⬅️ Назад", callback_data="admin"),
    ]
    
    await edit_section(
        query,
        caption=txt,
        image_key="logs",
        reply_markup=InlineKeyboardMarkup(chunk_buttons(btns, per_row=2)),
    )


async def admin_logs_search(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Поиск в журнале по ID пользователя."""
    if not is_admin(query.from_user.id):
        await edit_section(query, caption="❌ Доступ запрещён.", image_key="admin")
        return
    
    context.user_data["awaiting_logs_search"] = True
    await edit_section(
        query,
        caption="🔍 Введите ID пользователя для поиска в журнале:",
        image_key="logs",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("⬅️ Отмена", callback_data="admin_view_logs")]]
        ),
    )


async def admin_logs_stats(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Статистика журнала."""
    if not is_admin(query.from_user.id):
        await edit_section(query, caption="❌ Доступ запрещён.", image_key="admin")
        return
    
    cur.execute("SELECT COUNT(*) as count FROM admin_logs")
    total_logs = cur.fetchone()["count"]
    cur.execute("SELECT COUNT(DISTINCT user_id) as count FROM admin_logs")
    unique_users = cur.fetchone()["count"]
    cur.execute("SELECT action, COUNT(*) as count FROM admin_logs GROUP BY action ORDER BY count DESC LIMIT 5")
    top_actions = cur.fetchall()
    
    txt = f"📊 Статистика журнала:\n\n"
    txt += f"• Всего записей: {total_logs}\n"
    txt += f"• Уникальных пользователей: {unique_users}\n\n"
    txt += "Топ-5 действий:\n"
    for action in top_actions:
        txt += f"• {action['action']}: {action['count']} раз\n"
    
    await edit_section(
        query,
        caption=txt,
        image_key="logs",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("⬅️ Назад", callback_data="admin_view_logs")]]
        ),
    )


async def handle_logs_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка поиска в журнале."""
    if not context.user_data.get("awaiting_logs_search"):
        return
    
    txt = update.message.text.strip()
    if not txt.isdigit():
        await update.message.reply_text("❌ Введите числовой ID пользователя.")
        return
    
    user_id = int(txt)
    cur.execute(
        "SELECT action, ts FROM admin_logs WHERE user_id = ? ORDER BY ts DESC LIMIT 20",
        (user_id,)
    )
    rows = cur.fetchall()
    
    if not rows:
        await update.message.reply_text(f"❌ Действия пользователя {user_id} не найдены в журнале.")
        context.user_data["awaiting_logs_search"] = False
        return
    
    txt_result = f"📜 Действия пользователя {user_id}:\n\n"
    for row in rows:
        t = time.strftime("%d.%m %H:%M", time.localtime(row["ts"]))
        txt_result += f"[{t}] {row['action']}\n"
    
    await update.message.reply_text(txt_result)
    context.user_data["awaiting_logs_search"] = False


def log_admin_action(user_id: int, action: str) -> None:
    """Записывает действие администратора в журнал."""
    _execute(
        "INSERT INTO admin_logs (user_id, action, ts) VALUES (?, ?, ?)",
        (user_id, action, int(time.time()))
    )


def get_admin_logs_stats() -> Dict[str, Any]:
    """Получает статистику журнала."""
    cur.execute("SELECT COUNT(*) as count FROM admin_logs")
    total_logs = cur.fetchone()["count"]
    
    cur.execute("SELECT COUNT(DISTINCT user_id) as count FROM admin_logs")
    unique_users = cur.fetchone()["count"]
    
    cur.execute("SELECT action, COUNT(*) as count FROM admin_logs GROUP BY action ORDER BY count DESC LIMIT 5")
    top_actions = cur.fetchall()
    
    return {
        "total_logs": total_logs,
        "unique_users": unique_users,
        "top_actions": top_actions
    }