# BioSkeptic — an AI red team for drug-discovery claims

BioSkeptic pressure-tests **drug → target → disease** claims by running them against a panel of
**grounded refuting mechanisms** — checks backed by real biomedical databases (Open Targets genetics,
GTEx, the Human Protein Atlas, IMPC mouse knockouts, ClinicalTrials.gov, PubMed, the FDA label). Every
concern it raises comes with a **source link you can open and check**, so it's an *auditable* second
opinion, not a black box.

It ships in three forms:

| Form | What it is | Who it's for |
|---|---|---|
| **Chat / web app** (`web/`) | the interactive red-team assistant | end users |
| **MCP server** (`mcp_server/`) | the same tools exposed to any AI agent | Claude Desktop / Code, other MCP clients |
| **`bioskeptic.refine`** (Python library) | batch data/KG refinement | data & ML pipelines |

Both the MCP server and the library are **free and local** — they run on your machine and use **your own**
`ANTHROPIC_API_KEY` (a few of the checks call an LLM; the rest are free public-database lookups).

---

## Install

```bash
git clone https://github.com/DoronLevinson/bioskeptic && cd bioskeptic
pip install -e .            # or:  uv sync
export ANTHROPIC_API_KEY=sk-ant-...   # used by the LLM-backed mechanisms
```

---

## 1. MCP server — give any agent BioSkeptic's tools

The MCP server exposes BioSkeptic's engine as **tools an AI agent can call**. It runs over **stdio** by
default — the client launches it locally and talks over stdin/stdout, so it's free and private.

### The tools it provides
- **Resolvers** — `resolve_target`, `resolve_drug`, `resolve_disease` (+ `suggest_*`): turn a messy name
  or a knowledge-graph id (`Gene::7157`, `Disease::MESH:…`) into a grounded ID passport.
- **`drug_targets`** — a drug's direct mechanism-of-action target(s) from Open Targets/ChEMBL.
- **`build_report`** — the core: runs *every* refuting mechanism on a resolved drug–target–disease claim
  and returns a structured report (flagged concerns, checks that passed, precision, cited links).
- **Dig tools** — `search_trials` (ClinicalTrials.gov), `search_pubmed` (PubMed), `fda_label` (FDA label):
  chase a concern down to primary evidence, keyed on the ids you already resolved.

### Add it to Claude Desktop
Add this to your `claude_desktop_config.json` (Settings → Developer → Edit Config), then restart Claude:

```json
{
  "mcpServers": {
    "bioskeptic": {
      "command": "uv",
      "args": ["run", "python", "-m", "mcp_server.server"],
      "cwd": "/absolute/path/to/bioskeptic",
      "env": { "ANTHROPIC_API_KEY": "sk-ant-..." }
    }
  }
}
```

Now ask Claude something like *"use bioskeptic to red-team: evolocumab inhibits PCSK9 to treat high LDL
cholesterol"* and it will call the tools and hand you a cited report.

*(To run it as a hosted HTTP endpoint instead of stdio, set `MCP_TRANSPORT=streamable-http`.)*

---

## 2. `bioskeptic.refine` — batch data & KG refinement

The datasets and knowledge graphs behind drug discovery are **noisy**: many target–disease links are just
text-mined co-mentions with no real biology behind them. `bioskeptic.refine` runs the refuting panel over
those relations and **flags the weakly-grounded ones**, each with a cited reason — so you can clean a
dataset, refine a KG, or train repurposing models on relations that actually hold up.

### One relation
```python
from bioskeptic.refine import audit_pair

r = audit_pair(target="TP53", disease="type 2 diabetes")   # names, ids, or DRKG ids all work
r.flagged          # True
r.flag_mechanisms  # ['text_mining_only', 'mouse_ko_normal']
print(r.details)   # human-readable reasons + source links
r.findings         # structured: [{mechanism, title, reason, sources: [...]}, ...]
```

### A whole dataframe
```python
import pandas as pd
from bioskeptic.refine import audit_dataframe

df = pd.DataFrame({"target": ["TP53", "PCSK9"], "disease": ["type 2 diabetes", "high LDL cholesterol"]})
out = audit_dataframe(df)     # runs concurrently; adds columns:
#   target_name, disease_name, resolved, flagged, flags, flag_mechanisms, findings
out[out["flags"] >= 2]        # keep only corroborated flags
```

### Sample & audit a real knowledge graph (DRKG)
```python
from bioskeptic.refine import sample_target_disease, audit_dataframe

df, total = sample_target_disease(n=100)   # downloads DRKG once, samples 100 Gene–Disease edges
out = audit_dataframe(df)
print(f"flagged {out['flagged'].sum()} of {len(out)}")
```

A saved 100-edge run lives at [`bioskeptic/refine/sample_drkg_100.csv`](bioskeptic/refine/sample_drkg_100.csv).
On that sample, the strict "≥3 mechanisms" tier flags 16 relations, **13 of them genuine (~81% precision)**.

**Cost note:** three of the eight mechanisms call an LLM (a few cents per audit on your key); the other
five and all resolution are free public-database lookups.

---

## Web app
```bash
uvicorn web.app:app --reload    # then open http://127.0.0.1:8000
```
