# MSO-02C G2 zero-safe DNN metric selection protocol

Status: `FROZEN_BEFORE_ANY_SYNTHETIC_CANDIDATE_COMPARISON`.

This contract prospectively governs **MSO-02C G2 — Zero-Safe DNN Metric
Selection and Prospective Amendment**. It is frozen before running any
candidate on the synthetic S1--S18 fixtures. Its authority is the user
instruction attachment
`/Users/xiejinbo/.codex/attachments/acbcde39-cb9f-43a2-8117-9494893d0435/pasted-text.txt`,
SHA-256
`8d160805df3778a9efd65a9c4886c5c337b6725393fc37aa7fb62bece92e6f90`.

## 1. Immutable handoff and firewall

```text
G1_FINAL_COMMIT = b6dac26624b9b45912a79e6cddec1c0caa509adf
G2_PRE_SYNTHETIC_COMMIT = RECORDED_BY_POST_COMMIT_G2_MANIFEST
branch = main
working_tree_clean_at_handoff = true
remote = none
push = false

MSO02B_PAIRED_PRELEARNING_IDENTIFIABILITY_REQUALIFICATION_NOT_EVALUABLE
H_MSO01_MULTISCALE_IDENTIFIABILITY_RESCUE_NOT_EVALUABLE
```

Those two scientific states are permanent and may not be relabelled PASS or
FAIL. No MSO-02B or G1 historical artifact may be modified.

G1 A/B attribution evidence and the earlier consumed MSO-02B evidence have
already been seen. This fact is disclosed, but neither is an input to the G2
candidate-selection algorithm. G2 is isolated to formulas and synthetic data
created by its frozen generator.

Before this protocol was committed, one auxiliary static-audit process issued
one over-broad text search whose output included old MSO-02B metric/checkpoint
lines. The exact number of matched old files was not recorded. That process did
not open or hash either store, did not recompute a candidate, did not transmit
any old numeric value into this protocol, and its threshold recommendation is
quarantined and excluded. This incident must remain visible in the G2 report
and ledgers; it may not be represented as zero old-metric text access. The
selection remains prospective because its formulas, fixtures, hard criteria,
and threshold rule below are frozen without any old value as an input.

During G2:

```text
REAL_MSO02B_CANDIDATE_PERFORMANCE_COMPARISON = false
REAL_TARGET_OR_OBSERVABLE_PAYLOAD_READ = false
G1_DERIVED_OUTCOME_PAYLOAD_READ_FOR_SELECTION = false
OLD_METRIC_TEXT_ACCIDENTAL_SEARCH_EVENTS = 1
OLD_METRIC_MATCHED_FILE_COUNT = NOT_RECORDED
OLD_METRIC_NUMERIC_VALUES_USED_FOR_SELECTION = false
OLD_METRIC_RECOMPUTATION_COUNT = 0
TARGET_STORE_PAYLOAD_READ_COUNT = 0
OBSERVABLE_STORE_PAYLOAD_READ_COUNT = 0
CONSUMED_TARGET_METRIC_REPLAY_BEFORE_FREEZE = false
CONSUMED_REPLAY = false
NEW_H3_VERDICT = false
MSO03_ELIGIBLE = false
ATTENTION_AUTHORIZED = false
NEURAL_TRAINING_AUTHORIZED = false
LEARNED_OPERATOR_AUTHORIZED = false
```

Only the new `06_experiments/mso02c/g2/` synthetic namespace and the G2
contract/report/manifest paths listed below may be written.

## 2. Common notation and immutable aggregation units

For arm `a`, component `q`, formal case `c`, and particle `i`, let

```text
n[a,q,c,i] = mean over the frozen K10 descriptor neighbours of
             squared target disagreement
b[q,c,i]   = mean over the frozen K10 matched-random comparators of
             squared target disagreement
```

Both are non-negative binary64 energy quantities. The prospective statistic
retains `K=10`, the frozen exclusions, descriptor definition, and Euclidean
distance. G2 changes no feature, scale, normalization, fold, case, or neighbour
rule.

For each case, without particle deletion:

```text
N[a,q,c] = arithmetic mean over every registered particle n[a,q,c,i]
B[q,c]   = arithmetic mean over every registered particle b[q,c,i]
```

For family `g` and fold `f`, `L[f,g]` is the complete registered set of
lineages in that cell and `C[f,g,l]` is the complete registered set of cases
in lineage `l`. Every required family-fold cell and every registered lineage
must be non-empty. Define the balanced linear aggregation operator

```text
W(x) = mean over 6 folds f
         mean over 4 families g
           mean over lineages l in L[f,g]
             mean over cases c in C[f,g,l] of x[c]
```

Thus particles are equal only within their case, cases are equal within their
lineage, and lineages, families, and folds are exactly equal at their respective
levels. This prevents a lineage with more registered cases from dominating the
point estimand. The lineage-first bootstrap preserves that hierarchy; no
outcome-dependent lineage or case weight is permitted.

## 3. Exact zero branches

For finite non-negative binary64 particle primitives `U,V`, define
`POINTWISE_RATIO_BRANCH(U,V)`:

1. `V > 0`: return the finite numeric value `U/V` (including `U=0 -> 0`);
2. `V == 0 and U == 0`: numeric value is null and status is
   `NO_TARGET_CONTRAST_NOT_EVALUABLE`;
3. `V == 0 and U > 0`: numeric value is null and status is
   `POSITIVE_OVER_ZERO_ADVERSE_UNBOUNDED`;
4. negative or non-finite input: `INTEGRITY_FAILURE`.

There is no epsilon, tolerance, clipping, deletion, or outcome-dependent
branch. JSON uses null, never NaN or infinity.

For Candidates B, C, and D, division occurs only after aggregation. Their
`AGGREGATE_RATIO_BRANCH(U,V)` is:

1. `V > 0`: return the finite numeric value `U/V`;
2. `V == 0`: numeric value is null and status is
   `NO_AGGREGATE_RANDOM_CONTRAST_NOT_EVALUABLE`, while an auxiliary flag
   distinguishes `U==0` from `U>0`;
3. negative or non-finite input: `INTEGRITY_FAILURE`.

This aggregate rule implements the user-mandated rule that a zero aggregate
random-disagreement denominator is NOT_EVALUABLE and must never auto-PASS.

## 4. Frozen candidate set

### Candidate A — pointwise ratio with explicit zero branches

Apply `POINTWISE_RATIO_BRANCH(n[a,q,c,i], b[q,c,i])` particlewise, then take the
arithmetic mean within case and `W` across the frozen hierarchy. A required 0/0 row
propagates NOT_EVALUABLE; a required positive/0 row propagates the adverse
unbounded status. No particle may be dropped. Candidate A preserves the most
literal pointwise interpretation but has no unique continuous extension at
`(0,0)`.

### Candidate B — globally case-equal ratio of aggregates

```text
U_B = arithmetic mean over every formal case c of N[a,q,c]
V_B = arithmetic mean over every formal case c of B[q,c]
D_B = AGGREGATE_RATIO_BRANCH(U_B,V_B)
```

Candidate B retains every particle and case and is invariant to an isolated
0/0 particle or case whenever the total denominator remains positive. It does
not correct unequal family or fold case counts and therefore is tested for
family/fold dominance.

### Candidate C — family/fold case-equal ratio of balanced aggregates

```text
U_C = W(N[a,q,.])
V_C = W(B[q,.])
D_C = AGGREGATE_RATIO_BRANCH(U_C,V_C)
```

The ratio is taken once, after separately applying the identical linear
case/family/fold hierarchy to numerator and denominator. It is **not** the mean
of case ratios or family-fold ratios. Consequently, an isolated zero particle,
case, or family-fold denominator does not cause singularity while other
registered evidence keeps `V_C>0`; a zero total `V_C` remains NOT_EVALUABLE.

### Candidate D — target-scale-normalized absolute disagreement

For a non-negative, outcome-independent, prospectively specified squared target
scale `Q2[q,c]`, define

```text
U_D = W(N[a,q,.])
V_D = W(Q2[q,.])
D_D = AGGREGATE_RATIO_BRANCH(U_D,V_D)
```

Candidate D is eligible only if `Q2` is available before any target access,
transforms covariantly as squared target amplitude, has a unique
componentwise physical/statistical justification, and supplies a defensible
gate without calibration to consumed outcomes. A fixed arbitrary scale or an
actual-target RMS/quantile scale is prohibited. Candidate D is also audited for
loss of the original neighbour-versus-random interpretation.

No fifth candidate may be added in response to a synthetic outcome. A purely
mathematical correction to A--D requires a prospective erratum committed before
rerunning any affected fixture.

## 5. Synthetic-only fixtures frozen before execution

Fixtures use exact rational primitives parsed from integer numerator and
positive denominator fields. Binary64 conversion, when exercised, must be
round-to-nearest-even and audited against the exact result. Each listed case is
its own lineage unless stated otherwise. Minimal algebraic fixtures declare
their active fold/family cells explicitly; S12 exercises unequal family size,
and the bootstrap fixture expands the construction to all six folds and four
families. `Q2=1` unless stated otherwise. No fixture may be revised after any
candidate output is observed.

| ID | Frozen perturbation and required purpose |
|---|---|
| S1 | Two cases, each with particles `(N,B)=(1,1),(3,1)`: all positive; A/B/C/D value `2`. |
| S2 | Two cases with particles `[(0,0),(1,1)]` and `[(1,1),(1,1)]`: isolated 0/0; A is NOT_EVALUABLE, B=C=`1`, D=`3/4`. |
| S3 | Four particles total, one `(1,0)` and three `(1,1)`: A adverse-unbounded, B=C=`4/3`, D=`1`. |
| S4 | Cases `[(0,0),(0,0)]` and `[(1,1),(1,1)]`: multiple zero particles; A NOT_EVALUABLE, B=C=`1`, D=`1/2`. |
| S5 | Single case `[(1,0),(1,0)]`: A adverse-unbounded, B=C NOT_EVALUABLE, D=`1`. |
| S6 | Cases `[(1,0),(1,0)]` and `[(1,1),(1,1)]`: A adverse-unbounded, B=C=`2`, D=`1`. |
| S7 | Two active family-fold cells containing respectively `(1,0)` and `(1,1)`: A adverse-unbounded, B=C=`2`, D=`1`; C must not divide within each cell. |
| S8 | Constant target, all `(0,0)` and `Q2=0`: all candidates NOT_EVALUABLE; zero may not be called perfect. |
| S9 | S1 multiplied by squared amplitude `alpha^2=9`, including `Q2`: every candidate remains `2`; `alpha=0` is separately S8. |
| S10 | One case `(N,B)=(1,2^-100)`: A=B=C=`2^100`, finite and unbounded as `B->0+`; D=`1`. |
| S11 | Case 1 has one `(9,1)` particle; case 2 has three `(1,1)` particles: A=B=C=D=`5`; forbidden particle pooling would give `3`. |
| S12 | Family 1 has one `(9,1)` case; family 2 has three `(1,1)` cases: B=`3`, C=`5`, A and D=`5`; duplicating cases within the large family must not change C. |
| S13 | Three cases with `(N,B)=(100,1),(1,1),(1,1)`: all candidates `34`; finite outlier influence is monotone and disclosed. |
| S14 | SS has `(0,1)`: every candidate SS statistic is exactly zero. |
| S15 | MS has `(0,1)`: every candidate MS statistic is exactly zero. |
| S16 | SS and MS both `(0,1)`: both statistics zero; relative rescue NOT_EVALUABLE. |
| S17 | SS `(0,1)`, MS `(1,1)`: relative rescue NOT_EVALUABLE with auxiliary worsening flag. |
| S18 | SS `(1,1)`, MS `(0,1)`: point relative ratio zero and reduction one. |

Each A--D × S1--S18 row records definedness, status, finite numeric value if
any, continuity class, monotonicity, amplitude invariance, particle/case/family/
fold weighting, bootstrap and paired-comparison compatibility, zero-baseline
rescue semantics, and preservation of the DNN interpretation. Tests may not be
changed after observing their output.

## 6. Frozen selection rule

The selection matrix has these twelve predeclared criteria, each rated exactly
`PASS`, `CONDITIONAL`, or `FAIL`:

1. realistic isolated-zero definedness;
2. no arbitrary epsilon;
3. dimensionless value or independently justified scale;
4. target-amplitude invariance;
5. case-equal compatibility;
6. family/fold equal compatibility;
7. lineage-first cluster-bootstrap compatibility;
8. paired SS/MS compatibility;
9. explicit and interpretable zero semantics;
10. preservation of neighbour-versus-random disagreement meaning;
11. no particle or case deletion;
12. no singularity caused by an isolated exact zero.

All twelve are hard requirements for the primary metric; `CONDITIONAL` does not
pass a hard requirement. There is no weighted score. A candidate may remain a
named diagnostic sensitivity if it fails. The primary metric is the sole
candidate rated `PASS` on all twelve and satisfying every mandatory S1--S18
expectation. If more than one candidate passes, choose in this frozen tie order:
greater preservation of the random-baseline meaning, then stronger lineage/
family/fold equality, then fewer non-evaluable isolated-zero fixtures, then
fewer auxiliary frozen inputs, then lexical candidate ID. If none passes,
terminate
`MSO02C_G2_ZERO_SAFE_DNN_METRIC_NOT_ESTABLISHED`.

## 7. Prospective absolute gate derivation

If the selected statistic is a ratio of squared-disagreement aggregates with
`0=perfect` and `1=random-equivalent`, its independently derived absolute
identifiability boundary is

```text
TAU_ABS = 1
```

because `D<1` is exactly the claim that descriptor-neighbour squared target
disagreement is lower than matched-random disagreement under the identical
balanced hierarchy. The prospective absolute gate requires both the point
estimate and the metric-family, three-component simultaneous one-sided 95% UCB
to be strictly `<1`. Equality is random-equivalent and does not qualify. This
is a semantic null boundary, not an arbitrary practical margin; G2 claims no
independently justified half-RMS or other margin. It is fixed from the original
random-baseline interpretation and not from a synthetic acceptance rate or any
MSO-02B value.

The synthetic audit must confirm that the selected statistic actually retains
that interpretation and is invariant under S9. If not, or if Candidate D is
selected without an equally independent scale-specific boundary, terminate
`MSO02C_G2_ZERO_SAFE_METRIC_IDENTIFIED_BUT_ABSOLUTE_GATE_NOT_JUSTIFIED`.

## 8. Relative rescue and zero-arm semantics

For positive formal statistics, retain the original practical-significance
philosophy:

```text
point D_MS / D_SS <= 0.80
simultaneous one-sided 95% UCB <= 0.90
```

For an energy-ratio statistic, 0.80 remains exactly a 20% reduction of the
random-normalized squared-disagreement estimand; it is not claimed to be a 20%
RMS reduction. This justification, not prior observed performance, controls
retention of the threshold.

Zero branches are frozen prospectively:

- `D_SS=0` for any required component: relative rescue status is
  `RELATIVE_RESCUE_NOT_EVALUABLE_ZERO_SS_BASELINE`, whether `D_MS` is zero or
  positive; an auxiliary deterministic worsening flag may be true but cannot
  replace the inferential status;
- `D_SS>0,D_MS=0`: point ratio is zero. It is eligible only under
  `EXACT_ZERO_MS_DOMINANCE`, requiring every otherwise-valid paired bootstrap
  replicate to have `D_SS>0,D_MS=0`; then UCB is exactly zero. Otherwise the
  relative gate is NOT_EVALUABLE;
- no absolute-difference margin is invented in G2.

## 9. Prospective bootstrap and multiplicity semantics

Fresh H-MSO-01R will freeze 10,000 target-blind paired draws before target
access. For each arm/component and each draw:

1. within every family×fold stratum, resample lineages with replacement;
2. for each selected lineage occurrence, resample its complete cases with
   replacement using the frozen case multiplicities;
3. never resample particles within a case;
4. recompute case `N_c,B_c`, the balanced numerator and denominator aggregates,
   and their ratio from the draw multiplicities;
5. use identical draw identities for SS/MS and all three components;
6. never bootstrap precomputed pointwise or case ratios.

Empty required cells, non-finite terms, or a zero total random denominator make
that replicate degenerate; it is never deleted and redrawn. More than 200 of
10,000 degenerate draws, or fewer than two valid draws, make the metric family
NOT_EVALUABLE. Otherwise use all valid draws with a common three-component
valid-draw mask. For component `q`, let `theta_q` be the point, `theta_bq` its
valid bootstrap values, and `se_q=sample_sd(theta_bq,ddof=1)`. For an upper
bound use

```text
T_b = max_q ((theta_q - theta_bq) / se_q)
k   = ceil(0.95 * n_valid) - 1       # zero-based, after ascending sort
crit = max(0, sorted(T)[k])
U_q = theta_q + crit * se_q
```

For a lower bound reverse the point/bootstrap subtraction and use
`L_q=theta_q-crit*se_q`. Absolute bounds operate on the direct statistic scale.
Positive/positive relative rescue operates on `log(D_MS/D_SS)` and exponentiates
the bound. A zero standard error is accepted only when every valid draw equals
the point, in which case its studentized contribution is zero and bound equals
point; otherwise the family is NOT_EVALUABLE. No refit, neighbour reselection,
feature change, or normalization recomputation occurs inside bootstrap.

## 10. Prospective amendment gate

Only after the scripts independently verify the frozen fixture expectations,
selection matrix, threshold meaning, zero branches, and bootstrap compatibility
may G2 create
`00_project_contract/amendments/ca_mso01_zero_safe_dnn_semantics.md`.
The amendment must state:

- old H-MSO-01 remains permanently NOT_EVALUABLE;
- the new hypothesis is H-MSO-01R;
- consumed MSO-02B and G1 evidence had already been seen, but no real candidate
  performance was read or computed in G2;
- the exact selected statistic, hierarchy, zero semantics, gates, bootstrap,
  multiplicity, K10, exclusions, and unchanged non-DNN gates;
- no epsilon, case deletion, feature/scale change, consumed replay, or fresh
  execution occurred.

Successful freezing sets only
`H_MSO01R_FRESH_REQUALIFICATION_ELIGIBLE=true`. H-MSO-01R is not executed. Its
future evidence must use a completely fresh 384-case atlas (96 per family),
zero lineage overlap, fresh target-blind SS/MS freeze, folds, normalization,
paired bootstrap, and only then target access.

## 11. Required artifacts, terminal states, and stop boundary

Required outputs:

```text
06_experiments/mso02c/g2/synthetic_metric_stress_tests.csv
06_experiments/mso02c/g2/candidate_metric_selection_matrix.csv
06_experiments/mso02c/g2/zero_semantics_audit.csv
06_experiments/mso02c/g2/aggregation_semantics_audit.csv
06_experiments/mso02c/g2/bootstrap_compatibility_audit.csv
06_experiments/mso02c/g2/threshold_derivation_report.md
07_reports/mso02c_g2_zero_safe_metric_selection_report.md
08_manifests/mso02c_g2_manifest.json
08_manifests/mso02c_g2_status_ledger.json
```

If all gates pass, also create
`00_project_contract/amendments/ca_mso01_zero_safe_dnn_semantics.md` and set:

```text
MSO02C_DNN_DEGENERACY_ATTRIBUTED_AND_ZERO_SAFE_REQUALIFICATION_CONTRACT_FROZEN
H_MSO01R_FRESH_REQUALIFICATION_ELIGIBLE = true
```

Otherwise use exactly one of the two authorized failure terminal states from
the user instruction. The final report answers all 23 required questions.
Completion uses the exact commit message
`MSO-02C G2: freeze zero-safe DNN requalification semantics`, then verifies
`main`, clean tree, no remote, and no push. In every terminal state, stop before
consumed replay, H-MSO-01R, MSO-03, or learning.
