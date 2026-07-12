import re
from dataclasses import dataclass, field

from bioskeptic.resolver.fetch import get_json, ot_query

DISEASE_PAGE = "https://platform.opentargets.org/disease/{}"
EUTILS_ESUMMARY = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=mesh&retmode=json&id={}"


# The disease's "ID passport" — identifiers only; payload (associations, evidence) lives in the data layer.
@dataclass
class Disease:
    name: str | None = None
    efo: str | None = None            # EFO/MONDO id — the canonical key (the hub every disease lookup uses)
    mesh: str | None = None           # MeSH id — free on the DRKG path (input is MeSH), else from OT xrefs if present, else None
    omim: str | None = None           # OMIM id (genetic diseases; None when legitimately absent)
    umls: str | None = None           # UMLS CUI — the universal medical-concept id
    synonyms: list[str] = field(default_factory=list)          # alias names, for literature/trials search
    therapeutic_areas: list[str] = field(default_factory=list) # broad classes ("cancer", "cardiovascular")
    url: str | None = None            # Open Targets disease page, for a human to verify

    @property
    def resolved(self) -> bool:
        return self.efo is not None


@dataclass
class DiseaseHit:
    name: str | None
    description: str | None   # one-line gloss so a human can tell ambiguous names apart
    efo: str | None
    url: str | None


# Resolve a disease in any shape (name, EFO/MONDO id, or DRKG 'Disease::MESH:…') to a full ID passport.
def resolve_disease(query: str) -> Disease:
    efo, mesh = _resolve_identity(_strip_prefix(query))
    if efo is None:
        return Disease(mesh=mesh)             # DRKG path may keep a MeSH id even if efo lookup failed
    core = _ot_disease(efo)
    if core is None:
        return Disease(efo=efo, mesh=mesh, url=DISEASE_PAGE.format(efo))
    return Disease(
        name=core["name"],
        efo=efo,
        mesh=mesh or core["mesh"],
        omim=core["omim"],
        umls=core["umls"],
        synonyms=core["synonyms"],
        therapeutic_areas=core["therapeutic_areas"],
        url=DISEASE_PAGE.format(efo),
    )


# Top-k candidate diseases for chat disambiguation ("which did you mean?"), EFO/MONDO ranked above HP/Orphanet.
def suggest_diseases(query: str, k: int = 5) -> list[DiseaseHit]:
    return _rank(_search_diseases(query, k))


# 'Disease::MESH:D013921' -> 'MESH:D013921'; a bare name/id passes through unchanged.
def _strip_prefix(query: str) -> str:
    q = (query or "").strip()
    return q.split("::", 1)[1] if "::" in q else q


# Route by input shape to (canonical efo, mesh-if-known). Name + MeSH paths reach efo via OT search.
def _resolve_identity(raw: str) -> tuple[str | None, str | None]:
    if re.match(r"(EFO|MONDO|HP|Orphanet|DOID)[_:]", raw, re.I):   # already an ontology id — trust it
        return raw.replace(":", "_"), None
    if raw.upper().startswith("MESH") or re.fullmatch(r"D\d+", raw, re.I):   # MeSH id (DRKG disease key)
        mesh = raw.split(":")[-1].upper()
        name = _mesh_to_name(mesh)
        return (_efo_from_name(name) if name else None), mesh
    return _efo_from_name(raw), None                               # a disease name


# OT search a name -> its best EFO/MONDO id (prefer a real disease term over an HP phenotype).
def _efo_from_name(name: str) -> str | None:
    ranked = _rank(_search_diseases(name, 10))
    return ranked[0].efo if ranked else None


# One OT disease(efoId) call -> the passport payload (name, synonyms, therapeutic areas, and slotted xrefs).
def _ot_disease(efo: str) -> dict | None:
    d = ot_query(
        "query($e:String!){ disease(efoId:$e){ name dbXRefs"
        " synonyms{ relation terms } therapeuticAreas{ id name } } }",
        {"e": efo},
    )
    dz = (d or {}).get("disease") or {}
    if not dz.get("name"):
        return None
    xr = dz.get("dbXRefs") or []
    synonyms, seen = [], set()
    for s in dz.get("synonyms") or []:
        if s.get("relation") == "hasExactSynonym":
            for t in s.get("terms") or []:
                if t and t not in seen:
                    seen.add(t)
                    synonyms.append(t)
    return {
        "name": dz.get("name"),
        "synonyms": synonyms,
        "therapeutic_areas": [t["name"] for t in dz.get("therapeuticAreas") or [] if t.get("name")],
        "umls": _xref(xr, "UMLS"),
        "omim": _xref(xr, "OMIM", "OMIMPS"),
        "mesh": _xref(xr, "MESH", "MSH"),
    }


# Pull the first cross-ref value matching any of the given prefixes from an OT dbXRefs list.
def _xref(dbxrefs: list[str], *prefixes: str) -> str | None:
    wanted = {p.upper() for p in prefixes}
    for x in dbxrefs:
        pre, _, val = x.partition(":")
        if pre.upper() in wanted:
            return val
    return None


# NCBI eutils: a MeSH descriptor id (e.g. 'D013921') -> its preferred term name, for the OT search step.
# A descriptor's Entrez UID is deterministically '68' + its digits (D003924 -> 68003924), so no fuzzy search.
def _mesh_to_name(mesh_id: str) -> str | None:
    mesh_id = mesh_id.upper()
    if not (mesh_id.startswith("D") and mesh_id[1:].isdigit()):
        return None
    uid = "68" + mesh_id[1:]
    su = get_json(EUTILS_ESUMMARY.format(uid))
    rec = ((su or {}).get("result") or {}).get(uid) or {}
    terms = rec.get("ds_meshterms")
    return terms[0] if isinstance(terms, list) and terms else rec.get("title")


# OT disease search -> DiseaseHit candidates (name, description, efo, url).
def _search_diseases(query: str, k: int) -> list[DiseaseHit]:
    # Drop apostrophes ("Alzheimer's" -> "Alzheimers"), turn other punctuation into spaces, collapse whitespace —
    # OT search returns junk otherwise (apostrophes -> measurement terms; comma-inverted MeSH names -> zero hits).
    clean = " ".join(re.sub(r"[^0-9A-Za-z\s-]", " ", query.replace("'", "").replace("’", "")).split())
    d = ot_query(
        "query($q:String!,$k:Int!){ search(queryString:$q, entityNames:[\"disease\"], page:{index:0,size:$k}){"
        " hits{ id object{ ... on Disease{ name description } } } } }",
        {"q": clean, "k": k},
    )
    hits = ((d or {}).get("search") or {}).get("hits") or []
    out = []
    for h in hits:
        o = h.get("object") or {}
        eid = h.get("id")
        out.append(DiseaseHit(o.get("name"), o.get("description"), eid, DISEASE_PAGE.format(eid) if eid else None))
    return out


# Rank curated diseases first: sink measurement/biomarker concepts, then MONDO > EFO > HP/Orphanet.
# (MONDO ids are curated diseases; the polluting quantitative-trait terms that hijack lay queries are EFO.)
def _rank(hits: list[DiseaseHit]) -> list[DiseaseHit]:
    def tier(eid: str) -> int:
        if eid.startswith("MONDO_"):
            return 0
        if eid.startswith("EFO_"):
            return 1
        return 2  # HP phenotypes, Orphanet, …

    def key(h: DiseaseHit):
        name = (h.name or "").lower()
        is_measurement = any(w in name for w in ("measurement", "biomarker"))  # not a disease — push last
        return (is_measurement, tier(h.efo or ""))

    return sorted(hits, key=key)
