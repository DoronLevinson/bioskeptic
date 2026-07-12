from bioskeptic.refute import (m01_direction, m02_colocalization, m03_cis_mr, m04_text_mining,
                               m06_haploinsufficiency, m07_expression, m10_single_cell, m13_mouse_ko)

# Every refuting mechanism, in doc order. Each module exposes:
#   NAME              — the mechanism's id
#   check(claim)      — the rule: returns a Finding (flagged True/False) or None (abstain)
#   available(claim)  — cheap "does the source hold this datum?" test (for the benchmark precheck)
# Add a module here when a new mechanism lands (or auto-discover later).
MECHANISMS = [m01_direction, m02_colocalization, m03_cis_mr, m04_text_mining, m06_haploinsufficiency,
              m07_expression, m10_single_cell, m13_mouse_ko]
