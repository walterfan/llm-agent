"""City search and lookup API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.city import CityDetail, CitySearchResponse, CitySearchResult
from app.services.city_service import city_service

router = APIRouter()


@router.get("/search", response_model=CitySearchResponse)
def search_cities(
    q: str = Query(..., min_length=1, description="Search query for city name"),
    limit: int = Query(20, ge=1, le=50, description="Maximum number of results"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CitySearchResponse:
    """
    Search cities by name (Chinese or English).

    Requires authentication.
    """
    cities = city_service.search_cities(db, q, limit=limit)

    results = [city_service.to_search_result(city) for city in cities]

    return CitySearchResponse(
        cities=results,
        total=len(results),
    )


@router.get("/{ad_code}", response_model=CityDetail)
def get_city_by_code(
    ad_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CityDetail:
    """
    Get city details by AD (Administrative Division) code.

    Requires authentication.
    """
    # Validate AD code format
    if not ad_code.isdigit() or len(ad_code) != 6:
        raise HTTPException(
            status_code=400,
            detail="Invalid AD code. Must be 6 digits.",
        )

    city = city_service.get_by_ad_code(db, ad_code)

    if not city:
        raise HTTPException(
            status_code=404,
            detail=f"City not found with AD code: {ad_code}",
        )

    return city_service.to_detail(city)
