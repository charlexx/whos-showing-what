#!/usr/bin/env python3
"""Who's Showing What — CLI entry point."""

import argparse
import sys

from commands import exhibition, artist, venue, build, stats, validate


BANNER = """
  Who's Showing What — CLI
  A curated tracker of exhibitions featuring African artists.
"""


def refresh(args):
    """Run validate + build in sequence."""
    val_exit = validate.run_validate(args)
    if val_exit != 0:
        return val_exit
    return build.run_build(args)


def main():
    parser = argparse.ArgumentParser(
        prog="wsw",
        description="Who's Showing What — Exhibition tracker for African artists showing worldwide",
    )
    subparsers = parser.add_subparsers(dest="command")

    exhibition.register(subparsers)
    artist.register(subparsers)
    venue.register(subparsers)
    build.register(subparsers)
    stats.register(subparsers)
    validate.register(subparsers)

    # refresh = validate + build
    refresh_p = subparsers.add_parser("refresh", help="Validate data then build site")
    refresh_p.set_defaults(func=refresh)

    args = parser.parse_args()

    if args.command is None:
        print(BANNER, file=sys.stderr)
        parser.print_help(sys.stderr)
        sys.exit(0)

    try:
        exit_code = args.func(args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    sys.exit(exit_code or 0)


if __name__ == "__main__":
    main()
