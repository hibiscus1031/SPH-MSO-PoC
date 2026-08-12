# H-MSO-01R-B fresh confirmatory multiscale identifiability requalification report

Terminal status: `HMSO01R_B_FRESH_CONFIRMATORY_MULTISCALE_IDENTIFIABILITY_RESCUE_NOT_QUALIFIED`.

This release evaluates only the prospectively frozen H-MSO-01R hypothesis on the 384-case R-A atlas. `DNN` means Descriptor Nearest-Neighbour and Candidate C is its only formal statistic. Historical H-MSO-01 remains permanently NOT_EVALUABLE. No neural model, attention model, optimizer, training, time integration, solver-in-loop, rollout, sealed test, ARC access, or MSO-03 execution occurred.

## Candidate C, CVAR, oracle, and coverage

| Component | SS Candidate C D (UCB) | MS Candidate C D (UCB) | MS/SS Candidate C ratio (UCB) | SS/MS CVAR (rescue ratio/UCB) | SS/MS oracle NRMSE (rescue ratio/UCB) |
|---|---:|---:|---:|---:|---:|
| `density_rate` | 0.35538256 (0.46544824) | 0.071640791 (0.13694575) | 0.20158781 (0.53106221) | 0.19798051/0.030563654 (0.15437709/0.2048862) | 0.54037899/0.16259511 (0.30089088/0.53170602) |
| `pressure_gradient_acceleration` | 0.47559984 (0.58232509) | 0.47138675 (0.58872404) | 0.99114152 (1.1190984) | 0.33004875/0.34510363 (1.0456141/1.20732) | 0.50788425/0.25235989 (0.49688465/0.56948427) |
| `viscosity_laplacian_acceleration` | 0.75055618 (0.872749) | 0.73458285 (0.87303182) | 0.97871801 (1.1097595) | 0.46037841/0.47275502 (1.0268836/1.200177) | 0.46713985/0.18754481 (0.40147464/0.47377305) |

## Component decisions

| Component | Evaluable | Absolute verdict | Relative-rescue verdict | Final status |
|---|---:|---:|---:|---|
| `density_rate` | PASS | PASS | PASS | `H_MSO01R_COMPONENT_QUALIFIED` |
| `pressure_gradient_acceleration` | PASS | FAIL | FAIL | `H_MSO01R_COMPONENT_NOT_QUALIFIED` |
| `viscosity_laplacian_acceleration` | PASS | FAIL | FAIL | `H_MSO01R_COMPONENT_NOT_QUALIFIED` |

## Required 30 answers

1. **Yes: 384/384.** Every formal case completed every frozen target/reference qualification check before analysis.
2. **Yes.** Every formal defect is reference minus the frozen lambda=1 base SPH operator; no 0.75/1.25/1.50 defect target was generated.
3. **Yes.** The fresh observable store remained `65ca1a7fea58248207fc5a22e14855b4a84c392c7ef17cefdf2d396687cc38cd` before target generation, after generation, after analysis, and at release.
4. **Yes: SS=39 and MS=110.** No column was added or removed.
5. **Yes.** Pointwise Candidate C division count is `0`; only post-aggregation divisions were performed.
6. **Yes.** Component/arm W(B) values are serialized in the Candidate C metric tables.
7. **No.** Exact Candidate C evaluability/status values, including the canonical CA zero status where applicable, are serialized componentwise.
8. **SS Candidate C D/UCB:** listed for all three components in the metric table above.
9. **MS Candidate C D/UCB:** listed for all three components in the metric table above.
10. **Candidate C SS→MS point ratio/UCB:** listed for all three components in the metric table above.
11. **Candidate C absolute gates:** `density_rate` SS=PASS [D=0.35538256, UCB=0.46544824]; MS=PASS [D=0.071640791, UCB=0.13694575]; `pressure_gradient_acceleration` SS=PASS [D=0.47559984, UCB=0.58232509]; MS=PASS [D=0.47138675, UCB=0.58872404]; `viscosity_laplacian_acceleration` SS=PASS [D=0.75055618, UCB=0.872749]; MS=PASS [D=0.73458285, UCB=0.87303182].
12. **Candidate C relative gates:** `density_rate`=PASS [ratio=0.20158781, UCB=0.53106221]; `pressure_gradient_acceleration`=FAIL [ratio=0.99114152, UCB=1.1190984]; `viscosity_laplacian_acceleration`=FAIL [ratio=0.97871801, UCB=1.1097595].
13. **CVAR SS/MS and rescue:** `density_rate` SS=0.19798051 [UCB=0.23936376]; MS=0.030563654 [UCB=0.036547883]; rescue ratio=0.15437709, UCB=0.2048862; gates=PASS/PASS; `pressure_gradient_acceleration` SS=0.33004875 [UCB=0.39737991]; MS=0.34510363 [UCB=0.44396072]; rescue ratio=1.0456141, UCB=1.20732; gates=FAIL/FAIL; `viscosity_laplacian_acceleration` SS=0.46037841 [UCB=0.54001052]; MS=0.47275502 [UCB=0.57404533]; rescue ratio=1.0268836, UCB=1.200177; gates=FAIL/FAIL.
14. **Oracle SS/MS NRMSE and rescue:** `density_rate` SS=0.54037899 [UCB=0.71558318]; MS=0.16259511 [UCB=0.28337059]; rescue ratio=0.30089088, UCB=0.53170602; gates=PASS/PASS; `pressure_gradient_acceleration` SS=0.50788425 [UCB=0.70240614]; MS=0.25235989 [UCB=0.35010266]; rescue ratio=0.49688465, UCB=0.56948427; gates=PASS/PASS; `viscosity_laplacian_acceleration` SS=0.46713985 [UCB=0.58766434]; MS=0.18754481 [UCB=0.24039958]; rescue ratio=0.40147464, UCB=0.47377305; gates=PASS/PASS.
15. **Mean-baseline improvement:** `density_rate`=PASS [SS improvement=0.36413632, LCB=0.29749411; MS improvement=0.80867442, LCB=0.71748224]; `pressure_gradient_acceleration`=PASS [SS improvement=0.37125543, LCB=0.29429535; MS improvement=0.68758647, LCB=0.63904132]; `viscosity_laplacian_acceleration`=PASS [SS improvement=0.47498064, LCB=0.42020703; MS improvement=0.78921804, LCB=0.75408638].
16. **Worst-family gates:** `density_rate` absolute families [F1=0.35398585/UCB 0.74237029 (PASS), F2=0.057983225/UCB 0.078634944 (PASS), F3=0.0409064/UCB 0.060333112 (PASS), F4=0.19750497/UCB 0.24845422 (PASS)]; worst SS/MS=0.83059475/0.35398585; paired <=0.05 guard=PASS; `pressure_gradient_acceleration` absolute families [F1=0.28379304/UCB 0.4637486 (PASS), F2=0.16406151/UCB 0.24525816 (PASS), F3=0.16568481/UCB 0.24646806 (PASS), F4=0.39590019/UCB 0.65586649 (PASS)]; worst SS/MS=0.77187238/0.39590019; paired <=0.05 guard=PASS; `viscosity_laplacian_acceleration` absolute families [F1=0.18190523/UCB 0.2830542 (PASS), F2=0.082114036/UCB 0.10848817 (PASS), F3=0.062501925/UCB 0.079916549 (PASS), F4=0.42365803/UCB 0.57030741 (PASS)]; worst SS/MS=0.6933343/0.42365803; paired <=0.05 guard=PASS.
17. **Coverage overall/family/fold:** `density_rate` overall SS/MS=0.93214287/0.94172809 (MS gate PASS); SS families [F1=0.97609847, F2=0.99183934, F3=0.9921875, F4=0.76844618], MS families [F1=0.9601304 (PASS), F2=0.96984236 (PASS), F3=0.98743873 (PASS), F4=0.84950087 (PASS)]; SS folds [FOLD_0=0.97910443, FOLD_1=0.94628906, FOLD_2=0.97427875, FOLD_3=0.91238497, FOLD_4=0.82832606, FOLD_5=0.95247396], MS folds [FOLD_0=0.96389591, FOLD_1=0.94628906, FOLD_2=0.96033241, FOLD_3=0.94632633, FOLD_4=0.83596622, FOLD_5=0.99755859] all-valid=PASS; paired guard=PASS; `pressure_gradient_acceleration` overall SS/MS=0.93214287/0.94172809 (MS gate PASS); SS families [F1=0.97609847, F2=0.99183934, F3=0.9921875, F4=0.76844618], MS families [F1=0.9601304 (PASS), F2=0.96984236 (PASS), F3=0.98743873 (PASS), F4=0.84950087 (PASS)]; SS folds [FOLD_0=0.97910443, FOLD_1=0.94628906, FOLD_2=0.97427875, FOLD_3=0.91238497, FOLD_4=0.82832606, FOLD_5=0.95247396], MS folds [FOLD_0=0.96389591, FOLD_1=0.94628906, FOLD_2=0.96033241, FOLD_3=0.94632633, FOLD_4=0.83596622, FOLD_5=0.99755859] all-valid=PASS; paired guard=PASS; `viscosity_laplacian_acceleration` overall SS/MS=0.93214287/0.94172809 (MS gate PASS); SS families [F1=0.97609847, F2=0.99183934, F3=0.9921875, F4=0.76844618], MS families [F1=0.9601304 (PASS), F2=0.96984236 (PASS), F3=0.98743873 (PASS), F4=0.84950087 (PASS)]; SS folds [FOLD_0=0.97910443, FOLD_1=0.94628906, FOLD_2=0.97427875, FOLD_3=0.91238497, FOLD_4=0.82832606, FOLD_5=0.95247396], MS folds [FOLD_0=0.96389591, FOLD_1=0.94628906, FOLD_2=0.96033241, FOLD_3=0.94632633, FOLD_4=0.83596622, FOLD_5=0.99755859] all-valid=PASS; paired guard=PASS. Coverage was used only as geometry evidence.
18. **Yes.** Method `MAXIMUM_STUDENTIZED`, confidence `0.95`, scope `THREE_PRIMARY_COMPONENTS_WITHIN_EACH_METRIC_FAMILY`; every required bound procedure executed and emitted a status row (a legitimate `NOT_EVALUABLE` row does not claim a numeric bound).
19. **Component evaluability:** shown in the component-decision table above, with all mandatory metric/fold flags in `component_verdicts.csv`.
20. **Component absolute verdicts:** `density_rate`=PASS; `pressure_gradient_acceleration`=FAIL; `viscosity_laplacian_acceleration`=FAIL.
21. **Component relative-rescue verdicts:** `density_rate`=PASS; `pressure_gradient_acceleration`=FAIL; `viscosity_laplacian_acceleration`=FAIL.
22. **Final component statuses:** shown above using the frozen five-state taxonomy.
23. **Global H-MSO-01R:** `H_MSO01R_MULTISCALE_IDENTIFIABILITY_RESCUE_NOT_QUALIFIED`.
24. **No.** All target-derived scientific modification counts are zero: `True`.
25. **No.** Neural/attention/Transformer/optimizer/training counts are all zero: `True`.
26. **Only eligibility if qualified:** `MSO03_DETERMINISTIC_CLOSURE_BASELINE_ELIGIBLE=False`; MSO-03 was not executed.
27. **Yes.** Under NOT_QUALIFIED/NOT_EVALUABLE, all learning routes and MSO-03 eligibility remain false; under QUALIFIED, all learning routes still remain false.
28. **Yes.** Old H-MSO-01 remains permanently `H_MSO01_MULTISCALE_IDENTIFIABILITY_RESCUE_NOT_EVALUABLE`.
29. **Git:** `HMSO01R_A_FINAL_COMMIT=9048eff137001e5f644575bd02c3856b4f4ac532`, `HMSO01R_B_PRE_TARGET_COMMIT=1c99103edaf76aa05915458fd498e07b1241e272`, `HMSO01R_B_FINAL_COMMIT=RECORDED_BY_FINAL_GIT_COMMIT_AND_USER_HANDOFF` pending the non-amended release commit.
30. **Final terminal status:** `HMSO01R_B_FRESH_CONFIRMATORY_MULTISCALE_IDENTIFIABILITY_RESCUE_NOT_QUALIFIED`.

## Governance disclosure and stop

R-A's frozen synthetic-preflight CSVs and firewall counters were eligibility evidence but were not executable-bound call traces or OS-level access proofs. R-B therefore ran an executable-bound synthetic preflight before first target/reference access and emitted direct target-access, Candidate C division, bootstrap, and firewall ledgers. This disclosure changes no frozen scientific value.

The scoped pre-target lambda-one base-operator identity audit matched 384/384 cases (ordered digest `4cf2df0d4b4bcf25ee497e89a12f6edb07bdeae7b195f5ca100bedef79467e40`) and performed no analytical/reference evaluation, defect generation, target read/write, or historical outcome read. It was not first target access.

H-MSO-01R-B stops here. MSO-03, neural models, attention, learned operators, optimization, and training remain unexecuted.
