# Literature boundary report

Cutoff: 2026-08-12. This is a boundary registration, not a systematic review or novelty guarantee. Exact metadata and scientific scope were checked against primary paper, proceedings, publisher, or institutional records. “No reported prospective qualification” means no preregistered, fresh, prelearning identifiability qualification was identified in the cited primary material; ordinary test splits are not treated as equivalent.

## Boundary by adjacent direction

### A. Learned or parameterized SPH kernels

[Woodward et al., *Physical Review Fluids* 8, 054602 (2023)](https://doi.org/10.1103/PhysRevFluids.8.054602) explicitly develop parameterized smoothing kernels inside a learned Lagrangian turbulence hierarchy. This makes kernel-learning novelty unavailable to MSO. MSO differs by freezing the kernel family and probing the response of the same qualified operator at candidate support scales before any learning.

### B. Neural SPH

[Toshev et al., ICML 2024, arXiv:2402.06275](https://arxiv.org/abs/2402.06275) combine GNN simulators with SPH pressure, viscous, external-force, and relaxation components to improve long rollouts. MSO cannot claim the first neural/SPH hybrid or SPH-enhanced neural simulator. Its target is an instantaneous discretization defect and MSO-00 contains no model or rollout.

### C. Symmetric basis convolutions

[Winchenbach and Thuerey, ICLR 2024](https://proceedings.iclr.cc/paper_files/paper/2024/hash/1386faadf55462905db1548cff151a78-Abstract-Conference.html) learn particle continuous convolutions with even/odd basis symmetries. This is a high representation-overlap threat. MSO must distinguish numerical operator-response observables from learned convolution bases.

### D. Momentum-conserving particle networks

[Prantl et al., NeurIPS 2022](https://proceedings.neurips.cc/paper_files/paper/2022/hash/2dd7f33ffbb59b4ff987be5442a13016-Abstract-Conference.html) guarantee linear momentum with antisymmetric continuous convolution and a hierarchical architecture. MSO may inherit the philosophy of hard reciprocal pair structure from PIO, but cannot claim first hard momentum conservation or infer angular momentum/energy guarantees from antisymmetry alone.

### E. Differentiable SPH

[JAX-SPH, arXiv:2403.04750](https://arxiv.org/abs/2403.04750) and [diffSPH, arXiv:2507.21684](https://arxiv.org/abs/2507.21684) provide differentiable SPH, inverse/adjoint optimization, and solver-in-loop capabilities. AD/FD and differentiable-SPH novelty is unavailable. MSO-01 may qualify numerical interfaces but MSO-00 neither differentiates nor optimizes a solver.

### F. Learned mesh-free differential operators and moment constraints

[Trask et al., GMLS-Nets, arXiv:1909.05371](https://arxiv.org/abs/1909.05371) parameterize GMLS estimators for operators on unstructured point clouds with approximation-theory support. MSO cannot claim first learned mesh-free operator or first moment-structured point operator. Its first learning object is the already-frozen DDO defect, not a newly learned differential stencil.

### G. Multiscale neural operators on point clouds/graphs

[Li et al., Multipole Graph Neural Operator, NeurIPS 2020](https://proceedings.neurips.cc/paper/2020/hash/4b21cf96d4cf612f239a6c322b10c8fe-Abstract.html) and [Lino et al., MultiScaleGNN, arXiv:2106.04900](https://arxiv.org/abs/2106.04900) use multilevel graphs to capture multiple interaction ranges/resolutions. MSO cannot claim the first multiscale neural operator or multiscale graph fluid simulator. Its narrow distinction is same particles, same physical operator, same kernel family, support-scale response, and prelearning identifiability.

### H. Local-global particle Transformers

[Wang et al., FluidFormer, *Neural Networks* 198, 108631 (2026)](https://www.sciencedirect.com/science/article/pii/S0893608026000936) combine continuous local convolution and global self-attention for particle-fluid rollout. This forecloses attention/Transformer/local-global novelty. MSO selects no architecture, and attention is not a first-stage hypothesis.

### I. Multiscale Lagrangian turbulence models

[Tian et al., PNAS 120, e2213638120 (2023)](https://doi.org/10.1073/pnas.2213638120) construct physics-informed Lagrangian LES with generalized weakly compressible SPH and separately modeled subgrid effects. MSO cannot claim first scale-aware Lagrangian/SPH learning. Its object is numerical support-response identifiability for a fixed-time defect, not turbulence closure or temporal LES.

### J. Deng–Hani–Ma particle → kinetic → fluid limits

[Deng, Hani and Ma, *Long time derivation of the Boltzmann equation from hard sphere dynamics*](https://annals.math.princeton.edu/articles/22284) and their [arXiv:2503.01800 particle-to-fluid program](https://arxiv.org/abs/2503.01800) are registered only as `MATHEMATICAL/METHODOLOGICAL_INSPIRATION`. Their hard-sphere, Boltzmann-Grad, kinetic, and hydrodynamic-limit objects are not SPH support-scale observables. MSO will not state that these results prove SPH multiscale well-posedness, identifiability, qualification, or architecture validity.

## Five most dangerous novelty overlaps

1. **Woodward et al. (2023): parameterized SPH kernels and Lagrangian turbulence hierarchy — HIGH.** It directly blocks learned-kernel and broad multiscale-SPH novelty.
2. **Winchenbach & Thuerey (2024): symmetric basis particle convolutions — HIGH.** It blocks broad representation/symmetry and particle-convolution novelty.
3. **Prantl et al. (2022): hard momentum-conserving hierarchical particle network — HIGH.** It blocks hard-conservation and hierarchical particle-network novelty.
4. **Tian et al. (2023): physics-informed Lagrangian LES — HIGH.** It blocks broad scale-aware Lagrangian turbulence/SPH-learning novelty.
5. **FluidFormer (2026): continuous-convolution local/global Transformer — HIGH.** It blocks attention, Transformer, and local-global particle-fluid novelty.

GMLS-Nets and MultiScaleGNN are also high threats to broad “learned mesh-free operator” and “multiscale neural CFD” wording. They are not in the top five only because MSO's frozen target and same-state SPH response give a somewhat clearer object-level distinction.

## Defensible MSO gap

The registered sources learn kernels, dynamics, PDE solution operators, subgrid closures, or temporal simulators, and/or propose differentiable infrastructure. None of the checked primary materials reports the exact prospective design frozen here:

- preserve \(d_h^*=R_h\mathcal L(q^*)-\mathcal L_h(R_hq^*)\);
- evaluate one qualified SPH semidiscrete operator on the same deployment state at several candidate support scales without changing particle resolution;
- keep SS and MS fresh arms identical except for representation;
- test deployment-compatible conditional ambiguity and a non-neural oracle before architecture selection;
- require both absolute identifiability and paired relative rescue with lineage-held-out fresh requalification.

This is a **working gap**, not a “first ever” claim. It must be rechecked before publication and narrowed if newer or missed work demonstrates the same learning object, intervention, and prospective evidence order.
