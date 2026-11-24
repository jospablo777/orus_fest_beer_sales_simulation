This document records how the study was built: the question, the data, the model, the calibration, the experiments, the statistics, and the steps to reproduce every number. The values themselves, with their sources, are in [ASSUMPTIONS.md](assumptions.qmd). Result values are quoted from the tables in `output/tables/` and appear on the site pages; this document describes how they are produced.

## 1. Question and rationale

At Orus Fest 2026 (Salón Olímpico Pantitlán, Mexico City, 1 August 2026) buying a beer between 18:00 and 20:00 took more than 40 minutes and two lines. The organizer wants a better setup for the next edition: how to sell, how many people to staff, and how many tickets to sell.

No sales records, ticket scans or staff rosters are available. The evidence is one attendee's account (times, waits, lines, payment system, crowd behaviour), a reported attendance of 2,000, a satellite image of the hall, and the published lineup. With evidence of this kind a statistical model fitted to past sales is not possible. The study therefore uses a mechanistic simulation:

1. Write down how people arrive, move, get thirsty, choose a line, wait and leave, using rules that can be checked one by one.
2. Treat every quantity nobody measured as uncertain and give it a range.
3. Keep the combinations under which the simulated 2026 night looks like the night that was observed.
4. Rerun each of those plausible nights with a different setup and measure the change.

The answer is a comparison of setups across all plausible versions of 2026. Exact waiting times for the next edition are outside its scope. A setup that wins in nearly every plausible night can be recommended even when the absolute numbers are uncertain.

## 2. Data

| Source | What it gives | Used for |
|---|---|---|
| Report of the attendees who ran the study | arrival 15:30, when buying was relatively quick although it took a while; over 40 min in the beer exchange line alone, with tickets bought earlier, between 18:00 and 20:00 (God Module and Das Ich); long lines at the ticket window and at the exchange; no attempt to buy after 20:00; hall fullest around 22:00; one ticket window for every drink; two exchange lines for beer and one for cocktails and shots; 5 to 8 people serving; several beers bought per visit for friends; food sold at separate counters; no roaming sellers; no re-entry; followers hold the stage front before their act and others drink between sets | calibration targets, model rules |
| Video about the event (<https://www.facebook.com/watch/?v=1338140721641943>) | 2,000 attendees | number of unique attendees |
| VICE México | hall capacity of 2,500 | sanity check on the peak |
| Satellite screenshot annotated by the study author and `analysis/salon_olimpico_zoning.R` | hall outline 52.2 × 30.1 m (about ±10% per side); stage, bar, vendor strips, tables | the floor plan |
| Official schedule poster, Orus Producciones (`docs/sources/orus_fest_2026_schedule.jpg`) | every band and DJ set with start and end times, 13:00 to 03:00 | running order, opening and closing time |
| Instagram profiles of all ten bands and DJ Scorpio, recorded 2026-11-23 (`docs/sources/popularity_instagram.csv`, screenshots in `docs/sources/`) | follower counts from 326 (Tracción Omega) to 10.7K (Peter Heppner) | relative popularity of the bands |

## 3. Model

The model is agent-based and runs in discrete time (5 s steps) from doors (13:00) to close (03:00). Code: `sim/model.py`, `sim/venue.py`. The study covers beer. The cocktail line and its staff are outside the model; the floor its line occupied is kept clear.

### 3.1 Space

The hall is a grid of 1 m cells in a local frame: y from the stage wall (0, south) to the bar wall (52.2 m, north), x from the east wall (0) to the west wall (30.1 m). Plan views put the stage at the top, so they show the hall as on the map after a half turn. Cells between the stage edge (y = 9) and the bar zone (y = 43.2) are standing cells. Cells in the vendor strips and the table area are side cells with a lower density cap. The toilets take the east end of the bar wall (5 m wide, assumed), so the bar runs from x = 5 m to the west wall; they are drawn on the plan views, and trips to them are not modelled. The tables (9 × 9 m) sit in the north-west corner in front of the bar, the short vendor strip is on the west side and the long one on the east side, as in the annotated screenshot. The positions observed at Orus Fest 2026 come from the study authors' sketch: the entrance and exit on the east wall next to the stage, the lighting and drone crew area (about 6 × 5 m, x 12.3 to 18.3 m, y 22.2 to 27.2 m) in the middle of the floor, and from east to west along the counter the ticket line (x 7.1 m), the cocktail line (x 12.4 m) and the two beer exchange lines (x 15.7 and 18.9 m). The crew area and a 1 m strip under the cocktail line are removed from the standing cells, which leaves 663 m² of free floor. Density in each cell is recounted every step and smoothed over 3 × 3 cells.

### 3.2 Attendees and groups

Each of the 2,000 attendees has:

- **A core act**, drawn with probability proportional to `fans_k ** core_power`. `fans_k` is the share of the audience that follows act k.
- **An attendance window**: the core band plus Poisson(`acts_before_mean`) bands before it and Poisson(`acts_after_mean`) after it. A share `whole_event_share` stays through the last band whatever their core band.
- **A group of friends** of size 1 + Poisson(`group_size_mean` − 1), at most 6. Attendees with the same core act and window are grouped. A group shares the window of its first member, arrives 10 to 60 min before the first band of the window and leaves 0 to 25 min after the last. Of the groups that see the last band, a share `close_stay_share` stays for the closing DJ sets. Nobody re-enters.
- **A set of followed acts**: the core act, plus each other act in the window with probability `fans_k`.
- **Drinker status, base thirst rate and patience**, drawn independently.

The number of people inside at any moment, including the peak, is an output of these windows.

### 3.3 Where people stand

At every band start and every changeover the model computes the focus band: the band playing, or during a DJ set between bands the next band. Followers of the focus act prefer cells close to the stage, with weight `exp(-(y - 9) / front_scale_m)`. Everyone else prefers cells toward the bar, vendors and tables, with weight `0.35 + exp(-(43.6 - y) / back_scale_m)`. When the focus changes:

- followers who are not within `front_zone_m` of the stage move up with probability `fan_move_share`;
- non-followers within that zone step back with probability `nonfan_leave_share`;
- anyone else picks a new spot with probability `shuffle_share`.

Spots are sampled in chunks. Each chunk updates the cell counts, so no cell exceeds its density cap (3.0 people/m² on the floor, 1.0 at the sides). People who walk to a new spot, a line or the exit move in a straight line at the Weidmann speed for the density of the cell they are in:

v(ρ) = v₀ · (1 − exp(−1.913 · (1/ρ − 1/5.4))), with v₀ = 1.34 m/s.

People do not collide and lines are fixed rows of positions. The model therefore cannot compare line layouts, barriers or walkways.

### 3.4 Thirst

A drinker who is standing at a spot, has finished the previous beer (`drink_min` per beer) and is not about to leave becomes thirsty in a step with probability `rate · m · a · dt`, where a is `afternoon_thirst_mult` before 18:00 and 1 after. The multiplier m depends on the moment and on the person:

| Moment | Person follows the focus act | m |
|---|---|---|
| set playing | yes | `fan_thirst_mult` (0.35) |
| set playing | no | `nonfan_thirst_mult` (1.15) |
| changeover | yes (holding a spot for the next act) | `holder_thirst_mult` (0.6) |
| changeover | no | `changeover_boost` (calibrated, 1.2 to 2.4) |

When a popular act ends, its followers who do not follow the next act all become likely buyers at the same time. This produces the surge between sets.

### 3.5 Rounds for friends

When a thirsty person goes for beer, each friend of the group who is standing in the crowd and has finished their last beer joins the purchase with probability `round_join_share`, up to `round_max_beers` beers per visit. Friends in a round do not start a purchase of their own. When the buyer is served, each friend receives one beer. The friend's next thirst is then delayed by `drink_min` plus an exponential time with the friend's own rate, which is the time they would still have waited for their own thirst. Rounds therefore change the number of beers per visit and leave each person's consumption unchanged.

### 3.6 Choosing a line, balking and reneging

A thirsty person first looks for a roaming seller with stock within `see_radius_m`. If one is there they raise a hand and wait. Otherwise they estimate the wait at every open line they can use:

expected wait = (people in the line + people walking to it + 1) × recent time per visit at that kind of station + distance / 0.6 m/s

The time per visit is a running average of the last visits at ticket windows, exchange stations and pay-at-the-station points. In the ticket system a person without enough tickets for the round adds the ticket line estimate to the shortest exchange line. They pick the smallest estimate. If it is larger than their patience (lowered to `fan_patience_mult` × patience while an act they follow plays), they do not join and retry 8 to 20 minutes later (balking). Someone already in a line who has waited `renege_factor` × patience leaves it (reneging). Balking and reneging both count as abandoned attempts.

### 3.7 Service

Each line is served first come, first served by one or more people. A line served by k people starts the next service as soon as any of them is free. Lines run from the counter toward the stage; a line that reaches the crew area stops 0.5 m short of it and continues in lanes beside the first one. Service times are lognormal with coefficient of variation 0.45. A service ends at its exact time, and the next one starts at that time when its customer was already waiting, so service times are not rounded to the 5 s step.

- **Ticket system (2026)**: one ticket window and two beer exchange lines, with the people serving beer split between the two lines (3 and 2 when 5 serve). The buyer gets the tickets for the current round plus Poisson(`bundle_mean` − 1) spare ones, at most 10 per visit, then walks to the shortest exchange line. The first beer of a visit takes `s_pour_mean_s` and each further beer `extra_beer_factor` of that. The ticket window also sold tickets for cocktails and shots; its time per beer buyer (`s_cash_mean_s`) is an effective time that includes those customers.
- **Pay at the serving station**: one person and one line per station, payment (`s_pay_direct_s`) plus serving. The stations are spread over the counter from x 5.6 m (past the east vendor strip) to x 20 m (1 m short of the tables), with a gap at the cocktail line.

In 30% of visits the buyer takes two beers for themself. Satellite stations work like pay-at-the-station points placed on the inner edge of a vendor strip. Shift stations accept people only inside their time window.

**Bar workers.** Each server of a service point is one person behind the counter. At every step a bar worker is off (the station is outside its shift), idle, charging or pouring. A visit at a station is split into its payment time and its pouring time, drawn as before; the customer pays first (`bar.pay_first`, assumed). The ticket window worker charges for the whole visit and the 2026 exchange workers pour for the whole visit. The run records the busy and staffed seconds of the bar workers by clock hour and the seconds the sellers spend walking, selling, walking to a refill and refilling (`bar_busy_hHH`, `bar_charging_share` and `seller_*_share` in the scenario metrics). Recording the states draws no random numbers, and a test checks that the metrics of three fixed nights are unchanged (`tests/fixtures/reference_metrics.json`).

### 3.8 Roaming sellers

Each seller carries 6 beers per trip and patrols toward randomly chosen attendees. A seller claims the nearest raised hand within `detect_radius_m`, walks there through the crowd (Weidmann speed × 0.85) and sells in about 30 s plus 12 s per further beer. With no beers left, the seller walks to the nearer end of the bar and refills in 2 minutes. A person whose hand is not claimed within 6 minutes walks to the bar.

### 3.9 Order of operations in a step

1. Recount density.
2. Update the focus act and move the crowd.
3. Admit arrivals.
4. Send leavers to the exit.
5. Move and serve sellers.
6. Draw thirst, form rounds and choose lines.
7. Serve every line.
8. Move walkers.
9. Check reneging once per minute.
10. Record a summary once per minute.

`tests/test_model.py` checks the invariants of a run (`uv run --group dev pytest`): beers held by attendees equal beers in transactions, no attendee holds a negative number of tickets, no round stays open at the end, everyone leaves, and friends arrive and leave together.

## 4. Outcomes

| Metric | Definition |
|---|---|
| Time in line | from joining the first line to holding a beer, or to giving up. Including people who gave up keeps the measure from looking better when lines are so long that people walk away. |
| Wait until service | Kaplan-Meier median of the minutes from joining a line to being served (Kaplan and Meier 1958). A person who gave up is censored: the wait was at least the time spent in line. When fewer than half of the people are ever served, the longest recorded time is reported as a lower bound. |
| Exchange-line wait, 18:00 to 20:00 | wait until service of the people who joined a beer exchange line in that window. This is the quantity the observers reported (over 40 min with tickets in hand). |
| Whole purchase without tickets, 18:00 to 20:00 | wait until service from joining the ticket line, for people who started without tickets in that window. It is a prediction: the observers already held tickets. |
| Headliner-hour waits | the same statistics for 21:30 to 22:30. Nothing was observed in that hour, so they are predictions. |
| Wait of 1 in 10 buyers | 90th percentile time in line for people who joined between 18:00 and 02:00 (`staffing.yaml: service_target.window`). The window starts at the hour in which lines formed in 2026. |
| People in each line | mean number of people queued at the ticket window and at the exchange stations in a window |
| Beers sold | all beers handed over during the night |
| Abandoned attempts | balks plus reneges; abandon share = abandoned / (abandoned + purchases) |
| Hours in line | time in line added over all attendees |
| Served within 5 minutes | share of purchases with at most 5 min in line |
| Headliner minutes in line | minutes of the Heppner (22:00 to 23:30) and Solitary Experiments (00:00 to 01:15) sets that attendees spent in a line, divided by buyers served between 22:00 and 01:15 |
| Heavy drinking | share of attendees with 6 or more beers |
| Staff | people selling at the busiest moment (ticket window, serving stations, sellers) |
| Staff hours | sum of the open hours of every selling position |
| Floor density at the fullest moment | people standing on the free floor divided by its area. People at tables, in vendor aisles and behind the counter line are not counted. |

## 5. Calibration

`scripts/run_calibration.py` estimates the unknown inputs with approximate Bayesian computation and a sequential sampler (population Monte Carlo, Beaumont et al. 2009). The ranges are in `config/calibration.yaml`.

A simulated 2026 night matches the observations when all six tests pass (test 2 has a lower and an upper limit):

1. median time in line for people joining 15:00 to 16:00 is at most 10 minutes;
2. the wait until service in the beer exchange lines is at least 35 minutes and at most 70 minutes for people who join them between 18:00 and 20:00. The report says over 40 with tickets in hand; 5 minutes of tolerance on the lower limit absorbs single-run noise. The longest wait was not measured: 70 minutes is an upper limit set by the study author, an assumption without an observation behind it, and it has no tolerance. A night whose median is not reached by the end of the shortened run (the Kaplan-Meier estimate never falls to one half) fails the upper limit;
3. the ticket line holds at least 20 people on average between 18:00 and 20:00;
4. the beer exchange lines hold at least 20 people in total on average between 18:00 and 20:00 (10 in each of the two lines);
5. the number of people inside at 22:00 is at least 90% of the night's maximum. The report places the peak "around 22:00", an estimate made from the running order;
6. at least 20% of the purchase attempts at the bar that start between 18:00 and 20:00 are given up. An attempt is given up when the person decides not to join the line they see (the expected wait exceeds their patience) or leaves a line after 1.5 times their patience in it. The report says "a lot of people gave up"; the 20% is assumed. In the model almost every attempt given up is a decision not to join, since a person who joins expects a wait below their patience.

The distance of a night from the observations is the sum of the relative shortfalls of the six tests, and it is zero when all pass.

- **Stage 0** draws 320 input sets from the ranges with a Latin hypercube (seed 2026), simulates the 2026 setup once per set (seed 10000 + id) and keeps the closest quarter.
- **Shortened runs.** A calibration run computes only the test statistics. The occupancy test depends on arrival and departure times alone and needs no simulation. The run stops at 16:20 when the early test fails, and otherwise 80 minutes after the end of the window of test 2 (the larger of 60 minutes and the upper limit plus 10), at 21:20, so that everyone who joined in the window is followed past the upper limit. People still in an exchange line at 21:20 are censored at the minutes they have waited so far.
- **Each later stage** proposes new input sets around the kept ones (a Gaussian move with twice the weighted variance of the kept sets; one option up or down for the number of people serving), keeps those within a smaller distance (the median distance of the previous stage), and gives each a weight equal to prior density over proposal density.
- **The last stage** keeps only nights that pass every test. Those nights are rerun for the whole night with the same seed, and the few that fail a test on the whole-night statistics are dropped. The weighted nights are resampled (systematic resampling) into 64 posterior draws, `output/runs/posterior_draws.csv`. Every later step uses that file. `output/runs/calibration_draws.csv` holds every simulated night with its stage, distance and weight, and `output/tables/calibration_summary.csv` reports the number of simulations, the number of matching nights and the effective sample size.

Stage 0 is plain rejection sampling, and it matches all five tests in about 1 night in 300. The sequential sampler is used for that reason.

The two line tests require 20 people in each line. `output/tables/threshold_check.csv` compares the effect of the plan in the nights with at least 30 people in each line and in the rest. `run_calibration.py --reaccept` applies changed thresholds to the last stage of an existing calibration without new shortened runs, and `run_calibration.py --more N` adds simulations to the last stage. Every simulated batch is stored under `output/runs/parts_calibration` until the run ends, so a run that stops continues from the stored batches when the same command is issued again.

Development history, kept for transparency. Each step below changed the model or its inputs, and the calibration was rerun from scratch after each one:

1. **Assumed running order** (Heppner at 22:30) and a test on the time of the maximum occupancy. The test was replaced by the 90% share.
2. **Official schedule poster** replaced the assumed running order.
3. **Wider attendance windows and whole-event attendees** (attendee: "most people came to see several bands or the whole event"), with a calibrated afternoon drinking pace.
4. **Instagram follower counts** for all bands replaced the assumed follower shares.
5. **Review of 2026-11-23** (`docs/REVIEW.md`). It found that the first calibration assumed 1 or 2 ticket cashiers and 5 to 8 pourers, which made the ticket booth the slower stage in 99% of the input sets before any comparison with 2026.
6. **New facts from the attendee** on 2026-11-23: one ticket window for every drink; two beer exchange lines and one for cocktails; long lines at both stages; several beers per visit for friends; the wait of over 40 minutes happened between 18:00 and 20:00 and nobody tried to buy later. The model gained groups of friends and rounds, exact service times and a wait statistic for people who started without tickets. The ticket window is fixed at one, its time per buyer ranges from 8 to 60 s, the people serving beer range from 2 to 6, and the sequential sampler replaced rejection sampling.
7. **Floor plan.** The plan had been drawn as a mirror image of the annotated screenshot. It is now the screenshot after a half turn, with the tables in the north-west corner and the long vendor strip on the east side.
8. **Line threshold.** The two line tests first required 30 people in each line. That calibration kept 33 nights with an effective sample size of 17, and the threshold was set to 20.
9. **Seller hours and service window.** With sellers from 19:00 the plan kept a wait between 18:00 and 19:00, the hour in which the 2026 lines formed. Sellers start at 18:00 and the service target covers 18:00 to 02:00.
10. **Second correction from the attendees** on 2026-11-23: the wait of over 40 minutes was in the beer exchange line alone, with tickets bought earlier in the afternoon, and buying at 15:30 was relatively quick although it took a while. The earlier calibration had matched 40 minutes for the whole purchase of a person without tickets, and in its matching nights the exchange line took a median of 18 minutes. The test now applies to the exchange line, waits are measured until service with the Kaplan-Meier estimator, and the ranges of patience, serving time and tickets per visit were widened.
11. **Sellers carry 6 beers per trip** (a tray of cups, as the study authors have seen at festivals) and refill at the bar. The first runs assumed 24 per trip, which made the crew with 6 sellers look sufficient.
12. **Inputs at the edge of their range and giving up.** With patience capped at 110 minutes and the afternoon drinking pace at 0.3 or more, the matching nights gathered near those limits. The ranges were widened (patience 25 to 180 minutes, afternoon pace 0.1 to 1.0, tickets per visit 1 to 8), and the test on purchase attempts given up was added from the attendees' report that a lot of people gave up.
13. **Observed hall layout** (study authors' sketch, 2026-11-24): entrance on the east wall next to the stage, ticket line, cocktail line and two shared beer lines at their observed places, and the lighting and drone booth in the middle of the floor. The free floor went from 708 to 663 m².
14. **Upper limit on the exchange-line wait** (2026-11-24). Without it the estimate of the 2026 wait moved with the allowed ranges (42 minutes under the narrow ranges, 56 under the wide ones on the earlier layout), while the attendees only saw "more than 40". Test 2 became two-sided with an assumed upper limit of 70 minutes. The run without the limit is kept as `output/sensitivity/no_upper_limit` and compared on the technical page. In the same pass the staffing grid moved to 64 nights per crew and 0 to 12 sellers, two crews are reported per ticket level, and an option without sellers was added.
15. **Serving options** (2026-11-24): unopened cans, draft beer and faster payment, compared by the crew each one needs (section 6.3).
16. **Sellers up to 15 and one set of nights** (2026-11-24). Every minimum crew used 12 sellers, the largest number in the grid, so the grid gained 15. The scenarios and what-ifs moved from 48 nights with their own seeds to the 64 nights and seeds of the staffing grid, so the plan reads the same count of nights in the staffing table and in the what-if table.
17. **Crews chosen by stress cases** (2026-11-24). With 15 sellers in the grid the fewest-hours rule moved the recommended crew at 2,000 tickets from 8 + 12 to 6 + 15, although four crews near the same hours met the target in 61 or 62 of 64 nights. The recommended and complete crews are now chosen by their lowest share of nights met across seven stress cases (section 6.1), and a complete level (every night) was added.

## 6. Experiments

### 6.1 Staffing grid and the plan

`scripts/run_staffing.py` runs every combination of tickets (1,500, 2,000, 2,500), serving stations (4, 6, 8, 10, 12) and roaming sellers (0, 3, 6, 9, 12, 15), with payment at the station (card or cash, 15 s) and sellers on the floor from 18:00 to 02:30, on 64 posterior draws (seed 90000 + draw). A night meets the service target when 9 of 10 buyers who join a line between 18:00 and 02:00 wait at most 10 minutes and at most 5% of purchase attempts are abandoned. For every crew, `sim/staffing.py` counts the nights that meet the target and gives the share an exact (Clopper-Pearson) 95% interval. Two crews are chosen per ticket level, each the one with the fewest staff hours among the crews that meet the target in a required share of the nights: the minimum crew (90%, `staffing.yaml: reliability`) and the recommended crew (95%, `reliability_recommended`). When no crew reaches 95%, the recommended crew falls back to the minimum crew and the pages say so. A third level, the complete crew, meets the target in every simulated night (`reliability_complete: 1.0`).

The recommended and complete crews are chosen by their results under stress (`scripts/run_crew_mixes.py`). At 2,000 tickets several crews within a few staff hours of each other meet the target in 61 or 62 of 64 nights; with 64 nights that difference is within noise (the exact intervals overlap almost entirely), so the fewest-hours rule picks among equals by chance, and adding 15 sellers to the grid moved the recommended crew from 8 + 12 to 6 + 15. The candidates of a level are the crews that reach its share with staff hours within 5% of the fewest. Each candidate runs seven stress cases on the 64 staffing nights and seeds: two bar workers absent, three sellers absent, sellers starting at 19:00, sellers 30% less productive (sale and refill times ×1.3, walking speed ×0.8), demand +30%, tickets +25%, and payment taking 25 s. The chosen candidate has the highest lowest share of nights that meet the target across the stress cases; ties go to the higher mean share, then to fewer staff hours. Every cell carries a Clopper-Pearson interval, and the chosen crew is compared with each other candidate in each case with an exact McNemar test on the paired nights, Holm-adjusted over all comparisons (`output/tables/crew_mixes.csv`). The table also gives the counter width per station between `pour_x_min` and `pour_x_max` without the gap at the cocktail line, and flags widths under 1.0 m. `staffing_plan.csv` records in `chosen_by` whether a crew was chosen by its staff hours or by the stress cases. The results are in `output/tables/staffing_reliability.csv` and `staffing_plan.csv`. One extra combination at 3,000 tickets feeds the capacity chart.

The **plan** is payment at the serving station with the recommended crew for 2,000 tickets (`config/report.yaml: plan_tickets`). The what-if `plan_minimum` runs the minimum crew, `plan_minimum_two_absent` the minimum crew with two people missing at the bar, and `no_sellers` an option without sellers: 12 stations at the main bar and a second bar with 4 stations on the inner edge of the east vendor strip. The scenario `plan` in `config/scenarios.yaml` reads that crew from `staffing_plan.csv`, so the staffing grid runs before the scenarios.

### 6.2 Counterfactual scenarios

`scripts/run_scenarios.py` runs every scenario in `config/scenarios.yaml` on the 64 posterior draws of the staffing grid. All scenarios of a draw use the same random seed, the one the staffing grid uses (90000 + draw): the same people, with the same arrival times, friends, followed acts, thirst rates and patience. The difference between a scenario and the 2026 setup on the same draw is that night's counterfactual effect. The plan scenario repeats the staffing nights of the recommended crew, so both tables give the same count of nights that meet the target.

The main family holds single changes to the 2026 setup (4 ticket windows, tickets sold with entry, 6 roaming sellers, a 2-station satellite bar), payment at the station with the 2026 head count (card or cash, and cashless wristbands), two larger setups, and the plan. The what-if family reruns the 2026 setup and the plan under other conditions: 2,500 tickets, 30% more demand, payment that takes 25 s, two bartenders absent, and sellers who start at 19:00.

Both scripts run in batches stored under `output/runs/parts_*`. A run that stops before the end continues from the last stored batch when the same command is issued again. The calibration does the same.

### 6.3 Serving options

`scripts/run_serving.py` compares ways of serving at the plan ticket level (`config/serving.yaml`): unopened cans (12 s saved per beer, with 8 and 20 s as low and high cases), draft beer from a tap (6 s saved per beer after keg changes), faster payment (6 s in place of 15) and cans with faster payment. The saving per beer (`bar.pour_saving_s`) is taken off the serving time of each beer of a visit and is capped at three quarters of that time. Each option runs the crew grid of the staffing step on the same 64 nights with the same seeds, so the options differ only in the serving time, and the minimum and recommended crews are chosen as in section 6.1. The 2026 practice is the staffing grid itself. None of the savings was measured: they come from the study authors' judgement of the time it takes to open a bottle and pour it into a cup, and from the observation that every beer in 2026 was opened and poured.

## 7. Statistical analysis

`analysis/figures.R` holds the statistics. Two kinds of interval are reported and labelled. The interval of the median is a 95% percentile bootstrap interval (4,000 resamples) for the typical night. The range across nights covers 5% to 95% of the simulated nights.

| Output | Method | Question |
|---|---|---|
| Figure 01 | range tried against histogram of the posterior draws | which unknown values are consistent with 2026 |
| Figure 02, `calibration_regressions.csv` | OLS on every simulated night with standardized predictors, for the buyer's wait and for the people in each line between 18:00 and 20:00 | which unknowns drive each line |
| Figure 03 | median and bands of occupancy and of people in each line across nights | the shape of the night |
| Figure 04 | median time in line per 15-minute bin, per setup, against 2026 | when each setup helps |
| Figure 05, `counterfactual_effects.csv` | same-night differences against 2026: median, bootstrap interval of the median, range across nights, nights improved with an exact binomial lower bound, Wilcoxon signed-rank test | what each change does |
| `comparisons.csv` | same-night differences between pairs of setups, with bootstrap interval and Wilcoxon test | whether a larger setup is worth its staff |
| Figure 06 | OLS of the extra beers under the plan on the unknowns | in which nights the plan helps most |
| Figure 08, `what_if.csv` | wait of 1 in 10 buyers under what-if conditions | whether the plan holds on a different night |
| Figure 09, `arimax_sales.csv` | event study of people in lines around the end of a set; regression of beers sold per 5 minutes on people inside and a changeover indicator with AR(1) errors, fitted per night, with a Ljung-Box test of the residuals | whether sales follow the crowd or stay flat at the bar's limit |
| Figure 12 | share of nights in which each crew meets the target | how many staff for how many tickets |
| Figure 13, `capacity.csv` | people per m² of free floor at the fullest moment against tickets | how many tickets the floor takes |
| `sensitivity_ranges.csv`, `sensitivity_staffing.csv` | the current run against a run with narrower calibration ranges (`output/sensitivity/narrow_ranges`): quantiles of the inputs and outcomes with a Mann-Whitney U test, and the share of nights that meet the target for every recommended crew with Fisher's exact test (`scripts/compare_calibrations.py`) | whether the plan depends on the limits of the calibration ranges |

`scripts/make_summary.py` draws the figures of the organizer pages in Spanish and English, and `sim/diagrams.py` the process diagrams. `scripts/report_values.py` collects every number shown on the site.

## 8. Reproducing the study

1. Install uv and rv. Run `uv sync --group site`, then `rv sync` and `rv activate` in the project folder. `uv.lock` pins the Python packages and Quarto; commit `rv.lock` after the first `rv sync`.
2. Run `./scripts/run_all.sh`, or run the steps in the README in order: calibration, staffing, scenarios, videos, R analysis, summary figures, site. R must run in a UTF-8 locale (`run_all.sh` sets `LC_ALL=C.UTF-8` when none is set) so that labels such as × and ≤ print correctly.
3. Every simulation step appends a record to `output/run_manifest.jsonl`: UTC time, git commit, SHA-256 of each config file, Python and package versions, number of runs, and runtime. `analysis/figures.R` writes `output/tables/sessionInfo.txt`.

Each run gets its seed from the draw number, so the number of processes does not change any result. With the same configs, the same seeds and the same package versions, outputs are identical. A change of NumPy major version can change random streams.

Every simulation step runs in a process pool with one simulated night per process (`sim/experiments.py: pool`), and the videos render one clip and language per process. The pool uses every core unless `--processes N` (or `PROCESSES=N` for `run_all.sh`) sets a limit, and the runtime falls almost in proportion to the number of cores. Runtime on 2 CPU cores: calibration about 2 hours at the limit of 12,000 simulations (0.6 s per shortened run), staffing grid about 50 minutes, scenarios about 25, videos about 8, R analysis and figures under 2 minutes. On an Apple M4 Pro with 14 cores (macOS 26): calibration 4.7 minutes for 4,928 simulations and 4.4 more for the 4,032 added with `--more` (12 processes), staffing grid 12.7 minutes for 4,864 runs, scenarios 2.6 minutes for 1,008 runs, the four videos 1.5 minutes, and the full pipeline about 30 minutes.

## 9. Limitations

- **Calibration evidence.** The targets come from the account of the attendees who ran the study, and the thresholds that turn "long lines" and "over 40 minutes" into numbers are assumed. Sales, entries and service times were not measured.
- **After 20:00.** The observers stopped buying at 20:00. Waits during the headliners are predictions.
- **Serving speed under the plan.** A serving station under the plan takes the calibrated time per beer of the 2026 bar plus the payment time. All beer in 2026 was bottled or canned. Each one was opened and poured into a cup, and a large beer took two, so most of the serving time is work that stays under the plan. If part of that time came from handling tickets or from the disorder at the counter, the plan needs fewer stations than reported. Draft beer would change the serving time and calls for a new estimate.
- **Hall size.** The outline was read from a satellite image without a scale bar. The error is near 10% per side (`report.yaml: hall_side_uncertainty`), and the capacity results scale with the area. The ticket level at which the free floor reaches the density limit is reported with the range for a hall 10% smaller or larger per side. That range rescales the floor area of the simulated nights; the simulation was not rerun with other hall sizes.
- **Movement.** People walk in straight lines and do not collide, and they pass through the crew area and the cocktail line on their way. Line layouts, barriers, walkways and evacuation cannot be evaluated.
- **Scope.** Cocktails and shots, food, restrooms and smoking areas are not modelled. The ticket window's work for other drinks enters only through its effective time per beer buyer.
- **Groups.** Friends buy together and share arrival and departure. They do not stand together in the model.
- **Running order.** The times are the published plan. Real sets start late, and every delay moves the surges.
- **Sellers.** The seller rules (visibility, beers per trip, refill time) are not calibrated, because there were no sellers in 2026. The load of 6 beers per trip (a tray of 6 large beers in cups) is what the study authors have seen at other festivals, and the refill time of 2 minutes is assumed (4 minutes in a what-if). Seller results are a plan to test at a small scale first.
- **Money.** Sales in MXN use an assumed price and exclude the cost of staff, card fees and equipment.
- **Occupancy.** Peak occupancy depends on the assumed attendance windows. The 2,000 figure is a single reported number with no description of how it was counted.

## 10. References

Sources of the crowd-management recommendations are listed in [LITERATURE_REVIEW.md](literature.qmd).

- Beaumont, M. A., Cornuet, J.-M., Marin, J.-M., & Robert, C. P. (2009). Adaptive approximate Bayesian computation. *Biometrika*, 96(4), 983–990. https://doi.org/10.1093/biomet/asp052
- Clopper, C. J., & Pearson, E. S. (1934). The use of confidence or fiducial limits illustrated in the case of the binomial. *Biometrika*, 26(4), 404–413. https://doi.org/10.1093/biomet/26.4.404
- Efron, B. (1979). Bootstrap methods: another look at the jackknife. *The Annals of Statistics*, 7(1), 1–26. https://doi.org/10.1214/aos/1176344552
- Fisher, R. A. (1922). On the interpretation of χ² from contingency tables, and the calculation of P. *Journal of the Royal Statistical Society*, 85(1), 87–94. https://doi.org/10.2307/2340521
- Kaplan, E. L., & Meier, P. (1958). Nonparametric estimation from incomplete observations. *Journal of the American Statistical Association*, 53(282), 457–481. https://doi.org/10.1080/01621459.1958.10501452
- Ljung, G. M., & Box, G. E. P. (1978). On a measure of lack of fit in time series models. *Biometrika*, 65(2), 297–303. https://doi.org/10.1093/biomet/65.2.297
- International Code Council. (2018). *2018 International Building Code*. Country Club Hills, IL: ICC. Table 1004.5 sets an occupant load factor of 0.46 m² (5 ft²) net per person for standing space.
- Mann, H. B., & Whitney, D. R. (1947). On a test of whether one of two random variables is stochastically larger than the other. *The Annals of Mathematical Statistics*, 18(1), 50–60. https://doi.org/10.1214/aoms/1177730491
- National Fire Protection Association. (2018). *NFPA 101: Life Safety Code* (2018 ed.). Quincy, MA: NFPA. Section 12.1.7.1 caps the occupant load of an assembly area of up to 930 m² (10,000 ft²) at one person per 0.46 m² (5 ft²) of available floor space, and of a larger area at one person per 0.65 m² (7 ft²).
- Weidmann, U. (1993). *Transporttechnik der Fussgänger: Transporttechnische Eigenschaften des Fussgängerverkehrs, Literaturauswertung* (2nd, extended ed.; Schriftenreihe des IVT, No. 90). Institut für Verkehrsplanung, Transporttechnik, Strassen- und Eisenbahnbau, ETH Zürich. https://doi.org/10.3929/ethz-b-000242008
- Wilcoxon, F. (1945). Individual comparisons by ranking methods. *Biometrics Bulletin*, 1(6), 80–83. https://doi.org/10.2307/3001968

