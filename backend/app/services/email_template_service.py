"""Email template service for rendering recommendation emails."""

import logging
from pathlib import Path
from typing import List

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.schemas.recommendation import RecommendationResponse

logger = logging.getLogger(__name__)

# Get templates directory
TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "emails"
jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)


class EmailTemplateService:
    """Service for rendering email templates."""

    @staticmethod
    def render_recommendation_email(
        user_name: str,
        city: str,
        date: str,
        weather: dict,
        recommendation: RecommendationResponse,
        unsubscribe_url: str | None = None,
    ) -> tuple[str, str]:
        """
        Render recommendation email template.

        Args:
            user_name: User's display name
            city: City name
            date: Date string (ISO format)
            weather: Weather data
            recommendation: Recommendation response
            unsubscribe_url: Optional unsubscribe URL

        Returns:
            Tuple of (html_body, text_body)
        """
        try:
            template = jinja_env.get_template("recommendation.html")
            html_body = template.render(
                user_name=user_name or "用户",
                city=city,
                date=date,
                weather={
                    "temperature": weather.get(
                        "temperature_float", weather.get("temperature", 0)
                    ),
                    "condition": weather.get("weather", ""),
                    "humidity": weather.get(
                        "humidity_float", weather.get("humidity", 0)
                    ),
                    "wind": f"{weather.get('wind_direction', '')}{weather.get('wind_power', '')}级",
                },
                recommendation={
                    "clothing_items": recommendation.clothing_items,
                    "advice": recommendation.advice,
                    "weather_warnings": recommendation.weather_warnings or [],
                    "emoji_summary": recommendation.emoji_summary,
                },
                unsubscribe_url=unsubscribe_url or "#",
            )

            # Generate plain text version
            text_body = EmailTemplateService._html_to_text(html_body)

            return html_body, text_body

        except Exception as e:
            logger.error(f"Failed to render email template: {e}")
            # Fallback to simple text email
            temp = weather.get("temperature_float", weather.get("temperature", 0))
            cond = weather.get("weather", "")
            humidity = weather.get("humidity_float", weather.get("humidity", 0))
            text_body = f"""
亲，

今日天气推荐 ({city}, {date})

天气：{temp}°C, {cond}
湿度：{humidity}%

推荐服装：
{chr(10).join('- ' + item for item in recommendation.clothing_items)}

建议：
{recommendation.advice}

{recommendation.emoji_summary}
"""
            return f"<pre>{text_body}</pre>", text_body

    @staticmethod
    def _html_to_text(html: str) -> str:
        """
        Convert HTML to plain text (simple implementation).

        Args:
            html: HTML content

        Returns:
            Plain text content
        """
        import re

        # Remove script and style elements
        html = re.sub(
            r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE
        )
        html = re.sub(
            r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE
        )

        # Convert common HTML tags to text
        html = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
        html = re.sub(r"<p[^>]*>", "\n", html, flags=re.IGNORECASE)
        html = re.sub(r"</p>", "\n", html, flags=re.IGNORECASE)
        html = re.sub(r"<li[^>]*>", "\n- ", html, flags=re.IGNORECASE)
        html = re.sub(r"</li>", "", html, flags=re.IGNORECASE)
        html = re.sub(r"<h[1-6][^>]*>", "\n", html, flags=re.IGNORECASE)
        html = re.sub(r"</h[1-6]>", "\n", html, flags=re.IGNORECASE)

        # Remove all remaining HTML tags
        text = re.sub(r"<[^>]+>", "", html)

        # Clean up whitespace
        text = re.sub(r"\n\s*\n", "\n\n", text)
        text = text.strip()

        return text

    @staticmethod
    def render_multi_day_recommendation_email(
        user_name: str,
        city: str,
        recommendations: List,  # List of DailyRecommendation objects
        unsubscribe_url: str | None = None,
    ) -> tuple[str, str]:
        """
        Render multi-day recommendation email template.

        Args:
            user_name: User's display name
            city: City name
            recommendations: List of DailyRecommendation objects
            unsubscribe_url: Optional unsubscribe URL

        Returns:
            Tuple of (html_body, text_body)
        """
        try:
            template = jinja_env.get_template("recommendation_multi_day.html")

            # Format recommendations for template
            daily_items = []
            for daily_rec in recommendations:
                # Handle both DailyRecommendation (from MultiDayRecommendationResponse)
                # and Recommendation models (from database)
                if hasattr(daily_rec, "recommendation"):
                    # DailyRecommendation object
                    rec = daily_rec.recommendation
                    weather_summary = daily_rec.weather_summary
                    # Parse weather summary to extract temperature
                    temp_parts = weather_summary.split("，") if weather_summary else []
                    temp_range = temp_parts[1] if len(temp_parts) > 1 else ""

                    daily_items.append(
                        {
                            "date": daily_rec.date,
                            "date_label": daily_rec.date_label,
                            "weather": {
                                "temperature_high": "",  # Not directly available in DailyRecommendation
                                "temperature_low": "",  # Not directly available in DailyRecommendation
                                "condition": temp_parts[0] if temp_parts else "",
                                "wind": "",  # Not directly available in DailyRecommendation
                                "summary": weather_summary,
                            },
                            "recommendation": {
                                "clothing_items": (
                                    rec.clothing_items
                                    if hasattr(rec, "clothing_items")
                                    else []
                                ),
                                "advice": rec.advice if hasattr(rec, "advice") else "",
                                "weather_warnings": (
                                    rec.weather_warnings
                                    if hasattr(rec, "weather_warnings")
                                    else []
                                ),
                                "emoji_summary": (
                                    rec.emoji_summary
                                    if hasattr(rec, "emoji_summary")
                                    else ""
                                ),
                            },
                        }
                    )
                else:
                    # Recommendation model from database
                    weather_data = (
                        daily_rec.weather_data
                        if hasattr(daily_rec, "weather_data")
                        else {}
                    )
                    response_data = (
                        daily_rec.response if hasattr(daily_rec, "response") else {}
                    )

                    daily_items.append(
                        {
                            "date": weather_data.get("date", ""),
                            "date_label": weather_data.get("date_label", ""),
                            "weather": {
                                "temperature_high": weather_data.get(
                                    "temperature_high", ""
                                ),
                                "temperature_low": weather_data.get(
                                    "temperature_low", ""
                                ),
                                "condition": weather_data.get("weather_text", ""),
                                "wind": weather_data.get("wind_direction", ""),
                                "summary": "",
                            },
                            "recommendation": {
                                "clothing_items": response_data.get(
                                    "clothing_items", []
                                ),
                                "advice": response_data.get("advice", ""),
                                "weather_warnings": response_data.get(
                                    "weather_warnings"
                                )
                                or [],
                                "emoji_summary": response_data.get("emoji_summary", ""),
                            },
                        }
                    )

            html_body = template.render(
                user_name=user_name or "用户",
                city=city,
                daily_recommendations=daily_items,
                unsubscribe_url=unsubscribe_url or "#",
            )

            # Generate plain text version
            text_body = EmailTemplateService._html_to_text(html_body)

            return html_body, text_body

        except Exception as e:
            logger.error(f"Failed to render multi-day email template: {e}")
            # Fallback to simple text email
            text_body = f"""
亲，

您好！这是您未来三天在{city}的穿衣建议：

"""
            for rec in recommendations:
                weather_data = rec.weather_data
                response_data = rec.response
                text_body += f"""
{weather_data.get('date_label', '')}（{weather_data.get('date', '')}）：
天气：{weather_data.get('weather_text', '')}
温度：{weather_data.get('temperature_low', '')}°C - {weather_data.get('temperature_high', '')}°C

建议穿着：
{', '.join(response_data.get('clothing_items', []))}

{response_data.get('advice', '')}

---
"""

            text_body += """
祝您生活愉快！

---
MCP Weather Server
退订邮件通知，请访问：{unsubscribe_url or '#'}
"""
            return text_body, text_body
