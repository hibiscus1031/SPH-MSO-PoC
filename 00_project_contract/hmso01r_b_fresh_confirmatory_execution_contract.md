# H-MSO-01R-B fresh confirmatory multiscale identifiability requalification execution contract

Status: `FROZEN_PROSPECTIVELY_BEFORE_FIRST_FRESH_TARGET_OR_REFERENCE_ACCESS`.

This contract is the complete execution boundary for `H-MSO-01R-B`, the formal scientific-target stage of the new prospective hypothesis `H-MSO-01R`. It preserves every frozen scientific value and resolves only the unavoidable composition of the CA-MSO-01 Candidate C amendment with the already-frozen non-DNN H-MSO-01 gate. It does not repair, replace, reinterpret, or reopen any historical verdict.

## 1. Permanent history, Git handoff, and self-binding rule

The following historical states are permanent:

- `MSO02B_PAIRED_PRELEARNING_IDENTIFIABILITY_REQUALIFICATION_NOT_EVALUABLE`;
- `H_MSO01_MULTISCALE_IDENTIFIABILITY_RESCUE_NOT_EVALUABLE`.

The R-A release-order placeholder is resolved only by `08_manifests/hmso01r_a_git_handoff.json`: `RECORDED_BY_FINAL_GIT_COMMIT_AND_HANDOFF -> 9048eff137001e5f644575bd02c3856b4f4ac532`. The old R-A report, manifest, and status ledger must not be edited. The authorized parent is `HMSO01R_A_FINAL_COMMIT=9048eff137001e5f644575bd02c3856b4f4ac532`, branch `main`, remote none, clean working tree, and push false.

This contract, the import/role registries, both executables, the release finalizer, the passing executable-bound synthetic preflight, and `08_manifests/hmso01r_b_pre_target_freeze.json` must be committed together with message `H-MSO-01R-B: freeze fresh confirmatory execution` before first target/reference access. The synthetic preflight is run target-blind from the exact candidate evaluator bytes and then included in the freeze/commit; it reads no real target, reference, or observable payload. A file cannot contain the hash of the commit that contains itself. Therefore the freeze uses the prospective sentinel `DISCOVERED_AT_FIRST_TARGET_ACCESS_FROM_CLEAN_HEAD`; the target builder must discover the then-current clean `main` HEAD, prove that every frozen input/executable/preflight is the exact Git blob listed by the freeze, and record that commit as `HMSO01R_B_PRE_TARGET_COMMIT` in `target_access_ledger.json`. A placeholder is never accepted as an execution identity. Target/reference access is forbidden unless the discovered commit exists, differs from the R-A parent, is on `main`, the tree is clean, and no remote exists.

The final release commit cannot self-bind either. The report, manifest, and status ledger shall use `RECORDED_BY_FINAL_GIT_COMMIT_AND_USER_HANDOFF`; the actual `HMSO01R_B_FINAL_COMMIT` is reported only after the non-amended final commit succeeds. No prior commit may be amended.

The exact required pre-target commit message is `H-MSO-01R-B: freeze fresh confirmatory execution`. The exact required final commit message is `H-MSO-01R-B: fresh confirmatory multiscale identifiability requalification`.

## 2. Authoritative frozen evidence

The release must validate the following complete-file SHA-256 identities before target generation and again before verdict publication. Historical manifests and ledgers in this table are verified as opaque bytes/Git blobs only; their scientific-outcome payloads must not be parsed or used. A mismatch terminates as `HMSO01R_B_FROZEN_EVIDENCE_IDENTITY_FAILURE` and no scientific verdict may be emitted.

| Identity | Path | SHA-256 |
|---|---|---|
| MSO-00 | `08_manifests/mso00_manifest.json` | `c00261aac588f8b1f34e0a606259512ea8d45cf3e9cb0a10f40ab0970a2f7d95` |
| MSO-01 manifest | `08_manifests/mso01_manifest.json` | `bf2fad0dfaf03db02d21db30c4f35a145187df557dcd60b26a4e0ee7f5348306` |
| MSO-01 ledger | `08_manifests/mso01_status_ledger.json` | `425ad0dd0cf4ba62bd802024d7a3b44243f15ad0cc93f122ed1983cf4eb448ef` |
| MSO-02A manifest | `08_manifests/mso02a_manifest.json` | `c8e8770cda1779041b5b380b7ccec387446c9aa0f82c2b50f4a38655ad968e81` |
| MSO-02A ledger | `08_manifests/mso02a_status_ledger.json` | `f59196a1de2adffbc6ba1eda2c737c628ae63a3caeb88e969b98e3fc36cb7212` |
| MSO-02B manifest | `08_manifests/mso02b_manifest.json` | `94ce69002d714acff2176fc71910e18766f873ed26be7437763eb34762e68fe6` |
| MSO-02B ledger | `08_manifests/mso02b_status_ledger.json` | `cb9864b34c94f4ae022745fa9b6040bd2baaf6bdae7156a3905b22584a268815` |
| MSO-02C G1 manifest | `08_manifests/mso02c_g1_ab_attribution_manifest.json` | `e7652d1e706bd4b4e552973d90dfc4fe1b0fb634fd58328a9fc5331e3ae70dac` |
| MSO-02C G1 ledger | `08_manifests/mso02c_g1_ab_attribution_status_ledger.json` | `d076ef93d145a00bddcf278bd593e9d5971d5b3596f7cea3ac018ebe82375fb1` |
| MSO-02C G2 manifest | `08_manifests/mso02c_g2_manifest.json` | `e7d001f714cdaa0bf1a2d45e5148677fed50ee8628eff6bb2caa22eafaba8c95` |
| MSO-02C G2 ledger | `08_manifests/mso02c_g2_status_ledger.json` | `9d677839d3035ca4a16eb414bf13b958b3fcce9af24caa7416043f3b7b251b1d` |
| CA-MSO-01 | `00_project_contract/amendments/ca_mso01_zero_safe_dnn_semantics.md` | `fec81d9dceeb4edc93b19adf0eb063e564effda81f700ea69174963b75454650` |
| R-A contract | `00_project_contract/hmso01r_a_fresh_requalification_atlas_freeze_contract.md` | `e2aa0c65089121c22af8c408923bdeed1c7eab3bf88c560db8405ccec46607a3` |
| R-A manifest | `08_manifests/hmso01r_a_manifest.json` | `3b182be2bd8a6a2622548ab51f91b363ef9b38b9f3142314f7166516d43776a1` |
| R-A ledger | `08_manifests/hmso01r_a_status_ledger.json` | `d59aaa656da136c9291c8be58b4ae10b9017a9731daebcef96cae06542548bf3` |
| formal atlas | `05_registries/hmso01r_a_formal_fresh_atlas_registry.json` | `7fd7aa6c8415051ad83f0028b75b4684121886cb3645060e4e5c3ac54ebc268a` |
| particle sample | `05_registries/hmso01r_a_formal_particle_sample_registry.json` | `a4b7da1a9f6e4efab7ccbc9ec3bb5e4235a82aef30ce64017895df05ab1c2b01` |
| six folds | `05_registries/hmso01r_a_lineage_fold_registry.json` | `941edc1827e55ca2ffec1125734e0791786e2d157c3aa873ae0a24f520f8815b` |
| SS schema | `06_experiments/hmso01r_a/ss_observable_schema_identity.json` | `2bfe3b7f0b1869cade1e9e8d7554eff589c3b017512470b9e8eabf8b18130e70` |
| MS schema | `06_experiments/hmso01r_a/ms_observable_schema_identity.json` | `13a6e83f03576619afa335e69df737547947501c63dd691066119fd9d2823fb3` |
| normalization | `06_experiments/hmso01r_a/fold_normalization_registry.json` | `d9842a2ba2b347d0aeb1e950118bf62d3c89d0f80639a5f475cd9c5acb683018` |
| descriptor geometry | `06_experiments/hmso01r_a/descriptor_geometry_freeze.json` | `1641f0a68bf59a9f3f949e8ee058971db154d0f68eccf6e23efe6122f4067768` |
| descriptor identities | `06_experiments/hmso01r_a/descriptor_neighbor_identities.npz` | `1d98e7c2038c9d6b7391b1ab953084dfafb47ef3ade7c62815c9f676694408b4` |
| random registry | `05_registries/hmso01r_a_random_baseline_identity_registry.json` | `cc6fa10eb77fbbd7a9b8db00d9214ff971a351fbbefdfee38b0c7db898bace99` |
| random identities | `06_experiments/hmso01r_a/random_baseline_identities.npz` | `74268059f33c5fc9ec885ccb1ef7f61b22120f4eac7e9862bab6fddc844d8b07` |
| bootstrap registry | `05_registries/hmso01r_a_bootstrap_registry.json` | `7e1f2686b468cd47eb18ade38e9eb74c389e72e600fc5a89831035925cc278da` |
| bootstrap draws | `06_experiments/hmso01r_a/bootstrap_draws.npz` | `3a5853ce6b353c8c2584b0f95651904fb1506a0a3e3af6985981374789d4667e` |
| coverage geometry | `06_experiments/hmso01r_a/coverage_geometry_freeze.json` | `a51fd951bcad7f32a228229176055161b8117e9a266cdd4a99975bea7be447e4` |
| observable store | `06_experiments/hmso01r_a/observable/hmso01r_a_observable_store.npz` | `65ca1a7fea58248207fc5a22e14855b4a84c392c7ef17cefdf2d396687cc38cd` |

The pre-target freeze is the machine-readable authority for these identities and for the import/vendor and executable identities created for R-B. Every regular frozen artifact must record path, file SHA-256, Git blob OID, Git-blob-content SHA-256, role, stage, source, and consumption status. At first access, file bytes, blob bytes, and the freeze must all agree.

## 3. Historical-result firewall and R-A evidence limitation

Repository-wide grep, `rg`, semantic search, or directory traversal for DDO, PIO, or MSO historical results, reports, metrics, checkpoints, or outcome text is prohibited. Only the hash-bound sources, explicitly whitelisted provenance files, R-A frozen artifacts, and authoritative contracts/amendments may be opened. Any accidental match must be logged completely by path, command class, time, and whether payload text was exposed; no old numerical outcome may be used.

R-A's Candidate C CSV preflights are frozen eligibility evidence, but they are summary outputs: they do not bind the R-B evaluator executable and do not provide a direct call-level trace proving every R-B aggregation/division and draw consumption. R-A's firewall JSON is an instrumented governance counter, not an operating-system access trace; it proves only the actions covered by its instrumentation. These evidentiary limits do not alter any frozen scientific value or R-A status.

Consequently, before first target/reference access, R-B must run the exact committed `run_hmso01r_b_formal.py` in synthetic-only preflight mode and write `candidate_c_implementation_preflight.json`. That preflight must bind its own executable SHA-256 and Git blob; exercise scalar/vector, isolated 0/0, isolated positive/0, zero aggregate, positive aggregate, zero SS, exact-zero MS, hierarchical equal weights, all 10,000 frozen draw identities, exactly 201 degenerate plus 9,799 valid draws, and exactly 9,999 degenerate plus one valid draw; prove that both threshold constructions are NOT_EVALUABLE for all three components; confirm no actual target/observable payload was read; and directly record zero pointwise divisions, expected final divisions, per-draw re-aggregation, paired-arm identity, and zero epsilon/clipping/deletion. Target execution and formal analysis must additionally emit direct target-access, division, bootstrap-consumption, and firewall ledgers. A missing or failing B preflight forbids target access.

A scoped target-blind pre-target audit recomputed only the frozen lambda-1 base SPH operator matrix identities for the 384 R-A cases. It found 384/384 matches with ordered digest `4cf2df0d4b4bcf25ee497e89a12f6edb07bdeae7b195f5ca100bedef79467e40`. It performed zero analytical continuum/reference evaluations, defect generations, target reads/writes, or historical outcome reads. This is a base-operator identity audit, not first fresh target/reference access, and must be recorded as such in the freeze and access ledger.

## 4. Authorization and absolute stop boundary

Authorized activities are `NEW_SCIENTIFIC_TARGET_EVALUATION`, `TARGET_GENERATION`, `TARGET_READ`, `REFERENCE_OPERATOR_READ`, `DNN_CANDIDATE_C_EVALUATION`, `CONDITIONAL_VARIANCE_EVALUATION`, `ORACLE_FIT`, `COVERAGE_EVALUATION`, `PAIRED_RESCUE_EVALUATION`, `BOOTSTRAP_INFERENCE`, and `H_MSO01R_VERDICT`.

Forbidden activities are old pointwise-DNN formal evaluation, neural/attention/Transformer models, learned operators, optimizers, training, time integration, solver-in-loop, rollout, sealed-test access, and ARC access. Here DNN always means Descriptor Nearest-Neighbour. The stage stops immediately after release of the H-MSO-01R verdict and eligibility decision. It must not execute MSO-03, neural, attention, or training under any outcome.

## 5. Formal population, no second chance, and target definition

Use all and only the R-A formal atlas: exactly 384 cases, 96 each in F1-F4; the frozen 128 particles per case; the frozen lineages, families, folds, particle-state hashes, disorder, support scales, and row identities. No reserve, case replacement, deletion, addition, lineage change, seed redraw, fold change, particle resampling, or target-dependent resampling is allowed. At first target access, `CASE_REPLACEMENT_AUTHORIZED=false` permanently for H-MSO-01R.

For exactly three primary components—`density_rate`, `pressure_gradient_acceleration`, and `viscosity_laplacian_acceleration`—construct only

`d_h* = R_h L(q*) - L_h(R_h q*)`,

with `L_h` exactly the frozen lambda `1.00` base SPH operator and the sign reference-minus-base. Lambda 0.75, 1.25, and 1.50 are input-representation scales only. Defects `d_0.75h*`, `d_1.25h*`, and `d_1.50h*` are forbidden. `interpolation_density` is diagnostic only; `total_acceleration` is derived diagnostic only; neither may determine a verdict. `HIGH_RESOLUTION_SPH_IS_TRUTH=false`.

After first target access there is no second chance: no new cases, reserves, lineages, lambdas, features, feature deletion, PCA, whitening, distance, K, random baseline, normalization, folds, bootstrap draws, metrics, thresholds, oracle, or component deletion may alter H-MSO-01R. Any future redesign requires a separately authorized hypothesis.

## 6. Physically separated target/reference execution and qualification

Before generation, verify and record the DDO source HEAD, source paths/hashes, import/vendor hashes, and frozen base-operator hashes. Source implementation is immutable. The target builder may read only the formal case/particle registries, analytical field definitions, physical constants, lambda-1 operator, and reference definitions. It may not read the SS/MS feature matrix, descriptor-neighbour outcomes, Candidate C/CVAR/oracle outcomes, or any prior scientific metric. Target/reference artifacts live only in `06_experiments/hmso01r_b/target_ref/`; the R-A observable store is read-only.

The target store must bind `formal_case_index`, `case_id`, `particle_id`, `particle_state_hash`, `lineage`, `family`, `fold`, all three primary target arrays, and numerical/reference uncertainty metadata. Even if full-case targets are generated, formal analysis joins only the frozen particle sample.

All 384/384 cases must pass analytical derivative/reference consistency, finite values, sign convention, lambda-1 base identity, repeatability, component identity, component closure, numerical/reference uncertainty, and target/particle-state join identity before scientific analysis. Any failure forbids reserve use and terminates `HMSO01R_B_TARGET_REFERENCE_QUALIFICATION_NOT_COMPLETE` with `H_MSO01R_STATUS=NOT_EVALUATED_DUE_TO_TARGET_QUALIFICATION_FAILURE`. A target/observable mismatch terminates `HMSO01R_B_TARGET_OBSERVABLE_PAIRING_FAILURE`. Neither condition may be called a scientific FAIL.

Target, SS, and MS must match row-for-row on case id, particle id, particle-state hash, lineage, family, and fold. The only formal intervention is representation. Hash the R-A observable store before generation, after generation, after formal analysis, and before release; every hash must equal `65ca1a7fea58248207fc5a22e14855b4a84c392c7ef17cefdf2d396687cc38cd`.

## 7. Frozen representations, normalization, neighbours, random baseline, and coverage

SS remains exactly 39 dimensions and MS exactly 110. Retain constant, duplicate, and IQR-degenerate columns. No feature may be added or deleted; PCA, whitening, correlation pruning, feature selection, learned embeddings, and distance redesign are forbidden.

Use only the frozen per-arm, training-fold-only median/IQR normalization. Exact-zero IQR uses divisor one and retains the column. Never refit normalization or use targets to alter observable scaling.

Use the six lineage-held-out folds; normalized Euclidean descriptor distance; K=10; frozen same-case, same-lineage, and seed exclusions; frozen deterministic tie order; and the frozen candidate pools and neighbour identities. K=5/20 cannot be searched or substituted. Use the exact frozen matched-random identities, identical for SS/MS per query; no RNG draw or target-dependent rematching is allowed. Coverage uses only the frozen R-A observable-space machinery and reports overall, familywise, and foldwise values. It is a geometry gate and can never substitute for an identifiability metric.

## 8. Candidate C: sole formal DNN statistic and canonical status

Candidate C from CA-MSO-01 is the only formal DNN statistic. For query particle `i`, `N_i` is the mean over the frozen K=10 descriptor neighbours of squared target disagreement; `B_i` is the mean over the frozen K=10 matched-random comparators. Use scalar square for density and squared Euclidean norm for vector components, all in float64. Epsilon, clipping, flooring, pointwise division, and row/group deletion are forbidden.

Apply equal weights in the exact order particle to case, case to lineage, lineage to family, and family to fold. Only after both aggregates are complete perform one division: `D=W(N)/W(B)`. Isolated `N_i=B_i=0` and `N_i>0,B_i=0` remain present. If final `W(B)>0`, D is evaluable. If `W(B)=0`, the authoritative CA-MSO-01 canonical status is `NO_AGGREGATE_RANDOM_CONTRAST_NOT_EVALUABLE`. The current-instruction string `DNN_NOT_EVALUABLE_ZERO_AGGREGATE_RANDOM_BASELINE` is a recorded alias only and must normalize to the CA status; it is never a distinct branch. If `D_SS=0`, the relative status is `RELATIVE_RESCUE_NOT_EVALUABLE_ZERO_SS_BASELINE`. No epsilon or absolute-difference fallback may rescue either branch.

Absolute Candidate C requires strict point `D<1` and three-component simultaneous one-sided 95% `UCB(D)<1`; equality does not qualify. Evaluate and report this gate for both arms, but the unchanged absolute-identifiability composite consumes the MS gate. Relative rescue requires `D_MS/D_SS<=0.80` and simultaneous UCB `<=0.90`.

## 9. Prospective Candidate C composition with the unchanged H3 gate

CA-MSO-01 replaced the DNN statistic but did not redesign H3. To remove the only unavoidable ambiguity before target access, the following mapping is frozen:

1. The single Candidate C MS absolute gate replaces both legacy pointwise DNN-median and DNN-p90 absolute inputs. Those old metrics and gates are not computed, and Candidate C enters the conjunction only once.
2. Candidate C relative point/UCB replaces the legacy DNN-p90 rescue input.
3. Candidate C replaces the old DNN-median input in the nonworsening guard, preserving its exact margins and stability rule. Define `dimensionless_floor=128*eps64` and call the ratio stable only when evaluable `D_SS > 100*dimensionless_floor`. For evaluable positive `D_SS`, require `D_MS-D_SS<=0.02` and, when stable, also `D_MS/D_SS<=1.05`; when positive but not stable, only the unchanged absolute 0.02 leg applies. No epsilon is added. `D_SS=0` remains NOT_EVALUABLE under CA-MSO-01 and cannot reach this guard.
4. Fold-level Candidate C replaces the legacy DNN-p90 leg in the three-effect reversal rule. A component fails the rule if any otherwise-valid fold has Candidate-C MS worse than SS by more than the frozen dimensionless floor (`128*eps64`), CVAR MS worse than SS by more than that floor, and oracle-NRMSE MS worse than SS by more than that floor, simultaneously. All other reversal semantics are unchanged.

No other gate, margin, confidence rule, fold rule, or non-DNN input changes.

## 10. Bootstrap and simultaneous inference

Consume all and only the R-A 10,000 fresh unique paired lineage-first cluster draws; no redraw is permitted. Each replicate must independently reconstruct balanced `W(N)` and `W(B)` and then perform one aggregate division. Bootstrapping a precomputed ratio is forbidden. Record 10,000/10,000 draws consumed, unique-draw identity, paired SS/MS identity, aggregate-denominator-degenerate draw count, evaluable draw count, and every Candidate C division. More than 200 degenerate Candidate C draws or fewer than two valid draws makes that DNN metric family NOT_EVALUABLE.

Use the frozen one-sided 95% maximum-studentized simultaneous correction across the three primary components within each metric family. Pointwise intervals cannot replace simultaneous bounds. Paired positive ratios use the frozen paired log-ratio inference without outcome-dependent epsilon. The frozen confidence level, multiplicity scope, nearest-rank critical value, zero-SE handling, and all non-DNN degeneracy/effective-lineage rules are unchanged. `all_required_bound_procedures_executed=true` (and the compatibility alias `all_required_bounds_computed=true`) means that all 57 preregistered `(metric_family, component)` procedures ran and emitted their required status rows; it does not claim that every row has an evaluable numeric bound. `all_required_bounds_evaluable` is true only when every row is `EVALUABLE`, with paired Candidate-C `EXACT_ZERO_MS_DOMINANCE` counted as numerically evaluable because its exact point and bound are both zero.

## 11. Frozen non-DNN estimators and exact gates

Conditional variance uses the same frozen K=10 target-blind neighbourhoods, target transform, unbiased within-neighbour trace estimator, development total-trace normalization, case/family/fold equal weighting, and simultaneous UCB. The simple non-neural oracle family remains exactly KNN averaging K={5,10,20}, ridge with alpha 1, and degree-two polynomial ridge on the frozen seven-column invariant subset, with identical folds, nested lineage-held-out selection, target scaling, candidate tie order, selection loss, and SS/MS protocol. RF, boosting, neural, GNN, Transformer, attention, and neural operators are forbidden.

For each component, unchanged MS absolute gates are:

- Candidate C point `<1` and simultaneous UCB `<1` (the sole DNN input);
- CVAR point `<=0.25` and simultaneous UCB `<=0.35`;
- oracle NRMSE point `<=0.60` and simultaneous UCB `<=0.70`;
- improvement over the identical mean predictor point `>=25%` and simultaneous LCB `>=15%`;
- every-family NRMSE point `<=0.85` and no family UCB `>1.00`;
- overall coverage `>=90%` and every-family coverage `>=80%`; and
- all six folds valid and fold-equal, with every other frozen absolute requirement.

For each component, unchanged paired MS/SS rescue gates after the Candidate C mapping are:

- Candidate C point ratio `<=0.80` and simultaneous ratio UCB `<=0.90`;
- CVAR ratio `<=0.80` and simultaneous ratio UCB `<=0.90`;
- oracle-NRMSE ratio `<=0.85` and simultaneous ratio UCB `<=0.95`;
- Candidate C nonworsening by the exact 0.02 absolute and stable 5% relative margins above;
- MS worst-family NRMSE no more than 0.05 above SS and passing its absolute gate;
- MS overall/family coverage passing absolute gates and no corresponding value more than 0.05 below SS;
- no valid fold reversing Candidate C, CVAR, and oracle NRMSE together; and
- simultaneous confidence, six-fold validity, and every other frozen relative requirement.

## 12. Evaluability, component taxonomy, and global decision

For each primary component separately determine `DNN_EVALUABLE`, `CVAR_EVALUABLE`, `ORACLE_EVALUABLE`, `COVERAGE_EVALUABLE`, and `ALL_REQUIRED_FOLDS_VALID`. Every non-DNN overall, family, and fold primitive and every confidence bound must serialize an explicit `{status,evaluable,not_evaluable_mechanism}` leaf. The exact non-DNN mechanisms are `NOT_EVALUABLE_DEVELOPMENT_TARGET_VARIANCE_NONPOSITIVE_OR_NONFINITE`, `NOT_EVALUABLE_ORACLE_SELECTION_PREDICTION_OR_TARGET_RMS_INVALID`, `NOT_EVALUABLE_MEAN_BASELINE_NONPOSITIVE_OR_ORACLE_INVALID`, `NOT_EVALUABLE_COVERAGE_GEOMETRY_INVALID`, `NOT_EVALUABLE_EXCESS_DEGENERATE_OR_INSUFFICIENT_EFFECTIVE_LINEAGE_BOOTSTRAP`, and `NOT_EVALUABLE_UNSTABLE_RATIO_NO_FROZEN_ABSOLUTE_DIFFERENCE_MARGIN`; non-overall improvement rows use `NOT_APPLICABLE_NON_OVERALL_SCOPE`. A non-finite value is permitted only with its specific mechanism; a missing status, a generic silent `NaN`, or conversion of non-evaluability to scientific failure is forbidden.

Preserve the inherited two-side evaluability semantics. `ABSOLUTE_IDENTIFIABILITY_EVALUABLE` is the conjunction of the finite/evaluable Candidate-C, CVAR, oracle, improvement, family, coverage, confidence, and fold inputs actually consumed by the absolute composite. `RELATIVE_MULTISCALE_RESCUE_EVALUABLE` is the conjunction of the finite/evaluable SS/MS Candidate-C, paired Candidate-C, CVAR rescue, oracle rescue, family guard, coverage guard, confidence, nonworsening, and reversal/fold inputs actually consumed by the relative composite. An input that belongs only to the opposite side cannot turn an otherwise evaluable side into FAIL. Compute each side's PASS only from that side's own evaluability and gate conjunction. Then `COMPONENT_EVALUABLE = ABSOLUTE_IDENTIFIABILITY_EVALUABLE AND RELATIVE_MULTISCALE_RESCUE_EVALUABLE`; the consolidated DNN/CVAR/oracle/coverage/fold flags must agree with the corresponding mandatory inputs across both sides. If the component is not evaluable, its status is `H_MSO01R_COMPONENT_NOT_EVALUABLE`; NOT_EVALUABLE must never be called FAIL.

Define `ABSOLUTE_IDENTIFIABILITY_PASS = ABSOLUTE_IDENTIFIABILITY_EVALUABLE AND` the conjunction of all absolute requirements, and `RELATIVE_MULTISCALE_RESCUE_PASS = RELATIVE_MULTISCALE_RESCUE_EVALUABLE AND` the conjunction of all relative requirements. Then `COMPONENT_H_MSO01R_PASS = COMPONENT_EVALUABLE AND ABSOLUTE_IDENTIFIABILITY_PASS AND RELATIVE_MULTISCALE_RESCUE_PASS`.

The exhaustive component taxonomy is:

- non-evaluable: `H_MSO01R_COMPONENT_NOT_EVALUABLE`;
- absolute PASS and rescue PASS: `H_MSO01R_COMPONENT_QUALIFIED`;
- absolute PASS and rescue FAIL: `IDENTIFIABLE_BUT_MULTISCALE_RESCUE_NOT_ESTABLISHED`;
- absolute FAIL and rescue PASS: `RELATIVE_RESCUE_OBSERVED_BUT_ABSOLUTE_IDENTIFIABILITY_NOT_QUALIFIED`;
- absolute FAIL and rescue FAIL: `H_MSO01R_COMPONENT_NOT_QUALIFIED`.

Only three qualified primary components permit `H_MSO01R_MULTISCALE_IDENTIFIABILITY_RESCUE_QUALIFIED`. If all are evaluable but any is not qualified, use `H_MSO01R_MULTISCALE_IDENTIFIABILITY_RESCUE_NOT_QUALIFIED`. If any is NOT_EVALUABLE, use `H_MSO01R_MULTISCALE_IDENTIFIABILITY_RESCUE_NOT_EVALUABLE`; this has priority over scientific failure.

If qualified, only `MSO03_DETERMINISTIC_CLOSURE_BASELINE_ELIGIBLE=true` is granted. Neural training, attention, and learned operators remain unauthorized, and MSO-03 is not executed. If NOT_QUALIFIED or NOT_EVALUABLE, MSO-03 eligibility and every learning route remain false. A NOT_EVALUABLE result must name its most specific mechanism and cannot trigger a metric repair.

## 13. Direct ledgers, firewall counters, and release refusal

The target builder and evaluator must directly record authorized target case evaluations, reference evaluations, target-store reads/writes, Candidate C evaluations, CVAR evaluations, oracle fits, coverage evaluations, paired rescue evaluations, and bootstrap draws consumed. The following prohibited counts must all equal integer zero:

`neural_model_count`, `attention_count`, `transformer_count`, `learned_operator_count`, `optimizer_count`, `training_count`, `time_integration_count`, `solver_in_loop_count`, `rollout_count`, `sealed_test_count`, `arc_access_count`, `target_derived_feature_modification_count`, `target_derived_scale_modification_count`, `target_derived_fold_modification_count`, `target_derived_normalization_modification_count`, `target_derived_metric_modification_count`, `target_derived_gate_modification_count`, `target_derived_oracle_modification_count`, and `case_replacement_after_target_access`.

Release validation must refuse to write a report, manifest, status ledger, or verdict if any required artifact or required field is missing; any input/executable/blob hash differs; target qualification is not exactly 384/384; the target/observable join is not exact; the observable hash changed; dimensions are not 39/110; the B synthetic preflight failed; 10,000 draw consumption/paired identity is not proved; pointwise Candidate-C division is nonzero; expected aggregate divisions are not proved; any mandatory metric/bound/fold status is absent; any prohibited counter is nonzero; or the summary/component/global statuses are internally inconsistent.

The release manifest must register every formal artifact with SHA-256, role, stage, source, and consumption status. The final report must answer all 30 user-required questions explicitly. After committing `H-MSO-01R-B: fresh confirmatory multiscale identifiability requalification`, report the discovered pre-target commit and actual final commit, require branch `main`, clean tree, remote none, push false, and stop immediately. No MSO-03, neural, attention, or training action is authorized by this contract.

## 14. Exact formal artifact set

In addition to this contract, the import manifest, target-role registry, R-A Git handoff, pre-target freeze, target builder, formal evaluator, executable synthetic preflight, and release finalizer, a complete run must produce exactly the following named formal runtime/release evidence (and no old pointwise-DNN substitute):

- `06_experiments/hmso01r_b/target_reference_qualification.csv`;
- `06_experiments/hmso01r_b/target_observable_join_audit.csv`;
- `06_experiments/hmso01r_b/target_access_ledger.json`;
- `06_experiments/hmso01r_b/ss_candidate_c_dnn_metrics.csv`;
- `06_experiments/hmso01r_b/ms_candidate_c_dnn_metrics.csv`;
- `06_experiments/hmso01r_b/candidate_c_paired_rescue_metrics.csv`;
- `06_experiments/hmso01r_b/candidate_c_bootstrap_bounds.csv`;
- `06_experiments/hmso01r_b/candidate_c_division_audit.json`;
- `06_experiments/hmso01r_b/ss_conditional_variance_metrics.csv`;
- `06_experiments/hmso01r_b/ms_conditional_variance_metrics.csv`;
- `06_experiments/hmso01r_b/ss_oracle_metrics.csv`;
- `06_experiments/hmso01r_b/ms_oracle_metrics.csv`;
- `06_experiments/hmso01r_b/coverage_metrics.csv`;
- `06_experiments/hmso01r_b/paired_non_dnn_rescue_metrics.csv`;
- `06_experiments/hmso01r_b/bootstrap_simultaneous_bounds.csv`;
- `06_experiments/hmso01r_b/component_verdicts.csv`;
- `06_experiments/hmso01r_b/formal_summary.json`;
- `06_experiments/hmso01r_b/firewall_audit.json`;
- `06_experiments/hmso01r_b/target_ref/hmso01r_b_target_store.npz`;
- `07_reports/hmso01r_b_fresh_confirmatory_identifiability_report.md`;
- `08_manifests/hmso01r_b_manifest.json`; and
- `08_manifests/hmso01r_b_status_ledger.json`.

The manifest must register this complete set, all prospective inputs/executables, and itself. Because a manifest cannot contain its own SHA-256, its self row uses `FINAL_GIT_BLOB_AT_HMSO01R_B_FINAL_COMMIT`, which the actual non-amended final Git commit and user handoff resolve. No formal checkpoint is authorized or required.

## 15. Exact final-report questions and release handoff

The report must explicitly answer, with componentwise values/statuses rather than merely referring the reader to an artifact:

1. Did 384/384 target/reference cases qualify?
2. Was only the lambda-1 base defect used?
3. Was the fresh observable-store hash unchanged before/after generation, after analysis, and before release?
4. Did SS/MS remain 39/110 dimensions?
5. Was Candidate C never computed pointwise?
6. Was aggregate `W(B)>0` for every component/arm?
7. Did any Candidate C become NOT_EVALUABLE?
8. What are all SS Candidate-C point values and simultaneous UCBs?
9. What are all MS Candidate-C point values and simultaneous UCBs?
10. What are all Candidate-C SS-to-MS ratios and simultaneous UCBs?
11. Which Candidate-C absolute gates passed?
12. Which Candidate-C relative gates passed?
13. What are CVAR SS/MS values, confidence quantities, and rescue results?
14. What are oracle SS/MS NRMSE values, confidence quantities, and rescue results?
15. Did mean-baseline improvement pass, with point values and simultaneous LCBs?
16. Did every worst-family gate pass, with family point/UCB values and paired guard?
17. Did coverage overall, familywise, and foldwise pass, with all values and guards?
18. Were all simultaneous bounds executed with the frozen multiplicity method, scope, and confidence?
19. Is each component evaluable?
20. What is each component's independent absolute sub-verdict: PASS, FAIL, or NOT_EVALUABLE?
21. What is each component's independent relative-rescue sub-verdict: PASS, FAIL, or NOT_EVALUABLE?
22. What is each component's final five-state status?
23. Is global H-MSO-01R QUALIFIED, NOT_QUALIFIED, or NOT_EVALUABLE?
24. Did any target-derived scientific modification occur?
25. Was any neural, attention, Transformer, optimizer, or training action executed?
26. Under QUALIFIED, did MSO-03 receive eligibility only, without execution?
27. Under NOT_QUALIFIED/NOT_EVALUABLE, do MSO-03 and every learning route remain unauthorized?
28. Does old H-MSO-01 remain permanently NOT_EVALUABLE?
29. What are the R-A final, R-B pre-target, and R-B final Git identities, using only the unavoidable prospective final-commit sentinel inside self-bound artifacts?
30. What is the exact final terminal status?

Only after those artifacts validate may a new, non-amended commit with subject `H-MSO-01R-B: fresh confirmatory multiscale identifiability requalification` be created. The handoff must report the actual final commit outside its self-bound contents and confirm `main`, clean tree, no remote, no push. Execution then stops.
