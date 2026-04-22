"""Build static site from data."""

import html
import json
import sys
from datetime import date, datetime
from pathlib import Path

from utils.dates import format_date_long, get_status

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
SITE_DIR = Path(__file__).resolve().parent.parent.parent / "site"
BASE_URL = "https://radar.formefemine.com"


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

    _build_exhibition_pages(exhibitions, artists, venues)
    _build_sitemap(exhibitions)
    _build_robots_txt()

    return 0


def _load(filename):
    with open(DATA_DIR / filename) as f:
        return json.load(f)


# ==================== Exhibition Pages ====================

def _build_exhibition_pages(exhibitions, artists, venues):
    """Generate individual HTML pages for each exhibition."""
    exh_dir = SITE_DIR / "exhibition"
    exh_dir.mkdir(exist_ok=True)

    # Clear existing generated pages
    for f in exh_dir.glob("*.html"):
        f.unlink()

    artist_map = {a["id"]: a for a in artists}
    venue_map = {v["id"]: v for v in venues}

    for exh in exhibitions:
        page_html = _render_exhibition_page(exh, artist_map, venue_map, exhibitions)
        (exh_dir / f"{exh['id']}.html").write_text(page_html, encoding="utf-8")

    print(f"Built {len(exhibitions)} exhibition pages", file=sys.stderr)


def _find_related(exh, all_exhibitions, venue_map, max_count=6):
    """Find up to max_count related exhibitions in priority order."""
    h = html.escape
    current_id = exh["id"]
    artist_ids = set(exh.get("artist_ids", []))
    venue_id = exh.get("venue_id", "")
    city = exh.get("city", "")
    focus = exh.get("focus", "")

    seen = {current_id}
    related = []

    # Priority 1: Same artist
    if artist_ids:
        for other in all_exhibitions:
            if other["id"] in seen:
                continue
            if artist_ids & set(other.get("artist_ids", [])):
                seen.add(other["id"])
                related.append((other, "Same artist"))
                if len(related) >= max_count:
                    return related

    # Priority 2: Same venue
    if venue_id:
        for other in all_exhibitions:
            if other["id"] in seen:
                continue
            if other.get("venue_id") == venue_id:
                seen.add(other["id"])
                related.append((other, "Same venue"))
                if len(related) >= max_count:
                    return related

    # Priority 3: Same city
    if city:
        for other in all_exhibitions:
            if other["id"] in seen:
                continue
            if other.get("city") == city:
                seen.add(other["id"])
                related.append((other, f"Also in {h(city)}"))
                if len(related) >= max_count:
                    return related

    # Priority 4: Same focus
    if focus:
        for other in all_exhibitions:
            if other["id"] in seen:
                continue
            if other.get("focus") == focus:
                seen.add(other["id"])
                related.append((other, "Similar focus"))
                if len(related) >= max_count:
                    return related

    return related


def _render_related_html(exh, all_exhibitions, venue_map):
    """Render the related exhibitions section HTML."""
    h = html.escape
    related = _find_related(exh, all_exhibitions, venue_map)
    if not related:
        return ""

    cards = []
    for other, reason in related:
        oid = h(other["id"])
        otitle = h(other["title"])
        ovenue = venue_map.get(other.get("venue_id", ""), {})
        ovenue_name = h(ovenue.get("name", other.get("venue_id", "")))
        ocity = h(other.get("city", ""))
        ocountry = h(other.get("country", ""))
        odates = f"{format_date_long(other['start_date'])} \u2013 {format_date_long(other['end_date'])}"
        cards.append(
            f'<a href="../exhibition/{oid}.html" class="exh-related-card">'
            f'<span class="exh-related-card-title">{otitle}</span>'
            f'<span class="exh-related-card-venue">{ovenue_name}</span>'
            f'<span class="exh-related-card-city">{ocity}, {ocountry}</span>'
            f'<span class="exh-related-card-dates">{h(odates)}</span>'
            f'<span class="exh-related-card-reason">{reason}</span>'
            f"</a>"
        )

    return (
        '<section class="exh-related">'
        "<h2>Related exhibitions</h2>"
        '<div class="exh-related-grid">' + "".join(cards) + "</div>"
        "</section>"
    )


def _render_exhibition_page(exh, artist_map, venue_map, all_exhibitions=None):
    """Return a complete HTML string for an exhibition detail page."""
    h = html.escape
    exh_id = exh["id"]
    title = h(exh["title"])
    status = get_status(exh["start_date"], exh["end_date"])
    date_range = f"{format_date_long(exh['start_date'])} \u2013 {format_date_long(exh['end_date'])}"

    venue = venue_map.get(exh["venue_id"], {})
    venue_name = h(venue.get("name", exh["venue_id"]))
    venue_website = venue.get("website", "")
    city = h(exh["city"])
    country = h(exh["country"])
    region = h(exh["region"])

    # Resolve artists
    artists_html = ""
    artist_names_plain = []
    if exh.get("artist_ids"):
        artist_items = []
        for aid in exh["artist_ids"]:
            a = artist_map.get(aid)
            if a:
                name = h(a["name"])
                origin = h(a.get("origin_country", ""))
                detail = f' <span class="exh-artist-origin">{origin}</span>' if origin else ""
                artist_items.append(f"<li><strong>{name}</strong>{detail}</li>")
                artist_names_plain.append(a["name"])
            else:
                artist_items.append(f"<li>{h(aid)}</li>")
                artist_names_plain.append(aid)
        artists_html = (
            '<section class="exh-artists">'
            "<h2>Artists</h2>"
            '<ul class="exh-artist-list">' + "".join(artist_items) + "</ul>"
            "</section>"
        )

    # Description
    description_html = ""
    desc_text = exh.get("description", "")
    if desc_text:
        description_html = (
            '<section class="exh-description">'
            f"<p>{h(desc_text)}</p>"
            "</section>"
        )

    # Badges
    exh_type = h(exh.get("type", ""))
    admission = h(exh.get("admission", ""))
    focus = exh.get("focus", "")
    admission_class = " free" if admission == "free" else ""

    focus_badge = ""
    if focus:
        focus_badge = f'<span class="badge badge-focus {h(focus)}">{h(focus)}</span>'

    badges_html = (
        '<div class="exh-badges">'
        f'<span class="badge badge-status {h(status)}">{h(status)}</span>'
        f'<span class="badge badge-type">{exh_type}</span>'
        f'<span class="badge badge-admission{admission_class}">{admission}</span>'
        f'{focus_badge}'
        "</div>"
    )

    # Mediums
    mediums_html = ""
    if exh.get("mediums"):
        tags = "".join(f'<span class="medium-tag">{h(m)}</span>' for m in exh["mediums"])
        mediums_html = f'<div class="exh-mediums">{tags}</div>'

    # Details grid
    details_items = []
    details_items.append(f"<dt>City</dt><dd>{city}</dd>")
    details_items.append(f"<dt>Country</dt><dd>{country}</dd>")
    details_items.append(f"<dt>Region</dt><dd>{region}</dd>")
    if exh_type:
        details_items.append(f"<dt>Type</dt><dd>{exh_type}</dd>")
    if admission:
        details_items.append(f"<dt>Admission</dt><dd>{admission}</dd>")
    if focus:
        focus_labels = {
            "dedicated": "Dedicated to African artists",
            "diaspora": "Black diaspora artists",
            "significant": "Significant African and diaspora presence",
            "featured": "African and diaspora artists featured",
        }
        focus_display = focus_labels.get(focus, h(focus))
        details_items.append(f"<dt>Focus</dt><dd>{focus_display}</dd>")
    if exh.get("source"):
        details_items.append(f'<dt>Source</dt><dd>{h(exh["source"])}</dd>')
    if exh.get("confidence"):
        details_items.append(f'<dt>Confidence</dt><dd>{h(exh["confidence"])}</dd>')

    details_html = (
        '<section class="exh-details">'
        "<h2>Details</h2>"
        '<dl class="exh-details-grid">' + "".join(details_items) + "</dl>"
        "</section>"
    )

    # Venue section
    if venue_website:
        venue_link = f'<a href="{h(venue_website)}" target="_blank" rel="noopener noreferrer">{venue_name}</a>'
    else:
        venue_link = venue_name
    venue_type = h(venue.get("type", ""))
    venue_type_html = f' <span class="exh-venue-type">({venue_type})</span>' if venue_type else ""

    venue_section = (
        '<section class="exh-venue">'
        "<h2>Venue</h2>"
        f"<p>{venue_link}{venue_type_html}</p>"
        f"<p>{city}, {country}</p>"
        "</section>"
    )

    # CTA
    cta_html = ""
    if exh.get("url"):
        cta_html = (
            '<div class="exh-cta-wrap">'
            f'<a class="exh-cta" href="{h(exh["url"])}" target="_blank" rel="noopener noreferrer">'
            'Visit exhibition <span>\u2192</span>'
            "</a>"
            "</div>"
        )

    # JSON-LD structured data
    jsonld = {
        "@context": "https://schema.org",
        "@type": "ExhibitionEvent",
        "name": exh["title"],
        "startDate": exh["start_date"],
        "endDate": exh["end_date"],
        "location": {
            "@type": "Place",
            "name": venue.get("name", ""),
            "address": {
                "@type": "PostalAddress",
                "addressLocality": exh["city"],
                "addressCountry": exh["country"],
            },
        },
    }
    if exh.get("url"):
        jsonld["url"] = exh["url"]
    if exh.get("description"):
        jsonld["description"] = exh["description"]
    if artist_names_plain:
        jsonld["performer"] = [
            {"@type": "Person", "name": name} for name in artist_names_plain
        ]

    jsonld_str = json.dumps(jsonld, indent=2, ensure_ascii=False)

    # Related exhibitions
    related_html = ""
    if all_exhibitions:
        related_html = _render_related_html(exh, all_exhibitions, venue_map)

    # OG description
    og_desc = desc_text if desc_text else f"{exh['title']} at {venue.get('name', '')}, {exh['city']}"
    if len(og_desc) > 200:
        og_desc = og_desc[:197] + "..."

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="description" content="{h(og_desc)}">
  <link rel="canonical" href="{BASE_URL}/exhibition/{h(exh_id)}.html">
  <meta property="og:type" content="website">
  <meta property="og:title" content="{title} — Radar">
  <meta property="og:description" content="{h(og_desc)}">
  <meta property="og:url" content="{BASE_URL}/exhibition/{h(exh_id)}.html">
  <meta property="og:image" content="{BASE_URL}/static/og-image.svg">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{title} — Radar">
  <meta name="twitter:description" content="{h(og_desc)}">
  <meta name="twitter:image" content="{BASE_URL}/static/og-image.svg">
  <title>{title} — Radar</title>
  <link rel="stylesheet" href="../css/styles.css">
  <script type="application/ld+json">
{jsonld_str}
  </script>
  <script>if(localStorage.getItem("radar-theme")==="dark")document.documentElement.setAttribute("data-theme","dark")</script>
</head>
<body>
  <a href="#main" class="skip-link">Skip to content</a>
  <header class="exh-header-bar">
    <a href="../" class="exh-back">\u2190 All exhibitions</a>
    <button id="theme-toggle" class="theme-toggle" aria-label="Toggle light/dark mode">&#9728;</button>
  </header>

  <article class="exh-page" id="main">
    {badges_html}
    <h1 class="exh-title">{title}</h1>
    <p class="exh-dates">
      <span class="exh-status-label {h(status)}">{h(status).capitalize()}</span>
      \u00a0\u00b7\u00a0 {h(date_range)}
    </p>

    {venue_section}
    {artists_html}
    {description_html}
    {mediums_html}
    {details_html}
    {cta_html}
    {related_html}
  </article>

  <footer class="exh-footer">
    <p class="footer-brand">Radar by <a href="https://formefemine.com" class="footer-link">Forme Femine</a> &middot; <a href="../about.html" class="footer-about-link">About</a></p>
    <p class="footer-copy">&copy; {date.today().year}</p>
  </footer>

  <script>
  (function(){{
    var t=document.getElementById("theme-toggle");
    function g(){{var s=localStorage.getItem("radar-theme");if(s)return s;return"light"}}
    function a(m){{if(m==="dark"){{document.documentElement.setAttribute("data-theme","dark")}}else{{document.documentElement.removeAttribute("data-theme")}}if(t){{t.textContent=m==="dark"?"\\u263E":"\\u2600"}}}}
    a(g());
    if(t){{t.addEventListener("click",function(){{var c=document.documentElement.getAttribute("data-theme")==="dark"?"dark":"light";var n=c==="dark"?"light":"dark";a(n);localStorage.setItem("radar-theme",n)}})}}
  }})();
  </script>
</body>
</html>"""


# ==================== Sitemap ====================

def _build_sitemap(exhibitions):
    """Generate sitemap.xml with main page and all exhibition pages."""
    today = date.today().isoformat()

    urls = []
    urls.append(
        f"  <url>\n"
        f"    <loc>{BASE_URL}/</loc>\n"
        f"    <lastmod>{today}</lastmod>\n"
        f"    <changefreq>weekly</changefreq>\n"
        f"  </url>"
    )

    urls.append(
        f"  <url>\n"
        f"    <loc>{BASE_URL}/about.html</loc>\n"
        f"    <lastmod>{today}</lastmod>\n"
        f"    <changefreq>monthly</changefreq>\n"
        f"  </url>"
    )

    for exh in exhibitions:
        exh_id = html.escape(exh["id"])
        urls.append(
            f"  <url>\n"
            f"    <loc>{BASE_URL}/exhibition/{exh_id}.html</loc>\n"
            f"    <lastmod>{today}</lastmod>\n"
            f"    <changefreq>monthly</changefreq>\n"
            f"  </url>"
        )

    sitemap = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls) + "\n"
        "</urlset>\n"
    )

    (SITE_DIR / "sitemap.xml").write_text(sitemap, encoding="utf-8")
    print(f"Built sitemap.xml ({len(urls)} URLs)", file=sys.stderr)


# ==================== Robots.txt ====================

def _build_robots_txt():
    """Generate robots.txt."""
    content = (
        "User-agent: *\n"
        "Allow: /\n"
        f"\nSitemap: {BASE_URL}/sitemap.xml\n"
    )
    (SITE_DIR / "robots.txt").write_text(content, encoding="utf-8")
    print("Built robots.txt", file=sys.stderr)
