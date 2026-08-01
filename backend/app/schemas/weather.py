"""Weather schemas for API requests and responses."""

from datetime import datetime

from pydantic import BaseModel, Field


class ForecastCast(BaseModel):
    """Single day forecast data."""

    date: str = Field(..., description="Date (YYYY-MM-DD)")
    week: str = Field(..., description="Day of week")
    dayweather: str = Field(..., description="Daytime weather condition")
    nightweather: str = Field(..., description="Nighttime weather condition")
    daytemp: str = Field(..., description="Daytime temperature")
    nighttemp: str = Field(..., description="Nighttime temperature")
    daywind: str = Field(..., description="Daytime wind direction")
    nightwind: str = Field(..., description="Nighttime wind direction")
    daypower: str = Field(..., description="Daytime wind power level")
    nightpower: str = Field(..., description="Nighttime wind power level")


class ForecastData(BaseModel):
    """Forecast weather data (3-4 days)."""

    city: str = Field(..., description="City name")
    province: str = Field(..., description="Province name")
    adcode: str = Field(..., description="Administrative division code")
    reporttime: str = Field(..., description="Forecast report timestamp")
    casts: list[ForecastCast] = Field(
        default_factory=list, description="Forecast for next 3-4 days"
    )


class WeatherData(BaseModel):
    """Weather data from provider."""

    city: str = Field(..., description="City name")
    province: str | None = Field(None, description="Province name")
    ad_code: str = Field(..., description="Administrative division code")
    weather: str = Field(..., description="Weather condition (e.g., 晴, 雨)")
    temperature: str = Field(..., description="Temperature (string format)")
    temperature_float: float = Field(..., description="Temperature (numeric)")
    humidity: str = Field(..., description="Humidity percentage (string)")
    humidity_float: float = Field(..., description="Humidity percentage (numeric)")
    wind_direction: str = Field(..., description="Wind direction")
    wind_power: str = Field(..., description="Wind power level")
    report_time: str = Field(..., description="Weather report timestamp")
    cached: bool = Field(default=False, description="Whether data is from cache")
    forecast: ForecastData | None = Field(
        None, description="Forecast data if requested"
    )


class WeatherResponse(BaseModel):
    """Response for weather API endpoint."""

    success: bool = Field(..., description="Whether request was successful")
    data: WeatherData | None = Field(None, description="Weather data if successful")
    error: str | None = Field(None, description="Error message if failed")


class WeatherQuery(BaseModel):
    """Query parameters for weather request."""

    city: str = Field(..., description="City name or AD code", min_length=1)
    extensions: str = Field(
        default="base",
        description="Weather type: base (current) or all (current + forecast)",
    )
