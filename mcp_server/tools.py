from dataclasses import asdict

from bioskeptic.data import clinicaltrials as _ct
from bioskeptic.data import openfda as _fda
from bioskeptic.data import pubmed as _pubmed
from bioskeptic.refute.core import ClaimTriple
from bioskeptic.refute.redteam import assess, red_team, report_to_dict
from bioskeptic.resolver import disease as _disease
from bioskeptic.resolver import drug as _drug
from bioskeptic.resolver import target as _target
from bioskeptic.resolver.disease import Disease as _Disease
from bioskeptic.resolver.disease import genetic_trait as _genetic_trait
from bioskeptic.resolver.drug import Drug as _Drug
from bioskeptic.resolver.target import Target as _Target


# A resolved passport dataclass -> JSON dict, including the computed `resolved` flag (a @property asdict drops).
def _passport(obj) -> dict:
    d = asdict(obj)
    d["resolved"] = obj.resolved
    return d


def resolve_target(query: str) -> dict:
    """Resolve a gene/protein target (name, Ensembl/Entrez id, or DRKG 'Gene::…') to its full ID passport."""
    return _passport(_target.resolve_target(query))


def suggest_targets(query: str, k: int = 5) -> list[dict]:
    """Suggest up to k target candidates (symbol, ensembl, name, biotype) for an ambiguous name, so the user can pick."""
    return [asdict(h) for h in _target.suggest_targets(query, k)]


def resolve_drug(query: str) -> dict:
    """Resolve a drug (name, ChEMBL/DrugBank id, or DRKG 'Compound::…') to its full ID passport."""
    return _passport(_drug.resolve_drug(query))


def suggest_drugs(query: str, k: int = 5) -> list[dict]:
    """Suggest up to k drug candidates (name, chembl id, modality) for an ambiguous name, so the user can pick."""
    return [asdict(h) for h in _drug.suggest_drugs(query, k)]


def resolve_disease(query: str) -> dict:
    """Resolve a disease (name, EFO/MONDO id, or DRKG 'Disease::MESH:…') to its full ID passport."""
    return _passport(_disease.resolve_disease(query))


def suggest_diseases(query: str, k: int = 5) -> list[dict]:
    """Suggest up to k disease candidates (name, description, efo) for an ambiguous name, so the user can pick."""
    return [asdict(h) for h in _disease.suggest_diseases(query, k)]


def build_report(target_symbol: str, target_ensembl: str, disease_name: str, disease_efo: str,
                 direction: str, drug_name: str = "", drug_chembl: str = "") -> dict:
    """Run the full BioSkeptic red-team panel (every refuting mechanism) plus an overall assessment on a
    resolved drug-target-disease claim, and return a structured report (flagged concerns, checks that
    passed, not-applicable checks, cited links, and the assessment). Call this ONCE, after the drug,
    target, and disease are all pinned down and resolved. `direction` is how the drug acts on the target:
    'inhibit' (lowers / blocks / antagonist / degrader) or 'activate' (raises / agonist)."""
    claim = ClaimTriple(
        target=_Target(symbol=target_symbol or None, ensembl=target_ensembl or None),
        disease=_Disease(name=disease_name or None, efo=disease_efo or None,
                         genetic_efo=_genetic_trait(f"{disease_name} {disease_efo}")),
        drug=(_Drug(name=drug_name or None, chembl_id=drug_chembl or None) if drug_name else None),
        direction=(direction or None),
    )
    report = red_team(claim)
    return report_to_dict(report, assess(report))


def search_pubmed(term: str, k: int = 6) -> dict:
    """Search PubMed and return the total match count plus the top k papers (PMID, title, year, journal,
    first author, link). Build `term` from the ids you already resolved, for precision: a gene symbol,
    drug name, or disease term, optionally tagged [tiab] to restrict to title/abstract and combined with
    AND/OR — e.g. 'SLC12A1[tiab] AND ototoxicity' or 'evolocumab[tiab] AND myocardial'. Use it to check
    how much is known about a concern and to cite specific papers; the count alone is a signal (thousands
    = well-studied, a handful = obscure)."""
    count, papers = _pubmed.search(term, k)
    return {"query": term, "total_count": count, "papers": [asdict(p) for p in papers]}


def search_trials(intervention: str = "", condition: str = "", k: int = 10) -> dict:
    """Search ClinicalTrials.gov for registered trials of a drug (intervention) in a disease (condition);
    either may be blank for a drug-only or disease-only search. Returns the total count plus the top k
    trials (NCT id, title, phase, status, why it stopped for terminated/withdrawn trials, link). Pass the
    resolved drug and disease names. This is the key check for 'has this been tried, and did it fail?' — a
    terminated late-phase trial or a why-stopped naming futility/toxicity is a strong red flag; and the
    absence of any trial is itself informative."""
    count, trials = _ct.search(intervention, condition, k)
    return {"intervention": intervention, "condition": condition,
            "total_count": count, "trials": [asdict(t) for t in trials]}


def fda_label(drug: str) -> dict | None:
    """Fetch the FDA-approved drug label for a drug (brand or generic name), returning its safety-relevant
    sections (boxed warning, warnings, contraindications, adverse reactions, indications) plus a DailyMed
    link. Returns null if the drug has no FDA label (novel or non-US drugs). Use it to ground on-target-
    toxicity and safety concerns in the official label rather than from memory."""
    lab = _fda.label(drug)
    return asdict(lab) if lab else None


# The resolver tool set (pin down entities), the dig tools (id-keyed retrieval for chasing concerns after
# the report), and the full set shared by MCP + the web agent loop.
RESOLVERS = [resolve_target, suggest_targets, resolve_drug, suggest_drugs, resolve_disease, suggest_diseases]
DIG = [search_trials, search_pubmed, fda_label]
ALL = RESOLVERS + [build_report] + DIG
