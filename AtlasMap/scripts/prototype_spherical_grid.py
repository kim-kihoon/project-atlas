"""Generate and verify the configured OGC ISEA3H Korea-area prototype."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys


def resolve(root, relative_path):
    path = (root / relative_path).resolve()
    if root != path and root not in path.parents:
        raise ValueError(f"Path escapes project root: {relative_path}")
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/atlas_east_asia.json")
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    root = config_path.parent.parent.resolve()
    settings = json.loads(config_path.read_text(encoding="utf-8"))
    grid = settings["globalization"]["global_grid"]
    if grid["crs_or_dggs"] != "OGC ISEA3H":
        raise ValueError(f"Unsupported spherical grid: {grid['crs_or_dggs']}")

    try:
        from dggal import (
            Application, Array, Degrees, GeoExtent, GeoPoint, ISEA3H,
            pydggal_setup,
        )
    except ImportError as exc:
        raise SystemExit(
            "DGGAL is required. Install the pinned requirements-dggs.txt first."
        ) from exc

    app = Application(appGlobals=globals())
    pydggal_setup(app)
    dggrs = ISEA3H()
    level = int(grid["level"])
    edge_refinement = int(grid["edge_refinement"])
    west, south, east, north = map(float, grid["prototype_bbox_wgs84"])
    bbox = GeoExtent(
        GeoPoint(Degrees(south), Degrees(west)),
        GeoPoint(Degrees(north), Degrees(east)),
    )
    zones = list(dggrs.listZones(level, bbox))
    zones.sort(key=dggrs.getZoneTextID)

    global_count = int(dggrs.countZones(level))
    if global_count != int(grid["global_cell_count"]):
        raise ValueError(
            f"Global cell count mismatch: {global_count} != {grid['global_cell_count']}"
        )

    output_path = resolve(root, grid["prototype_geojson"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    areas = []
    edge_counts = []
    neighbor_counts = []
    sample_ids = []
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write('{"type":"FeatureCollection","features":[\n')
        for position, zone in enumerate(zones):
            zone_id = str(dggrs.getZoneTextID(zone))
            area_km2 = float(dggrs.getZoneArea(zone)) / 1_000_000.0
            edge_count = int(dggrs.countZoneEdges(zone))
            neighbor_count = int(dggrs.getZoneNeighbors(zone, Array("<int>")).count)
            centroid = dggrs.getZoneWGS84Centroid(zone)
            vertices = dggrs.getZoneRefinedWGS84Vertices(zone, edge_refinement)
            ring = [[float(vertex.lon), float(vertex.lat)] for vertex in vertices]
            ring.append(ring[0])
            feature = {
                "type": "Feature",
                "id": f"ATLAS_ISEA3H_L{level}_{zone_id}",
                "properties": {
                    "zone_id": zone_id,
                    "level": level,
                    "cell_type": "pentagon" if edge_count == 5 else "hexagon",
                    "area_km2": area_km2,
                    "neighbor_count": neighbor_count,
                    "center_lon": float(centroid.lon),
                    "center_lat": float(centroid.lat),
                },
                "geometry": {"type": "Polygon", "coordinates": [ring]},
            }
            if position:
                handle.write(",\n")
            json.dump(feature, handle, ensure_ascii=False, separators=(",", ":"))
            areas.append(area_km2)
            edge_counts.append(edge_count)
            neighbor_counts.append(neighbor_count)
            if len(sample_ids) < 5:
                sample_ids.append(zone_id)
        handle.write("\n]}\n")

    seoul = dggrs.getZoneFromWGS84Centroid(
        level, GeoPoint(Degrees(37.5665), Degrees(126.9780))
    )
    seoul_id = str(dggrs.getZoneTextID(seoul))
    report_path = resolve(root, grid["prototype_report"])
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report = [
        "# Atlas spherical-grid prototype report",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        f"- DGGRS: `{grid['crs_or_dggs']}`",
        f"- Definition: {grid['definition_uri']}",
        f"- Level: {level}",
        f"- Global cells: {global_count:,}",
        f"- Prototype bbox WGS84: [{west}, {south}, {east}, {north}]",
        f"- Prototype bbox cells: {len(zones):,}",
        f"- Area range in prototype: {min(areas):.12f} to {max(areas):.12f} km2",
        f"- Cell edge counts in prototype: {sorted(set(edge_counts))}",
        f"- Neighbor counts in prototype: {sorted(set(neighbor_counts))}",
        f"- Seoul sample zone: `ATLAS_ISEA3H_L{level}_{seoul_id}`",
        f"- First zone IDs: {', '.join(f'`{value}`' for value in sample_ids)}",
        f"- GeoJSON: `{grid['prototype_geojson']}`",
        "",
        "The bbox output is a geometry/provenance reference. The production",
        "Korean build now enumerates these same canonical cells and reruns the",
        "country-neutral ownership, naming, city and population rules.",
    ]
    report_path.write_text("\n".join(report) + "\n", encoding="utf-8", newline="\n")
    print(f"Wrote {len(zones)} cells: {output_path}")
    print(f"Wrote report: {report_path}")


if __name__ == "__main__":
    main()
