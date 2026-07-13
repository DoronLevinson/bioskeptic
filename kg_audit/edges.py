import os
import random
import tarfile
import urllib.request

# DRKG (Drug Repurposing Knowledge Graph) ships as one ~90 MB tarball holding a single 3-column TSV
# (head \t relation \t tail), with entities like "Gene::7157" and "Disease::MESH:D001943".
DRKG_URL = "https://dgl-data.s3-us-west-2.amazonaws.com/dataset/DRKG/drkg.tar.gz"
_CACHE = os.path.join(os.path.dirname(__file__), "data")


# Download + extract drkg.tsv once into the cache dir; returns its path.
def ensure_drkg(cache_dir: str = _CACHE) -> str:
    os.makedirs(cache_dir, exist_ok=True)
    tsv = os.path.join(cache_dir, "drkg.tsv")
    if os.path.exists(tsv):
        return tsv
    tgz = os.path.join(cache_dir, "drkg.tar.gz")
    if not os.path.exists(tgz):
        urllib.request.urlretrieve(DRKG_URL, tgz)
    with tarfile.open(tgz) as tar:
        # basename == "drkg.tsv" skips the macOS AppleDouble sidecar "._drkg.tsv"
        member = next(m for m in tar.getmembers() if os.path.basename(m.name) == "drkg.tsv")
        member.name = "drkg.tsv"          # flatten any leading dir
        tar.extract(member, cache_dir)
    return tsv


# Reservoir-sample n random Gene<->Disease edges from DRKG, normalised to (target, relation, disease).
# Returns a dataframe [target, relation, disease] and the total number of Gene-Disease edges seen.
def sample_target_disease(n: int = 100, seed: int = 0, cache_dir: str = _CACHE):
    import pandas as pd
    tsv = ensure_drkg(cache_dir)
    rng = random.Random(seed)
    reservoir, seen = [], 0
    with open(tsv) as fh:
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) != 3:
                continue
            h, rel, t = parts
            if h.startswith("Gene::") and t.startswith("Disease::"):
                gene, dis = h, t
            elif h.startswith("Disease::") and t.startswith("Gene::"):
                gene, dis = t, h
            else:
                continue
            seen += 1
            rec = {"target": gene, "relation": rel, "disease": dis}
            if len(reservoir) < n:
                reservoir.append(rec)
            else:
                j = rng.randint(0, seen - 1)
                if j < n:
                    reservoir[j] = rec
    return pd.DataFrame(reservoir), seen
