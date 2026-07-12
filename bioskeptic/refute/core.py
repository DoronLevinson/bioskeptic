from dataclasses import dataclass, field

from bioskeptic.resolver.disease import Disease
from bioskeptic.resolver.drug import Drug
from bioskeptic.resolver.target import Target


# The claim a refuting mechanism tries to break: three passports + the claimed drug->target direction.
@dataclass
class ClaimTriple:
    target: Target | None = None
    disease: Disease | None = None
    drug: Drug | None = None
    direction: str | None = None          # "inhibit" | "activate" — the claimed drug->target action

    # Build a claim straight from a benchmark JSONL row (partial passports, no resolution needed).
    @classmethod
    def from_benchmark_row(cls, row: dict) -> "ClaimTriple":
        t = row.get("target") or {}
        d = row.get("disease") or {}
        dr = row.get("drug")
        return cls(
            target=Target(symbol=t.get("symbol"), ensembl=t.get("ensembl")),
            disease=Disease(name=d.get("name"), efo=d.get("efo")),
            drug=Drug(name=dr.get("name"), chembl_id=dr.get("chembl")) if dr else None,
            direction=row.get("direction"),
        )


# The result one refuting mechanism returns: fired or not, a human explanation, and its sources.
@dataclass
class Finding:
    mechanism: str                        # mechanism name, e.g. "direction_of_effect"
    flagged: bool                         # True = a grounded concern fired · False = checked, clean.
                                          # SUGGESTIVE, not a verdict: a cited flag the agent weighs
                                          # (each mechanism has known mis-fire patterns — see the docs).
    explanation: str                      # human sentence, filled from a premade template + the datum
    sources: list[str] = field(default_factory=list)   # links: data-source page + citations
