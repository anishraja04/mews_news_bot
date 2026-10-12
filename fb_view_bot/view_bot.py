import os
import sys
import time
import random
import argparse
import requests
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')

# ==========================================
# ⚙️ Configuration & Defaults
# ==========================================
DEFAULT_PAGE_REELS_URL = "https://www.facebook.com/hindinewsmews/reels/"
FB_PAGE_ID = "1330940560103897"
FB_TOKEN = "EAATquicTHUMBSrIA2GYyZBMEZAAiRWIOaMbmoNEQWuZBJ7ZBPWo7KctMX5KUCy3Iw2z9JZBUsJYwIbzH7fxFcdpSos0UOf7GV9BNdwuLFX5YzFBexNZC5xMVX5SqOChHa9ofF3uziDSZCujvtX0wifbNjjOIZCSsZCIZCrGwiFITrpnj8Lkibv2vomCpzcUXOC1PZAWAAkRsEkS"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
]

VIEWPORTS = [
    {"width": 1366, "height": 768},
    {"width": 1920, "height": 1080},
    {"width": 1440, "height": 900},
    {"width": 1536, "height": 864},
    {"width": 1280, "height": 800}
]

def get_latest_reels_from_api(limit=3):
    """फेसबुक ग्राफ एपीआई से ताज़ा रील आईडी और लिंक्स प्राप्त करना"""
    try:
        url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/videos?fields=id,permalink_url,created_time&limit={limit}&access_token={FB_TOKEN}"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json().get("data", [])
            reel_urls = []
            for item in data:
                p_url = item.get("permalink_url", "")
                if "/reel/" in p_url:
                    reel_urls.append(f"https://www.facebook.com{p_url}")
                elif item.get("id"):
                    reel_urls.append(f"https://www.facebook.com/reel/{item['id']}/")
            return reel_urls
    except Exception as e:
        print(f"⚠️ API Fetch Warning: {e}")
    return []

def dismiss_popups(page):
    """लॉगिन और कुकी पॉपअप को हटाना"""
    try:
        page.keyboard.press("Escape")
        time.sleep(1.0)
        close_btn = page.locator('[aria-label="बंद करें"], [aria-label="Close"]')
        if close_btn.count() > 0:
            close_btn.first.click()
            time.sleep(1.0)
    except Exception:
        pass

def simulate_human_actions(page, duration_sec):
    """मानव जैसा प्राकृतिक व्यवहार (माउस मूवमेंट, स्क्रॉल आदि)"""
    start = time.time()
    next_action_time = start + random.uniform(3.0, 6.0)
    
    while time.time() - start < duration_sec:
        time.sleep(1.0)
        now = time.time()
        
        # समय-समय पर माउस को थोड़ा हिलाना
        if now >= next_action_time:
            try:
                x = random.randint(200, 800)
                y = random.randint(200, 600)
                page.mouse.move(x, y)
                # कभी-कभार हल्का स्क्रॉल
                if random.random() < 0.25:
                    page.mouse.wheel(0, random.choice([-50, 50]))
            except Exception:
                pass
            next_action_time = now + random.uniform(4.0, 8.0)

def watch_single_view(browser, target_url, watch_time_sec=20, session_num=1):
    """एक नई ताज़ा विंडो/सेशन में वीडियो खोलना और देखना"""
    ua = random.choice(USER_AGENTS)
    vp = random.choice(VIEWPORTS)
    
    print(f"\n🎬 [सेशन #{session_num}] नया व्यू शुरू: {target_url[:55]}...")
    print(f"   👤 User-Agent: {ua.split()[0]} {ua.split()[1]}")
    print(f"   ⏱️ टार्गेट वॉच टाइम: {watch_time_sec} सेकंड")
    
    # बिल्कुल नया, अलग कुकी और कैश सेशन
    context = browser.new_context(
        user_agent=ua,
        viewport=vp,
        locale="hi-IN"
    )
    
    # एंटी-डिटेक्शन मास्क
    page = context.new_page()
    page.add_init_script("delete Object.getPrototypeOf(navigator).webdriver;")
    
    view_success = False
    try:
        # हमेशा पेज के रील्स टैब से शुरू करें (Facebook Splash Bypass)
        page.goto(DEFAULT_PAGE_REELS_URL, wait_until="domcontentloaded", timeout=40000)
        time.sleep(4)
        dismiss_popups(page)
        
        # स्क्रॉल करके रील्स ग्रिड को ट्रिगर करना
        print("   📜 रील्स ग्रिड लोड करने के लिए स्क्रॉल कर रहा हूँ...")
        page.evaluate("window.scrollBy(0, 700)")
        time.sleep(2)
        page.evaluate("window.scrollBy(0, 500)")
        time.sleep(2)
        dismiss_popups(page)
        
        # रील कार्ड का चयन
        reel_id = target_url.strip("/").split("/")[-1] if target_url else ""
        links = page.locator('a[href*="/reel/"]').all()
        target_link = None
        
        if reel_id:
            for l in links:
                href = l.get_attribute("href") or ""
                if reel_id in href:
                    target_link = l
                    break
                    
        if not target_link and links:
            target_link = links[0]  # सबसे ताज़ा रील
            
        if target_link:
            print(f"   🎯 रील कार्ड पर क्लिक किया (उपलब्ध रील्स: {len(links)})...")
            target_link.click()
            time.sleep(6)
            try:
                page.wait_for_selector("video", timeout=10000)
            except Exception:
                pass
        else:
            print("   ⚠️ कोई रील कार्ड नहीं मिला, डायरेक्ट लिंक आज़मा रहा हूँ...")
            page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(5)
            
        # वीडियो प्लेयर की जांच
        video_locator = page.locator("video")
        has_video = video_locator.count() > 0
        
        if has_video:
            print("   ▶️ वीडियो एलिमेंट सक्रिय! प्लेबैक की पुष्टि कर रहा हूँ...")
            # वीडियो प्ले सुनिश्चित करना
            page.evaluate("""() => {
                const v = document.querySelector('video');
                if (v) {
                    v.muted = true;
                    if (v.paused) { v.play(); }
                }
            }""")
            
            # वीडियो देखना और वॉच टाइम पूरा करना
            simulate_human_actions(page, watch_time_sec)
            
            # फाइनल प्लेबैक टाइम चेक
            playback_time = page.evaluate("""() => {
                const v = document.querySelector('video');
                return v ? v.currentTime : 0;
            }""")
            print(f"   ✅ सफलतापूर्वक देखा गया! (प्लेबैक टाइम: {playback_time:.1f}s)")
            view_success = True
        else:
            print("   ⚠️ वीडियो टैग नहीं मिला, पेज व्यू 10 सेकंड रखा...")
            simulate_human_actions(page, 10)
            view_success = True
            
    except Exception as e:
        print(f"   ❌ सेशन #{session_num} में एरर: {e}")
    finally:
        try:
            context.close()
        except Exception:
            pass
            
    return view_success

def binge_scroll_session(browser, num_reels=3, watch_per_reel=15):
    """एक ही विज़िटर द्वारा एक के बाद एक कई रील्स को स्क्रॉल करके देखना (High Retention Binge)"""
    ua = random.choice(USER_AGENTS)
    vp = random.choice(VIEWPORTS)
    
    print(f"\n🔄 [Binge Scroll] एक साथ {num_reels} रील्स लगातार देखी जा रही हैं...")
    context = browser.new_context(user_agent=ua, viewport=vp, locale="hi-IN")
    page = context.new_page()
    page.add_init_script("delete Object.getPrototypeOf(navigator).webdriver;")
    
    try:
        page.goto(DEFAULT_PAGE_REELS_URL, wait_until="domcontentloaded", timeout=35000)
        time.sleep(4)
        dismiss_popups(page)
        page.evaluate("window.scrollBy(0, 700)")
        time.sleep(3)
        dismiss_popups(page)
        
        links = page.locator('a[href*="/reel/"]').all()
        if links:
            links[0].click()
            time.sleep(3)
            
            for i in range(1, num_reels + 1):
                dismiss_popups(page)
                print(f"   📱 [रील {i}/{num_reels}] चल रही है ({watch_per_reel}s)...")
                
                # वीडियो को प्ले करना
                page.evaluate("""() => {
                    const v = document.querySelector('video');
                    if (v) { v.muted = true; if (v.paused) v.play(); }
                }""")
                
                simulate_human_actions(page, watch_per_reel)
                
                # अगली रील पर स्क्रॉल (ArrowDown या Next)
                if i < num_reels:
                    print("   ⬇️ अगली रील पर स्क्रॉल किया जा रहा है...")
                    page.keyboard.press("ArrowDown")
                    time.sleep(2)
                    
            print("   🎉 Binge Scroll सेशन सफलतापूर्वक पूरा हुआ!")
        else:
            print("   ⚠️ कोई रील लिंक नहीं मिला।")
    except Exception as e:
        print(f"   ❌ Binge Scroll में एरर: {e}")
    finally:
        context.close()

def main():
    parser = argparse.ArgumentParser(description="Facebook Video & Reel View Booster Bot")
    parser.add_argument("--url", type=str, default="", help="विशिष्ट वीडियो/रील का यूआरएल (वैकल्पिक)")
    parser.add_argument("--views", type=int, default=5, help="कुल कितने व्यूज देने हैं (डिफ़ॉल्ट: 5)")
    parser.add_argument("--watch-min", type=int, default=15, help="न्यूनतम वॉच टाइम सेकंड्स (डिफ़ॉल्ट: 15)")
    parser.add_argument("--watch-max", type=int, default=30, help="अधिकतम वॉच टाइम सेकंड्स (डिफ़ॉल्ट: 30)")
    parser.add_argument("--binge", action="store_true", help="Binge Scroll मोड चलाएं (लगातार रील्स स्क्रॉल करना)")
    parser.add_argument("--headless", type=bool, default=True, help="हेडलेस मोड (डिफ़ॉल्ट: True)")
    
    args = parser.parse_args()
    
    print("==================================================")
    print("🚀 Facebook Video / Reel View Booster Bot")
    print("==================================================")
    print(f"🎯 टार्गेट व्यूज: {args.views}")
    print(f"⏳ वॉच टाइम रेंज: {args.watch_min}s - {args.watch_max}s")
    
    # टार्गेट यूआरएल का निर्धारण
    target_url = args.url
    if not target_url:
        print("🔍 ताज़ा रील्स खोज रहा हूँ...")
        api_reels = get_latest_reels_from_api(limit=1)
        if api_reels:
            target_url = api_reels[0]
            print(f"📌 ताज़ा पोस्टेड रील मिली: {target_url}")
        else:
            target_url = DEFAULT_PAGE_REELS_URL
            print(f"📌 पेज रील्स टैब का उपयोग किया जाएगा: {target_url}")
            
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=args.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--mute-audio'
            ]
        )
        
        # अगर binge मोड चुना गया है
        if args.binge:
            binge_scroll_session(browser, num_reels=min(args.views, 5), watch_per_reel=random.randint(args.watch_min, args.watch_max))
        else:
            successful_views = 0
            for i in range(1, args.views + 1):
                watch_time = random.randint(args.watch_min, args.watch_max)
                success = watch_single_view(browser, target_url, watch_time_sec=watch_time, session_num=i)
                if success:
                    successful_views += 1
                    
                # व्यूज के बीच स्वाभाविक रैंडम पॉज़
                if i < args.views:
                    pause = random.randint(4, 9)
                    print(f"   💤 अगले सेशन से पहले {pause} सेकंड का विराम...")
                    time.sleep(pause)
                    
            print("\n==================================================")
            print(f"🎉 कार्य संपन्न! कुल {successful_views}/{args.views} व्यूज सफलतापूर्वक इनिशियलाइज़ किए गए!")
            print("==================================================")
            
        browser.close()

if __name__ == "__main__":
    main()
