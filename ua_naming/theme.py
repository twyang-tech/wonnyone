"""Shared colors for classic Tk widgets embedded in the existing ttk theme."""
from tkinter import ttk

IMAGE_ACCENT = '#FFBB18'
VIDEO_ACCENT = '#8BBA08'
WARNING_COLOR = '#e54848'


def palette(widget):
    style = ttk.Style(widget)
    return {
        'background': style.lookup('TFrame', 'background') or widget.winfo_toplevel().cget('background'),
        'foreground': style.lookup('TLabel', 'foreground'),
        'selectbackground': style.lookup('TEntry', 'selectbackground') or style.lookup('TButton', 'background', ('active',)),
        'selectforeground': style.lookup('TEntry', 'selectforeground') or style.lookup('TLabel', 'foreground'),
    }


def style_surface(widget):
    widget.configure(background=palette(widget)['background'])


def style_text(widget):
    colors = palette(widget)
    widget.configure(**{key: value for key, value in colors.items() if value},
                     insertbackground=colors['foreground'], borderwidth=0,
                     highlightthickness=0, padx=8, pady=6)
    widget.tag_configure('warning', foreground=WARNING_COLOR)


def fill_preview(widget, text):
    """Keep ordinary text readable and highlight warning sections without new panels."""
    widget.configure(state='normal')
    widget.delete('1.0', 'end')
    warning_section = False
    for line in text.splitlines(keepends=True):
        if line.strip() in ('경고 (확인 후 진행 가능)', '실행 차단 (수정 필요)'):
            warning_section = True
        warning = warning_section or '세트 경고:' in line or 'Preview 분석 실패:' in line
        widget.insert('end', line, ('warning',) if warning else ())
    widget.configure(state='disabled')
