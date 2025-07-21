import os
import requests
import time
from datetime import datetime
import re
import json
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from bs4 import BeautifulSoup
import random

TELEGRAM_TOKEN = "7908433957:AAEyetZTWACBNn6t-wHPQwB89p1PtkQEvfg"
CHANNEL_ID = "@fiveleaguesua"
ADMIN_CHAT_ID = "YOUR_ADMIN_CHAT_ID"  # Твій chat_id для погодження

CLUBS = {
    'manchester united': '🔴 Манчестер Юнайтед',
    'manchester city': '🔵 Манчестер Сіті', 
    'liverpool': '🔴 Ліверпуль',
    'chelsea': '🔵 Челсі',
    'arsenal': '🔴 Арсенал',
    'tottenham': '⚪ Тоттенгем',
    'real madrid': '⚪ Реал Мадрид',
    'barcelona': '🔵 Барселона',
    'atletico madrid': '🔴 Атлетіко Мадрид',
    'juventus': '⚫ Ювентус',
    'milan': '🔴 Мілан',
    'inter milan': '🔵 Інтер',
    'bayern munich': '🔴 Баварія',
    'psg': '🔵 ПСЖ',
    'borussia dortmund': '🟡 Борусія Дортмунд'
}

processed_articles = set()
pending_posts = {}

def get_user_agent():
    """Випадковий User-Agent"""
    agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    ]
    return random.choice(agents)

def translate_text(text):
    """Покращений переклад"""
    try:
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        if len(text) > 400:
            text = text[:400]
            
        # Спробуємо кілька сервісів
        services = [
            "https://api.mymemory.translated.net/get",
            "https://translate.googleapis.com/translate_a/single"
        ]
        
        for service_url in services:
            try:
                if "mymemory" in service_url:
                    params = {'q': text, 'langpair': 'en|uk'}
                    response = requests.get(service_url, params=params, timeout=10)
                    data = response.json()
                    
                    if 'responseData' in data:
                        translated = data['responseData']['translatedText']
                        if "MYMEMORY WARNING" not in translated.upper():
                            return clean_translation(translated)
                            
                elif "googleapis" in service_url:
                    params = {
                        'client': 'gtx',
                        'sl': 'en',
                        'tl': 'uk',
                        'dt': 't',
                        'q': text
                    }
                    response = requests.get(service_url, params=params, timeout=10)
                    result = response.json()
                    if result and len(result) > 0 and len(result[0]) > 0:
                        translated = ''.join([x[0] for x in result[0] if x[0]])
                        return clean_translation(translated)
                        
            except:
                continue
                
        return text
    except:
        return text

def clean_translation(text):
    """Очищення перекладу"""
    # Заміни для кращої української
    replacements = {
        'інтернаціонале': 'міжнародний',
        'реал мадрид': 'Реал Мадрид',
        'барселона': 'Барселона',
        'манчестер юнайтед': 'Манчестер Юнайтед',
        'ліверпуль': 'Ліверпуль',
        'челсі': 'Челсі',
        'арсенал': 'Арсенал',
        'баварія мюнхен': 'Баварія',
        'пс жермен': 'ПСЖ'
    }
    
    text_lower = text.lower()
    for eng, ua in replacements.items():
        text = re.sub(re.escape(eng), ua, text, flags=re.IGNORECASE)
    
    return text

def get_club_name(text):
    """Отримуємо українське ім'я клубу"""
    text_lower = text.lower()
    for eng_name, ua_name in CLUBS.items():
        if eng_name in text_lower:
            return ua_name
    return None

def is_quality_news(title, description):
    """ШІ-редактор: чи варта новина публікації?"""
    text = (title + " " + description).lower()
    
    # Обов'язкові елементи якісної новини
    has_player_name = bool(re.search(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b', title + " " + description))
    has_money = bool(re.search(r'(€|£|\$)\d+|million|billion', text))
    has_concrete_info = any(word in text for word in ['signed', 'agreed', 'confirmed', 'official', 'announced'])
    
    # Відкидаємо погані новини
    bad_indicators = ['rumour', 'reportedly', 'could', 'might', 'possible', 'potential', 'linked with']
    has_bad_indicators = any(indicator in text for indicator in bad_indicators)
    
    # Цікаві теми
    interesting_topics = ['transfer', 'signing', 'injury', 'sacked', 'appointed', 'record', 'goal', 'hat-trick']
    has_interesting_topic = any(topic in text for topic in interesting_topics)
    
    # Логіка вибору
    score = 0
    if has_player_name: score += 3
    if has_money: score += 2
    if has_concrete_info: score += 2
    if has_interesting_topic: score += 1
    if has_bad_indicators: score -= 2
    
    return score >= 4

def parse_bbc_sport():
    """Парсинг BBC Sport Football"""
    try:
        url = "https://www.bbc.com/sport/football"
        headers = {'User-Agent': get_user_agent()}
        response = requests.get(url, headers=headers, timeout=15)
        
        soup = BeautifulSoup(response.content, 'html.parser')
        articles = []
        
        # Шукаємо статті
        for article in soup.find_all(['article', 'div'], class_=re.compile(r'(story|article|item)')):
            try:
                title_elem = article.find(['h1', 'h2', 'h3'], class_=re.compile(r'(title|headline)'))
                if not title_elem:
                    continue
                    
                title = title_elem.get_text(strip=True)
                description = ""
                
                # Шукаємо опис
                desc_elem = article.find('p')
                if desc_elem:
                    description = desc_elem.get_text(strip=True)
                
                if len(title) > 20 and is_quality_news(title, description):
                    article_hash = hash(title)
                    if article_hash not in processed_articles:
                        articles.append({
                            'title': title,
                            'description': description,
                            'source': 'BBC Sport',
                            'hash': article_hash
                        })
                        
            except:
                continue
                
        return articles[:5]  # Топ-5
        
    except Exception as e:
        print(f"❌ Помилка парсингу BBC: {e}")
        return []

def parse_sky_sports():
    """Парсинг Sky Sports"""
    try:
        url = "https://www.skysports.com/football/news"
        headers = {'User-Agent': get_user_agent()}
        response = requests.get(url, headers=headers, timeout=15)
        
        soup = BeautifulSoup(response.content, 'html.parser')
        articles = []
        
        for article in soup.find_all(['div', 'article'], class_=re.compile(r'(news-list|story)')):
            try:
                title_elem = article.find(['h1', 'h2', 'h3', 'h4'])
                if not title_elem:
                    continue
                    
                title = title_elem.get_text(strip=True)
                description = ""
                
                desc_elem = article.find('p')
                if desc_elem:
                    description = desc_elem.get_text(strip=True)
                
                if len(title) > 20 and is_quality_news(title, description):
                    article_hash = hash(title)
                    if article_hash not in processed_articles:
                        articles.append({
                            'title': title,
                            'description': description,
                            'source': 'Sky Sports',
                            'hash': article_hash
                        })
                        
            except:
                continue
                
        return articles[:5]
        
    except Exception as e:
        print(f"❌ Помилка парсингу Sky Sports: {e}")
        return []

def parse_marca():
    """Парсинг Marca"""
    try:
        url = "https://www.marca.com/en/football.html"
        headers = {'User-Agent': get_user_agent()}
        response = requests.get(url, headers=headers, timeout=15)
        
        soup = BeautifulSoup(response.content, 'html.parser')
        articles = []
        
        for article in soup.find_all(['article', 'div'], class_=re.compile(r'(article|story|news)')):
            try:
                title_elem = article.find(['h1', 'h2', 'h3'])
                if not title_elem:
                    continue
                    
                title = title_elem.get_text(strip=True)
                description = ""
                
                desc_elem = article.find('p')
                if desc_elem:
                    description = desc_elem.get_text(strip=True)
                
                if len(title) > 20 and is_quality_news(title, description):
                    article_hash = hash(title)
                    if article_hash not in processed_articles:
                        articles.append({
                            'title': title,
                            'description': description,
                            'source': 'Marca',
                            'hash': article_hash
                        })
                        
            except:
                continue
                
        return articles[:5]
        
    except Exception as e:
        print(f"❌ Помилка парсингу Marca: {e}")
        return []

def get_football_news():
    """Збираємо новини з усіх джерел"""
    all_articles = []
    
    print("📡 BBC Sport...")
    all_articles.extend(parse_bbc_sport())
    
    time.sleep(2)  # Пауза між запитами
    
    print("📡 Sky Sports...")
    all_articles.extend(parse_sky_sports())
    
    time.sleep(2)
    
    print("📡 Marca...")
    all_articles.extend(parse_marca())
    
    # Сортуємо за якістю
    if all_articles:
        # Відбираємо найкращу
        best_article = max(all_articles, key=lambda x: len(x['title']) + len(x.get('description', '')))
        processed_articles.add(best_article['hash'])
        return [format_post(best_article['title'], best_article['description'], best_article['source'])]
    
    return []

def format_post(title, description, source="Football News"):
    """Формуємо емоційний пост у стилі 'Спортс'"""
    post_type = determine_post_type(title, description)

    emoji_map = {
        "transfer": "💰",
        "injury": "🏥", 
        "manager": "👔",
        "performance": "⚽",
        "general": "📰"
    }
    emoji = emoji_map.get(post_type, "📰")

    # Переклад
    title_ua = translate_text(title)
    desc_ua = translate_text(description) if description else ""

    # Виділення клубу
    club = get_club_name(title + " " + description)
    club_str = f"{club} " if club else ""

    # Заголовок
    headline = f"{emoji} {club_str}{title_ua.strip()}".strip()

    # Основний текст — коротко, по ділу, емоційно
    short_desc = desc_ua.strip()
    if len(short_desc) > 300:
        short_desc = short_desc[:300] + "…"

    # Фіналка
    punch = "🔥 Увімкнув режим бомбардира!" if post_type == "performance" else \
            "💥 Це може змінити хід сезону." if post_type == "transfer" else \
            "🤕 Втратили ключового гравця." if post_type == "injury" else \
            "👀 Слідкуємо за розвитком."    

    # Формуємо пост
    post = f"<b>{headline}</b>\n\n"

"
    post += f"{short_desc}

"
    post += f"{punch}
"
    post += f"📰 Джерело: <i>{source}</i>"

    return post

def send_message(text, chat_id=CHANNEL_ID, reply_markup=None):
    """Надсилаємо повідомлення в Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup)
    
    try:
        response = requests.post(url, data=data, timeout=10)
        return response
    except Exception as e:
        print(f"❌ Помилка надсилання: {e}")
        return None

def create_approval_keyboard():
    """Створюємо кнопки для погодження"""
    return {
        "inline_keyboard": [
            [
                {"text": "✅ Опублікувати", "callback_data": "approve"},
                {"text": "❌ Відхилити", "callback_data": "reject"}
            ]
        ]
    }

def handle_callback(update):
    """Обробка натискання кнопок"""
    try:
        callback_data = update.get('callback_data')
        message_id = update.get('message', {}).get('message_id')
        
        if callback_data == 'approve' and message_id in pending_posts:
            # Публікуємо пост
            post_text = pending_posts[message_id]
            result = send_message(post_text, CHANNEL_ID)
            
            if result and result.status_code == 200:
                # Редагуємо повідомлення з підтвердженням
                edit_message(message_id, "✅ <b>ОПУБЛІКОВАНО!</b>")
                print("✅ Пост опубліковано!")
            else:
                edit_message(message_id, "❌ Помилка публікації")
                
            del pending_posts[message_id]
            
        elif callback_data == 'reject' and message_id in pending_posts:
            edit_message(message_id, "❌ <b>ВІДХИЛЕНО</b>")
            del pending_posts[message_id]
            print("❌ Пост відхилено")
            
    except Exception as e:
        print(f"❌ Помилка обробки callback: {e}")

def edit_message(message_id, new_text):
    """Редагуємо повідомлення"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageText"
    data = {
        "chat_id": ADMIN_CHAT_ID,
        "message_id": message_id,
        "text": new_text,
        "parse_mode": "HTML"
    }
    
    try:
        requests.post(url, data=data, timeout=10)
    except Exception as e:
        print(f"❌ Помилка редагування: {e}")

def check_updates():
    """Перевіряємо оновлення Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            for update in data.get('result', []):
                if 'callback_query' in update:
                    handle_callback(update['callback_query'])
                    
    except Exception as e:
        print(f"❌ Помилка перевірки оновлень: {e}")

def run_server():
    """HTTP сервер для Render"""
    port = int(os.environ.get("PORT", 5000))
    server = HTTPServer(('', port), SimpleHTTPRequestHandler)
    print(f"🌐 Сервер запущено на порту {port}")
    server.serve_forever()

def main():
    """Головна функція бота"""
    print("🤖 Five Leagues Bot v3.0 - Запуск...")
    
    # Перевіряємо токен
    if ADMIN_CHAT_ID == "8142520596":
        print("⚠️ УВАГА: Встановіть ADMIN_CHAT_ID!")
    
    # Стартове повідомлення
    start_msg = "🤖 <b>Five Leagues Bot v3.0 запущено!</b> 🇺🇦\n\n⚽ Моніторимо BBC Sport, Sky Sports, Marca..."
    result = send_message(start_msg)
    
    if result and result.status_code == 200:
        print("✅ Стартове повідомлення надіслано")
    
    while True:
        try:
            current_time = datetime.now().strftime("%H:%M:%S")
            print(f"🕐 {current_time} - Збираємо новини...")
            
            # Перевіряємо callback'и
            check_updates()
            
            articles = get_football_news()
            
            if articles:
                best_article = articles[0]
                
                # Надсилаємо на погодження
                approval_msg = f"📋 <b>НОВИНА НА ПОГОДЖЕННЯ:</b>\n\n{'-'*40}\n\n{best_article}\n\n{'-'*40}"
                
                keyboard = create_approval_keyboard()
                result = send_message(approval_msg, ADMIN_CHAT_ID, keyboard)
                
                if result and result.status_code == 200:
                    message_data = result.json()
                    message_id = message_data.get('result', {}).get('message_id')
                    if message_id:
                        pending_posts[message_id] = best_article
                        print("📤 Новину надіслано на погодження")
                else:
                    print("❌ Помилка надсилання новини на погодження")
            else:
                print("📰 Нових якісних новин не знайдено")
            
            print("⏰ Наступна перевірка через 30 хвилин...")
            
            # Перевіряємо оновлення кожні 30 секунд протягом 30 хвилин
            for _ in range(60):  # 60 * 30 секунд = 30 хвилин
                time.sleep(30)
                check_updates()
            
        except Exception as e:
            print(f"❌ Помилка в основному циклі: {e}")
            time.sleep(300)  # 5 хвилин при помилці

if __name__ == "__main__":
    # Запускаємо HTTP сервер в окремому потоці
    threading.Thread(target=run_server, daemon=True).start()
    
    # Запускаємо бота
    main()
