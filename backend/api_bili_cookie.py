"""B站 Cookie 配置 API"""

from fastapi import APIRouter
from pydantic import BaseModel

from bili_cookie import load_cookie, save_cookie, is_cookie_enabled

router = APIRouter(prefix="/api/bili-cookie", tags=["B站Cookie"])


class SetCookieRequest(BaseModel):
    cookie: str
    enabled: bool


@router.get("/config")
async def get_cookie_config():
    data = load_cookie()
    return {
        "enabled": data.get("enabled", False),
        "has_cookie": bool(data.get("cookie")),
    }


@router.post("/config")
async def set_cookie(req: SetCookieRequest):
    save_cookie(req.cookie, req.enabled)
    return {"success": True, "message": "Cookie 已保存"}


@router.get("/status")
async def get_status():
    return {"enabled": is_cookie_enabled()}
