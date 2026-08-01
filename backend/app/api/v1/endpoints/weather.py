"""Weather API endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.models.user import User
from app.schemas.weather import WeatherData, WeatherResponse
from app.services.cache_service import get_weather_cache
from app.services.city_service import city_service
from app.services.weather import get_weather_provider

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=WeatherResponse)
async def get_weather(
    city: str = Query(
        ..., min_length=1, description="City name (Chinese/English) or AD code"
    ),
    extensions: str = Query(
        "base", description="Weather type: base (current) or all (current + forecast)"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WeatherResponse:
    """
    Get current weather for a city.

    The city parameter can be:
    - AD code (6 digits, e.g., "340100" for Hefei)
    - City name in Chinese (e.g., "合肥")
    - City name in English (e.g., "Hefei")

    The extensions parameter can be:
    - "base": Current weather only (default)
    - "all": Current weather + 3-4 day forecast

    Requires authentication.

    Weather data is cached for 1 hour to minimize API calls.
    """
    try:
        # Resolve city name/code to AD code
        ad_code = city_service.resolve_city_code(db, city)

        if not ad_code:
            return WeatherResponse(
                success=False,
                error=f"City not found: {city}. Please check the city name or code.",
            )

        # Check cache first (include extensions in cache key)
        cache = get_weather_cache(ttl=settings.WEATHER_CACHE_TTL)
        cache_key = f"weather:{ad_code}:{extensions}"

        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"Cache hit for city {ad_code} (extensions={extensions})")
            cached_data.cached = True
            return WeatherResponse(
                success=True,
                data=cached_data,
            )

        # Cache miss - fetch from provider
        logger.info(
            f"Cache miss for city {ad_code}, fetching from provider (extensions={extensions})"
        )
        provider = get_weather_provider()

        weather_data = await provider.fetch_weather(ad_code, extensions=extensions)

        # Cache the result
        cache.set(cache_key, weather_data)
        logger.info(f"Cached weather data for city {ad_code} (extensions={extensions})")

        return WeatherResponse(
            success=True,
            data=weather_data,
        )

    except HTTPException:
        # Re-raise HTTP exceptions from provider
        raise
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return WeatherResponse(
            success=False,
            error=str(e),
        )
    except Exception as e:
        logger.error(f"Unexpected error fetching weather: {e}", exc_info=True)
        return WeatherResponse(
            success=False,
            error="An unexpected error occurred while fetching weather data.",
        )
