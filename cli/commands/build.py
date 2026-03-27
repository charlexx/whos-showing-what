"""Build static site from data."""

import json
import sys
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
SITE_DIR = Path(__file__).resolve().parent.parent.parent / "site"


def register(subparsers):
    parser = subparsers.add_parser("build", help="Build static site from data")
    parser.set_defaults(func=run_build)


def run_build(args):
    artists = _load("artists.json")
    venues = _load("venues.json")
    exhibitions = _load("exhibitions.json")

    generated = datetime.now().strftime("%Y-%m-%d %H:%M")

    site_data = {
        "exhibitions": exhibitions,
        "artists": artists,
        "venues": venues,
        "generated": generated,
    }

    out_path = SITE_DIR / "js" / "site-data.js"
    with open(out_path, "w") as f:
        f.write("// Auto-generated — do not edit\n")
        f.write("const WSW_DATA = ")
        json.dump(site_data, f, indent=2, ensure_ascii=False)
        f.write(";\n")

    print(f"Built site data: {len(exhibitions)} exhibitions, "
          f"{len(artists)} artists, {len(venues)} venues", file=sys.stderr)
    print(f"Generated: {generated}", file=sys.stderr)
    return 0


def _load(filename):
    with open(DATA_DIR / filename) as f:
        return json.load(f)
