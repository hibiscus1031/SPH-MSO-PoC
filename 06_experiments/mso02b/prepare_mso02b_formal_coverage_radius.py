#!/usr/bin/env python3
"""Freeze target-blind formal-sample coverage radii for MSO-02B.

The calibration population is exactly the prospectively selected 128 particles
per formal case.  For each arm and held-out outer fold, the development rows
are queried against the same development population while applying the same
case, lineage, and nonzero disorder-seed exclusions as the formal evaluator.
The radius is the inverted-CDF p95 of each development row's tenth permitted
neighbour distance.  No target or analytical reference is read.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
from scipy.spatial import cKDTree


ROOT = Path(__file__).resolve().parents[2]
FORMAL = ROOT / "05_registries/mso02a_formal_fresh_atlas_registry.json"
SAMPLE = ROOT / "05_registries/mso02b_formal_particle_sample_registry.json"
OBSERVABLE = ROOT / "06_experiments/mso02a/observable/mso02a_observable_store.npz"
NORMALIZATION = ROOT / "06_experiments/mso02a/fold_normalization_registry.json"
OUTPUT = ROOT / "05_registries/mso02b_formal_coverage_radius_registry.json"
PRIMARY_K = 10


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def ordered_indices(indices: np.ndarray, sample_key: np.ndarray) -> np.ndarray:
    hashes = np.asarray(
        [hashlib.sha256(str(sample_key[index]).encode("utf-8")).hexdigest() for index in indices]
    )
    order = np.lexsort((sample_key[indices], hashes))
    return indices[order]


def kth_permitted_distances(
    x: np.ndarray,
    case_id: np.ndarray,
    lineage: np.ndarray,
    seed: np.ndarray,
) -> np.ndarray:
    """Return each row's exact tenth permitted neighbour distance in chunks."""

    tree = cKDTree(x, compact_nodes=True, balanced_tree=True)
    result = np.full(x.shape[0], np.nan, dtype=np.float64)
    query_schedule = tuple(
        sorted(set(min(x.shape[0], value) for value in (256, 2048, 8192, x.shape[0])))
    )
    for chunk_start in range(0, x.shape[0], 128):
        chunk = np.arange(chunk_start, min(chunk_start + 128, x.shape[0]), dtype=np.int64)
        unresolved = chunk.copy()
        for use_k in query_schedule:
            if unresolved.size == 0:
                break
            distances, candidates = tree.query(
                x[unresolved], k=use_k, eps=0, p=2, workers=1
            )
            if use_k == 1:
                distances, candidates = distances[:, None], candidates[:, None]
            keep_unresolved: list[int] = []
            for local, query_row in enumerate(unresolved):
                candidate = np.asarray(candidates[local], dtype=np.int64)
                distance = np.asarray(distances[local], dtype=np.float64)
                permitted = (
                    (case_id[candidate] != case_id[query_row])
                    & (lineage[candidate] != lineage[query_row])
                )
                query_seed = int(seed[query_row])
                if query_seed != 0:
                    permitted &= seed[candidate] != query_seed
                permitted_distance = np.sort(distance[permitted], kind="stable")
                if permitted_distance.size >= PRIMARY_K:
                    result[query_row] = float(permitted_distance[PRIMARY_K - 1])
                else:
                    keep_unresolved.append(int(query_row))
            unresolved = np.asarray(keep_unresolved, dtype=np.int64)
        if unresolved.size:
            raise RuntimeError(
                f"formal coverage calibration has insufficient permitted neighbours: "
                f"chunk={chunk_start} unresolved={unresolved.size}"
            )
    if not np.isfinite(result).all():
        raise RuntimeError("formal coverage radii are nonfinite")
    return result


def main() -> None:
    formal = json.loads(FORMAL.read_text(encoding="utf-8"))
    sample = json.loads(SAMPLE.read_text(encoding="utf-8"))
    normalization = json.loads(NORMALIZATION.read_text(encoding="utf-8"))
    cases = sorted(formal["cases"], key=lambda row: int(row["formal_case_index"]))
    samples = sorted(sample["cases"], key=lambda row: int(row["formal_case_index"]))
    if len(cases) != 384 or len(samples) != 384:
        raise RuntimeError("formal coverage population mismatch")

    full_rows: list[int] = []
    case_ids: list[str] = []
    lineages: list[str] = []
    seeds: list[int] = []
    folds: list[int] = []
    sample_keys: list[str] = []
    for case, registered in zip(cases, samples, strict=True):
        case_index = int(case["formal_case_index"])
        if int(registered["formal_case_index"]) != case_index:
            raise RuntimeError("formal coverage sample order mismatch")
        particles = [int(value) for value in registered["particle_ids_in_hash_order"]]
        if len(particles) != 128 or len(set(particles)) != 128:
            raise RuntimeError(f"formal coverage sample mismatch case={case_index}")
        for particle in particles:
            full_rows.append(case_index * 576 + particle)
            case_ids.append(case["case_id"])
            lineages.append(case["field_lineage_id"])
            seeds.append(int(case["jitter_seed"]))
            folds.append(int(case["fold"].split("_")[1]))
            sample_keys.append(f"{case['case_id']}|{particle}")

    full = np.asarray(full_rows, dtype=np.int64)
    meta = {
        "case_id": np.asarray(case_ids),
        "lineage": np.asarray(lineages),
        "seed": np.asarray(seeds, dtype=np.int64),
        "fold": np.asarray(folds, dtype=np.int8),
        "sample_key": np.asarray(sample_keys),
    }
    with np.load(OBSERVABLE, allow_pickle=False) as store:
        features = {
            "SS": np.asarray(store["ss_features"][full], dtype=np.float64),
            "MS": np.asarray(store["ms_features"][full], dtype=np.float64),
        }
    if features["SS"].shape != (49152, 39) or features["MS"].shape != (49152, 110):
        raise RuntimeError("formal coverage observable shape mismatch")

    arms: dict[str, Any] = {}
    for arm in ("SS", "MS"):
        records = []
        for outer in range(6):
            development = np.flatnonzero(meta["fold"] != outer)
            development = ordered_indices(development, meta["sample_key"])
            fold_record = next(
                row
                for row in normalization["arms"][arm]["folds"]
                if row["held_out_fold"] == f"FOLD_{outer}"
            )
            median = np.asarray(fold_record["median"], dtype=np.float64)
            divisor = np.asarray(fold_record["divisor"], dtype=np.float64)
            x = (features[arm][development] - median) / divisor
            if not np.isfinite(x).all():
                raise RuntimeError(f"nonfinite formal coverage geometry {arm} fold={outer}")
            radii = kth_permitted_distances(
                x,
                meta["case_id"][development],
                meta["lineage"][development],
                meta["seed"][development],
            )
            record = {
                "held_out_fold": f"FOLD_{outer}",
                "development_sample_row_count": int(development.size),
                "unique_development_case_count": int(
                    np.unique(meta["case_id"][development]).size
                ),
                "k10_radius_p95": float(
                    np.quantile(radii, 0.95, method="inverted_cdf")
                ),
                "k10_radius_max": float(np.max(radii)),
                "k10_radius_min": float(np.min(radii)),
                "finite": True,
            }
            records.append(record)
            print(
                f"MSO02B_FORMAL_COVERAGE arm={arm} outer={outer} "
                f"rows={development.size} radius={record['k10_radius_p95']:.17g}",
                flush=True,
            )
        arms[arm] = {
            "feature_dimension": int(features[arm].shape[1]),
            "folds": records,
        }

    write_json(
        OUTPUT,
        {
            "schema_version": "1.0.0",
            "stage": "MSO-02B",
            "status": "FROZEN_TARGET_BLIND_BEFORE_FIRST_FORMAL_DEFECT_OR_TARGET",
            "formal_sample_particles_per_case": 128,
            "formal_sample_row_count": 49152,
            "primary_k": PRIMARY_K,
            "distance": "PLAIN_EUCLIDEAN_AFTER_EXACT_FROZEN_ARM_OUTER_FOLD_NORMALIZATION",
            "calibration": "DEVELOPMENT_SAMPLE_LEAVE_ONE_COMPLETE_CASE_LINEAGE_AND_NONZERO_SEED_OUT",
            "calibration_statistic": "TENTH_PERMITTED_DEVELOPMENT_NEIGHBOUR_DISTANCE",
            "quantile": "NUMPY_INVERTED_CDF_P95",
            "heldout_criterion": "TENTH_PERMITTED_DEVELOPMENT_NEIGHBOUR_DISTANCE_LE_RADIUS",
            "exclusions": {
                "same_case": True,
                "same_field_lineage": True,
                "same_nonzero_disorder_seed": True,
                "zero_seed_is_shared_stochastic_exclusion": False,
            },
            "mso02a_16_particle_geometry_radius_used": False,
            "target_or_reference_read_count": 0,
            "observable_matrix_read_count": 1,
            "source_sha256": {
                str(FORMAL.relative_to(ROOT)): sha256(FORMAL),
                str(SAMPLE.relative_to(ROOT)): sha256(SAMPLE),
                str(OBSERVABLE.relative_to(ROOT)): sha256(OBSERVABLE),
                str(NORMALIZATION.relative_to(ROOT)): sha256(NORMALIZATION),
            },
            "arms": arms,
        },
    )
    print(
        json.dumps(
            {
                "status": "MSO02B_FORMAL_COVERAGE_RADIUS_FROZEN_TARGET_BLIND",
                "output_sha256": sha256(OUTPUT),
            },
            sort_keys=True,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
