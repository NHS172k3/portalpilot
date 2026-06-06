from uuid import UUID

from agents import Agent

from app.agent import FilingAgent
from app.computer_use import ComputerUseHarness
from app.config import Settings
from app.models import (
    AgentResearchResult,
    ComputerUseRunRequest,
    ComputerUseRunResponse,
    ComputerUseAccessSessionResponse,
    DocumentExtractRequest,
    DocumentExtractResponse,
    FilingDescribeRequest,
)


class PortalPilotOrchestrator:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.research_service = FilingAgent(settings)
        self.computer_use_service = ComputerUseHarness(settings)
        self.research_agent = Agent(
            name="PortalPilot Research Agent",
            instructions="Research official filing requirements and emit dashboard-ready structured recommendations.",
        )
        self.document_agent = Agent(
            name="PortalPilot Document Agent",
            instructions="Extract reusable filing facts from untrusted documents with confidence and sensitivity labels.",
        )
        self.computer_use_agent = Agent(
            name="PortalPilot Computer-Use Agent",
            instructions="Control a browser only for safe non-final portal preparation, stopping at human-only boundaries.",
        )

    @property
    def agent_names(self) -> list[str]:
        return [self.research_agent.name, self.document_agent.name, self.computer_use_agent.name]

    async def research_filing(self, request: FilingDescribeRequest) -> AgentResearchResult:
        result = await self.research_service.research(request)
        result.activity.insert(0, self._agent_activity("research", self.research_agent.name))
        return result

    async def extract_document(self, request: DocumentExtractRequest) -> DocumentExtractResponse:
        result = await self.research_service.extract_document(request)
        result.activity.detail = f"{self.document_agent.name}: {result.activity.detail or ''}".strip()
        return result

    async def run_computer_use(self, request: ComputerUseRunRequest) -> ComputerUseRunResponse:
        result = await self.computer_use_service.run(request)
        result.agents = self.agent_names
        return result

    async def start_access_session(self, request: ComputerUseRunRequest, filing_id: UUID | None = None) -> ComputerUseAccessSessionResponse:
        return await self.computer_use_service.start_access_session(request, filing_id=filing_id)

    async def resume_access_session(
        self,
        session_id: str,
        request: ComputerUseRunRequest,
        filing_id: UUID | None = None,
    ) -> ComputerUseRunResponse:
        result = await self.computer_use_service.resume_access_session(session_id, request, filing_id=filing_id)
        result.agents = self.agent_names
        return result

    async def close_access_session(self, session_id: str, filing_id: UUID | None = None) -> bool:
        return await self.computer_use_service.close_access_session(session_id, filing_id=filing_id)

    def _agent_activity(self, run_type: str, agent_name: str):
        from app.models import ActivityEvent

        return ActivityEvent(
            event_type=f"{run_type}_agent_selected",
            summary=f"{agent_name} selected",
            detail="OpenAI Agents SDK agent definition loaded by PortalPilot orchestrator.",
        )
