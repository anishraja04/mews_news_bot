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

# राजनीति (Politics) और देश की बड़ी खबरों पर मुख्य फोकस
POLITICAL_FEEDS = [
    "http://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms",  # India / National Politics (राजनीति)
    "http://timesofindia.indiatimes.com/rssfeedstopstories.cms",    # Top Headlines (प्रमुख राजनीतिक व राष्ट्रीय खबरें)
    "http://timesofindia.indiatimes.com/rssfeeds/-2128839596.cms",  # Delhi (संसद, सरकार, चुनाव और राजनीति)
    "https://feeds.feedburner.com/ndtvnews-india-news"              # NDTV India Politics
]

SECONDARY_FEEDS = [
    "https://timesofindia.indiatimes.com/rssfeeds/54829575.cms",    # खेल (Cricket)
    "https://timesofindia.indiatimes.com/rssfeeds/3908999.cms"       # ट्रेंडिंग (Viral)
]

# राजनीतिक कीवर्ड्स जिनके आधार पर स्कोरिंग होगी (High Priority)
POLITICAL_KEYWORDS = [
    'modi', 'bjp', 'congress', 'rahul', 'gandhi', 'election', 'minister', 'govt', 'court',
    'supreme court', 'cji', 'mp', 'mla', 'cm', 'yadav', 'kejriwal', 'aap', 'parliament',
    'assembly', 'lok sabha', 'rajya sabha', 'nda', 'india bloc', 'police', 'bill', 'party',
    'leader', 'vote', 'owaisi', 'chief minister', 'prime minister', 'cabinet', 'governor',
    'rajya', 'pradhan mantri', 'delhi', 'center', 'centre', 'bengal', 'up', 'bihar',
    'akhilesh', 'mamata', 'shah', 'amit shah', 'dussehra', 'rally', 'protest', 'bsp', 'sp'
]

VIDEO_INTERVAL_SECONDS = 900   # 15 मिनट (15 * 60)
IMAGE_INTERVAL_SECONDS = 1800  # 30 मिनट (30 * 60)

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
    return {"last_video_time": 0, "last_image_time": 0}

def save_bot_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

def clean_html(raw_html):
    soup = BeautifulSoup(raw_html, "html.parser")
    return soup.get_text().strip()

def translate_to_hindi(text):
    if not text:
        return ""
    # 1. Google Translate direct RPC (Super fast & reliable)
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
            
            # 1. Real HD Photo from og:image
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
        print(f"⚠️ Article extract notice: {e}")
        
    return body, img_url

def score_political_entry(entry):
    """राजनीतिक कीवर्ड्स के आधार पर प्राथमिकता स्कोर तय करना"""
    title_lower = entry.title.lower()
    desc_lower = getattr(entry, 'description', '').lower()
    score = 0
    for kw in POLITICAL_KEYWORDS:
        if kw in title_lower:
            score += 3
        if kw in desc_lower:
            score += 1
    return score

def get_ranked_news_candidates(already_selected_links=None):
    """राजनीतिक खबरों को प्राथमिकता देकर क्रमबद्ध लिस्ट तैयार करना"""
    posted = load_posted_news()
    if already_selected_links:
        posted.update(already_selected_links)
        
    candidates = []
    
    # 1. पहले राजनीतिक फ़ीड्स से खबरें एकत्र करना
    for rss_url in POLITICAL_FEEDS:
        try:
            feed = feedparser.parse(rss_url)
            for entry in feed.entries:
                if entry.link not in posted:
                    score = score_political_entry(entry) + 5 # राजनीतिक फ़ीड्स को +5 बोनस
                    candidates.append((score, entry))
        except Exception:
            pass
            
    # 2. सेकंडरी फ़ीड्स से खबरें (बैकअप के लिए)
    for rss_url in SECONDARY_FEEDS:
        try:
            feed = feedparser.parse(rss_url)
            for entry in feed.entries:
                if entry.link not in posted:
                    score = score_political_entry(entry)
                    candidates.append((score, entry))
        except Exception:
            pass
            
    # स्कोर के आधार पर घटते क्रम में सॉर्ट करना (सबसे बड़ी राजनीतिक खबर सबसे ऊपर)
    candidates.sort(key=lambda x: x[0], reverse=True)
    return [entry for score, entry in candidates]

def is_valid_real_image(img_url):
    """जांचना कि फोटो असली है या सिर्फ TOI का लोगो / डिफ़ॉल्ट प्लेसहोल्डर"""
    if not img_url or not isinstance(img_url, str):
        return False
    
    img_url_lower = img_url.lower()
    
    # TOI Generic Red Logo ID (msid-47529300) और अन्य प्लेसहोल्डर्स
    BAD_PATTERNS = [
        '47529300',      # TOI Generic Red Logo
        'default',
        'placeholder',
        'logo',
        'no-image',
        'no_image',
        'blank',
        'generic',
        'unsplash.com'
    ]
    
    for bad in BAD_PATTERNS:
        if bad in img_url_lower:
            return False
            
    if not (img_url.startswith('http://') or img_url.startswith('https://')):
        return False
        
    return True

def prepare_news_item(entry):
    """न्यूज़ को प्रोसेस करके हिंदी और डिटेल्स तैयार करना (सिर्फ असली फोटो वाली खबरें)"""
    # 1. पहले असली HD फोटो और पूरी खबर निकालें
    full_eng_text, real_photo = extract_article_details(entry.link)
    
    img_url = real_photo
    if not img_url and getattr(entry, 'enclosures', None) and len(entry.enclosures) > 0:
        img_url = entry.enclosures[0].get('href', '')
        
    # अगर असली फोटो नहीं है (या TOI का लोगो है) तो इसे पोस्ट नहीं करना है
    if not is_valid_real_image(img_url):
        print(f"⚠️ असली फोटो अनुपलब्ध (TOI लोगो या खाली): '{entry.title[:45]}...' -> SKIP")
        return None
        
    eng_title = entry.title
    eng_summary = clean_html(entry.description)
    
    print(f"🇬🇧 English Headline: {eng_title}")
    print("🔄 इसे शानदार हिंदी में ट्रांसलेट कर रहा हूँ...")
    
    hi_title = translate_to_hindi(eng_title)
    hi_summary = translate_to_hindi(eng_summary)
    
    if full_eng_text:
        print("📖 पूरी खबर (Full Article) मिल गई! हिंदी में ट्रांसलेट कर रहा हूँ...")
        hi_full_story = translate_long_article(full_eng_text)
    else:
        hi_full_story = hi_summary
        
    print(f"📸 असली रियल फोटो मिली: {img_url[:65]}...")
    print(f"🇮🇳 Hindi Headline: {hi_title}")
    
    return {
        "title": hi_title,
        "summary": hi_summary,
        "full_story": hi_full_story,
        "link": entry.link,
        "img_url": img_url
    }

def create_image_post(news):
    print("🎨 [Photo Post] 800x1000 इन्फोग्राफिक इमेज बना रहा हूँ...")
    html_file = os.path.join(os.path.dirname(__file__), "template.html")
    img_file = os.path.join(os.path.dirname(__file__), "latest_news.png")
    
    with open(html_file, "r", encoding="utf-8") as f:
        html_content = f.read()
    
    html_content = html_content.replace("यहाँ न्यूज़ की बड़ी हेडलाइन आएगी", news['title'])
    
    photo_url = news.get('img_url') or "https://images.unsplash.com/photo-1585829365295-ab7cd400c167?w=1200"
    html_content = html_content.replace("यहाँ_इमेज_आएगी", photo_url)
        
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 800, "height": 1000})
        page.set_content(html_content)
        page.screenshot(path=img_file)
        browser.close()
        
    print(f"✅ इमेज तैयार है: {img_file}")
    return img_file

def build_anchor_script(news):
    """100% सिर्फ खबर पर फोकस - नो एक्स्ट्रा ग्रीटिंग्स या फिलर्स"""
    title = news['title'].strip()
    full_story = news.get('full_story', news.get('summary', '')).strip()
    
    clean_sentences = [
        s.strip() for s in full_story.replace('\n', ' ').split('।') 
        if len(s.strip()) > 15
    ]
    
    context = ""
    if clean_sentences:
        context = "। ".join(clean_sentences[:2]) + "।"
    else:
        context = news.get('summary', '')
        
    # 'म्यूज़ न्यूज़' (Miyuz Niyuz) सही उच्चारण और सीधा सिर्फ खबर
    script = f"म्यूज़ न्यूज़ पर बड़ी खबर। {title}। {context}"
    return script

def generate_google_tts(text, audio_path, speed=1.35):
    """Google Translate TTS बैकअप इंजन (क्लाउड/GitHub Actions 403 ब्लॉक से सुरक्षित)"""
    import urllib.parse
    
    delimiters = ['।', '.', '!', '?', ',', ';', '\n']
    temp_text = text
    for d in delimiters:
        temp_text = temp_text.replace(d, '|' + d + '|')
        
    raw_pieces = [p.strip() for p in temp_text.split('|') if p.strip()]
    chunks = []
    current = ""
    for piece in raw_pieces:
        if len(current) + len(piece) + 1 <= 80:
            current = (current + " " + piece).strip()
        else:
            if current:
                chunks.append(current)
            if len(piece) > 80:
                words = piece.split()
                w_curr = ""
                for w in words:
                    if len(w_curr) + len(w) + 1 <= 80:
                        w_curr = (w_curr + " " + w).strip()
                    else:
                        if w_curr:
                            chunks.append(w_curr)
                        w_curr = w
                if w_curr:
                    chunks.append(w_curr)
                current = ""
            else:
                current = piece
    if current:
        chunks.append(current)
        
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    combined_audio = bytearray()
    for chunk in chunks:
        if not chunk.strip():
            continue
        params = {
            'ie': 'UTF-8',
            'q': chunk,
            'tl': 'hi',
            'client': 'tw-ob'
        }
        url = f"https://translate.google.com/translate_tts?{urllib.parse.urlencode(params)}"
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200 and len(resp.content) > 100:
                combined_audio.extend(resp.content)
        except Exception as e:
            print(f"⚠️ Google TTS chunk चेतावनी: {e}")
            
    if not combined_audio:
        raise RuntimeError("Google TTS से कोई ऑडियो प्राप्त नहीं हुआ")
        
    temp_raw = audio_path + ".raw.mp3"
    with open(temp_raw, "wb") as f:
        f.write(combined_audio)
        
    cmd = [
        'ffmpeg', '-y',
        '-i', temp_raw,
        '-filter:a', f'atempo={speed}',
        '-vn',
        audio_path
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.path.exists(temp_raw):
        try:
            os.remove(temp_raw)
        except Exception:
            pass
    return True

def generate_voiceover(text, audio_path):
    """Dual-Engine TTS: पहले Edge-TTS, अगर 403 ब्लॉक या नेटवर्क एरर आए तो तुरंत Google TTS बैकअप"""
    # 1. Edge-TTS आज़माएँ (तेज और रियलिस्टिक Madhur Neural)
    try:
        import edge_tts
        async def _speak():
            communicate = edge_tts.Communicate(text, "hi-IN-MadhurNeural", rate="+45%")
            await asyncio.wait_for(communicate.save(audio_path), timeout=25.0)
            
        asyncio.run(_speak())
        if os.path.exists(audio_path) and os.path.getsize(audio_path) > 1000:
            print("✅ Edge-TTS वॉइसओवर सफलतापूर्वक तैयार हुआ!")
            return True
    except Exception as e:
        print(f"⚠️ Edge-TTS में एरर (संभवतः GitHub Actions/Azure IP 403 ब्लॉक): {e}")
        print("🔄 बैकअप Google TTS इंजन पर स्विच कर रहा हूँ...")
        
    # 2. Google TTS बैकअप आज़माएँ
    try:
        generate_google_tts(text, audio_path, speed=1.35)
        if os.path.exists(audio_path) and os.path.getsize(audio_path) > 1000:
            print("✅ Google TTS बैकअप वॉइसओवर सफलतापूर्वक तैयार हुआ!")
            return True
    except Exception as e2:
        print(f"❌ Google TTS बैकअप भी विफल रहा: {e2}")
        
    return False

def get_audio_duration(audio_path):
    try:
        cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'json', audio_path]
        r = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(json.loads(r.stdout)['format']['duration'])
    except Exception:
        return 12.0

def create_reel_video(news):
    print("🎬 [Reel Post] 9:16 वर्टिकल रील, रियल फोटो मोशन और 1.5x AI वॉइसओवर बना रहा हूँ...")
    try:
        html_file = os.path.join(os.path.dirname(__file__), "template_reel.html")
        frame_img_file = os.path.join(os.path.dirname(__file__), "reel_frame.png")
        audio_file = os.path.join(os.path.dirname(__file__), "reel_voice.mp3")
        video_file = os.path.join(os.path.dirname(__file__), "latest_reel.mp4")
        
        with open(html_file, "r", encoding="utf-8") as f:
            html_content = f.read()
            
        html_content = html_content.replace("यहाँ न्यूज़ की बड़ी हेडलाइन आएगी", news['title'])
        
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
        print(f"🎙️ AI न्यूज़ एंकर वॉइसओवर (1.5x स्पीड): '{voice_script[:75]}...'")
        ok = generate_voiceover(voice_script, audio_file)
        if not ok or not os.path.exists(audio_file) or os.path.getsize(audio_file) < 500:
            print("⚠️ वॉइसओवर फ़ाइल तैयार नहीं हो सकी!")
            return None
        
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
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0 and os.path.exists(video_file) and os.path.getsize(video_file) > 1000:
            print(f"✅ रियल रील वीडियो तैयार है: {video_file} ({os.path.getsize(video_file)} bytes)")
            return video_file
        else:
            print(f"❌ FFmpeg रेंडर विफल रहा: {res.stderr[-300:] if res.stderr else 'अज्ञात एरर'}")
            return None
    except Exception as e:
        print(f"❌ create_reel_video में एरर आया: {e}")
        return None

def build_full_caption(news):
    """कैप्शन में पूरी खबर विस्तार से"""
    return f"""🚨 【बड़ी खबर】
{news['title']}

📖 【पूरी खबर विस्तार से】
{news['full_story']}

📌 ताज़ा और निष्पक्ष खबरों के लिए Mews News को फॉलो करें!
#MewsNews #HindiNews #BreakingNews #Trending #Politics #PoliticalNews #India"""

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
    force_all = "--force" in sys.argv or os.environ.get("FORCE_RUN") == "true"
    force_video = "--force-video" in sys.argv
    force_image = "--force-image" in sys.argv
    
    state = load_bot_state()
    now = time.time()
    last_video_time = state.get("last_video_time", 0)
    last_image_time = state.get("last_image_time", 0)
    
    elapsed_video = now - last_video_time
    elapsed_image = now - last_image_time
    
    # टाइमर चेक: वीडियो हर 15 मिनट, इमेज हर 30 मिनट
    should_post_video = force_all or force_video or (elapsed_video >= VIDEO_INTERVAL_SECONDS)
    should_post_image = force_all or force_image or (elapsed_image >= IMAGE_INTERVAL_SECONDS)
    
    print(f"⏱️ स्थिति: वीडियो के बाद {int(elapsed_video/60)}m बीते (लक्ष्य: 15m) -> {'चलना चाहिए' if should_post_video else 'इंतज़ार'}")
    print(f"⏱️ स्थिति: फोटो के बाद {int(elapsed_image/60)}m बीते (लक्ष्य: 30m) -> {'चलना चाहिए' if should_post_image else 'इंतज़ार'}")
    
    if not should_post_video and not should_post_image:
        rem_v = int((VIDEO_INTERVAL_SECONDS - elapsed_video) / 60)
        rem_i = int((IMAGE_INTERVAL_SECONDS - elapsed_image) / 60)
        print(f"⏳ अभी दोनों का समय नहीं हुआ है (अगली रील {rem_v}m बाद, अगला फोटो {rem_i}m बाद)।")
        print("💤 बोट अभी विश्राम कर रहा है।")
        return
        
    candidates = get_ranked_news_candidates()
    if not candidates:
        print("🤷‍♂️ कोई नई न्यूज़ नहीं मिली।")
        return
        
    used_links = set()
    
    # 1. 🎬 अगर 15 मिनट हो गए हैं -> Video (Reel) पोस्ट करें
    if should_post_video:
        print("\n===============================")
        print("🎬 15 MIN REEL POST TRIGGERED")
        print("===============================")
        news_item = None
        for cand in candidates:
            if cand.link not in used_links:
                item = prepare_news_item(cand)
                if item:
                    news_item = item
                    used_links.add(cand.link)
                    break
                    
        if news_item:
            try:
                video_path = create_reel_video(news_item)
                if video_path and post_reel_to_facebook(video_path, news_item):
                    save_posted_news(news_item['link'])
                    state["last_video_time"] = int(now)
                    save_bot_state(state)
                    print("🎉 REEL सफलतापूर्वक पोस्ट हो गई!")
                elif not video_path:
                    print("⚠️ रील वीडियो तैयार नहीं हो सका, अगली बार पुनः प्रयास करेंगे।")
            except Exception as e:
                print(f"❌ रील पोस्ट प्रोसेस में त्रुटि: {e}")
        else:
            print("🤷‍♂️ रील के लिए कोई वैध असली-फोटो वाली खबर नहीं मिली।")
            
    # 2. 🎨 अगर 30 मिनट हो गए हैं -> Image (Photo Post) पोस्ट करें
    if should_post_image:
        print("\n===============================")
        print("🎨 30 MIN PHOTO POST TRIGGERED")
        print("===============================")
        
        if should_post_video and news_item:
            time.sleep(5)  # 5 सेकंड का अंतर
            
        news_item = None
        for cand in candidates:
            if cand.link not in used_links:
                item = prepare_news_item(cand)
                if item:
                    news_item = item
                    used_links.add(cand.link)
                    break
                    
        if news_item:
            try:
                img_path = create_image_post(news_item)
                if post_photo_to_facebook(img_path, news_item):
                    save_posted_news(news_item['link'])
                    state["last_image_time"] = int(now)
                    save_bot_state(state)
                    print("🎉 PHOTO पोस्ट सफलतापूर्वक हो गई!")
            except Exception as e:
                print(f"❌ फोटो पोस्ट प्रोसेस में त्रुटि: {e}")
        else:
            print("🤷‍♂️ फोटो पोस्ट के लिए कोई वैध असली-फोटो वाली खबर नहीं मिली।")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"⚠️ मुख्य प्रोग्राम में अप्रत्याशित अपवाद: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(0)

