#!/usr/bin/env python3
"""
Build a neofetch-style info card SVG to sit to the RIGHT of the ASCII portrait:
colored key/value rows for work experience, tech stack, and highlights.

Static content — hand-author the ROWS list below to match your real details.
Lines fade and slide in on a short stagger so the panel feels like it is
printing alongside the portrait. STATIC=1 emits the frozen state for previews.

    python scripts/make_info_card.py        # writes info-card.svg
    STATIC=1 python scripts/make_info_card.py
"""
import html
import os

HERE   = os.path.dirname(os.path.abspath(__file__))
OUT    = os.path.join(HERE, "..", "info-card.svg")
STATIC = bool(os.environ.get("STATIC"))

W, H       = 480, 400
PAD        = 20
TITLEBAR_H = 30
KEY_X      = PAD
VAL_X      = PAD + 100
LINE_H     = 20.5

BG      = "#0d1117"
BG2     = "#111722"
FRAME   = "#30363d"
MUTED   = "#7d8590"
INK     = "#c9d1d9"
KEY     = "#ffa657"      # orange keys
SECTION = "#58a6ff"      # blue section headers
GREEN   = "#3fb950"
ACCENT  = "#22d3ee"

# ── Content — edit this to match your details ────────────────────────────────
# Row types:
#   ("host",)          →  "aditya@github" title + underline rule
#   ("kv", key, val)   →  orange key + light value
#   ("sec", title)     →  blue "─── title ───" rule
#   ("bul", text)      →  green dot + light text
#   ("gap",)           →  vertical space
ROWS = [
    ("host",),
    ("kv", "Now",      "Student + Open Source Developer"),
    ("kv", "Prev",     "Intern @ Tech Mahindra"),
    ("kv", "Location", "India"),
    ("kv", "Edu",      "Computer Science"),
    ("gap",),
    ("sec", "Stack"),
    ("kv", "Languages", "Python, JavaScript, TypeScript"),
    ("kv", "Frontend",  "React, Next.js, HTML/CSS"),
    ("kv", "Backend",   "Node.js, FastAPI, Django"),
    ("kv", "Tools",     "Git, Docker, Linux"),
    ("gap",),
    ("sec", "Highlights"),
    ("bul", "Building in public on GitHub"),
    ("bul", "Passionate about automation & tooling"),
    ("bul", "Always learning something new"),
]
# ─────────────────────────────────────────────────────────────────────────────


def esc(s: str) -> str:
    return html.escape(s)


def rise(inner: str, i: int) -> str:
    """Wrap element in a fade+slide animation, staggered by row index."""
    if STATIC:
        return f"<g>{inner}</g>"
    delay = 0.15 + i * 0.06
    dur   = 0.35
    return (
        f'<g opacity="0" transform="translate(0,5)">'
        f'{inner}'
        f'<animate attributeName="opacity" from="0" to="1" '
        f'begin="{delay:.2f}s" dur="{dur:.2f}s" fill="freeze"/>'
        f'<animateTransform attributeName="transform" type="translate" '
        f'from="0,5" to="0,0" begin="{delay:.2f}s" dur="{dur:.2f}s" fill="freeze"/>'
        f'</g>'
    )


def render_row(row_type, args, y, idx):
    """Return SVG markup for a single row."""
    if row_type == "host":
        handle = "aditya@github"
        inner  = (
            f'<text x="{KEY_X}" y="{y}" font-size="13" font-weight="bold" fill="{ACCENT}">'
            f'{esc(handle)}</text>'
            f'<line x1="{KEY_X}" y1="{y + 4}" x2="{W - PAD}" y2="{y + 4}" '
            f'stroke="{FRAME}" stroke-width="1"/>'
        )
        return rise(inner, idx), LINE_H + 8

    elif row_type == "kv":
        key, val = args
        inner = (
            f'<text x="{KEY_X}" y="{y}" font-size="11" fill="{KEY}">{esc(key)}</text>'
            f'<text x="{VAL_X}" y="{y}" font-size="11" fill="{INK}">{esc(val)}</text>'
        )
        return rise(inner, idx), LINE_H

    elif row_type == "sec":
        title = args[0]
        mid   = W // 2
        inner = (
            f'<text x="{mid}" y="{y}" text-anchor="middle" font-size="11" '
            f'font-weight="bold" fill="{SECTION}">─── {esc(title)} ───</text>'
        )
        return rise(inner, idx), LINE_H

    elif row_type == "bul":
        text  = args[0]
        dot_x = KEY_X + 4
        txt_x = KEY_X + 14
        inner = (
            f'<circle cx="{dot_x}" cy="{y - 4}" r="3" fill="{GREEN}"/>'
            f'<text x="{txt_x}" y="{y}" font-size="11" fill="{INK}">{esc(text)}</text>'
        )
        return rise(inner, idx), LINE_H

    elif row_type == "gap":
        return "", LINE_H * 0.55

    return "", 0


def main():
    parts = []

    # ── Background + titlebar ─────────────────────────────────────────────
    parts.append(f'<rect width="{W}" height="{H}" rx="10" fill="{BG}"/>')
    parts.append(f'<rect width="{W}" height="{TITLEBAR_H}" rx="10" fill="{BG2}"/>')
    parts.append(f'<rect y="{TITLEBAR_H - 1}" width="{W}" height="1" fill="{FRAME}" opacity=".35"/>')

    # traffic-light dots
    for i, col in enumerate(["#ff5f57", "#ffbd2e", "#28c841"]):
        parts.append(f'<circle cx="{14 + i * 18}" cy="{TITLEBAR_H // 2}" r="5" fill="{col}"/>')

    # title text
    parts.append(
        f'<text x="{W // 2}" y="{TITLEBAR_H // 2 + 5}" text-anchor="middle" '
        f'font-size="11" fill="{MUTED}" '
        f'font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace">'
        f'~/profile/info-card.sh</text>'
    )

    # ── Rows ──────────────────────────────────────────────────────────────
    y   = float(TITLEBAR_H + PAD + 12)
    idx = 0
    for row in ROWS:
        row_type = row[0]
        args     = row[1:]
        markup, advance = render_row(row_type, args, y, idx)
        if markup:
            parts.append(markup)
            idx += 1
        y += advance

    # ── Status bar ────────────────────────────────────────────────────────
    bar_y = H - 22
    parts.append(f'<rect y="{bar_y}" width="{W}" height="22" rx="0" fill="{BG2}" opacity=".8"/>')
    parts.append(
        f'<text x="{PAD}" y="{bar_y + 14}" font-size="9" fill="{MUTED}" '
        f'font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace">'
        f'AdityaTiwari64 · github.com/AdityaTiwari64</text>'
    )

    # ── Assemble SVG ──────────────────────────────────────────────────────
    mono = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'role="img" aria-label="Aditya Tiwari info card">\n'
        f'<style>text{{font-family:{mono};}}</style>\n'
        + "\n".join(parts)
        + "\n</svg>"
    )

    with open(OUT, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"Written {OUT}")


if __name__ == "__main__":
    main()
