from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from ..concepts.scorer import ConceptAssignment, ScoredRecord
from ..evidence.schemas import EvidenceUnit
from ..registry.schemas import ConceptEntry


class OldPOEMapperError(RuntimeError):
    """Raised when a structured record cannot be mapped through old POE."""


@dataclass(frozen=True)
class OldPOEDomainMapperSpec:
    domain_id: str
    package: str
    pipeline_class: str
    snapshot_class: str | None = None


_OLD_POE_DOMAIN_SPECS: tuple[OldPOEDomainMapperSpec, ...] = (
    OldPOEDomainMapperSpec("macro-regime-v1", "macro_regime_v1", "MacroRegimePipeline", "MacroRegimeSnapshot"),
    OldPOEDomainMapperSpec("natural-gas-v1", "natural_gas_v1", "NaturalGasPipeline", None),
    OldPOEDomainMapperSpec("ai-regime-v1", "ai_regime_v1", "AIRegimePipeline", "AIRegimeSnapshot"),
    OldPOEDomainMapperSpec("sovereign-debt-v1", "sovereign_debt_v1", "SovereignDebtPipeline", "SovereignDebtSnapshot"),
    OldPOEDomainMapperSpec("credit-cycle-v1", "credit_cycle_v1", "CreditCyclePipeline", "CreditCycleSnapshot"),
    OldPOEDomainMapperSpec("energy-regime-v1", "energy_regime_v1", "EnergyRegimePipeline", "EnergyRegimeSnapshot"),
    OldPOEDomainMapperSpec("labor-market-v1", "labor_market_v1", "LaborMarketPipeline", "LaborMarketSnapshot"),
    OldPOEDomainMapperSpec("crypto-regime-v1", "crypto_regime_v1", "CryptoRegimePipeline", "CryptoRegimeSnapshot"),
    OldPOEDomainMapperSpec("geopolitics-v1", "geopolitics_v1", "GeopoliticsPipeline", "GeopoliticsSnapshot"),
    OldPOEDomainMapperSpec("sf-urban-v1", "sf_urban_v1", "SFUrbanPipeline", "SFUrbanSnapshot"),
)


class OldPOEDomainMapperAdapter:
    """
    Adapter for old POE deterministic ingestion mappers.

    Old POE domains do not expose one uniform ``evidence_mapper`` object.
    Their deterministic mapping logic lives in pure
    ``*Pipeline.build_evidence_record`` methods and canonical variable
    definitions live in ``domain.get_variables``. This adapter calls those
    existing methods and translates old POE ``EvidenceRecord`` objects into
    POE-A ``ScoredRecord`` artifacts without copying mapper logic.
    """

    def __init__(self, spec: OldPOEDomainMapperSpec) -> None:
        self.spec = spec

    def __call__(
        self,
        evidence: EvidenceUnit,
        concepts: Sequence[ConceptEntry],
    ) -> ScoredRecord:
        record = self._build_old_poe_record(evidence)
        return translate_old_poe_evidence_record(
            record=record,
            concepts=concepts,
            evidence_id=evidence.evidence_id,
            variables_by_name=self._variables_by_name(),
        )

    def _build_old_poe_record(self, evidence: EvidenceUnit) -> Any:
        metadata = evidence.metadata
        direct_record = (
            metadata.get("old_poe_evidence_record")
            or metadata.get("poe_evidence_record")
        )
        if direct_record is not None:
            return _coerce_old_evidence_record(direct_record)

        pipeline_cls = self._pipeline_class()
        mapper_args = metadata.get("old_poe_mapper_args") or metadata.get("poe_mapper_args")
        if isinstance(mapper_args, list):
            return pipeline_cls.build_evidence_record(
                *[self._coerce_mapper_arg(arg) for arg in mapper_args]
            )

        snapshot = metadata.get("old_poe_snapshot") or metadata.get("poe_snapshot")
        if snapshot is not None:
            if self.spec.snapshot_class is None:
                raise OldPOEMapperError(
                    f"{self.spec.domain_id} requires old_poe_mapper_args; no single snapshot class is registered"
                )
            return pipeline_cls.build_evidence_record(self._coerce_snapshot(snapshot))

        raise OldPOEMapperError(
            f"No old POE evidence record, snapshot, or mapper args supplied for {self.spec.domain_id}"
        )

    def _pipeline_module(self) -> Any:
        return importlib.import_module(
            f"src.domains.{self.spec.package}.ingestion.pipeline"
        )

    def _domain_module(self) -> Any:
        return importlib.import_module(f"src.domains.{self.spec.package}.domain")

    def _pipeline_class(self) -> Any:
        return getattr(self._pipeline_module(), self.spec.pipeline_class)

    def _snapshot_class(self) -> Any:
        if self.spec.snapshot_class is None:
            raise OldPOEMapperError(f"No snapshot class registered for {self.spec.domain_id}")
        return getattr(self._pipeline_module(), self.spec.snapshot_class)

    def _variables_by_name(self) -> dict[str, Any]:
        variables = self._domain_module().get_variables()
        return dict(variables)

    def _coerce_snapshot(self, snapshot: Any) -> Any:
        if not isinstance(snapshot, Mapping):
            return snapshot
        return self._snapshot_class()(**dict(snapshot))

    def _coerce_mapper_arg(self, arg: Any) -> Any:
        if not isinstance(arg, Mapping):
            return arg
        class_name = arg.get("class") or arg.get("type")
        values = arg.get("values", arg.get("data", arg))
        if not class_name:
            return values
        cls = getattr(self._pipeline_module(), str(class_name), None)
        if cls is None:
            for module_name in (
                f"src.domains.{self.spec.package}.ingestion.noaa_client",
                f"src.domains.{self.spec.package}.ingestion.eia_client",
                f"src.domains.{self.spec.package}.ingestion.fred_client",
                f"src.domains.{self.spec.package}.ingestion.yfinance_client",
                f"src.domains.{self.spec.package}.ingestion.gdelt_client",
                f"src.domains.{self.spec.package}.ingestion.sfgov_client",
            ):
                try:
                    module = importlib.import_module(module_name)
                except ImportError:
                    continue
                cls = getattr(module, str(class_name), None)
                if cls is not None:
                    break
        if cls is None:
            raise OldPOEMapperError(f"Could not resolve old POE mapper arg class {class_name!r}")
        return cls(**dict(values))


def discover_old_poe_domain_mappers() -> dict[str, OldPOEDomainMapperAdapter]:
    """Return lazy adapters for the structured domains shipped by old POE."""
    mappers: dict[str, OldPOEDomainMapperAdapter] = {}
    for spec in _OLD_POE_DOMAIN_SPECS:
        adapter = OldPOEDomainMapperAdapter(spec)
        aliases = {
            spec.domain_id,
            spec.domain_id.replace("-", "_"),
            spec.package,
        }
        for alias in aliases:
            mappers[alias] = adapter
    return mappers


def translate_old_poe_evidence_record(
    *,
    record: Any,
    concepts: Sequence[ConceptEntry],
    evidence_id: str,
    variables_by_name: Mapping[str, Any],
) -> ScoredRecord:
    variables_by_id = {str(v.variable_id): v for v in variables_by_name.values()}
    concept_by_id = {c.concept_id: c for c in concepts}
    concept_by_name = {c.name: c for c in concepts}
    old_assignments = getattr(record, "observed_assignments", [])

    assignments: list[ConceptAssignment] = []
    matched_names: set[str] = set()
    matched_ids: set[str] = set()

    for old_assignment in old_assignments:
        old_variable_id = str(getattr(old_assignment, "variable_id"))
        old_variable = variables_by_id.get(old_variable_id)
        variable_name = getattr(old_variable, "name", old_variable_id)
        concept = concept_by_id.get(old_variable_id) or concept_by_name.get(variable_name)
        if concept is None:
            assignments.append(_assignment_from_old(old_assignment, old_variable_id, variable_name))
            continue
        assignments.append(_assignment_from_old(old_assignment, concept.concept_id, concept.name))
        matched_names.add(concept.name)
        matched_ids.add(concept.concept_id)

    for concept in concepts:
        if concept.name not in matched_names and concept.concept_id not in matched_ids:
            assignments.append(
                ConceptAssignment(
                    concept_id=concept.concept_id,
                    variable_name=concept.name,
                    assigned_value=None,
                    confidence=0.0,
                    missingness="MISSING",
                )
            )

    return ScoredRecord(evidence_id=evidence_id, assignments=assignments)


def _assignment_from_old(
    old_assignment: Any,
    concept_id: str,
    variable_name: str,
) -> ConceptAssignment:
    missingness = str(
        getattr(getattr(old_assignment, "missingness", "OBSERVED"), "value", getattr(old_assignment, "missingness", "OBSERVED"))
    )
    if missingness not in {"OBSERVED", "SOFT_OBSERVED", "MISSING"}:
        missingness = "MISSING"
    assigned_value = getattr(old_assignment, "observed_value", None)
    if assigned_value is not True and assigned_value is not False:
        assigned_value = None
        missingness = "MISSING"
    return ConceptAssignment(
        concept_id=concept_id,
        variable_name=variable_name,
        assigned_value=assigned_value,
        confidence=float(getattr(old_assignment, "confidence", 1.0) or 0.0),
        missingness=missingness,
    )


def _coerce_old_evidence_record(record: Any) -> Any:
    if not isinstance(record, Mapping):
        return record
    try:
        from src.engine.schemas import EvidenceRecord
    except ImportError as exc:
        raise OldPOEMapperError(
            "Old POE is not importable; install sibling probabilistic_ontology_engine"
        ) from exc
    return EvidenceRecord.model_validate(dict(record))
