"""
Weather tool for the Personal Secretary agent.

Reuses the existing weather provider to fetch weather data.
"""

from typing import Optional

from pydantic import BaseModel, Field

from app.services.secretary_agent.tracing import trace_tool_call


class WeatherInput(BaseModel):
    """Input schema for weather tool."""

    city: str = Field(
        description="City name or AD code (e.g., 'Beijing', '北京' or '110000')"
    )


class WeatherResponse(BaseModel):
    """Response schema for weather tool."""

    city: str = Field(description="City name")
    province: str = Field(description="Province name")
    temperature: str = Field(description="Current temperature")
    weather: str = Field(description="Weather condition (e.g., 'Sunny', 'Cloudy')")
    wind: str = Field(description="Wind information")
    humidity: str = Field(description="Humidity percentage")
    suggestion: str = Field(description="Practical suggestion based on weather")


# Common city name to AD code mapping
CITY_CODE_MAP = {
    # Direct municipalities
    "北京": "110000",
    "beijing": "110000",
    "上海": "310000",
    "shanghai": "310000",
    "天津": "120000",
    "tianjin": "120000",
    "重庆": "500000",
    "chongqing": "500000",
    # Provincial capitals
    "广州": "440100",
    "guangzhou": "440100",
    "深圳": "440300",
    "shenzhen": "440300",
    "杭州": "330100",
    "hangzhou": "330100",
    "南京": "320100",
    "nanjing": "320100",
    "成都": "510100",
    "chengdu": "510100",
    "武汉": "420100",
    "wuhan": "420100",
    "西安": "610100",
    "xian": "610100",
    "苏州": "320500",
    "suzhou": "320500",
}


def _resolve_city_code(city: str) -> str:
    """Resolve city name to AD code if possible."""
    # If already looks like an AD code (6 digits), return as is
    if city.isdigit() and len(city) == 6:
        return city

    # Try to find in mapping (case insensitive)
    city_lower = city.lower().strip()
    if city_lower in CITY_CODE_MAP:
        return CITY_CODE_MAP[city_lower]

    # Check Chinese names
    city_stripped = city.strip()
    if city_stripped in CITY_CODE_MAP:
        return CITY_CODE_MAP[city_stripped]

    # Default to Beijing if not found
    return "110000"


@trace_tool_call
async def get_weather(city: str) -> WeatherResponse:
    """
    Get current weather for a specified city.

    Uses the existing weather provider to fetch weather data
    from configured weather providers (e.g., Gaode).

    Args:
        city: City name or AD code (e.g., 'Beijing', '北京', '110000')

    Returns:
        WeatherResponse with current conditions and suggestions
    """
    from app.services.weather.provider_factory import get_weather_provider

    # Resolve city to AD code
    city_code = _resolve_city_code(city)

    # Get weather provider singleton
    provider = get_weather_provider()

    # Fetch weather data (base = current weather)
    weather_data = await provider.fetch_weather(city_code, extensions="base")

    # Generate suggestion based on conditions
    suggestion = _generate_suggestion_from_data(weather_data)

    return WeatherResponse(
        city=weather_data.city or city,
        province=weather_data.province or "",
        temperature=f"{weather_data.temperature}°C",
        weather=weather_data.weather,
        wind=f"{weather_data.wind_direction}风 {weather_data.wind_power}级",
        humidity=f"{weather_data.humidity}%",
        suggestion=suggestion,
    )


def _generate_suggestion_from_data(weather_data) -> str:
    """Generate a practical suggestion based on weather conditions."""
    if not weather_data:
        return "无法获取天气信息"

    weather = (weather_data.weather or "").lower()

    # Use the float temperature for comparison
    try:
        temp = weather_data.temperature_float
    except (ValueError, AttributeError):
        temp = 20.0

    suggestions = []

    # Temperature-based suggestions
    if temp < 5:
        suggestions.append("穿厚外套，注意保暖")
    elif temp < 15:
        suggestions.append("建议穿外套或毛衣")
    elif temp > 30:
        suggestions.append("天气炎热，注意防暑降温")

    # Weather-based suggestions
    if "rain" in weather or "雨" in weather:
        suggestions.append("记得带伞")
    elif "snow" in weather or "雪" in weather:
        suggestions.append("注意路滑，穿防滑鞋")
    elif "sunny" in weather or "晴" in weather:
        if temp > 25:
            suggestions.append("阳光强烈，注意防晒")
    elif "fog" in weather or "雾" in weather or "霾" in weather:
        suggestions.append("能见度低，出行注意安全")
    elif "阴" in weather:
        suggestions.append("天气阴沉，注意心情")

    return "；".join(suggestions) if suggestions else "天气适宜外出"
