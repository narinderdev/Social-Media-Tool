from fastapi import APIRouter, Depends

from app.auth import require_user
from app.config import account_status, default_social_account, platform_status

router = APIRouter(prefix="/api", tags=["platforms"])


@router.get("/platforms")
def get_platforms(account: str | None = None, _: dict = Depends(require_user)) -> dict:
    return {"platforms": platform_status(account)}


@router.get("/accounts")
def get_accounts(_: dict = Depends(require_user)) -> dict:
    return {"accounts": account_status(), "defaultAccount": default_social_account()}
