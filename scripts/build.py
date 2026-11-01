#!/usr/bin/env python3
"""Генератор SVG-панелей для профиля L1DRE  (Watch Dogs 2 x Steam).

    python scripts/build.py

Тянет данные из GitHub (с GITHUB_TOKEN, если он есть в окружении)
и пишет в assets/: header, profile, showcase, activity, footer.
Нужен только Pillow (для ASCII-портрета из аватарки).
"""
import datetime as dt
import html
import json
import os
import random
import re
import urllib.request
from pathlib import Path

# ── что можно править под себя ───────────────────────────────────────────
USER = "L1DRE"
ALIAS = "gostname"
INFO = [  # строки под ником в карточке профиля
    ("role", "Lead Programmer"),
    ("team", "FIRST Tech Challenge"),
    ("stack", "Java · C++ · Android SDK"),
]
NOW_PLAYING = "FTC // autonomous.java"
TAGLINE = "> hello, friend. добро пожаловать в мой цифровой дневник"
TAGS = [("JAVA", "mg"), ("C++", "cy"), ("ANDROID SDK", "yl"), ("FTC", "txt")]
# ─────────────────────────────────────────────────────────────────────────

TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
OUT = Path(__file__).resolve().parent.parent / "assets"
FONT = ("'JetBrains Mono','Cascadia Mono','SF Mono',Consolas,'DejaVu Sans Mono',"
        "'Liberation Mono',Menlo,monospace")

BG, PANEL, LINE = "#050507", "#0d0f13", "#23262d"
TXT, DIM, FAINT = "#ececec", "#7d828c", "#2f323a"
MG, CY, YL, GR = "#ff2e88", "#00e5ff", "#f4e04d", "#a4d007"

LANG_COLORS = {
    "Java": "#b07219", "Python": "#3572A5", "HTML": "#e34c26", "CSS": "#663399",
    "JavaScript": "#f1e05a", "TypeScript": "#3178c6", "C++": "#f34b7d", "C": "#555555",
    "Kotlin": "#A97BFF", "Shell": "#89e051", "C#": "#178600", "Go": "#00ADD8",
}
# цвета кружка уровня, как в Steam: по десяткам
LEVEL_COLORS = ["#9b9b9b", "#c02942", "#d95b43", "#fecc23", "#467a3c",
                "#4e8ddb", "#7652c9", "#c252c9", "#542437", "#997c52"]
RANKS = [(5, "Скрипт-кидди"), (10, "Нетраннер"), (20, "Хакер"), (30, "Мастер"), (999, "Легенда ctOS")]
MONTHS = ["янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"]

# ANSI Shadow-подобные глифы для заголовка
GLYPHS = {
    "L": ["██╗     ", "██║     ", "██║     ", "██║     ", "███████╗", "╚══════╝"],
    "1": [" ██╗", "███║", "╚██║", " ██║", " ██║", " ╚═╝"],
    "D": ["██████╗ ", "██╔══██╗", "██║  ██║", "██║  ██║", "██████╔╝", "╚═════╝ "],
    "R": ["██████╗ ", "██╔══██╗", "██████╔╝", "██╔══██╗", "██║  ██║", "╚═╝  ╚═╝"],
    "E": ["███████╗", "██╔════╝", "█████╗  ", "██╔══╝  ", "███████╗", "╚══════╝"],
}

# пиксельная маска 8x8 для иконки ранга
MASK = ["..XXXX..", ".XXXXXX.", "XXXXXXXX", "X..XX..X", "X..XX..X", "XXXXXXXX", ".XX..XX.", "..X..X.."]


# ── данные ───────────────────────────────────────────────────────────────
def fetch(url, data=None, raw=False):
    req = urllib.request.Request(url, data=data, headers={
        "User-Agent": f"{USER}-profile-builder", "Accept": "application/vnd.github+json"})
    if TOKEN and "api.github.com" in url:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read()
    return body if raw else json.loads(body)


def calendar_graphql():
    q = """query($l:String!){user(login:$l){contributionsCollection{contributionCalendar{
      weeks{contributionDays{date contributionCount contributionLevel}}}}}}"""
    res = fetch("https://api.github.com/graphql",
                data=json.dumps({"query": q, "variables": {"l": USER}}).encode())
    lv = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}
    weeks = res["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    return [{"date": d["date"], "count": d["contributionCount"], "level": lv[d["contributionLevel"]]}
            for w in weeks for d in w["contributionDays"]]


def calendar_html():
    page = fetch(f"https://github.com/users/{USER}/contributions", raw=True).decode()
    tips = {m[0]: m[1] for m in re.findall(r'<tool-tip[^>]*for="([^"]+)"[^>]*>([^<]*)</tool-tip>', page)}
    days = []
    for td in re.findall(r"<td[^>]*data-date=[^>]*>", page):
        date = re.search(r'data-date="([^"]+)"', td)[1]
        cid = re.search(r'id="([^"]+)"', td)[1]
        level = int(re.search(r'data-level="(\d)"', td)[1])
        m = re.match(r"(\d+) contribution", tips.get(cid, ""))
        days.append({"date": date, "count": int(m[1]) if m else 0, "level": level})
    return sorted(days, key=lambda d: d["date"])


def collect():
    user = fetch(f"https://api.github.com/users/{USER}")
    repos = fetch(f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner")
    own = [r for r in repos if not r["fork"]]
    langs = {}
    for r in own:
        for name, size in fetch(r["languages_url"]).items():
            langs[name] = langs.get(name, 0) + size
    days = None
    if TOKEN:
        try:
            days = calendar_graphql()
        except Exception as e:  # токен без нужных прав — откатываемся на HTML
            print("graphql failed:", e)
    days = days or calendar_html()
    return {
        "user": user,
        "repos": len(own),
        "stars": sum(r["stargazers_count"] for r in own),
        "langs": sorted(langs.items(), key=lambda kv: -kv[1]),
        "days": days,
    }


def streaks(days):
    best = run = 0
    for d in days:
        run = run + 1 if d["count"] else 0
        best = max(best, run)
    cur, rest = 0, list(days)
    if rest and not rest[-1]["count"]:  # сегодня ещё может быть пусто
        rest.pop()
    for d in reversed(rest):
        if not d["count"]:
            break
        cur += 1
    return cur, best


def level_from_xp(xp):
    lvl = 0
    while True:
        step = 100 * (lvl // 10 + 1)
        if xp < step:
            return lvl, xp, step
        xp -= step
        lvl += 1


def plural(n, forms):
    n = abs(n) % 100
    if 10 < n < 20:
        return forms[2]
    n %= 10
    return forms[0] if n == 1 else forms[1] if 2 <= n <= 4 else forms[2]


# ── svg-кирпичики ────────────────────────────────────────────────────────
def esc(s):
    return html.escape(str(s), quote=True)


BASE_CSS = """
text{white-space:pre}
.txt{fill:%s}.dim{fill:%s}.faint{fill:%s}.mg{fill:%s}.cy{fill:%s}.yl{fill:%s}.gr{fill:%s}
.b{font-weight:700}
@keyframes blink{0%%,49%%{opacity:1}50%%,100%%{opacity:0}}
.blink{animation:blink 1.1s steps(1) infinite}
@keyframes sweep{from{transform:translateY(-60px)}to{transform:translateY(var(--h))}}
.sweep{animation:sweep 7s linear infinite}
""" % (TXT, DIM, FAINT, MG, CY, YL, GR)

COMMON_DEFS = f"""
<pattern id="scan" width="4" height="3" patternUnits="userSpaceOnUse"><rect width="4" height="1" fill="#000" opacity=".45"/></pattern>
<linearGradient id="beam" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="{CY}" stop-opacity="0"/><stop offset=".8" stop-color="{CY}" stop-opacity=".07"/>
  <stop offset="1" stop-color="{CY}" stop-opacity=".18"/></linearGradient>
<linearGradient id="neon" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{MG}"/><stop offset="1" stop-color="{CY}"/></linearGradient>
<filter id="glow" x="-30%" y="-30%" width="160%" height="160%">
  <feGaussianBlur stdDeviation="2.2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
"""


def svg(w, h, body, css="", defs="", title=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'font-family="{FONT}" role="img" aria-label="{esc(title)}">\n<title>{esc(title)}</title>\n'
            f'<style>{BASE_CSS}{css}</style>\n<defs>{COMMON_DEFS}{defs}</defs>\n{body}\n</svg>\n')


def mono(lines, x, y, cw, lh, fs, cls="txt", extra=""):
    """Строки ASCII ровно по сетке: textLength держит ширину при любом моно-шрифте."""
    out = []
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        out.append(f'<text x="{x:.1f}" y="{y + i * lh:.1f}" font-size="{fs}" class="{cls}" {extra} '
                   f'textLength="{len(line) * cw:.1f}" lengthAdjust="spacingAndGlyphs" '
                   f'xml:space="preserve">{esc(line)}</text>')
    return "\n".join(out)


def noise(w, h, rng, fs=10, opacity=0.08, density=0.5, chars="01<>/\\#%&*+=-:.{}[]"):
    cw, lh = fs * 0.6, fs * 1.3
    lines = ["".join(rng.choice(chars) if rng.random() < density else " " for _ in range(int(w / cw) + 1))
             for _ in range(int(h / lh) + 1)]
    return f'<g opacity="{opacity}">{mono(lines, 0, fs, cw, lh, fs)}</g>'


def chrome(w, h):
    """Сканлайны, бегущий луч и уголки — общий «экран» для всех панелей."""
    c = 14
    corners = "".join(
        f'<path d="M{x} {y + c * sy} V{y} H{x + c * sx}" fill="none" stroke="{col}" stroke-width="2"/>'
        for x, y, sx, sy, col in [(6, 6, 1, 1, MG), (w - 6, 6, -1, 1, CY), (6, h - 6, 1, -1, CY), (w - 6, h - 6, -1, -1, MG)])
    return (f'<rect class="sweep" style="--h:{h}px" width="{w}" height="60" fill="url(#beam)"/>'
            f'<rect width="{w}" height="{h}" fill="url(#scan)"/>{corners}')


def panel(x, y, w, h, title, count=None):
    head = (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{PANEL}" stroke="{LINE}"/>'
            f'<rect x="{x}" y="{y}" width="{w}" height="34" fill="#14171c"/>'
            f'<rect x="{x}" y="{y}" width="3" height="34" fill="{MG}"/>'
            f'<text x="{x + 16}" y="{y + 22}" font-size="14" class="txt">{esc(title)}</text>')
    if count is not None:
        head += f'<text x="{x + 16 + len(title) * 8.6 + 8}" y="{y + 23}" font-size="17" class="dim">{count}</text>'
    return head


# ── панели ───────────────────────────────────────────────────────────────
def build_header(d):
    W, H = 840, 300
    rng = random.Random(1337)
    word = "L1DRE"
    rows = [""] * 6
    for i, ch in enumerate(word):
        for r in range(6):
            rows[r] += GLYPHS[ch][r] + (" " if i < len(word) - 1 else "")
    cw, lh, fs = 13.5, 21, 21
    x0 = (W - len(rows[0]) * cw) / 2
    y0 = 92

    def layer(cls):
        return f'<g class="{cls}">{mono(rows, x0, y0, cw, lh, fs, cls="")}</g>'

    # набор текста посимвольно через clipPath + курсор, который едет за текстом
    tcw, tx, ty = 8.4, x0, 252
    n = len(TAGLINE)
    times = [round(0.55 * i / n, 4) for i in range(n + 1)] + [0.94]
    widths = [round(i * tcw, 1) for i in range(n + 1)] + [0]
    kt, ws = ";".join(map(str, times)), ";".join(map(str, widths))
    xs = ";".join(str(round(tx + w, 1)) for w in widths)
    typing = (f'<clipPath id="type"><rect x="{tx}" y="{ty - 16}" width="0" height="22">'
              f'<animate attributeName="width" values="{ws}" keyTimes="{kt}" calcMode="discrete" dur="10s" repeatCount="indefinite"/>'
              f'</rect></clipPath>')
    tagline = (f'<g clip-path="url(#type)"><text x="{tx}" y="{ty}" font-size="14" class="txt" '
               f'textLength="{n * tcw:.1f}" lengthAdjust="spacingAndGlyphs" xml:space="preserve">'
               f'{esc(TAGLINE)}</text></g>'
               f'<rect x="{tx}" y="{ty - 13}" width="8" height="16" fill="{MG}" class="blink">'
               f'<animate attributeName="x" values="{xs}" keyTimes="{kt}" calcMode="discrete" dur="10s" repeatCount="indefinite"/></rect>')

    chips, cx = [], tx
    for label, cls in TAGS:
        wdt = len(label) * 7.2 + 22
        chips.append(f'<rect x="{cx}" y="{ty + 16}" width="{wdt:.1f}" height="20" fill="none" stroke="{LINE}"/>'
                     f'<rect x="{cx}" y="{ty + 16}" width="3" height="20" class="{cls}"/>'
                     f'<text x="{cx + 12}" y="{ty + 30}" font-size="11" class="{cls} b">{esc(label)}</text>')
        cx += wdt + 8

    hexid = " ".join(f"{ord(c):02X}" for c in USER)
    side_l = mono(["0x" + "".join(rng.choice("0123456789ABCDEF") for _ in range(8)) for _ in range(8)],
                  22, 96, 6.6, 15, 11, cls="faint")
    side_r = "\n".join(
        f'<text x="{W - 22}" y="{96 + i * 15}" font-size="11" text-anchor="end" class="{c}">{esc(t)}</text>'
        for i, (t, c) in enumerate([("SYS ....... OK", "dim"), ("NET ....... UP", "dim"), ("ROOT .. GRANTED", "mg"),
                                    ("TRACE ..... OFF", "dim"), ("NODE ..... " + USER, "cy"), ("", "dim"),
                                    ("> breach.exe", "yl"), ("[██████░░] 78%", "dim")]))

    css = f"""
.gc{{fill:{CY};animation:gc 6s steps(1) infinite}}
.gm{{fill:{MG};animation:gm 6s steps(1) infinite}}
.gw{{fill:#f4f4f4}}
.sl{{fill:{YL};opacity:0;animation:sl 6s steps(1) infinite}}
@keyframes gc{{0%{{transform:translate(2px,0)}}80%{{transform:translate(9px,-1px)}}82%{{transform:translate(-5px,2px)}}84%{{transform:translate(14px,0)}}86%{{transform:translate(2px,0)}}95%{{transform:translate(-4px,0)}}96%{{transform:translate(2px,0)}}}}
@keyframes gm{{0%{{transform:translate(-2px,0)}}80%{{transform:translate(-10px,1px)}}82%{{transform:translate(6px,-2px)}}84%{{transform:translate(-15px,0)}}86%{{transform:translate(-2px,0)}}95%{{transform:translate(5px,0)}}96%{{transform:translate(-2px,0)}}}}
@keyframes sl{{0%{{opacity:0}}81%{{opacity:1;transform:translateX(22px)}}83%{{opacity:1;transform:translateX(-30px)}}85%{{opacity:0}}}}
"""
    band = f'<clipPath id="band"><rect x="0" y="{y0 + lh * 1.2}" width="{W}" height="{lh * 1.3}"/></clipPath>'
    body = f"""
<rect width="{W}" height="{H}" fill="{BG}"/>
{noise(W, H, rng, opacity=0.07)}
<rect width="{W}" height="28" fill="#0c0d11"/><rect y="28" width="{W}" height="1" fill="{LINE}"/>
<text x="16" y="19" font-size="11" class="dim"><tspan class="mg">▌</tspan>ctOS 2.0 :: NODE {USER} :: SESSION {dt.date.today():%Y.%m.%d}</text>
<text x="{W - 16}" y="19" font-size="11" class="dim" text-anchor="end">SIGNAL <tspan class="cy">▂▃▅▇</tspan> :: 0x{hexid.replace(' ', '')}</text>
{side_l}
{side_r}
{layer('gc')}
{layer('gm')}
{layer('gw')}
<g clip-path="url(#band)"><g class="sl">{mono(rows, x0, y0, cw, lh, fs, cls="")}</g></g>
{typing}{tagline}
{''.join(chips)}
{chrome(W, H)}
"""
    return svg(W, H, body, css, band, title=f"{USER} — ctOS banner")


def hacker_art(cols=58, rows=32):
    """Фигура в капюшоне с LED-маской: рисуем силуэт в Pillow и переводим в ASCII-слои."""
    from PIL import Image, ImageDraw, ImageFilter
    S = 240

    def canvas():
        im = Image.new("L", (S, S), 0)
        return im, ImageDraw.Draw(im)

    body, d = canvas()
    d.polygon([(6, 240), (36, 192), (95, 170), (145, 170), (204, 192), (234, 240)], fill=125)
    d.polygon([(76, 240), (98, 176), (142, 176), (164, 240)], fill=60)
    d.ellipse((52, 18, 188, 200), fill=205)
    d.ellipse((62, 28, 178, 194), fill=150)
    d.ellipse((80, 60, 160, 182), fill=14)
    d.rounded_rectangle((86, 94, 154, 152), radius=16, fill=48)
    body = body.filter(ImageFilter.GaussianBlur(3))
    rim, r = canvas()
    r.arc((52, 18, 188, 200), start=-75, end=70, fill=255, width=8)
    r.line([(204, 192), (234, 240)], fill=255, width=8)
    rim = rim.filter(ImageFilter.GaussianBlur(1))
    a = body.resize((cols, rows), Image.LANCZOS).load()
    b = rim.resize((cols, rows), Image.LANCZOS).load()

    ramp = " .,:;-=+*x#%@"
    rng = random.Random(USER)
    base, edge, rain = [], [], []
    for y in range(rows):
        lb, le, lr = [], [], []
        for x in range(cols):
            v = a[x, y]
            ch = ramp[min(len(ramp) - 1, v * len(ramp) // 256)]
            is_rim = b[x, y] > 110 and v > 40
            lb.append(" " if is_rim else ch)
            le.append(rng.choice("#%@x") if is_rim else " ")
            lr.append(rng.choice("01") if v < 8 and rng.random() < 0.14 else " ")
        base.append(lb), edge.append(le), rain.append(lr)

    # LED-маска: глаза и рот, второй кадр — моргание
    eyes = [" ▄▄▄▄▄     ▄▄▄▄▄ ",
            "  ▀████▄ ▄████▀  ",
            "                 ",
            "    ▄▀▄▀▄▀▄▀▄    "]
    shut = ["                 ",
            "  ▄▄▄▄▄▄ ▄▄▄▄▄▄  ",
            "                 ",
            "    ▄▀▄▀▄▀▄▀▄    "]
    mx, my = cols // 2 - len(eyes[0]) // 2, int(rows * 0.43)
    led_open, led_shut = [[" "] * cols for _ in range(rows)], [[" "] * cols for _ in range(rows)]
    for dy in range(len(eyes)):
        for dx in range(len(eyes[0])):
            if eyes[dy][dx] != " " or shut[dy][dx] != " ":
                base[my + dy][mx + dx] = " "
            led_open[my + dy][mx + dx] = eyes[dy][dx]
            led_shut[my + dy][mx + dx] = shut[dy][dx]
    join = lambda g: ["".join(row) for row in g]
    return {"base": join(base), "rim": join(edge), "rain": join(rain),
            "led": join(led_open), "blink": join(led_shut)}


def build_profile(d):
    W, H = 840, 300
    rng = random.Random(42)
    u = d["user"]
    total = sum(x["count"] for x in d["days"])
    xp = total * 10 + d["repos"] * 40 + d["stars"] * 50 + u["followers"] * 25
    lvl, have, need = level_from_xp(xp)
    rank = next(name for top, name in RANKS if lvl < top)
    lcol = LEVEL_COLORS[min(lvl // 10, 9)]
    created = dt.datetime.fromisoformat(u["created_at"].replace("Z", "+00:00"))

    # аватар-рамка + ASCII-портрет
    ax, ay, a = 26, 28, 244
    layers = hacker_art()
    cw, lh = (a - 12) / len(layers["base"][0]), (a - 12) / len(layers["base"])
    fs = round(lh * 0.95, 2)

    def put(key):
        return mono(layers[key], ax + 6, ay + 6 + lh * 0.82, cw, lh, fs, cls="")

    art = put("base")
    figure = (f'<g fill="{FAINT}">{put("rain")}</g><g fill="url(#pfade)">{art}</g><g fill="{CY}" opacity=".85">{put("rim")}</g>'
              f'<g fill="{MG}" filter="url(#glow)"><g class="eo">{put("led")}</g><g class="ec">{put("blink")}</g></g>')
    band = (f'<linearGradient id="pfade" gradientUnits="userSpaceOnUse" x1="0" y1="{ay}" x2="0" y2="{ay + a}">'
            f'<stop offset="0" stop-color="#f0f0f0"/><stop offset=".55" stop-color="#b9bcc2"/><stop offset="1" stop-color="#4a4e57"/></linearGradient>'
            f'<clipPath id="pb1"><rect x="{ax}" y="{ay + a * .34}" width="{a}" height="{lh * 3}"/></clipPath>'
            f'<clipPath id="pb2"><rect x="{ax}" y="{ay + a * .68}" width="{a}" height="{lh * 2}"/></clipPath>'
            f'<clipPath id="pframe"><rect x="{ax}" y="{ay}" width="{a}" height="{a}"/></clipPath>')
    avatar = (f'<rect x="{ax - 4}" y="{ay - 4}" width="{a + 8}" height="{a + 8}" fill="none" stroke="url(#neon)" stroke-width="2" filter="url(#glow)"/>'
              f'<rect x="{ax}" y="{ay}" width="{a}" height="{a}" fill="#000"/>'
              f'<g clip-path="url(#pframe)">{figure}'
              f'<g clip-path="url(#pb1)"><g class="pg1" fill="{MG}">{art}</g></g>'
              f'<g clip-path="url(#pb2)"><g class="pg2" fill="{CY}">{art}</g></g></g>'
              f'<circle cx="{ax + a - 6}" cy="{ay + a - 6}" r="9" fill="{BG}" stroke="{LINE}"/>'
              f'<circle cx="{ax + a - 6}" cy="{ay + a - 6}" r="4.5" fill="{GR}" class="blink"/>')

    nx = 302
    info = "\n".join(
        f'<text x="{nx}" y="{176 + i * 22}" font-size="13"><tspan class="mg">▶ </tspan>'
        f'<tspan class="dim">{esc(k.ljust(6))}</tspan><tspan class="mg"> ▶ </tspan><tspan class="txt">{esc(v)}</tspan></text>'
        for i, (k, v) in enumerate(INFO))
    who = f"""
<text x="{nx}" y="66" font-size="32" class="txt b">{USER}<tspan font-size="16" class="dim"> ▾</tspan></text>
<text x="{nx}" y="92" font-size="13" class="dim">Hi, I'm <tspan class="txt">{esc(ALIAS)}</tspan>  ·  dedsec-node #{u['id'] % 10000:04d}</text>
<text x="{nx}" y="120" font-size="12" fill="#4a4e57">- - - - - - - - - - -<tspan class="mg"> ○ </tspan>- - - - - - - - - - -</text>
<text x="{nx}" y="144" font-size="12" class="dim">☾ {created:%d.%m.%Y} ☽   на GitHub</text>
{info}
"""

    # правая колонка: уровень, ранг, xp, статус
    rx, rw = 604, 210
    pix = "".join(f'<rect x="{rx + 14 + c * 5}" y="{110 + r * 5}" width="5" height="5" fill="{MG if r in (3, 4) and c in (1, 2, 5, 6) else TXT}"/>'
                  for r, row in enumerate(MASK) for c, ch in enumerate(row) if ch == "X")
    bar = int((rw - 28) * have / need)
    right = f"""
<text x="{rx}" y="66" font-size="21" class="txt">Уровень</text>
<circle cx="{rx + 128}" cy="59" r="17" fill="none" stroke="{lcol}" stroke-width="2.5"/>
<text x="{rx + 128}" y="65" font-size="15" class="txt b" text-anchor="middle">{lvl}</text>
<rect x="{rx}" y="96" width="{rw}" height="66" fill="#14161b" stroke="{LINE}"/>
<rect x="{rx + 8}" y="104" width="50" height="50" fill="#000" stroke="{LINE}"/>
{pix}
<text x="{rx + 70}" y="124" font-size="13" class="txt">{esc(rank)}</text>
<text x="{rx + 70}" y="144" font-size="12" class="dim">{xp} XP</text>
<rect x="{rx}" y="172" width="{rw - 28}" height="5" fill="{FAINT}"/>
<rect x="{rx}" y="172" width="{bar}" height="5" fill="{lcol}"/>
<text x="{rx}" y="194" font-size="11" class="dim">до ур. {lvl + 1}: {need - have} XP</text>
<text x="{rx}" y="236" font-size="19" class="gr">В игре</text>
<text x="{rx}" y="258" font-size="12" class="gr" opacity=".75">{esc(NOW_PLAYING)}</text>
"""
    css = """
.ec{opacity:0;animation:ec 4.5s steps(1) infinite}.eo{animation:eo 4.5s steps(1) infinite}
@keyframes ec{0%{opacity:0}93%{opacity:1}96%{opacity:0}}
@keyframes eo{0%{opacity:1}93%{opacity:0}96%{opacity:1}}
.pg1{animation:pg1 5s steps(1) infinite}.pg2{animation:pg2 5s steps(1) infinite}
@keyframes pg1{0%{opacity:0}70%{opacity:1;transform:translateX(9px)}72%{transform:translateX(-6px)}74%{opacity:0}}
@keyframes pg2{0%{opacity:0}88%{opacity:1;transform:translateX(-8px)}90%{transform:translateX(5px)}92%{opacity:0}}
"""
    body = f"""
<defs><linearGradient id="pbg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#16181d"/><stop offset="1" stop-color="{BG}"/></linearGradient></defs>
<rect width="{W}" height="{H}" fill="url(#pbg)"/>
{noise(W, H, rng, opacity=0.05, density=0.35)}
{avatar}{who}{right}
{chrome(W, H)}
"""
    return svg(W, H, body, css, band, title=f"{USER} — профиль, уровень {lvl}")


def build_showcase(d):
    W = 840
    u = d["user"]
    days = d["days"]
    total = sum(x["count"] for x in days)
    _, best = streaks(days)
    age = (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(u["created_at"].replace("Z", "+00:00"))).days

    tiles, letters = [], [">"] + list(USER) + ["_"]
    tw, gap, tx0, ty = 98, 13, 26, 62
    for i, ch in enumerate(letters):
        x = tx0 + i * (tw + gap)
        cls = "flick" if ch == "D" else "blink" if ch == "_" else ""
        stroke = MG if ch in "_>" else TXT
        tiles.append(f'<rect x="{x}" y="{ty}" width="{tw}" height="84" fill="#08090b" stroke="#2c2f37" stroke-width="2"/>'
                     f'<rect x="{x + 4}" y="{ty + 4}" width="{tw - 8}" height="76" fill="none" stroke="#16181d"/>'
                     f'<text x="{x + tw / 2}" y="{ty + 61}" font-size="54" text-anchor="middle" fill="none" '
                     f'stroke="{stroke}" stroke-width="2" filter="url(#glow)" class="{cls}">{esc(ch)}</text>')

    stats = [(total, plural(total, ("вклад", "вклада", "вкладов")) + " за год"),
             (d["repos"], plural(d["repos"], ("репозиторий", "репозитория", "репозиториев"))),
             (age, plural(age, ("день", "дня", "дней")) + " на GitHub"),
             (best, "рекордная серия, " + plural(best, ("день", "дня", "дней")))]
    st = "".join(f'<text x="{26 + i * 200}" y="196" font-size="34" class="txt">{v}</text>'
                 f'<text x="{26 + i * 200}" y="218" font-size="12" class="dim">{esc(lbl)}</text>'
                 for i, (v, lbl) in enumerate(stats))

    # «значки» — языки
    langs = d["langs"][:6]
    lsum = sum(s for _, s in d["langs"]) or 1
    badges, bx = [], 26
    for name, size in langs:
        col = LANG_COLORS.get(name, "#8b8b8b")
        cx, cy, r = bx + 26, 292, 24
        hexp = " ".join(f"{cx + r * c:.1f},{cy + r * s:.1f}" for c, s in
                        [(0, -1), (.866, -.5), (.866, .5), (0, 1), (-.866, .5), (-.866, -.5)])
        badges.append(f'<polygon points="{hexp}" fill="{col}" fill-opacity=".18" stroke="{col}" stroke-width="2"/>'
                      f'<text x="{cx}" y="{cy + 5}" font-size="14" text-anchor="middle" class="txt b">{esc(name[:2].upper())}</text>'
                      f'<text x="{bx + 60}" y="{cy - 3}" font-size="13" class="txt">{esc(name)}</text>'
                      f'<text x="{bx + 60}" y="{cy + 14}" font-size="11" class="dim">{size * 100 / lsum:.1f}%</text>')
        bx += 134
    seg, sx = [], 26
    for name, size in d["langs"]:
        w = (W - 52) * size / lsum
        seg.append(f'<rect x="{sx:.1f}" y="336" width="{max(w - 1, 0):.1f}" height="6" fill="{LANG_COLORS.get(name, "#8b8b8b")}"/>')
        sx += w

    H = 366
    css = f"""
.flick{{animation:flick 4s infinite}}
@keyframes flick{{0%,18%,22%,25%,53%,57%,100%{{opacity:1}}20%,24%,55%{{opacity:.15}}}}
"""
    body = f"""
<rect width="{W}" height="{H}" fill="{BG}"/>
{panel(10, 10, W - 20, 222, "Витрина достижений")}
{''.join(tiles)}
<line x1="26" y1="160" x2="{W - 26}" y2="160" stroke="{LINE}"/>
{st}
{panel(10, 244, W - 20, 112, "Значки", len(d["langs"]))}
{''.join(badges)}
{''.join(seg)}
{chrome(W, H)}
"""
    return svg(W, H, body, css, title=f"{USER} — витрина достижений")


def build_activity(d):
    W, H = 840, 258
    days = d["days"]
    total = sum(x["count"] for x in days)
    cur, best = streaks(days)
    peak = max((x["count"] for x in days), default=0)

    first = dt.date.fromisoformat(days[0]["date"])
    start = first - dt.timedelta(days=(first.weekday() + 1) % 7)  # неделя с воскресенья, как у GitHub
    cw, rh, gx, gy = 14, 19, 62, 82
    chars = "·░▒▓█"
    cells, months, last_m = [], [], None
    weeks = 0
    for x in days:
        day = dt.date.fromisoformat(x["date"])
        col = (day - start).days // 7
        row = (day.weekday() + 1) % 7
        weeks = max(weeks, col + 1)
        cells.append(f'<text x="{gx + col * cw}" y="{gy + row * rh}" font-size="15" class="l{x["level"]}">{chars[x["level"]]}</text>')
        if row == 0 and day.month != last_m and day.day <= 7:
            months.append(f'<text x="{gx + col * cw}" y="{gy - 22}" font-size="11" class="dim">{MONTHS[day.month - 1]}</text>')
            last_m = day.month
    labels = "".join(f'<text x="24" y="{gy + r * rh}" font-size="11" class="dim">{t}</text>'
                     for r, t in [(1, "пн"), (3, "ср"), (5, "пт")])
    legend = (f'<text x="{W - 26}" y="{H - 24}" font-size="11" class="dim" text-anchor="end">меньше '
              + " ".join(f'<tspan class="l{i}">{c}</tspan>' for i, c in enumerate(chars)) + " больше</text>")
    foot = (f'<text x="26" y="{H - 24}" font-size="12" class="dim">'
            f'<tspan class="mg">▌</tspan>{total} {plural(total, ("вклад", "вклада", "вкладов"))}   '
            f'<tspan class="cy">▌</tspan>серия: {cur}   <tspan class="yl">▌</tspan>рекорд: {best}   '
            f'<tspan class="txt">▌</tspan>пик: {peak}/день</text>')
    beam_w = weeks * cw
    css = f"""
.l0{{fill:#3d414a}}.l1{{fill:#6b2a52}}.l2{{fill:#b02e74}}.l3{{fill:{MG}}}.l4{{fill:#ffd1e8}}
.l3,.l4{{filter:url(#glow)}}
.scanx{{animation:scanx 9s linear infinite}}
@keyframes scanx{{from{{transform:translateX(0)}}to{{transform:translateX({beam_w}px)}}}}
"""
    body = f"""
<rect width="{W}" height="{H}" fill="{BG}"/>
{panel(10, 10, W - 20, H - 20, "Журнал активности  //  surveillance.log")}
{''.join(months)}{labels}
<g class="scanx"><rect x="{gx - 4}" y="{gy - 16}" width="{cw}" height="{rh * 7}" fill="{CY}" opacity=".12"/>
<rect x="{gx - 4 + cw}" y="{gy - 16}" width="1" height="{rh * 7}" fill="{CY}" opacity=".6"/></g>
{''.join(cells)}
{foot}{legend}
{chrome(W, H)}
"""
    return svg(W, H, body, css, title=f"{USER} — {total} вкладов за год")


def build_footer(d):
    W, H = 840, 96
    rng = random.Random(9)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    css = """.fg{animation:fg 7s steps(1) infinite}
@keyframes fg{0%{transform:none}90%{transform:translate(-6px,1px)}92%{transform:translate(5px,0)}94%{transform:none}}"""
    body = f"""
<rect width="{W}" height="{H}" fill="{BG}"/>
{noise(W, H, rng, opacity=0.06)}
<g class="fg">
<text x="{W / 2 - 2}" y="46" font-size="20" text-anchor="middle" class="cy" opacity=".7">[ CONNECTION TERMINATED ]</text>
<text x="{W / 2 + 2}" y="46" font-size="20" text-anchor="middle" class="mg" opacity=".7">[ CONNECTION TERMINATED ]</text>
<text x="{W / 2}" y="46" font-size="20" text-anchor="middle" class="txt b">[ CONNECTION TERMINATED ]</text></g>
<text x="{W / 2}" y="72" font-size="11" text-anchor="middle" class="dim">stay curious :: hack everything :: last sync {stamp}<tspan class="mg blink"> █</tspan></text>
{chrome(W, H)}
"""
    return svg(W, H, body, css, title="connection terminated")


def main():
    d = collect()
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fn in [("header", build_header), ("profile", build_profile), ("showcase", build_showcase),
                     ("activity", build_activity), ("footer", build_footer)]:
        (OUT / f"{name}.svg").write_text(fn(d), encoding="utf-8")
        print("wrote", name)


if __name__ == "__main__":
    main()
