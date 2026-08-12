# MSO-01 scale semantics

Status: `FROZEN_BEFORE_NUMERICAL_RESPONSE_EVALUATION`.

The candidate ladder is exactly `[0.75, 1.00, 1.25, 1.50]`. For every registered fixture,

\[
h_\lambda=\lambda h_0,\qquad h_0=4\,\Delta x.
\]

Changing `h` changes compact support and may change topology. It does not change particle resolution, particle count, spacing, state samples, domain, kernel family, EOS, viscosity, or precision. The authoritative support predicate and minimum-image convention are those in the hash-bound parent `neighborhood.py`; boundary tolerance is not redefined by MSO.

The authoritative graph is the parent's lexicographically sorted, deduplicated directed graph with reciprocal nonself edges and one defined self edge per particle. Graph equality across different scales is neither required nor expected. Only monotone nesting under the common positions and scalar support rule is required.

The baseline `lambda=1.00` is mandatory and must reproduce the parent direct path bitwise. Non-unit responses are direct deployment observables. They are not defects, targets, reference approximations, scale rankings, or evidence that multiscale representation improves identifiability.

Registered scale-response summaries are direct RMS, baseline-difference RMS, baseline log-scale divided-difference RMS, `S_0.75_1.25`, `S_1.00_1.50`, `C_0.75_1.00_1.25`, `C_1.00_1.25_1.50`, and graph/topology diagnostics. A topology change is reported, not smoothed away.
