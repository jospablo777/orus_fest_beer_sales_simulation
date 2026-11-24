"""Unit checks of the helpers that turn the tables into page text.

Run: uv run --group dev pytest
"""

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "site"))

import report_values  # noqa: E402
from _organizer import what_if_status  # noqa: E402


def test_long_date_uses_month_names_without_locale():
    assert report_values.long_date("2026-11-24", "es") == "24 de noviembre de 2026"
    assert report_values.long_date("2026-01-05", "en") == "5 January 2026"


def test_shortest_interval_holds_the_share():
    x = pd.Series([2] * 20 + [3] * 50 + [4] * 22 + [5] * 6 + [6] * 2)
    lo, hi, k, n = report_values.shortest_interval(x, 0.9)
    assert (lo, hi, k, n) == (2, 4, 92, 100)


def test_shortest_interval_prefers_the_range_with_more_values():
    x = pd.Series([1] * 5 + [2] * 45 + [3] * 45 + [4] * 5)
    lo, hi, k, _ = report_values.shortest_interval(x, 0.9)
    assert (lo, hi, k) == (2, 3, 90)


def test_what_if_status_labels():
    r = {"reliability": 0.9,
         "wi_a_met": 58, "wi_a_nights": 64, "wi_a_met_hi": 0.97,
         "wi_b_met": 55, "wi_b_nights": 64, "wi_b_met_hi": 0.93,
         "wi_c_met": 31, "wi_c_nights": 64, "wi_c_met_hi": 0.61}
    assert what_if_status(r, "a") == "met"
    assert what_if_status(r, "b") == "near"
    assert what_if_status(r, "c") == "far"


def test_candidates_within_five_percent_and_three_levels():
    from sim import staffing
    s = pd.DataFrame({"n_total": [2000] * 5, "n_pour": [6, 8, 10, 12, 4],
                      "sellers": [15, 12, 9, 6, 15], "staff": [21, 20, 19, 18, 19],
                      "staff_hours": [211.5, 214.0, 216.5, 230.0, 183.5],
                      "share_met": [62 / 64, 61 / 64, 1.0, 61 / 64, 58 / 64],
                      "nights_met": [62, 61, 64, 61, 58], "nights": [64] * 5})
    c = staffing.candidates(s, 0.95)
    assert set(zip(c["n_pour"], c["sellers"])) == {(6, 15), (8, 12), (10, 9)}
    plan = staffing.plan_table(s, 0.9, 0.95, 1.0)
    assert list(plan["level"]) == ["minimum", "recommended", "complete"]
    assert tuple(plan.loc[plan["level"] == "complete", ["n_pour", "sellers"]].iloc[0]) == (10, 9)
    assert (plan["chosen_by"] == "fewest staff hours").all()


def test_summary_page_stays_short():
    import _organizer
    assert _organizer.running_words("es") <= 300
