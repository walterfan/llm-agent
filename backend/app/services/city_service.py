"""City lookup and search service."""

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.city import City
from app.schemas.city import CityDetail, CitySearchResult


class CityService:
    """Service for city lookup and search operations."""

    @staticmethod
    def search_cities(db: Session, query: str, limit: int = 20) -> list[City]:
        """
        Search cities by name (Chinese or English).

        Args:
            db: Database session
            query: Search query string
            limit: Maximum number of results

        Returns:
            List of matching cities
        """
        if not query or not query.strip():
            return []

        search_term = f"%{query.strip()}%"

        # Search in both Chinese and English names
        cities = (
            db.query(City)
            .filter(
                or_(
                    City.location_name_zh.like(search_term),
                    City.location_name_en.ilike(search_term),
                    City.city_zh.like(search_term),
                    City.city_en.ilike(search_term),
                )
            )
            .order_by(
                # Prioritize exact matches
                City.location_name_zh == query.strip(),
                City.location_name_en.ilike(query.strip()),
                City.location_name_zh,
            )
            .limit(limit)
            .all()
        )

        return cities

    @staticmethod
    def get_by_ad_code(db: Session, ad_code: str) -> City | None:
        """
        Get city by AD (Administrative Division) code.

        Args:
            db: Database session
            ad_code: 6-digit AD code

        Returns:
            City object or None if not found
        """
        return db.query(City).filter(City.ad_code == ad_code).first()

    @staticmethod
    def get_by_location_id(db: Session, location_id: str) -> City | None:
        """
        Get city by location ID.

        Args:
            db: Database session
            location_id: Location identifier

        Returns:
            City object or None if not found
        """
        return db.query(City).filter(City.location_id == location_id).first()

    @staticmethod
    def resolve_city_code(db: Session, city_input: str) -> str | None:
        """
        Resolve city name or code to AD code.

        Args:
            db: Database session
            city_input: City name (Chinese/English) or AD code

        Returns:
            AD code if found, None otherwise
        """
        # Check if input is already an AD code
        if city_input.isdigit() and len(city_input) == 6:
            city = CityService.get_by_ad_code(db, city_input)
            return city.ad_code if city else None

        # Search by name
        cities = CityService.search_cities(db, city_input, limit=1)
        if cities:
            return cities[0].ad_code

        return None

    @staticmethod
    def to_search_result(city: City) -> CitySearchResult:
        """
        Convert City model to CitySearchResult schema.

        Args:
            city: City model instance

        Returns:
            CitySearchResult schema
        """
        return CitySearchResult(
            location_id=city.location_id,
            location_name_zh=city.location_name_zh,
            location_name_en=city.location_name_en,
            ad_code=city.ad_code,
            province_zh=city.province_zh,
            city_zh=city.city_zh,
            display_name=city.display_name,
        )

    @staticmethod
    def to_detail(city: City) -> CityDetail:
        """
        Convert City model to CityDetail schema.

        Args:
            city: City model instance

        Returns:
            CityDetail schema
        """
        return CityDetail(
            location_id=city.location_id,
            location_name_zh=city.location_name_zh,
            location_name_en=city.location_name_en,
            ad_code=city.ad_code,
            province_zh=city.province_zh,
            province_en=city.province_en,
            city_zh=city.city_zh,
            city_en=city.city_en,
            latitude=city.latitude,
            longitude=city.longitude,
            timezone=city.timezone,
        )


# Singleton instance
city_service = CityService()
