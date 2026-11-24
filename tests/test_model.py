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


def test_shared_lines_serve_in_parallel_within_their_staff():
    cfg = params.with_overrides(params.load(), {"crowd.n_total": 800, "bar.n_pour": 4})
    sim = Simulation(cfg, seed=5)
    sim.start()
    pour = [p for p in sim.points if p.kind == "pour"]
    assert [p.servers for p in pour] == [2, 2]
    most = 0
    for t in np.arange(4 * 3600.0, 9 * 3600.0, 300.0):
        sim.advance(t)
        for p in pour:
            assert len(p.serving) <= p.servers
            most = max(most, len(p.serving))
    assert most == 2


def test_nobody_stands_in_the_booth_or_the_cocktail_line():
    from sim.venue import Venue, _inside
    v = Venue(params.load())
    x, y = v.cell_x[v.spot_cells], v.cell_y[v.spot_cells]
    assert not _inside(x, y, v.cfg["booth"]).any()
    assert not _inside(x, y, v.cocktail_strip()).any()


def _passing_night(**change):
    """Calibration statistics of a night that passes every test, with some values changed."""
    m = {"early_median_min": 5.0, "obs_exchange_median_min": 50.0, "obs_exchange_reached": True,
         "occupancy_at_peak_obs_share": 0.95, "queue_cash_obs": 40.0, "queue_pour_obs": 90.0,
         "obs_left_share": 0.4}
    m.update(change)
    return pd.DataFrame([m])


def test_exchange_wait_between_the_limits_passes():
    from sim import experiments as ex
    obs = ex.load_calibration()["observations"]
    assert ex.distance(_passing_night(), obs).iloc[0] == 0


def test_exchange_wait_above_the_upper_limit_fails():
    from sim import experiments as ex
    obs = ex.load_calibration()["observations"]
    assert ex.distance(_passing_night(obs_exchange_median_min=80.0), obs).iloc[0] > 0


def test_exchange_median_not_reached_fails():
    from sim import experiments as ex
    obs = ex.load_calibration()["observations"]
    night = _passing_night(obs_exchange_median_min=50.0, obs_exchange_reached=False)
    assert ex.distance(night, obs).iloc[0] > 0


def test_km_median_flags_a_median_that_is_not_reached():
    from sim.experiments import km_median_reached
    assert km_median_reached([10, 20, 30, 40], [True, True, True, False]) == (20.0, True)
    assert km_median_reached([10, 20, 30, 40], [True, False, False, False]) == (40.0, False)


def test_pour_saving_takes_the_saving_off_each_beer():
    cfg = params.with_overrides(params.load(), {"crowd.n_total": 50, "bar.mode": "direct"})
    slow = Simulation(cfg, seed=1)
    fast = Simulation(params.with_overrides(cfg, {"bar.pour_saving_s": 12}), seed=1)
    slow.start()
    fast.start()
    t_slow = np.mean([slow._service_time("direct", 2) for _ in range(4000)])
    t_fast = np.mean([fast._service_time("direct", 2) for _ in range(4000)])
    assert abs((t_slow - t_fast) - 24.0) < 3.0


def test_reference_nights_unchanged():
    """The 2026 setup and the plan on three fixed draws and seeds give the stored metrics
    (tests/fixtures/reference_metrics.json, written by tests/make_fixture.py before the
    worker states were added). New metrics may be added; stored ones must not change."""
    import json
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import make_fixture
    stored = json.loads(make_fixture.FIXTURE.read_text())
    runs, obs = make_fixture.cases()
    for name, cfg, seed in runs:
        now = make_fixture.metrics_of(cfg, seed, obs)
        for key, value in stored[name].items():
            assert now[key] == value, f"{name}: {key} {now[key]} != {value}"


def _worker_night(**extra):
    over = {"bar.mode": "direct", "bar.n_pour": 4, "bar.s_pay_direct_s": 15,
            "bar.extra_pour": 2, "bar.extra_from": "19:00", "bar.extra_to": "23:00",
            "sellers.n": 3, "sellers.start": "18:00", "sellers.end": "02:30",
            "crowd.n_total": 600, **extra}
    cfg = params.with_overrides(params.load(), over)
    sim = Simulation(cfg, seed=5, record_frames=True, frame_every_s=300)
    drawn = []
    draw = sim._service_time

    def recording(kind, beers, **kw):
        out = draw(kind, beers, **kw)
        drawn.append(out)
        return out

    sim._service_time = recording
    return sim, sim.run(), drawn


def test_worker_states_add_up_to_the_staff():
    from sim.model import W_OFF
    sim, res, _ = _worker_night()
    servers = sum(p.servers for p in sim.points)
    for f in res["frames"]:
        assert len(f["w_state"]) == servers
        on = sum(p.servers for p in sim.points if p.is_open(f["t"]))
        assert int((f["w_state"] != W_OFF).sum()) == on
    s = res["series"]
    bar = s[["bar_off", "bar_idle", "bar_charging", "bar_pouring"]].sum(axis=1)
    assert (bar == servers).all()
    sellers = s[[c for c in s.columns if c.startswith("sellers_")]].sum(axis=1)
    assert (sellers == sim.k).all()
    assert (s["bar_off"] > 0).any() and (s["bar_charging"] > 0).any()


def test_charging_and_pouring_add_up_to_the_service_times():
    _, res, drawn = _worker_night()
    w = res["workers"]
    assert w["charging_s"].sum() + w["pouring_s"].sum() == pytest.approx(sum(drawn), rel=1e-9)
    assert w["charging_s"].sum() > 0 and w["pouring_s"].sum() > 0


def test_ticket_window_charges_and_exchange_pours():
    cfg = params.with_overrides(params.load(), {"crowd.n_total": 600})
    sim = Simulation(cfg, seed=3)
    res = sim.run()
    s = res["series"]
    w = res["workers"]
    assert w["charging_s"].sum() > 0 and w["pouring_s"].sum() > 0
    cash = sum(p.servers for p in sim.points if p.kind == "cash")
    assert (s["bar_charging"] <= cash).all()


def test_line_waits_count_people_in_service():
    """People still in line or at the counter count as not yet served (the calibration's
    shortened runs read this while services are under way)."""
    cfg = params.with_overrides(params.load(), {"crowd.n_total": 600})
    sim = Simulation(cfg, seed=4)
    sim.start()
    sim.advance(7 * 3600)
    minutes, served = sim.line_waits_so_far(0, 7 * 3600, "pour")
    assert len(minutes) == len(served) and len(minutes) > 0
