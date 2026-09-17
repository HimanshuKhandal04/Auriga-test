from math import ceil
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import Integer, func, select
from sqlalchemy.orm import Session

from app.models.garage import ParkingSpot, SpotType
from app.models.parking import ParkingSession, SessionStatus
from app.schemas.lookup import (
    EvAvailabilityResponse,
    PaginationMetadata,
    ParkingSessionItem,
    ParkingSessionListResponse,
    ParkingSpotItem,
    ParkingSpotListResponse,
)

SESSION_SORT_FIELDS = {
    "check_in": ParkingSession.check_in,
    "license_plate": ParkingSession.license_plate,
    "vehicle_type": ParkingSession.vehicle_type,
    "spot": ParkingSpot.spot_number,
}

SPOT_SORT_FIELDS = {
    "spot_number": ParkingSpot.spot_number,
    "floor": ParkingSpot.floor,
    "spot_type": ParkingSpot.spot_type,
    "is_occupied": ParkingSpot.is_occupied,
    "created_at": ParkingSpot.created_at,
}


def search_sessions(db: Session, plate: str | None, page: int, page_size: int) -> ParkingSessionListResponse[ParkingSessionItem]:
    normalized_plate = plate.strip().upper() if plate is not None else None
    if plate is not None and not normalized_plate:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Plate cannot be empty")

    query = _session_query()
    count_query = _session_count_query()
    if normalized_plate:
        pattern = f"%{normalized_plate}%"
        query = query.where(ParkingSession.license_plate.ilike(pattern))
        count_query = count_query.where(ParkingSession.license_plate.ilike(pattern))

    total = db.scalar(count_query) or 0
    rows = db.execute(
        query.order_by(ParkingSession.check_in.desc(), ParkingSession.id.desc())
        .offset(_offset(page, page_size)).limit(page_size)
    ).all()
    return ParkingSessionListResponse(
        items=[_session_item(session, spot) for session, spot in rows],
        pagination=_metadata(page, page_size, total),
    )


def list_sessions(db: Session, session_status: SessionStatus, page: int, page_size: int, sort: str, order: str) -> ParkingSessionListResponse[ParkingSessionItem]:
    sort_column = _allowed_sort(SESSION_SORT_FIELDS, sort)
    query = _session_query().where(ParkingSession.status == session_status)
    count_query = _session_count_query().where(ParkingSession.status == session_status)
    total = db.scalar(count_query) or 0
    direction = sort_column.asc() if order == "asc" else sort_column.desc()
    tie_breaker = ParkingSession.id.asc() if order == "asc" else ParkingSession.id.desc()
    rows = db.execute(
        query.order_by(direction, tie_breaker).offset(_offset(page, page_size)).limit(page_size)
    ).all()
    return ParkingSessionListResponse(
        items=[_session_item(session, spot) for session, spot in rows],
        pagination=_metadata(page, page_size, total),
    )


def list_spots(db: Session, page: int, page_size: int, sort: str, order: str, spot_type: SpotType | None, availability: bool | None) -> ParkingSpotListResponse:
    sort_column = _allowed_sort(SPOT_SORT_FIELDS, sort)
    query = select(ParkingSpot)
    count_query = select(func.count()).select_from(ParkingSpot)
    if spot_type is not None:
        query = query.where(ParkingSpot.spot_type == spot_type)
        count_query = count_query.where(ParkingSpot.spot_type == spot_type)
    if availability is not None:
        occupied = not availability
        query = query.where(ParkingSpot.is_occupied.is_(occupied))
        count_query = count_query.where(ParkingSpot.is_occupied.is_(occupied))

    total = db.scalar(count_query) or 0
    direction = sort_column.asc() if order == "asc" else sort_column.desc()
    tie_breaker = ParkingSpot.id.asc() if order == "asc" else ParkingSpot.id.desc()
    spots = db.scalars(query.order_by(direction, tie_breaker).offset(_offset(page, page_size)).limit(page_size)).all()
    return ParkingSpotListResponse(
        items=[
            ParkingSpotItem(
                spot_id=spot.id,
                spot_number=spot.spot_number,
                floor=spot.floor,
                spot_type=spot.spot_type,
                is_occupied=spot.is_occupied,
                created_at=spot.created_at,
            )
            for spot in spots
        ],
        pagination=_metadata(page, page_size, total),
    )


def ev_availability(db: Session) -> EvAvailabilityResponse:
    total, occupied = db.execute(
        select(
            func.count(ParkingSpot.id),
                func.coalesce(func.sum(ParkingSpot.is_occupied.cast(Integer)), 0),
        ).where(ParkingSpot.spot_type == SpotType.EV)
    ).one()
    total, occupied = int(total), int(occupied)
    return EvAvailabilityResponse(
        total_ev_spots=total,
        occupied_ev_spots=occupied,
        available_ev_spots=total - occupied,
    )


def _session_query():
    return select(ParkingSession, ParkingSpot).join(ParkingSpot, ParkingSession.spot_id == ParkingSpot.id)


def _session_count_query():
    return select(func.count()).select_from(ParkingSession)


def _session_item(session: ParkingSession, spot: ParkingSpot) -> ParkingSessionItem:
    return ParkingSessionItem(
        session_id=session.id,
        license_plate=session.license_plate,
        vehicle_type=session.vehicle_type,
        spot_number=spot.spot_number,
        floor=spot.floor,
        check_in=session.check_in,
        check_out=session.check_out,
        fee=session.fee,
        status=session.status.value,
    )


def _allowed_sort(fields: dict[str, Any], requested: str) -> Any:
    if requested not in fields:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid sort field '{requested}'. Allowed fields: {', '.join(fields)}",
        )
    return fields[requested]


def _offset(page: int, page_size: int) -> int:
    return (page - 1) * page_size


def _metadata(page: int, page_size: int, total: int) -> PaginationMetadata:
    return PaginationMetadata(page=page, page_size=page_size, total=total, total_pages=ceil(total / page_size) if total else 0)