"""Crew selection from the staffing grid.

A crew (taps, sellers) is judged by the share of simulated nights in which it meets the
service target. The plan for a ticket level is the crew with the fewest staff hours among
those whose share reaches the required reliability.
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


def plan_crew(tickets: int) -> dict:
    """Taps and sellers of the plan for a ticket level, read from the staffing table."""
    if not PLAN_FILE.exists():
        raise FileNotFoundError(f"{PLAN_FILE} is missing; run scripts/run_staffing.py first")
    plan = pd.read_csv(PLAN_FILE)
    row = plan[plan["n_total"] == tickets]
    if row.empty:
        raise ValueError(f"no crew in the staffing grid reaches the reliability for "
                         f"{tickets} tickets")
    return {"plan_taps": int(row["n_pour"].iloc[0]), "plan_sellers": int(row["sellers"].iloc[0])}
