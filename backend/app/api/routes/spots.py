from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.garage import SpotType
from app.schemas.lookup import EvAvailabilityResponse, ParkingSpotListResponse
from app.services.lookup import ev_availability, list_spots

router = APIRouter()


@router.get("", response_model=ParkingSpotListResponse)
def spots(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: str = Query("floor"),
    order: str = Query("asc", pattern="^(asc|desc)$"),
    spot_type: Optional[SpotType] = None,
    availability: Optional[bool] = None,
    db: Session = Depends(get_db),
) -> ParkingSpotListResponse:
    return list_spots(db, page, page_size, sort, order, spot_type, availability)


@router.get("/ev/availability", response_model=EvAvailabilityResponse)
def ev_spot_availability(db: Session = Depends(get_db)) -> EvAvailabilityResponse:
    return ev_availability(db)