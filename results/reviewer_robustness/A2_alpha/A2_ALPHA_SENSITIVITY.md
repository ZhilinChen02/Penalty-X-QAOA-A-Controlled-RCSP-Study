# A2 — CVaR alpha sensitivity

Discovery completion: 1008/1008 runs. Failed records across executed scopes: 0.

## Protocol

The discovery scan freezes alpha={0.02,0.05,0.10,0.25,0.50,1.00}, COBYLA, p=3, the original three p2-seed embeddings, and 120 actual objective calls. Alpha=0.10 remains the historical frozen choice; no sensitivity result can replace the preregistered held-out headline. Every non-0.10 held-out row is labelled POST_HOC_SENSITIVITY.

Manifest: `results/reviewer_robustness/manifests/manifest_alpha_sensitivity.json`.

## Numerical findings

The maximum observed |CVaR(alpha=1)−mean energy| is 2.420e-13; this is the mathematical endpoint control, not a claim that optimized feasibility must be monotone in alpha.

- alpha=0.02: graph mean G_feas difference versus alpha=1 is 0.2115, 95% graph-cluster bootstrap CI [0.0843, 0.3175].
- alpha=0.05: graph mean G_feas difference versus alpha=1 is 0.2636, 95% graph-cluster bootstrap CI [0.1345, 0.3864].
- alpha=0.1: graph mean G_feas difference versus alpha=1 is 0.3022, 95% graph-cluster bootstrap CI [0.2012, 0.4023].
- alpha=0.25: graph mean G_feas difference versus alpha=1 is 0.2693, 95% graph-cluster bootstrap CI [0.1771, 0.3659].
- alpha=0.5: graph mean G_feas difference versus alpha=1 is 0.1578, 95% graph-cluster bootstrap CI [0.0782, 0.2450].
- alpha=1: graph mean G_feas difference versus alpha=1 is 0.0000, 95% graph-cluster bootstrap CI [0.0000, 0.0000].
- Non-monotone optimized G_feas trajectories: 54/56 tasks (reported descriptively; no monotonicity was preregistered).

## Interpretation and limitation

Robustness is judged as a neighborhood around alpha=0.10, not by selecting the best alpha. Task rows are descriptive and graph-level intervals are post-hoc. These results do not alter the frozen confirmatory family.

## Claim impact

The complete discovery grid can determine whether alpha=0.10 is locally robust.
If the complete graph-level scan supports a neighborhood, the paper may report that neighborhood as post-hoc robustness while retaining alpha=0.10 as the sole frozen confirmatory choice; it must not select a replacement alpha from these results.

<!-- REVIEWER_ROBUSTNESS_SYNTHESIS -->

## Completed-result interpretation

- alpha=0.02 versus 0.10: graph-mean ΔG_feas=-0.0907, 95% graph bootstrap CI [-0.1571, -0.0286].
- alpha=0.05 versus 0.10: graph-mean ΔG_feas=-0.0386, 95% graph bootstrap CI [-0.0851, 0.0017].
- alpha=0.25 versus 0.10: graph-mean ΔG_feas=-0.0329, 95% graph bootstrap CI [-0.0739, 0.0139].
- alpha=0.5 versus 0.10: graph-mean ΔG_feas=-0.1444, 95% graph bootstrap CI [-0.2202, -0.0696].
- alpha=1 versus 0.10: graph-mean ΔG_feas=-0.3022, 95% graph bootstrap CI [-0.4024, -0.2032].

- Held-out POST_HOC_SENSITIVITY alpha=0.05 versus alpha=1: graph-mean ΔG_feas=0.2935, 95% CI [0.1602, 0.4338].
- Held-out POST_HOC_SENSITIVITY alpha=0.25 versus alpha=1: graph-mean ΔG_feas=0.2919, 95% CI [0.1943, 0.4007].
- Held-out POST_HOC_SENSITIVITY alpha=0.5 versus alpha=1: graph-mean ΔG_feas=0.1234, 95% CI [-0.0031, 0.2370].

The discovery curve has a robust neighborhood around 0.10: 0.05 and 0.25 are close on equal-weight graph means, while 0.02 and 0.50 are weaker but remain above the alpha=1 endpoint. The optimized curve is strongly non-monotone (54/56 tasks), which was allowed by protocol. Alpha=1 recovers the mean-energy objective numerically but does not authorize replacing the historical frozen alpha=0.10 choice.

**Claim impact:** supports that alpha=0.10 is not an isolated brittle choice; all held-out additions remain explicitly post-hoc.
