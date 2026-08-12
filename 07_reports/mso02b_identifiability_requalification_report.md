# MSO-02B paired prelearning identifiability requalification report

Terminal status: `MSO02B_PAIRED_PRELEARNING_IDENTIFIABILITY_REQUALIFICATION_NOT_EVALUABLE`.

This is the first formal SPH-MSO scientific target experiment. It used only the frozen SS/MS representations and simple non-neural diagnostics. `DNN` means Descriptor Nearest-Neighbour. No neural model, optimizer, training, time integration, rollout, sealed test, or MSO-03 execution occurred.

## Frozen release identities

- Initial pre-target handoff commit: `887d4cdab3dbd9e856e552ff47e50a3cf481d72f`.
- Target/analysis execution-freeze commit: `65aaedc86c97b876a0ce84745d7eee50dfeba660`.
- Non-scientific formal-execution erratum commit: `9322658dae0bc97062bd88faae1df0588c514d66`.
- Formal-execution erratum SHA-256: `b046991e08e81bc8ef2be87f203b9ceda5672bdbd1d5c3d217ab0dd8428efb9b`.
- Target precompute freeze SHA-256: `9dcf39f43e46323433f2e29c73ac3b09743d4a1070af032c0f44c7bd49783962`.
- Target store SHA-256: `16f1ebd26d0d1aa74dd0892dfe2feb0967024f9219dd8c102c8faafc934f81e2`.
- Observable store SHA-256 before/after: `3dfedfa666c32e4e578f1821f441370da288fd636fc977d2fb15bf470654102e` / `3dfedfa666c32e4e578f1821f441370da288fd636fc977d2fb15bf470654102e`.
- SS/MS dimensions remain 39/110. The representations retain five exact constants per arm, all 13/65 fold-IQR-degenerate involved columns, and all five registered exact MS duplicates; there was no feature deletion, PCA, whitening, or target-derived pruning.

## Absolute metrics

| Arm | Component | DNN median (UCB) | DNN p90 (UCB) | Conditional variance (UCB) | Oracle NRMSE (UCB) | Mean-baseline improvement (LCB) | Coverage |
|---|---|---:|---:|---:|---:|---:|---:|
| SS | `density_rate` | NOT_EVALUABLE (NOT_EVALUABLE) | NOT_EVALUABLE (NOT_EVALUABLE) | 0.13355335 (0.16804153) | 0.54435798 (0.77753908) | 0.30712333 (0.19471097) | 0.93594404 |
| SS | `pressure_gradient_acceleration` | NOT_EVALUABLE (NOT_EVALUABLE) | NOT_EVALUABLE (NOT_EVALUABLE) | 0.25958416 (0.30439363) | 0.51448372 (0.6741293) | 0.34062984 (0.26042749) | 0.93594404 |
| SS | `viscosity_laplacian_acceleration` | NOT_EVALUABLE (NOT_EVALUABLE) | NOT_EVALUABLE (NOT_EVALUABLE) | 0.43972437 (0.51454693) | 0.39985817 (0.52185765) | 0.51314485 (0.44021384) | 0.93594404 |
| MS | `density_rate` | NOT_EVALUABLE (NOT_EVALUABLE) | NOT_EVALUABLE (NOT_EVALUABLE) | 0.012669873 (0.016546842) | 0.83481411 (1.0730567) | -0.062578737 (-0.43048127) | 0.93740458 |
| MS | `pressure_gradient_acceleration` | NOT_EVALUABLE (NOT_EVALUABLE) | NOT_EVALUABLE (NOT_EVALUABLE) | 0.25483611 (0.30072053) | 0.24681838 (0.34236042) | 0.68367381 (0.61352533) | 0.93740458 |
| MS | `viscosity_laplacian_acceleration` | NOT_EVALUABLE (NOT_EVALUABLE) | NOT_EVALUABLE (NOT_EVALUABLE) | 0.4063582 (0.47663374) | 0.16885691 (0.2230484) | 0.79440496 (0.75288051) | 0.93740458 |

## Paired multiscale rescue

| Component | DNN p90 ratio / reduction / UCB | Conditional-variance ratio / reduction / UCB | Oracle-NRMSE ratio / reduction / UCB |
|---|---:|---:|---:|
| `density_rate` | NOT_EVALUABLE / NOT_EVALUABLE / NOT_EVALUABLE (NOT_EVALUABLE_UNSTABLE_RATIO_NO_FROZEN_ABSOLUTE_DIFFERENCE_MARGIN) | 0.094867504 / 0.9051325 / 0.12322942 (EVALUABLE) | 1.5335756 / -0.53357557 / 2.2494792 (EVALUABLE) |
| `pressure_gradient_acceleration` | NOT_EVALUABLE / NOT_EVALUABLE / NOT_EVALUABLE (NOT_EVALUABLE_UNSTABLE_RATIO_NO_FROZEN_ABSOLUTE_DIFFERENCE_MARGIN) | 0.98170901 / 0.018290993 / 1.0262298 (EVALUABLE) | 0.47973993 / 0.52026007 / 0.56705605 (EVALUABLE) |
| `viscosity_laplacian_acceleration` | NOT_EVALUABLE / NOT_EVALUABLE / NOT_EVALUABLE (NOT_EVALUABLE_UNSTABLE_RATIO_NO_FROZEN_ABSOLUTE_DIFFERENCE_MARGIN) | 0.92412027 / 0.075879732 / 1.0758273 (EVALUABLE) | 0.42229201 / 0.57770799 / 0.491608 (EVALUABLE) |

## Component and global verdicts

| Component | Absolute evaluable/pass | Relative evaluable/pass | Component verdict |
|---|---:|---:|---|
| `density_rate` | False/False | False/False | `H_MSO01_COMPONENT_NOT_EVALUABLE` |
| `pressure_gradient_acceleration` | False/False | False/False | `H_MSO01_COMPONENT_NOT_EVALUABLE` |
| `viscosity_laplacian_acceleration` | False/False | False/False | `H_MSO01_COMPONENT_NOT_EVALUABLE` |

Global H-MSO-01: `H_MSO01_MULTISCALE_IDENTIFIABILITY_RESCUE_NOT_EVALUABLE`. Coverage remains a component-independent input-geometry gate and was not allowed to substitute for DNN, conditional variance, or oracle identifiability.

## Required final answers

1. Target/reference qualification: **384/384 qualified**, 0 failed.
2. Target definition: **yes**, continuum analytical reference minus the frozen lambda=1 base SPH operator; no 0.75/1.25/1.50 defect target was generated.
3. Observable store unchanged: **True**.
4. Frozen dimensions: **SS=39, MS=110**.
5. SS absolute metrics: reported componentwise in the absolute-metrics table above.
6. MS absolute metrics: reported componentwise in the absolute-metrics table above.
7. DNN p90 paired rescue: reported as point ratio/reduction and simultaneous UCB above.
8. Conditional-variance paired rescue: reported as point ratio/reduction and simultaneous UCB above.
9. Oracle-NRMSE paired rescue: reported as point ratio/reduction and simultaneous UCB above.
10. Simultaneous confidence requirements: each exact pass/fail is serialized in `component_verdicts.csv`; any non-evaluable bound propagates explicitly rather than being called a scientific failure.
11. Absolute gates: exact check dictionaries are serialized per component in `component_verdicts.csv` and summarized above.
12. Relative rescue gates: exact check dictionaries are serialized per component in `component_verdicts.csv` and summarized above.
13. Component verdicts: listed in the component verdict table above.
14. Global H-MSO-01: **H_MSO01_MULTISCALE_IDENTIFIABILITY_RESCUE_NOT_EVALUABLE**.
15. Coverage: reported overall/family/fold; it cannot replace identifiability and did not alter another metric's verdict.
16. Post-target feature/scale/gate/fold/normalization modifications: **all zero**.
17. Neural/optimizer/training activity: **all zero**.
18. If qualified, only deterministic-baseline eligibility is granted: **False**; MSO-03 was not run.
19. If not qualified or not evaluable, neural/attention/learned-operator authorization remains false: **True**.
20. Final terminal status: `MSO02B_PAIRED_PRELEARNING_IDENTIFIABILITY_REQUALIFICATION_NOT_EVALUABLE`.

## Governance disclosure and stop

Source-import QA evaluated A/B reference consistency for 384 frozen states after the initial pre-target commit but before formal defect generation. One static source-audit text search accidentally surfaced a pre-existing historical H3 summary line; it was not used for code, thresholds, tuning, metrics, or verdicts, and no historical target/H3 payload was opened. Formal defect generation began only after the target-blind amendments, executable hashes, provenance, and clean execution-freeze commit were fixed.

The first formal-evaluator attempt stopped before any held-out metric row, checkpoint, confidence bound, or verdict was written because the scalar density-rate DNN array used a vector-oriented norm helper and raised `AxisError`. The frozen scalar statistic already required elementwise squared differences followed by the K mean. Erratum 01 implemented exactly that formula, recorded the discarded attempt's one target/observable payload read, opaque-hash reads, and twelve numerical oracle bundle fit attempts (whose individual success/failure outcomes were not persisted before the checkpoint), and changed no feature, scale, gate, fold, normalization, bootstrap, oracle family, case, or target. No printed or persisted scientific outcome informed the correction.

MSO-02B stops here. MSO-03, neural training, architecture search, attention, and learned operators remain unexecuted.
