from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

EventType = Literal[
    "intent",
    "action",
    "observation",
    "decision",
    "approval_requested",
    "approval_resolved",
    "error",
    "summary",
]
ActorType = Literal["agent", "system", "human"]
RiskLevel = Literal["low", "medium", "high"]
ApprovalStatus = Literal["not_required", "pending", "approved", "rejected"]
EvidenceKind = Literal["log", "url", "artifact", "diff"]


class Approval(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ApprovalStatus
    decision_id: str | None = None
    requested_by: str | None = None
    resolved_by: str | None = None
    resolved_at: datetime | None = None
    reason: str | None = None


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: EvidenceKind
    label: str
    ref: str


class EventMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow: str
    step: str


class EventPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    timestamp: datetime
    type: EventType
    actor: ActorType
    title: str = Field(min_length=1)
    details: str = Field(min_length=1)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    risk_level: RiskLevel | None = None
    requires_approval: bool = False
    approval: Approval
    evidence: list[Evidence] = Field(default_factory=list)
    meta: EventMeta | None = None

    @field_validator("timestamp")
    @classmethod
    def validate_and_normalize_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must include timezone information")
        return value.astimezone(timezone.utc)
