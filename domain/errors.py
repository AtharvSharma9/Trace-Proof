"""
Custom exception hierarchy for PRAMAAN.

Views import these and map them to user-facing messages.
No service ever raises a bare Exception or lets a stack trace escape.
"""

class PramaanError(Exception):
    """Base for all application errors."""

class AuthError(PramaanError):
    """Raised by auth_service for any authentication / authorisation failure."""

class LockedOutError(AuthError):
    """Badge is locked; carries minutes_remaining."""
    def __init__(self, badge_no: str, minutes_remaining: float):
        self.badge_no = badge_no
        self.minutes_remaining = minutes_remaining
        super().__init__(f"Badge {badge_no} is locked for {minutes_remaining:.0f} more minute(s).")

class InvalidCredentialsError(AuthError):
    """Wrong password or unknown badge."""
    def __init__(self, badge_no: str, attempts_remaining: int):
        self.badge_no = badge_no
        self.attempts_remaining = attempts_remaining
        super().__init__(
            f"Invalid credentials for {badge_no}. "
            f"{attempts_remaining} attempt(s) before lockout."
        )

class SessionExpiredError(AuthError):
    """Token is valid but the session has expired."""

class ReAuthRequired(AuthError):
    """The requested action requires the officer to re-enter their password."""

class ParseError(PramaanError):
    """Raised by parsers when a file cannot be parsed at all (not rejected rows)."""
    def __init__(self, path, reason: str):
        self.path = path
        self.reason = reason
        super().__init__(f"Cannot parse {path}: {reason}")

class PathTraversalError(PramaanError):
    """Raised when an input path escapes the case folder."""

class FileTooLargeError(PramaanError):
    """Raised when a file exceeds the configured size limit."""
    def __init__(self, path, size_bytes: int, limit_bytes: int):
        self.path = path
        self.size_bytes = size_bytes
        self.limit_bytes = limit_bytes
        super().__init__(
            f"{path} is {size_bytes / 1e6:.1f} MB; limit is {limit_bytes / 1e6:.0f} MB."
        )

class PasswordProtectedError(ParseError):
    """Raised when an Excel file is encrypted."""

class IntegrityError(PramaanError):
    """Raised by integrity_service when the chain or file hash is broken."""

class DuplicateEvidenceError(PramaanError):
    """Raised when the same file (by SHA-256) is ingested twice into one case."""
