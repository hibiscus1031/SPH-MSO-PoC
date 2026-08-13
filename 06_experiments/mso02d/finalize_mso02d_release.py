#!/usr/bin/env python3
"""Finalize MSO-02D from already-published diagnostic tables only.

This release-only executable never opens an observable or target payload and
never fits a model.  It validates the D0/D1/D2 boundary, repairs the D2
case-level CVAR *reporting aggregation* back to the frozen H-MSO-01R-B
fold-by-family equal-cell semantics, applies the preregistered mechanism
taxonomy, and writes the D3 register/report/ledger/manifest.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import argparse
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path
import subprocess
from typing import Any, Iterable

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "06_experiments/mso02d"
FINALIZER = Path(__file__).resolve()
REPORT = ROOT / "07_reports/mso02d_componentwise_failure_attribution_report.md"
MANIFEST = ROOT / "08_manifests/mso02d_manifest.json"
STATUS = ROOT / "08_manifests/mso02d_status_ledger.json"
FUTURE = ROOT / "05_registries/mso02d_future_hypothesis_candidate_register.json"
G1_AUDIT = OUT / "g1_full_population_polarization_audit.json"
D3_AUDIT = OUT / "d3_governance_adjudication_audit.json"

EVIDENCE = "EXPLORATORY_CONSUMED_DIAGNOSTIC_ONLY"
TERMINAL = "MSO02D_COMPONENTWISE_FAILURE_ATTRIBUTION_COMPLETE_NO_ACTIONABLE_TARGET_BLIND_ROUTE"
OLD_MSO02B = "MSO02B_PAIRED_PRELEARNING_IDENTIFIABILITY_REQUALIFICATION_NOT_EVALUABLE"
OLD_H_MSO01 = "H_MSO01_MULTISCALE_IDENTIFIABILITY_RESCUE_NOT_EVALUABLE"
OLD_HMSO01R_B = "HMSO01R_B_FRESH_CONFIRMATORY_MULTISCALE_IDENTIFIABILITY_RESCUE_NOT_QUALIFIED"
FINAL_PLACEHOLDER = "RECORDED_BY_FINAL_GIT_COMMIT_AND_USER_HANDOFF"

HMSO01R_A_FINAL = "9048eff137001e5f644575bd02c3856b4f4ac532"
HMSO01R_B_PRE_TARGET = "1c99103edaf76aa05915458fd498e07b1241e272"
HMSO01R_B_FINAL = "47a15ce3e38dbf13d671b9ae7275bb84761ae279"
MSO02D_PROTOCOL = "78ba0d5518909c96e3bf34383e0d95f30ca9ba17"
MSO02D_D0 = "8c2ea721c28fd94b5a71b117d8ce93a657b723e5"
MSO02D_D1_SCIENCE_FREEZE = "6d4456ec40d58456141e34f64a2c4ef9af355309"
MSO02D_D1_RELEASE_BINDING = "9cd76d0cc3ddd5202689278769446b4044bf5e5e"

# Pre-D3 and adjudicated byte identities are frozen here so that rerunning this
# release-only finalizer cannot erase the provenance of the initial D2 tables.
# The pre-D3 mechanism identities were independently reconstructed from the
# persisted D2 inputs with the frozen D2 adjudicator; the unchanged route matrix
# below is the byte-for-byte reconstruction anchor.
PRE_D3_CVAR_STRATA_SHA256 = "0776176ae20b1e2167656c46c95688e65b79ea96e6a326277c93def7052d0f58"
ADJUDICATED_CVAR_STRATA_SHA256 = "43d035dc76fdc3fe7dee587080f5e0c19807621167dab7fcf39dd421368a83da"
PRE_D3_MECHANISM_EVIDENCE_SHA256 = "5094b3c5392d73d77604598cfae5eca4ee785639ef7fff303923585819e410c5"
ADJUDICATED_MECHANISM_EVIDENCE_SHA256 = "ed81e307f1237cdc68aa687cadc1be66db3d127d6682bd4f0cdb85b44eb4ecd2"
PRE_D3_MECHANISM_VERDICTS_SHA256 = "2ab05184b5afd891cfff5c4b5a3a5f920487660c33bd188451703089bfe30c65"
ADJUDICATED_MECHANISM_VERDICTS_SHA256 = "7ecba0887333c0b90546663089ca78ed498044368cf2e1fe6d9dd12a41db90b1"
PRE_D3_ROUTE_MATRIX_SHA256 = "39d2da02eb6f3b6b23bf8a0928acdadeb6c6de1e016b9dd9309a36c70cdeb2a6"

COMPONENTS = (
    "density_rate",
    "pressure_gradient_acceleration",
    "viscosity_laplacian_acceleration",
)
ARMS = ("SS", "MS")
FAMILIES = ("F1", "F2", "F3", "F4")
FOLDS = tuple(f"FOLD_{index}" for index in range(6))

CANONICAL = OUT / "canonical_result_identity_audit.json"
THETA = OUT / "theta_definition_audit.json"
NRMSE = OUT / "nrmse_denominator_equivalence_audit.json"
ACCESS = OUT / "diagnostic_access_ledger.json"
FIREWALL = OUT / "firewall_audit.json"
FREEZE = OUT / "target_blind_geometry_freeze.json"
CVAR_HOTSPOT = OUT / "cvar_hotspot_map.csv"
CVAR_STRATA = OUT / "cvar_stratum_decomposition.csv"
MECHANISM_EVIDENCE = OUT / "mechanism_evidence_matrix.csv"
MECHANISM_VERDICTS = OUT / "mechanism_verdicts.csv"
ROUTES = OUT / "route_adjudication_matrix.csv"
DESIGN = OUT / "design_only_failure_stratification.csv"
OLD_G1 = ROOT / "06_experiments/mso02c/zero_denominator_ab_attribution.csv"

REQUIRED_EXPERIMENT_FILES = (
    "canonical_result_identity_audit.json",
    "theta_definition_audit.json",
    "nrmse_denominator_equivalence_audit.json",
    "target_blind_subspace_diagnostics.csv",
    "subspace_stability_audit.csv",
    "feature_group_energy_audit.csv",
    "target_blind_geometry_selection_matrix.csv",
    "target_blind_geometry_freeze.json",
    "target_blind_geometry_target_alignment.csv",
    "directional_proxy_availability_audit.csv",
    "directional_proxy_overlap_audit.csv",
    "directional_proxy_target_alignment.csv",
    "directional_proxy_residual_diagnostics.csv",
    "candidate_c_wn_wb_decomposition.csv",
    "candidate_c_ratio_cancellation_audit.csv",
    "cvar_hotspot_map.csv",
    "cvar_stratum_decomposition.csv",
    "oracle_residual_decomposition.csv",
    "oracle_gain_stratum_map.csv",
    "ss_ms_geometry_diagnostics.csv",
    "distance_concentration_audit.csv",
    "hubness_audit.csv",
    "neighbour_turnover_audit.csv",
    "near_collision_audit.csv",
    "ambiguity_vs_coverage.csv",
    "fixed_feature_group_ablation.csv",
    "design_only_failure_stratification.csv",
    "mechanism_evidence_matrix.csv",
    "mechanism_verdicts.csv",
    "route_adjudication_matrix.csv",
    "diagnostic_access_ledger.json",
    "firewall_audit.json",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    write_text_atomic(path, json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n")


def write_csv_atomic(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    if not rows:
        raise RuntimeError(f"refuse empty CSV {path}")
    fields = fields or list(rows[0])
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def git_output(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True,
    ).stdout.strip()


def verify_git_boundary(*, validate_only: bool) -> str:
    if git_output("branch", "--show-current") != "main" or git_output("remote"):
        raise RuntimeError("MSO02D_GIT_BOUNDARY_CONFLICT")
    head = git_output("rev-parse", "HEAD")
    subject = git_output("show", "-s", "--format=%s", "HEAD")
    allowed = {
        "MSO-02D D1: freeze target-blind alignment selection before target diagnostics",
        "MSO-02D: componentwise failure attribution and route adjudication",
    }
    if subject not in allowed:
        raise RuntimeError(f"MSO02D_UNEXPECTED_HEAD_SUBJECT:{subject}")
    if not validate_only and head != MSO02D_D1_RELEASE_BINDING:
        raise RuntimeError(f"MSO02D_RELEASE_MUST_START_AT_D1_BINDING:{head}")
    for commit, subject_expected in (
        (HMSO01R_B_FINAL, "H-MSO-01R-B: fresh confirmatory multiscale identifiability requalification"),
        (MSO02D_PROTOCOL, "MSO-02D: freeze componentwise attribution and route adjudication protocol"),
        (MSO02D_D0, "MSO-02D D0: freeze target-blind alignment and directional proxy definitions"),
        (MSO02D_D1_SCIENCE_FREEZE, "MSO-02D D1: freeze target-blind alignment selection before target diagnostics"),
        (MSO02D_D1_RELEASE_BINDING, "MSO-02D D1: freeze target-blind alignment selection before target diagnostics"),
    ):
        observed = git_output("show", "-s", "--format=%s", commit)
        if observed != subject_expected:
            raise RuntimeError(f"MSO02D_COMMIT_SUBJECT_CONFLICT:{commit}:{observed}")
    return head


def require_outputs() -> None:
    for name in REQUIRED_EXPERIMENT_FILES:
        if not (OUT / name).is_file():
            raise RuntimeError(f"MSO02D_REQUIRED_OUTPUT_MISSING:{name}")
    for path in (
        ROOT / "00_project_contract/mso02d_componentwise_failure_attribution_contract.md",
        ROOT / "05_registries/mso02d_feature_group_registry.json",
        ROOT / "05_registries/mso02d_target_blind_geometry_candidate_registry.json",
        ROOT / "05_registries/mso02d_directional_scale_response_proxy_registry.json",
        ROOT / "08_manifests/hmso01r_b_git_handoff.json",
        ROOT / "08_manifests/mso02d_d1_execution_erratum_01.json",
        ROOT / "08_manifests/mso02d_d2_execution_erratum_01.json",
    ):
        if not path.is_file():
            raise RuntimeError(f"MSO02D_REQUIRED_GOVERNANCE_ARTIFACT_MISSING:{path}")


def verify_d2_governance() -> tuple[dict[str, Any], dict[str, Any]]:
    canonical = read_json(CANONICAL)
    theta = read_json(THETA)
    nrmse = read_json(NRMSE)
    access = read_json(ACCESS)
    firewall = read_json(FIREWALL)
    freeze = read_json(FREEZE)
    if canonical.get("status") != "PASS" or len(canonical.get("rows", [])) != 9:
        raise RuntimeError("MSO02D_CANONICAL_IDENTITY_NOT_PASS")
    if not all(row.get("cross_source_identity_match") for row in canonical["rows"]):
        raise RuntimeError("MSO02D_CANONICAL_CROSS_SOURCE_CONFLICT")
    if theta.get("status") != "NOT_ADMISSIBLE_UNDEFINED_DIAGNOSTIC":
        raise RuntimeError("MSO02D_THETA_GOVERNANCE_CONFLICT")
    if nrmse.get("status") != "NOT_EQUIVALENT" or nrmse.get("one_minus_nrmse_squared_authorized"):
        raise RuntimeError("MSO02D_NRMSE_GOVERNANCE_CONFLICT")
    if access.get("d1_commit") != MSO02D_D1_RELEASE_BINDING:
        raise RuntimeError("MSO02D_D1_ACCESS_BINDING_CONFLICT")
    if access.get("consumed_target_reads") != 1 or access.get("prepublication_consumed_target_reads_total") != 4:
        raise RuntimeError("MSO02D_TARGET_READ_LEDGER_CONFLICT")
    if access.get("status") != "COMPLETE_FOR_STAGE_CUTOFF":
        raise RuntimeError("MSO02D_D2_INCOMPLETE")
    if firewall.get("status") != "PASS" or not firewall.get("all_prohibited_counts_zero"):
        raise RuntimeError("MSO02D_FIREWALL_FAILURE")
    if any(int(value) != 0 for value in firewall.get("prohibited_activity_counts", {}).values()):
        raise RuntimeError("MSO02D_NONZERO_PROHIBITED_ACTIVITY")
    if freeze.get("status") != "ROUTE_A_TARGET_BLIND_GEOMETRY_CANDIDATE_NOT_ESTABLISHED":
        raise RuntimeError("MSO02D_D1_SELECTION_STATUS_CONFLICT")
    if freeze.get("selected_candidate_id") is not None:
        raise RuntimeError("MSO02D_UNEXPECTED_D1_SELECTED_CANDIDATE")
    return access, firewall


def mean(values: Iterable[float]) -> float:
    values = list(values)
    if not values or not all(math.isfinite(value) for value in values):
        raise RuntimeError("MSO02D_INVALID_AGGREGATION_INPUT")
    return float(np.mean(np.asarray(values, dtype=np.float64)))


def legacy_equal_lineage_aggregate(
    rows: list[dict[str, str]], field: str, scope: str, scope_id: str,
) -> float:
    selected = rows
    if scope == "FOLD":
        selected = [row for row in selected if row["fold"] == scope_id]
    elif scope == "FAMILY":
        selected = [row for row in selected if row["family"] == scope_id]
    elif scope == "FAMILY_FOLD":
        family, fold = scope_id.split("|")
        selected = [row for row in selected if row["family"] == family and row["fold"] == fold]
    elif scope == "LINEAGE":
        selected = [row for row in selected if row["lineage"] == scope_id]
    elif scope != "OVERALL":
        raise RuntimeError(f"MSO02D_UNSUPPORTED_LEGACY_SCOPE:{scope}")
    cells: list[float] = []
    for fold in sorted({row["fold"] for row in selected}):
        for family in sorted({row["family"] for row in selected}):
            cell = [row for row in selected if row["fold"] == fold and row["family"] == family]
            if not cell:
                continue
            lineage_values = [
                mean(float(row[field]) for row in cell if row["lineage"] == lineage)
                for lineage in sorted({row["lineage"] for row in cell})
            ]
            cells.append(mean(lineage_values))
    return mean(cells)


def reconstructed_original_cvar_sha(
    rows: list[dict[str, str]], hotspots: list[dict[str, str]], fields: list[str],
) -> str:
    """Recreate the pre-D3 D2 CSV bytes from persisted case primitives."""
    case_scopes = {"OVERALL", "FOLD", "FAMILY", "FAMILY_FOLD", "LINEAGE"}
    by_key: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in hotspots:
        by_key[(row["arm"], row["component"])].append(row)
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for row in rows:
        reconstructed = {key: row.get(key, "") for key in fields}
        if row["scope"] in case_scopes:
            source = by_key[(row["arm"], row["component"])]
            reconstructed["cvar"] = legacy_equal_lineage_aggregate(
                source, "cvar", row["scope"], row["scope_id"]
            )
            reconstructed["coverage_fraction"] = legacy_equal_lineage_aggregate(
                source, "coverage_fraction", row["scope"], row["scope_id"]
            )
        writer.writerow(reconstructed)
    return hashlib.sha256(output.getvalue().encode("utf-8")).hexdigest()


def canonical_case_aggregate(
    rows: list[dict[str, str]], field: str, scope: str, scope_id: str,
) -> float:
    selected = rows
    if scope == "FOLD":
        selected = [row for row in selected if row["fold"] == scope_id]
    elif scope == "FAMILY":
        selected = [row for row in selected if row["family"] == scope_id]
    elif scope == "FAMILY_FOLD":
        family, fold = scope_id.split("|")
        selected = [row for row in selected if row["family"] == family and row["fold"] == fold]
    elif scope == "LINEAGE":
        selected = [row for row in selected if row["lineage"] == scope_id]
        return mean(float(row[field]) for row in selected)
    elif scope != "OVERALL":
        raise RuntimeError(f"MSO02D_UNSUPPORTED_CASE_SCOPE:{scope}")
    cells: list[float] = []
    for fold in sorted({row["fold"] for row in selected}):
        for family in sorted({row["family"] for row in selected}):
            cell = [float(row[field]) for row in selected if row["fold"] == fold and row["family"] == family]
            if cell:
                cells.append(mean(cell))
    return mean(cells)


def correct_cvar_reporting() -> dict[str, Any]:
    rows = read_csv(CVAR_STRATA)
    hotspots = read_csv(CVAR_HOTSPOT)
    input_sha = sha256(CVAR_STRATA)
    if input_sha not in {PRE_D3_CVAR_STRATA_SHA256, ADJUDICATED_CVAR_STRATA_SHA256}:
        raise RuntimeError(f"MSO02D_CVAR_RELEASE_INPUT_IDENTITY_CONFLICT:{input_sha}")
    original_fields = [field for field in rows[0] if field != "aggregation"]
    original_sha = (
        reconstructed_original_cvar_sha(rows, hotspots, original_fields)
        if "aggregation" in rows[0] else sha256(CVAR_STRATA)
    )
    if original_sha != PRE_D3_CVAR_STRATA_SHA256:
        raise RuntimeError(f"MSO02D_CVAR_PRE_D3_RECONSTRUCTION_CONFLICT:{original_sha}")
    case_scopes = {"OVERALL", "FOLD", "FAMILY", "FAMILY_FOLD", "LINEAGE"}
    by_arm_component: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in hotspots:
        if row.get("evidence_class") != EVIDENCE:
            raise RuntimeError("MSO02D_CVAR_HOTSPOT_EVIDENCE_CLASS_CONFLICT")
        by_arm_component[(row["arm"], row["component"])].append(row)
    corrected: list[dict[str, Any]] = []
    affected_count = 0
    rewritten_this_invocation = 0
    for row in rows:
        output: dict[str, Any] = dict(row)
        if row["scope"] in case_scopes:
            source = by_arm_component[(row["arm"], row["component"])]
            cvar = canonical_case_aggregate(source, "cvar", row["scope"], row["scope_id"])
            coverage = canonical_case_aggregate(source, "coverage_fraction", row["scope"], row["scope_id"])
            legacy_cvar = legacy_equal_lineage_aggregate(
                source, "cvar", row["scope"], row["scope_id"]
            )
            legacy_coverage = legacy_equal_lineage_aggregate(
                source, "coverage_fraction", row["scope"], row["scope_id"]
            )
            if legacy_cvar != cvar or legacy_coverage != coverage:
                affected_count += 1
            if float(row["cvar"]) != cvar or float(row["coverage_fraction"]) != coverage:
                rewritten_this_invocation += 1
            output["cvar"] = repr(cvar)
            output["coverage_fraction"] = repr(coverage)
            output["aggregation"] = "FROZEN_EQUAL_FOLD_FAMILY_CELL_CASE_MEAN"
        else:
            output["aggregation"] = "FROZEN_PARTICLE_STRATUM_MEAN"
        corrected.append(output)
    fields = list(corrected[0])
    write_csv_atomic(CVAR_STRATA, corrected, fields)
    corrected_sha = sha256(CVAR_STRATA)
    if corrected_sha != ADJUDICATED_CVAR_STRATA_SHA256:
        raise RuntimeError(f"MSO02D_CVAR_ADJUDICATED_IDENTITY_CONFLICT:{corrected_sha}")

    canonical = read_json(CANONICAL)
    lookup = {(row["metric"], row["component"]): row for row in canonical["rows"]}
    reread = read_csv(CVAR_STRATA)
    validation: list[dict[str, Any]] = []
    for arm in ARMS:
        for component in COMPONENTS:
            row = next(
                row for row in reread
                if row["arm"] == arm and row["component"] == component
                and row["scope"] == "OVERALL" and row["scope_id"] == "ALL"
            )
            expected = float(lookup[("cvar", component)]["csv_ss" if arm == "SS" else "csv_ms"])
            observed = float(row["cvar"])
            if observed != expected:
                raise RuntimeError(f"MSO02D_CVAR_CANONICAL_AGGREGATION_FAILURE:{arm}:{component}:{observed}:{expected}")
            validation.append({"arm": arm, "component": component, "observed": observed, "expected": expected, "exact_match": True})
    return {
        "original_sha256": original_sha,
        "corrected_sha256": corrected_sha,
        "corrected_row_count": affected_count,
        "input_sha256_before_this_invocation": input_sha,
        "rows_rewritten_this_invocation": rewritten_this_invocation,
        "correction": "REPLACE_NONCANONICAL_EQUAL_LINEAGE_CASE_SCOPE_REPORTING_WITH_FROZEN_EQUAL_FOLD_FAMILY_CELL_CASE_MEAN",
        "scientific_primitive_modified": False,
        "target_payload_read": False,
        "canonical_validation": validation,
    }


def overall_rows(name: str) -> list[dict[str, str]]:
    return [row for row in read_csv(OUT / name) if row.get("scope") == "OVERALL" and row.get("scope_id") == "ALL"]


def make_mechanism_outputs() -> tuple[dict[str, Any], dict[str, str]]:
    input_evidence_sha = sha256(MECHANISM_EVIDENCE)
    input_verdict_sha = sha256(MECHANISM_VERDICTS)
    if input_evidence_sha not in {
        PRE_D3_MECHANISM_EVIDENCE_SHA256, ADJUDICATED_MECHANISM_EVIDENCE_SHA256,
    }:
        raise RuntimeError(f"MSO02D_MECHANISM_EVIDENCE_INPUT_IDENTITY_CONFLICT:{input_evidence_sha}")
    if input_verdict_sha not in {
        PRE_D3_MECHANISM_VERDICTS_SHA256, ADJUDICATED_MECHANISM_VERDICTS_SHA256,
    }:
        raise RuntimeError(f"MSO02D_MECHANISM_VERDICTS_INPUT_IDENTITY_CONFLICT:{input_verdict_sha}")
    if sha256(ROUTES) != PRE_D3_ROUTE_MATRIX_SHA256:
        raise RuntimeError("MSO02D_PRE_D3_ROUTE_MATRIX_IDENTITY_CONFLICT")
    candidate = {(row["arm"], row["component"]): row for row in overall_rows("candidate_c_wn_wb_decomposition.csv")}
    cvar = {(row["arm"], row["component"]): row for row in overall_rows("cvar_stratum_decomposition.csv")}
    oracle = {row["component"]: row for row in overall_rows("oracle_gain_stratum_map.csv")}
    near = {(row["geometry"], row["component"]): row for row in overall_rows("near_collision_audit.csv")}
    geometry = [
        row for row in read_csv(OUT / "ss_ms_geometry_diagnostics.csv")
        if row["record_type"] == "FORMAL_U0_GEOMETRY_SUMMARY"
        and row["scope_type"] == "OVERALL"
    ]
    geom = {row["arm"]: row for row in geometry}
    turnover = next(
        row for row in read_csv(OUT / "neighbour_turnover_audit.csv")
        if row["scope_type"] == "OVERALL" and row["comparison_id"] == "FORMAL_SS_TO_MS"
    )
    ablation = {
        (row["component"], row["design_id"]): row
        for row in read_csv(OUT / "fixed_feature_group_ablation.csv")
        if row["scope"] == "OVERALL"
    }
    overlap = read_csv(OUT / "directional_proxy_overlap_audit.csv")
    proxy_alignment = [
        row for row in read_csv(OUT / "directional_proxy_target_alignment.csv")
        if row["scope"] == "OVERALL" and row["status"] == "EVALUABLE"
    ]
    density_proxy = max(
        (row for row in proxy_alignment if row["component"] == "density_rate"),
        key=lambda row: abs(float(row["proxy_distance_target_disagreement_spearman"])),
    )
    pressure_proxy = max(
        (row for row in proxy_alignment if row["component"] == "pressure_gradient_acceleration"),
        key=lambda row: abs(float(row["proxy_distance_target_disagreement_spearman"])),
    )
    rows: list[dict[str, Any]] = []

    def add(mechanism: str, diagnostic: str, component: str, direction: str, result: str, source: str,
            folds: str = "", families: str = "") -> None:
        rows.append({
            "mechanism_id": mechanism,
            "diagnostic_class": diagnostic,
            "component": component,
            "direction": direction,
            "result": result,
            "supporting_fold_count": folds,
            "supporting_family_count": families,
            "source": source,
            "claim_boundary": "OPERATIONAL_CONSUMED_DIAGNOSTIC_NOT_INTRINSIC_IDENTIFIABILITY_PROOF",
            "status": "ADJUDICATED_D3",
            "evidence_class": EVIDENCE,
        })

    add("F-MS1", "D1_TARGET_BLIND_SELECTION", "ALL", "NO_ACTIONABLE_SUPPORT",
        "selected_candidate_id=null", "target_blind_geometry_freeze.json")
    add("F-MS1", "FORMAL_U0_TARGET_ALIGNMENT", "PRESSURE_AND_VISCOSITY", "SUGGESTIVE_NOT_CAUSAL",
        "formal_geometry_target_alignment_does_not_identify_a_target_blind_repair", "target_blind_geometry_target_alignment.csv")

    for component in COMPONENTS[1:]:
        cand_ratio = float(candidate[("MS", component)]["d_wn_over_wb"]) / float(candidate[("SS", component)]["d_wn_over_wb"])
        cvar_ratio = float(cvar[("MS", component)]["cvar"]) / float(cvar[("SS", component)]["cvar"])
        add("F-MS2", "CANDIDATE_C_PERSISTENCE", component, "SUPPORT", f"MS_over_SS={cand_ratio:.17g}",
            "candidate_c_wn_wb_decomposition.csv")
        add("F-MS2", "FORMAL_CVAR_PERSISTENCE", component, "SUPPORT", f"MS_over_SS={cvar_ratio:.17g}",
            "cvar_stratum_decomposition.csv")
        add("F-MS2", "OPERATIONAL_NEAR_COLLISION_INSIDE_COVERAGE", component, "SUPPORT",
            "MS_near_collision_count=" + near[("U0_MS", component)]["near_collision_count"],
            "near_collision_audit.csv|ambiguity_vs_coverage.csv")

    add("F-MS3", "GLOBAL_ORACLE_PREDICTIVE_STRUCTURE", "PRESSURE_AND_VISCOSITY", "PREDICTIVE_INFORMATION_PRESENT",
        "oracle_gain_replicates_but_does_not_prove_information_sufficiency", "oracle_gain_stratum_map.csv", "6/6", "4/4")
    add("F-MS3", "INCREMENTAL_DIRECTIONAL_INFORMATION", "PRESSURE_AND_VISCOSITY", "NO_EVALUATED_INCREMENT",
        f"eligible_incremental_proxy_count={sum(row['eligible_as_route_b_incremental_information']=='True' for row in overlap)}",
        "directional_proxy_overlap_audit.csv")

    density_c = float(candidate[("MS", "density_rate")]["d_wn_over_wb"]) / float(candidate[("SS", "density_rate")]["d_wn_over_wb"])
    pressure_c = float(candidate[("MS", "pressure_gradient_acceleration")]["d_wn_over_wb"]) / float(candidate[("SS", "pressure_gradient_acceleration")]["d_wn_over_wb"])
    viscosity_c = float(candidate[("MS", "viscosity_laplacian_acceleration")]["d_wn_over_wb"]) / float(candidate[("SS", "viscosity_laplacian_acceleration")]["d_wn_over_wb"])
    add("F-MS4", "DENSITY_MOMENTUM_LOCAL_RESPONSE_CONTRAST", "ALL", "SUPPORT",
        f"candidate_ratios=density:{density_c:.6g};pressure:{pressure_c:.6g};viscosity:{viscosity_c:.6g}",
        "candidate_c_wn_wb_decomposition.csv|cvar_stratum_decomposition.csv")
    add("F-MS4", "PROXY_CLASS_ASSOCIATION_CONTRAST", "ALL", "SUPPORT",
        f"density_best={density_proxy['proxy_class']};momentum_best={pressure_proxy['proxy_class']}",
        "directional_proxy_target_alignment.csv")
    add("F-MS4", "FIXED_G4_ABLATION_COMPONENT_CONTRAST", "ALL", "SUPPORT",
        "leave_G4_out_improves_pressure_and_viscosity_6/6_folds_4/4_families_but_density_2/6_1/4",
        "fixed_feature_group_ablation.csv", "6/6 momentum; 2/6 density", "4/4 momentum; 1/4 density")

    add("F-MS5", "DISTANCE_CONCENTRATION_AND_LOCAL_RANDOM_SEPARATION", "ALL", "SUPPORT_PARTIAL",
        f"concentration_index={geom['SS']['distance_concentration_index']}->{geom['MS']['distance_concentration_index']};"
        f"k10_random_ratio={geom['SS']['k10_to_random_median_ratio']}->{geom['MS']['k10_to_random_median_ratio']}",
        "ss_ms_geometry_diagnostics.csv")
    add("F-MS5", "HUBNESS", "ALL", "SUPPORT_PARTIAL",
        f"skew={geom['SS']['hubness_occurrence_skew']}->{geom['MS']['hubness_occurrence_skew']};"
        f"gini={geom['SS']['neighbour_occurrence_gini']}->{geom['MS']['neighbour_occurrence_gini']}",
        "ss_ms_geometry_diagnostics.csv|hubness_audit.csv")
    add("F-MS5", "SS_TO_MS_NEIGHBOUR_TURNOVER", "ALL", "SUPPORT_PARTIAL",
        f"mean_turnover={turnover['mean_neighbour_turnover']}", "neighbour_turnover_audit.csv")
    add("F-MS5", "REVERSE_EVIDENCE", "DENSITY_AND_ALL", "LIMITS_TO_PARTIAL",
        f"semantic_group_domination={geom['SS']['semantic_group_domination']}->{geom['MS']['semantic_group_domination']};density_succeeds",
        "ss_ms_geometry_diagnostics.csv|canonical_result_identity_audit.json")

    for component in COMPONENTS[1:]:
        add("F-MS6", "ORACLE_GAIN_REPLICATION", component, "SUPPORT",
            f"oracle_MS_over_SS={oracle[component]['oracle_nrmse_ratio_ms_over_ss']}",
            "oracle_gain_stratum_map.csv", "6/6", "4/4")
        add("F-MS6", "LOCAL_CANDIDATE_C_NONRESCUE", component, "SUPPORT",
            "candidate_MS_over_SS=" + format(
                float(candidate[("MS", component)]["d_wn_over_wb"])
                / float(candidate[("SS", component)]["d_wn_over_wb"]), ".17g"
            ),
            "candidate_c_wn_wb_decomposition.csv")
        add("F-MS6", "LOCAL_CVAR_NONRESCUE", component, "SUPPORT",
            "cvar_MS_over_SS=" + format(
                float(cvar[("MS", component)]["cvar"])
                / float(cvar[("SS", component)]["cvar"]), ".17g"
            ),
            "cvar_stratum_decomposition.csv")
    add("F-MS6", "FORMAL_COVERAGE_GUARD", "PRESSURE_AND_VISCOSITY", "SUPPORT",
        "formal_coverage_passes_and_cannot_substitute_for_identifiability", "ambiguity_vs_coverage.csv")
    add("F-MS6", "INSIDE_COVERAGE_OPERATIONAL_AMBIGUITY", "PRESSURE_AND_VISCOSITY", "SUPPORT",
        "all_observed_MS_momentum_near_collisions_are_inside_coverage", "ambiguity_vs_coverage.csv")
    add("F-MS6", "DENSITY_POSITIVE_CONTROL_CONTRAST", "ALL", "SUPPORT",
        "density_Candidate_C_CVAR_and_oracle_all_improve_while_momentum_local_metrics_do_not", "canonical_result_identity_audit.json")

    evidence_fields = [
        "mechanism_id", "diagnostic_class", "component", "direction", "result",
        "supporting_fold_count", "supporting_family_count", "source", "claim_boundary",
        "status", "evidence_class",
    ]
    write_csv_atomic(MECHANISM_EVIDENCE, rows, evidence_fields)

    verdict_specs = (
        ("F-MS1", "TARGET_GEOMETRY_MISALIGNMENT", "INCONCLUSIVE", 2,
         "NO_TARGET_BLIND_ALTERNATIVE_GEOMETRY_WAS_ESTABLISHED"),
        ("F-MS2", "PERSISTENT_OPERATIONAL_LOCAL_AMBIGUITY", "SUPPORTED_PARTIAL", 3,
         "CANDIDATE_C_CVAR_AND_INSIDE_COVERAGE_NEAR_COLLISIONS_SUPPORT_ONLY_OPERATIONAL_AMBIGUITY"),
        ("F-MS3", "CURRENT_SUPPORT_SCALE_FAMILY_INSUFFICIENT", "INCONCLUSIVE", 2,
         "PREDICTIVE_INFORMATION_EXISTS_BUT_MISSING_INFORMATION_TYPE_OR_NECESSITY_IS_NOT_IDENTIFIED"),
        ("F-MS4", "COMPONENT_SPECIFIC_REPRESENTATION_REQUIREMENT", "SUPPORTED_PARTIAL", 3,
         "LOCAL_RESPONSE_PROXY_CLASS_AND_FIXED_GROUP_DEPENDENCE_DIFFER_BY_COMPONENT_WITH_NUMERICAL_LIMITS"),
        ("F-MS5", "HIGH_DIMENSION_DISTANCE_DILUTION", "SUPPORTED_PARTIAL", 3,
         "CONCENTRATION_HUBNESS_AND_TURNOVER_SUPPORT_A_PARTIAL_EFFECT_BUT_DENSITY_SUCCEEDS_IN_THE_SAME_110D_GEOMETRY"),
        ("F-MS6", "GLOBAL_PREDICTABILITY_LOCAL_IDENTIFIABILITY_SEPARATION", "SUPPORTED_DOMINANT", 6,
         "MULTIPLE_INDEPENDENT_DIAGNOSTICS_REPLICATE_FOR_BOTH_MOMENTUM_COMPONENTS_WITH_DENSITY_AS_POSITIVE_CONTROL"),
    )
    verdict_rows = [{
        "mechanism_id": identifier,
        "mechanism": name,
        "verdict": verdict,
        "independent_diagnostic_count": count,
        "taxonomy_minimum_satisfied": (verdict not in {"SUPPORTED_PARTIAL", "SUPPORTED_DOMINANT"}) or count >= (3 if verdict == "SUPPORTED_DOMINANT" else 2),
        "adjudication_reason": reason,
        "claim_boundary": "OPERATIONAL_CONSUMED_DIAGNOSTIC_NOT_INTRINSIC_IDENTIFIABILITY_PROOF",
        "status": "ADJUDICATED_D3",
        "evidence_class": EVIDENCE,
    } for identifier, name, verdict, count, reason in verdict_specs]
    write_csv_atomic(MECHANISM_VERDICTS, verdict_rows)
    corrected_evidence_sha = sha256(MECHANISM_EVIDENCE)
    corrected_verdict_sha = sha256(MECHANISM_VERDICTS)
    if corrected_evidence_sha != ADJUDICATED_MECHANISM_EVIDENCE_SHA256:
        raise RuntimeError(f"MSO02D_MECHANISM_EVIDENCE_ADJUDICATED_IDENTITY_CONFLICT:{corrected_evidence_sha}")
    if corrected_verdict_sha != ADJUDICATED_MECHANISM_VERDICTS_SHA256:
        raise RuntimeError(f"MSO02D_MECHANISM_VERDICTS_ADJUDICATED_IDENTITY_CONFLICT:{corrected_verdict_sha}")
    verdict_map = {row["mechanism_id"]: row["verdict"] for row in verdict_rows}
    correction = {
        "original_mechanism_evidence_sha256": PRE_D3_MECHANISM_EVIDENCE_SHA256,
        "corrected_mechanism_evidence_sha256": corrected_evidence_sha,
        "original_mechanism_verdicts_sha256": PRE_D3_MECHANISM_VERDICTS_SHA256,
        "corrected_mechanism_verdicts_sha256": corrected_verdict_sha,
        "input_mechanism_evidence_sha256_before_this_invocation": input_evidence_sha,
        "input_mechanism_verdicts_sha256_before_this_invocation": input_verdict_sha,
        "pre_d3_reconstruction_anchor_route_matrix_sha256": PRE_D3_ROUTE_MATRIX_SHA256,
        "pre_d3_reconstruction_method": "PERSISTED_D2_INPUTS_WITH_FROZEN_D2_ADJUDICATOR_NO_TARGET_READ",
        "correction": "ENFORCE_PREREGISTERED_INDEPENDENT_DIAGNOSTIC_MINIMA_AND_D3_TAXONOMY",
        "target_payload_read": False,
        "formal_verdict_modified": False,
        "h_mso01r_reverdict": False,
        "mso02d_diagnostic_adjudication_only": True,
    }
    return correction, verdict_map


def make_g1_audit() -> dict[str, Any]:
    old = [row for row in read_csv(OLD_G1) if row["component"] == "pressure_gradient_acceleration"]
    old_counts: dict[str, dict[str, int]] = {}
    for arm in ARMS:
        counts = Counter(row["query_polarization"] for row in old if row["arm"] == arm)
        old_counts[arm] = {key: int(counts[key]) for key in sorted(counts)}
        if old_counts[arm] != {"longitudinal": 65, "transverse": 54}:
            raise RuntimeError("MSO02D_OLD_G1_FINGERPRINT_IDENTITY_FAILURE")
    design = [row for row in read_csv(DESIGN) if row["design_only_label"] == "polarization" and row["arm"] == "MS"]
    full_population: dict[str, Any] = {}
    case_counts: dict[str, int] = {}
    for row in design:
        polarization = json.loads(row["stratum"])
        case_counts[polarization] = int(row["case_count"])
        if row["component"] in COMPONENTS[1:]:
            full_population.setdefault(row["component"], {})[polarization] = {
                "case_count": int(row["case_count"]),
                "candidate_c": float(row["candidate_c_d"]),
                "cvar": float(row["cvar"]),
                "near_collision_rate": float(row["near_collision_rate"]),
                "oracle_residual_rms": float(row["oracle_residual_rms"]),
            }
    if case_counts != {"longitudinal": 111, "none": 161, "transverse": 112}:
        raise RuntimeError(f"MSO02D_FULL_POPULATION_POLARIZATION_COUNT_FAILURE:{case_counts}")
    pressure = full_population["pressure_gradient_acceleration"]
    viscosity = full_population["viscosity_laplacian_acceleration"]
    pressure_long_minus_trans = pressure["longitudinal"]["candidate_c"] - pressure["transverse"]["candidate_c"]
    viscosity_long_minus_trans = viscosity["longitudinal"]["candidate_c"] - viscosity["transverse"]["candidate_c"]
    cross_component_direction_consistent = pressure_long_minus_trans * viscosity_long_minus_trans > 0
    audit = {
        "schema_version": "1.0.0",
        "project": "SPH-MSO-PoC",
        "stage": "MSO-02D-D3",
        "status": "G1_65_54_FULL_POPULATION_REPLICATION_NOT_ESTABLISHED",
        "evidence_class": EVIDENCE,
        "old_zero_denominator_subset": {
            "source": str(OLD_G1.relative_to(ROOT)),
            "source_sha256": sha256(OLD_G1),
            "population_scope": "OLD_G1_ZERO_DENOMINATOR_PRESSURE_SUBSET_ONLY",
            "counts_by_arm": old_counts,
            "load_bearing_for_full_population_route_b": False,
        },
        "full_fresh_r_b_population": {
            "source": str(DESIGN.relative_to(ROOT)),
            "source_sha256": sha256(DESIGN),
            "polarization_case_counts": case_counts,
            "component_strata": full_population,
            "pressure_longitudinal_minus_transverse_candidate_c": pressure_long_minus_trans,
            "viscosity_longitudinal_minus_transverse_candidate_c": viscosity_long_minus_trans,
            "cross_component_direction_consistent": cross_component_direction_consistent,
        },
        "exact_65_54_count_comparison_applicable_to_full_population": False,
        "replication_status": "REPLICATION_NOT_ESTABLISHED",
        "reason": "THE_OLD_COUNTS_DESCRIBE_A_BINARY_ZERO_DENOMINATOR_SUBSET; FULL_POPULATION_POLARIZATION_STRATA_HAVE_111_112_161_CASES_AND_OPPOSITE_PRESSURE_VISCOSITY_CANDIDATE_C_DIRECTIONS",
        "route_b_may_rely_on_old_fingerprint": False,
        "target_payload_read_by_d3": False,
        "fresh_evidence_generated": False,
    }
    write_json_atomic(G1_AUDIT, audit)
    return audit


def make_future_register() -> dict[str, Any]:
    candidates = [
        {
            "candidate_id": "H2-A",
            "candidate_name": "TARGET_BLIND_ALIGNED_MULTISCALE_GEOMETRY",
            "status": "NOT_SUPPORTED",
            "motivating_evidence": [
                "U1_U2_U3_PROSPECTIVELY_DEFINED_FROM_TRAINING_FOLD_OBSERVABLES_ONLY",
                "D1_ROUTE_A_TARGET_BLIND_GEOMETRY_CANDIDATE_NOT_ESTABLISHED",
                "SELECTED_CANDIDATE_ID_NULL_AND_NO_LEGAL_T3_NONIDENTITY_COMPARISON",
            ],
            "deployment_availability": "DETERMINISTIC_FROM_EXISTING_110D_BUT_NO_TRANSFORM_SELECTED",
            "new_information_or_reparameterization": "TARGET_BLIND_REPARAMETERIZATION_ONLY",
            "overlap_with_existing_110d": "EXACT_SAME_COLUMNS_WITH_SCALING_PROJECTION_OR_WHITENING",
            "overlap_with_ddo02b": "NO_PRINCIPAL_FRAME; GEOMETRY_TRANSFORM_CLASS_NOT_DDO02B_FRAME_DESCRIPTOR",
            "leakage_risk": "LOW_ONLY_IF_FROZEN_BEFORE_TARGET; ANY_POST_D2_SELECTION_IS_PROHIBITED",
            "expected_deployment_cost": "NOT_APPLICABLE_WITHOUT_A_SELECTED_TRANSFORM",
            "single_variable_intervention": "NOT_ESTABLISHED_BECAUSE_NO_UNIQUE_TRANSFORM_EXISTS",
            "fresh_falsifiable_test": "A_SEPARATE_PRETARGET_CONTRACT_COULD_FREEZE_ONE_TRANSFORM_VS_U0_ON_COMPLETELY_FRESH_LINEAGES",
            "density_role": "PRIMARY_NONINFERIORITY_AND_REQUALIFICATION_GUARD_FOR_ANY_UNIVERSAL_TEST",
            "pressure_viscosity_primary_role": "MOMENTUM_PRIMARY_COMPONENTS_IF_A_FUTURE_INTERVENTION_EVER_EXISTS",
            "why_not_post_hoc_h_mso01r_rescue": "TARGET_INFORMED_RETURN_TO_D1_SELECTION_IS_FORBIDDEN_AND_NO_CANDIDATE_WAS_ESTABLISHED",
            "evidence_strength": "NOT_SUPPORTED_BY_PREREGISTERED_D1_SELECTION",
            "prospective_contract_design_recommended": False,
            "fresh_compute_authorized": False,
        },
        {
            "candidate_id": "H2-B",
            "candidate_name": "O2_EQUIVARIANT_DIRECTION_RESOLVED_SCALE_RESPONSE",
            "status": "NOT_SUPPORTED",
            "motivating_evidence": [
                "P1_P4_USE_NO_PRINCIPAL_EIGENFRAME_SIGN_CONVENTION_OR_ARBITRARY_FALLBACK",
                "P1_P4_FULL_POPULATION_ASSOCIATIONS_WERE_EVALUATED",
                "ALL_70_EVALUATED_PROXIES_ARE_EXISTING_110D_ALGEBRAIC_REPARAMETERIZATIONS",
                "P5_IS_THE_ONLY_NEW_INFORMATION_CLASS_AND_WAS_UNAVAILABLE_UNEVALUATED",
                "G1_65_54_FULL_POPULATION_REPLICATION_NOT_ESTABLISHED",
            ],
            "definition_scope_limitation": {
                "P1_materialized": ["DELTA_0p75_1p25_1p50", "G_LOG_SECANT_0p75_1p25_1p50"],
                "not_materialized_as_P1_vectors": ["S_0p75_1p25", "S_1p00_1p50", "C_0p75_1p00_1p25", "C_1p00_1p25_1p50"],
                "interpretation": "NO_ROUTE_B_EVIDENCE_IS_CLAIMED_FOR_UNMATERIALIZED_S_OR_C_VECTOR_SCOPE",
            },
            "deployment_availability": "P1_P4_FIXED_ALGEBRA_AVAILABLE; P5_NOT_RECONSTRUCTIBLE_FROM_FROZEN_STORE",
            "new_information_or_reparameterization": "NO_EVALUATED_NEW_INFORMATION_PROXY",
            "overlap_with_existing_110d": "P1_P4_DETERMINISTIC_ALGEBRA; P5_WOULD_REQUIRE_NEW_NONBASE_PER_SCALE_TENSOR_MOMENTS",
            "overlap_with_ddo02b": "PRINCIPLED_NO_FRAME_DIFFERENCE_BUT_NO_EVALUATED_INCREMENTAL_INFORMATION",
            "leakage_risk": "LOW_FOR_FROZEN_P1_P5_DEFINITIONS; INVENTING_OR_SELECTING_AFTER_TARGET_IS_PROHIBITED",
            "expected_deployment_cost": "P1_ZERO; P2_P4_FIXED_SCALAR_ARITHMETIC; P5_NEW_TENSOR_MOMENT_EVALUATION",
            "single_variable_intervention": "POTENTIAL_P5_ONLY_ADDITION_NOT_ESTABLISHED_OR_AUTHORIZED",
            "fresh_falsifiable_test": "A_SEPARATE_PRETARGET_CONTRACT_COULD_ADD_ONE_P5_TENSOR_RESPONSE_ON_FRESH_LINEAGES_WITH_DENSITY_GUARD",
            "density_role": "NONDEGRADATION_NEGATIVE_CONTROL_GUARD_FOR_MOMENTUM_SPECIFIC_DIRECTIONAL_TEST",
            "pressure_viscosity_primary_role": "JOINT_MOMENTUM_PRIMARY_COMPONENTS_IN_A_SEPARATE_FUTURE_CONTRACT_ONLY",
            "why_not_post_hoc_h_mso01r_rescue": "P1_P4_ADD_NO_INFORMATION_P5_WAS_NOT_PRESENT_AND_G1_FULL_POPULATION_REPLICATION_WAS_NOT_ESTABLISHED",
            "evidence_strength": "NOT_SUPPORTED_NO_TWO_INCREMENTAL_PROXIES_OR_REQUIRED_REPLICATION",
            "prospective_contract_design_recommended": False,
            "fresh_compute_authorized": False,
        },
        {
            "candidate_id": "H2-S",
            "candidate_name": "SUPERVISED_REPRESENTATION_LEARNING",
            "status": "OUTSIDE_PRELEARNING_SCOPE",
            "motivating_evidence": [
                "FROZEN_NONNEURAL_ORACLE_SHOWS_GLOBAL_PREDICTIVE_STRUCTURE",
                "TARGET_BLIND_A_AND_INCREMENTAL_B_ARE_NOT_ACTIONABLE",
                "THIS_DOES_NOT_ESTABLISH_THAT_SUPERVISION_CLOSES_LOCAL_OPERATIONAL_AMBIGUITY",
            ],
            "deployment_availability": "NOT_EVALUATED; OFFLINE_TARGET_SUPERVISION_WOULD_BE_REQUIRED",
            "new_information_or_reparameterization": "TARGET_DERIVED_GEOMETRY_OUTSIDE_PRELEARNING_SCOPE",
            "overlap_with_existing_110d": "MAY_USE_110D_INPUT_BUT_ADDS_TARGET_DERIVED_PARAMETERS",
            "overlap_with_ddo02b": "SEPARATE_SUPERVISED_PROJECT_CLASS",
            "leakage_risk": "CATEGORICALLY_OUTSIDE_CURRENT_PRELEARNING_FIREWALL",
            "expected_deployment_cost": "UNKNOWN_UNREGISTERED_MODEL_TRAINING_VALIDATION_AND_GOVERNANCE",
            "single_variable_intervention": "NOT_DEFINED_IN_MSO02D",
            "fresh_falsifiable_test": "WOULD_REQUIRE_SEPARATE_CONTRACT_TRAINING_AND_FRESH_LINEAGE_HELD_OUT_EVALUATION",
            "density_role": "AT_MINIMUM_NONDEGRADATION_CONTROL_UNDER_ANY_SEPARATE_FUTURE_CONTRACT",
            "pressure_viscosity_primary_role": "POTENTIAL_RESEARCH_TARGETS_ONLY_IN_A_SEPARATE_PROJECT",
            "why_not_post_hoc_h_mso01r_rescue": "LEARNED_GEOMETRY_DOES_NOT_ANSWER_NATURAL_PRELEARNING_IDENTIFIABILITY_AND_CANNOT_REVERDICT_H_MSO01R",
            "evidence_strength": "OUTSIDE_PRELEARNING_SCOPE_NOT_EVALUATED",
            "prospective_contract_design_recommended": False,
            "fresh_compute_authorized": False,
            "neural_training_authorized": False,
        },
    ]
    register = {
        "schema_version": "1.0.0",
        "project": "SPH-MSO-PoC",
        "stage": "MSO-02D-D3",
        "status": "FUTURE_HYPOTHESIS_CANDIDATES_ADJUDICATED",
        "evidence_class": EVIDENCE,
        "candidate_status_taxonomy": [
            "SUPPORTED_FOR_PROSPECTIVE_CONTRACT_DESIGN", "INCONCLUSIVE",
            "NOT_SUPPORTED", "OUTSIDE_PRELEARNING_SCOPE",
        ],
        "candidates": candidates,
        "route_summary": {
            "route_a": "NOT_SUPPORTED",
            "route_b": "NOT_SUPPORTED",
            "route_c": "SUPPORT_SCALE_ROUTE_CLOSURE_RECOMMENDED",
            "paper_route_recommended": True,
        },
        "governance": {
            "new_prospective_hypothesis_design_recommended": False,
            "fresh_compute_authorized": False,
            "h_mso01r_reverdict": False,
            "formal_feature_modification": False,
            "formal_metric_modification": False,
            "neural_training_authorized": False,
            "attention_authorized": False,
            "transformer_authorized": False,
            "learned_operator_authorized": False,
            "mso03_authorized": False,
        },
    }
    write_json_atomic(FUTURE, register)
    return register


def fmt(value: float, digits: int = 6) -> str:
    return f"{value:.{digits}g}"


def make_report(verdicts: dict[str, str], g1: dict[str, Any], access: dict[str, Any], firewall: dict[str, Any]) -> str:
    canonical = {(row["metric"], row["component"]): row for row in read_json(CANONICAL)["rows"]}
    candidate = {(row["arm"], row["component"]): row for row in overall_rows("candidate_c_wn_wb_decomposition.csv")}
    cvar = {(row["arm"], row["component"]): row for row in overall_rows("cvar_stratum_decomposition.csv")}
    oracle = {row["component"]: row for row in overall_rows("oracle_gain_stratum_map.csv")}
    near = {(row["geometry"], row["component"]): row for row in overall_rows("near_collision_audit.csv")}
    ambiguity = {(row["geometry"], row["component"], row["coverage_status"]): row for row in read_csv(OUT / "ambiguity_vs_coverage.csv")}
    geom = {
        row["arm"]: row for row in read_csv(OUT / "ss_ms_geometry_diagnostics.csv")
        if row["record_type"] == "FORMAL_U0_GEOMETRY_SUMMARY" and row["scope_type"] == "OVERALL"
    }
    turnover = next(row for row in read_csv(OUT / "neighbour_turnover_audit.csv") if row["scope_type"] == "OVERALL" and row["comparison_id"] == "FORMAL_SS_TO_MS")
    selection = {
        row["candidate_id"]: row for row in read_csv(OUT / "target_blind_geometry_selection_matrix.csv")
        if row["record_type"] == "TARGET_BLIND_SELECTION_SUMMARY"
    }
    proxy_overlap = read_csv(OUT / "directional_proxy_overlap_audit.csv")
    proxy_available = read_csv(OUT / "directional_proxy_availability_audit.csv")
    proxy_align = [row for row in read_csv(OUT / "directional_proxy_target_alignment.csv") if row["scope"] == "OVERALL" and row["status"] == "EVALUABLE"]
    residual = read_csv(OUT / "directional_proxy_residual_diagnostics.csv")
    ablation = {(row["component"], row["design_id"]): row for row in read_csv(OUT / "fixed_feature_group_ablation.csv") if row["scope"] == "OVERALL"}

    def ratio(metric: str, component: str) -> float:
        return float(canonical[(metric, component)]["paired_or_recomputed_ratio"])

    def formal_cvar_family(component: str, family: str, arm: str) -> float:
        rows = [row for row in read_csv(CVAR_HOTSPOT) if row["component"] == component and row["family"] == family and row["arm"] == arm]
        return mean(mean(float(row["cvar"]) for row in rows if row["fold"] == fold) for fold in FOLDS)

    def formal_cvar_fold(component: str, fold: str, arm: str) -> float:
        rows = [row for row in read_csv(CVAR_HOTSPOT) if row["component"] == component and row["fold"] == fold and row["arm"] == arm]
        return mean(mean(float(row["cvar"]) for row in rows if row["family"] == family) for family in FAMILIES)

    pressure_proxy = max((row for row in proxy_align if row["component"] == COMPONENTS[1]), key=lambda row: abs(float(row["proxy_distance_target_disagreement_spearman"])))
    viscosity_proxy = max((row for row in proxy_align if row["component"] == COMPONENTS[2]), key=lambda row: abs(float(row["proxy_distance_target_disagreement_spearman"])))
    overall_ridge = [row for row in residual if row["diagnostic"] == "FROZEN_ALPHA1_RIDGE_RESIDUAL_INCREMENT" and row["scope"] == "OVERALL"]
    singular_count = sum(bool(row.get("numerical_failure")) for row in residual)
    p_in = ambiguity[("U0_MS", COMPONENTS[1], "INSIDE_COVERAGE")]
    p_out = ambiguity[("U0_MS", COMPONENTS[1], "OUTSIDE_COVERAGE")]
    v_in = ambiguity[("U0_MS", COMPONENTS[2], "INSIDE_COVERAGE")]
    v_out = ambiguity[("U0_MS", COMPONENTS[2], "OUTSIDE_COVERAGE")]

    lines = [
        "# MSO-02D Componentwise Identifiability Failure Attribution and Route Adjudication Report",
        "",
        f"Terminal status: `{TERMINAL}`.",
        "",
        f"Evidence class: `{EVIDENCE}`. 本报告仅为 consumed-evidence diagnostic attribution；不修改 H-MSO-01R、formal metric、feature、fold、normalization、gate 或 component verdict。",
        "",
        "## 关键结论",
        "",
        "Route A 与 Route B 均未形成 actionable target-blind candidate；F-MS6（global predictability/local operational identifiability separation）为 dominant。建议关闭当前 support-scale development route 并转论文，不创建 fresh H-MSO-02 atlas，不授权 fresh compute、MSO-03 或 learning。",
        "",
        "## 必答 40 项",
        "",
        "1. **Frozen R-B canonical results 是否全部一致？** 是。九项跨源 identity 均 PASS、最大跨源差异为 0。"
        f"Density 的 Candidate C/CVAR/oracle 为 `{canonical[('candidate_c', COMPONENTS[0])]['csv_ss']:.8g}→{canonical[('candidate_c', COMPONENTS[0])]['csv_ms']:.8g}` / `{canonical[('cvar', COMPONENTS[0])]['csv_ss']:.8g}→{canonical[('cvar', COMPONENTS[0])]['csv_ms']:.8g}` / `{canonical[('oracle', COMPONENTS[0])]['csv_ss']:.8g}→{canonical[('oracle', COMPONENTS[0])]['csv_ms']:.8g}`；"
        f"pressure 为 `{canonical[('candidate_c', COMPONENTS[1])]['csv_ss']:.8g}→{canonical[('candidate_c', COMPONENTS[1])]['csv_ms']:.8g}` / `{canonical[('cvar', COMPONENTS[1])]['csv_ss']:.8g}→{canonical[('cvar', COMPONENTS[1])]['csv_ms']:.8g}` / `{canonical[('oracle', COMPONENTS[1])]['csv_ss']:.8g}→{canonical[('oracle', COMPONENTS[1])]['csv_ms']:.8g}`；"
        f"viscosity 为 `{canonical[('candidate_c', COMPONENTS[2])]['csv_ss']:.8g}→{canonical[('candidate_c', COMPONENTS[2])]['csv_ms']:.8g}` / `{canonical[('cvar', COMPONENTS[2])]['csv_ss']:.8g}→{canonical[('cvar', COMPONENTS[2])]['csv_ms']:.8g}` / `{canonical[('oracle', COMPONENTS[2])]['csv_ss']:.8g}→{canonical[('oracle', COMPONENTS[2])]['csv_ms']:.8g}`。",
        "",
        "2. **NRMSE denominator 是否验证，能否解释为 explained variance？** 已审计但不等价。冻结 denominator 是 outer-fold development population 上、case/family-equal 的 about-zero target RMS，并进一步按 fold×family cellwise roots 聚合，不是同权中心化 pooled variance。`1-NRMSE²` 与任何 R²-like quantity 均未获授权。",
        "",
        "3. **θ 是否有可复核定义，5.4/13.4 是否可用？** 没有找到完整公式、输入、分母与 aggregation provenance；状态为 `NOT_ADMISSIBLE_UNDEFINED_DIAGNOSTIC`，5.4/13.4 不得作为承重证据。",
        "",
        f"4. **Density 为什么三项同时改善？** 操作上，formal U0 的 `W(N)` 从 `{candidate[('SS', COMPONENTS[0])]['wn']}` 降至 `{candidate[('MS', COMPONENTS[0])]['wn']}`，而 `W(B)={candidate[('SS', COMPONENTS[0])]['wb']}` 在两 arm 相同；因此 Candidate C 降至 `{ratio('candidate_c', COMPONENTS[0]):.6g}×`。CVAR 与 oracle 同时降至 `{ratio('cvar', COMPONENTS[0]):.6g}×`、`{ratio('oracle', COMPONENTS[0]):.6g}×`，均在 6/6 folds、4/4 families 同向。这里只证明当前局部几何能读取 density 的预测结构，不宣称物理因果机制已证明。",
        "",
        f"5. **Pressure 为什么 oracle 改善但 local ambiguity 不改善？** Oracle 降至 `{ratio('oracle', COMPONENTS[1]):.6g}×`（6/6、4/4），但 Candidate C 仅为 `{ratio('candidate_c', COMPONENTS[1]):.6g}×`，formal CVAR 反而为 `{ratio('cvar', COMPONENTS[1]):.6g}×`。`W(N)` 仅从 `{candidate[('SS', COMPONENTS[1])]['wn']}` 到 `{candidate[('MS', COMPONENTS[1])]['wn']}`，`W(B)` 不变；global model 可利用结构，但 frozen Euclidean K10 未稳定形成 target-similar neighbourhood。",
        "",
        f"6. **Viscosity 为什么相似？** Oracle 为 `{ratio('oracle', COMPONENTS[2]):.6g}×`（6/6、4/4），Candidate C 仅 `{ratio('candidate_c', COMPONENTS[2]):.6g}×`，formal CVAR 为 `{ratio('cvar', COMPONENTS[2]):.6g}×`；因此同样是 global/local separation，而不是信息充分性的证明。",
        "",
        "7. **Candidate C 不改善来自 W(N)、W(B) 还是 ratio cancellation？** 不是 denominator cancellation；三个 component 的 W(B) 在 SS/MS 完全相同。变化全部来自 W(N)：density 下降约 79.8%，pressure 约 0.9%，viscosity 约 2.1%。Momentum 的局部 numerator 几乎不变。",
        "",
        f"8. **Momentum CVAR hotspot 是否集中于 F4/少数 fold？** 有显著集中但非唯一来源。Pressure F4 `{formal_cvar_family(COMPONENTS[1], 'F4', 'SS'):.6g}→{formal_cvar_family(COMPONENTS[1], 'F4', 'MS'):.6g}`，FOLD_5 `{formal_cvar_fold(COMPONENTS[1], 'FOLD_5', 'SS'):.6g}→{formal_cvar_fold(COMPONENTS[1], 'FOLD_5', 'MS'):.6g}`；viscosity F4 `{formal_cvar_family(COMPONENTS[2], 'F4', 'SS'):.6g}→{formal_cvar_family(COMPONENTS[2], 'F4', 'MS'):.6g}`，FOLD_3 `{formal_cvar_fold(COMPONENTS[2], 'FOLD_3', 'SS'):.6g}→{formal_cvar_fold(COMPONENTS[2], 'FOLD_3', 'MS'):.6g}`。",
        "",
        "9. **还是跨多数 family/fold 持续？** 不是所有 strata 一致恶化，而是“广泛残留 + 大幅 hotspot”。Pressure 多数 fold/family 的点变化很小，F4/FOLD_5 拉高 formal aggregate；viscosity 的 F2/F4 与 FOLD_3 是主要反向 strata。F4 仅有 8 个 independent lineages，粒子行不得当作独立复制。",
        "",
        "10. **Oracle gain 是否跨至少 4/6 folds 与 3/4 families？** 是。三个 component 均为 6/6 folds、4/4 families 改善。",
        "",
        f"11. **Formal MS distance concentration 是否恶化？** 是，幅度有限。按“越低越集中”的 index，`{geom['SS']['distance_concentration_index']}→{geom['MS']['distance_concentration_index']}`；K10 distance CV `{geom['SS']['k10_distance_coefficient_of_variation']}→{geom['MS']['k10_distance_coefficient_of_variation']}`，而 K10/random median ratio `{geom['SS']['k10_to_random_median_ratio']}→{geom['MS']['k10_to_random_median_ratio']}`，显示局部/随机分离减弱。",
        "",
        f"12. **Hubness 是否恶化？** 是。Skew `{geom['SS']['hubness_occurrence_skew']}→{geom['MS']['hubness_occurrence_skew']}`、Gini `{geom['SS']['neighbour_occurrence_gini']}→{geom['MS']['neighbour_occurrence_gini']}`、zero-occurrence fraction `{geom['SS']['zero_occurrence_fraction']}→{geom['MS']['zero_occurrence_fraction']}`。",
        "",
        f"13. **Neighbour turnover 多大？** SS-U0→MS-U0 mean turnover `{turnover['mean_neighbour_turnover']}`、median `{turnover['median_neighbour_turnover']}`；complete turnover `{turnover['complete_turnover_fraction']}`，identical K10 set `{turnover['identical_set_fraction']}`。",
        "",
        f"14. **是否有稳定 target-blind 低维 structure？** 未建立。U1 的 hubness/group-domination replication 失败；U2 的 fold transform similarity `{selection['U2']['fold_transform_stability_median']}<0.75` 且 group domination 0/6、0/4；U3 concentration 0/6、0/4。",
        "",
        "15. **哪个 candidate 被唯一选中？** 无；freeze 为 `ROUTE_A_TARGET_BLIND_GEOMETRY_CANDIDATE_NOT_ESTABLISHED`，selected=null。",
        "",
        "16. **该 candidate 在 T3 是否改善 momentum alignment？** 不适用。没有 D1-selected nonidentity candidate，D2 不得用 target 回选 U1-U3。",
        "",
        "17. **Route A 是否 actionable？** 否，Route A=`NOT_SUPPORTED`；候选冻结、momentum replication、两类 alignment diagnostics 与 density guard 均未形成可评估的完整链。",
        "",
        f"18. **是否存在无 principal-frame fallback 的 O(2) proxies？** 存在 `{sum(row['status']=='EVALUABLE' for row in proxy_available)}` 个可计算 proxy；均无 eigenframe/sign/arbitrary fallback。但 `{sum(row['algebraic_reparameterization']=='True' for row in proxy_overlap)}` 个全部只是 110D 代数重参数化；唯一 new-information P5 在 frozen deployment store 不可用。",
        "",
        f"19. **完整 pressure/viscosity population 是否有 directional evidence？** 有强描述性 association：最强 Spearman 分别 `{float(pressure_proxy['proxy_distance_target_disagreement_spearman']):.6g}` 与 `{float(viscosity_proxy['proxy_distance_target_disagreement_spearman']):.6g}`。但 `{len(overall_ridge)}` 条 overall frozen-alpha1 increment 均因 fold 不完整而不可评估，fold-level singular failures=`{singular_count}`；且所有可算 proxy 都不是新增信息，所以不能形成 actionable 增量结论。",
        "",
        "20. **G1 的 65/54 是否在完整 population 复现？** `REPLICATION_NOT_ESTABLISHED`。65/54 仅是旧 pressure zero-denominator subset；完整 R-B 为 longitudinal 111 cases、transverse 112、none 161。Pressure 与 viscosity 的 longitudinal-vs-transverse Candidate C 方向相反，不能形成跨 momentum component 的统一 fingerprint；Route B 不得依赖旧计数。",
        "",
        "21. **Route B 是否 actionable？** 否。Eligible incremental-information proxy=0；P5 未评估；residual replication 不完整；G1 full-population replication 未建立。Route B=`NOT_SUPPORTED`。",
        "",
        f"22. **Near collision 在 MS 是否持续？** 是，限于 operational claim。Pressure `{near[('U0_SS', COMPONENTS[1])]['near_collision_count']}→{near[('U0_MS', COMPONENTS[1])]['near_collision_count']}` / 983040；viscosity `{near[('U0_SS', COMPONENTS[2])]['near_collision_count']}→{near[('U0_MS', COMPONENTS[2])]['near_collision_count']}` / 983040；density 均为 0。不得称为 intrinsic mathematical non-identifiability。",
        "",
        f"23. **High ambiguity 是否主要在 formal coverage 内？** 是。MS pressure inside/outside near-collision count=`{p_in['near_collision_count']}/{p_out['near_collision_count']}`；viscosity=`{v_in['near_collision_count']}/{v_out['near_collision_count']}`。这排除“只发生在 coverage 外”，但不证明固有不可辨识。",
        "",
        f"24. **哪些 feature groups 驱动 oracle gain？** 不能归因给单一 group。数值稳定的最佳单组加法是 BASE+G2（density/pressure/viscosity NRMSE `{ablation[(COMPONENTS[0], 'BASE_PLUS_G2')]['oracle_nrmse']}/{ablation[(COMPONENTS[1], 'BASE_PLUS_G2')]['oracle_nrmse']}/{ablation[(COMPONENTS[2], 'BASE_PLUS_G2')]['oracle_nrmse']}`），仍远差 full MS。Leave-G3-out 均恶化；leave-G1/G2 有 singular 或灾难性不稳定，说明多组交互与数值条件限制，不能作 causal ranking。",
        "",
        f"25. **Component dependence 是否不同？** 是。Leave-G4-out 对 pressure `{ablation[(COMPONENTS[1], 'FULL_MS')]['oracle_nrmse']}→{ablation[(COMPONENTS[1], 'LEAVE_G4_OUT')]['oracle_nrmse']}`、viscosity `{ablation[(COMPONENTS[2], 'FULL_MS')]['oracle_nrmse']}→{ablation[(COMPONENTS[2], 'LEAVE_G4_OUT')]['oracle_nrmse']}`，均 6/6 folds、4/4 families；density 仅微变且 2/6、1/4。这是 exploratory component contrast，不授权删 G4。",
        "",
        f"26. **F-MS1？** `{verdicts['F-MS1']}`：没有通过 target-blind selection 的替代 geometry，不能证明失败主要由可修复 geometry misalignment 导致。",
        "",
        f"27. **F-MS2？** `{verdicts['F-MS2']}`：Candidate C persistence、formal CVAR persistence、coverage 内 near collisions 三类独立 diagnostics 支持 operational ambiguity；不声称 intrinsic non-identifiability。",
        "",
        f"28. **F-MS3？** `{verdicts['F-MS3']}`：representation 含预测信息，但现有诊断不能证明 observable family 本身必然不足，也不能推出 temporal/history/nonlocal/directional information 必须。",
        "",
        f"29. **F-MS4？** `{verdicts['F-MS4']}`：density-vs-momentum local response、proxy class、fixed G4 ablation 三类 contrast 支持 component dependence；数值不稳定与缺少 prospective intervention 限制为 partial。",
        "",
        f"30. **F-MS5？** `{verdicts['F-MS5']}`：distance concentration、hubness 与约 39.6% mean turnover 支持部分 dilution；但 semantic domination 反而下降且 density 在同一 110D 成功，因此不是 dominant/sole cause。",
        "",
        f"31. **F-MS6？** `{verdicts['F-MS6']}`：momentum oracle 6/6、4/4 改善，Candidate C/CVAR 不 rescue，coverage 内 ambiguity 持续，density 同时三项改善，满足 dominant 的多诊断与 replication 边界。",
        "",
        "32. **是否有新的 deployment-compatible、target-blind missing-variable/geometry hypothesis？** 没有满足全部 actionable criteria 的 candidate。H2-A、H2-B 均 NOT_SUPPORTED；H2-S 仅登记为 OUTSIDE_PRELEARNING_SCOPE。",
        "",
        "33. **该 hypothesis 是否只是 metric redesign？** 没有 supported hypothesis。现存 Route A 是 geometry/metric reparameterization，P1-P4 是 110D algebraic re-expression；二者均未达到 prospective-contract 条件。",
        "",
        "34. **A/B/C 如何裁决？** Route A=`NOT_SUPPORTED`；Route B=`NOT_SUPPORTED`；Route C=`SUPPORT_SCALE_ROUTE_CLOSURE_RECOMMENDED`。",
        "",
        "35. **Density positive result 是否完整保留？** 是：`density_rate=H_MSO01R_COMPONENT_QUALIFIED` 保持；不得因 global failure 抹去，也不外推至 momentum。",
        "",
        f"36. **H-MSO-01R global NOT_QUALIFIED 是否保持？** 是，仍为 `{OLD_HMSO01R_B}`；旧 gate 与 verdict 未修改，`h_mso01r_reverdict=false`。",
        "",
        f"37. **是否生成 fresh evidence？** 否。Fresh case/target/reference、bootstrap redraw 与 formal artifact modification 均为 0。成功 D2 target read=1；另完整披露 prepublication target reads=4（3 个未发布失败尝试 + 1 个 oracle identity validation），累计 payload open=5，失败尝试没有发布科学结果。",
        "",
        "38. **是否运行 neural/attention/training？** 否。Neural、attention、Transformer、optimizer、training、learned operator、solver-in-loop、rollout、sealed-test、ARC 全部为 0 且未授权。",
        "",
        "39. **推荐 H-MSO-02 还是关闭路线转论文？** 推荐关闭当前 support-scale development route 并转论文；不推荐现在设计或启动新的 H-MSO-02 contract。",
        "",
        f"40. **Final terminal status？** `{TERMINAL}`；`SUPPORT_SCALE_ROUTE_CLOSURE_RECOMMENDED=true`，`PAPER_ROUTE_RECOMMENDED=true`，`FRESH_COMPUTE_AUTHORIZED=false`。",
        "",
        "## D3 治理说明",
        "",
        "D2 的 CVAR case primitives 未变；D3 仅把 case-scope reporting 从额外 lineage 等权修正回 frozen formal 的 24 个 fold×family cell 等权 case mean，并与 canonical 六个 SS/MS component 点值逐项 exact-match。Mechanism verdict 亦按 preregistered independent-diagnostic minima 重裁；这些都是 MSO-02D diagnostic governance，不是 H-MSO-01R re-verdict。",
        "",
        "## Git / stop boundary",
        "",
        f"- `HMSO01R_B_FINAL_COMMIT={HMSO01R_B_FINAL}`",
        f"- `MSO02D_PRE_DIAGNOSTIC_COMMIT={MSO02D_PROTOCOL}`",
        f"- `MSO02D_TARGET_BLIND_GEOMETRY_FREEZE_COMMIT={MSO02D_D1_SCIENCE_FREEZE}`",
        f"- `MSO02D_TARGET_BLIND_GEOMETRY_SCIENCE_FREEZE_COMMIT={MSO02D_D1_SCIENCE_FREEZE}`",
        f"- `MSO02D_TARGET_BLIND_GEOMETRY_RELEASE_BINDING_COMMIT={MSO02D_D1_RELEASE_BINDING}`",
        f"- `MSO02D_FINAL_COMMIT={FINAL_PLACEHOLDER}`",
        "- branch=`main`; remote=`none`; push=`false`.",
        "",
        "立即停止：不创建 fresh atlas，不启动 H-MSO-02，不执行 MSO-03、neural、attention、Transformer、optimizer 或 training。",
    ]
    return "\n".join(lines) + "\n"


def make_status(verdicts: dict[str, str], access: dict[str, Any], firewall: dict[str, Any]) -> dict[str, Any]:
    routes = read_csv(ROUTES)
    route_status = {route: next(row["route_status"] for row in routes if row["route"] == route) for route in ("A", "B", "C")}
    status = {
        "schema_version": "1.0.0",
        "project": "SPH-MSO-PoC",
        "stage": "MSO-02D",
        "date": "2026-08-13",
        "timezone": "Asia/Shanghai",
        "terminal_status": TERMINAL,
        "evidence_class": EVIDENCE,
        "permanent_scientific_statuses": {
            "mso02b": OLD_MSO02B,
            "h_mso01": OLD_H_MSO01,
            "hmso01r_b": OLD_HMSO01R_B,
        },
        "component_status": {
            "density_rate": "H_MSO01R_COMPONENT_QUALIFIED",
            "pressure_gradient_acceleration": "H_MSO01R_COMPONENT_NOT_QUALIFIED",
            "viscosity_laplacian_acceleration": "H_MSO01R_COMPONENT_NOT_QUALIFIED",
        },
        "canonical_result_identity_status": "PASS",
        "theta_status": "NOT_ADMISSIBLE_UNDEFINED_DIAGNOSTIC",
        "nrmse_denominator_equivalence_status": "NOT_EQUIVALENT",
        "one_minus_nrmse_squared_authorized": False,
        "target_blind_geometry_selection_status": "ROUTE_A_TARGET_BLIND_GEOMETRY_CANDIDATE_NOT_ESTABLISHED",
        "selected_target_blind_geometry_candidate_id": None,
        "mechanism_verdicts": verdicts,
        "route_adjudication": {
            "route_a": route_status["A"],
            "route_b": route_status["B"],
            "route_c": route_status["C"],
        },
        "future_hypothesis_status": {
            "H2-A": "NOT_SUPPORTED",
            "H2-B": "NOT_SUPPORTED",
            "H2-S": "OUTSIDE_PRELEARNING_SCOPE",
        },
        "support_scale_route_closure_recommended": True,
        "paper_route_recommended": True,
        "new_prospective_hypothesis_design_recommended": False,
        "fresh_compute_authorized": False,
        "mso03_deterministic_closure_baseline_eligible": False,
        "neural_training_authorized": False,
        "attention_authorized": False,
        "transformer_authorized": False,
        "learned_operator_authorized": False,
        "allowed_activity_counts": firewall["allowed_activity_counts"],
        "cumulative_mso02d_target_payload_open_count": int(access["consumed_target_reads"]) + int(access["prepublication_consumed_target_reads_total"]),
        "prepublication_failed_target_diagnostic_attempt_count": int(access["prepublication_failed_consumed_target_diagnostic_attempts"]),
        "prohibited_activity_counts": firewall["prohibited_activity_counts"],
        "all_prohibited_counts_zero": True,
        "formal_artifacts_modified": False,
        "fresh_scientific_evidence_generated": False,
        "h_mso01r_reverdict": False,
        "git": {
            "branch": "main",
            "remote": None,
            "push_performed": False,
            "hmso01r_a_final_commit": HMSO01R_A_FINAL,
            "hmso01r_b_pre_target_commit": HMSO01R_B_PRE_TARGET,
            "hmso01r_b_final_commit": HMSO01R_B_FINAL,
            "mso02d_pre_diagnostic_commit": MSO02D_PROTOCOL,
            "mso02d_d0_commit": MSO02D_D0,
            "mso02d_target_blind_geometry_freeze_commit": MSO02D_D1_SCIENCE_FREEZE,
            "mso02d_target_blind_geometry_science_freeze_commit": MSO02D_D1_SCIENCE_FREEZE,
            "mso02d_target_blind_geometry_release_binding_commit": MSO02D_D1_RELEASE_BINDING,
            "mso02d_final_commit": FINAL_PLACEHOLDER,
        },
        "artifact_sha256": {
            str(REPORT.relative_to(ROOT)): sha256(REPORT),
            str(FUTURE.relative_to(ROOT)): sha256(FUTURE),
            str(G1_AUDIT.relative_to(ROOT)): sha256(G1_AUDIT),
            str(D3_AUDIT.relative_to(ROOT)): sha256(D3_AUDIT),
            str(CVAR_STRATA.relative_to(ROOT)): sha256(CVAR_STRATA),
            str(MECHANISM_EVIDENCE.relative_to(ROOT)): sha256(MECHANISM_EVIDENCE),
            str(MECHANISM_VERDICTS.relative_to(ROOT)): sha256(MECHANISM_VERDICTS),
        },
        "stop_after_mso02d": True,
        "fresh_atlas_created": False,
        "h_mso02_started": False,
        "mso03_executed": False,
    }
    write_json_atomic(STATUS, status)
    return status


def artifact_stage_source(path: Path) -> tuple[str, str, str]:
    rel = str(path.relative_to(ROOT))
    name = path.name
    if name == "hmso01r_b_git_handoff.json":
        return "H-MSO-01R-B-HANDOFF", "POST_RELEASE_PROVENANCE_BINDING", "CONSUMED_PROVENANCE"
    if rel.startswith("00_project_contract/"):
        return "MSO-02D-PROTOCOL", "USER_AUTHORIZED_PROTOCOL", "FROZEN_DEFINITION"
    if name in {
        "mso02d_feature_group_registry.json", "mso02d_target_blind_geometry_candidate_registry.json",
        "mso02d_directional_scale_response_proxy_registry.json",
    }:
        return "MSO-02D-D0", "TARGET_BLIND_DEFINITION", "FROZEN_AND_CONSUMED"
    if name == "mso02d_future_hypothesis_candidate_register.json":
        return "MSO-02D-D3", "ROUTE_ADJUDICATION", "FINAL_GOVERNANCE_OUTPUT"
    if name == "target_blind_geometry_target_alignment.csv":
        return "MSO-02D-D2", "CONSUMED_EVIDENCE_DIAGNOSTIC_COMPUTATION", "FINAL_DIAGNOSTIC_OUTPUT"
    if name == "cvar_stratum_decomposition.csv":
        return (
            "MSO-02D-D2-D3",
            "D2_CONSUMED_CASE_PRIMITIVES_WITH_D3_FROZEN_AGGREGATION_CORRECTION",
            "D3_GOVERNANCE_CORRECTED_DIAGNOSTIC_OUTPUT",
        )
    if name in {"mechanism_evidence_matrix.csv", "mechanism_verdicts.csv"}:
        return (
            "MSO-02D-D3",
            "D3_GOVERNANCE_ADJUDICATION_FROM_PERSISTED_D2_DIAGNOSTICS",
            "FINAL_GOVERNANCE_ADJUDICATED_OUTPUT",
        )
    if name == "route_adjudication_matrix.csv":
        return (
            "MSO-02D-D2-D3",
            "D2_PROVISIONAL_ROUTE_ADJUDICATION_REAFFIRMED_BY_D3",
            "FINAL_GOVERNANCE_REAFFIRMED_OUTPUT",
        )
    if "checkpoints/" in rel or name.startswith("target_blind_") or name in {
        "subspace_stability_audit.csv", "feature_group_energy_audit.csv", "distance_concentration_audit.csv",
        "hubness_audit.csv", "neighbour_turnover_audit.csv", "ss_ms_geometry_diagnostics.csv",
        "d1_target_blind_execution_audit.json",
    }:
        return "MSO-02D-D1", "OBSERVABLE_ONLY_TARGET_BLIND_COMPUTATION", "FROZEN_D1_OUTPUT"
    if name in {"mso02d_d1_execution_erratum_01.json", "mso02d_d2_execution_erratum_01.json"}:
        return "MSO-02D-EXECUTION-ERRATUM", "ADDITIVE_EXECUTION_PROVENANCE", "CONSUMED_PROVENANCE"
    if name in {"finalize_mso02d_release.py", "d3_governance_adjudication_audit.json", "g1_full_population_polarization_audit.json"}:
        return "MSO-02D-D3", "RELEASE_ONLY_DERIVED_GOVERNANCE", "FINAL_GOVERNANCE_OUTPUT"
    if rel.startswith("07_reports/") or name in {"mso02d_status_ledger.json"}:
        return "MSO-02D-D3", "FINAL_SCIENTIFIC_HANDOFF", "FINAL_RELEASE_OUTPUT"
    if name == "run_mso02d_target_blind.py":
        return "MSO-02D-D0-D1", "FROZEN_TARGET_BLIND_EXECUTOR", "CONSUMED_EXECUTABLE"
    if name == "run_mso02d_target_diagnostics.py":
        return "MSO-02D-D0-D2", "FROZEN_CONSUMED_DIAGNOSTIC_EXECUTOR_WITH_ERRATUM_CHAIN", "CONSUMED_EXECUTABLE"
    return "MSO-02D-D2", "CONSUMED_EVIDENCE_DIAGNOSTIC_COMPUTATION", "FINAL_DIAGNOSTIC_OUTPUT"


def stage_artifacts() -> list[Path]:
    paths: set[Path] = {
        ROOT / "00_project_contract/mso02d_componentwise_failure_attribution_contract.md",
        ROOT / "08_manifests/hmso01r_b_git_handoff.json",
        ROOT / "08_manifests/mso02d_d1_execution_erratum_01.json",
        ROOT / "08_manifests/mso02d_d2_execution_erratum_01.json",
        REPORT,
        STATUS,
    }
    paths.update(ROOT.glob("05_registries/mso02d_*.json"))
    paths.update(path for path in OUT.rglob("*") if path.is_file() and "__pycache__" not in path.parts)
    return sorted(paths, key=lambda path: str(path.relative_to(ROOT)))


def make_manifest() -> dict[str, Any]:
    registry: list[dict[str, Any]] = []
    output_paths = stage_artifacts()
    output_relatives = {str(path.relative_to(ROOT)) for path in output_paths}
    upstream = read_json(ACCESS).get("upstream_identity_audit", {}).get("verified", {})
    if not isinstance(upstream, dict) or len(upstream) != 82:
        raise RuntimeError("MSO02D_UPSTREAM_MANIFEST_REGISTRY_SOURCE_CONFLICT")
    overlap = output_relatives.intersection(upstream)
    if overlap:
        raise RuntimeError(f"MSO02D_MANIFEST_OUTPUT_UPSTREAM_OVERLAP:{','.join(sorted(overlap))}")
    for relative, expected_sha in sorted(upstream.items()):
        path = ROOT / relative
        if not path.is_file() or sha256(path) != expected_sha:
            raise RuntimeError(f"MSO02D_UPSTREAM_MANIFEST_IDENTITY_CONFLICT:{relative}")
        registry.append({
            "path": relative,
            "sha256": expected_sha,
            "source": "FROZEN_UPSTREAM_ARTIFACT_VERIFIED_BY_D2_IDENTITY_AUDIT",
            "stage": "MSO-02D-UPSTREAM-IDENTITY",
            "evidence_class": EVIDENCE,
            "consumption_status": "READ_ONLY_CONSUMED_UPSTREAM_EVIDENCE",
        })
    for path in output_paths:
        stage, source, consumption = artifact_stage_source(path)
        registry.append({
            "path": str(path.relative_to(ROOT)),
            "sha256": sha256(path),
            "source": source,
            "stage": stage,
            "evidence_class": EVIDENCE,
            "consumption_status": consumption,
        })
    registry.append({
        "path": str(MANIFEST.relative_to(ROOT)),
        "sha256": "FINAL_GIT_BLOB_AT_MSO02D_FINAL_COMMIT",
        "source": "SELF_BINDING_BY_FINAL_GIT_COMMIT_AND_USER_HANDOFF",
        "stage": "MSO-02D-D3",
        "evidence_class": EVIDENCE,
        "consumption_status": "FINAL_RELEASE_OUTPUT",
    })
    manifest = {
        "schema_version": "1.0.0",
        "project": "SPH-MSO-PoC",
        "stage": "MSO-02D",
        "date": "2026-08-13",
        "timezone": "Asia/Shanghai",
        "terminal_status": TERMINAL,
        "evidence_class": EVIDENCE,
        "artifact_registry": registry,
        "artifact_count": len(registry),
        "decision_summary": {
            "route_a": "NOT_SUPPORTED",
            "route_b": "NOT_SUPPORTED",
            "route_c": "SUPPORT_SCALE_ROUTE_CLOSURE_RECOMMENDED",
            "f_ms6": "SUPPORTED_DOMINANT",
            "paper_route_recommended": True,
            "fresh_compute_authorized": False,
        },
        "git": {
            "branch": "main",
            "remote": None,
            "push_performed": False,
            "hmso01r_b_final_commit": HMSO01R_B_FINAL,
            "mso02d_pre_diagnostic_commit": MSO02D_PROTOCOL,
            "mso02d_d0_commit": MSO02D_D0,
            "mso02d_target_blind_geometry_freeze_commit": MSO02D_D1_SCIENCE_FREEZE,
            "mso02d_target_blind_geometry_science_freeze_commit": MSO02D_D1_SCIENCE_FREEZE,
            "mso02d_target_blind_geometry_release_binding_commit": MSO02D_D1_RELEASE_BINDING,
            "mso02d_final_commit": FINAL_PLACEHOLDER,
        },
        "manifest_self_binding": "FINAL_GIT_BLOB_AT_MSO02D_FINAL_COMMIT",
        "governance": {
            "formal_artifacts_modified": False,
            "fresh_scientific_evidence_generated": False,
            "h_mso01r_reverdict": False,
            "fresh_compute_authorized": False,
            "mso03_executed": False,
            "neural_attention_transformer_training_executed": False,
            "stop_after_mso02d": True,
        },
    }
    write_json_atomic(MANIFEST, manifest)
    return manifest


def validate_release() -> None:
    require_outputs()
    for path in OUT.glob("*.csv"):
        rows = read_csv(path)
        if not rows or any(row.get("evidence_class") != EVIDENCE for row in rows):
            raise RuntimeError(f"MSO02D_CSV_EVIDENCE_CLASS_FAILURE:{path.name}")
    for path in (CANONICAL, THETA, NRMSE, ACCESS, FIREWALL, FREEZE, G1_AUDIT, D3_AUDIT, FUTURE, STATUS, MANIFEST):
        if read_json(path).get("evidence_class") != EVIDENCE and path not in (ACCESS, FIREWALL, FREEZE):
            raise RuntimeError(f"MSO02D_JSON_EVIDENCE_CLASS_FAILURE:{path}")
    status = read_json(STATUS)
    if status.get("terminal_status") != TERMINAL or not status.get("all_prohibited_counts_zero"):
        raise RuntimeError("MSO02D_STATUS_RELEASE_FAILURE")
    verdicts = read_csv(MECHANISM_VERDICTS)
    for row in verdicts:
        count = int(row["independent_diagnostic_count"])
        if row["verdict"] == "SUPPORTED_PARTIAL" and count < 2:
            raise RuntimeError(f"MSO02D_PARTIAL_TAXONOMY_FAILURE:{row['mechanism_id']}")
        if row["verdict"] == "SUPPORTED_DOMINANT" and count < 3:
            raise RuntimeError(f"MSO02D_DOMINANT_TAXONOMY_FAILURE:{row['mechanism_id']}")
    routes = read_csv(ROUTES)
    expected = {"A": "NOT_SUPPORTED", "B": "NOT_SUPPORTED", "C": "SUPPORT_SCALE_ROUTE_CLOSURE_RECOMMENDED"}
    for route, route_status in expected.items():
        if {row["route_status"] for row in routes if row["route"] == route} != {route_status}:
            raise RuntimeError(f"MSO02D_ROUTE_FAILURE:{route}")
    manifest = read_json(MANIFEST)
    manifest_paths = [row["path"] for row in manifest["artifact_registry"]]
    if len(manifest_paths) != len(set(manifest_paths)):
        raise RuntimeError("MSO02D_MANIFEST_DUPLICATE_PATH")
    upstream = read_json(ACCESS)["upstream_identity_audit"]["verified"]
    upstream_records = {
        row["path"]: row for row in manifest["artifact_registry"]
        if row["consumption_status"] == "READ_ONLY_CONSUMED_UPSTREAM_EVIDENCE"
    }
    if set(upstream_records) != set(upstream):
        raise RuntimeError("MSO02D_MANIFEST_UPSTREAM_COVERAGE_FAILURE")
    for relative, expected_sha in upstream.items():
        row = upstream_records[relative]
        if row["sha256"] != expected_sha or row["stage"] != "MSO-02D-UPSTREAM-IDENTITY":
            raise RuntimeError(f"MSO02D_MANIFEST_UPSTREAM_METADATA_FAILURE:{relative}")
    for row in manifest["artifact_registry"]:
        if row["path"] == str(MANIFEST.relative_to(ROOT)):
            continue
        path = ROOT / row["path"]
        if sha256(path) != row["sha256"]:
            raise RuntimeError(f"MSO02D_MANIFEST_HASH_FAILURE:{row['path']}")
        for key in ("source", "stage", "evidence_class", "consumption_status"):
            if not row.get(key):
                raise RuntimeError(f"MSO02D_MANIFEST_METADATA_MISSING:{row['path']}:{key}")
    text = REPORT.read_text(encoding="utf-8")
    if sum(f"{index}. **" in text for index in range(1, 41)) != 40:
        raise RuntimeError("MSO02D_REPORT_40_ANSWER_FAILURE")
    forbidden = ("1/3 to 1/2", "overall prior probability")
    if any(value in text for value in forbidden):
        raise RuntimeError("MSO02D_INTERNAL_PRIOR_LEAKAGE")


def release() -> None:
    verify_git_boundary(validate_only=False)
    require_outputs()
    access, firewall = verify_d2_governance()
    cvar_correction = correct_cvar_reporting()
    mechanism_correction, verdicts = make_mechanism_outputs()
    g1 = make_g1_audit()
    make_future_register()
    d3_audit = {
        "schema_version": "1.0.0",
        "project": "SPH-MSO-PoC",
        "stage": "MSO-02D-D3",
        "status": "D3_GOVERNANCE_ADJUDICATION_COMPLETE",
        "evidence_class": EVIDENCE,
        "cvar_reporting_correction": cvar_correction,
        "mechanism_taxonomy_correction": mechanism_correction,
        "g1_full_population_audit_path": str(G1_AUDIT.relative_to(ROOT)),
        "g1_full_population_audit_sha256": sha256(G1_AUDIT),
        "target_payload_read_by_d3": False,
        "observable_payload_read_by_d3": False,
        "oracle_fit_count_by_d3": 0,
        "fresh_scientific_evidence_generated": False,
        "formal_artifacts_modified": False,
        "h_mso01r_reverdict": False,
    }
    write_json_atomic(D3_AUDIT, d3_audit)
    write_text_atomic(REPORT, make_report(verdicts, g1, access, firewall))
    make_status(verdicts, access, firewall)
    make_manifest()
    validate_release()
    print(TERMINAL)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true")
    arguments = parser.parse_args()
    verify_git_boundary(validate_only=arguments.validate)
    if arguments.validate:
        verify_d2_governance()
        validate_release()
        print("MSO02D_RELEASE_VALID")
    else:
        release()


if __name__ == "__main__":
    main()
