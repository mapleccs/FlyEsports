"""
Tests for JWT service functionality.

This module tests the JWT service including:
- Token generation and validation
- Token pair creation
- Token refresh mechanisms
- Permission integration testing
- Error handling and edge cases
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from jose import jwt

from src.infrastructure.services.jwt_service import (
    JWTService,
    TokenPair,
    TokenClaims
)
from src.domain.entities.user import User
from src.domain.value_objects.user import Username, Email


class TestTokenPair:
    """Test TokenPair data class functionality."""

    def test_token_pair_creation_with_required_fields(self):
        """Test TokenPair can be created with required fields."""
        # Arrange & Act
        token_pair = TokenPair(
            access_token="access.jwt.token",
            refresh_token="refresh.jwt.token"
        )
        
        # Assert
        assert token_pair.access_token == "access.jwt.token"
        assert token_pair.refresh_token == "refresh.jwt.token"
        assert token_pair.token_type == "bearer"
        assert token_pair.expires_in == 0

    def test_token_pair_creation_with_all_fields(self):
        """Test TokenPair can be created with all fields."""
        # Arrange & Act
        token_pair = TokenPair(
            access_token="access.jwt.token",
            refresh_token="refresh.jwt.token",
            token_type="Bearer",
            expires_in=3600
        )
        
        # Assert
        assert token_pair.access_token == "access.jwt.token"
        assert token_pair.refresh_token == "refresh.jwt.token"
        assert token_pair.token_type == "Bearer"
        assert token_pair.expires_in == 3600


class TestTokenClaims:
    """Test TokenClaims data class functionality."""

    def test_token_claims_creation(self):
        """Test TokenClaims can be created with all fields."""
        # Arrange
        exp_time = datetime.utcnow() + timedelta(hours=1)
        iat_time = datetime.utcnow()
        
        # Act
        claims = TokenClaims(
            user_id=1,
            username="testuser",
            email="test@example.com",
            is_active=True,
            is_verified=True,
            exp=exp_time,
            iat=iat_time,
            token_type="access"
        )
        
        # Assert
        assert claims.user_id == 1
        assert claims.username == "testuser"
        assert claims.email == "test@example.com"
        assert claims.is_active is True
        assert claims.is_verified is True
        assert claims.exp == exp_time
        assert claims.iat == iat_time
        assert claims.token_type == "access"


class TestJWTService:
    """Test JWTService functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.jwt_service = JWTService()
        self.mock_user = Mock(spec=User)
        self.mock_user.id = 1
        self.mock_user.username = Mock(spec=Username)
        self.mock_user.username.value = "testuser"
        self.mock_user.email = Mock(spec=Email)
        self.mock_user.email.value = "test@example.com"
        self.mock_user.is_active = True
        self.mock_user.is_verified = True

    def test_jwt_service_initialization(self):
        """Test JWTService initializes with correct settings."""
        # Act
        service = JWTService()
        
        # Assert
        assert service.secret_key is not None
        assert service.algorithm is not None
        assert service.access_token_expire_minutes > 0
        assert service.refresh_token_expire_days == 7

    def test_create_token_pair_success(self):
        """Test successful token pair creation."""
        # Act
        token_pair = self.jwt_service.create_token_pair(self.mock_user)
        
        # Assert
        assert isinstance(token_pair, TokenPair)
        assert token_pair.access_token is not None
        assert token_pair.refresh_token is not None
        assert token_pair.token_type == "bearer"
        assert token_pair.expires_in > 0

    def test_create_token_pair_contains_correct_claims(self):
        """Test token pair contains correct user claims."""
        # Act
        token_pair = self.jwt_service.create_token_pair(self.mock_user)
        
        # Decode tokens to verify claims
        access_payload = jwt.decode(
            token_pair.access_token,
            key="dummy", 
            options={"verify_signature": False}
        )
        refresh_payload = jwt.decode(
            token_pair.refresh_token,
            key="dummy", 
            options={"verify_signature": False}
        )
        
        # Assert access token claims
        assert access_payload["user_id"] == 1
        assert access_payload["username"] == "testuser"
        assert access_payload["email"] == "test@example.com"
        assert access_payload["is_active"] is True
        assert access_payload["is_verified"] is True
        assert access_payload["token_type"] == "access"
        
        # Assert refresh token claims
        assert refresh_payload["user_id"] == 1
        assert refresh_payload["username"] == "testuser"
        assert refresh_payload["email"] == "test@example.com"
        assert refresh_payload["token_type"] == "refresh"

    def test_verify_access_token_success(self):
        """Test successful access token verification."""
        # Arrange
        token_pair = self.jwt_service.create_token_pair(self.mock_user)
        
        # Act
        claims = self.jwt_service.verify_access_token(token_pair.access_token)
        
        # Assert
        assert claims is not None
        assert isinstance(claims, TokenClaims)
        assert claims.user_id == 1
        assert claims.username == "testuser"
        assert claims.email == "test@example.com"
        assert claims.token_type == "access"

    def test_verify_access_token_with_refresh_token_fails(self):
        """Test access token verification fails with refresh token."""
        # Arrange
        token_pair = self.jwt_service.create_token_pair(self.mock_user)
        
        # Act
        claims = self.jwt_service.verify_access_token(token_pair.refresh_token)
        
        # Assert
        assert claims is None

    def test_verify_access_token_with_invalid_token(self):
        """Test access token verification fails with invalid token."""
        # Act
        claims = self.jwt_service.verify_access_token("invalid.jwt.token")
        
        # Assert
        assert claims is None

    def test_verify_access_token_with_malformed_token(self):
        """Test access token verification fails with malformed token."""
        # Act
        claims = self.jwt_service.verify_access_token("not-a-jwt-token")
        
        # Assert
        assert claims is None

    def test_verify_refresh_token_success(self):
        """Test successful refresh token verification."""
        # Arrange
        token_pair = self.jwt_service.create_token_pair(self.mock_user)
        
        # Act
        claims = self.jwt_service.verify_refresh_token(token_pair.refresh_token)
        
        # Assert
        assert claims is not None
        assert isinstance(claims, TokenClaims)
        assert claims.user_id == 1
        assert claims.username == "testuser"
        assert claims.email == "test@example.com"
        assert claims.token_type == "refresh"

    def test_verify_refresh_token_with_access_token_fails(self):
        """Test refresh token verification fails with access token."""
        # Arrange
        token_pair = self.jwt_service.create_token_pair(self.mock_user)
        
        # Act
        claims = self.jwt_service.verify_refresh_token(token_pair.access_token)
        
        # Assert
        assert claims is None

    def test_refresh_access_token_success(self):
        """Test successful access token refresh."""
        # Arrange - Create initial token pair
        token_pair = self.jwt_service.create_token_pair(self.mock_user)
        
        # Change user status to ensure new token has different data
        self.mock_user.is_verified = False  # Change a field to make tokens different
        
        # Act
        new_access_token = self.jwt_service.refresh_access_token(
            token_pair.refresh_token, 
            self.mock_user
        )
        
        # Assert
        assert new_access_token is not None
        
        # Verify new token is valid and contains updated user data
        new_claims = self.jwt_service.verify_access_token(new_access_token)
        assert new_claims is not None
        assert new_claims.user_id == 1
        assert new_claims.is_verified is False  # Should reflect updated user status
        
        # Verify new token is valid
        claims = self.jwt_service.verify_access_token(new_access_token)
        assert claims is not None
        assert claims.user_id == 1

    def test_refresh_access_token_with_wrong_user(self):
        """Test access token refresh fails with wrong user."""
        # Arrange
        token_pair = self.jwt_service.create_token_pair(self.mock_user)
        
        wrong_user = Mock(spec=User)
        wrong_user.id = 999
        
        # Act
        new_token = self.jwt_service.refresh_access_token(
            token_pair.refresh_token, 
            wrong_user
        )
        
        # Assert
        assert new_token is None

    def test_refresh_access_token_with_invalid_refresh_token(self):
        """Test access token refresh fails with invalid refresh token."""
        # Act
        new_token = self.jwt_service.refresh_access_token(
            "invalid.refresh.token", 
            self.mock_user
        )
        
        # Assert
        assert new_token is None

    def test_decode_token_without_verification(self):
        """Test token decoding without signature verification."""
        # Arrange
        token_pair = self.jwt_service.create_token_pair(self.mock_user)
        
        # Act
        payload = self.jwt_service.decode_token_without_verification(token_pair.access_token)
        
        # Assert
        assert payload is not None
        assert payload["user_id"] == 1
        assert payload["username"] == "testuser"
        assert payload["token_type"] == "access"

    def test_decode_token_without_verification_invalid_token(self):
        """Test token decoding fails with completely invalid token."""
        # Act
        payload = self.jwt_service.decode_token_without_verification("not-a-jwt")
        
        # Assert
        assert payload is None

    def test_get_token_expiry_success(self):
        """Test getting token expiry time."""
        # Arrange
        token_pair = self.jwt_service.create_token_pair(self.mock_user)
        
        # Act
        expiry = self.jwt_service.get_token_expiry(token_pair.access_token)
        
        # Assert
        assert expiry is not None
        assert isinstance(expiry, datetime)
        assert expiry > datetime.utcnow()

    def test_get_token_expiry_invalid_token(self):
        """Test getting token expiry fails with invalid token."""
        # Act
        expiry = self.jwt_service.get_token_expiry("invalid.token")
        
        # Assert
        assert expiry is None

    def test_is_token_expired_with_valid_token(self):
        """Test token expiry check with valid token."""
        # Arrange
        token_pair = self.jwt_service.create_token_pair(self.mock_user)
        
        # Act
        is_expired = self.jwt_service.is_token_expired(token_pair.access_token)
        
        # Assert
        assert is_expired is False

    def test_is_token_expired_with_invalid_token(self):
        """Test token expiry check with invalid token."""
        # Act
        is_expired = self.jwt_service.is_token_expired("invalid.token")
        
        # Assert
        assert is_expired is True

    @patch('src.infrastructure.services.jwt_service.datetime')
    def test_is_token_expired_with_expired_token(self, mock_datetime):
        """Test token expiry check with expired token."""
        # Arrange - Create token in the past
        past_time = datetime(2020, 1, 1)
        mock_datetime.utcnow.return_value = past_time
        mock_datetime.fromtimestamp = datetime.fromtimestamp
        
        token_pair = self.jwt_service.create_token_pair(self.mock_user)
        
        # Reset mock to current time
        mock_datetime.utcnow.return_value = datetime.utcnow()
        
        # Act
        is_expired = self.jwt_service.is_token_expired(token_pair.access_token)
        
        # Assert
        assert is_expired is True


class TestJWTServicePermissionIntegration:
    """Test JWT service integration with permission system."""

    def setup_method(self):
        """Set up test fixtures."""
        self.jwt_service = JWTService()

    def test_permission_dependency_with_valid_jwt(self):
        """Test permission dependency extraction with valid JWT."""
        # Arrange
        mock_user = Mock(spec=User)
        mock_user.id = 1
        mock_user.username = Mock(value="testuser")
        mock_user.email = Mock(value="test@example.com")
        mock_user.is_active = True
        mock_user.is_verified = True
        
        token_pair = self.jwt_service.create_token_pair(mock_user)
        
        # Act - Verify token can be decoded to extract user_id
        claims = self.jwt_service.verify_access_token(token_pair.access_token)
        
        # Assert - Claims contain user_id that can be used by permission dependencies
        assert claims is not None
        assert claims.user_id == 1
        assert isinstance(claims.user_id, int)  # Type needed for permission lookups

    def test_jwt_claims_contain_permission_relevant_data(self):
        """Test JWT claims contain data relevant for permission checking."""
        # Arrange
        mock_user = Mock(spec=User)
        mock_user.id = 123
        mock_user.username = Mock(value="admin")
        mock_user.email = Mock(value="admin@example.com")
        mock_user.is_active = True
        mock_user.is_verified = True
        
        # Act
        token_pair = self.jwt_service.create_token_pair(mock_user)
        claims = self.jwt_service.verify_access_token(token_pair.access_token)
        
        # Assert - Claims contain all data needed for permission checks
        assert claims.user_id == 123  # Primary key for permission lookups
        assert claims.username == "admin"  # Username for logging/auditing
        assert claims.email == "admin@example.com"  # Email for notifications
        assert claims.is_active is True  # Account status check
        assert claims.is_verified is True  # Verification status

    def test_jwt_service_handles_user_status_changes(self):
        """Test JWT service properly handles user status in tokens."""
        # Arrange - Create user with different statuses
        active_user = Mock(spec=User)
        active_user.id = 1
        active_user.username = Mock(value="active")
        active_user.email = Mock(value="active@example.com")
        active_user.is_active = True
        active_user.is_verified = True
        
        inactive_user = Mock(spec=User)
        inactive_user.id = 2
        inactive_user.username = Mock(value="inactive")
        inactive_user.email = Mock(value="inactive@example.com")
        inactive_user.is_active = False
        inactive_user.is_verified = False
        
        # Act
        active_token = self.jwt_service.create_token_pair(active_user)
        inactive_token = self.jwt_service.create_token_pair(inactive_user)
        
        active_claims = self.jwt_service.verify_access_token(active_token.access_token)
        inactive_claims = self.jwt_service.verify_access_token(inactive_token.access_token)
        
        # Assert
        assert active_claims.is_active is True
        assert active_claims.is_verified is True
        assert inactive_claims.is_active is False
        assert inactive_claims.is_verified is False

    def test_token_refresh_updates_user_status(self):
        """Test token refresh uses current user status."""
        # Arrange - Create initial token
        user = Mock(spec=User)
        user.id = 1
        user.username = Mock(value="user")
        user.email = Mock(value="user@example.com")
        user.is_active = True
        user.is_verified = False
        
        token_pair = self.jwt_service.create_token_pair(user)
        
        # Change user status
        user.is_verified = True
        
        # Act - Refresh token with updated user
        new_access_token = self.jwt_service.refresh_access_token(
            token_pair.refresh_token, 
            user
        )
        
        # Assert - New token has updated status
        new_claims = self.jwt_service.verify_access_token(new_access_token)
        assert new_claims.is_verified is True


class TestJWTServiceErrorHandling:
    """Test JWT service error handling and edge cases."""

    def setup_method(self):
        """Set up test fixtures."""
        self.jwt_service = JWTService()

    def test_verify_token_with_missing_required_fields(self):
        """Test token verification fails with missing required fields."""
        # Arrange - Create token with missing fields
        incomplete_payload = {
            "user_id": 1,
            # Missing username, email, exp, iat
            "token_type": "access"
        }
        
        token = jwt.encode(
            incomplete_payload, 
            self.jwt_service.secret_key, 
            algorithm=self.jwt_service.algorithm
        )
        
        # Act
        claims = self.jwt_service.verify_access_token(token)
        
        # Assert
        assert claims is None

    def test_verify_token_with_wrong_algorithm(self):
        """Test token verification fails with wrong algorithm."""
        # Arrange - Create token with different algorithm
        payload = {
            "user_id": 1,
            "username": "test",
            "email": "test@example.com",
            "exp": datetime.utcnow() + timedelta(hours=1),
            "iat": datetime.utcnow(),
            "token_type": "access"
        }
        
        # Use different algorithm
        token = jwt.encode(payload, "wrong-secret", algorithm="HS512")
        
        # Act
        claims = self.jwt_service.verify_access_token(token)
        
        # Assert
        assert claims is None

    def test_create_token_with_none_user_fields(self):
        """Test token creation handles None values in user fields gracefully."""
        # Arrange
        mock_user = Mock(spec=User)
        mock_user.id = 1
        mock_user.username = Mock(value="testuser")
        mock_user.email = Mock(value="test@example.com")
        mock_user.is_active = None  # None value
        mock_user.is_verified = None  # None value
        
        # Act - Should not raise exception
        token_pair = self.jwt_service.create_token_pair(mock_user)
        
        # Assert - Token created successfully
        assert token_pair.access_token is not None
        
        # Verify claims handle None values
        claims = self.jwt_service.verify_access_token(token_pair.access_token)
        assert claims is not None
        # JWT service should handle None gracefully

    def test_token_expiry_edge_cases(self):
        """Test token expiry handling edge cases."""
        # Test with token that has no expiry field
        payload_no_exp = {"user_id": 1}
        token_no_exp = jwt.encode(
            payload_no_exp, 
            "secret", 
            algorithm=self.jwt_service.algorithm
        )
        
        assert self.jwt_service.get_token_expiry(token_no_exp) is None
        assert self.jwt_service.is_token_expired(token_no_exp) is True