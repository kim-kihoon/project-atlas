"""QGIS Processing script that builds the Atlas Republic of Korea map."""

from collections import Counter
from datetime import datetime, timezone
import csv
import io
import json
import math
from pathlib import Path
import re
import zipfile

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
    QgsMarkerSymbol,
    QgsPalLayerSettings,
    QgsPointXY,
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


def load_city_source(root, settings):
    source = settings["city_source"]
    archive_path = resolve(root, source["path"])
    if not archive_path.exists():
        raise QgsProcessingException(f"City source does not exist: {archive_path}")
    aliases = source.get("canonical_aliases", {})
    korean_names = source["names_ko"]
    selected = {}
    with zipfile.ZipFile(archive_path) as archive:
        with archive.open(source["member"]) as raw:
            reader = csv.reader(io.TextIOWrapper(raw, encoding="utf-8"), delimiter="\t")
            for row in reader:
                if len(row) < 19 or row[8] != source["country_code"]:
                    continue
                try:
                    population = int(row[14] or 0)
                    latitude = float(row[4])
                    longitude = float(row[5])
                except ValueError:
                    continue
                if population < int(source["minimum_population"]):
                    continue
                ascii_name = row[2].strip()
                feature_class, feature_code = row[6], row[7]
                is_city_place = feature_class == "P"
                is_city_admin = feature_code == "ADM2" and ascii_name.lower().endswith("-si")
                if not (is_city_place or is_city_admin):
                    continue
                canonical = re.sub(r"-si$", "", ascii_name.lower()).replace(" ", "-")
                canonical = aliases.get(canonical, canonical)
                if canonical not in korean_names:
                    raise QgsProcessingException(
                        f"Missing Korean city-name mapping for {ascii_name} ({canonical})"
                    )
                record = {
                    "city_id": row[0], "canonical": canonical,
                    "name_ko": korean_names[canonical],
                    "name_en": canonical.replace("-", " ").title(),
                    "latitude": latitude, "longitude": longitude,
                    "population": population, "feature_code": feature_code,
                    "admin1_source_code": row[10], "source_date": row[18],
                }
                previous = selected.get(canonical)
                if previous is None or (population, row[0]) > (previous["population"], previous["city_id"]):
                    selected[canonical] = record
    if not selected:
        raise QgsProcessingException("No qualifying cities found in GeoNames source")
    return [selected[key] for key in sorted(selected)]


def normalized_unit_name(value):
    value = re.sub(r"\s*\[[^]]*\]\s*", "", value.strip().lower())
    value = value.replace(" district", "").replace("county", "")
    value = re.sub(r"-(si|gun|gu)$", "", value)
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-")


def display_unit_name(value):
    value = re.sub(r"\s*\[[^]]*\]\s*", "", value.strip())
    return re.sub(r"-(si|gun|gu)$", "", value, flags=re.IGNORECASE)


def load_admin2_population(root, settings):
    """Load comparable ADM2 population and Korean names from GeoNames."""
    city_source = settings["city_source"]
    naming = settings["tile_naming"]
    archive_path = resolve(root, city_source["path"])
    records = {}
    ids = set()
    with zipfile.ZipFile(archive_path) as archive:
        with archive.open(city_source["member"]) as raw:
            reader = csv.reader(io.TextIOWrapper(raw, encoding="utf-8"), delimiter="\t")
            for row in reader:
                if len(row) < 19 or row[8] != city_source["country_code"] or row[7] != "ADM2":
                    continue
                admin_code = naming["geonames_admin1_codes"].get(row[10])
                if not admin_code:
                    continue
                try:
                    population = int(row[14] or 0)
                except ValueError:
                    population = 0
                key = (admin_code, normalized_unit_name(row[2]))
                record = {
                    "geoname_id": row[0], "population": population,
                    "name_en": display_unit_name(row[2]), "name_ko": None,
                }
                previous = records.get(key)
                if previous is None or (population, row[0]) > (
                    previous["population"], previous["geoname_id"]
                ):
                    records[key] = record
                ids.add(row[0])

    korean = {}
    alternate_path = resolve(root, naming["alternate_names_path"])
    with zipfile.ZipFile(alternate_path) as archive:
        with archive.open(naming["alternate_names_member"]) as raw:
            reader = csv.reader(io.TextIOWrapper(raw, encoding="utf-8"), delimiter="\t")
            for row in reader:
                if (
                    len(row) < 4 or row[1] not in ids
                    or (row[2] != "ko" and not re.search(r"[가-힣]", row[3]))
                ):
                    continue
                value = re.sub(r"(특별자치)?(시|군|구)$", "", row[3].strip())
                if not value:
                    continue
                preferred = len(row) > 4 and row[4] == "1"
                current = korean.get(row[1])
                score = (1 if row[2] == "ko" else 0, 1 if preferred else 0, -len(value), value)
                if current is None or score > current[0]:
                    korean[row[1]] = (score, value)
    for record in records.values():
        match = korean.get(record["geoname_id"])
        if match:
            record["name_ko"] = match[1]
    return records


def build_naming_units(root, settings, target_crs, context, admin_geometries, city_records):
    naming = settings["tile_naming"]
    source_path = resolve(root, naming["boundary_path"])
    source_layer = QgsVectorLayer(str(source_path), "geoboundaries_admin2", "ogr")
    if not source_layer.isValid():
        raise QgsProcessingException(f"Invalid naming boundary layer: {source_path}")
    transform = QgsCoordinateTransform(source_layer.crs(), target_crs, context.transformContext())
    populations = load_admin2_population(root, settings)
    admin_by_code = {item["code"]: item for item in settings["admin1"]}
    aggregate_codes = set(naming["aggregate_admin1_codes"])
    city_by_name = {item["canonical"]: item for item in city_records}
    parts = {}
    for feature in source_layer.getFeatures():
        geometry = QgsGeometry(feature.geometry())
        geometry.transform(transform)
        if not geometry.isGeosValid():
            geometry = geometry.makeValid()
        if geometry.isEmpty():
            continue
        admin_scores = {
            code: geometry.intersection(admin_geometry).area()
            for code, admin_geometry in admin_geometries.items()
            if geometry.boundingBox().intersects(admin_geometry.boundingBox())
        }
        if not admin_scores:
            continue
        source_name = str(feature["shapeName"])
        canonical = normalized_unit_name(source_name)
        documented_admins = sorted(code for code, name in populations if name == canonical)
        if len(documented_admins) == 1:
            admin_code = documented_admins[0]
        else:
            eligible_admins = documented_admins or sorted(admin_scores)
            admin_code = sorted(
                eligible_admins, key=lambda code: (-admin_scores.get(code, 0.0), code)
            )[0]
        if admin_code in aggregate_codes:
            admin = admin_by_code[admin_code]
            canonical = normalized_unit_name(admin["name_en"])
            unit_code = f"{admin_code}:{canonical}"
            city = city_by_name.get(canonical)
            values = {
                "unit_code": unit_code, "admin1_code": admin_code,
                "name_ko": admin["name_ko"], "name_en": admin["name_en"],
                "population": city["population"] if city else 0,
                "population_known": bool(city), "source_names": set(), "geometries": [],
            }
        else:
            unit_code = f"{admin_code}:{canonical}"
            population = populations.get((admin_code, canonical), {})
            values = {
                "unit_code": unit_code, "admin1_code": admin_code,
                "name_ko": population.get("name_ko") or display_unit_name(source_name),
                "name_en": display_unit_name(source_name),
                "population": int(population.get("population", 0)),
                "population_known": int(population.get("population", 0)) > 0,
                "source_names": set(), "geometries": [],
            }
        unit = parts.setdefault(unit_code, values)
        unit["source_names"].add(source_name)
        unit["geometries"].append(geometry)
    units = []
    for unit_code in sorted(parts):
        unit = parts[unit_code]
        unit["geometry"] = QgsGeometry.unaryUnion(unit.pop("geometries"))
        unit["source_names"] = ", ".join(sorted(unit["source_names"]))
        units.append(unit)
    if not units:
        raise QgsProcessingException("No tile naming units were built")
    return units


def allocate_tile_names(
    candidates, selected_indexes, admin_assignments, units, minimum_share, feedback
):
    """Match first representatives globally, then fill within each tile owner."""
    unit_by_code = {unit["unit_code"]: unit for unit in units}
    overlaps = {}
    nearest_fallbacks = set()
    for index in selected_indexes:
        tile = candidates[index]
        scores = {}
        for unit in units:
            if unit["admin1_code"] != admin_assignments[index]:
                continue
            geometry = unit["geometry"]
            if not tile["geometry"].boundingBox().intersects(geometry.boundingBox()):
                continue
            area = tile["geometry"].intersection(geometry).area()
            if area > 0:
                scores[unit["unit_code"]] = area
        if not scores:
            owner_units = [
                unit for unit in units if unit["admin1_code"] == admin_assignments[index]
            ]
            if not owner_units:
                raise QgsProcessingException(
                    f"No naming units configured for owner {admin_assignments[index]}"
                )
            nearest = min(
                owner_units,
                key=lambda unit: (
                    tile["geometry"].distance(unit["geometry"]), unit["unit_code"]
                ),
            )
            scores[nearest["unit_code"]] = 0.0
            nearest_fallbacks.add(index)
        overlaps[index] = scores

    eligible_tiles = {}
    for unit in units:
        code = unit["unit_code"]
        options = []
        for index in selected_indexes:
            area = overlaps[index].get(code, 0.0)
            if area / candidates[index]["geometry"].area() >= minimum_share:
                options.append(index)
        eligible_tiles[code] = sorted(
            options,
            key=lambda index: (-overlaps[index][code], candidates[index]["tile_id"]),
        )

    # Maximum-cardinality bipartite matching. Processing high-population units
    # first preserves them when there are fewer usable tiles than units, while
    # augmenting paths avoid wasting a tile that can represent another unit.
    tile_to_unit = {}
    unit_to_tile = {}

    def assign_unit(code, seen_tiles, seen_units):
        if code in seen_units:
            return False
        seen_units.add(code)
        for index in eligible_tiles[code]:
            if index in seen_tiles:
                continue
            seen_tiles.add(index)
            incumbent = tile_to_unit.get(index)
            if incumbent is None or assign_unit(incumbent, seen_tiles, seen_units):
                tile_to_unit[index] = code
                unit_to_tile[code] = index
                if incumbent is not None and unit_to_tile.get(incumbent) == index:
                    del unit_to_tile[incumbent]
                return True
        return False

    priority_units = sorted(
        units,
        key=lambda unit: (
            0 if unit["population_known"] else 1,
            -unit["population"], unit["unit_code"],
        ),
    )
    for unit in priority_units:
        assign_unit(unit["unit_code"], set(), set())

    assignments = dict(tile_to_unit)
    methods = {index: "unique_representation" for index in assignments}
    for index in selected_indexes:
        if index in assignments:
            continue
        scores = overlaps[index]
        assignments[index] = sorted(scores, key=lambda code: (-scores[code], code))[0]
        methods[index] = (
            "owner_nearest_fallback" if index in nearest_fallbacks else "dominant_overlap_fill"
        )

    mismatched = [
        candidates[index]["tile_id"] for index, code in assignments.items()
        if unit_by_code[code]["admin1_code"] != admin_assignments[index]
    ]
    if mismatched:
        raise QgsProcessingException(f"Naming/admin ownership mismatch: {mismatched}")
    feedback.pushInfo(
        f"Named {len(selected_indexes)} tiles from {len(units)} units; "
        f"represented {len(unit_to_tile)} unique units; "
        f"used {len(nearest_fallbacks)} same-owner nearest-boundary fallbacks"
    )
    return assignments, overlaps, methods, unit_to_tile


def allocate_tiles(candidates, admins, country_iso3, feedback):
    """Keep country-dominant tiles, assign dominant admin, then satisfy minima."""
    selected = [
        i for i, item in enumerate(candidates)
        if item["dominant_territory"] == country_iso3
    ]
    selected.sort(key=lambda i: candidates[i]["tile_id"])
    if not selected:
        raise QgsProcessingException(f"No candidate is dominated by {country_iso3}")
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
                f"Cannot satisfy minimum representation for {code} with the selected country tiles"
            )
        _, _, _, _, index = sorted(options)[0]
        donor = assignments[index]
        assignments[index] = code
        counts[donor] -= 1
        counts[code] += 1
        minimum_exceptions[index] = (donor, code)

    feedback.pushInfo(
        f"Selected {len(selected)} {country_iso3}-dominant tiles; "
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
        return tr("Builds the deterministic dominant-overlap Korea GeoPackage, QGIS project, report and preview.")

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
        country_iso3 = settings["country"]["iso3"]

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
        source_country_extent = None
        filter_field = settings["source"]["country_filter_field"]
        filter_value = settings["source"]["country_filter_value"]
        for feature in source_layer.getFeatures():
            if str(feature[filter_field]) != filter_value:
                continue
            feature_extent = feature.geometry().boundingBox()
            if source_country_extent is None:
                source_country_extent = QgsRectangle(feature_extent)
            else:
                source_country_extent.combineExtentWith(feature_extent)
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

        # Build nearby country polygons from the same global Admin-1 source so
        # border and coastal cells can compare countries and ocean consistently.
        search_extent = QgsRectangle(source_country_extent)
        search_extent.grow(float(settings["grid"]["nearby_country_search_buffer_degrees"]))
        country_parts = {}
        for feature in source_layer.getFeatures():
            geometry = feature.geometry()
            if geometry.isEmpty() or not geometry.boundingBox().intersects(search_extent):
                continue
            code = str(feature["adm0_a3"] or "")
            if not code:
                continue
            transformed = QgsGeometry(geometry)
            transformed.transform(transform)
            if not transformed.isGeosValid():
                transformed = transformed.makeValid()
            if not transformed.isEmpty():
                country_parts.setdefault(code, []).append(transformed)
        country_geometries = {
            code: QgsGeometry.unaryUnion(parts) for code, parts in country_parts.items()
        }
        if country_iso3 not in country_geometries:
            raise QgsProcessingException(f"Country geometry missing for {country_iso3}")
        nearby_land = QgsGeometry.unaryUnion(list(country_geometries.values()))
        feedback.pushInfo(f"Nearby country competitors: {', '.join(sorted(country_geometries))}")

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
                country_overlaps = {}
                for code, country_geometry in country_geometries.items():
                    if not geometry.boundingBox().intersects(country_geometry.boundingBox()):
                        continue
                    area = geometry.intersection(country_geometry).area()
                    if area >= float(grid["candidate_min_overlap_m2"]):
                        country_overlaps[code] = area
                ocean_area = max(
                    0.0,
                    geometry.area() - geometry.intersection(nearby_land).area(),
                )
                territory_scores = dict(country_overlaps)
                territory_scores[grid["ocean_code"]] = ocean_area
                dominant_territory = sorted(
                    territory_scores,
                    key=lambda code: (-territory_scores[code], code),
                )[0]
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
                        "country_overlaps": country_overlaps,
                        "ocean_area": ocean_area,
                        "dominant_territory": dominant_territory,
                    }
                )
        feedback.pushInfo(
            f"Generated {len(candidates)} candidates; "
            f"{sum(1 for item in candidates if item['land_area'] > 0)} intersect land"
        )
        feedback.setProgress(40)

        assignments, minimum_exceptions = allocate_tiles(
            candidates, admins, country_iso3, feedback
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

        city_records = load_city_source(root, settings)
        naming_units = build_naming_units(
            root, settings, target_crs, context, admin_geometries, city_records
        )
        tile_name_assignments, tile_name_overlaps, tile_name_methods, unique_unit_tiles = allocate_tile_names(
            candidates, selected_indexes, assignments, naming_units,
            float(settings["tile_naming"]["minimum_tile_share"]), feedback,
        )
        naming_unit_by_code = {unit["unit_code"]: unit for unit in naming_units}

        city_crs = QgsCoordinateReferenceSystem("EPSG:4326")
        city_transform = QgsCoordinateTransform(city_crs, target_crs, context.transformContext())
        city_by_unit_code = {}
        city_classes = settings["city_classification"]
        for city in city_records:
            point = city_transform.transform(QgsPointXY(city["longitude"], city["latitude"]))
            geometry = QgsGeometry.fromPointXY(point)
            admin1_code = settings["tile_naming"]["geonames_admin1_codes"].get(
                city["admin1_source_code"]
            )
            unit_code = f"{admin1_code}:{city['canonical']}" if admin1_code else None
            city_class = (
                "metropolis" if city["population"] >= int(city_classes["metropolis_population_min"])
                else "city"
            )
            named_indexes = sorted(
                [index for index, code in tile_name_assignments.items() if code == unit_code],
                key=lambda index: candidates[index]["tile_id"],
            )
            city.update(
                {
                    "geometry": geometry, "unit_code": unit_code,
                    "tile_id": candidates[named_indexes[0]]["tile_id"] if named_indexes else None,
                    "admin1_code": admin1_code,
                    "city_class": city_class,
                    "is_capital": city["city_id"] == settings["city_source"]["capital_geoname_id"],
                }
            )
            if unit_code in naming_unit_by_code:
                city_by_unit_code[unit_code] = city

        candidate_fields = QgsFields()
        for name, kind in (
            ("candidate_id", QVariant.String),
            ("grid_row", QVariant.Int),
            ("grid_col", QVariant.Int),
            ("land_area_km2", QVariant.Double),
            ("land_ratio", QVariant.Double),
            ("dominant_territory", QVariant.String),
            ("ocean_ratio", QVariant.Double),
            ("best_admin", QVariant.String),
            ("best_overlap", QVariant.Double),
            ("selected", QVariant.Bool),
            ("assigned_admin", QVariant.String),
            ("assignment_method", QVariant.String),
            ("country_scores_json", QVariant.String),
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
                    candidate["dominant_territory"],
                    candidate["ocean_area"] / hex_area,
                    best_admin, best_overlap / 1_000_000.0,
                    index in assignments, assignments.get(index),
                    (
                        "manual_override" if candidate["tile_id"] in override_reasons
                        else "minimum_representation" if index in minimum_exceptions
                        else "dominant_overlap"
                    ) if index in assignments else None,
                    json.dumps(
                        {
                            **{
                                code: round(area / 1_000_000.0, 6)
                                for code, area in sorted(candidate["country_overlaps"].items())
                            },
                            grid["ocean_code"]: round(candidate["ocean_area"] / 1_000_000.0, 6),
                        },
                        ensure_ascii=False, separators=(",", ":"),
                    ),
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
            ("map_class", QVariant.String),
            ("tile_name_code", QVariant.String), ("tile_name_ko", QVariant.String),
            ("tile_name_en", QVariant.String), ("tile_name_method", QVariant.String),
            ("tile_name_population", QVariant.LongLong),
            ("tile_name_overlap_km2", QVariant.Double),
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
            naming_code = tile_name_assignments[index]
            naming_unit = naming_unit_by_code[naming_code]
            naming_overlap = tile_name_overlaps[index].get(naming_code, 0.0)
            city = city_by_unit_code.get(naming_code)
            city_class = city["city_class"] if city else None
            is_capital = bool(city and city["is_capital"])
            district_slots = 3 if city_class == "metropolis" else 2 if city_class == "city" else 1
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
                "population": city["population"] if city else None,
                "city_name_ko": city["name_ko"] if city else None,
                "city_name_en": city["name_en"] if city else None,
                "city_class": city_class, "is_capital": is_capital,
                "map_class": "capital" if is_capital else city_class or code,
                "tile_name_code": naming_code,
                "tile_name_ko": naming_unit["name_ko"],
                "tile_name_en": naming_unit["name_en"],
                "tile_name_method": tile_name_methods[index],
                "tile_name_population": (
                    city["population"] if city else
                    naming_unit["population"] if naming_unit["population_known"] else None
                ),
                "tile_name_overlap_km2": naming_overlap / 1_000_000.0,
                "district_slots": district_slots,
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
            ("tile_id", QVariant.String), ("admin1_code", QVariant.String),
            ("unit_code", QVariant.String),
            ("source_year", QVariant.Int), ("source_url", QVariant.String),
        ):
            city_fields.append(QgsField(name, kind))
        city_layer = memory_layer("Point", target_crs, "city_markers", city_fields)
        city_features = []
        for city in city_records:
            feature = QgsFeature(city_layer.fields())
            feature.setGeometry(city["geometry"])
            feature.setAttributes(
                [
                    city["city_id"], city["name_ko"], city["name_en"], city["population"],
                    city["city_class"], city["is_capital"], city["tile_id"], city["admin1_code"],
                    city["unit_code"],
                    int(city["source_date"][:4]) if city["source_date"][:4].isdigit() else None,
                    "https://www.geonames.org/export/",
                ]
            )
            city_features.append(feature)
        city_layer.dataProvider().addFeatures(city_features)

        naming_fields = QgsFields()
        for name, kind in (
            ("unit_code", QVariant.String), ("admin1_code", QVariant.String),
            ("name_ko", QVariant.String), ("name_en", QVariant.String),
            ("population", QVariant.LongLong), ("population_known", QVariant.Bool),
            ("source_names", QVariant.String), ("source_year", QVariant.Int),
        ):
            naming_fields.append(QgsField(name, kind))
        naming_layer = memory_layer("MultiPolygon", target_crs, "admin2_naming_source", naming_fields)
        naming_features = []
        for unit in naming_units:
            feature = QgsFeature(naming_layer.fields())
            feature.setGeometry(unit["geometry"])
            feature.setAttributes(
                [
                    unit["unit_code"], unit["admin1_code"], unit["name_ko"], unit["name_en"],
                    unit["population"] if unit["population_known"] else None,
                    unit["population_known"], unit["source_names"],
                    int(settings["tile_naming"]["boundary_year"]),
                ]
            )
            naming_features.append(feature)
        naming_layer.dataProvider().addFeatures(naming_features)

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
        write_gpkg_layer(naming_layer, gpkg_path, "admin2_naming_source", False)
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
        persisted_naming = QgsVectorLayer(
            f"{gpkg_path}|layername=admin2_naming_source", "City-county naming reference", "ogr"
        )
        persisted_borders = QgsVectorLayer(f"{gpkg_path}|layername=admin1_tile_borders", "Game admin borders", "ogr")
        persisted_coast = QgsVectorLayer(f"{gpkg_path}|layername=coastal_tile_outlines", "Coastal tile outlines", "ogr")
        for layer in (
            persisted_tiles, persisted_admin, persisted_admin_labels, persisted_candidates,
            persisted_cities, persisted_naming, persisted_borders, persisted_coast,
        ):
            if not layer.isValid():
                raise QgsProcessingException(f"Failed to reload persisted layer: {layer.name()}")

        categories = []
        class_colors = settings["city_classification"]["colors"]
        for value, label in (
            ("capital", "수도"), ("metropolis", "인구 100만 이상"),
            ("city", "인구 50만 이상 100만 미만"),
        ):
            symbol = QgsFillSymbol.createSimple(
                {"color": class_colors[value], "outline_color": "#36454f", "outline_width": "0.35"}
            )
            categories.append(QgsRendererCategory(value, symbol, label))
        for admin in admins:
            symbol = QgsFillSymbol.createSimple(
                {"color": admin["color"], "outline_color": "#36454f", "outline_width": "0.35"}
            )
            categories.append(QgsRendererCategory(admin["code"], symbol, admin["name_ko"]))
        persisted_tiles.setRenderer(QgsCategorizedSymbolRenderer("map_class", categories))
        label_settings = QgsPalLayerSettings()
        label_settings.fieldName = (
            "tile_name_ko || CASE WHEN @map_scale < 350000 THEN '\\n' || tile_id ELSE '' END"
        )
        label_settings.isExpression = True
        label_settings.scaleVisibility = True
        label_settings.maximumScale = 1600000
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
        persisted_cities.setRenderer(
            QgsSingleSymbolRenderer(
                QgsMarkerSymbol.createSimple(
                    {"name": "circle", "color": "#ffffff", "outline_color": "#202020", "size": "2.4"}
                )
            )
        )
        city_labels = QgsPalLayerSettings()
        city_labels.fieldName = "city_name_ko"
        city_labels.isExpression = False
        city_labels.scaleVisibility = True
        city_labels.maximumScale = 900000
        city_text = QgsTextFormat()
        city_text.setSize(8)
        city_text.setColor(QColor("#202020"))
        city_buffer = QgsTextBufferSettings()
        city_buffer.setEnabled(True)
        city_buffer.setSize(0.7)
        city_buffer.setColor(QColor("white"))
        city_text.setBuffer(city_buffer)
        city_labels.setFormat(city_text)
        persisted_cities.setLabeling(QgsVectorLayerSimpleLabeling(city_labels))
        # A tile has exactly one visible city/county name: tile_name_ko.
        # City markers remain available for population classification and
        # inspection, but their labels would create a second name on the tile.
        persisted_cities.setLabelsEnabled(False)
        persisted_naming.setRenderer(
            QgsSingleSymbolRenderer(
                QgsFillSymbol.createSimple(
                    {"color": "0,0,0,0", "outline_color": "#777777", "outline_width": "0.2"}
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
        project.addMapLayer(persisted_naming, False)
        reference_group.addLayer(persisted_admin)
        reference_group.addLayer(persisted_candidates)
        reference_group.addLayer(persisted_naming)
        reference_group.setItemVisibilityChecked(False)
        project.setFileName(str(project_path))
        if not project.write():
            raise QgsProcessingException(f"Failed to write QGIS project: {project_path}")

        render_preview(
            [persisted_admin_labels, persisted_borders, persisted_coast, persisted_tiles],
            preview_path,
        )

        report_lines = [
            "# Atlas Korea tile allocation report", "",
            f"Generated: {datetime.now(timezone.utc).isoformat()}", "",
            f"- Orientation: `{orientation}`", f"- Final tiles: **{len(selected_indexes)}**",
            f"- Target tile area: {settings['grid']['target_area_km2']} km2", "",
            "- Country selection: dominant overlap among nearby countries and ocean; no fixed national total",
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
        report_lines.extend(["", "## Tile naming", ""])
        report_lines.extend(
            [
                "- Hard constraint: tile name must belong to the tile's assigned admin-1 owner",
                "- First pass: one representative tile per city/county through population-priority matching",
                f"- Minimum overlap share for first-pass matching: "
                f"{float(settings['tile_naming']['minimum_tile_share']):.0%}",
                "- Second pass: remaining tiles use the largest-overlap city/county within the same owner",
                f"- Naming units: {len(naming_units)}",
                f"- Uniquely represented units: {len(unique_unit_tiles)}",
                f"- Dominant-overlap fill tiles: "
                f"{sum(1 for method in tile_name_methods.values() if method == 'dominant_overlap_fill')}",
                f"- Same-owner nearest-boundary fallbacks: "
                f"{sum(1 for method in tile_name_methods.values() if method == 'owner_nearest_fallback')}",
            ]
        )
        city_counts = Counter(city["city_class"] for city in city_records)
        report_lines.extend(
            [
                "", "## Population-based city classes", "",
                "City class changes tile fill only; administrative ownership and borders remain separate.", "",
                f"- Capital markers: {sum(1 for city in city_records if city['is_capital'])}",
                f"- Metropolis markers (1,000,000+): {city_counts.get('metropolis', 0)}",
                f"- City markers (500,000-999,999): {city_counts.get('city', 0)}",
                f"- Markers linked to a same-name tile: "
                f"{sum(1 for city in city_records if city['tile_id'])}/{len(city_records)}",
            ]
        )
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
