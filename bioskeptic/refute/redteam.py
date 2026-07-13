from dataclasses import dataclass, field

from bioskeptic.refute.core import ClaimTriple, Finding
from bioskeptic.refute.registry import BY_NAME, MECHANISMS

# red_team(claim) is deterministic: run every mechanism, collect what each returned into a Report.
# The weighing of those flags is no longer a separate assess() LLM pass — the chat agent reasons over
# the report itself (it gets each mechanism's reliability, blind spots, and precision) and curates the
# concerns it wants to surface via the add_concern tool. So this module just builds the evidence.


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
            report.not_applicable.append(m.name)
        elif finding.flagged:
            report.flagged.append(finding)
        else:
            report.clean.append(finding)
    return report


# Short human titles for the report panel (the NAMEs are machine ids).
_TITLES = {
    "direction_of_effect": "Genetic direction of effect",
    "not_causal_gene": "Causal gene at the locus",
    "cis_mr_null": "Causal effect (genetic experiment)",
    "text_mining_only": "Real evidence vs. text-mining",
    "haploinsufficient_inhibited": "Dosage sensitivity",
    "not_expressed_in_tissue": "Expressed in the affected tissue",
    "absent_from_driver_cell": "Present in the disease's driver cell",
    "mouse_ko_normal": "Mouse-knockout phenotype",
}

# Friendly source name from a link, for the panel's citation chips.
def _source_label(url: str) -> str:
    d = (url or "").lower()
    for key, label in (("proteinatlas", "Human Protein Atlas"), ("opentargets", "Open Targets"),
                       ("gtexportal", "GTEx"), ("pubmed", "PubMed"), ("epigraphdb", "EpiGraphDB"),
                       ("cbioportal", "cBioPortal"), ("clinicalgenome", "ClinGen"), ("gnomad", "gnomAD")):
        if key in d:
            return label
    return "source"


# Serialize a Report into one JSON-ready dict — the shape shared by the agent's memory (as a tool result)
# and the UI report panel. Each mechanism row carries what it checks + what it found + cited links, plus
# the metadata the agent needs to weigh and rank it: reliability, blind spots, benchmark, and precision.
def report_to_dict(report: Report) -> dict:
    def row(f: Finding) -> dict:
        info = BY_NAME.get(f.mechanism)
        return {
            "name": f.mechanism,
            "title": _TITLES.get(f.mechanism, f.mechanism.replace("_", " ").capitalize()),
            "what_it_checks": info.explanation if info else "",
            "finding": f.explanation,
            "sources": [{"label": _source_label(u), "url": u} for u in f.sources if u],
            # the agent reads these to judge and RANK each concern itself:
            "reliability": info.reliability if info else "",
            "blind_spots": info.reliability_advanced if info else "",
            "benchmark": info.evaluation if info else "",
            "precision": info.precision if info else None,   # None = too rare / disease-independent to grade
            "recall": info.recall if info else None,
        }

    c = report.claim
    return {
        "claim": {
            "drug": (c.drug.name if c.drug else None),
            "target": (c.target.symbol if c.target else None),
            "disease": (c.disease.name if c.disease else None),
            "direction": c.direction,
        },
        "flagged": [row(f) for f in report.flagged],
        "clean": [row(f) for f in report.clean],
        "not_applicable": [{"name": n, "title": _TITLES.get(n, n)} for n in report.not_applicable],
    }
