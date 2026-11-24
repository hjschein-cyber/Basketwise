#!/usr/bin/env python3
"""Conservative weekly snapshot of public product cards at thefarmer.co.il.
If scraping becomes unreliable, keep last good file rather than invent prices.
"""
import asyncio
import datetime as dt
import hashlib
import json
import re
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parent
SITE = "https://thefarmer.co.il/"
EXTRACT = r'''() => {
  let out = [];
  for (const img of document.querySelectorAll("img[alt]")) {
    const name = (img.getAttribute("alt") || "").trim();
    if (name.length < 2 || name.length > 95 || /^(מוצא:|the farmer|logo|image|דגל)/i.test(name)) continue;
    let node = img.parentElement;
    for (let depth = 0; node && depth < 9; depth++, node = node.parentElement) {
      const text = (node.innerText || "").trim();
      if (text.length > 350 || text.length < 3) continue;
      const prices = [...text.matchAll(/₪\s*(\d+(?:[.,]\d{1,2})?)/g)];
      if (prices.length !== 1) continue;
      const pics = [...node.querySelectorAll("img[alt]")].filter(x => !/^(מוצא:|דגל)/.test(x.alt));
      if (pics.length > 2) continue;
      const controls = [...node.querySelectorAll("button")].map(x => (x.textContent || "").trim());
      if (!controls.some(x => ["+", "＋", "−", "-"].includes(x)) && depth > 6) continue;
      out.push({name, text, price: parseFloat(prices[0][1].replace(",", "."))});
      break;
    }
  }
  return out;
}'''

def sizing(text):
    t = text.replace("״", '"').replace("׳", "'")
    pattern = r'(כ\s*)?(\d+(?:[.,]\d+)?)\s*[-–]\s*(\d+(?:[.,]\d+)?)\s*(?:ק["\x27]?ג|קילו|kg)\b'
    m = re.search(pattern, t, re.I)
    if m:
        a,b = float(m[2].replace(",",".")), float(m[3].replace(",","."))
        return ((a+b)/2, "kg", f"{a:g}–{b:g} ק״ג", True)
    m = re.search(r'(כ\s*)?(\d+(?:[.,]\d+)?)\s*(?:ק["\x27]?ג|קילו|kg)\b', t, re.I)
    if m:
        return (float(m[2].replace(",",".")), "kg", f"{'כ' if m[1] else ''}{m[2]} ק״ג", bool(m[1]))
    m = re.search(r'(כ\s*)?(\d+(?:[.,]\d+)?)\s*(?:גר["\x27]?|גרם|g|gram)\b', t, re.I)
    if m:
        return (float(m[2].replace(",","."))/1000, "kg", m.group(0), bool(m[1]))
    m = re.search(r'(\d+)\s*יחידות',t)
    if m:
        return (float(m[1]), "each", m.group(0), False)
    if re.search(r'ליחידה|/יחידה', t):
        return (1, "each", "ליחידה", False)
    if re.search(r'למארז|לאריזה',t):
        return (1, "pack", "למארז", False)
    return (None, "unknown", "", False)

def category(name):
    if any(s in name for s in ["חסה","כוסברה","שמיר","פטרוז","נענע","סלרי","רוקט","תרד"]):
        return "ירק עלים"
    if any(s in name for s in ["אגוז","שקד","קשיו","פיסטוק","פקאן"]):
        return "פיצוחים"
    if any(s in name for s in ["אבוקדו","תפוח","אבטיח","מלון","בננה","תפוז","לימון","אננס","מנגו","אפרסק","אוכמ","רימון","ענב","קיווי","תמר"]):
        return "פירות"
    return "ירקות"

async def collect():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = await browser.new_page(locale="he-IL", viewport={"width":1420,"height":1000})
        await page.goto(SITE,wait_until="domcontentloaded",timeout=45000)
        try:
            await page.wait_for_load_state("networkidle", timeout=25000)
        except Exception:
            pass
        await page.wait_for_timeout(2000)
        for _ in range(8):
            await page.mouse.wheel(0,1250)
            await page.wait_for_timeout(350)
        raw = await page.evaluate(EXTRACT)
        await browser.close()
        return raw

def main():
    raw = asyncio.run(collect())
    products, seen = [], set()
    for item in raw:
        name = item.get("name","").strip()
        price = item.get("price")
        if not name or name in seen or not isinstance(price,(float,int)) or not 0 < price < 1500:
            continue
        info = item.get("text","").replace(name,"",1).split("₪",1)[0]
        qty,unit,description,approx = sizing(info)
        products.append({"id":"f_"+hashlib.sha1(name.encode("utf-8")).hexdigest()[:12],
                         "name":name,"category":category(name),"price":price,
                         "sizeQty":qty,"unit":unit,"sizeText":description,
                         "approx":approx,"url":SITE})
        seen.add(name)
    if len(products)<25:
        raise RuntimeError(f"Only {len(products)} products found; retain previous price file.")
    existing = ROOT/"farmer_prices.json"
    if existing.exists():
        old = json.loads(existing.read_text(encoding="utf-8")).get("products",[])
        if len(old)>=30 and len(products)<len(old)*0.65:
            raise RuntimeError("Extracted catalog unexpectedly shrank; retain previous prices.")
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    data = {"source":SITE,"capturedAt":now,"mode":"live_site",
            "note":"Public website prices; package weights may be approximate.","products":products}
    history_path=ROOT/"farmer_history.json"
    history=json.loads(history_path.read_text(encoding="utf-8")) if history_path.exists() else {"snapshots":[]}
    history["snapshots"]=(history.get("snapshots",[])+[{"capturedAt":now,"products":products}])[-52:]
    history_path.write_text(json.dumps(history,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    existing.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Saved {len(products)} Farmer products at {now}")

if __name__=="__main__":
    main()
