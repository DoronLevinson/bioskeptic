import urllib.parse as up
from dataclasses import dataclass

from bioskeptic.resolver.fetch import get_json

_EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


@dataclass
class Paper:
    pmid: str
    title: str
    year: str
    journal: str
    first_author: str
    url: str


# Search PubMed for `term` (NCBI E-utils: esearch for ids + count, esummary for the metadata).
# `term` is a raw PubMed query the caller builds from resolved ids for precision, e.g.
# "SLC12A1[tiab] AND ototoxicity" — the [tiab] tag restricts a term to title/abstract, and AND/OR
# combine terms. Returns (total match count, the top k papers). The count alone is a signal:
# thousands = well-studied, a handful = obscure.
def search(term: str, k: int = 6) -> tuple[int, list[Paper]]:
    if not term:
        return 0, []
    q = up.quote(term)
    es = get_json(f"{_EUTILS}/esearch.fcgi?db=pubmed&term={q}&retmode=json&retmax={k}")
    sr = (es or {}).get("esearchresult", {})
    ids = sr.get("idlist") or []
    count = int(sr.get("count") or 0)
    if not ids:
        return count, []
    su = get_json(f"{_EUTILS}/esummary.fcgi?db=pubmed&id={','.join(ids)}&retmode=json")
    res = (su or {}).get("result", {})
    papers = []
    for uid in res.get("uids", []):
        r = res.get(uid) or {}
        authors = r.get("authors") or []
        papers.append(Paper(
            pmid=uid,
            title=(r.get("title") or "").rstrip("."),
            year=(r.get("pubdate") or "")[:4],
            journal=r.get("fulljournalname") or r.get("source") or "",
            first_author=(authors[0]["name"] if authors else ""),
            url=f"https://pubmed.ncbi.nlm.nih.gov/{uid}/",
        ))
    return count, papers
