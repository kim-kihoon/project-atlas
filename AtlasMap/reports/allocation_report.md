# Atlas Korean Peninsula tile allocation report

Generated: 2026-07-16T02:11:58.439768+00:00

- Orientation: `pointy_top`
- Final tiles: **364**
- Target tile area: 605.21 km2

- Country selection: dominant overlap among nearby countries and ocean; no fixed national total
- Country ownership: a tile and its assigned Admin-1 always belong to the same dominant country
- Assignment policy: one positive-overlap same-country representative per feasible official Admin-1; remaining tiles use greatest overlap
- National ownership and target counts are never overridden

| Code | Admin area | Target | Actual | Difference |
| --- | --- | ---: | ---: | ---: |
| KR-11 | 서울 / Seoul | 1 | 1 | 0 |
| KR-26 | 부산 / Busan | 1 | 1 | 0 |
| KR-27 | 대구 / Daegu | 3 | 1 | -2 |
| KR-28 | 인천 / Incheon | 2 | 1 | -1 |
| KR-29 | 광주 / Gwangju | 1 | 1 | 0 |
| KR-30 | 대전 / Daejeon | 1 | 1 | 0 |
| KR-31 | 울산 / Ulsan | 2 | 1 | -1 |
| KR-50 | 세종 / Sejong | 1 | 1 | 0 |
| KR-41 | 경기 / Gyeonggi | 17 | 17 | 0 |
| KR-42 | 강원 / Gangwon | 28 | 32 | 4 |
| KR-43 | 충북 / Chungbuk | 12 | 12 | 0 |
| KR-44 | 충남 / Chungnam | 14 | 11 | -3 |
| KR-45 | 전북 / Jeonbuk | 13 | 15 | 2 |
| KR-46 | 전남 / Jeonnam | 20 | 15 | -5 |
| KR-47 | 경북 / Gyeongbuk | 30 | 30 | 0 |
| KR-48 | 경남 / Gyeongnam | 17 | 15 | -2 |
| KR-49 | 제주 / Jeju | 3 | 3 | 0 |
| KP-01 | 평양 / Pyongyang | 5 | 2 | -3 |
| KP-02 | 평안남도 / South Pyongan | 20 | 16 | -4 |
| KP-03 | 평안북도 / North Pyongan | 20 | 20 | 0 |
| KP-04 | 자강도 / Chagang | 27 | 27 | 0 |
| KP-05 | 황해남도 / South Hwanghae | 14 | 14 | 0 |
| KP-06 | 황해북도 / North Hwanghae | 13 | 20 | 7 |
| KP-07 | 강원도 / Kangwon | 18 | 18 | 0 |
| KP-08 | 함경남도 / South Hamgyong | 31 | 33 | 2 |
| KP-09 | 함경북도 / North Hamgyong | 27 | 28 | 1 |
| KP-10 | 량강도 / Ryanggang | 23 | 27 | 4 |
| KP-14 | 남포 / Nampo | 1 | 1 | 0 |

## Admin-1 representation assignments

- `ATLAS_P_R100030_C100017`: KR-46 -> KR-29; assigned overlap 124.103 km2
- `ATLAS_P_R100030_C100024`: KR-48 -> KR-26; assigned overlap 186.256 km2
- `ATLAS_P_R100034_C100023`: KR-47 -> KR-27; assigned overlap 218.259 km2
- `ATLAS_P_R100036_C100018`: KR-44 -> KR-30; assigned overlap 161.756 km2
- `ATLAS_P_R100037_C100017`: KR-44 -> KR-50; assigned overlap 220.694 km2
- `ATLAS_P_R100041_C100016`: KR-41 -> KR-28; assigned overlap 173.651 km2
- `ATLAS_P_R100041_C100017`: KR-41 -> KR-11; assigned overlap 252.392 km2

## Tile naming

- Hard constraint: tile name must intersect the tile and remain inside its country; naming geometry is not clipped to Admin-1 ownership
- Representative pass: units reserve their best free tile in descending population order
- Fill pass: remaining tiles use greatest overlap; ties use population then stable code
- Candidate threshold: any positive overlap; no minimum share
- Naming units: 345
- Uniquely represented units: 278
- Positive-overlap representatives below the legacy 5% reporting threshold: 13
- Dominant-overlap fill tiles: 86
- Population-redistribution fill tiles: 0
- Same-country nearest-boundary fallbacks: 0

## Initial cities and game population

Each real city receives one representative anchor tile with its GeoNames city population.
WorldPop distributes the residual population; UN WPP fixes the exact national total.
Every tile in a represented city-name group inherits the anchor city's display class without duplicating population.
Non-city tiles over 100,000 residents are upgrade-eligible, not automatically cities.

- Capital tiles outlined in yellow: 3
- Metropolis tiles: 12
- City tiles: 63
- Player city-upgrade eligible tiles: 75
- Qualifying real cities without a distinct tile at this resolution: 11
  - `KR-41:ansan`: Ansan (623,256)
  - `KR-41:anyang`: Anyang (595,644)
  - `KR-41:bucheon`: Bucheon (850,731)
  - `KR-41:guri`: Guri (211,720)
  - `KR-41:hanam`: Hanam (328,412)
  - `KR-41:osan`: Osan (238,788)
  - `KR-41:seongnam`: Seongnam (914,832)
  - `KR-41:uiwang`: Uiwang (154,923)
  - `KR-41:yangju`: Yangju (285,930)
  - `KR-41:yeoju`: Yeoju (114,750)
  - `KR-48:gijang`: Gijang (176,388)
- KOR: tile sum 51,600,388; UN WPP target 51,600,388; raw WorldPop weight sum 9,287,531.22
- PRK: tile sum 26,633,691; UN WPP target 26,633,691; raw WorldPop weight sum 19,186,472.57

Naming-unit populations remain internal allocation evidence only:
- GeoNames ADM2 populations: 153
- GeoNames populated-place recoveries: 42
- WorldPop naming-unit recoveries: 150

## Boundary tiles

- `ATLAS_P_R100029_C100019` -> `KR-46`; intersects KR-46, KR-48
- `ATLAS_P_R100030_C100016` -> `KR-46`; intersects KR-45, KR-46
- `ATLAS_P_R100030_C100017` -> `KR-29`; intersects KR-29, KR-46
- `ATLAS_P_R100030_C100018` -> `KR-46`; intersects KR-45, KR-46
- `ATLAS_P_R100030_C100019` -> `KR-46`; intersects KR-46, KR-48
- `ATLAS_P_R100030_C100020` -> `KR-48`; intersects KR-46, KR-48
- `ATLAS_P_R100030_C100024` -> `KR-26`; intersects KR-26, KR-48
- `ATLAS_P_R100031_C100015` -> `KR-45`; intersects KR-45, KR-46
- `ATLAS_P_R100031_C100016` -> `KR-46`; intersects KR-45, KR-46
- `ATLAS_P_R100031_C100017` -> `KR-45`; intersects KR-45, KR-46
- `ATLAS_P_R100031_C100018` -> `KR-45`; intersects KR-45, KR-46
- `ATLAS_P_R100031_C100019` -> `KR-48`; intersects KR-45, KR-46, KR-48
- `ATLAS_P_R100031_C100024` -> `KR-48`; intersects KR-26, KR-31, KR-48
- `ATLAS_P_R100032_C100019` -> `KR-45`; intersects KR-45, KR-48
- `ATLAS_P_R100032_C100020` -> `KR-48`; intersects KR-45, KR-48
- `ATLAS_P_R100032_C100021` -> `KR-48`; intersects KR-47, KR-48
- `ATLAS_P_R100032_C100022` -> `KR-48`; intersects KR-47, KR-48
- `ATLAS_P_R100032_C100023` -> `KR-47`; intersects KR-47, KR-48
- `ATLAS_P_R100032_C100024` -> `KR-47`; intersects KR-31, KR-47, KR-48
- `ATLAS_P_R100032_C100025` -> `KR-31`; intersects KR-31, KR-47
- `ATLAS_P_R100033_C100019` -> `KR-45`; intersects KR-45, KR-48
- `ATLAS_P_R100033_C100020` -> `KR-48`; intersects KR-45, KR-47, KR-48
- `ATLAS_P_R100033_C100021` -> `KR-47`; intersects KR-47, KR-48
- `ATLAS_P_R100033_C100022` -> `KR-47`; intersects KR-27, KR-47
- `ATLAS_P_R100033_C100023` -> `KR-47`; intersects KR-27, KR-47
- `ATLAS_P_R100033_C100024` -> `KR-47`; intersects KR-31, KR-47
- `ATLAS_P_R100034_C100016` -> `KR-45`; intersects KR-44, KR-45
- `ATLAS_P_R100034_C100017` -> `KR-45`; intersects KR-44, KR-45
- `ATLAS_P_R100034_C100018` -> `KR-45`; intersects KR-44, KR-45
- `ATLAS_P_R100034_C100019` -> `KR-45`; intersects KR-43, KR-44, KR-45
- `ATLAS_P_R100034_C100020` -> `KR-43`; intersects KR-43, KR-45, KR-47
- `ATLAS_P_R100034_C100022` -> `KR-47`; intersects KR-27, KR-47
- `ATLAS_P_R100034_C100023` -> `KR-27`; intersects KR-27, KR-47
- `ATLAS_P_R100035_C100017` -> `KR-44`; intersects KR-44, KR-45
- `ATLAS_P_R100035_C100018` -> `KR-44`; intersects KR-30, KR-43, KR-44, KR-45
- `ATLAS_P_R100035_C100019` -> `KR-43`; intersects KR-43, KR-44
- `ATLAS_P_R100035_C100020` -> `KR-47`; intersects KR-43, KR-47
- `ATLAS_P_R100036_C100018` -> `KR-30`; intersects KR-30, KR-43, KR-44, KR-50
- `ATLAS_P_R100036_C100019` -> `KR-43`; intersects KR-30, KR-43, KR-44
- `ATLAS_P_R100036_C100020` -> `KR-43`; intersects KR-43, KR-47
- `ATLAS_P_R100037_C100017` -> `KR-50`; intersects KR-43, KR-44, KR-50
- `ATLAS_P_R100037_C100018` -> `KR-43`; intersects KR-43, KR-44, KR-50
- `ATLAS_P_R100037_C100019` -> `KR-43`; intersects KR-43, KR-47
- `ATLAS_P_R100037_C100020` -> `KR-47`; intersects KR-43, KR-47
- `ATLAS_P_R100037_C100024` -> `KR-47`; intersects KR-42, KR-47
- `ATLAS_P_R100038_C100017` -> `KR-44`; intersects KR-41, KR-44
- `ATLAS_P_R100038_C100018` -> `KR-44`; intersects KR-41, KR-43, KR-44
- `ATLAS_P_R100038_C100021` -> `KR-43`; intersects KR-43, KR-47
- `ATLAS_P_R100038_C100022` -> `KR-47`; intersects KR-43, KR-47
- `ATLAS_P_R100038_C100024` -> `KR-47`; intersects KR-42, KR-47
- `ATLAS_P_R100038_C100025` -> `KR-42`; intersects KR-42, KR-47
- `ATLAS_P_R100039_C100016` -> `KR-41`; intersects KR-41, KR-44
- `ATLAS_P_R100039_C100017` -> `KR-41`; intersects KR-41, KR-44
- `ATLAS_P_R100039_C100018` -> `KR-41`; intersects KR-41, KR-43
- `ATLAS_P_R100039_C100019` -> `KR-43`; intersects KR-41, KR-42, KR-43
- `ATLAS_P_R100039_C100020` -> `KR-43`; intersects KR-42, KR-43
- `ATLAS_P_R100039_C100021` -> `KR-43`; intersects KR-42, KR-43
- `ATLAS_P_R100039_C100022` -> `KR-42`; intersects KR-42, KR-43, KR-47
- `ATLAS_P_R100039_C100023` -> `KR-47`; intersects KR-42, KR-47
- `ATLAS_P_R100039_C100024` -> `KR-42`; intersects KR-42, KR-47
- `ATLAS_P_R100040_C100019` -> `KR-41`; intersects KR-41, KR-42
- `ATLAS_P_R100040_C100020` -> `KR-42`; intersects KR-41, KR-42, KR-43
- `ATLAS_P_R100040_C100021` -> `KR-42`; intersects KR-42, KR-43
- `ATLAS_P_R100040_C100022` -> `KR-42`; intersects KR-42, KR-43
- `ATLAS_P_R100041_C100016` -> `KR-28`; intersects KR-11, KR-28, KR-41
- `ATLAS_P_R100041_C100017` -> `KR-11`; intersects KR-11, KR-41
- `ATLAS_P_R100041_C100019` -> `KR-41`; intersects KR-41, KR-42
- `ATLAS_P_R100041_C100020` -> `KR-42`; intersects KR-41, KR-42
- `ATLAS_P_R100042_C100016` -> `KR-41`; intersects KP-06, KR-28, KR-41
- `ATLAS_P_R100042_C100017` -> `KR-41`; intersects KR-11, KR-41
- `ATLAS_P_R100042_C100018` -> `KR-41`; intersects KR-11, KR-41
- `ATLAS_P_R100042_C100019` -> `KR-41`; intersects KR-41, KR-42
- `ATLAS_P_R100043_C100015` -> `KP-06`; intersects KP-05, KP-06, KR-41
- `ATLAS_P_R100043_C100016` -> `KR-41`; intersects KP-06, KR-41
- `ATLAS_P_R100043_C100019` -> `KR-42`; intersects KR-41, KR-42
- `ATLAS_P_R100044_C100014` -> `KP-05`; intersects KP-05, KP-06
- `ATLAS_P_R100044_C100015` -> `KP-05`; intersects KP-05, KP-06
- `ATLAS_P_R100044_C100017` -> `KR-41`; intersects KP-06, KP-07, KR-41, KR-42
- `ATLAS_P_R100044_C100018` -> `KR-41`; intersects KR-41, KR-42
- `ATLAS_P_R100044_C100019` -> `KR-42`; intersects KR-41, KR-42
- `ATLAS_P_R100045_C100013` -> `KP-06`; intersects KP-05, KP-06
- `ATLAS_P_R100045_C100014` -> `KP-06`; intersects KP-05, KP-06
- `ATLAS_P_R100045_C100015` -> `KP-06`; intersects KP-05, KP-06
- `ATLAS_P_R100045_C100016` -> `KP-06`; intersects KP-06, KP-07
- `ATLAS_P_R100045_C100017` -> `KP-07`; intersects KP-07, KR-41, KR-42
- `ATLAS_P_R100045_C100018` -> `KR-42`; intersects KP-07, KR-42
- `ATLAS_P_R100045_C100019` -> `KR-42`; intersects KP-07, KR-42
- `ATLAS_P_R100045_C100020` -> `KR-42`; intersects KP-07, KR-42
- `ATLAS_P_R100045_C100021` -> `KR-42`; intersects KP-07, KR-42
- `ATLAS_P_R100046_C100013` -> `KP-06`; intersects KP-05, KP-06
- `ATLAS_P_R100046_C100016` -> `KP-06`; intersects KP-06, KP-07
- `ATLAS_P_R100046_C100021` -> `KP-07`; intersects KP-07, KR-42
- `ATLAS_P_R100046_C100022` -> `KR-42`; intersects KP-07, KR-42
- `ATLAS_P_R100047_C100011` -> `KP-05`; intersects KP-05, KP-14
- `ATLAS_P_R100047_C100012` -> `KP-05`; intersects KP-05, KP-06, KP-14
- `ATLAS_P_R100047_C100016` -> `KP-06`; intersects KP-06, KP-07
- `ATLAS_P_R100047_C100021` -> `KP-07`; intersects KP-07, KR-42
- `ATLAS_P_R100048_C100012` -> `KP-14`; intersects KP-02, KP-06, KP-14
- `ATLAS_P_R100048_C100013` -> `KP-06`; intersects KP-01, KP-06, KP-14
- `ATLAS_P_R100048_C100014` -> `KP-06`; intersects KP-01, KP-06
- `ATLAS_P_R100048_C100015` -> `KP-06`; intersects KP-01, KP-02, KP-06
- `ATLAS_P_R100048_C100016` -> `KP-06`; intersects KP-02, KP-06
- `ATLAS_P_R100048_C100017` -> `KP-06`; intersects KP-06, KP-07
- `ATLAS_P_R100049_C100012` -> `KP-02`; intersects KP-01, KP-02, KP-14
- `ATLAS_P_R100049_C100013` -> `KP-01`; intersects KP-01, KP-06
- `ATLAS_P_R100049_C100014` -> `KP-01`; intersects KP-01, KP-02, KP-06
- `ATLAS_P_R100049_C100015` -> `KP-02`; intersects KP-01, KP-02, KP-06
- `ATLAS_P_R100049_C100016` -> `KP-06`; intersects KP-02, KP-06
- `ATLAS_P_R100049_C100017` -> `KP-07`; intersects KP-02, KP-06, KP-07, KP-08
- `ATLAS_P_R100050_C100013` -> `KP-02`; intersects KP-01, KP-02
- `ATLAS_P_R100050_C100014` -> `KP-02`; intersects KP-01, KP-02
- `ATLAS_P_R100050_C100016` -> `KP-02`; intersects KP-02, KP-08
- `ATLAS_P_R100050_C100017` -> `KP-08`; intersects KP-02, KP-07, KP-08
- `ATLAS_P_R100050_C100018` -> `KP-07`; intersects KP-07, KP-08
- `ATLAS_P_R100051_C100012` -> `KP-02`; intersects KP-02, KP-03
- `ATLAS_P_R100051_C100016` -> `KP-08`; intersects KP-02, KP-08
- `ATLAS_P_R100051_C100017` -> `KP-08`; intersects KP-07, KP-08
- `ATLAS_P_R100051_C100018` -> `KP-08`; intersects KP-07, KP-08
- `ATLAS_P_R100052_C100013` -> `KP-03`; intersects KP-02, KP-03
- `ATLAS_P_R100052_C100014` -> `KP-02`; intersects KP-02, KP-03
- `ATLAS_P_R100052_C100016` -> `KP-02`; intersects KP-02, KP-08
- `ATLAS_P_R100052_C100017` -> `KP-08`; intersects KP-02, KP-08
- `ATLAS_P_R100053_C100014` -> `KP-03`; intersects KP-02, KP-03
- `ATLAS_P_R100053_C100015` -> `KP-02`; intersects KP-02, KP-03, KP-04
- `ATLAS_P_R100053_C100016` -> `KP-02`; intersects KP-02, KP-08
- `ATLAS_P_R100053_C100017` -> `KP-08`; intersects KP-02, KP-08
- `ATLAS_P_R100054_C100014` -> `KP-03`; intersects KP-03, KP-04
- `ATLAS_P_R100054_C100015` -> `KP-04`; intersects KP-03, KP-04
- `ATLAS_P_R100054_C100016` -> `KP-04`; intersects KP-02, KP-04
- `ATLAS_P_R100054_C100017` -> `KP-02`; intersects KP-02, KP-04
- `ATLAS_P_R100054_C100018` -> `KP-08`; intersects KP-02, KP-08
- `ATLAS_P_R100055_C100012` -> `KP-03`; intersects KP-03, KP-04
- `ATLAS_P_R100055_C100013` -> `KP-04`; intersects KP-03, KP-04
- `ATLAS_P_R100055_C100016` -> `KP-04`; intersects KP-02, KP-04
- `ATLAS_P_R100055_C100017` -> `KP-08`; intersects KP-02, KP-04, KP-08
- `ATLAS_P_R100055_C100019` -> `KP-08`; intersects KP-08, KP-10
- `ATLAS_P_R100056_C100013` -> `KP-04`; intersects KP-03, KP-04
- `ATLAS_P_R100056_C100017` -> `KP-04`; intersects KP-04, KP-08
- `ATLAS_P_R100056_C100018` -> `KP-08`; intersects KP-04, KP-08
- `ATLAS_P_R100056_C100020` -> `KP-10`; intersects KP-08, KP-10
- `ATLAS_P_R100056_C100021` -> `KP-08`; intersects KP-08, KP-10
- `ATLAS_P_R100056_C100024` -> `KP-08`; intersects KP-08, KP-09
- `ATLAS_P_R100057_C100018` -> `KP-08`; intersects KP-04, KP-08
- `ATLAS_P_R100057_C100019` -> `KP-10`; intersects KP-08, KP-10
- `ATLAS_P_R100057_C100021` -> `KP-10`; intersects KP-08, KP-10
- `ATLAS_P_R100057_C100023` -> `KP-08`; intersects KP-08, KP-09
- `ATLAS_P_R100058_C100019` -> `KP-08`; intersects KP-04, KP-08, KP-10
- `ATLAS_P_R100058_C100020` -> `KP-10`; intersects KP-08, KP-10
- `ATLAS_P_R100058_C100022` -> `KP-08`; intersects KP-08, KP-10
- `ATLAS_P_R100058_C100023` -> `KP-08`; intersects KP-08, KP-09
- `ATLAS_P_R100058_C100024` -> `KP-09`; intersects KP-08, KP-09
- `ATLAS_P_R100059_C100017` -> `KP-04`; intersects KP-04, KP-10
- `ATLAS_P_R100059_C100018` -> `KP-10`; intersects KP-04, KP-10
- `ATLAS_P_R100059_C100019` -> `KP-10`; intersects KP-08, KP-10
- `ATLAS_P_R100059_C100022` -> `KP-10`; intersects KP-08, KP-10
- `ATLAS_P_R100059_C100023` -> `KP-10`; intersects KP-08, KP-09, KP-10
- `ATLAS_P_R100060_C100017` -> `KP-04`; intersects KP-04, KP-10
- `ATLAS_P_R100060_C100018` -> `KP-10`; intersects KP-04, KP-10
- `ATLAS_P_R100060_C100024` -> `KP-09`; intersects KP-09, KP-10
- `ATLAS_P_R100061_C100017` -> `KP-10`; intersects KP-04, KP-10
- `ATLAS_P_R100061_C100023` -> `KP-10`; intersects KP-09, KP-10
- `ATLAS_P_R100062_C100023` -> `KP-10`; intersects KP-09, KP-10
- `ATLAS_P_R100063_C100023` -> `KP-09`; intersects KP-09, KP-10

## Manual overrides

- None
