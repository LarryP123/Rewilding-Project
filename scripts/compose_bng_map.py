"""Composite the finished BNG alignment map: title, legend, scale bar, north
arrow, and finding callout on top of a QGIS-rendered choropleth.

Run after rendering outputs/qgis/bng_alignment.qgs to a cropped PNG (see
README "Build a QGIS project" section for the qgis_process / gdal_translate
commands). Reads outputs/qgis/bng_alignment_cropped.png, writes
outputs/qgis/bng_alignment_map.png.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.image import imread

IN_PNG = "outputs/qgis/bng_alignment_cropped.png"
OUT_PNG = "outputs/qgis/bng_alignment_map.png"

# Same breaks/colors as the QGIS graduated renderer (renderer-v2 in bng_alignment.qgs)
BREAKS = [0.0, 35.72, 40.68, 44.34, 46.63, 67.04]
COLORS = [
    (247 / 255, 252 / 255, 245 / 255),
    (199 / 255, 233 / 255, 192 / 255),
    (116 / 255, 196 / 255, 118 / 255),
    (49 / 255, 163 / 255, 84 / 255),
    (0 / 255, 109 / 255, 44 / 255),
]
BNG_COLOR = (215 / 255, 25 / 255, 28 / 255)

# Map extent used for the render, EPSG:27700 metres
XMIN, YMIN, XMAX, YMAX = 82607.0, 5553.0, 655526.0, 657532.0

MAP_LEFT, MAP_RIGHT, MAP_TOP, MAP_BOTTOM = 0.04, 0.72, 0.90, 0.10


def main() -> None:
    img = imread(IN_PNG)
    h, w = img.shape[0], img.shape[1]

    fig = plt.figure(figsize=(14, 16), dpi=200, facecolor="white")
    gs = fig.add_gridspec(1, 1, left=MAP_LEFT, right=MAP_RIGHT, top=MAP_TOP, bottom=MAP_BOTTOM)
    ax_map = fig.add_subplot(gs[0, 0])
    ax_map.imshow(img)
    ax_map.axis("off")

    fig.text(0.04, 0.965, "Rewilding Opportunity vs Registered Biodiversity Net Gain Sites",
              fontsize=20, fontweight="bold", ha="left", va="top", family="sans-serif")
    fig.text(0.04, 0.935, "England, 1km hex grid — balanced-scenario suitability score against the real BNG Gain Site Register",
              fontsize=12.5, ha="left", va="top", family="sans-serif", color="#333333")

    # ---- Legend panel (right side) ----
    legend_x = 0.755
    ax_legend = fig.add_axes([legend_x, 0.30, 0.22, 0.55])
    ax_legend.axis("off")

    ax_legend.text(0, 1.0, "Rewilding opportunity score", fontsize=12.5, fontweight="bold", va="top", transform=ax_legend.transAxes)
    ax_legend.text(0, 0.965, "(balanced scenario, 0–100)", fontsize=10, va="top", color="#444444", transform=ax_legend.transAxes)

    n = len(COLORS)
    sw_h = 0.055
    start_y = 0.90
    for i, c in enumerate(COLORS):
        y = start_y - i * (sw_h + 0.012)
        ax_legend.add_patch(mpatches.Rectangle((0, y - sw_h), 0.14, sw_h, transform=ax_legend.transAxes,
                                                facecolor=c, edgecolor="#999999", linewidth=0.5))
        label = f"{BREAKS[i]:.1f} – {BREAKS[i + 1]:.1f}"
        ax_legend.text(0.19, y - sw_h / 2, label, fontsize=10.5, va="center", transform=ax_legend.transAxes)

    sep_y = start_y - n * (sw_h + 0.012) - 0.03
    ax_legend.plot([0, 0.6], [sep_y, sep_y], color="#cccccc", linewidth=0.8, transform=ax_legend.transAxes)

    pt_y = sep_y - 0.07
    ax_legend.scatter([0.07], [pt_y], s=90, color=BNG_COLOR, edgecolor="#232323", linewidth=0.8,
                       transform=ax_legend.transAxes, zorder=5)
    ax_legend.text(0.19, pt_y, "Registered BNG site", fontsize=10.5, va="center", transform=ax_legend.transAxes)
    ax_legend.text(0.19, pt_y - 0.045, "(n = 312, live register mirror)", fontsize=9, va="center", color="#444444",
                   transform=ax_legend.transAxes)

    # ---- Key finding callout ----
    finding_y = pt_y - 0.13
    ax_legend.add_patch(mpatches.FancyBboxPatch((0, finding_y - 0.37), 0.92, 0.37,
                                                 boxstyle="round,pad=0.01,rounding_size=0.01",
                                                 transform=ax_legend.transAxes,
                                                 facecolor="#f4f4f0", edgecolor="#cccccc", linewidth=0.6))
    finding_text = (
        "Finding: BNG sites track\n"
        "development, not ecology.\n\n"
        "Only 40% of top-100 balanced\n"
        "hexes sit within 10km of a\n"
        "site, vs 45% nationally\n"
        "(r = 0.10 across scenarios).\n\n"
        "Distance to urban/industrial\n"
        "land explains BNG proximity\n"
        "~2x better (r = 0.27): 73.7%\n"
        "of sites sit within 2km of\n"
        "urban land, vs 63.0% nationally."
    )
    ax_legend.text(0.05, finding_y - 0.02, finding_text, fontsize=9.3, va="top", ha="left",
                   transform=ax_legend.transAxes, linespacing=1.5)

    # ---- Scale bar (figure-level, in the blank strip below the map — this
    # is deliberately NOT drawn inside the map image's own pixel space,
    # since a coastline shape (e.g. Cornwall tapering into the bottom-left
    # corner) can leave no clear room there regardless of where the bar is
    # nudged) ----
    map_width_km = (XMAX - XMIN) / 1000.0
    km_per_figfrac = map_width_km / (MAP_RIGHT - MAP_LEFT)
    bar_km = 100
    bar_frac_len = bar_km / km_per_figfrac
    bar_x0_fig = MAP_LEFT
    bar_y_fig = 0.065

    fig.add_artist(plt.Line2D([bar_x0_fig, bar_x0_fig + bar_frac_len], [bar_y_fig, bar_y_fig],
                               transform=fig.transFigure, color="black", linewidth=3, solid_capstyle="butt"))
    tick_kms = [0, 50, 100]
    for tick_km in tick_kms:
        tx = bar_x0_fig + (tick_km / bar_km) * bar_frac_len
        fig.add_artist(plt.Line2D([tx, tx], [bar_y_fig - 0.005, bar_y_fig + 0.005],
                                   transform=fig.transFigure, color="black", linewidth=1.5))
        label = f"{tick_km} km" if tick_km == tick_kms[-1] else f"{tick_km}"
        fig.text(tx, bar_y_fig + 0.014, label, fontsize=9, ha="center", va="bottom", transform=fig.transFigure)

    # ---- North arrow ----
    na_x = w - w * 0.055
    na_y0 = h * 0.10
    na_len = h * 0.05
    ax_map.annotate("", xy=(na_x, na_y0 - na_len), xytext=(na_x, na_y0),
                     arrowprops=dict(arrowstyle="-|>", color="black", linewidth=2, mutation_scale=18))
    ax_map.text(na_x, na_y0 - na_len - h * 0.018, "N", fontsize=13, fontweight="bold", ha="center", va="top")

    # ---- Attribution ----
    fig.text(0.04, 0.025,
             "Data: rewilding-suitability canonical v6 hex scores; Biodiversity Gain Site Register "
             "(via The Wildlife Trusts public mirror, updated daily). CRS: EPSG:27700 (British National Grid).\n"
             "Rendered with QGIS 3.44 (native:rasterize) · Laurence Pengelly · github.com/LarryP123/Rewilding-Project",
             fontsize=8.3, ha="left", va="bottom", color="#555555", family="sans-serif")

    fig.savefig(OUT_PNG, facecolor="white")
    print("wrote", OUT_PNG)


if __name__ == "__main__":
    main()
