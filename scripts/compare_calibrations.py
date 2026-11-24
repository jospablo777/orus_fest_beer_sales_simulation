"""Compare the current results with reference runs made under other calibration settings.

Each reference folder under output/sensitivity/ holds copies of output/tables, the runs
posterior_draws.csv, scenario_metrics.csv and staffing_grid.csv, and the calibration.yaml it
used. For a reference named NAME the script writes
    output/tables/sensitivity_NAME_ranges.csv    inputs, 2026 outcomes and plan outcomes, per run
    output/tables/sensitivity_NAME_staffing.csv  minimum and recommended crews per ticket level
                                                 in either run, with the nights in which each
                                                 meets the target under both runs
The two runs simulate different nights, so outcomes are compared with the Mann-Whitney U
test and shares of nights with Fisher's exact test.
Usage: uv run python scripts/compare_calibrations.py [--reference DIR ...]
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


def staffing_table(ref: Path, cur: Path, target: dict, levels: list[float]) -> pd.DataFrame:
    summary = {k: staffing.summarize(pd.read_csv(d / "staffing_grid.csv"), target)
               for k, d in (("reference", ref), ("current", cur))}
    chosen = {k: pd.concat([staffing.choose(s, r) for r in levels]) for k, s in summary.items()}
    crews = pd.concat(chosen.values())[staffing.KEYS].drop_duplicates()
    rows = []
    for crew in crews.itertuples(index=False):
        row = {"n_total": crew.n_total, "n_pour": crew.n_pour, "sellers": crew.sellers}
        counts = {}
        for k, s in summary.items():
            hit = s[(s["n_total"] == crew.n_total) & (s["n_pour"] == crew.n_pour)
                    & (s["sellers"] == crew.sellers)]
            if hit.empty:                     # a crew outside the grid of the other run
                hit = pd.Series({"nights_met": 0, "nights": 0})
            else:
                hit = hit.iloc[0]
            met, n = int(hit["nights_met"]), int(hit["nights"])
            counts[k] = (met, n)
            c = chosen[k]
            picked = ((c["n_total"] == crew.n_total) & (c["n_pour"] == crew.n_pour)
                      & (c["sellers"] == crew.sellers)).any()
            row.update({f"{k}_met": met, f"{k}_nights": n, f"{k}_chosen": bool(picked)})
        (a, n1), (b, n2) = counts["reference"], counts["current"]
        row["p_fisher"] = (stats.fisher_exact([[a, n1 - a], [b, n2 - b]])[1]
                           if n1 and n2 else float("nan"))
        rows.append(row)
    return pd.DataFrame(rows).sort_values(["n_total", "n_pour", "sellers"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reference", nargs="*", type=Path,
                    default=sorted(p for p in (ROOT / "output" / "sensitivity").glob("*")
                                   if (p / "runs").is_dir()))
    args = ap.parse_args()
    cur_runs = ROOT / "output" / "runs"
    stf = params.load(ROOT / "config" / "staffing.yaml")
    levels = [stf["reliability"], stf.get("reliability_recommended", stf["reliability"])]
    tables = ROOT / "output" / "tables"
    for old in tables.glob("sensitivity_*.csv"):
        old.unlink()
    for ref in args.reference:
        name = ref.name
        ranges_table(ref / "runs", cur_runs).to_csv(tables / f"sensitivity_{name}_ranges.csv",
                                                     index=False)
        staffing_table(ref / "runs", cur_runs, stf["service_target"], levels).to_csv(
            tables / f"sensitivity_{name}_staffing.csv", index=False)
        print(f"wrote output/tables/sensitivity_{name}_ranges.csv and _staffing.csv")


if __name__ == "__main__":
    main()
