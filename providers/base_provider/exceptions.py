class BaseProviderException(Exception):
    """Base exception for all provider-related errors.

    Attributes:
        error_code: A code identifying the error type
        message: Human-readable error description
    """

    def __init__(self, message: str, error_code: str = "PROVIDER_ERROR"):
        self.error_code = error_code
        self.message = message
        super().__init__(message)


class SyncNotSupportedException(BaseProviderException):
    """Exception raised when synchronous operations are not supported.

    Typically raised when trying to call sync methods on an async-only provider.
    """

    def __init__(self, message: str = "Synchronous operations not supported"):
        super().__init__(message, "SYNC_NOT_SUPPORTED")


class AsyncNotSupportedException(BaseProviderException):
    """Exception raised when asynchronous operations are not supported.

    Typically raised when trying to call async methods on a sync-only provider.
    """

    def __init__(self, message: str = "Asynchronous operations not supported"):
        super().__init__(message, "ASYNC_NOT_SUPPORTED")
