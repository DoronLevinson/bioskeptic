import urllib.request

from bioskeptic.data.core import Datapoint
from bioskeptic.resolver.target import Target

_URL = "https://ftp.clinicalgenome.org/ClinGen_gene_curation_list_GRCh38.tsv"
_HI: dict = {}                             # gene symbol -> haploinsufficiency score (int); loaded once
_LOADED = False


# Load the ClinGen dosage-sensitivity table once (gene symbol -> HI score). Columns: 0=symbol, 4=HI score.
def _load():
    global _LOADED
    if _LOADED:
        return
    _LOADED = True
    try:
        req = urllib.request.Request(_URL, headers={"User-Agent": "bioskeptic/0.1"})
        text = urllib.request.urlopen(req, timeout=60).read().decode()
    except Exception:
        return
    for line in text.splitlines():
        if line.startswith("#") or not line.strip():
            continue
        cols = line.split("\t")
        if len(cols) < 5:
            continue
        try:
            _HI[cols[0].strip()] = int(cols[4])
        except ValueError:
            continue


# ClinGen's curated haploinsufficiency call for the target (HI score) — one datapoint. HI=3 = sufficient
# evidence that losing a single copy causes disease (dosage-sensitive). None if the gene isn't curated.
def haploinsufficiency(target: Target) -> Datapoint | None:
    sym = target.symbol if target else None
    if not sym:
        return None
    _load()
    if sym not in _HI:
        return None                        # gene not in the dosage-curation list -> abstain
    hi = _HI[sym]
    return Datapoint(
        value={"hi_score": hi, "haploinsufficient": hi == 3},
        label="ClinGen haploinsufficiency (dosage) score",
        summary=(f"haploinsufficiency score {hi}"
                 + (" — sufficient evidence for haploinsufficiency" if hi == 3 else "")),
        source="ClinGen dosage sensitivity",
        url=f"https://search.clinicalgenome.org/kb/genes?search={sym}")
