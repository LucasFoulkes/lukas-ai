"""
    Errors for the AIRC module
"""


class AIRCError(Exception):
    """
        A generic error for Async IRC
    """


class HandlerError(AIRCError):
    """
        Generic error raised for a handler failing
    """


class CheckFailure(AIRCError):
    """
        Raised when a command can't run due to checks failing
    """
