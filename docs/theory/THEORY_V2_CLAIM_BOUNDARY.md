# Theory Validation v2 claim boundary

## Valid levels

[V1_THEOREM] Level 1: for a uniformly random size-$M$ marked subset and
oracle-only, $\mathcal F$-independent fixed-query control, the phase-sensitive
and coarse average-success bounds hold.

[V2_NEW_PROOF] Level 2: intermediate measurements, classical feed-forward,
mixed states, variable stopping with a deterministic hard cap, and
history-controlled phases are covered after the explicit purification and
oracle-interface refinements in the adaptive theorem.

[V1_THEOREM] Level 3: a fixed instance-independent QAOA schedule has $p=q$
only when each layer contains exactly one relevant membership-equivalent query.

[V2_NEW_PROOF] Level 4: same-instance variational training is covered only when
all $\mathcal F$-dependent information arrives through counted membership
queries and the complete training-plus-output interaction has a deterministic
total cap.

[INFERENCE] Level 5: the direct RCSP application is limited to nonstandard
oracle-RCSP. Standard explicit-input RCSP remains an empirical case study, not
a corollary of the black-box theorem.

## Refined expected-query statement

[COUNTEREXAMPLE] The hard-cap quadratic expression cannot use
$\mathbb E Q$ in place of $q$.

[V2_NEW_PROOF] A truncation-plus-Markov theorem is valid and still yields an
asymptotic $\Omega(\phi^{-1/2})$ mean-query requirement for fixed success under
the oracle-only model.

## Outside the black-box model

[COUNTEREXAMPLE] Each of the following can evade the theorem without violating
it:

- a classical list of feasible labels;
- an explicit marked singleton identifier;
- an $\mathcal F$-dependent initial feasible state;
- an $\mathcal F$-dependent or feasibility-preserving mixer;
- explicit coefficients that reveal the marked path;
- a rich distance, gradient, cost, or violation oracle;
- preprocessing that enumerates the feasible set.

## Prohibited wording

[COUNTEREXAMPLE] **“All QAOA algorithms require
$\Omega(\phi^{-1/2})$ circuit depth.”** Final depth is not total training query
cost, and structured/explicit-input methods violate the information model.

[OPEN_GAP] **“CVaR cannot overcome feasible-space dilution in RCSP because of
Grover's lower bound.”** The theorem concerns oracle access and feasibility
success, not CVaR's behavior under explicit multilevel RCSP Hamiltonians.

[OPEN_GAP] **“The black-box theorem proves a lower bound for every explicit
RCSP instance.”** No polynomial explicit-input bridge was found.

[V2_NEW_PROOF] **“A trained $p=3$ QAOA uses only three relevant oracle
queries.”** Every shot and every training/final execution contributes queries.

[COUNTEREXAMPLE] **“Feasibility-preserving mixers violate the quantum-search
lower bound.”** They inject feasible structure and are outside the direct
membership-only theorem.

## Required unresolved labels

[OPEN_GAP] `RICH_COST_ORACLE_EXTENSION_OPEN`.

[OPEN_GAP] Polynomial explicit-input RCSP bridge.

[OPEN_GAP] Exact prior-art status of the v1 phase-sensitive sum.

[OPEN_GAP] Independent external proof and prior-art review.
