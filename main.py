import socket
import requests.packages.urllib3.util.connection as urllib_conn

def allowed_gai_family():
    return socket.AF_INET

urllib_conn.allowed_gai_family = allowed_gai_family

import telebot
import requests
import re
import html

TOKEN = '8668630984:AAEQgKGPaJbrX-cgkLH62_MlLPdjaseDwtA'
bot = telebot.TeleBot(TOKEN)

RAW_URLS = [
    'https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/BLACK_VLESS_RUS.txt',
    'https://ghp.ci/https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/BLACK_VLESS_RUS.txt'
]

SUB_URL = 'https://ancient-forest-b030.axelitvari.workers.dev/#Desentom%20VPN'

def parse_keys():
    headers = {'User-Agent': 'Mozilla/5.0'}
    for url in RAW_URLS:
        try:
            response = requests.get(url, headers=headers, timeout=7)
            if response.status_code == 200 and response.text:
                pattern = r'(?:ss|vless|vmess|trojan|hysteria2|hy2)://[^\s<"\'\n&]+'
                keys = re.findall(pattern, response.text)
                if keys:
                    return list(dict.fromkeys(keys))
        except Exception as e:
            print(f"Ошибка загрузки с {url}: {e}")
    return []

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Нажми /get_vpn, чтобы получить ключ.")

@bot.message_handler(commands=['get_vpn'])
def send_vpn_key(message):
    try:
        bot.send_message(message.chat.id, "Desentom VPN создаёт ключ...")
        
        keys = parse_keys()
        
        if keys:
            latest_key = keys[-1]
            safe_key = html.escape(latest_key)
            safe_sub = html.escape(SUB_URL)
            
            caption = (
                f"<b>Свежий ключ:</b>\n"
                f"<code>{safe_key}</code>\n\n"
                f"🔗 <b>Ссылка подписки для HAPP (нажми, чтобы скопировать):</b>\n"
                f"<code>{safe_sub}</code>"
            )
            
            bot.send_message(message.chat.id, caption, parse_mode='HTML')
        else:
            bot.send_message(message.chat.id, "Не удалось сгенерировать ключ. Попробуйте позже.")
    except Exception as e:
        print(f"Ошибка при обработке /get_vpn: {e}")
        bot.send_message(message.chat.id, "Произошла ошибка при отправке ключа.")

if __name__ == '__main__':
    print("Бот успешно запущен!")
    bot.polling(none_stop=True)