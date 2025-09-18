"""
Общие функции и константы для бота
"""
import sqlite3
import time
from typing import List, Optional, Tuple, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram import InputMediaPhoto

# Константы
AUTUMN_FOOD_PRICE = 1000
AUTUMN_EVENT_IMG = "https://i.postimg.cc/fb1TQF6W/5355070803995131046.jpg"

# Изображения
IMAGES = {
    "main": "https://i.postimg.cc/8kqJ8Q8H/5355070803995130955.jpg",
    "farm": "https://i.postimg.cc/8kqJ8Q8H/5355070803995130955.jpg",
    "shop": "https://i.postimg.cc/8kqJ8Q8H/5355070803995130955.jpg",
    "farmers": "https://i.postimg.cc/28MN9vvh/5355070803995130971.jpg",
    "status": "https://i.postimg.cc/2jPf2hnv/5355070803995130978.jpg",
    "coins": "https://i.postimg.cc/SxnCk0JH/5355070803995130993.jpg",
    "casino": "https://i.postimg.cc/zvZBKMj2/5355070803995131009.jpg",
    "promo": "https://i.postimg.cc/kXCG50DB/5355070803995131030.jpg",
    "autumn": AUTUMN_EVENT_IMG,
    "logs": "https://i.postimg.cc/fb1TQF6W/5355070803995131046.jpg",
    "admin": "https://i.postimg.cc/fb1TQF6W/5355070803995131046.jpg",
    "top": "https://i.postimg.cc/mg2rY7Y4/5355070803995131023.jpg",
}

# Глобальные переменные (будут инициализированы в main.py)
_execute = None
cur = None
is_admin = None
edit_section = None
chunk_buttons = None
format_num = None
get_user = None
update_user = None
log_user_action = None


def init_common_functions(execute_func, cursor, admin_func, edit_func, chunk_func, 
                         format_func, user_func, update_func, log_func):
    """Инициализация общих функций"""
    global _execute, cur, is_admin, edit_section, chunk_buttons, format_num, get_user, update_user, log_user_action
    _execute = execute_func
    cur = cursor
    is_admin = admin_func
    edit_section = edit_func
    chunk_buttons = chunk_func
    format_num = format_func
    get_user = user_func
    update_user = update_func
    log_user_action = log_func