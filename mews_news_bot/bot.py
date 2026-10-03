import os
import requests
import feedparser
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from translate import Translator
import sys
import time
import random

sys.stdout.reconfigure(encoding='utf-8')

# ==========================================
# 🛑 Settings
# ==========================================
FB_PAGE_ID = "1330940560103897" 
FB_TOKEN = "EAATquicTHUMBSuJxsZA6iFxkUOLQHvjd5cYAyItoSncJyO2bSpmHBs0dTF2rcSShyllQRRnbssC1AQNyxoIc5euTW3VZCNA8b63xVkL2YxPtNUK2is4pQFMuhf6gxZAsN6u5mkZBb3BrKZCZBeZB60PRnqfiinoGgVA62riIHrbGIPgnd8wuEMD8JqYsP0wjZB5klZAXb2tGAngwHLqsJ6HKu4WNIrVKGjMM43ABVuQXY"

# यहाँ मैंने क्रिकेट, फन (Entertainment), पॉलिटिक्स और ट्रेंडिंग न्यूज़ के अलग-अलग RSS डाल दिए हैं
RSS_FEEDS = [
    "https://timesofindia.indiatimes.com/rssfeeds/54829575.cms", # Cricket (खेल)
    "https://timesofindia.indiatimes.com/rssfeeds/1081479906.cms", # Entertainment (फन/मनोरंजन)
    "https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms", # India/Politics (राजनीति)
    "https://timesofindia.indiatimes.com/rssfeeds/3908999.cms" # Trending/Unique (अजब-गजब/यूनिक)
]

POSTED_FILE = os.path.join(os.path.dirname(__file__), "posted_news.txt")
# ==========================================

def load_posted_news():
    if os.path.exists(POSTED_FILE):
        with open(POSTED_FILE, "r", encoding="utf-8") as f:
            return set(f.read().splitlines())
    return set()

def save_posted_news(link):
    with open(POSTED_FILE, "a", encoding="utf-8") as f:
        f.write(link + "\n")

def clean_html(raw_html):
    soup = BeautifulSoup(raw_html, "html.parser")
    return soup.get_text().strip()

def get_unique_news():
    posted = load_posted_news()
    
    # Randomly किसी एक केटेगरी से न्यूज़ उठाएंगे (Cricket, Fun, Politics)
    random.shuffle(RSS_FEEDS)
    
    for rss_url in RSS_FEEDS:
        print(f"📰 इस केटेगरी से न्यूज़ ढूँढ रहा हूँ: {rss_url}")
        feed = feedparser.parse(rss_url)
        
        for entry in feed.entries:
            if entry.link not in posted:
                eng_title = entry.title
                eng_summary = clean_html(entry.description)
                
                print(f"🇬🇧 English Headline: {eng_title}")
                print("🔄 इसे शानदार हिंदी में ट्रांसलेट कर रहा हूँ...")
                
                try:
                    translator = Translator(to_lang='hi')
                    hi_title = translator.translate(eng_title)
                    hi_summary = translator.translate(eng_summary)
                    
                    # Extract the real news image URL from the RSS feed enclosure
                    img_url = ""
                    if getattr(entry, 'enclosures', None) and len(entry.enclosures) > 0:
                        img_url = entry.enclosures[0].get('href', '')
                    
                    print(f"🇮🇳 Hindi Headline: {hi_title}")
                    return {"title": hi_title, "summary": hi_summary, "link": entry.link, "img_url": img_url}
                except Exception as e:
                    print("❌ ट्रांसलेट करने में एरर आया, दूसरी न्यूज़ देखते हैं...")
                    continue
                    
    print("❌ अभी कोई नई यूनिक न्यूज़ नहीं मिली!")
    return None

def create_infographic(news):
    print("🎨 इन्फोग्राफिक इमेज बना रहा हूँ...")
    html_file = os.path.join(os.path.dirname(__file__), "template.html")
    img_file = os.path.join(os.path.dirname(__file__), "latest_news.png")
    
    with open(html_file, "r", encoding="utf-8") as f:
        html_content = f.read()
    
    # HTML में हेडलाइन और रियल न्यूज़ इमेज डालना
    html_content = html_content.replace("यहाँ न्यूज़ की बड़ी हेडलाइन आएगी", news['title'])
    
    if news.get('img_url'):
        html_content = html_content.replace("यहाँ_इमेज_आएगी", news['img_url'])
    else:
        # अगर न्यूज़ में फोटो नहीं है, तो कोई डिफ़ॉल्ट डार्क फोटो डाल सकते हैं
        html_content = html_content.replace("यहाँ_इमेज_आएगी", "https://images.unsplash.com/photo-1495020689067-958852a7765e?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80")
    
    
    # Playwright से HTML को Image में बदलना
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 800, "height": 1000})
        page.set_content(html_content)
        page.screenshot(path=img_file)
        browser.close()
        
    print(f"✅ इमेज तैयार है: {img_file}")
    return img_file

def post_to_facebook(image_path, news):
    print("🚀 फेसबुक पर पोस्ट कर रहा हूँ...")
    url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/photos"
    
    # अब यहाँ कैप्शन में कोई लिंक (Link) नहीं है! 🚫🔗
    caption = f"🚨 {news['title']}\n\n{news['summary']}\n\n#MewsNews #HindiNews #BreakingNews #Trending"
    
    payload = {
        'message': caption,
        'access_token': FB_TOKEN
    }
    
    with open(image_path, 'rb') as img:
        files = {'source': img}
        response = requests.post(url, data=payload, files=files)
        
    if response.status_code == 200:
        print("✅ फेसबुक पर सफलतापूर्वक पोस्ट हो गया!")
        print("Facebook Post ID:", response.json().get('id'))
        return True
    else:
        print("❌ पोस्ट करने में एरर आया:")
        print(response.json())
        return False

def main():
    print("🚀 GitHub Actions / बोट चालू हो गया है! एक नई न्यूज़ चेक कर रहा हूँ...")
    
    news = get_unique_news()
    
    if news:
        img_path = create_infographic(news)
        success = post_to_facebook(img_path, news)
        
        if success:
            save_posted_news(news['link'])
            print("✅ सक्सेस! न्यूज़ पोस्ट हो गई।")
        else:
            print("❌ पोस्ट फेल हो गई।")
    else:
        print("🤷‍♂️ कोई नई न्यूज़ नहीं मिली।")

if __name__ == "__main__":
    main()
