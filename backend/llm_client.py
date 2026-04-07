"""通用大模型客户端 - 支持多厂商API"""

import os
import json
from openai import OpenAI
import httpx

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "llm_config.json")

LLM_PROVIDERS = {
    "deepseek": {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com",
        "models": ["deepseek-chat", "deepseek-coder"],
    },
    "dashscope": {
        "name": "阿里灵积 (DashScope)",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "models": ["qwen-plus", "qwen-turbo", "qwen-max", "qwen2.5-coder-7b-instruct", "qwen2.5-72b-instruct"],
    },
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4", "gpt-3.5-turbo"],
    },
    "anthropic": {
        "name": "Anthropic (Claude)",
        "base_url": "https://api.anthropic.com/v1",
        "models": ["claude-sonnet-4-20250514", "claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022"],
        "extra_headers": {"anthropic-version": "2023-06-01"},
    },
    "moonshot": {
        "name": "Moonshot (月之暗面)",
        "base_url": "https://api.moonshot.cn/v1",
        "models": ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"],
    },
    "zhipu": {
        "name": "智谱AI (GLM)",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "models": ["glm-4-flash", "glm-4-plus", "glm-4"],
    },
    "siliconflow": {
        "name": "SiliconFlow",
        "base_url": "https://api.siliconflow.cn/v1",
        "models": ["Qwen/Qwen2.5-7B-Instruct", "Qwen/Qwen2.5-72B-Instruct", "THUDM/glm4-9b-chat", "deepseek-ai/DeepSeek-V2-Chat"],
    },
}


def load_config():
    """从文件加载配置"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"provider": "deepseek", "api_key": "", "model": "deepseek-chat"}


def save_config(config):
    """保存配置到文件"""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def get_llm_config():
    return load_config()


def set_llm_config(provider: str, api_key: str, model: str):
    config = {"provider": provider, "api_key": api_key, "model": model}
    save_config(config)


def is_configured():
    config = load_config()
    return bool(config.get("api_key"))


class LLMClient:
    def __init__(self, provider: str, api_key: str, model: str):
        self.provider = provider
        self.api_key = api_key
        self.model = model

        provider_info = LLM_PROVIDERS.get(provider, {})

        self.client = OpenAI(
            api_key=api_key,
            base_url=provider_info.get("base_url", "https://api.deepseek.com"),
            http_client=httpx.Client(timeout=60.0),
        )

        extra_headers = provider_info.get("extra_headers", {})
        if extra_headers:
            self.client.headers.update(extra_headers)

    def chat(self, messages: list, stream: bool = True, **kwargs):
        return self.client.chat.completions.create(
            model=self.model, messages=messages, stream=stream, **kwargs
        )

    def chat_no_stream(self, messages: list, **kwargs):
        return self.client.chat.completions.create(
            model=self.model, messages=messages, stream=False, **kwargs
        )


def get_all_providers() -> dict:
    return {
        key: {"name": info["name"], "models": info["models"]}
        for key, info in LLM_PROVIDERS.items()
    }
