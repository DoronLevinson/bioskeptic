import urllib.parse as up
from dataclasses import dataclass

from bioskeptic.resolver.fetch import get_json

_CT = "https://clinicaltrials.gov/api/v2/studies"


@dataclass
class Trial:
    nct: str
    title: str
    phase: str
    status: str
    why_stopped: str          # populated only for terminated / withdrawn trials — the key red-team field
    url: str


# Search ClinicalTrials.gov (v2 API) for trials of an intervention (drug) in a condition (disease).
# Either may be blank (drug-only or disease-only search). Returns (total match count, the top k trials).
# why_stopped is set only for terminated/withdrawn studies — the highest-signal field for "tried and failed".
def search(intervention: str = "", condition: str = "", k: int = 10) -> tuple[int, list[Trial]]:
    if not (intervention or condition):
        return 0, []
    params = {"pageSize": str(k), "countTotal": "true"}
    if intervention:
        params["query.intr"] = intervention
    if condition:
        params["query.cond"] = condition
    ct = get_json(f"{_CT}?{up.urlencode(params)}")
    if not ct:
        return 0, []
    trials = []
    for s in ct.get("studies", []):
        p = s.get("protocolSection", {})
        idm = p.get("identificationModule", {})
        st = p.get("statusModule", {})
        des = p.get("designModule", {})
        nct = idm.get("nctId") or ""
        phases = des.get("phases") or []
        trials.append(Trial(
            nct=nct,
            title=idm.get("briefTitle") or "",
            phase=" / ".join(ph.replace("PHASE", "Phase ") for ph in phases) or "N/A",
            status=st.get("overallStatus") or "",
            why_stopped=st.get("whyStopped") or "",
            url=f"https://clinicaltrials.gov/study/{nct}",
        ))
    return int(ct.get("totalCount") or 0), trials
