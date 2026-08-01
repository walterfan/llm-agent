"""LLM provider factory."""

from typing import Type

from app.services.llm.base import LLMProvider
from app.services.llm.openai_compatible import OpenAICompatibleProvider


class LLMProviderFactory:
    """Factory to create LLM provider instances."""

    _providers: dict[str, Type[LLMProvider]] = {
        "openai": OpenAICompatibleProvider,
        "deepseek": OpenAICompatibleProvider,
        "anthropic": OpenAICompatibleProvider,  # Anthropic also supports OpenAI-compatible API
        "ollama": OpenAICompatibleProvider,
        "vllm": OpenAICompatibleProvider,
    }

    @staticmethod
    def register_provider(name: str, provider_cls: Type[LLMProvider]):
        """
        Register a new LLM provider.

        Args:
            name: Provider name
            provider_cls: Provider class (must inherit from LLMProvider)
        """
        if not issubclass(provider_cls, LLMProvider):
            raise ValueError("Provider class must inherit from LLMProvider")
        LLMProviderFactory._providers[name] = provider_cls

    @staticmethod
    def get_provider(
        provider_type: str,
        base_url: str,
        api_key: str,
        model: str,
        verify_ssl: bool = True,
        timeout: int = 30,
        **kwargs,
    ) -> LLMProvider:
        """
        Get an LLM provider instance by type.

        Args:
            provider_type: Provider type (e.g., "openai", "deepseek")
            base_url: Base URL for the API
            api_key: API key for authentication
            model: Model name to use
            verify_ssl: Whether to verify SSL certificates
            timeout: Timeout for API calls in seconds
            **kwargs: Additional provider-specific parameters

        Returns:
            An instance of the specified LLMProvider

        Raises:
            ValueError: If the provider type is not supported
        """
        provider_cls = LLMProviderFactory._providers.get(provider_type.lower())
        if not provider_cls:
            raise ValueError(
                f"Unsupported LLM provider type: {provider_type}. "
                f"Supported types: {list(LLMProviderFactory._providers.keys())}"
            )

        return provider_cls(
            base_url=base_url,
            api_key=api_key,
            model=model,
            verify_ssl=verify_ssl,
            timeout=timeout,
            **kwargs,
        )
