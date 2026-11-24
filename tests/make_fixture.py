"""Writes tests/fixtures/reference_metrics.json: the night metrics of the 2026 setup and the
plan for three fixed posterior draws and seeds. tests/test_model.py checks that later model
versions reproduce them when the new features are off.

Usage: uv run python tests/make_fixture.py
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sim import experiments as ex  # noqa: E402
from sim import params  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "reference_metrics.json"
DRAWS = [0, 21, 42]                      # rows of output/runs/posterior_draws.csv
PLAN = {"bar.mode": "direct", "bar.n_pour": 6, "bar.s_pay_direct_s": 15, "sellers.n": 15,
        "sellers.start": "18:00", "sellers.end": "02:30"}


def cases():
    """(name, config, seed) for the six reference nights."""
    cal = ex.load_calibration()
    post = pd.read_csv(ROOT / "output" / "runs" / "posterior_draws.csv")
    cols = [c for c in post.columns if c in cal["priors"]]
    base = params.load()
    out = []
    for k in DRAWS:
        row = post.iloc[k]
        cfg = ex.draw_config(base, row[cols], cal["priors"])
        seed = 90_000 + int(row["draw"])
        out.append((f"baseline_{k}", cfg, seed))
        out.append((f"plan_{k}", params.with_overrides(cfg, PLAN), seed))
    return out, cal["observations"]


def metrics_of(cfg, seed, obs):
    m, _, _ = ex.run_metrics(cfg, seed, obs)
    return {k: (None if isinstance(v, float) and np.isnan(v) else
                v.item() if hasattr(v, "item") else v) for k, v in m.items()}


def main():
    runs, obs = cases()
    FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    data = {name: metrics_of(cfg, seed, obs) for name, cfg, seed in runs}
    FIXTURE.write_text(json.dumps(data, indent=1, sort_keys=True))
    print("wrote", FIXTURE)


if __name__ == "__main__":
    main()
