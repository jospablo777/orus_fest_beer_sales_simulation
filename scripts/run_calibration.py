"""Calibration: find the inputs under which the simulated 2026 setup matches what was seen.

Method: approximate Bayesian computation with a sequential sampler (population Monte Carlo,
Beaumont et al. 2009). Stage 0 draws inputs from the prior ranges (Latin hypercube) and
scores each simulated night by its distance from the observations. Each later stage
proposes new inputs around the closest nights of the stage before, keeps those within a
smaller distance, and weights them by prior density over proposal density. The last stage
keeps only nights that pass every test. The weighted nights are resampled into
output/runs/posterior_draws.csv, the sample used by every later step.

Every simulated batch is stored under output/runs/parts_calibration until the run ends. A
run that stops before the end replays the stored batches when the same command is issued
again and continues with the first batch that is missing.

Usage: uv run python scripts/run_calibration.py [--base FILE] [--calibration FILE]
"""

import argparse
import hashlib
import json
import shutil
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sim import experiments as ex  # noqa: E402
from sim import params  # noqa: E402

OUT = params.ROOT / "output" / "runs"
PARTS = OUT / "parts_calibration"
STEP_PROBS = np.array([0.2, 0.6, 0.2])      # choice inputs move one option down, stay, or up
MODEL_SOURCE = hashlib.sha256(b"".join(
    (params.ROOT / "sim" / name).read_bytes()
    for name in ("model.py", "venue.py", "experiments.py"))).hexdigest()


def stored(kind: str, base, obs, rows: pd.DataFrame, compute) -> pd.DataFrame:
    """compute() for one batch, read from PARTS when the same batch was simulated before
    with the same configuration and the same model code."""
    key = hashlib.sha256(json.dumps([MODEL_SOURCE, base, obs, rows.to_dict("list")],
                                    sort_keys=True, default=str).encode()).hexdigest()[:24]
    path = PARTS / f"{kind}_{key}.pkl"
    if path.exists():
        return pd.read_pickle(path)
    out = compute()
    PARTS.mkdir(parents=True, exist_ok=True)
    out.to_pickle(path)
    return out


def simulate(base, priors, obs, rows: pd.DataFrame, processes) -> pd.DataFrame:
    """Shortened runs: only the statistics of the calibration tests."""
    tasks = [(ex.draw_config(base, row, priors), 10_000 + int(row["draw"]), obs,
              {"draw": int(row["draw"])}) for _, row in rows.iterrows()]
    out = rows.merge(stored("short", base, obs, rows,
                            lambda: ex.run_calibration_tasks(tasks, processes)), on="draw")
    out["distance"] = ex.distance(out, obs)
    return out


def full_runs(base, priors, obs, rows: pd.DataFrame, processes) -> pd.DataFrame:
    """Whole-night runs of the same inputs and seeds, with every metric."""
    tasks = [(ex.draw_config(base, row, priors), 10_000 + int(row["draw"]), obs,
              {"draw": int(row["draw"])}) for _, row in rows.iterrows()]
    metrics = stored("full", base, obs, rows, lambda: ex.run_many(tasks, processes)[0])
    out = rows.merge(metrics, on="draw")
    out["distance"] = ex.distance(out, obs)
    return out


def to_unit(df: pd.DataFrame, priors: dict) -> np.ndarray:
    """Inputs as numbers: floats as they are, choices as the index of the option."""
    cols = []
    for name, spec in priors.items():
        if spec["type"] == "choice":
            cols.append(df[name].map({v: k for k, v in enumerate(spec["values"])}).to_numpy(float))
        else:
            cols.append(df[name].to_numpy(float))
    return np.column_stack(cols)


def propose(rng, particles, weights, sigma, priors, n) -> np.ndarray:
    """n proposals inside the prior ranges: a weighted pick of a particle plus a move."""
    names = list(priors)
    out = []
    while len(out) < n:
        theta = particles[rng.choice(len(particles), p=weights)].copy()
        ok = True
        for k, name in enumerate(names):
            spec = priors[name]
            if spec["type"] == "choice":
                theta[k] += rng.choice([-1, 0, 1], p=STEP_PROBS)
                ok &= 0 <= theta[k] < len(spec["values"])
            else:
                theta[k] += rng.normal(0.0, sigma[k])
                ok &= spec["low"] <= theta[k] <= spec["high"]
        if ok:
            out.append(theta)
    return np.array(out)


def proposal_density(theta, particles, weights, sigma, priors) -> np.ndarray:
    dens = np.ones((len(theta), len(particles)))
    for k, spec in enumerate(priors.values()):
        diff = theta[:, [k]] - particles[None, :, k]
        if spec["type"] == "choice":
            step = np.rint(diff).astype(int)
            dens *= np.where(np.abs(step) <= 1, STEP_PROBS[np.clip(step + 1, 0, 2)], 0.0)
        else:
            dens *= np.exp(-0.5 * (diff / sigma[k]) ** 2) / sigma[k]
    return dens @ weights


def to_frame(theta, priors, first_id) -> pd.DataFrame:
    cols = {}
    for k, (name, spec) in enumerate(priors.items()):
        cols[name] = ([spec["values"][int(round(v))] for v in theta[:, k]]
                      if spec["type"] == "choice" else theta[:, k])
    df = pd.DataFrame(cols)
    df.insert(0, "draw", np.arange(first_id, first_id + len(df)))
    return df


def systematic_resample(rng, weights, n) -> np.ndarray:
    positions = (rng.random() + np.arange(n)) / n
    return np.searchsorted(np.cumsum(weights), positions)


def sample_stages(base, priors, obs, smp, seed, rng, processes):
    """Stage 0 from the prior ranges, then stages with a shrinking distance limit.
    Returns the nights kept in the last stage, every simulated night, the number of
    simulations and the index of the last stage."""
    stage = simulate(base, priors, obs, ex.latin_hypercube(priors, smp["prior_draws"],
                                                           seed=seed), processes)
    stage["stage"], stage["weight"] = 0, 1.0
    history = [stage]
    n_sim = len(stage)
    eps = float(stage["distance"].quantile(smp["keep_share"]))
    stage["weight"] = (stage["distance"] <= eps).astype(float)
    kept = stage[stage["distance"] <= eps]
    weights = np.full(len(kept), 1.0 / len(kept))
    print(f"stage 0: {n_sim} nights, {int((stage.distance == 0).sum())} pass every test, "
          f"next distance limit {eps:.2f}", flush=True)

    k = 0
    while eps > 0 and n_sim < smp["max_simulations"]:
        k += 1
        eps = float(kept["distance"].quantile(smp["shrink"]))
        if eps < smp["min_distance"] or k >= smp["max_stages"]:
            eps = 0.0
        particles = to_unit(kept, priors)
        mean = weights @ particles
        sigma = np.sqrt(2.0 * (weights @ (particles - mean) ** 2)) + 1e-9
        rows = []
        while sum(len(r) for r in rows) < smp["particles"] and n_sim < smp["max_simulations"]:
            theta = propose(rng, particles, weights, sigma, priors, smp["batch"])
            sims = simulate(base, priors, obs, to_frame(theta, priors, n_sim), processes)
            n_sim += len(sims)
            sims["stage"] = k
            sims["weight"] = 1.0 / proposal_density(theta, particles, weights, sigma, priors)
            history.append(sims.assign(weight=np.where(sims["distance"] <= eps,
                                                       sims["weight"], 0.0)))
            rows.append(sims[sims["distance"] <= eps])
            print(f"stage {k}: limit {eps:.2f}, kept {sum(len(r) for r in rows)} "
                  f"after {n_sim} nights", flush=True)
        kept = pd.concat(rows, ignore_index=True)
        weights = kept["weight"].to_numpy() / kept["weight"].sum()

    return kept, history, n_sim, k


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=params.ROOT / "config" / "base.yaml")
    ap.add_argument("--calibration", default=params.ROOT / "config" / "calibration.yaml")
    ap.add_argument("--processes", type=int, default=None)
    ap.add_argument("--reaccept", action="store_true",
                    help="apply the observation thresholds of the YAML again to the last stage "
                         "of an existing calibration, without new shortened runs")
    ap.add_argument("--more", type=int, default=0,
                    help="add this many simulations to the last stage of an existing "
                         "calibration (output/runs/calibration_draws.csv)")
    args = ap.parse_args()
    base = params.load(args.base)
    cal = ex.load_calibration(args.calibration)
    priors, obs, smp = cal["priors"], cal["observations"], cal["sampler"]
    rng = np.random.default_rng(cal["seed"])
    t0 = time.time()

    if args.more or args.reaccept:
        # Work on the last stage of an existing calibration: its proposal population is the
        # set of nights kept in the stage before, so the weights can be computed again.
        old = pd.read_csv(OUT / "calibration_draws.csv")
        k = int(old["stage"].max())
        seeds = old[(old["stage"] == k - 1) & (old["weight"] > 0)]
        particles = to_unit(seeds, priors)
        weights = seeds["weight"].to_numpy() / seeds["weight"].sum()
        mean = weights @ particles
        sigma = np.sqrt(2.0 * (weights @ (particles - mean) ** 2)) + 1e-9
        last = old["stage"] == k
        old.loc[last, "distance"] = ex.distance(old[last], obs)
        old.loc[last, "weight"] = np.where(
            old.loc[last, "distance"] == 0,
            1.0 / proposal_density(to_unit(old[last], priors), particles, weights, sigma, priors),
            0.0)
        history, n_sim, target = [old], len(old), len(old) + args.more
        rows = [old[(old["stage"] == k) & (old["distance"] == 0)]]
        while n_sim < target:
            theta = propose(rng, particles, weights, sigma, priors, smp["batch"])
            sims = simulate(base, priors, obs, to_frame(theta, priors, n_sim), args.processes)
            n_sim += len(sims)
            sims["stage"] = k
            sims["weight"] = 1.0 / proposal_density(theta, particles, weights, sigma, priors)
            history.append(sims.assign(weight=np.where(sims["distance"] == 0, sims["weight"], 0.0)))
            rows.append(sims[sims["distance"] == 0])
            print(f"stage {k}: kept {sum(len(r) for r in rows)} after {n_sim} nights", flush=True)
        kept = pd.concat(rows, ignore_index=True)
    else:
        kept, history, n_sim, k = sample_stages(base, priors, obs, smp, cal["seed"], rng,
                                                args.processes)

    all_draws = pd.concat(history, ignore_index=True)
    all_draws["accepted"] = (all_draws["stage"] == k) & (all_draws["distance"] == 0) if k else (
        all_draws["distance"] == 0)
    OUT.mkdir(parents=True, exist_ok=True)
    all_draws.to_csv(OUT / "calibration_draws.csv", index=False)

    # Whole-night runs of the matching nights. A night stays when it still passes every test
    # with the statistics of the whole night.
    prior_cols = ["draw"] + list(priors)
    short = kept[kept["distance"] == 0]
    final = full_runs(base, priors, obs, short[prior_cols], args.processes)
    final = final.merge(short[["draw", "weight"]], on="draw")
    final = final[final["distance"] == 0].reset_index(drop=True)
    print(f"{len(short)} nights match in the shortened runs, {len(final)} in whole-night runs",
          flush=True)
    w = final["weight"].to_numpy() / final["weight"].sum()
    ess = 1.0 / np.sum(w ** 2)
    n_post = int(smp["posterior_draws"])
    pick = systematic_resample(rng, w, n_post)
    post = final.iloc[pick].reset_index(drop=True).assign(stage=k)
    post = post.rename(columns={"draw": "source_draw"})
    post.insert(0, "draw", rng.permutation(n_post))        # new ids give new random seeds
    post = post.sort_values("draw").drop(columns=["weight"])
    post["accepted"] = True
    post.to_csv(OUT / "posterior_draws.csv", index=False)
    params.write_manifest("calibration", {
        "base": str(args.base), "calibration": str(args.calibration), "simulations": n_sim,
        "stages": k, "matching_nights": len(final), "effective_sample_size": round(ess, 1),
        "posterior_draws": n_post, "seconds": round(time.time() - t0)})
    shutil.rmtree(PARTS, ignore_errors=True)
    print(f"{n_sim} nights in {time.time() - t0:.0f} s; {len(final)} match 2026 "
          f"(effective sample size {ess:.0f}); {n_post} posterior draws written")


if __name__ == "__main__":
    main()
