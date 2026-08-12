# MSO-01 target-blind numerical qualification report

## Terminal decision

`MSO01_TARGET_BLIND_MULTISCALE_NUMERICAL_LADDER_QUALIFIED`

`LADDER_STATUS = FULL`

Qualified subset: `[0.75, 1.00, 1.25, 1.50]`.

All four prospectively frozen support multipliers passed. This result establishes only that the candidate scales are numerically legal, deterministic, structurally compatible, repeatable, and numerically distinguishable target-blind observations of the same frozen static SPH operator. It does not evaluate defect identifiability, representation benefit, learnability, any neural architecture, or rollout.

## Execution and provenance boundary

- MSO-00 artifact hashes were verified before work; every registered hash matched.
- PIO parent HEAD remained `a0556093070f7f069ca6bea64b5f83d37bea9c76`; DDO parent HEAD remained `d76d29ae51e8104641b710371f0fcb248d5ea268`. Both parent worktrees were clean at the pre-execution audit and were not modified.
- The five imported PIO Stage01C static files matched the MSO-00 source hashes and their immutable MSO destination hashes byte-for-byte. No provenance mismatch occurred.
- ARC code, result, parameter, evidence, and path access count was zero.
- The project root was not a Git repository. No repository, remote, branch, or commit was created.

## Scale decisions

| lambda | Decision | Directed edges across regular / 5% jitter / 10% jitter | Mean nonself neighbors across fixtures | Failure reason |
|---:|---|---|---|---|
| 0.75 | `QUALIFIED` | 16,704 / 15,550 / 15,574 | 28.000 / 25.997 / 26.038 | none |
| 1.00 | `QUALIFIED` | 28,224 / 27,058 / 27,356 | 48.000 / 45.976 / 46.493 | none |
| 1.25 | `QUALIFIED` | 46,656 / 43,238 / 43,820 | 80.000 / 74.066 / 75.076 | none |
| 1.50 | `QUALIFIED` | 65,088 / 64,006 / 64,664 | 112.000 / 110.122 / 111.264 | none |

Counts include the parent-defined one-self-edge-per-particle convention in the directed-edge total; the reported neighbor means exclude self.

## Q1 — lambda=1 identity

The direct PIO parent path and the immutable MSO vendor path were compared on all three registered states. All 51/51 identity rows passed bitwise with maximum absolute discrepancy `0.0`. The comparison covered canonical row/column order, displacements, distances, edge and particle support, kernel values, kernel gradients, density rate, pressure acceleration, viscosity acceleration, total acceleration, and raw zeroth/first kernel moments. The registered `Delta L_1` values were exact zero.

Therefore `lambda=1.00` strictly reproduces the frozen base implementation.

## Q2 — support and topology

- Repeated construction returned bitwise-identical graphs and support metadata in all 12 case-scale evaluations.
- Duplicate, nonreciprocal, out-of-bounds, missing-self, omitted strict-support, unexpected-support, and invalid minimum-image counts were all zero.
- The total nesting violation count was zero, so `E_0.75 subset E_1.00 subset E_1.25 subset E_1.50` held on every registered state.
- The minimum 1st-percentile nonself neighbor count was `24`, above the frozen gate of `8`; no particle had zero neighbors.
- Weighted covariance rank-deficient environment count was zero. The smallest observed covariance eigenvalue was `0.003979372281203254`, maximum anisotropy condition number was `1.2157576295912575`, and minimum support-completeness fraction was `1.0`.

No support or rank degeneracy was detected.

## Q3 — determinism and structural identities

All 360/360 invariance/structure rows passed.

- Operator repeats were bitwise identical.
- Edge reorder, particle permutation, periodic translation, and Galilean checks passed the prospectively frozen float64 tolerance. Their largest absolute discrepancies were respectively `4.9960e-16`, `1.3462e-15`, `3.4348e-15`, and `7.7716e-16`.
- Uniform velocity produced exact-zero density-rate velocity-difference and viscosity responses at every case-scale combination.
- Pressure and viscosity pair-force reciprocity residuals were exactly zero. Maximum relative global internal-force residuals were `9.1598e-18` for pressure and `8.1306e-18` for viscosity, both below `256*eps64`.
- Viscosity gamma symmetry residual was zero and gamma remained nonnegative.
- Viscous accumulated and direct pair power were nonpositive, spanning `[-0.0108413, -0.00906070]`; their maximum identity difference was `3.4694e-18`.
- Total acceleration component closure was bitwise exact.

Pressure central-force torque was retained as a diagnostic. No angular-momentum guarantee was claimed for the noncentral viscosity force, and no energy or thermodynamic claim was inferred beyond the registered viscous-power property.

## Q4 — numerical scale-response resolvability

Every non-unit scale/component passed `R >= 100` on all three fixtures (the gate required at least two). The table gives the minimum and maximum `R` over fixtures.

| lambda | density_rate R | pressure acceleration R | viscosity acceleration R |
|---:|---:|---:|---:|
| 0.75 | `5.14e11`–`5.22e11` | `3.57e11`–`4.96e11` | `3.22e10`–`7.77e10` |
| 1.25 | `6.41e11`–`6.46e11` | `4.07e11`–`4.15e11` | `4.55e10`–`5.04e10` |
| 1.50 | `1.33e12`–`1.34e12` | `8.07e11`–`8.12e11` | `9.70e10`–`1.01e11` |

The global minimum was `3.2157950312e10`. Direct scale RMS, baseline-difference RMS, log-scale divided-difference RMS, both preregistered pair slopes, both preregistered nonuniform curvatures, topology growth, repeat noise, reorder noise, the dtype floor, `U`, and `R` are retained in the audit tables. These ratios mean only that the static scale response is distinguishable from repeat/accumulation uncertainty; they say nothing about predicting `d_h*`.

## Cost diagnostics

The peak observed process RSS was `333,185,024` bytes. Median operator-only relative costs versus lambda=1 were `0.635`, `1.000`, `1.607`, and `2.333` for lambda `0.75`, `1.00`, `1.25`, and `1.50`, respectively. Median combined graph-plus-operator relative costs were `1.307`, `1.000`, `1.031`, and `1.250`; short graph timings are noisy and diagnostic only. All four graphs were evaluated sequentially, and no scale was rejected for cost.

## Firewall audit

Pre- and post-execution controlled access audits both passed:

- target data file open count: `0`;
- reference archive read count: `0`;
- defect generation count: `0`;
- H3 metric count: `0`;
- oracle fit count: `0`;
- neural model count: `0`;
- optimizer count: `0`;
- time integration count: `0`;
- rollout count: `0`;
- sealed-test count: `0`.

No target/reference outcome informed a scale, fixture, tolerance, aggregation, or gate.

## Required final answers

1. **Which lambda passed?** All four: `0.75`, `1.00`, `1.25`, `1.50`.
2. **Which failed and why?** None failed; the failure-reason lists are empty.
3. **Did lambda=1 reproduce the frozen base operator?** Yes, bitwise on every registered identity quantity and fixture.
4. **Were graphs monotonically nested?** Yes; total nesting violations were zero.
5. **Was support/rank degeneracy present?** No; zero isolated and zero rank-deficient environments, with full support completeness.
6. **Were component structural identities preserved?** Yes; all registered repeatability, invariance, reciprocal-force, dissipation, uniform-velocity, and component-closure gates passed.
7. **Was scale response above numerical/repeat uncertainty?** Yes; every non-unit component passed on all three fixtures, with global minimum `R = 3.2157950312e10` against gate `100`.
8. **Was any target/reference data read?** No; both controlled counts were zero.
9. **Was any H3/oracle/neural computation performed?** No; all corresponding counts were zero.
10. **Is the ladder FULL, PARTIAL, or FAIL?** `FULL`.
11. **If PARTIAL, is it one- or two-sided?** Not applicable. The full ladder is two-sided in support.
12. **Does MSO-02 receive only eligibility?** Yes: `MSO02_PRELEARNING_IDENTIFIABILITY_EXPERIMENT_ELIGIBLE = true`; MSO-02 was not executed.
13. **Was any post-outcome gate/scale modification made?** No. No ranking or replacement scale was produced.
14. **Final terminal status?** `MSO01_TARGET_BLIND_MULTISCALE_NUMERICAL_LADDER_QUALIFIED`.

Stop after MSO-01. Do not execute MSO-02.
