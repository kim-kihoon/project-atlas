# PRK boundary source update - 2026-07-16

> Superseding decision: the NGII/OSM attempt below remains evidence, but Atlas
> now uses pinned CGAZ 6.0.0 for PRK ADM0/ADM1/ADM2. No PRK-only geometry patch
> will be applied. See `reports/global_snapshot_decision.md`.

Status: **source acquisition incomplete; release gate remains FAIL**

This update records work performed after the full Korea audit to locate one
compatible modern DPRK ADM1/ADM2 hierarchy. No manual boundary or ownership
override was introduced.

## NGII 2024 public-data files

The National Geographic Information Institute publishes matching 2024-08-08
ADM1 and ADM2 CSV tables through the Korean public-data portal under Korea Open
Government License Type 1.

| File | Rows | Useful evidence | Geometry verdict |
| --- | ---: | --- | --- |
| `ngii_prk_admin1_20240808.csv` | 12 | Pyongyang, Kaesong, Nampo and nine provinces | Unusable for build |
| `ngii_prk_admin2_20240808.csv` | 218 | Official ADM2 names and UFID values, including Sangwon | Unusable for build |

The `SDE.ST_GEOMETRY` values contain geometry type, envelope, area/perimeter
summaries and a process-local string such as `oracle.sql.BLOB@...`. Polygon
vertices are not present. Reconstructing a boundary from the envelope would be
fabrication and is forbidden by the project rules.

Both originals are CP949 encoded and are preserved without conversion. Their
row counts and BLOB-reference structure were verified using that encoding.
`.gitattributes` marks this source directory `-text` so Git cannot normalize the
original byte stream.

The ADM1 table is also not the complete 2022 13-unit hierarchy: it omits Rason.
It is retained as official evidence, not configured as a boundary source.

## OpenStreetMap screening

Read-only Nominatim and Overpass checks against DPRK country relation `192734`
returned:

- 13 ADM1 relations with ISO 3166-2 codes, including `KP-13` Rason, `KP-14`
  Nampo and `KP-15` Kaesong;
- 201 ADM2 relations inside the country relation;
- Sangwon County relation `3860474`, displayed under North Hwanghae;
- the expected remaining province and city codes `KP-01` through `KP-10`.

This is the first screened candidate in the audit that satisfies both modern
ADM1 completeness and the Sangwon hierarchy at the metadata level. It is also
globally extensible in principle.

After full Overpass geometry requests timed out, a pinned Geofabrik
`north-korea-260710.osm.pbf` extract was downloaded. Its published MD5 matches,
and its SHA-256 is recorded in `data/source/README.md`. GDAL/QGIS 3.44.12 read
the extract and produced an EPSG:5179 candidate GeoPackage.
PBF files are covered by Git LFS in `.gitattributes`.

| Polygon check | Result |
| --- | --- |
| ADM1 polygons | 12 valid features |
| ADM2 polygons | 195 valid features |
| Sangwon parent by point-on-surface | North Hwanghae, PASS |
| ADM2 polygons without an available ADM1 parent | 23, FAIL |
| North Pyongan `KP-03` | Relation tags/bounds exist; member geometry absent, FAIL |

The candidate is therefore rejected as a current geometry input. The live OSM
count of 13 does not imply 13 usable polygons. OpenStreetMap's ODbL attribution
and derived-database obligations would also require review before any future
adoption and game distribution.

GDAL also emitted four non-closed-ring warnings while reading ADM2 relations.
The written GeoPackage geometries report valid after driver handling, but the
source warnings remain an additional topology-review requirement.

## Release impact

No config, ownership assignment or generated map was changed from the last
audited build. The current Natural Earth/geoBoundaries mixture still has 11 PRK
ADM1 units and still assigns Sangwon to Pyongyang after clipping. Consequently:

- structural Korea validation remains PASS;
- modern administrative-reference validation remains FAIL;
- the Korea map remains NOT YET PASS for release.

The Windows validation launcher was rerun after this source audit. All
structural checks completed, and the nonzero exit remained limited to the two
expected dated gates: missing `KP-14`/`KP-15`, and Sangwon assigned to `KP-01`
instead of `KP-06`.

## Next acceptance steps

1. Obtain a corrected pinned OSM extract or another redistributable polygon
   snapshot with complete ADM1 and ADM2 geometries.
2. Record source timestamp, original filename, checksum and license terms.
3. Verify 13 ADM1 units, 201-or-current ADM2 membership, Sangwon under North
   Hwanghae, polygon validity, non-overlap, coverage and ADM2-within-ADM1
   containment.
4. Only then configure one compatible PRK hierarchy and rebuild all greatest-
   overlap ownership, naming, borders and capital outlines.
5. Run the full build, release validator, Unreal exports and visual inspection.

Until all five steps pass, Atlas must not synthesize special-city boundaries,
mix live OSM geometry with stale parents, or suppress the dated validation
failures.
