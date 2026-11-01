import asyncio
import random
import uuid
import sqlite3
import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# ==========================================
# НАСТРОЙКИ
# ==========================================
BOT_TOKEN = "9017454233:AAGZmGs3Psi_RmnzO6p_bFJoP3VsHtidI28" # СМЕНИ ТОКЕН ЧЕРЕЗ /revoke!
CHANNEL_ID = "@oxvedosech"
SUPPORT_USERNAME = "@ShopOxvesose"
INSTRUCTION_LINK = "https://t.me/+W8mVmDi19MNkNDMx" 
ADMIN_ID = 8881713465 

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ==========================================
# БАЗА ДАННЫХ
# ==========================================
conn = sqlite3.connect('shop.db')
cursor = conn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY, username TEXT, referrer_id INTEGER, 
    points INTEGER DEFAULT 0, active_promo INTEGER DEFAULT 0
)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS tickets (
    ticket_id TEXT PRIMARY KEY, user_id INTEGER, product TEXT, 
    days TEXT, price TEXT, status TEXT, date TEXT
)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS stats (key TEXT PRIMARY KEY, value INTEGER)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS promo (code TEXT PRIMARY KEY, discount INTEGER)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)''') 

cursor.execute("INSERT OR IGNORE INTO stats (key, value) VALUES ('starts', 0)")
cursor.execute("INSERT OR IGNORE INTO stats (key, value) VALUES ('orders', 0)")
cursor.execute("INSERT OR IGNORE INTO promo (code, discount) VALUES ('OXVEDOSE2k', 5)")
conn.commit()

# --- ТОВАРЫ ---
PRODUCTS = {
    "magic_vip": {"name": "MAGIC VIP", "desc": "🔥 Максимальная мощь, обход античита.", "prices": {"1 день": "300 ₽", "7 дней": "1320 ₽", "14 дней": "2300 ₽"}},
    "magic_lite": {"name": "MAGIC LITE", "desc": "⚡️ Легкая версия, стабильная работа.", "prices": {"1 день": "250 ₽", "7 дней": "1050 ₽", "14 дней": "1550 ₽"}},
    "zolo": {"name": "ZOLO", "desc": "🧟‍♀️ Топовый софт для PUBG.", "prices": {"1 день": "270₽", "3 дня": "370₽", "7 дней": "580₽", "14 дней": "900₽", "30 дней": "1300₽", "60 дней": "1370₽"}},
    "uki": {"name": "UKI MOD", "desc": "❤️ Стабильный мод для новичков.", "prices": {"1 день": "340₽", "3 дня": "430₽", "7 дней": "800₽", "30 дней": "1500₽", "60 дней": "2000₽"}},
    "jarvis": {"name": "JARVIS MOD", "desc": "🤟 Умный софт с меню.", "prices": {"1 день": "340₽", "3 дня": "450₽", "7 дней": "800₽", "14 дней": "950₽", "30 дней": "2200₽", "60 дней": "2600₽"}},
    "zmod": {"name": "Z MOD", "desc": "⚡️ Быстрый и компактный.", "prices": {"1 день": "250₽", "3 дня": "380₽", "7 дней": "700₽", "14 дней": "1000₽", "30 дней": "1200₽", "60 дней": "1600₽"}},
}

ACCOUNTS = {
    "acc_usa": {"name": "🇺🇸 США (+1)", "desc": "Чистые номера.", "prices": {"1 шт": "179₽", "5 шт": "799₽"}},
    "acc_kz": {"name": "🇰🇿 Казахстан (+77)", "desc": "Для регистрации.", "prices": {"1 шт": "359₽", "5 шт": "1599₽"}},
}

# ==========================================
# КЛАВИАТУРЫ
# ==========================================
def get_main_kb(user_id):
    kb = [
        [KeyboardButton(text="🛒 Купить софт"), KeyboardButton(text="📱 Купить аккаунты")],
        [KeyboardButton(text="🎁 Рефералка/Промокод"), KeyboardButton(text="📜 Мои заказы")],
        [KeyboardButton(text="💳 Способы оплаты"), KeyboardButton(text="💬 Отзывы"), KeyboardButton(text="🆘 Поддержка")]
    ]
    if user_id == ADMIN_ID:
        kb.append([KeyboardButton(text="👑 Админ-панель")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

games_kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🎯 OXIDE")], [KeyboardButton(text="🔫 PUBG MOBILE")], [KeyboardButton(text="⬅️ Назад")]], resize_keyboard=True)
oxide_kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="👑 MAGIC VIP"), KeyboardButton(text="💎 MAGIC LITE")], [KeyboardButton(text="⬅️ Назад")]], resize_keyboard=True)
pubg_kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🧟‍♀️ ZOLO"), KeyboardButton(text="❤️ UKI MOD")], [KeyboardButton(text="🤟 JARVIS MOD"), KeyboardButton(text="⚡️ Z MOD")], [KeyboardButton(text="⬅️ Назад")]], resize_keyboard=True)
accounts_kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🇺🇸 США (+1)"), KeyboardButton(text="🇰🇿 Казахстан (+77)")], [KeyboardButton(text="⬅️ Назад")]], resize_keyboard=True)
pay_kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📸 Я оплатил (скинуть чек)")], [KeyboardButton(text="⬅️ Назад")]], resize_keyboard=True)

class UserState(StatesGroup):
    waiting_for_captcha = State()
    waiting_for_receipt = State()
    waiting_for_promo = State()
    waiting_for_broadcast = State()
    waiting_for_promo_create = State()
    waiting_for_review_photo = State()

# ==========================================
# БАЗОВЫЕ ФУНКЦИИ
# ==========================================
async def check_user_sub(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status not in ["left", "kicked"]
    except Exception: 
        return True 

def register_user(user_id, username, referrer_id=None):
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id, username, referrer_id) VALUES (?, ?, ?)", (user_id, username, referrer_id))
        if referrer_id and referrer_id != user_id:
            cursor.execute("UPDATE users SET points = points + 50 WHERE user_id = ?", (referrer_id,))
        conn.commit()

# ==========================================
# СТАРТ
# ==========================================
@dp.message(CommandStart())
async def start_cmd(message: types.Message, state: FSMContext):
    await state.clear()
    args = message.text.split()
    referrer_id = int(args[1].replace("ref_", "")) if len(args) > 1 and args[1].startswith("ref_") else None

    register_user(message.from_user.id, message.from_user.username, referrer_id)
    cursor.execute("UPDATE stats SET value = value + 1 WHERE key = 'starts'")
    conn.commit()

    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Я согласен с правилами", callback_data="agree")]])
    await message.answer("📜 **ПОЛЬЗОВАТЕЛЬСКОЕ СОГЛАШЕНИЕ**\n\n1. Товар цифровой, возврату не подлежит.\n2. Передача ключей третьим лицам запрещена.\n\nНажмите кнопку ниже, чтобы продолжить.", reply_markup=kb)

@dp.callback_query(F.data == "agree")
async def process_agree(callback: CallbackQuery):
    await callback.message.delete()
    await callback.message.answer(f"⚠️ **Подпишитесь на канал:** {CHANNEL_ID}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Я подписался ✅", callback_data="check_sub")]]))

@dp.callback_query(F.data == "check_sub")
async def process_check_sub(callback: CallbackQuery):
    if await check_user_sub(callback.from_user.id):
        await callback.message.delete()
        await callback.message.answer("👋 Добро пожаловать в магазин!", reply_markup=get_main_kb(callback.from_user.id))
    else:
        await callback.answer("❌ Вы не подписались!", show_alert=True)

# ==========================================
# МЕНЮ
# ==========================================
@dp.message(F.text == "🛒 Купить софт")
async def buy_menu(message: types.Message): await message.answer("🎮 Выбери игру:", reply_markup=games_kb)

@dp.message(F.text == "🎯 OXIDE")
async def oxide_menu(message: types.Message): await message.answer("🎯 Выбери софт для OXIDE:", reply_markup=oxide_kb)

@dp.message(F.text == "🔫 PUBG MOBILE")
async def pubg_menu(message: types.Message): await message.answer("🔫 Выбери софт для PUBG:", reply_markup=pubg_kb)

@dp.message(F.text == "📱 Купить аккаунты")
async def accounts_menu(message: types.Message): await message.answer("📱 Выбери страну аккаунта:", reply_markup=accounts_kb)

# ==========================================
# ВЫБОР ТОВАРА
# ==========================================
async def generate_price_buttons(product_data, prefix, state, message, prod_key):
    await state.update_data(product=prod_key)
    buttons, row = [], []
    for days in product_data["prices"].keys():
        row.append(InlineKeyboardButton(text=days, callback_data=f"{prefix}_{days}"))
        if len(row) == 2: buttons.append(row); row = []
    if row: buttons.append(row)
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer(f"📦 **{product_data['name']}**\n\n{product_data.get('desc', '')}\n\n👇 Выбери опцию:", reply_markup=kb)

@dp.message(F.text.in_(["👑 MAGIC VIP", "💎 MAGIC LITE", "🧟‍♀️ ZOLO", "❤️ UKI MOD", "🤟 JARVIS MOD", "⚡️ Z MOD"]))
async def show_days_buttons(message: types.Message, state: FSMContext):
    text_map = {"👑 MAGIC VIP": "magic_vip", "💎 MAGIC LITE": "magic_lite", "🧟‍♀️ ZOLO": "zolo", "❤️ UKI MOD": "uki", "🤟 JARVIS MOD": "jarvis", "⚡️ Z MOD": "zmod"}
    prod_key = text_map.get(message.text)
    await generate_price_buttons(PRODUCTS[prod_key], "day", state, message, prod_key)

@dp.message(F.text.in_(["🇺🇸 США (+1)", "🇰🇿 Казахстан (+77)"]))
async def show_acc_buttons(message: types.Message, state: FSMContext):
    text_map = {"🇺🇸 США (+1)": "acc_usa", "🇰🇿 Казахстан (+77)": "acc_kz"}
    prod_key = text_map.get(message.text)
    await generate_price_buttons(ACCOUNTS[prod_key], "acc", state, message, prod_key)

# ==========================================
# ВЫБОР ОПЦИИ, ПРОМОКОД И КАПЧА
# ==========================================
@dp.callback_query(F.data.startswith("day_") | F.data.startswith("acc_"))
async def process_choice(callback: CallbackQuery, state: FSMContext):
    is_acc = callback.data.startswith("acc_")
    opt = callback.data.replace("acc_", "").replace("day_", "")
    data = await state.get_data()
    prod_key = data.get("product")
    if not prod_key: return await callback.answer("Ошибка. Начните заново /start", show_alert=True)
        
    prod_db = ACCOUNTS if is_acc else PRODUCTS
    base_price_str = prod_db[prod_key]["prices"][opt]
    price_num = int(''.join(filter(str.isdigit, base_price_str.split("₽")[0])))
    
    # Безопасная проверка промокода (защита от пустой базы)
    cursor.execute("SELECT active_promo FROM users WHERE user_id = ?", (callback.from_user.id,))
    user_data = cursor.fetchone()
    promo_discount = user_data[0] if user_data else 0
    
    discount_msg = ""
    final_price = price_num
    if promo_discount and promo_discount > 0:
        final_price = int(price_num - (price_num * promo_discount / 100))
        discount_msg = f"\n🎁 **Ваш промокод на {promo_discount}% применен!**\n"
        cursor.execute("UPDATE users SET active_promo = 0 WHERE user_id = ?", (callback.from_user.id,))
        conn.commit()

    final_price_str = f"{final_price}₽"
    await state.update_data(days=opt, price=final_price_str)
    
    await callback.message.edit_text(
        f"📦 **{prod_db[prod_key]['name']}**\n⏱ Опция: **{opt}**\n💰 Цена: **{final_price_str}**{discount_msg}\n\n🛡 Проверка на робота:"
    )
    
    a, b = random.randint(1, 10), random.randint(1, 10)
    await state.update_data(captcha_answer=a+b)
    await callback.message.answer(f"Сколько будет {a} + {b}? (напиши цифру)")
    await state.set_state(UserState.waiting_for_captcha)
    await callback.answer()

@dp.message(UserState.waiting_for_captcha)
async def captcha_check(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if message.text.isdigit() and int(message.text) == data.get("captcha_answer"):
        pay_text = (
            "✅ Проверка пройдена!\n\n"
            "💳 **РЕКВИЗИТЫ:**\n"
            "Озон Банк: +7 (906) 461-54-18\n"
            f"Звёзды (писать сюда): {SUPPORT_USERNAME}\n\n"
            "👇 После оплаты нажми кнопку ниже и отправь чек."
        )
        await message.answer(pay_text, reply_markup=pay_kb)
        await state.set_state(UserState.waiting_for_receipt)
    else:
        await message.answer("❌ Неверно! Попробуй еще раз.")

# ==========================================
# ОТПРАВКА ЧЕКА И АВТО-ОТЗЫВ
# ==========================================
@dp.message(UserState.waiting_for_receipt, F.photo | F.document)
async def receive_receipt(message: types.Message, state: FSMContext):
    data = await state.get_data()
    prod_key, days, price = data.get("product"), data.get("days"), data.get("price")
    if not prod_key: return await message.answer("Ошибка сессии. Начните заново /start")
    
    p_name = PRODUCTS.get(prod_key, ACCOUNTS.get(prod_key, {"name": "Неизвестно"}))["name"]
    ticket_id = str(uuid.uuid4())[:8].upper() 
    today = datetime.date.today().isoformat()
    
    cursor.execute("INSERT INTO tickets (ticket_id, user_id, product, days, price, status, date) VALUES (?, ?, ?, ?, ?, 'Pending', ?)", 
                   (ticket_id, message.from_user.id, prod_key, days, price, today))
    cursor.execute("UPDATE stats SET value = value + 1 WHERE key = 'orders'")
    conn.commit()
    
    caption_text = (
        f"💰 **НОВЫЙ ЧЕК!**\n\n"
        f"👤 Клиент: @{message.from_user.username or 'Скрыт'} (ID: {message.from_user.id})\n"
        f"📦 Товар: {p_name} ({days})\n"
        f"💵 Сумма: {price}\n"
        f"🎫 Тикет: `{ticket_id}`\n\n"
        f"👇 Чтобы выдать ключ, отправь:\n"
        f"`/tickets {ticket_id} ТВОЙ-КЛЮЧ`"
    )
    
    try:
        await bot.send_photo(
            chat_id=ADMIN_ID, 
            photo=message.photo[-1].file_id if message.photo else message.document.file_id, 
            caption=caption_text, 
            parse_mode="Markdown"
        )
    except Exception as e:
        await bot.send_message(ADMIN_ID, caption_text + f"\n\n(Ошибка фото: {e})", parse_mode="Markdown")
    
    review_text = (
        f"🕒 **Заказ {ticket_id} отправлен на проверку.**\n\n"
        f"🙏 Пожалуйста, пока мы проверяем оплату, оставьте отзыв о нашем магазине!\n"
        f"Перешлите это фото или напишите отзыв сюда: {SUPPORT_USERNAME}"
    )
    
    cursor.execute("SELECT value FROM settings WHERE key = 'review_photo'")
    review_photo = cursor.fetchone()
    
    try:
        if review_photo:
            await bot.send_photo(
                chat_id=message.from_user.id,
                photo=review_photo[0],
                caption=review_text,
                reply_markup=get_main_kb(message.from_user.id)
            )
        else:
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💬 Написать отзыв", url=f"https://t.me/{SUPPORT_USERNAME.replace('@', '')}")]
            ])
            await message.answer(review_text, reply_markup=kb)
    except Exception:
        await message.answer(review_text, reply_markup=get_main_kb(message.from_user.id))
        
    await state.clear()

# ==========================================
# ВЫДАЧА КЛЮЧА
# ==========================================
@dp.message(Command("tickets"))
async def admin_issue_key(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split(maxsplit=2)
    if len(args) < 3: return await message.reply("⚠️ Формат: `/tickets ID КЛЮЧ`")
    
    ticket_id, key = args[1].upper(), args[2]
    cursor.execute("SELECT user_id, status FROM tickets WHERE ticket_id = ?", (ticket_id,))
    row = cursor.fetchone()
    
    if not row: return await message.reply("❌ Тикет не найден.")
    user_id, status = row
    if status != 'Pending': return await message.reply("❌ Тикет уже обработан.")
        
    try:
        msg = await bot.send_message(user_id, "⚙️ **Генерация ключа...**")
        await asyncio.sleep(2)
        
        success_text = (
            f"🎉 **Спасибо за покупку!**\n\n"
            f"🔑 Ваш ключ: `{key}`\n\n"
            f"📖 **ФАЙЛЫ И УСТАНОВКА:**\n{INSTRUCTION_LINK}\n\n"
            f"🛡 **КАК НЕ ПОЛУЧИТЬ БАН:**\n"
            f"1. Не играйте внаглую.\n"
            f"2. Если палят — выйдите на 10 минут.\n"
            f"3. Играйте в часы низкого онлайна.\n\n"
            f"🙏 **Оставьте отзыв:** {SUPPORT_USERNAME}"
        )
        await msg.edit_text(success_text, parse_mode="Markdown")
        
        cursor.execute("UPDATE tickets SET status = 'Done' WHERE ticket_id = ?", (ticket_id,))
        conn.commit()
        await message.reply(f"✅ Ключ выдан по тикету {ticket_id}!")
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")

# ==========================================
# МОИ ЗАКАЗЫ
# ==========================================
@dp.message(F.text == "📜 Мои заказы")
async def my_orders(message: types.Message):
    cursor.execute("SELECT ticket_id, product, days, price, status FROM tickets WHERE user_id = ? ORDER BY rowid DESC LIMIT 5", (message.from_user.id,))
    orders = cursor.fetchall()
    if not orders: return await message.answer("У вас пока нет заказов.")
    text = "📜 **Ваши последние 5 заказов:**\n\n"
    for o in orders:
        status = "✅ Выдан" if o[4] == "Done" else "🕒 В обработке"
        text += f"Тикет: `{o[0]}`\nТовар: {o[1]} ({o[2]})\nСумма: {o[3]}\nСтатус: {status}\n\n"
    await message.answer(text, parse_mode="Markdown")

# ==========================================
# РЕФЕРАЛКА И ПРОМОКОДЫ
# ==========================================
@dp.message(F.text == "🎁 Рефералка/Промокод")
async def ref_system(message: types.Message):
    cursor.execute("SELECT points FROM users WHERE user_id = ?", (message.from_user.id,))
    res = cursor.fetchone()
    points = res[0] if res else 0
    
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{message.from_user.id}"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🎟 Ввести промокод", callback_data="enter_promo")]])
    await message.answer(
        f"🎁 **Ваши баллы:** {points}\n"
        f"Приглашайте друзей (+50 баллов).\n"
        f"Баллы автоматически дают скидку при покупке софта.\n\n"
        f"Ваша ссылка:\n`{ref_link}`", parse_mode="Markdown", reply_markup=kb
    )

@dp.callback_query(F.data == "enter_promo")
async def promo_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите ваш промокод:")
    await state.set_state(UserState.waiting_for_promo)
    await callback.answer()

@dp.message(UserState.waiting_for_promo)
async def promo_check(message: types.Message, state: FSMContext):
    code = message.text.strip().upper()
    cursor.execute("SELECT discount FROM promo WHERE code = ?", (code,))
    res = cursor.fetchone()
    if res:
        cursor.execute("UPDATE users SET active_promo = ? WHERE user_id = ?", (res[0], message.from_user.id))
        conn.commit()
        await message.answer(f"✅ Промокод активирован! Скидка {res[0]}% применится при следующей покупке софта.")
    else: 
        await message.answer("❌ Неверный промокод.")
    await state.clear()

# ==========================================
# АДМИН-ПАНЕЛЬ
# ==========================================
@dp.message(F.text == "👑 Админ-панель")
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    cursor.execute("SELECT value FROM stats WHERE key = 'starts'"); starts = cursor.fetchone()[0]
    cursor.execute("SELECT value FROM stats WHERE key = 'orders'"); orders = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users"); users = cursor.fetchone()[0]

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="🎟 Создать промокод", callback_data="admin_promo")],
        [InlineKeyboardButton(text="🖼 Фото для отзыва", callback_data="admin_set_review")]
    ])
    await message.answer(f"📊 **АДМИН-ПАНЕЛЬ**\n\n👤 Юзеров: {users}\n🚀 Стартов: {starts}\n🛒 Заказов: {orders}", reply_markup=kb)

@dp.callback_query(F.data == "admin_set_review")
async def review_photo_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    await callback.message.answer("Отправь фотографию для отзыва (она будет уходить клиентам):")
    await state.set_state(UserState.waiting_for_review_photo)
    await callback.answer()

@dp.message(UserState.waiting_for_review_photo, F.photo)
async def save_review_photo(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('review_photo', ?)", (message.photo[-1].file_id,))
    conn.commit()
    await message.answer("✅ Фото для отзывов сохранено!")
    await state.clear()

@dp.callback_query(F.data == "admin_broadcast")
async def broadcast_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    await callback.message.answer("Введите текст для рассылки:")
    await state.set_state(UserState.waiting_for_broadcast)
    await callback.answer()

@dp.message(UserState.waiting_for_broadcast)
async def broadcast_send(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    cursor.execute("SELECT user_id FROM users"); users = cursor.fetchall()
    success = 0
    await message.answer("Рассылка запущена...")
    for u in users:
        try:
            await bot.send_message(u[0], message.text)
            success += 1
            await asyncio.sleep(0.05)
        except: pass
    await message.answer(f"✅ Доставлено: {success} чел.")
    await state.clear()

@dp.callback_query(F.data == "admin_promo")
async def promo_create(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    await callback.message.answer("Введите промокод и скидку (например: NEWYEAR 15):")
    await state.set_state(UserState.waiting_for_promo_create)
    await callback.answer()

@dp.message(UserState.waiting_for_promo_create)
async def promo_save(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    try:
        code, discount = message.text.upper().split()
        cursor.execute("INSERT OR REPLACE INTO promo (code, discount) VALUES (?, ?)", (code, int(discount)))
        conn.commit()
        await message.answer(f"✅ Промокод {code} на {discount}% создан!")
    except: 
        await message.answer("❌ Ошибка формата. Пиши: КОД СКИДКА")
    await state.clear()

# ==========================================
# ОСТАЛЬНОЕ
# ==========================================
@dp.message(F.text == "⬅️ Назад")
async def back(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Главное меню:", reply_markup=get_main_kb(message.from_user.id))

@dp.message(F.text == "💳 Способы оплаты")
async def pay_info(message: types.Message):
    await message.answer(f"💳 Озон Банк: +7 (906) 461-54-18\n⭐ Звёзды (писать сюда): {SUPPORT_USERNAME}\n\n📸 После оплаты нажми «Я оплатил» и отправь чек.")

@dp.message(F.text == "💬 Отзывы")
async def reviews_info(message: types.Message):
    await message.answer("💬 Отзывы: https://t.me/+n4g8yVSJ2N8zMzg6")

@dp.message(F.text == "🆘 Поддержка")
async def support_info(message: types.Message):
    await message.answer(f"🆘 Поддержка: {SUPPORT_USERNAME}")

async def main():
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
