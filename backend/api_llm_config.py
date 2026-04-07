"""大模型配置 API"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from summarizer import LLMConfig
from llm_client import get_all_providers, LLM_PROVIDERS

router = APIRouter(prefix="/api/llm", tags=["大模型配置"])


class SetLLMConfigRequest(BaseModel):
    provider: str
    api_key: str
    model: str


@router.get("/providers")
async def list_providers():
    return get_all_providers()


@router.get("/config")
async def get_llm_config():
    config = LLMConfig.get()
    return {
        "provider": config.get("provider", "deepseek"),
        "model": config.get("model", "deepseek-chat"),
        "is_configured": LLMConfig.is_configured(),
    }


@router.post("/config")
async def set_llm_config(req: SetLLMConfigRequest):
    if req.provider not in LLM_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"不支持的厂商: {req.provider}")
    LLMConfig.set(req.provider, req.api_key, req.model)
    return {"success": True, "message": "配置已保存"}
