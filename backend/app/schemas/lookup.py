from datetime import datetime
from decimal import Decimal
from typing import Generic, TypeVar

from pydantic import BaseModel

from app.models.garage import SpotType

ItemT = TypeVar("ItemT")


class PaginationMetadata(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


class ParkingSessionItem(BaseModel):
    session_id: int
    license_plate: str
    vehicle_type: SpotType
    spot_number: str
    floor: int
    check_in: datetime
    check_out: datetime | None
    fee: Decimal | None
    status: str


class ParkingSessionListResponse(BaseModel, Generic[ItemT]):
    items: list[ItemT]
    pagination: PaginationMetadata


class ParkingSpotItem(BaseModel):
    spot_id: int
    spot_number: str
    floor: int
    spot_type: SpotType
    is_occupied: bool
    created_at: datetime


class ParkingSpotListResponse(BaseModel):
    items: list[ParkingSpotItem]
    pagination: PaginationMetadata


class EvAvailabilityResponse(BaseModel):
    total_ev_spots: int
    occupied_ev_spots: int
    available_ev_spots: int