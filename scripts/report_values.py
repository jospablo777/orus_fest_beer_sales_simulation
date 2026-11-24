"""Numbers shown on the site, read from output/tables and output/runs.

compute() returns a dict used by site/_organizer.py (organizer pages in Spanish and English)
and by site/technical.qmd, so every page shows the same values.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sim import params, staffing  # noqa: E402
from sim.venue import Venue  # noqa: E402

ROOT = params.ROOT
TAB = ROOT / "output" / "tables"
RUNS = ROOT / "output" / "runs"


def n0(x):
    return f"{x:,.0f}"


def n1(x):
    return f"{x:,.1f}"


def pct(x):
    return f"{100 * x:.0f}%"


def table(name):
    return pd.read_csv(TAB / name)


def hourly_sales(series: pd.DataFrame, scenario: str) -> pd.DataFrame:
    """Beers sold per clock hour: median and 5% to 95% of the nights."""
    s = series[series["scenario"] == scenario].sort_values(["draw", "clock_min"]).copy()
    s["hour"] = (s["clock_min"] // 60).astype(int)
    last = s.groupby(["draw", "hour"])["beers_total"].max().unstack("hour")
    per_hour = last.diff(axis=1)
    per_hour.iloc[:, 0] = last.iloc[:, 0]
    out = per_hour.quantile([0.05, 0.5, 0.95]).T
    out.columns = ["lo", "med", "hi"]
    out["clock"] = [f"{h % 24:02d}:00" for h in out.index]
    out = out.reset_index()
    return out[out["hour"] < 27]            # the event closes at 03:00


def crew_rows(plan: pd.DataFrame, levels) -> list[dict]:
    """Minimum and recommended crew per ticket level, as dicts for the page tables. A level
    without any crew gets one row with crew None."""
    rows = []
    for level in sorted(levels):
        got = plan[plan["n_total"] == level]
        if got.empty:
            rows.append({"tickets": level, "crew": None, "level": None})
            continue
        for kind in ("minimum", "recommended", "complete"):
            if not (got["level"] == kind).any():
                continue
            r = got[got["level"] == kind].iloc[0]
            rows.append({
                "tickets": level, "crew": kind, "level": kind, "taps": int(r["n_pour"]),
                "sellers": int(r["sellers"]), "met": int(r["nights_met"]),
                "nights": int(r["nights"]), "share_lo": float(r["share_lo"]),
                "share_hi": float(r["share_hi"]), "wait_median": float(r["wait_median"]),
                "wait_bad": float(r["wait_bad_night"]), "inside": float(r["inside_peak"]),
                "density": float(r["floor_density"]), "staff_hours": float(r["staff_hours"]),
                "staff": float(r["staff"]),
                "fallback": bool(r["fallback"])})
    return rows


def shortest_interval(values: pd.Series, share: float = 0.9) -> tuple[int, int, int, int]:
    """Narrowest range of whole numbers [lo, hi] that holds at least `share` of the values,
    as (lo, hi, values inside, values). Ties go to the range that holds more values."""
    x = values.round().astype(int)
    levels = sorted(x.unique())
    best = None
    for i, lo in enumerate(levels):
        for hi in levels[i:]:
            k = int(x.between(lo, hi).sum())
            if k >= share * len(x):
                key = (hi - lo, -k)
                if best is None or key < best[0]:
                    best = (key, (int(lo), int(hi), k, len(x)))
                break
    return best[1]


def counter_per_station(n_pour: int) -> float:
    """Meters of counter per station between pour_x_min and pour_x_max, without the gap left
    at the cocktail line (sim/venue.py: station_x)."""
    base = params.load()
    b, c = base["bar"], base["venue"].get("cocktail_line")
    length = b["pour_x_max"] - b["pour_x_min"]
    if c and b["pour_x_min"] < c["x"] < b["pour_x_max"]:
        length -= 2 * (c["half_width"] + 0.7)
    return length / n_pour


def serving_savings() -> dict:
    """Seconds saved per beer by each serving option of config/serving.yaml."""
    options = params.load(ROOT / "config" / "serving.yaml")["options"]
    return {k: float(o["overrides"].get("bar.pour_saving_s", 0.0)) for k, o in options.items()}


MONTHS = {"es": ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
                 "septiembre", "octubre", "noviembre", "diciembre"],
          "en": ["January", "February", "March", "April", "May", "June", "July", "August",
                 "September", "October", "November", "December"]}


def long_date(iso: str, lang: str) -> str:
    """"2026-11-24" as "24 de noviembre de 2026" or "24 November 2026", without the locale."""
    year, month, day = (int(p) for p in str(iso).split("-"))
    name = MONTHS[lang][month - 1]
    return f"{day} de {name} de {year}" if lang == "es" else f"{day} {name} {year}"


def reference_values(name: str, stf_cfg: dict, tickets: int) -> dict | None:
    """2026 estimates and the recommended crew of a reference run in output/sensitivity."""
    ref = ROOT / "output" / "sensitivity" / name / "runs"
    if not ref.is_dir():
        return None
    m = pd.read_csv(ref / "scenario_metrics.csv")
    base = m[m["scenario"] == "baseline"]
    out = {}
    for col in ("obs_exchange_median_min", "obs_buyer_median_min"):
        out[col] = (float(base[col].median()), float(base[col].quantile(0.05)),
                    float(base[col].quantile(0.95)))
    summ = staffing.summarize(pd.read_csv(ref / "staffing_grid.csv"), stf_cfg["service_target"])
    summ = summ[summ["n_total"].isin(stf_cfg["grid"]["crowd.n_total"])]
    pt = staffing.plan_table(summ, stf_cfg["reliability"],
                             stf_cfg.get("reliability_recommended", stf_cfg["reliability"]))
    rec = pt[(pt["n_total"] == tickets) & (pt["level"] == "recommended")]
    out["crew"] = (None if rec.empty else
                   (int(rec["n_pour"].iloc[0]), int(rec["sellers"].iloc[0]),
                    int(rec["nights_met"].iloc[0]), int(rec["nights"].iloc[0])))
    plan = staffing.plan_crew(tickets)
    hit = summ[(summ["n_total"] == tickets) & (summ["n_pour"] == plan["plan_taps"])
               & (summ["sellers"] == plan["plan_sellers"])]
    out["plan_crew"] = (None if hit.empty else
                        (int(hit["nights_met"].iloc[0]), int(hit["nights"].iloc[0])))
    return out


def mixes_values(tickets: int, plan_taps: int, plan_sellers: int) -> dict:
    """From output/tables/crew_mixes.csv at a ticket level: the recommended and complete
    crews under 25% more tickets, and the best candidate of the recommended level with fewer
    stations than the plan (base nights and worst stress case)."""
    path = TAB / "crew_mixes.csv"
    if not path.exists():
        return {}
    mx = pd.read_csv(path)
    mx = mx[mx["n_total"] == tickets]
    out = {}
    for level in ("recommended", "complete"):
        c = mx[(mx["level"] == level) & mx["chosen"] & (mx["case"] == "tickets_plus_25")]
        if len(c):
            out[f"{level}_plus25_met"] = int(c["nights_met"].iloc[0])
            out[f"{level}_plus25_nights"] = int(c["nights"].iloc[0])
    rec = mx[(mx["level"] == "recommended") & (mx["n_pour"] < plan_taps)]
    if len(rec):
        g = rec.groupby(["n_pour", "sellers"])
        worst = rec[rec["case"] != "base"].groupby(["n_pour", "sellers"])["nights_met"].min()
        base = rec[rec["case"] == "base"].set_index(["n_pour", "sellers"])["nights_met"]
        best = worst.sort_values(ascending=False).index[0]
        out.update({"alt_taps": int(best[0]), "alt_sellers": int(best[1]),
                    "alt_base": int(base.loc[best]), "alt_worst": int(worst.loc[best]),
                    "alt_nights": int(g["nights"].first().loc[best])})
    return out


def compute() -> dict:
    report_cfg = params.load(ROOT / "config" / "report.yaml")
    stf_cfg = params.load(ROOT / "config" / "staffing.yaml")
    cal_cfg = params.load(ROOT / "config" / "calibration.yaml")
    base_cfg = params.load()
    price = report_cfg["beer_price_mxn"]
    head = report_cfg["headline_scenario"]
    tickets = int(report_cfg["plan_tickets"])
    target = stf_cfg["service_target"]

    cal = table("calibration_summary.csv").iloc[0]
    eff = table("counterfactual_effects.csv")
    cmp_ = table("comparisons.csv")
    rev = table("counterfactual_2026_revenue.csv").iloc[0]
    wi = table("what_if.csv").set_index("scenario")
    rel = table("staffing_reliability.csv")
    plan = table("staffing_plan.csv")
    cap = table("capacity.csv").sort_values("n_total")
    ar = table("arimax_sales.csv")
    reg = table("calibration_regressions.csv")
    met = pd.read_csv(RUNS / "scenario_metrics.csv")
    series = pd.read_csv(RUNS / "scenario_series.csv")
    post = pd.read_csv(RUNS / "posterior_draws.csv")

    def med(scn, col):
        return float(met.loc[met["scenario"] == scn, col].median())

    def rng(scn, col):
        x = met.loc[met["scenario"] == scn, col]
        return float(x.quantile(0.05)), float(x.quantile(0.95))

    def effect(scn, prefix):
        return eff[(eff["scenario"] == scn) & eff["outcome"].str.startswith(prefix)].iloc[0]

    def compare(first, second, outcome):
        return cmp_[(cmp_["first"] == first) & (cmp_["second"] == second)
                    & (cmp_["outcome"] == outcome)].iloc[0]

    at_level = plan[plan["n_total"] == tickets].set_index("level")
    crew, low = at_level.loc["recommended"], at_level.loc["minimum"]
    full = at_level.loc["complete"] if "complete" in at_level.index else crew
    raw = {"price": price, "tickets": tickets, "plan_taps": int(crew["n_pour"]),
           "plan_sellers": int(crew["sellers"]), "target_wait": target["evening_p90_min"],
           "min_taps": int(low["n_pour"]), "min_sellers": int(low["sellers"]),
           "fallback": bool(crew["fallback"]),
           "rec_met": int(crew["nights_met"]), "rec_nights": int(crew["nights"]),
           "rec_share_lo": float(crew["share_lo"]), "rec_share_hi": float(crew["share_hi"]),
           "rec_wait_bad": float(crew["wait_bad_night"]),
           "min_met": int(low["nights_met"]), "min_nights": int(low["nights"]),
           "min_share_lo": float(low["share_lo"]), "min_share_hi": float(low["share_hi"]),
           "min_wait_bad": float(low["wait_bad_night"]),
           "inside_plan": float(crew["inside_peak"]),
           "reliability_rec": stf_cfg.get("reliability_recommended", stf_cfg["reliability"]),
           "target_abandon": target["abandon_share"], "reliability": stf_cfg["reliability"],
           "density_limit": stf_cfg["safety"]["floor_density_limit"],
           "min_line": cal_cfg["observations"]["both_lines"]["min_people"]}
    raw["svc_from"], raw["svc_to"] = params.service_window()
    raw["obs_from"] = cal_cfg["observations"]["long_wait"]["from"]
    raw["obs_to"] = cal_cfg["observations"]["long_wait"]["to"]
    plan_cfg = params.load(ROOT / "config" / "scenarios.yaml")["scenarios"][head]["overrides"]
    raw["sellers_from"], raw["sellers_to"] = plan_cfg["sellers.start"], plan_cfg["sellers.end"]
    raw["clip_from"] = report_cfg["clips"]["night"]["from"]
    raw["clip_to"] = report_cfg["clips"]["night"]["to"]
    cols = ["evening_p90_min", "obs_buyer_median_min", "obs_median_min", "night_buyer_median_min",
            "obs_exchange_median_min", "obs_ticket_median_min", "night_exchange_median_min",
            "night_median_min", "queue_cash_night", "queue_pour_night", "beers_total",
            "lost_attempts", "abandon_share", "line_hours", "within5_share", "max_in_lines",
            "headliner_min_per_buyer", "heavy6_share", "beers_peak_hour", "staff",
            "staff_hours", "queue_cash_obs", "queue_pour_obs", "peak_occupancy"]
    for tag, scn in (("base", "baseline"), ("plan", head), ("tap", "pay_at_tap"),
                     ("full", "full_setup")):
        for c in cols:
            raw[f"{tag}_{c}"] = med(scn, c)
            raw[f"{tag}_{c}_lo"], raw[f"{tag}_{c}_hi"] = rng(scn, c)
    raw["nights"] = int(met["draw"].nunique())
    by_sellers = met.loc[met["scenario"] == head, "beers_seller"] / met.loc[met["scenario"] == head, "beers_total"]
    raw["plan_seller_share"] = float(by_sellers.median())
    raw["plan_seller_share_lo"] = float(by_sellers.quantile(0.05))
    raw["plan_seller_share_hi"] = float(by_sellers.quantile(0.95))
    e_wait, e_beer = effect(head, "Wait of 1 in 10"), effect(head, "Beers")
    e_hours = effect(head, "Hours in line")
    for tag, e in (("d_wait", e_wait), ("d_beers", e_beer), ("d_hours", e_hours)):
        for k in ("med", "med_lo", "med_hi", "lo", "hi", "improved_n", "n", "improved_lo"):
            raw[f"{tag}_{k}"] = float(e[k])
    raw["pour_2026"] = float(post["bar.n_pour"].median())
    raw["pour_2026_lo"] = float(post["bar.n_pour"].quantile(0.05))
    raw["pour_2026_hi"] = float(post["bar.n_pour"].quantile(0.95))
    raw["window_s"] = float(post["bar.s_cash_mean_s"].median())
    raw["serve_s"] = float(post["bar.s_pour_mean_s"].median())
    for scn in wi.index:
        raw[f"wi_{scn}"] = float(wi.loc[scn, "p90"])
        raw[f"wi_{scn}_hi"] = float(wi.loc[scn, "p90_hi"])
        raw[f"wi_{scn}_met"] = int(wi.loc[scn, "nights_met"])
        raw[f"wi_{scn}_nights"] = int(wi.loc[scn, "nights"])
        raw[f"wi_{scn}_met_lo"] = float(wi.loc[scn, "met_lo"])
        raw[f"wi_{scn}_met_hi"] = float(wi.loc[scn, "met_hi"])
    stf_sales = table("staff_sales.csv").iloc[0]
    for k in ("staff_2026", "staff_2026_lo", "staff_2026_hi", "staff_plan", "hours_2026",
              "hours_plan", "extra_hours", "beers_per_extra_hour", "med_lo", "med_hi", "p05",
              "p95"):
        raw[f"ss_{k}"] = float(stf_sales[k])
    raw["base_exchange_reached_share"] = float(
        met.loc[met["scenario"] == "baseline", "obs_exchange_reached"].astype(bool).mean())
    raw["long_wait_max"] = cal_cfg["observations"]["long_wait"].get("max_median_min")
    raw["long_wait_min"] = cal_cfg["observations"]["long_wait"]["min_median_min"]
    raw["ref_no_limit"] = reference_values("no_upper_limit", stf_cfg, tickets)
    raw.update(mixes_values(tickets, int(crew["n_pour"]), int(crew["sellers"])))
    shares_path = TAB / "worker_shares.csv"
    if shares_path.exists():
        ws = pd.read_csv(shares_path)
        q = ws[ws["quantity"] == "bar busy share, whole night"].set_index("scenario")["med"]
        raw["busy_base"], raw["busy_plan"] = pct(q["baseline"]), pct(q[head])
    else:
        raw["busy_base"] = raw["busy_plan"] = ""
    for k in ("author", "contact_label", "contact_url", "date"):
        raw[k] = report_cfg.get(k, "")
    raw.update({"full_taps": int(full["n_pour"]), "full_sellers": int(full["sellers"]),
                "full_met": int(full["nights_met"]), "full_nights": int(full["nights"]),
                "full_staff": float(full["staff"]), "full_staff_hours": float(full["staff_hours"]),
                "rec_staff": float(crew["staff"]),
                "counter_m_plan": counter_per_station(int(crew["n_pour"])),
                "surcharge": report_cfg.get("ticket_surcharge_mxn", 0),
                "paying_tickets": report_cfg.get("paying_tickets", tickets)})
    above = raw["full_staff_hours"] - raw["ss_hours_2026"]
    budget = raw["surcharge"] * raw["paying_tickets"]
    raw["cost_limit_full"] = budget / above if above > 0 and budget else None

    raw["max_sellers"] = max(stf_cfg["grid"]["sellers.n"])
    raw["model_tickets"] = int(base_cfg["crowd"]["n_total"])
    (raw["pour_interval_lo"], raw["pour_interval_hi"], raw["pour_interval_k"],
     raw["pour_interval_n"]) = shortest_interval(post["bar.n_pour"])

    lim = raw["density_limit"]

    def tickets_at(density):
        """Ticket level at which the free floor reaches a density, interpolated on the
        simulated levels. None outside them."""
        if not cap["density"].min() <= density <= cap["density"].max():
            return None
        return float(np.interp(density, cap["density"], cap["n_total"]))

    # A hall whose sides are a share s longer has (1 + s)^2 the floor area, so it reaches
    # the density limit at the ticket level where the measured hall reaches lim * (1 + s)^2.
    side = report_cfg["hall_side_uncertainty"]
    raw["cap_tickets"] = tickets_at(lim)
    raw["cap_tickets_lo"] = tickets_at(lim * (1 - side) ** 2)
    raw["cap_tickets_hi"] = tickets_at(lim * (1 + side) ** 2)
    raw["hall_side_uncertainty"] = side
    raw["density_limit_large"] = stf_cfg["safety"]["floor_density_limit_large_area"]
    raw["cap_tickets_large"] = tickets_at(raw["density_limit_large"])
    raw["density_at_plan"] = float(cap.loc[cap["n_total"] == tickets, "density"].iloc[0])
    raw["floor_m2"] = int(Venue(params.load()).floor_cells.size)

    crews = rel[rel["n_total"] == tickets].sort_values(["staff_hours", "staff"])
    staffing_rows = crew_rows(plan, stf_cfg["grid"]["crowd.n_total"])

    serving_path = TAB / "serving_options.csv"
    v = {"raw": raw, "crews": crews, "staffing_rows": staffing_rows,
         "serving": pd.read_csv(serving_path) if serving_path.exists() else None,
         "threshold_check": table("threshold_check.csv"),
         "hourly_plan": hourly_sales(series, head), "hourly_2026": hourly_sales(series, "baseline"),
         "comparisons": cmp_, "effects": eff, "what_if": wi.reset_index(),
         "scenario_metrics": met}

    # formatted strings for the technical page
    f = {
        "sims": n0(cal["simulations"]), "stages": n0(cal["stages"]), "matching": n0(cal["matching"]),
        "ess": n0(cal["effective_sample"]), "post_n": n0(cal["posterior_draws"]),
        "pour_2026": f"{raw['pour_2026_lo']:.0f} to {raw['pour_2026_hi']:.0f}",
        "window_s": n0(raw["window_s"]), "serve_s": n0(raw["serve_s"]),
        "nights": n0(raw["nights"]), "price": n0(price), "tickets": n0(tickets),
        "occ_med": n0(cal["peak_occupancy_median"]), "occ_lo": n0(cal["peak_occupancy_p05"]),
        "occ_hi": n0(cal["peak_occupancy_p95"]),
        "ticket_line": n0(raw["base_queue_cash_obs"]), "exchange_line": n0(raw["base_queue_pour_obs"]),
        "base_exchange_wait": n0(raw["base_obs_exchange_median_min"]),
        "base_exchange_wait_lo": n0(raw["base_obs_exchange_median_min_lo"]),
        "base_exchange_wait_hi": n0(raw["base_obs_exchange_median_min_hi"]),
        "base_ticket_wait": n0(raw["base_obs_ticket_median_min"]),
        "base_buyer_wait": n0(raw["base_obs_buyer_median_min"]),
        "base_buyer_wait_lo": n0(raw["base_obs_buyer_median_min_lo"]),
        "base_buyer_wait_hi": n0(raw["base_obs_buyer_median_min_hi"]),
        "base_night_wait": n0(raw["base_night_exchange_median_min"]),
        "base_night_wait_lo": n0(raw["base_night_exchange_median_min_lo"]),
        "base_night_wait_hi": n0(raw["base_night_exchange_median_min_hi"]),
        "base_p90": n0(raw["base_evening_p90_min"]),
        "base_beers": n0(raw["base_beers_total"]), "base_beers_lo": n0(raw["base_beers_total_lo"]),
        "base_beers_hi": n0(raw["base_beers_total_hi"]), "base_lost": n0(raw["base_lost_attempts"]),
        "base_hours": n0(raw["base_line_hours"]), "base_staff": n0(raw["base_staff"]),
        "plan_p90": n1(raw["plan_evening_p90_min"]), "plan_p90_hi": n1(raw["plan_evening_p90_min_hi"]),
        "plan_beers": n0(raw["plan_beers_total"]), "plan_hours": n0(raw["plan_line_hours"]),
        "plan_staff": n0(raw["plan_staff"]), "plan_taps": str(raw["plan_taps"]),
        "plan_sellers": str(raw["plan_sellers"]),
        "plan_met": f"{int(crew['nights_met'])} of {int(crew['nights'])}",
        "plan_share_lo": pct(crew["share_lo"]), "plan_share_hi": pct(crew["share_hi"]),
        "min_taps": str(raw["min_taps"]), "min_sellers": str(raw["min_sellers"]),
        "min_met": f"{raw['min_met']} of {raw['min_nights']}",
        "min_share_lo": pct(raw["min_share_lo"]), "min_share_hi": pct(raw["min_share_hi"]),
        "reliability_rec": pct(raw["reliability_rec"]),
        "staff_2026": n0(raw["ss_staff_2026"]),
        "staff_2026_range": f"{raw['ss_staff_2026_lo']:.0f} to {raw['ss_staff_2026_hi']:.0f}",
        "staff_plan": n0(raw["ss_staff_plan"]), "extra_hours": n0(raw["ss_extra_hours"]),
        "per_hour": n0(raw["ss_beers_per_extra_hour"]),
        "per_hour_lo": n0(raw["ss_med_lo"]), "per_hour_hi": n0(raw["ss_med_hi"]),
        "per_hour_p05": n0(raw["ss_p05"]), "per_hour_p95": n0(raw["ss_p95"]),
        "per_hour_mxn": n0(round(raw["ss_beers_per_extra_hour"] * price, -1)),
        "per_hour_mxn_lo": n0(round(raw["ss_med_lo"] * price, -1)),
        "per_hour_mxn_hi": n0(round(raw["ss_med_hi"] * price, -1)),
        "exchange_reached": pct(raw["base_exchange_reached_share"]),
        "d_wait": n1(-raw["d_wait_med"]), "d_wait_lo": n1(-raw["d_wait_med_hi"]),
        "d_wait_hi": n1(-raw["d_wait_med_lo"]),
        "d_beers": n0(raw["d_beers_med"]), "d_beers_lo": n0(raw["d_beers_med_lo"]),
        "d_beers_hi": n0(raw["d_beers_med_hi"]), "d_beers_p05": n0(raw["d_beers_lo"]),
        "d_beers_p95": n0(raw["d_beers_hi"]),
        "d_mxn": n0(raw["d_beers_med"] * price), "d_mxn_lo": n0(raw["d_beers_med_lo"] * price),
        "d_mxn_hi": n0(raw["d_beers_med_hi"] * price),
        "improved": f"{int(raw['d_wait_improved_n'])} of {int(raw['d_wait_n'])}",
        "improved_lo": pct(raw["d_wait_improved_lo"]),
        "tap_p90": n1(raw["tap_evening_p90_min"]), "tap_p90_hi": n1(raw["tap_evening_p90_min_hi"]),
        "tap_staff": n0(raw["tap_staff"]),
        "heavy_base": f"{100 * raw['base_heavy6_share']:.1f}%",
        "heavy_plan": f"{100 * raw['plan_heavy6_share']:.1f}%",
        "heavy_plan_lo": f"{100 * raw['plan_heavy6_share_lo']:.1f}%",
        "heavy_plan_hi": f"{100 * raw['plan_heavy6_share_hi']:.1f}%",
        "peak_hour_plan": n0(raw["plan_beers_peak_hour"]), "peak_hour_base": n0(raw["base_beers_peak_hour"]),
        "tgt_wait": str(raw["target_wait"]), "tgt_ab": pct(raw["target_abandon"]),
        "svc_window": f"{raw['svc_from']} and {raw['svc_to']}",
        "seller_load": str(base_cfg["sellers"]["capacity"]),
        "seller_refill": f"{base_cfg['sellers']['restock_s'] / 60:.0f}",
        "sellers_hours": f"{raw['sellers_from']} to {raw['sellers_to']}",
        "reliability": pct(raw["reliability"]), "lim": str(lim), "floor_m2": n0(raw["floor_m2"]),
        "cap_tickets": n0(round(raw["cap_tickets"], -2)) if raw["cap_tickets"] else "above the grid",
        "cap_tickets_lo": (n0(round(raw["cap_tickets_lo"], -2)) if raw["cap_tickets_lo"]
                           else "below the grid"),
        "cap_tickets_hi": (n0(round(raw["cap_tickets_hi"], -2)) if raw["cap_tickets_hi"]
                           else "above the grid"),
        "hall_side": pct(side),
        "lim_large": str(raw["density_limit_large"]),
        "cap_tickets_large": (f"near {n0(round(raw['cap_tickets_large'], -2))} tickets"
                              if raw["cap_tickets_large"] else
                              f"below {n0(cap['n_total'].min())} tickets, the lowest level simulated"
                              if raw["density_limit_large"] < cap["density"].min() else
                              "above the highest level simulated"),
        "wait_min": n0(raw["long_wait_min"]),
        "wait_max": n0(raw["long_wait_max"]) if raw["long_wait_max"] else "no",
        "crew_nights": str(raw["rec_nights"]),
        "base_p90_lo": n0(raw["base_evening_p90_min_lo"]),
        "base_p90_hi": n0(raw["base_evening_p90_min_hi"]),
        "density_at_plan": f"{raw['density_at_plan']:.2f}",
        "max_sellers": str(raw["max_sellers"]),
    }
    for first, second, tag in (("pay_at_tap", head, "plan_vs_tap"), (head, "full_setup", "full_vs_plan"),
                               ("pay_at_tap", "cashless", "cashless_vs_tap")):
        w, b = compare(first, second, "evening_p90_min"), compare(first, second, "beers_total")
        f[f"{tag}_wait"] = f"{w['med']:+.1f} min ({w['med_lo']:+.1f} to {w['med_hi']:+.1f})"
        f[f"{tag}_beers"] = f"{b['med']:+,.0f} ({b['med_lo']:+,.0f} to {b['med_hi']:+,.0f})"
        f[f"{tag}_staff"] = f"{w['staff_diff']:+.0f}"
    shares_path = TAB / "worker_shares.csv"
    if shares_path.exists():
        ws = pd.read_csv(shares_path)
        for scn, tag in (("baseline", "base"), (head, "plan")):
            for q, key in (("bar busy share, whole night", "busy"),
                           ("bar charging share of busy time", "charging")):
                row = ws[(ws["scenario"] == scn) & (ws["quantity"] == q)].iloc[0]
                f[f"w_{key}_{tag}"] = f"{pct(row['med'])} ({pct(row['lo'])} to {pct(row['hi'])})"
        for state in ("walking", "selling", "to refill", "refilling"):
            row = ws[ws["quantity"] == f"seller {state}"].iloc[0]
            f[f"w_seller_{state.replace(' ', '_')}"] = (f"{pct(row['med'])} ({pct(row['lo'])} "
                                                        f"to {pct(row['hi'])})")
        busy = pd.read_csv(TAB / "worker_busy.csv")
        for scn, tag in (("baseline", "base"), (head, "plan")):
            b = busy[busy["scenario"] == scn]
            top = b.loc[b["med"].idxmax()]
            f[f"w_peak_{tag}"] = f"{int(top['hour']) % 24:02d}:00"
            f[f"w_peak_share_{tag}"] = pct(top["med"])
    for scn in wi.index:
        f[f"wi_{scn}"] = n1(raw[f"wi_{scn}"])
        f[f"wi_{scn}_hi"] = n1(raw[f"wi_{scn}_hi"])
    f["seller_share"] = pct(raw["plan_seller_share"])
    f["seller_share_lo"] = pct(raw["plan_seller_share_lo"])
    f["seller_share_hi"] = pct(raw["plan_seller_share_hi"])
    arb = ar[(ar["scenario"] == "baseline") & ar["term"].str.startswith("per 100")].iloc[0]
    arp = ar[(ar["scenario"] == head) & ar["term"].str.startswith("per 100")].iloc[0]
    f["ar_b"], f["ar_p"] = f"{arb['med']:.2f}", f"{arp['med']:.2f}"
    for key, model in (("drv_wait", "Wait in the exchange line"), ("drv_ticket", "People in the ticket"),
                       ("drv_exchange", "People in the exchange")):
        d = reg[reg["model"].str.startswith(model)].assign(a=lambda t: t["estimate"].abs())
        top = d.sort_values("a", ascending=False)["term"].head(3)
        f[key] = "; ".join(term[0].lower() + term[1:] for term in top)
    v.update(f)
    return v


if __name__ == "__main__":
    values = compute()
    for k, val in values.items():
        if isinstance(val, str):
            print(f"{k:22s} {val}")
