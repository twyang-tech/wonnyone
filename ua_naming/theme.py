"""Shared colors for classic Tk widgets embedded in the existing ttk theme."""
from tkinter import ttk

IMAGE_ACCENT = '#FFBB18'
VIDEO_ACCENT = '#8BBA08'
WARNING_COLOR = '#e54848'
SOURCE_COLOR = '#808080'


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
    widget.tag_configure('source', foreground=SOURCE_COLOR)
    widget.tag_configure('filename', foreground=IMAGE_ACCENT)


def fill_preview(widget, text):
    """Keep ordinary text readable and highlight warning sections without new panels."""
    widget.configure(state='normal')
    widget.delete('1.0', 'end')
    warning_section = False
    for line in text.splitlines(keepends=True):
        if line.strip() in ('경고 (확인 후 진행 가능)', '실행 차단 (수정 필요)'):
            warning_section = True
        warning = warning_section or '세트 경고:' in line or 'Preview 분석 실패:' in line
        if line.startswith('원본:'):
            widget.insert('end', line, ('source',))
        elif line.startswith('최종:'):
            # Both Windows and POSIX separators; only the final filename is accented.
            content = line.rstrip('\r\n')
            split = max(content.rfind('/'), content.rfind('\\')) + 1
            if split == 0:
                split = len('최종: ')
            widget.insert('end', content[:split])
            widget.insert('end', content[split:], ('filename',))
            widget.insert('end', line[len(content):])
        else:
            widget.insert('end', line, ('warning',) if warning else ())
    widget.configure(state='disabled')
