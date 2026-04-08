"""通用大模型视频总结模块 - 支持多厂商"""

import os
import re
import tempfile
from typing import Optional

import httpx

from llm_client import LLMClient, load_config, LLM_PROVIDERS


def _is_bilibili_url(url: str) -> bool:
    return "bilibili.com" in url or "b23.tv" in url


class SubtitleExtractor:
    """从视频 URL 提取平台字幕"""

    PREFERRED_LANGS = ["zh-Hans", "zh", "zh-CN", "en", "ja", "ko"]

    def extract(self, url: str) -> dict:
        if _is_bilibili_url(url):
            result = self._extract_bilibili(url)
            if result["has_subtitle"]:
                return result

        return {"has_subtitle": False, "language": "", "subtitle_type": "none", "segments": [], "full_text": ""}

    def _extract_bilibili(self, url: str) -> dict:
        empty = {"has_subtitle": False, "language": "", "subtitle_type": "none", "segments": [], "full_text": ""}
        try:
            bvid = self._parse_bvid(url)
            if not bvid:
                return empty

            headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.bilibili.com"}

            view_resp = httpx.get(f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}", headers=headers, timeout=15)
            view_data = view_resp.json().get("data", {})
            cid, aid = view_data.get("cid"), view_data.get("aid")
            if not cid or not aid:
                return empty

            dm_resp = httpx.get(f"https://api.bilibili.com/x/v2/dm/view?aid={aid}&oid={cid}&type=1", headers=headers, timeout=15)
            dm_data = dm_resp.json().get("data", {})
            subtitle_list = dm_data.get("subtitle", {}).get("subtitles", [])

            if not subtitle_list:
                return empty

            best = subtitle_list[0]
            for s in subtitle_list:
                if s.get("lan") in ("zh", "zh-Hans"):
                    best = s
                    break

            sub_type = "auto" if best.get("lan", "").startswith("ai-") else "manual"
            sub_url = best.get("subtitle_url", "")
            if sub_url.startswith("//"):
                sub_url = "https:" + sub_url

            if not sub_url:
                return empty

            sub_resp = httpx.get(sub_url, headers=headers, timeout=15)
            body = sub_resp.json().get("body", [])

            segments = [{"start": round(item.get("from", 0), 2), "end": round(item.get("to", 0), 2), "text": item.get("content", "").strip()} for item in body if item.get("content", "").strip()]
            full_text = " ".join(seg["text"] for seg in segments)
            return {"has_subtitle": True, "language": best.get("lan", "zh"), "subtitle_type": sub_type, "segments": segments, "full_text": full_text}
        except Exception as e:
            print(f"B站字幕提取失败: {e}")
            return empty

    @staticmethod
    def _parse_bvid(url: str) -> Optional[str]:
        m = re.search(r"(BV[a-zA-Z0-9]+)", url)
        return m.group(1) if m else None


class VideoSummarizer:
    """使用通用大模型 API 生成视频总结"""

    def __init__(self, provider: str = None, api_key: str = None, model: str = None):
        if provider and api_key and model:
            self.client = LLMClient(provider, api_key, model)
            self.provider = provider
            self.model = model
        else:
            config = load_config()
            self.provider = config.get("provider", "deepseek")
            self.model = config.get("model", "deepseek-chat")
            api_key = config.get("api_key", "")
            if not api_key:
                raise ValueError("请先在设置中配置大模型 API Key")
            self.client = LLMClient(self.provider, api_key, self.model)

    def summarize_stream(self, subtitle_text: str, language: str = "zh"):
        prompt = self._build_summary_prompt(subtitle_text, language)
        system_prompt = "你是一个专业的视频内容分析助手，擅长提取关键信息并生成结构化的总结。"
        response = self.client.chat([{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}], stream=True, temperature=0.7, max_tokens=4096)
        for chunk in response:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content

    def generate_mindmap(self, subtitle_text: str, language: str = "zh") -> str:
        prompt = self._build_mindmap_prompt(subtitle_text, language)
        system_prompt = "你是一个专业的思维导图生成助手，擅长将内容组织为清晰的层级结构。"
        response = self.client.chat([{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}], stream=False, temperature=0.5, max_tokens=4096)
        return response.choices[0].message.content

    def chat_stream(self, subtitle_text: str, question: str):
        prompt = self._build_chat_prompt(subtitle_text, question)
        system_prompt = "你是一个视频内容问答助手，根据提供的视频字幕内容来回答用户的问题。"
        response = self.client.chat([{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}], stream=True, temperature=0.7, max_tokens=2048)
        for chunk in response:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content

    @staticmethod
    def _build_summary_prompt(subtitle_text: str, language: str) -> str:
        truncated = subtitle_text[:15000]
        lang_hint = "中文" if language.startswith("zh") else "与原文相同的语言"
        return f"""请对以下视频字幕内容进行深度总结分析，使用{lang_hint}输出。

要求输出格式：
## 视频概述
## 内容大纲
## 核心知识要点
## 总结

---
视频字幕内容：
{truncated}"""

    @staticmethod
    def _build_mindmap_prompt(subtitle_text: str, language: str) -> str:
        truncated = subtitle_text[:15000]
        lang_hint = "中文" if language.startswith("zh") else "与原文相同的语言"
        return f"""请将以下视频字幕内容整理为思维导图结构，使用{lang_hint}输出。使用 Markdown 标题层级格式。\n\n视频字幕内容：\n{truncated}"""

    @staticmethod
    def _build_chat_prompt(subtitle_text: str, question: str) -> str:
        truncated = subtitle_text[:12000]
        return f"""视频字幕内容：\n{truncated}\n\n用户问题：{question}\n\n请基于视频内容给出准确、详细的回答。"""
