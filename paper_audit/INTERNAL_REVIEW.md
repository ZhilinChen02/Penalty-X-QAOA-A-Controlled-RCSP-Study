# Internal hostile review

> **NOT EXTERNAL PEER REVIEW.** This is the single required internal machine
> review of the assembled paper. It is not an independent human assessment and
> must not be described as one.

Review date: 2026-08-29

Evidence boundary: frozen source commit
`260e258af7d397f53c62521d9f52b31223076ec9`

Review policy: one hostile pass followed by one consolidated revision.

## Reviewer A — QAOA / quantum algorithms

- **Major concern:** The exact-statevector CVaR objective suppresses the
  finite-shot estimation cost and variance that a device implementation would
  face. The held-out effect is therefore an objective-alignment result, not a
  hardware-performance or resource-advantage result.
- **Minor concern:** Readers may mistake the membership-oracle theorem for a
  direct lower bound on the rich diagonal-energy experiments.
- **Unsupported wording to exclude:** “CVaR beats the black-box bound” or
  “CVaR solves feasible-space dilution.”
- **Missing citation:** No missing citation for the claims made: the original
  QAOA, alternating-operator, CVaR, warm-start, and Grover-mixer sources are
  cited. A broader VQA sampling survey could aid context but is not needed to
  support a present claim.
- **Unclear figure:** Figure 10 encodes named cost categories, not measured
  magnitudes; this must remain explicit in its caption.
- **Likely rejection reason:** The scope could be read as too narrow---one
  mixer, exact simulation, and depth three---if the controlled attribution and
  negative scaling evidence are not made central.

## Reviewer B — optimization / RCSP

- **Major concern:** Synthetic layered DAGs do not establish behavior on
  natural RCSP instances or competitiveness with classical labeling,
  dominance, and preprocessing methods.
- **Minor concern:** Exact route enumeration is appropriate at the studied
  sizes but is not a deployable oracle; O2 must remain a capacity control.
- **Unsupported wording to exclude:** “The RCSP problem has complexity
  proportional to raw edge-bit dilution.”
- **Missing citation:** The cited primary RCSP algorithm supports the problem
  background. A modern survey might improve breadth during venue adaptation,
  but adding an unverified secondary citation would not strengthen the frozen
  claim set.
- **Unclear figure:** Figure 1 is an attribution schematic and should not be
  read as an end-to-end solver workflow.
- **Likely rejection reason:** Reviewers may regard the task family as a toy
  benchmark unless the paper foregrounds why its controls isolate optimizer,
  loss, representation, and Hamiltonian scale.

## Reviewer C — statistics / experimental design

- **Major concern:** The primary inference has 15 independent graph units;
  the 84 task rows are repeated budget variants and must never be advertised as
  84 independent replications. Heterogeneity and the one negative H1 graph
  matter.
- **Minor concern:** The H2 margin was prospectively frozen but is a
  benchmark-scale tolerance, not a deployment-calibrated utility threshold.
- **Unsupported wording to exclude:** “CVaR is equivalent to O2” or “CVaR wins
  on every held-out task.”
- **Missing citation:** No external statistical method citation is necessary
  to reproduce the explicitly defined complete sign-flip enumeration,
  grouped bootstrap, and Holm adjustment; the preregistration is the operative
  source.
- **Unclear figure:** Figure 6 should keep individual graph contrasts visible
  and label the H2 line as a non-inferiority margin, not a zero null.
- **Likely rejection reason:** Treating task rows as independent or obscuring
  the discovery selection step would invalidate the confirmatory framing.

## Reviewer D — theory / query complexity

- **Major concern:** The search-theoretic core is close to Grover/BBBV,
  multiple-marked search, and advice/preprocessing literature. Exact novelty of
  the posterior-projector and finite-advice formulations remains unresolved;
  the proofs have no independent human review.
- **Minor concern:** The adaptive result needs its pathwise hard cap and
  controlled direct-sum query interface; the quantum-advice statement covers
  one accessible pre-search state, not refreshing or interaction.
- **Unsupported wording to exclude:** “Every explicit RCSP instance requires
  $\Omega(\phi_{\mathrm{state}}^{-1/2})$ time” or “a new advice theorem.”
- **Missing citation:** The closest audited primary search, arbitrary-phase,
  advice, min-entropy, graph-query, and succinct-representation sources are
  present. Forward/backward priority tracing remains a human task.
- **Unclear figure:** Figure 9 can be misread unless the three domains---raw
  edge-bit space, membership-query labels, and explicit RCSP input---remain
  visually and textually separate.
- **Likely rejection reason:** An overclaimed novelty or an unqualified transfer
  from random membership search to rich explicit RCSP would be fatal.

## Reviewer E — general journal editor

- **Major concern:** Combining an empirical attribution study, a negative
  scaling response, and a theory boundary makes the manuscript long. The
  empirical held-out result must remain the center, with proofs in the
  appendix.
- **Minor concern:** Affiliation, funding, acknowledgments, repository/DOI,
  and venue formatting are intentionally unresolved.
- **Unsupported wording to exclude:** Any claim of quantum advantage,
  universal QAOA behavior, a confirmed global scaling law, or theorem
  priority.
- **Missing citation:** Citation coverage is internally complete (21/21 keys
  verified); independent prior-art review remains mandatory before submission.
- **Unclear figure:** Figures 4 and 7 require captions that explicitly define
  the sign convention and distinguish feasible entry from conditional route
  quality.
- **Likely rejection reason:** Without strict claim hierarchy, the breadth may
  appear as several partially complete papers rather than one controlled
  empirical story.

## Consolidated revision performed once

The following changes form one revision pass:

1. Make finite-shot CVaR estimation an explicit implementation limitation at
   the objective definition, not only in the limitations section.
2. State that the H2 margin is a preregistered benchmark tolerance and is not
   calibrated to deployment utility.
3. Reinforce in the theory transition that the oracle statements do not rank
   the empirical objectives or classical RCSP solvers.
4. Tighten Figure 10's caption to state that its cells are text-coded ledger
   categories rather than measured magnitudes.
5. Repair the supplementary hash table's TeX command and retain all model,
   censoring, and nonadvantage qualifications.

## Five material concerns remaining after revision

1. Independent human proof and theorem-priority review has not occurred.
2. The empirical scope remains synthetic, exact-statevector, Penalty-X, and
   depth-three for the held-out comparison.
3. The held-out analysis has 15 independent graph units, and the H2 margin has
   no deployment-utility calibration.
4. Hardware sampling cost, CVaR tail-estimation variance, and end-to-end
   classical-solver comparisons remain unmeasured.
5. The $m=20$ reversal and $m=22$ resource censoring preclude a global scaling
   conclusion.
