# Sources

Primary material behind the model inputs. Each file is referenced from `config/base.yaml` and `docs/ASSUMPTIONS.md`.

| File | Content | Recorded | Used for |
|---|---|---|---|
| `orus_fest_2026_schedule.jpg` | "Horarios Orus Fest 2026" poster by Orus Producciones, Salón Olímpico Pantitlán, 1 August 2026 | supplied 2026-11-23 | running order, doors and close (`base.yaml: schedule`, `event`) |
| `popularity_instagram.csv` | Instagram follower counts of every band and DJ Scorpio, with handle, value as shown, date and evidence file | 2026-11-23 | follower shares (`base.yaml: schedule[].ig_followers`, `popularity`) |
| `instagram_*.jpg` | screenshots of the profile headers listed in `popularity_instagram.csv` | 2026-11-23 | evidence for the counts |

Counts are as displayed by Instagram on the recording date. "10.7K" and "25.7K" are rounded by Instagram and entered as 10,700 and 25,700. Follower counts change over time; rerunning with new counts means editing `ig_followers` in `config/base.yaml` and adding a row here with the new date.

Web sources (accessed 2026-11-23):

- Attendance of 2,000: video about Orus Fest 2026, <https://www.facebook.com/watch/?v=1338140721641943> (figure as relayed by the study author; the page itself could not be opened from the analysis environment).
- Hall capacity of 2,500: VICE México, "El lugar más punk de la CDMX en los 90: Ex-Balneario Olímpico Pantitlán", <https://www.vice.com/es/article/el-lugar-mas-punk-de-la-cdmx-en-los-90-ex-balneario-olimpico-pantitlan/>.
- Coordinates of the venue: Google Maps place "SALÓN OLIMPICO", 19.4119544, -99.0690891.
