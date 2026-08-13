# MSO-02D Componentwise Identifiability Failure Attribution and Route Adjudication Report

Terminal status: `MSO02D_COMPONENTWISE_FAILURE_ATTRIBUTION_COMPLETE_NO_ACTIONABLE_TARGET_BLIND_ROUTE`.

Evidence class: `EXPLORATORY_CONSUMED_DIAGNOSTIC_ONLY`. 本报告仅为 consumed-evidence diagnostic attribution；不修改 H-MSO-01R、formal metric、feature、fold、normalization、gate 或 component verdict。

## 关键结论

Route A 与 Route B 均未形成 actionable target-blind candidate；F-MS6（global predictability/local operational identifiability separation）为 dominant。建议关闭当前 support-scale development route 并转论文，不创建 fresh H-MSO-02 atlas，不授权 fresh compute、MSO-03 或 learning。

## 必答 40 项

1. **Frozen R-B canonical results 是否全部一致？** 是。九项跨源 identity 均 PASS、最大跨源差异为 0。Density 的 Candidate C/CVAR/oracle 为 `0.35538256→0.071640791` / `0.19798051→0.030563654` / `0.54037899→0.16259511`；pressure 为 `0.47559984→0.47138675` / `0.33004875→0.34510363` / `0.50788425→0.25235989`；viscosity 为 `0.75055618→0.73458285` / `0.46037841→0.47275502` / `0.46713985→0.18754481`。

2. **NRMSE denominator 是否验证，能否解释为 explained variance？** 已审计但不等价。冻结 denominator 是 outer-fold development population 上、case/family-equal 的 about-zero target RMS，并进一步按 fold×family cellwise roots 聚合，不是同权中心化 pooled variance。`1-NRMSE²` 与任何 R²-like quantity 均未获授权。

3. **θ 是否有可复核定义，5.4/13.4 是否可用？** 没有找到完整公式、输入、分母与 aggregation provenance；状态为 `NOT_ADMISSIBLE_UNDEFINED_DIAGNOSTIC`，5.4/13.4 不得作为承重证据。

4. **Density 为什么三项同时改善？** 操作上，formal U0 的 `W(N)` 从 `0.006291549076702527` 降至 `0.0012682995704503253`，而 `W(B)=0.017703595326272418` 在两 arm 相同；因此 Candidate C 降至 `0.201588×`。CVAR 与 oracle 同时降至 `0.154377×`、`0.300891×`，均在 6/6 folds、4/4 families 同向。这里只证明当前局部几何能读取 density 的预测结构，不宣称物理因果机制已证明。

5. **Pressure 为什么 oracle 改善但 local ambiguity 不改善？** Oracle 降至 `0.496885×`（6/6、4/4），但 Candidate C 仅为 `0.991142×`，formal CVAR 反而为 `1.04561×`。`W(N)` 仅从 `0.9457716995418465` 到 `0.9373935968609581`，`W(B)` 不变；global model 可利用结构，但 frozen Euclidean K10 未稳定形成 target-similar neighbourhood。

6. **Viscosity 为什么相似？** Oracle 为 `0.401475×`（6/6、4/4），Candidate C 仅 `0.978718×`，formal CVAR 为 `1.02688×`；因此同样是 global/local separation，而不是信息充分性的证明。

7. **Candidate C 不改善来自 W(N)、W(B) 还是 ratio cancellation？** 不是 denominator cancellation；三个 component 的 W(B) 在 SS/MS 完全相同。变化全部来自 W(N)：density 下降约 79.8%，pressure 约 0.9%，viscosity 约 2.1%。Momentum 的局部 numerator 几乎不变。

8. **Momentum CVAR hotspot 是否集中于 F4/少数 fold？** 有显著集中但非唯一来源。Pressure F4 `0.923851→0.987692`，FOLD_5 `0.364845→0.626969`；viscosity F4 `0.660071→0.802262`，FOLD_3 `0.772292→1.23235`。

9. **还是跨多数 family/fold 持续？** 不是所有 strata 一致恶化，而是“广泛残留 + 大幅 hotspot”。Pressure 多数 fold/family 的点变化很小，F4/FOLD_5 拉高 formal aggregate；viscosity 的 F2/F4 与 FOLD_3 是主要反向 strata。F4 仅有 8 个 independent lineages，粒子行不得当作独立复制。

10. **Oracle gain 是否跨至少 4/6 folds 与 3/4 families？** 是。三个 component 均为 6/6 folds、4/4 families 改善。

11. **Formal MS distance concentration 是否恶化？** 是，幅度有限。按“越低越集中”的 index，`224.36712106005666→217.34710969103776`；K10 distance CV `0.2733084774245903→0.23113149432319502`，而 K10/random median ratio `0.002325489855327127→0.00929723741062847`，显示局部/随机分离减弱。

12. **Hubness 是否恶化？** 是。Skew `1.631850782075731→2.149326178376823`、Gini `0.41017624851730133→0.44163864950339`、zero-occurrence fraction `0.07069905598958333→0.09104410807291667`。

13. **Neighbour turnover 多大？** SS-U0→MS-U0 mean turnover `0.39579467773437504`、median `0.19999999999999996`；complete turnover `0.20035807291666666`，identical K10 set `0.3919270833333333`。

14. **是否有稳定 target-blind 低维 structure？** 未建立。U1 的 hubness/group-domination replication 失败；U2 的 fold transform similarity `0.4942210863728243<0.75` 且 group domination 0/6、0/4；U3 concentration 0/6、0/4。

15. **哪个 candidate 被唯一选中？** 无；freeze 为 `ROUTE_A_TARGET_BLIND_GEOMETRY_CANDIDATE_NOT_ESTABLISHED`，selected=null。

16. **该 candidate 在 T3 是否改善 momentum alignment？** 不适用。没有 D1-selected nonidentity candidate，D2 不得用 target 回选 U1-U3。

17. **Route A 是否 actionable？** 否，Route A=`NOT_SUPPORTED`；候选冻结、momentum replication、两类 alignment diagnostics 与 density guard 均未形成可评估的完整链。

18. **是否存在无 principal-frame fallback 的 O(2) proxies？** 存在 `70` 个可计算 proxy；均无 eigenframe/sign/arbitrary fallback。但 `70` 个全部只是 110D 代数重参数化；唯一 new-information P5 在 frozen deployment store 不可用。

19. **完整 pressure/viscosity population 是否有 directional evidence？** 有强描述性 association：最强 Spearman 分别 `0.996441` 与 `0.989241`。但 `78` 条 overall frozen-alpha1 increment 均因 fold 不完整而不可评估，fold-level singular failures=`169`；且所有可算 proxy 都不是新增信息，所以不能形成 actionable 增量结论。

20. **G1 的 65/54 是否在完整 population 复现？** `REPLICATION_NOT_ESTABLISHED`。65/54 仅是旧 pressure zero-denominator subset；完整 R-B 为 longitudinal 111 cases、transverse 112、none 161。Pressure 与 viscosity 的 longitudinal-vs-transverse Candidate C 方向相反，不能形成跨 momentum component 的统一 fingerprint；Route B 不得依赖旧计数。

21. **Route B 是否 actionable？** 否。Eligible incremental-information proxy=0；P5 未评估；residual replication 不完整；G1 full-population replication 未建立。Route B=`NOT_SUPPORTED`。

22. **Near collision 在 MS 是否持续？** 是，限于 operational claim。Pressure `270→1543` / 983040；viscosity `1135→902` / 983040；density 均为 0。不得称为 intrinsic mathematical non-identifiability。

23. **High ambiguity 是否主要在 formal coverage 内？** 是。MS pressure inside/outside near-collision count=`1543/0`；viscosity=`902/0`。这排除“只发生在 coverage 外”，但不证明固有不可辨识。

24. **哪些 feature groups 驱动 oracle gain？** 不能归因给单一 group。数值稳定的最佳单组加法是 BASE+G2（density/pressure/viscosity NRMSE `0.24039400291017207/0.43467524429837984/0.45404630272074703`），仍远差 full MS。Leave-G3-out 均恶化；leave-G1/G2 有 singular 或灾难性不稳定，说明多组交互与数值条件限制，不能作 causal ranking。

25. **Component dependence 是否不同？** 是。Leave-G4-out 对 pressure `0.25235988894350103→0.24978779886855454`、viscosity `0.18754480586081715→0.1733300040067205`，均 6/6 folds、4/4 families；density 仅微变且 2/6、1/4。这是 exploratory component contrast，不授权删 G4。

26. **F-MS1？** `INCONCLUSIVE`：没有通过 target-blind selection 的替代 geometry，不能证明失败主要由可修复 geometry misalignment 导致。

27. **F-MS2？** `SUPPORTED_PARTIAL`：Candidate C persistence、formal CVAR persistence、coverage 内 near collisions 三类独立 diagnostics 支持 operational ambiguity；不声称 intrinsic non-identifiability。

28. **F-MS3？** `INCONCLUSIVE`：representation 含预测信息，但现有诊断不能证明 observable family 本身必然不足，也不能推出 temporal/history/nonlocal/directional information 必须。

29. **F-MS4？** `SUPPORTED_PARTIAL`：density-vs-momentum local response、proxy class、fixed G4 ablation 三类 contrast 支持 component dependence；数值不稳定与缺少 prospective intervention 限制为 partial。

30. **F-MS5？** `SUPPORTED_PARTIAL`：distance concentration、hubness 与约 39.6% mean turnover 支持部分 dilution；但 semantic domination 反而下降且 density 在同一 110D 成功，因此不是 dominant/sole cause。

31. **F-MS6？** `SUPPORTED_DOMINANT`：momentum oracle 6/6、4/4 改善，Candidate C/CVAR 不 rescue，coverage 内 ambiguity 持续，density 同时三项改善，满足 dominant 的多诊断与 replication 边界。

32. **是否有新的 deployment-compatible、target-blind missing-variable/geometry hypothesis？** 没有满足全部 actionable criteria 的 candidate。H2-A、H2-B 均 NOT_SUPPORTED；H2-S 仅登记为 OUTSIDE_PRELEARNING_SCOPE。

33. **该 hypothesis 是否只是 metric redesign？** 没有 supported hypothesis。现存 Route A 是 geometry/metric reparameterization，P1-P4 是 110D algebraic re-expression；二者均未达到 prospective-contract 条件。

34. **A/B/C 如何裁决？** Route A=`NOT_SUPPORTED`；Route B=`NOT_SUPPORTED`；Route C=`SUPPORT_SCALE_ROUTE_CLOSURE_RECOMMENDED`。

35. **Density positive result 是否完整保留？** 是：`density_rate=H_MSO01R_COMPONENT_QUALIFIED` 保持；不得因 global failure 抹去，也不外推至 momentum。

36. **H-MSO-01R global NOT_QUALIFIED 是否保持？** 是，仍为 `HMSO01R_B_FRESH_CONFIRMATORY_MULTISCALE_IDENTIFIABILITY_RESCUE_NOT_QUALIFIED`；旧 gate 与 verdict 未修改，`h_mso01r_reverdict=false`。

37. **是否生成 fresh evidence？** 否。Fresh case/target/reference、bootstrap redraw 与 formal artifact modification 均为 0。成功 D2 target read=1；另完整披露 prepublication target reads=4（3 个未发布失败尝试 + 1 个 oracle identity validation），累计 payload open=5，失败尝试没有发布科学结果。

38. **是否运行 neural/attention/training？** 否。Neural、attention、Transformer、optimizer、training、learned operator、solver-in-loop、rollout、sealed-test、ARC 全部为 0 且未授权。

39. **推荐 H-MSO-02 还是关闭路线转论文？** 推荐关闭当前 support-scale development route 并转论文；不推荐现在设计或启动新的 H-MSO-02 contract。

40. **Final terminal status？** `MSO02D_COMPONENTWISE_FAILURE_ATTRIBUTION_COMPLETE_NO_ACTIONABLE_TARGET_BLIND_ROUTE`；`SUPPORT_SCALE_ROUTE_CLOSURE_RECOMMENDED=true`，`PAPER_ROUTE_RECOMMENDED=true`，`FRESH_COMPUTE_AUTHORIZED=false`。

## D3 治理说明

D2 的 CVAR case primitives 未变；D3 仅把 case-scope reporting 从额外 lineage 等权修正回 frozen formal 的 24 个 fold×family cell 等权 case mean，并与 canonical 六个 SS/MS component 点值逐项 exact-match。Mechanism verdict 亦按 preregistered independent-diagnostic minima 重裁；这些都是 MSO-02D diagnostic governance，不是 H-MSO-01R re-verdict。

## Git / stop boundary

- `HMSO01R_B_FINAL_COMMIT=47a15ce3e38dbf13d671b9ae7275bb84761ae279`
- `MSO02D_PRE_DIAGNOSTIC_COMMIT=78ba0d5518909c96e3bf34383e0d95f30ca9ba17`
- `MSO02D_TARGET_BLIND_GEOMETRY_FREEZE_COMMIT=6d4456ec40d58456141e34f64a2c4ef9af355309`
- `MSO02D_TARGET_BLIND_GEOMETRY_SCIENCE_FREEZE_COMMIT=6d4456ec40d58456141e34f64a2c4ef9af355309`
- `MSO02D_TARGET_BLIND_GEOMETRY_RELEASE_BINDING_COMMIT=9cd76d0cc3ddd5202689278769446b4044bf5e5e`
- `MSO02D_FINAL_COMMIT=RECORDED_BY_FINAL_GIT_COMMIT_AND_USER_HANDOFF`
- branch=`main`; remote=`none`; push=`false`.

立即停止：不创建 fresh atlas，不启动 H-MSO-02，不执行 MSO-03、neural、attention、Transformer、optimizer 或 training。
