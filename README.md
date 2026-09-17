# ParkFlow

ParkFlow is a full-stack parking-garage management MVP. It manages typed parking spots across floors, active parking sessions, deterministic vehicle assignment, checkout billing, valet plate transfer, and operational lookup views.

## Problem solved

Garage operators need a reliable way to see capacity, assign compatible spaces, track vehicles, calculate checkout fees, and release spaces without maintaining manual lists. ParkFlow centralizes those workflows behind a FastAPI API and a small Next.js dashboard.

## Key features

- Registration and JWT login with bcrypt password hashing.
- Compact, standard, and EV spots across multiple floors.
- Automatic compatibility-aware check-in with deterministic allocation.
- Checkout with rounded-up hours, tiered pricing, and a configured daily cap.
- Paginated plate search, active-session history, sorted spot lists, and EV availability.
- `POST /clock` automation for sessions older than 24 hours.
- Authenticated valet hand-off through `POST /api/parking/transfer`.
- Next.js dashboard for live garage data, check-in, search, and checkout.

## Technology stack

- Frontend: Next.js 15, React 19, TypeScript, Tailwind CSS.
- Backend: FastAPI, Uvicorn, Python.
- Database: SQLite with SQLAlchemy 2.
- Validation: Pydantic and Pydantic Settings.
- Authentication: JWT with `python-jose` and bcrypt password hashes.

## Project structure

```text
.
├── backend/
│   ├── app/
│   │   ├── api/routes/       # FastAPI route modules
│   │   ├── core/             # Settings, DB session, security
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # Pydantic API contracts
│   │   └── services/         # Parking, billing, and lookup logic
│   ├── seed_data.py          # Idempotent development spot seed
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── app/                  # Next.js pages and dashboard client
│   ├── lib/api.ts            # Typed API client
│   ├── package.json
│   └── .next/                # Generated build output
├── README.md
└── REASONING.md
```

## Prerequisites

- Python 3.11+ recommended.
- Node.js 18.18+ and npm.
- A terminal with two processes available.

## Setup

From the repository root:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python seed_data.py
```

The seed script creates the eight development spots and is safe to run repeatedly.

In a second terminal:

```bash
cd frontend
npm install
```

## Run commands

Backend, from `backend/`:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend, from `frontend/`:

```bash
npm run dev
```

Open `http://localhost:3000`. API docs are at `http://localhost:8000/docs`.

## Environment variables

Backend variables are documented in [backend/.env.example](backend/.env.example):

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | SQLite URL; default `sqlite:///./parkflow.db` |
| `JWT_SECRET_KEY` | JWT signing secret; replace the development value |
| `JWT_ALGORITHM` | JWT algorithm; default `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Reserved token lifetime setting |
| `PARKING_RATE_CARD_PATH` | Path to the supplied CSV/JSON rate card |
| `PARKING_RATE_CARD_FORMAT` | Optional `csv` or `json` override |
| `PARKING_FIRST_HOUR_RATE` | Development fallback first-hour rate; default `5` |
| `PARKING_ADDITIONAL_HOUR_RATE` | Development fallback additional-hour rate; default `3` |
| `PARKING_DAILY_CAP` | Development fallback daily cap; default `30` |

The frontend API client uses `NEXT_PUBLIC_API_URL || "http://localhost:8000"`. For Codespaces, set it to the forwarded backend URL, for example:

```bash
NEXT_PUBLIC_API_URL=https://<codespace>-8000.app.github.dev npm run dev
```

## API endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Health check. |
| `POST` | `/api/auth/register` | Create a user account. |
| `POST` | `/api/auth/login` | Return a JWT bearer token. |
| `GET` | `/api/parking/search` | Partial normalized plate search with pagination. |
| `GET` | `/api/parking/active` | Active sessions with pagination and allowlisted sorting. |
| `GET` | `/api/parking/history` | Completed sessions with pagination and allowlisted sorting. |
| `POST` | `/api/parking/check-in` | Normalize a plate and assign a compatible spot. |
| `POST` | `/api/parking/check-out` | Complete an active session and release its spot. |
| `POST` | `/api/parking/transfer` | Authenticated valet plate hand-off. |
| `GET` | `/api/spots` | Paginated spots with type, availability, sorting, and filters. |
| `GET` | `/api/spots/ev/availability` | Total, occupied, and available EV counts. |
| `POST` | `/clock` | Close active sessions older than 24 simulated hours. |
| `GET` | `/api/garages` | Exists as a route but currently returns `501`; garage CRUD is not implemented. |

## Authentication

Register and log in through `/api/auth/register` and `/api/auth/login`. Login returns:

```json
{"access_token":"<jwt>","token_type":"bearer"}
```

Send protected requests with `Authorization: Bearer <jwt>`. Currently, the transfer endpoint requires authentication; the dashboard stores the login token in browser local storage.

## Example requests

Check-in:

```bash
curl -X POST http://localhost:8000/api/parking/check-in \
    -H 'Content-Type: application/json' \
    -d '{"license_plate":"ABC-123","vehicle_type":"COMPACT"}'
```

Checkout by session ID:

```bash
curl -X POST http://localhost:8000/api/parking/check-out \
    -H 'Content-Type: application/json' \
    -d '{"session_id":1}'
```

Checkout billing and `/clock` use the fallback rates from `.env.example` when `PARKING_RATE_CARD_PATH` is empty. Deployments can supply a CSV or JSON rate card to override those values.

## Testing and verification

There are no committed automated tests yet; `backend/tests/` only contains the package marker. Use these checks:

```bash
curl http://localhost:8000/health
cd backend && python -m compileall -q app
cd frontend && npm run build
```

Interactive API verification is available at `/docs`. Seed data with `cd backend && python seed_data.py` before testing check-in.

## Debugging connection problems

- Confirm the backend is listening on port 8000: `curl http://localhost:8000/health`.
- Confirm the frontend is on port 3000: `npm run dev` from `frontend/`.
- Set `NEXT_PUBLIC_API_URL` before starting Next.js; restart Next.js after changing it because public environment variables are build-time values.
- In a browser, use the backend forwarded URL rather than `localhost` when the frontend is opened through Codespaces.
- FastAPI allows `localhost:3000`, `127.0.0.1:3000`, and matching Codespaces forwarded frontend origins through CORS.
- Inspect the browser Network tab for the exact API URL and response status. API errors are displayed by the dashboard/auth forms.

## GitHub and Codespaces

Clone or open the repository in a Codespace, then run the backend and frontend in separate terminals using the commands above. Forward ports `8000` and `3000`. When using forwarded URLs, set `NEXT_PUBLIC_API_URL` to the forwarded backend URL and open the forwarded frontend URL. The FastAPI CORS configuration permits the standard Codespaces `*-3000.app.github.dev` origin pattern.
