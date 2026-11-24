"""Staffing and capacity grid from config/staffing.yaml.

Usage: uv run python scripts/run_staffing.py [--base FILE] [--calibration FILE]
                                             [--staffing FILE] [--processes P]
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=params.ROOT / "config" / "base.yaml")
    ap.add_argument("--calibration", default=params.ROOT / "config" / "calibration.yaml")
    ap.add_argument("--staffing", default=params.ROOT / "config" / "staffing.yaml")
    ap.add_argument("--processes", type=int, default=None)
    ap.add_argument("--tables-only", action="store_true",
                    help="rebuild the tables from output/runs/staffing_grid.csv without runs")
    args = ap.parse_args()

    base = params.load(args.base)
    cal = ex.load_calibration(args.calibration)
    spec = params.load(args.staffing)
    draws = pd.read_csv(OUT / "posterior_draws.csv")
    acc = draws.head(spec["draws"])
    prior_cols = [c for c in draws.columns if c in cal["priors"]]
    keys = list(spec["grid"])

    tasks = []
    for _, row in acc.iterrows():
        cfg = ex.draw_config(base, row[prior_cols], cal["priors"])
        cfg = params.with_overrides(cfg, sc.resolve(spec["setup"], cfg))
        combos = [dict(zip(keys, values))
                  for values in itertools.product(*(spec["grid"][k] for k in keys))]
        for combo in combos + list(spec.get("extra_cells", [])):
            tags = {"draw": int(row["draw"]), **{k.split(".")[-1]: v for k, v in combo.items()}}
            tasks.append((params.with_overrides(cfg, combo), 90_000 + int(row["draw"]),
                          cal["observations"], tags))
    t0 = time.time()
    if args.tables_only:
        metrics = pd.read_csv(OUT / "staffing_grid.csv")
    else:
        metrics, _, _ = ex.run_many_resumable(tasks, OUT / "parts_staffing",
                                              processes=args.processes)
        metrics.to_csv(OUT / "staffing_grid.csv", index=False)
    tables = params.ROOT / "output" / "tables"
    tables.mkdir(parents=True, exist_ok=True)
    summary = staffing.summarize(metrics, spec["service_target"])
    summary.to_csv(tables / "staffing_reliability.csv", index=False)
    in_grid = summary[summary["n_total"].isin(spec["grid"]["crowd.n_total"])]
    plan = staffing.plan_table(in_grid, spec["reliability"], spec["reliability_recommended"],
                               spec.get("reliability_complete"))
    plan.to_csv(staffing.PLAN_FILE, index=False)
    print(plan[["n_total", "level", "n_pour", "sellers", "nights_met", "nights", "fallback"]]
          .to_string(index=False))
    params.write_manifest("staffing", {"base": str(args.base), "staffing": str(args.staffing), "draws": len(acc), "runs": len(tasks), "seconds": round(time.time() - t0)})
    print(f"{len(tasks)} runs in {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
