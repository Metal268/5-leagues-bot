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

def translate_text(text):
    """Переклад через безкоштовний API Google Translate"""
    try:
        # Використовуємо MyMemory API (безкоштовний)
        url = "https://api.mymemory.translated.net/get"
        params = {
            'q': text[:500],  # Обмежуємо довжину
            'langpair': 'en|uk'  # з англійської на українську
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if 'responseData' in data and data['responseData']['translatedText']:
            translated = data['responseData']['translatedText']
            
            # Якщо переклад поганий, повертаємо оригінал
            if "MYMEMORY WARNING" in translated.upper():
                return text
            
            return translated
        else:
            return text
            
    except Exception as e:
        print(f"Помилка перекладу: {e}")
        return text

def send_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHANNEL_ID, "text": text, "parse_mode": "HTML"}
    response = requests.post(url, data=data)
    return response.json()

def is_important_news(title, description):
    text = (title + " " + description).lower()
    return any(keyword in text for keyword in IMPORTANT_KEYWORDS)

def format_post(title, description, source):
    """Форматуємо пост як справжній український спортивний журналіст"""
    
    # Перекладаємо заголовок
    title_ua = translate_text(title)
    
    # Додаємо емодзі залежно від теми
    emoji = "⚽️"
    title_lower = title.lower()
    if "transfer" in title_lower or "million" in title_lower:
        emoji = "💰"
    elif "injury" in title_lower or "injured" in title_lower:
        emoji = "🏥"
    elif "sacked" in title_lower or "appointed" in title_lower:
        emoji = "📋"
    elif "champions league" in title_lower:
        emoji = "🏆"
    
    post = f"{emoji} <b>{title_ua}</b>\n\n"
    
    if description:
        # Очищаємо HTML теги
        description = re.sub('<.*?>', '', description)
        
        # Обрізаємо до розумної довжини
        if len(description) > 300:
            description = description[:300] + "..."
        
        # Перекладаємо опис
        description_ua = translate_text(description)
        post += f"{description_ua}\n\n"
    
    # Перекладаємо назву джерела
    source_translations = {
        "Sky Sports Football": "Sky Sports",
        "BBC Sport - Football": "BBC Sport",
        "ESPN Soccer": "ESPN",
        "Goal.com": "Goal.com"
    }
    
    source_ua = source_translations.get(source, source)
    post += f"📰 <i>За інформацією {source_ua}</i>"
    
    return post

def get_news():
    new_articles = []
    
    for feed_url in RSS_FEEDS:
        try:
            print(f"🔍 Перевіряю: {feed_url}")
            feed = feedparser.parse(feed_url)
            source_name = feed.feed.title if hasattr(feed.feed, 'title') else "Football News"
            
            for entry in feed.entries[:5]:  # Тільки останні 5 новин
                article_id = entry.link
                
                if article_id not in processed_articles:
                    title = entry.title
                    description = entry.get('summary', '')
                    
                    if is_important_news(title, description):
                        print(f"✅ Важлива новина: {title[:50]}...")
                        formatted_post = format_post(title, description, source_name)
                        new_articles.append((formatted_post, article_id))
                        processed_articles.add(article_id)
                        
                        # Показуємо результат для тестування
                        print(f"📰 ГОТОВИЙ ПОСТ:")
                        print("="*50)
                        print(formatted_post)
                        print("="*50)
            
        except Exception as e:
            print(f"Помилка з {feed_url}: {e}")
    
    return new_articles

def main():
    send_message("🤖 Five Leagues Bot запущено! Моніторинг новин активний.")
    
    while True:
        try:
            print(f"🕐 {datetime.now()} - Перевірка новин...")
            articles = get_news()
            
            if articles:
                # Відправляємо найкращу статтю на погодження
                best_article = articles[0][0]
                
                approval_text = f"📋 <b>НОВИНА НА ПОГОДЖЕННЯ:</b>\n\n{best_article}\n\n❓ Публікувати? Відповідь: ТАК/НІ/ВИПРАВИТИ"
                print("📤 Надсилаю на погодження...")
                send_message(approval_text)
            else:
                print("ℹ️ Важливих новин не знайдено")
            
            print(f"😴 Сплю 30 хвилин до наступної перевірки...")
            time.sleep(1800)  # 30 хвилин
            
        except Exception as e:
            print(f"Помилка: {e}")
            time.sleep(300)  # 5 хвилин при помилці

# Для тестування - розкоментуй цю функцію
def test_single_post():
    """Тестуємо один пост одразу"""
    print("🧪 ТЕСТОВИЙ РЕЖИМ")
    articles = get_news()
    if not articles:
        print("❌ Новин не знайдено")
    else:
        print(f"✅ Знайдено {len(articles)} новин")

if __name__ == "__main__":
    # test_single_post()  # Розкоментуй для швидкого тесту
    main()

# Для Render
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler

def run_server():
    port = int(os.environ.get("PORT", 5000))
    server = HTTPServer(('', port), SimpleHTTPRequestHandler)
    server.serve_forever()

threading.Thread(target=run_server, daemon=True).start()
