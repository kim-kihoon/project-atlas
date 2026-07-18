"""Export Atlas East Asia tiles to GeoJSON and CSV."""

import csv
import json
from pathlib import Path

from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (
    QgsCoordinateReferenceSystem,
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


def tr(text):
    return QCoreApplication.translate("AtlasKoreaExport", text)


def resolve(root, relative_path):
    path = (root / relative_path).resolve()
    if root != path and root not in path.parents:
        raise QgsProcessingException(f"Path escapes project root: {relative_path}")
    return path


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

    def processAlgorithm(self, parameters, context, feedback):
        config_path = Path(self.parameterAsFile(parameters, CONFIG, context)).resolve()
        root = config_path.parent.parent.resolve()
        settings = json.loads(config_path.read_text(encoding="utf-8"))
        gpkg = resolve(root, settings["outputs"]["geopackage"])
        geojson = resolve(root, settings["outputs"]["geojson"])
        csv_path = resolve(root, settings["outputs"]["csv"])
        geojson.parent.mkdir(parents=True, exist_ok=True)
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        layer = QgsVectorLayer(f"{gpkg}|layername=east_asia_tiles", "east_asia_tiles", "ogr")
        if not layer.isValid():
            raise QgsProcessingException(f"Invalid east_asia_tiles layer: {gpkg}")

        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "GeoJSON"
        options.fileEncoding = "UTF-8"
        options.destCRS = QgsCoordinateReferenceSystem("EPSG:4326")
        options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile
        result = QgsVectorFileWriter.writeAsVectorFormatV3(
            layer, str(geojson), QgsProject.instance().transformContext(), options
        )
        if result[0] != QgsVectorFileWriter.NoError:
            raise QgsProcessingException(f"GeoJSON export failed: {result}")

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
        feedback.setProgress(100)
        return {OUTPUT_GEOJSON: str(geojson), OUTPUT_CSV: str(csv_path)}
