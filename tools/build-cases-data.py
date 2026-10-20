"""Builds public/cases/data.js from open CS2 data.

Items + images: github.com/ByMykel/CSGO-API   (skins.json crates.json keychains.json stickers.json)
Prices:         github.com/ByMykel/counter-strike-price-tracker  static/latest.json -> prices.json (Steam market, USD cents)

Usage: python3 tools/build-cases-data.py <dir with the five json files>
Prices are converted to rubles at USD_RUB. Items above the Steam market cap and Doppler
phases get hand-set estimates (see OVERRIDE_USD / PHASE_MULT).
"""
import hashlib
import json
import os
import random
import sys

SRC = sys.argv[1]
OUT = os.path.join(os.path.dirname(__file__), "..", "public", "cases", "data.js")
IMG_PREFIX = "https://community.akamai.steamstatic.com/economy/image/"
USD_RUB = 82

WEAR_CODE = {"Factory New": "FN", "Minimal Wear": "MW", "Field-Tested": "FT", "Well-Worn": "WW", "Battle-Scarred": "BS"}
RARITY = {
    "rarity_common_weapon": "consumer", "rarity_uncommon_weapon": "industrial",
    "rarity_rare_weapon": "milspec", "rarity_mythical_weapon": "restricted",
    "rarity_legendary_weapon": "classified", "rarity_ancient_weapon": "covert",
    "rarity_ancient": "gold", "rarity_contraband_weapon": "contraband",
}
RARITY_BY_NAME = {"High Grade": "milspec", "Remarkable": "restricted", "Exotic": "classified",
                  "Extraordinary": "covert", "Contraband": "contraband"}
# Items the Steam market can't list (price cap) — rough third-party prices, USD, by wear
OVERRIDE_USD = {"AWP | Dragon Lore": 9000, "M4A4 | Howl": 5500, "AWP | Gungnir": 9500,
                "AK-47 | Wild Lotus": 6500, "AWP | Desert Hydra": 2600, "AK-47 | Gold Arabesque": 4200,
                "AWP | The Prince": 3500, "AWP | Medusa": 3800, "M4A1-S | Welcome to the Jungle": 1900}
PHASE_MULT = {"Ruby": 5.0, "Sapphire": 6.0, "Black Pearl": 3.0, "Emerald": 6.5, "Phase 2": 1.3, "Phase 4": 1.15}


def load(name):
    with open(os.path.join(SRC, name), encoding="utf-8") as f:
        return json.load(f)


def rng(*key):
    return random.Random(hashlib.md5("|".join(map(str, key)).encode()).hexdigest())


def short_img(url):
    return url[len(IMG_PREFIX):] if url and url.startswith(IMG_PREFIX) else (url or "")


def rub(usd):
    v = usd * USD_RUB
    return round(v, 2) if v < 100 else float(round(v))


PRICES = load("prices.json")["prices"]
items = {}


def add_skin(x):
    name = x["name"]
    wears = [w["name"] for w in x.get("wears") or []]
    priced = [(w, PRICES[f"{name} ({w})"]) for w in wears if f"{name} ({w})" in PRICES]
    if not wears and name in PRICES:
        priced = [("", PRICES[name])]
    r = rng(x["id"])
    if priced:
        wear, cents = r.choice(priced)
        usd = cents / 100
    elif name in OVERRIDE_USD:
        wear = r.choice(wears) if wears else ""
        usd = OVERRIDE_USD[name] * {"Factory New": 1.6, "Minimal Wear": 1.15}.get(wear, 1.0)
    else:
        return
    phase = x.get("phase") or ""
    usd *= PHASE_MULT.get(phase, 1.0)
    pattern = (x.get("pattern") or {}).get("name") or "Vanilla"
    items[x["id"]] = {
        "w": x["weapon"]["name"], "s": pattern + (f" ({phase})" if phase else ""), "c": x["category"]["name"],
        "r": RARITY.get(x["rarity"]["id"], "milspec"), "x": WEAR_CODE.get(wear, ""), "p": rub(usd),
        "i": short_img(x.get("image")), "col": [c["name"] for c in x.get("collections") or []],
        "cr": [c["name"] for c in x.get("crates") or []], "ph": phase, "pat": pattern,
    }


def add_misc(x, kind):
    name = x.get("market_hash_name") or x["name"]
    if name not in PRICES:
        return
    pre, _, rest = x["name"].partition(" | ")
    items[x["id"]] = {
        "w": pre or kind, "s": rest or x["name"], "c": kind,
        "r": RARITY_BY_NAME.get(x["rarity"]["name"], "milspec"), "x": "", "p": rub(PRICES[name] / 100),
        "i": short_img(x.get("image")), "col": [c["name"] for c in x.get("collections") or []], "cr": [], "ph": "", "pat": "",
    }


for x in load("skins.json"):
    if x.get("image"):
        add_skin(x)
for x in load("keychains.json"):
    if x.get("image"):
        add_misc(x, "Charm")
STICKER_COLS = {"Auto Racing Sticker Collection", "Fruits And Veggies Sticker Collection", "2025 Community Sticker Collection"}
for x in load("stickers.json"):
    if x.get("image") and STICKER_COLS & {c["name"] for c in x.get("collections") or []}:
        add_misc(x, "Sticker")

GUNS = [k for k, v in items.items() if v["c"] not in ("Charm", "Sticker")]
KNIVES = [k for k in GUNS if items[k]["c"] == "Knives"]
GLOVES = [k for k in GUNS if items[k]["c"] == "Gloves"]
CRATE_IMG = {c["name"]: short_img(c["image"]) for c in load("crates.json") if c.get("image")}
CASE_IMGS = [CRATE_IMG[n] for n in CRATE_IMG if n.endswith("Case") and "Souvenir" not in n]


def txt(k):
    v = items[k]
    return (v["s"] + " " + v["w"]).lower()


def match(kws, src=None):
    kws = [k.lower() for k in kws]
    return [k for k in (src or GUNS) if any(kw in txt(k) for kw in kws)]


def in_col(names):
    return [k for k, v in items.items() if set(v["col"]) & set(names)]


def in_crate(name):
    return [k for k, v in items.items() if name in v["cr"]]


def rarity(r):
    return [k for k in GUNS if items[k]["r"] == r]


def build(case_id, price, pool, extra_top=None):
    """Pick ~15 items spread over price bands around the case price, preferring the themed pool."""
    r = rng(case_id)
    bands = [(0.05, 0.6, 6), (0.6, 1.7, 3), (1.7, 7, 3), (7, 120, 3)]
    chosen = []
    for lo, hi, n in bands:
        def cands(src):
            return [k for k in src if lo * price <= items[k]["p"] < hi * price and k not in chosen]
        c = cands(pool)
        r.shuffle(c)
        if len(c) < n:
            g = cands((extra_top or []) if lo >= 1.7 else []) or cands(GUNS)
            r.shuffle(g)
            c += g[: n - len(c)]
        chosen += c[:n]
    if not any(items[k]["p"] >= price * 3 for k in chosen):
        top = sorted(set(pool) | set(extra_top or []), key=lambda k: -items[k]["p"])
        chosen += top[:3]
    if not any(items[k]["p"] < price for k in chosen):
        chosen += sorted(pool, key=lambda k: items[k]["p"])[:4]
    return sorted(set(chosen), key=lambda k: -items[k]["p"])


img_cycle = iter(CASE_IMGS * 4)
cases = []


def case(cid, name, price, section, pool, badge=None, kind="box", crate=None, extra_top=None):
    contents = pool if kind == "collection" else build(cid, price, pool, extra_top)
    contents = sorted(set(contents), key=lambda k: -items[k]["p"])
    img = CRATE_IMG.get(crate) if crate else None
    cases.append({"id": cid, "name": name, "price": price, "section": section, "badge": badge, "kind": kind,
                  "img": "" if kind == "collection" else (img or next(img_cycle)), "items": contents})


TOP = KNIVES + GLOVES

case("egg", "Яичный", 100, "chicken", GUNS, "limited")
case("chicken", "Куриный", 250, "chicken", GUNS, "limited")
case("catalan", "Каталонский", 500, "chicken", match(["Red", "Gold", "Yellow", "Fire"]), "limited")
case("silk", "Шелковый", 1000, "chicken", match(["Silk", "Kimono", "Wraps", "Purple", "Crimson"]), "limited")
case("golden-egg", "Золотое яйцо", 2500, "chicken", match(["Gold", "Doppler", "Fade", "Lore"]), "limited", extra_top=TOP)

case("crimson-leaf", "Багровый лист", 39, "new", match(["Red", "Crimson", "Blood", "Leaf", "Maple", "Autumn"]))
case("morpheus", "Морфей", 79, "new", match(["Dream", "Nightmare", "Neo", "Toxic", "Green", "Hypnotic"]))
case("minion", "Миньон", 99, "new", match(["Yellow", "Banana", "Bright", "Gold", "Sun"]))
case("w", "w", 150, "new", GUNS, "new")
case("rainy-evening", "Дождливый вечер", 349, "new", match(["Blue", "Rain", "Storm", "Water", "Night", "Ocean"]))
case("spider", "Паучий", 679, "new", match(["Web", "Spider", "Widow", "Venom", "Crimson"]))
case("autumn", "Шепот осени", 799, "new", match(["Autumn", "Leaf", "Forest", "Orange", "Copper", "Rust", "Bronze", "Amber"]))
case("burgundy", "Бургунди", 1199, "new", match(["Crimson", "Wine", "Ruby", "Blood", "Purple", "Velvet"]))
case("heavenly", "Небесный", 9999, "new", match(["Sky", "Angel", "Wings", "Cloud", "Blue", "Sapphire", "Halo"]), "new", extra_top=TOP)
case("oasis", "Оазис", 49900, "new", match(["Gold", "Desert", "Emerald", "Doppler", "Fade", "Lore", "Gamma"]), "new", extra_top=TOP)

case("kc-drboom", "Коллекция брелков Dr. Boom", 100, "armory", in_col(["Dr Boom Charm Collection"]), kind="collection")
case("kc-community", "Коллекция брелоков от сообщества", 170, "armory", in_col(["Missing Link Community Charm Collection"]), kind="collection")
case("kc-missinglink", "Коллекция брелков Missing Link", 120, "armory", in_col(["Missing Link Charm Collection"]), kind="collection")
case("kc-smallarms", "Коллекция брелков Малый калибр", 85, "armory", in_col(["Small Arms Charm Collection"]), kind="collection")
case("col-spytech", "Коллекция «Шпионаж и технологии»", 900, "armory", in_col(["The Spy Tech Collection"]), "fresh", kind="collection")
case("col-arabesque", "Коллекция «Арабеска»", 800, "armory", in_col(["The Arabesque Collection"]), "fresh", kind="collection")
case("col-overpass", "Коллекция Overpass 2024", 399, "armory", in_col(["The Overpass 2024 Collection"]), kind="collection")
case("col-fever", "Лихорадка", 310, "armory", in_col(["The Fever Collection"]), kind="collection")
case("st-racing", "Автомобильные гоночные наклейки", 90, "armory", in_col(["Auto Racing Sticker Collection"]), kind="collection")
case("st-fruits", "Набор стикеров \"Фрукты и овощи\"", 65, "armory", in_col(["Fruits And Veggies Sticker Collection"]), kind="collection")
case("st-community", "Коллекция наклеек от сообщества 2025", 65, "armory", in_col(["2025 Community Sticker Collection"]), kind="collection")

case("bw", "Черно-Белый", 479, "color", match(["Black", "White", "Mono", "Shadow", "Ash", "Ghost", "Graphite", "Snow", "Ink"]))
case("green", "Зеленый", 799, "color", match(["Green", "Emerald", "Jade", "Toxic", "Acid", "Venom", "Lime", "Jungle", "Gator"]))
case("yellow", "Желтый", 999, "color", match(["Yellow", "Gold", "Sun", "Amber", "Desert", "Lemon", "Sand", "Honey"]))
case("blue", "Синий", 1399, "color", match(["Blue", "Sapphire", "Ocean", "Cobalt", "Ice", "Frost", "Water", "Aqua", "Wave"]))
case("red", "Красный", 1999, "color", match(["Red", "Crimson", "Blood", "Ruby", "Fire", "Inferno", "Hellfire", "Lava"]))

case("danger-zone", "Зона боевых действий CS", 999, "limited", in_crate("Danger Zone Case"), crate="Danger Zone Case")
case("alpha", "Операция «Альфа»", 1599, "limited", in_col(["The Alpha Collection"]) + in_crate("Operation Phoenix Weapon Case"), crate="Operation Phoenix Weapon Case")
case("aurora-2", "Аврора 2", 1899, "limited", in_crate("Chroma 2 Case"), crate="Chroma 2 Case")
case("crystal-2", "Кристалл 2", 2599, "limited", in_crate("Prisma 2 Case"), crate="Prisma 2 Case")
case("aurora", "Операция «Аврора»", 2999, "limited", in_crate("Operation Hydra Case"), crate="Operation Hydra Case")

case("magnum", "Магнум", 19, "ours", match(["Desert Eagle", "R8 Revolver"]))
case("exposition", "Экспозиция", 69, "ours", in_col(["The Gallery Collection"]) + GUNS[:0], crate="Gallery Case")
case("summer-set", "Летний Набор", 199, "ours", match(["Sun", "Beach", "Tropical", "Neon", "Summer", "Surf", "Palm"]))
case("serpent", "Змей", 499, "ours", match(["Snake", "Serpent", "Viper", "Cobra", "Python", "Hydra"]))
case("zeiss", "Лаборатория ZEISS", 699, "ours", match(["AWP", "SSG 08", "SCAR-20", "G3SG1", "Scope", "Lab"]))
case("monolith", "Тактический монолит", 999, "ours", match(["AK-47", "M4A4", "M4A1-S", "Tactical", "Monolith"]), extra_top=TOP)
case("quarantine", "Операция «Карантин»", 1399, "ours", match(["Toxic", "Hazard", "Bioleak", "Plague", "Biohazard", "Contamination", "Poison"]), extra_top=TOP)
case("gta-vi", "GTA VI", 6500, "ours", match(["Neon", "Vice", "Miami", "Pink", "Rider", "Hotline"]), extra_top=TOP)
case("summer-club", "Летний Клуб", 13999, "ours", match(["Sun", "Tropical", "Fade", "Summer", "Ocean"]), extra_top=TOP)
case("premium-cache", "Премиум Cache", 17999, "ours", in_col(["The Cache Collection"]) + match(["Doppler", "Fade"], KNIVES), extra_top=TOP)
case("golden-hour", "Золотой час", 4999, "ours", match(["Gold", "Sun", "Amber", "Desert", "Lore"]), extra_top=TOP)
case("new-gloves", "Новые Перчатки", 2999, "ours", GLOVES + match(["Hand"]), extra_top=GLOVES)

case("fracture", "Раскол", 100, "special", in_crate("Fracture Case"), crate="Fracture Case")
case("esports-2013", "Про-лига 2013", 200, "special", in_crate("eSports 2013 Case"), crate="eSports 2013 Case")
case("broken-fang", "Операция «Железный коготь»", 300, "special", in_crate("Operation Broken Fang Case"), crate="Operation Broken Fang Case")
case("kilowatt", "Мегаватт", 400, "special", in_crate("Kilowatt Case"), crate="Kilowatt Case")
case("inferno", "Операция «Инферно»", 500, "special", in_col(["The 2018 Inferno Collection", "The Inferno Collection"]), extra_top=TOP)

case("cleaver", "Тесак", 29, "cheap", GUNS)
case("snakebite", "Ответный удар", 35, "cheap", in_crate("Snakebite Case"), crate="Snakebite Case")
case("gamma-2", "Сигма 2", 55, "cheap", in_crate("Gamma 2 Case"), crate="Gamma 2 Case")
case("gamma", "Сигма", 59, "cheap", in_crate("Gamma Case"), crate="Gamma Case")
case("eclipse", "Затмение", 79, "cheap", in_crate("Horizon Case"), crate="Horizon Case")

case("r-milspec", "Армейское", 39, "rarity", rarity("milspec"))
case("r-restricted", "Запрещенное", 159, "rarity", rarity("restricted"))
case("r-classified", "Засекреченное", 649, "rarity", rarity("classified"))
case("r-covert", "Тайное", 5899, "rarity", rarity("covert"))
case("r-knife", "Ножевой", 12499, "rarity", KNIVES)

case("vanilla", "Оригинальные ножи", 19999, "lux", [k for k in KNIVES if items[k]["pat"] == "Vanilla"] + KNIVES)
case("damascus", "Дамасская сталь", 24999, "lux", match(["Damascus"], KNIVES), extra_top=KNIVES)
case("ultraviolet", "Ультрафиолет", 28999, "lux", match(["Ultraviolet"], KNIVES), extra_top=KNIVES)
case("legends", "Легенды", 28999, "lux", match(["Lore", "Autotronic", "Doppler", "Fade"], KNIVES) + match(["Dragon Lore", "Howl", "Fire Serpent"]), extra_top=KNIVES)
case("crimson-web", "Кровавая Паутина", 29999, "lux", match(["Crimson Web"], KNIVES + GLOVES), extra_top=KNIVES)
case("waves", "Волны", 34999, "lux", match(["Doppler"], KNIVES), extra_top=KNIVES)
case("tiger-tooth", "Зуб Тигра", 39999, "lux", match(["Tiger Tooth"], KNIVES), extra_top=KNIVES)
case("case-hardened", "Поверхностная закалка", 40999, "lux", match(["Case Hardened"], KNIVES), extra_top=KNIVES)
case("gradient", "Градиент", 49999, "lux", match(["Fade"], KNIVES), extra_top=KNIVES)
case("lux-gloves", "Люксовые перчатки", 64999, "lux", GLOVES, extra_top=GLOVES)
case("sapphire", "Сапфировый", 119999, "lux", [k for k in KNIVES if items[k]["ph"] in ("Sapphire", "Phase 4", "Phase 3")], extra_top=KNIVES)
case("emerald", "Изумруд", 129999, "lux", [k for k in KNIVES if items[k]["ph"] in ("Emerald", "Phase 2", "Phase 1")] + match(["Gamma Doppler"], KNIVES), extra_top=KNIVES)
case("ruby", "Рубиновый", 139999, "lux", [k for k in KNIVES if items[k]["ph"] in ("Ruby", "Phase 1", "Phase 2")], extra_top=KNIVES)
case("black-pearl", "Черная Жемчужина", 159999, "lux", [k for k in KNIVES if items[k]["ph"] in ("Black Pearl", "Phase 3", "Phase 4")], extra_top=KNIVES)
case("royal", "Королевский", 299999, "lux", sorted(TOP + match(["Dragon Lore", "Howl", "Gungnir", "Wild Lotus"]), key=lambda k: -items[k]["p"])[:40], extra_top=TOP)

case("premium-1", "Премиум 1", 4999, "premium", GUNS, extra_top=TOP)
case("premium-2", "Премиум 2", 8999, "premium", GUNS, extra_top=TOP)
case("premium-3", "Премиум 3", 13999, "premium", GUNS, extra_top=TOP)
case("premium-4", "Премиум 4", 19999, "premium", GUNS, extra_top=TOP)
case("premium-5", "Премиум 5", 29999, "premium", GUNS, extra_top=TOP)

case("daily", "Ежедневный", 0, "rewards", [])
cases[-1]["items"] = sorted(rng("daily").sample([k for k in GUNS if items[k]["p"] < 150], 14), key=lambda k: -items[k]["p"])

out_items = {k: [v["w"], v["s"], v["c"], v["r"], v["x"], v["p"], v["i"]] for k, v in items.items()}
payload = {"img": IMG_PREFIX, "items": out_items, "cases": cases}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    f.write("// Generated by tools/build-cases-data.py (ByMykel/CSGO-API + Steam market prices, RUB).\n")
    f.write("window.MC_DATA=" + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n")
print("items", len(out_items), "cases", len(cases), "bytes", os.path.getsize(OUT))
for c in cases:
    ps = [items[k]["p"] for k in c["items"]]
    print(f'{c["id"]:15} {c["price"]:>7} n={len(ps):2} min={min(ps):>10} max={max(ps):>11} cheap={sum(p < c["price"] for p in ps)}')
