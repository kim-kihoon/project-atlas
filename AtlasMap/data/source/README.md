# Source data

## United Nations World Population Prospects 2024

- Provider: United Nations, Department of Economic and Social Affairs,
  Population Division
- Dataset: World Population Prospects 2024, total population by sex
- URL: https://population.un.org/wpp/
- Direct file: https://population.un.org/wpp/assets/Excel%20Files/1_Indicator%20(Standard)/CSV_FILES/WPP2024_TotalPopulationBySex.csv.gz
- Downloaded: 2026-07-15 (Asia/Seoul)
- Original file: `WPP2024_TotalPopulationBySex.csv.gz`
- SHA-256: `66b84489fd7875b62de9b40d960b803b8c8439367c98deab89c2f770970925b9`
- Selection: `Variant = Medium`, `Time = 2026`; KOR 51,600,388 and PRK
  26,633,691 residents after converting the source's thousands to persons.
- Use: exact national game-population totals. WorldPop supplies only the
  relative spatial weights between tiles.
- License: United Nations data terms apply; project-specific redistribution
  review remains deferred by the project owner.

## SGIS 2025 Republic of Korea administrative boundaries

- Provider: National Data Agency, SGIS administrative statistics boundaries
- Dataset page: https://www.data.go.kr/data/15129688/fileData.do
- Direct file: https://www.data.go.kr/cmm/cmm/fileDownload.do?atchFileId=FILE_000000003601705&fileDetailSn=1&insertDataPrcus=N
- Downloaded: 2026-07-16 (Asia/Seoul)
- Reference boundary: 2025 Q2; source DBF update date: 2026-01-14
- Original archive: `sgis_2025/SGIS_Administrative_Boundaries_2025.zip`
- Original archive size: 251,294,559 bytes
- SHA-256: `3f517984bfdf4bbe43ee2a8849cff010d70ac5a826f880e6976b9a1f2b30611b`
- Extracted source: `sgis_2025/admin1/bnd_sido_00_2025_2Q.*`
- CRS and coverage: EPSG:5179, all 17 Republic of Korea first-level
  administrative areas
- License/terms: the portal records `이용허락범위 제한 없음` (no restriction
  on the permitted scope of use).
- Use: authoritative KOR national land union and KOR Admin-1 ownership. The
  extracted source files are preserved without geometry edits.

## Natural Earth Admin 1 - States, Provinces

- Source: Natural Earth, 1:10m Cultural Vectors, Admin 1
- URL: https://naturalearthdata.com/downloads/10m-cultural-vectors/
- Direct file: https://naturalearth.s3.amazonaws.com/10m_cultural/ne_10m_admin_1_states_provinces.zip
- Downloaded: 2026-07-15 (Asia/Seoul)
- Dataset version: 5.1.1; DBF last-update metadata: 2022-05-08
- Original archive: `ne_10m_admin_1_states_provinces.zip`
- SHA-256: `efc59726337323058f9446210adc96673179cd344e053666ee3d28cb58ba2b05`
- License/terms status: Natural Earth describes the data as public domain and
  free for any type of project. Final project-specific redistribution review is
  intentionally deferred by the project owner.
- Selection/use: PRK Admin-1 ownership and the global nearby-country competitor
  reference used for country-versus-ocean dominance. Natural Earth is no longer
  used as the KOR Admin-1 authority.

The archive and extracted original files are preserved unchanged. Generated,
filtered, repaired, and reprojected layers belong in
`data/processed/Atlas_Korea.gpkg`.

## GeoNames Republic of Korea place data

- Provider: GeoNames geographical database
- URL: https://download.geonames.org/export/dump/KR.zip
- Downloaded: 2026-07-15 (Asia/Seoul)
- Original archive: `KR.zip`
- SHA-256: `39a040976726f385f61d70dacf6f3d6c0793fe3bfe13545bc459efdf482be08a`
- Archive member used: `KR.txt`
- Selection: population at least 100,000 and either feature class `P`, or an
  `ADM2` feature whose ASCII name ends in `-si`; duplicate city names are
  collapsed using the highest recorded population.
- Population meaning: GeoNames' positive recorded population value is primary.
  Invalid ADM2 values are recovered by shared admin-2 code, then normalized
  name, before the WorldPop raster fallback described below.
- License: GeoNames data is provided under Creative Commons Attribution 4.0.
- Download reference archive retained during source evaluation:
  `cities500.zip`, SHA-256
  `28b72bbe2a9e010de46cc4f34121f2dd0f6b5c9f0829d71242d8f1a64e0c496e`.

## WorldPop Republic of Korea population grid

- Provider: WorldPop, University of Southampton
- Dataset: South Korea 2020 unconstrained population count, 1 km, UN-adjusted
- URL: https://hub.worldpop.org/geodata/summary?id=37084
- Direct file: https://data.worldpop.org/GIS/Population/Global_2000_2020_1km_UNadj/2020/KOR/kor_ppp_2020_1km_Aggregated_UNadj.tif
- DOI: `10.5258/SOTON/WP00671`
- Downloaded: 2026-07-15 (Asia/Seoul)
- Original file: `kor_ppp_2020_1km_Aggregated_UNadj.tif`
- SHA-256: `9c8b0d1609d7a1c03d8eb156b6747c5da9e8e1afd73356e46cb3fe1f28349d30`
- Units: estimated people per raster cell, with national total adjusted to the
  UN Population Division estimate.
- Use: final country-neutral fallback only when GeoNames has no positive ADM2
  or matching populated-place population. Population is calculated by zonal
  sum within the naming-unit polygon.
- License: Creative Commons Attribution 4.0.

## geoBoundaries Republic of Korea ADM2

- Provider: geoBoundaries, `gbOpen`, boundary ID `KOR-ADM2-91817680`
- Source: https://www.geoboundaries.org/api/current/gbOpen/KOR/ADM2/
- Pinned file: https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/KOR/ADM2/geoBoundaries-KOR-ADM2.geojson
- Downloaded: 2026-07-15 (Asia/Seoul)
- Boundary reference year: 2020
- Original file: `geoBoundaries-KOR-ADM2.geojson`
- SHA-256: `c367911b02f2cd7dcae6512087d84965131971de0c9def2fc5d0ed9a7392f2d8`
- License recorded by the provider for this boundary: CC BY 3.0
- Use: city/county overlap geometry for tile display names. Districts belonging
  to a special or metropolitan city are dissolved to that first-level city so
  the naming unit remains comparable to provincial cities and counties.

## GeoNames Republic of Korea alternate names

- Provider: GeoNames geographical database
- URL: https://download.geonames.org/export/dump/alternatenames/KR.zip
- Downloaded: 2026-07-15 (Asia/Seoul)
- Original archive: `geonames-alternatenames-KR.zip`
- SHA-256: `b28f39c5fc501ddca044877c54ad77376011ce82cefb8ac8726774b1517d56c5`
- Archive member used: `KR.txt`
- Use: Korean display names matched to GeoNames ADM2 identifiers. Untagged
  Hangul alternatives are accepted when no Korean-language-tagged value exists.
- License: GeoNames data is provided under Creative Commons Attribution 4.0.

## GeoNames Democratic People's Republic of Korea place data

- Provider: GeoNames geographical database
- URL: https://download.geonames.org/export/dump/KP.zip
- Downloaded: 2026-07-15 (Asia/Seoul)
- Original archive: `KP.zip`
- SHA-256: `10bd99adafc7545e65e363e4ab85e84f436a6b328a0e6249b949b14f6833e611`
- Archive member used: `KP.txt`
- Use: the same population selection, validation, and recovery rules used for
  the Republic of Korea; Pyongyang GeoNames ID `1871859` is the capital source.
- License: GeoNames data is provided under Creative Commons Attribution 4.0.

## geoBoundaries Democratic People's Republic of Korea ADM2

- Provider: geoBoundaries, `gbOpen`
- Source: https://www.geoboundaries.org/api/current/gbOpen/PRK/ADM2/
- Downloaded: 2026-07-15 (Asia/Seoul)
- Boundary reference year: 2019
- Original file: `geoBoundaries-PRK-ADM2.geojson`
- Feature count: 179
- SHA-256: `4265ce501c4402a8bafdc27298c8462e41ed6f3170d50624503c3770b8ce91e9`
- Use: city/county overlap geometry for North Korean tile display names.
- License family: geoBoundaries `gbOpen`; redistribution review remains subject
  to the provider metadata and the project owner's later license review.

## GeoNames Democratic People's Republic of Korea alternate names

- Provider: GeoNames geographical database
- URL: https://download.geonames.org/export/dump/alternatenames/KP.zip
- Downloaded: 2026-07-15 (Asia/Seoul)
- Original archive: `geonames-alternatenames-KP.zip`
- SHA-256: `a0550bda8394bb50e1e5117b7d744bcb6cbcda538405a3fd568f13b4020a23df`
- Archive member used: `KP.txt`
- Use: Korean display names matched to GeoNames identifiers when available.
- License: GeoNames data is provided under Creative Commons Attribution 4.0.

## WorldPop Democratic People's Republic of Korea population grid

- Provider: WorldPop, University of Southampton
- Dataset: North Korea 2020 unconstrained population count, 1 km, UN-adjusted
- URL: https://hub.worldpop.org/geodata/summary?id=37063
- Direct file: https://data.worldpop.org/GIS/Population/Global_2000_2020_1km_UNadj/2020/PRK/prk_ppp_2020_1km_Aggregated_UNadj.tif
- DOI: `10.5258/SOTON/WP00671`
- Downloaded: 2026-07-15 (Asia/Seoul)
- Original file: `prk_ppp_2020_1km_Aggregated_UNadj.tif`
- SHA-256: `dbabdc46b6994919f24ccdf9b3fd44ea7f4eb837dde93f35d39d88afb600b5c7`
- Use: country-neutral zonal-sum fallback for unresolved North Korean naming
  units, identical to the Republic of Korea workflow.
- License: Creative Commons Attribution 4.0.

## Rejected global boundary candidate: World Bank Official Boundaries v3

- Provider: World Bank
- Dataset: World Bank Official Boundaries
- Catalog: https://datacatalog.worldbank.org/search/dataset/0038272/world-bank-official-boundaries
- Dataset version: 3
- Catalog modified: 2026-07-14
- Downloaded: 2026-07-16 (Asia/Seoul)
- License: Creative Commons Attribution 4.0
- Directory manifest: `world_bank_official_boundaries_v3_2026_07_14/DR0095370.csv`
- ADM0 source: `world_bank_official_boundaries_v3_2026_07_14/World Bank Official Boundaries - Admin 0.gpkg`
  - Size: 60,002,304 bytes
  - SHA-256: `a8f9860adbacdc21887f1e7375de9d7744a858e9771fb1a3c8179f2927b304f5`
- ADM1 source: `world_bank_official_boundaries_v3_2026_07_14/World Bank Official Boundaries - Admin 1.gpkg`
  - Size: 92,393,472 bytes
  - SHA-256: `fc4690ab58df4dcb363e5c6e3edf3c856b96341eede5ecbb441156afaf10d77c`
- ADM2 source: `world_bank_official_boundaries_v3_2026_07_14/World Bank Official Boundaries - Admin 2.gpkg`
  - Size: 217,718,784 bytes
  - SHA-256: `1259da4d3e6ff97d0554f3f0d151e7fcbe04fb37a235dc983ca5b32ed06daf7f`
- Evaluation: rejected as the Atlas canonical global snapshot. The files are
  retained unchanged as auditable source evidence and are not configured as
  build inputs. See `reports/global_boundary_candidate_report.md`.

## Global boundary screening sample: geoBoundaries commit 9469f09

- Provider/product: geoBoundaries `gbOpen`
- API: https://www.geoboundaries.org/api.html
- Pinned release-data commit: `9469f09`
- Downloaded: 2026-07-16 (Asia/Seoul)
- Purpose: KOR/PRK screening before downloading and evaluating the complete
  versioned CGAZ global ADM0/ADM1/ADM2 package.
- Directory: `geoboundaries_9469f09_candidate/`
- `KOR_ADM1.geojson`: 17 features, reference year 2021, SHA-256
  `6683cd1ad991676d96493fd0aae068215426497ccf82c8b0eb5683cad341cddc`
- `KOR_ADM2.geojson`: 228 file features, reference year 2020, SHA-256
  `c367911b02f2cd7dcae6512087d84965131971de0c9def2fc5d0ed9a7392f2d8`
- `PRK_ADM1.geojson`: 11 features, reference year 2018, SHA-256
  `f9aab34ec157591f4e3c573cc13b2dc390c9274f241768c7d7d98141a944368c`
- `PRK_ADM2.geojson`: 179 features, reference year 2019, SHA-256
  `4265ce501c4402a8bafdc27298c8462e41ed6f3170d50624503c3770b8ce91e9`
- Licenses: KOR ADM1 Public Domain; KOR ADM2 CC BY 3.0; PRK ADM1/ADM2
  CC BY 3.0 IGO, as returned by the official API.
- Screening status: not accepted. KOR ADM1 is complete and the Sangwon ADM2
  point-on-surface falls in North Hwanghae, but the global composite, hierarchy
  topology and metadata/file count discrepancy still require validation.
