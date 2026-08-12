# Experiment storage boundary

No experiment was executed in MSO-00 and this directory contains no scientific data.

Any future authorized stage must use physically separate subdirectories:

- `observable/` for deployment-available `obs__*` quantities;
- `reference_target/` for `target_ref__*` and `target__*` quantities;
- `design_governance/` for `design__*` lineage, split, and role records.

MSO-01 may create only target-blind numerical-qualification artifacts after a separate execution instruction. It may not create or read the reference/target partition.
