# Source data

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
- Selection: features where `adm0_a3 = 'KOR'`
- Verification: the selected source contains exactly 17 features, including
  Sejong (`KR-50`).

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
