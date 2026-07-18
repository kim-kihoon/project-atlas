# Atlas canonical boundary snapshot decision

Decision date: 2026-07-16 (Asia/Seoul)

Status: **ACCEPTED FOR THE KOREAN PROTOTYPE AND FUTURE COUNTRY INGESTION**

## Selected baseline

Atlas pins geoBoundaries CGAZ 6.0.0 at commit
`1289e40e366c7b320550be1ee0614a9472d572d4`. ADM0, ADM1 and ADM2 are read
from the same global release. The selection deliberately prioritizes worldwide
coverage, compatible hierarchy fields, stable IDs, open redistribution terms
and reproducibility over the newest boundary available for each country.

| Level | Global features | Groups | Invalid | SHA-256 |
| --- | ---: | ---: | ---: | --- |
| ADM0 | 218 | 218 | 0 | `95761885d55abf850d75d6835779a6e9fae966b1fa1ad5534f40865e5b71180c` |
| ADM1 | 3,223 | 218 | 0 | `1571b7bfc8a64940ad8c380a91d997a6d9a9a78090b235aced00eb44a2c0106e` |
| ADM2 | 49,617 | 218 | 0 | `06cadadae2f1e8fab89dec62365a850b663da280df712c39c96e3c9f33a49696` |

All required group and feature identifiers are nonblank, and global ADM1/ADM2
identifiers are unique.

## Korean Peninsula screening

- KOR: 17 ADM1 and 228 ADM2 features.
- PRK: 11 ADM1 and 179 ADM2 features.
- KOR/PRK have no invalid geometries or same-level positive-area overlaps in
  the screening extract.
- Sangwon's point-on-surface is in North Hwanghae in this snapshot.
- Six KOR island ADM2 representative points fall outside their documented ADM1
  after simplification. Naming therefore uses same-country positive overlap and
  is not clipped by ADM1.
- PRK reflects an older 11-unit first-level hierarchy with Nampo and without
  the modern separate Rason/Kaesong arrangement. This is an intentional frozen
  snapshot limitation.
- Several KOR metropolitan extents are historically smaller than current
  official extents. The prototype grid was subsequently reduced globally from
  605.21 km2 to 200.00 km2 per hex to improve internal-development spatial
  detail without city-specific scale exceptions. Small official areas may
  still require the common feasible one-tile representation rule.
- The finer grid exposed small places where the frozen ADM2 layer has no
  positive overlap inside an assigned Admin-1 tile. In that exact case only,
  the pipeline uses the same-owner Admin-1 name as a zero-population coverage
  fallback. It does not compete for a representative tile or alter ownership.
- The KOR ADM1 and ADM2 layers are not internally hierarchical in several
  metropolitan areas. Dalseong-gun overlaps North Gyeongsang by 98.707% and
  Daegu by only 1.293%; Gwangsan-gu overlaps South Jeolla by 98.597% and
  Gwangju by only 1.403%. Gwangju Seo-gu is likewise placed primarily outside
  the Gwangju ADM1 extent.
- The KOR ADM2 layer has no Yeonggwang-gun polygon, even though GeoNames retains
  a populated-place record for Yeonggwang. Population evidence alone cannot
  create missing boundary geometry.
- These conflicts are documented in
  `reports/korea_cgaz_hierarchy_consistency_audit.md`. They are accepted frozen
  snapshot limitations, not evidence that the modern administrative
  relationships are correct.

## Enforced compatibility rules

- No country-specific boundary replacement or ownership override.
- Country ownership always follows greatest overlap. Each feasible official
  Admin-1 receives one positive-overlap representative; remaining ownership
  follows greatest overlap. Target counts remain reports only.
- Naming is clipped to the final Admin-1 scope and uses positive-overlap units
  in descending population order, then greatest-overlap fill.
- Tile IDs are based on grid coordinates and never contain the owner.
- Modern administrative facts remain `report_only` evidence unless Atlas
  migrates the entire global snapshot.
- Source-hierarchy contradictions remain `report_only`; the pipeline does not
  apply country-specific parent overrides, geometry patches or missing-unit
  synthesis.

## Release result

The final Korean build contains 364 complete hexes: 158 KOR and 206 PRK. The
Korea release validation passes. The separate global-readiness audit still
blocks declaring this EPSG:5179 prototype a world-build pipeline until a global
CRS/DGGS, antimeridian and polar policy, data-driven country registry and
global-scale spatial indexing are implemented.
