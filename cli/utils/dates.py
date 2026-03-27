"""Date handling utilities."""

import re
from datetime import date

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

MONTHS = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]

MONTHS_LONG = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def is_valid_date(date_str):
    """Check if a string is a valid YYYY-MM-DD date."""
    if not DATE_RE.match(date_str):
        return False
    try:
        parse_date(date_str)
        return True
    except ValueError:
        return False


def parse_date(date_str):
    """Parse a YYYY-MM-DD string into a date object."""
    year, month, day = map(int, date_str.split("-"))
    return date(year, month, day)


def format_date(date_str):
    """Return human-readable format like '15 Feb 2026'."""
    d = parse_date(date_str)
    return f"{d.day} {MONTHS[d.month - 1]} {d.year}"


def format_date_long(date_str):
    """Return human-readable format like '8 October 2025'."""
    d = parse_date(date_str)
    return f"{d.day} {MONTHS_LONG[d.month - 1]} {d.year}"


def validate_date_range(start_str, end_str):
    """Return True if start_date <= end_date."""
    return parse_date(start_str) <= parse_date(end_str)


def get_status(start_date, end_date):
    """Return 'upcoming', 'current', or 'past' based on today's date."""
    today = date.today()
    start = parse_date(start_date)
    end = parse_date(end_date)
    if today < start:
        return "upcoming"
    elif today > end:
        return "past"
    else:
        return "current"


def today_str():
    """Return today's date as YYYY-MM-DD."""
    return date.today().isoformat()
