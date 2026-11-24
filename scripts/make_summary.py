"""Figures for the organizer pages, in English and Spanish.

summary_wait_<lang>.png    typical time in line through the night, 2026 and the plan
summary_sales_<lang>.png   beers sold per hour, 2026 and the plan
summary_crews_<lang>.png   crew options and the share of nights in which each meets the target
summary_plan_<lang>.png    floor plan of the recommended setup with numbered actions
The first three also come in a narrow version for phones (summary_*_narrow_<lang>.png).
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
from sim.animate import C_W_POURING, draw_venue  # noqa: E402
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
        "nights": "{k} of {n} nights", "chosen": "recommended", "minimum": "minimum",
        "needed": "{r} of nights",
        "seen": "fitted to what we saw", "estimate": "estimate",
        "wait_title_short": "Time in line by hour joined", "wait_y_short": "minutes in line",
        "seen_narrow": "fitted to\nwhat we saw",
        "crews_title_short": "Crew options, {tickets} tickets",
        "crews_x_short": "nights where 9 of 10 wait {wait} min or less",
        "nights_short": "{k} / {n}",
    },
    "es": {
        "wait_title": "Tiempo en fila según la hora en que la persona se formó",
        "wait_y": "minutos en fila (persona típica)",
        "y2026": "2026", "plan": "Plan", "band": "rango entre noches simuladas",
        "sales_title": "Cervezas vendidas por hora", "sales_y": "cervezas por hora",
        "crews_title": "Opciones de personal para {tickets} boletos, de menos a más horas de trabajo",
        "crews_x": "porcentaje de noches simuladas en que 9 de cada 10 esperan {wait} min o menos",
        "crew": "{taps} puestos", "crew_s": "{taps} puestos + {sellers} vendedores",
        "nights": "{k} de {n} noches", "chosen": "recomendado", "minimum": "mínimo",
        "needed": "{r} de las noches",
        "seen": "ajustado a lo que vimos", "estimate": "estimación",
        "wait_title_short": "Tiempo en fila según la hora", "wait_y_short": "minutos en fila",
        "seen_narrow": "ajustado a\nlo que vimos",
        "crews_title_short": "Opciones de personal, {tickets} boletos",
        "crews_x_short": "noches en que 9 de cada 10 esperan {wait} min o menos",
        "nights_short": "{k} / {n}",
    },
}


def clock_ticks(ax, lo, hi, step=120):
    ticks = np.arange(lo, hi + 1, step)
    ax.set_xticks(ticks)
    ax.set_xticklabels([f"{int(t // 60) % 24:02d}:00" for t in ticks])


# Narrow variants for phones: shown 340 px wide, the smallest text must be at least 11 CSS px.
# A figure NARROW_W inches wide with text of NARROW_FONT points gives
# NARROW_FONT * 340 / (72 * NARROW_W) CSS px, about 11.8 px.
NARROW_W = 4.8
NARROW_FONT = 12
# The narrow crews chart shows the crews that meet the target in at least this share of
# nights (40 of 64), plus the minimum and recommended crews.
NARROW_MIN_SHARE = 40 / 64


def out_name(name: str, lang: str, narrow: bool) -> Path:
    return FIG / (f"{name}_narrow_{lang}.png" if narrow else f"{name}_{lang}.png")


def series_legend(ax, handles, labels, fontsize, ncol=None):
    """Legend between the title and the axes, aligned left (one row unless ncol is given)."""
    ax.legend(handles, labels, frameon=False, loc="lower left", bbox_to_anchor=(0, 1.0),
              ncol=ncol or len(handles), borderaxespad=0.2, handlelength=1.6,
              columnspacing=1.2, fontsize=fontsize)


def wait_figure(waits: pd.DataFrame, head: str, lang: str, narrow: bool = False):
    t = TEXT[lang]
    size = NARROW_FONT if narrow else 13
    fig, ax = plt.subplots(figsize=(NARROW_W, 4.6) if narrow else (10, 4.8))
    lines = []
    for scn, color, name in (("baseline", theme.RED, t["y2026"]), (head, theme.BRONZE, t["plan"])):
        w = waits[waits["scenario"] == scn].groupby("clock_min")["median"].quantile(
            [0.05, 0.5, 0.95]).unstack()
        ax.fill_between(w.index, w[0.05], w[0.95], color=color, alpha=0.22, lw=0)
        lines += ax.plot(w.index, w[0.5], color=color, lw=3)
    band = patches.Patch(color=theme.MUTED, alpha=0.35, lw=0)
    title = t["wait_title_short"] if narrow else t["wait_title"]
    ax.set_title(title, loc="left", pad=52 if narrow else 34,
                 fontsize=size + 1 if narrow else 15)
    ax.set_ylabel(t["wait_y_short"] if narrow else t["wait_y"], fontsize=size)
    ax.grid(axis="y", lw=0.8)
    clock_ticks(ax, 13 * 60, 26 * 60, step=240 if narrow else 120)
    ax.tick_params(labelsize=size)
    ax.set_ylim(bottom=0)
    # The attendees stopped buying at 20:00; the 2026 curve after that hour is an estimate.
    seen_end = 20 * 60
    top = ax.get_ylim()[1]
    ax.axvline(seen_end, color=theme.INK, lw=1.2, ls=(0, (4, 3)), alpha=0.8)
    seen = t["seen_narrow"] if narrow else t["seen"]
    gap = 20 if narrow else 8
    ax.text(seen_end - gap, top * 0.97, seen, ha="right", va="top",
            fontsize=size if narrow else 11.5, color=theme.MUTED, linespacing=1.15)
    ax.text(seen_end + gap, top * 0.97, t["estimate"], ha="left", va="top",
            fontsize=size if narrow else 11.5, color=theme.MUTED)
    series_legend(ax, lines + [band], [t["y2026"], t["plan"], t["band"]],
                  size if narrow else 12, ncol=2 if narrow else None)
    fig.savefig(out_name("summary_wait", lang, narrow), dpi=160, bbox_inches="tight")
    plt.close(fig)


def sales_figure(v: dict, lang: str, narrow: bool = False):
    t = TEXT[lang]
    size = NARROW_FONT if narrow else 13
    fig, ax = plt.subplots(figsize=(NARROW_W, 4.4) if narrow else (10, 4.8))
    width = 0.4
    for k, (df, color, name) in enumerate(((v["hourly_2026"], theme.RED, t["y2026"]),
                                           (v["hourly_plan"], theme.BRONZE, t["plan"]))):
        x = np.arange(len(df)) + (k - 0.5) * width
        ax.bar(x, df["med"], width=width, color=color, edgecolor=theme.PAPER,
               linewidth=0.8 if narrow else 1.5, label=name)
        ax.vlines(x, df["lo"], df["hi"], color=theme.INK, lw=1.0 if narrow else 1.2, alpha=0.7)
    clocks = v["hourly_plan"]["clock"].tolist()
    every = 3 if narrow else 1
    ax.set_xticks(np.arange(len(clocks))[::every])
    ax.set_xticklabels(clocks[::every], rotation=0, fontsize=size if narrow else 10.5)
    ax.tick_params(axis="y", labelsize=size)
    ax.set_title(t["sales_title"], loc="left", pad=30 if narrow else 34,
                 fontsize=size + 1 if narrow else 15)
    ax.set_ylabel(t["sales_y"], fontsize=size)
    ax.grid(axis="y", lw=0.8)
    ax.set_axisbelow(True)
    handles, labels = ax.get_legend_handles_labels()
    series_legend(ax, handles, labels, size if narrow else 12)
    fig.savefig(out_name("summary_sales", lang, narrow), dpi=160, bbox_inches="tight")
    plt.close(fig)


def crews_figure(v: dict, lang: str, narrow: bool = False):
    t, raw = TEXT[lang], v["raw"]
    crews = v["crews"]
    chosen = (crews["n_pour"] == raw["plan_taps"]) & (crews["sellers"] == raw["plan_sellers"])
    minimum = (crews["n_pour"] == raw["min_taps"]) & (crews["sellers"] == raw["min_sellers"])
    # the recommended crew, every crew with fewer staff hours (the minimum crew among them),
    # and the smallest crew without sellers that reaches the minimum reliability; the
    # technical page shows the full grid
    limit = crews.loc[chosen, "staff_hours"].iloc[0]
    keep = crews["staff_hours"] <= limit
    alone = crews[(crews["sellers"] == 0) & (crews["share_met"] >= raw["reliability"])]
    if len(alone):
        keep |= crews.index == alone.sort_values("staff_hours").index[0]
    if narrow:
        keep &= crews["share_met"] >= NARROW_MIN_SHARE
        keep |= chosen | minimum
    crews = crews[keep].sort_values(["staff_hours", "staff"], ascending=False)
    names = [t["crew_s" if r.sellers else "crew"].format(taps=int(r.n_pour), sellers=int(r.sellers))
             for r in crews.itertuples()]
    chosen = ((crews["n_pour"] == raw["plan_taps"])
              & (crews["sellers"] == raw["plan_sellers"])).to_numpy()
    minimum = ((crews["n_pour"] == raw["min_taps"])
               & (crews["sellers"] == raw["min_sellers"])).to_numpy() & ~chosen
    colors = np.where(chosen, theme.BRONZE, np.where(minimum, "#8c6a2c", theme.SILVER))

    def tag(c, mn):
        if c:
            return t["chosen"] + (f" = {t['minimum']}" if raw["fallback"] else "")
        return t["minimum"] if mn else ""

    y = np.arange(len(crews))
    if narrow:
        # each label on its own line above its bar, the count of nights at the end of the bar
        step = 1.6
        y = y * step
        fig, ax = plt.subplots(figsize=(NARROW_W, 0.62 * len(crews) + 1.9))
        ax.barh(y, 100 * crews["share_met"], color=colors, edgecolor=theme.PAPER,
                linewidth=1.0, height=0.62)
        for yi, name, r, c, mn in zip(y, names, crews.itertuples(), chosen, minimum):
            label = name + (f"  ·  {tag(c, mn)}" if tag(c, mn) else "")
            ax.text(0, yi + 0.42, label, va="bottom", ha="left", fontsize=NARROW_FONT,
                    fontweight="bold" if (c or mn) else "normal", color=theme.INK, zorder=4,
                    bbox={"fc": ax.get_facecolor(), "ec": "none", "pad": 1.0})
            ax.text(102, yi, t["nights_short"].format(
                k=int(r.nights_met), n=int(r.nights)), va="center", fontsize=NARROW_FONT,
                color=theme.INK)
        for share in (raw["reliability"], raw["reliability_rec"]):
            ax.axvline(100 * share, color=theme.INK, lw=1.0, ls=(0, (4, 3)), alpha=0.8)
        ax.text(100 * raw["reliability_rec"] + 2.5, y.max() + 1.45,
                f"{100 * raw['reliability']:.0f}% · {100 * raw['reliability_rec']:.0f}%",
                ha="left", va="top", fontsize=NARROW_FONT, color=theme.MUTED)
        ax.set_yticks([])
        ax.set_ylim(y.min() - 0.6, y.max() + 1.5)
        ax.set_xlim(0, 128)
        ax.set_xticks([0, 50, 100])
        ax.set_xticklabels(["0%", "50%", "100%"], fontsize=NARROW_FONT)
        ax.set_xlabel(t["crews_x_short"].format(wait=raw["target_wait"]), fontsize=NARROW_FONT)
        ax.set_title(t["crews_title_short"].format(tickets=f"{raw['tickets']:,}"), loc="left",
                     pad=10, fontsize=NARROW_FONT + 1)
        ax.spines["left"].set_visible(False)
        fig.savefig(out_name("summary_crews", lang, narrow), dpi=160, bbox_inches="tight")
        plt.close(fig)
        return

    fig, ax = plt.subplots(figsize=(10, 0.46 * len(crews) + 1.6))
    ax.barh(y, 100 * crews["share_met"], color=colors, edgecolor=theme.PAPER, linewidth=1.5,
            height=0.7)
    for yi, r, c, mn in zip(y, crews.itertuples(), chosen, minimum):
        label = t["nights"].format(k=int(r.nights_met), n=int(r.nights))
        if tag(c, mn):
            label += f"  ·  {tag(c, mn)}"
        ax.text(103, yi, label, va="center", fontsize=11.5,
                fontweight="bold" if (c or mn) else "normal")
    for share in (raw["reliability"], raw["reliability_rec"]):
        ax.axvline(100 * share, color=theme.INK, lw=1.0, ls=(0, (4, 3)), alpha=0.8)
    ax.text(100 * raw["reliability"] - 1, len(crews) - 0.35,
            f"{t['minimum']} {100 * raw['reliability']:.0f}%", fontsize=10,
            color=theme.MUTED, va="bottom", ha="right")
    ax.text(100 * raw["reliability_rec"] + 1, len(crews) - 0.35,
            f"{t['chosen']} {100 * raw['reliability_rec']:.0f}%", fontsize=10,
            color=theme.MUTED, va="bottom", ha="left")
    ax.set_yticks(y)
    ax.set_yticklabels(names)
    ax.set_xlim(0, 150)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"])
    ax.set_xlabel(t["crews_x"].format(wait=raw["target_wait"]), fontsize=11.5)
    ax.set_title(t["crews_title"].format(tickets=f"{raw['tickets']:,}"), loc="left", pad=12)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    fig.savefig(out_name("summary_crews", lang, narrow), dpi=160, bbox_inches="tight")
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
    # one person behind each station of the recommended crew
    ax.scatter(xs, np.full(len(xs), cy + 1.0), s=46, marker="s", c=C_W_POURING,
               edgecolors=theme.INK, linewidths=1.0, zorder=6)
    # open walkway beside the lighting booth, from the stage front to the end of the lanes
    walk_x = 9.5
    ax.add_patch(patches.FancyArrowPatch((walk_x, vz["stage"]["y1"] + 3), (walk_x, cy - 7.5),
                                         arrowstyle="<|-|>", mutation_scale=16, lw=1.6,
                                         color=theme.MUTED, linestyle=(0, (4, 3))))
    # one dot per seller of the plan, on open floor clear of the booth and the cocktail line
    slots = [(7.5, 15.0), (21.0, 15.5), (15.5, 31.5), (7.0, 33.0), (21.5, 30.0), (15.0, 14.0),
             (7.0, 22.0), (21.5, 22.5), (11.0, 18.0), (18.5, 19.0), (19.0, 35.5), (10.5, 37.0),
             (15.5, 19.5), (7.5, 29.0), (23.0, 12.0)]
    if raw["plan_sellers"]:
        sx, sy = np.array(slots[:min(raw["plan_sellers"], len(slots))]).T
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
    badge(5, walk_x - 2.6, (vz["stage"]["y1"] + cy) / 2 - 1.0)   # open floor and ticket cap
    badge(6, vz["tables"]["x0"] + 4.5, cy + 3.2)                 # service limits
    fig.savefig(FIG / f"summary_plan_{lang}.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    v = report_values.compute()
    head = params.load(params.ROOT / "config" / "report.yaml")["headline_scenario"]
    waits = pd.read_csv(RUNS / "scenario_waits.csv")
    for lang in ("en", "es"):
        for narrow in (False, True):
            wait_figure(waits, head, lang, narrow)
            sales_figure(v, lang, narrow)
            crews_figure(v, lang, narrow)
        plan_figure(v, lang)
    print("summary figures written to", FIG)


if __name__ == "__main__":
    main()
