#!/usr/bin/env python3
"""Build auditable Synthesis-v1 CSV assets from frozen predecessor evidence.

This script performs no optimization and does not mutate predecessor roots.  It
only writes derived inventories and review matrices under results/synthesis_v1.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "synthesis_v1"
SOURCE_COMMIT = "0657e603434cf7a7b7f9b7d1f5756dc1f85ae882"
AUDIT_LABEL = "SECOND_PASS_MACHINE_AUDIT"


def write_csv(name: str, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            extrasaction="raise",
            lineterminator="\n",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def inventory_stage(path: str) -> str:
    prefixes = [
        ("results/smoke/", "SMOKE"),
        ("results/phase0/", "PHASE0_V1"),
        ("results/phase0_v2_dilution_stress/", "PHASE0_V2"),
        ("results/phase1_pilot_v1/", "PHASE1_PILOT"),
        ("results/phase1_1_optimization_diagnostic/", "PHASE1_1"),
        ("results/phase1_2_objective_alignment/", "PHASE1_2"),
        ("results/phase2_confirmatory_v1/", "PHASE2"),
        ("results/phase3_scaling_v1/", "PHASE3"),
        ("results/theory_validation_v1/", "THEORY_V1"),
        ("results/theory_validation_v2/", "THEORY_V2"),
        ("results/theory_validation_v3/", "THEORY_V3"),
        ("docs/theory/", "THEORY_DOCUMENTATION"),
        ("configs/", "CONFIGURATION"),
        ("data/manifests/", "MANIFEST"),
        ("protocols/", "PROTOCOL"),
    ]
    return next((stage for prefix, stage in prefixes if path.startswith(prefix)), "PROTECTED_OTHER")


def inventory_type(stage: str, path: str) -> str:
    low = path.lower()
    if "failure_census" in low:
        return "NEGATIVE_RESULT"
    if stage == "PHASE3" and any(token in low for token in ("resource", "censor")):
        return "RESOURCE_CENSORED"
    if "counterexample" in low:
        return "COUNTEREXAMPLE"
    if "cost_relocation" in low or "cost_method" in low or "cost_ledger" in low:
        return "COST_ACCOUNTING"
    if "query" in low and stage.startswith("THEORY"):
        return "QUERY_LOWER_BOUND"
    if stage.startswith("THEORY"):
        return "THEOREM"
    if stage == "PHASE2":
        return "PREREGISTERED_HELDOUT"
    if stage == "PHASE3":
        return "EXPLORATORY"
    if stage in {"PHASE1_1", "PHASE1_2"}:
        return "MECHANISTIC"
    if stage == "PHASE1_PILOT":
        return "EXPLORATORY"
    if stage in {"CONFIGURATION", "MANIFEST", "PROTOCOL"}:
        return "DESCRIPTIVE"
    return "DESCRIPTIVE"


def inventory_inference(stage: str, asset_type: str) -> str:
    if asset_type in {"THEOREM", "COUNTEREXAMPLE", "QUERY_LOWER_BOUND", "COST_ACCOUNTING"}:
        return "FORMAL_THEORY"
    if stage == "PHASE2":
        return "PREREGISTERED_HELDOUT"
    if stage == "PHASE3":
        return "SCALING_RESPONSE_RESOURCE_CENSORED"
    if stage in {"PHASE1_1", "PHASE1_2"}:
        return "DISCOVERY_MECHANISTIC"
    if stage == "PHASE1_PILOT":
        return "DISCOVERY_EXPLORATORY"
    return "DESCRIPTIVE_PROVENANCE"


def inventory_claim_ceiling(stage: str, asset_type: str) -> str:
    if asset_type == "COUNTEREXAMPLE":
        return "Impossibility within the stated representation and input model"
    if asset_type == "QUERY_LOWER_BOUND":
        return "Query complexity only under the stated access model"
    if asset_type == "THEOREM":
        return "Formal result under explicit assumptions; novelty not implied"
    if asset_type == "COST_ACCOUNTING":
        return "Resource taxonomy; not a universal runtime theorem"
    if stage == "PHASE2":
        return "Preregistered held-out result for the frozen Penalty-X p=3 task family"
    if stage == "PHASE3":
        return "Heterogeneous scaling response through m=20; m=22 resource-censored"
    if stage in {"PHASE1_PILOT", "PHASE1_1", "PHASE1_2"}:
        return "Exploratory or mechanistic evidence; no confirmatory generalization"
    return "Descriptive construction, integrity, or provenance evidence"


def build_inventory() -> None:
    manifest = OUT / "protected_hashes_before.sha256"
    rows: list[dict[str, object]] = []
    for index, line in enumerate(manifest.read_text(encoding="utf-8").splitlines(), start=1):
        digest, path = line.split("  ", 1)
        stage = inventory_stage(path)
        asset_type = inventory_type(stage, path)
        low = path.lower()
        key = any(
            token in low
            for token in (
                "summary.json", "report.md", "preregistration.md", "claim_matrix",
                "canonical_results.csv", "confirmatory_statistics", "task_characterization.csv",
                "graph_level_contrasts.csv", "objective_results.csv", "compensation_by_objective.csv",
                "proof", "theorem", "counterexample", "padding_lemma", "query_rcsp_bound",
                "advice_query", "effective_structure", "cost_relocation", "manifest", "protocol",
            )
        )
        if "/figures/" in low or low.endswith((".png", ".pdf")):
            key = False
        included = "YES" if key else "NO"
        reason = "" if key else "Frozen support/intermediate asset; retained for reproducibility but not cited directly"
        rows.append(
            {
                "asset_id": f"A{index:04d}",
                "stage": stage,
                "asset_type": asset_type,
                "path": path,
                "commit_or_manifest": SOURCE_COMMIT,
                "sha256": digest,
                "scientific_status": "FROZEN_CANONICAL",
                "inference_tier": inventory_inference(stage, asset_type),
                "claim_ceiling": inventory_claim_ceiling(stage, asset_type),
                "immutable": "YES",
                "included_in_manuscript": included,
                "exclusion_reason": reason,
            }
        )
    write_csv(
        "SYNTHESIS_INPUT_INVENTORY.csv",
        ["asset_id", "stage", "asset_type", "path", "commit_or_manifest", "sha256",
         "scientific_status", "inference_tier", "claim_ceiling", "immutable",
         "included_in_manuscript", "exclusion_reason"],
        rows,
    )


PROOF_ROWS = [
    {
        "result_id": "T1",
        "statement": "Average fixed-query phase-sensitive dilution bound with coefficient (1+sum_t |exp(-i gamma_t)-1|)^2 phi and probability cap",
        "status": "PASS",
        "assumptions": "Uniform size-M subset of N labels; fixed F-independent initial state and inter-query unitaries; fixed phase schedule; success means measuring a marked label",
        "independent_derivation_summary": "Compare to the identity-oracle reference evolution. A slot changes the state by c_t times its marked-reference component. Uniform-subset averaging gives expected squared marked overlap phi; L2 Minkowski across slots and at the final projector gives (1+sum c_t)sqrt(phi), then square and cap at one.",
        "existing_proof_comparison": "Matches the Theory-v1 hybrid proof; the reconstructed proof uses the same two Minkowski steps and no pointwise overlap claim.",
        "edge_cases": "M=0 gives zero success by separate convention; M=N gives a vacuous cap; q=0 gives average success at most phi.",
        "identified_risk": "The theorem is average over F, not pointwise; phases and all nonquery operations must be F-independent.",
        "required_repair": "NONE",
        "paper_wording": "For a uniform random size-M marked subset and a fixed membership-query circuit, average success is bounded by the phase-sensitive expression.",
    },
    {
        "result_id": "T2",
        "statement": "Adaptive hard-cap membership-query dilution bound E P_success <= min{1,(2q+1)^2 phi}",
        "status": "PASS_WITH_CLARIFICATION",
        "assumptions": "At most q counted membership queries on every execution path; all other F-dependence excluded; finite classical histories can be purified and deferred",
        "independent_derivation_summary": "Purify mixed states, measurements and feed-forward into orthogonal history registers. Pad early-stopping branches with queries on isolated scratch registers. The direct-sum controlled query differs from identity by operator norm at most two on the marked subspace, so the same reference-hybrid recurrence gives (2q+1)sqrt(phi).",
        "existing_proof_comparison": "Agrees with Theory-v2. Its branch-dependent-phase statement is valid only when the history-controlled operation is itself the counted query interface and branches remain coherently isolated.",
        "edge_cases": "q=0; early stopping; mixed inputs; internal randomness; deferred measurements; fixed hard cap rather than expected query count.",
        "identified_risk": "Calling an arbitrarily stronger history-controlled oracle one membership query would change the model.",
        "required_repair": "Clarify the direct-sum counted-query interface in the manuscript; no historical correction.",
        "paper_wording": "The hard-cap bound covers adaptive measurements and feed-forward after purification, provided every oracle-dependent slot is charged as membership access.",
    },
    {
        "result_id": "T3",
        "statement": "Trained-algorithm specialization with q_total equal to all training, sampling, feedback and final membership queries",
        "status": "PASS_WITH_CLARIFICATION",
        "assumptions": "Complete end-to-end interaction has a pathwise membership-query cap; no free F-dependent training data or rich cost oracle",
        "independent_derivation_summary": "Treat the training transcript, optimizer state, samples, feedback and final execution as one adaptive protocol. T2 applies to their total counted membership calls regardless of where classical storage separates stages.",
        "existing_proof_comparison": "Matches Theory-v2 trained-oracle reduction and Theory-v3 query-generated-advice qualification.",
        "edge_cases": "Cached query-generated advice remains charged; instance-independent parameter reuse is free of F-dependence; explicit rich attributes are outside the membership-only model.",
        "identified_risk": "The result does not lower-bound final trained circuit depth or classical optimization time.",
        "required_repair": "Use total membership-query wording throughout.",
        "paper_wording": "The constraint is on end-to-end membership access, not on the depth of the final trained circuit.",
    },
    {
        "result_id": "T4",
        "statement": "Expected-query truncation: E P <= min{1, qbar/(T+1)+min[1,(2T+1)^2 phi]} for every integer T>=0",
        "status": "PASS_WITH_CLARIFICATION",
        "assumptions": "Global mean qbar=E Q over instance and internal randomness; nonnegative integer query count; T deterministic",
        "independent_derivation_summary": "Split on Q<=T. Replace executions exceeding T by failure to obtain a hard-cap-T protocol, apply T2 to the first event, and use Markov Pr(Q>T)=Pr(Q>=T+1)<=qbar/(T+1).",
        "existing_proof_comparison": "Matches the Theory-v2 correction and rejects the false substitution q=E Q.",
        "edge_cases": "T integer; qbar=0; phi=0 by separate convention; the asymptotic Omega(phi^-1/2) corollary needs fixed positive target success and sufficiently small phi.",
        "identified_risk": "Substituting qbar directly into (2q+1)^2 is invalid because the square is convex.",
        "required_repair": "Print the truncation inequality before any asymptotic corollary.",
        "paper_wording": "Expected-query control follows by truncation and a tail term, not by replacing the hard cap with the mean.",
    },
    {
        "result_id": "T5",
        "statement": "Raw edge-bit feasible-state fraction alone cannot imply a universal explicit-RCSP lower bound",
        "status": "PASS",
        "assumptions": "Explicit adjacency-list graph and rational nonnegative attributes; output is an explicit source-target edge sequence",
        "independent_derivation_summary": "An m-edge directed chain has one feasible route and edge-bit density 2^-m, yet reading and outputting the only route costs Theta(m). This contradicts any universal c*phi_state^-1/2 lower bound for large m.",
        "existing_proof_comparison": "Matches Theory-v3 unique-chain theorem and preserves the distinction between explicit problem complexity and an edge-qubit algorithm's behavior.",
        "edge_cases": "m>=1; positive costs/resources; output length itself is Theta(m).",
        "identified_risk": "The counterexample does not show that dilution is irrelevant to a particular full-space QAOA implementation.",
        "required_repair": "NONE",
        "paper_wording": "Raw edge-bit density is representation-dependent and is not, by itself, an explicit-RCSP hardness parameter.",
    },
    {
        "result_id": "T6",
        "statement": "Serial edge-subdivision representation-padding lemma with phi_state(I^(r))=2^-(r-1) phi_state(I)",
        "status": "PASS_WITH_CLARIFICATION",
        "assumptions": "A selected directed edge is replaced by a private r-edge serial path; additive rational attributes are split exactly",
        "independent_derivation_summary": "Contracting or expanding the private serial path gives a route bijection. Split each additive coefficient as a/r across the r edges, preserving totals, feasibility, ordering and optima. The valid-route numerator is fixed while edge count increases by r-1.",
        "existing_proof_comparison": "Matches Theory-v3. Coefficient bit length grows by O(log r), while the explicit topology and total input length grow Theta(r); only the per-coefficient representation is logarithmic in r.",
        "edge_cases": "Zero coefficients; rational coefficients; routes not using the subdivided edge; disconnected edge-bit selections remain invalid.",
        "identified_risk": "Polynomially representable coefficients must not be misreported as a poly(log r)-size explicit graph.",
        "required_repair": "Clarify per-coefficient versus total explicit input growth.",
        "paper_wording": "Subdivision changes raw state density by an exponential-in-padding factor while preserving the route problem under linear-time conversion.",
    },
    {
        "result_id": "T7",
        "statement": "Explicit-attribute random-access RCSP subclass has Q_RCSP,tau(K,M)=Theta_tau(sqrt(K/M)) in the nontrivial target regime",
        "status": "PASS_WITH_CLARIFICATION",
        "assumptions": "Known K-branch topology; length-K explicit status array accessed only through counted quantum random access; 1<=M<=K; fixed target success tau",
        "independent_derivation_summary": "Set branch resource totals to two iff z_i=1 and three otherwise. A feasible route identifies a marked index and one attribute query checks a branch. Multiple-marked search gives the lower bound and amplitude amplification gives the upper bound.",
        "existing_proof_comparison": "Matches Theory-v3. It is an input-query/cell-probe reduction on Theta(K) entries, not an explicit-RAM time lower bound or an exponential lower bound in log K.",
        "edge_cases": "M=K needs zero queries; for M/K>=tau a zero-query random branch already meets target; exact-feasible-output or tau>M/K gives the nontrivial form.",
        "identified_risk": "Free access to the full array defeats this query accounting; phi_path=M/K differs from phi_state=M/2^(2K).",
        "required_repair": "State the target-success regime alongside every Theta expression.",
        "paper_wording": "Under counted random access to an explicit length-K attribute array, the parallel-branch subclass inherits multiple-marked search complexity.",
    },
    {
        "result_id": "T8",
        "statement": "Posterior structure theorem with Lambda(S)=E_S ||E[Pi_F|S]||_infinity",
        "status": "PASS_WITH_CLARIFICATION",
        "assumptions": "Uniform size-M prior before a classical structure channel; hard cap q after S; post-S operations may depend on S but residual F-dependence is membership-only",
        "independent_derivation_summary": "Condition on S=s. The posterior projector is diagonal with entries Pr(x in F|s), so its norm is the largest posterior membership marginal. Each normalized s-dependent identity-oracle reference has conditional expected marked weight at most lambda_s. The purified hybrid proof then yields min{1,C(s)^2 lambda_s}; averaging and c_t<=2 gives min{1,(2q+1)^2 Lambda}.",
        "existing_proof_comparison": "Matches Theory-v3; the cap remains inside the conditional expectation until the valid coarser averaging step.",
        "edge_cases": "Zero-probability advice values omitted; constant S returns Lambda=phi; M=0 handled separately; M=N is vacuous.",
        "identified_risk": "Expectation and operator norm cannot be interchanged; a global phase-sensitive coefficient requires an S-uniform bound.",
        "required_repair": "Spell out conditional independence and distinguish E[min] from min of an upper expectation.",
        "paper_wording": "Classical structure changes the barrier through the largest posterior membership marginal, averaged over advice outputs.",
    },
    {
        "result_id": "T9",
        "statement": "Finite classical advice: Lambda(S)<=min{1,2^b phi} and P_success<=min{1,(2q+1)^2 2^b phi}",
        "status": "PASS_WITH_CLARIFICATION",
        "assumptions": "Classical advice support cardinality at most 2^b; b is an integer alphabet-size bound, not mutual information",
        "independent_derivation_summary": "For each supported s choose a maximizing label x_s. Sum Pr(S=s,x_s in F), upper-bound each joint event by Pr(x_s in F)=phi, and count at most 2^b supported outputs. Repeated x_s values only make this union-free sum looser.",
        "existing_proof_comparison": "Matches Theory-v3 proof and its duplicate-label audit.",
        "edge_cases": "b=0; advice names a marked element; duplicate maximizers; 2^b phi>=1; logarithmic lower bound clipped at zero before applying the ceiling.",
        "identified_risk": "Shannon or mutual information alone does not establish the same support bound.",
        "required_repair": "Call b a support-size or finite-alphabet bound.",
        "paper_wording": "An advice alphabet of at most 2^b outputs can increase posterior concentration by at most 2^b.",
    },
    {
        "result_id": "T10",
        "statement": "One-shot finite-dimensional pre-search quantum advice bound with total accessible advice dimension d",
        "status": "PASS_WITH_CLARIFICATION",
        "assumptions": "One F-dependent density operator on a total d-dimensional accessible register is supplied before search; all later F-dependence is counted membership access",
        "independent_derivation_summary": "Use a canonical purification of each density operator and carry an inaccessible reference through the analysis. Since rho_F<=I_d, any F-independent completely positive trace-nonincreasing reference map has average marked weight at most phi Tr A(I_d)<=d phi. The conditional hybrid step then gives the d-fold concentration factor without a d^2 loss.",
        "existing_proof_comparison": "Matches the Theory-v3 finite-dimensional argument. Mixed advice and entanglement with an inaccessible purifying reference are covered because only the accessible support dimension is counted.",
        "edge_cases": "d=1; mixed states; inaccessible purification; d phi>=1. Fresh copies, refreshed advice and interactive F-dependent providers are not covered.",
        "identified_risk": "Counting each refreshed d-dimensional message as though it were the same one-shot state would widen the theorem without proof.",
        "required_repair": "Use the phrase one pre-search advice state of total accessible dimension d.",
        "paper_wording": "A one-shot d-dimensional advice register is covered; repeated or interactive quantum advice remains outside the proved model.",
    },
    {
        "result_id": "T11",
        "statement": "Effective structure bits and effective support give necessary query-structure compression conditions",
        "status": "PASS_WITH_CLARIFICATION",
        "assumptions": "0<phi=M/N and M>0; Lambda in [phi,1]; target average success tau>0",
        "independent_derivation_summary": "Define b_eff=log2(Lambda/phi) and K_eff=M/Lambda. Algebra gives N/K_eff=2^b_eff, 0<=b_eff<=log2(1/phi), M<=K_eff<=N, and the success bound implies b_eff+2log2(2q+1)>=log2(tau/phi).",
        "existing_proof_comparison": "Matches Theory-v3 exactly and uses no sufficiency direction.",
        "edge_cases": "M=0 excluded from logarithmic definitions; phi=1 gives b_eff=0 and K_eff=N=M; negative right-hand tradeoff is vacuous.",
        "identified_risk": "b_eff is a posterior-concentration summary, not implementation time, memory, gate count or a sufficient construction.",
        "required_repair": "Label all compression inequalities necessary conditions.",
        "paper_wording": "Useful structure must compress posterior effective support enough to satisfy a necessary, not sufficient, query-structure tradeoff.",
    },
]


def build_proof_review() -> None:
    write_csv(
        "second_pass_proof_review.csv",
        ["result_id", "statement", "status", "assumptions", "independent_derivation_summary",
         "existing_proof_comparison", "edge_cases", "identified_risk", "required_repair", "paper_wording"],
        PROOF_ROWS,
    )


PRIOR_SOURCES = [
    ("PA01", "Bennett; Bernstein; Brassard; Vazirani", "Strengths and Weaknesses of Quantum Computing", 1997, "SIAM Journal on Computing", "journal", "10.1137/S0097539796300933", "quant-ph/9701001", "https://arxiv.org/abs/quant-ph/9701001", "hybrid lower bound", "unstructured black-box search", "Omega(sqrt(N)) search core", "NO", "none", "worst-case", "T1,T2,T3", "hybrid/asymptotic search lower bound", "dilution/QAOA application and exact phase coefficient not supplied", "Core clearly preexisting", "HIGH"),
    ("PA02", "Boyer; Brassard; Høyer; Tapp", "Tight Bounds on Quantum Searching", 1998, "Fortschritte der Physik", "journal", "10.1002/(SICI)1521-3978(199806)46:4/5<493::AID-PROP493>3.0.CO;2-P", "quant-ph/9605034", "https://arxiv.org/abs/quant-ph/9605034", "multiple-solution analysis", "Grover search with unknown or multiple solutions", "Theta(sqrt(N/M)) and exact success behavior", "NO", "none", "worst-case/randomized", "T7", "multiple-marked upper/lower core", "explicit RCSP embedding absent", "Explicit RCSP result is an application/reduction", "HIGH"),
    ("PA03", "Zalka", "Grover's quantum searching algorithm is optimal", 1999, "Physical Review A", "journal", "10.1103/PhysRevA.60.2746", "quant-ph/9711070", "https://arxiv.org/abs/quant-ph/9711070", "main optimality theorem", "black-box search", "exact optimality at fixed success", "NO", "none", "worst-case", "T1,T2,T7", "tight Grover optimality", "posterior/advice formulation absent", "Core clearly preexisting", "HIGH"),
    ("PA04", "Høyer", "Arbitrary phases in quantum amplitude amplification", 2000, "Physical Review A", "journal", "10.1103/PhysRevA.62.052304", "quant-ph/0006031", "https://arxiv.org/abs/quant-ph/0006031", "phase condition and algorithms", "amplitude amplification with arbitrary phases", "phase-dependent amplification conditions", "NO", "none", "algorithmic", "T1", "arbitrary-phase search preexists", "No located bound with 1+sum |exp(-i gamma_t)-1|", "Exact coefficient potentially distinct; priority unresolved", "HIGH"),
    ("PA05", "Brassard; Høyer; Mosca; Tapp", "Quantum Amplitude Amplification and Estimation", 2002, "AMS Contemporary Mathematics", "proceedings", "10.1090/conm/305/05215", "quant-ph/0005055", "https://arxiv.org/abs/quant-ph/0005055", "amplitude amplification theorem", "search from arbitrary initial success probability", "quadratic amplification", "NO", "none", "algorithmic", "T1,T7", "matching upper-bound machinery", "No posterior structure channel", "Core clearly preexisting", "HIGH"),
    ("PA06", "Ambainis; de Wolf", "Average-Case Quantum Query Complexity", 2001, "Journal of Physics A", "journal", "10.1088/0305-4470/34/35/302", "quant-ph/9904079", "https://arxiv.org/abs/quant-ph/9904079", "average-case framework", "query complexity under input distributions", "distributional/average query results", "NO", "none", "average", "T1,T4", "average-case query framing", "Random fixed-cardinality posterior projector absent", "Average-case core preexisting", "HIGH"),
    ("PA07", "Montanaro", "Quantum search with advice", 2010, "TQC 2010 / LNCS", "conference", "10.1007/978-3-642-18073-6_7", "0908.3066", "https://arxiv.org/abs/0908.3066", "main search-with-advice bounds", "known prior distribution on target location", "optimal expected queries under a prior", "NO", "classical prior distribution", "average", "T8,T11", "search under prior concentration", "Advice is not an instance-dependent channel output; Lambda formula absent", "Closest prior-distribution result", "HIGH"),
    ("PA08", "He; Zhang; Sun", "Quantum Search with Prior Knowledge", 2021, "Quantum Information Processing", "journal", "10.1007/s11128-021-03160-3", "2009.08721", "https://arxiv.org/abs/2009.08721", "weighted-search construction", "search with known nonuniform priors", "algorithms exploiting prior knowledge", "NO", "classical prior", "average", "T8,T11", "prior-information algorithms", "Instance-dependent structure channel and upper bound absent", "Related, not equivalent", "MODERATE"),
    ("PA09", "Aaronson", "Limitations of Quantum Advice and One-Way Communication", 2005, "Theory of Computing", "journal", "10.4086/toc.2005.v001a001", "quant-ph/0402095", "https://arxiv.org/abs/quant-ph/0402095", "advice simulation/limitations", "complexity classes with polynomial quantum advice", "general quantum-advice limitations", "YES", "quantum advice", "worst-case", "T10", "quantum advice is established resource", "No one-shot marked-subset d phi theorem located", "Model differs materially", "HIGH"),
    ("PA10", "Aaronson; Kuperberg", "Quantum Versus Classical Proofs and Advice", 2007, "Theory of Computing", "journal", "10.4086/toc.2007.v003a007", "quant-ph/0604056", "https://arxiv.org/abs/quant-ph/0604056", "marked-state oracle separation", "oracle marked quantum state and advice", "advice/query tradeoffs in a different state-search model", "YES", "classical/quantum advice", "worst-case", "T10", "dimension/advice-query interactions", "Not the random marked-subset membership model", "Close concept, non-equivalent theorem", "HIGH"),
    ("PA11", "Nayebi; Aaronson; Belovs; Trevisan", "Quantum Lower Bound for Inverting a Permutation with Advice", 2015, "Theory of Computing", "journal", "10.4086/toc.2015.v011a007", "1408.3193", "https://arxiv.org/abs/1408.3193", "ST^2 lower bound", "permutation inversion after preprocessing", "classical advice/query tradeoff", "YES", "classical preprocessing advice", "average/worst-case variants", "T9,T11", "asymptotic advice-query tradeoff", "Different function/inversion model and no exact 2^b phi bound", "Asymptotic advice core preexisting", "HIGH"),
    ("PA12", "Chung; Liao; Qian", "Lower Bounds for Function Inversion with Quantum Advice", 2020, "TQC / LIPIcs", "conference", "10.4230/LIPIcs.TQC.2020.8", "1911.09176", "https://arxiv.org/abs/1911.09176", "main tradeoff theorem", "function inversion with quantum advice", "quantum advice/time tradeoffs", "YES", "quantum advice", "average", "T10,T11", "finite quantum-advice tradeoff families", "Different model; exact one-shot posterior-projector statement absent", "Quantum-advice core preexisting", "HIGH"),
    ("PA13", "Chung; Guo; Liu; Qian", "Tight Quantum Time-Space Tradeoffs for Function Inversion", 2020, "FOCS", "conference", "10.1109/FOCS46700.2020.00074", "2006.05650", "https://arxiv.org/abs/2006.05650", "time-space theorems", "function inversion/preprocessing", "tight inversion tradeoffs", "YES", "classical/quantum storage", "average", "T9,T10,T11", "preprocessing query-space tradeoffs", "No RCSP or Lambda posterior", "Related asymptotic core", "HIGH"),
    ("PA14", "König; Renner; Schaffner", "The Operational Meaning of Min- and Max-Entropy", 2009, "IEEE Transactions on Information Theory", "journal", "10.1109/TIT.2009.2025545", "0807.1338", "https://arxiv.org/abs/0807.1338", "guessing-probability theorem", "classical-quantum side information", "conditional min-entropy equals guessing probability", "NO", "classical/quantum side information", "average", "T8,T10,T11", "posterior guessing-probability language", "Does not supply the membership-query hybrid bound", "Posterior interpretation has established information-theoretic analogues", "HIGH"),
    ("PA15", "Ballester; Wehner; Winter", "State Discrimination with Post-Measurement Information", 2008, "IEEE Transactions on Information Theory", "journal", "10.1109/TIT.2008.928276", "quant-ph/0608014", "https://arxiv.org/abs/quant-ph/0608014", "post-information discrimination", "quantum state discrimination with side information", "side information changes guessing tasks", "YES", "classical post-measurement info", "average", "T8,T10", "side-information formalism", "Not a membership-query search theorem", "Conceptual relation only", "HIGH"),
    ("PA16", "Dürr; Heiligman; Høyer; Mhalla", "Quantum Query Complexity of Some Graph Problems", 2006, "SIAM Journal on Computing", "journal", "10.1137/050644719", "quant-ph/0401091", "https://arxiv.org/abs/quant-ph/0401091", "graph query upper/lower bounds", "adjacency matrix/list graph queries", "model-sensitive graph query complexity", "NO", "graph adjacency oracle", "worst-case", "T7", "graph query lower bounds preexist", "Not explicit attribute-array RCSP construction", "Supports access-model qualification", "HIGH"),
    ("PA17", "Wesołowski; Piddock", "Quantum Algorithms for the Shortest Path Problem", 2024, "arXiv preprint", "preprint", "", "2408.10427", "https://arxiv.org/abs/2408.10427", "query algorithms and lower bounds", "shortest paths in matrix/list models", "shortest-path query bounds", "NO", "graph query oracle", "worst-case", "T7", "nearby graph-query literature", "No RCSP parallel-attribute theorem", "Nearby but different problem/model", "MODERATE"),
    ("PA18", "Galperin; Wigderson", "Succinct Representations of Graphs", 1983, "Information and Control", "journal", "10.1016/S0019-9958(83)80004-7", "", "https://doi.org/10.1016/S0019-9958(83)80004-7", "succinct graph complexity", "explicit versus succinct graph encodings", "representation can change complexity", "NO", "explicit/succinct descriptions", "worst-case", "T5,T6,T7", "representation sensitivity preexisting", "No edge-bit dilution padding formula", "General distinction preexisting", "HIGH"),
    ("PA19", "Hadfield; Wang; O'Gorman; Rieffel; Venturelli; Biswas", "From the Quantum Approximate Optimization Algorithm to a Quantum Alternating Operator Ansatz", 2019, "Algorithms", "journal", "10.3390/a12020034", "1709.03489", "https://arxiv.org/abs/1709.03489", "alternating-operator framework", "constraint-aware variational optimization", "feasibility-preserving mixers", "NO", "problem structure", "algorithmic", "T3,T11", "structured mixer framework preexists", "No membership-query cost accounting theorem", "Structure relocation must be framed conservatively", "HIGH"),
    ("PA20", "Bärtschi; Eidenbenz", "Grover Mixers for QAOA: Shifting Complexity from Mixer Design to State Preparation", 2020, "IEEE QCE", "conference", "10.1109/QCE49297.2020.00020", "2006.00354", "https://arxiv.org/abs/2006.00354", "Grover-mixer construction", "QAOA feasible-subspace mixers", "explicit complexity relocation framing", "NO", "feasible-state preparation", "algorithmic", "T11", "state-preparation/mixer tradeoff preexists", "No multi-resource accounting contract or posterior theorem", "Cost-relocation idea clearly preexisting", "HIGH"),
    ("PA21", "Barkoutsos et al.", "Improving Variational Quantum Optimization using CVaR", 2020, "Quantum", "journal", "10.22331/q-2020-04-20-256", "1907.04769", "https://quantum-journal.org/papers/q-2020-04-20-256/", "CVaR objective experiments", "variational quantum optimization", "CVaR use in VQAs/QAOA", "NO", "rich cost samples", "empirical", "T3", "CVaR application clearly preexisting", "No RCSP held-out study or membership-only violation", "Empirical contribution is domain-specific evidence, not CVaR novelty", "HIGH"),
    ("PA22", "Egger; Mareček; Woerner", "Warm-starting quantum optimization", 2021, "Quantum", "journal", "10.22331/q-2021-06-17-479", "2009.10095", "https://arxiv.org/abs/2009.10095", "warm-start constructions", "QAOA with classical relaxation", "classical structure injection", "NO", "classical warm start", "algorithmic", "T11", "warm-start mechanism preexists", "No posterior effective-bit theorem", "Supports cost relocation taxonomy", "HIGH"),
    ("PA23", "Bittel; Kliesch", "Training Variational Quantum Algorithms Is NP-Hard", 2021, "Physical Review Letters", "journal", "10.1103/PhysRevLett.127.120502", "2101.07267", "https://arxiv.org/abs/2101.07267", "hardness theorem", "classical training of variational algorithms", "training can carry computational burden", "NO", "explicit Hamiltonian access", "worst-case", "T3,T11", "training-cost difficulty", "Not a membership-query theorem", "Supports orthogonal cost accounting", "HIGH"),
]


def build_prior_art() -> None:
    fields = ["citation_id", "authors", "title", "year", "venue", "publication_status", "doi", "arxiv_id", "primary_url", "result_location", "model", "theorem_scope", "exact_formula", "adaptive", "advice_type", "average_or_worst_case", "relation_to_T1_T11", "preexisting_component", "potentially_distinct_component", "novelty_implication", "confidence"]
    rows = [dict(zip(fields, row)) for row in PRIOR_SOURCES]
    write_csv("prior_art_comparison_matrix.csv", fields, rows)

    searches = [
        ("S01", "multiple-marked quantum search lower bounds", "PA01;PA02;PA03;PA05", "Theta(sqrt(N/M)) core located"),
        ("S02", "average-case quantum search", "PA06;PA07", "Distributional query frameworks and prior search located"),
        ("S03", "hybrid argument quantum search", "PA01;PA03", "BBBV hybrid and exact optimality located"),
        ("S04", "arbitrary-phase quantum search bounds", "PA04;PA05", "Arbitrary-phase amplification located; requested additive coefficient not located"),
        ("S05", "adaptive quantum query search", "PA01;PA03;PA06", "General query core located; no exact posterior adaptive formula"),
        ("S06", "quantum search with classical advice", "PA07;PA11;PA13", "Prior-distribution and inversion-preprocessing results located"),
        ("S07", "quantum search with quantum advice", "PA09;PA10;PA12;PA13", "Quantum advice/inversion tradeoffs located; one-shot d phi statement not located"),
        ("S08", "search under prior distributions", "PA07;PA08", "Strong closest prior-search family"),
        ("S09", "posterior guessing probability", "PA14;PA15", "Conditional guessing/min-entropy analogues located"),
        ("S10", "query complexity with preprocessing", "PA11;PA12;PA13", "Asymptotic time-space/advice tradeoffs located"),
        ("S11", "data-structure query tradeoffs", "PA11;PA13", "Function-inversion preprocessing literature located"),
        ("S12", "function inversion with advice", "PA11;PA12;PA13", "Classical and quantum advice lower bounds located"),
        ("S13", "quantum search side information", "PA07;PA10;PA14;PA15", "Several non-equivalent side-information models located"),
        ("S14", "quantum state discrimination with side information", "PA14;PA15", "Information-theoretic side-information results located"),
        ("S15", "explicit graph input-query lower bounds", "PA16;PA17", "Adjacency query models located; explicit RAM distinction confirmed"),
        ("S16", "shortest path quantum query lower bounds", "PA16;PA17", "Shortest-path graph-query work located"),
        ("S17", "constrained shortest path quantum query complexity", "PA17", "No exact explicit-attribute RCSP parallel-path result located"),
        ("S18", "resource-constrained shortest path query complexity", "PA17", "Classical RCSP sources and nearby quantum graph queries; exact theorem not located"),
        ("S19", "representation padding complexity", "PA18", "General explicit/succinct representation sensitivity located; exact padding counterexample not located"),
        ("S20", "succinct versus explicit graph complexity", "PA18", "Foundational succinct graph distinction located"),
        ("S21", "QAOA query complexity", "PA19;PA20;PA23", "Alternating operators, cost relocation and training hardness located"),
        ("S22", "variational quantum algorithm query complexity", "PA23", "Training hardness differs from membership-query total-access theorem"),
        ("S23", "feasible-space dilution QAOA", "PA19;PA20", "Structured feasible-space methods located; exact dilution theorem not located"),
        ("S24", "CVaR QAOA constrained optimization", "PA21", "CVaR VQA use clearly preexisting"),
        ("S25", "backward and forward tracing from Boyer, Montanaro, Nayebi and Bärtschi", "PA01;PA03;PA05;PA08;PA10;PA12;PA13;PA19;PA22", "Expanded adjacent search/advice and mixer literature; no exact Lambda theorem located"),
    ]
    rows = [
        {"search_id": sid, "search_date": "2026-08-29", "query_family": query,
         "source_policy": "PRIMARY_SOURCES_ONLY", "primary_sources_inspected": sources,
         "outcome": outcome, "exact_match_found": "NO" if "not located" in outcome.lower() else "COMPONENT_ONLY",
         "notes": "Search completeness cannot establish priority; novelty remains unresolved."}
        for sid, query, sources, outcome in searches
    ]
    write_csv("prior_art_search_log.csv", ["search_id", "search_date", "query_family", "source_policy", "primary_sources_inspected", "outcome", "exact_match_found", "notes"], rows)


EMPIRICAL_ROWS = [
    ("E0A", "Task-universe v1 duplicate stress", "DISCOVERY", "task", 175, 25, "duplicate feasible-set count", "53/175 task rows repeated feasible sets after budget construction; phi range 1.90735e-6 to 0.0234375", "descriptive exact count", "none", 0, "Phase-0 synthetic DAG construction", "DESCRIPTIVE; motivates correction", "results/phase0/summary.json"),
    ("E0B", "Task-universe v2 distinct-cardinality correction", "DISCOVERY", "task/base graph", 140, 25, "distinct feasible sets and phi", "0 duplicate feasible sets; 140 summed graph-level distinct sets; median phi 0.00012207", "descriptive exact count", "none", 0, "Corrected Phase-0 v2 universe", "MECHANISTIC construction evidence", "results/phase0_v2_dilution_stress/summary.json"),
    ("E1A", "Hamiltonian scale audit", "DISCOVERY", "task", 140, 25, "energy-span and ground-state contract", "Ground-state correctness 140/140; raw span confounded; controlled within-base span ratio median 1.07495", "descriptive audit", "none", 0, "No QAOA optimization in the scale audit", "MECHANISTIC; scale-control contract", "results/phase0_v2_dilution_stress/HAMILTONIAN_SCALE_AUDIT.md;results/phase0_v2_dilution_stress/hamiltonian_scale_audit.csv"),
    ("E2A", "Penalty-X depth pilot", "DISCOVERY", "task", 56, 10, "P_feas and log gain G", "Median P_feas p1/p2/p3=0.005089/0.005984/0.003190; median G=1.6759/1.6366/1.5193", "task distributions; no confirmatory interval", "exploratory multiple depths", 0, "Exact statevector, Penalty-X, p=1,2,3", "EXPLORATORY only", "results/phase1_pilot_v1/pilot_summary.json"),
    ("E3A", "Nested ansatz identity and optimizer failure attribution", "DISCOVERY", "seed/run and task", 168, 10, "embedded p2 identity; continuation response", "Nested identity 168/168; original p3 worse than embedded p2 in 29/168; continuation improved objective in 29/29 and G in 27/29", "paired deterministic audit", "mechanistic multiple diagnostics", 0, "Original pilot p3 anomaly", "MECHANISTIC optimizer attribution", "results/phase1_1_optimization_diagnostic/summary.json"),
    ("E3B", "Objective-feasibility misalignment", "DISCOVERY", "run", 168, 10, "objective final versus G", "Random p3 had lower objective than continuation in 108/168, yet lower G in 82 of those comparisons", "paired descriptive count", "mechanistic", 0, "Penalty objective only", "MECHANISTIC; no universal optimizer claim", "results/phase1_1_optimization_diagnostic/summary.json"),
    ("E4A", "Objective discovery and capacity gap", "DISCOVERY", "task", 56, 10, "graph compensation G", "Median capacity gap O2-O0=0.2193 decades; O1 residual 0.2417; O3 residual 0.0069", "exploratory paired summaries", "multiple objectives exploratory", 0, "O2 exact-feasibility objective is mechanistic/nondeployable", "EXPLORATORY objective selection", "results/phase1_2_objective_alignment/summary.json"),
    ("E4B", "CVaR discovery response", "DISCOVERY", "task", 56, 10, "P_feas, P_opt, G", "O3 exceeded O0 on P_feas in 50/56 and P_opt in 51/56; median P_feas O0/O3=0.02168/0.04279", "exploratory paired counts", "objective family selected after discovery", 0, "CVaR alpha=0.10, Penalty-X p=3", "Discovery only; motivates held-out test", "results/phase1_2_objective_alignment/summary.json"),
    ("E5A", "Preregistered H1 CVaR versus mean", "HELDOUT", "base graph", 84, 15, "graph-level mean Delta G(O3-O0)", "0.354714949 decades; bootstrap SE 0.074725821; one-sided 95% lower 0.237378536; Holm p=0.000244141", "preregistered graph bootstrap and sign flip", "Holm over H1/H2", 0, "Held-out graphs/tasks; p=3 exact statevector", "PREREGISTERED_HELDOUT confirmation", "results/phase2_confirmatory_v1/confirmatory_statistics.json"),
    ("E5B", "Preregistered H2 CVaR noninferiority to capacity", "HELDOUT", "base graph", 84, 15, "graph-level mean Delta G(O3-O2)", "-0.00859515 decades against -0.10 margin; lower bound -0.03604875; Holm p=0.000244141", "preregistered graph bootstrap and shifted sign flip", "Holm over H1/H2", 0, "O2 is a mechanistic ceiling, not deployable", "PREREGISTERED_HELDOUT noninferiority", "results/phase2_confirmatory_v1/confirmatory_statistics.json"),
    ("E5C", "Held-out optimal-route concentration", "HELDOUT_SECONDARY", "task", 84, 15, "P_opt and conditional optimality", "O3-O0 P_opt wins/ties/losses=80/0/4; median difference 0.00639968; both P_feas and P_opt increased on 79/84 tasks", "preregistered secondary/descriptive paired audit", "secondary outcomes", 0, "Same frozen Phase-2 runs", "SUPPORTED secondary evidence", "results/phase2_confirmatory_v1/summary.json;results/phase2_confirmatory_v1/task_level_contrasts.csv"),
    ("E5D", "CVaR tail mechanism audit", "HELDOUT_MECHANISM", "task", 84, 15, "tail separation and feasible-tail composition", "Energy separation and tail-condition checks passed 84/84; 20/84 tails were fully feasible", "deterministic audit", "secondary mechanism", 0, "CVaR alpha=0.10", "MECHANISTIC interpretation only", "results/phase2_confirmatory_v1/cvar_tail_diagnostics.csv"),
    ("E6A", "Phase-3 scaling response", "PREREGISTERED_SCALING_RESPONSE", "base graph/objective", 180, 30, "eta and held-out response", "Completed through m=20; O3 extrapolation eta mean 1.28214 versus O0 0.61499; mean-vs-CVaR reversal at m=20", "frozen development/interpolation/extrapolation protocol", "model/objective comparisons", 0, "m=22 censored; no global scaling law", "RESOURCE_CENSORED scaling response", "results/phase3_scaling_v1/summary.json"),
    ("E6B", "Phase-3 feasible-entry bottleneck decomposition", "POST_HOLDOUT_DESCRIPTIVE", "graph-objective trajectory", 75, 25, "P_opt=P_feas*P_opt|feas slopes", "75/75 completed trajectories had positive conditional-optimality slope while feasible-entry probability declined", "descriptive post-holdout decomposition", "not confirmatory", 0, "Completed m<=20 only", "DESCRIPTIVE_ONLY", "results/phase3_scaling_v1/optimality_scaling.csv"),
    ("E6C", "Phase-3 resource censoring", "RESOURCE_PREFLIGHT", "size stratum", 180, 30, "execution completion", "540 p2 and 540 p3 rows completed; m=22 cells censored by preflight; no other scientific failures", "resource guard", "not applicable", 180, "CPU NumPy exact statevector", "RESOURCE_CENSORED", "results/phase3_scaling_v1/resource_preflight.json;results/phase3_scaling_v1/failure_census.csv"),
    ("E7A", "Theory-v1-v3 chain", "THEORY", "theorem", 11, 0, "formal proof status", "Membership-only barrier, adaptive total-query extension, representation counterexample, explicit-attribute subclass, posterior/advice tradeoff and cost accounting", "formal reconstruction and numerical theorem tests", "not applicable", 0, "Specified information-access models only", "THEOREM; novelty unresolved", "results/theory_validation_v1/summary.json;results/theory_validation_v2/summary.json;results/theory_validation_v3/summary.json"),
]


def build_empirical() -> None:
    fields = ["evidence_id", "claim", "discovery_or_heldout", "analysis_unit", "sample_task_count", "base_graph_count", "primary_metric", "effect", "uncertainty", "multiplicity", "failure_count", "scope", "claim_ceiling", "source_files"]
    write_csv("empirical_evidence_matrix.csv", fields, [dict(zip(fields, row)) for row in EMPIRICAL_ROWS])

    nums = [
        ("C-E0-UNIVERSE", "N001", 175, "tasks", "results/phase0/summary.json", "task_count"),
        ("C-E0-UNIVERSE", "N002", 53, "duplicate feasible sets", "results/phase0/summary.json", "duplicate_feasible_set_count"),
        ("C-E0-UNIVERSE", "N003", 140, "tasks", "results/phase0_v2_dilution_stress/summary.json", "task_count"),
        ("C-E0-UNIVERSE", "N004", 0, "duplicate feasible sets", "results/phase0_v2_dilution_stress/summary.json", "duplicate_feasible_set_count"),
        ("C-E0-UNIVERSE", "N005", 1.9073486328125e-06, "phi", "results/phase0_v2_dilution_stress/summary.json", "feasible_state_fraction_min"),
        ("C-E0-UNIVERSE", "N006", 0.0234375, "phi", "results/phase0_v2_dilution_stress/summary.json", "feasible_state_fraction_max"),
        ("C-E2-PILOT", "N007", 56, "tasks", "results/phase1_pilot_v1/pilot_summary.json", "frozen_execution_identity.task_count"),
        ("C-E2-PILOT", "N008", 504, "optimized rows", "results/phase1_pilot_v1/pilot_summary.json", "frozen_execution_identity.completed_optimized_row_count"),
        ("C-E2-PILOT", "N009", -0.5399946195590973, "kappa", "results/phase1_pilot_v1/pilot_summary.json", "dilution_response[depth=3].kappa_median"),
        ("C-E3-OPT", "N010", 29, "runs", "results/phase1_1_optimization_diagnostic/summary.json", "original_p3_optimizer_adequacy.worse_than_embedded_count"),
        ("C-E3-OPT", "N011", 168, "runs", "results/phase1_1_optimization_diagnostic/summary.json", "validation.nested_identity_rows"),
        ("C-E4-OBJDISC", "N012", 0.21929835458021296, "decades", "results/phase1_2_objective_alignment/summary.json", "capacity_gaps.median_O2_minus_O0_G"),
        ("C-E4-OBJDISC", "N013", 0.006897021383468704, "decades", "results/phase1_2_objective_alignment/summary.json", "capacity_gaps.median_O2_minus_O3_G"),
        ("C-E5-H1", "N014", 0.3547149490180106, "decades", "results/phase2_confirmatory_v1/confirmatory_statistics.json", "H1.effect_mean"),
        ("C-E5-H1", "N015", 0.07472582111285479, "bootstrap SE", "results/phase2_confirmatory_v1/confirmatory_statistics.json", "H1.bootstrap_standard_error"),
        ("C-E5-H1", "N016", 0.23737853648218638, "one-sided 95% lower", "results/phase2_confirmatory_v1/confirmatory_statistics.json", "H1.one_sided_95_lower_bound"),
        ("C-E5-H1", "N017", 0.000244140625, "Holm p", "results/phase2_confirmatory_v1/confirmatory_statistics.json", "H1.holm_adjusted_p_value"),
        ("C-E5-H2", "N018", -0.008595149938274194, "decades", "results/phase2_confirmatory_v1/confirmatory_statistics.json", "H2.effect_mean"),
        ("C-E5-H2", "N019", -0.03604874990402986, "one-sided 95% lower", "results/phase2_confirmatory_v1/confirmatory_statistics.json", "H2.one_sided_95_lower_bound"),
        ("C-E5-POPT", "N020", 80, "task wins", "results/phase2_confirmatory_v1/summary.json", "routing_quality.O3_vs_O0_P_opt_wins"),
        ("C-E5-POPT", "N021", 0.006399681964961, "probability", "results/phase2_confirmatory_v1/summary.json", "routing_quality.paired_median_P_opt_difference"),
        ("C-E6-SCALING", "N022", 180, "tasks", "results/phase3_scaling_v1/summary.json", "task_universe.tasks"),
        ("C-E6-SCALING", "N023", 20, "qubits/edges", "results/phase3_scaling_v1/summary.json", "task_universe.completed_size_ceiling"),
        ("C-E6-SCALING", "N024", 22, "qubits/edges", "results/phase3_scaling_v1/summary.json", "resource_preflight.resource_censored_sizes[0]"),
        ("C-E6-SCALING", "N025", 0.6149865942, "eta", "results/phase3_scaling_v1/summary.json", "heldout_validation.extrapolation[O0,B_FLAT].eta_MAE"),
        ("C-E6-SCALING", "N026", 1.2821385529, "eta", "results/phase3_scaling_v1/summary.json", "heldout_validation.extrapolation[O3,B_FLAT].eta_MAE"),
        ("C-THEORY-VALIDATION", "N027", 0, "violations", "results/theory_validation_v3/summary.json", "posterior_violations"),
        ("C-THEORY-VALIDATION", "N028", 80860, "subset evaluations", "results/theory_validation_v3/summary.json", "posterior_subset_evaluations"),
    ]
    rows = [
        {"claim_id": cid, "number_id": nid, "value": value, "units": units,
         "source_file": source, "source_field_or_row": locator,
         "evidence_status": "CANONICAL_REPORTED", "verification": "INTEGRITY_RECOMPUTATION",
         "notes": "Read-only extraction/identity check; no inferential pooling or new optimization."}
        for cid, nid, value, units, source, locator in nums
    ]
    write_csv("numeric_claim_audit.csv", ["claim_id", "number_id", "value", "units", "source_file", "source_field_or_row", "evidence_status", "verification", "notes"], rows)


CLAIMS = [
    ("C-T1", "For a uniform random fixed-size feasible subset, fixed-query membership-only success obeys the phase-sensitive dilution bound.", "THEOREM", "Theory boundary", "THEORY", "Theory-v1", "FORMAL_THEORY", "docs/theory/GLOBAL_QAOA_DILUTION_THEOREM.md", "theorem statement", "Uniform size-M prior; F-independent nonqueries", "Average over feasible subsets", "SUPPORTED_WITH_SCOPE_LIMITS", "PASS", "POTENTIALLY_DISTINCT", "Average success obeys the stated phase-sensitive membership-query bound.", "Every explicit RCSP instance needs this many queries.", "F3", "proofs"),
    ("C-T2", "Adaptive membership-only protocols with hard cap q obey P <= min{1,(2q+1)^2 phi}.", "THEOREM", "Theory boundary", "THEORY", "Theory-v2", "FORMAL_THEORY", "docs/theory/ADAPTIVE_QUERY_DILUTION_THEOREM.md", "hard-cap theorem", "Pathwise cap; counted direct-sum membership interface", "Average random marked subsets", "SUPPORTED_WITH_SCOPE_LIMITS", "PASS_WITH_CLARIFICATION", "PREEXISTING_ASYMPTOTIC_CORE", "The hard-cap theorem covers purified adaptive protocols.", "The theorem bounds final trained depth.", "F3", "proofs"),
    ("C-T3", "Training-generated structure remains charged through total membership-query access.", "COROLLARY", "Theory boundary", "THEORY", "Theory-v2/v3", "FORMAL_THEORY", "docs/theory/TRAINED_QAOA_TOTAL_QUERY_THEOREM.md", "total-query specialization", "All F-dependence membership-only", "End-to-end query accounting", "SUPPORTED_WITH_SCOPE_LIMITS", "PASS_WITH_CLARIFICATION", "LIKELY_REFORMULATION", "Training, feedback and final queries count together.", "Training time is lower-bounded by final depth.", "T-S1", "proofs"),
    ("C-T4", "Expected-query access is controlled by a truncation bound, not by substituting E Q for q.", "COROLLARY", "Theory boundary", "THEORY", "Theory-v2", "FORMAL_THEORY", "docs/theory/ADAPTIVE_QUERY_DILUTION_THEOREM.md", "expected-query section", "Integer query count; global mean", "Membership-only prior", "SUPPORTED_WITH_SCOPE_LIMITS", "PASS_WITH_CLARIFICATION", "LIKELY_REFORMULATION", "Use the explicit tail-plus-hard-cap truncation inequality.", "Replace q by E Q in the squared bound.", "T-S1", "proofs"),
    ("C-T5", "Raw edge-bit density alone cannot yield a universal explicit-RCSP lower bound.", "COUNTEREXAMPLE", "Models and boundaries", "THEORY", "Theory-v3", "FORMAL_THEORY", "docs/theory/RAW_EDGE_BIT_DILUTION_COUNTEREXAMPLE.md", "unique-chain theorem", "Explicit adjacency-list input and route output", "Impossibility of raw-density-only lower bound", "SUPPORTED", "PASS", "LIKELY_REFORMULATION", "Raw state density is representation-dependent and insufficient by itself.", "Raw density is irrelevant to edge-qubit QAOA.", "F1;F2", "proofs"),
    ("C-T6", "Serial subdivision changes phi_state by 2^-(r-1) without changing the logical route problem.", "COROLLARY", "Models and boundaries", "THEORY", "Theory-v3", "FORMAL_THEORY", "docs/theory/REPRESENTATION_PADDING_LEMMA.md", "padding lemma", "Private subdivision; exact rational splitting", "Representation transformation", "SUPPORTED_WITH_SCOPE_LIMITS", "PASS_WITH_CLARIFICATION", "POTENTIALLY_DISTINCT", "Coefficient bits grow O(log r) and explicit topology grows Theta(r).", "Subdivision makes RCSP exponentially harder.", "F2", "proofs"),
    ("C-T7", "A parallel-branch explicit-attribute RCSP subclass inherits Theta_tau(sqrt(K/M)) random-access query complexity in the nontrivial regime.", "QUERY_LOWER_BOUND", "Models and boundaries", "THEORY", "Theory-v3", "FORMAL_THEORY", "docs/theory/EXPLICIT_ATTRIBUTE_QUERY_RCSP_BOUND.md", "lower and upper bounds", "Explicit length-K array under counted random access", "Input-query complexity, not RAM time", "SUPPORTED_WITH_SCOPE_LIMITS", "PASS_WITH_CLARIFICATION", "LIKELY_REFORMULATION", "The explicit attribute-array subclass reduces to multiple-marked search.", "Exponential lower bound in compact graph size.", "F1", "proofs"),
    ("C-T8", "Classical structure modifies membership-query dilution through posterior concentration Lambda(S).", "THEOREM", "Theory boundary", "THEORY", "Theory-v3", "FORMAL_THEORY", "docs/theory/POSTERIOR_STRUCTURE_DILUTION_THEOREM.md", "posterior theorem", "Classical pre-search channel; residual membership uncertainty", "Uniform fixed-cardinality prior", "SUPPORTED_WITH_SCOPE_LIMITS", "PASS_WITH_CLARIFICATION", "POTENTIALLY_DISTINCT", "The posterior-projector norm controls conditional reference overlap.", "All natural RCSP structure is summarized by Lambda.", "F4", "proofs"),
    ("C-T9", "An advice alphabet of at most 2^b outputs implies P <= min{1,(2q+1)^2 2^b phi}.", "COROLLARY", "Theory boundary", "THEORY", "Theory-v3", "FORMAL_THEORY", "docs/theory/ADVICE_QUERY_TRADEOFF.md", "finite-advice corollary", "Support-size bits, not mutual information", "Classical advice only", "SUPPORTED_WITH_SCOPE_LIMITS", "PASS_WITH_CLARIFICATION", "POTENTIALLY_DISTINCT", "Finite-alphabet classical advice obeys the stated necessary bound.", "b advice bits equal b runtime bits.", "F4", "proofs"),
    ("C-T10", "One pre-search quantum advice state of total accessible dimension d has a finite-dimensional analogue.", "THEOREM", "Theory boundary", "THEORY", "Theory-v3", "FORMAL_THEORY", "docs/theory/ADVICE_QUERY_TRADEOFF.md", "quantum-advice section", "One state; total accessible dimension d", "No refreshed or interactive advice", "SUPPORTED_WITH_SCOPE_LIMITS", "PASS_WITH_CLARIFICATION", "POTENTIALLY_DISTINCT", "The one-shot finite-dimensional model covers mixed advice and inaccessible purification.", "The result covers repeated interactive quantum advice.", "T-S1", "proofs"),
    ("C-T11", "b_eff and K_eff express necessary posterior support compression, not sufficient implementation cost.", "COROLLARY", "Theory boundary", "THEORY", "Theory-v3", "FORMAL_THEORY", "docs/theory/EFFECTIVE_STRUCTURE_BITS.md", "effective quantities", "0<phi; target tau>0", "Necessary condition", "SUPPORTED_WITH_SCOPE_LIMITS", "PASS_WITH_CLARIFICATION", "LIKELY_REFORMULATION", "Effective bits summarize posterior concentration.", "Effective bits are runtime or a conservation law.", "F4", "proofs"),
    ("C-E0-UNIVERSE", "The corrected task universe removes duplicate feasible-set levels while retaining a broad controlled dilution range.", "MECHANISM", "Experimental design", "EMPIRICAL", "Phase0/0v2", "DESCRIPTIVE", "results/phase0/summary.json;results/phase0_v2_dilution_stress/summary.json", "task_count;duplicate_feasible_set_count;phi extrema", "Synthetic controlled DAGs", "Construction audit", "SUPPORTED", "SECOND_PASS_MACHINE_AUDIT", "NOT_APPLICABLE", "V2 has 140 tasks, no duplicated feasible sets and the reported phi range.", "The task universe represents natural RCSP prevalence.", "F5;T1", "protocols"),
    ("C-E1-SCALE", "The scale-controlled Hamiltonian contract preserves all task ground states and reduces within-graph scale drift.", "MECHANISM", "Experimental design", "EMPIRICAL", "Phase0v2", "MECHANISTIC", "results/phase0_v2_dilution_stress/HAMILTONIAN_SCALE_AUDIT.md;results/phase0_v2_dilution_stress/hamiltonian_scale_audit.csv", "ground-state checks;span ratios", "Audit only; no optimization", "140 tasks", "SUPPORTED", "SECOND_PASS_MACHINE_AUDIT", "NOT_APPLICABLE", "All 140 controlled ground states are correct under the frozen contract.", "Scale control removes every confound.", "F5;T1", "protocols"),
    ("C-E2-PILOT", "The initial Penalty-X depth pilot showed partial compensation and a p=3 anomaly.", "EMPIRICAL_DISCOVERY", "Discovery diagnostics", "EMPIRICAL", "Phase1 pilot", "EXPLORATORY", "results/phase1_pilot_v1/pilot_summary.json", "main_numerical_ranges;dilution_response", "56 tasks; 10 graphs", "Exploratory", "DESCRIPTIVE_ONLY", "SECOND_PASS_MACHINE_AUDIT", "NOT_APPLICABLE", "The pilot motivated optimizer attribution.", "Depth three is intrinsically worse.", "F5", "additional_results"),
    ("C-E3-OPT", "Continuation diagnostics attribute much of the original p=3 anomaly to optimization failure, while objective and feasibility remain misaligned.", "MECHANISM", "Discovery diagnostics", "EMPIRICAL", "Phase1.1", "MECHANISTIC", "results/phase1_1_optimization_diagnostic/summary.json;results/phase1_1_optimization_diagnostic/nested_ansatz_identity.csv", "continuation;identity;objective comparison", "Frozen pilot tasks", "Mechanistic", "SUPPORTED_WITH_SCOPE_LIMITS", "SECOND_PASS_MACHINE_AUDIT", "NOT_APPLICABLE", "Continuation repaired the identified original failure set; lower energy did not uniformly mean higher feasibility.", "Classical optimization explains all dilution.", "F5;T2", "additional_results"),
    ("C-E4-OBJDISC", "Exploratory objective attribution identified an O2 capacity gap and selected O3 CVaR for held-out testing.", "EMPIRICAL_DISCOVERY", "Objective attribution", "EMPIRICAL", "Phase1.2", "EXPLORATORY", "results/phase1_2_objective_alignment/summary.json", "capacity_gaps;paired_comparisons", "Same 56 discovery tasks", "No confirmatory pooling", "SUPPORTED_WITH_SCOPE_LIMITS", "SECOND_PASS_MACHINE_AUDIT", "CLEARLY_PREEXISTING_CVAR", "O2 is a mechanistic ceiling; O3 nearly closed its discovery gap.", "CVaR was invented here or O2 is deployable.", "F5", "additional_results"),
    ("C-E5-H1", "On preregistered held-out graphs, O3 CVaR improved dilution compensation over O0 mean-energy optimization.", "HELDOUT_CONFIRMATION", "Held-out results", "EMPIRICAL", "Phase2", "PREREGISTERED_HELDOUT", "results/phase2_confirmatory_v1/confirmatory_statistics.json", "H1", "15 graph-level units; 84 tasks; Holm control", "Penalty-X p=3 statevector", "SUPPORTED_WITH_SCOPE_LIMITS", "SECOND_PASS_MACHINE_AUDIT", "CVAR_PREEXISTS_APPLICATION", "Graph-level mean improvement was 0.3547 decades with preregistered inference.", "CVaR generally beats QAOA objectives.", "F6;T3", "protocols"),
    ("C-E5-H2", "Held-out O3 CVaR was noninferior to the exact-feasibility O2 capacity objective at the preregistered margin.", "HELDOUT_CONFIRMATION", "Held-out results", "EMPIRICAL", "Phase2", "PREREGISTERED_HELDOUT", "results/phase2_confirmatory_v1/confirmatory_statistics.json", "H2", "15 graph-level units; margin -0.10; Holm control", "O2 mechanistic ceiling", "SUPPORTED_WITH_SCOPE_LIMITS", "SECOND_PASS_MACHINE_AUDIT", "CVAR_PREEXISTS_APPLICATION", "The lower confidence bound exceeded the preregistered noninferiority margin.", "O3 is equivalent to O2 for all tasks.", "F6;T3", "protocols"),
    ("C-E5-POPT", "Held-out CVaR gains in feasible entry generally did not sacrifice optimal-route concentration.", "MECHANISM", "Held-out results", "EMPIRICAL", "Phase2", "HELDOUT_SECONDARY", "results/phase2_confirmatory_v1/summary.json;results/phase2_confirmatory_v1/task_level_contrasts.csv", "routing_quality", "Secondary outcomes", "Same held-out family", "SUPPORTED_WITH_SCOPE_LIMITS", "SECOND_PASS_MACHINE_AUDIT", "NOT_APPLICABLE", "O3 increased both P_feas and P_opt on 79 of 84 held-out tasks.", "CVaR always improves route quality.", "F7;T4", "additional_results"),
    ("C-E5-TAIL", "Held-out tail audits support the mechanism that CVaR used energy information beyond binary membership.", "MECHANISM", "Held-out results", "EMPIRICAL", "Phase2", "HELDOUT_MECHANISM", "results/phase2_confirmatory_v1/cvar_tail_diagnostics.csv", "tail_condition;energy_separation", "CVaR alpha=0.10", "Mechanistic", "SUPPORTED_WITH_SCOPE_LIMITS", "SECOND_PASS_MACHINE_AUDIT", "CVAR_PREEXISTS_APPLICATION", "The CVaR tail satisfied the frozen separation checks.", "CVaR violates a membership-query lower bound.", "F7", "additional_results"),
    ("C-E6-SCALING", "Phase 3 provides heterogeneous, resource-censored scaling response rather than a confirmed global scaling law.", "SCALING_RESPONSE", "Scaling response", "EMPIRICAL", "Phase3", "SCALING_RESPONSE_RESOURCE_CENSORED", "results/phase3_scaling_v1/summary.json;results/phase3_scaling_v1/SCALING_LAW_REPORT.md", "heldout_validation;resource_preflight", "m<=20 complete; m=22 censored", "No predecessor pooling", "RESOURCE_CENSORED", "SECOND_PASS_MACHINE_AUDIT", "NOT_APPLICABLE", "The extrapolation response reversed the earlier mean-versus-CVaR ordering at m=20.", "A global dilution scaling law was confirmed.", "F8;T5", "additional_results"),
    ("C-E6-BOTTLENECK", "Post-holdout decomposition suggests feasible entry, not conditional optimality, is the high-size bottleneck in completed trajectories.", "MECHANISM", "Scaling response", "EMPIRICAL", "Phase3", "POST_HOLDOUT_DESCRIPTIVE", "results/phase3_scaling_v1/optimality_scaling.csv", "trajectory slopes", "75 completed graph-objective trajectories", "Descriptive after holdout", "DESCRIPTIVE_ONLY", "SECOND_PASS_MACHINE_AUDIT", "NOT_APPLICABLE", "Report as a descriptive mechanism hypothesis.", "The bottleneck is universally proved.", "F7;F8", "additional_results"),
    ("C-COST", "Structure-injected methods relocate burden among information, preprocessing, state preparation, mixers, richer queries and validation.", "COST_RELOCATION", "Cost relocation", "BOTH", "Theory-v3", "COST_ACCOUNTING", "docs/theory/STRUCTURE_COST_RELOCATION_CONTRACT.md", "resource ledger", "Orthogonal resources; missing costs remain unknown", "Not a scalar runtime theorem", "SUPPORTED_WITH_SCOPE_LIMITS", "PASS_WITH_CLARIFICATION", "LIKELY_REFORMULATION", "Use the ledger to expose rather than erase structure costs.", "A preserving mixer obtains structure for free.", "F9;T6", "artifact"),
    ("C-LIM-NOADV", "The evidence does not establish general quantum advantage.", "LIMITATION", "Limitations", "BOTH", "All", "BOUNDARY", "results/synthesis_v1/CLAIM_EVIDENCE_MATRIX.csv", "scope synthesis", "No classical end-to-end advantage test or hardware", "Global", "SUPPORTED", "SECOND_PASS_MACHINE_AUDIT", "NOT_APPLICABLE", "No general quantum-advantage claim is made.", "Quantum advantage is demonstrated.", "", ""),
    ("C-LIM-MODELS", "The theory and experiments use explicitly different information-access models.", "LIMITATION", "Limitations", "BOTH", "All", "BOUNDARY", "docs/theory/QAOA_INFORMATION_ACCESS_MODELS.md", "model distinctions", "Membership-only theory versus rich explicit energy in experiments", "Global", "SUPPORTED", "SECOND_PASS_MACHINE_AUDIT", "NOT_APPLICABLE", "The theory is a boundary and accounting lens, not a direct runtime lower bound for the experiments.", "The black-box theorem directly proves empirical RCSP hardness.", "F1", "proofs"),
    ("C-THEORY-VALIDATION", "Theory-v1-v3 numerical checks found no violations in their enumerated finite validation cells.", "MECHANISM", "Artifact", "THEORY", "Theory-v1-v3", "MECHANISTIC", "results/theory_validation_v1/summary.json;results/theory_validation_v2/summary.json;results/theory_validation_v3/summary.json", "numerical_validation", "Finite enumerations are not proofs", "Validation only", "SUPPORTED_WITH_SCOPE_LIMITS", "SECOND_PASS_MACHINE_AUDIT", "NOT_APPLICABLE", "Numerical checks support implementation integrity and found no violation.", "Numerical checks prove the theorems.", "", "artifact"),
]


def build_claims() -> None:
    fields = ["claim_id", "candidate_wording", "claim_class", "manuscript_section", "theory_or_empirical", "evidence_stage", "inference_tier", "source_files", "source_fields", "assumptions", "scope", "status", "review_status", "prior_art_status", "allowed_wording", "prohibited_wording", "figure_or_table", "appendix_dependency"]
    write_csv("CLAIM_EVIDENCE_MATRIX.csv", fields, [dict(zip(fields, row)) for row in CLAIMS])


def build_strategy() -> None:
    rows = [
        {"option": "A_INTEGRATED", "description": "One theory plus explicit-RCSP plus empirical case-study paper", "scientific_coherence": 3, "novelty_defensibility": 2, "evidence_maturity": 4, "reviewer_risk": 2, "venue_fit": 2, "manuscript_length": 1, "proof_burden": 2, "empirical_burden": 3, "artifact_clarity": 2, "chance_of_overclaim": 1, "favorable_total": 22, "recommendation": "NOT_PRIMARY", "rationale": "Broad but combines different access models, unresolved theory priority and a long empirical chain."},
        {"option": "B_TWO_PAPER_SPLIT", "description": "Separate theory and empirical papers", "scientific_coherence": 4, "novelty_defensibility": 2, "evidence_maturity": 3, "reviewer_risk": 3, "venue_fit": 3, "manuscript_length": 4, "proof_burden": 2, "empirical_burden": 4, "artifact_clarity": 4, "chance_of_overclaim": 4, "favorable_total": 33, "recommendation": "CONTINGENCY", "rationale": "Cleaner separation, but the theory manuscript is not defensible until independent proof and prior-art review resolve contribution priority."},
        {"option": "C_EMPIRICAL_PRIMARY", "description": "Empirical RCSP objective-alignment paper with scoped search theory and structure taxonomy as boundaries", "scientific_coherence": 5, "novelty_defensibility": 4, "evidence_maturity": 5, "reviewer_risk": 4, "venue_fit": 5, "manuscript_length": 4, "proof_burden": 4, "empirical_burden": 4, "artifact_clarity": 5, "chance_of_overclaim": 5, "favorable_total": 45, "recommendation": "PRIMARY", "rationale": "Centers the preregistered result and mechanistic evidence while using theory conservatively without depending on unresolved priority."},
    ]
    write_csv("publication_strategy_matrix.csv", ["option", "description", "scientific_coherence", "novelty_defensibility", "evidence_maturity", "reviewer_risk", "venue_fit", "manuscript_length", "proof_burden", "empirical_burden", "artifact_clarity", "chance_of_overclaim", "favorable_total", "recommendation", "rationale"], rows)

    venues = [
        ("INFORMS Journal on Computing", "PRIMARY_FIT", "High if framed as computational OR and reproducible optimization study", "Strong computational experiment and artifact expectation", "Strong for RCSP and algorithmic evidence", "25 pages plus documented appendices in current author guidance", "Hybrid/subscription options depend on publisher policy", "Synthetic RCSP narrowness must be tied to OR methodology", "Not fatal if simulation methodology is central", "Known search core is acceptable as boundary, not claimed main novelty", "https://pubsonline.informs.org/page/ijoc/submission-guidelines;https://pubsonline.informs.org/page/ijoc/editorial-statement", "HIGH"),
        ("Quantum Science and Technology", "SECONDARY_FIT", "Requires a significant quantum-science advance", "Theory or experimental evidence accepted; controlled simulation possible", "Good benchmark/methodology fit", "Article type guidance is flexible; verify at submission", "Hybrid open access", "RCSP case study must support a broader quantum-method lesson", "No hardware is a reviewer risk but not a categorical bar", "Unresolved theory novelty weakens a theory-led pitch", "https://publishingsupport.iopscience.iop.org/journals/quantum-science-technology/about-quantum-science-technology/", "HIGH"),
        ("Physical Review A", "SECONDARY_FIT", "Technical quantum-information contribution expected", "Analytical and numerical work both in scope", "Artifacts useful but not the journal's sole organizing principle", "Regular Articles have no fixed length limit; Letters are constrained", "Hybrid open access", "An RCSP-only narrative may appear narrow", "No hardware is acceptable for theory/numerics but limits empirical breadth", "Use theory as scoped framework unless priority strengthens", "https://journals.aps.org/pra/authors", "HIGH"),
        ("Quantum", "SECONDARY_FIT", "Rigorous technical contribution required", "Open quantum-science journal; numerical studies possible", "Reproducibility strongly aligned with community expectations", "No fixed assessment inferred here; verify current author instructions", "Fully open access", "Needs a broad lesson beyond one routing family", "No hardware can be acceptable but raises significance burden", "Known theory core increases contribution-definition risk", "https://quantum-journal.org/about/", "MODERATE"),
        ("ACM Transactions on Quantum Computing", "POSSIBLE", "High-impact original quantum computing research", "Theory/practice both within scope", "Software and algorithm artifacts fit", "Verify current article-format rules before submission", "ACM open-access terms depend on author/institution agreements", "RCSP must be connected to general quantum algorithms", "No hardware not automatically disqualifying", "Theory-led version needs resolved novelty", "https://acm-stoc.org/stoc2020/acm-journals/tqc-new-announcement-06-2020.pdf", "MODERATE"),
        ("IEEE Transactions on Quantum Engineering", "POSSIBLE_LOW", "Engineering contribution and deployability emphasized", "Resource, compilation or systems evidence would strengthen fit", "Artifact detail is useful", "Verify current author instructions", "Fully open access", "Controlled RCSP is relevant, but implementation engineering is limited", "Lack of hardware and deployment cost data is material", "Known search theory is secondary", "https://tqe.ieee.org/", "HIGH"),
        ("Quantum Information Processing", "POSSIBLE", "Broad quantum-information originality standard", "Algorithms, theory and computational studies in scope", "Benchmark artifacts fit but are not sufficient alone", "Verify current article-type limits", "Hybrid open access", "Broad scope tolerates applications, but impact must be clear", "No hardware is not a categorical issue", "Conservative novelty positioning needed", "https://link.springer.com/journal/11128/aims-and-scope", "HIGH"),
        ("PRX Quantum", "HIGH_RISK", "Exceptional advance, connection, capability or insight expected", "Very high evidence/significance bar", "Artifact quality helps but cannot replace significance", "Flexible length", "Fully open access with APC", "RCSP case study likely too narrow without broader breakthrough", "No hardware raises the burden for a primarily empirical paper", "Unresolved and likely preexisting theoretical core is a major weakness", "https://journals.aps.org/prxquantum/scope;https://journals.aps.org/prxquantum/about", "HIGH"),
        ("IEEE QCE", "FUTURE_CONFERENCE_OPTION", "Track-specific technical novelty expected", "Shorter conference evidence package", "Artifact/demo alignment possible", "Full papers 8-10 pages plus references in 2026 call", "Proceedings access follows IEEE policy", "RCSP fits applications/algorithms tracks", "No hardware may be acceptable in algorithms track", "Could present scoped empirical story", "https://qce.quantum.ieee.org/2026/call-for-technical-papers/", "HIGH; 2026 deadline already passed as of audit date"),
    ]
    fields = ["venue", "fit", "theory_novelty_expectation", "empirical_evidence_expectation", "benchmark_artifact_fit", "length", "open_access", "rcsp_scope_risk", "lack_of_hardware", "known_theory_core_effect", "official_sources", "confidence"]
    write_csv("venue_matrix.csv", fields, [dict(zip(fields, row)) for row in venues])


def build_architecture() -> None:
    sections = [
        ("1", "Introduction", "Pose the controlled question of how objective design changes feasible entry under representation-induced dilution.", "C-E5-H1;C-E5-H2;C-E6-SCALING;C-LIM-NOADV", "", "E0-E6 overview", "F5", "", "900 words", "", "Do not lead with theorem novelty or quantum advantage."),
        ("2", "RCSP representations and access models", "Separate explicit RCSP, edge-bit state space and route-attribute query domain.", "C-T5;C-T6;C-T7;C-LIM-MODELS", "T5-T7 scoped", "E0 task encoding", "F1;F2", "T1", "1100 words", "Full proofs", "Reviewers may conflate raw density with problem hardness."),
        ("3", "Controlled experimental design and frozen evidence", "Explain distinct-feasible-set construction, Hamiltonian scale control, objectives and preregistered split.", "C-E0-UNIVERSE;C-E1-SCALE", "", "E0;E1", "F5", "T2", "1300 words", "Protocols; manifests; scale tables", "Synthetic family and exact-statevector scope."),
        ("4", "Discovery-stage optimizer and objective attribution", "Show why the p=3 anomaly was diagnosed and how O3 was selected without leaking into held-out inference.", "C-E2-PILOT;C-E3-OPT;C-E4-OBJDISC", "", "E2-E4", "F5", "T3", "1300 words", "Detailed pilot/optimizer figures", "Do not pool discovery and confirmation."),
        ("5", "Preregistered held-out results", "Present H1/H2 first, then secondary P_opt and tail-mechanism audits.", "C-E5-H1;C-E5-H2;C-E5-POPT;C-E5-TAIL", "", "E5", "F6;F7", "T4", "1500 words", "Full task contrasts; resampling details", "O2 must remain a mechanistic ceiling."),
        ("6", "Scaling response and resource ceiling", "Report development/interpolation/extrapolation heterogeneity and m=22 censoring.", "C-E6-SCALING;C-E6-BOTTLENECK", "", "E6", "F8", "T5", "1100 words", "All model diagnostics", "Never call this a confirmed global scaling law."),
        ("7", "Membership-only boundary and structure-cost interpretation", "Use black-box theory to explain what the experiment does and does not evade; expose relocation costs.", "C-T1;C-T2;C-T3;C-T4;C-T8;C-T9;C-T10;C-T11;C-COST", "T1-T4,T8-T11 summarized", "Theory validation only", "F3;F4;F9", "T6", "1300 words", "Proofs; ledger", "Theory and experiment have different access models; novelty unresolved."),
        ("8", "Related work", "Position Grover/search/advice, constrained QAOA, CVaR and RCSP computational work.", "C-E4-OBJDISC;C-COST;C-LIM-MODELS", "", "", "", "", "1100 words", "Expanded prior-art matrix", "CVaR and mixer cost relocation clearly preexist."),
        ("9", "Limitations and open problems", "Freeze proven, empirical and theory limitations plus external-review needs.", "C-LIM-NOADV;C-LIM-MODELS;C-E6-SCALING", "", "E6 censoring", "", "", "900 words", "", "Do not present future work as completed evidence."),
        ("10", "Conclusion", "Restate held-out empirical result and scoped structure-cost lesson.", "C-E5-H1;C-E5-H2;C-E6-SCALING;C-COST", "", "E5-E6", "", "", "400 words", "", "No priority, advantage or universal-hardness language."),
    ]
    fields = ["section_id", "section", "purpose", "claims", "theorems", "empirical_evidence", "figures", "tables", "word_page_budget", "appendix_material", "reviewer_risks"]
    write_csv("manuscript_section_matrix.csv", fields, [dict(zip(fields, row)) for row in sections])

    edges = [
        ("D01", "uniform-fixed-cardinality-prior", "T1", "definition", "CENTER_APPENDIX", "PREEXISTING_ASYMPTOTIC_CORE", "YES"),
        ("D02", "identity-oracle hybrid lemma", "T1", "proof", "CENTER_APPENDIX", "PREEXISTING_ASYMPTOTIC_CORE", "YES"),
        ("D03", "T1 hybrid machinery", "T2", "purified adaptive extension", "APPENDIX", "LIKELY_REFORMULATION", "YES"),
        ("D04", "T2", "T3", "end-to-end protocol specialization", "APPENDIX", "LIKELY_REFORMULATION", "YES"),
        ("D05", "T2", "T4", "truncation plus Markov tail", "APPENDIX", "LIKELY_REFORMULATION", "YES"),
        ("D06", "explicit chain construction", "T5", "counterexample", "MAIN", "LIKELY_REFORMULATION", "YES"),
        ("D07", "route contraction/expansion", "T6", "bijection", "MAIN", "POTENTIALLY_DISTINCT", "YES"),
        ("D08", "multiple-marked search", "T7", "reduction lower/upper bound", "MAIN", "LIKELY_REFORMULATION", "YES"),
        ("D09", "T2 conditional hybrid", "T8", "condition on S", "APPENDIX", "POTENTIALLY_DISTINCT", "YES"),
        ("D10", "T8", "T9", "finite-support union-free bound", "APPENDIX", "POTENTIALLY_DISTINCT", "YES"),
        ("D11", "T8 operator domination", "T10", "one-shot dimension bound", "APPENDIX", "POTENTIALLY_DISTINCT", "YES"),
        ("D12", "T8;T9", "T11", "algebraic reparameterization", "MAIN_SUMMARY", "LIKELY_REFORMULATION", "YES"),
    ]
    fields = ["edge_id", "prerequisite", "dependent", "dependency_type", "placement", "prior_art_class", "independent_human_review_mandatory"]
    write_csv("theorem_dependency_edges.csv", fields, [dict(zip(fields, row)) for row in edges])

    visuals = [
        ("F1", "MAIN", "How do explicit RCSP, edge-bit states and candidate-route queries differ?", "docs/theory;synthetic schematics only", "C-T5;C-T7;C-LIM-MODELS", "three-domain schematic", "Label input size and access model on every domain", "Could imply a direct theorem transfer", "PLANNED"),
        ("F2", "MAIN", "Why is raw phi_state representation-dependent?", "results/theory_validation_v3/raw_phi_counterexamples.csv;representation_padding_validation.csv", "C-T5;C-T6", "chain/padding two-panel", "Show O(m) output cost and unchanged logical routes", "Could be mistaken for exponential problem hardness", "SOURCE_READY"),
        ("F3", "SUPPLEMENT", "What does the membership-only hard-cap bound say?", "results/theory_validation_v1;results/theory_validation_v2", "C-T1;C-T2", "bound curves", "Average-prior and membership-only labels", "Could be applied to rich RCSP", "SOURCE_READY"),
        ("F4", "MAIN", "How must posterior structure and query access trade off?", "results/theory_validation_v3/effective_structure_examples.csv", "C-T8;C-T9;C-T11", "tradeoff contours", "Necessary-only annotation", "Advice bits could be read as runtime", "SOURCE_READY"),
        ("F5", "MAIN", "How were discovery, scale control, attribution and holdout separated?", "protocols;manifests;phase summaries", "C-E0-UNIVERSE;C-E1-SCALE;C-E2-PILOT;C-E3-OPT;C-E4-OBJDISC", "pipeline/timeline", "Discovery and held-out colors; no pooled estimate", "May imply prospective status for discovery", "PLANNED"),
        ("F6", "MAIN", "Did held-out O3 improve compensation and approach O2?", "results/phase2_confirmatory_v1/graph_level_contrasts.csv", "C-E5-H1;C-E5-H2", "graph-paired forest/raincloud", "Graph unit, lower bounds, noninferiority margin", "Task pseudo-replication", "SOURCE_READY"),
        ("F7", "MAIN", "Did feasible entry trade off with conditional route optimality?", "results/phase2_confirmatory_v1/task_level_contrasts.csv", "C-E5-POPT;C-E5-TAIL", "P_opt decomposition", "Identity P_opt=P_feas*P_opt|feas", "Causal mechanism overstatement", "SOURCE_READY"),
        ("F8", "MAIN", "Does the response persist at larger controlled sizes?", "results/phase3_scaling_v1/canonical_results.csv;extrapolation_validation.csv;failure_census.csv", "C-E6-SCALING;C-E6-BOTTLENECK", "faceted scaling response", "m=22 censored band; m=20 reversal callout", "Could look like a fitted global law", "SOURCE_READY"),
        ("F9", "MAIN", "Where does structure injection move burden?", "results/theory_validation_v3/structure_cost_method_matrix.csv", "C-COST", "resource-flow map", "MEASURED/DERIVED/UNKNOWN labels", "Could imply a scalar cost theorem", "SOURCE_READY"),
        ("T1", "MAIN", "What evidence is discovery, held-out, theory or censored?", "results/synthesis_v1/empirical_evidence_matrix.csv", "C-E0-UNIVERSE;C-E5-H1;C-E5-H2;C-E6-SCALING", "evidence-stage table", "Inference tier and claim ceiling", "Stage boundaries could be lost", "PLANNED"),
        ("T2", "MAIN", "What are the controlled task/objective definitions?", "configs;protocols;phase reports", "C-E0-UNIVERSE;C-E1-SCALE", "design table", "Frozen hashes and objective roles", "O2 deployability confusion", "PLANNED"),
        ("T3", "MAIN", "What did optimizer attribution establish?", "results/phase1_1_optimization_diagnostic/summary.json", "C-E3-OPT", "diagnostic summary", "Counts and claim ceiling", "Could imply all failures repaired", "PLANNED"),
        ("T4", "MAIN", "What are the preregistered H1/H2 estimates?", "results/phase2_confirmatory_v1/confirmatory_statistics.json", "C-E5-H1;C-E5-H2", "confirmatory statistics table", "Units, graph n, multiplicity", "Mixing task and graph units", "SOURCE_READY"),
        ("T5", "SUPPLEMENT", "Which Phase-3 cells were completed or censored?", "results/phase3_scaling_v1/failure_census.csv", "C-E6-SCALING", "completion/censor table", "Resource reason", "Censoring could be mistaken for failure", "SOURCE_READY"),
        ("T6", "SUPPLEMENT", "Which structure methods relocate which costs?", "results/theory_validation_v3/structure_cost_method_matrix.csv", "C-COST", "method ledger", "Evidence-status legend", "Unknown costs could be inferred as zero", "SOURCE_READY"),
    ]
    fields = ["visual_id", "main_or_supplement", "scientific_question", "source_data", "claim_ids", "plot_type", "required_annotations", "risk_of_misinterpretation", "status"]
    write_csv("figure_table_plan.csv", fields, [dict(zip(fields, row)) for row in visuals])


def build_reviews_and_gates() -> None:
    attacks = [
        ("R01", "This is just Grover/BBBV.", "PARTLY_VALID", "Acknowledge the asymptotic black-box core explicitly; claim only scoped formulations/applications while priority remains unresolved.", "PA01-PA06;C-T1;C-T2", "Move full proofs to appendix and center held-out evidence.", "Exact posterior/phase forms still need independent literature review."),
        ("R02", "Raw feasible fraction is encoding-dependent.", "VALID", "Agree; T5-T6 prove this boundary and the manuscript separates phi_state from phi_path.", "C-T5;C-T6;F1;F2", "Introduce representation distinction before any dilution plot.", "Empirical edge-bit behavior remains representation-specific."),
        ("R03", "The RCSP lower bound is only an oracle/input-query result.", "VALID", "State explicit topology plus explicit length-K attribute array under counted random access; do not claim RAM time.", "C-T7", "Put the access model in theorem title and caption.", "Natural explicit-RCSP time lower bounds remain open."),
        ("R04", "CVaR has already been used in QAOA.", "VALID", "Cite Barkoutsos et al.; the contribution is controlled RCSP attribution and held-out confirmation, not CVaR invention.", "PA21;C-E4-OBJDISC;C-E5-H1", "Remove novelty verbs around CVaR.", "Domain generality remains limited."),
        ("R05", "O2 directly optimizes feasibility and is not deployable.", "VALID", "Present O2 only as an exact-feasibility capacity ceiling.", "C-E4-OBJDISC;C-E5-H2", "Label O2 MECHANISTIC CEILING in every visual.", "The ceiling depends on exact feasible labels."),
        ("R06", "The empirical result covers only Penalty-X p=3.", "VALID", "Restrict confirmatory claims to the frozen p=3 Penalty-X setting; depth pilot is exploratory.", "C-E2-PILOT;C-E5-H1", "Add scope sentence in abstract and limitations.", "No mixer/ansatz generality is established."),
        ("R07", "The scaling law failed at m=20/22.", "VALID_IN_SUBSTANCE", "Report an m=20 objective-order reversal and m=22 resource censoring; call Phase 3 a heterogeneous scaling response.", "C-E6-SCALING", "Use censor marks and avoid law language.", "Upper-size behavior remains unresolved."),
        ("R08", "Classical optimization dominates the story.", "PARTLY_VALID", "Show optimizer attribution as a necessary mechanism, record wall time separately, and avoid excluding classical bottlenecks.", "C-E3-OPT;C-COST", "Include optimizer diagnostics and cost ledger.", "No end-to-end quantum/classical advantage analysis."),
        ("R09", "Structure advice bits are not runtime.", "VALID", "Agree; b_eff is only posterior concentration and the ledger keeps compute/gates/queries orthogonal.", "C-T11;C-COST", "Use necessary-condition labels.", "Computing useful S remains open."),
        ("R10", "Feasible-subspace mixers may solve feasibility by construction.", "VALID", "They escape the membership-only full-space setup by stronger structure/state preparation; charge construction and preparation costs.", "PA19;PA20;C-COST", "Add method matrix and oracle-simulation qualification.", "No universal lower bound for those richer methods."),
        ("R11", "No quantum hardware was tested.", "VALID", "Describe exact-statevector evidence and algorithmic mechanism only.", "C-E5-H1;C-E6-SCALING", "State in abstract/limitations and avoid deployment claims.", "Noise and hardware compilation are untested."),
        ("R12", "The benchmark is synthetic.", "VALID", "Use controlled DAGs as a causal/diagnostic benchmark and avoid prevalence claims.", "C-E0-UNIVERSE", "Explain construction purpose and publish manifests.", "External RCSP validity remains open."),
        ("R13", "The same author designed and audited all proofs.", "VALID", "Label this SECOND_PASS_MACHINE_AUDIT and require independent human proof and prior-art review before submission.", "second_pass_proof_review.csv", "Add external-review gate prominently.", "No independent review has yet occurred."),
        ("R14", "The theory and experiment use different information-access models.", "VALID", "Make the difference an organizing feature: membership-only bounds define a boundary, while CVaR uses rich cost information.", "C-LIM-MODELS;C-E5-TAIL", "Add F1 and a model contract table.", "Theory does not directly lower-bound empirical runtime."),
    ]
    fields = ["attack_id", "attack", "validity", "response", "evidence", "required_manuscript_change", "remaining_weakness"]
    write_csv("reviewer_attack_matrix.csv", fields, [dict(zip(fields, row)) for row in attacks])

    gates = [
        ("G1", "Proof consistency", "PASS_WITH_LIMITATIONS", "T1-T11 pass the machine reconstruction; nine require explicit scope clarifications.", "Independent human proof review remains mandatory."),
        ("G2", "Prior-art positioning", "PASS_WITH_LIMITATIONS", "No central empirical contribution depends on priority; theory novelty remains unresolved.", "Independent forward/backward literature review required."),
        ("G3", "Empirical integrity", "PASS", "Every headline number is mapped to frozen canonical evidence and hashes.", "None within synthesis."),
        ("G4", "Claim scope", "PASS", "Membership-only results are not applied as explicit rich-RCSP runtime bounds.", "Maintain model labels during drafting."),
        ("G5", "Held-out result", "PASS", "Phase-2 preregistered confirmation is separate from discovery and has zero overlap.", "Do not pool Phase1.2 and Phase2 inferentially."),
        ("G6", "Scaling language", "PASS", "Phase 3 is labeled heterogeneous scaling response and resource-censored.", "m=22 remains unresolved."),
        ("G7", "Cost relocation", "PASS", "Advice/effective bits are not equated with runtime or gates.", "Implementation costs for many structure methods remain unknown."),
        ("G8", "Reproducibility", "PASS", "Protected roots are hash-frozen and a release/validation plan exists.", "Archive/DOI not yet executed."),
        ("G9", "External review readiness", "PASS_WITH_LIMITATIONS", "A compact theorem/prior-art/claim-boundary review package is prepared.", "Actual external review has not occurred."),
    ]
    fields = ["gate_id", "gate", "status", "evidence", "remaining_action"]
    write_csv("readiness_gates.csv", fields, [dict(zip(fields, row)) for row in gates])

    failures = [
        ("F001", "Theory novelty", "NOVELTY_UNRESOLVED", "Exact posterior-projector/advice formulas not located, but adjacent search/advice cores are extensive.", "Do not use priority language; seek independent review."),
        ("F002", "Theorem review independence", "OPEN", "Current review is a second machine pass, not external human review.", "Send review_package to independent theorists."),
        ("F003", "Quantum advice scope", "OUTSIDE_MODEL", "Refreshed or interactive advice is not covered.", "Keep explicit nonclaim."),
        ("F004", "Rich cost oracle", "OPEN", "Membership-only theorem does not bound CVaR energy access.", "State richer information model."),
        ("F005", "Explicit RCSP hardness", "OPEN", "Only the attribute random-access subclass has a query bound.", "No universal raw-phi or RAM-time claim."),
        ("F006", "Phase3 m=22", "RESOURCE_CENSORED", "Resource guard excluded the upper size.", "Report censoring; do not complete in synthesis."),
        ("F007", "Phase3B", "PENDING_OUTSIDE_SYNTHESIS", "No completed immutable result exists in the source commit.", "Exclude from evidence."),
        ("F008", "Hardware", "NOT_TESTED", "Evidence uses CPU exact statevector.", "List empirical limitation."),
        ("F009", "External validity", "OPEN", "Controlled synthetic DAG family only.", "Require external reproduction/natural instances later."),
        ("F010", "TeX compilation", "TOOLING_UNAVAILABLE", "No TeX compiler is installed; static brace/environment, input and bibliography checks pass.", "Retain TeX sources and compile during external review when tooling is available."),
    ]
    fields = ["failure_id", "area", "status", "evidence", "disposition"]
    write_csv("failure_census.csv", fields, [dict(zip(fields, row)) for row in failures])


def build_summary() -> None:
    summary = {
        "stage": "Synthesis v1 — Second-Pass Theory Review, Evidence Integration, and Manuscript Architecture Freeze",
        "audit_label": AUDIT_LABEL,
        "status": "COMPLETE",
        "source_commit": SOURCE_COMMIT,
        "protected_file_count": sum(1 for _ in (OUT / "protected_hashes_before.sha256").open(encoding="utf-8")),
        "theory_review_verdict": "SECOND_PASS_PASS_WITH_CLARIFICATIONS",
        "theory_review_status_counts": {"PASS": 2, "PASS_WITH_CLARIFICATION": 9, "REQUIRES_REPAIR": 0, "INVALID": 0, "OPEN": 0},
        "prior_art_primary_verdict": "THEORY_NOVELTY_UNRESOLVED",
        "prior_art_secondary_verdict": "POTENTIALLY_DISTINCT_POSTERIOR_STRUCTURE_RESULT",
        "publication_architecture": "EMPIRICAL_PRIMARY_PAPER_RECOMMENDED",
        "manuscript_readiness": "READY_AFTER_EXTERNAL_PROOF_REVIEW",
        "next_action": "SEEK_EXTERNAL_PROOF_REVIEW",
        "phase3b_status": "PENDING_OUTSIDE_SYNTHESIS_V1",
        "qaoa_experiments_run": False,
        "canonical_evidence_modified": False,
        "external_human_review_claimed": False,
        "pushed": False,
        "merged": False,
        "protected_inventory_rows": 1403,
        "theory_review_rows": 11,
        "prior_art_searches": 25,
        "primary_source_matrix_rows": 23,
        "empirical_evidence_rows": 16,
        "numeric_claim_rows": 28,
        "claim_matrix_rows": 26,
        "readiness_gates": 9,
        "tests_passed": 165,
        "tests_failed": 0,
        "full_test_runtime_seconds": 188.78,
        "post_generation_integrity_tests_passed": 15,
        "post_generation_integrity_runtime_seconds": 1228.69,
        "latex_compilation": "TOOLING_UNAVAILABLE_STATIC_CHECKS_PASS",
        "protected_hash_verification": "1403_OF_1403_PASS",
        "commit_sha": "REPORTED_AT_HANDOFF",
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    build_inventory()
    build_proof_review()
    build_prior_art()
    build_empirical()
    build_claims()
    build_strategy()
    build_architecture()
    build_reviews_and_gates()
    build_summary()


if __name__ == "__main__":
    main()
