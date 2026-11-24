#!/usr/bin/env bash
# Full pipeline: calibration, staffing, scenarios, videos, R analysis, summary figures, site.
# Requires uv (Python), rv (R) and ffmpeg. Run from the project root.
#
# Every simulation step runs one simulated night per process and uses every CPU core.
# PROCESSES=6 ./scripts/run_all.sh limits the number of processes.
set -euo pipefail
cd "$(dirname "$0")/.."

# R parses the UTF-8 labels in analysis/figures.R, so it needs a UTF-8 locale.
if [[ -z "${LC_ALL:-}" ]]; then
  if locale -a 2>/dev/null | grep -qix "C.UTF-8"; then
    export LC_ALL=C.UTF-8
  else
    export LC_ALL=en_US.UTF-8
  fi
fi
# One thread per process: the process pool already uses every core.
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 MKL_NUM_THREADS=1

# Expanded as ${workers[@]+...} because bash 3.2 (macOS) rejects an empty array under set -u.
workers=()
if [[ -n "${PROCESSES:-}" ]]; then
  workers=(--processes "$PROCESSES")
fi

uv sync --group site
rv sync
rv activate

uv run python scripts/run_calibration.py ${workers[@]+"${workers[@]}"}            # posterior_draws.csv
uv run python scripts/run_staffing.py ${workers[@]+"${workers[@]}"}               # crew by reliability, staffing_plan.csv
uv run python scripts/run_serving.py ${workers[@]+"${workers[@]}"}                # serving options, needs the staffing grid
uv run python scripts/run_scenarios.py ${workers[@]+"${workers[@]}"}              # needs the plan crew from the step above
uv run python scripts/make_animation.py --clip all ${workers[@]+"${workers[@]}"}  # videos in English and Spanish
Rscript analysis/figures.R   # picks up rv/library through the .Rprofile written by `rv activate`
uv run python scripts/make_summary.py               # organizer figures, needs the R tables
if compgen -G "output/sensitivity/*/runs" > /dev/null; then
  uv run python scripts/compare_calibrations.py     # against every run in output/sensitivity
fi
./scripts/render_site.sh                            # site/_site
uv run python scripts/make_preview.py               # output/preview, the summary as one page
