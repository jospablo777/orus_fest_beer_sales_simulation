# Orus Fest beer-sales simulation

[Versión en español](README.md)

The report for the organizers is published at <https://jospablo777.github.io/orus_fest_beer_sales_simulation/>.

Agent-based model of attendance and beer sales at Salón Olímpico Pantitlán (Mexico City). It is calibrated to what we saw when we attended Orus Fest 2026 (1 August 2026) and is used to compare ways of selling at the next edition.

At the 2026 edition beer was sold through a ticket system. One window sold tickets for every drink, and a second line exchanged them at the bar. At 15:30 buying was relatively quick, although it still took a while. Between 18:00 and 20:00 the exchange line took over 40 minutes with the tickets already bought, and the line at the ticket window was long as well. The model reproduces that night, then reruns it with other ways of selling and other crews.

## What the model does

- **Attendance.** 2,000 attendees ([reported](https://www.facebook.com/watch/?v=1338140721641943)) arrive in groups of friends between 13:00 and 23:30 and leave after a chosen last act. Nobody re-enters. The number inside at the peak is an output.
- **Running order.** The official Orus Fest 2026 schedule (Orus Producciones poster, `docs/sources/`): ten bands from 13:30 to 01:15 with DJ sets in between, music until 03:00.
- **Space.** The hall is a 52.2 × 30.1 m rectangle split into 1 m cells, with the stage, bar, tables and vendor strips of the annotated satellite screenshot (`analysis/salon_olimpico_zoning.R`). Walking speed falls with local density (Weidmann, 1993).
- **Popularity.** Each band's share of followers comes from its Instagram follower count (recorded 2026-11-23), relative to Peter Heppner.
- **Demand and crowd.** Each attendee comes for one core band and follows some of the bands around it. Followers pack the stage front while their band plays, and everyone else is the main source of the beer rush between bands. One friend buys for the group.
- **Selling.** One ticket window and exchange lines (2026), pay-at-the-station points, a satellite bar and roaming sellers. People skip a line that looks longer than their patience and leave a line they have been in too long.
- **Calibration.** Approximate Bayesian computation with a sequential sampler (Beaumont et al., 2009) over the unknowns (`config/calibration.yaml`). A night matches 2026 when buying is relatively quick at 15:00 to 16:00, the exchange line takes 35 to 70 min for a person who joins it between 18:00 and 20:00 (the longest wait was not measured; 70 min is an assumed limit), both lines hold at least 20 people in that window, at least 20% of the purchase attempts in that window are given up, and the hall is near its fullest at 22:00. The wait in a line is estimated with the method of Kaplan and Meier (1958), which counts a person who left the line as someone who waited at least until that moment.
- **Staffing.** A grid of tickets × serving stations × sellers. The minimum crew meets the waiting target in at least 90% of the simulated nights and the recommended crew in at least 95%.
- **Counterfactuals.** Every scenario reruns each night with the same random seed. The difference from the 2026 setup on the same night is that night's counterfactual effect.

Every assumption, its source and the file that sets it are listed in [docs/ASSUMPTIONS.md](docs/ASSUMPTIONS.md). The study design, model logic, statistics and reproduction steps are in [docs/METHODS.md](docs/METHODS.md). The papers behind the crowd-management recommendations are in [docs/LITERATURE_REVIEW.md](docs/LITERATURE_REVIEW.md), and primary sources (schedule poster, Instagram screenshots) in `docs/sources/`.

## Setup

Python and Quarto are managed with [uv](https://docs.astral.sh/uv/) (`pyproject.toml`, `uv.lock`). R is managed with [rv](https://a2-ai.github.io/rv-docs/) (`rproject.toml`).

```bash
uv sync --group site   # creates .venv from uv.lock, with Quarto for the website
rv sync                # installs the R packages into rv/library and writes rv.lock
rv activate            # writes .Rprofile so Rscript in this folder uses rv/library
```

Set `r_version` in `rproject.toml` to the major.minor of your R before `rv sync`. Commit `rv.lock` after the first sync so later installs resolve to the same package versions. Rendering the videos needs `ffmpeg` on the PATH.

## Run

```bash
./scripts/run_all.sh                  # everything, about 4 hours on 2 cores
PROCESSES=6 ./scripts/run_all.sh      # the same with at most 6 processes
```

or step by step, in this order:

```bash
uv run python scripts/run_calibration.py                      # output/runs/posterior_draws.csv
uv run python scripts/run_staffing.py                         # crew by reliability, output/tables/staffing_plan.csv
uv run python scripts/run_serving.py                          # serving options, output/tables/serving_options.csv
uv run python scripts/run_scenarios.py                        # output/runs/scenario_*.csv (reads the plan crew)
uv run python scripts/make_animation.py --clip all            # output/animations/*_{en,es}.mp4, both clips
LC_ALL=en_US.UTF-8 Rscript analysis/figures.R                 # output/figures, output/tables (any UTF-8 locale)
uv run python scripts/make_summary.py                         # organizer figures in English and Spanish
uv run python scripts/compare_calibrations.py                 # output/tables/sensitivity_*.csv, against the narrow-range run
./scripts/render_site.sh                                      # site/_site
uv run python scripts/make_preview.py                         # output/preview, the summary as one page
```

`run_scenarios.py --families what_if` reruns one scenario family and merges it into the existing outputs. `uv run --group dev pytest` runs the tests of the model.

The calibration, the staffing grid, the scenarios and the videos run in parallel: each simulated night (or each video) takes one process and every core of the computer is used, so the runtime falls almost in proportion to the number of cores. `--processes N` on each script, or `PROCESSES=N` for `run_all.sh`, limits the number of processes. Results do not depend on the number of processes, because each night takes its seed from its number. `run_calibration.py`, `run_staffing.py` and `run_scenarios.py` store their progress in batches under `output/runs/parts_*`. If a run stops, the same command continues from the last stored batch.

## Changing assumptions

All inputs are YAML:

| File | Contents |
|---|---|
| `config/base.yaml` | hall geometry, running order, bar setup, sellers, crowd behaviour |
| `config/calibration.yaml` | ranges for the unknowns, the observations of 2026 and the sampler settings |
| `config/scenarios.yaml` | setups to compare and what-if conditions |
| `config/staffing.yaml` | staffing grid, waiting target and required reliability |
| `config/serving.yaml` | faster ways of serving (closed cans, draft beer, fast payment) and the time each one saves |
| `config/report.yaml` | beer price for sales figures, headline scenario, ticket level of the plan, clock windows of the videos |

To try a variant without editing the defaults, copy a file and pass it in:

```bash
cp config/base.yaml config/base_alt.yaml        # e.g. move Rotersand before Solitary Experiments
uv run python scripts/run_calibration.py --base config/base_alt.yaml
```

A scenario override is a dotted path into `base.yaml`. Values that start with `=` are computed from the calibrated night, for example `bar.n_pour: "= n_pour + n_cashiers"` moves the ticket seller behind the bar.

## Outputs

| File | Description |
|---|---|
| `output/runs/calibration_draws.csv` | every simulated 2026 night of the calibration with its stage, distance and weight |
| `output/runs/posterior_draws.csv` | the nights that match 2026, resampled by weight; input of every later step |
| `output/runs/scenario_*.csv`, `staffing_grid.csv` | one row per simulated night and setup |
| `output/tables/*.csv` | numbers behind the figures and the site |
| `output/figures/01_` to `13_*.png` | technical figures (calibration, effects, time series, staffing, capacity) |
| `output/figures/summary_*_{en,es}.png` | figures of the organizer pages |
| `output/animations/*.mp4`, `*.jpg` | side-by-side floor videos (whole evening and slow-motion changeover) and the still image shown before each one plays |
| `output/preview/` | the organizer summary as a single page (Spanish and English) with its figures and videos; it opens from disk and does not need Quarto |
| `output/run_manifest.jsonl` | one record per simulation step: time, git commit, config hashes, package versions |
| `docs/REVIEW.md`, `output/review/` | review of an earlier version and the checks behind it |

## Layout

```
config/      YAML inputs
sim/         model (venue.py, model.py), experiments, scenarios, staffing, diagrams, videos
scripts/     command-line entry points
analysis/    R analysis and the zoning script for the hall geometry
docs/        methods, assumptions, literature review, review, primary sources
site/        Quarto website
output/      generated
```

## References

- Beaumont, M. A., Cornuet, J.-M., Marin, J.-M., & Robert, C. P. (2009). Adaptive approximate Bayesian computation. *Biometrika*, 96(4), 983–990. https://doi.org/10.1093/biomet/asp052
- Kaplan, E. L., & Meier, P. (1958). Nonparametric estimation from incomplete observations. *Journal of the American Statistical Association*, 53(282), 457–481. https://doi.org/10.1080/01621459.1958.10501452
- Weidmann, U. (1993). *Transporttechnik der Fussgänger: Transporttechnische Eigenschaften des Fussgängerverkehrs, Literaturauswertung* (2nd, extended ed.; Schriftenreihe des IVT, No. 90). Institut für Verkehrsplanung, Transporttechnik, Strassen- und Eisenbahnbau, ETH Zürich. https://doi.org/10.3929/ethz-b-000242008

The ten crowd-management sources behind the operational recommendations are cited in full in [docs/LITERATURE_REVIEW.md](docs/LITERATURE_REVIEW.md).
