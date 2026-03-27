"""Artist management commands."""

import json
import sys
from pathlib import Path

from utils.ids import make_artist_id, id_exists

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DATA_FILE = DATA_DIR / "artists.json"

ORIGIN_REGIONS = ["West Africa", "East Africa", "Southern Africa", "North Africa", "Central Africa"]


def _load(filename="artists.json"):
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
    parser = subparsers.add_parser("artist", help="Manage artists")
    sub = parser.add_subparsers(dest="action", required=True)

    # add
    add_p = sub.add_parser("add", help="Add an artist")
    add_p.add_argument("--name")
    add_p.add_argument("--origin-country")
    add_p.add_argument("--origin-region", choices=ORIGIN_REGIONS)
    add_p.add_argument("--mediums", nargs="+")
    add_p.add_argument("--based-in", nargs=2, metavar=("CITY", "COUNTRY"))
    add_p.add_argument("--is-diaspora", action="store_true", default=False)
    add_p.add_argument("--birth-year", type=int)
    add_p.add_argument("--website", default="")
    add_p.add_argument("--notes", default="")
    add_p.set_defaults(func=add_artist)

    # list
    list_p = sub.add_parser("list", help="List artists")
    list_p.add_argument("--country")
    list_p.add_argument("--region", choices=ORIGIN_REGIONS)
    list_p.set_defaults(func=list_artists)

    # search
    search_p = sub.add_parser("search", help="Search artists by name")
    search_p.add_argument("query")
    search_p.set_defaults(func=search_artists)

    # show
    show_p = sub.add_parser("show", help="Show artist details")
    show_p.add_argument("id")
    show_p.set_defaults(func=show_artist)

    # edit
    edit_p = sub.add_parser("edit", help="Edit an artist")
    edit_p.add_argument("id")
    edit_p.set_defaults(func=edit_artist)

    # remove
    rm_p = sub.add_parser("remove", help="Remove an artist")
    rm_p.add_argument("id")
    rm_p.set_defaults(func=remove_artist)


def add_artist(args):
    print("Add Artist", file=sys.stderr)

    name = args.name or _prompt_required("Name")
    origin_country = args.origin_country or _prompt_required("Origin country")
    origin_region = args.origin_region or _prompt_required("Origin region", choices=ORIGIN_REGIONS)

    if args.mediums:
        mediums = args.mediums
    else:
        raw = _prompt_required("Mediums (comma-separated)")
        mediums = [m.strip() for m in raw.split(",") if m.strip()]

    data = _load()
    new_id = make_artist_id(name)
    if id_exists(data, new_id):
        print(f"Error: Artist {new_id} already exists", file=sys.stderr)
        return 1

    entry = {
        "id": new_id,
        "name": name,
        "origin_country": origin_country,
        "origin_region": origin_region,
        "mediums": mediums,
    }

    # Optional fields via interactive prompts
    based_in_city = args.based_in[0] if args.based_in else _prompt("Based in city")
    based_in_country = args.based_in[1] if args.based_in else (_prompt("Based in country") if based_in_city else "")
    if based_in_city and based_in_country:
        entry["based_in"] = [based_in_city, based_in_country]

    diaspora = args.is_diaspora or (_prompt("Is diaspora? (y/N)").lower() == "y")
    if diaspora:
        entry["is_diaspora"] = True

    birth_year = args.birth_year or _prompt("Birth year")
    if birth_year:
        entry["birth_year"] = int(birth_year)

    website = args.website or _prompt("Website")
    if website:
        entry["website"] = website

    notes = args.notes or _prompt("Notes")
    if notes:
        entry["notes"] = notes

    data.append(entry)
    _save(data)
    print(f"Added artist {new_id}: {name}", file=sys.stderr)
    print(json.dumps(entry, indent=2, ensure_ascii=False))
    return 0


def list_artists(args):
    data = _load()
    filtered = data
    if args.country:
        filtered = [a for a in filtered
                    if a.get("origin_country", "").lower() == args.country.lower()]
    if args.region:
        filtered = [a for a in filtered if a.get("origin_region") == args.region]
    print(json.dumps(filtered, indent=2, ensure_ascii=False))
    return 0


def search_artists(args):
    """Fuzzy name match — case-insensitive substring search."""
    data = _load()
    query = args.query.lower()
    matches = [a for a in data if query in a.get("name", "").lower()]
    if not matches:
        print(f"No artists matching '{args.query}'", file=sys.stderr)
        return 0
    print(json.dumps(matches, indent=2, ensure_ascii=False))
    return 0


def show_artist(args):
    data = _load()
    for entry in data:
        if entry["id"] == args.id:
            print(json.dumps(entry, indent=2, ensure_ascii=False))
            return 0
    print(f"Error: Artist {args.id} not found", file=sys.stderr)
    return 2


def edit_artist(args):
    data = _load()
    for entry in data:
        if entry["id"] == args.id:
            print(f"Editing {args.id} (press Enter to keep current value)", file=sys.stderr)
            for field in ["name", "origin_country", "origin_region", "birth_year",
                          "website", "notes"]:
                current = entry.get(field, "")
                new_val = _prompt(field, default=str(current) if current else "")
                if new_val and new_val != str(current):
                    if field == "birth_year":
                        entry[field] = int(new_val)
                    else:
                        entry[field] = new_val
            # Mediums
            current_mediums = ", ".join(entry.get("mediums", []))
            new_mediums = _prompt("mediums (comma-separated)", default=current_mediums)
            if new_mediums and new_mediums != current_mediums:
                entry["mediums"] = [m.strip() for m in new_mediums.split(",") if m.strip()]

            _save(data)
            print(f"Updated artist {args.id}", file=sys.stderr)
            print(json.dumps(entry, indent=2, ensure_ascii=False))
            return 0
    print(f"Error: Artist {args.id} not found", file=sys.stderr)
    return 2


def remove_artist(args):
    data = _load()
    target = None
    for a in data:
        if a["id"] == args.id:
            target = a
            break
    if not target:
        print(f"Error: Artist {args.id} not found", file=sys.stderr)
        return 2

    # Warn if referenced by exhibitions
    exhibitions = _load("exhibitions.json")
    refs = [e for e in exhibitions if args.id in e.get("artist_ids", [])]
    if refs:
        print(f"  Warning: Artist is referenced by {len(refs)} exhibition(s):", file=sys.stderr)
        for e in refs:
            print(f"    {e['id']}: {e['title']}", file=sys.stderr)

    confirm = input(f"  Remove '{target['name']}' ({args.id})? [y/N] ").strip().lower()
    if confirm != "y":
        print("Cancelled.", file=sys.stderr)
        return 0

    filtered = [a for a in data if a["id"] != args.id]
    _save(filtered)
    print(f"Removed artist {args.id}", file=sys.stderr)
    return 0
