"""
Unit tests for registration API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from src.presentation.api.main import create_app


class TestRegistrationAPI:
    """Test suite for registration API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        app = create_app()
        return TestClient(app)

    def test_registration_health_endpoint(self, client):
        """Test registration health endpoint."""
        response = client.get("/api/v1/registration/health")
        
        assert response.status_code == 200
        assert response.json()["status"] == "Registration service is healthy"

    @patch('src.infrastructure.database.connection.database_manager')
    def test_get_regions_for_registration_active_only(self, mock_db_manager, client):
        """Test getting active regions for registration."""
        # Mock database session
        mock_session = AsyncMock()
        mock_db_manager.get_session.return_value.__aenter__.return_value = mock_session
        
        # Mock query result
        mock_result = AsyncMock()
        mock_result.fetchall.return_value = [
            (26, "华北赛区", "北京、天津、河北、山西、内蒙古地区", True, "2025-09-09T14:12:01.609941+00:00", None),
            (27, "华东赛区", "上海、江苏、浙江、安徽、福建、江西、山东地区", True, "2025-09-09T14:12:01.611127+00:00", None),
        ]
        mock_session.execute.return_value = mock_result
        
        response = client.get("/api/v1/registration/regions?active_only=true")
        
        assert response.status_code == 200
        data = response.json()
        assert "regions" in data
        assert "total" in data
        assert len(data["regions"]) == 2
        assert data["regions"][0]["region_name"] == "华北赛区"
        assert data["regions"][0]["is_active"] is True

    @patch('src.infrastructure.database.connection.database_manager')
    def test_get_regions_for_registration_all(self, mock_db_manager, client):
        """Test getting all regions for registration."""
        # Mock database session
        mock_session = AsyncMock()
        mock_db_manager.get_session.return_value.__aenter__.return_value = mock_session
        
        # Mock query result
        mock_result = AsyncMock()
        mock_result.fetchall.return_value = [
            (26, "华北赛区", "北京、天津、河北、山西、内蒙古地区", True, "2025-09-09T14:12:01.609941+00:00", None),
            (27, "华东赛区", "上海、江苏、浙江、安徽、福建、江西、山东地区", False, "2025-09-09T14:12:01.611127+00:00", None),
        ]
        mock_session.execute.return_value = mock_result
        
        response = client.get("/api/v1/registration/regions")
        
        assert response.status_code == 200
        data = response.json()
        assert "regions" in data
        assert "total" in data
        assert len(data["regions"]) == 2
        # Should include both active and inactive regions
        assert any(region["is_active"] for region in data["regions"])
        assert any(not region["is_active"] for region in data["regions"])

    @patch('src.infrastructure.database.connection.database_manager')
    def test_get_regions_for_registration_database_error(self, mock_db_manager, client):
        """Test handling database errors."""
        # Mock database session to raise an exception
        mock_session = AsyncMock()
        mock_db_manager.get_session.return_value.__aenter__.return_value = mock_session
        mock_session.execute.side_effect = Exception("Database connection failed")
        
        response = client.get("/api/v1/registration/regions")
        
        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert "获取赛区列表失败" in data["error"]["message"]