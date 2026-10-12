import os
import sys
import time
import random
import asyncio
from playwright.async_api import async_playwright

sys.stdout.reconfigure(encoding='utf-8')

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

REELS_PAGE_URL = "https://www.facebook.com/hindinewsmews/reels/"

async def single_viewer(browser, worker_id, watch_time=6, stagger=0.0):
    if stagger > 0:
        await asyncio.sleep(stagger)
        
    ua = random.choice(USER_AGENTS)
    vp = random.choice(VIEWPORTS)
    ctx = await browser.new_context(user_agent=ua, viewport=vp, locale="hi-IN")
    page = await ctx.new_page()
    await page.add_init_script("delete Object.getPrototypeOf(navigator).webdriver;")
    
    success = False
    try:
        await page.goto(REELS_PAGE_URL, wait_until="domcontentloaded", timeout=35000)
        await asyncio.sleep(4)
        await page.keyboard.press("Escape")
        await page.evaluate("window.scrollBy(0, 700)")
        await asyncio.sleep(2.5)
        await page.evaluate("window.scrollBy(0, 400)")
        await asyncio.sleep(2)
        await page.keyboard.press("Escape")
        
        links = await page.locator('a[href*="/reel/"]').all()
        if links:
            await links[0].click()
            await asyncio.sleep(5)
            # Ensure video plays
            await page.evaluate("""() => {
                const v = document.querySelector('video');
                if (v) { v.muted = true; if (v.paused) v.play(); }
            }""")
            await asyncio.sleep(watch_time)
            cur_time = await page.evaluate("() => { const v = document.querySelector('video'); return v ? v.currentTime : 0; }")
            print(f"   [View #{worker_id}] ✅ सफलतापूर्वक देखा गया: {cur_time:.1f}s")
            success = True
        else:
            print(f"   [View #{worker_id}] ⚠️ रील कार्ड नहीं मिला")
    except Exception as e:
        print(f"   [View #{worker_id}] ⚠️ एरर: {e}")
    finally:
        try:
            await ctx.close()
        except Exception:
            pass
    return success

async def _boost_async(total_views, batch_size=4):
    print("==================================================")
    print(f"🚀 [Auto View Booster] रील अपलोड होते ही शुरू!")
    print(f"🎯 कुल टार्गेट व्यूज: {total_views} (बैच साइज़: {batch_size})")
    print("==================================================")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--mute-audio'
            ]
        )
        
        completed = 0
        successful = 0
        
        while completed < total_views:
            current_batch = min(batch_size, total_views - completed)
            tasks = [
                single_viewer(browser, completed + i + 1, watch_time=random.randint(6, 10), stagger=i * 0.8)
                for i in range(current_batch)
            ]
            results = await asyncio.gather(*tasks)
            completed += current_batch
            successful += sum(results)
            print(f"📊 प्रगति: {completed}/{total_views} व्यूज संपन्न (सफल: {successful})")
            
            if completed < total_views:
                await asyncio.sleep(random.uniform(1.5, 3.0))
                
        await browser.close()
        print("==================================================")
        print(f"🎉 [Auto View Booster] संपन्न! कुल {successful}/{total_views} व्यूज सफलतापूर्वक जोड़े गए!")
        print("==================================================")
        return successful

def auto_boost_views(min_views=50, max_views=100, batch_size=4):
    """रील अपलोड होते ही 50 से 100 रैंडम व्यूज ऑटोमैटिक इनिशियलाइज़ करना"""
    total = random.randint(min_views, max_views)
    try:
        return asyncio.run(_boost_async(total_views=total, batch_size=batch_size))
    except Exception as e:
        print(f"⚠️ Auto View Booster में चेतावनी: {e}")
        return 0

if __name__ == "__main__":
    auto_boost_views(min_views=5, max_views=8, batch_size=3)
