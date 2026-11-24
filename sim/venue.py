"""Hall geometry: walkable cells, spot sampling, service points and queue slots."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

import numpy as np

# Weidmann (1993) speed-density relation for pedestrian flow on level ground.
WEIDMANN_GAMMA = 1.913
WEIDMANN_RHO_MAX = 5.4


def weidmann_speed(rho: np.ndarray, v0: float) -> np.ndarray:
    rho = np.clip(rho, 0.05, WEIDMANN_RHO_MAX - 0.05)
    v = v0 * (1.0 - np.exp(-WEIDMANN_GAMMA * (1.0 / rho - 1.0 / WEIDMANN_RHO_MAX)))
    return np.clip(v, 0.08, v0)


def _inside(cx, cy, r):
    return (cx >= r["x0"]) & (cx < r["x1"]) & (cy >= r["y0"]) & (cy < r["y1"])


@dataclass
class ServicePoint:
    """One line at the counter, served by `servers` people."""
    kind: str                 # "cash", "pour" or "direct"
    x: float
    y: float
    slots: np.ndarray         # (n, 2) positions of queue places, index 0 at the counter
    servers: int = 1
    queue: deque = field(default_factory=deque)
    serving: list = field(default_factory=list)   # [attendee, end of service, server index]
    free_at: list = field(default_factory=list)   # time at which each server became free
    walking: int = 0          # attendees heading to this line
    open_from: float = -np.inf  # seconds after doors; the line accepts people in this window
    open_to: float = np.inf
    label: str = "bar"

    def __post_init__(self):
        if not self.free_at:
            self.free_at = [-1.0] * self.servers

    def is_open(self, t: float) -> bool:
        return self.open_from <= t < self.open_to


def queue_slots(x0, y0, direction, lateral, lane_len, spacing=0.55, lane_gap=0.7, n=900):
    """Snake-shaped line: straight lanes of lane_len meters that alternate direction."""
    d = np.asarray(direction, float)
    lat = np.asarray(lateral, float)
    per_lane = max(int(lane_len / spacing), 1)
    idx = np.arange(n)
    lane = idx // per_lane
    along = (idx % per_lane) * spacing
    along = np.where(lane % 2 == 0, along, (per_lane - 1) * spacing - along)
    pos = (np.array([x0, y0])[None, :]
           + along[:, None] * d[None, :]
           + (lane * lane_gap)[:, None] * lat[None, :])
    return pos


class Venue:
    def __init__(self, cfg: dict):
        v = cfg["venue"]
        self.cfg = v
        self.L = v["length_m"]
        self.W = v["width_m"]
        self.nx = int(np.ceil(self.W))
        self.ny = int(np.ceil(self.L))
        cx, cy = np.meshgrid(np.arange(self.nx) + 0.5, np.arange(self.ny) + 0.5)
        self.cell_x = cx.ravel()
        self.cell_y = cy.ravel()

        audience = (self.cell_y > v["stage"]["y1"]) & (self.cell_y < v["bar_zone"]["y0"])
        side = (_inside(self.cell_x, self.cell_y, v["tables"])
                | _inside(self.cell_x, self.cell_y, v["vendors_west"])
                | _inside(self.cell_x, self.cell_y, v["vendors_east"]))
        # The lighting and drone booth and the cocktail line take floor where nobody stands.
        blocked = np.zeros(self.cell_x.size, bool)
        if v.get("booth"):
            blocked |= _inside(self.cell_x, self.cell_y, v["booth"])
        if v.get("cocktail_line"):
            blocked |= _inside(self.cell_x, self.cell_y, self.cocktail_strip())
        audience &= ~blocked
        self.floor_cells = np.flatnonzero(audience & ~side)
        self.is_floor = audience & ~side
        self.side_cells = np.flatnonzero(audience & side)
        self.spot_cells = np.concatenate([self.floor_cells, self.side_cells])
        self.spot_cap = np.concatenate([
            np.full(self.floor_cells.size, v["floor_cap_ppm2"]),
            np.full(self.side_cells.size, v["side_cap_ppm2"]),
        ])
        self.spot_is_side = np.concatenate([
            np.zeros(self.floor_cells.size, bool), np.ones(self.side_cells.size, bool)])
        self.stage_front = v["stage"]["y1"]
        self.entrance = np.array([v["entrance"]["x"], v["entrance"]["y"]])
        # Sellers refill at the two ends of the counter that the floor reaches: next to the
        # east vendor strip and next to the tables.
        self.restock_points = np.array([[v["vendors_east"]["x1"] + 0.5, v["counter_y"] + 1.0],
                                        [v["tables"]["x0"] - 0.5, v["counter_y"] + 1.0]])

    def lane_length(self, x: float, default: float) -> float:
        """Length of the first lane of a line that starts at the counter at x: the line runs
        toward the stage and stops 0.5 m short of the booth when the booth is in its way."""
        b = self.cfg.get("booth")
        if b and b["x0"] - 1.0 <= x <= b["x1"] + 1.0:
            return min(default, self.cfg["counter_y"] - 1.0 - b["y1"])
        return default

    def cocktail_strip(self) -> dict:
        """Floor taken by the cocktail line, from the counter toward the stage."""
        c = self.cfg["cocktail_line"]
        y1 = self.cfg["bar_zone"]["y0"]
        y0 = self.cfg["counter_y"] - 0.5 - self.lane_length(c["x"], c["length_m"])
        return {"x0": c["x"] - c["half_width"], "x1": c["x"] + c["half_width"], "y0": y0, "y1": y1}

    def station_x(self, n: int, lo: float, hi: float) -> np.ndarray:
        """x of n stations spread evenly over the counter from lo to hi, leaving a gap at the
        cocktail line."""
        segs = [(lo, hi)]
        c = self.cfg.get("cocktail_line")
        if c and lo < c["x"] < hi:
            g = c["half_width"] + 0.7
            segs = [(lo, c["x"] - g), (c["x"] + g, hi)]
        total = sum(b - a for a, b in segs)
        pos = np.linspace(0.0, total, n) if n > 1 else np.array([total / 2])
        out = []
        for d in pos:
            for a, b in segs:
                if d <= b - a + 1e-9:
                    out.append(a + d)
                    break
                d -= b - a
        return np.array(out)

    def cell_index(self, x, y):
        ix = np.clip(x.astype(int), 0, self.nx - 1)
        iy = np.clip(y.astype(int), 0, self.ny - 1)
        return iy * self.nx + ix

    def front_weights(self) -> np.ndarray:
        """Spot preference of people who follow the act on stage (or the next act)."""
        y = self.cell_y[self.spot_cells]
        w = np.exp(-(y - self.stage_front) / self.cfg["front_scale_m"])
        return np.where(self.spot_is_side, 0.02 * w.mean(), w)

    def back_weights(self) -> np.ndarray:
        """Spot preference of everyone else: toward the bar, the vendors and the tables."""
        y = self.cell_y[self.spot_cells]
        w = 0.35 + np.exp(-(self.cfg["counter_y"] - y) / self.cfg["back_scale_m"])
        return np.where(self.spot_is_side, 0.8 * w.mean(), w)

    def sample_spots(self, rng, n, base_w, occupied, chunk=20):
        """Sample n positions. `occupied` counts people standing in or heading to each cell;
        sampling runs in chunks and updates it, so a cell does not exceed its cap."""
        occ = occupied[self.spot_cells].astype(float)
        cells = np.empty(n, int)
        for s in range(0, n, chunk):
            m = min(chunk, n - s)
            free = np.clip(1.0 - occ / self.spot_cap, 0.0, 1.0)
            w = base_w * free
            if w.sum() <= 0:
                w = base_w
            pick = rng.choice(w.size, size=m, p=w / w.sum())
            np.add.at(occ, pick, 1.0)
            cells[s:s + m] = pick
        cells = self.spot_cells[cells]
        x = self.cell_x[cells] + rng.uniform(-0.5, 0.5, n)
        y = self.cell_y[cells] + rng.uniform(-0.5, 0.5, n)
        return x, y

    def build_service_points(self, cfg: dict, t0_min: float = 0.0) -> list[ServicePoint]:
        b = cfg["bar"]
        cy = self.cfg["counter_y"] - 0.5
        points: list[ServicePoint] = []
        if b["mode"] == "ticket":
            # Ticket windows: their lines run toward the stage and snake toward the east wall.
            for x in b["cashier_x"][: b["n_cashiers"]]:
                points.append(ServicePoint("cash", x, cy + 0.3,
                                           queue_slots(x, cy, (0, -1), (-1, 0),
                                                       self.lane_length(x, 24.0))))
            # Beer exchange lines: the people serving beer are split between them.
            xs, n = b["exchange_x"], b["n_pour"]
            for k, x in enumerate(xs):
                servers = n // len(xs) + (1 if k < n % len(xs) else 0)
                if servers:
                    points.append(ServicePoint("pour", x, cy + 0.3,
                                               queue_slots(x, cy, (0, -1), (1, 0),
                                                           self.lane_length(x, 22.0),
                                                           lane_gap=0.6),
                                               servers=servers))
        else:
            # One station per person serving, each with its own line. Extra stations are
            # staffed only during a shift window (bar.extra_pour, extra_from/to).
            n = b["n_pour"]
            n_extra = int(b.get("extra_pour", 0))
            xs = self.station_x(n + n_extra, b["pour_x_min"], b["pour_x_max"])
            extra_idx = (set(np.linspace(0, len(xs) - 1, n_extra).round().astype(int))
                         if n_extra else set())
            if n_extra:
                from .params import clock_to_min
                shift = ((clock_to_min(b["extra_from"]) - t0_min) * 60,
                         (clock_to_min(b["extra_to"]) - t0_min) * 60)
            for k, x in enumerate(xs):
                sp = ServicePoint("direct", float(x), cy + 0.3,
                                  queue_slots(x, cy, (0, -1), (1, 0),
                                              self.lane_length(x, 22.0), lane_gap=0.6))
                if k in extra_idx:
                    sp.open_from, sp.open_to = shift
                points.append(sp)
        if b.get("satellite_bar"):
            side = b.get("satellite_side", "east")
            sides = ["east", "west"] if side == "both" else [side]
            for sd in sides:
                # the bar stands on the inner edge of the strip and its lines run into the floor
                strip = self.cfg[f"vendors_{sd}"]
                inner_low = strip["x0"] > self.W / 2
                xb, d = (strip["x0"], (-1, 0)) if inner_low else (strip["x1"], (1, 0))
                ys = b["satellite_y"] + np.arange(b["satellite_n_pour"]) * 3.0
                for y in ys:
                    points.append(ServicePoint("direct", xb, float(y),
                                               queue_slots(xb + 0.3 * d[0], float(y), d, (0, -1),
                                                           6.0, lane_gap=0.6),
                                               label="satellite"))
        return points
