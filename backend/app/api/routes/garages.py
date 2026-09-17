from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("")
def list_garages() -> None:
    raise HTTPException(status_code=501, detail="Garage management is not implemented yet")
