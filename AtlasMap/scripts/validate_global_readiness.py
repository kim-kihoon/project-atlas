#!/usr/bin/env python3
"""Audit whether the Korea prototype is structurally ready for a world build."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def configured_countries(settings):
    primary = {
        "country": settings["country"],
        "admin1_source": settings["admin1_source"],
        "tile_naming": settings["tile_naming"],
    }
    return [primary, *settings.get("additional_countries", [])]


def nonempty(value):
    return value is not None and value != "" and value != [] and value != {}


def main():
    parser = argparse.ArgumentParser(
        description="Write the Atlas global-readiness audit report."
    )
    parser.add_argument(
        "--config",
        default="config/atlas_korea.json",
        help="Path to the current Atlas configuration.",
    )
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    root = config_path.parent.parent
    settings = json.loads(config_path.read_text(encoding="utf-8"))
    globalization = settings.get("globalization", {})
    snapshot = globalization.get("canonical_boundary_snapshot", {})
    global_grid = globalization.get("global_grid", {})
    countries = configured_countries(settings)
    build_path = root / "scripts" / "build_korea_map.py"
    build_text = build_path.read_text(encoding="utf-8")

    checks = []

    def check(name, passed, detail, failure_status="FAIL"):
        checks.append((name, "PASS" if passed else failure_status, detail))

    rules_path = root / str(globalization.get("rules_document") or "")
    check(
        "Authoritative global rules document",
        bool(globalization.get("rules_document")) and rules_path.is_file(),
        str(globalization.get("rules_document") or "unset"),
    )

    candidate_status = snapshot.get("candidate_status")
    candidate_report = snapshot.get("candidate_report")
    check(
        "Global boundary candidate evaluation is recorded",
        candidate_status in {"accepted", "rejected"}
        and nonempty(candidate_report)
        and (root / str(candidate_report)).is_file(),
        f"provider={snapshot.get('candidate_provider') or 'unset'}; "
        f"status={candidate_status or 'unevaluated'}; report={candidate_report or 'unset'}",
    )

    required_snapshot_fields = (
        "provider", "version", "reference_year", "license", "sha256",
        "adm0_path", "adm1_path", "adm2_path",
    )
    missing_snapshot = [field for field in required_snapshot_fields if not nonempty(snapshot.get(field))]
    check(
        "One frozen global ADM0/ADM1/ADM2 snapshot",
        not missing_snapshot,
        f"missing={missing_snapshot}; candidate={snapshot.get('candidate_provider') or 'unset'}; "
        f"candidate_status={candidate_status or 'unevaluated'}",
    )
    required_levels = set(snapshot.get("required_levels", []))
    check(
        "Canonical snapshot requires all hierarchy levels",
        required_levels == {"ADM0", "ADM1", "ADM2"},
        f"levels={sorted(required_levels)}",
    )
    configured_snapshot_paths = [snapshot.get(key) for key in ("adm0_path", "adm1_path", "adm2_path")]
    missing_files = [value for value in configured_snapshot_paths if value and not (root / value).is_file()]
    check(
        "Configured canonical boundary files exist",
        all(configured_snapshot_paths) and not missing_files,
        f"paths={configured_snapshot_paths}; missing={missing_files}",
    )

    admin1_signatures = {
        (
            str(item["admin1_source"].get("path")),
            str(item["admin1_source"].get("archive_member") or ""),
            str(
                item["admin1_source"].get("snapshot_version")
                or item["admin1_source"].get("source_year", 0)
            ),
        )
        for item in countries
    }
    adm2_signatures = {
        (
            str(item["tile_naming"].get("boundary_path")),
            str(item["tile_naming"].get("boundary_archive_member") or ""),
            str(
                item["tile_naming"].get("snapshot_version")
                or item["tile_naming"].get("boundary_year", 0)
            ),
        )
        for item in countries
    }
    check(
        "Configured countries do not mix boundary snapshots",
        len(admin1_signatures) == 1 and len(adm2_signatures) == 1 and not missing_snapshot,
        f"ADM1={sorted(admin1_signatures)}; ADM2={sorted(adm2_signatures)}",
    )

    grid_missing = [
        field for field in ("crs_or_dggs", "tile_id_scheme", "world_wrap_policy", "polar_policy")
        if not nonempty(global_grid.get(field))
    ]
    check(
        "Global grid, world-wrap and polar policies are frozen",
        not grid_missing and str(settings.get("crs")) != "EPSG:5179",
        f"missing={grid_missing}; prototype_crs={settings.get('crs')}",
    )
    check(
        "Tile IDs are independent of ownership",
        nonempty(global_grid.get("tile_id_scheme"))
        and "tile_prefix = (" not in build_text
        and "dominant_territory if dominant_territory" not in build_text,
        "grid-coordinate scheme configured; ownership-derived prefix absent",
    )

    registry_path = globalization.get("country_registry_path")
    check(
        "Country and admin registry is data-driven",
        nonempty(registry_path) and (root / str(registry_path)).is_file(),
        f"registry={registry_path or 'unset'}; configured_countries={len(countries)}",
    )
    check(
        "Spatial indexes are used for global boundary lookup",
        "QgsSpatialIndex" in build_text,
        "QgsSpatialIndex not found in the current builder",
    )
    hierarchy_audit = globalization.get("hierarchy_coherence_audit", {})
    hierarchy_report = hierarchy_audit.get("prototype_report")
    hierarchy_policy = hierarchy_audit.get("policy")
    hierarchy_automated = hierarchy_audit.get("automated_global_audit") is True
    check(
        "ADM1/ADM2 hierarchy coherence is audited without country patches",
        hierarchy_automated
        and hierarchy_policy == "country_neutral_report_only_no_automatic_repair"
        and nonempty(hierarchy_report)
        and (root / str(hierarchy_report)).is_file(),
        f"policy={hierarchy_policy or 'unset'}; "
        f"prototype_report={hierarchy_report or 'unset'}; "
        f"automated_global_audit={hierarchy_automated}",
    )
    pairwise_marker = "for position, first_index in enumerate(selected_indexes):"
    coordinate_neighbor_lookup = pairwise_marker not in build_text
    check(
        "Neighbor lookup is coordinate based rather than pairwise",
        coordinate_neighbor_lookup,
        (
            "normalized edge-key topology lookup"
            if coordinate_neighbor_lookup
            else "current builder performs an O(n^2) selected-tile neighbor scan"
        ),
    )

    validation = settings.get("validation", {})
    allocation_policy = settings.get("admin_assignment", {})
    ownership_quota_enabled = (
        int(allocation_policy.get("minimum_tiles_per_admin", 0)) not in {0, 1}
        or str(allocation_policy.get("policy")) not in {
            "strict_greatest_overlap_within_dominant_country",
            "greatest_overlap_then_same_country_minimum_representation",
        }
    )
    check(
        "Global gate has no country-specific tile-count quotas",
        not ownership_quota_enabled,
        "frozen counts are regression observations; the universal one-tile "
        "official-area floor is not a country target quota",
    )

    output_values = [str(value) for value in settings.get("outputs", {}).values()]
    korea_named_outputs = [value for value in output_values if "Korea" in value]
    check(
        "Output contract is world-build capable",
        not korea_named_outputs,
        f"prototype_outputs={korea_named_outputs}",
        failure_status="WARN",
    )
    checks.append((
        "Prototype country coverage",
        "INFO",
        f"configured={[item['country']['iso3'] for item in countries]}",
    ))

    failures = [name for name, status, _ in checks if status == "FAIL"]
    warnings = [name for name, status, _ in checks if status == "WARN"]
    ready = not failures
    report_relative = globalization.get("readiness_report") or "reports/global_readiness_report.md"
    report_path = root / report_relative
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Atlas global readiness report",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        f"Overall result: **{'PASS' if ready else 'FAIL'}**",
        "",
        f"- Blocking failures: {len(failures)}",
        f"- Warnings: {len(warnings)}",
        f"- Configured prototype countries: {len(countries)}",
        "",
        "| Check | Result | Detail |",
        "| --- | --- | --- |",
    ]
    lines.extend(
        f"| {name} | {status} | {detail.replace('|', '/')} |"
        for name, status, detail in checks
    )
    lines.extend([
        "",
        "## Interpretation",
        "",
        "This audit is separate from the Korean Peninsula release gate. A FAIL here",
        "does not invalidate a geometrically correct Korea build; it means the current",
        "pipeline must not yet be treated as the canonical world-map pipeline.",
        "",
        "The authoritative design contract is `GLOBAL_MAP_RULES.md`.",
        "",
    ])
    report_path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(f"Global readiness: {'PASS' if ready else 'FAIL'}")
    print(f"Report: {report_relative}")
    if failures:
        print("Blocking checks:")
        for failure in failures:
            print(f"- {failure}")
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
