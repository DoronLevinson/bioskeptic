from bioskeptic.data import anatomy, gtex, hpa
from bioskeptic.refute.core import ClaimTriple, Finding

NAME = "not_expressed_in_tissue"
_TPM_FLOOR = 1.0                             # median TPM < 1 = "not expressed" (standard convention)


# Fire only if the target is absent from the disease's tissue in BULK *and* its driver cell type —
# the single-cell rescue rules out rare-but-functional cells that bulk RNA dilutes to near-zero.
def check(claim: ClaimTriple) -> Finding | None:
    expr = gtex.tissue_expression(claim.target)
    if expr is None:
        return None                          # no expression data -> abstain

    tissues = anatomy.affected_tissues(claim.disease, list(expr.value.keys()))
    if not tissues:
        return None                          # systemic disease / no mappable tissue -> abstain

    levels = {t: expr.value.get(t, 0.0) for t in tissues}
    symbol = (claim.target.symbol if claim.target else None) or "the target"
    dname = (claim.disease.name if claim.disease else None) or "the disease"

    if not all(v < _TPM_FLOOR for v in levels.values()):
        present = ", ".join(f"{t} {v:.1f} TPM" for t, v in levels.items())
        return Finding(NAME, False,
            f"{symbol} is expressed in the tissue affected by {dname} ({present}).",
            [expr.url])

    # bulk-absent -> single-cell rescue: is it present in the cell type that drives the disease?
    sc = hpa.single_cell_expression(claim.target)
    if sc is not None and anatomy.expressed_in_driver_cell(claim.disease, sc.value) is True:
        return Finding(NAME, False,
            f"{symbol} reads low in bulk {'/'.join(tissues)} but IS present in the cell type that drives "
            f"{dname} (single-cell: {sc.summary}), so it is reachable there after all.",
            [expr.url, sc.url])

    # absent in bulk AND driver cell (or single-cell has no data) -> a real, if suggestive, flag
    detail = ", ".join(f"{t} {v:.2f} TPM" for t, v in levels.items())
    sources = [expr.url] + ([sc.url] if sc else [])
    return Finding(NAME, True,
        f"{symbol} is not expressed in the tissue affected by {dname} ({detail}; below 1 TPM), nor in "
        f"its driver cell type — its RNA is {expr.summary}. A real absence, but weigh it against the "
        f"drug's actual site of action (a drug can act on a different organ, e.g. a diuretic on the kidney).",
        sources)


# Does GTEx hold tissue expression for this target? (the disease->tissue step is checked at runtime.)
def available(claim: ClaimTriple) -> bool:
    return gtex.tissue_expression(claim.target) is not None
