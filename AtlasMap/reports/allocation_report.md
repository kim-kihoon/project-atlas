# Atlas Korea tile allocation report

Generated: 2026-07-15T00:05:14.533170+00:00

- Orientation: `pointy_top`
- Final tiles: **160**
- Target tile area: 605.21 km2

- Country selection: dominant overlap among nearby countries and ocean; no fixed national total
- Assignment policy: dominant administrative overlap with configured minimum representation
- Target counts are advisory, not hard constraints

| Code | Admin area | Target | Minimum | Actual | Difference |
| --- | --- | ---: | ---: | ---: | ---: |
| KR-11 | 서울 / Seoul | 1 | 1 | 1 | 0 |
| KR-26 | 부산 / Busan | 1 | 1 | 1 | 0 |
| KR-27 | 대구 / Daegu | 3 | 1 | 1 | -2 |
| KR-28 | 인천 / Incheon | 2 | 1 | 1 | -1 |
| KR-29 | 광주 / Gwangju | 1 | 1 | 1 | 0 |
| KR-30 | 대전 / Daejeon | 1 | 1 | 1 | 0 |
| KR-31 | 울산 / Ulsan | 2 | 1 | 1 | -1 |
| KR-50 | 세종 / Sejong | 1 | 1 | 1 | 0 |
| KR-41 | 경기 / Gyeonggi | 17 | 1 | 16 | -1 |
| KR-42 | 강원 / Gangwon | 28 | 1 | 33 | 5 |
| KR-43 | 충북 / Chungbuk | 12 | 1 | 12 | 0 |
| KR-44 | 충남 / Chungnam | 14 | 1 | 11 | -3 |
| KR-45 | 전북 / Jeonbuk | 13 | 1 | 15 | 2 |
| KR-46 | 전남 / Jeonnam | 20 | 1 | 16 | -4 |
| KR-47 | 경북 / Gyeongbuk | 30 | 1 | 30 | 0 |
| KR-48 | 경남 / Gyeongnam | 17 | 1 | 16 | -1 |
| KR-49 | 제주 / Jeju | 3 | 1 | 3 | 0 |

## Minimum-representation exceptions

- `KOR_P_R100030_C100017`: dominant `KR-46` -> required `KR-29`; required overlap 132.92 km2
- `KOR_P_R100030_C100024`: dominant `KR-48` -> required `KR-26`; required overlap 235.65 km2
- `KOR_P_R100034_C100023`: dominant `KR-47` -> required `KR-27`; required overlap 221.49 km2
- `KOR_P_R100036_C100018`: dominant `KR-44` -> required `KR-30`; required overlap 162.54 km2
- `KOR_P_R100037_C100017`: dominant `KR-44` -> required `KR-50`; required overlap 218.87 km2
- `KOR_P_R100041_C100016`: dominant `KR-41` -> required `KR-28`; required overlap 204.61 km2
- `KOR_P_R100041_C100017`: dominant `KR-41` -> required `KR-11`; required overlap 264.79 km2

## Tile naming

- Default: city/county with the largest hex overlap
- Minimum overlap share for a population exception: 5%
- Exception: a missing higher-population unit may take one overlapping tile only when the current unit keeps at least one other tile
- Naming units: 161
- Population-representation exceptions: 5

- `KOR_P_R100031_C100023`: `밀양` (108,621) -> `김해` (531,966); overlap 222.44 km2
- `KOR_P_R100035_C100019`: `영동` (43,680) -> `옥천` (56,634); overlap 226.47 km2
- `KOR_P_R100038_C100022`: `단양` (37,320) -> `예천` (58,081); overlap 150.88 km2
- `KOR_P_R100041_C100024`: `삼척` (72,368) -> `동해` (103,115); overlap 96.08 km2
- `KOR_P_R100044_C100022`: `인제` (34,120) -> `속초` (89,461); overlap 51.54 km2

## Population-based city classes

City class changes tile fill only; administrative ownership and borders remain separate.

- Capital markers: 1
- Metropolis markers (1,000,000+): 11
- City markers (500,000-999,999): 12

## Boundary tiles

- `KOR_P_R100029_C100019` -> `KR-46`; intersects KR-46, KR-48
- `KOR_P_R100030_C100016` -> `KR-46`; intersects KR-45, KR-46
- `KOR_P_R100030_C100017` -> `KR-29`; intersects KR-29, KR-46
- `KOR_P_R100030_C100018` -> `KR-46`; intersects KR-45, KR-46
- `KOR_P_R100030_C100019` -> `KR-46`; intersects KR-46, KR-48
- `KOR_P_R100030_C100020` -> `KR-48`; intersects KR-46, KR-48
- `KOR_P_R100030_C100024` -> `KR-26`; intersects KR-26, KR-48
- `KOR_P_R100031_C100015` -> `KR-45`; intersects KR-45, KR-46
- `KOR_P_R100031_C100016` -> `KR-46`; intersects KR-45, KR-46
- `KOR_P_R100031_C100017` -> `KR-45`; intersects KR-45, KR-46
- `KOR_P_R100031_C100018` -> `KR-45`; intersects KR-45, KR-46
- `KOR_P_R100031_C100019` -> `KR-48`; intersects KR-45, KR-46, KR-48
- `KOR_P_R100031_C100024` -> `KR-48`; intersects KR-26, KR-31, KR-48
- `KOR_P_R100032_C100019` -> `KR-45`; intersects KR-45, KR-48
- `KOR_P_R100032_C100020` -> `KR-48`; intersects KR-45, KR-48
- `KOR_P_R100032_C100021` -> `KR-48`; intersects KR-47, KR-48
- `KOR_P_R100032_C100022` -> `KR-48`; intersects KR-47, KR-48
- `KOR_P_R100032_C100023` -> `KR-47`; intersects KR-47, KR-48
- `KOR_P_R100032_C100024` -> `KR-47`; intersects KR-31, KR-47, KR-48
- `KOR_P_R100032_C100025` -> `KR-31`; intersects KR-31, KR-47
- `KOR_P_R100033_C100019` -> `KR-45`; intersects KR-45, KR-48
- `KOR_P_R100033_C100020` -> `KR-48`; intersects KR-45, KR-47, KR-48
- `KOR_P_R100033_C100021` -> `KR-47`; intersects KR-47, KR-48
- `KOR_P_R100033_C100022` -> `KR-47`; intersects KR-27, KR-47
- `KOR_P_R100033_C100023` -> `KR-47`; intersects KR-27, KR-47
- `KOR_P_R100033_C100024` -> `KR-47`; intersects KR-31, KR-47
- `KOR_P_R100034_C100016` -> `KR-45`; intersects KR-44, KR-45
- `KOR_P_R100034_C100017` -> `KR-45`; intersects KR-44, KR-45
- `KOR_P_R100034_C100018` -> `KR-45`; intersects KR-44, KR-45
- `KOR_P_R100034_C100019` -> `KR-45`; intersects KR-43, KR-44, KR-45
- `KOR_P_R100034_C100020` -> `KR-43`; intersects KR-43, KR-45, KR-47
- `KOR_P_R100034_C100022` -> `KR-47`; intersects KR-27, KR-47
- `KOR_P_R100034_C100023` -> `KR-27`; intersects KR-27, KR-47
- `KOR_P_R100035_C100017` -> `KR-44`; intersects KR-44, KR-45
- `KOR_P_R100035_C100018` -> `KR-44`; intersects KR-30, KR-43, KR-44, KR-45
- `KOR_P_R100035_C100019` -> `KR-43`; intersects KR-43, KR-44
- `KOR_P_R100035_C100020` -> `KR-47`; intersects KR-43, KR-47
- `KOR_P_R100036_C100017` -> `KR-44`; intersects KR-44, KR-50
- `KOR_P_R100036_C100018` -> `KR-30`; intersects KR-30, KR-43, KR-44, KR-50
- `KOR_P_R100036_C100019` -> `KR-43`; intersects KR-30, KR-43, KR-44
- `KOR_P_R100036_C100020` -> `KR-43`; intersects KR-43, KR-47
- `KOR_P_R100037_C100017` -> `KR-50`; intersects KR-43, KR-44, KR-50
- `KOR_P_R100037_C100018` -> `KR-43`; intersects KR-43, KR-44, KR-50
- `KOR_P_R100037_C100019` -> `KR-43`; intersects KR-43, KR-47
- `KOR_P_R100037_C100020` -> `KR-47`; intersects KR-43, KR-47
- `KOR_P_R100037_C100024` -> `KR-47`; intersects KR-42, KR-47
- `KOR_P_R100038_C100017` -> `KR-44`; intersects KR-41, KR-44
- `KOR_P_R100038_C100018` -> `KR-44`; intersects KR-41, KR-43, KR-44
- `KOR_P_R100038_C100021` -> `KR-43`; intersects KR-43, KR-47
- `KOR_P_R100038_C100022` -> `KR-47`; intersects KR-43, KR-47
- `KOR_P_R100038_C100024` -> `KR-47`; intersects KR-42, KR-47
- `KOR_P_R100038_C100025` -> `KR-42`; intersects KR-42, KR-47
- `KOR_P_R100039_C100017` -> `KR-41`; intersects KR-41, KR-44
- `KOR_P_R100039_C100018` -> `KR-41`; intersects KR-41, KR-43
- `KOR_P_R100039_C100019` -> `KR-43`; intersects KR-41, KR-42, KR-43
- `KOR_P_R100039_C100020` -> `KR-43`; intersects KR-42, KR-43
- `KOR_P_R100039_C100021` -> `KR-43`; intersects KR-42, KR-43
- `KOR_P_R100039_C100022` -> `KR-42`; intersects KR-42, KR-43, KR-47
- `KOR_P_R100039_C100023` -> `KR-47`; intersects KR-42, KR-47
- `KOR_P_R100039_C100024` -> `KR-42`; intersects KR-42, KR-47
- `KOR_P_R100040_C100019` -> `KR-41`; intersects KR-41, KR-42
- `KOR_P_R100040_C100020` -> `KR-42`; intersects KR-41, KR-42, KR-43
- `KOR_P_R100040_C100021` -> `KR-42`; intersects KR-42, KR-43
- `KOR_P_R100040_C100022` -> `KR-42`; intersects KR-42, KR-43
- `KOR_P_R100041_C100016` -> `KR-28`; intersects KR-11, KR-28, KR-41
- `KOR_P_R100041_C100017` -> `KR-11`; intersects KR-11, KR-41
- `KOR_P_R100041_C100019` -> `KR-41`; intersects KR-41, KR-42
- `KOR_P_R100041_C100020` -> `KR-42`; intersects KR-41, KR-42
- `KOR_P_R100042_C100016` -> `KR-41`; intersects KR-28, KR-41
- `KOR_P_R100042_C100017` -> `KR-41`; intersects KR-11, KR-41
- `KOR_P_R100042_C100018` -> `KR-41`; intersects KR-11, KR-41
- `KOR_P_R100042_C100019` -> `KR-41`; intersects KR-41, KR-42
- `KOR_P_R100042_C100020` -> `KR-42`; intersects KR-41, KR-42
- `KOR_P_R100043_C100019` -> `KR-42`; intersects KR-41, KR-42
- `KOR_P_R100044_C100017` -> `KR-41`; intersects KR-41, KR-42
- `KOR_P_R100044_C100018` -> `KR-41`; intersects KR-41, KR-42
- `KOR_P_R100044_C100019` -> `KR-42`; intersects KR-41, KR-42

## Manual overrides

- None
