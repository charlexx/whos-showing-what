"""Exhibition management commands."""

import json
import sys
from pathlib import Path

from utils.dates import get_status, is_valid_date, today_str
from utils.ids import make_id, id_exists

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DATA_FILE = DATA_DIR / "exhibitions.json"

TYPES = ["solo", "group", "fair", "biennial", "residency", "screening", "performance"]
ADMISSION = ["free", "paid", "donation", "rsvp"]
FOCUS = ["dedicated", "diaspora", "significant", "featured"]
STATUSES = ["upcoming", "current", "past"]
SOURCES = ["manual", "submission", "scrape", "api"]
REGIONS = [
    "West Africa", "East Africa", "Southern Africa", "North Africa", "Central Africa",
    "Europe", "North America", "South America", "Caribbean", "Middle East", "Asia", "Oceania",
]


def _load(filename="exhibitions.json"):
    with open(DATA_DIR / filename) as f:
        return json.load(f)


def _save(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def _prompt(label, default="", choices=None):
    """Interactive prompt with optional choices list."""
    suffix = f" [{default}]" if default else ""
    if choices:
        print(f"  Options: {', '.join(choices)}", file=sys.stderr)
    val = input(f"  {label}{suffix}: ").strip()
    return val if val else default


def _prompt_required(label, choices=None):
    """Interactive prompt that requires a non-empty value."""
    while True:
        val = _prompt(label, choices=choices)
        if val:
            return val
        print("  (required)", file=sys.stderr)


def _pick_artists():
    """Show existing artists and prompt for IDs."""
    artists = _load("artists.json")
    if artists:
        print("\n  Existing artists:", file=sys.stderr)
        for a in artists:
            print(f"    {a['id']}  {a['name']} ({a.get('origin_country', '')})", file=sys.stderr)
    ids = []
    while True:
        aid = _prompt("Artist ID (blank to finish)" if ids else "Artist ID (at least one required)")
        if not aid and ids:
            break
        if aid:
            ids.append(aid)
    return ids


def _pick_venue():
    """Show existing venues and prompt for ID."""
    venues = _load("venues.json")
    if venues:
        print("\n  Existing venues:", file=sys.stderr)
        for v in venues:
            print(f"    {v['id']}  {v['name']} — {v.get('city', '')}, {v.get('country', '')}", file=sys.stderr)
    return _prompt_required("Venue ID")


def register(subparsers):
    parser = subparsers.add_parser("exhibition", help="Manage exhibitions")
    sub = parser.add_subparsers(dest="action", required=True)

    # add
    add_p = sub.add_parser("add", help="Add an exhibition")
    add_p.add_argument("--title")
    add_p.add_argument("--artist", action="append", dest="artist_ids")
    add_p.add_argument("--venue", dest="venue_id")
    add_p.add_argument("--city")
    add_p.add_argument("--country")
    add_p.add_argument("--region", choices=REGIONS)
    add_p.add_argument("--start", dest="start_date")
    add_p.add_argument("--end", dest="end_date")
    add_p.add_argument("--type", dest="exh_type", choices=TYPES)
    add_p.add_argument("--admission", choices=ADMISSION)
    add_p.add_argument("--mediums", nargs="+")
    add_p.add_argument("--focus", choices=FOCUS)
    add_p.add_argument("--source", default="manual", choices=SOURCES)
    add_p.add_argument("--status", choices=STATUSES)
    add_p.add_argument("--description", default="")
    add_p.add_argument("--url", default="")
    add_p.add_argument("--image-url", default="")
    add_p.set_defaults(func=add_exhibition)

    # list
    list_p = sub.add_parser("list", help="List exhibitions")
    list_p.add_argument("--current", action="store_true")
    list_p.add_argument("--upcoming", action="store_true")
    list_p.add_argument("--past", action="store_true")
    list_p.add_argument("--city")
    list_p.add_argument("--country")
    list_p.add_argument("--artist")
    list_p.set_defaults(func=list_exhibitions)

    # show
    show_p = sub.add_parser("show", help="Show exhibition details")
    show_p.add_argument("id")
    show_p.set_defaults(func=show_exhibition)

    # edit
    edit_p = sub.add_parser("edit", help="Edit an exhibition")
    edit_p.add_argument("id")
    edit_p.set_defaults(func=edit_exhibition)

    # remove
    rm_p = sub.add_parser("remove", help="Remove an exhibition")
    rm_p.add_argument("id")
    rm_p.set_defaults(func=remove_exhibition)

    # refresh-status
    rs_p = sub.add_parser("refresh-status", help="Recalculate all status fields from dates")
    rs_p.set_defaults(func=refresh_status)


def add_exhibition(args):
    print("Add Exhibition", file=sys.stderr)

    title = args.title or _prompt_required("Title")
    artist_ids = args.artist_ids or _pick_artists()
    venue_id = args.venue_id or _pick_venue()
    city = args.city or _prompt_required("City")
    country = args.country or _prompt_required("Country")
    region = args.region or _prompt_required("Region", choices=REGIONS)
    start_date = args.start_date or _prompt_required("Start date (YYYY-MM-DD)")
    end_date = args.end_date or _prompt_required("End date (YYYY-MM-DD)")
    exh_type = args.exh_type or _prompt_required("Type", choices=TYPES)
    admission = args.admission or _prompt_required("Admission", choices=ADMISSION)

    if args.mediums:
        mediums = args.mediums
    else:
        raw = _prompt_required("Mediums (comma-separated)")
        mediums = [m.strip() for m in raw.split(",") if m.strip()]

    focus = args.focus or _prompt_required("Focus", choices=FOCUS)
    source = args.source or "manual"
    description = args.description or _prompt("Description")
    url = args.url or _prompt("URL")
    image_url = args.image_url or _prompt("Image URL")

    if not is_valid_date(start_date) or not is_valid_date(end_date):
        print("Error: Invalid date format. Use YYYY-MM-DD.", file=sys.stderr)
        return 1

    # Auto-calculate status from dates if not provided
    status = args.status or get_status(start_date, end_date)

    data = _load()

    venue_part = venue_id.replace("ven-", "")
    artist_part = artist_ids[0].replace("art-", "") if artist_ids else title
    year = start_date[:4]
    new_id = make_id("exh", venue_part, artist_part, year)

    if id_exists(data, new_id):
        print(f"Error: Exhibition {new_id} already exists", file=sys.stderr)
        return 1

    entry = {
        "id": new_id,
        "title": title,
        "artist_ids": artist_ids,
        "venue_id": venue_id,
        "city": city,
        "country": country,
        "region": region,
        "start_date": start_date,
        "end_date": end_date,
        "type": exh_type,
        "admission": admission,
        "mediums": mediums,
        "focus": focus,
        "source": source,
        "added_date": today_str(),
        "status": status,
    }
    if description:
        entry["description"] = description
    if url:
        entry["url"] = url
    if image_url:
        entry["image_url"] = image_url

    data.append(entry)
    _save(data)
    print(f"Added exhibition {new_id}: {title}", file=sys.stderr)
    print(json.dumps(entry, indent=2, ensure_ascii=False))
    return 0


def list_exhibitions(args):
    data = _load()

    filtered = data
    if args.current:
        filtered = [e for e in filtered if _live_status(e) == "current"]
    elif args.upcoming:
        filtered = [e for e in filtered if _live_status(e) == "upcoming"]
    elif args.past:
        filtered = [e for e in filtered if _live_status(e) == "past"]
    if args.city:
        filtered = [e for e in filtered if e.get("city", "").lower() == args.city.lower()]
    if args.country:
        filtered = [e for e in filtered if e.get("country", "").lower() == args.country.lower()]
    if args.artist:
        filtered = [e for e in filtered if args.artist in e.get("artist_ids", [])]

    print(json.dumps(filtered, indent=2, ensure_ascii=False))
    return 0


def show_exhibition(args):
    data = _load()
    for entry in data:
        if entry["id"] == args.id:
            print(json.dumps(entry, indent=2, ensure_ascii=False))
            return 0
    print(f"Error: Exhibition {args.id} not found", file=sys.stderr)
    return 2


def edit_exhibition(args):
    data = _load()
    for entry in data:
        if entry["id"] == args.id:
            print(f"Editing {args.id} (press Enter to keep current value)", file=sys.stderr)
            for field in ["title", "city", "country", "region", "start_date",
                          "end_date", "type", "admission", "focus", "status",
                          "description", "url", "image_url"]:
                current = entry.get(field, "")
                new_val = _prompt(field, default=str(current))
                if new_val and new_val != str(current):
                    entry[field] = new_val
            _save(data)
            print(f"Updated exhibition {args.id}", file=sys.stderr)
            print(json.dumps(entry, indent=2, ensure_ascii=False))
            return 0
    print(f"Error: Exhibition {args.id} not found", file=sys.stderr)
    return 2


def remove_exhibition(args):
    data = _load()
    target = None
    for e in data:
        if e["id"] == args.id:
            target = e
            break
    if not target:
        print(f"Error: Exhibition {args.id} not found", file=sys.stderr)
        return 2

    confirm = input(f"  Remove '{target['title']}' ({args.id})? [y/N] ").strip().lower()
    if confirm != "y":
        print("Cancelled.", file=sys.stderr)
        return 0

    filtered = [e for e in data if e["id"] != args.id]
    _save(filtered)
    print(f"Removed exhibition {args.id}", file=sys.stderr)
    return 0


def refresh_status(args):
    """Recalculate all status fields from dates."""
    data = _load()
    updated = 0
    for e in data:
        start = e.get("start_date", "")
        end = e.get("end_date", "")
        if is_valid_date(start) and is_valid_date(end):
            new_status = get_status(start, end)
            if e.get("status") != new_status:
                e["status"] = new_status
                updated += 1
    _save(data)
    print(f"Refreshed statuses: {updated} updated out of {len(data)} exhibitions", file=sys.stderr)
    return 0


def _live_status(e):
    """Get live status from dates, falling back to stored status."""
    start = e.get("start_date", "")
    end = e.get("end_date", "")
    if is_valid_date(start) and is_valid_date(end):
        return get_status(start, end)
    return e.get("status", "")
