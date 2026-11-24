"""Figures for the organizer pages, in English and Spanish.

summary_wait_<lang>.png    typical time in line through the night, 2026 and the plan
summary_sales_<lang>.png   beers sold per hour, 2026 and the plan
summary_crews_<lang>.png   crew options and the share of nights in which each meets the target
summary_plan_<lang>.png    floor plan of the recommended setup with numbered actions
summary_changes_<lang>.png wait of 9 of 10 buyers for single changes and the plan
summary_mixes_<lang>.png   crews of the recommended level under the stress cases
summary_busy_<lang>.png    share of time the bar staff are busy, by hour
before_after_og_<lang>.png 1200 x 630 image for link previews
The charts also come in a narrow version for phones (summary_*_narrow_<lang>.png).
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
        "complete": "complete",
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
        "complete": "completo",
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
    """Crew options at the plan ticket level from fewer to more staff hours, up to the
    complete crew. The minimum, recommended and complete crews are highlighted with a fill
    and a bold label; dashed lines mark the shares of the minimum and recommended levels."""
    t, raw = TEXT[lang], v["raw"]
    crews = v["crews"]

    def is_crew(df, taps, sellers):
        return (df["n_pour"] == taps) & (df["sellers"] == sellers)

    levels = [("minimum", raw["min_taps"], raw["min_sellers"], "#8c6a2c"),
              ("chosen", raw["plan_taps"], raw["plan_sellers"], theme.BRONZE),
              ("complete", raw["full_taps"], raw["full_sellers"], "#d9a441")]
    marked = np.zeros(len(crews), bool)
    for _, taps, sellers, _ in levels:
        marked |= np.array(is_crew(crews, taps, sellers), dtype=bool)
    limit = crews.loc[is_crew(crews, raw["full_taps"], raw["full_sellers"]), "staff_hours"]
    limit = float(limit.iloc[0]) if len(limit) else crews["staff_hours"].max()
    keep = np.array(crews["staff_hours"] <= limit, dtype=bool)
    if narrow:
        keep &= np.array(crews["share_met"] >= NARROW_MIN_SHARE, dtype=bool)
    crews = crews[keep | marked].sort_values(["staff_hours", "staff"], ascending=False)
    names = [t["crew_s" if r.sellers else "crew"].format(taps=int(r.n_pour), sellers=int(r.sellers))
             for r in crews.itertuples()]
    tags, colors = [], []
    for r in crews.itertuples():
        tag, color = "", theme.SILVER
        for key, taps, sellers, c in levels:
            if (r.n_pour, r.sellers) == (taps, sellers):
                tag = t[key] if not tag else f"{tag} = {t[key]}"
                color = c
        tags.append(tag)
        colors.append(color)
    rec, rmin = 100 * raw["reliability_rec"], 100 * raw["reliability"]

    y = np.arange(len(crews))
    if narrow:
        # each label on its own line above its bar, the count of nights at the end of the bar
        y = y * 1.6
        fig, ax = plt.subplots(figsize=(NARROW_W, 0.62 * len(crews) + 2.4))
        ax.barh(y, 100 * crews["share_met"], color=colors, edgecolor=theme.PAPER,
                linewidth=1.0, height=0.62)
        for yi, name, r, tag in zip(y, names, crews.itertuples(), tags):
            label = name + (f"  ·  {tag}" if tag else "")
            ax.text(0, yi + 0.42, label, va="bottom", ha="left", fontsize=NARROW_FONT,
                    fontweight="bold" if tag else "normal", color=theme.INK, zorder=4,
                    bbox={"fc": ax.get_facecolor(), "ec": "none", "pad": 1.0})
            ax.text(102, yi, t["nights_short"].format(k=int(r.nights_met), n=int(r.nights)),
                    va="center", fontsize=NARROW_FONT, color=theme.INK,
                    fontweight="bold" if tag else "normal")
        for share in (rmin, rec):
            ax.axvline(share, color=theme.INK, lw=1.0, ls=(0, (4, 3)), alpha=0.8)
        top = y.max()
        box = {"fc": ax.get_facecolor(), "ec": "none", "pad": 1.5}
        ax.text(rec - 1, top + 2.45, f"{t['chosen']} {rec:.0f}%", ha="right", va="center",
                fontsize=NARROW_FONT, color=theme.MUTED, bbox=box, zorder=5)
        ax.text(rmin - 1, top + 1.75, f"{t['minimum']} {rmin:.0f}%", ha="right", va="center",
                fontsize=NARROW_FONT, color=theme.MUTED, bbox=box, zorder=5)
        ax.set_yticks([])
        ax.set_ylim(y.min() - 0.6, top + 2.9)
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

    fig, ax = plt.subplots(figsize=(10, 0.46 * len(crews) + 1.8))
    ax.barh(y, 100 * crews["share_met"], color=colors, edgecolor=theme.PAPER, linewidth=1.5,
            height=0.7)
    for yi, r, tag in zip(y, crews.itertuples(), tags):
        label = t["nights"].format(k=int(r.nights_met), n=int(r.nights))
        if tag:
            label += f"  ·  {tag}"
        ax.text(103, yi, label, va="center", fontsize=11.5,
                fontweight="bold" if tag else "normal")
    for share in (rmin, rec):
        ax.axvline(share, color=theme.INK, lw=1.0, ls=(0, (4, 3)), alpha=0.8)
    ax.text(rmin - 1, len(crews) - 0.35, f"{t['minimum']} {rmin:.0f}%", fontsize=10,
            color=theme.MUTED, va="bottom", ha="right")
    ax.text(rec + 1, len(crews) - 0.35, f"{t['chosen']} {rec:.0f}%", fontsize=10,
            color=theme.MUTED, va="bottom", ha="left")
    ax.set_yticks(y)
    ax.set_yticklabels(names)
    for lab, tag in zip(ax.get_yticklabels(), tags):
        if tag:
            lab.set_fontweight("bold")
    ax.set_ylim(-0.6, len(crews) + 0.4)
    ax.set_xlim(0, 155)
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


CHANGES = {"en": {"baseline": "2026 as it was", "more_cashiers": "4 ticket windows",
                  "pay_at_tap": "Payment at the bar, same staff",
                  "sellers_6": "6 floor sellers", "plan": "The plan"},
           "es": {"baseline": "2026 como fue", "more_cashiers": "4 ventanillas de fichas",
                  "pay_at_tap": "Cobrar en la barra, mismo personal",
                  "sellers_6": "6 vendedores en pista", "plan": "El plan"}}
MORE = {"en": {"x": "wait of 9 of 10 buyers, 18:00 to 02:00 (min)", "beers": "+{b} beers",
               "title": "Each change on its own against 2026",
               "mix_title": "Crews with almost the same hours, {tickets} tickets",
               "mix_x": "nights that meet the target (of {n})", "base": "base night",
               "worst": "worst of {k} stress cases", "chosen": "chosen",
               "busy_title": "Share of time the bar staff are busy",
               "busy_y": "busy (charging or serving)", "plan": "Plan", "y2026": "2026",
               "hours": "{h} h"},
        "es": {"x": "espera de 9 de cada 10 compradores, 18:00 a 02:00 (min)",
               "beers": "+{b} cervezas", "title": "Cada cambio por separado frente a 2026",
               "mix_title": "Combinaciones con casi las mismas horas, {tickets} boletos",
               "mix_x": "noches que cumplen la meta (de {n})", "base": "noche base",
               "worst": "peor de {k} casos de estrés", "chosen": "elegida",
               "busy_title": "Porcentaje del tiempo que la barra está ocupada",
               "busy_y": "ocupada (cobrando o sirviendo)", "plan": "Plan", "y2026": "2026",
               "hours": "{h} h"}}


def changes_figure(v: dict, lang: str, narrow: bool = False):
    """Wait of 9 of 10 buyers for 2026, three single changes and the plan; whiskers from the
    5th to the 95th percentile between nights; extra beers at the end of each bar."""
    m, eff = v["scenario_metrics"], v["effects"]
    names, t = CHANGES[lang], MORE[lang]
    size = NARROW_FONT if narrow else 12
    keys = list(names)
    fig, ax = plt.subplots(figsize=(NARROW_W, 5.4) if narrow else (10, 4.2))
    y = np.arange(len(keys))[::-1] * (1.7 if narrow else 1.0)
    top = 0.0
    for yi, k in zip(y, keys):
        x = m.loc[m["scenario"] == k, "evening_p90_min"]
        med, lo, hi = x.median(), x.quantile(0.05), x.quantile(0.95)
        top = max(top, hi)
        color = theme.BRONZE if k == "plan" else (theme.RED if k == "baseline" else theme.SILVER)
        ax.barh(yi, med, color=color, height=0.55, edgecolor=theme.PAPER)
        ax.hlines(yi, lo, hi, color=theme.INK, lw=1.3, alpha=0.8)
        if k == "baseline":
            beers = ""
        else:
            e = eff[(eff["scenario"] == k) & eff["outcome"].str.startswith("Beers")].iloc[0]
            beers = t["beers"].format(b=f"{e['med']:,.0f}")
        label = f"{np.ceil(med - 1e-9):.0f} min" + (f"  ·  {beers}" if beers else "")
        if narrow:
            ax.text(0, yi + 0.42, names[k], fontsize=size, va="bottom", color=theme.INK,
                    fontweight="bold" if k == "plan" else "normal")
            ax.text(hi + 3, yi, label, fontsize=size, va="center", color=theme.INK)
        else:
            ax.text(hi + 3, yi, label, fontsize=size, va="center", color=theme.INK)
    if not narrow:
        ax.set_yticks(y)
        ax.set_yticklabels([names[k] for k in keys], fontsize=size)
    else:
        ax.set_yticks([])
        ax.set_ylim(y.min() - 0.6, y.max() + 1.2)
    ax.set_xlim(0, top * (1.75 if narrow else 1.45))
    ax.set_xlabel(t["x"], fontsize=size)
    ax.tick_params(axis="x", labelsize=size)
    ax.tick_params(axis="y", length=0)
    ax.spines["left"].set_visible(False)
    ax.set_title(t["title"], loc="left", fontsize=size + 1 if narrow else 15, pad=10)
    ax.grid(axis="x", lw=0.8)
    ax.set_axisbelow(True)
    fig.savefig(out_name("summary_changes", lang, narrow), dpi=160, bbox_inches="tight")
    plt.close(fig)


def mixes_figure(v: dict, lang: str, narrow: bool = False):
    """Candidate crews of the recommended level at the plan ticket level: nights met on the
    base night and in the worst stress case. The chosen crew is drawn bold and marked."""
    path = params.ROOT / "output" / "tables" / "crew_mixes.csv"
    if not path.exists():
        return
    t, raw = MORE[lang], v["raw"]
    mx = pd.read_csv(path)
    mx = mx[(mx["n_total"] == raw["tickets"]) & (mx["level"] == "recommended")]
    crews = mx.groupby(["n_pour", "sellers"]).agg(
        hours=("staff_hours", "first"), chosen=("chosen", "first"),
        base=("nights_met", lambda s: s[mx.loc[s.index, "case"] == "base"].iloc[0]),
        worst=("nights_met", lambda s: s[mx.loc[s.index, "case"] != "base"].min()),
        nights=("nights", "first"), cases=("case", lambda c: (c != "base").sum())
    ).reset_index().sort_values("hours")
    size = NARROW_FONT if narrow else 12
    fig, ax = plt.subplots(figsize=(NARROW_W, 0.95 * len(crews) + 1.6) if narrow
                           else (10, 0.62 * len(crews) + 1.8))
    step = 1.9 if narrow else 1.0
    y = np.arange(len(crews))[::-1] * step
    crew_txt = TEXT[lang]["crew_s"]
    for yi, r in zip(y, crews.itertuples()):
        bold = "bold" if r.chosen else "normal"
        ax.barh(yi + 0.18, r.base, height=0.32, color=theme.SILVER)
        ax.barh(yi - 0.18, r.worst, height=0.32,
                color=theme.BRONZE if r.chosen else theme.RED, hatch=None if r.chosen else "//",
                edgecolor=theme.PAPER)
        name = crew_txt.format(taps=r.n_pour, sellers=r.sellers) + " · " + t["hours"].format(
            h=f"{r.hours:.0f}") + (f"  ·  {t['chosen']}" if r.chosen else "")
        if narrow:
            ax.text(0, yi + 0.42, name, fontsize=size, va="bottom", fontweight=bold,
                    color=theme.INK)
        else:
            ax.text(-1.5, yi, name, fontsize=size, va="center", ha="right", fontweight=bold,
                    color=theme.INK)
        ax.text(r.base + 0.8, yi + 0.18, f"{r.base}", fontsize=size - 1, va="center",
                color=theme.INK)
        ax.text(r.worst + 0.8, yi - 0.18, f"{r.worst}", fontsize=size - 1, va="center",
                color=theme.INK, fontweight=bold)
    n = int(crews["nights"].iloc[0])
    ax.set_xlim(0, n * 1.12)
    ax.set_yticks([])
    if narrow:
        ax.set_ylim(y.min() - 0.6, y.max() + 1.25)
    ax.set_xlabel(t["mix_x"].format(n=n), fontsize=size)
    ax.tick_params(axis="x", labelsize=size)
    ax.spines["left"].set_visible(False)
    from matplotlib.patches import Patch
    handles = [Patch(color=theme.SILVER, label=t["base"]),
               Patch(facecolor=theme.RED, hatch="//", edgecolor=theme.PAPER,
                     label=t["worst"].format(k=int(crews["cases"].iloc[0])))]
    series_legend(ax, handles, [h.get_label() for h in handles], size if narrow else 12,
                  ncol=1 if narrow else None)
    ax.set_title(t["mix_title"].format(tickets=f"{raw['tickets']:,}"), loc="left",
                 pad=48 if narrow else 30, fontsize=size + 1 if narrow else 15)
    fig.savefig(out_name("summary_mixes", lang, narrow), dpi=160, bbox_inches="tight")
    plt.close(fig)


def busy_figure(lang: str, narrow: bool = False):
    path = params.ROOT / "output" / "tables" / "worker_busy.csv"
    if not path.exists():
        return
    t = MORE[lang]
    b = pd.read_csv(path)
    size = NARROW_FONT if narrow else 12
    fig, ax = plt.subplots(figsize=(NARROW_W, 4.2) if narrow else (10, 4.4))
    lines = []
    for scn, color, name in (("baseline", theme.RED, t["y2026"]),
                             (b["scenario"].unique()[-1], theme.BRONZE, t["plan"])):
        d = b[b["scenario"] == scn].sort_values("hour")
        ax.fill_between(d["hour"], 100 * d["lo"], 100 * d["hi"], color=color, alpha=0.2, lw=0)
        lines += ax.plot(d["hour"], 100 * d["med"], color=color, lw=2.6, marker="o", ms=4)
    step = 4 if narrow else 2
    hours = np.arange(13, 27, step)
    ax.set_xticks(hours)
    ax.set_xticklabels([f"{h % 24:02d}:00" for h in hours], fontsize=size)
    ax.set_ylim(0, 105)
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_yticklabels(["0%", "25%", "50%", "75%", "100%"], fontsize=size)
    ax.set_ylabel(t["busy_y"], fontsize=size)
    ax.grid(axis="y", lw=0.8)
    series_legend(ax, lines, [t["y2026"], t["plan"]], size if narrow else 12)
    ax.set_title(t["busy_title"], loc="left", pad=30, fontsize=size + 1 if narrow else 15)
    fig.savefig(out_name("summary_busy", lang, narrow), dpi=160, bbox_inches="tight")
    plt.close(fig)


def og_image(v: dict, lang: str):
    """1200 x 630 image for link previews: the before-and-after message in two panels."""
    import yaml
    text = yaml.safe_load((params.ROOT / "site" / "_text.yaml").read_text(encoding="utf-8"))
    raw = v["raw"]
    import math
    f = {"obs_from": raw["obs_from"], "obs_to": raw["obs_to"],
         "plan_wait": str(math.ceil(max(raw["plan_obs_median_min"], 1) - 1e-9))}

    def tx(key, **kw):
        return text[key][lang].format(**{**f, **kw})
    fig = plt.figure(figsize=(12, 6.3), dpi=100)
    fig.patch.set_facecolor(theme.PAPER)
    fig.text(0.05, 0.92, "Orus Fest", fontsize=22, fontweight="bold", color=theme.RED,
             va="center")
    fig.text(0.05, 0.84, tx("ba_title"), fontsize=26, fontweight="bold", color=theme.INK,
             va="center")
    staff_2026 = int(round(raw["ss_staff_2026"]))
    panels = [(0.05, tx("ba_2026"), tx("ba_wait_2026"), tx("ba_lines_2026"),
               tx("ba_staff_2026", n=staff_2026), theme.RED),
              (0.53, tx("ba_plan"), tx("ba_wait_plan"), tx("ba_lines_plan"),
               tx("ba_staff_plan", taps=raw["plan_taps"], sellers=raw["plan_sellers"]),
               theme.BRONZE)]
    for x0, label, wait, lines, staff, color in panels:
        fig.patches.append(patches.FancyBboxPatch((x0, 0.1), 0.42, 0.63,
                                                  boxstyle="round,pad=0.005,rounding_size=0.02",
                                                  transform=fig.transFigure, fill=False,
                                                  ec=color, lw=3))
        fig.text(x0 + 0.03, 0.65, label, fontsize=24, fontweight="bold", color=color)
        fig.text(x0 + 0.21, 0.48, wait, fontsize=42 if len(wait) > 8 else 64,
                 fontweight="bold", color=color, ha="center", va="center")
        fig.text(x0 + 0.21, 0.29, lines, fontsize=20, color=theme.INK, ha="center")
        fig.text(x0 + 0.21, 0.17, staff, fontsize=20, color=theme.MUTED, ha="center")
    fig.savefig(FIG / f"before_after_og_{lang}.png", dpi=100, facecolor=theme.PAPER)
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
            changes_figure(v, lang, narrow)
            mixes_figure(v, lang, narrow)
            busy_figure(lang, narrow)
        plan_figure(v, lang)
        og_image(v, lang)
    print("summary figures written to", FIG)


if __name__ == "__main__":
    main()
