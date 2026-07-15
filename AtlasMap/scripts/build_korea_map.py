"""QGIS Processing script that builds the Atlas Republic of Korea map."""

from collections import Counter
from datetime import datetime, timezone
import csv
import gzip
import io
import json
import math
from pathlib import Path
import re
import zipfile

import processing
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
    QgsWkbTypes,
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


def configured_countries(settings):
    primary = {
        "country": settings["country"], "city_source": settings["city_source"],
        "tile_naming": settings["tile_naming"],
        "population_fallback": settings["population_fallback"],
        "admin1": settings["admin1"],
    }
    return [primary, *settings.get("additional_countries", [])]


def load_national_population_totals(root, settings, country_iso3s):
    model = settings["population_model"]
    source_path = resolve(root, model["national_totals_path"])
    if not source_path.exists():
        raise QgsProcessingException(
            f"National population source does not exist: {source_path}"
        )
    year = int(model["national_totals_year"])
    variant = str(model["national_totals_variant"])
    multiplier = 1000 if model.get("national_totals_units") == "thousands" else 1
    totals = {}
    with gzip.open(source_path, "rt", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            iso3 = str(row.get("ISO3_code") or "")
            if (
                iso3 not in country_iso3s
                or str(row.get("Variant") or "") != variant
                or int(row.get("Time") or -1) != year
            ):
                continue
            totals[iso3] = int(round(float(row["PopTotal"]) * multiplier))
    missing = sorted(country_iso3s - set(totals))
    if missing or any(value <= 0 for value in totals.values()):
        raise QgsProcessingException(
            f"Missing or invalid national population totals: {missing}, totals={totals}"
        )
    return totals


def allocate_tile_populations(
    root, country_settings, candidates, selected_by_country,
    target_crs, context, national_totals, city_anchor_by_index,
):
    """Fix real-city anchors, then allocate the national residual by WorldPop weight."""
    result = {}
    raw_sums = {}
    methods = {}
    source_ids = {}
    for item in country_settings:
        iso3 = item["country"]["iso3"]
        raster_path = resolve(root, item["population_fallback"]["path"])
        if not raster_path.exists():
            raise QgsProcessingException(
                f"Population weight raster does not exist for {iso3}: {raster_path}"
            )
        fields = QgsFields()
        fields.append(QgsField("candidate_index", QVariant.Int))
        layer = memory_layer("Polygon", target_crs, f"{iso3}_population_tiles", fields)
        features = []
        for index in sorted(selected_by_country[iso3]):
            feature = QgsFeature(layer.fields())
            feature.setGeometry(candidates[index]["geometry"])
            feature.setAttribute("candidate_index", index)
            features.append(feature)
        layer.dataProvider().addFeatures(features)
        zonal = processing.run(
            "native:zonalstatisticsfb",
            {
                "INPUT": layer,
                "INPUT_RASTER": str(raster_path),
                "RASTER_BAND": 1,
                "COLUMN_PREFIX": "wp_",
                "STATISTICS": [1],
                "OUTPUT": "memory:",
            },
            context=context,
        )["OUTPUT"]
        weights = {
            int(feature["candidate_index"]): max(0.0, float(feature["wp_sum"] or 0.0))
            for feature in zonal.getFeatures()
        }
        national_total = int(national_totals[iso3])
        country_indexes = sorted(selected_by_country[iso3])
        anchors = {
            index: city_anchor_by_index[index]
            for index in country_indexes if index in city_anchor_by_index
        }
        fixed_total = sum(int(city["population"]) for city in anchors.values())
        if fixed_total >= national_total:
            raise QgsProcessingException(
                f"City anchor population is not below national total for {iso3}: "
                f"{fixed_total} >= {national_total}"
            )
        for index, city in anchors.items():
            result[index] = int(city["population"])
            methods[index] = "geonames_city_anchor"
            source_ids[index] = str(city["city_id"])

        residual_indexes = [index for index in country_indexes if index not in anchors]
        residual_total = national_total - fixed_total
        residual_weights = {index: weights[index] for index in residual_indexes}
        total_weight = sum(residual_weights.values())
        if total_weight <= 0:
            raise QgsProcessingException(f"No positive residual population weights for {iso3}")
        exact = {
            index: residual_total * weight / total_weight
            for index, weight in residual_weights.items()
        }
        allocated = {index: math.floor(value) for index, value in exact.items()}
        remainder = residual_total - sum(allocated.values())
        order = sorted(
            exact,
            key=lambda index: (
                -(exact[index] - allocated[index]), candidates[index]["tile_id"],
            ),
        )
        for index in order[:remainder]:
            allocated[index] += 1
        if sum(allocated.values()) != residual_total:
            raise QgsProcessingException(
                f"Residual population allocation does not reconcile for {iso3}"
            )
        result.update(allocated)
        for index in allocated:
            methods[index] = "worldpop_residual_reconciled_to_un_wpp_total_largest_remainder"
            source_ids[index] = "WPP2024"
        raw_sums[iso3] = total_weight
    return result, raw_sums, methods, source_ids


def make_hexagon(cx, cy, side, orientation):
    start_angle = 30.0 if orientation == "pointy_top" else 0.0
    points = []
    from qgis.core import QgsPointXY

    for index in range(6):
        angle = math.radians(start_angle + index * 60.0)
        points.append(QgsPointXY(cx + side * math.cos(angle), cy + side * math.sin(angle)))
    points.append(points[0])
    return QgsGeometry.fromPolygonXY([points])


def shared_edge_geometry(first, second):
    """Normalize a shared hex edge when GEOS returns a microscopic polygon sliver."""
    shared = first.intersection(second)
    geometry_type = QgsWkbTypes.geometryType(shared.wkbType())
    if geometry_type == QgsWkbTypes.LineGeometry:
        if shared.isMultipart():
            lines = [line for line in shared.asMultiPolyline() if line]
            if not lines:
                return QgsGeometry()
            line = max(lines, key=lambda value: QgsGeometry.fromPolylineXY(value).length())
            return QgsGeometry.fromPolylineXY(line)
        return shared
    if geometry_type == QgsWkbTypes.PolygonGeometry:
        polygons = shared.asMultiPolygon() if shared.isMultipart() else [shared.asPolygon()]
        segments = []
        for polygon in polygons:
            for ring in polygon:
                for index in range(len(ring) - 1):
                    segment = QgsGeometry.fromPolylineXY([ring[index], ring[index + 1]])
                    segments.append(segment)
        return max(segments, key=lambda value: value.length()) if segments else QgsGeometry()
    return QgsGeometry()


def hex_edge_records(geometry, precision=3):
    ring = geometry.asPolygon()[0]
    points = list(ring[:-1] if ring and ring[0] == ring[-1] else ring)
    records = []
    for index, first in enumerate(points):
        second = points[(index + 1) % len(points)]
        first_key = (round(first.x(), precision), round(first.y(), precision))
        second_key = (round(second.x(), precision), round(second.y(), precision))
        endpoints = sorted((first_key, second_key))
        key = (
            f"{endpoints[0][0]:.{precision}f},{endpoints[0][1]:.{precision}f}|"
            f"{endpoints[1][0]:.{precision}f},{endpoints[1][1]:.{precision}f}"
        )
        records.append((key, QgsGeometry.fromPolylineXY([first, second])))
    return records


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
                is_city_place = feature_code in {
                    "PPL", "PPLA", "PPLA2", "PPLA3", "PPLA4", "PPLA5", "PPLC",
                }
                is_city_admin = feature_code == "ADM2" and ascii_name.lower().endswith("-si")
                if not (is_city_place or is_city_admin):
                    continue
                canonical = re.sub(r"-si$", "", ascii_name.lower()).replace(" ", "-")
                canonical = aliases.get(canonical, canonical)
                record = {
                    "city_id": row[0], "canonical": canonical,
                    "name_ko": korean_names.get(canonical, display_unit_name(ascii_name)),
                    "name_en": canonical.replace("-", " ").title(),
                    "latitude": latitude, "longitude": longitude,
                    "population": population, "feature_code": feature_code,
                    "admin1_source_code": row[10], "source_date": row[18],
                    "is_capital": row[0] == source["capital_geoname_id"],
                }
                key = (row[10], canonical)
                previous = selected.get(key)
                if previous is None or (population, row[0]) > (previous["population"], previous["city_id"]):
                    selected[key] = record
    if not selected:
        raise QgsProcessingException("No qualifying cities found in GeoNames source")
    return [selected[key] for key in sorted(selected)]


def match_cities_to_naming_units(city_records, units, target_crs, context):
    """Match city points to the city/county unit that contains them."""
    transform = QgsCoordinateTransform(
        QgsCoordinateReferenceSystem("EPSG:4326"),
        target_crs,
        context.transformContext(),
    )
    city_by_unit = {}
    match_methods = {}
    for city in city_records:
        point = transform.transform(
            QgsPointXY(float(city["longitude"]), float(city["latitude"]))
        )
        point_geometry = QgsGeometry.fromPointXY(point)
        containing = [
            unit for unit in units
            if unit["geometry"].boundingBox().contains(point)
            and unit["geometry"].intersects(point_geometry)
        ]
        if containing:
            unit = sorted(containing, key=lambda value: value["unit_code"])[0]
            method = "point_in_naming_unit"
        else:
            unit = min(
                units,
                key=lambda value: (
                    value["geometry"].distance(point_geometry), value["unit_code"],
                ),
            )
            method = "nearest_naming_unit"
        code = unit["unit_code"]
        previous = city_by_unit.get(code)
        if previous is None or (city["population"], city["city_id"]) > (
            previous["population"], previous["city_id"]
        ):
            city_by_unit[code] = city
            match_methods[code] = method
    return city_by_unit, match_methods


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
    aliases = city_source.get("canonical_aliases", {})
    records = {}
    places_by_admin2 = {}
    places_by_name = {}
    ids = set()
    with zipfile.ZipFile(archive_path) as archive:
        with archive.open(city_source["member"]) as raw:
            reader = csv.reader(io.TextIOWrapper(raw, encoding="utf-8"), delimiter="\t")
            for row in reader:
                if len(row) < 19 or row[8] != city_source["country_code"]:
                    continue
                admin_code = naming["geonames_admin1_codes"].get(row[10])
                if not admin_code:
                    continue
                try:
                    population = int(row[14] or 0)
                except ValueError:
                    population = 0
                canonical = normalized_unit_name(row[2])
                canonical = aliases.get(canonical, canonical)
                if row[6] == "P" and population > 0:
                    place = {
                        "geoname_id": row[0], "population": population,
                        "admin2_source_code": row[11], "canonical": canonical,
                    }
                    if row[11]:
                        key = (admin_code, row[11])
                        previous = places_by_admin2.get(key)
                        if previous is None or (population, row[0]) > (
                            previous["population"], previous["geoname_id"]
                        ):
                            places_by_admin2[key] = place
                    key = (admin_code, canonical)
                    previous = places_by_name.get(key)
                    if previous is None or (population, row[0]) > (
                        previous["population"], previous["geoname_id"]
                    ):
                        places_by_name[key] = place
                if row[7] != "ADM2":
                    continue
                key = (admin_code, normalized_unit_name(row[2]))
                record = {
                    "geoname_id": row[0], "population": population if population > 0 else 0,
                    "name_en": display_unit_name(row[2]), "name_ko": None,
                    "admin2_source_code": row[11],
                    "population_method": "geonames_adm2" if population > 0 else "unknown",
                    "population_source_id": row[0] if population > 0 else None,
                }
                previous = records.get(key)
                if previous is None or (population, row[0]) > (
                    previous["population"], previous["geoname_id"]
                ):
                    records[key] = record
                ids.add(row[0])

    for (admin_code, canonical), record in records.items():
        if record["population"] > 0:
            continue
        fallback = None
        if record["admin2_source_code"]:
            fallback = places_by_admin2.get((admin_code, record["admin2_source_code"]))
        method = "geonames_populated_place_same_admin2"
        if fallback is None:
            fallback = places_by_name.get((admin_code, canonical))
            method = "geonames_populated_place_same_name"
        if fallback is not None:
            record["population"] = fallback["population"]
            record["population_method"] = method
            record["population_source_id"] = fallback["geoname_id"]

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
    city_by_unit = {}
    for city in city_records:
        admin_code = naming["geonames_admin1_codes"].get(city["admin1_source_code"])
        if not admin_code:
            continue
        key = (admin_code, city["canonical"])
        previous = city_by_unit.get(key)
        if previous is None or (city["population"], city["city_id"]) > (
            previous["population"], previous["city_id"]
        ):
            city_by_unit[key] = city
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
            city = city_by_unit.get((admin_code, canonical))
            values = {
                "unit_code": unit_code, "admin1_code": admin_code,
                "name_ko": admin["name_ko"], "name_en": admin["name_en"],
                "population": city["population"] if city else 0,
                "population_known": bool(city),
                "population_method": "geonames_populated_place" if city else "unknown",
                "population_source_id": city["city_id"] if city else None,
                "source_names": set(), "geometries": [],
                "source_year": int(naming["boundary_year"]),
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
                "population_method": population.get("population_method", "unknown"),
                "population_source_id": population.get("population_source_id"),
                "source_names": set(), "geometries": [],
                "source_year": int(naming["boundary_year"]),
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
    unresolved = [unit for unit in units if not unit["population_known"]]
    if unresolved:
        fallback = settings.get("population_fallback", {})
        raster_path = resolve(root, fallback.get("path", ""))
        if not raster_path.exists():
            raise QgsProcessingException(
                f"Population fallback raster does not exist: {raster_path}"
            )
        fallback_fields = QgsFields()
        fallback_fields.append(QgsField("unit_code", QVariant.String))
        fallback_layer = memory_layer(
            "MultiPolygon", target_crs, "population_fallback_units", fallback_fields
        )
        fallback_features = []
        for unit in unresolved:
            feature = QgsFeature(fallback_layer.fields())
            feature.setGeometry(unit["geometry"])
            feature.setAttribute("unit_code", unit["unit_code"])
            fallback_features.append(feature)
        fallback_layer.dataProvider().addFeatures(fallback_features)
        result = processing.run(
            "native:zonalstatisticsfb",
            {
                "INPUT": fallback_layer,
                "INPUT_RASTER": str(raster_path),
                "RASTER_BAND": 1,
                "COLUMN_PREFIX": "wp_",
                "STATISTICS": [1],
                "OUTPUT": "memory:",
            },
            context=context,
        )
        worldpop_by_code = {
            str(feature["unit_code"]): int(round(float(feature["wp_sum"] or 0.0)))
            for feature in result["OUTPUT"].getFeatures()
        }
        for unit in unresolved:
            population = worldpop_by_code.get(unit["unit_code"], 0)
            if population <= 0:
                continue
            unit["population"] = population
            unit["population_known"] = True
            unit["population_method"] = "worldpop_un_adjusted_zonal_sum"
            unit["population_source_id"] = fallback["source_id"]
    return units


def allocate_tile_names(
    candidates, selected_indexes, admin_assignments, units, minimum_share,
    priority_units, feedback,
):
    """Assign by population, keep one representative, then redistribute duplicates."""
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

    assignments = {}
    methods = {}
    rescue_assignments = set()
    population_by_code = {
        unit["unit_code"]: int(
            priority_units.get(unit["unit_code"], {}).get(
                "population", unit.get("population") or 0
            )
        )
        for unit in units
    }
    # Reserve one compatible tile for every real-city unit before the general
    # population-first pass. An augmenting-path match prevents a small city
    # from disappearing merely because a larger neighbour overlaps the same
    # limited set of tiles.
    priority_codes = {
        code for code, priority in priority_units.items()
        if int(priority.get("tier", 0)) >= 2
    }
    city_options = {
        code: sorted(
            [
                index for index in selected_indexes
                if admin_assignments[index] == unit_by_code[code]["admin1_code"]
                and overlaps[index].get(code, 0.0) > 0.0
            ],
            key=lambda index: (
                -overlaps[index][code], candidates[index]["tile_id"],
            ),
        )
        for code in priority_codes
    }
    tile_to_priority = {}

    def reserve_priority_tile(code, visited):
        for index in city_options[code]:
            if index in visited:
                continue
            visited.add(index)
            previous = tile_to_priority.get(index)
            if previous is None or reserve_priority_tile(previous, visited):
                tile_to_priority[index] = code
                return True
        return False

    for code in sorted(
        priority_codes,
        key=lambda value: (
            -population_by_code[value], len(city_options[value]), value,
        ),
    ):
        # A dense metro area can contain more qualifying real cities than the
        # finite hex grid has distinct same-owner tiles. Keep the maximum
        # compatible matching; unmatched cities remain source evidence but do
        # not become initial game cities in this resolution.
        if city_options[code]:
            reserve_priority_tile(code, set())

    # Pass 1: every tile goes to the highest-population same-owner unit that
    # overlaps it at all. Population ties use overlap, then stable unit code.
    for index in selected_indexes:
        if index in tile_to_priority:
            assignments[index] = tile_to_priority[index]
            methods[index] = "real_city_reservation"
            continue
        scores = overlaps[index]
        assignments[index] = sorted(
            scores,
            key=lambda code: (
                -population_by_code.get(code, 0), -scores[code], code,
            ),
        )[0]
        methods[index] = "population_first"

    counts = Counter(assignments.values())
    # Pass 2: duplicated units keep the tile where they occupy the most area.
    # Their other tiles become vacancies for units with no representative.
    vacant = []
    for code in sorted(counts):
        indexes = [index for index in selected_indexes if assignments[index] == code]
        representative = sorted(
            indexes,
            key=lambda index: (-overlaps[index].get(code, 0.0), candidates[index]["tile_id"]),
        )[0]
        for index in indexes:
            if index != representative:
                vacant.append(index)
                counts[code] -= 1

    # Pass 3: process unrepresented units by population. Each receives its
    # largest-overlap compatible vacancy. Unused vacancies return to their
    # largest-overlap same-owner unit, even if that creates a duplicate.
    missing_units = sorted(
        [unit for unit in units if counts.get(unit["unit_code"], 0) == 0],
        key=lambda unit: (-population_by_code[unit["unit_code"]], unit["unit_code"]),
    )
    available = set(vacant)
    for unit in missing_units:
        code = unit["unit_code"]
        options = [
            index for index in available
            if admin_assignments[index] == unit["admin1_code"]
            and overlaps[index].get(code, 0.0) > 0.0
        ]
        if not options:
            continue
        index = sorted(
            options,
            key=lambda value: (
                -overlaps[value][code], candidates[value]["tile_id"],
            ),
        )[0]
        assignments[index] = code
        counts[code] += 1
        available.remove(index)

    for index in sorted(available, key=lambda value: candidates[value]["tile_id"]):
        scores = overlaps[index]
        assignments[index] = sorted(scores, key=lambda code: (-scores[code], code))[0]
        counts[assignments[index]] += 1

    unit_to_tile = {}
    for code in sorted(counts):
        indexes = [index for index in selected_indexes if assignments[index] == code]
        if not indexes:
            continue
        representative = sorted(
            indexes,
            key=lambda index: (-overlaps[index].get(code, 0.0), candidates[index]["tile_id"]),
        )[0]
        unit_to_tile[code] = representative
        for index in indexes:
            dominant_code = sorted(
                overlaps[index], key=lambda value: (-overlaps[index][value], value)
            )[0]
            methods[index] = (
                "owner_nearest_fallback" if index in nearest_fallbacks
                else "unique_representation" if index == representative
                else "dominant_overlap_fill" if assignments[index] == dominant_code
                else "population_redistribution_fill"
            )
        share = overlaps[representative].get(code, 0.0) / candidates[representative]["geometry"].area()
        if share + 1e-12 < minimum_share:
            methods[representative] = "positive_overlap_representation"
            rescue_assignments.add(representative)
    mismatched = [
        candidates[index]["tile_id"] for index, code in assignments.items()
        if unit_by_code[code]["admin1_code"] != admin_assignments[index]
    ]
    if mismatched:
        raise QgsProcessingException(f"Naming/admin ownership mismatch: {mismatched}")
    feedback.pushInfo(
        f"Named {len(selected_indexes)} tiles from {len(units)} units; "
        f"represented {len(unit_to_tile)} unique units; "
        f"used {len(rescue_assignments)} positive-overlap representatives; "
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
    admin_codes = {admin["code"] for admin in admins}
    for index in selected:
        overlaps = {
            code: area for code, area in candidates[index]["overlaps"].items()
            if code in admin_codes
        }
        if not overlaps:
            raise QgsProcessingException(
                f"{country_iso3}-dominant tile {candidates[index]['tile_id']} has no same-country admin overlap"
            )
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
        display_language = settings.get("display_language", "en")
        if display_language not in {"en", "ko"}:
            raise QgsProcessingException(
                f"Unsupported display_language: {display_language}"
            )
        display_suffix = "en" if display_language == "en" else "ko"
        country_settings = configured_countries(settings)
        admins = [admin for item in country_settings for admin in item["admin1"]]
        admin_by_code = {admin["code"]: admin for admin in admins}
        country_iso3s = {item["country"]["iso3"] for item in country_settings}
        admin_country_by_code = {
            admin["code"]: item["country"]["iso3"]
            for item in country_settings for admin in item["admin1"]
        }
        national_population_totals = load_national_population_totals(
            root, settings, country_iso3s
        )

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
            ("country_iso3", QVariant.String),
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
        filter_values = country_iso3s
        for feature in source_layer.getFeatures():
            if str(feature[filter_field]) not in filter_values:
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
        if missing or len(admin_geometries) != len(admins):
            raise QgsProcessingException(
                f"Expected all {len(admins)} configured admin areas. Missing={missing}, found={len(admin_geometries)}"
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
        missing_countries = sorted(country_iso3s - set(country_geometries))
        if missing_countries:
            raise QgsProcessingException(f"Country geometries missing: {missing_countries}")
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
                # Preserve the existing KOR IDs while giving every newly
                # selected country its own collision-free stable namespace.
                tile_prefix = (
                    dominant_territory if dominant_territory in country_iso3s else "ATLAS"
                )
                tile_id = (
                    f"{tile_prefix}_{orientation[0].upper()}_"
                    f"R{row + 100000:06d}_C{col + 100000:06d}"
                )
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

        assignments = {}
        minimum_exceptions = {}
        selected_by_country = {}
        for item in country_settings:
            iso3 = item["country"]["iso3"]
            country_assignments, country_exceptions = allocate_tiles(
                candidates, item["admin1"], iso3, feedback
            )
            collisions = sorted(set(assignments) & set(country_assignments))
            if collisions:
                raise QgsProcessingException(
                    f"Country tile collision for {iso3}: {collisions}"
                )
            assignments.update(country_assignments)
            minimum_exceptions.update(country_exceptions)
            selected_by_country[iso3] = set(country_assignments)
        overrides = load_overrides(override_path)
        override_reasons = {}
        for candidate_index, code in list(assignments.items()):
            tile_id = candidates[candidate_index]["tile_id"]
            if tile_id not in overrides:
                continue
            target_code, reason = overrides[tile_id]
            if target_code not in admin_by_code:
                raise QgsProcessingException(f"Override for {tile_id} uses unknown admin code {target_code}")
            if admin_country_by_code[target_code] != candidates[candidate_index]["dominant_territory"]:
                raise QgsProcessingException(
                    f"Override for {tile_id} would cross a national boundary"
                )
            assignments[candidate_index] = target_code
            override_reasons[tile_id] = reason

        selected_indexes = sorted(assignments, key=lambda i: candidates[i]["tile_id"])
        selected_ids = {candidates[i]["tile_id"] for i in selected_indexes}
        neighbors = {tile_id: [] for tile_id in selected_ids}
        for position, first_index in enumerate(selected_indexes):
            first = candidates[first_index]
            for second_index in selected_indexes[position + 1 :]:
                second = candidates[second_index]
                if not first["geometry"].boundingBox().intersects(second["geometry"].boundingBox()):
                    continue
                # Normalize the GEOS intersection because floating-point noise
                # can turn a shared edge into a microscopic polygon sliver.
                shared_geometry = shared_edge_geometry(first["geometry"], second["geometry"])
                if shared_geometry.length() >= side * 0.5:
                    neighbors[first["tile_id"]].append(second["tile_id"])
                    neighbors[second["tile_id"]].append(first["tile_id"])
        for value in neighbors.values():
            value.sort()

        edge_members = {}
        for index in selected_indexes:
            for edge_key, geometry in hex_edge_records(candidates[index]["geometry"]):
                edge_members.setdefault(edge_key, []).append((index, geometry))
        admin_border_records = []
        for edge_key, members in sorted(edge_members.items()):
            if len(members) == 1:
                first_index, geometry = members[0]
                admin_border_records.append(
                    (
                        geometry, edge_key, "exterior", candidates[first_index]["tile_id"], "",
                        assignments[first_index], "",
                        candidates[first_index]["dominant_territory"], "",
                    )
                )
            elif len(members) == 2:
                (first_index, geometry), (second_index, _) = members
                first_admin = assignments[first_index]
                second_admin = assignments[second_index]
                if first_admin != second_admin:
                    first_country = candidates[first_index]["dominant_territory"]
                    second_country = candidates[second_index]["dominant_territory"]
                    admin_border_records.append(
                        (
                            geometry, edge_key,
                            "country" if first_country != second_country else "admin",
                            candidates[first_index]["tile_id"],
                            candidates[second_index]["tile_id"], first_admin, second_admin,
                            first_country, second_country,
                        )
                    )
            else:
                raise QgsProcessingException(
                    f"Hex edge {edge_key} belongs to {len(members)} selected tiles"
                )

        city_classes = settings["city_classification"]
        naming_units = []
        capital_unit_codes = set()
        city_by_unit_code = {}
        city_match_methods = {}
        tile_name_assignments = {}
        tile_name_overlaps = {}
        tile_name_methods = {}
        unique_unit_tiles = {}
        for item in country_settings:
            iso3 = item["country"]["iso3"]
            city_records = load_city_source(root, item)
            country_admin_geometries = {
                code: geometry for code, geometry in admin_geometries.items()
                if admin_country_by_code[code] == iso3
            }
            country_units = build_naming_units(
                root, item, target_crs, context, country_admin_geometries, city_records
            )
            country_cities, country_match_methods = match_cities_to_naming_units(
                city_records, country_units, target_crs, context
            )
            country_capitals = {
                code for code, city in country_cities.items() if city["is_capital"]
            }
            priority_units = {
                unit["unit_code"]: {
                    "tier": (
                        4 if unit["unit_code"] in country_capitals
                        else 2 if unit["unit_code"] in country_cities
                        else 1
                    ),
                    "population": int(
                        country_cities.get(unit["unit_code"], unit)["population"] or 0
                    ),
                }
                for unit in country_units
            }
            country_indexes = sorted(
                selected_by_country[iso3], key=lambda i: candidates[i]["tile_id"]
            )
            name_assignments, name_overlaps, name_methods, unit_tiles = allocate_tile_names(
                candidates, country_indexes, assignments, country_units,
                float(item["tile_naming"]["minimum_tile_share"]),
                priority_units, feedback,
            )
            naming_units.extend(country_units)
            capital_unit_codes.update(country_capitals)
            city_by_unit_code.update(country_cities)
            city_match_methods.update(country_match_methods)
            tile_name_assignments.update(name_assignments)
            tile_name_overlaps.update(name_overlaps)
            tile_name_methods.update(name_methods)
            unique_unit_tiles.update(unit_tiles)
        naming_unit_by_code = {unit["unit_code"]: unit for unit in naming_units}

        capital_border_records = []
        for edge_key, members in sorted(edge_members.items()):
            capital_members = [
                (index, geometry) for index, geometry in members
                if tile_name_assignments.get(index) in capital_unit_codes
            ]
            if len(capital_members) != 1:
                continue
            index, geometry = capital_members[0]
            capital_code = tile_name_assignments[index]
            if len(members) == 2:
                other_index = next(value[0] for value in members if value[0] != index)
                if tile_name_assignments.get(other_index) == capital_code:
                    continue
            capital_border_records.append(
                (geometry, edge_key, capital_code, candidates[index]["tile_id"])
            )

        unrepresented_city_units = sorted(set(city_by_unit_code) - set(unique_unit_tiles))
        city_anchor_by_index = {
            unique_unit_tiles[code]: city for code, city in city_by_unit_code.items()
            if code in unique_unit_tiles
        }

        (tile_populations, raw_population_sums, tile_population_methods,
         tile_population_source_ids) = allocate_tile_populations(
            root, country_settings, candidates, selected_by_country,
            target_crs, context, national_population_totals, city_anchor_by_index,
        )
        feedback.pushInfo(
            "Allocated exact national populations: "
            + ", ".join(
                f"{iso3}={national_population_totals[iso3]:,}"
                for iso3 in sorted(national_population_totals)
            )
        )

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
            ("population_year", QVariant.Int),
            ("population_method", QVariant.String),
            ("population_source_id", QVariant.String),
            ("city_name_ko", QVariant.String), ("city_name_en", QVariant.String),
            ("city_class", QVariant.String), ("is_capital", QVariant.Bool),
            ("is_initial_city", QVariant.Bool),
            ("city_upgrade_eligible", QVariant.Bool),
            ("map_class", QVariant.String),
            ("tile_name_code", QVariant.String), ("tile_name_ko", QVariant.String),
            ("tile_name_en", QVariant.String), ("tile_name_method", QVariant.String),
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
            population = int(tile_populations[index])
            is_initial_city = index in city_anchor_by_index
            city_class = (
                "metropolis"
                if is_initial_city
                and population >= int(city_classes["metropolis_population_min"])
                else "city"
                if is_initial_city
                else None
            )
            # Capital status follows the final tile name and controls only the
            # yellow group outline; fill remains admin/city/metropolis.
            is_capital = naming_code in capital_unit_codes
            city_upgrade_eligible = (
                not is_initial_city and not is_capital
                and population >= int(city_classes["city_population_min"])
            )
            district_slots = 3 if city_class == "metropolis" else 2 if city_class == "city" else 1
            overlap = candidate["overlaps"].get(code, 0.0)
            feature = QgsFeature(tile_layer.fields())
            feature.setGeometry(candidate["geometry"])
            values = {
                "tile_id": candidate["tile_id"],
                "country_iso3": candidate["dominant_territory"],
                "admin1_code": code, "admin1_name_ko": admin["name_ko"],
                "admin1_name_en": admin["name_en"], "area_km2": candidate["geometry"].area() / 1_000_000.0,
                "land_ratio": candidate["land_area"] / candidate["geometry"].area(),
                "is_coastal": candidate["land_area"] / candidate["geometry"].area() < 0.999,
                "center_x": candidate["cx"], "center_y": candidate["cy"],
                "neighbor_ids": json.dumps(neighbors[candidate["tile_id"]], separators=(",", ":")),
                "population": population,
                "population_year": int(settings["population_model"]["national_totals_year"]),
                "population_method": tile_population_methods[index],
                "population_source_id": tile_population_source_ids[index],
                "city_name_ko": naming_unit["name_ko"] if city_class or is_capital else None,
                "city_name_en": naming_unit["name_en"] if city_class or is_capital else None,
                "city_class": city_class, "is_capital": is_capital,
                "is_initial_city": is_initial_city,
                "city_upgrade_eligible": city_upgrade_eligible,
                "map_class": city_class or "admin",
                "tile_name_code": naming_code,
                "tile_name_ko": naming_unit["name_ko"],
                "tile_name_en": naming_unit["name_en"],
                "tile_name_method": tile_name_methods[index],
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
                [code, admin_country_by_code[code], admin["name_ko"], admin["name_en"],
                 admin_source_names[code],
                 int(settings["source"]["source_year"]), int(admin["target_tiles"]),
                 int(admin.get("minimum_tiles", 0)), counts[code]]
            )
            admin_features.append(feature)
        admin_layer.dataProvider().addFeatures(admin_features)

        naming_fields = QgsFields()
        for name, kind in (
            ("unit_code", QVariant.String), ("admin1_code", QVariant.String),
            ("name_ko", QVariant.String), ("name_en", QVariant.String),
            ("population", QVariant.LongLong), ("population_known", QVariant.Bool),
            ("population_method", QVariant.String),
            ("population_source_id", QVariant.String),
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
                    unit["population_known"], unit["population_method"],
                    unit["population_source_id"], unit["source_names"], unit["source_year"],
                ]
            )
            naming_features.append(feature)
        naming_layer.dataProvider().addFeatures(naming_features)

        border_fields = QgsFields()
        for name, kind in (
            ("edge_key", QVariant.String), ("edge_type", QVariant.String),
            ("tile_id_a", QVariant.String), ("tile_id_b", QVariant.String),
            ("admin_a", QVariant.String), ("admin_b", QVariant.String),
            ("country_a", QVariant.String), ("country_b", QVariant.String),
        ):
            border_fields.append(QgsField(name, kind))
        border_layer = memory_layer("LineString", target_crs, "admin1_tile_borders", border_fields)
        border_features = []
        for (
            geometry, edge_key, edge_type, tile_a, tile_b, admin_a, admin_b,
            country_a, country_b,
        ) in admin_border_records:
            feature = QgsFeature(border_layer.fields())
            feature.setGeometry(geometry)
            feature.setAttributes(
                [edge_key, edge_type, tile_a, tile_b, admin_a, admin_b, country_a, country_b]
            )
            border_features.append(feature)
        border_layer.dataProvider().addFeatures(border_features)

        capital_border_fields = QgsFields()
        for name, kind in (
            ("edge_key", QVariant.String), ("capital_code", QVariant.String),
            ("tile_id", QVariant.String),
        ):
            capital_border_fields.append(QgsField(name, kind))
        capital_border_layer = memory_layer(
            "LineString", target_crs, "capital_tile_outlines", capital_border_fields
        )
        capital_border_features = []
        for geometry, edge_key, capital_code, tile_id in capital_border_records:
            feature = QgsFeature(capital_border_layer.fields())
            feature.setGeometry(geometry)
            feature.setAttributes([edge_key, capital_code, tile_id])
            capital_border_features.append(feature)
        capital_border_layer.dataProvider().addFeatures(capital_border_features)

        write_gpkg_layer(admin_layer, gpkg_path, "admin1_source", True)
        write_gpkg_layer(candidate_layer, gpkg_path, "hex_candidates", False)
        write_gpkg_layer(tile_layer, gpkg_path, "korea_tiles", False)
        write_gpkg_layer(naming_layer, gpkg_path, "admin2_naming_source", False)
        write_gpkg_layer(border_layer, gpkg_path, "admin1_tile_borders", False)
        write_gpkg_layer(capital_border_layer, gpkg_path, "capital_tile_outlines", False)
        feedback.pushInfo(f"Wrote GeoPackage: {gpkg_path}")
        feedback.setProgress(88)

        # Reload persisted layers so the project contains relative GeoPackage paths.
        persisted_tiles = QgsVectorLayer(
            f"{gpkg_path}|layername=korea_tiles", "Korean Peninsula game tiles", "ogr"
        )
        persisted_admin = QgsVectorLayer(f"{gpkg_path}|layername=admin1_source", "Real admin-1 reference", "ogr")
        persisted_admin_labels = QgsVectorLayer(f"{gpkg_path}|layername=admin1_source", "Admin names and tile counts", "ogr")
        persisted_candidates = QgsVectorLayer(f"{gpkg_path}|layername=hex_candidates", "Hex candidates", "ogr")
        persisted_naming = QgsVectorLayer(
            f"{gpkg_path}|layername=admin2_naming_source", "City-county naming reference", "ogr"
        )
        persisted_borders = QgsVectorLayer(f"{gpkg_path}|layername=admin1_tile_borders", "Game admin borders", "ogr")
        persisted_capital_borders = QgsVectorLayer(
            f"{gpkg_path}|layername=capital_tile_outlines", "Capital outlines", "ogr"
        )
        for layer in (
            persisted_tiles, persisted_admin, persisted_admin_labels, persisted_candidates,
            persisted_naming, persisted_borders, persisted_capital_borders,
        ):
            if not layer.isValid():
                raise QgsProcessingException(f"Failed to reload persisted layer: {layer.name()}")

        categories = []
        class_colors = settings["city_classification"]["colors"]
        category_labels = {
            "en": {
                "admin": "Administrative tile",
                "city": "City · population 100,000–999,999",
                "metropolis": "Metropolis · population 1,000,000+",
            },
            "ko": {
                "admin": "일반 행정구역",
                "city": "도시 · 인구 10만 이상 100만 미만",
                "metropolis": "대도시 · 인구 100만 이상",
            },
        }
        for value in ("admin", "city", "metropolis"):
            label = category_labels[display_language][value]
            symbol = QgsFillSymbol.createSimple(
                {"color": class_colors[value], "outline_color": "#6b737b", "outline_width": "0.25"}
            )
            categories.append(QgsRendererCategory(value, symbol, label))
        persisted_tiles.setRenderer(QgsCategorizedSymbolRenderer("map_class", categories))
        label_settings = QgsPalLayerSettings()
        label_settings.fieldName = (
            f"tile_name_{display_suffix} || CASE WHEN @map_scale < 350000 "
            "THEN '\\n' || tile_id ELSE '' END"
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
        admin_labels.fieldName = (
            f"admin1_name_{display_suffix} || ' (' || tile_count || ')'"
        )
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
        border_categories = []
        for value, color, width, label in (
            ("admin", "#151515", "0.8", "행정구역 경계"),
            ("country", "#050505", "1.35", "국가 경계"),
            ("exterior", "#151515", "0.8", "지도 외곽"),
        ):
            border_categories.append(
                QgsRendererCategory(
                    value,
                    QgsLineSymbol.createSimple(
                        {
                            "line_color": color, "line_width": width,
                            "capstyle": "round", "joinstyle": "round",
                        }
                    ),
                    label,
                )
            )
        persisted_borders.setRenderer(
            QgsCategorizedSymbolRenderer("edge_type", border_categories)
        )
        persisted_capital_borders.setRenderer(
            QgsSingleSymbolRenderer(
                QgsLineSymbol.createSimple(
                    {
                        "line_color": class_colors["capital_outline"],
                        "line_width": "1.4", "capstyle": "round", "joinstyle": "round",
                    }
                )
            )
        )
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
        project.setTitle("Atlas - Korean Peninsula Hex Map")
        root_node = project.layerTreeRoot()
        game_group = root_node.addGroup("Game Map")
        reference_group = root_node.addGroup("Validation Reference")
        project.addMapLayer(persisted_tiles, False)
        project.addMapLayer(persisted_admin_labels, False)
        project.addMapLayer(persisted_capital_borders, False)
        project.addMapLayer(persisted_borders, False)
        game_group.addLayer(persisted_admin_labels)
        game_group.addLayer(persisted_capital_borders)
        game_group.addLayer(persisted_borders)
        game_group.addLayer(persisted_tiles)
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
            [persisted_admin_labels, persisted_capital_borders, persisted_borders, persisted_tiles],
            preview_path,
        )

        report_lines = [
            "# Atlas Korean Peninsula tile allocation report", "",
            f"Generated: {datetime.now(timezone.utc).isoformat()}", "",
            f"- Orientation: `{orientation}`", f"- Final tiles: **{len(selected_indexes)}**",
            f"- Target tile area: {settings['grid']['target_area_km2']} km2", "",
            "- Country selection: dominant overlap among nearby countries and ocean; no fixed national total",
            "- Country ownership: a tile and its assigned Admin-1 always belong to the same dominant country",
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
                "- First pass: every tile goes to its highest-population overlapping same-owner unit",
                "- Duplicate pass: each unit keeps its largest-overlap representative tile",
                "- Redistribution: unrepresented units take compatible vacancies in population order",
                "- Candidate threshold: any positive overlap; no minimum share",
                f"- Naming units: {len(naming_units)}",
                f"- Uniquely represented units: {len(unique_unit_tiles)}",
                f"- Positive-overlap representatives below the legacy 5% reporting threshold: "
                f"{sum(1 for method in tile_name_methods.values() if method == 'positive_overlap_representation')}",
                f"- Dominant-overlap fill tiles: "
                f"{sum(1 for method in tile_name_methods.values() if method == 'dominant_overlap_fill')}",
                f"- Population-redistribution fill tiles: "
                f"{sum(1 for method in tile_name_methods.values() if method == 'population_redistribution_fill')}",
                f"- Same-owner nearest-boundary fallbacks: "
                f"{sum(1 for method in tile_name_methods.values() if method == 'owner_nearest_fallback')}",
            ]
        )
        population_method_counts = Counter(
            unit["population_method"] for unit in naming_units
        )
        tile_class_counts = Counter(
            "metropolis"
            if index in city_anchor_by_index
            and tile_populations[index] >= int(city_classes["metropolis_population_min"])
            else "city"
            if index in city_anchor_by_index
            else "admin"
            for index in selected_indexes
        )
        upgrade_eligible_count = sum(
            1 for index in selected_indexes
            if index not in city_anchor_by_index
            and tile_name_assignments[index] not in capital_unit_codes
            and tile_populations[index] >= int(city_classes["city_population_min"])
        )
        country_population_sums = Counter()
        for index in selected_indexes:
            country_population_sums[candidates[index]["dominant_territory"]] += (
                tile_populations[index]
            )
        report_lines.extend(
            [
                "", "## Initial cities and game population", "",
                "Each real city receives one representative anchor tile with its GeoNames city population.",
                "WorldPop distributes the residual population; UN WPP fixes the exact national total.",
                "Non-city tiles over 100,000 residents are upgrade-eligible, not automatically cities.", "",
                f"- Capital tiles outlined in yellow: "
                f"{sum(1 for index in selected_indexes if tile_name_assignments[index] in capital_unit_codes)}",
                f"- Metropolis tiles: {tile_class_counts.get('metropolis', 0)}",
                f"- City tiles: {tile_class_counts.get('city', 0)}",
                f"- Player city-upgrade eligible tiles: {upgrade_eligible_count}",
                f"- Qualifying real cities without a distinct tile at this resolution: "
                f"{len(unrepresented_city_units)}",
            ]
        )
        for code in unrepresented_city_units:
            city = city_by_unit_code[code]
            report_lines.append(
                f"  - `{code}`: {city['name_en']} ({int(city['population']):,})"
            )
        for iso3 in sorted(national_population_totals):
            report_lines.append(
                f"- {iso3}: tile sum {country_population_sums[iso3]:,}; "
                f"UN WPP target {national_population_totals[iso3]:,}; "
                f"raw WorldPop weight sum {raw_population_sums[iso3]:,.2f}"
            )
        report_lines.extend(
            [
                "", "Naming-unit populations remain internal allocation evidence only:",
                f"- GeoNames ADM2 populations: {population_method_counts.get('geonames_adm2', 0)}",
                f"- GeoNames populated-place recoveries: "
                f"{sum(count for method, count in population_method_counts.items() if method.startswith('geonames_populated_place'))}",
                f"- WorldPop naming-unit recoveries: "
                f"{population_method_counts.get('worldpop_un_adjusted_zonal_sum', 0)}",
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
