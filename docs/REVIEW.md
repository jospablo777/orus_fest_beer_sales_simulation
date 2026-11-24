# Review of the study and the report

This review describes the version of the study as it stood on 2026-11-23 at 14:30. The findings of sections 2 and 3 were acted on the same day, and section 12 lists what changed. The numbers in sections 1 to 8 refer to the earlier version; `output/review/` keeps the tables behind them.

The review covers the model code (`sim/`), the experiment scripts, the R analysis, the outputs of the last full run, the HTML report and the Quarto site. Its printed tables are saved in `output/review/summary.txt`.

## 1. Verdict

| Claim in the report | Status | Evidence |
|---|---|---|
| Removing the ticket step helps | Confirmed | The night improved in 24 of 24 simulated nights (exact 95% interval for the share, 86% to 100%) and in 19 of 19 nights under a second reading of the bar crew |
| The gain is 58 to 2.4 minutes with the same staff | Open | It depends on two facts about 2026 that were assumed (section 2.1) |
| 6 taps are enough for 2,000 tickets | Unsafe | That crew met the waiting target in 3 of 6 simulated nights (section 2.2) |
| The report is ready for the organizers | Open | It recommends two different setups, it is in English, and most of its figures are technical (sections 2.4 and 4) |

## 2. Findings that change the recommendations

### 2.1 The bottleneck was set by the inputs

The calibration assumed 1 or 2 ticket cashiers and 5 to 8 pourers. With those ranges the ticket booth has the lower capacity in 99% of the 360 input sets before any comparison with 2026, and in all 43 accepted sets. The booth serves a median of 250 beers per hour (5% to 95% range 141 to 472) and the pourers 1,006 (580 to 1,485). The busiest hour with payment at the tap sells 594 beers (434 to 889). The statement "the line formed at the booth" is therefore an assumption of the study.

A second calibration tested another reading of "5 to 8 people serving": 2 to 4 cashiers and 3 to 5 pourers (96 input sets, 19 accepted).

| Limiting stage in 2026 | Nights | Wait for 1 in 10 buyers, 2026 | With payment at the tap | Nights that improve | Extra beers (median) |
|---|---|---|---|---|---|
| Ticket booth | 10 | 52 min | 28 min (worst 48) | 10 of 10 | 1,825 |
| Pourers | 9 | 46 min | 26 min (worst 47) | 9 of 9 | 1,323 |

Payment at the tap helps in every case. With the smaller crew it leaves a wait near 27 min, so the crew size becomes the main decision.

One observation separates the two readings. In the current calibration the ticket line holds 109 people at 22:00 (58 to 201) and the exchange line fewer than 2. In the nights limited by the pourers the exchange line is the long one in 8 of 9. The study author stood in both lines and can say which was longer. The organizers know the number of ticket windows.

### 2.2 The crew in the report misses the target in half of the nights

The report picks the smallest crew whose median wait meets the target (1 in 10 buyers waits at most 10 min, at most 5% of attempts abandoned). The grid has 6 simulated nights per crew.

| Crew at 2,000 tickets | Nights that meet the target | Worst night, wait for 1 in 10 buyers |
|---|---|---|
| 6 taps (in the report) | 3 of 6 | 46 min |
| 8 taps | 5 of 6 | 29 min |
| 6 taps and 3 sellers | 5 of 6 | 27 min |
| 6 taps and 6 sellers | 6 of 6 | 5 min |
| 8 taps and 3 sellers | 6 of 6 | 7 min |

With 6 nights, 6 of 6 gives an exact 95% interval of 54% to 100% for the share of nights that meet the target. A crew recommendation needs a rule based on that share (for example 9 of 10 nights) and at least 30 nights per crew.

### 2.3 The calibration target is unstable

The model keeps an input set when the median wait at 21:30 to 22:30 is at least 35 min. In the ticket system the waits fall in two groups. People who hold tickets wait about 2 min and people who must buy tickets wait 45 min or more. The median moves from one group to the other with small changes. Input set 56 gave 45 min in the calibration run and 2 min in five later runs with other random seeds. Of the 24 accepted sets used for the scenarios, 21 pass the acceptance tests again with another seed.

The target should be the wait of a person who has to buy tickets (the situation the observer described), and each input set should be run with several seeds.

### 2.4 The report recommends two setups

The TL;DR recommends payment at the tap with 6 taps and optional sellers. The second video, the tile "+2,222 beers", the what-if section and one figure describe "the proposal": cashless wristbands, a satellite bar and 4 sellers with 14 staff. The TL;DR also says "the same 8 people" and then "6 taps". The report needs one named plan, used in every section.

### 2.5 The larger setups add nothing measurable

The table gives differences on the same night with a 95% interval for the median.

| Comparison | Wait for 1 in 10 buyers | Beers sold | Extra staff |
|---|---|---|---|
| Cashless wristband against card or cash at the tap | -0.7 min (-1.3 to -0.4) | +20 (-5 to +80) | 0 |
| Full proposal against card or cash at the tap | -0.4 min (-1.9 to +0.3) | -20 (-45 to +39) | 6 |
| 3 extra evening taps against cashless | -0.1 min (-0.5 to -0.1) | +9 (-9 to +36) | 3 |

With the current inputs, wristbands, the satellite bar and extra evening taps bring less than 2 minutes and no extra sales. This holds only if section 2.1 confirms the current reading of the crew.

### 2.6 The model cannot test lines, barriers or walkways

People walk in straight lines, pass through each other and through the vendor and table areas, and lines are fixed rows of positions. The five tap layouts give the same result for that reason. The actions "one barrier lane per tap" and "keep the middle of the floor open" come from the literature. The report should label them as such and drop the layout figure.

### 2.7 The ticket cap

- The density divides everyone inside by the free floor (753 m²). People at the tables, in the vendor aisles and in lines are counted on the free floor, so the cap of about 2,100 tickets is on the low side.
- The hall size (52.2 × 30.1 m) has not been measured. A 5% error in area moves the cap by about 100 tickets.
- The licensed capacity of the hall is the legal limit and belongs in the report next to the simulated one.

### 2.8 Money and drinking figures

- The money figure is revenue at an assumed MXN 80 per beer. It has no cost of staff, card fees or equipment, and sales in 2026 range from 1,350 to 4,560 beers across accepted nights (5% to 95%). The number of beers sold in 2026, from the organizers' stock records, removes most of that range.
- The share of attendees with 6 or more beers (2.4% to 8.7%) comes from one simulated night. It needs to be saved for every night and reported with an interval.

## 3. Smaller defects

| Defect | Effect | Change |
|---|---|---|
| A service ends only on a 5-second step | Each service lasts 2.5 s longer on average, 6% to 10% of its length, in every setup | Start the next service at the exact end time of the previous one |
| At most 2 beers per visit | A person buying for a group needs several visits, so service time per beer is too high | Add group purchases with a calibrated size |
| Tickets per cashier visit do not react to the line | People in 2026 could buy 10 at once after seeing the line | Let the number of tickets grow with the line length |
| Food was sold in the same zone | Food orders are not modelled | Ask whether food and beer shared staff and lines |
| Scenarios use the first 24 accepted sets and the staffing grid the first 6 | Small samples; wide intervals | Use all accepted sets |
| No tests of the model | Errors in counts pass unnoticed | Add checks: people in equals people out, beers sold equals beers in transactions, tickets never negative |
| `rv.lock` missing and no git commit | R versions and the code version are not pinned | Run `rv sync` locally and commit |

## 4. Helping non-technical staff

1. One page for the organizers, in Spanish, with five decisions. Each decision has one number and one picture. Methods, assumptions and literature stay on their own pages.
2. Plain wording everywhere on that page. "9 of 10 people get their beer within N minutes" replaces "90th percentile". "Simulated nights" replaces "draws". The words calibration, counterfactual, regression and Latin hypercube leave the page.
3. Counts that need no statistics. On the representative night, everyone's time in line adds up to 705 hours in 2026 and 37 hours with payment at the tap. 45% of purchases were served within 5 minutes in 2026 and 100% with payment at the tap.
4. Three confidence labels in words (firm, probable, to be checked at the event), one per decision.
5. A box "What we need from you" with the data requests of section 9.
6. A one-page checklist for the day of the event and a one-page briefing for bar staff.
7. Larger text in figures. At page width, figures 02, 05 and 12 show text near 10 px and labels near 7 px. The two calibration figures placed side by side show half of that.

## 5. Animations to add

| Animation | Purpose |
|---|---|
| One changeover in slow motion (21:25 to 22:10, 5 seconds per frame, about 45 s), with captions | Shows the rush to the bar when a band ends. The current video covers 6.5 hours in 19 seconds |
| The whole night in 60 s with running counters and three pauses (15:30, 19:00, 22:00) | The story of the night for a presentation |
| Two highlighted attendees with the same plans under both setups, with a counter of minutes of Peter Heppner missed | Makes the cost personal |
| The counter seen from the staff side, each station marked busy or idle | Shows idle pourers next to a saturated ticket booth |
| Line length through the night as a growing bar, both setups | Works on a phone and in a slide |
| Density map over time | For the safety team |
| A slider on the site to pick the minute | Lets people stop and look |

Short vertical clips with Spanish captions suit sharing by phone.

## 6. Visualizations to add

1. Beers per hour the crowd asked for against the beers per hour each stage could serve, by hour. This is the central finding in one picture.
2. What happened to every 10 purchase attempts in each setup (served within 5 min, served after a long wait, gave up).
3. Crew options with the share of nights that meet the target and its interval. It replaces the heat map of medians.
4. A rota by hour (taps open from 13:00 to 03:00). Sales on the representative night run near 45 to 170 beers per hour before 18:00 and about 340 to 490 from 18:00 to 01:00.
5. A stock plan with beers per hour, a range and the total to order.
6. Revenue and cost of each option in MXN, with ranges.
7. A ranked chart of the unknowns by how much each one changes the decision.
8. Floor plan before and after with the area taken by the lines.

The layout figure, the regression figure and the time-series regression move to the Methods page.

## 7. Simulation upgrades

- Fix the three model defects of section 3 (service rounding, group purchases, tickets per visit).
- Calibrate with the crew facts of section 2.1, or with both readings kept as two cases.
- Run 2,000 or more input sets with 3 seeds each. One run takes 6 to 10 s on one core, so this takes about 35 minutes on a 24-core workstation.
- Use every accepted set in the scenarios and at least 30 nights per crew in the staffing grid.
- Search the rota by hour (taps and sellers per hour) with a cost model, in place of a fixed crew for 14 hours.
- Add restrooms, exits with an evacuation run, late starts of sets, and arrivals from the entry scans.
- Movement with obstacles and contact between people is needed before the model can compare line layouts.

## 8. Quantification and inference to add

1. Two intervals for every result, each labelled: the interval for the typical night and the range across nights. Payment at the tap cuts the wait by 54.7 min (95% interval of the median 45.4 to 58.4) and adds 2,247 beers (1,836 to 2,536).
2. Exact binomial intervals for shares of nights (24 of 24 gives 86% to 100%).
3. Decisions by reliability: the share of nights in which a crew meets the target.
4. Paired tests for differences and equivalence tests for "no difference" claims, with stated margins (2 minutes, 100 beers).
5. Variance split. Unknown inputs explain 98% of the variance of the wait and 99% of the variance of sales. Run-to-run noise explains the rest. The uncertainty therefore falls with more data from 2026.
6. Weighted calibration with replicate runs, the effective number of accepted sets, and checks against observations left out of the calibration.
7. Sensitivity indices (Sobol) with intervals next to the regression.
8. Value of information for each unknown: the expected gain from measuring it before deciding.
9. Survival analysis of waits. People who gave up are censored observations; the current statistics count their time as a wait.
10. A queueing-theory check of the simulated waits.
11. Profit distribution per crew and the number of extra beers that pays for one more person.
12. Results under other acceptance thresholds (35 min, 10 min, 90%).
13. The time when the line passes a set length, with an interval. It tells when every tap must be open.
14. The chance that a buyer waits more than 15 or 30 minutes, by hour.

## 9. Information needed

The study author attended and can answer five questions.

1. Which line was longer around 22:00, the ticket line or the exchange line.
2. The number of ticket windows, and whether "5 to 8 people serving" included the ticket sellers.
3. Whether food and beer shared the counter and the staff.
4. Whether people bought several beers per visit for friends.
5. Two wall lengths of the hall measured in Google Maps.

The organizers hold the following records.

1. Beers sold in 2026 (stock bought minus stock left).
2. Tickets sold and entry scan times from the ticketing platform.
3. Bar staff by hour, prices, and the split between cash and card.
4. Licensed capacity of the hall, and the position and width of each exit.
5. Photos or videos of the ticket and bar lines, with the time each one was taken.
6. Reports from attendees (a short survey of ticket buyers): time in line to get a drink, number and kind of drinks, and whether they stood in the drink line only or also in the ticket line.
7. Who runs the bar and receives the drink sales (Orus Producciones, the venue or a concessionaire).
8. Whether the venue allows closed cans to be handed to the crowd.
9. Cost of a staff hour at the bar (or of a shift and its length) and the margin per beer.
10. Cocktails sold and the people serving cocktails.

## 10. Work plan

| Step | Content | New simulations |
|---|---|---|
| 1 | Report: one plan, crew chosen by reliability, intervals on every number, organizer page in Spanish, technical sections moved, larger text, the capacity chart, the data-request box | None |
| 2 | Model fixes, calibration with the answers of section 9, 2,000 input sets with replicate seeds, full staffing grid, rota by hour, cost model | Full rerun |
| 3 | The animations of section 5 and a crew calculator on the site | Short runs |
| 4 | Sensitivity indices, value of information, survival analysis, restrooms, evacuation | Partial |

## 11. Changes made during the review

- `output/run_manifest.jsonl` stored absolute paths of the machine that ran the study. Paths are now relative to the project (`sim/params.py`).
- Captions, figure subtitles and four sentences in the docs were rewritten as plain statements.
- `output/review/` was added.

No result of the study was changed.

## 12. What changed after the review

| Finding | Change |
|---|---|
| 2.1 The bottleneck was set by the inputs | The attendee supplied new facts: one ticket window for every drink, two beer exchange lines, long lines at both stages, rounds for friends, and the long wait at 18:00 to 20:00. The calibration now matches those facts and lets either stage be the slower one |
| 2.2 Crew chosen by the median of 6 nights | Crews are chosen by reliability: the target must be met in at least 90% of 32 nights (`sim/staffing.py`) |
| 2.3 Unstable calibration target | The wait is measured on people who started without tickets, and the matching nights are verified with whole-night runs |
| 2.4 Two setups in the report | One plan, defined by the staffing grid and used on every page |
| 2.5 Larger setups | Compared against the plan with same-night differences (`comparisons.csv`) |
| 2.6 Lines, barriers and walkways | Labelled as guidance from the literature; the layout scenarios were removed |
| 2.7 Ticket cap | Density counts the people standing on the free floor; the hall size carries its 10% margin and the licensed capacity is named as the limit |
| 2.8 Money and drinking | Sales carry intervals and are labelled as sales at an assumed price; heavy drinking is computed for every night |
| 3 Service rounding, group purchases, first-N draws | Exact service times, rounds for friends, weighted posterior sample |
| 4 Organizer page | Spanish and English summaries with process diagrams, plain wording and a data-request box |
| Found while checking the rendered pages | With sellers from 19:00 the plan kept a wait of several minutes between 18:00 and 19:00, the hour in which the 2026 lines formed. Sellers now start at 18:00, the service target covers 18:00 to 02:00, and a what-if keeps the 19:00 start for comparison |
| Found while checking the rendered pages | The recommended crews sat at the lower edge of the staffing grid (6 stations). The grid now starts at 4 stations |
| 2.7 Ticket cap, addition | The ticket level at which the floor reaches the density limit is reported with the range implied by the 10% margin of the hall size |
| Corrected observation | The wait of over 40 min between 18:00 and 20:00 was in the beer exchange line alone, with tickets bought earlier. Calibration test 2 uses the wait until service in the exchange lines (Kaplan-Meier median; people who gave up are censored), and the ranges of patience, serving time and tickets per visit were widened |
| Seller load | Sellers carry 6 beers per trip (a tray of 6 large beers in cups, as the study authors have seen at other festivals) and refill in 2 min at an end of the bar (assumed). The seller grid is 0, 3, 6 and 9. What-ifs cover a 4 min refill and 12 beers per trip |
| Parallel runs | One process pool per program with one simulated night per process. Calibration, staffing and scenarios store batches under `output/runs/parts_*` and continue after an interruption. The full pipeline runs in under an hour on 14 cores |
| Inputs at the edge of their range | With patience capped at 110 min and the afternoon drinking pace at 0.3 or more, the matching nights gathered near those limits. The ranges were widened (patience 25 to 180 min, afternoon pace 0.1 to 1.0, tickets per visit 1 to 8), and the narrow-range run is kept as a sensitivity check (`output/sensitivity/narrow_ranges`, technical report) |
| Giving up | The attendees reported that a lot of people gave up. A sixth test requires at least 20% of the purchase attempts started between 18:00 and 20:00 to be given up. In the model almost all of them are people who see the line and do not join, so the test bounds patience from above |
| Observed hall layout | The study authors drew the layout of the night: entrance next to the stage on the east wall, ticket line, cocktail line and two beer lines at their places, and a lighting and drone booth of about 6 × 5 m in the middle of the floor. The model uses those positions; the two beer lines share the people serving beer, the booth and the cocktail line are taken from the standing floor (663 m² left) and lines that reach the booth end at its back |
| One-sided test on the 2026 wait | The estimate of the 2026 exchange-line wait moved with the allowed ranges, and the organizer page showed waits far above what was seen. Test 2 is two-sided with an upper limit of 70 min set by the study author as an assumption; a night whose median is not reached fails. The run without the limit is kept and compared on the technical page |
| Crew at the edge of the reliability | The recommended crew met the target in exactly 29 of 32 nights. The staffing grid now runs 64 nights per crew, reports a minimum crew (90% of nights) and a recommended crew (95%), and the pages give what the minimum crew loses on a bad night and with two people missing |
| Dependence on sellers | Sellers sell about half the beer under the plan and none worked in 2026. An option without sellers (12 stations and a second bar with 4) is simulated and reported with its nights met, and the page recommends a trial of the sellers at a smaller event |
| Staff and cost | The pages give the people handling beer in 2026 and under the plan and the extra beers per extra staff hour, in pesos at the assumed price, and ask the organizers for the cost of a bar shift and the margin per beer |
| Faster serving | Unopened cans, draft beer and faster payment are compared by the crew each one needs at 2,000 tickets, on the same nights as the staffing grid. The time each one saves was not measured and is stated as an assumption with low and high cases |
| Sellers at the edge of the grid and two sets of nights | Every minimum crew used 12 sellers, the largest number tested. The grid now goes to 15 sellers. The scenarios and what-ifs ran on 48 nights with their own seeds, so the plan showed one count of nights in the staffing table and another in the what-if table. They now run on the 64 staffing nights with the staffing seeds |
| Organizer pages on phones and kinds of range | Charts have narrow versions with text of at least 11 px, tables show each row as a block below 600 px, and the videos have a phone cut with the floor panels and their readouts. Every range on the organizer pages covers 9 of 10 simulated nights; intervals of the median stay on the technical page |
| Toilets | The study author reported the toilets at the east end of the bar wall. The plan views draw them (5 m wide, assumed) and the bar starts after them; the model does not simulate trips to the toilets |
| Workers behind the bar | Each person serving is drawn behind the counter as off, idle, charging or pouring, in the videos, the floor plan and the process diagrams. The run records busy shares by hour and seller time by state; a fixture of three nights checks that recording them changes no other result |

Tests of the model invariants were added (`tests/test_model.py`). The staffing and scenario runs store their progress in batches and continue after an interruption. Still open: a git commit, restrooms, exits and evacuation, a cost model, and the measured size of the hall.
