import os
import re
import shutil
import yt_dlp
from typing import Optional


def _find_ffmpeg_path() -> Optional[str]:
    """查找 ffmpeg 可执行文件路径"""
    if shutil.which("ffmpeg"):
        return os.path.dirname(shutil.which("ffmpeg"))
    try:
        import static_ffmpeg
        paths = static_ffmpeg.run.get_or_fetch_platform_executables_else_raise()
        return os.path.dirname(paths[0])
    except Exception:
        return None


def _try_bilibili_api(url: str) -> Optional[dict]:
    """尝试使用 B站 API 解析"""
    from bili_api import extract_bvid, parse_bilibili_bvid, is_bilibili_url
    if not is_bilibili_url(url):
        return None
    bvid = extract_bvid(url)
    if not bvid:
        return None
    try:
        return parse_bilibili_bvid(bvid)
    except Exception:
        return None


class VideoDownloader:
    """yt-dlp 封装层，提供视频解析、下载、直链获取能力"""

    DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), "downloads")

    def __init__(self):
        os.makedirs(self.DOWNLOAD_DIR, exist_ok=True)
        self.ffmpeg_path = _find_ffmpeg_path()
        self.has_ffmpeg = self.ffmpeg_path is not None

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        return re.sub(r'[\\/*?:"<>|]', "_", name)

    @staticmethod
    def _format_filesize(size: Optional[int]) -> str:
        if not size:
            return "未知大小"
        if size < 1024 * 1024:
            return f"{size / 1024:.0f}KB"
        if size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f}MB"
        return f"{size / (1024 * 1024 * 1024):.2f}GB"

    @staticmethod
    def _format_duration(seconds: Optional[int]) -> str:
        if not seconds:
            return "00:00"
        hours, remainder = divmod(int(seconds), 3600)
        minutes, secs = divmod(remainder, 60)
        if hours:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"

    def parse_video(self, url: str) -> dict:
        """解析视频信息，不下载文件"""
        
        # 优先尝试 B站 API
        bili_result = _try_bilibili_api(url)
        if bili_result:
            return bili_result
        
        # 回退到 yt-dlp
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "noplaylist": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        if not info:
            raise ValueError("无法解析该链接")

        formats = self._extract_formats(info)
        platform = info.get("extractor", info.get("extractor_key", "Unknown"))

        return {
            "id": info.get("id", ""),
            "title": info.get("title", "未知标题"),
            "thumbnail": info.get("thumbnail", ""),
            "duration": info.get("duration"),
            "duration_string": self._format_duration(info.get("duration")),
            "uploader": info.get("uploader", info.get("channel", "未知")),
            "platform": platform,
            "view_count": info.get("view_count"),
            "upload_date": info.get("upload_date", ""),
            "description": info.get("description", ""),
            "formats": formats,
        }

    def _extract_formats(self, info: dict) -> list:
        formats = info.get("formats", []) or []
        if not formats and info.get("url"):
            return []

        results = []
        seen = set()

        for fmt in formats:
            format_id = fmt.get("format_id", "")
            ext = fmt.get("ext", "")
            url = fmt.get("url", "")
            if not url or format_id in seen:
                continue
            if fmt.get("vcodec", "none") == "none" and fmt.get("acodec", "none") == "none":
                continue

            resolution = fmt.get("resolution", "")
            if not resolution and fmt.get("width"):
                height = fmt.get("height", 0)
                resolution = f"{fmt.get('width', 0)}x{height}" if height else "unknown"

            filesize = fmt.get("filesize") or fmt.get("filesize_approx", 0)
            results.append({
                "format_id": format_id,
                "ext": ext,
                "resolution": resolution,
                "filesize": filesize,
                "filesize_string": self._format_filesize(filesize),
                "url": url,
                "codec": f"{fmt.get('vcodec', 'unknown')}/{fmt.get('acodec', 'unknown')}",
            })
            seen.add(format_id)

        for fmt in formats:
            if fmt.get("url") and "+" in fmt.get("format_id", ""):
                format_id = fmt.get("format_id", "")
                if format_id not in seen:
                    results.insert(0, {
                        "format_id": format_id,
                        "ext": "mp4",
                        "resolution": "最高画质",
                        "filesize": 0,
                        "filesize_string": "未知",
                        "url": fmt.get("url", ""),
                        "codec": f"{fmt.get('vcodec', '')} + {fmt.get('acodec', '')}",
                        "acodec": "merged",
                    })
                    seen.add(format_id)

        return results[:15]

    def download_video(self, url: str, format_id: str) -> dict:
        """下载视频到服务器临时目录，返回文件路径和元数据"""
        if not self.has_ffmpeg and "+" in format_id:
            format_id = "best"

        ydl_opts = {
            "format": format_id,
            "outtmpl": os.path.join(self.DOWNLOAD_DIR, "%(title)s.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
        }

        if self.has_ffmpeg:
            ydl_opts["ffmpeg_location"] = self.ffmpeg_path
            ydl_opts["merge_output_format"] = "mp4"

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        if not info:
            raise ValueError("下载失败")

        title = self._sanitize_filename(info.get("title", "video"))
        ext = info.get("ext", "mp4")
        filename = f"{title}.{ext}"
        filepath = os.path.join(self.DOWNLOAD_DIR, filename)

        if not os.path.exists(filepath):
            prepared = ydl.prepare_filename(info)
            if os.path.exists(prepared):
                filepath = prepared
                filename = os.path.basename(prepared)
            else:
                for f in os.listdir(self.DOWNLOAD_DIR):
                    if title in f:
                        filepath = os.path.join(self.DOWNLOAD_DIR, f)
                        filename = f
                        break

        return {
            "filepath": filepath,
            "filename": filename,
            "title": info.get("title", "video"),
            "ext": ext,
        }

    def get_direct_url(self, url: str, format_id: str) -> dict:
        """获取视频直链"""
        ydl_opts = {
            "format": format_id,
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "skip_download": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        if not info:
            raise ValueError("无法获取视频信息")

        formats = info.get("formats", []) or []
        target = None

        for fmt in formats:
            if fmt.get("format_id") == format_id and fmt.get("url"):
                target = fmt
                break

        if not target:
            for fmt in formats:
                if fmt.get("url") and fmt.get("format_id"):
                    target = fmt
                    break

        if not target:
            raise ValueError("未找到可用格式")

        return {
            "url": target.get("url", ""),
            "format_id": target.get("format_id", ""),
            "ext": target.get("ext", "mp4"),
        }

    def get_available_formats(self, url: str) -> list:
        """获取视频可用格式列表"""
        info = self.parse_video(url)
        return info.get("formats", [])
