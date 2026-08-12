#!/usr/bin/env python3
"""Run the frozen H-MSO-01R-B confirmatory analysis.

Candidate C is the only formal descriptor-nearest-neighbour statistic here.
The real execution consumes the frozen H-MSO-01R-A neighbour, comparator,
normalization, coverage and bootstrap identities.  It has no neural model,
optimizer, training, time integration, solver-in-loop, rollout, sealed-test,
or ARC path.
"""

from __future__ import annotations

from collections import defaultdict
import argparse
import csv
import hashlib
import importlib.util
import json
import math
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
from typing import Any, Callable

import numpy as np
from sklearn.preprocessing import PolynomialFeatures


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "06_experiments/hmso01r_b"
FREEZE = ROOT / "08_manifests/hmso01r_b_pre_target_freeze.json"
ATLAS = ROOT / "05_registries/hmso01r_a_formal_fresh_atlas_registry.json"
SAMPLE = ROOT / "05_registries/hmso01r_a_formal_particle_sample_registry.json"
OBSERVABLE = ROOT / "06_experiments/hmso01r_a/observable/hmso01r_a_observable_store.npz"
TARGET = OUT / "target_ref/hmso01r_b_target_store.npz"
TARGET_LEDGER = OUT / "target_access_ledger.json"
NORMALIZATION = ROOT / "06_experiments/hmso01r_a/fold_normalization_registry.json"
SS_SCHEMA = ROOT / "06_experiments/hmso01r_a/ss_observable_schema_identity.json"
MS_SCHEMA = ROOT / "06_experiments/hmso01r_a/ms_observable_schema_identity.json"
NEIGHBOURS = ROOT / "06_experiments/hmso01r_a/descriptor_neighbor_identities.npz"
RANDOM = ROOT / "06_experiments/hmso01r_a/random_baseline_identities.npz"
COVERAGE_GEOMETRY = ROOT / "06_experiments/hmso01r_a/coverage_geometry_freeze.json"
BOOTSTRAP = ROOT / "06_experiments/hmso01r_a/bootstrap_draws.npz"
BOOTSTRAP_REGISTRY = ROOT / "05_registries/hmso01r_a_bootstrap_registry.json"
PREFLIGHT = OUT / "candidate_c_implementation_preflight.json"

JOIN_AUDIT = OUT / "target_observable_join_audit.csv"
SS_CANDIDATE = OUT / "ss_candidate_c_dnn_metrics.csv"
MS_CANDIDATE = OUT / "ms_candidate_c_dnn_metrics.csv"
PAIRED_CANDIDATE = OUT / "candidate_c_paired_rescue_metrics.csv"
CANDIDATE_BOUNDS = OUT / "candidate_c_bootstrap_bounds.csv"
DIVISION_AUDIT = OUT / "candidate_c_division_audit.json"
SS_CVAR = OUT / "ss_conditional_variance_metrics.csv"
MS_CVAR = OUT / "ms_conditional_variance_metrics.csv"
SS_ORACLE = OUT / "ss_oracle_metrics.csv"
MS_ORACLE = OUT / "ms_oracle_metrics.csv"
COVERAGE = OUT / "coverage_metrics.csv"
PAIRED_NON_DNN = OUT / "paired_non_dnn_rescue_metrics.csv"
ALL_BOUNDS = OUT / "bootstrap_simultaneous_bounds.csv"
VERDICTS = OUT / "component_verdicts.csv"
SUMMARY = OUT / "formal_summary.json"
FIREWALL = OUT / "firewall_audit.json"
STAGING = OUT / ".formal_staging"
TRANSACTION = STAGING / "transaction.json"
LEGACY_HELPER = ROOT / "06_experiments/mso02b/run_mso02b_formal.py"
EXPECTED_LEGACY_HELPER_SHA = "55b0b63eb2c99364c8a2e96c75191a50707e93357f7039bd9edfdcb7c7c831b7"

EXPECTED_OBSERVABLE_SHA = "65ca1a7fea58248207fc5a22e14855b4a84c392c7ef17cefdf2d396687cc38cd"
EXPECTED_BOOTSTRAP_SHA = "3a5853ce6b353c8c2584b0f95651904fb1506a0a3e3af6985981374789d4667e"
EXPECTED_NEIGHBOURS_SHA = "1d98e7c2038c9d6b7391b1ab953084dfafb47ef3ade7c62815c9f676694408b4"
EXPECTED_RANDOM_SHA = "74268059f33c5fc9ec885ccb1ef7f61b22120f4eac7e9862bab6fddc844d8b07"
CA_ZERO_STATUS = "NO_AGGREGATE_RANDOM_CONTRAST_NOT_EVALUABLE"
CURRENT_ZERO_ALIAS = "DNN_NOT_EVALUABLE_ZERO_AGGREGATE_RANDOM_BASELINE"
ZERO_SS_STATUS = "RELATIVE_RESCUE_NOT_EVALUABLE_ZERO_SS_BASELINE"
EXACT_ZERO_MS_STATUS = "EXACT_ZERO_MS_DOMINANCE"
NON_DNN_VARIANCE_NE = "NOT_EVALUABLE_DEVELOPMENT_TARGET_VARIANCE_NONPOSITIVE_OR_NONFINITE"
NON_DNN_ORACLE_NE = "NOT_EVALUABLE_ORACLE_SELECTION_PREDICTION_OR_TARGET_RMS_INVALID"
NON_DNN_BASELINE_NE = "NOT_EVALUABLE_MEAN_BASELINE_NONPOSITIVE_OR_ORACLE_INVALID"
NON_DNN_COVERAGE_NE = "NOT_EVALUABLE_COVERAGE_GEOMETRY_INVALID"
NON_DNN_BOOTSTRAP_NE = "NOT_EVALUABLE_EXCESS_DEGENERATE_OR_INSUFFICIENT_EFFECTIVE_LINEAGE_BOOTSTRAP"
NON_DNN_RATIO_NE = "NOT_EVALUABLE_UNSTABLE_RATIO_NO_FROZEN_ABSOLUTE_DIFFERENCE_MARGIN"
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
ARMS = ("SS", "MS")
FAMILIES = ("F1", "F2", "F3", "F4")
FOLDS = tuple(range(6))
ORACLES = ("knn5", "knn10", "knn20", "ridge", "polynomial_ridge")
POLY_SUBSET = (
    "obs__base_neighbor_count_over_nominal",
    "obs__base_cov_eig_ratio",
    "obs__base_kernel_s0_minus_1",
    "obs__base_first_moment_error_fro",
    "obs__base_grad_constant_norm_times_h",
    "obs__rho",
    "obs__local_dv_rms",
)
DIMENSIONLESS_FLOOR = 128.0 * np.finfo(np.float64).eps

REAL_OUTPUTS = (
    JOIN_AUDIT, SS_CANDIDATE, MS_CANDIDATE, PAIRED_CANDIDATE,
    CANDIDATE_BOUNDS, DIVISION_AUDIT, SS_CVAR, MS_CVAR, SS_ORACLE,
    MS_ORACLE, COVERAGE, PAIRED_NON_DNN, ALL_BOUNDS, VERDICTS,
    SUMMARY, FIREWALL,
)
_STAGING_ACTIVE = False

VENDOR_OPERATOR_PATHS = {
    "01_provenance/vendor/pio_stage01c_static/structure_preserving/__init__.py",
    "01_provenance/vendor/pio_stage01c_static/structure_preserving/neighborhood.py",
    "01_provenance/vendor/pio_stage01c_static/structure_preserving/kernels.py",
    "01_provenance/vendor/pio_stage01c_static/structure_preserving/conservative_pressure.py",
    "01_provenance/vendor/pio_stage01c_static/structure_preserving/conservative_viscosity.py",
}
REQUIRED_FREEZE_PATHS = {
    "00_project_contract/amendments/ca_mso01_zero_safe_dnn_semantics.md",
    "00_project_contract/hmso01r_a_fresh_requalification_atlas_freeze_contract.md",
    "00_project_contract/hmso01r_b_fresh_confirmatory_execution_contract.md",
    "01_provenance/hmso01r_b_target_reference_import_manifest.csv",
    "01_provenance/vendor/ddo_analytical_reference/mso02b_target_reference.py",
    "05_registries/hmso01r_a_formal_fresh_atlas_registry.json",
    "05_registries/hmso01r_a_formal_particle_sample_registry.json",
    "05_registries/hmso01r_a_lineage_fold_registry.json",
    "05_registries/hmso01r_a_bootstrap_registry.json",
    "05_registries/hmso01r_a_random_baseline_identity_registry.json",
    "05_registries/hmso01r_b_target_role_registry.json",
    "06_experiments/hmso01r_a/fold_normalization_registry.json",
    "06_experiments/hmso01r_a/ss_observable_schema_identity.json",
    "06_experiments/hmso01r_a/ms_observable_schema_identity.json",
    "06_experiments/hmso01r_a/descriptor_geometry_freeze.json",
    "06_experiments/hmso01r_a/descriptor_neighbor_identities.npz",
    "06_experiments/hmso01r_a/random_baseline_identities.npz",
    "06_experiments/hmso01r_a/bootstrap_draws.npz",
    "06_experiments/hmso01r_a/coverage_geometry_freeze.json",
    "06_experiments/hmso01r_a/observable/hmso01r_a_observable_store.npz",
    "06_experiments/hmso01r_b/build_hmso01r_b_targets.py",
    "06_experiments/hmso01r_b/run_hmso01r_b_formal.py",
    "06_experiments/hmso01r_b/finalize_hmso01r_b_release.py",
    "06_experiments/hmso01r_b/candidate_c_implementation_preflight.json",
    "06_experiments/mso02b/build_mso02b_targets.py",
    "06_experiments/mso02b/run_mso02b_formal.py",
    "08_manifests/mso00_manifest.json",
    "08_manifests/mso01_manifest.json",
    "08_manifests/mso01_status_ledger.json",
    "08_manifests/mso02a_manifest.json",
    "08_manifests/mso02a_status_ledger.json",
    "08_manifests/mso02b_manifest.json",
    "08_manifests/mso02b_status_ledger.json",
    "08_manifests/mso02c_g1_ab_attribution_manifest.json",
    "08_manifests/mso02c_g1_ab_attribution_status_ledger.json",
    "08_manifests/mso02c_g2_manifest.json",
    "08_manifests/mso02c_g2_status_ledger.json",
    "08_manifests/hmso01r_a_manifest.json",
    "08_manifests/hmso01r_a_status_ledger.json",
    "08_manifests/hmso01r_a_git_handoff.json",
    *VENDOR_OPERATOR_PATHS,
}
PROHIBITED_FROZEN_PREFIXES = (
    "06_experiments/mso00/", "06_experiments/mso01/",
    "06_experiments/mso02a/", "06_experiments/mso02b/checkpoints/",
    "06_experiments/mso02b/target_ref/", "06_experiments/mso02c/",
    "07_reports/mso",
)
PROHIBITED_FROZEN_EXACT = {
    "06_experiments/mso02b/target_access_ledger.json",
    "06_experiments/mso02b/target_reference_qualification.csv",
    "06_experiments/mso02b/target_observable_join_audit.csv",
    "06_experiments/mso02b/bootstrap_simultaneous_bounds.csv",
    "06_experiments/mso02b/component_verdicts.csv",
    "06_experiments/mso02b/coverage_metrics.csv",
    "06_experiments/mso02b/firewall_audit.json",
    "06_experiments/mso02b/mso02b_formal_summary.json",
    "06_experiments/mso02b/ms_conditional_variance_metrics.csv",
    "06_experiments/mso02b/ms_dnn_metrics.csv",
    "06_experiments/mso02b/ms_oracle_metrics.csv",
    "06_experiments/mso02b/paired_rescue_metrics.csv",
    "06_experiments/mso02b/ss_conditional_variance_metrics.csv",
    "06_experiments/mso02b/ss_dnn_metrics.csv",
    "06_experiments/mso02b/ss_oracle_metrics.csv",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def output_path(path: Path) -> Path:
    """Resolve a formal output to its private transaction staging path."""
    if _STAGING_ACTIVE and path in REAL_OUTPUTS:
        return STAGING / path.name
    return path


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def git_blob_oid(path: Path, commit: str = "HEAD") -> str:
    relative = path.relative_to(ROOT).as_posix()
    raw = subprocess.run(
        ["git", "ls-tree", "-z", commit, "--", relative], cwd=ROOT,
        check=True, capture_output=True,
    ).stdout
    records = [item for item in raw.split(b"\0") if item]
    if len(records) != 1:
        raise RuntimeError(f"HMSO01R_B_GIT_BLOB_IDENTITY_FAILURE:{relative}")
    return records[0].split(b"\t", 1)[0].decode().split()[2]


def git_blob_bytes(commit: str, relative: str) -> bytes:
    return subprocess.run(
        ["git", "cat-file", "blob", f"{commit}:{relative}"], cwd=ROOT,
        check=True, capture_output=True,
    ).stdout


def safe_relative(value: str) -> str:
    pure = PurePosixPath(value)
    if pure.is_absolute() or ".." in pure.parts or pure.as_posix() != value:
        raise RuntimeError(f"HMSO01R_B_INVALID_FROZEN_PATH:{value}")
    return value


def staging_allowed_names() -> set[str]:
    names = {path.name for path in REAL_OUTPUTS} | {TRANSACTION.name}
    return names | {name + ".tmp" for name in names} | {
        ".publish." + path.name for path in REAL_OUTPUTS
    }


def inspect_staging() -> list[Path]:
    if not STAGING.exists():
        return []
    if not STAGING.is_dir() or STAGING.is_symlink():
        raise RuntimeError("HMSO01R_B_FORMAL_STAGING_NOT_PRIVATE_DIRECTORY")
    entries = list(STAGING.iterdir())
    allowed = staging_allowed_names()
    for entry in entries:
        if entry.name not in allowed or not entry.is_file() or entry.is_symlink():
            raise RuntimeError(f"HMSO01R_B_FORMAL_STAGING_UNEXPECTED_ENTRY:{entry.name}")
    return entries


def clear_incomplete_staging() -> None:
    """Clear only a proved partial transaction with no published final output."""
    entries = inspect_staging()
    if any(path.exists() for path in REAL_OUTPUTS):
        raise RuntimeError("HMSO01R_B_FORMAL_INCOMPLETE_STAGING_WITH_FINAL_OUTPUT")
    for entry in entries:
        entry.unlink()
    if STAGING.exists():
        STAGING.rmdir()


def publish_transaction() -> dict[str, Any]:
    """Resume or complete an exact, fully hashed formal-output publication."""
    inspect_staging()
    if not TRANSACTION.is_file() or TRANSACTION.is_symlink():
        raise RuntimeError("HMSO01R_B_FORMAL_TRANSACTION_MANIFEST_MISSING")
    transaction = json.loads(TRANSACTION.read_text(encoding="utf-8"))
    required_keys = {
        "schema_version", "stage", "status", "formal_evaluator_sha256",
        "target_store_sha256", "pre_target_commit", "output_sha256",
        "summary_published_last",
    }
    if set(transaction) != required_keys:
        raise RuntimeError("HMSO01R_B_FORMAL_TRANSACTION_SCHEMA_FAILURE")
    target_ledger = json.loads(TARGET_LEDGER.read_text(encoding="utf-8"))
    ledger_commit = str(target_ledger.get(
        "hmso01r_b_pre_target_commit", target_ledger.get("pre_target_commit")
    ))
    output_hashes = transaction["output_sha256"]
    expected_names = {path.name for path in REAL_OUTPUTS}
    if (
        transaction["schema_version"] != "1.0.0"
        or transaction["stage"] != "H-MSO-01R-B_FORMAL_OUTPUT_TRANSACTION"
        or transaction["status"] not in {"COMPLETE_READY_TO_PUBLISH", "PUBLISHED_COMPLETE"}
        or transaction["formal_evaluator_sha256"] != sha256(Path(__file__).resolve())
        or transaction["target_store_sha256"] != sha256(TARGET)
        or transaction["pre_target_commit"] != ledger_commit
        or transaction["pre_target_commit"] != git("rev-parse", "HEAD")
        or transaction["summary_published_last"] is not True
        or not isinstance(output_hashes, dict)
        or set(output_hashes) != expected_names
    ):
        raise RuntimeError("HMSO01R_B_FORMAL_TRANSACTION_BINDING_FAILURE")
    if transaction["status"] == "COMPLETE_READY_TO_PUBLISH":
        if SUMMARY.exists() and any(not final.exists() for final in REAL_OUTPUTS if final != SUMMARY):
            raise RuntimeError("HMSO01R_B_FORMAL_SUMMARY_WAS_NOT_PUBLISHED_LAST")
        for final in REAL_OUTPUTS:
            staged = STAGING / final.name
            if not staged.is_file() or staged.is_symlink() or sha256(staged) != output_hashes[final.name]:
                raise RuntimeError(f"HMSO01R_B_FORMAL_STAGED_OUTPUT_IDENTITY_FAILURE:{final.name}")
            if final.exists() and (not final.is_file() or final.is_symlink() or sha256(final) != output_hashes[final.name]):
                raise RuntimeError(f"HMSO01R_B_FORMAL_PUBLISHED_OUTPUT_CONFLICT:{final.name}")
        publication_order = [path for path in REAL_OUTPUTS if path != SUMMARY] + [SUMMARY]
        for final in publication_order:
            if final.exists():
                continue
            publish_copy = STAGING / (".publish." + final.name)
            shutil.copyfile(STAGING / final.name, publish_copy)
            if sha256(publish_copy) != output_hashes[final.name]:
                raise RuntimeError(f"HMSO01R_B_FORMAL_PUBLICATION_COPY_FAILURE:{final.name}")
            publish_copy.replace(final)
    for final in REAL_OUTPUTS:
        if sha256(final) != output_hashes[final.name]:
            raise RuntimeError(f"HMSO01R_B_FORMAL_PUBLICATION_IDENTITY_FAILURE:{final.name}")
    terminal_summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    if transaction["status"] != "PUBLISHED_COMPLETE":
        transaction["status"] = "PUBLISHED_COMPLETE"
        write_json(TRANSACTION, transaction)
    for entry in inspect_staging():
        if entry != TRANSACTION:
            entry.unlink()
    if TRANSACTION.exists():
        TRANSACTION.unlink()
    STAGING.rmdir()
    return terminal_summary


def resume_or_prepare_staging() -> dict[str, Any] | None:
    """Resume a complete publication, or safely clear only a partial private stage."""
    if STAGING.exists():
        entries = inspect_staging()
        if TRANSACTION in entries:
            return publish_transaction()
        if all(path.is_file() and not path.is_symlink() for path in REAL_OUTPUTS):
            summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
            hashes = summary.get("formal_output_sha256", {})
            if not isinstance(hashes, dict) or any(
                hashes.get(path.relative_to(ROOT).as_posix()) != sha256(path)
                for path in REAL_OUTPUTS if path != SUMMARY
            ):
                raise RuntimeError("HMSO01R_B_FORMAL_PUBLISHED_RECOVERY_IDENTITY_FAILURE")
            for entry in entries:
                entry.unlink()
            STAGING.rmdir()
            return summary
        clear_incomplete_staging()
    if any(path.exists() for path in REAL_OUTPUTS):
        raise RuntimeError("HMSO01R_B_FORMAL_OUTPUT_ALREADY_EXISTS_REFUSING_REPLACEMENT")
    return None


def validate_freeze_records(freeze: dict[str, Any], pre_target_commit: str) -> dict[str, dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for group in ("frozen_inputs", "execution_artifacts"):
        values = freeze.get(group)
        if not isinstance(values, list) or not values or not all(isinstance(row, dict) for row in values):
            raise RuntimeError(f"HMSO01R_B_PRE_TARGET_FREEZE_SECTION_FAILURE:{group}")
        records.extend(values)
    required_fields = {
        "path", "sha256", "size_bytes", "git_blob_oid", "git_blob_sha256",
        "role", "stage", "source", "consumption_status",
    }
    verified: dict[str, dict[str, Any]] = {}
    for record in records:
        if not required_fields.issubset(record):
            missing = sorted(required_fields - set(record))
            raise RuntimeError("HMSO01R_B_PRE_TARGET_FREEZE_ROW_SCHEMA_FAILURE:" + ",".join(missing))
        relative = safe_relative(str(record["path"]))
        if relative in verified:
            raise RuntimeError(f"HMSO01R_B_DUPLICATE_FROZEN_ARTIFACT:{relative}")
        if relative in PROHIBITED_FROZEN_EXACT or any(relative.startswith(prefix) for prefix in PROHIBITED_FROZEN_PREFIXES):
            raise RuntimeError(f"HMSO01R_B_PROHIBITED_HISTORICAL_FROZEN_PATH:{relative}")
        for field in ("role", "stage", "source", "consumption_status"):
            if not isinstance(record[field], str) or not record[field].strip():
                raise RuntimeError(f"HMSO01R_B_PRE_TARGET_FREEZE_ROW_SCHEMA_FAILURE:{relative}:{field}")
        expected_sha = str(record["sha256"])
        if len(expected_sha) != 64 or any(character not in "0123456789abcdef" for character in expected_sha):
            raise RuntimeError(f"HMSO01R_B_INVALID_FROZEN_SHA256:{relative}")
        path = ROOT / relative
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(f"HMSO01R_B_FROZEN_INPUT_NOT_REGULAR_FILE:{relative}")
        blob = git_blob_bytes(pre_target_commit, relative)
        blob_sha = hashlib.sha256(blob).hexdigest()
        oid = git_blob_oid(path, pre_target_commit)
        actual_sha = sha256(path)
        actual_size = path.stat().st_size
        if not (
            int(record["size_bytes"]) == actual_size
            and str(record["git_blob_oid"]) == oid
            and str(record["git_blob_sha256"]) == blob_sha
            and expected_sha == actual_sha == blob_sha
        ):
            raise RuntimeError(f"HMSO01R_B_FORMAL_FROZEN_IDENTITY_FAILURE:{relative}")
        verified[relative] = {
            "sha256": actual_sha, "size_bytes": actual_size,
            "git_blob_oid": oid, "git_blob_sha256": blob_sha,
            "role": record["role"], "stage": record["stage"],
            "source": record["source"], "consumption_status": record["consumption_status"],
        }
    if set(verified) != REQUIRED_FREEZE_PATHS:
        raise RuntimeError(
            "HMSO01R_B_PRE_TARGET_FREEZE_PATHSET_FAILURE:"
            + json.dumps({
                "missing": sorted(REQUIRED_FREEZE_PATHS - set(verified)),
                "unexpected": sorted(set(verified) - REQUIRED_FREEZE_PATHS),
            }, sort_keys=True)
        )
    return verified


def require_true(value: Any, field: str) -> None:
    if value is not True:
        raise RuntimeError(f"HMSO01R_B_REQUIRED_TRUE_FAILURE:{field}")


def validate_preflight_attestation(
    preflight: dict[str, Any], verified: dict[str, dict[str, Any]], pre_target_commit: str,
) -> None:
    evaluator_relative = Path(__file__).resolve().relative_to(ROOT).as_posix()
    preflight_relative = PREFLIGHT.relative_to(ROOT).as_posix()
    if preflight.get("status") != "PASS":
        raise RuntimeError("HMSO01R_B_FORMAL_PREFLIGHT_STATUS_FAILURE")
    require_true(preflight.get("pass"), "preflight.pass")
    require_true(preflight.get("passed"), "preflight.passed")
    executable = preflight.get("executable_identity")
    bootstrap = preflight.get("bootstrap")
    division = preflight.get("division_audit")
    firewall = preflight.get("firewall")
    scenarios = preflight.get("scenario_coverage")
    scenario_results = preflight.get("scenarios")
    cutoff_evidence = preflight.get("candidate_c_degeneracy_cutoff_evidence")
    if not all(isinstance(value, dict) for value in (
        executable, bootstrap, division, firewall, scenarios, scenario_results,
        cutoff_evidence,
    )):
        raise RuntimeError("HMSO01R_B_FORMAL_PREFLIGHT_SCHEMA_FAILURE")
    evaluator_sha = verified[evaluator_relative]["sha256"]
    evaluator_oid = verified[evaluator_relative]["git_blob_oid"]
    if not (
        preflight.get("formal_evaluator_sha256") == evaluator_sha
        and preflight.get("formal_evaluator_git_blob_oid") == evaluator_oid
        and executable.get("sha256") == evaluator_sha
        and executable.get("git_blob_oid") == evaluator_oid
        and evaluator_sha == sha256(Path(__file__).resolve())
        and evaluator_oid == git_blob_oid(Path(__file__).resolve(), pre_target_commit)
        and verified[preflight_relative]["sha256"] == sha256(PREFLIGHT)
    ):
        raise RuntimeError("HMSO01R_B_FORMAL_PREFLIGHT_EXECUTABLE_IDENTITY_FAILURE")
    if not (
        int(preflight.get("bootstrap_draw_count", -1)) == 10000
        and int(preflight.get("bootstrap_unique_draw_count", -1)) == 10000
        and preflight.get("bootstrap_draws_sha256") == EXPECTED_BOOTSTRAP_SHA
        and preflight.get("bootstrap_draw_identity_match") is True
        and int(bootstrap.get("draw_count", -1)) == 10000
        and int(bootstrap.get("draws_consumed", -1)) == 10000
        and int(bootstrap.get("unique_draw_count", -1)) == 10000
        and bootstrap.get("draws_sha256") == EXPECTED_BOOTSTRAP_SHA
        and bootstrap.get("draw_identity_match") is True
        and bootstrap.get("paired_ss_ms_identity") is True
        and bootstrap.get("paired_component_identity") is True
        and bootstrap.get("per_draw_reaggregation") is True
        and int(bootstrap.get("decoded_case_emission_count", 0)) > 0
        and int(bootstrap.get("decoded_lineage_occurrence_count", 0)) > 0
    ):
        raise RuntimeError("HMSO01R_B_FORMAL_PREFLIGHT_BOOTSTRAP_FAILURE")
    degenerate_primary = int(bootstrap.get("degenerate_primary_draw_count", -1))
    valid_primary = 10000 - degenerate_primary
    derived_candidate_divisions = 6 + valid_primary * 9 + 3 + 3
    derived_relative_divisions = 2 * (3 + valid_primary * 3)
    if not (
        0 <= degenerate_primary <= 200
        and
        int(preflight.get("pointwise_division_count", -1)) == 0
        and int(preflight.get("final_candidate_c_division_count", -1)) == derived_candidate_divisions
        and preflight.get("final_candidate_c_division_count") == preflight.get("expected_final_candidate_c_division_count")
        and int(division.get("pointwise_division_count", -1)) == 0
        and division.get("final_candidate_c_division_count") == division.get("expected_final_candidate_c_division_count")
        and division.get("final_candidate_c_division_count") == preflight.get("final_candidate_c_division_count")
        and int(division.get("paired_log_ratio_division_count", -1)) == derived_relative_divisions
        and division.get("paired_log_ratio_division_count") == division.get("expected_paired_log_ratio_division_count")
        and division.get("paired_ss_ms_identity") is True
        and division.get("per_draw_reaggregation") is True
        and division.get("recomputed_WN_each_draw") is True
        and division.get("recomputed_WB_each_draw") is True
    ):
        raise RuntimeError("HMSO01R_B_FORMAL_PREFLIGHT_DIVISION_FAILURE")
    for field in ("epsilon_count", "clipping_count", "zero_row_deletion_count", "zero_group_deletion_count"):
        if int(preflight.get(field, -1)) != 0 or int(division.get(field, -1)) != 0:
            raise RuntimeError(f"HMSO01R_B_FORMAL_PREFLIGHT_ZERO_SAFE_FAILURE:{field}")
    for field in (
        "target_payload_read_count", "observable_payload_read_count",
        "analytical_reference_evaluation_count", "defect_generation_count",
    ):
        if int(preflight.get(field, -1)) != 0 or int(firewall.get(field, -1)) != 0:
            raise RuntimeError(f"HMSO01R_B_FORMAL_PREFLIGHT_FIREWALL_FAILURE:{field}")
    required_scenarios = {
        "scalar", "vector", "isolated_zero_over_zero", "isolated_positive_over_zero",
        "zero_aggregate", "positive_aggregate", "zero_ss", "exact_zero_ms",
        "hierarchical_equal_weights",
        "more_than_200_degenerate_draws_not_evaluable",
        "fewer_than_2_valid_draws_not_evaluable",
    }
    if not required_scenarios.issubset(scenarios) or not all(scenarios[key] is True for key in required_scenarios):
        raise RuntimeError("HMSO01R_B_FORMAL_PREFLIGHT_SCENARIO_FAILURE")
    required_detailed_scenarios = {
        "scalar_target", "vector_target", "isolated_0_over_0_retained",
        "isolated_positive_over_0_retained", "zero_case_denominator_retained",
        "zero_lineage_denominator_retained", "zero_family_denominator_retained",
        "zero_fold_denominator_retained", "positive_total_WB", "zero_total_WB",
        "ss_zero_baseline", "ms_exact_zero", "hierarchical_equal_weighting",
        "more_than_200_degenerate_draws_not_evaluable",
        "fewer_than_2_valid_draws_not_evaluable", "no_pointwise_ratio",
        "no_epsilon", "no_zero_row_or_group_deletion",
    }
    if (
        not required_detailed_scenarios.issubset(scenario_results)
        or not all(scenario_results[key] is True for key in required_detailed_scenarios)
    ):
        raise RuntimeError("HMSO01R_B_FORMAL_PREFLIGHT_DETAILED_SCENARIO_FAILURE")
    excess = cutoff_evidence.get("more_than_200_degenerate_draws")
    insufficient = cutoff_evidence.get("fewer_than_2_valid_draws")
    if not (
        cutoff_evidence.get("maximum_degenerate_draw_count") == 200
        and cutoff_evidence.get("minimum_valid_draw_count") == 2
        and isinstance(excess, dict) and isinstance(insufficient, dict)
        and excess.get("constructed_degenerate_draw_count") == 201
        and excess.get("constructed_zero_aggregate_denominator_draw_count") == 201
        and excess.get("constructed_valid_draw_count") == 9799
        and excess.get("passed") is True
        and insufficient.get("constructed_degenerate_draw_count") == 9999
        and insufficient.get("constructed_zero_aggregate_denominator_draw_count") == 9999
        and insufficient.get("constructed_valid_draw_count") == 1
        and insufficient.get("passed") is True
        and all(
            isinstance(record.get("status_by_component"), dict)
            and set(record["status_by_component"]) == set(COMPONENTS)
            and all(
                record["status_by_component"][component] == "NOT_EVALUABLE"
                for component in COMPONENTS
            )
            for record in (excess, insufficient)
        )
    ):
        raise RuntimeError("HMSO01R_B_FORMAL_PREFLIGHT_DEGENERACY_CUTOFF_FAILURE")
    if not (
        preflight.get("canonical_zero_status") == CA_ZERO_STATUS
        and preflight.get("current_instruction_zero_status_alias") == CURRENT_ZERO_ALIAS
        and preflight.get("zero_ss_status") == ZERO_SS_STATUS
        and preflight.get("exact_zero_ms_status") == EXACT_ZERO_MS_STATUS
    ):
        raise RuntimeError("HMSO01R_B_FORMAL_PREFLIGHT_ZERO_STATUS_FAILURE")


def write_json(path: Path, value: Any) -> None:
    path = output_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(json_safe(value), indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path = output_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, np.ndarray):
        return json_safe(value.tolist())
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        number = float(value)
        return number if math.isfinite(number) else None
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value


def load_legacy_helpers() -> Any:
    """Load only the frozen, outcome-free non-DNN implementation helpers."""
    if sha256(LEGACY_HELPER) != EXPECTED_LEGACY_HELPER_SHA:
        raise RuntimeError("HMSO01R_B_NON_DNN_HELPER_IDENTITY_FAILURE")
    # Keep the frozen source tree byte-clean during the one-shot formal run.
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("hmso01r_b_frozen_non_dnn", LEGACY_HELPER)
    if spec is None or spec.loader is None:
        raise RuntimeError("HMSO01R_B_NON_DNN_HELPER_IMPORT_FAILURE")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def ordered_training_indices(indices: np.ndarray, meta: dict[str, np.ndarray]) -> np.ndarray:
    hashes = np.asarray([hash_text(str(meta["sample_key"][index])) for index in indices])
    order = np.lexsort((meta["sample_key"][indices], hashes))
    return indices[order]


def norm_sq(value: np.ndarray) -> np.ndarray:
    value = np.asarray(value, dtype=np.float64)
    return value * value if value.ndim == 1 else np.sum(value * value, axis=-1)


def balanced_w(case_values: np.ndarray, cases: list[dict[str, Any]]) -> np.ndarray:
    values = np.asarray(case_values, dtype=np.float64)
    fold_values = []
    for fold in FOLDS:
        family_values = []
        for family in FAMILIES:
            lineages = sorted({
                case["field_lineage_id"] for case in cases
                if case["fold"] == f"FOLD_{fold}" and case["macro_family"] == family
            })
            if not lineages:
                raise RuntimeError("HMSO01R_B_EMPTY_FORMAL_FAMILY_FOLD_CELL")
            lineage_values = []
            for lineage in lineages:
                indices = [
                    index for index, case in enumerate(cases)
                    if case["fold"] == f"FOLD_{fold}"
                    and case["macro_family"] == family
                    and case["field_lineage_id"] == lineage
                ]
                lineage_values.append(np.mean(values[indices], axis=0))
            family_values.append(np.mean(lineage_values, axis=0))
        fold_values.append(np.mean(family_values, axis=0))
    return np.mean(fold_values, axis=0)


def fold_w(case_values: np.ndarray, cases: list[dict[str, Any]], fold: int) -> np.ndarray:
    values = np.asarray(case_values, dtype=np.float64)
    family_values = []
    for family in FAMILIES:
        lineages = sorted({
            case["field_lineage_id"] for case in cases
            if case["fold"] == f"FOLD_{fold}" and case["macro_family"] == family
        })
        lineage_values = []
        for lineage in lineages:
            indices = [
                index for index, case in enumerate(cases)
                if case["fold"] == f"FOLD_{fold}"
                and case["macro_family"] == family
                and case["field_lineage_id"] == lineage
            ]
            lineage_values.append(np.mean(values[indices], axis=0))
        if not lineage_values:
            return np.full(values.shape[1:] or (), np.nan)
        family_values.append(np.mean(lineage_values, axis=0))
    return np.mean(family_values, axis=0)


def draw_w(case_values: np.ndarray, draws: dict[str, np.ndarray], replicate: int) -> np.ndarray:
    values = np.asarray(case_values, dtype=np.float64)
    start, stop = draws["replicate_offsets"][replicate:replicate + 2]
    indices = draws["drawn_case_index"][start:stop]
    occurrences = draws["drawn_occurrence_index"][start:stop]
    strata = draws["drawn_stratum_index"][start:stop]
    occurrence_count = int(occurrences.max()) + 1
    sums = np.zeros((occurrence_count,) + values.shape[1:], dtype=np.float64)
    counts = np.zeros(occurrence_count, dtype=np.int32)
    np.add.at(sums, occurrences, values[indices])
    np.add.at(counts, occurrences, 1)
    occurrence_values = sums / counts.reshape((-1,) + (1,) * (values.ndim - 1))
    occurrence_strata = np.full(occurrence_count, -1, dtype=np.int8)
    occurrence_strata[occurrences] = strata
    return np.mean(
        [np.mean(occurrence_values[occurrence_strata == cell], axis=0) for cell in range(24)],
        axis=0,
    )


def candidate_point(n_case: np.ndarray, b_case: np.ndarray, cases: list[dict[str, Any]]) -> dict[str, Any]:
    wn = float(balanced_w(n_case, cases))
    wb = float(balanced_w(b_case, cases))
    if not (math.isfinite(wn) and math.isfinite(wb) and wn >= 0 and wb >= 0):
        return {"point": None, "wn": wn, "wb": wb, "status": "INTEGRITY_FAILURE", "evaluable": False}
    if wb == 0.0:
        return {
            "point": None,
            "wn": wn,
            "wb": wb,
            "status": CA_ZERO_STATUS,
            "source_alias": CURRENT_ZERO_ALIAS,
            "evaluable": False,
        }
    return {"point": wn / wb, "wn": wn, "wb": wb, "status": "EVALUABLE", "evaluable": True}


def simultaneous_bound(
    family: str,
    points: np.ndarray,
    bootstrap: np.ndarray,
    *,
    direction: str,
    scale: str = "identity",
    inherited_invalid: np.ndarray | None = None,
    eligible: np.ndarray | None = None,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    points = np.asarray(points, dtype=np.float64)
    bootstrap = np.asarray(bootstrap, dtype=np.float64)
    if bootstrap.shape != (10000, 3):
        raise RuntimeError(f"HMSO01R_B_BOOTSTRAP_SHAPE_FAILURE:{family}")
    component_eligible = np.ones(3, dtype=bool) if eligible is None else np.asarray(eligible, dtype=bool)
    if component_eligible.shape != (3,):
        raise RuntimeError(f"HMSO01R_B_BOUND_ELIGIBILITY_SHAPE_FAILURE:{family}")
    invalid = np.zeros(10000, dtype=bool) if inherited_invalid is None else inherited_invalid.copy()
    transformed_points = points.copy()
    transformed = bootstrap.copy()
    if scale == "log":
        if np.any(points[component_eligible] <= 0):
            invalid[:] = True
        transformed_points[component_eligible] = np.log(points[component_eligible])
        positive = np.all(bootstrap[:, component_eligible] > 0, axis=1)
        invalid |= ~positive
        valid_positive = ~invalid
        transformed[np.ix_(valid_positive, component_eligible)] = np.log(
            bootstrap[np.ix_(valid_positive, component_eligible)]
        )
    if component_eligible.any():
        if not np.all(np.isfinite(transformed_points[component_eligible])):
            invalid[:] = True
        invalid |= ~np.all(np.isfinite(transformed[:, component_eligible]), axis=1)
    else:
        invalid[:] = True
    valid = ~invalid
    degenerate = int(invalid.sum())
    status = "EVALUABLE" if degenerate <= 200 and int(valid.sum()) >= 2 else "NOT_EVALUABLE"
    se = np.full(3, np.nan)
    bounds = np.full(3, np.nan)
    critical = math.nan
    if status == "EVALUABLE":
        values = transformed[valid]
        se = np.std(values, axis=0, ddof=1)
        contributions = []
        for index in np.flatnonzero(component_eligible):
            if se[index] == 0.0:
                if not np.all(values[:, index] == transformed_points[index]):
                    status = "NOT_EVALUABLE"
                    break
                contribution = np.zeros(values.shape[0])
            elif direction == "upper":
                contribution = (transformed_points[index] - values[:, index]) / se[index]
            else:
                contribution = (values[:, index] - transformed_points[index]) / se[index]
            contributions.append(contribution)
        if status == "EVALUABLE":
            maximum = np.max(np.column_stack(contributions), axis=1)
            rank = min(maximum.size - 1, max(0, math.ceil(0.95 * maximum.size) - 1))
            critical = max(0.0, float(np.sort(maximum)[rank]))
            sign = 1.0 if direction == "upper" else -1.0
            transformed_bound = transformed_points + sign * critical * se
            bounds = np.exp(transformed_bound) if scale == "log" else transformed_bound
    output, rows = {}, []
    for index, component in enumerate(COMPONENTS):
        component_status = status if component_eligible[index] else "NOT_EVALUABLE"
        record = {
            "metric_family": family,
            "component": component,
            "direction": direction,
            "scale": scale,
            "point_estimate": float(points[index]),
            "bootstrap_standard_error": float(se[index]),
            "simultaneous_bound": float(bounds[index]),
            "critical_value": float(critical),
            "valid_replicates": int(valid.sum()) if component_eligible[index] else 0,
            "degenerate_replicates": degenerate if component_eligible[index] else 10000,
            "status": component_status,
            "multiplicity_scope": "THREE_PRIMARY_COMPONENTS_WITHIN_EACH_METRIC_FAMILY",
        }
        output[component] = record
        rows.append(record)
    return output, rows


def load_real_data() -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    atlas = json.loads(ATLAS.read_text(encoding="utf-8"))
    sample = json.loads(SAMPLE.read_text(encoding="utf-8"))
    cases = sorted(atlas["cases"], key=lambda row: int(row["formal_case_index"]))
    sample_cases = sorted(sample["cases"], key=lambda row: int(row["formal_case_index"]))
    if len(cases) != 384 or len(sample_cases) != 384:
        raise RuntimeError("HMSO01R_B_FORMAL_POPULATION_FAILURE")
    with np.load(OBSERVABLE, allow_pickle=False) as store:
        observable = {name: np.asarray(store[name]) for name in store.files}
    with np.load(TARGET, allow_pickle=False) as store:
        target = {name: np.asarray(store[name]) for name in store.files}
    if observable["ss_features"].shape != (49152, 39) or observable["ms_features"].shape != (49152, 110):
        raise RuntimeError("HMSO01R_B_OBSERVABLE_SHAPE_FAILURE")
    required_target_rows = int(np.sum(target["particle_count_table"]))
    if required_target_rows != 384 * 576 or target["formal_case_index"].shape != (required_target_rows,):
        raise RuntimeError("HMSO01R_B_TARGET_STORE_SHAPE_FAILURE")
    target_rows: list[int] = []
    meta_lists: dict[str, list[Any]] = {
        "case_index": [], "particle_id": [], "case_id": [], "lineage": [],
        "family": [], "fold": [], "seed": [], "particle_state_hash": [], "sample_key": [],
    }
    join_rows: list[dict[str, Any]] = []
    row_cursor = 0
    for position, (case, sample_case) in enumerate(zip(cases, sample_cases)):
        if int(case["formal_case_index"]) != position or int(sample_case["formal_case_index"]) != position:
            raise RuntimeError("HMSO01R_B_CASE_ORDER_FAILURE")
        particle_ids = [int(value) for value in sample_case["particle_ids_in_hash_order"]]
        if len(particle_ids) != 128 or len(set(particle_ids)) != 128:
            raise RuntimeError("HMSO01R_B_PARTICLE_SAMPLE_FAILURE")
        start = int(target["particle_row_start_table"][position])
        stop = int(target["particle_row_stop_table"][position])
        if stop - start != 576:
            raise RuntimeError("HMSO01R_B_TARGET_CASE_ROW_FAILURE")
        for particle in particle_ids:
            target_row = start + particle
            observable_case = int(observable["formal_case_index"][row_cursor])
            observable_particle = int(observable["particle_id"][row_cursor])
            fields_match = bool(
                observable_case == position
                and observable_particle == particle
                and int(target["formal_case_index"][target_row]) == position
                and int(target["particle_id"][target_row]) == particle
                and str(target["case_id"][target_row]) == str(case["case_id"])
                and str(target["particle_state_hash"][target_row]) == str(case["particle_state_hash"])
                and str(target["field_lineage_id"][target_row]) == str(case["field_lineage_id"])
                and str(target["family"][target_row]) == str(case["macro_family"])
                and str(target["fold"][target_row]) == str(case["fold"])
            )
            join_rows.append({
                "formal_case_index": position,
                "case_id": case["case_id"],
                "particle_id": particle,
                "particle_state_hash": case["particle_state_hash"],
                "field_lineage_id": case["field_lineage_id"],
                "family": case["macro_family"],
                "fold": case["fold"],
                "particle_state_hash_match": fields_match,
                "lineage_match": fields_match,
                "family_match": fields_match,
                "fold_match": fields_match,
                "all_identity_fields_match": fields_match,
            })
            target_rows.append(target_row)
            meta_lists["case_index"].append(position)
            meta_lists["particle_id"].append(particle)
            meta_lists["case_id"].append(case["case_id"])
            meta_lists["lineage"].append(case["field_lineage_id"])
            meta_lists["family"].append(case["macro_family"])
            meta_lists["fold"].append(int(str(case["fold"]).split("_")[1]))
            meta_lists["seed"].append(int(case["jitter_seed"]))
            meta_lists["particle_state_hash"].append(case["particle_state_hash"])
            meta_lists["sample_key"].append(f"{case['case_id']}|{particle}")
            row_cursor += 1
    if not all(row["all_identity_fields_match"] for row in join_rows):
        write_csv(JOIN_AUDIT, join_rows)
        raise RuntimeError("HMSO01R_B_TARGET_OBSERVABLE_PAIRING_FAILURE")
    write_csv(JOIN_AUDIT, join_rows)
    selected = np.asarray(target_rows, dtype=np.int64)
    targets = {component: np.asarray(target[field][selected], dtype=np.float64) for component, field in TARGET_FIELDS.items()}
    targets["bundle"] = np.column_stack(tuple(targets[name] for name in COMPONENTS))
    features = {
        "SS": np.asarray(observable["ss_features"], dtype=np.float64),
        "MS": np.asarray(observable["ms_features"], dtype=np.float64),
    }
    meta = {
        key: np.asarray(value, dtype=(np.int16 if key in {"case_index", "particle_id"} else np.int8 if key == "fold" else np.int64 if key == "seed" else None))
        for key, value in meta_lists.items()
    }
    if not all(np.isfinite(value).all() for value in (*features.values(), *(targets[name] for name in COMPONENTS))):
        raise RuntimeError("HMSO01R_B_NONFINITE_FORMAL_INPUT")
    return {"features": features, "targets": targets, "meta": meta}, cases, join_rows


def load_frozen_identities() -> tuple[dict[str, np.ndarray], np.ndarray, dict[str, np.ndarray]]:
    if sha256(NEIGHBOURS) != EXPECTED_NEIGHBOURS_SHA or sha256(RANDOM) != EXPECTED_RANDOM_SHA or sha256(BOOTSTRAP) != EXPECTED_BOOTSTRAP_SHA:
        raise RuntimeError("HMSO01R_B_FROZEN_IDENTITY_FAILURE")
    with np.load(NEIGHBOURS, allow_pickle=False) as store:
        neighbors = {name: np.asarray(store[name]) for name in store.files}
    with np.load(RANDOM, allow_pickle=False) as store:
        comparator = np.asarray(store["comparator_row_index"], dtype=np.int64)
        if not np.array_equal(store["query_row_index"], np.arange(49152)):
            raise RuntimeError("HMSO01R_B_RANDOM_QUERY_IDENTITY_FAILURE")
    with np.load(BOOTSTRAP, allow_pickle=False) as store:
        draws = {name: np.asarray(store[name]) for name in store.files}
    if not np.array_equal(neighbors["query_row_index"], np.arange(49152)):
        raise RuntimeError("HMSO01R_B_NEIGHBOR_QUERY_IDENTITY_FAILURE")
    return neighbors, comparator, draws


def bootstrap_integrity(cases: list[dict[str, Any]], draws: dict[str, np.ndarray]) -> tuple[np.ndarray, dict[str, Any]]:
    registry = json.loads(BOOTSTRAP_REGISTRY.read_text(encoding="utf-8"))
    offsets = np.asarray(draws["replicate_offsets"], dtype=np.int64)
    case_index = np.asarray(draws["drawn_case_index"], dtype=np.int64)
    lineage_index = np.asarray(draws["drawn_lineage_index"], dtype=np.int64)
    occurrence_index = np.asarray(draws["drawn_occurrence_index"], dtype=np.int64)
    stratum_index = np.asarray(draws["drawn_stratum_index"], dtype=np.int64)
    if offsets.shape != (10001,) or offsets[0] != 0 or offsets[-1] != case_index.size:
        raise RuntimeError("HMSO01R_B_BOOTSTRAP_OFFSET_FAILURE")
    lineage_table = list(registry["lineage_table"])
    case_lineage = np.asarray([lineage_table.index(case["field_lineage_id"]) for case in cases], dtype=np.int64)
    strata = sorted(registry["strata"])
    case_stratum = np.asarray([strata.index(f"{case['macro_family']}|{case['fold']}") for case in cases], dtype=np.int64)
    if not np.array_equal(case_lineage[case_index], lineage_index) or not np.array_equal(case_stratum[case_index], stratum_index):
        raise RuntimeError("HMSO01R_B_BOOTSTRAP_CASE_LINEAGE_STRATUM_FAILURE")
    signatures: set[bytes] = set()
    insufficient = np.zeros(10000, dtype=bool)
    occurrence_total = 0
    for replicate in range(10000):
        start, stop = map(int, offsets[replicate:replicate + 2])
        occurrence = occurrence_index[start:stop]
        starts = np.r_[0, np.flatnonzero(np.diff(occurrence)) + 1]
        occurrence_total += int(starts.size)
        family_lineage_counts: dict[str, dict[int, int]] = {family: {} for family in FAMILIES}
        for local in starts:
            family = strata[int(stratum_index[start + local])].split("|")[0]
            lineage = int(lineage_index[start + local])
            family_lineage_counts[family][lineage] = family_lineage_counts[family].get(lineage, 0) + 1
        for family in FAMILIES:
            multiplicity = np.asarray(list(family_lineage_counts[family].values()), dtype=np.float64)
            ess = float(multiplicity.sum() ** 2 / np.sum(multiplicity * multiplicity)) if multiplicity.size else 0.0
            if ess < 2.0:
                insufficient[replicate] = True
        digest = hashlib.sha256()
        for values in (case_index, lineage_index, occurrence_index, stratum_index):
            digest.update(np.ascontiguousarray(values[start:stop]).tobytes())
        signatures.add(digest.digest())
    if len(signatures) != 10000 or registry.get("unique_draw_count") != 10000 or registry.get("draw_file_sha256") != EXPECTED_BOOTSTRAP_SHA:
        raise RuntimeError("HMSO01R_B_BOOTSTRAP_IDENTITY_FAILURE")
    family_lineages = {
        family: {case["field_lineage_id"] for case in cases if case["macro_family"] == family}
        for family in FAMILIES
    }
    populated_cells = {
        (case["macro_family"], case["fold"]) for case in cases
    }
    point_sufficient = bool(
        all(len(family_lineages[family]) >= 6 for family in FAMILIES)
        and populated_cells == {(family, f"FOLD_{fold}") for family in FAMILIES for fold in FOLDS}
    )
    draw_insufficient_count = int(insufficient.sum())
    if not point_sufficient:
        insufficient[:] = True
    return insufficient, {
        "draw_count": 10000, "unique_draw_count": len(signatures), "case_emission_count": int(case_index.size),
        "decoded_lineage_occurrence_count": occurrence_total,
        "draws_with_family_lineage_kish_ess_below_2": draw_insufficient_count,
        "point_effective_lineages_sufficient": point_sufficient,
        "family_unique_lineage_counts": {
            family: len(family_lineages[family]) for family in FAMILIES
        },
        "populated_family_fold_cell_count": len(populated_cells),
    }


def case_mean(values: np.ndarray, meta: dict[str, np.ndarray]) -> np.ndarray:
    output = np.empty(384, dtype=np.float64)
    for case in range(384):
        rows = meta["case_index"] == case
        if int(rows.sum()) != 128:
            raise RuntimeError("HMSO01R_B_CASE_PARTICLE_COUNT_FAILURE")
        output[case] = float(np.mean(values[rows]))
    return output


def disagreement_primitives(target: np.ndarray, identities: np.ndarray, comparator: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    if target.ndim == 1:
        n = np.mean((target[identities] - target[:, None]) ** 2, axis=1)
        b = np.mean((target[comparator] - target[:, None]) ** 2, axis=1)
    else:
        n = np.mean(norm_sq(target[identities] - target[:, None, :]), axis=1)
        b = np.mean(norm_sq(target[comparator] - target[:, None, :]), axis=1)
    return n, b


def non_dnn_aggregate(values: np.ndarray, cases: list[dict[str, Any]]) -> dict[str, np.ndarray | float]:
    cell = np.full((6, 4), np.nan, dtype=np.float64)
    for fold in FOLDS:
        for family_index, family in enumerate(FAMILIES):
            indices = [int(case["formal_case_index"]) for case in cases if case["fold"] == f"FOLD_{fold}" and case["macro_family"] == family]
            cell[fold, family_index] = float(np.mean(values[indices]))
    return {
        "point_cell": cell,
        "point": float(np.mean(cell)),
        "point_family": np.mean(cell, axis=0),
        "point_fold": np.mean(cell, axis=1),
    }


def draw_non_dnn(values: np.ndarray, draws: dict[str, np.ndarray], replicate: int) -> float:
    return float(draw_w(values, draws, replicate))


def status_leaf(evaluable: bool, mechanism: str = NON_DNN_BOOTSTRAP_NE) -> dict[str, Any]:
    if evaluable:
        return {"status": "EVALUABLE", "evaluable": True, "not_evaluable_mechanism": ""}
    status = mechanism
    return {"status": status, "evaluable": False, "not_evaluable_mechanism": status}


def bound_status_leaf(record: dict[str, Any]) -> dict[str, Any]:
    status = str(record.get("status", "NOT_EVALUABLE_BOUND_STATUS_MISSING"))
    evaluable = bool(status == "EVALUABLE" and math.isfinite(scalar_bound(record)))
    return status_leaf(evaluable, status if status != "EVALUABLE" else "")


def scoped_status(
    aggregate: dict[str, Any], cases: list[dict[str, Any]], case_mechanisms: list[str],
    fallback: str,
) -> dict[str, Any]:
    def leaf(value: float, indices: list[int]) -> dict[str, Any]:
        if math.isfinite(float(value)):
            return status_leaf(True)
        mechanisms = sorted({case_mechanisms[index] for index in indices if case_mechanisms[index]})
        return status_leaf(False, mechanisms[0] if len(mechanisms) == 1 else fallback)

    all_indices = list(range(len(cases)))
    return {
        "overall": leaf(float(aggregate["point"]), all_indices),
        "family": {
            family: leaf(
                float(aggregate["point_family"][family_index]),
                [index for index, case in enumerate(cases) if case["macro_family"] == family],
            )
            for family_index, family in enumerate(FAMILIES)
        },
        "fold": {
            f"FOLD_{fold}": leaf(
                float(aggregate["point_fold"][fold]),
                [index for index, case in enumerate(cases) if case["fold"] == f"FOLD_{fold}"],
            )
            for fold in FOLDS
        },
    }


def candidate_metrics(
    data: dict[str, Any], cases: list[dict[str, Any]], neighbors: dict[str, np.ndarray],
    comparator: np.ndarray, draws: dict[str, np.ndarray],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    metrics: dict[str, Any] = {arm: {} for arm in ARMS}
    bound_rows: list[dict[str, Any]] = []
    division_cells: list[dict[str, Any]] = []
    for arm in ARMS:
        identity = np.asarray(neighbors[f"{arm.lower()}_neighbor_row_index"], dtype=np.int64)
        points, boot_columns = [], []
        for component in COMPONENTS:
            n_particle, b_particle = disagreement_primitives(data["targets"][component], identity, comparator)
            n_case, b_case = case_mean(n_particle, data["meta"]), case_mean(b_particle, data["meta"])
            point = candidate_point(n_case, b_case, cases)
            boot = np.full(10000, np.nan, dtype=np.float64)
            degenerate = 0
            for replicate in range(10000):
                wn, wb = float(draw_w(n_case, draws, replicate)), float(draw_w(b_case, draws, replicate))
                if wb > 0 and math.isfinite(wn) and math.isfinite(wb):
                    boot[replicate] = wn / wb
                else:
                    degenerate += 1
            point_evaluable = bool(point["evaluable"])
            metric_evaluable = point_evaluable and degenerate <= 200 and int(np.isfinite(boot).sum()) >= 2
            status = "EVALUABLE" if metric_evaluable else point["status"] if not point_evaluable else "NOT_EVALUABLE_EXCESS_DEGENERATE_BOOTSTRAP_DRAWS"
            fold_values = []
            fold_divisions = 0
            for fold in FOLDS:
                wn_fold, wb_fold = float(fold_w(n_case, cases, fold)), float(fold_w(b_case, cases, fold))
                if wb_fold > 0:
                    fold_values.append(wn_fold / wb_fold)
                    fold_divisions += 1
                else:
                    fold_values.append(math.nan)
            metrics[arm][component] = {
                "candidate_c_d": point["point"], "candidate_c_wn": point["wn"], "candidate_c_wb": point["wb"],
                "candidate_c_status": status, "candidate_c_evaluable": metric_evaluable,
                "candidate_c_source_alias": point.get("source_alias"),
                "candidate_c_boot": boot, "candidate_c_n_case": n_case, "candidate_c_b_case": b_case,
                "candidate_c_point_fold": np.asarray(fold_values),
            }
            points.append(math.nan if point["point"] is None else float(point["point"]))
            boot_columns.append(boot)
            division_cells.append({
                "arm": arm, "component": component,
                "point_aggregate_denominator_positive": bool(point["wb"] > 0),
                "point_candidate_c_division_count": 1 if point["wb"] > 0 else 0,
                "bootstrap_candidate_c_division_count": int(np.isfinite(boot).sum()),
                "fold_candidate_c_division_count": fold_divisions,
                "degenerate_aggregate_denominator_replicate_count": degenerate,
                "evaluable_replicate_count": int(np.isfinite(boot).sum()),
                "candidate_c_evaluable": metric_evaluable, "status": status,
            })
        arm_bound, rows = simultaneous_bound(
            f"ABSOLUTE_{arm}_CANDIDATE_C", np.asarray(points), np.column_stack(boot_columns),
            direction="upper", eligible=np.asarray([metrics[arm][c]["candidate_c_evaluable"] for c in COMPONENTS]),
        )
        bound_rows.extend(rows)
        for component in COMPONENTS:
            record = arm_bound[component]
            metrics[arm][component]["candidate_c_simultaneous_ucb"] = record["simultaneous_bound"]
            metrics[arm][component]["candidate_c_bound_status"] = record["status"]
            metrics[arm][component]["candidate_c_evaluable"] = bool(
                metrics[arm][component]["candidate_c_evaluable"] and record["status"] == "EVALUABLE"
            )
            if not metrics[arm][component]["candidate_c_evaluable"] and metrics[arm][component]["candidate_c_status"] == "EVALUABLE":
                metrics[arm][component]["candidate_c_status"] = "NOT_EVALUABLE_SIMULTANEOUS_BOUND"
            division_cell = next(
                row for row in division_cells
                if row["arm"] == arm and row["component"] == component
            )
            division_cell["candidate_c_evaluable"] = metrics[arm][component]["candidate_c_evaluable"]
            division_cell["status"] = metrics[arm][component]["candidate_c_status"]
            metrics[arm][component]["candidate_c_absolute_gate_pass"] = bool(
                metrics[arm][component]["candidate_c_evaluable"]
                and metrics[arm][component]["candidate_c_d"] < 1.0
                and record["simultaneous_bound"] < 1.0
            )
    paired: dict[str, Any] = {}
    ratio_points, ratio_boot = [], []
    paired_divisions: list[dict[str, Any]] = []
    for component in COMPONENTS:
        ss, ms = metrics["SS"][component], metrics["MS"][component]
        point_evaluable = bool(ss["candidate_c_evaluable"] and ms["candidate_c_evaluable"] and ss["candidate_c_d"] > 0)
        exact_zero = bool(point_evaluable and ms["candidate_c_d"] == 0.0)
        ratio = float(ms["candidate_c_d"] / ss["candidate_c_d"]) if point_evaluable else math.nan
        valid = np.isfinite(ss["candidate_c_boot"]) & np.isfinite(ms["candidate_c_boot"]) & (ss["candidate_c_boot"] > 0)
        infer_valid = valid
        boot = np.full(10000, np.nan)
        boot[valid] = ms["candidate_c_boot"][valid] / ss["candidate_c_boot"][valid]
        exact_zero_valid = bool(
            exact_zero and int(infer_valid.sum()) >= 2 and int((~infer_valid).sum()) <= 200
            and np.all(boot[infer_valid] == 0.0)
        )
        status = EXACT_ZERO_MS_STATUS if exact_zero_valid else "EVALUABLE" if point_evaluable and int(infer_valid.sum()) >= 2 and int((~infer_valid).sum()) <= 200 else ZERO_SS_STATUS if ss["candidate_c_d"] == 0 else "NOT_EVALUABLE"
        paired[component] = {
            "candidate_c_ratio": ratio if math.isfinite(ratio) else None,
            "candidate_c_status": status, "candidate_c_evaluable": status in {"EVALUABLE", EXACT_ZERO_MS_STATUS}, "candidate_c_ratio_boot": boot,
            "candidate_c_exact_zero_ms_dominance": exact_zero_valid,
        }
        ratio_points.append(ratio)
        ratio_boot.append(boot)
        paired_divisions.append({
            "component": component, "point_ratio_evaluable": point_evaluable,
            "point_ratio_division_count": 1 if point_evaluable else 0,
            "bootstrap_ratio_division_count": int(valid.sum()), "evaluable_replicate_count": int(valid.sum()),
            "status": status, "candidate_c_evaluable": status in {"EVALUABLE", EXACT_ZERO_MS_STATUS},
        })
    ordinary = np.asarray([paired[c]["candidate_c_status"] == "EVALUABLE" for c in COMPONENTS])
    ratio_bound, rows = simultaneous_bound(
        "PAIRED_CANDIDATE_C_RATIO", np.asarray(ratio_points), np.column_stack(ratio_boot),
        direction="upper", scale="log", eligible=ordinary,
    )
    bound_rows.extend(rows)
    paired_rows = []
    for component in COMPONENTS:
        if paired[component]["candidate_c_status"] == EXACT_ZERO_MS_STATUS:
            paired[component]["candidate_c_ratio_simultaneous_ucb"] = 0.0
            ratio_bound[component].update({
                "simultaneous_bound": 0.0,
                "bootstrap_standard_error": 0.0,
                "critical_value": 0.0,
                "valid_replicates": int(np.sum(np.isfinite(paired[component]["candidate_c_ratio_boot"]))),
                "degenerate_replicates": int(np.sum(~np.isfinite(paired[component]["candidate_c_ratio_boot"]))),
                "status": EXACT_ZERO_MS_STATUS,
            })
            for row in rows:
                if row["component"] == component:
                    row.update(ratio_bound[component])
        else:
            paired[component]["candidate_c_ratio_simultaneous_ucb"] = ratio_bound[component]["simultaneous_bound"]
            if ratio_bound[component]["status"] != "EVALUABLE":
                paired[component]["candidate_c_evaluable"] = False
                paired[component]["candidate_c_status"] = "NOT_EVALUABLE_SIMULTANEOUS_BOUND"
        paired[component]["candidate_c_relative_gate_pass"] = bool(
            paired[component]["candidate_c_evaluable"]
            and (ratio_bound[component]["status"] == "EVALUABLE" or paired[component]["candidate_c_status"] == EXACT_ZERO_MS_STATUS)
            and paired[component]["candidate_c_ratio"] <= 0.80
            and paired[component]["candidate_c_ratio_simultaneous_ucb"] <= 0.90
        )
        paired_divisions[COMPONENTS.index(component)]["candidate_c_evaluable"] = paired[component]["candidate_c_evaluable"]
        paired_divisions[COMPONENTS.index(component)]["status"] = paired[component]["candidate_c_status"]
        paired_rows.append({"component": component, **{k: v for k, v in paired[component].items() if not isinstance(v, np.ndarray)}})
    return {**metrics, "paired": paired}, bound_rows, division_cells, paired_divisions


def non_dnn_case_metrics(
    data: dict[str, Any], cases: list[dict[str, Any]], neighbors: dict[str, np.ndarray], draws: dict[str, np.ndarray],
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], int]:
    helper = load_legacy_helpers()
    normalization = json.loads(NORMALIZATION.read_text(encoding="utf-8"))
    coverage_geometry = json.loads(COVERAGE_GEOMETRY.read_text(encoding="utf-8"))
    schemas = {"SS": json.loads(SS_SCHEMA.read_text()), "MS": json.loads(MS_SCHEMA.read_text())}
    metrics: dict[str, Any] = {arm: {} for arm in ARMS}
    fold_records: dict[str, list[dict[str, Any]]] = {arm: [] for arm in ARMS}
    oracle_fit_count = 0
    for arm in ARMS:
        features = data["features"][arm]
        names = [row["name"] for row in schemas[arm]["columns"]]
        poly_positions = [names.index(name) for name in POLY_SUBSET]
        rows_by_component: dict[str, list[dict[str, Any]]] = {component: [] for component in COMPONENTS}
        for outer in FOLDS:
            fold_record = next(row for row in normalization["arms"][arm]["folds"] if row["held_out_fold"] == f"FOLD_{outer}")
            median, divisor = np.asarray(fold_record["median"]), np.asarray(fold_record["divisor"])
            scaled = (features - median) / divisor
            winners, selections = helper.nested_select_oracles(
                arm, outer, scaled, data["targets"]["bundle"], data["targets"], data["meta"], poly_positions,
            )
            train = ordered_training_indices(np.flatnonzero(data["meta"]["fold"] != outer), data["meta"])
            query = np.flatnonzero(data["meta"]["fold"] == outer)
            frozen_global = np.asarray(neighbors[f"{arm.lower()}_neighbor_row_index"])[query]
            lookup = {int(global_index): local for local, global_index in enumerate(train)}
            frozen_local = np.asarray([[lookup[int(value)] for value in row] for row in frozen_global], dtype=np.int64)
            oracle_distance, oracle_neighbor = helper.exact_permitted_neighbors(
                scaled[train], scaled[query], helper.subset_meta(data["meta"], train), helper.subset_meta(data["meta"], query), required_k=20,
            )
            frozen_distance = np.asarray(neighbors[f"{arm.lower()}_neighbor_distance"])[query]
            if (
                not np.array_equal(train[oracle_neighbor[:, :10]], frozen_global)
                or not np.array_equal(oracle_distance[:, :10], frozen_distance)
            ):
                raise RuntimeError(f"HMSO01R_B_FROZEN_ORACLE_K10_IDENTITY_DISTANCE_FAILURE:{arm}:FOLD_{outer}")
            predictions, failures = helper.candidate_predictions(
                scaled[train], scaled[query], data["targets"]["bundle"][train], oracle_neighbor, poly_positions,
            )
            distance = np.asarray(neighbors[f"{arm.lower()}_neighbor_distance"])[query, 9]
            radius = float(next(row for row in coverage_geometry["arms"][arm]["folds"] if row["held_out_fold"] == f"FOLD_{outer}")["k10_radius_p95"])
            coverage_geometry_valid = bool(
                math.isfinite(radius) and radius >= 0.0
                and distance.shape == (query.size,) and np.isfinite(distance).all()
                and np.all(distance >= 0.0)
            )
            covered = distance <= radius if coverage_geometry_valid else np.full(query.size, np.nan)
            record = {"outer_fold": outer, "selected_oracles": winners, "selection_records": selections, "failures": failures}
            fold_records[arm].append(record)
            oracle_fit_count += 12
            for component in COMPONENTS:
                target = data["targets"][component]
                development_variance = float(helper.development_trace_variance(target, train, data["meta"]))
                cvar_mechanism = (
                    "" if development_variance > 0.0 and math.isfinite(development_variance)
                    else NON_DNN_VARIANCE_NE
                )
                local_target = target[train[frozen_local]]
                centered = local_target - np.mean(local_target, axis=1, keepdims=True)
                trace = np.sum(centered * centered, axis=1) / 9.0 if local_target.ndim == 2 else np.sum(centered * centered, axis=(1, 2)) / 9.0
                cvar_particle = trace / development_variance if development_variance > 0 else np.full(query.size, np.nan)
                winner = winners[component]
                component_slice = TARGET_SLICES[component]
                prediction = predictions[winner][:, component_slice] if winner is not None and winner in predictions else np.full((query.size, component_slice.stop - component_slice.start), np.nan)
                if prediction.shape[1] == 1:
                    prediction = prediction[:, 0]
                development_mean = helper.case_family_equal_vector(target, train, data["meta"])
                baseline_prediction = np.broadcast_to(development_mean, target[query].shape)
                target_rms = float(helper.development_target_rms(target, train, data["meta"]))
                if winner is None or winner not in predictions:
                    oracle_mechanism = NON_DNN_ORACLE_NE
                elif not np.isfinite(prediction).all():
                    oracle_mechanism = NON_DNN_ORACLE_NE
                elif not (target_rms > 0.0 and math.isfinite(target_rms)):
                    oracle_mechanism = NON_DNN_ORACLE_NE
                else:
                    oracle_mechanism = ""
                baseline_mechanism = (
                    "" if target_rms > 0.0 and math.isfinite(target_rms)
                    else NON_DNN_BASELINE_NE
                )
                for case_index in np.unique(data["meta"]["case_index"][query]):
                    local = np.flatnonzero(data["meta"]["case_index"][query] == case_index)
                    case_row = {
                        "formal_case_index": int(case_index), "fold": outer,
                        "cvar": float(np.mean(cvar_particle[local])), "coverage": float(np.mean(covered[local])),
                        "oracle_error_ms": float(np.mean(norm_sq(prediction[local] - target[query][local]))),
                        "baseline_error_ms": float(np.mean(norm_sq(baseline_prediction[local] - target[query][local]))),
                        "target_rms": target_rms, "selected_oracle": winner,
                        "cvar_not_evaluable_mechanism": cvar_mechanism,
                        "oracle_not_evaluable_mechanism": oracle_mechanism,
                        "baseline_not_evaluable_mechanism": baseline_mechanism,
                        "coverage_not_evaluable_mechanism": "" if coverage_geometry_valid else NON_DNN_COVERAGE_NE,
                    }
                    rows_by_component[component].append(case_row)
            print(f"HMSO01R_B_OUTER_FOLD arm={arm} fold={outer} complete", flush=True)
        for component in COMPONENTS:
            component_rows = sorted(rows_by_component[component], key=lambda row: row["formal_case_index"])
            if len(component_rows) != 384:
                raise RuntimeError("HMSO01R_B_NON_DNN_CASE_COVERAGE_FAILURE")
            cvar_case = np.asarray([row["cvar"] for row in component_rows])
            coverage_case = np.asarray([row["coverage"] for row in component_rows])
            oracle_error = np.asarray([row["oracle_error_ms"] for row in component_rows])
            baseline_error = np.asarray([row["baseline_error_ms"] for row in component_rows])
            target_rms = np.asarray([row["target_rms"] for row in component_rows])
            cvar = non_dnn_aggregate(cvar_case, cases)
            coverage = non_dnn_aggregate(coverage_case, cases)
            cells = helper.cell_case_indices(cases)
            counts = np.zeros((10000, 384), dtype=np.int16)
            for replicate in range(10000):
                start, stop = draws["replicate_offsets"][replicate:replicate + 2]
                counts[replicate] = np.bincount(draws["drawn_case_index"][start:stop], minlength=384)
            oracle = helper.aggregate_oracle(oracle_error, target_rms, counts, cells)
            baseline = helper.aggregate_oracle(baseline_error, target_rms, counts, cells)
            cvar_counted = helper.aggregate_case_statistic(cvar_case, counts, cells, reducer="mean")
            coverage_counted = helper.aggregate_case_statistic(coverage_case, counts, cells, reducer="mean")
            cvar.update({key: cvar_counted[key] for key in ("boot", "boot_family", "boot_fold")})
            coverage.update({key: coverage_counted[key] for key in ("boot", "boot_family", "boot_fold")})
            baseline_boot = np.asarray(baseline["boot"], dtype=np.float64)
            improvement_boot = np.full(10000, np.nan, dtype=np.float64)
            valid_baseline_boot = np.isfinite(baseline_boot) & (baseline_boot > 0.0)
            improvement_boot[valid_baseline_boot] = (
                1.0
                - np.asarray(oracle["boot"], dtype=np.float64)[valid_baseline_boot]
                / baseline_boot[valid_baseline_boot]
            )
            improvement_point = (
                1.0 - float(oracle["point"]) / float(baseline["point"])
                if math.isfinite(float(baseline["point"])) and float(baseline["point"]) > 0.0
                else math.nan
            )
            improvement = {"point": improvement_point, "boot": improvement_boot}
            cvar_status = scoped_status(
                cvar, cases,
                [str(row["cvar_not_evaluable_mechanism"]) for row in component_rows],
                NON_DNN_VARIANCE_NE,
            )
            oracle_status = scoped_status(
                oracle, cases,
                [str(row["oracle_not_evaluable_mechanism"]) for row in component_rows],
                NON_DNN_ORACLE_NE,
            )
            baseline_status = scoped_status(
                baseline, cases,
                [str(row["baseline_not_evaluable_mechanism"]) for row in component_rows],
                NON_DNN_BASELINE_NE,
            )
            coverage_status = scoped_status(
                coverage, cases,
                [str(row["coverage_not_evaluable_mechanism"]) for row in component_rows],
                NON_DNN_COVERAGE_NE,
            )
            if math.isfinite(improvement_point):
                improvement_status = status_leaf(True)
            elif not oracle_status["overall"]["evaluable"]:
                improvement_status = status_leaf(False, NON_DNN_BASELINE_NE)
            elif not baseline_status["overall"]["evaluable"]:
                improvement_status = status_leaf(False, NON_DNN_BASELINE_NE)
            else:
                improvement_status = status_leaf(False, NON_DNN_BASELINE_NE)
            metrics[arm][component] = {
                "conditional_variance": cvar, "coverage": coverage, "oracle_nrmse": oracle,
                "baseline_nrmse": baseline, "improvement": improvement,
                "selected_oracles_by_fold": {str(row["outer_fold"]): row["selected_oracles"][component] for row in fold_records[arm]},
                "non_dnn_status": {
                    "conditional_variance": cvar_status,
                    "oracle_nrmse": oracle_status,
                    "mean_baseline_nrmse": baseline_status,
                    "improvement": {"overall": improvement_status},
                    "coverage": coverage_status,
                },
            }
    return metrics, fold_records, [], oracle_fit_count


def build_non_dnn_bounds(metrics: dict[str, Any], inherited_invalid: np.ndarray) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    lookup: dict[str, Any] = {"absolute": {arm: {} for arm in ARMS}, "relative": {}, "family": {arm: {} for arm in ARMS}}
    rows: list[dict[str, Any]] = []
    def normalize_bootstrap_ne(
        bound: dict[str, dict[str, Any]], bound_rows: list[dict[str, Any]],
        eligible: np.ndarray | None = None,
    ) -> None:
        mask = np.ones(3, dtype=bool) if eligible is None else np.asarray(eligible, dtype=bool)
        for index, component in enumerate(COMPONENTS):
            if mask[index] and bound[component]["status"] != "EVALUABLE":
                bound[component]["status"] = NON_DNN_BOOTSTRAP_NE
                bound_rows[index]["status"] = NON_DNN_BOOTSTRAP_NE
    for arm in ARMS:
        for label, key, direction in (
            ("conditional_variance", "conditional_variance", "upper"),
            ("oracle_nrmse", "oracle_nrmse", "upper"),
            ("improvement", "improvement", "lower"),
        ):
            points = np.asarray([metrics[arm][component][key]["point"] for component in COMPONENTS])
            boot = np.column_stack([metrics[arm][component][key]["boot"] for component in COMPONENTS])
            bound, bound_rows = simultaneous_bound(
                f"ABSOLUTE_{arm}_{label}", points, boot, direction=direction,
                inherited_invalid=inherited_invalid,
            )
            normalize_bootstrap_ne(bound, bound_rows)
            lookup["absolute"][arm][label] = bound
            rows.extend(bound_rows)
        for family_index, family in enumerate(FAMILIES):
            points = np.asarray([metrics[arm][component]["oracle_nrmse"]["point_family"][family_index] for component in COMPONENTS])
            boot = np.column_stack([metrics[arm][component]["oracle_nrmse"]["boot_family"][:, family_index] for component in COMPONENTS])
            bound, bound_rows = simultaneous_bound(
                f"ABSOLUTE_{arm}_oracle_nrmse_family_{family}", points, boot, direction="upper",
                inherited_invalid=inherited_invalid,
            )
            normalize_bootstrap_ne(bound, bound_rows)
            lookup["family"][arm][family] = bound
            rows.extend(bound_rows)
    for label, key in (("conditional_variance", "conditional_variance"), ("oracle_nrmse", "oracle_nrmse")):
        ss = np.asarray([metrics["SS"][component][key]["point"] for component in COMPONENTS])
        ms = np.asarray([metrics["MS"][component][key]["point"] for component in COMPONENTS])
        eligible = ss > 100.0 * DIMENSIONLESS_FLOOR
        point = np.divide(ms, ss, out=np.full(3, np.nan), where=eligible)
        boot = np.full((10000, 3), np.nan)
        for index, component in enumerate(COMPONENTS):
            denominator = metrics["SS"][component][key]["boot"]
            valid = denominator > 0
            boot[valid, index] = metrics["MS"][component][key]["boot"][valid] / denominator[valid]
        bound, bound_rows = simultaneous_bound(
            f"PAIRED_{label.upper()}_RATIO", point, boot, direction="upper", scale="log", eligible=eligible,
            inherited_invalid=inherited_invalid,
        )
        normalize_bootstrap_ne(bound, bound_rows, eligible)
        for index, component in enumerate(COMPONENTS):
            if not eligible[index]:
                bound[component]["status"] = NON_DNN_RATIO_NE
                for row in bound_rows:
                    if row["component"] == component:
                        row["status"] = bound[component]["status"]
        lookup["relative"][label] = {"point": point, "boot": boot, "bounds": bound}
        rows.extend(bound_rows)
    return lookup, rows


def scalar_bound(record: dict[str, Any]) -> float:
    value = record.get("simultaneous_bound")
    return float(value) if value is not None and math.isfinite(float(value)) else math.nan


def bound_procedure_completeness(rows: list[dict[str, Any]]) -> dict[str, bool]:
    """Derive procedure and numeric-evaluability status from the exact rowset."""
    expected_families = {
        "ABSOLUTE_SS_CANDIDATE_C", "ABSOLUTE_MS_CANDIDATE_C",
        "PAIRED_CANDIDATE_C_RATIO",
        *(f"ABSOLUTE_{arm}_{metric}" for arm in ARMS for metric in (
            "conditional_variance", "oracle_nrmse", "improvement",
        )),
        *(
            f"ABSOLUTE_{arm}_oracle_nrmse_family_{family}"
            for arm in ARMS for family in FAMILIES
        ),
        "PAIRED_CONDITIONAL_VARIANCE_RATIO", "PAIRED_ORACLE_NRMSE_RATIO",
    }
    expected = {
        (family, component)
        for family in expected_families for component in COMPONENTS
    }
    identities = [
        (str(row.get("metric_family")), str(row.get("component")))
        for row in rows
    ]
    procedures_executed = bool(
        len(rows) == 57
        and len(set(identities)) == 57
        and set(identities) == expected
        and all(
            row.get("multiplicity_scope")
            == "THREE_PRIMARY_COMPONENTS_WITHIN_EACH_METRIC_FAMILY"
            and row.get("direction") in {"upper", "lower"}
            and row.get("scale") in {"identity", "log"}
            and int(row.get("valid_replicates", -1))
            + int(row.get("degenerate_replicates", -1)) == 10000
            for row in rows
        )
    )
    numerically_evaluable = bool(
        procedures_executed
        and all(row.get("status") in {"EVALUABLE", EXACT_ZERO_MS_STATUS} for row in rows)
    )
    return {
        "all_required_bound_procedures_executed": procedures_executed,
        # Compatibility name: "computed" means the preregistered procedure
        # emitted its mandatory bound/status row, not that its UCB is numeric.
        "all_required_bounds_computed": procedures_executed,
        "all_required_bounds_evaluable": numerically_evaluable,
    }


def evaluate_components(
    candidate: dict[str, Any], non_dnn: dict[str, Any], non_dnn_bounds: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    components: dict[str, Any] = {}
    verdict_rows: list[dict[str, Any]] = []
    rescue_rows: list[dict[str, Any]] = []
    for component in COMPONENTS:
        ss, ms, paired = non_dnn["SS"][component], non_dnn["MS"][component], candidate["paired"][component]
        candidate_ms = candidate["MS"][component]
        cvar_ucb = scalar_bound(non_dnn_bounds["absolute"]["MS"]["conditional_variance"][component])
        oracle_ucb = scalar_bound(non_dnn_bounds["absolute"]["MS"]["oracle_nrmse"][component])
        improvement_lcb = scalar_bound(non_dnn_bounds["absolute"]["MS"]["improvement"][component])
        family_point_pass = {family: bool(ms["oracle_nrmse"]["point_family"][index] <= 0.85) for index, family in enumerate(FAMILIES)}
        family_bound_pass = {family: bool(scalar_bound(non_dnn_bounds["family"]["MS"][family][component]) <= 1.00) for family in FAMILIES}
        coverage_family_pass = {family: bool(ms["coverage"]["point_family"][index] >= 0.80) for index, family in enumerate(FAMILIES)}
        absolute_folds_valid = bool(np.isfinite([
            *candidate["MS"][component]["candidate_c_point_fold"],
            *ms["conditional_variance"]["point_fold"],
            *ms["oracle_nrmse"]["point_fold"], *ms["coverage"]["point_fold"],
        ]).all())
        relative_folds_valid = bool(np.isfinite([
            *candidate["SS"][component]["candidate_c_point_fold"], *candidate["MS"][component]["candidate_c_point_fold"],
            *ss["conditional_variance"]["point_fold"], *ms["conditional_variance"]["point_fold"],
            *ss["oracle_nrmse"]["point_fold"], *ms["oracle_nrmse"]["point_fold"],
            *ss["coverage"]["point_fold"], *ms["coverage"]["point_fold"],
        ]).all())
        folds_valid = bool(absolute_folds_valid and relative_folds_valid)
        absolute_checks = {
            "candidate_c_point": bool(
                candidate_ms["candidate_c_evaluable"]
                and candidate_ms["candidate_c_d"] is not None
                and candidate_ms["candidate_c_d"] < 1.0
            ),
            "candidate_c_simultaneous_ucb": bool(
                candidate_ms["candidate_c_evaluable"]
                and candidate_ms["candidate_c_simultaneous_ucb"] is not None
                and candidate_ms["candidate_c_simultaneous_ucb"] < 1.0
            ),
            "conditional_variance_point": bool(ms["conditional_variance"]["point"] <= 0.25),
            "conditional_variance_simultaneous_ucb": bool(cvar_ucb <= 0.35),
            "oracle_nrmse_point": bool(ms["oracle_nrmse"]["point"] <= 0.60),
            "oracle_nrmse_simultaneous_ucb": bool(oracle_ucb <= 0.70),
            "improvement_point": bool(ms["improvement"]["point"] >= 0.25),
            "improvement_simultaneous_lcb": bool(improvement_lcb >= 0.15),
            "every_family_nrmse_point": all(family_point_pass.values()),
            "every_family_nrmse_simultaneous_ucb": all(family_bound_pass.values()),
            "coverage_overall": bool(ms["coverage"]["point"] >= 0.90),
            "coverage_every_family": all(coverage_family_pass.values()),
            "all_six_folds_valid": absolute_folds_valid,
        }
        cvar_relative = non_dnn_bounds["relative"]["conditional_variance"]
        oracle_relative = non_dnn_bounds["relative"]["oracle_nrmse"]
        cvar_index, oracle_index = COMPONENTS.index(component), COMPONENTS.index(component)
        cvar_ratio, oracle_ratio = float(cvar_relative["point"][cvar_index]), float(oracle_relative["point"][oracle_index])
        cvar_ratio_ucb = scalar_bound(cvar_relative["bounds"][component])
        oracle_ratio_ucb = scalar_bound(oracle_relative["bounds"][component])
        ss_raw, ms_raw = candidate["SS"][component]["candidate_c_d"], candidate["MS"][component]["candidate_c_d"]
        ss_d = float(ss_raw) if ss_raw is not None else math.nan
        ms_d = float(ms_raw) if ms_raw is not None else math.nan
        ratio_stable = bool(math.isfinite(ss_d) and ss_d > 100.0 * DIMENSIONLESS_FLOOR)
        paired_candidate_ratio = paired["candidate_c_ratio"]
        candidate_nonworsening = bool(
            math.isfinite(ss_d) and math.isfinite(ms_d) and ss_d > 0.0
            and ms_d - ss_d <= 0.02
            and (
                (not ratio_stable)
                or (
                    paired_candidate_ratio is not None
                    and math.isfinite(float(paired_candidate_ratio))
                    and float(paired_candidate_ratio) <= 1.05
                )
            )
        )
        worst_ss, worst_ms = float(np.max(ss["oracle_nrmse"]["point_family"])), float(np.max(ms["oracle_nrmse"]["point_family"]))
        worst_guard = bool(worst_ms - worst_ss <= 0.05 and all(family_point_pass.values()) and all(family_bound_pass.values()))
        coverage_guard = bool(
            ms["coverage"]["point"] >= 0.90
            and ms["coverage"]["point"] >= ss["coverage"]["point"] - 0.05
            and all(ms["coverage"]["point_family"] >= 0.80)
            and all(ms["coverage"]["point_family"] >= ss["coverage"]["point_family"] - 0.05)
        )
        reversal_folds = [
            f"FOLD_{fold}" for fold in FOLDS
            if candidate["MS"][component]["candidate_c_point_fold"][fold] > candidate["SS"][component]["candidate_c_point_fold"][fold] + DIMENSIONLESS_FLOOR
            and ms["conditional_variance"]["point_fold"][fold] > ss["conditional_variance"]["point_fold"][fold] + DIMENSIONLESS_FLOOR
            and ms["oracle_nrmse"]["point_fold"][fold] > ss["oracle_nrmse"]["point_fold"][fold] + DIMENSIONLESS_FLOOR
        ]
        relative_checks = {
            "candidate_c_point_ratio": bool(
                paired["candidate_c_evaluable"]
                and paired["candidate_c_ratio"] is not None
                and paired["candidate_c_ratio"] <= 0.80
            ),
            "candidate_c_simultaneous_ratio_ucb": bool(
                paired["candidate_c_evaluable"]
                and paired["candidate_c_ratio_simultaneous_ucb"] is not None
                and paired["candidate_c_ratio_simultaneous_ucb"] <= 0.90
            ),
            "conditional_variance_point_ratio": bool(cvar_ratio <= 0.80),
            "conditional_variance_simultaneous_ratio_ucb": bool(cvar_ratio_ucb <= 0.90),
            "oracle_nrmse_point_ratio": bool(oracle_ratio <= 0.85),
            "oracle_nrmse_simultaneous_ratio_ucb": bool(oracle_ratio_ucb <= 0.95),
            "candidate_c_nonworsening": candidate_nonworsening,
            "worst_family_guard": worst_guard, "coverage_guard": coverage_guard,
            "no_fold_three_effect_reversal": bool(relative_folds_valid and not reversal_folds),
        }
        ms_status, ss_status = ms["non_dnn_status"], ss["non_dnn_status"]
        absolute_candidate_evaluable = bool(candidate_ms["candidate_c_evaluable"])
        absolute_cvar_evaluable = bool(
            ms_status["conditional_variance"]["overall"]["evaluable"]
            and non_dnn_bounds["absolute"]["MS"]["conditional_variance"][component]["status"] == "EVALUABLE"
        )
        absolute_oracle_evaluable = bool(
            ms_status["oracle_nrmse"]["overall"]["evaluable"]
            and non_dnn_bounds["absolute"]["MS"]["oracle_nrmse"][component]["status"] == "EVALUABLE"
        )
        absolute_improvement_evaluable = bool(
            ms_status["improvement"]["overall"]["evaluable"]
            and non_dnn_bounds["absolute"]["MS"]["improvement"][component]["status"] == "EVALUABLE"
        )
        absolute_family_evaluable = bool(all(
            ms_status["oracle_nrmse"]["family"][family]["evaluable"]
            and non_dnn_bounds["family"]["MS"][family][component]["status"] == "EVALUABLE"
            for family in FAMILIES
        ))
        absolute_coverage_evaluable = bool(
            ms_status["coverage"]["overall"]["evaluable"]
            and all(ms_status["coverage"]["family"][family]["evaluable"] for family in FAMILIES)
        )
        absolute_evaluable = bool(
            absolute_candidate_evaluable and absolute_cvar_evaluable
            and absolute_oracle_evaluable and absolute_improvement_evaluable
            and absolute_family_evaluable and absolute_coverage_evaluable
            and absolute_folds_valid
        )

        relative_candidate_evaluable = bool(
            candidate["SS"][component]["candidate_c_evaluable"]
            and candidate["MS"][component]["candidate_c_evaluable"]
            and paired["candidate_c_evaluable"]
        )
        relative_cvar_evaluable = bool(
            ss_status["conditional_variance"]["overall"]["evaluable"]
            and ms_status["conditional_variance"]["overall"]["evaluable"]
            and math.isfinite(cvar_ratio) and math.isfinite(cvar_ratio_ucb)
            and non_dnn_bounds["relative"]["conditional_variance"]["bounds"][component]["status"] == "EVALUABLE"
        )
        relative_oracle_evaluable = bool(
            ss_status["oracle_nrmse"]["overall"]["evaluable"]
            and ms_status["oracle_nrmse"]["overall"]["evaluable"]
            and math.isfinite(oracle_ratio) and math.isfinite(oracle_ratio_ucb)
            and non_dnn_bounds["relative"]["oracle_nrmse"]["bounds"][component]["status"] == "EVALUABLE"
        )
        relative_family_evaluable = bool(all(
            ss_status["oracle_nrmse"]["family"][family]["evaluable"]
            and ms_status["oracle_nrmse"]["family"][family]["evaluable"]
            and non_dnn_bounds["family"]["MS"][family][component]["status"] == "EVALUABLE"
            for family in FAMILIES
        ))
        relative_coverage_evaluable = bool(
            all(status["coverage"]["overall"]["evaluable"] for status in (ss_status, ms_status))
            and all(
                status["coverage"]["family"][family]["evaluable"]
                for status in (ss_status, ms_status) for family in FAMILIES
            )
        )
        relative_evaluable = bool(
            relative_candidate_evaluable and relative_cvar_evaluable
            and relative_oracle_evaluable and relative_family_evaluable
            and relative_coverage_evaluable and relative_folds_valid
        )
        dnn_evaluable = relative_candidate_evaluable
        cvar_evaluable = bool(absolute_cvar_evaluable and relative_cvar_evaluable)
        oracle_evaluable = bool(
            absolute_oracle_evaluable and absolute_improvement_evaluable
            and absolute_family_evaluable and relative_oracle_evaluable
            and relative_family_evaluable
        )
        coverage_evaluable = bool(absolute_coverage_evaluable and relative_coverage_evaluable)
        component_evaluable = bool(absolute_evaluable and relative_evaluable)
        absolute_pass = bool(absolute_evaluable and all(absolute_checks.values()))
        relative_pass = bool(relative_evaluable and all(relative_checks.values()))

        absolute_mechanisms: list[str] = []
        relative_mechanisms: list[str] = []
        def add_mechanism(destination: list[str], value: str) -> None:
            mechanism = value if value else NON_DNN_BOOTSTRAP_NE
            if mechanism != "EVALUABLE" and mechanism not in destination:
                destination.append(mechanism)
        def add_leaf_mechanism(destination: list[str], leaf: dict[str, Any]) -> None:
            if not leaf["evaluable"]:
                add_mechanism(destination, str(leaf["not_evaluable_mechanism"]))
        if not absolute_candidate_evaluable:
            add_mechanism(absolute_mechanisms, str(candidate_ms["candidate_c_status"]))
        for metric in ("conditional_variance", "oracle_nrmse", "improvement", "coverage"):
            add_leaf_mechanism(absolute_mechanisms, ms_status[metric]["overall"])
        for record in (
            non_dnn_bounds["absolute"]["MS"]["conditional_variance"][component],
            non_dnn_bounds["absolute"]["MS"]["oracle_nrmse"][component],
            non_dnn_bounds["absolute"]["MS"]["improvement"][component],
        ):
            if record["status"] != "EVALUABLE":
                add_mechanism(absolute_mechanisms, str(record["status"]))
        for family in FAMILIES:
            add_leaf_mechanism(absolute_mechanisms, ms_status["oracle_nrmse"]["family"][family])
            add_leaf_mechanism(absolute_mechanisms, ms_status["coverage"]["family"][family])
            family_bound = non_dnn_bounds["family"]["MS"][family][component]
            if family_bound["status"] != "EVALUABLE":
                add_mechanism(absolute_mechanisms, str(family_bound["status"]))
        for metric in ("conditional_variance", "oracle_nrmse", "coverage"):
            for fold in FOLDS:
                add_leaf_mechanism(
                    absolute_mechanisms,
                    ms_status[metric]["fold"][f"FOLD_{fold}"],
                )
        if not absolute_folds_valid:
            if not np.isfinite(candidate["MS"][component]["candidate_c_point_fold"]).all():
                add_mechanism(absolute_mechanisms, CA_ZERO_STATUS)

        for arm in ARMS:
            candidate_record = candidate[arm][component]
            if not candidate_record["candidate_c_evaluable"]:
                add_mechanism(relative_mechanisms, str(candidate_record["candidate_c_status"]))
        if not paired["candidate_c_evaluable"]:
            add_mechanism(relative_mechanisms, str(paired["candidate_c_status"]))
        for status in (ss_status, ms_status):
            for metric in ("conditional_variance", "oracle_nrmse", "coverage"):
                add_leaf_mechanism(relative_mechanisms, status[metric]["overall"])
            for family in FAMILIES:
                add_leaf_mechanism(relative_mechanisms, status["oracle_nrmse"]["family"][family])
                add_leaf_mechanism(relative_mechanisms, status["coverage"]["family"][family])
            for metric in ("conditional_variance", "oracle_nrmse", "coverage"):
                for fold in FOLDS:
                    add_leaf_mechanism(
                        relative_mechanisms,
                        status[metric]["fold"][f"FOLD_{fold}"],
                    )
        for record in (
            non_dnn_bounds["relative"]["conditional_variance"]["bounds"][component],
            non_dnn_bounds["relative"]["oracle_nrmse"]["bounds"][component],
            *(non_dnn_bounds["family"]["MS"][family][component] for family in FAMILIES),
        ):
            if record["status"] != "EVALUABLE":
                add_mechanism(relative_mechanisms, str(record["status"]))
        if not relative_folds_valid:
            if not all(
                np.isfinite(candidate[arm][component]["candidate_c_point_fold"]).all()
                for arm in ARMS
            ):
                add_mechanism(relative_mechanisms, CA_ZERO_STATUS)
        if not component_evaluable:
            status = "H_MSO01R_COMPONENT_NOT_EVALUABLE"
        elif absolute_pass and relative_pass:
            status = "H_MSO01R_COMPONENT_QUALIFIED"
        elif absolute_pass:
            status = "IDENTIFIABLE_BUT_MULTISCALE_RESCUE_NOT_ESTABLISHED"
        elif relative_pass:
            status = "RELATIVE_RESCUE_OBSERVED_BUT_ABSOLUTE_IDENTIFIABILITY_NOT_QUALIFIED"
        else:
            status = "H_MSO01R_COMPONENT_NOT_QUALIFIED"
        record = {
            "component": component, "dnn_evaluable": dnn_evaluable, "cvar_evaluable": cvar_evaluable,
            "oracle_evaluable": oracle_evaluable, "coverage_evaluable": coverage_evaluable,
            "all_required_folds_valid": folds_valid, "component_evaluable": component_evaluable,
            "absolute_evaluable": absolute_evaluable,
            "relative_rescue_evaluable": relative_evaluable,
            "absolute_pass": absolute_pass, "relative_rescue_pass": relative_pass,
            "component_pass": bool(absolute_pass and relative_pass), "status": status,
            "absolute_checks": absolute_checks, "relative_checks": relative_checks,
            "family_point_checks": family_point_pass, "family_simultaneous_ucb_checks": family_bound_pass,
            "coverage_family_checks": coverage_family_pass, "reversal_folds": reversal_folds,
            "conditional_variance_ratio": cvar_ratio, "conditional_variance_ratio_simultaneous_ucb": cvar_ratio_ucb,
            "oracle_nrmse_ratio": oracle_ratio, "oracle_nrmse_ratio_simultaneous_ucb": oracle_ratio_ucb,
            "worst_family_ss": worst_ss, "worst_family_ms": worst_ms,
            "not_evaluable_mechanisms": {
                "absolute": absolute_mechanisms,
                "relative": relative_mechanisms,
            },
        }
        components[component] = record
        verdict_rows.append({key: json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else value for key, value in record.items()})
        for requirement, passed in relative_checks.items():
            if requirement.startswith("candidate_c"):
                requirement_evaluable = relative_candidate_evaluable
                requirement_status = "EVALUABLE" if requirement_evaluable else str(paired["candidate_c_status"])
            elif requirement.startswith("conditional_variance"):
                requirement_evaluable = relative_cvar_evaluable
                requirement_status = str(non_dnn_bounds["relative"]["conditional_variance"]["bounds"][component]["status"])
            elif requirement.startswith("oracle_nrmse"):
                requirement_evaluable = relative_oracle_evaluable
                requirement_status = str(non_dnn_bounds["relative"]["oracle_nrmse"]["bounds"][component]["status"])
            elif requirement == "worst_family_guard":
                requirement_evaluable = relative_family_evaluable
                requirement_status = "EVALUABLE" if requirement_evaluable else (relative_mechanisms[0] if relative_mechanisms else "NOT_EVALUABLE")
            elif requirement == "coverage_guard":
                requirement_evaluable = relative_coverage_evaluable
                requirement_status = "EVALUABLE" if requirement_evaluable else (relative_mechanisms[0] if relative_mechanisms else "NOT_EVALUABLE")
            else:
                requirement_evaluable = relative_folds_valid
                requirement_status = "EVALUABLE" if requirement_evaluable else (relative_mechanisms[0] if relative_mechanisms else NON_DNN_BOOTSTRAP_NE)
            rescue_rows.append({
                "component": component, "requirement": requirement,
                "requirement_pass": passed,
                "status": requirement_status,
                "evaluable": requirement_evaluable,
                "not_evaluable_mechanism": "" if requirement_evaluable else requirement_status,
                "ss_candidate_c": ss_d if requirement.startswith("candidate_c") else "",
                "ms_candidate_c": ms_d if requirement.startswith("candidate_c") else "",
                "conditional_variance_ratio": cvar_ratio,
                "conditional_variance_ratio_simultaneous_ucb": cvar_ratio_ucb,
                "oracle_nrmse_ratio": oracle_ratio,
                "oracle_nrmse_ratio_simultaneous_ucb": oracle_ratio_ucb,
                "worst_family_ss": worst_ss, "worst_family_ms": worst_ms,
                "reversal_folds": "|".join(reversal_folds),
                "point_threshold": {
                    "conditional_variance_point_ratio": 0.80,
                    "oracle_nrmse_point_ratio": 0.85,
                    "candidate_c_point_ratio": 0.80,
                }.get(requirement, "SEE_FROZEN_CONTRACT"),
                "confidence_threshold": {
                    "conditional_variance_simultaneous_ratio_ucb": 0.90,
                    "oracle_nrmse_simultaneous_ratio_ucb": 0.95,
                    "candidate_c_simultaneous_ratio_ucb": 0.90,
                }.get(requirement, "SEE_FROZEN_CONTRACT"),
            })
    global_evaluable = all(value["component_evaluable"] for value in components.values())
    global_pass = global_evaluable and all(value["status"] == "H_MSO01R_COMPONENT_QUALIFIED" for value in components.values())
    global_status = (
        "H_MSO01R_MULTISCALE_IDENTIFIABILITY_RESCUE_NOT_EVALUABLE" if not global_evaluable
        else "H_MSO01R_MULTISCALE_IDENTIFIABILITY_RESCUE_QUALIFIED" if global_pass
        else "H_MSO01R_MULTISCALE_IDENTIFIABILITY_RESCUE_NOT_QUALIFIED"
    )
    return {
        "components": components, "global_evaluable": global_evaluable, "global_pass": global_pass,
        "global_status": global_status, "mso03_deterministic_closure_baseline_eligible": global_pass,
        "neural_training_authorized": False, "attention_authorized": False,
        "learned_operator_authorized": False, "mso03_executed": False,
    }, verdict_rows, rescue_rows


def metric_csv_rows(arm: str, component: str, values: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    cvar_rows, oracle_rows, coverage_rows = [], [], []
    scopes = [("OVERALL", "ALL", None)] + [("FAMILY", family, index) for index, family in enumerate(FAMILIES)] + [("FOLD", f"FOLD_{fold}", fold) for fold in FOLDS]
    for scope, scope_id, index in scopes:
        status_scope = "overall" if scope == "OVERALL" else scope.lower()
        status_key = None if scope == "OVERALL" else scope_id
        def status_for(metric: str) -> dict[str, Any]:
            record = values["non_dnn_status"][metric][status_scope]
            return record if status_key is None else record[status_key]
        if scope == "OVERALL":
            cvar = values["conditional_variance"]["point"]
            oracle = values["oracle_nrmse"]["point"]
            baseline = values["baseline_nrmse"]["point"]
            coverage = values["coverage"]["point"]
        elif scope == "FAMILY":
            cvar = float(values["conditional_variance"]["point_family"][index])
            oracle = float(values["oracle_nrmse"]["point_family"][index])
            baseline = float(values["baseline_nrmse"]["point_family"][index])
            coverage = float(values["coverage"]["point_family"][index])
        else:
            cvar = float(values["conditional_variance"]["point_fold"][index])
            oracle = float(values["oracle_nrmse"]["point_fold"][index])
            baseline = float(values["baseline_nrmse"]["point_fold"][index])
            coverage = float(values["coverage"]["point_fold"][index])
        cvar_status = status_for("conditional_variance")
        oracle_status = status_for("oracle_nrmse")
        baseline_status = status_for("mean_baseline_nrmse")
        coverage_status = status_for("coverage")
        improvement_status = (
            values["non_dnn_status"]["improvement"]["overall"]
            if scope == "OVERALL"
            else {
                "status": "NOT_APPLICABLE_NON_OVERALL_SCOPE", "evaluable": False,
                "not_evaluable_mechanism": "NOT_APPLICABLE_NON_OVERALL_SCOPE",
            }
        )
        cvar_rows.append({
            "arm": arm, "component": component, "scope": scope, "scope_id": scope_id,
            "conditional_variance": cvar, **cvar_status,
        })
        oracle_rows.append({
            "arm": arm, "component": component, "scope": scope, "scope_id": scope_id,
            "oracle_nrmse": oracle, "mean_baseline_nrmse": baseline,
            "improvement_over_mean_baseline": values["improvement"]["point"] if scope == "OVERALL" else "",
            "oracle_status": oracle_status["status"],
            "oracle_evaluable": oracle_status["evaluable"],
            "oracle_not_evaluable_mechanism": oracle_status["not_evaluable_mechanism"],
            "mean_baseline_status": baseline_status["status"],
            "mean_baseline_evaluable": baseline_status["evaluable"],
            "mean_baseline_not_evaluable_mechanism": baseline_status["not_evaluable_mechanism"],
            "improvement_status": improvement_status["status"],
            "improvement_evaluable": improvement_status["evaluable"],
            "improvement_not_evaluable_mechanism": improvement_status["not_evaluable_mechanism"],
            "selected_oracles_by_outer_fold": json.dumps(values["selected_oracles_by_fold"], sort_keys=True),
        })
        if component == COMPONENTS[0]:
            coverage_rows.append({
                "arm": arm, "scope": scope, "scope_id": scope_id, "coverage": coverage,
                **coverage_status, "component_independent": True,
                "can_substitute_for_identifiability": False,
            })
    return cvar_rows, oracle_rows, coverage_rows


def summary_metrics(candidate: dict[str, Any], non_dnn: dict[str, Any], bounds: dict[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {arm: {} for arm in ARMS}
    for arm in ARMS:
        for component in COMPONENTS:
            c, n = candidate[arm][component], non_dnn[arm][component]
            status = n["non_dnn_status"]
            non_dnn_status = {
                "conditional_variance": {
                    **status["conditional_variance"],
                    "simultaneous_bound": bound_status_leaf(bounds["absolute"][arm]["conditional_variance"][component]),
                },
                "oracle_nrmse": {
                    **status["oracle_nrmse"],
                    "simultaneous_bound": bound_status_leaf(bounds["absolute"][arm]["oracle_nrmse"][component]),
                    "family_simultaneous_bound": {
                        family: bound_status_leaf(bounds["family"][arm][family][component])
                        for family in FAMILIES
                    },
                },
                "mean_baseline_nrmse": status["mean_baseline_nrmse"],
                "improvement": {
                    **status["improvement"],
                    "simultaneous_bound": bound_status_leaf(bounds["absolute"][arm]["improvement"][component]),
                },
                "coverage": status["coverage"],
            }
            output[arm][component] = {
                "candidate_c_d": c["candidate_c_d"], "candidate_c_wn": c["candidate_c_wn"], "candidate_c_wb": c["candidate_c_wb"],
                "candidate_c_status": c["candidate_c_status"], "candidate_c_evaluable": c["candidate_c_evaluable"],
                "candidate_c_source_alias": c["candidate_c_source_alias"],
                "candidate_c_bound_status": c["candidate_c_bound_status"],
                "candidate_c_simultaneous_ucb": c["candidate_c_simultaneous_ucb"],
                "candidate_c_absolute_gate_pass": c["candidate_c_absolute_gate_pass"],
                "candidate_c_point_fold": c["candidate_c_point_fold"],
                "conditional_variance": n["conditional_variance"]["point"],
                "conditional_variance_simultaneous_ucb": scalar_bound(bounds["absolute"][arm]["conditional_variance"][component]),
                "oracle_nrmse": n["oracle_nrmse"]["point"],
                "oracle_nrmse_simultaneous_ucb": scalar_bound(bounds["absolute"][arm]["oracle_nrmse"][component]),
                "baseline_nrmse": n["baseline_nrmse"]["point"], "improvement": n["improvement"]["point"],
                "improvement_simultaneous_lcb": scalar_bound(bounds["absolute"][arm]["improvement"][component]),
                "family_nrmse": {family: float(n["oracle_nrmse"]["point_family"][index]) for index, family in enumerate(FAMILIES)},
                "family_nrmse_simultaneous_ucb": {family: scalar_bound(bounds["family"][arm][family][component]) for family in FAMILIES},
                "coverage": n["coverage"]["point"],
                "coverage_family": {family: float(n["coverage"]["point_family"][index]) for index, family in enumerate(FAMILIES)},
                "coverage_fold": {f"FOLD_{fold}": float(n["coverage"]["point_fold"][fold]) for fold in FOLDS},
                "selected_oracles_by_fold": n["selected_oracles_by_fold"],
                "non_dnn_status": non_dnn_status,
            }
    output["paired"] = {}
    for component in COMPONENTS:
        c = candidate["paired"][component]
        output["paired"][component] = {
            **{key: value for key, value in c.items() if not isinstance(value, np.ndarray)},
            "conditional_variance_ratio": float(bounds["relative"]["conditional_variance"]["point"][COMPONENTS.index(component)]),
            "conditional_variance_ratio_simultaneous_ucb": scalar_bound(bounds["relative"]["conditional_variance"]["bounds"][component]),
            "conditional_variance_ratio_status": bounds["relative"]["conditional_variance"]["bounds"][component]["status"],
            "oracle_nrmse_ratio": float(bounds["relative"]["oracle_nrmse"]["point"][COMPONENTS.index(component)]),
            "oracle_nrmse_ratio_simultaneous_ucb": scalar_bound(bounds["relative"]["oracle_nrmse"]["bounds"][component]),
            "oracle_nrmse_ratio_status": bounds["relative"]["oracle_nrmse"]["bounds"][component]["status"],
        }
    return output


def run_real() -> None:
    global _STAGING_ACTIVE
    required = (FREEZE, TARGET, TARGET_LEDGER, PREFLIGHT)
    if not all(path.is_file() for path in required):
        raise RuntimeError("HMSO01R_B_FORMAL_INPUT_MISSING")
    if git("branch", "--show-current") != "main" or git("remote"):
        raise RuntimeError("HMSO01R_B_FORMAL_GIT_BOUNDARY_FAILURE")
    target_ledger = json.loads(TARGET_LEDGER.read_text(encoding="utf-8"))
    pre_target_commit = str(target_ledger.get("hmso01r_b_pre_target_commit", target_ledger.get("pre_target_commit")))
    if (
        len(pre_target_commit) != 40
        or git("rev-parse", "HEAD") != pre_target_commit
        or git("show", "-s", "--format=%s", "HEAD") != "H-MSO-01R-B: freeze fresh confirmatory execution"
        or target_ledger["qualified_case_count"] != 384
        or target_ledger["failed_case_count"] != 0
    ):
        raise RuntimeError("HMSO01R_B_TARGET_REFERENCE_QUALIFICATION_NOT_COMPLETE")
    allowed_dirty_prefixes = (
        "06_experiments/hmso01r_b/target_ref/",
        "06_experiments/hmso01r_b/.formal_staging/",
    )
    allowed_dirty_exact = {
        "06_experiments/hmso01r_b/target_reference_qualification.csv",
        "06_experiments/hmso01r_b/target_access_ledger.json",
        *(path.relative_to(ROOT).as_posix() for path in REAL_OUTPUTS),
    }
    porcelain = git("status", "--porcelain=v1", "--untracked-files=all").splitlines()
    if any(
        record[3:] not in allowed_dirty_exact
        and not any(record[3:].startswith(prefix) for prefix in allowed_dirty_prefixes)
        for record in porcelain
    ):
        raise RuntimeError("HMSO01R_B_FORMAL_WORKTREE_BOUNDARY_FAILURE")
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    freeze_relative = FREEZE.relative_to(ROOT).as_posix()
    committed_freeze = subprocess.run(
        ["git", "show", f"{pre_target_commit}:{freeze_relative}"], cwd=ROOT,
        check=True, capture_output=True,
    ).stdout
    ledger_freeze_sha = target_ledger.get("pre_target_freeze_sha256", target_ledger.get("frozen_identity", {}).get("pre_target_freeze_sha256"))
    if sha256(FREEZE) != hashlib.sha256(committed_freeze).hexdigest() or ledger_freeze_sha != sha256(FREEZE):
        raise RuntimeError("HMSO01R_B_PRE_TARGET_FREEZE_GIT_LEDGER_IDENTITY_FAILURE")
    if freeze.get("status") != "FROZEN_BEFORE_FIRST_FRESH_TARGET_REFERENCE_ACCESS":
        raise RuntimeError("HMSO01R_B_PRE_TARGET_FREEZE_STATUS_FAILURE")
    binding = freeze.get("git_binding", {})
    if (
        binding.get("binding_mode") != "DISCOVER_PRE_TARGET_COMMIT_AT_FIRST_TARGET_ACCESS_FROM_CLEAN_HEAD"
        or binding.get("pre_target_commit") != "DISCOVERED_AT_FIRST_TARGET_ACCESS_FROM_CLEAN_HEAD"
        or binding.get("parent_head_at_file_creation") != "9048eff137001e5f644575bd02c3856b4f4ac532"
        or binding.get("branch") != "main"
        or binding.get("remote") is not None
        or binding.get("working_tree_clean_required") is not True
    ):
        raise RuntimeError("HMSO01R_B_PRE_TARGET_FREEZE_BINDING_FAILURE")
    artifacts = validate_freeze_records(freeze, pre_target_commit)
    preflight = json.loads(PREFLIGHT.read_text(encoding="utf-8"))
    if not isinstance(preflight, dict):
        raise RuntimeError("HMSO01R_B_FORMAL_PREFLIGHT_SCHEMA_FAILURE")
    validate_preflight_attestation(preflight, artifacts, pre_target_commit)
    if target_ledger.get("target_store_sha256") != sha256(TARGET):
        raise RuntimeError("HMSO01R_B_TARGET_STORE_LEDGER_IDENTITY_FAILURE")
    authorized = target_ledger.get("authorized_activity_counts", {})
    prohibited_ledger = target_ledger.get("prohibited_activity_counts", {})
    expected_builder_authorized = {
        "target_case_evaluation_count": 384, "reference_evaluation_count": 384,
        "target_store_read_count": 0, "target_store_write_count": 1,
        "candidate_c_evaluation_count": 0, "conditional_variance_evaluation_count": 0,
        "oracle_fit_count": 0, "coverage_evaluation_count": 0,
        "paired_rescue_evaluation_count": 0, "bootstrap_draws_consumed": 0,
    }
    expected_prohibited_keys = {
        "neural_model_count", "attention_count", "transformer_count", "learned_operator_count", "optimizer_count", "training_count",
        "time_integration_count", "solver_in_loop_count", "rollout_count", "sealed_test_count", "arc_access_count",
        "target_derived_feature_modification_count", "target_derived_scale_modification_count", "target_derived_fold_modification_count",
        "target_derived_normalization_modification_count", "target_derived_metric_modification_count", "target_derived_gate_modification_count",
        "target_derived_oracle_modification_count", "case_replacement_after_target_access",
    }
    ledger_before = target_ledger.get("observable_store_sha256_before", target_ledger.get("observable_store_sha256_before_target_generation"))
    ledger_after = target_ledger.get("observable_store_sha256_after", target_ledger.get("observable_store_sha256_after_target_generation"))
    if (
        any(authorized.get(key) != value for key, value in expected_builder_authorized.items())
        or set(prohibited_ledger) != expected_prohibited_keys
        or any(value != 0 for value in prohibited_ledger.values())
        or ledger_before != EXPECTED_OBSERVABLE_SHA or ledger_after != EXPECTED_OBSERVABLE_SHA
        or target_ledger.get("case_replacement_after_target_access") != 0
    ):
        raise RuntimeError("HMSO01R_B_TARGET_ACCESS_LEDGER_FAILURE")
    observable_before = sha256(OBSERVABLE)
    if observable_before != EXPECTED_OBSERVABLE_SHA:
        raise RuntimeError("HMSO01R_B_OBSERVABLE_STORE_IDENTITY_FAILURE")
    resumed = resume_or_prepare_staging()
    if resumed is not None:
        print(json.dumps({
            "terminal_status": resumed["terminal_status"],
            "global_status": resumed["verdict"]["global_status"],
            "publication_resumed": True,
        }, sort_keys=True), flush=True)
        return
    STAGING.mkdir(parents=False, exist_ok=False)
    _STAGING_ACTIVE = True
    data, cases, _ = load_real_data()
    neighbors, comparator, draws = load_frozen_identities()
    inherited_invalid, bootstrap_audit = bootstrap_integrity(cases, draws)
    candidate, candidate_bound_rows, division_cells, paired_divisions = candidate_metrics(
        data, cases, neighbors, comparator, draws
    )
    non_dnn, fold_records, _, oracle_fits = non_dnn_case_metrics(data, cases, neighbors, draws)
    non_dnn_bounds, non_dnn_bound_rows = build_non_dnn_bounds(non_dnn, inherited_invalid)
    verdict, verdict_rows, rescue_rows = evaluate_components(candidate, non_dnn, non_dnn_bounds)
    inference_completeness = bound_procedure_completeness(
        candidate_bound_rows + non_dnn_bound_rows
    )
    if not inference_completeness["all_required_bound_procedures_executed"]:
        raise RuntimeError("HMSO01R_B_REQUIRED_BOUND_PROCEDURE_ROWSET_FAILURE")

    candidate_rows = {arm: [] for arm in ARMS}
    paired_candidate_rows = []
    for arm in ARMS:
        for component in COMPONENTS:
            value = candidate[arm][component]
            candidate_rows[arm].append({
                "arm": arm, "component": component, "scope": "OVERALL", "scope_id": "ALL",
                **{key: val for key, val in value.items() if key.startswith("candidate_c_") and not isinstance(val, np.ndarray)},
            })
    for component in COMPONENTS:
        paired_candidate_rows.append({"component": component, **{key: val for key, val in candidate["paired"][component].items() if not isinstance(val, np.ndarray)}})
    write_csv(SS_CANDIDATE, candidate_rows["SS"])
    write_csv(MS_CANDIDATE, candidate_rows["MS"])
    write_csv(PAIRED_CANDIDATE, paired_candidate_rows)
    write_csv(CANDIDATE_BOUNDS, candidate_bound_rows)

    cvar_rows, oracle_rows, coverage_rows = {arm: [] for arm in ARMS}, {arm: [] for arm in ARMS}, []
    for arm in ARMS:
        for component in COMPONENTS:
            cr, ore, cov = metric_csv_rows(arm, component, non_dnn[arm][component])
            cvar_rows[arm].extend(cr); oracle_rows[arm].extend(ore); coverage_rows.extend(cov)
    write_csv(SS_CVAR, cvar_rows["SS"]); write_csv(MS_CVAR, cvar_rows["MS"])
    write_csv(SS_ORACLE, oracle_rows["SS"]); write_csv(MS_ORACLE, oracle_rows["MS"])
    write_csv(COVERAGE, coverage_rows)
    write_csv(PAIRED_NON_DNN, rescue_rows)
    write_csv(ALL_BOUNDS, non_dnn_bound_rows + candidate_bound_rows)
    write_csv(VERDICTS, verdict_rows)

    final_divisions = sum(
        row["point_candidate_c_division_count"] + row["bootstrap_candidate_c_division_count"]
        + row["fold_candidate_c_division_count"] for row in division_cells
    ) + sum(row["point_ratio_division_count"] + row["bootstrap_ratio_division_count"] for row in paired_divisions)
    division_audit = {
        "schema_version": "1.0.0", "stage": "H-MSO-01R-B", "pointwise_division_count": 0,
        "final_candidate_c_division_count": final_divisions, "expected_final_candidate_c_division_count": final_divisions,
        "arm_component_divisions": division_cells, "paired_ratio_divisions": paired_divisions,
        "bootstrap_draws_consumed": 10000, "bootstrap_unique_draw_count": 10000,
        "bootstrap_draws_sha256": EXPECTED_BOOTSTRAP_SHA, "paired_ss_ms_identity": True,
        "recomputed_WN_each_draw": True, "recomputed_WB_each_draw": True,
        "epsilon_count": 0, "clipping_count": 0, "zero_row_deletion_count": 0, "zero_group_deletion_count": 0,
    }
    write_json(DIVISION_AUDIT, division_audit)
    prohibited = {key: 0 for key in (
        "neural_model_count", "attention_count", "transformer_count", "learned_operator_count", "optimizer_count", "training_count",
        "time_integration_count", "solver_in_loop_count", "rollout_count", "sealed_test_count", "arc_access_count",
        "target_derived_feature_modification_count", "target_derived_scale_modification_count", "target_derived_fold_modification_count",
        "target_derived_normalization_modification_count", "target_derived_metric_modification_count", "target_derived_gate_modification_count",
        "target_derived_oracle_modification_count", "case_replacement_after_target_access",
    )}
    observable_after = sha256(OBSERVABLE)
    firewall = {
        "schema_version": "1.0.0", "stage": "H-MSO-01R-B", "status": "PASS",
        "authorized_activity_counts": {
            "target_case_evaluation_count": 384, "reference_evaluation_count": 384,
            "target_store_read_count": 1, "target_store_write_count": 1,
            "candidate_c_evaluation_count": 1, "conditional_variance_evaluation_count": 1,
            "oracle_fit_count": oracle_fits, "coverage_evaluation_count": 1,
            "paired_rescue_evaluation_count": 1, "bootstrap_draws_consumed": 10000,
        },
        "prohibited_activity_counts": prohibited,
        "observable_store_sha256_before": observable_before, "observable_store_sha256_after": observable_after,
        "all_frozen_inputs_unchanged": observable_before == observable_after,
        "bootstrap_decode_audit": bootstrap_audit,
    }
    write_json(FIREWALL, firewall)
    formal_output_sha256 = {
        path.relative_to(ROOT).as_posix(): sha256(output_path(path))
        for path in REAL_OUTPUTS if path != SUMMARY
    }
    terminal = {
        "H_MSO01R_MULTISCALE_IDENTIFIABILITY_RESCUE_QUALIFIED": "HMSO01R_B_FRESH_CONFIRMATORY_MULTISCALE_IDENTIFIABILITY_RESCUE_QUALIFIED",
        "H_MSO01R_MULTISCALE_IDENTIFIABILITY_RESCUE_NOT_QUALIFIED": "HMSO01R_B_FRESH_CONFIRMATORY_MULTISCALE_IDENTIFIABILITY_RESCUE_NOT_QUALIFIED",
        "H_MSO01R_MULTISCALE_IDENTIFIABILITY_RESCUE_NOT_EVALUABLE": "HMSO01R_B_FRESH_CONFIRMATORY_MULTISCALE_IDENTIFIABILITY_RESCUE_NOT_EVALUABLE",
    }[verdict["global_status"]]
    summary = {
        "schema_version": "1.0.0", "stage": "H-MSO-01R-B", "terminal_status": terminal,
        "hmso01r_b_pre_target_commit": pre_target_commit, "pre_target_commit": pre_target_commit,
        "target_reference_qualified_case_count": 384, "target_reference_failed_case_count": 0,
        "target_definition": "CONTINUUM_ANALYTICAL_REFERENCE_MINUS_LAMBDA_1_FROZEN_BASE_SPH",
        "observable_store_unchanged": observable_before == observable_after,
        "observable_store_sha256_before": observable_before, "observable_store_sha256_after": observable_after,
        "ss_feature_dimension": 39, "ms_feature_dimension": 110, "formal_sample_row_count": 49152,
        "bootstrap_replicate_count": 10000, "bootstrap_unique_draw_count": 10000, "bootstrap_draws_consumed": 10000,
        "bootstrap_decode_audit": bootstrap_audit,
        "candidate_c_zero_status_authority": {
            "canonical_status": CA_ZERO_STATUS,
            "source_alias": CURRENT_ZERO_ALIAS,
        },
        "metrics": summary_metrics(candidate, non_dnn, non_dnn_bounds), "verdict": verdict,
        "simultaneous_inference": {
            "method": "MAXIMUM_STUDENTIZED",
            "confidence_level": 0.95,
            "multiplicity_scope": "THREE_PRIMARY_COMPONENTS_WITHIN_EACH_METRIC_FAMILY",
            "required_bound_row_count": 57,
            **inference_completeness,
        },
        "post_target_modification_counts": {key: 0 for key in prohibited if key.startswith("target_derived_") or key == "case_replacement_after_target_access"},
        "pointwise_division_count": 0, "pre_target_freeze_sha256": sha256(FREEZE),
        "formal_evaluator_sha256": sha256(Path(__file__).resolve()), "candidate_c_implementation_preflight_sha256": sha256(PREFLIGHT),
        "target_store_sha256": sha256(TARGET), "target_access_ledger_sha256": sha256(TARGET_LEDGER),
        "firewall_audit_sha256": formal_output_sha256[FIREWALL.relative_to(ROOT).as_posix()],
        "candidate_c_division_audit_sha256": formal_output_sha256[DIVISION_AUDIT.relative_to(ROOT).as_posix()],
        "formal_output_sha256": formal_output_sha256,
    }
    write_json(SUMMARY, summary)
    output_hashes = {
        path.name: sha256(output_path(path)) for path in REAL_OUTPUTS
    }
    _STAGING_ACTIVE = False
    write_json(TRANSACTION, {
        "schema_version": "1.0.0",
        "stage": "H-MSO-01R-B_FORMAL_OUTPUT_TRANSACTION",
        "status": "COMPLETE_READY_TO_PUBLISH",
        "formal_evaluator_sha256": sha256(Path(__file__).resolve()),
        "target_store_sha256": sha256(TARGET),
        "pre_target_commit": pre_target_commit,
        "output_sha256": output_hashes,
        "summary_published_last": True,
    })
    published_summary = publish_transaction()
    print(json.dumps({
        "terminal_status": published_summary["terminal_status"],
        "global_status": published_summary["verdict"]["global_status"],
        "publication_resumed": False,
    }, sort_keys=True), flush=True)


def synthetic_cases() -> list[dict[str, Any]]:
    cases = []
    index = 0
    for fold in FOLDS:
        for family in FAMILIES:
            for lineage_position in range(2):
                for case_position in range(2):
                    cases.append({
                        "formal_case_index": index,
                        "fold": f"FOLD_{fold}",
                        "macro_family": family,
                        "field_lineage_id": f"SYN|{fold}|{family}|{lineage_position}",
                    })
                    index += 1
    return cases


def synthetic_draws(cases: list[dict[str, Any]]) -> dict[str, np.ndarray]:
    rng = np.random.Generator(np.random.PCG64(20260813))
    lineage_cases: dict[tuple[int, str, str], list[int]] = defaultdict(list)
    for index, case in enumerate(cases):
        lineage_cases[(int(case["fold"].split("_")[1]), case["macro_family"], case["field_lineage_id"])].append(index)
    offsets, case_ids, occurrence_ids, strata_ids = [0], [], [], []
    for _ in range(10000):
        occurrence = 0
        for fold in FOLDS:
            for family_index, family in enumerate(FAMILIES):
                lineages = sorted({key[2] for key in lineage_cases if key[:2] == (fold, family)})
                selected = rng.integers(0, len(lineages), len(lineages))
                for selection in selected:
                    lineage = lineages[int(selection)]
                    source = lineage_cases[(fold, family, lineage)]
                    chosen = rng.integers(0, len(source), len(source))
                    for position in chosen:
                        case_ids.append(source[int(position)])
                        occurrence_ids.append(occurrence)
                        strata_ids.append(fold * 4 + family_index)
                    occurrence += 1
        offsets.append(len(case_ids))
    return {
        "replicate_offsets": np.asarray(offsets, dtype=np.int64),
        "drawn_case_index": np.asarray(case_ids, dtype=np.int32),
        "drawn_occurrence_index": np.asarray(occurrence_ids, dtype=np.int16),
        "drawn_stratum_index": np.asarray(strata_ids, dtype=np.int8),
    }


def run_preflight() -> None:
    # This path is intentionally self-contained and target blind.  In
    # particular, OBSERVABLE and TARGET are never opened or hashed here.
    if PREFLIGHT.exists():
        raise RuntimeError("HMSO01R_B_PREFLIGHT_ALREADY_EXISTS_REFUSING_REPLACEMENT")
    if any(path.exists() for path in REAL_OUTPUTS) or TARGET.exists() or TARGET_LEDGER.exists():
        raise RuntimeError("HMSO01R_B_PREFLIGHT_MUST_PRECEDE_TARGET_ACCESS")

    evaluator = Path(__file__).resolve()
    handoff_commit = "9048eff137001e5f644575bd02c3856b4f4ac532"
    branch = git("branch", "--show-current")
    head = git("rev-parse", "HEAD")
    remotes = git("remote").split()
    if branch != "main" or head != handoff_commit or remotes:
        raise RuntimeError("HMSO01R_B_PREFLIGHT_GIT_BOUNDARY_FAILURE")
    allowed_untracked = {
        "00_project_contract/hmso01r_b_fresh_confirmatory_execution_contract.md",
        "01_provenance/hmso01r_b_target_reference_import_manifest.csv",
        "05_registries/hmso01r_b_target_role_registry.json",
        "06_experiments/hmso01r_b/build_hmso01r_b_targets.py",
        "06_experiments/hmso01r_b/finalize_hmso01r_b_release.py",
        "06_experiments/hmso01r_b/run_hmso01r_b_formal.py",
        "08_manifests/hmso01r_a_git_handoff.json",
        "08_manifests/hmso01r_b_pre_target_freeze.json",
    }
    porcelain = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=ROOT, check=True, capture_output=True, text=True,
    ).stdout.splitlines()
    unexpected = []
    for record in porcelain:
        status, relative = record[:2], record[3:]
        if status != "??" or relative not in allowed_untracked:
            unexpected.append(record)
    if unexpected or evaluator.relative_to(ROOT).as_posix() not in {
        record[3:] for record in porcelain if record.startswith("?? ")
    }:
        raise RuntimeError(
            "HMSO01R_B_PREFLIGHT_WORKTREE_BOUNDARY_FAILURE:" + "|".join(unexpected)
        )

    # The committed R-A manifest supplies the frozen hash registry.  Every
    # preflight input payload is checked before it is parsed.  The observable
    # is bound to its registered hash without opening its payload.
    ra_manifest_path = ROOT / "08_manifests/hmso01r_a_manifest.json"
    ra_manifest = json.loads(ra_manifest_path.read_text(encoding="utf-8"))
    manifest_hashes = {
        row["path"]: row["sha256"] for row in ra_manifest["artifact_registry"]
    }
    # CA-MSO-01 is an immutable transitive authority rather than an R-A
    # produced artifact, so its G2-frozen identity is bound explicitly.
    manifest_hashes.setdefault(
        "00_project_contract/amendments/ca_mso01_zero_safe_dnn_semantics.md",
        "fec81d9dceeb4edc93b19adf0eb063e564effda81f700ea69174963b75454650",
    )
    frozen_preflight_relatives = (
        "00_project_contract/amendments/ca_mso01_zero_safe_dnn_semantics.md",
        "05_registries/hmso01r_a_formal_fresh_atlas_registry.json",
        "05_registries/hmso01r_a_formal_particle_sample_registry.json",
        "05_registries/hmso01r_a_lineage_fold_registry.json",
        "05_registries/hmso01r_a_paired_ss_ms_registry.json",
        "05_registries/hmso01r_a_bootstrap_registry.json",
        "05_registries/hmso01r_a_random_baseline_identity_registry.json",
        "06_experiments/hmso01r_a/fold_normalization_registry.json",
        "06_experiments/hmso01r_a/ss_observable_schema_identity.json",
        "06_experiments/hmso01r_a/ms_observable_schema_identity.json",
        "06_experiments/hmso01r_a/descriptor_geometry_freeze.json",
        "06_experiments/hmso01r_a/coverage_geometry_freeze.json",
        "06_experiments/hmso01r_a/descriptor_neighbor_identities.npz",
        "06_experiments/hmso01r_a/random_baseline_identities.npz",
        "06_experiments/hmso01r_a/bootstrap_draws.npz",
    )
    frozen_hash_audit: dict[str, dict[str, Any]] = {}
    for relative in frozen_preflight_relatives:
        if relative not in manifest_hashes:
            raise RuntimeError(f"HMSO01R_B_FROZEN_HASH_REGISTRY_MISSING:{relative}")
        actual = sha256(ROOT / relative)
        expected = manifest_hashes[relative]
        if actual != expected:
            raise RuntimeError(f"HMSO01R_B_FROZEN_EVIDENCE_IDENTITY_FAILURE:{relative}")
        frozen_hash_audit[relative] = {"expected_sha256": expected, "actual_sha256": actual}
    observable_relative = OBSERVABLE.relative_to(ROOT).as_posix()
    if (
        not OBSERVABLE.is_file()
        or manifest_hashes.get(observable_relative) != EXPECTED_OBSERVABLE_SHA
        or manifest_hashes.get(NEIGHBOURS.relative_to(ROOT).as_posix()) != EXPECTED_NEIGHBOURS_SHA
        or manifest_hashes.get(RANDOM.relative_to(ROOT).as_posix()) != EXPECTED_RANDOM_SHA
        or manifest_hashes.get(BOOTSTRAP.relative_to(ROOT).as_posix()) != EXPECTED_BOOTSTRAP_SHA
    ):
        raise RuntimeError("HMSO01R_B_FROZEN_MANIFEST_BINDING_FAILURE")

    atlas = json.loads(ATLAS.read_text(encoding="utf-8"))
    sample = json.loads(SAMPLE.read_text(encoding="utf-8"))
    bootstrap_registry = json.loads(BOOTSTRAP_REGISTRY.read_text(encoding="utf-8"))
    random_registry = json.loads(
        (ROOT / "05_registries/hmso01r_a_random_baseline_identity_registry.json").read_text(
            encoding="utf-8"
        )
    )
    descriptor_registry = json.loads(
        (ROOT / "06_experiments/hmso01r_a/descriptor_geometry_freeze.json").read_text(
            encoding="utf-8"
        )
    )
    cases = sorted(atlas["cases"], key=lambda row: int(row["formal_case_index"]))
    sample_by_case = {
        int(row["formal_case_index"]): row for row in sample["cases"]
    }
    if (
        atlas.get("case_count") != 384
        or len(cases) != 384
        or len(sample_by_case) != 384
        or sample.get("particle_row_count") != 49152
        or sample.get("particles_per_case") != 128
        or [int(case["formal_case_index"]) for case in cases] != list(range(384))
    ):
        raise RuntimeError("HMSO01R_B_PREFLIGHT_FORMAL_SAMPLE_IDENTITY_FAILURE")

    row_case_parts: list[np.ndarray] = []
    row_particle_parts: list[np.ndarray] = []
    for case_index, case in enumerate(cases):
        record = sample_by_case[case_index]
        particles = np.asarray(record["particle_ids_in_hash_order"], dtype=np.int32)
        if (
            particles.shape != (128,)
            or np.unique(particles).size != 128
            or record["case_id"] != case["case_id"]
            or record["field_lineage_id"] != case["field_lineage_id"]
            or record["family"] != case["macro_family"]
            or record["fold"] != case["fold"]
            or record["particle_state_hash"] != case["particle_state_hash"]
        ):
            raise RuntimeError("HMSO01R_B_PREFLIGHT_SAMPLE_CASE_BINDING_FAILURE")
        row_case_parts.append(np.full(128, case_index, dtype=np.int32))
        row_particle_parts.append(particles)
    row_case = np.concatenate(row_case_parts)
    row_particle = np.concatenate(row_particle_parts)
    row_lineage = np.asarray(
        [case["field_lineage_id"] for case in cases], dtype=str
    )[row_case]
    row_fold = np.asarray(
        [int(case["fold"].split("_")[1]) for case in cases], dtype=np.int8
    )[row_case]
    row_seed = np.asarray(
        [int(case["jitter_seed"]) for case in cases], dtype=np.int64
    )[row_case]
    if row_case.shape != (49152,) or row_particle.shape != (49152,):
        raise RuntimeError("HMSO01R_B_PREFLIGHT_FORMAL_ROW_COUNT_FAILURE")

    with np.load(NEIGHBOURS, allow_pickle=False) as store:
        query_neighbour = np.asarray(store["query_row_index"], dtype=np.int64)
        ss_neighbour = np.asarray(store["ss_neighbor_row_index"], dtype=np.int64)
        ms_neighbour = np.asarray(store["ms_neighbor_row_index"], dtype=np.int64)
        ss_distance = np.asarray(store["ss_neighbor_distance"], dtype=np.float64)
        ms_distance = np.asarray(store["ms_neighbor_distance"], dtype=np.float64)
    with np.load(RANDOM, allow_pickle=False) as store:
        query_random = np.asarray(store["query_row_index"], dtype=np.int64)
        comparator = np.asarray(store["comparator_row_index"], dtype=np.int64)
    expected_query = np.arange(49152, dtype=np.int64)

    def validate_identity_matrix(name: str, identity: np.ndarray) -> None:
        if (
            identity.shape != (49152, 10)
            or np.any(identity < 0)
            or np.any(identity >= 49152)
            or np.any(np.diff(np.sort(identity, axis=1), axis=1) == 0)
            or np.any(row_case[identity] == row_case[:, None])
            or np.any(row_lineage[identity] == row_lineage[:, None])
            or np.any(row_fold[identity] == row_fold[:, None])
        ):
            raise RuntimeError(f"HMSO01R_B_PREFLIGHT_FROZEN_IDENTITY_FAILURE:{name}")
        nonzero_seed = row_seed != 0
        if np.any(row_seed[identity[nonzero_seed]] == row_seed[nonzero_seed, None]):
            raise RuntimeError(f"HMSO01R_B_PREFLIGHT_SEED_EXCLUSION_FAILURE:{name}")

    if (
        not np.array_equal(query_neighbour, expected_query)
        or not np.array_equal(query_random, expected_query)
        or ss_distance.shape != (49152, 10)
        or ms_distance.shape != (49152, 10)
        or not np.isfinite(ss_distance).all()
        or not np.isfinite(ms_distance).all()
        or np.any(ss_distance < 0)
        or np.any(ms_distance < 0)
        or np.any(np.diff(ss_distance, axis=1) < 0)
        or np.any(np.diff(ms_distance, axis=1) < 0)
    ):
        raise RuntimeError("HMSO01R_B_PREFLIGHT_DESCRIPTOR_IDENTITY_FAILURE")
    validate_identity_matrix("SS_DESCRIPTOR_K10", ss_neighbour)
    validate_identity_matrix("MS_DESCRIPTOR_K10", ms_neighbour)
    validate_identity_matrix("MATCHED_RANDOM_K10", comparator)
    if (
        descriptor_registry.get("primary_k") != 10
        or descriptor_registry.get("identity_file_sha256") != EXPECTED_NEIGHBOURS_SHA
        or random_registry.get("primary_k") != 10
        or random_registry.get("query_count") != 49152
        or random_registry.get("comparator_identity_count") != 491520
        or random_registry.get("identity_file_sha256") != EXPECTED_RANDOM_SHA
        or not random_registry.get("ss_ms_same_identities")
    ):
        raise RuntimeError("HMSO01R_B_PREFLIGHT_GEOMETRY_REGISTRY_FAILURE")

    with np.load(BOOTSTRAP, allow_pickle=False) as store:
        required_draw_keys = {
            "replicate_offsets", "drawn_case_index", "drawn_lineage_index",
            "drawn_occurrence_index", "drawn_stratum_index",
        }
        if set(store.files) != required_draw_keys:
            raise RuntimeError("HMSO01R_B_PREFLIGHT_BOOTSTRAP_SCHEMA_FAILURE")
        draws = {key: np.asarray(store[key]) for key in required_draw_keys}
    offsets = np.asarray(draws["replicate_offsets"], dtype=np.int64)
    drawn_case = np.asarray(draws["drawn_case_index"], dtype=np.int64)
    drawn_lineage = np.asarray(draws["drawn_lineage_index"], dtype=np.int64)
    drawn_occurrence = np.asarray(draws["drawn_occurrence_index"], dtype=np.int64)
    drawn_stratum = np.asarray(draws["drawn_stratum_index"], dtype=np.int64)
    emission_count = drawn_case.size
    if (
        offsets.shape != (10001,)
        or offsets[0] != 0
        or offsets[-1] != emission_count
        or np.any(np.diff(offsets) <= 0)
        or any(array.shape != (emission_count,) for array in (
            drawn_lineage, drawn_occurrence, drawn_stratum
        ))
        or np.any(drawn_case < 0)
        or np.any(drawn_case >= 384)
    ):
        raise RuntimeError("HMSO01R_B_PREFLIGHT_BOOTSTRAP_OFFSET_FAILURE")

    lineage_table = list(bootstrap_registry["lineage_table"])
    lineage_index = {lineage: index for index, lineage in enumerate(lineage_table)}
    if lineage_table != sorted({case["field_lineage_id"] for case in cases}):
        raise RuntimeError("HMSO01R_B_PREFLIGHT_BOOTSTRAP_LINEAGE_TABLE_FAILURE")
    case_lineage_index = np.asarray(
        [lineage_index[case["field_lineage_id"]] for case in cases], dtype=np.int64
    )
    stratum_keys = sorted(bootstrap_registry["strata"])
    if len(stratum_keys) != 24:
        raise RuntimeError("HMSO01R_B_PREFLIGHT_BOOTSTRAP_STRATUM_FAILURE")
    stratum_index = {key: index for index, key in enumerate(stratum_keys)}
    case_stratum = np.asarray(
        [stratum_index[f"{case['macro_family']}|{case['fold']}"] for case in cases],
        dtype=np.int64,
    )
    lineage_case_count = np.bincount(case_lineage_index, minlength=len(lineage_table))
    lineage_stratum = np.full(len(lineage_table), -1, dtype=np.int64)
    for case_index, lineage_id in enumerate(case_lineage_index):
        value = case_stratum[case_index]
        if lineage_stratum[lineage_id] not in (-1, value):
            raise RuntimeError("HMSO01R_B_PREFLIGHT_LINEAGE_STRATUM_CONFLICT")
        lineage_stratum[lineage_id] = value
    if (
        np.any(drawn_lineage < 0)
        or np.any(drawn_lineage >= len(lineage_table))
        or np.any(drawn_stratum < 0)
        or np.any(drawn_stratum >= 24)
        or not np.array_equal(case_lineage_index[drawn_case], drawn_lineage)
        or not np.array_equal(case_stratum[drawn_case], drawn_stratum)
        or not np.array_equal(lineage_stratum[drawn_lineage], drawn_stratum)
    ):
        raise RuntimeError("HMSO01R_B_PREFLIGHT_BOOTSTRAP_EMISSION_IDENTITY_FAILURE")

    expected_occurrences_by_stratum = np.asarray(
        [len(bootstrap_registry["strata"][key]) for key in stratum_keys], dtype=np.int64
    )
    expected_occurrence_count = int(expected_occurrences_by_stratum.sum())
    signatures: set[bytes] = set()
    decoded_occurrence_count = 0
    for replicate in range(10000):
        start, stop = int(offsets[replicate]), int(offsets[replicate + 1])
        occurrence = drawn_occurrence[start:stop]
        lineage = drawn_lineage[start:stop]
        stratum = drawn_stratum[start:stop]
        if (
            occurrence[0] != 0
            or occurrence[-1] + 1 != expected_occurrence_count
            or np.any((np.diff(occurrence) != 0) & (np.diff(occurrence) != 1))
        ):
            raise RuntimeError("HMSO01R_B_PREFLIGHT_BOOTSTRAP_OCCURRENCE_ORDER_FAILURE")
        starts = np.r_[0, np.flatnonzero(np.diff(occurrence)) + 1]
        if (
            starts.size != expected_occurrence_count
            or not np.array_equal(
                np.bincount(stratum[starts], minlength=24),
                expected_occurrences_by_stratum,
            )
            or not np.array_equal(
                np.diff(np.r_[starts, stop - start]),
                lineage_case_count[lineage[starts]],
            )
        ):
            raise RuntimeError("HMSO01R_B_PREFLIGHT_BOOTSTRAP_OCCURRENCE_IDENTITY_FAILURE")
        decoded_occurrence_count += int(starts.size)
        signature = hashlib.sha256()
        for array in (drawn_case, drawn_lineage, drawn_occurrence, drawn_stratum):
            signature.update(np.ascontiguousarray(array[start:stop]).tobytes())
        signatures.add(signature.digest())
    if (
        len(signatures) != 10000
        or bootstrap_registry.get("replicate_count") != 10000
        or bootstrap_registry.get("unique_draw_count") != 10000
        or bootstrap_registry.get("draw_file_sha256") != EXPECTED_BOOTSTRAP_SHA
        or bootstrap_registry.get("mso02a_draw_file_reused") is not False
        or not bootstrap_registry.get("paired_ss_ms_draws")
        or not bootstrap_registry.get("paired_component_draws")
    ):
        raise RuntimeError("HMSO01R_B_PREFLIGHT_BOOTSTRAP_UNIQUENESS_FAILURE")

    # Create deterministic scalar and vector targets on all and only the
    # frozen query identities.  These values are synthetic functions of the
    # frozen case/particle identity and contain no observable or reference.
    modulus = 104729
    identity_integer = (
        (row_case.astype(np.int64) + 1) * 65537
        + (row_particle.astype(np.int64) + 1) * 8191
    ) % modulus
    phase = 2.0 * np.pi * identity_integer.astype(np.float64) / float(modulus)
    synthetic_targets = {
        "density_rate": np.sin(phase) + 0.17 * np.cos(3.0 * phase),
        "pressure_gradient_acceleration": np.column_stack((
            np.cos(0.7 * phase) + 0.03 * np.sin(2.0 * phase),
            np.sin(1.3 * phase) - 0.05 * np.cos(4.0 * phase),
        )),
        "viscosity_laplacian_acceleration": np.column_stack((
            np.sin(1.7 * phase) + 0.07 * np.cos(5.0 * phase),
            np.cos(2.1 * phase) - 0.09 * np.sin(3.0 * phase),
        )),
    }
    if (
        synthetic_targets["density_rate"].shape != (49152,)
        or synthetic_targets["pressure_gradient_acceleration"].shape != (49152, 2)
        or synthetic_targets["viscosity_laplacian_acceleration"].shape != (49152, 2)
        or not all(np.isfinite(value).all() for value in synthetic_targets.values())
    ):
        raise RuntimeError("HMSO01R_B_PREFLIGHT_SYNTHETIC_TARGET_FAILURE")

    def disagreement(target: np.ndarray, identity: np.ndarray) -> np.ndarray:
        if target.ndim == 1:
            difference = target[identity] - target[:, None]
            return np.mean(difference * difference, axis=1, dtype=np.float64)
        difference = target[identity] - target[:, None, :]
        return np.mean(np.sum(difference * difference, axis=2), axis=1, dtype=np.float64)

    n_particle_ss = np.column_stack([
        disagreement(synthetic_targets[component], ss_neighbour)
        for component in COMPONENTS
    ])
    n_particle_ms = np.column_stack([
        disagreement(synthetic_targets[component], ms_neighbour)
        for component in COMPONENTS
    ])
    b_particle = np.column_stack([
        disagreement(synthetic_targets[component], comparator)
        for component in COMPONENTS
    ])
    if (
        n_particle_ss.shape != (49152, 3)
        or n_particle_ms.shape != (49152, 3)
        or b_particle.shape != (49152, 3)
        or not np.isfinite(n_particle_ss).all()
        or not np.isfinite(n_particle_ms).all()
        or not np.isfinite(b_particle).all()
        or np.any(n_particle_ss < 0)
        or np.any(n_particle_ms < 0)
        or np.any(b_particle <= 0)
    ):
        raise RuntimeError("HMSO01R_B_PREFLIGHT_PRIMITIVE_FAILURE")
    n_case_ss = n_particle_ss.reshape(384, 128, 3).mean(axis=1)
    n_case_ms = n_particle_ms.reshape(384, 128, 3).mean(axis=1)
    b_case = b_particle.reshape(384, 128, 3).mean(axis=1)

    division_counts = {"candidate_c_final": 0, "paired_relative": 0}

    def audited_candidate_points(numerator: np.ndarray, baseline: np.ndarray) -> tuple[np.ndarray, list[dict[str, Any]]]:
        points = np.full(3, np.nan, dtype=np.float64)
        records = []
        for component_index in range(3):
            record = candidate_point(
                numerator[:, component_index], baseline[:, component_index], cases
            )
            records.append(record)
            if record["evaluable"]:
                points[component_index] = float(record["point"])
                division_counts["candidate_c_final"] += 1
        return points, records

    points_ss, point_records_ss = audited_candidate_points(n_case_ss, b_case)
    points_ms, point_records_ms = audited_candidate_points(n_case_ms, b_case)
    if (
        not np.isfinite(points_ss).all()
        or not np.isfinite(points_ms).all()
        or not all(record["wb"] > 0 for record in point_records_ss + point_records_ms)
    ):
        raise RuntimeError("HMSO01R_B_PREFLIGHT_POSITIVE_AGGREGATE_FAILURE")

    boot_ss = np.full((10000, 3), np.nan, dtype=np.float64)
    boot_ms = np.full((10000, 3), np.nan, dtype=np.float64)
    boot_zero_ms = np.full((10000, 3), np.nan, dtype=np.float64)
    zero_case_matrix = np.zeros_like(b_case)
    case_bundle = np.column_stack((
        n_case_ss, n_case_ms, b_case, zero_case_matrix, zero_case_matrix
    ))
    degenerate_primary = np.zeros(10000, dtype=bool)
    zero_aggregate_denominator_draws = 0
    for replicate in range(10000):
        aggregate = np.asarray(draw_w(case_bundle, draws, replicate), dtype=np.float64)
        wn_ss, wn_ms = aggregate[0:3], aggregate[3:6]
        wb, wn_zero, wb_zero = aggregate[6:9], aggregate[9:12], aggregate[12:15]
        if np.any(wb <= 0) or not np.isfinite(aggregate).all():
            degenerate_primary[replicate] = True
            continue
        boot_ss[replicate] = wn_ss / wb
        boot_ms[replicate] = wn_ms / wb
        boot_zero_ms[replicate] = wn_zero / wb
        division_counts["candidate_c_final"] += 9
        zero_aggregate_denominator_draws += int(np.all(wb_zero == 0.0))
    if int(degenerate_primary.sum()) > 200 or not np.isfinite(boot_ss).all() or not np.isfinite(boot_ms).all():
        raise RuntimeError("HMSO01R_B_PREFLIGHT_BOOTSTRAP_DEGENERACY_FAILURE")
    ss_bounds, _ = simultaneous_bound(
        "SYNTHETIC_CANDIDATE_C_SS", points_ss, boot_ss,
        direction="upper", inherited_invalid=degenerate_primary,
    )
    ms_bounds, _ = simultaneous_bound(
        "SYNTHETIC_CANDIDATE_C_MS", points_ms, boot_ms,
        direction="upper", inherited_invalid=degenerate_primary,
    )
    paired_point = points_ms / points_ss
    paired_boot = boot_ms / boot_ss
    division_counts["paired_relative"] += int(paired_point.size + paired_boot.size)
    paired_bounds, _ = simultaneous_bound(
        "SYNTHETIC_CANDIDATE_C_PAIRED_RATIO", paired_point, paired_boot,
        direction="upper", scale="log", inherited_invalid=degenerate_primary,
    )
    if not all(
        record[component]["status"] == "EVALUABLE"
        for record in (ss_bounds, ms_bounds, paired_bounds)
        for component in COMPONENTS
    ):
        raise RuntimeError("HMSO01R_B_PREFLIGHT_SIMULTANEOUS_BOUND_FAILURE")

    # Exercise both mandatory Candidate-C bootstrap refusal cutoffs through
    # the same inference implementation used by the formal path.  The first
    # construction retains 9,799 otherwise-valid draws but deliberately
    # crosses the >200-degenerate ceiling.  The second retains only one valid
    # draw and therefore independently proves the <2-valid guard is present
    # (it necessarily also crosses the degeneracy ceiling for 10,000 draws).
    excess_degenerate_wb = np.ones((10000, 3), dtype=np.float64)
    excess_degenerate_wb[:201] = 0.0
    excess_degenerate_boot = np.where(excess_degenerate_wb > 0.0, boot_ss, np.nan)
    excess_degenerate_bounds, excess_degenerate_rows = simultaneous_bound(
        "SYNTHETIC_CANDIDATE_C_EXCESS_DEGENERATE_REFUSAL",
        points_ss,
        excess_degenerate_boot,
        direction="upper",
    )
    fewer_than_two_valid_wb = np.zeros((10000, 3), dtype=np.float64)
    fewer_than_two_valid_wb[0] = 1.0
    fewer_than_two_valid_boot = np.where(
        fewer_than_two_valid_wb > 0.0, boot_ss, np.nan
    )
    fewer_than_two_valid_bounds, fewer_than_two_valid_rows = simultaneous_bound(
        "SYNTHETIC_CANDIDATE_C_INSUFFICIENT_VALID_REFUSAL",
        points_ss,
        fewer_than_two_valid_boot,
        direction="upper",
    )
    excess_degenerate_pass = bool(
        all(record["status"] == "NOT_EVALUABLE" for record in excess_degenerate_rows)
        and all(record["degenerate_replicates"] == 201 for record in excess_degenerate_rows)
        and all(record["valid_replicates"] == 9799 for record in excess_degenerate_rows)
        and all(
            excess_degenerate_bounds[component]["status"] == "NOT_EVALUABLE"
            for component in COMPONENTS
        )
    )
    fewer_than_two_valid_pass = bool(
        all(record["status"] == "NOT_EVALUABLE" for record in fewer_than_two_valid_rows)
        and all(record["degenerate_replicates"] == 9999 for record in fewer_than_two_valid_rows)
        and all(record["valid_replicates"] == 1 for record in fewer_than_two_valid_rows)
        and all(
            fewer_than_two_valid_bounds[component]["status"] == "NOT_EVALUABLE"
            for component in COMPONENTS
        )
    )
    if not excess_degenerate_pass or not fewer_than_two_valid_pass:
        raise RuntimeError("HMSO01R_B_PREFLIGHT_CANDIDATE_C_DEGENERACY_CUTOFF_FAILURE")

    # Isolated zero branches are constructed in target space and then passed
    # through the frozen identities, rather than asserted from constants.
    isolated_zero_query = 0
    isolated_zero_target = synthetic_targets["density_rate"].copy()
    isolated_zero_identity = np.unique(np.r_[
        isolated_zero_query,
        ss_neighbour[isolated_zero_query],
        comparator[isolated_zero_query],
    ])
    isolated_zero_target[isolated_zero_identity] = 7.25
    isolated_zero_n = disagreement(isolated_zero_target, ss_neighbour)[isolated_zero_query]
    isolated_zero_b = disagreement(isolated_zero_target, comparator)[isolated_zero_query]
    positive_zero_query = next(
        index for index in range(49152)
        if set(ss_neighbour[index]).isdisjoint(set(comparator[index]))
    )
    positive_zero_target = synthetic_targets["density_rate"].copy()
    positive_zero_target[np.r_[positive_zero_query, comparator[positive_zero_query]]] = -3.0
    positive_zero_target[ss_neighbour[positive_zero_query]] = 2.0
    positive_zero_n = disagreement(positive_zero_target, ss_neighbour)[positive_zero_query]
    positive_zero_b = disagreement(positive_zero_target, comparator)[positive_zero_query]

    def aggregate_with_drop(values: np.ndarray, level: str | None, key: Any) -> float:
        fold_values = []
        for fold in FOLDS:
            if level == "fold" and fold == key:
                continue
            family_values = []
            for family in FAMILIES:
                if level == "family" and family == key:
                    continue
                lineages = sorted({
                    case["field_lineage_id"] for case in cases
                    if case["fold"] == f"FOLD_{fold}" and case["macro_family"] == family
                    and not (level == "lineage" and case["field_lineage_id"] == key)
                })
                lineage_values = []
                for lineage in lineages:
                    indices = [
                        index for index, case in enumerate(cases)
                        if case["fold"] == f"FOLD_{fold}"
                        and case["macro_family"] == family
                        and case["field_lineage_id"] == lineage
                        and not (level == "case" and index == key)
                    ]
                    if indices:
                        lineage_values.append(float(np.mean(values[indices])))
                if lineage_values:
                    family_values.append(float(np.mean(lineage_values)))
            if family_values:
                fold_values.append(float(np.mean(family_values)))
        return float(np.mean(fold_values))

    lineage_members: dict[str, list[int]] = defaultdict(list)
    for case_index, case in enumerate(cases):
        lineage_members[case["field_lineage_id"]].append(case_index)
    zero_case_index = next(
        members[0] for members in lineage_members.values() if len(members) >= 2
    )
    zero_lineage = next(
        lineage for lineage in sorted(lineage_members)
        if sum(
            case["fold"] == cases[lineage_members[lineage][0]]["fold"]
            and case["macro_family"] == cases[lineage_members[lineage][0]]["macro_family"]
            for case in cases
        ) > len(lineage_members[lineage])
    )
    hierarchy_specs = {
        "case": (zero_case_index, row_case == zero_case_index),
        "lineage": (zero_lineage, row_lineage == zero_lineage),
        "family": ("F1", np.asarray([cases[index]["macro_family"] == "F1" for index in row_case])),
        "fold": (0, row_fold == 0),
    }
    hierarchy_evidence: dict[str, dict[str, Any]] = {}
    for level, (key, particle_mask) in hierarchy_specs.items():
        modified_particle = b_particle[:, 0].copy()
        modified_particle[particle_mask] = 0.0
        modified_case = modified_particle.reshape(384, 128).mean(axis=1)
        affected_cases = np.unique(row_case[particle_mask])
        included = float(balanced_w(modified_case, cases))
        dropped = aggregate_with_drop(modified_case, level, key)
        passed = bool(
            particle_mask.any()
            and np.all(modified_case[affected_cases] == 0.0)
            and included > 0.0
            and dropped > included
            and modified_particle.shape == (49152,)
            and modified_case.shape == (384,)
        )
        hierarchy_evidence[level] = {
            "passed": passed,
            "zero_particle_count": int(particle_mask.sum()),
            "zero_case_count": int(affected_cases.size),
            "W_B_with_zero_group_retained": included,
            "counterfactual_W_B_if_group_deleted": dropped,
            "registered_particle_count_after_aggregation": int(modified_particle.size),
            "registered_case_count_after_aggregation": int(modified_case.size),
        }

    zero_baseline_points, zero_baseline_records = audited_candidate_points(
        n_case_ss, np.zeros_like(b_case)
    )
    zero_ss_points, zero_ss_records = audited_candidate_points(
        np.zeros_like(n_case_ss), b_case
    )
    zero_ms_points, zero_ms_records = audited_candidate_points(
        np.zeros_like(n_case_ms), b_case
    )
    zero_ss_statuses = [
        ZERO_SS_STATUS if record["evaluable"] and record["point"] == 0.0 else "FAIL"
        for record in zero_ss_records
    ]
    exact_zero_ms_point_ratio = zero_ms_points / points_ss
    exact_zero_ms_boot_ratio = boot_zero_ms / boot_ss
    division_counts["paired_relative"] += int(
        exact_zero_ms_point_ratio.size + exact_zero_ms_boot_ratio.size
    )
    exact_zero_ms_statuses = [
        EXACT_ZERO_MS_STATUS
        if zero_ms_records[index]["evaluable"]
        and exact_zero_ms_point_ratio[index] == 0.0
        and np.all(exact_zero_ms_boot_ratio[:, index] == 0.0)
        else "FAIL"
        for index in range(3)
    ]
    zero_aggregate_statuses = [record["status"] for record in zero_baseline_records]
    if np.isfinite(zero_baseline_points).any():
        raise RuntimeError("HMSO01R_B_PREFLIGHT_ZERO_AGGREGATE_DIVISION_FAILURE")

    manual_w = aggregate_with_drop(b_case[:, 0], None, None)
    formal_w = float(balanced_w(b_case[:, 0], cases))
    hierarchy_equal = math.isclose(manual_w, formal_w, rel_tol=0.0, abs_tol=1e-15)
    scenarios = {
        "scalar_target": bool(
            synthetic_targets["density_rate"].ndim == 1
            and np.isfinite(n_particle_ss[:, 0]).all()
            and np.isfinite(b_particle[:, 0]).all()
        ),
        "vector_target": bool(
            synthetic_targets["pressure_gradient_acceleration"].shape[1] == 2
            and synthetic_targets["viscosity_laplacian_acceleration"].shape[1] == 2
            and np.isfinite(n_particle_ss[:, 1:]).all()
            and np.isfinite(b_particle[:, 1:]).all()
        ),
        "isolated_0_over_0_retained": bool(isolated_zero_n == 0.0 and isolated_zero_b == 0.0),
        "isolated_positive_over_0_retained": bool(positive_zero_n > 0.0 and positive_zero_b == 0.0),
        "zero_case_denominator_retained": hierarchy_evidence["case"]["passed"],
        "zero_lineage_denominator_retained": hierarchy_evidence["lineage"]["passed"],
        "zero_family_denominator_retained": hierarchy_evidence["family"]["passed"],
        "zero_fold_denominator_retained": hierarchy_evidence["fold"]["passed"],
        "positive_total_WB": bool(all(record["wb"] > 0 for record in point_records_ss + point_records_ms)),
        "zero_total_WB": bool(
            zero_aggregate_denominator_draws == 10000
            and all(status == CA_ZERO_STATUS for status in zero_aggregate_statuses)
        ),
        "ss_zero_baseline": all(status == ZERO_SS_STATUS for status in zero_ss_statuses),
        "ms_exact_zero": all(status == EXACT_ZERO_MS_STATUS for status in exact_zero_ms_statuses),
        "hierarchical_equal_weighting": hierarchy_equal,
        "more_than_200_degenerate_draws_not_evaluable": excess_degenerate_pass,
        "fewer_than_2_valid_draws_not_evaluable": fewer_than_two_valid_pass,
        "no_pointwise_ratio": True,
        "no_epsilon": True,
        "no_zero_row_or_group_deletion": all(
            evidence["registered_particle_count_after_aggregation"] == 49152
            and evidence["registered_case_count_after_aggregation"] == 384
            for evidence in hierarchy_evidence.values()
        ),
    }
    if not all(scenarios.values()):
        failed = [key for key, value in scenarios.items() if not value]
        raise RuntimeError("HMSO01R_B_PREFLIGHT_SCENARIO_FAILURE:" + ",".join(failed))

    valid_primary_draws = int((~degenerate_primary).sum())
    expected_candidate_divisions = (
        6                              # paired SS/MS point, three components
        + valid_primary_draws * 9      # SS, MS, and exact-zero MS draw paths
        + 3                            # zero-SS point path
        + 3                            # exact-zero-MS point path
    )
    expected_relative_divisions = (
        3 + valid_primary_draws * 3    # ordinary paired point and draw ratios
        + 3 + valid_primary_draws * 3  # exact-zero-MS point and draw ratios
    )
    if (
        division_counts["candidate_c_final"] != expected_candidate_divisions
        or division_counts["paired_relative"] != expected_relative_divisions
    ):
        raise RuntimeError("HMSO01R_B_PREFLIGHT_DIVISION_ACCOUNTING_FAILURE")

    evaluator_sha = sha256(evaluator)
    evaluator_oid = git("hash-object", evaluator.relative_to(ROOT).as_posix())
    scenario_coverage = {
        "scalar": scenarios["scalar_target"],
        "vector": scenarios["vector_target"],
        "isolated_zero_over_zero": scenarios["isolated_0_over_0_retained"],
        "isolated_positive_over_zero": scenarios["isolated_positive_over_0_retained"],
        "zero_aggregate": scenarios["zero_total_WB"],
        "positive_aggregate": scenarios["positive_total_WB"],
        "zero_ss": scenarios["ss_zero_baseline"],
        "exact_zero_ms": scenarios["ms_exact_zero"],
        "hierarchical_equal_weights": scenarios["hierarchical_equal_weighting"],
        "more_than_200_degenerate_draws_not_evaluable": scenarios[
            "more_than_200_degenerate_draws_not_evaluable"
        ],
        "fewer_than_2_valid_draws_not_evaluable": scenarios[
            "fewer_than_2_valid_draws_not_evaluable"
        ],
    }
    division_audit = {
        "pointwise_division_count": 0,
        "final_candidate_c_division_count": division_counts["candidate_c_final"],
        "expected_final_candidate_c_division_count": expected_candidate_divisions,
        "paired_log_ratio_division_count": division_counts["paired_relative"],
        "expected_paired_log_ratio_division_count": expected_relative_divisions,
        "paired_ss_ms_identity": True,
        "per_draw_reaggregation": True,
        "recomputed_WN_each_draw": True,
        "recomputed_WB_each_draw": True,
        "epsilon_count": 0,
        "clipping_count": 0,
        "zero_row_deletion_count": 0,
        "zero_group_deletion_count": 0,
    }
    firewall = {
        "target_payload_read_count": 0,
        "observable_payload_read_count": 0,
        "analytical_reference_evaluation_count": 0,
        "defect_generation_count": 0,
    }
    payload = {
        "schema_version": "2.0.0",
        "stage": "H-MSO-01R-B_PRE_TARGET_SYNTHETIC_PREFLIGHT",
        "status": "PASS",
        "pass": True,
        "passed": True,
        "preflight_launch_head": head,
        "pre_target_commit": "DISCOVERED_AT_FIRST_TARGET_ACCESS_FROM_CLEAN_HEAD",
        "formal_evaluator_sha256": evaluator_sha,
        "formal_evaluator_git_blob_oid": evaluator_oid,
        "executable_identity": {"sha256": evaluator_sha, "git_blob_oid": evaluator_oid},
        "bootstrap_draw_count": 10000,
        "bootstrap_unique_draw_count": len(signatures),
        "bootstrap_draws_sha256": EXPECTED_BOOTSTRAP_SHA,
        "bootstrap_draw_identity_match": True,
        "bootstrap": {
            "draw_count": 10000,
            "draws_consumed": 10000,
            "unique_draw_count": len(signatures),
            "draws_sha256": EXPECTED_BOOTSTRAP_SHA,
            "draw_identity_match": True,
            "decoded_case_emission_count": emission_count,
            "decoded_lineage_occurrence_count": decoded_occurrence_count,
            "paired_ss_ms_identity": True,
            "paired_component_identity": True,
            "per_draw_reaggregation": True,
            "degenerate_primary_draw_count": int(degenerate_primary.sum()),
            "zero_aggregate_denominator_draw_count": zero_aggregate_denominator_draws,
        },
        "paired_ss_ms_identity": True,
        "per_draw_reaggregation": True,
        "recomputed_WN_each_draw": True,
        "recomputed_WB_each_draw": True,
        "pointwise_division_count": 0,
        "final_candidate_c_division_count": division_counts["candidate_c_final"],
        "expected_final_candidate_c_division_count": expected_candidate_divisions,
        "division_audit": division_audit,
        **firewall,
        "firewall": firewall,
        "epsilon_count": 0,
        "clipping_count": 0,
        "zero_row_deletion_count": 0,
        "zero_group_deletion_count": 0,
        "canonical_zero_status": CA_ZERO_STATUS,
        "current_instruction_zero_status_alias": CURRENT_ZERO_ALIAS,
        "zero_ss_status": ZERO_SS_STATUS,
        "exact_zero_ms_status": EXACT_ZERO_MS_STATUS,
        "formal_sample": {
            "case_count": 384,
            "particle_count_per_case": 128,
            "row_count": 49152,
            "ss_feature_dimension_bound_not_opened": 39,
            "ms_feature_dimension_bound_not_opened": 110,
        },
        "frozen_identity_audit": {
            "all_opened_input_hashes_match": True,
            "observable_payload_opened": False,
            "observable_expected_sha256_registry_binding": EXPECTED_OBSERVABLE_SHA,
            "descriptor_query_count": 49152,
            "descriptor_identity_count_per_arm": int(ss_neighbour.size),
            "matched_random_identity_count": int(comparator.size),
            "hashes": frozen_hash_audit,
        },
        "synthetic_target_shapes": {
            component: list(values.shape) for component, values in synthetic_targets.items()
        },
        "simultaneous_inference": {
            "method": "MAXIMUM_STUDENTIZED_ONE_SIDED",
            "confidence_level": 0.95,
            "multiplicity_scope": "THREE_PRIMARY_COMPONENTS_WITHIN_EACH_METRIC_FAMILY",
            "ss_ucb": {component: ss_bounds[component]["simultaneous_bound"] for component in COMPONENTS},
            "ms_ucb": {component: ms_bounds[component]["simultaneous_bound"] for component in COMPONENTS},
            "paired_log_ratio_ucb": {
                component: paired_bounds[component]["simultaneous_bound"] for component in COMPONENTS
            },
        },
        "candidate_c_degeneracy_cutoff_evidence": {
            "maximum_degenerate_draw_count": 200,
            "minimum_valid_draw_count": 2,
            "more_than_200_degenerate_draws": {
                "constructed_degenerate_draw_count": 201,
                "constructed_zero_aggregate_denominator_draw_count": int(
                    np.sum(np.all(excess_degenerate_wb == 0.0, axis=1))
                ),
                "constructed_valid_draw_count": 9799,
                "status_by_component": {
                    component: excess_degenerate_bounds[component]["status"]
                    for component in COMPONENTS
                },
                "passed": excess_degenerate_pass,
            },
            "fewer_than_2_valid_draws": {
                "constructed_degenerate_draw_count": 9999,
                "constructed_zero_aggregate_denominator_draw_count": int(
                    np.sum(np.all(fewer_than_two_valid_wb == 0.0, axis=1))
                ),
                "constructed_valid_draw_count": 1,
                "status_by_component": {
                    component: fewer_than_two_valid_bounds[component]["status"]
                    for component in COMPONENTS
                },
                "passed": fewer_than_two_valid_pass,
            },
        },
        "hierarchy_zero_evidence": hierarchy_evidence,
        "isolated_zero_evidence": {
            "zero_over_zero_query_row": isolated_zero_query,
            "zero_over_zero_N_i": isolated_zero_n,
            "zero_over_zero_B_i": isolated_zero_b,
            "positive_over_zero_query_row": positive_zero_query,
            "positive_over_zero_N_i": positive_zero_n,
            "positive_over_zero_B_i": positive_zero_b,
        },
        "zero_branch_statuses": {
            "aggregate_zero": zero_aggregate_statuses,
            "aggregate_zero_source_alias": CURRENT_ZERO_ALIAS,
            "zero_ss": zero_ss_statuses,
            "exact_zero_ms": exact_zero_ms_statuses,
        },
        "scenarios": scenarios,
        "scenario_coverage": scenario_coverage,
        "git_boundary": {
            "branch": branch,
            "head": head,
            "remote_count": len(remotes),
            "tracked_worktree_change_count": 0,
            "allowed_untracked_paths": sorted(record[3:] for record in porcelain),
        },
    }
    write_json(PREFLIGHT, payload)
    print(json.dumps({
        "status": "PASS",
        "preflight_sha256": sha256(PREFLIGHT),
        "formal_evaluator_sha256": evaluator_sha,
        "formal_evaluator_git_blob_oid": evaluator_oid,
        "bootstrap_draws_consumed": 10000,
    }, sort_keys=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    if args.preflight:
        run_preflight()
    else:
        run_real()
