import collections
import csv
import json
import pathlib
import random

from bioskeptic.data.opentargets import disease_specificity
from bioskeptic.refute.core import ClaimTriple
from bioskeptic.refute.registry import MECHANISMS
from bioskeptic.resolver.fetch import ot_query, get_json

HERE = pathlib.Path(__file__).parent
SOURCES = HERE / "sources"
SOURCE_DATE = "2026-07-12"                 # download date -> each row's source_version
SEED = 0                                   # deterministic sampling + scrambling

# how many rows of each kind (kept small + simple; total well under 500)
N_TRUE = 100                               # approved pairs (the precision / mis-fire set)
N_CLINGEN_NEG = 50                         # expert-refuted target-disease negatives
N_SWAP = 150                               # easy negatives: random disease-swaps
N_FLIP = 0                                 # direction flips removed — only #1/#6 are direction-sensitive
                                           # and need clean-genetic-direction pairs; re-add a proper
                                           # direction cohort when #6 lands
SPECIFICITY_MAX = 50                       # drop indications whose disease has > this many descendants (too broad)

# ChEMBL action_type -> our coarse therapeutic direction (only the cleanly-flippable ones)
_INHIBIT = {"INHIBITOR", "ANTAGONIST", "BLOCKER", "NEGATIVE ALLOSTERIC MODULATOR",
            "DEGRADER", "INVERSE AGONIST", "DISRUPTING AGENT"}
_ACTIVATE = {"AGONIST", "ACTIVATOR", "POSITIVE ALLOSTERIC MODULATOR", "PARTIAL AGONIST",
             "STABILISER", "OPENER"}


# --- sources -------------------------------------------------------------------------------------

# A page of approved (max_phase 4) molecule ids from ChEMBL, newest-registered first.
def approved_chembl_ids(limit=400):
    url = f"https://www.ebi.ac.uk/chembl/api/data/molecule.json?max_phase=4&limit={limit}"
    d = get_json(url) or {}
    return [(m["molecule_chembl_id"], (m.get("pref_name") or "").title())
            for m in d.get("molecules", []) if m.get("pref_name")]


# One Open Targets drug() call -> its mechanism targets (with direction) + its APPROVAL indications.
def ot_drug(chembl):
    q = """query D($id:String!){ drug(chemblId:$id){ name
      mechanismsOfAction{ rows{ actionType targets{ id approvedSymbol } } }
      indications{ rows{ maxClinicalStage disease{ id name } } } } }"""
    d = ot_query(q, {"id": chembl})
    return (d or {}).get("drug")


# Cheap symbol -> Ensembl gene id via mygene (one call), for ClinGen rows.
def symbol_to_ensembl(symbol):
    d = get_json(f"https://mygene.info/v3/query?q=symbol:{symbol}&species=human&fields=ensembl.gene")
    hits = (d or {}).get("hits") or []
    if not hits:
        return None
    ens = hits[0].get("ensembl")
    if isinstance(ens, list):
        ens = ens[0] if ens else None
    return (ens or {}).get("gene") if isinstance(ens, dict) else None


# --- row construction ----------------------------------------------------------------------------

def _direction(action_type):
    if action_type in _INHIBIT:
        return "inhibit"
    if action_type in _ACTIVATE:
        return "activate"
    return None


def _row(kind, drug, target, disease, direction, relation, label, negative_type, source):
    return {"kind": kind, "drug": drug, "target": target, "disease": disease,
            "direction": direction, "relation": relation, "label": label,
            "negative_type": negative_type, "source": source, "source_version": SOURCE_DATE,
            "pubmed_bin": None}


# Which mechanisms actually have a datum for this row (availability, not the fired/silent outcome).
def _coverage(row):
    claim = ClaimTriple.from_benchmark_row(row)
    return [m.name for m in MECHANISMS if m.available(claim)]


# Build the TRUE approved rows: one per (drug, primary target, approved disease), deduped + sampled.
def build_true_rows(rng):
    rows, seen = [], set()
    for chembl, name in approved_chembl_ids():
        drug = ot_drug(chembl)
        if not drug:
            continue
        moa = (drug.get("mechanismsOfAction") or {}).get("rows") or []
        target, direction = None, None
        for r in moa:                              # first row that names a human target
            if r.get("targets"):
                t = r["targets"][0]
                target = {"ensembl": t["id"], "symbol": t.get("approvedSymbol")}
                direction = _direction(r.get("actionType"))
                break
        if not target:
            continue
        for ind in (drug.get("indications") or {}).get("rows") or []:
            if ind.get("maxClinicalStage") != "APPROVAL":
                continue
            dis = ind["disease"]
            sp = disease_specificity(dis["id"])           # keep only specific diseases, not broad umbrellas
            if not sp or sp.is_therapeutic_area or sp.n_descendants > SPECIFICITY_MAX:
                continue
            key = (chembl, target["ensembl"], dis["id"])
            if key in seen:
                continue
            seen.add(key)
            rows.append(_row("drug_disease", {"chembl": chembl, "name": name.title()},
                             target, {"efo": dis["id"], "name": dis["name"]},
                             direction, "indicated_for", True, None, "open_targets"))
        if len(rows) >= N_TRUE * 3:                # gather a surplus, then precheck down
            break
    rng.shuffle(rows)
    selected = []
    for r in rows:                                 # precheck: keep rows some mechanism has data for
        cov = _coverage(r)
        if not cov:
            continue
        r["coverage"] = cov
        selected.append(r)
        if len(selected) >= N_TRUE:
            break
    return selected


# Read ClinGen validity CSV -> refuted target-disease negatives (Refuted / Disputed / No-Known).
def build_clingen_negatives(rng):
    neg_labels = {"Refuted", "Disputed", "No Known Disease Relationship"}
    raw = []
    with open(SOURCES / "clingen_validity.csv", newline="") as f:
        for c in csv.reader(f):
            if len(c) < 7 or c[6] not in neg_labels:
                continue
            raw.append((c[0], c[2], c[3]))         # symbol, disease name, MONDO id
    rng.shuffle(raw)
    rows = []
    for symbol, disease_name, mondo in raw:
        if len(rows) >= N_CLINGEN_NEG:
            break
        ens = symbol_to_ensembl(symbol)
        if not ens:
            continue
        efo = mondo.replace(":", "_")              # "MONDO:0013212" -> OT-style "MONDO_0013212"
        rows.append(_row("target_disease", None, {"ensembl": ens, "symbol": symbol},
                         {"efo": efo, "name": disease_name}, None, "therapeutic_target",
                         False, "refuted_curated", "clingen"))
    return rows


# Easy negatives: swap each row's disease for a random unrelated one; flip a slice of directions.
def build_scrambles(true_rows, rng):
    real = {(r["target"]["ensembl"], r["disease"]["efo"]) for r in true_rows}
    diseases = list({(r["disease"]["efo"], r["disease"]["name"]) for r in true_rows})
    swaps = []
    for r in rng.sample(true_rows, min(N_SWAP, len(true_rows))):
        for _ in range(10):                        # try a few times to dodge a real pair
            efo, name = rng.choice(diseases)
            if (r["target"]["ensembl"], efo) not in real:
                break
        else:
            continue
        swaps.append(_row(r["kind"], r["drug"], r["target"], {"efo": efo, "name": name},
                          r["direction"], r["relation"], False, "constructed_disease_swap",
                          "open_targets"))
    flips = []
    flippable = [r for r in true_rows if r["direction"] in ("inhibit", "activate")]
    for r in rng.sample(flippable, min(N_FLIP, len(flippable))):
        flipped = "activate" if r["direction"] == "inhibit" else "inhibit"
        flips.append(_row(r["kind"], r["drug"], r["target"], r["disease"], flipped,
                          r["relation"], False, "constructed_direction_flip", "open_targets"))
    return swaps + flips


# --- entry point ---------------------------------------------------------------------------------

def _write(path, rows):
    with open(path, "w") as f:
        for i, r in enumerate(rows):
            f.write(json.dumps({"id": f"{path.stem}_{i:04d}", **r}) + "\n")


def main():
    rng = random.Random(SEED)
    print("building TRUE approved rows from Open Targets ...")
    true_rows = build_true_rows(rng)
    print(f"  TRUE approved pairs: {len(true_rows)}")

    scrambles = build_scrambles(true_rows, rng)
    print(f"  scramble negatives:  {len(scrambles)}")

    print("building ClinGen refuted negatives ...")
    clingen = build_clingen_negatives(rng)
    print(f"  ClinGen negatives:   {len(clingen)}")

    for r in scrambles + clingen:                  # precheck-annotate the negatives too
        r["coverage"] = _coverage(r)
    cov_dist = collections.Counter(len(r["coverage"]) for r in true_rows)
    print(f"  TRUE coverage (# mechanisms with data per row): {dict(sorted(cov_dist.items()))}")

    # drug_disease.jsonl = TRUE approved + their scrambles
    dd = true_rows + scrambles
    _write(HERE / "drug_disease.jsonl", dd)

    # target_disease.jsonl = TRUE collapsed to target-disease + ClinGen negatives + target scrambles
    td_true = [{**r, "kind": "target_disease", "drug": None, "relation": "therapeutic_target"}
               for r in true_rows]
    td_scr = [{**r, "kind": "target_disease", "drug": None, "relation": "therapeutic_target"}
              for r in scrambles]
    td = td_true + clingen + td_scr
    _write(HERE / "target_disease.jsonl", td)

    print(f"\nwrote drug_disease.jsonl   ({len(dd)} rows: {len(true_rows)} true / {len(scrambles)} false)")
    print(f"wrote target_disease.jsonl ({len(td)} rows: {len(td_true)} true / {len(clingen)+len(td_scr)} false)")


if __name__ == "__main__":
    main()
