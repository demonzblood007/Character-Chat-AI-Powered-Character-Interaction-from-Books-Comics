"""
User Exceptions
===============

Custom exceptions for user-related errors.
"""


class UserException(Exception):
    """Base exception for user errors."""
    status_code: int = 400
    detail: str = "User error"
    
    def __init__(self, detail: str = None):
        self.detail = detail or self.__class__.detail
        super().__init__(self.detail)


class UserNotFoundError(UserException):
    """Raised when a user is not found."""
    status_code = 404
    detail = "User not found"


class UserAlreadyExistsError(UserException):
    """Raised when trying to create a user that already exists."""
    status_code = 409
    detail = "User already exists"


class UserDeactivatedError(UserException):
    """Raised when trying to access a deactivated user."""
    status_code = 403
    detail = "User account is deactivated"


class InsufficientCreditsError(UserException):
    """Raised when user doesn't have enough credits."""
    status_code = 402
    detail = "Insufficient credits"


class BookLimitReachedError(UserException):
    """Raised when user has reached their book upload limit."""
    status_code = 403
    detail = "Book upload limit reached for your subscription tier"

