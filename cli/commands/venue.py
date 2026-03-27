"""Venue management commands."""

import json
import sys
from pathlib import Path

from utils.ids import make_venue_id, id_exists

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DATA_FILE = DATA_DIR / "venues.json"

VENUE_TYPES = ["gallery", "museum", "institution", "project-space", "fair",
               "biennial-venue", "artist-run", "university", "online"]


def _load(filename="venues.json"):
    with open(DATA_DIR / filename) as f:
        return json.load(f)


def _save(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def _prompt(label, default="", choices=None):
    suffix = f" [{default}]" if default else ""
    if choices:
        print(f"  Options: {', '.join(choices)}", file=sys.stderr)
    val = input(f"  {label}{suffix}: ").strip()
    return val if val else default


def _prompt_required(label, choices=None):
    while True:
        val = _prompt(label, choices=choices)
        if val:
            return val
        print("  (required)", file=sys.stderr)


def register(subparsers):
    parser = subparsers.add_parser("venue", help="Manage venues")
    sub = parser.add_subparsers(dest="action", required=True)

    # add
    add_p = sub.add_parser("add", help="Add a venue")
    add_p.add_argument("--name")
    add_p.add_argument("--city")
    add_p.add_argument("--country")
    add_p.add_argument("--type", dest="venue_type", choices=VENUE_TYPES)
    add_p.add_argument("--website", default="")
    add_p.add_argument("--notes", default="")
    add_p.set_defaults(func=add_venue)

    # list
    list_p = sub.add_parser("list", help="List venues")
    list_p.add_argument("--city")
    list_p.add_argument("--type", dest="venue_type", choices=VENUE_TYPES)
    list_p.set_defaults(func=list_venues)

    # show
    show_p = sub.add_parser("show", help="Show venue details")
    show_p.add_argument("id")
    show_p.set_defaults(func=show_venue)

    # edit
    edit_p = sub.add_parser("edit", help="Edit a venue")
    edit_p.add_argument("id")
    edit_p.set_defaults(func=edit_venue)

    # remove
    rm_p = sub.add_parser("remove", help="Remove a venue")
    rm_p.add_argument("id")
    rm_p.set_defaults(func=remove_venue)


def add_venue(args):
    print("Add Venue", file=sys.stderr)

    name = args.name or _prompt_required("Name")
    city = args.city or _prompt_required("City")
    country = args.country or _prompt_required("Country")
    venue_type = args.venue_type or _prompt_required("Type", choices=VENUE_TYPES)

    data = _load()
    new_id = make_venue_id(name)
    if id_exists(data, new_id):
        print(f"Error: Venue {new_id} already exists", file=sys.stderr)
        return 1

    entry = {
        "id": new_id,
        "name": name,
        "city": city,
        "country": country,
        "type": venue_type,
    }

    website = args.website or _prompt("Website")
    if website:
        entry["website"] = website

    notes = args.notes or _prompt("Notes")
    if notes:
        entry["notes"] = notes

    data.append(entry)
    _save(data)
    print(f"Added venue {new_id}: {name}", file=sys.stderr)
    print(json.dumps(entry, indent=2, ensure_ascii=False))
    return 0


def list_venues(args):
    data = _load()
    filtered = data
    if args.city:
        filtered = [v for v in filtered if v.get("city", "").lower() == args.city.lower()]
    if args.venue_type:
        filtered = [v for v in filtered if v.get("type") == args.venue_type]
    print(json.dumps(filtered, indent=2, ensure_ascii=False))
    return 0


def show_venue(args):
    data = _load()
    for entry in data:
        if entry["id"] == args.id:
            print(json.dumps(entry, indent=2, ensure_ascii=False))
            return 0
    print(f"Error: Venue {args.id} not found", file=sys.stderr)
    return 2


def edit_venue(args):
    data = _load()
    for entry in data:
        if entry["id"] == args.id:
            print(f"Editing {args.id} (press Enter to keep current value)", file=sys.stderr)
            for field in ["name", "city", "country", "website", "notes"]:
                current = entry.get(field, "")
                new_val = _prompt(field, default=str(current) if current else "")
                if new_val and new_val != str(current):
                    entry[field] = new_val
            current_type = entry.get("type", "")
            new_type = _prompt("type", default=current_type, choices=VENUE_TYPES)
            if new_type and new_type != current_type:
                entry["type"] = new_type
            _save(data)
            print(f"Updated venue {args.id}", file=sys.stderr)
            print(json.dumps(entry, indent=2, ensure_ascii=False))
            return 0
    print(f"Error: Venue {args.id} not found", file=sys.stderr)
    return 2


def remove_venue(args):
    data = _load()
    target = None
    for v in data:
        if v["id"] == args.id:
            target = v
            break
    if not target:
        print(f"Error: Venue {args.id} not found", file=sys.stderr)
        return 2

    # Warn if referenced by exhibitions
    exhibitions = _load("exhibitions.json")
    refs = [e for e in exhibitions if e.get("venue_id") == args.id]
    if refs:
        print(f"  Warning: Venue is referenced by {len(refs)} exhibition(s):", file=sys.stderr)
        for e in refs:
            print(f"    {e['id']}: {e['title']}", file=sys.stderr)

    confirm = input(f"  Remove '{target['name']}' ({args.id})? [y/N] ").strip().lower()
    if confirm != "y":
        print("Cancelled.", file=sys.stderr)
        return 0

    filtered = [v for v in data if v["id"] != args.id]
    _save(filtered)
    print(f"Removed venue {args.id}", file=sys.stderr)
    return 0
