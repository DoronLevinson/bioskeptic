# BioSkeptic — refuting mechanisms

For a drug to treat a disease, a whole chain of biological assumptions must *all* hold: the target has
to be real and causal for the disease, present where and when the disease acts, actually needed by the
disease, and physically engageable by this particular drug. BioSkeptic does not try to prove a claim
works — it tries to **refute** it, by finding a single grounded datapoint that shows one required
assumption fails. If any one fails, the drug cannot work, no matter how good the rest of the story looks.

Each mechanism below is one such **grounded refutation rule**. A fired mechanism is a **suggestive,
cited flag — not a verdict.** It reports a real datapoint that *usually* means the drug won't work, but
not always; every mechanism has known blind spots where it flags a workable drug, learned from running
it against the benchmark. The agent sees each flag *together with these caveats* and weighs them for the
user — that is what makes BioSkeptic a red team rather than an oracle.

For every mechanism we give:

- **What it checks** — the assumption it guards, and how a fact can break it.
- **What we need to know** — the biological question we must answer, in plain terms.
- **Source** — literature establishing why the assumption is a genuine requirement.
- **Reliability** *(where benchmarked)* — when the flag is trustworthy, and its known mis-fire patterns.

---

### 1. Genetic direction-of-effect

**What it checks.** A drug only helps if it pushes the target the direction human genetics say is
protective. If people who naturally *lose* the target's function are protected from the disease, then a
drug that *increases* the target's activity is working the wrong way.

**What we need to know.** Whether raising or lowering the target's function is the protective direction
in humans — and which way this drug moves it.

**Source.** Open Targets direction-of-effect (Nat Genet 2024, PMID 39701122); Plenge et al. 2013
(PMID 23868113); Nelson et al. 2015, genetic support for drug indications (PMID 26121088).

**Reliability.** Trustworthy only when human genetics give a clean, one-directional signal for a
*monotonic* target (more/less function → consistently more/less disease). It deliberately abstains on
two classes where germline direction contradicts the therapeutic one: **oncology** targets (germline
risk ≠ the somatic dependency the drug exploits) and **ion channels** (both too much and too little are
pathological, so a single genetic direction misleads). Outside those, a fired flag is high-confidence.

### 2. Causal-gene / colocalization null

**What it checks.** A genetic signal sits at a stretch of DNA, not on a single gene. The signal near the
target may actually be driven by a *neighbouring* gene, with the target an innocent passenger.

**What we need to know.** Whether the genetic association at that location statistically points to *this*
target as the causal gene, or to a nearby one.

**Source.** Open Targets Genetics L2G (Mountjoy et al. Nat Genet 2021, PMID 34711957); colocalization
(Giambartolomei et al. PLoS Genet 2014, PMID 24830394); locus resolution (Musunuru et al. Nature 2010,
PMID 20686566).

**Reliability.** Rare-data and precision-oriented — it can only speak when the pair has a GWAS
credible-set locus, so it abstains on ~90% of pairs and on almost all *Mendelian* gene–disease pairs
(which have no GWAS loci). When it fires it catches a genuine passenger gene — a target consistently
outranked as the causal gene (L2G) by a *confident* neighbour (guarded to fire only when the neighbour's
L2G ≥ 0.5, so weak loci don't trigger it). Known mis-fire: **partner subunits of the same protein
complex** — a target's own partner subunit can be the top L2G gene (e.g. the two soluble-guanylate-cyclase
subunits GUCY1A1/GUCY1B1), which reads as "outranked" but is really the same drug target.

### 3. Causal null (Mendelian randomization)

**What it checks.** An association between target and disease is not the same as causation. Using natural
genetic variation that changes the target's protein level as a built-in experiment, a well-powered test
can come back convincingly null — associated, but not causal.

**What we need to know.** Whether a well-powered natural-experiment test of the target's level against
the disease shows a real causal effect, or a confident null.

**Source.** Zheng et al. Nat Genet 2020 (PMID 32895551); cis-MR for target validation, Schmidt et al.
Nat Commun 2020 (PMID 32895371).

**Reliability.** Decisive where it applies (GDF15/MPO/CST3 biomarker→coronary-heart-disease nulls fire;
LPA and IL6R causal effects stay clean) but **very narrow**: the cis-pQTL MR atlas covers only ~1000
plasma/secreted proteins, so most drug targets (GPCRs, ion channels, intracellular enzymes) aren't in it
— on a general drug-target benchmark it abstains ~100% of the time (only ~1 in 10 targets is even in the
atlas). A fired flag is strong: it requires a *well-powered* null (p ≥ 0.05 with the whole 95% CI within
±0.10 log-OR/SD); wide-CI "no power" nulls are abstained on, never fired. Escape hatches: MR tests
lifelong *modest plasma-level* modulation, not maximal pharmacology or intracellular/CNS action; most
rows are single-cis-SNP Wald ratios without a pleiotropy check; the disease→atlas-outcome match is
token-based and could pick a related sub-trait.

### 4. Text-mining-only association

**What it checks.** The target–disease link the program is built on may reflect no real biology at all —
it can exist purely because papers happen to *co-mention* the two, with no direct experimental or
genetic evidence behind it.

**What we need to know.** Whether the association rests on any direct biological evidence, or only on
literature co-occurrence.

**Source.** Open Targets association scoring (Ochoa et al. 2021, PMID 33196847); Europe PMC text-mining
(Kafkas et al. 2017).

**Reliability.** Very high precision, deliberately narrow. It fires only when the association's *sole*
evidence type is literature co-mention — 0 false alarms on 100 approved drugs and 0 on real (even
ultimately-refuted) gene–disease associations, which always carry some genetic/clinical/expression
evidence. So it catches *only* the pure co-mention edge and stays silent when any real biology exists
(refuted genetic support is the job of #2/#3, not this). It also abstains when there is no association
at all (that is a separate "no association" check). Caveat: on approved drugs its silence is partly
circular — the "clinical" evidence type comes from the same known-drug data that defines "approved" —
so validate its precision on drug-independent pairs.

### 5. Genetic effect-size ceiling

**What it checks.** A statistically real genetic association can still be therapeutically useless. A
locus can be genome-wide significant yet move the disease trait so slightly that even completely
modulating the target could not deliver a meaningful clinical effect.

**What we need to know.** The *magnitude* of the target's genetic effect on the disease — not just
whether it is significant.

**Source.** Open Targets Genetics / gene-burden evidence (Ochoa et al. 2021, PMID 33196847; Backman et
al. 2021, PMID 34662886).

### 6. Haploinsufficiency / dosage mismatch

**What it checks.** Reducing a target's activity is only safe when the gene tolerates it. If the gene is
dosage-sensitive — losing a single copy already causes disease — then an inhibitor, antagonist, or
degrader pushes dosage in the harmful direction.

**What we need to know.** Whether the target is dosage-sensitive (does halving its activity already
cause disease), and whether the drug lowers its activity.

**Source.** gnomAD constraint (Karczewski et al. 2020, PMID 32461654); ClinGen dosage sensitivity
(Riggs et al. 2012, PMID 22995991; Rehm et al. 2015, PMID 26014595).

**Reliability.** Disease-independent (it judges target + direction, not the disease), so a benchmark
whose negatives differ only in the disease **cannot discriminate it** — its precision sits at 0.50 by
construction, exactly like #1. The fire condition is precise, though: it fires only when a *lowering*
drug targets a **ClinGen-curated haploinsufficient gene (HI=3, ~417 genes)** — not merely a
loss-of-function-constrained one (gnomAD pLI over-fired on safely-druggable constrained targets like
EGFR; ClinGen HI=3 fixes that). Its real value is the target-intrinsic flag ("you are lowering a
dosage-sensitive gene") and being the second direction-sensitive mechanism (with #1) for the deferred
direction cohort.

### 7. Absent from tissue and driver cell

**What it checks.** A drug needs something to act on. If the target is undetectable both in the affected
tissue overall and in the specific cell type that drives the disease, there is nothing there to engage.

**What we need to know.** Whether the target is expressed in the affected tissue and, specifically, in
the cell type that drives the disease.

**Source.** GTEx Consortium, Science 2020 (PMID 32913098); Human Protein Atlas single-cell (Karlsson et
al. Sci Adv 2021, PMID 34321199).

**Reliability.** A fired flag means the target's bulk RNA is absent from the disease's tissue — a real
observation, but not always disqualifying. Two common false alarms: (1) **the drug acts on a different
organ than the disease** (e.g. a diuretic acts on the kidney to treat heart or liver disease), so the
target's absence from the disease's own organ is irrelevant; (2) **the target's functional cells are a
tiny fraction of the tissue** (neuronal receptors/transporters, inducible enzymes), so bulk RNA reads
near-zero while the target is really there. The flag names where the target *is* expressed — weigh that
against the drug's actual site of action. A **single-cell rescue is built**: the flag fires only if the
target is also absent from the disease's *driver cell type* (HPA single-cell), which tames case 2
(rare-cell targets). Case 1 (drug-acts-elsewhere) is a site-of-action issue no expression data can fix,
so it remains the mechanism's precision ceiling (~67% on the benchmark).

**What it checks.** The target must be present when the patient is actually treated. Some genes are
expressed only during development and switched off in adult tissue — a drug given to an adult finds
nothing to act on.

**What we need to know.** Whether the target is expressed in the adult, disease-relevant window, or only
during development.

**Source.** GTEx Consortium, Science 2020 (PMID 32913098); Bgee (Bastian et al. NAR 2021, PMID 33037820);
not-expressed convention (Wagner et al. 2012, PMID 22872506).

### 9. Deleted in the disease

**What it checks.** An inhibitor needs its target to be present in the tumour. If the target gene is
deeply (homozygously) deleted in the disease's tumours, the protein is simply gone — there is nothing
left to inhibit.

**What we need to know.** Whether the target gene is deleted or lost in the disease's tumours.

**Source.** cBioPortal (Cerami et al. 2012, PMID 22588877; Gao et al. 2013, PMID 23550210); TCGA
PanCancer Atlas; GISTIC2 copy-number calls (Mermel et al. 2011, PMID 21527027).

### 10. Absent from the disease-driver cell type

**What it checks.** A target can look expressed in a bulk tissue yet be entirely absent from the specific
cell type that drives the disease — the bulk signal is carried by *other* cells in the tissue.

**What we need to know.** Whether the target is expressed in the disease-driving cell type specifically,
not just somewhere in the tissue.

**Source.** GTEx Consortium, Science 2020 (PMID 32913098); Human Protein Atlas single-cell (Karlsson et
al. Sci Adv 2021, PMID 34321199).

**Reliability.** High-recall, noisy — the high-recall counterpart to #7 on the expression axis. On the
benchmark it catches **78/100 disease-swaps and 30/50 ClinGen refuted** (the most ClinGen of any
mechanism, recall 0.76) but false-alarms on **56% of approved drugs** (precision 0.66). #7 requires
absence in bulk *and* the driver cell (precise, low-recall); this fires on driver-cell absence alone
(broad, noisy). Same irreducible expression confound as #7 — "absent from the driver cell" can't tell a
target that works via a rare cell or a different route from one that's genuinely irrelevant — plus HPA's
single-cell atlas doesn't resolve every driver cell. Use it as a high-recall suggestive flag, weighed
against #7 and where the target is actually expressed.

### 11. Protein absent despite mRNA

**What it checks.** A drug engages the target *protein*, not its transcript. mRNA and protein are only
loosely coupled, so a transcript can be present while the protein itself is undetectable — leaving the
drug nothing to bind.

**What we need to know.** Whether the target protein (not just its mRNA) is actually detectable in the
relevant tissue.

**Source.** Human Protein Atlas (Uhlén et al. Science 2015, PMID 25613900); GTEx Consortium 2020
(PMID 32913098); mRNA–protein discordance (Liu et al. Cell 2016, PMID 27104977).

### 12. Not a dependency in the lineage

**What it checks.** The premise for an oncology target is that the cancer *needs* it. Genome-wide
knockout screens across cancer cell lines can show the gene is not a dependency in the relevant lineage:
cells lose it and keep growing.

**What we need to know.** Whether knocking the target out actually impairs cancer cells of the relevant
lineage.

**Source.** DepMap / Chronos gene effect (Dempster et al. 2021, PMID 34700118); Cancer Dependency Map
(Tsherniak et al. 2017, PMID 28753430).

### 13. Model-organism knockout is normal

**What it checks.** If the target were causally required, removing it should produce a phenotype. When
the whole-animal (mouse) knockout of the target is viable and phenotypically normal in the
disease-relevant system, target loss does not produce the expected effect.

**What we need to know.** Whether deleting the target in a whole animal produces a disease-relevant
phenotype, or nothing.

**Source.** International Mouse Phenotyping Consortium (Dickinson et al. 2016, PMID 27626380; Groza et
al. 2023, PMID 36305833).

**Reliability.** High-recall, moderately precise, and broadly applicable (data on most genes). On the
benchmark it catches **73/100 disease-swaps and 21/50 ClinGen refuted** — the first mechanism to catch
the independent ClinGen negatives — at ~71% precision, but it **false-alarms on ~38% of approved drugs**,
because mouse-knockout phenotype is a noisy proxy for human drug efficacy. The dominant, **irreducible**
mis-fire is **species difference** — a viable knockout whose adult phenotype simply doesn't match the
human disease (or a readout IMPC's fixed panel doesn't score); also **paralog redundancy** (a close
paralog compensates, so the KO looks normal yet a drug works) and the drug's mechanism differing from a
full genetic knockout. One mis-fire class *is* fixed by a guardrail: a **non-viable knockout that was
never phenotyped as an adult** (a lethality label with ≤6 total phenotypes) — firing "not required" on
an embryonic-lethal essential gene is unsound, so those abstain. (Genes with a lethality label but many
adult phenotypes are viable alleles with real data and are kept.) A fired flag means "deleting the gene
in mice shows nothing disease-relevant" — a real, citable concern, weighed against these escapes.
(Disease→phenotype relevance is judged by the LLM, so its eval is the slowest — one call per pair.)

### 14. No recurrent driver alteration

**What it checks.** The premise is that the target is an oncogenic *driver*, so inhibiting it switches
the cancer off. If, in the relevant cancer, the gene is essentially never recurrently mutated, amplified,
or depended-on, it is an innocent bystander — not a driver.

**What we need to know.** Whether the target is a recurrent driver of the disease (mutated / amplified /
depended-on), or merely present.

**Source.** cBioPortal (Cerami et al. 2012, PMID 22588877; Gao et al. 2013, PMID 23550210); GISTIC2
(Mermel et al. 2011, PMID 21527027); DepMap (Dempster et al. 2021, PMID 34700118; Tsherniak et al. 2017,
PMID 28753430).

### 15. Localization vs modality mismatch

**What it checks.** A drug that binds its target can only treat the disease if it can physically reach
it. An antibody or large protein biologic cannot cross the cell membrane, so it cannot engage a target
that lives exclusively inside the cell.

**What we need to know.** Where the target sits (cell surface / secreted vs strictly intracellular), and
whether the drug's modality can reach that compartment.

**Source.** UniProt and Human Protein Atlas subcellular localization; antibody membrane-impermeability
is standard cell biology (Alberts et al., *Molecular Biology of the Cell*).

### 16. Potency gap

**What it checks.** The drug must engage its target at a concentration a safe dose can reach. If the
drug's best measured potency is weak — far above the exposure a tolerable dose achieves — it never
meaningfully engages the target in a patient.

**What we need to know.** The drug's best measured potency against the target, versus the exposure a
tolerable dose can realistically reach.

**Source.** ChEMBL bioactivity (Zdrazil et al. 2024, PMID 37933841; pChEMBL definition); standard
medicinal-chemistry potency practice.

### 17. No measured drug↔target activity

**What it checks.** A knowledge-graph edge "drug D acts on target T" should reflect a real
pharmacological interaction. It doesn't if the drug has been assayed against many proteins but shows
*zero* measured activity against the claimed target.

**What we need to know.** Whether there is any measured binding or activity linking this drug to this
target at all.

**Source.** ChEMBL bioactivity (Zdrazil et al. 2024, PMID 37933841; Gaulton et al. 2017, PMID 27899562).

### 18. Resistance-mutation / wrong-form mismatch

**What it checks.** The drug must engage the *form* of the target that actually drives the disease. A
form-selective drug fails if it engages a version of the target that is not the disease-driving one — for
example, binding wild-type protein when the driver is a resistant mutant.

**What we need to know.** Which molecular form of the target drives this disease, and whether the drug
engages that form.

**Source.** cBioPortal (Cerami et al. 2012, PMID 22588877; Gao et al. 2013, PMID 23550210); hotspot
recurrence (Chang et al. 2016, PMID 26619011).
