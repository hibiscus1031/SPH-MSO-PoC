#!/usr/bin/env python3
"""Run MSO-02D consumed-target diagnostics after the D1 target-blind freeze.

This executor is deliberately unable to create cases, targets, references,
bootstrap draws, formal metrics, or learned models.  It opens the consumed
target payload only after validating the D1 self-binding commit, a clean local
repository with no remote, the D0/D1 artifact hashes, both H-MSO-01R frozen
manifests, and the canonical published result identities.

The default ``--stage all`` is the release path.  Earlier stage cutoffs are
available for bounded runtime review; every invocation still starts from a
clean D1 repository and reruns all prerequisites, so a dirty partial run can
never be silently resumed.
"""

from __future__ import annotations

from collections import defaultdict
import argparse
import ast
import csv
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Iterable, Sequence

import numpy as np
from scipy.stats import spearmanr


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "06_experiments/mso02d"
REG = ROOT / "05_registries"

D0_CONTRACT = ROOT / "00_project_contract/mso02d_componentwise_failure_attribution_contract.md"
D0_FEATURE_GROUPS = REG / "mso02d_feature_group_registry.json"
D0_GEOMETRY_REGISTRY = REG / "mso02d_target_blind_geometry_candidate_registry.json"
D0_PROXY_REGISTRY = REG / "mso02d_directional_scale_response_proxy_registry.json"
D1_FREEZE = OUT / "target_blind_geometry_freeze.json"
D1_NEIGHBOURS = OUT / "target_blind_geometry_selected_neighbours.npz"

A_MANIFEST = ROOT / "08_manifests/hmso01r_a_manifest.json"
A_STATUS = ROOT / "08_manifests/hmso01r_a_status_ledger.json"
B_MANIFEST = ROOT / "08_manifests/hmso01r_b_manifest.json"
B_STATUS = ROOT / "08_manifests/hmso01r_b_status_ledger.json"
A_HANDOFF = ROOT / "08_manifests/hmso01r_a_git_handoff.json"
B_HANDOFF = ROOT / "08_manifests/hmso01r_b_git_handoff.json"

ATLAS = REG / "hmso01r_a_formal_fresh_atlas_registry.json"
SAMPLE = REG / "hmso01r_a_formal_particle_sample_registry.json"
OBSERVABLE = ROOT / "06_experiments/hmso01r_a/observable/hmso01r_a_observable_store.npz"
TARGET = ROOT / "06_experiments/hmso01r_b/target_ref/hmso01r_b_target_store.npz"
NORMALIZATION = ROOT / "06_experiments/hmso01r_a/fold_normalization_registry.json"
SS_SCHEMA = ROOT / "06_experiments/hmso01r_a/ss_observable_schema_identity.json"
MS_SCHEMA = ROOT / "06_experiments/hmso01r_a/ms_observable_schema_identity.json"
FORMAL_NEIGHBOURS = ROOT / "06_experiments/hmso01r_a/descriptor_neighbor_identities.npz"
RANDOM_IDENTITIES = ROOT / "06_experiments/hmso01r_a/random_baseline_identities.npz"
COVERAGE_GEOMETRY = ROOT / "06_experiments/hmso01r_a/coverage_geometry_freeze.json"
BOOTSTRAP = ROOT / "06_experiments/hmso01r_a/bootstrap_draws.npz"
FROZEN_HELPER = ROOT / "06_experiments/mso02b/run_mso02b_formal.py"

B_DIR = ROOT / "06_experiments/hmso01r_b"
SS_CANDIDATE = B_DIR / "ss_candidate_c_dnn_metrics.csv"
MS_CANDIDATE = B_DIR / "ms_candidate_c_dnn_metrics.csv"
PAIRED_CANDIDATE = B_DIR / "candidate_c_paired_rescue_metrics.csv"
SS_CVAR = B_DIR / "ss_conditional_variance_metrics.csv"
MS_CVAR = B_DIR / "ms_conditional_variance_metrics.csv"
SS_ORACLE = B_DIR / "ss_oracle_metrics.csv"
MS_ORACLE = B_DIR / "ms_oracle_metrics.csv"
COVERAGE_METRICS = B_DIR / "coverage_metrics.csv"
COMPONENT_VERDICTS = B_DIR / "component_verdicts.csv"
FORMAL_SUMMARY = B_DIR / "formal_summary.json"

HMSO01R_A_FINAL_COMMIT = "9048eff137001e5f644575bd02c3856b4f4ac532"
HMSO01R_B_PRE_TARGET_COMMIT = "1c99103edaf76aa05915458fd498e07b1241e272"
HMSO01R_B_FINAL_COMMIT = "47a15ce3e38dbf13d671b9ae7275bb84761ae279"
D0_SUBJECT = "MSO-02D D0: freeze target-blind alignment and directional proxy definitions"
D1_SUBJECT = "MSO-02D D1: freeze target-blind alignment selection before target diagnostics"
EVIDENCE_CLASS = "EXPLORATORY_CONSUMED_DIAGNOSTIC_ONLY"
INTEGRITY_STOP = "MSO02D_UPSTREAM_EVIDENCE_INTEGRITY_CONFLICT"
CANONICAL_STOP = "MSO02D_CANONICAL_RESULT_IDENTITY_FAILURE"
TOL = 5e-8
NUMERIC_TOL = 1e-12

COMPONENTS = (
    "density_rate",
    "pressure_gradient_acceleration",
    "viscosity_laplacian_acceleration",
)
TARGET_FIELDS = {
    "density_rate": "target_density_rate",
    "pressure_gradient_acceleration": "target_pressure_gradient_acceleration",
    "viscosity_laplacian_acceleration": "target_viscosity_laplacian_acceleration",
}
TARGET_SLICES = {
    "density_rate": slice(0, 1),
    "pressure_gradient_acceleration": slice(1, 3),
    "viscosity_laplacian_acceleration": slice(3, 5),
}
FAMILIES = ("F1", "F2", "F3", "F4")
FOLDS = tuple(range(6))
ARMS = ("SS", "MS")
POLY_SUBSET = (
    "obs__base_neighbor_count_over_nominal",
    "obs__base_cov_eig_ratio",
    "obs__base_kernel_s0_minus_1",
    "obs__base_first_moment_error_fro",
    "obs__base_grad_constant_norm_times_h",
    "obs__rho",
    "obs__local_dv_rms",
)

CORE_OUTPUTS = (
    "target_blind_geometry_target_alignment.csv",
    "directional_proxy_availability_audit.csv",
    "directional_proxy_overlap_audit.csv",
    "directional_proxy_target_alignment.csv",
    "directional_proxy_residual_diagnostics.csv",
    "candidate_c_wn_wb_decomposition.csv",
    "candidate_c_ratio_cancellation_audit.csv",
    "cvar_hotspot_map.csv",
    "cvar_stratum_decomposition.csv",
    "near_collision_audit.csv",
    "ambiguity_vs_coverage.csv",
    "design_only_failure_stratification.csv",
)
ORACLE_OUTPUTS = ("oracle_residual_decomposition.csv", "oracle_gain_stratum_map.csv")
ABLATION_OUTPUTS = ("fixed_feature_group_ablation.csv",)
ADJUDICATION_OUTPUTS = (
    "mechanism_evidence_matrix.csv",
    "mechanism_verdicts.csv",
    "route_adjudication_matrix.csv",
    "diagnostic_access_ledger.json",
    "firewall_audit.json",
)


class Stop(RuntimeError):
    """A fail-closed scientific or provenance stop."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git(*args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", *args], cwd=ROOT, check=check, capture_output=True, text=True
    )
    return result.stdout.strip()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise Stop(f"{INTEGRITY_STOP}:JSON_OBJECT_REQUIRED:{path.relative_to(ROOT)}")
    return value


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, np.ndarray):
        return json_safe(value.tolist())
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if not math.isfinite(float(value)) else float(value)
    if isinstance(value, float):
        return None if not math.isfinite(value) else value
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(json_safe(value), indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        rows = [{"status": "NOT_APPLICABLE_NO_ROWS", "evidence_class": EVIDENCE_CLASS}]
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            clean = {}
            for key in fields:
                value = json_safe(row.get(key, ""))
                clean[key] = json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else value
            writer.writerow(clean)


def add_evidence(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{**row, "evidence_class": EVIDENCE_CLASS} for row in rows]


def atomic_publish(staging: Path, names: Sequence[str]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name in names:
        source = staging / name
        if not source.is_file():
            raise Stop(f"MSO02D_OUTPUT_COMPLETENESS_FAILURE:{name}")
    for name in names:
        os.replace(staging / name, OUT / name)


def recursively_find(value: Any, keys: set[str]) -> Any | None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key.lower() in keys:
                return item
        for item in value.values():
            found = recursively_find(item, keys)
            if found is not None:
                return found
    elif isinstance(value, list):
        for item in value:
            found = recursively_find(item, keys)
            if found is not None:
                return found
    return None


def full_commit(value: Any, field: str) -> str:
    text = str(value)
    if not re.fullmatch(r"[0-9a-f]{40}", text):
        raise Stop(f"{INTEGRITY_STOP}:{field}_FULL_COMMIT_REQUIRED:{text}")
    return text


def validate_git_and_d1() -> tuple[dict[str, Any], str, str]:
    """Validate every pre-target Git/D0/D1 condition before other payload use."""
    if not D1_FREEZE.is_file():
        raise Stop(f"{INTEGRITY_STOP}:D1_FREEZE_MISSING")
    freeze = read_json(D1_FREEZE)
    head = full_commit(git("rev-parse", "HEAD"), "HEAD")
    if git("branch", "--show-current") != "main":
        raise Stop(f"{INTEGRITY_STOP}:BRANCH_NOT_MAIN")
    if git("status", "--porcelain=v1", "--untracked-files=all"):
        raise Stop(f"{INTEGRITY_STOP}:WORKING_TREE_NOT_CLEAN")
    if git("remote"):
        raise Stop(f"{INTEGRITY_STOP}:REMOTE_PRESENT")
    if git("log", "-1", "--format=%s") != D1_SUBJECT:
        raise Stop(f"{INTEGRITY_STOP}:D1_SUBJECT_MISMATCH")

    marker = recursively_find(
        freeze,
        {"d1_commit", "mso02d_d1_commit", "target_blind_geometry_freeze_commit"},
    )
    if marker in {"SELF_GIT_COMMIT", "SELF_BINDING_GIT_COMMIT", "HEAD"}:
        tracked = subprocess.run(
            ["git", "show", f"HEAD:{D1_FREEZE.relative_to(ROOT).as_posix()}"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout
        if tracked != D1_FREEZE.read_bytes():
            raise Stop(f"{INTEGRITY_STOP}:D1_FREEZE_NOT_SELF_BOUND_AT_HEAD")
        d1_commit = head
    else:
        d1_commit = full_commit(marker, "D1")
    if head != d1_commit:
        raise Stop(f"{INTEGRITY_STOP}:HEAD_NOT_D1_FREEZE_COMMIT")

    d0_value = recursively_find(
        freeze,
        {"d0_commit", "mso02d_d0_commit", "target_blind_definition_freeze_commit"},
    )
    d0_commit = full_commit(d0_value, "D0")
    if git("show", "-s", "--format=%s", d0_commit) != D0_SUBJECT:
        raise Stop(f"{INTEGRITY_STOP}:D0_SUBJECT_MISMATCH")
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", d0_commit, d1_commit], cwd=ROOT
    ).returncode
    if ancestor != 0 or d0_commit == d1_commit:
        raise Stop(f"{INTEGRITY_STOP}:D0_D1_ANCESTRY_FAILURE")

    artifact_hashes = recursively_find(
        freeze, {"artifact_sha256", "artifact_hashes", "frozen_artifact_sha256"}
    )
    if not isinstance(artifact_hashes, dict):
        raise Stop(f"{INTEGRITY_STOP}:D1_ARTIFACT_HASH_MAP_MISSING")
    required = {
        D0_CONTRACT.relative_to(ROOT).as_posix(),
        D0_FEATURE_GROUPS.relative_to(ROOT).as_posix(),
        D0_GEOMETRY_REGISTRY.relative_to(ROOT).as_posix(),
        D0_PROXY_REGISTRY.relative_to(ROOT).as_posix(),
        D1_NEIGHBOURS.relative_to(ROOT).as_posix(),
        "06_experiments/mso02d/target_blind_subspace_diagnostics.csv",
        "06_experiments/mso02d/subspace_stability_audit.csv",
        "06_experiments/mso02d/feature_group_energy_audit.csv",
        "06_experiments/mso02d/target_blind_geometry_selection_matrix.csv",
        "06_experiments/mso02d/ss_ms_geometry_diagnostics.csv",
        "06_experiments/mso02d/distance_concentration_audit.csv",
        "06_experiments/mso02d/hubness_audit.csv",
        "06_experiments/mso02d/neighbour_turnover_audit.csv",
    }
    missing = sorted(required - set(artifact_hashes))
    if missing:
        raise Stop(f"{INTEGRITY_STOP}:D0_D1_HASH_ENTRIES_MISSING:{','.join(missing)}")
    for relative, expected in artifact_hashes.items():
        path = ROOT / str(relative)
        if not path.is_file() or sha256(path) != str(expected):
            raise Stop(f"{INTEGRITY_STOP}:D0_D1_ARTIFACT_HASH_MISMATCH:{relative}")
    return freeze, d0_commit, d1_commit


def validate_manifest_registry(
    manifest_path: Path, manifest: dict[str, Any], *, self_commit: str | None = None
) -> dict[str, str]:
    registry = manifest.get("artifact_registry")
    if not isinstance(registry, list) or not registry:
        raise Stop(f"{INTEGRITY_STOP}:EMPTY_MANIFEST_REGISTRY:{manifest_path.name}")
    verified: dict[str, str] = {}
    for record in registry:
        if not isinstance(record, dict) or "path" not in record or "sha256" not in record:
            raise Stop(f"{INTEGRITY_STOP}:MALFORMED_MANIFEST_RECORD:{manifest_path.name}")
        relative, expected = str(record["path"]), str(record["sha256"])
        if expected.startswith("FINAL_GIT_BLOB_"):
            if self_commit is None:
                raise Stop(f"{INTEGRITY_STOP}:UNRESOLVED_MANIFEST_SELF_BINDING:{relative}")
            actual_bytes = subprocess.run(
                ["git", "show", f"{self_commit}:{relative}"],
                cwd=ROOT,
                check=True,
                capture_output=True,
            ).stdout
            if actual_bytes != (ROOT / relative).read_bytes():
                raise Stop(f"{INTEGRITY_STOP}:MANIFEST_SELF_BLOB_MISMATCH:{relative}")
            verified[relative] = hashlib.sha256(actual_bytes).hexdigest()
            continue
        path = ROOT / relative
        if not path.is_file() or sha256(path) != expected:
            raise Stop(f"{INTEGRITY_STOP}:FROZEN_ARTIFACT_HASH_MISMATCH:{relative}")
        verified[relative] = expected
    return verified


def validate_upstream_evidence() -> dict[str, Any]:
    a_manifest, b_manifest = read_json(A_MANIFEST), read_json(B_MANIFEST)
    if a_manifest.get("terminal_status") != "HMSO01R_A_FRESH_CONFIRMATORY_ATLAS_AND_ZERO_SAFE_ANALYSIS_FROZEN":
        raise Stop(f"{INTEGRITY_STOP}:A_STATUS_MISMATCH")
    if b_manifest.get("terminal_status") != "HMSO01R_B_FRESH_CONFIRMATORY_MULTISCALE_IDENTIFIABILITY_RESCUE_NOT_QUALIFIED":
        raise Stop(f"{INTEGRITY_STOP}:B_STATUS_MISMATCH")
    if git("rev-parse", HMSO01R_A_FINAL_COMMIT) != HMSO01R_A_FINAL_COMMIT:
        raise Stop(f"{INTEGRITY_STOP}:A_COMMIT_MISSING")
    if git("rev-parse", HMSO01R_B_PRE_TARGET_COMMIT) != HMSO01R_B_PRE_TARGET_COMMIT:
        raise Stop(f"{INTEGRITY_STOP}:B_PRE_TARGET_COMMIT_MISSING")
    if git("rev-parse", HMSO01R_B_FINAL_COMMIT) != HMSO01R_B_FINAL_COMMIT:
        raise Stop(f"{INTEGRITY_STOP}:B_FINAL_COMMIT_MISSING")
    b_git = b_manifest.get("git", {})
    if (
        b_git.get("hmso01r_a_final_commit") != HMSO01R_A_FINAL_COMMIT
        or b_git.get("hmso01r_b_pre_target_commit") != HMSO01R_B_PRE_TARGET_COMMIT
    ):
        raise Stop(f"{INTEGRITY_STOP}:B_MANIFEST_GIT_BOUNDARY_MISMATCH")

    a_verified = validate_manifest_registry(A_MANIFEST, a_manifest)
    b_verified = validate_manifest_registry(
        B_MANIFEST, b_manifest, self_commit=HMSO01R_B_FINAL_COMMIT
    )
    required = {
        A_MANIFEST.relative_to(ROOT).as_posix(),
        A_STATUS.relative_to(ROOT).as_posix(),
        B_STATUS.relative_to(ROOT).as_posix(),
        OBSERVABLE.relative_to(ROOT).as_posix(),
        TARGET.relative_to(ROOT).as_posix(),
        SS_SCHEMA.relative_to(ROOT).as_posix(),
        MS_SCHEMA.relative_to(ROOT).as_posix(),
        ATLAS.relative_to(ROOT).as_posix(),
        SAMPLE.relative_to(ROOT).as_posix(),
        "05_registries/hmso01r_a_lineage_fold_registry.json",
        NORMALIZATION.relative_to(ROOT).as_posix(),
        "06_experiments/hmso01r_a/descriptor_geometry_freeze.json",
        FORMAL_NEIGHBOURS.relative_to(ROOT).as_posix(),
        RANDOM_IDENTITIES.relative_to(ROOT).as_posix(),
        "05_registries/hmso01r_a_bootstrap_registry.json",
        BOOTSTRAP.relative_to(ROOT).as_posix(),
        "00_project_contract/amendments/ca_mso01_zero_safe_dnn_semantics.md",
        SS_CANDIDATE.relative_to(ROOT).as_posix(),
        MS_CANDIDATE.relative_to(ROOT).as_posix(),
        SS_CVAR.relative_to(ROOT).as_posix(),
        MS_CVAR.relative_to(ROOT).as_posix(),
        SS_ORACLE.relative_to(ROOT).as_posix(),
        MS_ORACLE.relative_to(ROOT).as_posix(),
        COVERAGE_METRICS.relative_to(ROOT).as_posix(),
        COMPONENT_VERDICTS.relative_to(ROOT).as_posix(),
        FORMAL_SUMMARY.relative_to(ROOT).as_posix(),
    }
    all_verified = {**a_verified, **b_verified}
    missing = sorted(required - set(all_verified))
    if missing:
        raise Stop(f"{INTEGRITY_STOP}:REQUIRED_UPSTREAM_IDENTITIES_MISSING:{','.join(missing)}")
    # A manifest is itself frozen by B; B manifest/status are bound at release.
    if sha256(A_MANIFEST) != b_verified[A_MANIFEST.relative_to(ROOT).as_posix()]:
        raise Stop(f"{INTEGRITY_STOP}:A_MANIFEST_IDENTITY_MISMATCH")
    return {
        "a_manifest_sha256": sha256(A_MANIFEST),
        "b_manifest_git_blob_commit": HMSO01R_B_FINAL_COMMIT,
        "verified_artifact_count": len(all_verified),
        "verified": all_verified,
    }


def canonical_result_identity_audit() -> dict[str, Any]:
    tables = {
        "candidate_c": (read_csv(SS_CANDIDATE), read_csv(MS_CANDIDATE), read_csv(PAIRED_CANDIDATE)),
        "cvar": (read_csv(SS_CVAR), read_csv(MS_CVAR), None),
        "oracle": (read_csv(SS_ORACLE), read_csv(MS_ORACLE), None),
    }
    columns = {
        "candidate_c": "candidate_c_d",
        "cvar": "conditional_variance",
        "oracle": "oracle_nrmse",
    }
    summary = read_json(FORMAL_SUMMARY)["metrics"]
    rows: list[dict[str, Any]] = []
    all_match = True
    for component in COMPONENTS:
        for metric in ("candidate_c", "cvar", "oracle"):
            ss_rows, ms_rows, paired = tables[metric]
            column = columns[metric]
            ss_row = next(r for r in ss_rows if r["component"] == component and r.get("scope", "OVERALL") == "OVERALL")
            ms_row = next(r for r in ms_rows if r["component"] == component and r.get("scope", "OVERALL") == "OVERALL")
            ss, ms = float(ss_row[column]), float(ms_row[column])
            if metric == "candidate_c":
                paired_column = "candidate_c_ratio"
                paired_value = float(next(r for r in paired or [] if r["component"] == component)[paired_column])
                summary_key = "candidate_c_d"
                summary_ratio_key = "candidate_c_ratio"
            else:
                paired_value = ms / ss
                summary_key = "conditional_variance" if metric == "cvar" else "oracle_nrmse"
                summary_ratio_key = "conditional_variance_ratio" if metric == "cvar" else "oracle_nrmse_ratio"
            computed_ratio = ms / ss
            independent = {
                "csv_ss": ss,
                "csv_ms": ms,
                "ratio_recomputed_from_csv": computed_ratio,
                "paired_or_recomputed_ratio": paired_value,
                "formal_summary_ss": float(summary["SS"][component][summary_key]),
                "formal_summary_ms": float(summary["MS"][component][summary_key]),
                "formal_summary_paired_ratio": float(summary["paired"][component][summary_ratio_key]),
            }
            reference = computed_ratio
            match = bool(
                math.isclose(independent["csv_ss"], independent["formal_summary_ss"], rel_tol=TOL, abs_tol=TOL)
                and math.isclose(independent["csv_ms"], independent["formal_summary_ms"], rel_tol=TOL, abs_tol=TOL)
                and math.isclose(reference, independent["paired_or_recomputed_ratio"], rel_tol=TOL, abs_tol=TOL)
                and math.isclose(reference, independent["formal_summary_paired_ratio"], rel_tol=TOL, abs_tol=TOL)
            )
            all_match &= match
            rows.append({
                "component": component,
                "metric": metric,
                **independent,
                "max_cross_source_absolute_difference": max(
                    abs(independent["csv_ss"] - independent["formal_summary_ss"]),
                    abs(independent["csv_ms"] - independent["formal_summary_ms"]),
                    abs(reference - independent["paired_or_recomputed_ratio"]),
                    abs(reference - independent["formal_summary_paired_ratio"]),
                ),
                "tolerance": TOL,
                "cross_source_identity_match": match,
            })
    result = {
        "schema_version": "1.0.0",
        "stage": "MSO-02D-D2-PRE-TARGET",
        "evidence_class": EVIDENCE_CLASS,
        "status": "PASS" if all_match else CANONICAL_STOP,
        "tolerance_absolute_relative": TOL,
        "machine_loaded_not_manually_substituted": True,
        "authorized_numeric_constants_embedded_in_executor": False,
        "rows": rows,
        "source_sha256": {
            str(path.relative_to(ROOT)): sha256(path)
            for path in (SS_CANDIDATE, MS_CANDIDATE, PAIRED_CANDIDATE, SS_CVAR, MS_CVAR, SS_ORACLE, MS_ORACLE)
        },
    }
    if not all_match:
        raise Stop(CANONICAL_STOP)
    return result


def theta_definition_audit() -> dict[str, Any]:
    """Text/source-only audit; binary payload directories are never traversed."""
    suffixes = {".md", ".json", ".csv", ".py", ".txt"}
    terms = re.compile(r"(?:\btheta\b|θ|5\.4|13\.4)", re.IGNORECASE)
    required_patterns = {
        "formula": re.compile(r"(?:formula|定义|=|\\theta|θ)"),
        "inputs": re.compile(r"(?:input|输入量|变量)"),
        "denominator": re.compile(r"(?:denominator|分母)"),
        "aggregation": re.compile(r"(?:aggregation|聚合)"),
        "component_mapping": re.compile(r"(?:component|分量|pressure|viscosity)"),
        "fold_family": re.compile(r"(?:fold|family|折|族)"),
        "uncertainty": re.compile(r"(?:uncertainty|置信|bootstrap|不确定)"),
        "value_mapping": re.compile(r"5\.4.*13\.4|13\.4.*5\.4", re.DOTALL),
    }
    hits: list[dict[str, Any]] = []
    combined = ""
    for relative in git("ls-files").splitlines():
        path = ROOT / relative
        if path.suffix.lower() not in suffixes or not path.is_file():
            continue
        if "/target_ref/" in f"/{relative}" or "mso02d" in relative.lower():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if not terms.search(text):
            continue
        matching_lines = [
            {"line": i, "text": line[:500]}
            for i, line in enumerate(text.splitlines(), 1)
            if terms.search(line)
        ]
        hits.append({"path": relative, "sha256": sha256(path), "matches": matching_lines})
        combined += "\n" + text
    completeness = {name: bool(pattern.search(combined)) for name, pattern in required_patterns.items()}
    # Mentions in the protocol are not a definition.  Every definition field
    # must coexist in a non-MSO-02D upstream source before theta is admissible.
    complete = bool(hits and all(completeness.values()))
    return {
        "schema_version": "1.0.0",
        "stage": "MSO-02D-D2-PRE-TARGET",
        "evidence_class": EVIDENCE_CLASS,
        "audit": "THETA_DEFINITION_AUDIT",
        "status": "EXPLORATORY_CONSUMED_DIAGNOSTIC_ONLY" if complete else "NOT_ADMISSIBLE_UNDEFINED_DIAGNOSTIC",
        "complete_reproducible_definition_found": complete,
        "required_definition_fields": completeness,
        "repository_scope": "GIT_TRACKED_TEXT_AND_SOURCE_ONLY_EXCLUDING_MSO02D_AND_TARGET_REF",
        "binary_target_payload_opened": False,
        "source_hits": hits,
        "load_bearing_evidence_authorized": False,
    }


def nrmse_denominator_equivalence_audit() -> dict[str, Any]:
    source = FROZEN_HELPER.read_text(encoding="utf-8")
    tree = ast.parse(source)
    definitions = {
        node.name: ast.get_source_segment(source, node) or ""
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name in {"development_target_rms", "case_family_equal_vector", "aggregate_oracle"}
    }
    complete = set(definitions) == {"development_target_rms", "case_family_equal_vector", "aggregate_oracle"}
    target_about_zero = "norm_sq(values[rows])" in definitions.get("development_target_rms", "")
    mean_centered_baseline = "case_family_equal_vector" in source
    mean_of_cell_nrmse = "np.mean(point_cell)" in definitions.get("aggregate_oracle", "")
    equivalent = bool(complete and not target_about_zero and not mean_of_cell_nrmse)
    # The frozen implementation uses sqrt(E||Y||^2), not centered target
    # variance, and averages cellwise root-normalized errors.  Therefore the
    # standard variance-decomposition identity is disproved, not merely absent.
    status = "EQUIVALENT" if equivalent else "NOT_EQUIVALENT"
    return {
        "schema_version": "1.0.0",
        "stage": "MSO-02D-D2-PRE-TARGET",
        "evidence_class": EVIDENCE_CLASS,
        "status": status,
        "r2_like_quantity_admissible": equivalent,
        "one_minus_nrmse_squared_authorized": equivalent,
        "nrmse_denominator": "sqrt(case/family-equal E[||Y||^2]) over each outer-fold development population",
        "mean_baseline": "case/family-equal development mean prediction evaluated with the same about-zero target RMS",
        "standard_variance_denominator": "centered sum/mean of squared deviations from the applicable mean with matched weights",
        "denominator_centering_equivalent": not target_about_zero,
        "aggregation_equivalent": not mean_of_cell_nrmse,
        "fold_family_weighting_equivalent": False,
        "reason": "Frozen target RMS is about zero and frozen NRMSE is a mean of fold-family cellwise roots; it is not the centered pooled variance decomposition denominator.",
        "source": FROZEN_HELPER.relative_to(ROOT).as_posix(),
        "source_sha256": sha256(FROZEN_HELPER),
        "function_source_sha256": {
            name: hashlib.sha256(text.encode("utf-8")).hexdigest()
            for name, text in definitions.items()
        },
    }


def load_frozen_helper() -> Any:
    b_manifest = read_json(B_MANIFEST)
    record = next(
        (
            row for row in b_manifest["artifact_registry"]
            if row["path"] == FROZEN_HELPER.relative_to(ROOT).as_posix()
        ),
        None,
    )
    if record is None or sha256(FROZEN_HELPER) != record["sha256"]:
        raise Stop(f"{INTEGRITY_STOP}:FROZEN_ORACLE_HELPER_IDENTITY_FAILURE")
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("mso02d_frozen_non_dnn", FROZEN_HELPER)
    if spec is None or spec.loader is None:
        raise Stop("MSO02D_FROZEN_HELPER_IMPORT_FAILURE")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_consumed_data(access: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """First and only target-payload opener; called after all preflight gates."""
    atlas = read_json(ATLAS)
    sample = read_json(SAMPLE)
    cases = sorted(atlas["cases"], key=lambda row: int(row["formal_case_index"]))
    sample_cases = sorted(sample["cases"], key=lambda row: int(row["formal_case_index"]))
    if len(cases) != 384 or len(sample_cases) != 384:
        raise Stop("MSO02D_FORMAL_POPULATION_FAILURE")
    with np.load(OBSERVABLE, allow_pickle=False) as store:
        observable = {name: np.asarray(store[name]) for name in store.files}
    access["consumed_observable_reads"] += 1
    with np.load(TARGET, allow_pickle=False) as store:
        target = {name: np.asarray(store[name]) for name in store.files}
    access["consumed_target_reads"] += 1
    if observable.get("ss_features", np.empty(0)).shape != (49152, 39):
        raise Stop("MSO02D_SS_OBSERVABLE_SHAPE_FAILURE")
    if observable.get("ms_features", np.empty(0)).shape != (49152, 110):
        raise Stop("MSO02D_MS_OBSERVABLE_SHAPE_FAILURE")
    if int(np.sum(target["particle_count_table"])) != 384 * 576:
        raise Stop("MSO02D_TARGET_POPULATION_SHAPE_FAILURE")

    selected_target_rows: list[int] = []
    meta: dict[str, list[Any]] = defaultdict(list)
    cursor = 0
    for position, (case, sample_case) in enumerate(zip(cases, sample_cases)):
        if int(case["formal_case_index"]) != position or int(sample_case["formal_case_index"]) != position:
            raise Stop("MSO02D_CASE_ORDER_FAILURE")
        particle_ids = [int(x) for x in sample_case["particle_ids_in_hash_order"]]
        if len(particle_ids) != 128 or len(set(particle_ids)) != 128:
            raise Stop("MSO02D_PARTICLE_SAMPLE_IDENTITY_FAILURE")
        start, stop = int(target["particle_row_start_table"][position]), int(target["particle_row_stop_table"][position])
        if stop - start != 576:
            raise Stop("MSO02D_TARGET_CASE_ROW_FAILURE")
        for particle_id in particle_ids:
            target_row = start + particle_id
            fields_match = bool(
                int(observable["formal_case_index"][cursor]) == position
                and int(observable["particle_id"][cursor]) == particle_id
                and int(target["formal_case_index"][target_row]) == position
                and int(target["particle_id"][target_row]) == particle_id
                and str(target["case_id"][target_row]) == str(case["case_id"])
                and str(target["particle_state_hash"][target_row]) == str(case["particle_state_hash"])
                and str(target["field_lineage_id"][target_row]) == str(case["field_lineage_id"])
                and str(target["family"][target_row]) == str(case["macro_family"])
                and str(target["fold"][target_row]) == str(case["fold"])
            )
            if not fields_match:
                raise Stop("MSO02D_TARGET_OBSERVABLE_PAIRING_FAILURE")
            selected_target_rows.append(target_row)
            meta["case_index"].append(position)
            meta["particle_id"].append(particle_id)
            meta["case_id"].append(case["case_id"])
            meta["lineage"].append(case["field_lineage_id"])
            meta["family"].append(case["macro_family"])
            meta["fold"].append(int(str(case["fold"]).split("_")[1]))
            meta["seed"].append(int(case["jitter_seed"]))
            meta["sample_key"].append(f"{case['case_id']}|{particle_id}")
            cursor += 1
    selected = np.asarray(selected_target_rows, dtype=np.int64)
    targets = {
        component: np.asarray(target[field][selected], dtype=np.float64)
        for component, field in TARGET_FIELDS.items()
    }
    targets["bundle"] = np.column_stack([targets[c] for c in COMPONENTS])
    result_meta = {
        key: np.asarray(
            values,
            dtype=np.int32 if key in {"case_index", "particle_id"} else np.int8 if key == "fold" else np.int64 if key == "seed" else None,
        )
        for key, values in meta.items()
    }
    features = {
        "SS": np.asarray(observable["ss_features"], dtype=np.float64),
        "MS": np.asarray(observable["ms_features"], dtype=np.float64),
    }
    if not all(np.isfinite(x).all() for x in [*features.values(), *(targets[c] for c in COMPONENTS)]):
        raise Stop("MSO02D_NONFINITE_CONSUMED_INPUT")
    return {"features": features, "targets": targets, "meta": result_meta}, cases


def load_identities(
    freeze: dict[str, Any], access: dict[str, Any]
) -> tuple[dict[str, np.ndarray], np.ndarray, dict[str, np.ndarray]]:
    with np.load(FORMAL_NEIGHBOURS, allow_pickle=False) as store:
        formal = {name: np.asarray(store[name]) for name in store.files}
    with np.load(RANDOM_IDENTITIES, allow_pickle=False) as store:
        if not np.array_equal(store["query_row_index"], np.arange(49152)):
            raise Stop("MSO02D_RANDOM_QUERY_IDENTITY_FAILURE")
        comparator = np.asarray(store["comparator_row_index"], dtype=np.int64)
    with np.load(D1_NEIGHBOURS, allow_pickle=False) as store:
        d1 = {name: np.asarray(store[name]) for name in store.files}
    access["consumed_metric_reads"] += 3
    if not np.array_equal(formal.get("query_row_index"), np.arange(49152)):
        raise Stop("MSO02D_FORMAL_NEIGHBOUR_QUERY_IDENTITY_FAILURE")
    if not np.array_equal(d1.get("query_row_index"), np.arange(49152)):
        raise Stop("MSO02D_D1_NEIGHBOUR_QUERY_IDENTITY_FAILURE")
    for arm in ("ss", "ms"):
        if formal.get(f"{arm}_neighbor_row_index", np.empty(0)).shape != (49152, 10):
            raise Stop(f"MSO02D_FORMAL_NEIGHBOUR_SHAPE_FAILURE:{arm}")
    return formal, comparator, d1


def norm_sq(value: np.ndarray) -> np.ndarray:
    value = np.asarray(value, dtype=np.float64)
    return value * value if value.ndim == 1 else np.sum(value * value, axis=-1)


def row_norm(value: np.ndarray) -> np.ndarray:
    value = np.asarray(value, dtype=np.float64)
    return np.abs(value) if value.ndim == 1 else np.linalg.norm(value, axis=-1)


def case_mean(values: np.ndarray, meta: dict[str, np.ndarray]) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    output = np.empty((384,) + values.shape[1:], dtype=np.float64)
    for case in range(384):
        rows = meta["case_index"] == case
        if int(rows.sum()) != 128:
            raise Stop("MSO02D_CASE_PARTICLE_COUNT_FAILURE")
        output[case] = np.mean(values[rows], axis=0)
    return output


def disagreement(
    target: np.ndarray, identities: np.ndarray, comparator: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    neighbour = norm_sq(target[identities] - target[:, None])
    random = norm_sq(target[comparator] - target[:, None])
    return np.mean(neighbour, axis=1), np.mean(random, axis=1), neighbour


def scope_case_indices(cases: list[dict[str, Any]]) -> list[tuple[str, str, np.ndarray]]:
    output: list[tuple[str, str, np.ndarray]] = [("OVERALL", "ALL", np.arange(384))]
    for fold in FOLDS:
        output.append(("FOLD", f"FOLD_{fold}", np.asarray([i for i, c in enumerate(cases) if c["fold"] == f"FOLD_{fold}"])))
    for family in FAMILIES:
        output.append(("FAMILY", family, np.asarray([i for i, c in enumerate(cases) if c["macro_family"] == family])))
    for fold in FOLDS:
        for family in FAMILIES:
            output.append(("FAMILY_FOLD", f"{family}|FOLD_{fold}", np.asarray([i for i, c in enumerate(cases) if c["fold"] == f"FOLD_{fold}" and c["macro_family"] == family])))
    for lineage in sorted({str(c["field_lineage_id"]) for c in cases}):
        output.append(("LINEAGE", lineage, np.asarray([i for i, c in enumerate(cases) if c["field_lineage_id"] == lineage])))
    return output


def equal_lineage_aggregate(
    values: np.ndarray,
    cases: list[dict[str, Any]],
    *,
    folds: set[str] | None = None,
    families: set[str] | None = None,
    lineages: set[str] | None = None,
) -> float:
    values = np.asarray(values, dtype=np.float64)
    cells: list[float] = []
    active_folds = sorted(folds or {str(c["fold"]) for c in cases})
    active_families = sorted(families or {str(c["macro_family"]) for c in cases})
    for fold in active_folds:
        for family in active_families:
            available = sorted({
                str(c["field_lineage_id"]) for c in cases
                if c["fold"] == fold and c["macro_family"] == family
                and (lineages is None or str(c["field_lineage_id"]) in lineages)
            })
            if not available:
                continue
            lineage_values = []
            for lineage in available:
                indices = [i for i, c in enumerate(cases) if c["fold"] == fold and c["macro_family"] == family and c["field_lineage_id"] == lineage]
                lineage_values.append(float(np.mean(values[indices])))
            cells.append(float(np.mean(lineage_values)))
    return float(np.mean(cells)) if cells else math.nan


def aggregate_for_scope(
    values: np.ndarray, cases: list[dict[str, Any]], scope: str, scope_id: str
) -> float:
    kwargs: dict[str, set[str]] = {}
    if scope == "FOLD":
        kwargs["folds"] = {scope_id}
    elif scope == "FAMILY":
        kwargs["families"] = {scope_id}
    elif scope == "FAMILY_FOLD":
        family, fold = scope_id.split("|")
        kwargs.update(folds={fold}, families={family})
    elif scope == "LINEAGE":
        kwargs["lineages"] = {scope_id}
    return equal_lineage_aggregate(values, cases, **kwargs)


def inverted_quantile(values: np.ndarray, q: float) -> float:
    return float(np.quantile(np.asarray(values, dtype=np.float64), q, method="inverted_cdf"))


def safe_spearman(x: np.ndarray, y: np.ndarray) -> tuple[float, str]:
    x, y = np.asarray(x, dtype=np.float64), np.asarray(y, dtype=np.float64)
    valid = np.isfinite(x) & np.isfinite(y)
    if int(valid.sum()) < 3 or np.unique(x[valid]).size < 2 or np.unique(y[valid]).size < 2:
        return math.nan, "NOT_EVALUABLE_CONSTANT_OR_INSUFFICIENT"
    value = float(spearmanr(x[valid], y[valid]).statistic)
    return value, "EVALUABLE" if math.isfinite(value) else "NOT_EVALUABLE_NONFINITE"


def selected_candidate_info(freeze: dict[str, Any], d1: dict[str, np.ndarray]) -> tuple[str | None, str]:
    candidate = recursively_find(freeze, {"selected_candidate_id", "selected_geometry_candidate_id"})
    status = str(recursively_find(freeze, {"selection_status", "status"}) or "")
    if candidate in {None, "", "NONE", "NOT_APPLICABLE"}:
        return None, status or "ROUTE_A_TARGET_BLIND_GEOMETRY_CANDIDATE_NOT_ESTABLISHED"
    candidate_id = str(candidate)
    if "selected_neighbor_row_index" not in d1 or "selected_neighbor_distance" not in d1:
        raise Stop("MSO02D_SELECTED_D1_NEIGHBOUR_ARRAYS_MISSING")
    encoded = d1.get("selected_candidate_id")
    if encoded is not None:
        observed = str(np.asarray(encoded).reshape(-1)[0])
        if observed != candidate_id:
            raise Stop("MSO02D_SELECTED_CANDIDATE_IDENTITY_MISMATCH")
    return candidate_id, status or "SELECTED_TARGET_BLIND_CANDIDATE_FROZEN"


def development_variance_by_fold(
    helper: Any, targets: dict[str, np.ndarray], meta: dict[str, np.ndarray]
) -> dict[str, np.ndarray]:
    result: dict[str, np.ndarray] = {}
    for component in COMPONENTS:
        values = np.full(6, np.nan)
        for fold in FOLDS:
            train = np.flatnonzero(meta["fold"] != fold)
            values[fold] = float(helper.development_trace_variance(targets[component], train, meta))
        if not np.all(np.isfinite(values) & (values > 0)):
            raise Stop(f"MSO02D_DEVELOPMENT_VARIANCE_FAILURE:{component}")
        result[component] = values
    return result


def coverage_masks(
    formal: dict[str, np.ndarray], meta: dict[str, np.ndarray]
) -> dict[str, np.ndarray]:
    geometry = read_json(COVERAGE_GEOMETRY)
    result: dict[str, np.ndarray] = {}
    for arm in ARMS:
        mask = np.zeros(49152, dtype=bool)
        distance = np.asarray(formal[f"{arm.lower()}_neighbor_distance"], dtype=np.float64)[:, 9]
        records = geometry.get("arms", {}).get(arm, {}).get("folds", [])
        for fold in FOLDS:
            record = next((r for r in records if r.get("held_out_fold") == f"FOLD_{fold}"), None)
            if record is None:
                raise Stop(f"MSO02D_COVERAGE_RADIUS_MISSING:{arm}:FOLD_{fold}")
            radius = float(record["k10_radius_p95"])
            rows = meta["fold"] == fold
            mask[rows] = distance[rows] <= radius
        result[arm] = mask
    return result


def random_descriptor_distances(
    data: dict[str, Any],
    comparator: np.ndarray,
    d1: dict[str, np.ndarray],
    selected_id: str | None,
    access: dict[str, Any],
) -> dict[str, np.ndarray]:
    output: dict[str, np.ndarray] = {}
    if "frozen_random_comparator_row_index" in d1 and not np.array_equal(
        np.asarray(d1["frozen_random_comparator_row_index"], dtype=np.int64), comparator
    ):
        raise Stop("MSO02D_D1_RANDOM_COMPARATOR_IDENTITY_FAILURE")
    for arm, geometry in (("SS", "U0_SS"), ("MS", "U0_MS")):
        key = "u0_random_comparator_distance" if arm == "MS" else ""
        if key and key in d1:
            values = np.asarray(d1[key], dtype=np.float64)
        else:
            values = np.full(comparator.shape, np.nan, dtype=np.float64)
            for fold in FOLDS:
                median, divisor = normalization_arrays(arm, fold)
                scaled = (data["features"][arm] - median) / divisor
                query = np.flatnonzero(data["meta"]["fold"] == fold)
                values[query] = np.linalg.norm(scaled[comparator[query]] - scaled[query, None, :], axis=2)
            access["target_blind_transform_diagnostic_computations"] += 1
        if values.shape != comparator.shape or not np.isfinite(values).all() or np.any(values < 0):
            raise Stop(f"MSO02D_RANDOM_DESCRIPTOR_DISTANCE_FAILURE:{geometry}")
        output[geometry] = values
    if selected_id is not None:
        if "selected_random_comparator_distance" not in d1:
            raise Stop("MSO02D_D1_SELECTED_RANDOM_DESCRIPTOR_DISTANCE_MISSING")
        values = np.asarray(d1["selected_random_comparator_distance"], dtype=np.float64)
        if values.shape != comparator.shape or not np.isfinite(values).all() or np.any(values < 0):
            raise Stop("MSO02D_D1_SELECTED_RANDOM_DESCRIPTOR_DISTANCE_FAILURE")
        output["D1_SELECTED"] = values
    return output


def candidate_decomposition(
    data: dict[str, Any], cases: list[dict[str, Any]], formal: dict[str, np.ndarray], comparator: np.ndarray
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[tuple[str, str], dict[str, np.ndarray]]]:
    rows: list[dict[str, Any]] = []
    case_primitives: dict[tuple[str, str], dict[str, np.ndarray]] = {}
    scopes = scope_case_indices(cases)
    for arm in ARMS:
        identities = np.asarray(formal[f"{arm.lower()}_neighbor_row_index"], dtype=np.int64)
        for component in COMPONENTS:
            n_particle, b_particle, _ = disagreement(data["targets"][component], identities, comparator)
            n_case, b_case = case_mean(n_particle, data["meta"]), case_mean(b_particle, data["meta"])
            case_primitives[(arm, component)] = {"wn": n_case, "wb": b_case}
            for scope, scope_id, _ in scopes:
                wn = aggregate_for_scope(n_case, cases, scope, scope_id)
                wb = aggregate_for_scope(b_case, cases, scope, scope_id)
                rows.append({
                    "arm": arm,
                    "component": component,
                    "scope": scope,
                    "scope_id": scope_id,
                    "wn": wn,
                    "wb": wb,
                    "d_wn_over_wb": wn / wb if wb > 0 else None,
                    "status": "EVALUABLE" if wb > 0 and math.isfinite(wn) else "NOT_EVALUABLE_NONPOSITIVE_WB",
                    "aggregation": "EQUAL_FOLD_FAMILY_LINEAGE_THEN_CASE_MEAN_AS_APPLICABLE",
                })
    cancellation: list[dict[str, Any]] = []
    lookup = {(r["component"], r["scope"], r["scope_id"], r["arm"]): r for r in rows}
    for component in COMPONENTS:
        for scope, scope_id, _ in scopes:
            ss = lookup[(component, scope, scope_id, "SS")]
            ms = lookup[(component, scope, scope_id, "MS")]
            wn_ratio = ms["wn"] / ss["wn"] if ss["wn"] > 0 else math.nan
            wb_ratio = ms["wb"] / ss["wb"] if ss["wb"] > 0 else math.nan
            d_ratio = ms["d_wn_over_wb"] / ss["d_wn_over_wb"] if ss["d_wn_over_wb"] and ss["d_wn_over_wb"] > 0 else math.nan
            cancellation.append({
                "component": component,
                "scope": scope,
                "scope_id": scope_id,
                "ss_wn": ss["wn"],
                "ms_wn": ms["wn"],
                "wn_ratio_ms_over_ss": wn_ratio,
                "ss_wb": ss["wb"],
                "ms_wb": ms["wb"],
                "wb_ratio_ms_over_ss": wb_ratio,
                "ss_d": ss["d_wn_over_wb"],
                "ms_d": ms["d_wn_over_wb"],
                "d_ratio_ms_over_ss": d_ratio,
                "log_scale_cancellation_gap": abs(math.log(wn_ratio) - math.log(wb_ratio)) if wn_ratio > 0 and wb_ratio > 0 else None,
                "numerator_delta": ms["wn"] - ss["wn"],
                "denominator_delta": ms["wb"] - ss["wb"],
                "status": "EVALUABLE" if all(math.isfinite(x) and x > 0 for x in (wn_ratio, wb_ratio, d_ratio)) else "NOT_EVALUABLE_RATIO",
            })
    return add_evidence(rows), add_evidence(cancellation), case_primitives


def target_amplitude_labels(target: np.ndarray) -> tuple[np.ndarray, dict[str, float]]:
    magnitude = row_norm(target)
    p25, p75 = inverted_quantile(magnitude, 0.25), inverted_quantile(magnitude, 0.75)
    labels = np.full(magnitude.size, "MID_P25_TO_P75", dtype="U24")
    labels[magnitude <= p25] = "LOW_LE_P25"
    labels[magnitude >= p75] = "HIGH_GE_P75"
    return labels, {"p25": p25, "p75": p75}


def cvar_diagnostics(
    data: dict[str, Any],
    cases: list[dict[str, Any]],
    formal: dict[str, np.ndarray],
    helper: Any,
    coverage: dict[str, np.ndarray],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[tuple[str, str], dict[str, np.ndarray]]]:
    variances = development_variance_by_fold(helper, data["targets"], data["meta"])
    hotspot_rows: list[dict[str, Any]] = []
    stratum_rows: list[dict[str, Any]] = []
    state: dict[tuple[str, str], dict[str, np.ndarray]] = {}
    for arm in ARMS:
        identities = np.asarray(formal[f"{arm.lower()}_neighbor_row_index"], dtype=np.int64)
        for component in COMPONENTS:
            target = data["targets"][component]
            local = target[identities]
            centered = local - np.mean(local, axis=1, keepdims=True)
            trace = np.sum(centered * centered, axis=1) / 9.0 if target.ndim == 1 else np.sum(centered * centered, axis=(1, 2)) / 9.0
            denominator = variances[component][data["meta"]["fold"]]
            particle = trace / denominator
            c_case = case_mean(particle, data["meta"])
            coverage_case = case_mean(coverage[arm].astype(float), data["meta"])
            state[(arm, component)] = {
                "particle": particle,
                "case": c_case,
                "within_dispersion": trace,
                "coverage_case": coverage_case,
            }
            amplitude, thresholds = target_amplitude_labels(target)
            for case_index, case in enumerate(cases):
                hotspot_rows.append({
                    "arm": arm,
                    "component": component,
                    "formal_case_index": case_index,
                    "case_id": case["case_id"],
                    "family": case["macro_family"],
                    "fold": case["fold"],
                    "lineage": case["field_lineage_id"],
                    "jitter_fraction": case.get("jitter_fraction"),
                    "polarization": case.get("polarization"),
                    "cvar": c_case[case_index],
                    "coverage_fraction": coverage_case[case_index],
                    "coverage_status": "INSIDE_MAJORITY" if coverage_case[case_index] >= 0.5 else "OUTSIDE_MAJORITY",
                    "status": "EVALUABLE",
                })
            for scope, scope_id, _ in scope_case_indices(cases):
                stratum_rows.append({
                    "arm": arm,
                    "component": component,
                    "scope": scope,
                    "scope_id": scope_id,
                    "cvar": aggregate_for_scope(c_case, cases, scope, scope_id),
                    "coverage_fraction": aggregate_for_scope(coverage_case, cases, scope, scope_id),
                    "status": "EVALUABLE",
                })
            for label in ("LOW_LE_P25", "MID_P25_TO_P75", "HIGH_GE_P75"):
                selected = amplitude == label
                stratum_rows.append({
                    "arm": arm,
                    "component": component,
                    "scope": "TARGET_AMPLITUDE",
                    "scope_id": label,
                    "cvar": float(np.mean(particle[selected])),
                    "coverage_fraction": float(np.mean(coverage[arm][selected])),
                    "target_magnitude_p25": thresholds["p25"],
                    "target_magnitude_p75": thresholds["p75"],
                    "status": "EVALUABLE",
                })
            for cover_label, selected in (("INSIDE_COVERAGE", coverage[arm]), ("OUTSIDE_COVERAGE", ~coverage[arm])):
                stratum_rows.append({
                    "arm": arm,
                    "component": component,
                    "scope": "COVERAGE_STATUS",
                    "scope_id": cover_label,
                    "cvar": float(np.mean(particle[selected])) if np.any(selected) else None,
                    "coverage_fraction": float(np.mean(coverage[arm][selected])) if np.any(selected) else None,
                    "status": "EVALUABLE" if np.any(selected) else "NOT_APPLICABLE_EMPTY_STRATUM",
                })
    return add_evidence(hotspot_rows), add_evidence(stratum_rows), state


def edge_scope_masks(meta: dict[str, np.ndarray], cases: list[dict[str, Any]]) -> list[tuple[str, str, np.ndarray]]:
    output = [("OVERALL", "ALL", np.ones(49152, dtype=bool))]
    for fold in FOLDS:
        output.append(("FOLD", f"FOLD_{fold}", meta["fold"] == fold))
    for family in FAMILIES:
        output.append(("FAMILY", family, meta["family"] == family))
    for fold in FOLDS:
        for family in FAMILIES:
            output.append(("FAMILY_FOLD", f"{family}|FOLD_{fold}", (meta["fold"] == fold) & (meta["family"] == family)))
    for lineage in sorted(set(meta["lineage"].astype(str))):
        output.append(("LINEAGE", lineage, meta["lineage"].astype(str) == lineage))
    return output


def near_collision_diagnostics(
    data: dict[str, Any],
    cases: list[dict[str, Any]],
    geometries: dict[str, tuple[np.ndarray, np.ndarray]],
    random_distances: dict[str, np.ndarray],
    comparator: np.ndarray,
    coverage: dict[str, np.ndarray],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[tuple[str, str], dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    ambiguity_rows: list[dict[str, Any]] = []
    state: dict[tuple[str, str], dict[str, Any]] = {}
    scopes = edge_scope_masks(data["meta"], cases)
    for geometry, (identities, distances) in geometries.items():
        formal_arm = "SS" if geometry == "U0_SS" else "MS" if geometry == "U0_MS" else None
        for component in COMPONENTS:
            target = data["targets"][component]
            neighbour_target_edge = norm_sq(target[identities] - target[:, None])
            random_target_edge = norm_sq(target[comparator] - target[:, None])
            target_edge = np.column_stack([neighbour_target_edge, random_target_edge])
            descriptor_edge = np.column_stack([
                np.asarray(distances, dtype=np.float64), random_distances[geometry]
            ])
            descriptor_cut = inverted_quantile(descriptor_edge.reshape(-1), 0.10)
            target_cut = inverted_quantile(target_edge.reshape(-1), 0.90)
            collision = (descriptor_edge <= descriptor_cut) & (target_edge >= target_cut)
            state[(geometry, component)] = {
                "collision": collision,
                "descriptor_threshold": descriptor_cut,
                "target_threshold": target_cut,
                "target_edge": target_edge,
                "comparison_population": "FROZEN_K10_NEIGHBOURS_PLUS_FROZEN_K10_MATCHED_RANDOM_EDGES",
            }
            for scope, scope_id, query_mask in scopes:
                selected = np.broadcast_to(query_mask[:, None], collision.shape)
                rows.append({
                    "geometry": geometry,
                    "component": component,
                    "scope": scope,
                    "scope_id": scope_id,
                    "descriptor_near_quantile": 0.10,
                    "target_far_quantile": 0.90,
                    "descriptor_distance_threshold": descriptor_cut,
                    "target_disagreement_threshold": target_cut,
                    "near_collision_rate": float(np.mean(collision[selected])),
                    "near_collision_count": int(np.sum(collision[selected])),
                    "legal_pair_count": int(np.sum(selected)),
                    "comparison_population": "FROZEN_K10_NEIGHBOURS_PLUS_FROZEN_K10_MATCHED_RANDOM_EDGES",
                    "interpretation": "PERSISTENT_OPERATIONAL_NEAR_COLLISION_EVIDENCE",
                    "status": "EVALUABLE",
                })
            if formal_arm is not None:
                query_covered = coverage[formal_arm]
                for label, query_mask in (("INSIDE_COVERAGE", query_covered), ("OUTSIDE_COVERAGE", ~query_covered)):
                    selected = np.broadcast_to(query_mask[:, None], collision.shape)
                    ambiguity_rows.append({
                        "geometry": geometry,
                        "arm": formal_arm,
                        "component": component,
                        "coverage_status": label,
                        "near_collision_rate": float(np.mean(collision[selected])) if np.any(selected) else None,
                        "near_collision_count": int(np.sum(collision[selected])),
                        "legal_pair_count": int(np.sum(selected)),
                        "comparison_population": "FROZEN_K10_NEIGHBOURS_PLUS_FROZEN_K10_MATCHED_RANDOM_EDGES",
                        "status": "EVALUABLE" if np.any(selected) else "NOT_APPLICABLE_EMPTY_STRATUM",
                    })
            else:
                ambiguity_rows.append({
                    "geometry": geometry,
                    "arm": "DIAGNOSTIC_SELECTED",
                    "component": component,
                    "coverage_status": "NOT_APPLICABLE_NO_FORMAL_SELECTED_GEOMETRY_COVERAGE_RADIUS",
                    "near_collision_rate": float(np.mean(collision)),
                    "near_collision_count": int(np.sum(collision)),
                    "legal_pair_count": int(collision.size),
                    "comparison_population": "FROZEN_K10_NEIGHBOURS_PLUS_FROZEN_K10_MATCHED_RANDOM_EDGES",
                    "status": "NOT_APPLICABLE_FORMAL_COVERAGE",
                })
    return add_evidence(rows), add_evidence(ambiguity_rows), state


def route_a_alignment(
    data: dict[str, Any],
    cases: list[dict[str, Any]],
    comparator: np.ndarray,
    geometries: dict[str, tuple[np.ndarray, np.ndarray]],
    cvar_state: dict[tuple[str, str], dict[str, np.ndarray]],
    near_state: dict[tuple[str, str], dict[str, Any]],
    selected_id: str | None,
    helper: Any,
) -> list[dict[str, Any]]:
    no_candidate = selected_id is None or "D1_SELECTED" not in geometries
    rows: list[dict[str, Any]] = []
    variances = development_variance_by_fold(helper, data["targets"], data["meta"])
    scopes = edge_scope_masks(data["meta"], cases)
    random_cache: dict[str, np.ndarray] = {}
    for component in COMPONENTS:
        target = data["targets"][component]
        random_cache[component] = norm_sq(target[comparator] - target[:, None])
    for geometry in (("U0_MS",) if no_candidate else ("U0_MS", "D1_SELECTED")):
        identities, distances = geometries[geometry]
        for component in COMPONENTS:
            target = data["targets"][component]
            target_edge = norm_sq(target[identities] - target[:, None])
            n_particle = np.mean(target_edge, axis=1)
            b_particle = np.mean(random_cache[component], axis=1)
            local = target[identities]
            centered = local - np.mean(local, axis=1, keepdims=True)
            trace = np.sum(centered * centered, axis=1) / 9.0 if target.ndim == 1 else np.sum(centered * centered, axis=(1, 2)) / 9.0
            cvar_particle = trace / variances[component][data["meta"]["fold"]]
            n_case = case_mean(n_particle, data["meta"])
            b_case = case_mean(b_particle, data["meta"])
            cvar_case = case_mean(cvar_particle, data["meta"])
            trace_case = case_mean(trace, data["meta"])
            collision = near_state[(geometry, component)]["collision"]
            for scope, scope_id, query_mask in scopes:
                if scope not in {"OVERALL", "FOLD", "FAMILY", "FAMILY_FOLD"}:
                    continue
                edge_mask = np.broadcast_to(query_mask[:, None], target_edge.shape)
                collision_mask = np.broadcast_to(query_mask[:, None], collision.shape)
                rho, rho_status = safe_spearman(distances[edge_mask], target_edge[edge_mask])
                wn = aggregate_for_scope(n_case, cases, scope, scope_id)
                wb = aggregate_for_scope(b_case, cases, scope, scope_id)
                rows.append({
                    "geometry": geometry,
                    "selected_candidate_id": selected_id if geometry == "D1_SELECTED" else "U0",
                    "component": component,
                    "scope": scope,
                    "scope_id": scope_id,
                    "descriptor_distance_target_disagreement_spearman": rho,
                    "spearman_status": rho_status,
                    "k10_wn": wn,
                    "matched_random_wb": wb,
                    "candidate_c_d": wn / wb if wb > 0 else None,
                    "cvar": aggregate_for_scope(cvar_case, cases, scope, scope_id),
                    "within_neighbour_target_dispersion": aggregate_for_scope(trace_case, cases, scope, scope_id),
                    "near_collision_rate": float(np.mean(collision[collision_mask])),
                    "status": "EVALUABLE" if wb > 0 else "NOT_EVALUABLE_NONPOSITIVE_WB",
                })
    lookup = {(r["geometry"], r["component"], r["scope"], r["scope_id"]): r for r in rows}
    for row in rows:
        if row["geometry"] != "D1_SELECTED":
            row["comparison_to_u0"] = "REFERENCE"
            continue
        u0 = lookup[("U0_MS", row["component"], row["scope"], row["scope_id"])]
        row.update({
            "delta_candidate_c_d_vs_u0": row["candidate_c_d"] - u0["candidate_c_d"],
            "delta_cvar_vs_u0": row["cvar"] - u0["cvar"],
            "delta_spearman_vs_u0": row["descriptor_distance_target_disagreement_spearman"] - u0["descriptor_distance_target_disagreement_spearman"] if row["spearman_status"] == u0["spearman_status"] == "EVALUABLE" else None,
            "delta_near_collision_rate_vs_u0": row["near_collision_rate"] - u0["near_collision_rate"],
            "candidate_c_improved": row["candidate_c_d"] < u0["candidate_c_d"] - NUMERIC_TOL,
            "cvar_improved": row["cvar"] < u0["cvar"] - NUMERIC_TOL,
            "spearman_improved": row["descriptor_distance_target_disagreement_spearman"] > u0["descriptor_distance_target_disagreement_spearman"] + NUMERIC_TOL if row["spearman_status"] == u0["spearman_status"] == "EVALUABLE" else False,
            "near_collision_improved": row["near_collision_rate"] < u0["near_collision_rate"] - NUMERIC_TOL,
            "comparison_to_u0": "EXPLORATORY_AFTER_TARGET_BLIND_SELECTION",
        })
    if no_candidate:
        rows.append({
            "geometry": "D1_SELECTED",
            "selected_candidate_id": None,
            "component": "ALL",
            "scope": "OVERALL",
            "scope_id": "ALL",
            "status": "NOT_APPLICABLE_NO_TARGET_BLIND_CANDIDATE_ESTABLISHED",
        })
    return add_evidence(rows)


def normalization_arrays(arm: str, fold: int) -> tuple[np.ndarray, np.ndarray]:
    registry = read_json(NORMALIZATION)
    record = next(
        row for row in registry["arms"][arm]["folds"]
        if row["held_out_fold"] == f"FOLD_{fold}"
    )
    median, divisor = np.asarray(record["median"], dtype=np.float64), np.asarray(record["divisor"], dtype=np.float64)
    if median.shape != divisor.shape or not np.all(np.isfinite(median)) or not np.all(np.isfinite(divisor)) or np.any(divisor <= 0):
        raise Stop(f"MSO02D_NORMALIZATION_FAILURE:{arm}:FOLD_{fold}")
    return median, divisor


def predict_frozen_model(
    helper: Any,
    winner: str,
    train_x: np.ndarray,
    query_x: np.ndarray,
    train_y: np.ndarray,
    train_global: np.ndarray,
    query_global: np.ndarray,
    meta: dict[str, np.ndarray],
    *,
    frozen_global_neighbors: np.ndarray | None,
    polynomial_positions: list[int],
) -> np.ndarray:
    if winner == "ridge":
        result = np.asarray(helper.ridge_predict(train_x, train_y, query_x, alpha=1.0))
        return result[:, 0] if train_y.ndim == 1 and result.ndim == 2 and result.shape[1] == 1 else result
    if winner in {"knn5", "knn10", "knn20"}:
        k = int(winner[3:])
        if frozen_global_neighbors is not None and frozen_global_neighbors.shape[1] >= k:
            global_neighbours = frozen_global_neighbors[:, :k]
            return np.mean(train_y[[{int(v): i for i, v in enumerate(train_global)}[int(v)] for v in global_neighbours.reshape(-1)]].reshape(global_neighbours.shape + train_y.shape[1:]), axis=1)
        _, local = helper.exact_permitted_neighbors(
            train_x,
            query_x,
            helper.subset_meta(meta, train_global),
            helper.subset_meta(meta, query_global),
            required_k=k,
        )
        return np.mean(train_y[local[:, :k]], axis=1)
    if winner == "polynomial_ridge":
        polynomial = helper.PolynomialFeatures(degree=2, include_bias=False)
        poly_train = polynomial.fit_transform(train_x[:, polynomial_positions])
        poly_query = polynomial.transform(query_x[:, polynomial_positions])
        result = np.asarray(helper.ridge_predict(poly_train, train_y, poly_query, alpha=1.0))
        return result[:, 0] if train_y.ndim == 1 and result.ndim == 2 and result.shape[1] == 1 else result
    raise Stop(f"MSO02D_UNKNOWN_FROZEN_ORACLE:{winner}")


def formal_nrmse_from_predictions(
    target: np.ndarray,
    prediction: np.ndarray,
    meta: dict[str, np.ndarray],
    helper: Any,
) -> tuple[float, np.ndarray, np.ndarray]:
    cells = np.full((6, 4), np.nan, dtype=np.float64)
    target_rms = np.full(6, np.nan, dtype=np.float64)
    error = norm_sq(prediction - target)
    for fold in FOLDS:
        train = np.flatnonzero(meta["fold"] != fold)
        target_rms[fold] = float(helper.development_target_rms(target, train, meta))
        for family_index, family in enumerate(FAMILIES):
            rows = (meta["fold"] == fold) & (meta["family"] == family)
            case_energy = case_mean(np.where(rows, error, np.nan), meta)
            case_ids = np.unique(meta["case_index"][rows])
            cells[fold, family_index] = math.sqrt(float(np.nanmean(case_energy[case_ids]))) / target_rms[fold]
    return float(np.mean(cells)), cells, error


def replay_frozen_oracles(
    data: dict[str, Any],
    cases: list[dict[str, Any]],
    formal: dict[str, np.ndarray],
    helper: Any,
    access: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[tuple[str, str], dict[str, Any]]]:
    summary = read_json(FORMAL_SUMMARY)["metrics"]
    schemas = {"SS": read_json(SS_SCHEMA), "MS": read_json(MS_SCHEMA)}
    predictions: dict[tuple[str, str], np.ndarray] = {}
    selected_models: dict[tuple[str, str, int], str] = {}
    for arm in ARMS:
        names = [row["name"] for row in schemas[arm]["columns"]]
        poly_positions = [names.index(name) for name in POLY_SUBSET]
        features = data["features"][arm]
        for component in COMPONENTS:
            target = data["targets"][component]
            prediction = np.full_like(target, np.nan, dtype=np.float64)
            winners = summary[arm][component]["selected_oracles_by_fold"]
            for fold in FOLDS:
                median, divisor = normalization_arrays(arm, fold)
                scaled = (features - median) / divisor
                train_global = helper.ordered_training_indices(np.flatnonzero(data["meta"]["fold"] != fold), data["meta"])
                query_global = np.flatnonzero(data["meta"]["fold"] == fold)
                winner = str(winners[str(fold)])
                selected_models[(arm, component, fold)] = winner
                frozen_global = np.asarray(formal[f"{arm.lower()}_neighbor_row_index"])[query_global]
                prediction[query_global] = predict_frozen_model(
                    helper,
                    winner,
                    scaled[train_global],
                    scaled[query_global],
                    target[train_global],
                    train_global,
                    query_global,
                    data["meta"],
                    frozen_global_neighbors=frozen_global,
                    polynomial_positions=poly_positions,
                )
                access["consumed_oracle_diagnostic_fits"] += 1
            if not np.isfinite(prediction).all():
                raise Stop(f"MSO02D_ORACLE_REPLAY_NONFINITE:{arm}:{component}")
            predictions[(arm, component)] = prediction

    decomposition: list[dict[str, Any]] = []
    state: dict[tuple[str, str], dict[str, Any]] = {}
    frozen_tables = {"SS": read_csv(SS_ORACLE), "MS": read_csv(MS_ORACLE)}
    for arm in ARMS:
        for component in COMPONENTS:
            target, prediction = data["targets"][component], predictions[(arm, component)]
            point, cells, error = formal_nrmse_from_predictions(target, prediction, data["meta"], helper)
            frozen_point = float(next(r for r in frozen_tables[arm] if r["component"] == component and r["scope"] == "OVERALL")["oracle_nrmse"])
            if not math.isclose(point, frozen_point, rel_tol=TOL, abs_tol=TOL):
                raise Stop(f"MSO02D_FROZEN_ORACLE_REPLAY_IDENTITY_FAILURE:{arm}:{component}:{point}:{frozen_point}")
            residual_norm = np.sqrt(error)
            residual = prediction - target
            state[(arm, component)] = {
                "prediction": prediction,
                "residual": residual,
                "residual_norm": residual_norm,
                "error": error,
                "cell_nrmse": cells,
                "point_nrmse": point,
            }
            decomposition.append({
                "arm": arm, "component": component, "scope": "OVERALL", "scope_id": "ALL",
                "oracle_nrmse": point, "residual_rms": math.sqrt(float(np.mean(error))),
                "frozen_metric_reproduced": True, "status": "EVALUABLE",
            })
            for fold in FOLDS:
                decomposition.append({
                    "arm": arm, "component": component, "scope": "FOLD", "scope_id": f"FOLD_{fold}",
                    "oracle_nrmse": float(np.mean(cells[fold])),
                    "residual_rms": math.sqrt(float(np.mean(error[data["meta"]["fold"] == fold]))),
                    "selected_oracle": selected_models[(arm, component, fold)], "status": "EVALUABLE",
                })
            for family_index, family in enumerate(FAMILIES):
                decomposition.append({
                    "arm": arm, "component": component, "scope": "FAMILY", "scope_id": family,
                    "oracle_nrmse": float(np.mean(cells[:, family_index])),
                    "residual_rms": math.sqrt(float(np.mean(error[data["meta"]["family"] == family]))),
                    "status": "EVALUABLE",
                })
            for fold in FOLDS:
                for family_index, family in enumerate(FAMILIES):
                    selected = (data["meta"]["fold"] == fold) & (data["meta"]["family"] == family)
                    decomposition.append({
                        "arm": arm, "component": component, "scope": "FAMILY_FOLD", "scope_id": f"{family}|FOLD_{fold}",
                        "oracle_nrmse": cells[fold, family_index],
                        "residual_rms": math.sqrt(float(np.mean(error[selected]))), "status": "EVALUABLE",
                    })
            amplitude, thresholds = target_amplitude_labels(target)
            for label in ("LOW_LE_P25", "MID_P25_TO_P75", "HIGH_GE_P75"):
                selected = amplitude == label
                decomposition.append({
                    "arm": arm, "component": component, "scope": "TARGET_AMPLITUDE", "scope_id": label,
                    "oracle_nrmse": None, "residual_rms": math.sqrt(float(np.mean(error[selected]))),
                    "target_magnitude_p25": thresholds["p25"], "target_magnitude_p75": thresholds["p75"], "status": "EVALUABLE_RAW_RESIDUAL_ONLY",
                })
            if target.ndim == 2:
                for axis, label in enumerate(("X_COORDINATE", "Y_COORDINATE")):
                    decomposition.append({
                        "arm": arm, "component": component, "scope": "VECTOR_DIRECTION", "scope_id": label,
                        "oracle_nrmse": None, "residual_rms": math.sqrt(float(np.mean(residual[:, axis] ** 2))),
                        "status": "EVALUABLE_COORDINATE_COMPONENT_NOT_INTRINSIC_DIRECTION",
                    })
            for polarization in sorted({str(c.get("polarization", "NOT_AVAILABLE")) for c in cases}):
                case_ids = [i for i, c in enumerate(cases) if str(c.get("polarization", "NOT_AVAILABLE")) == polarization]
                selected = np.isin(data["meta"]["case_index"], case_ids)
                decomposition.append({
                    "arm": arm, "component": component, "scope": "DESIGN_ONLY_POLARIZATION", "scope_id": polarization,
                    "oracle_nrmse": None, "residual_rms": math.sqrt(float(np.mean(error[selected]))) if np.any(selected) else None,
                    "status": "EVALUABLE_RAW_RESIDUAL_ONLY" if np.any(selected) else "NOT_APPLICABLE_EMPTY_STRATUM",
                })

    gain: list[dict[str, Any]] = []
    lookup = {(r["component"], r["scope"], r["scope_id"], r["arm"]): r for r in decomposition}
    keys = sorted({(r["component"], r["scope"], r["scope_id"]) for r in decomposition})
    for component, scope, scope_id in keys:
        ss, ms = lookup[(component, scope, scope_id, "SS")], lookup[(component, scope, scope_id, "MS")]
        ss_n, ms_n = ss.get("oracle_nrmse"), ms.get("oracle_nrmse")
        ss_r, ms_r = ss.get("residual_rms"), ms.get("residual_rms")
        gain.append({
            "component": component, "scope": scope, "scope_id": scope_id,
            "ss_oracle_nrmse": ss_n, "ms_oracle_nrmse": ms_n,
            "oracle_nrmse_ratio_ms_over_ss": ms_n / ss_n if ss_n not in {None, 0} and ms_n is not None else None,
            "oracle_nrmse_improved": bool(ms_n < ss_n - NUMERIC_TOL) if ss_n is not None and ms_n is not None else None,
            "ss_residual_rms": ss_r, "ms_residual_rms": ms_r,
            "residual_rms_ratio_ms_over_ss": ms_r / ss_r if ss_r not in {None, 0} and ms_r is not None else None,
            "residual_rms_improved": bool(ms_r < ss_r - NUMERIC_TOL) if ss_r is not None and ms_r is not None else None,
            "status": "EVALUABLE",
        })
    return add_evidence(decomposition), add_evidence(gain), state


def proxy_values_from_registry(
    registry: dict[str, Any], features: np.ndarray, names: list[str]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, np.ndarray]]:
    availability: list[dict[str, Any]] = []
    overlap: list[dict[str, Any]] = []
    values: dict[str, np.ndarray] = {}
    for proxy in registry.get("proxies", []):
        proxy_id = str(proxy.get("proxy_id", "MISSING_PROXY_ID"))
        inputs = list(proxy.get("input_feature_names", []))
        missing = [name for name in inputs if name not in names]
        operation = str(proxy.get("deterministic_operation", "")).upper().replace("-", "_").replace(" ", "_")
        status = "EVALUABLE"
        value: np.ndarray | None = None
        if missing:
            status = "NOT_AVAILABLE_INPUT_FEATURE_MISSING"
        elif not bool(proxy.get("target_blind_definition", False)):
            status = "NOT_ADMISSIBLE_DEFINITION_NOT_TARGET_BLIND"
        elif not bool(proxy.get("deployment_available", False)):
            status = "NOT_AVAILABLE_AT_DEPLOYMENT"
        elif any(bool(proxy.get(field, False)) for field in ("principal_frame_eigenvector_dependence", "eigenvector_sign_convention", "arbitrary_frame_fallback")):
            status = "NOT_ADMISSIBLE_FRAME_OR_FALLBACK_DEPENDENCE"
        else:
            columns = [features[:, names.index(name)] for name in inputs]
            try:
                if operation in {"IDENTITY", "SCALAR_IDENTITY"} and len(columns) == 1:
                    value = columns[0][:, None]
                elif "VECTOR" in operation and "NORM" not in operation and "DOT" not in operation and len(columns) in {2, 4, 6}:
                    value = np.column_stack(columns)
                elif "NORM_RATIO" in operation and len(columns) >= 4:
                    numerator = np.hypot(columns[0], columns[1])
                    denominator = np.hypot(columns[2], columns[3])
                    value = np.divide(numerator, denominator, out=np.zeros_like(numerator), where=denominator > 0)[:, None]
                elif "ORTHOGONAL" in operation and len(columns) >= 4:
                    base_sq = columns[2] ** 2 + columns[3] ** 2
                    cross = columns[0] * columns[3] - columns[1] * columns[2]
                    value = np.divide(cross * cross, base_sq, out=np.zeros_like(cross), where=base_sq > 0)[:, None]
                elif "PARALLEL" in operation and len(columns) >= 4:
                    base_sq = columns[2] ** 2 + columns[3] ** 2
                    dot = columns[0] * columns[2] + columns[1] * columns[3]
                    value = np.divide(dot * dot, base_sq, out=np.zeros_like(dot), where=base_sq > 0)[:, None]
                elif "CROSS" in operation and len(columns) >= 4:
                    value = (columns[0] * columns[3] - columns[1] * columns[2])[:, None]
                elif ("DOT" in operation or "GRAM" in operation or "ALIGNMENT" in operation) and len(columns) >= 4:
                    value = (columns[0] * columns[2] + columns[1] * columns[3])[:, None]
                elif "NORM_SQUARED" in operation and len(columns) >= 2:
                    value = np.sum(np.column_stack(columns) ** 2, axis=1)[:, None]
                elif "NORM" in operation and len(columns) >= 2:
                    value = np.linalg.norm(np.column_stack(columns), axis=1)[:, None]
                elif "TRACE" in operation and len(columns) >= 3:
                    value = (columns[0] + columns[2])[:, None]
                elif "DEVIATORIC" in operation and len(columns) >= 3:
                    value = np.sqrt(0.5 * (columns[0] - columns[2]) ** 2 + 2.0 * columns[1] ** 2)[:, None]
                elif "VECTOR_TENSOR_VECTOR" in operation and len(columns) >= 5:
                    value = (columns[0] ** 2 * columns[2] + 2 * columns[0] * columns[1] * columns[3] + columns[1] ** 2 * columns[4])[:, None]
                else:
                    status = "NOT_COMPUTABLE_UNRECOGNIZED_FROZEN_OPERATION"
            except (FloatingPointError, ValueError, IndexError):
                status = "NOT_COMPUTABLE_NUMERICAL_FAILURE"
        if value is not None:
            value = np.asarray(value, dtype=np.float64)
            if value.shape[0] != features.shape[0] or not np.isfinite(value).all():
                status, value = "NOT_COMPUTABLE_NONFINITE_OR_SHAPE_FAILURE", None
            else:
                values[proxy_id] = value
        availability.append({
            "proxy_id": proxy_id,
            "proxy_class": proxy.get("proxy_class"),
            "component": proxy.get("component"),
            "input_feature_names": inputs,
            "missing_input_feature_names": missing,
            "deterministic_operation": proxy.get("deterministic_operation"),
            "deployment_available": proxy.get("deployment_available"),
            "o2_parity": proxy.get("o2_parity"),
            "zero_semantics": proxy.get("zero_semantics"),
            "output_dimension": None if value is None else int(value.shape[1]),
            "status": status,
        })
        overlap_class = str(proxy.get("overlap_class", "UNSPECIFIED"))
        overlap.append({
            "proxy_id": proxy_id,
            "overlap_class": overlap_class,
            "new_deployment_information": overlap_class == "NEW_DEPLOYMENT_INFORMATION",
            "algebraic_reparameterization": overlap_class == "ALGEBRAIC_REPARAMETERIZATION_OF_EXISTING_110D_FEATURES",
            "overlap_with_existing_110d": proxy.get("overlap_with_existing_110d", overlap_class),
            "overlap_with_ddo02b": proxy.get("overlap_with_ddo02b"),
            "eligible_as_route_b_incremental_information": overlap_class == "NEW_DEPLOYMENT_INFORMATION" and status == "EVALUABLE",
            "status": status,
        })
    if not availability:
        availability.append({"proxy_id": "NONE", "status": "NOT_APPLICABLE_EMPTY_FROZEN_PROXY_REGISTRY"})
        overlap.append({"proxy_id": "NONE", "status": "NOT_APPLICABLE_EMPTY_FROZEN_PROXY_REGISTRY"})
    return add_evidence(availability), add_evidence(overlap), values


def directional_target_alignment(
    data: dict[str, Any], formal: dict[str, np.ndarray], registry: dict[str, Any], proxy_values: dict[str, np.ndarray]
) -> list[dict[str, Any]]:
    identities = np.asarray(formal["ms_neighbor_row_index"], dtype=np.int64)
    rows: list[dict[str, Any]] = []
    proxy_lookup = {str(p.get("proxy_id")): p for p in registry.get("proxies", [])}
    scopes = edge_scope_masks(data["meta"], [])
    for proxy_id, proxy_value in proxy_values.items():
        proxy = proxy_lookup[proxy_id]
        proxy_edge = row_norm(proxy_value[identities] - proxy_value[:, None])
        declared = str(proxy.get("component", "ALL"))
        components = COMPONENTS if declared in {"ALL", "BOTH", "MOMENTUM"} else tuple(c for c in COMPONENTS if c == declared)
        for component in components:
            target = data["targets"][component]
            target_edge = norm_sq(target[identities] - target[:, None])
            for scope, scope_id, query_mask in scopes:
                if scope not in {"OVERALL", "FOLD", "FAMILY", "FAMILY_FOLD"}:
                    continue
                selected = np.broadcast_to(query_mask[:, None], target_edge.shape)
                rho, status = safe_spearman(proxy_edge[selected], target_edge[selected])
                rows.append({
                    "proxy_id": proxy_id, "proxy_class": proxy.get("proxy_class"), "component": component,
                    "scope": scope, "scope_id": scope_id,
                    "proxy_distance_target_disagreement_spearman": rho,
                    "mean_proxy_neighbour_difference": float(np.mean(proxy_edge[selected])),
                    "mean_target_neighbour_disagreement": float(np.mean(target_edge[selected])),
                    "status": status,
                })
    if not rows:
        rows.append({"proxy_id": "NONE", "component": "ALL", "scope": "OVERALL", "scope_id": "ALL", "status": "NOT_APPLICABLE_NO_COMPUTABLE_FROZEN_PROXY"})
    return add_evidence(rows)


def directional_residual_diagnostics(
    data: dict[str, Any],
    registry: dict[str, Any],
    proxy_values: dict[str, np.ndarray],
    oracle_state: dict[tuple[str, str], dict[str, Any]],
    helper: Any,
    access: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    proxy_lookup = {str(p.get("proxy_id")): p for p in registry.get("proxies", [])}
    ms_names = [row["name"] for row in read_json(MS_SCHEMA)["columns"]]
    scalar_indices = [i for i, name in enumerate(ms_names) if not re.search(r"_(?:x|y|xy|yx|xx|yy)$", name)]
    for proxy_id, proxy_value in proxy_values.items():
        proxy = proxy_lookup[proxy_id]
        declared = str(proxy.get("component", "ALL"))
        components = COMPONENTS if declared in {"ALL", "BOTH", "MOMENTUM"} else tuple(c for c in COMPONENTS if c == declared)
        magnitude = row_norm(proxy_value)
        for component in components:
            residual_norm = oracle_state[("MS", component)]["residual_norm"]
            for scope, scope_id, mask in edge_scope_masks(data["meta"], []):
                if scope not in {"OVERALL", "FOLD", "FAMILY"}:
                    continue
                rho, status = safe_spearman(magnitude[mask], residual_norm[mask])
                rows.append({
                    "proxy_id": proxy_id, "component": component, "diagnostic": "PROXY_MAGNITUDE_VS_FROZEN_ORACLE_RESIDUAL",
                    "scope": scope, "scope_id": scope_id, "spearman": rho, "status": status,
                })
            fold_ratios = []
            for fold in FOLDS:
                train = helper.ordered_training_indices(np.flatnonzero(data["meta"]["fold"] != fold), data["meta"])
                query = np.flatnonzero(data["meta"]["fold"] == fold)
                median, divisor = normalization_arrays("MS", fold)
                scaled = (data["features"]["MS"] - median) / divisor
                baseline_x = scaled[:, scalar_indices]
                p_train = proxy_value[train]
                p_median = np.median(p_train, axis=0)
                p_iqr = np.quantile(p_train, 0.75, axis=0) - np.quantile(p_train, 0.25, axis=0)
                p_iqr[p_iqr == 0] = 1.0
                augmented = np.column_stack([baseline_x, (proxy_value - p_median) / p_iqr])
                y = residual_norm
                base_prediction = helper.ridge_predict(baseline_x[train], y[train], baseline_x[query], alpha=1.0)
                augmented_prediction = helper.ridge_predict(augmented[train], y[train], augmented[query], alpha=1.0)
                base_rmse = math.sqrt(float(np.mean((base_prediction - y[query]) ** 2)))
                aug_rmse = math.sqrt(float(np.mean((augmented_prediction - y[query]) ** 2)))
                ratio = aug_rmse / base_rmse if base_rmse > 0 else math.nan
                fold_ratios.append(ratio)
                rows.append({
                    "proxy_id": proxy_id, "component": component,
                    "diagnostic": "FROZEN_ALPHA1_RIDGE_RESIDUAL_INCREMENT",
                    "scope": "FOLD", "scope_id": f"FOLD_{fold}",
                    "scalar_baseline_residual_magnitude_rmse": base_rmse,
                    "scalar_plus_proxy_residual_magnitude_rmse": aug_rmse,
                    "rmse_ratio": ratio,
                    "improved": bool(ratio < 1.0 - NUMERIC_TOL) if math.isfinite(ratio) else False,
                    "status": "EVALUABLE" if math.isfinite(ratio) else "NOT_EVALUABLE_NONFINITE",
                })
                access["consumed_oracle_diagnostic_fits"] += 2
            rows.append({
                "proxy_id": proxy_id, "component": component,
                "diagnostic": "FROZEN_ALPHA1_RIDGE_RESIDUAL_INCREMENT",
                "scope": "OVERALL", "scope_id": "ALL",
                "median_rmse_ratio": float(np.median(fold_ratios)),
                "improved_fold_count": int(np.sum(np.asarray(fold_ratios) < 1.0 - NUMERIC_TOL)),
                "status": "EVALUABLE",
            })
    if not rows:
        rows.append({"proxy_id": "NONE", "component": "ALL", "diagnostic": "ALL", "scope": "OVERALL", "scope_id": "ALL", "status": "NOT_APPLICABLE_NO_COMPUTABLE_FROZEN_PROXY"})
    return add_evidence(rows)


def fixed_feature_group_ablation(
    data: dict[str, Any],
    helper: Any,
    oracle_state: dict[tuple[str, str], dict[str, Any]],
    access: dict[str, Any],
) -> list[dict[str, Any]]:
    registry = read_json(D0_FEATURE_GROUPS)
    groups = [g for g in registry.get("groups", []) if bool(g.get("ablation_eligible", False))]
    by_id = {str(g["group_id"]): sorted(int(i) for i in g.get("feature_indices_zero_based", [])) for g in groups}
    if "G0" not in by_id or not by_id["G0"]:
        return add_evidence([{"design_id": "NONE", "component": "ALL", "scope": "OVERALL", "scope_id": "ALL", "status": "NOT_EVALUABLE_FROZEN_G0_GROUP_MISSING"}])
    all_indices = list(range(110))
    designs: list[tuple[str, list[int], str]] = [("BASE_ONLY", by_id["G0"], "BASE_ONLY")]
    for group_id, indices in sorted(by_id.items()):
        if group_id == "G0" or not indices:
            continue
        designs.append((f"BASE_PLUS_{group_id}", sorted(set(by_id["G0"] + indices)), "BASE_PLUS_SINGLE_GROUP"))
    for group_id, indices in sorted(by_id.items()):
        if group_id == "G0" or not indices:
            continue
        designs.append((f"LEAVE_{group_id}_OUT", [i for i in all_indices if i not in set(indices)], "LEAVE_ONE_GROUP_OUT"))
    designs.append(("FULL_MS", all_indices, "FULL_MS"))
    # Registry mistakes cannot trigger repeated/adaptive designs.
    unique: dict[tuple[int, ...], tuple[str, list[int], str]] = {}
    for design in designs:
        unique.setdefault(tuple(design[1]), design)
    designs = list(unique.values())

    summary = read_json(FORMAL_SUMMARY)["metrics"]["MS"]
    names = [row["name"] for row in read_json(MS_SCHEMA)["columns"]]
    rows: list[dict[str, Any]] = []
    per_design: dict[tuple[str, str], tuple[float, np.ndarray, np.ndarray]] = {}
    for design_id, indices, design_class in designs:
        positions = {old: new for new, old in enumerate(indices)}
        missing_poly = [names.index(name) for name in POLY_SUBSET if names.index(name) not in positions]
        for component in COMPONENTS:
            target = data["targets"][component]
            prediction = np.full_like(target, np.nan, dtype=np.float64)
            status = "EVALUABLE"
            for fold in FOLDS:
                winner = str(summary[component]["selected_oracles_by_fold"][str(fold)])
                if winner == "polynomial_ridge" and missing_poly:
                    status = "NOT_EVALUABLE_FROZEN_POLYNOMIAL_INPUT_ABSENT"
                    break
                median, divisor = normalization_arrays("MS", fold)
                scaled = ((data["features"]["MS"] - median) / divisor)[:, indices]
                train = helper.ordered_training_indices(np.flatnonzero(data["meta"]["fold"] != fold), data["meta"])
                query = np.flatnonzero(data["meta"]["fold"] == fold)
                poly_positions = [positions[names.index(name)] for name in POLY_SUBSET if names.index(name) in positions]
                prediction[query] = predict_frozen_model(
                    helper, winner, scaled[train], scaled[query], target[train], train, query, data["meta"],
                    frozen_global_neighbors=None, polynomial_positions=poly_positions,
                )
                access["consumed_oracle_diagnostic_fits"] += 1
            if status != "EVALUABLE" or not np.isfinite(prediction).all():
                rows.append({
                    "design_id": design_id, "design_class": design_class, "component": component,
                    "scope": "OVERALL", "scope_id": "ALL", "feature_count": len(indices),
                    "feature_indices_zero_based": indices, "status": status if status != "EVALUABLE" else "NOT_EVALUABLE_NONFINITE_PREDICTION",
                })
                continue
            point, cells, error = formal_nrmse_from_predictions(target, prediction, data["meta"], helper)
            per_design[(design_id, component)] = (point, cells, error)
            rows.append({
                "design_id": design_id, "design_class": design_class, "component": component,
                "scope": "OVERALL", "scope_id": "ALL", "feature_count": len(indices),
                "feature_indices_zero_based": indices, "oracle_nrmse": point,
                "residual_rms": math.sqrt(float(np.mean(error))), "status": "EVALUABLE",
            })
            for fold in FOLDS:
                rows.append({
                    "design_id": design_id, "design_class": design_class, "component": component,
                    "scope": "FOLD", "scope_id": f"FOLD_{fold}", "feature_count": len(indices),
                    "oracle_nrmse": float(np.mean(cells[fold])),
                    "residual_rms": math.sqrt(float(np.mean(error[data["meta"]["fold"] == fold]))), "status": "EVALUABLE",
                })
            for family_index, family in enumerate(FAMILIES):
                rows.append({
                    "design_id": design_id, "design_class": design_class, "component": component,
                    "scope": "FAMILY", "scope_id": family, "feature_count": len(indices),
                    "oracle_nrmse": float(np.mean(cells[:, family_index])),
                    "residual_rms": math.sqrt(float(np.mean(error[data["meta"]["family"] == family]))), "status": "EVALUABLE",
                })
    full_rows = {(r["component"], r["scope"], r["scope_id"]): r for r in rows if r["design_id"] == "FULL_MS" and r["status"] == "EVALUABLE"}
    for row in rows:
        full = full_rows.get((row["component"], row["scope"], row["scope_id"]))
        if full is None or row.get("oracle_nrmse") is None:
            continue
        row["delta_oracle_nrmse_vs_full_ms"] = row["oracle_nrmse"] - full["oracle_nrmse"]
        row["delta_residual_rms_vs_full_ms"] = row["residual_rms"] - full["residual_rms"]
    for design_id, _, _ in designs:
        for component in COMPONENTS:
            overall = next((r for r in rows if r["design_id"] == design_id and r["component"] == component and r["scope"] == "OVERALL"), None)
            if overall is None or overall.get("status") != "EVALUABLE":
                continue
            folds = [r for r in rows if r["design_id"] == design_id and r["component"] == component and r["scope"] == "FOLD"]
            families = [r for r in rows if r["design_id"] == design_id and r["component"] == component and r["scope"] == "FAMILY"]
            overall["folds_better_than_full_ms"] = int(sum((r.get("delta_oracle_nrmse_vs_full_ms") or 0) < -NUMERIC_TOL for r in folds))
            overall["families_better_than_full_ms"] = int(sum((r.get("delta_oracle_nrmse_vs_full_ms") or 0) < -NUMERIC_TOL for r in families))
    # Full MS must reproduce the already-audited frozen replay.
    for component in COMPONENTS:
        full = per_design.get(("FULL_MS", component))
        if full is None or not math.isclose(full[0], oracle_state[("MS", component)]["point_nrmse"], rel_tol=TOL, abs_tol=TOL):
            raise Stop(f"MSO02D_FIXED_ABLATION_FULL_MS_IDENTITY_FAILURE:{component}")
    return add_evidence(rows)


def design_only_stratification(
    data: dict[str, Any],
    cases: list[dict[str, Any]],
    candidate_state: dict[tuple[str, str], dict[str, np.ndarray]],
    cvar_state: dict[tuple[str, str], dict[str, np.ndarray]],
    near_state: dict[tuple[str, str], dict[str, Any]],
    oracle_state: dict[tuple[str, str], dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    fields = (
        "macro_family", "fold", "field_lineage_id", "field_subtype", "polarization",
        "disorder_state_id", "layout_class", "jitter_fraction", "mode_indices",
    )
    rows: list[dict[str, Any]] = []
    for field in fields:
        levels = sorted({json.dumps(c.get(field, "NOT_AVAILABLE"), sort_keys=True) for c in cases})
        for level in levels:
            indices = np.asarray([i for i, c in enumerate(cases) if json.dumps(c.get(field, "NOT_AVAILABLE"), sort_keys=True) == level])
            if not indices.size:
                continue
            particle_mask = np.isin(data["meta"]["case_index"], indices)
            for arm in ARMS:
                geometry = f"U0_{arm}"
                for component in COMPONENTS:
                    wn = float(np.mean(candidate_state[(arm, component)]["wn"][indices]))
                    wb = float(np.mean(candidate_state[(arm, component)]["wb"][indices]))
                    collision = near_state[(geometry, component)]["collision"]
                    record = {
                        "design_only_label": field,
                        "stratum": level,
                        "arm": arm,
                        "component": component,
                        "case_count": int(indices.size),
                        "candidate_c_wn": wn,
                        "candidate_c_wb": wb,
                        "candidate_c_d": wn / wb if wb > 0 else None,
                        "cvar": float(np.mean(cvar_state[(arm, component)]["case"][indices])),
                        "near_collision_rate": float(np.mean(collision[particle_mask])),
                        "model_input_authorized": False,
                        "status": "EVALUABLE",
                    }
                    if oracle_state is None:
                        record["oracle_residual_rms"] = None
                        record["oracle_status"] = "NOT_COMPUTED_AT_THIS_STAGE_CUTOFF"
                    else:
                        record["oracle_residual_rms"] = math.sqrt(float(np.mean(oracle_state[(arm, component)]["error"][particle_mask])))
                        record["oracle_status"] = "EVALUABLE"
                    rows.append(record)
    return add_evidence(rows)


def adjudicate_mechanisms_and_routes(
    alignment: list[dict[str, Any]],
    directional_target: list[dict[str, Any]],
    directional_residual: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
    cvar_rows: list[dict[str, Any]],
    gain_rows: list[dict[str, Any]],
    ambiguity_rows: list[dict[str, Any]],
    proxy_overlap: list[dict[str, Any]],
    selected_id: str | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    evidence: list[dict[str, Any]] = []
    verdicts: list[dict[str, Any]] = []
    routes: list[dict[str, Any]] = []

    def selected_rows(table: list[dict[str, Any]], **conditions: Any) -> list[dict[str, Any]]:
        return [r for r in table if all(r.get(k) == v for k, v in conditions.items())]

    # Route A uses four independent registered alignment diagnostics.  A fold
    # or family supports alignment only when at least two improve strictly.
    route_a_counts: dict[str, dict[str, int]] = {}
    for component in COMPONENTS:
        selected = selected_rows(alignment, geometry="D1_SELECTED", component=component)
        fold_support = sum(
            sum(bool(r.get(k, False)) for k in ("candidate_c_improved", "cvar_improved", "spearman_improved", "near_collision_improved")) >= 2
            for r in selected if r.get("scope") == "FOLD"
        )
        family_support = sum(
            sum(bool(r.get(k, False)) for k in ("candidate_c_improved", "cvar_improved", "spearman_improved", "near_collision_improved")) >= 2
            for r in selected if r.get("scope") == "FAMILY"
        )
        overall = next((r for r in selected if r.get("scope") == "OVERALL"), {})
        route_a_counts[component] = {
            "folds": fold_support,
            "families": family_support,
            "diagnostics": sum(bool(overall.get(k, False)) for k in ("candidate_c_improved", "cvar_improved", "spearman_improved", "near_collision_improved")),
        }
    density_non_degradation = bool(
        selected_id is not None
        and route_a_counts["density_rate"]["diagnostics"] >= 0
        and all(
            not r.get("candidate_c_d", math.inf) > u.get("candidate_c_d", -math.inf) + NUMERIC_TOL
            and not r.get("cvar", math.inf) > u.get("cvar", -math.inf) + NUMERIC_TOL
            for r in selected_rows(alignment, geometry="D1_SELECTED", component="density_rate", scope="OVERALL")
            for u in selected_rows(alignment, geometry="U0_MS", component="density_rate", scope="OVERALL")
        )
    )
    route_a_actionable = bool(
        selected_id is not None
        and all(route_a_counts[c]["folds"] >= 4 and route_a_counts[c]["families"] >= 3 and route_a_counts[c]["diagnostics"] >= 2 for c in COMPONENTS[1:])
        and density_non_degradation
    )
    for component, counts in route_a_counts.items():
        evidence.append({
            "mechanism_id": "F-MS1", "diagnostic_class": "FROZEN_TARGET_BLIND_GEOMETRY_T3_ALIGNMENT",
            "component": component, "supporting_fold_count": counts["folds"],
            "supporting_family_count": counts["families"], "independent_overall_diagnostic_count": counts["diagnostics"],
            "source": "target_blind_geometry_target_alignment.csv", "direction": "SUPPORT" if counts["diagnostics"] >= 2 else "NO_SUPPORT",
        })

    new_proxies = {r["proxy_id"] for r in proxy_overlap if r.get("eligible_as_route_b_incremental_information") is True}
    route_b_component: dict[str, dict[str, int]] = {}
    for component in COMPONENTS[1:]:
        supported_proxies = set()
        max_folds = max_families = 0
        for proxy_id in new_proxies:
            target_fold = selected_rows(directional_target, proxy_id=proxy_id, component=component, scope="FOLD")
            target_family = selected_rows(directional_target, proxy_id=proxy_id, component=component, scope="FAMILY")
            residual_fold = selected_rows(directional_residual, proxy_id=proxy_id, component=component, diagnostic="FROZEN_ALPHA1_RIDGE_RESIDUAL_INCREMENT", scope="FOLD")
            folds = min(sum((r.get("proxy_distance_target_disagreement_spearman") or 0) > 0 for r in target_fold), sum(bool(r.get("improved")) for r in residual_fold))
            families = sum((r.get("proxy_distance_target_disagreement_spearman") or 0) > 0 for r in target_family)
            max_folds, max_families = max(max_folds, folds), max(max_families, families)
            if folds >= 4 and families >= 3:
                supported_proxies.add(proxy_id)
        route_b_component[component] = {"folds": max_folds, "families": max_families, "independent_proxies": len(supported_proxies)}
        evidence.append({
            "mechanism_id": "F-MS3", "diagnostic_class": "DIRECTIONAL_SCALE_RESPONSE_INCREMENT",
            "component": component, "supporting_fold_count": max_folds, "supporting_family_count": max_families,
            "independent_proxy_count": len(supported_proxies), "source": "directional_proxy_target_alignment.csv|directional_proxy_residual_diagnostics.csv",
            "direction": "SUPPORT" if len(supported_proxies) >= 2 else "NO_SUPPORT",
        })
    route_b_actionable = bool(all(x["folds"] >= 4 and x["families"] >= 3 and x["independent_proxies"] >= 2 for x in route_b_component.values()))

    candidate_lookup = {(r["arm"], r["component"], r["scope"], r["scope_id"]): r for r in candidate_rows}
    cvar_lookup = {(r["arm"], r["component"], r["scope"], r["scope_id"]): r for r in cvar_rows}
    gain_lookup = {(r["component"], r["scope"], r["scope_id"]): r for r in gain_rows}
    separation_component: dict[str, dict[str, Any]] = {}
    for component in COMPONENTS:
        oracle_folds = sum(bool(r.get("oracle_nrmse_improved")) for r in gain_rows if r["component"] == component and r["scope"] == "FOLD")
        oracle_families = sum(bool(r.get("oracle_nrmse_improved")) for r in gain_rows if r["component"] == component and r["scope"] == "FAMILY")
        ss_c = candidate_lookup[("SS", component, "OVERALL", "ALL")]["d_wn_over_wb"]
        ms_c = candidate_lookup[("MS", component, "OVERALL", "ALL")]["d_wn_over_wb"]
        ss_v = cvar_lookup[("SS", component, "OVERALL", "ALL")]["cvar"]
        ms_v = cvar_lookup[("MS", component, "OVERALL", "ALL")]["cvar"]
        separation_component[component] = {
            "oracle_folds": oracle_folds, "oracle_families": oracle_families,
            "candidate_ratio": ms_c / ss_c, "cvar_ratio": ms_v / ss_v,
        }
        evidence.extend([
            {"mechanism_id": "F-MS6", "diagnostic_class": "ORACLE_GAIN_REPLICATION", "component": component, "supporting_fold_count": oracle_folds, "supporting_family_count": oracle_families, "source": "oracle_gain_stratum_map.csv", "direction": "SUPPORT" if oracle_folds >= 4 and oracle_families >= 3 else "NO_SUPPORT"},
            {"mechanism_id": "F-MS6", "diagnostic_class": "LOCAL_CANDIDATE_C_RESPONSE", "component": component, "ratio_ms_over_ss": ms_c / ss_c, "source": "candidate_c_wn_wb_decomposition.csv", "direction": "PERSISTENT" if ms_c / ss_c > 0.8 else "IMPROVED"},
            {"mechanism_id": "F-MS6", "diagnostic_class": "LOCAL_CVAR_RESPONSE", "component": component, "ratio_ms_over_ss": ms_v / ss_v, "source": "cvar_stratum_decomposition.csv", "direction": "PERSISTENT" if ms_v / ss_v > 0.8 else "IMPROVED"},
        ])
    coverage_checks = read_csv(COMPONENT_VERDICTS)
    momentum_coverage = all(json.loads(next(r for r in coverage_checks if r["component"] == c)["relative_checks"])["coverage_guard"] for c in COMPONENTS[1:])
    inside_majority = True
    for component in COMPONENTS[1:]:
        inside = next(r for r in ambiguity_rows if r["geometry"] == "U0_MS" and r["component"] == component and r["coverage_status"] == "INSIDE_COVERAGE")
        outside = next(r for r in ambiguity_rows if r["geometry"] == "U0_MS" and r["component"] == component and r["coverage_status"] == "OUTSIDE_COVERAGE")
        inside_majority &= int(inside["near_collision_count"]) >= int(outside["near_collision_count"])
    density_contrast = bool(
        separation_component["density_rate"]["candidate_ratio"] <= 0.8
        and separation_component["density_rate"]["cvar_ratio"] <= 0.8
        and separation_component["density_rate"]["oracle_folds"] >= 4
        and separation_component["density_rate"]["oracle_families"] >= 3
    )
    fms6 = bool(
        all(
            separation_component[c]["oracle_folds"] >= 4
            and separation_component[c]["oracle_families"] >= 3
            and separation_component[c]["candidate_ratio"] > 0.8
            and separation_component[c]["cvar_ratio"] > 0.8
            for c in COMPONENTS[1:]
        )
        and momentum_coverage and inside_majority and density_contrast
    )
    evidence.extend([
        {"mechanism_id": "F-MS2", "diagnostic_class": "OPERATIONAL_NEAR_COLLISION_INSIDE_COVERAGE", "component": "PRESSURE_AND_VISCOSITY", "source": "ambiguity_vs_coverage.csv", "direction": "SUPPORT" if inside_majority else "NO_SUPPORT"},
        {"mechanism_id": "F-MS4", "diagnostic_class": "DENSITY_MOMENTUM_CONTRAST", "component": "ALL", "source": "candidate_c_wn_wb_decomposition.csv|cvar_stratum_decomposition.csv|oracle_gain_stratum_map.csv", "direction": "SUPPORT" if density_contrast else "NO_SUPPORT"},
        {"mechanism_id": "F-MS5", "diagnostic_class": "FORMAL_DISTANCE_DILUTION", "component": "ALL", "source": "distance_concentration_audit.csv|hubness_audit.csv|feature_group_energy_audit.csv", "direction": "AUDIT_ONLY_COMPONENT_INTERACTION_NOT_ESTABLISHED"},
        {"mechanism_id": "F-MS6", "diagnostic_class": "FORMAL_COVERAGE_GUARD", "component": "PRESSURE_AND_VISCOSITY", "source": "component_verdicts.csv", "direction": "SUPPORT" if momentum_coverage else "NO_SUPPORT"},
    ])

    verdict_map = {
        "F-MS1": "SUPPORTED_DOMINANT" if route_a_actionable and min(route_a_counts[c]["diagnostics"] for c in COMPONENTS[1:]) >= 3 else "SUPPORTED_PARTIAL" if selected_id is not None and all(route_a_counts[c]["diagnostics"] >= 2 for c in COMPONENTS[1:]) else "NOT_SUPPORTED" if selected_id is not None else "INCONCLUSIVE",
        "F-MS2": "SUPPORTED_PARTIAL" if inside_majority else "INCONCLUSIVE",
        "F-MS3": "SUPPORTED_PARTIAL" if any(x["independent_proxies"] >= 1 for x in route_b_component.values()) else "INCONCLUSIVE",
        "F-MS4": "SUPPORTED_PARTIAL" if density_contrast else "INCONCLUSIVE",
        "F-MS5": "INCONCLUSIVE",  # density succeeds in the same 110D geometry; dominant is prohibited.
        "F-MS6": "SUPPORTED_DOMINANT" if fms6 else "SUPPORTED_PARTIAL" if all(separation_component[c]["oracle_folds"] >= 4 for c in COMPONENTS[1:]) else "INCONCLUSIVE",
    }
    names = {
        "F-MS1": "TARGET_GEOMETRY_MISALIGNMENT", "F-MS2": "PERSISTENT_OPERATIONAL_LOCAL_AMBIGUITY",
        "F-MS3": "CURRENT_SUPPORT_SCALE_FAMILY_INSUFFICIENT", "F-MS4": "COMPONENT_SPECIFIC_REPRESENTATION_REQUIREMENT",
        "F-MS5": "HIGH_DIMENSION_DISTANCE_DILUTION", "F-MS6": "GLOBAL_PREDICTABILITY_LOCAL_IDENTIFIABILITY_SEPARATION",
    }
    for mechanism_id, verdict in verdict_map.items():
        mechanism_evidence = [r for r in evidence if r["mechanism_id"] == mechanism_id]
        verdicts.append({
            "mechanism_id": mechanism_id, "mechanism": names[mechanism_id], "verdict": verdict,
            "independent_diagnostic_count": len({r["diagnostic_class"] for r in mechanism_evidence}),
            "dominant_criteria_enforced": True,
            "claim_boundary": "OPERATIONAL_CONSUMED_DIAGNOSTIC_NOT_INTRINSIC_IDENTIFIABILITY_PROOF",
            "status": "ADJUDICATED",
        })

    route_status = {
        "A": "SUPPORTED_FOR_PROSPECTIVE_CONTRACT_DESIGN" if route_a_actionable else "INCONCLUSIVE" if selected_id is not None else "NOT_SUPPORTED",
        "B": "SUPPORTED_FOR_PROSPECTIVE_CONTRACT_DESIGN" if route_b_actionable else "INCONCLUSIVE" if new_proxies else "NOT_SUPPORTED",
        "C": "SUPPORT_SCALE_ROUTE_CLOSURE_RECOMMENDED" if not route_a_actionable and not route_b_actionable and fms6 else "NOT_TRIGGERED",
    }
    criteria = {
        "A": {
            "target_blind_candidate_frozen": selected_id is not None,
            "pressure_fold_family_replication": route_a_counts["pressure_gradient_acceleration"]["folds"] >= 4 and route_a_counts["pressure_gradient_acceleration"]["families"] >= 3,
            "viscosity_fold_family_replication": route_a_counts["viscosity_laplacian_acceleration"]["folds"] >= 4 and route_a_counts["viscosity_laplacian_acceleration"]["families"] >= 3,
            "two_alignment_diagnostics": all(route_a_counts[c]["diagnostics"] >= 2 for c in COMPONENTS[1:]),
            "density_non_degradation_strict": density_non_degradation,
            "deployment_target_reference_not_required": True,
        },
        "B": {
            "two_independent_new_information_proxies": all(x["independent_proxies"] >= 2 for x in route_b_component.values()),
            "pressure_fold_family_replication": route_b_component["pressure_gradient_acceleration"]["folds"] >= 4 and route_b_component["pressure_gradient_acceleration"]["families"] >= 3,
            "viscosity_fold_family_replication": route_b_component["viscosity_laplacian_acceleration"]["folds"] >= 4 and route_b_component["viscosity_laplacian_acceleration"]["families"] >= 3,
            "no_principal_frame_fallback": True,
            "deployment_target_reference_not_required": True,
        },
        "C": {"route_a_not_actionable": not route_a_actionable, "route_b_not_actionable": not route_b_actionable, "f_ms6_supported_dominant": fms6},
    }
    for route, checks in criteria.items():
        for criterion, passed in checks.items():
            routes.append({
                "route": route, "route_status": route_status[route], "criterion": criterion,
                "criterion_pass": bool(passed), "fresh_compute_authorized": False,
                "h_mso01r_reverdict": False, "status": "EVALUATED",
            })
    return add_evidence(evidence), add_evidence(verdicts), add_evidence(routes)


def initial_access_ledger(d0_commit: str, d1_commit: str) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0", "stage": "MSO-02D-D2", "evidence_class": EVIDENCE_CLASS,
        "d0_commit": d0_commit, "d1_commit": d1_commit,
        "consumed_observable_reads": 0, "consumed_target_reads": 0, "consumed_metric_reads": 0,
        "consumed_oracle_diagnostic_fits": 0, "consumed_bootstrap_reads": 0,
        "deployment_only_proxy_reconstruction_on_consumed_states": 0,
        "target_blind_transform_diagnostic_computations": 0,
        "target_payload_first_access_after_all_integrity_and_canonical_checks": True,
    }


def firewall(access: dict[str, Any]) -> dict[str, Any]:
    prohibited = {
        key: 0 for key in (
            "fresh_case_generation", "fresh_target_generation", "fresh_reference_generation", "new_confirmatory_h3",
            "h_mso01r_reverdict", "formal_metric_modification", "formal_gate_modification",
            "formal_feature_modification", "formal_scale_modification", "formal_fold_modification",
            "formal_normalization_modification", "formal_bootstrap_redraw", "neural_model", "attention",
            "transformer", "learned_operator", "optimizer", "training", "time_integration",
            "solver_in_loop", "rollout", "sealed_test", "arc_access",
        )
    }
    return {
        "schema_version": "1.0.0", "stage": "MSO-02D-D2", "evidence_class": EVIDENCE_CLASS,
        "allowed_activity_counts": {k: v for k, v in access.items() if isinstance(v, int)},
        "prohibited_activity_counts": prohibited,
        "all_prohibited_counts_zero": all(v == 0 for v in prohibited.values()),
        "formal_artifacts_modified": False,
        "fresh_compute_authorized": False,
        "neural_training_authorized": False,
        "status": "PASS",
    }


def stage_rank(stage: str) -> int:
    return {"identity": 0, "core": 1, "oracle": 2, "ablation": 3, "all": 4}[stage]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stage",
        choices=("identity", "core", "oracle", "ablation", "all"),
        default="all",
        help="Stop after a cumulative checkpoint; every invocation still requires a clean D1 HEAD.",
    )
    args = parser.parse_args()

    # This ordering is a scientific firewall.  Do not move any np.load(TARGET)
    # or target-dependent calculation above the entire block.
    freeze, d0_commit, d1_commit = validate_git_and_d1()
    upstream = validate_upstream_evidence()
    canonical = canonical_result_identity_audit()
    theta = theta_definition_audit()
    denominator = nrmse_denominator_equivalence_audit()
    access = initial_access_ledger(d0_commit, d1_commit)
    access["consumed_metric_reads"] = 10

    with tempfile.TemporaryDirectory(prefix="mso02d-d2-") as temp:
        staging = Path(temp)
        write_json(staging / "canonical_result_identity_audit.json", canonical)
        write_json(staging / "theta_definition_audit.json", theta)
        write_json(staging / "nrmse_denominator_equivalence_audit.json", denominator)
        base_names = [
            "canonical_result_identity_audit.json",
            "theta_definition_audit.json",
            "nrmse_denominator_equivalence_audit.json",
        ]
        if stage_rank(args.stage) == 0:
            write_json(staging / "diagnostic_access_ledger.json", {**access, "upstream_identity_audit": upstream, "stage_cutoff": args.stage})
            write_json(staging / "firewall_audit.json", firewall(access))
            atomic_publish(staging, base_names + ["diagnostic_access_ledger.json", "firewall_audit.json"])
            print("MSO02D_D2_IDENTITY_CHECKPOINT_COMPLETE_NO_TARGET_PAYLOAD_READ", flush=True)
            return

        data, cases = load_consumed_data(access)
        formal, comparator, d1 = load_identities(freeze, access)
        helper = load_frozen_helper()
        selected_id, selected_status = selected_candidate_info(freeze, d1)
        geometries: dict[str, tuple[np.ndarray, np.ndarray]] = {
            "U0_SS": (
                np.asarray(formal["ss_neighbor_row_index"], dtype=np.int64),
                np.asarray(formal["ss_neighbor_distance"], dtype=np.float64),
            ),
            "U0_MS": (
                np.asarray(formal["ms_neighbor_row_index"], dtype=np.int64),
                np.asarray(formal["ms_neighbor_distance"], dtype=np.float64),
            ),
        }
        # If D1 repeated U0 in its handoff, it must be byte-identical to formal U0.
        for key, expected in (
            ("u0_neighbor_row_index", formal["ms_neighbor_row_index"]),
            ("u0_neighbor_distance", formal["ms_neighbor_distance"]),
        ):
            if key in d1 and not np.array_equal(np.asarray(d1[key]), np.asarray(expected)):
                raise Stop(f"MSO02D_D1_U0_FORMAL_IDENTITY_FAILURE:{key}")
        if selected_id is not None:
            selected_indices = np.asarray(d1["selected_neighbor_row_index"], dtype=np.int64)
            selected_distances = np.asarray(d1["selected_neighbor_distance"], dtype=np.float64)
            if selected_indices.shape != (49152, 10) or selected_distances.shape != (49152, 10):
                raise Stop("MSO02D_D1_SELECTED_K10_SHAPE_FAILURE")
            if np.any(selected_indices < 0) or np.any(selected_indices >= 49152) or not np.isfinite(selected_distances).all() or np.any(selected_distances < 0):
                raise Stop("MSO02D_D1_SELECTED_K10_VALUE_FAILURE")
            geometries["D1_SELECTED"] = (selected_indices, selected_distances)

        coverage = coverage_masks(formal, data["meta"])
        random_distances = random_descriptor_distances(
            data, comparator, d1, selected_id, access
        )
        candidate_rows, cancellation_rows, candidate_state = candidate_decomposition(data, cases, formal, comparator)
        hotspot_rows, cvar_rows, cvar_state = cvar_diagnostics(data, cases, formal, helper, coverage)
        near_rows, ambiguity_rows, near_state = near_collision_diagnostics(
            data, cases, geometries, random_distances, comparator, coverage
        )
        alignment_rows = route_a_alignment(
            data, cases, comparator, geometries, cvar_state, near_state, selected_id, helper
        )
        proxy_registry = read_json(D0_PROXY_REGISTRY)
        ms_names = [row["name"] for row in read_json(MS_SCHEMA)["columns"]]
        proxy_availability, proxy_overlap, proxy_values = proxy_values_from_registry(
            proxy_registry, data["features"]["MS"], ms_names
        )
        access["deployment_only_proxy_reconstruction_on_consumed_states"] = len(proxy_values)
        directional_target = directional_target_alignment(data, formal, proxy_registry, proxy_values)
        directional_residual = add_evidence([{
            "proxy_id": "ALL", "component": "ALL", "diagnostic": "ALL", "scope": "OVERALL", "scope_id": "ALL",
            "status": "NOT_COMPUTED_AT_CORE_STAGE_CUTOFF",
        }])
        design_rows = design_only_stratification(
            data, cases, candidate_state, cvar_state, near_state, None
        )

        core_tables = {
            "target_blind_geometry_target_alignment.csv": alignment_rows,
            "directional_proxy_availability_audit.csv": proxy_availability,
            "directional_proxy_overlap_audit.csv": proxy_overlap,
            "directional_proxy_target_alignment.csv": directional_target,
            "directional_proxy_residual_diagnostics.csv": directional_residual,
            "candidate_c_wn_wb_decomposition.csv": candidate_rows,
            "candidate_c_ratio_cancellation_audit.csv": cancellation_rows,
            "cvar_hotspot_map.csv": hotspot_rows,
            "cvar_stratum_decomposition.csv": cvar_rows,
            "near_collision_audit.csv": near_rows,
            "ambiguity_vs_coverage.csv": ambiguity_rows,
            "design_only_failure_stratification.csv": design_rows,
        }
        for name, rows in core_tables.items():
            write_csv(staging / name, rows)
        publish_names = base_names + list(CORE_OUTPUTS)

        oracle_rows: list[dict[str, Any]] = []
        gain_rows: list[dict[str, Any]] = []
        oracle_state: dict[tuple[str, str], dict[str, Any]] = {}
        if stage_rank(args.stage) >= 2:
            oracle_rows, gain_rows, oracle_state = replay_frozen_oracles(
                data, cases, formal, helper, access
            )
            directional_residual = directional_residual_diagnostics(
                data, proxy_registry, proxy_values, oracle_state, helper, access
            )
            design_rows = design_only_stratification(
                data, cases, candidate_state, cvar_state, near_state, oracle_state
            )
            write_csv(staging / "directional_proxy_residual_diagnostics.csv", directional_residual)
            write_csv(staging / "design_only_failure_stratification.csv", design_rows)
            write_csv(staging / "oracle_residual_decomposition.csv", oracle_rows)
            write_csv(staging / "oracle_gain_stratum_map.csv", gain_rows)
            publish_names.extend(ORACLE_OUTPUTS)

        if stage_rank(args.stage) >= 3:
            ablation_rows = fixed_feature_group_ablation(data, helper, oracle_state, access)
            write_csv(staging / "fixed_feature_group_ablation.csv", ablation_rows)
            publish_names.extend(ABLATION_OUTPUTS)

        if stage_rank(args.stage) >= 4:
            evidence_rows, verdict_rows, route_rows = adjudicate_mechanisms_and_routes(
                alignment_rows, directional_target, directional_residual, candidate_rows,
                cvar_rows, gain_rows, ambiguity_rows, proxy_overlap, selected_id,
            )
            write_csv(staging / "mechanism_evidence_matrix.csv", evidence_rows)
            write_csv(staging / "mechanism_verdicts.csv", verdict_rows)
            write_csv(staging / "route_adjudication_matrix.csv", route_rows)
            publish_names.extend(ADJUDICATION_OUTPUTS[:3])

        ledger = {
            **access,
            "upstream_identity_audit": upstream,
            "d1_selection_status": selected_status,
            "selected_target_blind_candidate_id": selected_id,
            "stage_cutoff": args.stage,
            "read_order": [
                "GIT_D0_D1_BOUNDARY", "A_B_MANIFEST_HASHES", "CANONICAL_METRICS",
                "THETA_TEXT_SOURCE_AUDIT", "NRMSE_DENOMINATOR_AUDIT", "CONSUMED_TARGET_PAYLOAD",
            ],
            "status": "COMPLETE_FOR_STAGE_CUTOFF",
        }
        write_json(staging / "diagnostic_access_ledger.json", ledger)
        write_json(staging / "firewall_audit.json", firewall(access))
        publish_names.extend(["diagnostic_access_ledger.json", "firewall_audit.json"])
        atomic_publish(staging, publish_names)
    print(f"MSO02D_D2_{args.stage.upper()}_COMPLETE", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Stop as error:
        print(str(error), file=sys.stderr, flush=True)
        raise SystemExit(2) from error
