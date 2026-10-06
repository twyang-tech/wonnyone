"""Accessible confirmation for the already prepared local operation plan."""
import tkinter as tk
from tkinter import ttk
from .theme import WARNING_COLOR, style_surface, style_text


def confirmation_summary(plan):
    renamed = sum(item.source.name != item.destination.name for item in plan.files)
    images = sum(item.media.kind == '이미지' for item in plan.files)
    videos = sum(item.media.kind == '영상' for item in plan.files)
    actions = ['파일명 변경' if renamed else '파일명 유지']
    if images and plan.options.output_format != '원본 유지':
        actions.append('이미지 포맷 변환')
    if images and plan.options.compression != '압축 안 함':
        actions.append('이미지 압축')
    actions.append('원본 위치 저장 (이름 변경 시 원본 제거)' if plan.options.overwrite else '복사본 저장 (원본 유지)')
    return '\n'.join([
        f'총 {len(plan.files)}개 파일을 처리합니다.',
        f'이름 변경 예정 {renamed}개',
        f'이미지 {images}개 / 영상 {videos}개',
        f'경고 {len(plan.warnings)}건',
        ' / '.join(actions),
        '위 작업을 실행할까요?',
    ])


def confirm_execution(parent, plan):
    """Return True only on explicit execution; close/Escape always cancel."""
    previous_focus = parent.focus_get()
    previous_grab = parent.grab_current()
    accepted = False
    dialog = tk.Toplevel(parent)
    style_surface(dialog)
    dialog.title('최종 실행 확인')
    dialog.transient(parent)
    dialog.resizable(True, True)
    ttk.Label(dialog, text=confirmation_summary(plan), wraplength=580, justify='left').pack(
        fill='x', padx=18, pady=16)
    buttons = ttk.Frame(dialog)
    buttons.pack(fill='x', padx=18, pady=(0, 16))

    def close(run=False):
        nonlocal accepted
        accepted = run
        dialog.destroy()

    execute = ttk.Button(buttons, text='실행', command=lambda: close(True))
    execute.pack(side='right', padx=(8, 0))
    cancel = ttk.Button(buttons, text='취소', command=close)
    cancel.pack(side='right')

    def enter(event):
        # Execute only when the execution button has keyboard focus.
        close(dialog.focus_get() == execute)
        return 'break'

    dialog.protocol('WM_DELETE_WINDOW', close)
    dialog.bind('<Escape>', lambda e: (close(), 'break')[1])
    dialog.bind('<Return>', enter)
    dialog.bind('<KP_Enter>', enter)
    dialog.update_idletasks()
    dialog.geometry(f'+{parent.winfo_rootx() + 30}+{parent.winfo_rooty() + 30}')
    dialog.wait_visibility()
    dialog.grab_set()
    cancel.focus_set()
    parent.wait_window(dialog)
    if previous_grab is not None and previous_grab.winfo_exists():
        previous_grab.grab_set()
    if previous_focus is not None and previous_focus.winfo_exists():
        previous_focus.focus_set()
    return accepted
