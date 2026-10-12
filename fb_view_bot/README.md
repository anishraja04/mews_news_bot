# 🚀 Facebook Video & Reel View Booster Bot

यह बॉट आपकी Facebook Reels और Videos को प्राकृतिक रूप से देखने (Real Watch Time Retention) और Facebook एल्गोरिदम में वीडियो को इनिशियलाइज़ (Bootstrap) करने के लिए बनाया गया है।

---

## 🌟 फीचर्स:
1. **Auto-Detect Reels:** Facebook Page (`Mews News`) की सबसे ताज़ा रील्स को अपने आप ढूंढकर उस पर व्यूज भेजता है।
2. **Anti-Detection & Stealth:**
   - रैंडम User-Agents (Windows Chrome, Mac Safari, Edge, Firefox).
   - अलग-अलग स्क्रीन रेजोल्यूशन (1080p, 768p, 900p आदि).
   - हर व्यू के लिए नया आइसोलेटेड ब्राउज़र सेशन और कुकीज़।
   - प्राकृतिक माउस मूवमेंट्स और स्क्रॉलिंग।
3. **Real Playback Watch Time:** वीडियो को वास्तव में 15 से 45 सेकंड तक प्ले करके देखता है जिससे फेसबुक के एल्गोरिदम में हाई रिटेंशन सिग्नल जाता है।
4. **Binge Scroll Mode:** एक ही सेशन में एक के बाद एक कई रील्स लगातार स्क्रॉल करके देखना।

---

## 💻 कैसे चलाएं (How to Use):

### 1. डिफ़ॉल्ट ऑटो मोड (ताज़ा रील पर 5 व्यूज देना):
```bash
python fb_view_bot/view_bot.py --views 5
```

### 2. किसी विशेष रील लिंक पर व्यूज देना:
```bash
python fb_view_bot/view_bot.py --url https://www.facebook.com/reel/1400804892240093/ --views 10
```

### 3. ज्यादा वॉच टाइम के साथ व्यूज देना (उदा. 20 से 40 सेकंड):
```bash
python fb_view_bot/view_bot.py --views 8 --watch-min 20 --watch-max 40
```

### 4. Binge Scroll मोड (लगातार रील्स देखना):
```bash
python fb_view_bot/view_bot.py --binge --views 5
```
