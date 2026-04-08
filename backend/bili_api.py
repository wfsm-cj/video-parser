"""B站视频解析 - 使用官方 API"""

import httpx
import re
from typing import Optional


def parse_bilibili_bvid(bvid: str, p: int = 1) -> dict:
    """通过 B站官方 API 获取视频信息
    
    Args:
        bvid: B站视频 BV 号
        p: 分P索引，从1开始
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.bilibili.com",
    }
    
    # 获取视频基本信息
    resp = httpx.get(f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}", headers=headers, timeout=15)
    data = resp.json()
    
    if data.get("code") != 0:
        raise ValueError(f"B站 API 错误: {data.get('message')}")
    
    info = data.get("data", {})
    
    # 处理分P视频
    pages = info.get("pages", [])
    if p > 1 and len(pages) >= p:
        # 如果请求的是第2个及以后的视频，需要用分P的 cid
        page_info = pages[p - 1]
        cid = page_info.get("cid")
        aid = info.get("aid")
    else:
        cid = info.get("cid")
        aid = info.get("aid")
    
    # 获取视频播放地址 (DASH 格式)
    play_url = f"https://api.bilibili.com/x/player/playurl?avid={aid}&cid={cid}&qn=80&fnval=4048"
    play_resp = httpx.get(play_url, headers=headers, timeout=15)
    play_data = play_resp.json()
    
    formats = []
    
    if play_data.get("code") == 0:
        dash = play_data.get("data", {}).get("dash", {})
        
        # 视频流
        for video in dash.get("video", []):
            base_url = video.get("baseUrl") or video.get("base_url", "")
            if base_url:
                formats.append({
                    "format_id": f"video_{video.get('id')}",
                    "ext": "mp4",
                    "resolution": f"{video.get('width', 0)}x{video.get('height', 0)}",
                    "filesize": video.get("size", 0),
                    "filesize_string": format_size(video.get("size", 0)),
                    "url": base_url,
                    "codec": video.get("codecs", ""),
                })
        
        # 音频流
        for audio in dash.get("audio", []):
            base_url = audio.get("baseUrl") or audio.get("base_url", "")
            if base_url:
                formats.append({
                    "format_id": f"audio_{audio.get('id')}",
                    "ext": "m4a",
                    "resolution": "音频",
                    "filesize": audio.get("size", 0),
                    "filesize_string": format_size(audio.get("size", 0)),
                    "url": base_url,
                    "codec": audio.get("codecs", ""),
                })
        
        # 如果有视频+音频，添加合并选项
        if len([f for f in formats if "video" in f["format_id"]]) > 0 and len([f for f in formats if "audio" in f["format_id"]]) > 0:
            formats.insert(0, {
                "format_id": "dash_80",
                "ext": "mp4",
                "resolution": "720P",
                "filesize": 0,
                "filesize_string": "需合并",
                "url": "",
                "codec": "avc+acc",
                "dash": True,
            })
    
    # 获取正确的标题（分P视频标题）
    title = info.get("title", "未知标题")
    if p > 1 and len(pages) >= p:
        page_title = pages[p - 1].get("part", "")
        if page_title and page_title != title:
            title = f"{title} - {page_title}"
    
    return {
        "id": bvid,
        "title": title,
        "thumbnail": info.get("pic", "").replace("http://", "https://"),
        "duration": info.get("duration", 0),
        "duration_string": format_duration(info.get("duration", 0)),
        "uploader": info.get("owner", {}).get("name", "未知"),
        "platform": "BiliBili",
        "view_count": info.get("stat", {}).get("view", 0),
        "upload_date": format_date(info.get("pubdate", 0)),
        "description": info.get("desc", ""),
        "formats": formats,
    }


def format_size(size: int) -> str:
    if not size:
        return "未知"
    if size < 1024 * 1024:
        return f"{size / 1024:.0f}KB"
    if size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.1f}MB"
    return f"{size / (1024 * 1024 * 1024):.2f}GB"


def format_duration(seconds: int) -> str:
    if not seconds:
        return "00:00"
    minutes, secs = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def format_date(timestamp: int) -> str:
    import time
    return time.strftime("%Y-%m-%d", time.localtime(timestamp))


def extract_bvid_and_p(url: str) -> tuple[Optional[str], int]:
    """从 URL 提取 BVID 和分P索引
    
    Returns:
        (bvid, p): B站视频 BV 号和分P索引（从1开始）
    """
    # 提取 bvid
    bvid = None
    patterns = [
        r"bilibili\.com/video/(BV[\w]+)",
        r"b23\.tv/(\w+)",
        r"(BV[\w]{10})",
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            bvid = m.group(1)
            break
    
    if not bvid:
        return None, 1
    
    # 提取 p 参数
    p_match = re.search(r"[?&]p=(\d+)", url)
    p = int(p_match.group(1)) if p_match else 1
    
    return bvid, p


def is_bilibili_url(url: str) -> bool:
    return "bilibili.com" in url or "b23.tv" in url
