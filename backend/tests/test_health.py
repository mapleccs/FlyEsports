import pytest
from fastapi.testclient import TestClient


def test_health_check(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "0.1.0"
    assert "environment" in data


def test_auth_health(client: TestClient):
    response = client.get("/api/v1/auth/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "Auth service is healthy"


def test_teams_health(client: TestClient):
    response = client.get("/api/v1/teams/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "Teams service is healthy"


def test_tournaments_health(client: TestClient):
    response = client.get("/api/v1/tournaments/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "Tournaments service is healthy"