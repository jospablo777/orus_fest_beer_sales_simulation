# Assumptions

Every number the model uses, where it comes from, and where to change it. Source codes:

- **Observed**: reported by the attendees of Orus Fest 2026 (1 August 2026) who ran this study.
- **Reported**: published by a third party (organizer video, press).
- **Calibrated**: unknown; given a range in `config/calibration.yaml` and narrowed to the values under which the simulated 2026 setup reproduces the observations.
- **Assumed**: chosen by us; change it in the file listed and rerun.
- **Literature**: taken from a published model or standard.

## Observations used for calibration

| Observation | Value | Source | File |
|---|---|---|---|
| Arrival of the observers | 15:30 | Observed | `calibration.yaml: observations.early_wait` |
| Waiting at 15:00 to 16:00 | relatively quick, although it still took a while; median time in line at most 10 min | Observed; the 10 is assumed | `calibration.yaml: observations.early_wait` |
| Waiting between 18:00 and 20:00 (God Module, Das Ich) | over 40 min in the beer exchange line alone, with tickets bought earlier in the afternoon. Matched when the median time until service in the exchange lines is 35 min or more for people who join them in that window. A person without tickets stood in the ticket line first | Observed; the 5 min of tolerance is assumed | `calibration.yaml: observations.long_wait` |
| Lines between 18:00 and 20:00 | long lines at the ticket window and at the beer exchange; matched when each holds at least 20 people on average (10 in each of the two beer lines) | Observed; the 20 is assumed | `calibration.yaml: observations.both_lines` |
| Giving up between 18:00 and 20:00 | "a lot of people gave up"; matched when at least 20% of the purchase attempts at the bar that start in that window are given up, either by not joining the line a person sees or by leaving a line before service. People still in line at 21:00 count as not having given up | Observed; the 20% is assumed | `calibration.yaml: observations.gave_up` |
| After 20:00 | the observers stopped trying to buy; every later wait is a prediction of the model | Observed | `calibration.yaml: observations.headliner_window` |
| Occupancy peak | around 22:00; accepted when people inside at 22:00 are at least 90% of the night's maximum | Observed (attendee estimate) | `calibration.yaml: observations.peak_occupancy` |
| Payment system | one ticket window for every drink, then exchange lines (two for beer, one for cocktails and shots); up to 10 tickets per purchase | Observed | `base.yaml: bar.mode = ticket`, `bar.n_cashiers = 1` |
| Buying for friends | people bought several beers per visit | Observed |
| Tickets bought ahead | the observers first bought one ticket per beer, then 10 tickets in one visit for the rest of the night | Observed | `calibration.yaml: priors.bar.bundle_mean` | `calibration.yaml: priors.crowd.group_size_mean` |
| Food | separate counters and staff | Observed | not modelled |
| Staff serving drinks at the peak | 5 to 8 in total; people serving beer taken as 2 to 6, since the ticket window and the cocktail line had their own staff | Observed total, assumed split | `calibration.yaml: priors.bar.n_pour` |
| Roaming sellers | none | Observed | `base.yaml: sellers.n = 0` |
| Re-entry | not allowed; a person who leaves does not come back | Observed | built into `sim/model.py` (one arrival and one departure per attendee) |
| Band popularity | Instagram follower counts of all ten bands, recorded 2026-11-23 | Reported: `docs/sources/popularity_instagram.csv` | `base.yaml: schedule[].ig_followers` |
| Running order | official "Horarios Orus Fest 2026" poster: 11 bands from 13:30 to 01:15 with DJ sets between them, DJs until 03:00; Peter Heppner 22:00 to 23:30, Solitary Experiments 00:00 to 01:15 | Reported: Orus Producciones poster, `docs/sources/orus_fest_2026_schedule.jpg` | `base.yaml: schedule` |
| Crowd behaviour | followers of an act pack the stage front while it plays and wait there through the changeover before it; others go for a beer between sets; more popular acts draw more people to the front | Observed (attendee description) | `base.yaml: crowd`, `schedule[].fans` |

## Attendance

| Item | Value | Source | File |
|---|---|---|---|
| Unique attendees over the day | 2,000 | Reported: video about Orus Fest 2026, <https://www.facebook.com/watch/?v=1338140721641943> | `base.yaml: crowd.n_total` |
| People inside at the peak | model output (`output/tables/calibration_summary.csv`) | Derived from arrivals and departures | `output/runs/calibration_draws.csv: peak_occupancy` |
| Why each person comes | one core act per person, drawn with weight followers² (headliners dominate) | Assumed | `base.yaml: crowd.core_power` |
| How long each person stays | the core band plus a Poisson number of bands before it (mean 1.0 to 4.0) and after it (mean 1.0 to 3.5) | Calibrated | `calibration.yaml: crowd.acts_before_mean`, `crowd.acts_after_mean` |
| Whole-event attendees | 10% to 50% of attendees stay through Solitary Experiments whatever their core band; their arrival follows their window | Calibrated (attendee: "most people came to see several bands or the whole event") | `calibration.yaml: crowd.whole_event_share` |
| Closing DJ crowd | 30% of those who saw the last band stay, leaving uniformly between 01:15 and 03:00 | Assumed | `base.yaml: crowd.close_stay_share` |
| Arrival | 10 to 60 min before the first act of the person's window | Assumed | `base.yaml: crowd.arrival_lead_min` |
| Departure | 0 to 25 min after the last act of the window; nobody re-enters | Assumed | `base.yaml: crowd.leave_lag_min` |
| Doors open, close | 13:00, 03:00 | Reported: the official schedule starts at 13:00 and its last DJ set ends at 03:00 | `base.yaml: event` |

Why 2,000 is read as unique attendees and the peak is lower:

1. A published attendance figure for a festival counts tickets or entries over the whole day.
2. The event ran from 13:00 to 03:00. People who came for the national acts in the afternoon left before the night, and many who came for the headliners arrived after 19:00. With no re-entry each person enters once, so the 2,000 is spread over the day.
3. The free floor is about 710 m² and the vendor strips and tables hold about 350 people. With 2,000 inside at once the free floor would stay near 2.3 people/m² for hours, above the NFPA 101 limit for assembly areas of about 2.2 people/m².
4. VICE México cites a capacity of 2,500 for the hall (<https://www.vice.com/es/article/el-lugar-mas-punk-de-la-cdmx-en-los-90-ex-balneario-olimpico-pantitlan/>). A peak below 2,000 sits under that figure with margin.

The what-if scenarios `baseline_sold_out` and `plan_sold_out` rerun the night with 2,500 attendees, and the staffing grid covers 1,500 to 2,500.

## Running order and followers

Times come from the official schedule poster published by Orus Producciones (`docs/sources/orus_fest_2026_schedule.jpg`). The attendee's earlier recollection put Heppner at 22:30; the poster says 22:00, and the model uses the poster. DJ sets, performances and the 5-minute Remembransas segment between bands are treated as changeovers: nobody follows them, and the crowd orients to the next band. The follower shares are assumed.

Every band's follower share is derived from its Instagram follower count relative to Peter Heppner: share = 0.75 × (followers / 10,700)^0.5. The square root dampens the gaps, since global followers say little about who travels to a Mexico City show; the 0.75 for Heppner is assumed. Counts were recorded on 2026-11-23 from the official profiles; source, handle, value as displayed and screenshot for each are in `docs/sources/popularity_instagram.csv`. Settings: `base.yaml: popularity`, values in `schedule[].ig_followers`.

| Band | Start | End | Instagram followers (2026-11-23) | Followers share |
|---|---|---|---|---|
| Tracción Omega | 13:30 | 14:15 | 326 | 0.13 |
| La Danza de las Ánimas | 14:30 | 15:10 | 1,231 | 0.25 |
| Clekktor | 15:25 | 16:05 | 3,258 | 0.41 |
| Eisfabrik | 16:20 | 17:05 | 6,473 | 0.58 |
| God Module | 17:30 | 18:15 | 7,469 | 0.63 |
| Das Ich | 18:30 | 19:15 | 7,288 | 0.62 |
| Rotersand | 19:35 | 20:20 | 5,433 | 0.53 |
| Funker Vogt | 20:40 | 21:25 | 5,299 | 0.53 |
| Peter Heppner | 22:00 | 23:30 | 10,700 (shown as 10.7K) | 0.75 (anchor) |
| Solitary Experiments | 00:00 | 01:15 | 8,921 | 0.68 |

DJ Scorpio (25,700 followers, shown as 25.7K) is recorded but not used. DJ sets are modelled as changeovers, and a personal account with about 2,900 posts measures social reach more than draw at a show. To test the opposite assumption, change his DJ set to `kind: band` with a `fans` value.

DJ sets: 13:00 to 13:30, then between every pair of bands (15 to 35 min), and from 01:15 to 03:00. File: `base.yaml: schedule`.

## Demand

| Item | Value | Source | File |
|---|---|---|---|
| Share of attendees who drink beer | 0.60 to 0.90 | Calibrated | `calibration.yaml` |
| Beers per hour per drinker (base rate) | mean 0.5 to 1.3, lognormal across people with CV 0.5 | Calibrated mean, assumed spread | `calibration.yaml`, `base.yaml: crowd.rate_cv` |
| Thirst while an act the person follows plays | base rate × 0.35 | Assumed | `base.yaml: crowd.fan_thirst_mult` |
| Thirst while an act the person does not follow plays | base rate × 1.15 | Assumed | `base.yaml: crowd.nonfan_thirst_mult` |
| Thirst in a changeover, person does not follow the next act | base rate × 1.2 to 2.4 | Calibrated | `calibration.yaml: crowd.changeover_boost` |
| Thirst in a changeover, person follows the next act and holds a spot | base rate × 0.6 | Assumed | `base.yaml: crowd.holder_thirst_mult` |
| Drinking pace before 18:00 | base rate × 0.1 to 1.0 | Calibrated (reconciles a large early crowd with the short lines seen at 15:30) | `calibration.yaml: crowd.afternoon_thirst_mult` |
| Minimum time between beers | 14 min per beer | Assumed | `base.yaml: crowd.drink_min` |
| Buyer takes two beers for themself | 30% of visits; a large beer was two bottles or cans poured into one cup | Share assumed; large beers observed | `base.yaml: crowd.double_share` |
| Groups of friends | mean size 1.5 to 3.5 (1 + Poisson, at most 6); a group shares its attendance window, arrival and departure | Calibrated mean | `calibration.yaml: crowd.group_size_mean`, `sim/model.py: _init_agents` |
| Rounds | when one member goes for beer, each friend who has finished their last beer joins with probability 0.7, up to 6 beers per visit. The friend's own thirst is then paused by the time they would still have waited, so rounds do not raise consumption | Assumed | `base.yaml: crowd.round_join_share`, `round_max_beers`, `sim/model.py: _collect_round` |
| First thirst after entering | 5 to 30 min | Assumed | `sim/model.py: _arrivals` |

## Waiting behaviour

| Item | Value | Source | File |
|---|---|---|---|
| Patience (max expected wait a person accepts) | lognormal, median 25 to 180 min, sd of log 0.45. The upper end is well above the 40 min the observers stayed in one line, and the giving-up test bounds it from above | Calibrated median | `calibration.yaml`, `base.yaml: crowd.patience_*` |
| Patience while an act the person follows plays | patience × 0.6 | Assumed | `base.yaml: crowd.fan_patience_mult` |
| Balking | a person who expects to wait longer than their patience does not join and retries 8 to 20 min later | Assumed | `base.yaml: crowd.defer_min` |
| Reneging | a person leaves a line after 1.5 × patience in it | Assumed | `base.yaml: crowd.renege_factor` |
| Line choice | shortest expected wait including a walking estimate at 0.6 m/s; the time per visit at each kind of station is a running average of recent visits | Assumed | `sim/model.py: _route`, `_line_estimate` |

## Bar and payment

| Item | Value | Source | File |
|---|---|---|---|
| Ticket window | 1 | Observed | `base.yaml: bar.n_cashiers` |
| People serving beer | 2 to 6 | Calibrated within the observed total | `calibration.yaml` |
| Ticket window, time per beer buyer | mean 8 to 60 s, lognormal CV 0.45. The window also served buyers of other drinks, so this is an effective time | Calibrated | `calibration.yaml`, `base.yaml: bar.service_cv` |
| Tickets per window visit | the tickets for the current round plus Poisson(mean − 1) spare ones, mean 1.0 to 8.0, at most 10 | Calibrated | `calibration.yaml: bar.bundle_mean` |
| Serving a beer | mean 15 to 75 s for the first beer of a visit; each further beer takes 0.5 to 1.0 of that. All beer was bottled or canned: each one was opened and poured into a cup, and a large beer took two | Calibrated; the bottles and cans were observed | `calibration.yaml: bar.s_pour_mean_s`, `bar.extra_beer_factor` |
| Service clock | a service ends at its exact time and the next one starts then if its customer was waiting | Design choice | `sim/model.py: _serve` |
| Payment at the serving station (scenarios) | 15 s card or cash (the plan), 6 s cashless wristband, 25 s in the slow-payment what-if | Assumed | `scenarios.yaml` |
| Bar layout | counter along the north wall at y = 43.6 m. In the model frame x starts at the east wall: tables in the north-west corner in front of the counter (x 21.1 to 30.1 m), ticket window at x 19.6 m next to the tables, serving stations spread east of it to x 2.0 m; one line per server, lines run south into the floor | Assumed | `base.yaml: bar`, `sim/venue.py` |
| Satellite taps (scenarios) | on the inner edge of a vendor strip, pay at the tap; position and side set per scenario | Assumed | `base.yaml: bar.satellite_*`, `scenarios.yaml` |
| Shift taps (scenarios) | extra taps that take customers only inside a time window | Assumed | `base.yaml: bar.extra_*` |

## Roaming sellers (scenarios only)

| Item | Value | Source | File |
|---|---|---|---|
| Hours | 17:00 to 02:30 (plan and staffing grid: 18:00 to 02:30, from the hour in which lines formed in 2026) | Assumed | `base.yaml: sellers`, `scenarios.yaml`, `staffing.yaml` |
| Load | 6 beers per trip (a tray of 6 large beers in cups) | Observed at other festivals by the study authors | `base.yaml: sellers.capacity` |
| Sale | 30 s per sale of one beer, 12 s more per further beer | Assumed | `base.yaml: sellers.s_sale_s` |
| Refill | walk to the nearer end of the bar, 2 min to refill; 4 min in a what-if | Assumed | `base.yaml: sellers.restock_s` |
| Visibility | a thirsty attendee waits for a seller within 8 m; a seller notices raised hands within 14 m; attendees give up on sellers after 6 min and walk to the bar | Assumed | `base.yaml: sellers.*_radius_m`, `wait_max_min` |
| Movement | patrol toward random attendees, walking speed × 0.85 | Assumed | `base.yaml: sellers.speed_factor` |

## Space and movement

| Item | Value | Source | File |
|---|---|---|---|
| Hall | 52.2 × 30.1 m, read from a satellite screenshot without a scale bar, with vehicles as size references (about ±10% per side). Zones follow the study author's annotated screenshot: stage at the south end, bar at the north end, tables in the north-west corner, a short vendor strip on the west side and a long one on the east side | Estimated | `base.yaml: venue`, `analysis/salon_olimpico_zoning.R` |
| Plan views | stage at the top; the hall appears as on the map after a half turn (east on the left) | Design choice | `base.yaml: venue` |
| Entrance | west wall next to the stage | Assumed | `base.yaml: venue.entrance` |
| Where followers stand | preference decays with distance from the stage edge over 5 m; vendor aisles and tables almost never chosen | Assumed | `base.yaml: venue.front_scale_m`, `sim/venue.py: front_weights` |
| Where everyone else stands | preference rises toward the bar over 10 m, with vendor aisles and tables included | Assumed | `base.yaml: venue.back_scale_m`, `sim/venue.py: back_weights` |
| Crowd shift at a set start or changeover | 85% of followers of the focus act who are not within 12 m of the stage move up; 60% of non-followers within 12 m step back; 10% of the rest pick a new spot | Assumed | `base.yaml: crowd.front_zone_m`, `fan_move_share`, `nonfan_leave_share`, `shuffle_share` |
| Density caps | 3.0 people/m² on the floor, 1.0 in vendor aisles and the table area | Assumed | `base.yaml: venue.*_cap_ppm2` |
| Walking speed | Weidmann speed-density relation, free speed 1.34 m/s | Literature (Weidmann 1993) | `sim/venue.py: weidmann_speed` |

## Staffing and capacity grid

| Item | Value | Source | File |
|---|---|---|---|
| Grid | 1,500 to 2,500 tickets × 4 to 12 serving stations × 0 to 9 sellers, payment at the station (15 s); 3,000 tickets for the capacity chart | Design choice | `config/staffing.yaml` |
| Service target | 9 of 10 buyers who join a line between 18:00 and 02:00 wait at most 10 min; at most 5% of purchase attempts abandoned | Assumed | `config/staffing.yaml: service_target` |
| Reliability | a crew is recommended when it meets the target in at least 90% of the simulated nights; among those, the one with the fewest staff hours | Assumed | `config/staffing.yaml: reliability`, `sim/staffing.py` |
| Safety reference | 2.2 people/m² (NFPA 101 limit for assembly areas of up to 930 m², 0.46 m² per person), compared with the people standing on the free floor. NFPA 101 caps larger areas at 0.65 m² per person (1.54 people/m²); the free floor is about 710 m² and the whole audience area, with vendor strips and tables, about 1,050 m². The technical report gives the ticket level for both values. The licensed capacity of the hall is the legal limit | Literature | `config/staffing.yaml: safety` |

## Analysis

| Item | Value | Source | File |
|---|---|---|---|
| Beer price used for revenue figures | MXN 80 | Assumed | `config/report.yaml` |
| Nights used | 64 nights resampled by weight from the nights that match 2026; 48 of them for the scenarios and 32 for the staffing grid | Design choice (runtime) | `calibration.yaml: sampler`, `scripts/run_scenarios.py --max-draws`, `staffing.yaml: draws` |
| Random seeds | calibration draw d uses seed 10000 + d; scenarios of draw d share seed 50000 + d; staffing grid 90000 + d | Design choice | `scripts/` |

## References

- International Code Council. (2018). *2018 International Building Code*. Country Club Hills, IL: ICC. Table 1004.5, occupant load factor of 0.46 m² (5 ft²) net per person for standing space.
- National Fire Protection Association. (2018). *NFPA 101: Life Safety Code* (2018 ed.). Quincy, MA: NFPA. Section 12.1.7.1, occupant load of assembly areas.
- Orus Producciones. (2026). *Horarios Orus Fest 2026* [Poster]. Salón Olímpico Pantitlán, Mexico City, 1 August 2026. Copy in `docs/sources/orus_fest_2026_schedule.jpg`.
- VICE México. (n.d.). El lugar más punk de la CDMX en los 90: Ex-Balneario Olímpico Pantitlán. Retrieved 23 November 2026, from https://www.vice.com/es/article/el-lugar-mas-punk-de-la-cdmx-en-los-90-ex-balneario-olimpico-pantitlan/
- Video about Orus Fest 2026 [Video]. (2026). Facebook. Retrieved 23 November 2026, from https://www.facebook.com/watch/?v=1338140721641943
- Weidmann, U. (1993). *Transporttechnik der Fussgänger: Transporttechnische Eigenschaften des Fussgängerverkehrs, Literaturauswertung* (2nd, extended ed.; Schriftenreihe des IVT, No. 90). Institut für Verkehrsplanung, Transporttechnik, Strassen- und Eisenbahnbau, ETH Zürich. https://doi.org/10.3929/ethz-b-000242008
