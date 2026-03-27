"""Display summary statistics."""

import json
import sys
from collections import Counter
from pathlib import Path

from utils.dates import get_status, is_valid_date

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


def register(subparsers):
    parser = subparsers.add_parser("stats", help="Show summary statistics")
    parser.set_defaults(func=run_stats)


def run_stats(args):
    artists = _load("artists.json")
    venues = _load("venues.json")
    exhibitions = _load("exhibitions.json")

    # Status breakdown
    status_counts = Counter()
    for e in exhibitions:
        start = e.get("start_date", "")
        end = e.get("end_date", "")
        if is_valid_date(start) and is_valid_date(end):
            status_counts[get_status(start, end)] += 1

    print(f"Exhibitions:  {len(exhibitions)}", file=sys.stderr)
    if status_counts:
        print(f"  current:    {status_counts.get('current', 0)}", file=sys.stderr)
        print(f"  upcoming:   {status_counts.get('upcoming', 0)}", file=sys.stderr)
        print(f"  past:       {status_counts.get('past', 0)}", file=sys.stderr)
    print(f"Artists:      {len(artists)}", file=sys.stderr)
    print(f"Venues:       {len(venues)}", file=sys.stderr)
    print(file=sys.stderr)

    # Top 5 cities
    city_counts = Counter(e.get("city", "Unknown") for e in exhibitions)
    if city_counts:
        print("Top cities by exhibition count:", file=sys.stderr)
        for city, count in city_counts.most_common(5):
            print(f"  {city}: {count}", file=sys.stderr)
        print(file=sys.stderr)

    # Date range
    dates = []
    for e in exhibitions:
        for field in ("start_date", "end_date"):
            d = e.get(field, "")
            if is_valid_date(d):
                dates.append(d)
    if dates:
        dates.sort()
        print(f"Date range:   {dates[0]} to {dates[-1]}", file=sys.stderr)

    return 0


def _load(filename):
    with open(DATA_DIR / filename) as f:
        return json.load(f)
