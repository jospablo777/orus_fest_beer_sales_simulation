"""Compare the current results with a reference run made under other calibration settings.

The reference folder holds copies of output/tables, the runs posterior_draws.csv,
scenario_metrics.csv and staffing_grid.csv, and the calibration.yaml it used.
Writes
    output/tables/sensitivity_ranges.csv    inputs, 2026 outcomes and plan outcomes, per run
    output/tables/sensitivity_staffing.csv  recommended crew per ticket level, and the share
                                            of nights that meet the target for each crew
                                            recommended in either run
The two runs simulate different nights, so outcomes are compared with the Mann-Whitney U
test and shares of nights with Fisher's exact test.
Usage: uv run python scripts/compare_calibrations.py [--reference output/sensitivity/narrow_ranges]
"""

import argparse
import sys
from pathlib import Path

import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sim import params, staffing  # noqa: E402

INPUTS = {
    "crowd.patience_median_min": "Median patience (min)",
    "crowd.afternoon_thirst_mult": "Drinking pace before 18:00 (share of the evening pace)",
    "bar.bundle_mean": "Tickets per visit to the ticket window (mean, 1 + spare)",
    "bar.n_pour": "People serving beer in 2026",
    "bar.s_pour_mean_s": "Serving time, first beer of a visit (s)",
}
OUTCOMES_2026 = {
    "obs_exchange_median_min": "2026, exchange-line wait 18:00 to 20:00 (min)",
    "obs_buyer_median_min": "2026, whole purchase without tickets 18:00 to 20:00 (min)",
    "night_exchange_median_min": "2026, exchange-line wait 21:30 to 22:30 (min)",
    "beers_total": "2026, beers sold",
    "abandon_share": "2026, share of purchase attempts given up",
}
OUTCOMES_PLAN = {
    "evening_p90_min": "Plan, wait of 1 in 10 buyers 18:00 to 02:00 (min)",
    "beers_total": "Plan, beers sold",
    "abandon_share": "Plan, share of purchase attempts given up",
}


def quantiles(x: pd.Series) -> dict:
    return {"med": x.median(), "lo": x.quantile(0.05), "hi": x.quantile(0.95), "n": len(x)}


def ranges_table(ref: Path, cur: Path) -> pd.DataFrame:
    rows = []
    post = {k: pd.read_csv(d / "posterior_draws.csv") for k, d in
            (("reference", ref), ("current", cur))}
    for col, label in INPUTS.items():
        row = {"part": "input", "quantity": label}
        for k, df in post.items():
            row.update({f"{k}_{s}": v for s, v in quantiles(df[col]).items()})
        rows.append(row)
    sm = {k: pd.read_csv(d / "scenario_metrics.csv") for k, d in
          (("reference", ref), ("current", cur))}
    for scenario, outcomes, part in (("baseline", OUTCOMES_2026, "2026"),
                                     ("plan", OUTCOMES_PLAN, "plan")):
        for col, label in outcomes.items():
            row = {"part": part, "quantity": label}
            values = {}
            for k, df in sm.items():
                values[k] = df.loc[df["scenario"] == scenario, col].dropna()
                row.update({f"{k}_{s}": v for s, v in quantiles(values[k]).items()})
            row["p_mann_whitney"] = stats.mannwhitneyu(values["reference"], values["current"],
                                                       alternative="two-sided").pvalue
            rows.append(row)
    return pd.DataFrame(rows)


def staffing_table(ref: Path, cur: Path, target: dict, reliability: float) -> pd.DataFrame:
    summary = {k: staffing.summarize(pd.read_csv(d / "staffing_grid.csv"), target)
               for k, d in (("reference", ref), ("current", cur))}
    chosen = {k: staffing.choose(s, reliability) for k, s in summary.items()}
    crews = pd.concat(chosen.values())[staffing.KEYS].drop_duplicates()
    rows = []
    for crew in crews.itertuples(index=False):
        row = {"n_total": crew.n_total, "n_pour": crew.n_pour, "sellers": crew.sellers}
        counts = {}
        for k, s in summary.items():
            hit = s[(s["n_total"] == crew.n_total) & (s["n_pour"] == crew.n_pour)
                    & (s["sellers"] == crew.sellers)].iloc[0]
            met, n = int(hit["nights_met"]), int(hit["nights"])
            counts[k] = (met, n)
            c = chosen[k]
            picked = ((c["n_total"] == crew.n_total) & (c["n_pour"] == crew.n_pour)
                      & (c["sellers"] == crew.sellers)).any()
            row.update({f"{k}_met": met, f"{k}_nights": n, f"{k}_recommended": bool(picked)})
        (a, n1), (b, n2) = counts["reference"], counts["current"]
        row["p_fisher"] = stats.fisher_exact([[a, n1 - a], [b, n2 - b]])[1]
        rows.append(row)
    return pd.DataFrame(rows).sort_values(["n_total", "n_pour", "sellers"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reference", default=ROOT / "output" / "sensitivity" / "narrow_ranges",
                    type=Path)
    args = ap.parse_args()
    ref_runs, cur_runs = args.reference / "runs", ROOT / "output" / "runs"
    stf = params.load(ROOT / "config" / "staffing.yaml")
    tables = ROOT / "output" / "tables"
    ranges_table(ref_runs, cur_runs).to_csv(tables / "sensitivity_ranges.csv", index=False)
    staffing_table(ref_runs, cur_runs, stf["service_target"], stf["reliability"]).to_csv(
        tables / "sensitivity_staffing.csv", index=False)
    print("wrote output/tables/sensitivity_ranges.csv and sensitivity_staffing.csv")


if __name__ == "__main__":
    main()
