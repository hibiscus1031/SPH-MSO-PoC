# MSO-02D componentwise identifiability failure attribution and route adjudication contract

Status: `FROZEN_BEFORE_NEW_ATTRIBUTION_COMPUTATION`.

Evidence class: `CONSUMED_EVIDENCE_DIAGNOSTIC_ONLY`.

This contract authorizes only componentwise diagnostic attribution on the already-consumed H-MSO-01R-A/B population. It does not reopen, repair, amend, or replace H-MSO-01R; it does not authorize fresh cases, targets, references, an H-MSO-02 atlas, MSO-03, or learning.

## 1. Permanent scientific and Git boundary

The following states are immutable:

```text
MSO02B_PAIRED_PRELEARNING_IDENTIFIABILITY_REQUALIFICATION_NOT_EVALUABLE
H_MSO01_MULTISCALE_IDENTIFIABILITY_RESCUE_NOT_EVALUABLE
HMSO01R_B_FRESH_CONFIRMATORY_MULTISCALE_IDENTIFIABILITY_RESCUE_NOT_QUALIFIED
```

The immutable component states are:

```text
density_rate = H_MSO01R_COMPONENT_QUALIFIED
pressure_gradient_acceleration = H_MSO01R_COMPONENT_NOT_QUALIFIED
viscosity_laplacian_acceleration = H_MSO01R_COMPONENT_NOT_QUALIFIED
```

The authorized parent is:

```text
HMSO01R_A_FINAL_COMMIT = 9048eff137001e5f644575bd02c3856b4f4ac532
HMSO01R_B_PRE_TARGET_COMMIT = 1c99103edaf76aa05915458fd498e07b1241e272
HMSO01R_B_FINAL_COMMIT = 47a15ce3e38dbf13d671b9ae7275bb84761ae279
branch = main
remote = none
push = false
```

`08_manifests/hmso01r_b_git_handoff.json` is the sole post-release binding from `RECORDED_BY_FINAL_GIT_COMMIT_AND_USER_HANDOFF` to the final R-B commit. No R-B report, manifest, ledger, metric, store, or registry may be rewritten.

The following are false throughout MSO-02D:

```text
H_MSO01R_REVERDICT
METRIC_REPAIR
GATE_AMENDMENT
FEATURE_AMENDMENT
COMPONENT_EXCLUSION
POST_HOC_H_MSO01R_RESCUE
```

## 2. Claims and interpretation firewall

Every newly generated scientific table or JSON conclusion is labeled `EXPLORATORY_CONSUMED_DIAGNOSTIC_ONLY`. New diagnostics may support attribution or prospective contract design only; they are not confirmatory evidence and cannot generate a new H-MSO-01R verdict.

The frozen lineage-held-out non-neural oracle may establish that `X_MS CONTAINS SUBSTANTIAL PREDICTIVE STRUCTURE`. It cannot establish that all variables required for local target uniqueness are present. Global prediction of `E[Y|X]` and residual `Var(Y|X)` are reported separately.

NRMSE is never converted automatically to explained variance by `1-NRMSE^2`. An R2-like interpretation is admissible only if a machine audit proves equivalence of the NRMSE denominator, mean-baseline denominator, case/lineage/family/fold aggregation, and weights to the standard variance decomposition. Otherwise only NRMSE, mean-baseline improvement, and foldwise/familywise residuals are used.

Candidate C `D<1` means only that descriptor-neighbour target disagreement is lower than matched-random target disagreement. It does not prove sufficient geometry or closed conditional ambiguity.

Operational near collisions and persistent local ambiguity are not described as intrinsic mathematical non-identifiability or mathematical multivaluedness.

## 3. Absolute prohibitions

The following action counts must remain zero:

```text
fresh_case_generation
fresh_target_generation
fresh_reference_generation
new_confirmatory_h3
h_mso01r_reverdict
formal_metric_modification
formal_gate_modification
formal_feature_modification
formal_scale_modification
formal_fold_modification
formal_normalization_modification
formal_bootstrap_redraw
neural_model
attention
transformer
learned_operator
optimizer
training
time_integration
solver_in_loop
rollout
sealed_test
arc_access
```

The formal SS/MS matrices, schemas, folds, normalizations, K, random comparators, bootstrap draws, Candidate C, CVAR, oracle family, coverage, gates, and component membership are read-only. Diagnostic transformations live only in `06_experiments/mso02d/` and never replace formal artifacts.

## 4. Permitted consumed evidence and activity

MSO-02D may read the hash-frozen H-MSO-01R-A observable store, schemas, registries, normalization, descriptor geometry, formal neighbour/random/bootstrap identities, and DESIGN_ONLY case/family/lineage metadata. After the target-blind freeze commit it may read the hash-frozen H-MSO-01R-B target store, Candidate C sufficient statistics/metrics, CVAR, oracle, coverage, predictions or residuals if present, component verdicts, bounds, checkpoints, summary, qualifications, and governance ledgers.

Permitted new actions are deterministic decomposition, target-blind geometry diagnostics, fixed preregistered group ablation with the frozen oracle, frozen oracle diagnostic replay when persisted predictions are absent, deployment-only directional proxy reconstruction, and exploratory target-alignment diagnostics on consumed rows.

Only the frozen 10,000 H-MSO-01R-A bootstrap identities may be consumed for uncertainty. No draw, threshold, p-value, model, or hyperparameter search is permitted.

## 5. Evidence identity and canonical-result stops

Before target-informed attribution, the executor recomputes the complete-file SHA-256 identities registered by the frozen H-MSO-01R-A precompute/manifest and H-MSO-01R-B manifest for at least the A/B manifest and status ledgers, observable store, target store, SS/MS schemas, formal atlas and particle registries, fold and normalization registries, descriptor geometry and identities, random registry and identities, bootstrap registry and draws, CA-MSO-01 amendment, Candidate C metrics, CVAR metrics, oracle metrics, coverage, component verdicts, and formal summary.

Any mismatch terminates immediately as `MSO02D_UPSTREAM_EVIDENCE_INTEGRITY_CONFLICT`. No attribution verdict is published after a mismatch.

Canonical values are loaded from frozen artifacts, never hard-coded as computed results, and compared with the user-authorized canonical identity table at a strict absolute/relative tolerance of `5e-8`. Any mismatch terminates as `MSO02D_CANONICAL_RESULT_IDENTITY_FAILURE`.

## 6. Mandatory stage firewall and commits

Execution order is strict:

1. protocol/handoff commit before attribution computation;
2. D0 candidate, proxy, group, diagnostic, and selection-rule freeze without target payload access;
3. D0 commit `MSO-02D D0: freeze target-blind alignment and directional proxy definitions`;
4. D1 observable-only T1/T2 computation and unique candidate/no-candidate freeze;
5. D1 commit `MSO-02D D1: freeze target-blind alignment selection before target diagnostics`;
6. D2 consumed-target identity audit and exploratory attribution without returning to alter D1;
7. D3 mechanism and route adjudication, release artifacts, and final commit.

The access ledger records every allowed payload class and first access stage. Before the D1 commit, `consumed_target_reads=0` and no target-informed metric payload is used for candidate/proxy definition or selection.

## 7. Theta definition audit

`THETA_DEFINITION_AUDIT` searches only authoritative frozen project artifacts and records the exact definition, formula, inputs, denominator, aggregation, component mapping, source path and SHA-256, target use, fold/family decomposition, uncertainty, and the mapping of the informal values `5.4/13.4`.

If any required element is absent, the status is `NOT_ADMISSIBLE_UNDEFINED_DIAGNOSTIC` and theta is not load-bearing evidence. If all elements are reproducible, its maximum status in this stage is `EXPLORATORY_CONSUMED_DIAGNOSTIC_ONLY` unless the preregistered fold/family replication rule is met.

## 8. D0 target-blind feature-group registry

MS columns are assigned from ordered schema names and frozen mathematical semantics only:

```text
G0 BASE_SINGLE_SCALE
G1 RAW_MULTI_SCALE_OPERATOR_VALUES
G2 BASELINE_SCALE_DIFFERENCES
G3 LOG_SCALE_DIVIDED_DIFFERENCES
G4 TOPOLOGY_SUPPORT_SUMMARIES
G5 DIRECTIONAL_OR_TENSOR_QUANTITIES_ALREADY_REGISTERED
G6 OTHER_PROSPECTIVELY_REGISTERED_MS_QUANTITIES
```

Ambiguous columns remain explicitly `UNMAPPED_NOT_FOR_ABLATION`; no forced or target-informed classification is allowed. Fixed ablations are BASE only, BASE plus each single mapped MS group, leave one mapped MS group out, and full MS. Adaptive combinations and feature-level selection are prohibited.

## 9. D0 Route A candidates

All candidates use only training-fold observables and deterministic float64 transforms. Targets never enter fitting, ranking, or tie-breaking.

`U0 FORMAL_IDENTITY_GEOMETRY` is the frozen per-arm training-fold median/IQR transform with exact-zero IQR divisor one and Euclidean distance.

`U1 SEMANTIC_GROUP_EQUAL_NORM` starts from the U0-normalized MS matrix. For group `g`, its training energy is `E_g = mean_i sum_{j in g} z_ij^2`. A positive-energy group is multiplied by `E_g^(-1/2)`; common multiplication of all groups is immaterial and omitted. A zero-energy group uses multiplier one with `ZERO_ENERGY_UNIT_FALLBACK`. No group or feature is deleted and within-group coordinates are unchanged.

`U2 OBSERVABLE_PARTICIPATION_SUBSPACE` starts from the U0-normalized MS matrix, centers by the training mean, forms the population covariance, uses deterministic symmetric eigendecomposition with descending eigenvalue and stable original-index tie order, and sets `r = ceil((tr C)^2 / tr(C^2))`, clipped to `[1,110]`. It projects onto the first `r` eigenvectors without target-based rank choice and without whitening. Exact-zero total covariance is `NOT_APPLICABLE_ZERO_COVARIANCE`.

`U3 SHRINKAGE_WHITENED_GEOMETRY` starts from the U0-normalized MS matrix and fits scikit-learn `LedoitWolf(assume_centered=False, store_precision=False, block_size=1000)` on training observables. The symmetric covariance is eigendecomposed; eigenvalues below `max_eigenvalue*1e-12` are clipped to that tolerance solely for numerical inversion. The centered coordinates are multiplied by the full-rank inverse square root. The installed Python, NumPy, SciPy, and scikit-learn versions are recorded. A zero maximum eigenvalue is `NOT_APPLICABLE_ZERO_COVARIANCE`.

No candidate may be added after D0.

## 10. D1 T1/T2 observable-only diagnostics and selection

T1 reports covariance/singular spectra, participation ratio, stable rank, cumulative-variance ranks at 90/95/99%, exact duplicate burden, fold-IQR degeneracy, group energy, group collinearity, cross-fold principal angles, and cross-family subspace stability for SS and MS. PCA/eigenspectra are diagnostic only.

T2 evaluates U0-U3 with all held-out rows as queries and the frozen legal training pools, K=10, the formal deterministic tie order `(distance, case_id, particle_id)`, and the frozen matched-random row identities as the random-distance reference. It reports K1/K10 distances, random-distance distribution, nearest-to-random-median ratio, distance concentration, K10 coefficient of variation, occurrence skew/Gini, neighbour-set transport/stability, effective dimension, duplicate domination, and semantic-group distance contribution.

For a query, `nearest_to_median_ratio = d_K1 / median(d_random)` and `k10_to_median_ratio = mean(d_K1..d_K10) / median(d_random)`. Lower is less concentrated. `distance_spread = (p90(d_random)-p10(d_random))/median(d_random)`. Hubness is computed from K10 occurrence counts over legal training rows; Gini uses the standard sorted nonnegative-sample formula. Group domination is the median over queries of the largest group-specific squared transformed difference divided by the sum of nonnegative group-specific squared transformed differences. For U2/U3, group-specific differences are transformed separately before squaring; cross terms are excluded by the registered additive diagnostic convention.

A non-identity candidate passes each fold or family stratum only when, relative to U0:

- `k10_to_median_ratio <= U0 * 1.01` and `nearest_to_median_ratio <= U0 * 1.01`;
- occurrence Gini `<= U0 + 0.01`;
- semantic-group domination `<= U0 + 0.01`;
- all values are finite and the transform is applicable.

It must pass concentration in at least 5/6 folds and 3/4 families, pass hubness in at least 5/6 folds and 3/4 families, pass group domination in at least 5/6 folds and 3/4 families, and meet its preregistered transform-stability audit. Stability requires median pairwise fold and family cosine/principal-angle similarity at least 0.75; for U1 this is cosine similarity of log group multipliers, for U2 top-`min(r_a,r_b)` projector overlap divided by that rank, and for U3 normalized Frobenius similarity of inverse-square-root transforms.

Among passing candidates, a deterministic composite rank is the sum of ranks (lower is better) of median fold `k10_to_median_ratio`, occurrence Gini, semantic-group domination, and fold/family transport coefficient of variation. Exact ties resolve by candidate ID `U1 < U2 < U3`. Selection additionally requires improvement beyond U0 in at least two of the first three median-fold criteria by more than numerical tolerance `1e-12`; otherwise no candidate is selected.

If none passes, the freeze status is `ROUTE_A_TARGET_BLIND_GEOMETRY_CANDIDATE_NOT_ESTABLISHED`. The selected transform parameters, selection inputs, source hashes, and registry/code hashes are frozen before target access.

## 11. D2 Route A target alignment

After the D1 commit only, U0 and the sole selected candidate (if any) are applied with identical folds, legal pools, K=10, exclusions, ties, and matched-random identities. Exploratory diagnostics are descriptor-distance/target-disagreement Spearman association, K10 disagreement enrichment, Candidate C `W(N)`, `W(B)`, and `D`, CVAR, within-neighbour target dispersion, fixed 10% near collisions, fold/family consistency, and density nondegradation.

Route A is `SUPPORTED_FOR_PROSPECTIVE_CONTRACT_DESIGN` only if its selection was entirely target blind; pressure and viscosity improve in at least 4/6 folds and 3/4 families; density has no major degradation; at least two independent alignment diagnostics improve; no feature/group was deleted; deployment needs no target/reference; and a single-variable fresh test can be specified. Otherwise it is `INCONCLUSIVE` or `NOT_SUPPORTED`. No new formal PASS/FAIL is emitted.

## 12. D0/D2 Route B directional proxies

Every proxy obeys:

```text
NO_PRINCIPAL_FRAME_EIGENVECTOR_DEPENDENCE = true
NO_EIGENVECTOR_SIGN_CONVENTION = true
NO_DEGENERACY_FALLBACK_TO_ARBITRARY_FRAME = true
O2_EQUIVARIANT_OR_INVARIANT_CONSTRUCTION = true
DEPLOYMENT_AVAILABLE = true
```

The D0 registry may contain only deterministic quantities from the frozen deployment state/schema: vector scale differences and log-scale divided differences; reflection-even cross-scale dot-product Gram entries; separately labeled reflection-odd 2D cross products; base-operator alignments, squared parallel/orthogonal magnitudes, and norm ratios with explicit zero-base status; trace/deviatoric norms and vector-tensor-vector contractions from already-deployed covariance or local-velocity second-moment tensors; and coordinate-free support-anisotropy invariants. No eigendirection, sign convention, arbitrary-frame fallback, target, or reference is used.

Each proxy is labeled `NEW_DEPLOYMENT_INFORMATION` or `ALGEBRAIC_REPARAMETERIZATION_OF_EXISTING_110D_FEATURES`, with input columns, support, determinism, O(2) parity, zero semantics, overlap with the 110D representation and DDO-02B, and incremental deployment cost. Algebraic reparameterizations belong to representation geometry and cannot by themselves satisfy Route B's new-information criterion.

After the proxy-definition hash freeze, D2 reports proxy association with target disagreement and formal-oracle residuals, full-population ambiguity/near-collision strata, invariant directional classes, fold/family replication, and frozen-ridge residual diagnostics using only the frozen oracle family/hyperparameters. It separately tests whether the old zero-denominator G1 `65/54` polarization fingerprint replicates in the full R-B pressure and viscosity population; the old subset counts are never treated as full-population evidence.

Route B is actionable only with two independent proxy diagnostics, support for both momentum components in at least 4/6 folds and 3/4 families, deployment compatibility, complete zero semantics, no principal-frame fallback, principled difference from DDO-02B, incremental information rather than simple 110D re-expression, density nondegradation, no target/reference at deployment, and a single-variable fresh intervention. Otherwise it is `INCONCLUSIVE` or `NOT_SUPPORTED`.

## 13. Fixed decompositions

Candidate C is decomposed into `W(N)`, `W(B)`, and `D=W(N)/W(B)` by overall, fold, family, family-fold, and lineage strata using frozen neighbour and matched-random identities. This determines whether non-improvement comes from numerator persistence, denominator change, ratio cancellation, isolated strata, or opposing strata; it creates no new gate.

Frozen CVAR semantics are decomposed by overall, fold, family, family-fold, lineage, target-amplitude stratum, and coverage status. K, neighbours, target transform, weighting, and normalization do not change.

Persisted cross-fitted oracle predictions/residuals are preferred. If absent, the exact frozen oracle family, folds, hyperparameters, selection, target scaling, and feature arms are replayed with no new option. Outputs are NRMSE and residual RMS by fold, family, lineage, amplitude, vector direction, and invariant directional strata. No explained-variance shortcut is used.

Formal U0 SS=39/MS=110 diagnostics report distance concentration, hubness, neighbour turnover, effective participation ratio, exact/near duplicates, and semantic-group contributions without changing the formal metric.

Near collision is fixed as `descriptor distance in bottom 10% of legal normalized distances AND target disagreement in top 10%` within the registered comparison population. Thresholds cannot be searched or changed. Results are called only `persistent operational near-collision evidence` and are reported inside/outside frozen formal coverage.

DESIGN_ONLY labels may stratify diagnostics but never enter a model or formal feature matrix.

## 14. Mechanisms and verdict taxonomy

Only these mechanisms are adjudicated:

- `F-MS1 TARGET_GEOMETRY_MISALIGNMENT`;
- `F-MS2 PERSISTENT_OPERATIONAL_LOCAL_AMBIGUITY`;
- `F-MS3 CURRENT_SUPPORT_SCALE_FAMILY_INSUFFICIENT`;
- `F-MS4 COMPONENT_SPECIFIC_REPRESENTATION_REQUIREMENT`;
- `F-MS5 HIGH_DIMENSION_DISTANCE_DILUTION`;
- `F-MS6 GLOBAL_PREDICTABILITY_LOCAL_IDENTIFIABILITY_SEPARATION`.

Allowed verdicts are `SUPPORTED_DOMINANT`, `SUPPORTED_PARTIAL`, `NOT_SUPPORTED`, and `INCONCLUSIVE`. Dominant requires at least three independent diagnostics, replication in at least 4/6 folds and 3/4 families, no major contrary evidence, joint explanation of pressure and viscosity, and consistency with density success. Partial requires at least two independent diagnostics but has fold/family/component limitations. F-MS5 is capped at `SUPPORTED_PARTIAL` unless a component interaction explains density success in the same 110D geometry.

F-MS6 is dominant only if pressure/viscosity oracle gains replicate in at least 4/6 folds and 3/4 families, Candidate C and CVAR do not improve, coverage passes, ambiguity is mainly inside coverage, and density shows the contrasting joint Candidate C/CVAR/oracle improvement. Its claim is limited to separation under the frozen representation, normalization, and Euclidean K10 geometry.

## 15. Future candidates and route adjudication

The future register contains:

- `H2-A TARGET_BLIND_ALIGNED_MULTISCALE_GEOMETRY` only as actionable when Route A meets all criteria;
- `H2-B O2_EQUIVARIANT_DIRECTION_RESOLVED_SCALE_RESPONSE` only as actionable when Route B meets all criteria;
- `H2-S SUPERVISED_REPRESENTATION_LEARNING` always `OUTSIDE_PRELEARNING_SCOPE` and unauthorized.

Candidate statuses are limited to `SUPPORTED_FOR_PROSPECTIVE_CONTRACT_DESIGN`, `INCONCLUSIVE`, `NOT_SUPPORTED`, and `OUTSIDE_PRELEARNING_SCOPE`. `AUTHORIZED_FOR_FRESH_COMPUTE` is forbidden.

If at least one A/B candidate is actionable, the terminal status is `MSO02D_COMPONENTWISE_FAILURE_ATTRIBUTION_COMPLETE_ACTIONABLE_HYPOTHESIS_IDENTIFIED` and only prospective contract design is recommended. If neither is actionable and F-MS6 is dominant, the terminal status is `MSO02D_COMPONENTWISE_FAILURE_ATTRIBUTION_COMPLETE_NO_ACTIONABLE_TARGET_BLIND_ROUTE`, support-scale route closure and a paper route are recommended, and fresh compute remains unauthorized.

The density positive result is preserved verbatim: support-scale multiscale representation qualified operational identifiability rescue for `density_rate` within frozen H-MSO-01R scope. It is neither erased by global failure nor extrapolated to momentum or learning.

## 16. Required outputs and provenance

All user-listed contract, registry, experiment, report, handoff, manifest, and status-ledger outputs are mandatory. The final manifest registers each output and every consumed upstream artifact with path, SHA-256, source, stage, evidence class, and consumption status. The final report answers all forty authorized questions and states the NRMSE/theta audit boundaries.

The final firewall records allowed read/diagnostic counts and zero for every prohibited activity. Internal informal prior probabilities are excluded from every scientific artifact.

## 17. Stop boundary

Under every outcome:

```text
FRESH_COMPUTE_AUTHORIZED = false
MSO03_DETERMINISTIC_CLOSURE_BASELINE_ELIGIBLE = false
NEURAL_TRAINING_AUTHORIZED = false
ATTENTION_AUTHORIZED = false
TRANSFORMER_AUTHORIZED = false
LEARNED_OPERATOR_AUTHORIZED = false
```

The stage stops immediately after the non-amended final commit `MSO-02D: componentwise failure attribution and route adjudication`, with branch `main`, a clean working tree, no remote, and no push.
