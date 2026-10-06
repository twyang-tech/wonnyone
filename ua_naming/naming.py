import os
import re
from .media import IMAGE_EXTENSIONS, VIDEO_EXTENSIONS, get_image_resolution, get_video_resolution, get_video_duration_sec

# 영상 파일에 한해 픽셀 해상도 대신 비율로 표시하고 싶을 때 쓰는 옵션
ASPECT_RATIO_NONE = "사용 안 함 (픽셀 해상도 그대로)"
ASPECT_RATIO_OPTIONS = [ASPECT_RATIO_NONE, "1x1", "16x9", "9x16", "4x3"]

# 이미지 파일에 한해 확장자를 바꾸고 싶을 때 쓰는 옵션 (영상 파일에는 적용 안 함)
IMAGE_OUTPUT_FORMATS = ["원본 유지", "JPG", "PNG", "WEBP"]

# 이미지 파일에 한해 크기/비율은 그대로 두고 용량만 줄이고 싶을 때 쓰는 옵션 (영상 파일에는 적용 안 함)
COMPRESSION_LEVELS = ["압축 안 함", "약한 압축", "강한 압축"]
# JPG/WEBP는 quality 값으로, PNG는 색상 수(팔레트)를 줄여서 압축합니다.
COMPRESSION_QUALITY_MAP = {"압축 안 함": 95, "약한 압축": 75, "강한 압축": 50}
COMPRESSION_PNG_COLORS_MAP = {"압축 안 함": None, "약한 압축": 200, "강한 압축": 96}


def get_resolution(filepath, ext):
    ext_lower = ext.lower()
    if ext_lower in IMAGE_EXTENSIONS:
        res = get_image_resolution(filepath)
    elif ext_lower in VIDEO_EXTENSIONS:
        res = get_video_resolution(filepath)
    else:
        res = None
    return res if res else "해상도미확인"


def sanitize(text):
    # 파일명에 쓸 수 없는 문자 제거, 공백은 그대로 두되 앞뒤 공백만 정리
    text = text.strip()
    return re.sub(r'[\\/:*?"<>|]', "", text)


def build_new_filename(filepath, game_title, feature, country, date_str, include_duration=False,
                        aspect_ratio=None, image_output_format=None):
    base, ext = os.path.splitext(filepath)
    ext_lower = ext.lstrip(".").lower()
    is_video = ext_lower in VIDEO_EXTENSIONS

    if is_video:
        format_label = "VID"  # 영상 파일은 확장자 종류 상관없이 VID로 통일
        final_ext = ext  # 영상은 확장자/포맷 변경을 지원하지 않음
    else:
        if image_output_format and image_output_format != "원본 유지":
            final_ext = "." + image_output_format.lower()
            format_label = image_output_format.upper()
        else:
            final_ext = ext
            format_label = ext.lstrip(".").upper()  # 이미지 등은 실제 확장자 그대로 (예: PNG, JPG)

    # 영상 파일이고 비율 옵션이 선택되어 있으면, 픽셀 해상도 대신 비율 텍스트 사용 (이미지에는 적용 안 함)
    if is_video and aspect_ratio and aspect_ratio != ASPECT_RATIO_NONE:
        resolution = aspect_ratio
    else:
        resolution = get_resolution(filepath, ext.lstrip("."))

    duration_part = ""
    if include_duration and is_video:
        duration_sec = get_video_duration_sec(filepath)
        duration_label = f"{duration_sec}sec" if duration_sec is not None else "길이미확인"
        duration_part = f"_{duration_label}"

    new_name = (
        f"{format_label}_{sanitize(game_title)}_{sanitize(feature)}_{sanitize(country)}"
        f"_{resolution}{duration_part}_{date_str}{final_ext}"
    )
    return new_name, format_label, resolution, is_video


