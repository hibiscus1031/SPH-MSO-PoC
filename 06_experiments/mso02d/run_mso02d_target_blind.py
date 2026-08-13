#!/usr/bin/env python3
"""MSO-02D D1 observable-only geometry adjudication.

This executable is deliberately limited to the frozen H-MSO-01R-A observable
population and the D0 target-blind registries.  It never discovers input files:
every readable payload is on the explicit allowlist below.  In particular, D1
has no path, loader, or CLI option for outcome-bearing artifacts.

The command is intentionally split only at the operational boundary::

    python 06_experiments/mso02d/run_mso02d_target_blind.py run
    python 06_experiments/mso02d/run_mso02d_target_blind.py validate

``run`` writes per-candidate/per-fold checkpoints transactionally, then writes
the T1/T2 tables, transform parameters, frozen K10 identities/distances, and the
D1 freeze.  ``validate`` rechecks upstream identities and every frozen D1 hash.
Neither command performs target access or scientific route adjudication.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
import platform
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

# Keep fitted observable transforms reproducible and resource-bounded.
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("VECLIB_MAXIMUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")

import numpy as np
import scipy
from scipy.spatial import cKDTree
from scipy.stats import skew
import sklearn
from sklearn.covariance import LedoitWolf


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "06_experiments" / "mso02d"
CHECKPOINTS = OUT / "checkpoints"
REG = ROOT / "05_registries"
UP = ROOT / "06_experiments" / "hmso01r_a"

EVIDENCE_CLASS = "EXPLORATORY_CONSUMED_DIAGNOSTIC_ONLY"
PROTOCOL_COMMIT = "78ba0d5518909c96e3bf34383e0d95f30ca9ba17"
HMSO01R_A_FINAL_COMMIT = "9048eff137001e5f644575bd02c3856b4f4ac532"
D0_SUBJECT = "MSO-02D D0: freeze target-blind alignment and directional proxy definitions"
D1_SUBJECT = "MSO-02D D1: freeze target-blind alignment selection before target diagnostics"
K = 10
FOLD_COUNT = 6
FAMILIES = ("F1", "F2", "F3", "F4")
EXPECTED_ROWS = 49_152
EXPECTED_DIMS = {"SS": 39, "MS": 110}
CANDIDATES = ("U0", "U1", "U2", "U3")
NONIDENTITY_CANDIDATES = ("U1", "U2", "U3")
TOL = 1.0e-12
EIGEN_TOL = 1.0e-12
CHECKPOINT_VERSION = "MSO02D_D1_GEOMETRY_CHECKPOINT_V1"

FEATURE_REGISTRY = REG / "mso02d_feature_group_registry.json"
CANDIDATE_REGISTRY = REG / "mso02d_target_blind_geometry_candidate_registry.json"
DIRECTIONAL_PROXY_REGISTRY = REG / "mso02d_directional_scale_response_proxy_registry.json"
D0_CONTRACT = ROOT / "00_project_contract" / "mso02d_componentwise_failure_attribution_contract.md"
TARGET_DIAGNOSTICS_EXECUTABLE = OUT / "run_mso02d_target_diagnostics.py"
ATLAS = REG / "hmso01r_a_formal_fresh_atlas_registry.json"
PARTICLES = REG / "hmso01r_a_formal_particle_sample_registry.json"
FOLDS = REG / "hmso01r_a_lineage_fold_registry.json"
PAIRED = REG / "hmso01r_a_paired_ss_ms_registry.json"
RANDOM_REGISTRY = REG / "hmso01r_a_random_baseline_identity_registry.json"
OBSERVABLE = UP / "observable" / "hmso01r_a_observable_store.npz"
SS_SCHEMA = UP / "ss_observable_schema_identity.json"
MS_SCHEMA = UP / "ms_observable_schema_identity.json"
NORMALIZATION = UP / "fold_normalization_registry.json"
GEOMETRY = UP / "descriptor_geometry_freeze.json"
NEIGHBOURS = UP / "descriptor_neighbor_identities.npz"
RANDOM_IDENTITIES = UP / "random_baseline_identities.npz"
A_MANIFEST = ROOT / "08_manifests" / "hmso01r_a_manifest.json"
A_STATUS = ROOT / "08_manifests" / "hmso01r_a_status_ledger.json"

T1_SUBSPACE = OUT / "target_blind_subspace_diagnostics.csv"
T1_STABILITY = OUT / "subspace_stability_audit.csv"
T1_GROUP_ENERGY = OUT / "feature_group_energy_audit.csv"
T2_SELECTION = OUT / "target_blind_geometry_selection_matrix.csv"
FORMAL_GEOMETRY = OUT / "ss_ms_geometry_diagnostics.csv"
DISTANCE_AUDIT = OUT / "distance_concentration_audit.csv"
HUBNESS_AUDIT = OUT / "hubness_audit.csv"
TURNOVER_AUDIT = OUT / "neighbour_turnover_audit.csv"
TRANSFORMS = OUT / "target_blind_geometry_transform_parameters.npz"
SELECTED_NEIGHBOURS = OUT / "target_blind_geometry_selected_neighbours.npz"
EXECUTION_AUDIT = OUT / "d1_target_blind_execution_audit.json"
FREEZE = OUT / "target_blind_geometry_freeze.json"

# No input outside this set may be opened by this executable.
UPSTREAM_ALLOWLIST = (
    A_MANIFEST,
    A_STATUS,
    ATLAS,
    PARTICLES,
    FOLDS,
    PAIRED,
    RANDOM_REGISTRY,
    OBSERVABLE,
    SS_SCHEMA,
    MS_SCHEMA,
    NORMALIZATION,
    GEOMETRY,
    NEIGHBOURS,
    RANDOM_IDENTITIES,
    FEATURE_REGISTRY,
    CANDIDATE_REGISTRY,
    DIRECTIONAL_PROXY_REGISTRY,
    D0_CONTRACT,
    TARGET_DIAGNOSTICS_EXECUTABLE,
)

UPSTREAM_MANIFEST_PATHS = tuple(
    path.relative_to(ROOT).as_posix()
    for path in (
        ATLAS,
        PARTICLES,
        FOLDS,
        PAIRED,
        RANDOM_REGISTRY,
        OBSERVABLE,
        SS_SCHEMA,
        MS_SCHEMA,
        NORMALIZATION,
        GEOMETRY,
        NEIGHBOURS,
        RANDOM_IDENTITIES,
        A_STATUS,
    )
)


class IntegrityError(RuntimeError):
    """Fail-closed D1 identity or semantics conflict."""


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    if path not in UPSTREAM_ALLOWLIST and path != FREEZE and not path.is_relative_to(OUT):
        raise IntegrityError(f"MSO02D_D1_INPUT_FIREWALL_VIOLATION: {path}")
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise IntegrityError(f"MSO02D_D1_JSON_OBJECT_REQUIRED: {rel(path)}")
    return value


def atomic_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    payload = (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    atomic_bytes(path, payload)


def atomic_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise IntegrityError(f"MSO02D_D1_EMPTY_TABLE: {rel(path)}")
    keys: list[str] = []
    preferred = ["evidence_class", "record_type", "arm", "candidate_id", "scope_type", "scope_id"]
    union = {key for row in rows for key in row}
    keys.extend(key for key in preferred if key in union)
    keys.extend(sorted(union.difference(keys)))
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=keys, extrasaction="raise", lineterminator="\n")
    writer.writeheader()
    for source in rows:
        row = dict(source)
        if row.get("evidence_class") != EVIDENCE_CLASS:
            raise IntegrityError(f"MSO02D_D1_EVIDENCE_CLASS_MISSING: {rel(path)}")
        writer.writerow(row)
    atomic_bytes(path, stream.getvalue().encode("utf-8"))


def atomic_npz(path: Path, **arrays: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".npz", dir=path.parent)
    os.close(descriptor)
    try:
        np.savez_compressed(temporary, **arrays)
        with open(temporary, "rb") as handle:
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def git(*args: str, binary: bool = False) -> str | bytes:
    process = subprocess.run(
        ["git", *args], cwd=ROOT, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    if process.returncode != 0:
        raise IntegrityError(
            f"MSO02D_D1_GIT_FAILURE: git {' '.join(args)}: {process.stderr.decode(errors='replace').strip()}"
        )
    return process.stdout if binary else process.stdout.decode("utf-8").strip()


def git_blob_hash(commit: str, path: Path) -> str:
    payload = git("show", f"{commit}:{rel(path)}", binary=True)
    assert isinstance(payload, bytes)
    return hashlib.sha256(payload).hexdigest()


def git_boundary(require_d0_subject: bool) -> dict[str, Any]:
    head = str(git("rev-parse", "HEAD"))
    branch = str(git("branch", "--show-current"))
    remotes = [item for item in str(git("remote")).splitlines() if item]
    if branch != "main" or remotes:
        raise IntegrityError("MSO02D_D1_GIT_BOUNDARY_CONFLICT")
    if subprocess.run(
        ["git", "merge-base", "--is-ancestor", PROTOCOL_COMMIT, head], cwd=ROOT, check=False
    ).returncode != 0:
        raise IntegrityError("MSO02D_D1_PROTOCOL_COMMIT_NOT_ANCESTOR")
    subject = str(git("show", "-s", "--format=%s", head))
    if require_d0_subject and subject != D0_SUBJECT:
        raise IntegrityError(f"MSO02D_D1_D0_COMMIT_REQUIRED: current subject={subject!r}")
    if require_d0_subject:
        for frozen_path in (
            D0_CONTRACT,
            FEATURE_REGISTRY,
            CANDIDATE_REGISTRY,
            DIRECTIONAL_PROXY_REGISTRY,
            Path(__file__),
            TARGET_DIAGNOSTICS_EXECUTABLE,
        ):
            if not frozen_path.is_file() or git_blob_hash(head, frozen_path) != sha256(frozen_path):
                raise IntegrityError(f"MSO02D_D1_D0_BLOB_IDENTITY_CONFLICT: {rel(frozen_path)}")
    dirty = str(git("status", "--porcelain=v1", "--untracked-files=all")).splitlines()
    unexpected: list[str] = []
    output_prefix = rel(OUT) + "/"
    for line in dirty:
        candidate = line[3:] if len(line) >= 4 else line
        if " -> " in candidate:
            candidate = candidate.split(" -> ", 1)[1]
        if not candidate.startswith(output_prefix):
            unexpected.append(line)
    if unexpected:
        raise IntegrityError(f"MSO02D_D1_UNRELATED_DIRTY_WORKTREE: {unexpected}")
    return {
        "head": head,
        "subject": subject,
        "branch": branch,
        "remote": None,
        "unexpected_dirty_paths": unexpected,
    }


def verify_upstream() -> dict[str, str]:
    for path in UPSTREAM_ALLOWLIST:
        if not path.is_file():
            raise IntegrityError(f"MSO02D_UPSTREAM_EVIDENCE_INTEGRITY_CONFLICT: missing {rel(path)}")

    # The A manifest and status are themselves bound to the immutable A release
    # commit.  All remaining consumed A files are checked against that manifest.
    for path in (A_MANIFEST, A_STATUS):
        if sha256(path) != git_blob_hash(HMSO01R_A_FINAL_COMMIT, path):
            raise IntegrityError(f"MSO02D_UPSTREAM_EVIDENCE_INTEGRITY_CONFLICT: git identity {rel(path)}")

    manifest = read_json(A_MANIFEST)
    registered = {entry["path"]: entry["sha256"] for entry in manifest.get("artifact_registry", [])}
    for relative in UPSTREAM_MANIFEST_PATHS:
        path = ROOT / relative
        if registered.get(relative) != sha256(path):
            raise IntegrityError(f"MSO02D_UPSTREAM_EVIDENCE_INTEGRITY_CONFLICT: manifest identity {relative}")

    status = read_json(A_STATUS)
    if status.get("terminal_status") != "HMSO01R_A_FRESH_CONFIRMATORY_ATLAS_AND_ZERO_SAFE_ANALYSIS_FROZEN":
        raise IntegrityError("MSO02D_UPSTREAM_EVIDENCE_INTEGRITY_CONFLICT: A status")
    if status.get("ss_feature_dimension") != 39 or status.get("ms_feature_dimension") != 110:
        raise IntegrityError("MSO02D_UPSTREAM_EVIDENCE_INTEGRITY_CONFLICT: feature dimensions")

    result = {rel(path): sha256(path) for path in UPSTREAM_ALLOWLIST}
    result[rel(Path(__file__))] = sha256(Path(__file__))
    return result


def validate_d0_registries(
    feature_registry: Mapping[str, Any], candidate_registry: Mapping[str, Any], ms_names: Sequence[str]
) -> list[dict[str, Any]]:
    groups = feature_registry.get("groups")
    if not isinstance(groups, list) or not groups:
        raise IntegrityError("MSO02D_D1_FEATURE_GROUP_REGISTRY_INVALID")
    parsed: list[dict[str, Any]] = []
    claimed: list[int] = []
    for group in groups:
        group_id = str(group.get("group_id", ""))
        indices = [int(value) for value in group.get("feature_indices_zero_based", [])]
        names = [str(value) for value in group.get("feature_names", [])]
        # G5/G6 are prospectively registered empty groups in the frozen 110D
        # schema.  Retaining them with explicit zero-energy semantics is not a
        # feature/group deletion; they simply contribute no coordinates.
        if not group_id or len(indices) != len(names):
            raise IntegrityError(f"MSO02D_D1_FEATURE_GROUP_INVALID: {group_id!r}")
        if names != [ms_names[index] for index in indices]:
            raise IntegrityError(f"MSO02D_D1_FEATURE_GROUP_SCHEMA_MISMATCH: {group_id}")
        if len(set(indices)) != len(indices):
            raise IntegrityError(f"MSO02D_D1_DUPLICATE_FEATURE_WITHIN_GROUP: {group_id}")
        claimed.extend(indices)
        parsed.append(
            {
                "group_id": group_id,
                "group_name": str(group.get("group_name", group_id)),
                "indices": np.asarray(indices, dtype=np.int64),
                "feature_names": names,
                "ablation_eligible": bool(group.get("ablation_eligible", False)),
            }
        )
    if sorted(claimed) != list(range(len(ms_names))):
        raise IntegrityError("MSO02D_D1_FEATURE_GROUPS_MUST_PARTITION_ALL_110_FEATURES")

    candidates = candidate_registry.get("candidates")
    if not isinstance(candidates, list):
        raise IntegrityError("MSO02D_D1_CANDIDATE_REGISTRY_INVALID")
    by_id = {str(item.get("candidate_id")): item for item in candidates}
    if set(by_id) != set(CANDIDATES):
        raise IntegrityError("MSO02D_D1_CANDIDATE_SET_CONFLICT")
    for candidate_id in CANDIDATES:
        item = by_id[candidate_id]
        if not bool(item.get("target_blind")) or str(item.get("input_arm")) != "MS":
            raise IntegrityError(f"MSO02D_D1_CANDIDATE_SEMANTICS_CONFLICT: {candidate_id}")
    frozen_versions = candidate_registry.get("runtime_versions_frozen_for_U3", {})
    actual_versions = {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "scikit_learn": sklearn.__version__,
    }
    if frozen_versions != actual_versions:
        raise IntegrityError(
            f"MSO02D_D1_U3_RUNTIME_IDENTITY_CONFLICT: frozen={frozen_versions} actual={actual_versions}"
        )
    rule = candidate_registry.get("selection_rule")
    if not isinstance(rule, dict):
        raise IntegrityError("MSO02D_D1_SELECTION_RULE_MISSING")
    if rule.get("no_candidate_status") != "ROUTE_A_TARGET_BLIND_GEOMETRY_CANDIDATE_NOT_ESTABLISHED":
        raise IntegrityError("MSO02D_D1_NO_CANDIDATE_STATUS_CONFLICT")
    per_stratum = rule.get("per_stratum_pass", {})
    replication = rule.get("minimum_replication", {})
    stability = rule.get("transform_stability", {})
    additional = rule.get("selection_additional_requirement", {})
    exact_rule_checks = (
        per_stratum.get("k10_to_median_ratio") == "candidate <= U0*1.01",
        per_stratum.get("nearest_to_median_ratio") == "candidate <= U0*1.01",
        per_stratum.get("neighbor_occurrence_gini") == "candidate <= U0+0.01",
        per_stratum.get("semantic_group_domination") == "candidate <= U0+0.01",
        all(
            replication.get(key, {}).get("folds") == 5
            and replication.get(key, {}).get("families") == 3
            for key in ("concentration", "hubness", "semantic_group_domination")
        ),
        stability.get("minimum_median_pairwise_fold_similarity") == 0.75,
        stability.get("minimum_median_pairwise_family_similarity") == 0.75,
        additional.get("minimum_number_of_improved_primary_median_fold_criteria") == 2,
        additional.get("strict_improvement_tolerance") == TOL,
        rule.get("composite_rank", {}).get("exact_tie_order") == ["U1", "U2", "U3"],
    )
    if not all(exact_rule_checks):
        raise IntegrityError("MSO02D_D1_FROZEN_SELECTION_RULE_CONFLICT")
    return parsed


@dataclass(frozen=True)
class DataBundle:
    ss: np.ndarray
    ms: np.ndarray
    row_case: np.ndarray
    row_particle: np.ndarray
    case_id: np.ndarray
    lineage: np.ndarray
    family: np.ndarray
    fold: np.ndarray
    seed: np.ndarray
    sample_key: np.ndarray
    schemas: dict[str, list[str]]
    normalization: dict[str, Any]
    groups: list[dict[str, Any]]
    frozen_neighbours: dict[str, np.ndarray]
    frozen_distances: dict[str, np.ndarray]
    random_rows: np.ndarray


def load_and_validate_data() -> DataBundle:
    ss_schema = read_json(SS_SCHEMA)
    ms_schema = read_json(MS_SCHEMA)
    schemas = {
        "SS": [str(item["name"]) for item in ss_schema.get("columns", [])],
        "MS": [str(item["name"]) for item in ms_schema.get("columns", [])],
    }
    for arm, schema in (("SS", ss_schema), ("MS", ms_schema)):
        if len(schemas[arm]) != EXPECTED_DIMS[arm] or schema.get("feature_dimension") != EXPECTED_DIMS[arm]:
            raise IntegrityError(f"MSO02D_D1_SCHEMA_DIMENSION_CONFLICT: {arm}")
        if schema.get("target_or_reference_columns") != []:
            raise IntegrityError(f"MSO02D_D1_SCHEMA_FIREWALL_CONFLICT: {arm}")
        for column in schema.get("columns", []):
            if not column.get("formal_input") or not column.get("deployment_available"):
                raise IntegrityError(f"MSO02D_D1_NONDEPLOYMENT_COLUMN: {column.get('name')}")

    feature_registry = read_json(FEATURE_REGISTRY)
    candidate_registry = read_json(CANDIDATE_REGISTRY)
    groups = validate_d0_registries(feature_registry, candidate_registry, schemas["MS"])

    with np.load(OBSERVABLE, allow_pickle=False) as store:
        if set(store.files) != {"ss_features", "ms_features", "formal_case_index", "particle_id"}:
            raise IntegrityError("MSO02D_D1_OBSERVABLE_STORE_SCHEMA_CONFLICT")
        ss = np.asarray(store["ss_features"], dtype=np.float64)
        ms = np.asarray(store["ms_features"], dtype=np.float64)
        row_case = np.asarray(store["formal_case_index"], dtype=np.int32)
        row_particle = np.asarray(store["particle_id"], dtype=np.int32)
    if ss.shape != (EXPECTED_ROWS, 39) or ms.shape != (EXPECTED_ROWS, 110):
        raise IntegrityError("MSO02D_D1_OBSERVABLE_SHAPE_CONFLICT")
    if row_case.shape != (EXPECTED_ROWS,) or row_particle.shape != (EXPECTED_ROWS,):
        raise IntegrityError("MSO02D_D1_OBSERVABLE_IDENTITY_SHAPE_CONFLICT")
    if not np.isfinite(ss).all() or not np.isfinite(ms).all():
        raise IntegrityError("MSO02D_D1_NONFINITE_OBSERVABLE")

    atlas = read_json(ATLAS)
    particle_registry = read_json(PARTICLES)
    fold_registry = read_json(FOLDS)
    paired = read_json(PAIRED)
    if atlas.get("case_count") != 384 or particle_registry.get("particle_row_count") != EXPECTED_ROWS:
        raise IntegrityError("MSO02D_D1_FORMAL_REGISTRY_SIZE_CONFLICT")
    if not any(
        paired.get(key) is True
        for key in (
            "all_case_particle_identity_checks_passed",
            "ss_ms_exact_rowwise_identity",
            "ss_ms_identical",
            "paired_case_particle_identity",
        )
    ):
        raise IntegrityError("MSO02D_D1_PAIRED_IDENTITY_CONFLICT")

    cases = sorted(atlas.get("cases", []), key=lambda item: int(item["formal_case_index"]))
    fold_cases = sorted(fold_registry.get("cases", []), key=lambda item: int(item["formal_case_index"]))
    particle_cases = sorted(particle_registry.get("cases", []), key=lambda item: int(item["formal_case_index"]))
    if len(cases) != 384 or len(fold_cases) != 384 or len(particle_cases) != 384:
        raise IntegrityError("MSO02D_D1_FORMAL_CASE_REGISTRY_CONFLICT")
    for index, (case, folded, sampled) in enumerate(zip(cases, fold_cases, particle_cases)):
        if int(case["formal_case_index"]) != index:
            raise IntegrityError("MSO02D_D1_NONCONTIGUOUS_CASE_INDEX")
        for key in ("case_id", "field_lineage_id", "fold"):
            if case[key] != folded[key]:
                raise IntegrityError(f"MSO02D_D1_FOLD_REGISTRY_CONFLICT: case={index} key={key}")
        rows = np.flatnonzero(row_case == index)
        expected_particles = np.asarray(sampled["particle_ids_in_hash_order"], dtype=np.int32)
        if rows.size != 128 or not np.array_equal(row_particle[rows], expected_particles):
            raise IntegrityError(f"MSO02D_D1_PARTICLE_REGISTRY_CONFLICT: case={index}")

    case_id = np.asarray([str(cases[index]["case_id"]) for index in row_case])
    lineage = np.asarray([str(cases[index]["field_lineage_id"]) for index in row_case])
    family = np.asarray([str(cases[index]["macro_family"]) for index in row_case])
    fold = np.asarray([int(str(cases[index]["fold"]).split("_")[-1]) for index in row_case], dtype=np.int8)
    seed = np.asarray([int(cases[index]["jitter_seed"]) for index in row_case], dtype=np.int64)
    sample_key = np.asarray([f"{case}|{int(particle)}" for case, particle in zip(case_id, row_particle)])
    if set(np.unique(fold).tolist()) != set(range(FOLD_COUNT)) or set(np.unique(family).tolist()) != set(FAMILIES):
        raise IntegrityError("MSO02D_D1_STRATUM_IDENTITY_CONFLICT")

    normalization = read_json(NORMALIZATION)
    if normalization.get("target_read_count") != 0 or normalization.get("fold_count") != FOLD_COUNT:
        raise IntegrityError("MSO02D_D1_NORMALIZATION_FIREWALL_CONFLICT")
    for arm in ("SS", "MS"):
        folds = normalization.get("arms", {}).get(arm, {}).get("folds", [])
        if len(folds) != FOLD_COUNT:
            raise IntegrityError(f"MSO02D_D1_NORMALIZATION_FOLD_CONFLICT: {arm}")
        for fold_index, record in enumerate(folds):
            median = np.asarray(record.get("median", []), dtype=np.float64)
            divisor = np.asarray(record.get("divisor", []), dtype=np.float64)
            iqr = np.asarray(record.get("iqr", []), dtype=np.float64)
            if median.shape != (EXPECTED_DIMS[arm],) or divisor.shape != median.shape or iqr.shape != median.shape:
                raise IntegrityError(f"MSO02D_D1_NORMALIZATION_SHAPE_CONFLICT: {arm} fold={fold_index}")
            if not np.isfinite(median).all() or not np.isfinite(divisor).all() or np.any(divisor <= 0):
                raise IntegrityError(f"MSO02D_D1_NORMALIZATION_VALUE_CONFLICT: {arm} fold={fold_index}")
            if not np.array_equal(divisor, np.where(iqr == 0.0, 1.0, iqr)):
                raise IntegrityError(f"MSO02D_D1_NORMALIZATION_FALLBACK_CONFLICT: {arm} fold={fold_index}")

    geometry = read_json(GEOMETRY)
    if geometry.get("primary_k") != K or geometry.get("target_read_count") != 0:
        raise IntegrityError("MSO02D_D1_GEOMETRY_FIREWALL_CONFLICT")
    if geometry.get("tie_order") != ["distance", "case_id", "particle_id"]:
        raise IntegrityError("MSO02D_D1_TIE_SEMANTICS_CONFLICT")
    with np.load(NEIGHBOURS, allow_pickle=False) as frozen:
        if set(frozen.files) != {
            "query_row_index", "ss_neighbor_row_index", "ms_neighbor_row_index",
            "ss_neighbor_distance", "ms_neighbor_distance",
        }:
            raise IntegrityError("MSO02D_D1_FROZEN_NEIGHBOUR_SCHEMA_CONFLICT")
        if not np.array_equal(frozen["query_row_index"], np.arange(EXPECTED_ROWS, dtype=np.int32)):
            raise IntegrityError("MSO02D_D1_FROZEN_QUERY_IDENTITY_CONFLICT")
        frozen_neighbours = {
            "SS": np.asarray(frozen["ss_neighbor_row_index"], dtype=np.int32),
            "MS": np.asarray(frozen["ms_neighbor_row_index"], dtype=np.int32),
        }
        frozen_distances = {
            "SS": np.asarray(frozen["ss_neighbor_distance"], dtype=np.float64),
            "MS": np.asarray(frozen["ms_neighbor_distance"], dtype=np.float64),
        }
    for arm in ("SS", "MS"):
        if frozen_neighbours[arm].shape != (EXPECTED_ROWS, K) or frozen_distances[arm].shape != (EXPECTED_ROWS, K):
            raise IntegrityError(f"MSO02D_D1_FROZEN_NEIGHBOUR_SHAPE_CONFLICT: {arm}")
        if np.any(frozen_neighbours[arm] < 0) or not np.isfinite(frozen_distances[arm]).all():
            raise IntegrityError(f"MSO02D_D1_FROZEN_NEIGHBOUR_VALUE_CONFLICT: {arm}")
        if np.any(np.diff(frozen_distances[arm], axis=1) < 0.0):
            raise IntegrityError(f"MSO02D_D1_FROZEN_NEIGHBOUR_ORDER_CONFLICT: {arm}")

    random_registry = read_json(RANDOM_REGISTRY)
    if random_registry.get("primary_k") != K or random_registry.get("target_dependence") is not False:
        raise IntegrityError("MSO02D_D1_RANDOM_REGISTRY_CONFLICT")
    with np.load(RANDOM_IDENTITIES, allow_pickle=False) as frozen:
        if set(frozen.files) != {"query_row_index", "comparator_row_index"}:
            raise IntegrityError("MSO02D_D1_RANDOM_IDENTITY_SCHEMA_CONFLICT")
        if not np.array_equal(frozen["query_row_index"], np.arange(EXPECTED_ROWS, dtype=np.int32)):
            raise IntegrityError("MSO02D_D1_RANDOM_QUERY_IDENTITY_CONFLICT")
        random_rows = np.asarray(frozen["comparator_row_index"], dtype=np.int32)
    if random_rows.shape != (EXPECTED_ROWS, K) or np.any(random_rows < 0):
        raise IntegrityError("MSO02D_D1_RANDOM_IDENTITY_SHAPE_CONFLICT")
    if any(np.unique(row).size != K for row in random_rows):
        raise IntegrityError("MSO02D_D1_RANDOM_IDENTITY_DUPLICATE_CONFLICT")

    bundle = DataBundle(
        ss=ss, ms=ms, row_case=row_case, row_particle=row_particle, case_id=case_id,
        lineage=lineage, family=family, fold=fold, seed=seed, sample_key=sample_key,
        schemas=schemas, normalization=normalization, groups=groups,
        frozen_neighbours=frozen_neighbours, frozen_distances=frozen_distances,
        random_rows=random_rows,
    )
    validate_frozen_identities(bundle)
    return bundle


def ordered_rows(rows: np.ndarray, data: DataBundle) -> np.ndarray:
    order = np.argsort(data.sample_key[rows], kind="stable")
    return np.asarray(rows[order], dtype=np.int64)


def legal_mask(query: int, candidates: np.ndarray, data: DataBundle) -> np.ndarray:
    mask = (data.case_id[candidates] != data.case_id[query]) & (data.lineage[candidates] != data.lineage[query])
    if int(data.seed[query]) != 0:
        mask &= data.seed[candidates] != data.seed[query]
    return mask


def fold_normalized(matrix: np.ndarray, arm: str, fold_index: int, rows: np.ndarray, data: DataBundle) -> np.ndarray:
    record = data.normalization["arms"][arm]["folds"][fold_index]
    median = np.asarray(record["median"], dtype=np.float64)
    divisor = np.asarray(record["divisor"], dtype=np.float64)
    return (matrix[rows] - median) / divisor


def validate_frozen_identities(data: DataBundle) -> None:
    all_rows = np.arange(EXPECTED_ROWS, dtype=np.int64)
    for query in range(EXPECTED_ROWS):
        for values in (data.frozen_neighbours["SS"][query], data.frozen_neighbours["MS"][query], data.random_rows[query]):
            if not legal_mask(query, np.asarray(values, dtype=np.int64), data).all():
                raise IntegrityError(f"MSO02D_D1_ILLEGAL_FROZEN_COMPARATOR: query={query}")
            if np.any(data.fold[np.asarray(values, dtype=np.int64)] == data.fold[query]):
                raise IntegrityError(f"MSO02D_D1_NONHELDOUT_FROZEN_COMPARATOR: query={query}")
    del all_rows

    for arm, matrix in (("SS", data.ss), ("MS", data.ms)):
        for fold_index in range(FOLD_COUNT):
            queries = np.flatnonzero(data.fold == fold_index)
            neighbours = data.frozen_neighbours[arm][queries]
            zq = fold_normalized(matrix, arm, fold_index, queries, data)
            zn = fold_normalized(matrix, arm, fold_index, neighbours.reshape(-1), data).reshape(
                queries.size, K, matrix.shape[1]
            )
            calculated = np.linalg.norm(zq[:, None, :] - zn, axis=2)
            recorded = data.frozen_distances[arm][queries]
            if not np.allclose(calculated, recorded, rtol=5.0e-13, atol=1.0e-10):
                raise IntegrityError(f"MSO02D_D1_FROZEN_DISTANCE_IDENTITY_CONFLICT: {arm} fold={fold_index}")
            for local, query in enumerate(queries):
                distances = recorded[local]
                candidates = neighbours[local]
                for index in range(1, K):
                    if distances[index] == distances[index - 1]:
                        previous = (str(data.case_id[candidates[index - 1]]), int(data.row_particle[candidates[index - 1]]))
                        current = (str(data.case_id[candidates[index]]), int(data.row_particle[candidates[index]]))
                        if current < previous:
                            raise IntegrityError(f"MSO02D_D1_FROZEN_TIE_ORDER_CONFLICT: {arm} query={query}")


def median_iqr(matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    q25, median, q75 = np.quantile(matrix, [0.25, 0.5, 0.75], axis=0)
    iqr = q75 - q25
    return median, np.where(iqr == 0.0, 1.0, iqr), iqr


def covariance_spectrum(matrix: np.ndarray) -> dict[str, Any]:
    centered = matrix - np.mean(matrix, axis=0)
    covariance = (centered.T @ centered) / float(matrix.shape[0])
    covariance = (covariance + covariance.T) * 0.5
    values, vectors = np.linalg.eigh(covariance)
    order = np.argsort(-values, kind="stable")
    values = np.maximum(values[order], 0.0)
    vectors = canonicalize_columns(vectors[:, order])
    total = float(np.sum(values))
    square_total = float(np.sum(values * values))
    participation = (total * total / square_total) if square_total > 0.0 else 0.0
    stable_rank = (total / float(values[0])) if values.size and values[0] > 0.0 else 0.0
    cumulative = np.cumsum(values) / total if total > 0.0 else np.zeros_like(values)

    def cumulative_rank(threshold: float) -> int:
        return int(np.searchsorted(cumulative, threshold, side="left") + 1) if total > 0.0 else 0

    return {
        "eigenvalues": values,
        "eigenvectors": vectors,
        "singular_values": np.sqrt(values * matrix.shape[0]),
        "participation_ratio": participation,
        "stable_rank": stable_rank,
        "rank_90": cumulative_rank(0.90),
        "rank_95": cumulative_rank(0.95),
        "rank_99": cumulative_rank(0.99),
        "trace": total,
    }


def canonicalize_columns(matrix: np.ndarray) -> np.ndarray:
    result = np.asarray(matrix, dtype=np.float64).copy()
    for column in range(result.shape[1]):
        pivot = int(np.argmax(np.abs(result[:, column])))
        if result[pivot, column] < 0.0:
            result[:, column] *= -1.0
    return result


def duplicate_counts(matrix: np.ndarray) -> tuple[int, int]:
    contiguous = np.ascontiguousarray(matrix)
    packed = contiguous.view(np.dtype((np.void, contiguous.dtype.itemsize * contiguous.shape[1]))).reshape(-1)
    _, counts = np.unique(packed, return_counts=True)
    duplicate_burden = int(np.sum(np.maximum(counts - 1, 0)))
    duplicate_member_count = int(np.sum(counts[counts > 1]))
    return duplicate_burden, duplicate_member_count


def participation_rank(values: np.ndarray) -> int:
    total = float(np.sum(values))
    square_total = float(np.sum(values * values))
    if square_total == 0.0:
        return 0
    return int(np.clip(math.ceil(total * total / square_total), 1, values.size))


def max_abs_feature_correlation(matrix: np.ndarray) -> float:
    if matrix.shape[1] < 2:
        return 0.0
    centered = matrix - np.mean(matrix, axis=0)
    norms = np.linalg.norm(centered, axis=0)
    valid = norms > 0.0
    if np.count_nonzero(valid) < 2:
        return 0.0
    unit = centered[:, valid] / norms[valid]
    correlation = np.abs(unit.T @ unit)
    np.fill_diagonal(correlation, 0.0)
    return float(np.max(correlation))


def t1_scope_matrix(
    arm: str, scope_type: str, scope_id: str, data: DataBundle
) -> tuple[np.ndarray, np.ndarray, str]:
    matrix = data.ss if arm == "SS" else data.ms
    if scope_type == "OVERALL":
        rows = np.arange(EXPECTED_ROWS, dtype=np.int64)
        median, divisor, _ = median_iqr(matrix[rows])
        semantics = "OBSERVABLE_ONLY_SCOPE_MEDIAN_IQR"
    elif scope_type == "TRAIN_EXCLUDING_FOLD":
        fold_index = int(scope_id.split("_")[-1])
        rows = np.flatnonzero(data.fold != fold_index)
        record = data.normalization["arms"][arm]["folds"][fold_index]
        median = np.asarray(record["median"], dtype=np.float64)
        divisor = np.asarray(record["divisor"], dtype=np.float64)
        semantics = "FROZEN_TRAIN_FOLD_MEDIAN_IQR"
    elif scope_type == "FAMILY":
        rows = np.flatnonzero(data.family == scope_id)
        global_median, global_divisor, _ = median_iqr(matrix)
        median, divisor = global_median, global_divisor
        semantics = "OBSERVABLE_ONLY_GLOBAL_MEDIAN_IQR_FOR_CROSS_FAMILY_COMPARISON"
    else:
        raise IntegrityError(f"MSO02D_D1_UNKNOWN_T1_SCOPE: {scope_type}")
    return rows, (matrix[rows] - median) / divisor, semantics


def compute_t1(data: DataBundle) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    group_rows: list[dict[str, Any]] = []
    spectra: dict[tuple[str, str, str], dict[str, Any]] = {}
    scopes = [("OVERALL", "ALL")]
    scopes.extend(("TRAIN_EXCLUDING_FOLD", f"FOLD_{fold}") for fold in range(FOLD_COUNT))
    scopes.extend(("FAMILY", family) for family in FAMILIES)
    for arm in ("SS", "MS"):
        raw = data.ss if arm == "SS" else data.ms
        for scope_type, scope_id in scopes:
            rows, normalized, normalization_semantics = t1_scope_matrix(arm, scope_type, scope_id, data)
            spectrum = covariance_spectrum(normalized)
            spectra[(arm, scope_type, scope_id)] = spectrum
            _, _, raw_iqr = median_iqr(raw[rows])
            duplicate_burden, duplicate_members = duplicate_counts(raw[rows])
            for index, (eigenvalue, singular) in enumerate(
                zip(spectrum["eigenvalues"], spectrum["singular_values"]), start=1
            ):
                diagnostics.append(
                    {
                        "evidence_class": EVIDENCE_CLASS,
                        "record_type": "COVARIANCE_AND_SINGULAR_SPECTRUM",
                        "arm": arm,
                        "scope_type": scope_type,
                        "scope_id": scope_id,
                        "normalization_semantics": normalization_semantics,
                        "row_count": int(rows.size),
                        "feature_dimension": int(raw.shape[1]),
                        "spectrum_index": index,
                        "covariance_eigenvalue": float(eigenvalue),
                        "singular_value": float(singular),
                        "participation_ratio": float(spectrum["participation_ratio"]),
                        "stable_rank": float(spectrum["stable_rank"]),
                        "cumulative_variance_rank_90": int(spectrum["rank_90"]),
                        "cumulative_variance_rank_95": int(spectrum["rank_95"]),
                        "cumulative_variance_rank_99": int(spectrum["rank_99"]),
                        "exact_duplicate_burden": duplicate_burden,
                        "exact_duplicate_member_count": duplicate_members,
                        "fold_iqr_degenerate_feature_count": int(np.count_nonzero(raw_iqr == 0.0)),
                        "diagnostic_only": True,
                    }
                )

            arm_groups = []
            for group in data.groups:
                indices = group["indices"][group["indices"] < raw.shape[1]]
                if indices.size:
                    arm_groups.append((group, indices))
            energy_matrix = np.column_stack(
                [np.sum(normalized[:, indices] ** 2, axis=1) for _, indices in arm_groups]
            )
            mean_energies = np.mean(energy_matrix, axis=0)
            total_energy = float(np.sum(mean_energies))
            for group_index, (group, indices) in enumerate(arm_groups):
                group_rows.append(
                    {
                        "evidence_class": EVIDENCE_CLASS,
                        "record_type": "SEMANTIC_GROUP_ENERGY",
                        "arm": arm,
                        "scope_type": scope_type,
                        "scope_id": scope_id,
                        "normalization_semantics": normalization_semantics,
                        "group_id": group["group_id"],
                        "group_name": group["group_name"],
                        "feature_count": int(indices.size),
                        "mean_total_squared_contribution": float(mean_energies[group_index]),
                        "fraction_of_all_group_energy": (
                            float(mean_energies[group_index] / total_energy) if total_energy > 0.0 else 0.0
                        ),
                        "maximum_absolute_within_group_feature_correlation": max_abs_feature_correlation(
                            normalized[:, indices]
                        ),
                        "zero_energy_status": (
                            "POSITIVE_ENERGY" if mean_energies[group_index] > 0.0 else "ZERO_ENERGY_UNIT_FALLBACK"
                        ),
                        "diagnostic_only": True,
                    }
                )
            if energy_matrix.shape[1] > 1:
                for left in range(energy_matrix.shape[1]):
                    for right in range(left + 1, energy_matrix.shape[1]):
                        x = energy_matrix[:, left]
                        y = energy_matrix[:, right]
                        if np.std(x) == 0.0 or np.std(y) == 0.0:
                            correlation = 0.0
                            status = "NOT_APPLICABLE_ZERO_VARIANCE"
                        else:
                            correlation = float(np.corrcoef(x, y)[0, 1])
                            status = "APPLICABLE"
                        group_rows.append(
                            {
                                "evidence_class": EVIDENCE_CLASS,
                                "record_type": "SCALE_RESPONSE_GROUP_ENERGY_COLLINEARITY",
                                "arm": arm,
                                "scope_type": scope_type,
                                "scope_id": scope_id,
                                "normalization_semantics": normalization_semantics,
                                "group_id": arm_groups[left][0]["group_id"],
                                "group_id_2": arm_groups[right][0]["group_id"],
                                "group_energy_pearson_correlation": correlation,
                                "correlation_status": status,
                                "diagnostic_only": True,
                            }
                        )

    stability: list[dict[str, Any]] = []
    for arm in ("SS", "MS"):
        for scope_type, identifiers, stability_type in (
            ("TRAIN_EXCLUDING_FOLD", [f"FOLD_{fold}" for fold in range(FOLD_COUNT)], "CROSS_FOLD"),
            ("FAMILY", list(FAMILIES), "CROSS_FAMILY"),
        ):
            for left_index, left in enumerate(identifiers):
                for right in identifiers[left_index + 1 :]:
                    a = spectra[(arm, scope_type, left)]
                    b = spectra[(arm, scope_type, right)]
                    rank_a = max(1, participation_rank(a["eigenvalues"]))
                    rank_b = max(1, participation_rank(b["eigenvalues"]))
                    rank = min(rank_a, rank_b)
                    singular = np.linalg.svd(
                        a["eigenvectors"][:, :rank].T @ b["eigenvectors"][:, :rank], compute_uv=False
                    )
                    singular = np.clip(singular, 0.0, 1.0)
                    angles = np.degrees(np.arccos(singular))
                    stability.append(
                        {
                            "evidence_class": EVIDENCE_CLASS,
                            "record_type": "PRINCIPAL_SUBSPACE_STABILITY",
                            "arm": arm,
                            "scope_type": stability_type,
                            "scope_id": f"{left}__{right}",
                            "left_scope": left,
                            "right_scope": right,
                            "left_participation_rank": rank_a,
                            "right_participation_rank": rank_b,
                            "comparison_rank": rank,
                            "projector_overlap_per_rank": float(np.mean(singular * singular)),
                            "principal_angle_median_degrees": float(np.median(angles)),
                            "principal_angle_maximum_degrees": float(np.max(angles)),
                            "diagnostic_only": True,
                        }
                    )
    return diagnostics, stability, group_rows, spectra


@dataclass
class Transform:
    candidate_id: str
    offset: np.ndarray
    linear: np.ndarray
    applicable: bool
    status: str
    effective_dimension: float
    rank: int
    group_multipliers: np.ndarray | None = None

    def apply(self, matrix: np.ndarray) -> np.ndarray:
        return (matrix - self.offset) @ self.linear


def fit_transform(candidate_id: str, training_z: np.ndarray, groups: Sequence[dict[str, Any]]) -> Transform:
    dimension = training_z.shape[1]
    if candidate_id == "U0":
        spectrum = covariance_spectrum(training_z)
        return Transform(
            candidate_id, np.zeros(dimension), np.eye(dimension), True, "APPLICABLE_FORMAL_IDENTITY",
            float(spectrum["participation_ratio"]), dimension,
        )
    if candidate_id == "U1":
        multipliers = np.ones(len(groups), dtype=np.float64)
        feature_weights = np.ones(dimension, dtype=np.float64)
        statuses: list[str] = []
        for group_index, group in enumerate(groups):
            indices = group["indices"]
            energy = float(np.mean(np.sum(training_z[:, indices] ** 2, axis=1)))
            if energy > 0.0:
                multipliers[group_index] = energy ** -0.5
                statuses.append("POSITIVE_ENERGY")
            else:
                multipliers[group_index] = 1.0
                statuses.append("ZERO_ENERGY_UNIT_FALLBACK")
            feature_weights[indices] = multipliers[group_index]
        transformed = training_z * feature_weights
        spectrum = covariance_spectrum(transformed)
        return Transform(
            candidate_id, np.zeros(dimension), np.diag(feature_weights), True,
            ";".join(statuses), float(spectrum["participation_ratio"]), dimension, multipliers,
        )
    if candidate_id == "U2":
        mean = np.mean(training_z, axis=0)
        spectrum = covariance_spectrum(training_z)
        rank = participation_rank(spectrum["eigenvalues"])
        if rank == 0:
            return Transform(
                candidate_id, mean, np.zeros((dimension, 1)), False,
                "NOT_APPLICABLE_ZERO_COVARIANCE", 0.0, 0,
            )
        linear = spectrum["eigenvectors"][:, :rank]
        projected = (training_z - mean) @ linear
        effective = covariance_spectrum(projected)["participation_ratio"]
        return Transform(candidate_id, mean, linear, True, "APPLICABLE_PARTICIPATION_RANK", float(effective), rank)
    if candidate_id == "U3":
        estimator = LedoitWolf(assume_centered=False, store_precision=False, block_size=1000).fit(training_z)
        covariance = (np.asarray(estimator.covariance_) + np.asarray(estimator.covariance_).T) * 0.5
        values, vectors = np.linalg.eigh(covariance)
        order = np.argsort(-values, kind="stable")
        values = values[order]
        vectors = canonicalize_columns(vectors[:, order])
        maximum = float(values[0]) if values.size else 0.0
        if maximum <= 0.0:
            return Transform(
                candidate_id, np.asarray(estimator.location_), np.zeros((dimension, dimension)), False,
                "NOT_APPLICABLE_ZERO_COVARIANCE", 0.0, 0,
            )
        threshold = maximum * EIGEN_TOL
        clipped = np.maximum(values, threshold)
        inverse_root = (vectors * (clipped ** -0.5)) @ vectors.T
        whitened = (training_z - np.asarray(estimator.location_)) @ inverse_root
        effective = covariance_spectrum(whitened)["participation_ratio"]
        status = f"APPLICABLE_LEDOIT_WOLF_EIGEN_CLIP_{threshold:.17g}"
        return Transform(
            candidate_id, np.asarray(estimator.location_), inverse_root, True, status,
            float(effective), dimension,
        )
    raise IntegrityError(f"MSO02D_D1_UNKNOWN_CANDIDATE: {candidate_id}")


def cosine_similarity(left: np.ndarray, right: np.ndarray) -> float:
    denominator = float(np.linalg.norm(left) * np.linalg.norm(right))
    if denominator == 0.0:
        return 1.0 if np.array_equal(left, right) else 0.0
    return float(np.dot(left.reshape(-1), right.reshape(-1)) / denominator)


def transform_similarity(left: Transform, right: Transform) -> float:
    if not left.applicable or not right.applicable:
        return 0.0
    if left.candidate_id == "U1":
        assert left.group_multipliers is not None and right.group_multipliers is not None
        return cosine_similarity(np.log(left.group_multipliers), np.log(right.group_multipliers))
    if left.candidate_id == "U2":
        rank = min(left.rank, right.rank)
        if rank == 0:
            return 0.0
        singular = np.linalg.svd(left.linear[:, :rank].T @ right.linear[:, :rank], compute_uv=False)
        return float(np.sum(np.clip(singular, 0.0, 1.0) ** 2) / rank)
    if left.candidate_id == "U3":
        return cosine_similarity(left.linear, right.linear)
    return 1.0


def prepare_transforms(data: DataBundle) -> tuple[dict[str, dict[int, Transform]], list[dict[str, Any]], dict[str, np.ndarray]]:
    fold_transforms: dict[str, dict[int, Transform]] = {candidate: {} for candidate in CANDIDATES}
    family_transforms: dict[str, dict[str, Transform]] = {candidate: {} for candidate in CANDIDATES}
    parameters: dict[str, np.ndarray] = {
        "candidate_ids": np.asarray(CANDIDATES),
        "fold_ids": np.arange(FOLD_COUNT, dtype=np.int8),
        "evidence_class": np.asarray(EVIDENCE_CLASS),
        "parameter_semantics": np.asarray("APPLY_TO_FROZEN_U0_NORMALIZED_MS_AS_(Z_OFFSET)@LINEAR"),
    }
    for fold_index in range(FOLD_COUNT):
        training_rows = np.flatnonzero(data.fold != fold_index)
        training_z = fold_normalized(data.ms, "MS", fold_index, training_rows, data)
        for candidate_id in CANDIDATES:
            transform = fit_transform(candidate_id, training_z, data.groups)
            fold_transforms[candidate_id][fold_index] = transform
            prefix = f"{candidate_id}_fold_{fold_index}"
            parameters[f"{prefix}_offset"] = transform.offset
            parameters[f"{prefix}_linear"] = transform.linear
            parameters[f"{prefix}_applicable"] = np.asarray(transform.applicable)
            parameters[f"{prefix}_rank"] = np.asarray(transform.rank, dtype=np.int32)
            parameters[f"{prefix}_effective_dimension"] = np.asarray(transform.effective_dimension)
            parameters[f"{prefix}_status"] = np.asarray(transform.status)
            if transform.group_multipliers is not None:
                parameters[f"{prefix}_group_multipliers"] = transform.group_multipliers

    global_median, global_divisor, _ = median_iqr(data.ms)
    global_z = (data.ms - global_median) / global_divisor
    for family in FAMILIES:
        family_z = global_z[data.family == family]
        for candidate_id in CANDIDATES:
            family_transforms[candidate_id][family] = fit_transform(candidate_id, family_z, data.groups)

    stability_rows: list[dict[str, Any]] = []
    for candidate_id in CANDIDATES:
        for scope, identities, collection in (
            ("CROSS_FOLD", list(range(FOLD_COUNT)), fold_transforms[candidate_id]),
            ("CROSS_FAMILY", list(FAMILIES), family_transforms[candidate_id]),
        ):
            for left_index, left_id in enumerate(identities):
                for right_id in identities[left_index + 1 :]:
                    similarity = transform_similarity(collection[left_id], collection[right_id])
                    stability_rows.append(
                        {
                            "evidence_class": EVIDENCE_CLASS,
                            "record_type": "CANDIDATE_TRANSFORM_STABILITY",
                            "arm": "MS",
                            "candidate_id": candidate_id,
                            "scope_type": scope,
                            "scope_id": f"{left_id}__{right_id}",
                            "left_transform": str(left_id),
                            "right_transform": str(right_id),
                            "transform_similarity": similarity,
                            "threshold": 0.75,
                            "pair_pass": bool(similarity >= 0.75),
                            "similarity_semantics": {
                                "U0": "IDENTITY",
                                "U1": "COSINE_OF_LOG_GROUP_MULTIPLIERS",
                                "U2": "PROJECTOR_OVERLAP_DIVIDED_BY_COMPARISON_RANK",
                                "U3": "NORMALIZED_FROBENIUS_SIMILARITY_OF_INVERSE_ROOT_TRANSFORMS",
                            }[candidate_id],
                            "diagnostic_only": True,
                        }
                    )
    return fold_transforms, stability_rows, parameters


def exact_legal_knn(
    train_x: np.ndarray,
    query_x: np.ndarray,
    train_rows: np.ndarray,
    query_rows: np.ndarray,
    data: DataBundle,
) -> tuple[np.ndarray, np.ndarray]:
    tree = cKDTree(train_x, compact_nodes=True, balanced_tree=True)
    neighbours = np.full((query_rows.size, K), -1, dtype=np.int32)
    distances_out = np.full((query_rows.size, K), np.nan, dtype=np.float64)
    schedules = tuple(sorted(set(min(train_rows.size, value) for value in (64, 256, 2048, train_rows.size))))
    for start in range(0, query_rows.size, 128):
        local_chunk = np.arange(start, min(start + 128, query_rows.size), dtype=np.int64)
        unresolved = local_chunk.copy()
        for use_k in schedules:
            if unresolved.size == 0:
                break
            tree_distance, local_indices = tree.query(query_x[unresolved], k=use_k, eps=0.0, p=2, workers=1)
            if use_k == 1:
                tree_distance = tree_distance[:, None]
                local_indices = local_indices[:, None]
            remaining: list[int] = []
            for local_index, query_local_index in enumerate(unresolved):
                query = int(query_rows[query_local_index])
                candidate_local = np.asarray(local_indices[local_index], dtype=np.int64)
                candidate_rows = train_rows[candidate_local]
                legal = legal_mask(query, candidate_rows, data)
                candidate_local = candidate_local[legal]
                candidate_rows = candidate_rows[legal]
                if candidate_rows.size:
                    exact_distance = np.linalg.norm(train_x[candidate_local] - query_x[query_local_index], axis=1)
                    ordered = sorted(
                        (
                            float(distance), str(data.case_id[row]), int(data.row_particle[row]), int(row)
                        )
                        for distance, row in zip(exact_distance, candidate_rows)
                    )
                else:
                    ordered = []
                boundary = float(np.asarray(tree_distance[local_index], dtype=np.float64)[-1])
                complete = len(ordered) >= K and (
                    use_k == train_rows.size or ordered[K - 1][0] < boundary
                )
                if complete:
                    chosen = ordered[:K]
                    neighbours[query_local_index] = [item[3] for item in chosen]
                    distances_out[query_local_index] = [item[0] for item in chosen]
                else:
                    remaining.append(int(query_local_index))
            unresolved = np.asarray(remaining, dtype=np.int64)
        if unresolved.size:
            raise IntegrityError("MSO02D_D1_EXACT_K10_COMPLETION_FAILURE")
    if not np.isfinite(distances_out).all() or np.any(neighbours < 0):
        raise IntegrityError("MSO02D_D1_EXACT_K10_NONFINITE")
    return neighbours, distances_out


def comparator_distances(
    z: np.ndarray,
    rows: np.ndarray,
    comparator_rows: np.ndarray,
    transform: Transform,
    row_to_local: Mapping[int, int] | None,
    full_z_lookup: callable,
) -> np.ndarray:
    result = np.empty((rows.size, K), dtype=np.float64)
    for start in range(0, rows.size, 256):
        stop = min(start + 256, rows.size)
        qrows = rows[start:stop]
        qz = z[start:stop]
        comparators = comparator_rows[start:stop]
        comparator_z = full_z_lookup(comparators.reshape(-1)).reshape(stop - start, K, z.shape[1])
        tq = transform.apply(qz)
        tc = transform.apply(comparator_z.reshape(-1, z.shape[1])).reshape(stop - start, K, -1)
        result[start:stop] = np.linalg.norm(tq[:, None, :] - tc, axis=2)
    return result


def group_distance_diagnostics(
    query_z: np.ndarray,
    neighbour_z: np.ndarray,
    transform: Transform,
    groups: Sequence[dict[str, Any]],
) -> tuple[np.ndarray, np.ndarray]:
    query_count = query_z.shape[0]
    group_share = np.zeros((query_count, len(groups)), dtype=np.float64)
    domination = np.zeros(query_count, dtype=np.float64)
    for start in range(0, query_count, 128):
        stop = min(start + 128, query_count)
        delta = (query_z[start:stop, None, :] - neighbour_z[start:stop]).reshape(-1, query_z.shape[1])
        contribution = np.zeros((delta.shape[0], len(groups)), dtype=np.float64)
        for group_index, group in enumerate(groups):
            indices = group["indices"]
            projected = delta[:, indices] @ transform.linear[indices, :]
            contribution[:, group_index] = np.einsum("ij,ij->i", projected, projected)
        total = np.sum(contribution, axis=1)
        shares = np.divide(contribution, total[:, None], out=np.zeros_like(contribution), where=total[:, None] > 0.0)
        shares = shares.reshape(stop - start, K, len(groups))
        group_share[start:stop] = np.mean(shares, axis=1)
        domination[start:stop] = np.mean(np.max(shares, axis=2), axis=1)
    return group_share, domination


def checkpoint_path(candidate_id: str, fold_index: int) -> Path:
    return CHECKPOINTS / f"geometry_{candidate_id}_fold{fold_index}.npz"


def checkpoint_fingerprint(input_hashes: Mapping[str, str], candidate_id: str, fold_index: int) -> str:
    return canonical_digest(
        {
            "version": CHECKPOINT_VERSION,
            "candidate_id": candidate_id,
            "fold": fold_index,
            "input_sha256": dict(sorted(input_hashes.items())),
            "k": K,
            "tie_order": ["distance", "case_id", "particle_id"],
        }
    )


def compute_candidate_fold(
    candidate_id: str,
    fold_index: int,
    transform: Transform,
    data: DataBundle,
    input_hashes: Mapping[str, str],
) -> dict[str, np.ndarray]:
    if not transform.applicable:
        raise IntegrityError(f"MSO02D_D1_CANDIDATE_NOT_APPLICABLE: {candidate_id} fold={fold_index}")
    queries = ordered_rows(np.flatnonzero(data.fold == fold_index), data)
    training = ordered_rows(np.flatnonzero(data.fold != fold_index), data)
    fingerprint = checkpoint_fingerprint(input_hashes, candidate_id, fold_index)
    path = checkpoint_path(candidate_id, fold_index)
    if path.exists():
        with np.load(path, allow_pickle=False) as saved:
            required = {
                "checkpoint_version", "evidence_class", "stage", "fingerprint", "candidate_id", "fold", "query_row_index",
                "neighbor_row_index", "neighbor_distance", "random_comparator_distance",
                "group_distance_share", "group_domination",
            }
            if not required.issubset(saved.files):
                raise IntegrityError(f"MSO02D_D1_CHECKPOINT_SCHEMA_CONFLICT: {rel(path)}")
            if str(saved["checkpoint_version"].item()) != CHECKPOINT_VERSION:
                raise IntegrityError(f"MSO02D_D1_CHECKPOINT_VERSION_CONFLICT: {rel(path)}")
            if str(saved["evidence_class"].item()) != EVIDENCE_CLASS or str(saved["stage"].item()) != "MSO-02D-D1":
                raise IntegrityError(f"MSO02D_D1_CHECKPOINT_EVIDENCE_CLASS_CONFLICT: {rel(path)}")
            if str(saved["fingerprint"].item()) != fingerprint:
                raise IntegrityError(f"MSO02D_D1_CHECKPOINT_IDENTITY_CONFLICT: {rel(path)}")
            result = {key: np.asarray(saved[key]) for key in required}
        if not np.array_equal(result["query_row_index"], queries.astype(np.int32)):
            raise IntegrityError(f"MSO02D_D1_CHECKPOINT_QUERY_CONFLICT: {rel(path)}")
        return result

    record = data.normalization["arms"]["MS"]["folds"][fold_index]
    median = np.asarray(record["median"], dtype=np.float64)
    divisor = np.asarray(record["divisor"], dtype=np.float64)

    def normalize_rows(rows: np.ndarray) -> np.ndarray:
        return (data.ms[rows] - median) / divisor

    training_z = normalize_rows(training)
    query_z = normalize_rows(queries)
    neighbours, distances = exact_legal_knn(
        transform.apply(training_z), transform.apply(query_z), training, queries, data
    )
    random_distance = comparator_distances(
        query_z, queries, data.random_rows[queries], transform, None, normalize_rows
    )
    neighbour_z = normalize_rows(neighbours.reshape(-1)).reshape(queries.size, K, data.ms.shape[1])
    group_share, domination = group_distance_diagnostics(query_z, neighbour_z, transform, data.groups)
    arrays = {
        "checkpoint_version": np.asarray(CHECKPOINT_VERSION),
        "evidence_class": np.asarray(EVIDENCE_CLASS),
        "stage": np.asarray("MSO-02D-D1"),
        "fingerprint": np.asarray(fingerprint),
        "candidate_id": np.asarray(candidate_id),
        "fold": np.asarray(fold_index, dtype=np.int8),
        "query_row_index": queries.astype(np.int32),
        "neighbor_row_index": neighbours.astype(np.int32),
        "neighbor_distance": distances,
        "random_comparator_distance": random_distance,
        "group_distance_share": group_share,
        "group_domination": domination,
    }
    atomic_npz(path, **arrays)
    return arrays


def frozen_u0_result(arm: str, data: DataBundle, transforms: dict[int, Transform] | None) -> dict[str, Any]:
    matrix = data.ss if arm == "SS" else data.ms
    groups = []
    for group in data.groups:
        indices = group["indices"][group["indices"] < matrix.shape[1]]
        if indices.size:
            copy = dict(group)
            copy["indices"] = indices
            groups.append(copy)
    neighbours = data.frozen_neighbours[arm].copy()
    distances = data.frozen_distances[arm].copy()
    random_distance = np.empty((EXPECTED_ROWS, K), dtype=np.float64)
    group_share = np.zeros((EXPECTED_ROWS, len(groups)), dtype=np.float64)
    domination = np.zeros(EXPECTED_ROWS, dtype=np.float64)
    effective: dict[int, float] = {}
    for fold_index in range(FOLD_COUNT):
        queries = np.flatnonzero(data.fold == fold_index)
        record = data.normalization["arms"][arm]["folds"][fold_index]
        median = np.asarray(record["median"], dtype=np.float64)
        divisor = np.asarray(record["divisor"], dtype=np.float64)

        def normalize_rows(rows: np.ndarray) -> np.ndarray:
            return (matrix[rows] - median) / divisor

        qz = normalize_rows(queries)
        transform = transforms[fold_index] if transforms is not None else fit_transform(
            "U0", normalize_rows(np.flatnonzero(data.fold != fold_index)), groups
        )
        random_distance[queries] = comparator_distances(
            qz, queries, data.random_rows[queries], transform, None, normalize_rows
        )
        nz = normalize_rows(neighbours[queries].reshape(-1)).reshape(queries.size, K, matrix.shape[1])
        shares, dom = group_distance_diagnostics(qz, nz, transform, groups)
        group_share[queries] = shares
        domination[queries] = dom
        effective[fold_index] = transform.effective_dimension
    return {
        "arm": arm,
        "candidate_id": "U0",
        "neighbours": neighbours,
        "distances": distances,
        "random_distances": random_distance,
        "group_share": group_share,
        "group_ids": [group["group_id"] for group in groups],
        "domination": domination,
        "effective_dimension": effective,
    }


def assemble_candidate_result(
    candidate_id: str,
    fold_transforms: Mapping[int, Transform],
    data: DataBundle,
    input_hashes: Mapping[str, str],
) -> dict[str, Any]:
    neighbours = np.full((EXPECTED_ROWS, K), -1, dtype=np.int32)
    distances = np.full((EXPECTED_ROWS, K), np.nan, dtype=np.float64)
    random_distance = np.full((EXPECTED_ROWS, K), np.nan, dtype=np.float64)
    group_share = np.zeros((EXPECTED_ROWS, len(data.groups)), dtype=np.float64)
    domination = np.zeros(EXPECTED_ROWS, dtype=np.float64)
    for fold_index in range(FOLD_COUNT):
        saved = compute_candidate_fold(
            candidate_id, fold_index, fold_transforms[fold_index], data, input_hashes
        )
        rows = np.asarray(saved["query_row_index"], dtype=np.int64)
        neighbours[rows] = saved["neighbor_row_index"]
        distances[rows] = saved["neighbor_distance"]
        random_distance[rows] = saved["random_comparator_distance"]
        group_share[rows] = saved["group_distance_share"]
        domination[rows] = saved["group_domination"]
    if np.any(neighbours < 0) or not np.isfinite(distances).all() or not np.isfinite(random_distance).all():
        raise IntegrityError(f"MSO02D_D1_CANDIDATE_ASSEMBLY_FAILURE: {candidate_id}")
    return {
        "arm": "MS",
        "candidate_id": candidate_id,
        "neighbours": neighbours,
        "distances": distances,
        "random_distances": random_distance,
        "group_share": group_share,
        "group_ids": [group["group_id"] for group in data.groups],
        "domination": domination,
        "effective_dimension": {
            fold: fold_transforms[fold].effective_dimension for fold in range(FOLD_COUNT)
        },
    }


def gini(values: np.ndarray) -> float:
    values = np.asarray(values, dtype=np.float64)
    if values.size == 0 or np.any(values < 0.0):
        raise IntegrityError("MSO02D_D1_GINI_INPUT_CONFLICT")
    total = float(np.sum(values))
    if total == 0.0:
        return 0.0
    ordered = np.sort(values)
    index = np.arange(1, ordered.size + 1, dtype=np.float64)
    return float(np.sum((2.0 * index - ordered.size - 1.0) * ordered) / (ordered.size * total))


def safe_cv(values: np.ndarray) -> float:
    mean = float(np.mean(values))
    return float(np.std(values) / abs(mean)) if mean != 0.0 else 0.0


def scope_masks(data: DataBundle) -> list[tuple[str, str, np.ndarray]]:
    scopes: list[tuple[str, str, np.ndarray]] = [
        ("OVERALL", "ALL", np.ones(EXPECTED_ROWS, dtype=bool))
    ]
    scopes.extend(("FOLD", f"FOLD_{fold}", data.fold == fold) for fold in range(FOLD_COUNT))
    scopes.extend(("FAMILY", family, data.family == family) for family in FAMILIES)
    return scopes


def occurrence_pool(scope_type: str, scope_id: str, mask: np.ndarray, data: DataBundle) -> np.ndarray:
    if scope_type == "FOLD":
        fold_index = int(scope_id.split("_")[-1])
        return np.flatnonzero(data.fold != fold_index)
    used_folds = np.unique(data.fold[mask])
    if used_folds.size == FOLD_COUNT:
        return np.arange(EXPECTED_ROWS, dtype=np.int64)
    return np.flatnonzero(~np.isin(data.fold, used_folds))


def geometry_metrics(result: Mapping[str, Any], data: DataBundle) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    distances = np.asarray(result["distances"])
    random_distance = np.asarray(result["random_distances"])
    neighbours = np.asarray(result["neighbours"])
    domination = np.asarray(result["domination"])
    for scope_type, scope_id, mask in scope_masks(data):
        query_rows = np.flatnonzero(mask)
        d = distances[query_rows]
        rd = random_distance[query_rows]
        random_median_per_query = np.median(rd, axis=1)
        nearest_ratio = np.divide(
            d[:, 0], random_median_per_query, out=np.full(query_rows.size, np.nan),
            where=random_median_per_query > 0.0,
        )
        k10_ratio = np.divide(
            np.mean(d, axis=1), random_median_per_query, out=np.full(query_rows.size, np.nan),
            where=random_median_per_query > 0.0,
        )
        k10_cv = np.divide(
            np.std(d, axis=1), np.mean(d, axis=1), out=np.zeros(query_rows.size),
            where=np.mean(d, axis=1) > 0.0,
        )
        finite = np.isfinite(nearest_ratio) & np.isfinite(k10_ratio)
        if not finite.all():
            raise IntegrityError(
                f"MSO02D_D1_NONFINITE_DISTANCE_RATIO: {result['candidate_id']} {scope_type} {scope_id}"
            )
        flat_random = rd.reshape(-1)
        random_p10, random_median, random_p90 = np.quantile(flat_random, [0.10, 0.50, 0.90])
        pool = occurrence_pool(scope_type, scope_id, mask, data)
        counts_full = np.bincount(neighbours[query_rows].reshape(-1), minlength=EXPECTED_ROWS)
        counts = counts_full[pool]
        skew_value = float(skew(counts, bias=False)) if np.std(counts) > 0.0 else 0.0
        effective_values = np.asarray(list(result["effective_dimension"].values()), dtype=np.float64)
        if scope_type == "FOLD":
            effective = float(result["effective_dimension"][int(scope_id.split("_")[-1])])
        else:
            effective = float(np.median(effective_values))
        rows.append(
            {
                "evidence_class": EVIDENCE_CLASS,
                "record_type": "OBSERVABLE_GEOMETRY_SUMMARY",
                "arm": result["arm"],
                "candidate_id": result["candidate_id"],
                "scope_type": scope_type,
                "scope_id": scope_id,
                "query_count": int(query_rows.size),
                "k": K,
                "k1_distance_p10": float(np.quantile(d[:, 0], 0.10)),
                "k1_distance_median": float(np.median(d[:, 0])),
                "k1_distance_p90": float(np.quantile(d[:, 0], 0.90)),
                "k10_mean_distance_p10": float(np.quantile(np.mean(d, axis=1), 0.10)),
                "k10_mean_distance_median": float(np.median(np.mean(d, axis=1))),
                "k10_mean_distance_p90": float(np.quantile(np.mean(d, axis=1), 0.90)),
                "random_distance_p10": float(random_p10),
                "random_distance_median": float(random_median),
                "random_distance_p90": float(random_p90),
                "nearest_to_random_median_ratio": float(np.median(nearest_ratio)),
                "nearest_to_median_ratio": float(np.median(nearest_ratio)),
                "k10_to_random_median_ratio": float(np.median(k10_ratio)),
                "k10_to_median_ratio": float(np.median(k10_ratio)),
                "distance_concentration_index": (
                    float((random_p90 - random_p10) / random_median) if random_median > 0.0 else 0.0
                ),
                "distance_concentration_index_definition": "(MATCHED_RANDOM_P90-P10)/MATCHED_RANDOM_MEDIAN; LOWER_MEANS_MORE_CONCENTRATED",
                "k10_distance_coefficient_of_variation": float(np.median(k10_cv)),
                "hubness_occurrence_skew": skew_value,
                "neighbour_occurrence_gini": gini(counts),
                "neighbor_occurrence_gini": gini(counts),
                "neighbour_occurrence_maximum": int(np.max(counts)),
                "zero_occurrence_fraction": float(np.mean(counts == 0)),
                "semantic_group_domination": float(np.median(domination[query_rows])),
                "effective_geometry_dimension": effective,
                "exact_duplicate_nearest_query_count": int(np.count_nonzero(d[:, 0] == 0.0)),
                "exact_duplicate_k10_edge_count": int(np.count_nonzero(d == 0.0)),
                "duplicate_coordinate_domination_fraction": float(np.mean(d == 0.0)),
                "near_duplicate_k10_edge_count": int(
                    np.count_nonzero(d <= np.maximum(1.0e-12, random_median_per_query[:, None] * 1.0e-12))
                ),
                "all_finite": True,
                "diagnostic_only": True,
            }
        )
    return rows


def overlap_fraction(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    result = np.empty(left.shape[0], dtype=np.float64)
    for start in range(0, left.shape[0], 1024):
        stop = min(start + 1024, left.shape[0])
        intersection = (left[start:stop, :, None] == right[start:stop, None, :]).any(axis=2).sum(axis=1)
        result[start:stop] = intersection / float(K)
    return result


def turnover_rows(
    comparison_id: str,
    left_arm: str,
    left_candidate: str,
    left: np.ndarray,
    right_arm: str,
    right_candidate: str,
    right: np.ndarray,
    data: DataBundle,
) -> list[dict[str, Any]]:
    overlap = overlap_fraction(left, right)
    rows: list[dict[str, Any]] = []
    for scope_type, scope_id, mask in scope_masks(data):
        values = overlap[mask]
        rows.append(
            {
                "evidence_class": EVIDENCE_CLASS,
                "record_type": "NEIGHBOUR_SET_TURNOVER",
                "arm": f"{left_arm}->{right_arm}",
                "candidate_id": f"{left_candidate}->{right_candidate}",
                "scope_type": scope_type,
                "scope_id": scope_id,
                "comparison_id": comparison_id,
                "query_count": int(values.size),
                "k": K,
                "mean_shared_neighbour_fraction": float(np.mean(values)),
                "median_shared_neighbour_fraction": float(np.median(values)),
                "mean_neighbour_turnover": float(np.mean(1.0 - values)),
                "median_neighbour_turnover": float(np.median(1.0 - values)),
                "complete_turnover_fraction": float(np.mean(values == 0.0)),
                "identical_set_fraction": float(np.mean(values == 1.0)),
                "tie_semantics": "DISTANCE_THEN_CASE_ID_THEN_PARTICLE_ID",
                "diagnostic_only": True,
            }
        )
    return rows


def metric_lookup(rows: Sequence[Mapping[str, Any]]) -> dict[tuple[str, str, str], Mapping[str, Any]]:
    return {
        (str(row["candidate_id"]), str(row["scope_type"]), str(row["scope_id"])): row
        for row in rows
        if row["arm"] == "MS"
    }


def median_scope_metric(
    lookup: Mapping[tuple[str, str, str], Mapping[str, Any]], candidate: str, scope: str, field: str
) -> float:
    identifiers = [f"FOLD_{fold}" for fold in range(FOLD_COUNT)] if scope == "FOLD" else list(FAMILIES)
    return float(np.median([float(lookup[(candidate, scope, identifier)][field]) for identifier in identifiers]))


def count_passes(
    lookup: Mapping[tuple[str, str, str], Mapping[str, Any]], candidate: str, scope: str, criterion: str
) -> int:
    identifiers = [f"FOLD_{fold}" for fold in range(FOLD_COUNT)] if scope == "FOLD" else list(FAMILIES)
    passed = 0
    for identifier in identifiers:
        value = lookup[(candidate, scope, identifier)]
        reference = lookup[("U0", scope, identifier)]
        if criterion == "concentration":
            condition = (
                float(value["k10_to_random_median_ratio"])
                <= float(reference["k10_to_random_median_ratio"]) * 1.01
                and float(value["nearest_to_random_median_ratio"])
                <= float(reference["nearest_to_random_median_ratio"]) * 1.01
            )
        elif criterion == "hubness":
            condition = float(value["neighbour_occurrence_gini"]) <= float(reference["neighbour_occurrence_gini"]) + 0.01
        elif criterion == "domination":
            condition = float(value["semantic_group_domination"]) <= float(reference["semantic_group_domination"]) + 0.01
        else:
            raise IntegrityError(f"MSO02D_D1_UNKNOWN_SELECTION_CRITERION: {criterion}")
        passed += int(condition)
    return passed


def ordinal_ranks(candidates: Sequence[str], values: Mapping[str, float]) -> dict[str, int]:
    ordered = sorted(candidates, key=lambda candidate: (values[candidate], CANDIDATES.index(candidate)))
    return {candidate: index + 1 for index, candidate in enumerate(ordered)}


def select_candidate(
    geometry_rows: Sequence[Mapping[str, Any]], transform_stability: Sequence[Mapping[str, Any]]
) -> tuple[list[dict[str, Any]], str | None, str]:
    lookup = metric_lookup(geometry_rows)
    stability_summary: dict[str, tuple[float, float]] = {}
    for candidate in CANDIDATES:
        fold_values = [
            float(row["transform_similarity"]) for row in transform_stability
            if row["candidate_id"] == candidate and row["scope_type"] == "CROSS_FOLD"
        ]
        family_values = [
            float(row["transform_similarity"]) for row in transform_stability
            if row["candidate_id"] == candidate and row["scope_type"] == "CROSS_FAMILY"
        ]
        stability_summary[candidate] = (float(np.median(fold_values)), float(np.median(family_values)))

    summary: dict[str, dict[str, Any]] = {}
    for candidate in CANDIDATES:
        fold_concentration = 6 if candidate == "U0" else count_passes(lookup, candidate, "FOLD", "concentration")
        family_concentration = 4 if candidate == "U0" else count_passes(lookup, candidate, "FAMILY", "concentration")
        fold_hubness = 6 if candidate == "U0" else count_passes(lookup, candidate, "FOLD", "hubness")
        family_hubness = 4 if candidate == "U0" else count_passes(lookup, candidate, "FAMILY", "hubness")
        fold_domination = 6 if candidate == "U0" else count_passes(lookup, candidate, "FOLD", "domination")
        family_domination = 4 if candidate == "U0" else count_passes(lookup, candidate, "FAMILY", "domination")
        fold_k10 = median_scope_metric(lookup, candidate, "FOLD", "k10_to_random_median_ratio")
        fold_gini = median_scope_metric(lookup, candidate, "FOLD", "neighbour_occurrence_gini")
        fold_dom = median_scope_metric(lookup, candidate, "FOLD", "semantic_group_domination")
        fold_values = [float(lookup[(candidate, "FOLD", f"FOLD_{fold}")]["k10_to_random_median_ratio"]) for fold in range(FOLD_COUNT)]
        family_values = [float(lookup[(candidate, "FAMILY", family)]["k10_to_random_median_ratio"]) for family in FAMILIES]
        transport_cv = 0.5 * (safe_cv(np.asarray(fold_values)) + safe_cv(np.asarray(family_values)))
        fold_stability, family_stability = stability_summary[candidate]
        gates = (
            fold_concentration >= 5 and family_concentration >= 3
            and fold_hubness >= 5 and family_hubness >= 3
            and fold_domination >= 5 and family_domination >= 3
            and fold_stability >= 0.75 and family_stability >= 0.75
        )
        if candidate == "U0":
            improvement_count = 0
            eligible = False
        else:
            improvement_count = sum(
                (
                    fold_k10 < median_scope_metric(lookup, "U0", "FOLD", "k10_to_random_median_ratio") - TOL,
                    fold_gini < median_scope_metric(lookup, "U0", "FOLD", "neighbour_occurrence_gini") - TOL,
                    fold_dom < median_scope_metric(lookup, "U0", "FOLD", "semantic_group_domination") - TOL,
                )
            )
            eligible = bool(gates and improvement_count >= 2)
        summary[candidate] = {
            "fold_concentration_pass_count": fold_concentration,
            "family_concentration_pass_count": family_concentration,
            "fold_hubness_pass_count": fold_hubness,
            "family_hubness_pass_count": family_hubness,
            "fold_group_domination_pass_count": fold_domination,
            "family_group_domination_pass_count": family_domination,
            "fold_transform_stability_median": fold_stability,
            "family_transform_stability_median": family_stability,
            "median_fold_k10_to_random_median_ratio": fold_k10,
            "median_fold_neighbour_occurrence_gini": fold_gini,
            "median_fold_semantic_group_domination": fold_dom,
            "fold_family_transport_coefficient_of_variation": transport_cv,
            "replication_and_stability_gates_pass": gates,
            "improvement_criterion_count": improvement_count,
            "selection_eligible": eligible,
        }

    passing = [candidate for candidate in NONIDENTITY_CANDIDATES if summary[candidate]["selection_eligible"]]
    rank_fields = (
        "median_fold_k10_to_random_median_ratio",
        "median_fold_neighbour_occurrence_gini",
        "median_fold_semantic_group_domination",
        "fold_family_transport_coefficient_of_variation",
    )
    rank_maps = {
        field: ordinal_ranks(passing, {candidate: float(summary[candidate][field]) for candidate in passing})
        for field in rank_fields
    } if passing else {}
    for candidate in CANDIDATES:
        ranks = [rank_maps[field][candidate] for field in rank_fields] if candidate in passing else []
        summary[candidate]["composite_rank_sum"] = int(sum(ranks)) if ranks else ""
        for field in rank_fields:
            summary[candidate][f"rank__{field}"] = rank_maps.get(field, {}).get(candidate, "")
    selected = min(
        passing,
        key=lambda candidate: (int(summary[candidate]["composite_rank_sum"]), CANDIDATES.index(candidate)),
    ) if passing else None
    status = "TARGET_BLIND_GEOMETRY_CANDIDATE_SELECTED" if selected else "ROUTE_A_TARGET_BLIND_GEOMETRY_CANDIDATE_NOT_ESTABLISHED"
    rows: list[dict[str, Any]] = []
    for candidate in CANDIDATES:
        for scope, identifiers in (
            ("FOLD", [f"FOLD_{fold}" for fold in range(FOLD_COUNT)]),
            ("FAMILY", list(FAMILIES)),
        ):
            for identifier in identifiers:
                value = lookup[(candidate, scope, identifier)]
                reference = lookup[("U0", scope, identifier)]
                concentration_pass = (
                    float(value["k10_to_random_median_ratio"])
                    <= float(reference["k10_to_random_median_ratio"]) * 1.01
                    and float(value["nearest_to_random_median_ratio"])
                    <= float(reference["nearest_to_random_median_ratio"]) * 1.01
                )
                hubness_pass = (
                    float(value["neighbour_occurrence_gini"])
                    <= float(reference["neighbour_occurrence_gini"]) + 0.01
                )
                domination_pass = (
                    float(value["semantic_group_domination"])
                    <= float(reference["semantic_group_domination"]) + 0.01
                )
                rows.append(
                    {
                        "evidence_class": EVIDENCE_CLASS,
                        "record_type": "TARGET_BLIND_SELECTION_STRATUM",
                        "arm": "MS",
                        "candidate_id": candidate,
                        "scope_type": scope,
                        "scope_id": identifier,
                        "k10_to_random_median_ratio": value["k10_to_random_median_ratio"],
                        "u0_k10_to_random_median_ratio": reference["k10_to_random_median_ratio"],
                        "nearest_to_random_median_ratio": value["nearest_to_random_median_ratio"],
                        "u0_nearest_to_random_median_ratio": reference["nearest_to_random_median_ratio"],
                        "neighbour_occurrence_gini": value["neighbour_occurrence_gini"],
                        "u0_neighbour_occurrence_gini": reference["neighbour_occurrence_gini"],
                        "semantic_group_domination": value["semantic_group_domination"],
                        "u0_semantic_group_domination": reference["semantic_group_domination"],
                        "concentration_pass": concentration_pass,
                        "hubness_pass": hubness_pass,
                        "semantic_group_domination_pass": domination_pass,
                        "all_three_stratum_criteria_pass": bool(
                            concentration_pass and hubness_pass and domination_pass
                        ),
                        "target_used_for_selection": False,
                        "diagnostic_only": True,
                    }
                )
    for candidate in CANDIDATES:
        rows.append(
            {
                "evidence_class": EVIDENCE_CLASS,
                "record_type": "TARGET_BLIND_SELECTION_SUMMARY",
                "arm": "MS",
                "candidate_id": candidate,
                "scope_type": "D1_SELECTION",
                "scope_id": "ALL_FOLDS_AND_FAMILIES",
                **summary[candidate],
                "selected": candidate == selected,
                "selection_status": status,
                "concentration_relative_tolerance": 0.01,
                "hubness_absolute_tolerance": 0.01,
                "group_domination_absolute_tolerance": 0.01,
                "minimum_fold_replication": "5/6",
                "minimum_family_replication": "3/4",
                "minimum_transform_similarity": 0.75,
                "minimum_strict_improvement_criteria": "2/3",
                "strict_improvement_tolerance": TOL,
                "deterministic_tie_order": "U1<U2<U3",
                "target_used_for_selection": False,
                "diagnostic_only": True,
            }
        )
    return rows, selected, status


def formal_geometry_rows(
    formal_results: Sequence[Mapping[str, Any]],
    all_metric_rows: Sequence[Mapping[str, Any]],
    data: DataBundle,
    t1_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    formal_keys = {(item["arm"], item["candidate_id"]) for item in formal_results}
    duplicate_lookup = {
        (row["arm"], row["scope_type"], row["scope_id"]): row
        for row in t1_rows if row["spectrum_index"] == 1
    }
    for metric in all_metric_rows:
        if (metric["arm"], metric["candidate_id"]) not in formal_keys:
            continue
        copy = dict(metric)
        copy["record_type"] = "FORMAL_U0_GEOMETRY_SUMMARY"
        t1_scope = {
            "OVERALL": ("OVERALL", "ALL"),
            "FOLD": ("TRAIN_EXCLUDING_FOLD", metric["scope_id"]),
            "FAMILY": ("FAMILY", metric["scope_id"]),
        }[str(metric["scope_type"])]
        source = duplicate_lookup[(metric["arm"], t1_scope[0], t1_scope[1])]
        copy["exact_coordinate_duplicate_burden"] = source["exact_duplicate_burden"]
        copy["exact_coordinate_duplicate_member_count"] = source["exact_duplicate_member_count"]
        copy["formal_metric_modified"] = False
        result.append(copy)
    for formal in formal_results:
        shares = np.asarray(formal["group_share"])
        for scope_type, scope_id, mask in scope_masks(data):
            for group_index, group_id in enumerate(formal["group_ids"]):
                result.append(
                    {
                        "evidence_class": EVIDENCE_CLASS,
                        "record_type": "FORMAL_U0_SEMANTIC_GROUP_DISTANCE_CONTRIBUTION",
                        "arm": formal["arm"],
                        "candidate_id": "U0",
                        "scope_type": scope_type,
                        "scope_id": scope_id,
                        "group_id": group_id,
                        "mean_additive_group_distance_share": float(np.mean(shares[mask, group_index])),
                        "group_contribution_semantics": "TRANSFORM_GROUP_SEPARATELY; CROSS_TERMS_EXCLUDED",
                        "formal_metric_modified": False,
                        "diagnostic_only": True,
                    }
                )
    return result


def write_final_npz(
    selected: str | None,
    u0_ms: Mapping[str, Any],
    results: Mapping[str, Mapping[str, Any]],
    input_hashes: Mapping[str, str],
) -> None:
    arrays: dict[str, np.ndarray] = {
        "query_row_index": np.arange(EXPECTED_ROWS, dtype=np.int32),
        "k": np.asarray(K, dtype=np.int8),
        "evidence_class": np.asarray(EVIDENCE_CLASS),
        "selection_status": np.asarray(
            "TARGET_BLIND_GEOMETRY_CANDIDATE_SELECTED" if selected else "ROUTE_A_TARGET_BLIND_GEOMETRY_CANDIDATE_NOT_ESTABLISHED"
        ),
        "selected_candidate_id": np.asarray(selected or "NONE"),
        "u0_neighbor_row_index": np.asarray(u0_ms["neighbours"], dtype=np.int32),
        "u0_neighbor_distance": np.asarray(u0_ms["distances"], dtype=np.float64),
        "u0_random_comparator_distance": np.asarray(u0_ms["random_distances"], dtype=np.float64),
        "frozen_random_comparator_row_index": np.asarray(results["U0"]["random_rows"], dtype=np.int32),
        "source_identity_digest": np.asarray(canonical_digest(dict(sorted(input_hashes.items())))),
    }
    if selected is not None:
        result = results[selected]
        arrays.update(
            {
                "selected_neighbor_row_index": np.asarray(result["neighbours"], dtype=np.int32),
                "selected_neighbor_distance": np.asarray(result["distances"], dtype=np.float64),
                "selected_random_comparator_distance": np.asarray(result["random_distances"], dtype=np.float64),
            }
        )
    atomic_npz(SELECTED_NEIGHBOURS, **arrays)


def execute() -> None:
    git_state = git_boundary(require_d0_subject=True)
    input_hashes = verify_upstream()
    data = load_and_validate_data()

    t1_rows, subspace_stability, group_energy, spectra = compute_t1(data)
    fold_transforms, transform_stability, transform_parameters = prepare_transforms(data)
    subspace_stability.extend(transform_stability)
    atomic_npz(TRANSFORMS, **transform_parameters)

    u0_ss = frozen_u0_result("SS", data, transforms=None)
    u0_ms = frozen_u0_result("MS", data, transforms=fold_transforms["U0"])
    results: dict[str, dict[str, Any]] = {
        "U0": {**u0_ms, "random_rows": data.random_rows},
    }
    for candidate_id in NONIDENTITY_CANDIDATES:
        results[candidate_id] = assemble_candidate_result(
            candidate_id, fold_transforms[candidate_id], data, input_hashes
        )

    metric_rows: list[dict[str, Any]] = []
    metric_rows.extend(geometry_metrics(u0_ss, data))
    for candidate_id in CANDIDATES:
        metric_rows.extend(geometry_metrics(results[candidate_id], data))

    selection_rows, selected, selection_status = select_candidate(metric_rows, transform_stability)
    turnover: list[dict[str, Any]] = []
    turnover.extend(
        turnover_rows(
            "FORMAL_SS_TO_MS", "SS", "U0", u0_ss["neighbours"],
            "MS", "U0", u0_ms["neighbours"], data,
        )
    )
    for candidate_id in NONIDENTITY_CANDIDATES:
        turnover.extend(
            turnover_rows(
                f"FORMAL_U0_TO_{candidate_id}", "MS", "U0", u0_ms["neighbours"],
                "MS", candidate_id, results[candidate_id]["neighbours"], data,
            )
        )

    formal_rows = formal_geometry_rows((u0_ss, u0_ms), metric_rows, data, t1_rows)
    distance_rows = [dict(row) for row in metric_rows]
    hubness_rows = [
        {
            key: row[key] for key in (
                "evidence_class", "record_type", "arm", "candidate_id", "scope_type", "scope_id",
                "query_count", "k", "hubness_occurrence_skew", "neighbour_occurrence_gini",
                "neighbour_occurrence_maximum", "zero_occurrence_fraction", "diagnostic_only",
            )
        }
        for row in metric_rows
    ]

    atomic_csv(T1_SUBSPACE, t1_rows)
    atomic_csv(T1_STABILITY, subspace_stability)
    atomic_csv(T1_GROUP_ENERGY, group_energy)
    atomic_csv(T2_SELECTION, selection_rows)
    atomic_csv(FORMAL_GEOMETRY, formal_rows)
    atomic_csv(DISTANCE_AUDIT, distance_rows)
    atomic_csv(HUBNESS_AUDIT, hubness_rows)
    atomic_csv(TURNOVER_AUDIT, turnover)
    write_final_npz(selected, u0_ms, results, input_hashes)

    output_paths = (
        T1_SUBSPACE, T1_STABILITY, T1_GROUP_ENERGY, T2_SELECTION, FORMAL_GEOMETRY,
        DISTANCE_AUDIT, HUBNESS_AUDIT, TURNOVER_AUDIT, TRANSFORMS, SELECTED_NEIGHBOURS,
    )
    audit = {
        "schema_version": "1.0.0",
        "stage": "MSO-02D-D1",
        "evidence_class": EVIDENCE_CLASS,
        "status": "MSO02D_D1_TARGET_BLIND_GEOMETRY_COMPUTATION_COMPLETE",
        "selection_status": selection_status,
        "selected_candidate_id": selected or None,
        "observable_row_count": EXPECTED_ROWS,
        "dimensions": EXPECTED_DIMS,
        "fold_count": FOLD_COUNT,
        "family_count": len(FAMILIES),
        "k": K,
        "tie_order": ["distance", "case_id", "particle_id"],
        "exclusions": {
            "same_case": True,
            "same_field_lineage": True,
            "same_nonzero_disorder_seed": True,
            "held_out_fold_training_pool_only": True,
        },
        "library_versions": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "scikit_learn": sklearn.__version__,
        },
        "u3_exact_method": {
            "estimator": "sklearn.covariance.LedoitWolf",
            "parameters": {
                "assume_centered": False,
                "store_precision": False,
                "block_size": 1000,
            },
            "inverse_root_eigenvalue_floor": "maximum_eigenvalue*1e-12",
        },
        "access_counts": {
            "consumed_observable_store_reads": 1,
            "consumed_observable_schema_reads": 2,
            "consumed_observable_registry_reads": 8,
            "consumed_target_payload_reads": 0,
            "outcome_metric_payload_reads": 0,
            "fresh_case_generation": 0,
            "fresh_target_generation": 0,
            "fresh_reference_generation": 0,
            "formal_metric_modification": 0,
            "formal_feature_modification": 0,
            "formal_fold_modification": 0,
            "formal_normalization_modification": 0,
            "neural_model": 0,
            "attention": 0,
            "transformer": 0,
            "optimizer": 0,
            "training": 0,
        },
        "git_at_execution_start": git_state,
        "input_sha256": dict(sorted(input_hashes.items())),
        "output_sha256": {rel(path): sha256(path) for path in output_paths},
    }
    atomic_json(EXECUTION_AUDIT, audit)

    bound_paths = (
        *output_paths,
        EXECUTION_AUDIT,
        D0_CONTRACT,
        FEATURE_REGISTRY,
        CANDIDATE_REGISTRY,
        DIRECTIONAL_PROXY_REGISTRY,
        Path(__file__),
        TARGET_DIAGNOSTICS_EXECUTABLE,
    )
    freeze = {
        "schema_version": "1.0.0",
        "stage": "MSO-02D-D1",
        "evidence_class": EVIDENCE_CLASS,
        "status": selection_status,
        "selected_candidate_id": selected or None,
        "selected_candidate_frozen_before_any_consumed_outcome_diagnostic": True,
        "target_payload_read_count": 0,
        "outcome_metric_payload_read_count": 0,
        "candidate_set": list(CANDIDATES),
        "selection_rule": {
            "concentration_nonworsening": "K10_AND_K1_RANDOM_MEDIAN_RATIOS <= U0*1.01",
            "hubness_nonworsening": "OCCURRENCE_GINI <= U0+0.01",
            "group_domination_nonworsening": "SEMANTIC_GROUP_DOMINATION <= U0+0.01",
            "minimum_replication": "EACH_CRITERION_AT_LEAST_5_OF_6_FOLDS_AND_3_OF_4_FAMILIES",
            "transform_stability": "MEDIAN_CROSS_FOLD_AND_CROSS_FAMILY_SIMILARITY >= 0.75",
            "composite_rank": "SUM_OF_ORDINAL_RANKS_FOR_FOLD_K10_RATIO_GINI_GROUP_DOMINATION_AND_FOLD_FAMILY_TRANSPORT_CV",
            "selection_additional_requirement": "AT_LEAST_2_OF_FIRST_3_MEDIAN_FOLD_CRITERIA_IMPROVE_BEYOND_1E-12",
            "tie_order": "U1<U2<U3",
        },
        "neighbour_artifact": {
            "path": rel(SELECTED_NEIGHBOURS),
            "sha256": sha256(SELECTED_NEIGHBOURS),
            "k": K,
            "no_candidate_semantics": "SELECTED_ARRAYS_ABSENT_AND_SELECTED_CANDIDATE_ID_NONE",
        },
        "transform_parameter_artifact": {
            "path": rel(TRANSFORMS),
            "sha256": sha256(TRANSFORMS),
            "use_in_later_stage": "AUDIT_ONLY; D1 K10 IDENTITIES_AND_DISTANCES_ARE_FROZEN",
        },
        "git_binding": {
            "protocol_commit": PROTOCOL_COMMIT,
            "d0_commit": git_state["head"],
            "d0_required_subject": D0_SUBJECT,
            "d1_commit": "SELF_GIT_COMMIT",
            "d1_required_subject": D1_SUBJECT,
            "branch": "main",
            "remote": None,
            "working_tree_clean_required_after_d1_commit": True,
        },
        "artifact_registry": [
            {
                "path": rel(path),
                "sha256": sha256(path),
                "source": (
                    "FROZEN_D0_TARGET_BLIND_DEFINITION"
                    if path in (
                        D0_CONTRACT,
                        FEATURE_REGISTRY,
                        CANDIDATE_REGISTRY,
                        DIRECTIONAL_PROXY_REGISTRY,
                        Path(__file__),
                        TARGET_DIAGNOSTICS_EXECUTABLE,
                    )
                    else "MSO02D_D1_OBSERVABLE_ONLY_DETERMINISTIC_COMPUTATION"
                ),
                "stage": "MSO-02D-D1",
                "evidence_class": EVIDENCE_CLASS,
                "consumption_status": (
                    "CONSUMED_D0_DEFINITION"
                    if path in (
                        D0_CONTRACT,
                        FEATURE_REGISTRY,
                        CANDIDATE_REGISTRY,
                        DIRECTIONAL_PROXY_REGISTRY,
                        Path(__file__),
                        TARGET_DIAGNOSTICS_EXECUTABLE,
                    )
                    else "FROZEN_FOR_D2_READ_ONLY_CONSUMPTION"
                ),
            }
            for path in bound_paths
        ],
        "artifact_sha256": {rel(path): sha256(path) for path in bound_paths},
        "input_sha256": dict(sorted(input_hashes.items())),
        "formal_ss_ms_matrices_modified": False,
        "fresh_scientific_evidence_generated": False,
        "fresh_compute_authorized": False,
    }
    atomic_json(FREEZE, freeze)
    validate_outputs(post_commit=False)
    print(json.dumps({"status": selection_status, "selected_candidate_id": selected, "freeze_sha256": sha256(FREEZE)}, indent=2))


def validate_outputs(post_commit: bool) -> None:
    verify_upstream()
    load_and_validate_data()
    if not FREEZE.is_file():
        raise IntegrityError("MSO02D_D1_FREEZE_MISSING")
    freeze = read_json(FREEZE)
    if freeze.get("evidence_class") != EVIDENCE_CLASS:
        raise IntegrityError("MSO02D_D1_FREEZE_EVIDENCE_CLASS_CONFLICT")
    if freeze.get("target_payload_read_count") != 0 or freeze.get("outcome_metric_payload_read_count") != 0:
        raise IntegrityError("MSO02D_D1_FREEZE_FIREWALL_CONFLICT")
    for relative, expected in freeze.get("artifact_sha256", {}).items():
        path = ROOT / relative
        if not path.is_file() or sha256(path) != expected:
            raise IntegrityError(f"MSO02D_D1_FROZEN_ARTIFACT_IDENTITY_CONFLICT: {relative}")
    neighbour = freeze.get("neighbour_artifact", {})
    neighbour_path = ROOT / str(neighbour.get("path", ""))
    if not neighbour_path.is_file() or sha256(neighbour_path) != neighbour.get("sha256"):
        raise IntegrityError("MSO02D_D1_NEIGHBOUR_FREEZE_CONFLICT")
    with np.load(neighbour_path, allow_pickle=False) as arrays:
        if not np.array_equal(arrays["query_row_index"], np.arange(EXPECTED_ROWS, dtype=np.int32)):
            raise IntegrityError("MSO02D_D1_NEIGHBOUR_QUERY_IDENTITY_CONFLICT")
        selected = str(arrays["selected_candidate_id"].item())
        if freeze.get("selected_candidate_id") is None:
            forbidden = {
                "selected_neighbor_row_index", "selected_neighbor_distance", "selected_random_comparator_distance"
            }
            if selected != "NONE" or forbidden.intersection(arrays.files):
                raise IntegrityError("MSO02D_D1_NO_CANDIDATE_ARRAY_SEMANTICS_CONFLICT")
        else:
            required = {
                "selected_neighbor_row_index", "selected_neighbor_distance", "selected_random_comparator_distance"
            }
            if selected != freeze["selected_candidate_id"] or not required.issubset(arrays.files):
                raise IntegrityError("MSO02D_D1_SELECTED_CANDIDATE_ARRAY_SEMANTICS_CONFLICT")
    if post_commit:
        state = git_boundary(require_d0_subject=False)
        if state["subject"] != D1_SUBJECT:
            raise IntegrityError("MSO02D_D1_POST_COMMIT_SUBJECT_CONFLICT")
        if str(git("status", "--porcelain=v1", "--untracked-files=all")):
            raise IntegrityError("MSO02D_D1_POST_COMMIT_WORKTREE_NOT_CLEAN")
        tracked = str(git("ls-tree", "-r", "--name-only", "HEAD", rel(FREEZE))).splitlines()
        if rel(FREEZE) not in tracked:
            raise IntegrityError("MSO02D_D1_FREEZE_NOT_TRACKED_AT_SELF_COMMIT")
    print(json.dumps({"status": "MSO02D_D1_TARGET_BLIND_FREEZE_VALID", "post_commit": post_commit}, indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("run", help="execute observable-only T1/T2 and freeze the D1 selection")
    validate = subparsers.add_parser("validate", help="validate upstream and frozen D1 artifact identities")
    validate.add_argument("--post-commit", action="store_true", help="also require the exact frozen D1 commit boundary")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        if args.command == "run":
            execute()
        else:
            validate_outputs(post_commit=bool(args.post_commit))
    except IntegrityError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
