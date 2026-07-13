"""kg_audit — run BioSkeptic's refuting-mechanism panel over a knowledge graph's edges.

Give it a target–disease connection (or a whole dataframe of them) and it resolves the entities,
runs every refuting mechanism, and flags any edge a mechanism fires on — with the reason and source
links attached as a string (straight from the Finding objects).
"""
from kg_audit.audit import AuditResult, audit_dataframe, audit_pair
from kg_audit.edges import ensure_drkg, sample_target_disease

__all__ = ["AuditResult", "audit_pair", "audit_dataframe", "ensure_drkg", "sample_target_disease"]
