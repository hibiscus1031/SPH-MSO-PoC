#!/usr/bin/env python3
"""Execute the frozen paired MSO-02B prelearning identifiability experiment.

`DNN` in this file means Descriptor Nearest-Neighbour.  The executable has no
neural model, optimizer, training loop, time integrator, or rollout path.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
from typing import Any, Callable

import numpy as np
from scipy.spatial import cKDTree
from sklearn.preprocessing import PolynomialFeatures


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "06_experiments/mso02b"
CHECKPOINTS = OUT / "checkpoints"
FORMAL = ROOT / "05_registries/mso02a_formal_fresh_atlas_registry.json"
SAMPLE_REGISTRY = ROOT / "05_registries/mso02b_formal_particle_sample_registry.json"
SEMANTICS = ROOT / "05_registries/mso02b_analysis_semantics_registry.json"
PRECOMPUTE = ROOT / "08_manifests/mso02b_target_precompute_freeze.json"
EXECUTION_ERRATUM = ROOT / "08_manifests/mso02b_formal_execution_erratum_01.json"
OBSERVABLE = ROOT / "06_experiments/mso02a/observable/mso02a_observable_store.npz"
TARGET = OUT / "target_ref/mso02b_target_store.npz"
NORMALIZATION = ROOT / "06_experiments/mso02a/fold_normalization_registry.json"
COVERAGE_GEOMETRY = ROOT / "05_registries/mso02b_formal_coverage_radius_registry.json"
BOOTSTRAP_REGISTRY = ROOT / "05_registries/mso02a_bootstrap_registry.json"
BOOTSTRAP_DRAWS = ROOT / "06_experiments/mso02a/bootstrap_draws.npz"
TARGET_LEDGER = OUT / "target_access_ledger.json"

JOIN_AUDIT = OUT / "target_observable_join_audit.csv"
SS_DNN = OUT / "ss_dnn_metrics.csv"
MS_DNN = OUT / "ms_dnn_metrics.csv"
SS_CVAR = OUT / "ss_conditional_variance_metrics.csv"
MS_CVAR = OUT / "ms_conditional_variance_metrics.csv"
SS_ORACLE = OUT / "ss_oracle_metrics.csv"
MS_ORACLE = OUT / "ms_oracle_metrics.csv"
COVERAGE = OUT / "coverage_metrics.csv"
RESCUE = OUT / "paired_rescue_metrics.csv"
BOUNDS = OUT / "bootstrap_simultaneous_bounds.csv"
VERDICTS = OUT / "component_verdicts.csv"
FIREWALL = OUT / "firewall_audit.json"
SUMMARY = OUT / "mso02b_formal_summary.json"

STAGED_FINAL_OUTPUTS = (
    JOIN_AUDIT,
    SS_DNN,
    MS_DNN,
    SS_CVAR,
    MS_CVAR,
    SS_ORACLE,
    MS_ORACLE,
    COVERAGE,
    RESCUE,
    BOUNDS,
    VERDICTS,
    FIREWALL,
    TARGET_LEDGER,
    SUMMARY,
)
FORMAL_STAGING: Path | None = None

ARMS = ("SS", "MS")
FAMILIES = ("F1", "F2", "F3", "F4")
FOLDS = tuple(range(6))
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
U_NUM_FIELDS = {
    "density_rate": "case_density_rate_U_num",
    "pressure_gradient_acceleration": "case_pressure_U_num",
    "viscosity_laplacian_acceleration": "case_viscosity_U_num",
}
ORACLES = ("knn5", "knn10", "knn20", "ridge", "polynomial_ridge")
SENSITIVITY_K = (5, 20)
PRIMARY_K = 10
DIMENSIONLESS_FLOOR = 128.0 * np.finfo(np.float64).eps


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def seed_integer(text: str) -> int:
    return int(hash_text(text), 16)


def output_destination(path: Path) -> Path:
    if FORMAL_STAGING is not None and path in STAGED_FINAL_OUTPUTS:
        return FORMAL_STAGING / path.name
    return path


def write_json(path: Path, payload: Any) -> None:
    path = output_destination(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path = output_destination(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else ["status"]
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def publish_staged_outputs() -> None:
    if FORMAL_STAGING is None:
        raise RuntimeError("formal staging directory is not configured")
    missing = [
        path.name for path in STAGED_FINAL_OUTPUTS
        if not (FORMAL_STAGING / path.name).exists()
    ]
    if missing:
        raise RuntimeError("incomplete formal staging set:" + ",".join(missing))
    publish_order = [
        path for path in STAGED_FINAL_OUTPUTS if path not in (TARGET_LEDGER, SUMMARY)
    ] + [TARGET_LEDGER, SUMMARY]
    for final in publish_order:
        staged = FORMAL_STAGING / final.name
        if final.exists() and final not in (TARGET_LEDGER, SUMMARY):
            if sha256(final) != sha256(staged):
                raise RuntimeError(f"partial published output conflicts with staging: {final}")
            continue
        final.parent.mkdir(parents=True, exist_ok=True)
        temporary = final.with_suffix(final.suffix + ".publish.tmp")
        temporary.write_bytes(staged.read_bytes())
        temporary.replace(final)
    for staged in FORMAL_STAGING.iterdir():
        if staged.is_file():
            staged.unlink()
    FORMAL_STAGING.rmdir()


def verify_frozen_inputs() -> dict[str, Any]:
    freeze = json.loads(PRECOMPUTE.read_text(encoding="utf-8"))
    if not EXECUTION_ERRATUM.exists():
        raise RuntimeError("MSO02B_FORMAL_EXECUTION_ERRATUM_MISSING")
    erratum = json.loads(EXECUTION_ERRATUM.read_text(encoding="utf-8"))
    target_store_sha256 = sha256(TARGET)
    corrected_keys = {
        "06_experiments/mso02b/run_mso02b_formal.py",
        "06_experiments/mso02b/finalize_mso02b_release.py",
    }
    if (
        erratum.get("status")
        != "FROZEN_POST_TARGET_NONSCIENTIFIC_EXECUTION_ERRATUM_BEFORE_FIRST_HELDOUT_METRIC_OUTPUT"
        or erratum.get("original_target_precompute_freeze_sha256") != sha256(PRECOMPUTE)
        or erratum.get("target_store_sha256") != target_store_sha256
        or erratum.get("observable_store_sha256")
        != freeze["frozen_input_sha256"][
            "06_experiments/mso02a/observable/mso02a_observable_store.npz"
        ]
        or erratum.get("execution_freeze_commit")
        != "65aaedc86c97b876a0ce84745d7eee50dfeba660"
        or set(erratum.get("original_execution_artifact_sha256", {})) != corrected_keys
        or set(erratum.get("corrected_execution_artifact_sha256", {})) != corrected_keys
        or erratum.get("scientific_definition_modification_counts")
        != {
            "feature": 0,
            "scale": 0,
            "gate": 0,
            "fold": 0,
            "normalization": 0,
            "bootstrap": 0,
            "oracle_family": 0,
            "case_replacement": 0,
        }
    ):
        raise RuntimeError("MSO02B_FORMAL_EXECUTION_ERRATUM_IDENTITY_FAILURE")
    errors = []
    frozen_actual: dict[str, str] = {}
    for group in ("frozen_input_sha256", "execution_artifact_sha256"):
        for relative, expected in freeze[group].items():
            actual = sha256(ROOT / relative)
            if group == "frozen_input_sha256":
                frozen_actual[relative] = actual
            if actual != expected:
                correction = erratum.get("corrected_execution_artifact_sha256", {}).get(relative)
                original = erratum.get("original_execution_artifact_sha256", {}).get(relative)
                if group != "execution_artifact_sha256" or original != expected or correction != actual:
                    errors.append(f"{relative}:{actual}!={expected}")
    for source in freeze.get("external_source_sha256", []):
        path = Path(source["path"])
        actual = sha256(path)
        if actual != source["sha256"]:
            errors.append(f"{path}:{actual}!={source['sha256']}")
    if errors:
        raise RuntimeError("MSO02B_FROZEN_EVIDENCE_IDENTITY_FAILURE:" + ";".join(errors))
    if freeze["formal_target_generation_started"]:
        raise RuntimeError("precompute freeze falsely records prior formal target generation")
    branch = subprocess.run(
        ["git", "branch", "--show-current"], cwd=ROOT, check=True,
        capture_output=True, text=True,
    ).stdout.strip()
    remotes = subprocess.run(
        ["git", "remote"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.split()
    if branch != "main" or remotes:
        raise RuntimeError("MSO02B_FORMAL_ERRATUM_COMMIT_GIT_BOUNDARY_FAILURE")
    committed_paths = corrected_keys | {
        "08_manifests/mso02b_formal_execution_erratum_01.json"
    }
    for relative in committed_paths:
        committed = subprocess.run(
            ["git", "show", f"HEAD:{relative}"], cwd=ROOT, check=True,
            capture_output=True,
        ).stdout
        if hashlib.sha256(committed).hexdigest() != sha256(ROOT / relative):
            raise RuntimeError(
                f"MSO02B_FORMAL_ERRATUM_COMMIT_IDENTITY_FAILURE:{relative}"
            )
    freeze["formal_execution_erratum"] = erratum
    freeze["verified_target_store_sha256"] = target_store_sha256
    freeze["verified_frozen_input_sha256"] = frozen_actual
    return freeze


def norm_sq(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    return values * values if values.ndim == 1 else np.sum(values * values, axis=-1)


def row_norm(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    return np.abs(values) if values.ndim == 1 else np.linalg.norm(values, axis=-1)


def inverted_quantile(values: np.ndarray, q: float) -> float:
    return float(np.quantile(np.asarray(values, dtype=np.float64), q, method="inverted_cdf"))


def case_family_equal_vector(values: np.ndarray, indices: np.ndarray, meta: dict[str, np.ndarray]) -> np.ndarray:
    family_values = []
    for family in FAMILIES:
        family_indices = indices[meta["family"][indices] == family]
        cases = np.unique(meta["case_index"][family_indices])
        case_values = []
        for case in cases:
            rows = family_indices[meta["case_index"][family_indices] == case]
            case_values.append(np.mean(values[rows], axis=0))
        if not case_values:
            raise RuntimeError(f"empty development family {family}")
        family_values.append(np.mean(case_values, axis=0))
    return np.mean(family_values, axis=0)


def development_target_rms(values: np.ndarray, indices: np.ndarray, meta: dict[str, np.ndarray]) -> float:
    family_energy = []
    for family in FAMILIES:
        family_indices = indices[meta["family"][indices] == family]
        cases = np.unique(meta["case_index"][family_indices])
        energies = []
        for case in cases:
            rows = family_indices[meta["case_index"][family_indices] == case]
            energies.append(float(np.mean(norm_sq(values[rows]))))
        if not energies:
            raise RuntimeError(f"empty target-RMS development family {family}")
        family_energy.append(float(np.mean(energies)))
    energy = float(np.mean(family_energy))
    return math.sqrt(energy) if energy > 0 and math.isfinite(energy) else math.nan


def development_trace_variance(values: np.ndarray, indices: np.ndarray, meta: dict[str, np.ndarray]) -> float:
    as_vector = values[:, None] if values.ndim == 1 else values
    family_means, family_second = [], []
    for family in FAMILIES:
        family_indices = indices[meta["family"][indices] == family]
        cases = np.unique(meta["case_index"][family_indices])
        case_means, case_second = [], []
        for case in cases:
            rows = family_indices[meta["case_index"][family_indices] == case]
            case_means.append(np.mean(as_vector[rows], axis=0))
            case_second.append(float(np.mean(norm_sq(as_vector[rows]))))
        family_means.append(np.mean(case_means, axis=0))
        family_second.append(float(np.mean(case_second)))
    mean = np.mean(family_means, axis=0)
    result = float(np.mean(family_second) - np.dot(mean, mean))
    return result


def load_formal_data() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    formal = json.loads(FORMAL.read_text(encoding="utf-8"))
    sample_registry = json.loads(SAMPLE_REGISTRY.read_text(encoding="utf-8"))
    cases = sorted(formal["cases"], key=lambda row: int(row["formal_case_index"]))
    if len(cases) != 384 or len(sample_registry["cases"]) != 384:
        raise RuntimeError("formal population or particle sample size mismatch")

    with np.load(OBSERVABLE, allow_pickle=False) as store:
        observable = {name: np.asarray(store[name]) for name in store.files}
    with np.load(TARGET, allow_pickle=False) as store:
        target = {name: np.asarray(store[name]) for name in store.files}

    required_rows = 384 * 576
    if observable["ss_features"].shape != (required_rows, 39):
        raise RuntimeError("SS observable shape mismatch")
    if observable["ms_features"].shape != (required_rows, 110):
        raise RuntimeError("MS observable shape mismatch")
    if target["formal_case_index"].shape != (required_rows,):
        raise RuntimeError("target row count mismatch")

    sample_full_rows: list[int] = []
    sample_case, sample_particle = [], []
    sample_case_id, sample_lineage, sample_family, sample_fold, sample_seed = [], [], [], [], []
    sample_state_hash, sample_key = [], []
    join_rows: list[dict[str, Any]] = []
    sample_by_case = {int(row["formal_case_index"]): row for row in sample_registry["cases"]}
    for case_index, case in enumerate(cases):
        registered = sample_by_case[case_index]
        particle_ids = [int(value) for value in registered["particle_ids_in_hash_order"]]
        if len(particle_ids) != 128 or len(set(particle_ids)) != 128:
            raise RuntimeError(f"formal particle sample mismatch for case {case_index}")
        case_rows = np.arange(case_index * 576, (case_index + 1) * 576)
        observable_case = observable["formal_case_index"][case_rows]
        observable_particle = observable["particle_id"][case_rows]
        target_case = target["formal_case_index"][case_rows]
        target_particle = target["particle_id"][case_rows]
        expected_particle = np.arange(576)
        row_order = (
            np.array_equal(observable_case, np.full(576, case_index))
            and np.array_equal(target_case, np.full(576, case_index))
            and np.array_equal(observable_particle, expected_particle)
            and np.array_equal(target_particle, expected_particle)
        )
        target_case_id = np.asarray(target["case_id"])[case_rows]
        target_state = np.asarray(target["particle_state_hash"])[case_rows]
        case_identity = bool(np.all(target_case_id == case["case_id"]))
        state_identity = bool(np.all(target_state == case["particle_state_hash"]))
        join_rows.append(
            {
                "formal_case_index": case_index,
                "case_id": case["case_id"],
                "particle_row_count": 576,
                "observable_case_id_derived_from_frozen_index_matches_target": case_identity,
                "observable_particle_id_sequence_matches_target": row_order,
                "observable_particle_state_hash_derived_from_registry_matches_target": state_identity,
                "silent_reorder_count": 0 if row_order else 1,
                "join_passed": bool(row_order and case_identity and state_identity),
            }
        )
        for particle in particle_ids:
            full_row = case_index * 576 + particle
            sample_full_rows.append(full_row)
            sample_case.append(case_index)
            sample_particle.append(particle)
            sample_case_id.append(case["case_id"])
            sample_lineage.append(case["field_lineage_id"])
            sample_family.append(case["macro_family"])
            sample_fold.append(int(case["fold"].split("_")[1]))
            sample_seed.append(int(case["jitter_seed"]))
            sample_state_hash.append(case["particle_state_hash"])
            sample_key.append(f"{case['case_id']}|{particle}")
    if not all(row["join_passed"] for row in join_rows):
        write_csv(JOIN_AUDIT, join_rows)
        raise RuntimeError("MSO02B_TARGET_OBSERVABLE_JOIN_FAILURE")
    write_csv(JOIN_AUDIT, join_rows)

    full = np.asarray(sample_full_rows, dtype=np.int64)
    sampled = {
        "SS": np.asarray(observable["ss_features"][full], dtype=np.float64),
        "MS": np.asarray(observable["ms_features"][full], dtype=np.float64),
    }
    targets = {}
    for component, field in TARGET_FIELDS.items():
        values = np.asarray(target[field][full], dtype=np.float64)
        targets[component] = values
    targets["bundle"] = np.column_stack(
        (
            targets["density_rate"],
            targets["pressure_gradient_acceleration"],
            targets["viscosity_laplacian_acceleration"],
        )
    )
    meta = {
        "full_row": full,
        "case_index": np.asarray(sample_case, dtype=np.int16),
        "particle_id": np.asarray(sample_particle, dtype=np.int16),
        "case_id": np.asarray(sample_case_id),
        "lineage": np.asarray(sample_lineage),
        "family": np.asarray(sample_family),
        "fold": np.asarray(sample_fold, dtype=np.int8),
        "seed": np.asarray(sample_seed, dtype=np.int64),
        "particle_state_hash": np.asarray(sample_state_hash),
        "sample_key": np.asarray(sample_key),
        "U_num_density_rate": np.asarray(target[U_NUM_FIELDS["density_rate"]], dtype=np.float64),
        "U_num_pressure_gradient_acceleration": np.asarray(target[U_NUM_FIELDS["pressure_gradient_acceleration"]], dtype=np.float64),
        "U_num_viscosity_laplacian_acceleration": np.asarray(target[U_NUM_FIELDS["viscosity_laplacian_acceleration"]], dtype=np.float64),
    }
    for arm in ARMS:
        if not np.isfinite(sampled[arm]).all():
            raise RuntimeError(f"nonfinite sampled {arm} observables")
    if not all(np.isfinite(targets[name]).all() for name in COMPONENTS):
        raise RuntimeError("nonfinite sampled targets")
    return {"features": sampled, "targets": targets, "meta": meta}, cases


def exact_permitted_neighbors(
    train_x: np.ndarray,
    query_x: np.ndarray,
    train_meta: dict[str, np.ndarray],
    query_meta: dict[str, np.ndarray],
    *,
    required_k: int = 20,
) -> tuple[np.ndarray, np.ndarray]:
    """Return exact permitted neighbors with deterministic complete tie sets."""

    tree = cKDTree(train_x, compact_nodes=True, balanced_tree=True)
    result_index = np.full((query_x.shape[0], required_k), -1, dtype=np.int64)
    result_distance = np.full((query_x.shape[0], required_k), np.inf, dtype=np.float64)
    unresolved = np.arange(query_x.shape[0], dtype=np.int64)
    schedules = []
    for value in (64, 256, 1024, 4096, train_x.shape[0]):
        value = min(value, train_x.shape[0])
        if value not in schedules:
            schedules.append(value)
    for use_k in schedules:
        if unresolved.size == 0:
            break
        distances, indices = tree.query(
            query_x[unresolved], k=use_k, eps=0, p=2, workers=1
        )
        if use_k == 1:
            distances, indices = distances[:, None], indices[:, None]
        next_unresolved = []
        for local, query_row in enumerate(unresolved):
            candidates = np.asarray(indices[local], dtype=np.int64)
            candidate_distances = np.asarray(distances[local], dtype=np.float64)
            permitted = (
                (train_meta["case_id"][candidates] != query_meta["case_id"][query_row])
                & (train_meta["lineage"][candidates] != query_meta["lineage"][query_row])
            )
            query_seed = int(query_meta["seed"][query_row])
            if query_seed != 0:
                permitted &= train_meta["seed"][candidates] != query_seed
            candidates = candidates[permitted]
            candidate_distances = candidate_distances[permitted]
            if candidates.size >= required_k:
                order = np.lexsort(
                    (
                        train_meta["particle_id"][candidates],
                        train_meta["case_id"][candidates],
                        candidate_distances,
                    )
                )
                candidates, candidate_distances = candidates[order], candidate_distances[order]
                cutoff = float(candidate_distances[required_k - 1])
                complete_tie_set = use_k == train_x.shape[0] or float(distances[local, -1]) > cutoff
                if complete_tie_set:
                    result_index[query_row] = candidates[:required_k]
                    result_distance[query_row] = candidate_distances[:required_k]
                    continue
            next_unresolved.append(query_row)
        unresolved = np.asarray(next_unresolved, dtype=np.int64)
    if unresolved.size or (result_index < 0).any() or not np.isfinite(result_distance).all():
        raise RuntimeError(f"exact permitted neighbor search unresolved rows={unresolved.size}")
    return result_distance, result_index


def subset_meta(meta: dict[str, np.ndarray], indices: np.ndarray) -> dict[str, np.ndarray]:
    keys = ("case_id", "lineage", "seed", "particle_id", "family", "fold", "case_index")
    return {key: meta[key][indices] for key in keys}


def ordered_training_indices(indices: np.ndarray, meta: dict[str, np.ndarray]) -> np.ndarray:
    hashes = np.asarray([hash_text(str(meta["sample_key"][index])) for index in indices])
    order = np.lexsort((meta["sample_key"][indices], hashes))
    return indices[order]


def ridge_predict(train_x: np.ndarray, train_y: np.ndarray, query_x: np.ndarray, alpha: float = 1.0) -> np.ndarray:
    values = train_y[:, None] if train_y.ndim == 1 else train_y
    x_mean, y_mean = train_x.mean(axis=0), values.mean(axis=0)
    xc, yc = train_x - x_mean, values - y_mean
    gram = xc.T @ xc
    gram.flat[:: gram.shape[0] + 1] += alpha
    beta = np.linalg.solve(gram, xc.T @ yc)
    return (query_x - x_mean) @ beta + y_mean


def candidate_predictions(
    train_x: np.ndarray,
    query_x: np.ndarray,
    train_bundle: np.ndarray,
    neighbor_local: np.ndarray,
    polynomial_positions: list[int],
) -> tuple[dict[str, np.ndarray], dict[str, str]]:
    predictions: dict[str, np.ndarray] = {}
    failures: dict[str, str] = {}
    for k in (5, 10, 20):
        name = f"knn{k}"
        prediction = np.mean(train_bundle[neighbor_local[:, :k]], axis=1)
        if np.isfinite(prediction).all():
            predictions[name] = prediction
        else:
            failures[name] = "FloatingPointError:nonfinite KNN prediction"
    try:
        ridge = ridge_predict(train_x, train_bundle, query_x, alpha=1.0)
        if not np.isfinite(ridge).all():
            raise FloatingPointError("nonfinite ridge prediction")
        predictions["ridge"] = ridge
    except (np.linalg.LinAlgError, FloatingPointError, ValueError) as error:
        failures["ridge"] = f"{type(error).__name__}:{error}"
    try:
        polynomial = PolynomialFeatures(degree=2, include_bias=False)
        poly_train = polynomial.fit_transform(train_x[:, polynomial_positions])
        poly_query = polynomial.transform(query_x[:, polynomial_positions])
        poly_prediction = ridge_predict(
            poly_train, train_bundle, poly_query, alpha=1.0
        )
        if not np.isfinite(poly_prediction).all():
            raise FloatingPointError("nonfinite polynomial ridge prediction")
        predictions["polynomial_ridge"] = poly_prediction
    except (np.linalg.LinAlgError, FloatingPointError, ValueError) as error:
        failures["polynomial_ridge"] = f"{type(error).__name__}:{error}"
    return predictions, failures


def inner_family_error_energy(
    target_query: np.ndarray,
    prediction_query: np.ndarray,
    query_global: np.ndarray,
    meta: dict[str, np.ndarray],
) -> dict[str, float]:
    output: dict[str, float] = {}
    local_case = meta["case_index"][query_global]
    local_family = meta["family"][query_global]
    for family in FAMILIES:
        family_local = np.flatnonzero(local_family == family)
        values = []
        for case in np.unique(local_case[family_local]):
            rows = family_local[local_case[family_local] == case]
            values.append(float(np.mean(norm_sq(prediction_query[rows] - target_query[rows]))))
        output[family] = float(np.mean(values)) if values else math.nan
    return output


def polynomial_positions(arm: str) -> list[int]:
    schema_path = ROOT / f"06_experiments/mso02a/{arm.lower()}_observable_schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    names = [column["name"] for column in schema["columns"]]
    semantics = json.loads(SEMANTICS.read_text(encoding="utf-8"))
    subset = semantics["oracle"]["polynomial_ridge"][f"frozen_{arm.lower()}_subset"]
    positions = [names.index(name) for name in subset]
    if len(positions) != 7 or len(set(positions)) != 7:
        raise RuntimeError(f"invalid frozen polynomial subset for {arm}")
    return positions


def nested_select_oracles(
    arm: str,
    outer: int,
    x_scaled: np.ndarray,
    bundle: np.ndarray,
    targets: dict[str, np.ndarray],
    meta: dict[str, np.ndarray],
    poly_positions: list[int],
) -> tuple[dict[str, str | None], list[dict[str, Any]]]:
    development_folds = [fold for fold in FOLDS if fold != outer]
    losses: dict[str, dict[str, list[float]]] = {
        component: {candidate: [] for candidate in ORACLES} for component in COMPONENTS
    }
    records: list[dict[str, Any]] = []
    for inner_validation in development_folds:
        train_global = np.flatnonzero(
            (meta["fold"] != outer) & (meta["fold"] != inner_validation)
        )
        train_global = ordered_training_indices(train_global, meta)
        query_global = np.flatnonzero(meta["fold"] == inner_validation)
        train_meta = subset_meta(meta, train_global)
        query_meta = subset_meta(meta, query_global)
        _, neighbor_local = exact_permitted_neighbors(
            x_scaled[train_global],
            x_scaled[query_global],
            train_meta,
            query_meta,
            required_k=20,
        )
        predictions, candidate_failures = candidate_predictions(
            x_scaled[train_global],
            x_scaled[query_global],
            bundle[train_global],
            neighbor_local,
            poly_positions,
        )
        for component in COMPONENTS:
            component_slice = TARGET_SLICES[component]
            train_target = targets[component]
            target_rms = development_target_rms(train_target, train_global, meta)
            query_target = targets[component][query_global]
            for candidate in ORACLES:
                if candidate not in predictions:
                    losses[component][candidate].append(math.inf)
                    records.append(
                        {
                            "arm": arm,
                            "outer_fold": outer,
                            "inner_validation_fold": inner_validation,
                            "component": component,
                            "candidate": candidate,
                            "inner_target_rms": target_rms,
                            "family_nrmse": {},
                            "inner_loss": None,
                            "valid": False,
                            "failure": candidate_failures.get(candidate, "candidate unavailable"),
                        }
                    )
                    continue
                prediction = predictions[candidate][:, component_slice]
                if prediction.shape[1] == 1:
                    prediction = prediction[:, 0]
                family_error = inner_family_error_energy(
                    query_target, prediction, query_global, meta
                )
                family_nrmse = {
                    family: (
                        math.sqrt(family_error[family]) / target_rms
                        if target_rms > 0 and family_error[family] >= 0
                        else math.nan
                    )
                    for family in FAMILIES
                }
                loss = float(np.mean(list(family_nrmse.values())))
                losses[component][candidate].append(loss)
                records.append(
                    {
                        "arm": arm,
                        "outer_fold": outer,
                        "inner_validation_fold": inner_validation,
                        "component": component,
                        "candidate": candidate,
                        "inner_target_rms": target_rms,
                        "family_nrmse": family_nrmse,
                        "inner_loss": loss,
                        "valid": bool(math.isfinite(loss)),
                    }
                )
        print(
            f"MSO02B_NESTED_ORACLE arm={arm} outer={outer} inner={inner_validation} complete",
            flush=True,
        )
    winners: dict[str, str | None] = {}
    for component in COMPONENTS:
        candidate_scores = {}
        for candidate in ORACLES:
            values = losses[component][candidate]
            candidate_scores[candidate] = (
                float(np.mean(values))
                if len(values) == 5 and np.isfinite(values).all()
                else math.inf
            )
        valid = [candidate for candidate in ORACLES if math.isfinite(candidate_scores[candidate])]
        winners[component] = (
            min(valid, key=lambda name: (candidate_scores[name], ORACLES.index(name)))
            if valid
            else None
        )
        for record in records:
            if record["component"] == component:
                candidate_score = candidate_scores[record["candidate"]]
                record["candidate_outer_mean_loss"] = (
                    candidate_score if math.isfinite(candidate_score) else None
                )
                record["selected_for_outer_fit"] = (
                    winners[component] is not None
                    and record["candidate"] == winners[component]
                )
                record["outer_selection_status"] = (
                    "SELECTED" if record["selected_for_outer_fit"] else
                    "ORACLE_NOT_EVALUABLE_ALL_CANDIDATES_INVALID" if winners[component] is None else
                    "NOT_SELECTED"
                )
    return winners, records


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
                    f"MSO02B|BASELINE|{meta['case_id'][global_index]}|{int(meta['particle_id'][global_index])}"
                )
            )
        )
        # The authoritative primary identity is exactly a size-10 draw.  The
        # K=20 diagnostic appends a separately domain-separated draw from the
        # remaining permitted pool so sensitivity computation cannot alter the
        # first ten identities.
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


def reciprocal_fraction(
    train_x: np.ndarray,
    query_x: np.ndarray,
    neighbor_local: np.ndarray,
    train_meta: dict[str, np.ndarray],
    query_meta: dict[str, np.ndarray],
) -> float:
    used = np.unique(neighbor_local[:, :PRIMARY_K])
    _, reverse_query_local = exact_permitted_neighbors(
        query_x,
        train_x[used],
        query_meta,
        {key: value[used] for key, value in train_meta.items()},
        required_k=PRIMARY_K,
    )
    reverse = {int(train_position): set(reverse_query_local[i].tolist()) for i, train_position in enumerate(used)}
    hits = 0
    for query_position in range(query_x.shape[0]):
        for train_position in neighbor_local[query_position, :PRIMARY_K]:
            hits += int(query_position in reverse[int(train_position)])
    return hits / float(query_x.shape[0] * PRIMARY_K)


def component_case_rows(
    arm: str,
    outer: int,
    component: str,
    train_global: np.ndarray,
    query_global: np.ndarray,
    neighbor_local: np.ndarray,
    random_local: np.ndarray,
    coverage_particle: np.ndarray,
    selected_prediction: np.ndarray,
    baseline_prediction: np.ndarray,
    selected_oracle: str | None,
    targets: dict[str, np.ndarray],
    meta: dict[str, np.ndarray],
) -> list[dict[str, Any]]:
    target_all = targets[component]
    query_target = target_all[query_global]
    neighbor_target = target_all[train_global[neighbor_local]]
    random_target = target_all[train_global[random_local]]
    if query_target.ndim == 1:
        neighbor_difference = neighbor_target - query_target[:, None]
        random_difference = random_target - query_target[:, None]
    else:
        neighbor_difference = neighbor_target - query_target[:, None, :]
        random_difference = random_target - query_target[:, None, :]
    if query_target.ndim == 1:
        numerator = np.mean(neighbor_difference[:, :PRIMARY_K] ** 2, axis=1)
        denominator = np.mean(random_difference[:, :PRIMARY_K] ** 2, axis=1)
    else:
        numerator = np.mean(norm_sq(neighbor_difference[:, :PRIMARY_K]), axis=1)
        denominator = np.mean(norm_sq(random_difference[:, :PRIMARY_K]), axis=1)
    dnn = np.divide(
        numerator,
        denominator,
        out=np.full_like(numerator, np.nan),
        where=denominator > 0,
    )
    dnn_sensitivity: dict[int, np.ndarray] = {}
    for k in SENSITIVITY_K:
        if query_target.ndim == 1:
            sensitivity_numerator = np.mean(neighbor_difference[:, :k] ** 2, axis=1)
            sensitivity_denominator = np.mean(random_difference[:, :k] ** 2, axis=1)
        else:
            sensitivity_numerator = np.mean(norm_sq(neighbor_difference[:, :k]), axis=1)
            sensitivity_denominator = np.mean(norm_sq(random_difference[:, :k]), axis=1)
        dnn_sensitivity[k] = np.divide(
            sensitivity_numerator,
            sensitivity_denominator,
            out=np.full_like(sensitivity_numerator, np.nan),
            where=sensitivity_denominator > 0,
        )
    cvars: dict[int, np.ndarray] = {}
    unconditional = development_trace_variance(target_all, train_global, meta)
    if unconditional > 0 and math.isfinite(unconditional):
        for k in (5, 10, 20):
            local = neighbor_target[:, :k]
            centered = local - np.mean(local, axis=1, keepdims=True)
            if local.ndim == 2:
                local_trace = np.sum(centered * centered, axis=1) / (k - 1)
            else:
                local_trace = np.sum(centered * centered, axis=(1, 2)) / (k - 1)
            cvars[k] = local_trace / unconditional
    else:
        cvars = {
            k: np.full(query_global.size, np.nan, dtype=np.float64)
            for k in (5, 10, 20)
        }
    if query_target.ndim == 1:
        sign = np.mean(
            np.sign(query_target)[:, None]
            * np.sign(neighbor_target[:, :PRIMARY_K])
            < 0,
            axis=1,
        )
    else:
        sign = np.mean(
            np.sum(query_target[:, None, :] * neighbor_target[:, :PRIMARY_K], axis=2) < 0,
            axis=1,
        )
    case_rows = []
    query_case = meta["case_index"][query_global]
    for case in np.unique(query_case):
        local_rows = np.flatnonzero(query_case == case)
        y = query_target[local_rows]
        prediction = selected_prediction[local_rows]
        baseline = baseline_prediction[local_rows]
        error = prediction - y
        baseline_error = baseline - y
        uncertainty = float(meta[f"U_num_{component}"][int(case)])
        row: dict[str, Any] = {
            "arm": arm,
            "outer_fold": outer,
            "component": component,
            "formal_case_index": int(case),
            "case_id": str(meta["case_id"][query_global[local_rows[0]]]),
            "family": str(meta["family"][query_global[local_rows[0]]]),
            "lineage": str(meta["lineage"][query_global[local_rows[0]]]),
            "particle_count": int(local_rows.size),
            "dnn_median": inverted_quantile(dnn[local_rows], 0.5),
            "dnn_p90": inverted_quantile(dnn[local_rows], 0.9),
            "dnn_median_k5_sensitivity": inverted_quantile(dnn_sensitivity[5][local_rows], 0.5),
            "dnn_p90_k5_sensitivity": inverted_quantile(dnn_sensitivity[5][local_rows], 0.9),
            "dnn_median_k20_sensitivity": inverted_quantile(dnn_sensitivity[20][local_rows], 0.5),
            "dnn_p90_k20_sensitivity": inverted_quantile(dnn_sensitivity[20][local_rows], 0.9),
            "cvar5": float(np.mean(cvars[5][local_rows])),
            "cvar10": float(np.mean(cvars[10][local_rows])),
            "cvar20": float(np.mean(cvars[20][local_rows])),
            "coverage": float(np.mean(coverage_particle[local_rows])),
            "sign_disagreement": float(np.mean(sign[local_rows])),
            "selected_oracle": selected_oracle or "NOT_EVALUABLE",
            "dnn_evaluable": bool(np.isfinite(dnn[local_rows]).all()),
            "conditional_variance_evaluable": bool(
                np.isfinite(cvars[10][local_rows]).all()
            ),
            "oracle_evaluable": bool(
                selected_oracle is not None and np.isfinite(prediction).all()
            ),
            "target_ms": float(np.mean(norm_sq(y))),
            "oracle_error_ms": float(np.mean(norm_sq(error))),
            "oracle_mae": float(np.mean(row_norm(error))),
            "oracle_bias": (
                float(np.mean(error))
                if error.ndim == 1
                else float(np.linalg.norm(np.mean(error, axis=0)))
            ),
            "baseline_error_ms": float(np.mean(norm_sq(baseline_error))),
            "target_uncertainty_U_num": uncertainty,
        }
        if y.ndim == 2:
            component_scale = 0.01
            floor = max(10.0 * uncertainty, 1.0e-6 * component_scale)
            active = np.linalg.norm(y, axis=1) > floor
            if active.any():
                denom = np.linalg.norm(y[active], axis=1) * np.linalg.norm(prediction[active], axis=1)
                valid = denom > 0
                if valid.any():
                    cosine = np.clip(
                        np.sum(y[active][valid] * prediction[active][valid], axis=1) / denom[valid],
                        -1.0,
                        1.0,
                    )
                    row["oracle_angle_degrees"] = float(np.degrees(np.arccos(cosine)).mean())
                else:
                    row["oracle_angle_degrees"] = None
            else:
                row["oracle_angle_degrees"] = None
        else:
            row["oracle_angle_degrees"] = None
        case_rows.append(row)
    return case_rows


def run_outer_fold(
    arm: str,
    outer: int,
    features: np.ndarray,
    targets: dict[str, np.ndarray],
    meta: dict[str, np.ndarray],
    normalization: dict[str, Any],
    coverage_geometry: dict[str, Any],
    freeze_sha: str,
    execution_erratum_sha: str,
    evaluator_sha: str,
    target_store_sha: str,
) -> dict[str, Any]:
    checkpoint = CHECKPOINTS / f"{arm.lower()}_fold{outer}.json"
    if checkpoint.exists():
        payload = json.loads(checkpoint.read_text(encoding="utf-8"))
        if payload["target_precompute_freeze_sha256"] != freeze_sha:
            raise RuntimeError(f"stale checkpoint {checkpoint}")
        if payload.get("target_store_sha256") != target_store_sha:
            raise RuntimeError(f"checkpoint target identity mismatch {checkpoint}")
        if (
            payload.get("formal_execution_erratum_sha256") != execution_erratum_sha
            or payload.get("formal_evaluator_sha256") != evaluator_sha
        ):
            raise RuntimeError(f"checkpoint erratum/evaluator identity mismatch {checkpoint}")
        if payload.get("arm") != arm or int(payload.get("outer_fold", -1)) != outer:
            raise RuntimeError(f"checkpoint arm/fold identity mismatch {checkpoint}")
        expected_cases = {
            int(case)
            for case in np.unique(meta["case_index"][meta["fold"] == outer])
        }
        rows = payload.get("case_rows", [])
        for component in COMPONENTS:
            component_cases = {
                int(row["formal_case_index"])
                for row in rows
                if row.get("component") == component
            }
            if component_cases != expected_cases:
                raise RuntimeError(f"checkpoint case schema mismatch {checkpoint} {component}")
        if set(payload.get("selected_oracles", {})) != set(COMPONENTS):
            raise RuntimeError(f"checkpoint selected-oracle schema mismatch {checkpoint}")
        print(f"MSO02B_CHECKPOINT_REUSED arm={arm} outer={outer}", flush=True)
        return payload

    fold_record = next(
        row
        for row in normalization["arms"][arm]["folds"]
        if row["held_out_fold"] == f"FOLD_{outer}"
    )
    median = np.asarray(fold_record["median"], dtype=np.float64)
    divisor = np.asarray(fold_record["divisor"], dtype=np.float64)
    if features.shape[1] != median.size or np.any(divisor <= 0):
        raise RuntimeError(f"normalization dimension/divisor failure {arm} {outer}")
    x_scaled = (features - median) / divisor
    if not np.isfinite(x_scaled).all():
        raise RuntimeError(f"nonfinite normalized observables {arm} {outer}")

    poly_positions = polynomial_positions(arm)
    winners, selection_records = nested_select_oracles(
        arm, outer, x_scaled, targets["bundle"], targets, meta, poly_positions
    )
    train_global = ordered_training_indices(np.flatnonzero(meta["fold"] != outer), meta)
    query_global = np.flatnonzero(meta["fold"] == outer)
    train_meta = subset_meta(meta, train_global)
    query_meta = subset_meta(meta, query_global)
    distances, neighbor_local = exact_permitted_neighbors(
        x_scaled[train_global],
        x_scaled[query_global],
        train_meta,
        query_meta,
        required_k=20,
    )
    random_local = random_baseline_indices(train_global, query_global, meta)
    random_hash = hashlib.sha256(random_local.tobytes()).hexdigest()
    predictions, candidate_failures = candidate_predictions(
        x_scaled[train_global],
        x_scaled[query_global],
        targets["bundle"][train_global],
        neighbor_local,
        poly_positions,
    )
    radius_record = next(
        row
        for row in coverage_geometry["arms"][arm]["folds"]
        if row["held_out_fold"] == f"FOLD_{outer}"
    )
    radius = float(radius_record["k10_radius_p95"])
    coverage_particle = distances[:, PRIMARY_K - 1] <= radius
    reciprocal = reciprocal_fraction(
        x_scaled[train_global],
        x_scaled[query_global],
        neighbor_local,
        train_meta,
        query_meta,
    )
    neighbor_family = Counter(
        train_meta["family"][neighbor_local[:, :PRIMARY_K]].reshape(-1).tolist()
    )
    case_rows: list[dict[str, Any]] = []
    development_rms = {}
    for component in COMPONENTS:
        component_slice = TARGET_SLICES[component]
        winner = winners[component]
        if winner is not None and winner in predictions:
            selected = predictions[winner][:, component_slice]
            if selected.shape[1] == 1:
                selected = selected[:, 0]
        else:
            query_shape = targets[component][query_global].shape
            selected = np.full(query_shape, np.nan, dtype=np.float64)
            if winner is not None:
                candidate_failures[winner] = (
                    "OUTER_SELECTED_CANDIDATE_UNAVAILABLE:"
                    + candidate_failures.get(winner, "unknown")
                )
                winners[component] = None
        development_mean = case_family_equal_vector(
            targets[component], train_global, meta
        )
        query_shape = targets[component][query_global].shape
        baseline_prediction = np.broadcast_to(development_mean, query_shape).copy()
        development_rms[component] = development_target_rms(
            targets[component], train_global, meta
        )
        component_rows = component_case_rows(
            arm,
            outer,
            component,
            train_global,
            query_global,
            neighbor_local,
            random_local,
            coverage_particle,
            selected,
            baseline_prediction,
            winners[component],
            targets,
            meta,
        )
        for row in component_rows:
            row["outer_development_target_rms"] = development_rms[component]
        case_rows.extend(component_rows)
    payload = {
        "schema_version": "1.0.0",
        "stage": "MSO-02B",
        "arm": arm,
        "outer_fold": outer,
        "target_precompute_freeze_sha256": freeze_sha,
        "formal_execution_erratum_sha256": execution_erratum_sha,
        "formal_evaluator_sha256": evaluator_sha,
        "target_store_sha256": target_store_sha,
        "training_sample_count": int(train_global.size),
        "query_sample_count": int(query_global.size),
        "feature_dimension": int(features.shape[1]),
        "selected_oracles": winners,
        "nested_selection_records": selection_records,
        "case_rows": case_rows,
        "coverage_radius": radius,
        "coverage_fraction_particle_diagnostic": float(np.mean(coverage_particle)),
        "reciprocal_neighbor_fraction": reciprocal,
        "neighbor_family_composition": dict(sorted(neighbor_family.items())),
        "random_baseline_index_sha256": random_hash,
        "development_target_rms": development_rms,
        "outer_candidate_fit_failures": candidate_failures,
    }
    write_json(checkpoint, json_safe(payload))
    print(f"MSO02B_OUTER_FOLD arm={arm} outer={outer} complete", flush=True)
    return payload


def run_arm(
    arm: str,
    features: np.ndarray,
    targets: dict[str, np.ndarray],
    meta: dict[str, np.ndarray],
    normalization: dict[str, Any],
    coverage_geometry: dict[str, Any],
    freeze_sha: str,
    execution_erratum_sha: str,
    evaluator_sha: str,
    target_store_sha: str,
) -> dict[str, Any]:
    folds = [
        run_outer_fold(
            arm,
            outer,
            features,
            targets,
            meta,
            normalization,
            coverage_geometry,
            freeze_sha,
            execution_erratum_sha,
            evaluator_sha,
            target_store_sha,
        )
        for outer in FOLDS
    ]
    random_hashes = [record["random_baseline_index_sha256"] for record in folds]
    return {
        "arm": arm,
        "folds": folds,
        "case_rows": [row for record in folds for row in record["case_rows"]],
        "selection_records": [
            row for record in folds for row in record["nested_selection_records"]
        ],
        "random_baseline_index_sha256_by_fold": random_hashes,
    }


def load_bootstrap_counts(cases: list[dict[str, Any]]) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    registry = json.loads(BOOTSTRAP_REGISTRY.read_text(encoding="utf-8"))
    with np.load(BOOTSTRAP_DRAWS, allow_pickle=False) as draw:
        offsets = np.asarray(draw["replicate_offsets"], dtype=np.int64)
        lineage_indices = np.asarray(draw["drawn_lineage_index"], dtype=np.int64)
        case_indices = np.asarray(draw["drawn_case_index"], dtype=np.int64)
    if offsets.shape != (10001,) or offsets[0] != 0 or offsets[-1] != case_indices.size:
        raise RuntimeError("bootstrap serialized offsets mismatch")
    lineages = registry["lineage_table"]
    cases_by_lineage: dict[str, list[int]] = defaultdict(list)
    family_by_lineage = {}
    for case in cases:
        lineage = case["field_lineage_id"]
        cases_by_lineage[lineage].append(int(case["formal_case_index"]))
        family_by_lineage[lineage] = case["macro_family"]
    for lineage in cases_by_lineage:
        cases_by_lineage[lineage].sort()
    counts = np.zeros((10000, 384), dtype=np.int16)
    insufficient_lineage = np.zeros(10000, dtype=bool)
    occurrence_count = 0
    for replicate in range(10000):
        start, stop = int(offsets[replicate]), int(offsets[replicate + 1])
        counts[replicate] = np.bincount(
            case_indices[start:stop], minlength=384
        ).astype(np.int16)
        position = start
        multiplicity_by_family: dict[str, Counter[str]] = {
            family: Counter() for family in FAMILIES
        }
        for stratum in sorted(registry["strata"]):
            family = stratum.split("|")[0]
            allowed = set(registry["strata"][stratum])
            for _ in range(len(allowed)):
                lineage = lineages[int(lineage_indices[position])]
                if lineage not in allowed:
                    raise RuntimeError("bootstrap lineage outside frozen stratum")
                size = len(cases_by_lineage[lineage])
                end = position + size
                if end > stop or not np.all(lineage_indices[position:end] == lineage_indices[position]):
                    raise RuntimeError("bootstrap lineage occurrence boundary mismatch")
                if not all(
                    int(case) in cases_by_lineage[lineage]
                    for case in case_indices[position:end]
                ):
                    raise RuntimeError("bootstrap case outside drawn lineage")
                multiplicity_by_family[family][lineage] += 1
                occurrence_count += 1
                position = end
        if position != stop:
            raise RuntimeError("bootstrap replicate not fully decoded")
        for family in FAMILIES:
            multiplicities = np.asarray(
                list(multiplicity_by_family[family].values()), dtype=np.float64
            )
            ess = (
                float(multiplicities.sum() ** 2 / np.sum(multiplicities**2))
                if multiplicities.size
                else 0.0
            )
            if ess < 2.0:
                insufficient_lineage[replicate] = True
    family_lineages = Counter()
    fold_lineages = Counter()
    for lineage, family in family_by_lineage.items():
        family_lineages[family] += 1
    for case in cases:
        fold_lineages[(case["macro_family"], case["fold"])] += 1
    point_sufficient = (
        all(family_lineages[family] >= 6 for family in FAMILIES)
        and len(fold_lineages) == 24
    )
    audit = {
        "replicate_count": 10000,
        "case_emission_count": int(case_indices.size),
        "decoded_lineage_occurrence_count": occurrence_count,
        "draws_with_family_lineage_kish_ess_below_2": int(insufficient_lineage.sum()),
        "point_effective_lineages_sufficient": point_sufficient,
        "family_unique_lineage_counts": dict(family_lineages),
    }
    if not point_sufficient:
        insufficient_lineage[:] = True
    return counts, insufficient_lineage, audit


def case_vector(rows: list[dict[str, Any]], component: str, field: str) -> np.ndarray:
    selected = [row for row in rows if row["component"] == component]
    if len(selected) != 384:
        raise RuntimeError(f"case metric row count mismatch {component} {field}: {len(selected)}")
    selected.sort(key=lambda row: int(row["formal_case_index"]))
    if [int(row["formal_case_index"]) for row in selected] != list(range(384)):
        raise RuntimeError(f"case metric order mismatch {component}")
    return np.asarray([row[field] for row in selected], dtype=np.float64)


def cell_case_indices(cases: list[dict[str, Any]]) -> dict[tuple[int, str], np.ndarray]:
    output = {}
    for fold in FOLDS:
        for family in FAMILIES:
            output[(fold, family)] = np.asarray(
                [
                    int(case["formal_case_index"])
                    for case in cases
                    if int(case["fold"].split("_")[1]) == fold
                    and case["macro_family"] == family
                ],
                dtype=np.int64,
            )
            if output[(fold, family)].size == 0:
                raise RuntimeError(f"empty formal cell fold={fold} family={family}")
    return output


def aggregate_case_statistic(
    values: np.ndarray,
    counts: np.ndarray,
    cells: dict[tuple[int, str], np.ndarray],
    *,
    reducer: str,
) -> dict[str, Any]:
    point_cell = np.full((6, 4), np.nan, dtype=np.float64)
    boot_cell = np.full((counts.shape[0], 6, 4), np.nan, dtype=np.float64)
    for fold in FOLDS:
        for family_index, family in enumerate(FAMILIES):
            indices = cells[(fold, family)]
            point_values = values[indices]
            if reducer == "mean":
                if np.isfinite(point_values).all():
                    point_cell[fold, family_index] = float(np.mean(point_values))
                    weights = counts[:, indices]
                    denominator = np.sum(weights, axis=1)
                    valid = denominator > 0
                    boot_cell[valid, fold, family_index] = (
                        weights[valid] @ point_values / denominator[valid]
                    )
                else:
                    point_cell[fold, family_index] = math.nan
                    boot_cell[:, fold, family_index] = math.nan
            else:
                q = 0.5 if reducer == "median" else 0.9
                if np.isfinite(point_values).all():
                    point_cell[fold, family_index] = inverted_quantile(point_values, q)
                    for replicate in range(counts.shape[0]):
                        repeated = np.repeat(point_values, counts[replicate, indices])
                        boot_cell[replicate, fold, family_index] = (
                            inverted_quantile(repeated, q) if repeated.size else math.nan
                        )
                else:
                    point_cell[fold, family_index] = math.nan
                    boot_cell[:, fold, family_index] = math.nan
    return {
        "point_cell": point_cell,
        "boot_cell": boot_cell,
        "point": float(np.mean(point_cell)),
        "boot": np.mean(boot_cell, axis=(1, 2)),
        "point_family": np.mean(point_cell, axis=0),
        "boot_family": np.mean(boot_cell, axis=1),
        "point_fold": np.mean(point_cell, axis=1),
        "boot_fold": np.mean(boot_cell, axis=2),
    }


def aggregate_optional_mean(
    values: np.ndarray,
    counts: np.ndarray,
    cells: dict[tuple[int, str], np.ndarray],
) -> dict[str, Any]:
    point_cell = np.full((6, 4), np.nan, dtype=np.float64)
    boot_cell = np.full((counts.shape[0], 6, 4), np.nan, dtype=np.float64)
    for fold in FOLDS:
        for family_index, family in enumerate(FAMILIES):
            indices = cells[(fold, family)]
            finite = np.isfinite(values[indices])
            if finite.any():
                valid_indices = indices[finite]
                point_cell[fold, family_index] = float(np.mean(values[valid_indices]))
                weights = counts[:, valid_indices]
                denominator = np.sum(weights, axis=1)
                valid_draw = denominator > 0
                boot_cell[valid_draw, fold, family_index] = (
                    weights[valid_draw] @ values[valid_indices] / denominator[valid_draw]
                )
    return {
        "point_cell": point_cell,
        "boot_cell": boot_cell,
        "point": float(np.nanmean(point_cell)) if np.isfinite(point_cell).any() else math.nan,
        "boot": np.nanmean(boot_cell, axis=(1, 2)),
        "point_family": np.nanmean(point_cell, axis=0),
        "boot_family": np.nanmean(boot_cell, axis=1),
        "point_fold": np.nanmean(point_cell, axis=1),
        "boot_fold": np.nanmean(boot_cell, axis=2),
    }


def aggregate_oracle(
    error_ms: np.ndarray,
    target_rms_by_case: np.ndarray,
    counts: np.ndarray,
    cells: dict[tuple[int, str], np.ndarray],
) -> dict[str, Any]:
    point_cell = np.full((6, 4), np.nan, dtype=np.float64)
    boot_cell = np.full((counts.shape[0], 6, 4), np.nan, dtype=np.float64)
    for fold in FOLDS:
        target_rms = float(target_rms_by_case[cells[(fold, FAMILIES[0])][0]])
        if not (target_rms > 0 and math.isfinite(target_rms)):
            continue
        for family_index, family in enumerate(FAMILIES):
            indices = cells[(fold, family)]
            if not np.all(target_rms_by_case[indices] == target_rms):
                continue
            if not np.isfinite(error_ms[indices]).all():
                continue
            point_cell[fold, family_index] = math.sqrt(float(np.mean(error_ms[indices]))) / target_rms
            weights = counts[:, indices]
            denominator = np.sum(weights, axis=1)
            valid = denominator > 0
            boot_energy = weights[valid] @ error_ms[indices] / denominator[valid]
            boot_cell[valid, fold, family_index] = np.sqrt(boot_energy) / target_rms
    return {
        "point_cell": point_cell,
        "boot_cell": boot_cell,
        "point": float(np.mean(point_cell)),
        "boot": np.mean(boot_cell, axis=(1, 2)),
        "point_family": np.mean(point_cell, axis=0),
        "boot_family": np.mean(boot_cell, axis=1),
        "point_fold": np.mean(point_cell, axis=1),
        "boot_fold": np.mean(boot_cell, axis=2),
    }


def aggregate_arm_metrics(
    arm_result: dict[str, Any],
    counts: np.ndarray,
    cells: dict[tuple[int, str], np.ndarray],
) -> dict[str, Any]:
    output: dict[str, Any] = {}
    rows = arm_result["case_rows"]
    for component in COMPONENTS:
        dnn_median = aggregate_case_statistic(
            case_vector(rows, component, "dnn_median"), counts, cells, reducer="mean"
        )
        dnn_p90 = aggregate_case_statistic(
            case_vector(rows, component, "dnn_p90"), counts, cells, reducer="mean"
        )
        dnn_median_k5 = aggregate_case_statistic(
            case_vector(rows, component, "dnn_median_k5_sensitivity"), counts, cells, reducer="mean"
        )
        dnn_p90_k5 = aggregate_case_statistic(
            case_vector(rows, component, "dnn_p90_k5_sensitivity"), counts, cells, reducer="mean"
        )
        dnn_median_k20 = aggregate_case_statistic(
            case_vector(rows, component, "dnn_median_k20_sensitivity"), counts, cells, reducer="mean"
        )
        dnn_p90_k20 = aggregate_case_statistic(
            case_vector(rows, component, "dnn_p90_k20_sensitivity"), counts, cells, reducer="mean"
        )
        cvar5 = aggregate_case_statistic(
            case_vector(rows, component, "cvar5"), counts, cells, reducer="mean"
        )
        cvar10 = aggregate_case_statistic(
            case_vector(rows, component, "cvar10"), counts, cells, reducer="mean"
        )
        cvar20 = aggregate_case_statistic(
            case_vector(rows, component, "cvar20"), counts, cells, reducer="mean"
        )
        coverage = aggregate_case_statistic(
            case_vector(rows, component, "coverage"), counts, cells, reducer="mean"
        )
        sign = aggregate_case_statistic(
            case_vector(rows, component, "sign_disagreement"), counts, cells, reducer="mean"
        )
        target_rms = case_vector(rows, component, "outer_development_target_rms")
        oracle = aggregate_oracle(
            case_vector(rows, component, "oracle_error_ms"), target_rms, counts, cells
        )
        baseline = aggregate_oracle(
            case_vector(rows, component, "baseline_error_ms"), target_rms, counts, cells
        )
        oracle_mae = aggregate_case_statistic(
            case_vector(rows, component, "oracle_mae"), counts, cells, reducer="mean"
        )
        oracle_bias = aggregate_case_statistic(
            case_vector(rows, component, "oracle_bias"), counts, cells, reducer="mean"
        )
        selected_rows = sorted(
            [row for row in rows if row["component"] == component],
            key=lambda row: int(row["formal_case_index"]),
        )
        angle_values = np.asarray(
            [
                math.nan if row["oracle_angle_degrees"] is None else float(row["oracle_angle_degrees"])
                for row in selected_rows
            ],
            dtype=np.float64,
        )
        oracle_angle = aggregate_optional_mean(angle_values, counts, cells)
        improvement_point = 1.0 - oracle["point"] / baseline["point"]
        improvement_boot = 1.0 - oracle["boot"] / baseline["boot"]
        output[component] = {
            "dnn_median": dnn_median,
            "dnn_p90": dnn_p90,
            "dnn_median_k5_sensitivity": dnn_median_k5,
            "dnn_p90_k5_sensitivity": dnn_p90_k5,
            "dnn_median_k20_sensitivity": dnn_median_k20,
            "dnn_p90_k20_sensitivity": dnn_p90_k20,
            "cvar5": cvar5,
            "cvar10": cvar10,
            "cvar20": cvar20,
            "coverage": coverage,
            "sign_disagreement": sign,
            "oracle_nrmse": oracle,
            "baseline_nrmse": baseline,
            "oracle_mae": oracle_mae,
            "oracle_bias": oracle_bias,
            "oracle_angle_degrees": oracle_angle,
            "improvement": {"point": improvement_point, "boot": improvement_boot},
            "worst_family_nrmse": float(np.max(oracle["point_family"])),
            "selected_oracles_by_fold": {
                str(fold): arm_result["folds"][fold]["selected_oracles"][component]
                for fold in FOLDS
            },
        }
    return output


def simultaneous_bound(
    metric_family: str,
    points: np.ndarray,
    bootstrap: np.ndarray,
    inherited_degenerate: np.ndarray,
    *,
    direction: str,
    scale: str = "identity",
    scope: str = "THREE_PRIMARY_COMPONENTS",
    eligible_components: np.ndarray | None = None,
    ineligible_status: str = "NOT_EVALUABLE",
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    points = np.asarray(points, dtype=np.float64)
    bootstrap = np.asarray(bootstrap, dtype=np.float64)
    eligible = (
        np.ones(3, dtype=bool)
        if eligible_components is None
        else np.asarray(eligible_components, dtype=bool)
    )
    if eligible.shape != (3,):
        raise RuntimeError("invalid simultaneous-bound component eligibility mask")
    if scale == "log":
        if eligible.any() and np.any(points[eligible] <= 0):
            valid = np.zeros(bootstrap.shape[0], dtype=bool)
            transformed_points = np.full_like(points, np.nan)
            transformed = np.full_like(bootstrap, np.nan)
        else:
            transformed_points = np.full_like(points, np.nan)
            transformed_points[eligible] = np.log(points[eligible])
            valid = (
                np.all(bootstrap[:, eligible] > 0, axis=1)
                if eligible.any()
                else np.zeros(bootstrap.shape[0], dtype=bool)
            )
            transformed = np.full_like(bootstrap, np.nan)
            transformed[np.ix_(valid, eligible)] = np.log(
                bootstrap[np.ix_(valid, eligible)]
            )
    else:
        transformed_points = points
        transformed = bootstrap
        valid = (
            np.ones(bootstrap.shape[0], dtype=bool)
            if eligible.any()
            else np.zeros(bootstrap.shape[0], dtype=bool)
        )
    valid &= ~inherited_degenerate
    if eligible.any():
        valid &= np.all(np.isfinite(transformed[:, eligible]), axis=1)
        valid &= np.isfinite(transformed_points[eligible]).all()
    degenerate = int((~valid).sum())
    result: dict[str, dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []
    status = "EVALUABLE" if degenerate <= 200 and int(valid.sum()) >= 2 else "NOT_EVALUABLE"
    critical = math.nan
    standard_error = np.full(3, np.nan)
    bounds = np.full(3, np.nan)
    if status == "EVALUABLE":
        values = transformed[valid]
        standard_error = np.std(values, axis=0, ddof=1)
        eligible_indices = np.flatnonzero(eligible)
        contributions = np.empty((values.shape[0], eligible_indices.size), dtype=np.float64)
        for contribution_index, component_index in enumerate(eligible_indices):
            se = float(standard_error[component_index])
            if se == 0.0:
                if np.all(values[:, component_index] == transformed_points[component_index]):
                    contributions[:, contribution_index] = 0.0
                else:
                    status = "NOT_EVALUABLE"
                    break
            elif direction == "upper":
                contributions[:, contribution_index] = (
                    transformed_points[component_index] - values[:, component_index]
                ) / se
            else:
                contributions[:, contribution_index] = (
                    values[:, component_index] - transformed_points[component_index]
                ) / se
        if status == "EVALUABLE":
            maximum = np.max(contributions, axis=1)
            rank = max(0, math.ceil(0.95 * maximum.size) - 1)
            critical = max(0.0, float(np.sort(maximum)[rank]))
            signed = 1.0 if direction == "upper" else -1.0
            transformed_bound = transformed_points.copy()
            transformed_bound[eligible] += signed * critical * standard_error[eligible]
            if scale == "log":
                bounds[eligible] = np.exp(transformed_bound[eligible])
            else:
                bounds[eligible] = transformed_bound[eligible]
    for index, component in enumerate(COMPONENTS):
        record = {
            "metric_family": metric_family,
            "scope": scope,
            "component": component,
            "direction": direction,
            "scale": scale,
            "point_estimate": float(points[index]),
            "bootstrap_standard_error": float(standard_error[index]),
            "simultaneous_bound": float(bounds[index]),
            "critical_value": float(critical),
            "valid_replicates": int(valid.sum()) if eligible[index] else 0,
            "degenerate_replicates": degenerate if eligible[index] else int(bootstrap.shape[0]),
            "status": status if eligible[index] else ineligible_status,
        }
        result[component] = record
        rows.append(record)
    return result, rows


def build_all_bounds(
    metrics: dict[str, dict[str, Any]],
    inherited_degenerate: np.ndarray,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    lookup: dict[str, Any] = {"absolute": {}, "relative": {}, "family": {}}
    rows: list[dict[str, Any]] = []
    metric_map = {
        "dnn_median": ("dnn_median", "upper"),
        "dnn_p90": ("dnn_p90", "upper"),
        "conditional_variance": ("cvar10", "upper"),
        "oracle_nrmse": ("oracle_nrmse", "upper"),
        "improvement": ("improvement", "lower"),
    }
    for arm in ARMS:
        lookup["absolute"][arm] = {}
        for label, (key, direction) in metric_map.items():
            points = np.asarray([metrics[arm][component][key]["point"] for component in COMPONENTS])
            boot = np.column_stack(
                [metrics[arm][component][key]["boot"] for component in COMPONENTS]
            )
            bound, bound_rows = simultaneous_bound(
                f"ABSOLUTE_{arm}_{label}",
                points,
                boot,
                inherited_degenerate,
                direction=direction,
            )
            lookup["absolute"][arm][label] = bound
            rows.extend(bound_rows)
        lookup["family"][arm] = {}
        for family_index, family in enumerate(FAMILIES):
            points = np.asarray(
                [
                    metrics[arm][component]["oracle_nrmse"]["point_family"][family_index]
                    for component in COMPONENTS
                ]
            )
            boot = np.column_stack(
                [
                    metrics[arm][component]["oracle_nrmse"]["boot_family"][:, family_index]
                    for component in COMPONENTS
                ]
            )
            bound, bound_rows = simultaneous_bound(
                f"ABSOLUTE_{arm}_oracle_nrmse_family_{family}",
                points,
                boot,
                inherited_degenerate,
                direction="upper",
                scope=f"THREE_PRIMARY_COMPONENTS_WITHIN_{family}",
            )
            lookup["family"][arm][family] = bound
            rows.extend(bound_rows)

    for label, key in (
        ("dnn_p90_ratio", "dnn_p90"),
        ("conditional_variance_ratio", "cvar10"),
        ("oracle_nrmse_ratio", "oracle_nrmse"),
    ):
        ss_point = np.asarray([metrics["SS"][component][key]["point"] for component in COMPONENTS])
        ms_point = np.asarray([metrics["MS"][component][key]["point"] for component in COMPONENTS])
        stable = ss_point > 100.0 * DIMENSIONLESS_FLOOR
        point_ratio = np.divide(ms_point, ss_point, out=np.full(3, np.nan), where=ss_point > 0)
        boot_ratio = np.column_stack(
            [
                metrics["MS"][component][key]["boot"]
                / metrics["SS"][component][key]["boot"]
                for component in COMPONENTS
            ]
        )
        bound, bound_rows = simultaneous_bound(
            f"PAIRED_{label}",
            point_ratio,
            boot_ratio,
            inherited_degenerate,
            direction="upper",
            scale="log",
            scope=(
                "THREE_PRIMARY_COMPONENTS"
                if stable.all()
                else "STABLE_PRIMARY_COMPONENT_SUBSET_WITH_UNSTABLE_COMPONENTS_NOT_EVALUABLE"
            ),
            eligible_components=stable,
            ineligible_status=(
                "NOT_EVALUABLE_UNSTABLE_RATIO_NO_FROZEN_ABSOLUTE_DIFFERENCE_MARGIN"
            ),
        )
        lookup["relative"][label] = {
            "bounds": bound,
            "stable": {component: bool(stable[i]) for i, component in enumerate(COMPONENTS)},
        }
        rows.extend(bound_rows)
    return lookup, rows


def metric_scope_rows(
    arm: str,
    component: str,
    metric: dict[str, Any],
    fields: list[tuple[str, dict[str, Any]]],
) -> list[dict[str, Any]]:
    rows = []
    overall = {"arm": arm, "scope": "OVERALL", "scope_id": "ALL", "component": component}
    for name, values in fields:
        overall[name] = values["point"]
    rows.append(overall)
    for family_index, family in enumerate(FAMILIES):
        row = {"arm": arm, "scope": "FAMILY", "scope_id": family, "component": component}
        for name, values in fields:
            row[name] = float(values["point_family"][family_index])
        rows.append(row)
    for fold in FOLDS:
        row = {"arm": arm, "scope": "FOLD", "scope_id": f"FOLD_{fold}", "component": component}
        for name, values in fields:
            row[name] = float(values["point_fold"][fold])
        rows.append(row)
    return rows


def write_metric_outputs(
    arm_results: dict[str, dict[str, Any]],
    metrics: dict[str, dict[str, Any]],
) -> None:
    for arm in ARMS:
        dnn_rows: list[dict[str, Any]] = []
        cvar_rows: list[dict[str, Any]] = []
        oracle_rows: list[dict[str, Any]] = []
        for component in COMPONENTS:
            values = metrics[arm][component]
            dnn_component = metric_scope_rows(
                arm,
                component,
                values,
                [
                    ("dnn_median_k10", values["dnn_median"]),
                    ("dnn_p90_k10", values["dnn_p90"]),
                    ("dnn_median_k5_sensitivity", values["dnn_median_k5_sensitivity"]),
                    ("dnn_p90_k5_sensitivity", values["dnn_p90_k5_sensitivity"]),
                    ("dnn_median_k20_sensitivity", values["dnn_median_k20_sensitivity"]),
                    ("dnn_p90_k20_sensitivity", values["dnn_p90_k20_sensitivity"]),
                    ("sign_disagreement_k10", values["sign_disagreement"]),
                ],
            )
            for row in dnn_component:
                if row["scope"] == "FOLD":
                    fold = int(row["scope_id"].split("_")[1])
                    row["reciprocal_neighbor_fraction_k10"] = arm_results[arm]["folds"][fold][
                        "reciprocal_neighbor_fraction"
                    ]
                    row["neighbor_family_composition_k10"] = json.dumps(
                        arm_results[arm]["folds"][fold]["neighbor_family_composition"],
                        sort_keys=True,
                    )
                else:
                    row["reciprocal_neighbor_fraction_k10"] = float(
                        np.mean(
                            [record["reciprocal_neighbor_fraction"] for record in arm_results[arm]["folds"]]
                        )
                    )
                    row["neighbor_family_composition_k10"] = "FOLD_SPECIFIC_SEE_FOLD_ROWS"
            dnn_rows.extend(dnn_component)
            cvar_rows.extend(
                metric_scope_rows(
                    arm,
                    component,
                    values,
                    [
                        ("conditional_variance_k5_sensitivity", values["cvar5"]),
                        ("conditional_variance_k10_primary", values["cvar10"]),
                        ("conditional_variance_k20_sensitivity", values["cvar20"]),
                    ],
                )
            )
            oracle_component = metric_scope_rows(
                arm,
                component,
                values,
                [
                    ("selected_oracle_nrmse", values["oracle_nrmse"]),
                    ("mean_target_baseline_nrmse", values["baseline_nrmse"]),
                    ("selected_oracle_mae", values["oracle_mae"]),
                    ("selected_oracle_bias", values["oracle_bias"]),
                    ("selected_oracle_angle_degrees", values["oracle_angle_degrees"]),
                ],
            )
            for row in oracle_component:
                row["improvement_over_mean_target_baseline"] = (
                    values["improvement"]["point"] if row["scope"] == "OVERALL" else ""
                )
                row["selected_oracles_by_outer_fold"] = json.dumps(
                    values["selected_oracles_by_fold"], sort_keys=True
                )
                row["nested_selection_used_heldout_target"] = False
            oracle_rows.extend(oracle_component)
        write_csv(SS_DNN if arm == "SS" else MS_DNN, dnn_rows)
        write_csv(SS_CVAR if arm == "SS" else MS_CVAR, cvar_rows)
        write_csv(SS_ORACLE if arm == "SS" else MS_ORACLE, oracle_rows)

    coverage_rows = []
    for arm in ARMS:
        values = metrics[arm][COMPONENTS[0]]["coverage"]
        coverage_rows.append(
            {
                "arm": arm,
                "scope": "OVERALL",
                "scope_id": "ALL",
                "coverage": values["point"],
                "component_independent": True,
                "can_substitute_for_identifiability": False,
            }
        )
        for family_index, family in enumerate(FAMILIES):
            coverage_rows.append(
                {
                    "arm": arm,
                    "scope": "FAMILY",
                    "scope_id": family,
                    "coverage": float(values["point_family"][family_index]),
                    "component_independent": True,
                    "can_substitute_for_identifiability": False,
                }
            )
        for fold in FOLDS:
            coverage_rows.append(
                {
                    "arm": arm,
                    "scope": "FOLD",
                    "scope_id": f"FOLD_{fold}",
                    "coverage": float(values["point_fold"][fold]),
                    "component_independent": True,
                    "can_substitute_for_identifiability": False,
                }
            )
    write_csv(COVERAGE, coverage_rows)


def finite_bound(record: dict[str, Any]) -> bool:
    return record["status"] == "EVALUABLE" and math.isfinite(record["simultaneous_bound"])


def evaluate_verdicts(
    metrics: dict[str, dict[str, Any]],
    bounds: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    rescue_rows: list[dict[str, Any]] = []
    verdict_rows: list[dict[str, Any]] = []
    component_summary: dict[str, Any] = {}
    relative_specs = {
        "dnn_p90": ("dnn_p90", "dnn_p90_ratio", 0.80, 0.90),
        "conditional_variance": ("cvar10", "conditional_variance_ratio", 0.80, 0.90),
        "oracle_nrmse": ("oracle_nrmse", "oracle_nrmse_ratio", 0.85, 0.95),
    }
    for component in COMPONENTS:
        ms = metrics["MS"][component]
        ss = metrics["SS"][component]
        absolute_records = bounds["absolute"]["MS"]
        absolute_checks = {
            "dnn_median_point": ms["dnn_median"]["point"] <= 0.20,
            "dnn_median_ucb": finite_bound(absolute_records["dnn_median"][component])
            and absolute_records["dnn_median"][component]["simultaneous_bound"] <= 0.25,
            "dnn_p90_point": ms["dnn_p90"]["point"] <= 0.50,
            "dnn_p90_ucb": finite_bound(absolute_records["dnn_p90"][component])
            and absolute_records["dnn_p90"][component]["simultaneous_bound"] <= 0.60,
            "conditional_variance_point": ms["cvar10"]["point"] <= 0.25,
            "conditional_variance_ucb": finite_bound(absolute_records["conditional_variance"][component])
            and absolute_records["conditional_variance"][component]["simultaneous_bound"] <= 0.35,
            "oracle_nrmse_point": ms["oracle_nrmse"]["point"] <= 0.60,
            "oracle_nrmse_ucb": finite_bound(absolute_records["oracle_nrmse"][component])
            and absolute_records["oracle_nrmse"][component]["simultaneous_bound"] <= 0.70,
            "improvement_point": ms["improvement"]["point"] >= 0.25,
            "improvement_lcb": finite_bound(absolute_records["improvement"][component])
            and absolute_records["improvement"][component]["simultaneous_bound"] >= 0.15,
        }
        family_point_checks, family_bound_checks = {}, {}
        for family_index, family in enumerate(FAMILIES):
            family_point_checks[family] = bool(
                ms["oracle_nrmse"]["point_family"][family_index] <= 0.85
            )
            family_record = bounds["family"]["MS"][family][component]
            family_bound_checks[family] = bool(
                finite_bound(family_record) and family_record["simultaneous_bound"] <= 1.00
            )
        coverage_overall = ms["coverage"]["point"] >= 0.90
        coverage_family = {
            family: bool(ms["coverage"]["point_family"][i] >= 0.80)
            for i, family in enumerate(FAMILIES)
        }
        six_fold_valid = all(
            np.isfinite(
                [
                    ms["dnn_median"]["point_fold"][fold],
                    ms["dnn_p90"]["point_fold"][fold],
                    ms["cvar10"]["point_fold"][fold],
                    ms["oracle_nrmse"]["point_fold"][fold],
                ]
            ).all()
            for fold in FOLDS
        )
        absolute_checks.update(
            {
                "every_family_nrmse_point": all(family_point_checks.values()),
                "every_family_nrmse_ucb": all(family_bound_checks.values()),
                "coverage_overall": coverage_overall,
                "coverage_every_family": all(coverage_family.values()),
                "all_six_folds_valid": six_fold_valid,
            }
        )
        absolute_evaluable = bool(
            six_fold_valid
            and np.isfinite(
                [
                    ms["dnn_median"]["point"],
                    ms["dnn_p90"]["point"],
                    ms["cvar10"]["point"],
                    ms["oracle_nrmse"]["point"],
                    ms["baseline_nrmse"]["point"],
                    ms["improvement"]["point"],
                    *ms["oracle_nrmse"]["point_family"],
                    ms["coverage"]["point"],
                    *ms["coverage"]["point_family"],
                ]
            ).all()
            and all(
                finite_bound(absolute_records[name][component])
                for name in (
                    "dnn_median",
                    "dnn_p90",
                    "conditional_variance",
                    "oracle_nrmse",
                    "improvement",
                )
            )
            and all(
                finite_bound(bounds["family"]["MS"][family][component])
                for family in FAMILIES
            )
        )
        absolute_pass = absolute_evaluable and all(absolute_checks.values())

        relative_checks: dict[str, bool] = {}
        for label, (metric_key, bound_key, point_threshold, confidence_threshold) in relative_specs.items():
            ss_point = float(ss[metric_key]["point"])
            ms_point = float(ms[metric_key]["point"])
            ratio = ms_point / ss_point if ss_point > 0 else math.nan
            record = bounds["relative"][bound_key]["bounds"][component]
            point_pass = bool(math.isfinite(ratio) and ratio <= point_threshold)
            confidence_pass = bool(
                finite_bound(record) and record["simultaneous_bound"] <= confidence_threshold
            )
            relative_checks[f"{label}_point"] = point_pass
            relative_checks[f"{label}_simultaneous_ucb"] = confidence_pass
            rescue_rows.append(
                {
                    "component": component,
                    "requirement": label,
                    "ss_point": ss_point,
                    "ms_point": ms_point,
                    "point_ratio_or_difference": ratio,
                    "simultaneous_bound": record["simultaneous_bound"],
                    "point_threshold": point_threshold,
                    "confidence_threshold": confidence_threshold,
                    "point_pass": point_pass,
                    "confidence_pass": confidence_pass,
                    "requirement_pass": point_pass and confidence_pass,
                    "status": record["status"],
                }
            )

        ss_median, ms_median = ss["dnn_median"]["point"], ms["dnn_median"]["point"]
        median_stable = ss_median > 100.0 * DIMENSIONLESS_FLOOR
        median_guard = (ms_median - ss_median <= 0.02) and (
            (not median_stable) or ms_median / ss_median <= 1.05
        )
        relative_checks["dnn_median_nonworsening"] = median_guard
        rescue_rows.append(
            {
                "component": component,
                "requirement": "dnn_median_nonworsening",
                "ss_point": ss_median,
                "ms_point": ms_median,
                "point_ratio_or_difference": ms_median - ss_median,
                "simultaneous_bound": "",
                "point_threshold": "difference<=0.02 AND stable_ratio<=1.05",
                "confidence_threshold": "POINT_ONLY",
                "point_pass": median_guard,
                "confidence_pass": True,
                "requirement_pass": median_guard,
                "status": "EVALUABLE" if median_stable else "RATIO_UNSTABLE_ABSOLUTE_GUARD_ONLY",
            }
        )

        worst_ss = float(np.max(ss["oracle_nrmse"]["point_family"]))
        worst_ms = float(np.max(ms["oracle_nrmse"]["point_family"]))
        worst_guard = (
            worst_ms - worst_ss <= 0.05
            and all(family_point_checks.values())
            and all(family_bound_checks.values())
        )
        relative_checks["worst_family_guard"] = worst_guard
        rescue_rows.append(
            {
                "component": component,
                "requirement": "worst_family_nrmse_guard",
                "ss_point": worst_ss,
                "ms_point": worst_ms,
                "point_ratio_or_difference": worst_ms - worst_ss,
                "simultaneous_bound": max(
                    bounds["family"]["MS"][family][component]["simultaneous_bound"]
                    for family in FAMILIES
                ),
                "point_threshold": 0.05,
                "confidence_threshold": "MS_EACH_FAMILY_UCB<=1.00",
                "point_pass": worst_ms - worst_ss <= 0.05 and all(family_point_checks.values()),
                "confidence_pass": all(family_bound_checks.values()),
                "requirement_pass": worst_guard,
                "status": "EVALUABLE" if all(
                    finite_bound(bounds["family"]["MS"][family][component]) for family in FAMILIES
                ) else "NOT_EVALUABLE",
            }
        )

        coverage_family_guard = all(
            ms["coverage"]["point_family"][i]
            >= ss["coverage"]["point_family"][i] - 0.05
            for i in range(4)
        )
        coverage_guard = (
            coverage_overall
            and all(coverage_family.values())
            and ms["coverage"]["point"] >= ss["coverage"]["point"] - 0.05
            and coverage_family_guard
        )
        relative_checks["coverage_guard"] = coverage_guard
        rescue_rows.append(
            {
                "component": component,
                "requirement": "coverage_guard_component_independent",
                "ss_point": ss["coverage"]["point"],
                "ms_point": ms["coverage"]["point"],
                "point_ratio_or_difference": ms["coverage"]["point"] - ss["coverage"]["point"],
                "simultaneous_bound": "NOT_APPLICABLE",
                "point_threshold": "MS>=0.90,each_family>=0.80,drop<=0.05",
                "confidence_threshold": "POINT_ONLY",
                "point_pass": coverage_guard,
                "confidence_pass": True,
                "requirement_pass": coverage_guard,
                "status": "EVALUABLE",
            }
        )

        relative_fold_valid = all(
            np.isfinite(
                [
                    metrics[arm][component][key]["point_fold"][fold]
                    for arm in ARMS
                    for key in ("dnn_p90", "cvar10", "oracle_nrmse")
                ]
            ).all()
            for fold in FOLDS
        )
        reversal_folds = []
        for fold in FOLDS:
            reversed_all = all(
                metrics["MS"][component][key]["point_fold"][fold]
                > metrics["SS"][component][key]["point_fold"][fold] + DIMENSIONLESS_FLOOR
                for key in ("dnn_p90", "cvar10", "oracle_nrmse")
            )
            if reversed_all:
                reversal_folds.append(f"FOLD_{fold}")
        no_reversal = relative_fold_valid and not reversal_folds
        relative_checks["no_fold_three_effect_reversal"] = no_reversal
        rescue_rows.append(
            {
                "component": component,
                "requirement": "no_fold_three_effect_reversal",
                "ss_point": "FOLDWISE",
                "ms_point": "FOLDWISE",
                "point_ratio_or_difference": "|".join(reversal_folds),
                "simultaneous_bound": "NOT_APPLICABLE",
                "point_threshold": "ZERO_REVERSAL_FOLDS",
                "confidence_threshold": "POINT_ONLY",
                "point_pass": no_reversal,
                "confidence_pass": True,
                "requirement_pass": no_reversal,
                "status": "EVALUABLE" if relative_fold_valid else "NOT_EVALUABLE",
            }
        )
        relative_evaluable = bool(
            relative_fold_valid
            and np.isfinite(
                [
                    ss["dnn_median"]["point"],
                    ms["dnn_median"]["point"],
                    ss["dnn_p90"]["point"],
                    ms["dnn_p90"]["point"],
                    ss["cvar10"]["point"],
                    ms["cvar10"]["point"],
                    ss["oracle_nrmse"]["point"],
                    ms["oracle_nrmse"]["point"],
                    *ss["oracle_nrmse"]["point_family"],
                    *ms["oracle_nrmse"]["point_family"],
                    ss["coverage"]["point"],
                    ms["coverage"]["point"],
                    *ss["coverage"]["point_family"],
                    *ms["coverage"]["point_family"],
                ]
            ).all()
            and all(
                finite_bound(bounds["relative"][bound_key]["bounds"][component])
                for _, bound_key, _, _ in relative_specs.values()
            )
            and all(
                finite_bound(bounds["family"]["MS"][family][component])
                for family in FAMILIES
            )
        )
        relative_pass = relative_evaluable and all(relative_checks.values())
        component_evaluable = absolute_evaluable and relative_evaluable
        component_pass = component_evaluable and absolute_pass and relative_pass
        if not component_evaluable:
            status = "H_MSO01_COMPONENT_NOT_EVALUABLE"
        elif component_pass:
            status = "H_MSO01_COMPONENT_IDENTIFIABILITY_AND_RESCUE_QUALIFIED"
        elif absolute_pass:
            status = "IDENTIFIABLE_BUT_MULTISCALE_RESCUE_NOT_ESTABLISHED"
        elif relative_pass:
            status = "RELATIVE_RESCUE_OBSERVED_BUT_ABSOLUTE_IDENTIFIABILITY_NOT_QUALIFIED"
        else:
            status = "ABSOLUTE_IDENTIFIABILITY_AND_RELATIVE_RESCUE_NOT_QUALIFIED"
        verdict_row = {
            "component": component,
            "ABSOLUTE_IDENTIFIABILITY_PASS": absolute_pass,
            "RELATIVE_MULTISCALE_RESCUE_PASS": relative_pass,
            "COMPONENT_H_MSO01_PASS": component_pass,
            "ABSOLUTE_IDENTIFIABILITY_EVALUABLE": absolute_evaluable,
            "RELATIVE_MULTISCALE_RESCUE_EVALUABLE": relative_evaluable,
            "COMPONENT_H_MSO01_EVALUABLE": component_evaluable,
            "component_status": status,
            "absolute_gate_checks": json.dumps(absolute_checks, sort_keys=True),
            "relative_gate_checks": json.dumps(relative_checks, sort_keys=True),
            "family_point_checks": json.dumps(family_point_checks, sort_keys=True),
            "family_simultaneous_ucb_checks": json.dumps(family_bound_checks, sort_keys=True),
            "coverage_family_checks": json.dumps(coverage_family, sort_keys=True),
            "reversal_folds": "|".join(reversal_folds),
        }
        verdict_rows.append(verdict_row)
        component_summary[component] = {
            "absolute_pass": absolute_pass,
            "relative_rescue_pass": relative_pass,
            "component_pass": component_pass,
            "absolute_evaluable": absolute_evaluable,
            "relative_rescue_evaluable": relative_evaluable,
            "component_evaluable": component_evaluable,
            "status": status,
            "absolute_checks": absolute_checks,
            "relative_checks": relative_checks,
        }
    global_evaluable = all(row["COMPONENT_H_MSO01_EVALUABLE"] for row in verdict_rows)
    global_pass = global_evaluable and all(
        row["COMPONENT_H_MSO01_PASS"] for row in verdict_rows
    )
    summary = {
        "components": component_summary,
        "global_evaluable": global_evaluable,
        "global_pass": global_pass,
        "global_status": (
            "H_MSO01_MULTISCALE_IDENTIFIABILITY_RESCUE_NOT_EVALUABLE"
            if not global_evaluable
            else "H_MSO01_MULTISCALE_IDENTIFIABILITY_RESCUE_QUALIFIED"
            if global_pass
            else "H_MSO01_MULTISCALE_IDENTIFIABILITY_RESCUE_NOT_QUALIFIED"
        ),
        "mso03_deterministic_closure_baseline_eligible": global_pass,
        "neural_training_authorized": False,
        "attention_authorized": False,
        "learned_operator_authorized": False,
    }
    return rescue_rows, verdict_rows, summary


def serializable_metric_summary(metrics: dict[str, dict[str, Any]], bounds: dict[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for arm in ARMS:
        output[arm] = {}
        for component in COMPONENTS:
            values = metrics[arm][component]
            output[arm][component] = {
                "dnn_median": values["dnn_median"]["point"],
                "dnn_median_simultaneous_ucb": bounds["absolute"][arm]["dnn_median"][component]["simultaneous_bound"],
                "dnn_p90": values["dnn_p90"]["point"],
                "dnn_p90_simultaneous_ucb": bounds["absolute"][arm]["dnn_p90"][component]["simultaneous_bound"],
                "conditional_variance": values["cvar10"]["point"],
                "conditional_variance_simultaneous_ucb": bounds["absolute"][arm]["conditional_variance"][component]["simultaneous_bound"],
                "oracle_nrmse": values["oracle_nrmse"]["point"],
                "oracle_nrmse_simultaneous_ucb": bounds["absolute"][arm]["oracle_nrmse"][component]["simultaneous_bound"],
                "baseline_nrmse": values["baseline_nrmse"]["point"],
                "improvement": values["improvement"]["point"],
                "improvement_simultaneous_lcb": bounds["absolute"][arm]["improvement"][component]["simultaneous_bound"],
                "family_nrmse": {
                    family: float(values["oracle_nrmse"]["point_family"][i])
                    for i, family in enumerate(FAMILIES)
                },
                "coverage": values["coverage"]["point"],
                "coverage_family": {
                    family: float(values["coverage"]["point_family"][i])
                    for i, family in enumerate(FAMILIES)
                },
                "selected_oracles_by_fold": values["selected_oracles_by_fold"],
            }
    output["paired_ratios"] = {}
    for component in COMPONENTS:
        output["paired_ratios"][component] = {}
        for label, metric_key, bound_key in (
            ("dnn_p90", "dnn_p90", "dnn_p90_ratio"),
            ("conditional_variance", "cvar10", "conditional_variance_ratio"),
            ("oracle_nrmse", "oracle_nrmse", "oracle_nrmse_ratio"),
        ):
            denominator = metrics["SS"][component][metric_key]["point"]
            ratio = (
                metrics["MS"][component][metric_key]["point"] / denominator
                if denominator > 0
                else math.nan
            )
            output["paired_ratios"][component][label] = {
                "ratio": ratio,
                "reduction": 1.0 - ratio,
                "simultaneous_ucb": bounds["relative"][bound_key]["bounds"][component]["simultaneous_bound"],
                "status": bounds["relative"][bound_key]["bounds"][component]["status"],
            }
    return output


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


def main() -> None:
    global FORMAL_STAGING
    if SUMMARY.exists():
        raise RuntimeError("MSO02B formal outputs already finalized; refusing replacement")
    final_outputs = (
        SS_DNN,
        MS_DNN,
        SS_CVAR,
        MS_CVAR,
        SS_ORACLE,
        MS_ORACLE,
        COVERAGE,
        RESCUE,
        BOUNDS,
        VERDICTS,
        FIREWALL,
        JOIN_AUDIT,
    )
    freeze = verify_frozen_inputs()
    freeze_sha = sha256(PRECOMPUTE)
    execution_erratum = freeze["formal_execution_erratum"]
    execution_erratum_sha = sha256(EXECUTION_ERRATUM)
    evaluator_sha = sha256(Path(__file__).resolve())
    target_store_sha = freeze["verified_target_store_sha256"]
    failed_attempt_counts = execution_erratum["failed_attempt_authorized_access_counts"]
    governance_audit_counts = execution_erratum[
        "post_failure_governance_audit_access_counts_before_corrective_resume"
    ]
    FORMAL_STAGING = OUT / ".formal_staging" / freeze_sha
    if (FORMAL_STAGING / SUMMARY.name).exists():
        staged_summary = json.loads(
            (FORMAL_STAGING / SUMMARY.name).read_text(encoding="utf-8")
        )
        if (
            staged_summary.get("formal_execution_erratum_sha256")
            != execution_erratum_sha
            or staged_summary.get("formal_evaluator_sha256") != evaluator_sha
        ):
            raise RuntimeError("complete formal staging has stale erratum/evaluator identity")
        publish_staged_outputs()
        completed = json.loads(SUMMARY.read_text(encoding="utf-8"))
        print(
            json.dumps(
                {
                    "terminal_status": completed["terminal_status"],
                    "global_h_mso01": completed["verdict"]["global_status"],
                    "mso03_deterministic_closure_baseline_eligible": completed["verdict"][
                        "mso03_deterministic_closure_baseline_eligible"
                    ],
                    "publication_resumed_from_complete_staging": True,
                },
                sort_keys=True,
            ),
            flush=True,
        )
        return
    if any(path.exists() for path in final_outputs):
        raise RuntimeError("partial final MSO02B outputs exist without complete staging")
    FORMAL_STAGING.mkdir(parents=True, exist_ok=True)
    target_ledger = json.loads(TARGET_LEDGER.read_text(encoding="utf-8"))
    if (
        target_ledger["qualified_case_count"] != 384
        or target_ledger["failed_case_count"] != 0
        or target_ledger["status"] != "MSO02B_TARGET_REFERENCE_QUALIFIED"
        or target_ledger["target_store_sha256"] != target_store_sha
    ):
        raise RuntimeError("MSO02B_TARGET_REFERENCE_QUALIFICATION_NOT_COMPLETE")

    frozen_before = dict(freeze["verified_frozen_input_sha256"])
    formal_data, cases = load_formal_data()
    normalization = json.loads(NORMALIZATION.read_text(encoding="utf-8"))
    coverage_geometry = json.loads(COVERAGE_GEOMETRY.read_text(encoding="utf-8"))

    # The single executable executes SS first and MS second.  All settings are
    # already hash-bound; no result-dependent branch can modify the second arm.
    arm_results: dict[str, dict[str, Any]] = {}
    arm_results["SS"] = run_arm(
        "SS",
        formal_data["features"]["SS"],
        formal_data["targets"],
        formal_data["meta"],
        normalization,
        coverage_geometry,
        freeze_sha,
        execution_erratum_sha,
        evaluator_sha,
        target_store_sha,
    )
    after_ss = {
        relative: sha256(ROOT / relative)
        for relative in freeze["frozen_input_sha256"]
    }
    if after_ss != frozen_before:
        raise RuntimeError("MSO02B_POST_TARGET_FROZEN_INPUT_MODIFICATION_AFTER_SS")
    arm_results["MS"] = run_arm(
        "MS",
        formal_data["features"]["MS"],
        formal_data["targets"],
        formal_data["meta"],
        normalization,
        coverage_geometry,
        freeze_sha,
        execution_erratum_sha,
        evaluator_sha,
        target_store_sha,
    )
    after_ms = {
        relative: sha256(ROOT / relative)
        for relative in freeze["frozen_input_sha256"]
    }
    if after_ms != frozen_before:
        raise RuntimeError("MSO02B_POST_TARGET_FROZEN_INPUT_MODIFICATION_AFTER_MS")
    if (
        arm_results["SS"]["random_baseline_index_sha256_by_fold"]
        != arm_results["MS"]["random_baseline_index_sha256_by_fold"]
    ):
        raise RuntimeError("SS/MS matched-random identities differ")

    counts, inherited_degenerate, bootstrap_audit = load_bootstrap_counts(cases)
    cells = cell_case_indices(cases)
    metrics = {
        arm: aggregate_arm_metrics(arm_results[arm], counts, cells) for arm in ARMS
    }
    bound_lookup, bound_rows = build_all_bounds(metrics, inherited_degenerate)
    write_metric_outputs(arm_results, metrics)
    write_csv(BOUNDS, bound_rows)
    rescue_rows, verdict_rows, verdict_summary = evaluate_verdicts(metrics, bound_lookup)
    write_csv(RESCUE, rescue_rows)
    write_csv(VERDICTS, verdict_rows)

    numerical_fit_failures = {
        (
            record["arm"],
            int(record["outer_fold"]),
            int(record["inner_validation_fold"]),
            record["candidate"],
        )
        for arm in ARMS
        for record in arm_results[arm]["selection_records"]
        if record["candidate"] in ("ridge", "polynomial_ridge")
        and bool(record.get("failure"))
    }
    for arm in ARMS:
        for fold_record in arm_results[arm]["folds"]:
            for candidate in fold_record.get("outer_candidate_fit_failures", {}):
                if candidate in ("ridge", "polynomial_ridge"):
                    numerical_fit_failures.add(
                        (arm, int(fold_record["outer_fold"]), -1, candidate)
                    )
    numerical_fit_attempts = 144
    numerical_fit_failure_count = len(numerical_fit_failures)
    failed_attempt_fit_attempts = int(
        failed_attempt_counts["oracle_ridge_or_polynomial_bundle_fit_attempts"]
    )
    failed_attempt_fit_outcome_unrecorded = int(
        failed_attempt_counts[
            "oracle_ridge_or_polynomial_bundle_fit_outcome_unrecorded"
        ]
    )
    if failed_attempt_fit_attempts != failed_attempt_fit_outcome_unrecorded:
        raise RuntimeError("failed-attempt oracle fit accounting is not closed")
    total_numerical_fit_attempts = (
        numerical_fit_attempts + failed_attempt_fit_attempts
    )
    current_numerical_fit_succeeded = numerical_fit_attempts - numerical_fit_failure_count
    formal_target_payload_reads = 1 + int(
        failed_attempt_counts["formal_target_store_payload_reads"]
    )
    formal_observable_matrix_reads = 1 + int(
        failed_attempt_counts["formal_observable_store_matrix_reads"]
    )
    formal_target_opaque_hash_reads = 1 + int(
        failed_attempt_counts["formal_target_store_opaque_hash_reads"]
    )
    formal_observable_opaque_hash_reads = 3 + int(
        failed_attempt_counts["formal_observable_store_opaque_hash_reads"]
    )
    governance_target_opaque_hash_reads = int(
        governance_audit_counts["target_store_opaque_hash_reads"]
    )
    governance_observable_opaque_hash_reads = int(
        governance_audit_counts["observable_store_opaque_hash_reads"]
    )

    firewall = {
        "schema_version": "1.0.0",
        "stage": "MSO-02B",
        "status": "PASS_WITH_DISCLOSED_UNUSED_ACCIDENTAL_HISTORICAL_TEXT_MATCH",
        "authorized_target_access_counts": {
            **target_ledger["authorized_target_access_counts"],
            "source_import_qa_reference_evaluations": 384,
            "formal_execution_attempts": 2,
            "failed_pre_metric_execution_attempts": 1,
            "formal_target_store_payload_reads": formal_target_payload_reads,
            "formal_observable_store_matrix_reads": formal_observable_matrix_reads,
            "formal_target_store_opaque_hash_reads": formal_target_opaque_hash_reads,
            "formal_observable_store_opaque_hash_reads": formal_observable_opaque_hash_reads,
            "post_failure_governance_target_store_opaque_hash_reads": governance_target_opaque_hash_reads,
            "post_failure_governance_observable_store_opaque_hash_reads": governance_observable_opaque_hash_reads,
            "formal_ss_arm_evaluations": 3,
            "formal_ms_arm_evaluations": 3,
            "paired_rescue_component_evaluations": 3,
            "conditional_variance_component_arm_evaluations": 6,
            "oracle_ridge_or_polynomial_bundle_fit_attempts": total_numerical_fit_attempts,
            "oracle_ridge_or_polynomial_bundle_fit_succeeded_recorded": current_numerical_fit_succeeded,
            "oracle_ridge_or_polynomial_bundle_fit_failed_recorded": numerical_fit_failure_count,
            "oracle_ridge_or_polynomial_bundle_fit_outcome_unrecorded": failed_attempt_fit_outcome_unrecorded,
            "bootstrap_replicates_consumed": 10000,
        },
        "prohibited_activity_counts": {
            "neural_model": 0,
            "optimizer": 0,
            "training": 0,
            "time_integration": 0,
            "solver_in_loop": 0,
            "rollout": 0,
            "sealed_test": 0,
            "arc_access": 0,
            "target_derived_feature_modification": 0,
            "target_derived_scale_modification": 0,
            "target_derived_fold_modification": 0,
            "target_derived_normalization_modification": 0,
            "target_derived_gate_modification": 0,
            "target_derived_oracle_family_modification": 0,
            "case_replacement_after_target_access": 0,
        },
        "governance_disclosure": {
            "historical_h3_accidental_text_match_read": 1,
            "historical_h3_result_used": 0,
            "historical_h3_payload_file_opened": 0,
            "description": "A source-audit rg result included one pre-existing provenance-summary line. It was not used for code, thresholds, metrics, tuning, or verdicts.",
            "formal_executable_historical_h3_read_count": 0,
            "formal_execution_erratum": {
                "path": str(EXECUTION_ERRATUM.relative_to(ROOT)),
                "sha256": sha256(EXECUTION_ERRATUM),
                "failed_attempt_exception": execution_erratum["failed_attempt"]["exception"],
                "heldout_metric_rows_written": execution_erratum["failed_attempt"][
                    "heldout_metric_rows_written"
                ],
                "scientific_result_or_verdict_written": False,
                "correction_used_target_values_or_outcomes": False,
            },
        },
        "ss_then_ms_no_adaptive_modification": True,
        "matched_random_identity_equal_between_arms": True,
        "observable_store_sha256_before": frozen_before[
            "06_experiments/mso02a/observable/mso02a_observable_store.npz"
        ],
        "observable_store_sha256_after": after_ms[
            "06_experiments/mso02a/observable/mso02a_observable_store.npz"
        ],
        "all_frozen_input_hashes_unchanged_after_ss_and_ms": True,
        "bootstrap_decode_audit": bootstrap_audit,
    }
    write_json(FIREWALL, firewall)

    target_ledger["authorized_target_access_counts"]["formal_execution_attempts"] = 2
    target_ledger["authorized_target_access_counts"]["failed_pre_metric_execution_attempts"] = 1
    access_counts = target_ledger["authorized_target_access_counts"]
    access_counts["target_store_payload_reads_by_target_builder"] = access_counts.pop(
        "target_store_payload_reads"
    )
    access_counts["target_store_opaque_hash_reads_by_target_builder"] = access_counts.pop(
        "target_store_opaque_hash_reads"
    )
    access_counts.pop("target_store_reads", None)
    access_counts["observable_store_opaque_hash_reads_by_target_builder"] = access_counts.pop(
        "observable_store_opaque_hash_reads"
    )
    access_counts["formal_evaluator_target_store_payload_reads"] = formal_target_payload_reads
    access_counts["formal_evaluator_observable_store_matrix_reads"] = formal_observable_matrix_reads
    access_counts["formal_evaluator_target_store_opaque_hash_reads"] = formal_target_opaque_hash_reads
    access_counts["formal_evaluator_observable_store_opaque_hash_reads"] = formal_observable_opaque_hash_reads
    access_counts["post_failure_governance_target_store_opaque_hash_reads"] = governance_target_opaque_hash_reads
    access_counts["post_failure_governance_observable_store_opaque_hash_reads"] = governance_observable_opaque_hash_reads
    access_counts["target_store_payload_reads_total_through_formal_evaluator"] = (
        access_counts["target_store_payload_reads_by_target_builder"]
        + formal_target_payload_reads
    )
    access_counts["target_store_opaque_hash_reads_total_through_formal_evaluator"] = (
        access_counts["target_store_opaque_hash_reads_by_target_builder"]
        + formal_target_opaque_hash_reads
        + governance_target_opaque_hash_reads
    )
    access_counts["observable_store_opaque_hash_reads_total_through_formal_evaluator"] = (
        access_counts["observable_store_opaque_hash_reads_by_target_builder"]
        + formal_observable_opaque_hash_reads
        + governance_observable_opaque_hash_reads
    )
    target_ledger["authorized_target_access_counts"]["h3_component_arm_evaluations"] = 6
    target_ledger["authorized_target_access_counts"]["oracle_bundle_fit_attempts"] = total_numerical_fit_attempts
    target_ledger["authorized_target_access_counts"]["oracle_bundle_fit_succeeded_recorded"] = (
        current_numerical_fit_succeeded
    )
    target_ledger["authorized_target_access_counts"]["oracle_bundle_fit_failed_recorded"] = (
        numerical_fit_failure_count
    )
    target_ledger["authorized_target_access_counts"]["oracle_bundle_fit_outcome_unrecorded"] = (
        failed_attempt_fit_outcome_unrecorded
    )
    target_ledger["authorized_target_access_counts"]["paired_bootstrap_replicates"] = 10000
    target_ledger["source_import_qa_reference_evaluation_count"] = 384
    target_ledger["historical_h3_accidental_text_match_read_count"] = 1
    target_ledger["historical_h3_result_used_count"] = 0
    target_ledger["observable_store_sha256_after_formal_evaluation"] = after_ms[
        "06_experiments/mso02a/observable/mso02a_observable_store.npz"
    ]
    target_ledger["formal_evaluation_status"] = verdict_summary["global_status"]
    target_ledger["formal_execution_erratum_sha256"] = sha256(EXECUTION_ERRATUM)
    write_json(TARGET_LEDGER, target_ledger)

    metric_summary = serializable_metric_summary(metrics, bound_lookup)
    terminal = (
        "MSO02B_PAIRED_PRELEARNING_IDENTIFIABILITY_REQUALIFICATION_NOT_EVALUABLE"
        if not verdict_summary["global_evaluable"]
        else "MSO02B_PAIRED_PRELEARNING_IDENTIFIABILITY_REQUALIFICATION_COMPLETE_QUALIFIED"
        if verdict_summary["global_pass"]
        else "MSO02B_PAIRED_PRELEARNING_IDENTIFIABILITY_REQUALIFICATION_COMPLETE_NOT_QUALIFIED"
    )
    summary = {
        "schema_version": "1.0.0",
        "stage": "MSO-02B",
        "terminal_status": terminal,
        "target_reference_qualified_case_count": 384,
        "target_reference_failed_case_count": 0,
        "target_definition": "CONTINUUM_ANALYTICAL_REFERENCE_MINUS_LAMBDA_1_FROZEN_BASE_SPH",
        "observable_store_unchanged": True,
        "ss_feature_dimension": 39,
        "ms_feature_dimension": 110,
        "formal_particle_count_per_case": 128,
        "formal_sample_row_count": 49152,
        "bootstrap_replicate_count": 10000,
        "metrics": metric_summary,
        "verdict": verdict_summary,
        "coverage_can_substitute_for_identifiability": False,
        "post_target_modification_counts": {
            "feature": 0,
            "scale": 0,
            "gate": 0,
            "fold": 0,
            "normalization": 0,
        },
        "neural_model_count": 0,
        "optimizer_count": 0,
        "training_count": 0,
        "mso03_executed": False,
        "target_precompute_freeze_sha256": freeze_sha,
        "formal_execution_erratum_sha256": execution_erratum_sha,
        "formal_evaluator_sha256": evaluator_sha,
        "failed_pre_metric_execution_attempt_count": 1,
        "failed_attempt_oracle_bundle_fit_attempts": failed_attempt_fit_attempts,
        "failed_attempt_oracle_bundle_fit_outcome_unrecorded": failed_attempt_fit_outcome_unrecorded,
        "firewall_audit_sha256": sha256(output_destination(FIREWALL)),
    }
    write_json(SUMMARY, json_safe(summary))
    publish_staged_outputs()
    print(
        json.dumps(
            {
                "terminal_status": terminal,
                "global_h_mso01": verdict_summary["global_status"],
                "mso03_deterministic_closure_baseline_eligible": verdict_summary[
                    "mso03_deterministic_closure_baseline_eligible"
                ],
            },
            sort_keys=True,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
