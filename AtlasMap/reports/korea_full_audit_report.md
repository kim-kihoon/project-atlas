# Atlas Korea full audit report

> Superseded on 2026-07-16 by the CGAZ 6.0.0 rebuild. Current result: Korea
> release validation **PASS**, 364 tiles (KOR 158, PRK 206), one feasible
> positive-overlap representative per official Admin-1 followed by
> greatest-overlap ownership, and ownership-independent grid IDs. See
> `reports/global_snapshot_decision.md`,
> `reports/korea_cgaz_hierarchy_consistency_audit.md` and
> `reports/validation_report.md`. The detailed counts below describe the
> superseded pre-CGAZ build and must not be read as current output.

Generated: 2026-07-16 (Asia/Seoul)

Overall result: **FAIL - modern PRK administrative hierarchy is incomplete**

The map was rebuilt from the configured sources, structurally validated,
exported again and inspected at the GeoPackage, QGIS project, preview and export
levels. Structural map logic now passes. The remaining release failures are
dated administrative-reference failures, not hex geometry failures.

## Execution results

| Stage | Result | Detail |
| --- | --- | --- |
| Build | PASS | 1,590 candidates; 365 final tiles; GeoPackage, QGIS project, report and preview regenerated |
| Repeat-build replacement | PASS | Existing GeoPackage replaced through a completed same-directory staging file |
| Structural validation | PASS | 65 checks passed |
| Administrative-reference validation | FAIL | 2 dated checks failed |
| Unreal CSV export | PASS | 365 rows |
| Unreal GeoJSON export | PASS | 365 features; all tile IDs match the CSV |
| Global-readiness audit | FAIL | 8 world-pipeline blockers remain |

QGIS had the old GeoPackage open during the first repeat-build attempt. The
build now writes a complete staging GeoPackage and replaces the deliverable only
after all layers succeed. When another application locks the target, the build
keeps the prior deliverable and reports that QGIS must be closed.

## Final dataset inventory

| Metric | KOR | PRK | Total |
| --- | ---: | ---: | ---: |
| Final tiles | 161 | 204 | 365 |
| Configured/generated Admin-1 units | 17 | 11 | 28 |
| National population | 51,600,388 | 26,633,691 | 78,234,079 |
| Initial city anchors | 58 | 23 | 81 |
| Capital-named tiles | 1 | 3 | 4 |

Other generated totals:

- map classes: 268 administrative, 82 city and 15 metropolis tiles;
- Admin-1 assignment: 360 greatest-overlap tiles and 5 representation tiles;
- naming assignment: 265 unique representatives, 10 positive-overlap
  representatives and 90 greatest-overlap fill tiles;
- 365 valid, unique regular-hex tile geometries;
- 524 game Admin-1 boundary edges;
- 20 capital-outline edges in two capital groups;
- no manual ownership override;
- exact WPP population reconciliation for both countries.

## Newly detected and fixed structural defects

### Repeat build on Windows

`CreateOrOverwriteFile` failed whenever `Atlas_Korea.gpkg` already existed.
The builder now writes a new same-directory GeoPackage and replaces the old file
only after all six layers are complete. This also prevents a failed partial
build from destroying the last valid deliverable.

### Incomplete neighbor lists

The former GEOS pairwise-intersection test missed many mathematically shared
hex edges because of floating-point differences. Existing IDs were valid and
symmetric, so the old validator did not detect absent relationships.

Adjacency is now derived from normalized hex-edge keys, the same topology used
for game borders. The validator independently reconstructs every shared edge
and requires exact equality with `neighbor_ids`.

The previously isolated northern tile now records:

```text
PRK_P_R100067_C100026
  -> PRK_P_R100066_C100026
  -> PRK_P_R100066_C100027
```

The new complete-neighbor check passes after the rebuild.

## Remaining release failures

### Missing modern PRK Admin-1 units

The configured Natural Earth PRK layer generates only 11 first-level units.
The modern 2022 structure contains 13: nine provinces, Pyongyang, Rason, Nampo
and Kaesong. The following required units are absent:

- `KP-14` Nampo, first-level again from 2010;
- `KP-15` Kaesong, elevated in 2019.

### Sangwon assigned to Pyongyang

The generated naming source assigns `Sangwon` to `KP-01` Pyongyang. For the
configured 2026 scenario date it must belong to `KP-06` North Hwanghae. The
current four-tile Pyongyang ownership group and its yellow outline are
internally consistent with the stale source, but not with the modern hierarchy.

Full chronology and source links are in
`reports/korea_administrative_reference_audit.md`.

## QGIS and export inspection

- The QGIS project uses relative paths and EPSG:5179.
- Tile labels remain configured with no close-zoom cutoff and are constrained
  to their polygons; Admin-1 summary labels are overview-only.
- Game Admin-1 borders and capital outlines render above tile fills.
- The overview PNG is byte-identical to the prior accepted overview and shows
  the complete peninsula and Jeju group.
- CSV and GeoJSON contain the same 365 `tile_id` values.
- GeoJSON loads through GDAL as 365 EPSG:5179 polygon features.

## Release verdict

The accurate status is:

- hex grid, national ownership, configured Admin-1 overlap, naming algorithm,
  population, adjacency, styling and exports: **PASS**;
- modern PRK administrative hierarchy: **FAIL**;
- overall Korea map release: **NOT YET PASS**.

The next corrective build must use a compatible PRK ADM1/ADM2 snapshot that
contains all 13 modern first-level units and places Sangwon in North Hwanghae.
No manual tile-ownership override may be used to simulate that correction.

## Boundary-source acquisition update

The 2024-08-08 NGII public-data files were downloaded and checksummed. They
confirm an official 12-unit table containing Kaesong and Nampo and provide 218
ADM2 names, but their `SDE.ST_GEOMETRY` strings contain only an envelope,
summary values and an inaccessible Oracle BLOB reference. They are therefore
usable as official hierarchy evidence, not as polygon geometry.

A 2026-07-16 OpenStreetMap live screening found all 13 modern ISO-coded ADM1
relations and 201 ADM2 relations within the DPRK country relation. A pinned
2026-07-10 Geofabrik PBF was then downloaded and inspected. GDAL produced 12
ADM1 and 195 ADM2 polygons: North Pyongan relation `356540` has no member
geometry, and 23 ADM2 polygons have no available ADM1 parent. Sangwon itself
does fall inside North Hwanghae. The OSM snapshot is therefore rejected as the
current build source, and the release verdict remains unchanged rather than
silently filling missing geometry or mixing providers.

Detailed acquisition evidence and the next acceptance gates are recorded in
`reports/prk_boundary_source_update_2026-07-16.md`.
