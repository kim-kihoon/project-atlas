# Korea data-quality findings

Updated: 2026-07-16 (Asia/Seoul)

## `Seo` label investigation

The displayed `Seo` was not evidence of a real independent city with that name.
It came from CGAZ ADM2 source records named `Seo-gu [West District]`. The old
display formatter removed `-gu`, producing the misleading label `Seo`.

One affected tile also became a city because GeoNames record `1841246` was
matched to it. That record contains an internally suspicious combination:

- name: `Masan` / `Masan-ni`;
- coordinates: 35.12725, 126.83149, inside the relevant Seo-gu polygon;
- population: 434,371, resembling the former Masan city population.

The prior matcher accepted any qualifying city point contained by a naming
polygon, even when city and unit names differed. This incorrectly made the
Seo-gu tile a Masan city anchor.

Corrections:

1. preserve `-gu` in displayed names, so the source is shown as `Seo-gu`;
2. require both point containment and matching normalized city/unit names;
3. remove nearest-only city-to-unit fallback;
4. leave unmatched city records as source evidence rather than initial cities.

Final result: the affected tile is labeled `Seo-gu`, has `map_class=admin`, no
`city_class`, no initial-city flag and no GeoNames city population anchor. Its
game population is assigned by the ordinary WPP/WorldPop residual model.

## Admin-1 representation restoration

The repository contract guarantees every feasible official Admin-1 one
positive-overlap same-country representative tile without removing another
official area's last tile. The temporary strict-only build violated that rule
and made several metropolitan boundaries disappear.

The restored build has all 17 KOR and all 11 configured PRK Admin-1 units
represented. Seven KOR tiles use the representation-floor method; PRK needs no
rescue tiles. Seoul, Busan, Daegu, Incheon, Gwangju, Daejeon, Ulsan and Sejong
each own at least one tile, so their topology-derived administrative outlines
are present again.

## Geometry persistence hardening

Clipping simplified naming polygons to ADM1 can return geometry collections or
line-only contact. The builder now extracts positive-area polygon components,
normalizes them to multipolygons and excludes zero-area contact. This generic
rule prevents silent feature loss in any future country.

## CGAZ ADM1/ADM2 hierarchy conflicts

The pinned CGAZ 6.0.0 release is globally consistent as a provider snapshot,
but its KOR ADM1 and ADM2 geometries are not a reliable parent hierarchy in
several metropolitan areas.

- Dalseong-gun is officially part of Daegu, but its CGAZ ADM2 polygon overlaps
  North Gyeongsang by 98.707% and Daegu by only 1.293%. The generic spatial
  parent rule therefore classifies it as `KR-47:dalseong`.
- Gwangsan-gu and Gwangju Seo-gu are autonomous districts of Gwangju, but their
  CGAZ polygons are assigned primarily to South Jeolla. They consequently
  escape the configured Gwangju aggregation and compete as independent Jeonnam
  naming units.
- Their naming populations, 392,653 for Gwangsan-gu and 335,853 for Seo-gu,
  place them first and second among the resulting Jeonnam candidates. The
  population-priority representative pass therefore gives each a tile before
  lower-population counties.
- The Seo-gu representative has only 1.290 km2 of Seo-gu overlap while Naju
  overlaps the same tile by 411.484 km2. This is permitted by the established
  rule that any positive overlap is eligible during the population-ordered
  representative pass; the surprising result is caused by bad parentage, not
  by a Korea-specific naming branch.
- Yeonggwang-gun is absent from the CGAZ KOR ADM2 layer, so it cannot enter the
  naming competition at all. Its GeoNames populated-place record is evidence,
  not a substitute polygon.

## Gwangju metropolis classification

GeoNames record `1841811` represents Gwangju as a qualifying city with
population 1,401,235, above the global one-million metropolis threshold. The
point falls in the CGAZ Dong-gu polygon, which the spatial hierarchy assigns to
South Jeolla. The surviving aggregated `KR-29:gwangju` geometry contains only
Buk-gu source geometry and lies about 1.1 km from the city point.

Because a city anchor requires both matching normalized name and point
containment, neither geometry is compatible: Dong-gu contains the point but
does not have the Gwangju unit name, while `KR-29:gwangju` has the name but does
not contain the point. The Gwangju tile therefore receives WPP/WorldPop residual
population, not the GeoNames city anchor, and remains `map_class=admin`.

This is a source-hierarchy failure amplified by correct generic matching. A
nearest or name-only fallback would also recreate the earlier Masan/Seo-gu
false-anchor defect and is therefore not an acceptable repair.

## Long-term decision

Atlas will not add KOR-only parent mappings, ownership overrides, boundary
edits or missing-county synthesis for these findings. The current output is a
reproducible frozen-snapshot baseline, not a claim of exact modern Korean
administrative semantics.

The globally safe response is to report ADM1/ADM2 contradictions and missing
units, then correct them only through a country-neutral source adapter or a
full worldwide snapshot migration. Detailed measurements and consequences are
in `reports/korea_cgaz_hierarchy_consistency_audit.md`.
