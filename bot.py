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
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
        'Mozilla/5.0 (X11; Linux x86_64)'
    ]
    return random.choice(agents)

def translate_text(text):
    """Покращений переклад"""
    try:
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        if len(text) > 400:
            text = text[:400]
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
    """Отримуємо українське ім'я клубу"""
    text_lower = text.lower()
    for eng_name, ua_name in CLUBS.items():
        if eng_name in text_lower:
            return ua_name
    return None

def is_quality_news(title, description):
    """Чи варта новина публікації?"""
    text = (title + " " + description).lower()
    has_player_name = bool(re.search(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b', text))
    has_money = bool(re.search(r'(€|£|\$)\d+|million|billion', text))
    has_concrete_info = any(w in text for w in ['signed','agreed','confirmed','official','announced'])
    bad_indicators = ['rumour','reportedly','could','might','possible','potential','linked with']
    has_bad = any(ind in text for ind in bad_indicators)
    topics = ['transfer','signing','injury','sacked','appointed','record','goal','hat-trick']
    has_topic = any(t in text for t in topics)
    score = 0
    if has_player_name: score += 3
    if has_money: score += 2
    if has_concrete_info: score += 2
    if has_topic: score += 1
    if has_bad: score -= 2
    return score >= 4

def parse_bbc_sport():
    """Парсинг BBC Sport"""
    try:
        url = "https://www.bbc.com/sport/football"
        headers = {'User-Agent': get_user_agent()}
        resp = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(resp.content, 'html.parser')
        arts = []
        for art in soup.find_all(['article','div'], class_=re.compile(r'(story|article|item)')):
            try:
                t = art.find(['h1','h2','h3'], class_=re.compile(r'(title|headline)'))
                if not t: continue
                title = t.get_text(strip=True)
                desc = art.find('p').get_text(strip=True) if art.find('p') else ""
                if len(title)>20 and is_quality_news(title, desc):
                    h = hash(title)
                    if h not in processed_articles:
                        arts.append({'title':title,'description':desc,'source':'BBC Sport','hash':h})
            except:
                continue
        return arts[:5]
    except Exception as e:
        print(f"❌ BBC error: {e}")
        return []

def parse_sky_sports():
    """Парсинг Sky Sports"""
    try:
        url = "https://www.skysports.com/football/news"
        headers = {'User-Agent': get_user_agent()}
        resp = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(resp.content, 'html.parser')
        arts = []
        for art in soup.find_all(['div','article'], class_=re.compile(r'(news-list|story)')):
            try:
                t = art.find(['h1','h2','h3','h4'])
                if not t: continue
                title = t.get_text(strip=True)
                desc = art.find('p').get_text(strip=True) if art.find('p') else ""
                if len(title)>20 and is_quality_news(title, desc):
                    h = hash(title)
                    if h not in processed_articles:
                        arts.append({'title':title,'description':desc,'source':'Sky Sports','hash':h})
            except:
                continue
        return arts[:5]
    except Exception as e:
        print(f"❌ Sky error: {e}")
        return []

def parse_marca():
    """Парсинг Marca"""
    try:
        url = "https://www.marca.com/en/football.html"
        headers = {'User-Agent': get_user_agent()}
        resp = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(resp.content, 'html.parser')
        arts = []
        for art in soup.find_all(['article','div'], class_=re.compile(r'(article|story|news)')):
            try:
                t = art.find(['h1','h2','h3'])
                if not t: continue
                title = t.get_text(strip=True)
                desc = art.find('p').get_text(strip=True) if art.find('p') else ""
                if len(title)>20 and is_quality_news(title, desc):
                    h = hash(title)
                    if h not in processed_articles:
                        arts.append({'title':title,'description':desc,'source':'Marca','hash':h})
            except:
                continue
        return arts[:5]
    except Exception as e:
        print(f"❌ Marca error: {e}")
        return []

def get_football_news():
    """Збираємо новини"""
    all_arts = []
    all_arts.extend(parse_bbc_sport())
    time.sleep(2)
    all_arts.extend(parse_sky_sports())
    time.sleep(2)
    all_arts.extend(parse_marca())
    if all_arts:
        best = max(all_arts, key=lambda x: len(x['title'])+len(x['description']))
        processed_articles.add(best['hash'])
        return [format_post(best['title'], best['description'], best['source'])]
    return []

def format_post(title, description, source="Football News"):
    """Формуємо емоційний пост у стилі 'Спортс'"""
    post_type = determine_post_type(title, description)

    em...
