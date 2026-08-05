"""Composite the finished Rewilding Network validation map: title, legend,
scale bar, north arrow, and finding callout on top of a QGIS-rendered
choropleth.

Run after rendering outputs/qgis/rewilding_network_validation.qgs to a
cropped PNG (see README "Validating against real rewilding sites" section
for the qgis_process / gdal_translate commands). Reads
outputs/qgis/rewilding_network_cropped.png, writes
outputs/qgis/rewilding_network_map.png.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.image import imread

IN_PNG = "outputs/qgis/rewilding_network_cropped.png"
OUT_PNG = "outputs/qgis/rewilding_network_map.png"

# Same breaks/colors as the QGIS graduated renderer (renderer-v2 in rewilding_network_validation.qgs)
BREAKS = [0.0, 28.97, 39.12, 41.56, 45.91, 72.23]
COLORS = [
    (247 / 255, 252 / 255, 245 / 255),
    (199 / 255, 233 / 255, 192 / 255),
    (116 / 255, 196 / 255, 118 / 255),
    (49 / 255, 163 / 255, 84 / 255),
    (0 / 255, 109 / 255, 44 / 255),
]
PROJECT_COLOR = (44 / 255, 127 / 255, 184 / 255)

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

    fig.text(0.04, 0.965, "Rewilding Opportunity vs Real Rewilding Network Sites",
              fontsize=20, fontweight="bold", ha="left", va="top", family="sans-serif")
    fig.text(0.04, 0.935, "England, 1km hex grid — low-conflict scenario score against 64 real, independently-chosen rewilding projects",
              fontsize=12, ha="left", va="top", family="sans-serif", color="#333333")

    # ---- Legend panel (right side) ----
    legend_x = 0.755
    ax_legend = fig.add_axes([legend_x, 0.28, 0.22, 0.57])
    ax_legend.axis("off")

    ax_legend.text(0, 1.0, "Rewilding opportunity score", fontsize=12.5, fontweight="bold", va="top", transform=ax_legend.transAxes)
    ax_legend.text(0, 0.965, "(low-conflict scenario, 0–100)", fontsize=10, va="top", color="#444444", transform=ax_legend.transAxes)

    n = len(COLORS)
    sw_h = 0.052
    start_y = 0.905
    for i, c in enumerate(COLORS):
        y = start_y - i * (sw_h + 0.011)
        ax_legend.add_patch(mpatches.Rectangle((0, y - sw_h), 0.14, sw_h, transform=ax_legend.transAxes,
                                                facecolor=c, edgecolor="#999999", linewidth=0.5))
        label = f"{BREAKS[i]:.1f} – {BREAKS[i + 1]:.1f}"
        ax_legend.text(0.19, y - sw_h / 2, label, fontsize=10.5, va="center", transform=ax_legend.transAxes)

    sep_y = start_y - n * (sw_h + 0.011) - 0.03
    ax_legend.plot([0, 0.6], [sep_y, sep_y], color="#cccccc", linewidth=0.8, transform=ax_legend.transAxes)

    pt_y = sep_y - 0.065
    ax_legend.scatter([0.07], [pt_y], s=140, marker="^", color=PROJECT_COLOR, edgecolor="#141414", linewidth=0.8,
                       transform=ax_legend.transAxes, zorder=5)
    ax_legend.text(0.19, pt_y, "Real Rewilding Network site", fontsize=10.5, va="center", transform=ax_legend.transAxes)
    ax_legend.text(0.19, pt_y - 0.042, "(n = 64, England, visible locations)", fontsize=9, va="center", color="#444444",
                   transform=ax_legend.transAxes)

    # ---- Key finding callout ----
    finding_y = pt_y - 0.12
    ax_legend.add_patch(mpatches.FancyBboxPatch((0, finding_y - 0.40), 0.92, 0.40,
                                                 boxstyle="round,pad=0.01,rounding_size=0.01",
                                                 transform=ax_legend.transAxes,
                                                 facecolor="#f4f4f0", edgecolor="#cccccc", linewidth=0.6))
    finding_text = (
        "Finding: real sites beat chance\n"
        "under low-conflict, not nature-first.\n\n"
        "For the hex nearest each real\n"
        "site, mean national percentile:\n\n"
        "Nature-first:    50.1 (chance)\n"
        "Balanced:        53.5\n"
        "Low-conflict:    60.5\n\n"
        "Real sites are 1.5x more likely\n"
        "than chance to land in this\n"
        "model's own top decile under\n"
        "the low-conflict lens shown here."
    )
    ax_legend.text(0.05, finding_y - 0.02, finding_text, fontsize=9.2, va="top", ha="left",
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
             "Data: rewilding-suitability canonical v6 hex scores; Rewilding Network project directory "
             "(Rewilding Britain, live API). CRS: EPSG:27700 (British National Grid).\n"
             "Rendered with QGIS 3.44 (native:rasterize) · Laurence Pengelly · github.com/LarryP123/Rewilding-Project",
             fontsize=8.3, ha="left", va="bottom", color="#555555", family="sans-serif")

    fig.savefig(OUT_PNG, facecolor="white")
    print("wrote", OUT_PNG)


if __name__ == "__main__":
    main()
