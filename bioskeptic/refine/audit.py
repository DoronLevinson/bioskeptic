from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from bioskeptic.refute.core import ClaimTriple
from bioskeptic.refute.redteam import _TITLES, red_team
from bioskeptic.resolver.disease import resolve_disease
from bioskeptic.resolver.target import resolve_target
from bioskeptic.refine.format import finding_to_string


@dataclass
class AuditResult:
    target: str                                    # input id / name
    disease: str
    target_name: str | None = None                 # resolved symbol
    disease_name: str | None = None                # resolved disease name
    resolved: bool = False                         # did both entities resolve to usable ids?
    flagged: bool = False                          # did any refuting mechanism fire?
    flags: list = field(default_factory=list)      # list[str]: one reason+sources line per fired mechanism
    flag_mechanisms: list = field(default_factory=list)  # machine names of the mechanisms that fired
    findings: list = field(default_factory=list)   # structured: [{mechanism, title, reason, sources}]
    details: str | None = None                     # the flags joined, or None if nothing fired
    n_flagged: int = 0
    n_clean: int = 0
    n_na: int = 0                                  # mechanisms that abstained (no data / out of scope)
    error: str | None = None


# Audit ONE target-disease connection: resolve both entities, run every refuting mechanism, and return
# the flags (reason + source links) for any that fired. `direction` ('inhibit'/'activate') is optional —
# the direction-dependent mechanisms simply abstain without it.
def audit_pair(target: str, disease: str, direction: str | None = None) -> AuditResult:
    try:
        tgt = resolve_target(target)
        dis = resolve_disease(disease)
    except Exception as e:
        return AuditResult(target, disease, resolved=False, flagged=False, error=f"{type(e).__name__}: {e}")
    if not (tgt and tgt.ensembl and dis and dis.efo):
        return AuditResult(target, disease, resolved=False, flagged=False,
                           error="could not resolve target and/or disease to usable ids")
    try:
        report = red_team(ClaimTriple(target=tgt, disease=dis, direction=direction))
    except Exception as e:
        return AuditResult(target, disease, target_name=tgt.symbol, disease_name=dis.name,
                           resolved=True, flagged=False, error=f"{type(e).__name__}: {e}")
    flags = [finding_to_string(f) for f in report.flagged]
    findings = [{"mechanism": f.mechanism,
                 "title": _TITLES.get(f.mechanism, f.mechanism.replace("_", " ").capitalize()),
                 "reason": f.explanation, "sources": [s for s in (f.sources or []) if s]}
                for f in report.flagged]
    return AuditResult(
        target=target, disease=disease, target_name=tgt.symbol, disease_name=dis.name, resolved=True,
        flagged=bool(flags), flags=flags, flag_mechanisms=[f.mechanism for f in report.flagged],
        findings=findings, details=("\n".join(flags) or None),
        n_flagged=len(report.flagged), n_clean=len(report.clean), n_na=len(report.not_applicable))


# Audit every row of a dataframe and return a COPY with new columns: `flagged` (bool) and `details`
# (the reason+sources string, or None when nothing fired). Also adds `resolved`. Rows run concurrently
# — the work is IO-bound (HTTP database lookups + Claude calls), so threads give a big speed-up.
def audit_dataframe(df, target_col: str = "target", disease_col: str = "disease",
                    direction_col: str | None = None, workers: int = 8):
    records = df.to_dict("records")

    def _one(rec):
        return audit_pair(rec[target_col], rec[disease_col],
                          rec.get(direction_col) if direction_col else None)

    with ThreadPoolExecutor(max_workers=workers) as ex:
        results = list(ex.map(_one, records))

    out = df.copy()
    out["target_name"] = [r.target_name for r in results]
    out["disease_name"] = [r.disease_name for r in results]
    out["resolved"] = [r.resolved for r in results]
    out["flagged"] = [r.flagged for r in results]
    out["flags"] = [r.n_flagged for r in results]
    out["flag_mechanisms"] = [";".join(r.flag_mechanisms) for r in results]
    out["findings"] = [r.details for r in results]
    return out
