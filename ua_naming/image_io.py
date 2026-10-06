import os
import io
import shutil
from .naming import COMPRESSION_QUALITY_MAP, COMPRESSION_PNG_COLORS_MAP

def save_image_with_options(src_path, dest_path, image_output_format, compression_level):
    """이미지 파일을 지정한 포맷/압축 옵션으로 저장.
    포맷 변경도 없고 압축도 '압축 안 함'이면 원본을 그대로 복사(빠르고 화질 손실 없음).
    가로/세로 크기와 비율은 절대 바꾸지 않고, 색상 정보(품질/팔레트)만 조절합니다.
    src_path와 dest_path가 같은 파일이어도(원본 덮어쓰기) 안전하게 동작합니다."""
    no_format_change = (not image_output_format) or (image_output_format == "원본 유지")
    no_compression = (not compression_level) or (compression_level == "압축 안 함")

    if no_format_change and no_compression:
        if os.path.abspath(src_path) == os.path.abspath(dest_path):
            return  # 바꿀 내용이 없고 자기 자신이면 아무 작업도 필요 없음
        shutil.copy2(src_path, dest_path)
        return

    from PIL import Image
    quality = COMPRESSION_QUALITY_MAP.get(compression_level, 95)
    png_colors = COMPRESSION_PNG_COLORS_MAP.get(compression_level)

    target_ext = os.path.splitext(dest_path)[1].lstrip(".").lower()

    # 원본 파일을 통째로 메모리에 읽어들인 뒤 여는 방식 -> src와 dest가 같은 경로여도(덮어쓰기) 안전함
    with open(src_path, "rb") as f:
        src_bytes = f.read()
    img = Image.open(io.BytesIO(src_bytes))
    img.load()

    if target_ext in ("jpg", "jpeg"):
        img = img.convert("RGB")  # JPEG는 투명도(알파) 지원 안 함
        img.save(dest_path, "JPEG", quality=quality, optimize=True)
    elif target_ext == "webp":
        img.save(dest_path, "WEBP", quality=quality)
    elif target_ext == "png":
        if png_colors:
            has_alpha = img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info)
            base_img = img.convert("RGBA") if has_alpha else img.convert("RGB")
            quantized = base_img.convert(
                "P", palette=Image.ADAPTIVE, colors=png_colors
            )
            quantized.save(dest_path, "PNG", optimize=True)
        else:
            img.save(dest_path, "PNG", optimize=True)
    else:
        # 그 외 포맷(gif, bmp 등)은 그대로 복사
        shutil.copy2(src_path, dest_path)


