"""Chooses the recommended and complete crews by their results under stress cases.

At each ticket level of the staffing grid, the candidates of a level are the crews that reach
its reliability with staff hours within 5% of the fewest (sim/staffing.py: candidates). Every
candidate runs the stress cases of config/staffing.yaml on the staffing nights and seeds. The
chosen crew has the highest lowest share of nights that meet the target across the stress
cases; ties go to the higher mean share across cases, then to fewer staff hours.

Writes
    output/runs/crew_mixes_runs.csv      one row per night, candidate and stress case
    output/tables/crew_mixes.csv         nights met per candidate and case, with exact
                                         intervals, the McNemar test against the chosen crew
                                         (Holm-adjusted) and the counter width per station
    output/tables/staffing_plan.csv      recommended and complete rows replaced by the chosen
                                         crews (chosen_by = "stress cases")
Usage: uv run python scripts/run_crew_mixes.py [--processes P]
"""

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sim import experiments as ex  # noqa: E402
from sim import params, staffing  # noqa: E402
from sim import scenarios as sc  # noqa: E402

RUNS = params.ROOT / "output" / "runs"
TAB = params.ROOT / "output" / "tables"


def counter_per_station(n_pour: int) -> float:
    """Meters of counter per station between pour_x_min and pour_x_max, without the gap left
    at the cocktail line (sim/venue.py: station_x)."""
    base = params.load()
    b, c = base["bar"], base["venue"].get("cocktail_line")
    length = b["pour_x_max"] - b["pour_x_min"]
    if c and b["pour_x_min"] < c["x"] < b["pour_x_max"]:
        length -= 2 * (c["half_width"] + 0.7)
    return length / n_pour


def resolve(over: dict, cfg: dict, crew: tuple[int, int]) -> dict:
    s = cfg["sellers"]
    names = {**sc._expr_names(cfg), "taps": crew[0], "sellers": crew[1],
             "s_sale_s": s["s_sale_s"], "restock_s": s["restock_s"],
             "speed_factor": s["speed_factor"]}
    out = {}
    for k, v in over.items():
        if isinstance(v, str) and v.startswith("="):
            v = eval(v[1:], {"__builtins__": {}, **sc.EXPR_FUNCS}, names)  # noqa: S307
            v = int(v) if isinstance(v, float) and v.is_integer() else v
        out[k] = v
    return out


def holm(p: pd.Series) -> pd.Series:
    order = p.sort_values().index
    adj, running, m = pd.Series(index=p.index, dtype=float), 0.0, len(p)
    for k, idx in enumerate(order):
        running = max(running, min((m - k) * p[idx], 1.0))
        adj[idx] = running
    return adj


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--processes", type=int, default=None)
    args = ap.parse_args()
    spec = params.load(params.ROOT / "config" / "staffing.yaml")
    target = spec["service_target"]
    cal = ex.load_calibration()
    base = params.load()
    draws = pd.read_csv(RUNS / "posterior_draws.csv").head(spec["draws"])
    cols = [c for c in draws.columns if c in cal["priors"]]
    summary = pd.read_csv(TAB / "staffing_reliability.csv")
    summary = summary[summary["n_total"].isin(spec["grid"]["crowd.n_total"])]
    levels = {"recommended": spec["reliability_recommended"],
              "complete": spec["reliability_complete"]}
    cands = pd.concat([staffing.candidates(summary, r).assign(level=lv)
                       for lv, r in levels.items()], ignore_index=True)
    crews = cands[["n_total", "n_pour", "sellers"]].drop_duplicates()
    cases = spec["stress_cases"]

    tasks = []
    for _, row in draws.iterrows():
        cfg0 = ex.draw_config(base, row[cols], cal["priors"])
        cfg0 = params.with_overrides(cfg0, sc.resolve(spec["setup"], cfg0))
        for c in crews.itertuples(index=False):
            crew = (int(c.n_pour), int(c.sellers))
            cfg1 = params.with_overrides(cfg0, {"crowd.n_total": int(c.n_total),
                                                "bar.n_pour": crew[0], "sellers.n": crew[1]})
            for name, over in cases.items():
                cfg = params.with_overrides(cfg1, resolve(over, cfg1, crew))
                tasks.append((cfg, 90_000 + int(row["draw"]), cal["observations"],
                              {"draw": int(row["draw"]), "n_total": int(c.n_total),
                               "n_pour": crew[0], "sellers": crew[1], "case": name}))
    t0 = time.time()
    metrics, _, _ = ex.run_many_resumable(tasks, RUNS / "parts_mixes", processes=args.processes)
    print(f"{len(tasks)} runs in {time.time() - t0:.0f} s")
    metrics.to_csv(RUNS / "crew_mixes_runs.csv", index=False)
    metrics["met"] = ((metrics["evening_p90_min"] <= target["evening_p90_min"])
                      & (metrics["abandon_share"] <= target["abandon_share"]))

    keys = ["n_total", "n_pour", "sellers"]
    cell = metrics.groupby(keys + ["case"]).agg(nights=("met", "size"),
                                                nights_met=("met", "sum"),
                                                wait_median=("evening_p90_min", "median"),
                                                wait_bad=("evening_p90_min",
                                                          lambda v: v.quantile(0.9))
                                                ).reset_index()
    base_rows = summary[keys + ["nights", "nights_met", "wait_median", "wait_bad_night",
                                "staff", "staff_hours"]].rename(
        columns={"wait_bad_night": "wait_bad"})
    cell = pd.concat([cell, base_rows.drop(columns=["staff", "staff_hours"])
                      .merge(crews, on=keys).assign(case="base")], ignore_index=True)
    cell["share_met"] = cell["nights_met"] / cell["nights"]
    ci = [staffing.exact_interval(k, n) for k, n in zip(cell["nights_met"], cell["nights"])]
    cell["share_lo"], cell["share_hi"] = [c[0] for c in ci], [c[1] for c in ci]

    rows, chosen = [], {}
    for (n_total, level), cand in cands.groupby(["n_total", "level"]):
        stress = cell[(cell["n_total"] == n_total) & (cell["case"] != "base")]
        score = []
        for c in cand.itertuples(index=False):
            s = stress[(stress["n_pour"] == c.n_pour) & (stress["sellers"] == c.sellers)]
            score.append((-s["share_met"].min(), -s["share_met"].mean(), c.staff_hours,
                          int(c.n_pour), int(c.sellers)))
        best = sorted(score)[0]
        chosen[(n_total, level)] = (best[3], best[4])
        win = metrics[(metrics["n_total"] == n_total) & (metrics["n_pour"] == best[3])
                      & (metrics["sellers"] == best[4])].set_index(["case", "draw"])["met"]
        for (worst, mean, hours, taps, sellers) in score:
            other = metrics[(metrics["n_total"] == n_total) & (metrics["n_pour"] == taps)
                            & (metrics["sellers"] == sellers)].set_index(["case", "draw"])["met"]
            for case in cases:
                a, b = win.loc[case], other.loc[case].reindex(win.loc[case].index)
                gain, loss = int((a & ~b).sum()), int((~a & b).sum())
                p = stats.binomtest(gain, gain + loss).pvalue if gain + loss else 1.0
                rows.append({"n_total": n_total, "level": level, "n_pour": taps,
                             "sellers": sellers, "case": case, "mcnemar_p": float(p)})
    tests = pd.DataFrame(rows)
    tests["mcnemar_p_holm"] = holm(tests["mcnemar_p"]).values
    out = cands[["n_total", "level"] + keys[1:] + ["staff", "staff_hours"]].merge(
        cell, on=keys)
    out = out.merge(tests, on=["n_total", "level", "n_pour", "sellers", "case"], how="left")
    out["chosen"] = [chosen[(n, lv)] == (t, s) for n, lv, t, s in
                     zip(out["n_total"], out["level"], out["n_pour"], out["sellers"])]
    out["counter_m_per_station"] = out["n_pour"].map(counter_per_station)
    out["counter_under_1m"] = out["counter_m_per_station"] < 1.0
    worst = out[out["case"] != "base"].groupby(["n_total", "level", "n_pour", "sellers"])
    out = out.merge(worst["share_met"].min().rename("worst_share").reset_index(),
                    on=["n_total", "level", "n_pour", "sellers"])
    out = out.merge(worst["share_met"].mean().rename("mean_share").reset_index(),
                    on=["n_total", "level", "n_pour", "sellers"])
    out.sort_values(["n_total", "level", "staff_hours", "n_pour", "case"]).to_csv(
        TAB / "crew_mixes.csv", index=False)

    plan = pd.read_csv(staffing.PLAN_FILE)
    if "chosen_by" not in plan:
        plan["chosen_by"] = "fewest staff hours"
    for (n_total, level), (taps, sellers) in chosen.items():
        mask = (plan["n_total"] == n_total) & (plan["level"] == level)
        row = summary[(summary["n_total"] == n_total) & (summary["n_pour"] == taps)
                      & (summary["sellers"] == sellers)].iloc[0]
        new = row.to_dict()
        new.update({"level": level, "fallback": False, "chosen_by": "stress cases"})
        plan = pd.concat([plan[~mask], pd.DataFrame([new])], ignore_index=True)
    order = {"minimum": 0, "recommended": 1, "complete": 2}
    plan = (plan.assign(k=plan["level"].map(order)).sort_values(["n_total", "k"])
            .drop(columns="k")[list(plan.columns)])
    for col in ("n_total", "n_pour", "sellers", "nights", "nights_met"):
        plan[col] = plan[col].astype(int)
    plan.to_csv(staffing.PLAN_FILE, index=False)
    show = out[out["case"] != "base"].groupby(["n_total", "level", "n_pour", "sellers"]).agg(
        staff_hours=("staff_hours", "first"), worst=("share_met", "min"),
        mean=("share_met", "mean"), chosen=("chosen", "first")).reset_index()
    print(show.to_string(index=False))
    print(plan[["n_total", "level", "n_pour", "sellers", "nights_met", "chosen_by"]]
          .to_string(index=False))


if __name__ == "__main__":
    main()
