from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import (
    create_token,
    get_current_user,
    hash_password,
    validate_email,
    validate_password,
    verify_password,
)
from database import create_user, get_user_by_email
from database import (
    PLAN_LABELS,
    get_daily_summary_limit_for_plan,
    get_effective_plan_tier,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


def _build_user_response(user: dict) -> dict:
    plan_tier = get_effective_plan_tier(user)
    vip_expire_at = None
    if user.get("is_vip") and user.get("vip_expire_at"):
        try:
            expire = datetime.fromisoformat(user["vip_expire_at"])
            if expire.tzinfo is None:
                expire = expire.replace(tzinfo=timezone.utc)
            if expire > datetime.now(timezone.utc):
                vip_expire_at = user["vip_expire_at"]
        except ValueError:
            pass

    return {
        "id": user["id"],
        "email": user["email"],
        "is_vip": plan_tier == "pro",
        "is_paid": plan_tier != "free",
        "plan_tier": plan_tier,
        "plan_name": PLAN_LABELS.get(plan_tier, "Free"),
        "daily_summary_limit": get_daily_summary_limit_for_plan(plan_tier),
        "vip_expire_at": vip_expire_at,
    }


@router.post("/register")
async def register(req: RegisterRequest):
    if not validate_email(req.email):
        raise HTTPException(status_code=400, detail="邮箱格式不正确")

    err = validate_password(req.password)
    if err:
        raise HTTPException(status_code=400, detail=err)

    if get_user_by_email(req.email):
        raise HTTPException(status_code=400, detail="该邮箱已注册")

    hashed = hash_password(req.password)
    user = create_user(req.email, hashed)
    token = create_token(user["id"], req.email)

    return {
        "success": True,
        "data": {
            "token": token,
            "user": {"id": user["id"], "email": req.email, "is_vip": False, "vip_expire_at": None},
        },
    }


@router.post("/login")
async def login(req: LoginRequest):
    user = get_user_by_email(req.email)
    if not user:
        raise HTTPException(status_code=400, detail="邮箱或密码错误")

    if not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="邮箱或密码错误")

    token = create_token(user["id"], user["email"])
    return {
        "success": True,
        "data": {
            "token": token,
            "user": _build_user_response(user),
        },
    }


@router.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    return {
        "success": True,
        "data": _build_user_response(user),
    }
