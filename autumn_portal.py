"""
Осенний портал - модуль для осеннего обновления с играми, магазином и ежедневными наградами
"""

import time
import random
import sqlite3
from typing import List, Dict, Any, Tuple
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

# Импорты из основного файла
from main import (
    _execute, cur, edit_section, chunk_buttons, format_num, 
    get_user, update_user, log_user_action, AUTUMN_FOOD_PRICE,
    AUTUMN_EVENT_IMG, IMAGES
)


# Осенние игры
AUTUMN_GAMES = [
    {
        "name": "🍂 Угадай лист",
        "description": "Угадайте цвет осеннего листа",
        "cost": 1000,
        "reward": 2000,
        "callback": "autumn_game_leaf"
    },
    {
        "name": "🎃 Тыквенная охота",
        "description": "Найдите спрятанную тыкву",
        "cost": 1500,
        "reward": 3000,
        "callback": "autumn_game_pumpkin"
    },
    {
        "name": "🍄 Грибная корзина",
        "description": "Соберите грибы в корзину",
        "cost": 2000,
        "reward": 4000,
        "callback": "autumn_game_mushroom"
    },
    {
        "name": "🌰 Ореховая загадка",
        "description": "Разгадайте загадку об орехах",
        "cost": 2500,
        "reward": 5000,
        "callback": "autumn_game_nut"
    },
    {
        "name": "🍁 Листопад",
        "description": "Поймайте падающие листья",
        "cost": 3000,
        "reward": 6000,
        "callback": "autumn_game_leaves"
    },
    {
        "name": "🦌 Оленья тропа",
        "description": "Помогите оленю найти путь",
        "cost": 4000,
        "reward": 8000,
        "callback": "autumn_game_deer"
    },
    {
        "name": "🌾 Урожай зерна",
        "description": "Соберите урожай пшеницы",
        "cost": 5000,
        "reward": 10000,
        "callback": "autumn_game_wheat"
    },
    {
        "name": "🍎 Яблочный сад",
        "description": "Соберите спелые яблоки",
        "cost": 6000,
        "reward": 12000,
        "callback": "autumn_game_apple"
    },
    {
        "name": "🌰 Беличья охота",
        "description": "Помогите белке найти орехи",
        "cost": 7000,
        "reward": 14000,
        "callback": "autumn_game_squirrel"
    },
    {
        "name": "🍂 Осенний ветер",
        "description": "Угадайте направление ветра",
        "cost": 8000,
        "reward": 16000,
        "callback": "autumn_game_wind"
    },
    {
        "name": "🦅 Орлиный полет",
        "description": "Помогите орлу найти добычу",
        "cost": 10000,
        "reward": 20000,
        "callback": "autumn_game_eagle"
    },
    {
        "name": "🌙 Осенняя ночь",
        "description": "Найдите созвездия на небе",
        "cost": 12000,
        "reward": 24000,
        "callback": "autumn_game_stars"
    }
]

# Осенний магазин
AUTUMN_SHOP = [
    {
        "name": "🍂 Осенний корм",
        "description": "Специальный корм для осенних питомцев",
        "price": 1000,
        "type": "feed",
        "callback": "buy_autumn_feed"
    },
    {
        "name": "🎃 Тыквенная маска",
        "description": "Маска для Хэллоуина (+5% к доходу)",
        "price": 5000,
        "type": "mask",
        "callback": "buy_autumn_mask"
    },
    {
        "name": "🍄 Грибной суп",
        "description": "Восстанавливает здоровье питомцев",
        "price": 3000,
        "type": "soup",
        "callback": "buy_autumn_soup"
    },
    {
        "name": "🌰 Ореховый торт",
        "description": "Увеличивает счастье питомцев",
        "price": 4000,
        "type": "cake",
        "callback": "buy_autumn_cake"
    },
    {
        "name": "🍁 Осенний венок",
        "description": "Украшение для фермы (+3% к доходу)",
        "price": 7000,
        "type": "wreath",
        "callback": "buy_autumn_wreath"
    },
    {
        "name": "🦌 Рога оленя",
        "description": "Редкий аксессуар (+10% к доходу)",
        "price": 15000,
        "type": "antlers",
        "callback": "buy_autumn_antlers"
    }
]


async def autumn_portal_menu(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Главное меню осеннего портала."""
    uid = query.from_user.id
    user = get_user(uid)
    
    # Проверяем активность осеннего события
    cur.execute("SELECT autumn_event_active FROM global_settings WHERE id = 1")
    active = cur.fetchone()["autumn_event_active"]
    
    if not active:
        await edit_section(
            query,
            caption="🍂 Осеннее событие неактивно. Обратитесь к администратору.",
            image_key="autumn",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⬅️ Назад", callback_data="back")]]
            ),
        )
        return
    
    text = (
        f"🍂 Осенний портал\n\n"
        f"Добро пожаловать в осеннее приключение!\n"
        f"У вас {user['autumn_feed']} осеннего корма\n\n"
        f"Выберите раздел:"
    )
    
    btns = [
        InlineKeyboardButton("🎮 Осенние игры", callback_data="autumn_games"),
        InlineKeyboardButton("🛒 Осенний магазин", callback_data="autumn_shop"),
        InlineKeyboardButton("🎁 Ежедневные награды", callback_data="autumn_daily"),
        InlineKeyboardButton("🔄 Обмен монет", callback_data="autumn_exchange"),
        InlineKeyboardButton("📊 Статистика", callback_data="autumn_stats"),
        InlineKeyboardButton("⬅️ Назад", callback_data="back"),
    ]
    
    await edit_section(
        query,
        caption=text,
        image_key="autumn",
        reply_markup=InlineKeyboardMarkup(chunk_buttons(btns, per_row=2)),
    )


async def autumn_games_menu(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Меню осенних игр."""
    uid = query.from_user.id
    user = get_user(uid)
    
    text = "🎮 Осенние игры\n\nВыберите игру:"
    
    btns = []
    for game in AUTUMN_GAMES:
        btns.append(
            InlineKeyboardButton(
                f"{game['name']} ({format_num(game['cost'])}🪙)",
                callback_data=game['callback']
            )
        )
    
    btns.append(InlineKeyboardButton("⬅️ Назад", callback_data="autumn_portal"))
    
    await edit_section(
        query,
        caption=text,
        image_key="autumn",
        reply_markup=InlineKeyboardMarkup(chunk_buttons(btns, per_row=1)),
    )


async def autumn_game_leaf(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Игра 'Угадай лист'."""
    uid = query.from_user.id
    user = get_user(uid)
    
    if user["coins"] < 1000:
        await edit_section(
            query,
            caption="❌ Недостаточно монет. Нужно 1000🪙.",
            image_key="autumn",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⬅️ Назад", callback_data="autumn_games")]]
            ),
        )
        return
    
    # Игра: угадать цвет листа
    colors = ["красный", "желтый", "оранжевый", "коричневый"]
    correct_color = random.choice(colors)
    
    text = (
        f"🍂 Угадай лист\n\n"
        f"Какого цвета осенний лист?\n"
        f"Варианты: {', '.join(colors)}\n\n"
        f"Введите цвет:"
    )
    
    context.user_data["autumn_game"] = {
        "type": "leaf",
        "correct": correct_color,
        "cost": 1000,
        "reward": 2000
    }
    
    await edit_section(
        query,
        caption=text,
        image_key="autumn",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("⬅️ Отмена", callback_data="autumn_games")]]
        ),
    )


async def autumn_game_pumpkin(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Игра 'Тыквенная охота'."""
    uid = query.from_user.id
    user = get_user(uid)
    
    if user["coins"] < 1500:
        await edit_section(
            query,
            caption="❌ Недостаточно монет. Нужно 1500🪙.",
            image_key="autumn",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⬅️ Назад", callback_data="autumn_games")]]
            ),
        )
        return
    
    # Игра: найти тыкву
    positions = ["лес", "сад", "поле", "дом"]
    correct_position = random.choice(positions)
    
    text = (
        f"🎃 Тыквенная охота\n\n"
        f"Где спрятана тыква?\n"
        f"Варианты: {', '.join(positions)}\n\n"
        f"Введите место:"
    )
    
    context.user_data["autumn_game"] = {
        "type": "pumpkin",
        "correct": correct_position,
        "cost": 1500,
        "reward": 3000
    }
    
    await edit_section(
        query,
        caption=text,
        image_key="autumn",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("⬅️ Отмена", callback_data="autumn_games")]]
        ),
    )


async def autumn_game_mushroom(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Игра 'Грибная корзина'."""
    uid = query.from_user.id
    user = get_user(uid)
    
    if user["coins"] < 2000:
        await edit_section(
            query,
            caption="❌ Недостаточно монет. Нужно 2000🪙.",
            image_key="autumn",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⬅️ Назад", callback_data="autumn_games")]]
            ),
        )
        return
    
    # Игра: собрать грибы
    mushrooms = ["белый", "подберезовик", "лисичка", "опенок"]
    correct_mushroom = random.choice(mushrooms)
    
    text = (
        f"🍄 Грибная корзина\n\n"
        f"Какой гриб нужно собрать?\n"
        f"Варианты: {', '.join(mushrooms)}\n\n"
        f"Введите гриб:"
    )
    
    context.user_data["autumn_game"] = {
        "type": "mushroom",
        "correct": correct_mushroom,
        "cost": 2000,
        "reward": 4000
    }
    
    await edit_section(
        query,
        caption=text,
        image_key="autumn",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("⬅️ Отмена", callback_data="autumn_games")]]
        ),
    )


async def autumn_game_nut(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Игра 'Ореховая загадка'."""
    uid = query.from_user.id
    user = get_user(uid)
    
    if user["coins"] < 2500:
        await edit_section(
            query,
            caption="❌ Недостаточно монет. Нужно 2500🪙.",
            image_key="autumn",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⬅️ Назад", callback_data="autumn_games")]]
            ),
        )
        return
    
    # Игра: загадка об орехах
    riddles = [
        ("Что растет на дубе?", "желудь"),
        ("Какой орех самый большой?", "кокос"),
        ("Что едят белки?", "орехи"),
        ("Какой орех зеленый?", "фисташка")
    ]
    
    riddle, answer = random.choice(riddles)
    
    text = (
        f"🌰 Ореховая загадка\n\n"
        f"Загадка: {riddle}\n\n"
        f"Введите ответ:"
    )
    
    context.user_data["autumn_game"] = {
        "type": "nut",
        "correct": answer,
        "cost": 2500,
        "reward": 5000
    }
    
    await edit_section(
        query,
        caption=text,
        image_key="autumn",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("⬅️ Отмена", callback_data="autumn_games")]]
        ),
    )


async def autumn_game_leaves(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Игра 'Листопад'."""
    uid = query.from_user.id
    user = get_user(uid)
    
    if user["coins"] < 3000:
        await edit_section(
            query,
            caption="❌ Недостаточно монет. Нужно 3000🪙.",
            image_key="autumn",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⬅️ Назад", callback_data="autumn_games")]]
            ),
        )
        return
    
    # Игра: поймать листья
    leaves = ["кленовый", "дубовый", "березовый", "рябиновый"]
    correct_leaf = random.choice(leaves)
    
    text = (
        f"🍁 Листопад\n\n"
        f"Какой лист нужно поймать?\n"
        f"Варианты: {', '.join(leaves)}\n\n"
        f"Введите лист:"
    )
    
    context.user_data["autumn_game"] = {
        "type": "leaves",
        "correct": correct_leaf,
        "cost": 3000,
        "reward": 6000
    }
    
    await edit_section(
        query,
        caption=text,
        image_key="autumn",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("⬅️ Отмена", callback_data="autumn_games")]]
        ),
    )


async def autumn_game_deer(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Игра 'Оленья тропа'."""
    uid = query.from_user.id
    user = get_user(uid)
    
    if user["coins"] < 4000:
        await edit_section(
            query,
            caption="❌ Недостаточно монет. Нужно 4000🪙.",
            image_key="autumn",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⬅️ Назад", callback_data="autumn_games")]]
            ),
        )
        return
    
    # Игра: помочь оленю
    paths = ["лесная", "горная", "речная", "луговая"]
    correct_path = random.choice(paths)
    
    text = (
        f"🦌 Оленья тропа\n\n"
        f"По какой тропе должен идти олень?\n"
        f"Варианты: {', '.join(paths)}\n\n"
        f"Введите тропу:"
    )
    
    context.user_data["autumn_game"] = {
        "type": "deer",
        "correct": correct_path,
        "cost": 4000,
        "reward": 8000
    }
    
    await edit_section(
        query,
        caption=text,
        image_key="autumn",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("⬅️ Отмена", callback_data="autumn_games")]]
        ),
    )


async def autumn_shop_menu(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Меню осеннего магазина."""
    uid = query.from_user.id
    user = get_user(uid)
    
    text = "🛒 Осенний магазин\n\nВыберите товар:"
    
    btns = []
    for item in AUTUMN_SHOP:
        btns.append(
            InlineKeyboardButton(
                f"{item['name']} ({format_num(item['price'])}🪙)",
                callback_data=item['callback']
            )
        )
    
    btns.append(InlineKeyboardButton("⬅️ Назад", callback_data="autumn_portal"))
    
    await edit_section(
        query,
        caption=text,
        image_key="autumn",
        reply_markup=InlineKeyboardMarkup(chunk_buttons(btns, per_row=1)),
    )


async def autumn_daily_section(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ежедневные награды осеннего события."""
    uid = query.from_user.id
    user = get_user(uid)
    
    # Исправляем ошибку с sqlite3.Row - используем try/except
    try:
        last_daily = user["last_autumn_daily"]
    except (KeyError, IndexError):
        last_daily = 0
    
    now = int(time.time())
    daily_cooldown = 86400  # 24 часа
    
    if now - last_daily < daily_cooldown:
        left = daily_cooldown - (now - last_daily)
        hours = left // 3600
        minutes = (left % 3600) // 60
        
        await edit_section(
            query,
            caption=f"🎁 Ежедневные награды\n\n⏰ Следующая награда через {hours}ч {minutes}м",
            image_key="autumn",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⬅️ Назад", callback_data="autumn_portal")]]
            ),
        )
        return
    
    # Выдаем награду
    reward_coins = random.randint(1000, 5000)
    reward_feed = random.randint(1, 3)
    
    update_user(
        uid,
        coins=user["coins"] + reward_coins,
        autumn_feed=user["autumn_feed"] + reward_feed,
        last_autumn_daily=now
    )
    
    log_user_action(uid, f"Получил ежедневную осеннюю награду: {reward_coins}🪙 + {reward_feed} корма")
    
    await edit_section(
        query,
        caption=(
            f"🎁 Ежедневная награда получена!\n\n"
            f"💰 Монеты: +{format_num(reward_coins)}🪙\n"
            f"🍂 Осенний корм: +{reward_feed}\n\n"
            f"Приходите завтра за новой наградой!"
        ),
        image_key="autumn",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("⬅️ Назад", callback_data="autumn_portal")]]
        ),
    )


async def autumn_exchange(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обмен монет на осенние монеты."""
    uid = query.from_user.id
    user = get_user(uid)
    
    # Получаем осенние монеты, если поле не существует, используем 0
    try:
        autumn_coins = user["autumn_coins"]
    except (KeyError, IndexError):
        autumn_coins = 0
    
    text = (
        f"🔄 Обмен монет\n\n"
        f"У вас: {format_num(user['coins'])}🪙\n"
        f"Осенних монет: {autumn_coins}🍂\n\n"
        f"Курс обмена: 1🪙 = 1 осенняя монета\n"
        f"Введите количество монет для обмена:"
    )
    
    context.user_data["awaiting_autumn_exchange"] = True
    
    await edit_section(
        query,
        caption=text,
        image_key="autumn",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("⬅️ Отмена", callback_data="autumn_portal")]]
        ),
    )


async def autumn_stats(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Статистика осеннего события."""
    uid = query.from_user.id
    user = get_user(uid)
    
    # Получаем осенние монеты
    try:
        autumn_coins = user["autumn_coins"]
    except (KeyError, IndexError):
        autumn_coins = 0
    
    # Получаем статистику игрока
    cur.execute("SELECT COUNT(*) as count FROM admin_logs WHERE user_id = ? AND action LIKE '%осенн%'", (uid,))
    autumn_actions = cur.fetchone()["count"]
    
    text = (
        f"📊 Статистика осеннего события\n\n"
        f"🍂 Осенний корм: {user['autumn_feed']}\n"
        f"🍂 Осенние монеты: {autumn_coins}\n"
        f"💰 Обычные монеты: {format_num(user['coins'])}\n"
        f"🎮 Осенних действий: {autumn_actions}\n\n"
        f"Последняя ежедневная награда: "
    )
    
    try:
        if user["last_autumn_daily"]:
            last_daily = time.strftime("%d.%m.%Y %H:%M", time.localtime(user["last_autumn_daily"]))
            text += last_daily
        else:
            text += "Никогда"
    except (KeyError, IndexError):
        text += "Никогда"
    
    await edit_section(
        query,
        caption=text,
        image_key="autumn",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("⬅️ Назад", callback_data="autumn_portal")]]
        ),
    )


async def handle_autumn_game_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка ввода в осенних играх."""
    if not context.user_data.get("autumn_game"):
        return
    
    game_data = context.user_data["autumn_game"]
    user_input = update.message.text.strip().lower()
    correct_answer = game_data["correct"].lower()
    
    uid = update.effective_user.id
    user = get_user(uid)
    
    if user_input == correct_answer:
        # Выигрыш
        reward = game_data["reward"]
        update_user(uid, coins=user["coins"] + reward)
        log_user_action(uid, f"Выиграл в осенней игре {game_data['type']}: {reward}🪙")
        
        await update.message.reply_text(
            f"🎉 Правильно! Вы выиграли {format_num(reward)}🪙!"
        )
    else:
        # Проигрыш
        cost = game_data["cost"]
        update_user(uid, coins=user["coins"] - cost)
        log_user_action(uid, f"Проиграл в осенней игре {game_data['type']}: {cost}🪙")
        
        await update.message.reply_text(
            f"💔 Неправильно! Правильный ответ: {game_data['correct']}\n"
            f"Вы потеряли {format_num(cost)}🪙"
        )
    
    context.user_data.pop("autumn_game", None)


async def handle_autumn_exchange_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка обмена монет."""
    if not context.user_data.get("awaiting_autumn_exchange"):
        return
    
    txt = update.message.text.strip()
    if not txt.isdigit():
        await update.message.reply_text("❌ Введите число.")
        return
    
    amount = int(txt)
    uid = update.effective_user.id
    user = get_user(uid)
    
    if amount <= 0:
        await update.message.reply_text("❌ Количество должно быть больше 0.")
        return
    
    if user["coins"] < amount:
        await update.message.reply_text("❌ Недостаточно монет.")
        return
    
    # Получаем текущие осенние монеты
    try:
        current_autumn_coins = user["autumn_coins"]
    except (KeyError, IndexError):
        current_autumn_coins = 0
    
    update_user(
        uid,
        coins=user["coins"] - amount,
        autumn_coins=current_autumn_coins + amount
    )
    
    log_user_action(uid, f"Обменял {amount}🪙 на осенние монеты")
    
    await update.message.reply_text(
        f"✅ Обмен завершен! Получено {amount} осенних монет🍂."
    )
    
    context.user_data["awaiting_autumn_exchange"] = False


# Функции для покупки товаров в осеннем магазине
async def buy_autumn_feed(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Покупка осеннего корма."""
    uid = query.from_user.id
    user = get_user(uid)
    
    # Получаем осенние монеты
    try:
        autumn_coins = user["autumn_coins"]
    except (KeyError, IndexError):
        autumn_coins = 0
    
    # Показываем варианты оплаты
    text = (
        f"🍂 Осенний корм\n\n"
        f"Стоимость: {format_num(AUTUMN_FOOD_PRICE)}🪙 или {AUTUMN_FOOD_PRICE}🍂\n\n"
        f"У вас:\n"
        f"💰 Обычные монеты: {format_num(user['coins'])}🪙\n"
        f"🍂 Осенние монеты: {autumn_coins}🍂\n\n"
        f"Выберите способ оплаты:"
    )
    
    btns = []
    if user["coins"] >= AUTUMN_FOOD_PRICE:
        btns.append(InlineKeyboardButton("💰 За обычные монеты", callback_data="buy_autumn_feed_normal"))
    if autumn_coins >= AUTUMN_FOOD_PRICE:
        btns.append(InlineKeyboardButton("🍂 За осенние монеты", callback_data="buy_autumn_feed_autumn"))
    
    btns.append(InlineKeyboardButton("⬅️ Назад", callback_data="autumn_shop"))
    
    await edit_section(
        query,
        caption=text,
        image_key="autumn",
        reply_markup=InlineKeyboardMarkup(chunk_buttons(btns, per_row=1)),
    )


async def buy_autumn_feed_normal(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Покупка осеннего корма за обычные монеты."""
    uid = query.from_user.id
    user = get_user(uid)
    
    if user["coins"] < AUTUMN_FOOD_PRICE:
        await edit_section(
            query,
            caption=f"❌ Недостаточно монет. Нужно {format_num(AUTUMN_FOOD_PRICE)}🪙.",
            image_key="autumn",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⬅️ Назад", callback_data="autumn_shop")]]
            ),
        )
        return
    
    update_user(
        uid,
        coins=user["coins"] - AUTUMN_FOOD_PRICE,
        autumn_feed=user["autumn_feed"] + 1,
        weekly_coins=user["weekly_coins"] + AUTUMN_FOOD_PRICE,
    )
    
    log_user_action(uid, f"Купил осенний корм за {AUTUMN_FOOD_PRICE}🪙")
    
    await edit_section(
        query,
        caption=f"✅ +1 осенний корм за {format_num(AUTUMN_FOOD_PRICE)}🪙.",
        image_key="autumn",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("⬅️ Назад", callback_data="autumn_shop")]]
        ),
    )


async def buy_autumn_feed_autumn(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Покупка осеннего корма за осенние монеты."""
    uid = query.from_user.id
    user = get_user(uid)
    
    # Получаем осенние монеты
    try:
        autumn_coins = user["autumn_coins"]
    except (KeyError, IndexError):
        autumn_coins = 0
    
    if autumn_coins < AUTUMN_FOOD_PRICE:
        await edit_section(
            query,
            caption=f"❌ Недостаточно осенних монет. Нужно {AUTUMN_FOOD_PRICE}🍂.",
            image_key="autumn",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⬅️ Назад", callback_data="autumn_shop")]]
            ),
        )
        return
    
    update_user(
        uid,
        autumn_coins=autumn_coins - AUTUMN_FOOD_PRICE,
        autumn_feed=user["autumn_feed"] + 1,
    )
    
    log_user_action(uid, f"Купил осенний корм за {AUTUMN_FOOD_PRICE}🍂")
    
    await edit_section(
        query,
        caption=f"✅ +1 осенний корм за {AUTUMN_FOOD_PRICE}🍂.",
        image_key="autumn",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("⬅️ Назад", callback_data="autumn_shop")]]
        ),
    )


async def buy_autumn_mask(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Покупка тыквенной маски."""
    uid = query.from_user.id
    user = get_user(uid)
    
    if user["coins"] < 5000:
        await edit_section(
            query,
            caption="❌ Недостаточно монет. Нужно 5000🪙.",
            image_key="autumn",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⬅️ Назад", callback_data="autumn_shop")]]
            ),
        )
        return
    
    update_user(uid, coins=user["coins"] - 5000)
    log_user_action(uid, "Купил тыквенную маску за 5000🪙")
    
    await edit_section(
        query,
        caption="✅ Тыквенная маска куплена! +5% к доходу.",
        image_key="autumn",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("⬅️ Назад", callback_data="autumn_shop")]]
        ),
    )


async def buy_autumn_soup(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Покупка грибного супа."""
    uid = query.from_user.id
    user = get_user(uid)
    
    if user["coins"] < 3000:
        await edit_section(
            query,
            caption="❌ Недостаточно монет. Нужно 3000🪙.",
            image_key="autumn",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⬅️ Назад", callback_data="autumn_shop")]]
            ),
        )
        return
    
    update_user(uid, coins=user["coins"] - 3000)
    log_user_action(uid, "Купил грибной суп за 3000🪙")
    
    await edit_section(
        query,
        caption="✅ Грибной суп куплен! Восстанавливает здоровье питомцев.",
        image_key="autumn",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("⬅️ Назад", callback_data="autumn_shop")]]
        ),
    )


async def buy_autumn_cake(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Покупка орехового торта."""
    uid = query.from_user.id
    user = get_user(uid)
    
    if user["coins"] < 4000:
        await edit_section(
            query,
            caption="❌ Недостаточно монет. Нужно 4000🪙.",
            image_key="autumn",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⬅️ Назад", callback_data="autumn_shop")]]
            ),
        )
        return
    
    update_user(uid, coins=user["coins"] - 4000)
    log_user_action(uid, "Купил ореховый торт за 4000🪙")
    
    await edit_section(
        query,
        caption="✅ Ореховый торт куплен! Увеличивает счастье питомцев.",
        image_key="autumn",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("⬅️ Назад", callback_data="autumn_shop")]]
        ),
    )


async def buy_autumn_wreath(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Покупка осеннего венка."""
    uid = query.from_user.id
    user = get_user(uid)
    
    if user["coins"] < 7000:
        await edit_section(
            query,
            caption="❌ Недостаточно монет. Нужно 7000🪙.",
            image_key="autumn",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⬅️ Назад", callback_data="autumn_shop")]]
            ),
        )
        return
    
    update_user(uid, coins=user["coins"] - 7000)
    log_user_action(uid, "Купил осенний венок за 7000🪙")
    
    await edit_section(
        query,
        caption="✅ Осенний венок куплен! +3% к доходу.",
        image_key="autumn",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("⬅️ Назад", callback_data="autumn_shop")]]
        ),
    )


async def buy_autumn_antlers(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Покупка рогов оленя."""
    uid = query.from_user.id
    user = get_user(uid)
    
    if user["coins"] < 15000:
        await edit_section(
            query,
            caption="❌ Недостаточно монет. Нужно 15000🪙.",
            image_key="autumn",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⬅️ Назад", callback_data="autumn_shop")]]
            ),
        )
        return
    
    update_user(uid, coins=user["coins"] - 15000)
    log_user_action(uid, "Купил рога оленя за 15000🪙")
    
    await edit_section(
        query,
        caption="✅ Рога оленя куплены! +10% к доходу.",
        image_key="autumn",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("⬅️ Назад", callback_data="autumn_shop")]]
        ),
    )


# Новые осенние игры
async def autumn_game_wheat(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Игра 'Урожай зерна'."""
    uid = query.from_user.id
    user = get_user(uid)
    
    if user["coins"] < 5000:
        await edit_section(
            query,
            caption="❌ Недостаточно монет. Нужно 5000🪙.",
            image_key="autumn",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⬅️ Назад", callback_data="autumn_games")]]
            ),
        )
        return
    
    # Игра: собрать урожай
    crops = ["пшеница", "рожь", "овес", "ячмень"]
    correct_crop = random.choice(crops)
    
    text = (
        f"🌾 Урожай зерна\n\n"
        f"Какое зерно нужно собрать?\n"
        f"Варианты: {', '.join(crops)}\n\n"
        f"Введите зерно:"
    )
    
    context.user_data["autumn_game"] = {
        "type": "wheat",
        "correct": correct_crop,
        "cost": 5000,
        "reward": 10000
    }
    
    await edit_section(
        query,
        caption=text,
        image_key="autumn",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("⬅️ Отмена", callback_data="autumn_games")]]
        ),
    )


async def autumn_game_apple(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Игра 'Яблочный сад'."""
    uid = query.from_user.id
    user = get_user(uid)
    
    if user["coins"] < 6000:
        await edit_section(
            query,
            caption="❌ Недостаточно монет. Нужно 6000🪙.",
            image_key="autumn",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⬅️ Назад", callback_data="autumn_games")]]
            ),
        )
        return
    
    # Игра: собрать яблоки
    apple_types = ["антоновка", "голден", "гренни", "фуджи"]
    correct_apple = random.choice(apple_types)
    
    text = (
        f"🍎 Яблочный сад\n\n"
        f"Какие яблоки нужно собрать?\n"
        f"Варианты: {', '.join(apple_types)}\n\n"
        f"Введите сорт:"
    )
    
    context.user_data["autumn_game"] = {
        "type": "apple",
        "correct": correct_apple,
        "cost": 6000,
        "reward": 12000
    }
    
    await edit_section(
        query,
        caption=text,
        image_key="autumn",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("⬅️ Отмена", callback_data="autumn_games")]]
        ),
    )


async def autumn_game_squirrel(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Игра 'Беличья охота'."""
    uid = query.from_user.id
    user = get_user(uid)
    
    if user["coins"] < 7000:
        await edit_section(
            query,
            caption="❌ Недостаточно монет. Нужно 7000🪙.",
            image_key="autumn",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⬅️ Назад", callback_data="autumn_games")]]
            ),
        )
        return
    
    # Игра: помочь белке найти орехи
    nuts = ["фундук", "грецкий", "кедровый", "миндаль"]
    correct_nut = random.choice(nuts)
    
    text = (
        f"🌰 Беличья охота\n\n"
        f"Какие орехи ищет белка?\n"
        f"Варианты: {', '.join(nuts)}\n\n"
        f"Введите орех:"
    )
    
    context.user_data["autumn_game"] = {
        "type": "squirrel",
        "correct": correct_nut,
        "cost": 7000,
        "reward": 14000
    }
    
    await edit_section(
        query,
        caption=text,
        image_key="autumn",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("⬅️ Отмена", callback_data="autumn_games")]]
        ),
    )


async def autumn_game_wind(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Игра 'Осенний ветер'."""
    uid = query.from_user.id
    user = get_user(uid)
    
    if user["coins"] < 8000:
        await edit_section(
            query,
            caption="❌ Недостаточно монет. Нужно 8000🪙.",
            image_key="autumn",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⬅️ Назад", callback_data="autumn_games")]]
            ),
        )
        return
    
    # Игра: угадать направление ветра
    directions = ["север", "юг", "восток", "запад"]
    correct_direction = random.choice(directions)
    
    text = (
        f"🍂 Осенний ветер\n\n"
        f"В какую сторону дует ветер?\n"
        f"Варианты: {', '.join(directions)}\n\n"
        f"Введите направление:"
    )
    
    context.user_data["autumn_game"] = {
        "type": "wind",
        "correct": correct_direction,
        "cost": 8000,
        "reward": 16000
    }
    
    await edit_section(
        query,
        caption=text,
        image_key="autumn",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("⬅️ Отмена", callback_data="autumn_games")]]
        ),
    )


async def autumn_game_eagle(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Игра 'Орлиный полет'."""
    uid = query.from_user.id
    user = get_user(uid)
    
    if user["coins"] < 10000:
        await edit_section(
            query,
            caption="❌ Недостаточно монет. Нужно 10000🪙.",
            image_key="autumn",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⬅️ Назад", callback_data="autumn_games")]]
            ),
        )
        return
    
    # Игра: помочь орлу найти добычу
    prey = ["заяц", "мышь", "рыба", "змея"]
    correct_prey = random.choice(prey)
    
    text = (
        f"🦅 Орлиный полет\n\n"
        f"Какую добычу ищет орел?\n"
        f"Варианты: {', '.join(prey)}\n\n"
        f"Введите добычу:"
    )
    
    context.user_data["autumn_game"] = {
        "type": "eagle",
        "correct": correct_prey,
        "cost": 10000,
        "reward": 20000
    }
    
    await edit_section(
        query,
        caption=text,
        image_key="autumn",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("⬅️ Отмена", callback_data="autumn_games")]]
        ),
    )


async def autumn_game_stars(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Игра 'Осенняя ночь'."""
    uid = query.from_user.id
    user = get_user(uid)
    
    if user["coins"] < 12000:
        await edit_section(
            query,
            caption="❌ Недостаточно монет. Нужно 12000🪙.",
            image_key="autumn",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⬅️ Назад", callback_data="autumn_games")]]
            ),
        )
        return
    
    # Игра: найти созвездия
    constellations = ["большая медведица", "малая медведица", "орион", "кассиопея"]
    correct_constellation = random.choice(constellations)
    
    text = (
        f"🌙 Осенняя ночь\n\n"
        f"Какое созвездие нужно найти?\n"
        f"Варианты: {', '.join(constellations)}\n\n"
        f"Введите созвездие:"
    )
    
    context.user_data["autumn_game"] = {
        "type": "stars",
        "correct": correct_constellation,
        "cost": 12000,
        "reward": 24000
    }
    
    await edit_section(
        query,
        caption=text,
        image_key="autumn",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("⬅️ Отмена", callback_data="autumn_games")]]
        ),
    )