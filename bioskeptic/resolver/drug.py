import re
import urllib.parse
from dataclasses import dataclass, field

from bioskeptic.resolver.fetch import get_json, post_json

CHEMBL_MOLECULE_URL = "https://www.ebi.ac.uk/chembl/api/data/molecule/{}.json"
CHEMBL_SEARCH_URL = "https://www.ebi.ac.uk/chembl/api/data/molecule/search?q={}&format=json&limit={}"
UNICHEM_URL = "https://www.ebi.ac.uk/unichem/api/v1/compounds"
CHEMBL_PAGE = "https://www.ebi.ac.uk/chembl/explore/compound/{}"

# UniChem source shortName -> our passport field (structure-based cross-refs; small molecules only)
_UNICHEM_FIELDS = {"drugbank": "drugbank_id", "pubchem": "pubchem_cid", "fdasrs": "unii", "gtopdb": "gtopdb"}


# The drug's "ID passport" — identifiers only; payload (mechanism, potency, labels) lives in the data layer.
@dataclass
class Drug:
    name: str | None = None
    chembl_id: str | None = None         # ChEMBL primary key — the hub every other lookup hangs off
    modality: str | None = None          # discriminator: "Small molecule" / "Antibody" / "Protein" / …
    inchikey: str | None = None          # structure key (small molecules; empty for biologics)
    atc: list[str] = field(default_factory=list)          # WHO therapeutic-class codes
    drugbank_id: str | None = None       # DrugBank / DRKG key
    pubchem_cid: str | None = None       # PubChem compound id
    unii: str | None = None              # FDA substance id (UniChem 'fdasrs')
    gtopdb: str | None = None            # Guide to Pharmacology ligand id
    synonyms: list[str] = field(default_factory=list)     # alias names (INN / BAN / other)
    trade_names: list[str] = field(default_factory=list)  # brand names
    url: str | None = None               # ChEMBL compound page, for a human to verify

    @property
    def resolved(self) -> bool:
        return self.chembl_id is not None


@dataclass
class DrugHit:
    name: str | None
    chembl_id: str | None
    modality: str | None     # shown so a human can tell an antibody from a small molecule
    url: str | None


# Resolve a drug in any shape (name, ChEMBL id, DrugBank id, or DRKG 'Compound::…') to a full ID passport.
def resolve_drug(query: str) -> Drug:
    chembl_id = _reach_chembl(_strip_prefix(query))
    if chembl_id is None:
        return Drug()
    chembl_id, mol = _canonical_molecule(chembl_id)
    if not mol:
        return Drug()
    inchikey = (mol.get("molecule_structures") or {}).get("standard_inchi_key")
    synonyms, trade_names = _split_synonyms(mol.get("molecule_synonyms") or [], mol.get("pref_name"))
    xref = _unichem_xrefs(inchikey) if inchikey else {}
    return Drug(
        name=mol.get("pref_name"),
        chembl_id=chembl_id,
        modality=mol.get("molecule_type"),
        inchikey=inchikey,
        atc=mol.get("atc_classifications") or [],
        drugbank_id=xref.get("drugbank_id"),
        pubchem_cid=xref.get("pubchem_cid"),
        unii=xref.get("unii"),
        gtopdb=xref.get("gtopdb"),
        synonyms=synonyms,
        trade_names=trade_names,
        url=CHEMBL_PAGE.format(chembl_id),
    )


# Top-k candidate drugs for chat disambiguation ("which did you mean?").
def suggest_drugs(query: str, k: int = 5) -> list[DrugHit]:
    d = get_json(CHEMBL_SEARCH_URL.format(urllib.parse.quote(query), k))
    out = []
    for m in ((d or {}).get("molecules") or [])[:k]:
        cid = m.get("molecule_chembl_id")
        out.append(DrugHit(m.get("pref_name") or query, cid, m.get("molecule_type"),
                           CHEMBL_PAGE.format(cid) if cid else None))
    return out


# 'Compound::DB00001' -> 'DB00001'; a bare name/id passes through unchanged.
def _strip_prefix(query: str) -> str:
    q = (query or "").strip()
    return q.split("::", 1)[1] if "::" in q else q


# Route by input shape to the canonical ChEMBL id.
def _reach_chembl(raw: str) -> str | None:
    if raw.upper().startswith("CHEMBL"):
        return raw.upper()
    if re.fullmatch(r"DB\d+", raw):                 # DrugBank id -> ChEMBL via UniChem
        return _chembl_from_drugbank(raw)
    return _chembl_from_name(raw)                    # a drug name


# Fetch the ChEMBL molecule, hopping to the parent (active ingredient) if this id is a salt form.
def _canonical_molecule(chembl_id: str) -> tuple[str, dict | None]:
    mol = get_json(CHEMBL_MOLECULE_URL.format(urllib.parse.quote(chembl_id)))
    if not mol:
        return chembl_id, None
    parent = (mol.get("molecule_hierarchy") or {}).get("parent_chembl_id")
    if parent and parent != chembl_id:
        parent_mol = get_json(CHEMBL_MOLECULE_URL.format(urllib.parse.quote(parent)))
        if parent_mol:
            return parent, parent_mol
    return chembl_id, mol


# ChEMBL molecule search -> the top hit's chembl id.
def _chembl_from_name(name: str) -> str | None:
    d = get_json(CHEMBL_SEARCH_URL.format(urllib.parse.quote(name), 1))
    mols = (d or {}).get("molecules") or []
    return mols[0].get("molecule_chembl_id") if mols else None


# UniChem reverse map: a DrugBank id -> its ChEMBL id (sourceID 2 = DrugBank).
def _chembl_from_drugbank(db_id: str) -> str | None:
    d = post_json(UNICHEM_URL, {"type": "sourceID", "sourceID": 2, "compound": db_id})
    for c in (d or {}).get("compounds", []):
        for s in c.get("sources", []):
            if s.get("shortName") == "chembl":
                return s.get("compoundId")
    return None


# UniChem forward map: an InChIKey -> the cross-ref ids we keep (drugbank / pubchem / unii / gtopdb).
def _unichem_xrefs(inchikey: str) -> dict:
    d = post_json(UNICHEM_URL, {"type": "inchikey", "compound": inchikey})
    comps = (d or {}).get("compounds") or []
    out: dict = {}
    if comps:
        for s in comps[0].get("sources", []):
            dest = _UNICHEM_FIELDS.get(s.get("shortName"))
            if dest and dest not in out:            # keep the first id per source
                out[dest] = s.get("compoundId")
    return out


# Split ChEMBL molecule_synonyms into (alias names, brand names), deduped and minus the pref name.
def _split_synonyms(raw_syn: list[dict], pref_name: str | None) -> tuple[list[str], list[str]]:
    pref = (pref_name or "").upper()
    synonyms, trade = [], []
    seen_s, seen_t = set(), set()
    for s in raw_syn:
        label = s.get("molecule_synonym")
        if not label:
            continue
        key = label.upper()
        if s.get("syn_type") == "TRADE_NAME":
            if key not in seen_t:
                seen_t.add(key)
                trade.append(label)
        elif key != pref and key not in seen_s:
            seen_s.add(key)
            synonyms.append(label)
    return synonyms, trade
