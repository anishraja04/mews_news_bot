import requests

FB_PAGE_ID = "1330940560103897"
FB_TOKEN = "EAATquicTHUMBSuJxsZA6iFxkUOLQHvjd5cYAyItoSncJyO2bSpmHBs0dTF2rcSShyllQRRnbssC1AQNyxoIc5euTW3VZCNA8b63xVkL2YxPtNUK2is4pQFMuhf6gxZAsN6u5mkZBb3BrKZCZBeZB60PRnqfiinoGgVA62riIHrbGIPgnd8wuEMD8JqYsP0wjZB5klZAXb2tGAngwHLqsJ6HKu4WNIrVKGjMM43ABVuQXY"

video_url = "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4"

print("Downloading sample video...")
r = requests.get(video_url)
with open("sample_video.mp4", "wb") as f:
    f.write(r.content)
print("Downloaded!")

print("Uploading video to Facebook Page...")
url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/videos"

payload = {
    'description': '🔥 ज़बरदस्त वायरल वीडियो! #Viral #Trending #MewsNews',
    'access_token': FB_TOKEN
}

with open("sample_video.mp4", 'rb') as vid:
    files = {'source': vid}
    response = requests.post(url, data=payload, files=files)

if response.status_code == 200:
    print("✅ वीडियो सफलतापूर्वक पोस्ट हो गया!")
    print("Facebook Video ID:", response.json().get('id'))
else:
    print("❌ वीडियो पोस्ट करने में एरर आया:")
    print(response.json())
