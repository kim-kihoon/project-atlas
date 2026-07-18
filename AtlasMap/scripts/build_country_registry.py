"""Build the data-driven Atlas country/Admin-1 registry from frozen sources."""

import csv
import io
import json
from pathlib import Path
import re
import zipfile

from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingOutputFile,
    QgsProcessingParameterFile,
    QgsSpatialIndex,
    QgsVectorLayer,
)


CONFIG = "CONFIG"
OUTPUT_REGISTRY = "OUTPUT_REGISTRY"


def resolve(root, relative_path):
    path = (root / relative_path).resolve()
    if root != path and root not in path.parents:
        raise QgsProcessingException(f"Path escapes project root: {relative_path}")
    return path


def vector_source_uri(root, relative_path, archive_member=None):
    path = resolve(root, relative_path)
    if archive_member:
        member = str(archive_member).replace("\\", "/").lstrip("/")
        return f"/vsizip/{path.as_posix()}/{member}"
    return str(path)


def normalized_name(value):
    value = re.sub(r"\s*\[[^]]*\]\s*", "", str(value).strip().lower())
    value = re.sub(
        r"\b(province|prefecture|municipality|autonomous region|special administrative region|county|city)\b",
        "",
        value,
    )
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-")


class AtlasCountryRegistryBuild(QgsProcessingAlgorithm):
    def tr(self, text):
        return QCoreApplication.translate("AtlasCountryRegistryBuild", text)

    def name(self):
        return "build_country_registry"

    def displayName(self):
        return self.tr("Build Atlas country registry")

    def group(self):
        return self.tr("Atlas")

    def groupId(self):
        return "atlas"

    def createInstance(self):
        return AtlasCountryRegistryBuild()

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFile(CONFIG, self.tr("Atlas JSON config")))
        self.addOutput(QgsProcessingOutputFile(OUTPUT_REGISTRY, self.tr("Country registry JSON")))

    def processAlgorithm(self, parameters, context, feedback):
        config_path = Path(self.parameterAsFile(parameters, CONFIG, context)).resolve()
        root = config_path.parent.parent
        settings = json.loads(config_path.read_text(encoding="utf-8"))
        globalization = settings["globalization"]
        registry_rel = globalization["country_registry_path"]
        registry_path = resolve(root, registry_rel)
        requested = globalization["country_registry_countries"]
        snapshot = globalization["canonical_boundary_snapshot"]
        layer = QgsVectorLayer(
            vector_source_uri(root, snapshot["adm1_path"], snapshot.get("adm1_member")),
            "cgaz_adm1",
            "ogr",
        )
        if not layer.isValid() or layer.crs() != QgsCoordinateReferenceSystem("EPSG:4326"):
            raise QgsProcessingException("Frozen CGAZ ADM1 source is invalid or not EPSG:4326")

        country_metadata = {item["iso3"]: item for item in requested}
        parts = {iso3: [] for iso3 in country_metadata}
        for feature in layer.getFeatures():
            iso3 = str(feature["shapeGroup"])
            if iso3 not in parts:
                continue
            geometry = QgsGeometry(feature.geometry())
            if not geometry.isGeosValid():
                geometry = geometry.makeValid()
            if geometry.isEmpty():
                raise QgsProcessingException(f"Empty ADM1 geometry: {feature['shapeID']}")
            parts[iso3].append(
                {
                    "source_code": str(feature["shapeID"]),
                    "name_en": str(feature["shapeName"]),
                    "geometry": geometry,
                }
            )

        countries = []
        for iso3 in sorted(parts):
            metadata = country_metadata[iso3]
            iso2 = metadata["iso2"]
            if not parts[iso3]:
                raise QgsProcessingException(f"No CGAZ ADM1 records for {iso3}")
            source_to_code = {
                item["source_code"]: f"{iso3}-{item['source_code']}" for item in parts[iso3]
            }
            index = QgsSpatialIndex()
            by_fid = {}
            for fid, item in enumerate(parts[iso3]):
                feature = QgsFeature(fid)
                feature.setGeometry(item["geometry"])
                index.addFeature(feature)
                by_fid[fid] = item

            geonames_path = resolve(root, f"data/source/{iso2}.zip")
            if not geonames_path.exists():
                raise QgsProcessingException(f"Missing GeoNames source: {geonames_path}")
            geonames_admin1 = {}
            admin1_place_candidates = {}
            capital = None
            with zipfile.ZipFile(geonames_path) as archive:
                with archive.open(f"{iso2}.txt") as raw:
                    reader = csv.reader(io.TextIOWrapper(raw, encoding="utf-8"), delimiter="\t")
                    for row in reader:
                        if len(row) < 19 or row[8] != iso2:
                            continue
                        try:
                            point = QgsPointXY(float(row[5]), float(row[4]))
                            population = int(row[14] or 0)
                        except ValueError:
                            continue
                        if row[7] == "ADM1" and row[10]:
                            geonames_admin1[row[10]] = point
                        if row[10] and row[6] == "P" and population > 0:
                            previous = admin1_place_candidates.get(row[10])
                            if previous is None or (population, row[0]) > previous[:2]:
                                admin1_place_candidates[row[10]] = (population, row[0], point)
                        if row[7] == "PPLC" and (capital is None or (population, row[0]) > capital[:2]):
                            capital = (population, row[0], row[2], point)
            if capital is None:
                raise QgsProcessingException(f"No GeoNames capital (PPLC) for {iso3}")

            capital_names = {normalized_name(capital[2])}
            alternate_path = resolve(root, f"data/source/geonames-alternatenames-{iso2}.zip")
            with zipfile.ZipFile(alternate_path) as archive:
                with archive.open(f"{iso2}.txt") as raw:
                    reader = csv.reader(io.TextIOWrapper(raw, encoding="utf-8"), delimiter="\t")
                    for row in reader:
                        if len(row) >= 4 and row[1] == capital[1]:
                            value = normalized_name(row[3])
                            if value:
                                capital_names.add(value)

            geonames_map = {}
            all_admin1_points = {
                source_code: point for source_code, point in geonames_admin1.items()
            }
            for source_code, candidate in admin1_place_candidates.items():
                all_admin1_points.setdefault(source_code, candidate[2])
            for source_code, point in sorted(all_admin1_points.items()):
                point_geometry = QgsGeometry.fromPointXY(point)
                matches = [
                    by_fid[fid]
                    for fid in index.intersects(point_geometry.boundingBox())
                    if by_fid[fid]["geometry"].intersects(point_geometry)
                ]
                if len(matches) == 1:
                    geonames_map[source_code] = source_to_code[matches[0]["source_code"]]

            aggregate_codes = {
                source_to_code[item["source_code"]]
                for item in parts[iso3]
                if "municipality" in item["name_en"].lower()
                or "special administrative region" in item["name_en"].lower()
            }
            capital_admin_canonical = None
            point_geometry = QgsGeometry.fromPointXY(capital[3])
            for fid in index.intersects(point_geometry.boundingBox()):
                admin = by_fid[fid]
                if (
                    admin["geometry"].intersects(point_geometry)
                    and normalized_name(admin["name_en"]) in capital_names
                ):
                    aggregate_codes.add(source_to_code[admin["source_code"]])
                    capital_admin_canonical = normalized_name(admin["name_en"])

            capital_source_canonical = re.sub(
                r"[^a-z0-9]+", "-", capital[2].strip().lower()
            ).strip("-")
            canonical_aliases = {}
            if (
                capital_admin_canonical
                and capital_source_canonical != capital_admin_canonical
            ):
                canonical_aliases[capital_source_canonical] = capital_admin_canonical

            admins = [
                {
                    "code": source_to_code[item["source_code"]],
                    "name_ko": None,
                    "name_en": item["name_en"],
                    "target_tiles": None,
                }
                for item in sorted(parts[iso3], key=lambda value: (value["name_en"], value["source_code"]))
            ]
            countries.append(
                {
                    "country": {
                        "iso3": iso3,
                        "iso2": iso2,
                        "name_ko": None,
                        "name_en": metadata["name_en"],
                    },
                    "admin1_source": {
                        "path": snapshot["adm1_path"],
                        "archive_member": snapshot.get("adm1_member"),
                        "filter_field": "shapeGroup",
                        "filter_value": iso3,
                        "code_field": "shapeID",
                        "name_field": "shapeName",
                        "source_year": 2023,
                        "snapshot_version": f"CGAZ-{snapshot['version']}",
                        "code_map": source_to_code,
                    },
                    "city_source": {
                        "path": f"data/source/{iso2}.zip",
                        "member": f"{iso2}.txt",
                        "provider": "GeoNames",
                        "country_code": iso2,
                        "minimum_population": 100000,
                        "capital_geoname_id": capital[1],
                        "canonical_aliases": canonical_aliases,
                        "names_ko": {},
                    },
                    "tile_naming": {
                        "boundary_path": snapshot["adm2_path"],
                        "boundary_archive_member": snapshot.get("adm2_member"),
                        "boundary_filter_field": "shapeGroup",
                        "boundary_filter_value": iso3,
                        "boundary_provider": "geoBoundaries CGAZ 6.0.0",
                        "snapshot_version": f"CGAZ-{snapshot['version']}",
                        "boundary_year": 2023,
                        "alternate_names_path": f"data/source/geonames-alternatenames-{iso2}.zip",
                        "alternate_names_member": f"{iso2}.txt",
                        "minimum_tile_share": 0.05,
                        "require_same_country": True,
                        "require_same_admin1": True,
                        "allocation_policy": "population_descending_unique_representatives_then_greatest_overlap_fill",
                        "aggregate_admin1_codes": sorted(aggregate_codes),
                        "geonames_admin1_codes": geonames_map,
                    },
                    "population_fallback": {
                        "path": f"data/source/{iso3.lower()}_ppp_2020_1km_Aggregated_UNadj.tif",
                        "provider": "WorldPop",
                        "year": 2020,
                        "source_id": "10.5258/SOTON/WP00671",
                        "policy": "un_adjusted_1km_zonal_sum_for_unresolved_units_only",
                    },
                    "admin1": admins,
                }
            )

        registry = {
            "schema_version": 1,
            "generator": "scripts/build_country_registry.py",
            "boundary_snapshot": f"CGAZ-{snapshot['version']}",
            "countries": countries,
        }
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        registry_path.write_text(
            json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        feedback.pushInfo(
            f"Wrote {len(countries)} countries and {sum(len(item['admin1']) for item in countries)} Admin-1 records"
        )
        return {OUTPUT_REGISTRY: str(registry_path)}
