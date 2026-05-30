"""Assignment routing layer for evidence-to-concept scoring."""

from .poe_compat import (
    OldPOEDomainMapperAdapter,
    OldPOEDomainMapperSpec,
    OldPOEMapperError,
    discover_old_poe_domain_mappers,
    translate_old_poe_evidence_record,
)
from .prefilter import ShadowPrefilter, ShadowPrefilterAnalysis
from .router import (
    AssignmentBackend,
    AssignmentResult,
    AssignmentRouter,
    DeterministicMapperBackend,
    DirectStructuredAssignmentBackend,
    HybridPrefilterScorerBackend,
    SemanticLLMScorerBackend,
)

__all__ = [
    "AssignmentBackend",
    "AssignmentResult",
    "AssignmentRouter",
    "DeterministicMapperBackend",
    "DirectStructuredAssignmentBackend",
    "HybridPrefilterScorerBackend",
    "SemanticLLMScorerBackend",
    "OldPOEDomainMapperAdapter",
    "OldPOEDomainMapperSpec",
    "OldPOEMapperError",
    "ShadowPrefilter",
    "ShadowPrefilterAnalysis",
    "discover_old_poe_domain_mappers",
    "translate_old_poe_evidence_record",
]
