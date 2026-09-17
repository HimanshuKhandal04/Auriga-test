from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Optional

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, Numeric, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.garage import SpotType


class SessionStatus(StrEnum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"


class ParkingSession(Base):
    __tablename__ = "parking_sessions"
    __table_args__ = (
        CheckConstraint("fee IS NULL OR fee >= 0", name="ck_parking_session_fee_non_negative"),
        Index("ix_parking_sessions_license_plate_status", "license_plate", "status"),
        Index("ix_parking_sessions_spot_status", "spot_id", "status"),
        Index(
            "uq_parking_sessions_active_license_plate",
            "license_plate",
            unique=True,
            sqlite_where=text("status = 'ACTIVE'"),
        ),
        Index(
            "uq_parking_sessions_active_spot",
            "spot_id",
            unique=True,
            sqlite_where=text("status = 'ACTIVE'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    license_plate: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    vehicle_type: Mapped[SpotType] = mapped_column(
        Enum(SpotType, create_constraint=True, name="vehicle_type_enum"), nullable=False, index=True
    )
    spot_id: Mapped[int] = mapped_column(ForeignKey("parking_spots.id"), nullable=False, index=True)
    check_in: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    check_out: Mapped[Optional[datetime]] = mapped_column(DateTime)
    fee: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus, create_constraint=True, name="session_status_enum"),
        nullable=False,
        default=SessionStatus.ACTIVE,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    spot = relationship("ParkingSpot", back_populates="sessions")
