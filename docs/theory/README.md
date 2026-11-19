# Theory notes

These notes contain the theory behind Section 5 of the original submission
(the scope of the dilution interpretation). The revised manuscript condenses
that section into one paragraph of its Discussion and keeps the theorem
statements and proofs in Online Resource 1, Sec. S1.

The notes are frozen. Their SHA-256 hashes are recorded in
`results/manifest.json` and checked by `scripts/verify_release.py`; the scope
statements are also checked by `tests/test_theory_v2_scope.py` and
`tests/test_theory_v3_scope.py`. The numerical validations are in
`results/theory_validation_v1/` to `v3/`, written by the
`scripts/validate_*.py` drivers listed in [../EXPERIMENTS.md](../EXPERIMENTS.md).

## Theorems and bounds

| Note | Title |
| --- | --- |
| [GLOBAL_QAOA_DILUTION_THEOREM.md](GLOBAL_QAOA_DILUTION_THEOREM.md) ([.tex](GLOBAL_QAOA_DILUTION_THEOREM.tex)) | Global full-space feasible-space dilution theorem |
| [ADAPTIVE_QUERY_DILUTION_THEOREM.md](ADAPTIVE_QUERY_DILUTION_THEOREM.md) ([.tex](ADAPTIVE_QUERY_DILUTION_THEOREM.tex)) | Adaptive hard-cap feasible-space dilution theorem |
| [POSTERIOR_STRUCTURE_DILUTION_THEOREM.md](POSTERIOR_STRUCTURE_DILUTION_THEOREM.md) ([.tex](POSTERIOR_STRUCTURE_DILUTION_THEOREM.tex)) | Posterior structure dilution theorem |
| [TRAINED_QAOA_TOTAL_QUERY_THEOREM.md](TRAINED_QAOA_TOTAL_QUERY_THEOREM.md) | Trained-QAOA total-query theorem |
| [ADVICE_QUERY_TRADEOFF.md](ADVICE_QUERY_TRADEOFF.md) | Finite classical advice and membership-query tradeoff |
| [EXPLICIT_ATTRIBUTE_QUERY_RCSP_BOUND.md](EXPLICIT_ATTRIBUTE_QUERY_RCSP_BOUND.md) | Explicit-attribute-query RCSP bound |
| [REPRESENTATION_PADDING_LEMMA.md](REPRESENTATION_PADDING_LEMMA.md) | Edge-subdivision representation-padding lemma |

## Access models and accounting

| Note | Title |
| --- | --- |
| [QAOA_INFORMATION_ACCESS_MODELS.md](QAOA_INFORMATION_ACCESS_MODELS.md) | QAOA information-access models |
| [QAOA_QUERY_ACCOUNTING.md](QAOA_QUERY_ACCOUNTING.md) | QAOA query accounting |
| [EFFECTIVE_STRUCTURE_BITS.md](EFFECTIVE_STRUCTURE_BITS.md) | Effective structure bits and effective support |

## Limits, counterexamples and structure injection

| Note | Title |
| --- | --- |
| [COUNTEREXAMPLES_AND_ESCAPE_ROUTES.md](COUNTEREXAMPLES_AND_ESCAPE_ROUTES.md) | Counterexamples and escape routes |
| [RAW_EDGE_BIT_DILUTION_COUNTEREXAMPLE.md](RAW_EDGE_BIT_DILUTION_COUNTEREXAMPLE.md) | Raw edge-bit dilution is not a universal explicit-RCSP hardness parameter |
| [EXPLICIT_DESCRIPTION_BARRIER.md](EXPLICIT_DESCRIPTION_BARRIER.md) | Explicit-description barrier |
| [STRUCTURE_COST_RELOCATION_CONTRACT.md](STRUCTURE_COST_RELOCATION_CONTRACT.md) | Structure-injection cost relocation contract |
| [STRUCTURE_INJECTION_METHOD_MATRIX.md](STRUCTURE_INJECTION_METHOD_MATRIX.md) | Structure-injection method matrix |

## Claim boundaries, audits and prior art

| Note | Title |
| --- | --- |
| [CLAIM_BOUNDARY.md](CLAIM_BOUNDARY.md) | Claim boundary for the global dilution theorem |
| [THEORY_V2_CLAIM_BOUNDARY.md](THEORY_V2_CLAIM_BOUNDARY.md) | Theory Validation v2 claim boundary |
| [THEORY_V3_CLAIM_BOUNDARY.md](THEORY_V3_CLAIM_BOUNDARY.md) | Theory-v3 claim boundary |
| [PROOF_AUDIT.md](PROOF_AUDIT.md) | Adversarial proof audit |
| [RCSP_BRIDGE_AUDIT.md](RCSP_BRIDGE_AUDIT.md) | RCSP bridge audit |
| [PRIOR_ART_AUDIT.md](PRIOR_ART_AUDIT.md) | Primary-source prior-art audit |
| [STRUCTURE_TRADEOFF_PRIOR_ART.md](STRUCTURE_TRADEOFF_PRIOR_ART.md) | Structure/advice prior-art audit |
| [THEORY_PAPER_POSITIONING.md](THEORY_PAPER_POSITIONING.md) | Theory paper positioning after v2 |
| [prior_art.bib](prior_art.bib) | Bibliography of the audits |
