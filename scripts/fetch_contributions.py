#!/usr/bin/env python3
"""
Scrape real daily contribution counts from GitHub's public, unauthenticated
contributions endpoint (the same fragment the profile page itself uses) and
write data/contributions.json with the raw days plus derived stats
(current streak, longest streak, best day, monthly totals).

No token, no auth, no GraphQL -- just the public HTML GitHub already serves.
Run daily by .github/workflows/update-profile-art.yml.
"""
import datetime
import json
import os
import re
import sys

import requests
from bs4 import BeautifulSoup

USERNAME = os.environ.get("GH_PROFILE_USER", "AdityaTiwari64")
URL = f"https://github.com/users/{USERNAME}/contributions"
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "contributions.json")


def fetch_days():
    """Fetch contribution calendar cells from GitHub's public HTML endpoint."""
    resp = requests.get(URL, headers={"User-Agent": "profile-readme-bot/1.0"}, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    cells = soup.select("td.ContributionCalendar-day")
    if not cells:
        print("no calendar cells found -- github markup may have changed", file=sys.stderr)
        sys.exit(1)

    days = []
    for td in cells:
        date = td.get("data-date")
        if not date:
            continue
        td_id = td.get("id")
        tooltip_el = soup.find("tool-tip", attrs={"for": td_id}) if td_id else None
        text = tooltip_el.get_text(strip=True) if tooltip_el else ""
        if re.search(r"no contributions", text, re.I):
            count = 0
        else:
            m = re.match(r"(\d+)", text)
            count = int(m.group(1)) if m else 0
        days.append({"date": date, "count": count})

    days.sort(key=lambda d: d["date"])
    return days


def compute_current_streak(days):
    """Walk backwards from today/yesterday to find the active streak length."""
    today = datetime.date.today().isoformat()
    streak = 0
    started = False
    for d in reversed(days):
        if not started:
            # allow today to have 0 (day isn't over yet) — start from yesterday
            if d["date"] == today:
                if d["count"] > 0:
                    streak = 1
                    started = True
                continue
            if d["count"] > 0:
                streak = 1
                started = True
                continue
            else:
                break
        else:
            if d["count"] > 0:
                streak += 1
            else:
                break
    return streak


def compute_longest_streak(days):
    """Find the longest run of consecutive days with count > 0."""
    longest = 0
    current = 0
    for d in days:
        if d["count"] > 0:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def compute_best_day(days):
    """Find the single day with the highest contribution count."""
    best = max(days, key=lambda d: d["count"])
    return {"date": best["date"], "count": best["count"]}


def compute_monthly_totals(days):
    """Aggregate contribution counts by calendar month."""
    months = {}
    for d in days:
        key = d["date"][:7]  # "YYYY-MM"
        months[key] = months.get(key, 0) + d["count"]
    return months


def main():
    print(f"Fetching contributions for {USERNAME}...")
    days = fetch_days()
    total = sum(d["count"] for d in days)

    data = {
        "username": USERNAME,
        "fetched_at": datetime.datetime.utcnow().isoformat() + "Z",
        "total": total,
        "days": days,
        "current_streak": compute_current_streak(days),
        "longest_streak": compute_longest_streak(days),
        "best_day": compute_best_day(days),
        "monthly_totals": compute_monthly_totals(days),
    }

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"  {len(days)} days, {total:,} total contributions")
    print(f"  current streak: {data['current_streak']} days")
    print(f"  longest streak: {data['longest_streak']} days")
    print(f"  best day: {data['best_day']['date']} ({data['best_day']['count']})")
    print(f"  written to {OUT_PATH}")


if __name__ == "__main__":
    main()
