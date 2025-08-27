"""UI styling module for CargoSim with dark theme and green accents."""

import tkinter as tk
from tkinter import ttk


def apply_theme(root: tk.Misc):
    """Apply the dark theme with green accents to all widgets."""
    style = ttk.Style()
    style.theme_use("clam")  # allow color overrides

    GREEN = "#00ff4a"
    BLACK = "#000000"
    WHITE = "#ffffff"
    FG = "#d9d9d9"

    # Window background
    try:
        root.configure(bg=BLACK)
    except tk.TclError:
        pass

    # Entries / Combos / Spinboxes
    for name in ("TEntry", "TCombobox", "TSpinbox"):
        style.configure(name, fieldbackground=BLACK, foreground=FG)
    style.configure("TEntry", insertcolor=WHITE)
    style.map("TCombobox", fieldbackground=[("readonly", BLACK)])
    style.configure("TCombobox", background=BLACK, arrowcolor=GREEN)

    # Notebook (tab headers and bar should be white)
    style.configure("TNotebook", background=WHITE, borderwidth=0)
    style.configure("TNotebook.Tab", background=WHITE, foreground="black", padding=(10, 4))
    style.map("TNotebook.Tab",
              background=[("selected", WHITE)],
              foreground=[("selected", "black")])

    # Scales: white trough + green knob (ttk)
    style.configure("Green.Horizontal.TScale", troughcolor=WHITE, background=GREEN)
    style.configure("Green.Vertical.TScale", troughcolor=WHITE, background=GREEN)

    # Checkbox focus ring off (don't highlight label region)
    style.configure("TCheckbutton", background=BLACK)

    # Reduce widget focus outlines globally when possible
    def _strip_focus(widget):
        try:
            widget.configure(highlightthickness=0, takefocus=0)
        except tk.TclError:
            pass
        for child in widget.winfo_children():
            _strip_focus(child)
    _strip_focus(root)
    
    # Mark that our dark theme has been applied
    try:
        root._dark_theme_applied = True
    except:
        pass
