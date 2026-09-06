# Counterexamples and escape routes

No counterexample was found inside the audited theorem class. Each construction
below can appear to violate the numeric bound only by removing an assumption.

| Construction | Result | Classification | Missing resource/accounting |
|---|---:|---|---|
| Prepare \(|G_{\mathcal F}\rangle\) initially | \(P=1,q=0\) | OUTSIDE_THEOREM_CLASS | Feasible-set-dependent state preparation |
| Use \(V_{\mathcal F}|0\rangle=|x\in\mathcal F\rangle\) | \(P=1,q=0\) | OUTSIDE_THEOREM_CLASS | Feasible-set-dependent unitary |
| Enumerate ℱ classically and load one item | \(P=1\) with no counted phase query | OUTSIDE_THEOREM_CLASS | Enumeration, memory, and data loading |
| Known fixed-prefix family | \(P=1\) by fixing prefix bits | OUTSIDE_THEOREM_CLASS | Succinct structural description |
| Feasibility-preserving mixer/subspace | State never leaves feasible sector | OUTSIDE_THEOREM_CLASS | Structured preparation and mixer synthesis |
| Rich cost/value oracle | May expose directions, distances, or graph structure | OUTSIDE_THEOREM_CLASS | Oracle is stronger than phase membership |

## Structured examples

- **Known fixed prefix:** set the prefix and prepare a uniform suffix. The subset
  is not an unknown unstructured member of the theorem's random family.
- **Fixed Hamming weight:** Dicke-state preparation and weight-preserving mixers
  can work entirely within the feasible subspace. Their construction cost and
  use of the weight constraint are outside the direct oracle accounting.
- **Known affine subspace:** linear algebra can prepare a uniform subspace state
  from generators. The generator description is additional information.

These examples do not refute the theorem. They show why it cannot be generalized
by deleting “all information about ℱ enters through phase queries.”

## Genuine pointwise failure of an overstatement

At (q=0), take an instance-independent initial state |1⟩ and (M=1). For the
particular set ℱ={1}, success is one although φ=1/N. Averaging over all singleton
sets restores exactly (1/N). Thus interpreting the theorem as a pointwise upper
bound would be genuinely false even without violating its actual assumptions.

## Nonuniform prior

If some basis elements are more likely to be feasible, an initial state may
concentrate on them. The replacement quantities are

\[
\mu_t=\sum_x\Pr[x\in\mathcal F]\|\alpha_{t,x}\|^2,
\]

and the generalized square-root bound uses √μ_t at each step. Uniform
cardinality alone does not force μ_t=φ under a nonuniform prior.
