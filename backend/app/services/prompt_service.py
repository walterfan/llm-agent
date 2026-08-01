"""Service for loading and managing prompt templates."""

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class PromptService:
    """Service for loading and formatting prompt templates from YAML configuration."""

    _prompts: dict[str, Any] | None = None
    _prompts_file = Path(__file__).parent.parent / "prompts.yaml"

    @classmethod
    def load_prompts(cls) -> dict[str, Any]:
        """Load prompts from YAML file (cached)."""
        if cls._prompts is None:
            try:
                with open(cls._prompts_file, "r", encoding="utf-8") as f:
                    cls._prompts = yaml.safe_load(f)
                logger.info(f"Loaded prompts from {cls._prompts_file}")
            except Exception as e:
                logger.error(f"Failed to load prompts from {cls._prompts_file}: {e}")
                cls._prompts = {}
        return cls._prompts

    @classmethod
    def get_single_day_prompt(
        cls,
        city: str,
        temperature: float,
        weather: str,
        humidity: float,
        wind_direction: str,
        wind_power: str,
        date: str,
        day_of_week: str,
        gender: str | None,
        age: int | None,
        identity: str | None,
        style: str | None,
        temperature_sensitivity: str | None,
        activity_context: str | None,
        other_preferences: str | None,
    ) -> str:
        """
        Get formatted single-day recommendation prompt.

        Args:
            city: City name
            temperature: Temperature in Celsius
            weather: Weather condition
            humidity: Humidity percentage
            wind_direction: Wind direction
            wind_power: Wind power level
            date: Date string
            day_of_week: Day of week in Chinese
            gender: User gender
            age: User age
            identity: User identity
            style: User style preference
            temperature_sensitivity: User temperature sensitivity
            activity_context: User activity context
            other_preferences: Other user preferences

        Returns:
            Formatted prompt string
        """
        prompts = cls.load_prompts()
        template = prompts.get("single_day_recommendation", "")

        return template.format(
            city=city,
            temperature=temperature,
            weather=weather,
            humidity=humidity,
            wind_direction=wind_direction,
            wind_power=wind_power,
            date=date,
            day_of_week=day_of_week,
            gender=gender or "未提供",
            age=age or "未提供",
            identity=identity or "未提供",
            style=style or "未提供",
            temperature_sensitivity=temperature_sensitivity or "正常",
            activity_context=activity_context or "未提供",
            other_preferences=other_preferences or "无",
        )

    @classmethod
    def get_multi_day_prompt(
        cls,
        date_label: str,
        date_formatted: str,
        weekday_zh: str,
        gender: str | None,
        age: int | None,
        identity: str | None,
        style: str | None,
        temperature_sensitivity: str | None,
        activity_context: str | None,
        other_preferences: str | None,
        city: str,
        weather_text: str,
        temperature_high: float,
        temperature_low: float,
        wind_direction: str,
        wind_power: str,
        temperature_adjustment: str,
    ) -> str:
        """
        Get formatted multi-day recommendation prompt.

        Args:
            date_label: Date label (今天, 明天, 后天)
            date_formatted: Formatted date string
            weekday_zh: Weekday in Chinese
            gender: User gender
            age: User age
            identity: User identity
            style: User style preference
            temperature_sensitivity: User temperature sensitivity
            activity_context: User activity context
            other_preferences: Other user preferences
            city: City name
            weather_text: Weather description
            temperature_high: High temperature
            temperature_low: Low temperature
            wind_direction: Wind direction
            wind_power: Wind power level
            temperature_adjustment: Temperature adjustment suggestion

        Returns:
            Formatted prompt string
        """
        prompts = cls.load_prompts()
        template = prompts.get("multi_day_recommendation", "")

        return template.format(
            date_label=date_label,
            date_formatted=date_formatted,
            weekday_zh=weekday_zh,
            gender=gender or "未知",
            age=age or "未知",
            identity=identity or "未知",
            style=style or "未知",
            temperature_sensitivity=temperature_sensitivity or "正常",
            activity_context=activity_context or "日常",
            other_preferences=other_preferences or "无",
            city=city,
            weather_text=weather_text,
            temperature_high=temperature_high,
            temperature_low=temperature_low,
            wind_direction=wind_direction,
            wind_power=wind_power,
            temperature_adjustment=temperature_adjustment,
        )

    @classmethod
    def get_temperature_adjustment(cls, temperature_sensitivity: str | None) -> str:
        """
        Get temperature adjustment suggestion based on user sensitivity.

        Args:
            temperature_sensitivity: User's temperature sensitivity

        Returns:
            Temperature adjustment suggestion
        """
        prompts = cls.load_prompts()
        adjustments = prompts.get("temperature_adjustments", {})

        if temperature_sensitivity in adjustments:
            return adjustments[temperature_sensitivity]
        return adjustments.get("default", "根据实际体感调整")

    @classmethod
    def get_weekday_zh(cls, weekday_en: str) -> str:
        """
        Get Chinese weekday name from English weekday.

        Args:
            weekday_en: English weekday name (Monday, Tuesday, etc.)

        Returns:
            Chinese weekday name
        """
        prompts = cls.load_prompts()
        weekdays = prompts.get("weekdays", {})
        return weekdays.get(weekday_en, weekday_en)

    @classmethod
    def get_fallback_recommendation(cls, temperature: float) -> dict[str, Any]:
        """
        Get fallback recommendation based on temperature.

        Args:
            temperature: Temperature in Celsius

        Returns:
            Dictionary with clothing, advice, and emoji
        """
        prompts = cls.load_prompts()
        fallbacks = prompts.get("fallback_recommendations", {})

        if temperature < 5:
            category = "very_cold"
        elif temperature < 15:
            category = "cold"
        elif temperature < 25:
            category = "mild"
        else:
            category = "hot"

        fallback = fallbacks.get(category, fallbacks.get("mild", {}))

        return {
            "clothing": fallback.get("clothing", []),
            "advice": fallback.get("advice", "").format(temperature=temperature),
            "emoji": fallback.get("emoji", "👔"),
        }

    @classmethod
    def get_weather_warnings(cls, weather: str) -> list[str]:
        """
        Get weather-specific warnings.

        Args:
            weather: Weather condition string

        Returns:
            List of warning messages
        """
        prompts = cls.load_prompts()
        warnings_config = prompts.get("weather_warnings", {})
        warnings = []

        if "雨" in weather and "rain" in warnings_config:
            warnings.append(warnings_config["rain"])
        if "雾" in weather or "霾" in weather:
            if "fog" in warnings_config:
                warnings.append(warnings_config["fog"])
            elif "haze" in warnings_config:
                warnings.append(warnings_config["haze"])

        return warnings
