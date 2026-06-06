from app.agent import FilingAgent, fallback_result
from app.config import Settings
from app.models import FilingDescribeRequest, FilingStatus


class FakeResponse:
    def __init__(self, output_text: str, output: list[dict] | None = None):
        self.output_text = output_text
        self.output = output or []


class FakeResponses:
    def __init__(self, output_text: str, output: list[dict] | None = None):
        self.calls: list[dict] = []
        self.output_text = output_text
        self.output = output or []

    async def create(self, **kwargs):
        tools = kwargs.get("tools") or []
        self.calls.append(kwargs)
        if tools and tools[0]["type"] == "web_search":
            raise RuntimeError("web_search unavailable")
        return FakeResponse(self.output_text, self.output)


class FakeClient:
    def __init__(self, output_text: str, output: list[dict] | None = None):
        self.responses = FakeResponses(output_text, output)


async def test_research_falls_back_from_web_search_to_preview_without_network():
    request = FilingDescribeRequest(description="Register a company and prepare for final submit.")
    output = fallback_result(request, "fake").model_dump_json()
    agent = FilingAgent(Settings(openai_api_key="test-key", supabase_url="", supabase_service_role_key=""))
    fake_client = FakeClient(output)
    agent.client = fake_client

    result = await agent.research(request)

    assert fake_client.responses.calls[0]["tools"][0]["type"] == "web_search"
    assert fake_client.responses.calls[0]["include"] == ["web_search_call.action.sources"]
    assert fake_client.responses.calls[1]["tools"][0]["type"] == "web_search_preview"
    assert "include" not in fake_client.responses.calls[1]
    assert result.requests == []
    assert result.fields == []
    assert result.checklist == []
    assert result.next_status == FilingStatus.NOT_STARTED


async def test_portal_like_research_defers_form_specific_outputs_until_browser_observation():
    request = FilingDescribeRequest(description="Prepare a portal application for a business license.")
    output = fallback_result(request, "fake")
    output.requests = []
    output.recommendation.reason = "The official portal application requires business account access and payment before submission."
    output_json = output.model_dump_json()
    agent = FilingAgent(Settings(openai_api_key="test-key", supabase_url="", supabase_service_role_key=""))
    agent.client = FakeClient(output_json)

    result = await agent.research(request)

    assert result.requests == []
    assert result.fields == []
    assert result.checklist == []
    assert result.next_status == FilingStatus.NOT_STARTED
    assert "browser observation" in result.recommendation.reason.lower()


async def test_research_prefers_cited_web_sources_and_drops_placeholder_urls():
    request = FilingDescribeRequest(description="Prepare a renewal filing with the official regulator portal.")
    output = fallback_result(request, "fake")
    output.recommendation.sources[0].url = "https://example.invalid/not-real"
    output_json = output.model_dump_json()
    cited_sources = [
        {
            "type": "web_search_call",
            "action": {
                "sources": [
                    {
                        "title": "Official regulator renewal guide",
                        "url": "https://regulator.gov.example/renewals",
                        "snippet": "Official renewal requirements and filing steps.",
                    }
                ]
            },
        }
    ]
    agent = FilingAgent(Settings(openai_api_key="test-key", supabase_url="", supabase_service_role_key=""))
    agent.client = FakeClient(output_json, cited_sources)

    result = await agent.research(request)

    assert [source.url for source in result.recommendation.sources] == ["https://regulator.gov.example/renewals"]


async def test_fallback_research_adds_official_singapore_company_registration_links_without_openai():
    request = FilingDescribeRequest(description="I need to register a new Singapore company after reserving a name.")
    result = fallback_result(request, "OPENAI_API_KEY is not configured")

    assert result.recommendation.agency == "Accounting and Corporate Regulatory Authority"
    assert result.recommendation.sources
    assert all(source.url.startswith("https://www.acra.gov.sg/") for source in result.recommendation.sources)
    assert result.requests == []
    assert result.fields == []
    assert result.checklist == []
