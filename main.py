#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# --------------------------------------------------------------
#   Bot «Farm» – полностью исправлен, доработан и расширен:
#   • Удалены все упоминания о перерождениях и X‑ферме.
#   • Добавлен журнал действий админа – возможность просматривать
#     последние действия игроков (покупка, кормление, продажа и т.д.).
#   • Для каждого раздела (меню, ферма, магазин, статус и т.д.)
#     теперь выводится изображение над текстом.
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
HUNGER_TIME = 10 * 3600          # 10 ч в секундах
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
#   Картинки питомцев ← NEW
# ----------------------------------------------------------------------
ANIMAL_IMAGES: Dict[str, str] = {
    "chickens":   "https://i.postimg.cc/sXhBfbdg/137158096.jpg",
    "cows":       "https://i.postimg.cc/rsT0gP5b/cows.jpg",
    "pigs":       "https://i.postimg.cc/4yM8VbJw/pigs.jpg",
    "ducks":      "https://i.postimg.cc/7ZxM3W9v/ducks.jpg",
    "geese":      "https://i.postimg.cc/8PcLZf4S/geese.jpg",
    "turkeys":    "https://i.postimg.cc/7tLz8jJ5/turkeys.jpg",
    "rabbits":    "https://i.postimg.cc/3N0gkKpF/rabbits.jpg",
    "rats":       "https://i.postimg.cc/2jR6V8gH/rats.jpg",
    "hamsters":   "https://i.postimg.cc/0yH4pT7L/hamsters.jpg",
    "goats":      "https://i.postimg.cc/6tWfJ9K5/goats.jpg",
    "sheep":      "https://i.postimg.cc/5tqV6c33/sheep.jpg",
    "donkeys":    "https://i.postimg.cc/44MkpV6G/donkeys.jpg",
    "mules":      "https://i.postimg.cc/gc7xgWQp/mules.jpg",
    "camels":     "https://i.postimg.cc/6z3WqRzK/camels.jpg",
    "alpacas":    "https://i.postimg.cc/3J6L2ZtV/alpacas.jpg",
    "llamas":     "https://i.postimg.cc/6p3d3VbK/llamas.jpg",
    "yak":        "https://i.postimg.cc/5N5Tzq9g/yak.jpg",
    "buffalo":    "https://i.postimg.cc/6tWfJ9K5/buffalo.jpg",
    "ferrets":    "https://i.postimg.cc/2jR6V8gH/ferrets.jpg",
    "otters":     "https://i.postimg.cc/0yH4pT7L/otters.jpg",
    # … сюда же добавьте ссылки для всех остальных (rare, epic, mystic, secret, ultra и т.д.) …
    # Пример:
    "horses":     "https://i.postimg.cc/6qh5THc7/horses.jpg",
    "dragons":    "https://i.postimg.cc/6qh5THc7/dragons.jpg",
    # Если ссылки нет – будет использовано изображение по умолчанию (MAIN_MENU_IMG)
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
            referred_by INTEGER DEFAULT 0
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
    conn.commit()


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
    }
    for col in needed:
        if col not in existing:
            log.info("Adding column %s to users", col)
            _execute(f"ALTER TABLE users ADD COLUMN {col} INTEGER DEFAULT 0")


def ensure_animal_columns() -> None:
    """Создаёт колонки‑питомцы, если их ещё нет."""
    cur.execute("PRAGMA table_info(users);")
    existing = {row["name"] for row in cur.fetchall()}
    for field, *_ in ANIMAL_CONFIG:
        if field not in existing:
            log.info("Adding animal column %s", field)
            _execute(f"ALTER TABLE users ADD COLUMN {field} INTEGER DEFAULT 0")


def ensure_global_settings_columns() -> None:
    """Миграция столбцов в global_settings (на случай будущих изменений)."""
    cur.execute("PRAGMA table_info(global_settings);")
    existing = {row["name"] for row in cur.fetchall()}
    for col in ("autumn_event_active", "season_start", "season_number"):
        if col not in existing:
            log.info("Adding column %s to global_settings", col)
            default = 0 if col != "season_number" else 1
            _execute(
                f"ALTER TABLE global_settings ADD COLUMN {col} INTEGER DEFAULT {default}"
            )


def ensure_promo_columns() -> None:
    """Проверяем, есть ли колонка `used` в promo_codes и добавляем её при необходимости."""
    cur.execute("PRAGMA table_info(promo_codes);")
    cols = {row["name"] for row in cur.fetchall()}
    if "used" not in cols:
        log.info("Adding column `used` to promo_codes")
        _execute("ALTER TABLE promo_codes ADD COLUMN used INTEGER DEFAULT 0")


# ----------------------------------------------------------------------
#   Администраторы
# ----------------------------------------------------------------------
def add_admins() -> None:
    admin_ids = [7852721487]          # ваш Telegram‑ID
    for aid in admin_ids:
        _execute(
            "INSERT OR IGNORE INTO admin_users (user_id) VALUES (?)",
            (aid,),
        )


def is_admin(user_id: int) -> bool:
    cur.execute("SELECT 1 FROM admin_users WHERE user_id = ?", (user_id,))
    return cur.fetchone() is not None


def log_user_action(user_id: int, action: str) -> None:
    """Записывает действие игрока в журнал админа."""
    _execute(
        "INSERT INTO admin_logs (user_id, action, ts) VALUES (?,?,?)",
        (user_id, action, int(time.time())),
    )


# ----------------------------------------------------------------------
#   Утилиты
# ----------------------------------------------------------------------
def format_num(n: int) -> str:
    """Число с разделителем тысяч (точка)."""
    return f"{n:,}".replace(",", ".")


def _safe_int(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (float, int)):
        v = int(value)
        return v if v <= MAX_INT else MAX_INT
    raise ValueError("Не число")


def update_user(user_id: int, **kwargs: Any) -> None:
    """Обновляет только переданные поля."""
    if not kwargs:
        return
    set_clause = ", ".join(f"{k}=?" for k in kwargs)
    vals = [
        _safe_int(v) if isinstance(v, (int, float, bool)) else v
        for v in kwargs.values()
    ]
    vals.append(user_id)
    _execute(f"UPDATE users SET {set_clause} WHERE user_id = ?", tuple(vals))


def get_user(user_id: int) -> sqlite3.Row:
    """Возвращает запись пользователя, создаёт её при необходимости."""
    cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    if not row:
        _execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
    # «Летучее» добавление новых колонок, если они вдруг появятся позже
    for field, *_ in ANIMAL_CONFIG:
        if field not in row.keys():
            _execute(f"ALTER TABLE users ADD COLUMN {field} INTEGER DEFAULT 0")
            cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cur.fetchone()
            break
    return row


def set_pet_last_fed(user_id: int, pet_field: str, timestamp: int) -> None:
    _execute(
        """
        INSERT INTO pet_last_fed (user_id, pet_field, last_fed)
        VALUES (?,?,?)
        ON CONFLICT(user_id, pet_field) DO UPDATE SET last_fed=excluded.last_fed
        """,
        (user_id, pet_field, timestamp),
    )


def get_pet_last_fed(user_id: int, pet_field: str) -> int | None:
    cur.execute(
        "SELECT last_fed FROM pet_last_fed WHERE user_id = ? AND pet_field = ?",
        (user_id, pet_field),
    )
    row = cur.fetchone()
    return row["last_fed"] if row else None


def delete_pet_last_fed(user_id: int, pet_field: str) -> None:
    _execute(
        "DELETE FROM pet_last_fed WHERE user_id = ? AND pet_field = ?",
        (user_id, pet_field),
    )


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
    ("ducks",         1, "🦆", "Утки",               "common",  150,
        "Крякают так громко, что даже волки останавливаются послушать."),
    ("geese",         2, "🦢", "Гуси",               "common",  250,
        "Охраняют двор, а их перья ценятся в магических ритуалах."),
    ("turkeys",       2, "🦃", "Индейки",            "common",  300,
        "Благодарны за каждый крик, превращая его в небольшую прибыль."),
    ("rabbits",       1, "🐇", "Кролики",            "common",  120,
        "Оставляют золотые морковки, если их правильно кормить."),
    ("rats",          1, "🐀", "Крысы",              "common",  100,
        "Скользят по стенам, иногда приносят удачу."),
    ("hamsters",      1, "🐹", "Хомяки",             "common",  130,
        "Крутятся в колесе, генерируя небольшие порции энергии."),
    ("goats",         4, "🐐", "Козы",               "common",  550,
        "Жуют всё подряд, в том числе старые контракты."),
    ("sheep",         4, "🐑", "Овцы",               "common",  540,
        "Мягко блеют, их шерсть продаётся в виде золотой пряжи."),
    ("donkeys",       2, "🐴", "Ослы",               "common",  400,
        "Терпеливо тянут тележки, принося небольшую прибыль."),
    ("mules",         3, "🐴", "Мулы",               "common",  450,
        "Сильнее ослов, их вопли отпугивают воров."),
    ("camels",        5, "🐪", "Верблюды",           "common",  700,
        "Хранят воду в горбах, их шипы иногда превращаются в камни."),
    ("alpacas",       5, "🦙", "Альпаки",            "common",  650,
        "Пушистые создания, их шерсть ценится в дорогих галереях."),
    ("llamas",        5, "🦙", "Ламы",               "common",  660,
        "Любят подбрасывать камни в сторону недоброжелателей."),
    ("yak",           6, "🐂", "Як",                 "common",  750,
        "Могут превратить молоко в золотой эликсир."),
    ("buffalo",       7, "🐃", "Буйвол",             "common",  900,
        "Громко рычат, когда собирают урожай, повышая доход."),
    ("ferrets",       2, "🦦", "Хорёк",              "common",  180,
        "Любят прятаться в норах, иногда находя забытые монеты."),
    ("otters",        3, "🦦", "Выдра",              "common",  200,
        "Плавают в реках, собирая редкие ракушки, которые продаются за монеты."),
    # ------------------- RARE -------------------
    ("horses",       70, "🐎", "Лошади",            "rare",    5_000,
        "Быстрые и грациозные, их гривы иногда блестят золотой пылью."),
    ("sheep_rare",   70, "🐑", "Овцы‑редкие",       "rare",    5_200,
        "Имеют золотую шерсть, из которой шьют мантию богатства."),
    ("goats_rare",   55, "🐐", "Козы‑редкие",       "rare",    4_800,
        "С их рогов падает золотой дождь раз в месяц."),
    ("alpacas_rare", 65, "🦙", "Альпаки‑редкие",    "rare",    6_300,
        "Их мягкая шерсть способна впитать магию, превращая её в монеты."),
    ("llamas_rare",  65, "🦙", "Ламы‑редкие",       "rare",    6_400,
        "Охраняют тайные проходы в подземельях, где спрятаны сокровища."),
    ("camels_rare",  75, "🐪", "Верблюды‑редкие",   "rare",    7_200,
        "Их горбы полны древних артефактов, продающихся за большие суммы."),
    ("yaks_rare",    85, "🐂", "Як‑редкие",         "rare",    8_000,
        "Сильные, как горные ветры, их молоко превращается в чистый золотой сок."),
    ("buffalo_rare", 95, "🐃", "Буйвол‑редкий",     "rare",    9_500,
        "Громко рычат, когда собирают урожай, удваивая доход."),
    ("ostrich",      80, "🦩", "Страус",            "rare",    5_500,
        "Беги быстрее всех, а его перья продаются за драгоценные камни."),
    ("emu",          80, "🦙", "Эму",               "rare",    5_600,
        "Своим криком вызывают духов, которые дарят монеты."),
    ("rhinoceros",  120, "🦏", "Носорог",           "rare",   12_000,
        "С рогом из чистого обсидиана, который ценится на аукционах."),
    ("hippopotamus",120, "🦛", "Бегемот",           "rare",   12_500,
        "Погружён в болото, где растут золотые кувшинки."),
    ("giraffe",     115, "🦒", "Жираф",             "rare",   11_800,
        "Высокий, как горы, его пятна иногда превращаются в кристаллы."),
    ("zebra",        95, "🦓", "Зебра",             "rare",   10_200,
        "Её полосы могут отражать свет и создавать иллюзию богатства."),
    ("bison",       105, "🦬", "Бизон",             "rare",   11_000,
        "Сильный, как буря, его рога способны отразить любой удар."),
    ("moose",       100, "🦌", "Лось",              "rare",   10_800,
        "Грозный, но в его рогах хранится древняя магия."),
    ("elk",          95, "🦌", "Вепрь",             "rare",   10_500,
        "Своим рёвом может вызвать дождь монет."),
    ("reindeer",    110, "🦌", "Северный олень",    "rare",   12_200,
        "Имеет золотые копыта, которые оставляют золотой след."),
    ("caribou",     110, "🦌", "Карибу",            "rare",   12_300,
        "Бежит сквозь леса, оставляя золотой мусор, который собирают охотники."),
    ("wild_boar",   120, "🐗", "Дикий кабан",       "rare",   13_000,
        "С его клыками можно расколоть любые сундуки."),
    # ------------------- EPIC -------------------
    ("dogs",        350, "🐕", "Собаки",            "epic",   30_000,
        "Верные охранники, их лай отгоняет воров и привлекает монеты."),
    ("cats",        425, "🐱", "Кошки",             "epic",   35_000,
        "Тайные охотники, их мурлыканье повышает доход фермы."),
    ("deer",        500, "🦌", "Олени",             "epic",   40_000,
        "Их рога могут быть выкованы в золотые артефакты."),
    ("foxes",       560, "🦊", "Лисы",              "epic",   45_000,
        "Хитрые, они прячут золотые клады в своих норах."),
    ("wolves",      630, "🐺", "Волки",             "epic",   50_000,
        "Своим воем привлекают диких зверей, повышающих доход."),
    ("bears",       720, "🐻", "Медведи",           "epic",   55_000,
        "Могут добывать мёд, который продаётся за огромные суммы."),
    ("boars",       685, "🐗", "Кабаны",            "epic",   53_000,
        "С их клыками можно открыть редкие сундуки."),
    ("raccoons",    450, "🦝", "Еноты",             "epic",   33_000,
        "Любят воровать блестящие вещи, которые потом продаются."),
    ("badgers",     475, "🦡", "Барсуки",           "epic",   35_000,
        "Копают под землёй, находя драгоценные кристаллы."),
    ("skunks",      400, "🦨", "Скунсы",            "epic",   30_000,
        "Их запах отпугивает воров, а ароматные шишки продаются за монеты."),
    ("lynx",        650, "🐈‍⬛", "Рысь",            "epic",   48_000,
        "Холодный взгляд превращает добычу в золото."),
    ("bobcat",      620, "🐈‍⬛", "Бобер‑кот",        "epic",   47_000,
        "Строит плотины из золотых веток."),
    ("jackal",      600, "🐕‍🦺", "Шакал",           "epic",   45_500,
        "Скользит в ночи, собирая монеты у спящих."),
    ("coyote",      590, "🐕‍🦺", "Койот",            "epic",   44_000,
        "Быстрый, как ветер, оставляет золотой след."),
    ("hyena",       720, "🦊", "Гиена",             "epic",   49_000,
        "Смеётся, когда монеты падают в её лапы."),
    ("wild_dog",    680, "🐕", "Дикая собака",      "epic",   42_000,
        "Бродит по пустошам, собирая редкие ресурсы."),
    ("wild_cat",    730, "🐈", "Дикая кошка",       "epic",   46_000,
        "Мягко мурлычет, превращая энергию в монеты."),
    ("jackrabbit",  560, "🐇", "Кролик‑скакун",     "epic",   38_000,
        "Скачет так быстро, что оставляет золотой след."),
    ("ermine",      610, "🦡", "Горностай",         "epic",   40_000,
        "Своей шубой может покрыть ферму золотой пылью."),
    ("marten",      590, "🦡", "Косуля",            "epic",   39_500,
        "Ловко собирает золотые орехи."),
    # ------------------- MYSTIC -------------------
    ("lions",      2000, "🦁", "Львы",              "mystic", 150_000,
        "Короли саванн, их рычание превращает землю в золото."),
    ("tigers",     2300, "🐯", "Тигры",             "mystic", 170_000,
        "Скрытные охотники, их полосы сияют драгоценными камнями."),
    ("pandas",     2600, "🐼", "Панды",             "mystic", 190_000,
        "Медитируют в бамбуковых рощах, где растут золотые листочки."),
    ("leopards",   2400, "🦚", "Гепарды",           "mystic", 165_000,
        "Бысты, как молния, их пятна могут превращаться в кристаллы."),
    ("jaguars",    2600, "🐆", "Ягуары",            "mystic", 175_000,
        "Сквозь ночную тьму они видят золотые сокровища."),
    ("cheetahs",   2500, "🐆", "Гепарды‑быстрые",   "mystic", 160_000,
        "Самые быстрые, их следы оставляют золотой пыль."),
    ("koalas",     2200, "🐨", "Коалы",             "mystic", 145_000,
        "Питаются магическим эвкалиптом, который превращается в монеты."),
    ("kangaroos",  2400, "🦘", "Кенгуру",           "mystic", 155_000,
        "Прыгают сквозь облака, собирая золотые звёзды."),
    ("platypus",   2300, "🦆", "Утконос",           "mystic", 150_000,
        "Своими странными способностями генерируют редкие ресурсы."),
    ("eagles",     2500, "🦅", "Орлы",              "mystic", 152_000,
        "Взмывают в небо, где находятся золотые облака."),
    ("hawks",      2400, "🦅", "Ястребы",           "mystic", 148_000,
        "Летят высоко, их крики вызывают падение монет с небес."),
    ("owls",       2300, "🦉", "Совы",              "mystic", 140_000,
        "Ночные стражи, их крики приносят золотой свет."),
    ("falcons",    2500, "🦅", "Соколы",            "mystic", 152_500,
        "Скорость и точность – их перья покрыты золотом."),
    ("griffin",    3800, "🦅", "Грифон",            "mystic", 300_000,
        "Полукрылый лев, охраняет сокровища, которые делит с хозяином."),
    ("phoenix",    4200, "🦜", "Феникс",            "mystic", 350_000,
        "Восстаёт из пепла, каждое возрождение приносит огромный доход."),
    ("unicorn",    3900, "🦄", "Единорог",          "mystic", 330_000,
        "Легенда, чей рог превращает всё в золото."),
    ("pegasus",    3800, "🦄","Пегас",             "mystic", 320_000,
        "Крылатый конь, его полёт ускоряет рост фермы."),
    ("kraken",     4300, "🐙","Кракен",            "mystic", 400_000,
        "Титан морей, его щупальца собирают редкие ресурсы."),
    ("yeti",       4100, "❄️","Йети",              "mystic", 380_000,
        "Скользит по снегу, оставляя золотой след."),
    ("sasquatch",  4000, "👣","Сасквоч",           "mystic", 375_000,
        "Тайный гигант, чьи шаги превращаются в монеты."),
    # ------------------- SECRET -------------------
    ("dragons",     8000, "🐉", "Драконы",          "secret", 1_500_000,
        "Огненные монстры, их чешуя – чистое золото."),
    ("hydras",      8500, "🐉", "Гидры",            "secret", 1_700_000,
        "Многоголовые чудовища, каждую голову можно продать за кучу монет."),
    ("leviathans",  9000, "🐋", "Левиафаны",        "secret", 1_900_000,
        "Гиганты океана, их шкуры ценятся на аукционах."),
    ("golems",      9500, "🗿", "Големы",           "secret", 2_100_000,
        "Из камня к золоту – их сердца полны ценных камней."),
    ("djinn",      10000, "🧞‍♂️", "Джинн",          "secret", 2_300_000,
        "Выполняют желания, но только за монеты."),
    ("basilisks",  10500, "🐍", "Базилиски",        "secret", 2_500_000,
        "Смотрят в вас – и вы получаете богатство."),
    ("chimeras",   11000, "🐲", "Химеры",           "secret", 2_700_000,
        "Сочетание сил, их части можно продать по разным ценам."),
    ("sirens",     11500, "🧜‍♀️", "Сирены",        "secret", 2_900_000,
        "Поют песни, которые заставляют монеты падать с небес."),
    ("wraiths",    12000, "👻", "Призраки",         "secret", 3_100_000,
        "Бродят между мирами, оставляя золотой туман."),
    ("specters",   12500, "👻", "Спектры",          "secret", 3_300_000,
        "Светятся в темноте, их свет – чистое золото."),
    ("liches",     13000, "☠️", "Личи",             "secret", 3_500_000,
        "Бессмертные маги, их книги полны ценных знаний."),
    ("archangels", 13500, "😇", "Архангелы",        "secret", 3_700_000,
        "Небесные воины, их благословения превращаются в монеты."),
    ("demon_lords",14000,"😈", "Владыки демонов",  "secret", 3_900_000,
        "Тёмные правители, их клятвы стоят огромных сумм."),
    ("celestials", 14500,"🌟","Божественные",     "secret", 4_100_000,
        "Светящиеся существа, их свет превращается в золото."),
    ("voidbeasts", 15000,"🌀","Существа Пустоты", "secret", 4_300_000,
        "Из бездны приносят редкие артефакты."),
    ("timekeepers",15500,"⏳","Хранители Времени","secret", 4_500_000,
        "Контролируют время, ускоряя рост дохода."),
    ("shadow_dragons",16000,"🐉","Теневые драконы","secret", 4_700_000,
        "Скрыты в тенях, их клыки продаются за баснословные суммы."),
    ("star_beasts",16500,"🌠","Звёздные звери","secret", 4_900_000,
        "Собирают свет звёзд, превращая его в монеты."),
    ("galactic_whales",17000,"🐋","Галактические киты","secret", 5_100_000,
        "Плывут по космосу, их песни приносят богатство."),
    ("secret_spider",18500,"🕷️","Паук‑секрет","secret", 5_300_000,
        "Ткань паука способна превращать любой предмет в золото."),
    # ------------------- ULTRA‑LEGENDARY (10 базовых) -------------------
    ("cosmic_behemoth",   80000, "🪐", "Космический Бегемот",    "ultra", 10_000_000,
        "Гигант из космоса, его дыхание превращает всё в драгоценные камни."),
    ("eternal_phoenix",   90000, "🦜", "Вечный Феникс",         "ultra", 12_000_000,
        "Восстаёт из пепла, каждое возрождение приносит огромный доход."),
    ("infinite_dragon",  100000, "🐉", "Бесконечный Дракон",    "ultra", 14_000_000,
        "Бесконечный, его чешуя стоит целое королевство."),
    ("mythic_leviathan",110000,"🐋","Мифический Левиафан","ultra", 16_000_000,
        "Легенда океанов, каждый его вздох – золотой дождь."),
    ("celestial_golem",  120000,"🗿","Небесный Голем",         "ultra", 18_000_000,
        "Создан из звёздного камня, его сердце – золотой кристалл."),
    ("void_kraken",       130000,"🐙","Кракен Пустоты",        "ultra", 20_000_000,
        "Ловит души в пустоте, превращая их в монеты."),
    ("time_wraith",       140000,"👻","Призрак Времени",       "ultra", 22_000_000,
        "Замораживает время, ускоряя рост дохода в разы."),
    ("stellar_unicorn",   150000,"🦄","Звёздный Единорог",     "ultra", 24_000_000,
        "Легенда, чей рог светит, превращая всё в золото."),
    ("dimensional_titan", 160000,"🧱","Измерительный Титан",   "ultra", 26_000_000,
        "Разрушает измерения, оставляя после себя золотой слой."),
    ("ultimate_spider",   170000,"🕷️","Ультимативный Паук",    "ultra", 28_000_000,
        "Ткань которого может превратить любой предмет в золото."),
    # ------------------- 40 остальных ULTRA‑LEGENDARY -------------------
    ("galactic_dragon",      180000, "🐉", "Галактический Дракон",      "ultra", 30_000_000,
        "Сквозь звёздные поля его пламя кристализуется в чистый золотоносный кристалл."),
    ("stellar_phoenix",      190000, "🦜", "Звёздный Феникс",          "ultra", 32_000_000,
        "Восстаёт из космического пепла, каждый полёт – миллиарды монет."),
    ("quantum_unicorn",      200000, "🦄", "Квантовый Единорог",        "ultra", 34_000_000,
        "Разрушает законы физики: каждый шаг генерирует золотой поток."),
    ("void_wyrm",            210000, "🐉", "Войд Вирм",                "ultra", 36_000_000,
        "Обитает в пустоте, поглощает всё, оставляя лишь золото."),
    ("alpha_leviathan",      220000, "🐋", "Альфа Левиафан",           "ultra", 38_000_000,
        "Владыка морей, каждое открытие воды превращается в монеты."),
    ("beta_golem",            230000, "🗿", "Бета Голем",               "ultra", 40_000_000,
        "Из камня к золоту – их сердца полны ценных камней."),
    ("sigma_kraken",          240000, "🐙", "Сигма Кракен",             "ultra", 42_000_000,
        "Увеличивает доход в 10 раз, когда активирован."),
    ("omega_spider",          250000, "🕷️","Омега Паук",                "ultra", 44_000_000,
        "Сеть его паутины охватывает весь мир, превращая всё в золото."),
    ("nebula_titan",          260000, "🧱","Титан Туманности",          "ultra", 46_000_000,
        "Сокрушает галактики, оставляя после себя золотой след."),
    ("chrono_phoenix",        270000, "🦜","Хроно Феникс",             "ultra", 48_000_000,
        "Переписывает время, каждый взлёт удваивает доход."),
    ("aurora_dragon",         280000, "🐉","Аврора Дракон",            "ultra", 50_000_000,
        "Светится полярным сиянием, каждое дыхание – золотой дождь."),
    ("radiant_unicorn",       290000, "🦄","Сияющий Единорог",         "ultra", 52_000_000,
        "Свет его рога превращает любой материал в золото."),
    ("celestial_spider",      300000, "🕷️","Небесный Паук",            "ultra", 54_000_000,
        "Ткань из космического света превращает всё в драгоценные камни."),
    ("hyper_leviathan",       310000, "🐋","Гипер‑Левиафан",           "ultra", 56_000_000,
        "Гипер‑масштабный, каждое движение генерирует сотни тысяч монет."),
    ("quantum_golem",         320000, "🗿","Квантовый Голем",          "ultra", 58_000_000,
        "Собран из квантовых частиц, излучает бесконечный доход."),
    ("void_phoenix",          330000, "🦜","Войд Феникс",              "ultra", 60_000_000,
        "Воскрешается из пустоты, каждое возрождение – миллиарды монет."),
    ("stellar_spider",        340000, "🕷️","Звёздный Паук",            "ultra", 62_000_000,
        "Плетёт паутину из звёздного света, превращая всё в золото."),
    ("cosmic_unicorn",        350000, "🦄","Космический Единорог",     "ultra", 64_000_000,
        "Рог из космического излучения превращает всё в монеты."),
    ("chrono_dragon",         360000, "🐉","Хроно Дракон",             "ultra", 66_000_000,
        "Контролирует время, каждый удар удваивает доход."),
    ("aurora_phoenix",        370000, "🦜","Аврора Феникс",            "ultra", 68_000_000,
        "Возрождается в сиянии полярных сияний, даря золотой дождь."),
    ("radiant_spider",        380000, "🕷️","Сияющий Паук",             "ultra", 70_000_000,
        "Ткань из чистого света превращает любые ресурсы в золото."),
    ("nebula_unicorn",        390000, "🦄","Туманный Единорог",        "ultra", 72_000_000,
        "Создаёт золотой вихрь при каждом шаге."),
    ("hyper_dragon",          400000, "🐉","Гипер Дракон",             "ultra", 74_000_000,
        "Увеличивает доход в 100 раз после каждой победы."),
    ("alpha_phoenix",         410000, "🦜","Альфа Феникс",             "ultra", 76_000_000,
        "Первая птица возрождения, её крик превращает всё в монеты."),
    ("beta_spider",           420000, "🕷️","Бета Паук",                "ultra", 78_000_000,
        "Сеть из черных нитей генерирует огромный доход."),
    ("sigma_unicorn",         430000, "🦄","Сигма Единорог",           "ultra", 80_000_000,
        "Мощный рог, генерирующий бесконечные монеты."),
    ("omega_dragon",          440000, "🐉","Омега Дракон",             "ultra", 82_000_000,
        "Последний дракон, каждое дыхание – золотой шторм."),
    ("chrono_spider",         450000, "🕷️","Хроно Паук",               "ultra", 84_000_000,
        "Ткань из времени, ускоряющая доход в разы."),
    ("aurora_unicorn",        460000, "🦄","Аврора Единорог",          "ultra", 86_000_000,
        "Светящийся рог создаёт золотой дождь."),
    ("radiant_dragon",        470000, "🐉","Сияющий Дракон",           "ultra", 88_000_000,
        "Каждое движение – поток золотой энергии."),
    ("nebula_spider",         480000, "🕷️","Туманный Паук",            "ultra", 90_000_000,
        "Ткань из космического тумана превращает всё в монеты."),
    ("hyper_unicorn",         490000, "🦄","Гипер Единорог",           "ultra", 92_000_000,
        "Экстремальный рост дохода при каждом шаге."),
    ("alpha_dragon",          500000, "🐉","Альфа Дракон",             "ultra", 94_000_000,
        "Самый первый дракон – каждый урон удваивает доход."),
    ("beta_phoenix",          510000, "🦜","Бета Феникс",              "ultra", 96_000_000,
        "Восстанавливается из звёздного пепла, даря огромный доход."),
    ("sigma_spider",          520000, "🕷️","Сигма Паук",               "ultra", 98_000_000,
        "Ткань из сигм, генерирует бесконечные монеты."),
    ("omega_unicorn",         530000, "🦄","Омега Единорог",           "ultra",100_000_000,
        "Последний рог, каждый удар – золотой взрыв."),
    # ------------------- МЕГА‑СУПЕР‑СЕКРЕТНЫЕ (10 новых) -------------------
    ("galactic_overlord", 1_000_000, "👑", "Галактический Оверлорд", "ultra",
        1_000_000_000_000,
        "Владыка всей вселенной – каждый час генерирует триллионы монет."),
    ("quantum_nihility",  1_200_000, "⚛️", "Квантовое Ничто",        "ultra",
        2_000_000_000_000,
        "Существует вне реальности, создаёт бесконечный поток монет."),
    ("void_eternity",     1_400_000, "🌀", "Вечность Пустоты",       "ultra",
        3_000_000_000_000,
        "Бесконечный цикл, каждый тик – миллиарды монет."),
    ("time_anomaly",      1_600_000, "⏳", "Аномалия Времени",       "ultra",
        5_000_000_000_000,
        "Искажает время, каждый момент приносит бесконечный доход."),
    ("omniscient_being",  1_800_000, "👁️", "Всевидящее Существо",    "ultra",
        10_000_000_000_000,
        "Знает всё, генерирует монеты быстрее света."),
    ("Rick",  3_000_000, "🐕‍🦺", "Дьявольская собака",    "ultra",
        20_000_000_000_000,
        "Просто существует."),
    ("Galac", 3_500_000, "☄️", "Гравитонный геккон «Крайзуб»",    "ultra",
        25_000_000_000_000,
        "Может «прыгать» между гравитационными «платформами», используя локальные искривления пространства, почти мгновенно перемещаясь на сотни километров."),
    ("Osminog",  4_500_000, "🐙", " Пульсирующий морской «Звёздный осьминог»",    "ultra",
        33_000_000_000_000,
        " Может синхронизировать своё биолюминесцентное свечение с космическими пульсациями, создавая «астрономические» сигналы, используемые для коммуникации с другими видами."),
    ("pes",  6_000_000, "🦕", "Песчаный кибер‑моль",    "ultra",
        45_000_000_000_000,
        "Моль может «плыть» по магнитным линиям поля, оставляя за собой след из кристаллического пепла, который служит как «маршрутный сигнал» для остальных особей."),
    ("trrr",  10_000_000, "🦊", "Лунный «Тканевый лис»",    "ultra",
        60_000_000_000_000,
        "Может менять форму своего тела, «растягивая» или «сжимая» собственные нити, тем самым прячась в тканевых лабиринтах."),
]

# ----------------------------------------------------------------------
#   Фермеры
# ----------------------------------------------------------------------
# (type, price, income_per_min, description)
FARMER_CONFIG: List[Tuple[str, int, int, str]] = [
    ("Местный фермер",          100_000_000,   5_000,  "Небольшой участок, даёт +5 000 🪙/мин."),
    ("Опытный фермер",          500_000_000,  30_000,  "Увеличивает доход всех животных на 5 %."),
    ("Профессиональный фермер", 25_000_000_000, 150_000,
        "Умножает доход в 2 раза и даёт +15 % к общему доходу."),
    ("Мастер‑фермер",           500_000_000_000,800_000,
        "Постоянный +800 000 🪙/мин, независимо от количества животных."),
    ("Эпический фермер",        1_000_000_000_000,5_000_000,
        "Увеличивает доход в 5 раз, а также даёт ежедневный бонус +5 % к доходу."),
    ("Легендарный фермер",      5_000_000_000_000,30_000_000,
        "Постоянный доход +30 млн 🪙/мин и доход в 10 раз."),
    # Дополнительные фермеры
    ("Герой‑фермер",            12_000_000_000_000, 80_000_000,
        "Супер‑доход +80 млн 🪙/мин и доход в 15 раз."),
    ("Титан‑фермер",            30_000_000_000_000, 200_000_000,
        "Мега‑доход +200 млн 🪙/мин, доход в 25 раз."),
    ("Бог‑фермер",              1_000_000_000_000_000, 500_000_000,
        "Божественный доход +500 млн 🪙/мин и доход в 50 раз."),
]
# Картинки фермеров (можно заменить на свои ссылки)
FARMER_IMAGES: Dict[str, str] = {
    "Местный фермер":          "https://i.postimg.cc/mkmgJD4J/437572358.jpg",
    "Опытный фермер":          "https://i.postimg.cc/j5KqjNdB/813994320.jpg",
    "Профессиональный фермер": "https://i.postimg.cc/K8MmrQ1d/751751786.jpg",
    "Мастер‑фермер":           "https://i.postimg.cc/q7rHcrV3/374351423.jpg",
    "Эпический фермер":        "https://i.postimg.cc/PqqsV4JX/132823775.jpg",
    "Легендарный фермер":      "https://i.postimg.cc/0NjF0yXr/722564872.jpg",
    "Герой‑фермер":            "https://i.postimg.cc/W1bHs4vS/872206903.jpg",
    "Титан‑фермер":            "https://i.postimg.cc/25LT5bXd/697384440.jpg",
    "Бог‑фермер":              "https://i.postimg.cc/3xsmnLnp/290306363.jpg",
}
def get_farmer(name: str) -> Tuple[str, int, int, str] | None:
    for rec in FARMER_CONFIG:
        if rec[0].lower() == name.lower():
            return rec
    return None


# ----------------------------------------------------------------------
#   Пагинация
# ----------------------------------------------------------------------
ITEMS_PER_PAGE = 10   # для пагинации в магазине и /pets


def paginate_items(items: List[Any], page: int) -> Tuple[List[Any], int]:
    total_pages = (len(items) - 1) // ITEMS_PER_PAGE + 1
    start = page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    return items[start:end], total_pages


# ----------------------------------------------------------------------
#   Доход (все питомцы, доход = income_per_minute)
# ----------------------------------------------------------------------
def calculate_income_per_min(user: sqlite3.Row) -> int:
    """Возврат дохода за одну минуту."""
    now = time.time()
    mult = 1.0
    # Обычный корм – +40 %
    if now < user["feed_bonus_end"]:
        mult *= 1.4
    # Осенний корм – ×2
    if now < user["autumn_bonus_end"]:
        mult *= 2.0
    base = 0
    for field, inc, *_ in ANIMAL_CONFIG:
        base += user[field] * inc
    # Доход от фермеров
    cur.execute("SELECT farmer_type, qty FROM farmers WHERE user_id = ?", (user["user_id"],))
    for row in cur.fetchall():
        farmer = get_farmer(row["farmer_type"])
        if farmer:
            _, _, farmer_income, _ = farmer
            base += farmer_income * row["qty"]
    base += user["custom_income"]
    base = int(base * mult)
    return max(1, base) if base > 0 else 0


# ----------------------------------------------------------------------
#   Автосбор дохода (каждую минуту)
# ----------------------------------------------------------------------
async def auto_collect(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Каждую минуту начисляем доход."""
    cur.execute("SELECT user_id FROM users")
    for (uid,) in cur.fetchall():
        user = get_user(uid)
        earned = calculate_income_per_min(user)
        if earned == 0:
            continue
        new_coins = min(user["coins"] + earned, MAX_INT)
        new_weekly = min(user["weekly_coins"] + earned, MAX_INT)
        update_user(uid, coins=new_coins, weekly_coins=new_weekly)
        log_user_action(uid, f"Получено {earned}🪙 (автосбор)")


# ----------------------------------------------------------------------
#   Проверка голода (каждые 5 мин)
# ----------------------------------------------------------------------
async def check_hunger(context: ContextTypes.DEFAULT_TYPE) -> None:
    cur.execute("SELECT user_id FROM users")
    for (uid,) in cur.fetchall():
        user = get_user(uid)
        for field, _, _, _, _, _, _ in ANIMAL_CONFIG:
            cnt = user[field]
            if cnt == 0:
                continue
            last_fed = get_pet_last_fed(uid, field)
            if last_fed is None:
                set_pet_last_fed(uid, field, int(time.time()))
                continue
            if time.time() - last_fed > HUNGER_TIME:
                update_user(uid, **{field: 0})
                delete_pet_last_fed(uid, field)
                log_user_action(uid, f"Потеряно всех {field} из‑за голода")


# ----------------------------------------------------------------------
#   Ежедневный билет
# ----------------------------------------------------------------------
def give_daily_ticket(user: sqlite3.Row) -> bool:
    now = int(time.time())
    if now - user["last_ticket_time"] >= 86400:
        update_user(
            user["user_id"],
            tickets=user["tickets"] + 1,
            last_ticket_time=now,
        )
        return True
    return False


# ----------------------------------------------------------------------
#   Титулы (большой набор «прикольных» названий)
# ----------------------------------------------------------------------
TITLE_TABLE: List[Tuple[int, str]] = [
    (0, "Новичок 🐣"),
    (500, "Фермер 🌾"),
    (1_000, "Саженец 🌱"),
    (2_500, "Почвовед 🌍"),
    (5_000, "Плантатор 🌿"),
    (7_500, "Агрокомбинатор 🚜"),
    (10_000, "Тракторист 🚜"),
    (12_500, "Сельский маг 🧙‍♂️"),
    (15_000, "Хозяин полей 🏞️"),
    (20_000, "Золотой пахарь 🪙"),
    (25_000, "Кузнец урожая ⚒️"),
    (30_000, "Эксперт агро 🧪"),
    (35_000, "Биоинженер 🧬"),
    (40_000, "Мастер фермы 🏆"),
    (45_000, "Легенда пахотных земель 🌾"),
    (50_000, "Суперфермер 🦸‍♂️"),
    (60_000, "Король урожая 👑"),
    (70_000, "Император зерна 👑"),
    (80_000, "Гроссмейстер фермы 🏅"),
    (90_000, "Бог урожая 🕊️"),
    (100_000, "Магнат 💰"),
    (125_000, "Титан сельского хозяйства 🗿"),
    (150_000, "Владыка полей 🏰"),
    (175_000, "Покровитель земли 🌍"),
    (200_000, "Повелитель посевов 🌾"),
    (250_000, "Солнечный фермер ☀️"),
    (300_000, "Галактический агроном 🌌"),
    (350_000, "Звёздный земледелец 🌠"),
    (400_000, "Космический фермер 🚀"),
    (500_000, "Легенда 🏆"),
    (750_000, "Мифический агроном 🐲"),
    (1_000_000, "Божественный фермер 👼"),
    (2_000_000, "Эпический магнат 🏅"),
    (5_000_000, "Бессмертный владелец 🌌"),
    (10_000_000, "Титан эпохи 🏛️"),
]


def get_status(coins: int) -> str:
    """Выбирает самый высокий титул, не превышающий количество монет."""
    title = "Новичок 🐣"
    for limit, name in TITLE_TABLE:
        if coins >= limit:
            title = name
        else:
            break
    return title


# ----------------------------------------------------------------------
#   Клавиатурные утилиты
# ----------------------------------------------------------------------
def chunk_buttons(
    buttons: List[InlineKeyboardButton], per_row: int = 3
) -> List[List[InlineKeyboardButton]]:
    return [buttons[i: i + per_row] for i in range(0, len(buttons), per_row)]


# ----------------------------------------------------------------------
#   Сезонный механизм
# ----------------------------------------------------------------------
def check_and_reset_season() -> None:
    """Если прошёл SEASON_LENGTH, сбрасываем всё и начинаем новый сезон."""
    cur.execute("SELECT season_start, season_number FROM global_settings WHERE id = 1")
    row = cur.fetchone()
    now = int(time.time())
    if now - row["season_start"] >= SEASON_LENGTH:
        # Полный сброс (удаляем всё)
        _execute("DELETE FROM users")
        _execute("DELETE FROM pet_last_fed")
        _execute("DELETE FROM decorations")
        _execute("DELETE FROM lottery")
        _execute("DELETE FROM boosters")
        _execute("DELETE FROM promo_codes")
        _execute("DELETE FROM farmers")
        new_start = now
        new_number = row["season_number"] + 1
        _execute(
            "UPDATE global_settings SET season_start = ?, season_number = ? WHERE id = 1",
            (new_start, new_number),
        )
        log.info("Сезон сброшен. Новый сезон №%s", new_number)


def get_season_info() -> Tuple[int, int]:
    """Возвращает (секунд до конца сезона, номер текущего сезона)."""
    cur.execute("SELECT season_start, season_number FROM global_settings WHERE id = 1")
    row = cur.fetchone()
    now = int(time.time())
    left = max(0, SEASON_LENGTH - (now - row["season_start"]))
    return left, row["season_number"]


# ----------------------------------------------------------------------
#   Общая функция редактирования разделов с картинкой ← NEW
# ----------------------------------------------------------------------
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


# ----------------------------------------------------------------------
#   Главное меню
# ----------------------------------------------------------------------
def build_main_menu(user_id: int) -> InlineKeyboardMarkup:
    rows = []
    rows.append([InlineKeyboardButton("ℹ️ О боте", callback_data="about")])
    other = [
        InlineKeyboardButton("🌾 Моя ферма", callback_data="farm"),
        InlineKeyboardButton("🛒 Магазин", callback_data="shop"),
        InlineKeyboardButton("👨‍🌾 Фермеры", callback_data="farmers_shop"),
        InlineKeyboardButton("📊 Статус", callback_data="status"),
        InlineKeyboardButton("💰 Получить монеты", callback_data="get_coins"),
        InlineKeyboardButton("🎰 Казино", callback_data="casino_info"),
        InlineKeyboardButton("🎟️ Промокоды", callback_data="promo"),
        InlineKeyboardButton("🍂 Осеннее событие", callback_data="autumn_event"),
    ]
    rows.extend(chunk_buttons(other, per_row=3))
    if is_admin(user_id):
        rows.append([InlineKeyboardButton("🔥 Админ", callback_data="admin")])
    return InlineKeyboardMarkup(rows)


# ----------------------------------------------------------------------
#   Показ главного меню
# ----------------------------------------------------------------------
async def show_main_menu(
    update: Update, context: ContextTypes.DEFAULT_TYPE, edit: bool = False
) -> None:
    user = update.effective_user
    db_user = get_user(user.id)
    ticket_msg = (
        "\n🎟️ Ты получил 1 билет за ежедневный вход!"
        if give_daily_ticket(db_user)
        else ""
    )
    text = f"🤖 Добро пожаловать в Ферму!{ticket_msg}"
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


# ----------------------------------------------------------------------
#   О боте
# ----------------------------------------------------------------------
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


# ----------------------------------------------------------------------
#   Моя ферма (без кнопки «Переродиться», без X‑фермы)
# ----------------------------------------------------------------------
async def farm_section(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = query.from_user.id
    user = get_user(uid)
    now = time.time()
    # Список животных
    lines = []
    for field, inc, emoji, name, *_ in ANIMAL_CONFIG:
        cnt = user[field]
        if cnt == 0:
            continue
        inc_total = inc * cnt
        last_fed = get_pet_last_fed(uid, field)
        timer = "—"
        if last_fed:
            left = int(HUNGER_TIME - (now - last_fed))
            if left > 0:
                h, r = divmod(left, 3600)
                m = r // 60
                timer = f"⏳ {h}ч {m}м"
        lines.append(
            f"{emoji} {name}: {cnt} (+{format_num(inc_total)}🪙/мин) {timer}"
        )
    farm_text = "\n".join(lines) or "❌ На ферме пока нет животных."
    # Список фермеров
    cur.execute("SELECT farmer_type, qty FROM farmers WHERE user_id = ?", (uid,))
    farmer_rows = cur.fetchall()
    farmer_lines = []
    for fr in farmer_rows:
        f_type = fr["farmer_type"]
        qty = fr["qty"]
        rec = get_farmer(f_type)
        if rec:
            _, _, inc, _ = rec
            farmer_lines.append(
                f"👨‍🌾 {f_type}: {qty} ( +{format_num(inc * qty)}🪙/мин )"
            )
    farmer_text = "\n".join(farmer_lines) if farmer_lines else "⚒️ Фермеров нет."
    # Инфо о бустах
    boost_parts = []
    if now < user["feed_bonus_end"]:
        left = int(user["feed_bonus_end"] - now)
        h, r = divmod(left, 3600)
        m = r // 60
        boost_parts.append(f"🍎 Обычный корм: +40% ({h}ч {m}м)")
    if now < user["autumn_bonus_end"]:
        left = int(user["autumn_bonus_end"] - now)
        h, r = divmod(left, 3600)
        m = r // 60
        boost_parts.append(f"🍂 Осенний корм: ×2 ({h}ч {m}м)")
    boost_line = "\n".join(boost_parts) if boost_parts else "⚡ Бустов нет"
    # Кнопки внутри фермы (без «Переродиться»)
    btns = [
        InlineKeyboardButton("🍎 Кормить животных", callback_data="feed_animal"),
        InlineKeyboardButton("📉 Продать животных", callback_data="sell_animal"),
        InlineKeyboardButton("🏗️ Улучшить базу", callback_data="upgrade_base"),
        InlineKeyboardButton("🏆 Топ фермеров", callback_data="top"),
        InlineKeyboardButton("⬅️ Главное меню", callback_data="back"),
    ]
    kb = InlineKeyboardMarkup(chunk_buttons(btns, per_row=2))
    await edit_section(
        query,
        caption=(
            f"🌾 Ферма 🌾\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 Монеты: {format_num(user['coins'])}\n"
            f"💰 Доход за минуту: {format_num(calculate_income_per_min(user))}🪙\n"
            f"🏗️ База: уровень {user['base_level']} (лимит: {user['pet_limit']})\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"{boost_line}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"{farm_text}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"{farmer_text}"
        ),
        image_key="farm",
        reply_markup=kb,
    )


# ----------------------------------------------------------------------
#   Кормление животных
# ----------------------------------------------------------------------
async def feed_animal_step(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = query.from_user.id
    user = get_user(uid)
    # Доступные типы корма
    feed_type_btns = []
    if user["feed"] > 0:
        feed_type_btns.append(
            InlineKeyboardButton("🍎 Обычный корм", callback_data="feed_type_normal")
        )
    if user["autumn_feed"] > 0:
        feed_type_btns.append(
            InlineKeyboardButton("🍂 Осенний корм", callback_data="feed_type_autumn")
        )
    if not feed_type_btns:
        await edit_section(
            query,
            caption="❌ У вас нет ни обычного, ни осеннего корма!",
            image_key="farm",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⬅️ Назад", callback_data="farm")]]
            ),
        )
        return
    # Сохраняем тип корма (по умолчанию – первый доступный)
    context.user_data["feed_type"] = "normal" if user["feed"] > 0 else "autumn"
    # Выбираем животное
    animal_btns = []
    for field, _, emoji, name, *_ in ANIMAL_CONFIG:
        if user[field] > 0:
            animal_btns.append(
                InlineKeyboardButton(f"{emoji} {name}", callback_data=f"feed_{field}")
            )
    if not animal_btns:
        await edit_section(
            query,
            caption="❌ У вас нет животных!",
            image_key="farm",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⬅️ Назад", callback_data="farm")]]
            ),
        )
        return
    animal_btns.append(InlineKeyboardButton("⬅️ Назад", callback_data="farm"))
    kb = InlineKeyboardMarkup(chunk_buttons(animal_btns, per_row=3))
    await edit_section(
        query,
        caption="🍎 Выберите животное для кормления:",
        image_key="farm",
        reply_markup=kb,
    )


async def feed_type_chosen(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатываем выбор типа корма (обычный/осенний)."""
    feed_type = query.data.split("_")[-1]          # normal / autumn
    context.user_data["feed_type"] = feed_type
    await edit_section(
        query,
        caption=f"✅ Выбран {'обычный' if feed_type == 'normal' else 'осенний'} корм. Выберите животное:",
        image_key="farm",
        reply_markup=query.message.reply_markup,
    )


async def feed_animal(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Кормим конкретное животное выбранным типом корма."""
    uid = query.from_user.id
    user = get_user(uid)
    animal = query.data.split("_", 1)[1]           # field name
    feed_type = context.user_data.get("feed_type", "normal")
    if feed_type == "normal":
        if user["feed"] == 0:
            await edit_section(
                query,
                caption="❌ Нет обычного корма!",
                image_key="farm",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("⬅️ Назад", callback_data="farm")]]
                ),
            )
            return
        update_user(
            uid,
            feed=user["feed"] - 1,
            feed_bonus_end=int(time.time()) + 3600,
            reputation=user["reputation"] + 1,
        )
        log_user_action(uid, f"Кормил {animal} обычным кормом")
        bonus_text = "+40% дохода"
    else:   # autumn
        if user["autumn_feed"] == 0:
            await edit_section(
                query,
                caption="❌ Нет осеннего корма!",
                image_key="farm",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("⬅️ Назад", callback_data="farm")]]
                ),
            )
            return
        update_user(
            uid,
            autumn_feed=user["autumn_feed"] - 1,
            autumn_bonus_end=int(time.time()) + 3600,
            reputation=user["reputation"] + 1,
        )
        log_user_action(uid, f"Кормил {animal} осенним кормом")
        bonus_text = "×2 дохода"
    set_pet_last_fed(uid, animal, int(time.time()))
    await edit_section(
        query,
        caption=f"🍎 {animal.capitalize()} покормлен! {bonus_text} на 1 ч.",
        image_key="farm",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("⬅️ Назад", callback_data="farm")]]
        ),
    )


# ----------------------------------------------------------------------
#   Продажа животных
# ----------------------------------------------------------------------
async def sell_animal_step(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = query.from_user.id
    user = get_user(uid)
    btns = []
    for field, _, emoji, name, _, price, _ in ANIMAL_CONFIG:
        if user[field] > 0:
            btns.append(
                InlineKeyboardButton(
                    f"📉 {emoji} {name} ({user[field]} шт.)",
                    callback_data=f"sell_{field}"
                )
            )
    if not btns:
        await edit_section(
            query,
            caption="❌ У тебя нет животных для продажи!",
            image_key="farm",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⬅️ Назад", callback_data="farm")]]
            ),
        )
        return
    btns.append(InlineKeyboardButton("⬅️ Назад", callback_data="farm"))
    kb = InlineKeyboardMarkup(chunk_buttons(btns, per_row=2))
    await edit_section(
        query,
        caption="📉 Выберите питомца, который хотите продать:",
        image_key="farm",
        reply_markup=kb,
    )


async def sell_animal_quantity(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    pet_field = query.data.split("_", 1)[1]
    uid = query.from_user.id
    user = get_user(uid)
    qty_btns = [
        InlineKeyboardButton("1", callback_data=f"sell_qty_{pet_field}_1"),
        InlineKeyboardButton("5", callback_data=f"sell_qty_{pet_field}_5"),
        InlineKeyboardButton("10", callback_data=f"sell_qty_{pet_field}_10"),
        InlineKeyboardButton("🅰️ Всё", callback_data=f"sell_qty_{pet_field}_all"),
    ]
    kb = InlineKeyboardMarkup([qty_btns])
    await edit_section(
        query,
        caption=f"Сколько {pet_field} продать? (у вас {user[pet_field]})",
        image_key="farm",
        reply_markup=kb,
    )


async def sell_animal_confirm(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатываем подтверждение продажи."""
    parts = query.data.split("_")
    # Формат: sell_qty_<field>_<qty>
    if len(parts) < 4:
        await query.edit_message_caption(caption="❌ Неверный формат.")
        return
    pet_field = "_".join(parts[2:-1])   # всё между 2‑м и предпоследним элементом
    qty_raw = parts[-1]
    rec = next((r for r in ANIMAL_CONFIG if r[0] == pet_field), None)
    if not rec:
        await query.edit_message_caption(caption="❌ Питомец не найден.")
        return
    price = rec[5]                     # цена за 1 шт.
    uid = query.from_user.id
    user = get_user(uid)
    owned = user[pet_field]
    qty = owned if qty_raw == "all" else int(qty_raw)
    qty = min(qty, owned)
    if qty <= 0:
        await query.edit_message_caption(caption="❌ Нечего продавать.")
        return
    reward = (price * qty) // 2      # 50 % от цены
    update_user(
        uid,
        **{pet_field: owned - qty},
        coins=user["coins"] + reward,
        weekly_coins=user["weekly_coins"] + reward,
        reputation=user["reputation"] + 1,
    )
    log_user_action(uid, f"Продал {qty} шт. {pet_field} за {reward}🪙")
    await edit_section(
        query,
        caption=(
            f"✅ Вы продали {qty} шт. `{pet_field}` за {format_num(reward)}🪙."
        ),
        image_key="farm",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("⬅️ Назад", callback_data="farm")]]
        ),
    )


# ----------------------------------------------------------------------
#   Улучшить базу
# ----------------------------------------------------------------------
async def upgrade_base(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = query.from_user.id
    user = get_user(uid)
    cost = BASE_UPGRADE_COST * (user["base_level"] + 1)
    if user["coins"] < cost:
        await edit_section(
            query,
            caption=f"❌ Недостаточно монет. Нужно {format_num(cost)}🪙.",
            image_key="farm",
        )
        return
    new_level = user["base_level"] + 1
    new_limit = user["pet_limit"] + BASE_LIMIT_STEP
    update_user(
        uid,
        coins=user["coins"] - cost,
        base_level=new_level,
        pet_limit=new_limit,
    )
    log_user_action(uid, f"Улучшил базу до уровня {new_level}")
    await edit_section(
        query,
        caption=(
            f"✅ База улучшена! Новый уровень – {new_level}\n"
            f"🧱 Лимит питомцев ↑ {new_limit}\n"
            f"💸 Потрачено {format_num(cost)}🪙."
        ),
        image_key="farm",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("⬅️ Назад", callback_data="farm")]]
        ),
    )


# ----------------------------------------------------------------------
#   Топ фермеров (раз в неделю, победитель получает тайный паук)
# ----------------------------------------------------------------------
async def top_farmers(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    now = int(time.time())
    week_sec = 604800
    # Сбрасываем топ раз в неделю
    if now - (get_user(query.from_user.id)["last_reset"] or 0) >= week_sec:
        cur.execute(
            "SELECT user_id, weekly_coins FROM users ORDER BY weekly_coins DESC LIMIT 1"
        )
        leader = cur.fetchone()
        if leader:
            # Выдаём тайный паук, но название не раскрываем
            update_user(leader["user_id"], secret_spider=1)
        _execute(
            "UPDATE users SET weekly_coins = 0, last_reset = ?, secret_spider = 0",
            (now,),
        )
    cur.execute(
        "SELECT username, weekly_coins, user_id FROM users ORDER BY weekly_coins DESC LIMIT 5"
    )
    top5 = cur.fetchall()
    txt = "🏆 Топ фермеров (недельный доход)\n━━━━━━━━━━━━\n"
    for i, row in enumerate(top5, 1):
        name = row["username"] or f"Пользователь {row['user_id']}"
        txt += f"{i}. {name} — {format_num(row['weekly_coins'])}🪙\n"
    left = max(0, week_sec - (now - (get_user(query.from_user.id)["last_reset"] or 0)))
    h, r = divmod(left, 3600)
    m = r // 60
    txt += f"━━━━━━━━━━━━\n🕷️ До тайного паука: {h}ч {m}м"
    await edit_section(
        query,
        caption=txt,
        image_key="top",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("⬅️ Назад", callback_data="farm")]]
        ),
    )


# ----------------------------------------------------------------------
#   Статус
# ----------------------------------------------------------------------
async def status_section(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = query.from_user.id
    user = get_user(uid)
    income_min = calculate_income_per_min(user)
    left, season_number = get_season_info()
    h, r = divmod(left, 3600)
    m = r // 60
    text = (
        f"📊 Статус 📊\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 ID: {user['user_id']}\n"
        f"💰 Монеты: {format_num(user['coins'])}\n"
        f"💰 Доход за минуту: {format_num(income_min)}🪙\n"
        f"🏗️ База: уровень {user['base_level']} (лимит: {user['pet_limit']})\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🎟️ Билетов: {user['tickets']}\n"
        f"💬 Репутация: {user['reputation']}\n"
        f"⚡ Титул: {get_status(user['coins'])}\n"
        f"🕷️ Паук‑секрет: {'Да' if user['secret_spider'] else 'Нет'}\n"
        f"⏳ До конца сезона №{season_number}: {h}ч {m}м\n"
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


# ----------------------------------------------------------------------
#   Получить монеты (задания)
# ----------------------------------------------------------------------
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


# ----------------------------------------------------------------------
#   Казино
# ----------------------------------------------------------------------
async def casino_info(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    await edit_section(
        query,
        caption=(
            "🎰 Чтобы сыграть в мини‑казино, используйте команду:\n"
            "/ставка <сумма> – минимум 100🪙.\n"
            "Пример: /ставка 5000"
        ),
        image_key="casino",
    )


# ----------------------------------------------------------------------
#   Магазин (питомцы + корм)
# ----------------------------------------------------------------------
async def render_shop(query, context: ContextTypes.DEFAULT_TYPE, page: int = 0) -> None:
    items, total_pages = paginate_items(ANIMAL_CONFIG, page)
    btns = [
        InlineKeyboardButton(
            f"🍎 Корм ({format_num(FOOD_PRICE)}🪙)", callback_data="buy_feed"
        )
    ]
    cur.execute("SELECT autumn_event_active FROM global_settings WHERE id = 1")
    if cur.fetchone()["autumn_event_active"]:
        btns.append(
            InlineKeyboardButton(
                f"🍂 Осенний корм ({format_num(AUTUMN_FOOD_PRICE)}🪙)",
                callback_data="buy_autumn_feed",
            )
        )
    for field, _, emoji, name, _, price, _ in items:
        btns.append(
            InlineKeyboardButton(
                f"{emoji} {name} ({format_num(price)}🪙)", callback_data=f"show_{field}"
            )
        )
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⏪ Пред.", callback_data="shop_prev"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("След. ⏩", callback_data="shop_next"))
    nav.append(InlineKeyboardButton("⬅️ Назад", callback_data="back"))
    kb = chunk_buttons(btns, per_row=2) + [nav]
    await edit_section(
        query,
        caption=f"🛒 Магазин – страница {page + 1}/{total_pages}",
        image_key="shop",
        reply_markup=InlineKeyboardMarkup(kb),
    )
    context.user_data["shop_page"] = page


async def shop_navigation(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    data = query.data
    cur_page = context.user_data.get("shop_page", 0)
    if data == "shop_next":
        await render_shop(query, context, page=cur_page + 1)
    elif data == "shop_prev":
        await render_shop(query, context, page=max(0, cur_page - 1))


# ----------------------------------------------------------------------
#   Показ питомца и покупка
# ----------------------------------------------------------------------
async def show_animal(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    field = query.data.split("_", 1)[1]
    rec = next((r for r in ANIMAL_CONFIG if r[0] == field), None)
    if not rec:
        await query.edit_message_caption(caption="❌ Питомец не найден.")
        return
    _, inc, emoji, name, _, price, desc = rec
    user = get_user(query.from_user.id)
    total_pets = sum(user[f] for f, *_ in ANIMAL_CONFIG)
    limit_reached = total_pets >= user["pet_limit"]
    txt = (
        f"{emoji} {name}\n"
        f"Доход: {inc}🪙/мин\n"
        f"Цена: {format_num(price)}🪙\n"
        f"{desc}"
    )
    if limit_reached:
        txt += f"\n⚠️ Вы достигли лимита питомцев ({user['pet_limit']}).\n"
        txt += "Сначала улучшите базу или продайте часть животных."
        btn = InlineKeyboardButton("⬅️ Назад", callback_data="shop")
        kb = InlineKeyboardMarkup([[btn]])
        await edit_section(query, caption=txt, image_key="shop", reply_markup=kb)
        return
    # Кнопка «Купить» → покажет окно выбора количества
    btn = InlineKeyboardButton("🛒 Купить", callback_data=f"buy_qty_{field}")
    kb = InlineKeyboardMarkup([[btn]])
    await edit_section(query, caption=txt, image_key="shop", reply_markup=kb)


async def buy_quantity(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    field = query.data.split("_", 2)[2]
    rec = next((r for r in ANIMAL_CONFIG if r[0] == field), None)
    if not rec:
        await query.edit_message_caption(caption="❌ Питомец не найден.")
        return
    _, _, _, _, _, price, _ = rec
    btns = [
        InlineKeyboardButton("1", callback_data=f"buy_confirm_{field}_1"),
        InlineKeyboardButton("5", callback_data=f"buy_confirm_{field}_5"),
        InlineKeyboardButton("10", callback_data=f"buy_confirm_{field}_10"),
        InlineKeyboardButton("🅰️ Всё", callback_data=f"buy_confirm_{field}_all"),
    ]
    kb = InlineKeyboardMarkup([btns])
    await edit_section(
        query,
        caption=f"Сколько {field} купить? (цена за 1 шт: {format_num(price)}🪙)",
        image_key="shop",
        reply_markup=kb,
    )


async def buy_confirm(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатываем подтверждение покупки."""
    parts = query.data.split("_")
    if len(parts) < 4:
        await query.edit_message_caption(caption="❌ Неверный формат.")
        return
    qty_raw = parts[-1]
    field = "_".join(parts[2:-1])   # всё между 2‑м и предпоследним элементом
    rec = next((r for r in ANIMAL_CONFIG if r[0] == field), None)
    if not rec:
        await query.edit_message_caption(caption="❌ Питомец не найден.")
        return
    _, _, _, _, _, price, _ = rec
    uid = query.from_user.id
    user = get_user(uid)
    # проверка лимита
    total_pets = sum(user[f] for f, *_ in ANIMAL_CONFIG)
    free_slots = user["pet_limit"] - total_pets
    if free_slots <= 0:
        await edit_section(
            query,
            caption=f"⚠️ Вы достигли лимита ({user['pet_limit']}) и не можете купить больше.",
            image_key="shop",
        )
        return
    qty = user["coins"] // price if qty_raw == "all" else int(qty_raw)
    qty = min(qty, free_slots)
    total_price = price * qty
    if qty <= 0:
        await edit_section(query, caption="❌ Нечего покупать.", image_key="shop")
        return
    if user["coins"] < total_price:
        await edit_section(
            query,
            caption=f"❌ Недостаточно монет. Нужно {format_num(total_price)}🪙.",
            image_key="shop",
        )
        return
    upd: Dict[str, Any] = {
        "coins": user["coins"] - total_price,
        "weekly_coins": user["weekly_coins"] + total_price,
        "reputation": user["reputation"] + 1,
    }
    upd[field] = user[field] + qty
    update_user(uid, **upd)
    set_pet_last_fed(uid, field, int(time.time()))
    log_user_action(uid, f"Купил {qty} шт. {field} за {total_price}🪙")
    await edit_section(
        query,
        caption=(
            f"🟢 Приобретено {qty} шт. {field}. Потрачено {format_num(total_price)}🪙."
        ),
        image_key="shop",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("⬅️ В магазин", callback_data="shop")]]
        ),
    )


# ----------------------------------------------------------------------
#   Корм (обычный и осенний)
# ----------------------------------------------------------------------
async def buy_feed(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = query.from_user.id
    user = get_user(uid)
    if user["coins"] < FOOD_PRICE:
        await edit_section(
            query,
            caption=f"❌ Недостаточно монет. Нужно {format_num(FOOD_PRICE)}🪙.",
            image_key="shop",
        )
        return
    update_user(
        uid,
        coins=user["coins"] - FOOD_PRICE,
        feed=user["feed"] + 1,
        weekly_coins=user["weekly_coins"] + FOOD_PRICE,
        reputation=user["reputation"] + 1,
    )
    log_user_action(uid, "+1 обычный корм")
    await edit_section(
        query,
        caption=f"✅ +1 обычный корм за {format_num(FOOD_PRICE)}🪙.",
        image_key="shop",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("⬅️ В магазин", callback_data="shop")]]
        ),
    )


async def buy_autumn_feed(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = query.from_user.id
    user = get_user(uid)
    if user["coins"] < AUTUMN_FOOD_PRICE:
        await edit_section(
            query,
            caption=f"❌ Недостаточно монет. Нужно {format_num(AUTUMN_FOOD_PRICE)}🪙.",
            image_key="shop",
        )
        return
    update_user(
        uid,
        coins=user["coins"] - AUTUMN_FOOD_PRICE,
        autumn_feed=user["autumn_feed"] + 1,
        weekly_coins=user["weekly_coins"] + AUTUMN_FOOD_PRICE,
        reputation=user["reputation"] + 1,
    )
    log_user_action(uid, "+1 осенний корм")
    await edit_section(
        query,
        caption=f"✅ +1 осенний корм за {format_num(AUTUMN_FOOD_PRICE)}🪙.",
        image_key="shop",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("⬅️ В магазин", callback_data="shop")]]
        ),
    )


# ----------------------------------------------------------------------
#   Осеннее событие (инфо + админ‑переключатель)
# ----------------------------------------------------------------------
async def autumn_event_info(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    cur.execute("SELECT autumn_event_active FROM global_settings WHERE id = 1")
    active = cur.fetchone()["autumn_event_active"]
    status = "✅ Включено" if active else "❌ Выключено"
    text = (
        f"{status}\n\n"
        "🍂 Осеннее событие – временный бонус:\n"
        f"• При покупке осеннего корма (в магазине) вы получаете двойной доход\n"
        f"  на 1 ч.\n"
        f"• Стоимость осеннего корма – {format_num(AUTUMN_FOOD_PRICE)}🪙.\n"
        "• Бонус активен только пока событие включено администратором."
    )
    await edit_section(
        query,
        caption=text,
        image_key="autumn",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("⬅️ Назад", callback_data="back")]]
        ),
    )


async def toggle_autumn_event(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(query.from_user.id):
        await edit_section(query, caption="❌ Доступ запрещён.", image_key="autumn")
        return
    cur.execute("SELECT autumn_event_active FROM global_settings WHERE id = 1")
    current = cur.fetchone()["autumn_event_active"]
    new_val = 0 if current else 1
    _execute(
        "UPDATE global_settings SET autumn_event_active = ? WHERE id = 1",
        (new_val,),
    )
    # Уведомляем всех игроков
    txt = f"🍂 Осеннее событие {'включено' if new_val else 'выключено'}."
    cur.execute("SELECT user_id FROM users")
    for (uid,) in cur.fetchall():
        try:
            context.bot.send_message(uid, txt)
        except Exception:
            pass
    await edit_section(
        query,
        caption=f"🍂 Осеннее событие {('включено' if new_val else 'выключено')}.",
        image_key="autumn",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("⬅️ Назад", callback_data="admin")]]
        ),
    )


# ----------------------------------------------------------------------
#   Промокоды
# ----------------------------------------------------------------------
def add_promo(
    code: str, coins: int, pet_field: str | None, pet_qty: int, max_uses: int
) -> None:
    """Создаёт промокод (может использоваться max_uses раз)."""
    _execute(
        """
        INSERT OR REPLACE INTO promo_codes
        (code, coins, pet_field, pet_qty, max_uses, used)
        VALUES (?,?,?,?,?,0)
        """,
        (code, coins, pet_field, pet_qty, max_uses),
    )


def get_promo(code: str) -> sqlite3.Row | None:
    cur.execute("SELECT * FROM promo_codes WHERE code = ?", (code,))
    return cur.fetchone()


def delete_promo(code: str) -> None:
    _execute("DELETE FROM promo_codes WHERE code = ?", (code,))


async def promo_menu(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать пользователю кнопку ввода кода."""
    await edit_section(
        query,
        caption="🎟️ Введите промокод (одно слово).",
        image_key="promo",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("⬅️ Назад", callback_data="back")]]
        ),
    )
    context.user_data["awaiting_promo_input"] = True


async def handle_promo_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает ввод кода пользователем."""
    code = update.message.text.strip().upper()
    promo = get_promo(code)
    if not promo:
        await update.message.reply_text("❌ Промокод не найден или исчерпан.")
        context.user_data["awaiting_promo_input"] = False
        return
    if promo["used"] >= promo["max_uses"]:
        await update.message.reply_text("❌ Промокод уже исчерпан.")
        context.user_data["awaiting_promo_input"] = False
        return
    uid = update.effective_user.id
    user = get_user(uid)
    # Добавляем монеты
    new_coins = min(user["coins"] + promo["coins"], MAX_INT)
    update_user(uid, coins=new_coins, weekly_coins=user["weekly_coins"] + promo["coins"])
    # Если указан питомец – добавляем
    if promo["pet_field"]:
        cur.execute(f"SELECT {promo['pet_field']} FROM users WHERE user_id = ?", (uid,))
        cur_row = cur.fetchone()
        cur_val = cur_row[promo["pet_field"]]
        update_user(uid, **{promo["pet_field"]: cur_val + promo["pet_qty"]})
        set_pet_last_fed(uid, promo["pet_field"], int(time.time()))
    # Увеличиваем счётчик использований
    _execute(
        "UPDATE promo_codes SET used = used + 1 WHERE code = ?",
        (code,),
    )
    log_user_action(uid, f"Активировал промокод {code}")
    await update.message.reply_text(
        f"✅ Промокод принят! Вы получили {format_num(promo['coins'])}🪙"
        + (f" и {promo['pet_qty']} шт. `{promo['pet_field']}`." if promo["pet_field"] else ".")
    )
    context.user_data["awaiting_promo_input"] = False


# ----------------------------------------------------------------------
#   Магазин фермеров (просмотр → подтверждение покупки)
# ----------------------------------------------------------------------
async def farmers_shop(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отображаем список фермеров без мгновенной покупки."""
    btns = []
    for farmer_type, price, inc, desc in FARMER_CONFIG:
        btns.append(
            InlineKeyboardButton(
                f"{farmer_type} ({format_num(price)}🪙)", callback_data=f"farmer_show_{farmer_type}"
            )
        )
    btns.append(InlineKeyboardButton("⬅️ Назад", callback_data="back"))
    kb = InlineKeyboardMarkup(chunk_buttons(btns, per_row=1))
    await edit_section(
        query,
        caption="👨‍🌾 Магазин фермеров – выберите фермера, чтобы увидеть детали.",
        image_key="farmers",
        reply_markup=kb,
    )


async def farmer_show_detail(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показ фото, описание и кнопку подтверждения покупки."""
    farmer_name = query.data.split("_", 2)[2]          # farmer_show_<name>
    rec = get_farmer(farmer_name)
    if not rec:
        await query.edit_message_caption(caption="❌ Фермера не найдено.")
        return
    _, price, inc, desc = rec
    photo_url = FARMER_IMAGES.get(farmer_name)
    text = (
        f"👨‍🌾 {farmer_name}\n"
        f"💸 Цена: {format_num(price)}🪙\n"
        f"📈 Доход: +{format_num(inc)}🪙/мин\n"
        f"📝 {desc}"
    )
    # Кнопка «Купить» → callback_data="farmer_buy_<name>"
    buy_btn = InlineKeyboardButton("✅ Купить", callback_data=f"farmer_buy_{farmer_name}")
    back_btn = InlineKeyboardButton("⬅️ Назад", callback_data="farmers_shop")
    kb = InlineKeyboardMarkup([[buy_btn], [back_btn]])
    if photo_url:
        await query.edit_message_media(
            media=InputMediaPhoto(media=photo_url, caption=text),
            reply_markup=kb,
        )
    else:
        await edit_section(query, caption=text, image_key="farmers", reply_markup=kb)


async def farmer_buy_confirm(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Фактическая покупка фермера после подтверждения."""
    farmer_name = query.data.split("_", 2)[2]          # farmer_buy_<name>
    rec = get_farmer(farmer_name)
    if not rec:
        await query.edit_message_caption(caption="❌ Фермера не найдено.")
        return
    _, price, inc, _ = rec
    uid = query.from_user.id
    user = get_user(uid)
    if user["coins"] < price:
        await edit_section(
            query,
            caption=f"❌ Недостаточно монет. Нужно {format_num(price)}🪙.",
            image_key="farmers",
        )
        return
    # Обновляем таблицу farmers
    cur.execute(
        "SELECT qty FROM farmers WHERE user_id = ? AND farmer_type = ?",
        (uid, farmer_name),
    )
    row = cur.fetchone()
    if row:
        new_qty = row["qty"] + 1
        _execute(
            "UPDATE farmers SET qty = ? WHERE user_id = ? AND farmer_type = ?",
            (new_qty, uid, farmer_name),
        )
    else:
        _execute(
            "INSERT INTO farmers (user_id, farmer_type, qty) VALUES (?,?,1)",
            (uid, farmer_name),
        )
    update_user(uid, coins=user["coins"] - price)
    log_user_action(uid, f"Купил фермера {farmer_name} за {price}🪙")
    # Отправляем фото, если есть
    photo_url = FARMER_IMAGES.get(farmer_name)
    if photo_url:
        await context.bot.send_photo(
            uid,
            photo=photo_url,
            caption=(
                f"✅ Вы купили фермера «{farmer_name}»!\n"
                f"💸 Стоимость: {format_num(price)}🪙\n"
                f"📈 Постоянный доход: +{format_num(inc)}🪙/мин."
            ),
        )
    else:
        await query.edit_message_caption(
            caption=(
                f"✅ Вы купили фермера «{farmer_name}»!\n"
                f"💸 Стоимость: {format_num(price)}🪙\n"
                f"📈 Постоянный доход: +{format_num(inc)}🪙/мин."
            ),
        )
    await query.edit_message_reply_markup(
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("⬅️ В магазин фермеров", callback_data="farmers_shop")]]
        )
    )


# ----------------------------------------------------------------------
#   Админ‑панель
# ----------------------------------------------------------------------
async def admin_panel(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(query.from_user.id):
        await edit_section(query, caption="❌ Доступ запрещён.", image_key="admin")
        return
    btns = [
        InlineKeyboardButton("🔄 Сброс топа", callback_data="admin_reset_top"),
        InlineKeyboardButton("🔁 Сброс всех аккаунтов", callback_data="admin_reset_all"),
        InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast"),
        InlineKeyboardButton("🕷️ Выдать паука‑секрета", callback_data="admin_give_spider"),
        InlineKeyboardButton("💰 Выдать монеты", callback_data="admin_set_coins"),
        InlineKeyboardButton("➕ Добавить монеты", callback_data="admin_add_coins"),
        InlineKeyboardButton("🧹 Обнулить X‑ферму", callback_data="admin_reset_xfarm"),
        InlineKeyboardButton("📜 Журнал действий", callback_data="admin_view_logs"),
        InlineKeyboardButton("🎟️ Создать промокод", callback_data="admin_create_promo"),
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
    if data == "admin_reset_top":
        _execute(
            "UPDATE users SET weekly_coins = 0, last_reset = ?, secret_spider = 0",
            (int(time.time()),),
        )
        await edit_section(query, caption="✅ Топ сброшен.", image_key="admin")
        return
    if data == "admin_reset_all":
        _execute("DELETE FROM users")
        _execute("DELETE FROM pet_last_fed")
        _execute("DELETE FROM decorations")
        _execute("DELETE FROM lottery")
        _execute("DELETE FROM boosters")
        _execute("DELETE FROM promo_codes")
        _execute("DELETE FROM farmers")
        await edit_section(query, caption="✅ Все аккаунты удалены.", image_key="admin")
        return
    if data == "admin_broadcast":
        context.user_data["awaiting_broadcast"] = True
        await edit_section(
            query,
            caption="✉️ Введите текст рассылки (будет отправлен всем пользователям).",
            image_key="admin",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⬅️ Отмена", callback_data="back")]]
            ),
        )
        return
    if data == "admin_give_spider":
        update_user(uid, secret_spider=1)
        await edit_section(query, caption="✅ Вы получили паука‑секрета.", image_key="admin")
        return
    if data == "admin_set_coins":
        context.user_data["awaiting_set_coins"] = True
        await edit_section(
            query,
            caption=(
                "💰 Введите user_id amount, пример:\n"
                "123456 5000000"
            ),
            image_key="admin",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⬅️ Отмена", callback_data="back")]]
            ),
        )
        return
    if data == "admin_add_coins":
        context.user_data["awaiting_add_coins"] = True
        await edit_section(
            query,
            caption=(
                "➕ Введите user_id amount, монеты будут прибавлены."
            ),
            image_key="admin",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⬅️ Отмена", callback_data="back")]]
            ),
        )
        return
    if data == "admin_reset_xfarm":
        # X‑ферма уже удалена из схемы, но оставим команду для совместимости.
        await edit_section(query, caption="✅ X‑ферма уже отсутствует.", image_key="admin")
        return
    if data == "admin_view_logs":
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
        await edit_section(
            query,
            caption=txt,
            image_key="logs",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⬅️ Назад", callback_data="admin")]]
            ),
        )
        return
    if data == "admin_create_promo":
        context.user_data["awaiting_create_promo"] = True
        await edit_section(
            query,
            caption=(
                "📝 Введите промокод в формате:\n"
                "CODE COINS [PET_FIELD PET_QTY] MAX_USES\n"
                "Пример без питомца: WELCOME 500 5\n"
                "Пример с питомцем: DRAGON1 1000 dragon 1 3"
            ),
            image_key="promo",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⬅️ Отмена", callback_data="back")]]
            ),
        )
        return
    if data == "admin_toggle_autumn":
        await toggle_autumn_event(query, context)
        return
    await edit_section(query, caption="❓ Неизвестная команда.", image_key="admin")


# ----------------------------------------------------------------------
#   Обработчик всех кнопок
# ----------------------------------------------------------------------
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
    # ------------------- Моя ферма -------------------
    if data == "farm":
        await farm_section(query, context)
        return
    # ------------------- Кормление -------------------
    if data == "feed_animal":
        await feed_animal_step(query, context)
        return
    if data.startswith("feed_type_"):
        await feed_type_chosen(query, context)
        return
    if data.startswith("feed_"):
        await feed_animal(query, context)
        return
    # ------------------- Продажа -------------------
    if data == "sell_animal":
        await sell_animal_step(query, context)
        return
    if data.startswith("sell_") and not data.startswith("sell_qty_"):
        await sell_animal_quantity(query, context)
        return
    if data.startswith("sell_qty_"):
        await sell_animal_confirm(query, context)
        return
    # ------------------- Улучшить базу -------------------
    if data == "upgrade_base":
        await upgrade_base(query, context)
        return
    # ------------------- Топ фермеров -------------------
    if data == "top":
        await top_farmers(query, context)
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
    # ------------------- Казино -------------------
    if data == "casino_info":
        await casino_info(query, context)
        return
    # ------------------- Магазин -------------------
    if data == "shop":
        await render_shop(query, context, page=0)
        return
    if data in ("shop_next", "shop_prev"):
        await shop_navigation(query, context)
        return
    if data.startswith("show_"):
        await show_animal(query, context)
        return
    if data.startswith("buy_qty_"):
        await buy_quantity(query, context)
        return
    if data.startswith("buy_confirm_"):
        await buy_confirm(query, context)
        return
    if data == "buy_feed":
        await buy_feed(query, context)
        return
    if data == "buy_autumn_feed":
        await buy_autumn_feed(query, context)
        return
    # ------------------- Фермеры -------------------
    if data == "farmers_shop":
        await farmers_shop(query, context)
        return
    if data.startswith("farmer_show_"):
        await farmer_show_detail(query, context)
        return
    if data.startswith("farmer_buy_"):
        await farmer_buy_confirm(query, context)
        return
    # ------------------- Осеннее событие -------------------
    if data == "autumn_event":
        await autumn_event_info(query, context)
        return
    if data == "admin_toggle_autumn":
        await toggle_autumn_event(query, context)
        return
    # ------------------- Промокоды -------------------
    if data == "promo":
        await promo_menu(query, context)
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


# ----------------------------------------------------------------------
#   /start (реферальный параметр)
# ----------------------------------------------------------------------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает /start, включая реферал."""
    txt = update.message.text if update.message else ""
    user = update.effective_user
    db_user = get_user(user.id)
    # Проверяем, не наступил ли новый сезон
    check_and_reset_season()
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


# ----------------------------------------------------------------------
#   Текстовые сообщения (разные команды)
# ----------------------------------------------------------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает все текстовые сообщения, не являющиеся командами."""
    user = update.effective_user
    txt = update.message.text if update.message else ""

    # ------------------- Рассылка (админ) -------------------
    if context.user_data.get("awaiting_broadcast"):
        for row in cur.execute("SELECT user_id FROM users"):
            try:
                await context.bot.send_message(row["user_id"], txt)
            except Exception:
                pass
        context.user_data["awaiting_broadcast"] = False
        await update.message.reply_text("✅ Рассылка отправлена.")
        return

    # ------------------- Выдача монет (админ) -------------------
    if context.user_data.get("awaiting_set_coins"):
        parts = txt.strip().split()
        if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
            await update.message.reply_text("❌ Формат: user_id amount")
            return
        target_id, amount = int(parts[0]), int(parts[1])
        update_user(target_id, coins=amount)
        context.user_data["awaiting_set_coins"] = False
        await update.message.reply_text(
            f"✅ Пользователю {target_id} установлено {format_num(amount)}🪙."
        )
        return

    if context.user_data.get("awaiting_add_coins"):
        parts = txt.strip().split()
        if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
            await update.message.reply_text("❌ Формат: user_id amount")
            return
        target_id, amount = int(parts[0]), int(parts[1])
        target_user = get_user(target_id)
        new_val = min(target_user["coins"] + amount, MAX_INT)
        update_user(target_id, coins=new_val)
        context.user_data["awaiting_add_coins"] = False
        await update.message.reply_text(
            f"✅ Пользователю {target_id} добавлено {format_num(amount)}🪙."
        )
        return

    # ------------------- Создание промокода (админ) -------------------
    if context.user_data.get("awaiting_create_promo"):
        parts = txt.strip().split()
        if len(parts) not in (3, 5):
            await update.message.reply_text(
                "❌ Формат: CODE COINS [PET_FIELD PET_QTY] MAX_USES"
            )
            return
        code = parts[0].upper()
        if not parts[1].isdigit():
            await update.message.reply_text("❌ COINS должно быть числом.")
            return
        coins = int(parts[1])
        pet_field = None
        pet_qty = 0
        max_uses = 1
        if len(parts) == 5:
            pet_field = parts[2]
            if not parts[3].isdigit():
                await update.message.reply_text("❌ PET_QTY должно быть числом.")
                return
            pet_qty = int(parts[3])
            if not parts[4].isdigit():
                await update.message.reply_text("❌ MAX_USES должно быть числом.")
                return
            max_uses = int(parts[4])
            if pet_field not in [f for f, *_ in ANIMAL_CONFIG]:
                await update.message.reply_text("❌ Неизвестный питомец.")
                return
        else:
            if not parts[2].isdigit():
                await update.message.reply_text("❌ MAX_USES должно быть числом.")
                return
            max_uses = int(parts[2])
        add_promo(code, coins, pet_field, pet_qty, max_uses)
        context.user_data["awaiting_create_promo"] = False
        await update.message.reply_text(
            f"✅ Промокод {code} создан. Монеты: {format_num(coins)}"
            + (f", Питомец: {pet_field} ×{pet_qty}" if pet_field else "")
            + f", Макс‑использований: {max_uses}"
        )
        return

    # ------------------- Промокод (пользователь) -------------------
    if context.user_data.get("awaiting_promo_input"):
        await handle_promo_input(update, context)
        return

    # ------------------- Казино -------------------
    if txt.lower().startswith("/ставка"):
        numbers = re.findall(r"\d+", txt)
        if not numbers:
            await update.message.reply_text("❌ Укажите сумму: /ставка 5000")
            return
        amount = int(numbers[-1])
        db_user = get_user(user.id)
        if amount < 100:
            await update.message.reply_text("❌ Минимальная ставка – 100🪙.")
            return
        if db_user["coins"] < amount:
            await update.message.reply_text("❌ Недостаточно монет.")
            return
        if random.random() < 0.3:
            win = amount
            update_user(
                user.id,
                coins=db_user["coins"] + win,
                weekly_coins=db_user["weekly_coins"] + win,
                reputation=db_user["reputation"] + 1,
            )
            log_user_action(user.id, f"Выиграл в казино {win}🪙")
            await update.message.reply_text(
                f"🎉 Вы выиграли! Ставка {format_num(amount)}🪙, выигрыш +{format_num(win)}🪙."
            )
        else:
            update_user(
                user.id,
                coins=db_user["coins"] - amount,
                weekly_coins=db_user["weekly_coins"] - amount,
                reputation=db_user["reputation"] - 1,
            )
            log_user_action(user.id, f"Проиграл в казино {amount}🪙")
            await update.message.reply_text(f"💔 Вы проиграли {format_num(amount)}🪙.")
        return

    # ------------------- Декорации фермы -------------------
    if txt.lower().startswith("/декор"):
        parts = txt.strip().split()
        if len(parts) != 2:
            await update.message.reply_text("❌ Формат: /декор <тип>")
            return
        deco_type = parts[1].lower()
        cur.execute(
            "SELECT level FROM decorations WHERE user_id = ? AND decor_type = ?",
            (user.id, deco_type),
        )
        row = cur.fetchone()
        cur_level = row["level"] if row else 0
        cost = 5000 * (cur_level + 1)
        if get_user(user.id)["coins"] < cost:
            await update.message.reply_text(
                f"❌ Недостаточно монет. Нужно {format_num(cost)}🪙."
            )
            return
        if row:
            _execute(
                "UPDATE decorations SET level = ? WHERE user_id = ? AND decor_type = ?",
                (cur_level + 1, user.id, deco_type),
            )
        else:
            _execute(
                "INSERT INTO decorations (user_id, decor_type, level) VALUES (?,?,1)",
                (user.id, deco_type),
            )
        # Бонус к доходу: +1% за каждый уровень
        bonus = int(0.01 * (cur_level + 1) * get_user(user.id)["custom_income"])
        update_user(user.id, custom_income=get_user(user.id)["custom_income"] + bonus)
        await update.message.reply_text(
            f"✅ Декорация «{deco_type}» улучшена до уровня {cur_level + 1}. "
            f"Получен бонус +{format_num(bonus)}🪙 к доходу."
        )
        return

    # ------------------- Лотерея -------------------
    if txt.lower().startswith("/лотерея"):
        parts = txt.strip().split()
        if len(parts) < 2:
            await update.message.reply_text(
                "❌ Формат: /лотерея купить <кол-во> | /лотерея сыграть"
            )
            return
        action = parts[1].lower()
        if action == "купить":
            if len(parts) != 3 or not parts[2].isdigit():
                await update.message.reply_text("❌ Укажите количество.")
                return
            qty = int(parts[2])
            price = 200 * qty
            u = get_user(user.id)
            if u["coins"] < price:
                await update.message.reply_text(
                    f"❌ Недостаточно монет. Нужно {format_num(price)}🪙."
                )
                return
            update_user(user.id, coins=u["coins"] - price)
            cur.execute(
                "INSERT INTO lottery (user_id, tickets) VALUES (?,?) "
                "ON CONFLICT(user_id) DO UPDATE SET tickets = tickets + excluded.tickets",
                (user.id, qty),
            )
            conn.commit()
            await update.message.reply_text(f"✅ Куплено {qty} лотерейных билетов.")
            return
        if action == "сыграть":
            cur.execute("SELECT tickets FROM lottery WHERE user_id = ?", (user.id,))
            row = cur.fetchone()
            if not row or row["tickets"] <= 0:
                await update.message.reply_text("❌ У вас нет билетов.")
                return
            roll = random.random()
            win = 0
            if roll < 0.10:
                win = 10_000
            elif roll < 0.15:
                win = 2_000
            cur.execute(
                "UPDATE lottery SET tickets = tickets - 1 WHERE user_id = ?",
                (user.id,),
            )
            conn.commit()
            if win:
                update_user(user.id, coins=get_user(user.id)["coins"] + win)
                await update.message.reply_text(
                    f"🎉 Вы выиграли {format_num(win)}🪙 в лотерее!"
                )
            else:
                await update.message.reply_text("💔 Вы не выиграли в этом раунде.")
            return

    # ------------------- Ускорители -------------------
    if txt.lower().startswith("/ускоритель"):
        parts = txt.strip().split()
        if len(parts) != 4 or parts[1].lower() != "купить":
            await update.message.reply_text(
                "❌ Формат: /ускоритель купить <множитель> <сек>"
            )
            return
        try:
            mult = float(parts[2])
            secs = int(parts[3])
        except ValueError:
            await update.message.reply_text("❌ Неверные параметры.")
            return
        if mult <= 1.0 or secs <= 0:
            await update.message.reply_text("❌ Множитель >1 и время >0.")
            return
        price = int(5_000 * mult * secs / 60)   # простая формула цены
        u = get_user(user.id)
        if u["coins"] < price:
            await update.message.reply_text(
                f"❌ Недостаточно монет. Нужно {format_num(price)}🪙."
            )
            return
        cur.execute(
            "SELECT multiplier, expires FROM boosters WHERE user_id = ?",
            (user.id,),
        )
        row = cur.fetchone()
        now = int(time.time())
        if row:
            cur_multiplier = row["multiplier"]
            cur_expires = row["expires"]
            new_multiplier = max(cur_multiplier, mult)
            new_expires = max(cur_expires, now + secs)
            _execute(
                "UPDATE boosters SET multiplier = ?, expires = ? WHERE user_id = ?",
                (new_multiplier, new_expires, user.id),
            )
        else:
            _execute(
                "INSERT INTO boosters (user_id, multiplier, expires) VALUES (?,?,?)",
                (user.id, mult, now + secs),
            )
        update_user(user.id, coins=u["coins"] - price)
        await update.message.reply_text(
            f"✅ Ускоритель ×{mult:.1f} активен на {secs}сек. Стоимость {format_num(price)}🪙."
        )
        return

    # ------------------- Трейд (упрощённый пример) -------------------
    if txt.lower().startswith("/trade"):
        await start_trade(query, context)   # функция start_trade реализована ниже
        return

    # ------------------- Любой другой текст -------------------
    # Игнорируем неизвестные сообщения
    return


# ----------------------------------------------------------------------
#   Трейд (упрощённый пример)
# ----------------------------------------------------------------------
async def start_trade(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Запускает простую схему трейда – запрос получателя."""
    context.user_data["trade_state"] = {"step": 1}
    await edit_section(
        query,
        caption="🤝 Трейд: введите ID получателя (user_id).",
        image_key="farm",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("⬅️ Назад", callback_data="back")]]
        ),
    )


async def handle_trade_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает ввод данных в процессе трейда."""
    txt = update.message.text.strip()
    state = context.user_data.get("trade_state")
    if not state:
        return
    uid = update.effective_user.id
    user = get_user(uid)
    if state["step"] == 1:
        if not txt.isdigit():
            await update.message.reply_text("❌ Нужно ввести числовой ID.")
            return
        state["target_id"] = int(txt)
        state["step"] = 2
        await update.message.reply_text("💰 Введите количество монет для отправки:")
        return
    if state["step"] == 2:
        if not txt.isdigit():
            await update.message.reply_text("❌ Введите число.")
            return
        amount = int(txt)
        if amount <= 0 or user["coins"] < amount:
            await update.message.reply_text("❌ Недостаточно монет.")
            return
        target_id = state["target_id"]
        target_user = get_user(target_id)
        update_user(uid, coins=user["coins"] - amount)
        update_user(target_id, coins=target_user["coins"] + amount)
        log_user_action(uid, f"Трейд: отправил {amount}🪙 пользователю {target_id}")
        await update.message.reply_text(
            f"✅ Трейд завершён! Перевод {format_num(amount)}🪙 пользователю {target_id}."
        )
        # Очистим состояние
        context.user_data.pop("trade_state", None)


# ----------------------------------------------------------------------
#   /pets – список всех питомцев (пагинация)
# ----------------------------------------------------------------------
async def pets_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await render_pets_command(update.message, context, page=0)


async def pets_nav(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data
    cur_page = context.user_data.get("pets_page", 0)
    if data == "pets_next":
        await render_pets_callback(query, context, page=cur_page + 1)
    elif data == "pets_prev":
        await render_pets_callback(query, context, page=max(0, cur_page - 1))


async def render_pets_command(message, context: ContextTypes.DEFAULT_TYPE, page: int = 0) -> None:
    items, total_pages = paginate_items(ANIMAL_CONFIG, page)
    lines = []
    for _, inc, emoji, name, _, price, desc in items:
        lines.append(
            f"{emoji} {name}\nДоход: {inc}🪙/мин, цена: {format_num(price)}🪙\n{desc}"
        )
    text = "\n\n".join(lines)
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⏪ Пред.", callback_data="pets_prev"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("След. ⏩", callback_data="pets_next"))
    nav.append(InlineKeyboardButton("⬅️ Главное меню", callback_data="back"))
    kb = InlineKeyboardMarkup([nav])
    await message.reply_photo(
        MAIN_MENU_IMG,
        caption=f"📜 Питомцы – страница {page + 1}/{total_pages}\n\n{text}",
        reply_markup=kb,
    )
    context.user_data["pets_page"] = page


async def render_pets_callback(query, context: ContextTypes.DEFAULT_TYPE, page: int = 0) -> None:
    items, total_pages = paginate_items(ANIMAL_CONFIG, page)
    lines = []
    for _, inc, emoji, name, _, price, desc in items:
        lines.append(
            f"{emoji} {name}\nДоход: {inc}🪙/мин, цена: {format_num(price)}🪙\n{desc}"
        )
    text = "\n\n".join(lines)
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⏪ Пред.", callback_data="pets_prev"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("След. ⏩", callback_data="pets_next"))
    nav.append(InlineKeyboardButton("⬅️ Главное меню", callback_data="back"))
    kb = InlineKeyboardMarkup([nav])
    await query.edit_message_media(
        media=InputMediaPhoto(media=MAIN_MENU_IMG, caption=f"📜 Питомцы – страница {page + 1}/{total_pages}\n\n{text}"),
        reply_markup=kb,
    )
    context.user_data["pets_page"] = page


# ----------------------------------------------------------------------
#   Групповые команды /top и /stats
# ----------------------------------------------------------------------
async def top_group_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Топ‑5 фермеров по weekly_coins (доступно в группах)."""
    cur.execute(
        "SELECT username, weekly_coins, user_id FROM users ORDER BY weekly_coins DESC LIMIT 5"
    )
    top5 = cur.fetchall()
    if not top5:
        text = "⚡ Пока нет игроков в базе."
    else:
        text = "🏆 Топ фермеров (недельный доход)\n━━━━━━━━━━━━\n"
        for i, row in enumerate(top5, 1):
            name = row["username"] or f"Пользователь {row['user_id']}"
            text += f"{i}. {name} — {format_num(row['weekly_coins'])}🪙\n"
    await update.message.reply_text(text)


async def stat_group_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Статистика того, кто ввёл команду в группе."""
    user = update.effective_user
    db_user = get_user(user.id)
    income_min = calculate_income_per_min(db_user)
    left, season_number = get_season_info()
    h, r = divmod(left, 3600)
    m = r // 60
    text = (
        f"📊 Статистика {user.full_name or user.username or 'Игрока'}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 ID: {db_user['user_id']}\n"
        f"💰 Монеты: {format_num(db_user['coins'])}\n"
        f"💰 Доход за минуту: {format_num(income_min)}🪙\n"
        f"🏗️ База: уровень {db_user['base_level']} (лимит: {db_user['pet_limit']})\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🎟️ Билетов: {db_user['tickets']}\n"
        f"💬 Репутация: {db_user['reputation']}\n"
        f"⚡ Титул: {get_status(db_user['coins'])}\n"
        f"🕷️ Паук‑секрет: {'Да' if db_user['secret_spider'] else 'Нет'}\n"
        f"🔁 Перерождений: {db_user.get('rebirths', 0)}\n"
        f"⏳ До конца сезона №{season_number}: {h}ч {m}м\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    await update.message.reply_text(text)


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
    ensure_global_settings_columns()
    ensure_promo_columns()          # <-- важный миграционный шаг
    if args.migrate:
        log.info("Миграция завершена, колонки добавлены.")
        return
    add_admins()
    app = ApplicationBuilder().token(TOKEN).build()
    # Основные команды
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("pets", pets_command))
    # Групповые команды
    app.add_handler(
        CommandHandler("top", top_group_handler, filters.ChatType.GROUPS)
    )
    app.add_handler(
        CommandHandler("stats", stat_group_handler, filters.ChatType.GROUPS)
    )
    # Альтернативные русские алиасы
    app.add_handler(
        MessageHandler(
            filters.ChatType.GROUPS & filters.Regex(r"^/топ(@\w+)?$"),
            lambda u, c: top_group_handler(u, c),
        )
    )
    app.add_handler(
        MessageHandler(
            filters.ChatType.GROUPS & filters.Regex(r"^/стата(@\w+)?$"),
            lambda u, c: stat_group_handler(u, c),
        )
    )
    # Обработчики
    app.add_handler(CallbackQueryHandler(button))
    # Навигация в списке питомцев
    app.add_handler(CallbackQueryHandler(pets_nav, pattern="^pets_"))
    # Текстовые сообщения
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    # Фоновые задачи
    app.job_queue.run_repeating(auto_collect, interval=60, first=10)          # доход каждые 1 мин
    app.job_queue.run_repeating(check_hunger, interval=300, first=30)        # проверка голода
    app.job_queue.run_repeating(
        lambda _: check_and_reset_season(),
        interval=86400,
        first=5,
    )                  # проверка сезона
    app.run_polling()


if __name__ == "__main__":
    main()