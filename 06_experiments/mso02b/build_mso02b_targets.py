#!/usr/bin/env python3
"""Build and qualify the isolated MSO-02B analytical target store.

This executable is intentionally unable to import the MSO-02A observable
matrix.  It hashes that immutable file as an opaque byte artifact before and
after target work, but only the formal case registry, the lambda-one vendor
operator, and the isolated analytical reference module enter target creation.
"""

from __future__ import annotations

import csv
from dataclasses import replace
import hashlib
import importlib
import io
import json
import math
from pathlib import Path
import subprocess
import sys
from typing import Any
import zipfile

import numpy as np
import torch


ROOT = Path(__file__).resolve().parents[2]
VENDOR = ROOT / "01_provenance/vendor/ddo_analytical_reference"
ref: Any = None


FORMAL = ROOT / "05_registries/mso02a_formal_fresh_atlas_registry.json"
PRECOMPUTE = ROOT / "08_manifests/mso02b_target_precompute_freeze.json"
OBSERVABLE = ROOT / "06_experiments/mso02a/observable/mso02a_observable_store.npz"
OUT = ROOT / "06_experiments/mso02b"
TARGET_DIR = OUT / "target_ref"
TARGET_STORE = TARGET_DIR / "mso02b_target_store.npz"
QUALIFICATION = OUT / "target_reference_qualification.csv"
LEDGER = OUT / "target_access_ledger.json"

PRIMARY = ("density_rate", "pressure", "viscosity")
STORE_NAMES = {
    "density_rate": "target_density_rate",
    "pressure": "target_pressure_gradient_acceleration",
    "viscosity": "target_viscosity_laplacian_acceleration",
}
CHANNEL_SCALE_KEYS = {
    "density_rate": "continuum_density_rate",
    "pressure": "continuum_pressure_acceleration",
    "viscosity": "continuum_viscosity_acceleration",
    "acceleration": "continuum_acceleration",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else ["status"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_deterministic_npz(path: Path, arrays: dict[str, np.ndarray]) -> None:
    """Write a byte-reproducible compressed NPZ with fixed member metadata."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with zipfile.ZipFile(
        temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for name in sorted(arrays):
            payload = io.BytesIO()
            np.lib.format.write_array(payload, np.asarray(arrays[name]), allow_pickle=False)
            info = zipfile.ZipInfo(f"{name}.npy", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            archive.writestr(info, payload.getvalue(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    temporary.replace(path)


def graph_equal(left: Any, right: Any) -> bool:
    fields = (
        "row",
        "col",
        "displacement",
        "distance",
        "edge_support",
        "particle_support",
        "domain_min",
        "domain_max",
    )
    return left.particle_count == right.particle_count and all(
        torch.equal(getattr(left, name), getattr(right, name)) for name in fields
    )


def all_finite(values: dict[str, torch.Tensor]) -> bool:
    return all(bool(torch.isfinite(value).all()) for value in values.values())


def permutation_seed(case_id: str) -> int:
    payload = f"MSO02B|NEIGHBOR_PERMUTATION|{case_id}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big") & ((1 << 63) - 1)


def float32_graph(graph: Any) -> Any:
    return replace(
        graph,
        displacement=graph.displacement.to(torch.float32),
        distance=graph.distance.to(torch.float32),
        edge_support=graph.edge_support.to(torch.float32),
        particle_support=graph.particle_support.to(torch.float32),
        domain_min=graph.domain_min.to(torch.float32),
        domain_max=graph.domain_max.to(torch.float32),
    )


def frozen_identity_check() -> dict[str, str]:
    branch = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    remotes = subprocess.run(
        ["git", "remote"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.split()
    if branch != "main" or status or remotes:
        raise RuntimeError("MSO02B_TARGET_EXECUTION_GIT_BOUNDARY_FAILURE")
    freeze = json.loads(PRECOMPUTE.read_text(encoding="utf-8"))
    mismatches = []
    actual_by_relative: dict[str, str] = {}
    for relative, expected in freeze["frozen_input_sha256"].items():
        actual = sha256(ROOT / relative)
        actual_by_relative[relative] = actual
        if actual != expected:
            mismatches.append(f"{relative}:{actual}!={expected}")
    for relative, expected in freeze["execution_artifact_sha256"].items():
        actual = sha256(ROOT / relative)
        if actual != expected:
            mismatches.append(f"{relative}:{actual}!={expected}")
    if mismatches:
        raise RuntimeError("MSO02B_FROZEN_EVIDENCE_IDENTITY_FAILURE:" + ";".join(mismatches))
    observable_relative = "06_experiments/mso02a/observable/mso02a_observable_store.npz"
    observable_hash = actual_by_relative[observable_relative]
    expected_observable = freeze["frozen_input_sha256"][
        observable_relative
    ]
    if observable_hash != expected_observable:
        raise RuntimeError("MSO02B_FROZEN_EVIDENCE_IDENTITY_FAILURE:observable_store")
    return {"observable_before": observable_hash, "freeze": sha256(PRECOMPUTE)}


def scale_for_reference(name: str, analytic: torch.Tensor, sph: torch.Tensor) -> float:
    return ref.characteristic_scale(
        ref.FROZEN_SCALES[CHANNEL_SCALE_KEYS[name]], analytic, sph
    )


def evaluate_case(case: dict[str, Any]) -> tuple[dict[str, Any], dict[str, np.ndarray], dict[str, dict[str, float]]]:
    state = ref.make_frozen_state(case)
    graph = ref.build_periodic_neighborhood(
        state["positions"],
        float(case["support_h"]),
        domain_minimum=(0.0, 0.0),
        domain_maximum=(1.0, 1.0),
    )
    repeat_graph = ref.build_periodic_neighborhood(
        state["positions"],
        float(case["support_h"]),
        domain_minimum=(0.0, 0.0),
        domain_maximum=(1.0, 1.0),
    )
    independent_graph = ref.independent_geometry_neighborhood(
        state["positions"], float(case["support_h"])
    )
    audit = ref.audit_periodic_neighborhood(state["positions"], graph)
    independent_audit = ref.audit_periodic_neighborhood(
        state["positions"], independent_graph
    )

    derivative_a = ref.evaluator_a_general(state["positions"], case)
    derivative_b = ref.evaluator_b_general(state["positions"], case)
    continuum_a = ref.continuum_components(derivative_a, nu=state["nu"])
    continuum_b = ref.continuum_components(derivative_b, nu=state["nu"])
    # The formal L_h is the exact MSO-02A vendor-base path whose complete
    # matrix hash is registered per case.  DDO's algebraically equivalent
    # edge-dot continuity accumulation is retained only as a diagnostic below.
    operator = ref.operator_components(graph, state)
    repeat_operator = ref.operator_components(repeat_graph, state)
    independent_operator = ref.operator_components(independent_graph, state)
    discrete = ref.operator_as_discrete(operator)
    repeat_discrete = ref.operator_as_discrete(repeat_operator)
    independent_discrete = ref.operator_as_discrete(independent_operator)

    generator = torch.Generator(device="cpu")
    generator.manual_seed(permutation_seed(case["case_id"]))
    permutation = torch.randperm(graph.row.numel(), generator=generator)
    permuted_operator = ref.operator_components(
        ref.permute_neighborhood(graph, permutation), state
    )
    compensated_operator = ref.compensated_operator_components(graph, state)
    permuted_discrete = ref.operator_as_discrete(permuted_operator)
    compensated = ref.operator_as_discrete(compensated_operator)

    targets_a = ref.defects(continuum_a, discrete)
    targets_b = ref.defects(continuum_b, discrete)
    targets_repeat = ref.defects(continuum_a, repeat_discrete)
    targets_permuted = ref.defects(continuum_a, permuted_discrete)
    targets_compensated = ref.defects(continuum_a, compensated)
    targets_geometry = ref.defects(continuum_a, independent_discrete)

    ddo_algebraic = ref.discrete_components(
        graph,
        state["density"],
        state["velocity"],
        mass=float(state["mass"][0]),
        nu=state["nu"],
    )
    qualification_discrete = {
        **discrete,
        "density_sum": ddo_algebraic["density_sum"],
        "interpolation_density": ddo_algebraic["interpolation_density"],
    }
    derivative_sph = ref.derivative_sph_channels(
        derivative_a,
        qualification_discrete,
        graph,
        mass=float(state["mass"][0]),
        nu=state["nu"],
    )
    continuum_sph = ref.continuum_sph_channels(qualification_discrete)

    derivative_gate_max = 0.0
    derivative_gate_pass = True
    derivative_gate_failures: list[str] = []
    for name in derivative_a:
        scale = ref.characteristic_scale(
            ref.FROZEN_SCALES[name], derivative_a[name], derivative_sph[name]
        )
        delta = ref.linf_difference(derivative_a[name], derivative_b[name])
        bound = ref.C_FP * ref.EPS64 * scale
        derivative_gate_max = max(derivative_gate_max, delta / scale if scale else delta)
        if not (math.isfinite(delta) and delta <= bound):
            derivative_gate_pass = False
            derivative_gate_failures.append(name)
    for name in continuum_a:
        key = {
            "density": "continuum_density",
            "density_rate": "continuum_density_rate",
            "pressure_acceleration": "continuum_pressure_acceleration",
            "viscosity_acceleration": "continuum_viscosity_acceleration",
            "acceleration": "continuum_acceleration",
        }[name]
        scale = ref.characteristic_scale(
            ref.FROZEN_SCALES[key], continuum_a[name], continuum_sph[name]
        )
        delta = ref.linf_difference(continuum_a[name], continuum_b[name])
        bound = ref.C_FP * ref.EPS64 * scale
        derivative_gate_max = max(derivative_gate_max, delta / scale if scale else delta)
        if not (math.isfinite(delta) and delta <= bound):
            derivative_gate_pass = False
            derivative_gate_failures.append(f"continuum:{name}")

    target_by_name = {
        "density_rate": targets_a["density_rate"],
        "pressure": targets_a["pressure"],
        "viscosity": targets_a["viscosity"],
        "acceleration": targets_a["acceleration"],
    }
    reference_by_name = {
        "density_rate": targets_b["density_rate"],
        "pressure": targets_b["pressure"],
        "viscosity": targets_b["viscosity"],
        "acceleration": targets_b["acceleration"],
    }
    repeat_by_name = {
        "density_rate": targets_repeat["density_rate"],
        "pressure": targets_repeat["pressure"],
        "viscosity": targets_repeat["viscosity"],
        "acceleration": targets_repeat["acceleration"],
    }
    perm_by_name = {
        "density_rate": targets_permuted["density_rate"],
        "pressure": targets_permuted["pressure"],
        "viscosity": targets_permuted["viscosity"],
        "acceleration": targets_permuted["acceleration"],
    }
    comp_by_name = {
        "density_rate": targets_compensated["density_rate"],
        "pressure": targets_compensated["pressure"],
        "viscosity": targets_compensated["viscosity"],
        "acceleration": targets_compensated["acceleration"],
    }
    geometry_by_name = {
        "density_rate": targets_geometry["density_rate"],
        "pressure": targets_geometry["pressure"],
        "viscosity": targets_geometry["viscosity"],
        "acceleration": targets_geometry["acceleration"],
    }

    uncertainties: dict[str, dict[str, float]] = {}
    sign_pass = True
    for name in (*PRIMARY, "acceleration"):
        analytic, sph = ref.target_analytic_and_sph(name, continuum_a, discrete)
        scale = scale_for_reference(name, analytic, sph)
        u_round = ref.C_FP * ref.EPS64 * scale
        delta_ref = ref.linf_difference(reference_by_name[name], target_by_name[name])
        delta_repeat = ref.linf_difference(repeat_by_name[name], target_by_name[name])
        delta_perm = ref.linf_difference(perm_by_name[name], target_by_name[name])
        delta_comp = ref.linf_difference(comp_by_name[name], target_by_name[name])
        delta_accum = max(delta_perm, delta_comp)
        delta_geometry = ref.linf_difference(geometry_by_name[name], target_by_name[name])
        delta_identity = (
            ref.linf_difference(
                target_by_name["acceleration"],
                target_by_name["pressure"] + target_by_name["viscosity"],
            )
            if name == "acceleration"
            else 0.0
        )
        u_num = (
            u_round
            + delta_ref
            + delta_repeat
            + delta_accum
            + delta_geometry
            + delta_identity
        )
        residual = ref.linf_difference(sph + target_by_name[name], analytic)
        passed = bool(math.isfinite(u_num) and residual <= u_num)
        sign_pass = sign_pass and passed
        uncertainties[name] = {
            "scale": scale,
            "U_round": u_round,
            "Delta_ref": delta_ref,
            "Delta_repeat": delta_repeat,
            "Delta_permutation": delta_perm,
            "Delta_compensated": delta_comp,
            "Delta_accumulation": delta_accum,
            "Delta_geometry": delta_geometry,
            "Delta_identity": delta_identity,
            "U_num": u_num,
            "sign_residual": residual,
            "sign_gate_passed": passed,
            "target_rms": float(
                torch.sqrt(
                    torch.mean(
                        target_by_name[name].square()
                        if target_by_name[name].ndim == 1
                        else torch.sum(target_by_name[name].square(), dim=1)
                    )
                )
            ),
        }

    operator_hash = hashlib.sha256(
        ref.operator_matrix(operator).contiguous().numpy().tobytes()
    ).hexdigest()
    state_hash = ref.particle_state_hash(state)
    ddo_pressure_viscosity_bitwise_identity = (
        torch.equal(ddo_algebraic["pressure_acceleration"], operator["pressure_gradient_acceleration"])
        and torch.equal(ddo_algebraic["viscosity_acceleration"], operator["viscosity_laplacian_acceleration"])
    )
    ddo_density_algebraic_linf = ref.linf_difference(
        ddo_algebraic["density_rate"], operator["density_rate"]
    )
    topology_identity = torch.equal(
        ref.topology_keys(graph), ref.topology_keys(independent_graph)
    )
    topology_primary_valid = all(
        int(audit[name]) == 0
        for name in (
            "duplicate_edge_count",
            "missing_self_edge_count",
            "nonreciprocal_nonself_edge_count",
            "out_of_bounds_edge_count",
            "omitted_strict_support_edge_count",
            "unexpected_edge_count",
        )
    )
    topology_independent_valid = all(
        int(independent_audit[name]) == 0
        for name in (
            "duplicate_edge_count",
            "missing_self_edge_count",
            "nonreciprocal_nonself_edge_count",
            "out_of_bounds_edge_count",
            "omitted_strict_support_edge_count",
            "unexpected_edge_count",
        )
    ) and bool(torch.isfinite(independent_graph.displacement).all())
    graph_repeatable = graph_equal(graph, repeat_graph)
    operator_repeatable = all(
        torch.equal(operator[name], repeat_operator[name]) for name in operator
    )
    component_closure_residual = ref.linf_difference(
        target_by_name["acceleration"],
        target_by_name["pressure"] + target_by_name["viscosity"],
    )
    component_closure_bound = sum(
        uncertainties[name]["U_num"] for name in ("acceleration", "pressure", "viscosity")
    )
    component_closure_pass = component_closure_residual <= component_closure_bound

    # Float32-vs-float64 is a diagnostic only and is explicitly excluded from U_num.
    graph32 = float32_graph(graph)
    state32 = {
        **state,
        "positions": state["positions"].to(torch.float32),
        "density": state["density"].to(torch.float32),
        "velocity": state["velocity"].to(torch.float32),
        "pressure": state["pressure"].to(torch.float32),
        "mass": state["mass"].to(torch.float32),
    }
    derivative32 = ref.evaluator_a_general(state["positions"].to(torch.float32), case)
    continuum32 = ref.continuum_components(derivative32, nu=state["nu"])
    discrete32 = ref.operator_as_discrete(ref.operator_components(graph32, state32))
    targets32 = ref.defects(continuum32, discrete32)
    precision_diagnostic = max(
        ref.linf_difference(targets32["density_rate"].to(torch.float64), target_by_name["density_rate"]),
        ref.linf_difference(targets32["pressure"].to(torch.float64), target_by_name["pressure"]),
        ref.linf_difference(targets32["viscosity"].to(torch.float64), target_by_name["viscosity"]),
    )

    finite = (
        all_finite(derivative_a)
        and all_finite(derivative_b)
        and all_finite(continuum_a)
        and all_finite(continuum_b)
        and all_finite(discrete)
        and all(bool(torch.isfinite(value).all()) for value in target_by_name.values())
    )
    identity = (
        state["position_hash"] == case["position_hash"]
        and state_hash == case["particle_state_hash"]
        and operator_hash == case["operator_base_hash"]
    )
    component_identity = (
        target_by_name["density_rate"].shape == (int(case["particle_count"]),)
        and target_by_name["pressure"].shape == (int(case["particle_count"]), 2)
        and target_by_name["viscosity"].shape == (int(case["particle_count"]), 2)
        and target_by_name["acceleration"].shape == (int(case["particle_count"]), 2)
        and bool(
            torch.isfinite(
                target_by_name["pressure"] + target_by_name["viscosity"]
            ).all()
        )
        and torch.equal(
            target_by_name["density_rate"],
            continuum_a["density_rate"] - operator["density_rate"],
        )
        and torch.equal(
            target_by_name["pressure"],
            continuum_a["pressure_acceleration"]
            - operator["pressure_gradient_acceleration"],
        )
        and torch.equal(
            target_by_name["viscosity"],
            continuum_a["viscosity_acceleration"]
            - operator["viscosity_laplacian_acceleration"],
        )
    )
    case_passed = all(
        (
            derivative_gate_pass,
            finite,
            identity,
            topology_identity,
            topology_primary_valid,
            topology_independent_valid,
            graph_repeatable,
            operator_repeatable,
            component_identity,
            component_closure_pass,
            sign_pass,
            all(math.isfinite(value["U_num"]) for value in uncertainties.values()),
        )
    )
    row: dict[str, Any] = {
        "formal_case_index": int(case["formal_case_index"]),
        "case_id": case["case_id"],
        "family": case["macro_family"],
        "fold": case["fold"],
        "field_lineage_id": case["field_lineage_id"],
        "particle_count": int(case["particle_count"]),
        "case_replacement_authorized": False,
        "position_hash_matches": state["position_hash"] == case["position_hash"],
        "particle_state_hash_matches": state_hash == case["particle_state_hash"],
        "lambda_1_operator_hash_matches": operator_hash == case["operator_base_hash"],
        "lambda_1_registered_operator_is_canonical_target_path": True,
        "ddo_algebraic_pressure_viscosity_bitwise_identity": ddo_pressure_viscosity_bitwise_identity,
        "ddo_algebraic_density_rate_linf_diagnostic": ddo_density_algebraic_linf,
        "primary_topology_audit_passed": topology_primary_valid,
        "independent_topology_audit_passed": topology_independent_valid,
        "primary_edge_count": int(graph.row.numel()),
        "independent_edge_count": int(independent_graph.row.numel()),
        "independent_topology_identity": topology_identity,
        "graph_repeatability_bitwise": graph_repeatable,
        "operator_repeatability_bitwise": operator_repeatable,
        "analytical_derivative_reference_gate_passed": derivative_gate_pass,
        "analytical_derivative_reference_max_relative": derivative_gate_max,
        "analytical_derivative_reference_failures": "|".join(derivative_gate_failures),
        "finite_values": finite,
        "target_component_identity": component_identity,
        "component_closure_residual": component_closure_residual,
        "component_closure_bound": component_closure_bound,
        "component_closure_passed": component_closure_pass,
        "target_sign_convention_all_primary_passed": sign_pass,
        "float32_precision_degradation_diagnostic_linf": precision_diagnostic,
        "float32_precision_diagnostic_topology_mode": "PRIMARY_TOPOLOGY_CAST_FLOAT32_DIAGNOSTIC_ONLY",
        "target_definition": "CONTINUUM_REFERENCE_MINUS_LAMBDA_1_BASE_SPH",
        "case_target_reference_qualified": case_passed,
    }
    for name in (*PRIMARY, "acceleration"):
        prefix = {
            "density_rate": "density_rate",
            "pressure": "pressure_gradient_acceleration",
            "viscosity": "viscosity_laplacian_acceleration",
            "acceleration": "total_acceleration_derived",
        }[name]
        for key, value in uncertainties[name].items():
            row[f"{prefix}__{key}"] = value

    arrays = {
        STORE_NAMES["density_rate"]: target_by_name["density_rate"].numpy(),
        STORE_NAMES["pressure"]: target_by_name["pressure"].numpy(),
        STORE_NAMES["viscosity"]: target_by_name["viscosity"].numpy(),
        "target_total_acceleration_derived": target_by_name["acceleration"].numpy(),
    }
    return row, arrays, uncertainties


def main() -> None:
    global ref
    if TARGET_STORE.exists() or QUALIFICATION.exists() or LEDGER.exists():
        raise RuntimeError("MSO02B target outputs already exist; refusing replacement")
    identities = frozen_identity_check()
    sys.path.insert(0, str(VENDOR))
    ref = importlib.import_module("mso02b_target_reference")
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    torch.set_default_dtype(torch.float64)
    ref.assert_static_operator_import_identity()
    formal_payload = json.loads(FORMAL.read_text(encoding="utf-8"))
    cases = formal_payload["cases"]
    if len(cases) != 384 or formal_payload["family_counts"] != {
        "F1": 96,
        "F2": 96,
        "F3": 96,
        "F4": 96,
    }:
        raise RuntimeError("MSO02B_FROZEN_EVIDENCE_IDENTITY_FAILURE:formal_population")

    qualification_rows: list[dict[str, Any]] = []
    target_blocks: dict[str, list[np.ndarray]] = {
        STORE_NAMES["density_rate"]: [],
        STORE_NAMES["pressure"]: [],
        STORE_NAMES["viscosity"]: [],
        "target_total_acceleration_derived": [],
    }
    row_case, row_particle = [], []
    row_case_id, row_lineage, row_family, row_fold, row_state_hash = [], [], [], [], []
    uncertainty_case: dict[str, list[float]] = {}
    for position, case in enumerate(cases):
        if int(case["formal_case_index"]) != position:
            raise RuntimeError("MSO02B_FROZEN_EVIDENCE_IDENTITY_FAILURE:formal_order")
        row, arrays, uncertainties = evaluate_case(case)
        qualification_rows.append(row)
        for name, value in arrays.items():
            target_blocks[name].append(value)
        count = int(case["particle_count"])
        row_case.extend([position] * count)
        row_particle.extend(range(count))
        row_case_id.extend([case["case_id"]] * count)
        row_lineage.extend([case["field_lineage_id"]] * count)
        row_family.extend([case["macro_family"]] * count)
        row_fold.extend([case["fold"]] * count)
        row_state_hash.extend([case["particle_state_hash"]] * count)
        for component, values in uncertainties.items():
            for key, value in values.items():
                uncertainty_case.setdefault(f"case_{component}_{key}", []).append(float(value))
        if (position + 1) % 24 == 0:
            print(f"MSO02B_TARGET_QUALIFICATION {position + 1}/384", flush=True)

    write_csv(QUALIFICATION, qualification_rows)
    failed = [row for row in qualification_rows if not row["case_target_reference_qualified"]]
    observable_after = sha256(OBSERVABLE)
    if observable_after != identities["observable_before"]:
        raise RuntimeError("MSO02B_FROZEN_EVIDENCE_IDENTITY_FAILURE:observable_mutated")

    ledger = {
        "schema_version": "1.0.0",
        "stage": "MSO-02B",
        "status": (
            "MSO02B_TARGET_REFERENCE_QUALIFICATION_NOT_COMPLETE"
            if failed
            else "MSO02B_TARGET_REFERENCE_QUALIFIED"
        ),
        "case_replacement_authorized": False,
        "authorized_target_access_counts": {
            "formal_case_registry_reads": 1,
            "formal_case_target_generations": len(cases),
            "analytical_reference_case_evaluations_A": len(cases),
            "analytical_reference_case_evaluations_B": len(cases),
            "lambda_1_base_operator_primary_evaluations": len(cases),
            "repeat_operator_evaluations": len(cases),
            "permuted_operator_evaluations": len(cases),
            "compensated_operator_evaluations": len(cases),
            "independent_geometry_operator_evaluations": len(cases),
            "ddo_algebraic_diagnostic_operator_evaluations": len(cases),
            "float32_diagnostic_evaluations": len(cases),
            "target_store_writes": 0 if failed else 1,
            "target_store_payload_reads": 0,
            "target_store_opaque_hash_reads": 0 if failed else 1,
            "target_store_reads": 0,
            "observable_store_opaque_hash_reads": 2,
            "observable_matrix_reads_by_target_builder": 0,
        },
        "forbidden_access_counts": {
            "historical_ddo_target_archive": 0,
            "historical_ddo_h3_outcome": 0,
            "sealed_test": 0,
            "arc": 0,
        },
        "observable_store_sha256_before_target_generation": identities["observable_before"],
        "observable_store_sha256_after_target_generation": observable_after,
        "qualified_case_count": len(cases) - len(failed),
        "failed_case_count": len(failed),
        "failed_case_ids": [row["case_id"] for row in failed],
        "target_store": str(TARGET_STORE.relative_to(ROOT)) if not failed else None,
        "target_store_sha256": None,
        "target_precompute_freeze_sha256": identities["freeze"],
    }
    if failed:
        write_json(LEDGER, ledger)
        raise RuntimeError("MSO02B_TARGET_REFERENCE_QUALIFICATION_NOT_COMPLETE")

    arrays: dict[str, np.ndarray] = {
        name: np.concatenate(blocks, axis=0) for name, blocks in target_blocks.items()
    }
    arrays.update(
        {
            "formal_case_index": np.asarray(row_case, dtype=np.int16),
            "particle_id": np.asarray(row_particle, dtype=np.int16),
            "case_id": np.asarray(row_case_id),
            "lineage_id": np.asarray(row_lineage),
            "family": np.asarray(row_family),
            "fold": np.asarray(row_fold),
            "particle_state_hash": np.asarray(row_state_hash),
            "case_id_table": np.asarray([case["case_id"] for case in cases]),
            "lineage_id_table": np.asarray([case["field_lineage_id"] for case in cases]),
            "family_table": np.asarray([case["macro_family"] for case in cases]),
            "fold_table": np.asarray([case["fold"] for case in cases]),
            "particle_state_hash_table": np.asarray([case["particle_state_hash"] for case in cases]),
            "target_sign": np.asarray("CONTINUUM_REFERENCE_MINUS_LAMBDA_1_BASE_SPH"),
            "primary_component_names": np.asarray(
                [
                    "density_rate",
                    "pressure_gradient_acceleration",
                    "viscosity_laplacian_acceleration",
                ]
            ),
        }
    )
    arrays.update({name: np.asarray(values, dtype=np.float64) for name, values in uncertainty_case.items()})
    write_deterministic_npz(TARGET_STORE, arrays)
    ledger["target_store_sha256"] = sha256(TARGET_STORE)
    write_json(LEDGER, ledger)
    print(
        json.dumps(
            {
                "status": ledger["status"],
                "qualified": ledger["qualified_case_count"],
                "target_store_sha256": ledger["target_store_sha256"],
                "observable_store_unchanged": observable_after == identities["observable_before"],
            },
            sort_keys=True,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
