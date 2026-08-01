"""Recommendation service for AI-powered AI Recommendations."""

import hashlib
import logging
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.recommendation import CostLog, Recommendation
from app.models.user import User
from app.schemas.recommendation import (
    DailyRecommendation,
    MultiDayRecommendationResponse,
    RecommendationOutput,
    RecommendationResponse,
    UserBasicInfo,
    WeatherSnapshot,
)
from app.schemas.weather import WeatherData
from app.services.cache_service import CacheService
from app.services.city_service import CityService
from app.services.llm.provider_factory import LLMProviderFactory
from app.services.prompt_service import PromptService
from app.services.weather.provider_factory import WeatherProviderFactory
from app.services.weather.weather_helper import WeatherHelper

logger = logging.getLogger(__name__)

# Initialize cache service for recommendations
recommendation_cache = CacheService(ttl=settings.RECOMMENDATION_CACHE_TTL)


class RecommendationService:
    """Service for generating and managing AI Recommendations."""

    def __init__(self, db: Session):
        self.db = db

    async def generate_recommendation(
        self, user: User, city: str, date: str | None = None
    ) -> RecommendationResponse:
        """
        Generate a personalized dress recommendation for the user.

        Args:
            user: The user requesting the recommendation
            city: City name or AD code
            date: Optional date (defaults to today)

        Returns:
            RecommendationResponse with clothing items and advice

        Raises:
            ValueError: If profile is incomplete or city not found
            HTTPException: If LLM or weather API fails
        """
        # Use today's date if not provided
        if not date:
            date = datetime.now().date().isoformat()

        # Fetch weather data
        weather_data = await self._fetch_weather(city)
        if not weather_data:
            raise ValueError(f"Unable to fetch weather data for city: {city}")

        # Check cache
        cache_key = self._build_cache_key(user.id, date, weather_data)
        cached = recommendation_cache.get(cache_key)
        if cached:
            logger.info(f"Cache hit for user={user.id}, city={city}, date={date}")
            cached["cached"] = True
            return RecommendationResponse(**cached)

        # Generate new recommendation
        logger.info(
            f"Cache miss - generating recommendation for user={user.id}, city={city}"
        )

        # Build prompt
        prompt = self._build_prompt(user, weather_data, date)

        # Call LLM
        llm_provider = LLMProviderFactory.get_provider(
            provider_type=settings.LLM_PROVIDER,
            base_url=settings.LLM_BASE_URL,
            api_key=settings.LLM_API_KEY,
            model=settings.LLM_MODEL,
            verify_ssl=settings.LLM_VERIFY_SSL,
            timeout=settings.LLM_TIMEOUT,
        )

        try:
            llm_response: RecommendationOutput = await llm_provider.generate_completion(
                prompt=prompt,
                response_model=RecommendationOutput,
                max_retries=3,
                temperature=0.7,
            )
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            # Fallback to generic recommendation
            llm_response = self._generate_fallback_recommendation(weather_data)

        # Save to database
        recommendation = Recommendation(
            user_id=user.id,
            city=weather_data.city,
            weather_data=weather_data.model_dump(),
            prompt=prompt,
            response=llm_response.model_dump(),
            cost_estimate=None,  # Calculate if tokens available
            tokens_used=None,
            created_at=datetime.utcnow(),
        )
        self.db.add(recommendation)
        self.db.commit()
        self.db.refresh(recommendation)

        # Log cost (placeholder - actual cost calculation would use token count)
        self._log_cost(user.id, recommendation.id, 0, 0)

        # Build response
        response_data = {
            "id": recommendation.id,
            "user_id": user.id,
            "city": weather_data.city,
            "weather_data": weather_data.model_dump(),
            "clothing_items": llm_response.clothing_items,
            "advice": llm_response.advice,
            "weather_warnings": llm_response.weather_warnings,
            "emoji_summary": llm_response.emoji_summary,
            "cached": False,
            "cost_estimate": recommendation.cost_estimate,
            "created_at": recommendation.created_at,
        }

        # Cache the result
        recommendation_cache.set(cache_key, response_data)

        return RecommendationResponse(**response_data)

    async def generate_multi_day(
        self,
        user: User,
        city: str,
        days: int = 3,
    ) -> MultiDayRecommendationResponse:
        """
        Generate N-day AI Recommendations for the current user (1-3 days).

        Args:
            user: The user requesting recommendations
            city: City AD code

        Returns:
            MultiDayRecommendationResponse with 3 days of recommendations

        Raises:
            ValueError: If profile is incomplete or city not found
        """
        days = max(1, min(int(days), 3))
        logger.info(
            f"Generating {days}-day recommendations for user={user.id}, city={city}"
        )

        # Get multi-day weather forecast
        weather_helper = WeatherHelper(self.db)
        try:
            forecasts = await weather_helper.get_forecast(city, days=days)
            logger.info(
                f"✅ Fetched {len(forecasts)} day(s) of weather forecast for city {city}"
            )
            for i, forecast in enumerate(forecasts):
                logger.debug(
                    f"  Day {i+1}: {forecast['date_label']} - {forecast['weather_text']}, {forecast['temperature_low']}°C - {forecast['temperature_high']}°C"
                )
        except Exception as e:
            logger.error(f"Failed to fetch 3-day forecast: {e}")
            raise ValueError(f"Unable to fetch weather forecast for city {city}")

        # Get city name
        city_obj = CityService.get_by_ad_code(self.db, city)
        # City model does not have `name`; use display_name / location_name_zh with fallback
        city_name = (
            (city_obj.display_name if city_obj else None)
            or (city_obj.location_name_zh if city_obj else None)
            or city
        )

        daily_recommendations = []
        today = date.today()

        for i, forecast_data in enumerate(forecasts):
            forecast_date = today + timedelta(days=i)
            date_label = forecast_data["date_label"]

            # Build prompt for this day
            prompt = self._build_multi_day_prompt(
                user=user,
                forecast=forecast_data,
                date_label=date_label,
                forecast_date=forecast_date,
            )

            # Call LLM
            llm_provider = LLMProviderFactory.get_provider(
                provider_type=settings.LLM_PROVIDER,
                base_url=settings.LLM_BASE_URL,
                api_key=settings.LLM_API_KEY,
                model=settings.LLM_MODEL,
                verify_ssl=settings.LLM_VERIFY_SSL,
                timeout=settings.LLM_TIMEOUT,
            )

            try:
                llm_response: RecommendationOutput = (
                    await llm_provider.generate_completion(
                        prompt=prompt,
                        response_model=RecommendationOutput,
                        max_retries=3,
                        temperature=0.7,
                    )
                )
            except Exception as e:
                logger.error(f"LLM generation failed for {date_label}: {e}")
                # Use fallback
                llm_response = RecommendationOutput(
                    clothing_items=["根据天气选择合适的衣物"],
                    advice=f"{date_label}天气{forecast_data['weather_text']}，温度{forecast_data['temperature_low']}°C-{forecast_data['temperature_high']}°C，请注意保暖。",
                    weather_warnings=None,
                    emoji_summary="👔🧥",
                )

            # Save to database
            recommendation = Recommendation(
                user_id=user.id,
                city=city_name,
                forecast_date=forecast_date,
                weather_data=forecast_data,
                prompt=prompt,
                response=llm_response.model_dump(),
                cost_estimate=None,
                tokens_used=None,
                created_at=datetime.utcnow(),
            )
            self.db.add(recommendation)
            self.db.flush()  # Get the ID without committing

            # Build recommendation response
            rec_response = RecommendationResponse(
                id=recommendation.id,
                user_id=user.id,
                city=city_name,
                weather_data=forecast_data,
                clothing_items=llm_response.clothing_items,
                advice=llm_response.advice,
                weather_warnings=llm_response.weather_warnings,
                emoji_summary=llm_response.emoji_summary,
                cached=False,
                cost_estimate=None,
                created_at=recommendation.created_at,
            )

            # Build weather summary
            weather_summary = f"{forecast_data['weather_text']}，{forecast_data['temperature_low']}°C - {forecast_data['temperature_high']}°C"

            daily_recommendations.append(
                DailyRecommendation(
                    date=forecast_date.isoformat(),
                    date_label=date_label,
                    recommendation=rec_response,
                    weather_summary=weather_summary,
                )
            )

        self.db.commit()

        logger.info(
            f"✅ Successfully generated {len(daily_recommendations)} day(s) of recommendations for user {user.id}"
        )

        response = MultiDayRecommendationResponse(
            user=UserBasicInfo(id=user.id, email=user.email, full_name=user.full_name),
            city=city_name,
            city_code=city,
            recommendations=daily_recommendations,
            email_sent=False,
            generated_at=datetime.utcnow(),
        )

        logger.debug(
            f"📦 MultiDayRecommendationResponse: {len(response.recommendations)} recommendations"
        )
        return response

    async def generate_for_user_multi_day(
        self, target_user: User, city_code: str, days: int = 3
    ) -> list[Recommendation]:
        """
        Generate multi-day recommendations for a specific user.

        This method is for admin use to generate recommendations on behalf of other users.

        Args:
            target_user: The user to generate recommendations for
            city_code: 6-digit city AD code
            days: Number of days to generate (default 3, max 4)

        Returns:
            List of Recommendation objects (one per day)

        Raises:
            ValueError: If user profile incomplete or city invalid
            Exception: If weather fetch or LLM generation fails
        """
        logger.info(
            f"Admin generating {days}-day recommendations for user {target_user.id} (city: {city_code})"
        )

        # Get multi-day weather forecast
        weather_helper = WeatherHelper(self.db)
        try:
            forecasts = await weather_helper.get_forecast(city_code, days=days)
        except Exception as e:
            logger.error(f"Failed to fetch {days}-day forecast: {e}")
            raise ValueError(
                f"Unable to fetch weather forecast for city {city_code}"
            ) from e

        if not forecasts:
            raise ValueError(f"No forecast data available for city {city_code}")

        # Generate recommendations for each day
        recommendations = []
        today = datetime.now().date()

        for i, forecast in enumerate(forecasts):
            forecast_date = today + timedelta(days=i)
            date_label = forecast["date_label"]

            logger.info(f"Generating recommendation for {date_label} ({forecast_date})")

            # Build prompt with date context
            prompt = self._build_multi_day_prompt(
                user=target_user,
                forecast=forecast,
                date_label=date_label,
                forecast_date=forecast_date,
            )

            # Call LLM
            try:
                llm_provider = LLMProviderFactory.get_provider(
                    provider_type=settings.LLM_PROVIDER,
                    base_url=settings.LLM_BASE_URL,
                    api_key=settings.LLM_API_KEY,
                    model=settings.LLM_MODEL,
                    verify_ssl=settings.LLM_VERIFY_SSL,
                    timeout=settings.LLM_TIMEOUT,
                )

                result = await llm_provider.generate_completion(
                    prompt=prompt,
                    response_model=RecommendationOutput,
                    max_retries=3,
                    temperature=0.7,
                )

                # Estimate cost
                prompt_tokens = len(prompt) // 4  # Rough estimate
                completion_tokens = len(str(result)) // 4
                total_tokens = prompt_tokens + completion_tokens
                cost = (prompt_tokens * 0.001 + completion_tokens * 0.002) / 1000

                # Store recommendation
                rec = Recommendation(
                    user_id=target_user.id,
                    city=forecast["city"],
                    forecast_date=forecast_date,  # Set the forecast date
                    weather_data=forecast,
                    prompt=prompt,
                    response=result.dict(),
                    cost_estimate=cost,
                    tokens_used=total_tokens,
                )
                self.db.add(rec)
                recommendations.append(rec)

                logger.info(f"Generated recommendation for {date_label}: {rec.id}")

            except Exception as e:
                logger.error(f"Failed to generate recommendation for {date_label}: {e}")
                raise

        # Commit all recommendations
        self.db.commit()

        # Log total cost
        total_cost = sum(r.cost_estimate or 0 for r in recommendations)
        total_tokens = sum(r.tokens_used or 0 for r in recommendations)

        cost_log = CostLog(
            user_id=target_user.id,
            recommendation_id=None,  # Not linked to single recommendation
            model=settings.LLM_MODEL,
            prompt_tokens=0,  # Could track individually if needed
            completion_tokens=0,
            total_tokens=total_tokens,
            estimated_cost=total_cost,
        )
        self.db.add(cost_log)
        self.db.commit()

        logger.info(
            f"✅ Generated {len(recommendations)} recommendations for user {target_user.id}. "
            f"Total cost: ${total_cost:.4f}, tokens: {total_tokens}"
        )

        return recommendations

    def _build_multi_day_prompt(
        self, user: User, forecast: dict, date_label: str, forecast_date: date
    ) -> str:
        """
        Build prompt for multi-day recommendation with date context.

        Args:
            user: User profile
            forecast: Weather forecast dict with temperature, weather_text, etc.
            date_label: Chinese label ("今天", "明天", "后天")
            forecast_date: Date object for the forecast

        Returns:
            Formatted prompt string
        """
        # Get day of week
        weekday = forecast_date.strftime("%A")
        weekday_zh = PromptService.get_weekday_zh(weekday)
        temperature_adjustment = PromptService.get_temperature_adjustment(
            user.temperature_sensitivity
        )

        return PromptService.get_multi_day_prompt(
            date_label=date_label,
            date_formatted=forecast_date.strftime("%Y年%m月%d日"),
            weekday_zh=weekday_zh,
            gender=user.gender,
            age=user.age,
            identity=user.identity,
            style=user.style,
            temperature_sensitivity=user.temperature_sensitivity,
            activity_context=user.activity_context,
            other_preferences=user.other_preferences,
            city=forecast["city"],
            weather_text=forecast["weather_text"],
            temperature_high=forecast["temperature_high"],
            temperature_low=forecast["temperature_low"],
            wind_direction=forecast["wind_direction"],
            wind_power=forecast["wind_power"],
            temperature_adjustment=temperature_adjustment,
        )

    def _get_temperature_adjustment(self, user: User) -> str:
        """Get temperature adjustment text based on user sensitivity."""
        return PromptService.get_temperature_adjustment(user.temperature_sensitivity)

    async def _fetch_weather(self, city: str) -> WeatherData | None:
        """Fetch weather data for a city."""
        try:
            weather_provider = WeatherProviderFactory.create(
                provider_type=settings.WEATHER_PROVIDER,
                base_url=settings.WEATHER_BASE_URL,
                api_key=settings.WEATHER_API_KEY,
            )

            # Try to resolve city to AD code
            city_obj = CityService.get_by_ad_code(self.db, city)
            if not city_obj:
                # Try searching by name
                cities = CityService.search_cities(self.db, city, limit=1)
                if cities:
                    city_obj = cities[0]

            if not city_obj:
                logger.error(f"City not found: {city}")
                return None

            ad_code = city_obj.ad_code
            weather_data = await weather_provider.fetch_weather(
                ad_code, extensions="base"
            )
            return weather_data

        except Exception as e:
            logger.error(f"Failed to fetch weather: {e}")
            return None

    def _build_prompt(
        self, user: User, weather: WeatherData, date: str | None = None
    ) -> str:
        """Build the prompt for LLM."""
        # Handle date - default to today if not provided
        if date is None:
            date_obj = datetime.utcnow()
            date_str = date_obj.strftime("%Y-%m-%d")
        elif isinstance(date, str):
            date_obj = datetime.fromisoformat(date)
            date_str = date
        else:
            # If date is already a datetime object, use it directly
            date_obj = date
            date_str = date_obj.strftime("%Y-%m-%d")

        # Get day of week
        weekday = date_obj.strftime("%A")
        day_of_week = PromptService.get_weekday_zh(weekday)

        return PromptService.get_single_day_prompt(
            city=weather.city,
            temperature=weather.temperature_float,
            weather=weather.weather,
            humidity=weather.humidity_float,
            wind_direction=weather.wind_direction,
            wind_power=weather.wind_power,
            date=date_str,
            day_of_week=day_of_week,
            gender=user.gender,
            age=user.age,
            identity=user.identity,
            style=user.style,
            temperature_sensitivity=user.temperature_sensitivity,
            activity_context=user.activity_context,
            other_preferences=user.other_preferences,
        )

    def _generate_fallback_recommendation(
        self, weather: WeatherData
    ) -> RecommendationOutput:
        """Generate a fallback recommendation when LLM fails."""
        temp = weather.temperature_float
        fallback = PromptService.get_fallback_recommendation(temp)
        warnings = PromptService.get_weather_warnings(weather.weather)

        return RecommendationOutput(
            clothing_items=fallback["clothing"],
            advice=fallback["advice"],
            weather_warnings=warnings if warnings else None,
            emoji_summary=fallback["emoji"],
        )

    def _build_cache_key(self, user_id: int, date: str, weather: WeatherData) -> str:
        """Build a cache key for the recommendation."""
        # Hash weather conditions to detect significant changes
        weather_str = (
            f"{weather.temperature_float}|{weather.weather}|{weather.wind_power}"
        )
        weather_hash = hashlib.md5(weather_str.encode()).hexdigest()[:8]
        return f"recommendation:{user_id}:{date}:{weather_hash}"

    def _log_cost(
        self,
        user_id: int,
        recommendation_id: str,
        prompt_tokens: int,
        completion_tokens: int,
    ):
        """Log cost for monitoring."""
        # Placeholder cost calculation (adjust based on actual provider pricing)
        # DeepSeek example: ¥0.001/1K input tokens, ¥0.002/1K output tokens
        input_cost = (prompt_tokens / 1000) * 0.001
        output_cost = (completion_tokens / 1000) * 0.002
        total_cost = input_cost + output_cost

        cost_log = CostLog(
            user_id=user_id,
            recommendation_id=recommendation_id,
            model=settings.LLM_MODEL,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            estimated_cost=total_cost,
            created_at=datetime.utcnow(),
        )
        self.db.add(cost_log)
        self.db.commit()

    def get_user_recommendations(
        self,
        user_id: int,
        limit: int = 20,
        offset: int = 0,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> tuple[list[Recommendation], int]:
        """
        Get user's recommendation history.

        Args:
            user_id: User ID
            limit: Max results
            offset: Pagination offset
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Tuple of (recommendations list, total count)
        """
        # Lazy cleanup: delete recommendations older than 14 days
        cutoff_date = datetime.utcnow() - timedelta(days=14)
        self.db.query(Recommendation).filter(
            Recommendation.user_id == user_id, Recommendation.created_at < cutoff_date
        ).delete()
        self.db.commit()

        # Build query
        query = self.db.query(Recommendation).filter(Recommendation.user_id == user_id)

        if start_date:
            query = query.filter(
                Recommendation.created_at >= datetime.fromisoformat(start_date)
            )
        if end_date:
            query = query.filter(
                Recommendation.created_at <= datetime.fromisoformat(end_date)
            )

        total = query.count()
        recommendations = (
            query.order_by(Recommendation.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        return recommendations, total

    def get_recommendation_by_id(
        self, recommendation_id: str, user_id: int
    ) -> Recommendation | None:
        """Get a specific recommendation by ID (with ownership check)."""
        return (
            self.db.query(Recommendation)
            .filter(
                Recommendation.id == recommendation_id,
                Recommendation.user_id == user_id,
            )
            .first()
        )
