import requests
import xml.etree.ElementTree as ET

def test_rss_feed():
    """Тестуємо один RSS фід без feedparser"""
    
    rss_url = "https://www.skysports.com/rss/football"
    
    try:
        print(f"🔍 Тестуємо: {rss_url}")
        
        # Запит до RSS
        response = requests.get(rss_url, timeout=10)
        print(f"✅ Статус: {response.status_code}")
        
        # Парсимо XML
        root = ET.fromstring(response.content)
        
        # Знаходимо перший item
        items = root.findall('.//item')
        print(f"📰 Знайдено новин: {len(items)}")
        
        if items:
            first_item = items[0]
            
            # Витягуємо дані
            title = first_item.find('title').text if first_item.find('title') is not None else "No title"
            description = first_item.find('description').text if first_item.find('description') is not None else "No description"
            link = first_item.find('link').text if first_item.find('link') is not None else "No link"
            
            print("\n" + "="*60)
            print("📋 ПЕРША НОВИНА:")
            print("="*60)
            print(f"🏷️ Заголовок: {title}")
            print(f"📝 Опис: {description[:200]}...")
            print(f"🔗 Посилання: {link}")
            print("="*60)
            
            return title, description
        else:
            print("❌ Новини не знайдено")
            
    except Exception as e:
        print(f"❌ Помилка: {e}")
        return None, None

if __name__ == "__main__":
    test_rss_feed()
