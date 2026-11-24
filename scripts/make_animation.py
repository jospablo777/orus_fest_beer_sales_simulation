"""Animated floor views of one calibrated night: the 2026 setup next to another setup.

Usage: uv run python scripts/make_animation.py [--scenario plan] [--clip night|changeover|all]
                                               [--langs en,es] [--draw N] [--still]
                                               [--processes P]
Clip windows, frame spacing and frame rate are set in config/report.yaml (clips). Every clip
and language is one job, and the jobs run in a process pool (sim/animate.py: render_clip).
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sim import experiments as ex  # noqa: E402
from sim import params  # noqa: E402
from sim.animate import render_clip  # noqa: E402

CLIPS = {name: {"window": (c["from"], c["to"]), "every_s": c["every_s"], "fps": c["fps"],
                "still": c.get("still")}
         for name, c in params.load(params.ROOT / "config" / "report.yaml")["clips"].items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default="plan")
    ap.add_argument("--clip", default="night", choices=list(CLIPS) + ["all"])
    ap.add_argument("--langs", default="en,es")
    ap.add_argument("--draw", type=int, default=None)
    ap.add_argument("--still", action="store_true",
                    help="write only the still image of the clip, to check the layout")
    ap.add_argument("--processes", type=int, default=None)
    args = ap.parse_args()
    clips = list(CLIPS) if args.clip == "all" else [args.clip]
    langs = args.langs.split(",")
    jobs = [(clip, CLIPS[clip], lang, args.scenario, args.draw, args.still, lang == langs[0])
            for clip in clips for lang in langs]
    for line in ex.pool(args.processes).imap_unordered(render_clip, jobs):
        print(line, flush=True)


if __name__ == "__main__":
    main()
