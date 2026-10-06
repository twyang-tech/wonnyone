import subprocess
import json
from functools import lru_cache
from pathlib import Path
from dataclasses import dataclass

def get_image_resolution(filepath):
    try:
        from PIL import Image
        with Image.open(filepath) as img:
            w, h = img.size
            return f"{w}x{h}"
    except Exception:
        return None


def get_video_resolution(filepath):
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error", "-select_streams", "v:0",
                "-show_entries", "stream=width,height",
                "-of", "json", filepath
            ],
            capture_output=True, text=True, timeout=15
        )
        data = json.loads(result.stdout)
        stream = data["streams"][0]
        return f"{stream['width']}x{stream['height']}"
    except Exception:
        return None


def get_video_duration_sec(filepath):
    """영상 길이를 초 단위 정수로 반환. 실패 시 None."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "json", filepath
            ],
            capture_output=True, text=True, timeout=15
        )
        data = json.loads(result.stdout)
        duration = float(data["format"]["duration"])
        return int(round(duration))
    except Exception:
        return None


IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "bmp", "webp", "tiff"}
VIDEO_EXTENSIONS = {"mp4", "mov", "avi", "webm", "mkv", "m4v", "wmv"}


@dataclass(frozen=True)
class MediaInfo:
    kind: str
    format: str
    resolution: str
    error: str = ""

@lru_cache(maxsize=512)
def _inspect(path, size, modified):
    ext = Path(path).suffix.lstrip(".").lower()
    if ext in IMAGE_EXTENSIONS:
        try:
            from PIL import Image
            with Image.open(path) as image:
                return MediaInfo("이미지", image.format, f"{image.width}x{image.height}")
        except Exception as exc:
            return MediaInfo("이미지", ext.upper(), "해상도미확인", f"이미지 읽기 실패: {exc}")
    if ext in VIDEO_EXTENSIONS:
        try:
            result = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                "-show_entries", "stream=width,height", "-of", "json", path],
                capture_output=True, text=True, timeout=15, check=True)
            stream = json.loads(result.stdout)["streams"][0]
            return MediaInfo("영상", ext.upper(), f"{stream['width']}x{stream['height']}")
        except Exception as exc:
            return MediaInfo("영상", ext.upper(), "해상도미확인", f"영상 분석 실패 (ffprobe 확인): {exc}")
    return MediaInfo("지원 안 함", ext.upper(), "해상도미확인", "지원하지 않는 확장자")

def inspect_media(path):
    try:
        stat = Path(path).stat()
        return _inspect(str(Path(path).resolve()), stat.st_size, stat.st_mtime_ns)
    except OSError as exc:
        return MediaInfo("지원 안 함", "", "해상도미확인", str(exc))
