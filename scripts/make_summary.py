"""Figures for the organizer pages, in English and Spanish.

summary_wait_<lang>.png    typical time in line through the night, 2026 and the plan
summary_sales_<lang>.png   beers sold per hour, 2026 and the plan
summary_crews_<lang>.png   crew options and the share of nights in which each meets the target
summary_plan_<lang>.png    floor plan of the recommended setup with numbered actions
Reads output/tables and output/runs through scripts/report_values.py.
Usage: uv run python scripts/make_summary.py
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib import patches  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import report_values  # noqa: E402
from sim import params, theme  # noqa: E402
from sim import scenarios as sc  # noqa: E402
from sim.animate import draw_venue  # noqa: E402
from sim.venue import Venue  # noqa: E402

FIG = params.ROOT / "output" / "figures"
RUNS = params.ROOT / "output" / "runs"
theme.apply()
plt.rcParams.update({"font.size": 13, "axes.titlesize": 15, "axes.titleweight": "bold",
                     "axes.spines.top": False, "axes.spines.right": False})

TEXT = {
    "en": {
        "wait_title": "Time in line by the hour a person joined",
        "wait_y": "minutes in line (typical person)",
        "y2026": "2026", "plan": "Plan", "band": "range across simulated nights",
        "sales_title": "Beers sold per hour", "sales_y": "beers per hour",
        "crews_title": "Crew options for {tickets} tickets, from fewer to more staff hours",
        "crews_x": "share of simulated nights in which 9 of 10 buyers wait {wait} min or less",
        "crew": "{taps} stations", "crew_s": "{taps} stations + {sellers} sellers",
        "nights": "{k} of {n} nights", "chosen": "recommended", "needed": "minimum {r}",
    },
    "es": {
        "wait_title": "Tiempo en fila según la hora en que la persona se formó",
        "wait_y": "minutos en fila (persona típica)",
        "y2026": "2026", "plan": "Plan", "band": "rango entre noches simuladas",
        "sales_title": "Cervezas vendidas por hora", "sales_y": "cervezas por hora",
        "crews_title": "Opciones de personal para {tickets} boletos, de menos a más horas de trabajo",
        "crews_x": "porcentaje de noches simuladas en que 9 de cada 10 esperan {wait} min o menos",
        "crew": "{taps} puestos", "crew_s": "{taps} puestos + {sellers} vendedores",
        "nights": "{k} de {n} noches", "chosen": "recomendado", "needed": "mínimo {r}",
    },
}


def clock_ticks(ax, lo, hi, step=120):
    ticks = np.arange(lo, hi + 1, step)
    ax.set_xticks(ticks)
    ax.set_xticklabels([f"{int(t // 60) % 24:02d}:00" for t in ticks])


def wait_figure(waits: pd.DataFrame, head: str, lang: str):
    t = TEXT[lang]
    fig, ax = plt.subplots(figsize=(10, 4.8))
    for scn, color, name in (("baseline", theme.RED, t["y2026"]), (head, theme.BRONZE, t["plan"])):
        w = waits[waits["scenario"] == scn].groupby("clock_min")["median"].quantile(
            [0.05, 0.5, 0.95]).unstack()
        ax.fill_between(w.index, w[0.05], w[0.95], color=color, alpha=0.22, lw=0)
        ax.plot(w.index, w[0.5], color=color, lw=3, label=name)
    ax.set_title(t["wait_title"], loc="left", pad=12)
    ax.set_ylabel(t["wait_y"])
    ax.grid(axis="y", lw=0.8)
    clock_ticks(ax, 13 * 60, 26 * 60)
    ax.set_ylim(bottom=0)
    ax.legend(frameon=False, loc="upper left", ncol=2)
    fig.savefig(FIG / f"summary_wait_{lang}.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


def sales_figure(v: dict, lang: str):
    t = TEXT[lang]
    fig, ax = plt.subplots(figsize=(10, 4.8))
    width = 0.4
    for k, (df, color, name) in enumerate(((v["hourly_2026"], theme.RED, t["y2026"]),
                                           (v["hourly_plan"], theme.BRONZE, t["plan"]))):
        x = np.arange(len(df)) + (k - 0.5) * width
        ax.bar(x, df["med"], width=width, color=color, edgecolor=theme.PAPER, linewidth=1.5,
               label=name)
        ax.vlines(x, df["lo"], df["hi"], color=theme.INK, lw=1.2, alpha=0.7)
    ax.set_xticks(np.arange(len(v["hourly_plan"])))
    ax.set_xticklabels(v["hourly_plan"]["clock"], rotation=0, fontsize=10.5)
    ax.set_title(t["sales_title"], loc="left", pad=12)
    ax.set_ylabel(t["sales_y"])
    ax.grid(axis="y", lw=0.8)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="upper left", ncol=2)
    fig.savefig(FIG / f"summary_sales_{lang}.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


def crews_figure(v: dict, lang: str):
    t, raw = TEXT[lang], v["raw"]
    crews = v["crews"]
    chosen = (crews["n_pour"] == raw["plan_taps"]) & (crews["sellers"] == raw["plan_sellers"])
    # the recommended crew, every crew with fewer staff hours, and the smallest crew
    # without sellers that reaches the reliability; the technical page shows the full grid
    limit = crews.loc[chosen, "staff_hours"].iloc[0]
    alone = crews[(crews["sellers"] == 0) & (crews["share_met"] >= raw["reliability"])]
    keep = crews["staff_hours"] <= limit
    if len(alone):
        keep |= crews.index == alone.sort_values("staff_hours").index[0]
    crews = crews[keep].sort_values(["staff_hours", "staff"], ascending=False)
    names = [t["crew_s" if r.sellers else "crew"].format(taps=int(r.n_pour), sellers=int(r.sellers))
             for r in crews.itertuples()]
    chosen = (crews["n_pour"] == raw["plan_taps"]) & (crews["sellers"] == raw["plan_sellers"])
    colors = np.where(chosen, theme.BRONZE, theme.SILVER)
    fig, ax = plt.subplots(figsize=(10, 0.46 * len(crews) + 1.6))
    y = np.arange(len(crews))
    ax.barh(y, 100 * crews["share_met"], color=colors, edgecolor=theme.PAPER, linewidth=1.5,
            height=0.7)
    for yi, r, c in zip(y, crews.itertuples(), chosen):
        label = t["nights"].format(k=int(r.nights_met), n=int(r.nights))
        if c:
            label += f"  ·  {t['chosen']}"
        ax.text(103, yi, label, va="center", fontsize=11.5,
                fontweight="bold" if c else "normal")
    ax.axvline(100 * raw["reliability"], color=theme.INK, lw=1.2, ls=(0, (4, 3)))
    ax.text(100 * raw["reliability"] - 1, len(crews) - 0.35,
            t["needed"].format(r=f"{100 * raw['reliability']:.0f}%"), fontsize=10.5,
            color=theme.MUTED, va="bottom", ha="right")
    ax.set_yticks(y)
    ax.set_yticklabels(names)
    ax.set_xlim(0, 140)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"])
    ax.set_xlabel(t["crews_x"].format(wait=raw["target_wait"]), fontsize=11.5)
    ax.set_title(t["crews_title"].format(tickets=f"{raw['tickets']:,}"), loc="left", pad=12)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    fig.savefig(FIG / f"summary_crews_{lang}.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


def plan_figure(v: dict, lang: str):
    raw = v["raw"]
    base = params.load()
    cfg = sc.apply(base, {"overrides": {"bar.mode": "direct", "bar.n_pour": raw["plan_taps"],
                                        "sellers.n": raw["plan_sellers"]}})
    venue = Venue(cfg)
    pts = [(p.kind, p.x, p.y) for p in venue.build_service_points(cfg)]
    vz = cfg["venue"]
    cy = vz["counter_y"]
    fig, ax = plt.subplots(figsize=(6.4, 9.6))
    draw_venue(ax, cfg, pts, lang=lang)
    xs = sorted(x for kind, x, _ in pts if kind == "direct")
    for x in xs:                                   # one barrier lane per station
        for dx in (-0.55, 0.55):
            ax.plot([x + dx, x + dx], [cy - 0.4, cy - 6.4], color=theme.INK, lw=1.4,
                    solid_capstyle="round")
    ax.add_patch(patches.FancyArrowPatch((13.0, vz["stage"]["y1"] + 3), (13.0, cy - 7.5),
                                         arrowstyle="<|-|>", mutation_scale=16, lw=1.6,
                                         color=theme.MUTED, linestyle=(0, (4, 3))))
    slots = [(9.0, 18.0), (19.0, 22.0), (9.5, 28.0), (18.5, 15.5), (8.0, 23.5), (19.5, 29.0)]
    if raw["plan_sellers"]:
        sx, sy = np.array(slots[:raw["plan_sellers"]]).T
        ax.scatter(sx, sy, s=120, c=theme.DOT_SELLER, edgecolors=theme.PAPER, linewidths=1.0,
                   zorder=6)

    def badge(n, x, y):
        ax.add_patch(patches.Circle((x, y), 1.55, fc=theme.BRONZE, ec=theme.PAPER, lw=1.8,
                                    zorder=8))
        ax.text(x, y, str(n), ha="center", va="center", color=theme.PAPER, fontsize=13,
                fontweight="bold", zorder=9)

    badge(1, xs[0] + 2.0, cy + 3.2)                              # pay where the beer is served
    badge(2, float(np.mean(xs)) + 1.0, cy + 3.2)                 # crew size
    badge(3, slots[0][0] - 3.0, slots[0][1])                     # sellers
    badge(4, xs[len(xs) // 2], cy - 8.6)                         # barrier lanes
    badge(5, 13.0 + 2.6, (vz["stage"]["y1"] + cy) / 2 - 4.0)     # open floor and ticket cap
    badge(6, vz["tables"]["x0"] + 4.5, cy + 3.2)                 # service limits
    fig.savefig(FIG / f"summary_plan_{lang}.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    v = report_values.compute()
    head = params.load(params.ROOT / "config" / "report.yaml")["headline_scenario"]
    waits = pd.read_csv(RUNS / "scenario_waits.csv")
    for lang in ("en", "es"):
        wait_figure(waits, head, lang)
        sales_figure(v, lang)
        crews_figure(v, lang)
        plan_figure(v, lang)
    print("summary figures written to", FIG)


if __name__ == "__main__":
    main()
