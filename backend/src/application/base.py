"""
Base classes for application layer components.

This module provides foundational classes for use cases, commands,
and application services in FlyEsports.
"""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic

# Import the base UseCase from domain
from ..domain.base import UseCase as DomainUseCase

# Type variables
TRequest = TypeVar('TRequest')
TResponse = TypeVar('TResponse')


class UseCase(DomainUseCase[TRequest, TResponse], ABC):
    """
    Base class for application use cases.

    Application use cases orchestrate domain objects and infrastructure
    services to fulfill business requirements.
    """

    @abstractmethod
    async def execute(self, request: TRequest) -> TResponse:
        """Execute the use case with the given request."""
        pass


class UseCaseError(Exception):
    """
    Base exception for use case errors.

    Represents errors that occur during use case execution,
    typically wrapping domain or infrastructure errors.
    """

    def __init__(self, message: str, inner_exception: Exception = None):
        super().__init__(message)
        self.message = message
        self.inner_exception = inner_exception


class ValidationError(UseCaseError):
    """
    Exception raised when input validation fails.
    """

    def __init__(self, message: str, field: str = None):
        super().__init__(message)
        self.field = field


class AuthorizationError(UseCaseError):
    """
    Exception raised when user lacks required permissions.
    """

    pass


class NotFoundError(UseCaseError):
    """
    Exception raised when a required resource is not found.
    """

    pass


class ConflictError(UseCaseError):
    """
    Exception raised when there's a business logic conflict.
    """

    pass