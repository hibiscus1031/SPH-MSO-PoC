#!/usr/bin/env python3
"""Attribute frozen MSO-02B matched-random exact-zero denominators.

This diagnostic intentionally never opens the MSO-02A observable store.  It
reconstructs the frozen random-baseline identities from target-free metadata,
reads the already consumed MSO-02B target once, and performs an in-memory raw
binary64 integrity replay only for cases involved in an exact-zero denominator.
It cannot reconstruct descriptor-neighbour numerators because particle-level
neighbour identities were not persisted and the observable payload is outside
the MSO-02C authorization.
"""

from __future__ import annotations

from collections import defaultdict
import csv
import hashlib
import importlib
import importlib.util
import io
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from typing import Any
import zipfile

import numpy as np
import scipy
import sklearn
import torch


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "06_experiments/mso02c"
FORMAL = ROOT / "05_registries/mso02a_formal_fresh_atlas_registry.json"
SAMPLE = ROOT / "05_registries/mso02b_formal_particle_sample_registry.json"
TARGET = ROOT / "06_experiments/mso02b/target_ref/mso02b_target_store.npz"
BUILDER = ROOT / "06_experiments/mso02b/build_mso02b_targets.py"
VENDOR = ROOT / "01_provenance/vendor/ddo_analytical_reference"

PARTICLE_MAP = OUT / "zero_denominator_particle_map.csv"
CASE_MAP = OUT / "zero_denominator_case_map.csv"
CELL_SUMMARY = OUT / "zero_denominator_family_fold_summary.csv"
MECHANISM = OUT / "degeneracy_mechanism_audit.csv"
AUDIT = OUT / "attribution_execution_audit.json"

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
FAMILIES = ("F1", "F2", "F3", "F4")
FOLDS = tuple(range(6))
PRIMARY_K = 10
EXPECTED_CASE_COUNTS = {
    "density_rate": 2,
    "pressure_gradient_acceleration": 87,
    "viscosity_laplacian_acceleration": 2,
}

STATIC_HASHES = {
    "00_project_contract/mso02c_dnn_degeneracy_diagnostic_contract.md":
        "781618a8cf52f05bded1b3af99b897815df78c1eefcde3c70d32ae60ac92753f",
    "05_registries/mso02a_formal_fresh_atlas_registry.json":
        "9893cf48d73be3316a66bb7b9c7f71db8c122247ce56b67d1b0f685605b761c6",
    "05_registries/mso02b_formal_particle_sample_registry.json":
        "98ff5716e3adbbaac4cac4899e76eb4d61d4e194396fe4e37041a94abe0ca229",
    "05_registries/mso02b_analysis_semantics_registry.json":
        "b271864a62800ea502d1f21621b3d937088f6809c0d31301e6effac96d203ce5",
    "05_registries/mso02b_target_role_registry.json":
        "31d971c050576cf4cc3e8fd211691f4c4714862eba18c5ae37391fb30044b61f",
    "06_experiments/mso02a/fold_normalization_registry.json":
        "f8fb9ccde826ece14690ab255955ecb7b922bc5cd27ddb9b0544b9fd9c9bd634",
    "06_experiments/mso02a/ss_observable_schema.json":
        "b2237506cac4bbc67dfda981f15daea47c32535259d394b962263a82190e2ec4",
    "06_experiments/mso02a/ms_observable_schema.json":
        "51ff5e04dde4b862f3cab19c80e2aea93c151006fe7b3f497001e43475ec18cb",
    "06_experiments/mso02b/run_mso02b_formal.py":
        "55b0b63eb2c99364c8a2e96c75191a50707e93357f7039bd9edfdcb7c7c831b7",
    "06_experiments/mso02b/build_mso02b_targets.py":
        "940a671927b20f219a4d2553ab61f36bc568e1c8e29bd9f043edd44103f1a08f",
    "06_experiments/mso02b/prepare_mso02b_target_freeze.py":
        "edb6e9a9b8c4d3ce69effeec010051b1c812a8812aff3b863b70e29a0e0d472c",
    "01_provenance/vendor/ddo_analytical_reference/mso02b_target_reference.py":
        "cd0d8794efa1900f307710e27438939bbff282aa0aa617629eab1f64427bc017",
    "01_provenance/vendor/ddo_analytical_reference/__init__.py":
        "c82e527905a94af4347d71bcc692885fbe0574aa0eb78c9855961376d91308ba",
    "01_provenance/mso02b_target_reference_import_manifest.csv":
        "124f430ca3bacd73d6ac8ec0f8789c2e76a04b460b9b172329cb7530b4a25b8a",
    "08_manifests/mso02b_target_precompute_freeze.json":
        "9dcf39f43e46323433f2e29c73ac3b09743d4a1070af032c0f44c7bd49783962",
    "08_manifests/mso02b_formal_execution_erratum_01.json":
        "b046991e08e81bc8ef2be87f203b9ceda5672bdbd1d5c3d217ab0dd8428efb9b",
    "08_manifests/mso02b_manifest.json":
        "94ce69002d714acff2176fc71910e18766f873ed26be7437763eb34762e68fe6",
    "08_manifests/mso02b_status_ledger.json":
        "cb9864b34c94f4ae022745fa9b6040bd2baaf6bdae7156a3905b22584a268815",
}
TARGET_SHA256 = "16f1ebd26d0d1aa74dd0892dfe2feb0967024f9219dd8c102c8faafc934f81e2"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def seed_integer(value: str) -> int:
    return int(hash_text(value), 16)


def exact_bits_equal(left: np.ndarray, right: np.ndarray) -> bool:
    a = np.ascontiguousarray(np.asarray(left, dtype=np.float64))
    b = np.ascontiguousarray(np.asarray(right, dtype=np.float64))
    return a.shape == b.shape and a.tobytes() == b.tobytes()


def numeric_exact_all(values: np.ndarray, query: np.ndarray) -> bool:
    return bool(np.all(values == query))


def bitwise_exact_all(values: np.ndarray, query: np.ndarray) -> bool:
    values = np.asarray(values, dtype=np.float64)
    query = np.asarray(query, dtype=np.float64)
    expanded = np.broadcast_to(query, values.shape)
    return exact_bits_equal(values, expanded)


def squared_disagreement(values: np.ndarray, query: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    query = np.asarray(query, dtype=np.float64)
    difference = values - query
    if query.ndim == 0:
        return difference * difference
    return np.sum(difference * difference, axis=-1)


def write_csv_atomic(path: Path, rows: list[dict[str, Any]]) -> None:
    if path.exists():
        raise RuntimeError(f"refusing to overwrite {path}")
    fields = list(rows[0]) if rows else ["status"]
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    if path.exists():
        raise RuntimeError(f"refusing to overwrite {path}")
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def check_git_and_static_identity() -> dict[str, str]:
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
    if branch != "main" or status or remotes:
        raise RuntimeError("MSO02C_G1_GIT_BOUNDARY_FAILURE")
    mismatches = []
    actual = {}
    for relative, expected in STATIC_HASHES.items():
        value = sha256(ROOT / relative)
        actual[relative] = value
        if value != expected:
            mismatches.append(f"{relative}:{value}!={expected}")
    if mismatches:
        raise RuntimeError("MSO02C_UPSTREAM_EVIDENCE_INTEGRITY_CONFLICT:" + ";".join(mismatches))
    return actual


def ordered_training_indices(indices: np.ndarray, meta: dict[str, np.ndarray]) -> np.ndarray:
    keys = meta["sample_key"][indices]
    digests = np.asarray([hash_text(str(key)) for key in keys])
    return indices[np.lexsort((keys, digests))]


def random_baseline_indices(
    train_global: np.ndarray,
    query_global: np.ndarray,
    meta: dict[str, np.ndarray],
) -> np.ndarray:
    result = np.empty((query_global.size, 20), dtype=np.int64)
    train_seed = meta["seed"][train_global]
    all_local = np.arange(train_global.size, dtype=np.int64)
    pool_by_seed: dict[int, np.ndarray] = {0: all_local}
    for seed in np.unique(meta["seed"][query_global]):
        if int(seed) != 0:
            pool_by_seed[int(seed)] = all_local[train_seed != int(seed)]
    for local, global_index in enumerate(query_global):
        seed = int(meta["seed"][global_index])
        pool = pool_by_seed[seed]
        rng = np.random.Generator(
            np.random.PCG64(
                seed_integer(
                    f"MSO02B|BASELINE|{meta['case_id'][global_index]}|"
                    f"{int(meta['particle_id'][global_index])}"
                )
            )
        )
        primary = rng.choice(pool, size=PRIMARY_K, replace=False)
        remaining = pool[~np.isin(pool, primary, assume_unique=False)]
        extension_rng = np.random.Generator(
            np.random.PCG64(
                seed_integer(
                    f"MSO02B|BASELINE_K20_EXTENSION|{meta['case_id'][global_index]}|"
                    f"{int(meta['particle_id'][global_index])}"
                )
            )
        )
        extension = extension_rng.choice(remaining, size=10, replace=False)
        result[local] = np.concatenate((primary, extension))
    return result


def build_sampled_metadata(
    cases: list[dict[str, Any]], sample_payload: dict[str, Any]
) -> dict[str, np.ndarray]:
    sample_by_case = {
        int(row["formal_case_index"]): row for row in sample_payload["cases"]
    }
    values: dict[str, list[Any]] = defaultdict(list)
    for ordinal, case in enumerate(cases):
        if int(case["formal_case_index"]) != ordinal:
            raise RuntimeError("formal case order mismatch")
        registered = sample_by_case[ordinal]
        particles = [int(value) for value in registered["particle_ids_in_hash_order"]]
        if len(particles) != 128 or len(set(particles)) != 128:
            raise RuntimeError(f"formal sample mismatch case={ordinal}")
        for rank, particle in enumerate(particles):
            values["full_row"].append(ordinal * 576 + particle)
            values["case_index"].append(ordinal)
            values["particle_id"].append(particle)
            values["sample_rank"].append(rank)
            values["case_id"].append(case["case_id"])
            values["lineage"].append(case["field_lineage_id"])
            values["family"].append(case["macro_family"])
            values["fold"].append(int(case["fold"].split("_")[1]))
            values["seed"].append(int(case["jitter_seed"]))
            values["sample_key"].append(f"{case['case_id']}|{particle}")
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


def in_memory_npz_roundtrip(array: np.ndarray) -> np.ndarray:
    payload = io.BytesIO()
    np.lib.format.write_array(payload, np.asarray(array), allow_pickle=False)
    archive_buffer = io.BytesIO()
    with zipfile.ZipFile(
        archive_buffer, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        info = zipfile.ZipInfo("value.npy", date_time=(1980, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o600 << 16
        archive.writestr(
            info, payload.getvalue(), compress_type=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        )
    archive_buffer.seek(0)
    with np.load(archive_buffer, allow_pickle=False) as loaded:
        return np.asarray(loaded["value"])


def load_raw_replay_module() -> tuple[Any, Any]:
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    torch.set_default_dtype(torch.float64)
    sys.path.insert(0, str(VENDOR))
    reference = importlib.import_module("mso02b_target_reference")
    reference.assert_static_operator_import_identity()
    spec = importlib.util.spec_from_file_location("mso02b_frozen_builder", BUILDER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot import frozen target builder")
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    builder.ref = reference
    return builder, reference


def main() -> None:
    for path in (PARTICLE_MAP, CASE_MAP, CELL_SUMMARY, MECHANISM, AUDIT):
        if path.exists():
            raise RuntimeError(f"MSO02C G1 output already exists: {path}")
    OUT.mkdir(parents=True, exist_ok=True)
    static_actual = check_git_and_static_identity()

    target_hash = sha256(TARGET)
    if target_hash != TARGET_SHA256:
        raise RuntimeError("MSO02C_UPSTREAM_EVIDENCE_INTEGRITY_CONFLICT:target hash")

    formal_payload = json.loads(FORMAL.read_text(encoding="utf-8"))
    sample_payload = json.loads(SAMPLE.read_text(encoding="utf-8"))
    cases = sorted(formal_payload["cases"], key=lambda row: int(row["formal_case_index"]))
    if len(cases) != 384 or int(sample_payload["case_count"]) != 384:
        raise RuntimeError("formal population mismatch")
    meta = build_sampled_metadata(cases, sample_payload)
    sampled_rows = meta["full_row"]

    with np.load(TARGET, allow_pickle=False) as store:
        required = {
            "formal_case_index", "particle_id", *TARGET_FIELDS.values()
        }
        if not required.issubset(store.files):
            raise RuntimeError("target schema mismatch")
        full_case = np.asarray(store["formal_case_index"])
        full_particle = np.asarray(store["particle_id"])
        if full_case.shape != (384 * 576,) or full_particle.shape != (384 * 576,):
            raise RuntimeError("target identity shape mismatch")
        if not np.array_equal(full_case, np.repeat(np.arange(384), 576)):
            raise RuntimeError("target case order mismatch")
        if not np.array_equal(full_particle, np.tile(np.arange(576), 384)):
            raise RuntimeError("target particle order mismatch")
        full_targets = {
            component: np.asarray(store[field], dtype=np.float64)
            for component, field in TARGET_FIELDS.items()
        }
    targets = {name: value[sampled_rows] for name, value in full_targets.items()}
    if not all(np.isfinite(value).all() for value in targets.values()):
        raise RuntimeError("nonfinite target payload")

    zero_records: list[dict[str, Any]] = []
    random_identity_hashes: dict[str, str] = {}
    raw_needed_sample_indices: set[int] = set()
    working: list[dict[str, Any]] = []
    for outer in FOLDS:
        train_global = ordered_training_indices(
            np.flatnonzero(meta["fold"] != outer), meta
        )
        query_global = np.flatnonzero(meta["fold"] == outer)
        random_local = random_baseline_indices(train_global, query_global, meta)
        random_global = train_global[random_local[:, :PRIMARY_K]]
        random_identity_hashes[f"FOLD_{outer}"] = hashlib.sha256(
            np.ascontiguousarray(random_global.astype("<i8")).tobytes()
        ).hexdigest()
        for component in COMPONENTS:
            values = targets[component]
            query_values = values[query_global]
            random_values = values[random_global]
            if query_values.ndim == 1:
                denominator = np.mean(
                    (random_values - query_values[:, None]) ** 2, axis=1
                )
            else:
                difference = random_values - query_values[:, None, :]
                denominator = np.mean(
                    np.sum(difference * difference, axis=-1), axis=1
                )
            if np.any(~np.isfinite(denominator)) or np.any(denominator < 0):
                raise RuntimeError("invalid matched-random denominator")
            for position in np.flatnonzero(denominator == 0.0):
                query_index = int(query_global[position])
                random_indices = np.asarray(random_global[position], dtype=np.int64)
                query = np.asarray(values[query_index], dtype=np.float64)
                comparisons = np.asarray(values[random_indices], dtype=np.float64)
                random_numeric_equal = numeric_exact_all(comparisons, query)
                random_bitwise_equal = bitwise_exact_all(comparisons, query)
                nonidentical_underflow = not random_numeric_equal
                raw_needed_sample_indices.add(query_index)
                raw_needed_sample_indices.update(int(value) for value in random_indices)
                working.append(
                    {
                        "component": component,
                        "outer": outer,
                        "query_index": query_index,
                        "random_indices": random_indices,
                        "denominator": float(denominator[position]),
                        "query_serialized_exact_zero": bool(np.all(query == 0.0)),
                        "random_targets_numeric_exact_identical": random_numeric_equal,
                        "random_targets_uint64_bitwise_identical": random_bitwise_equal,
                        "nonidentical_but_squared_underflow_to_zero": nonidentical_underflow,
                    }
                )

    raw_case_indices = sorted(
        {int(meta["case_index"][index]) for index in raw_needed_sample_indices}
    )
    builder, _ = load_raw_replay_module()
    raw_case_arrays: dict[int, dict[str, np.ndarray]] = {}
    serializer_roundtrip_bitwise = True
    raw_store_bitwise = True
    for case_index in raw_case_indices:
        row, arrays, _ = builder.evaluate_case(cases[case_index])
        if not bool(row["case_target_reference_qualified"]):
            raise RuntimeError(f"raw replay case qualification failed {case_index}")
        canonical = {
            "density_rate": np.asarray(arrays[TARGET_FIELDS["density_rate"]], dtype=np.float64),
            "pressure_gradient_acceleration": np.asarray(
                arrays[TARGET_FIELDS["pressure_gradient_acceleration"]], dtype=np.float64
            ),
            "viscosity_laplacian_acceleration": np.asarray(
                arrays[TARGET_FIELDS["viscosity_laplacian_acceleration"]], dtype=np.float64
            ),
        }
        for component, raw in canonical.items():
            roundtrip = in_memory_npz_roundtrip(raw)
            serializer_roundtrip_bitwise &= exact_bits_equal(raw, roundtrip)
            start = case_index * 576
            stored = full_targets[component][start:start + 576]
            raw_store_bitwise &= exact_bits_equal(raw, stored)
        raw_case_arrays[case_index] = canonical
    if not serializer_roundtrip_bitwise or not raw_store_bitwise:
        raise RuntimeError(
            "MSO02C_UPSTREAM_EVIDENCE_INTEGRITY_CONFLICT:RAW_REPLAY_IDENTITY_NOT_ESTABLISHED"
        )

    for base in working:
        component = str(base["component"])
        query_index = int(base["query_index"])
        random_indices = np.asarray(base["random_indices"], dtype=np.int64)
        query_case = int(meta["case_index"][query_index])
        query_particle = int(meta["particle_id"][query_index])
        raw_query = raw_case_arrays[query_case][component][query_particle]
        raw_random_values = []
        for random_index in random_indices:
            random_case = int(meta["case_index"][random_index])
            random_particle = int(meta["particle_id"][random_index])
            raw_random_values.append(
                raw_case_arrays[random_case][component][random_particle]
            )
        raw_random = np.asarray(raw_random_values, dtype=np.float64)
        raw_denominator = float(np.mean(squared_disagreement(raw_random, raw_query)))
        classification_e = bool(raw_denominator > 0.0 and base["denominator"] == 0.0)
        classification_f = bool(raw_denominator == 0.0 and base["denominator"] == 0.0)
        if classification_e == classification_f:
            raise RuntimeError("E/F classification is not exclusive")
        random_global_string = "|".join(str(int(value)) for value in random_indices)
        record = {
            "arm": "",
            "component": component,
            "formal_case_index": query_case,
            "case_id": str(meta["case_id"][query_index]),
            "particle_id": query_particle,
            "sample_global_index": query_index,
            "sample_rank_within_case": int(meta["sample_rank"][query_index]),
            "field_lineage_id": str(meta["lineage"][query_index]),
            "fold": f"FOLD_{int(base['outer'])}",
            "family": str(meta["family"][query_index]),
            "matched_random_denominator": base["denominator"],
            "matched_random_denominator_exact_zero": True,
            "descriptor_nn_numerator": "",
            "descriptor_nn_numerator_status": "INCONCLUSIVE_INPUT_NOT_AUTHORIZED",
            "classification_A_zero_over_zero": "INCONCLUSIVE_INPUT_NOT_AUTHORIZED",
            "classification_B_positive_over_zero": "INCONCLUSIVE_INPUT_NOT_AUTHORIZED",
            "classification_C_query_serialized_exact_zero": base["query_serialized_exact_zero"],
            "classification_C_query_raw_exact_zero": bool(np.all(raw_query == 0.0)),
            "classification_D_random_targets_numeric_exact_identical": base[
                "random_targets_numeric_exact_identical"
            ],
            "random_targets_uint64_bitwise_identical": base[
                "random_targets_uint64_bitwise_identical"
            ],
            "classification_E_serialization_caused_zero": classification_e,
            "classification_F_raw_float64_denominator_exact_zero": classification_f,
            "nonidentical_but_squared_underflow_to_zero": base[
                "nonidentical_but_squared_underflow_to_zero"
            ],
            "raw_store_target_bitwise_identity": True,
            "matched_random_sample_global_indices": random_global_string,
            "matched_random_identity_sha256": hashlib.sha256(
                np.ascontiguousarray(random_indices.astype("<i8")).tobytes()
            ).hexdigest(),
            "evidence_class": "CONSUMED_EVIDENCE_DIAGNOSTIC_ONLY",
        }
        for arm in ARMS:
            zero_records.append({**record, "arm": arm})

    zero_records.sort(
        key=lambda row: (
            row["arm"], row["component"], int(row["formal_case_index"]),
            int(row["particle_id"]),
        )
    )
    keys = [
        (row["arm"], row["component"], int(row["formal_case_index"]), int(row["particle_id"]))
        for row in zero_records
    ]
    if len(keys) != len(set(keys)):
        raise RuntimeError("duplicate zero-particle key")

    case_records: list[dict[str, Any]] = []
    for arm in ARMS:
        for component in COMPONENTS:
            subset = [
                row for row in zero_records
                if row["arm"] == arm and row["component"] == component
            ]
            for case_index in sorted({int(row["formal_case_index"]) for row in subset}):
                rows = [row for row in subset if int(row["formal_case_index"]) == case_index]
                first = rows[0]
                case_records.append(
                    {
                        "arm": arm,
                        "component": component,
                        "formal_case_index": case_index,
                        "case_id": first["case_id"],
                        "field_lineage_id": first["field_lineage_id"],
                        "fold": first["fold"],
                        "family": first["family"],
                        "zero_denominator_particle_count": len(rows),
                        "formal_particle_count": 128,
                        "zero_denominator_particle_fraction": len(rows) / 128.0,
                        "all_zero_rows_classification_F": all(
                            bool(row["classification_F_raw_float64_denominator_exact_zero"])
                            for row in rows
                        ),
                        "classification_A_B_status": "INCONCLUSIVE_INPUT_NOT_AUTHORIZED",
                        "evidence_class": "CONSUMED_EVIDENCE_DIAGNOSTIC_ONLY",
                    }
                )

    cell_records: list[dict[str, Any]] = []
    for arm in ARMS:
        for component in COMPONENTS:
            component_rows = [
                row for row in zero_records
                if row["arm"] == arm and row["component"] == component
            ]
            affected_cases = {int(row["formal_case_index"]) for row in component_rows}
            if len(affected_cases) != EXPECTED_CASE_COUNTS[component]:
                raise RuntimeError(
                    f"handoff case-count mismatch {arm} {component}: {len(affected_cases)}"
                )
            for family in FAMILIES:
                for fold in FOLDS:
                    population_cases = {
                        int(case["formal_case_index"])
                        for case in cases
                        if case["macro_family"] == family
                        and int(case["fold"].split("_")[1]) == fold
                    }
                    rows = [
                        row for row in component_rows
                        if row["family"] == family and row["fold"] == f"FOLD_{fold}"
                    ]
                    unique_cases = {int(row["formal_case_index"]) for row in rows}
                    unique_lineages = {str(row["field_lineage_id"]) for row in rows}
                    cell_records.append(
                        {
                            "arm": arm,
                            "component": component,
                            "family": family,
                            "fold": f"FOLD_{fold}",
                            "zero_denominator_particle_count": len(rows),
                            "formal_particle_count": len(population_cases) * 128,
                            "zero_denominator_particle_fraction": (
                                len(rows) / float(len(population_cases) * 128)
                                if population_cases else 0.0
                            ),
                            "affected_case_count_unique": len(unique_cases),
                            "formal_case_count": len(population_cases),
                            "affected_case_fraction": (
                                len(unique_cases) / float(len(population_cases))
                                if population_cases else 0.0
                            ),
                            "affected_lineage_count_unique": len(unique_lineages),
                        }
                    )

    component_summary: dict[str, dict[str, Any]] = {}
    for component in COMPONENTS:
        ss = [
            row for row in zero_records
            if row["arm"] == "SS" and row["component"] == component
        ]
        ms = [
            row for row in zero_records
            if row["arm"] == "MS" and row["component"] == component
        ]
        ss_keys = {(int(row["formal_case_index"]), int(row["particle_id"])) for row in ss}
        ms_keys = {(int(row["formal_case_index"]), int(row["particle_id"])) for row in ms}
        component_summary[component] = {
            "zero_denominator_particle_count_per_arm": len(ss),
            "formal_particle_count_per_arm": 49152,
            "zero_denominator_particle_fraction": len(ss) / 49152.0,
            "affected_case_count_unique": len({key[0] for key in ss_keys}),
            "formal_case_count": 384,
            "affected_case_fraction": len({key[0] for key in ss_keys}) / 384.0,
            "affected_lineage_count_unique": len({row["field_lineage_id"] for row in ss}),
            "affected_fold_count_unique": len({row["fold"] for row in ss}),
            "affected_family_count_unique": len({row["family"] for row in ss}),
            "ss_ms_zero_set_exactly_colocated": ss_keys == ms_keys,
            "classification_A_B_status": "INCONCLUSIVE_INPUT_NOT_AUTHORIZED",
            "classification_E_count": sum(
                bool(row["classification_E_serialization_caused_zero"]) for row in ss
            ),
            "classification_F_count": sum(
                bool(row["classification_F_raw_float64_denominator_exact_zero"]) for row in ss
            ),
        }

    all_f = all(
        bool(row["classification_F_raw_float64_denominator_exact_zero"])
        for row in zero_records
    )
    all_d = all(
        bool(row["classification_D_random_targets_numeric_exact_identical"])
        for row in zero_records
    )
    no_underflow = not any(
        bool(row["nonidentical_but_squared_underflow_to_zero"])
        for row in zero_records
    )
    mechanism_rows = [
        {
            "mechanism": "M1",
            "description": "physical_or_analytical_target_exact_degeneracy",
            "classification": "SUPPORTED" if all_f and all_d else "INCONCLUSIVE",
            "evidence": "raw_float64_replay_preserves_exact_target_equalities",
            "falsification_test": "raw_replay_denominator_nonzero_or_store_raw_identity_failure",
        },
        {
            "mechanism": "M2",
            "description": "manufactured_field_symmetry_or_nodal_zero_structure",
            "classification": "INCONCLUSIVE",
            "evidence": "exact_target_equalities_exist_but_symmetry_vs_repeated_value_not_yet_separated",
            "falsification_test": "map_raw_zero_and_nonzero_equalities_to_analytical_phase_and_node_classes",
        },
        {
            "mechanism": "M3",
            "description": "matched_random_sampling_construction_degeneracy",
            "classification": "SUPPORTED" if all_d else "INCONCLUSIVE",
            "evidence": "all_ten_frozen_random_targets_equal_query_for_each_zero_denominator",
            "falsification_test": "any_zero_denominator_with_nonidentical_random_target_without_underflow",
        },
        {
            "mechanism": "M4",
            "description": "case_or_family_stratification_creates_identical_target_matches",
            "classification": "NOT_SUPPORTED",
            "evidence": "matched_random_pool_is_not_family_stratified; only_fold_and_prohibited_identity_exclusions_apply",
            "falsification_test": "show_a_frozen_family_stratum_constraint_in_random_baseline_code",
        },
        {
            "mechanism": "M5",
            "description": "target_serialization_or_dtype_artifact",
            "classification": "NOT_SUPPORTED" if all_f else "SUPPORTED",
            "evidence": "raw_store_and_in_memory_NPZ_roundtrip_are_bitwise_identical",
            "falsification_test": "raw_denominator_positive_but_stored_denominator_zero",
        },
        {
            "mechanism": "M6",
            "description": "scalar_DNN_implementation_error_residual",
            "classification": "NOT_SUPPORTED" if all_f and no_underflow else "INCONCLUSIVE",
            "evidence": "denominator_replay_uses_frozen_scalar_vector_reductions_and_affects_scalar_and_vector_components",
            "falsification_test": "denominator_disappears_under_correct_frozen_rank_specific_reduction",
        },
        {
            "mechanism": "M7",
            "description": "other_including_square_underflow",
            "classification": "NOT_SUPPORTED" if no_underflow else "SUPPORTED",
            "evidence": "no_nonidentical_target_pair_squares_to_exact_zero" if no_underflow else "underflow_detected",
            "falsification_test": "find_nonidentical_comparator_with_zero_binary64_squared_distance",
        },
    ]
    for row in mechanism_rows:
        row.update(
            {
                "ss_ms_shared": all(
                    value["ss_ms_zero_set_exactly_colocated"]
                    for value in component_summary.values()
                ),
                "representation_independent": True,
                "field_family_concentrated": "SEE_FAMILY_FOLD_SUMMARY",
                "fold_concentrated": "SEE_FAMILY_FOLD_SUMMARY",
                "target_component_dependent": len(
                    {
                        value["affected_case_count_unique"]
                        for value in component_summary.values()
                    }
                ) > 1,
                "evidence_class": "CONSUMED_EVIDENCE_DIAGNOSTIC_ONLY",
            }
        )

    audit = {
        "schema_version": "1.0.0",
        "stage": "MSO-02C_G1",
        "status": "ATTRIBUTION_PARTIAL_INPUT_NOT_AUTHORIZED",
        "evidence_class": "CONSUMED_EVIDENCE_DIAGNOSTIC_ONLY",
        "source_contract_sha256": STATIC_HASHES[
            "00_project_contract/mso02c_dnn_degeneracy_diagnostic_contract.md"
        ],
        "source_commit": subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
            capture_output=True, text=True,
        ).stdout.strip(),
        "target_store_sha256": target_hash,
        "static_identity_sha256": static_actual,
        "runtime_fingerprint": {
            "python": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "torch": torch.__version__,
            "sklearn": sklearn.__version__,
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "byteorder": sys.byteorder,
            "pcg64_class": f"{np.random.PCG64.__module__}.{np.random.PCG64.__name__}",
        },
        "random_baseline_identity_sha256_by_fold": random_identity_hashes,
        "component_summary": component_summary,
        "raw_pre_serialization_target_replay_case_evaluations": len(raw_case_indices),
        "raw_replay_case_indices_sha256": hashlib.sha256(
            np.asarray(raw_case_indices, dtype="<i8").tobytes()
        ).hexdigest(),
        "serializer_roundtrip_bitwise_identity": serializer_roundtrip_bitwise,
        "raw_store_target_bitwise_identity": raw_store_bitwise,
        "authorized_access_counts": {
            "target_store_opaque_hash_reads_by_executable": 1,
            "target_store_payload_reads_by_executable": 1,
            "checkpoint_payload_reads_by_executable": 0,
            "metric_payload_reads_by_executable": 0,
            "bootstrap_identity_reads_by_executable": 0,
            "observable_store_opaque_hash_reads_by_executable": 0,
            "observable_store_payload_reads_by_executable": 0,
            "raw_frozen_target_replay_case_evaluations": len(raw_case_indices),
        },
        "manual_pre_execution_authorized_checkpoint_schema_reads": 1,
        "prohibited_action_counts": {
            "new_fresh_target_generation": 0,
            "new_confirmatory_h3_verdict": 0,
            "target_store_write": 0,
            "observable_store_read": 0,
            "case_deletion": 0,
            "case_replacement": 0,
            "neural_model": 0,
            "attention": 0,
            "optimizer": 0,
            "training": 0,
            "time_integration": 0,
            "solver_in_loop": 0,
            "rollout": 0,
            "sealed_test": 0,
            "arc_access": 0,
        },
        "attribution_blocker": (
            "descriptor-neighbour particle identities were not persisted in the authorized "
            "MSO-02B checkpoints; reconstructing them requires the unlisted observable payload"
        ),
        "candidate_performance_computed": False,
        "old_verdict_modified": False,
    }

    write_csv_atomic(PARTICLE_MAP, zero_records)
    write_csv_atomic(CASE_MAP, case_records)
    write_csv_atomic(CELL_SUMMARY, cell_records)
    write_csv_atomic(MECHANISM, mechanism_rows)
    write_json_atomic(AUDIT, audit)
    print("MSO02C_G1_ATTRIBUTION_PARTIAL_INPUT_NOT_AUTHORIZED", flush=True)


if __name__ == "__main__":
    main()
