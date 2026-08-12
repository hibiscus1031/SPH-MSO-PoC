#!/usr/bin/env python3
"""Freeze source provenance, formal particle identities, and MSO-02B executables."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
DDO = Path("/Users/xiejinbo/Documents/SPH-DDO-PoC")
FORMAL = ROOT / "05_registries/mso02a_formal_fresh_atlas_registry.json"
SAMPLE = ROOT / "05_registries/mso02b_formal_particle_sample_registry.json"
IMPORT = ROOT / "01_provenance/mso02b_target_reference_import_manifest.csv"
FREEZE = ROOT / "08_manifests/mso02b_target_precompute_freeze.json"

DDO_HEAD = "d76d29ae51e8104641b710371f0fcb248d5ea268"
AUTHORIZED_PARENT = "887d4cdab3dbd9e856e552ff47e50a3cf481d72f"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    target_access_artifacts = (
        ROOT / "06_experiments/mso02b/target_ref/mso02b_target_store.npz",
        ROOT / "06_experiments/mso02b/target_reference_qualification.csv",
        ROOT / "06_experiments/mso02b/target_access_ledger.json",
    )
    if any(path.exists() for path in target_access_artifacts):
        raise RuntimeError("formal target store exists; precompute freeze is immutable")
    branch = subprocess.run(
        ["git", "branch", "--show-current"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()
    remotes = subprocess.run(
        ["git", "remote"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.split()
    if branch != "main" or head != AUTHORIZED_PARENT or remotes:
        raise RuntimeError("MSO02B precompute Git boundary mismatch")
    ddo_head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=DDO, check=True, capture_output=True, text=True
    ).stdout.strip()
    if ddo_head != DDO_HEAD:
        raise RuntimeError("DDO frozen source HEAD mismatch")

    formal = json.loads(FORMAL.read_text(encoding="utf-8"))
    sample_rows = []
    for case in sorted(formal["cases"], key=lambda row: int(row["formal_case_index"])):
        ordered = sorted(
            range(int(case["particle_count"])),
            key=lambda particle: (
                hashlib.sha256(
                    f"MSO02B|PARTICLE|{case['case_id']}|{particle}".encode("utf-8")
                ).hexdigest(),
                particle,
            ),
        )
        selected = ordered[:128]
        sample_rows.append(
            {
                "formal_case_index": int(case["formal_case_index"]),
                "case_id": case["case_id"],
                "field_lineage_id": case["field_lineage_id"],
                "family": case["macro_family"],
                "fold": case["fold"],
                "particle_count": int(case["particle_count"]),
                "sample_count": 128,
                "particle_ids_in_hash_order": selected,
                "particle_id_array_sha256": hashlib.sha256(
                    np.asarray(selected, dtype=np.int16).tobytes()
                ).hexdigest(),
            }
        )
    write_json(
        SAMPLE,
        {
            "schema_version": "1.0.0",
            "stage": "MSO-02B",
            "status": "FROZEN_BEFORE_FORMAL_TARGET_GENERATION",
            "case_count": 384,
            "particles_per_case": 128,
            "formal_sample_row_count": 49152,
            "selection": "FIRST_128_BY_ASCENDING_FULL_SHA256_THEN_PARTICLE_ID",
            "hash_domain": "MSO02B|PARTICLE|<case_id>|<particle_id>",
            "particle_weights": "EQUAL_1_OVER_128_WITHIN_COMPLETE_CASE",
            "source_ddo_semantics": {
                "head": DDO_HEAD,
                "path": "08_scripts/h3_identifiability_semantics.py",
                "symbol": "selected_particle_ids",
                "sha256": "857f30efce8559ddf3d562051209d0069ba73c24f06183a685b7304155001234"
            },
            "domain_separated_for_mso02b": True,
            "mso02a_16_particle_geometry_sample_reused_as_formal_sample": False,
            "cases": sample_rows,
        },
    )

    destination = ROOT / "01_provenance/vendor/ddo_analytical_reference/mso02b_target_reference.py"
    source_specs = [
        (
            "08_scripts/ddo01d_atlas_builder.py",
            "ce523095e21cca07f247ef91efde878c05ea7745a1899c04a6d73fd0e2ffc44a",
            "field_values_general|evaluator_a_general|evaluator_b_general",
            "analytical field/reference adaptation for frozen MSO registry",
        ),
        (
            "08_scripts/ddo01a_preflight.py",
            "8ea2720fae9277ac6356d166d0443b6f666c6e23534aed37267d06273da7a3c2",
            "continuum_components|defects|linf_difference|permute_neighborhood",
            "continuum, defect sign, and repeat/permutation qualification adaptation",
        ),
        (
            "08_scripts/ddo01ar_requalification.py",
            "b4191e69b63e7118a305af888e107ed78a29501596f0659d4ba18e3f304c01cb",
            "C_FP|FROZEN_SCALES|fsum_scatter|independent_geometry_neighborhood|target_analytic_and_sph",
            "CA-01 uncertainty and independent-geometry adaptation",
        ),
        (
            "08_scripts/h3_identifiability_semantics.py",
            "857f30efce8559ddf3d562051209d0069ba73c24f06183a685b7304155001234",
            "selected_particle_ids|target_trace_variance|conditional_variance_ratios",
            "formal sampling and H3 estimator semantics imported into registry/executable",
        ),
        (
            "08_scripts/ddo01e_non_neural_analysis.py",
            "88bec6c76c6cf700842bab455cd1f164d4f9dd08123f42b9d81f8afb928ae39e",
            "ORACLES|ridge_predict|matched_random_baseline|angle_floor|PolynomialFeatures subset",
            "non-neural diagnostic semantics imported into registry/executable",
        ),
    ]
    import_rows = []
    for relative, expected, symbols, note in source_specs:
        source = DDO / relative
        actual = sha256(source)
        if actual != expected:
            raise RuntimeError(f"DDO source mismatch {relative}")
        if relative in (
            "08_scripts/h3_identifiability_semantics.py",
            "08_scripts/ddo01e_non_neural_analysis.py",
        ):
            imported_destination = "05_registries/mso02b_analysis_semantics_registry.json|06_experiments/mso02b/run_mso02b_formal.py"
            destination_hash = (
                sha256(ROOT / "05_registries/mso02b_analysis_semantics_registry.json")
                + "|"
                + sha256(ROOT / "06_experiments/mso02b/run_mso02b_formal.py")
            )
            import_mode = "PROVENANCE_BOUND_SEMANTICS_SERIALIZATION_AND_EXECUTABLE_ADAPTATION"
        else:
            imported_destination = str(destination.relative_to(ROOT))
            destination_hash = sha256(destination)
            import_mode = "PROVENANCE_BOUND_MATHEMATICAL_ADAPTATION_NOT_BYTE_COPY"
        import_rows.append(
            {
                "source_project": "SPH-DDO-PoC",
                "source_head": DDO_HEAD,
                "source_path": str(source),
                "source_sha256": actual,
                "source_symbols": symbols,
                "imported_destination": imported_destination,
                "destination_sha256": destination_hash,
                "import_mode": import_mode,
                "adaptation_note": note,
                "historical_target_or_h3_payload_imported": False,
            }
        )
        if relative == "08_scripts/h3_identifiability_semantics.py":
            import_rows.append(
                {
                    "source_project": "SPH-DDO-PoC",
                    "source_head": DDO_HEAD,
                    "source_path": str(source),
                    "source_sha256": actual,
                    "source_symbols": "selected_particle_ids",
                    "imported_destination": str(SAMPLE.relative_to(ROOT)),
                    "destination_sha256": sha256(SAMPLE),
                    "import_mode": "PROVENANCE_BOUND_DOMAIN_SEPARATED_PARTICLE_SAMPLE_SERIALIZATION",
                    "adaptation_note": "same first-128 full-SHA ordering with MSO02B domain separation",
                    "historical_target_or_h3_payload_imported": False,
                }
            )
    operator_hashes = {
        "__init__.py": "18afa8e375e06bd03ce68f17528c7a27722e1dbdab17536d1b060994446ad93a",
        "neighborhood.py": "44d61e0abbc9901472dae90f83127f5231fc3f6e8ac92a971228dfdcb230aaa8",
        "kernels.py": "bad08e0f49b308c568cd438c9981abd2c906e16c6570ebc0ca7d19d9847b333b",
        "conservative_pressure.py": "b6366666ba89cc1f367a95390a411905eee8b7f55fba28a024f5732860004064",
        "conservative_viscosity.py": "bdfbcb457f6973130f0131ec3c0a3fecc7197dd117c8256163cf3a1445307852",
    }
    operator_root = ROOT / "01_provenance/vendor/pio_stage01c_static/structure_preserving"
    for name, expected in operator_hashes.items():
        path = operator_root / name
        ddo_operator_source = DDO / "01_imported_baseline/structure_preserving" / name
        source_actual = sha256(ddo_operator_source)
        actual = sha256(path)
        if source_actual != expected or actual != expected:
            raise RuntimeError(f"static operator hash mismatch {name}")
        import_rows.append(
            {
                "source_project": "SPH-DDO-PoC_BYTE_IDENTICAL_VENDORED_OPERATOR",
                "source_head": DDO_HEAD,
                "source_path": str(ddo_operator_source),
                "source_sha256": source_actual,
                "source_symbols": "complete file",
                "imported_destination": str(path.relative_to(ROOT)),
                "destination_sha256": actual,
                "import_mode": "PREEXISTING_BYTE_IDENTICAL_HASH_BOUND_VENDOR",
                "adaptation_note": "no MSO-02B copy or edit",
                "historical_target_or_h3_payload_imported": False,
            }
        )
    IMPORT.parent.mkdir(parents=True, exist_ok=True)
    with IMPORT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(import_rows[0]), lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(import_rows)

    frozen_inputs = [
        "00_project_contract/mso02b_paired_prelearning_identifiability_execution_contract.md",
        "04_identifiability_contract/h_mso01_contract.md",
        "04_identifiability_contract/prospective_gate_proposal.md",
        "08_manifests/mso00_manifest.json",
        "08_manifests/mso01_manifest.json",
        "08_manifests/mso02a_manifest.json",
        "08_manifests/mso02a_git_handoff.json",
        "08_manifests/mso02b_pre_target_freeze.json",
        "05_registries/mso02a_formal_fresh_atlas_registry.json",
        "05_registries/mso02a_lineage_fold_registry.json",
        "05_registries/mso02a_paired_ss_ms_registry.json",
        "05_registries/mso02a_bootstrap_registry.json",
        "06_experiments/mso02a/ss_observable_schema.json",
        "06_experiments/mso02a/ms_observable_schema.json",
        "06_experiments/mso02a/fold_normalization_registry.json",
        "06_experiments/mso02a/observable_coverage_geometry.json",
        "06_experiments/mso02a/observable/mso02a_observable_store.npz",
        "06_experiments/mso02a/bootstrap_draws.npz",
    ]
    execution_artifacts = [
        "01_provenance/mso02b_target_reference_import_manifest.csv",
        "01_provenance/vendor/ddo_analytical_reference/__init__.py",
        "01_provenance/vendor/ddo_analytical_reference/mso02b_target_reference.py",
        "05_registries/mso02b_analysis_semantics_registry.json",
        "05_registries/mso02b_target_role_registry.json",
        "05_registries/mso02b_formal_particle_sample_registry.json",
        "05_registries/mso02b_formal_coverage_radius_registry.json",
        "05_registries/mso02b_oracle_numerical_preflight.json",
        "06_experiments/mso02b/build_mso02b_targets.py",
        "06_experiments/mso02b/run_mso02b_formal.py",
        "06_experiments/mso02b/finalize_mso02b_release.py",
        "06_experiments/mso02b/prepare_mso02b_target_freeze.py",
        "06_experiments/mso02b/prepare_mso02b_oracle_numerical_preflight.py",
        "06_experiments/mso02b/prepare_mso02b_formal_coverage_radius.py",
        "01_provenance/vendor/pio_stage01c_static/structure_preserving/__init__.py",
        "01_provenance/vendor/pio_stage01c_static/structure_preserving/neighborhood.py",
        "01_provenance/vendor/pio_stage01c_static/structure_preserving/kernels.py",
        "01_provenance/vendor/pio_stage01c_static/structure_preserving/conservative_pressure.py",
        "01_provenance/vendor/pio_stage01c_static/structure_preserving/conservative_viscosity.py",
    ]
    external = [
        {"path": str(DDO / relative), "sha256": expected}
        for relative, expected, _, _ in source_specs
    ]
    external.extend(
        {
            "path": str(DDO / "01_imported_baseline/structure_preserving" / name),
            "sha256": expected,
        }
        for name, expected in operator_hashes.items()
    )
    write_json(
        FREEZE,
        {
            "schema_version": "1.0.0",
            "stage": "MSO-02B",
            "status": "FROZEN_BEFORE_FORMAL_TARGET_GENERATION",
            "authorized_scientific_handoff_commit": AUTHORIZED_PARENT,
            "execution_freeze_commit": "RECORDED_BY_NEXT_CLEAN_GIT_COMMIT_AND_FINAL_HANDOFF",
            "branch": "main",
            "remote": None,
            "ddo_source_head": DDO_HEAD,
            "frozen_input_sha256": {
                relative: sha256(ROOT / relative) for relative in frozen_inputs
            },
            "execution_artifact_sha256": {
                relative: sha256(ROOT / relative) for relative in execution_artifacts
            },
            "external_source_sha256": external,
            "determinism": {
                "cpu": True,
                "float_dtype": "float64",
                "torch_num_threads": 1,
                "torch_num_interop_threads": 1,
                "torch_deterministic_algorithms": True,
                "neighbor_search": "cKDTree eps=0,p=2,workers=1 with complete deterministic tie expansion"
            },
            "formal_target_generation_started": False,
            "formal_target_store_write_count": 0,
            "formal_h3_evaluation_count": 0,
            "source_import_qa_reference_evaluation_count": 384,
            "source_import_qa_defect_generation_count": 0,
            "source_import_qa_target_store_write_count": 0,
            "historical_h3_accidental_text_match_read_count": 1,
            "historical_h3_result_used_count": 0,
            "historical_target_payload_read_count": 0,
            "first_reference_source_qa_access_occurred_after_authorized_pre_target_commit": True,
            "semantic_gap_count": 0,
            "ratio_unstable_branch": "NOT_EVALUABLE_IF_TRIGGERED_BECAUSE_NO_FROZEN_ABSOLUTE_DIFFERENCE_MARGIN_EXISTS",
        },
    )
    print(
        json.dumps(
            {
                "status": "MSO02B_TARGET_AND_ANALYSIS_EXECUTION_FROZEN",
                "formal_sample_rows": 49152,
                "import_rows": len(import_rows),
                "target_precompute_freeze_sha256": sha256(FREEZE),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
