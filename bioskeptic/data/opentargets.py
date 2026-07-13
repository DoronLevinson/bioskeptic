from collections import Counter
from dataclasses import dataclass

from bioskeptic.data.core import Datapoint
from bioskeptic.resolver.disease import Disease
from bioskeptic.resolver.fetch import ot_query
from bioskeptic.resolver.target import Target

# Genetic-evidence datasources safe for judging a DRUG (never the drug-derived clinical_precedence/chembl).
_DIRECTION_SOURCES = ["gene_burden", "gwas_credible_sets", "genomics_england", "eva",
                      "clingen", "orphanet", "gene2phenotype", "ot_genetics_portal"]

# (directionOnTarget, directionOnTrait) -> the therapeutic direction genetics imply for the target.
_THERAPEUTIC = {("LoF", "protect"): "inhibit", ("GoF", "risk"): "inhibit",
                ("LoF", "risk"): "activate", ("GoF", "protect"): "activate"}

# Plain-language gloss of each genetic combination, for the human summary.
_GLOSS = {("LoF", "protect"): "loss-of-function is protective",
          ("GoF", "risk"): "gain-of-function raises risk",
          ("LoF", "risk"): "loss-of-function raises risk",
          ("GoF", "protect"): "gain-of-function is protective"}


# The therapeutic direction human genetics imply for a (target, disease) pair — one cited datapoint.
def genetic_direction(target: Target, disease: Disease) -> Datapoint | None:
    ensembl = target.ensembl if target else None
    efo = disease.genetic_id if disease else None   # the trait id where genetics lives, else the disease id
    if not (ensembl and efo):
        return None                     # missing an id we need -> not available
    query = """query E($efo:String!,$ens:[String!]!,$ds:[String!]!){
      disease(efoId:$efo){ evidences(ensemblIds:$ens, datasourceIds:$ds, size:500){
        rows{ datasourceId directionOnTarget directionOnTrait literature } } } }"""
    d = ot_query(query, {"efo": efo, "ens": [ensembl], "ds": _DIRECTION_SOURCES})
    dis = (d or {}).get("disease")
    if not dis:
        return None
    combos: Counter = Counter()
    pmids: list[str] = []
    for r in dis["evidences"]["rows"]:
        key = (r.get("directionOnTarget"), r.get("directionOnTrait"))
        if key in _THERAPEUTIC:
            combos[key] += 1
            pmids += r.get("literature") or []
    if not combos:
        return None                     # no directional evidence for this pair
    votes = {"inhibit": 0, "activate": 0}
    for key, n in combos.items():
        votes[_THERAPEUTIC[key]] += n
    if votes["inhibit"] == votes["activate"]:
        return None                     # conflicting evidence -> don't commit
    direction = "inhibit" if votes["inhibit"] > votes["activate"] else "activate"
    dominant = max((k for k in combos if _THERAPEUTIC[k] == direction), key=lambda k: combos[k])
    seen = list(dict.fromkeys(pmids))[:5]
    return Datapoint(
        value=direction,
        label="genetically-therapeutic direction",
        summary=f"{votes[direction]} genetic evidence row(s): {_GLOSS[dominant]}",
        source="Open Targets genetics",
        url=f"https://platform.opentargets.org/evidence/{ensembl}/{efo}",
        citations=[f"https://pubmed.ncbi.nlm.nih.gov/{p}" for p in seen],
    )


# The evidence types behind a target-disease association ({datatype: score}) — one datapoint.
# Open Targets scores an association across datatypes; "literature" is text-mining (Europe PMC co-mention).
def association_evidence(target: Target, disease: Disease) -> Datapoint | None:
    ens = target.ensembl if target else None
    efo = disease.efo if disease else None
    if not (ens and efo):
        return None
    query = """query A($efo:String!,$ens:[String!]){ disease(efoId:$efo){
      associatedTargets(Bs:$ens){ rows{ score datatypeScores{ id score } } } } }"""
    dis = (ot_query(query, {"efo": efo, "ens": [ens]}) or {}).get("disease")
    rows = (dis or {}).get("associatedTargets", {}).get("rows") or []
    if not rows:
        return None                     # no association of any kind -> nothing for #4 to judge
    dts = {x["id"]: x["score"] for x in rows[0]["datatypeScores"]}
    return Datapoint(
        value=dts,
        label="target-disease association evidence types",
        summary="; ".join(f"{k} {v:.2f}" for k, v in sorted(dts.items(), key=lambda kv: -kv[1])),
        source="Open Targets association",
        url=f"https://platform.opentargets.org/evidence/{ens}/{efo}",
    )


# Is the target the top causal-gene (L2G) prediction at its GWAS loci for the disease, or is a
# neighbouring gene consistently ranked higher (target = innocent passenger)? — one datapoint.
def causal_gene_ranking(target: Target, disease: Disease) -> Datapoint | None:
    ens = target.ensembl if target else None
    efo = disease.genetic_id if disease else None   # genetics is indexed on the trait id
    if not (ens and efo):
        return None
    query = """query E($efo:String!,$ens:[String!]!){ disease(efoId:$efo){
      evidences(ensemblIds:$ens, datasourceIds:["gwas_credible_sets"], size:25){
        rows{ credibleSet{ studyLocusId l2GPredictions{ rows{ target{approvedSymbol id} score } } } } } } }"""
    dis = (ot_query(query, {"efo": efo, "ens": [ens]}) or {}).get("disease")
    rows = (dis or {}).get("evidences", {}).get("rows") or []
    loci = {}                            # studyLocusId -> (target_L2G, top_symbol, top_id, top_L2G)
    for row in rows:
        cs = row.get("credibleSet") or {}
        lid = cs.get("studyLocusId")
        preds = (cs.get("l2GPredictions") or {}).get("rows") or []
        if not lid or not preds or lid in loci:
            continue
        top = max(preds, key=lambda g: g["score"])
        tscore = next((g["score"] for g in preds if g["target"]["id"] == ens), 0.0)
        loci[lid] = (tscore, top["target"]["approvedSymbol"], top["target"]["id"], top["score"])
    if not loci:
        return None                      # no GWAS credible-set locus for this pair -> abstain
    sym = target.symbol or "the target"
    n_top = sum(1 for (_, _, top_id, _) in loci.values() if top_id == ens)
    non_top = [(ts, csym, cscore) for (ts, csym, cid, cscore) in loci.values() if cid != ens]
    ts, csym, cscore = max(non_top, key=lambda x: x[2]) if non_top else (None, None, None)
    summary = f"top L2G causal gene at {n_top}/{len(loci)} of its GWAS loci"
    if csym:
        summary += f"; strongest competitor {csym} (L2G {cscore:.2f}) vs {sym} ({ts:.2f})"
    return Datapoint(
        value={"frac_top": n_top / len(loci), "n_loci": len(loci), "n_top": n_top,
               "top_competitor": csym, "top_competitor_score": cscore, "target_best_score": ts},
        label="causal-gene (L2G) ranking at GWAS loci",
        summary=summary,
        source="Open Targets Genetics L2G",
        url=f"https://platform.opentargets.org/evidence/{ens}/{efo}")


# The target's mouse-knockout phenotypes (IMPC, via Open Targets) — one datapoint (value = label list).
def mouse_ko_phenotypes(target: Target) -> Datapoint | None:
    ens = target.ensembl if target else None
    if not ens:
        return None
    query = """query T($id:String!){ target(ensemblId:$id){ mousePhenotypes{ modelPhenotypeLabel } } }"""
    tgt = (ot_query(query, {"id": ens}) or {}).get("target")
    if not tgt:
        return None
    phenos = list(dict.fromkeys(p["modelPhenotypeLabel"] for p in (tgt.get("mousePhenotypes") or [])
                                if p.get("modelPhenotypeLabel")))
    if not phenos:
        return None                      # no mouse-knockout data -> abstain
    sym = target.symbol or "the target"
    return Datapoint(
        value=phenos,
        label="mouse knockout phenotypes (IMPC)",
        summary=f"{len(phenos)} knockout phenotype(s), e.g. {', '.join(phenos[:3])}",
        source="IMPC via Open Targets",
        url=f"https://platform.opentargets.org/target/{ens}?tab=mouse_phenotypes")


# --- guardrail predicates: classes where genetic direction != therapeutic direction --------------
# direction-of-effect assumes a monotonic dose-response; oncology (germline != somatic) and ion
# channels (U-shaped: both too-much and too-little are pathological) violate that assumption.

def is_oncology(disease: Disease) -> bool:
    efo = disease.efo if disease else None
    if not efo:
        return False
    query = """query D($id:String!){ disease(efoId:$id){ therapeuticAreas{ id } } }"""
    dis = (ot_query(query, {"id": efo}) or {}).get("disease")
    # "MONDO_0045024" = the "cancer or benign tumor" therapeutic area
    return bool(dis) and any(t["id"] == "MONDO_0045024" for t in (dis.get("therapeuticAreas") or []))


def is_ion_channel(target: Target) -> bool:
    ens = target.ensembl if target else None
    if not ens:
        return False
    query = """query T($id:String!){ target(ensemblId:$id){ targetClass{ label } } }"""
    tgt = (ot_query(query, {"id": ens}) or {}).get("target")
    return bool(tgt) and any(c.get("label") == "Ion channel" for c in (tgt.get("targetClass") or []))


# --- disease specificity (keyed on raw efo id; build.py uses ids, not passport objects) -----------
@dataclass
class Specificity:
    n_descendants: int                  # how many diseases sit *under* this term (broad = many)
    is_therapeutic_area: bool           # a top-level root (e.g. "cardiovascular disorder")


# How specific a disease term is — used by the benchmark builder to drop broad umbrella terms.
def disease_specificity(efo: str) -> Specificity | None:
    query = """query D($id:String!){ disease(efoId:$id){ descendants therapeuticAreas{ id } } }"""
    dis = (ot_query(query, {"id": efo}) or {}).get("disease")
    if not dis:
        return None
    tas = {t["id"] for t in (dis.get("therapeuticAreas") or [])}
    return Specificity(n_descendants=len(dis.get("descendants") or []),
                       is_therapeutic_area=efo in tas)
