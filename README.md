# Who's Showing What

**A curated tracker of exhibitions worldwide featuring African artists.**

## What is this?

Who's Showing What is a lightweight exhibition tracker that catalogues solo shows, group exhibitions, biennials, fairs, and more featuring African and African diaspora artists across the globe. Data is managed via a Python CLI and published as a static site.

## Who is it for?

- Curators researching African artists on the international circuit
- Collectors tracking exhibition histories
- Students and researchers studying contemporary African art
- Art tourists planning gallery visits worldwide

## CLI Usage

```bash
python cli/wsw.py <command> [options]
```

| Command      | Description                              |
|--------------|------------------------------------------|
| `exhibition` | Add, list, edit, remove exhibitions      |
| `artist`     | Add, list, search, edit, remove artists  |
| `venue`      | Add, list, edit, remove venues           |
| `build`      | Generate static site from data           |
| `stats`      | Print summary statistics                 |
| `validate`   | Check data integrity                     |
| `refresh`    | Validate + build in one step             |

## Tech Stack

- **Data management**: Python CLI (stdlib only, no external packages)
- **Frontend**: Vanilla HTML, CSS, and JavaScript
- **Hosting**: Cloudflare Pages (from `site/` directory)
- **Data format**: JSON files in `data/`

## Project Structure

```
cli/
  wsw.py              # CLI entry point
  commands/            # Subcommand modules
  utils/               # Shared utilities (IDs, dates)
data/
  exhibitions.json     # Exhibition records
  artists.json         # Artist records
  venues.json          # Venue records
site/
  index.html           # Static site
  css/styles.css
  js/app.js
  js/site-data.js      # Generated — do not edit
scripts/
  health-check.sh      # Run validation
```

## Requirements

- Python 3.10+
- No external dependencies

---

Built by Charlene Chikezie
