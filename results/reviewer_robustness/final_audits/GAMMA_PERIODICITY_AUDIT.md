# Gamma Periodicity Audit

Audit date: **2026-09-04**

## Verdict

**Case A.** The original pilot draws random gamma coordinates from
`[0, 2*pi]`; subsequent optimization is unbounded and does not wrap gamma.
The interval is an initialization domain, not a fundamental phase period of
the normalized Hamiltonian.

No frozen output or canonical datum was changed. Because Case C was not
observed, no new validation experiment or canonical rerun was warranted.

## Code and protocol evidence

| Question | Evidence | Finding |
| --- | --- | --- |
| Random initialization | `src/qroute_dilution/optimizer.py`, `initial_parameters` | `rng.uniform(0.0, 2.0 * np.pi, size=depth)` for gamma; beta uses `[0, pi]`. |
| Cost phase | `src/qroute_dilution/qaoa.py`, `apply_cost_layer` | Applies `exp(-1j * gamma * energies)` directly. |
| Primary COBYLA | `src/qroute_dilution/optimizer.py` | `scipy.optimize.minimize` is called without `bounds`. |
| Diagnostic optimizers | `src/qroute_dilution/diagnostic_optimizer.py` | COBYLA and Nelder--Mead calls have no `bounds`. |
| Objective comparison | `src/qroute_dilution/phase1_2_objectives.py` | COBYLA call has no `bounds`. |
| Reviewer robustness | `src/qroute_dilution/reviewer_robustness/optimization.py` | COBYLA, Nelder--Mead, and SLSQP calls have no `bounds`. |
| Wrapping/modulo | Repository-wide source search for `mod`, `remainder`, `fmod`, `wrap`, and parameter transforms | No gamma reduction modulo `2*pi` or equivalent transform occurs in an experimental optimizer or simulator path. |
| Frozen pilot protocol | `configs/phase1_pilot_v1.yaml` | Records `initial_gamma_interval: [0, 6.283185307179586]` and no optimizer bounds. |

The frozen YAML shorthand `none_periodic_phases` is a legacy label for the
absence of bounds. It is not executable wrapping logic and is not interpreted
as a claim that a general normalized Hamiltonian is `2*pi`-periodic in gamma.
The frozen configuration was left unchanged to preserve protocol identity.

## Stored-output cross-check

A read-only scan of 21 CSV files with parameter-vector columns parsed 39,612
stored gamma coordinates. It found 4,500 coordinates outside the pilot random-
initialization interval, with observed values below zero and above `2*pi`.
This is direct frozen-output evidence that optimization can leave the initial
interval and that results were not stored modulo `2*pi`.

Some later `initial_parameters` fields also fall outside `[0, 2*pi]` because
objective-comparison and held-out arms deliberately inherit an optimized
mean-energy-selected `p=2` point. This is consistent with the common-start
protocol and does not redefine the original random initialization rule.

## Scientific assessment

For a diagonal cost layer, shifting gamma by `2*pi` leaves the unitary
unchanged only under additional spectral conditions (for example, an
integer-valued spectrum up to a compatible global phase). The normalized RCSP
Hamiltonian generally has noninteger eigenvalue differences, so global
`2*pi` periodicity must not be asserted.

The implementation does not rely on that assertion: it evaluates the
unwrapped coordinate directly and lets the optimizer leave the random-start
interval. Therefore the audit finds **no gamma-wrapping threat to the frozen
scientific results**. The risk was terminological. Main-text and Online
Resource 1 wording now says that `[0, 2*pi]` is an initialization interval,
that coordinates are subsequently unbounded, and that no fundamental
`2*pi` gamma periodicity is assumed.
