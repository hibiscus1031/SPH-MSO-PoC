# MSO-02C G1 descriptor-neighbour reconstruction authorization

Status: `FROZEN_BEFORE_FIRST_OBSERVABLE_PAYLOAD_ACCESS`.

This artifact records the user's narrowly scoped supplemental authorization for
**MSO-02C G1 — Descriptor-Neighbour Identity Reconstruction and
Zero-Denominator A/B Attribution**. The complete authorization source is
`/Users/xiejinbo/.codex/attachments/29d4e32d-1b8d-44ad-8543-ad579232b3ba/pasted-text.txt`,
SHA-256
`65fd122c73b9926edc030fc19b21d03a6bf5304680192b9c01b0d90d3633322b`.

## Git and immutable scientific handoff

```text
PRE_OBSERVABLE_ACCESS_PARENT_HEAD = 8943de6b2b82dc25e850cab18eebe40c2939319d
G1_OBSERVABLE_ACCESS_AUTHORIZATION_COMMIT = RECORDED_BY_POST_COMMIT_G1_MANIFEST_AND_STATUS_LEDGER
branch = main
working_tree_clean_at_handoff = true
remote = none
push = false
```

The following states remain immutable:

```text
MSO02B_PAIRED_PRELEARNING_IDENTIFIABILITY_REQUALIFICATION_NOT_EVALUABLE
H_MSO01_MULTISCALE_IDENTIFIABILITY_RESCUE_NOT_EVALUABLE
```

They may not be relabelled PASS or FAIL. No MSO-00, MSO-01, MSO-02A,
MSO-02B, or already frozen MSO-02C artifact may be modified.

## Sole payload authorization

```text
MSO02C_G1_DESCRIPTOR_NEIGHBOUR_RECONSTRUCTION_AUTHORIZED = true

AUTHORIZED_OBSERVABLE_STORE =
06_experiments/mso02a/observable/mso02a_observable_store.npz

AUTHORIZED_OBSERVABLE_STORE_SHA256 =
3dfedfa666c32e4e578f1821f441370da288fd636fc977d2fb15bf470654102e

AUTHORIZED_KEYS =
- ss_features
- ms_features

FULL_FEATURE_MATRIX_READ = true

AUTHORIZED_PURPOSE =
reconstruct exactly the frozen MSO-02B descriptor-neighbour particle
identities for the already identified zero-denominator queries and compute only
their frozen descriptor-NN numerators for A/B attribution

EVIDENCE_CLASS = CONSUMED_EVIDENCE_DIAGNOSTIC_ONLY
```

Archive/key metadata may be inspected, but no observable payload array other
than `ss_features` and `ms_features` may be accessed. The complete matrices are
needed only because each frozen outer fold uses its complete legal training
candidate pool. Feature values may be held in memory but may not be written to
any new artifact; only query-vector hashes, normalized-query hashes, distances,
and neighbour identities may be emitted.

The already consumed target store may be read only for the three frozen target
fields and only to compute the K=10 numerator for the authorized zero-query and
reconstructed-neighbour identities. It may not guide feature, metric, scale,
threshold, or model choices.

## Frozen evidence identities checked before reconstruction

| Artifact | SHA-256 |
|---|---|
| observable store (recorded identity; first actual hash only after this authorization commit) | `3dfedfa666c32e4e578f1821f441370da288fd636fc977d2fb15bf470654102e` |
| `06_experiments/mso02a/ss_observable_schema.json` | `b2237506cac4bbc67dfda981f15daea47c32535259d394b962263a82190e2ec4` |
| `06_experiments/mso02a/ms_observable_schema.json` | `51ff5e04dde4b862f3cab19c80e2aea93c151006fe7b3f497001e43475ec18cb` |
| `06_experiments/mso02a/fold_normalization_registry.json` | `f8fb9ccde826ece14690ab255955ecb7b922bc5cd27ddb9b0544b9fd9c9bd634` |
| `05_registries/mso02a_formal_fresh_atlas_registry.json` | `9893cf48d73be3316a66bb7b9c7f71db8c122247ce56b67d1b0f685605b761c6` |
| `05_registries/mso02a_lineage_fold_registry.json` | `b163a6b3e70cde47e033d204d74b997fd218596885a4b96287dc160a948c42ff` |
| `05_registries/mso02b_formal_particle_sample_registry.json` | `98ff5716e3adbbaac4cac4899e76eb4d61d4e194396fe4e37041a94abe0ca229` |
| `05_registries/mso02b_analysis_semantics_registry.json` | `b271864a62800ea502d1f21621b3d937088f6809c0d31301e6effac96d203ce5` |
| `06_experiments/mso02b/run_mso02b_formal.py` | `55b0b63eb2c99364c8a2e96c75191a50707e93357f7039bd9edfdcb7c7c831b7` |
| target store | `16f1ebd26d0d1aa74dd0892dfe2feb0967024f9219dd8c102c8faafc934f81e2` |
| `06_experiments/mso02c/zero_denominator_particle_map.csv` | `803e5234f113373aa134c97b809cfeb807dad6bbe6c4c2346bfc393a1c46d893` |
| `06_experiments/mso02c/zero_denominator_case_map.csv` | `e8aa8855e91132809cbc7515d952c0295ad2cb1076b8a8dfa42eb1bcfad27aef` |
| `06_experiments/mso02c/zero_denominator_family_fold_summary.csv` | `72a0f04caf740c1f8a089e7e955c8b35c0d433db62480b77aa5e9b76a5a36ba1` |
| `06_experiments/mso02c/degeneracy_mechanism_audit.csv` | `52a81467c9df26993a00a8b6d70fd4c6339d85735bb14854ce8f13c62e77abb4` |
| `06_experiments/mso02c/attribution_execution_audit.json` | `40d69d0653be28083ce19fd3da2c50c83415b9e5ded0cb8235dfd0e6c09ae274` |

Any mismatch terminates as
`MSO02C_UPSTREAM_EVIDENCE_INTEGRITY_CONFLICT` before reconstruction.

## Exact inherited reconstruction semantics

The sole authoritative algorithm is the hash-bound MSO-02B formal runner and
its frozen registries. For each of six outer folds and each arm independently:

- use all and only its training-side formal sampled particles;
- retain all 39 SS or 110 MS columns in frozen order, including constants,
  IQR-degenerate columns, and five registered MS duplicates;
- apply the serialized outer-train median and divisor, including the frozen
  zero-IQR divisor-one fallback; never refit normalization;
- use ordinary Euclidean descriptor distance;
- use the runner's training order, same-case, same-lineage, and equal-nonzero
  same-seed exclusions;
- call the exact deterministic complete-tie expansion/order implementation;
- reconstruct the runner's primary result by invoking its required-K=20 search
  and taking ranks 1--10. K=5 and K=20 statistics are not computed.

The query universe is exactly the existing zero map: per arm, 2 density, 119
pressure, and 2 viscosity rows (123 total; 246 across two arms). SS/MS query
keys must be exactly colocated, but neighbour identities and A/B labels are
computed separately by arm.

For scalar density, the authorized numerator is

`N_i = mean_K((y_j-y_i)^2)`.

For each vector component it is

`N_i = mean_K(sum_Cartesian((y_j-y_i)^2))`.

All operations are binary64 in the frozen order. There is no epsilon,
tolerance, floor, clipping, or conversion of a positive number to zero. Given
the already frozen exact denominator `B_i=0`:

- `N_i == 0.0` means classification A (`0/0`);
- `N_i > 0.0` means classification B (`positive/0`).

Every authorized row must satisfy A XOR B. A negative, nonfinite, missing, or
non-K10 result terminates as an integrity/implementation failure. The old
matched-random denominator may be reconstructed only as an exact-zero identity
check using its unchanged frozen RNG, seed, pool, and K.

## Explicit prohibitions and zero counters

```text
OBSERVABLE_STORE_WRITE = false
FEATURE_MODIFICATION = false
FEATURE_DELETION = false
FEATURE_ADDITION = false
FEATURE_SELECTION = false
PCA = false
WHITENING = false
NORMALIZATION_MODIFICATION = false
DISTANCE_MODIFICATION = false
K_MODIFICATION = false
EXCLUSION_MODIFICATION = false
FOLD_MODIFICATION = false
CASE_MODIFICATION = false
TARGET_MODIFICATION = false

FULL_DNN_METRIC_RECOMPUTE = false
DNN_MEDIAN_RECOMPUTE = false
DNN_P90_RECOMPUTE = false
CVAR_RECOMPUTE = false
ORACLE_RECOMPUTE = false
PAIRED_RESCUE_RECOMPUTE = false
BOOTSTRAP_RECOMPUTE = false

CANDIDATE_METRIC_PERFORMANCE = false
METRIC_SELECTION = false
METRIC_AMENDMENT = false
CONSUMED_REPLAY = false
NEW_CONFIRMATORY_H3_VERDICT = false
ZERO_SAFE_METRIC_SELECTED = false
H_MSO01R_CONTRACT_FROZEN = false
H_MSO01R_FRESH_REQUALIFICATION_ELIGIBLE = false

NEURAL_MODEL = false
ATTENTION = false
ATTENTION_AUTHORIZED = false
OPTIMIZER = false
TRAINING = false
TIME_INTEGRATION = false
SOLVER_IN_LOOP = false
ROLLOUT = false
SEALED_TEST = false
ARC_ACCESS = false
MSO03_ELIGIBLE = false
NEURAL_TRAINING_AUTHORIZED = false
LEARNED_OPERATOR_AUTHORIZED = false

STOP_AFTER_AB_ATTRIBUTION = true
```

Existing G1 evidence is immutable. Any after-A/B mechanism audit uses the new
path `06_experiments/mso02c/degeneracy_mechanism_audit_after_ab.csv`.
Successful completion produces only the user-listed new G1 artifacts,
terminates as `MSO02C_G1_ZERO_DENOMINATOR_AB_ATTRIBUTION_COMPLETE`, creates the
exact completion commit, and stops. It does not select a metric, create the
zero-safe amendment, replay a candidate, execute H-MSO-01R, or enter MSO-03.
