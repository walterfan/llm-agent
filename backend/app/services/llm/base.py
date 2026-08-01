from abc import ABC, abstractmethod
from typing import Any, AsyncIterator

from pydantic import BaseModel


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(
        self, base_url: str, api_key: str, model: str, verify_ssl: bool = True
    ):
        """
        Initialize LLM provider.

        Args:
            base_url: Base URL for the API
            api_key: API key for authentication
            model: Model name to use
            verify_ssl: Whether to verify SSL certificates
        """
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.verify_ssl = verify_ssl

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the name of the provider."""
        pass

    @abstractmethod
    async def generate_completion(
        self,
        prompt: str,
        response_model: type[BaseModel],
        max_retries: int = 3,
        **kwargs: Any,
    ) -> BaseModel:
        """
        Generate a structured completion.

        Args:
            prompt: The prompt to send to the LLM
            response_model: Pydantic model for structured output
            max_retries: Maximum number of retries on failure
            **kwargs: Additional parameters

        Returns:
            Instance of response_model with LLM-generated data
        """
        pass

    async def generate_completion_stream(
        self, prompt: str, **kwargs: Any
    ) -> AsyncIterator[str]:
        """
        Generate a streaming completion (token-by-token).

        Args:
            prompt: The prompt to send to the LLM
            **kwargs: Additional parameters

        Yields:
            Individual tokens/chunks from the LLM

        Note:
            Default implementation raises NotImplementedError.
            Providers can override to support streaming.
        """
        raise NotImplementedError(f"{self.provider_name} does not support streaming")
        yield  # Make this an async generator
