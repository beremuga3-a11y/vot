"""
Модуль для работы с админ журналом
"""
import sqlite3
import time
from typing import List, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram import InputMediaPhoto

# Импорты из общего модуля
from common import IMAGES


def get_admin_logs(limit: int = 20) -> List[sqlite3.Row]:
    """Получить последние записи из админ журнала"""
    from common import cur
    cur.execute(
        "SELECT user_id, action, ts FROM admin_logs ORDER BY ts DESC LIMIT ?",
        (limit,)
    )
    return cur.fetchall()


def get_admin_logs_by_user(user_id: int, limit: int = 20) -> List[sqlite3.Row]:
    """Получить записи журнала для конкретного пользователя"""
    from common import cur
    cur.execute(
        "SELECT user_id, action, ts FROM admin_logs WHERE user_id = ? ORDER BY ts DESC LIMIT ?",
        (user_id, limit)
    )
    return cur.fetchall()


def get_admin_logs_stats() -> dict:
    """Получить статистику админ журнала"""
    from common import cur
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


async def admin_view_logs(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать админ журнал"""
    from common import is_admin, edit_section, chunk_buttons
    if not is_admin(query.from_user.id):
        await edit_section(query, caption="❌ Доступ запрещён.", image_key="admin")
        return
    
    rows = get_admin_logs()
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
    """Поиск в админ журнале по ID пользователя"""
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
    """Показать статистику админ журнала"""
    if not is_admin(query.from_user.id):
        await edit_section(query, caption="❌ Доступ запрещён.", image_key="admin")
        return
    
    stats = get_admin_logs_stats()
    
    txt = f"📊 Статистика журнала:\n\n"
    txt += f"• Всего записей: {stats['total_logs']}\n"
    txt += f"• Уникальных пользователей: {stats['unique_users']}\n\n"
    txt += "Топ-5 действий:\n"
    for action in stats['top_actions']:
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
    """Обработка поиска в журнале"""
    if not context.user_data.get("awaiting_logs_search"):
        return
    
    try:
        user_id = int(update.message.text.strip())
        rows = get_admin_logs_by_user(user_id)
        
        if not rows:
            txt = f"📜 Записи для пользователя ID {user_id} не найдены."
        else:
            txt = f"📜 Записи для пользователя ID {user_id}:\n"
            for row in rows:
                t = time.strftime("%d.%m %H:%M", time.localtime(row["ts"]))
                txt += f"[{t}] {row['action']}\n"
        
        btns = [
            InlineKeyboardButton("🔍 Новый поиск", callback_data="admin_logs_search"),
            InlineKeyboardButton("⬅️ Назад к журналу", callback_data="admin_view_logs"),
        ]
        
        await update.message.reply_photo(
            photo=IMAGES.get("logs", "https://i.postimg.cc/fb1TQF6W/5355070803995131046.jpg"),
            caption=txt,
            reply_markup=InlineKeyboardMarkup(chunk_buttons(btns, per_row=2)),
        )
        
        context.user_data["awaiting_logs_search"] = False
        
    except ValueError:
        await update.message.reply_text("❌ Неверный формат ID. Введите число.")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")
        context.user_data["awaiting_logs_search"] = False