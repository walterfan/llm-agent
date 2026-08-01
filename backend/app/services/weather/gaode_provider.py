"""Gaode (AutoNavi) weather provider implementation."""

import logging
from typing import Any

import httpx
from fastapi import HTTPException

from app.schemas.weather import ForecastCast, ForecastData, WeatherData
from app.services.weather.base import WeatherProvider

logger = logging.getLogger(__name__)


class GaodeProvider(WeatherProvider):
    """Gaode Weather API provider implementation."""

    @property
    def provider_name(self) -> str:
        """Get provider name."""
        return "gaode"

    def normalize_city_code(self, code: str) -> str:
        """
        Gaode uses AD codes directly (6-digit codes).

        Args:
            code: AD code

        Returns:
            Same AD code
        """
        # Validate AD code format
        if not code.isdigit() or len(code) != 6:
            raise ValueError(f"Invalid AD code: {code}. Must be 6 digits.")
        return code

    async def fetch_weather(
        self, city_code: str, extensions: str = "base"
    ) -> WeatherData:
        """
        Fetch weather from Gaode API.

        API Documentation: https://lbs.amap.com/api/webservice/guide/api/weatherinfo

        Args:
            city_code: AD code (6 digits)
            extensions: Weather type - "base" for current weather, "all" for current + forecast

        Returns:
            WeatherData object with optional forecast data

        Raises:
            ValueError: If city code is invalid
            HTTPException: If API request fails
        """
        # Normalize and validate city code
        normalized_code = self.normalize_city_code(city_code)

        # Validate extensions parameter
        if extensions not in ["base", "all"]:
            extensions = "base"

        # Build API URL
        url = f"{self.base_url}/v3/weather/weatherInfo"
        params = {
            "key": self.api_key,
            "city": normalized_code,
            "extensions": extensions,  # base = current weather, all = current + forecast
            "output": "json",  # Explicitly request JSON response
        }

        # Retry logic with exponential backoff
        max_retries = 3
        retry_delays = [1, 2, 4]  # seconds

        # Add headers to mimic browser request
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        }

        async with httpx.AsyncClient(timeout=10.0, headers=headers) as client:
            for attempt in range(max_retries):
                try:
                    logger.info(
                        f"Fetching weather from Gaode for city {normalized_code} (extensions={extensions}, attempt {attempt + 1}/{max_retries})"
                    )

                    # Log request details (mask API key for security)
                    masked_params = {**params, "key": f"{params['key'][:8]}..."}
                    logger.info(f"🔗 Request URL: {url}")
                    logger.info(f"📋 Request params: {masked_params}")
                    logger.info(f"📤 Request headers: {headers}")

                    response = await client.get(url, params=params)

                    # Log response details
                    logger.info(f"📥 Response status: {response.status_code}")
                    logger.info(f"📥 Response headers: {dict(response.headers)}")
                    logger.info(
                        f"📥 Response body: {response.text[:500]}"
                    )  # First 500 chars

                    response.raise_for_status()

                    data = response.json()
                    logger.info(f"📊 Parsed JSON: {data}")

                    # Check Gaode API status
                    if data.get("status") != "1":
                        error_msg = data.get("info", "Unknown error")
                        infocode = data.get("infocode", "Unknown")
                        logger.error(
                            f"Gaode API error: {error_msg} (infocode: {infocode})"
                        )
                        logger.error(f"Full API response: {data}")

                        if data.get("infocode") == "10001":
                            raise HTTPException(
                                status_code=401, detail="Invalid API key"
                            )
                        elif data.get("infocode") == "10003":
                            raise HTTPException(
                                status_code=404,
                                detail=f"City not found: {normalized_code}",
                            )
                        else:
                            raise HTTPException(
                                status_code=502,
                                detail=f"Weather provider error: {error_msg}",
                            )

                    # Parse response based on extensions type
                    if extensions == "all":
                        # Parse forecast data
                        forecasts = data.get("forecasts", [])
                        if not forecasts:
                            raise HTTPException(
                                status_code=404,
                                detail=f"No forecast data for city: {normalized_code}",
                            )

                        forecast_info = forecasts[0]
                        casts_data = forecast_info.get("casts", [])

                        # Parse forecast casts
                        forecast_casts = [
                            ForecastCast(
                                date=cast.get("date", ""),
                                week=cast.get("week", ""),
                                dayweather=cast.get("dayweather", ""),
                                nightweather=cast.get("nightweather", ""),
                                daytemp=cast.get("daytemp", ""),
                                nighttemp=cast.get("nighttemp", ""),
                                daywind=cast.get("daywind", ""),
                                nightwind=cast.get("nightwind", ""),
                                daypower=cast.get("daypower", ""),
                                nightpower=cast.get("nightpower", ""),
                            )
                            for cast in casts_data
                        ]

                        forecast_data = ForecastData(
                            city=forecast_info.get("city", ""),
                            province=forecast_info.get("province", ""),
                            adcode=forecast_info.get("adcode", normalized_code),
                            reporttime=forecast_info.get("reporttime", ""),
                            casts=forecast_casts,
                        )

                        # For "all" mode, use first day forecast as current weather
                        first_cast = casts_data[0] if casts_data else {}

                        weather_data = WeatherData(
                            city=forecast_info.get("city", ""),
                            province=forecast_info.get("province"),
                            ad_code=forecast_info.get("adcode", normalized_code),
                            weather=first_cast.get("dayweather", ""),
                            temperature=first_cast.get("daytemp", ""),
                            temperature_float=float(first_cast.get("daytemp", 0)),
                            humidity="0",  # Forecast mode doesn't provide humidity
                            humidity_float=0.0,
                            wind_direction=first_cast.get("daywind", ""),
                            wind_power=first_cast.get("daypower", ""),
                            report_time=forecast_info.get("reporttime", ""),
                            cached=False,
                            forecast=forecast_data,
                        )
                    else:
                        # Parse live (current) weather data
                        lives = data.get("lives", [])
                        if not lives:
                            raise HTTPException(
                                status_code=404,
                                detail=f"No weather data for city: {normalized_code}",
                            )

                        live_data = lives[0]

                        # Convert to WeatherData
                        weather_data = WeatherData(
                            city=live_data.get("city", ""),
                            province=live_data.get("province"),
                            ad_code=live_data.get("adcode", normalized_code),
                            weather=live_data.get("weather", ""),
                            temperature=live_data.get("temperature", ""),
                            temperature_float=float(
                                live_data.get(
                                    "temperature_float", live_data.get("temperature", 0)
                                )
                            ),
                            humidity=live_data.get("humidity", ""),
                            humidity_float=float(
                                live_data.get(
                                    "humidity_float", live_data.get("humidity", 0)
                                )
                            ),
                            wind_direction=live_data.get("winddirection", ""),
                            wind_power=live_data.get("windpower", ""),
                            report_time=live_data.get("reporttime", ""),
                            cached=False,
                            forecast=None,
                        )

                    logger.info(
                        f"Successfully fetched weather for {weather_data.city} (extensions={extensions})"
                    )
                    return weather_data

                except httpx.HTTPStatusError as e:
                    if e.response.status_code >= 500 and attempt < max_retries - 1:
                        # Retry on 5xx errors
                        logger.warning(
                            f"HTTP {e.response.status_code} error, retrying in {retry_delays[attempt]}s..."
                        )
                        await httpx.AsyncClient().aclose()  # Clean up
                        import asyncio

                        await asyncio.sleep(retry_delays[attempt])
                        continue
                    else:
                        logger.error(f"HTTP error fetching weather: {e}")
                        raise HTTPException(
                            status_code=e.response.status_code,
                            detail=f"Weather provider returned error: {e.response.status_code}",
                        )

                except httpx.TimeoutException:
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"Timeout, retrying in {retry_delays[attempt]}s..."
                        )
                        import asyncio

                        await asyncio.sleep(retry_delays[attempt])
                        continue
                    else:
                        logger.error("Timeout fetching weather after all retries")
                        raise HTTPException(
                            status_code=504, detail="Weather provider timeout"
                        )

                except httpx.RequestError as e:
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"Request error: {e}, retrying in {retry_delays[attempt]}s..."
                        )
                        import asyncio

                        await asyncio.sleep(retry_delays[attempt])
                        continue
                    else:
                        logger.error(f"Request error fetching weather: {e}")
                        raise HTTPException(
                            status_code=503, detail="Weather provider unavailable"
                        )

            # Should not reach here, but just in case
            raise HTTPException(
                status_code=503, detail="Weather provider unavailable after retries"
            )
