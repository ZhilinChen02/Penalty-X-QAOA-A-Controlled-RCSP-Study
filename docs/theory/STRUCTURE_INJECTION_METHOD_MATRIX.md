# Structure-injection method matrix

The machine-readable matrix is
`results/theory_validation_v3/structure_cost_method_matrix.csv`; the full
resource-by-method ledger is `structure_cost_full_ledger.csv`. No scalar score
combines these resources.

| Method | Injected structure | Theorem class | `phi` / `Lambda` effect | Relocated burden | Evidence and readiness |
|---|---|---|---|---|---|
| Penalty-X full-space QAOA | Explicit multilevel RCSP penalty Hamiltonian | `RICH_COST_INFORMATION`; membership theorem only after a proved simulation | Raw `phi_state` unchanged; no classical-advice `Lambda` assigned | Hamiltonian construction, energy access, training, sampling, invalid-output checks | Held-out outcomes `MEASURED`; simulation accounting `DERIVED`; device costs `UNKNOWN`; empirical case study, not deployment-ready |
| CVaR Penalty-X | Full energy distribution and tail aggregation | `RICH_COST_INFORMATION` | Raw `phi_state` unchanged; membership-only `Lambda` not assigned | Rich energy samples, tail estimation, optimizer calls, validation | Held-out benefit `MEASURED`; sampling counts chargeable `DERIVED`; rich-oracle lower bound `UNKNOWN`; empirical case study |
| Warm-start QAOA | Classical solution, relaxation, or learned initialization | Posterior theorem if modeled as `S`; otherwise stronger explicit access | Basis density unchanged unless restricted; `Lambda` may rise and must be evaluated | Relaxation/training, advice bytes, warm-state circuit | Posterior bound `BOUNDED`; v3 implementation costs `UNKNOWN`; mechanistic only |
| Feasible-subspace state preparation | State supported on feasible solutions | Stronger structure oracle, or simulated membership calls charged | Working support can have feasibility fraction one; raw density still exists; `Lambda` can be one | Enumeration/loader, gates, ancillas, postselection, retries | `rL` simulation charge `DERIVED`; loader costs `UNKNOWN`; mechanistic only |
| Path-exchange mixer | Feasible paths and allowed exchange graph | Structured mixer; stronger unless simulated | Reachable support may shrink; `Lambda` is not automatically `M/K` | Path/neighbor generation, mixer graph, compilation, connectivity | Total-query implication `BOUNDED`; graph/gate costs `UNKNOWN`; mechanistic only |
| XY/constraint-preserving mixer | Algebraically preserved constraints | Fixed structure if instance-independent; otherwise structured access | Can remove some invalid states; residual resource feasibility remains | Compilation, routing, Trotterization, residual checks | Algebraic preservation `DERIVED`; hardware and residual costs `UNKNOWN`; mechanistic only |
| Grover feasible-state mixer | Feasible-state preparation and reflections | Stronger structure oracle unless simulated | Effective feasibility support may become one; raw `phi_state` unchanged; `Lambda` can be one | Loader/reflection synthesis, membership calls, postselection | `rL` charge `DERIVED`; circuit cost `UNKNOWN`; mechanistic only |
| Explicit feasible-basis QAOA | Full feasible list, objectives, indexing, mixer graph | `OUTSIDE_MEMBERSHIP_ONLY_MODEL`; enumeration exposure | Working feasibility fraction one; `Lambda=1`, but much richer information is supplied | Enumeration, objective evaluation, storage, indexing, graph construction, loading | Classical `argmin` exposure `DERIVED`; implementation costs `UNKNOWN`; mechanistic only |
| Classical corridor restriction | Instance-dependent subgraph/candidate set | Posterior structure or richer explicit preprocessing | Candidate-domain density may rise; raw density unchanged; `Lambda` depends on posterior, not size alone | Corridor computation, miss risk, patch/rebuild, validation | `K_eff` condition `BOUNDED`; build/reuse costs `UNKNOWN`; mechanistic only |
| Oracle-RCSP branch search | Explicit topology and counted status array | `EXPLICIT_ATTRIBUTE_QUERY_RCSP` | Relevant `phi_path=M/K`; raw `phi_state=M/2^(2K)`; constant advice `Lambda=M/K` | Attribute queries and amplitude amplification | Construction numerics `MEASURED`; qualified query order `BOUNDED`; QRAM/deployment cost `UNKNOWN`; mechanistic query model |

## Interpretation boundary

Changing the candidate domain changes the density relevant to that new search
problem; it does not retroactively change the old raw edge-bit statistic.
Changing `Lambda` requires instance-dependent information. Preserving a fixed
constraint can reduce invalid support without revealing the remaining random
feasible set. Every such distinction is reported separately in the CSV rather
than inferred from a method name.
