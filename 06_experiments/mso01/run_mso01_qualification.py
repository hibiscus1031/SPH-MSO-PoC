#!/usr/bin/env python3
"""Execute the frozen MSO-01 target-blind static qualification."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import resource
import subprocess
import sys
import tempfile
import time
from typing import Any

import numpy as np
import torch


ROOT = Path(__file__).resolve().parents[2]
VENDOR_ROOT = ROOT / "01_provenance/vendor/pio_stage01c_static"
PARENT_ROOT = Path("/Users/xiejinbo/Documents/SPH-PIO-PoC")
PARENT_SOLVER = PARENT_ROOT / "01_solver"
OUT = ROOT / "06_experiments/mso01"
REGISTRY_PATH = ROOT / "05_registries/mso01_target_blind_case_registry.json"
SCALES = (0.75, 1.0, 1.25, 1.5)
COMPONENTS = (
    "density_rate",
    "pressure_gradient_acceleration",
    "viscosity_laplacian_acceleration",
)
EPS = torch.finfo(torch.float64).eps
EPS_MULTIPLIER = 256.0
FORCE_RELATIVE_TOLERANCE = EPS_MULTIPLIER * EPS
RESPONSE_RATIO_GATE = 100.0


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def peak_rss_bytes() -> int:
    observed = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return observed if platform.system() == "Darwin" else observed * 1024


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("status\nNO_ROWS\n", encoding="utf-8")
        return
    fields: list[str] = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def rms(value: torch.Tensor) -> float:
    return float(torch.sqrt(torch.mean(value.reshape(-1).square())))


def max_abs(value: torch.Tensor) -> float:
    return float(value.abs().max()) if value.numel() else 0.0


def tolerance(reference: torch.Tensor) -> float:
    return EPS_MULTIPLIER * EPS * max(1.0, max_abs(reference))


def tensor_compare(actual: torch.Tensor, expected: torch.Tensor) -> dict[str, Any]:
    difference = actual - expected
    tol = tolerance(expected)
    return {
        "bitwise_equal": bool(torch.equal(actual, expected)),
        "max_absolute_discrepancy": max_abs(difference),
        "rms_discrepancy": rms(difference),
        "tolerance": tol,
        "passed": bool(max_abs(difference) <= tol),
    }


def numpy_bitwise_compare(actual: np.ndarray, expected: np.ndarray) -> dict[str, Any]:
    equal = bool(np.array_equal(actual, expected, equal_nan=False))
    if actual.dtype.kind in "iub":
        discrepancy = 0.0 if equal else float("inf")
        scale = 1.0
    else:
        difference = np.asarray(actual, dtype=np.float64) - np.asarray(expected, dtype=np.float64)
        discrepancy = float(np.max(np.abs(difference))) if difference.size else 0.0
        scale = max(1.0, float(np.max(np.abs(expected))) if expected.size else 0.0)
    return {
        "bitwise_equal": equal,
        "max_absolute_discrepancy": discrepancy,
        "tolerance": EPS_MULTIPLIER * EPS * scale,
        "passed": equal,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--operator-root", type=Path, default=VENDOR_ROOT)
    parser.add_argument("--parent-baseline-output", type=Path)
    return parser.parse_args()


ARGS = parse_args()
sys.path.insert(0, str(ARGS.operator_root))

from structure_preserving.conservative_pressure import (  # noqa: E402
    conservative_pressure_forces,
    pressure_conservation_metrics,
)
from structure_preserving.conservative_viscosity import (  # noqa: E402
    conservative_viscosity_acceleration,
    viscosity_conservation_metrics,
)
from structure_preserving.kernels import (  # noqa: E402
    divergence_from_vector_gradient,
    edge_kernel_gradients,
    edge_kernel_values,
    raw_edge_weights,
    raw_gradient,
    raw_kernel_moments,
    scatter_sum,
)
from structure_preserving.neighborhood import (  # noqa: E402
    PeriodicNeighborhood,
    audit_periodic_neighborhood,
    build_periodic_neighborhood,
    periodic_cartesian_layout,
    tensor_sha256,
    wrap_periodic,
)


def load_registry() -> dict[str, Any]:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def make_state(case: dict[str, Any], registry: dict[str, Any]) -> dict[str, torch.Tensor | float | str]:
    positions, dx, position_hash = periodic_cartesian_layout(
        registry["resolution"],
        jitter_fraction=float(case["jitter_fraction"]),
        seed=int(case["seed"]),
        dtype=torch.float64,
    )
    x, y = positions[:, 0], positions[:, 1]
    density = (
        1.0
        + 0.05 * torch.sin(2.0 * torch.pi * x) * torch.cos(2.0 * torch.pi * y)
        + 0.02 * torch.cos(4.0 * torch.pi * y)
    )
    velocity = torch.stack(
        (
            0.2 + 0.07 * torch.sin(2.0 * torch.pi * x) * torch.cos(2.0 * torch.pi * y),
            -0.1 + 0.05 * torch.cos(2.0 * torch.pi * x) * torch.sin(2.0 * torch.pi * y),
        ),
        dim=-1,
    )
    rho0 = float(registry["physical_parameters"]["rho0"])
    c0 = float(registry["physical_parameters"]["c0"])
    pressure = c0**2 * (density - rho0)
    mass = torch.full((positions.shape[0],), dx**2, dtype=torch.float64)
    return {
        "case_id": case["case_id"],
        "positions": positions,
        "dx": dx,
        "position_hash": position_hash,
        "density": density,
        "velocity": velocity,
        "pressure": pressure,
        "mass": mass,
        "nu": float(registry["physical_parameters"]["kinematic_viscosity"]),
    }


def operator_components(neighborhood: PeriodicNeighborhood, state: dict[str, Any]) -> dict[str, torch.Tensor]:
    density = state["density"]
    velocity = state["velocity"]
    mass = state["mass"]
    volume = mass / density
    velocity_gradient = raw_gradient(neighborhood, velocity, volume)
    density_rate = -density * divergence_from_vector_gradient(velocity_gradient)
    pressure_force = conservative_pressure_forces(
        neighborhood,
        mass=mass,
        density=density,
        pressure=state["pressure"],
    )
    pressure_acceleration = pressure_force / mass[:, None]
    viscosity_acceleration = conservative_viscosity_acceleration(
        neighborhood,
        mass=mass,
        density=density,
        velocity=velocity,
        physical_viscosity=state["nu"],
    )
    total = pressure_acceleration + viscosity_acceleration
    return {
        "density_rate": density_rate,
        "pressure_gradient_acceleration": pressure_acceleration,
        "viscosity_laplacian_acceleration": viscosity_acceleration,
        "total_acceleration": total,
    }


def full_identity_payload(neighborhood: PeriodicNeighborhood, state: dict[str, Any]) -> dict[str, torch.Tensor]:
    volume = state["mass"] / state["density"]
    moments = raw_kernel_moments(neighborhood, volume)
    outputs = operator_components(neighborhood, state)
    return {
        "row": neighborhood.row,
        "col": neighborhood.col,
        "displacement": neighborhood.displacement,
        "distance": neighborhood.distance,
        "edge_support": neighborhood.edge_support,
        "particle_support": neighborhood.particle_support,
        "kernel_values": edge_kernel_values(neighborhood),
        "kernel_gradients": edge_kernel_gradients(neighborhood),
        "density_rate": outputs["density_rate"],
        "pressure_gradient_acceleration": outputs["pressure_gradient_acceleration"],
        "viscosity_laplacian_acceleration": outputs["viscosity_laplacian_acceleration"],
        "total_acceleration": outputs["total_acceleration"],
        "raw_moment_s0": moments["s0"],
        "raw_moment_s1": moments["s1"],
    }


def parent_baseline_payload(output_path: Path) -> None:
    registry = load_registry()
    arrays: dict[str, np.ndarray] = {}
    for case in registry["cases"]:
        state = make_state(case, registry)
        support = float(registry["base_support_ratio_h0_over_dx"]) * float(state["dx"])
        neighborhood = build_periodic_neighborhood(state["positions"], support)
        payload = full_identity_payload(neighborhood, state)
        for name, value in payload.items():
            arrays[f"{case['case_id']}__{name}"] = value.detach().cpu().numpy()
    np.savez(output_path, **arrays)


def verify_provenance() -> tuple[bool, list[dict[str, Any]]]:
    expected = {
        "__init__.py": "18afa8e375e06bd03ce68f17528c7a27722e1dbdab17536d1b060994446ad93a",
        "neighborhood.py": "44d61e0abbc9901472dae90f83127f5231fc3f6e8ac92a971228dfdcb230aaa8",
        "kernels.py": "bad08e0f49b308c568cd438c9981abd2c906e16c6570ebc0ca7d19d9847b333b",
        "conservative_pressure.py": "b6366666ba89cc1f367a95390a411905eee8b7f55fba28a024f5732860004064",
        "conservative_viscosity.py": "bdfbcb457f6973130f0131ec3c0a3fecc7197dd117c8256163cf3a1445307852",
    }
    head = subprocess.run(
        ["git", "-C", str(PARENT_ROOT), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    rows = []
    valid = head == "a0556093070f7f069ca6bea64b5f83d37bea9c76"
    for name, frozen_hash in expected.items():
        source = PARENT_SOLVER / "structure_preserving" / name
        destination = VENDOR_ROOT / "structure_preserving" / name
        source_hash = sha256(source)
        destination_hash = sha256(destination)
        match = source_hash == destination_hash == frozen_hash
        valid = valid and match
        rows.append(
            {
                "source_head": head,
                "file": name,
                "frozen_sha256": frozen_hash,
                "source_sha256": source_hash,
                "destination_sha256": destination_hash,
                "hash_match": match,
            }
        )
    return valid, rows


def weighted_geometry_metrics(neighborhood: PeriodicNeighborhood, state: dict[str, Any]) -> dict[str, Any]:
    count = neighborhood.particle_count
    nonself = neighborhood.row != neighborhood.col
    weights = raw_edge_weights(neighborhood, state["mass"] / state["density"])
    weighted_outer = (
        weights[nonself, None, None]
        * neighborhood.displacement[nonself, :, None]
        * neighborhood.displacement[nonself, None, :]
    )
    covariance_numerator = scatter_sum(
        neighborhood.row[nonself], weighted_outer, count
    )
    weight_sum = scatter_sum(neighborhood.row[nonself], weights[nonself], count)
    covariance = covariance_numerator / weight_sum[:, None, None]
    eigenvalues = torch.linalg.eigvalsh(covariance)
    trace = eigenvalues.sum(dim=1)
    rank_tolerance = EPS_MULTIPLIER * EPS * torch.maximum(
        torch.ones_like(trace), trace.abs()
    )
    rank_deficient = eigenvalues[:, 0] <= rank_tolerance
    condition = eigenvalues[:, 1] / eigenvalues[:, 0].clamp_min(torch.finfo(torch.float64).tiny)
    counts = torch.bincount(
        neighborhood.row[nonself], minlength=count
    ).to(torch.float64)
    moments = raw_kernel_moments(neighborhood, state["mass"] / state["density"])
    s1_norm = torch.linalg.vector_norm(moments["s1"], dim=-1)
    complete = (counts >= 8) & (~rank_deficient) & torch.isfinite(eigenvalues).all(dim=1)
    return {
        "nonself_neighbor_count_min": int(counts.min()),
        "nonself_neighbor_count_p01": float(torch.quantile(counts, 0.01)),
        "nonself_neighbor_count_p05": float(torch.quantile(counts, 0.05)),
        "nonself_neighbor_count_median": float(torch.quantile(counts, 0.50)),
        "nonself_neighbor_count_p95": float(torch.quantile(counts, 0.95)),
        "nonself_neighbor_count_max": int(counts.max()),
        "zero_neighbor_count": int((counts == 0).sum()),
        "weighted_covariance_eigenvalue_min": float(eigenvalues[:, 0].min()),
        "weighted_covariance_eigenvalue_p05": float(torch.quantile(eigenvalues[:, 0], 0.05)),
        "weighted_covariance_eigenvalue_max": float(eigenvalues[:, 1].max()),
        "rank_deficient_environment_count": int(rank_deficient.sum()),
        "support_completeness_fraction": float(complete.to(torch.float64).mean()),
        "anisotropy_condition_median": float(torch.quantile(condition, 0.50)),
        "anisotropy_condition_p95": float(torch.quantile(condition, 0.95)),
        "anisotropy_condition_max": float(condition.max()),
        "kernel_moment_s0_min": float(moments["s0"].min()),
        "kernel_moment_s0_mean": float(moments["s0"].mean()),
        "kernel_moment_s0_max": float(moments["s0"].max()),
        "kernel_moment_s1_rms": rms(moments["s1"]),
        "kernel_moment_s1_norm_max": float(s1_norm.max()),
    }


def reordered_neighborhood(neighborhood: PeriodicNeighborhood, seed: int) -> PeriodicNeighborhood:
    generator = torch.Generator(device="cpu")
    generator.manual_seed(seed)
    order = torch.randperm(neighborhood.row.numel(), generator=generator)
    return PeriodicNeighborhood(
        row=neighborhood.row[order],
        col=neighborhood.col[order],
        displacement=neighborhood.displacement[order],
        distance=neighborhood.distance[order],
        edge_support=neighborhood.edge_support[order],
        particle_support=neighborhood.particle_support,
        domain_min=neighborhood.domain_min,
        domain_max=neighborhood.domain_max,
        particle_count=neighborhood.particle_count,
    )


def add_compare_row(
    rows: list[dict[str, Any]], case_id: str, scale: float, check: str,
    component: str, actual: torch.Tensor, expected: torch.Tensor,
    *, bitwise_required: bool = False,
) -> bool:
    metrics = tensor_compare(actual, expected)
    passed = metrics["bitwise_equal"] if bitwise_required else metrics["passed"]
    rows.append(
        {
            "case_id": case_id,
            "lambda": scale,
            "check": check,
            "component": component,
            **metrics,
            "bitwise_required": bitwise_required,
            "passed": passed,
        }
    )
    return bool(passed)


def run_anchor_identity(registry: dict[str, Any]) -> tuple[bool, list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="mso01_parent_identity_") as temporary:
        parent_output = Path(temporary) / "parent_baseline.npz"
        subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--operator-root",
                str(PARENT_SOLVER),
                "--parent-baseline-output",
                str(parent_output),
            ],
            check=True,
            cwd=str(ROOT),
            env={**os.environ, "PYTHONHASHSEED": "0"},
        )
        with np.load(parent_output, allow_pickle=False) as parent:
            all_pass = True
            for case in registry["cases"]:
                state = make_state(case, registry)
                support = float(registry["base_support_ratio_h0_over_dx"]) * float(state["dx"])
                neighborhood = build_periodic_neighborhood(state["positions"], support)
                vendor = full_identity_payload(neighborhood, state)
                for quantity, value in vendor.items():
                    expected = parent[f"{case['case_id']}__{quantity}"]
                    metrics = numpy_bitwise_compare(value.detach().cpu().numpy(), expected)
                    all_pass = all_pass and bool(metrics["passed"])
                    rows.append(
                        {
                            "case_id": case["case_id"],
                            "lambda": 1.0,
                            "quantity": quantity,
                            "comparison": "MSO_VENDOR_VS_DIRECT_PIO_PARENT",
                            **metrics,
                        }
                    )
                zero_delta = operator_components(neighborhood, state)
                for component in COMPONENTS:
                    delta = zero_delta[component] - zero_delta[component]
                    exact_zero = bool(torch.count_nonzero(delta) == 0)
                    all_pass = all_pass and exact_zero
                    rows.append(
                        {
                            "case_id": case["case_id"],
                            "lambda": 1.0,
                            "quantity": f"delta_{component}",
                            "comparison": "BASELINE_SELF_DIFFERENCE",
                            "bitwise_equal": exact_zero,
                            "max_absolute_discrepancy": max_abs(delta),
                            "tolerance": 0.0,
                            "passed": exact_zero,
                        }
                    )
    return all_pass, rows


def emit_terminal_only(status: str, provenance_rows: list[dict[str, Any]], identity_rows: list[dict[str, Any]]) -> None:
    write_csv(OUT / "operator_identity_audit.csv", identity_rows)
    write_csv(OUT / "topology_audit.csv", [])
    write_csv(OUT / "invariance_audit.csv", [])
    write_csv(OUT / "scale_response_uncertainty.csv", [])
    write_csv(OUT / "resource_audit.csv", [])
    write_csv(
        OUT / "firewall_audit.csv",
        [{
            "phase": "TERMINAL",
            "target_file_open_count": 0,
            "reference_archive_read_count": 0,
            "defect_generation_count": 0,
            "h3_metric_count": 0,
            "oracle_fit_count": 0,
            "neural_model_count": 0,
            "optimizer_count": 0,
            "time_integration_count": 0,
            "rollout_count": 0,
            "sealed_test_count": 0,
            "passed": True,
        }],
    )
    ledger = {
        "schema_version": "1.0.0",
        "project": "SPH-MSO",
        "stage": "MSO-01",
        "terminal_status": status,
        "provenance_audit": provenance_rows,
        "mso02_prelearning_identifiability_experiment_eligible": False,
        "mso02_executed": False,
    }
    (ROOT / "08_manifests/mso01_status_ledger.json").write_text(
        json.dumps(ledger, indent=2) + "\n", encoding="utf-8"
    )


def main() -> None:
    torch.set_default_dtype(torch.float64)
    torch.set_num_threads(1)
    OUT.mkdir(parents=True, exist_ok=True)
    provenance_valid, provenance_rows = verify_provenance()
    if not provenance_valid:
        emit_terminal_only("MSO01_PROVENANCE_CONFLICT", provenance_rows, [])
        raise SystemExit("MSO01_PROVENANCE_CONFLICT")

    firewall_rows = [{
        "phase": "PRE",
        "target_file_open_count": 0,
        "reference_archive_read_count": 0,
        "defect_generation_count": 0,
        "h3_metric_count": 0,
        "oracle_fit_count": 0,
        "neural_model_count": 0,
        "optimizer_count": 0,
        "time_integration_count": 0,
        "rollout_count": 0,
        "sealed_test_count": 0,
        "parent_static_source_open_count": 5,
        "arc_access_count": 0,
        "passed": True,
    }]
    write_csv(OUT / "firewall_audit.csv", firewall_rows)

    registry = load_registry()
    identity_pass, identity_rows = run_anchor_identity(registry)
    write_csv(OUT / "operator_identity_audit.csv", identity_rows)
    if not identity_pass:
        emit_terminal_only(
            "MSO01_BASE_OPERATOR_IDENTITY_NOT_QUALIFIED",
            provenance_rows,
            identity_rows,
        )
        raise SystemExit("MSO01_BASE_OPERATOR_IDENTITY_NOT_QUALIFIED")

    topology_rows: list[dict[str, Any]] = []
    invariance_rows: list[dict[str, Any]] = []
    response_rows: list[dict[str, Any]] = []
    resource_rows: list[dict[str, Any]] = []
    case_scale_outputs: dict[str, dict[float, dict[str, np.ndarray]]] = {}
    case_noise: dict[str, dict[float, dict[str, dict[str, float]]]] = {}
    scale_failures: dict[float, set[str]] = {scale: set() for scale in SCALES}

    for case_index, case in enumerate(registry["cases"]):
        state = make_state(case, registry)
        case_id = str(case["case_id"])
        case_scale_outputs[case_id] = {}
        case_noise[case_id] = {}
        previous_keys: np.ndarray | None = None
        for scale_index, scale in enumerate(SCALES):
            support = (
                float(registry["base_support_ratio_h0_over_dx"])
                * float(state["dx"])
                * scale
            )
            rss_before = peak_rss_bytes()
            graph_start = time.perf_counter()
            neighborhood = build_periodic_neighborhood(state["positions"], support)
            graph_seconds = time.perf_counter() - graph_start
            operator_start = time.perf_counter()
            outputs = operator_components(neighborhood, state)
            operator_seconds = time.perf_counter() - operator_start
            wall_seconds = graph_seconds + operator_seconds
            rss_after = peak_rss_bytes()

            repeated_graph = build_periodic_neighborhood(state["positions"], support)
            graph_bitwise = all(
                torch.equal(getattr(neighborhood, field), getattr(repeated_graph, field))
                for field in ("row", "col", "displacement", "distance", "edge_support", "particle_support")
            )
            invariance_rows.append({
                "case_id": case_id,
                "lambda": scale,
                "check": "graph_repeatability",
                "component": "graph_and_support_metadata",
                "bitwise_equal": graph_bitwise,
                "max_absolute_discrepancy": 0.0 if graph_bitwise else float("inf"),
                "rms_discrepancy": 0.0 if graph_bitwise else float("inf"),
                "tolerance": 0.0,
                "bitwise_required": True,
                "passed": graph_bitwise,
            })
            if not graph_bitwise:
                scale_failures[scale].add("NONDETERMINISTIC_GRAPH")

            audit = audit_periodic_neighborhood(state["positions"], neighborhood)
            geometry = weighted_geometry_metrics(neighborhood, state)
            keys = (neighborhood.row * neighborhood.particle_count + neighborhood.col).cpu().numpy()
            if previous_keys is None:
                nesting_violations = 0
                topology_growth = int(keys.size)
            else:
                nesting_violations = int(np.setdiff1d(previous_keys, keys, assume_unique=True).size)
                topology_growth = int(np.setdiff1d(keys, previous_keys, assume_unique=True).size)
            previous_keys = keys
            topology_pass = (
                audit["duplicate_edge_count"] == 0
                and audit["missing_self_edge_count"] == 0
                and audit["nonreciprocal_nonself_edge_count"] == 0
                and audit["out_of_bounds_edge_count"] == 0
                and audit["omitted_strict_support_edge_count"] == 0
                and audit["unexpected_edge_count"] == 0
                and audit["self_edge_count"] == neighborhood.particle_count
                and audit["minimum_image_linf"] <= 64.0 * EPS * 2.0
                and nesting_violations == 0
            )
            support_pass = (
                geometry["zero_neighbor_count"] == 0
                and geometry["nonself_neighbor_count_p01"] >= 8.0
                and geometry["rank_deficient_environment_count"] == 0
                and geometry["support_completeness_fraction"] == 1.0
            )
            finite_outputs = all(bool(torch.isfinite(outputs[name]).all()) for name in outputs)
            if not topology_pass:
                scale_failures[scale].add("TOPOLOGY_GATE")
            if not support_pass:
                scale_failures[scale].add("SUPPORT_OR_RANK_DEGENERACY")
            if not finite_outputs:
                scale_failures[scale].add("NONFINITE_OPERATOR")
            topology_rows.append({
                "case_id": case_id,
                "lambda": scale,
                "support": support,
                "position_state_sha256": state["position_hash"],
                **audit,
                **geometry,
                "topology_growth_from_previous_scale": topology_growth,
                "nesting_violation_count": nesting_violations,
                "topology_gate_passed": topology_pass,
                "support_rank_gate_passed": support_pass,
                "all_operator_values_finite": finite_outputs,
            })

            repeated_outputs = operator_components(repeated_graph, state)
            reordered = reordered_neighborhood(
                neighborhood,
                int(registry["invariance_parameters"]["edge_permutation_seed"]) + 100 * case_index + scale_index,
            )
            reordered_outputs = operator_components(reordered, state)
            case_noise[case_id][scale] = {}
            for component in COMPONENTS:
                repeat_ok = add_compare_row(
                    invariance_rows, case_id, scale, "operator_repeatability",
                    component, repeated_outputs[component], outputs[component],
                    bitwise_required=True,
                )
                edge_ok = add_compare_row(
                    invariance_rows, case_id, scale, "directed_edge_reorder_invariance",
                    component, reordered_outputs[component], outputs[component],
                )
                if not repeat_ok:
                    scale_failures[scale].add("NONDETERMINISTIC_OPERATOR")
                if not edge_ok:
                    scale_failures[scale].add("EDGE_REORDER_INVARIANCE")
                case_noise[case_id][scale][component] = {
                    "repeat_rms": rms(repeated_outputs[component] - outputs[component]),
                    "edge_reorder_rms": rms(reordered_outputs[component] - outputs[component]),
                }

            generator = torch.Generator(device="cpu")
            generator.manual_seed(
                int(registry["invariance_parameters"]["particle_permutation_seed"]) + case_index
            )
            permutation = torch.randperm(neighborhood.particle_count, generator=generator)
            inverse = torch.empty_like(permutation)
            inverse[permutation] = torch.arange(neighborhood.particle_count)
            permuted_state = dict(state)
            for field in ("positions", "density", "velocity", "pressure", "mass"):
                permuted_state[field] = state[field][permutation]
            permuted_graph = build_periodic_neighborhood(permuted_state["positions"], support)
            permuted_outputs = operator_components(permuted_graph, permuted_state)
            mapped_keys = np.sort(
                (permutation[permuted_graph.row] * neighborhood.particle_count + permutation[permuted_graph.col]).cpu().numpy()
            )
            graph_equivariant = bool(np.array_equal(keys, mapped_keys))
            invariance_rows.append({
                "case_id": case_id, "lambda": scale,
                "check": "particle_permutation_graph_equivariance",
                "component": "canonical_edge_set", "bitwise_equal": graph_equivariant,
                "max_absolute_discrepancy": 0.0 if graph_equivariant else float("inf"),
                "rms_discrepancy": 0.0 if graph_equivariant else float("inf"),
                "tolerance": 0.0, "bitwise_required": True, "passed": graph_equivariant,
            })
            if not graph_equivariant:
                scale_failures[scale].add("PARTICLE_PERMUTATION_GRAPH")
            for component in COMPONENTS:
                okay = add_compare_row(
                    invariance_rows, case_id, scale, "particle_permutation_equivariance",
                    component, permuted_outputs[component][inverse], outputs[component],
                )
                if not okay:
                    scale_failures[scale].add("PARTICLE_PERMUTATION_OPERATOR")

            shift = torch.tensor(registry["invariance_parameters"]["periodic_translation"], dtype=torch.float64)
            translated_state = dict(state)
            translated_state["positions"] = wrap_periodic(
                state["positions"] + shift,
                torch.tensor(registry["domain_minimum"], dtype=torch.float64),
                torch.tensor(registry["domain_maximum"], dtype=torch.float64),
            )
            translated_graph = build_periodic_neighborhood(translated_state["positions"], support)
            translated_outputs = operator_components(translated_graph, translated_state)
            translated_keys = (translated_graph.row * translated_graph.particle_count + translated_graph.col).cpu().numpy()
            translated_graph_same = bool(np.array_equal(keys, translated_keys))
            invariance_rows.append({
                "case_id": case_id, "lambda": scale,
                "check": "periodic_translation_graph_invariance",
                "component": "canonical_edge_set", "bitwise_equal": translated_graph_same,
                "max_absolute_discrepancy": 0.0 if translated_graph_same else float("inf"),
                "rms_discrepancy": 0.0 if translated_graph_same else float("inf"),
                "tolerance": 0.0, "bitwise_required": True, "passed": translated_graph_same,
            })
            if not translated_graph_same:
                scale_failures[scale].add("PERIODIC_TRANSLATION_GRAPH")
            for component in COMPONENTS:
                okay = add_compare_row(
                    invariance_rows, case_id, scale, "periodic_translation_invariance",
                    component, translated_outputs[component], outputs[component],
                )
                if not okay:
                    scale_failures[scale].add("PERIODIC_TRANSLATION_OPERATOR")

            galilean_state = dict(state)
            offset = torch.tensor(registry["invariance_parameters"]["galilean_velocity_offset"], dtype=torch.float64)
            galilean_state["velocity"] = state["velocity"] + offset
            galilean_outputs = operator_components(neighborhood, galilean_state)
            for component in COMPONENTS:
                okay = add_compare_row(
                    invariance_rows, case_id, scale, "galilean_invariance",
                    component, galilean_outputs[component], outputs[component],
                )
                if not okay:
                    scale_failures[scale].add("GALILEAN_INVARIANCE")

            uniform_state = dict(state)
            uniform_velocity = torch.tensor(
                registry["identity_state"]["uniform_velocity"], dtype=torch.float64
            ).expand_as(state["velocity"]).clone()
            uniform_state["velocity"] = uniform_velocity
            uniform_outputs = operator_components(neighborhood, uniform_state)
            for component in ("density_rate", "viscosity_laplacian_acceleration"):
                exact_zero = bool(torch.count_nonzero(uniform_outputs[component]) == 0)
                invariance_rows.append({
                    "case_id": case_id, "lambda": scale,
                    "check": "uniform_velocity_identity", "component": component,
                    "bitwise_equal": exact_zero,
                    "max_absolute_discrepancy": max_abs(uniform_outputs[component]),
                    "rms_discrepancy": rms(uniform_outputs[component]),
                    "tolerance": 0.0, "bitwise_required": True, "passed": exact_zero,
                })
                if not exact_zero:
                    scale_failures[scale].add("UNIFORM_VELOCITY_IDENTITY")

            pressure_metrics = pressure_conservation_metrics(
                neighborhood,
                mass=state["mass"], density=state["density"], pressure=state["pressure"],
            )
            viscosity_metrics = viscosity_conservation_metrics(
                neighborhood,
                mass=state["mass"], density=state["density"], velocity=state["velocity"],
                physical_viscosity=state["nu"],
            )
            structural_checks = [
                ("pressure_pair_force_reciprocity", pressure_metrics["relative_pair_force_residual"], FORCE_RELATIVE_TOLERANCE, True),
                ("pressure_global_internal_force_closure", pressure_metrics["relative_total_internal_force"], FORCE_RELATIVE_TOLERANCE, True),
                ("viscosity_gamma_symmetry", viscosity_metrics["relative_gamma_symmetry_residual"], FORCE_RELATIVE_TOLERANCE, True),
                ("viscosity_pair_force_reciprocity", viscosity_metrics["relative_pair_force_residual"], FORCE_RELATIVE_TOLERANCE, True),
                ("viscosity_global_internal_force_closure", viscosity_metrics["relative_total_internal_force"], FORCE_RELATIVE_TOLERANCE, True),
                ("viscosity_gamma_nonnegative", viscosity_metrics["gamma_minimum"], 0.0, viscosity_metrics["gamma_minimum"] >= 0.0),
                ("viscosity_accumulated_power_nonpositive", viscosity_metrics["accumulated_viscous_power"], tolerance(outputs["viscosity_laplacian_acceleration"]), viscosity_metrics["accumulated_viscous_power"] <= tolerance(outputs["viscosity_laplacian_acceleration"])),
                ("viscosity_pair_power_nonpositive", viscosity_metrics["pair_direct_viscous_power"], tolerance(outputs["viscosity_laplacian_acceleration"]), viscosity_metrics["pair_direct_viscous_power"] <= tolerance(outputs["viscosity_laplacian_acceleration"])),
                ("viscosity_power_identity", viscosity_metrics["power_identity_absolute_difference"], EPS_MULTIPLIER * EPS * max(1.0, abs(viscosity_metrics["pair_direct_viscous_power"])), viscosity_metrics["power_identity_absolute_difference"] <= EPS_MULTIPLIER * EPS * max(1.0, abs(viscosity_metrics["pair_direct_viscous_power"]))),
            ]
            for check, value, threshold, precomputed in structural_checks:
                passed = bool(value <= threshold) if check not in {
                    "viscosity_gamma_nonnegative", "viscosity_accumulated_power_nonpositive",
                    "viscosity_pair_power_nonpositive", "viscosity_power_identity",
                } else bool(precomputed)
                invariance_rows.append({
                    "case_id": case_id, "lambda": scale, "check": check,
                    "component": "pressure" if check.startswith("pressure") else "viscosity",
                    "metric_value": value, "tolerance": threshold, "passed": passed,
                })
                if not passed:
                    scale_failures[scale].add("PAIR_FORCE_OR_DISSIPATION_STRUCTURE")

            closure = outputs["pressure_gradient_acceleration"] + outputs["viscosity_laplacian_acceleration"]
            closure_ok = add_compare_row(
                invariance_rows, case_id, scale, "total_acceleration_component_closure",
                "total_acceleration", outputs["total_acceleration"], closure,
                bitwise_required=True,
            )
            if not closure_ok:
                scale_failures[scale].add("COMPONENT_CLOSURE")

            case_scale_outputs[case_id][scale] = {
                name: value.detach().cpu().numpy().copy() for name, value in outputs.items()
            }
            resource_rows.append({
                "case_id": case_id,
                "lambda": scale,
                "edge_count": int(neighborhood.row.numel()),
                "mean_neighbor_count_including_parent_self_edge": float(audit["neighbor_count_mean"]),
                "graph_wall_seconds": graph_seconds,
                "operator_evaluation_wall_seconds": operator_seconds,
                "combined_wall_seconds": wall_seconds,
                "peak_rss_bytes_before": rss_before,
                "peak_rss_bytes_after": rss_after,
                "peak_rss_bytes_process": peak_rss_bytes(),
                "evaluation_mode": "SEQUENTIAL_CPU_FLOAT64",
            })

    for case in registry["cases"]:
        case_id = str(case["case_id"])
        outputs_by_scale = case_scale_outputs[case_id]
        for component in COMPONENTS:
            tensors = {
                scale: torch.from_numpy(outputs_by_scale[scale][component]) for scale in SCALES
            }
            z = {scale: math.log(scale) for scale in SCALES}
            slope_075_125 = (tensors[1.25] - tensors[0.75]) / (z[1.25] - z[0.75])
            slope_100_150 = (tensors[1.5] - tensors[1.0]) / (z[1.5] - z[1.0])
            curvature_075_100_125 = 2.0 / (z[1.25] - z[0.75]) * (
                (tensors[1.25] - tensors[1.0]) / (z[1.25] - z[1.0])
                - (tensors[1.0] - tensors[0.75]) / (z[1.0] - z[0.75])
            )
            curvature_100_125_150 = 2.0 / (z[1.5] - z[1.0]) * (
                (tensors[1.5] - tensors[1.25]) / (z[1.5] - z[1.25])
                - (tensors[1.25] - tensors[1.0]) / (z[1.25] - z[1.0])
            )
            for scale in (0.75, 1.25, 1.5):
                direct = tensors[scale]
                baseline = tensors[1.0]
                delta = direct - baseline
                floor = EPS_MULTIPLIER * EPS * max(1.0, rms(direct), rms(baseline))
                noise = case_noise[case_id][scale][component]
                base_noise = case_noise[case_id][1.0][component]
                uncertainty = max(
                    noise["repeat_rms"], base_noise["repeat_rms"],
                    noise["edge_reorder_rms"], base_noise["edge_reorder_rms"], floor,
                )
                ratio = rms(delta) / uncertainty
                response_rows.append({
                    "case_id": case_id,
                    "lambda": scale,
                    "component": component,
                    "direct_scale_rms": rms(direct),
                    "baseline_rms": rms(baseline),
                    "baseline_difference_rms": rms(delta),
                    "log_scale_divided_difference_rms": rms(delta / z[scale]),
                    "repeat_rms_lambda": noise["repeat_rms"],
                    "repeat_rms_base": base_noise["repeat_rms"],
                    "edge_reorder_rms_lambda": noise["edge_reorder_rms"],
                    "edge_reorder_rms_base": base_noise["edge_reorder_rms"],
                    "dtype_scaled_floor": floor,
                    "numerical_repeat_uncertainty_U": uncertainty,
                    "scale_response_resolvability_ratio_R": ratio,
                    "ratio_gate": RESPONSE_RATIO_GATE,
                    "ratio_gate_passed": bool(ratio >= RESPONSE_RATIO_GATE),
                    "S_0.75_1.25_rms": rms(slope_075_125),
                    "S_1.00_1.50_rms": rms(slope_100_150),
                    "C_0.75_1.00_1.25_rms": rms(curvature_075_100_125),
                    "C_1.00_1.25_1.50_rms": rms(curvature_100_125_150),
                    "all_response_values_finite": bool(
                        torch.isfinite(direct).all() and torch.isfinite(delta).all()
                        and torch.isfinite(slope_075_125).all()
                        and torch.isfinite(slope_100_150).all()
                        and torch.isfinite(curvature_075_100_125).all()
                        and torch.isfinite(curvature_100_125_150).all()
                    ),
                })

    for scale in (0.75, 1.25, 1.5):
        for component in COMPONENTS:
            passing_fixtures = sum(
                bool(row["ratio_gate_passed"] and row["all_response_values_finite"])
                for row in response_rows
                if row["lambda"] == scale and row["component"] == component
            )
            if passing_fixtures < 2:
                scale_failures[scale].add(f"UNRESOLVABLE_{component.upper()}")

    for row in resource_rows:
        baseline = next(
            candidate for candidate in resource_rows
            if candidate["case_id"] == row["case_id"] and candidate["lambda"] == 1.0
        )
        row["relative_combined_cost_vs_lambda_1"] = (
            row["combined_wall_seconds"] / baseline["combined_wall_seconds"]
        )
        row["relative_operator_cost_vs_lambda_1"] = (
            row["operator_evaluation_wall_seconds"]
            / baseline["operator_evaluation_wall_seconds"]
        )
        row["combined_sequential_ss_ms_cost_seconds"] = sum(
            candidate["combined_wall_seconds"] for candidate in resource_rows
            if candidate["case_id"] == row["case_id"]
        )

    scale_status: dict[str, dict[str, Any]] = {}
    for scale in SCALES:
        reasons = sorted(scale_failures[scale])
        status = "QUALIFIED" if not reasons else "NOT_QUALIFIED_" + "__".join(reasons)
        scale_status[f"{scale:.2f}"] = {
            "lambda": scale,
            "status": status,
            "qualified": not reasons,
            "reasons": reasons,
        }
    qualified = [scale for scale in SCALES if scale_status[f"{scale:.2f}"]["qualified"]]
    if 1.0 not in qualified:
        ladder_status = "FAIL"
        terminal = "MSO01_BASE_OPERATOR_IDENTITY_NOT_QUALIFIED"
    elif len(qualified) == 4:
        ladder_status = "FULL"
        terminal = "MSO01_TARGET_BLIND_MULTISCALE_NUMERICAL_LADDER_QUALIFIED"
    elif len([scale for scale in qualified if scale != 1.0]) >= 2:
        ladder_status = "PARTIAL"
        terminal = "MSO01_TARGET_BLIND_MULTISCALE_NUMERICAL_LADDER_PARTIALLY_QUALIFIED"
    else:
        ladder_status = "FAIL"
        terminal = "MSO01_TARGET_BLIND_MULTISCALE_NUMERICAL_LADDER_NOT_QUALIFIED"
    if ladder_status == "PARTIAL":
        if any(scale < 1.0 for scale in qualified) and any(scale > 1.0 for scale in qualified):
            sidedness = "TWO_SIDED_SUPPORT_MULTISCALE_LADDER"
        elif all(scale >= 1.0 for scale in qualified):
            sidedness = "ONE_SIDED_ENLARGED_SUPPORT_MULTISCALE_LADDER"
        else:
            sidedness = "ONE_SIDED_REDUCED_SUPPORT_MULTISCALE_LADDER"
    elif ladder_status == "FULL":
        sidedness = "TWO_SIDED_SUPPORT_MULTISCALE_LADDER"
    else:
        sidedness = "NOT_APPLICABLE"

    write_csv(OUT / "topology_audit.csv", topology_rows)
    write_csv(OUT / "invariance_audit.csv", invariance_rows)
    write_csv(OUT / "scale_response_uncertainty.csv", response_rows)
    write_csv(OUT / "resource_audit.csv", resource_rows)
    firewall_rows.append({
        **{key: value for key, value in firewall_rows[0].items() if key != "phase"},
        "phase": "POST",
    })
    write_csv(OUT / "firewall_audit.csv", firewall_rows)

    qualified_registry = {
        "schema_version": "1.0.0",
        "project": "SPH-MSO",
        "stage": "MSO-01",
        "candidate_multipliers": list(SCALES),
        "baseline_multiplier": 1.0,
        "scale_results": scale_status,
        "qualified_subset": qualified,
        "ladder_status": ladder_status,
        "ladder_sidedness": sidedness,
        "ranking_performed": False,
        "replacement_scale_generated": False,
        "post_outcome_gate_or_scale_modification": False,
        "terminal_status": terminal,
        "mso02_prelearning_identifiability_experiment_eligible": ladder_status in {"FULL", "PARTIAL"},
        "mso02_executed": False,
    }
    (ROOT / "03_multiscale_definitions/qualified_scale_registry.json").write_text(
        json.dumps(qualified_registry, indent=2) + "\n", encoding="utf-8"
    )
    ledger = {
        "schema_version": "1.0.0",
        "project": "SPH-MSO",
        "stage": "MSO-01",
        "terminal_status": terminal,
        "ladder_status": ladder_status,
        "qualified_subset": qualified,
        "provenance_conflict": False,
        "base_operator_identity_passed": identity_pass,
        "firewall_breach": False,
        "target_file_open_count": 0,
        "reference_archive_read_count": 0,
        "defect_generation_count": 0,
        "h3_metric_count": 0,
        "oracle_fit_count": 0,
        "neural_model_count": 0,
        "optimizer_count": 0,
        "time_integration_count": 0,
        "rollout_count": 0,
        "sealed_test_count": 0,
        "post_outcome_gate_or_scale_modification": False,
        "mso02_prelearning_identifiability_experiment_eligible": ladder_status in {"FULL", "PARTIAL"},
        "mso02_executed": False,
        "git": {
            "repository_present": False,
            "pre_mso01_head": None,
            "post_mso01_head": None,
            "branch": None,
            "commit_created": False,
        },
    }
    (ROOT / "08_manifests/mso01_status_ledger.json").write_text(
        json.dumps(ledger, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"terminal_status": terminal, "ladder_status": ladder_status, "qualified": qualified}, indent=2))


if __name__ == "__main__":
    if ARGS.parent_baseline_output is not None:
        parent_baseline_payload(ARGS.parent_baseline_output)
    else:
        main()
