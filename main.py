import socket
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests.packages.urllib3.util.connection as urllib_conn

def allowed_gai_family():
    return socket.AF_INET

urllib_conn.allowed_gai_family = allowed_gai_family

import telebot
from telebot import types
import html

# Встроенный веб-сервер для проверок Amvera
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_web_server():
    server = HTTPServer(('0.0.0.0', 80), HealthCheckHandler)
    server.serve_forever()

threading.Thread(target=run_web_server, daemon=True).start()

TOKEN = '8668630984:AAEQgKGPaJbrX-cgkLH62_MlLPdjaseDwtA'
bot = telebot.TeleBot(TOKEN)

# Данные подписки
STATIC_SERVER_KEY = (
    "vless://342f746b-26f3-4093-b87e-bfdb6a38def2@178.248.236.7:50443"
    "?security=reality&encryption=none&pbk=r-_zNu0BrD8PgGzg-KQSes06Si83txHWYPH-o8xXihk"
    "&fp=qq&type=tcp&flow=xtls-rprx-vision&sni=rutube.ru&sid=a66ffc56b634bd44#Desentom%20VPN"
)
SUB_URL = 'https://desentom-vpn.axelitvari.workers.dev/#Desentom%20VPN'

# Главное меню клавиатуры
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

# Меню выбора сроков
def get_periods_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_1m = types.InlineKeyboardButton("🗓 1 месяц — 100 ₽", callback_data="buy_1m")
    btn_3m = types.InlineKeyboardButton("🗓 3 месяца — 270 ₽ (скидка 10%)", callback_data="buy_3m")
    btn_6m = types.InlineKeyboardButton("🗓 6 месяцев — 500 ₽ (скидка 17%)", callback_data="buy_6m")
    btn_12m = types.InlineKeyboardButton("🗓 12 месяцев — 900 ₽ (выгода 25%)", callback_data="buy_12m")
    btn_back = types.InlineKeyboardButton("⬅️ Назад в меню", callback_data="main_menu")
    
    markup.add(btn_1m, btn_3m, btn_6m, btn_12m, btn_back)
    return markup

# Вспомогательная функция обновления сообщений
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

@bot.message_handler(commands=['start', 'menu'])
def send_welcome(message):
    text = (
        "🚀 <b>Добро пожаловать в главное меню Desentom VPN!</b>\n\n"
        "⚡️ Скоростной и защищенный доступ без лагов и ограничений.\n\n"
        "🗂 <b>Выберите действие:</b>"
    )
    try:
        with open('photo.jpg', 'rb') as photo:
            bot.send_photo(message.chat.id, photo, caption=text, parse_mode='HTML', reply_markup=get_main_menu())
    except FileNotFoundError:
        bot.send_message(message.chat.id, text, parse_mode='HTML', reply_markup=get_main_menu())

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    if call.data == "main_menu":
        text = "🚀 <b>Добро пожаловать в главное меню!</b>\n\n🗂 <b>Выберите действие:</b>"
        update_menu(call, text, get_main_menu())

    elif call.data == "buy_vpn":
        text = (
            "💳 <b>Выберите срок подписки Desentom VPN:</b>\n\n"
            "После выбора вы получите прямую ссылку для быстрой вставки в приложение Happ."
        )
        update_menu(call, text, get_periods_menu())

    elif call.data.startswith("buy_"):
        period_map = {
            "buy_1m": "1 месяц (100 ₽)",
            "buy_3m": "3 месяца (270 ₽)",
            "buy_6m": "6 месяцев (500 ₽)",
            "buy_12m": "12 месяцев (900 ₽)"
        }
        selected = period_map.get(call.data, "Подписка")
        
        safe_key = html.escape(STATIC_SERVER_KEY)
        safe_sub = html.escape(SUB_URL)
        
        caption = (
            f"✅ <b>Вы выбрали тариф: {selected}</b>\n\n"
            f"⚡️ <b>Ваша подписка Desentom VPN:</b>\n\n"
            f"🔗 <b>Ссылка для вставки в Happ (нажмите для копирования):</b>\n"
            f"<code>{safe_sub}</code>\n\n"
            f"🔑 <b>Прямой VLESS-ключ (для ручного ввода):</b>\n"
            f"<code>{safe_key}</code>"
        )
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("⬅️ Вернуться в меню", callback_data="main_menu"))
        update_menu(call, caption, markup)

    elif call.data == "my_subs":
        safe_sub = html.escape(SUB_URL)
        text = (
            f"📋 <b>Ваши подписки:</b>\n\n"
            f"🟢 <b>Статус:</b> Активна\n"
            f"🌐 <b>Сервис:</b> Desentom VPN\n\n"
            f"🔗 <b>Ссылка подписки:</b>\n<code>{safe_sub}</code>"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="main_menu"))
        update_menu(call, text, markup)

    elif call.data == "profile":
        user_id = call.from_user.id
        first_name = html.escape(call.from_user.first_name)
        text = (
            f"👤 <b>Ваш профиль:</b>\n\n"
            f"🆔 <b>Telegram ID:</b> <code>{user_id}</code>\n"
            f"👤 <b>Имя:</b> {first_name}\n"
            f"🌐 <b>Статус VPN:</b> Активен"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="main_menu"))
        update_menu(call, text, markup)

    elif call.data == "instruction":
        text = (
            "📖 <b>Инструкция по подключению:</b>\n\n"
            "1️⃣ Скачайте приложение <b>Happ</b> (доступно на Windows, Android, iOS).\n"
            "2️⃣ Нажмите на ссылку подписки в боте, чтобы скопировать её.\n"
            "3️⃣ Откройте Happ и нажмите кнопку <b>«Из буфера»</b> (или значок «+»).\n"
            "4️⃣ Выберите подписку <b>Desentom VPN</b> и нажмите кнопку включения!"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="main_menu"))
        update_menu(call, text, markup)

    elif call.data == "support":
        text = (
            "❓ <b>Возникли проблемы с VPN?</b>\n\n"
            "1. Откройте Happ и нажмите иконку обновить 🔄 возле подписки.\n"
            "2. Переключите режим с <b>Proxy</b> на <b>TUN</b> снизу экрана.\n"
            "3. Если ничего не помогает — перезапустите приложение Happ."
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="main_menu"))
        update_menu(call, text, markup)

    bot.answer_callback_query(call.id)

if __name__ == '__main__':
    print("Бот с меню успешно запущен!")
    bot.polling(none_stop=True)
