import os
import requests
import time
from datetime import datetime
import re
import json

TELEGRAM_TOKEN = "7908433957:AAEyetZTWACBNn6t-wHPQwB89p1PtkQEvfg"
CHANNEL_ID = "@fiveleaguesua"

# API новин (замість RSS)
NEWS_SOURCES = [
    "http://newsapi.org/v2/everything?q=football+premier+league&language=en&apiKey=demo",  # Demo key
    "https://www.goal.com/api/feeds/news?fmt=json&edition=en",
]

IMPORTANT_KEYWORDS = [
    "manchester", "liverpool", "chelsea", "arsenal", "tottenham",
    "real madrid", "barcelona", "atletico",
    "juventus", "milan", "inter", "napoli",
    "bayern", "dortmund", "leipzig",
    "psg", "lyon", "marseille",
    "champions league", "europa league", "transfer", "injury",
    "sacked", "appointed", "contract", "million"
]

processed_articles = set()

def translate_text(text):
    """Переклад через безкоштовний API"""
    try:
        url = "https://api.mymemory.translated.net/get"
        params = {'q': text[:500], 'langpair': 'en|uk'}
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if 'responseData' in data:
            translated = data['responseData']['translatedText']
            if "MYMEMORY WARNING" not in translated.upper():
                return translated
        return text
    except:
        return text

def send_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHANNEL_ID, "text": text, "parse_mode": "HTML"}
    return requests.post(url, data=data)

def is_important_news(title, description):
    text = (title + " " + description).lower()
    return any(keyword in text for keyword in IMPORTANT_KEYWORDS)

def format_post(title, description, source="Football News"):
    """Форматуємо пост українською"""
    title_ua = translate_text(title)
    
    emoji = "⚽️"
    if "transfer" in title.lower() or "million" in title.lower():
        emoji = "💰"
    elif "injury" in title.lower():
        emoji = "🏥"
    elif "sacked" in title.lower() or "appointed" in title.lower():
        emoji = "📋"
    
    post = f"{emoji} <b>{title_ua}</b>\n\n"
    
    if description:
        description = re.sub('<.*?>', '', description)
        if len(description) > 300:
            description = description[:300] + "..."
        description_ua = translate_text(description)
        post += f"{description_ua}\n\n"
    
    post += f"📰 <i>Джерело: {source}</i>"
    return post

def get_football_news():
    """Отримуємо новини через прямі запити"""
    articles = []
    
    # Тестові новини (поки API не налаштовані)
    test_news = [
        {
            "title": "Manchester United agree £60m deal for Bruno Fernandes replacement",
            "description": "Manchester United have reached an agreement to sign the Portuguese midfielder in a deal worth £60 million including add-ons.",
            "source": "Sky Sports"
        },
        {
            "title": "Liverpool injury update: Mohamed Salah ruled out for three weeks",
            "description": "Liverpool forward Mohamed Salah has been ruled out for three weeks with a hamstring injury sustained during training.",
            "source": "BBC Sport"
        }
    ]
    
    for news in test_news:
        if is_important_news(news["title"], news["description"]):
            formatted = format_post(news["title"], news["description"], news["source"])
            articles.append(formatted)
            print(f"✅ Сформовано пост:")
            print("="*50)
            print(formatted)
            print("="*50)
    
    return articles

def main():
    send_message("🤖 Five Leagues Bot запущено! 🇺🇦")
    
    while True:
        try:
            print(f"🕐 {datetime.now()} - Перевірка новин...")
            articles = get_football_news()
            
            if articles:
                best_article = articles[0]
                approval_msg = f"📋 <b>НОВИНА НА ПОГОДЖЕННЯ:</b>\n\n{best_article}\n\n❓ Публікувати? ТАК/НІ"
                send_message(approval_msg)
                print("📤 Надіслано на погодження")
            
            time.sleep(1800)  # 30 хвилин
            
        except Exception as e:
            print(f"❌ Помилка: {e}")
            time.sleep(300)

if __name__ == "__main__":
    main()

# Render server
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler

def run_server():
    port = int(os.environ.get("PORT", 5000))
    server = HTTPServer(('', port), SimpleHTTPRequestHandler)
    server.serve_forever()

threading.Thread(target=run_server, daemon=True).start()
