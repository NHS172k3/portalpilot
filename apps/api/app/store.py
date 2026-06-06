from datetime import datetime, timezone
from uuid import UUID

from supabase import Client, create_client

from app.config import Settings
from app.models import (
    ActionRequest,
    ActivityEvent,
    AgentResearchResult,
    CompanyProfile,
    Dashboard,
    DocumentExtractResponse,
    ExtractedFact,
    FilingCard,
    FilingDescribeRequest,
    FilingDetail,
    FilingStatus,
    Person,
    SourceType,
    new_id,
)


def now() -> datetime:
    return datetime.now(timezone.utc)


class InMemoryStore:
    def __init__(self):
        self.filings: dict[UUID, FilingDetail] = {}
        self.profile = CompanyProfile(
            legal_name="",
            trading_name="",
            registration_id="",
            address="",
            industry_summary="",
            primary_contact_email="",
            primary_contact_phone="",
            filing_notes="",
        )
        self.people: list[Person] = []
        self.documents: dict[UUID, DocumentExtractResponse] = {}
        self.global_activity: list[ActivityEvent] = []

    async def create_filing(self, request: FilingDescribeRequest, result: AgentResearchResult) -> FilingDetail:
        filing_id = new_id()
        created = now()
        open_requests = [
            ActionRequest(
                id=new_id(),
                filing_id=filing_id,
                filing_name=result.recommendation.filing_name,
                request_type=req.request_type,
                title=req.title,
                prompt=req.prompt,
                why_needed=req.why_needed,
                proposed_answer=req.proposed_answer,
                confidence=req.confidence,
                source_type=req.source_type,
                portal_url=req.portal_url,
                created_at=created,
            )
            for req in result.requests
        ]
        progress = 55 if result.next_status == FilingStatus.NEEDS_YOU else 35
        card = FilingCard(
            id=filing_id,
            name=result.recommendation.filing_name,
            jurisdiction=result.recommendation.jurisdiction,
            agency=result.recommendation.agency,
            status=result.next_status,
            progress=progress,
            last_agent_action=result.activity[-1].summary if result.activity else "Research completed",
            updated_at=created,
            open_requests=len(open_requests),
            deadline=result.recommendation.deadline,
        )
        detail = FilingDetail(
            card=card,
            recommendation=result.recommendation,
            checklist=result.checklist,
            fields=result.fields,
            requests=open_requests,
            activity=result.activity,
        )
        self.filings[filing_id] = detail
        return detail

    async def dashboard(self) -> Dashboard:
        board: dict[FilingStatus, list[FilingCard]] = {status: [] for status in FilingStatus}
        requests: list[ActionRequest] = []
        activity: list[ActivityEvent] = []
        for detail in self.filings.values():
            board[detail.card.status].append(detail.card)
            requests.extend([req for req in detail.requests if req.status == "open"])
            activity.extend(detail.activity)
        activity.extend(self.global_activity)
        return Dashboard(
            needs_you_count=len(requests),
            in_progress_count=len(board[FilingStatus.IN_PROGRESS]),
            upcoming_deadlines=sum(1 for detail in self.filings.values() if detail.card.deadline),
            board=board,
            requests=sorted(requests, key=lambda item: item.created_at, reverse=True),
            recent_activity=activity[-8:][::-1],
        )

    async def filing(self, filing_id: UUID) -> FilingDetail | None:
        return self.filings.get(filing_id)

    async def get_profile(self) -> CompanyProfile:
        return self.profile

    async def update_profile(self, profile: CompanyProfile) -> CompanyProfile:
        self.profile = profile
        self.global_activity.append(
            ActivityEvent(event_type="profile_updated", summary="Company profile updated", detail="Reusable filing profile facts were saved.")
        )
        return self.profile

    async def save_document_extraction(self, extraction: DocumentExtractResponse) -> DocumentExtractResponse:
        self.documents[extraction.document_id] = extraction
        self.global_activity.append(extraction.activity)
        return extraction

    async def answer_request(self, request_id: UUID, answer: str, save_to_profile: bool = True) -> ActionRequest | None:
        for detail in self.filings.values():
            for req in detail.requests:
                if req.id == request_id:
                    req.status = "answered"
                    req.proposed_answer = answer
                    detail.card.open_requests = len([item for item in detail.requests if item.status == "open"])
                    detail.card.status = FilingStatus.IN_PROGRESS if detail.card.open_requests == 0 else FilingStatus.NEEDS_YOU
                    detail.card.last_agent_action = "Human answer received; agent queued to resume"
                    detail.card.updated_at = now()
                    detail.activity.append(
                        ActivityEvent(event_type="request_answered", summary=req.title, detail="Answer saved and run queued to resume.")
                    )
                    if save_to_profile:
                        note = f"{req.title}: {answer}"
                        existing = self.profile.filing_notes or ""
                        self.profile.filing_notes = f"{existing}\n{note}".strip()
                    return req
        return None

    async def append_agent_requests(
        self,
        filing_id: UUID,
        requests: list,
        activity: list[ActivityEvent] | None = None,
    ) -> list[ActionRequest]:
        detail = self.filings.get(filing_id)
        if not detail:
            return []
        created = now()
        added = [
            ActionRequest(
                id=new_id(),
                filing_id=filing_id,
                filing_name=detail.card.name,
                request_type=req.request_type,
                title=req.title,
                prompt=req.prompt,
                why_needed=req.why_needed,
                proposed_answer=req.proposed_answer,
                confidence=req.confidence,
                source_type=req.source_type,
                portal_url=req.portal_url,
                created_at=created,
            )
            for req in requests
        ]
        detail.requests.extend(added)
        if activity:
            detail.activity.extend(activity)
        detail.card.open_requests = len([item for item in detail.requests if item.status == "open"])
        if added:
            detail.card.status = FilingStatus.NEEDS_YOU
            detail.card.last_agent_action = "Computer-use run paused for human review"
            detail.card.updated_at = created
        return added

    async def persistence_status(self) -> dict:
        return {"backend": "memory", "healthy": True, "remote_error": None, "missing_tables": []}


class SupabaseStore(InMemoryStore):
    def __init__(self, settings: Settings):
        super().__init__()
        self.client: Client = create_client(settings.supabase_url, settings.supabase_service_role_key)  # type: ignore[arg-type]
        self.remote_error: str | None = None
        self.required_tables = [
            "filings",
            "regulatory_recommendations",
            "agent_requests",
            "field_confidence_records",
            "readiness_checklist_items",
            "activity_events",
            "company_profiles",
            "documents",
            "extracted_facts",
            "agent_runs",
        ]

    async def create_filing(self, request: FilingDescribeRequest, result: AgentResearchResult) -> FilingDetail:
        detail = await super().create_filing(request, result)
        try:
            self.client.table("filings").insert(
                {
                    "id": str(detail.card.id),
                    "name": detail.card.name,
                    "jurisdiction": detail.card.jurisdiction,
                    "agency": detail.card.agency,
                    "status": detail.card.status,
                    "progress": detail.card.progress,
                    "last_agent_action": detail.card.last_agent_action,
                    "deadline": detail.card.deadline,
                }
            ).execute()
            self.client.table("regulatory_recommendations").insert(
                {
                    "filing_id": str(detail.card.id),
                    "reason": detail.recommendation.reason,
                    "prerequisites": detail.recommendation.prerequisites,
                    "fee_expectation": detail.recommendation.fee_expectation,
                    "warnings": detail.recommendation.warnings,
                    "confidence": detail.recommendation.confidence,
                    "sources": [source.model_dump() for source in detail.recommendation.sources],
                }
            ).execute()
            if detail.requests:
                self.client.table("agent_requests").insert(
                    [
                        {
                            "id": str(req.id),
                            "filing_id": str(req.filing_id),
                            "request_type": req.request_type,
                            "title": req.title,
                            "prompt": req.prompt,
                            "why_needed": req.why_needed,
                            "proposed_answer": req.proposed_answer,
                            "confidence": req.confidence,
                            "source_type": req.source_type,
                            "portal_url": req.portal_url,
                            "status": req.status,
                        }
                        for req in detail.requests
                    ]
                ).execute()
            if detail.fields:
                self.client.table("field_confidence_records").insert(
                    [
                        {
                            "filing_id": str(detail.card.id),
                            "portal_section": field.portal_section,
                            "field_label": field.field_label,
                            "proposed_value": field.proposed_value,
                            "source_type": field.source_type,
                            "confidence": field.confidence,
                            "sensitivity": field.sensitivity,
                            "status": field.status,
                            "reason": field.reason,
                        }
                        for field in detail.fields
                    ]
                ).execute()
            if detail.activity:
                self.client.table("activity_events").insert(
                    [
                        {
                            "filing_id": str(detail.card.id),
                            "event_type": event.event_type,
                            "summary": event.summary,
                            "detail": event.detail,
                        }
                        for event in detail.activity
                    ]
                ).execute()
            if detail.checklist:
                self.client.table("readiness_checklist_items").insert(
                    [
                        {
                            "filing_id": str(detail.card.id),
                            "label": item.label,
                            "status": item.status,
                            "reason": item.reason,
                        }
                        for item in detail.checklist
                    ]
                ).execute()
            self.remote_error = None
        except Exception as exc:
            self.remote_error = str(exc)
        return detail

    async def dashboard(self) -> Dashboard:
        try:
            rows = self.client.table("filings").select("*").order("updated_at", desc=True).execute().data or []
            requests = self.client.table("agent_requests").select("*, filings(name)").eq("status", "open").order("created_at", desc=True).execute().data or []
            activity_rows = self.client.table("activity_events").select("*").order("created_at", desc=True).limit(8).execute().data or []
            self.remote_error = None
        except Exception as exc:
            self.remote_error = str(exc)
            return await super().dashboard()

        request_counts: dict[str, int] = {}
        for row in requests:
            request_counts[row["filing_id"]] = request_counts.get(row["filing_id"], 0) + 1

        board: dict[FilingStatus, list[FilingCard]] = {status: [] for status in FilingStatus}
        for row in rows:
            status = FilingStatus(row["status"])
            board[status].append(
                FilingCard(
                    id=row["id"],
                    name=row["name"],
                    jurisdiction=row["jurisdiction"],
                    agency=row["agency"],
                    status=status,
                    progress=row["progress"],
                    last_agent_action=row["last_agent_action"],
                    updated_at=row["updated_at"],
                    open_requests=request_counts.get(row["id"], 0),
                    deadline=row.get("deadline"),
                )
            )

        action_requests = [self._request_from_row(row) for row in requests]
        return Dashboard(
            needs_you_count=len(action_requests),
            in_progress_count=len(board[FilingStatus.IN_PROGRESS]),
            upcoming_deadlines=sum(1 for row in rows if row.get("deadline")),
            board=board,
            requests=action_requests,
            recent_activity=[ActivityEvent(event_type=row["event_type"], summary=row["summary"], detail=row.get("detail")) for row in activity_rows],
        )

    async def filing(self, filing_id: UUID) -> FilingDetail | None:
        try:
            filing_rows = self.client.table("filings").select("*").eq("id", str(filing_id)).limit(1).execute().data or []
        except Exception as exc:
            self.remote_error = str(exc)
            return await super().filing(filing_id)
        if not filing_rows:
            return await super().filing(filing_id)
        row = filing_rows[0]
        try:
            request_rows = self.client.table("agent_requests").select("*, filings(name)").eq("filing_id", str(filing_id)).order("created_at", desc=True).execute().data or []
            recommendation_rows = self.client.table("regulatory_recommendations").select("*").eq("filing_id", str(filing_id)).order("created_at", desc=True).limit(1).execute().data or []
            checklist_rows = self.client.table("readiness_checklist_items").select("*").eq("filing_id", str(filing_id)).order("created_at").execute().data or []
            field_rows = self.client.table("field_confidence_records").select("*").eq("filing_id", str(filing_id)).order("created_at").execute().data or []
            activity_rows = self.client.table("activity_events").select("*").eq("filing_id", str(filing_id)).order("created_at", desc=True).execute().data or []
            self.remote_error = None
        except Exception as exc:
            self.remote_error = str(exc)
            return await super().filing(filing_id)

        open_count = len([item for item in request_rows if item["status"] == "open"])
        card = FilingCard(
            id=row["id"],
            name=row["name"],
            jurisdiction=row["jurisdiction"],
            agency=row["agency"],
            status=FilingStatus(row["status"]),
            progress=row["progress"],
            last_agent_action=row["last_agent_action"],
            updated_at=row["updated_at"],
            open_requests=open_count,
            deadline=row.get("deadline"),
        )
        if recommendation_rows:
            rec_row = recommendation_rows[0]
            recommendation = {
                "filing_name": row["name"],
                "jurisdiction": row["jurisdiction"],
                "agency": row["agency"],
                "reason": rec_row["reason"],
                "prerequisites": rec_row.get("prerequisites") or [],
                "fee_expectation": rec_row.get("fee_expectation"),
                "deadline": row.get("deadline"),
                "warnings": rec_row.get("warnings") or [],
                "confidence": rec_row["confidence"],
                "sources": rec_row.get("sources") or [],
            }
        else:
            recommendation = {
                "filing_name": row["name"],
                "jurisdiction": row["jurisdiction"],
                "agency": row["agency"],
                "reason": "No recommendation record found.",
                "prerequisites": [],
                "fee_expectation": None,
                "deadline": row.get("deadline"),
                "warnings": [],
                "confidence": 0,
                "sources": [],
            }
        return FilingDetail(
            card=card,
            recommendation=recommendation,  # type: ignore[arg-type]
            checklist=[{"label": item["label"], "status": item["status"], "reason": item["reason"]} for item in checklist_rows],  # type: ignore[list-item]
            fields=[
                {
                    "portal_section": item["portal_section"],
                    "field_label": item["field_label"],
                    "proposed_value": item.get("proposed_value"),
                    "source_type": item["source_type"],
                    "confidence": item["confidence"],
                    "sensitivity": item["sensitivity"],
                    "status": item["status"],
                    "reason": item["reason"],
                }
                for item in field_rows
            ],  # type: ignore[list-item]
            requests=[self._request_from_row(item) for item in request_rows],
            activity=[ActivityEvent(event_type=item["event_type"], summary=item["summary"], detail=item.get("detail")) for item in activity_rows],
        )

    async def answer_request(self, request_id: UUID, answer: str, save_to_profile: bool = True) -> ActionRequest | None:
        answered = await super().answer_request(request_id, answer, save_to_profile=save_to_profile)
        try:
            rows = self.client.table("agent_requests").select("filing_id").eq("id", str(request_id)).limit(1).execute().data or []
            if not rows:
                return answered
            filing_id = rows[0]["filing_id"]
            self.client.table("agent_requests").update(
                {
                    "status": "answered",
                    "proposed_answer": answer,
                }
            ).eq("id", str(request_id)).execute()
            open_rows = self.client.table("agent_requests").select("id").eq("filing_id", filing_id).eq("status", "open").execute().data or []
            next_status = FilingStatus.IN_PROGRESS if not open_rows else FilingStatus.NEEDS_YOU
            self.client.table("filings").update(
                {
                    "status": next_status,
                    "last_agent_action": "Human answer received; agent queued to resume",
                    "updated_at": now().isoformat(),
                }
            ).eq("id", filing_id).execute()
            self.client.table("activity_events").insert(
                {
                    "filing_id": filing_id,
                    "event_type": "request_answered",
                    "summary": "Action Center request answered",
                    "detail": "Answer saved and run queued to resume.",
                }
            ).execute()
            if save_to_profile:
                profile = await self.get_profile()
                note = f"Action Center answer: {answer}"
                profile.filing_notes = f"{profile.filing_notes or ''}\n{note}".strip()
                await self.update_profile(profile)
            detail = await self.filing(UUID(filing_id))
            if not detail:
                return answered
            self.remote_error = None
            return next((req for req in detail.requests if req.id == request_id), answered)
        except Exception as exc:
            self.remote_error = str(exc)
            return answered

    async def get_profile(self) -> CompanyProfile:
        try:
            rows = self.client.table("company_profiles").select("*").order("created_at").limit(1).execute().data or []
            self.remote_error = None
        except Exception as exc:
            self.remote_error = str(exc)
            return await super().get_profile()
        if not rows:
            return await super().get_profile()
        row = rows[0]
        return CompanyProfile(
            legal_name=row.get("legal_name") or "",
            trading_name=row.get("trading_name") or "",
            registration_id=row.get("registration_id") or "",
            address=row.get("address") or "",
            industry_summary=row.get("industry_summary") or "",
            primary_contact_email=row.get("primary_contact_email") or "",
            primary_contact_phone=row.get("primary_contact_phone") or "",
            filing_notes=row.get("filing_notes") or "",
        )

    async def update_profile(self, profile: CompanyProfile) -> CompanyProfile:
        try:
            existing = self.client.table("company_profiles").select("id").order("created_at").limit(1).execute().data or []
            payload = profile.model_dump()
            if existing:
                self.client.table("company_profiles").update(payload).eq("id", existing[0]["id"]).execute()
            else:
                self.client.table("company_profiles").insert(payload).execute()
            self.remote_error = None
        except Exception as exc:
            self.remote_error = str(exc)
        await super().update_profile(profile)
        return profile

    async def save_document_extraction(self, extraction: DocumentExtractResponse) -> DocumentExtractResponse:
        try:
            self.client.table("documents").insert(
                {
                    "id": str(extraction.document_id),
                    "file_name": extraction.file_name,
                    "mime_type": "text/plain",
                    "status": extraction.status,
                }
            ).execute()
            if extraction.facts:
                self.client.table("extracted_facts").insert(
                    [
                        {
                            "document_id": str(extraction.document_id),
                            "label": fact.label,
                            "value": fact.value,
                            "source_type": fact.source_type,
                            "confidence": fact.confidence,
                            "sensitivity": fact.sensitivity,
                            "evidence_note": fact.evidence_note,
                        }
                        for fact in extraction.facts
                    ]
                ).execute()
            self.remote_error = None
        except Exception as exc:
            self.remote_error = str(exc)
        await super().save_document_extraction(extraction)
        return extraction

    async def append_agent_requests(
        self,
        filing_id: UUID,
        requests: list,
        activity: list[ActivityEvent] | None = None,
    ) -> list[ActionRequest]:
        added = await super().append_agent_requests(filing_id, requests, activity=activity)
        if not added:
            return []
        try:
            self.client.table("agent_requests").insert(
                [
                    {
                        "id": str(req.id),
                        "filing_id": str(req.filing_id),
                        "request_type": req.request_type,
                        "title": req.title,
                        "prompt": req.prompt,
                        "why_needed": req.why_needed,
                        "proposed_answer": req.proposed_answer,
                        "confidence": req.confidence,
                        "source_type": req.source_type,
                        "portal_url": req.portal_url,
                        "status": req.status,
                    }
                    for req in added
                ]
            ).execute()
            if activity:
                self.client.table("activity_events").insert(
                    [
                        {
                            "filing_id": str(filing_id),
                            "event_type": event.event_type,
                            "summary": event.summary,
                            "detail": event.detail,
                        }
                        for event in activity
                    ]
                ).execute()
            self.client.table("filings").update(
                {
                    "status": FilingStatus.NEEDS_YOU,
                    "last_agent_action": "Computer-use run paused for human review",
                    "updated_at": now().isoformat(),
                }
            ).eq("id", str(filing_id)).execute()
            self.remote_error = None
        except Exception as exc:
            self.remote_error = str(exc)
        return added

    async def persistence_status(self) -> dict:
        missing: list[str] = []
        try:
            for table in self.required_tables:
                self.client.table(table).select("*").limit(1).execute()
            self.remote_error = None
        except Exception as exc:
            self.remote_error = str(exc)
            message = str(exc)
            for table in self.required_tables:
                if table in message:
                    missing.append(table)
        return {
            "backend": "supabase",
            "healthy": self.remote_error is None,
            "remote_error": self.remote_error,
            "missing_tables": missing,
        }

    def _request_from_row(self, row: dict) -> ActionRequest:
        filing_name = row.get("filings", {}).get("name") if isinstance(row.get("filings"), dict) else None
        return ActionRequest(
            id=row["id"],
            filing_id=row["filing_id"],
            filing_name=filing_name or "Filing",
            request_type=row["request_type"],
            title=row["title"],
            prompt=row["prompt"],
            why_needed=row["why_needed"],
            proposed_answer=row.get("proposed_answer"),
            confidence=row.get("confidence"),
            source_type=row.get("source_type"),
            portal_url=row.get("portal_url"),
            status=row["status"],
            created_at=row["created_at"],
        )


store_singleton: InMemoryStore | None = None


def get_store(settings: Settings) -> InMemoryStore:
    global store_singleton
    if store_singleton is None:
        store_singleton = SupabaseStore(settings) if settings.has_supabase else InMemoryStore()
    return store_singleton
