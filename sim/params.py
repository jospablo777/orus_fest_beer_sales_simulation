"""Configuration loading, overrides and clock conversion."""

from __future__ import annotations

import copy
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def clock_to_min(hhmm: str) -> int:
    """Minutes after 00:00 of the event day. Times before 08:00 belong to the next day."""
    h, m = (int(v) for v in hhmm.split(":"))
    minutes = 60 * h + m
    return minutes + 1440 if h < 8 else minutes


def min_to_clock(minutes: float) -> str:
    m = int(round(minutes)) % 1440
    return f"{m // 60:02d}:{m % 60:02d}"


def load(path: str | Path = ROOT / "config" / "base.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def service_window(path: str | Path = ROOT / "config" / "staffing.yaml") -> tuple[str, str]:
    """Clock window of the service target, as (from, to)."""
    window = load(path)["service_target"]["window"]
    return window["from"], window["to"]


def set_path(cfg: dict, dotted: str, value) -> None:
    keys = dotted.split(".")
    node = cfg
    for k in keys[:-1]:
        node = node[k]
    node[keys[-1]] = value


def with_overrides(cfg: dict, overrides: dict | None) -> dict:
    """Copy of cfg with dotted-path overrides applied, e.g. {"bar.n_cashiers": 3}."""
    out = copy.deepcopy(cfg)
    for k, v in (overrides or {}).items():
        set_path(out, k, v)
    return out


def write_manifest(step: str, extra: dict) -> None:
    """Append a record of a pipeline step to output/run_manifest.jsonl: time, git commit,
    hashes of the config files and package versions, plus step-specific fields."""
    import datetime
    import hashlib
    import json
    import platform
    import subprocess
    from importlib import metadata

    def sha(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:12]

    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                capture_output=True, text=True).stdout.strip() or None
    except OSError:
        commit = None
    def rel(value):
        # Paths are stored relative to the project root, so the record is the same on any machine.
        if isinstance(value, (str, Path)) and str(value).startswith(str(ROOT)):
            return str(Path(value).relative_to(ROOT))
        return value

    extra = {k: rel(val) for k, val in extra.items()}
    rec = {
        "step": step,
        "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "git_commit": commit,
        "python": platform.python_version(),
        "packages": {p: metadata.version(p) for p in ("numpy", "scipy", "pandas", "matplotlib",
                                                       "pyyaml")},
        "config_sha256": {f.name: sha(f) for f in sorted((ROOT / "config").glob("*.yaml"))},
        **extra,
    }
    out = ROOT / "output" / "run_manifest.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "a") as f:
        f.write(json.dumps(rec, default=str) + "\n")
