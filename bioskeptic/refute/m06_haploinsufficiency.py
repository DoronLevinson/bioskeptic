from bioskeptic.data import clingen
from bioskeptic.refute.core import ClaimTriple, Finding

NAME = "haploinsufficient_inhibited"


# Fire if the drug lowers a curated haploinsufficient target (ClinGen HI=3) — losing a single copy
# already causes disease, so an inhibitor/antagonist/degrader pushes dosage in the harmful direction.
def check(claim: ClaimTriple) -> Finding | None:
    if claim.direction != "inhibit":
        return None                          # only lowering a dosage-sensitive gene is harmful

    dp = clingen.haploinsufficiency(claim.target)
    if dp is None:
        return None                          # gene not dosage-curated -> abstain

    symbol = (claim.target.symbol if claim.target else None) or "the target"

    if not dp.value["haploinsufficient"]:
        return Finding(NAME, False,
            f"{symbol} is not haploinsufficient (ClinGen {dp.summary}), so lowering it is not "
            f"dosage-harmful.",
            [dp.url])
    return Finding(NAME, True,
        f"{symbol} is haploinsufficient (ClinGen {dp.summary}) — losing a single copy already causes "
        f"disease, so a drug that inhibits or lowers it pushes dosage in the harmful direction rather "
        f"than the therapeutic one.",
        [dp.url])


# Applies only to lowering drugs on a dosage-curated target. (datum existence, for the precheck.)
def available(claim: ClaimTriple) -> bool:
    return claim.direction == "inhibit" and clingen.haploinsufficiency(claim.target) is not None
