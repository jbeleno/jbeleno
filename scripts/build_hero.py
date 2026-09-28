"""Generate assets/hero.svg — a self-looping terminal + space-invaders animation.

Everything is SMIL so it plays inside GitHub's <img> sandbox (no JS allowed).
Every animation shares one global cycle of T seconds, so the loop stays in sync.

    python scripts/build_hero.py
"""
from pathlib import Path

T = 20.0  # full loop, seconds
W, H = 860, 390
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace"
CHAR_W = 9.0  # approx advance of a 15px monospace glyph

C = {
    "bg": "#0d1117", "border": "#30363d", "bar": "#161b22", "fg": "#e6edf3",
    "dim": "#8b949e", "green": "#3fb950", "blue": "#58a6ff", "purple": "#d2a8ff",
    "red": "#ff7b72", "yellow": "#e3b341", "orange": "#ffa657",
}


# ---------------------------------------------------------------- SMIL helpers
def _fmt(v):
    return f"{v:.2f}".rstrip("0").rstrip(".") if isinstance(v, float) else str(v)


def anim(attr, frames, mode="linear"):
    """frames: [(seconds, value), ...] -> <animate> on the global cycle."""
    frames = sorted(frames, key=lambda f: f[0])
    if frames[0][0] > 0:
        frames.insert(0, (0.0, frames[0][1]))
    if mode == "linear" and frames[-1][0] < T:
        frames.append((T, frames[-1][1]))
    kt = ";".join(f"{t / T:.4f}" for t, _ in frames)
    vals = ";".join(_fmt(v) for _, v in frames)
    return (f'<animate attributeName="{attr}" dur="{T}s" repeatCount="indefinite" '
            f'calcMode="{mode}" keyTimes="{kt}" values="{vals}"/>')


def visible(start, end=T):
    """Opacity 0 → 1 at `start`, back to 0 at `end`."""
    frames = [(0.0, 0), (start, 1)]
    if end < T:
        frames.append((end, 0))
    return anim("opacity", frames, "discrete")


# ---------------------------------------------------------------- pixel sprites
INVADER_A = """
..X.....X..
...X...X...
..XXXXXXX..
.XX.XXX.XX.
XXXXXXXXXXX
X.XXXXXXX.X
X.X.....X.X
...XX.XX...""".split()
INVADER_B = """
..X.....X..
X..X...X..X
X.XXXXXXX.X
XXX.XXX.XXX
XXXXXXXXXXX
.XXXXXXXXX.
..X.....X..
.X.......X.""".split()
SHIP = """
.....X.....
....XXX....
....XXX....
.XXXXXXXXX.
XXXXXXXXXXX
XXXXXXXXXXX""".split()
BOOM = """
X...X...X
.X..X..X.
..X...X..
XX.....XX
..X...X..
.X..X..X.
X...X...X""".split()


def sprite(rows, px, color, x0=0, y0=0):
    """Pixel art as one <path> (fewer nodes than a rect per pixel)."""
    d = []
    for j, row in enumerate(rows):
        i = 0
        while i < len(row):
            if row[i] == "X":
                k = i
                while k < len(row) and row[k] == "X":
                    k += 1
                d.append(f"M{x0 + i * px} {y0 + j * px}h{(k - i) * px}v{px}h-{(k - i) * px}z")
                i = k
            else:
                i += 1
    return f'<path fill="{color}" d="{"".join(d)}"/>'


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ---------------------------------------------------------------- scene
out = []
defs = []

# card + title bar
out.append(f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="12" fill="{C["bg"]}" stroke="{C["border"]}"/>')
out.append(f'<path d="M1 13a12 12 0 0 1 12-12h{W - 26}a12 12 0 0 1 12 12v23H1z" fill="{C["bar"]}"/>')
out.append(f'<line x1="1" y1="36" x2="{W - 1}" y2="36" stroke="{C["border"]}"/>')
for i, col in enumerate(["#ff5f57", "#febc2e", "#28c840"]):
    out.append(f'<circle cx="{22 + i * 20}" cy="18.5" r="6" fill="{col}"/>')
out.append(f'<text x="{W / 2}" y="23" text-anchor="middle" font-family="{MONO}" font-size="12" '
           f'fill="{C["dim"]}">jesus@neiva: ~/prod</text>')

scene = []  # everything that fades out at the end of the loop

# ---- terminal ---------------------------------------------------------------
X0 = 28
lines = [
    # (kind, y, text, start, end)  kind: cmd (typed) | out (instant)
    ("cmd", 64, "whoami", 0.4, 1.1),
    ("out", 86, [("Jesús Beleño", C["fg"]), (" · backend · mobile · applied AI · Neiva, CO", C["dim"])], 1.35, None),
    ("cmd", 114, "cat now.txt", 1.9, 2.8),
    ("out", 136, [("Product Engineer @ Symmetry", C["blue"]), (" — 1M+ downloads, 4.8★ · co-founder @ Skillion", C["dim"])], 3.05, None),
    ("cmd", 164, "./fix-bugs --env=production", 3.5, 4.9),
    ("out", 186, [("▶ 10 bugs detected in prod. ", C["red"]), ("launching fixer…", C["dim"])], 5.1, None),
]
for n, (kind, y, text, start, end) in enumerate(lines):
    if kind == "cmd":
        scene.append(f'<g>{visible(start - 0.25)}'
                     f'<text x="{X0}" y="{y}" font-family="{MONO}" font-size="15" fill="{C["green"]}" font-weight="bold">❯</text></g>')
        tx = X0 + 20
        clip = f"clip{n}"
        steps = len(text)
        frames = [(0.0, 0)] + [(start + (end - start) * k / steps, round((k + 1) * CHAR_W, 1)) for k in range(steps)]
        defs.append(f'<clipPath id="{clip}"><rect x="{tx}" y="{y - 16}" height="22" width="0">{anim("width", frames, "discrete")}</rect></clipPath>')
        scene.append(f'<text x="{tx}" y="{y}" font-family="{MONO}" font-size="15" fill="{C["fg"]}" clip-path="url(#{clip})">{esc(text)}</text>')
        # cursor that follows the typing, then disappears
        cur = [(0.0, tx)] + [(start + (end - start) * k / steps, round(tx + (k + 1) * CHAR_W, 1)) for k in range(steps)]
        scene.append(f'<rect y="{y - 13}" width="8" height="16" fill="{C["fg"]}" x="{tx}">'
                     f'{anim("x", cur, "discrete")}{visible(start - 0.25, end + 0.25)}</rect>')
    else:
        spans = "".join(f'<tspan fill="{col}">{esc(s)}</tspan>' for s, col in text)
        scene.append(f'<text x="{X0}" y="{y}" font-family="{MONO}" font-size="14">{visible(start)}{spans}</text>')

# ---- arena ------------------------------------------------------------------
AY0, AY1 = 204, H - 14
GAME_START = 5.5
scene.append(f'<g>{visible(GAME_START - 0.3)}'
             f'<line x1="20" y1="{AY0}" x2="{W - 20}" y2="{AY0}" stroke="{C["border"]}" stroke-dasharray="4 6"/></g>')

# twinkling stars
stars = [(60, 230), (140, 300), (250, 245), (380, 340), (470, 222), (600, 318), (700, 236), (790, 290), (820, 350), (95, 355), (530, 280), (330, 295)]
for i, (sx, sy) in enumerate(stars):
    scene.append(f'<circle cx="{sx}" cy="{sy}" r="1.2" fill="{C["dim"]}">{visible(GAME_START - 0.3)}'
                 f'<animate attributeName="r" values="0.6;1.6;0.6" dur="{1.6 + (i % 4) * 0.5}s" repeatCount="indefinite"/></circle>')

# aliens: 2 rows x 5 columns, each one a named bug
PX = 3
AW, AH = 11 * PX, 8 * PX
cols = [190, 320, 450, 580, 710]           # sprite centres
rows_y = [224, 276]                         # sprite tops
names = [["NullPointer", "N+1 query", "CORS", "OOM", "race cond."],
         ["HTTP 500", "flaky test", "mem leak", "deadlock", "tz bug"]]
colors = [C["purple"], C["red"]]

# kill order: bottom row first (so bullets never pass through a live alien)
order = [(1, 2), (1, 0), (1, 4), (1, 1), (1, 3), (0, 3), (0, 1), (0, 4), (0, 0), (0, 2)]
SHOT = 0.9
FIRST_SHOT = GAME_START + 0.6
MOVE, FLY = 0.32, 0.28

death = {}
for i, (r, c) in enumerate(order):
    death[(r, c)] = FIRST_SHOT + i * SHOT + MOVE + FLY

for r, y in enumerate(rows_y):
    for c, cx in enumerate(cols):
        x = cx - AW / 2
        dead = death[(r, c)]
        frame_a = sprite(INVADER_A, PX, colors[r], x, y)
        frame_b = sprite(INVADER_B, PX, colors[r], x, y)
        scene.append(
            f'<g>{visible(GAME_START, dead)}'
            f'<g>{frame_a}<animate attributeName="opacity" values="1;0" dur="1s" calcMode="discrete" repeatCount="indefinite"/></g>'
            f'<g opacity="0">{frame_b}<animate attributeName="opacity" values="0;1" dur="1s" calcMode="discrete" repeatCount="indefinite"/></g>'
            f'<text x="{cx}" y="{y + AH + 13}" text-anchor="middle" font-family="{MONO}" font-size="10" fill="{C["dim"]}">{esc(names[r][c])}</text>'
            f'</g>')
        # explosion
        bw = 9 * PX
        scene.append(f'<g>{visible(dead, dead + 0.3)}{sprite(BOOM, PX, C["yellow"], cx - bw / 2, y - 2)}</g>')

# ship
SHIP_W = 11 * PX
SHIP_Y = AY1 - 6 * PX - 4
ship_x0 = W / 2
ship_frames = [(0.0, ship_x0), (GAME_START, ship_x0)]
prev = ship_x0
for i, (r, c) in enumerate(order):
    s = FIRST_SHOT + i * SHOT
    ship_frames += [(s, prev), (s + MOVE, cols[c])]
    prev = cols[c]
end_shots = FIRST_SHOT + len(order) * SHOT
ship_frames += [(end_shots + 0.3, prev), (end_shots + 1.2, ship_x0)]
# translate the ship group: animate x of an inner <svg>-free <g> via transform
tf = [(t, f"{v - SHIP_W / 2:.1f} {SHIP_Y}") for t, v in ship_frames]
scene.append(f'<g>{visible(GAME_START)}<g>'
             f'<animateTransform attributeName="transform" type="translate" dur="{T}s" repeatCount="indefinite" '
             f'calcMode="linear" keyTimes="{";".join(f"{t / T:.4f}" for t, _ in tf + [(T, tf[-1][1])])}" '
             f'values="{";".join(v for _, v in tf + [(T, tf[-1][1])])}"/>'
             f'{sprite(SHIP, PX, C["green"])}</g></g>')

# bullets
for i, (r, c) in enumerate(order):
    fire = FIRST_SHOT + i * SHOT + MOVE
    hit = fire + FLY
    y_from, y_to = SHIP_Y - 10, rows_y[r] + AH - 8
    scene.append(f'<rect x="{cols[c] - 1.5}" width="3" height="10" rx="1" fill="{C["yellow"]}" y="{y_from}">'
                 f'{anim("y", [(0.0, y_from), (fire, y_from), (hit, y_to)])}{visible(fire, hit)}</rect>')

# score: bugs remaining
SCORE_X, SCORE_Y = W - 30, AY0 + 20
for k in range(11):  # k bugs left
    t_on = GAME_START if k == 10 else death[order[9 - k]]
    t_off = T if k == 0 else (death[order[10 - k]] if k < 10 else death[order[0]])
    color = C["green"] if k == 0 else C["orange"]
    scene.append(f'<text x="{SCORE_X}" y="{SCORE_Y}" text-anchor="end" font-family="{MONO}" font-size="12" fill="{color}">'
                 f'{visible(t_on, t_off)}BUGS IN PROD: {k:02d}</text>')
scene.append(f'<text x="30" y="{SCORE_Y}" font-family="{MONO}" font-size="12" fill="{C["dim"]}">{visible(GAME_START)}P1 · jbeleno</text>')

# victory
WIN = end_shots + 0.5
mid = (AY0 + SHIP_Y) / 2 + 6
scene.append(f'<g>{visible(WIN)}'
             f'<text x="{W / 2}" y="{mid - 8}" text-anchor="middle" font-family="{MONO}" font-size="26" font-weight="bold" fill="{C["green"]}">✓ ALL BUGS FIXED</text>'
             f'<text x="{W / 2}" y="{mid + 20}" text-anchor="middle" font-family="{MONO}" font-size="13" fill="{C["dim"]}">'
             f'deploy successful · 0 errors · p99 42ms · go touch grass</text></g>')

fade = anim("opacity", [(0.0, 1), (T - 0.9, 1), (T - 0.15, 0), (T, 0)])
svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
       f'role="img" aria-label="Terminal animation: Jesús Beleño fixing production bugs in a space-invaders game">'
       f'<title>jbeleno — fixing bugs in prod</title>'
       f'<defs>{"".join(defs)}</defs>{"".join(out)}<g>{fade}{"".join(scene)}</g></svg>')

dest = Path(__file__).resolve().parent.parent / "assets" / "hero.svg"
dest.write_text(svg, encoding="utf-8")
print(f"wrote {dest} ({len(svg) / 1024:.1f} KB)")
