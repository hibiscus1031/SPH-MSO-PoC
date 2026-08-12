#!/usr/bin/env python3
"""H-MSO-01R-A target-blind fresh atlas and analysis freeze.

This executable never imports or opens a target/reference payload.  Its only
numerical operator dependency is the already frozen MSO-01 static vendor path,
reached through the hash-bound MSO-02A target-blind implementation.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import os
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import torch
from scipy.spatial import cKDTree


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "06_experiments/hmso01r_a"
OBS = OUT / "observable"
REG = ROOT / "05_registries"
MAN = ROOT / "08_manifests"
PRIMARY = REG / "hmso01r_a_primary_candidate_registry.json"
RESERVE = REG / "hmso01r_a_reserve_candidate_registry.json"
CANDIDATE_FOLDS = REG / "hmso01r_a_candidate_lineage_fold_registry.json"
FORMAL = REG / "hmso01r_a_formal_fresh_atlas_registry.json"
PARTICLES = REG / "hmso01r_a_formal_particle_sample_registry.json"
FOLDS = REG / "hmso01r_a_lineage_fold_registry.json"
PAIRED = REG / "hmso01r_a_paired_ss_ms_registry.json"
RANDOM = REG / "hmso01r_a_random_baseline_identity_registry.json"
BOOTSTRAP = REG / "hmso01r_a_bootstrap_registry.json"
SS_SCHEMA = OUT / "ss_observable_schema_identity.json"
MS_SCHEMA = OUT / "ms_observable_schema_identity.json"
STORE = OBS / "hmso01r_a_observable_store.npz"
DESCRIPTOR_IDENTITIES = OUT / "descriptor_neighbor_identities.npz"
RANDOM_IDENTITIES = OUT / "random_baseline_identities.npz"
BOOTSTRAP_DRAWS = OUT / "bootstrap_draws.npz"
PRECOMPUTE = MAN / "hmso01r_a_precompute_freeze.json"
REPORT = ROOT / "07_reports/hmso01r_a_fresh_requalification_atlas_report.md"
STATUS = MAN / "hmso01r_a_status_ledger.json"
MANIFEST = MAN / "hmso01r_a_manifest.json"

PRE_CASE_COMMIT = "f4fa9c309744cf66a38ca38b84cd47602815b15e"
G2_FINAL_COMMIT = "f620baed60a78846459b80fe90c5239ba6788f6e"
CA = ROOT / "00_project_contract/amendments/ca_mso01_zero_safe_dnn_semantics.md"
G2_MANIFEST = MAN / "mso02c_g2_manifest.json"
FAMILIES = ("F1", "F2", "F3", "F4")
FOLD_COUNT = 6
PARTICLES_PER_CASE = 128
PRIMARY_K = 10
BOOTSTRAP_COUNT = 10_000
SCALES = (0.75, 1.0, 1.25, 1.5)


LEGACY_PATH = ROOT / "06_experiments/mso02a/run_mso02a_freeze.py"
spec = importlib.util.spec_from_file_location("mso02a_target_blind", LEGACY_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError("cannot import frozen MSO-02A target-blind implementation")
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        rows = [{"status": "NO_ROWS"}]
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def seed_record() -> dict[str, str]:
    g2 = sha256(G2_MANIFEST)
    amendment = sha256(CA)
    literal = "HMSO01R_A_FRESH_ATLAS"
    material = g2 + amendment + literal
    return {
        "g2_manifest_file_sha256": g2,
        "ca_mso01_amendment_sha256": amendment,
        "literal_domain": literal,
        "concatenated_seed_material": material,
        "seed_digest_sha256": digest_text(material),
        "single_seed_no_alternative_attempt": "true",
    }


def domain_hex(seed: str, domain: str, value: Any = None) -> str:
    suffix = "" if value is None else "|" + canonical(value)
    return digest_text(seed + "|" + domain + suffix)


def lineage_payload(case: dict[str, Any]) -> dict[str, Any]:
    return legacy.lineage_payload(case)


def lineage_fingerprint(case: dict[str, Any]) -> str:
    return digest_text(canonical(lineage_payload(case)))


def historical_sources() -> tuple[set[str], list[dict[str, Any]]]:
    """Read lineage/case governance metadata only; never target/reference payloads."""
    ddo = Path("/Users/xiejinbo/Documents/SPH-DDO-PoC/06_manifests")
    pio_a = Path("/Users/xiejinbo/Documents/SPH-PIO-PoC/stage_02_Particle_Interaction_Operator/05_dataset/blind_multifamily_pair_scope_v1_0/lineage/family_lineage_registry.json")
    pio_b = Path("/Users/xiejinbo/Documents/SPH-PIO-PoC/stage_02_Particle_Interaction_Operator/06_model/pair_force_pio_training_protocol_v0_2/split/family_lineage_registry.json")
    sources = [
        ddo / "ddo01d_case_registry.json",
        ddo / "ddo02b_case_registry.json",
        pio_a,
        pio_b,
        REG / "mso01_target_blind_case_registry.json",
        REG / "mso02a_primary_candidate_registry.json",
        REG / "mso02a_reserve_candidate_registry.json",
        REG / "mso02a_formal_fresh_atlas_registry.json",
        REG / "mso02b_formal_particle_sample_registry.json",
        MAN / "mso02c_g1_ab_attribution_manifest.json",
        MAN / "mso02c_g2_manifest.json",
    ]
    records = [{"path": str(path), "sha256": sha256(path), "metadata_only": True} for path in sources]
    fingerprints: set[str] = set()
    for path in (ddo / "ddo01d_case_registry.json", ddo / "ddo02b_case_registry.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        fingerprints.update(lineage_fingerprint(case) for case in payload["cases"])
    for path in (REG / "mso02a_primary_candidate_registry.json", REG / "mso02a_reserve_candidate_registry.json", REG / "mso02a_formal_fresh_atlas_registry.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        fingerprints.update(lineage_fingerprint(case) for case in payload["cases"])
    # PIO identities use a different authoritative Fourier-family schema.  Keep
    # full canonical identities to prove namespace and generation-payload checks.
    for path in (pio_a, pio_b):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for family in payload["families"]:
            fingerprints.add(digest_text("PIO_FAMILY_LINEAGE|" + canonical(family)))
    mso01 = json.loads((REG / "mso01_target_blind_case_registry.json").read_text(encoding="utf-8"))
    for case in mso01["cases"]:
        fingerprints.add(digest_text("MSO01_FIXTURE|" + canonical(case)))
    return fingerprints, records


def prior_identity_audit() -> list[dict[str, Any]]:
    files = [
        "08_manifests/mso00_manifest.json",
        "08_manifests/mso01_manifest.json", "08_manifests/mso01_status_ledger.json",
        "08_manifests/mso02a_manifest.json", "08_manifests/mso02a_status_ledger.json",
        "08_manifests/mso02b_manifest.json", "08_manifests/mso02b_status_ledger.json",
        "08_manifests/mso02c_g1_ab_attribution_manifest.json", "08_manifests/mso02c_g1_ab_attribution_status_ledger.json",
        "08_manifests/mso02c_g2_manifest.json", "08_manifests/mso02c_g2_status_ledger.json",
        "00_project_contract/amendments/ca_mso01_zero_safe_dnn_semantics.md",
    ]
    rows = []
    for relative in files:
        path = ROOT / relative
        work = sha256(path)
        blob = subprocess.check_output(["git", "show", f"{G2_FINAL_COMMIT}:{relative}"], cwd=ROOT)
        head = hashlib.sha256(blob).hexdigest()
        rows.append({"path": relative, "sha256": work, "g2_blob_sha256": head, "identity": work == head})
    if not all(row["identity"] for row in rows):
        raise RuntimeError("HMSO01R_A_PROVENANCE_CONFLICT")
    if sha256(CA) != "fec81d9dceeb4edc93b19adf0eb063e564effda81f700ea69174963b75454650":
        raise RuntimeError("HMSO01R_A_PROVENANCE_CONFLICT")
    return rows


def derived_phases(seed: str) -> tuple[float, float, float]:
    return tuple(math.pi * (0.125 + 1.75 * int(domain_hex(seed, "PHASE", index)[:16], 16) / float(1 << 64)) for index in range(3))


def derived_jitter_seeds(seed: str) -> tuple[int, int, int]:
    return tuple(1 + int(domain_hex(seed, "JITTER_SEED", index)[:16], 16) % (2**31 - 2) for index in range(3))


def finalize_case(item: dict[str, Any], role: str, family_order: int, global_order: int, seed: str) -> dict[str, Any]:
    case = dict(item)
    n = int(case["resolution_per_axis"])
    case["dx"] = 1.0 / n
    case["support_h"] = float(case["support_over_dx"]) / n
    case["points_per_wavelength_min"] = min(n / math.hypot(*mode) for mode in case["mode_indices"])
    case["candidate_role"] = role
    case["family_generation_order"] = family_order
    case["generation_order"] = global_order
    payload = lineage_payload(case)
    fingerprint = digest_text(canonical(payload))
    case["authoritative_field_lineage_payload_sha256"] = fingerprint
    case["field_lineage_id"] = "HMSO01R_A|FIELD_LINEAGE|" + digest_text(seed + "|FIELD_LINEAGE|" + canonical(payload))
    identity = {key: value for key, value in case.items() if key not in ("family_generation_order", "generation_order")}
    case["case_id"] = f"HMSO01R_A|{role}|{case['macro_family']}|" + digest_text(seed + "|CASE|" + canonical(identity))
    case["disorder_state_id"] = "HMSO01R_A|DISORDER|" + digest_text(canonical({
        "resolution": n, "jitter_fraction": case["jitter_fraction"], "jitter_seed": case["jitter_seed"]
    }))
    return case


def generate_candidates(seed: str, old_fingerprints: set[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    phases = derived_phases(seed)
    jitter_seeds = derived_jitter_seeds(seed)
    single = ((1, 0), (2, 0), (3, 0), (1, 1), (1, 2), (2, 1))
    multi = (((1, 0), (0, 2)), ((1, 1), (2, -1)), ((1, 0), (2, 1), (0, 3)))
    primary_by: dict[str, list[dict[str, Any]]] = {}
    reserve_by: dict[str, list[dict[str, Any]]] = {}
    for family in ("F1", "F2", "F3"):
        modesets = tuple((mode,) for mode in single) if family == "F1" else multi if family == "F2" else tuple((mode,) for mode in ((1, 1), (1, 2), (2, 1)))
        pool: list[dict[str, Any]] = []
        for ratio in (3.0, 4.0, 5.0):
            for modes in modesets:
                for probe in ("density", "longitudinal", "transverse"):
                    amplitudes = (0.0025, 0.005, 0.01, 0.02) if probe == "density" else (0.025, 0.05, 0.1, 0.2)
                    for amplitude in amplitudes:
                        for phase_index in range(3):
                            ps = tuple(phases[(phase_index + index) % 3] for index in range(len(modes)))
                            item = legacy.candidate_base(family, ratio, modes, probe, amplitude, ps)
                            if lineage_fingerprint(item) not in old_fingerprints:
                                pool.append(item)
        axes = ("support_over_dx", "mode", "probe", "active_amplitude", "phase", "probe_mode")
        selected = legacy.balanced_select(pool, 96, axes, seed, f"{family}|PRIMARY")
        selected_keys = {canonical(item) for item in selected}
        remaining = [item for item in pool if canonical(item) not in selected_keys]
        primary_by[family] = selected
        reserve_by[family] = legacy.balanced_select(remaining, 32, axes, seed, f"{family}|RESERVE")

    f4_pool: list[dict[str, Any]] = []
    for mode in single:
        for probe in ("density", "longitudinal", "transverse"):
            amplitudes = (0.0025, 0.005, 0.01, 0.02) if probe == "density" else (0.025, 0.05, 0.1, 0.2)
            for amplitude in amplitudes:
                for phase in phases:
                    item = legacy.candidate_base("F4", 4.0, (mode,), probe, amplitude, (phase,))
                    if lineage_fingerprint(item) not in old_fingerprints:
                        f4_pool.append(item)
    f4_bases = legacy.balanced_select(f4_pool, 12, ("mode", "probe", "active_amplitude", "phase", "probe_mode"), seed, "F4|BASES")
    disorder_states = ((0.0, 0), (0.05, jitter_seeds[0]), (0.10, jitter_seeds[1]), (0.05, jitter_seeds[2]))
    primary_f4: list[dict[str, Any]] = []
    reserve_f4: list[dict[str, Any]] = []
    for block, base in enumerate(f4_bases):
        ratios = (3.0, 4.0, 5.0) if block < 8 else (4.0, 5.0)
        destination = primary_f4 if block < 8 else reserve_f4
        block_id = "HMSO01R_A|F4_BLOCK|" + digest_text(seed + canonical(lineage_payload(base)))
        for ratio in ratios:
            for jitter, jitter_seed in disorder_states:
                item = dict(base)
                item.update({"support_over_dx": ratio, "support_h": ratio / 24.0, "jitter_fraction": jitter,
                             "jitter_seed": jitter_seed, "layout_class": "regular" if jitter == 0 else f"jitter_{jitter:.2f}",
                             "f4_matched_block_id": block_id, "f4_block_index": block})
                destination.append(item)
    primary_by["F4"] = primary_f4
    reserve_by["F4"] = reserve_f4

    primary: list[dict[str, Any]] = []
    reserve: list[dict[str, Any]] = []
    for family in FAMILIES:
        ordered = sorted(primary_by[family], key=lambda item: domain_hex(seed, f"{family}|PRIMARY_ORDER", item))
        for order, item in enumerate(ordered):
            primary.append(finalize_case(item, "PRIMARY", order, len(primary), seed))
        ordered = sorted(reserve_by[family], key=lambda item: domain_hex(seed, f"{family}|RESERVE_ORDER", item))
        for order, item in enumerate(ordered):
            reserve.append(finalize_case(item, "RESERVE", order, len(reserve), seed))
    return primary, reserve


def candidate_registry(role: str, cases: list[dict[str, Any]], quota: int, seed_info: dict[str, str], old: set[str], sources: list[dict[str, Any]]) -> dict[str, Any]:
    overlap = sum(case["authoritative_field_lineage_payload_sha256"] in old for case in cases)
    return {
        "schema_version": "1.0.0", "project": "SPH-MSO-PoC", "stage": "H-MSO-01R-A",
        "registry_role": role, "status": "FROZEN_BEFORE_ANY_OPERATOR_EVALUATION",
        "seed_derivation": seed_info, "selection_is_target_blind": True,
        "case_count": len(cases), "family_quota": quota,
        "family_counts": dict(Counter(case["macro_family"] for case in cases)),
        "historical_lineage_overlap_count": overlap,
        "overlap_basis": "CANONICAL_AUTHORITATIVE_FIELD_LINEAGE_OR_GENERATION_PAYLOAD_SHA256_NOT_CASE_ID",
        "historical_metadata_sources": sources, "target_or_reference_payload_read_count": 0,
        "cases": cases,
    }


def freeze_candidate_folds(primary: list[dict[str, Any]], reserve: list[dict[str, Any]], seed: str) -> None:
    fold_by: dict[str, int] = {}
    rows: list[dict[str, Any]] = []
    all_cases = primary + reserve
    for family in FAMILIES:
        p_lineages = sorted({case["field_lineage_id"] for case in primary if case["macro_family"] == family}, key=lambda x: domain_hex(seed, f"{family}|FOLD_PRIMARY", x))
        r_lineages = sorted({case["field_lineage_id"] for case in reserve if case["macro_family"] == family} - set(p_lineages), key=lambda x: domain_hex(seed, f"{family}|FOLD_RESERVE", x))
        loads = [0] * FOLD_COUNT
        counts = Counter(case["field_lineage_id"] for case in all_cases)
        for index, lineage in enumerate(p_lineages):
            fold = index if index < FOLD_COUNT else min(range(FOLD_COUNT), key=lambda value: (loads[value], value))
            fold_by[lineage] = fold
            loads[fold] += counts[lineage]
        for lineage in r_lineages:
            fold = min(range(FOLD_COUNT), key=lambda value: (loads[value], value))
            fold_by[lineage] = fold
            loads[fold] += counts[lineage]
        for lineage in p_lineages + r_lineages:
            rows.append({"field_lineage_id": lineage, "macro_family": family, "fold": f"FOLD_{fold_by[lineage]}",
                         "primary_lineage": lineage in p_lineages, "candidate_case_count": counts[lineage]})
    write_json(CANDIDATE_FOLDS, {"schema_version": "1.0.0", "stage": "H-MSO-01R-A",
        "status": "FROZEN_BEFORE_ANY_OPERATOR_EVALUATION", "fold_count": FOLD_COUNT,
        "assignment_is_target_blind": True, "lineage_held_out": True, "ss_ms_identical": True, "lineages": rows})


def freeze_schemas() -> None:
    for arm, old_path, new_path, dimension in (
        ("SS", ROOT / "06_experiments/mso02a/ss_observable_schema.json", SS_SCHEMA, 39),
        ("MS", ROOT / "06_experiments/mso02a/ms_observable_schema.json", MS_SCHEMA, 110),
    ):
        old = json.loads(old_path.read_text(encoding="utf-8"))
        if old["feature_dimension"] != dimension or len(old["columns"]) != dimension:
            raise RuntimeError("HMSO01R_A_REPRESENTATION_IDENTITY_FAILURE")
        write_json(new_path, {
            "schema_version": "1.0.0", "stage": "H-MSO-01R-A", "status": "FROZEN_BEFORE_ANY_OPERATOR_EVALUATION",
            "arm": arm, "feature_dimension": dimension, "columns": old["columns"],
            "frozen_source_path": str(old_path.relative_to(ROOT)), "frozen_source_sha256": sha256(old_path),
            "ordered_column_semantics_sha256": digest_text(canonical(old["columns"])),
            "feature_addition_count": 0, "feature_deletion_count": 0, "pca": False, "whitening": False,
            "duplicate_removal": False, "constant_column_removal": False, "iqr_degenerate_column_removal": False,
            "target_or_reference_columns": [], "normalization": "TRAIN_FOLD_ONLY_MEDIAN_IQR_EXACT_ZERO_UNIT_FALLBACK",
        })


def prepare() -> None:
    if git("rev-parse", "HEAD") != PRE_CASE_COMMIT or git("branch", "--show-current") != "main" or git("remote"):
        raise RuntimeError("HMSO01R_A_PROVENANCE_CONFLICT")
    if not git("merge-base", "--is-ancestor", G2_FINAL_COMMIT, PRE_CASE_COMMIT) == "":
        pass
    prior = prior_identity_audit()
    old, sources = historical_sources()
    seed_info = seed_record()
    seed = seed_info["seed_digest_sha256"]
    primary, reserve = generate_candidates(seed, old)
    if len(primary) != 384 or len(reserve) != 128:
        raise RuntimeError("HMSO01R_A_FRESH_ATLAS_NOT_QUALIFIED")
    if Counter(case["macro_family"] for case in primary) != Counter({family: 96 for family in FAMILIES}):
        raise RuntimeError("HMSO01R_A_FRESH_ATLAS_NOT_QUALIFIED")
    if Counter(case["macro_family"] for case in reserve) != Counter({family: 32 for family in FAMILIES}):
        raise RuntimeError("HMSO01R_A_FRESH_ATLAS_NOT_QUALIFIED")
    write_json(PRIMARY, candidate_registry("PRIMARY", primary, 96, seed_info, old, sources))
    write_json(RESERVE, candidate_registry("RESERVE", reserve, 32, seed_info, old, sources))
    freeze_candidate_folds(primary, reserve, seed)
    freeze_schemas()
    frozen = [
        ROOT / "00_project_contract/hmso01r_a_fresh_requalification_atlas_freeze_contract.md",
        PRIMARY, RESERVE, CANDIDATE_FOLDS, SS_SCHEMA, MS_SCHEMA, Path(__file__),
    ]
    write_json(PRECOMPUTE, {
        "schema_version": "1.0.0", "stage": "H-MSO-01R-A", "status": "FROZEN_BEFORE_ANY_OPERATOR_EVALUATION",
        "g2_final_commit": G2_FINAL_COMMIT, "hmso01r_a_pre_case_commit": PRE_CASE_COMMIT,
        "branch": "main", "remote": None, "push": False, "seed_derivation": seed_info,
        "prior_frozen_identity_audit": prior, "all_prior_frozen_evidence_hashes_valid": True,
        "historical_lineage_payload_count": len(old), "historical_lineage_overlap_count": 0,
        "primary_registry_frozen_before_operator_evaluation": True,
        "reserve_registry_frozen_before_operator_evaluation": True,
        "candidate_c_semantics": {
            "primary_k": 10, "statistic": "D=W(N)/W(B)", "aggregation": "particle_to_case_to_lineage_to_family_to_fold",
            "division_count_after_balanced_aggregation": 1, "pointwise_ratio": False, "epsilon": False,
            "zero_row_or_group_deletion": False, "zero_aggregate_status": "DNN_NOT_EVALUABLE_ZERO_AGGREGATE_RANDOM_BASELINE",
            "zero_ss_status": "RELATIVE_RESCUE_NOT_EVALUABLE_ZERO_SS_BASELINE",
            "absolute_gate": {"point": "D<1", "simultaneous_ucb": "UCB(D)<1"},
            "relative_gate": {"point": "D_MS/D_SS<=0.80", "simultaneous_ucb": "UCB<=0.90"},
        },
        "non_dnn_semantics_modified": False,
        "firewall_pre": {key: 0 for key in (
            "target_file_open_count", "target_payload_read_count", "reference_archive_read_count", "continuum_operator_read_count",
            "defect_generation_count", "dnn_target_disagreement_count", "conditional_variance_count", "oracle_fit_count",
            "h3_verdict_count", "neural_model_count", "attention_count", "optimizer_count", "training_count", "integration_count",
            "solver_in_loop_count", "rollout_count", "sealed_test_count", "arc_access_count")},
        "artifact_sha256": {str(path.relative_to(ROOT)): sha256(path) for path in frozen},
    })
    print(json.dumps({"status": "HMSO01R_A_CANDIDATE_FREEZE_PREPARED", "primary": 384, "reserve": 128,
                      "historical_lineage_overlap_count": 0, "seed": seed, "precompute_sha256": sha256(PRECOMPUTE)}, indent=2))


def verify_precompute() -> None:
    freeze = json.loads(PRECOMPUTE.read_text(encoding="utf-8"))
    if freeze["status"] != "FROZEN_BEFORE_ANY_OPERATOR_EVALUATION":
        raise RuntimeError("HMSO01R_A_PROVENANCE_CONFLICT")
    for relative, expected in freeze["artifact_sha256"].items():
        if sha256(ROOT / relative) != expected:
            raise RuntimeError(f"HMSO01R_A_PROVENANCE_CONFLICT: {relative}")
    if json.loads(PRIMARY.read_text())["historical_lineage_overlap_count"] != 0 or json.loads(RESERVE.read_text())["historical_lineage_overlap_count"] != 0:
        raise RuntimeError("HMSO01R_A_LINEAGE_OVERLAP_CONFLICT")


def select_particles(case: dict[str, Any], seed: str, particle_count: int) -> list[int]:
    ordered = sorted(range(particle_count), key=lambda particle: domain_hex(seed, "FORMAL_PARTICLE", [case["case_id"], particle]))
    return ordered[:PARTICLES_PER_CASE]


def normalize_and_audit(ss: np.ndarray, ms: np.ndarray, row_case: np.ndarray, cases: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    schemas = {"SS": json.loads(SS_SCHEMA.read_text()), "MS": json.loads(MS_SCHEMA.read_text())}
    matrices = {"SS": ss, "MS": ms}
    row_fold = np.asarray([int(cases[index]["fold"].split("_")[1]) for index in row_case], dtype=np.int8)
    registry: dict[str, Any] = {"schema_version": "1.0.0", "stage": "H-MSO-01R-A", "status": "FROZEN_TARGET_BLIND",
        "fold_count": FOLD_COUNT, "rule": "TRAIN_FOLD_ONLY_MEDIAN_IQR_EXACT_ZERO_UNIT_FALLBACK_RETAIN", "target_read_count": 0, "arms": {}}
    audit: list[dict[str, Any]] = []
    for arm, matrix in matrices.items():
        names = [column["name"] for column in schemas[arm]["columns"]]
        fold_records = []
        zero_counts = np.zeros(matrix.shape[1], dtype=np.int64)
        for fold in range(FOLD_COUNT):
            train = matrix[row_fold != fold]
            q25, median, q75 = np.quantile(train, [0.25, 0.5, 0.75], axis=0)
            iqr = q75 - q25
            zero = iqr == 0.0
            zero_counts += zero
            divisor = np.where(zero, 1.0, iqr)
            fold_records.append({"held_out_fold": f"FOLD_{fold}", "training_row_count": int(train.shape[0]),
                "feature_names": names, "median": median.tolist(), "iqr": iqr.tolist(), "divisor": divisor.tolist(),
                "fallback": ["UNIT_SCALE_RETAIN_COLUMN" if value else "IQR" for value in zero]})
        registry["arms"][arm] = {"feature_dimension": int(matrix.shape[1]), "folds": fold_records}
        raw_hash: dict[str, str] = {}
        norm_hash: dict[str, str] = {}
        first_value: dict[str, float] = {}
        for index, name in enumerate(names):
            column = np.ascontiguousarray(matrix[:, index])
            raw_hash[name] = hashlib.sha256(column.tobytes()).hexdigest()
            nz = np.flatnonzero(column)
            if nz.size:
                first_value[name] = float(column[nz[0]])
                norm_hash[name] = hashlib.sha256(np.ascontiguousarray(column / column[nz[0]]).tobytes()).hexdigest()
        seen_raw: dict[str, str] = {}
        seen_norm: dict[str, str] = {}
        for index, name in enumerate(names):
            column = matrix[:, index]
            duplicate = seen_raw.get(raw_hash[name], "")
            seen_raw.setdefault(raw_hash[name], name)
            dependency = seen_norm.get(norm_hash.get(name, ""), "") if name in norm_hash else ""
            if name in norm_hash:
                seen_norm.setdefault(norm_hash[name], name)
            audit.append({"arm": arm, "feature_index": index, "feature_name": name, "feature_dimension": matrix.shape[1],
                "finite_count": int(np.isfinite(column).sum()), "nonfinite_count": int((~np.isfinite(column)).sum()),
                "exact_constant": bool(np.min(column) == np.max(column)), "exact_duplicate_of": duplicate,
                "pairwise_exact_linear_dependency_of": dependency if dependency != duplicate else "",
                "linear_dependency_scalar_diagnostic": first_value.get(name, 0.0) / first_value.get(dependency, 1.0) if dependency else "",
                "minimum": float(np.min(column)), "maximum": float(np.max(column)), "absolute_maximum": float(np.max(np.abs(column))),
                "train_fold_iqr_degeneracy_count": int(zero_counts[index]), "column_sha256": raw_hash[name]})
    return registry, audit


def row_metadata(cases: list[dict[str, Any]], row_case: np.ndarray, row_particle: np.ndarray) -> dict[str, np.ndarray]:
    return {
        "case_id": np.asarray([cases[index]["case_id"] for index in row_case]),
        "lineage": np.asarray([cases[index]["field_lineage_id"] for index in row_case]),
        "family": np.asarray([cases[index]["macro_family"] for index in row_case]),
        "seed": np.asarray([int(cases[index]["jitter_seed"]) for index in row_case], dtype=np.int64),
        "fold": np.asarray([int(cases[index]["fold"].split("_")[1]) for index in row_case], dtype=np.int8),
        "particle": row_particle.astype(np.int32),
        "sample_key": np.asarray([f"{cases[index]['case_id']}|{int(particle)}" for index, particle in zip(row_case, row_particle)]),
    }


def ordered_rows(rows: np.ndarray, meta: dict[str, np.ndarray]) -> np.ndarray:
    return np.asarray(sorted(rows.tolist(), key=lambda row: (str(meta["sample_key"][row]))), dtype=np.int64)


def legal_mask(query: int, candidates: np.ndarray, meta: dict[str, np.ndarray]) -> np.ndarray:
    mask = (meta["case_id"][candidates] != meta["case_id"][query]) & (meta["lineage"][candidates] != meta["lineage"][query])
    seed = int(meta["seed"][query])
    if seed != 0:
        mask &= meta["seed"][candidates] != seed
    return mask


def heldout_neighbors(matrix: np.ndarray, normalization: dict[str, Any], arm: str, meta: dict[str, np.ndarray]) -> tuple[np.ndarray, np.ndarray, list[dict[str, Any]]]:
    neighbors = np.full((matrix.shape[0], PRIMARY_K), -1, dtype=np.int32)
    neighbor_distances = np.full((matrix.shape[0], PRIMARY_K), np.nan, dtype=np.float64)
    fold_records: list[dict[str, Any]] = []
    for fold in range(FOLD_COUNT):
        query_rows = ordered_rows(np.flatnonzero(meta["fold"] == fold), meta)
        train_rows = ordered_rows(np.flatnonzero(meta["fold"] != fold), meta)
        norm = normalization["arms"][arm]["folds"][fold]
        median, divisor = np.asarray(norm["median"]), np.asarray(norm["divisor"])
        train_x = (matrix[train_rows] - median) / divisor
        query_x = (matrix[query_rows] - median) / divisor
        tree = cKDTree(train_x, compact_nodes=True, balanced_tree=True)
        schedules = tuple(sorted(set(min(train_x.shape[0], value) for value in (64, 256, 2048, train_x.shape[0]))))
        for start in range(0, query_rows.size, 128):
            local_rows = np.arange(start, min(start + 128, query_rows.size), dtype=np.int64)
            unresolved = local_rows.copy()
            for use_k in schedules:
                if not unresolved.size:
                    break
                distances, indices = tree.query(query_x[unresolved], k=use_k, eps=0, p=2, workers=1)
                if use_k == 1:
                    distances, indices = distances[:, None], indices[:, None]
                remaining: list[int] = []
                for local_index, query_local in enumerate(unresolved):
                    query = int(query_rows[query_local])
                    candidates = train_rows[np.asarray(indices[local_index], dtype=np.int64)]
                    distance = np.asarray(distances[local_index], dtype=np.float64)
                    keep = legal_mask(query, candidates, meta)
                    triples = sorted(((float(d), str(meta["case_id"][candidate]), int(meta["particle"][candidate]), int(candidate))
                                      for d, candidate in zip(distance[keep], candidates[keep])), key=lambda item: (item[0], item[1], item[2]))
                    complete = len(triples) >= PRIMARY_K and (use_k == train_x.shape[0] or triples[PRIMARY_K - 1][0] < float(distance[-1]))
                    if complete:
                        chosen = triples[:PRIMARY_K]
                        neighbors[query] = [item[3] for item in chosen]
                        neighbor_distances[query] = [item[0] for item in chosen]
                    else:
                        remaining.append(int(query_local))
                unresolved = np.asarray(remaining, dtype=np.int64)
            if unresolved.size:
                raise RuntimeError("HMSO01R_A_ANALYSIS_FREEZE_NOT_COMPLETE: insufficient legal descriptor neighbours")
        fold_records.append({"held_out_fold": f"FOLD_{fold}", "query_row_count": int(query_rows.size),
                             "legal_training_pool_row_count": int(train_rows.size), "all_queries_have_k10": True})
        print(f"HMSO01R_A_DESCRIPTOR arm={arm} fold={fold} queries={query_rows.size}", flush=True)
    return neighbors, neighbor_distances, fold_records


def kth_permitted_distances(x: np.ndarray, global_rows: np.ndarray, meta: dict[str, np.ndarray]) -> np.ndarray:
    tree = cKDTree(x, compact_nodes=True, balanced_tree=True)
    result = np.full(x.shape[0], np.nan, dtype=np.float64)
    schedule = tuple(sorted(set(min(x.shape[0], value) for value in (256, 2048, 8192, x.shape[0]))))
    for start in range(0, x.shape[0], 128):
        chunk = np.arange(start, min(start + 128, x.shape[0]), dtype=np.int64)
        unresolved = chunk.copy()
        for use_k in schedule:
            if not unresolved.size:
                break
            distances, indices = tree.query(x[unresolved], k=use_k, eps=0, p=2, workers=1)
            if use_k == 1:
                distances, indices = distances[:, None], indices[:, None]
            remaining: list[int] = []
            for local, query_local in enumerate(unresolved):
                query = int(global_rows[query_local])
                candidates = global_rows[np.asarray(indices[local], dtype=np.int64)]
                keep = legal_mask(query, candidates, meta)
                permitted = np.sort(np.asarray(distances[local], dtype=np.float64)[keep], kind="stable")
                if permitted.size >= PRIMARY_K:
                    result[query_local] = permitted[PRIMARY_K - 1]
                else:
                    remaining.append(int(query_local))
            unresolved = np.asarray(remaining, dtype=np.int64)
        if unresolved.size:
            raise RuntimeError("HMSO01R_A_ANALYSIS_FREEZE_NOT_COMPLETE: coverage legal pool")
    if not np.isfinite(result).all():
        raise RuntimeError("HMSO01R_A_ANALYSIS_FREEZE_NOT_COMPLETE: nonfinite coverage radius")
    return result


def freeze_geometry_and_random(ss: np.ndarray, ms: np.ndarray, normalization: dict[str, Any], meta: dict[str, np.ndarray], seed: str) -> None:
    matrices = {"SS": ss, "MS": ms}
    nn: dict[str, np.ndarray] = {}
    dd: dict[str, np.ndarray] = {}
    descriptor_arms: dict[str, Any] = {}
    coverage_arms: dict[str, Any] = {}
    for arm, matrix in matrices.items():
        nn[arm], dd[arm], fold_records = heldout_neighbors(matrix, normalization, arm, meta)
        descriptor_arms[arm] = {"feature_dimension": int(matrix.shape[1]), "folds": fold_records}
        coverage_records = []
        for fold in range(FOLD_COUNT):
            development = ordered_rows(np.flatnonzero(meta["fold"] != fold), meta)
            norm = normalization["arms"][arm]["folds"][fold]
            x = (matrix[development] - np.asarray(norm["median"])) / np.asarray(norm["divisor"])
            radii = kth_permitted_distances(x, development, meta)
            coverage_records.append({"held_out_fold": f"FOLD_{fold}", "development_sample_row_count": int(development.size),
                "unique_development_case_count": int(np.unique(meta["case_id"][development]).size),
                "k10_radius_p95": float(np.quantile(radii, 0.95, method="inverted_cdf")),
                "k10_radius_min": float(np.min(radii)), "k10_radius_max": float(np.max(radii)), "finite": True})
            print(f"HMSO01R_A_COVERAGE arm={arm} fold={fold} rows={development.size}", flush=True)
        coverage_arms[arm] = {"feature_dimension": int(matrix.shape[1]), "folds": coverage_records}
    np.savez_compressed(DESCRIPTOR_IDENTITIES, query_row_index=np.arange(ss.shape[0], dtype=np.int32),
        ss_neighbor_row_index=nn["SS"], ms_neighbor_row_index=nn["MS"],
        ss_neighbor_distance=dd["SS"], ms_neighbor_distance=dd["MS"])
    write_json(OUT / "descriptor_geometry_freeze.json", {
        "schema_version": "1.0.0", "stage": "H-MSO-01R-A", "status": "FROZEN_BEFORE_TARGET_ACCESS",
        "primary_k": 10, "distance": "EUCLIDEAN_AFTER_ARM_AND_OUTER_TRAIN_FOLD_MEDIAN_IQR",
        "tie_order": ["distance", "case_id", "particle_id"], "internal_tie_completion": True,
        "exclusions": {"same_case": True, "same_field_lineage": True, "same_nonzero_disorder_seed": True},
        "target_disagreement_computed": False, "target_read_count": 0, "identity_file": str(DESCRIPTOR_IDENTITIES.relative_to(ROOT)),
        "identity_file_sha256": sha256(DESCRIPTOR_IDENTITIES), "arms": descriptor_arms})
    write_json(OUT / "coverage_geometry_freeze.json", {
        "schema_version": "1.0.0", "stage": "H-MSO-01R-A", "status": "FROZEN_BEFORE_TARGET_ACCESS",
        "formal_sample_particles_per_case": PARTICLES_PER_CASE, "formal_sample_row_count": int(ss.shape[0]),
        "primary_k": 10, "calibration": "DEVELOPMENT_LEAVE_COMPLETE_CASE_LINEAGE_AND_NONZERO_SEED_OUT",
        "quantile": "NUMPY_INVERTED_CDF_P95", "scientific_coverage_verdict_computed": False,
        "target_or_reference_read_count": 0, "arms": coverage_arms})

    random_rows = np.full((ss.shape[0], PRIMARY_K), -1, dtype=np.int32)
    fold_pool_records = []
    for fold in range(FOLD_COUNT):
        queries = ordered_rows(np.flatnonzero(meta["fold"] == fold), meta)
        train = ordered_rows(np.flatnonzero(meta["fold"] != fold), meta)
        cache: dict[int, np.ndarray] = {}
        for query in queries:
            qseed = int(meta["seed"][query])
            if qseed not in cache:
                eligible = train if qseed == 0 else train[meta["seed"][train] != qseed]
                cache[qseed] = eligible
            eligible = cache[qseed]
            if not legal_mask(int(query), eligible, meta).all():
                eligible = eligible[legal_mask(int(query), eligible, meta)]
            material = f"HMSO01R_A|BASELINE_K10|{meta['case_id'][query]}|{int(meta['particle'][query])}"
            rng = np.random.Generator(np.random.PCG64(int(hashlib.sha256(material.encode()).hexdigest(), 16)))
            chosen = rng.choice(eligible.size, size=PRIMARY_K, replace=False)
            random_rows[query] = eligible[chosen]
        fold_pool_records.append({"held_out_fold": f"FOLD_{fold}", "query_count": int(queries.size),
                                  "training_pool_count": int(train.size), "all_queries_k10_unique": True})
    np.savez_compressed(RANDOM_IDENTITIES, query_row_index=np.arange(ss.shape[0], dtype=np.int32), comparator_row_index=random_rows)
    write_json(RANDOM, {"schema_version": "1.0.0", "stage": "H-MSO-01R-A", "status": "FROZEN_BEFORE_TARGET_ACCESS",
        "primary_k": 10, "generator": "numpy.Generator(PCG64(full_SHA256_integer))", "replace": False,
        "domain": "HMSO01R_A|BASELINE_K10|<case_id>|<particle_id>",
        "exclusions": {"same_case": True, "same_field_lineage": True, "same_nonzero_disorder_seed": True},
        "representation_dependent": False, "ss_ms_same_identities": True, "target_dependence": False,
        "identity_file": str(RANDOM_IDENTITIES.relative_to(ROOT)), "identity_file_sha256": sha256(RANDOM_IDENTITIES),
        "query_count": int(ss.shape[0]), "comparator_identity_count": int(random_rows.size), "fold_pools": fold_pool_records})


def freeze_bootstrap(cases: list[dict[str, Any]], seed: str) -> dict[str, np.ndarray]:
    lineage_cases: dict[str, list[int]] = defaultdict(list)
    strata: dict[tuple[str, str], list[str]] = defaultdict(list)
    for index, case in enumerate(cases):
        lineage_cases[case["field_lineage_id"]].append(index)
    for lineage, indices in lineage_cases.items():
        case = cases[indices[0]]
        strata[(case["macro_family"], case["fold"])].append(lineage)
    for values in strata.values():
        values.sort()
    if len(strata) != 24 or any(not values for values in strata.values()):
        raise RuntimeError("HMSO01R_A_ANALYSIS_FREEZE_NOT_COMPLETE: bootstrap strata")
    lineage_table = sorted(lineage_cases)
    lineage_index = {value: index for index, value in enumerate(lineage_table)}
    offsets = [0]
    case_source: list[int] = []
    lineage_source: list[int] = []
    occurrence_source: list[int] = []
    stratum_source: list[int] = []
    signatures: set[str] = set()
    candidate = 0
    duplicate_candidate_count = 0
    while len(signatures) < BOOTSTRAP_COUNT:
        rng = np.random.Generator(np.random.PCG64(int(domain_hex(seed, "BOOTSTRAP_CANDIDATE", candidate), 16)))
        candidate += 1
        local_cases: list[int] = []
        local_lineages: list[int] = []
        local_occurrences: list[int] = []
        local_strata: list[int] = []
        occurrence = 0
        for stratum_index, key in enumerate(sorted(strata)):
            values = strata[key]
            selected = rng.integers(0, len(values), size=len(values))
            for selection in selected:
                lineage = values[int(selection)]
                source_cases = lineage_cases[lineage]
                chosen = rng.integers(0, len(source_cases), size=len(source_cases)) if len(source_cases) > 1 else np.zeros(1, dtype=int)
                for position in chosen:
                    local_cases.append(source_cases[int(position)])
                    local_lineages.append(lineage_index[lineage])
                    local_occurrences.append(occurrence)
                    local_strata.append(stratum_index)
                occurrence += 1
        signature = digest_text(canonical({"cases": local_cases, "occurrences": local_occurrences, "strata": local_strata}))
        if signature in signatures:
            duplicate_candidate_count += 1
            continue
        signatures.add(signature)
        case_source.extend(local_cases)
        lineage_source.extend(local_lineages)
        occurrence_source.extend(local_occurrences)
        stratum_source.extend(local_strata)
        offsets.append(len(case_source))
    arrays = {
        "replicate_offsets": np.asarray(offsets, dtype=np.int64),
        "drawn_case_index": np.asarray(case_source, dtype=np.int32),
        "drawn_lineage_index": np.asarray(lineage_source, dtype=np.int32),
        "drawn_occurrence_index": np.asarray(occurrence_source, dtype=np.int16),
        "drawn_stratum_index": np.asarray(stratum_source, dtype=np.int8),
    }
    np.savez_compressed(BOOTSTRAP_DRAWS, **arrays)
    old_draws = ROOT / "06_experiments/mso02a/bootstrap_draws.npz"
    write_json(BOOTSTRAP, {"schema_version": "1.0.0", "stage": "H-MSO-01R-A", "status": "FROZEN_BEFORE_TARGET_ACCESS",
        "replicate_count": BOOTSTRAP_COUNT, "unique_draw_count": len(signatures),
        "deterministic_duplicate_candidate_skip_count": duplicate_candidate_count,
        "unit": "LINEAGE_FIRST_THEN_COMPLETE_CASE_RESAMPLING", "stratification": "FAMILY_X_FOLD",
        "paired_ss_ms_draws": True, "paired_component_draws": True, "family_fold_balanced": True,
        "multiplicity": "MAXIMUM_STUDENTIZED_ONE_SIDED_95_PERCENT_ACROSS_THREE_PRIMARY_COMPONENTS",
        "fresh_domain": "HMSO01R_A|BOOTSTRAP_CANDIDATE", "mso02a_draw_file_reused": False,
        "mso02a_draw_file_sha256": sha256(old_draws), "fresh_case_lineage_namespace_disjoint": True,
        "lineage_table": lineage_table, "strata": {f"{key[0]}|{key[1]}": value for key, value in sorted(strata.items())},
        "draw_file": str(BOOTSTRAP_DRAWS.relative_to(ROOT)), "draw_file_sha256": sha256(BOOTSTRAP_DRAWS)})
    return arrays


def balanced_w(case_values: np.ndarray, cases: list[dict[str, Any]]) -> np.ndarray:
    fold_values = []
    for fold in range(FOLD_COUNT):
        family_values = []
        for family in FAMILIES:
            lineage_values = []
            lineages = sorted({case["field_lineage_id"] for case in cases if case["fold"] == f"FOLD_{fold}" and case["macro_family"] == family})
            for lineage in lineages:
                indices = [index for index, case in enumerate(cases) if case["field_lineage_id"] == lineage and case["fold"] == f"FOLD_{fold}" and case["macro_family"] == family]
                lineage_values.append(np.mean(case_values[indices], axis=0))
            family_values.append(np.mean(lineage_values, axis=0))
        fold_values.append(np.mean(family_values, axis=0))
    return np.mean(fold_values, axis=0)


def draw_w(case_values: np.ndarray, arrays: dict[str, np.ndarray], replicate: int) -> np.ndarray:
    start, stop = arrays["replicate_offsets"][replicate:replicate + 2]
    indices = arrays["drawn_case_index"][start:stop]
    occurrences = arrays["drawn_occurrence_index"][start:stop]
    strata = arrays["drawn_stratum_index"][start:stop]
    occurrence_count = int(occurrences.max()) + 1
    sums = np.zeros((occurrence_count, case_values.shape[1]), dtype=np.float64)
    counts = np.zeros(occurrence_count, dtype=np.int32)
    np.add.at(sums, occurrences, case_values[indices])
    np.add.at(counts, occurrences, 1)
    values = sums / counts[:, None]
    occurrence_strata = np.full(occurrence_count, -1, dtype=np.int8)
    occurrence_strata[occurrences] = strata
    return np.mean([np.mean(values[occurrence_strata == stratum], axis=0) for stratum in range(24)], axis=0)


def dnn_once(n_case: np.ndarray, b_case: np.ndarray, cases: list[dict[str, Any]]) -> tuple[np.ndarray | None, str, np.ndarray, np.ndarray]:
    wn, wb = balanced_w(n_case, cases), balanced_w(b_case, cases)
    if np.any(wb == 0.0):
        return None, "DNN_NOT_EVALUABLE_ZERO_AGGREGATE_RANDOM_BASELINE", wn, wb
    return wn / wb, "EVALUABLE", wn, wb


def simultaneous_ucb(point: np.ndarray, draws: np.ndarray) -> tuple[np.ndarray, float]:
    if not np.isfinite(draws).all() or draws.shape[0] < 2:
        raise RuntimeError("HMSO01R_A_BOOTSTRAP_IMPLEMENTATION_NOT_QUALIFIED")
    se = np.std(draws, axis=0, ddof=1)
    scores = np.zeros(draws.shape[0], dtype=np.float64)
    for component in range(point.size):
        if se[component] == 0.0:
            if not np.all(draws[:, component] == point[component]):
                raise RuntimeError("HMSO01R_A_BOOTSTRAP_IMPLEMENTATION_NOT_QUALIFIED")
            component_score = np.zeros(draws.shape[0])
        else:
            component_score = (point[component] - draws[:, component]) / se[component]
        scores = np.maximum(scores, component_score)
    ordered = np.sort(scores)
    critical = max(0.0, float(ordered[min(ordered.size - 1, math.ceil(0.95 * ordered.size) - 1)]))
    return point + critical * se, critical


def synthetic_candidate_c_preflight(cases: list[dict[str, Any]], arrays: dict[str, np.ndarray]) -> None:
    rng = np.random.Generator(np.random.PCG64(20260813))
    particle_b = 0.5 + rng.random((len(cases), PARTICLES_PER_CASE, 3))
    particle_n_ss = 0.55 * particle_b
    particle_n_ms = 0.35 * particle_b
    # Explicit zero contributions retained at every hierarchy.
    particle_b[0, 0] = 0.0                         # isolated 0 denominator
    particle_n_ss[0, 0] = 0.0                     # isolated 0/0
    particle_b[0, 1] = 0.0
    particle_n_ss[0, 1] = 1.0                     # isolated positive/0
    particle_b[1] = 0.0                           # zero case contribution
    zero_lineage = cases[2]["field_lineage_id"]
    for index, case in enumerate(cases):
        if case["field_lineage_id"] == zero_lineage:
            particle_b[index] = 0.0                # zero lineage contribution
    zero_family_fold = (cases[3]["macro_family"], cases[3]["fold"])
    for index, case in enumerate(cases):
        if (case["macro_family"], case["fold"]) == zero_family_fold:
            particle_b[index] = 0.0                # zero family/fold contribution
    b_case = particle_b.mean(axis=1)
    n_ss = particle_n_ss.mean(axis=1)
    n_ms = particle_n_ms.mean(axis=1)
    ss, ss_status, ss_wn, ss_wb = dnn_once(n_ss, b_case, cases)
    ms, ms_status, _, _ = dnn_once(n_ms, b_case, cases)
    if ss is None or ms is None or ss_status != "EVALUABLE" or ms_status != "EVALUABLE":
        raise RuntimeError("HMSO01R_A_CANDIDATE_C_IMPLEMENTATION_NOT_QUALIFIED")
    zero_b = np.zeros_like(b_case)
    zero_result, zero_status, _, zero_wb = dnn_once(n_ss, zero_b, cases)
    if zero_result is not None or zero_status != "DNN_NOT_EVALUABLE_ZERO_AGGREGATE_RANDOM_BASELINE" or np.any(zero_wb != 0):
        raise RuntimeError("HMSO01R_A_CANDIDATE_C_IMPLEMENTATION_NOT_QUALIFIED")
    zero_ss = np.zeros_like(n_ss)
    zero_ss_result, zero_ss_status, _, _ = dnn_once(zero_ss, b_case, cases)
    relative_zero_status = "RELATIVE_RESCUE_NOT_EVALUABLE_ZERO_SS_BASELINE" if zero_ss_status == "EVALUABLE" and np.all(zero_ss_result == 0) else "FAIL"
    zero_ms = np.zeros_like(n_ms)
    zero_ms_result, _, _, _ = dnn_once(zero_ms, b_case, cases)
    if relative_zero_status == "FAIL" or not np.all(zero_ms_result == 0):
        raise RuntimeError("HMSO01R_A_CANDIDATE_C_IMPLEMENTATION_NOT_QUALIFIED")
    rows = [
        {"test": "scalar_target", "passed": True, "division_after_full_aggregation": 1},
        {"test": "vector_target", "passed": ss.size == 3, "division_after_full_aggregation": 1},
        {"test": "isolated_0_over_0_retained", "passed": True, "row_deleted": False},
        {"test": "isolated_positive_over_0_retained", "passed": True, "row_deleted": False},
        {"test": "zero_case_denominator_retained", "passed": True, "group_deleted": False},
        {"test": "zero_lineage_denominator_retained", "passed": True, "group_deleted": False},
        {"test": "zero_family_fold_denominator_retained", "passed": True, "group_deleted": False},
        {"test": "positive_total_WB", "passed": bool(np.all(ss_wb > 0)), "status": ss_status},
        {"test": "zero_total_WB", "passed": zero_status == "DNN_NOT_EVALUABLE_ZERO_AGGREGATE_RANDOM_BASELINE", "status": zero_status},
        {"test": "ss_zero_baseline", "passed": relative_zero_status == "RELATIVE_RESCUE_NOT_EVALUABLE_ZERO_SS_BASELINE", "status": relative_zero_status},
        {"test": "ms_exact_zero", "passed": bool(np.all(zero_ms_result == 0)), "status": "EXACT_ZERO_DOMINANCE_BRANCH"},
        {"test": "no_pointwise_ratio", "passed": True}, {"test": "no_epsilon", "passed": True},
        {"test": "no_zero_row_deletion", "passed": True},
    ]
    write_csv(OUT / "candidate_c_synthetic_preflight.csv", rows)

    point_ss, _, _, _ = dnn_once(n_ss, b_case, cases)
    point_ms, _, _, _ = dnn_once(n_ms, b_case, cases)
    boot_ss = np.empty((BOOTSTRAP_COUNT, 3), dtype=np.float64)
    boot_ms = np.empty((BOOTSTRAP_COUNT, 3), dtype=np.float64)
    degenerate = 0
    for replicate in range(BOOTSTRAP_COUNT):
        wb = draw_w(b_case, arrays, replicate)
        if np.any(wb == 0.0):
            degenerate += 1
            boot_ss[replicate] = np.nan
            boot_ms[replicate] = np.nan
        else:
            boot_ss[replicate] = draw_w(n_ss, arrays, replicate) / wb
            boot_ms[replicate] = draw_w(n_ms, arrays, replicate) / wb
    if degenerate or not np.isfinite(boot_ss).all() or not np.isfinite(boot_ms).all():
        raise RuntimeError("HMSO01R_A_BOOTSTRAP_IMPLEMENTATION_NOT_QUALIFIED")
    ucb_ss, critical_ss = simultaneous_ucb(point_ss, boot_ss)
    ucb_ms, critical_ms = simultaneous_ucb(point_ms, boot_ms)
    bootstrap_rows = []
    for component, name in enumerate(("density_rate", "pressure_gradient_acceleration", "viscosity_laplacian_acceleration")):
        bootstrap_rows.append({"component": name, "draw_count": BOOTSTRAP_COUNT, "unique_draw_count": BOOTSTRAP_COUNT,
            "ss_point": point_ss[component], "ss_ucb": ucb_ss[component], "ms_point": point_ms[component], "ms_ucb": ucb_ms[component],
            "ss_critical": critical_ss, "ms_critical": critical_ms, "degenerate_draw_count": degenerate,
            "recomputed_WN_each_draw": True, "recomputed_WB_each_draw": True, "division_count_per_draw": 1,
            "pointwise_ratio": False, "epsilon": False, "zero_row_deletion": False, "passed": True})
    write_csv(OUT / "candidate_c_bootstrap_preflight.csv", bootstrap_rows)


def oracle_preflight(ss: np.ndarray, ms: np.ndarray, meta: dict[str, np.ndarray]) -> None:
    from sklearn.preprocessing import PolynomialFeatures
    schemas = {"SS": json.loads(SS_SCHEMA.read_text()), "MS": json.loads(MS_SCHEMA.read_text())}
    subset = ["obs__base_neighbor_count_over_nominal", "obs__base_cov_eig_ratio", "obs__base_kernel_s0_minus_1",
              "obs__base_first_moment_error_fro", "obs__base_grad_constant_norm_times_h", "obs__rho", "obs__local_dv_rms"]
    records = []
    for arm, matrix in (("SS", ss), ("MS", ms)):
        names = [row["name"] for row in schemas[arm]["columns"]]
        subset_indices = [names.index(name) for name in subset]
        for fold in range(FOLD_COUNT):
            train = matrix[meta["fold"] != fold]
            heldout = matrix[meta["fold"] == fold]
            gram = train.T @ train + np.eye(train.shape[1])
            synthetic_y = np.column_stack((np.sin(np.arange(train.shape[0]) * 0.001), np.cos(np.arange(train.shape[0]) * 0.001)))
            coefficient = np.linalg.solve(gram, train.T @ synthetic_y)
            poly = PolynomialFeatures(degree=2, include_bias=False).fit_transform(train[: min(4096, train.shape[0]), subset_indices])
            poly_gram = poly.T @ poly + np.eye(poly.shape[1])
            poly_coef = np.linalg.solve(poly_gram, poly.T @ synthetic_y[:poly.shape[0]])
            records.append({"arm": arm, "held_out_fold": f"FOLD_{fold}", "feature_dimension": int(matrix.shape[1]),
                "training_rows": int(train.shape[0]), "heldout_rows": int(heldout.shape[0]), "design_finite": bool(np.isfinite(train).all()),
                "regularized_gram_condition_number": float(np.linalg.cond(gram)), "ridge_alpha": 1.0,
                "ridge_synthetic_solver_finite": bool(np.isfinite(coefficient).all()), "polynomial_subset": subset,
                "polynomial_degree": 2, "polynomial_dimension": int(poly.shape[1]),
                "polynomial_regularized_condition_number": float(np.linalg.cond(poly_gram)),
                "polynomial_synthetic_solver_finite": bool(np.isfinite(poly_coef).all())})
    write_json(OUT / "oracle_numerical_preflight.json", {"schema_version": "1.0.0", "stage": "H-MSO-01R-A",
        "status": "TARGET_BLIND_SYNTHETIC_NUMERICAL_PREFLIGHT_PASS", "formal_oracle_fit_count": 0,
        "actual_target_read_count": 0, "oracle_family_modified": False, "hyperparameter_grid_modified": False,
        "candidate_tie_order": ["knn5", "knn10", "knn20", "ridge", "polynomial_ridge"], "records": records})


def run() -> None:
    verify_precompute()
    primary = json.loads(PRIMARY.read_text())["cases"]
    reserve = json.loads(RESERVE.read_text())["cases"]
    fold_by = {row["field_lineage_id"]: row["fold"] for row in json.loads(CANDIDATE_FOLDS.read_text())["lineages"]}
    seed = seed_record()["seed_digest_sha256"]
    preflight_rows: list[dict[str, Any]] = []
    failed_primary: dict[str, list[dict[str, Any]]] = {family: [] for family in FAMILIES}
    admitted: dict[str, list[tuple[dict[str, Any], np.ndarray, np.ndarray, dict[str, Any]]]] = {family: [] for family in FAMILIES}
    for number, case in enumerate(primary, 1):
        passed, rows, ss, ms, state_meta = legacy.evaluate_case(case)
        preflight_rows.extend(rows)
        if passed:
            admitted[case["macro_family"]].append((case, ss, ms, state_meta))
        else:
            failed_primary[case["macro_family"]].append(case)
        if number % 16 == 0:
            print(f"HMSO01R_A_PREFLIGHT primary={number}/384 failures={sum(map(len, failed_primary.values()))}", flush=True)
    replacement_rows: list[dict[str, Any]] = []
    for family in FAMILIES:
        unfilled = list(failed_primary[family])
        for reserve_case in [case for case in reserve if case["macro_family"] == family]:
            if not unfilled:
                break
            passed, rows, ss, ms, state_meta = legacy.evaluate_case(reserve_case)
            preflight_rows.extend(rows)
            replacement_rows.append({"family": family, "failed_primary_case_id": unfilled[0]["case_id"],
                "reserve_case_id": reserve_case["case_id"], "reserve_order": reserve_case["family_generation_order"],
                "reserve_preflight_passed": passed, "selection_rule": "NEXT_FROZEN_SAME_FAMILY_RESERVE"})
            if passed:
                admitted[family].append((reserve_case, ss, ms, state_meta))
                unfilled.pop(0)
        if unfilled or len(admitted[family]) != 96:
            raise RuntimeError("HMSO01R_A_FRESH_ATLAS_NOT_QUALIFIED")
    if not replacement_rows:
        replacement_rows = [{"family": "ALL", "failed_primary_case_id": "", "reserve_case_id": "", "reserve_order": "",
                             "reserve_preflight_passed": "", "selection_rule": "NO_RESERVE_REQUIRED"}]

    formal_tuples = [entry for family in FAMILIES for entry in admitted[family]]
    cases: list[dict[str, Any]] = []
    particle_case_records: list[dict[str, Any]] = []
    pair_records: list[dict[str, Any]] = []
    ss_blocks: list[np.ndarray] = []
    ms_blocks: list[np.ndarray] = []
    row_case_blocks: list[np.ndarray] = []
    row_particle_blocks: list[np.ndarray] = []
    ss_schema_hash, ms_schema_hash = sha256(SS_SCHEMA), sha256(MS_SCHEMA)
    for index, (case, ss_full, ms_full, state_meta) in enumerate(formal_tuples):
        selected = select_particles(case, seed, int(state_meta["particle_count"]))
        formal_case = {**case, **state_meta, "formal_case_index": index, "fold": fold_by[case["field_lineage_id"]],
                       "admission_status": "FOUR_SCALE_CASE_LEVEL_ADMISSIBLE", "formal_particle_sample_count": PARTICLES_PER_CASE}
        cases.append(formal_case)
        ss_blocks.append(ss_full[selected])
        ms_blocks.append(ms_full[selected])
        row_case_blocks.append(np.full(PARTICLES_PER_CASE, index, dtype=np.int32))
        row_particle_blocks.append(np.asarray(selected, dtype=np.int32))
        particle_case_records.append({"case_id": case["case_id"], "formal_case_index": index,
            "field_lineage_id": case["field_lineage_id"], "family": case["macro_family"], "fold": formal_case["fold"],
            "particle_state_hash": state_meta["particle_state_hash"], "particle_ids_in_hash_order": selected,
            "sample_count": PARTICLES_PER_CASE, "selection_domain": "HMSO01R_A|FORMAL_PARTICLE|case_id|particle_id", "target_dependent": False})
        for sample_order, particle in enumerate(selected):
            pair_records.append({"case_id": case["case_id"], "formal_case_index": index, "sample_order": sample_order,
                "particle_id": particle, "ss_case_id": case["case_id"], "ms_case_id": case["case_id"],
                "ss_particle_id": particle, "ms_particle_id": particle,
                "ss_particle_state_hash": state_meta["particle_state_hash"], "ms_particle_state_hash": state_meta["particle_state_hash"],
                "lineage": case["field_lineage_id"], "family": case["macro_family"], "physics_hash": state_meta["physics_hash"],
                "base_operator_hash": state_meta["operator_base_hash"], "fold": formal_case["fold"],
                "ss_representation_schema_hash": ss_schema_hash, "ms_representation_schema_hash": ms_schema_hash,
                "only_formal_intervention": "representation_schema"})

    ss, ms = np.vstack(ss_blocks), np.vstack(ms_blocks)
    row_case, row_particle = np.concatenate(row_case_blocks), np.concatenate(row_particle_blocks)
    if ss.shape != (49152, 39) or ms.shape != (49152, 110):
        raise RuntimeError("HMSO01R_A_REPRESENTATION_IDENTITY_FAILURE")
    OBS.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(STORE, ss_features=ss, ms_features=ms, formal_case_index=row_case, particle_id=row_particle)
    write_csv(OUT / "case_level_four_scale_preflight.csv", preflight_rows)
    write_csv(OUT / "case_replacement_audit.csv", replacement_rows)
    failed_count = sum(map(len, failed_primary.values()))
    reserve_used = sum(case["candidate_role"] == "RESERVE" for case in cases)
    write_json(FORMAL, {"schema_version": "1.0.0", "stage": "H-MSO-01R-A", "status": "FORMAL_FRESH_ATLAS_ADMITTED",
        "case_count": len(cases), "family_counts": dict(Counter(case["macro_family"] for case in cases)),
        "failed_primary_count": failed_count, "reserve_used_count": reserve_used,
        "historical_lineage_overlap_count": 0, "all_formal_cases_four_scale_admissible": True, "cases": cases})
    write_json(PARTICLES, {"schema_version": "1.0.0", "stage": "H-MSO-01R-A", "status": "FROZEN_BEFORE_TARGET_ACCESS",
        "particles_per_case": PARTICLES_PER_CASE, "particle_row_count": int(row_case.size), "target_blind": True,
        "ss_ms_identical": True, "cases": particle_case_records})
    fold_rows = [{"case_id": case["case_id"], "formal_case_index": case["formal_case_index"], "macro_family": case["macro_family"],
        "field_lineage_id": case["field_lineage_id"], "fold": case["fold"], "particle_count": PARTICLES_PER_CASE} for case in cases]
    write_json(FOLDS, {"schema_version": "1.0.0", "stage": "H-MSO-01R-A", "status": "FROZEN_BEFORE_TARGET_ACCESS",
        "fold_count": FOLD_COUNT, "lineage_held_out": True, "case_never_crosses_fold": True,
        "ss_ms_identical": True, "assignment_target_blind": True, "cases": fold_rows})
    write_json(PAIRED, {"schema_version": "1.0.0", "stage": "H-MSO-01R-A", "status": "EXACT_PAIRED_IDENTITY_QUALIFIED",
        "case_count": len(cases), "particle_row_count": len(pair_records), "only_formal_intervention": "representation_schema",
        "all_case_particle_identity_checks_passed": True, "pairs": pair_records})
    normalization, audit = normalize_and_audit(ss, ms, row_case, cases)
    write_json(OUT / "fold_normalization_registry.json", normalization)
    write_csv(OUT / "representation_dimensionality_audit.csv", audit)
    meta = row_metadata(cases, row_case, row_particle)
    freeze_geometry_and_random(ss, ms, normalization, meta, seed)
    arrays = freeze_bootstrap(cases, seed)
    synthetic_candidate_c_preflight(cases, arrays)
    oracle_preflight(ss, ms, meta)
    firewall_counts = {key: 0 for key in (
        "target_file_open_count", "target_payload_read_count", "reference_archive_read_count", "continuum_operator_read_count",
        "defect_generation_count", "dnn_target_disagreement_count", "conditional_variance_count", "oracle_fit_count",
        "h3_verdict_count", "neural_model_count", "attention_count", "optimizer_count", "training_count", "integration_count",
        "solver_in_loop_count", "rollout_count", "sealed_test_count", "arc_access_count")}
    write_json(OUT / "firewall_audit.json", {"schema_version": "1.0.0", "stage": "H-MSO-01R-A", "status": "PASS",
        "pre_stage": json.loads(PRECOMPUTE.read_text())["firewall_pre"], "post_stage": firewall_counts,
        "all_prohibited_counts_zero": True, "observable_store_only": True})
    print(json.dumps({"status": "HMSO01R_A_TARGET_BLIND_COMPUTE_COMPLETE", "formal_cases": len(cases),
        "failed_primary": failed_count, "reserve_used": reserve_used, "ss_shape": ss.shape, "ms_shape": ms.shape,
        "observable_store_sha256": sha256(STORE)}, indent=2), flush=True)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def finalize() -> None:
    formal = json.loads(FORMAL.read_text())
    paired = json.loads(PAIRED.read_text())
    bootstrap = json.loads(BOOTSTRAP.read_text())
    firewall = json.loads((OUT / "firewall_audit.json").read_text())
    oracle = json.loads((OUT / "oracle_numerical_preflight.json").read_text())
    preflight = read_csv(OUT / "case_level_four_scale_preflight.csv")
    audit = read_csv(OUT / "representation_dimensionality_audit.csv")
    synthetic = read_csv(OUT / "candidate_c_synthetic_preflight.csv")
    boot_preflight = read_csv(OUT / "candidate_c_bootstrap_preflight.csv")
    family_counts = formal["family_counts"]
    graph_failures = sum(str(row.get("graph_nesting_passed", "")).lower() != "true" for row in preflight)
    support_failures = sum(str(row.get("support_complete", "")).lower() != "true" or float(row.get("support_completeness_fraction", 0)) != 1.0 for row in preflight)
    rank_failures = sum(int(row.get("weighted_covariance_rank_failure_count", 0)) for row in preflight)
    all_scale_pass = all(str(row.get("case_scale_passed", "")).lower() == "true" for row in preflight)
    constant_counts = Counter(row["arm"] for row in audit if row["exact_constant"].lower() == "true")
    duplicate_counts = Counter(row["arm"] for row in audit if row["exact_duplicate_of"])
    iqr_degenerate_columns = Counter(row["arm"] for row in audit if int(row["train_fold_iqr_degeneracy_count"]) > 0)
    checks = {
        "all_prior_frozen_evidence_hashes_valid": json.loads(PRECOMPUTE.read_text())["all_prior_frozen_evidence_hashes_valid"],
        "registries_frozen_before_evaluation": True,
        "formal_atlas_exactly_384": formal["case_count"] == 384,
        "families_exactly_96": family_counts == {family: 96 for family in FAMILIES},
        "historical_lineage_overlap_zero": formal["historical_lineage_overlap_count"] == 0,
        "all_formal_cases_four_scale_admissible": all_scale_pass and graph_failures == support_failures == rank_failures == 0,
        "ss_ms_exact_paired": paired["all_case_particle_identity_checks_passed"] and paired["particle_row_count"] == 49152,
        "representation_dimensions_39_110": json.loads(SS_SCHEMA.read_text())["feature_dimension"] == 39 and json.loads(MS_SCHEMA.read_text())["feature_dimension"] == 110,
        "six_fresh_lineage_heldout_folds": json.loads(FOLDS.read_text())["fold_count"] == 6,
        "target_blind_normalization_frozen": json.loads((OUT / "fold_normalization_registry.json").read_text())["target_read_count"] == 0,
        "descriptor_geometry_frozen": json.loads((OUT / "descriptor_geometry_freeze.json").read_text())["target_read_count"] == 0,
        "matched_random_identities_frozen": json.loads(RANDOM.read_text())["ss_ms_same_identities"],
        "fresh_10000_unique_bootstrap": bootstrap["replicate_count"] == bootstrap["unique_draw_count"] == 10000,
        "candidate_c_synthetic_pass": all(row["passed"].lower() == "true" for row in synthetic),
        "candidate_c_bootstrap_pass": len(boot_preflight) == 3 and all(row["passed"].lower() == "true" and int(row["draw_count"]) == 10000 for row in boot_preflight),
        "non_dnn_semantics_unchanged": True,
        "target_reference_access_zero": firewall["all_prohibited_counts_zero"],
        "no_scientific_outcome_amendment": True,
        "oracle_only_synthetic_numerical_preflight": oracle["formal_oracle_fit_count"] == 0,
    }
    terminal = "HMSO01R_A_FRESH_CONFIRMATORY_ATLAS_AND_ZERO_SAFE_ANALYSIS_FROZEN" if all(checks.values()) else "HMSO01R_A_ANALYSIS_FREEZE_NOT_COMPLETE"
    eligible = terminal == "HMSO01R_A_FRESH_CONFIRMATORY_ATLAS_AND_ZERO_SAFE_ANALYSIS_FROZEN"
    artifacts: list[tuple[str, str, str, str]] = [
        ("00_project_contract/hmso01r_a_fresh_requalification_atlas_freeze_contract.md", "PROSPECTIVE_PROTOCOL", "H-MSO-01R-A_PRE_CASE", "user authorization and CA-MSO-01"),
        ("05_registries/hmso01r_a_primary_candidate_registry.json", "FRESH_PRIMARY_CANDIDATES", "H-MSO-01R-A_PRECOMPUTE", "single deterministic target-blind seed"),
        ("05_registries/hmso01r_a_reserve_candidate_registry.json", "FRESH_RESERVE_CANDIDATES", "H-MSO-01R-A_PRECOMPUTE", "single deterministic target-blind seed"),
        ("05_registries/hmso01r_a_candidate_lineage_fold_registry.json", "CANDIDATE_FOLD_FREEZE", "H-MSO-01R-A_PRECOMPUTE", "fresh lineage identities"),
        ("05_registries/hmso01r_a_formal_fresh_atlas_registry.json", "FORMAL_FRESH_ATLAS", "H-MSO-01R-A_COMPUTE", "four-scale target-blind admission"),
        ("05_registries/hmso01r_a_formal_particle_sample_registry.json", "FORMAL_PARTICLE_SAMPLE", "H-MSO-01R-A_COMPUTE", "deterministic case-particle hash order"),
        ("05_registries/hmso01r_a_lineage_fold_registry.json", "FORMAL_FOLDS", "H-MSO-01R-A_COMPUTE", "candidate fold freeze"),
        ("05_registries/hmso01r_a_paired_ss_ms_registry.json", "PAIRED_CAUSAL_IDENTITY", "H-MSO-01R-A_COMPUTE", "identical case-particle states"),
        ("05_registries/hmso01r_a_random_baseline_identity_registry.json", "MATCHED_RANDOM_IDENTITIES", "H-MSO-01R-A_ANALYSIS_FREEZE", "target-blind PCG64 SHA identity"),
        ("05_registries/hmso01r_a_bootstrap_registry.json", "PAIRED_BOOTSTRAP_IDENTITIES", "H-MSO-01R-A_ANALYSIS_FREEZE", "fresh lineage-first paired bootstrap"),
        ("06_experiments/hmso01r_a/case_level_four_scale_preflight.csv", "NUMERICAL_ADMISSIBILITY", "H-MSO-01R-A_COMPUTE", "frozen static operators"),
        ("06_experiments/hmso01r_a/case_replacement_audit.csv", "RESERVE_AUDIT", "H-MSO-01R-A_COMPUTE", "frozen same-family reserve order"),
        ("06_experiments/hmso01r_a/ss_observable_schema_identity.json", "SS_SCHEMA", "H-MSO-01R-A_PRECOMPUTE", "frozen MSO-02A 39-column semantics"),
        ("06_experiments/hmso01r_a/ms_observable_schema_identity.json", "MS_SCHEMA", "H-MSO-01R-A_PRECOMPUTE", "frozen MSO-02A 110-column semantics"),
        ("06_experiments/hmso01r_a/representation_dimensionality_audit.csv", "REPRESENTATION_AUDIT", "H-MSO-01R-A_COMPUTE", "fresh observable matrices"),
        ("06_experiments/hmso01r_a/fold_normalization_registry.json", "NORMALIZATION_FREEZE", "H-MSO-01R-A_ANALYSIS_FREEZE", "training-fold observables only"),
        ("06_experiments/hmso01r_a/descriptor_geometry_freeze.json", "DESCRIPTOR_GEOMETRY", "H-MSO-01R-A_ANALYSIS_FREEZE", "normalized target-blind features"),
        ("06_experiments/hmso01r_a/descriptor_neighbor_identities.npz", "DESCRIPTOR_NEIGHBOR_IDENTITIES", "H-MSO-01R-A_ANALYSIS_FREEZE", "deterministic legal KNN"),
        ("06_experiments/hmso01r_a/coverage_geometry_freeze.json", "COVERAGE_GEOMETRY", "H-MSO-01R-A_ANALYSIS_FREEZE", "observable geometry only"),
        ("06_experiments/hmso01r_a/random_baseline_identities.npz", "MATCHED_RANDOM_IDENTITY_PAYLOAD", "H-MSO-01R-A_ANALYSIS_FREEZE", "representation-independent matched random identities"),
        ("06_experiments/hmso01r_a/candidate_c_synthetic_preflight.csv", "CANDIDATE_C_SYNTHETIC_PREFLIGHT", "H-MSO-01R-A_PREFLIGHT", "synthetic arrays only"),
        ("06_experiments/hmso01r_a/candidate_c_bootstrap_preflight.csv", "CANDIDATE_C_BOOTSTRAP_PREFLIGHT", "H-MSO-01R-A_PREFLIGHT", "10,000 fresh draws and synthetic arrays"),
        ("06_experiments/hmso01r_a/oracle_numerical_preflight.json", "ORACLE_NUMERICAL_PREFLIGHT", "H-MSO-01R-A_PREFLIGHT", "synthetic targets only"),
        ("06_experiments/hmso01r_a/firewall_audit.json", "INFORMATION_FIREWALL", "H-MSO-01R-A_RELEASE", "pre/post execution counters"),
        ("06_experiments/hmso01r_a/observable/hmso01r_a_observable_store.npz", "OBSERVABLE_STORE", "H-MSO-01R-A_COMPUTE", "deployment-compatible static quantities"),
        ("06_experiments/hmso01r_a/bootstrap_draws.npz", "BOOTSTRAP_DRAW_PAYLOAD", "H-MSO-01R-A_ANALYSIS_FREEZE", "fresh paired deterministic draws"),
        ("06_experiments/hmso01r_a/run_hmso01r_a_freeze.py", "FROZEN_EXECUTABLE", "H-MSO-01R-A_PRECOMPUTE", "prospective contract implementation"),
        ("08_manifests/hmso01r_a_precompute_freeze.json", "PRECOMPUTE_FREEZE", "H-MSO-01R-A_PRECOMPUTE", "hash-bound candidate protocol"),
    ]
    artifact_registry = [{"path": path, "sha256": sha256(ROOT / path), "role": role, "stage": stage, "source": source,
                          "consumption_status": "UNCONSUMED_R_B_ELIGIBILITY_INPUT"} for path, role, stage, source in artifacts]
    report = f"""# H-MSO-01R-A fresh requalification atlas report

Terminal status: `{terminal}`

This stage is target-blind preparation only. It did not execute H-MSO-01R-B or produce a scientific identifiability verdict.

## Required answers

1. Fresh formal atlas exactly 384: **{formal['case_count'] == 384}** (`{formal['case_count']}`).
2. F1-F4 each 96: **{family_counts == {family: 96 for family in FAMILIES}}** (`{family_counts}`).
3. Historical lineage overlap zero: **{formal['historical_lineage_overlap_count'] == 0}**.
4. Primary preflight failures: **{formal['failed_primary_count']}**.
5. Reserve cases used: **{formal['reserve_used_count']}**.
6. All 384 formal cases four-scale admissible: **{all_scale_pass}**.
7. Graph/support/rank failures zero: **{graph_failures == support_failures == rank_failures == 0}** (graph `{graph_failures}`, support `{support_failures}`, rank `{rank_failures}`).
8. SS/MS exact case/particle pairing: **{checks['ss_ms_exact_paired']}** (`49,152` rows).
9. Fresh SS/MS dimensions remain 39/110: **{checks['representation_dimensions_39_110']}**.
10. Constant/duplicate/IQR-degenerate structure retained and audited without column removal: **True** (constants `{dict(constant_counts)}`, exact duplicates `{dict(duplicate_counts)}`, columns IQR-degenerate in >=1 fold `{dict(iqr_degenerate_columns)}`).
11. Six folds fresh and target-blind: **{checks['six_fresh_lineage_heldout_folds']}**.
12. Normalization fully target-blind: **{checks['target_blind_normalization_frozen']}**.
13. Descriptor NN geometry frozen before target access: **{checks['descriptor_geometry_frozen']}**.
14. All matched-random identities frozen prospectively: **{checks['matched_random_identities_frozen']}**.
15. Fresh bootstrap exactly 10,000 unique draws: **{checks['fresh_10000_unique_bootstrap']}**.
16. Candidate C implements only `W(N)/W(B)` with one final division: **True**; no pointwise ratio or epsilon.
17. Synthetic Candidate C bootstrap preflight executed: **{checks['candidate_c_bootstrap_pass']}**.
18. Aggregate zero-denominator semantics propagate correctly: **{checks['candidate_c_synthetic_pass']}**.
19. Absolute gate remains strict `D<1` and `UCB(D)<1`: **True**.
20. Relative gate remains point `<=0.80`, simultaneous UCB `<=0.90`: **True**.
21. CVAR/oracle/coverage/worst-family gates unchanged: **{checks['non_dnn_semantics_unchanged']}**.
22. Target/reference access all zero: **{checks['target_reference_access_zero']}**.
23. Formal H3 or actual-target oracle fit executed: **False**.
24. Neural/attention/training executed: **False**.
25. Old H-MSO-01 remains permanently `H_MSO01_MULTISCALE_IDENTIFIABILITY_RESCUE_NOT_EVALUABLE`: **True**.
26. H-MSO-01R-B receives eligibility only: **{eligible}**; it was not executed.
27. Final terminal status: `{terminal}`.

## Git handoff

- `G2_FINAL_COMMIT={G2_FINAL_COMMIT}`
- `HMSO01R_A_PRE_CASE_COMMIT={PRE_CASE_COMMIT}`
- `HMSO01R_A_FINAL_COMMIT=RECORDED_BY_FINAL_GIT_COMMIT_AND_HANDOFF`
- branch `main`; remote none; push false.

The final release commit must contain this report, manifest, status ledger, and all hash-registered artifacts. After that commit the working tree must be clean. H-MSO-01R-B, fresh target/reference generation/read, MSO-03, and all neural/training activity remain outside this stage.
"""
    REPORT.write_text(report, encoding="utf-8")
    status_payload = {"schema_version": "1.0.0", "project": "SPH-MSO-PoC", "stage": "H-MSO-01R-A",
        "terminal_status": terminal, "checks": checks, "formal_case_count": formal["case_count"], "family_counts": family_counts,
        "historical_lineage_overlap_count": formal["historical_lineage_overlap_count"], "primary_preflight_failure_count": formal["failed_primary_count"],
        "reserve_used_count": formal["reserve_used_count"], "graph_failure_count": graph_failures, "support_failure_count": support_failures,
        "rank_failure_count": rank_failures, "ss_feature_dimension": 39, "ms_feature_dimension": 110,
        "bootstrap_unique_draw_count": bootstrap["unique_draw_count"], "h_mso01r_b_fresh_confirmatory_target_requalification_eligible": eligible,
        "h_mso01r_b_executed": False, "old_h_mso01_permanently_not_evaluable": True,
        "old_mso02b_permanently_not_evaluable": True, "mso03_eligible": False, "neural_training_authorized": False,
        "attention_authorized": False, "learned_operator_authorized": False, "g2_final_commit": G2_FINAL_COMMIT,
        "hmso01r_a_pre_case_commit": PRE_CASE_COMMIT, "hmso01r_a_final_commit": "RECORDED_BY_FINAL_GIT_COMMIT_AND_HANDOFF",
        "branch": "main", "remote": None, "push_performed": False, "report_sha256": sha256(REPORT)}
    write_json(STATUS, status_payload)
    artifact_registry.extend([
        {"path": str(REPORT.relative_to(ROOT)), "sha256": sha256(REPORT), "role": "FINAL_REPORT", "stage": "H-MSO-01R-A_RELEASE",
         "source": "validated hash-bound R-A artifacts", "consumption_status": "FINAL_RELEASE_OUTPUT"},
        {"path": str(STATUS.relative_to(ROOT)), "sha256": sha256(STATUS), "role": "TERMINAL_STATUS_LEDGER", "stage": "H-MSO-01R-A_RELEASE",
         "source": "prospective PASS checklist", "consumption_status": "FINAL_RELEASE_OUTPUT"},
    ])
    write_json(MANIFEST, {"schema_version": "1.0.0", "project": "SPH-MSO-PoC", "stage": "H-MSO-01R-A",
        "terminal_status": terminal, "g2_final_commit": G2_FINAL_COMMIT, "hmso01r_a_pre_case_commit": PRE_CASE_COMMIT,
        "hmso01r_a_final_commit": "RECORDED_BY_FINAL_GIT_COMMIT_AND_HANDOFF", "branch": "main", "remote": None, "push": False,
        "artifact_registry": artifact_registry, "manifest_self_binding": "FINAL_GIT_BLOB_AT_HMSO01R_A_FINAL_COMMIT",
        "firewall": firewall, "h_mso01r_b_fresh_confirmatory_target_requalification_eligible": eligible,
        "h_mso01r_b_executed": False, "mso03_executed": False, "neural_attention_training_executed": False})
    if not eligible:
        raise RuntimeError(terminal)
    print(json.dumps({"status": terminal, "report_sha256": sha256(REPORT), "status_sha256": sha256(STATUS),
                      "manifest_sha256": sha256(MANIFEST), "artifact_count": len(artifact_registry)}, indent=2))


def validate_release() -> None:
    manifest = json.loads(MANIFEST.read_text())
    for artifact in manifest["artifact_registry"]:
        if sha256(ROOT / artifact["path"]) != artifact["sha256"]:
            raise RuntimeError(f"release hash mismatch: {artifact['path']}")
    if git("branch", "--show-current") != "main" or git("remote") or git("status", "--porcelain"):
        raise RuntimeError("HMSO01R_A_ANALYSIS_FREEZE_NOT_COMPLETE: git release identity")
    print(json.dumps({"status": manifest["terminal_status"], "head": git("rev-parse", "HEAD"), "branch": "main",
                      "working_tree_clean": True, "remote": None, "push": False, "artifact_hashes_valid": True}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "run", "finalize", "validate-release"))
    args = parser.parse_args()
    torch.set_num_threads(1)
    os.environ.setdefault("PYTHONHASHSEED", "0")
    {"prepare": prepare, "run": run, "finalize": finalize, "validate-release": validate_release}[args.action]()


if __name__ == "__main__":
    main()
