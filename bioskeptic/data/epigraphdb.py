import urllib.parse

from bioskeptic.data.core import Datapoint
from bioskeptic.resolver.disease import Disease
from bioskeptic.resolver.fetch import get_json
from bioskeptic.resolver.target import Target

_EPIGRAPHDB = "https://api.epigraphdb.org/pqtl/"
_MATCH_MIN = 0.6                            # token-Jaccard floor to accept a disease<->atlas-outcome match

# generic words dropped before token-matching a disease name against an atlas outcome label
_STOP = {"disease", "disorder", "syndrome", "the", "and", "of", "in", "with", "a", "an",
         "chronic", "acute", "primary", "secondary", "type", "self", "reported"}

# common disease-name variants -> the atlas's canonical phrasing (kept tiny and general)
_SYNONYM = {"coronary artery disease": "coronary heart disease", "cad": "coronary heart disease",
            "chd": "coronary heart disease", "heart attack": "myocardial infarction",
            "mi": "myocardial infarction", "t2d": "type 2 diabetes", "t2dm": "type 2 diabetes",
            "ra": "rheumatoid arthritis", "ibd": "inflammatory bowel disease"}


def _norm(s):
    return " ".join((s or "").lower().replace("'", "").replace(",", " ").replace("-", " ").split())


def _tokens(s):
    return {w for w in _norm(s).split() if w not in _STOP and len(w) >= 3}


# Jaccard on non-generic tokens; 1.0 for a normalized exact match. Higher = better disease match.
def _match_score(query, label):
    q, l = _SYNONYM.get(_norm(query), _norm(query)), _norm(label)
    if q == l:
        return 1.0
    tq, tl = _tokens(q), _tokens(l)
    if not (tq and tl and (tq & tl)):
        return 0.0
    return len(tq & tl) / len(tq | tl)


# The cis-pQTL Mendelian-randomization causal estimate of the target on the disease — one datapoint.
# cis instruments at the target's own locus proxy lifelong modulation, so this is a CAUSAL (not merely
# associational) estimate. value carries beta/se/p + whether any cis row for the outcome is significant.
def cis_mr_estimate(target: Target, disease: Disease) -> Datapoint | None:
    symbol = target.symbol if target else None
    name = disease.name if disease else None
    if not (symbol and name):
        return None
    url = _EPIGRAPHDB + "?" + urllib.parse.urlencode(
        {"query": symbol, "rtype": "simple", "searchflag": "proteins", "pvalue": "1"})
    rows = (get_json(url) or {}).get("results")
    if not rows:
        return None
    cis = [r for r in rows if r.get("trans_cis") == "cis"]
    scored = [(s, r) for r in cis if (s := _match_score(name, r.get("outID") or "")) >= _MATCH_MIN]
    if not scored:
        return None                        # protein in atlas but disease outcome not matched -> abstain
    top_label = max(scored, key=lambda z: z[0])[1].get("outID")
    parsed = []
    for _, r in scored:
        if (r.get("outID") or "") != top_label:
            continue
        try:
            parsed.append({"beta": float(r["beta"]), "se": float(r["se"]),
                           "pvalue": float(r["pvalue"]), "nsnp": int(r.get("nsnp") or 0)})
        except (TypeError, ValueError, KeyError):
            pass
    if not parsed:
        return None
    best = min(parsed, key=lambda p: p["se"])          # most precise cis estimate for this outcome
    ci = 1.96 * best["se"]
    return Datapoint(
        value={"beta": best["beta"], "se": best["se"], "pvalue": best["pvalue"], "nsnp": best["nsnp"],
               "ci_hi": abs(best["beta"]) + ci, "matched_outcome": top_label,
               "any_significant": any(p["pvalue"] < 0.05 for p in parsed)},
        label="cis-pQTL Mendelian-randomization causal estimate",
        summary=(f"beta={best['beta']:+.3f}/SD (95% CI ±{ci:.3f}, p={best['pvalue']:.2f}, "
                 f"{best['nsnp']} cis SNP) on '{top_label}'"),
        source="EpiGraphDB cis-pQTL MR (Zheng et al. 2020)",
        url=f"{_EPIGRAPHDB}?query={urllib.parse.quote(symbol)}&rtype=simple&searchflag=proteins&pvalue=1",
    )
