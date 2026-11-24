"""Process diagrams for the organizer pages: how a beer was bought in 2026 and how it is
bought under the plan. Each function returns an inline SVG string.

The drawings use currentColor for text and outlines, so they follow the page theme. Red marks
the 2026 lines and bronze the plan. The time bars of both diagrams share one scale. Each
diagram has a left-to-right layout for wide screens and a top-to-bottom one for phones
(narrow=True); the page shows one of them according to its width.
"""

from __future__ import annotations

import math
import textwrap
from html import escape

from . import theme

W = 960
NARROW_W = 360
TEXT = {
    "en": {
        "old_title": "In 2026 one beer took two lines",
        "new_title": "Under the plan there is one line, and the beer is paid for where it is served",
        "want": ["Wants", "a beer"], "back": ["Back to", "the show"],
        "window": ["Ticket window"], "window_sub": ["one window", "for every drink"],
        "exchange": ["Exchange", "at the bar"], "exchange_sub": ["2 beer lines,", "1 for cocktails"],
        "line1": "Line 1", "line2": "Line 2", "people": "about {n} people",
        "station": ["Any serving station", "takes card or cash", "and hands over the beer"],
        "stations": "{n} stations open", "sellers": "and {n} sellers walk the floor",
        "charges": "1 person charges", "serve": ["{n} person serves", "{n} people serve"],
        "charge_serve": "{n} people charge and serve",
        "one_line": "One short line",
        "old_seen": "Over 40 min in the exchange line with the tickets already bought. This is what we saw.",
        "old_exchange": "{wait} min estimated in the exchange line ({lo} to {hi} across nights)",
        "old_total": "{wait} min estimated in total for a person who also stood in the ticket line ({lo} to {hi})",
        "new_time": "{wait} min in line (people who joined between {a} and {b})",
        "old_note": ("Estimates for the people who joined a line between {a} and {b}. "
                     "An estimated {gave_up} of every 10 purchase attempts were abandoned."),
        "new_note": "9 of 10 buyers wait {p90} min or less between {a} and {b}",
        "cocktails": "cocktails and shots (outside this study)",
        "old_aria": "In 2026 a buyer stood in the ticket line and then in an exchange line.",
        "new_aria": "Under the plan a buyer stands in one line and pays where the beer is served.",
    },
    "es": {
        "old_title": "En 2026 había que hacer dos filas para una cerveza",
        "new_title": "Con el plan hay una sola fila y la cerveza se paga donde se sirve",
        "want": ["Quiere una", "cerveza"], "back": ["Vuelve", "al show"],
        "window": ["Caja de fichas"], "window_sub": ["una sola ventanilla", "para todas las bebidas"],
        "exchange": ["Canje", "en la barra"], "exchange_sub": ["2 filas de cerveza,", "1 de cocteles"],
        "line1": "Fila 1", "line2": "Fila 2", "people": "unas {n} personas",
        "station": ["Cualquier puesto de la barra", "cobra con tarjeta o efectivo", "y entrega la cerveza"],
        "stations": "{n} puestos abiertos", "sellers": "y {n} vendedores recorren la pista",
        "charges": "1 persona cobra", "serve": ["{n} persona sirve", "{n} personas sirven"],
        "charge_serve": "{n} personas cobran y sirven",
        "one_line": "Una fila corta",
        "old_seen": "Más de 40 min en la fila de canje con las fichas ya compradas, que es lo que vimos.",
        "old_exchange": "{wait} min estimados en la fila de canje (entre {lo} y {hi} según la noche)",
        "old_total": "{wait} min estimados en total para quien además hacía la fila de la caja (entre {lo} y {hi})",
        "new_time": "{wait} min en la fila (quienes se formaron entre las {a} y las {b})",
        "old_note": ("Estimaciones para quienes se formaron entre las {a} y las {b}. "
                     "Se estima que se abandonaron {gave_up} de cada 10 intentos de compra."),
        "new_note": "9 de cada 10 compradores esperan {p90} min o menos entre las {a} y las {b}",
        "cocktails": "cocteles y shots (fuera de este estudio)",
        "old_aria": "En 2026 la persona hacía la fila de fichas y luego una fila de canje.",
        "new_aria": "Con el plan la persona hace una sola fila y paga donde le sirven la cerveza.",
    },
}


def _text(x, y, lines, size=15, weight=400, anchor="middle", fill="currentColor", opacity=1.0):
    spans = "".join(f'<tspan x="{x}" dy="{0 if k == 0 else size * 1.25:.0f}">{escape(line)}</tspan>'
                    for k, line in enumerate(lines))
    return (f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}" fill="{fill}" opacity="{opacity}">{spans}</text>')


def _box(x, y, w, h, title, sub=None, stroke="currentColor", dy=0):
    """A box with its title and subtitle centered, moved dy pixels down."""
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="none" '
           f'stroke="{stroke}" stroke-opacity="0.55" stroke-width="1.5"/>']
    n = len(title) + (len(sub) if sub else 0)
    top = y + h / 2 - (n - 1) * 10 + 3 + dy
    out.append(_text(x + w / 2, top, title, size=18, weight=700))
    if sub:
        out.append(_text(x + w / 2, top + len(title) * 22 + 3, sub, size=14.5, opacity=0.8))
    return "".join(out)


def _worker(cx, cy, fill="currentColor", scale=1.0):
    """A person behind the bar: head and shoulders, centered at (cx, cy)."""
    r, w, h = 4.5 * scale, 15 * scale, 10 * scale
    return (f'<circle cx="{cx:.1f}" cy="{cy - 6 * scale:.1f}" r="{r:.1f}" fill="{fill}"/>'
            f'<path d="M{cx - w / 2:.1f},{cy + 1 * scale + h:.1f} v{-h / 2:.1f} '
            f'a{w / 2:.1f},{h / 2:.1f} 0 0 1 {w:.1f},0 v{h / 2:.1f} z" fill="{fill}"/>')


def _workers(cx, cy, n, fill="currentColor", step=22):
    first = cx - (n - 1) * step / 2
    return "".join(_worker(first + k * step, cy, fill) for k in range(n))


def _serve_label(t, n):
    return t["serve"][0 if n == 1 else 1].format(n=n)


def _arrow(x0, x1, y):
    return (f'<line x1="{x0}" y1="{y}" x2="{x1 - 7}" y2="{y}" stroke="currentColor" '
            f'stroke-opacity="0.6" stroke-width="1.5"/>'
            f'<polygon points="{x1},{y} {x1 - 9},{y - 5} {x1 - 9},{y + 5}" fill="currentColor" '
            f'fill-opacity="0.6"/>')


def _people(x0, y, n, fill, step=11, r=4):
    return "".join(f'<circle cx="{x0 + k * step}" cy="{y}" r="{r}" fill="{fill}"/>'
                   for k in range(n))


def _arrow_down(x, y0, y1):
    return (f'<line x1="{x}" y1="{y0}" x2="{x}" y2="{y1 - 7}" stroke="currentColor" '
            f'stroke-opacity="0.6" stroke-width="1.5"/>'
            f'<polygon points="{x},{y1} {x - 5},{y1 - 9} {x + 5},{y1 - 9}" fill="currentColor" '
            f'fill-opacity="0.6"/>')


def _svg(height, label, body, width=W):
    return (f'<svg viewBox="0 0 {width} {height:.0f}" role="img" aria-label="{escape(label)}" '
            f'style="max-width:100%;height:auto;display:block" xmlns="http://www.w3.org/2000/svg">'
            f'{body}</svg>')


def _one(lines):
    return [" ".join(lines)]


def _centered_people(y, n, fill, step=14, r=4.5):
    return _people(NARROW_W / 2 - (n - 1) * step / 2, y, n, fill, step=step, r=r)


def _footer(parts, y, bars, note):
    """Time bars with their headlines and a note at the bottom of a narrow diagram.
    bars: (share of the scale, color, opacity, headline). Returns the height."""
    left, width = 16, NARROW_W - 32
    for share, color, opacity, headline in bars:
        parts.append(f'<rect x="{left}" y="{y}" width="{max(width * share, 10):.0f}" '
                     f'height="20" rx="4" fill="{color}" fill-opacity="{opacity}"/>')
        head = textwrap.wrap(headline, 36)
        parts.append(_text(left, y + 44, head, size=16.5, weight=700, anchor="start"))
        y += 44 + 21 * (len(head) - 1) + 18
    body = textwrap.wrap(note, 44)
    parts.append(_text(left, y + 8, body, size=14, anchor="start", opacity=0.85))
    return y + 8 + 18 * (len(body) - 1) + 14


def _old_narrow(t, exchange_min, total_min, ticket_line, exchange_line, gave_up_of_10,
                scale_min, observed, exchange_rng, total_rng, pourers):
    left, width, mid = 16, NARROW_W - 32, NARROW_W / 2
    title = textwrap.wrap(t["old_title"], 30)
    parts = [_text(left, 28, title, size=20, weight=700, anchor="start")]
    y = 28 + 25 * (len(title) - 1) + 20
    parts.append(_box(left, y, width, 54, _one(t["want"])))
    y += 54
    parts.append(_text(mid, y + 24, [f'{t["line1"]} · ' + t["people"].format(n=round(ticket_line))],
                       size=15, fill=theme.DOT_TICKET, weight=700))
    parts.append(_centered_people(y + 42, 11, theme.DOT_TICKET))
    y += 58
    parts.append(_box(left, y, width, 112, t["window"], _one(t["window_sub"]), dy=-20))
    parts.append(_workers(mid, y + 72, 1))
    parts.append(_text(mid, y + 100, [t["charges"]], size=13.5, opacity=0.85))
    y += 112
    parts.append(_text(mid, y + 24, [f'{t["line2"]} · ' + t["people"].format(n=round(exchange_line))],
                       size=15, fill=theme.DOT_TICKET, weight=700))
    parts.append(_centered_people(y + 42, 11, theme.DOT_TICKET))
    parts.append(_centered_people(y + 58, 11, theme.DOT_TICKET))
    parts.append(_centered_people(y + 74, 11, theme.SILVER))
    parts.append(_text(mid, y + 97, [t["cocktails"]], size=13, opacity=0.7))
    y += 110
    parts.append(_box(left, y, width, 112, _one(t["exchange"]), _one(t["exchange_sub"]),
                      dy=-20))
    parts.append(_workers(mid, y + 72, pourers))
    parts.append(_text(mid, y + 100, [_serve_label(t, pourers)], size=13.5, opacity=0.85))
    y += 112
    parts.append(_arrow_down(mid, y + 6, y + 26))
    y += 32
    parts.append(_box(left, y, width, 54, _one(t["back"])))
    y += 54 + 30
    seen = textwrap.wrap(t["old_seen"], 34)
    parts.append(_text(left, y, seen, size=17, weight=700, anchor="start", fill=theme.DOT_TICKET))
    y += 21 * (len(seen) - 1) + 22
    bars = [(min(exchange_min / scale_min, 1.0), theme.RED, 1.0,
             t["old_exchange"].format(wait=round(exchange_min), lo=round(exchange_rng[0]),
                                      hi=round(exchange_rng[1]))),
            (min(total_min / scale_min, 1.0), theme.RED, 0.55,
             t["old_total"].format(wait=round(total_min), lo=round(total_rng[0]),
                                   hi=round(total_rng[1])))]
    height = _footer(parts, y, bars, t["old_note"].format(
        gave_up=f"{gave_up_of_10:.0f}", a=observed[0], b=observed[1]))
    return _svg(height, t["old_aria"], "".join(parts), NARROW_W)


def _new_narrow(t, wait_min, p90_min, stations, sellers, scale_min, observed, service):
    left, width, mid = 16, NARROW_W - 32, NARROW_W / 2
    title = textwrap.wrap(t["new_title"], 30)
    parts = [_text(left, 28, title, size=20, weight=700, anchor="start")]
    y = 28 + 25 * (len(title) - 1) + 20
    parts.append(_box(left, y, width, 54, _one(t["want"])))
    y += 54
    parts.append(_text(mid, y + 24, [t["one_line"]], size=15, fill=theme.BRONZE, weight=700))
    parts.append(_centered_people(y + 42, 3, theme.BRONZE))
    parts.append(_arrow_down(mid, y + 52, y + 72))
    y += 78
    shown = min(stations, 12)
    per_row = shown if shown <= 6 else math.ceil(shown / 2)
    rows = math.ceil(shown / per_row)
    box_h = 92 + rows * 40 + 44
    parts.append(f'<rect x="{left}" y="{y}" width="{width}" height="{box_h}" rx="10" fill="none" '
                 f'stroke="{theme.BRONZE}" stroke-width="2"/>')
    parts.append(_text(mid, y + 30, t["station"], size=16.5, weight=700))
    first = mid - (per_row * 32 - 8) / 2
    for k in range(shown):
        col, row = k % per_row, k // per_row
        y0 = y + 86 + row * 40
        parts.append(_worker(first + col * 32 + 12, y0 + 10, theme.BRONZE))
        parts.append(f'<rect x="{first + col * 32:.0f}" y="{y0 + 22:.0f}" width="24" height="8" '
                     f'rx="2" fill="{theme.BRONZE}" fill-opacity="0.55"/>')
    parts.append(_text(mid, y + 92 + rows * 40 + 8, [t["stations"].format(n=stations)],
                       size=13.5, opacity=0.85))
    parts.append(_text(mid, y + 92 + rows * 40 + 26, [t["charge_serve"].format(n=stations)],
                       size=13.5, opacity=0.85))
    y += box_h
    if sellers:
        parts.append(_text(mid, y + 24, [t["sellers"].format(n=sellers)], size=14.5,
                           opacity=0.85))
        y += 30
    parts.append(_arrow_down(mid, y + 6, y + 26))
    y += 32
    parts.append(_box(left, y, width, 54, _one(t["back"])))
    y += 54 + 24
    bars = [(min(wait_min / scale_min, 1.0), theme.BRONZE, 1.0,
             t["new_time"].format(wait=math.ceil(wait_min - 1e-9), a=observed[0], b=observed[1]))]
    height = _footer(parts, y, bars, t["new_note"].format(
        p90=math.ceil(p90_min - 1e-9), a=service[0], b=service[1]))
    return _svg(height, t["new_aria"], "".join(parts), NARROW_W)


def old_process(lang: str, exchange_min: float, total_min: float, ticket_line: float,
                exchange_line: float, gave_up_of_10: float, scale_min: float,
                observed: tuple[str, str], narrow: bool = False,
                exchange_rng: tuple[float, float] = (0, 0),
                total_rng: tuple[float, float] = (0, 0), pourers: int = 3) -> str:
    """The 2026 purchase: ticket window, then exchange at the bar. The first line under the
    drawing is what the attendees saw. exchange_min is the estimated wait in the exchange
    line and total_min the estimated wait of a person who starts without tickets, both for
    people who joined a line in the clock window `observed`; the *_rng pairs are their
    ranges across nights. pourers is the typical number of people serving beer in 2026."""
    t = TEXT[lang]
    if narrow:
        return _old_narrow(t, exchange_min, total_min, ticket_line, exchange_line,
                           gave_up_of_10, scale_min, observed, exchange_rng, total_rng, pourers)
    top, h = 70, 160
    mid = top + h / 2
    parts = [_text(20, 34, [t["old_title"]], size=22, weight=700, anchor="start")]
    parts.append(_box(20, top, 150, h, t["want"]))
    parts.append(_text(245, top - 6, [f'{t["line1"]} · ' + t["people"].format(n=round(ticket_line))],
                       size=15, fill=theme.DOT_TICKET, weight=700))
    parts.append(_people(184, mid, 11, theme.DOT_TICKET))
    parts.append(_box(310, top, 180, h, t["window"], t["window_sub"], dy=-30))
    parts.append(_workers(400, top + h - 50, 1))
    parts.append(_text(400, top + h - 16, [t["charges"]], size=13.5, opacity=0.85))
    parts.append(_text(565, top - 6, [f'{t["line2"]} · ' + t["people"].format(n=round(exchange_line))],
                       size=15, fill=theme.DOT_TICKET, weight=700))
    parts.append(_people(504, mid - 22, 11, theme.DOT_TICKET))
    parts.append(_people(504, mid, 11, theme.DOT_TICKET))
    parts.append(_people(504, mid + 22, 11, theme.SILVER))
    parts.append(_box(630, top, 170, h, t["exchange"], t["exchange_sub"], dy=-30))
    parts.append(_workers(715, top + h - 50, pourers))
    parts.append(_text(715, top + h - 16, [_serve_label(t, pourers)], size=13.5, opacity=0.85))
    parts.append(_arrow(806, 826, mid))
    parts.append(_box(830, top, 110, h, t["back"]))
    parts.append(_text(504, top + h + 22, [t["cocktails"]], size=13.5, anchor="start", opacity=0.7))
    parts.append(_text(20, top + h + 62, [t["old_seen"]], size=18, weight=700, anchor="start",
                       fill=theme.DOT_TICKET))
    bar_y = top + h + 84
    for minutes, rng, opacity, key in ((exchange_min, exchange_rng, 1.0, "old_exchange"),
                                       (total_min, total_rng, 0.55, "old_total")):
        width = (W - 40) * min(minutes / scale_min, 1.0)
        parts.append(f'<rect x="20" y="{bar_y}" width="{width:.0f}" height="22" rx="4" '
                     f'fill="{theme.RED}" fill-opacity="{opacity}"/>')
        parts.append(_text(20, bar_y + 46, [t[key].format(wait=round(minutes), lo=round(rng[0]),
                                                          hi=round(rng[1]))], size=17,
                           weight=700, anchor="start"))
        bar_y += 66
    parts.append(_text(20, bar_y + 6, [t["old_note"].format(gave_up=f"{gave_up_of_10:.0f}",
                                                            a=observed[0], b=observed[1])],
                       size=15.5, anchor="start", opacity=0.85))
    return _svg(bar_y + 22, t["old_aria"], "".join(parts))


def new_process(lang: str, wait_min: float, p90_min: float, stations: int, sellers: int,
                scale_min: float, observed: tuple[str, str], service: tuple[str, str],
                narrow: bool = False) -> str:
    """The purchase under the plan: one line per station, payment and beer at the same place.
    `observed` is the clock window of wait_min and `service` the one of p90_min."""
    t = TEXT[lang]
    if narrow:
        return _new_narrow(t, wait_min, p90_min, stations, sellers, scale_min, observed, service)
    top, h = 70, 160
    mid = top + h / 2
    parts = [_text(20, 34, [t["new_title"]], size=22, weight=700, anchor="start")]
    parts.append(_box(20, top, 150, h, t["want"]))
    parts.append(_text(245, top - 6, [t["one_line"]], size=15, fill=theme.BRONZE, weight=700))
    parts.append(_people(228, mid, 3, theme.BRONZE))
    parts.append(_arrow(266, 300, mid))
    bx, bw = 310, 490
    parts.append(f'<rect x="{bx}" y="{top}" width="{bw}" height="{h}" rx="10" fill="none" '
                 f'stroke="{theme.BRONZE}" stroke-width="2"/>')
    parts.append(_text(bx + 152, mid - 20, t["station"], size=16.5, weight=700))
    gx = bx + 310
    shown = min(stations, 12)
    per_row = shown if shown <= 5 else math.ceil(shown / 2)
    rows = math.ceil(shown / per_row)
    # one worker behind each station
    left = gx + 76 - (per_row * 32 - 8) / 2
    for k in range(shown):
        col, row = k % per_row, k // per_row
        y0 = top + 18 + row * 40
        parts.append(_worker(left + col * 32 + 12, y0 + 10, theme.BRONZE))
        parts.append(f'<rect x="{left + col * 32:.0f}" y="{y0 + 22:.0f}" width="24" height="8" '
                     f'rx="2" fill="{theme.BRONZE}" fill-opacity="0.55"/>')
    parts.append(_text(gx + 76, top + h - 30, [t["stations"].format(n=stations)], size=13.5,
                       opacity=0.85))
    parts.append(_text(gx + 76, top + h - 12, [t["charge_serve"].format(n=stations)],
                       size=13.5, opacity=0.85))
    parts.append(_arrow(806, 826, mid))
    parts.append(_box(830, top, 110, h, t["back"]))
    if sellers:
        parts.append(_text(bx, top + h + 22, [t["sellers"].format(n=sellers)], size=14.5,
                           anchor="start", opacity=0.85))
    bar_y = top + h + 44
    width = max((W - 40) * min(wait_min / scale_min, 1.0), 10)
    parts.append(f'<rect x="20" y="{bar_y}" width="{width:.0f}" height="22" rx="4" '
                 f'fill="{theme.BRONZE}"/>')
    parts.append(_text(20, bar_y + 46, [t["new_time"].format(wait=math.ceil(wait_min - 1e-9),
                                                             a=observed[0], b=observed[1])],
                       size=17, weight=700, anchor="start"))
    parts.append(_text(20, bar_y + 68, [t["new_note"].format(p90=math.ceil(p90_min - 1e-9),
                                                             a=service[0], b=service[1])],
                       size=14, anchor="start", opacity=0.8))
    return _svg(bar_y + 82, t["new_aria"], "".join(parts))


def before_after(lang: str, f: dict, taps: int, sellers: int, narrow: bool = False) -> str:
    """Two panels, 2026 and the plan: the lines as dots, one figure per person on staff and
    the wait between f["obs_from"] and f["obs_to"] as the largest text. In 2026 the figures
    are the typical people on staff (f["staff_2026"]); under the plan the stations (bronze)
    and the floor sellers (green)."""
    import yaml
    from pathlib import Path
    text = yaml.safe_load((Path(__file__).resolve().parents[1] / "site" / "_text.yaml")
                          .read_text(encoding="utf-8"))

    def tx(key, **kw):
        return text[key][lang].format(**{**f, **kw})

    staff_2026 = int(round(float(str(f["staff_2026"]).replace(",", ""))))
    width = NARROW_W if narrow else W
    pw = width - 32 if narrow else (W - 60) / 2
    ph = 250
    parts = []
    title = textwrap.wrap(tx("ba_title"), 30 if narrow else 80)
    parts.append(_text(16, 30, title, size=20 if narrow else 22, weight=700, anchor="start"))
    top = 30 + 25 * (len(title) - 1) + 22

    def panel(x0, y0, label, wait, lines, staff, color, dots, figs):
        out = [f'<rect x="{x0}" y="{y0}" width="{pw:.0f}" height="{ph}" rx="12" fill="none" '
               f'stroke="{color}" stroke-width="2"/>']
        cx = x0 + pw / 2
        out.append(_text(x0 + 18, y0 + 30, [label], size=17, weight=700, anchor="start",
                         fill=color))
        out.append(_text(cx, y0 + 86, [wait], size=46 if not narrow else 40, weight=800,
                         fill=color))
        out.append(_text(cx, y0 + 116, [lines], size=15, opacity=0.85))
        rows = [dots[k:k + 16] for k in range(0, len(dots), 16)]
        for j, row in enumerate(rows):
            first = cx - (len(row) - 1) * 6
            out += [f'<circle cx="{first + k * 12:.1f}" cy="{y0 + 140 + j * 13}" r="4" '
                    f'fill="{c}"/>' for k, c in enumerate(row)]
        fy = y0 + 140 + max(len(rows), 1) * 13 + 26
        per = 11 if narrow else 14
        for j in range(0, len(figs), per):
            chunk = figs[j:j + per]
            first = cx - (len(chunk) - 1) * 11
            out += [_worker(first + k * 22, fy + (j // per) * 30, c, scale=0.9)
                    for k, c in enumerate(chunk)]
        out.append(_text(cx, y0 + ph - 14, [staff], size=14, opacity=0.85))
        return "".join(out)

    old_dots = [theme.DOT_TICKET] * 16 + [theme.DOT_TAP] * 32
    new_dots = [theme.BRONZE] * 3
    old_figs = [theme.SILVER] * staff_2026
    new_figs = [theme.BRONZE] * taps + [theme.DOT_SELLER] * sellers
    p1 = panel(16, top, tx("ba_2026"), tx("ba_wait_2026"), tx("ba_lines_2026"),
               tx("ba_staff_2026", n=staff_2026), theme.RED, old_dots, old_figs)
    if narrow:
        y2 = top + ph + 16
        p2 = panel(16, y2, tx("ba_plan"), tx("ba_wait_plan"), tx("ba_lines_plan"),
                   tx("ba_staff_plan", taps=taps, sellers=sellers), theme.BRONZE, new_dots,
                   new_figs)
        height = y2 + ph + 12
    else:
        p2 = panel(16 + pw + 28, top, tx("ba_plan"), tx("ba_wait_plan"), tx("ba_lines_plan"),
                   tx("ba_staff_plan", taps=taps, sellers=sellers), theme.BRONZE, new_dots,
                   new_figs)
        height = top + ph + 12
    label = f'{tx("ba_2026")}: {tx("ba_wait_2026")}. {tx("ba_plan")}: {tx("ba_wait_plan")}.'
    return _svg(height, label, "".join(parts) + p1 + p2, width)
