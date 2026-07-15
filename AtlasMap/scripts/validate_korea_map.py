"""Release-gate validation for the Atlas Korea QGIS map."""

from collections import Counter
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import zipfile

from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (
    QgsGeometry,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingOutputFile,
    QgsProcessingParameterFile,
    QgsVectorLayer,
)


CONFIG = "CONFIG"
OUTPUT_REPORT = "OUTPUT_REPORT"


def tr(text):
    return QCoreApplication.translate("AtlasKoreaValidate", text)


def resolve(root, relative_path):
    path = (root / relative_path).resolve()
    if root != path and root not in path.parents:
        raise QgsProcessingException(f"Path escapes project root: {relative_path}")
    return path


def polygon_edges(geometry):
    if geometry.isMultipart():
        polygons = geometry.asMultiPolygon()
        if len(polygons) != 1:
            return []
        ring = polygons[0][0]
    else:
        polygons = geometry.asPolygon()
        if not polygons:
            return []
        ring = polygons[0]
    points = list(ring)
    if len(points) > 1 and points[0] == points[-1]:
        points.pop()
    if len(points) != 6:
        return []
    return [
        math.hypot(points[(i + 1) % 6].x() - points[i].x(), points[(i + 1) % 6].y() - points[i].y())
        for i in range(6)
    ]


class AtlasKoreaValidate(QgsProcessingAlgorithm):
    def name(self):
        return "atlas_korea_validate"

    def displayName(self):
        return tr("Validate Atlas Korea hex map")

    def group(self):
        return tr("Atlas")

    def groupId(self):
        return "atlas"

    def shortHelpString(self):
        return tr("Validates dominant country/admin assignment, geometry, adjacency, CRS and path rules.")

    def createInstance(self):
        return AtlasKoreaValidate()

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFile(CONFIG, tr("atlas_korea.json"), extension="json"))
        self.addOutput(QgsProcessingOutputFile(OUTPUT_REPORT, tr("Validation report")))

    def processAlgorithm(self, parameters, context, feedback):
        config_path = Path(self.parameterAsFile(parameters, CONFIG, context)).resolve()
        root = config_path.parent.parent.resolve()
        settings = json.loads(config_path.read_text(encoding="utf-8"))
        validation = settings["validation"]
        gpkg = resolve(root, settings["outputs"]["geopackage"])
        project_path = resolve(root, settings["outputs"]["project"])
        report_path = resolve(root, settings["outputs"]["validation_report"])
        report_path.parent.mkdir(parents=True, exist_ok=True)
        layer = QgsVectorLayer(f"{gpkg}|layername=korea_tiles", "korea_tiles", "ogr")

        checks = []
        failures = []

        def check(name, passed, detail):
            checks.append((name, bool(passed), detail))
            if not passed:
                failures.append(f"{name}: {detail}")

        check("GeoPackage layer loads", layer.isValid(), str(gpkg))
        if not layer.isValid():
            report_path.write_text("# Validation failed\n\nGeoPackage layer does not load.\n", encoding="utf-8")
            raise QgsProcessingException(f"Invalid korea_tiles layer: {gpkg}")

        check("CRS", layer.crs().authid() == settings["crs"], layer.crs().authid())
        features = list(layer.getFeatures())
        country_iso3 = settings["country"]["iso3"]
        wrong_country = [
            str(feature["tile_id"]) for feature in features
            if str(feature["country_iso3"] or "") != country_iso3
        ]
        check("Final country code", not wrong_country, f"wrong_country={wrong_country}")

        ids = [str(feature["tile_id"] or "") for feature in features]
        blank_ids = [i for i in ids if not i]
        duplicate_ids = sorted(tile_id for tile_id, count in Counter(ids).items() if count > 1)
        check("Tile IDs present", not blank_ids, f"blank={len(blank_ids)}")
        check("Tile IDs unique", not duplicate_ids, f"duplicates={duplicate_ids}")

        targets = {item["code"]: int(item["target_tiles"]) for item in settings["admin1"]}
        minimums = {item["code"]: int(item.get("minimum_tiles", 0)) for item in settings["admin1"]}
        actual = Counter(str(feature["admin1_code"] or "") for feature in features)
        minimum_deficits = {
            code: actual.get(code, 0) - minimum for code, minimum in minimums.items()
            if actual.get(code, 0) < minimum
        }
        unexpected_codes = sorted(set(actual) - set(targets))
        check(
            "Admin minimum representation",
            not minimum_deficits and not unexpected_codes,
            f"deficits={minimum_deficits}, unexpected={unexpected_codes}",
        )
        invalid_assignment = [feature["tile_id"] for feature in features if not feature["admin1_code"]]
        check("Exactly one admin assignment", not invalid_assignment, f"invalid={invalid_assignment}")

        candidate_layer = QgsVectorLayer(f"{gpkg}|layername=hex_candidates", "hex_candidates", "ogr")
        candidate_features = list(candidate_layer.getFeatures()) if candidate_layer.isValid() else []
        best_admin_by_id = {
            str(feature["candidate_id"]): str(feature["best_admin"] or "")
            for feature in candidate_features
        }
        selected_candidate_ids = {
            str(feature["candidate_id"]) for feature in candidate_features if bool(feature["selected"])
        }
        invalid_territory_dominance = []
        for feature in candidate_features:
            try:
                scores = json.loads(str(feature["country_scores_json"] or "{}"))
                expected_dominant = sorted(scores, key=lambda code: (-float(scores[code]), code))[0]
            except (ValueError, TypeError, KeyError, IndexError, json.JSONDecodeError):
                invalid_territory_dominance.append(str(feature["candidate_id"]))
                continue
            if str(feature["dominant_territory"] or "") != expected_dominant:
                invalid_territory_dominance.append(str(feature["candidate_id"]))
        check(
            "Dominant country-or-ocean calculation",
            not invalid_territory_dominance,
            f"invalid={invalid_territory_dominance}",
        )
        expected_country_selection = {
            str(feature["candidate_id"]) for feature in candidate_features
            if str(feature["dominant_territory"] or "") == country_iso3
        }
        selection_difference = sorted(selected_candidate_ids.symmetric_difference(expected_country_selection))
        check(
            "Dominant-country tile selection",
            not selection_difference,
            f"selection_difference={selection_difference}",
        )
        check(
            "Derived final tile count",
            len(features) == len(expected_country_selection),
            f"actual={len(features)}, derived={len(expected_country_selection)}",
        )
        dominant_mismatches = [
            str(feature["tile_id"]) for feature in features
            if str(feature["assignment_method"] or "") == "dominant_overlap"
            and str(feature["admin1_code"] or "") != best_admin_by_id.get(str(feature["tile_id"]), "")
        ]
        allowed_methods = {"dominant_overlap", "minimum_representation", "manual_override"}
        invalid_methods = [
            (str(feature["tile_id"]), str(feature["assignment_method"] or ""))
            for feature in features if str(feature["assignment_method"] or "") not in allowed_methods
        ]
        check("Assignment methods", not invalid_methods, f"invalid={invalid_methods}")
        check("Dominant-overlap assignments", not dominant_mismatches, f"mismatches={dominant_mismatches}")

        required_naming_fields = {
            "tile_name_code", "tile_name_ko", "tile_name_en", "tile_name_method",
            "tile_name_population", "tile_name_overlap_km2", "map_class",
        }
        missing_naming_fields = sorted(required_naming_fields - set(layer.fields().names()))
        check("Tile naming fields", not missing_naming_fields, f"missing={missing_naming_fields}")
        blank_names = [
            str(feature["tile_id"]) for feature in features
            if not str(feature["tile_name_code"] or "").strip()
            or not str(feature["tile_name_ko"] or "").strip()
            or not str(feature["tile_name_en"] or "").strip()
        ] if not missing_naming_fields else ids
        check("Every tile has one display name", not blank_names, f"blank={blank_names}")
        allowed_naming_methods = {
            "unique_representation", "dominant_overlap_fill", "owner_nearest_fallback"
        }
        invalid_naming_methods = [
            (str(feature["tile_id"]), str(feature["tile_name_method"] or ""))
            for feature in features
            if str(feature["tile_name_method"] or "") not in allowed_naming_methods
        ] if not missing_naming_fields else []
        check("Tile naming methods", not invalid_naming_methods, f"invalid={invalid_naming_methods}")

        naming_layer = QgsVectorLayer(
            f"{gpkg}|layername=admin2_naming_source", "admin2_naming_source", "ogr"
        )
        naming_features = list(naming_layer.getFeatures()) if naming_layer.isValid() else []
        naming_by_code = {
            str(feature["unit_code"]): feature for feature in naming_features
        }
        check("Naming reference layer", naming_layer.isValid() and bool(naming_features),
              f"units={len(naming_features)}")
        ownership_name_mismatches = []
        for tile in features:
            unit = naming_by_code.get(str(tile["tile_name_code"] or ""))
            if unit is None or str(unit["admin1_code"] or "") != str(tile["admin1_code"] or ""):
                ownership_name_mismatches.append(
                    (str(tile["tile_id"]), str(tile["admin1_code"] or ""),
                     str(tile["tile_name_code"] or ""))
                )
        check("Tile name belongs to admin owner", not ownership_name_mismatches,
              f"mismatches={ownership_name_mismatches}")
        dominant_name_mismatches = []
        for tile in features:
            if str(tile["tile_name_method"] or "") != "dominant_overlap_fill":
                continue
            scores = {}
            for unit in naming_features:
                if str(unit["admin1_code"] or "") != str(tile["admin1_code"] or ""):
                    continue
                if not tile.geometry().boundingBox().intersects(unit.geometry().boundingBox()):
                    continue
                area = tile.geometry().intersection(unit.geometry()).area()
                if area > 0:
                    scores[str(unit["unit_code"])] = area
            expected = sorted(scores, key=lambda code: (-scores[code], code))[0] if scores else ""
            if str(tile["tile_name_code"] or "") != expected:
                dominant_name_mismatches.append((str(tile["tile_id"]), expected))
        check("Maximum-overlap default names", not dominant_name_mismatches,
              f"mismatches={dominant_name_mismatches}")

        final_name_counts = Counter(str(feature["tile_name_code"] or "") for feature in features)
        representation_errors = []
        representation_codes = []
        minimum_share = float(settings["tile_naming"]["minimum_tile_share"])
        for tile in features:
            if str(tile["tile_name_method"] or "") != "unique_representation":
                continue
            code = str(tile["tile_name_code"] or "")
            representation_codes.append(code)
            overlap_share = (
                float(tile["tile_name_overlap_km2"] or 0.0)
                / float(tile["area_km2"] or 1.0)
            )
            if code not in naming_by_code or overlap_share + 1e-9 < minimum_share:
                representation_errors.append(
                    (str(tile["tile_id"]), code, round(overlap_share, 4))
                )
        duplicate_representations = sorted(
            code for code, count in Counter(representation_codes).items() if count > 1
        )
        check("Unique first-pass representatives",
              not representation_errors and not duplicate_representations,
              f"invalid={representation_errors}, duplicates={duplicate_representations}")

        city_layer = QgsVectorLayer(f"{gpkg}|layername=city_markers", "city_markers", "ogr")
        city_features = list(city_layer.getFeatures()) if city_layer.isValid() else []
        city_min = int(settings["city_classification"]["city_population_min"])
        metropolis_min = int(settings["city_classification"]["metropolis_population_min"])
        invalid_city_markers = []
        city_by_unit = {}
        city_link_errors = []
        tiles_by_id = {str(tile["tile_id"]): tile for tile in features}
        for city in city_features:
            population = int(city["population"] or 0)
            expected_class = "metropolis" if population >= metropolis_min else "city"
            if population < city_min or str(city["city_class"] or "") != expected_class:
                invalid_city_markers.append(str(city["city_id"]))
            tile_id = str(city["tile_id"] or "")
            city_by_unit[str(city["unit_code"] or "")] = city
            if tile_id:
                linked_tile = tiles_by_id.get(tile_id)
                if (
                    linked_tile is None
                    or str(linked_tile["tile_name_code"] or "") != str(city["unit_code"] or "")
                    or str(linked_tile["admin1_code"] or "") != str(city["admin1_code"] or "")
                ):
                    city_link_errors.append(str(city["city_id"]))
        check("Population-based city markers", city_layer.isValid() and not invalid_city_markers,
              f"markers={len(city_features)}, invalid={invalid_city_markers}")
        check("City markers link to same-name owner tiles", not city_link_errors,
              f"invalid={city_link_errors}")
        capital_tiles = [tile for tile in features if str(tile["map_class"] or "") == "capital"]
        capital_markers = [city for city in city_features if bool(city["is_capital"])]
        check(
            "Exactly one capital tile",
            len(capital_tiles) == 1 and len(capital_markers) == 1
            and str(capital_tiles[0]["tile_name_code"] or "")
            == str(capital_markers[0]["unit_code"] or ""),
            f"tiles={len(capital_tiles)}, markers={len(capital_markers)}",
        )
        tile_city_mismatches = []
        for tile in features:
            tile_id = str(tile["tile_id"])
            city = city_by_unit.get(str(tile["tile_name_code"] or ""))
            if city:
                expected_map_class = "capital" if bool(city["is_capital"]) else str(city["city_class"])
                if (
                    str(tile["tile_name_ko"] or "") != str(city["city_name_ko"] or "")
                    or
                    str(tile["city_name_ko"] or "") != str(city["city_name_ko"] or "")
                    or str(tile["city_class"] or "") != str(city["city_class"] or "")
                    or str(tile["map_class"] or "") != expected_map_class
                ):
                    tile_city_mismatches.append(tile_id)
            elif str(tile["map_class"] or "") != "admin":
                tile_city_mismatches.append(tile_id)
        check("City class follows final same-owner tile name", not tile_city_mismatches,
              f"mismatches={tile_city_mismatches}")
        actual_map_classes = {str(tile["map_class"] or "") for tile in features}
        expected_map_classes = {"admin", "city", "metropolis", "capital"}
        check(
            "Exactly four tile color classes",
            actual_map_classes == expected_map_classes,
            f"actual={sorted(actual_map_classes)}",
        )
        colors = settings["city_classification"]["colors"]

        def relative_luminance(hex_color):
            values = [int(hex_color.lstrip("#")[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
            linear = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
                      for value in values]
            return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

        check(
            "Metropolis fill darker than city fill",
            relative_luminance(colors["metropolis"]) < relative_luminance(colors["city"]),
            f"city={colors['city']}, metropolis={colors['metropolis']}",
        )

        border_layer = QgsVectorLayer(
            f"{gpkg}|layername=admin1_tile_borders", "admin1_tile_borders", "ogr"
        )
        border_features = list(border_layer.getFeatures()) if border_layer.isValid() else []
        invalid_borders = [
            (str(border["tile_id_a"]), str(border["tile_id_b"]))
            for border in border_features
            if not str(border["admin_a"] or "")
            or not str(border["admin_b"] or "")
            or str(border["admin_a"]) == str(border["admin_b"])
            or border.geometry().isEmpty()
        ]
        check(
            "Admin borders separate different owners",
            border_layer.isValid() and bool(border_features) and not invalid_borders,
            f"segments={len(border_features)}, invalid={invalid_borders}",
        )

        target_area = float(settings["grid"]["target_area_km2"])
        area_tolerance = float(validation["area_relative_tolerance"])
        edge_tolerance = float(validation["regular_edge_relative_tolerance"])
        invalid_geometries = []
        invalid_hexagons = []
        invalid_areas = []
        for feature in features:
            geometry = feature.geometry()
            tile_id = feature["tile_id"]
            if geometry.isEmpty() or not geometry.isGeosValid():
                invalid_geometries.append(tile_id)
                continue
            edges = polygon_edges(geometry)
            if len(edges) != 6 or min(edges) <= 0 or (max(edges) - min(edges)) / (sum(edges) / 6.0) > edge_tolerance:
                invalid_hexagons.append(tile_id)
            area = geometry.area() / 1_000_000.0
            if abs(area - target_area) / target_area > area_tolerance:
                invalid_areas.append((tile_id, round(area, 6)))
        check("Valid geometries", not invalid_geometries, f"invalid={invalid_geometries}")
        check("Complete regular hexagons", not invalid_hexagons, f"invalid={invalid_hexagons}")
        check("Hex target area", not invalid_areas, f"outside_tolerance={invalid_areas}")

        overlap_tolerance = float(validation["overlap_area_tolerance_m2"])
        overlaps = []
        for index, first in enumerate(features):
            first_geometry = first.geometry()
            for second in features[index + 1 :]:
                second_geometry = second.geometry()
                if not first_geometry.boundingBox().intersects(second_geometry.boundingBox()):
                    continue
                area = first_geometry.intersection(second_geometry).area()
                if area > overlap_tolerance:
                    overlaps.append((first["tile_id"], second["tile_id"], round(area, 3)))
        check("No tile overlap", not overlaps, f"overlaps={overlaps[:20]}")

        id_set = set(ids)
        neighbor_map = {}
        malformed_neighbors = []
        for feature in features:
            tile_id = str(feature["tile_id"])
            try:
                values = json.loads(str(feature["neighbor_ids"] or "[]"))
                if not isinstance(values, list):
                    raise ValueError("not a list")
                neighbor_map[tile_id] = [str(value) for value in values]
            except (ValueError, TypeError, json.JSONDecodeError) as error:
                malformed_neighbors.append((tile_id, str(error)))
                neighbor_map[tile_id] = []
        missing_neighbors = sorted(
            (tile_id, neighbor) for tile_id, values in neighbor_map.items() for neighbor in values
            if neighbor not in id_set
        )
        asymmetric = sorted(
            (tile_id, neighbor) for tile_id, values in neighbor_map.items() for neighbor in values
            if neighbor in neighbor_map and tile_id not in neighbor_map[neighbor]
        )
        check("Neighbor JSON", not malformed_neighbors, f"malformed={malformed_neighbors}")
        check("Neighbor IDs exist", not missing_neighbors, f"missing={missing_neighbors}")
        check("Neighbor symmetry", not asymmetric, f"asymmetric={asymmetric}")

        # Inspect scripts and the embedded .qgs XML for machine-specific data paths.
        # Build the Unix pattern in parts so this validator does not flag its
        # own source. The Windows pattern excludes URL schemes such as https:/. 
        absolute_patterns = [
            re.compile("/" + r"Users/[^/\s<]+/"),
            re.compile(r"(?<![A-Za-z])[A-Za-z]:[\\/](?![\\/])[^\s<]+"),
        ]
        path_hits = []
        border_above_tiles = False
        files_to_scan = sorted((root / "scripts").glob("*"))
        for path in files_to_scan:
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for line_number, line in enumerate(text.splitlines(), 1):
                if any(pattern.search(line) for pattern in absolute_patterns):
                    path_hits.append(f"{path.relative_to(root)}:{line_number}")
        if project_path.exists():
            with zipfile.ZipFile(project_path) as archive:
                for member in archive.namelist():
                    if not member.endswith(".qgs"):
                        continue
                    text = archive.read(member).decode("utf-8", errors="replace")
                    border_position = text.find('name="Game admin borders"')
                    tile_position = text.find('name="Korea game tiles"')
                    border_above_tiles = (
                        border_position >= 0 and tile_position >= 0
                        and border_position < tile_position
                    )
                    for line_number, line in enumerate(text.splitlines(), 1):
                        if any(pattern.search(line) for pattern in absolute_patterns):
                            path_hits.append(f"{project_path.name}:{line_number}")
        check("Relative shared paths", not path_hits, f"absolute_path_hits={path_hits}")
        check(
            "Admin border layer renders above tile fills",
            border_above_tiles,
            f"border_above_tiles={border_above_tiles}",
        )

        lines = [
            "# Atlas Korea validation report", "",
            f"Generated: {datetime.now(timezone.utc).isoformat()}", "",
            f"Overall result: **{'PASS' if not failures else 'FAIL'}**", "",
            "| Check | Result | Detail |", "| --- | --- | --- |",
        ]
        for name, passed, detail in checks:
            safe_detail = str(detail).replace("|", "\\|").replace("\n", " ")
            lines.append(f"| {name} | {'PASS' if passed else 'FAIL'} | {safe_detail} |")
        lines.extend([
            "", "## Allocation", "",
            "Targets are advisory; minimums are validation gates.", "",
            "| Code | Target | Minimum | Actual | Difference |",
            "| --- | ---: | ---: | ---: | ---: |",
        ])
        for item in settings["admin1"]:
            code = item["code"]
            target = int(item["target_tiles"])
            value = actual.get(code, 0)
            lines.append(
                f"| {code} | {target} | {item.get('minimum_tiles', 0)} | {value} | {value - target} |"
            )
        report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        feedback.pushInfo(f"Validation report: {report_path}")
        feedback.setProgress(100)
        if failures:
            raise QgsProcessingException("Validation failed:\n- " + "\n- ".join(failures))
        return {OUTPUT_REPORT: str(report_path)}
