import urllib.parse as up
from dataclasses import dataclass

from bioskeptic.resolver.fetch import get_json

_FDA = "https://api.fda.gov/drug/label.json"

# Structured label sections we surface, most red-team-relevant first (safety before indication).
_SECTIONS = [
    ("boxed_warning", "Boxed warning"),
    ("warnings_and_cautions", "Warnings & cautions"),
    ("warnings", "Warnings"),
    ("contraindications", "Contraindications"),
    ("adverse_reactions", "Adverse reactions"),
    ("indications_and_usage", "Indications & usage"),
]


@dataclass
class Label:
    brand: str
    generic: str
    sections: dict            # {human section name: text}
    url: str                  # DailyMed page for the label, when available


# Fetch the FDA-approved structured drug label for `drug` (brand or generic name). Returns None if the
# drug has no FDA label (novel or non-US drugs won't). Surfaces the safety-relevant sections, each
# truncated to `chars`, so on-target-tox and safety concerns can be grounded in the official label.
def label(drug: str, chars: int = 600) -> Label | None:
    if not drug:
        return None
    q = up.quote(f'(openfda.generic_name:"{drug}" OR openfda.brand_name:"{drug}")')
    fda = get_json(f"{_FDA}?search={q}&limit=1")
    res = (fda or {}).get("results") or []
    if not res:
        return None
    r = res[0]
    of = r.get("openfda", {})
    sections = {}
    for key, human in _SECTIONS:
        val = r.get(key)
        if val:
            text = " ".join(val) if isinstance(val, list) else str(val)
            sections[human] = text.strip()[:chars]
    set_id = r.get("set_id") or ""
    return Label(
        brand=", ".join(of.get("brand_name") or []) or drug,
        generic=", ".join(of.get("generic_name") or []),
        sections=sections,
        url=(f"https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid={set_id}"
             if set_id else "https://open.fda.gov/apis/drug/label/"),
    )
