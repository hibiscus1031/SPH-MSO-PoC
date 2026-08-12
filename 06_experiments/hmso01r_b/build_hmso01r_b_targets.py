#!/usr/bin/env python3
"""Build the isolated H-MSO-01R-B full-case analytical target store.

The executable has one semantic scientific input: the frozen H-MSO-01R-A
formal atlas.  It uses hash-bound analytical/reference and lambda-one operator
code.  The frozen particle-sample registry and observable store are byte-hashed
only; neither NPZ/JSON payload is loaded here.  In particular this module has
no array-loader invocation and cannot inspect an observable matrix.

The exact, already-qualified numerical case evaluator is reused from the
hash-bound MSO-02B target builder as a code helper.  Importing that module does
not execute its ``main``.  Its old input/output path globals are disabled before
the helper is called, and no historical result, report, checkpoint, target
store, or metric artifact is opened.
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
from types import ModuleType
from typing import Any, BinaryIO
import zipfile

import numpy as np
import torch


ROOT = Path(__file__).resolve().parents[2]
DDO_ROOT = Path("/Users/xiejinbo/Documents/SPH-DDO-PoC")

FORMAL_ATLAS = ROOT / "05_registries/hmso01r_a_formal_fresh_atlas_registry.json"
FORMAL_SAMPLE = ROOT / "05_registries/hmso01r_a_formal_particle_sample_registry.json"
OBSERVABLE = ROOT / "06_experiments/hmso01r_a/observable/hmso01r_a_observable_store.npz"
PRE_TARGET_FREEZE = ROOT / "08_manifests/hmso01r_b_pre_target_freeze.json"
IMPORT_MANIFEST = ROOT / "01_provenance/hmso01r_b_target_reference_import_manifest.csv"
ROLE_REGISTRY = ROOT / "05_registries/hmso01r_b_target_role_registry.json"
REFERENCE_MODULE = ROOT / "01_provenance/vendor/ddo_analytical_reference/mso02b_target_reference.py"
EVALUATOR_HELPER = ROOT / "06_experiments/mso02b/build_mso02b_targets.py"
FORMAL_ANALYSIS_HELPER_SOURCE = ROOT / "06_experiments/mso02b/run_mso02b_formal.py"
FORMAL_EVALUATOR = ROOT / "06_experiments/hmso01r_b/run_hmso01r_b_formal.py"
FINALIZER = ROOT / "06_experiments/hmso01r_b/finalize_hmso01r_b_release.py"
PREFLIGHT = ROOT / "06_experiments/hmso01r_b/candidate_c_implementation_preflight.json"

OUT = ROOT / "06_experiments/hmso01r_b"
TARGET_DIR = OUT / "target_ref"
TARGET_STORE = TARGET_DIR / "hmso01r_b_target_store.npz"
QUALIFICATION = OUT / "target_reference_qualification.csv"
LEDGER = OUT / "target_access_ledger.json"

HMSO01R_A_FINAL_COMMIT = "9048eff137001e5f644575bd02c3856b4f4ac532"
PRE_TARGET_COMMIT_SUBJECT = "H-MSO-01R-B: freeze fresh confirmatory execution"
DDO_SOURCE_HEAD = "d76d29ae51e8104641b710371f0fcb248d5ea268"
PRE_TARGET_COMMIT_SENTINEL = "DISCOVERED_AT_FIRST_TARGET_ACCESS_FROM_CLEAN_HEAD"
PRE_TARGET_BINDING_MODE = "DISCOVER_PRE_TARGET_COMMIT_AT_FIRST_TARGET_ACCESS_FROM_CLEAN_HEAD"
PRETARGET_OPERATOR_ORDERED_DIGEST = "4cf2df0d4b4bcf25ee497e89a12f6edb07bdeae7b195f5ca100bedef79467e40"

EXPECTED_FORMAL_ATLAS_SHA256 = "7fd7aa6c8415051ad83f0028b75b4684121886cb3645060e4e5c3ac54ebc268a"
EXPECTED_FORMAL_SAMPLE_SHA256 = "a4b7da1a9f6e4efab7ccbc9ec3bb5e4235a82aef30ce64017895df05ab1c2b01"
EXPECTED_OBSERVABLE_SHA256 = "65ca1a7fea58248207fc5a22e14855b4a84c392c7ef17cefdf2d396687cc38cd"
EXPECTED_BOOTSTRAP_DRAWS_SHA256 = "3a5853ce6b353c8c2584b0f95651904fb1506a0a3e3af6985981374789d4667e"
EXPECTED_REFERENCE_SHA256 = "cd0d8794efa1900f307710e27438939bbff282aa0aa617629eab1f64427bc017"
EXPECTED_HELPER_SHA256 = "940a671927b20f219a4d2553ab61f36bc568e1c8e29bd9f043edd44103f1a08f"
EXPECTED_FORMAL_ANALYSIS_HELPER_SOURCE_SHA256 = "55b0b63eb2c99364c8a2e96c75191a50707e93357f7039bd9edfdcb7c7c831b7"

DDO_SOURCE_SHA256 = {
    "08_scripts/ddo01d_atlas_builder.py": "ce523095e21cca07f247ef91efde878c05ea7745a1899c04a6d73fd0e2ffc44a",
    "08_scripts/ddo01a_preflight.py": "8ea2720fae9277ac6356d166d0443b6f666c6e23534aed37267d06273da7a3c2",
    "08_scripts/ddo01ar_requalification.py": "b4191e69b63e7118a305af888e107ed78a29501596f0659d4ba18e3f304c01cb",
    "01_imported_baseline/structure_preserving/__init__.py": "18afa8e375e06bd03ce68f17528c7a27722e1dbdab17536d1b060994446ad93a",
    "01_imported_baseline/structure_preserving/neighborhood.py": "44d61e0abbc9901472dae90f83127f5231fc3f6e8ac92a971228dfdcb230aaa8",
    "01_imported_baseline/structure_preserving/kernels.py": "bad08e0f49b308c568cd438c9981abd2c906e16c6570ebc0ca7d19d9847b333b",
    "01_imported_baseline/structure_preserving/conservative_pressure.py": "b6366666ba89cc1f367a95390a411905eee8b7f55fba28a024f5732860004064",
    "01_imported_baseline/structure_preserving/conservative_viscosity.py": "bdfbcb457f6973130f0131ec3c0a3fecc7197dd117c8256163cf3a1445307852",
}

VENDOR_OPERATOR_SHA256 = {
    "01_provenance/vendor/pio_stage01c_static/structure_preserving/__init__.py": "18afa8e375e06bd03ce68f17528c7a27722e1dbdab17536d1b060994446ad93a",
    "01_provenance/vendor/pio_stage01c_static/structure_preserving/neighborhood.py": "44d61e0abbc9901472dae90f83127f5231fc3f6e8ac92a971228dfdcb230aaa8",
    "01_provenance/vendor/pio_stage01c_static/structure_preserving/kernels.py": "bad08e0f49b308c568cd438c9981abd2c906e16c6570ebc0ca7d19d9847b333b",
    "01_provenance/vendor/pio_stage01c_static/structure_preserving/conservative_pressure.py": "b6366666ba89cc1f367a95390a411905eee8b7f55fba28a024f5732860004064",
    "01_provenance/vendor/pio_stage01c_static/structure_preserving/conservative_viscosity.py": "bdfbcb457f6973130f0131ec3c0a3fecc7197dd117c8256163cf3a1445307852",
}

REQUIRED_PRE_TARGET_PATHS = {
    "00_project_contract/amendments/ca_mso01_zero_safe_dnn_semantics.md",
    "00_project_contract/hmso01r_b_fresh_confirmatory_execution_contract.md",
    "01_provenance/hmso01r_b_target_reference_import_manifest.csv",
    "05_registries/hmso01r_a_formal_fresh_atlas_registry.json",
    "05_registries/hmso01r_a_formal_particle_sample_registry.json",
    "05_registries/hmso01r_b_target_role_registry.json",
    "06_experiments/hmso01r_a/observable/hmso01r_a_observable_store.npz",
    "06_experiments/hmso01r_b/build_hmso01r_b_targets.py",
    "06_experiments/hmso01r_b/run_hmso01r_b_formal.py",
    "06_experiments/hmso01r_b/finalize_hmso01r_b_release.py",
    "06_experiments/hmso01r_b/candidate_c_implementation_preflight.json",
    "06_experiments/mso02b/build_mso02b_targets.py",
    "06_experiments/mso02b/run_mso02b_formal.py",
    "08_manifests/hmso01r_a_git_handoff.json",
    "01_provenance/vendor/ddo_analytical_reference/mso02b_target_reference.py",
    *VENDOR_OPERATOR_SHA256,
}

# Hash validation of current R-A evidence is permitted.  These paths are never
# valid freeze inputs for this target-only executable, even as opaque bytes.
PROHIBITED_HISTORICAL_PATH_PREFIXES = (
    "06_experiments/mso00/",
    "06_experiments/mso01/",
    "06_experiments/mso02a/",
    "06_experiments/mso02b/checkpoints/",
    "06_experiments/mso02b/target_ref/",
    "06_experiments/mso02c/",
    "07_reports/mso",
)
PROHIBITED_HISTORICAL_EXACT_PATHS = {
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

PRIMARY = ("density_rate", "pressure", "viscosity")
STORE_NAMES = {
    "density_rate": "target_density_rate",
    "pressure": "target_pressure_gradient_acceleration",
    "viscosity": "target_viscosity_laplacian_acceleration",
    "acceleration": "target_total_acceleration_derived",
}
CANONICAL_COMPONENT_NAMES = {
    "density_rate": "density_rate",
    "pressure": "pressure_gradient_acceleration",
    "viscosity": "viscosity_laplacian_acceleration",
    "acceleration": "total_acceleration_derived",
}


def _sha256_stream(handle: BinaryIO) -> str:
    digest = hashlib.sha256()
    for block in iter(lambda: handle.read(1024 * 1024), b""):
        digest.update(block)
    return digest.hexdigest()


def sha256(path: Path) -> str:
    """Hash bytes opaquely; this never interprets an NPZ or JSON payload."""

    with path.open("rb") as handle:
        return _sha256_stream(handle)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def nested_first(value: dict[str, Any], *paths: tuple[str, ...]) -> Any:
    """Return the first present nested preflight field, or fail closed."""

    for path in paths:
        current: Any = value
        for key in path:
            if not isinstance(current, dict) or key not in current:
                break
            current = current[key]
        else:
            return current
    rendered = "|".join(".".join(path) for path in paths)
    raise RuntimeError(f"HMSO01R_B_PREFLIGHT_REQUIRED_FIELD_MISSING:{rendered}")


def strict_bool(value: Any, *, field: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().upper()
        if normalized in {"TRUE", "1", "YES", "PASS", "PASSED"}:
            return True
        if normalized in {"FALSE", "0", "NO", "FAIL", "FAILED"}:
            return False
    raise RuntimeError(f"HMSO01R_B_PREFLIGHT_INVALID_BOOLEAN:{field}:{value!r}")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else ["status"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_deterministic_npz(path: Path, arrays: dict[str, np.ndarray]) -> None:
    """Write a byte-reproducible compressed NPZ with fixed member metadata."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with zipfile.ZipFile(
        temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for name in sorted(arrays):
            payload = io.BytesIO()
            np.lib.format.write_array(payload, np.asarray(arrays[name]), allow_pickle=False)
            info = zipfile.ZipInfo(f"{name}.npy", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            archive.writestr(
                info,
                payload.getvalue(),
                compress_type=zipfile.ZIP_DEFLATED,
                compresslevel=9,
            )
    temporary.replace(path)


def git_text(arguments: list[str], *, cwd: Path = ROOT) -> str:
    return subprocess.run(
        ["git", *arguments], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


def safe_relative_path(value: str) -> str:
    pure = PurePosixPath(value)
    if pure.is_absolute() or ".." in pure.parts or not pure.parts:
        raise RuntimeError(f"HMSO01R_B_INVALID_FROZEN_PATH:{value}")
    normalized = pure.as_posix()
    # Source executables are eligible for an explicit hash-bound code import;
    # historical numerical/result payloads under prior experiment directories
    # are not.  MSO-02B's two approved source helpers are handled by this exact
    # allowlist; no output, target, report, checkpoint, or old main is allowed.
    prior_experiment = normalized.startswith("06_experiments/mso")
    approved_prior_code = normalized in {
        "06_experiments/mso02b/build_mso02b_targets.py",
        "06_experiments/mso02b/run_mso02b_formal.py",
    }
    if prior_experiment and not approved_prior_code:
        raise RuntimeError(f"HMSO01R_B_PROHIBITED_HISTORICAL_ARTIFACT_PATH:{normalized}")
    if normalized in PROHIBITED_HISTORICAL_EXACT_PATHS or any(
        normalized.startswith(prefix) for prefix in PROHIBITED_HISTORICAL_PATH_PREFIXES
    ):
        raise RuntimeError(f"HMSO01R_B_PROHIBITED_HISTORICAL_ARTIFACT_PATH:{normalized}")
    return normalized


def git_blob_oid(commit: str, relative: str, *, cwd: Path = ROOT) -> tuple[str, str]:
    output = subprocess.run(
        ["git", "ls-tree", "-z", commit, "--", relative],
        cwd=cwd,
        check=True,
        capture_output=True,
    ).stdout
    records = [record for record in output.split(b"\0") if record]
    if len(records) != 1:
        raise RuntimeError(f"HMSO01R_B_GIT_BLOB_NOT_UNIQUE:{relative}")
    metadata, recorded_path = records[0].split(b"\t", 1)
    mode, kind, oid = metadata.decode("ascii").split()
    if kind != "blob" or mode not in {"100644", "100755"}:
        raise RuntimeError(f"HMSO01R_B_GIT_OBJECT_NOT_REGULAR_BLOB:{relative}:{mode}:{kind}")
    if recorded_path.decode("utf-8") != relative:
        raise RuntimeError(f"HMSO01R_B_GIT_PATH_IDENTITY_FAILURE:{relative}")
    return oid, mode


def git_blob_sha256(commit: str, relative: str, *, cwd: Path = ROOT) -> str:
    process = subprocess.Popen(
        ["git", "cat-file", "blob", f"{commit}:{relative}"],
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert process.stdout is not None
    digest = _sha256_stream(process.stdout)
    stderr = process.stderr.read() if process.stderr is not None else b""
    return_code = process.wait()
    if return_code:
        raise RuntimeError(
            f"HMSO01R_B_GIT_BLOB_READ_FAILURE:{relative}:{stderr.decode('utf-8', errors='replace')}"
        )
    return digest


def verify_freeze_entry(
    entry: dict[str, Any], *, head: str
) -> tuple[str, dict[str, Any]]:
    required = {"path", "sha256", "size_bytes", "git_blob_oid", "git_blob_sha256"}
    missing = sorted(required - set(entry))
    if missing:
        raise RuntimeError(f"HMSO01R_B_PRE_TARGET_FREEZE_SCHEMA_MISSING:{','.join(missing)}")
    relative = safe_relative_path(str(entry["path"]))
    path = ROOT / relative
    if not path.is_file() or path.is_symlink():
        raise RuntimeError(f"HMSO01R_B_FROZEN_INPUT_NOT_REGULAR_FILE:{relative}")
    actual_size = path.stat().st_size
    actual_sha = sha256(path)
    oid, mode = git_blob_oid(head, relative)
    blob_sha = git_blob_sha256(head, relative)
    expected_sha = str(entry["sha256"])
    expected_blob_sha = str(entry["git_blob_sha256"])
    if not (
        actual_size == int(entry["size_bytes"])
        and actual_sha == expected_sha
        and oid == str(entry["git_blob_oid"])
        and blob_sha == expected_blob_sha
        and expected_blob_sha == expected_sha
        and blob_sha == actual_sha
    ):
        raise RuntimeError(
            "HMSO01R_B_FROZEN_EVIDENCE_IDENTITY_FAILURE:"
            f"{relative}:fs={actual_sha}:blob={blob_sha}:oid={oid}:size={actual_size}"
        )
    return relative, {
        "sha256": actual_sha,
        "size_bytes": actual_size,
        "git_blob_oid": oid,
        "git_mode": mode,
    }


def validate_target_blind_preflight(
    preflight: dict[str, Any], *, verified: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    """Require the committed evaluator-bound synthetic preflight to pass.

    The preflight contains synthetic/governance evidence only.  Reading it does
    not access a real target, analytical reference evaluation, or observable
    payload.  Its file and evaluator have already been proved identical to the
    blobs at the discovered pre-target commit.
    """

    evaluator_relative = FORMAL_EVALUATOR.relative_to(ROOT).as_posix()
    preflight_relative = PREFLIGHT.relative_to(ROOT).as_posix()
    evaluator_identity = verified[evaluator_relative]
    preflight_identity = verified[preflight_relative]

    passed = nested_first(
        preflight,
        ("passed",),
        ("all_tests_passed",),
        ("status",),
    )
    if not strict_bool(passed, field="preflight.passed"):
        raise RuntimeError("HMSO01R_B_CANDIDATE_C_IMPLEMENTATION_PREFLIGHT_FAILURE")

    evaluator_sha = str(
        nested_first(
            preflight,
            ("formal_evaluator_sha256",),
            ("executable_identity", "sha256"),
        )
    )
    evaluator_oid = str(
        nested_first(
            preflight,
            ("formal_evaluator_git_blob_oid",),
            ("executable_identity", "git_blob_oid"),
        )
    )
    if (
        evaluator_sha != evaluator_identity["sha256"]
        or evaluator_oid != evaluator_identity["git_blob_oid"]
    ):
        raise RuntimeError("HMSO01R_B_PREFLIGHT_EXECUTABLE_IDENTITY_FAILURE")

    draw_count = int(
        nested_first(
            preflight,
            ("bootstrap_draw_count",),
            ("bootstrap", "draw_count"),
            ("bootstrap", "draws_consumed"),
        )
    )
    unique_draw_count = int(
        nested_first(
            preflight,
            ("bootstrap_unique_draw_count",),
            ("bootstrap", "unique_draw_count"),
        )
    )
    draw_sha = str(
        nested_first(
            preflight,
            ("bootstrap_draws_sha256",),
            ("bootstrap", "draws_sha256"),
        )
    )
    draw_identity = strict_bool(
        nested_first(
            preflight,
            ("bootstrap_draw_identity_match",),
            ("bootstrap", "draw_identity_match"),
        ),
        field="preflight.bootstrap.draw_identity_match",
    )
    if not (
        draw_count == 10_000
        and unique_draw_count == 10_000
        and draw_sha == EXPECTED_BOOTSTRAP_DRAWS_SHA256
        and draw_identity
    ):
        raise RuntimeError("HMSO01R_B_PREFLIGHT_BOOTSTRAP_IDENTITY_FAILURE")

    pointwise = int(
        nested_first(
            preflight,
            ("pointwise_division_count",),
            ("division_audit", "pointwise_division_count"),
        )
    )
    actual_divisions = int(
        nested_first(
            preflight,
            ("final_candidate_c_division_count",),
            ("division_audit", "final_candidate_c_division_count"),
        )
    )
    expected_divisions = int(
        nested_first(
            preflight,
            ("expected_final_candidate_c_division_count",),
            ("division_audit", "expected_final_candidate_c_division_count"),
        )
    )
    paired_identity = strict_bool(
        nested_first(
            preflight,
            ("paired_ss_ms_identity",),
            ("division_audit", "paired_ss_ms_identity"),
            ("bootstrap", "paired_ss_ms_identity"),
        ),
        field="preflight.paired_ss_ms_identity",
    )
    per_draw_reaggregation = strict_bool(
        nested_first(
            preflight,
            ("per_draw_reaggregation",),
            ("division_audit", "per_draw_reaggregation"),
            ("bootstrap", "per_draw_reaggregation"),
        ),
        field="preflight.per_draw_reaggregation",
    )
    if not (
        pointwise == 0
        and actual_divisions == expected_divisions
        and actual_divisions > 0
        and paired_identity
        and per_draw_reaggregation
    ):
        raise RuntimeError("HMSO01R_B_PREFLIGHT_CANDIDATE_C_DIVISION_FAILURE")

    zero_count_keys = (
        "target_payload_read_count",
        "observable_payload_read_count",
        "analytical_reference_evaluation_count",
        "defect_generation_count",
    )
    for key in zero_count_keys:
        value = int(nested_first(preflight, (key,), ("firewall", key)))
        if value != 0:
            raise RuntimeError(f"HMSO01R_B_PREFLIGHT_INFORMATION_FIREWALL_FAILURE:{key}")
    for key in (
        "epsilon_count",
        "clipping_count",
        "zero_row_deletion_count",
        "zero_group_deletion_count",
    ):
        value = int(nested_first(preflight, (key,), ("division_audit", key)))
        if value != 0:
            raise RuntimeError(f"HMSO01R_B_PREFLIGHT_ZERO_SAFE_SEMANTICS_FAILURE:{key}")

    scenario_coverage = nested_first(preflight, ("scenario_coverage",))
    if not isinstance(scenario_coverage, dict):
        raise RuntimeError("HMSO01R_B_PREFLIGHT_SCENARIO_COVERAGE_MISSING")
    required_scenarios = {
        "scalar",
        "vector",
        "isolated_zero_over_zero",
        "isolated_positive_over_zero",
        "zero_aggregate",
        "positive_aggregate",
        "zero_ss",
        "exact_zero_ms",
        "more_than_200_degenerate_draws_not_evaluable",
        "fewer_than_2_valid_draws_not_evaluable",
        "hierarchical_equal_weights",
    }
    if not required_scenarios.issubset(scenario_coverage) or not all(
        strict_bool(scenario_coverage[key], field=f"preflight.scenario_coverage.{key}")
        for key in required_scenarios
    ):
        raise RuntimeError("HMSO01R_B_PREFLIGHT_SCENARIO_COVERAGE_FAILURE")

    return {
        "sha256": preflight_identity["sha256"],
        "git_blob_oid": preflight_identity["git_blob_oid"],
        "formal_evaluator_sha256": evaluator_sha,
        "formal_evaluator_git_blob_oid": evaluator_oid,
        "bootstrap_draw_count": draw_count,
        "bootstrap_unique_draw_count": unique_draw_count,
        "bootstrap_draws_sha256": draw_sha,
        "pointwise_division_count": pointwise,
        "final_candidate_c_division_count": actual_divisions,
        "expected_final_candidate_c_division_count": expected_divisions,
        "paired_ss_ms_identity": paired_identity,
        "per_draw_reaggregation": per_draw_reaggregation,
        "all_required_scenarios_passed": True,
    }


def validate_pre_target_boundary() -> dict[str, Any]:
    """Validate clean Git handoff and every declared pre-target blob.

    This function runs before analytical/reference modules are imported and
    before any case evaluation.  Except for the freeze JSON itself, all listed
    artifacts are consumed as opaque byte streams only.
    """

    if any(path.exists() for path in (TARGET_STORE, QUALIFICATION, LEDGER)):
        raise RuntimeError("HMSO01R_B_TARGET_OUTPUT_ALREADY_EXISTS_REFUSING_REPLACEMENT")
    branch = git_text(["branch", "--show-current"])
    status = git_text(["status", "--porcelain=v1"])
    remotes = git_text(["remote"]).split()
    head = git_text(["rev-parse", "HEAD"])
    if branch != "main" or status or remotes:
        raise RuntimeError("HMSO01R_B_TARGET_EXECUTION_GIT_BOUNDARY_FAILURE")
    if head == HMSO01R_A_FINAL_COMMIT:
        raise RuntimeError("HMSO01R_B_PRE_TARGET_COMMIT_NOT_CREATED")
    commit_subject = git_text(["show", "-s", "--format=%s", head])
    parent_record = git_text(["rev-list", "--parents", "-n", "1", head]).split()
    if commit_subject != PRE_TARGET_COMMIT_SUBJECT:
        raise RuntimeError("HMSO01R_B_PRE_TARGET_COMMIT_SUBJECT_FAILURE")
    if parent_record != [head, HMSO01R_A_FINAL_COMMIT]:
        raise RuntimeError("HMSO01R_B_PRE_TARGET_DIRECT_PARENT_FAILURE")
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", HMSO01R_A_FINAL_COMMIT, head],
        cwd=ROOT,
        check=False,
        capture_output=True,
    )
    if ancestor.returncode != 0:
        raise RuntimeError("HMSO01R_B_PRE_TARGET_PARENT_ANCESTRY_FAILURE")
    if not PRE_TARGET_FREEZE.is_file():
        raise RuntimeError("HMSO01R_B_PRE_TARGET_FREEZE_MISSING")

    freeze_relative = PRE_TARGET_FREEZE.relative_to(ROOT).as_posix()
    freeze_sha = sha256(PRE_TARGET_FREEZE)
    freeze_oid, freeze_mode = git_blob_oid(head, freeze_relative)
    freeze_blob_sha = git_blob_sha256(head, freeze_relative)
    if freeze_sha != freeze_blob_sha:
        raise RuntimeError("HMSO01R_B_PRE_TARGET_FREEZE_WORKTREE_BLOB_MISMATCH")
    freeze = json.loads(PRE_TARGET_FREEZE.read_text(encoding="utf-8"))
    if freeze.get("status") != "FROZEN_BEFORE_FIRST_FRESH_TARGET_REFERENCE_ACCESS":
        raise RuntimeError("HMSO01R_B_PRE_TARGET_FREEZE_STATUS_FAILURE")
    binding = freeze.get("git_binding", {})
    binding_mode = binding.get("binding_mode", freeze.get("binding_mode"))
    declared_commit = binding.get("pre_target_commit", freeze.get("pre_target_commit"))
    if binding_mode != PRE_TARGET_BINDING_MODE or declared_commit != PRE_TARGET_COMMIT_SENTINEL:
        raise RuntimeError("HMSO01R_B_PRE_TARGET_COMMIT_BINDING_SEMANTICS_FAILURE")
    if (
        binding.get("parent_head_at_file_creation") != HMSO01R_A_FINAL_COMMIT
        or binding.get("branch") != "main"
        or binding.get("remote") is not None
        or binding.get("working_tree_clean_required") is not True
    ):
        raise RuntimeError("HMSO01R_B_PRE_TARGET_FREEZE_GIT_BOUNDARY_FAILURE")

    entries: list[dict[str, Any]] = []
    for section in ("frozen_inputs", "execution_artifacts"):
        section_entries = freeze.get(section)
        if not isinstance(section_entries, list) or not section_entries:
            raise RuntimeError(f"HMSO01R_B_PRE_TARGET_FREEZE_SECTION_INVALID:{section}")
        if not all(isinstance(item, dict) for item in section_entries):
            raise RuntimeError(f"HMSO01R_B_PRE_TARGET_FREEZE_SECTION_INVALID:{section}")
        entries.extend(section_entries)

    verified: dict[str, dict[str, Any]] = {}
    for entry in entries:
        relative, identity = verify_freeze_entry(entry, head=head)
        if relative in verified:
            raise RuntimeError(f"HMSO01R_B_PRE_TARGET_FREEZE_DUPLICATE_PATH:{relative}")
        verified[relative] = identity
    missing_paths = sorted(REQUIRED_PRE_TARGET_PATHS - set(verified))
    if missing_paths:
        raise RuntimeError(
            "HMSO01R_B_PRE_TARGET_FREEZE_REQUIRED_PATH_MISSING:" + ";".join(missing_paths)
        )

    preflight_payload = json.loads(PREFLIGHT.read_text(encoding="utf-8"))
    if not isinstance(preflight_payload, dict):
        raise RuntimeError("HMSO01R_B_PREFLIGHT_INVALID_JSON_ROOT")
    preflight_attestation = validate_target_blind_preflight(
        preflight_payload, verified=verified
    )

    expected_hashes = {
        FORMAL_ATLAS.relative_to(ROOT).as_posix(): EXPECTED_FORMAL_ATLAS_SHA256,
        FORMAL_SAMPLE.relative_to(ROOT).as_posix(): EXPECTED_FORMAL_SAMPLE_SHA256,
        OBSERVABLE.relative_to(ROOT).as_posix(): EXPECTED_OBSERVABLE_SHA256,
        REFERENCE_MODULE.relative_to(ROOT).as_posix(): EXPECTED_REFERENCE_SHA256,
        EVALUATOR_HELPER.relative_to(ROOT).as_posix(): EXPECTED_HELPER_SHA256,
        FORMAL_ANALYSIS_HELPER_SOURCE.relative_to(ROOT).as_posix(): EXPECTED_FORMAL_ANALYSIS_HELPER_SOURCE_SHA256,
        **VENDOR_OPERATOR_SHA256,
    }
    mismatches = [
        f"{relative}:{verified[relative]['sha256']}!={expected}"
        for relative, expected in expected_hashes.items()
        if verified[relative]["sha256"] != expected
    ]
    if mismatches:
        raise RuntimeError(
            "HMSO01R_B_FROZEN_EVIDENCE_IDENTITY_FAILURE:" + ";".join(mismatches)
        )

    operator_audit = freeze.get("pre_target_operator_identity_audit")
    if not isinstance(operator_audit, dict):
        raise RuntimeError("HMSO01R_B_PRETARGET_OPERATOR_IDENTITY_AUDIT_MISSING")
    if not (
        operator_audit.get("target_blind") is True
        and int(operator_audit.get("count", -1)) == 384
        and int(operator_audit.get("matched", -1)) == 384
        and operator_audit.get("ordered_digest") == PRETARGET_OPERATOR_ORDERED_DIGEST
    ):
        raise RuntimeError("HMSO01R_B_PRETARGET_OPERATOR_IDENTITY_AUDIT_FAILURE")
    for key, value in operator_audit.items():
        if any(token in key for token in ("analytical", "reference", "defect", "target", "history")) and (
            key.endswith("_count") or key.endswith("_read") or key.endswith("_write")
        ):
            if key != "target_blind" and int(value) != 0:
                raise RuntimeError(f"HMSO01R_B_PRETARGET_OPERATOR_AUDIT_FIREWALL_FAILURE:{key}")

    return {
        "branch": branch,
        "head": head,
        "remote": None,
        "working_tree_clean": True,
        "freeze_sha256": freeze_sha,
        "freeze_git_blob_oid": freeze_oid,
        "freeze_git_blob_sha256": freeze_blob_sha,
        "freeze_git_mode": freeze_mode,
        "verified": verified,
        "verified_artifact_count": len(verified),
        "preflight_attestation": preflight_attestation,
    }


def validate_external_ddo_sources() -> dict[str, dict[str, str]]:
    if not DDO_ROOT.is_dir():
        raise RuntimeError("HMSO01R_B_DDO_SOURCE_ROOT_MISSING")
    head = git_text(["rev-parse", "HEAD"], cwd=DDO_ROOT)
    if head != DDO_SOURCE_HEAD:
        raise RuntimeError(f"HMSO01R_B_DDO_SOURCE_HEAD_MISMATCH:{head}")
    identities: dict[str, dict[str, str]] = {}
    for relative, expected in DDO_SOURCE_SHA256.items():
        path = DDO_ROOT / relative
        actual = sha256(path)
        oid, _ = git_blob_oid(head, relative, cwd=DDO_ROOT)
        blob_sha = git_blob_sha256(head, relative, cwd=DDO_ROOT)
        if actual != expected or blob_sha != expected:
            raise RuntimeError(
                f"HMSO01R_B_DDO_SOURCE_IDENTITY_FAILURE:{relative}:{actual}:{blob_sha}"
            )
        identities[relative] = {
            "sha256": actual,
            "git_blob_oid": oid,
            "git_blob_sha256": blob_sha,
        }
    return identities


def load_hash_bound_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"HMSO01R_B_MODULE_LOAD_SPEC_FAILURE:{path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_target_only_evaluator() -> tuple[ModuleType, ModuleType]:
    if sha256(REFERENCE_MODULE) != EXPECTED_REFERENCE_SHA256:
        raise RuntimeError("HMSO01R_B_REFERENCE_MODULE_HASH_MISMATCH")
    if sha256(EVALUATOR_HELPER) != EXPECTED_HELPER_SHA256:
        raise RuntimeError("HMSO01R_B_EVALUATOR_HELPER_HASH_MISMATCH")
    sys.dont_write_bytecode = True
    reference = load_hash_bound_module("hmso01r_b_hash_bound_reference", REFERENCE_MODULE)
    helper = load_hash_bound_module("hmso01r_b_hash_bound_evaluator_helper", EVALUATOR_HELPER)
    helper.ref = reference

    # The reused evaluate_case function does not reference these globals.  Null
    # them so the imported helper cannot accidentally expose any old payload to
    # this execution path.  Its main is replaced by a hard failure as defense in
    # depth and is never invoked.
    for name in (
        "FORMAL",
        "PRECOMPUTE",
        "OBSERVABLE",
        "OUT",
        "TARGET_DIR",
        "TARGET_STORE",
        "QUALIFICATION",
        "LEDGER",
    ):
        setattr(helper, name, None)

    def blocked_old_main() -> None:
        raise RuntimeError("HMSO01R_B_OLD_HELPER_MAIN_EXECUTION_FORBIDDEN")

    helper.main = blocked_old_main
    if not callable(getattr(helper, "evaluate_case", None)):
        raise RuntimeError("HMSO01R_B_EVALUATE_CASE_HELPER_MISSING")
    reference.assert_static_operator_import_identity()
    return reference, helper


def validate_formal_atlas(payload: dict[str, Any]) -> list[dict[str, Any]]:
    cases = payload.get("cases")
    if not isinstance(cases, list):
        raise RuntimeError("HMSO01R_B_FROZEN_FORMAL_ATLAS_SCHEMA_FAILURE")
    if not (
        payload.get("status") == "FORMAL_FRESH_ATLAS_ADMITTED"
        and payload.get("all_formal_cases_four_scale_admissible") is True
        and int(payload.get("case_count", -1)) == 384
        and len(cases) == 384
        and payload.get("family_counts") == {"F1": 96, "F2": 96, "F3": 96, "F4": 96}
        and int(payload.get("failed_primary_count", -1)) == 0
        and int(payload.get("reserve_used_count", -1)) == 0
    ):
        raise RuntimeError("HMSO01R_B_FROZEN_FORMAL_POPULATION_FAILURE")
    seen_case_ids: set[str] = set()
    for position, case in enumerate(cases):
        if not (
            int(case["formal_case_index"]) == position
            and case["candidate_role"] == "PRIMARY"
            and case["admission_status"] == "FOUR_SCALE_CASE_LEVEL_ADMISSIBLE"
            and case["macro_family"] in {"F1", "F2", "F3", "F4"}
            and case["fold"] in {f"FOLD_{index}" for index in range(6)}
            and int(case["formal_particle_sample_count"]) == 128
            and int(case["particle_count"]) == 576
            and case["dtype"] == "float64"
        ):
            raise RuntimeError(f"HMSO01R_B_FROZEN_FORMAL_CASE_IDENTITY_FAILURE:{position}")
        if case["case_id"] in seen_case_ids:
            raise RuntimeError(f"HMSO01R_B_DUPLICATE_FORMAL_CASE_ID:{case['case_id']}")
        seen_case_ids.add(case["case_id"])
    return cases


def make_ledger(
    *,
    boundary: dict[str, Any],
    external_sources: dict[str, dict[str, str]],
    observable_before: str,
    observable_after: str,
    qualification_rows: list[dict[str, Any]],
    failed_rows: list[dict[str, Any]],
    target_store_sha256: str | None,
) -> dict[str, Any]:
    case_count = len(qualification_rows)
    builder_sha = sha256(Path(__file__).resolve())
    status = (
        "HMSO01R_B_TARGET_REFERENCE_QUALIFICATION_NOT_COMPLETE"
        if failed_rows
        else "HMSO01R_B_TARGET_REFERENCE_QUALIFIED"
    )
    target_store_write_count = 0 if target_store_sha256 is None else 1
    # These canonical names are the direct, stage-local governance counters.
    # The more granular aliases below are retained for numerical provenance,
    # but release validation must consume these exact contract spellings.
    authorized_activity_counts = {
        "bootstrap_draws_consumed": 0,
        "candidate_c_evaluation_count": 0,
        "conditional_variance_evaluation_count": 0,
        "coverage_evaluation_count": 0,
        "oracle_fit_count": 0,
        "paired_rescue_evaluation_count": 0,
        "reference_evaluation_count": case_count,
        "target_case_evaluation_count": case_count,
        "target_store_read_count": 0,
        "target_store_write_count": target_store_write_count,
    }
    prohibited_activity_counts = {
        "arc_access_count": 0,
        "attention_count": 0,
        "case_replacement_after_target_access": 0,
        "learned_operator_count": 0,
        "neural_model_count": 0,
        "optimizer_count": 0,
        "rollout_count": 0,
        "sealed_test_count": 0,
        "solver_in_loop_count": 0,
        "target_derived_feature_modification_count": 0,
        "target_derived_fold_modification_count": 0,
        "target_derived_gate_modification_count": 0,
        "target_derived_metric_modification_count": 0,
        "target_derived_normalization_modification_count": 0,
        "target_derived_oracle_modification_count": 0,
        "target_derived_scale_modification_count": 0,
        "time_integration_count": 0,
        "training_count": 0,
        "transformer_count": 0,
    }
    return {
        "authorized_activity_counts": authorized_activity_counts,
        "authorized_target_access_counts": {
            **authorized_activity_counts,
            "analytical_reference_case_evaluations_A": case_count,
            "analytical_reference_case_evaluations_B": case_count,
            "compensated_operator_evaluations": case_count,
            "ddo_algebraic_diagnostic_operator_evaluations": case_count,
            "evaluator_helper_evaluate_case_calls": case_count,
            "evaluator_helper_main_calls": 0,
            "float32_diagnostic_evaluations": case_count,
            "formal_atlas_semantic_reads": 1,
            "formal_case_target_generations": case_count,
            "formal_particle_sample_opaque_hash_reads": 1,
            "formal_particle_sample_payload_reads": 0,
            "independent_geometry_operator_evaluations": case_count,
            "lambda_1_base_operator_primary_evaluations": case_count,
            "observable_matrix_reads_by_target_builder": 0,
            "observable_store_filesystem_opaque_hash_reads": 2,
            "observable_store_git_blob_opaque_hash_reads": 1,
            "permuted_operator_evaluations": case_count,
            "pretarget_base_operator_identity_audit_count": 384,
            "pretarget_base_operator_identity_audit_matched_count": 384,
            "repeat_operator_evaluations": case_count,
            "target_store_opaque_hash_reads": 0 if target_store_sha256 is None else 1,
            "target_store_payload_reads": 0,
            "target_store_writes": target_store_write_count,
        },
        "builder_separation": {
            "evaluator_helper_main_executed": False,
            "formal_analysis_helper_main_executed_by_target_builder": False,
            "formal_analysis_helper_source_loaded_by_target_builder": False,
            "formal_particle_sample_payload_loaded": False,
            "historical_result_report_checkpoint_or_target_payload_loaded": False,
            "observable_npz_loaded": False,
            "old_output_path_globals_disabled_before_evaluation": True,
            "semantic_scientific_inputs": [
                "05_registries/hmso01r_a_formal_fresh_atlas_registry.json",
                "hash-bound analytical/reference code",
                "hash-bound lambda-one operator code",
            ],
        },
        "case_replacement_after_target_access": 0,
        "case_replacement_authorized": False,
        "external_ddo_source_head": DDO_SOURCE_HEAD,
        "external_ddo_source_identities": external_sources,
        "failed_case_count": len(failed_rows),
        "failed_case_ids": [row["case_id"] for row in failed_rows],
        "forbidden_access_counts": {
            "arc_access": 0,
            "historical_ddo_h3_outcome": 0,
            "historical_ddo_target_archive": 0,
            "historical_mso_result_report_checkpoint": 0,
            "sealed_test": 0,
        },
        "frozen_identity": {
            "builder_sha256": builder_sha,
            "evaluator_helper_sha256": EXPECTED_HELPER_SHA256,
            "formal_atlas_sha256": EXPECTED_FORMAL_ATLAS_SHA256,
            "formal_particle_sample_sha256": EXPECTED_FORMAL_SAMPLE_SHA256,
            "observable_store_sha256": EXPECTED_OBSERVABLE_SHA256,
            "pre_target_freeze_sha256": boundary["freeze_sha256"],
            "candidate_c_implementation_preflight_sha256": boundary[
                "preflight_attestation"
            ]["sha256"],
            "formal_evaluator_sha256": boundary["preflight_attestation"][
                "formal_evaluator_sha256"
            ],
            "formal_analysis_helper_source_sha256": EXPECTED_FORMAL_ANALYSIS_HELPER_SOURCE_SHA256,
            "reference_module_sha256": EXPECTED_REFERENCE_SHA256,
            "vendor_operator_sha256": VENDOR_OPERATOR_SHA256,
        },
        "git": {
            "branch": boundary["branch"],
            "pre_target_commit": boundary["head"],
            "pre_target_commit_contains_all_declared_frozen_blobs": True,
            "pre_target_freeze_git_blob_oid": boundary["freeze_git_blob_oid"],
            "pre_target_freeze_git_blob_sha256": boundary["freeze_git_blob_sha256"],
            "remote": None,
            "working_tree_clean_before_first_target_access": True,
        },
        "h_mso01r_status": (
            "NOT_EVALUATED_DUE_TO_TARGET_QUALIFICATION_FAILURE" if failed_rows else "TARGETS_QUALIFIED_ANALYSIS_NOT_YET_EXECUTED"
        ),
        "numerical_definition": {
            "formal_operator_lambda": 1.0,
            "formal_targets": [
                "density_rate",
                "pressure_gradient_acceleration",
                "viscosity_laplacian_acceleration",
            ],
            "high_resolution_sph_is_truth": False,
            "sign": "CONTINUUM_ANALYTICAL_REFERENCE_MINUS_LAMBDA_1_FROZEN_BASE_SPH",
            "target_definition": "R_h L(q*) - L_h(R_h q*)",
            "total_acceleration": "DERIVED_DIAGNOSTIC_ONLY",
        },
        "observable_store_sha256_after_target_generation": observable_after,
        "observable_store_sha256_before_target_generation": observable_before,
        "observable_store_unchanged": observable_before == observable_after,
        "pre_target_commit": boundary["head"],
        "pretarget_base_operator_identity_audit": {
            "classification": "TARGET_BLIND_BASE_OPERATOR_IDENTITY_AUDIT_NOT_TARGET_REFERENCE_EVALUATION",
            "count": 384,
            "matched": 384,
            "ordered_digest": PRETARGET_OPERATOR_ORDERED_DIGEST,
        },
        "prohibited_activity_counts": prohibited_activity_counts,
        "target_blind_candidate_c_preflight_attestation": boundary[
            "preflight_attestation"
        ],
        "qualified_case_count": case_count - len(failed_rows),
        "qualification_artifact": str(QUALIFICATION.relative_to(ROOT)),
        "qualification_artifact_sha256": sha256(QUALIFICATION),
        "schema_version": "1.0.0",
        "scientific_modification_counts_after_target_access": {
            "case_replacement": 0,
            "feature": 0,
            "fold": 0,
            "gate": 0,
            "metric": 0,
            "normalization": 0,
            "operator_lambda": 0,
            "oracle": 0,
            "scale": 0,
        },
        "stage": "H-MSO-01R-B",
        "status": status,
        "target_row_scope": "ALL_PARTICLES_OF_ALL_384_FROZEN_FORMAL_CASES",
        "target_store": str(TARGET_STORE.relative_to(ROOT)) if target_store_sha256 else None,
        "target_store_sha256": target_store_sha256,
        "target_store_written": target_store_sha256 is not None,
        "verified_pre_target_artifact_count": boundary["verified_artifact_count"],
    }


def main() -> None:
    # Boundary and source identities are completed before analytical/reference
    # modules are imported.  This call discovers HMSO01R_B_PRE_TARGET_COMMIT as
    # the clean current HEAD and validates all freeze-declared Git blobs there.
    boundary = validate_pre_target_boundary()
    external_sources = validate_external_ddo_sources()
    verified = boundary["verified"]
    observable_relative = OBSERVABLE.relative_to(ROOT).as_posix()
    sample_relative = FORMAL_SAMPLE.relative_to(ROOT).as_posix()
    observable_before = verified[observable_relative]["sha256"]
    sample_hash = verified[sample_relative]["sha256"]
    if observable_before != EXPECTED_OBSERVABLE_SHA256 or sample_hash != EXPECTED_FORMAL_SAMPLE_SHA256:
        raise RuntimeError("HMSO01R_B_FROZEN_R_A_BYTE_IDENTITY_FAILURE")

    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    torch.set_default_dtype(torch.float64)
    reference, helper = load_target_only_evaluator()

    # This is the only semantic scientific data read by the target builder.
    formal_payload = json.loads(FORMAL_ATLAS.read_text(encoding="utf-8"))
    cases = validate_formal_atlas(formal_payload)

    qualification_rows: list[dict[str, Any]] = []
    target_blocks: dict[str, list[np.ndarray]] = {name: [] for name in STORE_NAMES.values()}
    row_formal_case_index: list[int] = []
    row_particle_id: list[int] = []
    row_particle_count: list[int] = []
    row_case_id: list[str] = []
    row_position_hash: list[str] = []
    row_state_hash: list[str] = []
    row_lineage: list[str] = []
    row_family: list[str] = []
    row_fold: list[str] = []
    case_row_start: list[int] = []
    case_row_stop: list[int] = []
    case_qualification_sha256: list[str] = []
    uncertainty_case: dict[str, list[Any]] = {}
    running_row = 0

    for position, case in enumerate(cases):
        row, arrays, uncertainties = helper.evaluate_case(case)
        count = int(case["particle_count"])
        expected_shapes = {
            "target_density_rate": (count,),
            "target_pressure_gradient_acceleration": (count, 2),
            "target_viscosity_laplacian_acceleration": (count, 2),
            "target_total_acceleration_derived": (count, 2),
        }
        full_case_shape_identity = all(
            name in arrays
            and tuple(np.asarray(arrays[name]).shape) == shape
            and np.asarray(arrays[name]).dtype == np.float64
            and bool(np.isfinite(np.asarray(arrays[name])).all())
            for name, shape in expected_shapes.items()
        )
        lambda_one_identity = bool(row["lambda_1_operator_hash_matches"])
        particle_state_join_identity = bool(row["particle_state_hash_matches"])
        no_reserve_identity = case["candidate_role"] == "PRIMARY"
        qualified = bool(
            row["case_target_reference_qualified"]
            and full_case_shape_identity
            and lambda_one_identity
            and particle_state_join_identity
            and no_reserve_identity
        )
        row.update(
            {
                "stage": "H-MSO-01R-B",
                "pre_target_commit": boundary["head"],
                "formal_operator_lambda": 1.0,
                "formal_lambda_1_only": True,
                "full_case_target_shape_dtype_finite_identity": full_case_shape_identity,
                "target_particle_state_join_identity": particle_state_join_identity,
                "formal_particle_ids_contiguous_zero_based": True,
                "formal_particle_sample_registry_payload_read_by_target_builder": False,
                "formal_particle_sample_registry_sha256": sample_hash,
                "reserve_case_used": False,
                "case_target_reference_qualified": qualified,
            }
        )
        qualification_rows.append(row)
        case_qualification_sha256.append(
            hashlib.sha256(canonical_json(row).encode("utf-8")).hexdigest()
        )
        for name in expected_shapes:
            target_blocks[name].append(np.asarray(arrays[name], dtype=np.float64))

        case_row_start.append(running_row)
        running_row += count
        case_row_stop.append(running_row)
        row_formal_case_index.extend([position] * count)
        row_particle_id.extend(range(count))
        row_particle_count.extend([count] * count)
        row_case_id.extend([case["case_id"]] * count)
        row_position_hash.extend([case["position_hash"]] * count)
        row_state_hash.extend([case["particle_state_hash"]] * count)
        row_lineage.extend([case["field_lineage_id"]] * count)
        row_family.extend([case["macro_family"]] * count)
        row_fold.extend([case["fold"]] * count)

        for component, values in uncertainties.items():
            canonical_component = CANONICAL_COMPONENT_NAMES[component]
            for key, value in values.items():
                uncertainty_case.setdefault(f"case_{canonical_component}__{key}", []).append(value)
        if (position + 1) % 24 == 0:
            print(f"HMSO01R_B_TARGET_REFERENCE_QUALIFICATION {position + 1}/384", flush=True)

    if len(qualification_rows) != 384:
        raise RuntimeError("HMSO01R_B_TARGET_REFERENCE_QUALIFICATION_NOT_COMPLETE")
    observable_after = sha256(OBSERVABLE)
    if observable_after != observable_before:
        raise RuntimeError("HMSO01R_B_FROZEN_OBSERVABLE_STORE_MUTATED")

    write_csv(QUALIFICATION, qualification_rows)
    failed = [row for row in qualification_rows if not row["case_target_reference_qualified"]]
    if failed:
        ledger = make_ledger(
            boundary=boundary,
            external_sources=external_sources,
            observable_before=observable_before,
            observable_after=observable_after,
            qualification_rows=qualification_rows,
            failed_rows=failed,
            target_store_sha256=None,
        )
        write_json(LEDGER, ledger)
        raise RuntimeError("HMSO01R_B_TARGET_REFERENCE_QUALIFICATION_NOT_COMPLETE")

    arrays: dict[str, np.ndarray] = {
        name: np.concatenate(blocks, axis=0).astype(np.float64, copy=False)
        for name, blocks in target_blocks.items()
    }
    arrays.update(
        {
            "base_operator_lambda": np.asarray(1.0, dtype=np.float64),
            "case_base_operator_lambda": np.ones(384, dtype=np.float64),
            "case_id": np.asarray(row_case_id),
            "case_id_table": np.asarray([case["case_id"] for case in cases]),
            "case_qualification_row_sha256": np.asarray(case_qualification_sha256),
            "case_target_reference_qualified": np.ones(384, dtype=np.bool_),
            "evaluator_helper_sha256": np.asarray(EXPECTED_HELPER_SHA256),
            "family": np.asarray(row_family),
            "family_table": np.asarray([case["macro_family"] for case in cases]),
            "field_lineage_id": np.asarray(row_lineage),
            "field_lineage_id_table": np.asarray([case["field_lineage_id"] for case in cases]),
            "fold": np.asarray(row_fold),
            "fold_table": np.asarray([case["fold"] for case in cases]),
            "formal_atlas_sha256": np.asarray(EXPECTED_FORMAL_ATLAS_SHA256),
            "formal_case_index": np.asarray(row_formal_case_index, dtype=np.int32),
            "formal_case_index_table": np.arange(384, dtype=np.int32),
            "formal_particle_sample_registry_sha256": np.asarray(EXPECTED_FORMAL_SAMPLE_SHA256),
            "formal_particle_sample_scope": np.asarray(
                "HASH_ONLY_IN_TARGET_BUILDER; FORMAL_ANALYSIS_MUST_JOIN_FROZEN_SAMPLE"
            ),
            "lineage": np.asarray(row_lineage),
            "lineage_id": np.asarray(row_lineage),
            "lineage_id_table": np.asarray([case["field_lineage_id"] for case in cases]),
            "observable_store_sha256": np.asarray(EXPECTED_OBSERVABLE_SHA256),
            "operator_base_hash_table": np.asarray([case["operator_base_hash"] for case in cases]),
            "particle_count": np.asarray(row_particle_count, dtype=np.int32),
            "particle_count_table": np.asarray([case["particle_count"] for case in cases], dtype=np.int32),
            "particle_id": np.asarray(row_particle_id, dtype=np.int32),
            "particle_row_start_table": np.asarray(case_row_start, dtype=np.int64),
            "particle_row_stop_table": np.asarray(case_row_stop, dtype=np.int64),
            "particle_state_hash": np.asarray(row_state_hash),
            "particle_state_hash_table": np.asarray([case["particle_state_hash"] for case in cases]),
            "position_hash": np.asarray(row_position_hash),
            "position_hash_table": np.asarray([case["position_hash"] for case in cases]),
            "pre_target_commit": np.asarray(boundary["head"]),
            "primary_component_names": np.asarray(
                [
                    "density_rate",
                    "pressure_gradient_acceleration",
                    "viscosity_laplacian_acceleration",
                ]
            ),
            "reference_module_sha256": np.asarray(EXPECTED_REFERENCE_SHA256),
            "support_h_table": np.asarray([case["support_h"] for case in cases], dtype=np.float64),
            "target_builder_sha256": np.asarray(sha256(Path(__file__).resolve())),
            "target_definition": np.asarray("R_h L(q*) - L_h(R_h q*)"),
            "target_row_scope": np.asarray("ALL_PARTICLES_OF_ALL_384_FROZEN_FORMAL_CASES"),
            "target_sign": np.asarray("CONTINUUM_ANALYTICAL_REFERENCE_MINUS_LAMBDA_1_FROZEN_BASE_SPH"),
        }
    )
    for name, values in uncertainty_case.items():
        dtype: Any = np.bool_ if name.endswith("__sign_gate_passed") else np.float64
        arrays[name] = np.asarray(values, dtype=dtype)
    source_hashes = {
        **{f"SPH-DDO-PoC/{path}": value for path, value in DDO_SOURCE_SHA256.items()},
        **VENDOR_OPERATOR_SHA256,
        "01_provenance/vendor/ddo_analytical_reference/mso02b_target_reference.py": EXPECTED_REFERENCE_SHA256,
        "05_registries/hmso01r_a_formal_fresh_atlas_registry.json": EXPECTED_FORMAL_ATLAS_SHA256,
        "05_registries/hmso01r_a_formal_particle_sample_registry.json": EXPECTED_FORMAL_SAMPLE_SHA256,
        "06_experiments/hmso01r_a/observable/hmso01r_a_observable_store.npz": EXPECTED_OBSERVABLE_SHA256,
        "06_experiments/mso02b/build_mso02b_targets.py": EXPECTED_HELPER_SHA256,
        "06_experiments/mso02b/run_mso02b_formal.py": EXPECTED_FORMAL_ANALYSIS_HELPER_SOURCE_SHA256,
        "06_experiments/hmso01r_b/build_hmso01r_b_targets.py": sha256(Path(__file__).resolve()),
    }
    arrays["source_identity_path_table"] = np.asarray(sorted(source_hashes))
    arrays["source_identity_sha256_table"] = np.asarray(
        [source_hashes[path] for path in sorted(source_hashes)]
    )

    write_deterministic_npz(TARGET_STORE, arrays)
    target_store_sha = sha256(TARGET_STORE)
    ledger = make_ledger(
        boundary=boundary,
        external_sources=external_sources,
        observable_before=observable_before,
        observable_after=observable_after,
        qualification_rows=qualification_rows,
        failed_rows=[],
        target_store_sha256=target_store_sha,
    )
    write_json(LEDGER, ledger)
    print(
        json.dumps(
            {
                "observable_store_unchanged": True,
                "pre_target_commit": boundary["head"],
                "qualified_case_count": 384,
                "status": ledger["status"],
                "target_store_sha256": target_store_sha,
            },
            sort_keys=True,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
