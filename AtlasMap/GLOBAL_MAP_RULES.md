# Atlas Global Map Rules

Status: authoritative design contract

Scope: the Korean Peninsula prototype and every country added later

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

1. Every country shares one immutable regular-hex grid. Do not generate a new
   grid origin at each border.
2. Final game tiles are complete regular hexagons and are never clipped to a
   coastline or administrative boundary.
3. The current prototype target area is 605.21 km2. Tolerances and orientation
   are configuration values.
4. A tile ID is derived only from immutable grid coordinates and orientation.
   It must not contain country, Admin-1, city name or current ownership.
5. Neighbor relationships are derived from grid coordinates or normalized
   shared-edge keys and must be symmetric.
6. EPSG:5179 is valid only for the Korean prototype. Before a world build, Atlas
   must freeze a global CRS or DGGS plus antimeridian, world-wrap and polar rules.

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
9. Multiple tiles may carry the same naming-unit code. The algorithm is identical
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

1. Capital status follows the represented capital naming-unit code and does not
   change ownership or fill class.
2. Draw one yellow outline on the exterior edges of the complete official
   capital ADM1 tile group. Cancel internal shared edges.
3. The capital ADM1 receives the same feasible one-tile representation floor as
   every other official ADM1.
4. A capital name may cross neither national nor Admin-1 ownership boundaries.

## 8. QGIS presentation

1. Use exactly three fills: `admin`, `city` and `metropolis`. Capital is an
   outline, not a fourth fill.
2. Tile names remain enabled at all closer zoom levels after their configured
   zoomed-out threshold and must fit completely inside the hex.
3. Show `tile_id` only at a sufficiently close scale.
4. Hide Admin-1 summary labels at close scales so they cannot cover tile names.
5. Keep source boundaries in a separate toggleable validation group.
6. Use project-relative paths and QGIS core functionality only.

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

The Korean release gate and world-readiness gate are separate.

Every regional release must verify:

- pinned sources and expected CRS;
- complete valid regular hexagons and target area tolerance;
- greatest-overlap country-or-ocean ownership;
- one feasible positive-overlap representative per official Admin-1, with
  greatest-overlap ownership for every remaining tile;
- no ownership overrides and no tile overlaps;
- positive-overlap same-country naming allocation;
- unique stable ownership-independent IDs;
- complete symmetric adjacency;
- exact national population reconciliation;
- three fills and correct capital naming-group outlines;
- relative shared paths, successful exports and generated preview.

The world-readiness gate additionally requires:

- frozen global CRS/DGGS, antimeridian and polar policies;
- a data-driven global country/admin registry;
- spatially indexed boundary lookup and scalable partitioning;
- sample tests for islands, enclaves, disputed areas, antimeridian crossings and
  polar regions;
- country-neutral ADM1/ADM2 hierarchy-coherence and source-completeness audits
  that report contradictions without silently repairing ownership;
- no country-specific ownership or naming exceptions.

Never call the world pipeline complete while the separate global-readiness
report has blocking failures.
