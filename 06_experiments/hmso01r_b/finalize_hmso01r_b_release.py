#!/usr/bin/env python3
"""Validate and publish the H-MSO-01R-B report, manifest, and status ledger.

This executable is release-only.  It never generates or opens a target NPZ,
never evaluates a scientific metric, and never repairs an incomplete analysis.
It hashes the target store opaquely and refuses publication unless the frozen
builder/evaluator outputs form a complete, internally consistent evidence set.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import subprocess
from typing import Any, Mapping, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "06_experiments/hmso01r_b"
REPORT = ROOT / "07_reports/hmso01r_b_fresh_confirmatory_identifiability_report.md"
MANIFEST = ROOT / "08_manifests/hmso01r_b_manifest.json"
STATUS = ROOT / "08_manifests/hmso01r_b_status_ledger.json"
FREEZE = ROOT / "08_manifests/hmso01r_b_pre_target_freeze.json"
HANDOFF = ROOT / "08_manifests/hmso01r_a_git_handoff.json"
CONTRACT = ROOT / "00_project_contract/hmso01r_b_fresh_confirmatory_execution_contract.md"
IMPORT_MANIFEST = ROOT / "01_provenance/hmso01r_b_target_reference_import_manifest.csv"
TARGET_ROLE = ROOT / "05_registries/hmso01r_b_target_role_registry.json"
FORMAL_ATLAS = ROOT / "05_registries/hmso01r_a_formal_fresh_atlas_registry.json"
FORMAL_SAMPLE = ROOT / "05_registries/hmso01r_a_formal_particle_sample_registry.json"
TARGET_BUILDER = OUT / "build_hmso01r_b_targets.py"
FORMAL_EVALUATOR = OUT / "run_hmso01r_b_formal.py"
FINALIZER = OUT / "finalize_hmso01r_b_release.py"
NON_DNN_HELPER = ROOT / "06_experiments/mso02b/run_mso02b_formal.py"
PREFLIGHT = OUT / "candidate_c_implementation_preflight.json"
QUALIFICATION = OUT / "target_reference_qualification.csv"
JOIN_AUDIT = OUT / "target_observable_join_audit.csv"
TARGET_LEDGER = OUT / "target_access_ledger.json"
TARGET_STORE = OUT / "target_ref/hmso01r_b_target_store.npz"
DIVISION_AUDIT = OUT / "candidate_c_division_audit.json"
FIREWALL = OUT / "firewall_audit.json"
SUMMARY = OUT / "formal_summary.json"

R_A_FINAL_COMMIT = "9048eff137001e5f644575bd02c3856b4f4ac532"
OBSERVABLE_SHA256 = "65ca1a7fea58248207fc5a22e14855b4a84c392c7ef17cefdf2d396687cc38cd"
CA_ZERO_STATUS = "NO_AGGREGATE_RANDOM_CONTRAST_NOT_EVALUABLE"
CURRENT_ZERO_ALIAS = "DNN_NOT_EVALUABLE_ZERO_AGGREGATE_RANDOM_BASELINE"
ZERO_SS_STATUS = "RELATIVE_RESCUE_NOT_EVALUABLE_ZERO_SS_BASELINE"
EXACT_ZERO_MS_STATUS = "EXACT_ZERO_MS_DOMINANCE"
PRE_TARGET_SENTINEL = "DISCOVERED_AT_FIRST_TARGET_ACCESS_FROM_CLEAN_HEAD"
FINAL_COMMIT_SENTINEL = "RECORDED_BY_FINAL_GIT_COMMIT_AND_USER_HANDOFF"
COMPONENTS = (
    "density_rate",
    "pressure_gradient_acceleration",
    "viscosity_laplacian_acceleration",
)
ARMS = ("SS", "MS")
FAMILIES = ("F1", "F2", "F3", "F4")
FOLDS = tuple(range(6))
DIMENSIONLESS_FLOOR = 128.0 * np.finfo(np.float64).eps
QUALIFICATION_CHECK_ALIASES = {
    "analytical_derivative_reference_consistency": (
        "analytical_derivative_reference_consistency",
        "analytical_reference_consistency",
        "reference_consistency_pass",
        "analytical_derivative_reference_gate_passed",
    ),
    "finite_values": ("finite_values", "finite", "finite_pass"),
    "sign_convention": (
        "sign_convention",
        "sign_convention_pass",
        "target_sign_convention_all_primary_passed",
    ),
    "lambda_1_base_identity": (
        "lambda_1_base_identity",
        "lambda1_base_identity",
        "base_operator_identity_pass",
        "lambda_1_operator_hash_matches",
    ),
    "component_identity": (
        "component_identity",
        "component_identity_pass",
        "target_component_identity",
    ),
    "component_closure": (
        "component_closure",
        "component_closure_pass",
        "component_closure_passed",
    ),
    "target_particle_state_join_identity": (
        "target_particle_state_join_identity",
        "particle_state_join_identity",
        "target_particle_state_join_pass",
    ),
}
PROHIBITED_KEYS = (
    "neural_model_count",
    "attention_count",
    "transformer_count",
    "learned_operator_count",
    "optimizer_count",
    "training_count",
    "time_integration_count",
    "solver_in_loop_count",
    "rollout_count",
    "sealed_test_count",
    "arc_access_count",
    "target_derived_feature_modification_count",
    "target_derived_scale_modification_count",
    "target_derived_fold_modification_count",
    "target_derived_normalization_modification_count",
    "target_derived_metric_modification_count",
    "target_derived_gate_modification_count",
    "target_derived_oracle_modification_count",
    "case_replacement_after_target_access",
)
RUNTIME_ARTIFACTS = (
    "06_experiments/hmso01r_b/candidate_c_implementation_preflight.json",
    "06_experiments/hmso01r_b/target_reference_qualification.csv",
    "06_experiments/hmso01r_b/target_observable_join_audit.csv",
    "06_experiments/hmso01r_b/target_access_ledger.json",
    "06_experiments/hmso01r_b/ss_candidate_c_dnn_metrics.csv",
    "06_experiments/hmso01r_b/ms_candidate_c_dnn_metrics.csv",
    "06_experiments/hmso01r_b/candidate_c_paired_rescue_metrics.csv",
    "06_experiments/hmso01r_b/candidate_c_bootstrap_bounds.csv",
    "06_experiments/hmso01r_b/candidate_c_division_audit.json",
    "06_experiments/hmso01r_b/ss_conditional_variance_metrics.csv",
    "06_experiments/hmso01r_b/ms_conditional_variance_metrics.csv",
    "06_experiments/hmso01r_b/ss_oracle_metrics.csv",
    "06_experiments/hmso01r_b/ms_oracle_metrics.csv",
    "06_experiments/hmso01r_b/coverage_metrics.csv",
    "06_experiments/hmso01r_b/paired_non_dnn_rescue_metrics.csv",
    "06_experiments/hmso01r_b/bootstrap_simultaneous_bounds.csv",
    "06_experiments/hmso01r_b/component_verdicts.csv",
    "06_experiments/hmso01r_b/formal_summary.json",
    "06_experiments/hmso01r_b/firewall_audit.json",
    "06_experiments/hmso01r_b/target_ref/hmso01r_b_target_store.npz",
)
FORBIDDEN_OLD_DNN_ARTIFACTS = (
    "06_experiments/hmso01r_b/ss_dnn_metrics.csv",
    "06_experiments/hmso01r_b/ms_dnn_metrics.csv",
    "06_experiments/hmso01r_b/dnn_median_metrics.csv",
    "06_experiments/hmso01r_b/dnn_p90_metrics.csv",
    "06_experiments/hmso01r_b/pointwise_dnn_ratios.csv",
)
CSV_COMPONENT_ARTIFACTS = (
    "06_experiments/hmso01r_b/ss_candidate_c_dnn_metrics.csv",
    "06_experiments/hmso01r_b/ms_candidate_c_dnn_metrics.csv",
    "06_experiments/hmso01r_b/candidate_c_paired_rescue_metrics.csv",
    "06_experiments/hmso01r_b/candidate_c_bootstrap_bounds.csv",
    "06_experiments/hmso01r_b/ss_conditional_variance_metrics.csv",
    "06_experiments/hmso01r_b/ms_conditional_variance_metrics.csv",
    "06_experiments/hmso01r_b/ss_oracle_metrics.csv",
    "06_experiments/hmso01r_b/ms_oracle_metrics.csv",
    "06_experiments/hmso01r_b/paired_non_dnn_rescue_metrics.csv",
    "06_experiments/hmso01r_b/bootstrap_simultaneous_bounds.csv",
    "06_experiments/hmso01r_b/component_verdicts.csv",
)

NON_DNN_NE_MECHANISMS = {
    "NOT_EVALUABLE_DEVELOPMENT_TARGET_VARIANCE_NONPOSITIVE_OR_NONFINITE",
    "NOT_EVALUABLE_ORACLE_SELECTION_PREDICTION_OR_TARGET_RMS_INVALID",
    "NOT_EVALUABLE_MEAN_BASELINE_NONPOSITIVE_OR_ORACLE_INVALID",
    "NOT_EVALUABLE_COVERAGE_GEOMETRY_INVALID",
    "NOT_EVALUABLE_EXCESS_DEGENERATE_OR_INSUFFICIENT_EFFECTIVE_LINEAGE_BOOTSTRAP",
    "NOT_EVALUABLE_UNSTABLE_RATIO_NO_FROZEN_ABSOLUTE_DIFFERENCE_MARGIN",
}
NON_DNN_BOOTSTRAP_NE = "NOT_EVALUABLE_EXCESS_DEGENERATE_OR_INSUFFICIENT_EFFECTIVE_LINEAGE_BOOTSTRAP"
NON_OVERALL_IMPROVEMENT_STATUS = "NOT_APPLICABLE_NON_OVERALL_SCOPE"
EXPECTED_IMPORT_EDGES = {
    "/Users/xiejinbo/Documents/SPH-DDO-PoC/08_scripts/ddo01d_atlas_builder.py":
        "01_provenance/vendor/ddo_analytical_reference/mso02b_target_reference.py",
    "/Users/xiejinbo/Documents/SPH-DDO-PoC/08_scripts/ddo01a_preflight.py":
        "01_provenance/vendor/ddo_analytical_reference/mso02b_target_reference.py",
    "/Users/xiejinbo/Documents/SPH-DDO-PoC/08_scripts/ddo01ar_requalification.py":
        "01_provenance/vendor/ddo_analytical_reference/mso02b_target_reference.py",
    "/Users/xiejinbo/Documents/SPH-DDO-PoC/01_imported_baseline/structure_preserving/__init__.py":
        "01_provenance/vendor/pio_stage01c_static/structure_preserving/__init__.py",
    "/Users/xiejinbo/Documents/SPH-DDO-PoC/01_imported_baseline/structure_preserving/neighborhood.py":
        "01_provenance/vendor/pio_stage01c_static/structure_preserving/neighborhood.py",
    "/Users/xiejinbo/Documents/SPH-DDO-PoC/01_imported_baseline/structure_preserving/kernels.py":
        "01_provenance/vendor/pio_stage01c_static/structure_preserving/kernels.py",
    "/Users/xiejinbo/Documents/SPH-DDO-PoC/01_imported_baseline/structure_preserving/conservative_pressure.py":
        "01_provenance/vendor/pio_stage01c_static/structure_preserving/conservative_pressure.py",
    "/Users/xiejinbo/Documents/SPH-DDO-PoC/01_imported_baseline/structure_preserving/conservative_viscosity.py":
        "01_provenance/vendor/pio_stage01c_static/structure_preserving/conservative_viscosity.py",
    "06_experiments/mso02b/build_mso02b_targets.py":
        "06_experiments/hmso01r_b/build_hmso01r_b_targets.py",
    "06_experiments/mso02b/run_mso02b_formal.py":
        "06_experiments/hmso01r_b/run_hmso01r_b_formal.py",
    "05_registries/hmso01r_a_formal_fresh_atlas_registry.json":
        "06_experiments/hmso01r_b/target_ref/hmso01r_b_target_store.npz",
    "05_registries/hmso01r_a_formal_particle_sample_registry.json":
        "06_experiments/hmso01r_b/target_ref/hmso01r_b_target_store.npz",
    "06_experiments/hmso01r_a/observable/hmso01r_a_observable_store.npz":
        "06_experiments/hmso01r_b/target_access_ledger.json",
}
EXPECTED_EXTERNAL_SOURCE_PATHS = {
    source for source in EXPECTED_IMPORT_EDGES if source.startswith("/Users/")
}
REQUIRED_FREEZE_PATHS = {
    "00_project_contract/amendments/ca_mso01_zero_safe_dnn_semantics.md",
    "00_project_contract/hmso01r_a_fresh_requalification_atlas_freeze_contract.md",
    "00_project_contract/hmso01r_b_fresh_confirmatory_execution_contract.md",
    "01_provenance/hmso01r_b_target_reference_import_manifest.csv",
    "01_provenance/vendor/ddo_analytical_reference/mso02b_target_reference.py",
    "01_provenance/vendor/pio_stage01c_static/structure_preserving/__init__.py",
    "01_provenance/vendor/pio_stage01c_static/structure_preserving/neighborhood.py",
    "01_provenance/vendor/pio_stage01c_static/structure_preserving/kernels.py",
    "01_provenance/vendor/pio_stage01c_static/structure_preserving/conservative_pressure.py",
    "01_provenance/vendor/pio_stage01c_static/structure_preserving/conservative_viscosity.py",
    "05_registries/hmso01r_a_formal_fresh_atlas_registry.json",
    "05_registries/hmso01r_a_formal_particle_sample_registry.json",
    "05_registries/hmso01r_a_lineage_fold_registry.json",
    "05_registries/hmso01r_a_random_baseline_identity_registry.json",
    "05_registries/hmso01r_a_bootstrap_registry.json",
    "05_registries/hmso01r_b_target_role_registry.json",
    "06_experiments/hmso01r_a/ss_observable_schema_identity.json",
    "06_experiments/hmso01r_a/ms_observable_schema_identity.json",
    "06_experiments/hmso01r_a/fold_normalization_registry.json",
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
}
EXPECTED_FROZEN_SHA256 = {
    "08_manifests/mso00_manifest.json": "c00261aac588f8b1f34e0a606259512ea8d45cf3e9cb0a10f40ab0970a2f7d95",
    "08_manifests/mso01_manifest.json": "bf2fad0dfaf03db02d21db30c4f35a145187df557dcd60b26a4e0ee7f5348306",
    "08_manifests/mso01_status_ledger.json": "425ad0dd0cf4ba62bd802024d7a3b44243f15ad0cc93f122ed1983cf4eb448ef",
    "08_manifests/mso02a_manifest.json": "c8e8770cda1779041b5b380b7ccec387446c9aa0f82c2b50f4a38655ad968e81",
    "08_manifests/mso02a_status_ledger.json": "f59196a1de2adffbc6ba1eda2c737c628ae63a3caeb88e969b98e3fc36cb7212",
    "08_manifests/mso02b_manifest.json": "94ce69002d714acff2176fc71910e18766f873ed26be7437763eb34762e68fe6",
    "08_manifests/mso02b_status_ledger.json": "cb9864b34c94f4ae022745fa9b6040bd2baaf6bdae7156a3905b22584a268815",
    "08_manifests/mso02c_g1_ab_attribution_manifest.json": "e7652d1e706bd4b4e552973d90dfc4fe1b0fb634fd58328a9fc5331e3ae70dac",
    "08_manifests/mso02c_g1_ab_attribution_status_ledger.json": "d076ef93d145a00bddcf278bd593e9d5971d5b3596f7cea3ac018ebe82375fb1",
    "08_manifests/mso02c_g2_manifest.json": "e7d001f714cdaa0bf1a2d45e5148677fed50ee8628eff6bb2caa22eafaba8c95",
    "08_manifests/mso02c_g2_status_ledger.json": "9d677839d3035ca4a16eb414bf13b958b3fcce9af24caa7416043f3b7b251b1d",
    "00_project_contract/amendments/ca_mso01_zero_safe_dnn_semantics.md": "fec81d9dceeb4edc93b19adf0eb063e564effda81f700ea69174963b75454650",
    "00_project_contract/hmso01r_a_fresh_requalification_atlas_freeze_contract.md": "e2aa0c65089121c22af8c408923bdeed1c7eab3bf88c560db8405ccec46607a3",
    "08_manifests/hmso01r_a_manifest.json": "3b182be2bd8a6a2622548ab51f91b363ef9b38b9f3142314f7166516d43776a1",
    "08_manifests/hmso01r_a_status_ledger.json": "d59aaa656da136c9291c8be58b4ae10b9017a9731daebcef96cae06542548bf3",
    "05_registries/hmso01r_a_formal_fresh_atlas_registry.json": "7fd7aa6c8415051ad83f0028b75b4684121886cb3645060e4e5c3ac54ebc268a",
    "05_registries/hmso01r_a_formal_particle_sample_registry.json": "a4b7da1a9f6e4efab7ccbc9ec3bb5e4235a82aef30ce64017895df05ab1c2b01",
    "05_registries/hmso01r_a_lineage_fold_registry.json": "941edc1827e55ca2ffec1125734e0791786e2d157c3aa873ae0a24f520f8815b",
    "06_experiments/hmso01r_a/ss_observable_schema_identity.json": "2bfe3b7f0b1869cade1e9e8d7554eff589c3b017512470b9e8eabf8b18130e70",
    "06_experiments/hmso01r_a/ms_observable_schema_identity.json": "13a6e83f03576619afa335e69df737547947501c63dd691066119fd9d2823fb3",
    "06_experiments/hmso01r_a/fold_normalization_registry.json": "d9842a2ba2b347d0aeb1e950118bf62d3c89d0f80639a5f475cd9c5acb683018",
    "06_experiments/hmso01r_a/descriptor_geometry_freeze.json": "1641f0a68bf59a9f3f949e8ee058971db154d0f68eccf6e23efe6122f4067768",
    "06_experiments/hmso01r_a/descriptor_neighbor_identities.npz": "1d98e7c2038c9d6b7391b1ab953084dfafb47ef3ade7c62815c9f676694408b4",
    "05_registries/hmso01r_a_random_baseline_identity_registry.json": "cc6fa10eb77fbbd7a9b8db00d9214ff971a351fbbefdfee38b0c7db898bace99",
    "06_experiments/hmso01r_a/random_baseline_identities.npz": "74268059f33c5fc9ec885ccb1ef7f61b22120f4eac7e9862bab6fddc844d8b07",
    "05_registries/hmso01r_a_bootstrap_registry.json": "7e1f2686b468cd47eb18ade38e9eb74c389e72e600fc5a89831035925cc278da",
    "06_experiments/hmso01r_a/bootstrap_draws.npz": "3a5853ce6b353c8c2584b0f95651904fb1506a0a3e3af6985981374789d4667e",
    "06_experiments/hmso01r_a/coverage_geometry_freeze.json": "a51fd951bcad7f32a228229176055161b8117e9a266cdd4a99975bea7be447e4",
    "06_experiments/hmso01r_a/observable/hmso01r_a_observable_store.npz": "65ca1a7fea58248207fc5a22e14855b4a84c392c7ef17cefdf2d396687cc38cd",
    "01_provenance/vendor/ddo_analytical_reference/mso02b_target_reference.py": "cd0d8794efa1900f307710e27438939bbff282aa0aa617629eab1f64427bc017",
    "06_experiments/mso02b/build_mso02b_targets.py": "940a671927b20f219a4d2553ab61f36bc568e1c8e29bd9f043edd44103f1a08f",
    "06_experiments/mso02b/run_mso02b_formal.py": "55b0b63eb2c99364c8a2e96c75191a50707e93357f7039bd9edfdcb7c7c831b7",
    "01_provenance/vendor/pio_stage01c_static/structure_preserving/__init__.py": "18afa8e375e06bd03ce68f17528c7a27722e1dbdab17536d1b060994446ad93a",
    "01_provenance/vendor/pio_stage01c_static/structure_preserving/neighborhood.py": "44d61e0abbc9901472dae90f83127f5231fc3f6e8ac92a971228dfdcb230aaa8",
    "01_provenance/vendor/pio_stage01c_static/structure_preserving/kernels.py": "bad08e0f49b308c568cd438c9981abd2c906e16c6570ebc0ca7d19d9847b333b",
    "01_provenance/vendor/pio_stage01c_static/structure_preserving/conservative_pressure.py": "b6366666ba89cc1f367a95390a411905eee8b7f55fba28a024f5732860004064",
    "01_provenance/vendor/pio_stage01c_static/structure_preserving/conservative_viscosity.py": "bdfbcb457f6973130f0131ec3c0a3fecc7197dd117c8256163cf3a1445307852",
}


class ReleaseRefusal(RuntimeError):
    """A named fail-closed H-MSO-01R-B release refusal."""


def refuse(code: str, detail: str = "") -> None:
    suffix = f":{detail}" if detail else ""
    raise ReleaseRefusal(f"{code}{suffix}")


def require(condition: bool, code: str, detail: str = "") -> None:
    if not condition:
        refuse(code, detail)


def sha256(path: Path) -> str:
    require(path.is_file(), "HMSO01R_B_REQUIRED_ARTIFACT_MISSING", str(path))
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def json_load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        refuse("HMSO01R_B_INVALID_JSON_ARTIFACT", f"{path}:{exc}")
    require(isinstance(value, dict), "HMSO01R_B_INVALID_JSON_ROOT", str(path))
    return value


def csv_load(path: Path) -> list[dict[str, str]]:
    try:
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            require(reader.fieldnames is not None, "HMSO01R_B_INVALID_CSV_HEADER", str(path))
            rows = list(reader)
    except (OSError, UnicodeError, csv.Error) as exc:
        refuse("HMSO01R_B_INVALID_CSV_ARTIFACT", f"{path}:{exc}")
    require(rows, "HMSO01R_B_EMPTY_REQUIRED_ARTIFACT", str(path))
    return rows


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(value.rstrip() + "\n", encoding="utf-8")
    temporary.replace(path)


def git(*arguments: str, text: bool = True) -> str | bytes:
    result = subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=text,
    )
    return result.stdout.strip() if text else result.stdout


def git_blob_bytes(commit: str, relative: str) -> bytes:
    result = subprocess.run(
        ["git", "show", f"{commit}:{relative}"],
        cwd=ROOT,
        check=False,
        capture_output=True,
    )
    require(
        result.returncode == 0,
        "HMSO01R_B_PRE_TARGET_GIT_BLOB_MISSING",
        f"{commit}:{relative}",
    )
    return result.stdout


def git_blob_oid(commit: str, relative: str) -> str:
    result = subprocess.run(
        ["git", "rev-parse", f"{commit}:{relative}"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    require(
        result.returncode == 0,
        "HMSO01R_B_PRE_TARGET_GIT_BLOB_MISSING",
        f"{commit}:{relative}",
    )
    return result.stdout.strip()


def as_bool(value: Any, *, field: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "pass", "passed"}:
            return True
        if normalized in {"false", "0", "no", "fail", "failed"}:
            return False
    refuse("HMSO01R_B_INVALID_BOOLEAN", f"{field}={value!r}")


def as_int(value: Any, *, field: str) -> int:
    if isinstance(value, bool):
        refuse("HMSO01R_B_INVALID_INTEGER", f"{field}={value!r}")
    try:
        result = int(value)
    except (TypeError, ValueError):
        refuse("HMSO01R_B_INVALID_INTEGER", f"{field}={value!r}")
    if isinstance(value, float) and not value.is_integer():
        refuse("HMSO01R_B_INVALID_INTEGER", f"{field}={value!r}")
    return result


def as_float(value: Any, *, field: str, allow_none: bool = False) -> float | None:
    if value is None or (isinstance(value, str) and value.strip().upper() in {"", "NA", "N/A", "NOT_EVALUABLE", "NONE", "NULL"}):
        if allow_none:
            return None
        refuse("HMSO01R_B_MISSING_FINITE_VALUE", field)
    try:
        result = float(value)
    except (TypeError, ValueError):
        refuse("HMSO01R_B_INVALID_FLOAT", f"{field}={value!r}")
    require(math.isfinite(result), "HMSO01R_B_NONFINITE_FORMAL_VALUE", field)
    return result


def optional_float(value: Any, *, field: str) -> float | None:
    """Parse a finite formal number, or a serialized non-evaluable value."""

    if value is None:
        return None
    if isinstance(value, str) and value.strip().upper() in {
        "", "NA", "N/A", "NAN", "NOT_EVALUABLE", "NONE", "NULL",
    }:
        return None
    return as_float(value, field=field)


def same_number(left: Any, right: Any, *, field: str) -> bool:
    """Compare independently serialized finite/NE values without loose rounding."""

    left_value = optional_float(left, field=f"{field}.left")
    right_value = optional_float(right, field=f"{field}.right")
    if left_value is None or right_value is None:
        return left_value is right_value
    return math.isclose(left_value, right_value, rel_tol=1e-13, abs_tol=1e-15)


def require_same_number(left: Any, right: Any, *, field: str) -> None:
    require(
        same_number(left, right, field=field),
        "HMSO01R_B_CROSS_ARTIFACT_NUMERIC_MISMATCH",
        field,
    )


def require_exact_keys(mapping: Mapping[str, Any], expected: Sequence[str], *, field: str) -> None:
    require(
        set(mapping) == set(expected),
        "HMSO01R_B_FORMAL_ARTIFACT_KEYSET_FAILURE",
        f"{field}:observed={sorted(mapping)}:expected={sorted(expected)}",
    )


def json_cell(value: Any, *, field: str) -> Any:
    try:
        return json.loads(str(value))
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        refuse("HMSO01R_B_INVALID_JSON_CSV_CELL", f"{field}:{exc}")


def first(mapping: Mapping[str, Any], names: Sequence[str], *, field: str, default: Any = ...) -> Any:
    for name in names:
        if name in mapping:
            return mapping[name]
    if default is not ...:
        return default
    refuse("HMSO01R_B_REQUIRED_FIELD_MISSING", f"{field}:{'|'.join(names)}")


def deep_first(mapping: Mapping[str, Any], paths: Sequence[Sequence[str]], *, field: str, default: Any = ...) -> Any:
    for path in paths:
        current: Any = mapping
        for key in path:
            if not isinstance(current, Mapping) or key not in current:
                break
            current = current[key]
        else:
            return current
    if default is not ...:
        return default
    refuse("HMSO01R_B_REQUIRED_FIELD_MISSING", field)


def component_name(row: Mapping[str, Any]) -> str | None:
    value = first(
        row,
        ("component", "target_component", "quantity", "primary_component"),
        field="component",
        default=None,
    )
    return str(value) if value is not None else None


def ensure_component_coverage(rows: Sequence[Mapping[str, Any]], label: str) -> None:
    observed = {component_name(row) for row in rows}
    missing = set(COMPONENTS) - observed
    require(not missing, "HMSO01R_B_COMPONENT_ROWS_INCOMPLETE", f"{label}:{sorted(missing)}")


def fmt(value: Any) -> str:
    if value is None:
        return "NOT_EVALUABLE"
    if isinstance(value, bool):
        return "PASS" if value else "FAIL"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f"{float(value):.8g}"
    return str(value)


def side_verdict(*, evaluable: bool, passed: bool) -> str:
    """Render a scientific sub-composite without relabelling NE as failure."""

    return "NOT_EVALUABLE" if not evaluable else "PASS" if passed else "FAIL"


def normalize_zero_status(status: Any) -> Any:
    return CA_ZERO_STATUS if status == CURRENT_ZERO_ALIAS else status


def validate_frozen_bootstrap_draws() -> dict[str, Any]:
    path = ROOT / "06_experiments/hmso01r_a/bootstrap_draws.npz"
    require(
        sha256(path) == "3a5853ce6b353c8c2584b0f95651904fb1506a0a3e3af6985981374789d4667e",
        "HMSO01R_B_BOOTSTRAP_IDENTITY_FAILURE",
    )
    try:
        with np.load(path, allow_pickle=False) as store:
            required = {
                "replicate_offsets",
                "drawn_case_index",
                "drawn_lineage_index",
                "drawn_occurrence_index",
                "drawn_stratum_index",
            }
            require(required == set(store.files), "HMSO01R_B_BOOTSTRAP_IDENTITY_FAILURE", "members")
            offsets = np.asarray(store["replicate_offsets"], dtype=np.int64)
            arrays = [
                np.asarray(store[name])
                for name in (
                    "drawn_case_index",
                    "drawn_lineage_index",
                    "drawn_occurrence_index",
                    "drawn_stratum_index",
                )
            ]
    except (OSError, ValueError) as exc:
        refuse("HMSO01R_B_BOOTSTRAP_IDENTITY_FAILURE", str(exc))
    require(
        offsets.shape == (10001,)
        and int(offsets[0]) == 0
        and np.all(np.diff(offsets) > 0)
        and all(array.shape == arrays[0].shape for array in arrays)
        and int(offsets[-1]) == arrays[0].shape[0],
        "HMSO01R_B_BOOTSTRAP_IDENTITY_FAILURE",
        "shape/offsets",
    )
    identities: set[str] = set()
    ordered = hashlib.sha256()
    decoded_lineage_occurrence_count = 0
    for replicate in range(10000):
        start, stop = (int(value) for value in offsets[replicate:replicate + 2])
        drawn_occurrence = arrays[2][start:stop]
        decoded_lineage_occurrence_count += int(np.unique(drawn_occurrence).size)
        digest = hashlib.sha256()
        digest.update(np.asarray([stop - start], dtype="<i8").tobytes())
        for array in arrays:
            digest.update(np.ascontiguousarray(array[start:stop]).tobytes())
        identity = digest.hexdigest()
        identities.add(identity)
        ordered.update(bytes.fromhex(identity))
    require(len(identities) == 10000, "HMSO01R_B_BOOTSTRAP_IDENTITY_FAILURE", "draws not unique")
    return {
        "draw_count": 10000,
        "unique_draw_count": len(identities),
        "ordered_draw_identity_digest": ordered.hexdigest(),
        "decoded_case_emission_count": int(arrays[0].shape[0]),
        "decoded_lineage_occurrence_count": decoded_lineage_occurrence_count,
        "sha256": sha256(path),
    }


def clean_release_workspace_allowed(relative: str) -> bool:
    """Return whether a dirty path is an expected, generated R-B release byte."""

    allowed_exact = set(RUNTIME_ARTIFACTS) | {
        str(REPORT.relative_to(ROOT)),
        str(MANIFEST.relative_to(ROOT)),
        str(STATUS.relative_to(ROOT)),
    }
    return relative in allowed_exact or relative.startswith(
        "06_experiments/hmso01r_b/.release_staging/"
    )


def validate_release_worktree_scope() -> list[str]:
    """Refuse unrelated dirt while permitting only expected runtime outputs.

    Prospective contract/executable bytes are separately required to match the
    pre-target commit blobs.  The only post-freeze dirty paths permitted here
    are the enumerated runtime outputs and the three release outputs.
    """

    output = subprocess.run(
        ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout
    records = [record for record in output.split(b"\0") if record]
    dirty: list[str] = []
    index = 0
    while index < len(records):
        record = records[index]
        require(len(record) >= 4, "HMSO01R_B_RELEASE_GIT_STATUS_PARSE_FAILURE")
        status = record[:2].decode("ascii", errors="strict")
        relative = record[3:].decode("utf-8")
        dirty.append(relative)
        if status[0] in {"R", "C"}:
            index += 1
            require(index < len(records), "HMSO01R_B_RELEASE_GIT_STATUS_PARSE_FAILURE")
            dirty.append(records[index].decode("utf-8"))
        index += 1
    unrelated = [relative for relative in dirty if not clean_release_workspace_allowed(relative)]
    require(not unrelated, "HMSO01R_B_RELEASE_UNRELATED_DIRTY_PATH", ",".join(unrelated))
    return dirty


def validate_external_git_source(record: Mapping[str, Any]) -> None:
    source_path = Path(str(first(record, ("path",), field="external source path")))
    expected_sha = str(first(record, ("sha256",), field=f"external source sha:{source_path}"))
    expected_head = str(first(record, ("git_head", "source_head"), field=f"external source head:{source_path}"))
    expected_oid = str(first(record, ("git_blob_oid",), field=f"external source blob oid:{source_path}"))
    expected_blob_sha = str(first(record, ("git_blob_sha256",), field=f"external source blob sha:{source_path}"))
    require(source_path.is_absolute() and source_path.is_file() and not source_path.is_symlink(), "HMSO01R_B_FROZEN_EXTERNAL_SOURCE_IDENTITY_FAILURE", str(source_path))
    root_text = subprocess.run(
        ["git", "-C", str(source_path.parent), "rev-parse", "--show-toplevel"],
        check=False,
        capture_output=True,
        text=True,
    )
    require(root_text.returncode == 0, "HMSO01R_B_FROZEN_EXTERNAL_SOURCE_GIT_FAILURE", str(source_path))
    source_root = Path(root_text.stdout.strip())
    relative = source_path.relative_to(source_root).as_posix()
    actual_head = subprocess.run(["git", "-C", str(source_root), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
    require(actual_head == expected_head, "HMSO01R_B_FROZEN_EXTERNAL_SOURCE_HEAD_FAILURE", relative)
    blob = subprocess.run(["git", "-C", str(source_root), "show", f"{expected_head}:{relative}"], check=False, capture_output=True)
    require(blob.returncode == 0, "HMSO01R_B_FROZEN_EXTERNAL_SOURCE_GIT_FAILURE", relative)
    actual_blob_sha = hashlib.sha256(blob.stdout).hexdigest()
    actual_oid = subprocess.run(["git", "-C", str(source_root), "rev-parse", f"{expected_head}:{relative}"], check=True, capture_output=True, text=True).stdout.strip()
    require(
        sha256(source_path) == expected_sha == expected_blob_sha == actual_blob_sha
        and expected_oid == actual_oid,
        "HMSO01R_B_FROZEN_EXTERNAL_SOURCE_IDENTITY_FAILURE",
        relative,
    )


def validate_freeze(
    freeze: Mapping[str, Any],
    pre_target_commit: str,
    target_ledger: Mapping[str, Any],
) -> list[str]:
    freeze_relative = str(FREEZE.relative_to(ROOT))
    freeze_file_sha = sha256(FREEZE)
    freeze_blob = git_blob_bytes(pre_target_commit, freeze_relative)
    freeze_blob_sha = hashlib.sha256(freeze_blob).hexdigest()
    ledger_freeze_sha = deep_first(
        target_ledger,
        (("frozen_identity", "pre_target_freeze_sha256"), ("pre_target_freeze_sha256",)),
        field="target ledger pre-target freeze sha256",
    )
    require(
        freeze_file_sha == freeze_blob_sha == ledger_freeze_sha,
        "HMSO01R_B_PRE_TARGET_FREEZE_GIT_LEDGER_IDENTITY_FAILURE",
    )
    freeze_oid = git_blob_oid(pre_target_commit, freeze_relative)
    ledger_freeze_oid = deep_first(
        target_ledger,
        (("git", "pre_target_freeze_git_blob_oid"),),
        field="target ledger pre-target freeze blob oid",
    )
    require(freeze_oid == ledger_freeze_oid, "HMSO01R_B_PRE_TARGET_FREEZE_GIT_OID_FAILURE")
    require(
        freeze.get("status") == "FROZEN_BEFORE_FIRST_FRESH_TARGET_REFERENCE_ACCESS",
        "HMSO01R_B_PRE_TARGET_FREEZE_STATUS_FAILURE",
    )
    binding = first(freeze, ("git_binding",), field="freeze.git_binding")
    require(isinstance(binding, Mapping), "HMSO01R_B_PRE_TARGET_FREEZE_SCHEMA_FAILURE", "git_binding")
    require(
        binding.get("binding_mode")
        == "DISCOVER_PRE_TARGET_COMMIT_AT_FIRST_TARGET_ACCESS_FROM_CLEAN_HEAD",
        "HMSO01R_B_PRE_TARGET_SELF_BINDING_FAILURE",
    )
    require(binding.get("pre_target_commit") == PRE_TARGET_SENTINEL, "HMSO01R_B_PRE_TARGET_SELF_BINDING_FAILURE")
    require(binding.get("parent_head_at_file_creation") == R_A_FINAL_COMMIT, "HMSO01R_B_PARENT_COMMIT_IDENTITY_FAILURE")
    require(binding.get("branch") == "main", "HMSO01R_B_PRE_TARGET_BRANCH_FAILURE")
    require(binding.get("remote") is None, "HMSO01R_B_PRE_TARGET_REMOTE_FAILURE")
    require(binding.get("working_tree_clean_required") is True, "HMSO01R_B_PRE_TARGET_CLEAN_RULE_MISSING")

    handoff = json_load(HANDOFF)
    placeholder = first(handoff, ("placeholder_binding",), field="R-A handoff placeholder_binding")
    require(isinstance(placeholder, Mapping), "HMSO01R_B_R_A_GIT_HANDOFF_FAILURE")
    require(
        placeholder.get("reported_placeholder") == "RECORDED_BY_FINAL_GIT_COMMIT_AND_HANDOFF"
        and placeholder.get("resolved_commit") == R_A_FINAL_COMMIT
        and placeholder.get("prior_artifacts_modified") is False
        and handoff.get("hmso01r_a_final_commit") == R_A_FINAL_COMMIT,
        "HMSO01R_B_R_A_GIT_HANDOFF_FAILURE",
    )
    handoff_git = first(handoff, ("git",), field="R-A handoff git")
    require(
        isinstance(handoff_git, Mapping)
        and handoff_git.get("branch") == "main"
        and handoff_git.get("remote") is None
        and handoff_git.get("working_tree_clean_at_handoff") is True
        and handoff_git.get("push_performed") is False,
        "HMSO01R_B_R_A_GIT_HANDOFF_FAILURE",
        "git boundary",
    )

    audit = first(
        freeze,
        ("pre_target_operator_identity_audit",),
        field="pre_target_operator_identity_audit",
    )
    require(isinstance(audit, Mapping), "HMSO01R_B_OPERATOR_AUDIT_SCHEMA_FAILURE")
    require(as_int(audit.get("formal_case_count"), field="operator_audit.formal_case_count") == 384, "HMSO01R_B_OPERATOR_AUDIT_FAILURE")
    require(as_int(audit.get("matching_case_count"), field="operator_audit.matching_case_count") == 384, "HMSO01R_B_OPERATOR_AUDIT_FAILURE")
    require(
        audit.get("ordered_matrix_hash_digest")
        == "4cf2df0d4b4bcf25ee497e89a12f6edb07bdeae7b195f5ca100bedef79467e40",
        "HMSO01R_B_OPERATOR_AUDIT_DIGEST_FAILURE",
    )
    for key in (
        "analytical_continuum_reference_evaluation_count",
        "defect_generation_count",
        "target_read_count",
        "target_write_count",
        "historical_outcome_read_count",
    ):
        require(as_int(audit.get(key), field=f"operator_audit.{key}") == 0, "HMSO01R_B_OPERATOR_AUDIT_SCOPE_FAILURE", key)
    require(audit.get("classification") == "TARGET_BLIND_BASE_OPERATOR_IDENTITY_AUDIT_NOT_FIRST_TARGET_ACCESS", "HMSO01R_B_OPERATOR_AUDIT_CLASSIFICATION_FAILURE")

    frozen_records: list[Mapping[str, Any]] = []
    for group in ("frozen_inputs", "execution_artifacts"):
        records = first(freeze, (group,), field=f"freeze.{group}")
        require(isinstance(records, list) and records, "HMSO01R_B_PRE_TARGET_FREEZE_SCHEMA_FAILURE", group)
        for record in records:
            require(isinstance(record, Mapping), "HMSO01R_B_PRE_TARGET_FREEZE_SCHEMA_FAILURE", group)
            frozen_records.append(record)

    paths: list[str] = []
    for record in frozen_records:
        relative = str(first(record, ("path",), field="freeze artifact path"))
        pure = PurePosixPath(relative)
        require(
            not pure.is_absolute() and ".." not in pure.parts and pure.as_posix() == relative,
            "HMSO01R_B_INVALID_FROZEN_PATH",
            relative,
        )
        require(
            (ROOT / relative).is_file() and not (ROOT / relative).is_symlink(),
            "HMSO01R_B_FROZEN_INPUT_NOT_REGULAR_FILE",
            relative,
        )
        require(relative not in paths, "HMSO01R_B_DUPLICATE_FROZEN_ARTIFACT", relative)
        paths.append(relative)
        for key in ("sha256", "size_bytes", "git_blob_oid", "git_blob_sha256", "role", "stage", "source", "consumption_status"):
            require(key in record, "HMSO01R_B_PRE_TARGET_FREEZE_SCHEMA_FAILURE", f"{relative}:{key}")
        for key in ("role", "stage", "source", "consumption_status"):
            require(
                isinstance(record[key], str) and bool(str(record[key]).strip()),
                "HMSO01R_B_PRE_TARGET_FREEZE_SCHEMA_FAILURE",
                f"{relative}:{key}:empty",
            )
        require(record["stage"] == "H-MSO-01R-B", "HMSO01R_B_PRE_TARGET_FREEZE_STAGE_FAILURE", relative)
        expected = str(record["sha256"])
        expected_blob_sha = str(record["git_blob_sha256"])
        expected_oid = str(record["git_blob_oid"])
        require(re.fullmatch(r"[0-9a-f]{64}", expected) is not None, "HMSO01R_B_INVALID_FROZEN_SHA256", relative)
        if relative in EXPECTED_FROZEN_SHA256:
            require(
                expected == EXPECTED_FROZEN_SHA256[relative],
                "HMSO01R_B_FROZEN_EVIDENCE_IDENTITY_FAILURE",
                relative,
            )
        require(expected == expected_blob_sha, "HMSO01R_B_FROZEN_FILE_BLOB_HASH_DISAGREEMENT", relative)
        actual_file = sha256(ROOT / relative)
        actual_size = (ROOT / relative).stat().st_size
        blob = git_blob_bytes(pre_target_commit, relative)
        actual_blob_sha = hashlib.sha256(blob).hexdigest()
        actual_oid = git_blob_oid(pre_target_commit, relative)
        require(actual_file == expected, "HMSO01R_B_FROZEN_EVIDENCE_IDENTITY_FAILURE", relative)
        require(actual_size == as_int(record["size_bytes"], field=f"freeze.{relative}.size_bytes"), "HMSO01R_B_FROZEN_FILE_SIZE_FAILURE", relative)
        require(actual_blob_sha == expected_blob_sha, "HMSO01R_B_FROZEN_GIT_BLOB_SHA256_FAILURE", relative)
        require(actual_oid == expected_oid, "HMSO01R_B_FROZEN_GIT_BLOB_OID_FAILURE", relative)

    require(
        set(paths) == REQUIRED_FREEZE_PATHS,
        "HMSO01R_B_PRE_TARGET_FREEZE_PATHSET_FAILURE",
        json.dumps(
            {
                "missing": sorted(REQUIRED_FREEZE_PATHS - set(paths)),
                "unexpected": sorted(set(paths) - REQUIRED_FREEZE_PATHS),
            },
            sort_keys=True,
        ),
    )

    external_sources = first(freeze, ("external_sources",), field="freeze.external_sources", default=[])
    require(isinstance(external_sources, list), "HMSO01R_B_EXTERNAL_SOURCE_FREEZE_SCHEMA_FAILURE")
    external_paths = [
        str(first(record, ("path",), field="external source path"))
        for record in external_sources
        if isinstance(record, Mapping)
    ]
    require(
        len(external_paths) == len(external_sources)
        and len(set(external_paths)) == len(external_paths)
        and set(external_paths) == EXPECTED_EXTERNAL_SOURCE_PATHS,
        "HMSO01R_B_EXTERNAL_SOURCE_FREEZE_PATHSET_FAILURE",
    )
    for record in external_sources:
        require(isinstance(record, Mapping), "HMSO01R_B_EXTERNAL_SOURCE_FREEZE_SCHEMA_FAILURE")
        validate_external_git_source(record)
    require(
        first(target_ledger, ("external_ddo_source_head",), field="target ledger external DDO HEAD")
        == "d76d29ae51e8104641b710371f0fcb248d5ea268",
        "HMSO01R_B_TARGET_ACCESS_LEDGER_EXTERNAL_SOURCE_FAILURE",
    )
    ledger_external = first(
        target_ledger,
        ("external_ddo_source_identities",),
        field="target ledger external DDO identities",
    )
    require(isinstance(ledger_external, Mapping), "HMSO01R_B_TARGET_ACCESS_LEDGER_EXTERNAL_SOURCE_FAILURE")
    expected_external_relatives = {
        path.removeprefix("/Users/xiejinbo/Documents/SPH-DDO-PoC/")
        for path in EXPECTED_EXTERNAL_SOURCE_PATHS
    }
    require(set(ledger_external) == expected_external_relatives, "HMSO01R_B_TARGET_ACCESS_LEDGER_EXTERNAL_SOURCE_FAILURE", "path set")
    for record in external_sources:
        relative = str(record["path"]).removeprefix("/Users/xiejinbo/Documents/SPH-DDO-PoC/")
        ledger_record = ledger_external[relative]
        require(
            isinstance(ledger_record, Mapping)
            and ledger_record.get("sha256") == record.get("sha256")
            and ledger_record.get("git_blob_oid") == record.get("git_blob_oid")
            and ledger_record.get("git_blob_sha256") == record.get("git_blob_sha256"),
            "HMSO01R_B_TARGET_ACCESS_LEDGER_EXTERNAL_SOURCE_FAILURE",
            relative,
        )
    ddo_head = deep_first(
        freeze,
        (("source_provenance", "ddo_source_head"),),
        field="freeze.source_provenance.ddo_source_head",
    )
    require(ddo_head == "d76d29ae51e8104641b710371f0fcb248d5ea268", "HMSO01R_B_DDO_SOURCE_HEAD_FREEZE_FAILURE")
    return paths


def validate_preflight(
    preflight: Mapping[str, Any],
    pre_target_commit: str,
    bootstrap_identity: Mapping[str, Any],
) -> None:
    passed = deep_first(
        preflight,
        (("passed",), ("all_tests_passed",), ("status",)),
        field="preflight pass",
    )
    if isinstance(passed, str) and passed in {"PASS", "PASSED"}:
        passed = True
    require(as_bool(passed, field="preflight.passed"), "HMSO01R_B_CANDIDATE_C_IMPLEMENTATION_PREFLIGHT_FAILURE")
    evaluator_sha = deep_first(
        preflight,
        (("formal_evaluator_sha256",), ("executable_identity", "sha256")),
        field="preflight formal evaluator sha256",
    )
    require(evaluator_sha == sha256(FORMAL_EVALUATOR), "HMSO01R_B_PREFLIGHT_EXECUTABLE_IDENTITY_FAILURE")
    evaluator_blob_oid = deep_first(
        preflight,
        (("formal_evaluator_git_blob_oid",), ("executable_identity", "git_blob_oid")),
        field="preflight formal evaluator Git blob OID",
    )
    preflight_commit = deep_first(
        preflight,
        (("pre_target_commit",), ("executable_identity", "commit")),
        field="preflight pre-target commit",
        default=PRE_TARGET_SENTINEL,
    )
    # Before the containing commit exists, the preflight must use the explicit
    # prospective sentinel plus a recorded candidate-blob OID.  At release the
    # freeze and target ledger bind that OID to the discovered pre-target commit.
    require(str(evaluator_blob_oid) == git_blob_oid(pre_target_commit, str(FORMAL_EVALUATOR.relative_to(ROOT))), "HMSO01R_B_PREFLIGHT_EXECUTABLE_GIT_BLOB_IDENTITY_FAILURE")
    require(
        preflight_commit in {
            PRE_TARGET_SENTINEL,
            "PENDING_COMMIT_OF_THIS_EXACT_PREFLIGHT_AND_EVALUATOR",
            pre_target_commit,
        },
        "HMSO01R_B_PREFLIGHT_EXECUTABLE_GIT_BLOB_IDENTITY_FAILURE",
    )
    draw_count = deep_first(
        preflight,
        (("bootstrap_draw_count",), ("bootstrap", "draw_count"), ("bootstrap", "draws_consumed")),
        field="preflight bootstrap draws",
    )
    require(as_int(draw_count, field="preflight.bootstrap_draw_count") == bootstrap_identity["draw_count"], "HMSO01R_B_PREFLIGHT_BOOTSTRAP_INCOMPLETE")
    unique_draw_count = deep_first(
        preflight,
        (("bootstrap_unique_draw_count",), ("bootstrap", "unique_draw_count")),
        field="preflight unique bootstrap draws",
    )
    require(as_int(unique_draw_count, field="preflight.bootstrap_unique_draw_count") == bootstrap_identity["unique_draw_count"], "HMSO01R_B_PREFLIGHT_BOOTSTRAP_IDENTITY_FAILURE")
    frozen_draw_sha = deep_first(
        preflight,
        (("bootstrap_draws_sha256",), ("bootstrap", "draws_sha256")),
        field="preflight bootstrap draws sha256",
    )
    require(
        frozen_draw_sha == bootstrap_identity["sha256"],
        "HMSO01R_B_PREFLIGHT_BOOTSTRAP_IDENTITY_FAILURE",
    )
    decoded_case_count = deep_first(
        preflight,
        (("bootstrap", "decoded_case_emission_count"),),
        field="preflight decoded case emissions",
    )
    decoded_occurrence_count = deep_first(
        preflight,
        (("bootstrap", "decoded_lineage_occurrence_count"),),
        field="preflight decoded lineage occurrences",
    )
    require(
        as_int(decoded_case_count, field="preflight decoded case emissions")
        == bootstrap_identity["decoded_case_emission_count"]
        and as_int(decoded_occurrence_count, field="preflight decoded lineage occurrences")
        == bootstrap_identity["decoded_lineage_occurrence_count"],
        "HMSO01R_B_PREFLIGHT_BOOTSTRAP_IDENTITY_FAILURE",
        "decoded identity counts",
    )
    paired = deep_first(
        preflight,
        (("paired_ss_ms_identity",), ("bootstrap", "paired_ss_ms_identity")),
        field="preflight paired SS/MS identity",
    )
    require(as_bool(paired, field="preflight.paired_ss_ms_identity"), "HMSO01R_B_PREFLIGHT_BOOTSTRAP_IDENTITY_FAILURE")
    reaggregate_wn = deep_first(
        preflight,
        (("recomputed_WN_each_draw",), ("bootstrap", "recomputed_WN_each_draw")),
        field="preflight WN reaggregation",
    )
    reaggregate_wb = deep_first(
        preflight,
        (("recomputed_WB_each_draw",), ("bootstrap", "recomputed_WB_each_draw")),
        field="preflight WB reaggregation",
    )
    require(
        as_bool(reaggregate_wn, field="preflight.recomputed_WN_each_draw")
        and as_bool(reaggregate_wb, field="preflight.recomputed_WB_each_draw"),
        "HMSO01R_B_PREFLIGHT_BOOTSTRAP_REAGGREGATION_FAILURE",
    )
    pointwise = deep_first(
        preflight,
        (("pointwise_division_count",), ("division_audit", "pointwise_division_count")),
        field="preflight pointwise division count",
    )
    require(as_int(pointwise, field="preflight.pointwise_division_count") == 0, "HMSO01R_B_POINTWISE_CANDIDATE_C_DIVISION_FORBIDDEN")
    actual_divisions = deep_first(
        preflight,
        (("final_candidate_c_division_count",), ("division_audit", "final_candidate_c_division_count")),
        field="preflight final division count",
    )
    expected_divisions = deep_first(
        preflight,
        (("expected_final_candidate_c_division_count",), ("division_audit", "expected_final_candidate_c_division_count")),
        field="preflight expected final division count",
    )
    require(
        as_int(actual_divisions, field="preflight.final divisions")
        == as_int(expected_divisions, field="preflight.expected divisions"),
        "HMSO01R_B_PREFLIGHT_CANDIDATE_C_DIVISION_COUNT_FAILURE",
    )
    degenerate_primary = as_int(
        deep_first(preflight, (("bootstrap", "degenerate_primary_draw_count"),), field="preflight degenerate primary draws"),
        field="preflight degenerate primary draws",
    )
    require(0 <= degenerate_primary <= 200, "HMSO01R_B_PREFLIGHT_BOOTSTRAP_DEGENERACY_FAILURE")
    valid_primary = 10000 - degenerate_primary
    derived_candidate_divisions = 6 + valid_primary * 9 + 3 + 3
    paired_actual = as_int(
        deep_first(preflight, (("division_audit", "paired_log_ratio_division_count"),), field="preflight paired divisions"),
        field="preflight paired divisions",
    )
    paired_expected_recorded = as_int(
        deep_first(preflight, (("division_audit", "expected_paired_log_ratio_division_count"),), field="preflight expected paired divisions"),
        field="preflight expected paired divisions",
    )
    derived_paired_divisions = 2 * (3 + valid_primary * 3)
    require(
        as_int(actual_divisions, field="preflight.final divisions")
        == as_int(expected_divisions, field="preflight.expected divisions")
        == derived_candidate_divisions
        and paired_actual == paired_expected_recorded == derived_paired_divisions,
        "HMSO01R_B_PREFLIGHT_CANDIDATE_C_DIVISION_COUNT_FAILURE",
    )
    for key in (
        "target_payload_read_count",
        "observable_payload_read_count",
        "analytical_reference_evaluation_count",
        "defect_generation_count",
    ):
        value = deep_first(
            preflight,
            ((key,), ("firewall", key)),
            field=f"preflight.{key}",
        )
        require(as_int(value, field=f"preflight.{key}") == 0, "HMSO01R_B_PREFLIGHT_INFORMATION_FIREWALL_FAILURE", key)
    for key in ("epsilon_count", "clipping_count", "zero_row_deletion_count", "zero_group_deletion_count"):
        value = deep_first(
            preflight,
            ((key,), ("division_audit", key)),
            field=f"preflight.{key}",
        )
        require(as_int(value, field=f"preflight.{key}") == 0, "HMSO01R_B_PREFLIGHT_ZERO_SAFE_SEMANTICS_FAILURE", key)
    canonical = deep_first(
        preflight,
        (("canonical_zero_status",), ("status_semantics", "canonical_zero_status")),
        field="preflight canonical zero status",
    )
    alias = deep_first(
        preflight,
        (("current_instruction_zero_status_alias",), ("status_semantics", "current_instruction_alias")),
        field="preflight zero alias",
    )
    require(canonical == CA_ZERO_STATUS and alias == CURRENT_ZERO_ALIAS, "HMSO01R_B_ZERO_STATUS_CANONICALIZATION_FAILURE")
    required_scenarios = {
        "scalar_target",
        "vector_target",
        "isolated_0_over_0_retained",
        "isolated_positive_over_0_retained",
        "zero_case_denominator_retained",
        "zero_lineage_denominator_retained",
        "zero_family_denominator_retained",
        "zero_fold_denominator_retained",
        "positive_total_WB",
        "zero_total_WB",
        "ss_zero_baseline",
        "ms_exact_zero",
        "hierarchical_equal_weighting",
        "more_than_200_degenerate_draws_not_evaluable",
        "fewer_than_2_valid_draws_not_evaluable",
        "no_pointwise_ratio",
        "no_epsilon",
        "no_zero_row_or_group_deletion",
    }
    scenarios = deep_first(
        preflight,
        (("scenarios",), ("scenario_results",)),
        field="preflight scenarios",
    )
    require(isinstance(scenarios, (list, Mapping)), "HMSO01R_B_PREFLIGHT_SCENARIO_COVERAGE_FAILURE")
    if isinstance(scenarios, Mapping):
        scenario_pass = {str(name): as_bool(value if not isinstance(value, Mapping) else first(value, ("passed", "pass"), field=f"preflight scenario {name}"), field=f"preflight scenario {name}") for name, value in scenarios.items()}
    else:
        scenario_pass = {}
        for row in scenarios:
            require(isinstance(row, Mapping), "HMSO01R_B_PREFLIGHT_SCENARIO_COVERAGE_FAILURE")
            name = str(first(row, ("name", "scenario", "test"), field="preflight scenario name"))
            scenario_pass[name] = as_bool(first(row, ("passed", "pass"), field=f"preflight scenario {name}"), field=f"preflight scenario {name}")
    require(required_scenarios.issubset(scenario_pass), "HMSO01R_B_PREFLIGHT_SCENARIO_COVERAGE_FAILURE", str(sorted(required_scenarios - set(scenario_pass))))
    require(all(scenario_pass[name] for name in required_scenarios), "HMSO01R_B_PREFLIGHT_SCENARIO_FAILURE")
    cutoff_evidence = first(
        preflight,
        ("candidate_c_degeneracy_cutoff_evidence",),
        field="preflight Candidate C degeneracy cutoff evidence",
    )
    require(isinstance(cutoff_evidence, Mapping), "HMSO01R_B_PREFLIGHT_DEGENERACY_CUTOFF_FAILURE")
    excess = first(
        cutoff_evidence,
        ("more_than_200_degenerate_draws",),
        field="preflight >200-degenerate evidence",
    )
    insufficient = first(
        cutoff_evidence,
        ("fewer_than_2_valid_draws",),
        field="preflight <2-valid evidence",
    )
    require(
        isinstance(excess, Mapping)
        and isinstance(insufficient, Mapping)
        and as_int(first(cutoff_evidence, ("maximum_degenerate_draw_count",), field="preflight degeneracy maximum"), field="preflight degeneracy maximum") == 200
        and as_int(first(cutoff_evidence, ("minimum_valid_draw_count",), field="preflight valid-draw minimum"), field="preflight valid-draw minimum") == 2
        and as_int(first(excess, ("constructed_degenerate_draw_count",), field="preflight excess degenerate count"), field="preflight excess degenerate count") == 201
        and as_int(first(excess, ("constructed_zero_aggregate_denominator_draw_count",), field="preflight excess zero-WB count"), field="preflight excess zero-WB count") == 201
        and as_int(first(excess, ("constructed_valid_draw_count",), field="preflight excess valid count"), field="preflight excess valid count") == 9799
        and as_bool(first(excess, ("passed",), field="preflight excess cutoff pass"), field="preflight excess cutoff pass")
        and as_int(first(insufficient, ("constructed_degenerate_draw_count",), field="preflight insufficient degenerate count"), field="preflight insufficient degenerate count") == 9999
        and as_int(first(insufficient, ("constructed_zero_aggregate_denominator_draw_count",), field="preflight insufficient zero-WB count"), field="preflight insufficient zero-WB count") == 9999
        and as_int(first(insufficient, ("constructed_valid_draw_count",), field="preflight insufficient valid count"), field="preflight insufficient valid count") == 1
        and as_bool(first(insufficient, ("passed",), field="preflight insufficient cutoff pass"), field="preflight insufficient cutoff pass"),
        "HMSO01R_B_PREFLIGHT_DEGENERACY_CUTOFF_FAILURE",
    )
    for label, record in (("excess", excess), ("insufficient", insufficient)):
        statuses = first(record, ("status_by_component",), field=f"preflight {label} cutoff statuses")
        require(
            isinstance(statuses, Mapping)
            and set(statuses) == set(COMPONENTS)
            and all(str(statuses[component]) == "NOT_EVALUABLE" for component in COMPONENTS),
            "HMSO01R_B_PREFLIGHT_DEGENERACY_CUTOFF_FAILURE",
            f"{label}:status_by_component",
        )


def validate_qualification(rows: Sequence[Mapping[str, str]]) -> list[str]:
    require(len(rows) == 384, "HMSO01R_B_TARGET_REFERENCE_QUALIFICATION_NOT_COMPLETE", f"row_count={len(rows)}")
    atlas_cases = first(json_load(FORMAL_ATLAS), ("cases",), field="formal atlas cases")
    require(isinstance(atlas_cases, list) and len(atlas_cases) == 384, "HMSO01R_B_FROZEN_ATLAS_SCHEMA_FAILURE")
    case_ids: list[str] = []
    for index, row in enumerate(rows):
        case_id = str(first(row, ("case_id",), field=f"qualification[{index}].case_id"))
        case_ids.append(case_id)
        frozen = atlas_cases[index]
        require(
            as_int(first(row, ("formal_case_index",), field=f"qualification[{index}].formal_case_index"), field=f"qualification[{index}].formal_case_index") == index
            and case_id == str(frozen["case_id"])
            and str(first(row, ("family", "macro_family"), field=f"qualification[{index}].family")) == str(frozen["macro_family"])
            and str(first(row, ("fold",), field=f"qualification[{index}].fold")) == str(frozen["fold"])
            and str(first(row, ("field_lineage_id", "lineage"), field=f"qualification[{index}].lineage")) == str(frozen["field_lineage_id"]),
            "HMSO01R_B_TARGET_REFERENCE_QUALIFICATION_IDENTITY_FAILURE",
            case_id,
        )
        if "particle_state_hash" in row:
            require(str(row["particle_state_hash"]) == str(frozen["particle_state_hash"]), "HMSO01R_B_TARGET_REFERENCE_QUALIFICATION_IDENTITY_FAILURE", f"{case_id}:particle_state_hash")
        overall = first(
            row,
            ("case_target_reference_qualified", "target_reference_qualified", "qualified"),
            field=f"qualification[{index}].qualified",
        )
        require(as_bool(overall, field=f"qualification[{case_id}].qualified"), "HMSO01R_B_TARGET_REFERENCE_QUALIFICATION_NOT_COMPLETE", case_id)
        for check, aliases in QUALIFICATION_CHECK_ALIASES.items():
            value = first(row, aliases, field=f"qualification[{case_id}].{check}")
            require(as_bool(value, field=f"qualification[{case_id}].{check}"), "HMSO01R_B_TARGET_REFERENCE_QUALIFICATION_NOT_COMPLETE", f"{case_id}:{check}")
        for check in ("graph_repeatability_bitwise", "operator_repeatability_bitwise"):
            require(
                as_bool(first(row, (check,), field=f"qualification[{case_id}].{check}"), field=f"qualification[{case_id}].{check}"),
                "HMSO01R_B_TARGET_REFERENCE_QUALIFICATION_NOT_COMPLETE",
                f"{case_id}:{check}",
            )
        uncertainty_columns = [
            name for name in row
            if name.endswith("__sign_gate_passed")
            or name.endswith("__uncertainty_gate_passed")
        ]
        require(len(uncertainty_columns) == 4, "HMSO01R_B_TARGET_REFERENCE_QUALIFICATION_SCHEMA_FAILURE", f"{case_id}:uncertainty checks")
        for name in uncertainty_columns:
            require(
                as_bool(row[name], field=f"qualification[{case_id}].{name}"),
                "HMSO01R_B_TARGET_REFERENCE_QUALIFICATION_NOT_COMPLETE",
                f"{case_id}:{name}",
            )
        uncertainty_values = [name for name in row if name.endswith("__U_num")]
        require(len(uncertainty_values) == 4, "HMSO01R_B_TARGET_REFERENCE_QUALIFICATION_SCHEMA_FAILURE", f"{case_id}:U_num")
        for name in uncertainty_values:
            as_float(row[name], field=f"qualification[{case_id}].{name}")
        lambda_value = first(row, ("formal_operator_lambda", "operator_lambda", "lambda"), field=f"qualification[{case_id}].lambda")
        require(as_float(lambda_value, field=f"qualification[{case_id}].lambda") == 1.0, "HMSO01R_B_FORMAL_TARGET_LAMBDA_FAILURE", case_id)
    require(len(set(case_ids)) == 384, "HMSO01R_B_TARGET_REFERENCE_QUALIFICATION_DUPLICATE_CASE")
    return case_ids


def validate_join(
    rows: Sequence[Mapping[str, str]],
    qualification_case_ids: Sequence[str],
) -> None:
    require(len(rows) == 384 * 128, "HMSO01R_B_TARGET_OBSERVABLE_PAIRING_FAILURE", f"row_count={len(rows)}")
    sample_payload = json_load(FORMAL_SAMPLE)
    atlas_payload = json_load(FORMAL_ATLAS)
    sample_cases = first(sample_payload, ("cases",), field="formal sample cases")
    atlas_cases = first(atlas_payload, ("cases",), field="formal atlas cases")
    require(isinstance(sample_cases, list) and len(sample_cases) == 384, "HMSO01R_B_FROZEN_PARTICLE_SAMPLE_SCHEMA_FAILURE")
    require(isinstance(atlas_cases, list) and len(atlas_cases) == 384, "HMSO01R_B_FROZEN_ATLAS_SCHEMA_FAILURE")
    require(len(qualification_case_ids) == 384 and len(set(qualification_case_ids)) == 384, "HMSO01R_B_TARGET_REFERENCE_QUALIFICATION_NOT_COMPLETE")
    atlas_by_id = {str(case["case_id"]): case for case in atlas_cases}
    sample_by_id = {str(case["case_id"]): case for case in sample_cases}
    require(set(atlas_by_id) == set(sample_by_id) == set(qualification_case_ids), "HMSO01R_B_TARGET_OBSERVABLE_PAIRING_FAILURE", "case population mismatch")
    expected: dict[tuple[str, str], dict[str, str]] = {}
    for case_id, sample_case in sample_by_id.items():
        atlas_case = atlas_by_id[case_id]
        require(int(sample_case["sample_count"]) == 128, "HMSO01R_B_FROZEN_PARTICLE_SAMPLE_SCHEMA_FAILURE", case_id)
        require(
            str(sample_case["particle_state_hash"]) == str(atlas_case["particle_state_hash"])
            and str(sample_case["field_lineage_id"]) == str(atlas_case["field_lineage_id"])
            and str(sample_case["family"]) == str(atlas_case["macro_family"])
            and str(sample_case["fold"]) == str(atlas_case["fold"]),
            "HMSO01R_B_FROZEN_PARTICLE_ATLAS_IDENTITY_FAILURE",
            case_id,
        )
        particle_ids = sample_case["particle_ids_in_hash_order"]
        require(isinstance(particle_ids, list) and len(particle_ids) == 128 and len(set(particle_ids)) == 128, "HMSO01R_B_FROZEN_PARTICLE_SAMPLE_SCHEMA_FAILURE", case_id)
        for particle_id in particle_ids:
            expected[(case_id, str(particle_id))] = {
                "particle_state_hash": str(atlas_case["particle_state_hash"]),
                "lineage": str(atlas_case["field_lineage_id"]),
                "family": str(atlas_case["macro_family"]),
                "fold": str(atlas_case["fold"]),
            }
    identities: set[tuple[str, str]] = set()
    for index, row in enumerate(rows):
        case_id = str(first(row, ("case_id",), field=f"join[{index}].case_id"))
        particle_id = str(first(row, ("particle_id",), field=f"join[{index}].particle_id"))
        identity = (case_id, particle_id)
        identities.add(identity)
        require(identity in expected, "HMSO01R_B_TARGET_OBSERVABLE_PAIRING_FAILURE", f"unexpected:{case_id}:{particle_id}")
        frozen = expected[identity]
        row_state = str(first(row, ("particle_state_hash", "target_particle_state_hash"), field=f"join[{index}].particle_state_hash"))
        row_lineage = str(first(row, ("field_lineage_id", "lineage", "lineage_id"), field=f"join[{index}].lineage"))
        row_family = str(first(row, ("family", "macro_family"), field=f"join[{index}].family"))
        row_fold = str(first(row, ("fold",), field=f"join[{index}].fold"))
        require(
            row_state == frozen["particle_state_hash"]
            and row_lineage == frozen["lineage"]
            and row_family == frozen["family"]
            and row_fold == frozen["fold"],
            "HMSO01R_B_TARGET_OBSERVABLE_PAIRING_FAILURE",
            f"frozen mismatch:{case_id}:{particle_id}",
        )
        match = first(
            row,
            ("all_identity_fields_match", "identity_match", "row_identity_match", "pairing_pass"),
            field=f"join[{index}].identity_match",
        )
        require(as_bool(match, field=f"join[{index}].identity_match"), "HMSO01R_B_TARGET_OBSERVABLE_PAIRING_FAILURE", f"{case_id}:{particle_id}")
        for key in ("particle_state_hash_match", "lineage_match", "family_match", "fold_match"):
            if key in row:
                require(as_bool(row[key], field=f"join[{index}].{key}"), "HMSO01R_B_TARGET_OBSERVABLE_PAIRING_FAILURE", f"{case_id}:{particle_id}:{key}")
    require(identities == set(expected), "HMSO01R_B_TARGET_OBSERVABLE_PAIRING_FAILURE", "missing, duplicate, or extra frozen identity")


def validate_division_audit(audit: Mapping[str, Any]) -> dict[str, Any]:
    require(as_int(first(audit, ("pointwise_division_count",), field="division.pointwise"), field="division.pointwise") == 0, "HMSO01R_B_POINTWISE_CANDIDATE_C_DIVISION_FORBIDDEN")
    actual = as_int(first(audit, ("final_candidate_c_division_count",), field="division.final"), field="division.final")
    expected = as_int(first(audit, ("expected_final_candidate_c_division_count",), field="division.expected"), field="division.expected")
    cells = first(audit, ("arm_component_divisions", "candidate_c_cells"), field="division arm-component cells")
    require(isinstance(cells, list) and len(cells) == 6, "HMSO01R_B_CANDIDATE_C_DIVISION_AUDIT_SCHEMA_FAILURE", "arm-component cells")
    observed_cells: set[tuple[str, str]] = set()
    fold_divisions_by_cell: dict[tuple[str, str], int] = {}
    arm_rows: dict[tuple[str, str], Mapping[str, Any]] = {}
    derived_candidate_c_divisions = 0
    for row in cells:
        require(isinstance(row, Mapping), "HMSO01R_B_CANDIDATE_C_DIVISION_AUDIT_SCHEMA_FAILURE")
        arm = str(first(row, ("arm",), field="division cell arm")).upper()
        component = str(first(row, ("component",), field="division cell component"))
        require(arm in ARMS and component in COMPONENTS, "HMSO01R_B_CANDIDATE_C_DIVISION_AUDIT_SCHEMA_FAILURE", f"{arm}:{component}")
        observed_cells.add((arm, component))
        arm_rows[(arm, component)] = row
        degenerate = as_int(first(row, ("degenerate_aggregate_denominator_replicate_count", "degenerate_draw_count"), field=f"division {arm}.{component} degenerate"), field=f"division {arm}.{component} degenerate")
        evaluable = as_int(first(row, ("evaluable_replicate_count", "valid_draw_count"), field=f"division {arm}.{component} evaluable"), field=f"division {arm}.{component} evaluable")
        require(degenerate >= 0 and evaluable >= 0 and degenerate + evaluable == 10000, "HMSO01R_B_CANDIDATE_C_BOOTSTRAP_COUNT_FAILURE", f"{arm}:{component}")
        status = normalize_zero_status(first(row, ("status", "candidate_c_status"), field=f"division {arm}.{component} status"))
        metric_evaluable = as_bool(first(row, ("evaluable", "candidate_c_evaluable"), field=f"division {arm}.{component} evaluable status"), field=f"division {arm}.{component} evaluable status")
        point_denominator_positive = as_bool(first(row, ("point_aggregate_denominator_positive", "point_wb_positive"), field=f"division {arm}.{component} point denominator"), field=f"division {arm}.{component} point denominator")
        bootstrap_and_point_evaluable = bool(
            point_denominator_positive
            and degenerate <= 200
            and evaluable >= 2
        )
        if metric_evaluable:
            require(bootstrap_and_point_evaluable and status == "EVALUABLE", "HMSO01R_B_CANDIDATE_C_DEGENERACY_RULE_FAILURE", f"{arm}:{component}")
        elif bootstrap_and_point_evaluable:
            require("NOT_EVALUABLE" in str(status), "HMSO01R_B_CANDIDATE_C_DEGENERACY_RULE_FAILURE", f"{arm}:{component}:bound-status")
        if not point_denominator_positive:
            require(status == CA_ZERO_STATUS, "HMSO01R_B_ZERO_AGGREGATE_STATUS_FAILURE", f"{arm}:{component}")
        if degenerate > 200 or evaluable < 2:
            require(not metric_evaluable and "NOT_EVALUABLE" in str(status), "HMSO01R_B_CANDIDATE_C_DEGENERACY_RULE_FAILURE", f"{arm}:{component}:status")
        point_divisions = as_int(first(row, ("point_candidate_c_division_count", "point_division_count"), field=f"division {arm}.{component} point divisions"), field=f"division {arm}.{component} point divisions")
        bootstrap_divisions = as_int(first(row, ("bootstrap_candidate_c_division_count", "bootstrap_division_count"), field=f"division {arm}.{component} bootstrap divisions"), field=f"division {arm}.{component} bootstrap divisions")
        fold_divisions = as_int(
            first(row, ("fold_candidate_c_division_count",), field=f"division {arm}.{component} fold divisions"),
            field=f"division {arm}.{component} fold divisions",
        )
        require(point_divisions == (1 if point_denominator_positive else 0), "HMSO01R_B_CANDIDATE_C_DIVISION_COUNT_FAILURE", f"{arm}:{component}:point")
        require(bootstrap_divisions == evaluable, "HMSO01R_B_CANDIDATE_C_DIVISION_COUNT_FAILURE", f"{arm}:{component}:bootstrap")
        require(0 <= fold_divisions <= 6, "HMSO01R_B_CANDIDATE_C_DIVISION_COUNT_FAILURE", f"{arm}:{component}:fold")
        fold_divisions_by_cell[(arm, component)] = fold_divisions
        derived_candidate_c_divisions += point_divisions + bootstrap_divisions + fold_divisions
    require(observed_cells == {(arm, component) for arm in ARMS for component in COMPONENTS}, "HMSO01R_B_CANDIDATE_C_DIVISION_AUDIT_SCHEMA_FAILURE", "cell identity")

    paired_cells = first(audit, ("paired_ratio_divisions", "paired_component_divisions"), field="division paired cells")
    require(isinstance(paired_cells, list) and len(paired_cells) == 3, "HMSO01R_B_CANDIDATE_C_DIVISION_AUDIT_SCHEMA_FAILURE", "paired cells")
    observed_paired: set[str] = set()
    paired_rows: dict[str, Mapping[str, Any]] = {}
    derived_paired_divisions = 0
    for row in paired_cells:
        require(isinstance(row, Mapping), "HMSO01R_B_CANDIDATE_C_DIVISION_AUDIT_SCHEMA_FAILURE")
        component = str(first(row, ("component",), field="paired division component"))
        require(component in COMPONENTS, "HMSO01R_B_CANDIDATE_C_DIVISION_AUDIT_SCHEMA_FAILURE", component)
        observed_paired.add(component)
        paired_rows[component] = row
        point_evaluable = as_bool(first(row, ("point_ratio_evaluable", "point_evaluable"), field=f"paired {component} point evaluable"), field=f"paired {component} point evaluable")
        valid_draws = as_int(first(row, ("evaluable_replicate_count", "valid_draw_count"), field=f"paired {component} valid draws"), field=f"paired {component} valid draws")
        point_count = as_int(first(row, ("point_ratio_division_count", "point_division_count"), field=f"paired {component} point divisions"), field=f"paired {component} point divisions")
        draw_count = as_int(first(row, ("bootstrap_ratio_division_count", "bootstrap_division_count"), field=f"paired {component} bootstrap divisions"), field=f"paired {component} bootstrap divisions")
        require(0 <= valid_draws <= 10000, "HMSO01R_B_CANDIDATE_C_BOOTSTRAP_COUNT_FAILURE", f"paired:{component}")
        require(point_count == (1 if point_evaluable else 0) and draw_count == valid_draws, "HMSO01R_B_CANDIDATE_C_DIVISION_COUNT_FAILURE", f"paired:{component}")
        derived_paired_divisions += point_count + draw_count
    require(observed_paired == set(COMPONENTS), "HMSO01R_B_CANDIDATE_C_DIVISION_AUDIT_SCHEMA_FAILURE", "paired identity")
    derived_expected = derived_candidate_c_divisions + derived_paired_divisions
    require(actual == expected == derived_expected and actual > 0, "HMSO01R_B_CANDIDATE_C_DIVISION_COUNT_FAILURE")
    require(as_int(first(audit, ("bootstrap_draws_consumed", "draw_count"), field="division.bootstrap_draws"), field="division.bootstrap_draws") == 10000, "HMSO01R_B_BOOTSTRAP_CONSUMPTION_FAILURE")
    require(as_int(first(audit, ("bootstrap_unique_draw_count", "unique_draw_count"), field="division.unique_draws"), field="division.unique_draws") == 10000, "HMSO01R_B_BOOTSTRAP_IDENTITY_FAILURE")
    require(first(audit, ("bootstrap_draws_sha256",), field="division.bootstrap_draws_sha256") == sha256(ROOT / "06_experiments/hmso01r_a/bootstrap_draws.npz"), "HMSO01R_B_BOOTSTRAP_IDENTITY_FAILURE")
    require(as_bool(first(audit, ("paired_ss_ms_identity", "paired_arms"), field="division.paired"), field="division.paired"), "HMSO01R_B_BOOTSTRAP_PAIRING_FAILURE")
    require(as_bool(first(audit, ("recomputed_WN_each_draw",), field="division.recomputed_WN_each_draw"), field="division.recomputed_WN_each_draw"), "HMSO01R_B_BOOTSTRAP_REAGGREGATION_FAILURE")
    require(as_bool(first(audit, ("recomputed_WB_each_draw",), field="division.recomputed_WB_each_draw"), field="division.recomputed_WB_each_draw"), "HMSO01R_B_BOOTSTRAP_REAGGREGATION_FAILURE")
    for key in ("epsilon_count", "clipping_count", "zero_row_deletion_count", "zero_group_deletion_count"):
        require(as_int(first(audit, (key,), field=f"division.{key}"), field=f"division.{key}") == 0, "HMSO01R_B_CANDIDATE_C_ZERO_SAFE_SEMANTICS_FAILURE", key)
    return {"arms": arm_rows, "paired": paired_rows, "fold_divisions": fold_divisions_by_cell}


def validate_firewall(firewall: Mapping[str, Any]) -> dict[str, int]:
    prohibited = first(firewall, ("prohibited_activity_counts",), field="firewall.prohibited_activity_counts")
    require(isinstance(prohibited, Mapping), "HMSO01R_B_FIREWALL_SCHEMA_FAILURE")
    counts: dict[str, int] = {}
    for key in PROHIBITED_KEYS:
        value = first(prohibited, (key,), field=f"firewall.prohibited.{key}")
        counts[key] = as_int(value, field=f"firewall.prohibited.{key}")
        require(counts[key] == 0, "HMSO01R_B_INFORMATION_FIREWALL_BREACH", key)
    authorized = first(firewall, ("authorized_activity_counts", "authorized_target_access_counts"), field="firewall.authorized counts")
    require(isinstance(authorized, Mapping), "HMSO01R_B_FIREWALL_SCHEMA_FAILURE", "authorized counts")
    required_authorized = {
        "target_case_evaluation_count": 384,
        "reference_evaluation_count": 384,
        "target_store_read_count": 1,
        "target_store_write_count": 1,
        "candidate_c_evaluation_count": 1,
        "conditional_variance_evaluation_count": 1,
        # Two arms x six outer folds x twelve frozen fit/selection operations.
        "oracle_fit_count": 144,
        "coverage_evaluation_count": 1,
        "paired_rescue_evaluation_count": 1,
        "bootstrap_draws_consumed": 10000,
    }
    authorized_aliases = {
        "target_case_evaluation_count": ("target_case_evaluation_count", "target_case_evaluations"),
        "reference_evaluation_count": ("reference_evaluation_count", "reference_evaluations"),
        "target_store_read_count": ("target_store_read_count", "target_store_reads"),
        "target_store_write_count": ("target_store_write_count", "target_store_writes"),
        "candidate_c_evaluation_count": ("candidate_c_evaluation_count", "dnn_candidate_c_evaluation_count", "candidate_c_evaluations"),
        "conditional_variance_evaluation_count": ("conditional_variance_evaluation_count", "conditional_variance_evaluations"),
        "oracle_fit_count": ("oracle_fit_count", "oracle_fits"),
        "coverage_evaluation_count": ("coverage_evaluation_count", "coverage_evaluations"),
        "paired_rescue_evaluation_count": ("paired_rescue_evaluation_count", "paired_rescue_evaluations"),
        "bootstrap_draws_consumed": ("bootstrap_draws_consumed", "bootstrap_draw_count"),
    }
    normalized: dict[str, int] = {}
    for key, expected in required_authorized.items():
        value = as_int(first(authorized, authorized_aliases[key], field=f"firewall.authorized.{key}"), field=f"firewall.authorized.{key}")
        normalized[key] = value
        require(value == expected, "HMSO01R_B_AUTHORIZED_ACTIVITY_LEDGER_FAILURE", key)
    before = deep_first(
        firewall,
        (("observable_store_sha256_before",), ("observable_store", "sha256_before")),
        field="firewall observable before",
    )
    after = deep_first(
        firewall,
        (("observable_store_sha256_after",), ("observable_store", "sha256_after")),
        field="firewall observable after",
    )
    require(before == OBSERVABLE_SHA256 and after == OBSERVABLE_SHA256, "HMSO01R_B_OBSERVABLE_STORE_IDENTITY_FAILURE")
    return normalized


def metric_block(summary: Mapping[str, Any], arm: str, component: str) -> Mapping[str, Any]:
    metrics = first(summary, ("metrics",), field="summary.metrics")
    require(isinstance(metrics, Mapping), "HMSO01R_B_FORMAL_SUMMARY_SCHEMA_FAILURE", "metrics")
    arm_map = first(metrics, (arm, arm.lower()), field=f"summary.metrics.{arm}")
    require(isinstance(arm_map, Mapping), "HMSO01R_B_FORMAL_SUMMARY_SCHEMA_FAILURE", arm)
    block = first(arm_map, (component,), field=f"summary.metrics.{arm}.{component}")
    require(isinstance(block, Mapping), "HMSO01R_B_FORMAL_SUMMARY_SCHEMA_FAILURE", f"{arm}.{component}")
    return block


def paired_block(summary: Mapping[str, Any], component: str) -> Mapping[str, Any]:
    metrics = first(summary, ("metrics",), field="summary.metrics")
    paired = first(metrics, ("paired", "paired_ratios", "paired_rescue"), field="summary.metrics.paired")
    require(isinstance(paired, Mapping), "HMSO01R_B_FORMAL_SUMMARY_SCHEMA_FAILURE", "paired")
    block = first(paired, (component,), field=f"summary.metrics.paired.{component}")
    require(isinstance(block, Mapping), "HMSO01R_B_FORMAL_SUMMARY_SCHEMA_FAILURE", component)
    return block


def candidate_values(block: Mapping[str, Any], label: str) -> tuple[float | None, float | None, str, bool]:
    status = normalize_zero_status(first(block, ("candidate_c_status", "dnn_status", "status"), field=f"{label}.candidate_c_status"))
    evaluable = as_bool(first(block, ("candidate_c_evaluable", "dnn_evaluable", "evaluable"), field=f"{label}.candidate_c_evaluable"), field=f"{label}.candidate_c_evaluable")
    point = as_float(first(block, ("candidate_c_d", "candidate_c", "dnn", "point"), field=f"{label}.candidate_c_d", default=None), field=f"{label}.candidate_c_d", allow_none=True)
    ucb = as_float(first(block, ("candidate_c_simultaneous_ucb", "candidate_c_ucb", "dnn_simultaneous_ucb", "simultaneous_ucb"), field=f"{label}.candidate_c_ucb", default=None), field=f"{label}.candidate_c_ucb", allow_none=True)
    if evaluable:
        require(point is not None and ucb is not None, "HMSO01R_B_CANDIDATE_C_VALUE_MISSING", label)
        require(status not in {CA_ZERO_STATUS, ZERO_SS_STATUS}, "HMSO01R_B_CANDIDATE_C_STATUS_INCONSISTENT", label)
    else:
        require(status in {CA_ZERO_STATUS, ZERO_SS_STATUS, "NOT_EVALUABLE"} or "NOT_EVALUABLE" in str(status), "HMSO01R_B_CANDIDATE_C_STATUS_INCONSISTENT", label)
    return point, ucb, str(status), evaluable


def verdict_components(summary: Mapping[str, Any]) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    verdict = first(summary, ("verdict",), field="summary.verdict")
    require(isinstance(verdict, Mapping), "HMSO01R_B_FORMAL_SUMMARY_SCHEMA_FAILURE", "verdict")
    components = first(verdict, ("components",), field="summary.verdict.components")
    require(isinstance(components, Mapping), "HMSO01R_B_FORMAL_SUMMARY_SCHEMA_FAILURE", "verdict.components")
    return verdict, components


def unique_rows(
    rows: Sequence[Mapping[str, Any]],
    keys: Sequence[str],
    *,
    label: str,
) -> dict[tuple[str, ...], Mapping[str, Any]]:
    output: dict[tuple[str, ...], Mapping[str, Any]] = {}
    for row_index, row in enumerate(rows):
        identity = tuple(str(first(row, (key,), field=f"{label}[{row_index}].{key}")) for key in keys)
        require(identity not in output, "HMSO01R_B_DUPLICATE_FORMAL_METRIC_ROW", f"{label}:{identity}")
        output[identity] = row
    return output


def finite_vector(value: Any, length: int, *, field: str) -> list[float | None]:
    require(isinstance(value, list) and len(value) == length, "HMSO01R_B_FORMAL_SUMMARY_SCHEMA_FAILURE", field)
    return [optional_float(item, field=f"{field}[{index}]") for index, item in enumerate(value)]


def finite_map(value: Any, keys: Sequence[str], *, field: str) -> dict[str, float | None]:
    require(isinstance(value, Mapping), "HMSO01R_B_FORMAL_SUMMARY_SCHEMA_FAILURE", field)
    require_exact_keys(value, keys, field=field)
    return {key: optional_float(value[key], field=f"{field}.{key}") for key in keys}


def bool_map(value: Any, keys: Sequence[str], *, field: str) -> dict[str, bool]:
    require(isinstance(value, Mapping), "HMSO01R_B_COMPONENT_VERDICT_SCHEMA_FAILURE", field)
    require_exact_keys(value, keys, field=field)
    return {key: as_bool(value[key], field=f"{field}.{key}") for key in keys}


def require_bool_map(recorded: Any, expected: Mapping[str, bool], *, field: str) -> None:
    parsed = bool_map(recorded, tuple(expected), field=field)
    require(parsed == dict(expected), "HMSO01R_B_GATE_RECOMPUTATION_FAILURE", field)


def parse_status_leaf(
    value: Any,
    *,
    field: str,
    applicable: bool = True,
) -> dict[str, Any]:
    """Validate one explicit non-DNN evaluability/status/mechanism leaf."""

    require(isinstance(value, Mapping), "HMSO01R_B_NON_DNN_STATUS_SCHEMA_FAILURE", field)
    require_exact_keys(
        value,
        ("status", "evaluable", "not_evaluable_mechanism"),
        field=field,
    )
    status = str(value["status"])
    evaluable = as_bool(value["evaluable"], field=f"{field}.evaluable")
    mechanism = str(value["not_evaluable_mechanism"])
    if not applicable:
        require(
            status == NON_OVERALL_IMPROVEMENT_STATUS
            and not evaluable
            and mechanism == NON_OVERALL_IMPROVEMENT_STATUS,
            "HMSO01R_B_NON_DNN_STATUS_INCONSISTENT",
            field,
        )
    elif evaluable:
        require(
            status == "EVALUABLE" and mechanism == "",
            "HMSO01R_B_NON_DNN_STATUS_INCONSISTENT",
            field,
        )
    else:
        require(
            status in NON_DNN_NE_MECHANISMS and mechanism == status,
            "HMSO01R_B_NON_DNN_STATUS_INCONSISTENT",
            field,
        )
    return {"status": status, "evaluable": evaluable, "not_evaluable_mechanism": mechanism}


def require_value_status_consistency(value: Any, status_leaf: Mapping[str, Any], *, field: str) -> None:
    parsed = optional_float(value, field=field)
    require(
        (parsed is not None) == bool(status_leaf["evaluable"]),
        "HMSO01R_B_NON_DNN_VALUE_STATUS_MISMATCH",
        field,
    )


def csv_status_leaf(
    row: Mapping[str, Any],
    *,
    prefix: str,
    field: str,
    applicable: bool = True,
) -> dict[str, Any]:
    status_key = f"{prefix}_status" if prefix else "status"
    evaluable_key = f"{prefix}_evaluable" if prefix else "evaluable"
    mechanism_key = f"{prefix}_not_evaluable_mechanism" if prefix else "not_evaluable_mechanism"
    for key in (status_key, evaluable_key, mechanism_key):
        require(key in row, "HMSO01R_B_NON_DNN_STATUS_SCHEMA_FAILURE", f"{field}:{key}")
    return parse_status_leaf(
        {
            "status": row[status_key],
            "evaluable": row[evaluable_key],
            "not_evaluable_mechanism": row[mechanism_key],
        },
        field=field,
        applicable=applicable,
    )


def require_status_leaf_equal(left: Mapping[str, Any], right: Mapping[str, Any], *, field: str) -> None:
    require(dict(left) == dict(right), "HMSO01R_B_NON_DNN_STATUS_CROSS_ARTIFACT_MISMATCH", field)


def parse_non_dnn_status_tree(value: Any, *, field: str) -> dict[str, Any]:
    """Validate the exact summary status tree for every non-DNN primitive/bound."""

    require(isinstance(value, Mapping), "HMSO01R_B_NON_DNN_STATUS_SCHEMA_FAILURE", field)
    require_exact_keys(
        value,
        ("conditional_variance", "oracle_nrmse", "mean_baseline_nrmse", "improvement", "coverage"),
        field=field,
    )

    def scoped(metric: str, *, extra: Sequence[str] = ()) -> dict[str, Any]:
        record = value[metric]
        require(isinstance(record, Mapping), "HMSO01R_B_NON_DNN_STATUS_SCHEMA_FAILURE", f"{field}.{metric}")
        require_exact_keys(record, ("overall", "family", "fold", *extra), field=f"{field}.{metric}")
        families = record["family"]
        folds = record["fold"]
        require(isinstance(families, Mapping), "HMSO01R_B_NON_DNN_STATUS_SCHEMA_FAILURE", f"{field}.{metric}.family")
        require(isinstance(folds, Mapping), "HMSO01R_B_NON_DNN_STATUS_SCHEMA_FAILURE", f"{field}.{metric}.fold")
        require_exact_keys(families, FAMILIES, field=f"{field}.{metric}.family")
        fold_keys = tuple(f"FOLD_{fold}" for fold in FOLDS)
        require_exact_keys(folds, fold_keys, field=f"{field}.{metric}.fold")
        parsed: dict[str, Any] = {
            "overall": parse_status_leaf(record["overall"], field=f"{field}.{metric}.overall"),
            "family": {
                family: parse_status_leaf(families[family], field=f"{field}.{metric}.family.{family}")
                for family in FAMILIES
            },
            "fold": {
                fold_key: parse_status_leaf(folds[fold_key], field=f"{field}.{metric}.fold.{fold_key}")
                for fold_key in fold_keys
            },
        }
        return parsed

    conditional = scoped("conditional_variance", extra=("simultaneous_bound",))
    conditional["simultaneous_bound"] = parse_status_leaf(
        value["conditional_variance"]["simultaneous_bound"],
        field=f"{field}.conditional_variance.simultaneous_bound",
    )
    oracle = scoped("oracle_nrmse", extra=("simultaneous_bound", "family_simultaneous_bound"))
    oracle["simultaneous_bound"] = parse_status_leaf(
        value["oracle_nrmse"]["simultaneous_bound"],
        field=f"{field}.oracle_nrmse.simultaneous_bound",
    )
    family_bounds = value["oracle_nrmse"]["family_simultaneous_bound"]
    require(isinstance(family_bounds, Mapping), "HMSO01R_B_NON_DNN_STATUS_SCHEMA_FAILURE", f"{field}.oracle_nrmse.family_simultaneous_bound")
    require_exact_keys(family_bounds, FAMILIES, field=f"{field}.oracle_nrmse.family_simultaneous_bound")
    oracle["family_simultaneous_bound"] = {
        family: parse_status_leaf(
            family_bounds[family],
            field=f"{field}.oracle_nrmse.family_simultaneous_bound.{family}",
        )
        for family in FAMILIES
    }
    baseline = scoped("mean_baseline_nrmse")
    coverage = scoped("coverage")
    improvement_record = value["improvement"]
    require(isinstance(improvement_record, Mapping), "HMSO01R_B_NON_DNN_STATUS_SCHEMA_FAILURE", f"{field}.improvement")
    require_exact_keys(improvement_record, ("overall", "simultaneous_bound"), field=f"{field}.improvement")
    improvement = {
        "overall": parse_status_leaf(improvement_record["overall"], field=f"{field}.improvement.overall"),
        "simultaneous_bound": parse_status_leaf(
            improvement_record["simultaneous_bound"],
            field=f"{field}.improvement.simultaneous_bound",
        ),
    }
    return {
        "conditional_variance": conditional,
        "oracle_nrmse": oracle,
        "mean_baseline_nrmse": baseline,
        "improvement": improvement,
        "coverage": coverage,
    }


def validate_bound_rows(
    candidate_rows: Sequence[Mapping[str, Any]],
    all_rows: Sequence[Mapping[str, Any]],
) -> dict[tuple[str, str], Mapping[str, Any]]:
    candidate_index = unique_rows(candidate_rows, ("metric_family", "component"), label="candidate bounds")
    all_index = unique_rows(all_rows, ("metric_family", "component"), label="all bounds")
    candidate_families = {
        "ABSOLUTE_SS_CANDIDATE_C",
        "ABSOLUTE_MS_CANDIDATE_C",
        "PAIRED_CANDIDATE_C_RATIO",
    }
    non_dnn_families = {
        *(f"ABSOLUTE_{arm}_{metric}" for arm in ARMS for metric in ("conditional_variance", "oracle_nrmse", "improvement")),
        *(f"ABSOLUTE_{arm}_oracle_nrmse_family_{family}" for arm in ARMS for family in FAMILIES),
        "PAIRED_CONDITIONAL_VARIANCE_RATIO",
        "PAIRED_ORACLE_NRMSE_RATIO",
    }
    expected_candidate = {(family, component) for family in candidate_families for component in COMPONENTS}
    expected_all = {(family, component) for family in candidate_families | non_dnn_families for component in COMPONENTS}
    require(set(candidate_index) == expected_candidate, "HMSO01R_B_BOUND_ROWSET_FAILURE", "candidate")
    require(set(all_index) == expected_all, "HMSO01R_B_BOUND_ROWSET_FAILURE", "all")
    for identity, row in candidate_index.items():
        require(dict(row) == dict(all_index[identity]), "HMSO01R_B_CANDIDATE_BOUND_ARTIFACT_MISMATCH", str(identity))
    for (family, component), row in all_index.items():
        expected_direction = "lower" if family.endswith("_improvement") else "upper"
        expected_scales = {"log"} if family.startswith("PAIRED_") else {"identity", "linear"}
        require(str(first(row, ("direction",), field=f"bound.{family}.{component}.direction")).lower() == expected_direction, "HMSO01R_B_BOUND_SCHEMA_FAILURE", f"{family}:{component}:direction")
        require(str(first(row, ("scale",), field=f"bound.{family}.{component}.scale")).lower() in expected_scales, "HMSO01R_B_BOUND_SCHEMA_FAILURE", f"{family}:{component}:scale")
        require(first(row, ("multiplicity_scope",), field=f"bound.{family}.{component}.scope") == "THREE_PRIMARY_COMPONENTS_WITHIN_EACH_METRIC_FAMILY", "HMSO01R_B_BOUND_SCHEMA_FAILURE", f"{family}:{component}:scope")
        status = normalize_zero_status(first(row, ("status",), field=f"bound.{family}.{component}.status"))
        point = optional_float(first(row, ("point_estimate",), field=f"bound.{family}.{component}.point"), field=f"bound.{family}.{component}.point")
        bound = optional_float(first(row, ("simultaneous_bound",), field=f"bound.{family}.{component}.bound"), field=f"bound.{family}.{component}.bound")
        valid = as_int(first(row, ("valid_replicates",), field=f"bound.{family}.{component}.valid"), field=f"bound.{family}.{component}.valid")
        degenerate = as_int(first(row, ("degenerate_replicates",), field=f"bound.{family}.{component}.degenerate"), field=f"bound.{family}.{component}.degenerate")
        require(valid >= 0 and degenerate >= 0 and valid + degenerate == 10000, "HMSO01R_B_BOUND_REPLICATE_COUNT_FAILURE", f"{family}:{component}")
        if status == "EVALUABLE":
            require(point is not None and bound is not None and valid >= 2 and degenerate <= 200, "HMSO01R_B_BOUND_EVALUABILITY_FAILURE", f"{family}:{component}")
            as_float(first(row, ("bootstrap_standard_error",), field=f"bound.{family}.{component}.se"), field=f"bound.{family}.{component}.se")
            as_float(first(row, ("critical_value",), field=f"bound.{family}.{component}.critical"), field=f"bound.{family}.{component}.critical")
        elif status == EXACT_ZERO_MS_STATUS:
            require(family == "PAIRED_CANDIDATE_C_RATIO" and point == 0.0 and bound == 0.0, "HMSO01R_B_EXACT_ZERO_BOUND_FAILURE", component)
        else:
            require("NOT_EVALUABLE" in str(status), "HMSO01R_B_BOUND_STATUS_FAILURE", f"{family}:{component}:{status}")
            if family in non_dnn_families:
                require(
                    status in NON_DNN_NE_MECHANISMS,
                    "HMSO01R_B_NON_DNN_STATUS_INCONSISTENT",
                    f"bound:{family}:{component}:{status}",
                )
    return all_index


def validate_metric_artifacts(
    summary: Mapping[str, Any],
    division_records: Mapping[str, Any],
    parsed_csvs: Mapping[str, Sequence[Mapping[str, Any]]],
    coverage_rows: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Independently cross-bind CSVs, summary primitives, bounds, and gates."""

    path = "06_experiments/hmso01r_b/"
    candidate_by_arm = {
        "SS": unique_rows(parsed_csvs[path + "ss_candidate_c_dnn_metrics.csv"], ("component",), label="SS Candidate C"),
        "MS": unique_rows(parsed_csvs[path + "ms_candidate_c_dnn_metrics.csv"], ("component",), label="MS Candidate C"),
    }
    paired_candidate = unique_rows(parsed_csvs[path + "candidate_c_paired_rescue_metrics.csv"], ("component",), label="paired Candidate C")
    cvar_by_arm = {
        "SS": unique_rows(parsed_csvs[path + "ss_conditional_variance_metrics.csv"], ("component", "scope", "scope_id"), label="SS CVAR"),
        "MS": unique_rows(parsed_csvs[path + "ms_conditional_variance_metrics.csv"], ("component", "scope", "scope_id"), label="MS CVAR"),
    }
    oracle_by_arm = {
        "SS": unique_rows(parsed_csvs[path + "ss_oracle_metrics.csv"], ("component", "scope", "scope_id"), label="SS oracle"),
        "MS": unique_rows(parsed_csvs[path + "ms_oracle_metrics.csv"], ("component", "scope", "scope_id"), label="MS oracle"),
    }
    coverage_index = unique_rows(coverage_rows, ("arm", "scope", "scope_id"), label="coverage")
    rescue_index = unique_rows(parsed_csvs[path + "paired_non_dnn_rescue_metrics.csv"], ("component", "requirement"), label="paired non-DNN")
    verdict_index = unique_rows(parsed_csvs[path + "component_verdicts.csv"], ("component",), label="component verdicts")
    bounds = validate_bound_rows(
        parsed_csvs[path + "candidate_c_bootstrap_bounds.csv"],
        parsed_csvs[path + "bootstrap_simultaneous_bounds.csv"],
    )

    expected_scopes = {("OVERALL", "ALL"), *( ("FAMILY", family) for family in FAMILIES), *( ("FOLD", f"FOLD_{fold}") for fold in FOLDS)}
    require(all(set(index) == {(component, scope, scope_id) for component in COMPONENTS for scope, scope_id in expected_scopes} for index in cvar_by_arm.values()), "HMSO01R_B_CVAR_ROWSET_FAILURE")
    require(all(set(index) == {(component, scope, scope_id) for component in COMPONENTS for scope, scope_id in expected_scopes} for index in oracle_by_arm.values()), "HMSO01R_B_ORACLE_ROWSET_FAILURE")
    require(set(coverage_index) == {(arm, scope, scope_id) for arm in ARMS for scope, scope_id in expected_scopes}, "HMSO01R_B_COVERAGE_ROWSET_FAILURE")
    require(all(set(index) == {(component,) for component in COMPONENTS} for index in candidate_by_arm.values()), "HMSO01R_B_CANDIDATE_C_ROWSET_FAILURE")
    require(set(paired_candidate) == {(component,) for component in COMPONENTS}, "HMSO01R_B_CANDIDATE_C_ROWSET_FAILURE", "paired")
    require(set(verdict_index) == {(component,) for component in COMPONENTS}, "HMSO01R_B_COMPONENT_VERDICT_ROWSET_FAILURE")
    for arm in ARMS:
        for component in COMPONENTS:
            for scope, scope_id in expected_scopes:
                cvar_row = cvar_by_arm[arm][(component, scope, scope_id)]
                require(
                    str(first(cvar_row, ("arm",), field=f"cvar csv {arm}.{component}.{scope_id}.arm")).upper() == arm,
                    "HMSO01R_B_CVAR_CSV_ARM_FAILURE",
                    f"{arm}:{component}:{scope_id}",
                )
                cvar_status = csv_status_leaf(
                    cvar_row,
                    prefix="",
                    field=f"cvar csv {arm}.{component}.{scope_id}.status",
                )
                require_value_status_consistency(
                    cvar_row["conditional_variance"],
                    cvar_status,
                    field=f"cvar csv {arm}.{component}.{scope_id}",
                )
                oracle_row = oracle_by_arm[arm][(component, scope, scope_id)]
                require(
                    str(first(oracle_row, ("arm",), field=f"oracle csv {arm}.{component}.{scope_id}.arm")).upper() == arm,
                    "HMSO01R_B_ORACLE_CSV_ARM_FAILURE",
                    f"{arm}:{component}:{scope_id}",
                )
                oracle_status = csv_status_leaf(
                    oracle_row,
                    prefix="oracle",
                    field=f"oracle csv {arm}.{component}.{scope_id}.oracle_status",
                )
                baseline_status = csv_status_leaf(
                    oracle_row,
                    prefix="mean_baseline",
                    field=f"oracle csv {arm}.{component}.{scope_id}.baseline_status",
                )
                improvement_status = csv_status_leaf(
                    oracle_row,
                    prefix="improvement",
                    field=f"oracle csv {arm}.{component}.{scope_id}.improvement_status",
                    applicable=scope == "OVERALL",
                )
                require_value_status_consistency(
                    oracle_row["oracle_nrmse"], oracle_status,
                    field=f"oracle csv {arm}.{component}.{scope_id}",
                )
                require_value_status_consistency(
                    oracle_row["mean_baseline_nrmse"], baseline_status,
                    field=f"baseline csv {arm}.{component}.{scope_id}",
                )
                require_value_status_consistency(
                    oracle_row["improvement_over_mean_baseline"], improvement_status,
                    field=f"improvement csv {arm}.{component}.{scope_id}",
                )
        for scope, scope_id in expected_scopes:
            coverage_row = coverage_index[(arm, scope, scope_id)]
            coverage_status = csv_status_leaf(
                coverage_row,
                prefix="",
                field=f"coverage csv {arm}.{scope_id}.status",
            )
            require_value_status_consistency(
                coverage_row["coverage"], coverage_status,
                field=f"coverage csv {arm}.{scope_id}",
            )
            require(as_bool(coverage_row["component_independent"], field=f"coverage csv {arm}.{scope_id}.component_independent"), "HMSO01R_B_COVERAGE_SEMANTICS_FAILURE", f"{arm}:{scope_id}:component-independent")
            require(not as_bool(coverage_row["can_substitute_for_identifiability"], field=f"coverage csv {arm}.{scope_id}.substitute"), "HMSO01R_B_COVERAGE_SEMANTICS_FAILURE", f"{arm}:{scope_id}:substitution")

    expected_absolute_keys = (
        "candidate_c_point", "candidate_c_simultaneous_ucb",
        "conditional_variance_point", "conditional_variance_simultaneous_ucb",
        "oracle_nrmse_point", "oracle_nrmse_simultaneous_ucb",
        "improvement_point", "improvement_simultaneous_lcb",
        "every_family_nrmse_point", "every_family_nrmse_simultaneous_ucb",
        "coverage_overall", "coverage_every_family", "all_six_folds_valid",
    )
    expected_relative_keys = (
        "candidate_c_point_ratio", "candidate_c_simultaneous_ratio_ucb",
        "conditional_variance_point_ratio", "conditional_variance_simultaneous_ratio_ucb",
        "oracle_nrmse_point_ratio", "oracle_nrmse_simultaneous_ratio_ucb",
        "candidate_c_nonworsening", "worst_family_guard", "coverage_guard",
        "no_fold_three_effect_reversal",
    )
    require(set(rescue_index) == {(component, requirement) for component in COMPONENTS for requirement in expected_relative_keys}, "HMSO01R_B_PAIRED_RESCUE_ROWSET_FAILURE")

    _, summary_components = verdict_components(summary)
    derived: dict[str, dict[str, Any]] = {}
    for component in COMPONENTS:
        arm_values: dict[str, dict[str, Any]] = {}
        for arm in ARMS:
            block = metric_block(summary, arm, component)
            row = candidate_by_arm[arm][(component,)]
            require(str(first(row, ("arm",), field=f"candidate csv {arm}.{component}.arm")).upper() == arm, "HMSO01R_B_CANDIDATE_C_CSV_ARM_FAILURE", f"{arm}:{component}")
            require(
                str(first(row, ("scope",), field=f"candidate csv {arm}.{component}.scope")).upper() == "OVERALL"
                and str(first(row, ("scope_id",), field=f"candidate csv {arm}.{component}.scope_id")).upper() == "ALL",
                "HMSO01R_B_CANDIDATE_C_CSV_SCOPE_FAILURE",
                f"{arm}:{component}",
            )
            for key in ("candidate_c_d", "candidate_c_wn", "candidate_c_wb", "candidate_c_simultaneous_ucb"):
                require_same_number(first(row, (key,), field=f"candidate csv {arm}.{component}.{key}"), first(block, (key,), field=f"summary {arm}.{component}.{key}"), field=f"candidate:{arm}:{component}:{key}")
            row_status = normalize_zero_status(first(row, ("candidate_c_status",), field=f"candidate csv {arm}.{component}.status"))
            summary_status = normalize_zero_status(first(block, ("candidate_c_status",), field=f"summary {arm}.{component}.status"))
            require(row_status == summary_status, "HMSO01R_B_CANDIDATE_C_STATUS_INCONSISTENT", f"{arm}:{component}")
            recorded_evaluable = as_bool(first(block, ("candidate_c_evaluable",), field=f"summary {arm}.{component}.evaluable"), field=f"summary {arm}.{component}.evaluable")
            require(as_bool(first(row, ("candidate_c_evaluable",), field=f"candidate csv {arm}.{component}.evaluable"), field=f"candidate csv {arm}.{component}.evaluable") == recorded_evaluable, "HMSO01R_B_CANDIDATE_C_CSV_MISMATCH", f"{arm}:{component}:evaluable")
            bound_row = bounds[(f"ABSOLUTE_{arm}_CANDIDATE_C", component)]
            bound_status = normalize_zero_status(first(bound_row, ("status",), field=f"candidate bound {arm}.{component}.status"))
            if "candidate_c_bound_status" in row:
                require(normalize_zero_status(row["candidate_c_bound_status"]) == bound_status, "HMSO01R_B_CANDIDATE_C_BOUND_STATUS_MISMATCH", f"{arm}:{component}")
            require_same_number(block["candidate_c_d"], bound_row["point_estimate"], field=f"candidate-bound:{arm}:{component}:point")
            require_same_number(block["candidate_c_simultaneous_ucb"], bound_row["simultaneous_bound"], field=f"candidate-bound:{arm}:{component}:ucb")
            audit_row = division_records["arms"][(arm, component)]
            wb = optional_float(block["candidate_c_wb"], field=f"summary {arm}.{component}.wb")
            point = optional_float(block["candidate_c_d"], field=f"summary {arm}.{component}.point")
            ucb = optional_float(block["candidate_c_simultaneous_ucb"], field=f"summary {arm}.{component}.ucb")
            denominator_positive = as_bool(first(audit_row, ("point_aggregate_denominator_positive",), field=f"audit {arm}.{component}.denominator"), field=f"audit {arm}.{component}.denominator")
            require((wb is not None and wb > 0) == denominator_positive, "HMSO01R_B_CANDIDATE_C_DENOMINATOR_FAILURE", f"{arm}:{component}")
            valid = as_int(first(audit_row, ("evaluable_replicate_count",), field=f"audit {arm}.{component}.valid"), field=f"audit {arm}.{component}.valid")
            degenerate = as_int(first(audit_row, ("degenerate_aggregate_denominator_replicate_count",), field=f"audit {arm}.{component}.degenerate"), field=f"audit {arm}.{component}.degenerate")
            expected_evaluable = bool(denominator_positive and point is not None and ucb is not None and valid >= 2 and degenerate <= 200 and bound_status == "EVALUABLE")
            require(recorded_evaluable == expected_evaluable, "HMSO01R_B_CANDIDATE_C_EVALUABILITY_RECOMPUTATION_FAILURE", f"{arm}:{component}")
            require(as_bool(first(audit_row, ("candidate_c_evaluable",), field=f"audit {arm}.{component}.evaluable"), field=f"audit {arm}.{component}.evaluable") == expected_evaluable, "HMSO01R_B_CANDIDATE_C_EVALUABILITY_RECOMPUTATION_FAILURE", f"audit:{arm}:{component}")
            if not denominator_positive:
                require(point is None and summary_status == CA_ZERO_STATUS, "HMSO01R_B_ZERO_AGGREGATE_STATUS_FAILURE", f"{arm}:{component}")
                require(first(block, ("candidate_c_source_alias",), field=f"summary {arm}.{component}.source_alias") == CURRENT_ZERO_ALIAS, "HMSO01R_B_ZERO_STATUS_ALIAS_FAILURE", f"{arm}:{component}:summary")
                require(first(row, ("candidate_c_source_alias",), field=f"candidate csv {arm}.{component}.source_alias") == CURRENT_ZERO_ALIAS, "HMSO01R_B_ZERO_STATUS_ALIAS_FAILURE", f"{arm}:{component}:csv")
            elif not expected_evaluable:
                require(point is not None and "NOT_EVALUABLE" in str(summary_status), "HMSO01R_B_CANDIDATE_C_STATUS_INCONSISTENT", f"{arm}:{component}")
            else:
                require(summary_status == "EVALUABLE", "HMSO01R_B_CANDIDATE_C_STATUS_INCONSISTENT", f"{arm}:{component}")
            candidate_gate = bool(expected_evaluable and point is not None and ucb is not None and point < 1.0 and ucb < 1.0)
            require(as_bool(first(block, ("candidate_c_absolute_gate_pass",), field=f"summary {arm}.{component}.gate"), field=f"summary {arm}.{component}.gate") == candidate_gate, "HMSO01R_B_CANDIDATE_C_ABSOLUTE_GATE_INCONSISTENT", f"{arm}:{component}")
            require(as_bool(first(row, ("candidate_c_absolute_gate_pass",), field=f"candidate csv {arm}.{component}.gate"), field=f"candidate csv {arm}.{component}.gate") == candidate_gate, "HMSO01R_B_CANDIDATE_C_CSV_MISMATCH", f"{arm}:{component}:gate")
            folds = finite_vector(first(block, ("candidate_c_point_fold",), field=f"summary {arm}.{component}.folds"), 6, field=f"summary {arm}.{component}.folds")
            require(sum(value is not None for value in folds) == division_records["fold_divisions"][(arm, component)], "HMSO01R_B_CANDIDATE_C_FOLD_DIVISION_COUNT_FAILURE", f"{arm}:{component}")
            arm_values[arm] = {"block": block, "point": point, "ucb": ucb, "evaluable": expected_evaluable, "gate": candidate_gate, "folds": folds}

        paired = paired_block(summary, component)
        paired_row = paired_candidate[(component,)]
        for key in ("candidate_c_ratio", "candidate_c_ratio_simultaneous_ucb"):
            require_same_number(first(paired_row, (key,), field=f"paired csv {component}.{key}"), first(paired, (key,), field=f"paired summary {component}.{key}"), field=f"paired-candidate:{component}:{key}")
        paired_status = normalize_zero_status(first(paired, ("candidate_c_status",), field=f"paired summary {component}.status"))
        require(normalize_zero_status(first(paired_row, ("candidate_c_status",), field=f"paired csv {component}.status")) == paired_status, "HMSO01R_B_CANDIDATE_C_STATUS_INCONSISTENT", f"paired:{component}")
        pair_bound = bounds[("PAIRED_CANDIDATE_C_RATIO", component)]
        require_same_number(paired["candidate_c_ratio"], pair_bound["point_estimate"], field=f"paired-bound:{component}:point")
        require_same_number(paired["candidate_c_ratio_simultaneous_ucb"], pair_bound["simultaneous_bound"], field=f"paired-bound:{component}:ucb")
        ss_d, ms_d = arm_values["SS"]["point"], arm_values["MS"]["point"]
        pair_audit = division_records["paired"][component]
        pair_valid = as_int(first(pair_audit, ("evaluable_replicate_count",), field=f"pair audit {component}.valid"), field=f"pair audit {component}.valid")
        point_ratio_evaluable = bool(arm_values["SS"]["evaluable"] and arm_values["MS"]["evaluable"] and ss_d is not None and ss_d > 0)
        require(as_bool(first(pair_audit, ("point_ratio_evaluable",), field=f"pair audit {component}.point"), field=f"pair audit {component}.point") == point_ratio_evaluable, "HMSO01R_B_CANDIDATE_C_PAIRED_AUDIT_MISMATCH", f"{component}:point")
        expected_ratio = ms_d / ss_d if point_ratio_evaluable and ms_d is not None else None
        require_same_number(paired["candidate_c_ratio"], expected_ratio, field=f"paired-candidate:{component}:derived-ratio")
        exact_zero = bool(point_ratio_evaluable and expected_ratio == 0.0 and paired_status == EXACT_ZERO_MS_STATUS)
        require(
            as_bool(
                first(paired, ("candidate_c_exact_zero_ms_dominance",), field=f"paired summary {component}.exact_zero"),
                field=f"paired summary {component}.exact_zero",
            )
            == exact_zero,
            "HMSO01R_B_EXACT_ZERO_BOUND_FAILURE",
            f"summary:{component}",
        )
        require(
            as_bool(
                first(paired_row, ("candidate_c_exact_zero_ms_dominance",), field=f"paired csv {component}.exact_zero"),
                field=f"paired csv {component}.exact_zero",
            )
            == exact_zero,
            "HMSO01R_B_EXACT_ZERO_BOUND_FAILURE",
            f"csv:{component}",
        )
        pair_bound_status = str(first(pair_bound, ("status",), field=f"paired bound {component}.status"))
        expected_pair_evaluable = bool(point_ratio_evaluable and pair_valid >= 2 and 10000 - pair_valid <= 200 and (pair_bound_status == "EVALUABLE" or exact_zero))
        recorded_pair_evaluable = as_bool(first(paired, ("candidate_c_evaluable",), field=f"paired summary {component}.evaluable"), field=f"paired summary {component}.evaluable")
        require(recorded_pair_evaluable == expected_pair_evaluable, "HMSO01R_B_CANDIDATE_C_EVALUABILITY_RECOMPUTATION_FAILURE", f"paired:{component}")
        require(as_bool(first(pair_audit, ("candidate_c_evaluable",), field=f"pair audit {component}.evaluable"), field=f"pair audit {component}.evaluable") == expected_pair_evaluable, "HMSO01R_B_CANDIDATE_C_PAIRED_AUDIT_MISMATCH", f"{component}:evaluable")
        require(normalize_zero_status(first(pair_audit, ("status",), field=f"pair audit {component}.status")) == paired_status, "HMSO01R_B_CANDIDATE_C_PAIRED_AUDIT_MISMATCH", f"{component}:status")
        require(as_bool(first(paired_row, ("candidate_c_evaluable",), field=f"paired csv {component}.evaluable"), field=f"paired csv {component}.evaluable") == expected_pair_evaluable, "HMSO01R_B_CANDIDATE_C_CSV_MISMATCH", f"paired:{component}:evaluable")
        ratio = optional_float(paired["candidate_c_ratio"], field=f"paired summary {component}.ratio")
        ratio_ucb = optional_float(paired["candidate_c_ratio_simultaneous_ucb"], field=f"paired summary {component}.ucb")
        candidate_relative_gate = bool(expected_pair_evaluable and ratio is not None and ratio_ucb is not None and ratio <= 0.80 and ratio_ucb <= 0.90)
        require(as_bool(first(paired, ("candidate_c_relative_gate_pass",), field=f"paired summary {component}.gate"), field=f"paired summary {component}.gate") == candidate_relative_gate, "HMSO01R_B_CANDIDATE_C_RELATIVE_GATE_INCONSISTENT", component)
        require(as_bool(first(paired_row, ("candidate_c_relative_gate_pass",), field=f"paired csv {component}.gate"), field=f"paired csv {component}.gate") == candidate_relative_gate, "HMSO01R_B_CANDIDATE_C_CSV_MISMATCH", f"paired:{component}:gate")

        non_dnn: dict[str, dict[str, Any]] = {}
        for arm in ARMS:
            block = arm_values[arm]["block"]
            status_tree = parse_non_dnn_status_tree(
                first(block, ("non_dnn_status",), field=f"summary {arm}.{component}.non_dnn_status"),
                field=f"summary {arm}.{component}.non_dnn_status",
            )
            for scope, scope_id in expected_scopes:
                status_scope = "overall" if scope == "OVERALL" else scope.lower()
                status_key = None if scope == "OVERALL" else scope_id
                for metric, index, prefix in (
                    ("conditional_variance", cvar_by_arm[arm], ""),
                    ("oracle_nrmse", oracle_by_arm[arm], "oracle"),
                    ("mean_baseline_nrmse", oracle_by_arm[arm], "mean_baseline"),
                ):
                    summary_leaf = status_tree[metric][status_scope]
                    if status_key is not None:
                        summary_leaf = summary_leaf[status_key]
                    require_status_leaf_equal(
                        summary_leaf,
                        csv_status_leaf(
                            index[(component, scope, scope_id)],
                            prefix=prefix,
                            field=f"{metric} csv {arm}.{component}.{scope_id}.status",
                        ),
                        field=f"{metric}:{arm}:{component}:{scope_id}:status",
                    )
                coverage_summary_leaf = status_tree["coverage"][status_scope]
                if status_key is not None:
                    coverage_summary_leaf = coverage_summary_leaf[status_key]
                require_status_leaf_equal(
                    coverage_summary_leaf,
                    csv_status_leaf(
                        coverage_index[(arm, scope, scope_id)],
                        prefix="",
                        field=f"coverage csv {arm}.{scope_id}.status",
                    ),
                    field=f"coverage:{arm}:{component}:{scope_id}:status",
                )
                if scope == "OVERALL":
                    require_status_leaf_equal(
                        status_tree["improvement"]["overall"],
                        csv_status_leaf(
                            oracle_by_arm[arm][(component, scope, scope_id)],
                            prefix="improvement",
                            field=f"improvement csv {arm}.{component}.status",
                        ),
                        field=f"improvement:{arm}:{component}:status",
                    )

            def bound_leaf(family: str) -> dict[str, Any]:
                bound_record = bounds[(family, component)]
                bound_status = str(bound_record["status"])
                return parse_status_leaf(
                    {
                        "status": bound_status,
                        "evaluable": bound_status == "EVALUABLE",
                        "not_evaluable_mechanism": "" if bound_status == "EVALUABLE" else bound_status,
                    },
                    field=f"bound status {family}.{component}",
                )

            require_status_leaf_equal(
                status_tree["conditional_variance"]["simultaneous_bound"],
                bound_leaf(f"ABSOLUTE_{arm}_conditional_variance"),
                field=f"bound-status:{arm}:{component}:conditional_variance",
            )
            require_status_leaf_equal(
                status_tree["oracle_nrmse"]["simultaneous_bound"],
                bound_leaf(f"ABSOLUTE_{arm}_oracle_nrmse"),
                field=f"bound-status:{arm}:{component}:oracle_nrmse",
            )
            require_status_leaf_equal(
                status_tree["improvement"]["simultaneous_bound"],
                bound_leaf(f"ABSOLUTE_{arm}_improvement"),
                field=f"bound-status:{arm}:{component}:improvement",
            )
            for family in FAMILIES:
                require_status_leaf_equal(
                    status_tree["oracle_nrmse"]["family_simultaneous_bound"][family],
                    bound_leaf(f"ABSOLUTE_{arm}_oracle_nrmse_family_{family}"),
                    field=f"bound-status:{arm}:{component}:oracle-family:{family}",
                )
            cvar_overall = cvar_by_arm[arm][(component, "OVERALL", "ALL")]
            oracle_overall = oracle_by_arm[arm][(component, "OVERALL", "ALL")]
            require(str(first(cvar_overall, ("arm",), field=f"cvar {arm}.{component}.arm")).upper() == arm, "HMSO01R_B_CVAR_CSV_ARM_FAILURE", f"{arm}:{component}")
            require(str(first(oracle_overall, ("arm",), field=f"oracle {arm}.{component}.arm")).upper() == arm, "HMSO01R_B_ORACLE_CSV_ARM_FAILURE", f"{arm}:{component}")
            require_same_number(block["conditional_variance"], cvar_overall["conditional_variance"], field=f"cvar:{arm}:{component}:overall")
            require_same_number(block["oracle_nrmse"], oracle_overall["oracle_nrmse"], field=f"oracle:{arm}:{component}:overall")
            require_same_number(block["baseline_nrmse"], oracle_overall["mean_baseline_nrmse"], field=f"baseline:{arm}:{component}:overall")
            require_same_number(block["improvement"], oracle_overall["improvement_over_mean_baseline"], field=f"improvement:{arm}:{component}:overall")
            oracle_point = optional_float(block["oracle_nrmse"], field=f"summary {arm}.{component}.oracle-for-improvement")
            baseline_point = optional_float(block["baseline_nrmse"], field=f"summary {arm}.{component}.baseline-for-improvement")
            expected_improvement = (
                1.0 - oracle_point / baseline_point
                if oracle_point is not None and baseline_point is not None and baseline_point > 0.0
                else None
            )
            require_same_number(
                block["improvement"],
                expected_improvement,
                field=f"improvement-derived:{arm}:{component}",
            )
            selected = first(block, ("selected_oracles_by_fold",), field=f"summary {arm}.{component}.selected")
            require(isinstance(selected, Mapping) and set(map(str, selected)) == {str(fold) for fold in FOLDS}, "HMSO01R_B_ORACLE_SELECTION_SCHEMA_FAILURE", f"{arm}:{component}")
            for scope, scope_id in expected_scopes:
                oracle_row = oracle_by_arm[arm][(component, scope, scope_id)]
                require(json_cell(oracle_row["selected_oracles_by_outer_fold"], field=f"oracle selected {arm}.{component}.{scope_id}") == selected, "HMSO01R_B_ORACLE_SELECTION_CSV_MISMATCH", f"{arm}:{component}:{scope_id}")
            family_nrmse = finite_map(block["family_nrmse"], FAMILIES, field=f"summary {arm}.{component}.family_nrmse")
            family_ucb = finite_map(block["family_nrmse_simultaneous_ucb"], FAMILIES, field=f"summary {arm}.{component}.family_ucb")
            coverage_family = finite_map(block["coverage_family"], FAMILIES, field=f"summary {arm}.{component}.coverage_family")
            coverage_fold = finite_map(block["coverage_fold"], tuple(f"FOLD_{fold}" for fold in FOLDS), field=f"summary {arm}.{component}.coverage_fold")
            for value_key, status_metric in (
                ("conditional_variance", "conditional_variance"),
                ("oracle_nrmse", "oracle_nrmse"),
                ("baseline_nrmse", "mean_baseline_nrmse"),
                ("improvement", "improvement"),
                ("coverage", "coverage"),
            ):
                require_value_status_consistency(
                    block[value_key],
                    status_tree[status_metric]["overall"],
                    field=f"summary-value-status:{arm}:{component}:{value_key}",
                )
            for value_key, status_metric in (
                ("conditional_variance_simultaneous_ucb", "conditional_variance"),
                ("oracle_nrmse_simultaneous_ucb", "oracle_nrmse"),
                ("improvement_simultaneous_lcb", "improvement"),
            ):
                require_value_status_consistency(
                    block[value_key],
                    status_tree[status_metric]["simultaneous_bound"],
                    field=f"summary-value-status:{arm}:{component}:{value_key}",
                )
            cvar_folds, oracle_folds = [], []
            for fold in FOLDS:
                fold_id = f"FOLD_{fold}"
                cvar_folds.append(optional_float(cvar_by_arm[arm][(component, "FOLD", fold_id)]["conditional_variance"], field=f"cvar {arm}.{component}.{fold_id}"))
                oracle_folds.append(optional_float(oracle_by_arm[arm][(component, "FOLD", fold_id)]["oracle_nrmse"], field=f"oracle {arm}.{component}.{fold_id}"))
                require_same_number(coverage_fold[fold_id], coverage_index[(arm, "FOLD", fold_id)]["coverage"], field=f"coverage:{arm}:{component}:{fold_id}")
            for family in FAMILIES:
                require_value_status_consistency(
                    family_nrmse[family],
                    status_tree["oracle_nrmse"]["family"][family],
                    field=f"summary-value-status:{arm}:{component}:family_nrmse:{family}",
                )
                require_value_status_consistency(
                    family_ucb[family],
                    status_tree["oracle_nrmse"]["family_simultaneous_bound"][family],
                    field=f"summary-value-status:{arm}:{component}:family_ucb:{family}",
                )
                require_value_status_consistency(
                    coverage_family[family],
                    status_tree["coverage"]["family"][family],
                    field=f"summary-value-status:{arm}:{component}:coverage_family:{family}",
                )
                require_same_number(family_nrmse[family], oracle_by_arm[arm][(component, "FAMILY", family)]["oracle_nrmse"], field=f"oracle-family:{arm}:{component}:{family}")
                require_same_number(family_nrmse[family], bounds[(f"ABSOLUTE_{arm}_oracle_nrmse_family_{family}", component)]["point_estimate"], field=f"oracle-family-bound:{arm}:{component}:{family}:point")
                require_same_number(family_ucb[family], bounds[(f"ABSOLUTE_{arm}_oracle_nrmse_family_{family}", component)]["simultaneous_bound"], field=f"oracle-family-bound:{arm}:{component}:{family}")
                require_same_number(coverage_family[family], coverage_index[(arm, "FAMILY", family)]["coverage"], field=f"coverage-family:{arm}:{component}:{family}")
            for fold in FOLDS:
                fold_id = f"FOLD_{fold}"
                require_value_status_consistency(
                    coverage_fold[fold_id],
                    status_tree["coverage"]["fold"][fold_id],
                    field=f"summary-value-status:{arm}:{component}:coverage_fold:{fold_id}",
                )
            require_same_number(block["coverage"], coverage_index[(arm, "OVERALL", "ALL")]["coverage"], field=f"coverage:{arm}:{component}:overall")
            for key, family in (("conditional_variance_simultaneous_ucb", "conditional_variance"), ("oracle_nrmse_simultaneous_ucb", "oracle_nrmse"), ("improvement_simultaneous_lcb", "improvement")):
                require_same_number(block[key], bounds[(f"ABSOLUTE_{arm}_{family}", component)]["simultaneous_bound"], field=f"bound:{arm}:{component}:{family}")
            for key, family in (("conditional_variance", "conditional_variance"), ("oracle_nrmse", "oracle_nrmse"), ("improvement", "improvement")):
                require_same_number(block[key], bounds[(f"ABSOLUTE_{arm}_{family}", component)]["point_estimate"], field=f"bound-point:{arm}:{component}:{family}")
            non_dnn[arm] = {
                "cvar": optional_float(block["conditional_variance"], field=f"summary {arm}.{component}.cvar"),
                "cvar_ucb": optional_float(block["conditional_variance_simultaneous_ucb"], field=f"summary {arm}.{component}.cvar_ucb"),
                "oracle": optional_float(block["oracle_nrmse"], field=f"summary {arm}.{component}.oracle"),
                "oracle_ucb": optional_float(block["oracle_nrmse_simultaneous_ucb"], field=f"summary {arm}.{component}.oracle_ucb"),
                "baseline": optional_float(block["baseline_nrmse"], field=f"summary {arm}.{component}.baseline"),
                "improvement": optional_float(block["improvement"], field=f"summary {arm}.{component}.improvement"),
                "improvement_lcb": optional_float(block["improvement_simultaneous_lcb"], field=f"summary {arm}.{component}.improvement_lcb"),
                "family": family_nrmse, "family_ucb": family_ucb,
                "coverage": optional_float(block["coverage"], field=f"summary {arm}.{component}.coverage"),
                "coverage_family": coverage_family, "coverage_fold": coverage_fold,
                "cvar_folds": cvar_folds, "oracle_folds": oracle_folds,
                "status": status_tree,
            }

        cvar_ratio = optional_float(first(paired, ("conditional_variance_ratio",), field=f"paired {component}.cvar_ratio"), field=f"paired {component}.cvar_ratio")
        cvar_ratio_ucb = optional_float(first(paired, ("conditional_variance_ratio_simultaneous_ucb",), field=f"paired {component}.cvar_ucb"), field=f"paired {component}.cvar_ucb")
        oracle_ratio = optional_float(first(paired, ("oracle_nrmse_ratio",), field=f"paired {component}.oracle_ratio"), field=f"paired {component}.oracle_ratio")
        oracle_ratio_ucb = optional_float(first(paired, ("oracle_nrmse_ratio_simultaneous_ucb",), field=f"paired {component}.oracle_ucb"), field=f"paired {component}.oracle_ucb")
        cvar_ratio_status = first(paired, ("conditional_variance_ratio_status",), field=f"paired {component}.cvar_status")
        oracle_ratio_status = first(paired, ("oracle_nrmse_ratio_status",), field=f"paired {component}.oracle_status")
        require(cvar_ratio_status == bounds[("PAIRED_CONDITIONAL_VARIANCE_RATIO", component)]["status"], "HMSO01R_B_BOUND_STATUS_CROSS_ARTIFACT_MISMATCH", f"paired-cvar:{component}")
        require(oracle_ratio_status == bounds[("PAIRED_ORACLE_NRMSE_RATIO", component)]["status"], "HMSO01R_B_BOUND_STATUS_CROSS_ARTIFACT_MISMATCH", f"paired-oracle:{component}")
        require_same_number(cvar_ratio, bounds[("PAIRED_CONDITIONAL_VARIANCE_RATIO", component)]["point_estimate"], field=f"paired-cvar-bound:{component}:point")
        require_same_number(cvar_ratio_ucb, bounds[("PAIRED_CONDITIONAL_VARIANCE_RATIO", component)]["simultaneous_bound"], field=f"paired-cvar-bound:{component}:ucb")
        require_same_number(oracle_ratio, bounds[("PAIRED_ORACLE_NRMSE_RATIO", component)]["point_estimate"], field=f"paired-oracle-bound:{component}:point")
        require_same_number(oracle_ratio_ucb, bounds[("PAIRED_ORACLE_NRMSE_RATIO", component)]["simultaneous_bound"], field=f"paired-oracle-bound:{component}:ucb")
        if non_dnn["SS"]["cvar"] is not None and non_dnn["MS"]["cvar"] is not None and non_dnn["SS"]["cvar"] > 100.0 * DIMENSIONLESS_FLOOR:
            require_same_number(cvar_ratio, non_dnn["MS"]["cvar"] / non_dnn["SS"]["cvar"], field=f"paired-cvar-derived:{component}")
        else:
            require(
                cvar_ratio is None
                and cvar_ratio_ucb is None
                and cvar_ratio_status == "NOT_EVALUABLE_UNSTABLE_RATIO_NO_FROZEN_ABSOLUTE_DIFFERENCE_MARGIN",
                "HMSO01R_B_NON_DNN_UNSTABLE_RATIO_SEMANTICS_FAILURE",
                f"conditional_variance:{component}",
            )
        if non_dnn["SS"]["oracle"] is not None and non_dnn["MS"]["oracle"] is not None and non_dnn["SS"]["oracle"] > 100.0 * DIMENSIONLESS_FLOOR:
            require_same_number(oracle_ratio, non_dnn["MS"]["oracle"] / non_dnn["SS"]["oracle"], field=f"paired-oracle-derived:{component}")
        else:
            require(
                oracle_ratio is None
                and oracle_ratio_ucb is None
                and oracle_ratio_status == "NOT_EVALUABLE_UNSTABLE_RATIO_NO_FROZEN_ABSOLUTE_DIFFERENCE_MARGIN",
                "HMSO01R_B_NON_DNN_UNSTABLE_RATIO_SEMANTICS_FAILURE",
                f"oracle_nrmse:{component}",
            )

        absolute_fold_values = [
            *arm_values["MS"]["folds"],
            *non_dnn["MS"]["cvar_folds"],
            *non_dnn["MS"]["oracle_folds"],
            *non_dnn["MS"]["coverage_fold"].values(),
        ]
        relative_fold_values = [
            *arm_values["SS"]["folds"], *arm_values["MS"]["folds"],
            *non_dnn["SS"]["cvar_folds"], *non_dnn["MS"]["cvar_folds"],
            *non_dnn["SS"]["oracle_folds"], *non_dnn["MS"]["oracle_folds"],
            *non_dnn["SS"]["coverage_fold"].values(), *non_dnn["MS"]["coverage_fold"].values(),
        ]
        absolute_folds_valid = all(value is not None for value in absolute_fold_values)
        relative_folds_valid = all(value is not None for value in relative_fold_values)
        folds_valid = absolute_folds_valid and relative_folds_valid
        family_point_checks = {family: bool(non_dnn["MS"]["family"][family] is not None and non_dnn["MS"]["family"][family] <= 0.85) for family in FAMILIES}
        family_bound_checks = {family: bool(non_dnn["MS"]["family_ucb"][family] is not None and non_dnn["MS"]["family_ucb"][family] <= 1.00) for family in FAMILIES}
        coverage_family_checks = {family: bool(non_dnn["MS"]["coverage_family"][family] is not None and non_dnn["MS"]["coverage_family"][family] >= 0.80) for family in FAMILIES}
        absolute_checks = {
            "candidate_c_point": bool(arm_values["MS"]["evaluable"] and ms_d is not None and ms_d < 1.0),
            "candidate_c_simultaneous_ucb": bool(arm_values["MS"]["evaluable"] and arm_values["MS"]["ucb"] is not None and arm_values["MS"]["ucb"] < 1.0),
            "conditional_variance_point": bool(non_dnn["MS"]["cvar"] is not None and non_dnn["MS"]["cvar"] <= 0.25),
            "conditional_variance_simultaneous_ucb": bool(non_dnn["MS"]["cvar_ucb"] is not None and non_dnn["MS"]["cvar_ucb"] <= 0.35),
            "oracle_nrmse_point": bool(non_dnn["MS"]["oracle"] is not None and non_dnn["MS"]["oracle"] <= 0.60),
            "oracle_nrmse_simultaneous_ucb": bool(non_dnn["MS"]["oracle_ucb"] is not None and non_dnn["MS"]["oracle_ucb"] <= 0.70),
            "improvement_point": bool(non_dnn["MS"]["improvement"] is not None and non_dnn["MS"]["improvement"] >= 0.25),
            "improvement_simultaneous_lcb": bool(non_dnn["MS"]["improvement_lcb"] is not None and non_dnn["MS"]["improvement_lcb"] >= 0.15),
            "every_family_nrmse_point": all(family_point_checks.values()),
            "every_family_nrmse_simultaneous_ucb": all(family_bound_checks.values()),
            "coverage_overall": bool(non_dnn["MS"]["coverage"] is not None and non_dnn["MS"]["coverage"] >= 0.90),
            "coverage_every_family": all(coverage_family_checks.values()),
            "all_six_folds_valid": absolute_folds_valid,
        }
        ratio_stable = bool(ss_d is not None and ss_d > 100.0 * DIMENSIONLESS_FLOOR)
        candidate_nonworsening = bool(ss_d is not None and ss_d > 0 and ms_d is not None and ms_d - ss_d <= 0.02 and ((not ratio_stable) or (ratio is not None and ratio <= 1.05)))
        family_values_finite = all(non_dnn[arm]["family"][family] is not None for arm in ARMS for family in FAMILIES)
        worst_ss = max(non_dnn["SS"]["family"].values()) if family_values_finite else None
        worst_ms = max(non_dnn["MS"]["family"].values()) if family_values_finite else None
        worst_guard = bool(worst_ss is not None and worst_ms is not None and worst_ms - worst_ss <= 0.05 and all(family_point_checks.values()) and all(family_bound_checks.values()))
        coverage_guard = bool(
            non_dnn["SS"]["coverage"] is not None and non_dnn["MS"]["coverage"] is not None
            and non_dnn["MS"]["coverage"] >= 0.90
            and non_dnn["MS"]["coverage"] >= non_dnn["SS"]["coverage"] - 0.05
            and all(non_dnn["SS"]["coverage_family"][family] is not None and non_dnn["MS"]["coverage_family"][family] is not None and non_dnn["MS"]["coverage_family"][family] >= 0.80 and non_dnn["MS"]["coverage_family"][family] >= non_dnn["SS"]["coverage_family"][family] - 0.05 for family in FAMILIES)
        )
        reversal_folds = [
            f"FOLD_{fold}" for fold in FOLDS
            if all(value is not None for value in (
                arm_values["MS"]["folds"][fold], arm_values["SS"]["folds"][fold],
                non_dnn["MS"]["cvar_folds"][fold], non_dnn["SS"]["cvar_folds"][fold],
                non_dnn["MS"]["oracle_folds"][fold], non_dnn["SS"]["oracle_folds"][fold],
            ))
            and arm_values["MS"]["folds"][fold] > arm_values["SS"]["folds"][fold] + DIMENSIONLESS_FLOOR
            and non_dnn["MS"]["cvar_folds"][fold] > non_dnn["SS"]["cvar_folds"][fold] + DIMENSIONLESS_FLOOR
            and non_dnn["MS"]["oracle_folds"][fold] > non_dnn["SS"]["oracle_folds"][fold] + DIMENSIONLESS_FLOOR
        ]
        relative_checks = {
            "candidate_c_point_ratio": bool(expected_pair_evaluable and ratio is not None and ratio <= 0.80),
            "candidate_c_simultaneous_ratio_ucb": bool(expected_pair_evaluable and ratio_ucb is not None and ratio_ucb <= 0.90),
            "conditional_variance_point_ratio": bool(cvar_ratio is not None and cvar_ratio <= 0.80),
            "conditional_variance_simultaneous_ratio_ucb": bool(cvar_ratio_ucb is not None and cvar_ratio_ucb <= 0.90),
            "oracle_nrmse_point_ratio": bool(oracle_ratio is not None and oracle_ratio <= 0.85),
            "oracle_nrmse_simultaneous_ratio_ucb": bool(oracle_ratio_ucb is not None and oracle_ratio_ucb <= 0.95),
            "candidate_c_nonworsening": candidate_nonworsening,
            "worst_family_guard": worst_guard,
            "coverage_guard": coverage_guard,
            "no_fold_three_effect_reversal": relative_folds_valid and not reversal_folds,
        }
        absolute_candidate_evaluable = bool(arm_values["MS"]["evaluable"])
        absolute_cvar_evaluable = bool(
            non_dnn["MS"]["status"]["conditional_variance"]["overall"]["evaluable"]
            and bounds[("ABSOLUTE_MS_conditional_variance", component)]["status"] == "EVALUABLE"
        )
        absolute_oracle_evaluable = bool(
            non_dnn["MS"]["status"]["oracle_nrmse"]["overall"]["evaluable"]
            and bounds[("ABSOLUTE_MS_oracle_nrmse", component)]["status"] == "EVALUABLE"
        )
        absolute_improvement_evaluable = bool(
            non_dnn["MS"]["status"]["improvement"]["overall"]["evaluable"]
            and bounds[("ABSOLUTE_MS_improvement", component)]["status"] == "EVALUABLE"
        )
        absolute_family_evaluable = all(
            non_dnn["MS"]["status"]["oracle_nrmse"]["family"][family]["evaluable"]
            and bounds[(f"ABSOLUTE_MS_oracle_nrmse_family_{family}", component)]["status"] == "EVALUABLE"
            for family in FAMILIES
        )
        absolute_coverage_evaluable = bool(
            non_dnn["MS"]["status"]["coverage"]["overall"]["evaluable"]
            and all(non_dnn["MS"]["status"]["coverage"]["family"][family]["evaluable"] for family in FAMILIES)
        )
        absolute_evaluable = bool(
            absolute_candidate_evaluable and absolute_cvar_evaluable
            and absolute_oracle_evaluable and absolute_improvement_evaluable
            and absolute_family_evaluable and absolute_coverage_evaluable
            and absolute_folds_valid
        )

        relative_candidate_evaluable = bool(
            arm_values["SS"]["evaluable"] and arm_values["MS"]["evaluable"] and expected_pair_evaluable
        )
        relative_cvar_evaluable = bool(
            non_dnn["SS"]["status"]["conditional_variance"]["overall"]["evaluable"]
            and non_dnn["MS"]["status"]["conditional_variance"]["overall"]["evaluable"]
            and cvar_ratio is not None and cvar_ratio_ucb is not None
            and bounds[("PAIRED_CONDITIONAL_VARIANCE_RATIO", component)]["status"] == "EVALUABLE"
        )
        relative_oracle_evaluable = bool(
            non_dnn["SS"]["status"]["oracle_nrmse"]["overall"]["evaluable"]
            and non_dnn["MS"]["status"]["oracle_nrmse"]["overall"]["evaluable"]
            and oracle_ratio is not None and oracle_ratio_ucb is not None
            and bounds[("PAIRED_ORACLE_NRMSE_RATIO", component)]["status"] == "EVALUABLE"
        )
        relative_family_evaluable = all(
            non_dnn["SS"]["status"]["oracle_nrmse"]["family"][family]["evaluable"]
            and non_dnn["MS"]["status"]["oracle_nrmse"]["family"][family]["evaluable"]
            and bounds[(f"ABSOLUTE_MS_oracle_nrmse_family_{family}", component)]["status"] == "EVALUABLE"
            for family in FAMILIES
        )
        relative_coverage_evaluable = bool(
            all(non_dnn[arm]["status"]["coverage"]["overall"]["evaluable"] for arm in ARMS)
            and all(
                non_dnn[arm]["status"]["coverage"]["family"][family]["evaluable"]
                for arm in ARMS for family in FAMILIES
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

        def add_mechanism(destination: list[str], mechanism_value: Any) -> None:
            mechanism = str(normalize_zero_status(mechanism_value)) if mechanism_value else "NOT_EVALUABLE_UNSPECIFIED_MANDATORY_INPUT"
            if mechanism != "EVALUABLE" and mechanism not in destination:
                destination.append(mechanism)

        def add_leaf_mechanism(destination: list[str], leaf: Mapping[str, Any]) -> None:
            if not bool(leaf["evaluable"]):
                add_mechanism(destination, leaf["not_evaluable_mechanism"])

        if not absolute_candidate_evaluable:
            add_mechanism(absolute_mechanisms, arm_values["MS"]["block"]["candidate_c_status"])
        for metric in ("conditional_variance", "oracle_nrmse", "improvement", "coverage"):
            add_leaf_mechanism(absolute_mechanisms, non_dnn["MS"]["status"][metric]["overall"])
        for family_name in (
            "ABSOLUTE_MS_conditional_variance",
            "ABSOLUTE_MS_oracle_nrmse",
            "ABSOLUTE_MS_improvement",
        ):
            if bounds[(family_name, component)]["status"] != "EVALUABLE":
                add_mechanism(absolute_mechanisms, bounds[(family_name, component)]["status"])
        for family in FAMILIES:
            add_leaf_mechanism(
                absolute_mechanisms,
                non_dnn["MS"]["status"]["oracle_nrmse"]["family"][family],
            )
            add_leaf_mechanism(
                absolute_mechanisms,
                non_dnn["MS"]["status"]["coverage"]["family"][family],
            )
            family_bound_status = bounds[(f"ABSOLUTE_MS_oracle_nrmse_family_{family}", component)]["status"]
            if family_bound_status != "EVALUABLE":
                add_mechanism(absolute_mechanisms, family_bound_status)
        for metric in ("conditional_variance", "oracle_nrmse", "coverage"):
            for fold in FOLDS:
                add_leaf_mechanism(
                    absolute_mechanisms,
                    non_dnn["MS"]["status"][metric]["fold"][f"FOLD_{fold}"],
                )
        if not absolute_folds_valid:
            if any(value is None for value in arm_values["MS"]["folds"]):
                add_mechanism(absolute_mechanisms, CA_ZERO_STATUS)

        for arm in ARMS:
            if not arm_values[arm]["evaluable"]:
                add_mechanism(relative_mechanisms, arm_values[arm]["block"]["candidate_c_status"])
        if not expected_pair_evaluable:
            add_mechanism(relative_mechanisms, paired_status)
        for arm in ARMS:
            for metric in ("conditional_variance", "oracle_nrmse", "coverage"):
                add_leaf_mechanism(relative_mechanisms, non_dnn[arm]["status"][metric]["overall"])
            for family in FAMILIES:
                add_leaf_mechanism(
                    relative_mechanisms,
                    non_dnn[arm]["status"]["oracle_nrmse"]["family"][family],
                )
                add_leaf_mechanism(
                    relative_mechanisms,
                    non_dnn[arm]["status"]["coverage"]["family"][family],
                )
            for metric in ("conditional_variance", "oracle_nrmse", "coverage"):
                for fold in FOLDS:
                    add_leaf_mechanism(
                        relative_mechanisms,
                        non_dnn[arm]["status"][metric]["fold"][f"FOLD_{fold}"],
                    )
        for family_name in ("PAIRED_CONDITIONAL_VARIANCE_RATIO", "PAIRED_ORACLE_NRMSE_RATIO"):
            if bounds[(family_name, component)]["status"] != "EVALUABLE":
                add_mechanism(relative_mechanisms, bounds[(family_name, component)]["status"])
        for family in FAMILIES:
            family_bound_status = bounds[(f"ABSOLUTE_MS_oracle_nrmse_family_{family}", component)]["status"]
            if family_bound_status != "EVALUABLE":
                add_mechanism(relative_mechanisms, family_bound_status)
        if not relative_folds_valid:
            if any(
                value is None
                for arm in ARMS
                for value in arm_values[arm]["folds"]
            ):
                add_mechanism(relative_mechanisms, CA_ZERO_STATUS)

        recorded = first(summary_components, (component,), field=f"verdict.components.{component}")
        require(isinstance(recorded, Mapping), "HMSO01R_B_COMPONENT_VERDICT_SCHEMA_FAILURE", component)
        require_bool_map(recorded["absolute_checks"], absolute_checks, field=f"verdict.{component}.absolute_checks")
        require_bool_map(recorded["relative_checks"], relative_checks, field=f"verdict.{component}.relative_checks")
        require_bool_map(recorded["family_point_checks"], family_point_checks, field=f"verdict.{component}.family_point_checks")
        require_bool_map(recorded["family_simultaneous_ucb_checks"], family_bound_checks, field=f"verdict.{component}.family_bound_checks")
        require_bool_map(recorded["coverage_family_checks"], coverage_family_checks, field=f"verdict.{component}.coverage_family_checks")
        require(first(recorded, ("reversal_folds",), field=f"verdict.{component}.reversal_folds") == reversal_folds, "HMSO01R_B_REVERSAL_RECOMPUTATION_FAILURE", component)
        require(
            first(recorded, ("not_evaluable_mechanisms",), field=f"verdict.{component}.not_evaluable_mechanisms")
            == {"absolute": absolute_mechanisms, "relative": relative_mechanisms},
            "HMSO01R_B_NOT_EVALUABLE_MECHANISM_MISMATCH",
            component,
        )
        expected_flags = {
            "dnn_evaluable": dnn_evaluable,
            "cvar_evaluable": cvar_evaluable,
            "oracle_evaluable": oracle_evaluable,
            "coverage_evaluable": coverage_evaluable,
            "all_required_folds_valid": folds_valid,
            "absolute_evaluable": absolute_evaluable,
            "relative_rescue_evaluable": relative_evaluable,
            "component_evaluable": component_evaluable,
            "absolute_pass": absolute_pass,
            "relative_rescue_pass": relative_pass,
            "component_pass": absolute_pass and relative_pass,
        }
        for key, expected_value in expected_flags.items():
            require(as_bool(first(recorded, (key,), field=f"verdict.{component}.{key}"), field=f"verdict.{component}.{key}") == expected_value, "HMSO01R_B_GATE_RECOMPUTATION_FAILURE", f"{component}:{key}")
        for key, expected_value in (("conditional_variance_ratio", cvar_ratio), ("conditional_variance_ratio_simultaneous_ucb", cvar_ratio_ucb), ("oracle_nrmse_ratio", oracle_ratio), ("oracle_nrmse_ratio_simultaneous_ucb", oracle_ratio_ucb), ("worst_family_ss", worst_ss), ("worst_family_ms", worst_ms)):
            require_same_number(first(recorded, (key,), field=f"verdict.{component}.{key}"), expected_value, field=f"verdict:{component}:{key}")
        verdict_row = verdict_index[(component,)]
        for key, expected_value in recorded.items():
            require(key in verdict_row, "HMSO01R_B_COMPONENT_VERDICT_CSV_MISMATCH", f"{component}:{key}:missing")
            if isinstance(expected_value, (dict, list)):
                require(json_cell(verdict_row[key], field=f"verdict csv {component}.{key}") == expected_value, "HMSO01R_B_COMPONENT_VERDICT_CSV_MISMATCH", f"{component}:{key}")
            elif expected_value is None:
                require(optional_float(verdict_row[key], field=f"verdict csv {component}.{key}") is None, "HMSO01R_B_COMPONENT_VERDICT_CSV_MISMATCH", f"{component}:{key}")
            elif isinstance(expected_value, bool):
                require(as_bool(verdict_row[key], field=f"verdict csv {component}.{key}") == expected_value, "HMSO01R_B_COMPONENT_VERDICT_CSV_MISMATCH", f"{component}:{key}")
            elif isinstance(expected_value, (float, int)) and not isinstance(expected_value, bool):
                require_same_number(verdict_row[key], expected_value, field=f"verdict-csv:{component}:{key}")
            else:
                require(str(verdict_row[key]) == str(expected_value), "HMSO01R_B_COMPONENT_VERDICT_CSV_MISMATCH", f"{component}:{key}")
        for requirement, expected_value in relative_checks.items():
            rescue_row = rescue_index[(component, requirement)]
            require(as_bool(rescue_row["requirement_pass"], field=f"rescue csv {component}.{requirement}") == expected_value, "HMSO01R_B_PAIRED_RESCUE_CSV_MISMATCH", f"{component}:{requirement}")
            if requirement.startswith("candidate_c"):
                requirement_evaluable = relative_candidate_evaluable
                requirement_status = "EVALUABLE" if requirement_evaluable else str(paired_status)
            elif requirement.startswith("conditional_variance"):
                requirement_evaluable = relative_cvar_evaluable
                requirement_status = str(bounds[("PAIRED_CONDITIONAL_VARIANCE_RATIO", component)]["status"])
            elif requirement.startswith("oracle_nrmse"):
                requirement_evaluable = relative_oracle_evaluable
                requirement_status = str(bounds[("PAIRED_ORACLE_NRMSE_RATIO", component)]["status"])
            elif requirement == "worst_family_guard":
                requirement_evaluable = relative_family_evaluable
                requirement_status = "EVALUABLE" if requirement_evaluable else (
                    relative_mechanisms[0] if relative_mechanisms else "NOT_EVALUABLE"
                )
            elif requirement == "coverage_guard":
                requirement_evaluable = relative_coverage_evaluable
                requirement_status = "EVALUABLE" if requirement_evaluable else (
                    relative_mechanisms[0] if relative_mechanisms else "NOT_EVALUABLE"
                )
            else:
                requirement_evaluable = relative_folds_valid
                requirement_status = "EVALUABLE" if requirement_evaluable else (
                    relative_mechanisms[0] if relative_mechanisms else NON_DNN_BOOTSTRAP_NE
                )
            require(
                rescue_row["status"] == requirement_status
                and as_bool(rescue_row["evaluable"], field=f"rescue csv {component}.{requirement}.evaluable") == requirement_evaluable
                and rescue_row["not_evaluable_mechanism"] == ("" if requirement_evaluable else requirement_status),
                "HMSO01R_B_PAIRED_RESCUE_CSV_MISMATCH",
                f"{component}:{requirement}:status",
            )
            for key, expected_number in (
                ("conditional_variance_ratio", cvar_ratio),
                ("conditional_variance_ratio_simultaneous_ucb", cvar_ratio_ucb),
                ("oracle_nrmse_ratio", oracle_ratio),
                ("oracle_nrmse_ratio_simultaneous_ucb", oracle_ratio_ucb),
                ("worst_family_ss", worst_ss),
                ("worst_family_ms", worst_ms),
            ):
                require_same_number(
                    rescue_row[key],
                    expected_number,
                    field=f"paired-rescue:{component}:{requirement}:{key}",
                )
            require(
                rescue_row["reversal_folds"] == "|".join(reversal_folds),
                "HMSO01R_B_PAIRED_RESCUE_CSV_MISMATCH",
                f"{component}:{requirement}:reversal_folds",
            )
            candidate_requirement = requirement.startswith("candidate_c")
            require_same_number(
                rescue_row["ss_candidate_c"],
                ss_d if candidate_requirement else None,
                field=f"paired-rescue:{component}:{requirement}:ss_candidate_c",
            )
            require_same_number(
                rescue_row["ms_candidate_c"],
                ms_d if candidate_requirement else None,
                field=f"paired-rescue:{component}:{requirement}:ms_candidate_c",
            )
            point_threshold = {
                "candidate_c_point_ratio": 0.80,
                "conditional_variance_point_ratio": 0.80,
                "oracle_nrmse_point_ratio": 0.85,
            }.get(requirement)
            confidence_threshold = {
                "candidate_c_simultaneous_ratio_ucb": 0.90,
                "conditional_variance_simultaneous_ratio_ucb": 0.90,
                "oracle_nrmse_simultaneous_ratio_ucb": 0.95,
            }.get(requirement)
            if point_threshold is None:
                require(rescue_row["point_threshold"] == "SEE_FROZEN_CONTRACT", "HMSO01R_B_PAIRED_RESCUE_CSV_MISMATCH", f"{component}:{requirement}:point_threshold")
            else:
                require_same_number(rescue_row["point_threshold"], point_threshold, field=f"paired-rescue:{component}:{requirement}:point_threshold")
            if confidence_threshold is None:
                require(rescue_row["confidence_threshold"] == "SEE_FROZEN_CONTRACT", "HMSO01R_B_PAIRED_RESCUE_CSV_MISMATCH", f"{component}:{requirement}:confidence_threshold")
            else:
                require_same_number(rescue_row["confidence_threshold"], confidence_threshold, field=f"paired-rescue:{component}:{requirement}:confidence_threshold")
        derived[component] = {
            "absolute_checks": absolute_checks,
            "relative_checks": relative_checks,
            "family_point_checks": family_point_checks,
            "family_bound_checks": family_bound_checks,
            "coverage_family_checks": coverage_family_checks,
            "reversal_folds": reversal_folds,
            "not_evaluable_mechanisms": {"absolute": absolute_mechanisms, "relative": relative_mechanisms},
            "non_dnn": non_dnn,
            "candidate": arm_values,
            "paired": {"ratio": ratio, "ucb": ratio_ucb, "evaluable": expected_pair_evaluable, "gate": candidate_relative_gate},
            **expected_flags,
        }
    return derived


def validate_summary(
    summary: Mapping[str, Any],
    firewall: Mapping[str, Any],
    division: Mapping[str, Any],
    division_records: Mapping[str, Any],
    parsed_csvs: Mapping[str, Sequence[Mapping[str, Any]]],
    coverage_rows: Sequence[Mapping[str, Any]],
) -> tuple[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]]:
    require(as_int(first(summary, ("ss_feature_dimension",), field="summary.ss_feature_dimension"), field="summary.ss_feature_dimension") == 39, "HMSO01R_B_REPRESENTATION_DIMENSION_FAILURE", "SS")
    require(as_int(first(summary, ("ms_feature_dimension",), field="summary.ms_feature_dimension"), field="summary.ms_feature_dimension") == 110, "HMSO01R_B_REPRESENTATION_DIMENSION_FAILURE", "MS")
    for key in ("bootstrap_replicate_count", "bootstrap_unique_draw_count", "bootstrap_draws_consumed"):
        require(as_int(first(summary, (key,), field=f"summary.{key}"), field=f"summary.{key}") == 10000, "HMSO01R_B_BOOTSTRAP_CONSUMPTION_FAILURE", key)
    require(as_bool(first(summary, ("observable_store_unchanged",), field="summary.observable_store_unchanged"), field="summary.observable_store_unchanged"), "HMSO01R_B_OBSERVABLE_STORE_IDENTITY_FAILURE")
    before = first(summary, ("observable_store_sha256_before",), field="summary.observable before")
    after = first(summary, ("observable_store_sha256_after",), field="summary.observable after")
    require(before == after == OBSERVABLE_SHA256, "HMSO01R_B_OBSERVABLE_STORE_IDENTITY_FAILURE")
    formal_output_hashes = first(summary, ("formal_output_sha256",), field="summary.formal_output_sha256")
    require(isinstance(formal_output_hashes, Mapping), "HMSO01R_B_FORMAL_OUTPUT_HASH_MAP_FAILURE")
    expected_formal_output_paths = set(RUNTIME_ARTIFACTS) - {
        str(PREFLIGHT.relative_to(ROOT)),
        str(QUALIFICATION.relative_to(ROOT)),
        str(TARGET_LEDGER.relative_to(ROOT)),
        str(TARGET_STORE.relative_to(ROOT)),
        str(SUMMARY.relative_to(ROOT)),
    }
    require(set(formal_output_hashes) == expected_formal_output_paths, "HMSO01R_B_FORMAL_OUTPUT_HASH_MAP_FAILURE", "path set")
    for relative in sorted(expected_formal_output_paths):
        require(
            formal_output_hashes[relative] == sha256(ROOT / relative),
            "HMSO01R_B_FORMAL_OUTPUT_HASH_MAP_FAILURE",
            relative,
        )

    simultaneous = first(summary, ("simultaneous_inference",), field="summary.simultaneous_inference")
    require(isinstance(simultaneous, Mapping), "HMSO01R_B_SIMULTANEOUS_INFERENCE_SCHEMA_FAILURE")
    require(simultaneous.get("method") == "MAXIMUM_STUDENTIZED", "HMSO01R_B_SIMULTANEOUS_INFERENCE_FAILURE", "method")
    require(as_float(simultaneous.get("confidence_level"), field="simultaneous.confidence_level") == 0.95, "HMSO01R_B_SIMULTANEOUS_INFERENCE_FAILURE", "confidence")
    scope = simultaneous.get("multiplicity_scope")
    require(scope in {"THREE_PRIMARY_COMPONENTS_WITHIN_EACH_METRIC_FAMILY", "THREE_PRIMARY_COMPONENTS_PER_METRIC_FAMILY"}, "HMSO01R_B_SIMULTANEOUS_INFERENCE_FAILURE", "scope")
    # This flag attests execution and row/status emission for every frozen bound
    # procedure.  It does not assert that every emitted numeric bound is
    # evaluable; each exact bound row carries its own status and mechanism and
    # is independently cross-validated below.
    bound_rows = parsed_csvs["06_experiments/hmso01r_b/bootstrap_simultaneous_bounds.csv"]
    require(len(bound_rows) == 57, "HMSO01R_B_BOUND_ROWSET_FAILURE", f"row_count={len(bound_rows)}")
    all_bound_procedures_executed = True  # exact 57-row identity/schema is proven by validate_bound_rows
    all_bounds_evaluable = all(
        str(normalize_zero_status(first(row, ("status",), field="summary bound status")))
        in {"EVALUABLE", EXACT_ZERO_MS_STATUS}
        for row in bound_rows
    )
    require(
        as_int(
            simultaneous.get("required_bound_row_count"),
            field="simultaneous.required_bound_row_count",
        )
        == 57
        and
        as_bool(
            simultaneous.get("all_required_bound_procedures_executed"),
            field="simultaneous.all_required_bound_procedures_executed",
        )
        == all_bound_procedures_executed
        and as_bool(
            simultaneous.get("all_required_bounds_computed"),
            field="simultaneous.all_required_bounds_computed",
        )
        == all_bound_procedures_executed
        and as_bool(
            simultaneous.get("all_required_bounds_evaluable"),
            field="simultaneous.all_required_bounds_evaluable",
        )
        == all_bounds_evaluable,
        "HMSO01R_B_SIMULTANEOUS_INFERENCE_FAILURE",
        "procedure/evaluability flags",
    )

    summary_modifications = first(summary, ("post_target_modification_counts",), field="summary.post_target_modification_counts")
    require(isinstance(summary_modifications, Mapping), "HMSO01R_B_POST_TARGET_MODIFICATION_SCHEMA_FAILURE")
    for key in PROHIBITED_KEYS[11:]:
        require(as_int(first(summary_modifications, (key,), field=f"summary.modifications.{key}"), field=f"summary.modifications.{key}") == 0, "HMSO01R_B_POST_TARGET_SCIENTIFIC_MODIFICATION", key)
    zero_authority = first(summary, ("candidate_c_zero_status_authority",), field="summary.candidate_c_zero_status_authority")
    require(
        isinstance(zero_authority, Mapping)
        and zero_authority.get("canonical_status") == CA_ZERO_STATUS
        and zero_authority.get("source_alias") == CURRENT_ZERO_ALIAS,
        "HMSO01R_B_ZERO_STATUS_ALIAS_FAILURE",
        "summary authority",
    )

    verdict, components = verdict_components(summary)
    require(set(components) == set(COMPONENTS), "HMSO01R_B_COMPONENT_VERDICT_ROWSET_FAILURE", "summary")
    derived_metrics = validate_metric_artifacts(summary, division_records, parsed_csvs, coverage_rows)
    component_statuses: dict[str, str] = {}
    any_ne = False
    all_qualified = True
    for component in COMPONENTS:
        value = first(components, (component,), field=f"verdict.components.{component}")
        require(isinstance(value, Mapping), "HMSO01R_B_COMPONENT_VERDICT_SCHEMA_FAILURE", component)
        flags = {key: bool(derived_metrics[component][key]) for key in (
            "dnn_evaluable", "cvar_evaluable", "oracle_evaluable", "coverage_evaluable",
            "all_required_folds_valid", "absolute_evaluable", "relative_rescue_evaluable",
            "component_evaluable", "absolute_pass", "relative_rescue_pass",
        )}
        expected_evaluable = bool(flags["absolute_evaluable"] and flags["relative_rescue_evaluable"])
        require(
            flags["component_evaluable"] == expected_evaluable
            and expected_evaluable
            == all(flags[key] for key in ("dnn_evaluable", "cvar_evaluable", "oracle_evaluable", "coverage_evaluable", "all_required_folds_valid")),
            "HMSO01R_B_COMPONENT_EVALUABILITY_INCONSISTENT",
            component,
        )
        status = str(first(value, ("status",), field=f"verdict.{component}.status"))
        if not expected_evaluable:
            expected_status = "H_MSO01R_COMPONENT_NOT_EVALUABLE"
            any_ne = True
        elif flags["absolute_pass"] and flags["relative_rescue_pass"]:
            expected_status = "H_MSO01R_COMPONENT_QUALIFIED"
        elif flags["absolute_pass"]:
            expected_status = "IDENTIFIABLE_BUT_MULTISCALE_RESCUE_NOT_ESTABLISHED"
        elif flags["relative_rescue_pass"]:
            expected_status = "RELATIVE_RESCUE_OBSERVED_BUT_ABSOLUTE_IDENTIFIABILITY_NOT_QUALIFIED"
        else:
            expected_status = "H_MSO01R_COMPONENT_NOT_QUALIFIED"
        require(status == expected_status, "HMSO01R_B_COMPONENT_STATUS_TAXONOMY_FAILURE", component)
        component_statuses[component] = status
        all_qualified = all_qualified and status == "H_MSO01R_COMPONENT_QUALIFIED"

    expected_global = (
        "H_MSO01R_MULTISCALE_IDENTIFIABILITY_RESCUE_NOT_EVALUABLE"
        if any_ne
        else "H_MSO01R_MULTISCALE_IDENTIFIABILITY_RESCUE_QUALIFIED"
        if all_qualified
        else "H_MSO01R_MULTISCALE_IDENTIFIABILITY_RESCUE_NOT_QUALIFIED"
    )
    global_status = first(verdict, ("global_status",), field="verdict.global_status")
    require(global_status == expected_global, "HMSO01R_B_GLOBAL_VERDICT_INCONSISTENT")
    global_evaluable = as_bool(first(verdict, ("global_evaluable",), field="verdict.global_evaluable"), field="verdict.global_evaluable")
    global_pass = as_bool(first(verdict, ("global_pass",), field="verdict.global_pass"), field="verdict.global_pass")
    eligible = as_bool(first(verdict, ("mso03_deterministic_closure_baseline_eligible", "mso03_eligible"), field="verdict.mso03_eligible"), field="verdict.mso03_eligible")
    require(global_evaluable == (not any_ne), "HMSO01R_B_GLOBAL_EVALUABILITY_INCONSISTENT")
    require(global_pass == all_qualified and eligible == all_qualified, "HMSO01R_B_DOWNSTREAM_ELIGIBILITY_INCONSISTENT")
    for key in ("neural_training_authorized", "attention_authorized", "learned_operator_authorized", "mso03_executed"):
        require(not as_bool(first(verdict, (key,), field=f"verdict.{key}"), field=f"verdict.{key}"), "HMSO01R_B_FORBIDDEN_AUTHORIZATION_OR_EXECUTION", key)

    terminal = first(summary, ("terminal_status",), field="summary.terminal_status")
    terminal_map = {
        "H_MSO01R_MULTISCALE_IDENTIFIABILITY_RESCUE_QUALIFIED": "HMSO01R_B_FRESH_CONFIRMATORY_MULTISCALE_IDENTIFIABILITY_RESCUE_QUALIFIED",
        "H_MSO01R_MULTISCALE_IDENTIFIABILITY_RESCUE_NOT_QUALIFIED": "HMSO01R_B_FRESH_CONFIRMATORY_MULTISCALE_IDENTIFIABILITY_RESCUE_NOT_QUALIFIED",
        "H_MSO01R_MULTISCALE_IDENTIFIABILITY_RESCUE_NOT_EVALUABLE": "HMSO01R_B_FRESH_CONFIRMATORY_MULTISCALE_IDENTIFIABILITY_RESCUE_NOT_EVALUABLE",
    }
    require(terminal == terminal_map[expected_global], "HMSO01R_B_TERMINAL_STATUS_INCONSISTENT")

    bindings = {
        "pre_target_freeze_sha256": sha256(FREEZE),
        "formal_evaluator_sha256": sha256(FORMAL_EVALUATOR),
        "candidate_c_implementation_preflight_sha256": sha256(PREFLIGHT),
        "target_store_sha256": sha256(TARGET_STORE),
        "target_access_ledger_sha256": sha256(TARGET_LEDGER),
        "firewall_audit_sha256": sha256(FIREWALL),
        "candidate_c_division_audit_sha256": sha256(DIVISION_AUDIT),
    }
    for key, expected in bindings.items():
        require(first(summary, (key,), field=f"summary.{key}") == expected, "HMSO01R_B_FORMAL_OUTPUT_BINDING_FAILURE", key)
    require(
        first(summary, ("pointwise_division_count",), field="summary.pointwise_division_count")
        == first(division, ("pointwise_division_count",), field="division.pointwise_division_count"),
        "HMSO01R_B_FORMAL_OUTPUT_BINDING_FAILURE",
        "pointwise division count",
    )
    require(
        deep_first(firewall, (("observable_store_sha256_after",), ("observable_store", "sha256_after")), field="firewall observable after")
        == after,
        "HMSO01R_B_FORMAL_OUTPUT_BINDING_FAILURE",
        "observable store",
    )
    return verdict, components, derived_metrics


def validate_target_ledger(ledger: Mapping[str, Any]) -> str:
    pre_target_commit = str(first(ledger, ("hmso01r_b_pre_target_commit", "pre_target_commit"), field="target ledger pre-target commit"))
    require(re.fullmatch(r"[0-9a-f]{40}", pre_target_commit) is not None, "HMSO01R_B_PRE_TARGET_COMMIT_INVALID")
    require(pre_target_commit != R_A_FINAL_COMMIT, "HMSO01R_B_PRE_TARGET_COMMIT_NOT_CREATED")
    git_boundary = first(ledger, ("git",), field="target ledger git")
    require(isinstance(git_boundary, Mapping), "HMSO01R_B_TARGET_ACCESS_LEDGER_SCHEMA_FAILURE", "git")
    require(first(git_boundary, ("branch",), field="target ledger branch") == "main", "HMSO01R_B_PRE_TARGET_GIT_BOUNDARY_FAILURE", "branch")
    require(first(git_boundary, ("remote",), field="target ledger remote") is None, "HMSO01R_B_PRE_TARGET_GIT_BOUNDARY_FAILURE", "remote")
    require(as_bool(first(git_boundary, ("working_tree_clean_before_first_target_access",), field="target ledger clean"), field="target ledger clean"), "HMSO01R_B_PRE_TARGET_GIT_BOUNDARY_FAILURE", "clean")
    replacement_authorized = first(
        ledger,
        ("case_replacement_authorized_after_first_target_access", "case_replacement_authorized"),
        field="target ledger case replacement authorization",
    )
    require(as_bool(replacement_authorized, field="target ledger case replacement authorization") is False, "HMSO01R_B_CASE_REPLACEMENT_AFTER_TARGET_ACCESS")
    require(as_int(first(ledger, ("case_replacement_after_target_access",), field="target ledger case replacement count"), field="target ledger case replacement count") == 0, "HMSO01R_B_CASE_REPLACEMENT_AFTER_TARGET_ACCESS")
    target_sha = sha256(TARGET_STORE)
    require(first(ledger, ("target_store_sha256",), field="target ledger store sha") == target_sha, "HMSO01R_B_TARGET_STORE_LEDGER_IDENTITY_FAILURE")
    frozen_identity = first(ledger, ("frozen_identity",), field="target ledger frozen_identity")
    require(isinstance(frozen_identity, Mapping), "HMSO01R_B_TARGET_ACCESS_LEDGER_SCHEMA_FAILURE", "frozen_identity")
    expected_frozen_ledger = {
        "builder_sha256": sha256(TARGET_BUILDER),
        "evaluator_helper_sha256": EXPECTED_FROZEN_SHA256["06_experiments/mso02b/build_mso02b_targets.py"],
        "formal_atlas_sha256": EXPECTED_FROZEN_SHA256[str(FORMAL_ATLAS.relative_to(ROOT))],
        "formal_particle_sample_sha256": EXPECTED_FROZEN_SHA256[str(FORMAL_SAMPLE.relative_to(ROOT))],
        "observable_store_sha256": OBSERVABLE_SHA256,
        "pre_target_freeze_sha256": sha256(FREEZE),
        "candidate_c_implementation_preflight_sha256": sha256(PREFLIGHT),
        "formal_evaluator_sha256": sha256(FORMAL_EVALUATOR),
        "formal_analysis_helper_source_sha256": EXPECTED_FROZEN_SHA256[str(NON_DNN_HELPER.relative_to(ROOT))],
        "reference_module_sha256": EXPECTED_FROZEN_SHA256["01_provenance/vendor/ddo_analytical_reference/mso02b_target_reference.py"],
    }
    for key, expected_identity in expected_frozen_ledger.items():
        require(
            first(frozen_identity, (key,), field=f"target ledger frozen_identity.{key}") == expected_identity,
            "HMSO01R_B_TARGET_ACCESS_LEDGER_FROZEN_IDENTITY_FAILURE",
            key,
        )
    require(
        first(frozen_identity, ("vendor_operator_sha256",), field="target ledger vendor operator identities")
        == {
            relative: EXPECTED_FROZEN_SHA256[relative]
            for relative in REQUIRED_FREEZE_PATHS
            if relative.startswith("01_provenance/vendor/pio_stage01c_static/structure_preserving/")
        },
        "HMSO01R_B_TARGET_ACCESS_LEDGER_FROZEN_IDENTITY_FAILURE",
        "vendor operators",
    )
    require(
        first(frozen_identity, ("candidate_c_implementation_preflight_sha256",), field="target ledger preflight sha") == sha256(PREFLIGHT)
        and first(frozen_identity, ("formal_evaluator_sha256",), field="target ledger evaluator sha") == sha256(FORMAL_EVALUATOR),
        "HMSO01R_B_TARGET_ACCESS_LEDGER_PREFLIGHT_BINDING_FAILURE",
    )
    before = first(ledger, ("observable_store_sha256_before", "observable_store_sha256_before_target_generation"), field="target ledger observable before")
    after = first(ledger, ("observable_store_sha256_after", "observable_store_sha256_after_target_generation"), field="target ledger observable after")
    require(before == after == OBSERVABLE_SHA256, "HMSO01R_B_OBSERVABLE_STORE_IDENTITY_FAILURE")
    require(as_int(first(ledger, ("qualified_case_count",), field="target ledger qualified cases"), field="target ledger qualified cases") == 384, "HMSO01R_B_TARGET_REFERENCE_QUALIFICATION_NOT_COMPLETE")
    require(as_int(first(ledger, ("failed_case_count",), field="target ledger failed cases"), field="target ledger failed cases") == 0, "HMSO01R_B_TARGET_REFERENCE_QUALIFICATION_NOT_COMPLETE")
    operator_audit = first(
        ledger,
        ("pretarget_base_operator_identity_audit",),
        field="target ledger pretarget operator audit",
    )
    require(
        isinstance(operator_audit, Mapping)
        and operator_audit.get("classification")
        == "TARGET_BLIND_BASE_OPERATOR_IDENTITY_AUDIT_NOT_TARGET_REFERENCE_EVALUATION"
        and as_int(operator_audit.get("count"), field="target ledger operator audit count") == 384
        and as_int(operator_audit.get("matched"), field="target ledger operator audit matched") == 384
        and operator_audit.get("ordered_digest")
        == "4cf2df0d4b4bcf25ee497e89a12f6edb07bdeae7b195f5ca100bedef79467e40",
        "HMSO01R_B_TARGET_ACCESS_LEDGER_OPERATOR_AUDIT_FAILURE",
    )
    authorized = first(ledger, ("authorized_activity_counts",), field="target ledger authorized_activity_counts")
    require(isinstance(authorized, Mapping), "HMSO01R_B_TARGET_ACCESS_LEDGER_SCHEMA_FAILURE", "authorized_activity_counts")
    expected_authorized = {
        "target_case_evaluation_count": 384,
        "reference_evaluation_count": 384,
        "target_store_read_count": 0,
        "target_store_write_count": 1,
        "candidate_c_evaluation_count": 0,
        "conditional_variance_evaluation_count": 0,
        "oracle_fit_count": 0,
        "coverage_evaluation_count": 0,
        "paired_rescue_evaluation_count": 0,
        "bootstrap_draws_consumed": 0,
    }
    for key, expected in expected_authorized.items():
        require(
            as_int(first(authorized, (key,), field=f"target ledger authorized.{key}"), field=f"target ledger authorized.{key}") == expected,
            "HMSO01R_B_TARGET_ACCESS_LEDGER_COUNT_FAILURE",
            key,
        )
    prohibited = first(ledger, ("prohibited_activity_counts",), field="target ledger prohibited_activity_counts")
    require(isinstance(prohibited, Mapping), "HMSO01R_B_TARGET_ACCESS_LEDGER_SCHEMA_FAILURE", "prohibited_activity_counts")
    for key in PROHIBITED_KEYS:
        require(
            as_int(first(prohibited, (key,), field=f"target ledger prohibited.{key}"), field=f"target ledger prohibited.{key}") == 0,
            "HMSO01R_B_INFORMATION_FIREWALL_BREACH",
            f"target_ledger:{key}",
        )
    return pre_target_commit


def validate_import_manifest(rows: Sequence[Mapping[str, str]]) -> None:
    """Validate every provenance edge rather than trusting the manifest file."""

    require(len(rows) == len(EXPECTED_IMPORT_EDGES), "HMSO01R_B_IMPORT_MANIFEST_ROWSET_FAILURE", f"rows={len(rows)}")
    current_destinations = {
        "06_experiments/hmso01r_b/build_hmso01r_b_targets.py": sha256(TARGET_BUILDER),
        "06_experiments/hmso01r_b/run_hmso01r_b_formal.py": sha256(FORMAL_EVALUATOR),
    }
    seen_source_destination: set[tuple[str, str]] = set()
    helper_edge = False
    builder_edge = False
    for index, row in enumerate(rows):
        require(
            str(first(row, ("historical_target_result_report_checkpoint_or_h3_payload_imported",), field=f"import[{index}].historical")).lower() == "false",
            "HMSO01R_B_HISTORICAL_OUTCOME_IMPORT_FORBIDDEN",
            str(index),
        )
        source_path = str(first(row, ("source_path",), field=f"import[{index}].source_path"))
        destination = str(first(row, ("imported_destination",), field=f"import[{index}].destination"))
        source_sha = str(first(row, ("source_sha256",), field=f"import[{index}].source_sha"))
        destination_sha = str(first(row, ("destination_sha256",), field=f"import[{index}].destination_sha"))
        identity = (source_path, destination)
        require(
            EXPECTED_IMPORT_EDGES.get(source_path) == destination,
            "HMSO01R_B_IMPORT_MANIFEST_EDGE_FAILURE",
            str(identity),
        )
        require(identity not in seen_source_destination, "HMSO01R_B_IMPORT_MANIFEST_DUPLICATE_EDGE", str(identity))
        seen_source_destination.add(identity)
        if source_path.startswith("/Users/"):
            require(sha256(Path(source_path)) == source_sha, "HMSO01R_B_IMPORT_SOURCE_IDENTITY_FAILURE", source_path)
            require(first(row, ("source_head",), field=f"import[{index}].source_head") == "d76d29ae51e8104641b710371f0fcb248d5ea268", "HMSO01R_B_IMPORT_SOURCE_HEAD_FAILURE", source_path)
        else:
            source = ROOT / source_path
            require(source.is_file() and sha256(source) == source_sha, "HMSO01R_B_IMPORT_SOURCE_IDENTITY_FAILURE", source_path)
            require(first(row, ("source_head",), field=f"import[{index}].source_head") == R_A_FINAL_COMMIT, "HMSO01R_B_IMPORT_SOURCE_HEAD_FAILURE", source_path)
            require(hashlib.sha256(git_blob_bytes(R_A_FINAL_COMMIT, source_path)).hexdigest() == source_sha, "HMSO01R_B_IMPORT_SOURCE_GIT_BLOB_FAILURE", source_path)
        if destination_sha in {"GENERATED_ONLY_AFTER_384_OF_384_QUALIFICATION", "GENERATED_AFTER_TARGET_QUALIFICATION"}:
            require(destination in {str(TARGET_STORE.relative_to(ROOT)), str(TARGET_LEDGER.relative_to(ROOT))}, "HMSO01R_B_IMPORT_DESTINATION_IDENTITY_FAILURE", destination)
        else:
            require((ROOT / destination).is_file() and sha256(ROOT / destination) == destination_sha, "HMSO01R_B_IMPORT_DESTINATION_IDENTITY_FAILURE", destination)
        if destination in current_destinations:
            require(destination_sha == current_destinations[destination], "HMSO01R_B_IMPORT_DESTINATION_IDENTITY_FAILURE", destination)
        if source_path == str(NON_DNN_HELPER.relative_to(ROOT)):
            require(source_sha == "55b0b63eb2c99364c8a2e96c75191a50707e93357f7039bd9edfdcb7c7c831b7" and destination == str(FORMAL_EVALUATOR.relative_to(ROOT)), "HMSO01R_B_IMPORT_HELPER_BOUNDARY_FAILURE")
            helper_edge = True
        if source_path == "06_experiments/mso02b/build_mso02b_targets.py":
            require(source_sha == "940a671927b20f219a4d2553ab61f36bc568e1c8e29bd9f043edd44103f1a08f" and destination == str(TARGET_BUILDER.relative_to(ROOT)), "HMSO01R_B_IMPORT_BUILDER_BOUNDARY_FAILURE")
            builder_edge = True
    require(
        helper_edge
        and builder_edge
        and {source for source, _ in seen_source_destination} == set(EXPECTED_IMPORT_EDGES),
        "HMSO01R_B_IMPORT_MANIFEST_ROWSET_FAILURE",
        "required source-only edges",
    )


def role_for(relative: str) -> str:
    mapping = {
        "00_project_contract/hmso01r_b_fresh_confirmatory_execution_contract.md": "PROSPECTIVE_FORMAL_EXECUTION_CONTRACT",
        "01_provenance/hmso01r_b_target_reference_import_manifest.csv": "TARGET_REFERENCE_SOURCE_PROVENANCE",
        "05_registries/hmso01r_b_target_role_registry.json": "FORMAL_TARGET_ROLE_REGISTRY",
        "08_manifests/hmso01r_a_git_handoff.json": "R_A_FINAL_GIT_HANDOFF",
        "08_manifests/hmso01r_b_pre_target_freeze.json": "PRE_TARGET_EVIDENCE_AND_EXECUTABLE_FREEZE",
        "08_manifests/hmso01r_b_manifest.json": "FINAL_FORMAL_ARTIFACT_MANIFEST",
        "06_experiments/hmso01r_b/candidate_c_implementation_preflight.json": "EXECUTABLE_CANDIDATE_C_SYNTHETIC_PREFLIGHT",
        "06_experiments/hmso01r_b/target_reference_qualification.csv": "FORMAL_TARGET_REFERENCE_QUALIFICATION",
        "06_experiments/hmso01r_b/target_observable_join_audit.csv": "FORMAL_TARGET_OBSERVABLE_JOIN_AUDIT",
        "06_experiments/hmso01r_b/target_access_ledger.json": "AUTHORIZED_TARGET_REFERENCE_ACCESS_LEDGER",
        "06_experiments/hmso01r_b/candidate_c_division_audit.json": "CANDIDATE_C_DIRECT_DIVISION_AUDIT",
        "06_experiments/hmso01r_b/firewall_audit.json": "FORMAL_INFORMATION_FIREWALL_AUDIT",
        "06_experiments/hmso01r_b/formal_summary.json": "FORMAL_MACHINE_READABLE_SUMMARY",
        "06_experiments/hmso01r_b/target_ref/hmso01r_b_target_store.npz": "PHYSICALLY_SEPARATED_FORMAL_TARGET_STORE",
        "07_reports/hmso01r_b_fresh_confirmatory_identifiability_report.md": "HUMAN_READABLE_FINAL_REPORT",
        "08_manifests/hmso01r_b_status_ledger.json": "TERMINAL_STATUS_LEDGER",
    }
    if relative in mapping:
        return mapping[relative]
    if relative.endswith(".py"):
        return "HASH_BOUND_EXECUTABLE"
    if "candidate_c" in relative and relative.endswith(".csv"):
        return "FORMAL_CANDIDATE_C_METRIC_OR_BOUND"
    if "conditional_variance" in relative:
        return "FORMAL_CONDITIONAL_VARIANCE_METRIC"
    if "oracle_metrics" in relative:
        return "FORMAL_NON_NEURAL_ORACLE_METRIC"
    if "coverage_metrics" in relative:
        return "FORMAL_OBSERVABLE_COVERAGE_METRIC"
    if "paired_non_dnn_rescue" in relative:
        return "FORMAL_PAIRED_NON_DNN_RESCUE_METRIC"
    if "bootstrap_simultaneous_bounds" in relative:
        return "FORMAL_MAXIMUM_STUDENTIZED_INFERENCE"
    if "component_verdicts" in relative:
        return "FORMAL_COMPONENT_VERDICTS"
    if "/vendor/" in f"/{relative}":
        return "HASH_BOUND_VENDOR_SOURCE"
    if relative.startswith("05_registries/"):
        return "FROZEN_SEMANTICS_OR_IDENTITY_REGISTRY"
    if relative.startswith("06_experiments/hmso01r_a/") or relative.startswith("08_manifests/"):
        return "FROZEN_EVIDENCE_INPUT"
    return "HMSO01R_B_FORMAL_ARTIFACT"


def source_for(relative: str) -> str:
    if relative.startswith("06_experiments/hmso01r_b/target_ref/") or "target_reference_qualification" in relative:
        return "hash-bound isolated R-B target builder and frozen R-A atlas"
    if relative in {
        str(REPORT.relative_to(ROOT)),
        str(MANIFEST.relative_to(ROOT)),
        str(STATUS.relative_to(ROOT)),
    }:
        return "release validator over complete hash-bound R-B evidence"
    if relative.startswith("06_experiments/hmso01r_b/") and relative not in {
        str(TARGET_BUILDER.relative_to(ROOT)), str(FORMAL_EVALUATOR.relative_to(ROOT)), str(FINALIZER.relative_to(ROOT))
    }:
        return "single hash-bound R-B formal evaluator or its direct ledger"
    if "/vendor/" in f"/{relative}":
        return "frozen DDO analytical/reference or lambda-one operator import"
    return "user-authorized R-B contract and frozen R-A/CA-MSO-01 evidence"


def consumption_for(relative: str) -> str:
    if relative in {
        str(REPORT.relative_to(ROOT)),
        str(MANIFEST.relative_to(ROOT)),
        str(STATUS.relative_to(ROOT)),
    }:
        return "FINAL_RELEASE_OUTPUT"
    if relative in RUNTIME_ARTIFACTS:
        return "CONSUMED_BY_FROZEN_H_MSO01R_VERDICT_AND_RELEASE"
    return "CONSUMED_BY_HMSO01R_B_EXECUTION_OR_RELEASE_VALIDATION"


def report_metric(block: Mapping[str, Any], aliases: Sequence[str], label: str) -> Any:
    return first(block, aliases, field=label, default=None)


def make_report(
    summary: Mapping[str, Any],
    verdict: Mapping[str, Any],
    components: Mapping[str, Any],
    derived_metrics: Mapping[str, Mapping[str, Any]],
    pre_target_commit: str,
    firewall: Mapping[str, Any],
) -> str:
    global_status = str(verdict["global_status"])
    terminal = str(summary["terminal_status"])
    rows: list[str] = [
        "# H-MSO-01R-B fresh confirmatory multiscale identifiability requalification report",
        "",
        f"Terminal status: `{terminal}`.",
        "",
        "This release evaluates only the prospectively frozen H-MSO-01R hypothesis on the 384-case R-A atlas. `DNN` means Descriptor Nearest-Neighbour and Candidate C is its only formal statistic. Historical H-MSO-01 remains permanently NOT_EVALUABLE. No neural model, attention model, optimizer, training, time integration, solver-in-loop, rollout, sealed test, ARC access, or MSO-03 execution occurred.",
        "",
        "## Candidate C, CVAR, oracle, and coverage",
        "",
        "| Component | SS Candidate C D (UCB) | MS Candidate C D (UCB) | MS/SS Candidate C ratio (UCB) | SS/MS CVAR (rescue ratio/UCB) | SS/MS oracle NRMSE (rescue ratio/UCB) |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for component in COMPONENTS:
        ss = metric_block(summary, "SS", component)
        ms = metric_block(summary, "MS", component)
        paired = paired_block(summary, component)
        rows.append(
            f"| `{component}` | {fmt(report_metric(ss, ('candidate_c_d','candidate_c','dnn','point'), 'ss candidate'))} ({fmt(report_metric(ss, ('candidate_c_simultaneous_ucb','candidate_c_ucb','dnn_simultaneous_ucb','simultaneous_ucb'), 'ss candidate ucb'))}) | "
            f"{fmt(report_metric(ms, ('candidate_c_d','candidate_c','dnn','point'), 'ms candidate'))} ({fmt(report_metric(ms, ('candidate_c_simultaneous_ucb','candidate_c_ucb','dnn_simultaneous_ucb','simultaneous_ucb'), 'ms candidate ucb'))}) | "
            f"{fmt(report_metric(paired, ('candidate_c_ratio','dnn_ratio'), 'candidate ratio'))} ({fmt(report_metric(paired, ('candidate_c_ratio_simultaneous_ucb','candidate_c_ratio_ucb','dnn_ratio_simultaneous_ucb'), 'candidate ratio ucb'))}) | "
            f"{fmt(report_metric(ss, ('conditional_variance','cvar'), 'ss cvar'))}/{fmt(report_metric(ms, ('conditional_variance','cvar'), 'ms cvar'))} ({fmt(report_metric(paired, ('conditional_variance_ratio','cvar_ratio'), 'cvar ratio'))}/{fmt(report_metric(paired, ('conditional_variance_ratio_simultaneous_ucb','cvar_ratio_ucb'), 'cvar ratio ucb'))}) | "
            f"{fmt(report_metric(ss, ('oracle_nrmse',), 'ss oracle'))}/{fmt(report_metric(ms, ('oracle_nrmse',), 'ms oracle'))} ({fmt(report_metric(paired, ('oracle_nrmse_ratio','oracle_ratio'), 'oracle ratio'))}/{fmt(report_metric(paired, ('oracle_nrmse_ratio_simultaneous_ucb','oracle_ratio_ucb'), 'oracle ratio ucb'))}) |"
        )
    rows.extend([
        "",
        "## Component decisions",
        "",
        "| Component | Evaluable | Absolute verdict | Relative-rescue verdict | Final status |",
        "|---|---:|---:|---:|---|",
    ])
    for component in COMPONENTS:
        value = components[component]
        absolute_evaluable = as_bool(
            first(value, ("absolute_evaluable",), field=f"report.{component}.absolute_evaluable"),
            field=f"report.{component}.absolute_evaluable",
        )
        relative_evaluable = as_bool(
            first(value, ("relative_rescue_evaluable",), field=f"report.{component}.relative_rescue_evaluable"),
            field=f"report.{component}.relative_rescue_evaluable",
        )
        rows.append(
            f"| `{component}` | {fmt(value['component_evaluable'])} | "
            f"{side_verdict(evaluable=absolute_evaluable, passed=as_bool(value['absolute_pass'], field=f'report.{component}.absolute_pass'))} | "
            f"{side_verdict(evaluable=relative_evaluable, passed=as_bool(value['relative_rescue_pass'], field=f'report.{component}.relative_rescue_pass'))} | "
            f"`{value['status']}` |"
        )

    wb_all_positive = all(
        float(metric_block(summary, arm, component).get("candidate_c_wb", metric_block(summary, arm, component).get("w_b", 0))) > 0
        for arm in ARMS for component in COMPONENTS
    )
    any_candidate_ne = any(
        not as_bool(first(metric_block(summary, arm, component), ("candidate_c_evaluable", "dnn_evaluable", "evaluable"), field="candidate evaluable"), field="candidate evaluable")
        for arm in ARMS for component in COMPONENTS
    ) or any(
        not as_bool(first(paired_block(summary, component), ("candidate_c_evaluable", "dnn_evaluable", "evaluable"), field="paired candidate evaluable"), field="paired candidate evaluable")
        for component in COMPONENTS
    )
    modifications = summary["post_target_modification_counts"]
    all_modifications_zero = all(as_int(modifications[key], field=key) == 0 for key in PROHIBITED_KEYS[11:])
    prohibited = firewall["prohibited_activity_counts"]
    no_neural = all(as_int(prohibited[key], field=key) == 0 for key in ("neural_model_count", "attention_count", "transformer_count", "optimizer_count", "training_count"))
    simultaneous = summary["simultaneous_inference"]
    q11, q12, q13, q14, q15, q16, q17 = [], [], [], [], [], [], []
    q20, q21 = [], []
    for component in COMPONENTS:
        derived = derived_metrics[component]
        ss, ms = derived["candidate"]["SS"], derived["candidate"]["MS"]
        paired_values = derived["paired"]
        nd_ss, nd_ms = derived["non_dnn"]["SS"], derived["non_dnn"]["MS"]
        absolute_checks, relative_checks = derived["absolute_checks"], derived["relative_checks"]
        q11.append(
            f"`{component}` SS={fmt(ss['gate'])} [D={fmt(ss['point'])}, UCB={fmt(ss['ucb'])}]; "
            f"MS={fmt(ms['gate'])} [D={fmt(ms['point'])}, UCB={fmt(ms['ucb'])}]"
        )
        q12.append(
            f"`{component}`={fmt(paired_values['gate'])} [ratio={fmt(paired_values['ratio'])}, "
            f"UCB={fmt(paired_values['ucb'])}]"
        )
        q13.append(
            f"`{component}` SS={fmt(nd_ss['cvar'])} [UCB={fmt(nd_ss['cvar_ucb'])}]; "
            f"MS={fmt(nd_ms['cvar'])} [UCB={fmt(nd_ms['cvar_ucb'])}]; rescue ratio={fmt(report_metric(paired_block(summary, component), ('conditional_variance_ratio',), 'report cvar ratio'))}, "
            f"UCB={fmt(report_metric(paired_block(summary, component), ('conditional_variance_ratio_simultaneous_ucb',), 'report cvar ratio ucb'))}; "
            f"gates={fmt(absolute_checks['conditional_variance_point'] and absolute_checks['conditional_variance_simultaneous_ucb'])}/{fmt(relative_checks['conditional_variance_point_ratio'] and relative_checks['conditional_variance_simultaneous_ratio_ucb'])}"
        )
        q14.append(
            f"`{component}` SS={fmt(nd_ss['oracle'])} [UCB={fmt(nd_ss['oracle_ucb'])}]; "
            f"MS={fmt(nd_ms['oracle'])} [UCB={fmt(nd_ms['oracle_ucb'])}]; rescue ratio={fmt(report_metric(paired_block(summary, component), ('oracle_nrmse_ratio',), 'report oracle ratio'))}, "
            f"UCB={fmt(report_metric(paired_block(summary, component), ('oracle_nrmse_ratio_simultaneous_ucb',), 'report oracle ratio ucb'))}; "
            f"gates={fmt(absolute_checks['oracle_nrmse_point'] and absolute_checks['oracle_nrmse_simultaneous_ucb'])}/{fmt(relative_checks['oracle_nrmse_point_ratio'] and relative_checks['oracle_nrmse_simultaneous_ratio_ucb'])}"
        )
        q15.append(
            f"`{component}`={fmt(absolute_checks['improvement_point'] and absolute_checks['improvement_simultaneous_lcb'])} "
            f"[SS improvement={fmt(nd_ss['improvement'])}, LCB={fmt(nd_ss['improvement_lcb'])}; "
            f"MS improvement={fmt(nd_ms['improvement'])}, LCB={fmt(nd_ms['improvement_lcb'])}]"
        )
        family_details = ", ".join(
            f"{family}={fmt(nd_ms['family'][family])}/UCB {fmt(nd_ms['family_ucb'][family])} "
            f"({fmt(derived['family_point_checks'][family] and derived['family_bound_checks'][family])})"
            for family in FAMILIES
        )
        ss_family_values = list(nd_ss["family"].values())
        ms_family_values = list(nd_ms["family"].values())
        report_worst_ss = max(ss_family_values) if all(value is not None for value in ss_family_values) else None
        report_worst_ms = max(ms_family_values) if all(value is not None for value in ms_family_values) else None
        q16.append(
            f"`{component}` absolute families [{family_details}]; worst SS/MS={fmt(report_worst_ss)}/{fmt(report_worst_ms)}; "
            f"paired <=0.05 guard={fmt(relative_checks['worst_family_guard'])}"
        )
        coverage_family_ss = ", ".join(
            f"{family}={fmt(nd_ss['coverage_family'][family])}"
            for family in FAMILIES
        )
        coverage_family_ms = ", ".join(
            f"{family}={fmt(nd_ms['coverage_family'][family])} ({fmt(derived['coverage_family_checks'][family])})"
            for family in FAMILIES
        )
        coverage_folds_ss = ", ".join(
            f"FOLD_{fold}={fmt(nd_ss['coverage_fold'][f'FOLD_{fold}'])}"
            for fold in FOLDS
        )
        coverage_folds_ms = ", ".join(
            f"FOLD_{fold}={fmt(nd_ms['coverage_fold'][f'FOLD_{fold}'])}"
            for fold in FOLDS
        )
        q17.append(
            f"`{component}` overall SS/MS={fmt(nd_ss['coverage'])}/{fmt(nd_ms['coverage'])} (MS gate {fmt(absolute_checks['coverage_overall'])}); "
            f"SS families [{coverage_family_ss}], MS families [{coverage_family_ms}]; "
            f"SS folds [{coverage_folds_ss}], MS folds [{coverage_folds_ms}] all-valid={fmt(absolute_checks['all_six_folds_valid'])}; "
            f"paired guard={fmt(relative_checks['coverage_guard'])}"
        )
        q20.append(
            f"`{component}`={side_verdict(evaluable=bool(derived['absolute_evaluable']), passed=bool(derived['absolute_pass']))}"
        )
        q21.append(
            f"`{component}`={side_verdict(evaluable=bool(derived['relative_rescue_evaluable']), passed=bool(derived['relative_rescue_pass']))}"
        )
    rows.extend([
        "",
        "## Required 30 answers",
        "",
        "1. **Yes: 384/384.** Every formal case completed every frozen target/reference qualification check before analysis.",
        "2. **Yes.** Every formal defect is reference minus the frozen lambda=1 base SPH operator; no 0.75/1.25/1.50 defect target was generated.",
        f"3. **Yes.** The fresh observable store remained `{OBSERVABLE_SHA256}` before target generation, after generation, after analysis, and at release.",
        "4. **Yes: SS=39 and MS=110.** No column was added or removed.",
        f"5. **Yes.** Pointwise Candidate C division count is `{summary['pointwise_division_count']}`; only post-aggregation divisions were performed.",
        f"6. **{'Yes' if wb_all_positive else 'No'}.** Component/arm W(B) values are serialized in the Candidate C metric tables.",
        f"7. **{'Yes' if any_candidate_ne else 'No'}.** Exact Candidate C evaluability/status values, including the canonical CA zero status where applicable, are serialized componentwise.",
        "8. **SS Candidate C D/UCB:** listed for all three components in the metric table above.",
        "9. **MS Candidate C D/UCB:** listed for all three components in the metric table above.",
        "10. **Candidate C SS→MS point ratio/UCB:** listed for all three components in the metric table above.",
        "11. **Candidate C absolute gates:** " + "; ".join(q11) + ".",
        "12. **Candidate C relative gates:** " + "; ".join(q12) + ".",
        "13. **CVAR SS/MS and rescue:** " + "; ".join(q13) + ".",
        "14. **Oracle SS/MS NRMSE and rescue:** " + "; ".join(q14) + ".",
        "15. **Mean-baseline improvement:** " + "; ".join(q15) + ".",
        "16. **Worst-family gates:** " + "; ".join(q16) + ".",
        "17. **Coverage overall/family/fold:** " + "; ".join(q17) + ". Coverage was used only as geometry evidence.",
        f"18. **Yes.** Method `{simultaneous['method']}`, confidence `{simultaneous['confidence_level']}`, scope `{simultaneous['multiplicity_scope']}`; every required bound procedure executed and emitted a status row (a legitimate `NOT_EVALUABLE` row does not claim a numeric bound).",
        "19. **Component evaluability:** shown in the component-decision table above, with all mandatory metric/fold flags in `component_verdicts.csv`.",
        "20. **Component absolute verdicts:** " + "; ".join(q20) + ".",
        "21. **Component relative-rescue verdicts:** " + "; ".join(q21) + ".",
        "22. **Final component statuses:** shown above using the frozen five-state taxonomy.",
        f"23. **Global H-MSO-01R:** `{global_status}`.",
        f"24. **No.** All target-derived scientific modification counts are zero: `{all_modifications_zero}`.",
        f"25. **No.** Neural/attention/Transformer/optimizer/training counts are all zero: `{no_neural}`.",
        f"26. **Only eligibility if qualified:** `MSO03_DETERMINISTIC_CLOSURE_BASELINE_ELIGIBLE={verdict['mso03_deterministic_closure_baseline_eligible']}`; MSO-03 was not executed.",
        "27. **Yes.** Under NOT_QUALIFIED/NOT_EVALUABLE, all learning routes and MSO-03 eligibility remain false; under QUALIFIED, all learning routes still remain false.",
        "28. **Yes.** Old H-MSO-01 remains permanently `H_MSO01_MULTISCALE_IDENTIFIABILITY_RESCUE_NOT_EVALUABLE`.",
        f"29. **Git:** `HMSO01R_A_FINAL_COMMIT={R_A_FINAL_COMMIT}`, `HMSO01R_B_PRE_TARGET_COMMIT={pre_target_commit}`, `HMSO01R_B_FINAL_COMMIT={FINAL_COMMIT_SENTINEL}` pending the non-amended release commit.",
        f"30. **Final terminal status:** `{terminal}`.",
        "",
        "## Governance disclosure and stop",
        "",
        "R-A's frozen synthetic-preflight CSVs and firewall counters were eligibility evidence but were not executable-bound call traces or OS-level access proofs. R-B therefore ran an executable-bound synthetic preflight before first target/reference access and emitted direct target-access, Candidate C division, bootstrap, and firewall ledgers. This disclosure changes no frozen scientific value.",
        "",
        "The scoped pre-target lambda-one base-operator identity audit matched 384/384 cases (ordered digest `4cf2df0d4b4bcf25ee497e89a12f6edb07bdeae7b195f5ca100bedef79467e40`) and performed no analytical/reference evaluation, defect generation, target read/write, or historical outcome read. It was not first target access.",
        "",
        "H-MSO-01R-B stops here. MSO-03, neural models, attention, learned operators, optimization, and training remain unexecuted.",
    ])
    return "\n".join(rows)


def main() -> None:
    if MANIFEST.exists() or REPORT.exists() or STATUS.exists():
        refuse(
            "HMSO01R_B_EXISTING_RELEASE_REQUIRES_INDEPENDENT_FULL_AUDIT",
            "refusing mutable-manifest resume or overwrite",
        )

    branch = str(git("branch", "--show-current"))
    head = str(git("rev-parse", "HEAD"))
    remotes = str(git("remote")).split()
    require(branch == "main" and not remotes, "HMSO01R_B_RELEASE_GIT_BOUNDARY_FAILURE")
    dirty_release_paths = validate_release_worktree_scope()

    for relative in RUNTIME_ARTIFACTS:
        require((ROOT / relative).is_file(), "HMSO01R_B_REQUIRED_ARTIFACT_MISSING", relative)
    for relative in FORBIDDEN_OLD_DNN_ARTIFACTS:
        require(not (ROOT / relative).exists(), "HMSO01R_B_OLD_POINTWISE_DNN_ARTIFACT_FORBIDDEN", relative)
    for path in (FREEZE, HANDOFF, CONTRACT, IMPORT_MANIFEST, TARGET_ROLE, TARGET_BUILDER, FORMAL_EVALUATOR, FINALIZER):
        require(path.is_file(), "HMSO01R_B_REQUIRED_ARTIFACT_MISSING", str(path.relative_to(ROOT)))

    freeze = json_load(FREEZE)
    preflight = json_load(PREFLIGHT)
    target_ledger = json_load(TARGET_LEDGER)
    division = json_load(DIVISION_AUDIT)
    firewall = json_load(FIREWALL)
    summary = json_load(SUMMARY)
    qualification_rows = csv_load(QUALIFICATION)
    join_rows = csv_load(JOIN_AUDIT)
    import_rows = csv_load(IMPORT_MANIFEST)
    validate_import_manifest(import_rows)

    bootstrap_identity = validate_frozen_bootstrap_draws()
    pre_target_commit = validate_target_ledger(target_ledger)
    require(head == pre_target_commit, "HMSO01R_B_RELEASE_HEAD_NOT_PRE_TARGET_COMMIT")
    require(str(git("show", "-s", "--format=%s", pre_target_commit)) == "H-MSO-01R-B: freeze fresh confirmatory execution", "HMSO01R_B_PRE_TARGET_COMMIT_SUBJECT_FAILURE")
    require(str(git("rev-parse", f"{pre_target_commit}^")) == R_A_FINAL_COMMIT, "HMSO01R_B_PRE_TARGET_COMMIT_PARENT_FAILURE")
    frozen_paths = validate_freeze(freeze, pre_target_commit, target_ledger)
    validate_preflight(preflight, pre_target_commit, bootstrap_identity)
    qualification_case_ids = validate_qualification(qualification_rows)
    validate_join(join_rows, qualification_case_ids)
    division_records = validate_division_audit(division)
    authorized_counts = validate_firewall(firewall)

    parsed_csvs: dict[str, list[dict[str, str]]] = {}
    for relative in CSV_COMPONENT_ARTIFACTS:
        rows = csv_load(ROOT / relative)
        ensure_component_coverage(rows, relative)
        parsed_csvs[relative] = rows
    coverage_rows = csv_load(OUT / "coverage_metrics.csv")
    require(any(row.get("scope", row.get("aggregation_scope", "")).lower() == "overall" for row in coverage_rows), "HMSO01R_B_COVERAGE_SCOPE_INCOMPLETE", "overall")
    require(any(row.get("scope", row.get("aggregation_scope", "")).lower() in {"family", "familywise"} for row in coverage_rows), "HMSO01R_B_COVERAGE_SCOPE_INCOMPLETE", "family")
    require(any(row.get("scope", row.get("aggregation_scope", "")).lower() in {"fold", "foldwise"} for row in coverage_rows), "HMSO01R_B_COVERAGE_SCOPE_INCOMPLETE", "fold")

    verdict, components, derived_metrics = validate_summary(
        summary,
        firewall,
        division,
        division_records,
        parsed_csvs,
        coverage_rows,
    )
    require(first(summary, ("hmso01r_b_pre_target_commit", "pre_target_commit"), field="summary.pre_target_commit") == pre_target_commit, "HMSO01R_B_FORMAL_OUTPUT_BINDING_FAILURE", "pre-target commit")
    require(first(summary, ("target_store_sha256",), field="summary.target store") == sha256(TARGET_STORE), "HMSO01R_B_TARGET_STORE_LEDGER_IDENTITY_FAILURE")

    generated_release_paths = (
        str(REPORT.relative_to(ROOT)),
        str(MANIFEST.relative_to(ROOT)),
        str(STATUS.relative_to(ROOT)),
    )
    all_paths = list(dict.fromkeys([
        *frozen_paths,
        str(FREEZE.relative_to(ROOT)),
        *RUNTIME_ARTIFACTS,
        *generated_release_paths,
    ]))
    non_generated = [relative for relative in all_paths if relative not in generated_release_paths]
    for relative in non_generated:
        path = ROOT / relative
        require(path.is_file(), "HMSO01R_B_REQUIRED_ARTIFACT_MISSING", relative)
        # Frozen historical manifests/ledgers are identity-checked opaquely above;
        # never parse their outcome payloads.  Only direct R-B runtime evidence
        # and the explicitly whitelisted R-B provenance CSV are schema-opened.
        if relative in RUNTIME_ARTIFACTS and path.suffix == ".json":
            json_load(path)
        elif (relative in RUNTIME_ARTIFACTS or relative == str(IMPORT_MANIFEST.relative_to(ROOT))) and path.suffix == ".csv":
            csv_load(path)

    staging = OUT / ".release_staging" / sha256(SUMMARY)
    require(not staging.exists(), "HMSO01R_B_CONFLICTING_RELEASE_STAGING_EXISTS", str(staging))
    staging.mkdir(parents=True)
    staged_report = staging / REPORT.name
    staged_status = staging / STATUS.name
    staged_manifest = staging / MANIFEST.name
    write_text(staged_report, make_report(summary, verdict, components, derived_metrics, pre_target_commit, firewall))

    terminal = str(summary["terminal_status"])
    global_status = str(verdict["global_status"])
    status_payload = {
        "schema_version": "1.0.0",
        "project": "SPH-MSO-PoC",
        "stage": "H-MSO-01R-B",
        "date": "2026-08-13",
        "timezone": "Asia/Shanghai",
        "terminal_status": terminal,
        "h_mso01r_global_status": global_status,
        "component_status": {component: components[component]["status"] for component in COMPONENTS},
        "component_evaluability": {
            component: {
                "absolute_evaluable": derived_metrics[component]["absolute_evaluable"],
                "relative_rescue_evaluable": derived_metrics[component]["relative_rescue_evaluable"],
                "component_evaluable": derived_metrics[component]["component_evaluable"],
                "not_evaluable_mechanisms": derived_metrics[component]["not_evaluable_mechanisms"],
            }
            for component in COMPONENTS
        },
        "component_absolute_verdict": {
            component: side_verdict(
                evaluable=bool(derived_metrics[component]["absolute_evaluable"]),
                passed=bool(derived_metrics[component]["absolute_pass"]),
            )
            for component in COMPONENTS
        },
        "component_relative_rescue_verdict": {
            component: side_verdict(
                evaluable=bool(derived_metrics[component]["relative_rescue_evaluable"]),
                passed=bool(derived_metrics[component]["relative_rescue_pass"]),
            )
            for component in COMPONENTS
        },
        "target_reference_qualified_case_count": 384,
        "target_reference_failed_case_count": 0,
        "ss_feature_dimension": 39,
        "ms_feature_dimension": 110,
        "bootstrap_draws_consumed": 10000,
        "observable_store_unchanged": True,
        "old_mso02b_permanently_not_evaluable": True,
        "old_h_mso01_permanently_not_evaluable": True,
        "mso03_deterministic_closure_baseline_eligible": verdict["mso03_deterministic_closure_baseline_eligible"],
        "mso03_executed": False,
        "neural_training_authorized": False,
        "attention_authorized": False,
        "learned_operator_authorized": False,
        "hmso01r_a_final_commit": R_A_FINAL_COMMIT,
        "hmso01r_b_pre_target_commit": pre_target_commit,
        "hmso01r_b_final_commit": FINAL_COMMIT_SENTINEL,
        "branch": "main",
        "remote": None,
        "push_performed": False,
        "report_sha256": sha256(staged_report),
        "target_store_sha256": sha256(TARGET_STORE),
        "pre_target_freeze_sha256": sha256(FREEZE),
        "post_target_modification_counts": summary["post_target_modification_counts"],
        "prohibited_activity_counts": firewall["prohibited_activity_counts"],
        "stop_after_hmso01r_b": True,
    }
    write_json(staged_status, status_payload)

    staged_by_relative = {
        str(REPORT.relative_to(ROOT)): staged_report,
        str(STATUS.relative_to(ROOT)): staged_status,
    }
    hash_cache: dict[str, str] = {}

    def registered_sha(relative: str) -> str:
        if relative == str(MANIFEST.relative_to(ROOT)):
            return "FINAL_GIT_BLOB_AT_HMSO01R_B_FINAL_COMMIT"
        if relative not in hash_cache:
            hash_cache[relative] = sha256(staged_by_relative.get(relative, ROOT / relative))
        return hash_cache[relative]

    registry = [
        {
            "path": relative,
            "sha256": registered_sha(relative),
            "role": role_for(relative),
            "stage": "H-MSO-01R-B",
            "source": source_for(relative),
            "consumption_status": consumption_for(relative),
        }
        for relative in all_paths
    ]
    manifest_payload = {
        "schema_version": "1.0.0",
        "project": "SPH-MSO-PoC",
        "stage": "H-MSO-01R-B",
        "date": "2026-08-13",
        "timezone": "Asia/Shanghai",
        "terminal_status": terminal,
        "git": {
            "branch": "main",
            "hmso01r_a_final_commit": R_A_FINAL_COMMIT,
            "hmso01r_b_pre_target_commit": pre_target_commit,
            "hmso01r_b_final_commit": FINAL_COMMIT_SENTINEL,
            "remote": None,
            "push_performed": False,
        },
        "manifest_self_binding": "FINAL_GIT_BLOB_AT_HMSO01R_B_FINAL_COMMIT",
        "decision_summary": {
            "qualified_target_cases": 384,
            "failed_target_cases": 0,
            "global_h_mso01r_status": global_status,
            "global_evaluable": verdict["global_evaluable"],
            "global_pass": verdict["global_pass"],
            "component_status": {component: components[component]["status"] for component in COMPONENTS},
            "component_absolute_verdict": {
                component: side_verdict(
                    evaluable=bool(derived_metrics[component]["absolute_evaluable"]),
                    passed=bool(derived_metrics[component]["absolute_pass"]),
                )
                for component in COMPONENTS
            },
            "component_relative_rescue_verdict": {
                component: side_verdict(
                    evaluable=bool(derived_metrics[component]["relative_rescue_evaluable"]),
                    passed=bool(derived_metrics[component]["relative_rescue_pass"]),
                )
                for component in COMPONENTS
            },
            "mso03_deterministic_closure_baseline_eligible": verdict["mso03_deterministic_closure_baseline_eligible"],
        },
        "activity_authorization": {
            "NEW_SCIENTIFIC_TARGET_EVALUATION": True,
            "TARGET_GENERATION": True,
            "TARGET_READ": True,
            "REFERENCE_OPERATOR_READ": True,
            "DNN_CANDIDATE_C_EVALUATION": True,
            "CONDITIONAL_VARIANCE_EVALUATION": True,
            "ORACLE_FIT": True,
            "COVERAGE_EVALUATION": True,
            "PAIRED_RESCUE_EVALUATION": True,
            "BOOTSTRAP_INFERENCE": True,
            "H_MSO01R_VERDICT": True,
            "OLD_POINTWISE_DNN_FORMAL_EVALUATION": False,
            "NEURAL_MODEL": False,
            "ATTENTION_MODEL": False,
            "TRANSFORMER_MODEL": False,
            "LEARNED_OPERATOR": False,
            "OPTIMIZER": False,
            "TRAINING": False,
            "TIME_INTEGRATION": False,
            "SOLVER_IN_LOOP": False,
            "ROLLOUT": False,
            "SEALED_TEST_ACCESS": False,
            "ARC_ACCESS": False,
            "MSO03_EXECUTED": False,
        },
        "authorized_activity_counts": authorized_counts,
        "prohibited_activity_counts": firewall["prohibited_activity_counts"],
        "governance_disclosure": {
            "r_a_preflight_and_firewall_evidence_limitations_disclosed": True,
            "r_b_executable_synthetic_preflight_required_and_passed": True,
            "direct_access_division_bootstrap_firewall_ledgers_required_and_validated": True,
            "target_blind_lambda_one_operator_identity_audit": freeze["pre_target_operator_identity_audit"],
            "historical_outcome_used": False,
        },
        "artifact_registry": registry,
        "validation": {
            "all_required_artifacts_present": True,
            "all_non_manifest_registered_sha256_recomputed_before_publication": True,
            "pre_target_git_blob_identities_verified": True,
            "frozen_evidence_identities_verified": True,
            "target_reference_qualification_384_of_384": True,
            "target_observable_join_49152_of_49152": True,
            "observable_store_unchanged": True,
            "representation_dimensions_39_110": True,
            "candidate_c_pointwise_division_count_zero": True,
            "candidate_c_expected_final_divisions_verified": True,
            "bootstrap_draws_10000_of_10000": True,
            "all_required_simultaneous_bounds_computed": True,
            "all_prohibited_counts_zero": True,
            "all_post_target_scientific_modification_counts_zero": True,
            "branch_main": True,
            "remote_none": True,
            "release_dirty_paths_restricted_to_expected_runtime_and_release_outputs": True,
            "release_dirty_path_count_before_publication": len(dirty_release_paths),
        },
        "authorization": {
            "mso03_deterministic_closure_baseline_eligible": verdict["mso03_deterministic_closure_baseline_eligible"],
            "mso03_executed": False,
            "neural_training_authorized": False,
            "attention_authorized": False,
            "learned_operator_authorized": False,
            "stage_stopped_after_hmso01r_b": True,
        },
    }
    write_json(staged_manifest, manifest_payload)

    # Parse and re-hash every staged release byte before any publication.
    json_load(staged_status)
    parsed_staged_manifest = json_load(staged_manifest)
    parsed_registry = first(parsed_staged_manifest, ("artifact_registry",), field="staged manifest artifact_registry")
    require(isinstance(parsed_registry, list) and len(parsed_registry) == len(all_paths), "HMSO01R_B_STAGED_MANIFEST_REGISTRY_FAILURE")
    observed_registry_paths: set[str] = set()
    for record in parsed_registry:
        require(isinstance(record, Mapping), "HMSO01R_B_STAGED_MANIFEST_REGISTRY_FAILURE")
        relative = str(first(record, ("path",), field="staged manifest registry path"))
        require(relative in all_paths and relative not in observed_registry_paths, "HMSO01R_B_STAGED_MANIFEST_REGISTRY_FAILURE", relative)
        observed_registry_paths.add(relative)
        require(first(record, ("sha256",), field=f"staged manifest {relative}.sha256") == registered_sha(relative), "HMSO01R_B_STAGED_MANIFEST_REGISTRY_HASH_FAILURE", relative)
    require(observed_registry_paths == set(all_paths), "HMSO01R_B_STAGED_MANIFEST_REGISTRY_FAILURE", "path set")
    require(status_payload["report_sha256"] == sha256(staged_report), "HMSO01R_B_STAGED_REPORT_IDENTITY_FAILURE")
    require(git("rev-parse", "HEAD") == head, "HMSO01R_B_GIT_HEAD_CHANGED_DURING_RELEASE_VALIDATION")
    validate_release_worktree_scope()

    for staged, final in ((staged_report, REPORT), (staged_status, STATUS), (staged_manifest, MANIFEST)):
        require(not final.exists(), "HMSO01R_B_CONFLICTING_PARTIAL_RELEASE", str(final))
        final.parent.mkdir(parents=True, exist_ok=True)
        temporary = final.with_suffix(final.suffix + ".publish.tmp")
        temporary.write_bytes(staged.read_bytes())
        temporary.replace(final)
        require(sha256(final) == sha256(staged), "HMSO01R_B_PUBLISHED_RELEASE_IDENTITY_FAILURE", str(final.relative_to(ROOT)))
    for staged in (staged_report, staged_status, staged_manifest):
        staged.unlink()
    staging.rmdir()
    validate_release_worktree_scope()
    print(json.dumps({
        "status": terminal,
        "manifest_sha256": sha256(MANIFEST),
        "report_sha256": sha256(REPORT),
        "status_ledger_sha256": sha256(STATUS),
        "registered_artifacts": len(registry),
        "hmso01r_b_pre_target_commit": pre_target_commit,
        "hmso01r_b_final_commit": FINAL_COMMIT_SENTINEL,
    }, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
