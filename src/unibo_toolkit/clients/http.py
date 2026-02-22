"""HTTP client for making requests to UniBo website."""

from typing import Any, Dict, Optional
import aiohttp


class HTTPClient:
    """Async HTTP client for UniBo website requests.

    Handles all HTTP communication with proper error handling,
    timeouts, and user agent configuration.
    """

    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    def __init__(
        self,
        timeout: int = 30,
        headers: Optional[Dict[str, str]] = None,
    ):
        """Initialize HTTP client.

        Args:
            timeout: Request timeout in seconds
            headers: Optional custom headers to merge with defaults
        """
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.headers = {**self.DEFAULT_HEADERS, **(headers or {})}
        self._session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self._session = aiohttp.ClientSession(
            timeout=self.timeout,
            headers=self.headers,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._session:
            await self._session.close()
            self._session = None

    async def get(self, url: str, params: Optional[Dict[str, Any]] = None, **kwargs) -> str:
        """Perform GET request and return response text.

        Args:
            url: Target URL
            params: Query parameters
            **kwargs: Additional arguments for aiohttp request

        Returns:
            Response text content

        Raises:
            aiohttp.ClientError: On network or HTTP errors
        """
        if not self._session:
            raise RuntimeError("HTTPClient must be used as async context manager")

        async with self._session.get(url, params=params, **kwargs) as response:
            response.raise_for_status()
            return await response.text()

    async def post(
        self, url: str, data: Optional[Any] = None, json: Optional[Dict[str, Any]] = None, **kwargs
    ) -> str:
        """Perform POST request and return response text.

        Args:
            url: Target URL
            data: Form data
            json: JSON payload
            **kwargs: Additional arguments for aiohttp request

        Returns:
            Response text content

        Raises:
            aiohttp.ClientError: On network or HTTP errors
        """
        if not self._session:
            raise RuntimeError("HTTPClient must be used as async context manager")

        async with self._session.post(url, data=data, json=json, **kwargs) as response:
            response.raise_for_status()
            return await response.text()
