# BioSkeptic — data sources

Every data resource BioSkeptic can reach, grouped by what it is **keyed on**.

- **Entity** = which of drug / target / disease the resource informs.
- **Needs** = the identifier from our resolver *passports* the resource consumes to look something up.

The resolvers (`bioskeptic/resolver/`) turn any user phrasing into a passport of stable ids; the data
layer (`bioskeptic/data/`) spends those ids here to pull the actual values. Nothing below is called
until an entity is resolved.

| # | Resource | One-liner | Entity | Id it needs |
|---|---|---|---|---|
| 1 | **Open Targets** (GraphQL) | the aggregation hub: gene↔disease associations, genetic evidence, known drugs, expression, safety, mechanism | target · disease · drug | ensembl / efo / chembl_id |
| 2 | **ChEMBL** (REST) | measured bioactivity (IC50/Ki) + curated drug & target records | drug · target | chembl_id, uniprot |
| 3 | **UniChem** | cross-reference mapper between compound databases | drug | inchikey / source id |
| 4 | **UniProt** | protein sequence, function, subcellular location, structure xrefs | target | uniprot |
| 5 | **mygene.info** | gene-id cross-mapping | target | entrez / ensembl / symbol |
| 6 | **GTEx** (v2) | bulk RNA expression across ~50 human tissues | target | gencode |
| 7 | **Human Protein Atlas** | single-cell + protein (IHC) expression & localization | target | ensembl |
| 8 | **gnomAD** (GraphQL) | population genetic constraint (pLI / LOEUF) | target | ensembl / symbol |
| 9 | **IMPC** (SOLR) | mouse-knockout phenotypes | target | symbol (MGI) |
| 10 | **cBioPortal** | cancer somatic mutations / copy-number across tumors | target | symbol / entrez |
| 11 | **DepMap** (via OT or portal) | cancer cell-line dependency (essentiality) | target | ensembl / symbol |
| 12 | **ClinGen** (dosage TSV) | curated haploinsufficiency / triplosensitivity | target | symbol |
| 13 | **EpiGraphDB** | pQTL Mendelian-randomization (causal target→disease) | target · disease | symbol/uniprot + disease |
| 14 | **NCBI eutils / MeSH** | medical vocabulary + descriptor lookup | disease | mesh / name |
| 15 | **PubMed** (E-utils, gene2pubmed) | biomedical literature | target · drug · disease | entrez / mesh / names |
| 16 | **ClinicalTrials.gov** | registered clinical trials | drug · disease | names / synonyms (or NCT) |
| 17 | **openFDA** | FDA labels, approvals, adverse events / black-box | drug | unii / name |
| 18 | **PubChem** (PUG-REST) | chemical properties + bioassays | drug | pubchem_cid |
| 19 | **Guide to Pharmacology** | expert-curated ligand↔target action | drug · target | gtopdb / target |
| 20 | **DrugBank** | drug reference (id + link only; data licensed) | drug | drugbank_id |
| 21 | **PDB / RCSB** (via UniProt) | 3D protein structures | target | pdb / uniprot |

> OLS4 was probed but set aside. DRKG is the knowledge graph we *feed from* (the source of claims to
> refute), not a live API.

## The shape to notice

Sources cluster hard on the **target**: that is where the deep, structured science lives (expression,
constraint, dependency, structure, bioactivity). The **drug** has a medium tail (chemistry, labels,
trials, curated action). The **disease** is mostly Open Targets plus literature and trials.

That asymmetry drives the design: most refuting mechanisms interrogate the target and its edges to the
disease and drug, because that is where a specific, keyed, non-obvious datapoint is most likely to sit
and break an assumption.
