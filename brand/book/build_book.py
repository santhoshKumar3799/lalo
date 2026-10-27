"""Builds the LALO brand book as one SVG per page, then a FigCraft script that imports them.

Run:  python -I build_book.py
Then: figcraft-cli run out/import.json --out LALO-brand-book.figcraft
"""
import base64
import json
import os
import re
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")
OUT = os.path.join(HERE, "out")

W, H = 1920, 1080
M = 96  # outer margin

GREEN = "#204D36"
GREEN_DK = "#173A28"
CREAM = "#FEEED0"
WHITE = "#FFFFFF"
BLUE = "#02389A"
BEIGE = "#EFE8DE"
INK = "#1A1A1A"
MUTED = "#6B6B66"

HEAD = "Poppins"
BODY = "Inter"


# ---------- assets ----------

def _inner(name):
    """Logo SVG body without the export's background rects, plus its size."""
    src = open(os.path.join(ASSETS, name), encoding="utf-8").read()
    w, h = re.search(r'<svg width="([\d.]+)" height="([\d.]+)"', src).groups()
    body = src[src.index('<g id="Frame 1">'):src.rindex("</svg>")]
    body = re.sub(r'<rect width="1138" height="1920"[^>]*/>', "", body)
    body = re.sub(r'\sid="[^"]*"', "", body)
    return body, float(w), float(h)


WORDMARK = _inner("wordmark.svg")
TAGLINE = _inner("tagline.svg")
MARK = _inner("mark.svg")
TAG_DX, TAG_DY = 56.4, 221.2  # tagline position under the wordmark in the original lockup
LOCKUP_W, LOCKUP_H = 357.0, TAG_DY + 12


def _paint(body, fg, bg):
    return body.replace('fill="#204D36"', f'fill="{fg}"').replace('fill="white"', f'fill="{bg}"')


def wordmark(x, y, width, fg, bg, name="LALO wordmark"):
    body, w, _ = WORDMARK
    s = width / w
    return f'<g id="{name}" transform="translate({x:.1f} {y:.1f}) scale({s:.4f})">{_paint(body, fg, bg)}</g>'


def lockup(x, y, width, fg, bg, name="LALO logo"):
    s = width / LOCKUP_W
    wbody, _, _ = WORDMARK
    tbody, _, _ = TAGLINE
    return (f'<g id="{name}" transform="translate({x:.1f} {y:.1f}) scale({s:.4f})">'
            f'{_paint(wbody, fg, bg)}'
            f'<g transform="translate({TAG_DX} {TAG_DY})">{_paint(tbody, fg, bg)}</g></g>')


def mark(x, y, height, fg, bg, name="Steam mark", rotate=0):
    body, w, h = MARK
    s = height / h
    rot = f" rotate({rotate} {w / 2:.1f} {h / 2:.1f})" if rotate else ""
    return f'<g id="{name}" transform="translate({x:.1f} {y:.1f}) scale({s:.4f}){rot}">{_paint(body, fg, bg)}</g>'


def image(path, x, y, w, h, name, r=0):
    data = base64.b64encode(open(os.path.join(ASSETS, path), "rb").read()).decode()
    cid = re.sub(r"\W", "", name) + "Clip"
    clip = (f'<clipPath id="{cid}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}"/></clipPath>')
    return (f'<defs>{clip}</defs><g id="{name}" clip-path="url(#{cid})">'
            f'<image x="{x}" y="{y}" width="{w}" height="{h}" preserveAspectRatio="xMidYMid slice" '
            f'href="data:image/png;base64,{data}"/></g>')


# ---------- primitives ----------

def rect(x, y, w, h, fill, r=0, name=None, stroke=None, sw=1, dash=None):
    n = f' id="{name}"' if name else ""
    s = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<rect{n} x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}"{s}{d}/>'


def circle(cx, cy, r, fill, stroke=None, sw=1, name=None):
    n = f' id="{name}"' if name else ""
    s = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    return f'<circle{n} cx="{cx}" cy="{cy}" r="{r}" fill="{fill}"{s}/>'


def line(x1, y1, x2, y2, color, sw=1, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{sw}"{d}/>'


def wrap(text, size, width, font=BODY):
    """Greedy line breaking with an average glyph width per font."""
    avg = 0.56 if font == HEAD else 0.53
    per_line = max(1, int(width / (size * avg)))
    lines = []
    for para in text.split("\n"):
        cur = ""
        for word in para.split(" "):
            trial = (cur + " " + word).strip()
            if len(trial) > per_line and cur:
                lines.append(cur)
                cur = word
            else:
                cur = trial
        lines.append(cur)
    return lines


def text(x, y, s, size, color, font=BODY, weight=400, width=None, lh=1.35, ls=0, anchor="start", name=None):
    lines = wrap(s, size, width, font) if width else s.split("\n")
    n = f' id="{escape(name)}"' if name else ""
    spans = "".join(
        f'<tspan x="{x}" y="{y + i * size * lh:.1f}">{escape(t)}</tspan>' for i, t in enumerate(lines))
    return (f'<text{n} font-family="{font}" font-size="{size}" font-weight="{weight}" fill="{color}" '
            f'letter-spacing="{ls}" text-anchor="{anchor}">{spans}</text>')


def head(x, y, s, size, color, **kw):
    return text(x, y, s, size, color, font=HEAD, weight=700, lh=kw.pop("lh", 1.0), **kw)


def label(x, y, s, color, size=15, anchor="start"):
    return text(x, y, s.upper(), size, color, font=HEAD, weight=400, ls=size * 0.18, anchor=anchor)


def spark(x, y, s, color, sw=None):
    """The three-line spark from the logo, as a stroked accent."""
    sw = sw or s * 0.11
    rays = [(-0.42, -0.95, -0.22, -0.5), (0.02, -1.0, 0.02, -0.52), (0.46, -0.9, 0.24, -0.46)]
    return "".join(
        f'<line x1="{x + a * s:.1f}" y1="{y + b * s:.1f}" x2="{x + c * s:.1f}" y2="{y + d * s:.1f}" '
        f'stroke="{color}" stroke-width="{sw:.1f}" stroke-linecap="round"/>' for a, b, c, d in rays)


def check(cx, cy, ok, color, tick=WHITE):
    if ok:
        p = f"M{cx - 9} {cy} L{cx - 2} {cy + 7} L{cx + 10} {cy - 7}"
    else:
        p = f"M{cx - 8} {cy - 8} L{cx + 8} {cy + 8} M{cx + 8} {cy - 8} L{cx - 8} {cy + 8}"
    return (circle(cx, cy, 20, color) +
            f'<path d="{p}" stroke="{tick}" stroke-width="3.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>')


def chrome(num, section, fg, rule=None):
    """Running header and footer used on every inside page."""
    rule = rule or fg
    return (label(M, 70, "LALO — Brand Guidelines", fg, 13) +
            label(W - M, 70, "Vol. 01 · 2026", fg, 13, anchor="end") +
            line(M, 92, W - M, 92, rule, 1) +
            line(M, H - 78, W - M, H - 78, rule, 1) +
            label(M, H - 46, section, fg, 13) +
            label(W - M, H - 46, f"{num:02d}", fg, 13, anchor="end"))


def page(name, bg, *parts):
    return name, (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
                  f'<rect id="Background" width="{W}" height="{H}" fill="{bg}"/>' + "".join(parts) + "</svg>")


def tint_dark(hex_color, amount=0.82):
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return "#{:02X}{:02X}{:02X}".format(round(r * amount), round(g * amount), round(b * amount))


def tint(hex_color, amount):
    """Mix a colour with white: amount 1 = the colour, 0 = white."""
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    mix = lambda c: round(255 - (255 - c) * amount)
    return "#{:02X}{:02X}{:02X}".format(mix(r), mix(g), mix(b))


# ---------- pages ----------

def p_cover():
    return page(
        "01 Cover", GREEN,
        *[mark(1500 + (i % 3) * 120, 130 + (i // 3) * 150, 110, GREEN_DK, GREEN, f"Pattern mark {i}", rotate=-12)
          for i in range(9)],
        label(M, 132, "Brand Guidelines", CREAM, 18),
        label(M, 162, "Volume 01 · October 2026", CREAM, 14),
        wordmark(M - 10, 300, 1180, CREAM, GREEN, "Hero wordmark"),
        line(M, H - 150, W - M, H - 150, CREAM, 1.5),
        label(M, H - 100, "Buns & Brews", CREAM, 22),
        text(W - M, H - 100, "Coffee and bun shop · Identity system", 20, CREAM, anchor="end"),
    )


CHAPTERS = [
    ("01", "The Brand", "Story, personality and voice", 3),
    ("02", "Logo", "Wordmark, versions, clear space, misuse", 6),
    ("03", "Brand Mark", "The steam swirl and app icons", 11),
    ("04", "Colour & Type", "Palette, tints, pairings, typography", 12),
    ("05", "In the World", "Graphics, photography, applications", 16),
]


def p_contents():
    rows = []
    y = 250
    for num, title, sub, pg in CHAPTERS:
        rows += [
            line(820, y - 58, W - M, y - 58, GREEN, 1),
            head(820, y + 20, num, 30, BLUE),
            head(930, y + 22, title, 64, GREEN),
            text(930, y + 70, sub, 20, MUTED),
            head(W - M, y + 22, f"{pg:02d}", 30, GREEN, anchor="end"),
        ]
        y += 150
    return page(
        "02 Contents", CREAM, chrome(2, "Contents", GREEN),
        head(M, 330, "What's\ninside", 150, GREEN, lh=0.95),
        text(M, 590, "Everything you need to make LALO look and sound like LALO — on a cup, a sign or a screen.",
             26, INK, width=560, lh=1.4),
        mark(M, 730, 200, GREEN, CREAM, "Contents mark"),
        spark(M + 210, 760, 70, GREEN),
        *rows,
    )


def chapter(num, title, items, pg, bg, fg, accent, photo=None):
    parts = []
    if photo:
        parts.append(image(photo, 0, 0, W, H, "Chapter photo"))
        parts.append(f'<rect id="Overlay" width="{W}" height="{H}" fill="{bg}" opacity="0.82"/>')
    if not photo:
        parts.append(mark(W - 560, 360, 760, tint_dark(bg), bg, "Chapter texture", rotate=-10))
    parts += [
        chrome(pg, f"Chapter {num}", fg),
        head(M - 20, 760, num, 620, accent, ls=-30, name="Chapter number"),
        head(1060, 360, title, 120, fg, width=760, lh=0.95),
    ]
    y = 560
    for it in items:
        parts += [circle(1072, y - 8, 7, accent), text(1100, y, it, 26, fg)]
        y += 52
    return page(f"{pg:02d} Chapter {num} {title}", bg, *parts)


def p_story():
    cards = [
        (M, 150, 860, 400, GREEN, CREAM, "Mission",
         "Make every day a little warmer with buns baked fresh each morning and coffee brewed with care."),
        (M + 890, 150, 838, 400, BLUE, WHITE, "Vision",
         "Be the neighbourhood's favourite pause — the place people choose when they want comfort and a smile."),
    ]
    parts = [chrome(4, "01 · The Brand", GREEN)]
    for x, y, w, h, bg, fg, ttl, body in cards:
        parts += [rect(x, y + 10, w, h, bg, 36, f"{ttl} card"),
                  label(x + 48, y + 80, ttl, fg, 16),
                  head(x + 48, y + 180, body, 44, fg, width=w - 100, lh=1.12)]
    values = [("Fresh daily", "Buns baked and coffee brewed fresh, every single day."),
              ("Comfort first", "A cosy place to pause, alone or with friends."),
              ("Simple joy", "Small treats that make an ordinary day better.")]
    x = M
    for i, (t, b) in enumerate(values):
        cx = x + i * 400
        parts += [rect(cx, 590, 380, 380, CREAM, 36, f"Value {i + 1}"),
                  head(cx + 40, 680, f"0{i + 1}", 34, BLUE),
                  head(cx + 40, 790, t, 40, GREEN),
                  text(cx + 40, 850, b, 22, INK, width=300)]
    parts.append(image("photo-sign.png", M + 1220, 600, 508, 370, "Story photo", 36))
    return page("04 Brand story", WHITE, *parts)


def p_personality():
    traits = [("Playful", "not silly"), ("Warm", "not sloppy"), ("Fresh", "not old-fashioned"),
              ("Confident", "not loud")]
    parts = [chrome(5, "01 · The Brand", GREEN),
             head(M, 230, "Personality\n& voice", 96, GREEN, lh=1.0),
             text(M, 450, "We talk like a friendly barista greeting a regular: short sentences, plain words, a little wit.",
                  24, INK, width=620, lh=1.45)]
    y = 640
    for t, n in traits:
        parts += [rect(M, y - 52, 300, 76, GREEN, 38), head(M + 150, y, t, 30, CREAM, anchor="middle"),
                  text(M + 330, y - 2, n, 26, MUTED)]
        y += 96
    bubbles = [(980, 170, 760, CREAM, GREEN, "Warm buns, fresh brews. Come on in.", True),
               (1080, 400, 660, GREEN, CREAM, "Your usual? We saved you a seat.", True),
               (980, 630, 760, BEIGE, MUTED, "Experience our premium artisanal beverage solutions.", False)]
    for x, y, w, bg, fg, s, ok in bubbles:
        parts += [rect(x, y, w, 180, bg, 90), f'<path d="M{x + 120} {y + 170} l-20 50 l70 -50 z" fill="{bg}"/>',
                  head(x + 70, y + 105, f"“{s}”", 34, fg, width=w - 170, lh=1.1),
                  check(x + w - 50, y + 40, ok, (CREAM if bg == GREEN else GREEN) if ok else INK, GREEN if bg == GREEN else WHITE)]
    parts.append(label(980, 905, "Say it like this — not like the last one", MUTED, 14))
    return page("05 Personality and voice", WHITE, *parts)


def p_primary_logo():
    return page(
        "07 Primary logo", CREAM, chrome(7, "02 · Logo", GREEN),
        rect(M, 130, 1100, 820, GREEN, 40, "Logo stage"),
        lockup(M + 190, 300, 720, CREAM, GREEN, "Primary logo"),
        head(1290, 230, "Primary\nlogo", 96, GREEN),
        text(1290, 450, "Hand-lettered LALO with a little spark of steam, sitting on BUNS & BREWS spaced wide. "
                        "Always use the original artwork — never retype or redraw it.", 24, INK, width=520, lh=1.45),
        *[x for i, (k, v) in enumerate([("Wordmark", "Custom rounded lettering"),
                                         ("Spark", "Three rays above the last O"),
                                         ("Tagline", "Wide-spaced capitals")])
          for x in (circle(1306, 700 + i * 80 - 8, 14, BLUE), head(1306, 700 + i * 80 - 1, str(i + 1), 16, WHITE, anchor="middle"),
                    head(1340, 700 + i * 80, k, 24, GREEN), text(1500, 700 + i * 80, v, 20, MUTED))],
        circle(M + 905, 300, 22, BLUE), head(M + 905, 307, "2", 18, WHITE, anchor="middle"),
        circle(M + 160, 420, 22, BLUE), head(M + 160, 427, "1", 18, WHITE, anchor="middle"),
        circle(M + 160, 765, 22, BLUE), head(M + 160, 772, "3", 18, WHITE, anchor="middle"),
    )


def p_variations():
    tiles = [("Primary · reversed", GREEN, CREAM, "Signage, cups, packaging, social"),
             ("Primary · positive", WHITE, GREEN, "Menus, website, receipts, documents"),
             ("Accent", BEIGE, BLUE, "Seasonal items, merch, campaigns"),
             ("One colour", INK, WHITE, "Stamps, embossing, single-colour print")]
    parts = [chrome(8, "02 · Logo", GREEN), head(M, 210, "Logo versions", 80, GREEN)]
    tw, th = 420, 640
    for i, (t, bg, fg, use) in enumerate(tiles):
        x = M + i * (tw + 16)
        stroke = BEIGE if bg == WHITE else None
        parts += [rect(x, 270, tw, th, bg, 32, t, stroke=stroke, sw=2),
                  lockup(x + 60, 470, tw - 120, fg, bg, f"{t} logo"),
                  label(x + 36, 330, t, fg, 14),
                  text(x + 36, 860, use, 19, fg, width=tw - 72)]
    return page("08 Logo versions", WHITE, *parts)


def p_clearspace():
    lx, ly, lw = 300, 450, 460
    s = lw / LOCKUP_W
    lh = LOCKUP_H * s
    xu = 46 * s  # spark height ≈ 1/4 of wordmark height
    parts = [chrome(9, "02 · Logo", GREEN),
             head(M, 210, "Clear space\n& minimum size", 80, GREEN),
             rect(M, 340, 920, 600, BEIGE, 32, "Clear space stage"),
             rect(lx - xu, ly - xu, lw + 2 * xu, lh + 2 * xu, "none", 0, "Clear space box", BLUE, 2, "10 8"),
             lockup(lx, ly, lw, GREEN, BEIGE)]
    for cx, cy in [(lx - xu / 2, ly + lh / 2), (lx + lw + xu / 2, ly + lh / 2), (lx + lw / 2, ly - xu / 2),
                   (lx + lw / 2, ly + lh + xu / 2)]:
        parts += [circle(cx, cy, 20, BLUE), head(cx, cy + 7, "x", 20, WHITE, anchor="middle")]
    parts += [text(M + 40, 900, "x = height of the spark. Keep this space empty on every side.", 20, INK)]
    sizes = [(360, "Print 30 mm · Screen 120 px", "With tagline"),
             (220, "Print 18 mm · Screen 72 px", "Wordmark only"),
             (110, "Print 10 mm · Screen 32 px", "Use the steam mark")]
    y = 380
    parts.append(label(1110, y - 20, "Minimum sizes", GREEN, 15))
    for i, (w, spec, kind) in enumerate(sizes):
        yy = y + 30 + i * 190
        parts.append(line(1110, yy - 10, W - M, yy - 10, BEIGE, 2))
        if i == 0:
            parts.append(lockup(1110, yy + 20, w * 0.62, GREEN, WHITE))
        elif i == 1:
            parts.append(wordmark(1110, yy + 25, w * 0.55, GREEN, WHITE))
        else:
            parts.append(mark(1120, yy + 15, 90, GREEN, WHITE))
        parts += [head(1420, yy + 70, kind, 30, GREEN), text(1420, yy + 112, spec, 20, MUTED)]
    return page("09 Clear space and minimum size", WHITE, *parts)


def p_misuse():
    tw, th = 548, 290
    donts = [("Don't stretch or squash", "stretch"), ("Don't rotate", "rotate"),
             ("Don't use off-palette colours", "colour"), ("Don't use low contrast", "contrast"),
             ("Don't add outlines or effects", "outline"), ("Don't place on busy photos", "photo")]
    parts = [chrome(10, "02 · Logo", GREEN), head(M, 210, "Please don't", 80, GREEN)]
    for i, (t, kind) in enumerate(donts):
        x = M + (i % 3) * (tw + 22)
        y = 250 + (i // 3) * (th + 90)
        bg, fg = (BEIGE, GREEN)
        inner = ""
        lw = 300
        lx, ly = x + (tw - lw) / 2, y + 70
        if kind == "stretch":
            inner = f'<g transform="translate({lx - 40} {ly + 20}) scale(1.35 0.6)">{lockup(0, 0, lw, GREEN, BEIGE)}</g>'
        elif kind == "rotate":
            inner = f'<g transform="rotate(-18 {x + tw / 2} {y + th / 2})">{lockup(lx, ly, lw, GREEN, BEIGE)}</g>'
        elif kind == "colour":
            bg = "#F4B6C2"
            inner = lockup(lx, ly, lw, "#E8572A", bg)
        elif kind == "contrast":
            bg = WHITE
            inner = lockup(lx, ly, lw, CREAM, WHITE)
        elif kind == "outline":
            inner = (f'<g transform="translate(6 6)">{lockup(lx, ly, lw, BLUE, BLUE)}</g>' + lockup(lx, ly, lw, GREEN, BEIGE))
        if kind == "photo":
            parts.append(image("photo-cups-cream.png", x, y, tw, th, f"Misuse photo", 28))
            inner = lockup(lx, ly, lw, GREEN, "#E9E2D6")
        else:
            parts.append(rect(x, y, tw, th, bg, 28, f"Misuse {i + 1}", stroke=BEIGE if bg == WHITE else None, sw=2))
        parts += [inner, check(x + tw - 40, y + 40, False, INK), text(x, y + th + 44, t, 22, INK)]
    return page("10 Logo misuse", WHITE, *parts)


def p_mark():
    parts = [chrome(11, "03 · Brand Mark", GREEN),
             rect(0, 0, 820, H, GREEN, 0, "Mark panel"),
             label(M, 70, "LALO — Brand Guidelines", CREAM, 13),
             label(M, H - 46, "03 · Brand Mark", CREAM, 13),
             mark(250, 250, 520, CREAM, GREEN, "Hero mark"),
             head(920, 230, "The steam\nmark", 96, GREEN),
             text(920, 440, "Rising steam shaped like an S, a leaf at its base and two little dots. It says fresh and "
                            "warm without words — use it where the wordmark would be too small or repeated too often.",
                  24, INK, width=860, lh=1.45)]
    x = 920
    for fg, bg, n in [(GREEN, WHITE, "Green"), (BLUE, WHITE, "Blue"), (INK, WHITE, "Black"), (CREAM, GREEN, "Cream")]:
        parts += [rect(x, 600, 200, 200, bg, 28, f"Mark {n}", stroke=BEIGE, sw=2), mark(x + 55, 625, 150, fg, bg),
                  label(x, 840, n, MUTED, 13)]
        x += 220
    parts.append(label(920, 920, "App icon sizes", GREEN, 13))
    x = 1180
    for s in [96, 64, 40, 28]:
        parts += [rect(x, 960 - s, s, s, GREEN, s * 0.24), mark(x + s * 0.25, 960 - s + s * 0.12, s * 0.76, CREAM, GREEN)]
        x += s + 28
    return page("11 Brand mark", WHITE, *parts)


PALETTE = [
    ("Olive Green", GREEN, "32 · 77 · 54", "58 · 0 · 30 · 70", 50, CREAM),
    ("Cream", CREAM, "254 · 238 · 208", "0 · 7 · 18 · 0", 25, GREEN),
    ("White", WHITE, "255 · 255 · 255", "0 · 0 · 0 · 0", 15, GREEN),
    ("Royal Blue", BLUE, "2 · 56 · 154", "99 · 64 · 0 · 40", 10, WHITE),
]


def p_palette():
    parts = [chrome(13, "04 · Colour & Type", GREEN)]
    x, total = M, W - 2 * M
    for name, hx, rgb, cmyk, pct, fg in PALETTE:
        w = total * pct / 100
        parts += [rect(x, 120, w, 720, hx, 0, name, stroke=BEIGE if hx == WHITE else None, sw=2),
                  head(x + 32, 210, f"{pct}%", 64 if pct > 12 else 40, fg)]
        if w > 240:
            parts += [head(x + 32, 680, name, 40, fg), text(x + 32, 730, f"HEX {hx}", 20, fg),
                      text(x + 32, 762, f"RGB {rgb}", 20, fg), text(x + 32, 794, f"CMYK {cmyk}", 20, fg)]
        else:
            parts += [head(x + 24, 680, name.replace(" ", "\n"), 28, fg, lh=1.1),
                      text(x + 24, 760, hx, 18, fg), text(x + 24, 790, "RGB " + rgb.replace(" · ", "/"), 15, fg),
                      text(x + 24, 816, "CMYK " + cmyk.replace(" · ", "/"), 15, fg)]
        x += w
    parts.append(head(M, 920, "Palette & proportion", 44, GREEN))
    parts.append(text(M + 560, 905, "Green and cream carry the brand. Blue is the wink — keep it to 10% or less. "
                                    "Support: Beige #EFE8DE for soft backgrounds, Ink #1A1A1A for small text.",
                      20, INK, width=1100, lh=1.45))
    return page("13 Colour palette", WHITE, *parts)


def p_tints():
    parts = [chrome(14, "04 · Colour & Type", GREEN), head(M, 210, "Tints & pairings", 80, GREEN)]
    steps = [100, 80, 60, 40, 20]
    for row, (n, hx) in enumerate([("Olive Green", GREEN), ("Royal Blue", BLUE)]):
        y = 280 + row * 190
        parts.append(label(M, y - 14, n, GREEN, 13))
        for i, s in enumerate(steps):
            c = tint(hx, s / 100)
            parts += [rect(M + i * 172, y, 160, 140, c, 20, f"{n} {s}"),
                      text(M + i * 172 + 18, y + 120, f"{s}%", 18, WHITE if s >= 60 else hx)]
    pairs = [(GREEN, CREAM, True), (WHITE, GREEN, True), (BEIGE, BLUE, True), (BLUE, WHITE, True),
             (GREEN, BLUE, False), (WHITE, CREAM, False)]
    parts.append(label(1040, 266, "Text on background", GREEN, 13))
    for i, (bg, fg, ok) in enumerate(pairs):
        x = 1040 + (i % 3) * 266
        y = 280 + (i // 3) * 330
        parts += [rect(x, y, 250, 310, bg, 24, stroke=BEIGE if bg == WHITE else None, sw=2),
                  head(x + 30, y + 150, "Aa", 110, fg), text(x + 30, y + 270, "Fresh buns daily", 20, fg),
                  check(x + 210, y + 40, ok, (CREAM if bg == GREEN else GREEN) if ok else INK, GREEN if bg == GREEN else WHITE)]
    parts += [rect(M, 680, 840, 280, CREAM, 28),
              head(M + 40, 770, "Rule of thumb", 34, GREEN),
              text(M + 40, 830, "Cream on green is the signature LALO look. Never put green and blue next to each "
                                "other, and never use cream text on white or beige.", 22, INK, width=740, lh=1.45)]
    return page("14 Tints and pairings", WHITE, *parts)


def p_type():
    scale = [("Display", HEAD, 700, 72, "Warm buns, fresh brews"), ("Heading", HEAD, 700, 40, "Today's specials"),
             ("Label", HEAD, 400, 18, "BUNS & BREWS · HOT DRINKS"),
             ("Body", BODY, 400, 20, "Soft brioche bun with cinnamon butter, baked every morning."),
             ("Price", BODY, 600, 20, "₹ 120   ₹ 180   ₹ 240")]
    parts = [chrome(15, "04 · Colour & Type", CREAM, rule=CREAM),
             head(M - 14, 700, "Aa", 440, CREAM, name="Specimen"),
             label(M, 180, "Headlines & labels", CREAM, 14), head(M, 250, "Poppins", 64, CREAM),
             text(M, 790, "ABCDEFGHIJKLMNOPQRSTUVWXYZ\nabcdefghijklmnopqrstuvwxyz\n0123456789 & ₹ ! ?", 28, CREAM,
                  font=HEAD, lh=1.5),
             label(M, 960, "Body text · Inter — warm, simple, easy to read", CREAM, 13),
             rect(980, 150, 844, 790, CREAM, 36, "Type scale card")]
    y = 250
    for n, f, wgt, sz, sample in scale:
        ls = sz * 0.3 if n == "Label" else 0
        parts += [label(1030, y - 40, f"{n} · {f} {'Bold' if wgt == 700 else 'SemiBold' if wgt == 600 else 'Regular'} · {sz}px", MUTED, 12),
                  text(1030, y + sz * 0.3, sample, min(sz, 60), GREEN, font=f, weight=wgt, ls=ls, width=760 if sz < 40 else None),
                  line(1030, y + sz * 0.3 + 40, 1774, y + sz * 0.3 + 40, BEIGE, 2)]
        y += max(130, sz * 1.4 + 70)
    return page("15 Typography", GREEN, *parts)


def p_graphics():
    parts = [chrome(17, "05 · In the World", GREEN), head(M, 210, "Graphic elements", 80, GREEN),
             rect(M, 260, 1000, 690, GREEN, 36, "Steam pattern panel")]
    for r in range(4):
        for c in range(7):
            x = M + 40 + c * 140 + (70 if r % 2 else 0)
            if x > M + 900:
                continue
            parts.append(mark(x, 290 + r * 150, 105, CREAM if (r + c) % 3 else BLUE, GREEN, f"Pattern {r}-{c}", rotate=-14))
    parts += [label(M + 40, 920, "Steam pattern — bags, tissue paper, backgrounds", CREAM, 13),
              rect(1130, 260, 694, 330, CREAM, 36, "Spark panel"),
              spark(1290, 470, 150, GREEN), head(1430, 430, "New!", 72, GREEN),
              label(1170, 550, "Spark accent — highlight new items & prices", GREEN, 13),
              rect(1130, 620, 694, 330, BEIGE, 36, "Shapes panel"),
              rect(1180, 680, 260, 110, GREEN, 55), rect(1460, 680, 130, 110, BLUE, 55),
              rect(1610, 680, 160, 110, CREAM, 55, stroke=GREEN, sw=3),
              label(1170, 910, "Bun-round shapes — pills for buttons, prices, tags", GREEN, 13)]
    return page("17 Graphic elements", WHITE, *parts)


def p_photo():
    rules = [(True, "Warm, natural daylight with soft shadows"), (True, "Real food, close up — steam, crumb, latte art"),
             (True, "Cream, beige, wood or LALO green backgrounds"), (True, "LALO packaging in the shot"),
             (False, "Cold blue tones or heavy filters"), (False, "Stock photos of food we don't sell")]
    parts = [image("photo-cups-green.png", 0, 0, 1000, H, "Photography hero"),
             chrome(18, "05 · In the World", GREEN),
             rect(0, 0, 1000, 100, GREEN, 0), label(M, 70, "LALO — Brand Guidelines", CREAM, 13),
             head(1080, 230, "Photography", 80, GREEN),
             text(1080, 320, "Warm, honest and close enough to smell. Every photo should make you want a bun.",
                  24, INK, width=740, lh=1.45)]
    y = 480
    for ok, t in rules:
        parts += [check(1100, y - 8, ok, GREEN if ok else INK), text(1140, y, t, 24, INK)]
        y += 72
    parts.append(text(1080, 950, "Mockups shown are AI-generated placeholders. Replace with real product photos before launch.",
                      16, MUTED, width=740))
    return page("18 Photography", WHITE, *parts)


def p_applications():
    return page(
        "19 Applications", BEIGE,
        chrome(19, "05 · In the World", GREEN),
        image("photo-sign.png", M, 130, 900, 820, "Signboard photo", 36),
        head(1060, 230, "Applications", 80, GREEN),
        rect(1060, 290, 764, 300, GREEN, 32, "Signboard spec"),
        label(1100, 350, "Shop sign", CREAM, 14),
        text(1100, 410, "Round hanging sign, Ø 600 mm. Primary reversed logo, cream on olive green, lit warm white. "
                        "Logo width = 70% of the sign.", 22, CREAM, width=690, lh=1.45),
        image("photo-cups-cream.png", 1060, 620, 370, 330, "Cups photo", 32),
        rect(1454, 620, 370, 330, CREAM, 32, "Cup spec"),
        label(1490, 680, "Cups", GREEN, 14),
        text(1490, 730, "White cups: green logo. Hero cup: green with cream logo. Steam mark on lids & sleeves.",
             20, INK, width=300, lh=1.45),
    )


def p_back():
    return page(
        "20 Back cover", CREAM,
        mark(810, 230, 380, GREEN, CREAM, "Closing mark"),
        head(W / 2, 780, "Warm buns, fresh brews.", 64, GREEN, anchor="middle"),
        label(W / 2, 850, "LALO · Buns & Brews · Brand Guidelines Vol. 01", GREEN, 14, anchor="middle"),
        spark(1110, 300, 70, BLUE),
    )


def pages():
    return [
        p_cover(), p_contents(),
        chapter("01", "The Brand", ["Brand story", "Personality & voice"], 3, GREEN, CREAM, CREAM),
        p_story(), p_personality(),
        chapter("02", "Logo", ["Primary logo", "Logo versions", "Clear space & size", "Misuse"], 6, CREAM, GREEN, GREEN),
        p_primary_logo(), p_variations(), p_clearspace(), p_misuse(), p_mark(),
        chapter("04", "Colour & Type", ["Palette & proportion", "Tints & pairings", "Typography"], 12, BLUE, WHITE, CREAM),
        p_palette(), p_tints(), p_type(),
        chapter("05", "In the World", ["Graphic elements", "Photography", "Applications"], 16, GREEN, CREAM, CREAM,
                photo="photo-sign.png"),
        p_graphics(), p_photo(), p_applications(), p_back(),
    ]


def main():
    os.makedirs(OUT, exist_ok=True)
    steps = [{"command": "page.rename", "params": {"name": "LALO Brand Book"}}]
    cols = 4
    for i, (name, svg) in enumerate(pages()):
        fn = os.path.join(OUT, re.sub(r"[^\w]+", "-", name).strip("-").lower() + ".svg")
        open(fn, "w", encoding="utf-8").write(svg)
        steps.append({"command": "file.import",
                      "params": {"path": fn.replace("\\", "/"), "x": (i % cols) * (W + 200), "y": (i // cols) * (H + 240)}})
    json.dump(steps, open(os.path.join(OUT, "import.json"), "w"), indent=1)
    print(f"{len(steps) - 1} pages written to {OUT}")


if __name__ == "__main__":
    main()
