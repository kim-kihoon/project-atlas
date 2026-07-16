"""Release-gate validation for the Atlas Korea QGIS map."""

from collections import Counter
import csv
from datetime import datetime, timezone
import json
import gzip
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


def load_national_population_totals(root, settings, country_iso3s):
    model = settings["population_model"]
    path = resolve(root, model["national_totals_path"])
    year = int(model["national_totals_year"])
    variant = str(model["national_totals_variant"])
    multiplier = 1000 if model.get("national_totals_units") == "thousands" else 1
    totals = {}
    with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            iso3 = str(row.get("ISO3_code") or "")
            if (
                iso3 in country_iso3s
                and str(row.get("Variant") or "") == variant
                and int(row.get("Time") or -1) == year
            ):
                totals[iso3] = int(round(float(row["PopTotal"]) * multiplier))
    return totals


def configured_countries(settings):
    primary = {
        "country": settings["country"],
        "admin1_source": settings["admin1_source"],
        "city_source": settings["city_source"],
        "tile_naming": settings["tile_naming"],
        "population_fallback": settings["population_fallback"],
        "admin1": settings["admin1"],
    }
    return [primary, *settings.get("additional_countries", [])]


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


def hex_edge_keys(geometry, precision=3):
    polygon = geometry.asMultiPolygon()[0] if geometry.isMultipart() else geometry.asPolygon()
    if not polygon:
        return []
    ring = polygon[0]
    points = list(ring[:-1] if ring and ring[0] == ring[-1] else ring)
    keys = []
    for index, first in enumerate(points):
        second = points[(index + 1) % len(points)]
        endpoints = sorted(
            (
                (round(first.x(), precision), round(first.y(), precision)),
                (round(second.x(), precision), round(second.y(), precision)),
            )
        )
        keys.append(
            f"{endpoints[0][0]:.{precision}f},{endpoints[0][1]:.{precision}f}|"
            f"{endpoints[1][0]:.{precision}f},{endpoints[1][1]:.{precision}f}"
        )
    return keys


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
        country_settings = configured_countries(settings)
        country_iso3s = {item["country"]["iso3"] for item in country_settings}
        admins = [admin for item in country_settings for admin in item["admin1"]]
        admin_country = {
            admin["code"]: item["country"]["iso3"]
            for item in country_settings for admin in item["admin1"]
        }
        national_population_totals = load_national_population_totals(
            root, settings, country_iso3s
        )
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

        display_language = str(settings.get("display_language", ""))
        check(
            "Display language is configured",
            display_language in {"en", "ko"},
            f"display_language={display_language}",
        )
        naming_policy_errors = [
            item["country"]["iso3"]
            for item in country_settings
            if item.get("tile_naming", {}).get("require_same_country") is not True
        ]
        check(
            "Every country enforces same-country naming",
            not naming_policy_errors,
            f"invalid={naming_policy_errors}",
        )
        admin_naming_policy_errors = [
            item["country"]["iso3"]
            for item in country_settings
            if not isinstance(
                item.get("tile_naming", {}).get("require_same_admin1"), bool
            )
        ]
        check(
            "Every country explicitly configures naming/Admin-1 coupling",
            not admin_naming_policy_errors,
            f"invalid={admin_naming_policy_errors}",
        )
        expected_naming_policy = (
            "population_descending_unique_representatives_then_greatest_overlap_fill"
        )
        naming_allocation_policy_errors = [
            item["country"]["iso3"]
            for item in country_settings
            if item.get("tile_naming", {}).get("allocation_policy")
            != expected_naming_policy
        ]
        check(
            "Every country uses representative-priority then greatest-overlap fill",
            not naming_allocation_policy_errors,
            f"invalid={naming_allocation_policy_errors}",
        )

        check("GeoPackage layer loads", layer.isValid(), str(gpkg))
        if not layer.isValid():
            report_path.write_text("# Validation failed\n\nGeoPackage layer does not load.\n", encoding="utf-8")
            raise QgsProcessingException(f"Invalid korea_tiles layer: {gpkg}")

        check("CRS", layer.crs().authid() == settings["crs"], layer.crs().authid())
        features = list(layer.getFeatures())
        wrong_country = [
            str(feature["tile_id"]) for feature in features
            if str(feature["country_iso3"] or "") not in country_iso3s
        ]
        check("Final country codes", not wrong_country, f"wrong_country={wrong_country}")

        ids = [str(feature["tile_id"] or "") for feature in features]
        blank_ids = [i for i in ids if not i]
        duplicate_ids = sorted(tile_id for tile_id, count in Counter(ids).items() if count > 1)
        check("Tile IDs present", not blank_ids, f"blank={len(blank_ids)}")
        check("Tile IDs unique", not duplicate_ids, f"duplicates={duplicate_ids}")

        targets = {item["code"]: int(item["target_tiles"]) for item in admins}
        actual = Counter(str(feature["admin1_code"] or "") for feature in features)
        unexpected_codes = sorted(set(actual) - set(targets))
        check(
            "Only configured Admin-1 owners are used",
            not unexpected_codes,
            f"unexpected={unexpected_codes}",
        )
        actual_country_counts = Counter(
            str(feature["country_iso3"] or "") for feature in features
        )
        expected_country_counts = {
            str(code): int(count)
            for code, count in validation.get("expected_country_tile_counts", {}).items()
        }
        country_regressions = {
            code: (actual_country_counts.get(code, 0), expected)
            for code, expected in expected_country_counts.items()
            if actual_country_counts.get(code, 0) != expected
        }
        expected_admin_counts = {
            str(code): int(count)
            for code, count in validation.get("expected_admin_tile_counts", {}).items()
        }
        admin_regressions = {
            code: (actual.get(code, 0), expected)
            for code, expected in expected_admin_counts.items()
            if actual.get(code, 0) != expected
        }
        check(
            "Frozen canonical-snapshot allocation is unchanged",
            not country_regressions and not admin_regressions,
            f"country={country_regressions}, admin={admin_regressions}",
        )
        invalid_assignment = [feature["tile_id"] for feature in features if not feature["admin1_code"]]
        check("Exactly one admin assignment", not invalid_assignment, f"invalid={invalid_assignment}")
        cross_country_assignments = [
            str(feature["tile_id"]) for feature in features
            if admin_country.get(str(feature["admin1_code"] or ""))
            != str(feature["country_iso3"] or "")
        ]
        check(
            "Admin assignment never crosses a country boundary",
            not cross_country_assignments,
            f"invalid={cross_country_assignments}",
        )

        candidate_layer = QgsVectorLayer(f"{gpkg}|layername=hex_candidates", "hex_candidates", "ogr")
        candidate_features = list(candidate_layer.getFeatures()) if candidate_layer.isValid() else []
        best_admin_by_id = {
            str(feature["candidate_id"]): str(feature["best_admin"] or "")
            for feature in candidate_features
        }
        admin_scores_by_id = {}
        for feature in candidate_features:
            try:
                admin_scores_by_id[str(feature["candidate_id"])] = json.loads(
                    str(feature["scores_json"] or "{}")
                )
            except json.JSONDecodeError:
                admin_scores_by_id[str(feature["candidate_id"])] = {}
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
            if str(feature["dominant_territory"] or "") in country_iso3s
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
        final_country_by_id = {
            str(feature["tile_id"]): str(feature["country_iso3"] or "") for feature in features
        }
        candidate_country_by_id = {
            str(feature["candidate_id"]): str(feature["dominant_territory"] or "")
            for feature in candidate_features
        }
        country_owner_mismatches = sorted(
            tile_id for tile_id, country in final_country_by_id.items()
            if country != candidate_country_by_id.get(tile_id)
        )
        check(
            "Every tile retains its dominant national owner",
            not country_owner_mismatches,
            f"mismatches={country_owner_mismatches}",
        )
        non_dominant_assignments = [
            str(feature["tile_id"]) for feature in features
            if str(feature["admin1_code"] or "")
            != best_admin_by_id.get(str(feature["tile_id"]), "")
        ]
        invalid_methods = [
            (str(feature["tile_id"]), str(feature["assignment_method"] or ""))
            for feature in features
            if str(feature["assignment_method"] or "")
            not in {"dominant_overlap", "admin1_representation"}
            or bool(feature["manual_override"])
        ]
        check("Ownership overrides are absent", not invalid_methods, f"invalid={invalid_methods}")
        representation_errors = []
        for feature in features:
            tile_id = str(feature["tile_id"])
            admin_code = str(feature["admin1_code"] or "")
            method = str(feature["assignment_method"] or "")
            is_non_dominant = tile_id in non_dominant_assignments
            score = float(admin_scores_by_id.get(tile_id, {}).get(admin_code, 0.0))
            if method == "admin1_representation" and (not is_non_dominant or score <= 0.0):
                representation_errors.append(tile_id)
            if method == "dominant_overlap" and is_non_dominant:
                representation_errors.append(tile_id)
        check(
            "Admin-1 assignments use greatest overlap or a positive-overlap representative",
            not representation_errors,
            f"invalid={representation_errors}",
        )
        minimum_admin_tiles = int(settings["admin_assignment"]["minimum_tiles_per_admin"])
        underrepresented_admins = {
            code: actual.get(code, 0) for code in targets
            if actual.get(code, 0) < minimum_admin_tiles
        }
        check(
            "Every official Admin-1 has its configured minimum representation",
            not underrepresented_admins,
            f"minimum={minimum_admin_tiles}, invalid={underrepresented_admins}",
        )

        required_naming_fields = {
            "tile_name_code", "tile_name_ko", "tile_name_en", "tile_name_method",
            "tile_name_overlap_km2", "map_class",
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
            "unique_representation", "positive_overlap_representation",
            "dominant_overlap_fill", "population_redistribution_fill",
            "country_nearest_fallback",
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
        admin_layer = QgsVectorLayer(
            f"{gpkg}|layername=admin1_source", "admin1_source", "ogr"
        )
        admin_geometry_by_code = {}
        if admin_layer.isValid():
            admin_geometry_by_code = {
                str(feature["admin1_code"]): feature.geometry()
                for feature in admin_layer.getFeatures()
            }
        expected_area_ranges = validation.get("expected_admin_area_km2_ranges", {})
        area_regressions = {}
        for code, limits in expected_area_ranges.items():
            geometry = admin_geometry_by_code.get(str(code))
            area_km2 = geometry.area() / 1_000_000.0 if geometry else 0.0
            minimum, maximum = float(limits[0]), float(limits[1])
            if not minimum <= area_km2 <= maximum:
                area_regressions[str(code)] = round(area_km2, 3)
        check(
            "Frozen canonical-snapshot Admin-1 area ranges",
            admin_layer.isValid() and not area_regressions,
            f"outside_ranges={area_regressions}",
        )
        clipped_admin_codes = {
            admin["code"]
            for item in country_settings
            if item.get("tile_naming", {}).get("require_same_admin1") is True
            for admin in item["admin1"]
        }
        naming_outside_admin = [
            str(unit["unit_code"])
            for unit in naming_features
            if str(unit["admin1_code"] or "") in clipped_admin_codes
            and (
                str(unit["admin1_code"] or "") not in admin_geometry_by_code
                or unit.geometry().difference(
                    admin_geometry_by_code[str(unit["admin1_code"] or "")]
                ).area() > float(validation["overlap_area_tolerance_m2"])
            )
        ]
        check(
            "Naming geometries follow configured Admin-1 clipping policy",
            admin_layer.isValid() and not naming_outside_admin,
            f"strict_admin_codes={sorted(clipped_admin_codes)}; outside={naming_outside_admin}",
        )
        administrative_reference = settings.get("administrative_reference", {})
        dated_enforcement = str(
            administrative_reference.get("enforcement") or "release_gate"
        )
        enforce_dated_facts = dated_enforcement == "release_gate"
        required_admin1_mismatches = []
        for fact in administrative_reference.get("required_admin1_units", []):
            code = str(fact.get("admin1_code") or "")
            country_iso3 = str(fact.get("country_iso3") or "")
            configured = code in admin_country and admin_country.get(code) == country_iso3
            generated = code in admin_geometry_by_code
            if not configured or not generated:
                required_admin1_mismatches.append({
                    "country": country_iso3,
                    "code": code,
                    "name": str(fact.get("name_en") or ""),
                    "configured": configured,
                    "generated": generated,
                    "effective_from": str(fact.get("effective_from") or ""),
                })
        check(
            "Dated required Admin-1 units",
            not required_admin1_mismatches if enforce_dated_facts else True,
            f"enforcement={dated_enforcement}; mismatches={required_admin1_mismatches}",
        )
        membership_mismatches = []
        for fact in administrative_reference.get("known_memberships", []):
            country_iso3 = str(fact.get("country_iso3") or "")
            unit_name = str(fact.get("unit_name_en") or "").strip().casefold()
            expected_admin = str(fact.get("expected_admin1_code") or "")
            matches = [
                unit for unit in naming_features
                if str(unit["name_en"] or "").strip().casefold() == unit_name
                and admin_country.get(str(unit["admin1_code"] or "")) == country_iso3
            ]
            actual_admins = sorted({
                str(unit["admin1_code"] or "") for unit in matches
            })
            if actual_admins != [expected_admin]:
                membership_mismatches.append({
                    "country": country_iso3,
                    "unit": str(fact.get("unit_name_en") or ""),
                    "expected": expected_admin,
                    "actual": actual_admins,
                    "effective_from": str(fact.get("effective_from") or ""),
                })
        check(
            "Dated administrative membership facts",
            (
                bool(administrative_reference.get("scenario_reference_date"))
                and not membership_mismatches
            ) if enforce_dated_facts else True,
            f"enforcement={dated_enforcement}; "
            f"scenario_date={administrative_reference.get('scenario_reference_date')}; "
            f"mismatches={membership_mismatches}",
        )
        allowed_population_methods = {
            "geonames_adm2", "geonames_populated_place",
            "geonames_populated_place_same_admin2",
            "geonames_populated_place_same_name",
            "worldpop_un_adjusted_zonal_sum", "unknown",
        }
        invalid_populations = []
        unresolved_populations = []
        for unit in naming_features:
            known = bool(unit["population_known"])
            population = int(unit["population"] or 0)
            method = str(unit["population_method"] or "")
            source_id = str(unit["population_source_id"] or "")
            if not known:
                unresolved_populations.append(str(unit["unit_code"]))
            if (
                method not in allowed_population_methods
                or (known and (population <= 0 or method == "unknown" or not source_id))
                or (not known and population != 0)
            ):
                invalid_populations.append(
                    (str(unit["unit_code"]), population, known, method)
                )
        check(
            "Population values are positive integers with provenance",
            not invalid_populations,
            f"invalid={invalid_populations}",
        )
        check(
            "All naming-unit populations are resolved",
            not unresolved_populations,
            f"unresolved={unresolved_populations}",
        )
        allocation_population_missing = (
            "allocation_population" not in naming_layer.fields().names()
        )
        naming_overlaps_by_tile = {}
        if not allocation_population_missing:
            for tile in features:
                tile_country = str(tile["country_iso3"] or "")
                candidates_for_tile = {}
                for unit in naming_features:
                    unit_admin_code = str(unit["admin1_code"] or "")
                    if (
                        admin_country.get(unit_admin_code)
                        != tile_country
                        or (
                            unit_admin_code in clipped_admin_codes
                            and unit_admin_code != str(tile["admin1_code"] or "")
                        )
                        or not tile.geometry().boundingBox().intersects(
                            unit.geometry().boundingBox()
                        )
                    ):
                        continue
                    area = tile.geometry().intersection(unit.geometry()).area()
                    if area > 0:
                        candidates_for_tile[str(unit["unit_code"])] = area
                naming_overlaps_by_tile[str(tile["tile_id"])] = candidates_for_tile
        tile_by_id = {str(tile["tile_id"]): tile for tile in features}
        representative_mismatches = []
        fill_mismatches = []
        for iso3 in sorted(country_iso3s):
            available = {
                str(tile["tile_id"]) for tile in features
                if str(tile["country_iso3"] or "") == iso3
            }
            country_units = sorted(
                (
                    unit for unit in naming_features
                    if admin_country.get(str(unit["admin1_code"] or "")) == iso3
                ),
                key=lambda unit: (
                    -int(unit["allocation_population"] or 0),
                    str(unit["unit_code"]),
                ),
            )
            population_by_code = {
                str(unit["unit_code"]): int(unit["allocation_population"] or 0)
                for unit in country_units
            }
            for unit in country_units:
                code = str(unit["unit_code"])
                options = [
                    tile_id for tile_id in available
                    if naming_overlaps_by_tile.get(tile_id, {}).get(code, 0.0) > 0.0
                ]
                if not options:
                    continue
                expected_tile_id = sorted(
                    options,
                    key=lambda tile_id: (
                        -naming_overlaps_by_tile[tile_id][code], tile_id
                    ),
                )[0]
                actual_code = str(tile_by_id[expected_tile_id]["tile_name_code"] or "")
                if actual_code != code:
                    representative_mismatches.append(
                        (code, expected_tile_id, actual_code)
                    )
                available.remove(expected_tile_id)
            for tile_id in sorted(available):
                scores = naming_overlaps_by_tile.get(tile_id, {})
                if not scores:
                    continue
                expected_code = sorted(
                    scores,
                    key=lambda code: (
                        -scores[code], -population_by_code.get(code, 0), code
                    ),
                )[0]
                actual_code = str(tile_by_id[tile_id]["tile_name_code"] or "")
                if actual_code != expected_code:
                    fill_mismatches.append((tile_id, expected_code, actual_code))
        check(
            "Population-descending units reserve their best available representative",
            not allocation_population_missing and not representative_mismatches,
            f"missing_field={allocation_population_missing}, "
            f"mismatches={representative_mismatches}",
        )
        check(
            "Remaining naming tiles retain greatest overlap",
            not fill_mismatches,
            f"mismatches={fill_mismatches}",
        )
        admin_name_mismatches = []
        for tile in features:
            unit = naming_by_code.get(str(tile["tile_name_code"] or ""))
            unit_admin_code = str(unit["admin1_code"] or "") if unit else ""
            if (
                unit is None
                or admin_country.get(unit_admin_code)
                != str(tile["country_iso3"] or "")
                or (
                    unit_admin_code in clipped_admin_codes
                    and unit_admin_code != str(tile["admin1_code"] or "")
                )
            ):
                admin_name_mismatches.append(
                    (str(tile["tile_id"]), str(tile["admin1_code"] or ""),
                     str(tile["tile_name_code"] or ""))
                )
        check(
            "Tile name and city fill obey configured country/Admin-1 scope",
            not admin_name_mismatches,
            f"mismatches={admin_name_mismatches}",
        )
        represented_name_codes = {
            str(tile["tile_name_code"] or "") for tile in features
        }
        missing_expected_names = sorted(
            set(validation.get("expected_represented_name_codes", []))
            - represented_name_codes
        )
        check(
            "Configured metropolitan names are represented",
            not missing_expected_names,
            f"missing={missing_expected_names}",
        )
        dominant_name_mismatches = []
        for tile in features:
            if str(tile["tile_name_method"] or "") != "dominant_overlap_fill":
                continue
            scores = {}
            for unit in naming_features:
                unit_admin_code = str(unit["admin1_code"] or "")
                if (
                    admin_country.get(unit_admin_code)
                    != str(tile["country_iso3"] or "")
                    or (
                        unit_admin_code in clipped_admin_codes
                        and unit_admin_code != str(tile["admin1_code"] or "")
                    )
                ):
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
        minimum_share_by_admin = {
            admin["code"]: float(item["tile_naming"]["minimum_tile_share"])
            for item in country_settings for admin in item["admin1"]
        }
        for tile in features:
            method = str(tile["tile_name_method"] or "")
            if method not in {"unique_representation", "positive_overlap_representation"}:
                continue
            code = str(tile["tile_name_code"] or "")
            representation_codes.append(code)
            overlap_share = (
                float(tile["tile_name_overlap_km2"] or 0.0)
                / float(tile["area_km2"] or 1.0)
            )
            unit = naming_by_code.get(code)
            minimum_share = minimum_share_by_admin[str(unit["admin1_code"])] if unit else 0.0
            normal_valid = method == "unique_representation" and overlap_share + 1e-9 >= minimum_share
            rescue_valid = (
                method == "positive_overlap_representation" and overlap_share > 0
            )
            if code not in naming_by_code or not (normal_valid or rescue_valid):
                representation_errors.append(
                    (str(tile["tile_id"]), code, round(overlap_share, 4))
                )
        duplicate_representations = sorted(
            code for code, count in Counter(representation_codes).items() if count > 1
        )
        check("Unique representatives after redistribution",
              not representation_errors and not duplicate_representations,
              f"invalid={representation_errors}, duplicates={duplicate_representations}")

        city_layer = QgsVectorLayer(f"{gpkg}|layername=city_markers", "city_markers", "ogr")
        check("City marker layer removed", not city_layer.isValid(),
              f"layer_valid={city_layer.isValid()}")
        city_min = int(settings["city_classification"]["city_population_min"])
        metropolis_min = int(settings["city_classification"]["metropolis_population_min"])
        check(
            "Global tile-population classification thresholds",
            city_min == 100000 and metropolis_min == 1000000,
            f"city={city_min}, metropolis={metropolis_min}",
        )
        required_population_fields = {
            "population", "population_year", "population_method", "population_source_id",
            "is_initial_city", "city_upgrade_eligible",
        }
        missing_population_fields = sorted(
            required_population_fields - set(layer.fields().names())
        )
        check(
            "Single game-tile population model fields",
            not missing_population_fields,
            f"missing={missing_population_fields}",
        )
        legacy_population_fields = sorted(
            {"tile_name_population", "tile_name_population_method"}
            & set(layer.fields().names())
        )
        check(
            "No second naming-unit population on game tiles",
            not legacy_population_fields,
            f"legacy={legacy_population_fields}",
        )
        population_year = int(settings["population_model"]["national_totals_year"])
        residual_method = str(settings["population_model"]["allocation_method"])
        anchor_method = str(settings["population_model"]["initial_city_method"])
        invalid_tile_populations = [
            str(tile["tile_id"]) for tile in features
            if int(tile["population"] or 0) < 0
            or int(tile["population_year"] or 0) != population_year
            or str(tile["population_method"] or "") not in {residual_method, anchor_method}
            or not str(tile["population_source_id"] or "")
            or (
                str(tile["population_method"] or "") == residual_method
                and str(tile["population_source_id"] or "")
                != str(settings["population_model"]["source_id"])
            )
            or (
                str(tile["population_method"] or "") == anchor_method
                and not str(tile["population_source_id"] or "").isdigit()
            )
        ]
        check(
            "Tile populations are non-negative integers with provenance",
            not invalid_tile_populations,
            f"invalid={invalid_tile_populations}",
        )
        actual_population_totals = Counter()
        for tile in features:
            actual_population_totals[str(tile["country_iso3"])] += int(tile["population"] or 0)
        population_total_mismatches = {
            iso3: (actual_population_totals.get(iso3, 0), expected)
            for iso3, expected in national_population_totals.items()
            if actual_population_totals.get(iso3, 0) != expected
        }
        check(
            "Tile populations exactly reconcile to UN WPP national totals",
            not population_total_mismatches,
            f"mismatches={population_total_mismatches}",
        )
        capital_tiles = [tile for tile in features if bool(tile["is_capital"])]
        capital_countries = Counter(str(tile["country_iso3"] or "") for tile in capital_tiles)
        capital_codes = {str(tile["tile_name_code"] or "") for tile in capital_tiles}
        capital_admin1_codes = {str(tile["admin1_code"] or "") for tile in capital_tiles}
        noncapital_capital_duplicates = [
            str(tile["tile_id"]) for tile in features
            if str(tile["tile_name_code"] or "") in capital_codes
            and not bool(tile["is_capital"])
        ]
        invalid_capital_countries = sorted(set(capital_countries) - country_iso3s)
        check(
            "Represented capital tiles belong to configured countries",
            not invalid_capital_countries,
            f"countries={dict(capital_countries)}, invalid={invalid_capital_countries}",
        )
        check(
            "Every tile named for a capital is marked as capital",
            not noncapital_capital_duplicates,
            f"invalid={noncapital_capital_duplicates}",
        )
        city_display_classes = {}
        invalid_city_anchors = []
        anchored_name_codes = {
            str(tile["tile_name_code"] or "")
            for tile in features if bool(tile["is_initial_city"])
        }
        for code in sorted(anchored_name_codes):
            anchor_classes = {
                str(tile["city_class"] or "") for tile in features
                if str(tile["tile_name_code"] or "") == code
                and bool(tile["is_initial_city"])
            }
            anchor_count = sum(
                1 for tile in features
                if str(tile["tile_name_code"] or "") == code
                and bool(tile["is_initial_city"])
            )
            if anchor_count != 1 or len(anchor_classes) != 1 or "" in anchor_classes:
                invalid_city_anchors.append((code, anchor_count, sorted(anchor_classes)))
            else:
                city_display_classes[code] = next(iter(anchor_classes))
        inconsistent_city_groups = [
            str(tile["tile_id"])
            for tile in features
            if str(tile["tile_name_code"] or "") in city_display_classes
            and str(tile["map_class"] or "")
            != city_display_classes[str(tile["tile_name_code"])]
        ]
        check(
            "Every represented city-name group inherits one display class",
            not invalid_city_anchors and not inconsistent_city_groups,
            f"invalid_anchors={invalid_city_anchors}, inconsistent={inconsistent_city_groups}",
        )

        invalid_capital_anchors = []
        for code in sorted(capital_codes):
            if code not in city_display_classes:
                invalid_capital_anchors.append(code)
        check(
            "Every capital group has one inherited anchor display class",
            not invalid_capital_anchors,
            f"invalid={invalid_capital_anchors}",
        )
        tile_city_mismatches = []
        for tile in features:
            tile_id = str(tile["tile_id"])
            map_class = str(tile["map_class"] or "")
            population = int(tile["population"] or 0)
            is_initial_city = bool(tile["is_initial_city"])
            expected_city_class = (
                "metropolis" if population >= metropolis_min
                else "city"
            ) if is_initial_city else ""
            name_code = str(tile["tile_name_code"] or "")
            expected_upgrade_eligible = (
                not is_initial_city and not bool(tile["is_capital"])
                and name_code not in city_display_classes
                and population >= city_min
            )
            expected_map_class = city_display_classes.get(name_code, "admin")
            expected_named = bool(expected_map_class != "admin" or bool(tile["is_capital"]))
            if (
                str(tile["city_class"] or "") != expected_city_class
                or map_class != expected_map_class
                or bool(tile["city_upgrade_eligible"]) != expected_upgrade_eligible
                or (
                    is_initial_city
                    != (str(tile["population_method"] or "") == anchor_method)
                )
                or (
                    expected_named
                    and str(tile["tile_name_ko"] or "") != str(tile["city_name_ko"] or "")
                )
                or (not expected_named and str(tile["city_name_ko"] or ""))
            ):
                tile_city_mismatches.append(tile_id)
        check("Initial city anchors and player upgrade eligibility are consistent", not tile_city_mismatches,
              f"mismatches={tile_city_mismatches}")
        actual_map_classes = {str(tile["map_class"] or "") for tile in features}
        expected_map_classes = {"admin", "city", "metropolis"}
        check(
            "Exactly three tile fill classes; capital is an outline",
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
        check(
            "Capital outline color is configured",
            bool(str(colors.get("capital_outline") or "").strip()),
            f"capital_outline={colors.get('capital_outline')}",
        )

        border_layer = QgsVectorLayer(
            f"{gpkg}|layername=admin1_tile_borders", "admin1_tile_borders", "ogr"
        )
        border_features = list(border_layer.getFeatures()) if border_layer.isValid() else []
        tile_by_id = {str(tile["tile_id"]): tile for tile in features}
        edge_members = {}
        for tile in features:
            for edge_key in hex_edge_keys(tile.geometry()):
                edge_members.setdefault(edge_key, []).append(tile)
        expected_border_types = {}
        invalid_topology = []
        for edge_key, members in edge_members.items():
            if len(members) == 1:
                expected_border_types[edge_key] = "exterior"
            elif len(members) == 2:
                if str(members[0]["admin1_code"]) != str(members[1]["admin1_code"]):
                    expected_border_types[edge_key] = (
                        "country"
                        if str(members[0]["country_iso3"]) != str(members[1]["country_iso3"])
                        else "admin"
                    )
            else:
                invalid_topology.append((edge_key, len(members)))
        actual_border_keys = set()
        invalid_borders = []
        for border in border_features:
            edge_key = str(border["edge_key"] or "")
            edge_type = str(border["edge_type"] or "")
            tile_a = str(border["tile_id_a"] or "")
            tile_b = str(border["tile_id_b"] or "")
            admin_a = str(border["admin_a"] or "")
            admin_b = str(border["admin_b"] or "")
            country_a = str(border["country_a"] or "")
            country_b = str(border["country_b"] or "")
            actual_border_keys.add(edge_key)
            valid = (
                edge_key in expected_border_types
                and edge_type == expected_border_types.get(edge_key)
                and tile_a in tile_by_id and admin_a == str(tile_by_id[tile_a]["admin1_code"])
                and country_a == str(tile_by_id[tile_a]["country_iso3"])
                and not border.geometry().isEmpty()
            )
            if edge_type in {"admin", "country"}:
                valid = valid and (
                    tile_b in tile_by_id and admin_b == str(tile_by_id[tile_b]["admin1_code"])
                    and country_b == str(tile_by_id[tile_b]["country_iso3"])
                    and admin_a != admin_b
                )
                if edge_type == "country":
                    valid = valid and country_a != country_b
                else:
                    valid = valid and country_a == country_b
            elif edge_type == "exterior":
                valid = valid and not tile_b and not admin_b and not country_b
            if not valid:
                invalid_borders.append(edge_key)
        check(
            "Same-owner groups have complete topology-derived outlines",
            border_layer.isValid() and actual_border_keys == set(expected_border_types)
            and len(border_features) == len(actual_border_keys)
            and not invalid_borders and not invalid_topology,
            f"edges={len(border_features)}, invalid={invalid_borders}, "
            f"topology={invalid_topology}, "
            f"missing={sorted(set(expected_border_types) - actual_border_keys)}",
        )
        capital_outline_layer = QgsVectorLayer(
            f"{gpkg}|layername=capital_tile_outlines", "capital_tile_outlines", "ogr"
        )
        capital_outline_features = (
            list(capital_outline_layer.getFeatures())
            if capital_outline_layer.isValid() else []
        )
        expected_capital_edges = set()
        for edge_key, members in edge_members.items():
            capital_members = [
                tile for tile in members
                if str(tile["admin1_code"] or "") in capital_admin1_codes
            ]
            if len(capital_members) != 1:
                continue
            capital = capital_members[0]
            if len(members) == 2:
                other = next(tile for tile in members if tile.id() != capital.id())
                if str(other["admin1_code"] or "") == str(capital["admin1_code"] or ""):
                    continue
            expected_capital_edges.add(edge_key)
        actual_capital_edges = {
            str(feature["edge_key"] or "") for feature in capital_outline_features
        }
        invalid_capital_edges = [
            str(feature["edge_key"] or "") for feature in capital_outline_features
            if str(feature["edge_key"] or "") not in expected_capital_edges
            or str(feature["tile_id"] or "") not in tile_by_id
            or str(tile_by_id[str(feature["tile_id"])]["admin1_code"] or "")
            not in capital_admin1_codes
            or str(feature["capital_code"] or "")
            != str(tile_by_id[str(feature["tile_id"])]["admin1_code"])
        ]
        check(
            "Capital outlines follow the exterior of each complete capital Admin-1 group",
            capital_outline_layer.isValid()
            and actual_capital_edges == expected_capital_edges
            and len(capital_outline_features) == len(actual_capital_edges)
            and not invalid_capital_edges,
            f"edges={len(capital_outline_features)}, invalid={invalid_capital_edges}, "
            f"missing={sorted(expected_capital_edges - actual_capital_edges)}",
        )
        coast_layer = QgsVectorLayer(
            f"{gpkg}|layername=coastal_tile_outlines", "coastal_tile_outlines", "ogr"
        )
        check(
            "Coastal line layer is intentionally absent",
            not coast_layer.isValid(),
            "coastal_tile_outlines is not published during border development",
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
        edge_tiles = {}
        for feature in features:
            tile_id = str(feature["tile_id"])
            for edge_key in hex_edge_keys(feature.geometry()):
                edge_tiles.setdefault(edge_key, []).append(tile_id)
        nonmanifold_edges = sorted(
            (edge_key, sorted(members))
            for edge_key, members in edge_tiles.items() if len(members) > 2
        )
        expected_neighbors = {tile_id: set() for tile_id in ids}
        for members in edge_tiles.values():
            if len(members) != 2:
                continue
            first, second = members
            expected_neighbors[first].add(second)
            expected_neighbors[second].add(first)
        neighbor_completeness_errors = sorted(
            (
                tile_id,
                sorted(expected_neighbors[tile_id]),
                sorted(set(neighbor_map.get(tile_id, []))),
            )
            for tile_id in ids
            if expected_neighbors[tile_id] != set(neighbor_map.get(tile_id, []))
        )
        check(
            "Neighbor lists exactly match all shared hex edges",
            not nonmanifold_edges and not neighbor_completeness_errors,
            f"nonmanifold_count={len(nonmanifold_edges)}; "
            f"nonmanifold_examples={nonmanifold_edges[:20]}; "
            f"mismatch_count={len(neighbor_completeness_errors)}; "
            f"mismatch_examples={neighbor_completeness_errors[:20]}",
        )

        # Inspect scripts and the embedded .qgs XML for machine-specific data paths.
        # Build the Unix pattern in parts so this validator does not flag its
        # own source. The Windows pattern excludes URL schemes such as https:/. 
        absolute_patterns = [
            re.compile("/" + r"Users/[^/\s<]+/"),
            re.compile(r"(?<![A-Za-z])[A-Za-z]:[\\/](?![\\/])[^\s<]+"),
        ]
        path_hits = []
        border_above_tiles = False
        capital_outline_above_tiles = False
        display_labels_match = False
        tile_labels_confined = False
        admin_labels_overview_only = False
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
                    capital_position = text.find('name="Capital outlines"')
                    tile_position = text.find('name="Korean Peninsula game tiles"')
                    border_above_tiles = (
                        border_position >= 0 and tile_position >= 0
                        and border_position < tile_position
                    )
                    capital_outline_above_tiles = (
                        capital_position >= 0 and tile_position >= 0
                        and capital_position < tile_position
                    )
                    display_labels_match = (
                        f"tile_name_{display_language}" in text
                        and f"admin1_name_{display_language}" in text
                    )
                    tile_label_start = text.find(
                        f'fieldName="tile_name_{display_language}'
                    )
                    tile_label_end = text.find("</settings>", tile_label_start)
                    tile_label_block = text[tile_label_start:tile_label_end]
                    tile_name_min_scale = int(
                        settings["labeling"]["tile_name_min_scale"]
                    )
                    tile_labels_confined = (
                        tile_label_start >= 0
                        and 'fitInPolygonOnly="1"' in tile_label_block
                        and 'centroidInside="1"' in tile_label_block
                        and 'scaleVisibility="1"' in tile_label_block
                        and f'scaleMax="{tile_name_min_scale}"' in tile_label_block
                        and 'scaleMin="0"' in tile_label_block
                    )
                    admin_label_start = text.find(
                        f'fieldName="admin1_name_{display_language}'
                    )
                    admin_label_end = text.find("</settings>", admin_label_start)
                    admin_label_block = text[admin_label_start:admin_label_end]
                    admin_name_min_scale = int(
                        settings["labeling"]["admin_name_min_scale"]
                    )
                    admin_name_max_scale = int(
                        settings["labeling"]["admin_name_max_scale"]
                    )
                    admin_labels_overview_only = (
                        admin_label_start >= 0
                        and 'scaleVisibility="1"' in admin_label_block
                        and f'scaleMax="{admin_name_min_scale}"' in admin_label_block
                        and f'scaleMin="{admin_name_max_scale}"' in admin_label_block
                    )
                    for line_number, line in enumerate(text.splitlines(), 1):
                        if any(pattern.search(line) for pattern in absolute_patterns):
                            path_hits.append(f"{project_path.name}:{line_number}")
        check("Relative shared paths", not path_hits, f"absolute_path_hits={path_hits}")
        check(
            "QGIS labels use the configured language",
            display_labels_match,
            f"display_language={display_language}",
        )
        check(
            "Tile labels stay inside hexes with no close-zoom cutoff",
            tile_labels_confined,
            f"tile_labels_confined={tile_labels_confined}",
        )
        check(
            "Admin summary labels are overview-only",
            admin_labels_overview_only,
            f"admin_labels_overview_only={admin_labels_overview_only}",
        )
        check(
            "Admin border layer renders above tile fills",
            border_above_tiles,
            f"border_above_tiles={border_above_tiles}",
        )
        check(
            "Capital outline layer renders above tile fills",
            capital_outline_above_tiles,
            f"capital_outline_above_tiles={capital_outline_above_tiles}",
        )

        lines = [
            "# Atlas Korean Peninsula validation report", "",
            f"Generated: {datetime.now(timezone.utc).isoformat()}", "",
            f"Overall result: **{'PASS' if not failures else 'FAIL'}**", "",
            "| Check | Result | Detail |", "| --- | --- | --- |",
        ]
        for name, passed, detail in checks:
            safe_detail = str(detail).replace("|", "\\|").replace("\n", " ")
            lines.append(f"| {name} | {'PASS' if passed else 'FAIL'} | {safe_detail} |")
        lines.extend([
            "", "## Allocation", "",
            "Targets are advisory; every feasible official Admin-1 receives its "
            "same-country representation floor, then remaining ownership follows "
            "greatest overlap.", "",
            "| Code | Target | Actual | Difference |",
            "| --- | ---: | ---: | ---: |",
        ])
        for item in admins:
            code = item["code"]
            target = int(item["target_tiles"])
            value = actual.get(code, 0)
            lines.append(
                f"| {code} | {target} | {value} | {value - target} |"
            )
        report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        feedback.pushInfo(f"Validation report: {report_path}")
        feedback.setProgress(100)
        if failures:
            raise QgsProcessingException("Validation failed:\n- " + "\n- ".join(failures))
        return {OUTPUT_REPORT: str(report_path)}
