# Phase 3 task universe report

The complete structural universe was generated without QAOA outcomes. All task
identities and graph-disjoint splits were frozen before scientific optimization.

- Base graphs: 30
- Tasks: 180
- Construction rejections: 19
- Feasible-count agreement: 180/180
- Penalty contract: 180/180

## Coverage by size

 size_m  base_graphs  tasks  candidate_routes_min  candidate_routes_max      phi_min  phi_max    D_min   D_max
     12            5     30                     6                     6 2.441406e-04 0.001465 2.834209 3.61236
     14            5     30                     7                     8 6.103516e-05 0.000488 3.311330 4.21442
     16            5     30                     9                    11 1.525879e-05 0.000168 3.775087 4.81648
     18            5     30                    11                    12 3.814697e-06 0.000046 4.339359 5.41854
     20            5     30                    11                    16 9.536743e-07 0.000015 4.816480 6.02060
     22            5     30                    14                    17 2.384186e-07 0.000004 5.392211 6.62266

The exact identity `phi_state=N_feasible/2^m` reconstructs log10(phi) with
maximum error 8.882e-16.
