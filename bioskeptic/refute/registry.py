from dataclasses import dataclass

from bioskeptic.refute import (m01_direction, m02_colocalization, m03_cis_mr, m04_text_mining,
                               m06_haploinsufficiency, m07_expression, m10_single_cell, m13_mouse_ko)


# A registered mechanism = its engine module plus the metadata the agent needs to weigh its flags.
# `explanation`/`reliability`/`evaluation` are all handed to Claude in redteam.assess().
@dataclass
class Mechanism:
    module: object            # exposes NAME, check(claim)->Finding|None, available(claim)->bool
    explanation: str          # what the check does, in plain biology (no databases / jargon)
    reliability: str          # when it is trustworthy and its known mis-fire patterns
    evaluation: str           # how it did on the benchmark, in plain terms

    @property
    def name(self) -> str:
        return self.module.NAME

    def check(self, claim):
        return self.module.check(claim)

    def available(self, claim) -> bool:
        return self.module.available(claim)


# Every refuting mechanism, in doc order. Add a Mechanism here when a new one lands.
MECHANISMS = [
    Mechanism(
        m01_direction,
        explanation="Checks whether the drug pushes the target the direction that would help the "
            "disease. Nature runs the experiment for us: people carry small genetic differences that "
            "make their target a bit more or less active. If those with a naturally LESS active target "
            "are protected from the disease, a helpful drug should also LOWER it — a drug that RAISES "
            "it is going the wrong way.",
        reliability="Trustworthy when human genetics give a clean, one-way signal. It stays silent for "
            "cancers and for ion-channel targets, where the genetic direction can be misleading (both "
            "too much and too little activity cause disease).",
        evaluation="On the test set it stayed silent on almost everything — it needs strong "
            "human-genetics data, which is rare. Precise on the cases where it does fire.",
    ),
    Mechanism(
        m02_colocalization,
        explanation="A stretch of DNA linked to a disease usually holds several neighbouring genes, and "
            "only one is the real culprit. This checks whether the evidence actually singles out THIS "
            "target as the cause, or whether a neighbouring gene is the real driver and the target is "
            "just an innocent bystander sitting next to it.",
        reliability="Fires only when a confident neighbouring gene clearly out-ranks the target as the "
            "likely cause. Known mistake: two genes that are partner halves of the same protein machine "
            "— one half can look like it 'out-ranks' the other, but they are really the same drug target.",
        evaluation="Rare — on the test set it spoke on only a handful of cases, and about half of those "
            "fires were correct. Needs a specific kind of genetic data most pairs don't have.",
    ),
    Mechanism(
        m03_cis_mr,
        explanation="Being linked to a disease is not the same as causing it. Using natural genetic "
            "variation as a built-in experiment, we can estimate whether nudging the target's level "
            "actually moves the disease. If a well-powered test finds essentially no effect, the target "
            "is a bystander marker, not a cause — so a drug that changes it won't help.",
        reliability="A confident 'no effect' is strong evidence. Cautions: it tests lifelong GENTLE "
            "nudges to a blood-measured protein, not a strong drug or a target that acts inside cells or "
            "the brain; and the estimate can be thin.",
        evaluation="Applied to almost nothing on the test set — the data it relies on only covers about "
            "one in ten targets (blood proteins). Very reliable on the few cases where it does apply.",
    ),
    Mechanism(
        m04_text_mining,
        explanation="Looks at WHAT KIND of evidence ties the target to the disease. Sometimes the only "
            "reason they appear connected is that scientific papers happen to mention both together, with "
            "no real experimental or genetic finding behind it — a link that may be coincidence, not "
            "biology.",
        reliability="Very rarely wrong: it only fires when paper co-mention is the ONLY evidence, with "
            "nothing experimental or genetic behind it.",
        evaluation="On the test set it never wrongly flagged a real, working drug (no false alarms), but "
            "it only catches the most blatant coincidence-only links, so it stays silent on most cases.",
    ),
    Mechanism(
        m06_haploinsufficiency,
        explanation="Some genes are so sensitive to dose that losing just one of the two copies already "
            "causes disease. For such a gene, a drug that lowers or blocks it pushes the dose even "
            "further down — the harmful direction — so trying to treat a disease by reducing it is likely "
            "to backfire.",
        reliability="Fires only for genes expert-curated as dose-sensitive, and only when the drug LOWERS "
            "the target. It judges the target itself, not the specific disease, so it is a general safety "
            "flag rather than a disease-specific one.",
        evaluation="The test set can't really grade it, because it ignores the disease (a wrong disease "
            "looks the same to it). It fires only on the small curated set of dose-sensitive genes.",
    ),
    Mechanism(
        m07_expression,
        explanation="A drug can only act where its target is actually present. This checks whether the "
            "target is switched on in the tissue the disease affects. If the target isn't made there, "
            "there is nothing in that tissue for the drug to act on.",
        reliability="Two common false alarms: (1) the drug deliberately acts on a DIFFERENT organ than "
            "the diseased one (for example, a water pill acts on the kidney to treat the heart); (2) the "
            "target's working cells are a tiny fraction of the tissue (like specific neurons), so a bulk "
            "measurement reads near-zero even though the target is there.",
        evaluation="On the test set it catches about 41% of wrong claims and false-alarms on about 17% of "
            "real drugs — right roughly 3 out of 4 times it fires.",
    ),
    Mechanism(
        m10_single_cell,
        explanation="A tissue is a mixture of many cell types, and usually one specific cell type drives "
            "the disease. Even if the target seems present in the tissue as a whole, this checks whether "
            "it is present in that particular disease-driving cell. If not, the drug can't act where it "
            "actually matters.",
        reliability="High-recall but noisy — same trap as the tissue check: 'absent from the driving "
            "cell' can't tell apart a target that works through a different route or a rare cell from one "
            "that's truly irrelevant; and the single-cell data doesn't resolve every cell type well.",
        evaluation="Catches the most wrong claims on the test set (about 78%) and is the best at catching "
            "disproven genetic links — but it false-alarms on about 56% of real drugs, so it is right "
            "only about two-thirds of the times it fires.",
    ),
    Mechanism(
        m13_mouse_ko,
        explanation="If a target is truly needed for a disease, then completely removing that gene in an "
            "animal should cause a related problem. This checks whether deleting the gene in mice produces "
            "any effect relevant to the disease. If the mouse is essentially fine, the target may not be "
            "required after all.",
        reliability="Noisy because a mouse is not a human: the human disease may not show up in mice, a "
            "backup gene may cover for the missing one, or a drug may work differently than fully deleting "
            "the gene.",
        evaluation="On the test set it catches about 66% of wrong claims and false-alarms on about 35% of "
            "real drugs — right roughly 7 out of 10 times it fires.",
    ),
]

# name -> Mechanism, so assess() can look up a fired flag's metadata.
BY_NAME = {m.name: m for m in MECHANISMS}
