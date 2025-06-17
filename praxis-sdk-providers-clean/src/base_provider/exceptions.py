class BaseProviderException(Exception):
    """Base exception for all provider-related errors."""
    pass


class SyncNotSupportedException(BaseProviderException):
    """Exception raised when synchronous queries are not supported."""
    pass

class AsyncNotSupportedException(BaseProviderException):
    """Exception raised when asynchronous streaming is not supported."""
    pass
