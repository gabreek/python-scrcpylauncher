# FILE: gui/widgets.py
# PURPOSE: Contém widgets reutilizáveis para a interface gráfica.

import tkinter as tk
from tkinter import ttk

def create_scrolling_frame(parent):
    """Cria um frame com uma barra de rolagem vertical."""
    canvas = tk.Canvas(parent, highlightthickness=0)
    scrollbar = ttk.Scrollbar(parent, orient='vertical', command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

    def on_canvas_configure(event):
        canvas.itemconfig(canvas_window, width=event.width)
    canvas.bind("<Configure>", on_canvas_configure)

    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    def _on_mousewheel(event):
        if event.num == 4:
            canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            canvas.yview_scroll(1, "units")
        else:
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    for widget in (parent, canvas, scrollable_frame, scrollbar):
        widget.bind("<MouseWheel>", _on_mousewheel)
        widget.bind("<Button-4>", _on_mousewheel)
        widget.bind("<Button-5>", _on_mousewheel)

    return canvas, scrollable_frame

def create_slider(parent, label, var, from_, to, step=1, suffix=""):
    """Cria um widget de slider simples."""
    frm = ttk.Frame(parent)
    frm.pack(fill='x', padx=10, pady=2)
    ttk.Label(frm, text=label, width=15, anchor='w').pack(side='left')
    value_label = ttk.Label(frm, text=f"{var.get()}{suffix}")
    value_label.pack(side='right')

    def update_label(val):
        value_label.config(text=f"{int(float(val))}{suffix}")

    scale = ttk.Scale(
        frm, from_=from_, to=to, variable=var, orient='horizontal',
        value=var.get(), command=update_label
    )
    scale.pack(side='left', fill='x', expand=True)

    # Problema 2: Adicionando o scroll do mouse ao slider
    def on_scroll(event):
        current_val = var.get()
        if event.num == 4 or (hasattr(event, 'delta') and event.delta > 0):
            new_val = min(to, current_val + step)
        elif event.num == 5 or (hasattr(event, 'delta') and event.delta < 0):
            new_val = max(from_, current_val - step)
        else:
            return
        var.set(new_val)
        update_label(new_val)

    scale.bind("<MouseWheel>", on_scroll)
    scale.bind("<Button-4>", on_scroll)
    scale.bind("<Button-5>", on_scroll)

    update_label(var.get())

def create_slider_with_buttons(parent, label, var, from_, to, step=1, suffix="", presets=[], button_style="Small.TButton"):
    """Cria um widget de slider com botões de predefinição."""
    main_frame = ttk.Frame(parent)
    main_frame.pack(fill='x', padx=10, pady=2)

    top_frame = ttk.Frame(main_frame)
    top_frame.pack(fill='x')

    ttk.Label(top_frame, text=label, width=15, anchor='w').pack(side='left')
    value_label = ttk.Label(top_frame, text=f"{var.get()}{suffix}", width=6)
    value_label.pack(side='right', padx=(5,0))

    def update_label(val):
        value_label.config(text=f"{int(float(val))}{suffix}")

    scale = ttk.Scale(
        top_frame, from_=from_, to=to, variable=var, orient='horizontal',
        value=var.get(), command=update_label
    )
    scale.pack(side='left', fill='x', expand=True)

    def on_scroll(event):
        current_val = var.get()
        if event.num == 4 or (hasattr(event, 'delta') and event.delta > 0):
            new_val = min(to, current_val + step)
        elif event.num == 5 or (hasattr(event, 'delta') and event.delta < 0):
            new_val = max(from_, current_val - step)
        else:
            return
        var.set(new_val)
        update_label(new_val)

    scale.bind("<MouseWheel>", on_scroll)
    scale.bind("<Button-4>", on_scroll)
    scale.bind("<Button-5>", on_scroll)

    if presets:
        center_frame = ttk.Frame(main_frame)
        center_frame.pack(fill='x')
        btn_frame = ttk.Frame(center_frame)
        btn_frame.pack()

        def set_and_update(value_to_set):
            var.set(value_to_set)
            update_label(value_to_set)

        for val in presets:
            ttk.Button(
                btn_frame, text=str(val), style=f"{button_style}.TButton" if "Font6" in button_style else button_style, width=5,
                command=lambda v=val: set_and_update(v)
            ).pack(side='left', padx=2)

    update_label(var.get())
