# Global full-space QAOA feasible-space dilution barrier: theory validation

## A. THEORY AUDIT STATUS

`COMPLETE`

This was an offline, adversarial theorem audit. It made no new scientific QAOA
runs. The proof was tested for hidden pointwise claims, ancilla restrictions,
invalid norm/expectation exchanges, indexing gaps, adaptive-query overreach, and
unsupported RCSP generalization.

## B. PRIMARY THEOREM VERDICT

`THEOREM_VALID_AS_STATED`

The phase-sensitive theorem is valid in its stated fixed-query black-box class.
Several corollaries require explicit scope or asymptotic refinements, and direct
structured-RCSP applicability is not proved.

## C. Correct theorem statement

Let (N\ge1), (0\le M\le N), and (\phi=M/N). Let ℱ be uniform over all
size-(M) subsets of an (N)-element computational query basis, and let

\[
\Pi_{\mathcal F}=\sum_{x\in\mathcal F}|x\rangle\langle x|.
\]

For an arbitrary ancilla Hilbert space, take any normalized pure input state,
unitaries (V_0,\ldots,V_q), and phases (\gamma_1,\ldots,\gamma_q) that are
independent of the particular ℱ. Assume all ℱ-dependent information enters
only through the counted queries

\[
Q_{\mathcal F}(\gamma_t)=I+(e^{-i\gamma_t}-1)
(\Pi_{\mathcal F}\otimes I_A).
\]

Define

\[
|\psi_{\mathcal F}\rangle=
V_qQ_{\mathcal F}(\gamma_q)V_{q-1}\cdots
V_1Q_{\mathcal F}(\gamma_1)V_0|\psi_{\rm in}\rangle
\]

and

\[
P_{\mathcal F}=\langle\psi_{\mathcal F}|
(\Pi_{\mathcal F}\otimes I_A)|\psi_{\mathcal F}\rangle.
\]

Then

\[
\boxed{
\mathbb E_{\mathcal F}P_{\mathcal F}
\le
\min\left\{1,
\left(1+\sum_{t=1}^q|e^{-i\gamma_t}-1|\right)^2\frac MN
\right\}.}
\]

In particular,

\[
\mathbb E_{\mathcal F}P_{\mathcal F}
\le\min\{1,(2q+1)^2\phi\}.
\]

This is an average bound. It implies the existence of a hard ℱ and thus a
worst-case lower bound for algorithms claiming a uniform guarantee, but it is
not a pointwise upper bound for every ℱ.

## D. Proof-step audit

| Proof step | Verdict | Finding |
|---|---|---|
| Identity-oracle reference marked mass | PASS | Writing the state as \(\sum_x|x\rangle|\alpha_x\rangle\) proves \(\mathbb Ea_t^2=M/N\) with arbitrary ancillas. |
| Single-query perturbation | PASS | \(Q-I=(e^{-i\gamma}-1)(\Pi_{\mathcal F}\otimes I_A)\) gives exact norm \(c_ta_t\). |
| Hybrid recursion | REFINED | Valid when \(d_t\) is defined after query (t) and (V_t), equivalently before query (t+1); then (d_0=0) after (V_0). |
| L2 average bound | PASS | Minkowski gives \(\|d_q\|_2\le\sqrt\phi\sum_tc_t\) without exchanging expectation and norm as an equality. |
| Final reference success | PASS | The ancilla-safe subset identity also gives \(\mathbb ER_{\mathcal F}=\phi\). |
| Final success projection | PASS | Projection contractivity gives the pointwise square-root inequality; a second Minkowski step and nonnegative squaring finish the proof. |

## E. Corollary verdicts

| Corollary | Verdict |
|---|---|
| PHASE_SENSITIVE_BOUND | `VALID_AS_STATED` |
| COARSE_QUERY_BOUND | `VALID_AS_STATED` |
| WORST_CASE_QUERY_LOWER_BOUND | `VALID_AFTER_REFINEMENT` |
| AVERAGE_CASE_QUERY_LOWER_BOUND | `VALID_AFTER_REFINEMENT` |
| FIXED_SCHEDULE_QAOA_DEPTH_BOUND | `VALID_AFTER_REFINEMENT` |
| TRAINED_QAOA_TOTAL_QUERY_BOUND | `VALID_STANDARD_REDUCTION_NOT_FORMALIZED` |
| EXPONENTIAL_DILUTION_COROLLARY | `VALID_AFTER_REFINEMENT` |
| GROVER_ASYMPTOTIC_TIGHTNESS | `VALID_AFTER_REFINEMENT` |
| DIRECT_RCSP_APPLICABILITY | `OPEN_GAP` |

The query lower bounds should include

\[
q\ge\max\left\{0,\frac12(\sqrt{\tau/\phi}-1)\right\},
\]

plus an integer ceiling if a discrete bound is desired. The asymptotic
Ω-statement assumes fixed τ>0 and φ→0. For exponential dilution, if
(q(n)\le Cn^k) eventually and φ_n≤2⁻ᵅⁿ, then for any fixed
(0<\beta<\alpha), average success is at most (2^{-\beta n}) for sufficiently
large (n).

## F. Numerical validation

- Parameter cells: **208**
- Deterministic random algorithms: **7,400**
- Algorithm/feasible-set evaluations: **732,000**
- Distinct feasible sets in the validation pools: **2,650**
- Maximum `average_success - phase_sensitive_bound`: **5.551e-16**
- Maximum `phase_sensitive_bound - coarse_bound`: **0.000e+00**
- Violations above (10^{-10}): **0**

For (N\le8), every size-(M) set was enumerated. For (N=16), each (M)
used 208 deterministic cyclic-orbit draws. This multiset has exactly uniform
one-point inclusion marginals, avoiding the logically invalid demand that an
ordinary finite Monte Carlo average obey an expectation bound to (10^{-10}).
The proof depends only on these one-point marginals, so the same inequality is
exact for the validation distribution.

The proof-trace diagnostics recorded every (a_t), (d_t), perturbation term,
and final projection. The maximum recursion and single-query identity residuals
were each (4.441\times10^{-16}). Python complex128 tests are numerical checks,
not a formal proof assistant.

`FORMAL_PROOF_ASSISTANT_NOT_AVAILABLE`

## G. Grover validation

Forty-eight ((N,M,q)) rows were checked for (N\in\{8,16,32,64\}), multiple
(M), and every (q) through the first success maximum. The maximum error in

\[
P_{\rm numerical}=\sin^2((2q+1)\arcsin\sqrt{M/N})
\]

was **1.110e-15**. In the selected dilute rows, the largest relative difference
from ((2q+1)^2\phi) was **8.16%**, decreasing with the expansion parameter.
The audited uniform expansion is

\[
P_{\rm Grover}=(2q+1)^2\phi+O((2q+1)^4\phi^2)
\]

when ((2q+1)\sqrt\phi\to0); for (q\ge1) this is the requested
(O(q^4\phi^2)) form. Grover is used only for achievability and asymptotic
order agreement. Exact universal optimality is not proved here.

## H. Counterexamples and scope

Removing any of the following assumptions permits evasion:

- ℱ-independent initialization: preparing \(|G_{\mathcal F}\rangle\) gives
  success one at (q=0);
- ℱ-independent unitaries: an ℱ-dependent unitary can map |0⟩ to a marked
  state;
- phase-query-only information: classical enumeration can reveal ℱ before the
  query algorithm;
- unstructured marked-set access: known prefixes, fixed-weight sectors, and known
  affine subspaces can be prepared structurally;
- membership-oracle strength: richer value oracles may expose gradients,
  distances, costs, or graph structure.

Every deliberate evasion is labeled `OUTSIDE_THEOREM_CLASS`. A separate genuine
counterexample exists only to the tempting pointwise overstatement: at (q=0),
an instance-independent basis state has success one for the singleton containing
that basis element even though the uniform average is (1/N).

For a nonuniform prior, replace φ by the reference-state-dependent quantities

\[
\mu_t=\sum_x\Pr[x\in\mathcal F]\|\alpha_{t,x}\|^2,
\]

giving

\[
\sqrt{\mathbb EP}\le\sqrt{\mu_{\rm out}}+
\sum_tc_t\sqrt{\mu_t}.
\]

## I. QAOA interpretation

**Fixed-schedule depth result.** For
(H_{\mathcal F}=I-\Pi_{\mathcal F}), one cost layer is one membership phase
query up to global phase. Thus (q=p) only for a fixed, instance-independent
schedule with one relevant query per layer. At most (c) queries per layer gives
(p\ge(\sqrt{\tau/\phi}-1)/(2c)) when positive.

**Trained variational total-query result.** The theorem must count training
evaluations, shots, feedback, and final execution together. Extending the pure
proof requires purification of randomness, coherent storage of outcomes,
deferred measurement, controlled feedback, and padding to a common finite
worst-case query count. This standard reduction was not formalized here.

**Structured-mixer exclusion.** Feasible-state preparation or
feasibility-preserving mixers can bypass full-space dilution because they inject
structure. Their preprocessing and synthesis costs are outside the direct model.

## J. RCSP interpretation

The direct black-box theorem (G1) is proved. A problem class containing the full
binary marked-set Hamiltonian family inherits a worst-case corollary for fixed
global schedules (G2). The theorem does **not** directly prove the same pointwise
bound for natural structured RCSP Hamiltonians (G3). No embedding of arbitrary
marked sets into the RCSP class and no independent RCSP-specific structural lower
bound is supplied, so `DIRECT_RCSP_APPLICABILITY` is `OPEN_GAP`.

## K. Allowed paper claim

For a fixed-query quantum algorithm whose only information about an unknown
size-(M) feasible set is supplied by counted phase-membership queries, the
average feasible probability over uniformly random marked sets is at most
[(1+\sum_t|e^{-i\gamma_t}-1|)]²(M/N), capped at one. Consequently,
constant uniform-average success, or a uniform guarantee over the full binary
marked-set family, requires order √((N/M)) counted queries; fixed
instance-independent binary-feasibility QAOA with one cost query per layer is a
special case. This statement does not by itself cover structure-injected methods,
trained final depth alone, rich cost oracles, or natural RCSP instances.

## L. Prohibited claim

“Every QAOA algorithm on every RCSP instance requires depth
Ω(φ⁻¹⁄²), even with instance-dependent initialization, structured mixers,
training, preprocessing, or richer cost access.”

That sentence is false as a consequence of this theorem: it changes an average
black-box result into a pointwise structured-problem claim and leaves major
resources uncounted.

## M. Remaining open gaps

- a fully formal adaptive-query purification/deferred-measurement theorem,
  especially for expected-query or variable-stopping-time procedures;
- lower bounds for structured or richer cost/value oracles;
- an RCSP-specific reduction or independent structural lower bound; and
- external prior-art and novelty verification before publication.

## N. Git

The theory-audit commit uses message:

`Audit the global QAOA dilution barrier`

No push is performed.
