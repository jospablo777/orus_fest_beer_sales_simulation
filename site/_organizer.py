"""Builds the organizer page in one language from site/_text.yaml and the simulation outputs.

site/index.qmd (Spanish) and site/en.qmd (English) call render(lang) and print the result,
so both pages share one structure and one set of numbers.
"""

import math
import sys
from pathlib import Path

import yaml

SITE = Path(__file__).resolve().parent
ROOT = SITE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import report_values  # noqa: E402
from sim import diagrams  # noqa: E402


def n0(x):
    return f"{x:,.0f}"


def up(x):
    """Whole minutes, rounded up, for statements of the form "x minutes or less"."""
    return f"{math.ceil(x - 1e-9):,d}"


def fields(v: dict, lang: str, text: dict) -> dict:
    r = v["raw"]
    price = r["price"]
    hp = v["hourly_plan"]
    early = hp[hp["hour"] < 18]["med"].max()
    cases = list(text["wi_case"])
    what_if = [r[f"wi_{k}"] for k in cases]
    worst = max(cases, key=lambda k: r[f"wi_{k}_hi"])
    f = {
        "tickets": n0(r["tickets"]), "price": n0(price),
        "base_p90": n0(r["base_evening_p90_min"]), "plan_p90": up(r["plan_evening_p90_min"]),
        "base_exchange": n0(r["base_obs_exchange_median_min"]),
        "base_buyer": n0(r["base_obs_buyer_median_min"]),
        "plan_wait": up(max(r["plan_obs_median_min"], 1)),
        "obs_from": r["obs_from"], "obs_to": r["obs_to"],
        "night_wait": n0(r["base_night_exchange_median_min"]),
        "night_wait_lo": n0(r["base_night_exchange_median_min_lo"]),
        "night_wait_hi": n0(r["base_night_exchange_median_min_hi"]),
        "q1": n0(r["base_queue_cash_obs"]), "q2": n0(r["base_queue_pour_obs"]),
        "base_maxq": n0(r["base_max_in_lines"]), "plan_maxq": n0(r["plan_max_in_lines"]),
        "base_lost": n0(r["base_lost_attempts"]), "plan_lost": n0(r["plan_lost_attempts"]),
        "d_beers": n0(r["d_beers_med"]), "d_beers_lo": n0(r["d_beers_med_lo"]),
        "d_beers_hi": n0(r["d_beers_med_hi"]), "d_mxn": n0(round(r["d_beers_med"] * price, -3)),
        "base_hours": n0(r["base_line_hours"]), "plan_hours": n0(r["plan_line_hours"]),
        "improved_n": n0(r["d_wait_improved_n"]), "nights": n0(r["nights"]),
        "heavy_base": f"{100 * r['base_heavy6_share']:.0f}%",
        "heavy_plan": f"{100 * r['plan_heavy6_share']:.0f}%",
        "inside_peak": n0(round(r["plan_peak_occupancy"], -1)), "lim": str(r["density_limit"]),
        "cap_tickets": n0(round(r["cap_tickets"], -2)) if r["cap_tickets"] else "",
        "target_wait": str(r["target_wait"]), "reliability": f"{100 * r['reliability']:.0f}%",
        "low_hour": n0(round(early + 5, -1)),
        "peak_hour": n0(round(r["plan_beers_peak_hour"], -1)),
        "peak_hour_lo": n0(round(r["plan_beers_peak_hour_lo"], -1)),
        "peak_hour_hi": n0(round(r["plan_beers_peak_hour_hi"], -1)),
        "base_peak_hour": n0(round(r["base_beers_peak_hour"], -1)),
        "wi_max": up(max(what_if)), "wi_worst": up(r[f"wi_{worst}_hi"]),
        "wi_worst_case": text["wi_case"][worst][lang],
        "svc_from": r["svc_from"], "svc_to": r["svc_to"],
        "sellers_from": r["sellers_from"], "sellers_to": r["sellers_to"],
        "clip_from": r["clip_from"], "clip_to": r["clip_to"],
        "sims": v["sims"], "hall_side": f"{100 * r['hall_side_uncertainty']:.0f}%",
        "pour_lo": n0(r["pour_2026_lo"]), "pour_hi": n0(r["pour_2026_hi"]),
    }
    crew = next(row for row in v["staffing_rows"] if row["tickets"] == r["tickets"])
    f["met"], f["crew_nights"] = str(crew["met"]), str(crew["nights"])
    taps, sellers = r["plan_taps"], r["plan_sellers"]
    f["crew_es"] = f"{taps} puestos en la barra" + (f" y {sellers} vendedores en pista" if sellers else "")
    f["crew_en"] = f"{taps} stations at the bar" + (f" and {sellers} sellers on the floor" if sellers else "")
    crews = v["crews"]
    alone = crews[(crews["sellers"] == 0) & (crews["share_met"] >= r["reliability"])]
    f["seller_share"] = f"{100 * r['plan_seller_share']:.0f}%"
    for code in ("es", "en"):
        fallback = (text["seller_fallback"][code].format(k=int(alone["n_pour"].min()))
                    if len(alone) else "")
        f[f"seller_note_{code}"] = (text["seller_note"][code].format(
            seller_share=f["seller_share"], seller_fallback=fallback) if sellers else "")
    if sellers and len(alone):
        k = int(alone["n_pour"].min())
        f["alt_es"] = f"Sin vendedores se necesitan {k} puestos en la barra."
        f["alt_en"] = f"Without sellers the bar needs {k} stations."
    elif sellers:
        f["alt_es"] = "Sin vendedores, ninguna de las opciones probadas cumple la meta."
        f["alt_en"] = "Without sellers, none of the options tested meets the target."
    else:
        f["alt_es"] = f["alt_en"] = ""
    known = "cap_sentence_known" if r["cap_tickets"] else "cap_sentence_none"
    for code in ("es", "en"):
        f["cap_range"] = ""
        if r["cap_tickets_lo"] and r["cap_tickets_hi"]:
            f["cap_range"] = text["cap_range"][code].format(
                cap_lo=n0(round(r["cap_tickets_lo"], -2)), cap_hi=n0(round(r["cap_tickets_hi"], -2)))
        f[f"cap_sentence_{code}"] = text[known][code].format(**f)
    return f


def pieces(lang: str) -> list[tuple[str, str]]:
    """The page as a list of (kind, content). Kinds: "html" (a block of HTML), "h2", "p"
    and "links" (the row of links to the technical pages, in Quarto markdown)."""
    text = yaml.safe_load((SITE / "_text.yaml").read_text(encoding="utf-8"))
    v = report_values.compute()
    r = v["raw"]
    f = fields(v, lang, text)

    def t(key):
        return text[key][lang].format(**f)

    def figure(inner, caption=None):
        cap = f"<figcaption>{caption}</figcaption>" if caption else ""
        return ("html", f'<figure class="plain-figure">{inner}{cap}</figure>')

    def img(name, alt):
        return f'<img src="assets/figures/{name}_{lang}.png" alt="{alt}" loading="lazy">'

    def video(name, label):
        return (f'<video controls preload="none" playsinline '
                f'poster="assets/video/{name}_{lang}.jpg" '
                f'src="assets/video/{name}_{lang}.mp4" aria-label="{label}"></video>')

    exchange, total = r["base_obs_exchange_median_min"], r["base_obs_buyer_median_min"]
    scale = max(exchange, total, 1.0)
    gave_up = 10 * r["base_abandon_share"]
    observed, service = (r["obs_from"], r["obs_to"]), (r["svc_from"], r["svc_to"])

    def both_layouts(draw):
        return (f'<div class="diagram wide">{draw(False)}</div>'
                f'<div class="diagram narrow">{draw(True)}</div>')

    old = both_layouts(lambda narrow: diagrams.old_process(
        lang, exchange, total, r["base_queue_cash_obs"], r["base_queue_pour_obs"], gave_up,
        scale, observed, narrow))
    new = both_layouts(lambda narrow: diagrams.new_process(
        lang, max(r["plan_obs_median_min"], 1), r["plan_evening_p90_min"], r["plan_taps"],
        r["plan_sellers"], scale, observed, service, narrow))

    out = [("html", f'<p class="lede">{t("lede")}</p>'),
           ("h2", t("h_old")), figure(old), ("p", t("old_text")),
           ("h2", t("h_new")), figure(new), ("p", t("new_text"))]

    tiles = "".join(
        f'<div class="tile good"><span class="v">{t(f"tile_{k}_v")}</span>'
        f'<span class="l">{t(f"tile_{k}")}</span></div>'
        for k in ("audience", "staff", "sales", "reputation"))
    out += [("h2", t("h_gain")), ("html", f'<div class="tiles">{tiles}</div>'),
            figure(img("summary_wait", t("fig_wait_alt")), t("wait_caption"))]

    seller_key = "sellers" if r["plan_sellers"] else "none"
    actions = [(t("a1_t"), t("a1")), (t("a2_t"), t("a2")),
               (t(f"a3_t_{seller_key}"), t(f"a3_{seller_key}")),
               (t("a4_t"), t("a4")), (t("a5_t"), t("a5")), (t("a6_t"), t("a6"))]
    items = "".join(f"<li><strong>{a}</strong><span>{b}</span></li>" for a, b in actions)
    out += [("h2", t("h_plan")),
            ("html", f'<div class="plan">{img("summary_plan", t("plan_alt"))}'
                     f'<ol class="actions">{items}</ol></div>')]

    out += [("h2", t("h_video")),
            figure(video("night_2026_vs_plan", t("video_night")), t("video_night")),
            figure(video("changeover_2026_vs_plan", t("video_change")), t("video_change"))]

    head = text["staff_table_head"][lang]
    rows = []
    for row in v["staffing_rows"]:
        if row.get("taps") is None:
            rows.append(f"<tr><td>{n0(row['tickets'])}</td><td colspan=\"4\">"
                        f"{text['staff_none'][lang]}</td></tr>")
        else:
            rows.append(f"<tr><td>{n0(row['tickets'])}</td><td>{row['taps']}</td>"
                        f"<td>{row['sellers']}</td><td>{row['met']} / {row['nights']}</td>"
                        f"<td>{n0(round(row['inside'], -1))}</td></tr>")
    table = ("<div class=\"tablewrap\"><table class=\"table\"><thead><tr>"
             + "".join(f"<th>{h}</th>" for h in head) + "</tr></thead><tbody>"
             + "".join(rows) + "</tbody></table></div>")
    out += [("h2", t("h_staff")), ("p", t("staff_text")),
            figure(img("summary_crews", t("fig_crews_alt"))), ("html", table),
            figure(img("summary_sales", t("fig_sales_alt")), t("sales_text")),
            ("p", t("whatif_text"))]

    conf = "".join(f'<div class="conf {k}"><strong>{t(f"conf_{k}_t")}</strong>'
                   f'<span>{t(f"conf_{k}")}</span></div>' for k in ("firm", "prob", "check"))
    out += [("h2", t("h_conf")), ("html", f'<div class="confs">{conf}</div>')]

    needs = "".join(f"<li>{item}</li>" for item in text["needs"][lang])
    out += [("h2", t("h_need")),
            ("html", f'<div class="needs"><p>{t("need_text")}</p><ol>{needs}</ol></div>')]

    out += [("h2", t("h_how")), ("p", t("how_text")), ("links", t("links"))]
    return out


def render(lang: str) -> str:
    """Quarto markdown of the page, included by site/index.qmd and site/en.qmd."""
    form = {"html": "\n```{{=html}}\n{}\n```\n", "h2": "\n## {}\n", "p": "\n{}\n",
            "links": "\n{}\n"}
    return "".join(form[kind].format(content) for kind, content in pieces(lang))


def render_html(lang: str) -> str:
    """The page as plain HTML without the links to the technical pages, for the single-file
    preview built by scripts/make_preview.py."""
    form = {"html": "{}\n", "h2": "<h2>{}</h2>\n", "p": "<p>{}</p>\n", "links": ""}
    return "".join(form[kind].format(content) for kind, content in pieces(lang))
