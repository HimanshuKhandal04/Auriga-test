from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.garage import ParkingSpot, SpotType
from app.models.parking import ParkingSession, SessionStatus
from app.schemas.parking import (
	AutoClosedSession,
	CheckInRequest,
	CheckInResponse,
	CheckOutRequest,
	CheckOutResponse,
	ClockResponse,
	TransferRequest,
	TransferResponse,
)
from app.services.billing import RateCardError, as_utc, calculate_fee, load_configured_rate_card


def check_in_vehicle(db: Session, request: CheckInRequest) -> CheckInResponse:
	license_plate = request.license_plate.strip().upper()
	if not license_plate:
		raise HTTPException(
			status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
			detail="License plate cannot be empty",
		)

	vehicle_type = SpotType(request.vehicle_type.value)
	compatible_types = {
		SpotType.EV: (SpotType.EV,),
		SpotType.STANDARD: (SpotType.STANDARD,),
		SpotType.COMPACT: (SpotType.COMPACT, SpotType.STANDARD),
	}[vehicle_type]

	try:
		with db.begin():
			active_session = db.scalar(
				select(ParkingSession.id)
				.where(
					ParkingSession.license_plate == license_plate,
					ParkingSession.status == SessionStatus.ACTIVE,
				)
				.limit(1)
			)
			if active_session is not None:
				raise HTTPException(
					status_code=status.HTTP_409_CONFLICT,
					detail="This vehicle already has an active parking session",
				)

			spots = db.scalars(
				select(ParkingSpot)
				.where(
					ParkingSpot.is_occupied.is_(False),
					ParkingSpot.spot_type.in_(compatible_types),
				)
				.order_by(ParkingSpot.floor, ParkingSpot.spot_number, ParkingSpot.id)
			).all()

			selected_spot = None
			for spot in spots:
				claimed = db.execute(
					update(ParkingSpot)
					.where(
						ParkingSpot.id == spot.id,
						ParkingSpot.is_occupied.is_(False),
					)
					.values(is_occupied=True)
				)
				if claimed.rowcount == 1:
					selected_spot = spot
					break

			if selected_spot is None:
				raise HTTPException(
					status_code=status.HTTP_409_CONFLICT,
					detail="No compatible parking spot is available",
				)

			check_in = datetime.now(timezone.utc)
			parking_session = ParkingSession(
				license_plate=license_plate,
				vehicle_type=vehicle_type,
				spot_id=selected_spot.id,
				check_in=check_in,
				status=SessionStatus.ACTIVE,
			)
			db.add(parking_session)
			db.flush()

			return CheckInResponse(
				session_id=parking_session.id,
				license_plate=license_plate,
				vehicle_type=request.vehicle_type,
				spot_number=selected_spot.spot_number,
				floor=selected_spot.floor,
				check_in=check_in,
			)
	except IntegrityError as exc:
		raise HTTPException(
			status_code=status.HTTP_409_CONFLICT,
			detail="This vehicle already has an active parking session",
		) from exc


def check_out_vehicle(db: Session, request: CheckOutRequest) -> CheckOutResponse:
	with db.begin():
		if request.session_id is not None:
			parking_session = db.scalar(
				select(ParkingSession).where(
					ParkingSession.id == request.session_id,
					ParkingSession.status == SessionStatus.ACTIVE,
				)
			)
		else:
			license_plate = (request.license_plate or "").strip().upper()
			if not license_plate:
				raise HTTPException(
					status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
					detail="License plate cannot be empty",
				)
			parking_session = db.scalar(
				select(ParkingSession).where(
					ParkingSession.license_plate == license_plate,
					ParkingSession.status == SessionStatus.ACTIVE,
				)
			)

		if parking_session is None:
			raise HTTPException(
				status_code=status.HTTP_404_NOT_FOUND,
				detail="No active parking session found",
			)

		spot = db.get(ParkingSpot, parking_session.spot_id)
		if spot is None:
			raise HTTPException(
				status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
				detail="Parking session refers to a missing spot",
			)

		check_out = datetime.now(timezone.utc)
		try:
			rate_card = load_configured_rate_card()
		except RateCardError as exc:
			raise HTTPException(
				status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
				detail=f"Parking rate card is not configured: {exc}",
			) from exc

		billable_hours, fee = calculate_fee(parking_session.check_in, check_out, rate_card)

		parking_session.check_out = check_out
		parking_session.fee = fee
		parking_session.status = SessionStatus.COMPLETED
		spot.is_occupied = False
		db.flush()

		return CheckOutResponse(
			license_plate=parking_session.license_plate,
			spot_number=spot.spot_number,
			check_in=parking_session.check_in,
			check_out=check_out,
			billable_hours=billable_hours,
			fee=fee,
		)


def auto_close_expired_sessions(db: Session, current_time: datetime) -> ClockResponse:
	checkout_time = as_utc(current_time)
	cutoff = checkout_time - timedelta(hours=24)

	with db.begin():
		active_sessions = db.scalars(
			select(ParkingSession)
			.where(ParkingSession.status == SessionStatus.ACTIVE)
			.with_for_update()
		).all()

		expired_sessions = [
			session for session in active_sessions if as_utc(session.check_in) < cutoff
		]
		if not expired_sessions:
			return ClockResponse(closed_count=0, closed_sessions=[])

		try:
			rate_card = load_configured_rate_card()
		except RateCardError as exc:
			raise HTTPException(
				status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
				detail=f"Parking rate card is not configured: {exc}",
			) from exc

		closed_sessions = []
		for parking_session in expired_sessions:
			spot = db.get(ParkingSpot, parking_session.spot_id)
			if spot is None:
				raise HTTPException(
					status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
					detail=f"Parking session {parking_session.id} refers to a missing spot",
				)

			_, fee = calculate_fee(parking_session.check_in, checkout_time, rate_card)
			parking_session.check_out = checkout_time
			parking_session.fee = fee
			parking_session.status = SessionStatus.COMPLETED
			spot.is_occupied = False
			closed_sessions.append(
				AutoClosedSession(
					session_id=parking_session.id,
					license_plate=parking_session.license_plate,
					fee=fee,
				)
			)

		db.flush()
		return ClockResponse(closed_count=len(closed_sessions), closed_sessions=closed_sessions)


def transfer_active_session(db: Session, request: TransferRequest) -> TransferResponse:
	current_license_plate = request.current_license_plate.strip().upper()
	new_license_plate = request.new_license_plate.strip().upper()
	if not current_license_plate or not new_license_plate:
		raise HTTPException(
			status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
			detail="License plates cannot be empty",
		)

	try:
		with db.begin():
			parking_session = db.scalar(
				select(ParkingSession)
				.where(
					ParkingSession.license_plate == current_license_plate,
					ParkingSession.status == SessionStatus.ACTIVE,
				)
				.with_for_update()
			)
			if parking_session is None:
				raise HTTPException(
					status_code=status.HTTP_404_NOT_FOUND,
					detail="No active parking session found for the current license plate",
				)

			another_active_session = db.scalar(
				select(ParkingSession.id)
				.where(
					ParkingSession.license_plate == new_license_plate,
					ParkingSession.status == SessionStatus.ACTIVE,
					ParkingSession.id != parking_session.id,
				)
				.limit(1)
			)
			if another_active_session is not None:
				raise HTTPException(
					status_code=status.HTTP_409_CONFLICT,
					detail="The new license plate already has an active parking session",
				)

			spot = db.get(ParkingSpot, parking_session.spot_id)
			if spot is None:
				raise HTTPException(
					status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
					detail="Parking session refers to a missing spot",
				)

			parking_session.license_plate = new_license_plate
			db.flush()
			return TransferResponse(
				session_id=parking_session.id,
				old_license_plate=current_license_plate,
				new_license_plate=new_license_plate,
				spot_number=spot.spot_number,
				floor=spot.floor,
				check_in=parking_session.check_in,
			)
	except IntegrityError as exc:
		raise HTTPException(
			status_code=status.HTTP_409_CONFLICT,
			detail="The new license plate already has an active parking session",
		) from exc
