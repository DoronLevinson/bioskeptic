from bioskeptic.data.llm import ask_claude
from bioskeptic.resolver.disease import Disease


# Which tissue(s) a disease acts in, chosen from a fixed vocabulary — Claude does the semantic match a
# database can't (e.g. "hepatocellular carcinoma" -> "Liver"). Returns [] for systemic / no clear tissue.
def affected_tissues(disease: Disease, tissue_options: list[str]) -> list[str]:
    name = disease.name if disease else None
    if not name or not tissue_options:
        return []
    prompt = (f'Disease: "{name}".\n'
              f"Fixed list of tissue names:\n{tissue_options}\n\n"
              "Which of these tissues does this disease primarily act on or occur in? "
              "Return ONLY the exact matching tissue name(s) from the list, comma-separated. "
              "If the disease is systemic or none of the listed tissues clearly fit, return NONE.")
    ans = ask_claude(prompt)
    if not ans or "NONE" in ans.upper():
        return []
    options = set(tissue_options)
    return [t.strip() for t in ans.split(",") if t.strip() in options]


# Is the target present in the cell type that drives the disease? Claude judges from the single-cell
# nCPM table (handles both the fuzzy cell-type match and "which cell drives this disease"). True /
# False / None(unknown). Used by #7's single-cell rescue: present -> the target is reachable after all.
def expressed_in_driver_cell(disease: Disease, cell_expr: dict) -> bool | None:
    name = disease.name if disease else None
    present = {c: v for c, v in (cell_expr or {}).items() if v >= 1.0}
    if not name:
        return None
    if not present:
        return False                       # detected in no cell type at nCPM >= 1
    prompt = (f'Disease: "{name}".\n'
              f"A target gene is expressed (nCPM) in these cell types:\n{present}\n\n"
              "Is this gene expressed in the cell type(s) that DRIVE this disease — i.e. is any listed "
              "cell type the disease's driver cell? Answer with ONE word: PRESENT, ABSENT, or UNKNOWN.")
    ans = (ask_claude(prompt) or "").upper()
    if "PRESENT" in ans:
        return True
    if "ABSENT" in ans:
        return False
    return None


# Does the mouse knockout produce any phenotype relevant to the disease? Claude judges from the phenotype
# list (fuzzy match a phenotype to the disease's organ system / process). True / False / None(unknown).
def phenotype_relevant_to_disease(disease: Disease, phenotypes: list) -> bool | None:
    name = disease.name if disease else None
    if not name or not phenotypes:
        return None
    prompt = (f'Disease: "{name}".\n'
              f"A gene's mouse-knockout phenotypes:\n{phenotypes[:80]}\n\n"
              "Does the mouse knockout show a phenotype that DIRECTLY matches this disease's own organ "
              "system or core pathological process? Be strict: a specific, on-point phenotype counts; a "
              "vague, whole-body, or tangential phenotype does NOT. Answer ONE word: RELEVANT (a direct, "
              "on-point phenotype exists) or NONE (only unrelated or tangential phenotypes).")
    ans = (ask_claude(prompt) or "").upper()
    if "NONE" in ans:
        return False
    if "RELEVANT" in ans:
        return True
    return None
