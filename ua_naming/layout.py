"""Presentation-only layout helpers; no file-processing dependencies."""
import sys
import tkinter as tk
from tkinter import ttk, font


class SingleLineLabel(ttk.Label):
    """Keep full text independently; displayed text fits allocated width."""
    def __init__(self, parent, text='', **kwargs):
        self.full_text = text
        super().__init__(parent, text='', width=1, anchor='w', **kwargs)
        self.bind('<Configure>', self._fit)

    def set_text(self, text):
        self.full_text = text.replace('\n', ' / ')
        self._fit()

    def _fit(self, event=None):
        face = font.Font(root=self, font=self.cget('font') or ttk.Style(self).lookup('TLabel', 'font') or 'TkDefaultFont')
        available = max(0, self.winfo_width() - 20)
        text = self.full_text
        if face.measure(text) > available:
            low, high = 0, len(text)
            while low < high:
                middle = (low + high + 1) // 2
                if face.measure(text[:middle] + '…') <= available:
                    low = middle
                else:
                    high = middle - 1
            text = text[:low] + '…' if available >= face.measure('…') else ''
        super().configure(text=text)


def action_slot(parent, row):
    """Identical outer dimensions for CTA, folder and date actions."""
    face = font.nametofont('TkDefaultFont', root=parent)
    slot = ttk.Frame(parent, width=max(84, face.measure('오늘 날짜로') + 24),
                     height=face.metrics('linespace') + 18)
    slot.grid(row=row, column=2, padx=10, pady=6, sticky='e')
    slot.pack_propagate(False)
    return slot


def center_initial_window(window, desired_width=1480, desired_height=760):
    window.update_idletasks()
    x, y, right, bottom = 0, 0, window.winfo_screenwidth(), window.winfo_screenheight()
    if sys.platform == 'win32':
        import ctypes
        from ctypes import wintypes
        class MONITORINFO(ctypes.Structure):
            _fields_ = [('cbSize', wintypes.DWORD), ('rcMonitor', wintypes.RECT),
                        ('rcWork', wintypes.RECT), ('dwFlags', wintypes.DWORD)]
        user32 = ctypes.windll.user32
        user32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
        user32.MonitorFromWindow.restype = wintypes.HANDLE
        user32.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MONITORINFO)]
        info = MONITORINFO(); info.cbSize = ctypes.sizeof(info)
        monitor = user32.MonitorFromWindow(window.winfo_id(), 2)
        if user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
            work = info.rcWork
            x, y, right, bottom = work.left, work.top, work.right, work.bottom
    # Leave space for window decorations as well as taskbar-excluded work area.
    width = max(1, min(desired_width, right - x - 32))
    height = max(1, min(desired_height, bottom - y - 72))
    left = x + (right - x - width) // 2
    top = y + (bottom - y - height - 40) // 2
    window.geometry(f'{width}x{height}{left:+d}{top:+d}')
    window.minsize(min(width, 800), min(height, 480))
