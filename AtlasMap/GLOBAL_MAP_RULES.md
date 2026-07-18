# Atlas Global Map Rules

Status: authoritative design contract

Scope: the East Asia six-country milestone and every country added later

Encoding: UTF-8

## 1. Canonical boundary snapshot

1. Production ADM0, ADM1 and ADM2 boundaries must come from one pinned global
   dataset version. Do not mix newer country-specific geometry into ownership.
2. The initial canonical snapshot is geoBoundaries CGAZ 6.0.0 at commit
   `1289e40e366c7b320550be1ee0614a9472d572d4`.
3. Pin provider, version, represented years, license, URLs, archive members and
   SHA-256 checksums. A build must never silently fetch a newer file.
4. Worldwide compatibility, stable fields and reproducibility take priority
   over country-specific recency. Older boundaries are acceptable when their
   limitations are documented.
5. Official or newer country sources may be used for audits, but never as
   silent ownership patches. Changing the canonical snapshot is a global data
   migration and requires full regression review.
6. Do not invent geometry, population, hierarchy, provenance or license data.
7. A shared release does not guarantee that ADM1 and ADM2 are internally
   hierarchical in every country. Atlas still derives an ADM2 naming unit's
   working parent from greatest geometric overlap with the pinned ADM1 layer.
8. When an external hierarchy reference or source attribute contradicts that
   spatial parent, record the conflict as data-quality evidence. Do not
   reparent, reshape or synthesize the unit for one country.
9. A missing source unit remains absent from the build. Country-specific
   boundary supplements, hand-authored parent tables and geometry patches are
   forbidden in the canonical pipeline.
10. A correction is eligible for production only through a globally applicable
    source adapter or a migration of the complete pinned worldwide snapshot.

## 2. Global grid and tile identity

1. Every country and ocean shares one immutable OGC ISEA3H level-11 discrete
   global grid on the WGS84 authalic sphere. The grid never resets at a national,
   regional, antimeridian or polyhedral-face boundary.
2. The complete world grid contains 1,771,472 cells: 1,771,460 hexagons and the
   12 pentagons mathematically required to close a sphere. A canonical hexagon
   has an area of about 287.933536 km2 and a canonical pentagon about
   239.944614 km2.
3. Final game cells are never clipped to coastlines or administrative
   boundaries. Geographic proportions remain global and no city receives a
   different resolution.
4. Canonical tile IDs are `ATLAS_ISEA3H_L11_{zone_text_id}` and derive only from
   the pinned DGGRS and canonical DGGAL zone identity. They never contain
   ownership, Admin-1, city or mutable gameplay state.
5. Neighbor relationships come from the canonical spherical DGGRS topology and
   must be symmetric. Hexagons have six canonical neighbors and pentagons five;
   a regional subset may expose fewer selected neighbors at its boundary.
6. ISEA face-local triangular subdivision meshes are welded across common
   vertices and edges before projection to the sphere and dual-cell
   construction. Final cells are therefore one continuous global mesh, not 20
   independently rendered planar grids, and have no antimeridian or polar seam.
7. DGGAL 0.0.6 is the pinned canonical grid engine. It is a scripted runtime
   dependency, not a QGIS plugin. QGIS core handles geometry, styling and file
   output.
8. `EPSG:8857` Equal Earth is the regional analysis/intersection CRS.
   `EPSG:3857` Web Mercator is the QGIS project and preview display CRS so the
   2D map retains a familiar cylindrical appearance. Projected geometry never
   defines canonical cell identity, cell type, spherical area or adjacency.

## 3. Country and ocean ownership

1. For every candidate hex, calculate actual intersection area against every
   relevant ADM0 territory and the remaining ocean area.
2. The greatest area wins. Stable territory code order breaks an exact tie.
3. National tile totals are derived results, never fixed targets.
4. Population, capital status, city status, desired balance and manual overrides
   may not change national ownership.
5. Two countries may never own the same tile. Disputed features remain exactly
   as represented by the pinned global snapshot.

## 4. Admin-1 ownership

1. After the country is fixed, compare only ADM1 units in that same country.
2. Initially assign the tile to the ADM1 unit with greatest intersection area.
   Stable admin code order breaks an exact tie.
3. Guarantee one positive-overlap same-country representative for every feasible
   official ADM1 that would otherwise receive zero tiles. Never take another
   official ADM1's last tile.
4. Target counts and historical design totals are report values only. The
   one-tile official-area floor is not a target-count quota.
5. `admin1_code` is ownership. It is never changed to make a name, city or
   capital visible.
6. Game administrative borders come from topology: cancel edges shared by the
   same owner and retain different-owner and exterior edges exactly once.

## 5. Display-name allocation

Ownership and display naming are independent dimensions.

1. Consider every same-country ADM2 or equivalent city/county naming unit whose
   geometry has positive area overlap with the tile.
2. Assign every naming unit to its greatest-overlap authoritative ADM1 and clip
   its geometry to that ADM1.
3. A tile considers only naming units belonging to its final ADM1 owner. Naming
   may cross neither national nor Admin-1 ownership boundaries.
4. Resolve naming-unit population through the same country-neutral GeoNames
   recovery sequence. Unknown values remain auditable and use the configured
   WorldPop fallback; never add country-specific population patches.
5. Process units in descending population order. Each unit may reserve its
   largest-overlap still-unclaimed compatible tile.
6. A smaller unit cannot evict a tile already reserved by a larger unit.
7. Fill remaining tiles with their greatest-overlap naming unit; use population
   and then stable unit code only as tie-breakers.
8. Any positive overlap is eligible. A nearest-only, zero-overlap fallback is
   forbidden.
9. If and only if a tile has no positive overlap with any eligible ADM2 or
   equivalent naming unit, use the same-owner Admin-1 geometry and name as an
   auditable coverage fallback. It must still have positive overlap, has zero
   naming-allocation population, and never participates in the unique
   representative pass or changes ownership.
10. Multiple tiles may carry the same naming-unit code. The algorithm is identical
   for every country and may not contain country-specific naming branches.

## 6. Cities and population

1. Administrative ownership and city class are independent. A city tile keeps
   its actual Admin-1 owner.
2. Each represented qualifying real city has at most one anchor tile.
3. A GeoNames city population from 100,000 to under 1,000,000 creates an initial
   `city`; 1,000,000 or more creates an initial `metropolis`.
4. Initial cities have two district slots, metropolises three and ordinary tiles
   one. Capital status adds no slot.
5. Ordinary tiles do not automatically become cities at 100,000; they become
   eligible for player-selected promotion.
6. Other tiles carrying the same naming-unit code inherit only the anchor's
   display `map_class`, not its population, `city_class` or initial-city state.
7. Each country has one exact integer game-population total from the configured
   UN WPP medium variant. City anchors are subtracted and the residual is
   distributed by WorldPop weights and largest remainder.

## 7. Capitals

1. `is_capital` is display-group membership and is true on every tile carrying
   the represented capital naming-unit code. It does not change ownership or
   fill class.
2. Draw one yellow outline only on the exterior edges of the complete
   capital-name tile group. Cancel shared edges between tiles carrying the same
   capital naming-unit code. Do not outline the rest of the capital ADM1 merely
   because it belongs to that administration.
3. `is_capital_anchor` identifies exactly one representative real-city anchor
   per country. Capital-only gameplay bonuses, facilities or slots apply to this
   anchor alone, never to every yellow-outlined tile.
4. The capital ADM1 receives the same feasible one-tile representation floor as
   every other official ADM1; capital display and gameplay status never alter
   Admin-1 allocation.
5. A capital name may cross neither national nor Admin-1 ownership boundaries.

## 8. QGIS presentation

1. Use exactly three fills: `admin`, `city` and `metropolis`. Capital is an
   outline, not a fourth fill.
2. Tile names remain enabled at all closer zoom levels after their configured
   zoomed-out threshold and must fit completely inside the hex.
3. Show `tile_id` only at a sufficiently close scale.
4. Hide Admin-1 summary labels at close scales so they cannot cover tile names.
5. Keep source boundaries in a separate toggleable validation group.
6. Use project-relative paths and QGIS core functionality for map processing
   and presentation. Do not require a QGIS plugin.
7. Render topology-derived Admin-1, country, exterior and capital logical sides
   with flat line caps and miter joins. Border widths must remain stronger than
   ordinary tile outlines without turning short spherical sides into dotted or
   blob-like marks at overview scale.
8. Preserve every canonical logical side as validation evidence. For QGIS
   presentation, line-merge only contiguous sides of the same boundary class
   and owner pair into continuous render chains; this must not dissolve source
   polygons, change ownership, or alter canonical adjacency.
9. Do not assume the DGGRS neighbor-list order equals refined boundary-side
   order. Match every side one-to-one to the nearest neighboring zone centroid
   on the sphere, and validate that each rendered shared side lies on both
   participating cell boundaries.

## 9. Global processing requirements

1. Read the country and admin registry from data. Do not copy one configuration
   block manually for roughly 200 countries.
2. Use spatial indexes for ADM0/ADM1/ADM2 lookup. A world build must not compare
   every hex with every polygon.
3. Normalize provider schema differences in one source adapter rather than in
   country-specific build code.
4. Support deterministic partitioned and incremental builds while preserving
   the same grid IDs and boundary results as a full build.

## 10. Validation gates

The East Asia release gate and world-readiness gate are separate.

Every regional release must verify:

- pinned sources and expected display/analysis CRS;
- canonical ISEA3H level-11 IDs, DGGAL round trips, cell types and spherical areas;
- complete valid uncut cells, including correct five-sided pentagons where present;
- greatest-overlap country-or-ocean ownership;
- one feasible positive-overlap representative per official Admin-1, with
  greatest-overlap ownership for every remaining tile;
- no ownership overrides and no tile overlaps;
- positive-overlap same-country naming allocation;
- Admin-1 naming fallback only where no eligible ADM2/equivalent overlap exists;
- unique stable ownership-independent IDs;
- complete symmetric canonical DGGRS adjacency and complete logical-side outlines;
- exact national population reconciliation;
- three fills and correct capital naming-group outlines;
- relative shared paths, successful exports and generated preview.

The world-readiness gate additionally requires:

- frozen global ISEA3H level, DGGAL version, 1,771,472-cell count and 12-pentagon contract;
- a data-driven global country/admin registry;
- spatially indexed boundary lookup and scalable partitioning;
- partitioned/LOD-capable world processing plus sample tests for islands,
  enclaves, disputed areas, all 12 pentagons, antimeridian crossings and polar regions;
- country-neutral ADM1/ADM2 hierarchy-coherence and source-completeness audits
  that report contradictions without silently repairing ownership;
- no country-specific ownership or naming exceptions.

Never call the world pipeline complete while the separate global-readiness
report has blocking failures.
