from httpx import ASGITransport, AsyncClient

from app.main import app


async def test_health():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["mode"] == "local_fallback"
    assert "OPENAI_API_KEY" in body["missing_env"]
    assert "SUPABASE_SERVICE_ROLE_KEY" in body["missing_env"]
    assert "http://127.0.0.1:3000" in body["cors_origins"]
    assert "PortalPilot Computer-Use Agent" in body["agents"]


async def test_local_cors_preflights_allow_common_next_origins():
    headers = {
        "Origin": "http://127.0.0.1:3000",
        "Access-Control-Request-Method": "GET",
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.options("/dashboard", headers=headers)

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:3000"


async def test_describe_filing_falls_back_without_openai_key():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/filings/describe",
            json={"description": "I need to register a new Singapore company after reserving a name."},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["card"]["status"] == "needs_you"
        assert body["requests"]

        filing_response = await client.get(f"/filings/{body['card']['id']}")
        dashboard_response = await client.get("/dashboard")

    assert filing_response.status_code == 200
    assert dashboard_response.status_code == 200
    dashboard = dashboard_response.json()
    assert dashboard["needs_you_count"] == 2
    assert any(request["request_type"] == "human_wall_handoff" for request in dashboard["requests"])


async def test_answer_request_closes_item_and_optionally_saves_to_profile():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post(
            "/filings/describe",
            json={"description": "I need to register a new Singapore company after reserving a name."},
        )
        request_id = created.json()["requests"][0]["id"]

        answered = await client.post(
            f"/agent-requests/{request_id}/answer",
            json={"answer": "Singapore, Accounting and Corporate Regulatory Authority", "save_to_profile": True},
        )
        profile = await client.get("/profile")

    assert answered.status_code == 200
    assert answered.json()["status"] == "answered"
    assert "Singapore" in profile.json()["filing_notes"]


async def test_profile_round_trip():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.put("/profile", json={"legal_name": "Example Labs", "industry_summary": "Software"})
        loaded = await client.get("/profile")

    assert response.status_code == 200
    assert loaded.status_code == 200
    assert loaded.json()["legal_name"] == "Example Labs"


async def test_document_extract_falls_back_without_openai_key():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/documents/extract",
            json={
                "file_name": "notes.txt",
                "content": "Company: Example Labs. Contact founder@example.com. Password: super-secret-value. Software platform.",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["facts"]
    assert body["activity"]["event_type"] == "document_extracted"
    serialized = str(body["facts"])
    assert "founder@example.com" not in serialized
    assert "super-secret-value" not in serialized


async def test_computer_use_route_pauses_on_login_wall():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post(
            "/filings/describe",
            json={"description": "I need to prepare a business portal filing draft."},
        )
        filing_id = created.json()["card"]["id"]
        response = await client.post(
            f"/filings/{filing_id}/computer-use",
            json={
                "target_url": "data:text/html,<html><body><h1>Sign in</h1><input type='password' /><button>Submit</button></body></html>",
                "max_steps": 1,
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "blocked"
    assert body["requests"][0]["request_type"] == "human_wall_handoff"
