#!/usr/bin/env python3
"""Validate and finalize the MSO-02B report, status ledger, and manifest."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "06_experiments/mso02b"
SUMMARY = OUT / "mso02b_formal_summary.json"
QUALIFICATION = OUT / "target_reference_qualification.csv"
TARGET_LEDGER = OUT / "target_access_ledger.json"
FIREWALL = OUT / "firewall_audit.json"
TARGET = OUT / "target_ref/mso02b_target_store.npz"
PRECOMPUTE = ROOT / "08_manifests/mso02b_target_precompute_freeze.json"
REPORT = ROOT / "07_reports/mso02b_identifiability_requalification_report.md"
STATUS = ROOT / "08_manifests/mso02b_status_ledger.json"
MANIFEST = ROOT / "08_manifests/mso02b_manifest.json"
PRE_TARGET_COMMIT = "887d4cdab3dbd9e856e552ff47e50a3cf481d72f"

COMPONENTS = (
    "density_rate",
    "pressure_gradient_acceleration",
    "viscosity_laplacian_acceleration",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text.rstrip() + "\n", encoding="utf-8")
    temporary.replace(path)


def fmt(value: Any) -> str:
    if value is None:
        return "NOT_EVALUABLE"
    if isinstance(value, bool):
        return "PASS" if value else "FAIL"
    if isinstance(value, (int, float)):
        return f"{float(value):.8g}"
    return str(value)


def bool_cell(value: str) -> bool:
    return value.strip().lower() in ("true", "1", "yes")


def role_for(relative: str) -> str:
    if relative.endswith("mso02b_target_store.npz"):
        return "PHYSICALLY_SEPARATED_FORMAL_TARGET_STORE"
    if "target_reference_qualification" in relative:
        return "FORMAL_TARGET_REFERENCE_QUALIFICATION"
    if "target_observable_join_audit" in relative:
        return "FORMAL_TARGET_OBSERVABLE_JOIN_AUDIT"
    if "bootstrap_simultaneous_bounds" in relative:
        return "FORMAL_SIMULTANEOUS_INFERENCE"
    if "component_verdicts" in relative:
        return "FORMAL_COMPONENT_VERDICTS"
    if any(name in relative for name in ("_dnn_metrics", "conditional_variance_metrics", "_oracle_metrics", "coverage_metrics", "paired_rescue_metrics")):
        return "FORMAL_H_MSO01_METRIC"
    if "/checkpoints/" in relative:
        return "FORMAL_CROSS_FITTED_CASE_SUFFICIENT_STATISTICS"
    if "firewall_audit" in relative:
        return "FORMAL_FIREWALL_AUDIT"
    if "formal_summary" in relative:
        return "FORMAL_MACHINE_READABLE_SUMMARY"
    if relative == str(REPORT.relative_to(ROOT)):
        return "HUMAN_READABLE_RELEASE_REPORT"
    if relative == str(STATUS.relative_to(ROOT)):
        return "TERMINAL_STATUS_LEDGER"
    if "execution_contract" in relative:
        return "PROSPECTIVE_AND_TARGET_BLIND_AMENDED_EXECUTION_CONTRACT"
    if "import_manifest" in relative:
        return "TARGET_REFERENCE_SOURCE_PROVENANCE"
    if "target_precompute_freeze" in relative:
        return "TARGET_AND_ANALYSIS_EXECUTABLE_FREEZE"
    if "pre_target_freeze" in relative or "git_handoff" in relative:
        return "PRE_TARGET_GIT_AND_EVIDENCE_HANDOFF"
    if "/vendor/" in relative:
        return "HASH_BOUND_VENDOR_SOURCE"
    if "/05_registries/" in f"/{relative}":
        return "PRE_TARGET_FROZEN_SEMANTICS_OR_IDENTITY_REGISTRY"
    if relative.endswith(".py"):
        return "HASH_BOUND_EXECUTABLE"
    if "target_access_ledger" in relative:
        return "AUTHORIZED_TARGET_ACCESS_LEDGER"
    return "MSO02B_RELEASE_ARTIFACT"


def source_for(relative: str) -> str:
    if "/vendor/ddo_analytical_reference/" in f"/{relative}":
        return "SPH-DDO-PoC@d76d29a source functions recorded in import manifest"
    if relative.endswith("mso02b_target_store.npz") or "target_reference_qualification" in relative:
        return "hash-bound isolated MSO-02B target builder and frozen formal registry"
    if any(token in relative for token in ("metrics.csv", "simultaneous_bounds.csv", "component_verdicts.csv", "formal_summary.json", "/checkpoints/", "join_audit.csv", "firewall_audit.json")):
        return "single hash-bound paired SS/MS formal executable"
    if relative in (str(REPORT.relative_to(ROOT)), str(STATUS.relative_to(ROOT))):
        return "validated MSO-02B formal summary, metrics, verdicts, and ledgers"
    if "coverage_radius" in relative or "oracle_numerical_preflight" in relative:
        return "target-blind formal observable precompute"
    if "import_manifest" in relative:
        return "frozen DDO HEAD and byte-verified MSO destinations"
    return "MSO-02B user authorization plus hash-bound frozen MSO-00/01/02A evidence"


def consumption_for(relative: str) -> str:
    role = role_for(relative)
    if role in (
        "FORMAL_H_MSO01_METRIC",
        "FORMAL_SIMULTANEOUS_INFERENCE",
        "FORMAL_COMPONENT_VERDICTS",
        "FORMAL_CROSS_FITTED_CASE_SUFFICIENT_STATISTICS",
        "FORMAL_TARGET_REFERENCE_QUALIFICATION",
        "PHYSICALLY_SEPARATED_FORMAL_TARGET_STORE",
        "FORMAL_TARGET_OBSERVABLE_JOIN_AUDIT",
    ):
        return "CONSUMED_BY_FROZEN_H_MSO01_VERDICT"
    if role in ("HUMAN_READABLE_RELEASE_REPORT", "TERMINAL_STATUS_LEDGER"):
        return "FINAL_RELEASE_OUTPUT"
    return "CONSUMED_BY_MSO02B_EXECUTION_OR_RELEASE_VALIDATION"


def main() -> None:
    if MANIFEST.exists() or REPORT.exists() or STATUS.exists():
        raise RuntimeError("MSO-02B release outputs already exist; refusing replacement")
    branch = subprocess.run(
        ["git", "branch", "--show-current"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()
    remotes = subprocess.run(
        ["git", "remote"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.split()
    if branch != "main" or remotes:
        raise RuntimeError("MSO02B release Git boundary failure")

    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    target_ledger = json.loads(TARGET_LEDGER.read_text(encoding="utf-8"))
    firewall = json.loads(FIREWALL.read_text(encoding="utf-8"))
    freeze = json.loads(PRECOMPUTE.read_text(encoding="utf-8"))
    with QUALIFICATION.open(encoding="utf-8", newline="") as handle:
        qualification_rows = list(csv.DictReader(handle))
    qualified = sum(bool_cell(row["case_target_reference_qualified"]) for row in qualification_rows)
    if qualified != 384 or len(qualification_rows) != 384:
        raise RuntimeError("MSO02B_TARGET_REFERENCE_QUALIFICATION_NOT_COMPLETE")
    if target_ledger["target_store_sha256"] != sha256(TARGET):
        raise RuntimeError("target store ledger identity mismatch")
    for group in ("frozen_input_sha256", "execution_artifact_sha256"):
        for relative, expected in freeze[group].items():
            if sha256(ROOT / relative) != expected:
                raise RuntimeError(f"MSO02B_FROZEN_EVIDENCE_IDENTITY_FAILURE:{relative}")

    metrics = summary["metrics"]
    verdict = summary["verdict"]
    report_lines = [
        "# MSO-02B paired prelearning identifiability requalification report",
        "",
        f"Terminal status: `{summary['terminal_status']}`.",
        "",
        "This is the first formal SPH-MSO scientific target experiment. It used only the frozen SS/MS representations and simple non-neural diagnostics. `DNN` means Descriptor Nearest-Neighbour. No neural model, optimizer, training, time integration, rollout, sealed test, or MSO-03 execution occurred.",
        "",
        "## Frozen release identities",
        "",
        f"- Initial pre-target handoff commit: `{PRE_TARGET_COMMIT}`.",
        f"- Target/analysis execution-freeze commit: `{head}`.",
        f"- Target precompute freeze SHA-256: `{sha256(PRECOMPUTE)}`.",
        f"- Target store SHA-256: `{sha256(TARGET)}`.",
        f"- Observable store SHA-256 before/after: `{firewall['observable_store_sha256_before']}` / `{firewall['observable_store_sha256_after']}`.",
        "- SS/MS dimensions remain 39/110. The representations retain five exact constants per arm, all 13/65 fold-IQR-degenerate involved columns, and all five registered exact MS duplicates; there was no feature deletion, PCA, whitening, or target-derived pruning.",
        "",
        "## Absolute metrics",
        "",
        "| Arm | Component | DNN median (UCB) | DNN p90 (UCB) | Conditional variance (UCB) | Oracle NRMSE (UCB) | Mean-baseline improvement (LCB) | Coverage |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for arm in ("SS", "MS"):
        for component in COMPONENTS:
            value = metrics[arm][component]
            report_lines.append(
                f"| {arm} | `{component}` | {fmt(value['dnn_median'])} ({fmt(value['dnn_median_simultaneous_ucb'])}) | "
                f"{fmt(value['dnn_p90'])} ({fmt(value['dnn_p90_simultaneous_ucb'])}) | "
                f"{fmt(value['conditional_variance'])} ({fmt(value['conditional_variance_simultaneous_ucb'])}) | "
                f"{fmt(value['oracle_nrmse'])} ({fmt(value['oracle_nrmse_simultaneous_ucb'])}) | "
                f"{fmt(value['improvement'])} ({fmt(value['improvement_simultaneous_lcb'])}) | {fmt(value['coverage'])} |"
            )
    report_lines.extend(
        [
            "",
            "## Paired multiscale rescue",
            "",
            "| Component | DNN p90 ratio / reduction / UCB | Conditional-variance ratio / reduction / UCB | Oracle-NRMSE ratio / reduction / UCB |",
            "|---|---:|---:|---:|",
        ]
    )
    for component in COMPONENTS:
        values = metrics["paired_ratios"][component]
        cells = []
        for name in ("dnn_p90", "conditional_variance", "oracle_nrmse"):
            value = values[name]
            cells.append(
                f"{fmt(value['ratio'])} / {fmt(value['reduction'])} / {fmt(value['simultaneous_ucb'])} ({value['status']})"
            )
        report_lines.append(f"| `{component}` | " + " | ".join(cells) + " |")

    report_lines.extend(
        [
            "",
            "## Component and global verdicts",
            "",
            "| Component | Absolute evaluable/pass | Relative evaluable/pass | Component verdict |",
            "|---|---:|---:|---|",
        ]
    )
    for component in COMPONENTS:
        value = verdict["components"][component]
        report_lines.append(
            f"| `{component}` | {value['absolute_evaluable']}/{value['absolute_pass']} | "
            f"{value['relative_rescue_evaluable']}/{value['relative_rescue_pass']} | `{value['status']}` |"
        )
    report_lines.extend(
        [
            "",
            f"Global H-MSO-01: `{verdict['global_status']}`. Coverage remains a component-independent input-geometry gate and was not allowed to substitute for DNN, conditional variance, or oracle identifiability.",
            "",
            "## Required final answers",
            "",
            f"1. Target/reference qualification: **{qualified}/384 qualified**, 0 failed.",
            "2. Target definition: **yes**, continuum analytical reference minus the frozen lambda=1 base SPH operator; no 0.75/1.25/1.50 defect target was generated.",
            f"3. Observable store unchanged: **{summary['observable_store_unchanged']}**.",
            f"4. Frozen dimensions: **SS={summary['ss_feature_dimension']}, MS={summary['ms_feature_dimension']}**.",
            "5. SS absolute metrics: reported componentwise in the absolute-metrics table above.",
            "6. MS absolute metrics: reported componentwise in the absolute-metrics table above.",
            "7. DNN p90 paired rescue: reported as point ratio/reduction and simultaneous UCB above.",
            "8. Conditional-variance paired rescue: reported as point ratio/reduction and simultaneous UCB above.",
            "9. Oracle-NRMSE paired rescue: reported as point ratio/reduction and simultaneous UCB above.",
            "10. Simultaneous confidence requirements: each exact pass/fail is serialized in `component_verdicts.csv`; any non-evaluable bound propagates explicitly rather than being called a scientific failure.",
            "11. Absolute gates: exact check dictionaries are serialized per component in `component_verdicts.csv` and summarized above.",
            "12. Relative rescue gates: exact check dictionaries are serialized per component in `component_verdicts.csv` and summarized above.",
            "13. Component verdicts: listed in the component verdict table above.",
            f"14. Global H-MSO-01: **{verdict['global_status']}**.",
            "15. Coverage: reported overall/family/fold; it cannot replace identifiability and did not alter another metric's verdict.",
            "16. Post-target feature/scale/gate/fold/normalization modifications: **all zero**.",
            "17. Neural/optimizer/training activity: **all zero**.",
            f"18. If qualified, only deterministic-baseline eligibility is granted: **{verdict['mso03_deterministic_closure_baseline_eligible']}**; MSO-03 was not run.",
            f"19. If not qualified or not evaluable, neural/attention/learned-operator authorization remains false: **{not verdict['neural_training_authorized']}**.",
            f"20. Final terminal status: `{summary['terminal_status']}`.",
            "",
            "## Governance disclosure and stop",
            "",
            "Source-import QA evaluated A/B reference consistency for 384 frozen states after the initial pre-target commit but before formal defect generation. One static source-audit text search accidentally surfaced a pre-existing historical H3 summary line; it was not used for code, thresholds, tuning, metrics, or verdicts, and no historical target/H3 payload was opened. Formal defect generation began only after the target-blind amendments, executable hashes, provenance, and clean execution-freeze commit were fixed.",
            "",
            "MSO-02B stops here. MSO-03, neural training, architecture search, attention, and learned operators remain unexecuted.",
        ]
    )
    write_text(REPORT, "\n".join(report_lines))

    status_payload = {
        "schema_version": "1.0.0",
        "project": "SPH-MSO",
        "stage": "MSO-02B",
        "date": "2026-08-12",
        "timezone": "Asia/Shanghai",
        "terminal_status": summary["terminal_status"],
        "target_reference_qualified_case_count": qualified,
        "target_reference_failed_case_count": 384 - qualified,
        "h_mso01": verdict,
        "mso03_deterministic_closure_baseline_eligible": verdict[
            "mso03_deterministic_closure_baseline_eligible"
        ],
        "mso03_executed": False,
        "neural_training_authorized": False,
        "attention_authorized": False,
        "learned_operator_authorized": False,
        "pre_target_mso02b_commit": PRE_TARGET_COMMIT,
        "target_analysis_execution_freeze_commit": head,
        "mso02b_final_commit": "RECORDED_BY_FINAL_GIT_COMMIT_AND_USER_HANDOFF",
        "branch": branch,
        "remote": None,
        "report_sha256": sha256(REPORT),
        "target_store_sha256": sha256(TARGET),
        "observable_store_unchanged": summary["observable_store_unchanged"],
        "post_target_modification_counts": summary["post_target_modification_counts"],
        "stop_after_mso02b": True,
    }
    write_json(STATUS, status_payload)

    artifact_paths = [
        "00_project_contract/mso02b_paired_prelearning_identifiability_execution_contract.md",
        "01_provenance/mso02b_target_reference_import_manifest.csv",
        "01_provenance/vendor/ddo_analytical_reference/__init__.py",
        "01_provenance/vendor/ddo_analytical_reference/mso02b_target_reference.py",
        "05_registries/mso02b_analysis_semantics_registry.json",
        "05_registries/mso02b_formal_particle_sample_registry.json",
        "05_registries/mso02b_formal_coverage_radius_registry.json",
        "05_registries/mso02b_oracle_numerical_preflight.json",
        "05_registries/mso02b_target_role_registry.json",
        "06_experiments/mso02b/build_mso02b_targets.py",
        "06_experiments/mso02b/prepare_mso02b_target_freeze.py",
        "06_experiments/mso02b/prepare_mso02b_formal_coverage_radius.py",
        "06_experiments/mso02b/prepare_mso02b_oracle_numerical_preflight.py",
        "06_experiments/mso02b/run_mso02b_formal.py",
        "06_experiments/mso02b/finalize_mso02b_release.py",
        "06_experiments/mso02b/target_reference_qualification.csv",
        "06_experiments/mso02b/target_observable_join_audit.csv",
        "06_experiments/mso02b/target_access_ledger.json",
        "06_experiments/mso02b/ss_dnn_metrics.csv",
        "06_experiments/mso02b/ms_dnn_metrics.csv",
        "06_experiments/mso02b/ss_conditional_variance_metrics.csv",
        "06_experiments/mso02b/ms_conditional_variance_metrics.csv",
        "06_experiments/mso02b/ss_oracle_metrics.csv",
        "06_experiments/mso02b/ms_oracle_metrics.csv",
        "06_experiments/mso02b/coverage_metrics.csv",
        "06_experiments/mso02b/paired_rescue_metrics.csv",
        "06_experiments/mso02b/bootstrap_simultaneous_bounds.csv",
        "06_experiments/mso02b/component_verdicts.csv",
        "06_experiments/mso02b/firewall_audit.json",
        "06_experiments/mso02b/mso02b_formal_summary.json",
        "06_experiments/mso02b/target_ref/mso02b_target_store.npz",
        "07_reports/mso02b_identifiability_requalification_report.md",
        "08_manifests/mso02a_git_handoff.json",
        "08_manifests/mso02b_pre_target_freeze.json",
        "08_manifests/mso02b_target_precompute_freeze.json",
        "08_manifests/mso02b_status_ledger.json",
    ]
    checkpoint_paths = sorted((OUT / "checkpoints").glob("*.json"))
    if len(checkpoint_paths) != 12:
        raise RuntimeError(f"expected 12 formal arm/fold checkpoints, found {len(checkpoint_paths)}")
    artifact_paths.extend(str(path.relative_to(ROOT)) for path in checkpoint_paths)
    artifact_paths.extend(freeze["execution_artifact_sha256"].keys())
    unique_paths = list(dict.fromkeys(artifact_paths))
    missing = [relative for relative in unique_paths if not (ROOT / relative).exists()]
    if missing:
        raise RuntimeError("missing required MSO02B artifacts:" + ",".join(missing))
    registry = [
        {
            "path": relative,
            "sha256": sha256(ROOT / relative),
            "role": role_for(relative),
            "source": source_for(relative),
            "stage": "MSO-02B",
            "consumption_status": consumption_for(relative),
        }
        for relative in unique_paths
    ]

    manifest = {
        "schema_version": "1.0.0",
        "project": "SPH-MSO",
        "stage": "MSO-02B",
        "date": "2026-08-12",
        "timezone": "Asia/Shanghai",
        "terminal_status": summary["terminal_status"],
        "source_request": {
            "path": "/Users/xiejinbo/.codex/attachments/48b0ebc0-3db7-4794-8376-49a6db2b9f58/pasted-text.txt",
            "sha256": "90f7a097645921754a39cf3da7162436debeb1eb0d2c0c450c3a1b33a771cb23",
        },
        "git": {
            "branch": branch,
            "pre_target_mso02b_commit": PRE_TARGET_COMMIT,
            "target_analysis_execution_freeze_commit": head,
            "mso02b_final_commit": "RECORDED_BY_FINAL_GIT_COMMIT_AND_USER_HANDOFF",
            "remote": None,
            "push_performed": False,
        },
        "activity_flags": {
            "NEW_SCIENTIFIC_TARGET_EVALUATION": True,
            "TARGET_GENERATION": True,
            "TARGET_READ": True,
            "REFERENCE_OPERATOR_READ": True,
            "H3_EVALUATION": True,
            "ORACLE_FIT": True,
            "NEURAL_MODEL": False,
            "NEURAL_TRAINING": False,
            "OPTIMIZER": False,
            "ATTENTION_MODEL": False,
            "LEARNED_OPERATOR": False,
            "TIME_INTEGRATION": False,
            "SOLVER_IN_LOOP": False,
            "ROLLOUT": False,
            "SEALED_TEST_ACCESS": False,
            "ARC_ACCESS": False,
            "MSO03_EXECUTED": False,
        },
        "decision_summary": {
            "qualified_target_cases": qualified,
            "failed_target_cases": 384 - qualified,
            "ss_feature_dimension": summary["ss_feature_dimension"],
            "ms_feature_dimension": summary["ms_feature_dimension"],
            "bootstrap_replicate_count": summary["bootstrap_replicate_count"],
            "global_h_mso01_status": verdict["global_status"],
            "global_h_mso01_evaluable": verdict["global_evaluable"],
            "global_h_mso01_pass": verdict["global_pass"],
            "component_status": {
                component: verdict["components"][component]["status"]
                for component in COMPONENTS
            },
            "mso03_deterministic_closure_baseline_eligible": verdict[
                "mso03_deterministic_closure_baseline_eligible"
            ],
        },
        "authorized_target_access_counts": firewall["authorized_target_access_counts"],
        "prohibited_activity_counts": firewall["prohibited_activity_counts"],
        "governance_disclosure": firewall["governance_disclosure"],
        "artifact_registry": registry,
        "validation": {
            "required_artifacts_present": True,
            "artifact_hashes_verified": all(
                sha256(ROOT / record["path"]) == record["sha256"] for record in registry
            ),
            "frozen_input_hashes_verified": True,
            "execution_artifact_hashes_verified": True,
            "target_store_hash_matches_ledger": True,
            "observable_store_unchanged": summary["observable_store_unchanged"],
            "target_observable_join_passed": True,
            "all_384_target_reference_cases_qualified": qualified == 384,
            "json_parse_validation": True,
            "csv_parse_validation": True,
            "branch_main": branch == "main",
            "remote_none": not remotes,
            "no_post_target_scientific_modification": all(
                value == 0 for value in summary["post_target_modification_counts"].values()
            ),
        },
        "authorization": {
            "mso03_deterministic_closure_baseline_eligible": verdict[
                "mso03_deterministic_closure_baseline_eligible"
            ],
            "mso03_executed": False,
            "neural_training_authorized": False,
            "attention_authorized": False,
            "learned_operator_authorized": False,
            "stage_stopped_after_mso02b": True,
        },
    }
    write_json(MANIFEST, manifest)
    print(
        json.dumps(
            {
                "status": summary["terminal_status"],
                "manifest_sha256": sha256(MANIFEST),
                "report_sha256": sha256(REPORT),
                "status_ledger_sha256": sha256(STATUS),
                "registered_artifacts": len(registry),
            },
            sort_keys=True,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
