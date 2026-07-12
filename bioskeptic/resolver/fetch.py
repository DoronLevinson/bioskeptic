import json
import urllib.request

OT_URL = "https://api.platform.opentargets.org/api/v4/graphql"
TIMEOUT = 60   # UniChem can be slow; be patient
RETRIES = 2    # public APIs (UniChem especially) throw transient 500s
_HEADERS = {"User-Agent": "bioskeptic/0.1", "Accept": "application/json"}

# In-process memo. Only *successful* results are stored, so a transient failure is never cached forever.
_CACHE: dict = {}


# Fetch + parse a request, with retry; cache only non-None results. `build` is a no-arg -> urllib Request.
def _fetch(key: tuple, build) -> dict | None:
    if key in _CACHE:
        return _CACHE[key]
    for _ in range(RETRIES):
        try:
            with urllib.request.urlopen(build(), timeout=TIMEOUT) as r:
                val = json.loads(r.read().decode())
            _CACHE[key] = val
            return val
        except Exception:
            continue
    return None


# POST a GraphQL query to Open Targets -> the 'data' object, or None.
def ot_query(query: str, variables: dict) -> dict | None:
    key = ("ot", query, json.dumps(variables, sort_keys=True))
    body = json.dumps({"query": query, "variables": variables}).encode()
    d = _fetch(key, lambda: urllib.request.Request(OT_URL, data=body, headers={**_HEADERS, "Content-Type": "application/json"}))
    return d.get("data") if d else None


# GET a JSON URL (mygene / GTEx / ChEMBL / UniProt) -> the parsed body, or None.
def get_json(url: str) -> dict | None:
    return _fetch(("get", url), lambda: urllib.request.Request(url, headers=_HEADERS))


# POST a JSON body to a REST endpoint (e.g. UniChem) -> the parsed body, or None.
def post_json(url: str, payload: dict) -> dict | None:
    key = ("post", url, json.dumps(payload, sort_keys=True))
    body = json.dumps(payload).encode()
    return _fetch(key, lambda: urllib.request.Request(url, data=body, headers={**_HEADERS, "Content-Type": "application/json"}))
