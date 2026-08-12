# MSO-02C DNN degeneracy diagnostic contract

Status: `FROZEN_BEFORE_CONSUMED_EVIDENCE_DIAGNOSTIC_EXECUTION`.

This contract authorizes only **MSO-02C — DNN Degeneracy Attribution and
Prospective Statistical Repair**. It is a diagnostic and prospective-contract
stage, not a new confirmatory experiment. Here and throughout this document,
`DNN` means Descriptor Nearest-Neighbour, never a neural network.

## 1. Immutable handoff and source authorization

The parent state is local commit
`79e6e86a983e56fb889ab39349da0fc53ddbe880` on `main`, with a clean working
tree, no Git remote, and no push. The additive handoff is
`08_manifests/mso02b_git_handoff.json`. The placeholder in the old MSO-02B
manifest is not rewritten.

The user authorization is the attachment named
`继续现有项目： /Users/xiejinbo/Documents/SPH-MSO-PoC 当前冻结终态： MSO02B_PAIRED_PRELEARNING…`,
stored outside this repository at
`/Users/xiejinbo/.codex/attachments/120a0658-18df-46b3-9696-e80f7e19063b/pasted-text.txt`,
with complete-file SHA-256
`8df06f5e080a56ff06f8e5827fe9399e82d9e301698cc09cff4c20e323ea94e7`.

The following MSO-02B identities are immutable diagnostic inputs:

| Input | SHA-256 |
|---|---|
| `00_project_contract/mso02b_paired_prelearning_identifiability_execution_contract.md` | `e7a73313fd3ff65c6126267f2e940f071d35fd12c4f93ee28c097309d56bfd0e` |
| `05_registries/mso02b_analysis_semantics_registry.json` | `b271864a62800ea502d1f21621b3d937088f6809c0d31301e6effac96d203ce5` |
| `05_registries/mso02b_formal_particle_sample_registry.json` | `98ff5716e3adbbaac4cac4899e76eb4d61d4e194396fe4e37041a94abe0ca229` |
| `06_experiments/mso02b/run_mso02b_formal.py` | `55b0b63eb2c99364c8a2e96c75191a50707e93357f7039bd9edfdcb7c7c831b7` |
| `06_experiments/mso02b/target_ref/mso02b_target_store.npz` | `16f1ebd26d0d1aa74dd0892dfe2feb0967024f9219dd8c102c8faafc934f81e2` |
| `06_experiments/mso02b/target_access_ledger.json` | `4fcf03ad4dd45c46a6537b2286508e01eb83352a16926656b12b1fdfad2d76e8` |
| `06_experiments/mso02b/mso02b_formal_summary.json` | `33b83a84c24330f90ad4f96089bca9a4f00f38b1923a3aec9e58975292924135` |
| `07_reports/mso02b_identifiability_requalification_report.md` | `b883523e0d9d8d0db3ea73aad6a567db5f83a6292f7b155243abbd0afad1ba8d` |
| `08_manifests/mso02b_manifest.json` | `94ce69002d714acff2176fc71910e18766f873ed26be7437763eb34762e68fe6` |
| `08_manifests/mso02b_status_ledger.json` | `cb9864b34c94f4ae022745fa9b6040bd2baaf6bdae7156a3905b22584a268815` |

All twelve checkpoint identities and every other consumed artifact identity are
authoritatively inherited from the immutable MSO-02B manifest. Before any
diagnostic load, the MSO-02C executable must verify the complete-file hashes of
every file it will consume. A mismatch terminates as
`MSO02C_UPSTREAM_EVIDENCE_INTEGRITY_CONFLICT` before scientific interpretation.

## 2. Permanent status firewall

MSO-02B remains
`MSO02B_PAIRED_PRELEARNING_IDENTIFIABILITY_REQUALIFICATION_NOT_EVALUABLE` and
H-MSO-01 remains
`H_MSO01_MULTISCALE_IDENTIFIABILITY_RESCUE_NOT_EVALUABLE`. Neither may be
relabelled PASS nor FAIL. No MSO-02B metric, checkpoint, report, manifest,
status ledger, component verdict, or target artifact may be modified.

The following are fixed false throughout MSO-02C:

- `NEW_FRESH_TARGET_GENERATION`
- `NEW_CONFIRMATORY_H3_VERDICT`
- `NEURAL_MODEL`
- `ATTENTION`
- `OPTIMIZER`
- `TRAINING`
- `TIME_INTEGRATION`
- `SOLVER_IN_LOOP`
- `ROLLOUT`
- `SEALED_TEST`
- `ARC_ACCESS`
- `MSO03_ELIGIBLE`
- `NEURAL_TRAINING_AUTHORIZED`
- `LEARNED_OPERATOR_AUTHORIZED`

Reading already consumed MSO-02B evidence is classified only as
`CONSUMED_EVIDENCE_DIAGNOSTIC_ONLY`. Non-DNN evidence may be summarized only as
`CONSUMED_EVIDENCE_MECHANISM_DIAGNOSTIC_ONLY`; its thresholds and verdicts are
not recomputed or reinterpreted.

## 3. Stage gates and access order

The following order is mandatory:

1. **G0 — prospective diagnostic freeze.** Add only this contract and the
   MSO-02B Git handoff, commit them, and verify `main`, clean tree, no remote.
   No target store, observable store, checkpoint payload, metric payload, or
   bootstrap draw payload may be opened before G0 is committed.
2. **G1 — exact attribution.** Verify frozen identities, then reconstruct the
   original K=10 matched-random and descriptor-neighbour sufficient statistics
   without altering their identities. G1 may calculate only attribution and
   integrity quantities, not any candidate SS/MS rescue performance.
3. **G2 — isolated mathematics and synthetic stress tests.** The metric
   selection process must run in a process that receives no MSO-02B target,
   checkpoint, metric, sufficient-statistic, or outcome input. It compares
   Candidates A--D using only definitions and deterministic synthetic S1--S8.
4. **G3 — prospective amendment freeze.** Only if G2 selects a zero-safe metric
   without reference to consumed-data candidate performance may
   `00_project_contract/amendments/ca_mso01_zero_safe_dnn_semantics.md` be
   written, hashed, and committed. The amendment is prospective only.
5. **G4 — optional consumed replay.** Only after the G3 commit is clean may the
   frozen candidate be replayed on the old 384 cases. Its status is
   `CONSUMED_DIAGNOSTIC_REPLAY_ONLY`; it cannot amend the metric, thresholds,
   fresh design, or any old verdict.
6. **G5 — release.** Audit all new artifacts, write the MSO-02C report,
   manifest, and status ledger, create the required final commit, verify clean
   `main`, no remote, no push, and stop. H-MSO-01R is not executed.

Each executable must declare its stage gate, inputs, output paths, payload-read
counts, and prohibited-action counts. Candidate selection code and consumed
replay code must be separate entry points. A replay executable must reject an
absent or mismatched prospective-amendment hash.

## 4. Exact degeneracy attribution

Use all and only the frozen 384 formal cases, their 128 formal sampled
particles per case, the original K=10 matched-random identities, the original
K=10 permitted descriptor-neighbour identities, and the three primary targets:

- `density_rate`
- `pressure_gradient_acceleration`
- `viscosity_laplacian_acceleration`

For particle `i`, define in binary64 with the original operation ordering

`N_i = mean_{j in descriptor-NN(i)} ||y_i-y_j||^2`

and

`B_i = mean_{r in matched-random(i)} ||y_i-y_r||^2`.

Zero means exact IEEE-754 binary64 equality to `+0.0` or `-0.0`; no tolerance,
rounding, clipping, epsilon, or near-zero substitution is allowed. Every row
with `B_i == 0` receives all applicable boolean labels:

- **A:** `B_i == 0` and `N_i == 0`;
- **B:** `B_i == 0` and `N_i > 0`;
- **C:** the query target `y_i` is componentwise exact zero;
- **D:** `y_i` and all K matched-random targets are componentwise bitwise
  identical;
- **E:** zero is caused only by target serialization or dtype conversion;
- **F:** the independently recomputed raw binary64 pre-serialization target
  still gives exact zero under the same matched-random identities.

NaN, infinity, or a negative squared-distance term is an integrity conflict,
not a zero. D implies `B_i == 0`; any observed converse failure is an
implementation or arithmetic audit item. C does not by itself imply B or D.

Output a complete zero-particle map and aggregate it without deduplication to
case, lineage, fold, family, arm, and component. Report total zero particles,
affected cases, affected lineages, folds, families, particle fraction, and case
fraction. Explicitly test the handed-off affected-case counts 2, 87, and 2.
SS/MS co-location means equality of the exact `(component, formal_case_index,
particle_id)` zero sets, not merely equality of counts.

For E/F, the diagnostic may recompute the already consumed target formula in
memory for registered old rows under the frozen target-builder and source
identities. This is
`CONSUMED_EVIDENCE_INTEGRITY_RECOMPUTATION_ONLY`, not fresh target generation.
It may write only equality/zero booleans and hashes of diagnostic identity
records; it must not write a target array, a replacement target store, or a new
case. Stored-versus-raw comparison is bitwise and tolerance-free. If the raw
route does not reproduce the frozen target identity or if E is supported, stop
with `MSO02C_UPSTREAM_EVIDENCE_INTEGRITY_CONFLICT`.

## 5. Competing mechanism audit

The mechanism table must classify each of M1--M7 as `SUPPORTED`,
`NOT_SUPPORTED`, or `INCONCLUSIVE`, with evidence and a falsification test:

- M1 physical/analytical exact-target degeneracy;
- M2 manufactured-field symmetry or nodal-zero structure;
- M3 matched-random sampling construction degeneracy;
- M4 case/family stratification creates identical-target matches;
- M5 serialization/dtype artifact;
- M6 residual scalar-DNN implementation error;
- M7 other.

The audit must separately state whether the degeneracy is SS/MS shared,
representation-independent, field-family concentrated, fold concentrated, and
target-component dependent. Causal attribution must distinguish the existence
of identical target values (M1/M2) from the sampled comparator set that makes
all K differences zero (M3/M4).

## 6. Candidate comparison and synthetic-only selection

Before selection, no candidate may be evaluated on consumed MSO-02B targets.
The isolated synthetic executable compares at least:

- Candidate A: particlewise ratio with explicit zero branches;
- Candidate B: per-case numerator/denominator aggregation followed by ratio;
- Candidate C: case-equal family/fold ratio of aggregated numerator and
  denominator primitives;
- Candidate D: target-scale-normalized absolute neighbour disagreement.

Selection criteria are total mathematical definedness, invariance, amplitude
scaling, exact case equality, lineage-bootstrap compatibility, preservation of
the original NN-versus-matched-random interpretation, absence of an arbitrary
epsilon, and deterministic S1--S8 behavior. The synthetic fixtures are:
positive denominators; isolated 0/0; isolated positive/0; an all-zero-denominator
case; an all-zero-denominator fold; constant target; near-zero but nonzero
target; and mixed target amplitudes. Each candidate must be checked for
definedness, monotonicity, scale invariance, hidden-epsilon independence,
case weighting, and resampling behavior.

For the ratio-of-aggregates candidate, retain the primitive case statistics

`N_c = mean_i mean_j ||y_i-y_j||^2`

and

`B_c = mean_i mean_r ||y_i-y_r||^2`,

then apply the frozen equal-case, equal-family, equal-fold aggregation to the
primitives before division. `mean_i(N_i/B_i)` is forbidden. Duplicate bootstrap
case draws are integer multiplicities and particles are never resampled.

No epsilon is permitted. An aggregate `B_agg == 0` may not be called PASS. Its
prospective state and the `SS == 0` relative-rescue branch must be frozen in the
amendment before replay. Any absolute-difference margin must have an external
mathematical or practice basis and cannot be fitted to the consumed outcome.
If the new statistic has a different scale, its absolute threshold requires an
independent prospective derivation rather than mechanical inheritance.

## 7. Prospective amendment boundary

The prospective amendment must freeze the old and new formulas, zero branches,
aggregation unit, K=10 primary and any diagnostic sensitivities, exclusions,
normalization, absolute gate, relative rescue gate, bootstrap decoding,
multiplicity, and status propagation. It must explicitly record that consumed
evidence was already seen and that original H-MSO-01 remains NOT_EVALUABLE.

Only DNN evaluability and the aggregation semantics required for zero safety
may change. Conditional variance, oracle, worst-family, coverage, bootstrap
multiplicity, folds, features, normalization, samples, and every other
H-MSO-01 threshold remain unchanged. No case or particle is deleted.

If no zero-safe statistic and independently justified gates can be frozen
without outcome tuning, terminate as
`MSO02C_DNN_DEGENERACY_ATTRIBUTED_REQUALIFICATION_CONTRACT_NOT_ESTABLISHED`.

## 8. Fresh H-MSO-01R design boundary

A successful amendment establishes only
`H_MSO01R_FRESH_REQUALIFICATION_ELIGIBLE=true`. H-MSO-01R requires a completely
fresh atlas: no DDO historical case, PIO lineage, MSO-02A/02B case or lineage,
MSO-01 fixture, or consumed target lineage may be reused. The prospective
default is 384 fresh cases, 96 per F1--F4, subject to a new target-blind design
freeze, four-scale preflight, pairing, folds, normalization, bootstrap, target
access, and paired requalification. MSO-02C does not execute any of these steps.

## 9. Required outputs and terminal states

Required new outputs are the exact paths authorized by the user under
`06_experiments/mso02c/`, the diagnostic report under `07_reports/`, and the
MSO-02C manifest/status ledger under `08_manifests/`. Old paths are read-only.
Every new artifact must be hash-registered with its evidence class and creation
stage. The ledger must report target, checkpoint, metric, bootstrap, raw
recomputation, and replay read counts separately, plus all prohibited-action
counts.

Success terminates as
`MSO02C_DNN_DEGENERACY_ATTRIBUTED_AND_ZERO_SAFE_REQUALIFICATION_CONTRACT_FROZEN`.
An integrity conflict terminates immediately as
`MSO02C_UPSTREAM_EVIDENCE_INTEGRITY_CONFLICT`. The final report answers all 16
questions in the authorization. The final Git commit message is exactly
`MSO-02C: attribute DNN degeneracy and freeze zero-safe requalification semantics`.
No push is authorized.
