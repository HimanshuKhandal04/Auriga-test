from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.parking import ClockRequest, ClockResponse
from app.services.parking import auto_close_expired_sessions

router = APIRouter()


@router.post("/clock", response_model=ClockResponse)
def clock(request: ClockRequest, db: Session = Depends(get_db)) -> ClockResponse:
    return auto_close_expired_sessions(db, request.current_time)