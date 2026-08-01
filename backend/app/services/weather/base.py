"""Abstract base class for weather providers."""

from abc import ABC, abstractmethod

from app.schemas.weather import WeatherData


class WeatherProvider(ABC):
    """Abstract interface for weather data providers."""

    def __init__(self, base_url: str, api_key: str):
        """
        Initialize weather provider.

        Args:
            base_url: Base URL for the weather API (configurable, not hardcoded)
            api_key: API key for authentication
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    @abstractmethod
    async def fetch_weather(
        self, city_code: str, extensions: str = "base"
    ) -> WeatherData:
        """
        Fetch weather data for a city.

        Args:
            city_code: City code (format depends on provider)
            extensions: Weather type - "base" for current weather, "all" for current + forecast

        Returns:
            WeatherData object

        Raises:
            ValueError: If city code is invalid
            HTTPException: If API request fails
        """
        pass

    @abstractmethod
    def normalize_city_code(self, code: str) -> str:
        """
        Convert generic city code to provider-specific format.

        Args:
            code: Generic city code (e.g., AD code)

        Returns:
            Provider-specific city code
        """
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Get provider name for logging/identification."""
        pass
