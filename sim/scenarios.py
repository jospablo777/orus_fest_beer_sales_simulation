"""Scenario definitions from config/scenarios.yaml.

An override value that is a string starting with "=" is evaluated against the calibrated
draw (see EXPR_NAMES). Everything else is used as written.
"""

from __future__ import annotations

from . import params

EXPR_FUNCS = {"min": min, "max": max, "round": round}


def _expr_names(cfg: dict) -> dict:
    b, c = cfg["bar"], cfg["crowd"]
    return {"n_pour": b["n_pour"], "n_cashiers": b["n_cashiers"],
            "bundle_mean": b["bundle_mean"], "s_cash_mean_s": b["s_cash_mean_s"],
            "s_pour_mean_s": b["s_pour_mean_s"], "n_total": c["n_total"],
            "rate_mean_per_h": c["rate_mean_per_h"]}


def _plan_names() -> dict:
    """plan_taps and plan_sellers (recommended crew) and plan_min_taps and plan_min_sellers
    (minimum crew), chosen by the staffing grid for the ticket level in config/report.yaml
    (plan_tickets)."""
    from . import staffing
    tickets = params.load(params.ROOT / "config" / "report.yaml")["plan_tickets"]
    return staffing.plan_crew(int(tickets))


def resolve(overrides: dict, cfg: dict) -> dict:
    names = _expr_names(cfg)
    if any(isinstance(v, str) and v.startswith("=") and "plan_" in v
           for v in (overrides or {}).values()):
        names.update(_plan_names())
    out = {}
    for k, v in (overrides or {}).items():
        if isinstance(v, str) and v.startswith("="):
            v = eval(v[1:], {"__builtins__": {}, **EXPR_FUNCS}, names)  # noqa: S307
        out[k] = v
    return out


def load(path=params.ROOT / "config" / "scenarios.yaml") -> dict:
    """Ordered dict: key -> {"label", "family", "overrides"}. Families: main, what_if."""
    spec = params.load(path)
    out = {}
    for key, sc in spec.get("scenarios", {}).items():
        out[key] = {"label": sc["label"], "family": "main", "overrides": sc.get("overrides", {})}
    for key, sc in spec.get("what_if", {}).items():
        if "on" in sc or True in sc:
            raise ValueError(f"what_if.{key}: use `based_on`, YAML reads `on` as a boolean")
        base = out[sc["based_on"]]["overrides"] if sc.get("based_on") else {}
        out[key] = {"label": sc["label"], "family": "what_if",
                    "overrides": {**base, **sc.get("overrides", {})}}
    return out


def apply(cfg: dict, scenario: dict) -> dict:
    return params.with_overrides(cfg, resolve(scenario["overrides"], cfg))
