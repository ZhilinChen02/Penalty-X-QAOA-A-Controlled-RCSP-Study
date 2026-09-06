# Trained-QAOA total-query theorem

## Interaction model

[V2_NEW_PROOF] A classical controller runs rounds $r=1,\ldots,R$. Based only
on its previous oracle-derived transcript and $\mathcal F$-independent code or
randomness, it selects one or more quantum circuits. If circuit $j$ in round
$r$ contains $p_{rj}$ relevant membership-oracle calls and is executed for
$S_{rj}$ shots, define

\[
q_{\mathrm{total}}
=\sum_{r=1}^{R}\sum_j S_{rj}p_{rj}+q_{\mathrm{final}}.
\]

[V2_NEW_PROOF] Different circuits may have different depths. Classical
floating-point work is not itself an oracle query. It becomes outside-model
side information if it reads an explicit $\mathcal F$-dependent instance or
feasible-set description without charge.

## Hard-cap corollary

[V2_NEW_PROOF] Assume:

1. every $\mathcal F$-dependent datum enters through a fixed phase-flip or
   membership-bit oracle;
2. the complete interaction makes at most $q_{\mathrm{total}}$ such calls on
   every branch;
3. all remaining classical and quantum control is independent of
   $\mathcal F$; and
4. the output is a label in the marked-set domain.

Then the adaptive theorem gives

\[
\boxed{
\mathbb E_{\mathcal F}P_{\mathrm{success}}
\le
\min\{1,(2q_{\mathrm{total}}+1)^2\phi\}.
}
\]

[V2_NEW_PROOF] The output may be a new final sample, the best earlier sampled
label, or a classically selected label from the transcript. In the purified
algorithm, the controller reversibly computes that selection into a final
output register; the proof does not require a new final circuit.

## Depth distinctions

[V1_THEOREM] For an instance-independent fixed schedule with one relevant
membership-equivalent cost query in each of $p$ layers, $q=p$. The fixed
depth corollary applies.

[V2_NEW_PROOF] For an instance-trained schedule, final circuit depth $p$ is
not total query cost. A nominal $p=3$ circuit run for $S$ shots in $K$
training evaluations already uses at least $3SK$ relevant calls, before
validation and final execution.

[COUNTEREXAMPLE] If a classical controller receives a complete list of
$\mathcal F$, it outputs a listed label with zero oracle queries. The same is
true when it receives an explicit singleton identifier. These are
`OUTSIDE_BLACK_BOX_MODEL`, not violations.

## Expected total query count

[COUNTEREXAMPLE] Replacing a hard cap by $\bar q=\mathbb E Q$ inside
$(2q+1)^2\phi$ is false because rare long Grover branches exploit convexity.

[V2_NEW_PROOF] Under a global mean-query guarantee, the valid conclusion is
the truncation family

\[
\mathbb E P
\le
\min\left\{1,\frac{\bar q}{T+1}
+\min\{1,(2T+1)^2\phi\}\right\},
\quad T\in\mathbb Z_{\ge0}.
\]

## Status

[V2_NEW_PROOF] `TRAINED_QAOA_TOTAL_QUERY_BOUND` is
`VALID_STANDARD_REDUCTION_FORMALIZED` under the hard-cap oracle-only
assumptions above.

[OPEN_GAP] It does not directly cover standard QAOA supplied with an explicit
QUBO, graph, penalties, constraint coefficients, gradients, or other free
same-instance information.
