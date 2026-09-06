# Reviewer Attack Matrix

The detailed response contract is in
`results/synthesis_v1/reviewer_attack_matrix.csv`. Valid criticism is accepted
rather than rhetorically dismissed.

| Attack | Validity | Required response |
|---|---|---|
| “This is just Grover/BBBV.” | Partly valid | Credit the black-box core; do not depend on theory priority. |
| “Raw fraction is encoding-dependent.” | Valid | Lead with T5/T6 and separate problem, state, and query domains. |
| “The RCSP bound is only input-query.” | Valid | Put the length-K random-access model in every theorem statement. |
| “CVaR has already been used.” | Valid | Cite prior CVaR work; claim controlled RCSP attribution/confirmation only. |
| “O2 is not deployable.” | Valid | Label it a mechanistic exact-feasibility capacity ceiling. |
| “Only Penalty-X p=3 is confirmed.” | Valid | Restrict H1/H2 scope; pilot depths remain exploratory. |
| “The scaling law failed.” | Valid in substance | Report m=20 reversal and m=22 censoring; remove law language. |
| “Classical optimization dominates.” | Partly valid | Show continuation attribution and keep classical cost in the ledger. |
| “Advice bits are not runtime.” | Valid | State b_eff is posterior concentration and necessary only. |
| “Feasible mixers solve feasibility by construction.” | Valid | Classify stronger structure/state preparation and charge it. |
| “No hardware.” | Valid | Restrict evidence to exact-statevector mechanism. |
| “Synthetic benchmark.” | Valid | Defend control, not natural-instance prevalence. |
| “Same author designed and audited proofs.” | Valid | Label `SECOND_PASS_MACHINE_AUDIT`; require independent human review. |
| “Theory and experiment use different models.” | Valid | Make the distinction explicit and central, not implicit. |

## Five highest residual risks

1. Search/advice priority remains unresolved for the exact posterior formulas.
2. The empirical and theory access models could still be conflated by readers.
3. The confirmatory result is narrow: synthetic DAGs, Penalty-X p=3,
   exact-statevector simulation, no hardware.
4. Phase-3 response reverses at m=20 and is censored at m=22.
5. No independent human proof, prior-art, or empirical reproduction has yet
   occurred.
