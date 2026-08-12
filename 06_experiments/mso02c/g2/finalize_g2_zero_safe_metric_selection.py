#!/usr/bin/env python3
"""Finalize synthetic MSO-02C G2 without reading any historical payload."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "06_experiments/mso02c/g2"
FREEZE = ROOT / "08_manifests/mso02c_g2_synthetic_execution_freeze.json"
CONTRACT = ROOT / "00_project_contract/mso02c_g2_zero_safe_metric_selection_contract.md"
ERRATUM = ROOT / "00_project_contract/mso02c_g2_zero_safe_metric_selection_protocol_erratum.md"
AMENDMENT = ROOT / "00_project_contract/amendments/ca_mso01_zero_safe_dnn_semantics.md"
REPORT = ROOT / "07_reports/mso02c_g2_zero_safe_metric_selection_report.md"
MANIFEST = ROOT / "08_manifests/mso02c_g2_manifest.json"
STATUS = ROOT / "08_manifests/mso02c_g2_status_ledger.json"

STRESS = OUT / "synthetic_metric_stress_tests.csv"
SELECTION = OUT / "candidate_metric_selection_matrix.csv"
ZERO = OUT / "zero_semantics_audit.csv"
AGG = OUT / "aggregation_semantics_audit.csv"
BOOT = OUT / "bootstrap_compatibility_audit.csv"
THRESHOLD = OUT / "threshold_derivation_report.md"
AUDIT = OUT / "synthetic_execution_audit.json"
DERIVED = [STRESS, SELECTION, ZERO, AGG, BOOT, THRESHOLD, AUDIT]
EXECUTION_ERRATUM = ROOT / "08_manifests/mso02c_g2_synthetic_execution_erratum_01.json"
FINALIZER_ERRATUM_1 = ROOT / "08_manifests/mso02c_g2_finalizer_erratum_01.json"
FINALIZER_ERRATUM_2 = ROOT / "08_manifests/mso02c_g2_finalizer_erratum_02.json"
EVIDENCE_ERRATUM = ROOT / "08_manifests/mso02c_g2_release_evidence_erratum_01.json"
ERRATA = [EXECUTION_ERRATUM, FINALIZER_ERRATUM_1, FINALIZER_ERRATUM_2, EVIDENCE_ERRATUM]
RELEASE_STAGING = OUT / ".g2_release_staging"
TERMINAL = "MSO02C_DNN_DEGENERACY_ATTRIBUTED_AND_ZERO_SAFE_REQUALIFICATION_CONTRACT_FROZEN"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def strict_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(), parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text)
    tmp.replace(path)


def exact_keys(rows: list[dict[str, str]], fields: tuple[str, ...], expected: set[tuple[str, ...]], label: str) -> None:
    actual = [tuple(row[field] for field in fields) for row in rows]
    if len(actual) != len(set(actual)) or set(actual) != expected:
        raise RuntimeError(f"MSO02C_G2_{label}_KEYSPACE_FAILURE")


def publish(staged: Path, final: Path) -> None:
    final.parent.mkdir(parents=True, exist_ok=True)
    if final.exists():
        if sha256(final) != sha256(staged):
            raise RuntimeError(f"MSO02C_G2_RELEASE_CONFLICT:{final}")
        return
    os.link(staged, final)


def main() -> None:
    freeze = strict_json(FREEZE)
    if git("branch", "--show-current") != "main" or git("remote"):
        raise RuntimeError("MSO02C_G2_FINALIZER_GIT_FAILURE")
    allowed = {f"?? {str(path.relative_to(ROOT))}" for path in DERIVED}
    actual = {line for line in git("status", "--porcelain").splitlines() if line}
    if actual != allowed:
        raise RuntimeError(f"MSO02C_G2_FINALIZER_DIRTY_SET_FAILURE:{sorted(actual ^ allowed)}")
    head = git("rev-parse", "HEAD")
    if freeze["execution_commit_recording"] != "CURRENT_HEAD_CONTAINING_EXACT_FROZEN_ARTIFACT_BLOBS":
        raise RuntimeError("MSO02C_G2_FINALIZER_COMMIT_RULE_MISSING")
    if git("show", f"HEAD:{FREEZE.relative_to(ROOT)}") != FREEZE.read_text().strip() or not head:
        raise RuntimeError("MSO02C_G2_FINALIZER_COMMIT_FAILURE")
    for rel, expected in freeze["artifact_sha256"].items():
        if sha256(ROOT / rel) != expected:
            raise RuntimeError(f"MSO02C_G2_FINALIZER_FROZEN_HASH_FAILURE:{rel}")
    for path in [AMENDMENT, REPORT, MANIFEST, STATUS]:
        if path.exists():
            raise RuntimeError(f"MSO02C_G2_FINAL_OUTPUT_EXISTS:{path}")
    if RELEASE_STAGING.exists():
        raise RuntimeError("MSO02C_G2_RELEASE_STAGING_EXISTS")
    for erratum in ERRATA:
        strict_json(erratum)

    audit = strict_json(AUDIT)
    stress = read_csv(STRESS)
    selection = read_csv(SELECTION)
    zero = read_csv(ZERO)
    aggregation = read_csv(AGG)
    bootstrap = read_csv(BOOT)
    if len(stress) != 84 or len(selection) != 48 or len(zero) != 20 or len(aggregation) != 12 or len(bootstrap) != 14:
        raise RuntimeError("MSO02C_G2_DERIVED_ROW_COUNT_FAILURE")
    stress_expected = {(f"S{i}", candidate, arm) for i in range(1, 19) for candidate in "ABCD" for arm in (("SS", "MS") if i >= 16 else (("SS",) if i == 14 else (("MS",) if i == 15 else ("POINT",))))}
    exact_keys(stress, ("fixture_id", "candidate", "arm"), stress_expected, "STRESS")
    exact_keys(selection, ("candidate", "criterion_id"), {(candidate, str(i)) for candidate in "ABCD" for i in range(1, 13)}, "SELECTION")
    exact_keys(zero, ("scenario", "level"), {(scenario, level) for scenario in ("ZERO_ZERO", "POSITIVE_ZERO", "ZERO_POSITIVE", "POSITIVE_POSITIVE") for level in ("POINTWISE", "AGGREGATE")} | {(fixture, f"RELATIVE_{candidate}") for fixture in ("S16", "S17", "S18") for candidate in "ABCD"}, "ZERO")
    exact_keys(aggregation, ("audit_id", "candidate"), {(audit_id, candidate) for audit_id in ("CASE_EQUAL_S11", "FAMILY_BALANCE_S12", "CELL_ZERO_NO_LOCAL_DIVISION_S7") for candidate in "ABCD"}, "AGGREGATION")
    if len({row["test_id"] for row in bootstrap}) != 14 or not all(row["executed"] == "true" and row["pass"] == "true" for row in bootstrap):
        raise RuntimeError("MSO02C_G2_BOOTSTRAP_EXECUTED_EVIDENCE_FAILURE")
    if not all(row["expectation_pass"] == "true" for row in stress):
        raise RuntimeError("MSO02C_G2_SYNTHETIC_EXPECTATION_FAILURE")
    candidate_all_pass = [candidate for candidate in "ABCD" if all(row["pass_for_primary"] == "true" for row in selection if row["candidate"] == candidate)]
    if candidate_all_pass != ["C"] or audit["selected_primary"] != "C":
        raise RuntimeError("MSO02C_G2_SELECTION_RECOMPUTE_FAILURE")
    if audit["real_target_or_observable_payload_reads"] != 0 or audit["consumed_replay"]:
        raise RuntimeError("MSO02C_G2_FIREWALL_FAILURE")
    if not audit["bootstrap_execution"]["all_pass"] or audit["bootstrap_execution"]["draw_count"] != 10_000:
        raise RuntimeError("MSO02C_G2_BOOTSTRAP_AUDIT_FAILURE")
    for path in DERIVED[:-1]:
        if audit["artifact_sha256"][str(path.relative_to(ROOT))] != sha256(path):
            raise RuntimeError(f"MSO02C_G2_AUDIT_HASH_FAILURE:{path}")

    amendment = f"""# CA-MSO-01: prospective zero-safe DNN semantics\n\nStatus: `FROZEN_PROSPECTIVELY_BEFORE_ANY_CONSUMED_REPLAY_OR_H_MSO01R_TARGET_ACCESS`.\n\n## Immutable scientific boundary\n\nThe old hypotheses remain permanently unchanged:\n\n- `MSO02B_PAIRED_PRELEARNING_IDENTIFIABILITY_REQUALIFICATION_NOT_EVALUABLE`\n- `H_MSO01_MULTISCALE_IDENTIFIABILITY_RESCUE_NOT_EVALUABLE`\n\nThis amendment creates only the future hypothesis `H-MSO-01R`. Consumed MSO-02B and G1 A/B evidence had already been seen. One over-broad old-metric text search was disclosed before protocol freeze; its matched-file count was not recorded and no numeric value from it was used. G2 performed no real candidate metric computation, store payload read, or consumed replay.\n\n## Prospective DNN statistic\n\nFor arm `a`, component `q`, case `c`, and registered particle `i`, retain frozen K=10 neighbours, matched-random comparators, exclusions, features, normalization, and Euclidean distance. Let `n[a,q,c,i]` and `b[q,c,i]` be their squared target-disagreement energies. First average all particles within each case to `N[a,q,c]` and `B[q,c]`. Then apply\n\n`W(x) = mean_fold mean_family mean_lineage mean_case-within-lineage x[c]`.\n\nThe H-MSO-01R DNN statistic is exactly `D[a,q]=W(N[a,q])/W(B[q])`. It is not a mean of particle, case, lineage, family, or fold ratios. No registered particle, case, lineage, family, or fold is deleted. If `W(B)==0`, the statistic is `NO_AGGREGATE_RANDOM_CONTRAST_NOT_EVALUABLE`; no epsilon, tolerance, clipping, or automatic PASS is allowed.\n\n## Gates\n\nThe absolute DNN gate requires both point `D<1` and the three-component simultaneous one-sided 95% UCB `<1`; equality is random-equivalent and does not qualify. For positive SS, the relative gate requires point `D_MS/D_SS<=0.80` and simultaneous UCB `<=0.90`. If SS is zero, relative rescue is `RELATIVE_RESCUE_NOT_EVALUABLE_ZERO_SS_BASELINE`. If SS is positive and MS is zero, exact-zero dominance requires every otherwise-valid paired draw to retain that branch.\n\nBootstrap uses 10,000 fresh target-blind paired lineage-first draws, the same draw for SS/MS and all components, and recomputes W(N), W(B), and their ratio from case primitives in every draw. More than 200 degenerate draws or fewer than two valid draws makes the DNN metric family NOT_EVALUABLE; max-studentized one-sided 95% multiplicity correction spans the three components.\n\nAll non-DNN gates remain unchanged. H-MSO-01R requires a completely fresh 384-case atlas, 96 per family, zero lineage overlap, fresh target-blind SS/MS freeze, folds, normalization, bootstrap, and only then target access. This amendment authorizes no replay, execution, MSO-03, attention, neural training, or learned operator.\n"""
    RELEASE_STAGING.mkdir(parents=True)
    staged_amendment = RELEASE_STAGING / AMENDMENT.name
    atomic_text(staged_amendment, amendment)

    answers = [
        "A, B, C, and D were compared under the frozen protocol.",
        "No real MSO-02B target performance was read or computed; one pre-freeze over-broad old-metric text search is disclosed, with zero numeric values used.",
        "No epsilon, tolerance floor, clipping, or deletion was used.",
        "A was rejected because isolated 0/0 is non-evaluable and positive/0 is unbounded at particle level, breaking total zero-safe bootstrap semantics.",
        "B was rejected as primary because global case weighting permits family, fold, and lineage-size dominance; it remains a mathematical comparator.",
        "C was selected because it alone passed all twelve hard criteria and all S1-S18 expectations.",
        "D was rejected because it requires an extra independently justified scale and loses the NN-versus-random interpretation.",
        "All S1-S18 fixtures completed with every frozen expectation passing.",
        "Candidate C: D=W(N)/W(B), with case, lineage, family, and fold balance before one division.",
        "Isolated 0/0 is retained in the aggregates; only a zero total denominator makes C NOT_EVALUABLE.",
        "Pointwise positive/0 is adverse-unbounded for A; for aggregate C, a zero total denominator is NOT_EVALUABLE with an auxiliary positive-numerator flag.",
        "An entire zero-denominator stratum contributes its numerator and zero denominator; C remains defined if total W(B)>0.",
        "If SS is zero, relative rescue is RELATIVE_RESCUE_NOT_EVALUABLE_ZERO_SS_BASELINE.",
        "The absolute gate is point and simultaneous UCB strictly below 1, the independently defined matched-random equivalence boundary.",
        "Yes. A point ratio of 0.80 is exactly a 20% reduction in the same squared-disagreement estimand; UCB remains at most 0.90.",
        "Yes. Every fresh paired lineage-first replicate recomputes W(N)/W(B); ratios are never bootstrapped as precomputed observations.",
        "Yes. All non-DNN gates remain unchanged.",
        "Yes. Old H-MSO-01 remains permanently NOT_EVALUABLE.",
        "Yes. The prospective CA-MSO-01 amendment is frozen by this release.",
        "Yes. H-MSO-01R receives only fresh requalification eligibility and is not executed.",
        "No consumed replay was executed.",
        "No MSO-03, neural, attention, optimizer, training, or learned-operator activity was authorized.",
        TERMINAL,
    ]
    report_lines = ["# MSO-02C G2 zero-safe metric selection report", "", f"Terminal status: `{TERMINAL}`", "", "## Required 23-question audit", ""]
    for index, answer in enumerate(answers, start=1):
        report_lines += [f"### {index}", "", answer, ""]
    staged_report = RELEASE_STAGING / REPORT.name
    atomic_text(staged_report, "\n".join(report_lines))

    registry_paths = [CONTRACT, ERRATUM, FREEZE, *ERRATA, *DERIVED]
    status_payload = {
        "schema_version": "MSO02C_G2_STATUS_V1",
        "terminal_status": TERMINAL,
        "g1_final_commit": "b6dac26624b9b45912a79e6cddec1c0caa509adf",
        "g2_pre_synthetic_commit": freeze["protocol_commit"],
        "g2_execution_commit": audit["execution_commit"],
        "g2_finalization_source_commit": head,
        "g2_final_commit": "RECORDED_BY_FINAL_GIT_COMMIT_AND_HANDOFF",
        "selected_primary": "C",
        "h_mso01r_fresh_requalification_eligible": True,
        "old_h_mso01_permanently_not_evaluable": True,
        "old_mso02b_permanently_not_evaluable": True,
        "real_target_or_observable_payload_reads": 0,
        "old_metric_accidental_search_events": 1,
        "old_metric_matched_file_count": "NOT_RECORDED",
        "old_metric_numeric_values_used_for_selection": 0,
        "consumed_replay": False,
        "h_mso01r_executed": False,
        "mso03_eligible": False,
        "attention_authorized": False,
        "neural_training_authorized": False,
        "learned_operator_authorized": False,
        "stop_after_g2": True,
        "g1_derived_outcome_payload_reads_for_selection": audit["g1_derived_outcome_payload_reads_for_selection"],
        "bootstrap_executed_test_count": audit["bootstrap_execution"]["test_count"],
        "bootstrap_synthetic_draw_count": audit["bootstrap_execution"]["draw_count"],
        "report_sha256": sha256(staged_report),
        "amendment_sha256": sha256(staged_amendment),
    }
    staged_status = RELEASE_STAGING / STATUS.name
    atomic_text(staged_status, json.dumps(status_payload, indent=2, sort_keys=True, allow_nan=False) + "\n")
    manifest_payload = {
        "schema_version": "MSO02C_G2_MANIFEST_V1",
        "terminal_status": TERMINAL,
        "selected_primary": "C",
        "h_mso01r_fresh_requalification_eligible": True,
        "firewall": {
            "real_candidate_performance_comparison": False,
            "real_target_or_observable_payload_reads": 0,
            "g1_derived_outcome_payload_reads_for_selection": 0,
            "consumed_replay": False,
            "old_metric_accidental_search_events": 1,
            "old_metric_matched_file_count": "NOT_RECORDED",
            "old_metric_numeric_values_used_for_selection": 0,
            "new_h3_verdict": False,
            "h_mso01r_executed": False,
            "mso03_eligible": False,
            "attention_authorized": False,
            "neural_training_authorized": False,
            "learned_operator_authorized": False,
        },
        "artifact_registry": [
            {"path": str(path.relative_to(ROOT)), "sha256": sha256(path), "role": "G2_FROZEN_OR_DERIVED_ARTIFACT"}
            for path in registry_paths
        ] + [
            {"path": str(AMENDMENT.relative_to(ROOT)), "sha256": sha256(staged_amendment), "role": "G2_FROZEN_AMENDMENT"},
            {"path": str(REPORT.relative_to(ROOT)), "sha256": sha256(staged_report), "role": "G2_FINAL_REPORT"},
            {"path": str(STATUS.relative_to(ROOT)), "sha256": sha256(staged_status), "role": "G2_TERMINAL_STATUS"}
        ],
        "manifest_self_binding": {"path": str(MANIFEST.relative_to(ROOT)), "whole_file_sha256": "REPORTED_BY_FINAL_GIT_HANDOFF", "binding": "FINAL_GIT_BLOB_AT_G2_FINAL_COMMIT"},
    }
    staged_manifest = RELEASE_STAGING / MANIFEST.name
    atomic_text(staged_manifest, json.dumps(manifest_payload, indent=2, sort_keys=True, allow_nan=False) + "\n")
    # Parse and hash every staged release before publishing. Status is terminal-last.
    strict_json(staged_manifest)
    strict_json(staged_status)
    if sha256(staged_report) != status_payload["report_sha256"] or sha256(staged_amendment) != status_payload["amendment_sha256"]:
        raise RuntimeError("MSO02C_G2_RELEASE_STAGED_HASH_FAILURE")
    publish(staged_amendment, AMENDMENT)
    publish(staged_report, REPORT)
    publish(staged_manifest, MANIFEST)
    publish(staged_status, STATUS)
    shutil.rmtree(RELEASE_STAGING)
    print(json.dumps({"terminal_status": TERMINAL, "manifest_sha256": sha256(MANIFEST), "report_sha256": sha256(REPORT), "status_sha256": sha256(STATUS)}, sort_keys=True))


if __name__ == "__main__":
    main()
