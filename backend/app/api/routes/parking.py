from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import get_current_user
from app.models.parking import SessionStatus
from app.schemas.lookup import ParkingSessionItem, ParkingSessionListResponse
from app.schemas.parking import (
    CheckInRequest,
    CheckInResponse,
    CheckOutRequest,
    CheckOutResponse,
    TransferRequest,
    TransferResponse,
)
from app.services.lookup import list_sessions, search_sessions
from app.services.parking import check_in_vehicle, check_out_vehicle, transfer_active_session

router = APIRouter()


@router.get("/search", response_model=ParkingSessionListResponse[ParkingSessionItem])
def search(
    plate: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> ParkingSessionListResponse[ParkingSessionItem]:
    return search_sessions(db, plate, page, page_size)


@router.get("/active", response_model=ParkingSessionListResponse[ParkingSessionItem])
def active(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: str = Query("check_in"),
    order: str = Query("asc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
) -> ParkingSessionListResponse[ParkingSessionItem]:
    return list_sessions(db, SessionStatus.ACTIVE, page, page_size, sort, order)


@router.get("/history", response_model=ParkingSessionListResponse[ParkingSessionItem])
def history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: str = Query("check_in"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
) -> ParkingSessionListResponse[ParkingSessionItem]:
    return list_sessions(db, SessionStatus.COMPLETED, page, page_size, sort, order)


@router.post("/check-in", response_model=CheckInResponse)
def check_in(request: CheckInRequest, db: Session = Depends(get_db)) -> CheckInResponse:
    return check_in_vehicle(db, request)


@router.post("/check-out", response_model=CheckOutResponse)
def check_out(request: CheckOutRequest, db: Session = Depends(get_db)) -> CheckOutResponse:
    return check_out_vehicle(db, request)


@router.post("/transfer", response_model=TransferResponse)
def transfer(
    request: TransferRequest,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
) -> TransferResponse:
    return transfer_active_session(db, request)
