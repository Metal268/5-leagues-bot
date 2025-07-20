import os
import requests
import time
from datetime import datetime
import re
import json
from bs4 import BeautifulSoup
import feedparser

TELEGRAM_TOKEN = "7908433957:AAEyetZTWACBNn6t-wHPQwB89p1PtkQEvfg"
CHANNEL_ID = "@fiveleaguesua"

# Джерела новин
NEWS_SOURCES = {
    'google_news': 'https://news.google.com/rss/search?q=football+premier+league+transfer&hl=en&gl=GB&ceid=GB:en',
    'sky_sports': 'https://www.skysports.com/football/news',
    'bbc_sport': 'https://www.bbc.com/sport/football',
}

LEAGUES = {
    'premier league': '🏴󠁧󠁢󠁥󠁮󠁧󠁿 АПЛ',
    'la liga': '🇪🇸 Ла Ліга', 
    'serie a': '🇮🇹 Серія А',
    'bundesliga': '🇩🇪 Бундесліга',
    'ligue 1': '🇫🇷 Ліга 1',
    'champions league': '🏆 Ліга Чемпіонів',
    'europa league': '🥈 Ліга Європи'
}

CLUBS = {
    'manchester united': '🔴 Манчестер Юнайтед',
    'manchester city': '🔵 Манчестер Сіті',
    'liverpool': '🔴 Ліверпуль',
    'chelsea': '🔵 Челсі',
    'arsenal': '🔴 Арсенал',
    'tottenham': '⚪ Тоттенгем',
    'real madrid': '⚪ Реал Мадрид',
    'barcelona': '🔵 Барселона',
    'juventus': '⚫ Ювентус',
    'milan': '🔴 Мілан',
    'bayern': '🔴 Баварія',
    'psg': '🔵 ПСЖ'
}

IMPORTANT_KEYWORDS = [
    "transfer", "signing", "deal", "million", "contract",
    "injury", "ruled out", "return", "fitness",
    "sacked", "fired", "appointed", "manager", "coach",
    "champions league", "europa league", "final",
    "record", "goal", "assist", "performance",
    "rumour", "target", "bid", "offer"
]

processed_articles = set()

def translate_text(text):
    """Покращений переклад"""
    try:
        # Спочатку чистимо текст
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        if len(text) > 500:
            text = text[:500]
            
        url = "https://api.mymemory.translated.net/get"
        params = {'q': text, 'langpair': 'en|uk'}
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if 'responseData' in data:
            translated = data['responseData']['translatedText']
            if "MYMEMORY WARNING" not in translated.upper():
                return translated
        return text
    except:
        return text

def get_club_name(text):
    """Отримуємо українське ім'я клубу"""
    text_lower = text.lower()
    for eng_name, ua_name in CLUBS.items():
        if eng_name in text_lower:
            return ua_name
    return None

def get_league_name(text):
    """Отримуємо українське ім'я ліги"""
    text_lower = text.lower()
    for eng_name, ua_name in LEAGUES.items():
        if eng_name in text_lower:
            return ua_name
    return None

def determine_post_type(title, description):
    """Визначаємо тип новини для емодзі"""
    text = (title + " " + description).lower()
    
    if any(word in text for word in ["transfer", "signing", "deal", "million", "contract"]):
        return "transfer"
    elif any(word in text for word in ["injury", "ruled out", "injured", "fitness"]):
        return "injury"
    elif any(word in text for word in ["sacked", "fired", "appointed", "manager"]):
        return "manager"
    elif any(word in text for word in ["goal", "scored", "assist", "performance"]):
        return "performance"
    elif any(word in text for word in ["champions league", "europa league", "final"]):
        return "european"
    else:
        return "general"

def format_post(title, description, source="Football News", url=""):
    """Покращений формат поста"""
    
    # Визначаємо тип новини
    post_type = determine_post_type(title, description)
    
    # Емодзі залежно від типу
    emoji_map = {
        "transfer": "💰",
        "injury": "🏥", 
        "manager": "👔",
        "performance": "⚽",
        "european": "🏆",
        "general": "📰"
    }
    
    main_emoji = emoji_map.get(post_type, "📰")
    
    # Перекладаємо заголовок
    title_ua = translate_text(title)
    
    # Шукаємо клуби та ліги в тексті
    club = get_club_name(title + " " + description)
    league = get_league_name(title + " " + description)
    
    # Формуємо заголовок
    header_parts = [main_emoji]
    if club:
        header_parts.append(club)
    if league:
        header_parts.append(league)
    
    header = " ".join(header_parts)
    
    # Початок поста
    post = f"{header}\n\n"
    post += f"<b>{title_ua}</b>\n\n"
    
    # Опис новини
    if description:
        # Чистимо опис
        description = re.sub('<.*?>', '', description)
        description = re.sub(r'\s+', ' ', description).strip()
        
        # Обрізаємо якщо довгий
        if len(description) > 400:
            description = description[:400] + "..."
            
        description_ua = translate_text(description)
        
        # Розбиваємо на абзаци для читабельності
        sentences = description_ua.split('. ')
        if len(sentences) > 1:
            first_part = '. '.join(sentences[:2]) + '.'
            post += f"{first_part}\n\n"
            
            if len(sentences) > 2:
                remaining = '. '.join(sentences[2:])
                post += f"<i>{remaining}</i>\n\n"
        else:
            post += f"{description_ua}\n\n"
    
    # Додаємо контекст залежно від типу новини
    context_map = {
        "transfer": "💼 <i>Трансферні новини</i>",
        "injury": "⚕️ <i>Медичні новини</i>",
        "manager": "🏢 <i>Кадрові зміни</i>", 
        "performance": "📊 <i>Спортивні результати</i>",
        "european": "🌍 <i>Єврокубки</i>",
        "general": "⚽ <i>Футбольні новини</i>"
    }
    
    post += f"{context_map.get(post_type, '⚽ <i>Футбольні новини</i>')}\n"
    post += f"📰 <i>Джерело: {source}</i>"
    
    return post

def get_google_news():
    """Отримуємо новини з Google News RSS"""
    try:
        feed_url = 'https://news.google.com/rss/search?q=football+premier+league+transfer+injury+manager&hl=en&gl=GB&ceid=GB:en'
        feed = feedparser.parse(feed_url)
        
        articles = []
        for entry in feed.entries[:5]:  # Берemo топ-5
            title = entry.title
            description = entry.get('summary', '')
            source = entry.get('source', {}).get('title', 'Google News')
            
            if is_important_news(title, description):
                articles.append({
                    'title': title,
                    'description': description,
                    'source': source,
                    'url': entry.link
                })
        
        return articles
    except Exception as e:
        print(f"❌ Помилка Google News: {e}")
        return []

def scrape_sky_sports():
    """Парсимо Sky Sports"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get('https://www.skysports.com/football/news', headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        articles = []
        news_items = soup.find_all('div', class_='news-list__item')[:3]
        
        for item in news_items:
            title_elem = item.find('a', class_='news-list__headline-link')
            if title_elem:
                title = title_elem.text.strip()
                description_elem = item.find('p', class_='news-list__summary')
                description = description_elem.text.strip() if description_elem else ""
                
                if is_important_news(title, description):
                    articles.append({
                        'title': title,
                        'description': description,
                        'source': 'Sky Sports',
                        'url': 'https://www.skysports.com' + title_elem.get('href', '')
                    })
        
        return articles
    except Exception as e:
        print(f"❌ Помилка Sky Sports: {e}")
        return []

def is_important_news(title, description):
    """Перевіряємо важливість новини"""
    text = (title + " " + description).lower()
    return any(keyword in text for keyword in IMPORTANT_KEYWORDS)

def get_football_news():
    """Збираємо новини з усіх джерел"""
    all_articles = []
    
    print("🔍 Збираємо новини з Google News...")
    all_articles.extend(get_google_news())
    
    print("🔍 Парсимо Sky Sports...")
    all_articles.extend(scrape_sky_sports())
    
    # Якщо реальних новин немає, додаємо тестові
    if not all_articles:
        print("📝 Використовуємо тестові новини...")
        test_news = [
            {
                "title": "Manchester United close to signing €80m midfielder from Real Madrid",
                "description": "Manchester United are reportedly close to finalizing a deal for Real Madrid's talented midfielder in a transfer worth €80 million. The Spanish international has been a long-term target for the Red Devils.",
                "source": "Sky Sports",
                "url": ""
            },
            {
                "title": "Liverpool's Mohamed Salah suffers injury setback, ruled out for three weeks", 
                "description": "Liverpool forward Mohamed Salah has suffered a hamstring injury during training and will be sidelined for approximately three weeks. The Egyptian international was in excellent form this season.",
                "source": "BBC Sport",
                "url": ""
            }
        ]
        all_articles = test_news
    
    # Форматуємо пости
    formatted_posts = []
    for article in all_articles:
        if article['title'] not in processed_articles:
            formatted = format_post(
                article['title'], 
                article['description'], 
                article['source'],
                article.get('url', '')
            )
            formatted_posts.append(formatted)
            processed_articles.add(article['title'])
            
            print(f"✅ Сформовано пост:")
            print("="*60)
            print(formatted)
            print("="*60)
    
    return formatted_posts

def send_message(text):
    """Надсилаємо повідомлення в Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": CHANNEL_ID, 
        "text": text, 
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    return requests.post(url, data=data)

def main():
    """Головна функція бота"""
    send_message("🤖 <b>Five Leagues Bot v2.0 запущено!</b> 🇺🇦\n\n⚽ Моніторимо топ-новини футболу...")
    
    while True:
        try:
            current_time = datetime.now().strftime("%H:%M:%S")
            print(f"🕐 {current_time} - Перевірка новин...")
            
            articles = get_football_news()
            
            if articles:
                # Берemo найкращу новину
                best_article = articles[0]
                
                # Надсилаємо на погодження
                approval_msg = f"📋 <b>НОВИНА НА ПОГОДЖЕННЯ:</b>\n\n{'-'*30}\n\n{best_article}\n\n{'-'*30}\n\n❓ <b>Публікувати?</b> ТАК/НІ"
                send_message(approval_msg)
                print("📤 Надіслано на погодження")
                
                # Якщо є ще новини, зберігаємо їх
                if len(articles) > 1:
                    print(f"📝 Збережено {len(articles)-1} додаткових новин")
            else:
                print("ℹ️ Нових важливих новин не знайдено")
            
            # Чекаємо 30 хвилин
            print("⏰ Наступна перевірка через 30 хвилин...")
            time.sleep(1800)
            
        except Exception as e:
            print(f"❌ Помилка: {e}")
            time.sleep(300)  # Чекаємо 5 хвилин при помилці

if __name__ == "__main__":
    main()

# Render server для хостингу
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler

def run_server():
    port = int(os.environ.get("PORT", 5000))
    server = HTTPServer(('', port), SimpleHTTPRequestHandler)
    print(f"🌐 Сервер запущено на порту {port}")
    server.serve_forever()

# Запускаємо сервер в окремому потоці
threading.Thread(target=run_server, daemon=True).start()
