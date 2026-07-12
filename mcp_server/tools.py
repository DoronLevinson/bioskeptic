from dataclasses import asdict

from bioskeptic.resolver import disease as _disease
from bioskeptic.resolver import drug as _drug
from bioskeptic.resolver import target as _target


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


# The full tool set, in a stable order — shared by the MCP server and the web agent loop.
ALL = [resolve_target, suggest_targets, resolve_drug, suggest_drugs, resolve_disease, suggest_diseases]
