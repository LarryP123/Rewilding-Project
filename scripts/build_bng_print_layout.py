"""Build a native QGIS Print Layout for the BNG alignment map and export it.

Unlike ``compose_bng_map.py`` (which rasterizes the canvas with ``native:rasterize``
and then draws the title/legend/scale bar/callout with matplotlib), this builds
the whole composition as an actual ``QgsPrintLayout`` inside
``outputs/qgis/bng_alignment.qgs`` — map item, legend item, scale bar item,
north arrow item, and label items — using QGIS's own Layout Composer object
model, and saves the layout back into the project so it's on the Layouts menu
when opened in the QGIS GUI.

This is written as a QGIS Processing script algorithm (see
``processing/script/ScriptTemplate.py`` in the QGIS install) rather than a
plain PyQGIS script, and run through ``qgis_process`` rather than the full
QGIS.app GUI binary: launching the GUI app (even with ``QT_QPA_PLATFORM=offscreen``
and ``--code``) hangs indefinitely on ``QgsProject.read()`` in this sandbox —
some GUI-only startup hook blocks waiting on a dialog or network call that
never resolves offscreen. ``qgis_process`` doesn't initialize that machinery,
loads the same project+layers fine, and is also what the README's headless
rasterize workflow already relies on.

    /Applications/QGIS.app/Contents/MacOS/qgis_process run \\
        scripts/build_bng_print_layout.py -- \\
        --PROJECT_PATH=outputs/qgis/bng_alignment.qgs
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from qgis.core import (
    QgsLayoutExporter,
    QgsLayoutItemLabel,
    QgsLayoutItemLegend,
    QgsLayoutItemMap,
    QgsLayoutItemPicture,
    QgsLayoutItemScaleBar,
    QgsLayoutPoint,
    QgsLayoutSize,
    QgsPrintLayout,
    QgsProcessingAlgorithm,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsTextFormat,
    QgsUnitTypes,
)
from qgis.PyQt.QtCore import QRectF
from qgis.PyQt.QtGui import QColor, QFont

PROJECT_ROOT = Path(__file__).resolve().parents[1]
NORTH_ARROW_SVG = Path(
    "/Applications/QGIS.app/Contents/Resources/qgis/svg/arrows/NorthArrow_02.svg"
)
OUT_PDF = PROJECT_ROOT / "outputs/qgis/bng_alignment_print_layout.pdf"
OUT_PNG = PROJECT_ROOT / "outputs/qgis/bng_alignment_print_layout.png"

LAYOUT_NAME = "BNG Alignment Print Layout"
PAGE_W, PAGE_H = 297.0, 420.0  # A3 portrait, mm
MM = QgsUnitTypes.LayoutMillimeters

TITLE = "Rewilding Opportunity vs Registered Biodiversity Net Gain Sites"
SUBTITLE = (
    "England, 1km hex grid — balanced-scenario suitability score against the "
    "real BNG Gain Site Register"
)
FINDING = (
    "Finding: BNG sites track development, not ecology.\n\n"
    "Only 40% of top-100 balanced hexes sit within 10km of a site, vs 45% "
    "nationally (r = 0.10 across scenarios).\n\n"
    "Distance to urban/industrial land explains BNG proximity ~2x better "
    "(r = 0.27): 73.7% of sites sit within 2km of urban land, vs 63.0% "
    "nationally."
)
ATTRIBUTION = (
    "Data: rewilding-suitability canonical v6 hex scores; Biodiversity Gain "
    "Site Register (via The Wildlife Trusts public mirror, updated daily). "
    "CRS: EPSG:27700 (British National Grid).\n"
    "Built as a native QGIS Print Layout (QGIS 3.44, PyQGIS) - Laurence "
    "Pengelly - github.com/LarryP123/Rewilding-Project"
)


def _text_format(font: QFont, color: str) -> QgsTextFormat:
    fmt = QgsTextFormat()
    fmt.setFont(font)
    fmt.setSize(font.pointSizeF())
    fmt.setColor(QColor(color))
    return fmt


def _label(layout: QgsPrintLayout, text: str, rect: QRectF, font: QFont, color: str = "#1a1a1a") -> QgsLayoutItemLabel:
    item = QgsLayoutItemLabel(layout)
    item.setText(text)
    item.setTextFormat(_text_format(font, color))
    item.attemptSetSceneRect(rect)
    layout.addLayoutItem(item)
    return item


class BuildBngPrintLayout(QgsProcessingAlgorithm):
    def name(self) -> str:
        return "buildbngprintlayout"

    def displayName(self) -> str:
        return "Build BNG print layout"

    def group(self) -> str:
        return "Rewilding suitability"

    def groupId(self) -> str:
        return "rewildingsuitability"

    def shortHelpString(self) -> str:
        return "Builds a native QGIS Print Layout for the BNG alignment map and exports it to PDF/PNG."

    def initAlgorithm(self, config: Optional[dict[str, Any]] = None):
        pass

    def createInstance(self):
        return self.__class__()

    def processAlgorithm(
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback,
    ) -> dict[str, Any]:
        project = context.project()
        feedback.pushInfo(f"project: {project.fileName()}")

        layers_by_name = {lyr.name(): lyr for lyr in project.mapLayers().values()}
        hex_layer = layers_by_name["Rewilding Opportunity (scenario_balanced)"]
        bng_layer = layers_by_name["Registered BNG Sites"]
        boundary_layer = layers_by_name["England Boundary"]

        manager = project.layoutManager()
        existing = manager.layoutByName(LAYOUT_NAME)
        if existing is not None:
            manager.removeLayout(existing)

        layout = QgsPrintLayout(project)
        layout.initializeDefaults()
        layout.setName(LAYOUT_NAME)
        layout.pageCollection().page(0).setPageSize(QgsLayoutSize(PAGE_W, PAGE_H, MM))

        # --- Map ---
        map_item = QgsLayoutItemMap(layout)
        map_item.attemptSetSceneRect(QRectF(10, 34, 210, 374))
        map_item.setFrameEnabled(True)
        map_item.setLayers([hex_layer, bng_layer, boundary_layer])
        extent = boundary_layer.extent()
        extent.scale(1.03)
        map_item.zoomToExtent(extent)
        layout.addLayoutItem(map_item)
        feedback.pushInfo("map item added")

        # --- Title / subtitle ---
        _label(layout, TITLE, QRectF(10, 8, 277, 12), QFont("Helvetica Neue", 20, QFont.Weight.Bold))
        _label(layout, SUBTITLE, QRectF(10, 20, 277, 10), QFont("Helvetica Neue", 11), color="#333333")

        # --- Legend ---
        legend = QgsLayoutItemLegend(layout)
        legend.setLinkedMap(map_item)
        legend.setTitle("Rewilding opportunity score")
        legend.setAutoUpdateModel(False)
        root = legend.model().rootGroup()
        legend_labels = {
            hex_layer: "Rewilding opportunity (balanced)",
            bng_layer: "Registered BNG sites",
        }
        for node_layer in list(root.findLayers()):
            layer = node_layer.layer()
            if layer not in (hex_layer, bng_layer):
                root.removeChildNode(node_layer)
            else:
                node_layer.setName(legend_labels[layer])
        legend.setResizeToContents(True)
        legend.attemptMove(QgsLayoutPoint(226, 40, MM))
        layout.addLayoutItem(legend)
        feedback.pushInfo("legend added")

        # --- North arrow ---
        north = QgsLayoutItemPicture(layout)
        north.setPicturePath(str(NORTH_ARROW_SVG))
        north.attemptSetSceneRect(QRectF(260, 200, 14, 20))
        layout.addLayoutItem(north)

        # --- Scale bar ---
        scalebar = QgsLayoutItemScaleBar(layout)
        scalebar.setLinkedMap(map_item)
        scalebar.setStyle("Line Ticks Up")
        scalebar.setUnits(QgsUnitTypes.DistanceKilometers)
        scalebar.setUnitLabel("km")
        scalebar.setNumberOfSegments(3)
        scalebar.setNumberOfSegmentsLeft(0)
        scalebar.setUnitsPerSegment(50)
        scalebar.setTextFormat(_text_format(QFont("Helvetica Neue", 8), "#1a1a1a"))
        scalebar.applyDefaultSize()
        scalebar.update()
        scalebar.attemptMove(QgsLayoutPoint(226, 232, MM))
        scalebar.attemptResize(QgsLayoutSize(60, 12, MM))
        layout.addLayoutItem(scalebar)
        feedback.pushInfo("scalebar added")

        # --- Finding callout ---
        finding_box = QgsLayoutItemLabel(layout)
        finding_box.setText(FINDING)
        finding_box.setTextFormat(_text_format(QFont("Helvetica Neue", 10), "#1a1a1a"))
        finding_box.setBackgroundEnabled(True)
        finding_box.setBackgroundColor(QColor("#f4f4f0"))
        finding_box.setFrameEnabled(True)
        finding_box.setFrameStrokeColor(QColor("#cccccc"))
        finding_box.setMargin(4)
        finding_box.attemptSetSceneRect(QRectF(226, 254, 61, 130))
        layout.addLayoutItem(finding_box)

        # --- Attribution ---
        _label(
            layout,
            ATTRIBUTION,
            QRectF(10, 410, 277, 8),
            QFont("Helvetica Neue", 7),
            color="#444444",
        )

        manager.addLayout(layout)
        project.write()
        feedback.pushInfo(f"saved layout '{LAYOUT_NAME}' into {project.fileName()}")

        exporter = QgsLayoutExporter(layout)
        pdf_settings = QgsLayoutExporter.PdfExportSettings()
        feedback.pushInfo("exporting pdf...")
        exporter.exportToPdf(str(OUT_PDF), pdf_settings)

        png_settings = QgsLayoutExporter.ImageExportSettings()
        png_settings.dpi = 300
        feedback.pushInfo("exporting png...")
        exporter.exportToImage(str(OUT_PNG), png_settings)
        feedback.pushInfo(f"exported {OUT_PDF} and {OUT_PNG}")

        return {}
