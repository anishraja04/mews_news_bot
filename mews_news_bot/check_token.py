import requests

TOKEN = "EAATquicTHUMBSvmN6AXw302uxfAj80oWNhCEaj7Ku2Tr2dcE3qR9fVhgLZCErUr9sZAZBgwVM374WEJMOfTd5ytFXxnWYjDHtPZArDHfC6ShZCeQmjleTe5SGLANevTnP18YS2UWTPWadNe9I7JkA9FTIEGWonzx1Mz5ZAZBZCsfRL2jc6LFjy4vZA9xDsX0lS8xTDBfuh0C4wUctOJyaTBTe3ENQjdUsaljDN24yS3zlfCxZCfLo15BxKl80lCOK4CdUyvrGKNsLZCVZCw4dVOFl7q0NPKM"

def check():
    url = f"https://graph.facebook.com/debug_token?input_token={TOKEN}&access_token={TOKEN}"
    r = requests.get(url).json()
    data = r.get("data", {})
    
    print("Token Info:")
    print("Type:", data.get("type"))
    print("App ID:", data.get("app_id"))
    print("Profile ID:", data.get("profile_id"))
    print("Is Valid:", data.get("is_valid"))
    
    # Verify if it's a page token
    if data.get("profile_id") == "1330940560103897":
        print("\n✅ YES! This is a PAGE TOKEN for Mews News.")
    else:
        print(f"\n❌ NO! This is NOT the Page Token for Mews News. Profile ID is {data.get('profile_id')}.")

check()
