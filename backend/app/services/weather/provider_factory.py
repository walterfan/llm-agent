"""Factory for creating weather provider instances."""

import logging
from typing import Dict, Type

from app.services.weather.base import WeatherProvider
from app.services.weather.gaode_provider import GaodeProvider

logger = logging.getLogger(__name__)


class WeatherProviderFactory:
    """Factory for creating weather provider instances based on configuration."""

    # Registry of available providers
    _providers: Dict[str, Type[WeatherProvider]] = {
        "gaode": GaodeProvider,
        # Future providers can be added here:
        # "qweather": QWeatherProvider,
        # "openweather": OpenWeatherProvider,
    }

    @classmethod
    def create(cls, provider_type: str, base_url: str, api_key: str) -> WeatherProvider:
        """
        Create weather provider instance.

        Args:
            provider_type: Provider type (e.g., "gaode", "qweather")
            base_url: Base URL for the provider API
            api_key: API key for authentication

        Returns:
            WeatherProvider instance

        Raises:
            ValueError: If provider type is not supported
        """
        provider_class = cls._providers.get(provider_type.lower())

        if provider_class is None:
            supported = ", ".join(cls._providers.keys())
            raise ValueError(
                f"Unsupported weather provider: {provider_type}. "
                f"Supported providers: {supported}"
            )

        logger.info(f"Creating weather provider: {provider_type}")
        return provider_class(base_url=base_url, api_key=api_key)

    @classmethod
    def register_provider(
        cls, name: str, provider_class: Type[WeatherProvider]
    ) -> None:
        """
        Register a new weather provider.

        Args:
            name: Provider name (lowercase)
            provider_class: Provider class implementing WeatherProvider
        """
        cls._providers[name.lower()] = provider_class
        logger.info(f"Registered weather provider: {name}")

    @classmethod
    def list_providers(cls) -> list[str]:
        """Get list of available provider names."""
        return list(cls._providers.keys())


# Global provider instance
_weather_provider: WeatherProvider | None = None


def get_weather_provider(
    provider_type: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
) -> WeatherProvider:
    """
    Get or create weather provider singleton.

    Args:
        provider_type: Provider type (defaults to settings if not provided)
        base_url: Base URL (defaults to settings if not provided)
        api_key: API key (defaults to settings if not provided)

    Returns:
        WeatherProvider instance
    """
    global _weather_provider

    if _weather_provider is None:
        if not all([provider_type, base_url, api_key]):
            # Import here to avoid circular dependency
            from app.core.config import settings

            provider_type = provider_type or settings.WEATHER_PROVIDER
            base_url = base_url or settings.WEATHER_BASE_URL
            api_key = api_key or settings.WEATHER_API_KEY

        _weather_provider = WeatherProviderFactory.create(
            provider_type=provider_type,
            base_url=base_url,
            api_key=api_key,
        )

    return _weather_provider


def reset_weather_provider() -> None:
    """Reset weather provider singleton (mainly for testing)."""
    global _weather_provider
    _weather_provider = None
