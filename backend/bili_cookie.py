"""B站 Cookie 配置"""

import os
import json

COOKIE_FILE = os.path.join(os.path.dirname(__file__), "bili_cookie.json")


def load_cookie():
    if os.path.exists(COOKIE_FILE):
        try:
            with open(COOKIE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"cookie": "", "enabled": False}


def save_cookie(cookie: str, enabled: bool):
    with open(COOKIE_FILE, "w", encoding="utf-8") as f:
        json.dump({"cookie": cookie, "enabled": enabled}, f, ensure_ascii=False, indent=2)


def get_cookie_dict():
    """获取 cookie 字典格式，用于 yt-dlp"""
    data = load_cookie()
    if not data.get("enabled") or not data.get("cookie"):
        return {}
    
    cookie_dict = {}
    for item in data["cookie"].split(";"):
        item = item.strip()
        if "=" in item:
            key, value = item.split("=", 1)
            cookie_dict[key.strip()] = value.strip()
    return cookie_dict


def is_cookie_enabled():
    data = load_cookie()
    return data.get("enabled", False) and bool(data.get("cookie"))


def load_cookie_string():
    """获取 cookie 字符串格式"""
    data = load_cookie()
    if not data.get("enabled") or not data.get("cookie"):
        return ""
    return data["cookie"]
