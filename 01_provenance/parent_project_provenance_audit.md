# Parent-project provenance audit

Audit date: 2026-08-12 (Asia/Shanghai). Audit mode: read-only. No parent file, Git ref, index, worktree, data artifact, or result was modified.

## Audited repositories

| Project | Role | Audited HEAD | Branch/status | Remote |
|---|---|---|---|---|
| SPH-DDO-PoC | read-only historical definition/evidence context | `d76d29ae51e8104641b710371f0fcb248d5ea268` | `main`, clean | `https://github.com/hibiscus1031/SPH-DDO-PoC.git` |
| SPH-PIO-PoC | read-only historical static-code provenance source | `a0556093070f7f069ca6bea64b5f83d37bea9c76` | `main`, clean | `https://github.com/hibiscus1031/SPH-PIO-PoC.git` |

SPH-ARC was not opened, read, searched, imported, or used. Its scientific evidence contribution is exactly zero.

## DDO inheritance boundary

Eligible documentary inheritance is limited to the fixed-time defect definition, sign convention, continuum/SPH modeled-term alignment, EOS/domain/component semantics, reference firewall, uncertainty philosophy, H1/H2/H3 ordering, case-equal/fold-equal aggregation, lineage-held-out design, and consumed-versus-fresh evidence separation.

Historical DDO H3 outcomes are context only. The fresh DDO-02B context was: 384 cases, 49,152 particles, and failure of all three primary mappings. Reported oracle NRMSE was 0.5481, 1.01, and 1.049; DNN p90 was 8.202, 45.54, and 26.88 for density, pressure, and viscosity respectively. These values informed the order of magnitude and practical-significance proposal but are not copied as SS data and cannot qualify MSO.

## PIO static-code trace

The five dependency-closed static Stage01C files below first appear in the available PIO Git history at commit `275fafb` (2026-07-31, `stage-01c requalify structure-preserving SPH operators`). DDO independently recorded and retained byte-identical copies. A direct `cmp` at the audited HEADs confirmed all five DDO/PIO pairs are byte-identical.

| File | SHA-256 | Static boundary |
|---|---|---|
| `__init__.py` | `18afa8e375e06bd03ce68f17528c7a27722e1dbdab17536d1b060994446ad93a` | package marker only |
| `neighborhood.py` | `44d61e0abbc9901472dae90f83127f5231fc3f6e8ac92a971228dfdcb230aaa8` | deterministic 2-D CPU periodic compact-support neighborhoods |
| `kernels.py` | `bad08e0f49b308c568cd438c9981abd2c906e16c6570ebc0ca7d19d9847b333b` | formula-specific 2-D Wendland C4 values/gradients and static candidate operators |
| `conservative_pressure.py` | `b6366666ba89cc1f367a95390a411905eee8b7f55fba28a024f5732860004064` | reciprocal symmetric pressure pair force and static diagnostics |
| `conservative_viscosity.py` | `bdfbcb457f6973130f0131ec3c0a3fecc7197dd117c8256163cf3a1445307852` | reciprocal physical-viscosity pair force and static diagnostics |

The historical claim boundary remains formula-specific and static. PIO Stage01C evidence does not imply full-solver, dynamic topology, convergence, rollout, or general learned-model qualification. PIO's project-level route was closed with fresh-validation 0/4 and sealed test closed; none of that is MSO evidence.

## Target-blind interface findings

- `build_periodic_neighborhood(positions, support, ...)` accepts scalar or per-particle positive support and makes edge support the pair average. It rejects support at least half the periodic extent.
- Kernel normalization and gradients depend explicitly on `edge_support`; therefore \(\lambda h\) can be supplied without changing particle positions or formula family.
- Pressure forces use one unordered pair and opposite accumulation, supporting the reciprocal antisymmetric interface.
- Viscosity uses the same opposite accumulation and a nonnegative pair coefficient under its stated checks; angular-momentum conservation is not implied for noncentral viscous forces.
- Topology can change as \(\lambda\) crosses particle distances. Smooth response in \(\lambda\) is therefore not assumed and must not be claimed merely from differentiability inside a fixed graph.
- No target, reference field, integrator, optimizer, rollout, or neural model is required by these static interfaces.

## ARC conflict audit

The audit searched candidate-file content and all available DDO/PIO Git commit subjects for explicit `SPH-ARC`/path-bound ARC references. No match was found. The candidate files have an available PIO Git origin and DDO byte-identity record. Accordingly:

`PROVENANCE_CONFLICT_DETECTED=false`.

This is a bounded repository audit, not proof about unrecorded pre-Git authoring. Any later evidence that a candidate came from or was modified through ARC immediately changes its status to `PROVENANCE_CONFLICT_QUARANTINE`; it must not be imported silently.

## MSO-00 import decision

No parent code is imported in MSO-00. The registry records candidates only. Code copying, if ever needed, requires a separate MSO-01 target-blind qualification decision, exact source commit/path/hash binding, dependency closure, license/ownership review, and a repeat ARC-conflict check.

Terminal provenance finding: `DDO_PIO_PROVENANCE_CLEAR_ARC_SCIENTIFIC_IMPORT_ZERO`.
