# Korea CGAZ hierarchy consistency audit

Audit date: 2026-07-16 (Asia/Seoul)

Status: **KNOWN FROZEN-SNAPSHOT LIMITATIONS; NO COUNTRY-SPECIFIC PATCH**

## Purpose

This audit separates three questions that must not be conflated:

1. Did Atlas apply its configured greatest-overlap and population-priority
   rules deterministically?
2. Are CGAZ ADM1 and ADM2 geometries internally consistent as a hierarchy?
3. Does the resulting map describe current Korean administrative membership?

For the cases below, the answer is yes to the first question and no to the
second and third. The allocation code is following the pinned geometry; the
geometry does not encode the expected hierarchy.

## Sources and method

- Canonical boundary snapshot: geoBoundaries CGAZ 6.0.0, commit
  `1289e40e366c7b320550be1ee0614a9472d572d4`.
- KOR ADM1 represented year in configuration: 2021.
- KOR ADM2 represented year in configuration: 2020.
- Hierarchy test: intersect each ADM2 polygon with every same-country ADM1 and
  select the greatest positive area.
- Naming evidence: configured GeoNames KOR dump and WorldPop fallback.
- Generated evidence: `data/processed/Atlas_Korea.gpkg` and
  `exports/Atlas_Korea_Tiles.csv`.

No geometry or assignment was modified during this audit.

## Finding 1: Dalseong-gun

Dalseong-gun has belonged to Daegu since 1 March 1995. This predates both CGAZ
represented years, so the conflict cannot be explained as a recent Gunwi-style
transfer.

| CGAZ ADM1 overlap | Share of Dalseong ADM2 |
| --- | ---: |
| North Gyeongsang | 98.707% |
| Daegu | 1.293% |

The generic spatial-parent rule therefore creates `KR-47:dalseong`. Its naming
population is 264,680, fourth highest among units classified under North
Gyeongsang, so it secures a representative tile early.

On tile `ATLAS_P_R100033_C100022`, the naming overlaps are:

| Naming unit | Overlap |
| --- | ---: |
| Dalseong | 280.568 km2 |
| Cheongdo | 58.536 km2 |
| Goryeong | 29.712 km2 |
| Gyeongsan | 3.659 km2 |
| Chilgok | 1.353 km2 |

Thus population priority is not the sole cause: Dalseong is also the
greatest-overlap naming polygon on that tile. The underlying defect is that the
pinned Daegu ADM1 geometry excludes almost all of the Dalseong ADM2 polygon.

Official reference:

- Dalseong-gun history, recording its March 1995 incorporation into Daegu:
  https://www.dalseong.daegu.kr/eng/index.do?menu_id=00003264

## Finding 2: Gwangju autonomous districts

Gwangsan-gu, Seo-gu, Nam-gu, Dong-gu and Buk-gu are autonomous districts of
Gwangju Metropolitan City, not independent Jeonnam cities or counties. CGAZ
stores autonomous districts as ADM2 polygons, which is valid, but several of
those polygons do not spatially fit the CGAZ Gwangju ADM1 polygon.

Measured examples:

| ADM2 unit | South Jeolla overlap | Gwangju overlap | Working parent |
| --- | ---: | ---: | --- |
| Gwangsan-gu | 98.597% | 1.403% | South Jeolla |
| Gwangju Seo-gu | effectively all | negligible | South Jeolla |
| Gwangju Buk-gu | 27.443% | 72.557% | Gwangju |

The builder aggregates metropolitan districts only after establishing their
working ADM1 parent. Gwangsan-gu and Seo-gu are first assigned to South Jeolla,
so they escape the `KR-29` Gwangju aggregation and become independent Jeonnam
naming candidates.

Their allocation populations are:

| Jeonnam-classified candidate | Population evidence |
| --- | ---: |
| Gwangsan-gu | 392,653 |
| Seo-gu | 335,853 |
| Suncheon | 276,375 |
| Yeosu | 268,823 |
| Mokpo | 210,806 |

They therefore rank first and second in the population-ordered representative
pass. This confirms that the naming logic explains which bad candidates win;
it does not explain why they became Jeonnam candidates.

The Seo-gu representative illustrates the interaction between the data defect
and the universal naming rule:

| Unit intersecting the tile | Overlap |
| --- | ---: |
| Naju | 411.484 km2 |
| Hwasun | 105.684 km2 |
| Yeongam | 54.641 km2 |
| Nam-gu | 18.223 km2 |
| Gwangsan-gu | 13.838 km2 |
| Seo-gu | 1.290 km2 |

Seo-gu receives the tile because every positive overlap is eligible and larger
populations reserve representatives first. That behavior is the established
global naming contract. Changing it only for Gwangju would be a prohibited
country-specific exception.

Official reference:

- Gwangju population by its five autonomous districts:
  https://www.gwangju.go.kr/eng/contentsView.do?pageId=eng25

## Finding 3: Gwangju city anchor

GeoNames city `1841811` has population 1,401,235 and exceeds the global
metropolis threshold of 1,000,000. It nevertheless does not become an anchor.

- The GeoNames point is inside the CGAZ Dong-gu polygon.
- That Dong-gu polygon is classified under South Jeolla rather than Gwangju.
- The surviving `KR-29:gwangju` aggregate contains only the Buk-gu source
  geometry.
- The city point is about 1,106 metres outside that aggregate.

The matcher requires both point containment and identical normalized city/unit
name. Dong-gu satisfies containment but not the name; `KR-29:gwangju` satisfies
the name but not containment. Consequently the generated Gwangju tile has
`is_initial_city=false`, no `city_class`, and `map_class=admin`. Its 1,713,444
game population is residual WPP/WorldPop allocation and is intentionally not
used to infer initial city status.

The strict matcher is necessary: weakening it to containment-only or nearest
matching previously attached an unrelated Masan record to Seo-gu. The safe
correction is coherent hierarchy data, not permissive matching.

## Finding 4: missing Yeonggwang-gun

The pinned CGAZ KOR ADM2 layer contains no Yeonggwang-gun polygon. GeoNames has
a Yeonggwang populated-place record with population 51,688, but Atlas does not
invent an administrative polygon from a point.

Yeonggwang therefore never enters the naming-unit competition. It did not lose
to Gwangsan-gu or Seo-gu on population; it was absent before allocation began.

## Consequences in the current build

- Daegu has one represented Admin1 tile, while Dalseong appears as a North
  Gyeongsang naming unit.
- Gwangsan-gu and Seo-gu consume two of the 15 Jeonnam-owned tile names.
- Several actual Jeonnam units remain unrepresented at this grid resolution;
  Mokpo, Gangjin, Wando, Hampyeong, Jindo, Gokseong and Gurye are among them.
- Gwangju is displayed as an ordinary administrative tile instead of a
  metropolis because its valid GeoNames city cannot anchor to the inconsistent
  naming geometry.
- Geometry, topology, deterministic allocation and national population checks
  can still pass. Those checks prove internal reproducibility, not semantic
  hierarchy accuracy.

## Root-cause classification

| Component | Assessment |
| --- | --- |
| CGAZ KOR ADM1/ADM2 geometry | Primary cause: hierarchy and completeness defects |
| Greatest-overlap Admin1 rule | Correctly applies the pinned geometry |
| Population-priority naming rule | Correctly selects among the resulting candidates, but amplifies bad parentage |
| Strict city-anchor matcher | Correctly refuses ambiguous or unrelated matches |
| Existing validation | Gap: does not yet reject semantic parent contradictions or missing expected units |

## Long-term decision

Atlas accepts these as documented limitations of the frozen global snapshot.
It will not add KOR-only parent maps, manual ownership changes, edited polygons,
missing-unit synthesis or permissive city-anchor fallbacks.

The long-term compatible approach is:

1. preserve one deterministic worldwide allocation algorithm;
2. audit ADM1/ADM2 hierarchy coherence and completeness with country-neutral
   checks;
3. treat contradictions as explicit data-quality evidence rather than silently
   repairing them;
4. correct production geometry only through a generic source adapter with
   reliable parent identifiers or a migration of the complete global snapshot;
5. rerun all countries and global regression cases after such a migration.

The current Korea build is therefore a valid reproducible CGAZ baseline, but
not a claim that every displayed KOR administrative relationship matches the
modern official hierarchy.
