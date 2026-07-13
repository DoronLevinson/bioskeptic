from bioskeptic.data import anatomy
from bioskeptic.data import opentargets as ot
from bioskeptic.refute.core import ClaimTriple, Finding

NAME = "mouse_ko_normal"


# Fire if the mouse knockout of the target produces no phenotype relevant to the disease — removing the
# target in a whole animal doesn't produce the expected effect, so the target may not be required.
def check(claim: ClaimTriple) -> Finding | None:
    dp = ot.mouse_ko_phenotypes(claim.target)
    if dp is None:
        return None                          # no mouse-knockout data -> abstain

    # non-viable knockout with no adult phenotyping (a lethality label AND very few total phenotypes) ->
    # no adult was scored, so "no relevant phenotype" is absence-of-evidence, not evidence the gene is
    # dispensable. Abstain. (Genes with a lethality label BUT many adult phenotypes are viable alleles
    # with real data — keep them; only the sparse, lethality-dominated ones are uninformative.)
    if len(dp.value) <= 6 and any("lethality" in p.lower() for p in dp.value):
        return None

    relevant = anatomy.phenotype_relevant_to_disease(claim.disease, dp.value)
    if relevant is None:
        return None                          # couldn't judge relevance -> abstain

    symbol = (claim.target.symbol if claim.target else None) or "the target"
    dname = (claim.disease.name if claim.disease else None) or "the disease"

    if relevant:
        return Finding(NAME, False,
            f"The mouse knockout of {symbol} produces phenotype(s) relevant to {dname} ({dp.summary}).",
            [dp.url])
    return Finding(NAME, True,
        f"The mouse knockout of {symbol} produces no phenotype relevant to {dname} — its "
        f"{len(dp.value)} knockout phenotype(s) are in unrelated systems (e.g. {', '.join(dp.value[:4])}) "
        f"— so removing the target does not produce the expected disease effect, suggesting it is not "
        f"required for the disease.",
        [dp.url])


# Does Open Targets hold mouse-knockout phenotypes for this target? (datum existence, for the precheck.)
def available(claim: ClaimTriple) -> bool:
    return ot.mouse_ko_phenotypes(claim.target) is not None
