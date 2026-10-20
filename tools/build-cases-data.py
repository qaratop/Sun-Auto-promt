"""Builds public/cases/data.js from the open CS2 item dataset (github.com/ByMykel/CSGO-API).

Usage: python3 tools/build-cases-data.py <dir with skins.json crates.json keychains.json stickers.json>
Prices are invented (deterministic per item) — the dataset has none.
"""
import hashlib
import json
import math
import os
import random
import sys

SRC = sys.argv[1]
OUT = os.path.join(os.path.dirname(__file__), "..", "public", "cases", "data.js")
IMG_PREFIX = "https://community.akamai.steamstatic.com/economy/image/"


def load(name):
    with open(os.path.join(SRC, name), encoding="utf-8") as f:
        return json.load(f)


def rng(*key):
    return random.Random(hashlib.md5("|".join(map(str, key)).encode()).hexdigest())


def short_img(url):
    return url[len(IMG_PREFIX):] if url and url.startswith(IMG_PREFIX) else (url or "")


WEAR = [("FN", "Factory New", 0.0, 0.07, 1.0), ("MW", "Minimal Wear", 0.07, 0.15, 0.78),
        ("FT", "Field-Tested", 0.15, 0.38, 0.6), ("WW", "Well-Worn", 0.38, 0.45, 0.5),
        ("BS", "Battle-Scarred", 0.45, 1.0, 0.42)]

RARITY = {
    "rarity_common_weapon": "consumer", "rarity_uncommon_weapon": "industrial",
    "rarity_rare_weapon": "milspec", "rarity_mythical_weapon": "restricted",
    "rarity_legendary_weapon": "classified", "rarity_ancient_weapon": "covert",
    "rarity_ancient": "gold", "rarity_contraband_weapon": "contraband",
    # stickers / charms
    "rarity_rare": "milspec", "rarity_mythical": "restricted", "rarity_legendary": "classified",
    "rarity_ancient_sticker": "covert", "rarity_contraband": "contraband",
}
RARITY_BY_NAME = {"High Grade": "milspec", "Remarkable": "restricted", "Exotic": "classified",
                  "Extraordinary": "covert", "Contraband": "contraband"}
BASE = {"consumer": 6, "industrial": 18, "milspec": 70, "restricted": 260, "classified": 1100,
        "covert": 4200, "gold": 16000, "contraband": 150000}
WEAPON_MULT = {"AK-47": 2.2, "AWP": 2.6, "M4A4": 1.6, "M4A1-S": 1.8, "Desert Eagle": 1.6, "USP-S": 1.5,
               "Glock-18": 1.4, "P90": 0.9, "Negev": 0.6, "Sawed-Off": 0.6, "MAG-7": 0.6}
KNIFE_MULT = {"Butterfly Knife": 2.2, "Karambit": 2.0, "M9 Bayonet": 1.6, "Skeleton Knife": 1.7,
              "Talon Knife": 1.5, "Bayonet": 1.3, "Stiletto Knife": 1.2, "Kukri Knife": 1.1,
              "Classic Knife": 1.1, "Flip Knife": 1.0, "Ursus Knife": 0.9, "Huntsman Knife": 0.8,
              "Nomad Knife": 0.9, "Paracord Knife": 0.7, "Survival Knife": 0.7, "Bowie Knife": 0.7,
              "Falchion Knife": 0.7, "Gut Knife": 0.5, "Navaja Knife": 0.45, "Shadow Daggers": 0.45}
PATTERN_MULT = {"Doppler": 1.8, "Gamma Doppler": 2.0, "Fade": 1.9, "Marble Fade": 1.6, "Tiger Tooth": 1.4,
                "Crimson Web": 1.6, "Slaughter": 1.3, "Lore": 1.5, "Autotronic": 1.3, "Case Hardened": 1.3,
                "Sapphire": 3.0, "Ruby": 3.0, "Emerald": 3.5, "Vice": 2.6, "Pandora's Box": 3.0,
                "Crimson Kimono": 2.4, "King Snake": 1.6, "Hedge Maze": 2.4, "Fade ": 2.0,
                "Safari Mesh": 0.45, "Forest DDPAT": 0.45, "Boreal Forest": 0.45, "Urban Masked": 0.5,
                "Scorched": 0.5, "Night Stripe": 0.6}
OVERRIDE = {"AWP | Dragon Lore": 250000, "AWP | Gungnir": 190000, "AWP | Medusa": 120000,
            "AK-47 | Fire Serpent": 60000, "AWP | The Prince": 90000, "M4A4 | Howl": 160000,
            "AK-47 | Wild Lotus": 75000, "AK-47 | Gold Arabesque": 70000, "M4A1-S | Welcome to the Jungle": 30000,
            "AWP | Desert Hydra": 45000, "M4A4 | Poseidon": 22000, "AWP | Asiimov": 9000,
            "AK-47 | Vulcan": 11000, "AK-47 | Redline": 1800, "M4A1-S | Printstream": 13000,
            "Desert Eagle | Blaze": 7800, "Glock-18 | Fade": 15000}


def wear_for(x, r):
    lo, hi = x.get("min_float") or 0.0, x.get("max_float") or 1.0
    allowed = [w for w in WEAR if w[3] > lo and w[2] < hi]
    return r.choice(allowed) if allowed else WEAR[2]


def round_price(p):
    if p < 100:
        return round(p, 2)
    return float(int(round(p)))


items = {}


def add_skin(x):
    r = rng(x["id"])
    rar = RARITY.get(x["rarity"]["id"], "milspec")
    weapon = x["weapon"]["name"]
    pattern = (x.get("pattern") or {}).get("name") or ""
    cat = x["category"]["name"]
    base = BASE[rar] * math.exp(r.gauss(0, 0.45))
    if cat == "Knives":
        base = 14000 * KNIFE_MULT.get(weapon, 0.8) * PATTERN_MULT.get(pattern, 0.85 if pattern else 1.15)
        base *= math.exp(r.gauss(0, 0.2))
    elif cat == "Gloves":
        base = 9000 * PATTERN_MULT.get(pattern, 1.0) * math.exp(r.gauss(0, 0.3))
    else:
        base *= WEAPON_MULT.get(weapon, 1.0)
    w = wear_for(x, r)
    name = x["name"]
    price = OVERRIDE.get(name, base * (1.0 if cat in ("Knives", "Gloves") else 1.0)) * w[4]
    items[x["id"]] = {
        "w": weapon, "s": pattern or "Vanilla", "c": cat, "r": rar, "x": w[0], "p": round_price(max(price, 1.5)),
        "i": short_img(x.get("image")), "col": [c["name"] for c in x.get("collections") or []],
    }


def add_misc(x, kind):
    r = rng(x["id"])
    rn = x["rarity"]["name"]
    rar = RARITY_BY_NAME.get(rn, RARITY.get(x["rarity"]["id"], "milspec"))
    base = {"milspec": 9, "restricted": 35, "classified": 140, "covert": 520, "contraband": 5000}[rar]
    name = x["name"]
    pre, _, rest = name.partition(" | ")
    items[x["id"]] = {
        "w": pre or kind, "s": rest or name, "c": kind, "r": rar, "x": "", "p": round_price(base * math.exp(r.gauss(0, 0.5))),
        "i": short_img(x.get("image")), "col": [c["name"] for c in x.get("collections") or []],
    }


skins = load("skins.json")
for x in skins:
    if x.get("image"):
        add_skin(x)
for x in load("keychains.json"):
    if x.get("image"):
        add_misc(x, "Charm")
stickers = [x for x in load("stickers.json")
            if any(c["name"] in ("Auto Racing Sticker Collection", "Fruits And Veggies Sticker Collection",
                                 "2025 Community Sticker Collection") for c in x.get("collections") or [])]
for x in stickers:
    if x.get("image"):
        add_misc(x, "Sticker")

GUNS = [k for k, v in items.items() if v["c"] not in ("Charm", "Sticker")]
crate_imgs = [short_img(c["image"]) for c in load("crates.json") if c.get("type") == "Case" and c.get("image")]


def match(kws):
    kws = [k.lower() for k in kws]
    return [k for k in GUNS if any(kw in (items[k]["s"] + " " + items[k]["w"]).lower() for kw in kws)]


def in_col(names):
    return [k for k, v in items.items() if set(v["col"]) & set(names)]


def build(case_id, price, pool, n_low=6, n_mid=3, n_high=3, n_top=3):
    """Pick case contents spread over price bands around the case price."""
    r = rng(case_id)
    bands = [(0.06, 0.6, n_low), (0.6, 1.7, n_mid), (1.7, 7, n_high), (7, 80, n_top)]
    chosen = []
    for lo, hi, n in bands:
        def cands(src):
            return [k for k in src if lo * price <= items[k]["p"] < hi * price and k not in chosen]
        c = cands(pool)
        if len(c) < n:
            c = c + r.sample(cands(GUNS), min(n - len(c) + 4, len(cands(GUNS))))
        r.shuffle(c)
        chosen += c[:n]
    if not any(items[k]["p"] >= price * 4 for k in chosen):
        chosen += sorted(GUNS, key=lambda k: -items[k]["p"])[r.randint(0, 6):][:2]
    return sorted(set(chosen), key=lambda k: -items[k]["p"])


ci = iter(crate_imgs * 3)
cases = []


def case(cid, name, price, section, pool, badge=None, kind="box", **kw):
    contents = pool if kind == "collection" else build(cid, price, pool, **kw)
    contents = sorted(set(contents), key=lambda k: -items[k]["p"])
    cases.append({"id": cid, "name": name, "price": price, "section": section, "badge": badge, "kind": kind,
                  "img": next(ci) if kind == "box" else "", "items": contents})


case("egg", "Яичный", 100, "chicken", GUNS, "limited")
case("chicken", "Куриный", 250, "chicken", GUNS, "limited")
case("catalan", "Каталонский", 500, "chicken", match(["Red", "Gold", "Yellow", "Fire"]), "limited")
case("silk", "Шелковый", 1000, "chicken", match(["Silk", "Kimono", "Wraps", "Purple", "Crimson"]), "limited")
case("golden-egg", "Золотое яйцо", 2500, "chicken", match(["Gold", "Doppler", "Fade", "Lore"]), "limited")

case("crimson-leaf", "Багровый лист", 39, "new", match(["Red", "Crimson", "Blood", "Leaf", "Maple", "Autumn"]))
case("morpheus", "Морфей", 79, "new", match(["Dream", "Nightmare", "Neo", "Toxic", "Green", "Hypnotic"]))
case("minion", "Миньон", 99, "new", match(["Yellow", "Banana", "Bright", "Gold", "Sun"]))
case("w", "w", 150, "new", GUNS, "new")
case("rainy-evening", "Дождливый вечер", 349, "new", match(["Blue", "Rain", "Storm", "Water", "Night", "Ocean"]))
case("spider", "Паучий", 679, "new", match(["Web", "Spider", "Widow", "Venom", "Crimson"]))
case("autumn", "Шепот осени", 799, "new", match(["Autumn", "Leaf", "Forest", "Orange", "Copper", "Rust", "Bronze", "Amber"]))
case("burgundy", "Бургунди", 1199, "new", match(["Crimson", "Wine", "Ruby", "Blood", "Purple", "Velvet"]))
case("heavenly", "Небесный", 9999, "new", match(["Sky", "Angel", "Wings", "Cloud", "Blue", "Sapphire", "Halo"]), "new")
case("oasis", "Оазис", 49900, "new", match(["Gold", "Desert", "Emerald", "Doppler", "Fade", "Lore", "Gamma"]), "new")

case("kc-drboom", "Коллекция брелков Dr. Boom", 100, "armory", in_col(["Dr Boom Charm Collection"]), kind="collection")
case("kc-community", "Коллекция брелоков от сообщества", 170, "armory", in_col(["Missing Link Community Charm Collection"]), kind="collection")
case("kc-missinglink", "Коллекция брелков Missing Link", 120, "armory", in_col(["Missing Link Charm Collection"]), kind="collection")
case("kc-smallarms", "Коллекция брелков Малый калибр", 85, "armory", in_col(["Small Arms Charm Collection"]), kind="collection")
case("col-spytech", "Коллекция «Шпионаж и технологии»", 900, "armory", in_col(["The Spy Tech Collection"]), "fresh", kind="collection")
case("col-arabesque", "Коллекция «Арабеска»", 800, "armory", in_col(["The Arabesque Collection"]), "fresh", kind="collection")
case("col-overpass", "Коллекция Overpass 2024", 399, "armory", in_col(["The Overpass 2024 Collection"]), kind="collection")
case("col-fever", "Лихорадка", 310, "armory", in_col(["The Fever Collection"]), kind="collection")
case("st-racing", "Автомобильные гоночные наклейки", 90, "armory", in_col(["Auto Racing Sticker Collection"]), kind="collection")
case("st-fruits", "Набор стикеров «Фрукты и овощи»", 65, "armory", in_col(["Fruits And Veggies Sticker Collection"]), kind="collection")
case("st-community", "Коллекция наклеек от сообщества 2025", 65, "armory", in_col(["2025 Community Sticker Collection"]), kind="collection")

case("bw", "Черно-Белый", 479, "color", match(["Black", "White", "Mono", "Shadow", "Ash", "Ghost", "Graphite", "Snow", "Ink"]))
case("green", "Зеленый", 799, "color", match(["Green", "Emerald", "Jade", "Toxic", "Acid", "Venom", "Lime", "Jungle", "Gator"]))
case("yellow", "Желтый", 999, "color", match(["Yellow", "Gold", "Sun", "Amber", "Desert", "Lemon", "Sand", "Honey"]))
case("blue", "Синий", 1399, "color", match(["Blue", "Sapphire", "Ocean", "Cobalt", "Ice", "Frost", "Water", "Aqua", "Wave"]))
case("red", "Красный", 1999, "color", match(["Red", "Crimson", "Blood", "Ruby", "Fire", "Inferno", "Hellfire", "Lava"]))

case("danger-zone", "Зона боевых действий CS", 999, "limited", in_col(["The Danger Zone Collection"]) + match(["Knife"]))
case("alpha", "Операция «Альфа»", 1599, "limited", in_col(["The Alpha Collection", "The Phoenix Collection"]))
case("aurora-2", "Аврора 2", 1899, "limited", in_col(["The Chroma 2 Collection", "The Spectrum 2 Collection"]))
case("crystal-2", "Кристалл 2", 2599, "limited", in_col(["The Prisma 2 Collection", "The Prisma Collection"]))
case("aurora", "Операция «Аврора»", 2999, "limited", in_col(["The Operation Hydra Collection", "The Chroma Collection"]))

# daily free case for the rewards page
case("daily", "Ежедневный", 0, "rewards", [k for k in GUNS if items[k]["p"] < 300])
cases[-1]["items"] = sorted(rng("daily").sample([k for k in GUNS if items[k]["p"] < 200], 14), key=lambda k: -items[k]["p"])

out_items = {}
for k, v in items.items():
    out_items[k] = [v["w"], v["s"], v["c"], v["r"], v["x"], v["p"], v["i"]]

payload = {"img": IMG_PREFIX, "items": out_items, "cases": cases}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    f.write("// Generated by tools/build-cases-data.py from github.com/ByMykel/CSGO-API. Prices are invented.\n")
    f.write("window.MC_DATA=" + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n")
print("items", len(out_items), "cases", len(cases), "bytes", os.path.getsize(OUT))
for c in cases:
    ps = [items[k]["p"] for k in c["items"]]
    print(f'{c["id"]:16} {c["price"]:>6} n={len(ps):2} min={min(ps):>9} max={max(ps):>9}')
