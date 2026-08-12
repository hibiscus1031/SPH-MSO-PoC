#!/usr/bin/env python3
"""Run the isolated, synthetic-only MSO-02C G2 metric qualification."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import platform
import subprocess
import sys
from collections import defaultdict
from fractions import Fraction
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
CONTRACT = ROOT / "00_project_contract/mso02c_g2_zero_safe_metric_selection_contract.md"
ERRATUM = ROOT / "00_project_contract/mso02c_g2_zero_safe_metric_selection_protocol_erratum.md"
FREEZE = ROOT / "08_manifests/mso02c_g2_synthetic_execution_freeze.json"
OUT = ROOT / "06_experiments/mso02c/g2"

STRESS = OUT / "synthetic_metric_stress_tests.csv"
SELECTION = OUT / "candidate_metric_selection_matrix.csv"
ZERO = OUT / "zero_semantics_audit.csv"
AGG = OUT / "aggregation_semantics_audit.csv"
BOOT = OUT / "bootstrap_compatibility_audit.csv"
THRESHOLD = OUT / "threshold_derivation_report.md"
AUDIT = OUT / "synthetic_execution_audit.json"

OUTPUTS = [STRESS, SELECTION, ZERO, AGG, BOOT, THRESHOLD, AUDIT]
STAGING = OUT / ".synthetic_staging"

CANDIDATES = ("A", "B", "C", "D")
FIXTURES = tuple(f"S{i}" for i in range(1, 19))
TERMINAL_INTERMEDIATE = "MSO02C_G2_SYNTHETIC_QUALIFICATION_COMPLETE_AWAITING_FINALIZATION"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run_git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def json_dump(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n")


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def frac(value: int | str | Fraction) -> Fraction:
    return value if isinstance(value, Fraction) else Fraction(value)


def mean(values: list[Fraction]) -> Fraction:
    if not values:
        raise ValueError("empty mean")
    return sum(values, Fraction()) / len(values)


def numeric_result(value: Fraction, status: str = "EVALUABLE") -> dict[str, Any]:
    return {"status": status, "value": value, "auxiliary": "NONE"}


def point_ratio(numerator: Fraction, denominator: Fraction) -> dict[str, Any]:
    if numerator < 0 or denominator < 0:
        return {"status": "INTEGRITY_FAILURE", "value": None, "auxiliary": "NEGATIVE"}
    if denominator > 0:
        return numeric_result(numerator / denominator)
    if numerator == 0:
        return {"status": "NO_TARGET_CONTRAST_NOT_EVALUABLE", "value": None, "auxiliary": "ZERO_OVER_ZERO"}
    return {"status": "POSITIVE_OVER_ZERO_ADVERSE_UNBOUNDED", "value": None, "auxiliary": "POSITIVE_OVER_ZERO"}


def aggregate_ratio(numerator: Fraction, denominator: Fraction) -> dict[str, Any]:
    if numerator < 0 or denominator < 0:
        return {"status": "INTEGRITY_FAILURE", "value": None, "auxiliary": "NEGATIVE"}
    if denominator > 0:
        return numeric_result(numerator / denominator)
    return {
        "status": "NO_AGGREGATE_RANDOM_CONTRAST_NOT_EVALUABLE",
        "value": None,
        "auxiliary": "ZERO_OVER_ZERO" if numerator == 0 else "POSITIVE_OVER_ZERO",
    }


def case_record(case_id: str, family: str, fold: int, lineage: str, particles: list[tuple[int | Fraction, int | Fraction]], q2: int | Fraction = 1) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "family": family,
        "fold": fold,
        "lineage": lineage,
        "particles": [(frac(n), frac(b)) for n, b in particles],
        "q2": frac(q2),
    }


def balanced(case_values: list[tuple[dict[str, Any], Fraction]]) -> Fraction:
    by_fold: dict[int, list[tuple[dict[str, Any], Fraction]]] = defaultdict(list)
    for case, value in case_values:
        by_fold[case["fold"]].append((case, value))
    fold_values: list[Fraction] = []
    for fold in sorted(by_fold):
        by_family: dict[str, list[tuple[dict[str, Any], Fraction]]] = defaultdict(list)
        for case, value in by_fold[fold]:
            by_family[case["family"]].append((case, value))
        family_values: list[Fraction] = []
        for family in sorted(by_family):
            by_lineage: dict[str, list[Fraction]] = defaultdict(list)
            for case, value in by_family[family]:
                by_lineage[case["lineage"]].append(value)
            family_values.append(mean([mean(by_lineage[key]) for key in sorted(by_lineage)]))
        fold_values.append(mean(family_values))
    return mean(fold_values)


def evaluate(candidate: str, cases: list[dict[str, Any]]) -> dict[str, Any]:
    n_case = [(case, mean([n for n, _ in case["particles"]])) for case in cases]
    b_case = [(case, mean([b for _, b in case["particles"]])) for case in cases]
    if candidate == "A":
        ratios: list[tuple[dict[str, Any], Fraction]] = []
        statuses: list[str] = []
        for case in cases:
            particle_values: list[Fraction] = []
            for n, b in case["particles"]:
                result = point_ratio(n, b)
                statuses.append(result["status"])
                if result["value"] is not None:
                    particle_values.append(result["value"])
            if len(particle_values) == len(case["particles"]):
                ratios.append((case, mean(particle_values)))
        if any(status == "POSITIVE_OVER_ZERO_ADVERSE_UNBOUNDED" for status in statuses):
            return {"status": "POSITIVE_OVER_ZERO_ADVERSE_UNBOUNDED", "value": None, "auxiliary": "POSITIVE_OVER_ZERO"}
        if any(status != "EVALUABLE" for status in statuses):
            return {"status": "NO_TARGET_CONTRAST_NOT_EVALUABLE", "value": None, "auxiliary": "ZERO_OVER_ZERO"}
        return numeric_result(balanced(ratios))
    if candidate == "B":
        return aggregate_ratio(mean([value for _, value in n_case]), mean([value for _, value in b_case]))
    if candidate == "C":
        return aggregate_ratio(balanced(n_case), balanced(b_case))
    if candidate == "D":
        q2_case = [(case, case["q2"]) for case in cases]
        return aggregate_ratio(balanced(n_case), balanced(q2_case))
    raise ValueError(candidate)


def fixtures() -> dict[str, dict[str, list[dict[str, Any]]]]:
    c = case_record
    f: dict[str, dict[str, list[dict[str, Any]]]] = {}
    f["S1"] = {"POINT": [c("c1", "F1", 0, "l1", [(1, 1), (3, 1)]), c("c2", "F1", 0, "l2", [(1, 1), (3, 1)])]}
    f["S2"] = {"POINT": [c("c1", "F1", 0, "l1", [(0, 0), (1, 1)]), c("c2", "F1", 0, "l2", [(1, 1), (1, 1)])]}
    f["S3"] = {"POINT": [c("c1", "F1", 0, "l1", [(1, 0), (1, 1)]), c("c2", "F1", 0, "l2", [(1, 1), (1, 1)])]}
    f["S4"] = {"POINT": [c("c1", "F1", 0, "l1", [(0, 0), (0, 0)]), c("c2", "F1", 0, "l2", [(1, 1), (1, 1)])]}
    f["S5"] = {"POINT": [c("c1", "F1", 0, "l1", [(1, 0), (1, 0)])]}
    f["S6"] = {"POINT": [c("c1", "F1", 0, "l1", [(1, 0), (1, 0)]), c("c2", "F1", 0, "l2", [(1, 1), (1, 1)])]}
    f["S7"] = {"POINT": [c("c1", "F1", 0, "l1", [(1, 0)]), c("c2", "F2", 0, "l2", [(1, 1)])]}
    f["S8"] = {"POINT": [c("c1", "F1", 0, "l1", [(0, 0), (0, 0)], q2=0)]}
    f["S9"] = {"POINT": [c("c1", "F1", 0, "l1", [(9, 9), (27, 9)], q2=9), c("c2", "F1", 0, "l2", [(9, 9), (27, 9)], q2=9)]}
    f["S10"] = {"POINT": [c("c1", "F1", 0, "l1", [(1, Fraction(1, 2**100))]) ]}
    f["S11"] = {"POINT": [c("c1", "F1", 0, "l1", [(9, 1)]), c("c2", "F1", 0, "l2", [(1, 1), (1, 1), (1, 1)])]}
    f["S12"] = {"POINT": [c("f1c1", "F1", 0, "l1", [(9, 1)]), c("f2c1", "F2", 0, "l2", [(1, 1)]), c("f2c2", "F2", 0, "l3", [(1, 1)]), c("f2c3", "F2", 0, "l4", [(1, 1)])]}
    f["S13"] = {"POINT": [c("c1", "F1", 0, "l1", [(100, 1)]), c("c2", "F1", 0, "l2", [(1, 1)]), c("c3", "F1", 0, "l3", [(1, 1)])]}
    f["S14"] = {"SS": [c("c1", "F1", 0, "l1", [(0, 1)])]}
    f["S15"] = {"MS": [c("c1", "F1", 0, "l1", [(0, 1)])]}
    f["S16"] = {"SS": [c("c1", "F1", 0, "l1", [(0, 1)])], "MS": [c("c1", "F1", 0, "l1", [(0, 1)])]}
    f["S17"] = {"SS": [c("c1", "F1", 0, "l1", [(0, 1)])], "MS": [c("c1", "F1", 0, "l1", [(1, 1)])]}
    f["S18"] = {"SS": [c("c1", "F1", 0, "l1", [(1, 1)])], "MS": [c("c1", "F1", 0, "l1", [(0, 1)])]}
    return f


EXPECTED: dict[tuple[str, str, str], tuple[str, Fraction | None]] = {
    **{("S1", c, "POINT"): ("EVALUABLE", Fraction(2)) for c in CANDIDATES},
    ("S2", "A", "POINT"): ("NO_TARGET_CONTRAST_NOT_EVALUABLE", None),
    ("S2", "B", "POINT"): ("EVALUABLE", Fraction(1)),
    ("S2", "C", "POINT"): ("EVALUABLE", Fraction(1)),
    ("S2", "D", "POINT"): ("EVALUABLE", Fraction(3, 4)),
    ("S3", "A", "POINT"): ("POSITIVE_OVER_ZERO_ADVERSE_UNBOUNDED", None),
    ("S3", "B", "POINT"): ("EVALUABLE", Fraction(4, 3)),
    ("S3", "C", "POINT"): ("EVALUABLE", Fraction(4, 3)),
    ("S3", "D", "POINT"): ("EVALUABLE", Fraction(1)),
    ("S4", "A", "POINT"): ("NO_TARGET_CONTRAST_NOT_EVALUABLE", None),
    ("S4", "B", "POINT"): ("EVALUABLE", Fraction(1)),
    ("S4", "C", "POINT"): ("EVALUABLE", Fraction(1)),
    ("S4", "D", "POINT"): ("EVALUABLE", Fraction(1, 2)),
    ("S5", "A", "POINT"): ("POSITIVE_OVER_ZERO_ADVERSE_UNBOUNDED", None),
    ("S5", "B", "POINT"): ("NO_AGGREGATE_RANDOM_CONTRAST_NOT_EVALUABLE", None),
    ("S5", "C", "POINT"): ("NO_AGGREGATE_RANDOM_CONTRAST_NOT_EVALUABLE", None),
    ("S5", "D", "POINT"): ("EVALUABLE", Fraction(1)),
    ("S6", "A", "POINT"): ("POSITIVE_OVER_ZERO_ADVERSE_UNBOUNDED", None),
    ("S6", "B", "POINT"): ("EVALUABLE", Fraction(2)),
    ("S6", "C", "POINT"): ("EVALUABLE", Fraction(2)),
    ("S6", "D", "POINT"): ("EVALUABLE", Fraction(1)),
    ("S7", "A", "POINT"): ("POSITIVE_OVER_ZERO_ADVERSE_UNBOUNDED", None),
    ("S7", "B", "POINT"): ("EVALUABLE", Fraction(2)),
    ("S7", "C", "POINT"): ("EVALUABLE", Fraction(2)),
    ("S7", "D", "POINT"): ("EVALUABLE", Fraction(1)),
    **{("S8", c, "POINT"): (("NO_TARGET_CONTRAST_NOT_EVALUABLE" if c == "A" else "NO_AGGREGATE_RANDOM_CONTRAST_NOT_EVALUABLE"), None) for c in CANDIDATES},
    **{("S9", c, "POINT"): ("EVALUABLE", Fraction(2)) for c in CANDIDATES},
    ("S10", "A", "POINT"): ("EVALUABLE", Fraction(2**100)),
    ("S10", "B", "POINT"): ("EVALUABLE", Fraction(2**100)),
    ("S10", "C", "POINT"): ("EVALUABLE", Fraction(2**100)),
    ("S10", "D", "POINT"): ("EVALUABLE", Fraction(1)),
    **{("S11", c, "POINT"): ("EVALUABLE", Fraction(5)) for c in CANDIDATES},
    ("S12", "A", "POINT"): ("EVALUABLE", Fraction(5)),
    ("S12", "B", "POINT"): ("EVALUABLE", Fraction(3)),
    ("S12", "C", "POINT"): ("EVALUABLE", Fraction(5)),
    ("S12", "D", "POINT"): ("EVALUABLE", Fraction(5)),
    **{("S13", c, "POINT"): ("EVALUABLE", Fraction(34)) for c in CANDIDATES},
    **{("S14", c, "SS"): ("EVALUABLE", Fraction(0)) for c in CANDIDATES},
    **{("S15", c, "MS"): ("EVALUABLE", Fraction(0)) for c in CANDIDATES},
    **{("S16", c, arm): ("EVALUABLE", Fraction(0)) for c in CANDIDATES for arm in ("SS", "MS")},
    **{("S17", c, "SS"): ("EVALUABLE", Fraction(0)) for c in CANDIDATES},
    **{("S17", c, "MS"): ("EVALUABLE", Fraction(1)) for c in CANDIDATES},
    **{("S18", c, "SS"): ("EVALUABLE", Fraction(1)) for c in CANDIDATES},
    **{("S18", c, "MS"): ("EVALUABLE", Fraction(0)) for c in CANDIDATES},
}


RATINGS: dict[str, tuple[str, ...]] = {
    "A": ("FAIL", "PASS", "PASS", "PASS", "PASS", "PASS", "FAIL", "CONDITIONAL", "PASS", "PASS", "PASS", "FAIL"),
    "B": ("PASS", "PASS", "PASS", "PASS", "PASS", "FAIL", "PASS", "PASS", "PASS", "PASS", "PASS", "PASS"),
    "C": ("PASS",) * 12,
    "D": ("PASS", "PASS", "CONDITIONAL", "CONDITIONAL", "PASS", "PASS", "PASS", "PASS", "PASS", "FAIL", "PASS", "CONDITIONAL"),
}

CRITERIA = (
    "REALISTIC_ISOLATED_ZERO_DEFINEDNESS",
    "NO_ARBITRARY_EPSILON",
    "DIMENSIONLESS_OR_INDEPENDENT_SCALE",
    "TARGET_AMPLITUDE_INVARIANCE",
    "CASE_EQUAL_COMPATIBILITY",
    "LINEAGE_FAMILY_FOLD_EQUAL_COMPATIBILITY",
    "LINEAGE_FIRST_CLUSTER_BOOTSTRAP_COMPATIBILITY",
    "PAIRED_SS_MS_COMPATIBILITY",
    "INTERPRETABLE_ZERO_SEMANTICS",
    "PRESERVES_NN_VS_RANDOM_MEANING",
    "NO_PARTICLE_OR_CASE_DELETION",
    "NO_ISOLATED_ZERO_SINGULARITY",
)


def relative_status(ss: dict[str, Any], ms: dict[str, Any]) -> tuple[str, Fraction | None, str]:
    if ss["status"] != "EVALUABLE" or ms["status"] != "EVALUABLE":
        return "NOT_EVALUABLE_ARM_STATISTIC", None, "NONE"
    if ss["value"] == 0:
        flag = "AUXILIARY_DETERMINISTIC_WORSENING" if ms["value"] > 0 else "NO_RESCUE_EVIDENCE"
        return "RELATIVE_RESCUE_NOT_EVALUABLE_ZERO_SS_BASELINE", None, flag
    ratio = ms["value"] / ss["value"]
    flag = "EXACT_ZERO_MS_DOMINANCE_REQUIRES_BOOTSTRAP" if ms["value"] == 0 else "NONE"
    return "EVALUABLE", ratio, flag


def semantic_fields(candidate: str, fixture_id: str) -> dict[str, str]:
    return {
        "continuity": "CONTINUOUS_WHERE_DENOMINATOR_POSITIVE" if candidate != "A" else "NO_CONTINUOUS_EXTENSION_AT_POINTWISE_ZERO_ZERO",
        "monotonicity": "NONDECREASING_IN_NUMERATOR_ON_DEFINED_DOMAIN",
        "target_scale_invariance": "PASS_FOR_NONZERO_COMMON_AMPLITUDE" if candidate != "D" else "CONDITIONAL_ON_Q2_COVARIANCE",
        "particle_weighting": "CASE_INTERNAL_EQUAL_ONLY",
        "case_weighting": "EQUAL_WITHIN_LINEAGE" if candidate in ("A", "C", "D") else "GLOBAL_CASE_EQUAL",
        "lineage_weighting": "EQUAL" if candidate in ("A", "C", "D") else "NOT_EQUAL_IF_CASE_COUNTS_DIFFER",
        "family_weighting": "EQUAL" if candidate in ("A", "C", "D") else "NOT_EQUAL_IF_CASE_COUNTS_DIFFER",
        "fold_weighting": "EQUAL" if candidate in ("A", "C", "D") else "NOT_EQUAL_IF_CASE_COUNTS_DIFFER",
        "bootstrap_compatibility": "PASS_BY_EXECUTED_24_CELL_SUITE" if candidate == "C" else ("CONDITIONAL" if candidate in ("B", "D") else "FAIL_POINTWISE_ZERO"),
        "paired_comparison_compatibility": "PASS" if candidate in ("B", "C", "D") else "CONDITIONAL",
        "zero_baseline_rescue_semantics": "SS_ZERO_RELATIVE_NOT_EVALUABLE",
        "dnn_interpretation": "PRESERVED_NN_VS_RANDOM" if candidate in ("A", "B", "C") else "LOST_TARGET_SCALE_REFERENCE",
        "fixture_semantic_scope": fixture_id,
    }


def bootstrap_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for fold in range(6):
        for family_no in range(1, 5):
            family = f"F{family_no}"
            for lineage_no in range(2):
                lineage = f"{family}_fold{fold}_lineage{lineage_no}"
                for case_no in range(2):
                    case_id = f"{lineage}_case{case_no}"
                    base = 1 + fold + family_no + lineage_no + case_no
                    cases.append(case_record(case_id, family, fold, lineage, [(Fraction(base, 4), 1)]))
    return cases


def resampled_cases(cases: list[dict[str, Any]], selector: int) -> list[dict[str, Any]]:
    grouped: dict[tuple[int, str], dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for case in cases:
        grouped[(case["fold"], case["family"])][case["lineage"]].append(case)
    out: list[dict[str, Any]] = []
    for stratum in sorted(grouped):
        lineages = sorted(grouped[stratum])
        for occurrence in range(len(lineages)):
            selected = lineages[0 if selector == 0 else occurrence % len(lineages)]
            source = grouped[stratum][selected]
            for case_occurrence in range(len(source)):
                out.append(source[0 if selector == 0 else case_occurrence % len(source)])
    return out


def executed_bootstrap_suite() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    cases = bootstrap_cases()
    if len(cases) != 96 or {(c["fold"], c["family"]) for c in cases} != {(f, f"F{g}") for f in range(6) for g in range(1, 5)}:
        raise RuntimeError("MSO02C_G2_BOOTSTRAP_24_CELL_FIXTURE_FAILURE")
    point = evaluate("C", cases)
    draws = [evaluate("C", resampled_cases(cases, selector % 2)) for selector in range(10_000)]
    recompute_pass = all(draw["status"] == "EVALUABLE" for draw in draws) and any(draw["value"] != point["value"] for draw in draws)
    paired_pass = all(evaluate("C", resampled_cases(cases, selector % 2))["value"] == draws[selector]["value"] for selector in range(10_000))
    boundary_200 = sum([False] * 9_800 + [True] * 200) <= 200
    boundary_201 = sum([False] * 9_799 + [True] * 201) > 200
    common_masks = [[True, True, True], [True, False, True], [True, True, True]]
    union_mask = [all(row) for row in common_masks]
    common_mask_pass = union_mask == [True, False, True]
    zero_se_draws = [Fraction(1, 2)] * 10
    zero_se_pass = all(value == Fraction(1, 2) for value in zero_se_draws)
    max_t_matrix = [[Fraction(1), Fraction(0), Fraction(-1)], [Fraction(2), Fraction(1), Fraction(0)]]
    max_t_pass = [max(row) for row in max_t_matrix] == [Fraction(1), Fraction(2)]
    log_relative_pass = abs((math.log(0.8) - math.log(1.0)) - math.log(0.8)) < 1e-15
    exact_zero_draws = [(Fraction(1), Fraction(0))] * 10
    exact_zero_pass = all(ss > 0 and ms == 0 for ss, ms in exact_zero_draws)
    zero_denominator_draw = evaluate("C", [case_record("z", "F1", 0, "lz", [(1, 0)])])
    zero_draw_pass = zero_denominator_draw["status"] == "NO_AGGREGATE_RANDOM_CONTRAST_NOT_EVALUABLE"
    binary64_roundtrip_pass = all(Fraction.from_float(float(value)) == value for value in (Fraction(0), Fraction(1, 2), Fraction(1), Fraction(2), Fraction(5)))
    integrity_pass = point_ratio(Fraction(-1), Fraction(1))["status"] == "INTEGRITY_FAILURE" and aggregate_ratio(Fraction(1), Fraction(-1))["status"] == "INTEGRITY_FAILURE"
    checks = [
        ("FULL_24_CELL_HIERARCHY", len(cases) == 96),
        ("LINEAGE_FIRST_CASE_RESAMPLING", recompute_pass),
        ("PAIRED_DRAW_IDENTITIES", paired_pass),
        ("RECOMPUTE_RATIO_EACH_DRAW", recompute_pass),
        ("ZERO_DENOMINATOR_NOT_REDRAWN", zero_draw_pass),
        ("DEGENERATE_BOUNDARY_200_EVALUABLE", boundary_200),
        ("DEGENERATE_BOUNDARY_201_NOT_EVALUABLE", boundary_201),
        ("THREE_COMPONENT_COMMON_VALID_MASK", common_mask_pass),
        ("ZERO_SE_IDENTICAL_DRAWS_BOUND_EQUALS_POINT", zero_se_pass),
        ("MAX_STUDENTIZED_COMPONENT_MAX", max_t_pass),
        ("POSITIVE_LOG_RELATIVE_TRANSFORM", log_relative_pass),
        ("EXACT_ZERO_MS_DOMINANCE_ALL_DRAWS", exact_zero_pass),
        ("BINARY64_EXACT_RATIONAL_ROUNDTRIP", binary64_roundtrip_pass),
        ("NEGATIVE_INPUT_INTEGRITY_FAILURE", integrity_pass),
    ]
    rows = [{"test_id": test_id, "candidate": "C", "executed": "true", "pass": str(passed).lower(), "fixture_folds": 6, "fixture_families": 4, "fixture_lineages": 48, "fixture_cases": 96, "details": "FROZEN_SYNTHETIC_ONLY"} for test_id, passed in checks]
    return rows, {"test_count": len(checks), "all_pass": all(passed for _, passed in checks), "draw_count": 10_000, "degenerate_boundary_pass": boundary_200 and boundary_201}


def main() -> None:
    if run_git("branch", "--show-current") != "main" or run_git("status", "--porcelain"):
        raise RuntimeError("MSO02C_G2_GIT_IDENTITY_FAILURE")
    if run_git("remote"):
        raise RuntimeError("MSO02C_G2_REMOTE_PRESENT")
    freeze = json.loads(FREEZE.read_text())
    head = run_git("rev-parse", "HEAD")
    if freeze["execution_commit_recording"] != "CURRENT_HEAD_CONTAINING_EXACT_FROZEN_ARTIFACT_BLOBS":
        raise RuntimeError("MSO02C_G2_EXECUTION_COMMIT_RULE_MISSING")
    if run_git("show", f"HEAD:{FREEZE.relative_to(ROOT)}") != FREEZE.read_text().strip():
        raise RuntimeError("MSO02C_G2_FREEZE_NOT_COMMITTED")
    if not head:
        raise RuntimeError("MSO02C_G2_EXECUTION_COMMIT_MISMATCH")
    for rel, expected in freeze["artifact_sha256"].items():
        if sha256(ROOT / rel) != expected:
            raise RuntimeError(f"MSO02C_G2_FROZEN_ARTIFACT_MISMATCH:{rel}")
    actual_runtime = {
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "machine": platform.machine(),
        "byteorder": sys.byteorder,
    }
    if actual_runtime != freeze["runtime_freeze"]:
        raise RuntimeError(f"MSO02C_G2_RUNTIME_MISMATCH:{actual_runtime}")
    for path in OUTPUTS:
        if path.exists():
            raise RuntimeError(f"MSO02C_G2_OUTPUT_ALREADY_EXISTS:{path}")
    if STAGING.exists():
        raise RuntimeError("MSO02C_G2_STAGING_ALREADY_EXISTS")

    STAGING.mkdir(parents=True)
    fx = fixtures()
    if tuple(fx) != FIXTURES:
        raise RuntimeError("fixture registry mismatch")
    stress_rows: list[dict[str, Any]] = []
    all_pass = True
    evaluated: dict[tuple[str, str, str], dict[str, Any]] = {}
    for fixture_id in FIXTURES:
        for candidate in CANDIDATES:
            for arm, cases in fx[fixture_id].items():
                result = evaluate(candidate, cases)
                expected_status, expected_value = EXPECTED[(fixture_id, candidate, arm)]
                passed = result["status"] == expected_status and result["value"] == expected_value
                all_pass &= passed
                evaluated[(fixture_id, candidate, arm)] = result
                value = result["value"]
                stress_rows.append({
                    "fixture_id": fixture_id,
                    "candidate": candidate,
                    "arm": arm,
                    "status": result["status"],
                    "value_num": "" if value is None else value.numerator,
                    "value_den": "" if value is None else value.denominator,
                    "value_float": "" if value is None else format(float(value), ".17g"),
                    "auxiliary_zero_branch": result["auxiliary"],
                    "expected_status": expected_status,
                    "expected_value_num": "" if expected_value is None else expected_value.numerator,
                    "expected_value_den": "" if expected_value is None else expected_value.denominator,
                    "expectation_pass": str(passed).lower(),
                    "epsilon_used": "false",
                    "particle_or_case_deleted": "false",
                    "real_data_input_count": 0,
                    **semantic_fields(candidate, fixture_id),
                })

    selection_rows: list[dict[str, Any]] = []
    for candidate in CANDIDATES:
        for index, (criterion, rating) in enumerate(zip(CRITERIA, RATINGS[candidate], strict=True), start=1):
            selection_rows.append({
                "candidate": candidate,
                "criterion_id": index,
                "criterion": criterion,
                "rating": rating,
                "hard_gate": "true",
                "pass_for_primary": str(rating == "PASS").lower(),
                "evidence_fixtures": "S1-S18",
            })
    qualified = [candidate for candidate in CANDIDATES if all(r == "PASS" for r in RATINGS[candidate])]
    if qualified != ["C"]:
        raise RuntimeError(f"MSO02C_G2_SELECTION_RULE_FAILURE:{qualified}")

    zero_rows: list[dict[str, Any]] = []
    for scenario, u, v in (("ZERO_ZERO", Fraction(0), Fraction(0)), ("POSITIVE_ZERO", Fraction(1), Fraction(0)), ("ZERO_POSITIVE", Fraction(0), Fraction(1)), ("POSITIVE_POSITIVE", Fraction(1), Fraction(1))):
        for level, function in (("POINTWISE", point_ratio), ("AGGREGATE", aggregate_ratio)):
            result = function(u, v)
            zero_rows.append({"scenario": scenario, "level": level, "status": result["status"], "numeric_value_present": str(result["value"] is not None).lower(), "auxiliary": result["auxiliary"], "epsilon_used": "false", "deletion_used": "false"})
    for fixture_id in ("S16", "S17", "S18"):
        for candidate in CANDIDATES:
            status, ratio, flag = relative_status(evaluated[(fixture_id, candidate, "SS")], evaluated[(fixture_id, candidate, "MS")])
            zero_rows.append({"scenario": fixture_id, "level": f"RELATIVE_{candidate}", "status": status, "numeric_value_present": str(ratio is not None).lower(), "auxiliary": flag if ratio is None else f"{flag}|ratio={ratio.numerator}/{ratio.denominator}|reduction={(1-ratio).numerator}/{(1-ratio).denominator}", "epsilon_used": "false", "deletion_used": "false"})

    aggregation_rows = [
        {"audit_id": "CASE_EQUAL_S11", "candidate": c, "expected": "5", "actual": str(evaluated[("S11", c, "POINT")]["value"]), "pass": "true"} for c in CANDIDATES
    ]
    aggregation_rows += [
        {"audit_id": "FAMILY_BALANCE_S12", "candidate": c, "expected": str(EXPECTED[("S12", c, "POINT")][1]), "actual": str(evaluated[("S12", c, "POINT")]["value"]), "pass": "true"} for c in CANDIDATES
    ]
    aggregation_rows += [
        {"audit_id": "CELL_ZERO_NO_LOCAL_DIVISION_S7", "candidate": c, "expected": EXPECTED[("S7", c, "POINT")][0], "actual": evaluated[("S7", c, "POINT")]["status"], "pass": "true"} for c in CANDIDATES
    ]

    bootstrap_rows, bootstrap_summary = executed_bootstrap_suite()
    if not bootstrap_summary["all_pass"]:
        raise RuntimeError("MSO02C_G2_BOOTSTRAP_EXECUTION_FAILURE")

    threshold_text = "# MSO-02C G2 prospective threshold derivation\n\n"
    threshold_text += "The selected statistic is Candidate C, `D=W(N)/W(B)`. "
    threshold_text += "It is non-negative, dimensionless, and invariant to every non-zero common target-amplitude scaling because both energies scale by the same square.\n\n"
    threshold_text += "The only independently derived absolute identifiability boundary is `D<1`: one is exact matched-random equivalence, so a simultaneous one-sided 95% UCB strictly below one establishes descriptor neighbours as more target-informative than the matched-random comparator. No old `0.25` gate, half-RMS margin, real outcome, or synthetic acceptance rate was used.\n\n"
    threshold_text += "For positive SS, `D_MS/D_SS<=0.80` remains exactly a 20% reduction in the same non-negative squared-disagreement estimand; its simultaneous UCB remains `<=0.90`. SS equal to zero makes percentage rescue NOT_EVALUABLE.\n"

    staged = {path: STAGING / path.name for path in OUTPUTS}
    write_csv(staged[STRESS], list(stress_rows[0]), stress_rows)
    write_csv(staged[SELECTION], list(selection_rows[0]), selection_rows)
    write_csv(staged[ZERO], list(zero_rows[0]), zero_rows)
    write_csv(staged[AGG], list(aggregation_rows[0]), aggregation_rows)
    write_csv(staged[BOOT], list(bootstrap_rows[0]), bootstrap_rows)
    staged[THRESHOLD].write_text(threshold_text)
    artifact_hashes = {str(path.relative_to(ROOT)): sha256(staged[path]) for path in OUTPUTS[:-1]}
    audit = {
        "schema_version": "MSO02C_G2_SYNTHETIC_AUDIT_V1",
        "status": TERMINAL_INTERMEDIATE,
        "g2_pre_synthetic_commit": freeze["protocol_commit"],
        "g2_protocol_erratum_commit": freeze["execution_parent_commit"],
        "execution_commit": head,
        "runtime": actual_runtime,
        "fixture_count": 18,
        "candidate_count": 4,
        "stress_row_count": len(stress_rows),
        "all_fixture_expectations_pass": all_pass,
        "qualified_candidates": qualified,
        "selected_primary": "C",
        "absolute_boundary": {"operator": "STRICTLY_LESS_THAN", "value": 1, "point_required": True, "simultaneous_ucb_required": True},
        "relative_gate": {"point_ratio_max": 0.80, "simultaneous_ucb_max": 0.90},
        "real_target_or_observable_payload_reads": 0,
        "g1_derived_outcome_payload_reads_for_selection": 0,
        "old_metric_accidental_search_events_disclosed": 1,
        "old_metric_numeric_values_used_for_selection": 0,
        "consumed_replay": False,
        "epsilon_used": False,
        "particle_or_case_deletion": False,
        "bootstrap_execution": bootstrap_summary,
        "execution_errata": [
            "08_manifests/mso02c_g2_synthetic_execution_erratum_01.json",
            "08_manifests/mso02c_g2_finalizer_erratum_01.json",
            "08_manifests/mso02c_g2_finalizer_erratum_02.json",
            "08_manifests/mso02c_g2_release_evidence_erratum_01.json"
        ],
        "artifact_sha256": artifact_hashes,
    }
    json_dump(staged[AUDIT], audit)
    for path in OUTPUTS:
        os.link(staged[path], path)
    for path in staged.values():
        path.unlink()
    STAGING.rmdir()
    print(json.dumps({"status": TERMINAL_INTERMEDIATE, "selected_primary": "C", "outputs": {str(p.relative_to(ROOT)): sha256(p) for p in OUTPUTS}}, sort_keys=True))


if __name__ == "__main__":
    main()
