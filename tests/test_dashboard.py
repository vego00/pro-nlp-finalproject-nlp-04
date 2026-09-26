import asyncio
from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from web import app as dashboard


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(dashboard.settings, "ROOT_DIR", tmp_path)
    dashboard.sessions.clear()
    dashboard.run_lock = asyncio.Lock()
    with TestClient(dashboard.app) as client:
        yield client


def test_dashboard_and_settings(client):
    assert client.get("/").status_code == 200
    assert client.get("/static/app.js").status_code == 200
    settings = client.get("/api/config").json()
    assert settings["model"]
    assert not any("key" in key for key in settings)


def test_session_isolation_validation_and_download(client):
    first = client.post("/api/sessions").json()["id"]
    second = client.post("/api/sessions").json()["id"]
    dashboard.sessions[first]["state"]["plan"]["final_markdown"] = "# Hello\n<script>alert(1)</script>"
    assert client.get(f"/api/sessions/{second}").json()["markdown"] == ""
    result = client.get(f"/api/sessions/{first}").json()
    assert "<script>" not in result["html"]
    assert "<h1>Hello</h1>" in result["html"]
    assert client.get(f"/api/sessions/{first}/download").text.startswith("# Hello")
    assert client.get(f"/api/sessions/{second}/download").status_code == 404
    assert client.get("/api/sessions/missing").status_code == 404
    assert client.post(f"/api/sessions/{first}/messages", json={"text":" "}).status_code == 422
    dashboard.sessions[first]["status"] = "running"
    assert client.post(f"/api/sessions/{first}/messages", json={"text":"hello"}).status_code == 409


def test_refresh_continuation_and_error_rollback(monkeypatch):
    calls = []
    def invoke(state):
        calls.append(state["user_response"])
        state["supervision"]["last_decision"] = "Refresh" if len(calls) == 1 else "ASK_USER"
        state["plan"]["final_markdown"] = "# Draft"
        return state
    monkeypatch.setattr(dashboard, "invoke_graph", invoke)
    dashboard.run_lock = asyncio.Lock()
    session = {"id":"test", "state":dashboard.initial_state(), "status":"running", "error":None}
    asyncio.run(dashboard.run(session, "idea"))
    assert calls == ["idea", "idea"]
    assert session["status"] == "ready"
    def fail(state):
        state["plan"]["final_markdown"] = "corrupted"
        raise RuntimeError("offline")
    monkeypatch.setattr(dashboard, "invoke_graph", fail)
    asyncio.run(dashboard.run(session, "retry"))
    assert session["status"] == "error"
    assert "offline" in session["error"]
    assert session["state"]["plan"]["final_markdown"] == "# Draft"


def test_message_background_and_form(client, monkeypatch):
    import time
    def invoke(state):
        state["messages"] += [HumanMessage(content=str(state["user_response"])), AIMessage(content="done")]
        state["supervision"].update(last_decision="ASK_USER", request_type="text")
        return state
    monkeypatch.setattr(dashboard, "invoke_graph", invoke)
    sid = client.post("/api/sessions").json()["id"]
    session = dashboard.sessions[sid]
    session["state"]["supervision"]["request_type"] = "idea_form"
    session["state"]["input_request"] = [{"current_section":"audience", "question":"누구?"}]
    url = f"/api/sessions/{sid}/messages"
    assert client.post(url, json={"text":"hello"}).status_code == 422
    assert client.post(url, json={"answers":{"audience":{"question":"누구?", "selected_option":"학생", "value":"학생"}}}).status_code == 202
    for _ in range(100):
        data = client.get(f"/api/sessions/{sid}").json()
        if data["status"] != "running":
            break
        time.sleep(.01)
    assert data["status"] == "ready"
    assert data["messages"][-1]["content"] == "done"


def test_llm_model_selection(monkeypatch):
    from models.llm import get_llm, get_mini_llm
    from config import config
    monkeypatch.setattr(config, "LLM_PROVIDER", "ollama")
    monkeypatch.setattr(config, "LLM_MODEL", "test-main")
    monkeypatch.setattr(config, "LLM_MINI_MODEL", "test-small")
    assert get_llm(json_mode=True).model == "test-main"
    assert get_llm(json_mode=True).format == "json"
    assert get_mini_llm().model == "test-small"
    monkeypatch.setattr(config, "LLM_PROVIDER", "invalid")
    with pytest.raises(ValueError, match="LLM_PROVIDER"):
        get_llm()


def test_draft_save_isolated_from_generated_document(client):
    sid = client.post("/api/sessions").json()["id"]
    other = client.post("/api/sessions").json()["id"]
    dashboard.sessions[sid]["state"]["plan"]["final_markdown"] = "AI result"
    text = "# My draft\n\n<script>alert(1)</script>"
    url = f"/api/sessions/{sid}/draft"
    result = client.put(url, json={"markdown":text})
    assert result.status_code == 200
    assert "<script>" not in result.json()["draft_html"]
    assert (dashboard.settings.ROOT_DIR / "output" / "drafts" / f"{sid}.md").read_text(encoding="utf-8") == text
    data = client.get(f"/api/sessions/{sid}").json()
    assert data["draft"] == text
    assert data["markdown"] == "AI result"
    assert client.get(f"/api/sessions/{other}").json()["draft"] == ""
    assert client.get(url + "/download").text == text
    assert client.put(url, json={"markdown":"x" * 200001}).status_code == 422
    dashboard.sessions[sid]["status"] = "running"
    assert client.put(url, json={"markdown":"changed"}).status_code == 200
    dashboard.sessions[sid]["status"] = "ready"
    assert client.put(url, json={"markdown":""}).json()["draft"] == ""


@pytest.mark.parametrize("include_draft", [True, False])
def test_draft_forwarded_only_when_requested(client, monkeypatch, include_draft):
    import time
    captured = []
    def invoke(state):
        captured.append(state["user_response"])
        return state
    monkeypatch.setattr(dashboard, "invoke_graph", invoke)
    sid = client.post("/api/sessions").json()["id"]
    client.put(f"/api/sessions/{sid}/draft", json={"markdown":"My original draft"})
    assert client.post(f"/api/sessions/{sid}/messages", json={"text":"Improve this", "include_draft":include_draft}).status_code == 202
    for _ in range(100):
        if client.get(f"/api/sessions/{sid}").json()["status"] != "running":
            break
        time.sleep(.01)
    assert captured and ("My original draft" in captured[0]) == include_draft
    assert "Improve this" in captured[0]
    assert client.get(f"/api/sessions/{sid}").json()["draft"] == "My original draft"


def test_rich_document_roundtrip(client):
    import json
    sid = client.post("/api/sessions").json()["id"]
    document = {"type":"doc", "content":[{"type":"taskList", "content":[
        {"type":"taskItem", "attrs":{"checked":True}, "content":[{"type":"paragraph", "content":[{"type":"text", "text":"done"}]}]}
    ]}]}
    response = client.put(f"/api/sessions/{sid}/draft", json={"markdown":"- [x] done", "document":document})
    assert response.json()["draft_document"] == document
    assert client.get(f"/api/sessions/{sid}").json()["draft_document"] == document
    persisted = dashboard.settings.ROOT_DIR / "output" / "drafts" / f"{sid}.json"
    assert json.loads(persisted.read_text(encoding="utf-8"))["document"] == document
    assert client.put(f"/api/sessions/{sid}/draft", json={"markdown":"x", "document":{"type":"script"}}).status_code == 422


def test_revision_is_preview_only_and_failure_preserves_draft(client, monkeypatch):
    sid = client.post("/api/sessions").json()["id"]
    client.put(f"/api/sessions/{sid}/draft", json={"markdown":"Original"})
    captured = []
    def revise(request):
        captured.append(request)
        return "**Revised** <script>alert(1)</script>"
    monkeypatch.setattr(dashboard, "revise_passage", revise)
    payload = {"selection":"Original", "instruction":"Shorten", "context":"Context"}
    response = client.post(f"/api/sessions/{sid}/revise", json=payload)
    assert response.status_code == 200
    assert "<strong>Revised</strong>" in response.json()["html"]
    assert "<script>" not in response.json()["html"]
    assert captured[0].model_dump() == payload
    assert client.get(f"/api/sessions/{sid}").json()["draft"] == "Original"
    def fail(request):
        raise RuntimeError("private provider details")
    monkeypatch.setattr(dashboard, "revise_passage", fail)
    response = client.post(f"/api/sessions/{sid}/revise", json=payload)
    assert response.status_code == 502
    assert "private provider details" not in response.text
    assert not dashboard.sessions[sid]["revising"]
    assert client.get(f"/api/sessions/{sid}").json()["draft"] == "Original"
    dashboard.sessions[sid]["status"] = "running"
    assert client.post(f"/api/sessions/{sid}/revise", json=payload).status_code == 409
    assert client.post(f"/api/sessions/{sid}/revise", json={**payload,"selection":" "}).status_code == 422
