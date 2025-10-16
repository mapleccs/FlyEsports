"""
User aggregate root.
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime, timezone
import uuid

from ..base import AggregateRoot, BusinessRuleViolationError
from ..value_objects.email import Email
from ..value_objects.user_preferences import UserPreferences


@dataclass
class User(AggregateRoot):
    """
    User aggregate root representing a platform user.

    A User is the core identity within the FlyEsports platform,
    managing authentication, preferences, and basic profile information.
    """

    user_id: str = field(default_factory=lambda: f"usr_{uuid.uuid4().hex[:12]}")
    username: str = ""
    email: Email = None
    password_hash: str = ""
    display_name: str = ""
    avatar_url: Optional[str] = None
    status: str = "active"  # active, suspended, deleted
    preferences: UserPreferences = field(default_factory=UserPreferences.create_default)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_active: Optional[datetime] = None

    # Statistics
    profile_count: int = 0
    total_matches: int = 0

    def __post_init__(self) -> None:
        """Post initialization validation and setup."""

        # Ensure email is Email value object
        if self.email and not isinstance(self.email, Email):
            object.__setattr__(self, "email", Email.create(str(self.email)))

        # Validate status
        valid_statuses = {"active", "suspended", "deleted"}
        if self.status not in valid_statuses:
            raise BusinessRuleViolationError(
                f"Invalid user status: {self.status}. Valid statuses: {valid_statuses}"
            )

        # Validate username
        if self.username and (len(self.username) < 3 or len(self.username) > 50):
            raise BusinessRuleViolationError(
                "Username must be between 3 and 50 characters"
            )

        # Validate display name
        if self.display_name and len(self.display_name) > 100:
            raise BusinessRuleViolationError(
                "Display name cannot exceed 100 characters"
            )

    @classmethod
    def create(
        cls,
        username: str,
        email: str,
        password_hash: str,
        display_name: Optional[str] = None,
    ) -> "User":
        """
        Create a new user.

        Args:
            username: Unique username for the user
            email: User's email address
            password_hash: Hashed password
            display_name: Optional display name (defaults to username)

        Returns:
            New User aggregate root

        Raises:
            BusinessRuleViolationError: If creation rules are violated
        """
        if not username or not username.strip():
            raise BusinessRuleViolationError("Username is required")

        if not email or not email.strip():
            raise BusinessRuleViolationError("Email is required")

        if not password_hash or not password_hash.strip():
            raise BusinessRuleViolationError("Password hash is required")

        username = username.strip()
        email_obj = Email.create(email.strip())
        display_name = display_name.strip() if display_name else username

        user = cls(
            username=username,
            email=email_obj,
            password_hash=password_hash,
            display_name=display_name,
        )

        # Add domain event for user creation
        from ..events.user_events import UserCreatedEvent

        event = UserCreatedEvent(
            user_id=user.user_id,
            username=username,
            email=email_obj.value,
            display_name=display_name,
            timestamp=user.created_at,
        )
        user.add_domain_event(event)

        return user

    def update_profile(
        self,
        display_name: Optional[str] = None,
        avatar_url: Optional[str] = None,
        preferences: Optional[UserPreferences] = None,
    ) -> None:
        """
        Update user profile information.

        Args:
            display_name: New display name
            avatar_url: New avatar URL
            preferences: New user preferences
        """
        old_data = {
            "display_name": self.display_name,
            "avatar_url": self.avatar_url,
            "preferences": self.preferences,
        }

        has_changes = False

        if display_name is not None and display_name != self.display_name:
            if len(display_name.strip()) > 100:
                raise BusinessRuleViolationError(
                    "Display name cannot exceed 100 characters"
                )
            object.__setattr__(self, "display_name", display_name.strip())
            has_changes = True

        if avatar_url is not None and avatar_url != self.avatar_url:
            object.__setattr__(self, "avatar_url", avatar_url)
            has_changes = True

        if preferences is not None and preferences != self.preferences:
            object.__setattr__(self, "preferences", preferences)
            has_changes = True

        if has_changes:
            object.__setattr__(self, "updated_at", datetime.now(timezone.utc))

            # Add domain event for user profile update
            from ..events.user_events import UserUpdatedEvent

            event = UserUpdatedEvent(
                user_id=self.user_id,
                old_data=old_data,
                new_data={
                    "display_name": self.display_name,
                    "avatar_url": self.avatar_url,
                    "preferences": self.preferences,
                },
                timestamp=self.updated_at,
            )
            self.add_domain_event(event)

    def record_activity(self) -> None:
        """Record user activity by updating last active timestamp."""
        object.__setattr__(self, "last_active", datetime.now(timezone.utc))

    def increment_profile_count(self) -> None:
        """Increment the number of player profiles owned by this user."""
        object.__setattr__(self, "profile_count", self.profile_count + 1)
        object.__setattr__(self, "updated_at", datetime.now(timezone.utc))

    def decrement_profile_count(self) -> None:
        """Decrement the number of player profiles owned by this user."""
        if self.profile_count > 0:
            object.__setattr__(self, "profile_count", self.profile_count - 1)
            object.__setattr__(self, "updated_at", datetime.now(timezone.utc))

    def increment_match_count(self) -> None:
        """Increment the total number of matches played by this user."""
        object.__setattr__(self, "total_matches", self.total_matches + 1)
        object.__setattr__(self, "updated_at", datetime.now(timezone.utc))

    def suspend(self, reason: str) -> None:
        """
        Suspend the user account.

        Args:
            reason: Reason for suspension

        Raises:
            BusinessRuleViolationError: If user is already suspended or deleted
        """
        if self.status != "active":
            raise BusinessRuleViolationError(
                f"Cannot suspend user with status: {self.status}"
            )

        if not reason or not reason.strip():
            raise BusinessRuleViolationError("Suspension reason is required")

        object.__setattr__(self, "status", "suspended")
        object.__setattr__(self, "updated_at", datetime.now(timezone.utc))

        # Add domain event for user suspension
        from ..events.user_events import UserSuspendedEvent

        event = UserSuspendedEvent(
            user_id=self.user_id, reason=reason.strip(), timestamp=self.updated_at
        )
        self.add_domain_event(event)

    def activate(self) -> None:
        """
        Activate the user account (unsuspend).

        Raises:
            BusinessRuleViolationError: If user is not suspended
        """
        if self.status != "suspended":
            raise BusinessRuleViolationError(
                f"Cannot activate user with status: {self.status}"
            )

        object.__setattr__(self, "status", "active")
        object.__setattr__(self, "updated_at", datetime.now(timezone.utc))

        # Add domain event for user activation
        from ..events.user_events import UserActivatedEvent

        event = UserActivatedEvent(user_id=self.user_id, timestamp=self.updated_at)
        self.add_domain_event(event)

    def delete(self) -> None:
        """
        Mark the user as deleted (soft delete).

        Raises:
            BusinessRuleViolationError: If user is already deleted
        """
        if self.status == "deleted":
            raise BusinessRuleViolationError("User is already deleted")

        object.__setattr__(self, "status", "deleted")
        object.__setattr__(self, "updated_at", datetime.now(timezone.utc))

        # Add domain event for user deletion
        from ..events.user_events import UserDeletedEvent

        event = UserDeletedEvent(user_id=self.user_id, timestamp=self.updated_at)
        self.add_domain_event(event)

    @property
    def is_active(self) -> bool:
        """Check if the user is active."""
        return self.status == "active"

    @property
    def is_suspended(self) -> bool:
        """Check if the user is suspended."""
        return self.status == "suspended"

    @property
    def is_deleted(self) -> bool:
        """Check if the user is deleted."""
        return self.status == "deleted"

    @property
    def has_profiles(self) -> bool:
        """Check if the user has any player profiles."""
        return self.profile_count > 0

    @property
    def has_match_experience(self) -> bool:
        """Check if the user has played any matches."""
        return self.total_matches > 0

    def __str__(self) -> str:
        """String representation of the user."""
        return f"User({self.username}, {self.display_name}, status={self.status})"

    def __hash__(self) -> int:
        """Hash based on user ID."""
        return hash(self.user_id)
