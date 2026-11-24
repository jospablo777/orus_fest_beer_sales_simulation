"""Colors and matplotlib defaults for all Python figures, taken from the Orus Fest 2026
promotion art (black background, blood red, bronze, bone white, steel blue).

The same values are used in analysis/figures.R and report/template.html.
Categorical order red, bronze, blue passes the CVD and lightness checks on PAPER.
"""

import matplotlib as mpl

PAPER = "#100d0c"      # page and figure background
FLOOR = "#1c1715"      # hall floor in plan views
INK = "#ece4d6"        # bone white text
MUTED = "#a69c8c"
GRID = "#2c2522"
RULE = "#3a312c"

RED = "#c42a3c"        # 2026 setup, problems
BRONZE = "#bd8a35"     # recommended setup
BLUE = "#3586c6"       # third series
SILVER = "#8e939b"     # neutral: other options, the crowd

# Crowd states in the floor views (brighter steps of the same hues for small dots).
DOT_CROWD = SILVER
DOT_TO_LINE = "#e3a33a"
DOT_TICKET = "#e5484d"
DOT_TAP = "#ee7a3c"
DOT_WAIT_SELLER = "#4aa3df"
DOT_SELLER = "#3fbf6a"

# Zone hues follow the study author's annotated screenshot (stage purple, bar turquoise,
# tables yellow, vendors green).
ZONES = {"stage": "#8C3CFF", "bar_zone": "#28B9D7", "tables": "#FFB91E",
         "vendors_west": "#6ED746", "vendors_east": "#6ED746"}

DENSITY_STEPS = ["#1c1715", "#4a1c20", "#8c2330", "#c42a3c", "#f2a7a0"]


def apply():
    mpl.rcParams.update({
        "figure.facecolor": PAPER,
        "savefig.facecolor": PAPER,
        "axes.facecolor": PAPER,
        "axes.edgecolor": RULE,
        "axes.labelcolor": INK,
        "axes.titlecolor": INK,
        "text.color": INK,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "grid.color": GRID,
        "legend.labelcolor": INK,
        "font.family": "DejaVu Sans",
    })
