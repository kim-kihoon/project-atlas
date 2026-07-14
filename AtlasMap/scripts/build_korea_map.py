"""QGIS Processing script that builds the Atlas Republic of Korea map."""

from collections import Counter
from datetime import datetime, timezone
import csv
import json
import math
from pathlib import Path

from qgis.PyQt.QtCore import QCoreApplication, QSize, QVariant
from qgis.PyQt.QtGui import QColor
from qgis.core import (
    Qgis,
    QgsCategorizedSymbolRenderer,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeature,
    QgsField,
    QgsFields,
    QgsFillSymbol,
    QgsGeometry,
    QgsLabelingEngineSettings,
    QgsLineSymbol,
    QgsMapRendererParallelJob,
    QgsMapSettings,
    QgsPalLayerSettings,
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingOutputFile,
    QgsProcessingParameterFile,
    QgsProject,
    QgsProperty,
    QgsRectangle,
    QgsRendererCategory,
    QgsSingleSymbolRenderer,
    QgsTextBufferSettings,
    QgsTextFormat,
    QgsVectorFileWriter,
    QgsVectorLayer,
    QgsVectorLayerSimpleLabeling,
)


CONFIG = "CONFIG"
OUTPUT_GPKG = "OUTPUT_GPKG"
OUTPUT_PROJECT = "OUTPUT_PROJECT"
OUTPUT_PREVIEW = "OUTPUT_PREVIEW"
OUTPUT_REPORT = "OUTPUT_REPORT"


def tr(text):
    return QCoreApplication.translate("AtlasKoreaBuild", text)


def resolve(root, relative_path):
    path = (root / relative_path).resolve()
    if root != path and root not in path.parents:
        raise QgsProcessingException(f"Path escapes project root: {relative_path}")
    return path


def make_hexagon(cx, cy, side, orientation):
    start_angle = 30.0 if orientation == "pointy_top" else 0.0
    points = []
    from qgis.core import QgsPointXY

    for index in range(6):
        angle = math.radians(start_angle + index * 60.0)
        points.append(QgsPointXY(cx + side * math.cos(angle), cy + side * math.sin(angle)))
    points.append(points[0])
    return QgsGeometry.fromPolygonXY([points])


def allocate_tiles(candidates, admins, requested, feedback):
    """Select by land coverage, assign by dominant overlap, then satisfy minima."""
    eligible = [i for i, item in enumerate(candidates) if item["land_area"] > 0]
    if len(eligible) < requested:
        raise QgsProcessingException(
            f"Only {len(eligible)} candidates intersect land; {requested} are required"
        )
    selected = sorted(
        eligible,
        key=lambda i: (-candidates[i]["land_area"], candidates[i]["tile_id"]),
    )[:requested]
    assignments = {}
    for index in selected:
        overlaps = candidates[index]["overlaps"]
        assignments[index] = sorted(overlaps, key=lambda code: (-overlaps[code], code))[0]

    minimums = {admin["code"]: int(admin.get("minimum_tiles", 0)) for admin in admins}
    counts = Counter(assignments.values())
    minimum_exceptions = {}
    deficits = [
        code for code, minimum in minimums.items()
        for _ in range(max(0, minimum - counts.get(code, 0)))
    ]
    # Handle the most spatially constrained missing admins first.
    deficits.sort(
        key=lambda code: (
            sum(1 for i in selected if candidates[i]["overlaps"].get(code, 0) > 0),
            code,
        )
    )
    for code in deficits:
        options = []
        for index in selected:
            candidate = candidates[index]
            required_overlap = candidate["overlaps"].get(code, 0.0)
            if required_overlap <= 0 or assignments[index] == code:
                continue
            donor = assignments[index]
            if counts[donor] <= minimums.get(donor, 0):
                continue
            donor_overlap = candidate["overlaps"].get(donor, 0.0)
            required_share = required_overlap / candidate["geometry"].area()
            regret = donor_overlap - required_overlap
            options.append((-required_share, regret, -candidate["land_area"], candidate["tile_id"], index))
        if not options:
            raise QgsProcessingException(
                f"Cannot satisfy minimum representation for {code} with the selected {requested} tiles"
            )
        _, _, _, _, index = sorted(options)[0]
        donor = assignments[index]
        assignments[index] = code
        counts[donor] -= 1
        counts[code] += 1
        minimum_exceptions[index] = (donor, code)

    feedback.pushInfo(
        f"Selected {requested} tiles by land overlap; "
        f"applied {len(minimum_exceptions)} minimum-representation exceptions"
    )
    return assignments, minimum_exceptions


def memory_layer(geometry, crs, name, fields):
    layer = QgsVectorLayer(f"{geometry}?crs={crs.authid()}", name, "memory")
    provider = layer.dataProvider()
    provider.addAttributes(fields)
    layer.updateFields()
    return layer


def write_gpkg_layer(layer, path, layer_name, first):
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "GPKG"
    options.layerName = layer_name
    options.fileEncoding = "UTF-8"
    options.actionOnExistingFile = (
        QgsVectorFileWriter.CreateOrOverwriteFile
        if first
        else QgsVectorFileWriter.CreateOrOverwriteLayer
    )
    result = QgsVectorFileWriter.writeAsVectorFormatV3(
        layer, str(path), QgsProject.instance().transformContext(), options
    )
    if result[0] != QgsVectorFileWriter.NoError:
        raise QgsProcessingException(f"Failed to write {layer_name}: {result}")


def load_overrides(path):
    if not path.exists():
        return {}
    result = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            tile_id = (row.get("tile_id") or "").strip()
            code = (row.get("target_admin1_code") or "").strip()
            if tile_id and code:
                result[tile_id] = (code, (row.get("reason") or "").strip())
    return result


def render_preview(layers, output_path):
    settings = QgsMapSettings()
    settings.setLayers(layers)
    extent = layers[-1].extent()
    extent.grow(max(extent.width(), extent.height()) * 0.05)
    settings.setExtent(extent)
    settings.setOutputSize(QSize(1400, 1600))
    settings.setBackgroundColor(QColor("#f7fbff"))
    settings.setOutputDpi(120)
    settings.setFlag(QgsMapSettings.Antialiasing, True)
    job = QgsMapRendererParallelJob(settings)
    job.start()
    job.waitForFinished()
    image = job.renderedImage()
    if not image.save(str(output_path), "PNG"):
        raise QgsProcessingException(f"Failed to save preview: {output_path}")


class AtlasKoreaBuild(QgsProcessingAlgorithm):
    def name(self):
        return "atlas_korea_build"

    def displayName(self):
        return tr("Build Atlas Korea hex map")

    def group(self):
        return tr("Atlas")

    def groupId(self):
        return "atlas"

    def shortHelpString(self):
        return tr("Builds the deterministic 166-tile Korea GeoPackage, QGIS project, report and preview.")

    def createInstance(self):
        return AtlasKoreaBuild()

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFile(CONFIG, tr("atlas_korea.json"), extension="json")
        )
        self.addOutput(QgsProcessingOutputFile(OUTPUT_GPKG, tr("Output GeoPackage")))
        self.addOutput(QgsProcessingOutputFile(OUTPUT_PROJECT, tr("Output QGIS project")))
        self.addOutput(QgsProcessingOutputFile(OUTPUT_PREVIEW, tr("Output preview")))
        self.addOutput(QgsProcessingOutputFile(OUTPUT_REPORT, tr("Allocation report")))

    def processAlgorithm(self, parameters, context, feedback):
        config_path = Path(self.parameterAsFile(parameters, CONFIG, context)).resolve()
        if not config_path.exists():
            raise QgsProcessingException(f"Config does not exist: {config_path}")
        root = config_path.parent.parent.resolve()
        settings = json.loads(config_path.read_text(encoding="utf-8"))
        admins = settings["admin1"]
        admin_by_code = {admin["code"]: admin for admin in admins}
        expected_total = int(settings["grid"]["target_tile_count"])
        if sum(int(item.get("minimum_tiles", 0)) for item in admins) > expected_total:
            raise QgsProcessingException("Configured admin minimums exceed target tile count")

        source_path = resolve(root, settings["source"]["path"])
        gpkg_path = resolve(root, settings["outputs"]["geopackage"])
        project_path = resolve(root, settings["outputs"]["project"])
        preview_path = resolve(root, settings["outputs"]["preview"])
        report_path = resolve(root, settings["outputs"]["allocation_report"])
        override_path = resolve(root, "overrides/tile_assignment_overrides.csv")
        for path in (gpkg_path, project_path, preview_path, report_path):
            path.parent.mkdir(parents=True, exist_ok=True)

        source_layer = QgsVectorLayer(str(source_path), "natural_earth_admin1", "ogr")
        if not source_layer.isValid():
            raise QgsProcessingException(f"Invalid source layer: {source_path}")
        target_crs = QgsCoordinateReferenceSystem(settings["crs"])
        if not target_crs.isValid():
            raise QgsProcessingException(f"Invalid target CRS: {settings['crs']}")
        transform = QgsCoordinateTransform(source_layer.crs(), target_crs, context.transformContext())

        admin_fields = QgsFields()
        for name, kind in (
            ("admin1_code", QVariant.String),
            ("admin1_name_ko", QVariant.String),
            ("admin1_name_en", QVariant.String),
            ("source_name", QVariant.String),
            ("source_year", QVariant.Int),
            ("tile_target", QVariant.Int),
            ("tile_minimum", QVariant.Int),
            ("tile_count", QVariant.Int),
        ):
            admin_fields.append(QgsField(name, kind))
        admin_layer = memory_layer("MultiPolygon", target_crs, "admin1_source", admin_fields)
        admin_geometries = {}
        admin_source_names = {}
        filter_field = settings["source"]["country_filter_field"]
        filter_value = settings["source"]["country_filter_value"]
        for feature in source_layer.getFeatures():
            if str(feature[filter_field]) != filter_value:
                continue
            code = str(feature["iso_3166_2"])
            if code not in admin_by_code:
                continue
            geometry = QgsGeometry(feature.geometry())
            geometry.transform(transform)
            if not geometry.isGeosValid():
                geometry = geometry.makeValid()
            if geometry.isEmpty():
                raise QgsProcessingException(f"Empty admin geometry after repair: {code}")
            admin_geometries[code] = geometry
            admin_source_names[code] = str(feature["name_en"])
        missing = sorted(set(admin_by_code) - set(admin_geometries))
        if missing or len(admin_geometries) != 17:
            raise QgsProcessingException(
                f"Expected all 17 configured admin areas. Missing={missing}, found={len(admin_geometries)}"
            )

        land = QgsGeometry.unaryUnion(list(admin_geometries.values()))
        if not land.isGeosValid():
            land = land.makeValid()
        feedback.pushInfo(f"Loaded and reprojected {len(admin_geometries)} admin areas")
        feedback.setProgress(10)

        grid = settings["grid"]
        side = float(grid["side_length_m"])
        orientation = grid["orientation"]
        if orientation not in ("pointy_top", "flat_top"):
            raise QgsProcessingException(f"Unsupported orientation: {orientation}")
        extent = land.boundingBox()
        buffer_distance = float(grid["extent_buffer_m"])
        xmin, xmax = extent.xMinimum() - buffer_distance, extent.xMaximum() + buffer_distance
        ymin, ymax = extent.yMinimum() - buffer_distance, extent.yMaximum() + buffer_distance
        origin_x, origin_y = float(grid["origin_x"]), float(grid["origin_y"])
        if orientation == "pointy_top":
            column_step = math.sqrt(3.0) * side
            row_step = 1.5 * side
        else:
            column_step = 1.5 * side
            row_step = math.sqrt(3.0) * side
        row_min = math.floor((ymin - origin_y) / row_step) - 2
        row_max = math.ceil((ymax - origin_y) / row_step) + 2
        col_min = math.floor((xmin - origin_x) / column_step) - 2
        col_max = math.ceil((xmax - origin_x) / column_step) + 2

        candidates = []
        processing_extent = QgsRectangle(xmin, ymin, xmax, ymax)
        for row in range(row_min, row_max + 1):
            for col in range(col_min, col_max + 1):
                if orientation == "pointy_top":
                    cx = origin_x + col * column_step + (row & 1) * column_step / 2.0
                    cy = origin_y + row * row_step
                else:
                    cx = origin_x + col * column_step
                    cy = origin_y + row * row_step + (col & 1) * row_step / 2.0
                geometry = make_hexagon(cx, cy, side, orientation)
                if not geometry.boundingBox().intersects(processing_extent):
                    continue
                overlaps = {}
                for code, admin_geometry in admin_geometries.items():
                    if not geometry.boundingBox().intersects(admin_geometry.boundingBox()):
                        continue
                    area = geometry.intersection(admin_geometry).area()
                    if area >= float(grid["candidate_min_overlap_m2"]):
                        overlaps[code] = area
                land_area = sum(overlaps.values())
                tile_id = f"KOR_{orientation[0].upper()}_R{row + 100000:06d}_C{col + 100000:06d}"
                candidates.append(
                    {
                        "tile_id": tile_id,
                        "row": row,
                        "col": col,
                        "cx": cx,
                        "cy": cy,
                        "geometry": geometry,
                        "overlaps": overlaps,
                        "land_area": land_area,
                    }
                )
        feedback.pushInfo(
            f"Generated {len(candidates)} candidates; "
            f"{sum(1 for item in candidates if item['land_area'] > 0)} intersect land"
        )
        feedback.setProgress(40)

        assignments, minimum_exceptions = allocate_tiles(
            candidates, admins, expected_total, feedback
        )
        overrides = load_overrides(override_path)
        override_reasons = {}
        for candidate_index, code in list(assignments.items()):
            tile_id = candidates[candidate_index]["tile_id"]
            if tile_id not in overrides:
                continue
            target_code, reason = overrides[tile_id]
            if target_code not in admin_by_code:
                raise QgsProcessingException(f"Override for {tile_id} uses unknown admin code {target_code}")
            assignments[candidate_index] = target_code
            override_reasons[tile_id] = reason

        selected_indexes = sorted(assignments, key=lambda i: candidates[i]["tile_id"])
        selected_ids = {candidates[i]["tile_id"] for i in selected_indexes}
        neighbors = {tile_id: [] for tile_id in selected_ids}
        admin_border_records = []
        for position, first_index in enumerate(selected_indexes):
            first = candidates[first_index]
            for second_index in selected_indexes[position + 1 :]:
                second = candidates[second_index]
                if not first["geometry"].boundingBox().intersects(second["geometry"].boundingBox()):
                    continue
                # Adjacent regular grid cells intersect in a line; polygon
                # intersection therefore gives the shared edge directly.
                shared = first["geometry"].intersection(second["geometry"]).length()
                if shared >= side * 0.5:
                    neighbors[first["tile_id"]].append(second["tile_id"])
                    neighbors[second["tile_id"]].append(first["tile_id"])
                    if assignments[first_index] != assignments[second_index]:
                        admin_border_records.append(
                            (
                                first["geometry"].intersection(second["geometry"]),
                                first["tile_id"], second["tile_id"],
                                assignments[first_index], assignments[second_index],
                            )
                        )
        for value in neighbors.values():
            value.sort()

        candidate_fields = QgsFields()
        for name, kind in (
            ("candidate_id", QVariant.String),
            ("grid_row", QVariant.Int),
            ("grid_col", QVariant.Int),
            ("land_area_km2", QVariant.Double),
            ("land_ratio", QVariant.Double),
            ("best_admin", QVariant.String),
            ("best_overlap", QVariant.Double),
            ("selected", QVariant.Bool),
            ("assigned_admin", QVariant.String),
            ("assignment_method", QVariant.String),
            ("scores_json", QVariant.String),
        ):
            candidate_fields.append(QgsField(name, kind))
        candidate_layer = memory_layer("Polygon", target_crs, "hex_candidates", candidate_fields)
        candidate_features = []
        hex_area = make_hexagon(0, 0, side, orientation).area()
        for index, candidate in enumerate(candidates):
            best_admin = max(candidate["overlaps"], key=candidate["overlaps"].get) if candidate["overlaps"] else None
            best_overlap = candidate["overlaps"].get(best_admin, 0.0) if best_admin else 0.0
            feature = QgsFeature(candidate_layer.fields())
            feature.setGeometry(candidate["geometry"])
            feature.setAttributes(
                [
                    candidate["tile_id"], candidate["row"], candidate["col"],
                    candidate["land_area"] / 1_000_000.0,
                    candidate["land_area"] / hex_area,
                    best_admin, best_overlap / 1_000_000.0,
                    index in assignments, assignments.get(index),
                    (
                        "manual_override" if candidate["tile_id"] in override_reasons
                        else "minimum_representation" if index in minimum_exceptions
                        else "dominant_overlap"
                    ) if index in assignments else None,
                    json.dumps(
                        {code: round(area / 1_000_000.0, 6) for code, area in sorted(candidate["overlaps"].items())},
                        ensure_ascii=False, separators=(",", ":"),
                    ),
                ]
            )
            candidate_features.append(feature)
        candidate_layer.dataProvider().addFeatures(candidate_features)

        tile_fields = QgsFields()
        field_specs = [
            ("tile_id", QVariant.String), ("country_iso3", QVariant.String),
            ("admin1_code", QVariant.String), ("admin1_name_ko", QVariant.String),
            ("admin1_name_en", QVariant.String), ("area_km2", QVariant.Double),
            ("land_ratio", QVariant.Double), ("is_coastal", QVariant.Bool),
            ("center_x", QVariant.Double), ("center_y", QVariant.Double),
            ("neighbor_ids", QVariant.String), ("population", QVariant.LongLong),
            ("city_name_ko", QVariant.String), ("city_name_en", QVariant.String),
            ("city_class", QVariant.String), ("is_capital", QVariant.Bool),
            ("district_slots", QVariant.Int), ("district_1", QVariant.String),
            ("district_2", QVariant.String), ("district_3", QVariant.String),
            ("primary_industry", QVariant.String), ("terrain", QVariant.String),
            ("source_year", QVariant.Int), ("manual_override", QVariant.Bool),
            ("assignment_method", QVariant.String),
            ("overlap_km2", QVariant.Double), ("assignment_score", QVariant.Double),
        ]
        for name, kind in field_specs:
            tile_fields.append(QgsField(name, kind))
        tile_layer = memory_layer("Polygon", target_crs, "korea_tiles", tile_fields)
        tile_features = []
        counts = Counter(assignments.values())
        for index in selected_indexes:
            candidate = candidates[index]
            code = assignments[index]
            admin = admin_by_code[code]
            overlap = candidate["overlaps"].get(code, 0.0)
            feature = QgsFeature(tile_layer.fields())
            feature.setGeometry(candidate["geometry"])
            values = {
                "tile_id": candidate["tile_id"], "country_iso3": settings["country"]["iso3"],
                "admin1_code": code, "admin1_name_ko": admin["name_ko"],
                "admin1_name_en": admin["name_en"], "area_km2": candidate["geometry"].area() / 1_000_000.0,
                "land_ratio": candidate["land_area"] / candidate["geometry"].area(),
                "is_coastal": candidate["land_area"] / candidate["geometry"].area() < 0.999,
                "center_x": candidate["cx"], "center_y": candidate["cy"],
                "neighbor_ids": json.dumps(neighbors[candidate["tile_id"]], separators=(",", ":")),
                "source_year": int(settings["source"]["source_year"]),
                "manual_override": candidate["tile_id"] in override_reasons,
                "assignment_method": (
                    "manual_override" if candidate["tile_id"] in override_reasons
                    else "minimum_representation" if index in minimum_exceptions
                    else "dominant_overlap"
                ),
                "overlap_km2": overlap / 1_000_000.0,
                "assignment_score": overlap / candidate["geometry"].area(),
            }
            feature.setAttributes([values.get(field.name()) for field in tile_layer.fields()])
            tile_features.append(feature)
        tile_layer.dataProvider().addFeatures(tile_features)

        # Add admin features after final counts are known.
        admin_features = []
        for admin in admins:
            code = admin["code"]
            feature = QgsFeature(admin_layer.fields())
            feature.setGeometry(admin_geometries[code])
            feature.setAttributes(
                [code, admin["name_ko"], admin["name_en"], admin_source_names[code],
                 int(settings["source"]["source_year"]), int(admin["target_tiles"]),
                 int(admin.get("minimum_tiles", 0)), counts[code]]
            )
            admin_features.append(feature)
        admin_layer.dataProvider().addFeatures(admin_features)

        city_fields = QgsFields()
        for name, kind in (
            ("city_id", QVariant.String), ("city_name_ko", QVariant.String),
            ("city_name_en", QVariant.String), ("population", QVariant.LongLong),
            ("city_class", QVariant.String), ("is_capital", QVariant.Bool),
            ("source_year", QVariant.Int), ("source_url", QVariant.String),
        ):
            city_fields.append(QgsField(name, kind))
        city_layer = memory_layer("Point", target_crs, "city_markers", city_fields)

        border_fields = QgsFields()
        for name, kind in (
            ("tile_id_a", QVariant.String), ("tile_id_b", QVariant.String),
            ("admin_a", QVariant.String), ("admin_b", QVariant.String),
        ):
            border_fields.append(QgsField(name, kind))
        border_layer = memory_layer("LineString", target_crs, "admin1_tile_borders", border_fields)
        border_features = []
        for geometry, tile_a, tile_b, admin_a, admin_b in admin_border_records:
            feature = QgsFeature(border_layer.fields())
            feature.setGeometry(geometry)
            feature.setAttributes([tile_a, tile_b, admin_a, admin_b])
            border_features.append(feature)
        border_layer.dataProvider().addFeatures(border_features)

        coast_fields = QgsFields()
        coast_fields.append(QgsField("tile_id", QVariant.String))
        coast_layer = memory_layer("LineString", target_crs, "coastal_tile_outlines", coast_fields)
        coast_features = []
        for index in selected_indexes:
            candidate = candidates[index]
            if candidate["land_area"] / candidate["geometry"].area() >= 0.999:
                continue
            ring = candidate["geometry"].asPolygon()[0]
            feature = QgsFeature(coast_layer.fields())
            feature.setGeometry(QgsGeometry.fromPolylineXY(ring))
            feature.setAttributes([candidate["tile_id"]])
            coast_features.append(feature)
        coast_layer.dataProvider().addFeatures(coast_features)

        write_gpkg_layer(admin_layer, gpkg_path, "admin1_source", True)
        write_gpkg_layer(candidate_layer, gpkg_path, "hex_candidates", False)
        write_gpkg_layer(tile_layer, gpkg_path, "korea_tiles", False)
        write_gpkg_layer(city_layer, gpkg_path, "city_markers", False)
        write_gpkg_layer(border_layer, gpkg_path, "admin1_tile_borders", False)
        write_gpkg_layer(coast_layer, gpkg_path, "coastal_tile_outlines", False)
        feedback.pushInfo(f"Wrote GeoPackage: {gpkg_path}")
        feedback.setProgress(88)

        # Reload persisted layers so the project contains relative GeoPackage paths.
        persisted_tiles = QgsVectorLayer(f"{gpkg_path}|layername=korea_tiles", "Korea game tiles", "ogr")
        persisted_admin = QgsVectorLayer(f"{gpkg_path}|layername=admin1_source", "Real admin-1 reference", "ogr")
        persisted_admin_labels = QgsVectorLayer(f"{gpkg_path}|layername=admin1_source", "Admin names and tile counts", "ogr")
        persisted_candidates = QgsVectorLayer(f"{gpkg_path}|layername=hex_candidates", "Hex candidates", "ogr")
        persisted_cities = QgsVectorLayer(f"{gpkg_path}|layername=city_markers", "City markers", "ogr")
        persisted_borders = QgsVectorLayer(f"{gpkg_path}|layername=admin1_tile_borders", "Game admin borders", "ogr")
        persisted_coast = QgsVectorLayer(f"{gpkg_path}|layername=coastal_tile_outlines", "Coastal tile outlines", "ogr")
        for layer in (
            persisted_tiles, persisted_admin, persisted_admin_labels, persisted_candidates,
            persisted_cities, persisted_borders, persisted_coast,
        ):
            if not layer.isValid():
                raise QgsProcessingException(f"Failed to reload persisted layer: {layer.name()}")

        categories = []
        for admin in admins:
            symbol = QgsFillSymbol.createSimple(
                {"color": admin["color"], "outline_color": "#36454f", "outline_width": "0.35"}
            )
            categories.append(QgsRendererCategory(admin["code"], symbol, admin["name_ko"]))
        persisted_tiles.setRenderer(QgsCategorizedSymbolRenderer("admin1_code", categories))
        label_settings = QgsPalLayerSettings()
        label_settings.fieldName = "tile_id"
        label_settings.isExpression = False
        label_settings.scaleVisibility = True
        label_settings.maximumScale = 750000
        label_format = QgsTextFormat()
        label_format.setSize(7)
        label_format.setColor(QColor("#202020"))
        buffer_settings = QgsTextBufferSettings()
        buffer_settings.setEnabled(True)
        buffer_settings.setSize(0.8)
        buffer_settings.setColor(QColor("white"))
        label_format.setBuffer(buffer_settings)
        label_settings.setFormat(label_format)
        persisted_tiles.setLabeling(QgsVectorLayerSimpleLabeling(label_settings))
        persisted_tiles.setLabelsEnabled(True)

        admin_symbol = QgsFillSymbol.createSimple(
            {"color": "0,0,0,0", "outline_color": "#111111", "outline_width": "0.7", "outline_style": "dash"}
        )
        persisted_admin.setRenderer(QgsSingleSymbolRenderer(admin_symbol))
        admin_labels = QgsPalLayerSettings()
        admin_labels.fieldName = "admin1_name_ko || ' (' || tile_count || ')'"
        admin_labels.isExpression = True
        admin_text = QgsTextFormat()
        admin_text.setSize(10)
        admin_text.setColor(QColor("#111111"))
        admin_labels.setFormat(admin_text)
        persisted_admin.setLabelsEnabled(False)
        persisted_admin_labels.setRenderer(
            QgsSingleSymbolRenderer(
                QgsFillSymbol.createSimple({"color": "0,0,0,0", "outline_style": "no"})
            )
        )
        persisted_admin_labels.setLabeling(QgsVectorLayerSimpleLabeling(admin_labels))
        persisted_admin_labels.setLabelsEnabled(True)

        persisted_candidates.setRenderer(
            QgsSingleSymbolRenderer(
                QgsFillSymbol.createSimple(
                    {"color": "0,0,0,0", "outline_color": "#b0b0b0", "outline_width": "0.1"}
                )
            )
        )
        persisted_borders.setRenderer(
            QgsSingleSymbolRenderer(
                QgsLineSymbol.createSimple({"line_color": "#202020", "line_width": "1.1"})
            )
        )
        persisted_coast.setRenderer(
            QgsSingleSymbolRenderer(
                QgsLineSymbol.createSimple(
                    {"line_color": "#1677b8", "line_width": "0.7", "line_style": "dash"}
                )
            )
        )

        project = QgsProject()
        project.setCrs(target_crs)
        try:
            project.setFilePathStorage(Qgis.FilePathType.Relative)
        except AttributeError:
            project.setFilePathStorage(QgsProject.FilePathType.Relative)
        project.setTitle("Atlas - Republic of Korea Hex Map")
        root_node = project.layerTreeRoot()
        game_group = root_node.addGroup("Game Map")
        reference_group = root_node.addGroup("Validation Reference")
        project.addMapLayer(persisted_tiles, False)
        project.addMapLayer(persisted_cities, False)
        project.addMapLayer(persisted_admin_labels, False)
        project.addMapLayer(persisted_borders, False)
        project.addMapLayer(persisted_coast, False)
        game_group.addLayer(persisted_tiles)
        game_group.addLayer(persisted_cities)
        game_group.addLayer(persisted_admin_labels)
        game_group.addLayer(persisted_borders)
        game_group.addLayer(persisted_coast)
        project.addMapLayer(persisted_admin, False)
        project.addMapLayer(persisted_candidates, False)
        reference_group.addLayer(persisted_admin)
        reference_group.addLayer(persisted_candidates)
        reference_group.setItemVisibilityChecked(False)
        project.setFileName(str(project_path))
        if not project.write():
            raise QgsProcessingException(f"Failed to write QGIS project: {project_path}")

        # The overview intentionally omits detailed tile IDs. They remain
        # scale-dependent labels in the interactive QGIS project.
        persisted_tiles.setLabelsEnabled(False)
        render_preview(
            [persisted_admin_labels, persisted_borders, persisted_coast, persisted_tiles],
            preview_path,
        )
        persisted_tiles.setLabelsEnabled(True)

        report_lines = [
            "# Atlas Korea tile allocation report", "",
            f"Generated: {datetime.now(timezone.utc).isoformat()}", "",
            f"- Orientation: `{orientation}`", f"- Final tiles: **{len(selected_indexes)}**",
            f"- Target tile area: {settings['grid']['target_area_km2']} km2", "",
            "- Assignment policy: dominant administrative overlap with configured minimum representation",
            "- Target counts are advisory, not hard constraints", "",
            "| Code | Admin area | Target | Minimum | Actual | Difference |",
            "| --- | --- | ---: | ---: | ---: | ---: |",
        ]
        for admin in admins:
            actual = counts[admin["code"]]
            report_lines.append(
                f"| {admin['code']} | {admin['name_ko']} / {admin['name_en']} | "
                f"{admin['target_tiles']} | {admin.get('minimum_tiles', 0)} | {actual} | "
                f"{actual - int(admin['target_tiles'])} |"
            )
        report_lines.extend(["", "## Minimum-representation exceptions", ""])
        if minimum_exceptions:
            for index, (dominant, assigned) in sorted(
                minimum_exceptions.items(), key=lambda item: candidates[item[0]]["tile_id"]
            ):
                candidate = candidates[index]
                report_lines.append(
                    f"- `{candidate['tile_id']}`: dominant `{dominant}` -> required `{assigned}`; "
                    f"required overlap {candidate['overlaps'].get(assigned, 0) / 1_000_000.0:.2f} km2"
                )
        else:
            report_lines.append("- None")
        boundary_tiles = []
        for index in selected_indexes:
            candidate = candidates[index]
            if len(candidate["overlaps"]) > 1:
                boundary_tiles.append(
                    (candidate["tile_id"], assignments[index], sorted(candidate["overlaps"]))
                )
        report_lines.extend(["", "## Boundary tiles", ""])
        if boundary_tiles:
            for tile_id, assigned, intersected in boundary_tiles:
                report_lines.append(
                    f"- `{tile_id}` -> `{assigned}`; intersects {', '.join(intersected)}"
                )
        else:
            report_lines.append("- None")
        report_lines.extend(["", "## Manual overrides", ""])
        if override_reasons:
            for tile_id, reason in sorted(override_reasons.items()):
                report_lines.append(f"- `{tile_id}`: {reason or 'No reason supplied'}")
        else:
            report_lines.append("- None")
        report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
        feedback.setProgress(100)
        return {
            OUTPUT_GPKG: str(gpkg_path), OUTPUT_PROJECT: str(project_path),
            OUTPUT_PREVIEW: str(preview_path), OUTPUT_REPORT: str(report_path),
        }
