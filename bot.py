import os
import requests
import time
from datetime import datetime

TELEGRAM_TOKEN = "7908433957:AAEyetZTWACBNn6t-wHPQwB89p1PtkQEvfg"
CHANNEL_ID = "@fiveleaguesua"

def send_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHANNEL_ID, "text": text, "parse_mode": "HTML"}
    requests.post(url, data=data)

# Тестове повідомлення
send_message("🤖 Five Leagues Bot запущено!")

while True:
    time.sleep(1800)  # 30 хвилин
