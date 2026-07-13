from bioskeptic.data import anatomy, hpa
from bioskeptic.refute.core import ClaimTriple, Finding

NAME = "absent_from_driver_cell"


# Fire if the target is absent from the specific cell type that drives the disease — even where the
# disease acts, a bulk-tissue signal can be carried by *other* cells, so the driving cells lack the target.
def check(claim: ClaimTriple) -> Finding | None:
    sc = hpa.single_cell_expression(claim.target)
    if sc is None:
        return None                          # no single-cell data -> abstain

    present = anatomy.expressed_in_driver_cell(claim.disease, sc.value)
    if present is None:
        return None                          # couldn't judge the driver cell -> abstain

    symbol = (claim.target.symbol if claim.target else None) or "the target"
    dname = (claim.disease.name if claim.disease else None) or "the disease"

    if present:
        return Finding(NAME, False,
            f"{symbol} is expressed in the cell type that drives {dname} (single-cell: {sc.summary}).",
            [sc.url])
    return Finding(NAME, True,
        f"{symbol} is not expressed in the cell type that drives {dname} — its single-cell expression "
        f"is confined to unrelated cell types ({sc.summary}) — so even where the disease acts, the "
        f"driving cells lack the target for the drug to engage.",
        [sc.url])


# Does the Human Protein Atlas hold single-cell expression for this target? (datum existence, precheck.)
def available(claim: ClaimTriple) -> bool:
    return hpa.single_cell_expression(claim.target) is not None
