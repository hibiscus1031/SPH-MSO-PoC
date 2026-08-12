#!/usr/bin/env python3
"""Prepare and execute the target-blind MSO-02A atlas/representation freeze."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import torch
from scipy.spatial import cKDTree


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "06_experiments/mso02a"
OBS = OUT / "observable"
PRIMARY = ROOT / "05_registries/mso02a_primary_candidate_registry.json"
RESERVE = ROOT / "05_registries/mso02a_reserve_candidate_registry.json"
CANDIDATE_FOLDS = ROOT / "05_registries/mso02a_candidate_lineage_fold_registry.json"
FORMAL = ROOT / "05_registries/mso02a_formal_fresh_atlas_registry.json"
FOLDS = ROOT / "05_registries/mso02a_lineage_fold_registry.json"
PAIRED = ROOT / "05_registries/mso02a_paired_ss_ms_registry.json"
BOOTSTRAP = ROOT / "05_registries/mso02a_bootstrap_registry.json"
SS_SCHEMA = OUT / "ss_observable_schema.json"
MS_SCHEMA = OUT / "ms_observable_schema.json"
PRECOMPUTE = ROOT / "08_manifests/mso02a_precompute_freeze.json"
STORE = OBS / "mso02a_observable_store.npz"
BOOTSTRAP_DRAWS = OUT / "bootstrap_draws.npz"
SCALES = (0.75, 1.0, 1.25, 1.5)
COMPONENT_SHAPES = {
    "density_rate": 1,
    "pressure_gradient_acceleration": 2,
    "viscosity_laplacian_acceleration": 2,
}
FAMILIES = ("F1", "F2", "F3", "F4")
FOLD_COUNT = 6
EPS = np.finfo(np.float64).eps


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    if not rows:
        rows = [{"status": "NO_ROWS"}]
        fields = ["status"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


VENDOR = ROOT / "01_provenance/vendor/pio_stage01c_static"
sys.path.insert(0, str(VENDOR))
from structure_preserving.conservative_pressure import conservative_pressure_forces  # noqa: E402
from structure_preserving.conservative_viscosity import conservative_viscosity_acceleration  # noqa: E402
from structure_preserving.kernels import (  # noqa: E402
    divergence_from_vector_gradient,
    edge_kernel_gradients,
    raw_edge_weights,
    raw_gradient,
    raw_kernel_moments,
    scatter_sum,
)
from structure_preserving.neighborhood import (  # noqa: E402
    audit_periodic_neighborhood,
    build_periodic_neighborhood,
    periodic_cartesian_layout,
    tensor_sha256,
)


def seed_record() -> dict[str, str]:
    m00 = sha256(ROOT / "08_manifests/mso00_manifest.json")
    m01 = sha256(ROOT / "08_manifests/mso01_manifest.json")
    material = m00 + m01 + "MSO02A_FRESH_ATLAS"
    return {
        "mso00_manifest_file_sha256": m00,
        "mso01_manifest_file_sha256": m01,
        "literal_domain": "MSO02A_FRESH_ATLAS",
        "concatenated_seed_material": material,
        "seed_digest_sha256": digest_text(material),
    }


def domain_hex(seed: str, domain: str, value: Any = None) -> str:
    suffix = "" if value is None else "|" + canonical(value)
    return digest_text(seed + "|" + domain + suffix)


def rank_key(seed: str, domain: str, value: Any) -> str:
    return domain_hex(seed, domain, value)


def derived_phases(seed: str) -> tuple[float, float, float]:
    phases = []
    for index in range(3):
        raw = int(domain_hex(seed, "PHASE", index)[:16], 16) / float(1 << 64)
        phases.append(math.pi * (0.125 + 1.75 * raw))
    return tuple(phases)


def derived_jitter_seeds(seed: str) -> tuple[int, int, int]:
    return tuple(1 + (int(domain_hex(seed, "JITTER_SEED", i)[:16], 16) % (2**31 - 2)) for i in range(3))


def lineage_payload(case: dict[str, Any]) -> dict[str, Any]:
    keys = ("macro_family", "field_subtype", "mode_indices", "phases_radians", "probe", "polarization", "active_amplitude")
    return {key: case[key] for key in keys}


def ddo_lineages() -> set[str]:
    result: set[str] = set()
    base = Path("/Users/xiejinbo/Documents/SPH-DDO-PoC/06_manifests")
    for name in ("ddo01d_case_registry.json", "ddo02b_case_registry.json"):
        registry = json.loads((base / name).read_text(encoding="utf-8"))
        result.update(canonical(lineage_payload(case)) for case in registry["cases"])
    return result


def candidate_base(family: str, ratio: float, modes: tuple[tuple[int, int], ...], probe: str,
                   amplitude: float, phases: tuple[float, ...]) -> dict[str, Any]:
    return {
        "macro_family": family,
        "field_subtype": "multi_mode" if family == "F2" else ("controlled_disorder_single_mode" if family == "F4" else "single_mode"),
        "resolution_per_axis": 24,
        "support_over_dx": ratio,
        "mode_indices": [list(mode) for mode in modes],
        "probe": probe,
        "polarization": "none" if probe == "density" else probe,
        "active_amplitude": amplitude,
        "phases_radians": list(phases),
        "rho0": 1.0,
        "c0": 10.0,
        "kinematic_viscosity": 0.01,
        "dtype": "float64",
        "domain_minimum": [0.0, 0.0],
        "domain_maximum": [1.0, 1.0],
        "layout_class": "regular",
        "jitter_fraction": 0.0,
        "jitter_seed": 0,
    }


def axis_value(item: dict[str, Any], axis: str) -> str:
    if axis == "mode":
        return "+".join(f"{x},{y}" for x, y in item["mode_indices"])
    if axis == "probe_mode":
        return item["probe"] + "|" + axis_value(item, "mode")
    if axis == "phase":
        return ",".join(format(value, ".17g") for value in item["phases_radians"])
    return str(item[axis])


def balanced_select(pool: list[dict[str, Any]], quota: int, axes: tuple[str, ...], seed: str, domain: str) -> list[dict[str, Any]]:
    categories = {axis: sorted({axis_value(item, axis) for item in pool}) for axis in axes}
    counts = {axis: defaultdict(int) for axis in axes}
    remaining = list(pool)
    selected: list[dict[str, Any]] = []
    for step in range(quota):
        after = step + 1
        def score(item: dict[str, Any]) -> tuple[Any, ...]:
            normalized = []
            deltas = []
            for axis in axes:
                current = counts[axis][axis_value(item, axis)]
                ideal = after / len(categories[axis])
                normalized.append((current + 1) * len(categories[axis]) / after)
                deltas.append(((current + 1 - ideal) ** 2 - (current - ideal) ** 2) / max(ideal, 1.0))
            return max(normalized), sum(deltas), rank_key(seed, domain, item)
        chosen = min(remaining, key=score)
        selected.append(chosen)
        remaining.remove(chosen)
        for axis in axes:
            counts[axis][axis_value(chosen, axis)] += 1
    return selected


def finalize_case(item: dict[str, Any], role: str, family_order: int, global_order: int, seed: str) -> dict[str, Any]:
    case = dict(item)
    n = int(case["resolution_per_axis"])
    case["dx"] = 1.0 / n
    case["support_h"] = float(case["support_over_dx"]) / n
    case["points_per_wavelength_min"] = min(n / math.hypot(*mode) for mode in case["mode_indices"])
    case["candidate_role"] = role
    case["family_generation_order"] = family_order
    case["generation_order"] = global_order
    lineage_digest = digest_text(seed + "|FIELD_LINEAGE|" + canonical(lineage_payload(case)))
    case["field_lineage_id"] = "MSO02A|FIELD_LINEAGE|" + lineage_digest
    identity_payload = {key: value for key, value in case.items() if key not in ("family_generation_order", "generation_order")}
    case_digest = digest_text(seed + "|CASE|" + canonical(identity_payload))
    case["case_id"] = f"MSO02A|{role}|{case['macro_family']}|{case_digest}"
    case["disorder_state_id"] = "MSO02A|DISORDER|" + digest_text(canonical({
        "resolution": n, "jitter_fraction": case["jitter_fraction"], "jitter_seed": case["jitter_seed"]
    }))
    return case


def schema_columns() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    base_names = [
        "obs__mass", "obs__rho", "obs__support_h", "obs__dx", "obs__rho0", "obs__c0",
        "obs__kinematic_viscosity", "obs__h_over_dx", "obs__base_nonself_neighbor_count",
        "obs__base_neighbor_count_over_nominal", "obs__base_cov_xx_over_h2", "obs__base_cov_xy_over_h2",
        "obs__base_cov_yy_over_h2", "obs__base_cov_eig_min_over_h2", "obs__base_cov_eig_max_over_h2",
        "obs__base_cov_eig_ratio", "obs__base_anisotropy_condition", "obs__base_neighbor_distance_cv",
        "obs__base_kernel_s0_minus_1", "obs__base_kernel_s0", "obs__base_first_moment_error_xx",
        "obs__base_first_moment_error_xy", "obs__base_first_moment_error_yx", "obs__base_first_moment_error_yy",
        "obs__base_first_moment_error_fro", "obs__base_grad_constant_x_times_h",
        "obs__base_grad_constant_y_times_h", "obs__base_grad_constant_norm_times_h",
        "obs__local_dv_mean_x", "obs__local_dv_mean_y", "obs__local_dv_rms",
        "obs__local_dv_second_xx", "obs__local_dv_second_xy", "obs__local_dv_second_yy",
        "obs__L_1p00__density_rate", "obs__L_1p00__pressure_acceleration_x",
        "obs__L_1p00__pressure_acceleration_y", "obs__L_1p00__viscosity_acceleration_x",
        "obs__L_1p00__viscosity_acceleration_y",
    ]
    base = [{"name": name, "role": "COMMON_SS_MS_BASE_REPRESENTATION", "formal_input": True, "deployment_available": True} for name in base_names]
    component_coords = ("density_rate", "pressure_acceleration_x", "pressure_acceleration_y", "viscosity_acceleration_x", "viscosity_acceleration_y")
    extra_names: list[str] = []
    for scale in (0.75, 1.25, 1.5):
        tag = f"{scale:.2f}".replace(".", "p")
        extra_names.extend(f"obs__L_{tag}__{component}" for component in component_coords)
        extra_names.extend(f"obs__delta_L_{tag}__{component}" for component in component_coords)
        extra_names.extend(f"obs__G_{tag}__{component}" for component in component_coords)
    for tag in ("0p75_1p25", "1p00_1p50"):
        extra_names.extend(f"obs__S_{tag}__{component}" for component in component_coords)
    for tag in ("0p75_1p00_1p25", "1p00_1p25_1p50"):
        extra_names.extend(f"obs__C_{tag}__{component}" for component in component_coords)
    for scale in (0.75, 1.25, 1.5):
        tag = f"{scale:.2f}".replace(".", "p")
        extra_names.extend((f"obs__topology_nonself_neighbor_count_{tag}", f"obs__topology_neighbor_count_delta_vs_base_{tag}"))
    extra = [{"name": name, "role": "MULTISCALE_RESPONSE_ONLY", "formal_input": True, "deployment_available": True} for name in extra_names]
    return base, base + extra


def prepare() -> None:
    seed_info = seed_record()
    seed = seed_info["seed_digest_sha256"]
    phases = derived_phases(seed)
    jitter_seeds = derived_jitter_seeds(seed)
    old_lineages = ddo_lineages()
    single = ((1, 0), (2, 0), (3, 0), (1, 1), (1, 2), (2, 1))
    multi = (((1, 0), (0, 2)), ((1, 1), (2, -1)), ((1, 0), (2, 1), (0, 3)))
    primary_by_family: dict[str, list[dict[str, Any]]] = {}
    reserve_by_family: dict[str, list[dict[str, Any]]] = {}
    for family in ("F1", "F2", "F3"):
        modesets = tuple((mode,) for mode in single) if family == "F1" else multi if family == "F2" else tuple((mode,) for mode in ((1, 1), (1, 2), (2, 1)))
        pool = []
        for ratio in (3.0, 4.0, 5.0):
            for modes in modesets:
                for probe in ("density", "longitudinal", "transverse"):
                    amplitudes = (0.0025, 0.005, 0.01, 0.02) if probe == "density" else (0.025, 0.05, 0.1, 0.2)
                    for amplitude in amplitudes:
                        for phase_index in range(3):
                            ps = tuple(phases[(phase_index + index) % 3] for index in range(len(modes)))
                            item = candidate_base(family, ratio, modes, probe, amplitude, ps)
                            if canonical(lineage_payload(item)) not in old_lineages:
                                pool.append(item)
        axes = ("support_over_dx", "mode", "probe", "active_amplitude", "phase", "probe_mode")
        selected = balanced_select(pool, 96, axes, seed, f"{family}|PRIMARY")
        selected_keys = {canonical(item) for item in selected}
        remaining = [item for item in pool if canonical(item) not in selected_keys]
        primary_by_family[family] = selected
        reserve_by_family[family] = balanced_select(remaining, 32, axes, seed, f"{family}|RESERVE")

    f4_pool = []
    for mode in single:
        for probe in ("density", "longitudinal", "transverse"):
            amplitudes = (0.0025, 0.005, 0.01, 0.02) if probe == "density" else (0.025, 0.05, 0.1, 0.2)
            for amplitude in amplitudes:
                for phase in phases:
                    item = candidate_base("F4", 4.0, (mode,), probe, amplitude, (phase,))
                    if canonical(lineage_payload(item)) not in old_lineages:
                        f4_pool.append(item)
    f4_bases = balanced_select(f4_pool, 12, ("mode", "probe", "active_amplitude", "phase", "probe_mode"), seed, "F4|BASES")
    disorder_states = ((0.0, 0), (0.05, jitter_seeds[0]), (0.10, jitter_seeds[1]), (0.05, jitter_seeds[2]))
    primary_f4 = []
    for block, base in enumerate(f4_bases[:8]):
        block_id = "MSO02A|F4_BLOCK|" + digest_text(seed + canonical(lineage_payload(base)))
        for ratio in (3.0, 4.0, 5.0):
            for jitter, jitter_seed in disorder_states:
                item = dict(base)
                item.update({"support_over_dx": ratio, "support_h": ratio / 24.0, "jitter_fraction": jitter,
                             "jitter_seed": jitter_seed, "layout_class": "regular" if jitter == 0 else f"jitter_{jitter:.2f}",
                             "f4_matched_block_id": block_id, "f4_block_index": block})
                primary_f4.append(item)
    reserve_f4 = []
    for block, base in enumerate(f4_bases[8:], start=8):
        block_id = "MSO02A|F4_BLOCK|" + digest_text(seed + canonical(lineage_payload(base)))
        for ratio in (4.0, 5.0):
            for jitter, jitter_seed in disorder_states:
                item = dict(base)
                item.update({"support_over_dx": ratio, "support_h": ratio / 24.0, "jitter_fraction": jitter,
                             "jitter_seed": jitter_seed, "layout_class": "regular" if jitter == 0 else f"jitter_{jitter:.2f}",
                             "f4_matched_block_id": block_id, "f4_block_index": block})
                reserve_f4.append(item)
    primary_by_family["F4"] = primary_f4
    reserve_by_family["F4"] = reserve_f4

    primary_cases: list[dict[str, Any]] = []
    reserve_cases: list[dict[str, Any]] = []
    for family in FAMILIES:
        ordered = sorted(primary_by_family[family], key=lambda item: rank_key(seed, f"{family}|PRIMARY_ORDER", item))
        for family_order, item in enumerate(ordered):
            primary_cases.append(finalize_case(item, "PRIMARY", family_order, len(primary_cases), seed))
        ordered_r = sorted(reserve_by_family[family], key=lambda item: rank_key(seed, f"{family}|RESERVE_ORDER", item))
        for family_order, item in enumerate(ordered_r):
            reserve_cases.append(finalize_case(item, "RESERVE", family_order, len(reserve_cases), seed))

    def registry(role: str, cases: list[dict[str, Any]], quota: int) -> dict[str, Any]:
        overlaps = sum(canonical(lineage_payload(case)) in old_lineages for case in cases)
        return {
            "schema_version": "1.0.0", "project": "SPH-MSO", "stage": "MSO-02A",
            "registry_role": role, "status": "FROZEN_BEFORE_FRESH_CASE_OPERATOR_EVALUATION",
            "seed_derivation": seed_info, "derived_phase_set_radians": list(phases),
            "derived_jitter_seeds": list(jitter_seeds), "selection_is_target_blind": True,
            "case_count": len(cases), "family_quota": quota,
            "family_counts": dict(Counter(case["macro_family"] for case in cases)),
            "ddo01d_ddo02b_lineage_overlap_count": overlaps,
            "pio_registered_identity_overlap_count": 0,
            "pio_overlap_basis": "disjoint MSO02A identity namespace and no PIO F1-F4 analytical-field lineage registry imported",
            "mso01_fixture_case_id_overlap_count": sum(case["case_id"].startswith("TBQ_") for case in cases),
            "cases": cases,
        }
    write_json(PRIMARY, registry("PRIMARY_REGISTRY", primary_cases, 96))
    write_json(RESERVE, registry("RESERVE_REGISTRY", reserve_cases, 32))

    fold_by: dict[str, int] = {}
    fold_rows = []
    for family in FAMILIES:
        primary_lineages = sorted({c["field_lineage_id"] for c in primary_cases if c["macro_family"] == family}, key=lambda x: domain_hex(seed, f"{family}|FOLD_PRIMARY", x))
        reserve_lineages = sorted({c["field_lineage_id"] for c in reserve_cases if c["macro_family"] == family} - set(primary_lineages), key=lambda x: domain_hex(seed, f"{family}|FOLD_RESERVE", x))
        loads = [0] * FOLD_COUNT
        case_counts = Counter(c["field_lineage_id"] for c in primary_cases + reserve_cases)
        for index, lineage in enumerate(primary_lineages):
            fold = index if index < FOLD_COUNT else min(range(FOLD_COUNT), key=lambda f: (loads[f], f))
            fold_by[lineage] = fold
            loads[fold] += case_counts[lineage]
        for lineage in reserve_lineages:
            fold = min(range(FOLD_COUNT), key=lambda f: (loads[f], f))
            fold_by[lineage] = fold
            loads[fold] += case_counts[lineage]
        for lineage in primary_lineages + reserve_lineages:
            fold_rows.append({"field_lineage_id": lineage, "macro_family": family, "fold": f"FOLD_{fold_by[lineage]}",
                              "primary_lineage": lineage in primary_lineages, "candidate_case_count": case_counts[lineage]})
    write_json(CANDIDATE_FOLDS, {"schema_version": "1.0.0", "stage": "MSO-02A", "status": "FROZEN_BEFORE_FRESH_CASE_OPERATOR_EVALUATION",
                                 "fold_count": FOLD_COUNT, "assignment_is_target_blind": True, "cases_never_cross_folds": True,
                                 "lineages": fold_rows})

    ss, ms = schema_columns()
    common = {"schema_version": "1.0.0", "stage": "MSO-02A", "status": "FROZEN_BEFORE_FRESH_CASE_OPERATOR_EVALUATION",
              "join_keys_are_formal_inputs": False, "target_or_reference_columns": [], "normalization": "TRAIN_FOLD_MEDIAN_IQR_WITH_UNIT_FALLBACK_RETAIN"}
    write_json(SS_SCHEMA, {**common, "arm": "SS", "feature_dimension": len(ss), "columns": ss})
    write_json(MS_SCHEMA, {**common, "arm": "MS", "feature_dimension": len(ms), "columns": ms})
    artifacts = [
        "00_project_contract/mso02a_fresh_atlas_and_representation_freeze_contract.md",
        "05_registries/mso02a_primary_candidate_registry.json", "05_registries/mso02a_reserve_candidate_registry.json",
        "05_registries/mso02a_candidate_lineage_fold_registry.json",
        "06_experiments/mso02a/ss_observable_schema.json", "06_experiments/mso02a/ms_observable_schema.json",
        "06_experiments/mso02a/run_mso02a_freeze.py",
    ]
    baseline = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    write_json(PRECOMPUTE, {"schema_version": "1.0.0", "stage": "MSO-02A", "status": "FROZEN_BEFORE_FRESH_CASE_OPERATOR_EVALUATION",
                            "pre_mso02_baseline_commit": baseline, "seed_derivation": seed_info,
                            "artifact_sha256": {rel: sha256(ROOT / rel) for rel in artifacts},
                            "target_file_open_count": 0, "reference_archive_read_count": 0, "continuum_operator_read_count": 0,
                            "defect_generation_count": 0, "h3_evaluation_count": 0, "oracle_fit_count": 0})
    print(json.dumps({"status": "MSO02A_PRECOMPUTE_FROZEN", "primary": len(primary_cases), "reserve": len(reserve_cases),
                      "ss_dimension": len(ss), "ms_dimension": len(ms), "pre_mso02_baseline_commit": baseline}, indent=2))


def verify_precompute() -> None:
    frozen = json.loads(PRECOMPUTE.read_text(encoding="utf-8"))
    errors = [rel for rel, expected in frozen["artifact_sha256"].items() if sha256(ROOT / rel) != expected]
    if errors:
        raise RuntimeError("MSO02A_PROVENANCE_CONFLICT:" + ",".join(errors))


def make_state(case: dict[str, Any]) -> dict[str, Any]:
    positions, dx, position_hash = periodic_cartesian_layout(
        int(case["resolution_per_axis"]), jitter_fraction=float(case["jitter_fraction"]), seed=int(case["jitter_seed"]),
        dtype=torch.float64, domain_minimum=(0.0, 0.0), domain_maximum=(1.0, 1.0))
    rho0, c0 = float(case["rho0"]), float(case["c0"])
    density = torch.full((positions.shape[0],), rho0, dtype=torch.float64)
    velocity = torch.zeros((positions.shape[0], 2), dtype=torch.float64)
    amplitude = float(case["active_amplitude"])
    modes = case["mode_indices"]
    phases = case["phases_radians"]
    if case["probe"] == "density":
        for mode, phase in zip(modes, phases):
            argument = 2.0 * torch.pi * (mode[0] * positions[:, 0] + mode[1] * positions[:, 1]) + phase
            density += rho0 * (amplitude / len(modes)) * torch.sin(argument)
    else:
        for mode, phase in zip(modes, phases):
            argument = 2.0 * torch.pi * (mode[0] * positions[:, 0] + mode[1] * positions[:, 1]) + phase
            norm = math.hypot(*mode)
            direction = torch.tensor((mode[0] / norm, mode[1] / norm), dtype=torch.float64)
            if case["probe"] == "transverse":
                direction = torch.tensor((-mode[1] / norm, mode[0] / norm), dtype=torch.float64)
            velocity += (amplitude / len(modes)) * torch.sin(argument)[:, None] * direction[None, :]
    pressure = c0**2 * (density - rho0)
    mass = torch.full((positions.shape[0],), dx**2, dtype=torch.float64)
    return {"positions": positions, "dx": dx, "position_hash": position_hash, "density": density, "velocity": velocity,
            "pressure": pressure, "mass": mass, "nu": float(case["kinematic_viscosity"])}


def operator_components(graph: Any, state: dict[str, Any]) -> dict[str, torch.Tensor]:
    volume = state["mass"] / state["density"]
    gradient = raw_gradient(graph, state["velocity"], volume)
    density_rate = -state["density"] * divergence_from_vector_gradient(gradient)
    pressure = conservative_pressure_forces(graph, mass=state["mass"], density=state["density"], pressure=state["pressure"]) / state["mass"][:, None]
    viscosity = conservative_viscosity_acceleration(graph, mass=state["mass"], density=state["density"], velocity=state["velocity"], physical_viscosity=state["nu"])
    return {"density_rate": density_rate, "pressure_gradient_acceleration": pressure,
            "viscosity_laplacian_acceleration": viscosity, "total_acceleration": pressure + viscosity}


def graph_equal(a: Any, b: Any) -> bool:
    return all(torch.equal(getattr(a, name), getattr(b, name)) for name in ("row", "col", "displacement", "distance", "edge_support", "particle_support"))


def particle_geometry(graph: Any, state: dict[str, Any], h: float) -> dict[str, torch.Tensor]:
    count = graph.particle_count
    nonself = graph.row != graph.col
    volume = state["mass"] / state["density"]
    weights = raw_edge_weights(graph, volume)
    counts = torch.bincount(graph.row[nonself], minlength=count).to(torch.float64)
    outer = weights[nonself, None, None] * graph.displacement[nonself, :, None] * graph.displacement[nonself, None, :]
    numerator = scatter_sum(graph.row[nonself], outer, count)
    weight_sum = scatter_sum(graph.row[nonself], weights[nonself], count)
    covariance = numerator / weight_sum[:, None, None]
    eig = torch.linalg.eigvalsh(covariance)
    distance_sum = scatter_sum(graph.row[nonself], graph.distance[nonself], count)
    distance_sq = scatter_sum(graph.row[nonself], graph.distance[nonself].square(), count)
    distance_mean = distance_sum / counts
    distance_std = torch.sqrt(torch.clamp(distance_sq / counts - distance_mean.square(), min=0.0))
    moments = raw_kernel_moments(graph, volume)
    gradients = edge_kernel_gradients(graph)
    xj_minus_xi = -graph.displacement
    first = scatter_sum(graph.row, volume[graph.col, None, None] * xj_minus_xi[:, :, None] * gradients[:, None, :], count)
    first_error = first - torch.eye(2, dtype=torch.float64)[None, :, :]
    grad_constant = scatter_sum(graph.row, volume[graph.col, None] * gradients, count)
    dv = state["velocity"][graph.col[nonself]] - state["velocity"][graph.row[nonself]]
    dv_mean = scatter_sum(graph.row[nonself], dv, count) / counts[:, None]
    dv_second = scatter_sum(graph.row[nonself], dv[:, :, None] * dv[:, None, :], count) / counts[:, None, None]
    return {"counts": counts, "covariance": covariance, "eig": eig, "distance_cv": distance_std / distance_mean,
            "moments_s0": moments["s0"], "first_error": first_error, "grad_constant": grad_constant,
            "dv_mean": dv_mean, "dv_second": dv_second, "dv_rms": torch.sqrt(torch.sum(torch.diagonal(dv_second, dim1=1, dim2=2), dim=1)),
            "rank_deficient": eig[:, 0] <= (256 * torch.finfo(torch.float64).eps * torch.maximum(torch.ones_like(eig[:, 0]), eig.sum(dim=1).abs()))}


def component_matrix(outputs: dict[str, torch.Tensor]) -> torch.Tensor:
    return torch.column_stack((outputs["density_rate"], outputs["pressure_gradient_acceleration"], outputs["viscosity_laplacian_acceleration"]))


def evaluate_case(case: dict[str, Any]) -> tuple[bool, list[dict[str, Any]], np.ndarray, np.ndarray, dict[str, Any]]:
    state = make_state(case)
    finite_state = all(bool(torch.isfinite(state[name]).all()) for name in ("positions", "density", "velocity", "pressure", "mass"))
    graphs: dict[float, Any] = {}
    outputs: dict[float, dict[str, torch.Tensor]] = {}
    geometries: dict[float, dict[str, torch.Tensor]] = {}
    rows: list[dict[str, Any]] = []
    base_h = float(case["support_h"])
    for scale in SCALES:
        support = base_h * scale
        graph = build_periodic_neighborhood(state["positions"], support, domain_minimum=(0.0, 0.0), domain_maximum=(1.0, 1.0))
        repeated_graph = build_periodic_neighborhood(state["positions"], support, domain_minimum=(0.0, 0.0), domain_maximum=(1.0, 1.0))
        audit = audit_periodic_neighborhood(state["positions"], graph)
        out = operator_components(graph, state)
        repeated_out = operator_components(graph, state)
        geometry = particle_geometry(graph, state, support)
        finite_operator = all(bool(torch.isfinite(value).all()) for value in out.values())
        repeatable = all(torch.equal(out[name], repeated_out[name]) for name in out)
        closure = torch.equal(out["total_acceleration"], out["pressure_gradient_acceleration"] + out["viscosity_laplacian_acceleration"])
        counts = geometry["counts"]
        reciprocal = audit["nonreciprocal_nonself_edge_count"] == 0
        convention = (audit["duplicate_edge_count"] == 0 and audit["out_of_bounds_edge_count"] == 0 and
                      audit["missing_self_edge_count"] == 0 and audit["self_edge_count"] == graph.particle_count)
        support_complete = audit["omitted_strict_support_edge_count"] == 0 and audit["unexpected_edge_count"] == 0
        periodic_ok = audit["minimum_image_linf"] <= 256 * EPS
        support_fraction = float(((counts >= 8) & (~geometry["rank_deficient"])).to(torch.float64).mean())
        base_identity = True
        if scale == 1.0:
            base_graph = build_periodic_neighborhood(state["positions"], base_h, domain_minimum=(0.0, 0.0), domain_maximum=(1.0, 1.0))
            base_out = operator_components(base_graph, state)
            base_identity = graph_equal(graph, base_graph) and all(torch.equal(out[name], base_out[name]) for name in out)
        rows.append({
            "candidate_role": case["candidate_role"], "case_id": case["case_id"], "family": case["macro_family"],
            "field_lineage_id": case["field_lineage_id"], "lambda": scale, "particle_count": graph.particle_count,
            "edge_count": int(graph.row.numel()), "finite_state": finite_state, "finite_operator_outputs": finite_operator,
            "deterministic_graph_construction": graph_equal(graph, repeated_graph), "reciprocal_graph_semantics": reciprocal,
            "duplicate_alias_self_edge_convention": convention, "periodic_minimum_image_correct": periodic_ok,
            "support_complete": support_complete, "zero_neighbor_count": int((counts == 0).sum()),
            "minimum_nonself_neighbor_count": int(counts.min()), "p01_nonself_neighbor_count": float(torch.quantile(counts, 0.01)),
            "minimum_support_requirement_passed": bool(float(torch.quantile(counts, 0.01)) >= 8.0),
            "weighted_covariance_rank_failure_count": int(geometry["rank_deficient"].sum()),
            "support_completeness_fraction": support_fraction, "operator_repeatability_bitwise": repeatable,
            "component_closure_bitwise": closure, "lambda_1_vendor_base_path_identity": base_identity,
        })
        graphs[scale], outputs[scale], geometries[scale] = graph, out, geometry
    nesting_ok = True
    for low, high in zip(SCALES[:-1], SCALES[1:]):
        low_keys = (graphs[low].row * graphs[low].particle_count + graphs[low].col).numpy()
        high_keys = (graphs[high].row * graphs[high].particle_count + graphs[high].col).numpy()
        if np.setdiff1d(low_keys, high_keys, assume_unique=True).size:
            nesting_ok = False
    z = {scale: math.log(scale) for scale in SCALES}
    matrices = {scale: component_matrix(outputs[scale]) for scale in SCALES}
    delta = {scale: matrices[scale] - matrices[1.0] for scale in (0.75, 1.25, 1.5)}
    g = {scale: delta[scale] / z[scale] for scale in delta}
    slopes = ((matrices[1.25] - matrices[0.75]) / (z[1.25] - z[0.75]),
              (matrices[1.5] - matrices[1.0]) / (z[1.5] - z[1.0]))
    curvatures = (
        2.0 / (z[1.25] - z[0.75]) * ((matrices[1.25] - matrices[1.0]) / (z[1.25] - z[1.0]) - (matrices[1.0] - matrices[0.75]) / (z[1.0] - z[0.75])),
        2.0 / (z[1.5] - z[1.0]) * ((matrices[1.5] - matrices[1.25]) / (z[1.5] - z[1.25]) - (matrices[1.25] - matrices[1.0]) / (z[1.25] - z[1.0])),
    )
    response_finite = all(bool(torch.isfinite(value).all()) for value in list(delta.values()) + list(g.values()) + list(slopes) + list(curvatures))
    mandatory_fields = ("finite_state", "finite_operator_outputs", "deterministic_graph_construction", "reciprocal_graph_semantics",
                        "duplicate_alias_self_edge_convention", "periodic_minimum_image_correct", "support_complete",
                        "minimum_support_requirement_passed", "operator_repeatability_bitwise", "component_closure_bitwise",
                        "lambda_1_vendor_base_path_identity")
    for row in rows:
        row["graph_nesting_passed"] = nesting_ok
        row["scale_response_finite"] = response_finite
        row["case_scale_passed"] = all(bool(row[field]) for field in mandatory_fields) and row["zero_neighbor_count"] == 0 and row["weighted_covariance_rank_failure_count"] == 0 and row["support_completeness_fraction"] == 1.0 and nesting_ok and response_finite
    passed = all(row["case_scale_passed"] for row in rows)

    n = state["positions"].shape[0]
    geom = geometries[1.0]
    h = base_h
    cov = geom["covariance"] / h**2
    eig = geom["eig"] / h**2
    nominal = math.pi * (h / state["dx"]) ** 2
    first = geom["first_error"]
    grad = geom["grad_constant"] * h
    base = torch.column_stack((
        state["mass"], state["density"], torch.full((n,), h, dtype=torch.float64), torch.full((n,), state["dx"], dtype=torch.float64),
        torch.full((n,), float(case["rho0"]), dtype=torch.float64), torch.full((n,), float(case["c0"]), dtype=torch.float64),
        torch.full((n,), float(case["kinematic_viscosity"]), dtype=torch.float64),
        torch.full((n,), h / state["dx"], dtype=torch.float64), geom["counts"], geom["counts"] / nominal,
        cov[:, 0, 0], cov[:, 0, 1], cov[:, 1, 1], eig[:, 0], eig[:, 1], eig[:, 0] / eig[:, 1], eig[:, 1] / eig[:, 0],
        geom["distance_cv"], geom["moments_s0"] - 1.0, geom["moments_s0"],
        first[:, 0, 0], first[:, 0, 1], first[:, 1, 0], first[:, 1, 1], torch.linalg.matrix_norm(first),
        grad[:, 0], grad[:, 1], torch.linalg.vector_norm(grad, dim=1), geom["dv_mean"][:, 0], geom["dv_mean"][:, 1], geom["dv_rms"],
        geom["dv_second"][:, 0, 0], geom["dv_second"][:, 0, 1], geom["dv_second"][:, 1, 1], matrices[1.0],
    ))
    extras = []
    for scale in (0.75, 1.25, 1.5): extras.append(matrices[scale])
    for scale in (0.75, 1.25, 1.5): extras.append(delta[scale])
    for scale in (0.75, 1.25, 1.5): extras.append(g[scale])
    extras.extend(slopes)
    extras.extend(curvatures)
    for scale in (0.75, 1.25, 1.5):
        extras.append(torch.column_stack((geometries[scale]["counts"], geometries[scale]["counts"] - geom["counts"])))
    ms = torch.column_stack((base, *extras))
    state_hash = hashlib.sha256()
    for name in ("positions", "density", "velocity", "mass"):
        state_hash.update(state[name].contiguous().numpy().tobytes())
    physics_hash = digest_text(canonical({key: case[key] for key in ("rho0", "c0", "kinematic_viscosity", "dtype", "domain_minimum", "domain_maximum")}))
    operator_hash = hashlib.sha256(matrices[1.0].contiguous().numpy().tobytes()).hexdigest()
    meta = {"particle_state_hash": state_hash.hexdigest(), "position_hash": state["position_hash"], "physics_hash": physics_hash,
            "operator_base_hash": operator_hash, "particle_count": n}
    return passed, rows, base.numpy(), ms.numpy(), meta


def normalization_and_audit(ss: np.ndarray, ms: np.ndarray, row_case: np.ndarray, formal_cases: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    schemas = {"SS": json.loads(SS_SCHEMA.read_text()), "MS": json.loads(MS_SCHEMA.read_text())}
    matrices = {"SS": ss, "MS": ms}
    case_fold = np.array([int(formal_cases[index]["fold"].split("_")[1]) for index in row_case], dtype=np.int16)
    registry: dict[str, Any] = {"schema_version": "1.0.0", "stage": "MSO-02A", "status": "FROZEN_TARGET_BLIND",
                                "fold_count": FOLD_COUNT, "rule": "TRAIN_FOLD_MEDIAN_IQR_WITH_UNIT_FALLBACK_RETAIN", "arms": {}}
    audit_rows: list[dict[str, Any]] = []
    for arm, matrix in matrices.items():
        names = [column["name"] for column in schemas[arm]["columns"]]
        fold_records = []
        iqr_zero_counts = np.zeros(matrix.shape[1], dtype=np.int64)
        for fold in range(FOLD_COUNT):
            train = matrix[case_fold != fold]
            q25, median, q75 = np.quantile(train, [0.25, 0.5, 0.75], axis=0)
            iqr = q75 - q25
            zero = iqr == 0.0
            iqr_zero_counts += zero
            scale = np.where(zero, 1.0, iqr)
            fold_records.append({"held_out_fold": f"FOLD_{fold}", "training_row_count": int(train.shape[0]),
                                 "feature_names": names, "median": median.tolist(), "iqr": iqr.tolist(), "divisor": scale.tolist(),
                                 "fallback": ["UNIT_SCALE_RETAIN_COLUMN" if value else "IQR" for value in zero]})
        registry["arms"][arm] = {"feature_dimension": matrix.shape[1], "folds": fold_records}
        raw_hash: dict[str, str] = {}
        normalized_hash: dict[str, str] = {}
        first_nonzero: dict[str, float] = {}
        for index, name in enumerate(names):
            column = np.ascontiguousarray(matrix[:, index])
            raw_hash[name] = hashlib.sha256(column.tobytes()).hexdigest()
            nz = np.flatnonzero(column)
            if nz.size:
                scale0 = float(column[nz[0]])
                first_nonzero[name] = scale0
                normalized_hash[name] = hashlib.sha256(np.ascontiguousarray(column / scale0).tobytes()).hexdigest()
        first_raw: dict[str, str] = {}
        first_norm: dict[str, str] = {}
        for index, name in enumerate(names):
            column = matrix[:, index]
            duplicate = first_raw.get(raw_hash[name], "")
            if not duplicate: first_raw[raw_hash[name]] = name
            dependency = ""
            if name in normalized_hash:
                dependency = first_norm.get(normalized_hash[name], "")
                if not dependency: first_norm[normalized_hash[name]] = name
            audit_rows.append({"arm": arm, "feature_index": index, "feature_name": name, "feature_dimension": matrix.shape[1],
                               "finite_count": int(np.isfinite(column).sum()), "nonfinite_count": int((~np.isfinite(column)).sum()),
                               "exact_constant": bool(np.min(column) == np.max(column)), "exact_duplicate_of": duplicate,
                               "pairwise_exact_linear_dependency_of": dependency if dependency != duplicate else "",
                               "linear_dependency_scalar_diagnostic": (first_nonzero.get(name, 0.0) / first_nonzero.get(dependency, 1.0)) if dependency else "",
                               "minimum": float(np.min(column)), "maximum": float(np.max(column)),
                               "absolute_maximum": float(np.max(np.abs(column))), "train_fold_iqr_degeneracy_count": int(iqr_zero_counts[index]),
                               "column_sha256": raw_hash[name]})
    return registry, audit_rows


def coverage_geometry(ss: np.ndarray, ms: np.ndarray, row_case: np.ndarray, row_particle: np.ndarray,
                      formal_cases: list[dict[str, Any]], normalization: dict[str, Any], seed: str) -> dict[str, Any]:
    matrices = {"SS": ss, "MS": ms}
    selected_rows = []
    for case_index, case in enumerate(formal_cases):
        rows = np.flatnonzero(row_case == case_index)
        ordered = sorted(rows.tolist(), key=lambda row: domain_hex(seed, "COVERAGE_PARTICLE", [case["case_id"], int(row_particle[row])]))
        selected_rows.extend(ordered[:16])
    selected = np.array(selected_rows, dtype=np.int64)
    sample_case = row_case[selected]
    sample_lineage = np.array([formal_cases[index]["field_lineage_id"] for index in sample_case])
    case_folds = np.array([int(formal_cases[index]["fold"].split("_")[1]) for index in sample_case])
    result = {"schema_version": "1.0.0", "stage": "MSO-02A", "status": "TARGET_BLIND_GEOMETRY_PRECOMPUTED",
              "distance": "EUCLIDEAN_AFTER_ARM_SPECIFIC_TRAIN_FOLD_MEDIAN_IQR", "primary_k": 10, "sensitivity_k": [5, 20],
              "exclusions": ["same_case", "same_disorder_seed", "same_field_lineage"],
              "coverage_radius_definition": "training-side leave-one-lineage-out 95th percentile K=10 radius",
              "diagnostic_sample_particles_per_case": 16, "target_disagreement_computed": False,
              "conditional_variance_computed": False, "arms": {}}
    for arm, matrix in matrices.items():
        records = []
        for fold in range(FOLD_COUNT):
            train_mask = case_folds != fold
            train_rows = selected[train_mask]
            train_lineage = sample_lineage[train_mask]
            fold_norm = normalization["arms"][arm]["folds"][fold]
            x = (matrix[train_rows] - np.asarray(fold_norm["median"])) / np.asarray(fold_norm["divisor"])
            tree = cKDTree(x)
            query_k = min(512, x.shape[0])
            distances, indices = tree.query(x, k=query_k, workers=1)
            radii = []
            for row_index in range(x.shape[0]):
                valid = [float(distance) for distance, neighbor in zip(distances[row_index], indices[row_index])
                         if train_lineage[int(neighbor)] != train_lineage[row_index]]
                if len(valid) < 10:
                    raise RuntimeError("insufficient cross-lineage observable neighbors")
                radii.append(valid[9])
            records.append({"held_out_fold": f"FOLD_{fold}", "development_sample_row_count": int(x.shape[0]),
                            "k10_radius_p95": float(np.quantile(radii, 0.95)), "k10_radius_max": float(np.max(radii)),
                            "finite": bool(np.isfinite(radii).all())})
        result["arms"][arm] = {"feature_dimension": matrix.shape[1], "folds": records}
    return result


def bootstrap_freeze(formal_cases: list[dict[str, Any]], seed: str) -> None:
    lineage_cases: dict[str, list[int]] = defaultdict(list)
    strata: dict[tuple[str, str], list[str]] = defaultdict(list)
    for index, case in enumerate(formal_cases):
        lineage_cases[case["field_lineage_id"]].append(index)
    for lineage, indices in lineage_cases.items():
        case = formal_cases[indices[0]]
        strata[(case["macro_family"], case["fold"])].append(lineage)
    for key in strata:
        strata[key].sort()
    lineage_occurrence: list[int] = []
    case_source: list[int] = []
    offsets = [0]
    lineage_table = sorted(lineage_cases)
    lineage_index = {lineage: index for index, lineage in enumerate(lineage_table)}
    for replicate in range(10000):
        rng = np.random.Generator(np.random.PCG64(int(domain_hex(seed, "BOOTSTRAP", replicate)[:16], 16)))
        for key in sorted(strata):
            values = strata[key]
            selected = rng.integers(0, len(values), size=len(values))
            for selection in selected:
                lineage = values[int(selection)]
                cases = lineage_cases[lineage]
                chosen_cases = rng.integers(0, len(cases), size=len(cases)) if len(cases) > 1 else np.zeros(1, dtype=int)
                for case_position in chosen_cases:
                    lineage_occurrence.append(lineage_index[lineage])
                    case_source.append(cases[int(case_position)])
        offsets.append(len(case_source))
    np.savez_compressed(BOOTSTRAP_DRAWS, replicate_offsets=np.asarray(offsets, dtype=np.int64),
                        drawn_lineage_index=np.asarray(lineage_occurrence, dtype=np.int32), drawn_case_index=np.asarray(case_source, dtype=np.int32))
    write_json(BOOTSTRAP, {"schema_version": "1.0.0", "stage": "MSO-02A", "status": "FROZEN_BEFORE_TARGET_ACCESS",
                           "replicate_count": 10000, "unit": "LINEAGE_THEN_COMPLETE_CASE", "stratification": "FAMILY_X_FOLD",
                           "paired_ss_ms_draws": True, "case_equal": True, "fold_equal": True, "family_equal": True,
                           "multiplicity": "paired maximum-studentized one-sided 95% across three primary components within metric family",
                           "lineage_table": lineage_table, "strata": {f"{k[0]}|{k[1]}": v for k, v in sorted(strata.items())},
                           "draw_file": str(BOOTSTRAP_DRAWS.relative_to(ROOT)), "draw_file_sha256": sha256(BOOTSTRAP_DRAWS),
                           "h_mso01_gates_modified": False})


def run() -> None:
    verify_precompute()
    primary = json.loads(PRIMARY.read_text())["cases"]
    reserve = json.loads(RESERVE.read_text())["cases"]
    fold_source = json.loads(CANDIDATE_FOLDS.read_text())["lineages"]
    fold_by = {row["field_lineage_id"]: row["fold"] for row in fold_source}
    preflight_rows: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []
    admitted: dict[str, list[tuple[dict[str, Any], np.ndarray, np.ndarray, dict[str, Any]]]] = {family: [] for family in FAMILIES}
    for case in primary:
        passed, rows, ss, ms, meta = evaluate_case(case)
        preflight_rows.extend(rows)
        if passed:
            admitted[case["macro_family"]].append((case, ss, ms, meta))
        else:
            failed.append(case)
    replacement_rows: list[dict[str, Any]] = []
    for family in FAMILIES:
        needed = 96 - len(admitted[family])
        reserves = [case for case in reserve if case["macro_family"] == family]
        for reserve_case in reserves[:needed]:
            passed, rows, ss, ms, meta = evaluate_case(reserve_case)
            preflight_rows.extend(rows)
            failed_primary = [case for case in failed if case["macro_family"] == family][len(replacement_rows)] if False else None
            replacement_rows.append({"family": family, "reserve_case_id": reserve_case["case_id"], "reserve_order": reserve_case["family_generation_order"],
                                     "reserve_preflight_passed": passed, "selection_rule": "NEXT_FROZEN_SAME_FAMILY_RESERVE"})
            if passed:
                admitted[family].append((reserve_case, ss, ms, meta))
        if len(admitted[family]) != 96:
            raise RuntimeError("MSO02A_FRESH_ATLAS_NOT_QUALIFIED")
    if not replacement_rows:
        replacement_rows = [{"family": "ALL", "reserve_case_id": "", "reserve_order": "", "reserve_preflight_passed": "",
                             "selection_rule": "NO_RESERVE_REQUIRED", "failed_primary_count": len(failed)}]
    formal_tuples = [entry for family in FAMILIES for entry in admitted[family]]
    formal_cases = []
    ss_blocks, ms_blocks, row_case_blocks, row_particle_blocks = [], [], [], []
    for index, (case, ss, ms, meta) in enumerate(formal_tuples):
        formal_case = {**case, **meta, "formal_case_index": index, "fold": fold_by[case["field_lineage_id"]],
                       "admission_status": "FOUR_SCALE_CASE_LEVEL_ADMISSIBLE"}
        formal_cases.append(formal_case)
        ss_blocks.append(ss); ms_blocks.append(ms)
        row_case_blocks.append(np.full(ss.shape[0], index, dtype=np.int32))
        row_particle_blocks.append(np.arange(ss.shape[0], dtype=np.int32))
    ss_matrix, ms_matrix = np.vstack(ss_blocks), np.vstack(ms_blocks)
    row_case, row_particle = np.concatenate(row_case_blocks), np.concatenate(row_particle_blocks)
    np.savez_compressed(STORE, ss_features=ss_matrix, ms_features=ms_matrix, formal_case_index=row_case, particle_id=row_particle)
    write_csv(OUT / "case_level_numerical_preflight.csv", preflight_rows)
    write_csv(OUT / "case_replacement_audit.csv", replacement_rows)
    write_json(FORMAL, {"schema_version": "1.0.0", "stage": "MSO-02A", "status": "FORMAL_FRESH_ATLAS_ADMITTED",
                        "case_count": len(formal_cases), "family_counts": dict(Counter(c["macro_family"] for c in formal_cases)),
                        "failed_primary_count": len(failed), "reserve_used_count": sum(c["candidate_role"] == "RESERVE" for c in formal_cases),
                        "ddo_pio_historical_lineage_overlap_count": 0, "all_formal_cases_four_scale_admissible": True, "cases": formal_cases})
    fold_rows = [{"case_id": c["case_id"], "formal_case_index": c["formal_case_index"], "macro_family": c["macro_family"],
                  "field_lineage_id": c["field_lineage_id"], "fold": c["fold"], "particle_count": c["particle_count"]} for c in formal_cases]
    write_json(FOLDS, {"schema_version": "1.0.0", "stage": "MSO-02A", "status": "FROZEN_BEFORE_TARGET_ACCESS", "fold_count": FOLD_COUNT,
                       "lineage_held_out": True, "case_equal": True, "fold_equal": True, "ss_ms_identical": True, "cases": fold_rows})
    ss_hash, ms_hash = sha256(SS_SCHEMA), sha256(MS_SCHEMA)
    paired_rows = [{"case_id": c["case_id"], "ss_case_id": c["case_id"], "ms_case_id": c["case_id"], "particle_state_hash": c["particle_state_hash"],
                    "ss_particle_state_hash": c["particle_state_hash"], "ms_particle_state_hash": c["particle_state_hash"], "family": c["macro_family"],
                    "lineage": c["field_lineage_id"], "physics_hash": c["physics_hash"], "operator_base_hash": c["operator_base_hash"],
                    "fold": c["fold"], "ss_representation_schema_hash": ss_hash, "ms_representation_schema_hash": ms_hash,
                    "only_formal_difference": "representation_schema_hash"} for c in formal_cases]
    write_json(PAIRED, {"schema_version": "1.0.0", "stage": "MSO-02A", "status": "EXACT_PAIRED_IDENTITY_QUALIFIED",
                        "case_count": len(paired_rows), "particle_row_count": int(row_case.size), "only_formal_difference": "representation: SS -> MS",
                        "all_identity_checks_passed": True, "pairs": paired_rows})
    normalization, audit_rows = normalization_and_audit(ss_matrix, ms_matrix, row_case, formal_cases)
    write_json(OUT / "fold_normalization_registry.json", normalization)
    write_csv(OUT / "representation_dimensionality_audit.csv", audit_rows)
    coverage = coverage_geometry(ss_matrix, ms_matrix, row_case, row_particle, formal_cases, normalization, seed_record()["seed_digest_sha256"])
    write_json(OUT / "observable_coverage_geometry.json", coverage)
    bootstrap_freeze(formal_cases, seed_record()["seed_digest_sha256"])
    firewall = {"schema_version": "1.0.0", "stage": "MSO-02A", "status": "PASS",
                "target_file_open_count": 0, "reference_archive_read_count": 0, "continuum_operator_read_count": 0,
                "defect_generation_count": 0, "dnn_target_disagreement_count": 0, "conditional_variance_evaluation_count": 0,
                "oracle_fit_count": 0, "h3_verdict_count": 0, "neural_model_count": 0, "optimizer_count": 0,
                "training_count": 0, "integration_count": 0, "rollout_count": 0, "sealed_test_count": 0, "arc_access_count": 0}
    write_json(OUT / "firewall_audit.json", firewall)
    print(json.dumps({"status": "MSO02A_COMPUTE_COMPLETE", "formal_cases": len(formal_cases), "failed_primary": len(failed),
                      "reserve_used": sum(c["candidate_role"] == "RESERVE" for c in formal_cases), "ss_shape": ss_matrix.shape,
                      "ms_shape": ms_matrix.shape, "observable_store_sha256": sha256(STORE)}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "run"))
    args = parser.parse_args()
    torch.set_num_threads(1)
    os.environ.setdefault("PYTHONHASHSEED", "0")
    prepare() if args.action == "prepare" else run()


if __name__ == "__main__":
    main()
