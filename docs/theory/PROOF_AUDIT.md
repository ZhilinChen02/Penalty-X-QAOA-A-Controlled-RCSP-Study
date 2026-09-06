# Adversarial proof audit

## Primary verdict

`THEOREM_VALID_AS_STATED`, with explicit domain and indexing conventions. The
proof was attacked at its ancilla averaging identity, hybrid state choice,
expectation/norm exchanges, final projection, and quantifiers. No counterexample
was found inside the stated fixed-query black-box class.

## Step-by-step audit

| Step | Verdict | Audit finding |
|---|---|---|
| Identity-oracle reference algorithm | PASS | Expanding the reference state as \(\sum_x|x\rangle|\alpha_x\rangle\) proves the expectation using only one-point inclusion probability; arbitrary ancillas are covered. |
| Single-query perturbation | PASS | The oracle difference is exactly a scalar times the marked projector, so the norm equality is exact. |
| Hybrid recursion | REFINED | The displayed indexing is valid when \(d_t\) is measured after query \(t\) and \(V_t\), hence immediately before query \(t+1\). With this convention \(d_0=0\) after \(V_0\). |
| L2 average bound | PASS | Pointwise iteration followed by Minkowski is valid; no expectation is moved through a nonlinear norm. |
| Final reference success | PASS | The same ancilla-safe inclusion identity gives \(\mathbb ER=\phi\). |
| Final success projection | PASS | Projection contractivity and the triangle inequality give the pointwise square-root inequality. A second Minkowski step is valid. |
| Squaring and probability cap | PASS | Both sides are nonnegative. The separate cap at one is necessary when the analytic expression exceeds one. |

## Corollary audit

| Corollary | Status | Qualification |
|---|---|---|
| Phase-sensitive bound | VALID_AS_STATED | Direct theorem. |
| Coarse query bound | VALID_AS_STATED | Uses \(c_t\le2\); the uncapped form remains true but may be vacuous. |
| Existence of a hard feasible set | VALID_AS_STATED | Existential only; not every \(\mathcal F\). |
| Uniform worst-case query lower bound | VALID_AFTER_REFINEMENT | Include \(\max\{0,\cdot\}\), integer ceiling if desired, and \(\phi\to0\) for the asymptotic claim. |
| Average-case query lower bound | VALID_AFTER_REFINEMENT | Same qualifications as the worst-case algebra. |
| Exponential dilution | VALID_AFTER_REFINEMENT | Requires fixed \(\alpha>0\), an eventual polynomial bound \(q(n)\le Cn^k\), and sufficiently large \(n\). |
| Fixed-schedule QAOA depth | VALID_AFTER_REFINEMENT | Applies to the binary marked-set Hamiltonian family with instance-independent initialization, mixers, and phases. |
| Multiple queries per layer | VALID_AFTER_REFINEMENT | If total relevant queries satisfy both \(q\ge L\) and \(q\le cp\), then \(p\ge L/c\). |
| Trained-QAOA total-query statement | VALID_STANDARD_REDUCTION_NOT_FORMALIZED | Requires coherent purification, deferred measurements, controlled feedback, and a fixed worst-case query cap. |
| Grover asymptotic tightness | VALID_AFTER_REFINEMENT | Exact construction plus leading-order comparison; exact universal optimality is not proved. |
| Direct structured-RCSP applicability | OPEN_GAP | No marked-set-to-RCSP reduction or RCSP-specific lower bound is supplied. |

## Why the average identity handles ancillas

For any normalized state in query tensor ancilla space, define the nonnegative
query weights (w_x=\|\alpha_x\|^2). They sum to one even when the ancilla
vectors are nonorthogonal or infinite-dimensional. The random projection has
mass \(\sum_{x\in\mathcal F}w_x\), whose expectation is
\(\sum_x(M/N)w_x=M/N\). No assumption about the reduced query state being pure
or uniform is used.

## Nonuniform priors

For a nonuniform prior define

\[
\mu_t=\mathbb E_{\mathcal F}
\|(\Pi_{\mathcal F}\otimes I)|\varphi_t\rangle\|^2,
\quad
\mu_{\rm out}=\mathbb E R_{\mathcal F}.
\]

The proof gives the generalized bound

\[
\sqrt{\mathbb EP_{\mathcal F}}
\le\sqrt{\mu_{\rm out}}+\sum_t c_t\sqrt{\mu_t}.
\]

If (p_x=\Pr[x\in\mathcal F]), then
\(\mu_t=\sum_xp_x\|\alpha_{t,x}\|^2\). It need not equal (M/N). A
nonuniform prior with uniform one-point marginals still satisfies the original
bound, regardless of higher-order correlations.

## Adaptive measurements and training

The fixed pure-query proof does not silently include measurement-driven
training. A standard reduction would need to:

1. purify all classical randomness;
2. store measurement outcomes coherently and defer their measurement;
3. replace classically selected future gates and phases by controlled unitaries;
4. count every oracle use across training circuits, sampling shots, feedback,
   and final execution;
5. pad every branch to a common finite worst-case query count; and
6. represent the final classical success event as a projective measurement on
   an output register.

Under those conditions the resulting pure algorithm is in a standard bounded
query model. This audit does not formalize that reduction, and expected-query or
unbounded stopping-time algorithms need an additional argument.

## Answers to adversarial reviewer questions

1. **Average-case, worst-case, or pointwise?** The direct upper bound is an
   average over uniform size-(M) sets. It implies an existential hard set and
   therefore a worst-case lower bound for uniform guarantees. It is not a
   pointwise upper bound.
2. **Arbitrary mixers?** Yes, if they are unitaries fixed independently of the
   particular feasible set. Feasible-set-dependent mixers are excluded.
3. **Arbitrary initial states?** Yes, including entangled nonuniform states, if
   independent of the particular feasible set.
4. **Ancillas?** Yes, arbitrary ancillas are directly covered.
5. **Adaptive measurements?** Not directly. A bounded-query purification and
   deferred-measurement reduction is standard but not formalized here.
6. **Trained QAOA parameters?** Only through total oracle-query accounting after
   the adaptive reduction; final circuit depth alone is not bounded automatically.
7. **Does \(p=q\) always hold?** No. It holds for the specified fixed schedule
   with exactly one relevant binary-feasibility query per layer.
8. **Can a full cost oracle reveal more?** Yes. Values, gradients, distances, or
   structural encodings exceed the membership phase-oracle model unless reduced
   to it with explicit query accounting.
9. **Directly structured RCSP?** No. An RCSP reduction or independent lower bound
   is missing.
10. **Can feasibility-preserving QAOA evade the bound?** It can bypass the direct
    model because feasible structure was injected in state preparation or the
    mixer; that resource must be counted separately.
11. **Is exact Grover optimality proved?** No. This audit proves the construction's
    exact success formula and asymptotic agreement with the lower-bound order.
12. **Is \((2q+1)^2\phi\) pointwise?** No.
13. **What if the right side exceeds one?** The theorem uses the minimum with one;
    the uncapped inequality is true but uninformative.
14. **What is hidden by structure injection?** Classical description length,
    preprocessing, enumeration, specialized state preparation, compiled gates,
    and structured-oracle access.
15. **Defensible paper wording?** A fixed-query algorithm whose only marked-set
    information is phase membership queries has uniform-random-set average
    feasible probability at most the phase-sensitive expression, implying
    square-root inverse-density query scaling for constant uniform or average
    success in that black-box family.

## Edge cases

- (M=0): the projector is zero, every oracle is identity, and success is zero.
  Grover's good state is undefined and is not used.
- (M=N): success is one and the capped bound is one. Grover's bad state is
  undefined and is not used.
- (q=0): average success equals φ exactly for every instance-independent
  state and (V_0).
- γ_t=0: the query is identity and (c_t=0).
- γ_t=π: (c_t=2), attaining the coarse coefficient.
- φ close to one: the probability cap normally makes the bound trivial.
- Unknown (M): the lower bound uses the actual (M) only in analysis; the
  algorithm need not know it. Choosing an optimal Grover stopping time generally
  requires knowing or estimating (M).
