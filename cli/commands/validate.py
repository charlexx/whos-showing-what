"""Validate data integrity."""

import json
import sys
from pathlib import Path

from utils.dates import validate_date_range, is_valid_date

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

STATUSES = {"upcoming", "current", "past"}
TYPES = {"solo", "group", "fair", "biennial", "residency", "screening", "performance"}
ADMISSION = {"free", "paid", "donation", "rsvp"}
FOCUS = {"dedicated", "diaspora", "significant", "featured"}
SOURCES = {"manual", "submission", "scrape", "api"}
REGIONS = {
    "West Africa", "East Africa", "Southern Africa", "North Africa", "Central Africa",
    "Europe", "North America", "South America", "Caribbean", "Middle East", "Asia", "Oceania",
}
ORIGIN_REGIONS = {"West Africa", "East Africa", "Southern Africa", "North Africa", "Central Africa"}
VENUE_TYPES = {"gallery", "museum", "institution", "project-space", "fair",
               "biennial-venue", "artist-run", "university", "online"}

# Required fields per entity
ARTIST_REQUIRED = ["id", "name", "origin_country", "origin_region", "mediums"]
VENUE_REQUIRED = ["id", "name", "city", "country", "type"]
EXHIBITION_REQUIRED = [
    "id", "title", "artist_ids", "venue_id", "city", "country", "region",
    "start_date", "end_date", "type", "admission", "mediums", "focus",
    "source", "added_date", "status",
]


def register(subparsers):
    parser = subparsers.add_parser("validate", help="Validate data integrity")
    parser.set_defaults(func=run_validate)


def run_validate(args):
    artists = _load("artists.json")
    venues = _load("venues.json")
    exhibitions = _load("exhibitions.json")

    artist_ids = {a["id"] for a in artists}
    venue_ids = {v["id"] for v in venues}
    errors = []

    # --- Duplicate ID checks ---
    _check_duplicates(artists, "Artist", errors)
    _check_duplicates(venues, "Venue", errors)
    _check_duplicates(exhibitions, "Exhibition", errors)

    # --- Artists ---
    for a in artists:
        _check_required(a, ARTIST_REQUIRED, "Artist", errors)
        if not a.get("id", "").startswith("art-"):
            errors.append(f"Artist {a.get('id', '?')}: invalid ID format")
        if a.get("origin_region") and a["origin_region"] not in ORIGIN_REGIONS:
            errors.append(f"Artist {a['id']}: invalid origin_region '{a['origin_region']}'")
        if "mediums" in a and (not isinstance(a["mediums"], list) or not a["mediums"]):
            errors.append(f"Artist {a['id']}: mediums must be a non-empty array")

    # --- Venues ---
    for v in venues:
        _check_required(v, VENUE_REQUIRED, "Venue", errors)
        if not v.get("id", "").startswith("ven-"):
            errors.append(f"Venue {v.get('id', '?')}: invalid ID format")
        if v.get("type") and v["type"] not in VENUE_TYPES:
            errors.append(f"Venue {v['id']}: invalid type '{v['type']}'")

    # --- Exhibitions ---
    for e in exhibitions:
        _check_required(e, EXHIBITION_REQUIRED, "Exhibition", errors)
        if not e.get("id", "").startswith("exh-"):
            errors.append(f"Exhibition {e.get('id', '?')}: invalid ID format")

        # Referential integrity
        for aid in e.get("artist_ids", []):
            if aid not in artist_ids:
                errors.append(f"Exhibition {e['id']}: references unknown artist {aid}")
        vid = e.get("venue_id")
        if vid and vid not in venue_ids:
            errors.append(f"Exhibition {e['id']}: references unknown venue {vid}")

        # Date validation
        start = e.get("start_date", "")
        end = e.get("end_date", "")
        if start and not is_valid_date(start):
            errors.append(f"Exhibition {e['id']}: invalid start_date '{start}'")
        if end and not is_valid_date(end):
            errors.append(f"Exhibition {e['id']}: invalid end_date '{end}'")
        if start and end and is_valid_date(start) and is_valid_date(end):
            if not validate_date_range(start, end):
                errors.append(f"Exhibition {e['id']}: start_date {start} is after end_date {end}")

        # Enum validation
        if e.get("status") and e["status"] not in STATUSES:
            errors.append(f"Exhibition {e['id']}: invalid status '{e['status']}'")
        if e.get("type") and e["type"] not in TYPES:
            errors.append(f"Exhibition {e['id']}: invalid type '{e['type']}'")
        if e.get("admission") and e["admission"] not in ADMISSION:
            errors.append(f"Exhibition {e['id']}: invalid admission '{e['admission']}'")
        if e.get("region") and e["region"] not in REGIONS:
            errors.append(f"Exhibition {e['id']}: invalid region '{e['region']}'")
        if e.get("focus") and e["focus"] not in FOCUS:
            errors.append(f"Exhibition {e['id']}: invalid focus '{e['focus']}'")
        if e.get("source") and e["source"] not in SOURCES:
            errors.append(f"Exhibition {e['id']}: invalid source '{e['source']}'")

    if errors:
        print(f"Validation FAILED with {len(errors)} error(s):", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 2
    else:
        print("Validation passed.", file=sys.stderr)
        return 0


def _check_duplicates(data, label, errors):
    seen = set()
    for entry in data:
        eid = entry.get("id", "")
        if eid in seen:
            errors.append(f"{label}: duplicate ID '{eid}'")
        seen.add(eid)


def _check_required(entry, required_fields, label, errors):
    for field in required_fields:
        if field not in entry or entry[field] is None or entry[field] == "":
            errors.append(f"{label} {entry.get('id', '?')}: missing required field '{field}'")


def _load(filename):
    with open(DATA_DIR / filename) as f:
        return json.load(f)
