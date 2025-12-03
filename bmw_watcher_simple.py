import time, json, os, re, requests
from bs4 import BeautifulSoup

SEARCH_URL = "https://www.marktplaats.nl/l/auto-s/bmw/f/5-serie+benzine/611+473/#f:10882,534|offeredSince:Altijd|constructionYearFrom:2019|mileageTo:100000|engineDisplacementFrom:4050|numberOfCilindersCarsFrom:8|engineHorsepowerFrom:600|sortBy:PRICE|sortOrder:INCREASING|postcode:6951GJ"
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1445823284078710867/U_MZ2Y0taHQ45uWCecx-RRixS-Hnh-X8LVloCrb_DdCia4nWkiLSZ6Tqd0sM48BRbpG_"

CHECK_INTERVAL = 300
SEEN_FILE = "seen_ads_simple.json"
MAX_KM = 100000

def load_seen():
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_seen(seen):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(list(seen), f, ensure_ascii=False, indent=2)

def extract_km(text):
    m = re.search(r'([\d\.]+)\s*km', text.lower())
    return int(m.group(1).replace(".", "")) if m else None

def fetch_ads():
    headers = {"User-Agent": "Mozilla/5.0 (BMW-Watcher/1.0)"}
    r = requests.get(SEARCH_URL, headers=headers, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    ads = {}
    for a in soup.select('a[href*="/v/"]'):
        href = a.get("href")
        if not href: continue
        url = "https://www.marktplaats.nl" + href if href.startswith("/") else href
        title = a.get_text(strip=True)
        if not title: continue
        parent = a.find_parent("li") or a.find_parent("article") or a.parent
        txt = parent.get_text(" ", strip=True) if parent else title
        km = extract_km(txt)
        if km is not None and km <= MAX_KM:
            ads[url] = title
    return ads

def send_to_discord(new_ads):
    for url, title in new_ads.items():
        payload = {"content": f"🚗 Nieuwe BMW advertentie:\n{title}\n{url}"}
        r = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        print("Discord response:", r.status_code, r.text)
        r.raise_for_status()

def main():
    seen = load_seen()
    print("🚀 BMW watcher gestart…")
    while True:
        try:
            ads = fetch_ads()
            new = {u:t for u,t in ads.items() if u not in seen}
            if new:
                print(f"🔔 {len(new)} nieuw")
                send_to_discord(new)
                seen.update(new.keys())
                save_seen(seen)
            else:
                print("⏳ Geen nieuwe advertenties…")
        except Exception as e:
            print("⚠️ Fout:", e)
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
