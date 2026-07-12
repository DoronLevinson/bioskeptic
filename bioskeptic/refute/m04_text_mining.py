from bioskeptic.data import opentargets as ot
from bioskeptic.refute.core import ClaimTriple, Finding

NAME = "text_mining_only"


# Fire if the target-disease association rests only on literature co-mention, with no other evidence.
# Any non-literature datatype (genetic, somatic, clinical/known-drug, pathway, expression, animal) counts
# as real biology -> clean. Whitelisting by "only literature" avoids missing a datatype name.
def check(claim: ClaimTriple) -> Finding | None:
    dp = ot.association_evidence(claim.target, claim.disease)
    if dp is None:
        return None                          # no association at all -> not this mechanism's case

    datatypes = dp.value
    symbol = (claim.target.symbol if claim.target else None) or "the target"
    dname = (claim.disease.name if claim.disease else None) or "the disease"

    if set(datatypes) == {"literature"}:
        return Finding(NAME, True,
            f"The {symbol}–{dname} association rests only on literature co-mention (its sole evidence "
            f"type is text-mining; no genetic, clinical, pathway, expression, or animal-model evidence) "
            f"— a knowledge-graph edge can exist purely because papers mention both.",
            [dp.url])
    return Finding(NAME, False,
        f"The {symbol}–{dname} association is backed by direct evidence ({dp.summary}).",
        [dp.url])


# Does Open Targets hold an association (of any kind) for this pair? (datum existence, for the precheck.)
def available(claim: ClaimTriple) -> bool:
    return ot.association_evidence(claim.target, claim.disease) is not None
