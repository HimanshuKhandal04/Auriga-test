from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, model_validator


class VehicleType(StrEnum):
    COMPACT = "COMPACT"
    STANDARD = "STANDARD"
    EV = "EV"


class CheckInRequest(BaseModel):
    license_plate: str
    vehicle_type: VehicleType


class CheckInResponse(BaseModel):
    session_id: int
    license_plate: str
    vehicle_type: VehicleType
    spot_number: str
    floor: int
    check_in: datetime


class CheckOutRequest(BaseModel):
    license_plate: Optional[str] = None
    session_id: Optional[int] = None

    @model_validator(mode="after")
    def require_lookup_key(self) -> "CheckOutRequest":
        if self.session_id is None and self.license_plate is None:
            raise ValueError("Provide either license_plate or session_id")
        if self.session_id is not None and self.license_plate is not None:
            raise ValueError("Provide only one of license_plate or session_id")
        return self


class CheckOutResponse(BaseModel):
    license_plate: str
    spot_number: str
    check_in: datetime
    check_out: datetime
    billable_hours: int
    fee: Decimal


class ClockRequest(BaseModel):
    current_time: datetime


class AutoClosedSession(BaseModel):
    session_id: int
    license_plate: str
    fee: Decimal


class ClockResponse(BaseModel):
    closed_count: int
    closed_sessions: list[AutoClosedSession]


class TransferRequest(BaseModel):
    current_license_plate: str
    new_license_plate: str


class TransferResponse(BaseModel):
    session_id: int
    old_license_plate: str
    new_license_plate: str
    spot_number: str
    floor: int
    check_in: datetime
