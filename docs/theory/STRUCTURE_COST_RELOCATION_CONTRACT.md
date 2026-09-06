# Structure-injection cost relocation contract

## Purpose

A method may escape a membership-only dilution bound by receiving structure,
using a richer oracle, restricting its candidate set, preparing a structured
state, or compiling a constrained mixer. That is a change in resource use, not
a contradiction. Every evaluation must retain the following orthogonal ledger;
the entries have different units and must not be collapsed into an arbitrary
scalar score.

Every cell carries one evidence status:

```text
MEASURED
DERIVED
BOUNDED
UNKNOWN
NOT_APPLICABLE
```

`MEASURED` requires an actual recorded observation, `DERIVED` an accounting
identity, `BOUNDED` a proved inequality, and `UNKNOWN` is preferable to an
invented estimate.

## Information resource

```text
classical advice bits
effective structure bits b_eff
candidate effective support K_eff
explicit instance bytes
learned parameter bytes
feasible-list size
```

`b_eff` is a posterior-concentration summary. It does not replace the bytes,
topology, values, or data structure needed to implement the advice.

## Classical computation

```text
preprocessing wall time
candidate generation
corridor construction
constraint propagation
relaxation
repair
feasible-set enumeration
mixer graph construction
parameter transfer/training
```

## Quantum/state-preparation resource

```text
state-preparation depth
state-preparation 1Q/2Q gates
ancillas
amplitude-loading calls
postselection probability
retries
```

## Structured mixer resource

```text
mixer description size
mixer compilation time
gate depth
two-qubit gates
neighbor-oracle calls
Trotter steps
connectivity overhead
```

## Query/oracle resource

```text
membership queries
rich cost queries
feasible-neighbor queries
attribute queries
training queries
sampling queries
final-execution queries
```

When a structured operation is simulated by `r` membership calls and invoked
`L` times, its derived membership charge is `rL`. Without a simulation it is a
stronger oracle and remains a separate column.

## Verification and decoding

```text
route decoding
constraint validation
objective validation
repair after invalid sample
```

## Dynamic reuse

```text
one-time build cost
per-instance cost
cache identity
reuse fraction
patch cost
rebuild cost
amortization horizon
```

Amortization is reported by resource and deployment horizon; it is not assumed
from nominal graph similarity.

## Query-generated structure

Advice produced by membership queries is not free. Pre- and post-advice calls
form one interaction with hard cap

\[
q_{\rm total}=q_{\rm pre}+q_{\rm post}.
\]

Training shots and repeated circuit evaluations are included. Advice derived
from richer explicit data belongs in a stronger information-access class and
must expose its bytes and preprocessing costs.

## Enumeration exposure

If preprocessing supplies the complete feasible list

\[
F=\{x_1,\ldots,x_M\}
\]

and every value `C(x_i)`, then the classical computation
`argmin_i C(x_i)` already returns an optimum. The ledger must record
enumeration, objective evaluation, storage, basis indexing, mixer-graph
construction, and state preparation. Full feasible-basis access is not merely
`b_eff` bits: `b_eff` is only the theorem's lower-dimensional concentration
summary.

## CVaR positioning

CVaR consumes the full sampled energy distribution, not only feasibility
membership. Its information class is

```text
RICH_COST_INFORMATION
```

unless a stated reduction simulates that energy information with counted
membership calls. CVaR's held-out empirical benefit shows that structured RCSP
energy information contains useful signal beyond binary feasibility
membership. That is an empirical interpretation, not a new query lower bound,
and CVaR neither violates nor “beats” the membership-only theorem.

## Contract verdict

The executable ledger contains every resource/method cell and refuses unknown
evidence-status values. Numerical values remain unknown where Theory-v3 did not
measure them.

```text
STRUCTURE_COST_CONTRACT_COMPLETE
```
