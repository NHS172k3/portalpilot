from app.agent import FilingAgent, fallback_result
from app.config import Settings
from app.models import FilingDescribeRequest, RequestType


class FakeResponse:
    def __init__(self, output_text: str):
        self.output_text = output_text


class FakeResponses:
    def __init__(self, output_text: str):
        self.calls: list[list[dict]] = []
        self.output_text = output_text

    async def create(self, **kwargs):
        tools = kwargs.get("tools") or []
        self.calls.append(tools)
        if tools and tools[0]["type"] == "web_search":
            raise RuntimeError("web_search unavailable")
        return FakeResponse(self.output_text)


class FakeClient:
    def __init__(self, output_text: str):
        self.responses = FakeResponses(output_text)


async def test_research_falls_back_from_web_search_to_preview_without_network():
    request = FilingDescribeRequest(description="Register a company and prepare for final submit.")
    output = fallback_result(request, "fake").model_dump_json()
    agent = FilingAgent(Settings(openai_api_key="test-key", supabase_url="", supabase_service_role_key=""))
    fake_client = FakeClient(output)
    agent.client = fake_client

    result = await agent.research(request)

    assert fake_client.responses.calls[0][0]["type"] == "web_search"
    assert fake_client.responses.calls[1][0]["type"] == "web_search_preview"
    assert any(req.request_type == RequestType.HUMAN_WALL_HANDOFF for req in result.requests)


async def test_portal_like_research_always_gets_access_handoff():
    request = FilingDescribeRequest(description="Prepare a portal application for a business license.")
    output = fallback_result(request, "fake")
    output.requests = []
    output.recommendation.reason = "The official portal application requires business account access and payment before submission."
    output_json = output.model_dump_json()
    agent = FilingAgent(Settings(openai_api_key="test-key", supabase_url="", supabase_service_role_key=""))
    agent.client = FakeClient(output_json)

    result = await agent.research(request)

    assert result.requests[0].request_type == RequestType.HUMAN_WALL_HANDOFF
    assert "log in" in result.requests[0].prompt.lower()
