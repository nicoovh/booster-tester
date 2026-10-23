#!/usr/bin/env python3
"""Build ratings.js from the 17Lands public datasets (CC BY 4.0).

The script reads two gzipped CSV files from the 17Lands public S3 bucket:
    analysis_data/game_data/game_data_public.<SET>.<FORMAT>.csv.gz
    analysis_data/draft_data/draft_data_public.<SET>.<FORMAT>.csv.gz
and computes, for every card:
    gih_wr  Games-in-hand win rate (card in opening hand or drawn)
    oh_wr   Opening-hand win rate
    gp_wr   Games-played win rate (card in main deck)
    gns_wr  Win rate of games where the card was in the deck but never seen
    iwd     Improvement when drawn = gih_wr - gns_wr
    ata     Average taken at (pick position, 1 = first pick)
    alsa    Average last seen at

Each file is downloaded once and kept in the data directory. The script
downloads again only with --refresh. It never calls the 17Lands website.

Usage:
    python3 -I fetch_ratings.py [--dir data_17lands] [--set FRA]
                                [--format PremierDraft] [--refresh]

Data: https://www.17lands.com/public_datasets (CC BY 4.0).
"""
import argparse
import csv
import datetime
import email.utils
import gzip
import json
import os
import re
import sys
import urllib.request

BASE = "https://17lands-public.s3.amazonaws.com/analysis_data"
HEADERS = {"User-Agent": "fra-booster-simulator/1.0 (one-off download of public dataset)"}

csv.field_size_limit(1 << 30)


def download(url, path, refresh):
    if os.path.exists(path) and not refresh:
        print(f"Using cached {path}", file=sys.stderr)
        return
    print(f"Downloading {url}", file=sys.stderr)
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req) as resp, open(path, "wb") as out:
        while True:
            chunk = resp.read(1 << 20)
            if not chunk:
                break
            out.write(chunk)
        modified = resp.headers.get("Last-Modified")
    # Keep the dataset date as the file's modification time.
    if modified:
        ts = email.utils.parsedate_to_datetime(modified).timestamp()
        os.utime(path, (ts, ts))
    print(f"Saved {path} ({os.path.getsize(path)} bytes, dataset dated {modified})", file=sys.stderr)


def open_csv(path):
    return csv.reader(gzip.open(path, "rt", encoding="utf-8", newline=""))


def game_stats(path):
    """One pass over the game data. Returns {card: counters} and game count."""
    reader = open_csv(path)
    header = next(reader)
    col = {name: i for i, name in enumerate(header)}
    won_i = col["won"]
    cards = [h[len("deck_"):] for h in header if h.startswith("deck_")]
    deck_i = [col["deck_" + c] for c in cards]
    oh_i = [col["opening_hand_" + c] for c in cards]
    drawn_i = [col["drawn_" + c] for c in cards]
    tut_i = [col["tutored_" + c] for c in cards]
    # Counters per card: [gih_n, gih_w, oh_n, oh_w, gp_n, gp_w, gns_n, gns_w]
    stats = {c: [0] * 8 for c in cards}
    games = 0
    for row in reader:
        games += 1
        won = 1 if row[won_i] == "True" else 0
        # Only cards in the main deck can be drawn, so scan deck columns first.
        for k in range(len(cards)):
            if row[deck_i[k]] == "0":
                continue
            s = stats[cards[k]]
            s[4] += 1
            s[5] += won
            oh = row[oh_i[k]] != "0"
            drawn = row[drawn_i[k]] != "0"
            if oh:
                s[2] += 1
                s[3] += won
            if oh or drawn:
                s[0] += 1
                s[1] += won
            elif row[tut_i[k]] == "0":
                s[6] += 1
                s[7] += won
    return stats, games


def draft_stats(path):
    """One pass over the draft data. Returns {card: [ata_sum, ata_n, alsa_sum, alsa_n]}.

    Every pick shows a different pack (packs pass around the table and come
    back after 8 picks), so each row's pack columns are scanned in full. The
    pack columns are contiguous, so one row's values are joined into a string
    and scanned with a regular expression, which is much faster than a Python
    loop over 300 columns.
    """
    reader = open_csv(path)
    header = next(reader)
    col = {name: i for i, name in enumerate(header)}
    draft_i, pack_i, pickno_i, pick_i = col["draft_id"], col["pack_number"], col["pick_number"], col["pick"]
    pack_idx = [i for i, h in enumerate(header) if h.startswith("pack_card_")]
    a, b = pack_idx[0], pack_idx[-1] + 1
    if pack_idx != list(range(a, b)):
        raise SystemExit("pack_card columns are not contiguous")
    cards = [header[i][len("pack_card_"):] for i in pack_idx]
    nonzero = re.compile(r"[^0]")
    stats = {c: [0, 0, 0, 0] for c in cards}
    picks = 0
    drafts = set()
    current = None          # (draft_id, pack_number)
    last_seen = {}          # card -> last pick number at which it was in a pack

    def flush():
        for c, p in last_seen.items():
            s = stats[c]
            s[2] += p + 1
            s[3] += 1

    for row in reader:
        picks += 1
        key = (row[draft_i], row[pack_i])
        pick_number = int(row[pickno_i])
        if key != current:
            flush()
            current = key
            drafts.add(key[0])
            last_seen = {}
        values = row[a:b]
        joined = "".join(values)
        if len(joined) == b - a:
            # Every value is one character, so a match position is a column.
            for m in nonzero.finditer(joined):
                last_seen[cards[m.start()]] = pick_number
        else:
            for k, v in enumerate(values):
                if v != "0":
                    last_seen[cards[k]] = pick_number
        picked = row[pick_i]
        if picked in stats:
            s = stats[picked]
            s[0] += pick_number + 1
            s[1] += 1
    flush()
    return stats, picks, len(drafts)


def rate(w, n):
    return round(w / n, 4) if n else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="data_17lands")
    ap.add_argument("--set", default="FRA")
    ap.add_argument("--format", default="PremierDraft")
    ap.add_argument("--refresh", action="store_true", help="download the files again")
    ap.add_argument("--out", default="ratings.js")
    args = ap.parse_args()

    os.makedirs(args.dir, exist_ok=True)
    files = {}
    for kind in ("game_data", "draft_data"):
        name = f"{kind}_public.{args.set}.{args.format}.csv.gz"
        path = os.path.join(args.dir, name)
        download(f"{BASE}/{kind}/{name}", path, args.refresh)
        files[kind] = path

    print("Reading game data...", file=sys.stderr)
    gstats, games = game_stats(files["game_data"])
    print(f"  {games} games", file=sys.stderr)
    print("Reading draft data...", file=sys.stderr)
    dstats, picks, drafts = draft_stats(files["draft_data"])
    print(f"  {picks} picks in {drafts} drafts", file=sys.stderr)

    cards = {}
    for name in sorted(set(gstats) | set(dstats)):
        g = gstats.get(name, [0] * 8)
        d = dstats.get(name, [0] * 4)
        gih = rate(g[1], g[0])
        gns = rate(g[7], g[6])
        cards[name] = {
            "gih_wr": gih, "gih_n": g[0],
            "oh_wr": rate(g[3], g[2]), "oh_n": g[2],
            "gp_wr": rate(g[5], g[4]), "gp_n": g[4],
            "gns_wr": gns,
            "iwd": round(gih - gns, 4) if gih is not None and gns is not None else None,
            "ata": round(d[0] / d[1], 2) if d[1] else None, "ata_n": d[1],
            "alsa": round(d[2] / d[3], 2) if d[3] else None, "alsa_n": d[3],
        }

    # The file modification time holds the dataset date (see download()).
    file_dates = {
        kind: datetime.datetime.fromtimestamp(os.path.getmtime(p), datetime.timezone.utc).strftime("%Y-%m-%d")
        for kind, p in files.items()
    }
    out = {
        "meta": {
            "source": "17Lands public datasets",
            "source_url": "https://www.17lands.com/public_datasets",
            "license": "CC BY 4.0",
            "set": args.set, "format": args.format,
            "games": games, "drafts": drafts, "picks": picks,
            "data_dates": file_dates,
            "generated": datetime.date.today().isoformat(),
        },
        "cards": cards,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        f.write("// Generated by fetch_ratings.py from the 17Lands public datasets (CC BY 4.0).\n")
        f.write("// https://www.17lands.com/public_datasets\n")
        f.write("window.RATINGS = ")
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")
    with_gih = sum(1 for c in cards.values() if c["gih_n"] >= 500)
    print(f"Wrote {args.out}: {len(cards)} cards, {with_gih} with at least 500 games in hand.", file=sys.stderr)


if __name__ == "__main__":
    main()
