import gzip
import json
import urllib.request

from bioskeptic.data.core import Datapoint
from bioskeptic.resolver.target import Target

_CACHE: dict = {}                          # per-gene HPA JSON is big; memoize by ensembl


# The Human Protein Atlas per-gene JSON (keyed on Ensembl; gzip-encoded, so decode it explicitly).
def _hpa_json(ensembl: str) -> dict | None:
    if ensembl in _CACHE:
        return _CACHE[ensembl]
    req = urllib.request.Request(f"https://www.proteinatlas.org/{ensembl}.json",
                                 headers={"User-Agent": "bioskeptic/0.1", "Accept-Encoding": "gzip"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            if r.headers.get("Content-Encoding") == "gzip":
                raw = gzip.decompress(raw)
            data = json.loads(raw.decode())
    except Exception:
        return None
    _CACHE[ensembl] = data
    return data


# The target's single-cell RNA expression (nCPM) per cell type — one datapoint (value = {cell type: nCPM}).
def single_cell_expression(target: Target) -> Datapoint | None:
    ens = target.ensembl if target else None
    if not ens:
        return None
    d = _hpa_json(ens)
    if not d:
        return None
    cells: dict = {}
    # merge the specific per-cell-type table with the broader group table (both list where it's expressed)
    for key in ("RNA single cell type specific nCPM", "RNA single cell type group specific nCPM"):
        for cell, val in (d.get(key) or {}).items():
            try:
                cells[cell] = float(val)
            except (TypeError, ValueError):
                pass
    if not cells:
        return None
    top = sorted(cells.items(), key=lambda kv: -kv[1])[:3]
    return Datapoint(
        value=cells,
        label="HPA single-cell expression (nCPM)",
        summary="highest in " + ", ".join(f"{c} ({v:.0f})" for c, v in top),
        source="Human Protein Atlas single-cell",
        url=f"https://www.proteinatlas.org/{ens}/single+cell",
    )
