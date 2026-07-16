# Korea administrative reference audit

> Current policy (2026-07-16): CGAZ 6.0.0 is the accepted frozen global
> snapshot. Modern facts below are `report_only` evidence and do not trigger
> country-specific geometry patches. Sangwon is under North Hwanghae in the
> accepted snapshot; PRK retains an older 11-unit ADM1 hierarchy. Current KOR
> ADM1/ADM2 conflicts are documented separately in
> `reports/korea_cgaz_hierarchy_consistency_audit.md`.

Status: active release audit

This document records administrative-boundary facts that geometry-only map
validation cannot establish. A structurally valid tile map is not historically
correct merely because its polygons, adjacency and ownership calculations pass.

## Scenario time basis

Atlas targets a modern Korean Peninsula scenario. Unless the configuration
explicitly pins a historical scenario date, post-2011 administrative membership
is required for the Pyongyang and North Hwanghae boundary discussed below.

## Pyongyang and Sangwon chronology

- Before the 2010 reorganization, Sangwon County was administered by Pyongyang.
- In 2010, Sangwon County, Chunghwa County and Sungho District were transferred
  from Pyongyang to North Hwanghae Province. Kangnam County was transferred at
  the same time.
- Kangnam County was restored to Pyongyang in 2011. Sangwon County was not.
- Therefore, `Sangwon -> Pyongyang` is historically usable only for a pre-2010
  scenario. For the modern Atlas scenario, the required parent is North
  Hwanghae.
- The 2022 first-level structure consists of nine provinces, Pyongyang directly
  governed city, and the three special cities Rason, Nampo and Kaesong: 13
  first-level units in total. Kaesong was elevated again in 2019.

References:

- Human Rights in North Korea, *The Pyongyang Republic* (2024):
  https://www.hrnk.org/wp-content/uploads/2024/07/Collins_PyongyangRepublic_FINAL_WEB.pdf
- North Korea Leadership Watch, *Pyongyang Shrunk by 1/3* (2010):
  https://www.nkleadershipwatch.org/2010/07/19/pyongyang-shrunk-by-13/
- Korea Times report citing the South Korean Ministry of Unification on the
  later Kangnam restoration (2012):
  https://www.koreatimes.co.kr/foreignaffairs/20120229/nk-incorporates-key-farming-county-into-pyongyang
- National Atlas of Korea, North Korean administrative divisions (2022 basis):
  https://nationalatlas.ngii.go.kr/pages/page_3875.php
- Ministry of Unification North Korea Information Portal, including the 2019
  Kaesong elevation:
  https://nkinfo.unikorea.go.kr/nkp/pge/view.do?menuId=SO302

## Boundary candidate findings

| Candidate | Reference observation | Sangwon parent | Decision |
| --- | --- | --- | --- |
| World Bank Official Boundaries v3 | KOR has only 15 ADM1 units and unusable placeholder ADM2 rows | `P'yongyang-si` (`PRK010`) | Rejected |
| geoBoundaries `gbOpen`, commit `9469f09` | KOR ADM1 has 17 units; PRK samples use 2018/2019 source years | Sangwon point-on-surface is inside North Hwanghae (`KP08`) | Screening only |
| NGII public-data CSV, 2024-08-08 | Official hierarchy metadata has 12 ADM1 rows (Pyongyang, Kaesong, Nampo and nine provinces) and 218 ADM2 rows, but the `SDE.ST_GEOMETRY` values expose only envelopes and an inaccessible Oracle BLOB reference | Sangwon is present as an official ADM2 record; geometry is not reconstructable from the CSV | Evidence only; rejected as geometry input |
| OpenStreetMap/Geofabrik, 2026-07-10 snapshot | Live tags expose 13 ADM1 and 201 ADM2 relations, but the pinned PBF produces only 12 ADM1 and 195 ADM2 polygons; current North Pyongan relation `356540` has tags but no member geometry | Sangwon polygon point-on-surface is inside North Hwanghae relation `356442` | Rejected as current geometry input |

The geoBoundaries sample fixes the specific Sangwon relationship but is not yet
accepted as the global canonical snapshot. Its complete CGAZ hierarchy,
topology, metadata counts, licenses and non-Korean samples still require review.

The NGII CSV files are retained unchanged under
`data/source/ngii_prk_20240808/`. They are authoritative hierarchy evidence,
but they cannot replace the configured boundary layer: the last argument is an
Oracle object reference such as `oracle.sql.BLOB@...`, not polygon coordinates.
The file's stated 12-unit first level also omits Rason even though the National
Atlas describes the 2022 structure as 13 units.

The OSM live screening resolves both dated facts at the tag/hierarchy level.
A pinned 2026-07-10 Geofabrik PBF was subsequently downloaded and transformed
to EPSG:5179. It confirms the Sangwon relationship spatially, but fails
hierarchy completeness: North Pyongan has no polygon, only 195 ADM2 polygons
are emitted, and 23 ADM2 points-on-surface have no available ADM1 parent.
Atlas will not build from a live query, synthesize North Pyongan, or accept an
incomplete parent hierarchy.

## Current frozen-snapshot observation

The current build no longer uses the earlier Natural Earth mixture described in
the historical candidate sections above. ADM0, ADM1 and ADM2 now come from the
same pinned CGAZ 6.0.0 global release.

- Sangwon is spatially assigned to North Hwanghae in the accepted snapshot.
- PRK still reflects an older 11-unit first-level hierarchy rather than the
  modern 13-unit reference structure.
- KOR has all configured 17 ADM1 units, but several metropolitan ADM1 polygons
  conflict with ADM2 membership. Dalseong is spatially classified under North
  Gyeongsang, and multiple Gwangju autonomous districts are classified under
  South Jeolla.
- The KOR ADM2 snapshot omits Yeonggwang-gun.

These are frozen-source limitations. They do not trigger country-specific
geometry edits or ownership overrides. The detailed KOR measurements, naming
effects and Gwangju metropolis-anchor failure are in
`reports/korea_cgaz_hierarchy_consistency_audit.md`.

## Future global snapshot migration gates

A future worldwide snapshot may replace CGAZ 6.0.0 only after it:

1. supplies one compatible ADM0/ADM1/ADM2 hierarchy for all configured
   countries;
2. exposes stable parent identifiers or passes country-neutral spatial
   hierarchy checks;
3. improves the known PRK and KOR discrepancies without introducing manual
   country patches;
4. preserves licenses, redistribution rights, stable identifiers and pinned
   checksums;
5. passes the complete regional and global regression suite.

Current status wording is:

- deterministic CGAZ Korea geometry validation: PASS;
- exact modern administrative semantics: known limitations, report only;
- world-build readiness: FAIL until the independent global blockers are closed.
