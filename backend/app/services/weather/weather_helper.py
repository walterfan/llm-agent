"""Weather helper service for multi-day forecasts."""

import logging
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.schemas.weather import ForecastCast, WeatherData
from app.services.cache_service import CacheService
from app.services.city_service import CityService
from app.services.weather.provider_factory import WeatherProviderFactory

logger = logging.getLogger(__name__)


class WeatherHelper:
    """Helper service for weather operations."""

    def __init__(self, db: Session):
        self.db = db
        self.cache = CacheService()

    async def get_forecast(self, city_code: str, days: int = 3) -> list[dict]:
        """
        Get multi-day weather forecast.

        Args:
            city_code: 6-digit city code (AD code)
            days: Number of days to forecast (default 3, max 4)

        Returns:
            List of daily forecast dicts with keys:
            - date: Date string (YYYY-MM-DD)
            - date_label: Chinese label ("今天", "明天", "后天", or "+N天")
            - weather_text: Weather condition
            - temperature_high: High temperature
            - temperature_low: Low temperature
            - wind_direction: Wind direction
            - wind_power: Wind power level

        Raises:
            ValueError: If city code is invalid or forecast unavailable
        """
        # Limit to 4 days (API limitation)
        days = min(days, 4)

        # Check cache
        cache_key = f"forecast:{city_code}:{days}"
        cached_data = self.cache.get(cache_key)
        if cached_data:
            logger.debug(f"Returning cached forecast for {city_code} ({days} days)")
            return cached_data

        # Fetch from weather provider with forecast
        weather_provider = WeatherProviderFactory.create(
            provider_type=settings.WEATHER_PROVIDER,
            base_url=settings.WEATHER_BASE_URL,
            api_key=settings.WEATHER_API_KEY,
        )

        # Get city name for provider
        city_obj = CityService.get_by_ad_code(self.db, city_code)
        if not city_obj:
            raise ValueError(f"Invalid city code: {city_code}")

        # Fetch with extensions="all" to get forecast
        weather_data: WeatherData = await weather_provider.fetch_weather(
            city_code, extensions="all"
        )

        if not weather_data.forecast or not weather_data.forecast.casts:
            raise ValueError(f"No forecast data available for city: {city_code}")

        logger.info(
            f"📊 Weather API returned {len(weather_data.forecast.casts)} forecast cast(s) for city {city_code}"
        )

        # Parse forecast data
        forecasts = []
        today = datetime.now().date()

        for i, cast in enumerate(weather_data.forecast.casts[:days]):
            # Calculate date label
            if i == 0:
                date_label = "今天"
            elif i == 1:
                date_label = "明天"
            elif i == 2:
                date_label = "后天"
            else:
                date_label = f"+{i}天"

            forecast_item = {
                "date": cast.date,
                "date_label": date_label,
                "weather_text": f"{cast.dayweather}/{cast.nightweather}",
                "temperature_high": cast.daytemp,
                "temperature_low": cast.nighttemp,
                "wind_direction": f"{cast.daywind}转{cast.nightwind}",
                "wind_power": f"{cast.daypower}级",
                "city": weather_data.city,
                "province": weather_data.province,
                "ad_code": weather_data.ad_code,
            }
            forecasts.append(forecast_item)

        # Cache for 1 hour (TTL is set in CacheService constructor)
        self.cache.set(cache_key, forecasts)

        logger.info(f"Fetched {len(forecasts)} day forecast for {city_code}")
        return forecasts

    def get_date_label(self, day_offset: int) -> str:
        """
        Convert day offset to Chinese label.

        Args:
            day_offset: 0 for today, 1 for tomorrow, 2 for day after tomorrow

        Returns:
            Chinese label string
        """
        labels = {0: "今天", 1: "明天", 2: "后天"}
        return labels.get(day_offset, f"+{day_offset}天")
