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

# Токени та налаштування
TELEGRAM_TOKEN = "7908433957:AAEyetZTWACBNn6t-wHPQwB89p1PtkQEvfg"
CHANNEL_ID = "@fiveleaguesua"
ADMIN_CHAT_ID = "YOUR_ADMIN_CHAT_ID"  # Замініть на ваш chat_id для погодження

# Словник клубів
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

# Допоміжні функції

def get_user_agent():
    """Випадковий User-Agent"""
    agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
        'Mozilla/5.0 (X11; Linux x86_64)'
    ]
    return random.choice(agents)


def translate_text(text):
    """Покращений переклад англійського тексту на українську"""
    try:
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        if len(text) > 400:
            text = text[:400]
        services = [
            "https://api.mymemory.translated.net/get",
            "https://translate.googleapis.com/translate_a/single"
        ]
        for service in services:
            try:
                if "mymemory" in service:
                    params = {'q': text, 'langpair': 'en|uk'}
                    resp = requests.get(service, params=params, timeout=10)
                    data = resp.json()
                    trans = data.get('responseData', {}).get('translatedText')
                    if trans and "WARNING" not in trans.upper():
                        return clean_translation(trans)
                else:
                    params = {'client':'gtx','sl':'en','tl':'uk','dt':'t','q':text}
                    resp = requests.get(service, params=params, timeout=10)
                    res = resp.json()
                    if res and res[0]:
                        trans = ''.join([x[0] for x in res[0] if x[0]])
                        return clean_translation(trans)
            except:
                continue
        return text
    except:
        return text


def clean_translation(text):
    """Очищення та корекція машинного перекладу"""
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
    for eng, ua in replacements.items():
        text = re.sub(re.escape(eng), ua, text, flags=re.IGNORECASE)
    return text


def get_club_name(text):
    """Отримуємо українське ім'я клубу за ключовим словом"""
    t = text.lower()
    for eng, ua in CLUBS.items():
        if eng in t:
            return ua
    return None


def determine_post_type(title, description):
    text = (title + ' ' + description).lower()
    if any(w in text for w in ['transfer','signing','deal','million']): return 'transfer'
    if any(w in text for w in ['injury','ruled out','injured']): return 'injury'
    if any(w in text for w in ['sacked','fired','appointed']): return 'manager'
    if any(w in text for w in ['goal','scored','performance']): return 'performance'
    return 'general'

# Парсери

def parse_bbc_sport():
    """Парсинг новин з BBC Sport"""
    try:
        url = 'https://www.bbc.com/sport/football'
        resp = requests.get(url, headers={'User-Agent':get_user_agent()}, timeout=15)
        soup = BeautifulSoup(resp.content, 'html.parser')
        arts = []
        for art in soup.find_all(['article','div'], class_=re.compile(r'(story|article|item)')):
            try:
                t = art.find(['h1','h2','h3'], class_=re.compile(r'(title|headline)'))
                if not t: continue
                title = t.get_text(strip=True)
                desc = art.find('p').get_text(strip=True) if art.find('p') else ''
                h = hash(title)
                if len(title)>20 and h not in processed_articles:
                    arts.append({'title':title,'description':desc,'source':'BBC Sport','hash':h})
            except:
                continue
        return arts[:5]
    except Exception as e:
        print(f'❌ BBC error: {e}')
        return []

def parse_sky_sports():
    """Парсинг новин з Sky Sports"""
    try:
        url = 'https://www.skysports.com/football/news'
        resp = requests.get(url, headers={'User-Agent':get_user_agent()}, timeout=15)
        soup = BeautifulSoup(resp.content, 'html.parser')
        arts=[]
        for art in soup.find_all(['div','article'], class_=re.compile(r'(news-list|story)')):
            try:
                t = art.find(['h1','h2','h3','h4'])
                if not t: continue
                title = t.get_text(strip=True)
                desc = art.find('p').get_text(strip=True) if art.find('p') else ''
                h=hash(title)
                if len(title)>20 and h not in processed_articles:
                    arts.append({'title':title,'description':desc,'source':'Sky Sports','hash':h})
            except:
                continue
        return arts[:5]
    except Exception as e:
        print(f'❌ Sky error: {e}')
        return []

def parse_marca():
    """Парсинг новин з Marca"""
    try:
        url = 'https://www.marca.com/en/football.html'
        resp = requests.get(url, headers={'User-Agent':get_user_agent()}, timeout=15)
        soup = BeautifulSoup(resp.content, 'html.parser')
        arts=[]
        for art in soup.find_all(['article','div'], class_=re.compile(r'(article|story|news)')):
            try:
                t = art.find(['h1','h2','h3'])
                if not t: continue
                title = t.get_text(strip=True)
                desc = art.find('p').get_text(strip=True) if art.find('p') else ''
                h=hash(title)
                if len(title)>20 and h not in processed_articles:
                    arts.append({'title':title,'description':desc,'source':'Marca','hash':h})
            except:
                continue
        return arts[:5]
    except Exception as e:
        print(f'❌ Marca error: {e}')
        return []

# Збір і вибір новини

def get_football_news():
    """Повертає сформований пост з найкращою новиною"""
    all_arts=[]
    all_arts.extend(parse_bbc_sport()); time.sleep(2)
    all_arts.extend(parse_sky_sports()); time.sleep(2)
    all_arts.extend(parse_marca())
    if all_arts:
        best = max(all_arts, key=lambda x: len(x['title'])+len(x['description']))
        processed_articles.add(best['hash'])
        return [format_post(best['title'], best['description'], best['source'])]
    return []

# Форматування посту

def format_post(title, description, source="Football News"):
    """Формуємо емоційний пост у стилі 'Спортс'"""
    post_type = determine_post_type(title, description)
    emoji_map = {"transfer":"💰","injury":"🏥","manager":"👔","performance":"⚽","general":"📰"}
    emoji = emoji_map.get(post_type, "📰")
    title_ua = translate_text(title)
    desc_ua = translate_text(description) if description else ""
    club = get_club_name(title + " " + description)
    club_str = f"{club} " if club else ""
    headline = f"{emoji} {club_str}{title_ua.strip()}".strip()
    short_desc = desc_ua.strip()
    if len(short_desc)>300: short_desc = short_desc[:300] + "…"
    punch = (
        "🔥 Увімкнув режим бомбардира!" if post_type=="performance" else
        "💥 Це може змінити хід сезону." if post_type=="transfer" else
        "🤕 Втратили ключового гравця." if post_type=="injury" else
        "👀 Слідкуємо за розвитком."
    )
    post = f"<b>{headline}</b>\n\n" + f"{short_desc}\n\n" + f"{punch}\n" + f"📰 Джерело: <i>{source}</i>"
    return post

# Взаємодія з Telegram API

def send_message(text, chat_id=CHANNEL_ID, reply_markup=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data={"chat_id":chat_id,"text":text,"parse_mode":"HTML","disable_web_page_preview":True}
    if reply_markup: data["reply_markup"]=json.dumps(reply_markup)
    try: return requests.post(url,data=data,timeout=10)
    except Exception as e: print(f"❌ Send error: {e}"); return None

def create_approval_keyboard():
    return {"inline_keyboard":[[{"text":"✅ Опублікувати","callback_data":"approve"},{"text":"❌ Відхилити","callback_data":"reject"}]]}

def handle_callback(update):
    try:
        cb=update.get('callback_data')
        mid=update.get('message',{}).get('message_id')
        if cb=='approve' and mid in pending_posts:
            txt=pending_posts[mid]; res=send_message(txt,CHANNEL_ID)
            if res and res.status_code==200: edit_message(mid,"✅ <b>ОПУБЛІКОВАНО!</b>")
            else: edit_message(mid,"❌ Помилка публікації")
            del pending_posts[mid]
        elif cb=='reject' and mid in pending_posts:
            edit_message(mid,"❌ <b>ВІДХИЛЕНО</b>"); del pending_posts[mid]
    except Exception as e:
        print(f"❌ Callback error: {e}")

def edit_message(message_id,new_text):
    url=f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageText"
    data={"chat_id":ADMIN_CHAT_ID,"message_id":message_id,"text":new_text,"parse_mode":"HTML"}
    try: requests.post(url,data=data,timeout=10)
    except Exception as e: print(f"❌ Edit error: {e}")

def check_updates():
    try:
        url=f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
        r=requests.get(url,timeout=10)
        if r.status_code==200:
            for upd in r.json().get('result',[]):
                if 'callback_query' in upd: handle_callback(upd['callback_query'])
    except Exception as e: print(f"❌ Updates error: {e}")

def run_server():
    port=int(os.environ.get('PORT',5000))
    srv=HTTPServer(('',port),SimpleHTTPRequestHandler)
    print(f"🌐 Server on port {port}")
    srv.serve_forever()

def main():
    print("🤖 Five Leagues Bot v3.0 запущено!")
    if ADMIN_CHAT_ID=="YOUR_ADMIN_CHAT_ID": print("⚠️ Set ADMIN_CHAT_ID!")
    start=f"🤖 <b>Five Leagues Bot v3.0 запущено!</b> 🇺🇦\n⚽ Моніторимо топ-новини..."
    res=send_message(start)
    if res and res.status_code==200: print("✅ Start sent")
    while True:
        try:
            print(f"🕐 {datetime.now().strftime('%H:%M:%S')} - Збір новин...")
            check_updates()
            posts=get_football_news()
            if posts:
                msg=f"📋 <b>НОВИНА НА ПОГОДЖЕННЯ:</b>\n\n{'-'*30}\n\n{posts[0]}\n\n{'-'*30}"
                kb=create_approval_keyboard()
                r=send_message(msg,ADMIN_CHAT_ID,kb)
                if r and r.status_code==200:
                    mid=r.json().get('result',{}).get('message_id')
                    if mid: pending_posts[mid]=posts[0]
            time.sleep(1800)
        except Exception as e:
            print(f"❌ Main loop error: {e}")
            time.sleep(300)

if __name__=='__main__':
    threading.Thread(target=run_server,daemon=True).start()
    main()
