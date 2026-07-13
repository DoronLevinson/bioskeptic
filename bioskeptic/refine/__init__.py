"""bioskeptic.refine — data-refinement library: run BioSkeptic's refuting-mechanism panel over the
target–disease relations in a dataset or knowledge graph to flag the weakly-grounded ones.

Give it a target–disease connection (or a whole dataframe of them) and it resolves the entities,
runs every refuting mechanism, and flags any relation a mechanism fires on — with the reason and
source links attached (as a string, or structured, straight from the Finding objects).
"""
from bioskeptic.refine.audit import AuditResult, audit_dataframe, audit_pair
from bioskeptic.refine.edges import ensure_drkg, sample_target_disease

__all__ = ["AuditResult", "audit_pair", "audit_dataframe", "ensure_drkg", "sample_target_disease"]
