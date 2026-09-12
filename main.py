import socket
import threading
import base64
import html
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests.packages.urllib3.util.connection as urllib_conn

def allowed_gai_family():
    return socket.AF_INET

urllib_conn.allowed_gai_family = allowed_gai_family

import telebot

# Сервер VLESS Desentom VPN
STATIC_SERVER_KEY = (
    "vless://342f746b-26f3-4093-b87e-bfdb6a38def2@178.248.236.7:50443"
    "?security=reality&encryption=none&pbk=r-_zNu0BrD8PgGzg-KQSes06Si83txHWYPH-o8xXihk"
    "&fp=qq&type=tcp&flow=xtls-rprx-vision&sni=rutube.ru&sid=a66ffc56b634bd44#Desentom%20VPN"
)

SUB_URL = 'https://ancient-forest-b030.axelitvari.workers.dev/'

# Встроенный веб-сервер (Health check + отдавалка Base64 подписки)
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ['/sub', '/sub/']:
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.end_headers()
            base64_key = base64.b64encode(STATIC_SERVER_KEY.encode('utf-8'))
            self.wfile.write(base64_key)
        else:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")

def run_web_server():
    server = HTTPServer(('0.0.0.0', 80), HealthCheckHandler)
    server.serve_forever()

threading.Thread(target=run_web_server, daemon=True).start()

TOKEN = '8668630984:AAEQgKGPaJbrX-cgkLH62_MlLPdjaseDwtA'
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Нажми /get_vpn, чтобы получить доступ к Desentom VPN.")

@bot.message_handler(commands=['get_vpn'])
def send_vpn_key(message):
    try:
        bot.send_message(message.chat.id, "Запрашиваю подписку Desentom VPN...")
        
        safe_key = html.escape(STATIC_SERVER_KEY)
        safe_sub = html.escape(SUB_URL)
        
        caption = (
            f"⚡️ <b>Подписка Desentom VPN</b>\n\n"
            f"🔗 <b>Ссылка для вставки в Happ (нажми, чтобы скопировать):</b>\n"
            f"<code>{safe_sub}</code>\n\n"
            f"🔑 <b>Прямой VLESS-ключ (для ручного добавления):</b>\n"
            f"<code>{safe_key}</code>"
        )
        
        bot.send_message(message.chat.id, caption, parse_mode='HTML')
    except Exception as e:
        print(f"Ошибка при обработке /get_vpn: {e}")
        bot.send_message(message.chat.id, "Произошла ошибка при отправке подписки.")

if __name__ == '__main__':
    print("Бот успешно запущен!")
    bot.polling(none_stop=True)
