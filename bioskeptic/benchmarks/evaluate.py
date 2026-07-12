import collections
import json
import pathlib

from bioskeptic.refute.core import ClaimTriple

HERE = pathlib.Path(__file__).parent

# which stat-group a row belongs to
def _group(r):
    if r["label"]:
        return "true"
    return {"constructed_disease_swap": "swap", "refuted_curated": "clingen"}.get(r["negative_type"])


# Run one mechanism over the benchmark and print per-group counts + a confusion matrix (non-na) +
# precision/recall. Positive class = "a false claim that should fire". target_disease.jsonl carries all
# three groups (TRUE, disease-swap, ClinGen); use drug_disease.jsonl for drug-dependent mechanisms.
def evaluate(mechanism, dataset="target_disease.jsonl"):
    rows = [json.loads(l) for l in open(HERE / dataset)]
    stats = collections.defaultdict(collections.Counter)          # group -> {fired, didnt, na}
    for r in rows:
        g = _group(r)
        if g is None:
            continue
        f = mechanism.check(ClaimTriple.from_benchmark_row(r))
        stats[g]["na" if f is None else ("fired" if f.flagged else "didnt")] += 1

    labels = {"true": "TRUE (approved)", "swap": "FALSE disease-swap", "clingen": "FALSE ClinGen refuted"}
    print(f"\n=== {mechanism.NAME}  ({dataset}) ===\n")
    for g in ("true", "swap", "clingen"):
        s = stats[g]
        n = s["fired"] + s["didnt"] + s["na"]
        print(f"  {labels[g]:24s} n={n:<4} fired={s['fired']:<4} didnt={s['didnt']:<4} na={s['na']}")

    # confusion matrix over the non-na rows (false = swap + clingen; true = approved)
    tp = stats["swap"]["fired"] + stats["clingen"]["fired"]
    fn = stats["swap"]["didnt"] + stats["clingen"]["didnt"]
    fp = stats["true"]["fired"]
    tn = stats["true"]["didnt"]
    print("\n  confusion (non-na):        fired   not-fired")
    print(f"    false claim (should fire)  TP={tp:<5} FN={fn}")
    print(f"    true  claim (should not)   FP={fp:<5} TN={tn}")
    prec = tp / (tp + fp) if (tp + fp) else float("nan")
    rec = tp / (tp + fn) if (tp + fn) else float("nan")
    print(f"\n  precision = TP/(TP+FP) = {tp}/{tp + fp} = {prec:.2f}")
    print(f"  recall    = TP/(TP+FN) = {tp}/{tp + fn} = {rec:.2f}")
