"""City model for Chinese city data."""

from sqlalchemy import Column, Float, Integer, String
from sqlalchemy.orm import declarative_base

from app.db.base import Base


class City(Base):
    """City model representing Chinese administrative divisions."""

    __tablename__ = "cities"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    location_id = Column(String(20), unique=True, nullable=False, index=True)
    location_name_zh = Column(String(100), nullable=False, index=True)
    location_name_en = Column(String(100), nullable=True)
    ad_code = Column(String(10), unique=True, nullable=False, index=True)
    province_zh = Column(String(50), nullable=True)
    province_en = Column(String(50), nullable=True)
    city_zh = Column(String(50), nullable=True)
    city_en = Column(String(50), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    timezone = Column(String(50), nullable=True)

    def __repr__(self) -> str:
        """String representation of City."""
        return f"<City {self.location_name_zh} ({self.ad_code})>"

    @property
    def display_name(self) -> str:
        """Generate display name for disambiguation."""
        if self.province_zh and self.city_zh:
            return f"{self.location_name_zh} ({self.province_zh})"
        elif self.province_zh:
            return f"{self.location_name_zh} ({self.province_zh})"
        return self.location_name_zh
