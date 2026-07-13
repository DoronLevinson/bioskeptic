from dataclasses import dataclass, field
from typing import Any


# One meaningful, cited fact pulled from a source — the uniform return of every data/ fetcher.
@dataclass
class Datapoint:
    value: Any                       # the fact itself: number / string / bool / small dict
    label: str                       # what it is, e.g. "genetically-therapeutic direction"
    summary: str                     # human phrasing of the value, e.g. "loss-of-function is protective (32 rows)"
    source: str                      # provenance name, e.g. "Open Targets genetics"
    url: str | None = None           # link a human can open to verify
    citations: list[str] = field(default_factory=list)   # PMIDs / dataset links
