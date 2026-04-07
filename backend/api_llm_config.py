"""大模型配置 API"""

import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pydantic import BaseModel

from summarizer import LLMConfig
from llm_client import get_all_providers, LLM_PROVIDERS, LLMClient

router = APIRouter(prefix="/api/llm", tags=["大模型配置"])


class SetLLMConfigRequest(BaseModel):
    provider: str
    api_key: str
    model: str


class TestAPIRequest(BaseModel):
    provider: str
    api_key: str
    model: str


@router.get("/providers")
async def list_providers():
    return get_all_providers()


@router.get("/providers/{provider}")
async def get_provider_models(provider: str):
    if provider not in LLM_PROVIDERS:
        raise HTTPException(status_code=404, detail="不支持的厂商")
    info = LLM_PROVIDERS[provider]
    return {"name": info["name"], "models": info["models"], "base_url": info["base_url"]}


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


@router.post("/test")
async def test_api_key(req: TestAPIRequest):
    """测试 API Key 是否有效"""
    if req.provider not in LLM_PROVIDERS:
        return {"valid": False, "message": f"不支持的厂商: {req.provider}"}

    try:
        client = LLMClient(req.provider, req.api_key, req.model)
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.chat_no_stream(
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=10
            )
        )
        if response.choices and response.choices[0].message:
            return {"valid": True, "message": "API Key 有效"}
        return {"valid": False, "message": "API 返回异常"}
    except Exception as e:
        error_msg = str(e)
        if "authentication" in error_msg.lower() or "api key" in error_msg.lower() or "invalid" in error_msg.lower():
            return {"valid": False, "message": "API Key 无效"}
        if "rate limit" in error_msg.lower():
            return {"valid": False, "message": "请求频率超限"}
        if "insufficient" in error_msg.lower() or "quota" in error_msg.lower() or "credits" in error_msg.lower():
            return {"valid": False, "message": "账户余额不足"}
        return {"valid": False, "message": error_msg[:100]}
