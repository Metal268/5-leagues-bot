import os
import requests
import time
from datetime import datetime
import re
import json
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler

TELEGRAM_TOKEN = "7908433957:AAEyetZTWACBNn6t-wHPQwB89p1PtkQEvfg"
CHANNEL_ID = "@fiveleaguesua"

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

processed_articles = set()

def translate_text(text):
    """Переклад через безкоштовний API"""
    try:
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

def determine_post_type(title, description):
    """Визначаємо тип новини"""
    text = (title + " " + description).lower()
    
    if any(word in text for word in ["transfer", "signing", "deal", "million"]):
        return "transfer"
    elif any(word in text for word in ["injury", "ruled out", "injured"]):
        return "injury"
    elif any(word in text for word in ["sacked", "fired", "appointed"]):
        return "manager"
    elif any(word in text for word in ["goal", "scored", "performance"]):
        return "performance"
    else:
        return "general"

def format_post(title, description, source="Football News"):
    """Покращений формат поста"""
    post_type = determine_post_type(title, description)
    
    emoji_map = {
        "transfer": "💰",
        "injury": "🏥", 
        "manager": "👔",
        "performance": "⚽",
        "general": "📰"
    }
    
    main_emoji = emoji_map.get(post_type, "📰")
    title_ua = translate_text(title)
    club = get_club_name(title + " " + description)
    
    # Формуємо заголовок
    header_parts = [main_emoji]
    if club:
        header_parts.append(club)
    
    header = " ".join(header_parts)
    
    # Початок поста
    post = f"{header}\n\n"
    post += f"<b>{title_ua}</b>\n\n"
    
    # Опис
    if description:
        description = re.sub('<.*?>', '', description)
        description = re.sub(r'\s+', ' ', description).strip()
        
        if len(description) > 300:
            description = description[:300] + "..."
            
        description_ua = translate_text(description)
        post += f"{description_ua}\n\n"
    
    # Контекст
    context_map = {
        "transfer": "💼 <i>Трансферні новини</i>",
        "injury": "⚕️ <i>Медичні новини</i>",
        "manager": "🏢 <i>Кадрові зміни</i>", 
        "performance": "📊 <i>Спортивні результати</i>",
        "general": "⚽ <i>Футбольні новини</i>"
    }
    
    post += f"{context_map.get(post_type, '⚽ <i>Футбольні новини</i>')}\n"
    post += f"📰 <i>Джерело: {source}</i>"
    
    return post

def get_football_news():
    """Тестові новини з ротацією"""
    test_news = [
        {
            "title": "Manchester United agree €85m deal for Real Madrid midfielder",
            "description": "Manchester United have reached an agreement with Real Madrid to sign their star midfielder in a deal worth €85 million. The transfer is expected to be completed this week.",
            "source": "Sky Sports"
        },
        {
            "title": "Liverpool's Mohamed Salah suffers hamstring injury, out for 4 weeks", 
            "description": "Liverpool forward Mohamed Salah has suffered a hamstring injury and will miss the next four weeks of action. The Egyptian was in excellent form this season.",
            "source": "BBC Sport"
        },
        {
            "title": "Chelsea sack manager after poor run of results",
            "description": "Chelsea have parted ways with their manager following a string of disappointing results. The club is already looking for a replacement.",
            "source": "ESPN"
        },
        {
            "title": "Barcelona target Arsenal striker in summer transfer window",
            "description": "Barcelona are reportedly interested in signing Arsenal's prolific striker during the summer transfer window. Talks are expected to begin soon.",
            "source": "Goal.com"
        },
        {
            "title": "Bayern Munich's star player scores hat-trick in Champions League",
            "description": "Bayern Munich's forward delivered a stunning hat-trick performance in the Champions League, leading his team to a commanding victory.",
            "source": "UEFA"
        }
    ]
    
    # Ротація новин
    import random
    selected_news = random.choice(test_news)
    
    formatted = format_post(
        selected_news['title'], 
        selected_news['description'], 
        selected_news['source']
    )
    
    print(f"✅ Сформовано пост:")
    print("="*60)
    print(formatted)
    print("="*60)
    
    return [formatted]

def send_message(text):
    """Надсилаємо повідомлення в Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": CHANNEL_ID, 
        "text": text, 
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        response = requests.post(url, data=data, timeout=10)
        return response
    except Exception as e:
        print(f"❌ Помилка надсилання: {e}")
        return None

def run_server():
    """HTTP сервер для Render"""
    port = int(os.environ.get("PORT", 5000))
    server = HTTPServer(('', port), SimpleHTTPRequestHandler)
    print(f"🌐 Сервер запущено на порту {port}")
    server.serve_forever()

def main():
    """Головна функція бота"""
    print("🤖 Five Leagues Bot v2.0 - Запуск...")
    
    # Стартове повідомлення
    start_msg = "🤖 <b>Five Leagues Bot v2.0 запущено!</b> 🇺🇦\n\n⚽ Моніторимо топ-новини футболу..."
    result = send_message(start_msg)
    
    if result and result.status_code == 200:
        print("✅ Стартове повідомлення надіслано")
    else:
        print("❌ Помилка надсилання стартового повідомлення")
        if result:
            print(f"Status: {result.status_code}")
            print(f"Response: {result.text}")
    
    while True:
        try:
            current_time = datetime.now().strftime("%H:%M:%S")
            print(f"🕐 {current_time} - Перевірка новин...")
            
            articles = get_football_news()
            
            if articles:
                best_article = articles[0]
                
                approval_msg = f"📋 <b>НОВИНА НА ПОГОДЖЕННЯ:</b>\n\n{'-'*30}\n\n{best_article}\n\n{'-'*30}\n\n❓ <b>Публікувати?</b> ТАК/НІ"
                
                result = send_message(approval_msg)
                
                if result and result.status_code == 200:
                    print("📤 Новину надіслано на погодження")
                else:
                    print("❌ Помилка надсилання новини")
                    if result:
                        print(f"Status: {result.status_code}")
                        print(f"Response: {result.text}")
            
            print("⏰ Наступна перевірка через 30 хвилин...")
            time.sleep(1800)  # 30 хвилин
            
        except Exception as e:
            print(f"❌ Помилка в основному циклі: {e}")
            time.sleep(300)  # 5 хвилин при помилці

if __name__ == "__main__":
    # Запускаємо HTTP сервер в окремому потоці
    threading.Thread(target=run_server, daemon=True).start()
    
    # Запускаємо бота
    main()
