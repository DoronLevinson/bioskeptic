import json
from dataclasses import dataclass, field

from bioskeptic.data.llm import ask_claude
from bioskeptic.refute.core import ClaimTriple, Finding
from bioskeptic.refute.registry import MECHANISMS

# Per-mechanism "what it catches + its known mis-fire patterns", distilled from refute_mechanisms.md.
# assess() feeds the fired mechanisms' notes to Claude so it weighs each flag against its real blind
# spots (not just the flag text). Keep in sync with the Reliability notes in the docs.
RELIABILITY = {
    "direction_of_effect": "Fires when a clean, one-directional human-genetics signal opposes the drug's "
        "direction. High-confidence when it fires (it abstains on oncology and ion channels, where "
        "germline direction misleads).",
    "not_causal_gene": "Fires when a confident neighbouring gene out-ranks the target's L2G at the "
        "disease's GWAS loci (an innocent-passenger target). Mis-fire: partner subunits of the SAME "
        "protein complex read as 'out-ranked' but are the same drug target.",
    "cis_mr_null": "A well-powered cis-MR causal null. Strong when it fires, but narrow. Escapes: MR "
        "tests lifelong MODEST plasma-level modulation, not maximal pharmacology or intracellular/CNS "
        "action; single-cis-SNP estimates lack a pleiotropy check.",
    "text_mining_only": "Very high precision: fires only when the target-disease association's ONLY "
        "evidence type is literature co-mention (no genetic/clinical/expression evidence). Rarely wrong.",
    "haploinsufficient_inhibited": "Fires when a LOWERING drug targets a ClinGen-curated haploinsufficient "
        "gene (HI=3). Disease-independent (a target property), so it is not specific to this indication.",
    "not_expressed_in_tissue": "Target's bulk RNA absent from the disease's tissue (and its driver cell). "
        "Mis-fires: the drug acts on a DIFFERENT organ than the disease (diuretics act on the kidney); the "
        "target's functional cells are a rare fraction of the tissue (neuronal receptors, inducible enzymes).",
    "absent_from_driver_cell": "Target absent from the disease's driver cell (single-cell). High-recall "
        "but NOISY (~34% of its fires on real drugs are wrong): same 'works via another route/rare cell' "
        "confound as #7, and HPA's single-cell atlas doesn't resolve every driver cell.",
    "mouse_ko_normal": "The mouse knockout shows no disease-relevant phenotype. Noisy: mouse != human "
        "(a human disease may not be modelled in mouse), a paralog may compensate for the knockout, or the "
        "drug's mechanism differs from a full genetic knockout.",
}

# The red-team runs in two clearly separated steps:
#   1. red_team(claim)  — deterministic: run every mechanism, collect what each returned into a Report.
#   2. assess(report)   — an LLM pass: hand the Report to Claude for an overall read of the flags.


@dataclass
class Report:
    """What one red-team sweep over a claim produced (deterministic, no LLM).

    flagged        — Findings that fired (grounded concerns), most relevant first.
    clean          — mechanisms that ran and found no problem.
    not_applicable — names of mechanisms that abstained (missing data / out of scope).
    """
    claim: ClaimTriple
    flagged: list[Finding] = field(default_factory=list)
    clean: list[Finding] = field(default_factory=list)
    not_applicable: list[str] = field(default_factory=list)


# STEP 1 — run every mechanism in MECHANISMS over the claim and bucket the results.
# For each mechanism: call check(claim); Finding.flagged True -> flagged, False -> clean, None -> n/a.
# Pure collection — no judgement here; the flags stay suggestive.
def red_team(claim: ClaimTriple) -> Report:
    report = Report(claim=claim)
    for m in MECHANISMS:
        finding = m.check(claim)
        if finding is None:
            report.not_applicable.append(m.NAME)
        elif finding.flagged:
            report.flagged.append(finding)
        else:
            report.clean.append(finding)
    return report


@dataclass
class Assessment:
    """Claude's overall read of a Report (the flags remain suggestive — this is a weighing, not a verdict).

    overall         — a short narrative the agent can speak: does the claim look refuted, shaky, or fine?
    likely_misfires — fired flags Claude judges are probably false alarms, each with a one-line why
                      (using the mechanism's known blind spots, e.g. #7 firing on a drug that acts on
                      another organ).
    worth_digging   — fired flags Claude thinks may well be real and deserve a closer look.
    """
    overall: str
    likely_misfires: list = field(default_factory=list)
    worth_digging: list = field(default_factory=list)


# A plain-language description of the claim, for the assessment prompt.
def _claim_str(claim: ClaimTriple) -> str:
    parts = []
    if claim.drug and claim.drug.name:
        parts.append(claim.drug.name)
    sym = claim.target.symbol if claim.target else None
    if sym:
        parts.append(f"{claim.direction or 'targeting'} {sym}" if claim.direction else f"targeting {sym}")
    if claim.disease and claim.disease.name:
        parts.append(f"to treat {claim.disease.name}")
    return " ".join(parts) or "the claim"


# STEP 2 — hand the Report to Claude for an overall assessment: which fired flags are probably mis-fires
# (each Finding's explanation already states its mechanism's blind spot), which are worth digging into,
# and whether the claim looks refuted overall. The flags stay suggestive; this is a weighing, not a verdict.
def assess(report: Report) -> Assessment:
    if not report.flagged:
        return Assessment(overall="No grounded concerns fired — the applicable mechanisms found nothing "
                                  "to refute in this claim.")
    # each fired flag = its datapoint (the explanation) + that mechanism's documented reliability/blind-spots
    flags = "\n".join(
        f"- [{f.mechanism}] DATAPOINT: {f.explanation}\n"
        f"    mechanism reliability: {RELIABILITY.get(f.mechanism, '(no note)')}"
        for f in report.flagged)
    prompt = (
        f"You are BioSkeptic's reviewer weighing a red-team panel's flags on the claim: "
        f"{_claim_str(report.claim)}.\n\n"
        f"FIRED concerns — each is a cited datapoint, followed by that mechanism's documented reliability "
        f"and known mis-fire patterns:\n{flags}\n\n"
        f"Checked and clean: {', '.join(f.mechanism for f in report.clean) or 'none'}. "
        f"Not applicable / no data: {', '.join(report.not_applicable) or 'none'}.\n\n"
        "Weigh each fired flag against its documented mis-fire patterns and your biology knowledge — a "
        "flag whose known blind spot fits this exact claim is a likely mis-fire. Reply with "
        "ONLY a JSON object:\n"
        '{"overall": "<1-2 sentences: does the claim look refuted, shaky, or fine, and why>",\n'
        ' "likely_misfires": ["<mechanism>: <one line why it is probably a false alarm>"],\n'
        ' "worth_digging": ["<mechanism>: <one line why it may be a real problem>"]}')
    raw = ask_claude(prompt, max_tokens=700) or ""
    try:
        data = json.loads(raw[raw.find("{"):raw.rfind("}") + 1])
        return Assessment(overall=data.get("overall", ""),
                          likely_misfires=data.get("likely_misfires") or [],
                          worth_digging=data.get("worth_digging") or [])
    except Exception:
        return Assessment(overall=raw.strip() or "(assessment unavailable)")
