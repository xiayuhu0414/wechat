from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint():
    with TestClient(app) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_message_payload_validation():
    with TestClient(app) as client:
        response = client.post("/api/messages/send", json={"targets": [], "messages": []})
    assert response.status_code == 422

