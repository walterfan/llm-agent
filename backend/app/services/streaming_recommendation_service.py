"""Streaming recommendation service."""

import json
import logging
from datetime import date as dt_date
from typing import AsyncIterator

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.recommendation import Recommendation
from app.models.user import User
from app.schemas.streaming import (
    StreamDataEvent,
    StreamDoneEvent,
    StreamErrorEvent,
    StreamStartEvent,
    StreamTokenEvent,
)
from app.services.city_service import CityService
from app.services.llm.provider_factory import LLMProviderFactory
from app.services.recommendation_service import RecommendationService
from app.services.weather.provider_factory import WeatherProviderFactory
from app.services.weather.weather_helper import WeatherHelper

logger = logging.getLogger(__name__)


class StreamingRecommendationService:
    """Service for generating streaming AI Recommendations."""

    def __init__(self, db: Session):
        self.db = db
        self.recommendation_service = RecommendationService(db)
        # CityService uses static methods, no need to instantiate
        self.llm_provider = LLMProviderFactory.get_provider(
            provider_type=settings.LLM_PROVIDER,
            base_url=settings.LLM_BASE_URL,
            api_key=settings.LLM_API_KEY,
            model=settings.LLM_MODEL,
            verify_ssl=settings.LLM_VERIFY_SSL,
            timeout=settings.LLM_TIMEOUT,
        )
        self.weather_provider = WeatherProviderFactory.create(
            provider_type=settings.WEATHER_PROVIDER,
            base_url=settings.WEATHER_BASE_URL,
            api_key=settings.WEATHER_API_KEY,
        )

    async def generate_recommendation_stream(
        self, user: User, city: str, date: str | None = None
    ) -> AsyncIterator[str]:
        """
        Generate a streaming dress recommendation.

        Yields Server-Sent Events (SSE) formatted as:
            data: {"type": "start", "message": "..."}\n\n
            data: {"type": "token", "content": "建议"}\n\n
            data: {"type": "data", "field": "weather", "value": {...}}\n\n
            data: {"type": "done", "message": "..."}\n\n

        Args:
            user: The user requesting the recommendation
            city: City name or AD code
            date: Optional date (defaults to today)

        Yields:
            SSE-formatted event strings
        """
        try:
            # Send start event
            yield self._format_sse(
                StreamStartEvent(
                    message=f"正在为{user.full_name or '您'}生成穿衣建议..."
                )
            )

            # Step 1: Get weather data
            yield self._format_sse(
                StreamDataEvent(field="status", value="正在获取天气数据...")
            )

            # Resolve city to AD code
            city_obj = CityService.get_by_ad_code(self.db, city)
            if not city_obj:
                # Try searching by name
                cities = CityService.search_cities(self.db, city, limit=1)
                if cities:
                    city_obj = cities[0]
            if not city_obj:
                raise ValueError(f"城市 '{city}' 未找到")

            # Fetch weather
            weather_data = await self.weather_provider.fetch_weather(
                city_obj.ad_code, extensions="base"
            )

            # Send weather data
            yield self._format_sse(
                StreamDataEvent(
                    field="weather",
                    value={
                        "city": weather_data.city,
                        "temperature": weather_data.temperature_float,
                        "weather": weather_data.weather,
                        "humidity": weather_data.humidity_float,
                    },
                )
            )

            # Step 2: Build prompt
            prompt = self.recommendation_service._build_prompt(user, weather_data, date)

            yield self._format_sse(
                StreamDataEvent(field="status", value="正在生成AI推荐...")
            )

            # Step 3: Stream LLM response
            full_response = ""
            async for token in self.llm_provider.generate_completion_stream(
                prompt, temperature=0.7, max_tokens=500
            ):
                full_response += token
                yield self._format_sse(StreamTokenEvent(content=token))

            # Step 4: Parse and save recommendation (best effort)
            try:
                # Try to extract structured data from the response
                # This is a simplified version - you might want more robust parsing
                recommendation_id = await self._save_recommendation(
                    user, city_obj.ad_code, weather_data, prompt, full_response
                )

                yield self._format_sse(
                    StreamDoneEvent(
                        message="推荐生成完成！", recommendation_id=recommendation_id
                    )
                )

            except Exception as e:
                logger.warning(f"Failed to save streaming recommendation: {e}")
                yield self._format_sse(
                    StreamDoneEvent(message="推荐生成完成（未保存）")
                )

        except ValueError as e:
            logger.error(f"Validation error in streaming: {e}")
            yield self._format_sse(StreamErrorEvent(message=str(e)))

        except Exception as e:
            logger.error(f"Error in streaming recommendation: {e}")
            yield self._format_sse(
                StreamErrorEvent(message="抱歉，推荐服务暂时不可用，请稍后再试。")
            )

    async def generate_recommendation_stream_3days(
        self,
        user: User,
        city: str,
        days: int = 3,
    ) -> AsyncIterator[str]:
        """
        Generate a 3-day streaming dress recommendation (today/tomorrow/day-after) via SSE.

        This keeps the existing `/stream` endpoint single-day. The 3-day stream:
        - fetches multi-day forecast (extensions=all via WeatherHelper)
        - streams one day at a time in the same SSE connection

        Events:
        - start/status (data)
        - day (data): indicates which day the following tokens belong to
        - token: LLM tokens for that day
        - day_done (data): summary + saved recommendation id (best effort)
        - done: stream completed
        """
        try:
            yield self._format_sse(
                StreamStartEvent(
                    message=f"正在为{user.full_name or '您'}生成未来3天穿衣建议..."
                )
            )

            yield self._format_sse(
                StreamDataEvent(field="status", value="正在获取未来3天天气预报...")
            )

            # Resolve city to AD code
            city_obj = CityService.get_by_ad_code(self.db, city)
            if not city_obj:
                cities = CityService.search_cities(self.db, city, limit=1)
                if cities:
                    city_obj = cities[0]
            if not city_obj:
                raise ValueError(f"城市 '{city}' 未找到")

            days = max(1, min(int(days), 3))

            # Fetch N-day forecast via WeatherHelper (uses extensions="all")
            forecasts = await WeatherHelper(self.db).get_forecast(
                city_obj.ad_code, days=days
            )
            if not forecasts:
                raise ValueError(f"城市 '{city_obj.ad_code}' 没有可用的天气预报数据")

            city_display = (
                getattr(city_obj, "display_name", None)
                or getattr(city_obj, "location_name_zh", None)
                or city_obj.ad_code
            )

            yield self._format_sse(
                StreamDataEvent(
                    field="forecast",
                    value={
                        "city": city_display,
                        "ad_code": city_obj.ad_code,
                        "days": len(forecasts),
                    },
                )
            )

            recommendation_ids: list[str] = []

            # Stream each day sequentially
            for day_index, forecast in enumerate(forecasts):
                date_label = forecast.get("date_label", f"+{day_index}天")
                forecast_date = forecast.get("date") or (dt_date.today().isoformat())

                yield self._format_sse(
                    StreamDataEvent(
                        field="status", value=f"正在生成{date_label}推荐..."
                    )
                )

                # Mark day boundary so the client can group subsequent tokens
                yield self._format_sse(
                    StreamDataEvent(
                        field="day",
                        value={
                            "index": day_index,
                            "date": forecast_date,
                            "label": date_label,
                            "weather_text": forecast.get("weather_text"),
                            "temperature_low": forecast.get("temperature_low"),
                            "temperature_high": forecast.get("temperature_high"),
                        },
                    )
                )

                # Build multi-day prompt for this day and stream tokens
                prompt = self.recommendation_service._build_multi_day_prompt(
                    user=user,
                    forecast=forecast,
                    date_label=date_label,
                    forecast_date=dt_date.fromisoformat(forecast_date),
                )

                full_response = ""
                async for token in self.llm_provider.generate_completion_stream(
                    prompt,
                    temperature=0.7,
                    max_tokens=700,
                ):
                    full_response += token
                    yield self._format_sse(StreamTokenEvent(content=token))

                # Best-effort save for this day (raw text)
                saved_id: str | None = None
                try:
                    saved_id = await self._save_recommendation_from_forecast(
                        user=user,
                        city_display=city_display,
                        city_ad_code=city_obj.ad_code,
                        forecast=forecast,
                        prompt=prompt,
                        response_text=full_response,
                    )
                    recommendation_ids.append(saved_id)
                except Exception as e:
                    logger.warning(
                        f"Failed to save 3-day streaming recommendation ({date_label}): {e}"
                    )

                yield self._format_sse(
                    StreamDataEvent(
                        field="day_done",
                        value={
                            "index": day_index,
                            "label": date_label,
                            "recommendation_id": saved_id,
                        },
                    )
                )

            # Provide list of IDs (if any) and finish
            if recommendation_ids:
                yield self._format_sse(
                    StreamDataEvent(
                        field="recommendation_ids", value=recommendation_ids
                    )
                )

            yield self._format_sse(StreamDoneEvent(message="未来3天推荐生成完成！"))

        except ValueError as e:
            logger.error(f"Validation error in 3-day streaming: {e}")
            yield self._format_sse(StreamErrorEvent(message=str(e)))
        except Exception as e:
            logger.error(f"Error in 3-day streaming recommendation: {e}")
            yield self._format_sse(
                StreamErrorEvent(message="抱歉，推荐服务暂时不可用，请稍后再试。")
            )

    def _format_sse(
        self,
        event: (
            StreamStartEvent
            | StreamTokenEvent
            | StreamDataEvent
            | StreamErrorEvent
            | StreamDoneEvent
        ),
    ) -> str:
        """Format an event as Server-Sent Event."""
        return f"data: {event.model_dump_json()}\n\n"

    async def _save_recommendation_from_forecast(
        self,
        user: User,
        city_display: str,
        city_ad_code: str,
        forecast: dict,
        prompt: str,
        response_text: str,
    ) -> str:
        """
        Save a 3-day streaming recommendation for a single day using forecast dict.

        Stores raw response text (best-effort). Structured parsing can be added later.
        """
        # Forecast date is already included in forecast dict from WeatherHelper
        forecast_date_str = forecast.get("date")
        forecast_date = (
            dt_date.fromisoformat(forecast_date_str) if forecast_date_str else None
        )

        recommendation = Recommendation(
            user_id=user.id,
            city=city_display,
            forecast_date=forecast_date,
            weather_data=forecast,
            prompt=prompt,
            response={
                "raw_text": response_text,
                "clothing_items": [],
                "advice": response_text,
            },
            cost_estimate=None,
            tokens_used=None,
        )

        self.db.add(recommendation)
        self.db.commit()
        self.db.refresh(recommendation)
        return recommendation.id

    async def _save_recommendation(
        self,
        user: User,
        city_ad_code: str,
        weather_data,
        prompt: str,
        response_text: str,
    ) -> str:
        """
        Save streaming recommendation to database.

        Args:
            user: User who requested the recommendation
            city_ad_code: City AD code
            weather_data: Weather data
            prompt: The prompt sent to LLM
            response_text: Full LLM response text

        Returns:
            Recommendation ID
        """
        import uuid
        from datetime import datetime

        from app.models.recommendation import Recommendation

        # Create a simple structured response from the text
        # In production, you might want more sophisticated parsing
        recommendation_id = str(uuid.uuid4())

        recommendation = Recommendation(
            id=recommendation_id,
            user_id=user.id,
            city=city_ad_code,
            weather_data=weather_data.model_dump(),
            prompt=prompt,
            response={
                "raw_text": response_text,
                "clothing_items": [],  # Would need parsing
                "advice": response_text,
                "generated_at": datetime.utcnow().isoformat(),
            },
            cost_estimate=None,
            tokens_used=None,
            created_at=datetime.utcnow(),
        )

        self.db.add(recommendation)
        self.db.commit()

        return recommendation_id
