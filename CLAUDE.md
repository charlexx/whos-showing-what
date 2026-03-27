# CLAUDE.md — Radar — Forme Femine

## What this is
A curated exhibition tracker for African artists showing worldwide.
Part of the Forme Femine ecosystem. Static site + Python CLI. No backend framework.

## Architecture
- Data: JSON files in data/ (exhibitions.json, artists.json, venues.json)
- CLI: Python, entry point is cli/wsw.py
- Site: vanilla HTML/CSS/JS in site/, no frameworks
- Build: CLI generates site/js/site-data.js from JSON sources
- Deploy: Cloudflare Pages from site/ directory

## Hard rules
- Straight quotes only in all JSON and code (no curly/smart quotes)
- All IDs are slugified with prefixes: exh-, art-, ven-
- No backend server, no database, no ORM, no framework
- site-data.js is GENERATED — never edit it directly
- Footer reads "Radar by Forme Femine" with Forme Femine linked to formefemine.com, plus copyright year below
- Dark mode is the default
- All filtering is client-side

## ID format
- Exhibitions: exh-{venue-slug}-{artist-or-title-slug}-{year} e.g. exh-tate-modern-el-anatsui-2026
- Artists: art-{name-slug} e.g. art-el-anatsui
- Venues: ven-{name-slug} e.g. ven-tate-modern

## Data schemas

### Exhibition (data/exhibitions.json)
Required fields: id, title, artist_ids (array of art- IDs), venue_id (ven- ID), city, country, region, start_date (YYYY-MM-DD), end_date (YYYY-MM-DD), type, admission, mediums (array), focus, source, added_date, status
Optional fields: description, url, image_url
type values: solo | group | fair | biennial | residency | screening | performance
focus values: dedicated | significant | featured
  dedicated = exhibition is specifically about African artists/art
  significant = African artists are a major presence but not exclusively African
  featured = one or more African artists included in a broader show
admission values: free | paid | donation | rsvp
status values: upcoming | current | past
source values: manual | submission | scrape | api
region values: West Africa | East Africa | Southern Africa | North Africa | Central Africa | Europe | North America | South America | Caribbean | Middle East | Asia | Oceania

### Artist (data/artists.json)
Required fields: id, name, origin_country, origin_region, mediums (array)
Optional fields: based_in (array [city, country]), is_diaspora (boolean, default false), birth_year, website, notes
origin_region values: West Africa | East Africa | Southern Africa | North Africa | Central Africa

### Venue (data/venues.json)
Required fields: id, name, city, country, type
Optional fields: website, notes
type values: gallery | museum | institution | project-space | fair | biennial-venue | artist-run | university | online

## CLI namespace
Entry point: python cli/wsw.py
Commands: exhibition, artist, venue, build, stats, validate, refresh

## Colours
Background: #0a0a0a
Surface/cards: #141414
Border: #1e1e1e
Text primary: #e8e4df
Text secondary: #8a8580
Accent: #c9a87c (warm gold — Forme Feminine palette)
Accent hover: #d4b88a
Status current: #4a9e6e
Status upcoming: #5b8dd4
Status past: #6b6560

## Commit discipline
Run `python cli/wsw.py validate` before every commit.
