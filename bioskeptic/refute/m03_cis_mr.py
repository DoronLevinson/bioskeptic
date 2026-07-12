from bioskeptic.data import epigraphdb as ee
from bioskeptic.refute.core import ClaimTriple, Finding

NAME = "cis_mr_null"
_SIG_P = 0.05             # p < this => a causal signal exists => the target may work (stay clean)
_TAU = 0.10              # a well-powered null keeps the WHOLE 95% CI within +/- this (|log-OR| per SD)


# Fire if a well-powered cis-MR estimate of the target on the disease is a precise null — genetically
# modulating the target does not move the disease, so the association is not causal. Abstain on a wide-CI
# ("no power", not "no effect") null; stay clean when a causal effect is present.
def check(claim: ClaimTriple) -> Finding | None:
    dp = ee.cis_mr_estimate(claim.target, claim.disease)
    if dp is None:
        return None                          # protein/outcome not in the atlas -> abstain

    v = dp.value
    symbol = (claim.target.symbol if claim.target else None) or "the target"
    dname = (claim.disease.name if claim.disease else None) or "the disease"

    if v["any_significant"]:
        return Finding(NAME, False,
            f"cis-MR of {symbol} on {dname} shows a causal effect ({dp.summary}) — association supported.",
            [dp.url])

    well_powered_null = v["pvalue"] >= _SIG_P and abs(v["beta"]) < _TAU and v["ci_hi"] < _TAU
    if not well_powered_null:
        return None                          # under-powered null (wide CI) -> abstain, don't over-refute

    return Finding(NAME, True,
        f"A well-powered cis-MR of {symbol} on '{v['matched_outcome']}' is a precise null ({dp.summary}); "
        f"the 95% CI tightly spans zero and excludes even a modest per-SD effect, so genetically "
        f"modulating {symbol} does not change {dname} — the association is not causal.",
        [dp.url])


# Is the target in the cis-pQTL MR atlas with a matched outcome for this disease? (for the precheck.)
def available(claim: ClaimTriple) -> bool:
    return ee.cis_mr_estimate(claim.target, claim.disease) is not None
