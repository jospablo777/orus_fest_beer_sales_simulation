"""Agent-based model of attendance and beer sales on the hall floor.

Clock: seconds after doors open. One step moves walkers with a density-dependent speed,
draws thirst events, runs every service point and roaming seller, and records summaries.
"""

from __future__ import annotations

from collections import deque

import numpy as np
from scipy.ndimage import uniform_filter

from .params import clock_to_min
from .venue import Venue, weidmann_speed

NOT_ARRIVED, TO_SPOT, WATCH, TO_QUEUE, QUEUED, SERVICE, WAIT_SELLER, TO_EXIT, GONE = range(9)
STATE_NAMES = ["not_arrived", "to_spot", "watch", "to_queue", "queued", "service",
               "wait_seller", "to_exit", "gone"]

S_PATROL, S_TO_CUSTOMER, S_SERVING, S_TO_RESTOCK, S_RESTOCKING, S_OFF = range(6)
# States of the people behind the bar (W_*) and of the sellers as reported (SELLER_STATES).
W_OFF, W_IDLE, W_CHARGING, W_POURING, W_STOCKING = range(5)
WORKER_STATES = ["off", "idle", "charging", "pouring", "stocking"]
SELLER_STATES = ["off", "walking", "selling", "to_refill", "refilling"]
SELLER_REPORT = {S_OFF: 0, S_PATROL: 1, S_TO_CUSTOMER: 1, S_SERVING: 2, S_TO_RESTOCK: 3,
                 S_RESTOCKING: 4}
NO_FRIENDS = np.empty(0, int)


def _lognormal(rng, mean, cv, size=None):
    sigma = np.sqrt(np.log1p(cv ** 2))
    mu = np.log(mean) - sigma ** 2 / 2
    return rng.lognormal(mu, sigma, size)


class Schedule:
    """Bands drive crowd behaviour; DJ sets between bands count as changeovers."""

    def __init__(self, cfg, t0_min):
        acts = cfg["schedule"]
        to_s = lambda hhmm: (clock_to_min(hhmm) - t0_min) * 60.0  # noqa: E731
        self.all_names = [a["act"] for a in acts]
        self.all_start = np.array([to_s(a["start"]) for a in acts])
        self.all_end = np.array([to_s(a["end"]) for a in acts])
        bands = [a for a in acts if a.get("kind", "band") == "band"]
        self.names = [a["act"] for a in bands]
        self.start = np.array([to_s(a["start"]) for a in bands])
        self.end = np.array([to_s(a["end"]) for a in bands])
        self.fans = np.array([a["fans"] for a in bands], float)
        pop = cfg.get("popularity", {})
        if pop.get("use_followers"):
            anchor = next(a for a in bands if a["act"] == pop["anchor_band"])
            for k, a in enumerate(bands):
                if a.get("ig_followers"):
                    ratio = a["ig_followers"] / anchor["ig_followers"]
                    self.fans[k] = min(anchor["fans"] * ratio ** pop["elasticity"], 0.95)

    def phase(self, t):
        """(index of band playing or -1, fan share of that band or 0)."""
        k = np.flatnonzero((self.start <= t) & (t < self.end))
        if k.size:
            return int(k[0]), float(self.fans[k[0]])
        return -1, 0.0

    def focus(self, t):
        """(band playing or -1, band the crowd is oriented to: the one playing, or between
        bands the next one, or -1 after the last band)."""
        k, _ = self.phase(t)
        if k >= 0:
            return k, k
        nxt = np.flatnonzero(self.start > t)
        return -1, int(nxt[0]) if nxt.size else -1

    def label(self, t):
        k = np.flatnonzero((self.all_start <= t) & (t < self.all_end))
        return self.all_names[k[0]] if k.size else "doors / closing"


class Simulation:
    def __init__(self, cfg: dict, seed: int = 0, record_frames: bool = False,
                 frame_every_s: float = 60.0, frame_window: tuple[str, str] | None = None):
        self.cfg = cfg
        self.rng = np.random.default_rng(seed)
        self.venue = Venue(cfg)
        self.dt = float(cfg["event"]["dt_s"])
        self.t0_min = clock_to_min(cfg["event"]["doors_open"])
        self.t_end = (clock_to_min(cfg["event"]["close"]) - self.t0_min) * 60.0
        self.sched = Schedule(cfg, self.t0_min)
        self.points = self.venue.build_service_points(cfg, self.t0_min)
        self.record_frames = record_frames
        self.frame_every = frame_every_s
        if frame_window:
            self.frame_t0 = (clock_to_min(frame_window[0]) - self.t0_min) * 60
            self.frame_t1 = (clock_to_min(frame_window[1]) - self.t0_min) * 60
        else:
            self.frame_t0, self.frame_t1 = 0.0, self.t_end
        self.afternoon_end = (clock_to_min(cfg["crowd"]["afternoon_end"]) - self.t0_min) * 60
        self._init_agents()
        self._init_sellers()

    # ------------------------------------------------------------------ setup

    def _init_agents(self):
        c = self.cfg["crowd"]
        rng = self.rng
        n = int(c["n_total"])
        self.n = n
        # Each attendee comes for one core act, drawn with weight fans_k ** core_power, and
        # stays for a Poisson number of acts before and after it. Inside that window they
        # follow the core act and each other act k with probability fans_k. Arrival is before
        # the first act of the window, departure after the last one. Nobody re-enters.
        n_acts = len(self.sched.names)
        w = self.sched.fans ** c["core_power"]
        core = rng.choice(n_acts, size=n, p=w / w.sum())
        first = np.clip(core - rng.poisson(c["acts_before_mean"], n), 0, n_acts - 1)
        last = np.clip(core + rng.poisson(c["acts_after_mean"], n), 0, n_acts - 1)
        # whole-event attendees stay through the last band; their arrival follows the window
        whole = rng.random(n) < c["whole_event_share"]
        last = np.where(whole, n_acts - 1, last)
        # Friends: attendees with the same core act and window form groups of mean size
        # group_size_mean. A group shares its window, arrival and departure. One member
        # buys for the friends who also want a beer (see _collect_round).
        sizes = np.minimum(1 + rng.poisson(max(c.get("group_size_mean", 1.0) - 1.0, 0.0), n), 6)
        n_groups = int(np.searchsorted(np.cumsum(sizes), n) + 1)
        gid_sorted = np.repeat(np.arange(n_groups), sizes[:n_groups])[:n]
        key = np.lexsort((last, first, core))
        group = np.empty(n, int)
        group[key] = gid_sorted
        leader = key[np.searchsorted(gid_sorted, np.arange(n_groups))]
        core, first, last = core[leader][group], first[leader][group], last[leader][group]

        idx = np.arange(n_acts)[None, :]
        window = (idx >= first[:, None]) & (idx <= last[:, None])
        fan = window & (rng.random((n, n_acts)) < self.sched.fans[None, :])
        fan[np.arange(n), core] = True
        lead = (rng.uniform(*c["arrival_lead_min"], n_groups) * 60)[group]
        lag = (rng.uniform(*c["leave_lag_min"], n_groups) * 60)[group]
        arr = np.clip(self.sched.start[first] - lead, 0.0, self.t_end)
        leave = np.clip(self.sched.end[last] + lag, 0.0, self.t_end)
        # some groups that saw the last band stay for the closing DJ sets
        stays = (rng.random(n_groups) < c["close_stay_share"])[group]
        close_t = rng.uniform(self.sched.end[-1], self.t_end, n_groups)[group]
        leave = np.where((last == n_acts - 1) & stays, close_t, leave)
        order = np.argsort(arr, kind="stable")
        self.arrival = arr[order]
        self.leave = leave[order]
        self.fan = fan[order]
        self.core = core[order]
        self.group = group[order]
        by_group = np.argsort(self.group, kind="stable")
        cuts = np.flatnonzero(np.diff(self.group[by_group])) + 1
        self.members = dict(zip(self.group[by_group][np.r_[0, cuts]].tolist(),
                                np.split(by_group, cuts)))

        self.drinker = rng.random(n) < c["drinker_share"]
        # crowd.rtd_share: attendees who buy ready-to-drink cans and no beer, taken from the
        # attendees who do not drink beer (no draw when the share is 0)
        rtd_share = float(c.get("rtd_share", 0.0) or 0.0)
        self.rtd = (~self.drinker & (rng.random(n) < rtd_share / max(1 - c["drinker_share"], 1e-9))
                    if rtd_share else np.zeros(n, bool))
        self.rtd_units = np.zeros(n, int)
        self.rate = _lognormal(rng, c["rate_mean_per_h"], c["rate_cv"], n) / 3600.0
        self.patience = rng.lognormal(np.log(c["patience_median_min"] * 60),
                                      c["patience_sd_log"], n)
        b = self.cfg["bar"]
        self.tickets = np.zeros(n, int)
        if b["mode"] == "ticket" and b["presale_fraction"] > 0:
            pre = rng.random(n) < b["presale_fraction"]
            self.tickets[pre] = b["presale_tickets"]

        self.state = np.full(n, NOT_ARRIVED, np.int8)
        self.x = np.full(n, self.venue.entrance[0])
        self.y = np.full(n, self.venue.entrance[1])
        self.tx = self.x.copy()
        self.ty = self.y.copy()
        self.target_q = np.full(n, -1, int)       # service point index while walking/queued
        self.next_eligible = np.zeros(n)
        self.want_t = np.full(n, np.nan)
        self.join_t = np.full(n, np.nan)
        self.q_enter = np.zeros(n)                # time of joining the current line
        self.via_cash = np.zeros(n, bool)         # current purchase started at a ticket cashier
        self.orders = {}                          # buyer -> friends included in the purchase
        self.ordered_by = np.full(n, -1, int)     # friend -> buyer who is getting their beer
        self.wait_start = np.full(n, np.nan)
        self.claimed = np.full(n, -1, int)
        self.skip_sellers = np.zeros(n, bool)
        self.beers = np.zeros(n, int)
        self.next_arrival = 0

        # (t_want, t_join, t_served, channel, beers, agent, via_cashier, t_line, line_kind)
        # t_join is the time of joining the first line of the visit; t_line the time of
        # joining the line in which the visit ended, of kind line_kind.
        self.txn = []
        self.balks = 0
        self.balk_t = []              # time of each decision not to join a line
        self.reneges = 0
        self.seller_giveups = 0

    def _init_sellers(self):
        s = self.cfg["sellers"]
        k = int(s["n"])
        self.k = k
        self.s_start = (clock_to_min(s["start"]) - self.t0_min) * 60
        self.s_end = (clock_to_min(s["end"]) - self.t0_min) * 60
        # sellers.shifts adds sellers with their own start and end; sellers.restock_extra adds
        # refill points away from the bar (each with a runner, counted in staff.extra)
        starts, ends = [self.s_start] * k, [self.s_end] * k
        for sh in s.get("shifts") or []:
            n_sh = int(sh["n"])
            starts += [(clock_to_min(sh["start"]) - self.t0_min) * 60] * n_sh
            ends += [(clock_to_min(sh["end"]) - self.t0_min) * 60] * n_sh
        k = len(starts)
        self.k = k
        self.s_start_i, self.s_end_i = np.array(starts, float), np.array(ends, float)
        extra = [[r["x"], r["y"]] for r in s.get("restock_extra") or []]
        self.restock = (np.vstack([self.venue.restock_points, extra]) if extra
                        else self.venue.restock_points)
        base = self.venue.restock_points[np.arange(k) % 2] if k else np.zeros((0, 2))
        self.sx = base[:, 0].copy()
        self.sy = base[:, 1].copy()
        self.stx = self.sx.copy()
        self.sty = self.sy.copy()
        self.s_state = np.full(k, S_OFF, np.int8)
        self.s_stock = np.full(k, int(s["capacity"]))
        self.s_busy = np.zeros(k)
        self.s_cust = np.full(k, -1, int)
        self.s_sold = np.zeros(k, int)

    # ------------------------------------------------------------------ helpers

    def _present_mask(self):
        return (self.state != NOT_ARRIVED) & (self.state != GONE)

    def _density(self):
        idx = self.venue.cell_index(self.x[self.present], self.y[self.present])
        counts = np.bincount(idx, minlength=self.venue.nx * self.venue.ny).astype(float)
        self.counts = counts
        grid = counts.reshape(self.venue.ny, self.venue.nx)
        self.rho = uniform_filter(grid, size=3, mode="constant").ravel()

    def _send_to_spot(self, ids):
        if len(ids) == 0:
            return
        ids = np.asarray(ids)
        # people at a spot count where they stand; people walking to one count at the target
        st = self.state
        standing = np.flatnonzero((st == WATCH) | (st == WAIT_SELLER) | (st == QUEUED)
                                  | (st == SERVICE))
        heading = np.flatnonzero(st == TO_SPOT)
        n_cells = self.venue.nx * self.venue.ny
        occupied = (np.bincount(self.venue.cell_index(self.x[standing], self.y[standing]),
                                minlength=n_cells)
                    + np.bincount(self.venue.cell_index(self.tx[heading], self.ty[heading]),
                                  minlength=n_cells))
        front = self._front_group(ids)
        for grp, w in ((front, self.w_front), (~front, self.w_back)):
            if grp.any():
                x, y = self.venue.sample_spots(self.rng, int(grp.sum()), w, occupied)
                self.tx[ids[grp]], self.ty[ids[grp]] = x, y
                np.add.at(occupied, self.venue.cell_index(x, y), 1)
        self.state[ids] = TO_SPOT
        self.target_q[ids] = -1

    def _front_group(self, ids):
        """True for attendees who follow the act the crowd is oriented to right now."""
        if self.focus_k < 0:
            return np.zeros(len(ids), bool)
        return self.fan[ids, self.focus_k]

    def _service_time(self, kind, beers, rtd=False):
        """Seconds of one visit. Also sets self._split = (charging, pouring) seconds; the
        ticket window only charges, the 2026 exchange lines only pour."""
        b = self.cfg["bar"]
        cv = b["service_cv"]
        if kind == "cash":
            out = _lognormal(self.rng, b["s_cash_mean_s"], cv)
            self._split = (out, 0.0)
        else:
            # each beer after the first takes extra_beer_factor of the time of the first
            units = 1.0 + b.get("extra_beer_factor", 1.0) * (beers - 1)
            mean = b["s_pour_mean_s"] * units
            if rtd and not b.get("rtd_poured", False):   # ready-to-drink cans handed closed
                mean = b["s_rtd_s"] * units
            # Serving options that skip opening and pouring (cans, draft beer) save a fixed
            # time per beer; at most three quarters of the serving time can be saved.
            saving = b.get("pour_saving_s", 0.0) * beers
            if saving:
                mean = max(mean - saving, 0.25 * mean)
            out = _lognormal(self.rng, mean, cv / np.sqrt(units))
            self._split = (0.0, out)
            if kind == "direct":
                pay = _lognormal(self.rng, b["s_pay_direct_s"], cv)
                self._split = (pay, out)
                out += pay
        # people judge a line by how long recent visits took at that kind of station
        self.visit_s[kind] = 0.95 * self.visit_s[kind] + 0.05 * out
        return out

    def _add_busy(self, start, charge, pour, pay_first):
        """Adds one service to the busy seconds of the bar workers, by clock hour."""
        a = start
        for name, d in ((("charging", charge), ("pouring", pour)) if pay_first
                        else (("pouring", pour), ("charging", charge))):
            self._spread(self.w_busy[name], a, a + d)
            a += d

    def _spread(self, hours, a, b, weight=1.0):
        """Adds weight times the seconds of [a, b) (seconds after doors) to an array of clock
        hours."""
        h0 = self.t0_min * 60
        while a < b:
            h = int((h0 + a) // 3600)
            edge = min(b, (h + 1) * 3600 - h0)
            k = h - self.hour0
            if 0 <= k < len(hours):
                hours[k] += weight * (edge - a)
            a = edge

    def worker_states(self, t):
        """Position and state of every bar worker at time t (W_OFF, W_IDLE, W_CHARGING,
        W_POURING). A worker stands behind the counter at the x of the station, with the
        sideways offset of a point with several servers; at a satellite bar, behind it."""
        pay_first = self.cfg["bar"].get("pay_first", True)
        first, second = (W_CHARGING, W_POURING) if pay_first else (W_POURING, W_CHARGING)
        wx, wy, ws = [], [], []
        cy = self.cfg["venue"]["counter_y"]
        for p in self.points:
            busy = {e[2]: e for e in p.serving}
            for m in range(p.servers):
                off = (m - (p.servers - 1) / 2) * 0.8
                if p.server_x:
                    wx.append(p.server_x[m])
                    wy.append(cy + 1.0)
                elif p.label == "satellite":
                    wx.append(p.x + (1.0 if p.x > self.venue.W / 2 else -1.0))
                    wy.append(p.y + off)
                else:
                    wx.append(p.x + off)
                    wy.append(cy + 1.0)
                if not p.is_open(t):
                    ws.append(W_OFF)
                elif m in busy:
                    e = busy[m]
                    if e[0] < 0:
                        ws.append(W_STOCKING)
                    elif p.kind == "cash":
                        ws.append(W_CHARGING)
                    elif p.kind == "pour":
                        ws.append(W_POURING)
                    else:
                        ws.append(first if t < e[3] else second)
                else:
                    ws.append(W_IDLE)
        return np.array(wx, float), np.array(wy, float), np.array(ws, np.int8)

    def _account(self, t):
        """Staffed seconds of the bar workers and seconds of the sellers in each state, by
        clock hour."""
        for p in self.points:
            if p.is_open(t):
                self._spread(self.w_staffed, t, t + self.dt, p.servers)
        if self.k:
            for st in self.s_state:
                r = SELLER_REPORT[int(st)]
                if r:
                    self.s_time[r] += self.dt

    def _prepour_spans(self):
        """Pre-pour windows in seconds after doors: from bar.prepour.lead_min before the end
        of each set that ends at 18:00 or later until the next set starts."""
        pp = self.cfg["bar"]["prepour"]
        from_t = (clock_to_min(pp.get("from", "18:00")) - self.t0_min) * 60
        st, en = self.sched.start, self.sched.end
        out = []
        for k in range(len(en)):
            if en[k] < from_t:
                continue
            nxt = st[k + 1] if k + 1 < len(st) else en[k]
            out.append((en[k] - pp["lead_min"] * 60, max(nxt, en[k])))
        return out

    def _adjust_split(self, p, t, beers):
        """Changes to a station visit from the options study, applied to self._split after the
        draws: stocked cups, a menu with more choices and pooled lines. Returns the visit."""
        b = self.cfg["bar"]
        charge, pour = self._split
        if self._prepour and pour > 0:
            pp = b["prepour"]
            fresh = pp["fresh_min"] * 60
            while p.stock and t - p.stock[0] > fresh:   # too old: thrown away
                p.stock.popleft()
                self.cups_discarded += 1
            f = b.get("extra_beer_factor", 1.0)
            units = 1.0 + f * (beers - 1)
            used = min(len(p.stock), beers)
            if used:
                for _ in range(used):
                    p.stock.popleft()
                self.cups_used += used
                share = (1.0 + f * (used - 1)) / units
                pour *= 1.0 - (1.0 - pp["handover_share"]) * share
        charge += self._menu_s
        if p.pooled:
            m = b.get("pool_service_mult", 1.0)
            charge, pour = charge * m, pour * m
        self._split = (charge, pour)
        return charge + pour

    def _stock_cup(self, p, t):
        """An idle server at a station with an empty line pours one cup to stock during the
        pre-pour windows (bar.prepour). Returns True when a pour started."""
        pp = self.cfg["bar"]["prepour"]
        if p.kind != "direct" or not p.is_open(t):
            return False
        if not any(a <= t < z for a, z in self._prepour_windows):
            return False
        pending = sum(1 for e in p.serving if e[0] < 0)
        if len(p.stock) + pending >= pp["cups_per_station"]:
            return False
        busy = {e[2] for e in p.serving}
        free = [m for m in range(p.servers) if m not in busy]
        if not free:
            return False
        s = min(free, key=lambda m: p.free_at[m])
        start = max(t, p.free_at[s])
        d = _lognormal(self.rng, self.cfg["bar"]["s_pour_mean_s"], self.cfg["bar"]["service_cv"])
        self._spread(self.w_busy["stocking"], start, start + d)
        p.serving.append([-1, start + d, s, start + d])
        return True

    def _line_estimate(self, p):
        return ((len(p.queue) + p.walking) / p.servers + 1) * self.visit_s[p.kind]

    def _collect_round(self, i, t):
        """Friends of buyer i join the purchase: drinkers of the same group who stand in the
        crowd and have finished their last beer accept with probability round_join_share.
        They do not start a purchase of their own while i is away. Buyers of ready-to-drink
        cans buy for themselves only."""
        if self.rtd[i]:
            return
        if i in self.orders:
            return
        c = self.cfg["crowd"]
        mates = self.members[self.group[i]]
        if mates.size == 1:
            return
        ok = mates[(mates != i) & self.drinker[mates] & (self.state[mates] == WATCH)
                   & (self.ordered_by[mates] < 0) & (t < self.leave[mates] - 900)
                   & (t >= self.next_eligible[mates])]
        ok = ok[self.rng.random(ok.size) < c["round_join_share"]][: int(c["round_max_beers"]) - 1]
        if ok.size:
            self.ordered_by[ok] = i
            self.orders[i] = ok

    def _release_round(self, i):
        friends = self.orders.pop(i, None)
        if friends is not None:
            self.ordered_by[friends] = -1

    def _route(self, i):
        """Chosen first service point and estimated wait for attendee i, or (-1, inf)."""
        best, best_est = -1, np.inf
        needs_ticket = self.tickets[i] < 1 + len(self.orders.get(i, ()))
        t = self.t_now
        pour_est = min(((self._line_estimate(p), j) for j, p in enumerate(self.points)
                        if p.kind == "pour" and p.is_open(t)), default=(np.inf, -1))
        for j, p in enumerate(self.points):
            if not p.is_open(t):
                continue
            if p.kind == "cash" and needs_ticket:
                est = self._line_estimate(p) + pour_est[0]
            elif p.kind == "pour" and not needs_ticket:
                est = self._line_estimate(p)
            elif p.kind == "direct":
                est = self._line_estimate(p)
            else:
                continue
            est += np.hypot(p.x - self.x[i], p.y - self.y[i]) / 0.6
            if self._noise:                      # people misjudge lines (crowd.line_choice_noise)
                est *= self.rng.lognormal(0.0, self._noise)
            if est < best_est:
                best, best_est = j, est
        return best, best_est

    def _go_to_line(self, i, j):
        p = self.points[j]
        p.walking += 1
        self.target_q[i] = j
        self.state[i] = TO_QUEUE

    def _decide(self, i, t):
        """Thirsty attendee i picks a seller, a line, or postpones."""
        c = self.cfg["crowd"]
        if self.k and self.sellers_on and not self.skip_sellers[i]:
            ok = (self.s_stock > 0) & (self.s_state != S_OFF)
            if ok.any():
                d = np.hypot(self.sx[ok] - self.x[i], self.sy[ok] - self.y[i])
                if d.min() <= self.cfg["sellers"]["see_radius_m"]:
                    self.state[i] = WAIT_SELLER
                    self.wait_start[i] = t
                    self.claimed[i] = -1
                    self._collect_round(i, t)
                    return
        self.skip_sellers[i] = False
        self._collect_round(i, t)
        j, est = self._route(i)
        k, _ = self.sched.phase(t)
        patience = self.patience[i] * (c["fan_patience_mult"] if k >= 0 and self.fan[i, k]
                                       else 1.0)
        if j < 0 or est > patience:
            self._release_round(i)
            self.balks += 1
            self.balk_t.append(t)
            self.next_eligible[i] = t + 60 * self.rng.uniform(*c["defer_min"])
            self.want_t[i] = np.nan
            return
        self.via_cash[i] = self.points[j].kind == "cash"
        self._go_to_line(i, j)

    def _finish_purchase(self, i, t, beers, channel, kind):
        c = self.cfg["crowd"]
        friends = self.orders.pop(i, NO_FRIENDS)
        served = friends[: max(beers - 1, 0)]
        own = beers - served.size
        if self.rtd[i]:
            self.rtd_units[i] += own
        else:
            self.beers[i] += own
        if friends.size:
            # A friend got this beer before their own thirst asked for it. The time they would
            # still have waited is added to the pause, so rounds do not raise consumption.
            self.beers[served] += 1
            self.next_eligible[served] = (t + c["drink_min"] * 60
                                          + self.rng.exponential(1.0 / self.rate[served]))
            self.ordered_by[friends] = -1
        t_line = self.join_t[i] if kind == "seller" else self.q_enter[i]
        self.txn.append((self.want_t[i], self.join_t[i], t, channel, beers, i,
                         bool(self.via_cash[i]), t_line, kind))
        self.via_cash[i] = False
        self.next_eligible[i] = t + own * c["drink_min"] * 60
        self.want_t[i] = np.nan
        self.join_t[i] = np.nan

    # ------------------------------------------------------------------ step parts

    def _arrivals(self, t):
        start = self.next_arrival
        while self.next_arrival < self.n and self.arrival[self.next_arrival] <= t:
            self.next_arrival += 1
        ids = np.arange(start, self.next_arrival)
        if ids.size:
            self.x[ids] = self.venue.entrance[0] + self.rng.uniform(-0.3, 0.3, ids.size)
            self.y[ids] = self.venue.entrance[1] + self.rng.uniform(-0.6, 0.6, ids.size)
            self.next_eligible[ids] = t + 60 * self.rng.uniform(5, 30, ids.size)
            self._send_to_spot(ids)

    def _phase_change(self, t):
        k, focus = self.sched.focus(t)
        if (k, focus) == self.phase_key:
            return
        self.phase_key = (k, focus)
        self.focus_k = focus
        c = self.cfg["crowd"]
        watchers = np.flatnonzero(self.state == WATCH)
        if watchers.size == 0 or focus < 0:
            return
        near_stage = self.y[watchers] < self.venue.stage_front + c["front_zone_m"]
        fans = self.fan[watchers, focus]
        u = self.rng.random(watchers.size)
        # followers of the focus act move up front; others near the stage drift back
        move = ((fans & ~near_stage & (u < c["fan_move_share"]))
                | (~fans & near_stage & (u < c["nonfan_leave_share"]))
                | (u < c["shuffle_share"]))
        self._send_to_spot(watchers[move])

    def _thirst(self, t):
        c = self.cfg["crowd"]
        k, focus = self.sched.focus(t)
        cand = np.flatnonzero((self.state == WATCH) & (self.drinker | self.rtd)
                              & (self.ordered_by < 0)
                              & (t >= self.next_eligible) & (t < self.leave - 900))
        if cand.size == 0:
            return
        if k >= 0:
            mult = np.where(self.fan[cand, k], c["fan_thirst_mult"], c["nonfan_thirst_mult"])
        elif focus >= 0:
            mult = np.where(self.fan[cand, focus], c["holder_thirst_mult"],
                            c["changeover_boost"])
        else:
            mult = np.full(cand.size, c["changeover_boost"])
        if t < self.afternoon_end:
            mult = mult * c["afternoon_thirst_mult"]
        hit = cand[self.rng.random(cand.size) < self.rate[cand] * mult * self.dt]
        for i in hit:
            self.want_t[i] = t
            self._decide(i, t)

    def _departures(self, t):
        ids = np.flatnonzero((self.state == WATCH) & (t >= self.leave))
        if ids.size:
            self.state[ids] = TO_EXIT
            self.tx[ids], self.ty[ids] = self.venue.entrance
        ws = np.flatnonzero((self.state == WAIT_SELLER) & (t >= self.leave + 600)
                            & (self.claimed < 0))
        for i in ws:
            self._release_round(i)
            self.state[i] = TO_EXIT
            self.tx[i], self.ty[i] = self.venue.entrance

    def _move(self, t):
        moving = np.flatnonzero((self.state == TO_SPOT) | (self.state == TO_QUEUE)
                                | (self.state == TO_EXIT))
        if moving.size == 0:
            return
        q = moving[self.state[moving] == TO_QUEUE]
        for i in q:
            p = self.points[self.target_q[i]]
            slot = p.slots[min(len(p.queue), len(p.slots) - 1)]
            self.tx[i], self.ty[i] = slot
        dx = self.tx[moving] - self.x[moving]
        dy = self.ty[moving] - self.y[moving]
        dist = np.hypot(dx, dy)
        rho = self.rho[self.venue.cell_index(self.x[moving], self.y[moving])]
        v = weidmann_speed(rho, self.cfg["crowd"]["walk_speed_ms"])
        step = v * self.dt
        arrived = dist <= step
        f = np.where(arrived, 1.0, step / np.maximum(dist, 1e-9))
        self.x[moving] += dx * f
        self.y[moving] += dy * f
        for i in moving[arrived]:
            s = self.state[i]
            if s == TO_SPOT:
                self.state[i] = WATCH
            elif s == TO_EXIT:
                self.state[i] = GONE
            else:
                p = self.points[self.target_q[i]]
                p.walking -= 1
                p.queue.append(i)
                self.q_enter[i] = t
                self.state[i] = QUEUED
                if np.isnan(self.join_t[i]):
                    self.join_t[i] = t

    def _serve(self, t):
        b = self.cfg["bar"]
        for p in self.points:
            # A service ends at its exact time, and the next one starts at that time when its
            # customer was already waiting, so service times are not rounded to the step.
            while True:
                if p.serving:
                    k = min(range(len(p.serving)), key=lambda m: p.serving[m][1])
                    i, done, s = p.serving[k][:3]
                    if t >= done:
                        p.serving.pop(k)
                        p.free_at[s] = done
                        if i < 0:                    # a cup poured to stock
                            p.stock.append(done)
                        else:
                            self._end_service(p, i, done, t, b)
                        continue
                if not p.queue and self._prepour and len(p.serving) < p.servers:
                    if self._stock_cup(p, t):
                        continue
                if not p.queue or len(p.serving) >= p.servers:
                    break
                busy = {e[2] for e in p.serving}
                s = min((m for m in range(p.servers) if m not in busy),
                        key=lambda m: p.free_at[m])
                i = p.queue.popleft()
                self.state[i] = SERVICE
                sx = p.server_x[s] if p.server_x else p.x + (s - (p.servers - 1) / 2) * 0.8
                self.x[i], self.y[i] = sx, p.y + 0.4
                start = min(t, max(p.free_at[s], self.q_enter[i]))
                if p.kind == "cash":
                    end = start + self._service_time("cash", 1)
                else:
                    nf = len(self.orders.get(i, ()))
                    want_two = self.rng.random() < self.cfg["crowd"]["double_share"]
                    two = want_two and (p.kind == "direct" or self.tickets[i] >= nf + 2)
                    beers = nf + (2 if two else 1)
                    self._pending_beers[i] = beers
                    end = start + self._service_time(p.kind, beers, rtd=bool(self.rtd[i]))
                    if p.kind == "direct" and (self._prepour or self._menu_s or p.pooled):
                        end = start + self._adjust_split(p, t, beers)
                # [attendee, end, server, end of the first phase]. The customer pays first
                # when bar.pay_first holds (assumed order); a phase can last 0 s.
                charge, pour = self._split
                pay_first = b.get("pay_first", True)
                self._add_busy(start, charge, pour, pay_first)
                p.serving.append([i, end, s, start + (charge if pay_first else pour)])
            n = len(p.queue)
            if n:
                ids = np.fromiter(p.queue, int, n)
                pos = p.slots[np.minimum(np.arange(n), len(p.slots) - 1)]
                self.x[ids], self.y[ids] = pos[:, 0], pos[:, 1]
                if p.label == "bar":
                    self.max_reach = max(self.max_reach, float(p.y - pos[:, 1].min()))

    def _end_service(self, p, i, done, t, b):
        """Attendee i leaves the counter of point p at time done."""
        if p.kind == "cash":
            # tickets for this round plus some for later, at most 10 per visit
            need = max(1 + len(self.orders.get(i, ())) - self.tickets[i], 0)
            spare = self.rng.poisson(max(b["bundle_mean"] - 1.0, 0.0))
            self.tickets[i] += max(min(need + spare, 10), need)
            pours = [jj for jj, pp in enumerate(self.points)
                     if pp.kind == "pour" and pp.is_open(t)]
            jj = min(pours, key=lambda m: self._line_estimate(self.points[m]))
            self._go_to_line(i, jj)
        else:
            beers = self._pending_beers[i]
            if p.kind == "pour":
                self.tickets[i] -= beers
            self._finish_purchase(i, done, beers, p.label, p.kind)
            self._send_to_spot([i])

    def _renege(self, t):
        c = self.cfg["crowd"]
        for p in self.points:
            if not p.queue:
                continue
            keep = []
            for i in p.queue:
                if t - self.join_t[i] > self.patience[i] * c["renege_factor"]:
                    self.reneges += 1
                    self.txn.append((self.want_t[i], self.join_t[i], t, "renege", 0, i,
                                     bool(self.via_cash[i]), self.q_enter[i], p.kind))
                    self.via_cash[i] = False
                    self._release_round(i)
                    self.want_t[i] = np.nan
                    self.join_t[i] = np.nan
                    self.next_eligible[i] = t + 60 * self.rng.uniform(*c["defer_min"])
                    self._send_to_spot([i])
                else:
                    keep.append(i)
            p.queue.clear()
            p.queue.extend(keep)

    def _sellers(self, t):
        if not self.k:
            return
        s = self.cfg["sellers"]
        on_i = (self.s_start_i <= t) & (t < self.s_end_i)
        self.sellers_on = bool(on_i.any())
        waiting = np.flatnonzero(self.state == WAIT_SELLER)
        # attendees who waited too long without a seller walk to the bar
        for i in waiting:
            if self.claimed[i] < 0 and t - self.wait_start[i] > s["wait_max_min"] * 60:
                self.seller_giveups += 1
                self.state[i] = WATCH
                self.skip_sellers[i] = True
                self._decide(i, t)
        free_wait = np.flatnonzero((self.state == WAIT_SELLER) & (self.claimed < 0))
        rho = self.rho[self.venue.cell_index(self.sx, self.sy)]
        v = weidmann_speed(rho, self.cfg["crowd"]["walk_speed_ms"] * s["speed_factor"])
        for m in range(self.k):
            on = on_i[m]
            st = self.s_state[m]
            if st == S_OFF:
                if on:
                    self.s_state[m] = S_PATROL
                    st = S_PATROL
                else:
                    continue
            if st == S_PATROL:
                if not on:
                    self.s_state[m] = S_OFF
                    continue
                if self.s_stock[m] <= 0:
                    self.s_state[m] = S_TO_RESTOCK
                    rp = self.restock
                    r = np.argmin(np.hypot(rp[:, 0] - self.sx[m], rp[:, 1] - self.sy[m]))
                    self.stx[m], self.sty[m] = rp[r]
                    continue
                if free_wait.size:
                    d = np.hypot(self.x[free_wait] - self.sx[m], self.y[free_wait] - self.sy[m])
                    near = np.argmin(d)
                    if d[near] <= s["detect_radius_m"]:
                        i = free_wait[near]
                        self.claimed[i] = m
                        self.s_cust[m] = i
                        self.s_state[m] = S_TO_CUSTOMER
                        free_wait = np.delete(free_wait, near)
                        continue
                if np.hypot(self.stx[m] - self.sx[m], self.sty[m] - self.sy[m]) < 1.0:
                    watchers = np.flatnonzero(self.state == WATCH)
                    if watchers.size:
                        i = self.rng.choice(watchers)
                        self.stx[m], self.sty[m] = self.x[i], self.y[i]
            elif st == S_TO_CUSTOMER:
                i = self.s_cust[m]
                if self.state[i] != WAIT_SELLER:
                    self.s_state[m] = S_PATROL
                    self.s_cust[m] = -1
                    continue
                self.stx[m], self.sty[m] = self.x[i], self.y[i]
                if np.hypot(self.x[i] - self.sx[m], self.y[i] - self.sy[m]) < 1.0:
                    self.s_state[m] = S_SERVING
                    own = 2 if self.rng.random() < self.cfg["crowd"]["double_share"] else 1
                    beers = min(own + len(self.orders.get(i, ())), self.s_stock[m])
                    self._pending_beers[i] = beers
                    self.s_busy[m] = t + _lognormal(self.rng, s["s_sale_s"] * (0.6 + 0.4 * beers),
                                                    0.35)
            elif st == S_SERVING:
                if t >= self.s_busy[m]:
                    i = self.s_cust[m]
                    beers = self._pending_beers[i]
                    self.s_stock[m] -= beers
                    self.s_sold[m] += beers
                    self.join_t[i] = self.wait_start[i]
                    self._finish_purchase(i, t, beers, "seller", "seller")
                    if self.state[i] == WAIT_SELLER:
                        self.state[i] = WATCH
                    self.claimed[i] = -1
                    self.s_cust[m] = -1
                    self.s_state[m] = S_PATROL
            elif st == S_TO_RESTOCK:
                if np.hypot(self.stx[m] - self.sx[m], self.sty[m] - self.sy[m]) < 0.8:
                    self.s_state[m] = S_RESTOCKING
                    self.s_busy[m] = t + s["restock_s"]
            elif st == S_RESTOCKING:
                if t >= self.s_busy[m]:
                    self.s_stock[m] = int(s["capacity"])
                    self.s_state[m] = S_PATROL if on else S_OFF
            if self.s_state[m] in (S_PATROL, S_TO_CUSTOMER, S_TO_RESTOCK):
                dx, dy = self.stx[m] - self.sx[m], self.sty[m] - self.sy[m]
                d = np.hypot(dx, dy)
                step = v[m] * self.dt
                f = 1.0 if d <= step else step / d
                self.sx[m] += dx * f
                self.sy[m] += dy * f

    # ------------------------------------------------------------------ run

    def run(self):
        self.start()
        self.advance(self.t_end)
        return self.results()

    def start(self):
        """Prepare the loop state. advance() can then be called one or more times."""
        self._pending_beers = np.ones(self.n, int)
        b = self.cfg["bar"]
        self.visit_s = {"cash": b["s_cash_mean_s"], "pour": b["s_pour_mean_s"] * 1.3,
                        "direct": b["s_pour_mean_s"] * 1.3 + b["s_pay_direct_s"]}
        # busy and staffed seconds of the bar workers and seller seconds by state
        self.hour0 = int(self.t0_min // 60)
        n_hours = int(np.ceil((self.t0_min * 60 + self.t_end) / 3600)) - self.hour0 + 1
        self.w_busy = {"charging": np.zeros(n_hours), "pouring": np.zeros(n_hours),
                       "stocking": np.zeros(n_hours)}
        b, c = self.cfg["bar"], self.cfg["crowd"]
        self._noise = float(c.get("line_choice_noise", 0.0) or 0.0)
        self._menu_s = float(b.get("menu_choice_s", 0.0) or 0.0)
        self._prepour = bool(b.get("prepour"))
        self._prepour_windows = self._prepour_spans() if self._prepour else []
        self.cups_discarded = self.cups_used = 0
        self.max_reach = 0.0
        for p in self.points:
            p.stock = deque()
        self.w_staffed = np.zeros(n_hours)
        self.s_time = np.zeros(len(SELLER_STATES))
        self._split = (0.0, 0.0)
        self.phase_key = (-2, -2)
        self.focus_k = -1
        self.sellers_on = False
        self.w_front = self.venue.front_weights()
        self.w_back = self.venue.back_weights()
        self.present = self._present_mask()
        self._density()
        self._rows, self._frames = [], []
        self._next_rec, self._next_frame, self._next_renege = 0.0, self.frame_t0, 60.0
        self.t_now = 0.0
        self._t = 0.0

    def advance(self, until: float):
        """Run the steps up to `until` seconds after doors."""
        t = self._t
        until = min(until, self.t_end)
        while t <= until:
            self.t_now = t
            self.present = self._present_mask()
            self._density()
            self._phase_change(t)
            self._arrivals(t)
            self._departures(t)
            self._sellers(t)
            self._thirst(t)
            self._serve(t)
            self._account(t)
            self._move(t)
            if t >= self._next_renege:
                self._renege(t)
                self._next_renege += 60.0
            if t >= self._next_rec:
                self._rows.append(self._summary(t))
                self._next_rec += 60.0
            if (self.record_frames and self.frame_t0 <= t <= self.frame_t1
                    and t >= self._next_frame):
                self._frames.append(self._frame(t))
                self._next_frame += self.frame_every
            t += self.dt
        self._t = t

    def results(self):
        return self._results(self._rows, self._frames)

    def waits_so_far(self, lo: float, hi: float, ticket_buyers: bool = False) -> np.ndarray:
        """Minutes in line of the people who joined a bar line between lo and hi (seconds
        after doors). People still in line count as an infinite wait, so the median stays
        correct while the night is running."""
        done = [(served - join) / 60.0
                for _, join, served, channel, _, _, via, _, _ in self.txn
                if channel != "seller" and lo <= join < hi and (via or not ticket_buyers)]
        waiting = ((self.state == QUEUED) | (self.state == SERVICE) | (self.state == TO_QUEUE))
        waiting &= (self.join_t >= lo) & (self.join_t < hi)
        if ticket_buyers:
            waiting &= self.via_cash
        return np.concatenate([np.array(done, float), np.full(int(waiting.sum()), np.inf)])

    def gave_up_so_far(self, lo: float, hi: float) -> tuple[int, int]:
        """Purchase attempts at the bar that started between lo and hi (seconds after doors):
        the number given up and the number in all. An attempt is given up when the person
        decides not to join the line they see, or leaves a line before service. People still
        in line count as attempts that have not been given up."""
        balked = sum(lo <= t < hi for t in self.balk_t)
        left = joined = 0
        for _, join, _, channel, _, _, _, _, _ in self.txn:
            if channel != "seller" and lo <= join < hi:
                joined += 1
                left += channel == "renege"
        waiting = ((self.state == QUEUED) | (self.state == SERVICE) | (self.state == TO_QUEUE))
        waiting &= (self.join_t >= lo) & (self.join_t < hi)
        return balked + left, balked + joined + int(waiting.sum())

    def line_waits_so_far(self, lo: float, hi: float, kind: str):
        """Minutes spent in a line of one kind ("cash", "pour" or "direct") by the people who
        joined it between lo and hi (seconds after doors), and whether each one was served.
        People who gave up and people still in the line have served = False: their time is
        a lower bound of the wait."""
        minutes, served = [], []
        for _, _, end, channel, _, _, _, t_line, line_kind in self.txn:
            if line_kind == kind and lo <= t_line < hi:
                minutes.append((end - t_line) / 60.0)
                served.append(channel != "renege")
        for p in self.points:
            if p.kind != kind:
                continue
            for i in list(p.queue) + [e[0] for e in p.serving if e[0] >= 0]:
                if lo <= self.q_enter[i] < hi:
                    minutes.append((self.t_now - self.q_enter[i]) / 60.0)
                    served.append(False)
        return np.array(minutes, float), np.array(served, bool)

    def _summary(self, t):
        st = self.state
        cash = sum(len(p.queue) for p in self.points if p.kind == "cash")
        pour = sum(len(p.queue) for p in self.points
                   if p.kind != "cash" and p.label == "bar")
        sat = sum(len(p.queue) for p in self.points if p.label == "satellite")
        front = (self.present & (self.y < self.venue.stage_front + 6)
                 & (self.x > 5) & (self.x < 25)).sum() / (6 * 20)
        cells = self.venue.cell_index(self.x[self.present], self.y[self.present])
        return {
            "t_min": t / 60.0,
            "clock_min": self.t0_min + t / 60.0,
            "occupancy": int(self.present.sum()),
            "on_floor": int(self.venue.is_floor[cells].sum()),
            "arrived": int(self.next_arrival),
            "left": int((st == GONE).sum()),
            "queue_cash": cash,
            "queue_pour": pour,
            "queue_satellite": sat,
            "wait_seller": int((st == WAIT_SELLER).sum()),
            "in_lines_total": int(((st == QUEUED) | (st == SERVICE) | (st == TO_QUEUE)).sum()),
            "beers_total": int(self.beers.sum()),
            "balks": self.balks,
            "reneges": self.reneges,
            "front_density": front,
            "max_rho": float(self.rho.max()),
            "act": self.sched.label(t),
            "band_playing": int(self.sched.phase(t)[0] >= 0),
            **self._state_counts(t),
        }

    def _state_counts(self, t):
        """Bar workers and sellers in each state at time t."""
        _, _, ws = self.worker_states(t)
        out = {f"bar_{name}": int((ws == k).sum()) for k, name in enumerate(WORKER_STATES)}
        rep = np.array([SELLER_REPORT[int(v)] for v in self.s_state], int)
        out.update({f"sellers_{name}": int((rep == k).sum())
                    for k, name in enumerate(SELLER_STATES)})
        return out

    def _frame(self, t):
        pres = np.flatnonzero(self.present)
        return {
            "t": t,
            "x": self.x[pres].astype(np.float32),
            "y": self.y[pres].astype(np.float32),
            "state": self.state[pres].copy(),
            "kind": np.array([self.points[q].kind if q >= 0 else "" for q in
                              self.target_q[pres]]) if pres.size else np.array([]),
            "sx": self.sx.copy(), "sy": self.sy.copy(),
            "s_state": self.s_state.copy(), "s_stock": self.s_stock.copy(),
            **dict(zip(("wx", "wy", "w_state"), self.worker_states(t))),
            "rho": self.counts.reshape(self.venue.ny, self.venue.nx).copy(),
        }

    def _results(self, rows, frames):
        import pandas as pd
        series = pd.DataFrame(rows)
        txn = pd.DataFrame(self.txn, columns=["t_want", "t_join", "t_served", "channel",
                                              "beers", "agent", "via_cashier", "t_line",
                                              "line_kind"])
        if len(txn):
            txn["line_min"] = (txn["t_served"] - txn["t_join"]) / 60.0
            txn["last_line_min"] = (txn["t_served"] - txn["t_line"]) / 60.0
            txn["clock_line_min"] = self.t0_min + txn["t_line"] / 60.0
            txn["total_min"] = (txn["t_served"] - txn["t_want"]) / 60.0
            txn["clock_join_min"] = self.t0_min + txn["t_join"] / 60.0
            txn["clock_served_min"] = self.t0_min + txn["t_served"] / 60.0
        return {"series": series, "txn": txn, "frames": frames,
                "seller_sold": self.s_sold.copy(), "seller_giveups": self.seller_giveups,
                "options": {"cups_discarded": self.cups_discarded, "cups_used": self.cups_used,
                            "max_reach_m": self.max_reach,
                            "rtd_units": int(self.rtd_units.sum()),
                            "heavy6_any_share": float(((self.beers + self.rtd_units) >= 6)
                                                      .mean())},
                "workers": {"hour0": self.hour0, "staffed_s": self.w_staffed.copy(),
                            "charging_s": self.w_busy["charging"].copy(),
                            "pouring_s": self.w_busy["pouring"].copy(),
                            "stocking_s": self.w_busy["stocking"].copy(),
                            "seller_s": dict(zip(SELLER_STATES, self.s_time.copy()))},
                "points": [(p.kind, p.x, p.y) for p in self.points]}
