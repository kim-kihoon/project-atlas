# Atlas spherical-grid Korea implementation report

Date: 2026-07-17

Status: **historical predecessor to the accepted East Asia spherical build**.
The Korea-only build passed at the time and its grid is now extended by the
six-country production milestone.

## 1. Purpose

This report records the completed migration of the Korean Peninsula prototype
from a local planar regular-hex grid to the canonical spherical grid intended
for the eventual Atlas world map. It separates implemented and validated facts
from future planning estimates.

The authoritative design contract remains `GLOBAL_MAP_RULES.md`. This report is
an implementation record and does not override that contract.

## 2. Canonical world grid

- DGGRS: OGC ISEA3H
- Reference surface: WGS84 authalic sphere
- Level: 11
- Generator: DGGAL 0.0.6, BSD-3-Clause
- Global cell count: 1,771,472
- Hexagons: 1,771,460
- Required pentagons: 12
- Ordinary hexagon area: 287.9335363986343 km2
- Pentagon area: 239.9446136655286 km2
- Hexagon neighbors: 6
- Pentagon neighbors: 5
- Canonical ID: `ATLAS_ISEA3H_L11_{zone_text_id}`

The 12 pentagons are a mathematical requirement of a closed spherical
hexagonal topology. They are valid cells, not errors or manual exceptions.

## 3. Geometry and QGIS representation

Canonical identity, hierarchy and adjacency come from ISEA3H. DGGAL generates
the WGS84 interchange geometry. The Korean GeoPackage projects those complete
cells to EPSG:5179 for intersection analysis and QGIS display without changing
their canonical IDs or neighbor relationships.

The cells are topological hexagons, not identical Euclidean regular hexagons in
every 2D projection. Their apparent orientation and curvature change when the
spherical grid is displayed in EPSG:5179. All Korean cells belong to ISEA face
`F8`; the visible inflection around the Jeolla-Gyeongsang area is not an
icosahedron face seam or pentagon. It is the projected appearance of a rotating
spherical grid, made visually prominent near the EPSG:5179 central meridian at
127.5 degrees east.

For a future world QGIS project:

- use an equal-area world projection for the familiar overview;
- optionally provide an ISEA unfolded-face view for topology inspection;
- retain appropriate regional projections for detailed editing;
- never derive canonical adjacency from the chosen display projection.

## 4. Korean production result

The 2026-07-17 deterministic rebuild produced:

| Country | Final cells |
| --- | ---: |
| Republic of Korea (`KOR`) | 332 |
| Democratic People's Republic of Korea (`PRK`) | 416 |
| Total | 748 |

These counts are derived from greatest country-or-ocean overlap. They are not
fixed quotas. The existing country-neutral Admin-1 representation, naming,
city anchoring, population reconciliation and capital-outline rules were rerun
without country-specific ownership patches.

Population reconciliation remains exact:

- KOR: 51,600,388
- PRK: 26,633,691

## 5. Logical-side rendering defect and correction

DGGAL refinement level 0 represents each logical cell side with five display
segments. The first spherical build compared those projected segments
individually. Tiny floating-point differences could leave one segment unmatched
and incorrectly classify it as an exterior administrative border. In QGIS this
appeared as isolated short black lines inside otherwise same-owner areas.

The corrected builder now:

1. maps every canonical cell side one-to-one to its DGGAL neighbor;
2. uses the sorted canonical neighbor-ID pair as the edge key;
3. stores all five refined display segments as one six-vertex polyline;
4. derives adjacency, administrative borders and capital outlines from that
   complete logical side;
5. rejects any border record that is only a partial refined segment.

The correction changed no tile ownership, names, cities or populations.

| Output | Before | After |
| --- | ---: | ---: |
| Administrative/country/exterior border records | 4,294 segment records | 796 logical sides |
| Capital outline records | 160 segment records | 32 logical sides |

The validation gate now explicitly checks that every administrative and capital
outline contains one complete canonical logical side.

## 6. Release validation

`reports/validation_report.md` records an overall PASS. Important spherical
checks include:

- global ISEA3H level-11 count equals 1,771,472;
- every final ID resolves to its canonical DGGAL zone;
- cell type, neighbor count and spherical area are correct;
- final cells are complete uncut candidates;
- no final cells overlap;
- neighbor lists are unique, symmetric and exactly match canonical topology;
- 796 administrative outline records are complete logical sides;
- 32 capital outline records are complete logical sides;
- country, Admin-1, naming, city and population rules still pass;
- QGIS paths are relative and the preview and Unreal exports are generated.

Verified commands on Windows:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_windows.ps1 -Stage build
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_windows.ps1 -Stage validate
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_windows.ps1 -Stage export
```

The equivalent macOS launcher uses the same configuration and Python logic.

## 7. Pentagon center locations

The following centers were queried directly from the configured DGGAL ISEA3H
level-11 grid. Geographic descriptions are approximate; future ownership still
uses the normal country-or-ocean overlap calculation.

| Zone | Latitude | Longitude | Approximate location |
| --- | ---: | ---: | --- |
| `F0-0-B` | 58.3971 | -168.8000 | Bering Sea west of Alaska |
| `F1-0-B` | 0.0000 | -137.0825 | eastern/central Pacific Ocean |
| `F2-0-B` | 31.8324 | -78.8000 | Atlantic east of South Carolina |
| `F3-0-B` | -31.8324 | -78.8000 | South Pacific west of Chile |
| `F4-0-B` | 0.0000 | -20.5175 | equatorial Atlantic Ocean |
| `F5-0-B` | -58.3971 | 11.2000 | Southern Ocean/southern Atlantic |
| `F6-0-B` | 0.0000 | 42.9175 | Somalia |
| `F7-0-B` | -31.8324 | 101.2000 | Indian Ocean west of Australia |
| `F8-0-B` | 31.8324 | 101.2000 | western Sichuan, China |
| `F9-0-B` | 0.0000 | 159.4825 | western equatorial Pacific Ocean |
| `FA-0-B` | 58.3971 | 11.2000 | Skagerrak near Sweden and Norway |
| `FB-0-B` | -58.3971 | -168.8000 | Southern Ocean southeast of New Zealand |

Approximately two pentagon centers are on land, in China and Somalia; most are
ocean cells. A center classification alone does not determine ownership.

## 8. World scalability status

The complete level contains about 1.77 million cells. This is manageable as an
indexed, partitioned dataset but should not be rendered as one fully labeled
QGIS layer at world overview scale. The intended architecture is:

- partition by ISEA parent cell or regional build unit;
- use spatial indexes for ADM0, ADM1 and ADM2 intersections;
- show generalized/parent cells at overview scales;
- load detailed level-11 geometry only for the visible region;
- enable tile labels only at useful close scales;
- keep static geometry separate from large gameplay-state tables;
- export Unreal data in deterministic chunks rather than one world GeoJSON.

`reports/global_readiness_report.md` remains FAIL for the world pipeline even
though the Korean release passes. The three current blockers are:

1. a data-driven country and administrative registry;
2. global ADM0 and ADM1 spatial indexes;
3. an automated country-neutral ADM1/ADM2 hierarchy-coherence audit.

## 9. Proposed East Asia milestone

The preferred next expansion milestone is six configured countries on the same
canonical grid: KOR, PRK, JPN, TWN, MNG and CHN.

The following figures are planning estimates only and must not become quotas:

| Country | Estimated land-dominant cells |
| --- | ---: |
| KOR | 332 validated |
| PRK | 416 validated |
| JPN | about 1,300 |
| TWN | about 125 |
| MNG | about 5,400 |
| CHN | about 33,000 |
| Total | about 40,000 to 42,000 |

Recommended implementation order:

1. Japan, to exercise islands, coastline dominance and fragmented Admin-1s;
2. Taiwan, while auditing how the pinned global snapshot encodes ADM0 status;
3. Mongolia, to exercise large sparse inland regions;
4. China, to exercise large-scale performance, many Admin-1s and metropolis
   allocation;
5. one integrated six-country regression build.

Taiwan or any disputed feature must follow the pinned canonical snapshot. Do
not introduce a political or country-specific ownership patch.

## 10. Primary artifacts

- `Atlas_Korea.qgz`
- `data/processed/Atlas_Korea.gpkg`
- `previews/Atlas_Korea_Overview.png`
- `exports/Atlas_Korea_Tiles.geojson`
- `exports/Atlas_Korea_Tiles.csv`
- `reports/allocation_report.md`
- `reports/validation_report.md`
- `reports/global_readiness_report.md`
- `reports/spherical_grid_decision.md`
- `reports/spherical_grid_prototype_report.md`
- `data/processed/Atlas_Spherical_Grid_Korea_Prototype.geojson`
