#!/usr/bin/env python3
"""Target-blind numerical preflight for the frozen non-neural oracle solvers."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.preprocessing import PolynomialFeatures


ROOT = Path(__file__).resolve().parents[2]
FORMAL = ROOT / "05_registries/mso02a_formal_fresh_atlas_registry.json"
SAMPLE = ROOT / "05_registries/mso02b_formal_particle_sample_registry.json"
OBSERVABLE = ROOT / "06_experiments/mso02a/observable/mso02a_observable_store.npz"
NORMALIZATION = ROOT / "06_experiments/mso02a/fold_normalization_registry.json"
SEMANTICS = ROOT / "05_registries/mso02b_analysis_semantics_registry.json"
OUTPUT = ROOT / "05_registries/mso02b_oracle_numerical_preflight.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def main() -> None:
    target_access_artifacts = (
        ROOT / "06_experiments/mso02b/target_ref/mso02b_target_store.npz",
        ROOT / "06_experiments/mso02b/target_reference_qualification.csv",
        ROOT / "06_experiments/mso02b/target_access_ledger.json",
    )
    if any(path.exists() for path in target_access_artifacts):
        raise RuntimeError("formal target access occurred; target-blind preflight is immutable")
    cases = sorted(
        json.loads(FORMAL.read_text(encoding="utf-8"))["cases"],
        key=lambda row: int(row["formal_case_index"]),
    )
    sampled = sorted(
        json.loads(SAMPLE.read_text(encoding="utf-8"))["cases"],
        key=lambda row: int(row["formal_case_index"]),
    )
    rows, folds = [], []
    for case, sample in zip(cases, sampled, strict=True):
        for particle in sample["particle_ids_in_hash_order"]:
            rows.append(int(case["formal_case_index"]) * 576 + int(particle))
            folds.append(int(case["fold"].split("_")[1]))
    rows = np.asarray(rows, dtype=np.int64)
    folds = np.asarray(folds, dtype=np.int8)
    with np.load(OBSERVABLE, allow_pickle=False) as store:
        matrices = {
            "SS": np.asarray(store["ss_features"][rows], dtype=np.float64),
            "MS": np.asarray(store["ms_features"][rows], dtype=np.float64),
        }
    normalization = json.loads(NORMALIZATION.read_text(encoding="utf-8"))
    semantics = json.loads(SEMANTICS.read_text(encoding="utf-8"))
    records = []
    for arm, matrix in matrices.items():
        schema = json.loads(
            (ROOT / f"06_experiments/mso02a/{arm.lower()}_observable_schema.json").read_text(
                encoding="utf-8"
            )
        )
        names = [column["name"] for column in schema["columns"]]
        subset = semantics["oracle"]["polynomial_ridge"][f"frozen_{arm.lower()}_subset"]
        positions = [names.index(name) for name in subset]
        for outer in range(6):
            fold_norm = normalization["arms"][arm]["folds"][outer]
            normalized = (
                matrix - np.asarray(fold_norm["median"], dtype=np.float64)
            ) / np.asarray(fold_norm["divisor"], dtype=np.float64)
            partitions = [("OUTER_DEVELOPMENT", -1, folds != outer)]
            partitions.extend(
                (
                    "INNER_TRAINING",
                    inner,
                    (folds != outer) & (folds != inner),
                )
                for inner in range(6)
                if inner != outer
            )
            for partition, inner, mask in partitions:
                for candidate, design in (
                    ("ridge", normalized[mask]),
                    (
                        "polynomial_ridge",
                        PolynomialFeatures(degree=2, include_bias=False).fit_transform(
                            normalized[mask][:, positions]
                        ),
                    ),
                ):
                    centered = design - design.mean(axis=0)
                    gram = centered.T @ centered
                    before = np.diag(gram).copy()
                    gram.flat[:: gram.shape[0] + 1] += 1.0
                    alpha_unresolved = int(np.sum(np.diag(gram) == before))
                    rhs_seed = np.sin(np.arange(centered.shape[0], dtype=np.float64))
                    rhs = centered.T @ rhs_seed[:, None]
                    try:
                        coefficient = np.linalg.solve(gram, rhs)
                        finite = bool(np.isfinite(coefficient).all())
                        failure = ""
                    except np.linalg.LinAlgError as error:
                        finite = False
                        failure = f"LinAlgError:{error}"
                    records.append(
                        {
                            "arm": arm,
                            "outer_fold": f"FOLD_{outer}",
                            "partition": partition,
                            "inner_validation_fold": "" if inner < 0 else f"FOLD_{inner}",
                            "candidate": candidate,
                            "training_row_count": int(mask.sum()),
                            "design_dimension": int(design.shape[1]),
                            "design_absolute_maximum": float(np.max(np.abs(design))),
                            "ridge_alpha": 1.0,
                            "diagonal_alpha_numerically_unresolved_count": alpha_unresolved,
                            "solve_succeeded_and_finite": finite,
                            "failure": failure,
                        }
                    )
    passed = all(record["solve_succeeded_and_finite"] for record in records)
    write_json(
        OUTPUT,
        {
            "schema_version": "1.0.0",
            "stage": "MSO-02B",
            "status": "PASS_TARGET_BLIND" if passed else "FAIL_TARGET_BLIND",
            "source_sample_registry_sha256": sha256(SAMPLE),
            "observable_store_sha256": sha256(OBSERVABLE),
            "normalization_registry_sha256": sha256(NORMALIZATION),
            "analysis_semantics_registry_sha256": sha256(SEMANTICS),
            "target_or_reference_read_count": 0,
            "solver": "exact frozen DDO centered normal equations plus alpha=1 diagonal and numpy.linalg.solve",
            "alpha_resolution_note": "Unresolved diagonal increments are reported as a representation-conditioning diagnostic; a finite solve remains an eligible frozen candidate and no alternate solver is substituted.",
            "record_count": len(records),
            "all_candidate_design_solves_succeeded_and_finite": passed,
            "records": records,
        },
    )
    if not passed:
        raise RuntimeError("MSO02B_ORACLE_TARGET_BLIND_NUMERICAL_PREFLIGHT_FAILED")
    print(
        json.dumps(
            {
                "status": "PASS_TARGET_BLIND",
                "records": len(records),
                "output_sha256": sha256(OUTPUT),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
