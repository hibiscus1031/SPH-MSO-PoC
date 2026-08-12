# H-MSO-01 prospective contract

Status: `CONTRACT_PROPOSAL_FROZEN_BEFORE_FRESH_TARGET_GENERATION`.

## Formal hypothesis

For the frozen instantaneous DDO defect and frozen SPH model, an explicitly support-scale-sensitive, deployment-compatible numerical-response representation reduces operational conditional ambiguity relative to an otherwise identical single-scale representation.

For primary component \(c\), let \(M_{c,m}^{SS}\) and \(M_{c,m}^{MS}\) be case-equal, fold-equal held-out estimates for metric family \(m\). H-MSO-01(c) passes only if MS meets every absolute gate and every paired relative-rescue gate in `prospective_gate_proposal.md`. The global hypothesis passes only if all three primary components pass. Otherwise the global result is `H_MSO01_NOT_SUPPORTED`; componentwise passes/failures remain reported.

This is deliberately falsifiable. A partial pass cannot be rewritten as a global pass.

## Learning object and components

The target remains exactly

\[
d_h^*=R_h\mathcal L(q^*)-\mathcal L_h(R_hq^*),
\]

with the DDO sign, fixed-time semantics, EOS, domain, modeled terms, support convention, and reference hierarchy. The three independent primary qualification components are density rate, pressure-gradient acceleration, and viscosity-Laplacian acceleration. Interpolation density is diagnostic only; total acceleration is derived only.

## Evidence population

- Formal MSO cases must be newly generated after MSO-00 and after the candidate ladder passes MSO-01.
- No DDO/PIO/ARC case, particle target, fitted statistic, split outcome, or target-derived choice is formal evidence.
- Before target generation, freeze a balanced case registry with at least 384 complete cases, at least 96 per retained DDO field family, and at least 6 complete field lineages represented in every family. If these minima cannot be met, amend the contract before target access or stop.
- A case is one complete field/layout/numerical configuration. Particles within a case are dependent observations, not independent replicates.
- Any pilot whose target has been viewed is `CONSUMED_DESIGN` and excluded from formal evidence.

## Split and aggregation

1. Assign complete field lineages to six outer folds by a deterministic manifest-bound hash before target generation.
2. All cases/seeds/resolutions from one lineage remain in one fold. SS and MS use the identical assignment.
3. Normalization, feature-space radii, bins, oracle hyperparameters, and regression coefficients are fitted within the five development folds only.
4. Evaluate on the held-out fold. Repeat six times.
5. First aggregate particles to case summaries with preregistered particle weights; then average cases equally within family/fold; then average folds equally. Family macro-averages are equal-weight unless a dimensional component definition requires a separately registered vector norm.
6. Use paired lineage/case cluster bootstrap draws shared by SS and MS. Report 10,000 deterministic resamples and simultaneous one-sided 95% bounds using the maximum studentized statistic across the three primary components within each metric family.

If fewer than the registered lineages support six folds, no particle-level resampling may be used to manufacture degrees of freedom.

## Metric families

### Descriptor nearest-neighbour disagreement

Robustly standardize each arm using development-fold deployment observables only. For every held-out particle, find `K=10` nearest development particles while excluding the same case, seed, and lineage. Target values are never used to choose neighbors. Report target disagreement relative to a deterministic matched random baseline, case median, case p90, reciprocal-neighbor consistency, family composition, sign disagreement, and coverage. `K={5,20}` is sensitivity only.

### Conditional variance

Estimate cross-fitted local conditional target variance using the same target-blind neighborhoods or target-blind bins. Divide within-neighborhood trace variance by total development-target trace variance componentwise. Report bias correction, effective case count, family composition, and simultaneous bootstrap bound.

### Simple non-neural oracle

Allowed classes are KNN averaging (`K={5,10,20}`), linear least squares/ridge, and degree-two polynomial ridge on a frozen invariant subset. Hyperparameters are selected only by nested lineage-held-out validation inside the outer development folds. Report held-out dimensional RMSE, `NRMSE=RMSE/target_RMS`, MAE, bias, vector angle above a prospectively fixed magnitude floor, and improvement over the development-fold mean-target predictor. These are diagnostics, not deployable models.

### Worst-family and coverage

Report every retained field family. No family may be hidden by a macro-average. Coverage radius is the arm-specific 95th percentile of leave-one-lineage-out development neighbor radii, frozen without target values. Report overall and per-family coverage.

## Fresh requalification

The first formal H-MSO-01 evaluation is already fresh relative to DDO and any MSO design pilot. If an outcome is used to redesign scales/descriptors/gates, it becomes consumed. A later claim requires a new registry with zero lineage/case overlap and reruns the unchanged amended contract. The sealed test remains unopened until a later governance decision.

## Stop rules

- Candidate scale ladder fails MSO-01: do not generate defect targets; issue a pre-target amendment or close the route.
- Firewall/schema audit fails: quarantine the affected artifact and invalidate both arms.
- SS/MS mismatch beyond representation: invalidate the causal comparison.
- Absolute gate fails: no architecture selection, even if a relative ratio looks favorable.
- Relative rescue fails: H-MSO-01 fails, even if MS alone passes an absolute threshold.
- Global hypothesis fails: retain component evidence and do not claim general multiscale rescue.

## Interpretation

A pass supports a bounded empirical statement over the registered atlas. It does not establish a universal inverse, a unique defect given arbitrary SPH states, a theorem of well-posedness, neural learnability, structure-preserving correction representability, time stability, or rollout performance.
