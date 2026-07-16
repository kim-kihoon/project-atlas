# Global boundary candidate report

> Superseding decision (2026-07-16): geoBoundaries CGAZ 6.0.0 was accepted
> after complete ADM0/ADM1/ADM2 screening. See
> `reports/global_snapshot_decision.md`. Earlier screening below is retained as
> decision history.

Candidate: World Bank Official Boundaries v3
Catalog modified: 2026-07-14
Evaluated: 2026-07-16 (Asia/Seoul)
Decision: **REJECTED as the Atlas canonical global snapshot**

## Decision summary

The candidate has a useful global ADM0/ADM1/ADM2 package and the examined KOR
and PRK geometries are valid, but its Korean administrative content is too old
and incomplete for the Atlas rules. Adopting it would reproduce several known
map errors rather than resolve them.

| Gate | Expected | Observed | Result |
| --- | --- | --- | --- |
| One global package | ADM0, ADM1 and ADM2 from one version | All three levels are present in version 3 | PASS |
| License/provenance | Redistributable, pinned and checksummed | CC BY 4.0; catalog date, files and SHA-256 recorded | PASS |
| KOR ADM1 completeness | Current 17 first-level units | 15 units | FAIL |
| KOR metropolitan units | Ulsan and Sejong represented | Both absent | FAIL |
| KOR ADM2 usefulness | Actual city/county naming units | 15 placeholder rows, all `Administrative unit not available` | FAIL |
| PRK ADM1 content | Internally coherent hierarchy suitable for current map | 11 units, including Kaesong-si as ADM1 | REVIEW/FAIL |
| Sangwon parent | North Hwanghae after the 2010 transfer | `P'yongyang-si` (`PRK010`) | FAIL |
| Geometry validity | Valid KOR/PRK polygons | 0 invalid features at ADM0, ADM1 and ADM2 | PASS |

## Observed hierarchy

- KOR ADM1 count: 15.
- PRK ADM1 count: 11.
- KOR ADM2 row count: 15; none is a usable city/county division.
- PRK ADM2 row count: 183.
- Sangwon row: ADM2 `PRK010005`, parent ADM1 `PRK010` (`P'yongyang-si`).

The Sangwon record confirms that this dataset uses the older Pyongyang extent.
It therefore cannot be used to decide the yellow Pyongyang capital outline for
the intended modern scenario.

## Geometry and packaging observations

- CRS: EPSG:4326 at all three levels.
- Layers: `WB_GAD_ADM0`, `WB_GAD_ADM1`, and `WB_GAD_ADM2`.
- Global feature counts: 251 ADM0, 3,193 ADM1, and 41,020 ADM2.
- KOR/PRK invalid geometry count: zero at every downloaded level using GDAL
  `ST_IsValid`.
- Attribute names and string values contain a leading UTF-8 BOM character in
  this distribution. Any future importer would need deterministic field/value
  normalization before matching ISO codes.

Geometry validity does not compensate for obsolete or missing administrative
units. The candidate remains evidence only and must not populate the canonical
snapshot paths in `config/atlas_korea.json`.

## Next candidate gate

The next provider or assembled snapshot must pass the same checks before any
Korea rebuild:

1. one pinned global ADM0/ADM1/ADM2 version and compatible license;
2. current-enough KOR 17-unit ADM1 hierarchy, including Ulsan and Sejong;
3. usable KOR city/county ADM2 units;
4. explicit PRK hierarchy review, including Sangwon under North Hwanghae;
5. valid geometry, parent-child containment, no same-level interior overlap,
   stable codes, and a documented normalization policy;
6. sample checks outside Korea before declaring the snapshot globally usable.

Until a candidate passes, the existing Korea prototype sources remain in use
and the global readiness gate must continue to fail.

## Next candidate screening: geoBoundaries gbOpen/CGAZ

The official geoBoundaries documentation identifies CGAZ as its global ADM0,
ADM1 and ADM2 composite and publishes reproducible releases. Release 6.0.0 and
the current pinned `releaseData` commit `9469f09` are the next candidate family.
GADM is not a default alternative because its standard license forbids
commercial use and redistribution without permission.

Initial KOR/PRK samples from commit `9469f09` show:

| Sample | API metadata | File observation | Screening result |
| --- | --- | --- | --- |
| KOR ADM1 | 2021, 17 units | 17 features; Ulsan and Sejong present | PASS |
| KOR ADM2 | 2020, API says 229 units | 228 features | FAIL pending explanation |
| PRK ADM1 | 2018, 11 units | 11 features | REVIEW; not a modern complete hierarchy |
| PRK ADM2 | 2019, 179 units | 179 features | PASS count |
| Sangwon | ADM2 sample | Point-on-surface lies in North Hwanghae (`KP08`) | PASS |

This is materially better than the World Bank candidate for the reported Korean
issues, but it is not yet a canonical snapshot. Before adoption, the complete
versioned CGAZ packages must be downloaded and checked for ADM0/ADM1/ADM2
nesting, same-level overlaps, gaps, stable identifiers, country coverage,
per-file licenses and the KOR ADM2 metadata discrepancy. At least several
non-Korean countries with enclaves, antimeridian crossings, islands and disputed
territories must also pass sample validation.
