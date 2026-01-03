"""Base service class with consistent error handling and logging.

All services should inherit from BaseService for:
- Consistent logging with service name prefix
- Health check pattern
- Proper exception handling
"""
from abc import ABC, abstractmethod
from typing import Optional, TypeVar, Generic
import httpx

from ..core import get_logger
from ..core.exceptions import ServiceUnavailableError, GalateaError


T = TypeVar('T')


class BaseService(ABC):
    """Base class for all Galatea services.
    
    Provides:
    - Consistent logging with service name
    - Health check pattern
    - HTTP client management
    - Error wrapping utilities
    """
    
    def __init__(self, service_name: str, base_url: Optional[str] = None):
        """Initialize the service.
        
        Args:
            service_name: Human-readable service name (e.g., "Ollama", "Kokoro")
            base_url: Optional base URL for HTTP services
        """
        self.service_name = service_name
        self.base_url = base_url
        self.logger = get_logger(f"service.{service_name.lower()}")
        self._is_available: Optional[bool] = None
    
    @property
    def is_available(self) -> bool:
        """Check if service is available (cached)."""
        if self._is_available is None:
            # Will be set on first health check
            return False
        return self._is_available
    
    async def check_health(self) -> bool:
        """Check if the service is healthy and available.
        
        Subclasses should override _health_check() to implement
        service-specific health checks.
        
        Returns:
            True if service is available
        """
        try:
            self._is_available = await self._health_check()
            if self._is_available:
                self.logger.debug(f"{self.service_name} is healthy")
            else:
                self.logger.warning(f"{self.service_name} health check failed")
            return self._is_available
        except Exception as e:
            self.logger.warning(f"{self.service_name} health check error: {e}")
            self._is_available = False
            return False
    
    @abstractmethod
    async def _health_check(self) -> bool:
        """Service-specific health check implementation.
        
        Override this method to implement the actual health check.
        Should return True if service is available, False otherwise.
        Should NOT raise exceptions - return False instead.
        """
        pass
    
    def _wrap_connection_error(self, error: Exception) -> ServiceUnavailableError:
        """Wrap a connection error in a ServiceUnavailableError.
        
        Args:
            error: The original exception
            
        Returns:
            A ServiceUnavailableError with helpful context
        """
        suggestion = self._get_recovery_suggestion()
        return ServiceUnavailableError(
            service_name=self.service_name,
            url=self.base_url,
            suggestion=suggestion
        )
    
    def _get_recovery_suggestion(self) -> str:
        """Get a recovery suggestion for when this service is unavailable.
        
        Override in subclasses for service-specific suggestions.
        """
        return f"Check if {self.service_name} is running"
    
    async def _http_get(
        self, 
        path: str, 
        timeout: float = 10.0,
        **kwargs
    ) -> httpx.Response:
        """Make an HTTP GET request with error handling.
        
        Args:
            path: URL path (will be joined with base_url)
            timeout: Request timeout in seconds
            **kwargs: Additional arguments passed to httpx.get()
            
        Returns:
            The HTTP response
            
        Raises:
            ServiceUnavailableError: If connection fails
        """
        url = f"{self.base_url}{path}" if self.base_url else path
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url, **kwargs)
                response.raise_for_status()
                return response
        except httpx.ConnectError as e:
            self.logger.error(f"Connection failed to {url}: {e}")
            raise self._wrap_connection_error(e)
        except httpx.HTTPStatusError as e:
            self.logger.error(f"HTTP error from {url}: {e.response.status_code}")
            raise
    
    async def _http_post(
        self,
        path: str,
        timeout: float = 30.0,
        **kwargs
    ) -> httpx.Response:
        """Make an HTTP POST request with error handling.
        
        Args:
            path: URL path (will be joined with base_url)
            timeout: Request timeout in seconds
            **kwargs: Additional arguments passed to httpx.post()
            
        Returns:
            The HTTP response
            
        Raises:
            ServiceUnavailableError: If connection fails
        """
        url = f"{self.base_url}{path}" if self.base_url else path
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(url, **kwargs)
                response.raise_for_status()
                return response
        except httpx.ConnectError as e:
            self.logger.error(f"Connection failed to {url}: {e}")
            raise self._wrap_connection_error(e)
        except httpx.HTTPStatusError as e:
            self.logger.error(f"HTTP error from {url}: {e.response.status_code}")
            raise


class ServiceResult(Generic[T]):
    """A result wrapper that can contain either a value or an error.
    
    Use this for operations that can fail gracefully.
    
    Example:
        result = await service.do_something()
        if result.success:
            process(result.value)
        else:
            log_error(result.error)
    """
    
    def __init__(
        self,
        value: Optional[T] = None,
        error: Optional[str] = None,
        exception: Optional[Exception] = None
    ):
        self._value = value
        self._error = error
        self._exception = exception
    
    @property
    def success(self) -> bool:
        """True if the operation succeeded."""
        return self._error is None and self._exception is None
    
    @property
    def value(self) -> T:
        """The result value. Raises if operation failed."""
        if not self.success:
            raise ValueError(f"Cannot get value from failed result: {self.error}")
        return self._value  # type: ignore
    
    @property
    def error(self) -> Optional[str]:
        """The error message, if any."""
        if self._error:
            return self._error
        if self._exception:
            return str(self._exception)
        return None
    
    @classmethod
    def ok(cls, value: T) -> "ServiceResult[T]":
        """Create a successful result."""
        return cls(value=value)
    
    @classmethod
    def fail(cls, error: str) -> "ServiceResult[T]":
        """Create a failed result with an error message."""
        return cls(error=error)
    
    @classmethod
    def from_exception(cls, exception: Exception) -> "ServiceResult[T]":
        """Create a failed result from an exception."""
        return cls(exception=exception)
