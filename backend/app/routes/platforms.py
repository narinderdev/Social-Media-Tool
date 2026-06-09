from fastapi import APIRouter, Depends

from app.auth import require_user
from app.config import platform_status

router = APIRouter(prefix="/api", tags=["platforms"])


@router.get("/platforms")
def get_platforms(_: dict = Depends(require_user)) -> dict:
    return {"platforms": platform_status()}
