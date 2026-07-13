from bioskeptic.data import opentargets as ot
from bioskeptic.refute.core import ClaimTriple, Finding

NAME = "direction_of_effect"


# Fire if the drug pushes the target opposite to the direction human genetics say is therapeutic.
def check(claim: ClaimTriple) -> Finding | None:
    if not claim.direction:
        return None                          # not applicable — no claimed direction to judge

    dp = ot.genetic_direction(claim.target, claim.disease)
    if dp is None:
        return None                          # missing ids or no directional evidence -> abstain

    # guardrails: abstain on classes where germline genetic direction != therapeutic direction
    if ot.is_oncology(claim.disease) or ot.is_ion_channel(claim.target):
        return None

    symbol = (claim.target.symbol if claim.target else None) or "the target"
    dname = (claim.disease.name if claim.disease else None) or "the disease"

    if claim.direction != dp.value:
        return Finding(NAME, True,
            f"Human genetics indicate that {dp.value}ing {symbol} is therapeutic for {dname} "
            f"({dp.summary}); this drug {claim.direction}s it — the wrong direction.",
            [dp.url, *dp.citations])
    return Finding(NAME, False,
        f"The drug's direction ({claim.direction}s {symbol}) matches the genetically-therapeutic "
        f"direction ({dp.summary}).",
        [dp.url])


# Does Open Targets hold directional genetic evidence for this pair? (datum existence, for the precheck.)
def available(claim: ClaimTriple) -> bool:
    return ot.genetic_direction(claim.target, claim.disease) is not None
