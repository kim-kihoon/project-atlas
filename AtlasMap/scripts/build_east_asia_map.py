"""QGIS Processing script that builds the Atlas East Asia map."""

from collections import Counter, defaultdict
from datetime import datetime, timezone
import csv
import gc
import gzip
import io
import importlib
import itertools
import json
import math
import os
from pathlib import Path
import re
import sys
import time
import uuid
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
    QgsSpatialIndex,
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
_DLL_DIRECTORY_HANDLES = []


def tr(text):
    return QCoreApplication.translate("AtlasKoreaBuild", text)


def resolve(root, relative_path):
    path = (root / relative_path).resolve()
    if root != path and root not in path.parents:
        raise QgsProcessingException(f"Path escapes project root: {relative_path}")
    return path


def vector_source_uri(root, relative_path, archive_member=None):
    """Return a GDAL URI while keeping every configured path project-relative."""
    path = resolve(root, relative_path)
    if archive_member:
        member = str(archive_member).replace("\\", "/").lstrip("/")
        return f"/vsizip/{path.as_posix()}/{member}"
    return str(path)


def configured_countries(root, settings):
    primary = {
        "country": settings["country"], "city_source": settings["city_source"],
        "admin1_source": settings["admin1_source"],
        "tile_naming": settings["tile_naming"],
        "population_fallback": settings["population_fallback"],
        "naming_coverage_fallback": settings["naming_coverage_fallback"],
        "admin1": settings["admin1"],
    }
    additional = [
        {**item, "naming_coverage_fallback": settings["naming_coverage_fallback"]}
        for item in settings.get("additional_countries", [])
    ]
    registry_path = settings.get("globalization", {}).get("country_registry_path")
    registry_countries = []
    if registry_path:
        path = resolve(root, registry_path)
        if not path.exists():
            raise QgsProcessingException(
                f"Country registry does not exist; run build_country_registry.py: {path}"
            )
        registry = json.loads(path.read_text(encoding="utf-8"))
        registry_countries = [
            {**item, "naming_coverage_fallback": settings["naming_coverage_fallback"]}
            for item in registry.get("countries", [])
        ]
    countries = [primary, *additional, *registry_countries]
    iso3s = [item["country"]["iso3"] for item in countries]
    if len(iso3s) != len(set(iso3s)):
        raise QgsProcessingException(f"Duplicate country registry entries: {iso3s}")
    return countries


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


def generate_spherical_cells(root, settings, extent_wgs84, target_crs, context):
    """Enumerate canonical ISEA3H cells and project only their display geometry.

    DGGAL owns identity, spherical area and adjacency. QGIS projection is used
    only for regional overlap analysis and display; it never creates topology.
    """
    runtime = resolve(root, ".runtime/dggal")
    if str(runtime) not in sys.path:
        sys.path.insert(0, str(runtime))
    runtime_bin = runtime / "bin"
    if runtime_bin.exists():
        os.environ["PATH"] = f"{runtime_bin}{os.pathsep}{os.environ.get('PATH', '')}"
        if hasattr(os, "add_dll_directory"):
            _DLL_DIRECTORY_HANDLES.append(os.add_dll_directory(str(runtime_bin)))
    try:
        from dggal import (
            Application, Array, Degrees, GeoExtent, GeoPoint, ISEA3H,
            pydggal_setup,
        )
    except ImportError as exc:
        raise QgsProcessingException(
            "DGGAL is unavailable. Run scripts/setup_dggs_windows.ps1 or "
            "scripts/setup_dggs_mac.sh first."
        ) from exc

    application = Application(appGlobals=globals())
    pydggal_setup(application)
    dggrs = ISEA3H()
    contract = settings["globalization"]["global_grid"]
    level = int(contract["level"])
    chunk_level = int(contract.get("chunk_level", 7))
    if chunk_level < 0 or chunk_level >= level:
        raise QgsProcessingException(
            f"Invalid ISEA3H chunk level {chunk_level}; expected 0 <= chunk < {level}"
        )
    edge_refinement = int(contract.get("edge_refinement", 0))
    buffer_degrees = float(contract.get("candidate_bbox_buffer_degrees", 2.0))
    west = max(-180.0, float(extent_wgs84.xMinimum()) - buffer_degrees)
    south = max(-90.0, float(extent_wgs84.yMinimum()) - buffer_degrees)
    east = min(180.0, float(extent_wgs84.xMaximum()) + buffer_degrees)
    north = min(90.0, float(extent_wgs84.yMaximum()) + buffer_degrees)
    query_extent = GeoExtent(
        GeoPoint(Degrees(south), Degrees(west)),
        GeoPoint(Degrees(north), Degrees(east)),
    )
    zones = list(dggrs.listZones(level, query_extent))
    zones.sort(key=lambda zone: str(dggrs.getZoneTextID(zone)))
    global_count = int(dggrs.countZones(level))
    expected_count = int(contract["global_cell_count"])
    if global_count != expected_count:
        raise QgsProcessingException(
            f"ISEA3H global count mismatch: {global_count} != {expected_count}"
        )

    wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")
    transform = QgsCoordinateTransform(wgs84, target_crs, context.transformContext())
    cells = []
    for zone in zones:
        zone_id = str(dggrs.getZoneTextID(zone))
        tile_id = f"ATLAS_ISEA3H_L{level}_{zone_id}"
        edge_count = int(dggrs.countZoneEdges(zone))
        if edge_count not in {5, 6}:
            raise QgsProcessingException(
                f"Unexpected ISEA3H edge count for {zone_id}: {edge_count}"
            )
        neighbor_zones = list(dggrs.getZoneNeighbors(zone, Array("<int>")))
        neighbor_ids = [
            f"ATLAS_ISEA3H_L{level}_{dggrs.getZoneTextID(value)}"
            for value in neighbor_zones
        ]
        if len(neighbor_ids) != edge_count:
            raise QgsProcessingException(
                f"Neighbor/edge mismatch for {zone_id}: {len(neighbor_ids)} != {edge_count}"
            )
        refined = list(dggrs.getZoneRefinedWGS84Vertices(zone, edge_refinement))
        if len(refined) % edge_count:
            raise QgsProcessingException(
                f"Refined boundary cannot be split into logical sides: {zone_id}"
            )
        points_wgs84 = [QgsPointXY(float(value.lon), float(value.lat)) for value in refined]
        polygon = QgsGeometry.fromPolygonXY([points_wgs84 + [points_wgs84[0]]])
        polygon.transform(transform)
        if not polygon.isGeosValid():
            polygon = polygon.makeValid()
        if polygon.isEmpty():
            raise QgsProcessingException(f"Empty projected ISEA3H cell: {zone_id}")

        segments_per_side = len(points_wgs84) // edge_count
        # DGGAL guarantees the neighbor set but does not guarantee that its
        # returned order matches the refined boundary's side order. Match the
        # two one-to-one on the sphere: the centroid across a side is nearest
        # that side's midpoint. With at most six edges, exhaustive assignment
        # is deterministic and inexpensive.
        def unit_vector(lon, lat):
            lon_r = math.radians(float(lon))
            lat_r = math.radians(float(lat))
            cos_lat = math.cos(lat_r)
            return (
                cos_lat * math.cos(lon_r),
                cos_lat * math.sin(lon_r),
                math.sin(lat_r),
            )

        side_vectors = []
        for side_index in range(edge_count):
            start = side_index * segments_per_side
            first_middle = points_wgs84[
                (start + segments_per_side // 2) % len(points_wgs84)
            ]
            second_middle = points_wgs84[
                (start + (segments_per_side + 1) // 2) % len(points_wgs84)
            ]
            first_vector = unit_vector(first_middle.x(), first_middle.y())
            second_vector = unit_vector(second_middle.x(), second_middle.y())
            vector = tuple(a + b for a, b in zip(first_vector, second_vector))
            magnitude = math.sqrt(sum(value * value for value in vector))
            side_vectors.append(tuple(value / magnitude for value in vector))
        neighbor_vectors = []
        for neighbor_zone in neighbor_zones:
            neighbor_centroid = dggrs.getZoneWGS84Centroid(neighbor_zone)
            neighbor_vectors.append(
                unit_vector(neighbor_centroid.lon, neighbor_centroid.lat)
            )
        def assignment_cost(side, neighbor):
            return 1.0 - sum(
                side_vectors[side][axis] * neighbor_vectors[neighbor][axis]
                for axis in range(3)
            )

        nearest_assignment = tuple(
            min(range(edge_count), key=lambda neighbor: (assignment_cost(side, neighbor), neighbor))
            for side in range(edge_count)
        )
        best_assignment = (
            nearest_assignment
            if len(set(nearest_assignment)) == edge_count
            else min(
                itertools.permutations(range(edge_count)),
                key=lambda assignment: (
                    sum(
                        assignment_cost(side, assignment[side])
                        for side in range(edge_count)
                    ),
                    assignment,
                ),
            )
        )
        ordered_neighbor_ids = [neighbor_ids[index] for index in best_assignment]
        edge_records = []
        for side_index, neighbor_id in enumerate(ordered_neighbor_ids):
            start = side_index * segments_per_side
            side_points = [
                points_wgs84[(start + offset) % len(points_wgs84)]
                for offset in range(segments_per_side + 1)
            ]
            side_geometry = QgsGeometry.fromPolylineXY(side_points)
            side_geometry.transform(transform)
            edge_key = "|".join(sorted((tile_id, neighbor_id)))
            edge_records.append((edge_key, side_geometry, neighbor_id))

        centroid = dggrs.getZoneWGS84Centroid(zone)
        center_lon = float(centroid.lon)
        center_lat = float(centroid.lat)
        center_unit = unit_vector(center_lon, center_lat)
        chunk_zone = dggrs.getZoneFromWGS84Centroid(chunk_level, centroid)
        if int(dggrs.getZoneLevel(chunk_zone)) != chunk_level:
            raise QgsProcessingException(
                f"Could not resolve level-{chunk_level} chunk for {zone_id}"
            )
        chunk_zone_id = str(dggrs.getZoneTextID(chunk_zone))
        center_geometry = QgsGeometry.fromPointXY(
            QgsPointXY(center_lon, center_lat)
        )
        center_geometry.transform(transform)
        center = center_geometry.asPoint()
        cells.append(
            {
                "tile_id": tile_id,
                "dggs_zone_id": zone_id,
                "dggs_level": level,
                "cell_type": "pentagon" if edge_count == 5 else "hexagon",
                "cell_area_m2": float(dggrs.getZoneArea(zone)),
                "row": -1,
                "col": -1,
                "cx": float(center.x()),
                "cy": float(center.y()),
                "center_lon": center_lon,
                "center_lat": center_lat,
                "center_unit": center_unit,
                "chunk_id": f"ATLAS_ISEA3H_L{chunk_level}_{chunk_zone_id}",
                "geometry": polygon,
                "edge_records": edge_records,
                "canonical_neighbor_ids": sorted(neighbor_ids),
                "side_neighbor_ids": ordered_neighbor_ids,
            }
        )
    return cells


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
            and unit["unit_code"].split(":", 1)[-1] == city["canonical"]
        ]
        if containing:
            unit = sorted(containing, key=lambda value: value["unit_code"])[0]
            method = "point_in_naming_unit"
        else:
            # A city point outside every compatible naming polygon remains
            # source evidence. Nearest-only matching can attach an unrelated
            # city to a simplified or misplaced district polygon.
            continue
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
    for suffix in (
        " special administrative region", " autonomous region", " municipality",
        " prefecture", " province", " district", " county", " city",
    ):
        value = value.replace(suffix, "")
    value = re.sub(r"-(si|gun|gu)$", "", value)
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-")


def display_unit_name(value):
    value = re.sub(r"\s*\[[^]]*\]\s*", "", value.strip())
    # Keep -gu because it denotes a district, not an independent city. Metro
    # districts normally dissolve to their Admin-1 name; retaining the suffix
    # prevents an exceptional district from masquerading as a city named Seo.
    return re.sub(r"-(si|gun)$", "", value, flags=re.IGNORECASE)


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
    source_uri = vector_source_uri(
        root, naming["boundary_path"], naming.get("boundary_archive_member")
    )
    source_layer = QgsVectorLayer(source_uri, "geoboundaries_admin2", "ogr")
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
    boundary_filter_field = naming.get("boundary_filter_field")
    boundary_filter_value = str(naming.get("boundary_filter_value", ""))
    for feature in source_layer.getFeatures():
        if (
            boundary_filter_field
            and str(feature[boundary_filter_field]) != boundary_filter_value
        ):
            continue
        geometry = QgsGeometry(feature.geometry())
        geometry.transform(transform)
        if not geometry.isGeosValid():
            geometry = geometry.makeValid()
        if geometry.isEmpty():
            continue
        source_name = str(feature["shapeName"])
        canonical = normalized_unit_name(source_name)
        documented_admins = sorted(code for code, name in populations if name == canonical)
        admin_scores = {}
        for code, admin_geometry in admin_geometries.items():
            if not geometry.boundingBox().intersects(admin_geometry.boundingBox()):
                continue
            area = geometry.intersection(admin_geometry).area()
            if area > 0.0:
                admin_scores[code] = area
        # Naming and ownership are separate. Prefer spatial parentage, then use
        # one unambiguous configured population parent when globally simplified
        # ADM1 geometry omits an ADM2 island. This is the same fallback for every
        # country and never changes tile ownership.
        if admin_scores:
            admin_code = sorted(
                admin_scores, key=lambda code: (-admin_scores[code], code)
            )[0]
        elif len(documented_admins) == 1 and documented_admins[0] in admin_by_code:
            admin_code = documented_admins[0]
        else:
            continue
        reassigned_from_documented_admin = bool(
            documented_admins and admin_code not in documented_admins
        )
        if admin_code in aggregate_codes and not reassigned_from_documented_admin:
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
            if not population and len(documented_admins) == 1:
                population = populations.get((documented_admins[0], canonical), {})
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
        if naming.get("require_same_admin1", False):
            geometry = geometry.intersection(admin_geometries[admin_code])
            if geometry.isEmpty():
                continue
        unit = parts.setdefault(unit_code, values)
        unit["source_names"].add(source_name)
        unit["geometries"].append(geometry)
    units = []
    for unit_code in sorted(parts):
        unit = parts[unit_code]
        source_geometries = unit.pop("geometries")
        if unit["admin1_code"] in aggregate_codes:
            geometry = QgsGeometry(admin_geometries[unit["admin1_code"]])
        else:
            geometry = QgsGeometry.unaryUnion(source_geometries)
        polygon_parts = [
            part for part in geometry.asGeometryCollection()
            if QgsWkbTypes.geometryType(part.wkbType())
            == QgsWkbTypes.PolygonGeometry
            and part.area() > 0.0
        ]
        if not polygon_parts:
            continue
        geometry = QgsGeometry.unaryUnion(polygon_parts)
        geometry.convertToMultiType()
        unit["geometry"] = geometry
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
    coverage_fallback = settings["naming_coverage_fallback"]
    if coverage_fallback["policy"] != "admin1_name_when_no_adm2_positive_overlap":
        raise QgsProcessingException(
            f"Unsupported naming coverage fallback: {coverage_fallback['policy']}"
        )
    for admin_code in sorted(admin_geometries):
        admin = admin_by_code[admin_code]
        geometry = QgsGeometry(admin_geometries[admin_code])
        geometry.convertToMultiType()
        units.append({
            "unit_code": f"{admin_code}:__admin1_fallback__",
            "admin1_code": admin_code,
            "name_ko": admin["name_ko"],
            "name_en": admin["name_en"],
            "population": 0,
            "population_known": True,
            "population_method": "admin1_coverage_fallback",
            "population_source_id": str(naming["snapshot_version"]),
            "source_names": "Admin-1 coverage fallback",
            "source_year": int(naming["boundary_year"]),
            "is_coverage_fallback": True,
            "geometry": geometry,
        })
    for unit in units:
        unit.setdefault("is_coverage_fallback", False)
    return units


def allocate_tile_names(
    candidates, selected_indexes, units, minimum_share,
    priority_units, tile_admin_assignments, require_same_admin1, feedback,
):
    """Assign positive-overlap naming units without crossing country borders."""
    overlaps = {}
    coverage_fallbacks = set()
    regular_units = [unit for unit in units if not unit["is_coverage_fallback"]]
    fallback_by_admin = {
        unit["admin1_code"]: unit for unit in units if unit["is_coverage_fallback"]
    }
    unit_by_fid = {}
    naming_spatial_index = QgsSpatialIndex()
    for fid, unit in enumerate(regular_units):
        feature = QgsFeature()
        feature.setId(fid)
        feature.setGeometry(unit["geometry"])
        naming_spatial_index.addFeature(feature)
        unit_by_fid[fid] = unit
    for index in selected_indexes:
        tile = candidates[index]
        scores = {}
        eligible_units = [
            unit_by_fid[fid]
            for fid in naming_spatial_index.intersects(tile["geometry"].boundingBox())
            if not require_same_admin1
            or unit_by_fid[fid]["admin1_code"] == tile_admin_assignments[index]
        ]
        for unit in eligible_units:
            geometry = unit["geometry"]
            if not tile["geometry"].boundingBox().intersects(geometry.boundingBox()):
                continue
            area = tile["geometry"].intersection(geometry).area()
            if area > 0:
                scores[unit["unit_code"]] = area
        if not scores:
            fallback = fallback_by_admin.get(tile_admin_assignments[index])
            area = (
                tile["geometry"].intersection(fallback["geometry"]).area()
                if fallback else 0.0
            )
            if area <= 0.0:
                raise QgsProcessingException(
                    f"No positive-overlap same-country naming unit for {tile['tile_id']}"
                )
            scores[fallback["unit_code"]] = area
            coverage_fallbacks.add(index)
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
    # Pass 1: process naming units globally in descending population order.
    # Each unit reserves its maximum-overlap still-unclaimed tile. A smaller
    # unit can therefore never take a better compatible tile from a larger one.
    unit_to_tile = {}
    available = set(selected_indexes)
    ordered_units = sorted(
        regular_units,
        key=lambda unit: (-population_by_code[unit["unit_code"]], unit["unit_code"]),
    )
    for unit in ordered_units:
        code = unit["unit_code"]
        options = [
            index for index in available
            if overlaps[index].get(code, 0.0) > 0.0
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
        unit_to_tile[code] = index
        available.remove(index)

    # Pass 2: fill remaining tiles with their greatest-overlap intersecting
    # unit. Population is only a deterministic tie-break after area, so it
    # controls representative priority without distorting residual geography.
    for index in sorted(available, key=lambda value: candidates[value]["tile_id"]):
        scores = overlaps[index]
        assignments[index] = sorted(
            scores,
            key=lambda code: (
                -scores[code], -population_by_code.get(code, 0), code,
            ),
        )[0]

    counts = Counter(assignments.values())
    for code in sorted(counts):
        indexes = [index for index in selected_indexes if assignments[index] == code]
        if not indexes:
            continue
        is_fallback = code.endswith(":__admin1_fallback__")
        representative = unit_to_tile.get(code)
        if is_fallback:
            for index in indexes:
                methods[index] = "admin1_coverage_fallback"
            continue
        if representative is None:
            representative = sorted(
                indexes,
                key=lambda index: (
                    -overlaps[index].get(code, 0.0), candidates[index]["tile_id"]
                ),
            )[0]
            unit_to_tile[code] = representative
        for index in indexes:
            dominant_code = sorted(
                overlaps[index], key=lambda value: (-overlaps[index][value], value)
            )[0]
            methods[index] = (
                "unique_representation" if index == representative
                else "dominant_overlap_fill" if assignments[index] == dominant_code
                else "population_redistribution_fill"
            )
        share = overlaps[representative].get(code, 0.0) / candidates[representative]["geometry"].area()
        if share + 1e-12 < minimum_share:
            methods[representative] = "positive_overlap_representation"
            rescue_assignments.add(representative)
    feedback.pushInfo(
        f"Named {len(selected_indexes)} tiles from {len(units)} units; "
        f"represented {len(unit_to_tile)} unique units; "
        f"used {len(rescue_assignments)} positive-overlap representatives; "
        f"used {len(coverage_fallbacks)} Admin-1 coverage fallbacks"
    )
    return assignments, overlaps, methods, unit_to_tile


def allocate_tiles(candidates, admins, country_iso3, minimum_tiles, feedback):
    """Assign dominant admins, then rescue feasible zero-tile official admins."""
    selected = [
        i for i, item in enumerate(candidates)
        if item["dominant_territory"] == country_iso3
    ]
    selected.sort(key=lambda i: candidates[i]["tile_id"])
    if not selected:
        raise QgsProcessingException(f"No candidate is dominated by {country_iso3}")
    assignments = {}
    representation_indexes = set()
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

    counts = Counter(assignments.values())
    if minimum_tiles > 1:
        raise QgsProcessingException(
            "Only a one-tile Admin-1 representation floor is currently supported"
        )
    if minimum_tiles == 1:
        missing_codes = sorted(code for code in admin_codes if counts[code] == 0)
        eligible = {
            code: [
                index for index in selected
                if candidates[index]["overlaps"].get(code, 0.0) > 0.0
            ]
            for code in missing_codes
        }
        missing_codes.sort(key=lambda code: (len(eligible[code]), code))
        for code in missing_codes:
            choices = [
                index for index in eligible[code]
                if index not in representation_indexes
                and counts[assignments[index]] > minimum_tiles
            ]
            choices.sort(
                key=lambda index: (
                    -candidates[index]["overlaps"][code],
                    candidates[index]["tile_id"],
                )
            )
            if not choices:
                feedback.pushWarning(
                    f"Cannot provide one same-country representative tile for {code} "
                    "without removing another official Admin-1's last tile; "
                    "recording the area as infeasible at this grid resolution"
                )
                continue
            index = choices[0]
            previous = assignments[index]
            assignments[index] = code
            counts[previous] -= 1
            counts[code] += 1
            representation_indexes.add(index)

    feedback.pushInfo(
        f"Selected {len(selected)} {country_iso3}-dominant tiles; "
        f"reserved {len(representation_indexes)} same-country Admin-1 representatives"
    )
    return assignments, representation_indexes


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


def render_preview(layers, output_path, display_crs, transform_context):
    settings = QgsMapSettings()
    settings.setLayers(layers)
    settings.setDestinationCrs(display_crs)
    settings.setTransformContext(transform_context)
    extent_transform = QgsCoordinateTransform(
        layers[-1].crs(), display_crs, transform_context
    )
    extent = extent_transform.transformBoundingBox(layers[-1].extent())
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


def merged_line_chains(grouped_geometries, snap_tolerance):
    """Join topology sides whose projected endpoints differ only by tolerance."""
    result = []
    for group_key in sorted(grouped_geometries):
        geometries = grouped_geometries[group_key]
        edges = []
        adjacency = defaultdict(list)

        def node_key(point):
            return (
                round(point.x() / snap_tolerance),
                round(point.y() / snap_tolerance),
            )

        for geometry in geometries:
            parts = geometry.asGeometryCollection() if geometry.isMultipart() else [geometry]
            for part in parts:
                points = list(part.asPolyline())
                if len(points) < 2:
                    continue
                first_key = node_key(points[0])
                last_key = node_key(points[-1])
                edge_index = len(edges)
                edges.append((points, first_key, last_key))
                adjacency[first_key].append(edge_index)
                adjacency[last_key].append(edge_index)
        unvisited = set(range(len(edges)))
        chains = []

        def walk(start_node, first_edge):
            chain = []
            used = 0
            current_node = start_node
            next_edge = first_edge
            while next_edge in unvisited:
                unvisited.remove(next_edge)
                points, first_key, last_key = edges[next_edge]
                if first_key == current_node:
                    oriented = list(points)
                    current_node = last_key
                else:
                    oriented = list(reversed(points))
                    current_node = first_key
                if chain:
                    oriented[0] = chain[-1]
                    chain.extend(oriented[1:])
                else:
                    chain.extend(oriented)
                used += 1
                candidates = sorted(
                    edge for edge in adjacency[current_node] if edge in unvisited
                )
                if len(adjacency[current_node]) != 2 or not candidates:
                    break
                next_edge = candidates[0]
            return chain, used

        branch_nodes = sorted(node for node, members in adjacency.items() if len(members) != 2)
        for start_node in branch_nodes:
            for edge_index in sorted(adjacency[start_node]):
                if edge_index in unvisited:
                    chains.append(walk(start_node, edge_index))
        while unvisited:
            edge_index = min(unvisited)
            _, first_key, _ = edges[edge_index]
            chains.append(walk(first_key, edge_index))
        for part_index, (points, side_count) in enumerate(chains):
            if len(points) >= 2:
                result.append(
                    (
                        group_key,
                        part_index,
                        side_count,
                        QgsGeometry.fromPolylineXY(points),
                    )
                )
    return result


class AtlasKoreaBuild(QgsProcessingAlgorithm):
    def name(self):
        return "atlas_east_asia_build"

    def displayName(self):
        return tr("Build Atlas East Asia hex map")

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
            QgsProcessingParameterFile(CONFIG, tr("atlas_east_asia.json"), extension="json")
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
        country_settings = configured_countries(root, settings)
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

        source_uri = vector_source_uri(
            root, settings["source"]["path"], settings["source"].get("archive_member")
        )
        source_layer = QgsVectorLayer(source_uri, "global_adm0", "ogr")
        if not source_layer.isValid():
            raise QgsProcessingException(f"Invalid source layer: {source_path}")
        analysis_crs_id = settings.get("analysis_crs", settings["crs"])
        display_crs_id = settings.get("display_crs", analysis_crs_id)
        target_crs = QgsCoordinateReferenceSystem(analysis_crs_id)
        if not target_crs.isValid():
            raise QgsProcessingException(f"Invalid analysis CRS: {analysis_crs_id}")
        display_crs = QgsCoordinateReferenceSystem(display_crs_id)
        if not display_crs.isValid():
            raise QgsProcessingException(f"Invalid display CRS: {display_crs_id}")
        global_transform = QgsCoordinateTransform(
            source_layer.crs(), target_crs, context.transformContext()
        )
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
        admin_source_years = {}
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
        # Administrative ownership uses a country-specific authoritative source.
        # The global source above remains only the nearby-country competitor layer.
        for item in country_settings:
            admin_source = item["admin1_source"]
            admin_source_path = resolve(root, admin_source["path"])
            country_layer = QgsVectorLayer(
                vector_source_uri(
                    root, admin_source["path"], admin_source.get("archive_member")
                ),
                f"{item['country']['iso3']}_admin1_source",
                "ogr",
            )
            if not country_layer.isValid():
                raise QgsProcessingException(
                    f"Invalid Admin-1 source: {admin_source_path}"
                )
            country_transform = QgsCoordinateTransform(
                country_layer.crs(), target_crs, context.transformContext()
            )
            configured_codes = {admin["code"] for admin in item["admin1"]}
            code_map = {
                str(raw): str(code)
                for raw, code in admin_source.get("code_map", {}).items()
            }
            geometry_parts = {}
            for feature in country_layer.getFeatures():
                source_filter = admin_source.get("filter_field")
                if (
                    source_filter
                    and str(feature[source_filter])
                    != str(admin_source.get("filter_value", ""))
                ):
                    continue
                raw_code = str(feature[admin_source["code_field"]])
                code = code_map.get(raw_code, raw_code)
                if code not in configured_codes:
                    continue
                geometry = QgsGeometry(feature.geometry())
                geometry.transform(country_transform)
                if not geometry.isGeosValid():
                    geometry = geometry.makeValid()
                if geometry.isEmpty():
                    raise QgsProcessingException(
                        f"Empty Admin-1 geometry after repair: {code}"
                    )
                geometry_parts.setdefault(code, []).append(geometry)
                admin_source_names[code] = str(feature[admin_source["name_field"]])
                admin_source_years[code] = int(admin_source["source_year"])
            for code, parts in geometry_parts.items():
                admin_geometries[code] = QgsGeometry.unaryUnion(parts)
        missing = sorted(set(admin_by_code) - set(admin_geometries))
        if missing or len(admin_geometries) != len(admins):
            raise QgsProcessingException(
                f"Expected all {len(admins)} configured admin areas. Missing={missing}, found={len(admin_geometries)}"
            )
        # Intersect individual polygon parts instead of sending a mainland hex
        # through a countrywide MultiPolygon containing thousands of remote
        # islands. Areas remain exact; bbox filtering only skips disjoint parts.
        admin_intersection_parts = {}
        admin_part_by_fid = {}
        admin_spatial_index = QgsSpatialIndex()
        admin_part_fid = 0
        for code, geometry in admin_geometries.items():
            parts = geometry.asGeometryCollection() if geometry.isMultipart() else [geometry]
            admin_intersection_parts[code] = [
                (part.boundingBox(), part) for part in parts if not part.isEmpty()
            ]
            for part_bbox, part in admin_intersection_parts[code]:
                feature = QgsFeature(admin_part_fid)
                feature.setGeometry(part)
                admin_spatial_index.addFeature(feature)
                admin_part_by_fid[admin_part_fid] = (code, part)
                admin_part_fid += 1

        # Build nearby country polygons from the same global Admin-1 source so
        # border and coastal cells can compare countries and ocean consistently.
        search_extent = QgsRectangle(source_country_extent)
        search_extent.grow(float(settings["grid"]["nearby_country_search_buffer_degrees"]))
        country_parts = {}
        for feature in source_layer.getFeatures():
            geometry = feature.geometry()
            if geometry.isEmpty() or not geometry.boundingBox().intersects(search_extent):
                continue
            code_field = settings["source"].get(
                "country_code_field", settings["source"]["country_filter_field"]
            )
            code = str(feature[code_field] or "")
            if not code:
                continue
            transformed = QgsGeometry(geometry)
            transformed.transform(global_transform)
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
        # For configured playable countries, national land is exactly the union
        # of that country's authoritative Admin-1 source. This keeps national
        # dominance and Admin-1 ownership on one internally consistent boundary.
        for iso3 in country_iso3s:
            parts = [
                geometry for code, geometry in admin_geometries.items()
                if admin_country_by_code[code] == iso3
            ]
            country_geometries[iso3] = QgsGeometry.unaryUnion(parts)
        non_playable_country_geometries = {
            code: geometry for code, geometry in country_geometries.items()
            if code not in country_iso3s
        }
        country_spatial_index = QgsSpatialIndex()
        country_by_fid = {}
        for fid, (code, geometry) in enumerate(sorted(non_playable_country_geometries.items())):
            feature = QgsFeature(fid)
            feature.setGeometry(geometry)
            country_spatial_index.addFeature(feature)
            country_by_fid[fid] = (code, geometry)
        feedback.pushInfo(f"Nearby country competitors: {', '.join(sorted(country_geometries))}")

        feedback.pushInfo(f"Loaded and reprojected {len(admin_geometries)} admin areas")
        feedback.setProgress(10)

        grid = settings["grid"]
        base_cells = generate_spherical_cells(
            root, settings, source_country_extent, target_crs, context
        )
        feedback.pushInfo(
            f"Enumerated {len(base_cells)} canonical ISEA3H cells near configured land"
        )
        candidates = []
        for base_cell in base_cells:
                geometry = base_cell["geometry"]
                overlaps = {}
                cell_bbox = geometry.boundingBox()
                for fid in admin_spatial_index.intersects(cell_bbox):
                    code, part = admin_part_by_fid[fid]
                    area = geometry.area() if part.contains(geometry) else geometry.intersection(part).area()
                    if area >= float(grid["candidate_min_overlap_m2"]):
                        overlaps[code] = overlaps.get(code, 0.0) + area
                if not overlaps:
                    continue
                land_area = sum(overlaps.values())
                # A playable country's land is the union of its Admin-1 areas,
                # so reuse the already exact Admin-1 intersections. This avoids
                # intersecting every hex with a second copy of the same detailed
                # coastline while keeping country and owner scores identical.
                country_overlaps = {
                    iso3: sum(
                        area for code, area in overlaps.items()
                        if admin_country_by_code[code] == iso3
                    )
                    for iso3 in country_iso3s
                }
                country_overlaps = {
                    code: area for code, area in country_overlaps.items()
                    if area >= float(grid["candidate_min_overlap_m2"])
                }
                for fid in country_spatial_index.intersects(cell_bbox):
                    code, country_geometry = country_by_fid[fid]
                    area = geometry.intersection(country_geometry).area()
                    if area >= float(grid["candidate_min_overlap_m2"]):
                        country_overlaps[code] = area
                non_playable_land_area = sum(
                    area for code, area in country_overlaps.items()
                    if code not in country_iso3s
                )
                ocean_area = max(
                    0.0,
                    geometry.area()
                    - sum(
                        country_overlaps.get(iso3, 0.0) for iso3 in country_iso3s
                    )
                    - non_playable_land_area,
                )
                territory_scores = dict(country_overlaps)
                territory_scores[grid["ocean_code"]] = ocean_area
                dominant_territory = sorted(
                    territory_scores,
                    key=lambda code: (-territory_scores[code], code),
                )[0]
                # IDs belong to the immutable grid coordinate, never to an
                # owner that can change when a boundary snapshot changes.
                candidates.append(
                    {
                        **base_cell,
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
        admin_representation_indexes = set()
        selected_by_country = {}
        for item in country_settings:
            iso3 = item["country"]["iso3"]
            country_assignments, country_representation_indexes = allocate_tiles(
                candidates, item["admin1"], iso3,
                int(settings["admin_assignment"]["minimum_tiles_per_admin"]),
                feedback,
            )
            collisions = sorted(set(assignments) & set(country_assignments))
            if collisions:
                raise QgsProcessingException(
                    f"Country tile collision for {iso3}: {collisions}"
                )
            assignments.update(country_assignments)
            admin_representation_indexes.update(country_representation_indexes)
            selected_by_country[iso3] = set(country_assignments)
        overrides = load_overrides(override_path)
        override_reasons = {}
        if overrides:
            raise QgsProcessingException(
                "Tile ownership overrides are disabled: every tile must retain "
                "its greatest-overlap country and Admin-1 owner"
            )

        selected_indexes = sorted(assignments, key=lambda i: candidates[i]["tile_id"])
        selected_ids = {candidates[i]["tile_id"] for i in selected_indexes}
        edge_members = {}
        for index in selected_indexes:
            for edge_key, geometry, _neighbor_id in candidates[index]["edge_records"]:
                edge_members.setdefault(edge_key, []).append((index, geometry))

        # Derive adjacency and borders from canonical DGGS neighbor-pair keys.
        # Each record is one complete logical cell side, even though its display
        # geometry contains several refined curve segments.
        neighbors = {tile_id: set() for tile_id in selected_ids}
        for members in edge_members.values():
            if len(members) != 2:
                continue
            first_index, second_index = members[0][0], members[1][0]
            first_id = candidates[first_index]["tile_id"]
            second_id = candidates[second_index]["tile_id"]
            neighbors[first_id].add(second_id)
            neighbors[second_id].add(first_id)
        neighbors = {
            tile_id: sorted(values) for tile_id, values in neighbors.items()
        }
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
            for unit in country_units:
                unit["allocation_population"] = int(
                    priority_units[unit["unit_code"]]["population"]
                )
            country_indexes = sorted(
                selected_by_country[iso3], key=lambda i: candidates[i]["tile_id"]
            )
            name_assignments, name_overlaps, name_methods, unit_tiles = allocate_tile_names(
                candidates, country_indexes, country_units,
                float(item["tile_naming"]["minimum_tile_share"]),
                priority_units, assignments,
                bool(item["tile_naming"].get("require_same_admin1", False)),
                feedback,
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
        capital_anchor_indexes = {
            unique_unit_tiles[code] for code in capital_unit_codes
            if code in unique_unit_tiles
        }
        capital_named_indexes = {
            index for index in selected_indexes
            if tile_name_assignments.get(index) in capital_unit_codes
        }

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

        capital_border_records = []
        for edge_key, members in sorted(edge_members.items()):
            capital_members = [
                (index, geometry) for index, geometry in members
                if index in capital_named_indexes
            ]
            capital_codes = {
                tile_name_assignments[index] for index, _ in capital_members
            }
            if not capital_members or (
                len(capital_members) == len(members) and len(capital_codes) == 1
            ):
                continue
            index, geometry = min(
                capital_members, key=lambda value: candidates[value[0]]["tile_id"]
            )
            capital_code = tile_name_assignments[index]
            capital_border_records.append(
                (geometry, edge_key, capital_code, candidates[index]["tile_id"])
            )

        unrepresented_city_units = sorted(set(city_by_unit_code) - set(unique_unit_tiles))
        city_anchor_by_index = {
            unique_unit_tiles[code]: city for code, city in city_by_unit_code.items()
            if code in unique_unit_tiles
        }
        city_map_class_by_code = {
            code: (
                "metropolis"
                if int(city_by_unit_code[code]["population"])
                >= int(city_classes["metropolis_population_min"])
                else "city"
            )
            for code in city_by_unit_code if code in unique_unit_tiles
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
            ("dggs_zone_id", QVariant.String),
            ("dggs_level", QVariant.Int),
            ("cell_type", QVariant.String),
            ("cell_area_km2", QVariant.Double),
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
        for index, candidate in enumerate(candidates):
            analysis_area = candidate["geometry"].area()
            same_country_overlaps = {
                code: area for code, area in candidate["overlaps"].items()
                if admin_country_by_code[code] == candidate["dominant_territory"]
            }
            best_admin = (
                sorted(same_country_overlaps, key=lambda code: (-same_country_overlaps[code], code))[0]
                if same_country_overlaps else None
            )
            best_overlap = same_country_overlaps.get(best_admin, 0.0) if best_admin else 0.0
            feature = QgsFeature(candidate_layer.fields())
            feature.setGeometry(candidate["geometry"])
            feature.setAttributes(
                [
                    candidate["tile_id"], candidate["dggs_zone_id"],
                    candidate["dggs_level"], candidate["cell_type"],
                    candidate["cell_area_m2"] / 1_000_000.0,
                    candidate["row"], candidate["col"],
                    candidate["land_area"] / 1_000_000.0,
                    candidate["land_area"] / analysis_area,
                    candidate["dominant_territory"],
                    candidate["ocean_area"] / analysis_area,
                    best_admin, best_overlap / 1_000_000.0,
                    index in assignments, assignments.get(index),
                    (
                        "admin1_representation"
                        if index in admin_representation_indexes
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
            ("tile_id", QVariant.String), ("dggs_zone_id", QVariant.String),
            ("dggs_level", QVariant.Int), ("cell_type", QVariant.String),
            ("country_iso3", QVariant.String),
            ("admin1_code", QVariant.String), ("admin1_name_ko", QVariant.String),
            ("admin1_name_en", QVariant.String), ("area_km2", QVariant.Double),
            ("land_ratio", QVariant.Double), ("is_coastal", QVariant.Bool),
            ("center_x", QVariant.Double), ("center_y", QVariant.Double),
            ("center_lon", QVariant.Double), ("center_lat", QVariant.Double),
            ("center_ux", QVariant.Double), ("center_uy", QVariant.Double),
            ("center_uz", QVariant.Double), ("chunk_id", QVariant.String),
            ("canonical_neighbor_ids", QVariant.String),
            ("side_neighbor_ids", QVariant.String),
            ("neighbor_ids", QVariant.String), ("population", QVariant.LongLong),
            ("population_year", QVariant.Int),
            ("population_method", QVariant.String),
            ("population_source_id", QVariant.String),
            ("city_name_ko", QVariant.String), ("city_name_en", QVariant.String),
            ("city_class", QVariant.String), ("is_capital", QVariant.Bool),
            ("is_capital_anchor", QVariant.Bool),
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
        tile_layer = memory_layer("Polygon", target_crs, "east_asia_tiles", tile_fields)
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
            # Capital-group status follows the final tile name. The yellow
            # outline follows exactly that complete naming-unit group, while
            # one representative anchor per country carries gameplay effects.
            is_capital = naming_code in capital_unit_codes
            is_capital_anchor = index in capital_anchor_indexes
            display_city_class = city_map_class_by_code.get(naming_code)
            city_upgrade_eligible = (
                not is_initial_city and not is_capital and not display_city_class
                and population >= int(city_classes["city_population_min"])
            )
            district_slots = 3 if city_class == "metropolis" else 2 if city_class == "city" else 1
            overlap = candidate["overlaps"].get(code, 0.0)
            feature = QgsFeature(tile_layer.fields())
            feature.setGeometry(candidate["geometry"])
            values = {
                "tile_id": candidate["tile_id"],
                "dggs_zone_id": candidate["dggs_zone_id"],
                "dggs_level": candidate["dggs_level"],
                "cell_type": candidate["cell_type"],
                "country_iso3": candidate["dominant_territory"],
                "admin1_code": code, "admin1_name_ko": admin["name_ko"],
                "admin1_name_en": admin["name_en"],
                "area_km2": candidate["cell_area_m2"] / 1_000_000.0,
                "land_ratio": candidate["land_area"] / candidate["geometry"].area(),
                "is_coastal": candidate["land_area"] / candidate["geometry"].area() < 0.999,
                "center_x": candidate["cx"], "center_y": candidate["cy"],
                "center_lon": candidate["center_lon"],
                "center_lat": candidate["center_lat"],
                "center_ux": candidate["center_unit"][0],
                "center_uy": candidate["center_unit"][1],
                "center_uz": candidate["center_unit"][2],
                "chunk_id": candidate["chunk_id"],
                "canonical_neighbor_ids": json.dumps(
                    candidate["canonical_neighbor_ids"], separators=(",", ":")),
                "side_neighbor_ids": json.dumps(
                    candidate["side_neighbor_ids"], separators=(",", ":")),
                "neighbor_ids": json.dumps(neighbors[candidate["tile_id"]], separators=(",", ":")),
                "population": population,
                "population_year": int(settings["population_model"]["national_totals_year"]),
                "population_method": tile_population_methods[index],
                "population_source_id": tile_population_source_ids[index],
                "city_name_ko": naming_unit["name_ko"] if display_city_class or is_capital else None,
                "city_name_en": naming_unit["name_en"] if display_city_class or is_capital else None,
                "city_class": city_class, "is_capital": is_capital,
                "is_capital_anchor": is_capital_anchor,
                "is_initial_city": is_initial_city,
                "city_upgrade_eligible": city_upgrade_eligible,
                "map_class": display_city_class or "admin",
                "tile_name_code": naming_code,
                "tile_name_ko": naming_unit["name_ko"],
                "tile_name_en": naming_unit["name_en"],
                "tile_name_method": tile_name_methods[index],
                "tile_name_overlap_km2": naming_overlap / 1_000_000.0,
                "district_slots": district_slots,
                "source_year": admin_source_years[code],
                "manual_override": False,
                "assignment_method": (
                    "admin1_representation"
                    if index in admin_representation_indexes
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
                 admin_source_years[code],
                 int(admin["target_tiles"]) if admin.get("target_tiles") is not None else None,
                 int(admin.get("minimum_tiles", 0)), counts[code]]
            )
            admin_features.append(feature)
        admin_layer.dataProvider().addFeatures(admin_features)

        naming_fields = QgsFields()
        for name, kind in (
            ("unit_code", QVariant.String), ("admin1_code", QVariant.String),
            ("name_ko", QVariant.String), ("name_en", QVariant.String),
            ("population", QVariant.LongLong), ("population_known", QVariant.Bool),
            ("allocation_population", QVariant.LongLong),
            ("population_method", QVariant.String),
            ("population_source_id", QVariant.String),
            ("is_coverage_fallback", QVariant.Bool),
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
                    unit["population_known"], unit["allocation_population"],
                    unit["population_method"],
                    unit["population_source_id"], unit["is_coverage_fallback"],
                    unit["source_names"], unit["source_year"],
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

        # Keep one-feature-per-logical-side layers above as validation evidence.
        # QGIS renders separate sub-pixel sides with a cap at every endpoint,
        # which resembles dots at an East Asia overview. Build additional
        # topology-derived continuous chains solely for presentation.
        admin_render_groups = defaultdict(list)
        for record in admin_border_records:
            geometry, _, edge_type, _, _, admin_a, admin_b, country_a, country_b = record
            if edge_type == "admin":
                boundary_key = ":".join(sorted((admin_a, admin_b)))
            elif edge_type == "country":
                boundary_key = ":".join(sorted((country_a, country_b)))
            else:
                boundary_key = country_a
            admin_render_groups[(edge_type, boundary_key)].append(geometry)
        chain_snap_tolerance = float(settings["map_styling"]["border_chain_snap_tolerance_m"])
        admin_render_chains = merged_line_chains(
            admin_render_groups, chain_snap_tolerance
        )
        render_border_fields = QgsFields()
        for name, kind in (
            ("chain_id", QVariant.String), ("edge_type", QVariant.String),
            ("boundary_key", QVariant.String), ("side_count", QVariant.Int),
        ):
            render_border_fields.append(QgsField(name, kind))
        render_border_layer = memory_layer(
            "LineString", target_crs, "admin1_border_render", render_border_fields
        )
        render_border_features = []
        for group_key, part_index, side_count, geometry in admin_render_chains:
            edge_type, boundary_key = group_key
            feature = QgsFeature(render_border_layer.fields())
            feature.setGeometry(geometry)
            feature.setAttributes(
                [f"{edge_type}:{boundary_key}:{part_index}", edge_type, boundary_key, side_count]
            )
            render_border_features.append(feature)
        render_border_layer.dataProvider().addFeatures(render_border_features)

        capital_render_groups = defaultdict(list)
        for geometry, _, capital_code, _ in capital_border_records:
            capital_render_groups[capital_code].append(geometry)
        capital_render_chains = merged_line_chains(
            capital_render_groups, chain_snap_tolerance
        )
        render_capital_fields = QgsFields()
        for name, kind in (
            ("chain_id", QVariant.String), ("capital_code", QVariant.String),
            ("side_count", QVariant.Int),
        ):
            render_capital_fields.append(QgsField(name, kind))
        render_capital_layer = memory_layer(
            "LineString", target_crs, "capital_outline_render", render_capital_fields
        )
        render_capital_features = []
        for capital_code, part_index, side_count, geometry in capital_render_chains:
            feature = QgsFeature(render_capital_layer.fields())
            feature.setGeometry(geometry)
            feature.setAttributes(
                [f"{capital_code}:{part_index}", capital_code, side_count]
            )
            render_capital_features.append(feature)
        render_capital_layer.dataProvider().addFeatures(render_capital_features)

        # Build a new GeoPackage beside the deliverable and replace the old
        # file only after every layer is written. QGIS/OGR's
        # CreateOrOverwriteFile fails on some Windows installations when the
        # destination GeoPackage already exists, which made repeat builds
        # fail even though the first build succeeded.
        staging_gpkg_path = gpkg_path.with_name(
            f".{gpkg_path.stem}.{uuid.uuid4().hex}.tmp.gpkg"
        )
        try:
            write_gpkg_layer(admin_layer, staging_gpkg_path, "admin1_source", True)
            write_gpkg_layer(candidate_layer, staging_gpkg_path, "hex_candidates", False)
            write_gpkg_layer(tile_layer, staging_gpkg_path, "east_asia_tiles", False)
            write_gpkg_layer(naming_layer, staging_gpkg_path, "admin2_naming_source", False)
            write_gpkg_layer(border_layer, staging_gpkg_path, "admin1_tile_borders", False)
            write_gpkg_layer(
                render_border_layer, staging_gpkg_path, "admin1_border_render", False
            )
            write_gpkg_layer(
                capital_border_layer,
                staging_gpkg_path,
                "capital_tile_outlines",
                False,
            )
            write_gpkg_layer(
                render_capital_layer,
                staging_gpkg_path,
                "capital_outline_render",
                False,
            )
            replace_error = None
            for _ in range(8):
                try:
                    gc.collect()
                    QCoreApplication.processEvents()
                    os.replace(staging_gpkg_path, gpkg_path)
                    replace_error = None
                    break
                except PermissionError as exc:
                    replace_error = exc
                    time.sleep(0.25)
            if replace_error is not None:
                raise QgsProcessingException(
                    "Cannot replace the existing GeoPackage. Close QGIS or any "
                    f"application using {gpkg_path.name}, then rebuild."
                ) from replace_error
        finally:
            if staging_gpkg_path.exists():
                staging_gpkg_path.unlink()
        feedback.pushInfo(f"Wrote GeoPackage: {gpkg_path}")
        feedback.setProgress(88)

        # Reload persisted layers so the project contains relative GeoPackage paths.
        persisted_tiles = QgsVectorLayer(
            f"{gpkg_path}|layername=east_asia_tiles", "East Asia game tiles", "ogr"
        )
        persisted_admin = QgsVectorLayer(f"{gpkg_path}|layername=admin1_source", "Real admin-1 reference", "ogr")
        persisted_admin_labels = QgsVectorLayer(f"{gpkg_path}|layername=admin1_source", "Admin names and tile counts", "ogr")
        persisted_candidates = QgsVectorLayer(f"{gpkg_path}|layername=hex_candidates", "Hex candidates", "ogr")
        persisted_naming = QgsVectorLayer(
            f"{gpkg_path}|layername=admin2_naming_source", "City-county naming reference", "ogr"
        )
        persisted_borders = QgsVectorLayer(f"{gpkg_path}|layername=admin1_border_render", "Game admin borders", "ogr")
        persisted_capital_borders = QgsVectorLayer(
            f"{gpkg_path}|layername=capital_outline_render", "Capital outlines", "ogr"
        )
        for layer in (
            persisted_tiles, persisted_admin, persisted_admin_labels, persisted_candidates,
            persisted_naming, persisted_borders, persisted_capital_borders,
        ):
            if not layer.isValid():
                raise QgsProcessingException(f"Failed to reload persisted layer: {layer.name()}")

        categories = []
        class_colors = settings["city_classification"]["colors"]
        map_styling = settings["map_styling"]
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
                {
                    "color": class_colors[value],
                    "outline_color": map_styling["tile_outline_color"],
                    "outline_width": str(map_styling["tile_outline_width_mm"]),
                }
            )
            categories.append(QgsRendererCategory(value, symbol, label))
        persisted_tiles.setRenderer(QgsCategorizedSymbolRenderer("map_class", categories))
        label_settings = QgsPalLayerSettings()
        label_settings.fieldName = (
            f"tile_name_{display_suffix} || CASE WHEN @map_scale < "
            f"{int(settings['labeling']['tile_id_max_scale'])} "
            "THEN '\\n' || tile_id ELSE '' END"
        )
        label_settings.isExpression = True
        label_settings.scaleVisibility = True
        # QgsPalLayerSettings uses `minimumScale` for the most zoomed-out
        # denominator and `maximumScale` for the most zoomed-in denominator.
        # Leave the zoomed-in end unlimited so labels never disappear while
        # the user zooms closer into the hex grid.
        label_settings.minimumScale = float(settings["labeling"]["tile_name_min_scale"])
        label_settings.maximumScale = 0
        label_settings.centroidInside = True
        label_settings.fitInPolygonOnly = True
        label_settings.priority = 8
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
        admin_labels.scaleVisibility = True
        admin_labels.minimumScale = float(settings["labeling"]["admin_name_min_scale"])
        admin_labels.maximumScale = float(settings["labeling"]["admin_name_max_scale"])
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
        border_style_by_type = {
            "admin": (
                map_styling["admin_border_color"],
                map_styling["admin_border_width_mm"],
            ),
            "country": (
                map_styling["country_border_color"],
                map_styling["country_border_width_mm"],
            ),
            "exterior": (
                map_styling["exterior_border_color"],
                map_styling["exterior_border_width_mm"],
            ),
        }
        for value, color, width, label in (
            ("admin", "#151515", "0.8", "행정구역 경계"),
            ("country", "#050505", "1.35", "국가 경계"),
            ("exterior", "#151515", "0.8", "지도 외곽"),
        ):
            color, width = border_style_by_type[value]
            border_categories.append(
                QgsRendererCategory(
                    value,
                    QgsLineSymbol.createSimple(
                        {
                            "line_color": color, "line_width": str(width),
                            "capstyle": map_styling["border_cap_style"],
                            "joinstyle": map_styling["border_join_style"],
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
                        "line_width": str(map_styling["capital_border_width_mm"]),
                        "capstyle": map_styling["border_cap_style"],
                        "joinstyle": map_styling["border_join_style"],
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
        project.setCrs(display_crs)
        try:
            project.setFilePathStorage(Qgis.FilePathType.Relative)
        except AttributeError:
            project.setFilePathStorage(QgsProject.FilePathType.Relative)
        project.setTitle("Atlas - East Asia Hex Map")
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

        # The portable project keeps labels enabled.  The overview is rendered
        # without text so headless cross-platform font substitution cannot
        # obscure the tile colors and topology during visual QA.
        persisted_tiles.setLabelsEnabled(False)
        persisted_admin_labels.setLabelsEnabled(False)
        overview_categories = []
        for value in ("admin", "city", "metropolis"):
            overview_categories.append(
                QgsRendererCategory(
                    value,
                    QgsFillSymbol.createSimple(
                        {"color": class_colors[value], "outline_style": "no"}
                    ),
                    value,
                )
            )
        persisted_tiles.setRenderer(
            QgsCategorizedSymbolRenderer("map_class", overview_categories)
        )
        render_preview(
            [persisted_admin_labels, persisted_capital_borders, persisted_borders, persisted_tiles],
            preview_path,
            display_crs,
            context.transformContext(),
        )

        report_lines = [
            "# Atlas East Asia tile allocation report", "",
            f"Generated: {datetime.now(timezone.utc).isoformat()}", "",
            "- Grid: OGC ISEA3H level-11 spherical DGGRS",
            f"- Analysis/intersection CRS: `{analysis_crs_id}`",
            f"- QGIS display CRS: `{display_crs_id}`",
            f"- Final tiles: **{len(selected_indexes)}**",
            f"- Canonical hexagon area: {grid['target_area_km2']} km2", "",
            "- Country selection: dominant overlap among nearby countries and ocean; no fixed national total",
            "- Country ownership: a tile and its assigned Admin-1 always belong to the same dominant country",
            "- Assignment policy: one positive-overlap same-country representative per feasible official Admin-1; remaining tiles use greatest overlap",
            "- National ownership and target counts are never overridden", "",
            "| Code | Admin area | Target | Actual | Difference |",
            "| --- | --- | ---: | ---: | ---: |",
        ]
        for admin in admins:
            actual = counts[admin["code"]]
            target = admin.get("target_tiles")
            difference = actual - int(target) if target is not None else "N/A"
            report_lines.append(
                f"| {admin['code']} | {admin['name_ko']} / {admin['name_en']} | "
                f"{target if target is not None else 'N/A'} | {actual} | "
                f"{difference} |"
            )
        report_lines.extend([
            "", "## Admin-1 representation assignments", "",
        ])
        if admin_representation_indexes:
            for index in sorted(
                admin_representation_indexes,
                key=lambda value: candidates[value]["tile_id"],
            ):
                candidate = candidates[index]
                assigned = assignments[index]
                same_country_codes = [
                    code for code in candidate["overlaps"]
                    if admin_country_by_code[code] == candidate["dominant_territory"]
                ]
                dominant = sorted(
                    same_country_codes,
                    key=lambda code: (-candidate["overlaps"][code], code),
                )[0]
                report_lines.append(
                    f"- `{candidate['tile_id']}`: {dominant} -> {assigned}; "
                    f"assigned overlap {candidate['overlaps'][assigned] / 1_000_000.0:.3f} km2"
                )
        else:
            report_lines.append("- None required; every official Admin-1 already had a dominant tile.")
        report_lines.extend(["", "## Tile naming", ""])
        report_lines.extend(
            [
                "- Hard constraint: tile name must positively overlap the tile and remain inside its final country and Admin-1 owner",
                "- Representative pass: units reserve their best free tile in descending population order",
                "- Fill pass: remaining tiles use greatest overlap; ties use population then stable code",
                "- Candidate threshold: any positive overlap; no minimum share",
                f"- Naming units: {len(naming_units)}",
                f"- Uniquely represented units: {len(unique_unit_tiles)}",
                f"- Positive-overlap representatives below the legacy 5% reporting threshold: "
                f"{sum(1 for method in tile_name_methods.values() if method == 'positive_overlap_representation')}",
                f"- Dominant-overlap fill tiles: "
                f"{sum(1 for method in tile_name_methods.values() if method == 'dominant_overlap_fill')}",
                f"- Population-redistribution fill tiles: "
                f"{sum(1 for method in tile_name_methods.values() if method == 'population_redistribution_fill')}",
                f"- Same-country nearest-boundary fallbacks: "
                f"{sum(1 for method in tile_name_methods.values() if method == 'country_nearest_fallback')}",
                f"- Admin-1 coverage fallbacks (only when no eligible ADM2 overlaps): "
                f"{sum(1 for method in tile_name_methods.values() if method == 'admin1_coverage_fallback')}",
            ]
        )
        population_method_counts = Counter(
            unit["population_method"] for unit in naming_units
        )
        tile_class_counts = Counter(
            city_map_class_by_code.get(tile_name_assignments[index], "admin")
            for index in selected_indexes
        )
        upgrade_eligible_count = sum(
            1 for index in selected_indexes
            if index not in city_anchor_by_index
            and tile_name_assignments[index] not in city_map_class_by_code
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
                "Every tile in a represented city-name group inherits the anchor city's display class without duplicating population.",
                "Non-city tiles over 100,000 residents are upgrade-eligible, not automatically cities.", "",
                f"- Capital tiles outlined in yellow: "
                f"{sum(1 for index in selected_indexes if tile_name_assignments[index] in capital_unit_codes)}",
                f"- Capital gameplay anchors: {len(capital_anchor_indexes)} (one per represented country)",
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
