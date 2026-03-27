"""Verify exhibition data — Layer 1 fact-checking (stdlib only, no API costs)."""

import difflib
import html
import json
import re
import ssl
import sys
import urllib.error
import urllib.request
from datetime import date, timedelta
from pathlib import Path

from utils.dates import is_valid_date, parse_date, today_str

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

TIMEOUT = 10  # seconds
USER_AGENT = "Radar/1.0 (exhibition-tracker; +https://radar.formefemine.com)"
PLACEHOLDER_DATES = {"2030-12-31", "2029-12-31", "2099-12-31"}
MAX_DURATION_DAYS = 730  # 2 years
SIMILARITY_THRESHOLD = 0.8

# SSL context — try default certs, fall back to unverified for macOS compat
try:
    _SSL_CTX = ssl.create_default_context()
    urllib.request.urlopen("https://example.com", timeout=5, context=_SSL_CTX)
except Exception:
    _SSL_CTX = ssl.create_default_context()
    _SSL_CTX.check_hostname = False
    _SSL_CTX.verify_mode = ssl.CERT_NONE

REQUIRED_FIELDS = [
    "title", "venue_id", "city", "country", "region",
    "start_date", "end_date", "type", "admission", "focus", "source",
]


def register(subparsers):
    parser = subparsers.add_parser("verify", help="Fact-check exhibition data")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print results without saving to exhibitions.json")
    parser.add_argument("--quiet", action="store_true",
                        help="Only show medium and low confidence results")
    parser.set_defaults(func=run_verify)


def run_verify(args):
    exhibitions = _load("exhibitions.json")
    artists = _load("artists.json")
    venues = _load("venues.json")

    artist_map = {a["id"]: a for a in artists}
    venue_map = {v["id"]: v for v in venues}

    dry_run = getattr(args, "dry_run", False)
    quiet = getattr(args, "quiet", False)

    counts = {"high": 0, "medium": 0, "low": 0}
    total = len(exhibitions)

    print(f"Verifying {total} exhibitions...\n", file=sys.stderr)

    for exh in exhibitions:
        eid = exh.get("id", "?")
        checks = []

        # --- 1. Required field completeness ---
        missing = _check_required_fields(exh)
        if missing:
            checks.append(("fail", f"Missing fields: {', '.join(missing)}"))
        else:
            checks.append(("pass", "All required fields present"))

        # --- 2. Date sanity ---
        date_issues = _check_dates(exh)
        for issue in date_issues:
            checks.append(("fail", issue))
        if not date_issues:
            checks.append(("pass", "Dates valid"))

        # --- 3. URL resolution + content matching ---
        url = exh.get("url", "").strip()
        artist_names = _resolve_artist_names(exh.get("artist_ids", []), artist_map)
        title = exh.get("title", "")

        if url:
            url_ok, url_msg = _check_url(url)
            checks.append(("pass" if url_ok else "fail", url_msg))

            if url_ok:
                page = _fetch_page(url)
                if page:
                    title_found = _text_in_page(title, page)
                    artist_found = any(_text_in_page(n, page) for n in artist_names) if artist_names else False

                    if title_found:
                        checks.append(("pass", "Title found on page"))
                    else:
                        checks.append(("warn", "Title not found on page"))

                    if artist_names:
                        if artist_found:
                            checks.append(("pass", "Artist name found on page"))
                        else:
                            checks.append(("warn", "No artist names found on page"))
                else:
                    checks.append(("warn", "Could not fetch page content"))
        else:
            checks.append(("warn", "No exhibition URL provided"))

        # --- 4. Venue cross-reference ---
        venue = venue_map.get(exh.get("venue_id", ""))
        venue_website = venue.get("website", "").strip() if venue else ""

        if venue_website:
            venue_page = _fetch_page(venue_website)
            if venue_page and _text_in_page(title, venue_page):
                checks.append(("pass", "Venue website confirms exhibition"))
            elif venue_page:
                checks.append(("warn", "Exhibition not found on venue website"))
            else:
                checks.append(("warn", "Could not fetch venue website"))
        elif not url:
            checks.append(("fail", "No URL and no venue website to cross-reference"))

        # --- 5. Duplicate detection ---
        # (handled in a second pass below, placeholder for now)

        # --- Score ---
        confidence = _score(checks, url)
        exh["verified"] = True if confidence == "high" else ("pending" if confidence == "medium" else False)
        exh["verified_date"] = today_str()
        exh["confidence"] = confidence
        counts[confidence] += 1

        if quiet and confidence == "high":
            continue

        _print_result(eid, checks, confidence)

    # --- Duplicate detection (cross-exhibition) ---
    dup_pairs = _find_duplicates(exhibitions)
    for id_a, id_b, ratio in dup_pairs:
        print(f"\n  {id_a}", file=sys.stderr)
        print(f"  \u2757 Possible duplicate of {id_b} (similarity: {ratio:.0%})", file=sys.stderr)
        # Mark both as medium at most if they were high
        for exh in exhibitions:
            if exh["id"] in (id_a, id_b):
                if exh.get("confidence") == "high":
                    exh["confidence"] = "medium"
                    exh["verified"] = "pending"
                    counts["high"] -= 1
                    counts["medium"] += 1

    # --- Summary ---
    print(f"\nVerified: {counts['high']} high, {counts['medium']} medium, {counts['low']} low",
          file=sys.stderr)

    if dry_run:
        print("(dry run — no changes saved)", file=sys.stderr)
        return 0

    _save("exhibitions.json", exhibitions)
    print("Results saved to data/exhibitions.json", file=sys.stderr)
    return 0


# ========== Checks ==========

def _check_required_fields(exh):
    missing = []
    for field in REQUIRED_FIELDS:
        val = exh.get(field)
        if val is None or val == "":
            missing.append(field)
    return missing


def _check_dates(exh):
    issues = []
    start_str = exh.get("start_date", "")
    end_str = exh.get("end_date", "")

    if not start_str or not is_valid_date(start_str):
        issues.append(f"Invalid start_date: {start_str!r}")
        return issues
    if not end_str or not is_valid_date(end_str):
        issues.append(f"Invalid end_date: {end_str!r}")
        return issues

    start = parse_date(start_str)
    end = parse_date(end_str)

    if start > end:
        issues.append(f"start_date ({start_str}) is after end_date ({end_str})")

    if end_str in PLACEHOLDER_DATES:
        issues.append(f"end_date looks like a placeholder ({end_str})")

    if (end - start).days > MAX_DURATION_DAYS:
        issues.append(f"Duration is {(end - start).days} days (>{MAX_DURATION_DAYS})")

    return issues


def _check_url(url):
    """Send a HEAD request. Return (ok, message)."""
    req = urllib.request.Request(url, method="HEAD",
                                headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=_SSL_CTX) as resp:
            code = resp.getcode()
            if code == 200:
                return True, f"URL resolves ({code})"
            return False, f"URL returned {code}"
    except urllib.error.HTTPError as e:
        # Some servers reject HEAD but accept GET — try GET with range
        if e.code == 405 or e.code == 403:
            return _check_url_get_fallback(url)
        return False, f"URL returned {e.code}"
    except urllib.error.URLError as e:
        return False, f"URL error: {e.reason}"
    except Exception as e:
        return False, f"URL error: {e}"


def _check_url_get_fallback(url):
    """Fallback: try a GET request if HEAD was rejected."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                               "Range": "bytes=0-1024"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=_SSL_CTX) as resp:
            code = resp.getcode()
            if code in (200, 206):
                return True, f"URL resolves ({code})"
            return False, f"URL returned {code}"
    except urllib.error.HTTPError as e:
        return False, f"URL returned {e.code}"
    except Exception as e:
        return False, f"URL error: {e}"


def _fetch_page(url):
    """Fetch page content as lowercase text. Returns None on failure."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=_SSL_CTX) as resp:
            raw = resp.read(512_000)  # limit to 500KB
            charset = resp.headers.get_content_charset() or "utf-8"
            try:
                text = raw.decode(charset, errors="replace")
            except (LookupError, UnicodeDecodeError):
                text = raw.decode("utf-8", errors="replace")
            # Strip HTML tags, decode entities, normalise whitespace
            text = html.unescape(text)
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"\s+", " ", text)
            return text.lower()
    except Exception:
        return None


def _text_in_page(needle, page_text):
    """Check if needle (or a close substring) appears in page text."""
    if not needle:
        return False
    needle_lower = needle.lower().strip()
    if needle_lower in page_text:
        return True
    # Try individual significant words (3+ chars) — if most match, count it
    words = [w for w in needle_lower.split() if len(w) >= 3]
    if not words:
        return False
    found = sum(1 for w in words if w in page_text)
    return found >= len(words) * 0.7


def _resolve_artist_names(artist_ids, artist_map):
    names = []
    for aid in artist_ids:
        artist = artist_map.get(aid)
        if artist:
            names.append(artist["name"])
    return names


def _find_duplicates(exhibitions):
    """Find exhibitions at the same venue with similar titles."""
    by_venue = {}
    for exh in exhibitions:
        vid = exh.get("venue_id", "")
        by_venue.setdefault(vid, []).append(exh)

    pairs = []
    for vid, exhs in by_venue.items():
        for i in range(len(exhs)):
            for j in range(i + 1, len(exhs)):
                t1 = exhs[i].get("title", "").lower()
                t2 = exhs[j].get("title", "").lower()
                ratio = difflib.SequenceMatcher(None, t1, t2).ratio()
                if ratio >= SIMILARITY_THRESHOLD:
                    pairs.append((exhs[i]["id"], exhs[j]["id"], ratio))
    return pairs


# ========== Scoring ==========

def _score(checks, url):
    """Score confidence based on check results."""
    fails = [c for c in checks if c[0] == "fail"]
    warns = [c for c in checks if c[0] == "warn"]
    passes = [c for c in checks if c[0] == "pass"]

    # Low: any hard failure (404, date issues, missing required fields, no sources at all)
    has_url_fail = any("URL returned" in c[1] or "URL error" in c[1] for c in fails)
    has_date_fail = any("start_date" in c[1] or "end_date" in c[1] or "placeholder" in c[1]
                        or "Duration" in c[1] for c in fails)
    has_missing_fields = any("Missing fields" in c[1] for c in fails)
    has_no_sources = any("No URL and no venue website" in c[1] for c in fails)

    if has_url_fail or has_date_fail or has_missing_fields or has_no_sources:
        return "low"

    # High: URL resolves AND (title or artist found on page) AND no fails AND no warns
    url_resolves = any("URL resolves" in c[1] for c in passes)
    content_confirmed = any("found on page" in c[1] or "confirms exhibition" in c[1] for c in passes)

    if url_resolves and content_confirmed and not fails:
        return "high"

    return "medium"


# ========== Output ==========

def _print_result(eid, checks, confidence):
    print(f"  {eid}", file=sys.stderr)
    for kind, msg in checks:
        if kind == "pass":
            icon = "\u2713"
        elif kind == "warn":
            icon = "\u26A0"
        else:
            icon = "\u2717"
        print(f"  {icon} {msg}", file=sys.stderr)

    suffix = ""
    if confidence == "low":
        suffix = " (needs manual review)"
    elif confidence == "medium":
        suffix = " (partial verification)"

    print(f"  \u2192 confidence: {confidence}{suffix}\n", file=sys.stderr)


# ========== I/O ==========

def _load(filename):
    with open(DATA_DIR / filename) as f:
        return json.load(f)


def _save(filename, data):
    with open(DATA_DIR / filename, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
