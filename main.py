import os
import socket
import threading
import sqlite3
import datetime
import html
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests.packages.urllib3.util.connection as urllib_conn

# Фикс сети для хостинга
def allowed_gai_family():
    return socket.AF_INET

urllib_conn.allowed_gai_family = allowed_gai_family

import telebot
from telebot import types

# --- ВСЕ ТВОИ НАСТРОЙКИ ---
TOKEN = '8668630984:AAEQgKGPaJbrX-cgkLH62_MlLPdjaseDwtA'
ADMIN_ID = 7088071281

# Путь к БД с защитой от удаления при пересборке
DB_DIR = '/data' if os.path.exists('/data') else '.'
DB_PATH = os.path.join(DB_DIR, 'users.db')

# Реквизиты ОЗОН Банка
PAYMENT_REQUISITES = (
    "💳 <b>Реквизиты для оплаты:</b>\n\n"
    "• <b>СБП (Номер телефона):</b> <code>+79956913031</code>\n"
    "• <b>Банк:</b> <b>\"ОЗОН\" Банк</b>\n"
    "• <b>Получатель:</b> Глеб В.\n\n"
)

# Твой точный VLESS-ключ
STATIC_SERVER_KEY = (
    "vless://a94610b9-b27a-49c8-9085-b4cc37c9abb1@kkooa.vz-or.com:443"
    "?security=reality&encryption=none&pbk=RJETAkoZ6lowmwc5f0HtPy00c3dfojqQuypriLExXRE"
    "&fp=qq&type=grpc&serviceName=ads.x5.ru&sni=ads.x5.ru&sid=abbcd128"
    "#🇵🇱%20Мобильная%20связь%201%20NEW"
)
SUB_URL = 'https://desentom-vpn.axelitvari.workers.dev/#Desentom%20VPN'

bot = telebot.TeleBot(TOKEN)
pending_payments = {}

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            sub_expires TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def get_user_sub(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT sub_expires FROM users WHERE user_id = ?', (user_id,))
    res = cursor.fetchone()
    conn.close()
    if res and res[0]:
        expire_date = datetime.datetime.strptime(res[0], "%Y-%m-%d %H:%M:%S")
        if expire_date > datetime.datetime.now():
            return expire_date
    return None

def add_user_sub(user_id, username, days):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    current_sub = get_user_sub(user_id)
    if current_sub:
        new_expire = current_sub + datetime.timedelta(days=days)
    else:
        new_expire = datetime.datetime.now() + datetime.timedelta(days=days)
        
    expire_str = new_expire.strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''
        INSERT INTO users (user_id, username, sub_expires)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            username = excluded.username,
            sub_expires = excluded.sub_expires
    ''', (user_id, username, expire_str))
    
    conn.commit()
    conn.close()
    return new_expire

# --- ВЕБ-СЕРВЕР ДЛЯ ХОСТИНГА ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_web_server():
    server = HTTPServer(('0.0.0.0', 80), HealthCheckHandler)
    server.serve_forever()

threading.Thread(target=run_web_server, daemon=True).start()

# --- КЛАВИАТУРЫ ---
def get_main_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_buy = types.InlineKeyboardButton("🛒 Купить VPN", callback_data="buy_vpn")
    btn_subs = types.InlineKeyboardButton("📋 Мои подписки", callback_data="my_subs")
    btn_profile = types.InlineKeyboardButton("👤 Мой профиль", callback_data="profile")
    btn_help = types.InlineKeyboardButton("📖 Инструкция", callback_data="instruction")
    btn_support = types.InlineKeyboardButton("❓ Не работает VPN?", callback_data="support")
    
    markup.add(btn_buy)
    markup.add(btn_subs)
    markup.add(btn_profile, btn_help)
    markup.add(btn_support)
    return markup

def get_periods_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_1m = types.InlineKeyboardButton("🗓 1 месяц — 100 ₽", callback_data="select_1m_30")
    btn_3m = types.InlineKeyboardButton("🗓 3 месяца — 270 ₽", callback_data="select_3m_90")
    btn_6m = types.InlineKeyboardButton("🗓 6 месяцев — 500 ₽", callback_data="select_6m_180")
    btn_12m = types.InlineKeyboardButton("🗓 12 месяцев — 900 ₽", callback_data="select_12m_365")
    btn_back = types.InlineKeyboardButton("⬅️ Назад в меню", callback_data="main_menu")
    
    markup.add(btn_1m, btn_3m, btn_6m, btn_12m, btn_back)
    return markup

def update_menu(call, text, reply_markup):
    try:
        if call.message.caption:
            bot.edit_message_caption(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                caption=text,
                parse_mode='HTML',
                reply_markup=reply_markup
            )
        else:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                parse_mode='HTML',
                reply_markup=reply_markup
            )
    except Exception as e:
        print(f"Ошибка обновления меню: {e}")

# --- КОМАНДА ДЛЯ АДМИНА (/backup) ---
@bot.message_handler(commands=['backup'])
def send_backup(message):
    if message.from_user.id == ADMIN_ID:
        try:
            if os.path.exists(DB_PATH):
                with open(DB_PATH, 'rb') as db_file:
                    bot.send_document(ADMIN_ID, db_file, caption="💾 <b>Резервная копия подписок (users.db)</b>", parse_mode='HTML')
            else:
                bot.send_message(ADMIN_ID, "⚠️ Файл базы данных не найден.")
        except Exception as e:
            bot.send_message(ADMIN_ID, f"❌ Ошибка выгрузки БД: {e}")

# --- ОБРАБОТКА КОМАНД ---
@bot.message_handler(commands=['start', 'menu'])
def send_welcome(message):
    text = (
        "🚀 <b>Добро пожаловать в главное меню Desentom VPN!</b>\n\n"
        "⚡️ Быстрый и защищенный доступ без ограничений.\n\n"
        "🗂 <b>Выберите действие:</b>"
    )
    try:
        with open('photo.jpg', 'rb') as photo:
            bot.send_photo(message.chat.id, photo, caption=text, parse_mode='HTML', reply_markup=get_main_menu())
    except FileNotFoundError:
        bot.send_message(message.chat.id, text, parse_mode='HTML', reply_markup=get_main_menu())

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    user_id = call.from_user.id

    if call.data == "main_menu":
        if user_id in pending_payments:
            del pending_payments[user_id]
            
        text = "🚀 <b>Главное меню Desentom VPN</b>\n\n🗂 <b>Выберите действие:</b>"
        update_menu(call, text, get_main_menu())

    elif call.data == "buy_vpn":
        text = "💳 <b>Выберите срок подписки Desentom VPN:</b>"
        update_menu(call, text, get_periods_menu())

    elif call.data.startswith("select_"):
        parts = call.data.split("_")
        period_name = parts[1]
        days = int(parts[2])
        
        prices = {"1m": "100 ₽", "3m": "270 ₽", "6m": "500 ₽", "12m": "900 ₽"}
        price = prices.get(period_name, "100 ₽")

        pending_payments[user_id] = {'days': days, 'price': price}

        text = (
            f"🛒 <b>Оформление подписки на {days} дней ({price})</b>\n\n"
            f"{PAYMENT_REQUISITES}"
            f"📸 <b>Пожалуйста, оплатите и отправьте скриншот чека прямо сюда (в этот чат).</b>\n\n"
            f"<i>Бот ждёт вашу фотографию...</i> ⏳"
        )
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        btn_cancel = types.InlineKeyboardButton("⬅️ Отменить покупку", callback_data="main_menu")
        markup.add(btn_cancel)
        
        update_menu(call, text, markup)

    # --- АДМИН-КНОПКИ ПОД ЧЕКОМ ---
    elif call.data.startswith("adm_approve_"):
        parts = call.data.split("_")
        target_id = int(parts[2])
        days = int(parts[3])

        expire_date = add_user_sub(target_id, call.from_user.username or "Пользователь", days)
        expire_str = expire_date.strftime("%d.%m.%Y %H:%M")

        bot.answer_callback_query(call.id, "Подписка успешно выдана!")
        
        bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption=f"✅ <b>Оплата подтверждена!</b>\nПользователю <code>{target_id}</code> выдана подписка до {expire_str}.",
            parse_mode='HTML'
        )

        safe_key = html.escape(STATIC_SERVER_KEY)
        safe_sub = html.escape(SUB_URL)
        user_text = (
            f"🎉 <b>Ваша оплата успешно подтверждена!</b>\n\n"
            f"🟢 <b>Подписка активна до:</b> {expire_str}\n\n"
            f"🔗 <b>Ссылка для вставки в Happ (нажмите для копирования):</b>\n"
            f"<code>{safe_sub}</code>\n\n"
            f"🔑 <b>Прямой VLESS-ключ:</b>\n"
            f"<code>{safe_key}</code>\n\n"
            f"<i>Для проверки статуса нажмите «Мои подписки» в главном меню.</i>"
        )
        try:
            bot.send_message(target_id, user_text, parse_mode='HTML')
        except Exception as e:
            print(f"Ошибка отправки пользователю: {e}")

        # Авто-бэкап базы данных админу
        try:
            with open(DB_PATH, 'rb') as db_file:
                bot.send_document(ADMIN_ID, db_file, caption=f"💾 <b>Авто-бэкап базы данных</b>\nВыдана подписка ID: <code>{target_id}</code> до {expire_str}", parse_mode='HTML')
        except Exception as e:
            print(f"Ошибка сохранения авто-бэкапа: {e}")

    elif call.data.startswith("adm_reject_"):
        target_id = int(call.data.split("_")[2])
        bot.answer_callback_query(call.id, "Заявка отклонена.")
        
        bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption=f"❌ Заявка пользователя <code>{target_id}</code> отклонена.",
            parse_mode='HTML'
        )
        try:
            bot.send_message(target_id, "❌ <b>Ваш чек был отклонён администратором.</b>\nЕсли произошла ошибка, напишите в поддержку.", parse_mode='HTML')
        except Exception:
            pass

    # --- КНОПКИ МЕНЮ ---
    elif call.data == "my_subs":
        sub = get_user_sub(user_id)
        if sub:
            expire_str = sub.strftime("%d.%m.%Y %H:%M")
            safe_sub = html.escape(SUB_URL)
            safe_key = html.escape(STATIC_SERVER_KEY)
            text = (
                f"📋 <b>Ваши подписки:</b>\n\n"
                f"🟢 <b>Статус:</b> Активна\n"
                f"⏳ <b>Действительна до:</b> {expire_str}\n"
                f"🌐 <b>Сервис:</b> Desentom VPN\n\n"
                f"🔗 <b>Ссылка для Happ:</b>\n<code>{safe_sub}</code>\n\n"
                f"🔑 <b>VLESS-ключ:</b>\n<code>{safe_key}</code>"
            )
        else:
            text = "📋 <b>Ваши подписки:</b>\n\n🔴 <b>Статус:</b> Нет активной подписки\n\nВы можете приобрести доступ, нажав кнопку «Купить VPN»."
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="main_menu"))
        update_menu(call, text, markup)

    elif call.data == "profile":
        sub = get_user_sub(user_id)
        status_text = f"🟢 Активна до {sub.strftime('%d.%m.%Y')}" if sub else "🔴 Не активна"
        
        text = (
            f"👤 <b>Ваш профиль:</b>\n\n"
            f"🆔 <b>Telegram ID:</b> <code>{user_id}</code>\n"
            f"👤 <b>Имя:</b> {html.escape(call.from_user.first_name)}\n"
            f"🌐 <b>Статус VPN:</b> {status_text}"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="main_menu"))
        update_menu(call, text, markup)

    elif call.data == "instruction":
        text = (
            "📖 <b>Инструкция по подключению:</b>\n\n"
            "1️⃣ Скачайте приложение <b>Happ</b>.\n"
            "2️⃣ Нажмите на ссылку подписки в боте, чтобы скопировать ее.\n"
            "3️⃣ Откройте Happ и нажмите кнопку <b>«Из буфера»</b>.\n"
            "4️⃣ Выберите <b>Desentom VPN</b> и нажмите «Включить»."
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="main_menu"))
        update_menu(call, text, markup)

    elif call.data == "support":
        text = (
            "❓ <b>Возникли проблемы?</b>\n\n"
            "1. Откройте Happ и нажмите иконку обновить 🔄.\n"
            "2. Переключите режим с <b>Proxy</b> на <b>TUN</b> внизу экрана.\n"
            "3. По любым вопросам обращайтесь к администратору."
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="main_menu"))
        update_menu(call, text, markup)

    bot.answer_callback_query(call.id)

# --- ОБРАБОТЧИК ЧЕКОВ И ВОССТАНОВЛЕНИЯ БАЗЫ ---
@bot.message_handler(content_types=['text', 'photo', 'document'])
def handle_files_and_text(message):
    user_id = message.from_user.id
    
    # Восстановление базы админом (если отправить файл users.db)
    if user_id == ADMIN_ID and message.content_type == 'document' and message.document.file_name == 'users.db':
        try:
            file_info = bot.get_file(message.document.file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            
            with open(DB_PATH, 'wb') as new_db:
                new_db.write(downloaded_file)
            
            bot.send_message(ADMIN_ID, "✅ <b>База данных подписок успешно восстановлена!</b>", parse_mode='HTML')
            return
        except Exception as e:
            bot.send_message(ADMIN_ID, f"❌ Ошибка при восстановлении БД: {e}")
            return

    if user_id in pending_payments:
        if message.content_type in ['photo', 'document']:
            payment_info = pending_payments[user_id]
            days = payment_info['days']
            price = payment_info['price']
            username = message.from_user.username or message.from_user.first_name

            file_id = message.photo[-1].file_id if message.content_type == 'photo' else message.document.file_id

            admin_markup = types.InlineKeyboardMarkup(row_width=2)
            btn_confirm = types.InlineKeyboardButton("✅ Подтвердить", callback_data=f"adm_approve_{user_id}_{days}")
            btn_reject = types.InlineKeyboardButton("❌ Отклонить", callback_data=f"adm_reject_{user_id}")
            admin_markup.add(btn_confirm, btn_reject)

            caption = (
                f"💰 <b>Новый чек на проверку!</b>\n\n"
                f"👤 <b>От:</b> @{username} (ID: <code>{user_id}</code>)\n"
                f"🗓 <b>Срок подписки:</b> {days} дней\n"
                f"💵 <b>Сумма к проверке:</b> {price}"
            )
            
            try:
                bot.send_photo(ADMIN_ID, file_id, caption=caption, parse_mode='HTML', reply_markup=admin_markup)
                bot.send_message(user_id, "✅ <b>Чек отправлен на проверку администратору!</b>\nОжидайте подтверждения, бот пришлет доступ автоматически.", parse_mode='HTML')
            except Exception as e:
                bot.send_message(user_id, "⚠️ Ошибка отправки чека администратору. Попробуйте еще раз позже.", parse_mode='HTML')
                print(f"Ошибка: {e}")

            del pending_payments[user_id]
            
        else:
            bot.send_message(user_id, "⚠️ <b>Пожалуйста, отправьте скриншот чека в виде картинки (фотографии)!</b>\n\nЕсли хотите отменить, нажмите /start", parse_mode='HTML')
    else:
        if message.text and not message.text.startswith('/'):
            bot.send_message(user_id, "Воспользуйтесь меню: /start")

if __name__ == '__main__':
    print("Бот Desentom VPN успешно запущен со всеми вашими данными!")
    bot.polling(none_stop=True)
