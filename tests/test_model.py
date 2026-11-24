"""Invariants of the model and unit checks of the crew selection.

Run: uv run --group dev pytest
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sim import params, staffing  # noqa: E402
from sim.model import GONE, NOT_ARRIVED, Simulation  # noqa: E402

SETUPS = {
    "ticket_window": {},
    "pay_at_station": {"bar.mode": "direct", "bar.n_pour": 6, "bar.s_pay_direct_s": 15},
    "pay_at_station_with_sellers": {"bar.mode": "direct", "bar.n_pour": 4, "sellers.n": 4,
                                    "sellers.start": "19:00", "sellers.end": "02:30"},
}


@pytest.fixture(scope="module", params=list(SETUPS))
def night(request):
    cfg = params.with_overrides(params.load(), {**SETUPS[request.param], "crowd.n_total": 600})
    sim = Simulation(cfg, seed=11)
    return sim, sim.run()


def test_beers_are_conserved(night):
    sim, res = night
    assert sim.beers.sum() == res["txn"]["beers"].sum() == res["series"]["beers_total"].iloc[-1]


def test_tickets_never_negative(night):
    sim, _ = night
    assert (sim.tickets >= 0).all()


def test_no_round_left_open(night):
    sim, _ = night
    assert not sim.orders
    assert (sim.ordered_by < 0).all()


def test_everyone_leaves(night):
    sim, _ = night
    assert np.isin(sim.state, [GONE, NOT_ARRIVED]).mean() > 0.97


def test_given_up_attempts_match_the_counters(night):
    sim, _ = night
    gave_up, attempts = sim.gave_up_so_far(0.0, sim.t_end + 1.0)
    bar_visits = sum(channel != "seller" for _, _, _, channel, *_ in sim.txn)
    assert gave_up == sim.balks + sim.reneges
    assert attempts == sim.balks + bar_visits


def test_waits_are_not_negative(night):
    _, res = night
    txn = res["txn"]
    assert (txn["t_served"] >= txn["t_join"] - 1e-9).all()


def test_floor_count_within_occupancy(night):
    _, res = night
    s = res["series"]
    assert (s["on_floor"] <= s["occupancy"]).all()


def test_friends_arrive_and_leave_together(night):
    sim, _ = night
    for members in list(sim.members.values())[:200]:
        assert np.ptp(sim.arrival[members]) == 0
        assert np.ptp(sim.leave[members]) == 0


def test_crew_choice_prefers_fewest_staff_hours():
    summary = pd.DataFrame({
        "n_total": [2000, 2000, 2000], "n_pour": [6, 8, 6], "sellers": [0, 0, 6],
        "share_met": [0.5, 0.95, 1.0], "staff_hours": [84.0, 112.0, 129.0],
        "staff": [6, 8, 12]})
    plan = staffing.choose(summary, 0.9)
    assert plan.loc[0, "n_pour"] == 8 and plan.loc[0, "sellers"] == 0


def test_exact_interval_all_nights_met():
    lo, hi = staffing.exact_interval(32, 32)
    assert hi == 1.0 and 0.89 < lo < 0.90


def test_resumable_run_continues_after_an_interruption(tmp_path, monkeypatch):
    from sim import experiments as ex

    obs = ex.load_calibration()["observations"]
    cfg = params.with_overrides(params.load(), {"crowd.n_total": 300})
    tasks = [(cfg, 20 + k, obs, {"draw": k}) for k in range(3)]
    run_many = ex.run_many
    whole = run_many(tasks, processes=1)
    parts, sizes = tmp_path / "parts", []

    def stops_at_second_batch(batch, processes=None):
        sizes.append(len(batch))
        if len(sizes) == 2:
            raise KeyboardInterrupt
        return run_many(batch, processes)

    def counts_batches(batch, processes=None):
        sizes.append(len(batch))
        return run_many(batch, processes)

    monkeypatch.setattr(ex, "run_many", stops_at_second_batch)
    with pytest.raises(KeyboardInterrupt):
        ex.run_many_resumable(tasks, parts, batch=2, processes=1)
    sizes.clear()
    monkeypatch.setattr(ex, "run_many", counts_batches)
    resumed = ex.run_many_resumable(tasks, parts, batch=2, processes=1)
    assert sizes == [1]                     # the stored batch of two tasks is not rerun
    assert not parts.exists()
    for a, b in zip(whole, resumed):
        pd.testing.assert_frame_equal(a, b)


def test_service_window_is_read_from_the_staffing_config():
    start, end = params.service_window()
    assert params.clock_to_min(start) < params.clock_to_min(end)


def test_worker_gives_the_same_night_in_a_spawned_process():
    """macOS starts worker processes with spawn. The worker function has to be importable
    there and return what it returns in this process."""
    import multiprocessing

    from sim import experiments as ex

    obs = ex.load_calibration()["observations"]
    cfg = params.with_overrides(params.load(), {"crowd.n_total": 300})
    task = (cfg, 31, obs, {"draw": 0})
    here = ex._task(task)
    with multiprocessing.get_context("spawn").Pool(1) as workers:
        there = workers.map(ex._task, [task])[0]
    pd.testing.assert_series_equal(pd.Series(here[0]), pd.Series(there[0]))
    pd.testing.assert_frame_equal(here[1], there[1])
