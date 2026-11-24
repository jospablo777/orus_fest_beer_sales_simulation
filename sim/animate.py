"""Floor animations and static space views from recorded frames."""

from __future__ import annotations

import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib import animation, patches  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

from .model import (QUEUED, SERVICE, S_OFF, S_RESTOCKING, TO_QUEUE, W_CHARGING,  # noqa: E402
                     W_IDLE, W_OFF, W_POURING, WAIT_SELLER)
from .params import min_to_clock  # noqa: E402
from .venue import Venue  # noqa: E402
from . import theme  # noqa: E402
from .i18n import labels as i18n_labels  # noqa: E402

theme.apply()
ZONE_COLORS = theme.ZONES
C_CROWD = theme.DOT_CROWD
C_TO_LINE = theme.DOT_TO_LINE
C_CASH = theme.DOT_TICKET
C_POUR = theme.DOT_TAP
C_WAIT_SELLER = theme.DOT_WAIT_SELLER
C_SELLER = theme.DOT_SELLER
C_BG = theme.FLOOR
INK = theme.INK
C_COUNTER = "#2a9fbf"
C_BOOTH = theme.BLUE
C_COCKTAIL = "#8a7a3a"
C_TOILETS = "#7a7f8c"
# Bar workers: square markers behind the counter. Idle is hollow; charging and pouring are
# filled with a light and a mid tone, which also differ in grey scale. On the bar fill
# (about #1e373c) the contrast ratios are about 12:1 (charging) and 5.6:1 (pouring).
C_W_CHARGING = "#f4efe6"
C_W_POURING = "#d9a441"
C_REFILL_EDGE = "#d9a441"


def worker_style(states):
    """Face and edge colours (RGBA) of the bar worker markers. Workers off shift are hidden."""
    from matplotlib.colors import to_rgba
    face = np.zeros((len(states), 4))
    edge = np.tile(to_rgba(INK), (len(states), 1))
    face[states == W_CHARGING] = to_rgba(C_W_CHARGING)
    face[states == W_POURING] = to_rgba(C_W_POURING)
    edge[states == W_OFF] = (0, 0, 0, 0)
    return face, edge

DENSITY_CMAP = LinearSegmentedColormap.from_list("density", theme.DENSITY_STEPS)


def _fit_inside(ax, txt, box, margin=0.4, max_size=8.0, min_size=4.0):
    """Shrink a text until it fits inside a box of the hall (meters), margin on each side."""
    fig = ax.figure
    renderer = fig.canvas.get_renderer()
    ax.apply_aspect()
    txt.set_fontsize(max_size)
    w = box["x1"] - box["x0"] - 2 * margin
    h = box["y1"] - box["y0"] - 2 * margin
    while txt.get_fontsize() > min_size:
        bb = txt.get_window_extent(renderer).transformed(ax.transData.inverted())
        if abs(bb.width) <= w and abs(bb.height) <= h:
            break
        txt.set_fontsize(txt.get_fontsize() - 0.25)


def draw_venue(ax, cfg, points, labels=True, lang="en", booth_label=True):
    """Plan view of the hall. booth_label=False leaves the booth unlabeled, for figures that
    name it in their legend."""
    v = cfg["venue"]
    L = i18n_labels(lang)
    ax.set_facecolor(C_BG)
    ax.add_patch(patches.Rectangle((0, 0), v["width_m"], v["length_m"], fill=False,
                                   lw=1.5, ec=INK))
    names = {"stage": L["stage"], "bar_zone": L["bar_zone"], "tables": L["tables"],
             "vendors_west": L["vendors"], "vendors_east": L["vendors"]}
    for key, col in ZONE_COLORS.items():
        r = v[key]
        ax.add_patch(patches.Rectangle((r["x0"], r["y0"]), r["x1"] - r["x0"], r["y1"] - r["y0"],
                                       fc=col, alpha=0.2, ec=col, lw=0.8))
        if labels:
            rot = 90 if key.startswith("vendors") else 0
            ax.text((r["x0"] + r["x1"]) / 2, (r["y0"] + r["y1"]) / 2 + (2.6 if key == "bar_zone"
                                                                        else 0),
                    names[key], ha="center", va="center", fontsize=8, color=col,
                    rotation=rot, alpha=0.9, fontweight="bold")
    venue = Venue(cfg)
    if v.get("toilets"):
        r = v["toilets"]
        ax.add_patch(patches.Rectangle((r["x0"], r["y0"]), r["x1"] - r["x0"], r["y1"] - r["y0"],
                                       fc=C_TOILETS, alpha=0.35, ec=C_TOILETS, lw=0.8, zorder=2))
        if labels:
            ax.text((r["x0"] + r["x1"]) / 2, (r["y0"] + r["y1"]) / 2, L["toilets"], ha="center",
                    va="center", fontsize=8, color=INK, rotation=90, fontweight="bold", zorder=2)
    if v.get("booth"):
        r = v["booth"]
        ax.add_patch(patches.Rectangle((r["x0"], r["y0"]), r["x1"] - r["x0"], r["y1"] - r["y0"],
                                       fc=C_BOOTH, alpha=0.35, ec=C_BOOTH, lw=0.8, zorder=2))
        booth_text = None
        if labels and booth_label:
            booth_text = ax.text((r["x0"] + r["x1"]) / 2, (r["y0"] + r["y1"]) / 2,
                                 textwrap.fill(L["booth"], 12), ha="center", va="center",
                                 color=INK, zorder=2, linespacing=1.1)
    if v.get("cocktail_line"):
        r = venue.cocktail_strip()
        ax.add_patch(patches.Rectangle((r["x0"], r["y0"]), r["x1"] - r["x0"], r["y1"] - r["y0"],
                                       fc=C_COCKTAIL, alpha=0.45, ec="none", zorder=2))
        if labels:
            ax.text((r["x0"] + r["x1"]) / 2, (r["y0"] + r["y1"]) / 2, L["cocktail_line"],
                    ha="center", va="center", fontsize=6, color=INK, rotation=90, zorder=2)
    ax.plot([v["bar_zone"]["x0"], v["bar_zone"]["x1"]], [v["counter_y"]] * 2, color=C_COUNTER,
            lw=2.2, alpha=0.9)
    for kind, x, y in points:
        style = {"cash": ("s", C_CASH), "pour": ("v", C_COUNTER), "direct": ("v", C_COUNTER)}
        m, c = style[kind]
        ax.plot(x, y + 0.2, marker=m, ms=6, color=c, mec=theme.PAPER, mew=0.6, zorder=5)
    e = v["entrance"]
    left = e["x"] < v["width_m"] / 2
    ax.plot([0 if left else v["width_m"]] * 2, [e["y"] - 1.0, e["y"] + 1.0], color=C_SELLER,
            lw=3, solid_capstyle="butt", zorder=4)
    ax.annotate(L["entrance"], (e["x"], e["y"]), (e["x"] + (1 if left else -1), e["y"] - 1.2),
                fontsize=7, color=INK, ha="left" if left else "right")
    ax.set_xlim(-0.5, v["width_m"] + 0.5)
    ax.set_ylim(v["length_m"] + 0.5, -0.5)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    if v.get("booth") and labels and booth_label:
        _fit_inside(ax, booth_text, v["booth"])


def _colors(frame):
    st = frame["state"]
    kind = frame["kind"]
    col = np.full(st.size, C_CROWD, dtype=object)
    col[st == TO_QUEUE] = C_TO_LINE
    inline = (st == QUEUED) | (st == SERVICE)
    col[inline & (kind == "cash")] = C_CASH
    col[inline & (kind != "cash")] = C_POUR
    col[st == WAIT_SELLER] = C_WAIT_SELLER
    size = np.where(col == C_CROWD, 5.0, 9.0)
    return col, size


def rolling_wait(txn, t_grid_clock, window_min=15):
    """Median time in line among people who left a line in the last window_min minutes."""
    if len(txn) == 0:
        return np.full(len(t_grid_clock), np.nan)
    served = txn["clock_served_min"].to_numpy()
    line = txn["line_min"].to_numpy()
    out = np.full(len(t_grid_clock), np.nan)
    for k, c in enumerate(t_grid_clock):
        m = (served > c - window_min) & (served <= c)
        if m.sum() >= 3:
            out[k] = np.median(line[m])
    return out


def _phone_layout(L, titles):
    """Phone cut: the two floor panels and their readouts, the clock above and the colour key
    below. Drawn 720 px wide; on a phone it is shown about 360 px wide."""
    # The bottom 18% of the frame stays empty for the video controls of a phone browser.
    fig = plt.figure(figsize=(7.2, 11.2))
    gs = fig.add_gridspec(1, 2, left=0.02, right=0.98, top=0.865, bottom=0.40, wspace=0.06)
    floor_axes = [fig.add_subplot(gs[0, j]) for j in range(2)]
    title = fig.text(0.03, 0.985, "", fontsize=18, fontweight="bold", color=INK, va="top")
    return fig, floor_axes, [], title, {"panel_title": 14, "wrap": 22, "info": 14,
                                        "info_y": -0.012, "legend": dict(
                                            loc="upper left", bbox_to_anchor=(0.03, 0.262),
                                            ncol=2, fontsize=12, columnspacing=1.0,
                                            handletextpad=0.3, labelspacing=0.35),
                                        "info_lines": 3, "bitrate": 2000, "worker_size": 22}


def _wide_layout(L, titles):
    # The bottom 10% of the frame stays empty: a browser draws its video controls there.
    fig = plt.figure(figsize=(16, 10))
    gs = fig.add_gridspec(3, 3, width_ratios=[1, 1, 1.35], left=0.02, right=0.97,
                          top=0.82, bottom=0.208, wspace=0.08, hspace=0.55)
    floor_axes = [fig.add_subplot(gs[:, 0]), fig.add_subplot(gs[:, 1])]
    ts_axes = [fig.add_subplot(gs[i, 2]) for i in range(3)]
    title = fig.text(0.02, 0.966, "", fontsize=21, fontweight="bold", color=INK, va="top")
    fig.text(0.02, 0.9145, L["dot_note"], fontsize=12.5, color=theme.MUTED, va="top")
    return fig, floor_axes, ts_axes, title, {"panel_title": 13, "wrap": 30, "info": 12,
                                             "info_y": -0.015, "legend": dict(
                                                 loc="upper left", bbox_to_anchor=(0.37, 0.985),
                                                 ncol=4, fontsize=11.5, columnspacing=1.0,
                                                 handletextpad=0.3, labelspacing=0.3),
                                             "info_lines": 2, "worker_size": 30,
                                             "order": [0, 10, 1, 2, 3, 4, 5, 6, 7, 8, 9]}


def side_by_side(runs, cfgs, titles, path, fps=20, dpi=120, lang="en", still_only=False,
                 still_at=None, layout="wide"):
    """runs: list of two result dicts with frames recorded over the same window.
    Writes the video and a still image with the same name and the suffix .jpg. The still is
    the frame nearest the clock time still_at ("HH:MM"), or the frame with the longest 2026
    lines when still_at is None. With still_only the video is skipped, which is enough to
    check the layout. layout "wide" shows the floor panels and three charts; "phone" shows
    only the floor panels and their readouts."""
    L = i18n_labels(lang)
    fa, fb = runs[0]["frames"], runs[1]["frames"]
    n = min(len(fa), len(fb))
    t0_min = runs[0]["series"]["clock_min"].iloc[0] - runs[0]["series"]["t_min"].iloc[0]
    clocks = np.array([t0_min + f["t"] / 60 for f in fa[:n]])

    build = _phone_layout if layout == "phone" else _wide_layout
    fig, floor_axes, ts_axes, title, look = build(L, titles)

    scat, sell, info, work = [], [], [], []
    for ax, run, cfg, ttl in zip(floor_axes, runs, cfgs, titles):
        draw_venue(ax, cfg, run["points"], lang=lang, booth_label=False)
        ax.set_title(textwrap.fill(ttl, look["wrap"]), fontsize=look["panel_title"], color=INK,
                     fontweight="bold", pad=6)
        scat.append(ax.scatter([], [], s=5, lw=0, zorder=3))
        sell.append(ax.scatter([], [], s=70, c=C_SELLER, marker="o", edgecolors=INK,
                               linewidths=0.9, zorder=6))
        work.append(ax.scatter([], [], s=look["worker_size"], marker="s", linewidths=1.2,
                               zorder=5))
        info.append(ax.text(0.5, look["info_y"], "", transform=ax.transAxes, ha="center",
                            va="top", fontsize=look["info"], color=INK, linespacing=1.5))

    legend = [(L["watching"], C_CROWD), (L["to_line"], C_TO_LINE),
              (L["ticket_line"], C_CASH), (L["tap_line"], C_POUR),
              (L["wait_seller"], C_WAIT_SELLER), (L["seller"], C_SELLER)]
    handles = [Line2D([], [], ls="", marker="o", ms=8, color=col) for _, col in legend]
    labels_ = [lab for lab, _ in legend]
    handles += [Line2D([], [], ls="", marker="o", ms=9, color=C_SELLER, mec=C_REFILL_EDGE,
                       mew=2.4),
                Line2D([], [], ls="", marker="s", ms=8, mfc="none", mec=INK, mew=1.2),
                Line2D([], [], ls="", marker="s", ms=8, mfc=C_W_CHARGING, mec=INK, mew=1.2),
                Line2D([], [], ls="", marker="s", ms=8, mfc=C_W_POURING, mec=INK, mew=1.2),
                Line2D([], [], ls="", marker="s", ms=10, color=C_BOOTH, alpha=0.6)]
    labels_ += [L["s_refill"], L["w_idle"], L["w_charging"], L["w_pouring"], L["booth"]]
    if "order" in look:              # columns are filled top to bottom; long labels share one
        handles = [handles[k] for k in look["order"]]
        labels_ = [labels_[k] for k in look["order"]]
    fig.legend(handles, labels_, frameon=False, labelcolor=INK, **look["legend"])

    palette = [theme.RED, theme.BRONZE]
    series_spec = [("occupancy", L["people_inside"]), ("in_lines_total", L["people_in_lines"]),
                   (None, L["wait_last15"])]
    markers = []
    waits = []
    for run in runs:
        waits.append(rolling_wait(run["txn"][run["txn"]["channel"] != "seller"]
                                  if len(run["txn"]) else run["txn"], clocks))
    for ax, (col, lab) in zip(ts_axes, series_spec):
        for j, run in enumerate(runs):
            s = run["series"]
            m = (s["clock_min"] >= clocks[0]) & (s["clock_min"] <= clocks[-1])
            if col:
                ax.plot(s.loc[m, "clock_min"], s.loc[m, col], color=palette[j], lw=1.8,
                        label=titles[j])
            else:
                ax.plot(clocks, waits[j], color=palette[j], lw=1.8, label=titles[j])
        ax.set_title(lab, fontsize=13, loc="left", color=INK)
        ax.grid(alpha=0.8)
        ax.spines[["top", "right"]].set_visible(False)
        tick_step = 60 if clocks[-1] - clocks[0] > 150 else 10
        ticks = np.arange(np.ceil(clocks[0] / tick_step) * tick_step, clocks[-1] + 1, tick_step)
        ax.set_xticks(ticks)
        ax.set_xticklabels([min_to_clock(x) for x in ticks], fontsize=11)
        ax.tick_params(axis="y", labelsize=11)
        markers.append(ax.axvline(clocks[0], color=INK, lw=1.0, alpha=0.5))
    if ts_axes:
        ts_axes[-1].legend(fontsize=12, frameon=False, loc="upper left", ncol=1,
                           bbox_to_anchor=(0.0, -0.22), handlelength=2.5)
    sched = runs[0]["series"].set_index("clock_min")["act"]

    def update(k):
        c = clocks[k]
        act = sched.iloc[np.argmin(np.abs(sched.index.to_numpy() - c))]
        title.set_text(f"{min_to_clock(c)}   ·   {act}")
        for j, frames in enumerate((fa, fb)):
            f = frames[k]
            col, size = _colors(f)
            scat[j].set_offsets(np.c_[f["x"], f["y"]])
            scat[j].set_color(col)
            scat[j].set_sizes(size)
            on = f["s_state"] != S_OFF
            sell[j].set_offsets(np.c_[f["sx"][on], f["sy"][on]] if on.any()
                                else np.empty((0, 2)))
            refill = f["s_state"][on] == S_RESTOCKING
            sell[j].set_edgecolors([C_REFILL_EDGE if r else INK for r in refill])
            sell[j].set_linewidths(np.where(refill, 2.4, 0.9))
            ws = f["w_state"]
            work[j].set_offsets(np.c_[f["wx"], f["wy"]])
            face, edge = worker_style(ws)
            work[j].set_facecolors(face)
            work[j].set_edgecolors(edge)
            staffed = int((ws != W_OFF).sum())
            busy = int(((ws == W_CHARGING) | (ws == W_POURING)).sum())
            busy_txt = L["busy_at_bar"].format(b=busy, n=staffed)
            n_line = int(np.isin(f["state"], [QUEUED, SERVICE]).sum())
            w = waits[j][k]
            beers = runs[j]["series"]
            b = beers.loc[(beers["clock_min"] - c).abs().idxmin(), "beers_total"]
            if look["info_lines"] == 3:
                wtxt = (f"\n{L['wait']} {w:.0f} {L['minutes']}" if np.isfinite(w) else "\n")
            else:
                wtxt = f"  ·  {L['wait']} {w:.0f} {L['minutes']}" if np.isfinite(w) else ""
            info[j].set_text(f"{n_line} {L['in_lines']}{wtxt}\n{b:,} {L['beers_sold']}"
                             f"\n{busy_txt}")
        for mk in markers:
            mk.set_xdata([c, c])
        return []

    if not still_only:
        anim = animation.FuncAnimation(fig, update, frames=n, interval=1000 / fps, blit=False)
        writer = animation.FFMpegWriter(fps=fps, codec="libx264",
                                        bitrate=look.get("bitrate", 4000),
                                        extra_args=["-preset", "veryfast", "-pix_fmt", "yuv420p"])
        anim.save(path, writer=writer, dpi=dpi)
    if still_at:
        from .params import clock_to_min
        update(int(np.argmin(np.abs(clocks - clock_to_min(still_at)))))
    else:
        in_line = [int(np.isin(f["state"], [QUEUED, SERVICE]).sum()) for f in fa[:n]]
        update(int(np.argmax(in_line)))
    fig.savefig(Path(path).with_suffix(".jpg"), dpi=dpi, pil_kwargs={"quality": 85})
    plt.close(fig)


def density_views(runs, cfgs, titles, path, window=("21:30", "23:30"), dpi=150, lang="en"):
    """Mean density (people per m2) per cell over a time window, one panel per run."""
    from .params import clock_to_min
    lo, hi = clock_to_min(window[0]), clock_to_min(window[1])
    fig, axes = plt.subplots(1, len(runs), figsize=(5.2 * len(runs), 8.2))
    vmax = 4.0
    for ax, run, cfg, ttl in zip(np.atleast_1d(axes), runs, cfgs, titles):
        t0 = run["series"]["clock_min"].iloc[0] - run["series"]["t_min"].iloc[0]
        sel = [f["rho"] for f in run["frames"] if lo <= t0 + f["t"] / 60 <= hi]
        mean = np.mean(sel, axis=0)
        mean = np.where(mean > 0.02, mean, np.nan)     # leave empty cells transparent
        draw_venue(ax, cfg, run["points"], labels=True, lang=lang)
        im = ax.imshow(mean, origin="upper", extent=(0, mean.shape[1], mean.shape[0], 0),
                       cmap=DENSITY_CMAP, vmin=0, vmax=vmax, interpolation="nearest",
                       alpha=0.9, zorder=0.5)
        ax.set_title(textwrap.fill(ttl, 28), fontsize=11.5, fontweight="bold", color=INK)
    cb = fig.colorbar(im, ax=axes, shrink=0.55, pad=0.02)
    cb.set_label(f"{i18n_labels(lang)['density_label']} {window[0]}–{window[1]}")
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)


def render_clip(job) -> str:
    """One video job, run in a worker process: simulate the 2026 setup and another setup
    over one clip and render the video in one language.

    job: (clip name, clip settings, language, scenario, draw or None, still_only, tables).
    The default draw is the posterior draw whose exchange-line wait is closest to the
    posterior median. The job with tables=True also writes the series and the transactions
    of the night clip."""
    import time

    import pandas as pd

    from . import experiments as ex
    from . import params
    from . import scenarios as sc
    from .model import Simulation

    clip_name, clip, lang, scenario, draw, still, tables = job
    runs_dir = params.ROOT / "output" / "runs"
    post = pd.read_csv(runs_dir / "posterior_draws.csv")
    if draw is None:
        target = post["obs_exchange_median_min"].median()
        row = post.iloc[(post["obs_exchange_median_min"] - target).abs().argmin()]
    else:
        row = post[post["draw"] == draw].iloc[0]
    priors = ex.load_calibration()["priors"]
    scen = sc.load()
    cfg_a = ex.draw_config(params.load(), row[[c for c in post.columns if c in priors]], priors)
    cfg_b = sc.apply(cfg_a, scen[scenario])
    seed = 70_000 + int(row["draw"])
    t0 = time.time()
    runs = [Simulation(c, seed=seed, record_frames=True, frame_every_s=clip["every_s"],
                       frame_window=clip["window"]).run() for c in (cfg_a, cfg_b)]
    L = i18n_labels(lang)
    titles = [L["setup_2026"], L["setup_plan"] if scenario == "plan" else scen[scenario]["label"]]
    out = params.ROOT / "output"
    (out / "animations").mkdir(parents=True, exist_ok=True)
    (out / "figures").mkdir(parents=True, exist_ok=True)
    for layout, suffix, dpi in (("wide", "", 120), ("phone", "_phone", 100)):
        side_by_side(runs, [cfg_a, cfg_b], titles,
                     out / "animations" / f"{clip_name}_2026_vs_{scenario}{suffix}_{lang}.mp4",
                     fps=clip["fps"], dpi=dpi, lang=lang, still_only=still,
                     still_at=clip.get("still"), layout=layout)
    if clip_name == "night" and not still:
        density_views(runs, [cfg_a, cfg_b], titles,
                      out / "figures" / f"density_2026_vs_{scenario}_{lang}.png", lang=lang)
        if tables:
            for name, run in zip(("baseline", scenario), runs):
                run["series"].to_csv(runs_dir / f"anim_series_{name}.csv", index=False)
                run["txn"].to_csv(runs_dir / f"anim_txn_{name}.csv", index=False)
    return f"{clip_name} {lang}: draw {int(row['draw'])}, done in {time.time() - t0:.0f} s"
