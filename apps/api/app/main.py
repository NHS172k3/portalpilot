from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings, get_settings
from app.models import (
    ActionRequest,
    AnswerRequest,
    CompanyProfile,
    ComputerUseAccessSessionResponse,
    ComputerUseRunRequest,
    ComputerUseRunResponse,
    Dashboard,
    DocumentExtractRequest,
    DocumentExtractResponse,
    FilingDescribeRequest,
    FilingDetail,
)
from app.orchestrator import PortalPilotOrchestrator
from app.store import InMemoryStore, get_store


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="PortalPilot API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    orchestrator = PortalPilotOrchestrator(settings)

    def store_dep() -> InMemoryStore:
        return get_store(settings)

    @app.get("/health")
    async def health():
        diagnostics: list[str] = []
        store = store_dep()
        persistence = await store.persistence_status()
        if not settings.has_openai:
            diagnostics.append("OPENAI_API_KEY is missing; agent research and extraction will use conservative fallback data.")
        if not settings.has_supabase:
            diagnostics.append("SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY is missing; API is using the in-memory demo store.")
        if settings.has_supabase and not persistence["healthy"]:
            diagnostics.append("Supabase is configured but persistence is degraded; API will keep a process-local memory copy.")
        return {
            "status": "ok",
            "mode": settings.backend_mode,
            "openai_configured": settings.has_openai,
            "supabase_configured": settings.has_supabase,
            "persistence": persistence,
            "missing_env": settings.missing_env,
            "cors_origins": settings.cors_origins,
            "computer_use_model": settings.computer_use_model,
            "agents": orchestrator.agent_names,
            "diagnostics": diagnostics,
        }

    @app.post("/filings/describe", response_model=FilingDetail)
    async def describe_filing(payload: FilingDescribeRequest, store: InMemoryStore = Depends(store_dep)):
        result = await orchestrator.research_filing(payload)
        return await store.create_filing(payload, result)

    @app.get("/dashboard", response_model=Dashboard)
    async def dashboard(store: InMemoryStore = Depends(store_dep)):
        return await store.dashboard()

    @app.get("/profile", response_model=CompanyProfile)
    async def get_profile(store: InMemoryStore = Depends(store_dep)):
        return await store.get_profile()

    @app.put("/profile", response_model=CompanyProfile)
    async def update_profile(payload: CompanyProfile, store: InMemoryStore = Depends(store_dep)):
        return await store.update_profile(payload)

    @app.post("/documents/extract", response_model=DocumentExtractResponse)
    async def extract_document(payload: DocumentExtractRequest, store: InMemoryStore = Depends(store_dep)):
        extraction = await orchestrator.extract_document(payload)
        return await store.save_document_extraction(extraction)

    @app.get("/filings/{filing_id}", response_model=FilingDetail)
    async def filing(filing_id: UUID, store: InMemoryStore = Depends(store_dep)):
        detail = await store.filing(filing_id)
        if not detail:
            raise HTTPException(status_code=404, detail="Filing not found")
        return detail

    @app.post("/agent-requests/{request_id}/answer", response_model=ActionRequest)
    async def answer_request(request_id: UUID, payload: AnswerRequest, store: InMemoryStore = Depends(store_dep)):
        answered = await store.answer_request(request_id, payload.answer, save_to_profile=payload.save_to_profile)
        if not answered:
            raise HTTPException(status_code=404, detail="Request not found")
        return answered

    @app.post("/filings/{filing_id}/computer-use", response_model=ComputerUseRunResponse)
    async def run_computer_use(filing_id: UUID, payload: ComputerUseRunRequest, store: InMemoryStore = Depends(store_dep)):
        detail = await store.filing(filing_id)
        if not detail:
            raise HTTPException(status_code=404, detail="Filing not found")
        objective = payload.objective or (
            f"Prepare safe non-final fields for {detail.card.name}. "
            "Use field confidence records as context only when visible on the current page."
        )
        field_answers = await store.field_answers_for_filing(filing_id)
        merged_answers = {**field_answers, **payload.field_answers}
        result = await orchestrator.run_computer_use(payload.model_copy(update={"objective": objective, "field_answers": merged_answers}))
        await store.apply_computer_use_result(filing_id, result)
        return result

    @app.post("/filings/{filing_id}/computer-use/access-session", response_model=ComputerUseAccessSessionResponse)
    async def start_computer_use_access_session(
        filing_id: UUID,
        payload: ComputerUseRunRequest,
        store: InMemoryStore = Depends(store_dep),
    ):
        detail = await store.filing(filing_id)
        if not detail:
            raise HTTPException(status_code=404, detail="Filing not found")
        objective = payload.objective or (
            f"Prepare safe non-final fields for {detail.card.name}. "
            "Wait for the user to complete login, CAPTCHA, MFA, or authorization before resuming."
        )
        return await orchestrator.start_access_session(
            payload.model_copy(update={"objective": objective, "allow_user_handoff": True}),
            filing_id=filing_id,
        )

    @app.post("/filings/{filing_id}/computer-use/access-session/{session_id}/resume", response_model=ComputerUseRunResponse)
    async def resume_computer_use_access_session(
        filing_id: UUID,
        session_id: str,
        payload: ComputerUseRunRequest,
        store: InMemoryStore = Depends(store_dep),
    ):
        detail = await store.filing(filing_id)
        if not detail:
            raise HTTPException(status_code=404, detail="Filing not found")
        objective = payload.objective or (
            f"Resume safe non-final field preparation for {detail.card.name} after user-cleared access."
        )
        field_answers = await store.field_answers_for_filing(filing_id)
        merged_answers = {**field_answers, **payload.field_answers}
        result = await orchestrator.resume_access_session(
            session_id,
            payload.model_copy(update={"objective": objective, "allow_user_handoff": True, "field_answers": merged_answers}),
            filing_id=filing_id,
        )
        await store.apply_computer_use_result(filing_id, result)
        return result

    @app.delete("/filings/{filing_id}/computer-use/access-session/{session_id}")
    async def close_computer_use_access_session(
        filing_id: UUID,
        session_id: str,
        store: InMemoryStore = Depends(store_dep),
    ):
        detail = await store.filing(filing_id)
        if not detail:
            raise HTTPException(status_code=404, detail="Filing not found")
        closed = await orchestrator.close_access_session(session_id, filing_id=filing_id)
        return {"closed": closed}

    return app


app = create_app()
