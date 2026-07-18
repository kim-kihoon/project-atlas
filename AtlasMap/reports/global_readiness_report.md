# Atlas global readiness report

Generated: 2026-07-17T15:45:11.889515+00:00

Overall result: **FAIL**

- Blocking failures: 1
- Warnings: 0
- Configured prototype countries: 6

| Check | Result | Detail |
| --- | --- | --- |
| Authoritative global rules document | PASS | GLOBAL_MAP_RULES.md |
| Global boundary candidate evaluation is recorded | PASS | provider=geoBoundaries CGAZ; status=accepted; report=reports/global_boundary_candidate_report.md |
| One frozen global ADM0/ADM1/ADM2 snapshot | PASS | missing=[]; candidate=geoBoundaries CGAZ; candidate_status=accepted |
| Canonical snapshot requires all hierarchy levels | PASS | levels=['ADM0', 'ADM1', 'ADM2'] |
| Configured canonical boundary files exist | PASS | paths=['data/source/geoboundaries_cgaz_6_0_0/geoBoundariesCGAZ_ADM0.zip', 'data/source/geoboundaries_cgaz_6_0_0/geoBoundariesCGAZ_ADM1.zip', 'data/source/geoboundaries_cgaz_6_0_0/geoBoundariesCGAZ_ADM2.zip']; missing=[] |
| Configured countries do not mix boundary snapshots | PASS | ADM1=[('data/source/geoboundaries_cgaz_6_0_0/geoBoundariesCGAZ_ADM1.zip', 'geoBoundariesCGAZ_ADM1.shp', 'CGAZ-6.0.0')]; ADM2=[('data/source/geoboundaries_cgaz_6_0_0/geoBoundariesCGAZ_ADM2.zip', 'geoBoundariesCGAZ_ADM2.shp', 'CGAZ-6.0.0')] |
| Global spherical grid, antimeridian and polar policies are frozen | PASS | missing=[]; regional_analysis_crs=EPSG:8857; regional_display_crs=EPSG:3857 |
| Canonical spherical DGGRS generator is reproducible | PASS | type=spherical_dggrs; dggrs=OGC ISEA3H; level=11; cells=1771472; generator=DGGAL 0.0.6 |
| Production ownership builder uses canonical spherical topology | PASS | builder enumerates ISEA3H cells and obtains adjacency from DGGAL |
| World-edge topology is implemented rather than deferred | PASS | antimeridian=native_spherical_adjacency_no_planar_seam; polar=native_spherical_cells_no_planar_singularity |
| Tile IDs are independent of ownership | PASS | grid-coordinate scheme configured; ownership-derived prefix absent |
| Country and admin registry is data-driven | PASS | registry=config/country_registry_east_asia.json; configured_countries=6 |
| Spatial indexes are used for global boundary lookup | PASS | naming lookup is indexed; ADM0 and ADM1 global lookup indexes remain pending |
| ADM1/ADM2 hierarchy coherence is audited without country patches | FAIL | policy=country_neutral_report_only_no_automatic_repair; prototype_report=reports/korea_cgaz_hierarchy_consistency_audit.md; automated_global_audit=False |
| Neighbor lookup is topology-key based rather than pairwise | PASS | canonical DGGRS neighbor keys |
| Global gate has no country-specific tile-count quotas | PASS | frozen counts are regression observations; the universal one-tile official-area floor is not a country target quota |
| Output contract is world-build capable | PASS | prototype_outputs=[] |
| Prototype country coverage | INFO | configured=['KOR', 'PRK', 'CHN', 'JPN', 'MNG', 'TWN'] |

## Interpretation

This audit is separate from the East Asia release gate. A FAIL here
does not invalidate a geometrically correct East Asia build; it means the current
pipeline must not yet be treated as the canonical world-map pipeline.

The authoritative design contract is `GLOBAL_MAP_RULES.md`.
