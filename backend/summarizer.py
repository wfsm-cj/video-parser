"""通用大模型视频总结模块 - 支持多厂商"""

import json
import os
import re
import tempfile
from typing import Optional

import httpx
import yt_dlp
from openai import OpenAI

from llm_client import LLMClient, LLMConfig, LLM_PROVIDERS


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

        info = self._get_video_info(url)

        manual_subs = info.get("subtitles") or {}
        auto_subs = info.get("automatic_captions") or {}
        manual_subs = {k: v for k, v in manual_subs.items() if k != "danmaku"}

        lang, sub_url, sub_type = self._pick_best_subtitle(manual_subs, auto_subs)
        if not sub_url:
            return {"has_subtitle": False, "language": "", "subtitle_type": "none", "segments": [], "full_text": ""}

        segments = self._download_and_parse(url, lang, sub_type)
        full_text = " ".join(seg["text"] for seg in segments)

        return {"has_subtitle": True, "language": lang, "subtitle_type": sub_type, "segments": segments, "full_text": full_text}

    def _extract_bilibili(self, url: str) -> dict:
        empty = {"has_subtitle": False, "language": "", "subtitle_type": "none", "segments": [], "full_text": ""}
        try:
            bvid = self._parse_bvid(url)
            if not bvid:
                return empty

            headers = {"User-Agent": "Mozilla/5.0", "Referer": f"https://www.bilibili.com/video/{bvid}"}

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
        except Exception:
            return empty

    @staticmethod
    def _parse_bvid(url: str) -> Optional[str]:
        m = re.search(r"(BV[a-zA-Z0-9]+)", url)
        return m.group(1) if m else None

    def _get_video_info(self, url: str) -> dict:
        ydl_opts = {"quiet": True, "no_warnings": True, "noplaylist": True, "extract_flat": False, "writesubtitles": True, "writeautomaticsub": True, "skip_download": True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        if not info:
            raise ValueError("无法解析该视频链接")
        return info

    def _pick_best_subtitle(self, manual_subs: dict, auto_subs: dict) -> tuple:
        for lang in self.PREFERRED_LANGS:
            if lang in manual_subs:
                url = self._get_format_url(manual_subs[lang])
                if url:
                    return lang, url, "manual"
        for lang in self.PREFERRED_LANGS:
            if lang in auto_subs:
                url = self._get_format_url(auto_subs[lang])
                if url:
                    return lang, url, "auto"
        return "", None, "none"

    @staticmethod
    def _get_format_url(formats: list) -> Optional[str]:
        for pref in ["json3", "srv3", "vtt"]:
            for fmt in formats:
                if fmt.get("ext") == pref:
                    return fmt.get("url")
        return formats[0].get("url") if formats else None

    def _download_and_parse(self, url: str, lang: str, sub_type: str) -> list:
        with tempfile.TemporaryDirectory() as tmp_dir:
            ydl_opts = {"quiet": True, "no_warnings": True, "noplaylist": True, "skip_download": True, "writesubtitles": sub_type == "manual", "writeautomaticsub": sub_type == "auto", "subtitleslangs": [lang], "subtitlesformat": "vtt", "outtmpl": os.path.join(tmp_dir, "subtitle")}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            vtt_files = [f for f in os.listdir(tmp_dir) if f.endswith(".vtt")]
            if not vtt_files:
                return []
            return self._parse_vtt(os.path.join(tmp_dir, vtt_files[0]))

    @staticmethod
    def _parse_vtt(filepath: str) -> list:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        segments = []
        blocks = re.split(r"\n\n+", content)
        time_pattern = re.compile(r"(\d{2}:\d{2}:\d{2}\.\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}\.\d{3})")
        seen = set()
        for block in blocks:
            lines = block.strip().split("\n")
            time_match, text_lines = None, []
            for line in lines:
                m = time_pattern.search(line)
                if m:
                    time_match = m
                elif time_match and line.strip() and not line.strip().isdigit():
                    clean = re.sub(r"<[^>]+>", "", line.strip())
                    if clean:
                        text_lines.append(clean)
            if time_match and text_lines:
                text = " ".join(text_lines)
                if text in seen:
                    continue
                seen.add(text)
                segments.append({"start": _time_to_seconds(time_match.group(1)), "end": _time_to_seconds(time_match.group(2)), "text": text})
        return segments


class VideoSummarizer:
    """使用通用大模型 API 生成视频总结"""

    def __init__(self, provider: str = None, api_key: str = None, model: str = None):
        if provider and api_key and model:
            self.client = LLMClient(provider, api_key, model)
            self.provider = provider
            self.model = model
        else:
            config = LLMConfig.get()
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


def _time_to_seconds(time_str: str) -> float:
    parts = time_str.split(":")
    return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
