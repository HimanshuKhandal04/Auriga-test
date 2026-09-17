from app.core.db import SessionLocal, init_db
from app.models.garage import ParkingSpot, SpotType

SEED_SPOTS = (
    (1, "C-01", SpotType.COMPACT),
    (1, "C-02", SpotType.COMPACT),
    (1, "S-01", SpotType.STANDARD),
    (1, "S-02", SpotType.STANDARD),
    (1, "E-01", SpotType.EV),
    (2, "C-03", SpotType.COMPACT),
    (2, "S-03", SpotType.STANDARD),
    (2, "E-02", SpotType.EV),
)


def seed_parking_spots() -> None:
    init_db()
    db = SessionLocal()
    try:
        with db.begin():
            existing_keys = {
                (floor, spot_number)
                for floor, spot_number in db.query(ParkingSpot.floor, ParkingSpot.spot_number).all()
            }

            created_count = 0
            existing_count = 0
            for floor, spot_number, spot_type in SEED_SPOTS:
                if (floor, spot_number) in existing_keys:
                    existing_count += 1
                    continue

                db.add(
                    ParkingSpot(
                        floor=floor,
                        spot_number=spot_number,
                        spot_type=spot_type,
                        is_occupied=False,
                    )
                )
                created_count += 1

        print(f"Created {created_count} parking spots; {existing_count} already existed.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_parking_spots()
