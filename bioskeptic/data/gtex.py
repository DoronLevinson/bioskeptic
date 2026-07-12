from bioskeptic.data.core import Datapoint
from bioskeptic.resolver.fetch import get_json
from bioskeptic.resolver.target import Target


# The GTEx gencode id for a target — use the passport's if present, else resolve by ensembl/symbol.
def _gencode(target: Target) -> str | None:
    if target.gencode:
        return target.gencode
    q = target.ensembl or target.symbol
    if not q:
        return None
    data = (get_json(f"https://gtexportal.org/api/v2/reference/gene?geneId={q}") or {}).get("data") or []
    return data[0]["gencodeId"] if data else None


# The target's median RNA expression (TPM) across all 54 GTEx tissues — one datapoint (value = {tissue: TPM}).
def tissue_expression(target: Target) -> Datapoint | None:
    if not target:
        return None
    gencode = _gencode(target)
    if not gencode:
        return None
    url = f"https://gtexportal.org/api/v2/expression/medianGeneExpression?gencodeId={gencode}&datasetId=gtex_v8"
    rows = (get_json(url) or {}).get("data") or []
    if not rows:
        return None
    expr = {r["tissueSiteDetailId"]: r["median"] for r in rows}
    top = sorted(expr.items(), key=lambda kv: -kv[1])[:3]
    return Datapoint(
        value=expr,
        label="GTEx median tissue expression (TPM)",
        summary="highest in " + ", ".join(f"{t} ({v:.0f})" for t, v in top),
        source="GTEx v8",
        url=f"https://gtexportal.org/home/gene/{target.symbol or gencode}",
    )
