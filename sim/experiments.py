"""Calibration draws, scenarios and per-run metrics.

Runs execute in a process pool, one simulated night per process at a time, so a step is
faster by about the number of CPU cores. Each run gets its seed from its task, and the
number of processes does not change any result. The worker functions are module-level
functions of the package, which keeps them importable when processes are spawned (the
default on macOS).
"""

from __future__ import annotations

import atexit
import hashlib
import json
import os
import shutil
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

from . import params
from .model import Simulation
from .params import clock_to_min, min_to_clock

HEADLINERS = ("Peter Heppner", "Solitary Experiments")
SERVICE_WINDOW = params.service_window()


_POOLS: dict[int, Pool] = {}


def pool(processes: int | None = None) -> Pool:
    """The process pool of this program for a number of processes (default: every CPU
    core). It is created on first use and kept, so later batches do not start the worker
    processes again."""
    n = processes or os.cpu_count() or 1
    if n not in _POOLS:
        _POOLS[n] = Pool(n)
        atexit.register(_POOLS[n].terminate)
    return _POOLS[n]


def load_calibration(path=params.ROOT / "config" / "calibration.yaml") -> dict:
    return params.load(path)


def latin_hypercube(priors: dict, n: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    cols = {}
    for name, spec in priors.items():
        u = (rng.permutation(n) + rng.random(n)) / n
        kind = spec["type"]
        if kind == "float":
            cols[name] = spec["low"] + u * (spec["high"] - spec["low"])
        elif kind == "int":
            cols[name] = np.round(spec["low"] + u * (spec["high"] - spec["low"])).astype(int)
        elif kind == "clock":
            a, b = clock_to_min(spec["low"]), clock_to_min(spec["high"])
            cols[name] = [min_to_clock(a + x * (b - a)) for x in u]
        elif kind == "choice":
            opts = spec["values"]
            cols[name] = [opts[min(int(x * len(opts)), len(opts) - 1)] for x in u]
        else:
            raise ValueError(f"unknown prior type {kind!r} for {name}")
    df = pd.DataFrame(cols)
    df.insert(0, "draw", np.arange(n))
    return df


def _window(txn, a, b, col="clock_join_min"):
    lo, hi = clock_to_min(a), clock_to_min(b)
    return txn[(txn[col] >= lo) & (txn[col] < hi)]


def km_median_reached(minutes, served) -> tuple[float, bool]:
    """Kaplan-Meier median of the minutes until service, and whether it was reached. A person
    who gave up or is still in line is censored: the wait was at least the recorded time.
    When the share served never reaches one half the median is not reached; the longest
    recorded time is then returned as a lower bound with reached = False. NaN without
    records."""
    minutes, served = np.asarray(minutes, float), np.asarray(served, bool)
    if minutes.size == 0:
        return float("nan"), False
    order = np.lexsort((~served, minutes))          # at equal times, served people first
    t, e = minutes[order], served[order]
    at_risk = np.arange(len(t), 0, -1)
    waiting = np.cumprod(np.where(e, 1.0 - 1.0 / at_risk, 1.0))
    hit = np.flatnonzero(waiting <= 0.5)
    return (float(t[hit[0]]), True) if hit.size else (float(t.max()), False)


def km_median(minutes, served) -> float:
    """km_median_reached without the flag."""
    return km_median_reached(minutes, served)[0]


def run_metrics(cfg: dict, seed: int, obs: dict) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    """One run. Returns scalar metrics, a 5-minute series and 15-minute wait quantiles."""
    sim = Simulation(cfg, seed=seed)
    res = sim.run()
    s, txn = res["series"], res["txn"]
    # time in line counts attendees who gave up (channel "renege") as well as buyers
    bar = txn[txn["channel"] != "seller"] if len(txn) else txn

    def med(df):
        return float(df["line_min"].median()) if len(df) else np.nan

    def until_served(df, minutes="line_min"):
        if not len(df):
            return np.nan
        return km_median(df[minutes], df["channel"] != "renege")

    early = _window(bar, obs["early_wait"]["from"], obs["early_wait"]["to"])

    def window_stats(spec):
        """Minutes until service and line lengths in one clock window. `exchange` is the
        wait in a beer exchange line, the quantity the 2026 observer reported. `ticket` is
        the wait at the ticket window and `buyer` the whole visit of a person who started
        without tickets. `all` covers every visit to a bar line; with payment at the station
        nobody passes a cashier and it is the only one of the four with records."""
        w = _window(bar, spec["from"], spec["to"])
        out = {"all": until_served(w), "buyer": np.nan, "ticket": np.nan, "exchange": np.nan,
               "exchange_reached": False}
        if len(w):
            via = w[w["via_cashier"]]
            out["buyer"] = until_served(via if len(via) >= 5 else w)
            if len(via):
                left_at_window = via["line_kind"] == "cash"
                minutes = np.where(left_at_window, via["last_line_min"],
                                   (via["t_line"] - via["t_join"]) / 60.0)
                out["ticket"] = km_median(minutes, ~left_at_window)
            ex_line = _window(bar[bar["line_kind"] == "pour"], spec["from"], spec["to"],
                              col="clock_line_min")
            if len(ex_line):
                out["exchange"], out["exchange_reached"] = km_median_reached(
                    ex_line["last_line_min"], ex_line["channel"] != "renege")
        lo, hi = clock_to_min(spec["from"]), clock_to_min(spec["to"])
        in_w = s[(s["clock_min"] >= lo) & (s["clock_min"] <= hi)]
        out["queue_cash"] = float(in_w["queue_cash"].mean())
        out["queue_pour"] = float(in_w["queue_pour"].mean())
        return out

    seen, night = window_stats(obs["long_wait"]), window_stats(obs["headliner_window"])
    # attempts that joined a bar line in the window and left it before service
    gave_spec = obs.get("gave_up", obs["long_wait"])
    gave_up, attempts = sim.gave_up_so_far(
        (clock_to_min(gave_spec["from"]) - sim.t0_min) * 60.0,
        (clock_to_min(gave_spec["to"]) - sim.t0_min) * 60.0)
    buys = bar[bar["beers"] > 0] if len(bar) else bar
    peak_occ_clock = float(s.loc[s["occupancy"].idxmax(), "clock_min"])
    at = clock_to_min(obs["peak_occupancy"]["at"])
    occ_at = float(s.loc[(s["clock_min"] - at).abs().idxmin(), "occupancy"])

    # minutes of headliner sets that attendees spent in lines or waiting for a seller
    lost = 0.0
    for k, name in enumerate(sim.sched.names):
        if name in HEADLINERS and len(txn):
            a, b = sim.sched.start[k], sim.sched.end[k]
            ov = np.clip(np.minimum(txn["t_served"], b) - np.maximum(txn["t_join"], a), 0, None)
            lost += ov.sum() / 60.0
    buyers = txn[txn["beers"] > 0] if len(txn) else txn

    drinkers = int(sim.drinker[sim.arrival <= sim.t_end].sum())
    # staff: people selling at the busiest moment; staff_hours: paid selling hours
    t_end_h = sim.t_end / 3600
    staff_h = 0.0
    staff = 0
    for p in sim.points:
        a = max(p.open_from, 0.0) / 3600
        b = min(p.open_to, sim.t_end) / 3600
        staff_h += p.servers * max(b - a, 0.0)
        staff += p.servers
    if sim.k:
        staff_h += sim.k * (sim.s_end - sim.s_start) / 3600
        staff += sim.k
    del t_end_h
    m = {
        "early_median_min": med(early),
        "obs_median_min": seen["all"],
        "obs_buyer_median_min": seen["buyer"],
        "obs_ticket_median_min": seen["ticket"],
        "obs_exchange_median_min": seen["exchange"],
        "obs_exchange_reached": seen["exchange_reached"],
        "queue_cash_obs": seen["queue_cash"],
        "queue_pour_obs": seen["queue_pour"],
        "obs_left_share": gave_up / attempts if attempts else np.nan,
        "night_median_min": night["all"],
        "night_buyer_median_min": night["buyer"],
        "night_ticket_median_min": night["ticket"],
        "night_exchange_median_min": night["exchange"],
        "queue_cash_night": night["queue_cash"],
        "queue_pour_night": night["queue_pour"],
        "evening_p90_min": float(_window(txn, *SERVICE_WINDOW)["line_min"].quantile(0.9))
        if len(txn) else np.nan,
        "peak_occupancy": int(s["occupancy"].max()),
        "peak_occupancy_clock": peak_occ_clock,
        "occupancy_at_peak_obs_share": occ_at / max(float(s["occupancy"].max()), 1.0),
        "beers_total": int(s["beers_total"].iloc[-1]),
        "beers_seller": int(txn.loc[txn["channel"] == "seller", "beers"].sum()) if len(txn) else 0,
        "beers_per_drinker": float(s["beers_total"].iloc[-1]) / max(drinkers, 1),
        "lost_attempts": int(s["balks"].iloc[-1] + s["reneges"].iloc[-1]),
        "max_in_lines": int(s["in_lines_total"].max()),
        "headliner_min_in_lines": lost,
        "headliner_min_per_buyer": lost / max(len(_window(buyers, "22:00", "01:15",
                                                          "clock_served_min")), 1),
        "staff": staff,
        "staff_hours": round(staff_h, 1),
        "beers_per_staff_hour": float(s["beers_total"].iloc[-1]) / max(staff_h, 1e-9),
        "front_density_max": float(s["front_density"].max()),
        "floor_density_peak": float(s["on_floor"].max()) / sim.venue.floor_cells.size,
        "on_floor_peak": int(s["on_floor"].max()),
        "heavy6_share": float((sim.beers >= 6).mean()),
        "heavy8_share": float((sim.beers >= 8).mean()),
        "line_hours": float(bar["line_min"].sum() / 60.0) if len(bar) else 0.0,
        "within5_share": float((buys["line_min"] <= 5).mean()) if len(buys) else np.nan,
        "beers_peak_hour": float(s["beers_total"].diff(60).max()),
        "abandon_share": int(s["balks"].iloc[-1] + s["reneges"].iloc[-1])
        / max(int(s["balks"].iloc[-1] + s["reneges"].iloc[-1]) + len(buyers), 1),
    }

    s5 = s[(s["t_min"] % 5) == 0][["clock_min", "occupancy", "in_lines_total", "queue_cash",
                                   "queue_pour", "queue_satellite", "wait_seller",
                                   "beers_total", "front_density", "act", "band_playing"]].copy()
    if len(txn):
        bins = (txn["clock_join_min"] // 15) * 15
        w = txn.groupby(bins)["line_min"].agg(
            median="median", p90=lambda v: v.quantile(0.9), n="size").reset_index()
        w = w.rename(columns={"clock_join_min": "clock_min"})
    else:
        w = pd.DataFrame(columns=["clock_min", "median", "p90", "n"])
    return m, s5, w


def calibration_metrics(cfg: dict, seed: int, obs: dict) -> dict:
    """The statistics of the calibration tests from a shortened run of the 2026 setup.

    The occupancy test depends only on arrival and departure times and is computed without
    simulating. The run stops after the early window when the early test fails, and
    otherwise after the long-wait window plus the larger of 60 minutes and the upper limit
    of the test plus 10, so that everyone who joined in the window is followed past that
    limit. People still in an exchange line at that time count with the minutes they have
    waited so far, as a lower bound.
    """
    sim = Simulation(cfg, seed=seed)
    sec = lambda clock: (clock_to_min(clock) - sim.t0_min) * 60.0  # noqa: E731
    grid = np.arange(0.0, sim.t_end, 300.0)
    inside = ((sim.arrival[None, :] <= grid[:, None]) & (sim.leave[None, :] > grid[:, None])).sum(1)
    at = sec(obs["peak_occupancy"]["at"])
    occ_at = ((sim.arrival <= at) & (sim.leave > at)).sum()
    m = {"occupancy_at_peak_obs_share": occ_at / max(inside.max(), 1), "peak_occupancy": int(inside.max()),
         "obs_exchange_median_min": np.nan, "obs_exchange_reached": False,
         "queue_cash_obs": np.nan, "queue_pour_obs": np.nan, "obs_left_share": np.nan}
    e, lw = obs["early_wait"], obs["long_wait"]
    sim.start()
    sim.advance(sec(e["to"]) + 1200.0)
    early = sim.waits_so_far(sec(e["from"]), sec(e["to"]))
    m["early_median_min"] = float(np.median(early)) if early.size else np.nan
    if not m["early_median_min"] <= e["max_median_min"]:
        return m
    follow_min = max(60.0, lw.get("max_median_min", 0.0) + 10.0)
    sim.advance(sec(lw["to"]) + 60.0 * follow_min)
    m["obs_exchange_median_min"], m["obs_exchange_reached"] = km_median_reached(
        *sim.line_waits_so_far(sec(lw["from"]), sec(lw["to"]), "pour"))
    s = pd.DataFrame(sim._rows)
    lo, hi = clock_to_min(lw["from"]), clock_to_min(lw["to"])
    in_w = s[(s["clock_min"] >= lo) & (s["clock_min"] <= hi)]
    m["queue_cash_obs"] = float(in_w["queue_cash"].mean())
    m["queue_pour_obs"] = float(in_w["queue_pour"].mean())
    gave_spec = obs.get("gave_up", lw)
    left, joined = sim.gave_up_so_far(sec(gave_spec["from"]), sec(gave_spec["to"]))
    m["obs_left_share"] = left / joined if joined else np.nan
    return m


def _calibration_task(args):
    cfg, seed, obs, tags = args
    m = calibration_metrics(cfg, seed, obs)
    m.update(tags)
    return m


def run_calibration_tasks(tasks, processes=None) -> pd.DataFrame:
    return pd.DataFrame(pool(processes).map(_calibration_task, tasks, chunksize=1))


def _task(args):
    cfg, seed, obs, tags = args
    m, s5, w = run_metrics(cfg, seed, obs)
    m.update(tags)
    for k, v in tags.items():
        s5[k] = v
        w[k] = v
    return m, s5, w


def run_many(tasks, processes=None):
    out = pool(processes).map(_task, tasks, chunksize=1)
    metrics = pd.DataFrame([o[0] for o in out])
    series = pd.concat([o[1] for o in out], ignore_index=True)
    waits = pd.concat([o[2] for o in out], ignore_index=True)
    return metrics, series, waits


def run_many_resumable(tasks, parts_dir, batch: int = 96, processes=None):
    """run_many in batches stored under parts_dir. A later call with the same tasks skips
    the stored batches, so an interrupted run continues where it stopped. The stored
    batches are removed when the last one finishes."""
    parts_dir = Path(parts_dir)
    key = hashlib.sha256(json.dumps(tasks, sort_keys=True, default=str).encode()).hexdigest()
    key_file = parts_dir / "tasks.sha256"
    if parts_dir.exists() and (not key_file.exists() or key_file.read_text() != key):
        shutil.rmtree(parts_dir)
    parts_dir.mkdir(parents=True, exist_ok=True)
    key_file.write_text(key)
    names = ("metrics", "series", "waits")
    starts = range(0, len(tasks), batch)
    for k, lo in enumerate(starts):
        done = parts_dir / f"done_{k:04d}"
        if done.exists():
            continue
        out = run_many(tasks[lo:lo + batch], processes)
        for name, df in zip(names, out):
            df.to_pickle(parts_dir / f"{name}_{k:04d}.pkl")
        done.touch()
        print(f"batch {k + 1} of {len(starts)} stored", flush=True)
    out = tuple(pd.concat([pd.read_pickle(parts_dir / f"{name}_{k:04d}.pkl")
                           for k in range(len(starts))], ignore_index=True)
                for name in names)
    shutil.rmtree(parts_dir)
    return out


def draw_config(base: dict, row: pd.Series, priors: dict) -> dict:
    """Base config with one draw applied. Integer and choice priors are cast back to int,
    since a pandas row of numeric columns arrives as float."""
    out = {}
    for k, v in row.items():
        if k not in priors:
            continue
        v = v.item() if hasattr(v, "item") else v
        if priors[k]["type"] in ("int", "choice") and isinstance(v, float) and v.is_integer():
            v = int(v)
        out[k] = v
    return params.with_overrides(base, out)


def distance(metrics: pd.DataFrame, obs: dict) -> pd.Series:
    """Distance of a simulated night from the 2026 observations: the sum of the relative
    shortfalls of each test. Zero means every test passes."""
    def short(value, limit, scale, above=True):
        gap = (limit - value) if above else (value - limit)
        return np.clip(gap / scale, 0.0, 3.0)

    e, pk = obs["early_wait"], obs["long_wait"]
    d = (short(metrics["early_median_min"], e["max_median_min"], e["max_median_min"], above=False)
         + short(metrics["obs_exchange_median_min"], pk["min_median_min"], pk["min_median_min"])
         + short(metrics["occupancy_at_peak_obs_share"],
                 obs["peak_occupancy"]["min_share_of_max"], 0.1))
    if "max_median_min" in pk:
        # A median that was not reached is above any limit the run could follow.
        upper = short(metrics["obs_exchange_median_min"], pk["max_median_min"],
                      pk["max_median_min"], above=False)
        reached = metrics.get("obs_exchange_reached")
        if reached is not None:
            upper = np.where(reached.eq(True).to_numpy(), upper, np.maximum(upper, 1.0))
        d = d + upper
    both = obs.get("both_lines")
    if both:
        d = (d + short(metrics["queue_cash_obs"], both["min_people"], both["min_people"])
             + short(metrics["queue_pour_obs"], both["min_people"], both["min_people"]))
    gave = obs.get("gave_up")
    if gave:
        d = d + short(metrics["obs_left_share"], gave["min_share"], gave["min_share"])
    return d.fillna(15.0)


def accepted(metrics: pd.DataFrame, obs: dict) -> pd.Series:
    return distance(metrics, obs) == 0
