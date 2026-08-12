"""DDO-compatible analytical target/reference and CA-01 uncertainty helpers.

This module contains no DDO data, report, metric, or outcome path.  It is a
minimal isolated adaptation of the source functions registered in
``01_provenance/mso02b_target_reference_import_manifest.csv``.  The state
sampler deliberately reproduces the frozen MSO-02A expression ordering; the
closed-form and autograd continuum paths implement the same DDO formulas.
"""

from __future__ import annotations

import hashlib
import inspect
import math
from dataclasses import replace
from pathlib import Path
import sys
from typing import Any

import numpy as np
import torch


ROOT = Path(__file__).resolve().parents[3]
STATIC_OPERATOR = ROOT / "01_provenance/vendor/pio_stage01c_static"
sys.path.insert(0, str(STATIC_OPERATOR))

from structure_preserving.conservative_pressure import (  # noqa: E402
    conservative_pressure_forces,
    conservative_pressure_pair_forces,
)
from structure_preserving.conservative_viscosity import (  # noqa: E402
    conservative_viscosity_acceleration,
    conservative_viscosity_pair_forces,
)
from structure_preserving.kernels import (  # noqa: E402
    divergence_from_vector_gradient,
    edge_kernel_gradients,
    edge_kernel_values,
    raw_gradient,
    scatter_sum,
)
from structure_preserving.neighborhood import (  # noqa: E402
    PeriodicNeighborhood,
    audit_periodic_neighborhood,
    build_periodic_neighborhood,
    periodic_cartesian_layout,
)


C_FP = 128.0
EPS64 = float(np.finfo(np.float64).eps)
FROZEN_SCALES = {
    "rho": 1.0,
    "grad_rho": 1.0,
    "pressure": 100.0,
    "grad_pressure": 100.0,
    "velocity": 0.1,
    "grad_velocity": 0.1,
    "divergence": 0.1,
    "vorticity": 0.1,
    "strain": 0.1,
    "lap_velocity": 0.1,
    "continuum_density": 1.0,
    "continuum_density_rate": 0.1,
    "continuum_pressure_acceleration": 0.01,
    "continuum_viscosity_acceleration": 0.01,
    "continuum_acceleration": 0.01,
    "density_rate": 0.1,
    "target_pressure": 0.01,
    "target_viscosity": 0.01,
    "target_acceleration": 0.01,
}


def assert_static_operator_import_identity() -> None:
    expected_root = (STATIC_OPERATOR / "structure_preserving").resolve()
    symbols = (
        conservative_pressure_forces,
        conservative_viscosity_acceleration,
        edge_kernel_gradients,
        raw_gradient,
        audit_periodic_neighborhood,
        build_periodic_neighborhood,
    )
    for symbol in symbols:
        module = inspect.getmodule(symbol)
        path = Path(module.__file__).resolve() if module and module.__file__ else None
        if path is None or expected_root not in path.parents:
            raise RuntimeError(f"MSO02B_STATIC_OPERATOR_IMPORT_CONFLICT:{symbol.__name__}:{path}")


def max_abs(value: torch.Tensor) -> float:
    return float(value.detach().abs().max()) if value.numel() else 0.0


def linf_difference(left: torch.Tensor, right: torch.Tensor) -> float:
    if left.numel() == 0:
        return 0.0
    return float(torch.max(torch.abs(left.detach().cpu() - right.detach().cpu())))


def make_frozen_state(case: dict[str, Any]) -> dict[str, Any]:
    """Reproduce the exact MSO-02A particle/state expression ordering."""

    if not (
        int(case["resolution_per_axis"]) == 24
        and float(case["rho0"]) == 1.0
        and float(case["c0"]) == 10.0
        and float(case["kinematic_viscosity"]) == 0.01
        and case["dtype"] == "float64"
        and case["domain_minimum"] == [0.0, 0.0]
        and case["domain_maximum"] == [1.0, 1.0]
    ):
        raise ValueError("formal case violates frozen DDO/MSO physical scope")
    positions, dx, position_hash = periodic_cartesian_layout(
        int(case["resolution_per_axis"]),
        jitter_fraction=float(case["jitter_fraction"]),
        seed=int(case["jitter_seed"]),
        dtype=torch.float64,
        domain_minimum=(0.0, 0.0),
        domain_maximum=(1.0, 1.0),
    )
    density = torch.full((positions.shape[0],), 1.0, dtype=torch.float64)
    velocity = torch.zeros((positions.shape[0], 2), dtype=torch.float64)
    amplitude = float(case["active_amplitude"])
    modes = case["mode_indices"]
    phases = case["phases_radians"]
    if case["probe"] == "density":
        for mode, phase in zip(modes, phases, strict=True):
            argument = 2.0 * torch.pi * (
                mode[0] * positions[:, 0] + mode[1] * positions[:, 1]
            ) + phase
            density += (amplitude / len(modes)) * torch.sin(argument)
    else:
        for mode, phase in zip(modes, phases, strict=True):
            argument = 2.0 * torch.pi * (
                mode[0] * positions[:, 0] + mode[1] * positions[:, 1]
            ) + phase
            norm = math.hypot(*mode)
            direction = torch.tensor(
                (mode[0] / norm, mode[1] / norm), dtype=torch.float64
            )
            if case["probe"] == "transverse":
                direction = torch.tensor(
                    (-mode[1] / norm, mode[0] / norm), dtype=torch.float64
                )
            velocity += (
                (amplitude / len(modes))
                * torch.sin(argument)[:, None]
                * direction[None, :]
            )
    pressure = 100.0 * (density - 1.0)
    mass = torch.full((positions.shape[0],), dx**2, dtype=torch.float64)
    return {
        "positions": positions,
        "dx": dx,
        "position_hash": position_hash,
        "density": density,
        "velocity": velocity,
        "pressure": pressure,
        "mass": mass,
        "nu": 0.01,
    }


def particle_state_hash(state: dict[str, Any]) -> str:
    digest = hashlib.sha256()
    for name in ("positions", "density", "velocity", "mass"):
        digest.update(state[name].contiguous().numpy().tobytes())
    return digest.hexdigest()


def field_values_general(
    x: torch.Tensor, case: dict[str, Any]
) -> tuple[torch.Tensor, torch.Tensor]:
    modes = case["mode_indices"]
    phases = case["phases_radians"]
    if len(modes) > 1 and case["macro_family"] != "F2":
        raise ValueError("only frozen F2 cases may contain multiple analytical modes")
    amplitude = (
        float(case["active_amplitude"]) / len(modes)
        if case["macro_family"] == "F2"
        else float(case["active_amplitude"])
    )
    rho = x[:, 0] * 0.0 + 1.0
    velocity = x * 0.0
    for mode, phase in zip(modes, phases, strict=True):
        wave = 2.0 * torch.pi * (
            mode[0] * x[:, 0] + mode[1] * x[:, 1]
        ) + phase
        if case["probe"] == "density":
            rho = rho + amplitude * torch.sin(wave)
        else:
            norm = math.hypot(*mode)
            direction = torch.tensor(
                (mode[0] / norm, mode[1] / norm), dtype=x.dtype, device=x.device
            )
            if case["probe"] == "transverse":
                direction = torch.stack((-direction[1], direction[0]))
            velocity = velocity + amplitude * torch.sin(wave)[:, None] * direction[None, :]
    return rho, velocity


def evaluator_a_general(x: torch.Tensor, case: dict[str, Any]) -> dict[str, torch.Tensor]:
    modes = case["mode_indices"]
    phases = case["phases_radians"]
    if len(modes) > 1 and case["macro_family"] != "F2":
        raise ValueError("only frozen F2 cases may contain multiple analytical modes")
    amplitude = (
        float(case["active_amplitude"]) / len(modes)
        if case["macro_family"] == "F2"
        else float(case["active_amplitude"])
    )
    rho = torch.ones(x.shape[0], dtype=x.dtype, device=x.device)
    grad_rho = torch.zeros_like(x)
    velocity = torch.zeros_like(x)
    grad_velocity = torch.zeros((x.shape[0], 2, 2), dtype=x.dtype, device=x.device)
    lap_velocity = torch.zeros_like(x)
    for mode, phase in zip(modes, phases, strict=True):
        kappa = 2.0 * math.pi * torch.tensor(mode, dtype=x.dtype, device=x.device)
        wave = 2.0 * torch.pi * (
            mode[0] * x[:, 0] + mode[1] * x[:, 1]
        ) + phase
        sine, cosine = torch.sin(wave), torch.cos(wave)
        if case["probe"] == "density":
            rho = rho + amplitude * sine
            grad_rho = grad_rho + amplitude * cosine[:, None] * kappa[None, :]
        else:
            k2 = torch.dot(kappa, kappa)
            direction = kappa / torch.sqrt(k2)
            if case["probe"] == "transverse":
                direction = torch.stack((-direction[1], direction[0]))
            contribution = amplitude * sine[:, None] * direction[None, :]
            velocity = velocity + contribution
            grad_velocity = grad_velocity + (
                amplitude
                * cosine[:, None, None]
                * direction[None, :, None]
                * kappa[None, None, :]
            )
            lap_velocity = lap_velocity - k2 * contribution
    pressure = 100.0 * (rho - 1.0)
    grad_pressure = 100.0 * grad_rho
    divergence = grad_velocity[:, 0, 0] + grad_velocity[:, 1, 1]
    vorticity = grad_velocity[:, 1, 0] - grad_velocity[:, 0, 1]
    strain = 0.5 * (grad_velocity + grad_velocity.transpose(1, 2))
    return {
        "rho": rho,
        "grad_rho": grad_rho,
        "pressure": pressure,
        "grad_pressure": grad_pressure,
        "velocity": velocity,
        "grad_velocity": grad_velocity,
        "divergence": divergence,
        "vorticity": vorticity,
        "strain": strain,
        "lap_velocity": lap_velocity,
    }


def evaluator_b_general(x_input: torch.Tensor, case: dict[str, Any]) -> dict[str, torch.Tensor]:
    x = x_input.detach().clone().requires_grad_(True)
    rho, velocity = field_values_general(x, case)
    pressure = 100.0 * (rho - 1.0)
    grad_rho = torch.autograd.grad(rho.sum(), x, create_graph=True)[0]
    grad_pressure = torch.autograd.grad(pressure.sum(), x, create_graph=True)[0]
    gradients, laps = [], []
    for component in range(2):
        grad = torch.autograd.grad(velocity[:, component].sum(), x, create_graph=True)[0]
        gradients.append(grad)
        lap = torch.zeros(x.shape[0], dtype=x.dtype, device=x.device)
        for axis in range(2):
            if grad[:, axis].requires_grad:
                second = torch.autograd.grad(
                    grad[:, axis].sum(), x, retain_graph=True, create_graph=True
                )[0][:, axis]
                lap = lap + second
        laps.append(lap)
    grad_velocity = torch.stack(gradients, dim=1)
    lap_velocity = torch.stack(laps, dim=1)
    divergence = grad_velocity[:, 0, 0] + grad_velocity[:, 1, 1]
    vorticity = grad_velocity[:, 1, 0] - grad_velocity[:, 0, 1]
    strain = 0.5 * (grad_velocity + grad_velocity.transpose(1, 2))
    return {
        "rho": rho.detach(),
        "grad_rho": grad_rho.detach(),
        "pressure": pressure.detach(),
        "grad_pressure": grad_pressure.detach(),
        "velocity": velocity.detach(),
        "grad_velocity": grad_velocity.detach(),
        "divergence": divergence.detach(),
        "vorticity": vorticity.detach(),
        "strain": strain.detach(),
        "lap_velocity": lap_velocity.detach(),
    }


def discrete_components(
    neighborhood: PeriodicNeighborhood,
    rho: torch.Tensor,
    velocity: torch.Tensor,
    *,
    mass: float,
    c0: float = 10.0,
    rho0: float = 1.0,
    nu: float = 0.01,
) -> dict[str, torch.Tensor]:
    row, col, count = neighborhood.row, neighborhood.col, neighborhood.particle_count
    kernel = edge_kernel_values(neighborhood)
    gradient = edge_kernel_gradients(neighborhood)
    masses = torch.full((count,), mass, dtype=rho.dtype, device=rho.device)
    volumes = masses / rho
    density_sum = scatter_sum(row, masses[col] * kernel, count)
    interpolation_density = scatter_sum(row, volumes[col] * rho[col] * kernel, count)
    velocity_difference = velocity[col] - velocity[row]
    divergence = scatter_sum(
        row,
        volumes[col] * torch.sum(velocity_difference * gradient, dim=1),
        count,
    )
    density_rate = -rho * divergence
    pressure = c0**2 * (rho - rho0)
    pressure_acceleration = conservative_pressure_forces(
        neighborhood, mass=masses, density=rho, pressure=pressure
    ) / masses[:, None]
    viscosity_acceleration = conservative_viscosity_acceleration(
        neighborhood,
        mass=masses,
        density=rho,
        velocity=velocity,
        physical_viscosity=nu,
    )
    return {
        "density_sum": density_sum,
        "interpolation_density": interpolation_density,
        "divergence": divergence,
        "density_rate": density_rate,
        "pressure_acceleration": pressure_acceleration,
        "viscosity_acceleration": viscosity_acceleration,
        "acceleration": pressure_acceleration + viscosity_acceleration,
    }


def operator_components(neighborhood: PeriodicNeighborhood, state: dict[str, Any]) -> dict[str, torch.Tensor]:
    volume = state["mass"] / state["density"]
    velocity_gradient = raw_gradient(neighborhood, state["velocity"], volume)
    density_rate = -state["density"] * divergence_from_vector_gradient(velocity_gradient)
    pressure = conservative_pressure_forces(
        neighborhood,
        mass=state["mass"],
        density=state["density"],
        pressure=state["pressure"],
    ) / state["mass"][:, None]
    viscosity = conservative_viscosity_acceleration(
        neighborhood,
        mass=state["mass"],
        density=state["density"],
        velocity=state["velocity"],
        physical_viscosity=state["nu"],
    )
    return {
        "density_rate": density_rate,
        "pressure_gradient_acceleration": pressure,
        "viscosity_laplacian_acceleration": viscosity,
        "total_acceleration": pressure + viscosity,
    }


def operator_matrix(outputs: dict[str, torch.Tensor]) -> torch.Tensor:
    return torch.column_stack(
        (
            outputs["density_rate"],
            outputs["pressure_gradient_acceleration"],
            outputs["viscosity_laplacian_acceleration"],
        )
    )


def continuum_components(derivative: dict[str, torch.Tensor], *, nu: float = 0.01) -> dict[str, torch.Tensor]:
    rho = derivative["rho"]
    pressure = -derivative["grad_pressure"] / rho[:, None]
    viscosity = nu * derivative["lap_velocity"]
    return {
        "density": rho,
        "density_rate": -rho * derivative["divergence"],
        "pressure_acceleration": pressure,
        "viscosity_acceleration": viscosity,
        "acceleration": pressure + viscosity,
    }


def defects(continuum: dict[str, torch.Tensor], discrete: dict[str, torch.Tensor]) -> dict[str, torch.Tensor]:
    pressure = continuum["pressure_acceleration"] - discrete["pressure_acceleration"]
    viscosity = continuum["viscosity_acceleration"] - discrete["viscosity_acceleration"]
    return {
        "density_rate": continuum["density_rate"] - discrete["density_rate"],
        "pressure": pressure,
        "viscosity": viscosity,
        "acceleration": continuum["acceleration"] - discrete["acceleration"],
        "component_acceleration_sum": pressure + viscosity,
    }


def permute_neighborhood(neighborhood: PeriodicNeighborhood, permutation: torch.Tensor) -> PeriodicNeighborhood:
    return replace(
        neighborhood,
        row=neighborhood.row[permutation],
        col=neighborhood.col[permutation],
        displacement=neighborhood.displacement[permutation],
        distance=neighborhood.distance[permutation],
        edge_support=neighborhood.edge_support[permutation],
    )


def fsum_scatter(row: torch.Tensor, values: torch.Tensor, particle_count: int) -> torch.Tensor:
    row_np = row.detach().cpu().numpy().astype(np.int64, copy=False)
    values_np = values.detach().cpu().numpy()
    order = np.argsort(row_np, kind="stable")
    sorted_row, sorted_values = row_np[order], values_np[order]
    flat = sorted_values.reshape(sorted_values.shape[0], -1)
    result = np.zeros((particle_count, flat.shape[1]), dtype=np.float64)
    start = 0
    while start < len(sorted_row):
        particle = int(sorted_row[start])
        stop = start + 1
        while stop < len(sorted_row) and int(sorted_row[stop]) == particle:
            stop += 1
        for component in range(flat.shape[1]):
            result[particle, component] = math.fsum(
                float(item) for item in flat[start:stop, component]
            )
        start = stop
    return torch.from_numpy(result.reshape((particle_count, *values.shape[1:]))).to(dtype=values.dtype)


def compensated_discrete_components(
    neighborhood: PeriodicNeighborhood,
    rho: torch.Tensor,
    velocity: torch.Tensor,
    *,
    mass: float,
    c0: float = 10.0,
    rho0: float = 1.0,
    nu: float = 0.01,
) -> dict[str, torch.Tensor]:
    row, col, count = neighborhood.row, neighborhood.col, neighborhood.particle_count
    masses = torch.full((count,), mass, dtype=rho.dtype)
    volumes = masses / rho
    kernel = edge_kernel_values(neighborhood)
    gradient = edge_kernel_gradients(neighborhood)
    density_sum = fsum_scatter(row, masses[col] * kernel, count)
    interpolation_density = fsum_scatter(row, volumes[col] * rho[col] * kernel, count)
    divergence = fsum_scatter(
        row,
        volumes[col] * torch.sum((velocity[col] - velocity[row]) * gradient, dim=1),
        count,
    )
    density_rate = -rho * divergence
    pressure = c0**2 * (rho - rho0)
    ip, jp, pressure_pair = conservative_pressure_pair_forces(
        neighborhood, mass=masses, density=rho, pressure=pressure
    )
    pressure_acceleration = fsum_scatter(
        torch.cat((ip, jp)), torch.cat((pressure_pair, -pressure_pair), dim=0), count
    ) / masses[:, None]
    iv, jv, viscosity_pair, _ = conservative_viscosity_pair_forces(
        neighborhood,
        mass=masses,
        density=rho,
        velocity=velocity,
        physical_viscosity=nu,
    )
    viscosity_acceleration = fsum_scatter(
        torch.cat((iv, jv)), torch.cat((viscosity_pair, -viscosity_pair), dim=0), count
    ) / masses[:, None]
    return {
        "density_sum": density_sum,
        "interpolation_density": interpolation_density,
        "divergence": divergence,
        "density_rate": density_rate,
        "pressure_acceleration": pressure_acceleration,
        "viscosity_acceleration": viscosity_acceleration,
        "acceleration": pressure_acceleration + viscosity_acceleration,
    }


def compensated_operator_components(
    neighborhood: PeriodicNeighborhood,
    state: dict[str, Any],
) -> dict[str, torch.Tensor]:
    """Reaccumulate the exact frozen MSO lambda-one operator terms with fsum.

    The continuity operator must retain the frozen raw-gradient tensor
    decomposition (componentwise accumulation followed by a trace); summing an
    edgewise dot product would be algebraically equivalent but would not be the
    same floating-point term sequence as the registered MSO base operator.
    """

    row, col, count = neighborhood.row, neighborhood.col, neighborhood.particle_count
    volume = state["mass"] / state["density"]
    gradient = edge_kernel_gradients(neighborhood)
    difference = state["velocity"][col] - state["velocity"][row]
    gradient_terms = (
        volume[col, None, None]
        * difference[:, :, None]
        * gradient[:, None, :]
    )
    velocity_gradient = fsum_scatter(row, gradient_terms, count)
    density_rate = -state["density"] * divergence_from_vector_gradient(velocity_gradient)

    ip, jp, pressure_pair = conservative_pressure_pair_forces(
        neighborhood,
        mass=state["mass"],
        density=state["density"],
        pressure=state["pressure"],
    )
    pressure = fsum_scatter(
        torch.cat((ip, jp)),
        torch.cat((pressure_pair, -pressure_pair), dim=0),
        count,
    ) / state["mass"][:, None]
    iv, jv, viscosity_pair, _ = conservative_viscosity_pair_forces(
        neighborhood,
        mass=state["mass"],
        density=state["density"],
        velocity=state["velocity"],
        physical_viscosity=state["nu"],
    )
    viscosity = fsum_scatter(
        torch.cat((iv, jv)),
        torch.cat((viscosity_pair, -viscosity_pair), dim=0),
        count,
    ) / state["mass"][:, None]
    return {
        "density_rate": density_rate,
        "pressure_gradient_acceleration": pressure,
        "viscosity_laplacian_acceleration": viscosity,
        "total_acceleration": pressure + viscosity,
    }


def operator_as_discrete(outputs: dict[str, torch.Tensor]) -> dict[str, torch.Tensor]:
    """Expose frozen operator outputs under DDO defect-helper channel names."""

    return {
        "density_rate": outputs["density_rate"],
        "pressure_acceleration": outputs["pressure_gradient_acceleration"],
        "viscosity_acceleration": outputs["viscosity_laplacian_acceleration"],
        "acceleration": outputs["total_acceleration"],
    }


def independent_geometry_neighborhood(
    positions: torch.Tensor, support: float, *, chunk_size: int = 128
) -> PeriodicNeighborhood:
    count = int(positions.shape[0])
    domain_min = torch.tensor((0.0, 0.0), dtype=positions.dtype)
    domain_max = torch.tensor((1.0, 1.0), dtype=positions.dtype)
    extent = domain_max - domain_min
    particle_support = torch.full((count,), support, dtype=positions.dtype)
    eps = torch.finfo(positions.dtype).eps
    rows, cols, displacements = [], [], []
    for start in range(0, count, chunk_size):
        stop = min(start + chunk_size, count)
        raw = positions[start:stop, None, :] - positions[None, :, :]
        displacement = raw - extent * torch.floor(raw / extent + 0.5)
        distance = torch.linalg.vector_norm(displacement, dim=-1)
        retained = distance <= support * (1.0 + 16.0 * eps)
        local = torch.nonzero(retained, as_tuple=False)
        rows.append(local[:, 0] + start)
        cols.append(local[:, 1])
        displacements.append(displacement[local[:, 0], local[:, 1]])
    row, col = torch.cat(rows).to(torch.int64), torch.cat(cols).to(torch.int64)
    displacement = torch.cat(displacements)
    distance = torch.linalg.vector_norm(displacement, dim=1)
    return PeriodicNeighborhood(
        row=row,
        col=col,
        displacement=displacement,
        distance=distance,
        edge_support=torch.full_like(distance, support),
        particle_support=particle_support,
        domain_min=domain_min,
        domain_max=domain_max,
        particle_count=count,
    )


def derivative_sph_channels(
    derivative: dict[str, torch.Tensor],
    discrete: dict[str, torch.Tensor],
    neighborhood: PeriodicNeighborhood,
    *,
    mass: float,
    nu: float = 0.01,
) -> dict[str, torch.Tensor]:
    rho, velocity = derivative["rho"], derivative["velocity"]
    volumes = torch.full_like(rho, mass) / rho
    gradient_velocity = raw_gradient(neighborhood, velocity, volumes)
    gradient_rho = raw_gradient(neighborhood, rho, volumes)
    divergence = gradient_velocity[:, 0, 0] + gradient_velocity[:, 1, 1]
    vorticity = gradient_velocity[:, 1, 0] - gradient_velocity[:, 0, 1]
    strain = 0.5 * (gradient_velocity + gradient_velocity.transpose(1, 2))
    return {
        "rho": discrete["density_sum"],
        "grad_rho": gradient_rho,
        "pressure": 100.0 * (rho - 1.0),
        "grad_pressure": -rho[:, None] * discrete["pressure_acceleration"],
        "velocity": velocity,
        "grad_velocity": gradient_velocity,
        "divergence": divergence,
        "vorticity": vorticity,
        "strain": strain,
        "lap_velocity": discrete["viscosity_acceleration"] / nu,
    }


def continuum_sph_channels(discrete: dict[str, torch.Tensor]) -> dict[str, torch.Tensor]:
    return {
        "density": discrete["density_sum"],
        "density_rate": discrete["density_rate"],
        "pressure_acceleration": discrete["pressure_acceleration"],
        "viscosity_acceleration": discrete["viscosity_acceleration"],
        "acceleration": discrete["acceleration"],
    }


def characteristic_scale(frozen: float, analytic: torch.Tensor, sph: torch.Tensor) -> float:
    return max(float(frozen), max_abs(analytic), max_abs(sph))


def topology_keys(neighborhood: PeriodicNeighborhood) -> torch.Tensor:
    return torch.sort(neighborhood.row * neighborhood.particle_count + neighborhood.col).values


def target_analytic_and_sph(
    name: str, continuum: dict[str, torch.Tensor], discrete: dict[str, torch.Tensor]
) -> tuple[torch.Tensor, torch.Tensor]:
    if name == "density_rate":
        return continuum["density_rate"], discrete["density_rate"]
    if name == "pressure":
        return continuum["pressure_acceleration"], discrete["pressure_acceleration"]
    if name == "viscosity":
        return continuum["viscosity_acceleration"], discrete["viscosity_acceleration"]
    if name == "acceleration":
        return continuum["acceleration"], discrete["acceleration"]
    raise KeyError(name)
