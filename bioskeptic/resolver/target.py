import urllib.parse
from dataclasses import dataclass, field

from bioskeptic.resolver.fetch import get_json, ot_query

MYGENE_URL = "https://mygene.info/v3/gene/{}"
GTEX_URL = "https://gtexportal.org/api/v2/reference/gene?geneId={}"
CHEMBL_TARGET_URL = "https://www.ebi.ac.uk/chembl/api/data/target?target_components__accession={}&format=json"
UNIPROT_PDB_URL = "https://rest.uniprot.org/uniprotkb/{}?fields=xref_pdb&format=json"
OT_PAGE = "https://platform.opentargets.org/target/{}"


# ================================================================================================
# What we return — the target's "ID passport" (identifiers only; payload lives in the data layer)
# ================================================================================================
@dataclass
class Target:
    symbol: str | None = None            # human label, e.g. "PCSK9"
    ensembl: str | None = None           # canonical gene id — our internal key
    uniprot: str | None = None           # protein id
    gencode: str | None = None           # versioned ensembl, for GTEx
    entrez: str | None = None            # NCBI Gene id — DRKG/NCBI/PubMed key
    chembl_target_id: str | None = None  # ChEMBL target — unlocks bioactivity (compounds vs this target)
    synonyms: list[str] = field(default_factory=list)  # alias symbols/names, for literature/trials search
    pdb: list[str] = field(default_factory=list)       # solved-structure ids (may be empty; often many)
    url: str | None = None               # Open Targets page, for a human to verify

    @property
    def resolved(self) -> bool:
        """True once we've reached a canonical Ensembl id — the bar for 'usable', even if extras are empty."""
        return self.ensembl is not None


@dataclass
class TargetHit:
    symbol: str | None       # candidate symbol
    ensembl: str | None      # its canonical Ensembl id
    name: str | None         # full gene name, e.g. "proprotein convertase subtilisin/kexin type 9"
    biotype: str | None      # e.g. "protein_coding" — lets a human spot a non-protein hit
    url: str | None          # Open Targets page, for a human to verify


# ================================================================================================
# Public entry points
# ================================================================================================
def resolve_target(query: str) -> Target:
    """Resolve a target in any shape (name, Ensembl id, Entrez id, or DRKG 'Gene::…') to a full ID passport."""
    raw = _strip_prefix(query)
    ensembl = _resolve_identity(raw)
    if ensembl is None:
        return Target()
    symbol, uniprot, synonyms = _ot_target(ensembl)
    if symbol is None:                          # OT doesn't recognise this ensembl -> treat as unresolved
        return Target()
    return Target(
        symbol=symbol,
        ensembl=ensembl,
        uniprot=uniprot,
        gencode=_gencode_from_ensembl(ensembl),
        entrez=_entrez_from_ensembl(ensembl),
        synonyms=synonyms,
        chembl_target_id=_chembl_target_from_uniprot(uniprot) if uniprot else None,
        pdb=_pdb_from_uniprot(uniprot) if uniprot else [],
        url=OT_PAGE.format(ensembl),
    )


def suggest_targets(query: str, k: int = 5) -> list[TargetHit]:
    """Return up to k valid (symbol, ensembl, name, biotype) candidates for a name, so chat can ask 'which did you mean?'."""
    return _search_targets(query, k)


# ================================================================================================
# Reach the canonical Ensembl
# ================================================================================================
def _strip_prefix(query: str) -> str:
    """'Gene::5122' -> '5122'; a bare name/id passes through unchanged."""
    q = (query or "").strip()
    return q.split("::", 1)[1] if "::" in q else q


def _resolve_identity(raw: str) -> str | None:
    """Route by input shape to the canonical Ensembl; the Entrez and name paths converge on _ensembl_from_symbol."""
    if raw.startswith("ENSG"):                          # already an Ensembl id — trust it
        return raw
    if raw.isdigit():                                   # Entrez id -> symbol -> canonical ensembl
        return _ensembl_from_symbol(_symbol_from_entrez(raw))
    return _ensembl_from_symbol(raw)                    # a name / symbol


def _ensembl_from_symbol(symbol: str | None) -> str | None:
    """OT search a symbol -> its canonical Ensembl; the MHC-safe choke point, picking the best exact match."""
    if not symbol:
        return None
    hits = _search_targets(symbol, k=5)
    for h in hits:                                      # prefer an exact symbol match over the raw top hit
        if h.symbol and h.symbol.upper() == symbol.upper():
            return h.ensembl
    return hits[0].ensembl if hits else None


def _symbol_from_entrez(entrez: str) -> str | None:
    """mygene -> the official symbol for an Entrez (NCBI Gene) id."""
    d = get_json(MYGENE_URL.format(urllib.parse.quote(entrez)) + "?fields=symbol")
    return (d or {}).get("symbol")


# ================================================================================================
# Fan out from the canonical Ensembl
# ================================================================================================
def _ot_target(ensembl: str) -> tuple[str | None, str | None, list[str]]:
    """One OT target(ensemblId) call -> (symbol, canonical UniProt, deduped alias synonyms)."""
    d = ot_query(
        "query($e:String!){ target(ensemblId:$e){ approvedSymbol"
        " proteinIds{ id source } symbolSynonyms{ label } nameSynonyms{ label } } }",
        {"e": ensembl},
    )
    t = (d or {}).get("target") or {}
    symbol = t.get("approvedSymbol")
    uniprot = _pick_uniprot(t.get("proteinIds") or [])
    synonyms: list[str] = []
    seen = set()
    for s in (t.get("symbolSynonyms") or []) + (t.get("nameSynonyms") or []):
        label = s.get("label")
        if label and label.upper() != (symbol or "").upper() and label not in seen:
            seen.add(label)
            synonyms.append(label)
    return symbol, uniprot, synonyms


def _pick_uniprot(protein_ids: list[dict]) -> str | None:
    """Prefer the reviewed Swiss-Prot accession, else any UniProt id."""
    swissprot = [p["id"] for p in protein_ids if p.get("source") == "uniprot_swissprot"]
    if swissprot:
        return swissprot[0]
    any_uniprot = [p["id"] for p in protein_ids if str(p.get("source", "")).startswith("uniprot")]
    return any_uniprot[0] if any_uniprot else None


def _entrez_from_ensembl(ensembl: str) -> str | None:
    """mygene -> the Entrez (NCBI Gene) id for an Ensembl gene (also canonicalises an Entrez-input target)."""
    d = get_json(MYGENE_URL.format(urllib.parse.quote(ensembl)) + "?fields=entrezgene")
    e = (d or {}).get("entrezgene")
    return str(e) if e is not None else None


def _gencode_from_ensembl(ensembl: str) -> str | None:
    """GTEx reference/gene -> the versioned GENCODE id (e.g. ENSG….11) that GTEx data is keyed by."""
    d = get_json(GTEX_URL.format(urllib.parse.quote(ensembl)))
    data = (d or {}).get("data") or []
    return data[0].get("gencodeId") if data else None


def _chembl_target_from_uniprot(uniprot: str) -> str | None:
    """ChEMBL target by UniProt accession -> the SINGLE PROTEIN target's chembl id (skips PPI/complex targets)."""
    d = get_json(CHEMBL_TARGET_URL.format(urllib.parse.quote(uniprot)))
    for t in (d or {}).get("targets") or []:
        if t.get("target_type") == "SINGLE PROTEIN":
            return t.get("target_chembl_id")
    return None


def _pdb_from_uniprot(uniprot: str) -> list[str]:
    """UniProt cross-references -> the list of PDB structure ids for this protein (may be empty)."""
    d = get_json(UNIPROT_PDB_URL.format(urllib.parse.quote(uniprot)))
    return [x["id"] for x in (d or {}).get("uniProtKBCrossReferences") or [] if x.get("database") == "PDB"]


# ================================================================================================
# Open Targets search (shared by suggest_targets and _ensembl_from_symbol)
# ================================================================================================
_SEARCH_GQL = """
query($q:String!, $k:Int!){
  search(queryString:$q, entityNames:["target"], page:{index:0, size:$k}){
    hits{ id object{ ... on Target{ approvedSymbol approvedName biotype } } }
  }
}
"""


def _search_targets(query: str, k: int) -> list[TargetHit]:
    """OT target search -> up to k TargetHit candidates (symbol, ensembl, full name, biotype)."""
    d = ot_query(_SEARCH_GQL, {"q": query, "k": k})
    hits = ((d or {}).get("search") or {}).get("hits") or []
    out = []
    for h in hits:
        obj = h.get("object") or {}
        ens = h.get("id")
        out.append(TargetHit(obj.get("approvedSymbol"), ens, obj.get("approvedName"),
                             obj.get("biotype"), OT_PAGE.format(ens) if ens else None))
    return out
