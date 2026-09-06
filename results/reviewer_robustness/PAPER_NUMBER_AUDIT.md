# Paper Number Audit

Generated: 2026-09-04T16:11:49.780840+00:00

Overall status: **PASS**

This audit recomputes the reviewer-robustness numbers displayed in the
assembled main article and Online Resource and verifies that each
formatted value occurs in the recursively expanded TeX source. The held-out
effect retained in the structured abstract is checked there specifically;
detailed robustness headlines are checked across the assembled main/ESM source.
The audit does not modify any result file.

| Item | Scope | Computed from artifact | Manuscript token | Occurrences | Status | Source |
|---|---|---:|---:|---:|---|---|
| A1 formal run count | assembled | `2016` | `2,016 runs` | 1 | PASS | `results/reviewer_robustness/A1_optimizer/optimizer_runs.csv` |
| A1 SciPy-count audit | assembled | `0/1512; null=504` | `1,512 runs` | 1 | PASS | `results/reviewer_robustness/A1_optimizer/optimizer_runs.csv` |
| A1 strict-stop missing counts | assembled | `504` | `504 SLSQP runs` | 1 | PASS | `results/reviewer_robustness/A1_optimizer/optimizer_runs.csv` |
| A1 COBYLA O0 nested failures | assembled | `28/168` | `28/168` | 3 | PASS | `results/reviewer_robustness/A1_optimizer/optimizer_summary.csv` |
| A1 COBYLA O3 nested failures | assembled | `38/168` | `38/168` | 2 | PASS | `results/reviewer_robustness/A1_optimizer/optimizer_summary.csv` |
| A1 COBYLA dual-PASS lower-energy/lower-feasibility pairs | assembled | `103/113` | `103/113` | 1 | PASS | `results/reviewer_robustness/A1_optimizer/optimizer_pass_subset.csv` |
| A1 COBYLA dual-PASS graph CI | assembled | `[0.5770,0.9971]` | `[0.5770,0.9971]` | 2 | PASS | `results/reviewer_robustness/A1_optimizer/optimizer_summary.csv` |
| A1 Nelder-Mead O0 nested failures | assembled | `54/168` | `54/168` | 2 | PASS | `results/reviewer_robustness/A1_optimizer/optimizer_summary.csv` |
| A1 Nelder-Mead O3 nested failures | assembled | `61/168` | `61/168` | 2 | PASS | `results/reviewer_robustness/A1_optimizer/optimizer_summary.csv` |
| A1 Nelder-Mead dual-PASS lower-energy/lower-feasibility pairs | assembled | `65/72` | `65/72` | 1 | PASS | `results/reviewer_robustness/A1_optimizer/optimizer_pass_subset.csv` |
| A1 Nelder-Mead dual-PASS graph CI | assembled | `[0.5796,1.2473]` | `[0.5796,1.2473]` | 2 | PASS | `results/reviewer_robustness/A1_optimizer/optimizer_summary.csv` |
| A1 SLSQP O0 nested failures | assembled | `46/168` | `46/168` | 2 | PASS | `results/reviewer_robustness/A1_optimizer/optimizer_summary.csv` |
| A1 SLSQP O3 nested failures | assembled | `72/168` | `72/168` | 2 | PASS | `results/reviewer_robustness/A1_optimizer/optimizer_summary.csv` |
| A1 SLSQP dual-PASS lower-energy/lower-feasibility pairs | assembled | `58/70` | `58/70` | 1 | PASS | `results/reviewer_robustness/A1_optimizer/optimizer_pass_subset.csv` |
| A1 SLSQP dual-PASS graph CI | assembled | `[0.6096,1.3458]` | `[0.6096,1.3458]` | 2 | PASS | `results/reviewer_robustness/A1_optimizer/optimizer_summary.csv` |
| B1 p2->p3 at 120 calls | assembled | `30/144 (20.8%)` | `30/144 (20.8\%)` | 1 | PASS | `results/reviewer_robustness/B1_depth_budget/nested_diagnostics.csv` |
| B1 p2->p3 at 240 calls | assembled | `31/144 (21.5%)` | `31/144 (21.5\%)` | 1 | PASS | `results/reviewer_robustness/B1_depth_budget/nested_diagnostics.csv` |
| B1 p2->p3 at 480 calls | assembled | `38/144 (26.4%)` | `38/144 (26.4\%)` | 1 | PASS | `results/reviewer_robustness/B1_depth_budget/nested_diagnostics.csv` |
| B1 p3->p4 at 120 calls | assembled | `45/144 (31.2%)` | `45/144 (31.2\%)` | 2 | PASS | `results/reviewer_robustness/B1_depth_budget/nested_diagnostics.csv` |
| B1 p3->p4 at 240 calls | assembled | `45/144 (31.2%)` | `45/144 (31.2\%)` | 2 | PASS | `results/reviewer_robustness/B1_depth_budget/nested_diagnostics.csv` |
| B1 p3->p4 at 480 calls | assembled | `47/144 (32.6%)` | `47/144 (32.6\%)` | 1 | PASS | `results/reviewer_robustness/B1_depth_budget/nested_diagnostics.csv` |
| B1 p4-p3 O0 G_feas at 120 calls | assembled | `0.7206; 10/10 positive` | `+0.7206` | 1 | PASS | `results/reviewer_robustness/B1_depth_budget/depth_budget_contrasts.csv` |
| B1 p4-p3 O3 G_feas at 120 calls | assembled | `0.2021; 10/10 positive` | `+0.2021` | 1 | PASS | `results/reviewer_robustness/B1_depth_budget/depth_budget_contrasts.csv` |
| A2 discovery graph-mean G_feas alpha=0.02 | assembled | `1.8982` | `1.8982` | 1 | PASS | `results/reviewer_robustness/A2_alpha/alpha_summary_graph.csv` |
| A2 discovery graph-mean G_feas alpha=0.05 | assembled | `1.9503` | `1.9503` | 1 | PASS | `results/reviewer_robustness/A2_alpha/alpha_summary_graph.csv` |
| A2 discovery graph-mean G_feas alpha=0.10 | assembled | `1.9889` | `1.9889` | 1 | PASS | `results/reviewer_robustness/A2_alpha/alpha_summary_graph.csv` |
| A2 discovery graph-mean G_feas alpha=0.25 | assembled | `1.9560` | `1.9560` | 1 | PASS | `results/reviewer_robustness/A2_alpha/alpha_summary_graph.csv` |
| A2 discovery graph-mean G_feas alpha=0.50 | assembled | `1.8445` | `1.8445` | 1 | PASS | `results/reviewer_robustness/A2_alpha/alpha_summary_graph.csv` |
| A2 discovery graph-mean G_feas alpha=1.00 | assembled | `1.6867` | `1.6867` | 1 | PASS | `results/reviewer_robustness/A2_alpha/alpha_summary_graph.csv` |
| A2 non-monotone task count | assembled | `54/56` | `54/56` | 2 | PASS | `results/reviewer_robustness/A2_alpha/alpha_summary_task.csv` |
| A2 alpha=1 objective endpoint | assembled | `2.4202861936828413e-13` | `2.42\times10^{-13}` | 2 | PASS | `results/reviewer_robustness/A2_alpha/alpha_runs.csv` |
| S1 matched initial-objective error | assembled | `2.0228263508670352e-13` | `2.02\times10^{-13}` | 1 | PASS | `results/reviewer_robustness/final_audits/alpha1_o0_equivalence.csv` |
| S1 matched discovery cells | assembled | `168` | `168 discovery cells` | 1 | PASS | `results/reviewer_robustness/final_audits/alpha1_o0_equivalence.csv` |
| S2 deeper-objective recomputation error | assembled | `1.5543122344752192e-15` | `1.55\times10^{-15}` | 1 | PASS | `results/reviewer_robustness/final_audits/nested_audit_cases.csv` |
| S2 embedded-objective recomputation error | assembled | `2.2204460492503131e-16` | `2.22\times10^{-16}` | 1 | PASS | `results/reviewer_robustness/final_audits/nested_audit_cases.csv` |
| S2 signed-regret recomputation error | assembled | `1.4155343563970746e-15` | `1.42\times10^{-15}` | 1 | PASS | `results/reviewer_robustness/final_audits/nested_audit_cases.csv` |
| S2 sampled audit cases | assembled | `24` | `24 stratified PASS/FAIL cases` | 1 | PASS | `results/reviewer_robustness/final_audits/nested_audit_cases.csv` |
| A3 fixed-endpoint P_feas ordering at 1000 shots | assembled | `94.8%` | `94.8\%` | 2 | PASS | `results/posthoc_finite_shot_endpoint_v1/aggregate.csv` |
| A3 fixed-endpoint P_feas ordering at 10000 shots | assembled | `99.3%` | `99.3\%` | 2 | PASS | `results/posthoc_finite_shot_endpoint_v1/aggregate.csv` |
| A3 fixed-endpoint P_feas ordering at 100000 shots | assembled | `100.0%` | `100.0\%` | 2 | PASS | `results/posthoc_finite_shot_endpoint_v1/aggregate.csv` |
| A3 mean O0/O3 alpha=.10 RMSE at 1000 shots | assembled | `0.04839285` | `0.04839` | 1 | PASS | `results/reviewer_robustness/A3_finite_shot/alpha_shot_estimator.csv` |
| A3 mean O0/O3 alpha=.10 RMSE at 10000 shots | assembled | `0.01569765` | `0.01570` | 1 | PASS | `results/reviewer_robustness/A3_finite_shot/alpha_shot_estimator.csv` |
| A3 mean O0/O3 alpha=.10 RMSE at 100000 shots | assembled | `0.00485944` | `0.00486` | 1 | PASS | `results/reviewer_robustness/A3_finite_shot/alpha_shot_estimator.csv` |
| A3 training effect EXACT_CANONICAL | assembled | `0.3599 [0.1641,0.5697], 9/10` | `0.3599` | 2 | PASS | `results/reviewer_robustness/A3_finite_shot/finite_shot_training_effect_summary.csv` |
| A3 training CI EXACT_CANONICAL | assembled | `[0.1641,0.5697]` | `[0.1641,0.5697]` | 2 | PASS | `results/reviewer_robustness/A3_finite_shot/finite_shot_training_effect_summary.csv` |
| A3 training effect SHOT_10000 | assembled | `0.1706 [-0.0106,0.3862], 8/10` | `0.1706` | 2 | PASS | `results/reviewer_robustness/A3_finite_shot/finite_shot_training_effect_summary.csv` |
| A3 training CI SHOT_10000 | assembled | `[-0.0106,0.3862]` | `[-0.0106,0.3862]` | 2 | PASS | `results/reviewer_robustness/A3_finite_shot/finite_shot_training_effect_summary.csv` |
| A3 training effect SHOT_1000 | assembled | `0.1246 [-0.0050,0.3351], 6/10` | `0.1246` | 2 | PASS | `results/reviewer_robustness/A3_finite_shot/finite_shot_training_effect_summary.csv` |
| A3 training CI SHOT_1000 | assembled | `[-0.0050,0.3351]` | `[-0.0050,0.3351]` | 2 | PASS | `results/reviewer_robustness/A3_finite_shot/finite_shot_training_effect_summary.csv` |
| A3 finite-shot training run count | assembled | `200` | `200/200 runs` | 1 | PASS | `results/reviewer_robustness/A3_finite_shot/finite_shot_training_runs.csv` |
| B2 exact optimum agreement | assembled | `140/140` | `140/140` | 6 | PASS | `results/reviewer_robustness/B2_classical/classical_summary.csv` |
| B2 median solve time | assembled | `50.0 microseconds` | `50.0` | 2 | PASS | `results/reviewer_robustness/B2_classical/classical_summary.csv` |
| B2 p95 solve time | assembled | `95.4 microseconds` | `95.4` | 2 | PASS | `results/reviewer_robustness/B2_classical/classical_summary.csv` |
| B2 maximum solve time | assembled | `188.1 microseconds` | `188.1` | 2 | PASS | `results/reviewer_robustness/B2_classical/classical_summary.csv` |
| B2 generated-label range | assembled | `median=13; max=30` | `median 13 and maximum 30` | 1 | PASS | `results/reviewer_robustness/B2_classical/classical_summary.csv` |
| Abstract held-out O3-O0 effect | abstract | `0.3547` | `$+0.3547$` | 1 | PASS | `results/finalization_audit_v1/claim_evidence_audit.csv` |
| Main/ESM frozen CVaR tail fraction | assembled | `alpha=0.10` | `\alpha=0.10` | 9 | PASS | `configs/phase2_confirmatory_v1.yaml` |
| Main/ESM alpha-neighborhood lower endpoint | assembled | `alpha=0.05` | `\alpha=0.05` | 3 | PASS | `results/reviewer_robustness/A2_alpha/alpha_summary_graph.csv` |
| Main/ESM alpha-neighborhood upper endpoint | assembled | `alpha=0.25` | `and 0.25` | 2 | PASS | `results/reviewer_robustness/A2_alpha/alpha_summary_graph.csv` |
| Main/ESM post-hoc maximum depth | assembled | `p=4` | `$p=4$` | 4 | PASS | `results/reviewer_robustness/B1_depth_budget/depth_budget_contrasts.csv` |
| Main/ESM 10k finite-shot training | assembled | `10,000 shots` | `10,000-shot` | 2 | PASS | `results/reviewer_robustness/A3_finite_shot/finite_shot_training_effect_summary.csv` |
| Main/ESM 1k finite-shot training | assembled | `1,000 shots` | `1,000-shot` | 2 | PASS | `results/reviewer_robustness/A3_finite_shot/finite_shot_training_effect_summary.csv` |

## Source fingerprints

- `configs/phase2_confirmatory_v1.yaml`: `0e87433b5b33ad10b58affe40162e1cbdbcd4bcb5ec45d9bd38c6222a5549a2f`
- `results/finalization_audit_v1/claim_evidence_audit.csv`: `f7cfb221efbfb394367182b71ecf1eb57e3aba9444f42be06a452a2923199a8b`
- `results/posthoc_finite_shot_endpoint_v1/aggregate.csv`: `f13be9815f00ff630d0f3c71aa5e9eb1bc413776cfa19135121b04b5cf98e0ac`
- `results/reviewer_robustness/A1_optimizer/optimizer_pass_subset.csv`: `38bc842554d2be9ad9a135da392b82a0841a3fec01f6b6094ac6e36cc5406887`
- `results/reviewer_robustness/A1_optimizer/optimizer_runs.csv`: `cb737fe085b62304360dba0f51c5dca128dad650cf1ddf3be3078c9548c10e96`
- `results/reviewer_robustness/A1_optimizer/optimizer_summary.csv`: `6060a61704ad5a4b06db3ccff8834397d6d46cb77e7a4ed55e0028003ff0ea01`
- `results/reviewer_robustness/A2_alpha/alpha_runs.csv`: `acf3f81b406efc3f5c59aa7c75335e377afadec59adb260221b61e229ddde948`
- `results/reviewer_robustness/A2_alpha/alpha_summary_graph.csv`: `86a4616090b6d13fd79ce17c8d347b391421988e44914f8845851bacd1925ac8`
- `results/reviewer_robustness/A2_alpha/alpha_summary_task.csv`: `a36ab598a6757706f98014a0084a607fee86ace4892389351b5d7786a710058a`
- `results/reviewer_robustness/A3_finite_shot/alpha_shot_estimator.csv`: `b7f703de171c4f2069c9a85522749b251a615fd1459dad33720eacca193f5e83`
- `results/reviewer_robustness/A3_finite_shot/finite_shot_training_effect_summary.csv`: `5a40579320d65b37573e7ac5106c287a4e34ae7548307a9b7d803f9fca33e215`
- `results/reviewer_robustness/A3_finite_shot/finite_shot_training_runs.csv`: `1b2d08dede17b34a4802dee001e794d0f66d90cb1b03cc5ad5d3ee1a941c9bad`
- `results/reviewer_robustness/B1_depth_budget/depth_budget_contrasts.csv`: `38531ee506e5b696254f1bbfc501fe6c3264acd01faf38bf9a9da8c269a0acdf`
- `results/reviewer_robustness/B1_depth_budget/nested_diagnostics.csv`: `aabdc62c87b59c6dd9351ae411f1d9e78eafbdb0034ba4bce9bdf6579ff8bf11`
- `results/reviewer_robustness/B2_classical/classical_summary.csv`: `d1caf6d4496f8692c20ca150d584e273c0f493a01b58dbcef5a04308a7a405ea`
- `results/reviewer_robustness/final_audits/alpha1_o0_equivalence.csv`: `d0f9ea262f8e43290807a73a33a3d9d9aa9b8defb5144a87e03f8724bd963beb`
- `results/reviewer_robustness/final_audits/nested_audit_cases.csv`: `af73611097d7b287955675267c550ce3a66643ff1f30fd824252c549f165e843`

## Verdict

All new manuscript numbers trace to formal result artifacts.
