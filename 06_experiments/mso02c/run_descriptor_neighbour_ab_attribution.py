#!/usr/bin/env python3
"""Reconstruct frozen K10 descriptor neighbours for MSO-02C G1 A/B attribution.

The observable loader is intentionally key-restricted to `ss_features` and
`ms_features`.  The target loader is key-restricted to the three primary target
arrays.  Only the 246 already frozen arm/component zero-denominator records are
classified; no complete DNN metric, candidate metric, bootstrap, or verdict is
computed.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import csv
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import sys
from typing import Any
import zipfile

import numpy as np
import scipy


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "06_experiments/mso02c"
AUTHORIZATION = ROOT / "00_project_contract/mso02c_g1_descriptor_neighbour_reconstruction_authorization.md"
EXECUTION_FREEZE = ROOT / "08_manifests/mso02c_g1_descriptor_reconstruction_execution_freeze.json"
FINALIZER = ROOT / "06_experiments/mso02c/finalize_mso02c_g1_ab_attribution.py"
OBSERVABLE = ROOT / "06_experiments/mso02a/observable/mso02a_observable_store.npz"
TARGET = ROOT / "06_experiments/mso02b/target_ref/mso02b_target_store.npz"
FORMAL = ROOT / "05_registries/mso02a_formal_fresh_atlas_registry.json"
SAMPLE = ROOT / "05_registries/mso02b_formal_particle_sample_registry.json"
NORMALIZATION = ROOT / "06_experiments/mso02a/fold_normalization_registry.json"
RUNNER = ROOT / "06_experiments/mso02b/run_mso02b_formal.py"
ZERO_MAP = OUT / "zero_denominator_particle_map.csv"

NEIGHBOURS = OUT / "descriptor_neighbour_identity_reconstruction.csv"
AB_ATTRIBUTION = OUT / "zero_denominator_ab_attribution.csv"
COMPONENT_SUMMARY = OUT / "ab_attribution_component_summary.csv"
FAMILY_FOLD_SUMMARY = OUT / "ab_attribution_family_fold_summary.csv"
MECHANISM_AFTER_AB = OUT / "degeneracy_mechanism_audit_after_ab.csv"
ACCESS_AUDIT = OUT / "descriptor_reconstruction_access_audit.json"
FAILURE_ACCESS_AUDIT = OUT / "descriptor_reconstruction_failure_access_audit.json"
EVENT_JOURNAL = OUT / "descriptor_reconstruction_execution_events.jsonl"
STAGING_ROOT = OUT / ".descriptor_reconstruction_staging"

EXECUTION_OUTPUTS = (
    NEIGHBOURS,
    AB_ATTRIBUTION,
    COMPONENT_SUMMARY,
    FAMILY_FOLD_SUMMARY,
    MECHANISM_AFTER_AB,
    ACCESS_AUDIT,
)

ARMS = ("SS", "MS")
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
FEATURE_FIELDS = {"SS": "ss_features", "MS": "ms_features"}
FEATURE_DIMENSIONS = {"SS": 39, "MS": 110}
FAMILIES = ("F1", "F2", "F3", "F4")
FOLDS = tuple(range(6))
PRIMARY_K = 10
INTERNAL_REQUIRED_K = 20
EXPECTED_BY_COMPONENT = {
    "density_rate": 2,
    "pressure_gradient_acceleration": 119,
    "viscosity_laplacian_acceleration": 2,
}
EXPECTED_CASES_BY_COMPONENT = {
    "density_rate": 2,
    "pressure_gradient_acceleration": 87,
    "viscosity_laplacian_acceleration": 2,
}

AUTHORIZATION_COMMIT = "c76026f5aac782718f83fc4369811eaeeec194a9"
OBSERVABLE_SHA256 = "3dfedfa666c32e4e578f1821f441370da288fd636fc977d2fb15bf470654102e"
TARGET_SHA256 = "16f1ebd26d0d1aa74dd0892dfe2feb0967024f9219dd8c102c8faafc934f81e2"

STATIC_HASHES = {
    "00_project_contract/mso02c_dnn_degeneracy_diagnostic_contract.md":
        "781618a8cf52f05bded1b3af99b897815df78c1eefcde3c70d32ae60ac92753f",
    "00_project_contract/mso02c_g1_descriptor_neighbour_reconstruction_authorization.md":
        "4da29a3d73b675ef2be98d1195aea0566d8b5cc86b3d1b6d1b945ccb85c8c3a1",
    "06_experiments/mso02a/ss_observable_schema.json":
        "b2237506cac4bbc67dfda981f15daea47c32535259d394b962263a82190e2ec4",
    "06_experiments/mso02a/ms_observable_schema.json":
        "51ff5e04dde4b862f3cab19c80e2aea93c151006fe7b3f497001e43475ec18cb",
    "06_experiments/mso02a/fold_normalization_registry.json":
        "f8fb9ccde826ece14690ab255955ecb7b922bc5cd27ddb9b0544b9fd9c9bd634",
    "05_registries/mso02a_formal_fresh_atlas_registry.json":
        "9893cf48d73be3316a66bb7b9c7f71db8c122247ce56b67d1b0f685605b761c6",
    "05_registries/mso02a_lineage_fold_registry.json":
        "b163a6b3e70cde47e033d204d74b997fd218596885a4b96287dc160a948c42ff",
    "05_registries/mso02b_formal_particle_sample_registry.json":
        "98ff5716e3adbbaac4cac4899e76eb4d61d4e194396fe4e37041a94abe0ca229",
    "05_registries/mso02b_analysis_semantics_registry.json":
        "b271864a62800ea502d1f21621b3d937088f6809c0d31301e6effac96d203ce5",
    "06_experiments/mso02b/run_mso02b_formal.py":
        "55b0b63eb2c99364c8a2e96c75191a50707e93357f7039bd9edfdcb7c7c831b7",
    "06_experiments/mso02c/zero_denominator_particle_map.csv":
        "803e5234f113373aa134c97b809cfeb807dad6bbe6c4c2346bfc393a1c46d893",
    "06_experiments/mso02c/zero_denominator_case_map.csv":
        "e8aa8855e91132809cbc7515d952c0295ad2cb1076b8a8dfa42eb1bcfad27aef",
    "06_experiments/mso02c/zero_denominator_family_fold_summary.csv":
        "72a0f04caf740c1f8a089e7e955c8b35c0d433db62480b77aa5e9b76a5a36ba1",
    "06_experiments/mso02c/degeneracy_mechanism_audit.csv":
        "52a81467c9df26993a00a8b6d70fd4c6339d85735bb14854ce8f13c62e77abb4",
    "06_experiments/mso02c/attribution_execution_audit.json":
        "40d69d0653be28083ce19fd3da2c50c83415b9e5ded0cb8235dfd0e6c09ae274",
    "06_experiments/mso02c/run_zero_denominator_attribution.py":
        "ae839d31826d33914d79c9f4504d103810653047fae7df2ca1b35ce741f29811",
    "08_manifests/mso02b_manifest.json":
        "94ce69002d714acff2176fc71910e18766f873ed26be7437763eb34762e68fe6",
    "08_manifests/mso02b_status_ledger.json":
        "cb9864b34c94f4ae022745fa9b6040bd2baaf6bdae7156a3905b22584a268815",
    "08_manifests/mso02c_g1_attribution_execution_freeze.json":
        "7813a4ab60b6e7f01108c4ff36159984a638e8e7b0b9d1e58645b453425fd756",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


def domain_hash(domain: str, payload: bytes) -> str:
    digest = hashlib.sha256()
    digest.update(domain.encode("utf-8"))
    digest.update(b"\x00")
    digest.update(payload)
    return digest.hexdigest()


def float_array_hash(domain: str, values: np.ndarray) -> str:
    array = np.ascontiguousarray(np.asarray(values, dtype="<f8"))
    header = canonical_json({"shape": list(array.shape), "dtype": "<f8"})
    return domain_hash(domain, header + b"\x00" + array.tobytes())


def int_array_hash(domain: str, values: np.ndarray) -> str:
    array = np.ascontiguousarray(np.asarray(values, dtype="<i8"))
    header = canonical_json({"shape": list(array.shape), "dtype": "<i8"})
    return domain_hash(domain, header + b"\x00" + array.tobytes())


def write_csv_atomic(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = list(rows[0]) if rows else ["status"]
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def publish_staged(staging: Path, outputs: tuple[Path, ...]) -> None:
    missing = [path.name for path in outputs if not (staging / path.name).exists()]
    if missing:
        raise RuntimeError("incomplete descriptor staging:" + ",".join(missing))
    for path in outputs:
        staged = staging / path.name
        if path.exists():
            if sha256(path) != sha256(staged):
                raise RuntimeError(f"conflicting partial descriptor output {path}")
            continue
        os.link(staged, path)
    for path in outputs:
        staged = staging / path.name
        if staged.exists():
            staged.unlink()
    if staging.exists():
        staging.rmdir()
    if STAGING_ROOT.exists() and not any(STAGING_ROOT.iterdir()):
        STAGING_ROOT.rmdir()


def write_failure_access_audit(
    *,
    execution_head: str | None,
    access_counts: dict[str, int],
    error: BaseException,
) -> None:
    payload = {
        "schema_version": "1.0.0",
        "stage": "MSO-02C_G1_DESCRIPTOR_NEIGHBOUR_RECONSTRUCTION",
        "status": "MSO02C_G1_EXECUTION_FAILED_AFTER_AUTHORIZATION",
        "execution_head": execution_head,
        "error_type": type(error).__name__,
        "error": str(error),
        "access_counts_at_failure": access_counts,
        "candidate_metric_performance_count": 0,
        "metric_selection_count": 0,
        "new_h3_verdict_count": 0,
    }
    if FAILURE_ACCESS_AUDIT.exists():
        existing = json.loads(FAILURE_ACCESS_AUDIT.read_text(encoding="utf-8"))
        existing.setdefault("attempts", []).append(payload)
        write_json_atomic(FAILURE_ACCESS_AUDIT, existing)
    else:
        write_json_atomic(FAILURE_ACCESS_AUDIT, {"attempts": [payload]})


def append_event(
    event: str,
    access_counts: dict[str, int],
    **details: Any,
) -> None:
    record = {
        "event": event,
        "access_counts": dict(access_counts),
        **details,
    }
    with EVENT_JOURNAL.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True, allow_nan=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def new_access_counts() -> dict[str, int]:
    return {
        "observable_store_hash_reads": 0,
        "observable_store_hash_reads_completed": 0,
        "observable_store_opaque_hash_reads": 0,
        "observable_archive_metadata_reads": 0,
        "observable_archive_metadata_reads_completed": 0,
        "observable_payload_store_open_sessions": 0,
        "observable_store_payload_reads": 0,
        "observable_payload_array_reads": 0,
        "ss_features_reads": 0,
        "ms_features_reads": 0,
        "other_observable_payload_key_reads": 0,
        "target_store_hash_reads": 0,
        "target_store_hash_reads_completed": 0,
        "target_store_opaque_hash_reads": 0,
        "target_archive_metadata_reads": 0,
        "target_archive_metadata_reads_completed": 0,
        "target_payload_store_open_sessions": 0,
        "target_store_payload_reads": 0,
        "target_payload_array_reads": 0,
        "target_density_rate_reads": 0,
        "target_pressure_gradient_acceleration_reads": 0,
        "target_viscosity_laplacian_acceleration_reads": 0,
        "other_target_payload_key_reads": 0,
        "checkpoint_opaque_hash_reads": 0,
        "checkpoint_payload_reads": 0,
        "metric_payload_reads": 0,
        "bootstrap_payload_reads": 0,
        "descriptor_nn_required_k20_search_attempts": 0,
        "descriptor_nn_required_k20_searches_completed": 0,
        "descriptor_nn_required_k20_repeat_attempts": 0,
        "descriptor_nn_required_k20_repeats_completed": 0,
        "query_target_row_consumptions": 0,
        "selected_k10_neighbour_target_row_consumptions": 0,
        "descriptor_nn_numerator_attempts": 0,
        "descriptor_nn_numerator_completed": 0,
    }


def git_identity_gate() -> str:
    branch = subprocess.run(
        ["git", "branch", "--show-current"], cwd=ROOT, check=True,
        capture_output=True, text=True,
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, check=True,
        capture_output=True, text=True,
    ).stdout.strip()
    remotes = subprocess.run(
        ["git", "remote"], cwd=ROOT, check=True,
        capture_output=True, text=True,
    ).stdout.split()
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
        capture_output=True, text=True,
    ).stdout.strip()
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", AUTHORIZATION_COMMIT, head],
        cwd=ROOT,
    )
    if branch != "main" or status or remotes or ancestor.returncode != 0:
        raise RuntimeError("MSO02C_G1_GIT_HANDOFF_CONFLICT")
    committed_auth = subprocess.run(
        ["git", "show", f"HEAD:{AUTHORIZATION.relative_to(ROOT)}"],
        cwd=ROOT, check=True, capture_output=True,
    ).stdout
    if hashlib.sha256(committed_auth).hexdigest() != sha256(AUTHORIZATION):
        raise RuntimeError("MSO02C_G1_AUTHORIZATION_COMMIT_IDENTITY_FAILURE")
    for path in (Path(__file__).resolve(), EXECUTION_FREEZE, FINALIZER):
        relative = path.relative_to(ROOT)
        committed = subprocess.run(
            ["git", "show", f"HEAD:{relative}"], cwd=ROOT, check=True,
            capture_output=True,
        ).stdout
        if hashlib.sha256(committed).hexdigest() != sha256(path):
            raise RuntimeError(f"MSO02C_G1_EXECUTION_COMMIT_IDENTITY_FAILURE:{relative}")
    return head


def frozen_identity_gate() -> dict[str, str]:
    actual = {}
    mismatches = []
    for relative, expected in STATIC_HASHES.items():
        value = sha256(ROOT / relative)
        actual[relative] = value
        if value != expected:
            mismatches.append(f"{relative}:{value}!={expected}")
    freeze = json.loads(EXECUTION_FREEZE.read_text(encoding="utf-8"))
    executable = str(Path(__file__).resolve().relative_to(ROOT))
    executable_hash = sha256(Path(__file__).resolve())
    if freeze.get("executable_path") != executable or freeze.get("executable_sha256") != executable_hash:
        mismatches.append("descriptor reconstruction executable identity")
    finalizer = str(FINALIZER.relative_to(ROOT))
    if (
        freeze.get("finalizer_path") != finalizer
        or not FINALIZER.is_file()
        or freeze.get("finalizer_sha256") != sha256(FINALIZER)
    ):
        mismatches.append("G1 finalizer identity")
    if mismatches:
        raise RuntimeError(
            "MSO02C_UPSTREAM_EVIDENCE_INTEGRITY_CONFLICT:" + ";".join(mismatches)
        )
    return actual


def runtime_identity_gate() -> dict[str, str]:
    freeze = json.loads(EXECUTION_FREEZE.read_text(encoding="utf-8"))
    expected = freeze["runtime_freeze"]
    actual = {
        "python_implementation": platform.python_implementation(),
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "machine": platform.machine(),
        "byteorder": sys.byteorder,
        "float64_itemsize": np.dtype(np.float64).itemsize,
        "float64_ieee_binary64": bool(
            np.finfo(np.float64).bits == 64
            and np.finfo(np.float64).nmant == 52
            and np.finfo(np.float64).iexp == 11
        ),
    }
    mismatches = [
        f"{key}:{actual[key]}!={expected[key]}"
        for key in actual if actual[key] != expected[key]
    ]
    if mismatches:
        raise RuntimeError(
            "MSO02C_G1_FROZEN_REPRESENTATION_IDENTITY_FAILURE:runtime:"
            + ";".join(mismatches)
        )
    return actual


def counted_store_hash(
    path: Path, access_counts: dict[str, int], store_name: str
) -> str:
    access_counts[f"{store_name}_store_hash_reads"] += 1
    access_counts[f"{store_name}_store_opaque_hash_reads"] += 1
    append_event(f"{store_name.upper()}_STORE_HASH_ATTEMPTED", access_counts)
    value = sha256(path)
    access_counts[f"{store_name}_store_hash_reads_completed"] += 1
    append_event(f"{store_name.upper()}_STORE_HASH_COMPLETED", access_counts)
    return value


def archive_metadata(
    path: Path, access_counts: dict[str, int], store_name: str
) -> list[str]:
    access_counts[f"{store_name}_archive_metadata_reads"] += 1
    append_event(f"{store_name.upper()}_ARCHIVE_METADATA_ATTEMPTED", access_counts)
    with zipfile.ZipFile(path, "r") as archive:
        members = sorted(info.filename for info in archive.infolist())
    access_counts[f"{store_name}_archive_metadata_reads_completed"] += 1
    append_event(f"{store_name.upper()}_ARCHIVE_METADATA_COMPLETED", access_counts)
    return members


def import_authoritative_runner() -> Any:
    spec = importlib.util.spec_from_file_location("mso02b_frozen_runner", RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot import frozen runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_sampled_metadata(
    cases: list[dict[str, Any]], sample_payload: dict[str, Any]
) -> dict[str, np.ndarray]:
    sample_by_case = {
        int(row["formal_case_index"]): row for row in sample_payload["cases"]
    }
    values: dict[str, list[Any]] = defaultdict(list)
    for case_index, case in enumerate(cases):
        if int(case["formal_case_index"]) != case_index:
            raise RuntimeError("formal case order mismatch")
        registered = sample_by_case[case_index]
        particle_ids = [int(value) for value in registered["particle_ids_in_hash_order"]]
        if len(particle_ids) != 128 or len(set(particle_ids)) != 128:
            raise RuntimeError(f"sample registry failure case={case_index}")
        for sample_rank, particle_id in enumerate(particle_ids):
            values["full_row"].append(case_index * 576 + particle_id)
            values["case_index"].append(case_index)
            values["particle_id"].append(particle_id)
            values["sample_rank"].append(sample_rank)
            values["case_id"].append(case["case_id"])
            values["lineage"].append(case["field_lineage_id"])
            values["family"].append(case["macro_family"])
            values["fold"].append(int(case["fold"].split("_")[1]))
            values["seed"].append(int(case["jitter_seed"]))
            values["sample_key"].append(f"{case['case_id']}|{particle_id}")
    return {
        "full_row": np.asarray(values["full_row"], dtype=np.int64),
        "case_index": np.asarray(values["case_index"], dtype=np.int16),
        "particle_id": np.asarray(values["particle_id"], dtype=np.int16),
        "sample_rank": np.asarray(values["sample_rank"], dtype=np.int16),
        "case_id": np.asarray(values["case_id"]),
        "lineage": np.asarray(values["lineage"]),
        "family": np.asarray(values["family"]),
        "fold": np.asarray(values["fold"], dtype=np.int8),
        "seed": np.asarray(values["seed"], dtype=np.int64),
        "sample_key": np.asarray(values["sample_key"]),
    }


def read_zero_map(meta: dict[str, np.ndarray]) -> list[dict[str, Any]]:
    with ZERO_MAP.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 246:
        raise RuntimeError(f"zero map row count {len(rows)} != 246")
    sample_lookup = {
        (str(meta["case_id"][index]), int(meta["particle_id"][index])): index
        for index in range(meta["case_id"].size)
    }
    seen = set()
    for row in rows:
        key = (
            row["arm"], row["component"], row["case_id"], int(row["particle_id"])
        )
        if key in seen:
            raise RuntimeError(f"duplicate zero map key {key}")
        seen.add(key)
        if row["arm"] not in ARMS or row["component"] not in COMPONENTS:
            raise RuntimeError(f"unexpected zero-map arm/component {key}")
        if float(row["matched_random_denominator"]) != 0.0:
            raise RuntimeError(f"nonzero frozen denominator {key}")
        if (
            row.get("classification_D_random_targets_numeric_exact_identical") != "True"
            or row.get("classification_F_raw_float64_denominator_exact_zero") != "True"
            or row.get("raw_store_target_bitwise_identity") != "True"
        ):
            raise RuntimeError(f"frozen exact-target multiplicity identity failure {key}")
        sample_key = (row["case_id"], int(row["particle_id"]))
        if sample_key not in sample_lookup:
            raise RuntimeError(f"zero query missing from frozen sample {sample_key}")
        index = int(sample_lookup[sample_key])
        if index != int(row["sample_global_index"]):
            raise RuntimeError(f"sample-global identity mismatch {key}")
        if (
            int(meta["case_index"][index]) != int(row["formal_case_index"])
            or f"FOLD_{int(meta['fold'][index])}" != row["fold"]
            or str(meta["family"][index]) != row["family"]
            or str(meta["lineage"][index]) != row["field_lineage_id"]
        ):
            raise RuntimeError(f"zero query metadata mismatch {key}")
        row["query_sample_global_index"] = index
    for arm in ARMS:
        for component, expected in EXPECTED_BY_COMPONENT.items():
            count = sum(
                row["arm"] == arm and row["component"] == component for row in rows
            )
            if count != expected:
                raise RuntimeError(f"zero count mismatch {arm} {component}: {count}")
    for component in COMPONENTS:
        ss = {
            (row["case_id"], int(row["particle_id"]))
            for row in rows if row["arm"] == "SS" and row["component"] == component
        }
        ms = {
            (row["case_id"], int(row["particle_id"]))
            for row in rows if row["arm"] == "MS" and row["component"] == component
        }
        if ss != ms:
            raise RuntimeError(f"SS/MS query zero sets not colocated {component}")
        expected_cases = EXPECTED_CASES_BY_COMPONENT[component]
        if len({case_id for case_id, _ in ss}) != expected_cases:
            raise RuntimeError(f"affected case count mismatch {component}")
    return rows


def load_authorized_payloads(access_counts: dict[str, int]) -> tuple[
    dict[str, np.ndarray], dict[str, np.ndarray], list[str], list[str]
]:
    observable_members = archive_metadata(OBSERVABLE, access_counts, "observable")
    target_members = archive_metadata(TARGET, access_counts, "target")
    for key in FEATURE_FIELDS.values():
        if f"{key}.npy" not in observable_members:
            raise RuntimeError(f"observable key missing {key}")
    for key in TARGET_FIELDS.values():
        if f"{key}.npy" not in target_members:
            raise RuntimeError(f"target key missing {key}")

    features: dict[str, np.ndarray] = {}
    access_counts["observable_payload_store_open_sessions"] += 1
    append_event("OBSERVABLE_PAYLOAD_SESSION_OPENED", access_counts)
    with np.load(OBSERVABLE, allow_pickle=False) as store:
        # Exactly two payload-array reads; do not enumerate or index other keys.
        access_counts["observable_store_payload_reads"] += 1
        access_counts["observable_payload_array_reads"] += 1
        access_counts["ss_features_reads"] += 1
        append_event("SS_FEATURES_READ_ATTEMPTED", access_counts)
        ss_features = store["ss_features"]
        append_event("SS_FEATURES_READ_COMPLETED", access_counts)
        access_counts["observable_store_payload_reads"] += 1
        access_counts["observable_payload_array_reads"] += 1
        access_counts["ms_features_reads"] += 1
        append_event("MS_FEATURES_READ_ATTEMPTED", access_counts)
        ms_features = store["ms_features"]
        append_event("MS_FEATURES_READ_COMPLETED", access_counts)
        if ss_features.dtype != np.float64 or ms_features.dtype != np.float64:
            raise RuntimeError("MSO02C_G1_FROZEN_REPRESENTATION_IDENTITY_FAILURE")
        features["SS"] = np.asarray(ss_features)
        features["MS"] = np.asarray(ms_features)
    targets: dict[str, np.ndarray] = {}
    access_counts["target_payload_store_open_sessions"] += 1
    append_event("TARGET_PAYLOAD_SESSION_OPENED", access_counts)
    with np.load(TARGET, allow_pickle=False) as store:
        # Exactly three payload-array reads; no identity or uncertainty arrays.
        access_counts["target_store_payload_reads"] += 1
        access_counts["target_payload_array_reads"] += 1
        access_counts["target_density_rate_reads"] += 1
        append_event("TARGET_DENSITY_RATE_READ_ATTEMPTED", access_counts)
        density = store["target_density_rate"]
        append_event("TARGET_DENSITY_RATE_READ_COMPLETED", access_counts)
        access_counts["target_store_payload_reads"] += 1
        access_counts["target_payload_array_reads"] += 1
        access_counts["target_pressure_gradient_acceleration_reads"] += 1
        append_event("TARGET_PRESSURE_READ_ATTEMPTED", access_counts)
        pressure = store["target_pressure_gradient_acceleration"]
        append_event("TARGET_PRESSURE_READ_COMPLETED", access_counts)
        access_counts["target_store_payload_reads"] += 1
        access_counts["target_payload_array_reads"] += 1
        access_counts["target_viscosity_laplacian_acceleration_reads"] += 1
        append_event("TARGET_VISCOSITY_READ_ATTEMPTED", access_counts)
        viscosity = store["target_viscosity_laplacian_acceleration"]
        append_event("TARGET_VISCOSITY_READ_COMPLETED", access_counts)
        if any(value.dtype != np.float64 for value in (density, pressure, viscosity)):
            raise RuntimeError("target dtype identity failure")
        targets["density_rate"] = np.asarray(density)
        targets["pressure_gradient_acceleration"] = np.asarray(pressure)
        targets["viscosity_laplacian_acceleration"] = np.asarray(viscosity)
    return features, targets, observable_members, target_members


def exact_numerator(
    component: str, query_target: np.ndarray, neighbour_targets: np.ndarray
) -> float:
    query = np.asarray(query_target, dtype=np.float64)
    neighbours = np.asarray(neighbour_targets, dtype=np.float64)
    if not np.isfinite(query).all() or not np.isfinite(neighbours).all():
        raise RuntimeError(f"nonfinite selected target value {component}")
    if neighbours.shape[0] != PRIMARY_K:
        raise RuntimeError(f"selected descriptor neighbour count != {PRIMARY_K}")
    if component == "density_rate":
        difference = neighbours - query
        result = float(np.mean(difference ** 2, axis=0))
    else:
        difference = neighbours - query[None, :]
        result = float(np.mean(np.sum(difference * difference, axis=-1), axis=0))
    if not math.isfinite(result) or result < 0.0:
        raise RuntimeError(f"invalid descriptor numerator {component}: {result}")
    return result


def execute(access_counts: dict[str, int]) -> None:
    freeze_sha = sha256(EXECUTION_FREEZE)
    staging = STAGING_ROOT / freeze_sha
    execution_head = git_identity_gate()
    static_actual = frozen_identity_gate()
    runtime_actual = runtime_identity_gate()
    runner = import_authoritative_runner()
    formal_payload = json.loads(FORMAL.read_text(encoding="utf-8"))
    sample_payload = json.loads(SAMPLE.read_text(encoding="utf-8"))
    normalization = json.loads(NORMALIZATION.read_text(encoding="utf-8"))
    cases = sorted(
        formal_payload["cases"], key=lambda row: int(row["formal_case_index"])
    )
    if len(cases) != 384 or int(sample_payload["case_count"]) != 384:
        raise RuntimeError("MSO02C_G1_FROZEN_REPRESENTATION_IDENTITY_FAILURE")
    meta = build_sampled_metadata(cases, sample_payload)
    zero_rows = read_zero_map(meta)
    for arm in ARMS:
        fold_rows = normalization["arms"][arm]["folds"]
        if len(fold_rows) != 6:
            raise RuntimeError("MSO02C_G1_FROZEN_REPRESENTATION_IDENTITY_FAILURE")
        for outer in FOLDS:
            matches = [
                row for row in fold_rows if row["held_out_fold"] == f"FOLD_{outer}"
            ]
            if len(matches) != 1:
                raise RuntimeError("MSO02C_G1_FROZEN_REPRESENTATION_IDENTITY_FAILURE")
            median = np.asarray(matches[0]["median"], dtype=np.float64)
            divisor = np.asarray(matches[0]["divisor"], dtype=np.float64)
            if (
                median.shape != (FEATURE_DIMENSIONS[arm],)
                or divisor.shape != (FEATURE_DIMENSIONS[arm],)
                or not np.isfinite(median).all()
                or not np.isfinite(divisor).all()
                or np.any(divisor <= 0.0)
            ):
                raise RuntimeError("MSO02C_G1_FROZEN_REPRESENTATION_IDENTITY_FAILURE")
    staging.mkdir(parents=True, exist_ok=False)
    append_event(
        "ATTEMPT_STARTED",
        access_counts,
        execution_head=execution_head,
        execution_freeze_sha256=freeze_sha,
    )

    # These are the first authorized opaque reads of the observable in MSO-02C G1.
    observable_hash_before = counted_store_hash(OBSERVABLE, access_counts, "observable")
    target_hash_before = counted_store_hash(TARGET, access_counts, "target")
    if observable_hash_before != OBSERVABLE_SHA256:
        raise RuntimeError("MSO02C_UPSTREAM_EVIDENCE_INTEGRITY_CONFLICT:observable hash")
    if target_hash_before != TARGET_SHA256:
        raise RuntimeError("MSO02C_UPSTREAM_EVIDENCE_INTEGRITY_CONFLICT:target hash")

    append_event("AUTHORIZED_PAYLOAD_LOAD_ATTEMPTED", access_counts)
    features_full, targets, observable_members, target_members = load_authorized_payloads(
        access_counts
    )
    append_event("AUTHORIZED_PAYLOAD_LOAD_COMPLETED", access_counts)

    required_rows = 384 * 576
    for arm in ARMS:
        if features_full[arm].shape != (required_rows, FEATURE_DIMENSIONS[arm]):
            raise RuntimeError("MSO02C_G1_FROZEN_REPRESENTATION_IDENTITY_FAILURE")
        if features_full[arm].dtype != np.float64:
            raise RuntimeError("MSO02C_G1_FROZEN_REPRESENTATION_IDENTITY_FAILURE")
    if targets["density_rate"].shape != (required_rows,):
        raise RuntimeError("target scalar shape mismatch")
    for component in COMPONENTS[1:]:
        if targets[component].shape != (required_rows, 2):
            raise RuntimeError(f"target vector shape mismatch {component}")
    if not all(value.dtype == np.float64 for value in targets.values()):
        raise RuntimeError("target dtype failure")

    sampled_features = {
        arm: np.asarray(features_full[arm][meta["full_row"]], dtype=np.float64)
        for arm in ARMS
    }
    if not all(np.isfinite(values).all() for values in sampled_features.values()):
        raise RuntimeError("MSO02C_G1_FROZEN_REPRESENTATION_IDENTITY_FAILURE")
    del features_full

    reconstruction: dict[tuple[str, int], dict[str, Any]] = {}
    search_invocations = 0
    deterministic_repeat_invocations = 0
    for arm in ARMS:
        for outer in FOLDS:
            fold_query = sorted(
                {
                    int(row["query_sample_global_index"])
                    for row in zero_rows
                    if row["arm"] == arm and row["fold"] == f"FOLD_{outer}"
                }
            )
            if not fold_query:
                continue
            fold_record = next(
                row for row in normalization["arms"][arm]["folds"]
                if row["held_out_fold"] == f"FOLD_{outer}"
            )
            median = np.asarray(fold_record["median"], dtype=np.float64)
            divisor = np.asarray(fold_record["divisor"], dtype=np.float64)
            if (
                median.shape != (FEATURE_DIMENSIONS[arm],)
                or divisor.shape != (FEATURE_DIMENSIONS[arm],)
                or np.any(divisor <= 0.0)
            ):
                raise RuntimeError("MSO02C_G1_FROZEN_REPRESENTATION_IDENTITY_FAILURE")
            x_scaled = (sampled_features[arm] - median) / divisor
            if not np.isfinite(x_scaled).all():
                raise RuntimeError("nonfinite frozen normalization result")

            train_global = runner.ordered_training_indices(
                np.flatnonzero(meta["fold"] != outer), meta
            )
            query_global = np.asarray(fold_query, dtype=np.int64)
            train_meta = runner.subset_meta(meta, train_global)
            query_meta = runner.subset_meta(meta, query_global)
            access_counts["descriptor_nn_required_k20_search_attempts"] += 1
            distances20, neighbours20 = runner.exact_permitted_neighbors(
                x_scaled[train_global], x_scaled[query_global],
                train_meta, query_meta, required_k=INTERNAL_REQUIRED_K,
            )
            access_counts["descriptor_nn_required_k20_searches_completed"] += 1
            search_invocations += 1
            access_counts["descriptor_nn_required_k20_repeat_attempts"] += 1
            repeat_distance, repeat_neighbour = runner.exact_permitted_neighbors(
                x_scaled[train_global], x_scaled[query_global],
                train_meta, query_meta, required_k=INTERNAL_REQUIRED_K,
            )
            access_counts["descriptor_nn_required_k20_repeats_completed"] += 1
            deterministic_repeat_invocations += 1
            if not (
                np.array_equal(distances20, repeat_distance)
                and np.array_equal(neighbours20, repeat_neighbour)
            ):
                raise RuntimeError("MSO02C_G1_DESCRIPTOR_NEIGHBOUR_RECONSTRUCTION_NOT_UNIQUE")

            training_hash = int_array_hash(
                f"MSO02C|ORDERED_TRAIN_POOL|FOLD_{outer}", train_global
            )
            for local, query_index in enumerate(query_global):
                nn_local = np.asarray(neighbours20[local, :PRIMARY_K], dtype=np.int64)
                nn_global = np.asarray(train_global[nn_local], dtype=np.int64)
                nn_distance = np.asarray(distances20[local, :PRIMARY_K], dtype=np.float64)
                if nn_global.shape != (PRIMARY_K,) or nn_distance.shape != (PRIMARY_K,):
                    raise RuntimeError("MSO02C_G1_AB_ATTRIBUTION_INCOMPLETE:K10")
                identity_payload = [
                    {
                        "rank": rank + 1,
                        "sample_global_index": int(global_index),
                        "full_store_row": int(meta["full_row"][global_index]),
                        "case_id": str(meta["case_id"][global_index]),
                        "particle_id": int(meta["particle_id"][global_index]),
                    }
                    for rank, global_index in enumerate(nn_global)
                ]
                neighbour_hash = domain_hash(
                    f"MSO02C|ORDERED_K10_NEIGHBOURS|FOLD_{outer}|{int(query_index)}",
                    canonical_json(identity_payload),
                )
                reconstruction[(arm, int(query_index))] = {
                    "outer": outer,
                    "train_global": train_global,
                    "training_hash": training_hash,
                    "nn_global": nn_global,
                    "nn_distance": nn_distance,
                    "neighbour_hash": neighbour_hash,
                    "query_feature_hash": float_array_hash(
                        f"MSO02C|QUERY_FEATURE|{arm}|FOLD_{outer}|{int(query_index)}",
                        sampled_features[arm][query_index],
                    ),
                    "normalized_query_feature_hash": float_array_hash(
                        f"MSO02C|NORMALIZED_QUERY_FEATURE|{arm}|FOLD_{outer}|{int(query_index)}",
                        x_scaled[query_index],
                    ),
                }

    neighbour_rows: list[dict[str, Any]] = []
    attribution_rows: list[dict[str, Any]] = []
    for frozen in sorted(
        zero_rows,
        key=lambda row: (
            row["arm"], row["component"], int(row["formal_case_index"]),
            int(row["particle_id"]),
        ),
    ):
        arm = frozen["arm"]
        component = frozen["component"]
        query_index = int(frozen["query_sample_global_index"])
        record = reconstruction.get((arm, query_index))
        if record is None:
            raise RuntimeError("MSO02C_G1_AB_ATTRIBUTION_INCOMPLETE")
        nn_global = np.asarray(record["nn_global"], dtype=np.int64)
        nn_full_rows = np.asarray(meta["full_row"][nn_global], dtype=np.int64)
        query_full_row = int(meta["full_row"][query_index])
        target = targets[component]
        query_target = target[query_full_row]
        neighbour_targets = target[nn_full_rows]
        access_counts["query_target_row_consumptions"] += 1
        access_counts["selected_k10_neighbour_target_row_consumptions"] += PRIMARY_K
        access_counts["descriptor_nn_numerator_attempts"] += 1
        numerator = exact_numerator(component, query_target, neighbour_targets)
        access_counts["descriptor_nn_numerator_completed"] += 1
        is_a = numerator == 0.0
        is_b = numerator > 0.0
        if is_a == is_b:
            raise RuntimeError("MSO02C_G1_AB_ATTRIBUTION_INCOMPLETE")
        all_nn_equal = bool(np.all(neighbour_targets == query_target))
        nn_nonidentical_underflow = bool(is_a and not all_nn_equal)
        for rank, (nn_index, distance) in enumerate(
            zip(nn_global, np.asarray(record["nn_distance"])), start=1
        ):
            neighbour_rows.append(
                {
                    "arm": arm,
                    "component": component,
                    "formal_case_index": int(frozen["formal_case_index"]),
                    "case_id": frozen["case_id"],
                    "particle_id": int(frozen["particle_id"]),
                    "query_sample_global_index": query_index,
                    "query_full_store_row": query_full_row,
                    "fold": frozen["fold"],
                    "family": frozen["family"],
                    "field_lineage_id": frozen["field_lineage_id"],
                    "nn_rank": rank,
                    "nn_sample_global_index": int(nn_index),
                    "nn_full_store_row": int(meta["full_row"][nn_index]),
                    "nn_case_id": str(meta["case_id"][nn_index]),
                    "nn_particle_id": int(meta["particle_id"][nn_index]),
                    "nn_lineage_id": str(meta["lineage"][nn_index]),
                    "descriptor_distance": format(float(distance), ".17g"),
                    "descriptor_distance_hex": float(distance).hex(),
                    "training_pool_identity_sha256": record["training_hash"],
                    "neighbour_set_sha256": record["neighbour_hash"],
                    "query_feature_vector_sha256": record["query_feature_hash"],
                    "normalized_query_feature_sha256": record[
                        "normalized_query_feature_hash"
                    ],
                    "evidence_class": "CONSUMED_EVIDENCE_DIAGNOSTIC_ONLY",
                }
            )
        attribution_rows.append(
            {
                "arm": arm,
                "component": component,
                "formal_case_index": int(frozen["formal_case_index"]),
                "case_id": frozen["case_id"],
                "particle_id": int(frozen["particle_id"]),
                "fold": frozen["fold"],
                "family": frozen["family"],
                "field_lineage_id": frozen["field_lineage_id"],
                "query_sample_global_index": query_index,
                "query_full_store_row": query_full_row,
                "query_polarization": str(
                    cases[int(frozen["formal_case_index"])]["polarization"]
                ),
                "matched_random_denominator": 0.0,
                "matched_random_denominator_exact_zero": True,
                "matched_random_denominator_source": "FROZEN_G1_ZERO_MAP_NOT_RECOMPUTED",
                "descriptor_nn_numerator": format(numerator, ".17g"),
                "descriptor_nn_numerator_hex": numerator.hex(),
                "descriptor_nn_numerator_exact_zero": is_a,
                "descriptor_nn_numerator_positive": is_b,
                "classification_A_zero_over_zero": is_a,
                "classification_B_positive_over_zero": is_b,
                "query_target_exact_zero": bool(np.all(query_target == 0.0)),
                "all_nn_targets_exact_equal_query": all_nn_equal,
                "nn_nonidentical_but_numerator_exact_zero": nn_nonidentical_underflow,
                "nn_neighbour_identity_sha256": record["neighbour_hash"],
                "evidence_class": "CONSUMED_EVIDENCE_DIAGNOSTIC_ONLY",
            }
        )

    if len(neighbour_rows) != 2460 or len(attribution_rows) != 246:
        raise RuntimeError("MSO02C_G1_AB_ATTRIBUTION_INCOMPLETE")
    if not all(
        bool(row["classification_A_zero_over_zero"])
        ^ bool(row["classification_B_positive_over_zero"])
        for row in attribution_rows
    ):
        raise RuntimeError("A/B exclusivity failure")

    component_rows: list[dict[str, Any]] = []
    for arm in ARMS:
        for component in COMPONENTS:
            rows = [
                row for row in attribution_rows
                if row["arm"] == arm and row["component"] == component
            ]
            a_count = sum(bool(row["classification_A_zero_over_zero"]) for row in rows)
            b_count = sum(bool(row["classification_B_positive_over_zero"]) for row in rows)
            if a_count + b_count != EXPECTED_BY_COMPONENT[component]:
                raise RuntimeError("component count conservation failure")
            affected_case_count = len({row["case_id"] for row in rows})
            if affected_case_count != EXPECTED_CASES_BY_COMPONENT[component]:
                raise RuntimeError("component affected-case conservation failure")
            component_rows.append(
                {
                    "arm": arm,
                    "component": component,
                    "zero_denominator_query_count": len(rows),
                    "A_count": a_count,
                    "B_count": b_count,
                    "A_fraction": a_count / len(rows),
                    "B_fraction": b_count / len(rows),
                    "affected_case_count": affected_case_count,
                    "affected_family_count": len({row["family"] for row in rows}),
                    "affected_fold_count": len({row["fold"] for row in rows}),
                    "affected_lineage_count": len({row["field_lineage_id"] for row in rows}),
                    "numerator_min_positive": min(
                        (
                            float.fromhex(row["descriptor_nn_numerator_hex"])
                            for row in rows if row["descriptor_nn_numerator_positive"]
                        ),
                        default="",
                    ),
                    "all_denominators_exact_zero": True,
                    "A_XOR_B_all_rows": True,
                }
            )

    family_fold_rows: list[dict[str, Any]] = []
    for arm in ARMS:
        for component in COMPONENTS:
            for family in FAMILIES:
                for fold in FOLDS:
                    rows = [
                        row for row in attribution_rows
                        if row["arm"] == arm and row["component"] == component
                        and row["family"] == family and row["fold"] == f"FOLD_{fold}"
                    ]
                    a_count = sum(
                        bool(row["classification_A_zero_over_zero"]) for row in rows
                    )
                    b_count = sum(
                        bool(row["classification_B_positive_over_zero"]) for row in rows
                    )
                    family_fold_rows.append(
                        {
                            "arm": arm,
                            "component": component,
                            "family": family,
                            "fold": f"FOLD_{fold}",
                            "zero_denominator_query_count": len(rows),
                            "A_count": a_count,
                            "B_count": b_count,
                            "A_fraction": a_count / len(rows) if rows else "",
                            "B_fraction": b_count / len(rows) if rows else "",
                            "affected_case_count": len({row["case_id"] for row in rows}),
                            "affected_lineage_count": len(
                                {row["field_lineage_id"] for row in rows}
                            ),
                        }
                    )

    # M1--M7 global audit plus M2a--M2d by arm/component/family.
    global_a = sum(bool(row["classification_A_zero_over_zero"]) for row in attribution_rows)
    global_b = sum(bool(row["classification_B_positive_over_zero"]) for row in attribution_rows)
    query_exact_zero_count = sum(
        bool(row["query_target_exact_zero"]) for row in attribution_rows
    )
    nn_underflow_count = sum(
        bool(row["nn_nonidentical_but_numerator_exact_zero"])
        for row in attribution_rows
    )
    mechanism_rows: list[dict[str, Any]] = [
        {
            "scope": "GLOBAL", "arm": "BOTH", "component": "ALL", "family": "ALL",
            "mechanism": "M1", "classification": "SUPPORTED",
            "evidence_count": len(attribution_rows), "query_count": len(attribution_rows),
            "evidence": "raw_float64_exact_zero_and_exact_target_multiplicity_already_frozen",
            "analytical_symmetry_subtype": "INCONCLUSIVE_AT_ANALYTICAL_SYMMETRY_SUBTYPE",
        },
        {
            "scope": "GLOBAL", "arm": "BOTH", "component": "ALL", "family": "ALL",
            "mechanism": "M2", "classification": "SUPPORTED",
            "evidence_count": len(attribution_rows),
            "query_count": len(attribution_rows),
            "evidence": (
                "frozen_random_target_exact_multiplicity_for_all_queries;"
                f"query_exact_zero_count={query_exact_zero_count};split_by_M2a_to_M2d"
            ),
            "analytical_symmetry_subtype": "INCONCLUSIVE_AT_ANALYTICAL_SYMMETRY_SUBTYPE",
        },
        {
            "scope": "GLOBAL", "arm": "BOTH", "component": "ALL", "family": "ALL",
            "mechanism": "M3", "classification": "SUPPORTED",
            "evidence_count": len(attribution_rows), "query_count": len(attribution_rows),
            "evidence": "frozen_matched_random_denominator_exact_zero_for_every_authorized_query",
            "analytical_symmetry_subtype": "NOT_APPLICABLE",
        },
        {
            "scope": "GLOBAL", "arm": "BOTH", "component": "ALL", "family": "ALL",
            "mechanism": "M4", "classification": "INCONCLUSIVE",
            "evidence_count": 0, "query_count": len(attribution_rows),
            "evidence": (
                "random_pool_not_family_stratified;family_value_multiplicity_contribution_"
                "not_separately_identified"
            ),
            "analytical_symmetry_subtype": "NOT_APPLICABLE",
        },
        {
            "scope": "GLOBAL", "arm": "BOTH", "component": "ALL", "family": "ALL",
            "mechanism": "M5", "classification": "NOT_SUPPORTED",
            "evidence_count": 0, "query_count": len(attribution_rows),
            "evidence": "prior_raw_store_and_serializer_bitwise_identity_remains_frozen",
            "analytical_symmetry_subtype": "NOT_APPLICABLE",
        },
        {
            "scope": "GLOBAL", "arm": "BOTH", "component": "ALL", "family": "ALL",
            "mechanism": "M6", "classification": "NOT_SUPPORTED",
            "evidence_count": 0, "query_count": len(attribution_rows),
            "evidence": (
                "exact_source_rank_specific_float64_reconstruction_found_no_residual;"
                "historical_particle_neighbour_arrays_were_not_persisted"
            ),
            "analytical_symmetry_subtype": "NOT_APPLICABLE",
        },
        {
            "scope": "GLOBAL", "arm": "BOTH", "component": "ALL", "family": "ALL",
            "mechanism": "M7",
            "classification": "SUPPORTED" if nn_underflow_count else "NOT_SUPPORTED",
            "evidence_count": nn_underflow_count, "query_count": len(attribution_rows),
            "evidence": (
                "nonidentical_descriptor_target_difference_squared_to_exact_zero"
                if nn_underflow_count else "no_integrity_failure_underflow_or_unclassified_A_B_row"
            ),
            "analytical_symmetry_subtype": "NOT_APPLICABLE",
        },
    ]
    for arm in ARMS:
        for component in COMPONENTS:
            for family in FAMILIES:
                rows = [
                    row for row in attribution_rows
                    if row["arm"] == arm and row["component"] == component
                    and row["family"] == family
                ]
                definitions = (
                    (
                        "M2a", "query_target_itself_exact_zero",
                        lambda row: bool(row["query_target_exact_zero"]),
                    ),
                    (
                        "M2b", "query_target_nonzero_but_random_targets_exact_repeated",
                        lambda row: not bool(row["query_target_exact_zero"]),
                    ),
                    (
                        "M2c", "descriptor_neighbours_target_identical",
                        lambda row: bool(row["all_nn_targets_exact_equal_query"]),
                    ),
                    (
                        "M2d", "descriptor_neighbours_differ_despite_random_zero",
                        lambda row: not bool(row["all_nn_targets_exact_equal_query"]),
                    ),
                )
                for mechanism, description, predicate in definitions:
                    evidence_count = sum(predicate(row) for row in rows)
                    classification = (
                        "INCONCLUSIVE" if not rows else
                        "SUPPORTED" if evidence_count > 0 else "NOT_SUPPORTED"
                    )
                    mechanism_rows.append(
                        {
                            "scope": "ARM_COMPONENT_FAMILY",
                            "arm": arm,
                            "component": component,
                            "family": family,
                            "mechanism": mechanism,
                            "classification": classification,
                            "evidence_count": evidence_count,
                            "query_count": len(rows),
                            "evidence": description,
                            "analytical_symmetry_subtype": (
                                "INCONCLUSIVE_AT_ANALYTICAL_SYMMETRY_SUBTYPE"
                                if mechanism in ("M2a", "M2b") else "NOT_APPLICABLE"
                            ),
                        }
                    )

    # Confirm representation-dependent neighbour differences for colocated keys.
    neighbour_hash_by_key = {
        (
            row["arm"], row["component"], row["case_id"], int(row["particle_id"])
        ): row["nn_neighbour_identity_sha256"]
        for row in attribution_rows
    }
    representation_difference_count = 0
    for row in attribution_rows:
        if row["arm"] != "SS":
            continue
        other = neighbour_hash_by_key[(
            "MS", row["component"], row["case_id"], int(row["particle_id"])
        )]
        representation_difference_count += int(
            row["nn_neighbour_identity_sha256"] != other
        )

    observable_hash_after = counted_store_hash(OBSERVABLE, access_counts, "observable")
    target_hash_after = counted_store_hash(TARGET, access_counts, "target")
    if observable_hash_after != observable_hash_before or target_hash_after != target_hash_before:
        raise RuntimeError("MSO02C_UPSTREAM_EVIDENCE_INTEGRITY_CONFLICT:store changed")

    unique_query_particles_by_arm = {
        arm: len({
            (row["case_id"], int(row["particle_id"]))
            for row in attribution_rows if row["arm"] == arm
        })
        for arm in ARMS
    }
    access_audit = {
        "schema_version": "1.0.0",
        "stage": "MSO-02C_G1_DESCRIPTOR_NEIGHBOUR_RECONSTRUCTION",
        "status": "MSO02C_G1_AB_ATTRIBUTION_EXECUTION_COMPLETE_AWAITING_FINALIZATION",
        "evidence_class": "CONSUMED_EVIDENCE_DIAGNOSTIC_ONLY",
        "pre_observable_access_parent_head": "8943de6b2b82dc25e850cab18eebe40c2939319d",
        "observable_access_authorization_commit": AUTHORIZATION_COMMIT,
        "descriptor_reconstruction_execution_commit": execution_head,
        "authorization_sha256": sha256(AUTHORIZATION),
        "execution_freeze_sha256": sha256(EXECUTION_FREEZE),
        "executable_sha256": sha256(Path(__file__).resolve()),
        "frozen_identity_sha256": static_actual,
        "observable_store_sha256_before": observable_hash_before,
        "observable_store_sha256_after": observable_hash_after,
        "target_store_sha256_before": target_hash_before,
        "target_store_sha256_after": target_hash_after,
        "observable_archive_members": observable_members,
        "target_archive_members": target_members,
        "observable_payload_keys_read": ["ss_features", "ms_features"],
        "target_payload_keys_read": [
            "target_density_rate",
            "target_pressure_gradient_acceleration",
            "target_viscosity_laplacian_acceleration",
        ],
        "runtime_fingerprint": {
            **runtime_actual,
            "python_implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "ckdtree": "scipy.spatial.cKDTree_compact_nodes_true_balanced_tree_true",
        },
        "access_counts": dict(access_counts),
        "observable_store_hash_reads": access_counts["observable_store_hash_reads"],
        "observable_store_payload_reads": access_counts[
            "observable_store_payload_reads"
        ],
        "target_store_hash_reads": access_counts["target_store_hash_reads"],
        "target_store_payload_reads": access_counts["target_store_payload_reads"],
        "zero_query_count": len(attribution_rows),
        "ss_reconstructed_query_count": 123,
        "ms_reconstructed_query_count": 123,
        "reconstruction_counts": {
            "component_query_keys_per_arm": 123,
            "arm_component_query_classifications": len(attribution_rows),
            "zero_query_count": len(attribution_rows),
            "zero_query_count_per_arm": 123,
            "ss_reconstructed_query_count": 123,
            "ms_reconstructed_query_count": 123,
            "unique_query_particles_by_arm": unique_query_particles_by_arm,
            "ss_reconstructed_component_queries": sum(
                row["arm"] == "SS" for row in attribution_rows
            ),
            "ms_reconstructed_component_queries": sum(
                row["arm"] == "MS" for row in attribution_rows
            ),
            "selected_k10_neighbour_target_lookups": len(neighbour_rows),
            "descriptor_nn_required_k20_internal_constructions": search_invocations,
            "descriptor_nn_required_k20_determinism_repeat_constructions": (
                deterministic_repeat_invocations
            ),
            "deterministic_repeat_all_equal": True,
            "k20_metric_evaluations": 0,
            "k20_sensitivity_evaluations": 0,
            "k5_sensitivity_evaluations": 0,
            "matched_random_denominator_recomputations": 0,
            "representation_dependent_neighbour_set_difference_count_of_123": (
                representation_difference_count
            ),
            "A_count_total": global_a,
            "B_count_total": global_b,
        },
        "prohibited_counts": {
            "full_dnn_metric_recompute_count": 0,
            "dnn_median_recompute_count": 0,
            "dnn_p90_recompute_count": 0,
            "candidate_metric_performance_count": 0,
            "metric_selection_count": 0,
            "amendment_creation_count": 0,
            "consumed_replay_count": 0,
            "new_h3_verdict_count": 0,
            "feature_modification_count": 0,
            "feature_deletion_count": 0,
            "feature_addition_count": 0,
            "feature_selection_count": 0,
            "pca_count": 0,
            "whitening_count": 0,
            "normalization_modification_count": 0,
            "distance_modification_count": 0,
            "K_modification_count": 0,
            "exclusion_modification_count": 0,
            "fold_modification_count": 0,
            "case_modification_count": 0,
            "target_modification_count": 0,
            "cvar_recompute_count": 0,
            "oracle_recompute_count": 0,
            "coverage_recompute_count": 0,
            "bootstrap_recompute_count": 0,
            "neural_count": 0,
            "attention_count": 0,
            "optimizer_count": 0,
            "training_count": 0,
            "integration_count": 0,
            "solver_in_loop_count": 0,
            "rollout_count": 0,
            "sealed_test_count": 0,
            "arc_access_count": 0,
        },
        "query_row_join_identity_basis": (
            "FROZEN_COMPLETE_OBSERVABLE_SHA_PLUS_PREVIOUSLY_PASSED_MSO02B_JOIN_AUDIT;"
            "observable_case_id_and_particle_id_payload_keys_not_authorized_or_read"
        ),
        "old_mso02b_or_h_mso01_verdict_modified": False,
        "preserved_mso02b_terminal_status": (
            "MSO02B_PAIRED_PRELEARNING_IDENTIFIABILITY_REQUALIFICATION_NOT_EVALUABLE"
        ),
        "preserved_h_mso01_global_status": (
            "H_MSO01_MULTISCALE_IDENTIFIABILITY_RESCUE_NOT_EVALUABLE"
        ),
        "metric_selection_authorized": False,
        "metric_amendment_authorized": False,
        "zero_safe_metric_selected": False,
        "metric_amendment_created": False,
        "consumed_replay": False,
        "h_mso01r_contract_frozen": False,
        "h_mso01r_fresh_requalification_eligible": False,
        "h_mso01r_fresh_requalification_authorized": False,
        "mso03_eligible": False,
        "attention_authorized": False,
        "neural_training_authorized": False,
        "learned_operator_authorized": False,
        "METRIC_SELECTION_AUTHORIZED": False,
        "METRIC_AMENDMENT_AUTHORIZED": False,
        "H_MSO01R_FRESH_REQUALIFICATION_AUTHORIZED": False,
        "MSO03_ELIGIBLE": False,
        "ATTENTION_AUTHORIZED": False,
        "NEURAL_TRAINING_AUTHORIZED": False,
        "LEARNED_OPERATOR_AUTHORIZED": False,
    }

    staged_paths = {path: staging / path.name for path in EXECUTION_OUTPUTS}
    write_csv_atomic(staged_paths[NEIGHBOURS], neighbour_rows)
    write_csv_atomic(staged_paths[AB_ATTRIBUTION], attribution_rows)
    write_csv_atomic(staged_paths[COMPONENT_SUMMARY], component_rows)
    write_csv_atomic(staged_paths[FAMILY_FOLD_SUMMARY], family_fold_rows)
    write_csv_atomic(staged_paths[MECHANISM_AFTER_AB], mechanism_rows)
    write_json_atomic(staged_paths[ACCESS_AUDIT], access_audit)

    # Strict parse/count validation before any final-path promotion.
    expected_csv_rows = {
        NEIGHBOURS: 2460,
        AB_ATTRIBUTION: 246,
        COMPONENT_SUMMARY: 6,
        FAMILY_FOLD_SUMMARY: 144,
        MECHANISM_AFTER_AB: 103,
    }
    for path, expected in expected_csv_rows.items():
        with staged_paths[path].open(encoding="utf-8", newline="") as handle:
            if len(list(csv.DictReader(handle))) != expected:
                raise RuntimeError(f"staged row-count failure {path}")
    json.loads(staged_paths[ACCESS_AUDIT].read_text(encoding="utf-8"))
    append_event(
        "COMPUTATION_COMPLETE",
        access_counts,
        staged_sha256={path.name: sha256(staged_paths[path]) for path in EXECUTION_OUTPUTS},
    )
    publish_staged(staging, EXECUTION_OUTPUTS)
    append_event(
        "EXECUTION_OUTPUTS_PUBLISHED_AWAITING_FINALIZATION",
        access_counts,
        published_sha256={path.name: sha256(path) for path in EXECUTION_OUTPUTS},
    )
    print(
        "MSO02C_G1_AB_ATTRIBUTION_EXECUTION_COMPLETE_AWAITING_FINALIZATION",
        flush=True,
    )


def main() -> None:
    access_counts = new_access_counts()
    freeze_sha = sha256(EXECUTION_FREEZE)
    staging = STAGING_ROOT / freeze_sha

    if all(path.exists() for path in EXECUTION_OUTPUTS):
        if not EVENT_JOURNAL.exists():
            raise RuntimeError("MSO02C_G1_PRIOR_ACCESS_ATTEMPT_REQUIRES_AUDIT")
        access_counts = json.loads(ACCESS_AUDIT.read_text(encoding="utf-8"))[
            "access_counts"
        ]
        events = [
            json.loads(line)
            for line in EVENT_JOURNAL.read_text(encoding="utf-8").splitlines()
        ]
        if not events or events[-1]["event"] not in (
            "COMPUTATION_COMPLETE",
            "EXECUTION_OUTPUTS_PUBLISHED_AWAITING_FINALIZATION",
        ):
            raise RuntimeError("MSO02C_G1_PRIOR_ACCESS_ATTEMPT_REQUIRES_AUDIT")
        computation_events = [
            event for event in events if event["event"] == "COMPUTATION_COMPLETE"
        ]
        if len(computation_events) != 1:
            raise RuntimeError("MSO02C_G1_PRIOR_ACCESS_ATTEMPT_REQUIRES_AUDIT")
        actual_sha = {path.name: sha256(path) for path in EXECUTION_OUTPUTS}
        if computation_events[0].get("staged_sha256") != actual_sha:
            raise RuntimeError("MSO02C_G1_PRIOR_ACCESS_ATTEMPT_REQUIRES_AUDIT")
        if (
            events[-1]["event"] == "EXECUTION_OUTPUTS_PUBLISHED_AWAITING_FINALIZATION"
            and events[-1].get("published_sha256") != actual_sha
        ):
            raise RuntimeError("MSO02C_G1_PRIOR_ACCESS_ATTEMPT_REQUIRES_AUDIT")
        if staging.exists():
            for candidate in staging.iterdir():
                matching = next(
                    (path for path in EXECUTION_OUTPUTS if path.name == candidate.name),
                    None,
                )
                if matching is None or not candidate.is_file() or sha256(candidate) != actual_sha[matching.name]:
                    raise RuntimeError("MSO02C_G1_PRIOR_ACCESS_ATTEMPT_REQUIRES_AUDIT")
                candidate.unlink()
            staging.rmdir()
            if STAGING_ROOT.exists() and not any(STAGING_ROOT.iterdir()):
                STAGING_ROOT.rmdir()
        if events[-1]["event"] == "COMPUTATION_COMPLETE":
            append_event(
                "EXECUTION_OUTPUTS_PUBLISHED_AWAITING_FINALIZATION",
                access_counts,
                promotion_recovery=True,
                published_sha256=actual_sha,
            )
        print(
            "MSO02C_G1_AB_ATTRIBUTION_EXECUTION_COMPLETE_AWAITING_FINALIZATION",
            flush=True,
        )
        return
    if staging.exists() and all((staging / path.name).exists() for path in EXECUTION_OUTPUTS):
        staged_audit = json.loads(
            (staging / ACCESS_AUDIT.name).read_text(encoding="utf-8")
        )
        access_counts = staged_audit["access_counts"]
        if not EVENT_JOURNAL.exists():
            raise RuntimeError("MSO02C_G1_PRIOR_ACCESS_ATTEMPT_REQUIRES_AUDIT")
        events = [
            json.loads(line)
            for line in EVENT_JOURNAL.read_text(encoding="utf-8").splitlines()
        ]
        computation_events = [
            event for event in events if event["event"] == "COMPUTATION_COMPLETE"
        ]
        staged_sha = {
            path.name: sha256(staging / path.name) for path in EXECUTION_OUTPUTS
        }
        if (
            not events
            or events[-1]["event"] != "COMPUTATION_COMPLETE"
            or len(computation_events) != 1
            or computation_events[0].get("access_counts") != access_counts
            or computation_events[0].get("staged_sha256") != staged_sha
        ):
            raise RuntimeError("MSO02C_G1_PRIOR_ACCESS_ATTEMPT_REQUIRES_AUDIT")
        publish_staged(staging, EXECUTION_OUTPUTS)
        append_event(
            "EXECUTION_OUTPUTS_PUBLISHED_AWAITING_FINALIZATION",
            access_counts,
            promotion_recovery=True,
            published_sha256={path.name: sha256(path) for path in EXECUTION_OUTPUTS},
        )
        print(
            "MSO02C_G1_AB_ATTRIBUTION_EXECUTION_COMPLETE_AWAITING_FINALIZATION",
            flush=True,
        )
        return
    if (
        any(path.exists() for path in EXECUTION_OUTPUTS)
        or EVENT_JOURNAL.exists()
        or FAILURE_ACCESS_AUDIT.exists()
        or STAGING_ROOT.exists()
    ):
        raise RuntimeError("MSO02C_G1_PRIOR_ACCESS_ATTEMPT_REQUIRES_AUDIT")

    execution_head: str | None = None
    try:
        execute(access_counts)
    except BaseException as error:
        try:
            execution_head = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
                capture_output=True, text=True,
            ).stdout.strip()
            if EVENT_JOURNAL.exists() or any(access_counts.values()):
                append_event(
                    "ATTEMPT_FAILED", access_counts,
                    error_type=type(error).__name__, error=str(error),
                )
                write_failure_access_audit(
                    execution_head=execution_head,
                    access_counts=access_counts,
                    error=error,
                )
        finally:
            raise


if __name__ == "__main__":
    main()
