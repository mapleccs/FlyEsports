"""
Email value object.
"""

import re
from dataclasses import dataclass
from typing import ClassVar

from ..base import ValueObject, BusinessRuleViolationError


@dataclass(frozen=True)
class Email(ValueObject):
    """
    Email value object with validation.

    Ensures that email addresses are valid and normalized.
    """

    value: str

    # Email validation regex pattern
    EMAIL_PATTERN: ClassVar[str] = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

    def __post_init__(self) -> None:
        """Validate and normalize email address."""
        if not self.value:
            raise BusinessRuleViolationError("Email cannot be empty")

        # Normalize email (lowercase)
        normalized_email = self.value.lower().strip()

        # Validate email format
        if not re.match(self.EMAIL_PATTERN, normalized_email):
            raise BusinessRuleViolationError(f"Invalid email format: {self.value}")

        # Update the value with normalized email
        object.__setattr__(self, "value", normalized_email)

    @classmethod
    def create(cls, email: str) -> "Email":
        """
        Create an Email value object.

        Args:
            email: The email address string

        Returns:
            Email value object

        Raises:
            BusinessRuleViolationError: If email format is invalid
        """
        return cls(value=email)

    @property
    def domain(self) -> str:
        """Get the domain part of the email."""
        return self.value.split("@")[1]

    @property
    def local_part(self) -> str:
        """Get the local part of the email (before @)."""
        return self.value.split("@")[0]

    def __str__(self) -> str:
        """String representation of the email."""
        return self.value

    def __hash__(self) -> int:
        """Hash based on the email value."""
        return hash(self.value)

    def __eq__(self, other: object) -> bool:
        """Equality check based on email value."""
        if not isinstance(other, Email):
            return False
        return self.value == other.value
