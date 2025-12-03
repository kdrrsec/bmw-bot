import os
from bs4 import BeautifulSoup

# ===== INSTELLINGEN =====

SEARCH_URL = "https://www.marktplaats.nl/l/auto-s/bmw/f/5-serie+benzine/611+473/#f:10882,534|offeredSince:Altijd|constructionYearFrom:2019|mileageTo:100000|engineDisplacementFrom:4050|numberOfCilindersCarsFrom:8|engineHorsepowerFrom:600|sortBy:PRICE|sortOrder:INCREASING|postcode:6951GJ"

# vul hier je (nieuwe, geldige) webhook in:
DISCORD_WEBHOOK_URL = os.getenv("https://discord.com/api/webhooks/1445871382368878774/rStk82EJyRxpGlrsVo4kZKJl3IkQmmDeVhNezkP-WbViiySjIPvtE5df8UDpjsPQWE4Y")

CHECK_INTERVAL = 300          # 5 minuten
SEEN_FILE = "seen_ads_embed.json"
MAX_KM = 100000

# =========================


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


def extract_km(text: str):
    m = re.search(r"([\d\.]+)\s*km", text.lower())
    if not m:
        return None
    try:
        return int(m.group(1).replace(".", ""))
    except ValueError:
        return None


def extract_price(text: str):
    cleaned = text.replace("\xa0", " ").replace(",", "")
    m = re.search(r"€\s*([\d\.]+)", cleaned)
    if not m:
        return None
    try:
        return int(m.group(1).replace(".", ""))
    except ValueError:
        return None


def fetch_ads():
    """Geeft dict {url: {title, km, price, image}} terug."""
    headers = {"User-Agent": "Mozilla/5.0 (BMW-Watcher/2.0)"}
    r = requests.get(SEARCH_URL, headers=headers, timeout=20)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")
    ads = {}

    for a in soup.select('a[href*="/v/"]'):
        href = a.get("href")
        if not href:
            continue

        url = "https://www.marktplaats.nl" + href if href.startswith("/") else href
        title = a.get_text(strip=True)
        if not title:
            continue

        parent = a.find_parent("li") or a.find_parent("article") or a.parent
        block_text = parent.get_text(" ", strip=True) if parent else title

        km = extract_km(block_text)
        if km is None or km > MAX_KM:
            continue

        price = extract_price(block_text)

        image_url = None
        if parent:
            img = parent.find("img")
            if img:
                image_url = img.get("src") or img.get("data-src")
                if image_url and not image_url.startswith("http"):
                    image_url = None

        ads[url] = {
            "title": title,
            "km": km,
            "price": price,
            "image": image_url,
        }

    return ads


def send_to_discord(new_ads):
    for url, ad in new_ads.items():
        km_text = f"{ad['km']:,} km".replace(",", ".")
        if ad["price"] is not None:
            price_text = f"€ {ad['price']:,}".replace(",", ".")
        else:
            price_text = "Onbekend"

        embed = {
            "title": ad["title"][:256],
            "url": url,
            "description": "Nieuwe BMW 5-serie advertentie gevonden op Marktplaats.",
            "color": 0x3498DB,  # blauw
            "fields": [
                {"name": "Kilometerstand", "value": km_text, "inline": True},
                {"name": "Prijs", "value": price_text, "inline": True},
            ],
        }

        if ad["image"]:
            embed["image"] = {"url": ad["image"]}

        payload = {
            "content": "🚗 **Nieuwe BMW advertentie!**",
            "embeds": [embed],
        }

        r = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        print("Discord response:", r.status_code, r.text)
        r.raise_for_status()


def main():
    seen = load_seen()
    print("🚀 BMW watcher (met embeds) gestart…")

    while True:
        try:
            ads = fetch_ads()
            new = {u: data for u, data in ads.items() if u not in seen}

            if new:
                print(f"🔔 {len(new)} nieuwe advertentie(s).")
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
