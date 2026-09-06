# QAOA information-access models

[V2_NEW_PROOF] Query lower bounds are statements about an information
interface, not just a circuit diagram. The following distinctions are required.

| Procedure | Membership-oracle theorem applies? | Reason | Tag |
|---|---:|---|---|
| Hidden marked-set oracle QAOA | Yes | All feasible-set information is charged to membership queries. | `V2_NEW_PROOF` |
| Explicit-QUBO QAOA | No, not directly | QUBO coefficients are free instance-dependent information. | `COUNTEREXAMPLE` |
| Explicit RCSP graph plus penalties | No, not directly | Topology, costs, resources, and penalty magnitudes reveal structure beyond membership. | `OPEN_GAP` |
| Feasible-subspace state preparation | No | Feasible structure is injected before counted queries. | `COUNTEREXAMPLE` |
| Parameters transferred from unrelated instances | Conditional | Covered only when the transferred data are independent of the hidden $\mathcal F$. | `INFERENCE` |
| Same-instance parameters trained through oracle calls only | Yes under a deterministic total cap | Every training shot and final call is included in $q_{\mathrm{total}}$. | `V2_NEW_PROOF` |
| Parameters computed from complete feasible enumeration | No | Enumeration supplies $\mathcal F$ outside the oracle account. | `COUNTEREXAMPLE` |

## Binary membership access

[V2_NEW_PROOF] A fixed phase-flip query or membership-bit query changes the
reference state only on the marked query-label subspace. This localization is
what produces the factor $\sqrt{\phi}$ in each hybrid step.

## Explicit Hamiltonian access

[COUNTEREXAMPLE] An explicitly supplied Hamiltonian can identify special basis
states without any oracle call. For a singleton encoded by per-bit penalties,
the minimum-penalty choice in each coefficient directly spells out the marked
bitstring.

## Rich value-oracle access

[OPEN_GAP] A value oracle returning objective cost, flow violation, resource
violation, distance, or a multilevel phase may distinguish states that binary
membership treats identically. No simulation by a constant number of
membership queries is established here. Therefore the exact dilution bound is
not transferred to this oracle.

[COUNTEREXAMPLE] A Hamming-distance oracle to a hidden $n$-bit singleton
reveals the singleton in $n+1$ classical queries: query $0^n$, then each unit
vector; the distance change determines every hidden bit. Membership search
requires order $2^{n/2}$ quantum queries. The information interfaces are not
equivalent.

## Structure-injected operations

[COUNTEREXAMPLE] Starting in
$|G_{\mathcal F}\rangle$ gives feasibility probability one with zero queries.
A mixer compiled to preserve exactly $\mathcal F$ similarly depends on
$\mathcal F$. Such methods do not violate the theorem; their state preparation,
compilation, preprocessing, or oracle construction is an uncounted resource.

## Fixed depth and trained depth

[V1_THEOREM] $p=q$ only for a fixed instance-independent schedule with one
relevant query per layer.

[V2_NEW_PROOF] Training through the same hidden oracle is covered only after
all circuit repetitions are combined into $q_{\mathrm{total}}$. The final trained
depth alone is not lower-bounded by the total-query theorem.
