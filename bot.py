import os
import requests
import time
import feedparser
from datetime import datetime, timedelta
import re

TELEGRAM_TOKEN = "7908433957:AAEyetZTWACBNn6t-wHPQwB89p1PtkQEvfg"
CHANNEL_ID = "@fiveleaguesua"

# RSS джерела топових ЗМІ
RSS_FEEDS = [
    "https://www.skysports.com/rss/football",
    "http://feeds.bbci.co.uk/sport/football/rss.xml",
    "https://www.espn.com/espn/rss/soccer/news",
    "https://www.goal.com/feeds/news?fmt=rss&edition=en",
]

# Ключові слова для фільтрації важливих новин
IMPORTANT_KEYWORDS = [
    "manchester", "liverpool", "chelsea", "arsenal", "tottenham",
    "real madrid", "barcelona", "atletico", "sevilla",
    "juventus", "milan", "inter", "napoli", "roma",
    "bayern", "dortmund", "leipzig",
    "psg", "lyon", "marseille",
    "champions league", "europa league", "transfer", "injury",
    "sacked", "appointed", "contract", "million", "record"
]

processed_articles = set()

def send_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHANNEL_ID, "text": text, "parse_mode": "HTML"}
    response = requests.post(url, data=data)
    return response.json()

def is_important_news(title, description):
    text = (title + " " + description).lower()
    return any(keyword in text for keyword in IMPORTANT_KEYWORDS)

def format_post(title, description, source):
    # Форматуємо пост як справжній журналіст
    post = f"⚽️ <b>{title}</b>\n\n"
    
    if description:
        # Обрізаємо опис до розумної довжини
        if len(description) > 200:
            description = description[:200] + "..."
        post += f"{description}\n\n"
    
    post += f"📰 <i>За інформацією {source}</i>"
    return post

def get_news():
    new_articles = []
    
    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            source_name = feed.feed.title if hasattr(feed.feed, 'title') else "Football News"
            
            for entry in feed.entries[:5]:  # Тільки останні 5 новин
                article_id = entry.link
                
                if article_id not in processed_articles:
                    title = entry.title
                    description = entry.get('summary', '')
                    
                    # Очищаємо HTML теги
                    description = re.sub('<.*?>', '', description)
                    
                    if is_important_news(title, description):
                        formatted_post = format_post(title, description, source_name)
                        new_articles.append((formatted_post, article_id))
                        processed_articles.add(article_id)
            
        except Exception as e:
            print(f"Помилка з {feed_url}: {e}")
    
    return new_articles

def main():
    send_message("🤖 Five Leagues Bot запущено! Моніторинг новин активний.")
    
    while True:
        try:
            articles = get_news()
            
            if articles:
                # Відправляємо найкращу статтю
                best_article = articles[0][0]  # Перша - найважливіша
                
                # Відправляємо на погодження
                approval_text = f"📋 <b>НОВИНА НА ПОГОДЖЕННЯ:</b>\n\n{best_article}\n\n❓ Публікувати? Відповідь: ТАК/НІ/ВИПРАВИТИ"
                send_message(approval_text)
            
            time.sleep(1800)  # 30 хвилин
            
        except Exception as e:
            print(f"Помилка: {e}")
            time.sleep(300)  # 5 хвилин при помилці

if __name__ == "__main__":
    main()

# Для Render
import os
port = int(os.environ.get("PORT", 5000))
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading

def run_server():
    server = HTTPServer(('', port), SimpleHTTPRequestHandler)
    server.serve_forever()

# Запускаємо сервер у фоні
threading.Thread(target=run_server, daemon=True).start()
