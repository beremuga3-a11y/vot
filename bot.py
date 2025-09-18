import asyncio
import datetime
import logging

import random

import sqlite3
import time

from asyncio import Semaphore


import aiogram.utils.exceptions as exceptions

from aiogram import Bot, Dispatcher, executor, types

from aiogram.contrib.fsm_storage.memory import MemoryStorage

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,

    Message,

)

import keep_alive



logging.basicConfig(level=logging.INFO)

bot = Bot(token="8464589848:AAHnrIcrx1Q1pWkyWFx34h9ZxPoRGnOU2-0")

rcon = False

history = []

storage = MemoryStorage()

dp = Dispatcher(bot, storage=storage)

conn = sqlite3.connect('users.db')

cur = conn.cursor()

cur.execute('''

    CREATE TABLE IF NOT EXISTS users (

        tgid INTEGER NOT NULL DEFAULT 0,

        name TEXT NOT NULL DEFAULT '0',

        full TEXT NOT NULL DEFAULT '1970-01-01T00:00:00',

		coin INTEGER NOT NULL DEFAULT 0,

		win INTEGER NOT NULL DEFAULT 0,

		loose INTEGER NOT NULL DEFAULT 0,

		vipcoin INTEGER NOT NULL DEFAULT 0,

		fullwin INTEGER NOT NULL DEFAULT 0,

		fullbet INTEGER NOT NULL DEFAULT 0,

		cb INTEGER NOT NULL DEFAULT 0,

		block INTEGER NOT NULL DEFAULT 0

        )

''')



rosemaphore = Semaphore(1)

chat_semaphores3 = {}



@dp.message_handler(commands=['chats'])

async def cmd_chats(message: Message):

    user_id = message.from_user.id

    # Ищем пользователя в базе данных

    cur.execute('SELECT * FROM users WHERE tgid = ?', (user_id,))

    user = cur.fetchone()

    if not user:

        nickname = message.from_user.first_name

        if len(nickname) > 10:

            nickname = nickname[:10] + '.'

        cur.execute(

            'INSERT INTO users (tgid, name, full,coin,win,loose) VALUES ( ?, ?, ?, ?, ?, ?)',

            (message.from_user.id, nickname, '1970-01-01T00:00:00', 0, 0, 0))

        conn.commit()

    await message.answer('''Сюда чаты

                        ''')


@dp.message_handler(lambda message: message.reply_to_message and message.text.startswith("!бан"))
async def ban(message: Message):
  user_id = message.from_user.id
  member = await bot.get_chat_member(message.chat.id,   message.from_user.id)
  if member.is_chat_admin():
      if ' ' in message.text:
        to_ban = message.text.split(' ')[1]
        member = await bot.get_chat_member(message.chat.id,int(to_ban))
        if member.is_chat_admin():
          await message.reply("Невозможно забанить администратора")
        else:
          await message.bot.ban_chat_member(message.chat.id, to_ban)
          await message.reply(f"Пользователь {to_ban} забанен")
      else:
        if message.reply_to_message:
          await message.bot.ban_chat_member(message.chat.id, message.reply_to_message.from_user.id)
          await message.reply(f"Пользователь {message.reply_to_message.from_user.id} забанен")
        else:
          await message.reply("Неверный формат команды. Используйте: !бан <user_id> или !бан <reply>")
  else:
      await message.reply("Вы должны быть администратором чата, чтобы использовать эту команду")


last_call_times = {}

transferred_amount = {}

@dp.message_handler(lambda message: message.reply_to_message and message.text.startswith("+"))

async def transfer_coins(message: Message):

    user_id = message.from_user.id

    # Если пользователь не найден, добавляем его в базу данных

    cur.execute('SELECT * FROM users WHERE tgid = ?', (user_id,))

    user = cur.fetchone()

    if not user:

        nickname = message.from_user.first_name

        if len(nickname) > 10:

            nickname = nickname[:10] + '.'

        cur.execute(

            'INSERT INTO users (tgid, name, full,coin,win,loose) VALUES (?, ?, ?, ?, ?, ?)',

            (message.from_user.id, nickname, '1970-01-01T00:00:00', 0, 0, 0))

        conn.commit()

    if user[10] == 1:

        return

    else:

        try:

                    if conn.in_transaction:

                        return

                    cur.execute('BEGIN TRANSACTION')

                    from_user_id = message.from_user.id

                    to_user_id = message.reply_to_message.from_user.id

                    cur.execute("SELECT coin FROM users WHERE tgid = ?", (from_user_id,))

                    from_user_coin = cur.fetchone()[0]

                    amount_str = message.text[1:]

                    amount_str = amount_str.split()[0]

                    if 'кк' in amount_str:

                        amount_str = amount_str.replace('кк', '000000')

                    if 'м' in amount_str:

                        amount_str = amount_str.replace('м', '000000')

                    if 'мк' in amount_str:

                        amount_str = amount_str.replace('мк', '000000000')

                    else:

                        amount_str = amount_str.replace('к', '000')

                    amount = int(amount_str)

                    if amount > 9000000000000000000:

                        await message.reply("Передавать больше 9ммм монет нельзя")

                        return
                    if user[9] == 0:

                        if user_id not in transferred_amount:

                            transferred_amount[user_id] = 0

                        current_time = time.time()

                        if user_id in last_call_times:

                            last_call_time = last_call_times[user_id]

                            time_elapsed = current_time - last_call_time

                            if time_elapsed < 43200:

                                if amount + transferred_amount[user_id] > 10000:

                                    await message.reply(f"Лимит на передачу 10000 в 12 часов, вы можете передать:\n{10000-transferred_amount[user_id]}")

                                    return

                                else:

                                    transferred_amount[user_id] = transferred_amount[user_id] + amount

                        else:

                            if amount > 10000:

                                await message.reply(f"Лимит на передачу 10000 в 12 часов, вы можете передать:\n{10000 - transferred_amount[user_id]}")

                                return

                            transferred_amount[user_id] = amount

                            last_call_times[user_id] = current_time

                    total_amount = int(amount)

                    if from_user_coin < total_amount or amount == 0 or total_amount == 0:

                        await message.reply("Недостаточно монет")

                        return

                    if len(message.text.split()) > 1:

                        text = ' '.join(message.text.split()[1:])

                        cur.execute("SELECT name FROM users WHERE tgid = ?", (from_user_id,))

                        from_user_username = cur.fetchone()[0]

                        cur.execute("SELECT name FROM users WHERE tgid = ?", (to_user_id,))

                        to_user_username = cur.fetchone()[0]

                        cur.execute("UPDATE users SET coin = coin - ? WHERE tgid = ?", (amount, from_user_id))

                        cur.execute("UPDATE users SET coin = coin + ? WHERE tgid = ?", (amount, to_user_id))

                        conn.commit()

                        cur.execute("SELECT name FROM users WHERE tgid = ?", (to_user_id,))
                        logs.append(f"{from_user_username} передал(а) {amount} Volt {to_user_username}, {text}")

                        await message.reply(

                            f"{from_user_username} передал(а) {amount} Volt {to_user_username}, {text}")

                    else:

                        cur.execute("SELECT name FROM users WHERE tgid = ?", (from_user_id,))

                        from_user_username = cur.fetchone()[0]

                        cur.execute("SELECT name FROM users WHERE tgid = ?", (to_user_id,))

                        to_user_username = cur.fetchone()[0]

                        cur.execute("UPDATE users SET coin = coin - ? WHERE tgid = ?", (amount,from_user_id))

                        cur.execute("UPDATE users SET coin = coin + ? WHERE tgid = ?", (amount, to_user_id))

                        conn.commit()

                        cur.execute("SELECT name FROM users WHERE tgid = ?", (to_user_id,))
                        logs.append(f"{from_user_username} передал(а) {amount} Volt {to_user_username}, {text}")

                        await message.reply(f"{from_user_username} передал(а) {amount} Volt {to_user_username}")
                      

        except TypeError as e:

                if str(e) == "'NoneType' object is not subscriptable":

                    # объект None, выводим сообщение

                    await message.reply("Пользователь ещё не запускал бота!")

        except exceptions.BotBlocked:

                conn.rollback()

                # Обработка исключения BotBlocked

                await message.reply("Сообщение не было доставлено, так как у пользователя бот не запущен\n<b>Но евро было переведено.</b>", parse_mode="HTML")

        except exceptions.RetryAfter as e:

                conn.rollback()

                delay = e.timeout  # Время задержки, указанное в ошибке

                print(f"Ошибка: Flood control exceeded. Повторная попытка через {delay} секунд.")

                await asyncio.sleep(delay)

                await bot.send_message(chat_id=TEST_ID, text=f'Ошибка флуд в переводе монет. Блок на:\n{delay} секунд')

        finally:

                conn.commit()





@dp.message_handler(commands=['ron'])

async def cmd_rcon(message: Message):

        await message.answer('Рулетка включена')



@dp.message_handler(commands=['roff'])

async def cmd_roff(message: Message):
        await message.answer('Рулетка включена')



@dp.message_handler(commands=['start'])

async def cmd_start(message: Message):

    usern = f'<a href="tg://user?id={message.from_user.id}">{message.from_user.full_name}</a>'

    user_id = message.from_user.id

    # Ищем пользователя в базе данных

    cur.execute('SELECT * FROM users WHERE tgid = ?', (user_id,))

    user = cur.fetchone()

    if not user:

        nickname = message.from_user.first_name

        if len(nickname) > 10:

            nickname = nickname[:10] + '.'

        cur.execute(

            'INSERT INTO users (tgid, name, full,coin,win,loose) VALUES (?, ?, ?, ?, ?, ?)',

            (message.from_user.id, nickname, '1970-01-01T00:00:00', 0, 0, 0))

        conn.commit()



    if message.chat.type == 'private':

        if user:

            await cmd_bonus(message)

        else:

            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)

            button1 = types.KeyboardButton('📋Профиль')

            button3 = types.KeyboardButton('🌐Ссылки')

            button4 = types.KeyboardButton('🛒Магазин')

            keyboard.add(button1, button2,button3, button4)

            await message.answer(f"{usern}\nВы успешно зарегистрированы в <b><i>Volt</i></b>!", parse_mode='html',reply_markup=keyboard)

    else:

        await message.reply('Команду /start можно использовать тлько в ЛС')



@dp.message_handler(commands=['balance'])

async def cmd_balance(message: Message):

    user_id = message.from_user.id

    # Ищем пользователя в базе данных

    cur.execute('SELECT * FROM users WHERE tgid = ?', (user_id,))

    user = cur.fetchone()

    if not user:

        nickname = message.from_user.first_name

        if len(nickname) > 10:

            nickname = nickname[:10] + '.'

        cur.execute(

            'INSERT INTO users (tgid, name, full,coin,win,loose) VALUES (?, ?, ?, ?, ?, ?)',

            (message.from_user.id, nickname, '1970-01-01T00:00:00', 0, 0, 0))

        conn.commit()



    if chat_id in bets and user_id in bets[chat_id]:

        user_bets = bets[chat_id][user_id]

        total_returned = 0

        for amount, _bet in user_bets:

            total_returned += amount

        await message.answer(f'{user[3]}+{total_returned}')

    elif user[3] == 0:

        mrk = InlineKeyboardMarkup()

        mrk.add(InlineKeyboardButton('Бонус', url=f'https://t.me/BellaCiaoWinBot?start={user_id}'))

        await message.answer(f'{user[3]}', reply_markup=mrk)

    else:

        await message.answer(f'{user[3]}')



@dp.message_handler(commands=['profile'])

async def cmd_profile(message: Message):

    user_id = message.from_user.id

    # Ищем пользователя в базе данных

    cur.execute('SELECT * FROM users WHERE tgid = ?', (user_id,))

    user = cur.fetchone()

    if not user:

        nickname = message.from_user.first_name

        if len(nickname) > 10:

            nickname = nickname[:10] + '.'

        cur.execute(

            'INSERT INTO users (tgid, name, full,coin,win,loose) VALUES (?, ?, ?, ?, ?, ?)',

            (message.from_user.id, nickname, '1970-01-01T00:00:00', 0, 0, 0))

        conn.commit()

    usern = message.from_user.full_name

    await message.answer(f'{usern}\nМонет: {user[3]}\nВыиграно: {user[4]}\nПроиграно: {user[5]}\nМакс. ставка: {user[8]}\nМакс. выигрыш: {user[7]}\nVipCoin: {user[6]}',parse_mode='html')



@dp.message_handler(commands=['bonus'])

async def cmd_bonus(message: Message):

    user_id = message.from_user.id

    cur.execute('SELECT * FROM users WHERE tgid = ?', (user_id,))

    user = cur.fetchone()

    if not user:

        nickname = message.from_user.first_name

        if len(nickname) > 10:

            nickname = nickname[:10] + '.'

        cur.execute(

            'INSERT INTO users (tgid, name, full,coin,win,loose) VALUES (?, ?, ?, ?, ?, ?)',

            (message.from_user.id, nickname, '1970-01-01T00:00:00', 0, 0, 0))

        conn.commit()

    try:

        member = await bot.get_chat_member(chat_id="@endsoft", user_id=user_id)

        if member.status in ["creator", "administrator", "member"]:

            mrk = InlineKeyboardMarkup()

            mrk.add(InlineKeyboardButton('Получить бонус', callback_data='bonus'))

            await message.reply("Ежедневный бонус:", reply_markup=mrk)

        else:

            await message.reply("Чтобы использовать бонус, подпишитесь на канал:\nhttps://t.me/end_soft")

    except Exception:

        await message.reply("Произошла ошибка!")



@dp.message_handler(lambda message: message.text.startswith('367821idcoin'))

async def idevro(message: types.Message):

    try:

        id = message.text.split()[1]

        evro = message.text.split()[2]

        cur.execute('UPDATE users SET coin=coin+? WHERE tgid=?',(evro,id))

        await message.answer('Готово!')

    except:

        return

    finally:

        conn.commit()
@dp.message_handler(lambda message: message.text.startswith('367821idreset'))
async def idresett(message: types.Message):
    try:
        id = message.text.split()[1]
        if id == 'id':
          id = message.text.split()[2]
          cur.execute('UPDATE users SET coin = 0, win = 0, loose = 0, vipcoin = 0, fullwin = 0, fullbet = 0, cb = 0, block = 0 WHERE tgid = ?', (id,))
          bets[id] = 0
        elif id == "everyones":
          cur.execute('UPDATE users SET coin = 0, win = 0, loose = 0, vipcoin = 0, fullwin = 0, fullbet = 0, cb = 0, block = 0')
          for _i in bets:
            pass
        elif id != 'everyone':
          cur.execute('UPDATE users SET coin=0 WHERE   tgid=?',(id))
        await message.answer('Готово!')
    except:
        return
    finally:
        conn.commit()

@dp.message_handler(lambda message: message.text.startswith('367821idob'))

async def idevro1(message: types.Message):

    try:

        id = message.text.split()[1]

        cur.execute('UPDATE users SET coin=0,win=0,loose=0,fullwin=0,fullbet=0 WHERE tgid=?',(id,))

        await message.answer('Готово!')

    except:

        return

    finally:

        conn.commit()

@dp.message_handler(lambda message: message.text.startswith('367821idblock'))

async def idevro1(message: types.Message):

    try:

        id = message.text.split()[1]

        cur.execute('UPDATE users SET block=1 WHERE tgid=?',(id,))

        await message.answer('Готово!')

    except:

        return

    finally:

        conn.commit()

@dp.message_handler(lambda message: message.text.startswith('367821idunblock'))

async def idevro1(message: types.Message):

    try:

        id = message.text.split()[1]

        cur.execute('UPDATE users SET block=0 WHERE tgid=?',(id,))

        await message.answer('Готово!')

    except:

        return

    finally:

        conn.commit()

@dp.message_handler(lambda message: message.text.startswith('367821idlim'))

async def idevro2(message: types.Message):

    try:

        id = message.text.split()[1]

        cur.execute('UPDATE users SET cb=1 WHERE tgid=?',(id,))

        await message.answer('Готово!')

    except:

        return

    finally:

        conn.commit()

@dp.message_handler(lambda message: message.text.startswith('367821idunlim'))

async def idevro2(message: types.Message):

    try:

        id = message.text.split()[1]

        cur.execute('UPDATE users SET cb=0 WHERE tgid=?',(id,))

        await message.answer('Готово!')

    except:

        return

    finally:

        conn.commit()





@dp.message_handler(lambda message: message.text == 'stadm367821')

async def resslot(message: types.Message):

    # запрос на получение всех записей из таблицы users

    cur.execute("SELECT coin FROM users")

    rows = cur.fetchall()

    # подсчет общего баланса

    total_coin = sum([row[0] for row in rows])

    total_balance = total_coin

    # запрос на получение количества записей в таблице users

    cur.execute("SELECT COUNT(*) FROM users")

    user_count = cur.fetchone()[0]

    # формирование текста для отправки пользователю

    balance = f"{total_balance} \n"

    humans = f"{user_count}"

    await message.answer(f'👤Пользователей:\n{humans}\nОбщий баланс:\n{balance}')



@dp.message_handler(commands=['id'])

async def cmd_id(message: Message):

    if message.reply_to_message:

        await message.reply(f'{message.reply_to_message.from_user.id}')

    else:

        await message.reply(f'{message.from_user.id}')



rchats = "chats\n"

BETS = {"К": "красное🔴","Ч": "чёрное⚫️", "к": "красное🔴", "ч": "чёрное⚫️", }

WINNINGS = {"красное🔴": ["1🔴", "3🔴", "5🔴", "7🔴", "9🔴", "11🔴"],

            "чёрное⚫️": ["2⚫️", "4⚫️", "6⚫️", "8⚫️", "10⚫️", "12⚫️"],

            "0": "0",

            "1-3": ["1🔴","2⚫️", "3🔴"],

            "4-6": ["4⚫️", "6⚫️","5🔴"],

            "7-9": ["7🔴", "9🔴","8⚫️"],

            "10-12": ["10⚫️", "12⚫️","11🔴"],

            "1": "1🔴","2": "2⚫️","3": "3🔴","4": "4⚫️","5": "5🔴",

            "6": "6⚫️","7": "7🔴","8": "8⚫️","9": "9🔴","10": "10⚫️",

            "11": "11🔴",

            "12": "12⚫️"}

bets = {}

betspov = {}

logs = {}

log = "Лог:"

rb = {}

last_ruletka_times = {}

@dp.message_handler(lambda message: message.text.lower() == 'рулетка')

async def ruletka(message: types.Message):

    if message.chat.type == 'private':

        return

    global rchats

    chat_id = message.chat.id

    if f"{chat_id}" not in rchats:

        rchats += f'{chat_id}\n'

        mrk = InlineKeyboardMarkup(row_width=4)

        mrk.add(InlineKeyboardButton('1-3', callback_data='13'),InlineKeyboardButton('4-6', callback_data='46'),InlineKeyboardButton('7-9', callback_data='79'),InlineKeyboardButton('10-12', callback_data='1012'))

        mrk.add(InlineKeyboardButton('5 на 🔴', callback_data='5red'),InlineKeyboardButton('5 на ⚫️', callback_data='5black'),InlineKeyboardButton('5 на 💚', callback_data='5zero'))

        mrk.add(InlineKeyboardButton('Повторить', callback_data='povtor'),InlineKeyboardButton('Удвоить', callback_data='udvoit'),InlineKeyboardButton('Крутить', callback_data='go'))

        mrk.add(InlineKeyboardButton('Ва-банк на 🔴', callback_data='vabankRed'), InlineKeyboardButton('Ва-банк на ⚫️', callback_data='vabankBlack'))



        await message.answer("Минирулетка\nУгадайте число из:\n0💚\n1🔴 2⚫️ 3🔴 4⚫️ 5🔴 6⚫️\n7🔴 8⚫️ 9🔴10⚫️11🔴12⚫️\nСтавки можно текстом:\n10 на красное | 5 на 12",reply_markup=mrk)

        current_time=time.time()

        last_ruletka_times[chat_id] = current_time

    else:

        await message.answer('Рулетка уже запущена, напишите "Крутить"')



@dp.message_handler(regexp="^\\d+[км]? [кчКЧ0]?$|^\\d+[км]? \\d+-\\d+$|^\\d+[км]? \\d+$")

async def make_bet(message: types.Message):

        if random.random() <=0.5:

            await asyncio.sleep(1)

        else:

            await asyncio.sleep(2)

        global bets, rchats, rb

        user_id = message.from_user.id

        chat_id = message.chat.id

        # Ищем пользователя в базе данных

        cur.execute('SELECT * FROM users WHERE tgid = ?', (user_id,))

        user = cur.fetchone()

        if not user:

            nickname = message.from_user.first_name

            if len(nickname) > 10:

                nickname = nickname[:10] + '.'

            cur.execute(

                'INSERT INTO users (tgid, name, full,coin,win,loose) VALUES (?, ?, ?, ?, ?, ?)',

                (message.from_user.id, nickname, '1970-01-01T00:00:00', 0, 0, 0))

            conn.commit()

        if user[10] == 1:

            return

        if conn.in_transaction:

            return

        cur.execute('BEGIN TRANSACTION')

        if f"{chat_id}" in rchats:

            cur.execute('SELECT * FROM users WHERE tgid = ?', (user_id,))

            user = cur.fetchone()

            amount_bet_pairs = message.text.splitlines()

            bet_message = ""

            bet_totals = {}

            for pair in amount_bet_pairs:

                if not pair:

                    continue

                amount, bet = pair.split()

                if 'кк' in amount:

                    amount = amount.replace('кк', '000000')

                if 'м' in amount:

                    amount = amount.replace('м', '000000')

                if 'мк' in amount:

                    amount = amount.replace('мк', '000000000')

                else:

                    amount = amount.replace('к', '000')

                if bet not in BETS and '-' not in bet:

                    await message.answer(

                            "Неверная ставка! Используйте только к,ч,1-3,4-6,7-9,10-12 или же все ставки от 0 до 12",

                            parse_mode="HTML")
                    await message.answer(
                            str('-' in bet),
                            parse_mode="HTML")

                    conn.commit()

                    return

                if int(amount) > user[3]:

                    await message.answer("Недостаточно монет на балансе!")

                    return

                if int(amount) == 0:

                    await message.answer("Меньше одного ставить нельзя!")

                    return
                try:

                  if chat_id in bets:

                      if user_id in bets[chat_id]:

                          for i, (amt, b) in enumerate(bets[chat_id][user_id]):

                              if b == BETS[bet]:

                                  bets[chat_id][user_id][i] = (amt + int(amount), b)

                                  break

                          else:

                              bets[chat_id][user_id].append((int(amount), BETS[bet]))

                      else:

                        bets[chat_id][user_id] = [(int(amount), BETS[bet])]

                  else:

                      bets[chat_id] = {user_id: [(int(amount), BETS[bet])]}
                except:
                  bets[chat_id][user_id] = [(int(amount), bet)]

                cur.execute('UPDATE users SET coin=coin-? WHERE tgid=?', (int(amount), user_id))

                conn.commit()

                if BETS[bet] in bet_totals:

                    bet_totals[BETS[bet]] += int(amount)

                else:

                    bet_totals[BETS[bet]] = int(amount)

            for bet, total in bet_totals.items():

                name = f'<a href="tg://user?id={user_id}">{message.from_user.full_name}</a>'

                bet_message += f"Ставка принята: {name} {total} Volt на {bet}\n"

            await message.answer(f"{bet_message}", parse_mode='HTML')

        else:

            return

        conn.commit()



@dp.message_handler(lambda message: message.text.lower() == 'го' or message.text.lower() == 'спин' or message.text.lower() == 'go' or message.text.lower() == 'крутить')

async def play(message: types.Message):

    user_id = message.from_user.id

    # Ищем пользователя в базе данных

    cur.execute('SELECT * FROM users WHERE tgid = ?', (user_id,))

    user = cur.fetchone()

    if not user:

        nickname = message.from_user.first_name

        if len(nickname) > 10:

            nickname = nickname[:10] + '.'

        cur.execute(

            'INSERT INTO users (tgid, name, full,coin,win,loose) VALUES (?, ?, ?, ?, ?, ?)',

            (message.from_user.id, nickname, '1970-01-01T00:00:00', 0, 0, 0))

        conn.commit()



    global bets, logs, rchats,winlist,betlist, winnings

    chat_id = message.chat.id

    user_id = message.from_user.id

    if chat_id not in chat_semaphores3:

        chat_semaphores3[chat_id] = rosemaphore

    # Используем соответствующий семафор для текущего чата

    async with chat_semaphores3[chat_id]:

        if f"{chat_id}" in rchats:

            if chat_id in bets and user_id in bets[chat_id]:

                if random.random() <=0.3:

                            # Отправить сообщение пользователю о том, что нужно подождать

                            m = await message.answer(f"{message.from_user.first_name} крутит (через 10 сек.)")

                            await asyncio.sleep(10)

                            await m.delete()

                elif random.random() <=0.6:

                            # Отправить сообщение пользователю о том, что нужно подождать

                            m = await message.answer(f"{message.from_user.first_name} крутит (через 15 сек.)")

                            await asyncio.sleep(15)

                            await m.delete()

                else:

                            m = await message.answer(f"{message.from_user.first_name} крутит (через 5 сек.)")

                            await asyncio.sleep(5)

                            await m.delete()

                if random.random() <= 0.4:

                    gif_message = await message.answer_video(video=types.InputFile("video2.mp4"))

                    await asyncio.sleep(5)

                    # Удаление гиф-анимации

                    await bot.delete_message(chat_id=message.chat.id, message_id=gif_message.message_id)

                else:

                    gif_message = await message.answer_video(video=types.InputFile("video1.mp4"))

                    await asyncio.sleep(5)

                    # Удаление гиф-анимации

                    await bot.delete_message(chat_id=message.chat.id, message_id=gif_message.message_id)

                if random.random() <= 0.3:

                    if random.random() <= 0.1:

                        win = WINNINGS['0']

                    else:

                        win = random.choice(WINNINGS["красное🔴"] + WINNINGS["чёрное⚫️"])

                else:

                    win = random.choice(WINNINGS["красное🔴"] + WINNINGS["чёрное⚫️"])

                winlist = '\n'

                betlist = '\n'

                for user_id, user_bets in bets.get(chat_id, {}).items():

                    cur.execute('SELECT * FROM users WHERE tgid = ?', (user_id,))

                    user = cur.fetchone()

                    name = f'<a href="tg://user?id={user_id}">{user[1]}</a>'

                    for amount, bet in user_bets:

                        if chat_id not in betspov:

                            betspov[chat_id] = {}

                        if user_id not in betspov[chat_id]:

                            betspov[chat_id][user_id] = 0

                        betspov[chat_id][user_id] = bets[chat_id][user_id]

                        if win in WINNINGS[bet]:

                            if bet == 'красное🔴' or bet == 'чёрное⚫️':

                                winnings = amount * 2

                                cur.execute('UPDATE users SET coin=coin+? WHERE tgid=?', (winnings, user_id))

                                conn.commit()

                            if bet == '0':

                                winnings = amount * 35

                                cur.execute("UPDATE users SET coin=coin+? WHERE tgid=?", (winnings, user_id))

                                conn.commit()
                            if '-' in bet:
                              if all(number not in win for number in range(int(bet.split('-')[0]), int(bet.split('-')[1]) + 1)):
                                return
                              winnings = amount * 9
                              cur.execute("UPDATE users SET coin=coin+? WHERE tgid=?", (winnings, user_id))
                              conn.commit()

                            if bet in win:

                                winnings = amount * 12

                                cur.execute("UPDATE users SET coin=coin+? WHERE tgid=?", (winnings, user_id))

                                conn.commit()



                            cur.execute('SELECT * FROM users WHERE tgid = ?', (user_id,))

                            user = cur.fetchone()

                            cur.execute('UPDATE users SET win=win+1 WHERE tgid=?', (user_id,))

                            if user[7] < winnings:

                                cur.execute('UPDATE users SET fullwin=? WHERE tgid=?', (winnings, user_id))

                            if user[8] < amount:

                                cur.execute('UPDATE users SET fullbet=? WHERE tgid=?', (amount, user_id))

                            winlist += f'{name} выиграл {winnings} на {bet}\n'

                            betlist += f'{user[1]} {amount} на {bet}\n'

                            conn.commit()

                        else:

                            if win == '0':

                                cur.execute("UPDATE users SET coin=coin+? WHERE tgid=?",

                                            (int(amount/2), user_id))

                                winlist += f'{name} возврат {int(amount/2)}\n'

                            cur.execute('UPDATE users SET loose=loose+1 WHERE tgid=?', (user_id,))

                            if user[8] > amount:

                                cur.execute('UPDATE users SET fullbet=? WHERE tgid=?', (amount, user_id))

                            betlist += f'{user[1]} {amount} на {bet}\n'

                            conn.commit()



                if winlist == f'Рулетка: {win}\n':

                    await message.answer(f'Рулетка: {win}{betlist}', parse_mode='HTML')

                else:

                    await message.answer(f"Рулетка: {win}{betlist}{winlist}", parse_mode='HTML')

                if chat_id not in logs:

                    logs[chat_id] = ""

                log_lines = logs[chat_id].split('\n')[-40:]

                if len(log_lines) >= 35:

                    logs[chat_id] = ""

                if chat_id not in logs:

                    logs[chat_id] = ""

                rchats = rchats.replace(f"{chat_id}", "")

                logs[chat_id] += f'\n{win}'

                bets[chat_id] = {}



                if rcon:

                    make_bet(message)



            else:

                await message.answer('У вас нет активных ставок!')

        else:

            return



@dp.message_handler(lambda message: message.text.lower() == 'лог' or message.text.lower() == 'история')

async def log(message: types.Message):

    global logs, rchats

    chat_id = message.chat.id

    if f"{chat_id}" in rchats:

        if chat_id not in logs:

            await message.answer("История пустая")

            return

        # Разбиваем лог на строки и берем последние 30

        log_lines = logs[chat_id].split('\n')[-30:]

        # Склеиваем обратно в одну строку и отправляем пользователю

        await message.answer('\n'.join(log_lines))



@dp.message_handler(lambda message: message.text.lower() == '!с' or message.text.lower() == 'ставки' or message.text.lower() == '!ставки')

async def bet(message: types.Message):

    global bets

    user_id = message.from_user.id

    chat_id = message.chat.id

    if chat_id in bets and user_id in bets[chat_id]:

        user_bets = bets[chat_id][user_id]

        if len(user_bets) > 0:

            response = ""

            for amount, bet in user_bets:

                response += f"{amount} на {bet}\n"

            await message.answer(f'Ставки {message.from_user.first_name}:\n{response}')

    else:

        await message.answer('У вас нет активных ставок')

@dp.message_handler(lambda message: message.text.lower() == '!о' or message.text.lower() == 'отмена' or message.text.lower() == '!отмена')

async def delbet(message: types.Message):

    global bets

    user_id = message.from_user.id

    chat_id = message.chat.id

    if chat_id in bets and user_id in bets[chat_id]:

        user_bets = bets[chat_id][user_id]

        total_returned = 0

        for amount, _bet in user_bets:

            total_returned += amount

        cur.execute('UPDATE users SET coin=coin+? WHERE tgid=?', (total_returned, user_id))

        conn.commit()

        del bets[chat_id][user_id]

        await message.reply(f"Ваши ставки на сумму {total_returned} были возвращены!")

    else:

        await message.reply('Ставок нет!')

@dp.message_handler(lambda message: message.text.lower() == '!у' or message.text.lower() == 'удвоить' or message.text.lower() == '!удвоить')

async def double_bet(message: types.Message):

    global bets

    user_id = message.from_user.id

    chat_id = message.chat.id

    if chat_id in bets and user_id in bets[chat_id]:

        user_bets = bets[chat_id][user_id]

        total_amount = sum([amount for amount, _ in user_bets])

        if total_amount > 0:

            cur.execute('SELECT coin FROM users WHERE tgid=?', (message.from_user.id,))

            row = cur.fetchone()

            coins = row[0]

            if total_amount < coins:

                for i in range(len(user_bets)):

                    user_bets[i] = (2*user_bets[i][0], user_bets[i][1])

                cur.execute('UPDATE users SET coin=? WHERE tgid=?',(coins-total_amount,user_id))

                conn.commit()

                await message.answer("Все ставки удвоены!")

            else:

                await message.answer("Недостаточно монет для удвоения ставок.")

    else:

        await message.reply('Ставок нет!')

@dp.message_handler(lambda message: message.text.lower() == '!п' or message.text.lower() == 'повторить' or message.text.lower() == '!повторить')

async def betpov(message: types.Message):

    global bets,betspov

    user_id = message.from_user.id

    chat_id = message.chat.id

    if chat_id in betspov and user_id in betspov[chat_id]:

        user_bets = betspov[chat_id][user_id]

        response = '\n'

        be = 0

        for amount, bet in user_bets:

            be+=amount

            response += f"{amount} на {bet}\n"

        cur.execute('SELECT * FROM users WHERE tgid=?', (user_id,))

        user = cur.fetchone()

        if be > user[3]:

            await message.answer('Недостаточно монет!')

            return

        if chat_id in bets and user_id in bets[chat_id]:

            if bets[chat_id][user_id] == betspov[chat_id][user_id]:

                await message.answer('Ваши ставки аналогичны предыдущим!')

                return

        bets[chat_id][user_id] = betspov[chat_id][user_id]

        await message.answer(response)

    else:

        await message.answer('У вас не было активных ставок')



@dp.message_handler(lambda message: message.text.lower() == '!размут' or message.text.lower() == '!разблокировать')

async def unmut_user(message):

    await unmute_user(message)

@dp.message_handler(lambda message: message.text.lower() == '!мут')

async def mut(message: types.Message):

    await mute_user(message)

@dp.message_handler(commands=['unmute'])

async def unmute_user(message: types.Message):

        user_id = message.from_user.id

        chat_id = message.chat.id

        # Получаем информацию о пользователе в чате

        chat_member = await bot.get_chat_member(chat_id, user_id)

        # Проверяем, является ли пользователь администратором или владельцем группы

        if chat_member.status in ['administrator', 'creator']:

            if message.reply_to_message:

                # Получаем информацию о пользователе, которого нужно размутить

                user = message.reply_to_message.from_user if message.reply_to_message else message.from_user

                # Размут пользователя

                await message.chat.restrict(user.id, can_send_messages=True, can_send_media_messages=True,

                                            can_send_other_messages=True, can_add_web_page_previews=True)

                # Отправляем сообщение о размуте пользователя

                user = f'<a href="tg://user?id={user.id}">{user.first_name}</a>'

                await message.reply(f"Пользователь <b>{user}</b> может писать в чате", parse_mode="HTML")

@dp.message_handler(commands=['mute'])

async def mute_user(message: types.Message):

        user_id = message.from_user.id

        chat_id = message.chat.id

        # Получаем информацию о пользователе в чате

        chat_member = await bot.get_chat_member(chat_id, user_id)

        # Проверяем, является ли пользователь администратором или владельцем группы

        if chat_member.status in ['administrator', 'creator']:

            if message.reply_to_message:

                # Парсим время из аргумента команды

                try:

                    minutes = int(message.get_args())

                except (ValueError, TypeError):

                    await message.reply("<b>Неправильный формат времени. Используйте:</b>\n/mute (время в минутах)",

                                        parse_mode="HTML")

                    return

                # Получаем информацию о пользователе, которому нужно дать мут

                user = message.reply_to_message.from_user if message.reply_to_message else message.from_user

                # Даем мут пользователю

                await message.chat.restrict(user.id, until_date=time.time() + 60 * minutes)

                # Отправляем сообщение об успешном муте

                user = f'<a href="tg://user?id={user.id}">{user.first_name}</a>'

                await message.reply(f"Пользователь <b>{user}</b> получил мут на {minutes} мин.", parse_mode="HTML")

@dp.message_handler(lambda message: message.text.lower() == '!бан' or message.text.lower() == '!ban' or message.text.lower() == '!забанить' or message.text.lower() == '!нахуй' or message.text.lower() == '!уйди')

async def ban_user(message):

        chat_id = message.chat.id

        user_id = message.from_user.id

        if chat_member.status in ['administrator', 'creator']:

            if message.reply_to_message:

                user_id = message.reply_to_message.from_user.id

                await bot.kick_chat_member(chat_id, user_id)

                await bot.send_message(chat_id, f"Пользователь <b>{message.reply_to_message.from_user.first_name}</b> забанен.\nПричина: {message.text.lower().split()[2]} {message.text.lower().split()[3]}",parse_mode="HTML")

            else:

                await bot.send_message(chat_id,

                                       "Вы должны ответить на сообщение пользователя, которого хотите забанить!")

@dp.message_handler(lambda message: message.text.lower() == 'разбан')

async def unban_user(message):

        user_id = message.from_user.id

        chat_id = message.chat.id

        chat_member = await bot.get_chat_member(chat_id, user_id)

        # Проверяем, является ли пользователь администратором или владельцем группы

        if chat_member.status in ['administrator', 'creator']:

            if message.reply_to_message:

                # Получаем информацию о пользователе, которого нужно размутить

                user = message.reply_to_message.from_user if message.reply_to_message else message.from_user

                # Размут пользователя

                await message.chat.restrict(user.id, can_send_messages=True, can_send_media_messages=True,

                                            can_send_other_messages=True, can_add_web_page_previews=True)

                # Отправляем сообщение о размуте пользователя

                user = f'<a href="tg://user?id={user.id}">{user.first_name}</a>'

                await message.reply(f"Пользователь <b>{user}</b> разбанен", parse_mode="HTML")





@dp.message_handler(lambda message: 'розыгрыш' in message.text.lower())

async def free(message: types.Message):

    user_id = message.from_user.id

    chat_id = message.chat.id

    chat_member = await bot.get_chat_member(chat_id, user_id)

    # Проверяем, является ли пользователь администратором или владельцем группы

    if chat_member.status not in ['administrator', 'creator']:

        if int(message.text.split()[1]) <= 25000:

            log = []

            cur.execute('UPDATE users SET coin=coin-? WHERE tgid=?', (message.text.split()[1], message.from_user.id))

            cur.execute('SELECT * FROM users ORDER BY RANDOM() LIMIT 1000')

            random_users = cur.fetchall()

            for user in random_users:

                user_id = user[0]

                current_coin = user[3]

                random_coin_increase = random.randint(0, 20)

                new_coin = current_coin + random_coin_increase

                log.append(f'{user.first_name} выиграл random_coin_increase\n')

                cur.execute('UPDATE users SET coin = ? WHERE tgid = ?', (new_coin, user_id))

            await message.reply(f"Раздача завершена \n {log}", parse_mode="HTML")

        else:

            await message.reply("Раздачи более 25000 только для администраторов", parse_mode="HTML")

    else:

        log = []

        cur.execute('UPDATE users SET coin=coin-? WHERE tgid=?', (message.text.split()[1], message.from_user.id))

        cur.execute('SELECT * FROM users ORDER BY RANDOM() LIMIT 1000')

        random_users = cur.fetchall()

        for user in random_users:

            user_id = user[0]

            current_coin = user[3]

            random_coin_increase = random.randint(0, 20)

            new_coin = current_coin + random_coin_increase

            log.append(f'{user.first_name} выиграл random_coin_increase\n')

            cur.execute('UPDATE users SET coin = ? WHERE tgid = ?', (new_coin, user_id))

        await message.reply(f"Раздача завершена \n {log}", parse_mode="HTML")









@dp.message_handler()

async def text(message: types.Message):

    user_id = message.from_user.id

    chat_id = message.chat.id

    # Ищем пользователя в базе данных

    cur.execute('SELECT * FROM users WHERE tgid = ?', (user_id,))

    user = cur.fetchone()

    if not user:

        nickname = message.from_user.first_name

        if len(nickname) > 10:

            nickname = nickname[:10] + '.'

        cur.execute(

            'INSERT INTO users (tgid, name, full,coin,win,loose) VALUES (?, ?, ?, ?, ?, ?)',

            (message.from_user.id, nickname, '1970-01-01T00:00:00', 0, 0, 0))

        conn.commit()



    if random.random() <= 0.5:

        await asyncio.sleep(1)

    else:

        await asyncio.sleep(1.5)



    mes = message.text.lower()



    if mes == 'б' or mes == "баланс":

        if chat_id in bets and user_id in bets[chat_id]:

            user_bets = bets[chat_id][user_id]

            total_returned = 0

            for amount, _bet in user_bets:

                total_returned += amount

            await message.answer(f'{user[3]}+{total_returned}')

        elif user[3] == 0:

            mrk = InlineKeyboardMarkup()

            mrk.add(InlineKeyboardButton('Бонус', url=f'https://t.me/BellaCiaoWinBot?start={user_id}'))

            await message.answer(f'{user[3]}',reply_markup=mrk)

        else:

            await message.answer(f'{user[3]}')

    if mes == 'профиль' or mes == '!профиль':

        usern = message.from_user.full_name

        await message.answer(

            f'{usern}\nМонет: {user[3]}\nВыиграно: {user[4]}\nПроиграно: {user[5]}\nМакс. ставка: {user[8]}\nМакс. выигрыш: {user[7]}\nVipCoin: {user[6]}',

            parse_mode='html')

    if message.text == '📋Профиль':

        usern = message.from_user.full_name

        await message.answer(

            f'{usern}\nМонет: {user[3]}\nВыиграно: {user[4]}\nПроиграно: {user[5]}\nМакс. ставка: {user[8]}\nМакс. выигрыш: {user[7]}\nVipCoin: {user[6]}',

            parse_mode='html')

    if message.text == '🌐Ссылки':

        await message.answer('сюды чаты')

    if message.text == '🛒Магазин':

        await message.answer('Дорабатывается')

    if mes == '!чаты' or mes == 'чаты' or mes == 'ссылки':

        await message.answer('сюды чаты ')

    if mes == '!бонус' or mes == 'бонус':

        if message.chat.type == 'private':

            user_id = message.from_user.id

            try:

                member = await bot.get_chat_member(chat_id="@end_soft", user_id=user_id)

                if member.status in ["creator", "administrator", "member"]:

                    mrk = InlineKeyboardMarkup()

                    mrk.add(InlineKeyboardButton('Получить бонус', callback_data='bonus'))

                    await message.reply("Ежедневный бонус:", reply_markup=mrk)

                else:

                    await message.reply("Чтобы использовать бонус, подпишитесь на канал:\nhttps://t.me/end_soft")

            except Exception:

                await message.reply("Произошла ошибка!")

        else:

            await asyncio.sleep(2)

            await message.answer('Бонус можно получить только в лс!')



    if mes == '!топ':

        mrk = InlineKeyboardMarkup(row_width=1)

        mrk.add(InlineKeyboardButton('Богатеи',callback_data='topcoin'),InlineKeyboardButton('Рулетка',callback_data='topruletka'))

        await message.answer('Какой топ вас интересует?', reply_markup=mrk)



buttonon = "humans\n\n"

@dp.callback_query_handler()

async def button(callback_query:types.CallbackQuery):

    await asyncio.sleep(0.5)

    global buttonon, bets, logs, rchats, winlist, betlist, winnings

    cd = callback_query.data

    user_id = callback_query.from_user.id

    chat_id = callback_query.message.chat.id



    if f'{user_id}' in buttonon:

        return

    buttonon+=f'{user_id}\n'

    try:

        cur.execute('SELECT * FROM users WHERE tgid=?', (user_id,))

        user = cur.fetchone()



        if user[10] == 1:

            return



        f'<a href="tg://user?id={user_id}">{user[1]}</a>'

        message_id = callback_query.message.message_id

        '{:,.0f}'.format(user[3]).replace(',', '.')

        win = '{:,.0f}'.format(user[4]).replace(',', '.')

        '{:,.0f}'.format(user[5]).replace(',', '.')



        if cd == 'bonus':

            # Получаем время последнего использования команды

            last_bonus_time = datetime.datetime.fromisoformat(user[2])

            time_since_last_bonus = datetime.datetime.now() - last_bonus_time

            if time_since_last_bonus.total_seconds() < 43200:

                time_left = datetime.timedelta(seconds=43200 - time_since_last_bonus.total_seconds())

                await bot.edit_message_text(chat_id=chat_id, message_id=message_id,

                                            text=f'<i>Вы уже использовали бонус. Следующий бонус будет доступен через</i> <code>{time_left}</code>',

                                            parse_mode='html')

            else:

                # Обновляем время последнего использования команды в базе данных

                cur.execute('UPDATE users SET full = ?, coin=coin+2500 WHERE tgid = ?',

                            (datetime.datetime.now().isoformat(), callback_query.from_user.id))

                conn.commit()

                await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text='+2500')



        if cd == 'go':

            user_id = callback_query.from_user.id

            # Ищем пользователя в базе данных

            cur.execute('SELECT * FROM users WHERE tgid = ?', (user_id,))

            user = cur.fetchone()

            if not user:

                nickname = callback_query.from_user.first_name

                if len(nickname) > 10:

                    nickname = nickname[:10] + '.'

                cur.execute(

                    'INSERT INTO users (tgid, name, full,coin,win,loose) VALUES (?, ?, ?, ?, ?, ?)',

                    (callback_query.from_user.id, nickname, '1970-01-01T00:00:00', 0, 0, 0))

                conn.commit()



            global bets, logs, rchats, winlist, betlist, winnings

            chat_id = callback_query.message.chat.id

            user_id = callback_query.from_user.id

            if chat_id not in chat_semaphores3:

                chat_semaphores3[chat_id] = rosemaphore

            # Используем соответствующий семафор для текущего чата

            async with (chat_semaphores3[chat_id]):

                if f"{chat_id}" in rchats:

                    if chat_id in bets and user_id in bets[chat_id]:

                        if random.random() <= 0.3:

                            # Отправить сообщение пользователю о том, что нужно подождать

                            m = await callback_query.message.answer(f"{callback_query.from_user.first_name} крутит (через 10 сек.)")

                            await asyncio.sleep(10)

                            await m.delete()

                        elif random.random() <= 0.6:

                            # Отправить сообщение пользователю о том, что нужно подождать

                            m = await callback_query.message.answer(f"{callback_query.from_user.first_name} крутит (через 15 сек.)")

                            await asyncio.sleep(15)

                            await m.delete()

                        else:

                            m = await callback_query.message.answer(f"{callback_query.from_user.first_name} крутит (через 5 сек.)")

                            await asyncio.sleep(5)

                            await m.delete()

                        if random.random() <= 0.4:

                            gif_message = await callback_query.message.answer_video(video=types.InputFile("video2.mp4"))

                            await asyncio.sleep(5)

                            # Удаление гиф-анимации

                            await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=gif_message.message_id)

                        else:

                            gif_message = await callback_query.message.answer_video(video=types.InputFile("video1.mp4"))

                            await asyncio.sleep(5)

                            # Удаление гиф-анимации

                            await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=gif_message.message_id)

                        if random.random() <= 0.3:

                            if random.random() <= 0.1:

                                win = WINNINGS['0']

                            else:

                                win = random.choice(WINNINGS["красное🔴"] + WINNINGS["чёрное⚫️"])

                        else:

                            win = random.choice(WINNINGS["красное🔴"] + WINNINGS["чёрное⚫️"])

                        winlist = '\n'

                        betlist = '\n'

                        for user_id, user_bets in bets.get(chat_id, {}).items():

                            cur.execute('SELECT * FROM users WHERE tgid = ?', (user_id,))

                            user = cur.fetchone()

                            name = f'<a href="tg://user?id={user_id}">{user[1]}</a>'

                            for amount, bet in user_bets:

                                if win in WINNINGS[bet]:

                                    if bet == 'красное🔴' or bet == 'чёрное⚫️':

                                        winnings = amount * 2

                                        cur.execute('UPDATE users SET coin=coin+? WHERE tgid=?', (winnings, user_id))

                                        conn.commit()

                                    if bet == '0':

                                        winnings = amount * 35

                                        cur.execute("UPDATE users SET coin=coin+? WHERE tgid=?", (winnings, user_id))

                                        conn.commit()

                                    if '-' in bet:

                                        if all(number not in win for number in range(int(bet.split('-')[0]), int(bet.split('-')[1]))):

                                            return

                                        winnings = amount * 9

                                        cur.execute("UPDATE users SET coin=coin+? WHERE tgid=?", (winnings, user_id))

                                        conn.commit()

                                    if bet in win:

                                        winnings = amount * 12

                                        cur.execute("UPDATE users SET coin=coin+? WHERE tgid=?", (winnings, user_id))

                                        conn.commit()



                                    cur.execute('SELECT * FROM users WHERE tgid = ?', (user_id,))

                                    user = cur.fetchone()

                                    cur.execute('UPDATE users SET win=win+1 WHERE tgid=?', (user_id,))

                                    if user[7] < winnings:

                                        cur.execute('UPDATE users SET fullwin=? WHERE tgid=?', (winnings, user_id))

                                    if user[8] < amount:

                                        cur.execute('UPDATE users SET fullbet=? WHERE tgid=?', (amount, user_id))

                                    winlist += f'{name} выиграл {winnings} на {bet}\n'

                                    history.append(winlist)

                                    betlist += f'{user[1]} {amount} на {bet}\n'

                                    conn.commit()

                                else:

                                    if win == '0':

                                        cur.execute("UPDATE users SET coin=coin+? WHERE tgid=?",

                                                    (int(amount / 2), user_id))

                                        winlist += f'{name} выиграл {int(amount / 2)} на {bet}\n'

                                        history.append(winlist)

                                    cur.execute('UPDATE users SET loose=loose+1 WHERE tgid=?', (user_id,))

                                    if user[8] > amount:

                                        cur.execute('UPDATE users SET fullbet=? WHERE tgid=?', (amount, user_id))

                                    betlist += f'{user[1]} {amount} на {bet}\n'

                                    conn.commit()



                        if winlist == f'Рулетка: {win}\n':

                            await callback_query.message.answer(f'Рулетка: {win}{betlist}', parse_mode='HTML')

                        else:

                            await callback_query.message.answer(f"Рулетка: {win}{betlist}{winlist}", parse_mode='HTML')

                        if chat_id not in logs:

                            logs[chat_id] = ""

                        log_lines = logs[chat_id].split('\n')[-40:]

                        if len(log_lines) >= 35:

                            logs[chat_id] = ""

                        if chat_id not in logs:

                            logs[chat_id] = ""

                        rchats = rchats.replace(f"{chat_id}", "")

                        logs[chat_id] += f'\n{win}'

                        bets[chat_id] = {}

                    else:

                        await callback_query.message.answer('У вас нет активных ставок!')

                else:

                    await asyncio.sleep(5)

                    return

                await asyncio.sleep(5)



        if cd == 'povtor':

            if chat_id in betspov and user_id in betspov[chat_id]:

                user_bets = betspov[chat_id][user_id]

                response = '\n'

                be = 0

                for amount, bet in user_bets:

                    be += amount

                    response += f"{amount} на {bet}\n"

                cur.execute('SELECT * FROM users WHERE tgid=?', (user_id,))

                user = cur.fetchone()

                if be > user[3]:

                    await callback_query.message.answer(f'{callback_query.from_user.first_name}, недостаточно монет!')

                    return

                if chat_id in bets and user_id in bets[chat_id]:

                    if bets[chat_id][user_id] == betspov[chat_id][user_id]:

                        await callback_query.message.answer(f'{callback_query.from_user.first_name}, ваши ставки аналогичны предыдущим!')

                        return

                bets[chat_id][user_id] = betspov[chat_id][user_id]

                await callback_query.message.answer(f"{callback_query.from_user.first_name}\n{response}")

            else:

                await callback_query.message.answer(f'{callback_query.from_user.first_name}, у вас не было активных ставок')

            await asyncio.sleep(3)



        if cd == 'udvoit':

            if chat_id in bets and user_id in bets[chat_id]:

                user_bets = bets[chat_id][user_id]

                total_amount = sum([amount for amount, _ in user_bets])

                if total_amount > 0:

                    cur.execute('SELECT coin FROM users WHERE tgid=?', (callback_query.message.from_user.id,))

                    row = cur.fetchone()

                    coins = row[0]

                    if total_amount < coins:

                        for i in range(len(user_bets)):

                            user_bets[i] = (2 * user_bets[i][0], user_bets[i][1])

                        cur.execute('UPDATE users SET coin=? WHERE tgid=?', (coins - total_amount, user_id))

                        conn.commit()

                        await callback_query.message.answer(f"{callback_query.from_user.first_name}. Все ставки удвоены!")

                    else:

                        await callback_query.message.answer(f"{callback_query.from_user.first_name}. Недостаточно монет для удвоения ставок.")

            else:

                await callback_query.message.answer(f'{callback_query.from_user.first_name}. Ставок нет!')

            await asyncio.sleep(3)



        if cd == 'vabankRed':

            if conn.in_transaction:

                return

            cur.execute('BEGIN TRANSACTION')

            if f"{chat_id}" in rchats:

                    bet_message = ""

                    bet_totals = {}

                    amount = user[0]

                    bet = 'квб'

                    if bet not in BETS and '-' not in bet:

                        await callback_query.message.answer(

                            f"{callback_query.from_user.first_name}. Неверная ставка! Используйте только к,ч,1-3,4-6,7-9,10-12 или же все ставки от 0 до 12",

                            parse_mode="HTML")

                        return

                    if int(amount) > user[3]:

                        await callback_query.message.answer(f"{callback_query.from_user.first_name}. Недостаточно монет на балансе!")

                        return

                    if chat_id in bets:

                        if user_id in bets[chat_id]:

                            for i, (amt, b) in enumerate(bets[chat_id][user_id]):

                                if b == BETS[bet]:

                                    bets[chat_id][user_id][i] = (amt + int(amount), b)

                                    break

                            else:

                                bets[chat_id][user_id].append((int(amount), BETS[bet]))

                        else:

                            bets[chat_id][user_id] = [(int(amount), BETS[bet])]

                    else:

                        bets[chat_id] = {user_id: [(int(amount), BETS[bet])]}

                    cur.execute('UPDATE users SET coin=coin-? WHERE tgid=?', (int(amount), user_id))

                    conn.commit()

                    if BETS[bet] in bet_totals:

                        bet_totals[BETS[bet]] += int(amount)

                    else:

                        bet_totals[BETS[bet]] = int(amount)

                    for bet, total in bet_totals.items():

                        name = f'<a href="tg://user?id={user_id}">{callback_query.from_user.full_name}</a>'

                        bet_message += f"Ставка принята: {name} {total} Volt на {bet}\n"

                    if chat_id not in betspov:

                        betspov[chat_id] = {}

                    if user_id not in betspov[chat_id]:

                        betspov[chat_id][user_id] = 0

                    betspov[chat_id][user_id] = bets[chat_id][user_id]

                    await callback_query.message.answer(f"{bet_message}", parse_mode='HTML')

            else:

                return

            conn.commit()

        if cd == 'vabankBlack':

            if conn.in_transaction:

                return

            cur.execute('BEGIN TRANSACTION')

            if f"{chat_id}" in rchats:

                    bet_message = ""

                    bet_totals = {}

                    amount = user[3]

                    bet = 'чвб'

                    if bet not in BETS and '-' not in bet:

                        await callback_query.message.answer(

                            f"{callback_query.from_user.first_name}. Неверная ставка! Используйте только к,ч,1-3,4-6,7-9,10-12 или же все ставки от 0 до 12",

                            parse_mode="HTML")

                        return

                    if int(amount) > user[3]:

                        await callback_query.message.answer(f"{callback_query.from_user.first_name}. Недостаточно монет на балансе!")

                        return

                    if chat_id in bets:

                        if user_id in bets[chat_id]:

                            for i, (amt, b) in enumerate(bets[chat_id][user_id]):

                                if b == BETS[bet]:

                                    bets[chat_id][user_id][i] = (amt + int(amount), b)

                                    break

                            else:

                                bets[chat_id][user_id].append((int(amount), BETS[bet]))

                        else:

                            bets[chat_id][user_id] = [(int(amount), BETS[bet])]

                    else:

                        bets[chat_id] = {user_id: [(int(amount), BETS[bet])]}

                    cur.execute('UPDATE users SET coin=coin-? WHERE tgid=?', (int(amount), user_id))

                    conn.commit()

                    if BETS[bet] in bet_totals:

                        bet_totals[BETS[bet]] += int(amount)

                    else:

                        bet_totals[BETS[bet]] = int(amount)

                    for bet, total in bet_totals.items():

                        name = f'<a href="tg://user?id={user_id}">{callback_query.from_user.full_name}</a>'

                        bet_message += f"Ставка принята: {name} {total} Volt на {bet}\n"

                    if chat_id not in betspov:

                        betspov[chat_id] = {}

                    if user_id not in betspov[chat_id]:

                        betspov[chat_id][user_id] = 0

                    betspov[chat_id][user_id] = bets[chat_id][user_id]

                    await callback_query.message.answer(f"{bet_message}", parse_mode='HTML')

            else:

                return

            conn.commit()



        if cd == '5red':

            if conn.in_transaction:

                return

            cur.execute('BEGIN TRANSACTION')

            if f"{chat_id}" in rchats:

                    bet_message = ""

                    bet_totals = {}

                    amount = 5

                    bet = 'к'

                    if bet not in BETS and '-' not in bet:

                        await callback_query.message.answer(

                            f"{callback_query.from_user.first_name}. Неверная ставка! Используйте только к,ч,1-3,4-6,7-9,10-12 или же все ставки от 0 до 12",

                            parse_mode="HTML")

                        return

                    if int(amount) > user[3]:

                        await callback_query.message.answer(f"{callback_query.from_user.first_name}. Недостаточно монет на балансе!")

                        return

                    if chat_id in bets:

                        if user_id in bets[chat_id]:

                            for i, (amt, b) in enumerate(bets[chat_id][user_id]):

                                if b == BETS[bet]:

                                    bets[chat_id][user_id][i] = (amt + int(amount), b)

                                    break

                            else:

                                bets[chat_id][user_id].append((int(amount), BETS[bet]))

                        else:

                            bets[chat_id][user_id] = [(int(amount), BETS[bet])]

                    else:

                        bets[chat_id] = {user_id: [(int(amount), BETS[bet])]}

                    cur.execute('UPDATE users SET coin=coin-? WHERE tgid=?', (int(amount), user_id))

                    conn.commit()

                    if BETS[bet] in bet_totals:

                        bet_totals[BETS[bet]] += int(amount)

                    else:

                        bet_totals[BETS[bet]] = int(amount)

                    for bet, total in bet_totals.items():

                        name = f'<a href="tg://user?id={user_id}">{callback_query.from_user.full_name}</a>'

                        bet_message += f"Ставка принята: {name} {total} Volt на {bet}\n"

                    if chat_id not in betspov:

                        betspov[chat_id] = {}

                    if user_id not in betspov[chat_id]:

                        betspov[chat_id][user_id] = 0

                    betspov[chat_id][user_id] = bets[chat_id][user_id]

                    await callback_query.message.answer(f"{bet_message}", parse_mode='HTML')

            else:

                return

            conn.commit()

        if cd == '5black':

            if conn.in_transaction:

                return

            cur.execute('BEGIN TRANSACTION')

            if f"{chat_id}" in rchats:

                    bet_message = ""

                    bet_totals = {}

                    amount = 5

                    bet = 'ч'

                    if bet not in BETS and '-' not in bet:

                        await callback_query.message.answer(

                            f"{callback_query.from_user.first_name}. Неверная ставка! Используйте только к,ч,1-3,4-6,7-9,10-12 или же все ставки от 0 до 12",

                            parse_mode="HTML")

                        return

                    if int(amount) > user[3]:

                        await callback_query.message.answer(f"{callback_query.from_user.first_name}. Недостаточно монет на балансе!")

                        return

                    if chat_id in bets:

                        if user_id in bets[chat_id]:

                            for i, (amt, b) in enumerate(bets[chat_id][user_id]):

                                if b == BETS[bet]:

                                    bets[chat_id][user_id][i] = (amt + int(amount), b)

                                    break

                            else:

                                bets[chat_id][user_id].append((int(amount), BETS[bet]))

                        else:

                            bets[chat_id][user_id] = [(int(amount), BETS[bet])]

                    else:

                        bets[chat_id] = {user_id: [(int(amount), BETS[bet])]}

                    cur.execute('UPDATE users SET coin=coin-? WHERE tgid=?', (int(amount), user_id))

                    conn.commit()

                    if BETS[bet] in bet_totals:

                        bet_totals[BETS[bet]] += int(amount)

                    else:

                        bet_totals[BETS[bet]] = int(amount)

                    for bet, total in bet_totals.items():

                        name = f'<a href="tg://user?id={user_id}">{callback_query.from_user.full_name}</a>'

                        bet_message += f"Ставка принята: {name} {total} Volt на {bet}\n"

                    if chat_id not in betspov:

                        betspov[chat_id] = {}

                    if user_id not in betspov[chat_id]:

                        betspov[chat_id][user_id] = 0

                    betspov[chat_id][user_id] = bets[chat_id][user_id]

                    await callback_query.message.answer(f"{bet_message}", parse_mode='HTML')

            else:

                return

            conn.commit()

        if cd == '5zero':

            if conn.in_transaction:

                return

            cur.execute('BEGIN TRANSACTION')

            if f"{chat_id}" in rchats:

                    bet_message = ""

                    bet_totals = {}

                    amount = 5

                    bet = '0'

                    if bet not in BETS and '-' not in bet:

                        await callback_query.message.answer(

                            f"{callback_query.from_user.first_name}. Неверная ставка! Используйте только к,ч,1-3,4-6,7-9,10-12 или же все ставки от 0 до 12",

                            parse_mode="HTML")

                        return

                    if int(amount) > user[3]:

                        await callback_query.message.answer(f"{callback_query.from_user.first_name}. Недостаточно монет на балансе!")

                        return

                    if chat_id in bets:

                        if user_id in bets[chat_id]:

                            for i, (amt, b) in enumerate(bets[chat_id][user_id]):

                                if b == BETS[bet]:

                                    bets[chat_id][user_id][i] = (amt + int(amount), b)

                                    break

                            else:

                                bets[chat_id][user_id].append((int(amount), BETS[bet]))

                        else:

                            bets[chat_id][user_id] = [(int(amount), BETS[bet])]

                    else:

                        bets[chat_id] = {user_id: [(int(amount), BETS[bet])]}

                    cur.execute('UPDATE users SET coin=coin-? WHERE tgid=?', (int(amount), user_id))

                    conn.commit()

                    if BETS[bet] in bet_totals:

                        bet_totals[BETS[bet]] += int(amount)

                    else:

                        bet_totals[BETS[bet]] = int(amount)

                    for bet, total in bet_totals.items():

                        name = f'<a href="tg://user?id={user_id}">{callback_query.from_user.full_name}</a>'

                        bet_message += f"Ставка принята: {name} {total} Volt на {bet}\n"

                    if chat_id not in betspov:

                        betspov[chat_id] = {}

                    if user_id not in betspov[chat_id]:

                        betspov[chat_id][user_id] = 0

                    betspov[chat_id][user_id] = bets[chat_id][user_id]

                    await callback_query.message.answer(f"{bet_message}", parse_mode='HTML')

            else:

                return

            conn.commit()

        if cd == '13':

            if conn.in_transaction:

                return

            cur.execute('BEGIN TRANSACTION')

            if f"{chat_id}" in rchats:

                    bet_message = ""

                    bet_totals = {}

                    amount = 5

                    bet = '1-3'

                    if bet not in BETS and '-' not in bet:

                        await callback_query.message.answer(

                            f"{callback_query.from_user.first_name}. Неверная ставка! Используйте только к,ч,1-3,4-6,7-9,10-12 или же все ставки от 0 до 12",

                            parse_mode="HTML")

                        return

                    if int(amount) > user[3]:

                        await callback_query.message.answer(f"{callback_query.from_user.first_name}. Недостаточно монет на балансе!")

                        return

                    if chat_id in bets:

                        if user_id in bets[chat_id]:

                            for i, (amt, b) in enumerate(bets[chat_id][user_id]):

                                if b == BETS[bet]:

                                    bets[chat_id][user_id][i] = (amt + int(amount), b)

                                    break

                            else:

                                bets[chat_id][user_id].append((int(amount), BETS[bet]))

                        else:

                            bets[chat_id][user_id] = [(int(amount), BETS[bet])]

                    else:

                        bets[chat_id] = {user_id: [(int(amount), BETS[bet])]}

                    cur.execute('UPDATE users SET coin=coin-? WHERE tgid=?', (int(amount), user_id))

                    conn.commit()

                    if BETS[bet] in bet_totals:

                        bet_totals[BETS[bet]] += int(amount)

                    else:

                        bet_totals[BETS[bet]] = int(amount)

                    for bet, total in bet_totals.items():

                        name = f'<a href="tg://user?id={user_id}">{callback_query.from_user.full_name}</a>'

                        bet_message += f"Ставка принята: {name} {total} Volt на {bet}\n"

                    if chat_id not in betspov:

                        betspov[chat_id] = {}

                    if user_id not in betspov[chat_id]:

                        betspov[chat_id][user_id] = 0

                    betspov[chat_id][user_id] = bets[chat_id][user_id]

                    await callback_query.message.answer(f"{bet_message}", parse_mode='HTML')

            else:

                return

            conn.commit()

        if cd == '46':

            if conn.in_transaction:

                return

            cur.execute('BEGIN TRANSACTION')

            if f"{chat_id}" in rchats:

                    bet_message = ""

                    bet_totals = {}

                    amount = 5

                    bet = '4-6'

                    if bet not in BETS and '-' not in bet:

                        await callback_query.message.answer(

                            f"{callback_query.from_user.first_name}. Неверная ставка! Используйте только к,ч,1-3,4-6,7-9,10-12 или же все ставки от 0 до 12",

                            parse_mode="HTML")

                        return

                    if int(amount) > user[3]:

                        await callback_query.message.answer(f"{callback_query.from_user.first_name}. Недостаточно монет на балансе!")

                        return

                    if chat_id in bets:

                        if user_id in bets[chat_id]:

                            for i, (amt, b) in enumerate(bets[chat_id][user_id]):

                                if b == BETS[bet]:

                                    bets[chat_id][user_id][i] = (amt + int(amount), b)

                                    break

                            else:

                                bets[chat_id][user_id].append((int(amount), BETS[bet]))

                        else:

                            bets[chat_id][user_id] = [(int(amount), BETS[bet])]

                    else:

                        bets[chat_id] = {user_id: [(int(amount), BETS[bet])]}

                    cur.execute('UPDATE users SET coin=coin-? WHERE tgid=?', (int(amount), user_id))

                    conn.commit()

                    if BETS[bet] in bet_totals:

                        bet_totals[BETS[bet]] += int(amount)

                    else:

                        bet_totals[BETS[bet]] = int(amount)

                    for bet, total in bet_totals.items():

                        name = f'<a href="tg://user?id={user_id}">{callback_query.from_user.full_name}</a>'

                        bet_message += f"Ставка принята: {name} {total} Volt на {bet}\n"

                    if chat_id not in betspov:

                        betspov[chat_id] = {}

                    if user_id not in betspov[chat_id]:

                        betspov[chat_id][user_id] = 0

                    betspov[chat_id][user_id] = bets[chat_id][user_id]

                    await callback_query.message.answer(f"{bet_message}", parse_mode='HTML')

            else:

                return

            conn.commit()

        if cd == '79':

            if conn.in_transaction:

                return

            cur.execute('BEGIN TRANSACTION')

            if f"{chat_id}" in rchats:

                    bet_message = ""

                    bet_totals = {}

                    amount = 5

                    bet = '7-9'

                    if bet not in BETS and '-' not in bet:

                        await callback_query.message.answer(

                            f"{callback_query.from_user.first_name}. Неверная ставка! Используйте только к,ч,1-3,4-6,7-9,10-12 или же все ставки от 0 до 12",

                            parse_mode="HTML")

                        return

                    if int(amount) > user[3]:

                        await callback_query.message.answer(f"{callback_query.from_user.first_name}. Недостаточно монет на балансе!")

                        return

                    if chat_id in bets:

                        if user_id in bets[chat_id]:

                            for i, (amt, b) in enumerate(bets[chat_id][user_id]):

                                if b == BETS[bet]:

                                    bets[chat_id][user_id][i] = (amt + int(amount), b)

                                    break

                            else:

                                bets[chat_id][user_id].append((int(amount), BETS[bet]))

                        else:

                            bets[chat_id][user_id] = [(int(amount), BETS[bet])]

                    else:

                        bets[chat_id] = {user_id: [(int(amount), BETS[bet])]}

                    cur.execute('UPDATE users SET coin=coin-? WHERE tgid=?', (int(amount), user_id))

                    conn.commit()

                    if BETS[bet] in bet_totals:

                        bet_totals[BETS[bet]] += int(amount)

                    else:

                        bet_totals[BETS[bet]] = int(amount)

                    for bet, total in bet_totals.items():

                        name = f'<a href="tg://user?id={user_id}">{callback_query.from_user.full_name}</a>'

                        bet_message += f"Ставка принята: {name} {total} Volt на {bet}\n"

                    if chat_id not in betspov:

                        betspov[chat_id] = {}

                    if user_id not in betspov[chat_id]:

                        betspov[chat_id][user_id] = 0

                    betspov[chat_id][user_id] = bets[chat_id][user_id]

                    await callback_query.message.answer(f"{bet_message}", parse_mode='HTML')

            else:

                return

            conn.commit()

        if cd == '1012':

            if conn.in_transaction:

                return

            cur.execute('BEGIN TRANSACTION')

            if f"{chat_id}" in rchats:

                    bet_message = ""

                    bet_totals = {}

                    amount = 5

                    bet = '10-12'

                    if bet not in BETS and '-' not in bet:

                        await callback_query.message.answer(

                            f"{callback_query.from_user.first_name}. Неверная ставка! Используйте только к,ч,1-3,4-6,7-9,10-12 или же все ставки от 0 до 12",

                            parse_mode="HTML")

                        return

                    if int(amount) > user[3]:

                        await callback_query.message.answer(f"{callback_query.from_user.first_name}. Недостаточно монет на балансе!")

                        return

                    if chat_id in bets:

                        if user_id in bets[chat_id]:

                            for i, (amt, b) in enumerate(bets[chat_id][user_id]):

                                if b == BETS[bet]:

                                    bets[chat_id][user_id][i] = (amt + int(amount), b)

                                    break

                            else:

                                bets[chat_id][user_id].append((int(amount), BETS[bet]))

                        else:

                            bets[chat_id][user_id] = [(int(amount), BETS[bet])]

                    else:

                        bets[chat_id] = {user_id: [(int(amount), BETS[bet])]}

                    cur.execute('UPDATE users SET coin=coin-? WHERE tgid=?', (int(amount), user_id))

                    conn.commit()

                    if BETS[bet] in bet_totals:

                        bet_totals[BETS[bet]] += int(amount)

                    else:

                        bet_totals[BETS[bet]] = int(amount)

                    for bet, total in bet_totals.items():

                        name = f'<a href="tg://user?id={user_id}">{callback_query.from_user.full_name}</a>'

                        bet_message += f"Ставка принята: {name} {total} Volt на {bet}\n"

                    if chat_id not in betspov:

                        betspov[chat_id] = {}

                    if user_id not in betspov[chat_id]:

                        betspov[chat_id][user_id] = 0

                    betspov[chat_id][user_id] = bets[chat_id][user_id]

                    await callback_query.message.answer(f"{bet_message}", parse_mode='HTML')

            else:

                return

            conn.commit()



        if cd == 'topcoin':

            await asyncio.sleep(3)

            cur.execute('SELECT name, coin FROM users ORDER BY coin DESC LIMIT 30')

            users = cur.fetchall()

            text = 'Топ богатеев\n'

            for i, user in enumerate(users):

                nickname = user[0]

                if len(nickname) > 10:

                    nickname = nickname[:10] + '..'

                slotg = user[1]

                # Форматируем баланс с разделителем точки

                text += f'{i + 1}. {nickname} - {slotg}\n'

            await bot.edit_message_text(chat_id=chat_id, message_id=message_id,

                                        text=f'{text}')

        if cd == 'topruletka':

            mrk = InlineKeyboardMarkup()

            mrk.add(InlineKeyboardButton('Выиграно',callback_data='topwin'),InlineKeyboardButton('Проиграно',callback_data='toploose'),InlineKeyboardButton('Макс.ставка',callback_data='maxbet'),InlineKeyboardButton('Макс.выиграш',callback_data='maxwin'))

            await bot.edit_message_text(chat_id=chat_id, message_id=message_id,

                                        text='Какой топ вас интересует?',reply_markup=mrk)

        if cd == 'topwin':

            await asyncio.sleep(3)

            cur.execute('SELECT name, win FROM users ORDER BY win DESC LIMIT 10')

            users = cur.fetchall()

            text = 'Топ по выиграшам\n'

            for i, user in enumerate(users):

                nickname = user[0]

                if len(nickname) > 10:

                    nickname = nickname[:10] + '..'

                slotg = user[1]

                # Форматируем баланс с разделителем точки

                text += f'{i + 1}. {nickname} - {slotg}\n'

            await bot.edit_message_text(chat_id=chat_id, message_id=message_id,

                                        text=f'{text}')

        if cd == 'toploose':

            await asyncio.sleep(3)

            cur.execute('SELECT name, loose FROM users ORDER BY loose DESC LIMIT 10')

            users = cur.fetchall()

            text = 'Топ по проигрышам\n'

            for i, user in enumerate(users):

                nickname = user[0]

                if len(nickname) > 10:

                    nickname = nickname[:10] + '..'

                slotg = user[1]

                # Форматируем баланс с разделителем точки

                text += f'{i + 1}. {nickname} - {slotg}\n'

            await bot.edit_message_text(chat_id=chat_id, message_id=message_id,

                                        text=f'{text}')

        if cd == 'maxbet':

            await asyncio.sleep(3)

            cur.execute('SELECT name, fullbet FROM users ORDER BY fullbet DESC LIMIT 10')

            users = cur.fetchall()

            text = 'Топ по высоким ставкам\n'

            for i, user in enumerate(users):

                nickname = user[0]

                if len(nickname) > 10:

                    nickname = nickname[:10] + '..'

                slotg = user[1]

                # Форматируем баланс с разделителем точки

                text += f'{i + 1}. {nickname} - {slotg}\n'

            await bot.edit_message_text(chat_id=chat_id, message_id=message_id,

                                        text=f'{text}')

        if cd == 'maxwin':

            await asyncio.sleep(3)

            cur.execute('SELECT name, fullwin FROM users ORDER BY fullwin DESC LIMIT 10')

            users = cur.fetchall()

            text = 'Топ по высоким выиграшам\n'

            for i, user in enumerate(users):

                nickname = user[0]

                if len(nickname) > 10:

                    nickname = nickname[:10] + '..'

                slotg = user[1]

                # Форматируем баланс с разделителем точки

                text += f'{i + 1}. {nickname} - {slotg}\n'

            await bot.edit_message_text(chat_id=chat_id, message_id=message_id,

                                        text=f'{text}')



    except Exception as e:

        print("Произошла ошибка:")

        print(e)

        await bot.answer_callback_query(callback_query.id, text='Не нажимайте так часто на кнопку!')

        await asyncio.sleep(3)

    finally:

        await asyncio.sleep(0.5)

        buttonon = buttonon.replace(f'{user_id}', '')

        conn.commit()



keep_alive.keep_alive()



if __name__ == '__main__':

    executor.start_polling(dp, skip_updates=True)

    # Закрываем курсор и соединение с базой данных

    cur.close()

    conn.close()