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

# Cases of the what-if table, in the order shown.
WHAT_IF = ["plan", "plan_minimum", "plan_two_absent", "plan_minimum_two_absent", "plan_sold_out",
           "plan_thirsty", "plan_slow_pay", "plan_late_sellers", "plan_slow_refill", "no_sellers"]


def n0(x):
    return f"{x:,.0f}"


def n10(x):
    """Rounded to the nearest 10, for counts of people."""
    return f"{round(x, -1):,.0f}"


def up(x):
    """Whole minutes, rounded up, for statements of the form "x minutes or less"."""
    return f"{math.ceil(x - 1e-9):,d}"


def crew_name(taps: int, sellers: int, lang: str) -> str:
    if lang == "es":
        return f"{taps} puestos en la barra" + (f" y {sellers} vendedores en pista" if sellers else "")
    return f"{taps} stations at the bar" + (f" and {sellers} sellers on the floor" if sellers else "")


def fields(v: dict, lang: str, text: dict) -> dict:
    r = v["raw"]
    price = r["price"]
    hp = v["hourly_plan"]
    early = hp[hp["hour"] < 18]["med"].max()
    pct0 = lambda x: f"{100 * x:.0f}%"  # noqa: E731
    f = {
        "tickets": n0(r["tickets"]), "price": n0(price),
        "plan_p90": up(r["plan_evening_p90_min"]),
        "plan_p90_bad": up(r["plan_evening_p90_min_hi"]),
        "base_exchange": n0(r["base_obs_exchange_median_min"]),
        "base_exchange_lo": n0(r["base_obs_exchange_median_min_lo"]),
        "base_exchange_hi": n0(r["base_obs_exchange_median_min_hi"]),
        "plan_wait": up(max(r["plan_obs_median_min"], 1)),
        "obs_from": r["obs_from"], "obs_to": r["obs_to"],
        "night_wait": n0(r["base_night_exchange_median_min"]),
        "night_wait_lo": n0(r["base_night_exchange_median_min_lo"]),
        "night_wait_hi": n0(r["base_night_exchange_median_min_hi"]),
        "q1": n0(r["base_queue_cash_obs"]), "q2": n0(r["base_queue_pour_obs"]),
        "q1_lo": n0(r["base_queue_cash_obs_lo"]), "q1_hi": n0(r["base_queue_cash_obs_hi"]),
        "q2_lo": n0(r["base_queue_pour_obs_lo"]), "q2_hi": n0(r["base_queue_pour_obs_hi"]),
        "base_maxq": n0(r["base_max_in_lines"]), "plan_maxq": n0(r["plan_max_in_lines"]),
        "base_maxq_lo": n0(r["base_max_in_lines_lo"]), "base_maxq_hi": n0(r["base_max_in_lines_hi"]),
        "base_lost": n10(r["base_lost_attempts"]), "plan_lost": n0(r["plan_lost_attempts"]),
        "base_lost_lo": n10(r["base_lost_attempts_lo"]),
        "base_lost_hi": n10(r["base_lost_attempts_hi"]),
        "d_beers": n0(r["d_beers_med"]), "d_beers_lo": n0(r["d_beers_med_lo"]),
        "d_beers_hi": n0(r["d_beers_med_hi"]), "d_mxn": n0(round(r["d_beers_med"] * price, -3)),
        "per_hour": n0(r["ss_beers_per_extra_hour"]),
        "per_hour_mxn": n0(round(r["ss_beers_per_extra_hour"] * price, -1)),
        "staff_2026": n0(r["ss_staff_2026"]), "staff_2026_lo": n0(r["ss_staff_2026_lo"]),
        "staff_2026_hi": n0(r["ss_staff_2026_hi"]), "staff_plan": n0(r["ss_staff_plan"]),
        "base_hours": n0(r["base_line_hours"]), "plan_hours": n0(r["plan_line_hours"]),
        "base_hours_lo": n0(r["base_line_hours_lo"]), "base_hours_hi": n0(r["base_line_hours_hi"]),
        "improved_n": n0(r["d_wait_improved_n"]), "nights": n0(r["nights"]),
        "heavy_base": f"{100 * r['base_heavy6_share']:.0f}%",
        "heavy_plan": f"{100 * r['plan_heavy6_share']:.0f}%",
        "inside_peak": n10(r["inside_plan"]), "lim": str(r["density_limit"]),
        "cap_tickets": n0(round(r["cap_tickets"], -2)) if r["cap_tickets"] else "",
        "target_wait": str(r["target_wait"]), "reliability": pct0(r["reliability"]),
        "reliability_rec": pct0(r["reliability_rec"]),
        "low_hour": n0(round(early + 5, -1)),
        "peak_hour": n0(round(r["plan_beers_peak_hour"], -1)),
        "peak_hour_lo": n0(round(r["plan_beers_peak_hour_lo"], -1)),
        "peak_hour_hi": n0(round(r["plan_beers_peak_hour_hi"], -1)),
        "base_peak_hour": n0(round(r["base_beers_peak_hour"], -1)),
        "base_peak_hour_lo": n0(round(r["base_beers_peak_hour_lo"], -1)),
        "base_peak_hour_hi": n0(round(r["base_beers_peak_hour_hi"], -1)),
        "svc_from": r["svc_from"], "svc_to": r["svc_to"],
        "sellers_from": r["sellers_from"], "sellers_to": r["sellers_to"],
        "clip_from": r["clip_from"], "clip_to": r["clip_to"],
        "sims": v["sims"], "hall_side": f"{100 * r['hall_side_uncertainty']:.0f}%",
        "pour_lo": n0(r["pour_2026_lo"]), "pour_hi": n0(r["pour_2026_hi"]),
        "wait_max": n0(r["long_wait_max"]) if r["long_wait_max"] else "",
        "wi_nights": n0(r["wi_plan_nights"]),
        "lim_large": str(r["density_limit_large"]),
    }
    taps, sellers = r["plan_taps"], r["plan_sellers"]
    f["crew_es"], f["crew_en"] = crew_name(taps, sellers, "es"), crew_name(taps, sellers, "en")
    f["min_crew_es"] = crew_name(r["min_taps"], r["min_sellers"], "es")
    f["min_crew_en"] = crew_name(r["min_taps"], r["min_sellers"], "en")
    f.update({"rec_met": str(r["rec_met"]), "rec_nights": str(r["rec_nights"]),
              "min_met": str(r["min_met"]), "min_nights": str(r["min_nights"]),
              "min_bad": up(r["min_wait_bad"]),
              "min_absent_met": str(r["wi_plan_minimum_two_absent_met"]),
              "min_absent_nights": str(r["wi_plan_minimum_two_absent_nights"]),
              "crew_nights": str(r["rec_nights"]),
              "seller_share": pct0(r["plan_seller_share"]),
              "alt_met": str(r["wi_no_sellers_met"]), "alt_nights": str(r["wi_no_sellers_nights"])})
    same = (taps, sellers) == (r["min_taps"], r["min_sellers"])
    alt_ok = r["wi_no_sellers_met"] >= r["reliability"] * r["wi_no_sellers_nights"]
    crews = v["crews"]
    alone = crews[(crews["sellers"] == 0) & (crews["share_met"] >= r["reliability"])]
    for code in ("es", "en"):
        f[f"alt_crew_{code}"] = text["alt_crew"][code]
        rec_key = "rec_fallback" if r["fallback"] else "rec_sentence"
        f[f"rec_sentence_{code}"] = text[rec_key][code].format(**f)
        f[f"min_sentence_{code}"] = "" if same else text["min_sentence"][code].format(
            **{**f, "min_crew_es": f["min_crew_es"], "min_crew_en": f["min_crew_en"]})
        f[f"alt_{code}"] = text["alt_ok" if alt_ok else "alt_none"][code].format(**f)
        f[f"alt_sentence_{code}"] = f[f"alt_{code}"]
        f[f"alone_sentence_{code}"] = (text["alone_sentence"][code].format(**f)
                                       if len(alone) else "")
    ref = r.get("ref_no_limit")
    for code in ("es", "en"):
        if ref and f["wait_max"]:
            ex, lo, hi = ref["obs_exchange_median_min"]
            crew = ref["crew"]
            ref_crew = (crew_name(crew[0], crew[1], code) + (
                f" ({crew[2]} de {crew[3]} noches)" if code == "es" else
                f" ({crew[2]} of {crew[3]} nights)")) if crew else (
                "ninguna opción probada" if code == "es" else "none of the options tested")
            if crew and (crew[0], crew[1]) == (taps, sellers):
                ref_crew = ("el mismo, " if code == "es" else "the same, ") + ref_crew
            f[f"no_limit_{code}"] = text["no_limit"][code].format(
                ref_exchange=n0(ex), ref_exchange_lo=n0(lo), ref_exchange_hi=n0(hi),
                base_exchange=f["base_exchange"], **{f"ref_crew_{code}": ref_crew})
        else:
            f[f"no_limit_{code}"] = ""
        large = r["cap_tickets_large"]
        if large:
            where = (f"cerca de {n0(round(large, -2))} boletos" if code == "es"
                     else f"near {n0(round(large, -2))} tickets")
        else:
            low = min(row["tickets"] for row in v["staffing_rows"])
            where = (f"por debajo de {n0(low)} boletos" if code == "es"
                     else f"below {n0(low)} tickets")
        f[f"cap_large_{code}"] = where
        f[f"cap_strict_{code}"] = text["cap_strict"][code].format(
            lim_large=f["lim_large"], **{f"cap_large_{code}": where})
    known = "cap_sentence_known" if r["cap_tickets"] else "cap_sentence_none"
    for code in ("es", "en"):
        f["cap_range"] = ""
        if r["cap_tickets_lo"] and r["cap_tickets_hi"]:
            f["cap_range"] = text["cap_range"][code].format(
                cap_lo=n0(round(r["cap_tickets_lo"], -2)), cap_hi=n0(round(r["cap_tickets_hi"], -2)))
        f[f"cap_sentence_{code}"] = text[known][code].format(**f)
    f["no_limit"] = f[f"no_limit_{lang}"]
    return f


def serving_section(v, lang, text, f, html_table) -> list[tuple[str, str]]:
    """Serving options (scripts/run_serving.py): a table with the minimum and recommended crew
    of each option and the wait with the plan crew, and the option that saves most hours."""
    sv = v["serving"]
    if sv is None or sv.empty:
        return []

    def short(taps, sellers):
        if taps != taps:                              # NaN: no crew reaches the share
            return text["staff_none"][lang]
        unit = ("puestos", "vendedores") if lang == "es" else ("stations", "sellers")
        return f"{int(taps)} {unit[0]}" + (f" + {int(sellers)} {unit[1]}" if sellers else "")

    rows = []
    for x in sv.itertuples():
        wait = (f"{up(x.plan_crew_wait)} / {up(x.plan_crew_wait_bad)}"
                if x.plan_crew_wait == x.plan_crew_wait else "")
        rows.append((text["serve_option"][x.option][lang], text["serve_assumption"][x.option][lang],
                     short(x.minimum_taps, x.minimum_sellers),
                     short(x.recommended_taps, x.recommended_sellers), wait))
    bottles = sv[sv["option"] == "bottles"].iloc[0]
    # the best option among the central assumptions; the low and high cases give the range
    central = sv[~sv["option"].str.endswith(("_low", "_high"))]
    saved = bottles["recommended_staff_hours"] - central["recommended_staff_hours"]
    best = central.loc[saved.idxmax()]
    if best["option"] != "bottles" and saved.max() >= 1:
        label = text["serve_option"][best["option"]][lang]
        fewer = int(best["recommended_sellers"]) < int(bottles["recommended_sellers"])
        closing = text["serve_best"][lang].format(
            best_label=label[:1].lower() + label[1:],
            best_crew=crew_name(int(best["recommended_taps"]), int(best["recommended_sellers"]),
                                lang),
            hours=n0(saved.max()),
            sellers_note=text["serve_fewer_sellers"][lang].format(
                s=int(best["recommended_sellers"]), b=int(bottles["recommended_sellers"]))
            if fewer else "")
    else:
        closing = text["serve_none"][lang]
    intro = text["serve_intro"][lang].format(serve_nights=n0(bottles["nights"]),
                                             tickets=f["tickets"])
    return [("h2", text["h_serve"][lang]), ("p", intro),
            ("html", html_table(text["serve_head"][lang], rows)), ("p", closing),
            ("p", text["serve_notes"][lang])]


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

    def html_table(head, rows):
        return ("<div class=\"tablewrap\"><table class=\"table\"><thead><tr>"
                + "".join(f"<th>{h}</th>" for h in head) + "</tr></thead><tbody>"
                + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>"
                          for row in rows) + "</tbody></table></div>")

    exchange, total = r["base_obs_exchange_median_min"], r["base_obs_buyer_median_min"]
    scale = max(exchange, total, 1.0)
    gave_up = 10 * r["base_abandon_share"]
    observed, service = (r["obs_from"], r["obs_to"]), (r["svc_from"], r["svc_to"])
    ex_rng = (r["base_obs_exchange_median_min_lo"], r["base_obs_exchange_median_min_hi"])
    tot_rng = (r["base_obs_buyer_median_min_lo"], r["base_obs_buyer_median_min_hi"])

    def both_layouts(draw):
        return (f'<div class="diagram wide">{draw(False)}</div>'
                f'<div class="diagram narrow">{draw(True)}</div>')

    old = both_layouts(lambda narrow: diagrams.old_process(
        lang, exchange, total, r["base_queue_cash_obs"], r["base_queue_pour_obs"], gave_up,
        scale, observed, narrow, exchange_rng=ex_rng, total_rng=tot_rng))
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

    rows = []
    for row in v["staffing_rows"]:
        if row["crew"] is None:
            rows.append((n0(row["tickets"]), text["staff_none"][lang], "", "", "", ""))
            continue
        kind = "fallback" if row["fallback"] else row["level"]
        rows.append((n0(row["tickets"]), text["crew_level"][kind][lang], row["taps"],
                     row["sellers"], f"{row['met']} / {row['nights']}", n10(row["inside"])))
    out += [("h2", t("h_staff")), ("p", t("staff_text")),
            figure(img("summary_crews", t("fig_crews_alt"))),
            ("html", html_table(text["staff_table_head"][lang], rows)),
            figure(img("summary_sales", t("fig_sales_alt")), t("sales_text"))]

    cases = [k for k in WHAT_IF if f"wi_{k}" in r]
    wi_rows = [(text["wi_case"][k][lang], up(r[f"wi_{k}"]),
                f"{r[f'wi_{k}_met']} / {r[f'wi_{k}_nights']}") for k in cases]
    def lower_first(s):
        return s[:1].lower() + s[1:]

    miss = [lower_first(text["wi_case"][k][lang]) for k in cases
            if r[f"wi_{k}_met"] < r["reliability"] * r[f"wi_{k}_nights"]]
    closing = (text["whatif_miss"][lang].format(reliability=f["reliability"],
                                                cases="; ".join(miss))
               if miss else text["whatif_all_ok"][lang].format(reliability=f["reliability"]))
    out += [("p", t("whatif_intro")),
            ("html", html_table(text["whatif_head"][lang], wi_rows)), ("p", closing)]
    out += serving_section(v, lang, text, f, html_table)

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
