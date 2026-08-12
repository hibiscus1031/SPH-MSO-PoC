#!/usr/bin/env python3
"""Validate and release MSO-02C G1 A/B attribution without store access."""

from __future__ import annotations

from collections import Counter, defaultdict
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "06_experiments/mso02c"
REPORT = ROOT / "07_reports/mso02c_g1_ab_attribution_report.md"
MANIFEST = ROOT / "08_manifests/mso02c_g1_ab_attribution_manifest.json"
STATUS = ROOT / "08_manifests/mso02c_g1_ab_attribution_status_ledger.json"
FREEZE = ROOT / "08_manifests/mso02c_g1_descriptor_reconstruction_execution_freeze.json"
RUNNER = OUT / "run_descriptor_neighbour_ab_attribution.py"
FINALIZER = Path(__file__).resolve()
AUTHORIZATION = ROOT / "00_project_contract/mso02c_g1_descriptor_neighbour_reconstruction_authorization.md"

NEIGHBOURS = OUT / "descriptor_neighbour_identity_reconstruction.csv"
AB = OUT / "zero_denominator_ab_attribution.csv"
COMPONENT = OUT / "ab_attribution_component_summary.csv"
FAMILY_FOLD = OUT / "ab_attribution_family_fold_summary.csv"
MECHANISM = OUT / "degeneracy_mechanism_audit_after_ab.csv"
ACCESS = OUT / "descriptor_reconstruction_access_audit.json"
JOURNAL = OUT / "descriptor_reconstruction_execution_events.jsonl"

EXECUTION_OUTPUTS = (NEIGHBOURS, AB, COMPONENT, FAMILY_FOLD, MECHANISM, ACCESS)
RELEASE_OUTPUTS = (REPORT, MANIFEST, STATUS)
STAGING_ROOT = OUT / ".g1_release_staging"

ARMS = ("SS", "MS")
COMPONENTS = (
    "density_rate",
    "pressure_gradient_acceleration",
    "viscosity_laplacian_acceleration",
)
EXPECTED_QUERIES = {
    "density_rate": 2,
    "pressure_gradient_acceleration": 119,
    "viscosity_laplacian_acceleration": 2,
}
EXPECTED_CASES = {
    "density_rate": 2,
    "pressure_gradient_acceleration": 87,
    "viscosity_laplacian_acceleration": 2,
}
TERMINAL = "MSO02C_G1_ZERO_DENOMINATOR_AB_ATTRIBUTION_COMPLETE"
OLD_MSO02B = "MSO02B_PAIRED_PRELEARNING_IDENTIFIABILITY_REQUALIFICATION_NOT_EVALUABLE"
OLD_H_MSO01 = "H_MSO01_MULTISCALE_IDENTIFIABILITY_RESCUE_NOT_EVALUABLE"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def truth(value: str) -> bool:
    if value not in ("True", "False"):
        raise RuntimeError(f"noncanonical Boolean {value!r}")
    return value == "True"


def write_text_atomic(path: Path, text: str) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    write_text_atomic(
        path,
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
    )


def git_head() -> str:
    branch = subprocess.run(
        ["git", "branch", "--show-current"], cwd=ROOT, check=True,
        capture_output=True, text=True,
    ).stdout.strip()
    remotes = subprocess.run(
        ["git", "remote"], cwd=ROOT, check=True, capture_output=True, text=True,
    ).stdout.split()
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
        capture_output=True, text=True,
    ).stdout.strip()
    if branch != "main" or remotes:
        raise RuntimeError("MSO02C_G1_GIT_HANDOFF_CONFLICT")
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    for path, expected in (
        (RUNNER, freeze["executable_sha256"]),
        (FINALIZER, freeze["finalizer_sha256"]),
        (FREEZE, sha256(FREEZE)),
        (AUTHORIZATION, freeze["authorization_sha256"]),
    ):
        relative = path.relative_to(ROOT)
        committed = subprocess.run(
            ["git", "show", f"HEAD:{relative}"], cwd=ROOT, check=True,
            capture_output=True,
        ).stdout
        if hashlib.sha256(committed).hexdigest() != expected or sha256(path) != expected:
            raise RuntimeError(f"execution commit blob mismatch {relative}")
    for relative, expected in freeze["frozen_input_sha256"].items():
        if sha256(ROOT / relative) != expected:
            raise RuntimeError(f"frozen G1 input mismatch {relative}")
    return head


def git_dirty_allowlist() -> None:
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, check=True,
        capture_output=True, text=True,
    ).stdout.splitlines()
    allowed = {
        str(path.relative_to(ROOT)) for path in (*EXECUTION_OUTPUTS, JOURNAL, *RELEASE_OUTPUTS)
    }
    staging_prefix = str(STAGING_ROOT.relative_to(ROOT)) + "/"
    for line in status:
        if not line.startswith("?? "):
            raise RuntimeError(f"tracked mutation before G1 release: {line}")
        relative = line[3:]
        if relative not in allowed and not relative.startswith(staging_prefix):
            raise RuntimeError(f"unexpected untracked path before G1 release: {relative}")


def verify_rows() -> dict[str, Any]:
    rows_nn = read_csv(NEIGHBOURS)
    rows_ab = read_csv(AB)
    rows_component = read_csv(COMPONENT)
    rows_family_fold = read_csv(FAMILY_FOLD)
    rows_mechanism = read_csv(MECHANISM)
    if [len(rows_nn), len(rows_ab), len(rows_component), len(rows_family_fold), len(rows_mechanism)] != [2460, 246, 6, 144, 103]:
        raise RuntimeError("G1 output row-count identity failure")

    nn_by_key: dict[tuple[str, str, str, int], list[dict[str, str]]] = defaultdict(list)
    for row in rows_nn:
        key = (row["arm"], row["component"], row["case_id"], int(row["particle_id"]))
        nn_by_key[key].append(row)
    if len(nn_by_key) != 246:
        raise RuntimeError("G1 neighbour query key count failure")
    for key, rows in nn_by_key.items():
        rows.sort(key=lambda row: int(row["nn_rank"]))
        if [int(row["nn_rank"]) for row in rows] != list(range(1, 11)):
            raise RuntimeError(f"K10 rank failure {key}")
        distance = [float.fromhex(row["descriptor_distance_hex"]) for row in rows]
        if any(not math.isfinite(value) or value < 0.0 for value in distance):
            raise RuntimeError(f"invalid descriptor distance {key}")
        if any(distance[index] > distance[index + 1] for index in range(9)):
            raise RuntimeError(f"nonmonotone descriptor distance {key}")
        if len({row["neighbour_set_sha256"] for row in rows}) != 1:
            raise RuntimeError(f"neighbour hash instability {key}")

    # The same arm/query has one descriptor K10 identity across target components.
    by_arm_query: dict[tuple[str, str, int], tuple[tuple[str, str], ...]] = {}
    for key, rows in nn_by_key.items():
        arm, _, case_id, particle_id = key
        identity = tuple((row["nn_case_id"], row["nn_particle_id"]) for row in rows)
        query = (arm, case_id, particle_id)
        if query in by_arm_query and by_arm_query[query] != identity:
            raise RuntimeError(f"cross-component neighbour mismatch {query}")
        by_arm_query[query] = identity

    ab_by_key: dict[tuple[str, str, str, int], dict[str, str]] = {}
    for row in rows_ab:
        key = (row["arm"], row["component"], row["case_id"], int(row["particle_id"]))
        if key in ab_by_key:
            raise RuntimeError(f"duplicate A/B row {key}")
        ab_by_key[key] = row
        if float(row["matched_random_denominator"]) != 0.0 or not truth(
            row["matched_random_denominator_exact_zero"]
        ):
            raise RuntimeError(f"denominator identity failure {key}")
        numerator = float.fromhex(row["descriptor_nn_numerator_hex"])
        if float(row["descriptor_nn_numerator"]) != numerator:
            raise RuntimeError(f"numerator decimal/hex mismatch {key}")
        if not math.isfinite(numerator) or numerator < 0.0:
            raise RuntimeError(f"invalid numerator {key}")
        label_a = truth(row["classification_A_zero_over_zero"])
        label_b = truth(row["classification_B_positive_over_zero"])
        if label_a == label_b or label_a != (numerator == 0.0) or label_b != (numerator > 0.0):
            raise RuntimeError(f"A/B classification failure {key}")
        if row["nn_neighbour_identity_sha256"] != nn_by_key[key][0]["neighbour_set_sha256"]:
            raise RuntimeError(f"A/B-neighbour identity mismatch {key}")
    if set(ab_by_key) != set(nn_by_key):
        raise RuntimeError("A/B and neighbour key mismatch")

    by_arm_component: dict[tuple[str, str], dict[str, Any]] = {}
    for arm in ARMS:
        for component in COMPONENTS:
            subset = [row for row in rows_ab if row["arm"] == arm and row["component"] == component]
            result = {
                "query_count": len(subset),
                "A_count": sum(truth(row["classification_A_zero_over_zero"]) for row in subset),
                "B_count": sum(truth(row["classification_B_positive_over_zero"]) for row in subset),
                "affected_case_count": len({row["case_id"] for row in subset}),
                "query_target_exact_zero_count": sum(truth(row["query_target_exact_zero"]) for row in subset),
            }
            if result["query_count"] != EXPECTED_QUERIES[component]:
                raise RuntimeError(f"query conservation failure {arm}/{component}")
            if result["A_count"] + result["B_count"] != result["query_count"]:
                raise RuntimeError(f"A/B conservation failure {arm}/{component}")
            if result["affected_case_count"] != EXPECTED_CASES[component]:
                raise RuntimeError(f"case conservation failure {arm}/{component}")
            by_arm_component[(arm, component)] = result

    expected_component_keys = {
        (arm, component) for arm in ARMS for component in COMPONENTS
    }
    recorded_component_keys = [
        (row["arm"], row["component"]) for row in rows_component
    ]
    if (
        len(recorded_component_keys) != len(set(recorded_component_keys))
        or set(recorded_component_keys) != expected_component_keys
    ):
        raise RuntimeError("component summary key-space failure")
    for row in rows_component:
        key = (row["arm"], row["component"])
        expected = by_arm_component[key]
        for field in ("zero_denominator_query_count", "A_count", "B_count", "affected_case_count"):
            source = {
                "zero_denominator_query_count": "query_count",
                "A_count": "A_count",
                "B_count": "B_count",
                "affected_case_count": "affected_case_count",
            }[field]
            if int(row[field]) != expected[source]:
                raise RuntimeError(f"component summary mismatch {key}/{field}")
        subset = [
            value for value in rows_ab
            if value["arm"] == key[0] and value["component"] == key[1]
        ]
        if int(row["affected_family_count"]) != len({value["family"] for value in subset}):
            raise RuntimeError(f"component family count mismatch {key}")
        if int(row["affected_fold_count"]) != len({value["fold"] for value in subset}):
            raise RuntimeError(f"component fold count mismatch {key}")
        if int(row["affected_lineage_count"]) != len({value["field_lineage_id"] for value in subset}):
            raise RuntimeError(f"component lineage count mismatch {key}")
        if float(row["A_fraction"]) != expected["A_count"] / expected["query_count"] or float(row["B_fraction"]) != expected["B_count"] / expected["query_count"]:
            raise RuntimeError(f"component fraction mismatch {key}")
        positive = [
            float.fromhex(value["descriptor_nn_numerator_hex"])
            for value in subset if truth(value["descriptor_nn_numerator_positive"])
        ]
        expected_min = min(positive) if positive else None
        recorded_min = float(row["numerator_min_positive"]) if row["numerator_min_positive"] else None
        if recorded_min != expected_min:
            raise RuntimeError(f"component positive minimum mismatch {key}")

    family_fold_counter = Counter(
        (row["arm"], row["component"], row["family"], row["fold"],
         truth(row["classification_A_zero_over_zero"]))
        for row in rows_ab
    )
    expected_family_fold_keys = {
        (arm, component, family, f"FOLD_{fold}")
        for arm in ARMS for component in COMPONENTS
        for family in ("F1", "F2", "F3", "F4") for fold in range(6)
    }
    recorded_family_fold_keys = [
        (row["arm"], row["component"], row["family"], row["fold"])
        for row in rows_family_fold
    ]
    if (
        len(recorded_family_fold_keys) != len(set(recorded_family_fold_keys))
        or set(recorded_family_fold_keys) != expected_family_fold_keys
    ):
        raise RuntimeError("family-fold summary key-space failure")
    for row in rows_family_fold:
        base = (row["arm"], row["component"], row["family"], row["fold"])
        a_count = family_fold_counter[base + (True,)]
        b_count = family_fold_counter[base + (False,)]
        if int(row["A_count"]) != a_count or int(row["B_count"]) != b_count:
            raise RuntimeError(f"family-fold summary mismatch {base}")
        if int(row["zero_denominator_query_count"]) != a_count + b_count:
            raise RuntimeError(f"family-fold conservation mismatch {base}")
        subset = [
            value for value in rows_ab
            if (value["arm"], value["component"], value["family"], value["fold"]) == base
        ]
        if int(row["affected_case_count"]) != len({value["case_id"] for value in subset}):
            raise RuntimeError(f"family-fold case mismatch {base}")
        if int(row["affected_lineage_count"]) != len({value["field_lineage_id"] for value in subset}):
            raise RuntimeError(f"family-fold lineage mismatch {base}")
        if subset:
            if float(row["A_fraction"]) != a_count / len(subset) or float(row["B_fraction"]) != b_count / len(subset):
                raise RuntimeError(f"family-fold fraction mismatch {base}")
        elif row["A_fraction"] or row["B_fraction"]:
            raise RuntimeError(f"family-fold empty fraction mismatch {base}")

    mechanism_index = {
        (row["scope"], row["arm"], row["component"], row["family"], row["mechanism"]): row
        for row in rows_mechanism
    }
    if len(mechanism_index) != len(rows_mechanism):
        raise RuntimeError("mechanism audit duplicate-key failure")
    for mechanism, classification in (
        ("M1", "SUPPORTED"), ("M2", "SUPPORTED"), ("M3", "SUPPORTED"),
        ("M4", "INCONCLUSIVE"), ("M5", "NOT_SUPPORTED"), ("M6", "NOT_SUPPORTED"),
    ):
        row = mechanism_index[("GLOBAL", "BOTH", "ALL", "ALL", mechanism)]
        if row["classification"] != classification:
            raise RuntimeError(f"global mechanism mismatch {mechanism}")
    if mechanism_index[("GLOBAL", "BOTH", "ALL", "ALL", "M2")][
        "analytical_symmetry_subtype"
    ] != "INCONCLUSIVE_AT_ANALYTICAL_SYMMETRY_SUBTYPE":
        raise RuntimeError("M2 subtype overclaim")
    for arm in ARMS:
        for component in COMPONENTS:
            for family in ("F1", "F2", "F3", "F4"):
                values = {
                    mechanism: mechanism_index[
                        ("ARM_COMPONENT_FAMILY", arm, component, family, mechanism)
                    ]
                    for mechanism in ("M2a", "M2b", "M2c", "M2d")
                }
                query_count = int(values["M2a"]["query_count"])
                subset = [
                    value for value in rows_ab
                    if value["arm"] == arm and value["component"] == component
                    and value["family"] == family
                ]
                expected_evidence = {
                    "M2a": sum(truth(value["query_target_exact_zero"]) for value in subset),
                    "M2b": sum(not truth(value["query_target_exact_zero"]) for value in subset),
                    "M2c": sum(truth(value["all_nn_targets_exact_equal_query"]) for value in subset),
                    "M2d": sum(not truth(value["all_nn_targets_exact_equal_query"]) for value in subset),
                }
                if query_count != len(subset):
                    raise RuntimeError("M2 query count mismatch")
                for mechanism, expected_count in expected_evidence.items():
                    if int(values[mechanism]["evidence_count"]) != expected_count:
                        raise RuntimeError(f"M2 evidence mismatch {arm}/{component}/{family}/{mechanism}")
                if int(values["M2a"]["evidence_count"]) + int(values["M2b"]["evidence_count"]) != query_count:
                    raise RuntimeError("M2a/M2b nonconservation")
                if int(values["M2c"]["evidence_count"]) + int(values["M2d"]["evidence_count"]) != query_count:
                    raise RuntimeError("M2c/M2d nonconservation")

    ss_keys = {(row["component"], row["case_id"], int(row["particle_id"])) for row in rows_ab if row["arm"] == "SS"}
    ms_keys = {(row["component"], row["case_id"], int(row["particle_id"])) for row in rows_ab if row["arm"] == "MS"}
    if ss_keys != ms_keys:
        raise RuntimeError("SS/MS zero query sets not colocated")
    difference_by_component: dict[str, int] = {}
    for component in COMPONENTS:
        difference_by_component[component] = sum(
            by_arm_query[("SS", case_id, particle_id)]
            != by_arm_query[("MS", case_id, particle_id)]
            for comp, case_id, particle_id in ss_keys if comp == component
        )

    polarization_by_component = {
        component: dict(Counter(
            row["query_polarization"] for row in rows_ab
            if row["arm"] == "SS" and row["component"] == component
        ))
        for component in COMPONENTS
    }
    return {
        "neighbours": rows_nn,
        "ab": rows_ab,
        "component": rows_component,
        "family_fold": rows_family_fold,
        "mechanism": rows_mechanism,
        "by_arm_component": by_arm_component,
        "mechanism_index": mechanism_index,
        "ss_ms_query_sets_colocated": True,
        "neighbour_difference_by_component": difference_by_component,
        "neighbour_difference_total": sum(difference_by_component.values()),
        "polarization_by_component": polarization_by_component,
    }


def verify_access(head: str) -> dict[str, Any]:
    audit = json.loads(ACCESS.read_text(encoding="utf-8"))
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    if audit["status"] != "MSO02C_G1_AB_ATTRIBUTION_EXECUTION_COMPLETE_AWAITING_FINALIZATION":
        raise RuntimeError("runner asserted terminal status before finalization")
    if audit["descriptor_reconstruction_execution_commit"] != head:
        raise RuntimeError("execution commit mismatch")
    if audit["execution_freeze_sha256"] != sha256(FREEZE):
        raise RuntimeError("execution freeze mismatch")
    if audit["executable_sha256"] != freeze["executable_sha256"]:
        raise RuntimeError("runner hash mismatch")
    if audit["observable_store_sha256_before"] != freeze["observable_store"]["recorded_sha256"] or audit["observable_store_sha256_after"] != freeze["observable_store"]["recorded_sha256"]:
        raise RuntimeError("recorded observable identity mismatch")
    if audit["target_store_sha256_before"] != freeze["target_store"]["recorded_sha256"] or audit["target_store_sha256_after"] != freeze["target_store"]["recorded_sha256"]:
        raise RuntimeError("recorded target identity mismatch")
    if audit["observable_payload_keys_read"] != ["ss_features", "ms_features"]:
        raise RuntimeError("observable key allowlist failure")
    if audit["target_payload_keys_read"] != freeze["target_store"]["authorized_payload_keys"]:
        raise RuntimeError("target key allowlist failure")
    for key in (
        "python_implementation", "python", "numpy", "scipy", "machine", "byteorder",
        "float64_itemsize", "float64_ieee_binary64",
    ):
        if audit["runtime_fingerprint"].get(key) != freeze["runtime_freeze"][key]:
            raise RuntimeError(f"runtime fingerprint mismatch {key}")
    counts = audit["access_counts"]
    expected = {
        "observable_store_hash_reads": 2,
        "observable_store_hash_reads_completed": 2,
        "observable_store_opaque_hash_reads": 2,
        "observable_archive_metadata_reads": 1,
        "observable_archive_metadata_reads_completed": 1,
        "observable_payload_store_open_sessions": 1,
        "observable_store_payload_reads": 2,
        "observable_payload_array_reads": 2,
        "ss_features_reads": 1,
        "ms_features_reads": 1,
        "other_observable_payload_key_reads": 0,
        "target_store_hash_reads": 2,
        "target_store_hash_reads_completed": 2,
        "target_store_opaque_hash_reads": 2,
        "target_archive_metadata_reads": 1,
        "target_archive_metadata_reads_completed": 1,
        "target_payload_store_open_sessions": 1,
        "target_store_payload_reads": 3,
        "target_payload_array_reads": 3,
        "target_density_rate_reads": 1,
        "target_pressure_gradient_acceleration_reads": 1,
        "target_viscosity_laplacian_acceleration_reads": 1,
        "other_target_payload_key_reads": 0,
        "checkpoint_opaque_hash_reads": 0,
        "checkpoint_payload_reads": 0,
        "metric_payload_reads": 0,
        "bootstrap_payload_reads": 0,
        "query_target_row_consumptions": 246,
        "selected_k10_neighbour_target_row_consumptions": 2460,
        "descriptor_nn_numerator_attempts": 246,
        "descriptor_nn_numerator_completed": 246,
    }
    for key, value in expected.items():
        if counts.get(key) != value:
            raise RuntimeError(f"access-count mismatch {key}")
    if counts["descriptor_nn_required_k20_search_attempts"] != counts["descriptor_nn_required_k20_searches_completed"] or counts["descriptor_nn_required_k20_repeat_attempts"] != counts["descriptor_nn_required_k20_repeats_completed"] or counts["descriptor_nn_required_k20_searches_completed"] != counts["descriptor_nn_required_k20_repeats_completed"]:
        raise RuntimeError("deterministic search count mismatch")
    if (
        audit.get("zero_query_count") != 246
        or audit.get("ss_reconstructed_query_count") != 123
        or audit.get("ms_reconstructed_query_count") != 123
        or audit["reconstruction_counts"]["zero_query_count"] != 246
        or audit["reconstruction_counts"]["ss_reconstructed_query_count"] != 123
        or audit["reconstruction_counts"]["ms_reconstructed_query_count"] != 123
    ):
        raise RuntimeError("required query count aliases missing")
    if any(int(value) != 0 for value in audit["prohibited_counts"].values()):
        raise RuntimeError("prohibited computation recorded")
    false_flags = (
        "old_mso02b_or_h_mso01_verdict_modified", "metric_selection_authorized",
        "metric_amendment_authorized", "zero_safe_metric_selected",
        "metric_amendment_created", "consumed_replay", "h_mso01r_contract_frozen",
        "h_mso01r_fresh_requalification_eligible",
        "h_mso01r_fresh_requalification_authorized", "mso03_eligible",
        "attention_authorized", "neural_training_authorized", "learned_operator_authorized",
        "METRIC_SELECTION_AUTHORIZED", "METRIC_AMENDMENT_AUTHORIZED",
        "H_MSO01R_FRESH_REQUALIFICATION_AUTHORIZED", "MSO03_ELIGIBLE",
        "ATTENTION_AUTHORIZED", "NEURAL_TRAINING_AUTHORIZED",
        "LEARNED_OPERATOR_AUTHORIZED",
    )
    if any(audit.get(key) is not False for key in false_flags):
        raise RuntimeError("authorization firewall flag failure")
    if audit["preserved_mso02b_terminal_status"] != OLD_MSO02B or audit["preserved_h_mso01_global_status"] != OLD_H_MSO01:
        raise RuntimeError("old verdict preservation failure")

    journal_rows = [json.loads(line) for line in JOURNAL.read_text(encoding="utf-8").splitlines()]
    if not journal_rows or journal_rows[-1]["event"] != "EXECUTION_OUTPUTS_PUBLISHED_AWAITING_FINALIZATION":
        raise RuntimeError("execution event journal incomplete")
    if journal_rows[-1]["access_counts"] != counts:
        raise RuntimeError("event journal/access audit count mismatch")
    computation_events = [
        row for row in journal_rows if row["event"] == "COMPUTATION_COMPLETE"
    ]
    actual_output_sha = {path.name: sha256(path) for path in EXECUTION_OUTPUTS}
    if (
        len(computation_events) != 1
        or computation_events[0].get("staged_sha256") != actual_output_sha
        or journal_rows[-1].get("published_sha256") != actual_output_sha
    ):
        raise RuntimeError("execution journal artifact-source binding failure")
    return audit


def counts_table(data: dict[str, Any]) -> dict[str, dict[str, dict[str, int]]]:
    result: dict[str, dict[str, dict[str, int]]] = {arm: {} for arm in ARMS}
    for arm in ARMS:
        for component in COMPONENTS:
            result[arm][component] = data["by_arm_component"][(arm, component)]
    return result


def report_text(head: str, data: dict[str, Any], audit: dict[str, Any]) -> str:
    counts = counts_table(data)
    global_mechanism = {
        mechanism: data["mechanism_index"][("GLOBAL", "BOTH", "ALL", "ALL", mechanism)]
        for mechanism in ("M1", "M2", "M3", "M4", "M5", "M6", "M7")
    }
    a_total = sum(counts[arm][component]["A_count"] for arm in ARMS for component in COMPONENTS)
    b_total = sum(counts[arm][component]["B_count"] for arm in ARMS for component in COMPONENTS)
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    lines = [
        "# MSO-02C G1 Descriptor-Neighbour A/B Attribution Report",
        "",
        f"Terminal status: `{TERMINAL}`.",
        "",
        "This is consumed-evidence diagnostic attribution only. It does not amend or re-verdict MSO-02B/H-MSO-01.",
        "",
        "## Required 23 answers",
        "",
        f"1. **Yes.** The observable SHA-256 matched before and after: `{audit['observable_store_sha256_before']}`. Release validation used the recorded hash chain and did not reread the store.",
        f"2. Observable payload keys read: `{', '.join(audit['observable_payload_keys_read'])}`. Target keys read: `{', '.join(audit['target_payload_keys_read'])}`.",
        "3. **Yes.** Only `ss_features` and `ms_features` were read from the observable payload; other observable payload-key reads were 0.",
        f"4. **Yes.** The hash-bound old runner `{freeze['authoritative_algorithm']['source_sha256']}` supplied six outer folds, frozen normalization, Euclidean distance, same-case/same-lineage/equal-nonzero-seed exclusions, complete tie ordering, internal required K=20, and consumption of ranks 1–10 only. No K5/K20 metric was evaluated.",
        f"5. **Yes.** {audit['reconstruction_counts']['descriptor_nn_required_k20_internal_constructions']} primary searches and {audit['reconstruction_counts']['descriptor_nn_required_k20_determinism_repeat_constructions']} repeats were exactly equal.",
    ]
    question_by_component = ((6, "density_rate", "density"), (7, "pressure_gradient_acceleration", "pressure"), (8, "viscosity_laplacian_acceleration", "viscosity"))
    for number, component, label in question_by_component:
        lines.append(
            f"{number}. {label}: SS A/B = {counts['SS'][component]['A_count']}/{counts['SS'][component]['B_count']} of {counts['SS'][component]['query_count']}; MS A/B = {counts['MS'][component]['A_count']}/{counts['MS'][component]['B_count']} of {counts['MS'][component]['query_count']}."
        )
    lines.extend([
        "9. **Yes.** SS/MS `(component, case_id, particle_id)` zero-query sets remained exactly colocated.",
        f"10. Representation-dependent neighbour differences occurred for {data['neighbour_difference_total']} of 123 colocated component-query keys: `{json.dumps(data['neighbour_difference_by_component'], sort_keys=True)}`.",
        f"11. **{'Yes' if a_total > 0 else 'No'}.** Exact-zero numerators occurred in {a_total} of 246 arm-query classifications (classification A); by arm/component: `{json.dumps({arm: {component: counts[arm][component]['A_count'] for component in COMPONENTS} for arm in ARMS}, sort_keys=True)}`.",
        f"12. **{'Yes' if b_total > 0 else 'No'}.** Positive numerators over exact-zero denominators occurred in {b_total} of 246 classifications (classification B); by arm/component: `{json.dumps({arm: {component: counts[arm][component]['B_count'] for component in COMPONENTS} for arm in ARMS}, sort_keys=True)}`.",
        f"13. M1={global_mechanism['M1']['classification']}, M2={global_mechanism['M2']['classification']}, and M3={global_mechanism['M3']['classification']}. M2 supports exact-target multiplicity, while its analytical symmetry subtype remains `INCONCLUSIVE_AT_ANALYTICAL_SYMMETRY_SUBTYPE`.",
        f"14. Pressure affected 119 queries in 87/384 cases per arm, versus 2 queries in 2/384 cases for density and viscosity. This wider incidence is linked to observed binary64 exact/repeated pressure-target multiplicity and frozen matched-random exact equality; A/B separates local K10 0/0 from positive/0. Polarization counts were `{json.dumps(data['polarization_by_component']['pressure_gradient_acceleration'], sort_keys=True)}`. The evidence does not uniquely identify a manufactured-field analytical symmetry, so that subtype remains inconclusive.",
        f"15. M5={global_mechanism['M5']['classification']}; M6={global_mechanism['M6']['classification']}; M7={global_mechanism['M7']['classification']}. Prior raw/store and serializer identity remained frozen, and exact-source deterministic reconstruction found no residual implementation fault; no historical particle-neighbour array had been persisted for bytewise comparison.",
        "16. **No.** Full DNN median/p90 recomputation counts were 0.",
        "17. **No.** Candidate zero-safe metric performance count was 0.",
        "18. **No.** Metric selection was neither authorized nor performed.",
        "19. **No.** No metric amendment was authorized or created.",
        f"20. **Yes.** The old states remain `{OLD_MSO02B}` and `{OLD_H_MSO01}`; modified=false.",
        "21. **No.** Neural, attention, optimizer, training, integration, solver-in-loop, rollout, sealed-test, and ARC counts were all 0.",
        "22. **Yes.** MSO-03 remains unauthorized/ineligible.",
        f"23. Final terminal status: `{TERMINAL}`.",
        "",
        "## Governance",
        "",
        f"Execution-freeze commit: `{head}`. The completion commit is recorded by the final Git handoff without rewriting this release.",
        "",
        "Immediate stop boundary: no candidate selection, amendment, consumed metric replay, H-MSO-01R, MSO-03, or learning follows this release.",
    ])
    return "\n".join(lines) + "\n"


def artifact_entry(path: Path, role: str) -> dict[str, Any]:
    return {
        "path": str(path.relative_to(ROOT)),
        "sha256": sha256(path),
        "role": role,
    }


def publish(staging: Path, order: tuple[Path, ...]) -> None:
    for final_path in order:
        staged = staging / final_path.name
        if not staged.is_file():
            raise RuntimeError(f"missing staged release artifact {staged}")
        if final_path.exists():
            if sha256(final_path) != sha256(staged):
                raise RuntimeError(f"conflicting partial release artifact {final_path}")
            continue
        staged.replace(final_path)


def main() -> None:
    # This finalizer never references either store path and performs no store read/hash.
    head = git_head()
    git_dirty_allowlist()
    if not all(path.is_file() for path in (*EXECUTION_OUTPUTS, JOURNAL)):
        raise RuntimeError("MSO02C_G1_AB_ATTRIBUTION_INCOMPLETE")
    data = verify_rows()
    audit = verify_access(head)
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    freeze_sha = sha256(FREEZE)
    staging = STAGING_ROOT / freeze_sha
    staging.mkdir(parents=True, exist_ok=True)

    staged_report = staging / REPORT.name
    staged_status = staging / STATUS.name
    staged_manifest = staging / MANIFEST.name
    write_text_atomic(staged_report, report_text(head, data, audit))

    counts = counts_table(data)
    status_payload = {
        "schema_version": "1.0.0",
        "stage": "MSO-02C_G1_DESCRIPTOR_NEIGHBOUR_AB_ATTRIBUTION",
        "terminal_status": TERMINAL,
        "starting_parent_head": "8943de6b2b82dc25e850cab18eebe40c2939319d",
        "observable_access_authorization_commit": "c76026f5aac782718f83fc4369811eaeeec194a9",
        "descriptor_reconstruction_execution_freeze_commit": head,
        "mso02c_g1_ab_attribution_commit": "RECORDED_BY_FINAL_GIT_COMMIT_AND_HANDOFF",
        "report_path": str(REPORT.relative_to(ROOT)),
        "report_sha256": sha256(staged_report),
        "descriptor_reconstruction_access_audit_sha256": sha256(ACCESS),
        "descriptor_reconstruction_access_counts": audit["access_counts"],
        "finalizer_access_counts": {
            "observable_store_hash_reads": 0,
            "observable_store_payload_reads": 0,
            "target_store_hash_reads": 0,
            "target_store_payload_reads": 0,
            "checkpoint_payload_reads": 0,
            "metric_payload_reads": 0,
            "bootstrap_payload_reads": 0,
        },
        "component_counts": counts,
        "ss_ms_query_key_sets_colocated": data["ss_ms_query_sets_colocated"],
        "representation_dependent_neighbour_difference_count": data["neighbour_difference_total"],
        "preserved_mso02b_status": OLD_MSO02B,
        "preserved_h_mso01_status": OLD_H_MSO01,
        "old_verdict_modified": False,
        "metric_selection_authorized": False,
        "metric_amendment_authorized": False,
        "zero_safe_metric_selected": False,
        "metric_amendment_created": False,
        "consumed_replay": False,
        "h_mso01r_contract_frozen": False,
        "h_mso01r_fresh_requalification_authorized": False,
        "h_mso01r_fresh_requalification_eligible": False,
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
        "stop_after_ab_attribution": True,
    }
    write_json_atomic(staged_status, status_payload)

    registry_paths = (
        ROOT / "00_project_contract/mso02c_dnn_degeneracy_diagnostic_contract.md",
        AUTHORIZATION,
        RUNNER,
        FINALIZER,
        FREEZE,
        ROOT / "06_experiments/mso02c/zero_denominator_particle_map.csv",
        ROOT / "06_experiments/mso02c/zero_denominator_case_map.csv",
        ROOT / "06_experiments/mso02c/zero_denominator_family_fold_summary.csv",
        ROOT / "06_experiments/mso02c/degeneracy_mechanism_audit.csv",
        ROOT / "06_experiments/mso02c/attribution_execution_audit.json",
        ROOT / "06_experiments/mso02c/run_zero_denominator_attribution.py",
        ROOT / "08_manifests/mso02c_g1_attribution_execution_freeze.json",
        *EXECUTION_OUTPUTS,
        JOURNAL,
    )
    registry = [artifact_entry(path, "FROZEN_INPUT_OR_G1_EXECUTION_ARTIFACT") for path in registry_paths]
    registry.extend([
        {"path": str(REPORT.relative_to(ROOT)), "sha256": sha256(staged_report), "role": "FINAL_REPORT"},
        {"path": str(STATUS.relative_to(ROOT)), "sha256": sha256(staged_status), "role": "TERMINAL_STATUS_LEDGER"},
    ])
    manifest_payload = {
        "schema_version": "1.0.0",
        "project": "SPH-MSO",
        "stage": "MSO-02C_G1_DESCRIPTOR_NEIGHBOUR_AB_ATTRIBUTION",
        "terminal_status": TERMINAL,
        "starting_parent_head": "8943de6b2b82dc25e850cab18eebe40c2939319d",
        "observable_access_authorization_commit": "c76026f5aac782718f83fc4369811eaeeec194a9",
        "descriptor_reconstruction_execution_freeze_commit": head,
        "mso02c_g1_ab_attribution_commit": "RECORDED_BY_FINAL_GIT_COMMIT_AND_HANDOFF",
        "artifact_registry": registry,
        "manifest_self_binding": {
            "path": str(MANIFEST.relative_to(ROOT)),
            "whole_file_sha256": "REPORTED_BY_FINALIZER_OUTPUT_AND_FINAL_GIT_HANDOFF",
            "binding": "FINAL_GIT_BLOB_AT_MSO02C_G1_AB_ATTRIBUTION_COMMIT",
        },
        "recorded_store_identities_no_release_reread": {
            "observable_store_sha256": freeze["observable_store"]["recorded_sha256"],
            "target_store_sha256": freeze["target_store"]["recorded_sha256"],
            "verification_mode": "RECORDED_HASH_CHAIN_NO_RELEASE_REREAD",
            "finalizer_observable_store_hash_reads": 0,
            "finalizer_observable_store_payload_reads": 0,
            "finalizer_target_store_hash_reads": 0,
            "finalizer_target_store_payload_reads": 0,
        },
        "preserved_scientific_state": {
            "mso02b": OLD_MSO02B,
            "h_mso01": OLD_H_MSO01,
            "modified": False,
        },
        "authorization_firewall": {
            "metric_selection_authorized": False,
            "metric_amendment_authorized": False,
            "consumed_replay_authorized": False,
            "h_mso01r_authorized": False,
            "mso03_authorized": False,
            "learning_authorized": False,
            "attention_authorized": False,
            "ATTENTION_AUTHORIZED": False,
        },
        "stop_after_ab_attribution": True,
    }
    write_json_atomic(staged_manifest, manifest_payload)

    # Strict staged roundtrip and one-way hash chain before terminal publication.
    parsed_status = json.loads(staged_status.read_text(encoding="utf-8"))
    parsed_manifest = json.loads(staged_manifest.read_text(encoding="utf-8"))
    if parsed_status["terminal_status"] != TERMINAL or parsed_manifest["terminal_status"] != TERMINAL:
        raise RuntimeError("staged terminal identity failure")
    registry_by_path = {row["path"]: row["sha256"] for row in parsed_manifest["artifact_registry"]}
    if registry_by_path[str(REPORT.relative_to(ROOT))] != sha256(staged_report) or registry_by_path[str(STATUS.relative_to(ROOT))] != sha256(staged_status):
        raise RuntimeError("staged release hash-chain failure")

    # Status is published last and is the unique terminal marker.
    publish(staging, (REPORT, MANIFEST, STATUS))
    for path in (staged_report, staged_manifest, staged_status):
        if path.exists():
            path.unlink()
    if staging.exists():
        staging.rmdir()
    if STAGING_ROOT.exists() and not any(STAGING_ROOT.iterdir()):
        STAGING_ROOT.rmdir()
    print(TERMINAL)
    print(f"report_sha256={sha256(REPORT)}")
    print(f"manifest_sha256={sha256(MANIFEST)}")
    print(f"status_sha256={sha256(STATUS)}")


if __name__ == "__main__":
    main()
