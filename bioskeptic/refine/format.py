from bioskeptic.refute.core import Finding
from bioskeptic.refute.redteam import _TITLES


# A flagged Finding -> a compact one-line string: the reason + its source links.
def finding_to_string(f: Finding) -> str:
    title = _TITLES.get(f.mechanism, f.mechanism.replace("_", " ").capitalize())
    line = f"⚑ {title}: {f.explanation}"
    srcs = [s for s in (f.sources or []) if s]
    if srcs:
        line += f"  (sources: {' | '.join(srcs)})"
    return line
