"""Serving options (config/serving.yaml) at the plan ticket level.

Every option runs the crew grid of config/staffing.yaml (stations x sellers) on the staffing
nights, with the staffing seeds, so the nights are the same as in the staffing grid. The
option `bottles` is the staffing grid itself and is read from output/runs/staffing_grid.csv.
Writes
    output/runs/serving_grid.csv            one row per night, crew and option
    output/tables/serving_reliability.csv   nights that meet the target, per option and crew
    output/tables/serving_options.csv       per option: minimum and recommended crew, and the
                                            plan crew under that option
Usage: uv run python scripts/run_serving.py [--processes P]
"""

import argparse
import itertools
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sim import experiments as ex  # noqa: E402
from sim import params  # noqa: E402
from sim import scenarios as sc  # noqa: E402
from sim import staffing  # noqa: E402

OUT = params.ROOT / "output" / "runs"
TABLES = params.ROOT / "output" / "tables"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--processes", type=int, default=None)
    ap.add_argument("--tables-only", action="store_true",
                    help="rebuild the tables from output/runs/serving_grid.csv without runs")
    args = ap.parse_args()

    base = params.load()
    cal = ex.load_calibration()
    spec = params.load(params.ROOT / "config" / "staffing.yaml")
    options = params.load(params.ROOT / "config" / "serving.yaml")["options"]
    tickets = int(params.load(params.ROOT / "config" / "report.yaml")["plan_tickets"])
    draws = pd.read_csv(OUT / "posterior_draws.csv").head(spec["draws"])
    prior_cols = [c for c in draws.columns if c in cal["priors"]]
    grid = {k: v for k, v in spec["grid"].items() if k != "crowd.n_total"}
    keys = list(grid)
    crews = [dict(zip(keys, values)) for values in itertools.product(*grid.values())]

    tasks = []
    for name, opt in options.items():
        if not opt["overrides"]:
            continue                          # the staffing grid itself
        for _, row in draws.iterrows():
            cfg = ex.draw_config(base, row[prior_cols], cal["priors"])
            cfg = params.with_overrides(cfg, sc.resolve(spec["setup"], cfg))
            cfg = params.with_overrides(cfg, {**opt["overrides"], "crowd.n_total": tickets})
            for crew in crews:
                tags = {"draw": int(row["draw"]), "option": name, "n_total": tickets,
                        **{k.split(".")[-1]: v for k, v in crew.items()}}
                tasks.append((params.with_overrides(cfg, crew), 90_000 + int(row["draw"]),
                              cal["observations"], tags))
    t0 = time.time()
    if args.tables_only:
        allruns = pd.read_csv(OUT / "serving_grid.csv")
    else:
        metrics, _, _ = ex.run_many_resumable(tasks, OUT / "parts_serving",
                                              processes=args.processes)
        staff_grid = pd.read_csv(OUT / "staffing_grid.csv")
        same = staff_grid[(staff_grid["n_total"] == tickets)
                          & staff_grid["draw"].isin(draws["draw"])].assign(option="bottles")
        allruns = pd.concat([same, metrics], ignore_index=True)
        allruns.to_csv(OUT / "serving_grid.csv", index=False)

    target = spec["service_target"]
    rel_lo = spec["reliability"]
    rel_hi = spec.get("reliability_recommended", rel_lo)
    plan_crew = staffing.plan_crew(tickets)
    rows, summaries = [], []
    for name, opt in options.items():
        summ = staffing.summarize(allruns[allruns["option"] == name].drop(columns="option"),
                                  target)
        summaries.append(summ.assign(option=name))
        plan = staffing.plan_table(summ, rel_lo, rel_hi).set_index("level")
        plan = plan[~plan.index.duplicated()]
        at_plan = summ[(summ["n_pour"] == plan_crew["plan_taps"])
                       & (summ["sellers"] == plan_crew["plan_sellers"])]
        row = {"option": name, "label": opt["label"], "assumption": opt["assumption"]}
        if len(at_plan):                      # the plan crew under this serving option
            a = at_plan.iloc[0]
            row.update({"plan_crew_met": int(a["nights_met"]), "nights": int(a["nights"]),
                        "plan_crew_wait": float(a["wait_median"]),
                        "plan_crew_wait_bad": float(a["wait_bad_night"])})
        for level in ("minimum", "recommended"):
            if level not in plan.index:
                row.update({f"{level}_taps": None})
                continue
            r = plan.loc[level]
            row.update({f"{level}_taps": int(r["n_pour"]), f"{level}_sellers": int(r["sellers"]),
                        f"{level}_met": int(r["nights_met"]),
                        f"{level}_share_lo": float(r["share_lo"]),
                        f"{level}_share_hi": float(r["share_hi"]),
                        f"{level}_staff_hours": float(r["staff_hours"]),
                        f"{level}_fallback": bool(r["fallback"])})
        rows.append(row)
    pd.concat(summaries, ignore_index=True).to_csv(TABLES / "serving_reliability.csv",
                                                   index=False)
    table = pd.DataFrame(rows)
    table.to_csv(TABLES / "serving_options.csv", index=False)
    print(table[["option", "minimum_taps", "minimum_sellers", "recommended_taps",
                 "recommended_sellers", "plan_crew_met", "plan_crew_wait"]].to_string(index=False))
    params.write_manifest("serving", {"runs": len(tasks), "seconds": round(time.time() - t0)})
    print(f"{len(tasks)} runs in {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
