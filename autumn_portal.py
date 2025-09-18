"""
Модуль для осеннего портала и всех осенних функций
"""
import sqlite3
import time
import random
from typing import List, Optional, Tuple
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram import InputMediaPhoto

# Импорты из общего модуля
from common import IMAGES, AUTUMN_FOOD_PRICE, AUTUMN_EVENT_IMG


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
        "name": "🎃 Тыквенная лотерея",
        "description": "Выберите тыкву и получите награду",
        "cost": 2000,
        "reward": 5000,
        "callback": "autumn_game_pumpkin"
    },
    {
        "name": "🍁 Собери листья",
        "description": "Соберите как можно больше листьев",
        "cost": 1500,
        "reward": 3000,
        "callback": "autumn_game_collect"
    },
    {
        "name": "🌰 Ореховая охота",
        "description": "Найдите спрятанные орехи",
        "cost": 2500,
        "reward": 6000,
        "callback": "autumn_game_nuts"
    },
    {
        "name": "🍄 Грибная поляна",
        "description": "Соберите съедобные грибы",
        "cost": 3000,
        "reward": 7500,
        "callback": "autumn_game_mushrooms"
    },
    {
        "name": "🌧️ Дождевая магия",
        "description": "Используйте магию дождя",
        "cost": 4000,
        "reward": 10000,
        "callback": "autumn_game_rain"
    }
]

# Осенний магазин
AUTUMN_SHOP = [
    {
        "name": "🍂 Осенний корм",
        "description": "Специальный корм для осеннего сезона",
        "price": 1000,
        "type": "feed",
        "amount": 1
    },
    {
        "name": "🎃 Тыквенная маска",
        "description": "Маска для защиты от злых духов",
        "price": 5000,
        "type": "decoration",
        "amount": 1
    },
    {
        "name": "🍁 Венок из листьев",
        "description": "Красивый венок для украшения фермы",
        "price": 3000,
        "type": "decoration",
        "amount": 1
    },
    {
        "name": "🌰 Мешок орехов",
        "description": "Питательные орехи для питомцев",
        "price": 2000,
        "type": "feed",
        "amount": 3
    },
    {
        "name": "🍄 Грибной суп",
        "description": "Вкусный суп для восстановления энергии",
        "price": 4000,
        "type": "boost",
        "amount": 1
    }
]


def get_autumn_daily_reward(user_id: int) -> bool:
    """Проверить и выдать ежедневную награду"""
    user = get_user(user_id)
    now = int(time.time())
    last_daily = user.get("last_autumn_daily", 0)
    
    # Проверяем, прошло ли 24 часа
    if now - last_daily < 86400:  # 24 часа в секундах
        return False
    
    # Выдаем награду
    reward = random.randint(1000, 5000)
    update_user(
        user_id,
        coins=user["coins"] + reward,
        last_autumn_daily=now
    )
    
    log_user_action(user_id, f"Получил ежедневную осеннюю награду: {reward} монет")
    return True


async def autumn_portal_menu(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Главное меню осеннего портала"""
    uid = query.from_user.id
    user = get_user(uid)
    
    # Проверяем активность осеннего события
    cur.execute("SELECT autumn_event_active FROM global_settings WHERE id = 1")
    active = cur.fetchone()["autumn_event_active"]
    
    if not active:
        await edit_section(
            query,
            caption="🍂 Осенний портал временно закрыт.\n\nОбратитесь к администратору для активации.",
            image_key="autumn",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⬅️ Назад", callback_data="back")]]
            ),
        )
        return
    
    # Проверяем ежедневную награду
    daily_available = get_autumn_daily_reward(uid)
    daily_text = "🎁 Ежедневная награда доступна!" if daily_available else "⏰ Ежедневная награда завтра"
    
    text = (
        f"🍂 Осенний портал\n\n"
        f"Добро пожаловать в мир осенней магии!\n\n"
        f"💰 Ваши осенние монеты: {format_num(user.get('autumn_coins', 0))}\n"
        f"{daily_text}\n\n"
        f"Выберите раздел:"
    )
    
    btns = [
        InlineKeyboardButton("🎮 Осенние игры", callback_data="autumn_games"),
        InlineKeyboardButton("🛒 Осенний магазин", callback_data="autumn_shop"),
        InlineKeyboardButton("🎁 Ежедневные награды", callback_data="autumn_daily"),
        InlineKeyboardButton("🔄 Обмен монет", callback_data="autumn_exchange"),
        InlineKeyboardButton("📊 Статистика", callback_data="autumn_stats"),
    ]
    
    await edit_section(
        query,
        caption=text,
        image_key="autumn",
        reply_markup=InlineKeyboardMarkup(chunk_buttons(btns, per_row=2)),
    )


async def autumn_games_menu(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Меню осенних игр"""
    uid = query.from_user.id
    user = get_user(uid)
    
    text = "🎮 Осенние игры\n\nВыберите игру для игры:"
    
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


async def autumn_shop_menu(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Меню осеннего магазина"""
    uid = query.from_user.id
    user = get_user(uid)
    
    text = "🛒 Осенний магазин\n\nВыберите товар для покупки:"
    
    btns = []
    for item in AUTUMN_SHOP:
        btns.append(
            InlineKeyboardButton(
                f"{item['name']} ({format_num(item['price'])}🪙)",
                callback_data=f"autumn_buy_{item['type']}_{item['amount']}"
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
    """Ежедневные награды"""
    uid = query.from_user.id
    user = get_user(uid)
    
    # Исправляем ошибку с sqlite3.Row
    last_daily = user.get("last_autumn_daily", 0) if hasattr(user, 'get') else user["last_autumn_daily"] if "last_autumn_daily" in user.keys() else 0
    now = int(time.time())
    
    if now - last_daily < 86400:
        left = 86400 - (now - last_daily)
        hours = left // 3600
        minutes = (left % 3600) // 60
        
        text = (
            f"🎁 Ежедневные награды\n\n"
            f"⏰ Следующая награда через: {hours}ч {minutes}м\n\n"
            f"Ежедневно получайте от 1000 до 5000 монет!"
        )
    else:
        text = (
            f"🎁 Ежедневные награды\n\n"
            f"✅ Награда доступна!\n\n"
            f"Нажмите кнопку ниже, чтобы получить награду."
        )
    
    btns = []
    if now - last_daily >= 86400:
        btns.append(InlineKeyboardButton("🎁 Получить награду", callback_data="autumn_claim_daily"))
    
    btns.append(InlineKeyboardButton("⬅️ Назад", callback_data="autumn_portal"))
    
    await edit_section(
        query,
        caption=text,
        image_key="autumn",
        reply_markup=InlineKeyboardMarkup(chunk_buttons(btns, per_row=1)),
    )


async def autumn_exchange_menu(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обмен монет"""
    uid = query.from_user.id
    user = get_user(uid)
    
    text = (
        f"🔄 Обмен монет\n\n"
        f"💰 Ваши монеты: {format_num(user['coins'])}\n"
        f"🍂 Осенние монеты: {format_num(user.get('autumn_coins', 0))}\n\n"
        f"Выберите тип обмена:"
    )
    
    btns = [
        InlineKeyboardButton("🪙 → 🍂 (1:1)", callback_data="autumn_exchange_to_autumn"),
        InlineKeyboardButton("🍂 → 🪙 (1:1)", callback_data="autumn_exchange_to_normal"),
        InlineKeyboardButton("⬅️ Назад", callback_data="autumn_portal"),
    ]
    
    await edit_section(
        query,
        caption=text,
        image_key="autumn",
        reply_markup=InlineKeyboardMarkup(chunk_buttons(btns, per_row=1)),
    )


async def autumn_stats_menu(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Статистика осеннего портала"""
    uid = query.from_user.id
    user = get_user(uid)
    
    # Получаем статистику игрока
    cur.execute("SELECT COUNT(*) as count FROM admin_logs WHERE user_id = ? AND action LIKE '%осенн%'", (uid,))
    autumn_actions = cur.fetchone()["count"]
    
    text = (
        f"📊 Статистика осеннего портала\n\n"
        f"💰 Обычные монеты: {format_num(user['coins'])}\n"
        f"🍂 Осенние монеты: {format_num(user.get('autumn_coins', 0))}\n"
        f"🍂 Осенний корм: {user.get('autumn_feed', 0)}\n"
        f"🎮 Осенних действий: {autumn_actions}\n\n"
        f"Последняя ежедневная награда: {time.strftime('%d.%m.%Y %H:%M', time.localtime(user.get('last_autumn_daily', 0))) if user.get('last_autumn_daily', 0) > 0 else 'Никогда'}"
    )
    
    btns = [
        InlineKeyboardButton("⬅️ Назад", callback_data="autumn_portal"),
    ]
    
    await edit_section(
        query,
        caption=text,
        image_key="autumn",
        reply_markup=InlineKeyboardMarkup(chunk_buttons(btns, per_row=1)),
    )


async def handle_autumn_game(query, context: ContextTypes.DEFAULT_TYPE, game_type: str) -> None:
    """Обработка осенних игр"""
    uid = query.from_user.id
    user = get_user(uid)
    
    # Находим игру
    game = None
    for g in AUTUMN_GAMES:
        if g["callback"] == f"autumn_game_{game_type}":
            game = g
            break
    
    if not game:
        await edit_section(query, caption="❌ Игра не найдена.", image_key="autumn")
        return
    
    # Проверяем достаточно ли монет
    if user["coins"] < game["cost"]:
        await edit_section(
            query,
            caption=f"❌ Недостаточно монет. Нужно {format_num(game['cost'])}🪙.",
            image_key="autumn"
        )
        return
    
    # Играем в игру
    success = random.choice([True, True, True, False])  # 75% шанс успеха
    
    if success:
        # Выигрыш
        reward = game["reward"]
        update_user(
            uid,
            coins=user["coins"] - game["cost"] + reward,
            weekly_coins=user["weekly_coins"] + reward
        )
        
        text = (
            f"🎉 Поздравляем!\n\n"
            f"Вы выиграли {format_num(reward)}🪙!\n"
            f"Потрачено: {format_num(game['cost'])}🪙\n"
            f"Чистая прибыль: {format_num(reward - game['cost'])}🪙"
        )
        
        log_user_action(uid, f"Выиграл в игре {game['name']}: {reward} монет")
    else:
        # Проигрыш
        update_user(uid, coins=user["coins"] - game["cost"])
        
        text = (
            f"😔 Не повезло!\n\n"
            f"Вы проиграли {format_num(game['cost'])}🪙.\n"
            f"Попробуйте еще раз!"
        )
        
        log_user_action(uid, f"Проиграл в игре {game['name']}: {game['cost']} монет")
    
    btns = [
        InlineKeyboardButton("🎮 Играть снова", callback_data=game["callback"]),
        InlineKeyboardButton("⬅️ Назад к играм", callback_data="autumn_games"),
    ]
    
    await edit_section(
        query,
        caption=text,
        image_key="autumn",
        reply_markup=InlineKeyboardMarkup(chunk_buttons(btns, per_row=1)),
    )


async def handle_autumn_buy(query, context: ContextTypes.DEFAULT_TYPE, item_type: str, amount: int) -> None:
    """Обработка покупки в осеннем магазине"""
    uid = query.from_user.id
    user = get_user(uid)
    
    # Находим товар
    item = None
    for i in AUTUMN_SHOP:
        if i["type"] == item_type and i["amount"] == amount:
            item = i
            break
    
    if not item:
        await edit_section(query, caption="❌ Товар не найден.", image_key="autumn")
        return
    
    # Проверяем достаточно ли монет
    if user["coins"] < item["price"]:
        await edit_section(
            query,
            caption=f"❌ Недостаточно монет. Нужно {format_num(item['price'])}🪙.",
            image_key="autumn"
        )
        return
    
    # Покупаем товар
    if item_type == "feed":
        update_user(
            uid,
            coins=user["coins"] - item["price"],
            autumn_feed=user.get("autumn_feed", 0) + amount
        )
        text = f"✅ Куплено {amount} шт. {item['name']} за {format_num(item['price'])}🪙."
    elif item_type == "decoration":
        update_user(uid, coins=user["coins"] - item["price"])
        text = f"✅ Куплено {item['name']} за {format_num(item['price'])}🪙."
    elif item_type == "boost":
        update_user(uid, coins=user["coins"] - item["price"])
        text = f"✅ Куплено {item['name']} за {format_num(item['price'])}🪙."
    
    log_user_action(uid, f"Купил в осеннем магазине: {item['name']}")
    
    btns = [
        InlineKeyboardButton("🛒 Продолжить покупки", callback_data="autumn_shop"),
        InlineKeyboardButton("⬅️ Назад", callback_data="autumn_portal"),
    ]
    
    await edit_section(
        query,
        caption=text,
        image_key="autumn",
        reply_markup=InlineKeyboardMarkup(chunk_buttons(btns, per_row=1)),
    )


async def handle_autumn_exchange(query, context: ContextTypes.DEFAULT_TYPE, exchange_type: str) -> None:
    """Обработка обмена монет"""
    uid = query.from_user.id
    user = get_user(uid)
    
    if exchange_type == "to_autumn":
        # Обычные монеты в осенние
        if user["coins"] < 1000:
            await edit_section(
                query,
                caption="❌ Минимальная сумма для обмена: 1000🪙.",
                image_key="autumn"
            )
            return
        
        exchange_amount = min(user["coins"], 10000)  # Максимум 10000 за раз
        update_user(
            uid,
            coins=user["coins"] - exchange_amount,
            autumn_coins=user.get("autumn_coins", 0) + exchange_amount
        )
        
        text = f"✅ Обменено {format_num(exchange_amount)}🪙 на осенние монеты."
        
    elif exchange_type == "to_normal":
        # Осенние монеты в обычные
        autumn_coins = user.get("autumn_coins", 0)
        if autumn_coins < 1000:
            await edit_section(
                query,
                caption="❌ Минимальная сумма для обмена: 1000🍂.",
                image_key="autumn"
            )
            return
        
        exchange_amount = min(autumn_coins, 10000)  # Максимум 10000 за раз
        update_user(
            uid,
            coins=user["coins"] + exchange_amount,
            autumn_coins=autumn_coins - exchange_amount
        )
        
        text = f"✅ Обменено {format_num(exchange_amount)}🍂 на обычные монеты."
    
    log_user_action(uid, f"Обмен монет: {exchange_type}")
    
    btns = [
        InlineKeyboardButton("🔄 Продолжить обмен", callback_data="autumn_exchange"),
        InlineKeyboardButton("⬅️ Назад", callback_data="autumn_portal"),
    ]
    
    await edit_section(
        query,
        caption=text,
        image_key="autumn",
        reply_markup=InlineKeyboardMarkup(chunk_buttons(btns, per_row=1)),
    )


async def handle_autumn_claim_daily(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Получение ежедневной награды"""
    uid = query.from_user.id
    
    if get_autumn_daily_reward(uid):
        user = get_user(uid)
        text = (
            f"🎉 Ежедневная награда получена!\n\n"
            f"Вы получили случайную сумму монет.\n"
            f"Приходите завтра за новой наградой!"
        )
    else:
        text = "❌ Награда уже получена сегодня. Приходите завтра!"
    
    btns = [
        InlineKeyboardButton("⬅️ Назад", callback_data="autumn_daily"),
    ]
    
    await edit_section(
        query,
        caption=text,
        image_key="autumn",
        reply_markup=InlineKeyboardMarkup(chunk_buttons(btns, per_row=1)),
    )