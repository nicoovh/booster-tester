#!/usr/bin/env python3
"""Build cards.js for the Reality Fracture (FRA) booster simulator.

The script downloads card data from the Scryfall API and writes a compact
JavaScript file. The page loads that file with a <script> tag, so the page
works from a file:// URL with no server.

Usage:
    python3 fetch_cards.py

Sources:
    - Scryfall API (card names, French names, images, rarities, numbers)
    - "Collecting Reality Fracture" (magic.wizards.com) for the booster slots
    - Draftsim echoed pairs list for the pair mapping
"""
import json
import re
import sys
import time
import urllib.parse
import urllib.request

API = "https://api.scryfall.com/cards/search"
HEADERS = {
    "User-Agent": "fra-booster-simulator/1.0 (local use)",
    "Accept": "application/json",
}


def search(query):
    """Return every card that matches a Scryfall search query."""
    url = API + "?" + urllib.parse.urlencode(
        {"q": query, "unique": "prints", "order": "set"}
    )
    cards = []
    while url:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req) as resp:
            page = json.load(resp)
        cards.extend(page["data"])
        url = page.get("next_page")
        time.sleep(0.15)
    return cards


def number(card):
    return int(re.match(r"(\d+)", card["collector_number"]).group(1))


def printed_name(card):
    """French name. Double-faced cards keep the name on the first face."""
    if card.get("printed_name"):
        return card["printed_name"]
    faces = card.get("card_faces") or []
    if faces and faces[0].get("printed_name"):
        return faces[0]["printed_name"]
    return card["name"]


def image(card):
    if card.get("image_uris"):
        return card["image_uris"]["normal"]
    return card["card_faces"][0]["image_uris"]["normal"]


# Echoed pairs: (Multiverse card, Echoverse card). Source: draftsim.com.
PAIRS = [
    ("Arni, Renowned Champion", "Arni, Humble Scribe"),
    ("Danitha, Sword of Hope", "Danitha, Spear of Agony"),
    ("Edgar, Moonlit Sovereign", "Edgar, Ancient Bloodlord"),
    ("Fblthp, Knows the Way", "Fblthp, Impossibly Lost"),
    ("Gallia, the Merrymaker", "Gallia, Tragic Host"),
    ("Thalia, the Survivor", "Geist of Saint Thalia"),
    ("Ghalta the Unstoppable", "Ghalta the Immovable"),
    ("Hapatra, the Desert Frost", "Hapatra, the Desert Fang"),
    ("Jiang Yanggu, Never Alone", "Jiang Yanggu, Alone"),
    ("Kiora of Salt and Sand", "Kiora of Fire and Ashes"),
    ("Koth of the Homestead", "Koth, the Geomancer"),
    ("Loot, the Nexus", "Loot, the Anomaly"),
    ("Mabel, Valley Hero", "Mabel, Bitter Recluse"),
    ("Marwyn, the Preserver", "Marwyn, the Clearcutter"),
    ("Pia, Aether Ascetic", "Pia, Determined Rebuilder"),
    ("Proft, Consulting Detective", "Proft, Sinister Mastermind"),
    ("Massacre Girl, Most Wanted", "Rescue Girl, First Responder"),
    ("Ruric Thar, Magecrusher", "Ruric Thar, Biomagus"),
    ("Saheeli, Jewel of Avishkar", "Saheeli, Consul of Oversight"),
    ("Tetsuko Umezawa, Fugitive", "Tetsuko Umezawa, Pursuer"),
    ("Teyo, Lightshield Expert", "Teyo, Diamondblade Mage"),
    ("Tinybones, Pocket Nuisance", "Titanbones, Towering Heart"),
    ("Tomik, Orzhov Lawmage", "Tomik, Izzet Sparkmage"),
    ("Traxos, Academy Guardian", "Traxos, Scourge Eternal"),
    ("Way of the Pyromancer", "Way of the Cryomancer"),
    ("Way of the Wildspeaker", "Way of the Deathbringer"),
    ("Way of the Necromancer", "Way of the Healer"),
    ("Way of the Mentor", "Way of the Warlord"),
    ("Way of the Mind Sculptor", "Way of the Paradox"),
    ("Winter, Team Player", "Winter, Tormented Loner"),
    ("Yargle, Goliath of Otaria", "Yargle, Glutton of Urborg"),
    ("Yoshimaru, Scrappy Stray", "Yoshimaru, Beloved Companion"),
    ("Yuriko, Blade of the Mighty", "Yuriko, Hope from the Shadows"),
    ("Gideon the Oathless", "Gideon's Memorial"),
    ("Karn, Gilded Guardian", "Karn, Argent Defender"),
    ("Liliana the Faultless", "Liliana the Repentant"),
    ("Lyra, Archangel of Dawn", "Lyra, Tolarian Archangel"),
    ("Samut, Hazoret's Champion", "Samut, Tyrant of Naktamun"),
    ("Tam, the Possibility", "Jace, Reality Sculptor"),
    ("Vraska, the Cutting Glare", "Vraska, Soul of Stone"),
    ("Ajani Resolute", "Ajani Unrelenting"),
    ("Chandra, Torch of Defiance", "Chandra, Chill of Compliance"),
    ("Garruk, Veiled Butcher", "Garruk, Curse Breaker"),
]
PAIR_OF = {}
for pair_id, (a, b) in enumerate(PAIRS):
    PAIR_OF[a] = pair_id
    PAIR_OF[b] = pair_id

# Collector number ranges of the Booster Fun treatments found in Play Boosters.
RANGES = [
    (291, 320, "echo_borderless"),  # Borderless echoed pairs (10 U, 14 R, 6 M)
    (321, 333, "shattered"),        # Shattered mirror (5 R, 8 M), non-foil only
    (334, 358, "stronghold"),       # Sculptor's stronghold (18 R, 7 M)
    (359, 381, "braintwister"),     # Braintwister series (5 U, 15 R, 3 M)
    (382, 396, "tower"),            # Tower basic lands (15)
    (397, 401, "portal"),           # Portal view lands (5 R)
]


def pool_of(card):
    """Classify a main-set or Booster Fun card into a simulator pool."""
    n = number(card)
    for lo, hi, pool in RANGES:
        if lo <= n <= hi:
            return pool
    if n > 290:
        return None  # Collector Booster only (Japan showcase, serialized, ...)
    if 281 <= n <= 290:
        return "basic"
    if card["name"] in PAIR_OF:
        return "echo"
    if card["type_line"].startswith("Land") and card["rarity"] == "common" and (
        card["name"].endswith("Commons") or card["name"].endswith("Annex")
    ):
        return "dual"
    return card["rarity"]


def main():
    print("Downloading FRA (fr)...", file=sys.stderr)
    fr = {c["collector_number"]: c for c in search("set:fra lang:fr")}
    print("Downloading FRA (en)...", file=sys.stderr)
    en = search("set:fra lang:en")
    print("Downloading SPG (fr)...", file=sys.stderr)
    spg = search("set:spg lang:fr cn>=159 cn<=168")

    cards = []
    for c in en:
        pool = pool_of(c)
        if pool is None:
            continue
        f = fr.get(c["collector_number"])
        entry = {
            "n": c["collector_number"],
            "set": "fra",
            "fr": printed_name(f) if f else c["name"],
            "en": c["name"],
            "rarity": c["rarity"],
            "pool": pool,
            "img": image(f) if f else image(c),
            "lang": "fr" if f else "en",
            "foil": "foil" in c["finishes"],
            "nonfoil": "nonfoil" in c["finishes"],
        }
        if pool in ("echo", "echo_borderless"):
            entry["pair"] = PAIR_OF[c["name"]]
            entry["echoverse"] = c.get("watermark") == "echoverse"
        if c.get("watermark") == "desparked":
            entry["desparked"] = True
        cards.append(entry)

    for c in spg:
        cards.append({
            "n": c["collector_number"],
            "set": "spg",
            "fr": printed_name(c),
            "en": c["name"],
            "rarity": c["rarity"],
            "pool": "spg",
            "img": image(c),
            "lang": "fr",
            "foil": False,
            "nonfoil": True,
        })

    # Sanity checks against the published set structure.
    counts = {}
    for c in cards:
        key = (c["pool"], c["rarity"])
        counts[key] = counts.get(key, 0) + 1
    expected = {
        ("common", "common"): 71, ("uncommon", "uncommon"): 43,
        ("rare", "rare"): 50, ("mythic", "mythic"): 20,
        ("dual", "common"): 10, ("basic", "common"): 10,
        ("echo", "uncommon"): 66, ("echo", "rare"): 14, ("echo", "mythic"): 6,
        ("echo_borderless", "uncommon"): 10, ("echo_borderless", "rare"): 14,
        ("echo_borderless", "mythic"): 6,
        ("shattered", "rare"): 5, ("shattered", "mythic"): 8,
        ("stronghold", "rare"): 18, ("stronghold", "mythic"): 7,
        ("braintwister", "uncommon"): 5, ("braintwister", "rare"): 15,
        ("braintwister", "mythic"): 3,
        ("tower", "common"): 15, ("portal", "rare"): 5,
        ("spg", "mythic"): 10,
    }
    ok = True
    for key, want in expected.items():
        got = counts.get(key, 0)
        flag = "" if got == want else "   <-- MISMATCH"
        if got != want:
            ok = False
        print(f"{key[0]:16s} {key[1]:9s} {got:4d} (expected {want}){flag}", file=sys.stderr)
    unexpected = set(counts) - set(expected)
    if unexpected:
        ok = False
        print("Unexpected pools:", unexpected, file=sys.stderr)
    missing_fr = [c["n"] for c in cards if c["lang"] != "fr"]
    print("Cards without a French print (English image used):", missing_fr, file=sys.stderr)
    if not ok:
        print("WARNING: counts differ from the published structure.", file=sys.stderr)

    with open("cards.js", "w", encoding="utf-8") as out:
        out.write("// Generated by fetch_cards.py from the Scryfall API. Do not edit.\n")
        out.write("window.CARDS = ")
        json.dump(cards, out, ensure_ascii=False, separators=(",", ":"))
        out.write(";\n")
    print(f"Wrote cards.js with {len(cards)} cards.", file=sys.stderr)


if __name__ == "__main__":
    main()
