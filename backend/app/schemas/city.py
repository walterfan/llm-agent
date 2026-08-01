"""City schemas for API requests and responses."""

from pydantic import BaseModel, ConfigDict, Field


class CityBase(BaseModel):
    """Base city schema with common fields."""

    location_id: str = Field(..., description="Unique location identifier")
    location_name_zh: str = Field(..., description="City name in Chinese")
    location_name_en: str | None = Field(None, description="City name in English")
    ad_code: str = Field(..., description="Administrative division code (6 digits)")
    province_zh: str | None = Field(None, description="Province name in Chinese")
    city_zh: str | None = Field(None, description="City name in Chinese (admin level)")


class CitySearchResult(CityBase):
    """City search result with display name."""

    display_name: str = Field(
        ..., description="Formatted display name for disambiguation"
    )

    model_config = ConfigDict(from_attributes=True)


class CityDetail(CityBase):
    """Detailed city information including coordinates."""

    province_en: str | None = Field(None, description="Province name in English")
    city_en: str | None = Field(None, description="City name in English")
    latitude: float | None = Field(None, description="Latitude coordinate")
    longitude: float | None = Field(None, description="Longitude coordinate")
    timezone: str | None = Field(None, description="Timezone (e.g., Asia/Shanghai)")

    model_config = ConfigDict(from_attributes=True)


class CitySearchResponse(BaseModel):
    """Response for city search endpoint."""

    cities: list[CitySearchResult] = Field(
        default_factory=list, description="List of matching cities"
    )
    total: int = Field(..., description="Total number of results")
