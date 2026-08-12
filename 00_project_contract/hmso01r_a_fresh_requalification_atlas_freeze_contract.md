# H-MSO-01R-A fresh requalification atlas and confirmatory analysis freeze contract

Status: `FROZEN_BEFORE_ANY_HMSO01R_FRESH_CASE_GENERATION`.

## Scope and immutable scientific state

This contract authorizes only `H-MSO-01R-A`, the target-blind preparation stage for the new prospective hypothesis `H-MSO-01R`. It does not authorize `H-MSO-01R-B`, target or reference generation/read, formal H3 evaluation, MSO-03, neural models, attention, optimization, training, time integration, solver-in-loop execution, rollout, sealed-test access, or ARC access.

The historical states remain permanently unchanged:

- `MSO02B_PAIRED_PRELEARNING_IDENTIFIABILITY_REQUALIFICATION_NOT_EVALUABLE`
- `H_MSO01_MULTISCALE_IDENTIFIABILITY_RESCUE_NOT_EVALUABLE`

`MSO03_ELIGIBLE`, `ATTENTION_AUTHORIZED`, `NEURAL_TRAINING_AUTHORIZED`, and `LEARNED_OPERATOR_AUTHORIZED` remain false. A successful R-A stage can establish eligibility for R-B only; it cannot establish any scientific identifiability or rescue result.

## Provenance handoff

The required starting identity is:

- branch: `main`
- `G2_FINAL_COMMIT`: `f620baed60a78846459b80fe90c5239ba6788f6e`
- working tree: clean
- remote: none
- push: false

Before this contract was created, the working-tree bytes of the MSO-00, MSO-01, MSO-02A, MSO-02B, MSO-02C G1, and MSO-02C G2 manifests and status ledgers were compared with their Git `HEAD` blobs and all identities passed. The CA-MSO-01 amendment SHA-256 is `fec81d9dceeb4edc93b19adf0eb063e564effda81f700ea69174963b75454650`, matching the frozen G2 status ledger.

The pre-case commit containing this contract shall be recorded as `HMSO01R_A_PRE_CASE_COMMIT` in the final R-A manifest, status ledger, and report. No fresh candidate registry or case is generated before that commit.

## Prospective hypothesis and target firewall

The hypothesis identity is `H-MSO-01R`:

> Does the prospectively frozen multiscale-response representation, evaluated with the zero-safe aggregate DNN statistic defined by CA-MSO-01, reduce deployment-compatible conditional ambiguity relative to the paired single-scale control on a completely fresh atlas?

The three primary components remain `density_rate`, `pressure_gradient_acceleration`, and `viscosity_laplacian_acceleration`. `interpolation_density` is diagnostic only and `total_acceleration` is derived diagnostic only. The future target definition remains `d_h* = R_h L(q*) - L_h(R_h q*)`, with the formal base operator fixed at lambda 1.00. R-A shall neither generate nor read that target.

R-A may create only a physically separated observable store containing deployment-compatible quantities. It shall contain no `q_ref`, `rho_ref`, `v_ref`, `a_ref`, continuum operator, `d_h*`, manufactured-field identity, lineage label as a model feature, design-only hidden variable, or target-derived quantity.

## Fresh atlas identity

Exactly one deterministic seed is derived from the frozen G2 manifest file SHA-256, the frozen CA-MSO-01 amendment SHA-256, and the literal `HMSO01R_A_FRESH_ATLAS`. No alternative seed may be tried or selected.

Before operator evaluation, the following registries are generated, deterministically ordered, and hash-frozen:

- PRIMARY: exactly 384 candidates, 96 in each of F1-F4.
- RESERVE: exactly 128 candidates, 32 in each of F1-F4.

Freshness is assessed using canonical authoritative field-lineage/generation payloads, not case-id strings. Candidate and formal lineages must have zero overlap with all registered or consumed DDO-01D, DDO-02B, PIO TRAIN/VALIDATION/FRESH, MSO-01, MSO-02A/B, MSO-02C G1/G2, reserve, and historically opened target/reference lineages discoverable from frozen governance registries. `HISTORICAL_LINEAGE_OVERLAP_COUNT` must equal zero.

Primary cases are evaluated first in frozen order. A failed primary may be replaced only by the next frozen same-family reserve candidate. Rejections remain in the permanent audit. No second reserve batch is permitted. Failure to admit exactly 96 cases per family terminates as `HMSO01R_A_FRESH_ATLAS_NOT_QUALIFIED`.

## Four-scale target-blind admissibility

The immutable MSO-01 scale ladder is `[0.75, 1.00, 1.25, 1.50]`. Every formal case must pass all four scales for finite state and operator outputs; deterministic, reciprocal, periodic-minimum-image graph semantics; duplicate/alias and self-edge conventions; graph nesting; zero-neighbour and minimum-support checks; weighted-covariance rank; support completeness; repeatability; lambda-1 vendor/base identity; component closure; and finite scale-response features.

SS and MS use the identical formal case set and particle states. Every formal case must be four-scale admissible.

## Frozen representations and paired particle identity

The SS schema is the previously frozen 39-dimensional schema and the MS schema is the previously frozen 110-dimensional schema. Their ordered column semantics must be byte-for-byte equivalent after removing stage-only metadata. No feature is added, deleted, deduplicated, transformed by PCA/whitening, or removed because it is constant, duplicate, linearly dependent, or IQR-degenerate.

For each formal case, exactly 128 particle identities are sampled deterministically before target access. The sample rule is hash-ranked by the prospective R-A seed, case identity, and particle id; it has no target input. SS and MS share each selected case id, particle id, particle-state hash, lineage, family, physics hash, base-operator hash, and fold. The sole formal intervention is the representation schema.

## Folds, normalization, descriptor and coverage geometry

Six target-blind lineage-held-out outer folds are constructed from the fresh lineages. All particles from a case and all cases from a lineage remain together; SS and MS assignments are identical; every family is represented in every fold where prospectively feasible. Target amplitude and historical H3 outcomes are prohibited fold inputs.

For each arm and fold, normalization uses training-fold-only median/IQR. Exact-zero IQR uses divisor 1 while retaining the column. These registries are frozen from fresh observable features and cannot be recomputed in R-B.

Normalized SS/MS descriptor geometry, legal cross-lineage training pools, exclusions, deterministic `(distance, case_id, particle_id)` tie ordering, K=10 primary neighbours, and coverage geometry are frozen before target access. Internal tie completion may inspect more than 10 candidates, but the frozen primary neighbour set is exactly 10. No target disagreement or scientific coverage verdict is computed in R-A.

## Matched-random comparator identity

For every formal query, exactly K=10 matched-random comparator identities are generated with deterministic PCG64/hash-domain seeds and the same formal exclusions. The full machine-readable identity registry is frozen before target access. SS and MS use the same comparator identities; the comparator does not depend on representation.

## Candidate C zero-safe DNN semantics

R-A freezes but does not evaluate the target-dependent primitives:

- `N_i`: mean squared target disagreement over the 10 legal descriptor nearest neighbours.
- `B_i`: mean squared target disagreement over the 10 frozen matched-random comparators.

The primary statistic is exactly `D = W(N) / W(B)`, where `W` applies equal weighting in the order particle to case, case to lineage, lineage to family, and family to fold. There is exactly one division after both fully balanced aggregates. Pointwise ratios, epsilon, clipping, zero-row/group deletion, and automatic zero-baseline PASS are forbidden.

Isolated and group-level zero denominators are retained. If final `W(B)==0`, status is `DNN_NOT_EVALUABLE_ZERO_AGGREGATE_RANDOM_BASELINE`. If the future SS point estimate is zero, relative rescue is `RELATIVE_RESCUE_NOT_EVALUABLE_ZERO_SS_BASELINE`.

The absolute gate remains strict: point `D<1` and simultaneous UCB `<1`. The relative gate remains point `D_MS/D_SS<=0.80` and simultaneous UCB `<=0.90`. All conditional-variance, non-neural oracle, mean-baseline, worst-family, coverage, family/fold, multiplicity, and simultaneous-confidence rules remain unchanged.

## Fresh paired bootstrap and synthetic-only implementation preflight

Exactly 10,000 fresh, unique, paired cluster-bootstrap draws are generated before target access. The frozen design is lineage-first, complete-case, family/fold balanced, identical for SS/MS and all components, with maximum-studentized one-sided simultaneous inference. No MSO-02A draw identity is reused and no draw is regenerated after target access.

Synthetic-only scalar and vector target arrays are used to execute Candidate C point and all 10,000-draw bootstrap paths. Tests cover isolated 0/0, isolated positive/0, zero case, lineage, family, and fold denominator contributions, positive/zero total `W(B)`, zero SS baseline, zero MS, one-division aggregation, no epsilon or deletion, per-replicate re-aggregation, simultaneous-bound execution, and NOT_EVALUABLE propagation. No old or fresh actual target is used.

Oracle preflight is restricted to finite design matrices, frozen polynomial/design construction, fold dimensions, condition-number diagnostics, regularization-matrix construction, and solver execution on synthetic targets. The oracle family and hyperparameter grid cannot be changed in response to observed conditioning.

## Firewall and terminal decision

Both pre- and post-stage firewall audits require zero target file opens/payload reads, reference archive reads, continuum-operator reads, defect generations, DNN target disagreements, conditional-variance evaluations, oracle fits, H3 verdicts, neural models, attention, optimizers, training, integration, solver-in-loop activity, rollout, sealed-test access, and ARC access. Any nonzero count terminates as `HMSO01R_A_INFORMATION_FIREWALL_BREACH`.

R-A passes only if every requirement in the user-authorized H-MSO-01R-A protocol is satisfied without amendment. Its sole PASS terminal status is:

`HMSO01R_A_FRESH_CONFIRMATORY_ATLAS_AND_ZERO_SAFE_ANALYSIS_FROZEN`

Only then may `HMSO01R_B_FRESH_CONFIRMATORY_TARGET_REQUALIFICATION_ELIGIBLE` be true. R-B remains unexecuted and unauthorized in this stage.
