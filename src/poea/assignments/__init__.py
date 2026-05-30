"""Assignment routing layer for evidence-to-concept scoring."""

from .poe_compat import (
    OldPOEDomainMapperAdapter,
    OldPOEDomainMapperSpec,
    OldPOEMapperError,
    discover_old_poe_domain_mappers,
    translate_old_poe_evidence_record,
)
from .prefilter import ShadowPrefilter, ShadowPrefilterAnalysis
from .prefilter_eval import EvaluationResult, PrefilterEvaluator, ThresholdResult
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
    "EvaluationResult",
    "HybridPrefilterScorerBackend",
    "OldPOEDomainMapperAdapter",
    "OldPOEDomainMapperSpec",
    "OldPOEMapperError",
    "PrefilterEvaluator",
    "SemanticLLMScorerBackend",
    "ShadowPrefilter",
    "ShadowPrefilterAnalysis",
    "ThresholdResult",
    "discover_old_poe_domain_mappers",
    "translate_old_poe_evidence_record",
]
