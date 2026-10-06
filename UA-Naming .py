# -*- coding: utf-8 -*-
"""
UA 소재 파일 자동 네이밍 도구 (단순 버전)
=================================
파일명 규칙: 파일포멧_게임타이틀명_소재특징_국가명_해상도_제작완료날짜.확장자

사용자가 입력하는 것: 게임타이틀명 / 소재특징 / 국가명 / 파일 선택
자동으로 채워지는 것: 파일포멧(확장자), 해상도(이미지/영상에서 직접 읽음), 제작완료날짜(오늘 날짜)

------------------------------------------------------------
[사전 설치 - 터미널/명령프롬프트에서 실행]
------------------------------------------------------------
pip install pillow

(선택) 드래그앤드롭으로 파일을 끌어다 놓고 싶다면:
pip install tkinterdnd2
(설치 안 해도 '파일 선택' 버튼으로 정상 사용 가능함)

(선택) 다크 테마(블랙 테마)를 쓰고 싶다면:
pip install ttkbootstrap
(설치 안 해도 자동으로 기본 테마(clam)로 대체되어 정상 동작함)

영상 파일(mp4 등)의 해상도까지 자동 인식하려면 ffmpeg 설치 필요
(설치 후 ffprobe 명령이 동작해야 함. 설치 안 해도 이미지 파일은 정상 동작함)
"""

import os
import re
import shutil
import subprocess
import json
import base64
import io
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False

try:
    import ttkbootstrap as tb
    TTKBOOTSTRAP_AVAILABLE = True
except ImportError:
    TTKBOOTSTRAP_AVAILABLE = False

# 드래그앤드롭을 쓰려면 TkinterDnD.Tk를 상속해야 하므로, 사용 가능 여부에 따라 베이스 클래스 결정
_BaseTk = TkinterDnD.Tk if DND_AVAILABLE else tk.Tk

# ============== 사용자 설정 영역 ==============
OUTPUT_FOLDER_DEFAULT = os.path.join(os.path.expanduser("~"), "Desktop", "UA_소재_완성")


# 창 테마 (ttkbootstrap 설치되어 있으면 이 테마를 우선 사용, 다크 테마 목록: darkly, cyborg, superhero, solar, vapor)
TTKBOOTSTRAP_THEME_NAME = "darkly"

# ttkbootstrap이 없을 때 대신 쓰는 기본 ttk 테마: 'clam', 'alt', 'default', 'classic' 은 어디서나 사용 가능
# Windows 전용: 'vista', 'winnative', 'xpnative' / Mac 전용: 'aqua'
THEME_NAME = "clam"

# 로고 이미지: 나날이 로고가 base64로 인코딩되어 코드 안에 내장되어 있습니다.
# (같은 폴더에 아래 이름의 파일을 두면 그 파일이 우선 사용됩니다 - 로고를 바꾸고 싶을 때 활용)
LOGO_FILENAMES = ["logo.png", "logo.jpg", "logo.jpeg"]
# 창/작업표시줄 아이콘: 같은 폴더에 아래 이름의 파일을 두면 그 파일이 아이콘으로 사용됩니다.
# (없으면 위 로고 이미지를 그대로 아이콘으로 재사용합니다)
ICON_FILENAMES = ["icon.ico", "icon.png"]
LOGO_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAfQAAADhCAYAAAA+ukcWAAAACXBIWXMAAC4jAAAuIwF4pT92AAAHtmlUWHRYTUw6Y29tLmFkb2JlLnhtcAAAAAAAPD94cGFja2V0IGJlZ2luPSLvu78iIGlkPSJXNU0wTXBDZWhpSHpyZVN6TlRjemtjOWQiPz4gPHg6eG1wbWV0YSB4bWxuczp4PSJhZG9iZTpuczptZXRhLyIgeDp4bXB0az0iQWRvYmUgWE1QIENvcmUgOS4xLWMwMDMgNzkuOTY5MGE4N2ZjLCAyMDI1LzAzLzA2LTIwOjUwOjE2ICAgICAgICAiPiA8cmRmOlJERiB4bWxuczpyZGY9Imh0dHA6Ly93d3cudzMub3JnLzE5OTkvMDIvMjItcmRmLXN5bnRheC1ucyMiPiA8cmRmOkRlc2NyaXB0aW9uIHJkZjphYm91dD0iIiB4bWxuczp4bXA9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC8iIHhtbG5zOmRjPSJodHRwOi8vcHVybC5vcmcvZGMvZWxlbWVudHMvMS4xLyIgeG1sbnM6cGhvdG9zaG9wPSJodHRwOi8vbnMuYWRvYmUuY29tL3Bob3Rvc2hvcC8xLjAvIiB4bWxuczp4bXBNTT0iaHR0cDovL25zLmFkb2JlLmNvbS94YXAvMS4wL21tLyIgeG1sbnM6c3RFdnQ9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC9zVHlwZS9SZXNvdXJjZUV2ZW50IyIgeG1sbnM6dGlmZj0iaHR0cDovL25zLmFkb2JlLmNvbS90aWZmLzEuMC8iIHhtbG5zOmV4aWY9Imh0dHA6Ly9ucy5hZG9iZS5jb20vZXhpZi8xLjAvIiB4bXA6Q3JlYXRvclRvb2w9IkFkb2JlIFBob3Rvc2hvcCBDQyAyMDE0IChNYWNpbnRvc2gpIiB4bXA6Q3JlYXRlRGF0ZT0iMjAxNC0xMi0xMFQxNjo0NzoxOSswOTowMCIgeG1wOk1vZGlmeURhdGU9IjIwMjYtMDEtMjFUMTE6MjY6NTkrMDk6MDAiIHhtcDpNZXRhZGF0YURhdGU9IjIwMjYtMDEtMjFUMTE6MjY6NTkrMDk6MDAiIGRjOmZvcm1hdD0iaW1hZ2UvcG5nIiBwaG90b3Nob3A6Q29sb3JNb2RlPSIzIiB4bXBNTTpJbnN0YW5jZUlEPSJ4bXAuaWlkOmFhMDcxMDlkLTBlMTItNDE1Yy04OWMxLWY0YzBjNTkzMWJjZCIgeG1wTU06RG9jdW1lbnRJRD0iYWRvYmU6ZG9jaWQ6cGhvdG9zaG9wOmJhMjVhMTRhLTA2YzMtMjY0NC04NDNiLWE0ZWRmMWUwYTk2ZCIgeG1wTU06T3JpZ2luYWxEb2N1bWVudElEPSJ4bXAuZGlkOmNiYWZkMjliLTcyMzMtNDc4OC1hODRkLWY4ZjcxMWJlZTUyYyIgdGlmZjpPcmllbnRhdGlvbj0iMSIgdGlmZjpYUmVzb2x1dGlvbj0iMzAwMDAwMC8xMDAwMCIgdGlmZjpZUmVzb2x1dGlvbj0iMzAwMDAwMC8xMDAwMCIgdGlmZjpSZXNvbHV0aW9uVW5pdD0iMiIgZXhpZjpDb2xvclNwYWNlPSIxIiBleGlmOlBpeGVsWERpbWVuc2lvbj0iMjAwMCIgZXhpZjpQaXhlbFlEaW1lbnNpb249IjkwMCI+IDx4bXBNTTpIaXN0b3J5PiA8cmRmOlNlcT4gPHJkZjpsaSBzdEV2dDphY3Rpb249ImNyZWF0ZWQiIHN0RXZ0Omluc3RhbmNlSUQ9InhtcC5paWQ6Y2JhZmQyOWItNzIzMy00Nzg4LWE4NGQtZjhmNzExYmVlNTJjIiBzdEV2dDp3aGVuPSIyMDE0LTEyLTEwVDE2OjQ3OjE5KzA5OjAwIiBzdEV2dDpzb2Z0d2FyZUFnZW50PSJBZG9iZSBQaG90b3Nob3AgQ0MgMjAxNCAoTWFjaW50b3NoKSIvPiA8cmRmOmxpIHN0RXZ0OmFjdGlvbj0ic2F2ZWQiIHN0RXZ0Omluc3RhbmNlSUQ9InhtcC5paWQ6YmU3NzlmMzEtYzNjMy00ZWQ2LWEyYzAtMjI1OWU3Yjg4MThjIiBzdEV2dDp3aGVuPSIyMDI2LTAxLTIxVDExOjI2OjU5KzA5OjAwIiBzdEV2dDpzb2Z0d2FyZUFnZW50PSJBZG9iZSBQaG90b3Nob3AgMjYuNiAoTWFjaW50b3NoKSIgc3RFdnQ6Y2hhbmdlZD0iLyIvPiA8cmRmOmxpIHN0RXZ0OmFjdGlvbj0ic2F2ZWQiIHN0RXZ0Omluc3RhbmNlSUQ9InhtcC5paWQ6YWEwNzEw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"
# ================================================


from ua_naming.naming import (
    build_new_filename, sanitize, ASPECT_RATIO_NONE, ASPECT_RATIO_OPTIONS,
    IMAGE_OUTPUT_FORMATS, COMPRESSION_LEVELS,
)
from ua_naming.media import VIDEO_EXTENSIONS
from ua_naming.planning import Options, build_plan, execute_plan, describe_plan
from ua_naming.theme import IMAGE_ACCENT, VIDEO_ACCENT, WARNING_COLOR, style_surface, style_text, fill_preview
from ua_naming.layout import SingleLineLabel, action_slot, center_initial_window
from ua_naming.dialogs import confirm_execution
from ua_naming.settings import load_config

CONFIG = load_config()
GAME_TITLES = CONFIG["games"] + ["직접입력"]
COUNTRIES = CONFIG["languages"] + ["직접입력"]


class ToolTip:
    """위젯에 마우스를 올리면 잠깐 뒤에 작은 설명 풍선을 띄워주는 간단한 툴팁.
    외부 라이브러리 없이 tkinter 기본 기능만으로 동작합니다."""

    def __init__(self, widget, text, delay=400):
        self.widget = widget
        self.text = text
        self.delay = delay  # 마우스를 올리고 이 시간(ms)이 지나야 표시됨
        self.tipwindow = None
        self._after_id = None
        widget.bind("<Enter>", self._schedule)
        widget.bind("<Leave>", self._hide)
        widget.bind("<ButtonPress>", self._hide)

    def _schedule(self, event=None):
        self._cancel()
        self._after_id = self.widget.after(self.delay, self._show)

    def _cancel(self):
        if self._after_id:
            self.widget.after_cancel(self._after_id)
            self._after_id = None

    def _show(self):
        if self.tipwindow or not self.text:
            return
        x = self.widget.winfo_rootx() + 10
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        tw = self.tipwindow = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)  # 창 테두리/타이틀바 없이 풍선만 표시
        try:
            tw.wm_attributes("-topmost", True)
        except Exception:
            pass
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            tw, text=self.text, justify="left",
            background="#ffffe0", foreground="#000000",
            relief="solid", borderwidth=1, font=("", 9),
            wraplength=320,
        )
        label.pack(ipadx=6, ipady=3)

    def _hide(self, event=None):
        self._cancel()
        if self.tipwindow:
            self.tipwindow.destroy()
            self.tipwindow = None


class App(_BaseTk):
    def __init__(self):
        super().__init__()
        self.title("UA 소재 자동 네이밍 도구")
        self.selected_files = []
        self._preview_job = None

        # ---- 테마 적용 ----
        # ttkbootstrap이 설치되어 있으면 다크 테마(TTKBOOTSTRAP_THEME_NAME) 적용,
        # 없으면 자동으로 기본 ttk 테마(THEME_NAME)로 대체 (에러 없이 정상 동작)
        self._listbox_colors = None
        if TTKBOOTSTRAP_AVAILABLE:
            try:
                tb_style = tb.Style(theme=TTKBOOTSTRAP_THEME_NAME)
                colors = tb_style.colors
                self._listbox_colors = {
                    "bg": colors.bg, "fg": colors.fg,
                    "selectbackground": colors.selectbg, "selectforeground": colors.selectfg,
                }
            except Exception:
                TTKBOOTSTRAP_FAILED = True
            else:
                TTKBOOTSTRAP_FAILED = False
        else:
            TTKBOOTSTRAP_FAILED = True

        if TTKBOOTSTRAP_FAILED:
            style = ttk.Style(self)
            try:
                style.theme_use(THEME_NAME)
            except tk.TclError:
                pass
            style.configure("TButton", padding=6)
            style.configure("TLabel", padding=2)
            style.configure("TCheckbutton", padding=2)

        # ---- 상단 헤더 (로고 + 제목) ----
        header = ttk.Frame(self)
        header.pack(fill="x", padx=10, pady=(10, 0))

        self.logo_image = None  # PhotoImage 참조 유지 (안 하면 가비지컬렉션으로 사라짐)
        try:
            from PIL import Image, ImageTk
            logo_bytes = None

            # 같은 폴더에 로고 파일이 있으면 그걸 우선 사용 (로고를 바꾸고 싶을 때 활용)
            script_dir = os.path.dirname(os.path.abspath(__file__))
            for logo_name in LOGO_FILENAMES:
                logo_path = os.path.join(script_dir, logo_name)
                if os.path.exists(logo_path):
                    with open(logo_path, "rb") as f:
                        logo_bytes = f.read()
                    break

            # 없으면 코드에 내장된 기본 로고 사용
            if logo_bytes is None and LOGO_BASE64 and LOGO_BASE64 != "PLACEHOLDER":
                logo_bytes = base64.b64decode(LOGO_BASE64)

            if logo_bytes:
                img = Image.open(io.BytesIO(logo_bytes))
                img.thumbnail((56, 56))
                self.logo_image = ImageTk.PhotoImage(img)
                ttk.Label(header, image=self.logo_image).pack(side="left", padx=(0, 10))

            # ---- 창/작업표시줄 아이콘 설정 ----
            # 같은 폴더에 icon.ico/icon.png가 있으면 그걸 우선 사용, 없으면 위 로고 이미지를 재사용
            icon_bytes = None
            for icon_name in ICON_FILENAMES:
                icon_path = os.path.join(script_dir, icon_name)
                if os.path.exists(icon_path):
                    with open(icon_path, "rb") as f:
                        icon_bytes = f.read()
                    break
            if icon_bytes is None:
                icon_bytes = logo_bytes  # 별도 아이콘 파일이 없으면 로고를 그대로 아이콘으로 사용

            if icon_bytes:
                icon_img = Image.open(io.BytesIO(icon_bytes))
                self._icon_image = ImageTk.PhotoImage(icon_img)  # 참조 유지 (가비지컬렉션 방지)
                self.iconphoto(True, self._icon_image)
        except Exception:
            pass

        ttk.Label(header, text="UA 소재 자동 네이밍 도구", font=("", 14, "bold")).pack(side="left")

        pad = {"padx": 10, "pady": 6}

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, padx=10, pady=10)
        body.columnconfigure(0, weight=1, uniform="main")
        body.columnconfigure(2, weight=1, uniform="main")
        body.rowconfigure(0, weight=1)
        left = ttk.Frame(body)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left.columnconfigure(0, weight=1)
        left.rowconfigure(22, weight=1)
        ttk.Separator(body, orient="vertical").grid(row=0, column=1, sticky="ns")
        settings = ttk.Frame(body)
        settings.grid(row=0, column=2, sticky="nsew", padx=(10, 0))
        run_button = ttk.Button(settings, text="확인 후 실행", command=self.run_process)
        run_button.pack(side="bottom", fill="x", padx=10, pady=(12, 6))
        ToolTip(run_button, "위에서 설정한 옵션대로 파일 이름을 바꿔 지정한 폴더에 복사본으로 저장합니다.")

        canvas = tk.Canvas(settings, highlightthickness=0, width=650)
        style_surface(canvas)
        body_scroll = ttk.Scrollbar(settings, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=body_scroll.set)
        body_scroll.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        frame = ttk.Frame(canvas)
        frame_window = canvas.create_window((0, 0), window=frame, anchor="nw")
        frame.bind("<Configure>", lambda event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(frame_window, width=event.width))
        frame.columnconfigure(1, weight=1)  # 1번 열(입력창들)이 전부 같은 너비로 맞춰지도록

        # ---- 실시간 파일명 미리보기 (맨 위, 옵션 바꿀 때마다 자동 갱신) ----
        preview_box = ttk.Frame(left, relief="groove", borderwidth=2)
        preview_box.grid(row=0, column=0, sticky="we", padx=10, pady=(0, 10))
        preview_box.columnconfigure(1, weight=1)

        ttk.Label(preview_box, text="파일명 미리보기 (예시)").grid(
            row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(6, 4)
        )
        ttk.Label(preview_box, text="이미지 예시", width=10, anchor="w").grid(
            row=1, column=0, sticky="w", padx=(8, 0), pady=(0, 2)
        )
        self.preview_image_var = tk.StringVar()
        ttk.Label(
            preview_box, textvariable=self.preview_image_var, foreground=IMAGE_ACCENT
        ).grid(row=1, column=1, sticky="w", padx=(0, 8), pady=(0, 2))

        ttk.Label(preview_box, text="영상 예시", width=10, anchor="w").grid(
            row=2, column=0, sticky="w", padx=(8, 0), pady=(0, 8)
        )
        self.preview_video_var = tk.StringVar()
        ttk.Label(
            preview_box, textvariable=self.preview_video_var, foreground=VIDEO_ACCENT
        ).grid(row=2, column=1, sticky="w", padx=(0, 8), pady=(0, 8))

        ttk.Label(frame, text="게임 타이틀명").grid(row=1, column=0, sticky="w", **pad)
        self.game_title_var = tk.StringVar(value=GAME_TITLES[0])
        self.game_title_combo = ttk.Combobox(frame, textvariable=self.game_title_var, values=GAME_TITLES)
        self.game_title_combo.grid(row=1, column=1, sticky="we", **pad)
        ToolTip(self.game_title_combo, "목록에서 게임을 선택하거나 '직접입력'을 고른 뒤 직접 타이핑하세요.")

        ttk.Label(frame, text="소재특징").grid(row=2, column=0, sticky="w", **pad)
        self.feature_var = tk.StringVar()
        feature_entry = ttk.Entry(frame, textvariable=self.feature_var)
        feature_entry.grid(row=2, column=1, sticky="we", **pad)
        ToolTip(feature_entry, "파일명에 들어갈 소재 특징을 입력하세요. 예: STICKER, 엔드카드, 뮤직박스 등")
        self.cta_var = tk.BooleanVar(value=False)
        cta_box = action_slot(frame, 3)
        cta_check = ttk.Checkbutton(cta_box, text="+CTA", variable=self.cta_var)
        cta_check.configure(padding=(6, 3))
        cta_check.pack(fill="both", expand=True)
        ToolTip(cta_check, "체크하면 소재특징 뒤에 '+CTA'가 자동으로 붙습니다. 예: STICKER → STICKER+CTA")

        ttk.Label(frame, text="국가명").grid(row=3, column=0, sticky="w", **pad)
        self.country_var = tk.StringVar(value=COUNTRIES[0])
        self.country_combo = ttk.Combobox(frame, textvariable=self.country_var, values=COUNTRIES)
        self.country_combo.grid(row=3, column=1, sticky="we", **pad)
        ToolTip(self.country_combo, "소재가 사용될 국가/언어 코드를 선택하세요.")

        ttk.Label(frame, text="완성 파일 저장 폴더").grid(row=4, column=0, sticky="w", **pad)
        self.output_folder_var = tk.StringVar(value=OUTPUT_FOLDER_DEFAULT)
        self.out_entry = ttk.Entry(frame, textvariable=self.output_folder_var)
        self.out_entry.grid(row=4, column=1, sticky="we", **pad)
        ToolTip(self.out_entry, "이름이 바뀐 파일 복사본이 저장될 폴더입니다. 원본 파일은 그대로 남습니다.")
        self.folder_button = ttk.Button(action_slot(frame, 4), text="폴더 변경", padding=(6, 3), command=self.choose_output_folder)
        self.folder_button.pack(fill="both", expand=True)
        ToolTip(self.folder_button, "저장 폴더를 다른 곳으로 바꾸고 싶을 때 클릭하세요.")

        ttk.Label(frame, text="제작완료날짜 (yymmdd)").grid(row=5, column=0, sticky="w", **pad)
        self.date_var = tk.StringVar(value=datetime.now().strftime("%y%m%d"))
        date_entry = ttk.Entry(frame, textvariable=self.date_var)
        date_entry.grid(row=5, column=1, sticky="we", **pad)
        ToolTip(date_entry, "기본값은 오늘 날짜예요. 다른 날짜를 쓰고 싶으면 yymmdd 형식(예: 260729)으로 직접 수정하세요.")
        today_button = ttk.Button(
            action_slot(frame, 5), text="오늘 날짜로", padding=(6, 3),
            command=lambda: self.date_var.set(datetime.now().strftime("%y%m%d"))
        )
        today_button.pack(fill="both", expand=True)
        ToolTip(today_button, "날짜를 다시 오늘 날짜로 되돌립니다.")

        self.include_duration_var = tk.BooleanVar(value=False)
        duration_check = ttk.Checkbutton(
            frame, text=" 영상 파일에 길이(초) 포함 (예: 30sec) - 이미지에는 영향 없음",
            variable=self.include_duration_var
        )
        duration_check.grid(row=6, column=0, columnspan=3, sticky="w", padx=10)
        ToolTip(duration_check, "체크하면 영상 파일명에 재생 길이가 초 단위로 추가됩니다. 이미지 파일에는 적용되지 않습니다.")

        ttk.Label(frame, text="영상 비율 표시 (선택)").grid(row=7, column=0, sticky="w", **pad)
        self.aspect_ratio_var = tk.StringVar(value=ASPECT_RATIO_NONE)
        self.aspect_ratio_combo = ttk.Combobox(
            frame, textvariable=self.aspect_ratio_var, values=ASPECT_RATIO_OPTIONS,
            state="readonly"
        )
        self.aspect_ratio_combo.grid(row=7, column=1, sticky="we", **pad)
        ToolTip(self.aspect_ratio_combo, "픽셀 해상도 대신 비율로 표시하고 싶을 때 선택하세요. 영상 파일에만 적용되고 이미지에는 영향 없습니다.")
        SingleLineLabel(
            frame, text="픽셀 단위가 아닌, 비율로 표시가 필요한 경우 사용 (영상 파일에만 적용, 이미지는 영향 없음)",
            foreground="gray"
        ).grid(row=8, column=0, columnspan=3, sticky="we", padx=10, pady=(2, 6))

        ttk.Label(frame, text="이미지 출력 포맷 (선택)").grid(row=9, column=0, sticky="w", **pad)
        self.image_output_format_var = tk.StringVar(value=IMAGE_OUTPUT_FORMATS[0])
        self.image_output_format_combo = ttk.Combobox(
            frame, textvariable=self.image_output_format_var, values=IMAGE_OUTPUT_FORMATS,
            state="readonly"
        )
        self.image_output_format_combo.grid(row=9, column=1, sticky="we", **pad)
        ToolTip(self.image_output_format_combo, "이미지 파일의 확장자를 바꿔서 저장하고 싶을 때 선택하세요. 영상 파일에는 적용되지 않습니다.")

        ttk.Label(frame, text="이미지 용량 압축 (선택)").grid(row=10, column=0, sticky="w", **pad)
        self.compression_level_var = tk.StringVar(value=COMPRESSION_LEVELS[0])
        self.compression_level_combo = ttk.Combobox(
            frame, textvariable=self.compression_level_var, values=COMPRESSION_LEVELS,
            state="readonly"
        )
        self.compression_level_combo.grid(row=10, column=1, sticky="we", **pad)
        ToolTip(
            self.compression_level_combo,
            "가로/세로 크기와 비율은 그대로 두고, 색상 정보만 줄여서 파일 용량을 줄입니다. 영상 파일에는 적용되지 않습니다."
        )
        SingleLineLabel(
            frame,
            text="해상도·비율은 바뀌지 않고, 색상 정보만 줄여 용량을 줄입니다 (이미지 파일에만 적용, 영상은 영향 없음)",
            foreground="gray"
        ).grid(row=11, column=0, columnspan=3, sticky="we", padx=10, pady=(2, 6))

        self.keep_original_name_var = tk.BooleanVar(value=False)
        keep_name_check = ttk.Checkbutton(
            frame,
            text=" 파일명은 그대로 두고 포맷변환/압축만 적용 (게임타이틀명 등 나머지 입력값은 무시됨)",
            variable=self.keep_original_name_var
        )
        keep_name_check.grid(row=12, column=0, columnspan=3, sticky="w", padx=10)
        ToolTip(
            keep_name_check,
            "체크하면 파일 이름은 원본 그대로 두고, 이미지 출력 포맷/용량 압축만 적용해서 저장합니다. "
            "게임타이틀명·소재특징·국가명·날짜 등은 사용되지 않습니다."
        )

        self.overwrite_original_var = tk.BooleanVar(value=False)
        overwrite_check = ttk.Checkbutton(
            frame,
            text=" 원본 파일에 덮어쓰기 (복사본을 만들지 않고 원본 위치에 바로 저장 — 되돌릴 수 없음)",
            variable=self.overwrite_original_var,
            command=self._on_overwrite_toggle,
        )
        overwrite_check.grid(row=13, column=0, columnspan=3, sticky="w", padx=10)
        ToolTip(
            overwrite_check,
            "체크하면 '완성 파일 저장 폴더' 설정은 무시되고, 원본 파일이 있던 바로 그 위치에 결과물이 저장됩니다. "
            "이름이 바뀌는 경우 원래 파일은 삭제됩니다. 되돌릴 수 없으니 신중하게 사용하세요."
        )

        ttk.Label(frame, text="파일명 문자열 치환 (선택)").grid(row=14, column=0, sticky="w", **pad)
        find_replace_frame = ttk.Frame(frame)
        find_replace_frame.grid(row=14, column=1, columnspan=2, sticky="we", padx=(0, 10), pady=6)
        self.find_text_var = tk.StringVar()
        find_entry = ttk.Entry(find_replace_frame, textvariable=self.find_text_var, width=14)
        find_entry.pack(side="left")
        ToolTip(find_entry, "파일명에서 찾을 문자열을 입력하세요. 비워두면 치환이 적용되지 않습니다.")
        ttk.Label(find_replace_frame, text=" → ").pack(side="left")
        self.replace_text_var = tk.StringVar()
        replace_entry = ttk.Entry(find_replace_frame, textvariable=self.replace_text_var, width=14)
        replace_entry.pack(side="left")
        ToolTip(replace_entry, "위에서 찾은 문자열을 이 문자열로 바꿉니다. 비워두면 그냥 삭제(공백으로 치환)됩니다.")
        SingleLineLabel(
            frame,
            text="파일명(확장자 제외)에서 찾을 문자열을 다른 문자열로 바꿉니다. 예: 공백 → _  (비워두면 적용 안 함)",
            foreground="gray"
        ).grid(row=15, column=0, columnspan=3, sticky="we", padx=10, pady=(2, 6))

        drop_hint = "파일 선택 (여러 개 가능) — 또는 아래 목록에 파일을 직접 드래그해서 놓아도 됩니다" \
            if DND_AVAILABLE else "파일 선택 (여러 개 가능)"
        select_button = ttk.Button(left, text=drop_hint, command=self.choose_files)
        select_button.grid(row=16, column=0, sticky="we", **pad)
        ToolTip(select_button, "이름을 바꿀 소재 파일을 선택하세요. 여러 개를 한 번에 고를 수 있습니다.")

        for var in (
            self.game_title_var, self.feature_var, self.cta_var,
            self.country_var, self.date_var, self.include_duration_var, self.aspect_ratio_var,
            self.image_output_format_var, self.keep_original_name_var,
            self.find_text_var, self.replace_text_var, self.output_folder_var,
            self.overwrite_original_var, self.compression_level_var,
        ):
            var.trace_add("write", self.update_preview)
        self.update_preview()

        self.file_listbox = tk.Listbox(left, height=10, width=70, selectmode=tk.EXTENDED)
        if self._listbox_colors:
            self.file_listbox.configure(**self._listbox_colors)
        self.file_listbox.grid(row=17, column=0, sticky="we", **pad)
        self.file_listbox.bind("<Delete>", lambda event: self.remove_selected_files())
        self.file_listbox.bind("<BackSpace>", lambda event: self.remove_selected_files())
        ToolTip(self.file_listbox, "선택된 파일 목록입니다. 클릭 후 Delete 키로 삭제할 수 있습니다.")

        if DND_AVAILABLE:
            self.file_listbox.drop_target_register(DND_FILES)
            self.file_listbox.dnd_bind("<<Drop>>", self.on_drop)
            hint = "위 목록에 파일을 마우스로 끌어다 놓으면 바로 추가됩니다. (목록 클릭 후 Delete 키로도 삭제 가능)"
            ttk.Label(left, text=hint, foreground="gray", wraplength=520).grid(
                row=18, column=0, sticky="w", padx=10
            )
        else:
            hint = ("드래그앤드롭을 쓰려면 터미널에서 'pip install tkinterdnd2' 실행 후 프로그램을 다시 켜주세요. "
                    "(설치 안 해도 '파일 선택' 버튼으로 정상 사용 가능합니다. 목록 클릭 후 Delete 키로 삭제 가능)")
            ttk.Label(left, text=hint, foreground="gray", wraplength=520).grid(
                row=18, column=0, sticky="w", padx=10
            )

        list_button_frame = ttk.Frame(left)
        list_button_frame.grid(row=19, column=0, sticky="we", padx=10, pady=6)
        remove_button = ttk.Button(list_button_frame, text="선택 항목 삭제", command=self.remove_selected_files)
        remove_button.pack(side="right", padx=(0, 5))
        ToolTip(remove_button, "목록에서 클릭(또는 Ctrl/Shift로 여러 개 선택)한 파일만 목록에서 제거합니다.")
        clear_button = ttk.Button(list_button_frame, text="전체 비우기", command=self.clear_all_files)
        clear_button.pack(side="right", padx=5)
        ToolTip(clear_button, "목록에 담긴 파일을 전부 비웁니다. (실제 파일은 삭제되지 않습니다)")

        self.status_var = tk.StringVar(value="대기 중")
        preview_heading = ttk.Frame(left)
        preview_heading.grid(row=21, column=0, sticky="we", padx=10, pady=(4, 2))
        preview_heading.columnconfigure(0, weight=1)
        ttk.Label(preview_heading, text="선택 파일 Preview · 소재 세트").grid(row=0, column=0, sticky="w")
        ttk.Label(preview_heading, textvariable=self.status_var, foreground=IMAGE_ACCENT).grid(row=0, column=1, sticky="e")

        # One continuous outer edge; children are inset and carry no panel border.
        panel_style = ttk.Style(self)
        border_color = (panel_style.lookup("TEntry", "bordercolor") or
                        panel_style.lookup("TButton", "background"))
        preview_border = tk.Frame(left, borderwidth=0, highlightthickness=1,
                                  highlightbackground=border_color, highlightcolor=border_color)
        style_surface(preview_border)
        preview_border.grid(row=22, column=0, sticky="nsew", padx=10, pady=6)
        preview_border.columnconfigure(0, weight=1)
        preview_border.rowconfigure(0, weight=1)
        preview_frame = ttk.Frame(preview_border)
        preview_frame.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(1, weight=1)
        self.preview_alert = SingleLineLabel(preview_frame, foreground=WARNING_COLOR, padding=(8, 6))
        self.preview_alert.grid(row=0, column=0, columnspan=2, sticky="we")
        self.actual_preview = tk.Text(preview_frame, height=10, width=1, wrap="word")
        style_text(self.actual_preview)
        scroll = ttk.Scrollbar(preview_frame, command=self.actual_preview.yview)
        self.actual_preview.configure(yscrollcommand=scroll.set)
        scroll.grid(row=1, column=1, sticky="ns")
        self.actual_preview.grid(row=1, column=0, sticky="nsew")
        self.actual_preview.configure(state="disabled")

        center_initial_window(self)

        # ---- Windows 타이틀바(상단 제목표시줄)도 다크로 (Windows 10 1809+/11 전용, 그 외 OS는 무시됨) ----
        self._apply_windows_dark_titlebar()

    def _apply_windows_dark_titlebar(self):
        import sys
        if sys.platform != "win32":
            return
        try:
            import ctypes
            self.update()
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            value = ctypes.c_int(1)
            # 20: Windows 11 / 최신 Windows 10, 19: 예전 Windows 10 빌드 - 둘 다 시도
            for attribute in (20, 19):
                result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, attribute, ctypes.byref(value), ctypes.sizeof(value)
                )
                if result == 0:
                    break
        except Exception:
            pass  # 다크 타이틀바 적용 실패해도 프로그램은 정상 동작

    def update_preview(self, *args):
        self.schedule_file_preview()
        find_text = self.find_text_var.get()
        replace_text = self.replace_text_var.get()

        if self.keep_original_name_var.get():
            image_output_format = self.image_output_format_var.get()
            ext_note = f".{image_output_format.lower()}" if image_output_format and image_output_format != "원본 유지" else "(원본 확장자 유지)"
            note = "  (파일명 치환 적용됨)" if find_text else ""
            self.preview_image_var.set(f"원본파일명{ext_note}  ← 파일명 유지 모드{note}")
            self.preview_video_var.set(f"원본파일명.mp4  ← 파일명 유지 모드 (영상은 항상 원본 그대로){note}")
            return

        game_title = sanitize(self.game_title_var.get().strip()) or "게임타이틀"
        feature_raw = self.feature_var.get().strip() or "소재특징"
        if self.cta_var.get():
            feature_raw = feature_raw + "+CTA"
        feature = sanitize(feature_raw)
        country = sanitize(self.country_var.get().strip()) or "국가"
        date_str = sanitize(self.date_var.get().strip()) or datetime.now().strftime("%y%m%d")

        image_output_format = self.image_output_format_var.get()
        if image_output_format and image_output_format != "원본 유지":
            image_ext = image_output_format.lower()
            image_format_label = image_output_format.upper()
        else:
            image_ext = "png"
            image_format_label = "PNG"
        image_example = f"{image_format_label}_{game_title}_{feature}_{country}_1920x1080_{date_str}.{image_ext}"

        aspect = self.aspect_ratio_var.get()
        video_resolution = aspect if aspect and aspect != ASPECT_RATIO_NONE else "1920x1080"
        duration_part = "_30sec" if self.include_duration_var.get() else ""
        video_example = f"VID_{game_title}_{feature}_{country}_{video_resolution}{duration_part}_{date_str}.mp4"

        find_text = self.find_text_var.get()
        replace_text = self.replace_text_var.get()
        if find_text:
            def _apply_find_replace(name):
                base, ext = os.path.splitext(name)
                return base.replace(find_text, replace_text) + ext
            image_example = _apply_find_replace(image_example)
            video_example = _apply_find_replace(video_example)

        self.preview_image_var.set(image_example)
        self.preview_video_var.set(video_example)

    def _on_overwrite_toggle(self):
        if self.overwrite_original_var.get():
            self.out_entry.state(["disabled"])
            self.folder_button.state(["disabled"])
        else:
            self.out_entry.state(["!disabled"])
            self.folder_button.state(["!disabled"])

    def choose_output_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output_folder_var.set(folder)

    def choose_files(self):
        files = filedialog.askopenfilenames(title="소재 파일 선택")
        if files:
            for f in files:
                if f not in self.selected_files:
                    self.selected_files.append(f)
            self.refresh_file_listbox()

    def on_drop(self, event):
        # event.data는 공백 포함 경로가 {중괄호}로 감싸져 올 수 있어 splitlist로 안전하게 분리
        paths = self.tk.splitlist(event.data)
        added = 0
        for p in paths:
            if os.path.isfile(p) and p not in self.selected_files:
                self.selected_files.append(p)
                added += 1
        if added:
            self.refresh_file_listbox()

    def refresh_file_listbox(self):
        self.schedule_file_preview()
        self.file_listbox.delete(0, tk.END)
        for f in self.selected_files:
            self.file_listbox.insert(tk.END, os.path.basename(f))

    def remove_selected_files(self):
        selected_indices = self.file_listbox.curselection()
        if not selected_indices:
            messagebox.showinfo("알림", "삭제할 파일을 목록에서 먼저 선택해주세요.\n(Ctrl 또는 Shift로 여러 개 선택 가능)")
            return
        for index in sorted(selected_indices, reverse=True):
            del self.selected_files[index]
        self.refresh_file_listbox()

    def clear_all_files(self):
        if not self.selected_files:
            return
        if messagebox.askyesno("확인", "선택된 파일 목록을 전부 비울까요?"):
            self.selected_files = []
            self.refresh_file_listbox()

    def current_options(self):
        return Options(
            game=self.game_title_var.get().strip(), feature=self.feature_var.get().strip(),
            language=self.country_var.get().strip(), date=self.date_var.get().strip(),
            cta=self.cta_var.get(), duration=self.include_duration_var.get(),
            aspect=self.aspect_ratio_var.get(), output_format=self.image_output_format_var.get(),
            compression=self.compression_level_var.get(), keep_name=self.keep_original_name_var.get(),
            overwrite=self.overwrite_original_var.get(), output_dir=self.output_folder_var.get().strip(),
            find=self.find_text_var.get(), replace=self.replace_text_var.get())

    def schedule_file_preview(self):
        if not hasattr(self, "find_text_var"):
            return
        if self._preview_job:
            self.after_cancel(self._preview_job)
        self._preview_job = self.after(350, self.refresh_actual_preview)

    def refresh_actual_preview(self):
        self._preview_job = None
        if not hasattr(self, "actual_preview"):
            return
        try:
            plan = build_plan(tuple(self.selected_files), self.current_options(), CONFIG)
            text = describe_plan(plan, include_warnings=False)
            alerts = (["실행 차단 (수정 필요)"] + plan.errors if plan.errors else [])
            if plan.warnings:
                alerts += [f"경고 {len(plan.warnings)}건 (확인 후 진행 가능)"] + plan.warnings
            notice = (f"실행 차단 {len(plan.errors)}건" if plan.errors else
                      f"경고 {len(plan.warnings)}건 발견" if plan.warnings else "Preview 갱신 완료")
        except Exception as exc:
            text = ""
            notice = "Preview 분석 실패"
            alerts = [f"Preview 분석 실패: {exc}"]
        self.preview_alert.set_text(" / ".join(alerts) if alerts else "정상: 경고 없음")
        self.preview_alert.configure(foreground=WARNING_COLOR if alerts else IMAGE_ACCENT)
        fill_preview(self.actual_preview, text)
        self.show_toast(notice)

    def show_toast(self, text):
        # Nonmodal, does not capture focus or interrupt keyboard navigation.
        if not hasattr(self, "_toast"):
            self._toast = ttk.Label(self, padding=(12, 8), relief="solid", takefocus=False)
            self._toast_job = None
        if self._toast_job:
            self.after_cancel(self._toast_job)
        self._toast.configure(text=text, foreground=WARNING_COLOR if ("경고" in text or "차단" in text or "실패" in text) else ttk.Style(self).lookup("TLabel", "foreground"))
        self._toast.place(relx=1.0, rely=1.0, anchor="se", x=-16, y=-16)
        self._toast.lift()
        self._toast_job = self.after(2500, self.hide_toast)

    def hide_toast(self):
        self._toast.place_forget()
        self._toast_job = None

    def run_process(self):
        try:
            plan = build_plan(tuple(self.selected_files), self.current_options(), CONFIG)
        except Exception as exc:
            messagebox.showerror("Preview 오류", str(exc))
            return
        # All details stay in the main Preview; only one summary modal precedes execution.
        self.refresh_actual_preview()
        if plan.errors:
            self.status_var.set("실행 차단: Preview 상단의 오류를 수정해주세요.")
            return
        if not confirm_execution(self, plan):
            return
        try:
            results, errors = execute_plan(plan)
        except Exception as exc:
            messagebox.showerror("실행 차단", str(exc))
            self.refresh_actual_preview()
            return
        self.status_var.set(f"완료: {len(results)}개 / 실패: {len(errors)}개")
        detail = "저장 결과:\n" + "\n".join(results)
        if errors:
            detail += "\n\n실패:\n" + "\n".join(errors)
        messagebox.showinfo("처리 결과", detail)
        self.refresh_actual_preview()


if __name__ == "__main__":
    app = App()
    app.mainloop()
