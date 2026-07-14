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
        return tr("Validates all fixed Atlas Korea tile, geometry, adjacency, CRS and path rules.")

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
        expected_count = int(settings["grid"]["target_tile_count"])
        check("Final tile count", len(features) == expected_count, f"{len(features)} / {expected_count}")

        ids = [str(feature["tile_id"] or "") for feature in features]
        blank_ids = [i for i in ids if not i]
        duplicate_ids = sorted(tile_id for tile_id, count in Counter(ids).items() if count > 1)
        check("Tile IDs present", not blank_ids, f"blank={len(blank_ids)}")
        check("Tile IDs unique", not duplicate_ids, f"duplicates={duplicate_ids}")

        configured = {item["code"]: int(item["tiles"]) for item in settings["admin1"]}
        actual = Counter(str(feature["admin1_code"] or "") for feature in features)
        quota_differences = {
            code: actual.get(code, 0) - target for code, target in configured.items()
            if actual.get(code, 0) != target
        }
        unexpected_codes = sorted(set(actual) - set(configured))
        check(
            "Admin quotas",
            not quota_differences and not unexpected_codes,
            f"differences={quota_differences}, unexpected={unexpected_codes}",
        )
        invalid_assignment = [feature["tile_id"] for feature in features if not feature["admin1_code"]]
        check("Exactly one admin assignment", not invalid_assignment, f"invalid={invalid_assignment}")

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
                    for line_number, line in enumerate(text.splitlines(), 1):
                        if any(pattern.search(line) for pattern in absolute_patterns):
                            path_hits.append(f"{project_path.name}:{line_number}")
        check("Relative shared paths", not path_hits, f"absolute_path_hits={path_hits}")

        lines = [
            "# Atlas Korea validation report", "",
            f"Generated: {datetime.now(timezone.utc).isoformat()}", "",
            f"Overall result: **{'PASS' if not failures else 'FAIL'}**", "",
            "| Check | Result | Detail |", "| --- | --- | --- |",
        ]
        for name, passed, detail in checks:
            safe_detail = str(detail).replace("|", "\\|").replace("\n", " ")
            lines.append(f"| {name} | {'PASS' if passed else 'FAIL'} | {safe_detail} |")
        lines.extend(["", "## Allocation", "", "| Code | Target | Actual |", "| --- | ---: | ---: |"])
        for item in settings["admin1"]:
            lines.append(f"| {item['code']} | {item['tiles']} | {actual.get(item['code'], 0)} |")
        report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        feedback.pushInfo(f"Validation report: {report_path}")
        feedback.setProgress(100)
        if failures:
            raise QgsProcessingException("Validation failed:\n- " + "\n- ".join(failures))
        return {OUTPUT_REPORT: str(report_path)}
