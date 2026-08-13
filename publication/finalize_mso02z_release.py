#!/usr/bin/env python3
"""Fail-closed MSO-02Z publication manifest finalizer.

This script performs packaging and SHA-256 registration only. It does not open
observable/target payloads or recompute any scientific quantity.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_HEAD = "337207223e559db2e793cee6c437399091843d7c"
TERMINAL_STATUS = (
    "PROJECT_SUPPORT_SCALE_MULTISCALE_ROUTE_CLOSED_PUBLICATION_EVIDENCE_FROZEN"
)

OUTPUT_PATHS = [
    "publication/final_hypothesis_ledger.csv",
    "publication/cross_stage_evidence_matrix.md",
    "publication/final_innovation_register.md",
    "publication/final_failure_taxonomy.md",
    "publication/final_claim_freeze.md",
    "publication/manuscript_narrative_source_pack.md",
    "publication/figure_table_plan.md",
    "publication/literature_gap_matrix_2026-08-13.csv",
    "publication/literature_verification_2026-08-13.md",
    "publication/finalize_mso02z_release.py",
    "07_reports/mso02z_project_closure_report.md",
    "08_manifests/mso02z_status_ledger.json",
    "08_manifests/mso02z_manifest.json",
]

UPSTREAM_PATHS = [
    "00_project_contract/mso_project_charter.md",
    "00_project_contract/mso_scope_and_claim_boundary.md",
    "00_project_contract/mso01_target_blind_numerical_qualification_contract.md",
    "00_project_contract/mso02a_fresh_atlas_and_representation_freeze_contract.md",
    "00_project_contract/mso02b_paired_prelearning_identifiability_execution_contract.md",
    "00_project_contract/mso02c_dnn_degeneracy_diagnostic_contract.md",
    "00_project_contract/mso02c_g1_descriptor_neighbour_reconstruction_authorization.md",
    "00_project_contract/mso02c_g2_zero_safe_metric_selection_contract.md",
    "00_project_contract/mso02c_g2_zero_safe_metric_selection_protocol_erratum.md",
    "00_project_contract/hmso01r_a_fresh_requalification_atlas_freeze_contract.md",
    "00_project_contract/hmso01r_b_fresh_confirmatory_execution_contract.md",
    "00_project_contract/mso02d_componentwise_failure_attribution_contract.md",
    "01_provenance/parent_project_provenance_audit.md",
    "02_literature_boundary/literature_gap_matrix.csv",
    "02_literature_boundary/literature_boundary_report.md",
    "06_experiments/hmso01r_b/formal_summary.json",
    "06_experiments/hmso01r_b/component_verdicts.csv",
    "06_experiments/hmso01r_b/candidate_c_paired_rescue_metrics.csv",
    "06_experiments/hmso01r_b/paired_non_dnn_rescue_metrics.csv",
    "06_experiments/mso02d/canonical_result_identity_audit.json",
    "06_experiments/mso02d/mechanism_evidence_matrix.csv",
    "06_experiments/mso02d/mechanism_verdicts.csv",
    "06_experiments/mso02d/route_adjudication_matrix.csv",
    "07_reports/mso00_final_report.md",
    "07_reports/mso01_numerical_qualification_report.md",
    "07_reports/mso02a_fresh_atlas_report.md",
    "07_reports/mso02b_identifiability_requalification_report.md",
    "07_reports/mso02c_g1_ab_attribution_report.md",
    "07_reports/mso02c_g2_zero_safe_metric_selection_report.md",
    "07_reports/hmso01r_a_fresh_requalification_atlas_report.md",
    "07_reports/hmso01r_b_fresh_confirmatory_identifiability_report.md",
    "07_reports/mso02d_componentwise_failure_attribution_report.md",
    "08_manifests/mso00_manifest.json",
    "08_manifests/mso01_status_ledger.json",
    "08_manifests/mso02a_status_ledger.json",
    "08_manifests/mso02b_status_ledger.json",
    "08_manifests/mso02c_g1_ab_attribution_status_ledger.json",
    "08_manifests/mso02c_g2_status_ledger.json",
    "08_manifests/hmso01r_a_status_ledger.json",
    "08_manifests/hmso01r_a_git_handoff.json",
    "08_manifests/hmso01r_b_status_ledger.json",
    "08_manifests/hmso01r_b_git_handoff.json",
    "08_manifests/mso02d_status_ledger.json",
    "08_manifests/mso02d_manifest.json",
]

EXTERNAL_SOURCES = [
    ("L01", "https://doi.org/10.1103/PhysRevFluids.8.054602", "learned SPH kernels"),
    ("L02", "https://proceedings.mlr.press/v235/toshev24a.html", "Neural SPH"),
    ("L03", "https://proceedings.iclr.cc/paper_files/paper/2024/hash/1386faadf55462905db1548cff151a78-Abstract-Conference.html", "symmetric particle convolutions"),
    ("L04", "https://proceedings.neurips.cc/paper_files/paper/2022/hash/2dd7f33ffbb59b4ff987be5442a13016-Abstract-Conference.html", "momentum-conserving particle networks"),
    ("L05", "https://arxiv.org/abs/2403.04750", "differentiable SPH"),
    ("L06", "https://arxiv.org/abs/2507.21684", "differentiable SPH and ML"),
    ("L07", "https://arxiv.org/abs/1909.05371", "learned mesh-free operators"),
    ("L08", "https://proceedings.neurips.cc/paper/2020/hash/4b21cf96d4cf612f239a6c322b10c8fe-Abstract.html", "point-cloud graph neural operators"),
    ("L09", "https://arxiv.org/abs/2106.04900", "multiscale graph fluid models"),
    ("L10", "https://www.sciencedirect.com/science/article/pii/S0893608026000936", "particle Transformers"),
    ("L11", "https://doi.org/10.1073/pnas.2213638120", "scale-aware Lagrangian ML"),
    ("L12", "https://annals.math.princeton.edu/articles/22284", "particle-to-kinetic limits"),
    ("L13", "https://arxiv.org/abs/2503.01800", "kinetic-to-fluid limits"),
    ("L14", "https://arxiv.org/abs/2603.24641", "self-supervised learned mesh-free differential operators"),
    ("L15", "https://arxiv.org/abs/2602.21551", "Gaussian particle operator and cross-scale attention"),
    ("L16", "https://arxiv.org/abs/2510.17813", "learned meshfree-particle boundary correction"),
    ("L17", "https://arxiv.org/abs/2604.24159", "quantum neural SPH"),
]


def run(*args: str) -> str:
    return subprocess.check_output(args, cwd=ROOT, text=True).strip()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_path(relative_path: str) -> str:
    path = ROOT / relative_path
    if not path.is_file():
        raise SystemExit(f"missing required artifact: {relative_path}")
    return sha256_bytes(path.read_bytes())


def verify_repository_boundary() -> None:
    if run("git", "rev-parse", "HEAD") != SOURCE_HEAD:
        raise SystemExit("MSO-02Z must finalize directly from the frozen MSO-02D commit")
    if run("git", "branch", "--show-current") != "main":
        raise SystemExit("MSO-02Z must finalize on main")
    if run("git", "remote"):
        raise SystemExit("MSO-02Z requires remote=none")
    if subprocess.run(["git", "diff", "--quiet"], cwd=ROOT).returncode:
        raise SystemExit("tracked working-tree modifications are prohibited")
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode:
        raise SystemExit("pre-existing staged modifications are prohibited")

    allowed = set(OUTPUT_PATHS)
    for line in run("git", "status", "--porcelain=v1", "--untracked-files=all").splitlines():
        if not line:
            continue
        status, path = line[:2], line[3:]
        if status != "??" or path not in allowed:
            raise SystemExit(f"out-of-scope worktree entry: {line}")


def verify_upstream() -> list[dict[str, object]]:
    registry: list[dict[str, object]] = []
    for relative_path in UPSTREAM_PATHS:
        current = (ROOT / relative_path).read_bytes()
        frozen = subprocess.check_output(
            ["git", "show", f"{SOURCE_HEAD}:{relative_path}"], cwd=ROOT
        )
        if current != frozen:
            raise SystemExit(f"frozen upstream artifact changed: {relative_path}")
        registry.append(
            {
                "path": relative_path,
                "sha256": sha256_bytes(current),
                "source": f"SPH-MSO-PoC@{SOURCE_HEAD}",
                "stage": "MSO-02Z-UPSTREAM-IDENTITY",
                "evidence_class": "FROZEN_UPSTREAM_EVIDENCE",
                "consumption_status": "READ_ONLY_CONSUMED_FOR_PUBLICATION_PACKAGING",
            }
        )
    return registry


def output_entry(relative_path: str) -> dict[str, object]:
    literature = "literature_" in relative_path
    return {
        "path": relative_path,
        "sha256": sha256_path(relative_path),
        "source": (
            "PUBLICATION_STAGE_PRIMARY_SOURCE_VERIFICATION_AND_FROZEN_BOUNDARY"
            if literature
            else "DERIVED_FROM_FROZEN_ARTIFACTS_ONLY"
        ),
        "stage": "MSO-02Z",
        "evidence_class": "PUBLICATION_CLAIM_BOUNDARY" if literature else "PUBLICATION_DERIVED_EVIDENCE_PACKAGE",
        "consumption_status": "FINAL_PUBLICATION_CLOSURE_OUTPUT",
    }


def main() -> None:
    verify_repository_boundary()
    upstream_registry = verify_upstream()

    output_registry = [
        output_entry(path)
        for path in OUTPUT_PATHS
        if path != "08_manifests/mso02z_manifest.json"
    ]
    output_registry.append(
        {
            "path": "08_manifests/mso02z_manifest.json",
            "sha256": "FINAL_GIT_BLOB_AT_MSO02Z_FINAL_COMMIT",
            "source": "MANIFEST_SELF_BINDING",
            "stage": "MSO-02Z",
            "evidence_class": "PUBLICATION_RELEASE_MANIFEST",
            "consumption_status": "FINAL_GIT_COMMIT_AND_USER_HANDOFF_SELF_BINDING",
        }
    )

    manifest = {
        "schema_version": "1.0.0",
        "project": "SPH-MSO-PoC",
        "stage": "MSO-02Z",
        "date": "2026-08-13",
        "timezone": "Asia/Shanghai",
        "terminal_status": TERMINAL_STATUS,
        "authorization": {
            "publication_packaging_only": True,
            "fresh_compute_authorized": False,
            "new_hypothesis_test_authorized": False,
            "h_mso02_authorized": False,
            "mso03_authorized": False,
            "neural_training_authorized": False,
            "attention_authorized": False,
            "transformer_authorized": False,
            "paper_route_authorized": True,
        },
        "git": {
            "branch": "main",
            "remote": None,
            "push_performed": False,
            "prior_commit_amended": False,
            "mso02d_final_commit": SOURCE_HEAD,
            "mso02z_final_commit": "RECORDED_BY_FINAL_GIT_COMMIT_AND_USER_HANDOFF",
        },
        "scientific_immutability": {
            "frozen_upstream_artifacts_modified": False,
            "scientific_values_recomputed": False,
            "fresh_scientific_evidence_generated": False,
            "target_or_observable_payload_read": False,
            "upstream_identity_count": len(upstream_registry),
        },
        "upstream_artifact_registry": upstream_registry,
        "publication_artifact_registry": output_registry,
        "external_literature_registry": [
            {
                "record_id": record_id,
                "url": url,
                "topic": topic,
                "access_date": "2026-08-13",
                "role": "PUBLICATION_CLAIM_BOUNDARY_ONLY",
            }
            for record_id, url, topic in EXTERNAL_SOURCES
        ],
        "validation": {
            "all_upstream_paths_exist": True,
            "all_upstream_bytes_equal_source_commit": True,
            "all_nonself_output_paths_exist": True,
            "tracked_worktree_diff_empty_before_release": True,
            "staged_diff_empty_before_release": True,
            "only_allowlisted_untracked_outputs_present": True,
            "upstream_registry_count": len(upstream_registry),
            "publication_registry_count": len(output_registry),
            "external_literature_count": len(EXTERNAL_SOURCES),
        },
        "manifest_self_binding": {
            "path": "08_manifests/mso02z_manifest.json",
            "sha256": "FINAL_GIT_BLOB_AT_MSO02Z_FINAL_COMMIT",
            "resolved_commit": "RECORDED_BY_FINAL_GIT_COMMIT_AND_USER_HANDOFF",
        },
        "stop_after_mso02z": True,
    }

    target = ROOT / "08_manifests/mso02z_manifest.json"
    target.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "terminal_status": TERMINAL_STATUS,
                "upstream_registry_count": len(upstream_registry),
                "publication_registry_count": len(output_registry),
                "manifest": str(target),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
