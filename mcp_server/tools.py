from dataclasses import asdict

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


# The resolver tool set (used to pin down entities) and the full set shared by MCP + the web agent loop.
RESOLVERS = [resolve_target, suggest_targets, resolve_drug, suggest_drugs, resolve_disease, suggest_diseases]
ALL = RESOLVERS + [build_report]
