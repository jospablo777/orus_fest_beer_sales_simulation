"""Crew selection from the staffing grid.

A crew (stations, sellers) is judged by the share of simulated nights in which it meets the
service target. For each ticket level two crews are chosen, each the one with the fewest staff
hours among the crews whose share reaches a required reliability: the minimum crew
(`reliability`) and the recommended crew (`reliability_recommended`). The plan uses the
recommended crew, or the minimum crew when no crew reaches the higher share.
"""

from __future__ import annotations

import pandas as pd
from scipy import stats

from . import params

PLAN_FILE = params.ROOT / "output" / "tables" / "staffing_plan.csv"
KEYS = ["n_total", "n_pour", "sellers"]


def exact_interval(k: int, n: int, level: float = 0.95) -> tuple[float, float]:
    """Clopper-Pearson interval for a share of k nights out of n."""
    ci = stats.binomtest(int(k), int(n)).proportion_ci(level, method="exact")
    return float(ci.low), float(ci.high)


def summarize(grid: pd.DataFrame, target: dict) -> pd.DataFrame:
    """One row per crew and ticket level."""
    g = grid.rename(columns={"n": "sellers"}).copy()
    g["met"] = ((g["evening_p90_min"] <= target["evening_p90_min"])
                & (g["abandon_share"] <= target["abandon_share"]))
    out = g.groupby(KEYS).agg(
        nights=("met", "size"), nights_met=("met", "sum"),
        wait_median=("evening_p90_min", "median"),
        wait_bad_night=("evening_p90_min", lambda v: v.quantile(0.9)),
        wait_worst=("evening_p90_min", "max"),
        abandon_median=("abandon_share", "median"),
        beers_median=("beers_total", "median"),
        staff=("staff", "median"), staff_hours=("staff_hours", "median"),
        inside_peak=("peak_occupancy", "median"),
        floor_density=("floor_density_peak", "median"),
        floor_density_lo=("floor_density_peak", lambda v: v.quantile(0.05)),
        floor_density_hi=("floor_density_peak", lambda v: v.quantile(0.95)),
    ).reset_index()
    out["share_met"] = out["nights_met"] / out["nights"]
    ci = [exact_interval(k, n) for k, n in zip(out["nights_met"], out["nights"])]
    out["share_lo"] = [c[0] for c in ci]
    out["share_hi"] = [c[1] for c in ci]
    return out


def choose(summary: pd.DataFrame, reliability: float) -> pd.DataFrame:
    """Per ticket level: the crew with the fewest staff hours whose share of nights that
    meet the target is at least `reliability`. Ticket levels with no such crew are left out."""
    ok = summary[summary["share_met"] >= reliability]
    ok = ok.sort_values(["n_total", "staff_hours", "staff"])
    return ok.groupby("n_total", as_index=False).first()


def plan_table(summary: pd.DataFrame, reliability: float,
               reliability_recommended: float) -> pd.DataFrame:
    """Minimum and recommended crew per ticket level, one row each (column `level`). A level
    whose recommended crew does not exist gets the minimum crew as its recommended row, with
    `fallback` set."""
    lo = choose(summary, reliability).assign(level="minimum", fallback=False)
    hi = choose(summary, reliability_recommended).assign(level="recommended", fallback=False)
    missing = lo[~lo["n_total"].isin(hi["n_total"])].assign(level="recommended", fallback=True)
    out = pd.concat([lo, hi, missing], ignore_index=True)
    return out.sort_values(["n_total", "level"]).reset_index(drop=True)


def plan_crew(tickets: int) -> dict:
    """Stations and sellers of the recommended crew (plan_taps, plan_sellers) and of the
    minimum crew (plan_min_taps, plan_min_sellers) for a ticket level."""
    if not PLAN_FILE.exists():
        raise FileNotFoundError(f"{PLAN_FILE} is missing; run scripts/run_staffing.py first")
    plan = pd.read_csv(PLAN_FILE)
    rows = plan[plan["n_total"] == tickets].set_index("level")
    if rows.empty:
        raise ValueError(f"no crew in the staffing grid reaches the reliability for "
                         f"{tickets} tickets")
    rec, low = rows.loc["recommended"], rows.loc["minimum"]
    return {"plan_taps": int(rec["n_pour"]), "plan_sellers": int(rec["sellers"]),
            "plan_min_taps": int(low["n_pour"]), "plan_min_sellers": int(low["sellers"])}
