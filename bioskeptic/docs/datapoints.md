# BioSkeptic — datapoints

What we pull from each source, and what it serves. This is the contract the `bioskeptic/data/` fetch
layer implements. **Use** legend: **E** = feeds an existing refuting mechanism (# shown) · **P** =
shown in the profiling report · **F** = feeds a future mechanism.

Every fetch consumes an id from a resolver *passport* (see [`data_sources.md`](./data_sources.md)) and
returns the value plus its provenance (source + link).

## Open Targets (the hub — most datapoints, ~one GraphQL call each)

| Datapoint | Source | Use |
|---|---|---|
| Genetic direction-of-effect (`evidences.directionOnTarget/onTrait`) | Open Targets | **E #1** |
| L2G / colocalization score at the locus | Open Targets | **E #2** |
| Association evidence-type breakdown (`datatypeScores`) | Open Targets | **E #4**, **P** |
| Gene-burden effect size (`beta` / OR) | Open Targets | **E #5** |
| Overall target↔disease association score | Open Targets | **P** |
| Mechanism of action → target + `actionType` (direction) | Open Targets | **E #1**, **P** (drug→target edge) |
| Known drugs (drug↔disease↔phase) | Open Targets | **P** (indications / disease's drugs) |
| DepMap essentiality (`depMapEssentiality.geneEffect` per lineage) | Open Targets | **E #12**, **P**, **F** (toxicity ceiling) |
| Common / pan-essentiality flag (`isEssential`) | Open Targets | **F** (toxicity ceiling) |
| Safety liabilities (`safetyLiabilities`) | Open Targets | **P**, **F** (on-target safety) |
| Tractability buckets (small-mol / antibody) | Open Targets | **P**, **F** (undruggable class) |
| Mouse KO phenotypes (`mousePhenotypes`, IMPC via OT) | Open Targets | **E #13** |
| Paralogs / homologues (`homologues`) | Open Targets | **P**, **F** (paralog compensation) |
| Disease description / therapeutic areas / synonyms | Open Targets | **P** |

## ChEMBL

| Datapoint | Source | Use |
|---|---|---|
| Bioactivities IC50/Ki/Kd + pChEMBL (drug↔target) | ChEMBL | **E #16, #17**, **P** (potency) |
| Molecule modality / type (small-mol vs antibody) | ChEMBL | **E #15**, **P** (modality) |
| ATC class | ChEMBL | **P** (drug class) |
| Max phase / indications | ChEMBL | **P** (approval status) |
| Activity across *other* targets (selectivity) | ChEMBL | **F** (off-target, selectivity) |

## Expression & localization

| Datapoint | Source | Use |
|---|---|---|
| Bulk median TPM per tissue (54 tissues) | GTEx v8 | **E #7, #8, #11**, **P** (expression profile) |
| Single-cell nCPM per cell type | Human Protein Atlas | **E #7, #10**, **P** |
| Protein (IHC) detection level | Human Protein Atlas | **E #11**, **P** |
| Subcellular localization | UniProt / HPA | **E #15**, **P** |
| Protein function / description / domains | UniProt | **P**, **F** (druggability) |

## Genetics / constraint / genomics

| Datapoint | Source | Use |
|---|---|---|
| Constraint LOEUF / pLI | gnomAD | **E #6**, **P**, **F** |
| Dosage sensitivity (HI / TS score) | ClinGen dosage | **E #6** |
| cis-pQTL Mendelian-randomization (β, CI, p) | EpiGraphDB | **E #3** |
| Copy-number deep-deletion frequency (GISTIC) | cBioPortal | **E #9, #14** |
| Mutation recurrence / driver frequency | cBioPortal | **E #14**, **P** (disease genomics) |
| Hotspot / resistance mutations | cBioPortal | **E #18** |
| Monogenic link (ClinVar / OMIM) | OT / NCBI | **P**, **F** (no-monogenic-link) |

## Drug safety, trials, chemistry

| Datapoint | Source | Use |
|---|---|---|
| Black-box / boxed warning / adverse events | openFDA | **P**, **F** (safety withdrawal) |
| Trial status / "why stopped" | ClinicalTrials.gov | **P** (dev status), **F** (prior trial failure) |
| Physicochemical props (MW, logP, TPSA, HBD/HBA) | PubChem | **P**, **F** (delivery / BBB) |
| 3D structures / count | PDB (via UniProt) | **P**, **F** (druggable pocket) |

## Network / pathway / literature (mostly future + profiling)

| Datapoint | Source | Use |
|---|---|---|
| Pathway membership & target↔disease-gene overlap | Reactome / KEGG | **F** (pathway overlap) |
| Interaction-network proximity | STRING | **F** (network connectivity) |
| Literature counts / recent papers | PubMed | **P**, and the agent's digging tool |

## Design notes

1. **Open Targets pays for itself twice.** Several of its fields feed *both* a mechanism *and* the
   profile (mechanism-of-action → #1's direction *and* the drug→target edge; DepMap essentiality →
   #12 *and* a profile stat). So `data/opentargets.py` unlocks the most across all three uses — build
   it first.
2. **Gotcha:** do **not** use OT's `baselineExpression` for the expression mechanisms (#7/#8/#11) — it
   covers only ~17 tissues. Hit **GTEx** and **HPA** directly.
3. **Profiling-only datapoints are the cheap wins** — physchem, ATC, structures, function text: no
   mechanism logic, just fetch-and-display. Good first fetchers to warm up on.
