import os
import requests
import feedparser
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import sys
import time
import json
import random
import asyncio
import subprocess

sys.stdout.reconfigure(encoding='utf-8')

# ==========================================
# 🛑 Settings & Configuration
# ==========================================
FB_PAGE_ID = "1330940560103897" 
FB_TOKEN = "EAATquicTHUMBSrIA2GYyZBMEZAAiRWIOaMbmoNEQWuZBJ7ZBPWo7KctMX5KUCy3Iw2z9JZBUsJYwIbzH7fxFcdpSos0UOf7GV9BNdwuLFX5YzFBexNZC5xMVX5SqOChHa9ofF3uziDSZCujvtX0wifbNjjOIZCSsZCIZCrGwiFITrpnj8Lkibv2vomCpzcUXOC1PZAWAAkRsEkS"

RSS_FEEDS = [
    "https://timesofindia.indiatimes.com/rssfeeds/54829575.cms",     # Cricket (खेल)
    "https://timesofindia.indiatimes.com/rssfeeds/1081479906.cms",   # Entertainment (मनोरंजन/फन)
    "https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms",  # India/Politics (राजनीति)
    "https://timesofindia.indiatimes.com/rssfeeds/3908999.cms"       # Trending/Unique (अजब-गजब)
]

INTERVAL_SECONDS = 1800  # 30 मिनट (30 * 60)
POSTED_FILE = os.path.join(os.path.dirname(__file__), "posted_news.txt")
STATE_FILE = os.path.join(os.path.dirname(__file__), "bot_state.json")
# ==========================================

def load_posted_news():
    if os.path.exists(POSTED_FILE):
        with open(POSTED_FILE, "r", encoding="utf-8") as f:
            return set(f.read().splitlines())
    return set()

def save_posted_news(link):
    with open(POSTED_FILE, "a", encoding="utf-8") as f:
        f.write(link + "\n")

def load_bot_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    # डिफ़ॉल्ट: पहली पोस्ट इमेज होगी
    return {"last_post_time": 0, "last_post_type": "reel"}

def save_bot_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

def clean_html(raw_html):
    soup = BeautifulSoup(raw_html, "html.parser")
    return soup.get_text().strip()

def translate_to_hindi(text):
    if not text:
        return ""
    # 1. Google Translate direct RPC (Lightning fast & 100% reliable)
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {"client": "gtx", "sl": "en", "tl": "hi", "dt": "t", "q": text}
        r = requests.get(url, params=params, timeout=12)
        if r.status_code == 200:
            return "".join([part[0] for part in r.json()[0] if part[0]])
    except Exception:
        pass
        
    # 2. Fallback to googletrans
    try:
        from googletrans import Translator
        return Translator().translate(text, dest='hi').text
    except Exception:
        return text

def translate_long_article(text, max_chars=1200):
    if not text:
        return ""
    text = text[:max_chars].strip()
    sentences = [s.strip() for s in text.split('. ') if s.strip()]
    
    chunks = []
    current_chunk = ""
    for s in sentences:
        if len(current_chunk) + len(s) < 400:
            current_chunk += s + ". "
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = s + ". "
    if current_chunk:
        chunks.append(current_chunk.strip())
        
    translated_parts = []
    for chunk in chunks:
        trans = translate_to_hindi(chunk)
        if trans:
            translated_parts.append(trans)
            
    return "\n\n".join(translated_parts)

def extract_article_details(link):
    """वेबपेज से रियल HD फोटो (og:image) और पूरी अनकट न्यूज़ निकालना"""
    body = ""
    img_url = ""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        r = requests.get(link, headers=headers, timeout=12)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # 1. Real HD News Photo from og:image
            og_img = soup.find('meta', {'property': 'og:image'})
            if og_img and og_img.get('content') and 'http' in og_img.get('content', ''):
                img_url = og_img['content'].strip()
                
            # 2. Full Article Body from JSON-LD
            scripts = soup.find_all('script', type='application/ld+json')
            for s in scripts:
                try:
                    if not s.string: 
                        continue
                    data = json.loads(s.string)
                    if isinstance(data, dict) and 'articleBody' in data and len(data['articleBody']) > 100:
                        body = data['articleBody'].strip()
                        break
                except Exception:
                    continue
    except Exception as e:
        print(f"⚠️ Article details extract notice: {e}")
        
    return body, img_url

def get_unique_news():
    posted = load_posted_news()
    random.shuffle(RSS_FEEDS)
    
    for rss_url in RSS_FEEDS:
        print(f"📰 RSS फ़ीड चेक कर रहा हूँ: {rss_url}")
        feed = feedparser.parse(rss_url)
        
        for entry in feed.entries:
            if entry.link not in posted:
                eng_title = entry.title
                eng_summary = clean_html(entry.description)
                
                print(f"🇬🇧 English Headline: {eng_title}")
                print("🔄 इसे शानदार हिंदी में ट्रांसलेट कर रहा हूँ...")
                
                try:
                    hi_title = translate_to_hindi(eng_title)
                    hi_summary = translate_to_hindi(eng_summary)
                    
                    # 1. पूरी विस्तृत न्यूज़ और रियल HD फोटो निकालना
                    full_eng_text, real_photo = extract_article_details(entry.link)
                    
                    if full_eng_text:
                        print("📖 पूरी खबर (Full Article) मिल गई! हिंदी में ट्रांसलेट कर रहा हूँ...")
                        hi_full_story = translate_long_article(full_eng_text)
                    else:
                        hi_full_story = hi_summary
                        
                    # रियल न्यूज़ इमेज URL सेट करना (og:image को प्राथमिकता)
                    img_url = real_photo
                    if not img_url and getattr(entry, 'enclosures', None) and len(entry.enclosures) > 0:
                        img_url = entry.enclosures[0].get('href', '')
                        
                    print(f"📸 रियल फोटो URL: {img_url[:60]}..." if img_url else "📸 डिफ़ॉल्ट बैकग्राउंड उपयोग होगा")
                    print(f"🇮🇳 Hindi Headline: {hi_title}")
                    
                    return {
                        "title": hi_title,
                        "summary": hi_summary,
                        "full_story": hi_full_story,
                        "link": entry.link,
                        "img_url": img_url
                    }
                except Exception as e:
                    print(f"❌ ट्रांसलेट करने में एरर आया: {e}, दूसरी न्यूज़ देखते हैं...")
                    continue
                    
    print("❌ अभी कोई नई यूनिक न्यूज़ नहीं मिली!")
    return None

def create_image_post(news):
    print("🎨 [Photo Post] 800x1000 इन्फोग्राफिक इमेज बना रहा हूँ...")
    html_file = os.path.join(os.path.dirname(__file__), "template.html")
    img_file = os.path.join(os.path.dirname(__file__), "latest_news.png")
    
    with open(html_file, "r", encoding="utf-8") as f:
        html_content = f.read()
    
    html_content = html_content.replace("यहाँ न्यूज़ की बड़ी हेडलाइन आएगी", news['title'])
    
    if news.get('img_url'):
        html_content = html_content.replace("यहाँ_इमेज_आएगी", news['img_url'])
    else:
        html_content = html_content.replace("यहाँ_इमेज_आएगी", "https://images.unsplash.com/photo-1585829365295-ab7cd400c167?w=1200")
        
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 800, "height": 1000})
        page.set_content(html_content)
        page.screenshot(path=img_file)
        browser.close()
        
    print(f"✅ इमेज तैयार है: {img_file}")
    return img_file

def build_anchor_script(news):
    """AI एंकर के लिए पूरा रियलिस्टिक न्यूज़ बुलेटिन स्क्रिप्ट (सिर्फ टाइटल नहीं)"""
    title = news['title'].strip()
    full_story = news.get('full_story', news.get('summary', '')).strip()
    
    # फुल स्टोरी से 1-2 महत्वपूर्ण और मुख्य वाक्य निकालना
    clean_sentences = [
        s.strip() for s in full_story.replace('\n', ' ').split('।') 
        if len(s.strip()) > 15
    ]
    
    context = ""
    if clean_sentences:
        context = "। ".join(clean_sentences[:2]) + "।"
    else:
        context = news.get('summary', '')
        
    script = f"नमस्कार, मेव्स न्यूज़ में बड़ी खबर। {title}। {context} ताज़ा और निष्पक्ष खबरों के लिए अभी जुड़े रहें मेव्स न्यूज़ के साथ।"
    return script

def generate_voiceover(text, audio_path):
    import edge_tts
    async def _speak():
        # hi-IN-MadhurNeural: बहुत ही स्पष्ट, गहरा और ह्यूमन-लाइक न्यूज़ एंकर वॉइस
        # rate="+45%": एग्जैक्ट 1.5x फास्ट और एनर्जेटिक स्पीड (जैसा यूट्यूब/इंस्टा रील्स में होता है)
        communicate = edge_tts.Communicate(text, "hi-IN-MadhurNeural", rate="+45%")
        await communicate.save(audio_path)
    asyncio.run(_speak())

def get_audio_duration(audio_path):
    try:
        cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'json', audio_path]
        r = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(json.loads(r.stdout)['format']['duration'])
    except Exception:
        return 12.0

def create_reel_video(news):
    print("🎬 [Reel Post] 9:16 वर्टिकल रील, रियल फुटेज/फोटो मोशन और 1.5x AI वॉइसओवर बना रहा हूँ...")
    html_file = os.path.join(os.path.dirname(__file__), "template_reel.html")
    frame_img_file = os.path.join(os.path.dirname(__file__), "reel_frame.png")
    audio_file = os.path.join(os.path.dirname(__file__), "reel_voice.mp3")
    video_file = os.path.join(os.path.dirname(__file__), "latest_reel.mp4")
    
    with open(html_file, "r", encoding="utf-8") as f:
        html_content = f.read()
        
    html_content = html_content.replace("यहाँ न्यूज़ की बड़ी हेडलाइन आएगी", news['title'])
    html_content = html_content.replace("यहाँ_शॉर्ट_समरी_आएगी", news['summary'])
    
    # असली रियल फोटो लगाना
    photo_url = news.get('img_url') or "https://images.unsplash.com/photo-1585829365295-ab7cd400c167?w=1200"
    html_content = html_content.replace("यहाँ_इमेज_आएगी", photo_url)
        
    # 1. 9:16 रील फ्रेम कैप्चर करना (720x1280)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 720, "height": 1280})
        page.set_content(html_content)
        page.screenshot(path=frame_img_file)
        browser.close()
        
    # 2. पूरा न्यूज़ एंकर स्क्रिप्ट और 1.5x फास्ट वॉइसओवर
    voice_script = build_anchor_script(news)
    print(f"🎙️ AI न्यूज़ एंकर वॉइसओवर (1.5x स्पीड) जनरेट कर रहा हूँ: '{voice_script[:75]}...'")
    generate_voiceover(voice_script, audio_file)
    
    # 3. FFmpeg से स्मूथ मोशन/ज़ूम (Ken Burns Real Camera Push) रेंडर करना
    audio_dur = get_audio_duration(audio_file)
    total_frames = int(audio_dur * 25) + 25
    print(f"⚡ FFmpeg से Cinematic Motion HD Reel ({audio_dur:.1f}s) तैयार कर रहा हूँ...")
    
    cmd = [
        'ffmpeg', '-y',
        '-loop', '1',
        '-i', frame_img_file,
        '-i', audio_file,
        '-filter_complex', f"zoompan=z='min(zoom+0.0006,1.10)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={total_frames}:s=720x1280:fps=25",
        '-c:v', 'libx264', '-preset', 'veryfast',
        '-c:a', 'aac', '-b:a', '192k',
        '-pix_fmt', 'yuv420p',
        '-shortest',
        '-movflags', '+faststart',
        video_file
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"✅ रियल रील वीडियो तैयार है: {video_file} ({os.path.getsize(video_file)} bytes)")
    return video_file

def build_full_caption(news):
    """कैप्शन में पूरी खबर विस्तार से"""
    return f"""🚨 【बड़ी खबर】
{news['title']}

📖 【पूरी खबर विस्तार से】
{news['full_story']}

📌 ताज़ा और निष्पक्ष खबरों के लिए Mews News को फॉलो करें!
#MewsNews #HindiNews #BreakingNews #Trending #ViralNews #India"""

def post_photo_to_facebook(image_path, news):
    print("🚀 फेसबुक पर फोटो पोस्ट कर रहा हूँ...")
    url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/photos"
    caption = build_full_caption(news)
    
    payload = {
        'message': caption,
        'access_token': FB_TOKEN
    }
    
    with open(image_path, 'rb') as img:
        files = {'source': img}
        response = requests.post(url, data=payload, files=files)
        
    if response.status_code == 200:
        print("✅ फोटो सफलतापूर्वक पोस्ट हो गई!")
        print("Facebook Post ID:", response.json().get('id'))
        return True
    else:
        print("❌ फोटो पोस्ट करने में एरर आया:", response.json())
        return False

def post_reel_to_facebook(video_path, news):
    print("🚀 फेसबुक पर रील (Video) पोस्ट कर रहा हूँ...")
    url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/videos"
    caption = build_full_caption(news)
    
    payload = {
        'description': caption,
        'access_token': FB_TOKEN
    }
    
    with open(video_path, 'rb') as vid:
        files = {'source': vid}
        response = requests.post(url, data=payload, files=files)
        
    if response.status_code == 200:
        print("✅ रील वीडियो सफलतापूर्वक पोस्ट हो गया!")
        print("Facebook Video/Reel ID:", response.json().get('id'))
        return True
    else:
        print("❌ रील पोस्ट करने में एरर आया:", response.json())
        return False

def main():
    print("🚀 Mews News Auto Poster शुरू हो रहा है...")
    force_run = "--force" in sys.argv or os.environ.get("FORCE_RUN") == "true"
    
    state = load_bot_state()
    now = time.time()
    last_post_time = state.get("last_post_time", 0)
    last_post_type = state.get("last_post_type", "image") # रील टेस्ट के लिए डिफ़ॉल्ट इमेज से शुरू
    elapsed = now - last_post_time
    
    if not force_run and elapsed < INTERVAL_SECONDS:
        remaining_min = int((INTERVAL_SECONDS - elapsed) / 60)
        print(f"⏳ अभी 30 मिनट नहीं हुए हैं (पिछली पोस्ट के बाद {int(elapsed/60)} मिनट बीते हैं)।")
        print(f"⏳ अगली पोस्ट {remaining_min} मिनट बाद होगी। बोट अभी रेस्ट कर रहा है।")
        return
        
    # अल्टरनेटिंग साइकिल: अगर पिछली बार इमेज थी तो अब रील, अगर रील थी तो अब इमेज
    next_type = "reel" if last_post_type == "image" else "image"
    print(f"🎯 इस बार की पोस्ट का प्रकार: {next_type.upper()} (पिछली पोस्ट थी: {last_post_type.upper()})")
    
    news = get_unique_news()
    if not news:
        print("🤷‍♂️ कोई नई न्यूज़ नहीं मिली।")
        return
        
    success = False
    if next_type == "image":
        img_path = create_image_post(news)
        success = post_photo_to_facebook(img_path, news)
    else:
        video_path = create_reel_video(news)
        success = post_reel_to_facebook(video_path, news)
        
    if success:
        save_posted_news(news['link'])
        state["last_post_time"] = int(now)
        state["last_post_type"] = next_type
        save_bot_state(state)
        print(f"🎉 सक्सेस! {next_type.upper()} सफलतापूर्वक पोस्ट हो गया। स्टेट सेव हो गई।")
    else:
        print("❌ पोस्ट फेल हो गई।")

if __name__ == "__main__":
    main()
