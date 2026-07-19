"""Export Atlas East Asia tiles and a versioned Unreal runtime fixture."""

import csv
import json
import math
from pathlib import Path

from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingOutputFile,
    QgsProcessingParameterFile,
    QgsProject,
    QgsVectorFileWriter,
    QgsVectorLayer,
)


CONFIG = "CONFIG"
OUTPUT_GEOJSON = "OUTPUT_GEOJSON"
OUTPUT_CSV = "OUTPUT_CSV"
OUTPUT_RUNTIME_FIXTURE = "OUTPUT_RUNTIME_FIXTURE"


def tr(text):
    return QCoreApplication.translate("AtlasKoreaExport", text)


def resolve(root, relative_path):
    path = (root / relative_path).resolve()
    if root != path and root not in path.parents:
        raise QgsProcessingException(f"Path escapes project root: {relative_path}")
    return path


def unit_vector(longitude, latitude):
    longitude_radians = math.radians(float(longitude))
    latitude_radians = math.radians(float(latitude))
    cos_latitude = math.cos(latitude_radians)
    return [
        cos_latitude * math.cos(longitude_radians),
        cos_latitude * math.sin(longitude_radians),
        math.sin(latitude_radians),
    ]


def parse_id_array(feature, field_name):
    try:
        value = json.loads(str(feature[field_name]))
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise QgsProcessingException(
            f"Invalid {field_name} JSON for {feature['tile_id']}"
        ) from exc
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise QgsProcessingException(
            f"{field_name} must be a JSON string array for {feature['tile_id']}"
        )
    return value


def exterior_unit_vectors(feature, transform):
    geometry = feature.geometry()
    geometry.transform(transform)
    polygons = geometry.asMultiPolygon() if geometry.isMultipart() else [geometry.asPolygon()]
    polygon = max(polygons, key=lambda value: len(value[0]) if value else 0)
    if not polygon or len(polygon[0]) < 4:
        raise QgsProcessingException(f"Missing exterior ring for {feature['tile_id']}")
    ring = list(polygon[0])
    if ring[0] == ring[-1]:
        ring.pop()
    return [unit_vector(point.x(), point.y()) for point in ring]


def validate_geojson_wgs84(path):
    document = json.loads(path.read_text(encoding="utf-8"))
    for feature in document.get("features", []):
        coordinates = feature.get("geometry", {}).get("coordinates", [])
        stack = [coordinates]
        while stack:
            value = stack.pop()
            if isinstance(value, list) and len(value) >= 2 and all(
                isinstance(component, (int, float)) for component in value[:2]
            ):
                if not (-180.0 <= value[0] <= 180.0 and -90.0 <= value[1] <= 90.0):
                    raise QgsProcessingException(
                        f"GeoJSON coordinate is not WGS84 longitude/latitude: {value[:2]}"
                    )
            elif isinstance(value, list):
                stack.extend(value)


class AtlasKoreaExport(QgsProcessingAlgorithm):
    def name(self):
        return "atlas_east_asia_export"

    def displayName(self):
        return tr("Export Atlas East Asia tiles for Unreal")

    def group(self):
        return tr("Atlas")

    def groupId(self):
        return "atlas"

    def shortHelpString(self):
        return tr("Exports final tile polygons to WGS84 GeoJSON and attributes to UTF-8 CSV.")

    def createInstance(self):
        return AtlasKoreaExport()

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFile(CONFIG, tr("atlas_east_asia.json"), extension="json"))
        self.addOutput(QgsProcessingOutputFile(OUTPUT_GEOJSON, tr("GeoJSON")))
        self.addOutput(QgsProcessingOutputFile(OUTPUT_CSV, tr("CSV")))
        self.addOutput(QgsProcessingOutputFile(OUTPUT_RUNTIME_FIXTURE, tr("Runtime fixture")))

    def processAlgorithm(self, parameters, context, feedback):
        config_path = Path(self.parameterAsFile(parameters, CONFIG, context)).resolve()
        root = config_path.parent.parent.resolve()
        settings = json.loads(config_path.read_text(encoding="utf-8"))
        gpkg = resolve(root, settings["outputs"]["geopackage"])
        geojson = resolve(root, settings["outputs"]["geojson"])
        csv_path = resolve(root, settings["outputs"]["csv"])
        fixture_path = resolve(root, settings["outputs"]["runtime_fixture"])
        geojson.parent.mkdir(parents=True, exist_ok=True)
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        layer = QgsVectorLayer(f"{gpkg}|layername=east_asia_tiles", "east_asia_tiles", "ogr")
        if not layer.isValid():
            raise QgsProcessingException(f"Invalid east_asia_tiles layer: {gpkg}")

        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "GeoJSON"
        options.fileEncoding = "UTF-8"
        wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")
        transform = QgsCoordinateTransform(layer.crs(), wgs84, context.transformContext())
        options.ct = transform
        options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile
        result = QgsVectorFileWriter.writeAsVectorFormatV3(
            layer, str(geojson), QgsProject.instance().transformContext(), options
        )
        if result[0] != QgsVectorFileWriter.NoError:
            raise QgsProcessingException(f"GeoJSON export failed: {result}")
        validate_geojson_wgs84(geojson)

        field_names = [field.name() for field in layer.fields()]
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(field_names)
            for feature in layer.getFeatures():
                row = []
                for field_name in field_names:
                    value = feature[field_name]
                    row.append("" if value is None else value)
                writer.writerow(row)

        features = sorted(layer.getFeatures(), key=lambda feature: str(feature["tile_id"]))
        required_fields = {
            "tile_id", "dggs_zone_id", "dggs_level", "cell_type", "country_iso3",
            "center_lon", "center_lat", "center_ux", "center_uy", "center_uz",
            "chunk_id", "canonical_neighbor_ids", "side_neighbor_ids", "neighbor_ids",
        }
        missing_fields = sorted(required_fields - set(field_names))
        if missing_fields:
            raise QgsProcessingException(
                f"Rebuild the GeoPackage before export; missing runtime fields: {missing_fields}"
            )

        selected = []
        korean_hexes = [
            feature for feature in features
            if feature["country_iso3"] == "KOR" and feature["cell_type"] == "hexagon"
        ]
        feature_by_tile_id = {
            str(feature["tile_id"]): feature for feature in features
        }
        boundary_hex = next((
            feature for feature in korean_hexes
            if any(
                neighbor_id in feature_by_tile_id
                and str(feature_by_tile_id[neighbor_id]["chunk_id"])
                != str(feature["chunk_id"])
                for neighbor_id in parse_id_array(feature, "neighbor_ids")
            )
        ), None)
        if boundary_hex is not None:
            selected.append(boundary_hex)
        second_hex = next(
            (feature for feature in korean_hexes if feature not in selected), None
        )
        if second_hex is not None:
            selected.append(second_hex)
        pentagon = next(
            (feature for feature in features if feature["cell_type"] == "pentagon"), None
        )
        if pentagon is not None:
            selected.append(pentagon)
        if len(selected) != 3:
            raise QgsProcessingException(
                "Runtime fixture requires a Korean chunk-boundary hexagon, "
                "a second Korean hexagon and one pentagon"
            )

        tiles = []
        for feature in selected:
            tiles.append({
                "tile_id": str(feature["tile_id"]),
                "dggs_zone_id": str(feature["dggs_zone_id"]),
                "dggs_level": int(feature["dggs_level"]),
                "cell_type": str(feature["cell_type"]),
                "chunk_id": str(feature["chunk_id"]),
                "center_lon_deg": float(feature["center_lon"]),
                "center_lat_deg": float(feature["center_lat"]),
                "center_unit": [
                    float(feature["center_ux"]),
                    float(feature["center_uy"]),
                    float(feature["center_uz"]),
                ],
                "canonical_neighbor_ids": parse_id_array(feature, "canonical_neighbor_ids"),
                "side_neighbor_ids": parse_id_array(feature, "side_neighbor_ids"),
                "regional_neighbor_ids": parse_id_array(feature, "neighbor_ids"),
                "boundary_unit_vectors": exterior_unit_vectors(feature, transform),
            })
        fixture = {
            "format_version": 1,
            "grid_id": "OGC_ISEA3H_L11",
            "is_partial_fixture": True,
            "tiles": tiles,
        }
        fixture_path.write_text(
            json.dumps(fixture, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        feedback.setProgress(100)
        return {
            OUTPUT_GEOJSON: str(geojson),
            OUTPUT_CSV: str(csv_path),
            OUTPUT_RUNTIME_FIXTURE: str(fixture_path),
        }
