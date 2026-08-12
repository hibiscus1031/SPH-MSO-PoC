# MSO-02C G1 Descriptor-Neighbour A/B Attribution Report

Terminal status: `MSO02C_G1_ZERO_DENOMINATOR_AB_ATTRIBUTION_COMPLETE`.

This is consumed-evidence diagnostic attribution only. It does not amend or re-verdict MSO-02B/H-MSO-01.

## Required 23 answers

1. **Yes.** The observable SHA-256 matched before and after: `3dfedfa666c32e4e578f1821f441370da288fd636fc977d2fb15bf470654102e`. Release validation used the recorded hash chain and did not reread the store.
2. Observable payload keys read: `ss_features, ms_features`. Target keys read: `target_density_rate, target_pressure_gradient_acceleration, target_viscosity_laplacian_acceleration`.
3. **Yes.** Only `ss_features` and `ms_features` were read from the observable payload; other observable payload-key reads were 0.
4. **Yes.** The hash-bound old runner `55b0b63eb2c99364c8a2e96c75191a50707e93357f7039bd9edfdcb7c7c831b7` supplied six outer folds, frozen normalization, Euclidean distance, same-case/same-lineage/equal-nonzero-seed exclusions, complete tie ordering, internal required K=20, and consumption of ranks 1–10 only. No K5/K20 metric was evaluated.
5. **Yes.** 12 primary searches and 12 repeats were exactly equal.
6. density: SS A/B = 2/0 of 2; MS A/B = 2/0 of 2.
7. pressure: SS A/B = 117/2 of 119; MS A/B = 119/0 of 119.
8. viscosity: SS A/B = 2/0 of 2; MS A/B = 2/0 of 2.
9. **Yes.** SS/MS `(component, case_id, particle_id)` zero-query sets remained exactly colocated.
10. Representation-dependent neighbour differences occurred for 117 of 123 colocated component-query keys: `{"density_rate": 0, "pressure_gradient_acceleration": 117, "viscosity_laplacian_acceleration": 0}`.
11. **Yes.** Exact-zero numerators occurred in 244 of 246 arm-query classifications (classification A); by arm/component: `{"MS": {"density_rate": 2, "pressure_gradient_acceleration": 119, "viscosity_laplacian_acceleration": 2}, "SS": {"density_rate": 2, "pressure_gradient_acceleration": 117, "viscosity_laplacian_acceleration": 2}}`.
12. **Yes.** Positive numerators over exact-zero denominators occurred in 2 of 246 classifications (classification B); by arm/component: `{"MS": {"density_rate": 0, "pressure_gradient_acceleration": 0, "viscosity_laplacian_acceleration": 0}, "SS": {"density_rate": 0, "pressure_gradient_acceleration": 2, "viscosity_laplacian_acceleration": 0}}`.
13. M1=SUPPORTED, M2=SUPPORTED, and M3=SUPPORTED. M2 supports exact-target multiplicity, while its analytical symmetry subtype remains `INCONCLUSIVE_AT_ANALYTICAL_SYMMETRY_SUBTYPE`.
14. Pressure affected 119 queries in 87/384 cases per arm, versus 2 queries in 2/384 cases for density and viscosity. This wider incidence is linked to observed binary64 exact/repeated pressure-target multiplicity and frozen matched-random exact equality; A/B separates local K10 0/0 from positive/0. Polarization counts were `{"longitudinal": 65, "transverse": 54}`. The evidence does not uniquely identify a manufactured-field analytical symmetry, so that subtype remains inconclusive.
15. M5=NOT_SUPPORTED; M6=NOT_SUPPORTED; M7=NOT_SUPPORTED. Prior raw/store and serializer identity remained frozen, and exact-source deterministic reconstruction found no residual implementation fault; no historical particle-neighbour array had been persisted for bytewise comparison.
16. **No.** Full DNN median/p90 recomputation counts were 0.
17. **No.** Candidate zero-safe metric performance count was 0.
18. **No.** Metric selection was neither authorized nor performed.
19. **No.** No metric amendment was authorized or created.
20. **Yes.** The old states remain `MSO02B_PAIRED_PRELEARNING_IDENTIFIABILITY_REQUALIFICATION_NOT_EVALUABLE` and `H_MSO01_MULTISCALE_IDENTIFIABILITY_RESCUE_NOT_EVALUABLE`; modified=false.
21. **No.** Neural, attention, optimizer, training, integration, solver-in-loop, rollout, sealed-test, and ARC counts were all 0.
22. **Yes.** MSO-03 remains unauthorized/ineligible.
23. Final terminal status: `MSO02C_G1_ZERO_DENOMINATOR_AB_ATTRIBUTION_COMPLETE`.

## Governance

Execution-freeze commit: `4260abd1a5080c8756e7e0b9b38d4956f973b10f`. The completion commit is recorded by the final Git handoff without rewriting this release.

Immediate stop boundary: no candidate selection, amendment, consumed metric replay, H-MSO-01R, MSO-03, or learning follows this release.
