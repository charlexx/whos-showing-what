"""ID generation utilities using slugified names."""

import re
import unicodedata


def slugify(text):
    """Lowercase, replace spaces with hyphens, strip non-alphanumeric (except hyphens)."""
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    return text.strip("-")


def make_id(prefix, *parts):
    """Join slugified parts with hyphens and prepend prefix.

    Example: make_id("exh", "Tate Modern", "El Anatsui", "2026")
             -> "exh-tate-modern-el-anatsui-2026"
    """
    slugs = [slugify(str(p)) for p in parts]
    return prefix + "-" + "-".join(slugs)


def make_artist_id(name):
    """Generate artist ID: art-{name-slug}."""
    return make_id("art", name)


def make_venue_id(name):
    """Generate venue ID: ven-{name-slug}."""
    return make_id("ven", name)


def make_exhibition_id(venue_slug, artist_or_title_slug, year):
    """Generate exhibition ID: exh-{venue-slug}-{artist-or-title-slug}-{year}."""
    return make_id("exh", venue_slug, artist_or_title_slug, year)


def id_exists(data, target_id):
    """Check if an ID already exists in a data list."""
    return any(entry["id"] == target_id for entry in data)
