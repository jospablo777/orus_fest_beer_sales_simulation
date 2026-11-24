"""Run every scenario on the accepted calibration draws.

All scenarios of one draw share the random seed (common random numbers), so the difference
between a scenario and the baseline of the same draw is that draw's counterfactual effect.
The draws and seeds are those of the staffing grid (config/staffing.yaml: draws, seed
90000 + draw), so the plan scenario repeats the staffing nights of the plan crew.

Usage: uv run python scripts/run_scenarios.py [--base FILE] [--calibration FILE]
                                              [--scenarios FILE] [--max-draws N] [--processes P]
"""

import argparse
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sim import experiments as ex  # noqa: E402
from sim import params  # noqa: E402
from sim import scenarios as sc  # noqa: E402

OUT = params.ROOT / "output" / "runs"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=params.ROOT / "config" / "base.yaml")
    ap.add_argument("--calibration", default=params.ROOT / "config" / "calibration.yaml")
    ap.add_argument("--scenarios", default=params.ROOT / "config" / "scenarios.yaml")
    ap.add_argument("--max-draws", type=int, default=None,
                    help="default: `draws` of config/staffing.yaml")
    ap.add_argument("--processes", type=int, default=None)
    ap.add_argument("--families", default=None,
                    help="comma-separated families to run (main, what_if); results replace "
                         "those families in the existing output files")
    args = ap.parse_args()

    base = params.load(args.base)
    cal = ex.load_calibration(args.calibration)
    scen = sc.load(args.scenarios)
    all_scen = scen
    if args.families:
        fams = set(args.families.split(","))
        scen = {k: v for k, v in scen.items() if v["family"] in fams}
    draws = pd.read_csv(OUT / "posterior_draws.csv")
    n_draws = args.max_draws or params.load(params.ROOT / "config" / "staffing.yaml")["draws"]
    acc = draws.head(n_draws)
    prior_cols = [c for c in draws.columns if c in cal["priors"]]

    tasks = []
    for _, row in acc.iterrows():
        cfg = ex.draw_config(base, row[prior_cols], cal["priors"])
        for key, s in scen.items():
            tasks.append((sc.apply(cfg, s), 90_000 + int(row["draw"]), cal["observations"],
                          {"draw": int(row["draw"]), "scenario": key, "family": s["family"],
                           "label": s["label"]}))
    t0 = time.time()
    metrics, series, waits = ex.run_many_resumable(tasks, OUT / "parts_scenarios",
                                                   processes=args.processes)
    outputs = {"scenario_metrics.csv": metrics, "scenario_series.csv": series,
               "scenario_waits.csv": waits}
    for name, df in outputs.items():
        path = OUT / name
        if args.families and path.exists():
            old = pd.read_csv(path)
            df = pd.concat([old[~old["scenario"].isin(scen)], df], ignore_index=True)
        df.to_csv(path, index=False)
    pd.DataFrame([{"scenario": k, "family": v["family"], "label": v["label"]}
                  for k, v in all_scen.items()]).to_csv(OUT / "scenario_labels.csv",
                                                        index=False)
    params.write_manifest("scenarios", {"base": str(args.base), "scenarios": str(args.scenarios), "families": args.families, "draws": len(acc), "runs": len(tasks), "seconds": round(time.time() - t0)})
    print(f"{len(tasks)} runs on {len(acc)} draws in {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
