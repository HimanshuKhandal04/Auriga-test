# ParkFlow Engineering Decision Record

## Requirements understood

ParkFlow needed a time-boxed full-stack parking MVP: typed multi-level spots, authenticated users, check-in/check-out, fees, 24-hour automation, valet transfer, operational lookups, and a usable dashboard. The implementation prioritizes backend-enforced rules and simple incremental structure.

## Architecture

The existing split is retained: Next.js App Router in `frontend/`, FastAPI routes in `backend/app/api/routes/`, SQLAlchemy models in `app/models/`, Pydantic contracts in `app/schemas/`, and business logic in `app/services/`. Routes stay thin and services are directly testable with SQLAlchemy sessions.

## Database and schema decisions

SQLite is configured through SQLAlchemy with `check_same_thread=False`. `User`, `Garage`, `ParkingSpot`, and `ParkingSession` use typed SQLAlchemy mappings. Spot floor/number pairs are unique; sessions have a foreign key to spots, enum checks, useful indexes, non-negative fees, and SQLite partial unique indexes for active plates and active spots.

## Parking rules and workflows

- EV vehicles use EV spots only.
- Standard vehicles use standard spots only.
- Compact vehicles use compact or standard spots.
- Check-in filters unoccupied compatible spots and orders by lowest floor, then spot number, then ID. Spot claiming and active-session creation share one transaction.
- Checkout accepts an active session ID or normalized plate, rounds elapsed partial hours up, applies the configured first-hour/additional-hour rate card and daily cap, completes the session, and frees its spot transactionally.

## Rate-card import

`app/services/billing.py` imports one rate-card record from CSV or JSON when configured. Cleaning is explicit and configurable: whitespace trimming, field-name normalization, and decimal separator selection. When no file is configured, documented development fallback rates keep checkout usable in a fresh clone; a supplied rate card overrides them. Invalid or negative imported rates are rejected.

## Automation and transfer

`POST /clock` accepts a simulated timestamp and closes active sessions strictly older than 24 hours. It reuses the billing function, sets the supplied checkout time, frees spots, and commits all closures transactionally. `POST /api/parking/transfer` requires a JWT, normalizes both plates, locks the active source session, rejects an active target plate, and mutates only the existing session plate; spot, session ID, and original check-in remain unchanged.

## Lookup APIs

Session search uses normalized partial plate matching. Active/history and spot APIs use `COUNT`, `OFFSET`, and `LIMIT` pagination. Sort fields resolve through explicit allowlists rather than arbitrary SQL column names. Spot lookup supports type and availability filters; EV availability is a database aggregation.

## Authentication

Registration stores bcrypt password hashes. Login issues a JWT signed with configured settings. The transfer route uses a bearer-token dependency. The frontend stores the returned token locally and sends it for protected calls.

## Testing performed

Validated real SQLite service workflows for check-in, checkout, billing rounding/cap, `/clock`, transfer, lookup filtering/pagination/sorting, and EV counts. Verified registration/login and CORS with live `curl` requests. Ran `python -m compileall -q app` and `npm run build` successfully.

## Bugs and fixes

- Duplicate spot field declarations were removed from `ParkingSpot`.
- SQLAlchemy/Python typing compatibility required SQLAlchemy `2.0.54` and conservative relationship/nullable annotations.
- SQLite EV aggregation required SQLAlchemy `Integer` rather than Python `int` in `cast`.
- The passlib/bcrypt adapter failed in the runtime; direct bcrypt `hashpw`/`checkpw` calls were used with the pinned bcrypt dependency.
- Frontend connection failures were addressed with the requested API URL fallback, localhost/Codespaces CORS rules, and live registration smoke checks.
- Some initial test scripts reused SQLAlchemy sessions after implicit read transactions; validation was corrected to use fresh transaction boundaries.

## Known limitations and future improvements

- Garage CRUD is still a `501` placeholder.
- No automated test suite is committed yet.
- Rate-card persistence/versioning is file-based rather than database-backed.
- JWT expiry enforcement and full auth lifecycle endpoints should be expanded.
- SQLite write concurrency is suitable for the challenge MVP, not a production-scale garage.
- Add migrations, stronger structured logging, production secret management, and end-to-end browser tests before deployment.