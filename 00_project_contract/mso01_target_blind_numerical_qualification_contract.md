# MSO-01 target-blind numerical qualification contract

Status at freeze: `PROSPECTIVE_CONTRACT_FROZEN_BEFORE_MSO01_RESPONSE_EVALUATION`.

This contract authorizes only `MSO-01 — Target-Blind Multiscale Numerical Qualification`. It does not authorize MSO-02. Every MSO-00 artifact and scientific fact remains frozen. If this document conflicts with the hash-bound MSO-00 manifest, MSO-00 prevails and MSO-01 stops with `MSO01_PROVENANCE_CONFLICT`.

## Scientific and information boundary

- Scientific parents remain SPH-DDO and SPH-PIO only. ARC access/import is zero.
- Allowed compute is CPU float64 static SPH semidiscrete evaluation, deterministic graph construction, synthetic deployment-state fixtures, invariance/closure tests, scale-response numerical uncertainty, and resource diagnostics.
- Defect generation/read/decode, continuum/reference operator data, `target_ref__*`, H3, oracle fitting, feature selection by target, neural models, optimizers, training, integration, solver-in-loop, rollout, and sealed-test access are forbidden.
- The only intervention is `support = lambda * h0`, with `lambda = [0.75, 1.00, 1.25, 1.50]`. Particle state, count, spacing, domain, EOS, viscosity, kernel formula, precision, and physical parameters remain fixed.

## Bound static operator

The immutable vendor package is copied byte-for-byte from PIO HEAD `a0556093070f7f069ca6bea64b5f83d37bea9c76`, paths registered by MSO-00. It provides the periodic graph, Wendland C4 kernel/gradient, conservative pressure pair force, conservative viscosity pair force, and shared scatter/moment utilities.

For each deployment state, with particle volume `V_j = m_j / rho_j`:

1. `density_rate = -rho_i * div(raw_gradient(v, V))`;
2. `pressure_gradient_acceleration = conservative_pressure_forces(m, rho, p) / m_i`, with frozen weakly-compressible EOS `p = c0^2 (rho-rho0)`;
3. `viscosity_laplacian_acceleration = conservative_viscosity_acceleration(m, rho, v, nu)`;
4. `total_acceleration = pressure_gradient_acceleration + viscosity_laplacian_acceleration` (derived diagnostic only).

No time step is taken. Self edges are retained exactly as defined by the parent graph; their differential/pair-force contributions are zero where imposed by the parent formulas. Directed edges are lexicographically canonical and reciprocal.

## Prospective fixtures

The authoritative case registry is `05_registries/mso01_target_blind_case_registry.json`. It contains three 24 x 24 periodic layouts (regular, 5% jitter, 10% jitter), base support `h0/dx = 4`, fixed seeds, one target-blind excitation state, and a uniform-velocity identity derivative of every case. No fixture is generated from a target or reference quantity.

## Frozen numerical gates

- `lambda=1.00` must be bitwise equal between the MSO vendor path and the direct PIO parent path for canonical edges/order, support metadata, displacements/distances, kernel values/gradients, all three primary operators, total acceleration, and registered moments. Any failure stops the formal ladder decision.
- Repeated graph/operator calls must be bitwise identical.
- Every graph must have zero duplicate, nonreciprocal, out-of-bounds, omitted-strict-support, unexpected, or minimum-image-invalid edges. Exactly one parent-defined self edge per particle is required.
- Edge sets must satisfy `E_0.75 subset E_1.00 subset E_1.25 subset E_1.50` for every fixture; the total nesting violation count must be zero.
- At every scale and fixture: zero isolated particles; 1st-percentile nonself neighbor count at least 8; all weighted 2-D covariance matrices full rank; all support/kernel/operator values finite.
- Float64 structural tolerance for non-bitwise invariance and closure comparisons is `T(x) = 256 * eps64 * max(1, max_abs(x))`. Relative pair/global-force residuals must be at most `256*eps64`. Viscous power must be nonpositive up to the corresponding absolute tolerance, and the accumulated/direct pair-power identity must pass that tolerance.
- Edge reorder is tested by a frozen random permutation of directed edges. Particle equivariance is tested with a frozen particle permutation. Periodic translation uses `[0.5, -0.25]`; Galilean translation uses `[0.375, -0.625]`. Results are compared at the tolerance above. Uniform velocity must produce exact-zero continuity velocity-difference and viscosity components.
- Total acceleration closure is bitwise because total is defined by the registered component sum. No angular-momentum, total-energy, or thermodynamic-consistency gate is inferred.

## Frozen scale-response uncertainty aggregation

For non-unit `lambda` and component `c`, on each fixture:

`Delta L(lambda,c) = L(lambda,c) - L(1,c)`.

The recorded direct, difference, and log-scale response magnitudes are flattened particle/component RMS values. The numerical uncertainty is prospectively fixed as

`U(lambda,c) = max(repeat_rms_lambda, repeat_rms_base, edge_reorder_rms_lambda, edge_reorder_rms_base, 256*eps64*max(1, rms(L_lambda,c), rms(L_1,c)))`.

The resolvability ratio is `R = rms(Delta L) / U`. A scale/component passes when `R >= 100` on at least two of the three registered excitation fixtures. This is only a numerical distinguishability gate and has no target-prediction meaning. Pairwise log-scale slopes and both registered nonuniform log-scale curvatures are computed with the MSO-00 formulas before the decision is emitted.

## Scale and terminal decisions

Each scale is `QUALIFIED` or `NOT_QUALIFIED_<REASON>`; scales are never ranked or replaced. The anchor must pass. Anchor plus at least two non-unit scales establishes a minimum ladder. Four passing scales is `FULL`; three or more including the anchor is `PARTIAL`; otherwise `FAIL`. A partial subset containing both smaller and larger support is two-sided; a subset with only larger support is `ONE_SIDED_ENLARGED_SUPPORT_MULTISCALE_LADDER`.

MSO-02 may receive only eligibility when the ladder is FULL or PARTIAL, and is never executed by this stage.

## Resource and governance rules

Scales are evaluated sequentially. Edge count, mean neighbor count, wall time, peak RSS, operator-only time, relative cost to lambda=1, and summed sequential SS/MS cost are diagnostics; cost alone cannot reject a completed scale. All result artifacts are SHA-256 registered with source provenance, creation stage, role, and consumed status. No gate, aggregation, fixture, or scale may change after response inspection.
