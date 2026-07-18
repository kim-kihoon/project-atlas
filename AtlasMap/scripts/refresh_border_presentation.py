"""Rebuild continuous QGIS border render chains from validated logical sides."""

from collections import defaultdict
import json
from pathlib import Path
import sys

from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis.core import (
    QgsCategorizedSymbolRenderer,
    QgsFeature,
    QgsField,
    QgsFields,
    QgsFillSymbol,
    QgsLineSymbol,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingOutputFile,
    QgsProcessingParameterFile,
    QgsProject,
    QgsRendererCategory,
    QgsSingleSymbolRenderer,
    QgsVectorLayer,
)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_east_asia_map import (  # noqa: E402
    memory_layer,
    merged_line_chains,
    render_preview,
    resolve,
    write_gpkg_layer,
)


CONFIG = "CONFIG"
OUTPUT_PROJECT = "OUTPUT_PROJECT"
OUTPUT_PREVIEW = "OUTPUT_PREVIEW"


def tr(text):
    return QCoreApplication.translate("AtlasBorderPresentation", text)


class AtlasBorderPresentation(QgsProcessingAlgorithm):
    def name(self):
        return "atlas_refresh_border_presentation"

    def displayName(self):
        return tr("Refresh Atlas continuous border presentation")

    def group(self):
        return tr("Atlas")

    def groupId(self):
        return "atlas"

    def shortHelpString(self):
        return tr("Line-merges validated logical sides and refreshes the QGIS project and preview.")

    def createInstance(self):
        return AtlasBorderPresentation()

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFile(CONFIG, tr("atlas_east_asia.json"), extension="json")
        )
        self.addOutput(QgsProcessingOutputFile(OUTPUT_PROJECT, tr("QGIS project")))
        self.addOutput(QgsProcessingOutputFile(OUTPUT_PREVIEW, tr("Preview PNG")))

    def processAlgorithm(self, parameters, context, feedback):
        config_path = Path(self.parameterAsFile(parameters, CONFIG, context)).resolve()
        root = config_path.parent.parent.resolve()
        settings = json.loads(config_path.read_text(encoding="utf-8"))
        gpkg = resolve(root, settings["outputs"]["geopackage"])
        project_path = resolve(root, settings["outputs"]["project"])
        preview_path = resolve(root, settings["outputs"]["preview"])
        raw_borders = QgsVectorLayer(
            f"{gpkg}|layername=admin1_tile_borders", "raw_admin_borders", "ogr"
        )
        raw_capitals = QgsVectorLayer(
            f"{gpkg}|layername=capital_tile_outlines", "raw_capital_outlines", "ogr"
        )
        if not raw_borders.isValid() or not raw_capitals.isValid():
            raise QgsProcessingException("Validated logical-side layers are unavailable")

        border_groups = defaultdict(list)
        for feature in raw_borders.getFeatures():
            edge_type = str(feature["edge_type"] or "")
            if edge_type == "admin":
                boundary_key = ":".join(
                    sorted((str(feature["admin_a"]), str(feature["admin_b"])))
                )
            elif edge_type == "country":
                boundary_key = ":".join(
                    sorted((str(feature["country_a"]), str(feature["country_b"])))
                )
            else:
                boundary_key = str(feature["country_a"] or "")
            border_groups[(edge_type, boundary_key)].append(feature.geometry())
        snap_tolerance = float(
            settings["map_styling"]["border_chain_snap_tolerance_m"]
        )
        border_chains = merged_line_chains(border_groups, snap_tolerance)
        border_fields = QgsFields()
        for name, kind in (
            ("chain_id", QVariant.String), ("edge_type", QVariant.String),
            ("boundary_key", QVariant.String), ("side_count", QVariant.Int),
        ):
            border_fields.append(QgsField(name, kind))
        border_layer = memory_layer(
            "LineString", raw_borders.crs(), "admin1_border_render", border_fields
        )
        features = []
        for group_key, part_index, side_count, geometry in border_chains:
            edge_type, boundary_key = group_key
            feature = QgsFeature(border_layer.fields())
            feature.setGeometry(geometry)
            feature.setAttributes(
                [f"{edge_type}:{boundary_key}:{part_index}", edge_type, boundary_key, side_count]
            )
            features.append(feature)
        border_layer.dataProvider().addFeatures(features)
        write_gpkg_layer(border_layer, gpkg, "admin1_border_render", False)

        capital_groups = defaultdict(list)
        for feature in raw_capitals.getFeatures():
            capital_groups[str(feature["capital_code"] or "")].append(feature.geometry())
        capital_chains = merged_line_chains(capital_groups, snap_tolerance)
        capital_fields = QgsFields()
        for name, kind in (
            ("chain_id", QVariant.String), ("capital_code", QVariant.String),
            ("side_count", QVariant.Int),
        ):
            capital_fields.append(QgsField(name, kind))
        capital_layer = memory_layer(
            "LineString", raw_capitals.crs(), "capital_outline_render", capital_fields
        )
        features = []
        for capital_code, part_index, side_count, geometry in capital_chains:
            feature = QgsFeature(capital_layer.fields())
            feature.setGeometry(geometry)
            feature.setAttributes([f"{capital_code}:{part_index}", capital_code, side_count])
            features.append(feature)
        capital_layer.dataProvider().addFeatures(features)
        write_gpkg_layer(capital_layer, gpkg, "capital_outline_render", False)

        project = QgsProject.instance()
        project.clear()
        if not project.read(str(project_path)):
            raise QgsProcessingException(f"Cannot read project: {project_path}")
        project_borders = project.mapLayersByName("Game admin borders")
        project_capitals = project.mapLayersByName("Capital outlines")
        project_tiles = project.mapLayersByName("East Asia game tiles")
        project_admin_labels = project.mapLayersByName("Admin names and tile counts")
        if not all((project_borders, project_capitals, project_tiles, project_admin_labels)):
            raise QgsProcessingException("Expected QGIS presentation layers are missing")
        project_border = project_borders[0]
        project_capital = project_capitals[0]
        project_tile = project_tiles[0]
        project_admin_label = project_admin_labels[0]
        project_border.setDataSource(
            f"{gpkg}|layername=admin1_border_render", "Game admin borders", "ogr"
        )
        project_capital.setDataSource(
            f"{gpkg}|layername=capital_outline_render", "Capital outlines", "ogr"
        )

        style = settings["map_styling"]
        labels = {"admin": "Admin border", "country": "Country border", "exterior": "Exterior"}
        categories = []
        for edge_type, color_key, width_key in (
            ("admin", "admin_border_color", "admin_border_width_mm"),
            ("country", "country_border_color", "country_border_width_mm"),
            ("exterior", "exterior_border_color", "exterior_border_width_mm"),
        ):
            categories.append(
                QgsRendererCategory(
                    edge_type,
                    QgsLineSymbol.createSimple(
                        {
                            "line_color": style[color_key],
                            "line_width": str(style[width_key]),
                            "capstyle": style["border_cap_style"],
                            "joinstyle": style["border_join_style"],
                        }
                    ),
                    labels[edge_type],
                )
            )
        project_border.setRenderer(QgsCategorizedSymbolRenderer("edge_type", categories))
        project_capital.setRenderer(
            QgsSingleSymbolRenderer(
                QgsLineSymbol.createSimple(
                    {
                        "line_color": settings["city_classification"]["colors"]["capital_outline"],
                        "line_width": str(style["capital_border_width_mm"]),
                        "capstyle": style["border_cap_style"],
                        "joinstyle": style["border_join_style"],
                    }
                )
            )
        )
        if not project.write(str(project_path)):
            raise QgsProcessingException(f"Cannot write project: {project_path}")

        project_tile.setLabelsEnabled(False)
        project_admin_label.setLabelsEnabled(False)
        fill_categories = []
        colors = settings["city_classification"]["colors"]
        for value in ("admin", "city", "metropolis"):
            fill_categories.append(
                QgsRendererCategory(
                    value,
                    QgsFillSymbol.createSimple({"color": colors[value], "outline_style": "no"}),
                    value,
                )
            )
        project_tile.setRenderer(QgsCategorizedSymbolRenderer("map_class", fill_categories))
        render_preview(
            [project_admin_label, project_capital, project_border, project_tile],
            preview_path,
            project.crs(),
            project.transformContext(),
        )
        feedback.pushInfo(
            f"Merged {raw_borders.featureCount()} admin sides into {len(border_chains)} chains"
        )
        feedback.pushInfo(
            f"Merged {raw_capitals.featureCount()} capital sides into {len(capital_chains)} chains"
        )
        return {OUTPUT_PROJECT: str(project_path), OUTPUT_PREVIEW: str(preview_path)}
