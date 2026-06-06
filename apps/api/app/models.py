from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class FilingStatus(StrEnum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    NEEDS_YOU = "needs_you"
    READY_FOR_REVIEW = "ready_for_review"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    ARCHIVED = "archived"


class RequestType(StrEnum):
    DATA_REQUEST = "data_request"
    HUMAN_WALL_HANDOFF = "human_wall_handoff"
    CONFIRMATION = "confirmation"
    WARNING = "warning"


class SourceType(StrEnum):
    BUSINESS_PROFILE = "business_profile"
    FILING_CONTEXT = "filing_context"
    UPLOADED_DOCUMENT = "uploaded_document"
    OFFICIAL_SOURCE = "official_source"
    AGENT_INFERENCE = "agent_inference"


class Sensitivity(StrEnum):
    PUBLIC = "public"
    BUSINESS = "business"
    PERSONAL = "personal"
    CONFIDENTIAL = "confidential"


class FieldStatus(StrEnum):
    FILLED = "filled"
    LEFT_BLANK = "left_blank"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"
    USER_REQUIRED = "user_required"
    NOT_APPLICABLE = "not_applicable"


class FilingDescribeRequest(BaseModel):
    description: str = Field(min_length=8, max_length=1600)
    company_context: str | None = Field(default=None, max_length=1600)


class CompanyProfile(BaseModel):
    legal_name: str | None = None
    trading_name: str | None = None
    registration_id: str | None = None
    address: str | None = None
    industry_summary: str | None = None
    primary_contact_email: str | None = None
    primary_contact_phone: str | None = None
    filing_notes: str | None = None


class Person(BaseModel):
    full_name: str
    role: str
    email: str | None = None
    sensitivity: Sensitivity = Sensitivity.PERSONAL


class OfficialSource(BaseModel):
    title: str
    url: str
    summary: str


class RegulatoryRecommendation(BaseModel):
    filing_name: str
    jurisdiction: str
    agency: str
    reason: str
    prerequisites: list[str] = Field(default_factory=list)
    fee_expectation: str | None = None
    deadline: str | None = None
    warnings: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    sources: list[OfficialSource] = Field(default_factory=list)


class ChecklistItem(BaseModel):
    label: str
    status: FieldStatus
    reason: str


class FieldConfidenceRecord(BaseModel):
    field_key: str | None = None
    selector: str | None = None
    input_kind: str | None = None
    portal_section: str
    field_label: str
    proposed_value: str | None = None
    source_type: SourceType
    confidence: float = Field(ge=0, le=1)
    sensitivity: Sensitivity
    status: FieldStatus
    reason: str


class ExtractedFact(BaseModel):
    label: str
    value: str | None = None
    source_type: SourceType
    confidence: float = Field(ge=0, le=1)
    sensitivity: Sensitivity
    evidence_note: str | None = None


class DocumentExtractRequest(BaseModel):
    file_name: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=8, max_length=12000)


class DocumentExtractResponse(BaseModel):
    document_id: UUID
    file_name: str
    status: str
    facts: list[ExtractedFact]
    activity: ActivityEvent


class ComputerUseRunRequest(BaseModel):
    target_url: str = Field(min_length=8, max_length=2048)
    objective: str | None = Field(default=None, max_length=1000)
    max_steps: int = Field(default=3, ge=1, le=8)
    allow_user_handoff: bool = False
    handoff_timeout_seconds: int = Field(default=180, ge=30, le=600)
    field_answers: dict[str, str] = Field(default_factory=dict)


class ComputerUseStep(BaseModel):
    step: int
    action_type: str
    status: str
    summary: str
    blocked_reason: str | None = None
    current_url: str | None = None


class ComputerUseRunResponse(BaseModel):
    status: str
    mode: str
    target_url: str
    current_url: str | None = None
    recommendation: RegulatoryRecommendation | None = None
    checklist: list[ChecklistItem] = Field(default_factory=list)
    fields: list[FieldConfidenceRecord] = Field(default_factory=list)
    user_handoff_used: bool = False
    user_handoff_timed_out: bool = False
    steps: list[ComputerUseStep] = Field(default_factory=list)
    requests: list[AgentRequestDraft] = Field(default_factory=list)
    activity: list[ActivityEvent] = Field(default_factory=list)
    blocked_reason: str | None = None
    agents: list[str] = Field(default_factory=list)


class ComputerUseAccessSessionResponse(BaseModel):
    session_id: str
    status: str
    target_url: str
    current_url: str | None = None
    handoff_reason: str | None = None
    prompt: str


class AgentRequestDraft(BaseModel):
    request_type: RequestType
    title: str
    prompt: str
    why_needed: str
    field_key: str | None = None
    proposed_answer: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    source_type: SourceType | None = None
    portal_url: str | None = None


class ActivityEvent(BaseModel):
    event_type: str
    summary: str
    detail: str | None = None


class AgentResearchResult(BaseModel):
    recommendation: RegulatoryRecommendation
    checklist: list[ChecklistItem]
    fields: list[FieldConfidenceRecord]
    requests: list[AgentRequestDraft]
    activity: list[ActivityEvent]
    next_status: FilingStatus


class FilingCard(BaseModel):
    id: UUID
    name: str
    jurisdiction: str
    agency: str
    status: FilingStatus
    progress: int = Field(ge=0, le=100)
    last_agent_action: str
    updated_at: datetime
    open_requests: int = 0
    deadline: str | None = None


class ActionRequest(BaseModel):
    id: UUID
    filing_id: UUID
    filing_name: str
    request_type: RequestType
    title: str
    prompt: str
    why_needed: str
    field_key: str | None = None
    proposed_answer: str | None = None
    confidence: float | None = None
    source_type: SourceType | None = None
    portal_url: str | None = None
    status: str = "open"
    created_at: datetime


class FilingDetail(BaseModel):
    card: FilingCard
    recommendation: RegulatoryRecommendation
    checklist: list[ChecklistItem]
    fields: list[FieldConfidenceRecord]
    requests: list[ActionRequest]
    activity: list[ActivityEvent]


class Dashboard(BaseModel):
    needs_you_count: int
    in_progress_count: int
    upcoming_deadlines: int
    board: dict[FilingStatus, list[FilingCard]]
    requests: list[ActionRequest]
    recent_activity: list[ActivityEvent]


class AnswerRequest(BaseModel):
    answer: str = Field(min_length=1, max_length=1600)
    save_to_profile: bool = True


def new_id() -> UUID:
    return uuid4()


JsonDict = dict[str, Any]
