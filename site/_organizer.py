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
WHAT_IF = ["plan", "plan_two_absent", "plan_sold_out",
           "plan_thirsty", "plan_slow_pay", "plan_late_sellers", "plan_slow_refill", "no_sellers"]


def n0(x):
    return f"{x:,.0f}"


def n10(x):
    """Rounded to the nearest 10, for counts of people."""
    return f"{round(x, -1):,.0f}"


def up(x):
    """Whole minutes, rounded up, for statements of the form "x minutes or less"."""
    return f"{math.ceil(x - 1e-9):,d}"


def crew_short(taps: int, sellers: int, lang: str) -> str:
    if lang == "es":
        return f"{taps} puestos y {sellers} vendedores" if sellers else f"{taps} puestos, sin vendedores"
    return f"{taps} stations and {sellers} sellers" if sellers else f"{taps} stations, no sellers"


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
        "d_beers": n0(r["d_beers_med"]), "d_beers_lo": n0(r["d_beers_lo"]),
        "d_beers_hi": n0(r["d_beers_hi"]), "d_mxn": n0(round(r["d_beers_med"] * price, -3)),
        "d_mxn_lo": n0(round(r["d_beers_lo"] * price, -3)),
        "d_mxn_hi": n0(round(r["d_beers_hi"] * price, -3)),
        "per_hour": n0(r["ss_beers_per_extra_hour"]),
        "per_hour_lo": n0(r["ss_p05"]), "per_hour_hi": n0(r["ss_p95"]),
        "extra_hours": n0(r["ss_extra_hours"]),
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
        "pour_lo": str(r["pour_interval_lo"]), "pour_hi": str(r["pour_interval_hi"]),
        "wait_max": n0(r["long_wait_max"]) if r["long_wait_max"] else "",
        "wi_nights": n0(r["wi_plan_nights"]),
        "lim_large": str(r["density_limit_large"]),
        "date": report_values.long_date(r["date"], lang), "author": r["author"],
        "festival_url": r["festival_url"],
        "contact_label": r["contact_label"], "contact_url": r["contact_url"],
        "max_sellers": str(r["max_sellers"]),
        "chk_beers": n0(round(r["base_beers_total"], -2)),
        "chk_beers_lo": n0(round(r["base_beers_total_lo"], -2)),
        "chk_beers_hi": n0(round(r["base_beers_total_hi"], -2)),
        "chk_tickets": n0(r["model_tickets"]),
        "chk_inside": n10(r["base_peak_occupancy"]),
        "chk_inside_lo": n10(r["base_peak_occupancy_lo"]),
        "chk_inside_hi": n10(r["base_peak_occupancy_hi"]),
        "chk_pour_lo": str(r["pour_interval_lo"]), "chk_pour_hi": str(r["pour_interval_hi"]),
        "chk_pour_k": str(r["pour_interval_k"]), "chk_pour_n": str(r["pour_interval_n"]),
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
              "seller_share_lo": pct0(r["plan_seller_share_lo"]),
              "seller_share_hi": pct0(r["plan_seller_share_hi"]),
              "rec_absent_met": str(r["wi_plan_two_absent_met"]),
              "rec_absent_nights": str(r["wi_plan_two_absent_nights"]),
              "alt_met": str(r["wi_no_sellers_met"]), "alt_nights": str(r["wi_no_sellers_nights"])})
    same = (taps, sellers) == (r["min_taps"], r["min_sellers"])
    close = abs(r["rec_met"] - r["min_met"]) <= 0.05 * r["rec_nights"]
    edge = r["max_sellers"] in (sellers, r["min_sellers"])
    alt_ok = r["wi_no_sellers_met"] >= r["reliability"] * r["wi_no_sellers_nights"]
    crews = v["crews"]
    alone = crews[(crews["sellers"] == 0) & (crews["share_met"] >= r["reliability"])]
    for code in ("es", "en"):
        f[f"alt_crew_{code}"] = text["alt_crew"][code]
        rec_key = "rec_fallback" if r["fallback"] else "rec_sentence"
        f[f"rec_sentence_{code}"] = text[rec_key][code].format(**f)
        f[f"min_crew_short_{code}"] = crew_short(r["min_taps"], r["min_sellers"], code)
        f[f"min_close_{code}"] = text["min_close"][code] if close else ""
        f[f"grows_{code}"] = text["min_grows"]["close" if close else "apart"][code]
        f[f"min_sentence_{code}"] = "" if same else text["min_sentence"][code].format(**f)
        f[f"grid_edge_{code}"] = text["grid_edge"][code].format(**f) if edge else ""
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
            plan_ref = ref.get("plan_crew") or ("", "")
            f[f"no_limit_{code}"] = text["no_limit"][code].format(
                ref_exchange=n0(ex), ref_exchange_lo=n0(lo), ref_exchange_hi=n0(hi),
                base_exchange=f["base_exchange"], ref_plan_met=plan_ref[0],
                ref_plan_nights=plan_ref[1], **{f"ref_crew_{code}": ref_crew})
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
                cap_lo=n0(round(r["cap_tickets_lo"], -2)), cap_hi=n0(round(r["cap_tickets_hi"], -2)),
                hall_side=f["hall_side"])
        f[f"cap_sentence_{code}"] = text[known][code].format(**f)
    f["no_limit"] = f[f"no_limit_{lang}"]
    return f


def what_if_status(r: dict, k: str) -> str:
    """met: share of nights at the reliability or above; near: below it, with the upper limit
    of the 95% Clopper-Pearson interval at the reliability or above; far: upper limit below."""
    share = r[f"wi_{k}_met"] / r[f"wi_{k}_nights"]
    if share >= r["reliability"]:
        return "met"
    return "near" if r[f"wi_{k}_met_hi"] >= r["reliability"] else "far"


SINGLE = ["baseline", "more_cashiers", "pay_at_tap", "sellers_6", "plan"]


def single_changes(v, lang, text, html_table) -> list[tuple[str, str]]:
    """Each change on its own against 2026 (main scenarios, same nights): additional people on
    beer, the wait of 9 of 10 buyers and the additional beers, each with the range between
    nights (5% to 95%)."""
    r, m, eff = v["raw"], v["scenario_metrics"], v["effects"]
    rng = text["single_range"][lang]

    def with_range(x, fmt):
        lo, med, hi = (fmt(q) for q in x.quantile([0.05, 0.5, 0.95]))
        return med if lo == hi else rng.format(v=med, lo=lo, hi=hi)

    base = m[m["scenario"] == "baseline"].set_index("draw")
    rows = []
    for k in SINGLE:
        x = m[m["scenario"] == k].set_index("draw")
        wait = with_range(x["evening_p90_min"], up)          # rounded up, as in the what-if table
        if k == "baseline":
            staff = text["single_base_staff"][lang].format(v=rng.format(
                v=n0(r["ss_staff_2026"]), lo=n0(r["ss_staff_2026_lo"]),
                hi=n0(r["ss_staff_2026_hi"])))
            beers = text["single_base_beers"][lang].format(v=rng.format(
                v=n0(r["base_beers_total"]), lo=n0(r["base_beers_total_lo"]),
                hi=n0(r["base_beers_total_hi"])))
        else:
            staff = with_range(x["staff"] - base["staff"].reindex(x.index),
                               lambda q: f"{q:+.0f}".replace("+0", "0"))
            e = eff[(eff["scenario"] == k) & eff["outcome"].str.startswith("Beers")].iloc[0]
            beers = rng.format(v=f"{e['med']:+,.0f}", lo=f"{e['lo']:+,.0f}",
                               hi=f"{e['hi']:+,.0f}")
        row = (text["single_case"][k][lang], staff, wait, beers)
        if k == "plan":
            row = tuple(f"<strong>{c}</strong>" for c in row)
        rows.append(row)
    nights = n0(base.index.nunique())
    return [("h2", text["h_single"][lang]),
            ("p", text["single_intro"][lang].format(nights=nights)),
            ("html", html_table(text["single_head"][lang], rows)),
            ("p", text["single_text"][lang]), ("links", text["single_more"][lang])]


def serving_section(v, lang, text, f, html_table) -> list[tuple[str, str]]:
    """Serving options (scripts/run_serving.py): with the plan crew, the wait and the nights
    that meet the target; and the working hours saved by the fewest-hours crew that meets the
    target in 95% of nights, against serving in cups."""
    sv = v["serving"]
    if sv is None or sv.empty:
        return []
    bottles = sv[sv["option"] == "bottles"].iloc[0]
    saved_all = bottles["recommended_staff_hours"] - sv.set_index("option")[
        "recommended_staff_hours"]
    rows = []
    for x in sv[~sv["option"].str.endswith(("_low", "_high"))].itertuples():
        has = x.plan_crew_wait == x.plan_crew_wait
        rows.append((f'{text["serve_option"][x.option][lang]} <span class="check">'
                     f'({text["serve_assumption"][x.option][lang]})</span>',
                     f"{up(x.plan_crew_wait)} / {up(x.plan_crew_wait_bad)}" if has else "",
                     f"{int(x.plan_crew_met)} / {int(x.nights)}" if has else "",
                     n0(max(saved_all[x.option], 0))))
    central = sv[~sv["option"].str.endswith(("_low", "_high"))].set_index("option")
    saved = saved_all[central.index]
    best = saved.idxmax()
    if best != "bottles" and saved.max() >= 1:
        label = text["serve_option"][best][lang]
        closing = text["serve_best"][lang].format(best_label=label[:1].lower() + label[1:],
                                                  hours=n0(saved.max()))
    else:
        closing = text["serve_none"][lang]
    if {"cans_low", "cans_high"} <= set(saved_all.index):
        saving = report_values.serving_savings()
        closing += " " + text["serve_cans_range"][lang].format(
            low_s=n0(saving["cans_low"]), high_s=n0(saving["cans_high"]),
            low_hours=n0(max(saved_all["cans_low"], 0)),
            high_hours=n0(max(saved_all["cans_high"], 0)))
    intro = text["serve_intro"][lang].format(serve_nights=n0(bottles["nights"]),
                                             tickets=f["tickets"])
    return [("h2", text["h_serve"][lang]), ("p", intro),
            ("html", html_table(text["serve_head"][lang], rows)), ("p", closing),
            ("p", text["serve_notes"][lang])]


SITE_URL = "https://jospablo777.github.io/orus_fest_beer_sales_simulation/"
SUMMARY_CHANGES = ["baseline", "more_cashiers", "pay_at_tap", "sellers_6", "plan"]


class Page:
    """Shared values and HTML helpers of the organizer pages in one language."""

    def __init__(self, lang: str):
        self.lang = lang
        self.text = yaml.safe_load((SITE / "_text.yaml").read_text(encoding="utf-8"))
        self.v = report_values.compute()
        self.r = self.v["raw"]
        self.f = fields(self.v, lang, self.text)
        self.f.update(extra_fields(self.v, lang, self.text, self.f))

    def t(self, key):
        return self.text[key][self.lang].format(**self.f)

    def figure(self, inner, caption=None, cls="plain-figure"):
        cap = f"<figcaption>{caption}</figcaption>" if caption else ""
        return ("html", f'<figure class="{cls}">{inner}{cap}</figure>')

    def img(self, name, alt):
        return (f'<img src="assets/figures/{name}_{self.lang}.png" alt="{alt}" '
                f'loading="lazy">')

    def chart(self, name, alt):
        """Wide image, and the narrow one for phones (scripts/make_summary.py)."""
        return (f'<div class="diagram wide">{self.img(name, alt)}</div>'
                f'<div class="diagram narrow">{self.img(f"{name}_narrow", alt)}</div>')

    def one_video(self, name, label, cls, extra=""):
        lang = self.lang
        return (f'<video class="{cls}" controls preload="none" playsinline {extra}'
                f'poster="assets/video/{name}_{lang}.jpg" '
                f'src="assets/video/{name}_{lang}.mp4" aria-label="{label}"></video>')

    def video(self, name, label, phone=None, extra=""):
        """Both floor panels with the charts, and the cut with the floor panels for phones."""
        return (self.one_video(name, label, "video-wide", extra)
                + self.one_video(phone or f"{name}_phone", label, "video-phone", extra))

    @staticmethod
    def html_table(head, rows):
        """Below 600 px wide each row is shown as a block of label and value (data-label)."""
        def cell(h, c):
            return f'<td data-label="{h}">{c}</td>'
        return ("<div class=\"tablewrap\"><table class=\"table stack\"><thead><tr>"
                + "".join(f"<th>{h}</th>" for h in head) + "</tr></thead><tbody>"
                + "".join("<tr>" + "".join(cell(h, c) for h, c in zip(head, row)) + "</tr>"
                          for row in rows) + "</tbody></table></div>")

    @staticmethod
    def both_layouts(draw):
        return (f'<div class="diagram wide">{draw(False)}</div>'
                f'<div class="diagram narrow">{draw(True)}</div>')

    def lead(self, key):
        return ("html", f'<p class="lead-claim"><strong>{self.t(key)}</strong></p>')


def extra_fields(v: dict, lang: str, text: dict, f: dict) -> dict:
    """Values of the summary and evidence pages that fields() does not give."""
    r, m = v["raw"], v["scenario_metrics"]
    base = m[m["scenario"] == "baseline"].set_index("draw")["evening_p90_min"]
    tap = m[m["scenario"] == "pay_at_tap"].set_index("draw")["evening_p90_min"]
    cut = (100 * (base - tap.reindex(base.index)) / base).dropna()
    med = {k: float(m.loc[m["scenario"] == k, "evening_p90_min"].median())
           for k in ("more_cashiers", "pay_at_tap")}
    out = {"tap_pct": n0(cut.median()), "tap_pct_lo": n0(cut.quantile(0.05)),
           "tap_pct_hi": n0(cut.quantile(0.95)),
           "plan_wait_lo": up(max(r["plan_obs_median_min_lo"], 1)),
           "plan_wait_hi": up(max(r["plan_obs_median_min_hi"], 1)),
           "extra_staff": n0(r["ss_staff_plan"] - r["ss_staff_2026"]),
           "inside_2026": n10(r["base_peak_occupancy"]),
           "best_single": n0(min(med.values())),
           "plan_taps": str(r["plan_taps"]), "plan_sellers": str(r["plan_sellers"]),
           "full_met": str(r["full_met"]), "full_nights": str(r["full_nights"]),
           "full_more": n0(r["full_staff"] - r["rec_staff"]),
           "counter_m": f"{r['counter_m_plan']:.1f}",
           "counter_flag": text["ev_counter_flag"][lang] if r["counter_m_plan"] < 1.0 else "",
           "surcharge": n0(r["surcharge"]), "paying": n0(r["paying_tickets"]),
           "budget": n0(r["surcharge"] * r["paying_tickets"]),
           "cost_limit": n0(r["cost_limit_full"]) if r["cost_limit_full"] else "",
           "busy_base": r["busy_base"], "busy_plan": r["busy_plan"]}
    # what-ifs of the plan crew itself (the minimum crew and the option without sellers are
    # other crews)
    cases = [k for k in WHAT_IF if f"wi_{k}" in r
             and k not in ("plan", "plan_minimum", "plan_minimum_two_absent", "no_sellers")]
    worst = min(cases, key=lambda k: r[f"wi_{k}_met"])
    out.update({"wi_ok": str(sum(what_if_status(r, k) == "met" for k in cases)),
                "wi_cases": str(len(cases)),
                "wi_worst": text["wi_case"][worst][lang][:1].lower()
                + text["wi_case"][worst][lang][1:],
                "wi_worst_met": str(r[f"wi_{worst}_met"])})
    for k in ("alt_taps", "alt_sellers", "alt_base", "alt_worst", "alt_nights"):
        out[k] = str(r.get(k, ""))
    out.update({"tickets_plus25": n0(round(r["tickets"] * 1.25)),
                "full_plus25": str(r.get("complete_plus25_met", "")),
                "rec_plus25": str(r.get("recommended_plus25_met", ""))})
    out["tap_range_touches_zero"] = cut.quantile(0.05) <= 0
    for code in ("es", "en"):
        out[f"price_note_{code}"] = text["price_note"][code].format(price=n0(r["price"]))
    out.update({"min_worst": str(r.get("minimum_worst_met", "")),
                "rec_worst": str(r.get("recommended_worst_met", "")),
                "full_worst": str(r.get("complete_worst_met", ""))})
    out["full_crew_es"] = crew_name(r["full_taps"], r["full_sellers"], "es")
    out["full_crew_en"] = crew_name(r["full_taps"], r["full_sellers"], "en")
    return out


def summary_pieces(lang: str) -> list[tuple[str, str]]:
    """The summary page. Kinds: "html", "h2", "p", "button" (link to the evidence page)."""
    pg = Page(lang)
    r, t = pg.r, pg.t
    out = [("html", f'<p class="byline"><a href="{r["contact_url"]}">{r["author"]}</a></p>')]
    ba = pg.both_layouts(lambda narrow: diagrams.before_after(
        lang, pg.f, r["plan_taps"], r["plan_sellers"], narrow))
    out += [("h2", t("sum_h_problem")), ("p", t("sum_problem")), pg.figure(ba)]
    gain1 = "sum_card1_gain_some" if pg.f["tap_range_touches_zero"] else "sum_card1_gain"
    gains = {1: t(gain1), 2: t("sum_card2_gain"), 3: t("sum_card3_gain")}
    cards = "".join(
        f'<div class="card"><strong>{t(f"sum_card{k}")}</strong>'
        f'<span class="gain">{gains[k]}</span></div>' for k in (1, 2, 3))
    out += [("h2", t("sum_h_do")), ("html", f'<div class="cards">{cards}</div>')]
    bigs = [(f"40+ → {pg.f['plan_wait']} min", t("sum_big_wait_l"), t("sum_big_wait_r")),
            (t("sum_big_beers_v"), t("sum_big_beers_l"), t("sum_big_beers_r")),
            (t("sum_big_staff_v"), t("sum_big_staff_l"), t("sum_big_staff_r"))]
    big = "".join(f'<div class="big"><span class="v">{a}</span><span class="l">{b}</span>'
                  f'<span class="rng">{c}</span></div>' for a, b, c in bigs)
    same = (r["full_taps"], r["full_sellers"]) == (r["plan_taps"], r["plan_sellers"])
    anchor = "evidencia.qmd" if lang == "es" else "evidence.qmd"
    out += [("h2", t("sum_h_total")), ("html", f'<div class="bigs">{big}</div>'),
            ("p", t("sum_levels_same" if same else "sum_levels")),
            ("html", f'<p class="method"><a href="{anchor.replace(".qmd", ".html")}'
                     f'#como-se-hizo">{t("sum_method")}</a></p>')]
    phone = ("night_2026_vs_plan_phone_light"
             if (SITE / "assets" / "video" / f"night_2026_vs_plan_phone_light_{lang}.mp4")
             .exists() else None)
    vid = pg.video("night_2026_vs_plan", t("sum_video_cap"), phone,
                   extra='muted loop data-autoplay="1" ')
    out += [("h2", t("sum_h_video")), pg.figure(vid, t("sum_video_cap")),
            ("html", AUTOPLAY_SCRIPT),
            pg.figure(pg.chart("summary_wait", t("fig_wait_alt")), t("sum_wait_cap"))]
    need = "".join(f"<li>{q}</li>" for q in pg.text["sum_need"][lang])
    out += [("h2", t("sum_h_need")),
            ("html", f'<div class="needs quick"><ul>{need}</ul><p>{t("sum_contact")}</p></div>'),
            ("button", (anchor, t("sum_button"))), ("p", t("sum_note"))]
    return out


# The night video plays muted on its own unless the reader's system asks for reduced
# motion; only the cut shown at the current width is started.
AUTOPLAY_SCRIPT = """<script>
(function () {
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  document.querySelectorAll("video[data-autoplay]").forEach(function (v) {
    if (v.offsetParent === null) return;
    v.muted = true;
    v.preload = "auto";
    var p = v.play();
    if (p && p.catch) p.catch(function () {});
  });
})();
</script>"""


def evidence_pieces(lang: str) -> list[tuple[str, str]]:
    """The evidence page, eleven sections, each opening with its conclusion."""
    pg = Page(lang)
    v, r, f, t, text = pg.v, pg.r, pg.f, pg.t, pg.text
    exchange, total = r["base_obs_exchange_median_min"], r["base_obs_buyer_median_min"]
    scale = max(exchange, total, 1.0)
    observed, service = (r["obs_from"], r["obs_to"]), (r["svc_from"], r["svc_to"])
    ex_rng = (r["base_obs_exchange_median_min_lo"], r["base_obs_exchange_median_min_hi"])
    tot_rng = (r["base_obs_buyer_median_min_lo"], r["base_obs_buyer_median_min_hi"])
    old = pg.both_layouts(lambda narrow: diagrams.old_process(
        lang, exchange, total, r["base_queue_cash_obs"], r["base_queue_pour_obs"],
        10 * r["base_abandon_share"], scale, observed, narrow, exchange_rng=ex_rng,
        total_rng=tot_rng, pourers=round(r["pour_2026"])))
    new = pg.both_layouts(lambda narrow: diagrams.new_process(
        lang, max(r["plan_obs_median_min"], 1), r["plan_evening_p90_min"], r["plan_taps"],
        r["plan_sellers"], scale, observed, service, narrow))
    out = [("h2", t("ev_h1")), pg.lead("ev_lead1"), pg.figure(old), ("p", t("ev_text1")),
           pg.figure(new), ("p", t("new_text"))]

    out += [("h2", t("ev_h2")), pg.lead("ev_lead2"),
            pg.figure(pg.video("night_2026_vs_plan", t("video_night")), t("video_night")),
            pg.figure(pg.video("changeover_2026_vs_plan", t("video_change")),
                      t("video_change"))]

    single = single_changes(v, lang, text, pg.html_table)
    out += [("h2", t("ev_h3")), pg.lead("ev_lead3"),
            pg.figure(pg.chart("summary_changes", t("ev_h3")), t("ev_changes_cap")),
            ("p", single[1][1]), single[2], ("p", single[3][1]), single[4]]

    rows = []
    for row in v["staffing_rows"]:
        if row["crew"] is None:
            rows.append((n0(row["tickets"]), text["staff_none"][lang], "", ""))
            continue
        kind = "fallback" if row["fallback"] else row["level"]
        people = "personas" if lang == "es" else "people"
        rows.append((n0(row["tickets"]), text["crew_level"][kind][lang],
                     f"{row['taps']} + {row['sellers']} · {n0(row['staff'])} {people} · "
                     f"{n0(row['staff_hours'])} h", f"{row['met']} / {row['nights']}"))
    out += [("h2", t("ev_h4")), pg.lead("ev_lead4"),
            pg.figure(pg.img("summary_plan", t("plan_alt")), t("ev_plan_legend"),
                      cls="plain-figure plan-figure"),
            ("p", t("ev_levels")),
            pg.figure(pg.chart("summary_mixes", t("ev_mixes_cap")), t("ev_mixes_cap")),
            ("p", t("ev_counter") + (" " + t("ev_counter_alt") if r.get("alt_taps") else "")),
            pg.figure(pg.chart("summary_crews", t("fig_crews_alt")), t("ev_crews_cap")),
            ("p", t("staff_text")),
            ("html", pg.html_table(text["staff_table_head_short"][lang], rows)),
            ("p", t("staff_intro")), ("p", t("ev_surcharge"))]

    small = "".join(f'<div class="small-num"><span class="v">{a.format(**f)}</span>'
                    f'<span class="l">{b.format(**f)}</span></div>'
                    for a, b in text["ev_small"][lang])
    out += [("h2", t("ev_h5")), pg.lead("ev_lead5"),
            pg.figure(pg.chart("summary_wait", t("fig_wait_alt")), t("wait_caption")),
            pg.figure(pg.chart("summary_sales", t("fig_sales_alt")), t("sales_text")),
            pg.figure(pg.chart("summary_busy", t("ev_busy_cap")), t("ev_busy_cap")),
            ("html", f'<div class="small-nums">{small}</div>')]

    cases = [k for k in WHAT_IF if f"wi_{k}" in r]
    wi_rows = [(text["wi_case"][k][lang], up(r[f"wi_{k}"]),
                f"{r[f'wi_{k}_met']} / {r[f'wi_{k}_nights']}",
                text["wi_status"][what_if_status(r, k)][lang]) for k in cases]
    out += [("h2", t("ev_h6")), pg.lead("ev_lead6"),
            ("html", pg.html_table(text["whatif_head"][lang], wi_rows)),
            ("p", t("whatif_intro"))]

    serve = serving_section(v, lang, text, f, pg.html_table)
    out += [("h2", t("ev_h7")), pg.lead("ev_lead7")] + serve[1:]

    out += [("h2", t("ev_h8")), pg.lead("ev_lead8"),
            ("html", f'<div class="confs"><div class="conf"><strong>{t("a5_t")}</strong>'
                     f'<span>{t("a5")}</span></div><div class="conf"><strong>{t("a6_t")}'
                     f'</strong><span>{t("a6")}</span></div></div>')]

    conf = "".join(f'<div class="conf {k}"><strong>{t(f"conf_{k}_t")}</strong>'
                   f'<span>{t(f"conf_{k}")}' + (f' {t("ev_crew_rule")}' if k == "prob" else "")
                   + '</span></div>' for k in ("firm", "prob", "check"))
    out += [("h2", t("ev_h9")), pg.lead("ev_lead9"), ("html", f'<div class="confs">{conf}</div>')]

    checks = [e.format(**f) for e in text["need_estimates"][lang]]
    needs = "".join(f"<li>{item}" + (f' <span class="check">{checks[k]}</span>'
                                     if k < len(checks) else "") + "</li>"
                    for k, item in enumerate(text["needs"][lang]))
    quick = "".join(f'<li><strong>{q}</strong> <span class="check">{why}</span></li>'
                    for q, why in text["need_quick"][lang])
    out += [("h2", t("ev_h10")), pg.lead("ev_lead10"),
            ("html", f'<div class="needs quick"><p>{t("need_quick_lead")}</p><ul>{quick}</ul>'
                     f'</div>'),
            ("html", f'<div class="needs"><p>{t("need_text")}</p><p>{t("need_check")}</p>'
                     f'<ol>{needs}</ol></div>')]

    out += [("h2id", (t("ev_h11"), "como-se-hizo")), pg.lead("ev_lead11"),
            ("p", t("how_text")), ("links", t("links"))]
    return out


PAGES = {"summary": summary_pieces, "evidence": evidence_pieces}


def _button_md(target):
    href, label = target
    return f'\n[{label}]({href}){{.btn .btn-primary .evidence-button}}\n'


def render(lang: str, page: str = "summary") -> str:
    """Quarto markdown of a page, included by site/index.qmd, en.qmd, evidencia.qmd and
    evidence.qmd."""
    form = {"html": "\n```{{=html}}\n{}\n```\n", "h2": "\n## {}\n", "p": "\n{}\n",
            "links": "\n{}\n"}
    parts = []
    for kind, content in PAGES[page](lang):
        if kind == "button":
            parts.append(_button_md(content))
        elif kind == "h2id":
            parts.append(f"\n## {content[0]} {{#{content[1]}}}\n")
        else:
            parts.append(form[kind].format(content))
    return "".join(parts)


def render_html(lang: str, page: str = "summary") -> str:
    """A page as plain HTML without the links to the technical pages, for the single-file
    preview built by scripts/make_preview.py. The evidence button points to the site."""
    form = {"html": "{}\n", "h2": "<h2>{}</h2>\n", "p": "<p>{}</p>\n", "links": ""}
    parts = []
    for kind, content in PAGES[page](lang):
        if kind == "button":
            href = SITE_URL + content[0].replace(".qmd", ".html")
            parts.append(f'<p><a class="evidence-button" href="{href}">{content[1]}</a></p>\n')
        elif kind == "h2id":
            parts.append(f'<h2 id="{content[1]}">{content[0]}</h2>\n')
        else:
            parts.append(form[kind].format(content))
    return "".join(parts)


def running_words(lang: str = "es") -> int:
    """Words of running text on the summary page: paragraphs, card text, numbers' labels and
    the questions; captions, the method line, the diagram and the byline do not count."""
    import re
    words = 0
    for kind, content in summary_pieces(lang):
        if kind == "p":
            words += len(re.sub(r"<[^>]+>", " ", content).split())
        elif kind == "button":
            words += len(content[1].split())
        elif kind == "html" and ('class="cards"' in content or 'class="bigs"' in content
                                 or 'class="needs' in content):
            words += len(re.sub(r"<[^>]+>", " ", content).split())
    return words
