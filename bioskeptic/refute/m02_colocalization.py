from bioskeptic.data import opentargets as ot
from bioskeptic.refute.core import ClaimTriple, Finding

NAME = "not_causal_gene"
_FRAC_FLOOR = 0.5          # target must be the top causal gene at >= half its loci to be the effector
_COMPETITOR_FLOOR = 0.5    # the outranking gene must be a confident causal call (else the locus is weak)


# Fire if a confident neighbouring gene consistently outranks the target as the causal gene (L2G) at the
# disease's GWAS loci — the target is the top prediction at < half its loci, so it may be a passenger.
def check(claim: ClaimTriple) -> Finding | None:
    dp = ot.causal_gene_ranking(claim.target, claim.disease)
    if dp is None:
        return None                          # no GWAS locus for this pair -> abstain

    v = dp.value
    symbol = (claim.target.symbol if claim.target else None) or "the target"
    dname = (claim.disease.name if claim.disease else None) or "the disease"

    competitor_confident = (v["top_competitor_score"] or 0) >= _COMPETITOR_FLOOR
    if v["frac_top"] >= _FRAC_FLOOR or not competitor_confident:
        return Finding(NAME, False,
            f"{symbol} is a plausible causal gene at its GWAS loci for {dname} "
            f"(top at {v['n_top']}/{v['n_loci']}; {dp.summary}).",
            [dp.url])
    return Finding(NAME, True,
        f"At the GWAS loci for {dname}, {symbol} is the top causal-gene prediction at only "
        f"{v['n_top']}/{v['n_loci']} — {v['top_competitor']} (L2G {v['top_competitor_score']:.2f}) "
        f"outranks {symbol} (L2G {v['target_best_score']:.2f}), so {symbol} may be an innocent "
        f"bystander at the locus rather than the effector.",
        [dp.url])


# Does Open Targets hold a GWAS credible-set locus for this pair? (datum existence, for the precheck.)
def available(claim: ClaimTriple) -> bool:
    return ot.causal_gene_ranking(claim.target, claim.disease) is not None
