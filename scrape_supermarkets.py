#!/usr/bin/env python3
"""Publish only verified, branch-specific regular produce prices from official price feeds.
Unmatched or ambiguous goods stay blank; no national-average substitutions.
"""
import datetime as dt
import json
import re
from pathlib import Path

import israeli_prices as ilp

ROOT=Path(__file__).resolve().parent
BRANCHES={
  "rami":{"chain":"rami-levy","id":"71","name":"רמי לוי רמת בית שמש",
          "address":"נהר הירקון 38","check":("רמת בית שמש","נהר הירקון")},
  "osher":{"chain":"osher-ad","id":"16","name":"אושר עד בית שמש - גליל",
           "address":"מורדי הגיטאות 6","check":("בית שמש","גליל","מורדי הגיטאות")},
}
# Allow only unambiguous fresh, loose produce. Generic prices never stand in for a
# named variety, packaged version or different weight unit.
ALIASES={
 "אבוקדו":(r"אבוקדו",r"מארז|מוכן|בשל|ארוז|קלוף|ממרח"),
 "גזר":(r"(^|\s)גזר(\s|$)",r"גמדי|מארז|ארוז|מיץ"),
 "בטטה":(r"בטט",r"ציפס|צ׳יפס|קפוא|מארז|ארוז"),
 "מלפפון":(r"מלפפונ",r"בייבי|מיני|חמוצ|מארז|ארוז"),
 "מלפפון בייבי":(r"מלפפונ.*(בייבי|מיני)",r"חמוצ|קפוא"),
 "חציל":(r"חציל",r"סלט|ממרח|קלוי|מוכן"),
 "סלק":(r"סלק",r"מבושל|בוואקום|ארוז|סלט"),
 "קישוא":(r"קישוא",r"ארוז|מארז|זוקיני|מוכן"),
 "בצל":(r"בצל",r"אדום|סגול|ירוק|מטוגן|שקית|ארוז|מארז"),
 "בצל אדום":(r"בצל.*(אדום|סגול)",r"שקית|ארוז|מארז"),
 "עגבניה":(r"עגבנ",r"שרי|מגי|ארוז|מיץ|מיובש|רסק"),
 "עגבניה מגי":(r"עגבנ.*מגי",r"ארוז|מארז"),
 "עגבניה שרי":(r"עגבנ.*שרי",r"צבעונ|מארז|ארוז"),
 "עגבניה שרי צבעוני":(r"עגבנ.*שרי.*צבעונ|עגבנ.*צבעונ.*שרי",r"ארוז|מארז"),
 "תפוח פינק לידי":(r"תפוח.*(פינק|ליידי|לידי)",r"מארז|ארוז|מיץ"),
 "תפוח זהוב":(r"תפוח.*(זהוב|גולדן)",r"מארז|ארוז|מיץ"),
 "תפוח גרנד":(r"תפוח.*(גרנד|סמית)",r"מארז|ארוז|מיץ"),
 "פלפל חריף":(r"פלפל.*חריף",r"ארוז|קפוא|מיובש|שאטה"),
 "פלפל":(r"פלפל",r"חריף|פלפלונ|מארז|ארוז|אבקה|צבעונ"),
 "קולורבי":(r"קולורבי",r"מארז|ארוז"),
 "שומר":(r"שומר",r"גרגרי|מארז|ארוז|מיובש"),
 "אפרסק":(r"אפרסק",r"מיובש|מארז|ארוז|שימור"),
 "תפו״א לבן":(r"תפוחי אדמה.*לבן|תפו.?א.*לבן",r"מארז|שק|ארוז|קפוא"),
}
def clean(s):
    return re.sub(r"\s+"," ",str(s or "").replace("״","").replace('"',"")).strip()

def loose_per_kg(item):
    unit=clean(getattr(item,"unit_of_measure","")).lower().replace(" ","").replace("'","")
    weighted=getattr(item,"is_weighted",None) is True
    kg=unit in ("קג","קילו","קילוגרם","kg") or "קילוגר" in unit
    try:
        count=float(getattr(item,"quantity",None) or 1)
        price=float(item.price)
    except (ValueError,TypeError,AttributeError):
        return False
    return (weighted or kg) and count==1 and price>0

def choose(name, items):
    if name not in ALIASES:
        return None
    pattern, exclude=ALIASES[name]
    candidates=[]
    for x in items:
        n=clean(getattr(x,"name",""))
        if loose_per_kg(x) and re.search(pattern,n) and not re.search(exclude,n):
            candidates.append(x)
    if not candidates:
        return None
    exact=[x for x in candidates if clean(x.name)==clean(name)]
    if len(exact)==1:
        return exact[0]
    if len(candidates)==1:
        return candidates[0]
    # Multiple indistinguishable products are only safe when prices agree.
    if len({str(x.price) for x in candidates})==1:
        return sorted(candidates,key=lambda x:len(clean(x.name)))[0]
    return None

def load_branch(sid, config, products):
    chain=config["chain"]
    target=str(config["id"]).lstrip("0")
    stores=ilp.get_stores(chain).stores
    matching=[x for x in stores if str(x.store_id).lstrip("0")==target]
    if len(matching)!=1:
        raise RuntimeError(f"{chain}: Store ID {target} is not unique ({len(matching)}).")
    store=matching[0]
    branch_info=clean(" ".join(str(getattr(store,key,"") or "") for key in ("name","address","city")))
    if not any(x in branch_info for x in config["check"]):
        raise RuntimeError(f"{chain}: Branch identity mismatch: {branch_info}")
    data=ilp.get_prices(chain,store_id=str(store.store_id))
    rows=getattr(data,"items",None) or []
    if len(rows)<200:
        raise RuntimeError(f"{chain}: PriceFull appears incomplete: {len(rows)} items")
    response_id=str(getattr(data,"store_id","") or "").lstrip("0")
    if response_id not in ("",target):
        raise RuntimeError(f"{chain}: Wrong price file returned ({response_id})")
    now=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    found=[]
    for p in products:
        if p.get("unit")!="kg":
            continue
        x=choose(p.get("name",""),rows)
        if x is None:
            continue
        found.append({"pid":p["id"],"name":p["name"],"unit":"kg",
                      "price":float(x.price),"retailerName":str(x.name),
                      "retailerCode":str(x.item_code),"date":now,
                      "source":"official PriceFull; regular shelf price"})
    if not found:
        raise RuntimeError(f"{chain}: No unambiguous produce matches; aborting update.")
    print(f"{sid}: {len(rows)} shelf records, {len(found)} conservative produce matches")
    return {"chain":chain,"branchName":str(store.name or config["name"]),
            "branchAddress":str(store.address or config["address"]),
            "storeId":str(store.store_id),"checkedAt":now,
            "totalPublishedItems":len(rows),"products":found}

def main():
    products=json.loads((ROOT/"farmer_prices.json").read_text(encoding="utf-8")).get("products",[])
    if not products:
        raise RuntimeError("Farmer reference missing")
    # Publish only after BOTH branch files pass verification.
    branches={sid:load_branch(sid,cfg,products) for sid,cfg in BRANCHES.items()}
    now=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    snap={"mode":"official_branch_files","capturedAt":now,
          "source":"https://url.publishedprices.co.il/",
          "description":"Branch-specific official regular prices, excluding promotions; conservatively matched fresh produce only.",
          "branches":branches}
    path=ROOT/"supermarket_prices.json"
    history_path=ROOT/"supermarket_history.json"
    history=json.loads(history_path.read_text(encoding="utf-8")) if history_path.exists() else {"snapshots":[]}
    history["snapshots"]=(history.get("snapshots",[])+[snap])[-26:]
    history_path.write_text(json.dumps(history,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    path.write_text(json.dumps(snap,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Published verified branch snapshot",now)

if __name__=="__main__":
    main()
