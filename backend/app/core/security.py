from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import bcrypt
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.models.user import User

bearer_scheme = HTTPBearer()


def hash_password(password: str) -> str:
	return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
	try:
		return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
	except ValueError:
		return False


def create_access_token(user_id: int) -> str:
	return jwt.encode({"sub": str(user_id)}, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def get_current_user(
	credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
	db: Session = Depends(get_db),
) -> User:
	unauthorized = HTTPException(
		status_code=status.HTTP_401_UNAUTHORIZED,
		detail="Invalid or missing authentication token",
		headers={"WWW-Authenticate": "Bearer"},
	)
	try:
		payload = jwt.decode(
			credentials.credentials,
			settings.jwt_secret_key,
			algorithms=[settings.jwt_algorithm],
		)
		subject = payload.get("sub")
		user_id = int(subject)
	except (JWTError, TypeError, ValueError):
		raise unauthorized from None

	user = db.get(User, user_id)
	if user is None:
		raise unauthorized
	return user
