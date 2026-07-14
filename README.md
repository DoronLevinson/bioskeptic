# BioSkeptic

**Try it live: [bioskeptic.onrender.com](https://bioskeptic.onrender.com/)**

BioSkeptic gives an AI better tools to check a drug–target–disease idea against real biological evidence —
so its answer is something you can **verify**, not just something that sounds right.

<!-- demo video goes here -->

## Introduction

Most drugs fail, and they fail for all kinds of reasons — they don't work, they aren't safe enough, they
aren't worth the cost. Much of that you only find out late, in the clinic. But one thing you *can*
sanity-check early is whether a drug–target–disease idea even holds up against what we already know. People
increasingly put that question to an AI, which is reasonable — but a language model answers from memory, and
it sounds just as confident whether or not there's real evidence behind what it says. You get something
plausible, with no easy way to check it.

BioSkeptic gives the model better tools for that one question. It checks the idea against real biological
data — is the target active where the disease is, do the genetics line up, has anything like it been tried —
and returns the concerns it finds, **each with a link to its source**. It doesn't tell you yes or no; it just
makes the answer checkable. The same tools work at scale, too: flagging the shaky links in a knowledge graph
or dataset before a model is trained on them.

It's one part of the picture — not a full assessment of a drug program — but it's a part you can check early,
and it makes consulting an AI on these ideas more reliable and easier to verify.

## How it works

BioSkeptic never hands down a verdict. Every check is a **suggestive, cited flag** with a documented
reliability, and the agent weighs them like a red-team lawyer — raising concerns, not passing judgement.

- **Data sources.** Every check is grounded in ~21 public biomedical databases — Open Targets (human
  genetics, associations, mouse phenotypes), GTEx and the Human Protein Atlas (expression), ChEMBL, ClinGen,
  EpiGraphDB, ClinicalTrials.gov, PubMed, and the FDA label. Each datapoint is one grounded fact with a link
  a human can open. → [`docs/data_sources.md`](bioskeptic/docs/data_sources.md)
- **Refuting mechanisms.** A set of specific, falsifiable questions drawn from the target-validation
  literature: *is the target expressed in the affected tissue? do human genetics point the right therapeutic
  direction? does deleting the gene in mice do anything relevant? is the link only a paper co-mention?* We
  catalogued ~18; **8 are implemented so far**, each with its own known blind spots.
  → [`docs/refute_mechanisms.md`](bioskeptic/docs/refute_mechanisms.md)
- **Benchmark & performance.** To know which mechanisms to trust, we built an objective benchmark from
  **approved** drug–target–disease indications (true), gene–disease links **refuted or disputed in ClinGen**
  (hard negatives), and **disease-swaps** (easy negatives), then measured each mechanism's precision and
  recall. Those numbers feed into how the agent weighs each flag. → [`bioskeptic/benchmarks/`](bioskeptic/benchmarks)

## Use it

**Try it live:** [bioskeptic.onrender.com](https://bioskeptic.onrender.com) — the chat app, running now, nothing to
install. Give it a claim like *"evolocumab inhibits PCSK9 to treat high LDL"* and it'll pin down the entities and
hand back a cited red-team report.

For your own agent or pipeline, both the MCP server and the library are **free and local** — they run on your
machine with your **own** `ANTHROPIC_API_KEY` (a few checks call an LLM; the rest are free public-database lookups).

```bash
git clone https://github.com/DoronLevinson/bioskeptic && cd bioskeptic
pip install -e .            # or:  uv sync
export ANTHROPIC_API_KEY=sk-ant-...
```

### MCP server — give any agent BioSkeptic's tools
The engine is exposed as tools an AI agent can call (`resolve_target/drug/disease`, `build_report`,
`search_trials`, `search_pubmed`, `fda_label`, `drug_targets`). It runs over **stdio**, so the client
launches it locally. Add it to `claude_desktop_config.json` and restart Claude:

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

Then ask it something like *"use bioskeptic to red-team: evolocumab inhibits PCSK9 to treat high LDL."*

### Python library — `bioskeptic.refine`
Runs the same panel over the target–disease relations in a dataset or knowledge graph and flags the
weakly-grounded ones, each with a cited reason.

```python
from bioskeptic.refine import audit_pair, audit_dataframe

r = audit_pair(target="TP53", disease="type 2 diabetes")
r.flagged        # True
print(r.details) # reasons + source links

out = audit_dataframe(df)   # df with 'target' and 'disease' cols → adds flagged / flags / findings columns
```

A saved 100-edge run on DRKG lives at
[`bioskeptic/refine/sample_drkg_100.csv`](bioskeptic/refine/sample_drkg_100.csv).

### Web app
```bash
uvicorn web.app:app --reload    # then open http://127.0.0.1:8000
```
