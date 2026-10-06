"""Accessible confirmation for the already prepared local operation plan."""
import tkinter as tk
from tkinter import ttk
from .theme import WARNING_COLOR, style_surface, style_text


def confirmation_summary(plan):
    changed = sum(
        item.source.name != item.destination.name
        or (item.media.kind == '이미지' and
            (plan.options.output_format != '원본 유지' or plan.options.compression != '압축 안 함'))
        for item in plan.files
    )
    flags = {label: any(f' — {label}:' in warning for warning in plan.warnings)
             for label in ('누락', '중복', '예상 외')}
    lines = [f'총 {len(plan.files)}개 파일을 처리합니다. 계속할까요?',
             f'처리 대상: {len(plan.files)}개 · 변경 예정: {changed}개 · 경고: {len(plan.warnings)}개',
             '변경 예정은 파일명 변경 또는 이미지 변환·압축 대상입니다.',
             '해상도: ' + ' / '.join(f'{label} {"있음" if found else "없음"}' for label, found in flags.items())]
    if plan.options.overwrite:
        lines.append('원본 위치 처리: 이름이 바뀌면 저장 성공 후 원본이 제거됩니다.')
    else:
        lines.append('복사본 저장: 원본은 유지됩니다.')
    return '\n'.join(lines)


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
    if plan.warnings:
        style = ttk.Style(dialog)
        style.configure('Warning.TLabelframe.Label', foreground=WARNING_COLOR)
        frame = ttk.LabelFrame(dialog, text='경고 내용', style='Warning.TLabelframe')
        frame.pack(fill='both', expand=True, padx=18, pady=(0, 12))
        text = tk.Text(frame, height=8, width=72, wrap='word', takefocus=True)
        style_text(text)
        scroll = ttk.Scrollbar(frame, command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y')
        text.pack(fill='both', expand=True)
        text.insert('1.0', '\n'.join(plan.warnings), 'warning')
        text.configure(state='disabled')
        # Text normally consumes Tab; allow traversal through the modal controls.
        text.bind('<Tab>', lambda e: (e.widget.tk_focusNext().focus_set(), 'break')[1])
        text.bind('<Shift-Tab>', lambda e: (e.widget.tk_focusPrev().focus_set(), 'break')[1])
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
