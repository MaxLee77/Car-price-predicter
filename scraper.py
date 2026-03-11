"""
OLX.uz - Avtomobil ma'lumotlarini yig'uvchi (Detail Page Scraper)
Har bir elon ichiga kirib to'liq ma'lumotlarni oladi.
Anti-bot: random delay, scroll, headless Chrome
"""
import asyncio
import csv
import random
import os
import re
from playwright.async_api import async_playwright

BASE_URL = "https://www.olx.uz/oz/transport/legkovye-avtomobili/?currency=UZS"
DATA_FILE = "data/cars_data.csv"
MAX_LIST_PAGES = 20   # 20 bet × ~50 elon = ~1000 ta URL (yetarli)

FIELDNAMES = ["Brand", "Model", "Year", "Mileage_km", "Transmission",
              "Color", "FuelType", "Price_USD", "Raw_Price", "Ad_URL"]

async def sleep(min_s=1, max_s=3):
    await asyncio.sleep(random.uniform(min_s, max_s))

# ─────────────────────────────────────────────
def extract_brand_from_url(url: str) -> str:
    """URL slug dan mashina brendini chiqaradi."""
    slug = url.split("/obyavlenie/")[-1].lower() if "/obyavlenie/" in url else url.lower()
    brand_map = {
        'chevrolet': 'Chevrolet', 'chevy': 'Chevrolet',
        'cobalt': 'Chevrolet', 'spark': 'Chevrolet',
        'lacetti': 'Chevrolet', 'gentra': 'Chevrolet',
        'malibu': 'Chevrolet', 'tracker': 'Chevrolet',
        'monza': 'Chevrolet', 'captiva': 'Chevrolet',
        'daewoo': 'Daewoo', 'nexia': 'Daewoo', 'matiz': 'Daewoo',
        'damas': 'Daewoo', 'labo': 'Daewoo',
        'kia': 'Kia', 'hyundai': 'Hyundai', 'toyota': 'Toyota',
        'lada': 'Lada', 'vaz': 'Lada', 'jiguli': 'Lada',
        'byd': 'BYD', 'bmw': 'BMW', 'mercedes': 'Mercedes',
        'volkswagen': 'Volkswagen', 'nissan': 'Nissan',
        'honda': 'Honda', 'opel': 'Opel', 'audi': 'Audi',
        'lexus': 'Lexus', 'porsche': 'Porsche', 'tesla': 'Tesla',
        'chery': 'Chery', 'haval': 'Haval', 'geely': 'Geely',
        'deepal': 'Deepal', 'leapmotor': 'Leapmotor',
    }
    for key, brand in brand_map.items():
        if key in slug:
            return brand
    return 'Boshqa'

def parse_price(price_str: str) -> float:
    """Narxni USD ga o'giradi."""
    try:
        num_str = re.sub(r'[^\d]', '', str(price_str))
        if not num_str:
            return None
        price = int(num_str)
        p_low = price_str.lower()
        if 'y.e' in p_low or '$' in p_low or 'ye' in p_low or 'usd' in p_low:
            return float(price)
        elif 'so' in p_low or 'sum' in p_low:
            return round(price / 12800, 2)
        else:
            return float(price)
    except Exception:
        return None

# ─────────────────────────────────────────────
async def get_ad_urls_from_list_page(page, page_num: int) -> list[str]:
    """Ro'yxat sahifasidan barcha elon URL larini qaytaradi."""
    url = BASE_URL if page_num == 1 else f"{BASE_URL}&page={page_num}"
    try:
        await page.goto(url, timeout=60000, wait_until='domcontentloaded')
        await page.wait_for_selector('[data-cy="l-card"] a', timeout=25000)
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await sleep(1, 2)
        cards = await page.locator('[data-cy="l-card"] a').all()
        urls = []
        for card in cards:
            href = await card.get_attribute("href")
            if href and '/obyavlenie/' in href:
                full = "https://www.olx.uz" + href if not href.startswith("http") else href
                if full not in urls:
                    urls.append(full)
        return urls
    except Exception as e:
        print(f"  [Ro'yxat sahifasi xatosi - bet {page_num}]: {e}")
        return []

async def scrape_ad_detail(page, url: str) -> dict | None:
    """Bitta elon sahifasidan to'liq ma'lumot oladi."""
    try:
        await page.goto(url, timeout=45000, wait_until='domcontentloaded')
        await page.wait_for_selector('p', timeout=10000)

        # Narx
        raw_price = "Noma'lum"
        price_els = await page.locator('[data-testid="ad-price-container"] h3, .css-90xrc0 h3').all()
        if not price_els:
            price_els = await page.locator('h3').all()
        for el in price_els:
            txt = (await el.inner_text()).strip()
            if any(c.isdigit() for c in txt):
                raw_price = txt
                break

        # Parametrlar (p teglari ichida "Label: Qiymat" formatida)
        params = {}
        
        def normalize(s):
            """Har xil apostrof va bo'shliqlarni normallashtirish."""
            return (s.replace('\u2019', "'")   # curly right apostrophe → straight
                     .replace('\u2018', "'")   # curly left apostrophe → straight
                     .replace('\u02bc', "'")   # modifier letter apostrophe → straight
                     .strip().lower())
        
        p_els = await page.locator('p').all()
        for el in p_els:
            txt = normalize(await el.inner_text())
            if ':' in txt and len(txt) < 120:
                parts = txt.split(':', 1)
                key = parts[0].strip()
                val = parts[1].strip()
                params[key] = val

        # li elementlardan ham urinib ko'ramiz
        li_els = await page.locator('li').all()
        for el in li_els:
            txt = normalize(await el.inner_text())
            if ':' in txt and len(txt) < 120:
                parts = txt.split(':', 1)
                key = parts[0].strip()
                val = parts[1].strip()
                if key not in params:
                    params[key] = val

        # Standart o'zbekcha kalitlar — normalize qilingan key larda qidirish
        def get(keys):
            for k in keys:
                kn = normalize(k)
                for pk, pv in params.items():
                    if kn in normalize(pk):
                        return pv
            return "Noma'lum"

        model_val   = get(["model"])
        year_val    = get(["ishlab chiqarilgan yili", "yil", "year"])
        mileage_val = get(["bosgan yo'li", "bosgan yo\u2019li", "bosgan yoli",
                           "mileage", "probeg", "yurgan"])
        trans_val   = get(["uzatmalar qutisi", "uzatmalar", "karobka", "transmiss"])
        color_val   = get(["rang"])
        fuel_val    = get(["yoqilg'i turi", "yoqilg\u2019i", "yoqilgi", "fuel", "benzin"])

        # Yilni tozalash
        year_clean = None
        m = re.search(r'(199\d|200\d|201\d|202\d)', str(year_val))
        if m:
            year_clean = int(m.group(1))

        # Probegni tozalash (km ga)
        mileage_clean = None
        m2 = re.sub(r'[^\d]', '', str(mileage_val))
        if m2:
            mileage_clean = int(m2)

        price_usd = parse_price(raw_price)

        brand = extract_brand_from_url(url)
        # Modelni yana URL slugdan ham tekshiramiz
        if model_val == "Noma'lum":
            slug = url.split("/obyavlenie/")[-1].lower()
            model_map = ['cobalt','kobalt','spark','gentra','jentra','lacetti','lasetti',
                         'malibu','matiz','tracker','treker','monza','captiva','kaptiva',
                         'damas','damaz','nexia','neksiya','neksa','sonet','k5','seltos']
            for mm in model_map:
                if mm in slug:
                    model_val = mm.capitalize()
                    break

        return {
            "Brand": brand,
            "Model": model_val.capitalize() if model_val != "Noma'lum" else model_val,
            "Year": year_clean,
            "Mileage_km": mileage_clean,
            "Transmission": trans_val,
            "Color": color_val,
            "FuelType": fuel_val,
            "Price_USD": price_usd,
            "Raw_Price": raw_price,
            "Ad_URL": url,
        }
    except Exception as e:
        print(f"  [Detail xatosi]: {e}")
        return None

# ─────────────────────────────────────────────
async def main():
    os.makedirs("data", exist_ok=True)

    # CSV faylni tayyorlaymiz
    with open(DATA_FILE, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                       " AppleWebKit/537.36 (KHTML, like Gecko)"
                       " Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
        )
        list_page   = await context.new_page()
        detail_page = await context.new_page()

        all_urls = []
        print("=" * 60)
        print("BOSQICH 1: Elon URL larini yig'ish...")
        print("=" * 60)
        for pg in range(1, MAX_LIST_PAGES + 1):
            urls = await get_ad_urls_from_list_page(list_page, pg)
            new_urls = [u for u in urls if u not in all_urls]
            all_urls.extend(new_urls)
            print(f"  Bet {pg:>2}: {len(new_urls)} yangi URL | Jami: {len(all_urls)}")
            if pg < MAX_LIST_PAGES:
                await sleep(2, 5)

        print(f"\nJami {len(all_urls)} ta elon URL si yig'ildi.")
        print("\n" + "=" * 60)
        print("BOSQICH 2: Har bir elon ma'lumotini olish...")
        print("=" * 60)

        saved = 0
        skipped = 0
        for idx, url in enumerate(all_urls, 1):
            print(f"[{idx}/{len(all_urls)}] {url}")
            data = await scrape_ad_detail(detail_page, url)
            await sleep(0.8, 2)

            if data and data["Price_USD"] and data["Year"]:
                with open(DATA_FILE, mode="a", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
                    writer.writerow(data)
                saved += 1
                print(f"  ✓ Saqlandi | {data['Brand']} {data['Model']} {data['Year']} "
                      f"| {data['Mileage_km']} km | {data['Transmission']} "
                      f"| {data['Color']} | ${data['Price_USD']}")
            else:
                skipped += 1
                print(f"  ✗ O'tkazib yuborildi (yetarli ma'lumot yo'q)")

            # Har 50 elondan keyin 10 soniya dam olamiz (bot bo'lmaslik uchun)
            if idx % 50 == 0:
                print(f"\n  [PAUZA] {idx} elon tugadi. 10 soniya dam olinmoqda...\n")
                await asyncio.sleep(10)

        await browser.close()

    print(f"\n{'='*60}")
    print(f"TUGADI! Saqlandi: {saved} | O'tkazildi: {skipped}")
    print(f"Ma'lumotlar: {DATA_FILE}")
    print(f"{'='*60}")

if __name__ == "__main__":
    asyncio.run(main())
