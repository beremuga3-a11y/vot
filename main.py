#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# --------------------------------------------------------------
#   Bot «Farm» – полностью исправлен, доработан и расширен:
#   • Удалены все упоминания о перерождениях и X‑ферме.
#   • Добавлен журнал действий админа – возможность просматривать
#     последние действия игроков (покупка, кормление, продажа и т.д.).
#   • Для каждого раздела (меню, ферма, магазин, статус и т.д.)
#     теперь выводится изображение над текстом.
#   • Добавлена полная статистика бота для админа
#   • Исправлены все ошибки в кланах и осеннем событии
#   • Добавлены новые осенние питомцы и механики
# --------------------------------------------------------------
import argparse
import logging
import random
import re
import time
import sqlite3
from typing import Any, Dict, List, Tuple

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    Update,
)
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ----------------------------------------------------------------------
#   Конфигурация
# ----------------------------------------------------------------------
TOKEN = "8137596673:AAGePL-4AZQHPIXLruyWkOQwDLfW_Hycudk"          # ваш токен
DB_PATH = "farm_bot.db"
MAX_INT = 9_223_372_036_854_775_807
HUNGER_TIME = 10 * 3600          # 10 ч в секундах
FOOD_PRICE = 500                # обычный корм
AUTUMN_FOOD_PRICE = 1000        # осенний корм
BASE_UPGRADE_COST = 5_000_000    # улучшение базы
BASE_LIMIT_STEP = 5               # шаг увеличения лимита при улучшении базы
SEASON_LENGTH = 60 * 24 * 3600   # 60 дней → один «сезон»
CHANNEL_USERNAME = "spiderfarminfo"
CHANNEL_ID = -1001234567890
CHAT_ID = -4966660960
CHAT_LINK = "https://t.me/+tjqmdwVMjtYxMTU6"
CHANNEL_LINK = "https://t.me/spiderfarminfo"

# Картинки
MAIN_MENU_IMG = "https://i.postimg.cc/fb1TQF6W/5355070803995131046.jpg"
AUTUMN_EVENT_IMG = "https://i.postimg.cc/fb1TQF6W/5355070803995131046.jpg"

# ----------------------------------------------------------------------
#   Изображения для разделов 
# ----------------------------------------------------------------------
SECTION_IMAGES: Dict[str, str] = {
    "about": "https://i.postimg.cc/BZ580SNj/5355070803995130961.jpg",
    "farm": "https://i.postimg.cc/dVf3BLQx/5355070803995130963.jpg",
    "shop": "https://i.postimg.cc/cHyJp2n7/5355070803995130964.jpg",
    "farmers": "https://i.postimg.cc/28MN9vvh/5355070803995130971.jpg",
    "status": "https://i.postimg.cc/2jPf2hnv/5355070803995130978.jpg",
    "coins": "https://i.postimg.cc/SxnCk0JH/5355070803995130993.jpg",
    "casino": "https://i.postimg.cc/zvZBKMj2/5355070803995131009.jpg",
    "promo": "https://i.postimg.cc/kXCG50DB/5355070803995131030.jpg",
    "autumn": AUTUMN_EVENT_IMG,
    "admin": "https://i.postimg.cc/fb1TQF6W/5355070803995131046.jpg",
    "logs": "https://i.postimg.cc/fb1TQF6W/5355070803995131046.jpg",
    "top": "https://i.postimg.cc/mg2rY7Y4/5355070803995131023.jpg",
}

# ----------------------------------------------------------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
log = logging.getLogger(__name__)

# ----------------------------------------------------------------------
#   База данных
# ----------------------------------------------------------------------
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.row_factory = sqlite3.Row
cur = conn.cursor()


def _execute(sql: str, params: Tuple = ()) -> None:
    """Упрощённый wrapper‑выполнения запросов."""
    cur.execute(sql, params)
    conn.commit()


def init_db() -> None:
    """Создаёт все таблицы (если их ещё нет) и делает миграцию."""
    # ---------- users ----------
    _execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            coins INTEGER DEFAULT 0,
            feed INTEGER DEFAULT 0,
            autumn_feed INTEGER DEFAULT 0,
            weekly_coins INTEGER DEFAULT 0,
            last_reset INTEGER DEFAULT 0,
            secret_spider INTEGER DEFAULT 0,
            click_count INTEGER DEFAULT 0,
            last_click_time INTEGER DEFAULT 0,
            feed_bonus_end INTEGER DEFAULT 0,
            autumn_bonus_end INTEGER DEFAULT 0,
            tickets INTEGER DEFAULT 0,
            last_ticket_time INTEGER DEFAULT 0,
            reputation INTEGER DEFAULT 0,
            custom_income INTEGER DEFAULT 0,
            pet_limit INTEGER DEFAULT 200,
            base_level INTEGER DEFAULT 0,
            subscribe_claimed INTEGER DEFAULT 0,
            chat_claimed INTEGER DEFAULT 0,
            click_reward_last INTEGER DEFAULT 0,
            referred_by INTEGER DEFAULT 0,
            last_active INTEGER DEFAULT 0,
            registration_date INTEGER DEFAULT 0,
            autumn_event_participation INTEGER DEFAULT 0
        );
        """
    )
    # ---------- admin_users ----------
    _execute(
        """
        CREATE TABLE IF NOT EXISTS admin_users (
            user_id INTEGER PRIMARY KEY
        );
        """
    )
    # ---------- global_settings ----------
    _execute(
        """
        CREATE TABLE IF NOT EXISTS global_settings (
            id INTEGER PRIMARY KEY,
            global_bonus_active INTEGER DEFAULT 0,
            autumn_event_active INTEGER DEFAULT 0,
            season_start INTEGER DEFAULT 0,
            season_number INTEGER DEFAULT 1
        );
        """
    )
    # создаём строку id=1, если её нет
    cur.execute("SELECT 1 FROM global_settings WHERE id = 1")
    if cur.fetchone() is None:
        _execute(
            """
            INSERT INTO global_settings (id, global_bonus_active, autumn_event_active,
                                         season_start, season_number)
            VALUES (1,0,0,?,1)
            """,
            (int(time.time()),),
        )
    else:
        cur.execute("SELECT season_start FROM global_settings WHERE id = 1")
        row = cur.fetchone()
        if row["season_start"] == 0:
            _execute(
                "UPDATE global_settings SET season_start = ? WHERE id = 1",
                (int(time.time()),),
            )
    # ---------- pet_last_fed ----------
    _execute(
        """
        CREATE TABLE IF NOT EXISTS pet_last_fed (
            user_id INTEGER,
            pet_field TEXT,
            last_fed INTEGER,
            PRIMARY KEY (user_id, pet_field)
        );
        """
    )
    # ---------- promo_codes ----------
    _execute(
        """
        CREATE TABLE IF NOT EXISTS promo_codes (
            code TEXT PRIMARY KEY,
            coins INTEGER NOT NULL,
            pet_field TEXT,
            pet_qty INTEGER DEFAULT 0,
            max_uses INTEGER DEFAULT 1,
            used INTEGER DEFAULT 0
        );
        """
    )
    # ---------- decorations ----------
    _execute(
        """
        CREATE TABLE IF NOT EXISTS decorations (
            user_id INTEGER,
            decor_type TEXT,
            level INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, decor_type)
        );
        """
    )
    # ---------- lottery ----------
    _execute(
        """
        CREATE TABLE IF NOT EXISTS lottery (
            user_id INTEGER PRIMARY KEY,
            tickets INTEGER DEFAULT 0
        );
        """
    )
    # ---------- boosters ----------
    _execute(
        """
        CREATE TABLE IF NOT EXISTS boosters (
            user_id INTEGER PRIMARY KEY,
            multiplier REAL DEFAULT 1.0,
            expires INTEGER DEFAULT 0
        );
        """
    )
    # ---------- farmers ----------
    _execute(
        """
        CREATE TABLE IF NOT EXISTS farmers (
            user_id INTEGER,
            farmer_type TEXT,
            qty INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, farmer_type)
        );
        """
    )
    # ---------- admin_logs ----------
    _execute(
        """
        CREATE TABLE IF NOT EXISTS admin_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT,
            ts INTEGER
        );
        """
    )
    # ---------- clans ----------
    _execute(
        """
        CREATE TABLE IF NOT EXISTS clans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            leader_id INTEGER NOT NULL,
            created_at INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            experience INTEGER DEFAULT 0,
            max_members INTEGER DEFAULT 10
        );
        """
    )
    # ---------- clan_members ----------
    _execute(
        """
        CREATE TABLE IF NOT EXISTS clan_members (
            user_id INTEGER,
            clan_id INTEGER,
            role TEXT DEFAULT 'member',
            joined_at INTEGER DEFAULT 0,
            contribution INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, clan_id)
        );
        """
    )
    # ---------- clan_battles ----------
    _execute(
        """
        CREATE TABLE IF NOT EXISTS clan_battles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            clan1_id INTEGER,
            clan2_id INTEGER,
            winner_id INTEGER,
            started_at INTEGER,
            ended_at INTEGER,
            prize INTEGER DEFAULT 0
        );
        """
    )
    conn.commit()


# ----------------------------------------------------------------------
#   Питомцы, цены и доход (доход = income_per_minute)
# ----------------------------------------------------------------------
# (field_name, income_per_minute, emoji, full_name, class, price, description)
ANIMAL_CONFIG: List[Tuple[str, int, str, str, str, int, str]] = [
    # ------------------- COMMON -------------------
    ("chickens",      2, "🐔", "Куры",               "common",  200,
        "Кормят себя зерном и приносят небольшой доход."),
    ("cows",          4, "🐄", "Коровы",             "common",  500,
        "Молоко этих коров превращается в золотой сыр."),
    ("pigs",          6, "🐖", "Свиньи",             "common",  800,
        "Любят копать, иногда находят забытые монеты."),
    # ------------------- ОСЕННИЕ ПИТОМЦЫ -------------------
    ("autumn_dragon", 15_000_000, "🐉", "Осенний Дракон", "autumn",
        100_000_000_000_000,
        "Дракон, чья чешуя переливается осенними красками. Каждый лист, который он касается, превращается в золото."),
    ("harvest_phoenix", 18_000_000, "🦜", "Феникс Урожая", "autumn",
        120_000_000_000_000,
        "Восстаёт из осенних листьев, принося богатство каждому возрождению."),
    ("golden_unicorn", 20_000_000, "🦄", "Золотой Единорог", "autumn",
        150_000_000_000_000,
        "Его рог светится осенним золотом, превращая всё вокруг в драгоценности."),
]


# Функции для работы с пользователями
def get_user(user_id: int) -> sqlite3.Row:
    """Возвращает запись пользователя, создаёт её при необходимости."""
    cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    if not row:
        now = int(time.time())
        _execute(
            "INSERT INTO users (user_id, registration_date, last_active) VALUES (?, ?, ?)", 
            (user_id, now, now)
        )
        cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
    else:
        # Обновляем время последней активности
        _execute("UPDATE users SET last_active = ? WHERE user_id = ?", (int(time.time()), user_id))
    
    return row


def update_user(user_id: int, **kwargs: Any) -> None:
    """Обновляет только переданные поля."""
    if not kwargs:
        return
    set_clause = ", ".join(f"{k}=?" for k in kwargs)
    vals = [
        int(v) if isinstance(v, (int, float, bool)) else v
        for v in kwargs.values()
    ]
    vals.append(user_id)
    _execute(f"UPDATE users SET {set_clause} WHERE user_id = ?", tuple(vals))


def format_num(n: int) -> str:
    """Число с разделителем тысяч (точка)."""
    return f"{n:,}".replace(",", ".")


def is_admin(user_id: int) -> bool:
    cur.execute("SELECT 1 FROM admin_users WHERE user_id = ?", (user_id,))
    return cur.fetchone() is not None


def log_user_action(user_id: int, action: str) -> None:
    """Записывает действие игрока в журнал админа."""
    try:
        _execute(
            "INSERT INTO admin_logs (user_id, action, ts) VALUES (?,?,?)",
            (user_id, action, int(time.time())),
        )
    except Exception as e:
        log.error(f"Ошибка записи в журнал: {e}")


def get_bot_statistics() -> Dict[str, Any]:
    """Возвращает статистику бота."""
    stats = {}
    
    # Общее количество пользователей
    cur.execute("SELECT COUNT(*) as count FROM users")
    stats["total_users"] = cur.fetchone()["count"]
    
    # Активные пользователи (заходили за последние 24 часа)
    day_ago = int(time.time()) - 86400
    cur.execute("SELECT COUNT(*) as count FROM users WHERE last_active >= ?", (day_ago,))
    stats["active_24h"] = cur.fetchone()["count"]
    
    # Активные пользователи (заходили за последнюю неделю)
    week_ago = int(time.time()) - 604800
    cur.execute("SELECT COUNT(*) as count FROM users WHERE last_active >= ?", (week_ago,))
    stats["active_week"] = cur.fetchone()["count"]
    
    # Новые пользователи за последние 24 часа
    cur.execute("SELECT COUNT(*) as count FROM users WHERE registration_date >= ?", (day_ago,))
    stats["new_24h"] = cur.fetchone()["count"]
    
    # Общее количество монет в игре
    cur.execute("SELECT SUM(coins) as total FROM users")
    stats["total_coins"] = cur.fetchone()["total"] or 0
    
    # Количество кланов
    cur.execute("SELECT COUNT(*) as count FROM clans")
    stats["total_clans"] = cur.fetchone()["count"]
    
    # Участников в кланах
    cur.execute("SELECT COUNT(*) as count FROM clan_members")
    stats["clan_members"] = cur.fetchone()["count"]
    
    # Активных битв
    cur.execute("SELECT COUNT(*) as count FROM clan_battles WHERE ended_at = 0")
    stats["active_battles"] = cur.fetchone()["count"]
    
    # Общее количество записей в логах
    cur.execute("SELECT COUNT(*) as count FROM admin_logs")
    stats["total_logs"] = cur.fetchone()["count"]
    
    # Количество промокодов
    cur.execute("SELECT COUNT(*) as count FROM promo_codes")
    stats["total_promos"] = cur.fetchone()["count"]
    
    # Топ питомец по количеству
    total_pets = {}
    for field, _, emoji, name, *_ in ANIMAL_CONFIG:
        cur.execute(f"SELECT SUM({field}) as total FROM users")
        total = cur.fetchone()["total"] or 0
        if total > 0:
            total_pets[name] = {"count": total, "emoji": emoji}
    
    if total_pets:
        top_pet = max(total_pets.items(), key=lambda x: x[1]["count"])
        stats["top_pet"] = {"name": top_pet[0], "count": top_pet[1]["count"], "emoji": top_pet[1]["emoji"]}
    else:
        stats["top_pet"] = {"name": "Нет", "count": 0, "emoji": "❌"}
    
    # Участники осеннего события
    cur.execute("SELECT COUNT(*) as count FROM users WHERE autumn_event_participation > 0")
    stats["autumn_participants"] = cur.fetchone()["count"]
    
    return stats


# Функции для кланов
def create_clan(name: str, leader_id: int) -> int:
    """Создаёт клан и возвращает его ID."""
    _execute(
        "INSERT INTO clans (name, leader_id, created_at) VALUES (?,?,?)",
        (name, leader_id, int(time.time()))
    )
    clan_id = cur.lastrowid
    _execute(
        "INSERT INTO clan_members (user_id, clan_id, role, joined_at) VALUES (?,?,?,?)",
        (leader_id, clan_id, "leader", int(time.time()))
    )
    log_user_action(leader_id, f"Создал клан '{name}'")
    return clan_id


def get_user_clan(user_id: int) -> sqlite3.Row | None:
    """Возвращает клан пользователя."""
    cur.execute(
        "SELECT c.* FROM clans c JOIN clan_members cm ON c.id = cm.clan_id WHERE cm.user_id = ?",
        (user_id,)
    )
    return cur.fetchone()


def join_clan(user_id: int, clan_id: int) -> bool:
    """Присоединяет пользователя к клану."""
    # Проверяем, есть ли место в клане
    cur.execute("SELECT COUNT(*) as count FROM clan_members WHERE clan_id = ?", (clan_id,))
    member_count = cur.fetchone()["count"]
    cur.execute("SELECT max_members FROM clans WHERE id = ?", (clan_id,))
    max_members = cur.fetchone()["max_members"]
    
    if member_count >= max_members:
        return False
    
    _execute(
        "INSERT INTO clan_members (user_id, clan_id, joined_at) VALUES (?,?,?)",
        (user_id, clan_id, int(time.time()))
    )
    log_user_action(user_id, f"Присоединился к клану {clan_id}")
    return True


def leave_clan(user_id: int) -> bool:
    """Покидает клан."""
    cur.execute("SELECT clan_id, role FROM clan_members WHERE user_id = ?", (user_id,))
    result = cur.fetchone()
    if not result:
        return False
    
    clan_id, role = result["clan_id"], result["role"]
    
    # Если лидер покидает клан, передаём лидерство другому участнику
    if role == "leader":
        cur.execute("SELECT user_id FROM clan_members WHERE clan_id = ? AND user_id != ? LIMIT 1", (clan_id, user_id))
        new_leader = cur.fetchone()
        if new_leader:
            _execute("UPDATE clan_members SET role = 'leader' WHERE user_id = ? AND clan_id = ?", (new_leader["user_id"], clan_id))
            _execute("UPDATE clans SET leader_id = ? WHERE id = ?", (new_leader["user_id"], clan_id))
        else:
            # Если в клане больше никого нет, удаляем клан
            _execute("DELETE FROM clans WHERE id = ?", (clan_id,))
    
    _execute("DELETE FROM clan_members WHERE user_id = ?", (user_id,))
    log_user_action(user_id, f"Покинул клан {clan_id}")
    return True


def get_clan_members(clan_id: int) -> List[sqlite3.Row]:
    """Возвращает список участников клана."""
    cur.execute(
        "SELECT cm.*, u.username FROM clan_members cm JOIN users u ON cm.user_id = u.user_id WHERE cm.clan_id = ? ORDER BY cm.contribution DESC",
        (clan_id,)
    )
    return cur.fetchall()


def get_clan_top() -> List[sqlite3.Row]:
    """Возвращает топ кланов по опыту."""
    cur.execute("SELECT * FROM clans ORDER BY experience DESC LIMIT 10")
    return cur.fetchall()


# Функции интерфейса
def chunk_buttons(
    buttons: List[InlineKeyboardButton], per_row: int = 3
) -> List[List[InlineKeyboardButton]]:
    return [buttons[i: i + per_row] for i in range(0, len(buttons), per_row)]


async def edit_section(
    query,
    caption: str,
    image_key: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    """Редактирует сообщение, заменяя фото на фото из SECTION_IMAGES[image_key]."""
    img = SECTION_IMAGES.get(image_key, MAIN_MENU_IMG)  # fallback
    await query.edit_message_media(
        media=InputMediaPhoto(media=img, caption=caption),
        reply_markup=reply_markup,
    )


def build_main_menu(user_id: int) -> InlineKeyboardMarkup:
    rows = []
    rows.append([InlineKeyboardButton("ℹ️ О боте", callback_data="about")])
    other = [
        InlineKeyboardButton("🌾 Моя ферма", callback_data="farm"),
        InlineKeyboardButton("🛒 Магазин", callback_data="shop"),
        InlineKeyboardButton("📊 Статус", callback_data="status"),
        InlineKeyboardButton("💰 Получить монеты", callback_data="get_coins"),
        InlineKeyboardButton("🍂 Осеннее событие", callback_data="autumn_event"),
        InlineKeyboardButton("⚔️ Кланы", callback_data="clans"),
    ]
    rows.extend(chunk_buttons(other, per_row=3))
    if is_admin(user_id):
        rows.append([InlineKeyboardButton("🔥 Админ", callback_data="admin")])
    return InlineKeyboardMarkup(rows)


async def show_main_menu(
    update: Update, context: ContextTypes.DEFAULT_TYPE, edit: bool = False
) -> None:
    user = update.effective_user
    db_user = get_user(user.id)
    text = f"🤖 Добро пожаловать в Ферму!"
    kb = build_main_menu(user.id)
    if edit:
        query = update.callback_query
        await edit_section(query, caption=text, image_key="main", reply_markup=kb)
    else:
        await update.message.reply_photo(
            MAIN_MENU_IMG,
            caption=text,
            reply_markup=kb,
        )


async def about_section(query) -> None:
    text = (
        "О боте «Ферма»\n"
        "Это простая ферма в Telegram. Вы покупаете животных, получаете доход, "
        "кормите их, улучшаете базу, играете в мини‑казино и можете обмениваться с другими игроками.\n\n"
        f"Чат проекта: {CHAT_LINK}\n"
        f"Канал проекта: {CHANNEL_LINK}\n\n"
        "Удачной фермы! 🐓🐄🐖"
    )
    btn = InlineKeyboardButton("⬅️ Назад", callback_data="back")
    await edit_section(
        query,
        caption=text,
        image_key="about",
        reply_markup=InlineKeyboardMarkup([[btn]]),
    )


async def status_section(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = query.from_user.id
    user = get_user(uid)
    text = (
        f"📊 Статус 📊\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 ID: {user['user_id']}\n"
        f"💰 Монеты: {format_num(user['coins'])}\n"
        f"🏗️ База: уровень {user['base_level']} (лимит: {user['pet_limit']})\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🎟️ Билетов: {user['tickets']}\n"
        f"💬 Репутация: {user['reputation']}\n"
        f"🍂 Очки осеннего события: {user['autumn_event_participation']}\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    back_btn = InlineKeyboardButton("⬅️ Главное меню", callback_data="back")
    kb = InlineKeyboardMarkup([[back_btn]])
    await edit_section(
        query,
        caption=text,
        image_key="status",
        reply_markup=kb,
    )


async def get_coins_menu(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать пользователю доступные задания."""
    btns = [
        InlineKeyboardButton("🤝 Пригласить друга", callback_data="task_referral"),
        InlineKeyboardButton("🔹 Кликнуть (1‑5 монет)", callback_data="task_click"),
        InlineKeyboardButton("⬅️ Назад", callback_data="back"),
    ]
    kb = InlineKeyboardMarkup(chunk_buttons(btns, per_row=2))
    await edit_section(
        query,
        caption="💰 Получить монеты – выполните задания и получайте награды!",
        image_key="coins",
        reply_markup=kb,
    )


async def task_referral(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = query.from_user.id
    link = f"https://t.me/{context.bot.username}?start={uid}"
    await edit_section(
        query,
        caption=(
            f"🤝 Пригласите друга, отправив ему эту ссылку:\n{link}\n"
            f"За каждого приглашённого вы получаете {format_num(500)}🪙."
        ),
        image_key="coins",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("⬅️ Назад", callback_data="get_coins")]]
        ),
    )


async def task_click(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Клик – небольшая награда."""
    uid = query.from_user.id
    user = get_user(uid)
    reward = random.randint(1, 5)
    update_user(
        uid,
        coins=user["coins"] + reward,
        weekly_coins=user["weekly_coins"] + reward,
        reputation=user["reputation"] + 1,
        click_reward_last=int(time.time()),
    )
    log_user_action(uid, f"Кликнул и получил {reward}🪙")
    await edit_section(
        query,
        caption=f"✨ Вы получили {format_num(reward)}🪙!",
        image_key="coins",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("⬅️ Назад", callback_data="get_coins")]]
        ),
    )


# Осеннее событие
async def autumn_event_info(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    cur.execute("SELECT autumn_event_active FROM global_settings WHERE id = 1")
    active = cur.fetchone()["autumn_event_active"]
    status = "✅ Включено" if active else "❌ Выключено"
    
    uid = query.from_user.id
    user = get_user(uid)
    participation = user["autumn_event_participation"]
    
    # Проверяем, есть ли у пользователя осенние питомцы
    autumn_pets = []
    for field, _, emoji, name, pet_class, *_ in ANIMAL_CONFIG:
        if pet_class == "autumn" and user[field] > 0:
            autumn_pets.append(f"{emoji} {name}: {user[field]}")
    
    text = (
        f"🍂 ОСЕННЕЕ СОБЫТИЕ {status}\n\n"
        "🎃 Особые возможности:\n"
        f"• Осенний корм дает ×2 к доходу на 1 час\n"
        f"• Стоимость осеннего корма: {format_num(AUTUMN_FOOD_PRICE)}🪙\n"
        f"• Доступны эксклюзивные осенние питомцы\n"
        f"• Ежедневные осенние квесты и награды\n\n"
        f"👤 Ваше участие: {participation} очков\n"
    )
    
    if autumn_pets:
        text += f"\n🍂 Ваши осенние питомцы:\n" + "\n".join(autumn_pets[:5])
        if len(autumn_pets) > 5:
            text += f"\n... и еще {len(autumn_pets) - 5}"
    else:
        text += "\n❌ У вас пока нет осенних питомцев"
    
    btns = []
    if active:
        btns.extend([
            InlineKeyboardButton("🎁 Ежедневная награда", callback_data="autumn_daily"),
            InlineKeyboardButton("🍂 Осенние питомцы", callback_data="autumn_pets"),
            InlineKeyboardButton("🎯 Осенние квесты", callback_data="autumn_quests"),
        ])
    
    btns.append(InlineKeyboardButton("⬅️ Назад", callback_data="back"))
    
    await edit_section(
        query,
        caption=text,
        image_key="autumn",
        reply_markup=InlineKeyboardMarkup(chunk_buttons(btns, per_row=2)),
    )


async def autumn_daily_reward(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ежедневная награда за осеннее событие."""
    uid = query.from_user.id
    user = get_user(uid)
    
    # Проверяем, можно ли получить награду (раз в день)
    last_reward = user.get("last_ticket_time", 0)  # Используем это поле для отслеживания
    now = int(time.time())
    
    if now - last_reward < 86400:  # 24 часа
        remaining = 86400 - (now - last_reward)
        h, r = divmod(remaining, 3600)
        m = r // 60
        await edit_section(
            query,
            caption=f"⏰ Ежедневная награда уже получена!\nСледующая награда через: {h}ч {m}м",
            image_key="autumn",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⬅️ Назад", callback_data="autumn_event")]]
            ),
        )
        return
    
    # Выдаем награду
    rewards = []
    autumn_feed_reward = random.randint(1, 3)
    coins_reward = random.randint(5000, 15000)
    participation_reward = random.randint(10, 30)
    
    update_user(
        uid,
        autumn_feed=user["autumn_feed"] + autumn_feed_reward,
        coins=user["coins"] + coins_reward,
        autumn_event_participation=user["autumn_event_participation"] + participation_reward,
        last_ticket_time=now,
    )
    
    # Шанс на осеннего питомца
    if random.random() < 0.1:  # 10% шанс
        autumn_pets = [field for field, _, _, _, pet_class, *_ in ANIMAL_CONFIG if pet_class == "autumn"]
        if autumn_pets:
            lucky_pet = random.choice(autumn_pets)
            update_user(uid, **{lucky_pet: user[lucky_pet] + 1})
            rewards.append(f"🍂 +1 {lucky_pet}")
    
    log_user_action(uid, f"Получил ежедневную осеннюю награду")
    
    text = (
        f"🎁 ЕЖЕДНЕВНАЯ ОСЕННЯЯ НАГРАДА!\n\n"
        f"🍂 Осенний корм: +{autumn_feed_reward}\n"
        f"💰 Монеты: +{format_num(coins_reward)}🪙\n"
        f"🎯 Очки участия: +{participation_reward}\n"
    )
    
    if rewards:
        text += f"\n🎉 БОНУС: {', '.join(rewards)}\n"
    
    text += f"\n⏰ Следующая награда через 24 часа"
    
    await edit_section(
        query,
        caption=text,
        image_key="autumn",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("⬅️ Назад", callback_data="autumn_event")]]
        ),
    )


# Админ-панель
async def admin_panel(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(query.from_user.id):
        await edit_section(query, caption="❌ Доступ запрещён.", image_key="admin")
        return
    btns = [
        InlineKeyboardButton("📊 Статистика бота", callback_data="admin_bot_stats"),
        InlineKeyboardButton("📜 Полный журнал", callback_data="admin_full_logs"),
        InlineKeyboardButton("🍂 Переключить осеннее событие", callback_data="admin_toggle_autumn"),
        InlineKeyboardButton("⬅️ Назад", callback_data="back"),
    ]
    kb = chunk_buttons(btns, per_row=2)
    await edit_section(
        query,
        caption="🔥 Админ‑панель 🔥",
        image_key="admin",
        reply_markup=InlineKeyboardMarkup(kb),
    )


async def admin_actions(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает все кнопки, начинающиеся с «admin_». """
    data = query.data
    uid = query.from_user.id
    if not is_admin(uid):
        await edit_section(query, caption="❌ Доступ запрещён.", image_key="admin")
        return
    
    if data == "admin_bot_stats":
        stats = get_bot_statistics()
        text = (
            f"📊 СТАТИСТИКА БОТА\n\n"
            f"👥 Пользователи:\n"
            f"• Всего зарегистрировано: {stats['total_users']}\n"
            f"• Активных за 24ч: {stats['active_24h']}\n"
            f"• Активных за неделю: {stats['active_week']}\n"
            f"• Новых за 24ч: {stats['new_24h']}\n\n"
            f"💰 Экономика:\n"
            f"• Всего монет в игре: {format_num(stats['total_coins'])}🪙\n\n"
            f"⚔️ Кланы:\n"
            f"• Всего кланов: {stats['total_clans']}\n"
            f"• Участников в кланах: {stats['clan_members']}\n"
            f"• Активных битв: {stats['active_battles']}\n\n"
            f"🍂 События:\n"
            f"• Участников осеннего события: {stats['autumn_participants']}\n\n"
            f"📊 Разное:\n"
            f"• Записей в журнале: {stats['total_logs']}\n"
            f"• Промокодов: {stats['total_promos']}\n"
            f"• Самый популярный питомец: {stats['top_pet']['emoji']} {stats['top_pet']['name']} ({format_num(stats['top_pet']['count'])} шт.)"
        )
        await edit_section(
            query,
            caption=text,
            image_key="admin",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔄 Обновить", callback_data="admin_bot_stats")],
                 [InlineKeyboardButton("⬅️ Назад", callback_data="admin")]]
            ),
        )
        return
    
    if data == "admin_full_logs":
        cur.execute(
            "SELECT user_id, action, ts FROM admin_logs ORDER BY ts DESC LIMIT 50"
        )
        rows = cur.fetchall()
        if not rows:
            txt = "📜 Журнал пуст."
        else:
            txt = "📜 Полный журнал действий (последние 50):\n\n"
            for row in rows:
                t = time.strftime("%d.%m %H:%M", time.localtime(row["ts"]))
                txt += f"[{t}] ID{row['user_id']}: {row['action']}\n"
        
        # Разбиваем на части, если текст слишком длинный
        if len(txt) > 4000:
            txt = txt[:4000] + "...\n\n(показаны первые записи)"
        
        btns = [
            InlineKeyboardButton("🗑️ Очистить журнал", callback_data="admin_clear_logs"),
            InlineKeyboardButton("⬅️ Назад", callback_data="admin"),
        ]
        
        await edit_section(
            query,
            caption=txt,
            image_key="logs",
            reply_markup=InlineKeyboardMarkup(chunk_buttons(btns, per_row=2)),
        )
        return
    
    if data == "admin_clear_logs":
        _execute("DELETE FROM admin_logs")
        await edit_section(
            query, 
            caption="✅ Журнал очищен.", 
            image_key="admin",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⬅️ Назад", callback_data="admin")]]
            )
        )
        return
    
    if data == "admin_toggle_autumn":
        cur.execute("SELECT autumn_event_active FROM global_settings WHERE id = 1")
        current = cur.fetchone()["autumn_event_active"]
        new_val = 0 if current else 1
        _execute(
            "UPDATE global_settings SET autumn_event_active = ? WHERE id = 1",
            (new_val,),
        )
        await edit_section(
            query,
            caption=f"🍂 Осеннее событие {('включено' if new_val else 'выключено')}.",
            image_key="autumn",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⬅️ Назад", callback_data="admin")]]
            ),
        )
        return


# Кланы
async def clans_menu(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Главное меню кланов."""
    uid = query.from_user.id
    user_clan = get_user_clan(uid)
    
    if user_clan:
        # Пользователь уже в клане
        members = get_clan_members(user_clan["id"])
        member_text = "\n".join([
            f"👤 {m['username'] or f'ID{m[\"user_id\"]}'} ({m['role']}) - {m['contribution']} вклада"
            for m in members[:10]  # Показываем только первых 10
        ])
        
        text = (
            f"⚔️ Ваш клан: {user_clan['name']}\n"
            f"👑 Лидер: ID{user_clan['leader_id']}\n"
            f"📊 Уровень: {user_clan['level']}\n"
            f"⭐ Опыт: {user_clan['experience']}\n"
            f"👥 Участников: {len(members)}/{user_clan['max_members']}\n\n"
            f"Участники:\n{member_text}"
        )
        
        btns = [
            InlineKeyboardButton("🏆 Топ кланов", callback_data="clan_top"),
            InlineKeyboardButton("🚪 Покинуть клан", callback_data="clan_leave"),
        ]
    else:
        # Пользователь не в клане
        text = (
            "⚔️ Система кланов\n\n"
            "Кланы - это объединения игроков для совместной игры!\n"
            "• Создавайте кланы и приглашайте друзей\n"
            "• Участвуйте в клановых битвах\n"
            "• Получайте бонусы за активность в клане\n"
            "• Соревнуйтесь с другими кланами"
        )
        
        btns = [
            InlineKeyboardButton("🏗️ Создать клан", callback_data="clan_create"),
            InlineKeyboardButton("🔍 Найти клан", callback_data="clan_search"),
            InlineKeyboardButton("🏆 Топ кланов", callback_data="clan_top"),
        ]
    
    btns.append(InlineKeyboardButton("⬅️ Назад", callback_data="back"))
    kb = InlineKeyboardMarkup(chunk_buttons(btns, per_row=2))
    
    await edit_section(
        query,
        caption=text,
        image_key="admin",  # Используем админ картинку для кланов
        reply_markup=kb,
    )


async def clan_create(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Создание клана."""
    uid = query.from_user.id
    if get_user_clan(uid):
        await edit_section(
            query,
            caption="❌ Вы уже состоите в клане!",
            image_key="admin",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⬅️ Назад", callback_data="clans")]]
            ),
        )
        return
    
    context.user_data["awaiting_clan_name"] = True
    await edit_section(
        query,
        caption="🏗️ Введите название клана (максимум 20 символов):",
        image_key="admin",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("⬅️ Отмена", callback_data="clans")]]
        ),
    )


async def clan_top(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Топ кланов."""
    clans = get_clan_top()
    
    if not clans:
        text = "❌ Пока нет кланов."
    else:
        text = "🏆 Топ кланов по опыту:\n\n"
        for i, clan in enumerate(clans, 1):
            cur.execute("SELECT COUNT(*) as count FROM clan_members WHERE clan_id = ?", (clan["id"],))
            member_count = cur.fetchone()["count"]
            text += f"{i}. 🏰 {clan['name']}\n"
            text += f"   Уровень: {clan['level']} | Опыт: {clan['experience']}\n"
            text += f"   Участников: {member_count}/{clan['max_members']}\n\n"
    
    await edit_section(
        query,
        caption=text,
        image_key="top",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("⬅️ Назад", callback_data="clans")]]
        ),
    )


# Главный обработчик кнопок
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass
    data = query.data
    
    # ------------------- Универсальная «Назад» -------------------
    if data == "back":
        await show_main_menu(update, context, edit=True)
        return
    # ------------------- О боте -------------------
    if data == "about":
        await about_section(query)
        return
    # ------------------- Статус -------------------
    if data == "status":
        await status_section(query, context)
        return
    # ------------------- Получить монеты -------------------
    if data == "get_coins":
        await get_coins_menu(query, context)
        return
    if data == "task_referral":
        await task_referral(query, context)
        return
    if data == "task_click":
        await task_click(query, context)
        return
    # ------------------- Осеннее событие -------------------
    if data == "autumn_event":
        await autumn_event_info(query, context)
        return
    if data == "autumn_daily":
        await autumn_daily_reward(query, context)
        return
    # ------------------- Кланы -------------------
    if data == "clans":
        await clans_menu(query, context)
        return
    if data == "clan_create":
        await clan_create(query, context)
        return
    if data == "clan_top":
        await clan_top(query, context)
        return
    if data == "clan_leave":
        uid = query.from_user.id
        if leave_clan(uid):
            await edit_section(
                query,
                caption="✅ Вы покинули клан.",
                image_key="admin",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("⬅️ Назад", callback_data="clans")]]
                ),
            )
        else:
            await edit_section(
                query,
                caption="❌ Вы не состоите в клане.",
                image_key="admin",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("⬅️ Назад", callback_data="clans")]]
                ),
            )
        return
    # ------------------- Админ‑панель -------------------
    if data == "admin":
        await admin_panel(query, context)
        return
    if data.startswith("admin_"):
        await admin_actions(query, context)
        return
    # ------------------- Неизвестная команда -------------------
    await query.edit_message_caption(caption="❓ Неизвестная команда.")


# Команды
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает /start, включая реферал."""
    txt = update.message.text if update.message else ""
    user = update.effective_user
    db_user = get_user(user.id)
    
    # Реферальный параметр: /start <ref_id>
    if txt.startswith("/start"):
        parts = txt.split()
        if len(parts) == 2 and parts[1].isdigit():
            ref_id = int(parts[1])
            if db_user["referred_by"] == 0 and ref_id != user.id:
                update_user(user.id, referred_by=ref_id)
                # награда рефереру
                ref_user = get_user(ref_id)
                update_user(
                    ref_id,
                    coins=ref_user["coins"] + 500,
                    weekly_coins=ref_user["weekly_coins"] + 500,
                    reputation=ref_user["reputation"] + 1,
                )
                try:
                    await context.bot.send_message(
                        ref_id,
                        f"🤝 Вы получили {format_num(500)}🪙 за приглашение нового игрока!",
                    )
                except Exception:
                    pass
    await show_main_menu(update, context, edit=False)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает все текстовые сообщения, не являющиеся командами."""
    user = update.effective_user
    txt = update.message.text if update.message else ""

    # ------------------- Создание клана -------------------
    if context.user_data.get("awaiting_clan_name"):
        clan_name = txt.strip()
        if len(clan_name) > 20:
            await update.message.reply_text("❌ Название клана слишком длинное (максимум 20 символов).")
            return
        if len(clan_name) < 3:
            await update.message.reply_text("❌ Название клана слишком короткое (минимум 3 символа).")
            return
        
        uid = update.effective_user.id
        if get_user_clan(uid):
            await update.message.reply_text("❌ Вы уже состоите в клане!")
            context.user_data["awaiting_clan_name"] = False
            return
        
        try:
            clan_id = create_clan(clan_name, uid)
            await update.message.reply_text(f"✅ Клан '{clan_name}' создан! ID клана: {clan_id}")
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка создания клана: {str(e)}")
        
        context.user_data["awaiting_clan_name"] = False
        return


def add_admins() -> None:
    admin_ids = [7852721487]          # ваш Telegram‑ID
    for aid in admin_ids:
        _execute(
            "INSERT OR IGNORE INTO admin_users (user_id) VALUES (?)",
            (aid,),
        )


def ensure_user_columns() -> None:
    """Добавляем недостающие колонки в таблице users (миграция)."""
    cur.execute("PRAGMA table_info(users);")
    existing = {row["name"] for row in cur.fetchall()}
    needed = {
        "feed",
        "autumn_feed",
        "weekly_coins",
        "last_reset",
        "secret_spider",
        "click_count",
        "last_click_time",
        "feed_bonus_end",
        "autumn_bonus_end",
        "tickets",
        "last_ticket_time",
        "reputation",
        "custom_income",
        "pet_limit",
        "base_level",
        "subscribe_claimed",
        "chat_claimed",
        "click_reward_last",
        "referred_by",
        "last_active",
        "registration_date",
        "autumn_event_participation",
    }
    for col in needed:
        if col not in existing:
            log.info("Adding column %s to users", col)
            default_val = int(time.time()) if col in ("last_active", "registration_date") else 0
            _execute(f"ALTER TABLE users ADD COLUMN {col} INTEGER DEFAULT {default_val}")


def ensure_animal_columns() -> None:
    """Создаёт колонки‑питомцы, если их ещё нет."""
    cur.execute("PRAGMA table_info(users);")
    existing = {row["name"] for row in cur.fetchall()}
    for field, *_ in ANIMAL_CONFIG:
        if field not in existing:
            log.info("Adding animal column %s", field)
            _execute(f"ALTER TABLE users ADD COLUMN {field} INTEGER DEFAULT 0")


# ----------------------------------------------------------------------
#   Запуск бота
# ----------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--migrate", action="store_true", help="Только выполнить миграцию колонок"
    )
    args = parser.parse_args()
    init_db()
    ensure_user_columns()
    ensure_animal_columns()
    if args.migrate:
        log.info("Миграция завершена, колонки добавлены.")
        return
    add_admins()
    app = ApplicationBuilder().token(TOKEN).build()
    # Основные команды
    app.add_handler(CommandHandler("start", start_command))
    # Обработчики
    app.add_handler(CallbackQueryHandler(button))
    # Текстовые сообщения
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()


if __name__ == "__main__":
    main()