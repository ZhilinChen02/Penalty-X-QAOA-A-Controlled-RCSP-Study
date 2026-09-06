# Penalty scale control

The prospective `penalty_contract_v2_scale_controlled` isolates feasible-space dilution
from the raw magnitude of v2 integer resources. It does not replace the historical medium
contract and was selected without QAOA outcomes.

## Frozen formula

```text
S_resource = sum of edge resources for the base graph
P_resource = 1[resource_excess > 0] + min((resource_excess/S_resource)^2, 1)
S_flow = exact max flow_penalty_raw over the fixed edge-bit representation
P_flow = 1[flow_penalty_raw > 0] + min(flow_penalty_raw/S_flow, 1)
E = routing_cost + 172*P_flow + 172*P_resource
```

The hard indicator preserves constraint classification even for the smallest positive
violation. The bounded severity retains ordering information without allowing resource units
to dominate the diagonal scale. Base-graph scales are reused unchanged across stress budgets.

## Exhaustive validation

- Flow/resource classification preserved: 140/140 tasks.
- Valid, resource-feasible, exact-original-optimal ground state: 140/140 tasks.
- Current contract exact-original-optimal ground state: 140/140 tasks.
- QAOA outcomes consulted: no.
- Phase 1 executed: false.
