#!/usr/bin/env python3
"""
Render data/contributions.json (produced by fetch_contributions.py) as a proper
GitHub-style contribution heatmap SVG: a grid of rounded, colored boxes in the
classic 53-week x 7-day calendar layout, revealed once with a diagonal
line-after-line slide-down animation (CSS keyframes, plays on load then
freezes -- no looping), a Less->More legend, and a real stats footer.

Run by .github/workflows/update-profile-art.yml after fetch_contributions.py.
"""
import datetime
import json
import os

HERE = os.path.dirname(__file__)
IN_PATH  = os.path.join(HERE, "..", "data", "contributions.json")
OUT_PATH = os.path.join(HERE, "..", "contrib-heatmap.svg")

# GitHub-ish green ramp: empty -> brightest (level 5 is a neon top end)
PALETTE = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353", "#69f0a0"]

CELL         = 12
GAP          = 3
STEP         = CELL + GAP
PAD          = 22
LEFT_LABEL_W = 30
TOP_LABEL_H  = 20
TITLEBAR_H   = 30

BG     = "#0a0e14"
BG2    = "#0d1420"
FRAME  = "#1f6feb"
MUTED  = "#7d8590"
TEXT   = "#e6edf3"
ACCENT = "#22d3ee"
GREEN  = "#39d353"
GOLD   = "#f2cc60"

# Reveal timing (one-shot diagonal sweep)
COL_T    = 0.018   # per-column delay (left -> right sweep)
ROW_T    = 0.045   # per-row delay    (top  -> bottom cascade)
CELL_DUR = 0.42


def level_for(count):
    if count == 0: return 0
    if count <= 5:  return 1
    if count <= 15: return 2
    if count <= 30: return 3
    if count <= 50: return 4
    return 5


def build_grid(days):
    """Arrange days into weekly columns (Sun=0 … Sat=6)."""
    first    = datetime.date.fromisoformat(days[0]["date"])
    lead_pad = (first.weekday() + 1) % 7   # Sunday=0
    grid = []
    col  = [None] * lead_pad
    for d in days:
        date    = datetime.date.fromisoformat(d["date"])
        weekday = (date.weekday() + 1) % 7
        while len(col) < weekday:
            col.append(None)
        col.append((d["date"], d["count"], level_for(d["count"])))
        if len(col) == 7:
            grid.append(col)
            col = []
    if col:
        while len(col) < 7:
            col.append(None)
        grid.append(col)
    return grid


def month_label_positions(grid):
    seen, labels = set(), []
    for ci, column in enumerate(grid):
        for cell in column:
            if cell is None:
                continue
            date = datetime.date.fromisoformat(cell[0])
            key  = (date.year, date.month)
            if key not in seen and date.day <= 7:
                seen.add(key)
                labels.append((ci, date.strftime("%b")))
            break
    return labels


def render(data):
    days   = data["days"]
    grid   = build_grid(days)
    n_cols = len(grid)
    art_w  = n_cols * STEP
    art_h  = 7 * STEP

    month_labels = month_label_positions(grid)

    canvas_w = PAD + LEFT_LABEL_W + art_w + PAD
    stats_h  = 88
    canvas_h = TITLEBAR_H + TOP_LABEL_H + art_h + stats_h + PAD

    # ── CSS ────────────────────────────────────────────────────────────────
    css = """\
@keyframes cell {
  0%   { opacity: 0; transform: translateY(-6px); }
  60%  { opacity: 1; }
  100% { opacity: 1; transform: translateY(0);    }
}
text { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
"""

    lines = []
    lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{canvas_w}" height="{canvas_h}" role="img" aria-label="Contribution heatmap">')
    lines.append(f'<style>{css}</style>')

    # ── Background ─────────────────────────────────────────────────────────
    lines.append(f'<rect width="{canvas_w}" height="{canvas_h}" rx="10" fill="{BG}"/>')

    # ── Title bar ──────────────────────────────────────────────────────────
    lines.append(f'<rect width="{canvas_w}" height="{TITLEBAR_H}" rx="10" fill="{BG2}"/>')
    lines.append(f'<rect y="{TITLEBAR_H - 1}" width="{canvas_w}" height="1" fill="{FRAME}" opacity=".35"/>')
    # traffic-light dots
    for i, col in enumerate(["#ff5f57", "#ffbd2e", "#28c841"]):
        lines.append(f'<circle cx="{14 + i * 18}" cy="{TITLEBAR_H // 2}" r="5" fill="{col}"/>')
    title_txt = "AdityaTiwari64 — contribution graph"
    lines.append(f'<text x="{canvas_w // 2}" y="{TITLEBAR_H // 2 + 5}" text-anchor="middle" font-size="11" fill="{MUTED}">{title_txt}</text>')

    # ── Day-of-week labels ─────────────────────────────────────────────────
    day_names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    art_x0    = PAD + LEFT_LABEL_W
    art_y0    = TITLEBAR_H + TOP_LABEL_H
    for ri, name in enumerate(day_names):
        if ri % 2 == 1:   # only Mon, Wed, Fri to avoid crowding
            y = art_y0 + ri * STEP + CELL // 2 + 4
            lines.append(f'<text x="{art_x0 - 6}" y="{y}" text-anchor="end" font-size="9" fill="{MUTED}">{name}</text>')

    # ── Month labels ───────────────────────────────────────────────────────
    for ci, label in month_labels:
        x = art_x0 + ci * STEP
        y = TITLEBAR_H + TOP_LABEL_H - 5
        lines.append(f'<text x="{x}" y="{y}" font-size="10" fill="{MUTED}">{label}</text>')

    # ── Cells ──────────────────────────────────────────────────────────────
    for ci, column in enumerate(grid):
        for ri, cell in enumerate(column):
            x = art_x0 + ci * STEP
            y = art_y0 + ri * STEP
            color = PALETTE[cell[2]] if cell else PALETTE[0]
            delay = ci * COL_T + ri * ROW_T
            anim  = (f'style="animation:cell {CELL_DUR:.2f}s ease both;'
                     f'animation-delay:{delay:.3f}s" ')
            tip = ""
            if cell:
                date_str  = cell[0]
                cnt       = cell[1]
                tip_label = f"{cnt} contribution{'s' if cnt != 1 else ''} on {date_str}"
                tip = f'<title>{tip_label}</title>'
            lines.append(
                f'<rect {anim}x="{x}" y="{y}" width="{CELL}" height="{CELL}" '
                f'rx="2" fill="{color}">{tip}</rect>'
            )

    # ── Stats footer ───────────────────────────────────────────────────────
    total   = data.get("total", 0)
    c_str   = data.get("current_streak", 0)
    l_str   = data.get("longest_streak", 0)
    best    = data.get("best_day", {})
    best_ct = best.get("count", 0)
    best_dt = best.get("date", "")

    footer_y = art_y0 + art_h + 16
    sep      = f'  ·  '

    stats_line1 = f"{total:,} contributions in the last year"
    stats_line2 = (f"Current streak: {c_str} days"
                   f"{sep}Longest streak: {l_str} days"
                   f"{sep}Best day: {best_ct} ({best_dt})")

    lines.append(f'<text x="{canvas_w // 2}" y="{footer_y}" text-anchor="middle" font-size="12" font-weight="600" fill="{GREEN}">{stats_line1}</text>')
    lines.append(f'<text x="{canvas_w // 2}" y="{footer_y + 18}" text-anchor="middle" font-size="10" fill="{MUTED}">{stats_line2}</text>')

    # ── Less->More legend ──────────────────────────────────────────────────
    legend_y  = footer_y + 40
    legend_x0 = canvas_w // 2 - (len(PALETTE) * (CELL + 4) + 60) // 2
    lines.append(f'<text x="{legend_x0}" y="{legend_y + CELL - 1}" font-size="9" fill="{MUTED}">Less</text>')
    for li, color in enumerate(PALETTE):
        lx = legend_x0 + 30 + li * (CELL + 4)
        lines.append(f'<rect x="{lx}" y="{legend_y}" width="{CELL}" height="{CELL}" rx="2" fill="{color}"/>')
    more_x = legend_x0 + 30 + len(PALETTE) * (CELL + 4) + 2
    lines.append(f'<text x="{more_x}" y="{legend_y + CELL - 1}" font-size="9" fill="{MUTED}">More</text>')

    lines.append("</svg>")
    return "\n".join(lines)


def main():
    with open(IN_PATH, encoding="utf-8") as f:
        data = json.load(f)

    svg = render(data)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"Written {OUT_PATH}")


if __name__ == "__main__":
    main()
