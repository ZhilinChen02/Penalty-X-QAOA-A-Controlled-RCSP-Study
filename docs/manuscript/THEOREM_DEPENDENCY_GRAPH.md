# Theorem Dependency Graph

All theorem nodes require independent human proof review before submission.
This document records logical dependency and manuscript placement; it does not
assert priority.

```text
uniform fixed-cardinality prior + identity-oracle hybrid
                    |
                    v
          T1 fixed-query phase bound
             |               |
             v               v
       T2 adaptive cap   T8 posterior structure
          /      \          /        \
         v        v        v          v
 T3 total query  T4 truncation  T9 classical  T10 quantum
                                      \       /
                                       v     v
                                    T11 effective

explicit chain ------> T5 raw-phi counterexample
private subdivision --> T6 padding lemma
multiple-marked search + parallel attributes --> T7 RCSP query bound
```

| Result | Prerequisites | Placement | Prior-art class | Human review |
|---|---|---|---|---|
| T1 fixed-query | uniform prior; identity reference; hybrid and L2 Minkowski | appendix, main summary | preexisting asymptotic core; exact form potentially distinct | mandatory |
| T2 adaptive cap | T1 machinery; purification; direct-sum query interface | appendix | likely reformulation | mandatory |
| T3 trained total query | T2; end-to-end transcript model | appendix qualification | likely reformulation | mandatory |
| T4 expected-query truncation | T2; Markov tail for integer Q | appendix | likely reformulation | mandatory |
| T5 raw-phi counterexample | explicit chain and output model | main | likely reformulation/application | mandatory |
| T6 padding | private serial subdivision; rational attribute split | main/appendix proof | potentially distinct statement | mandatory |
| T7 explicit-attribute RCSP | multiple-marked search; amplitude amplification | main/appendix proof | likely reformulation/application | mandatory |
| T8 posterior structure | conditional T2 hybrid; diagonal posterior projector | appendix, main summary | potentially distinct | mandatory |
| T9 finite classical advice | T8; finite support maximizers | appendix | potentially distinct exact form | mandatory |
| T10 finite quantum advice | T8-style hybrid; operator domination on dimension d | appendix | potentially distinct exact form | mandatory |
| T11 effective quantities | T8/T9 algebra; 0<phi | main interpretation | likely reformulation | mandatory |

The machine-readable edge list is
`results/synthesis_v1/theorem_dependency_edges.csv`. T5--T7 are logically
independent of T1--T4 and T8--T11; the manuscript must not imply otherwise.
