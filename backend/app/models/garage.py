from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class SpotType(StrEnum):
    COMPACT = "COMPACT"
    STANDARD = "STANDARD"
    EV = "EV"


class Garage(Base):
    __tablename__ = "garages"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))


class ParkingSpot(Base):
    __tablename__ = "parking_spots"
    __table_args__ = (UniqueConstraint("floor", "spot_number", name="uq_parking_spot_floor_number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    spot_number: Mapped[str] = mapped_column(String(30))
    floor: Mapped[int] = mapped_column(Integer, index=True)
    spot_type: Mapped[SpotType] = mapped_column(
        Enum(SpotType, create_constraint=True, name="spot_type_enum"), nullable=False, index=True
    )
    is_occupied: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    sessions = relationship("ParkingSession", back_populates="spot")
