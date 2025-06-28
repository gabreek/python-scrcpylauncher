# FILE: gui/scrcpy_frame.py
# PURPOSE: Cria e gerencia a aba de controle do Scrcpy.

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import ttkbootstrap as bstt
from .widgets import create_slider, create_slider_with_buttons
from utils import adb_handler, scrcpy_handler

def create_scrcpy_tab(notebook, app_config, style, restart_app_callback):
    """
    Cria a aba Scrcpy com todos os seus widgets e lógicas.
    """
    scrcpy_frame = ttk.Frame(notebook)
    notebook.add(scrcpy_frame, text='Config')

    canvas = tk.Canvas(scrcpy_frame, highlightthickness=0)
    scrollbar = ttk.Scrollbar(scrcpy_frame, orient='vertical', command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")
        )
    )

    canvas.create_window((0, 0), window=scrollable_frame, anchor='nw')
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side='left', fill='both', expand=True)
    scrollbar.pack(side='right', fill='y')

    app_map = {}
    full_app_list = []
    video_encoders = {}
    audio_encoders = {}

    # --- Device Info ---
    device_info_frame = ttk.LabelFrame(scrollable_frame, text="Device Status")
    device_info_frame.pack(fill='x', padx=10, pady=5)
    info_label = ttk.Label(device_info_frame, text="Checking device status...")
    info_label.pack(padx=5, pady=5)

    def run_threaded(target_func, *args, on_success=None, on_error=None, **kwargs):
        def task_wrapper():
            try:
                result = target_func(*args, **kwargs)
                if on_success:
                    scrcpy_frame.after(0, lambda: on_success(result))
            except Exception as e:
                print(f"Error in thread: {e}")
                if on_error:
                    scrcpy_frame.after(0, lambda: on_error(e))

        threading.Thread(target=task_wrapper, daemon=True).start()

    def update_device_info():
        def on_success(info):
            info_label.config(text=info)
            scrcpy_frame.after(180000, update_device_info)
        def on_error(e):
            info_label.config(text="Device not connected or ADB error")
            scrcpy_frame.after(180000, update_device_info)

        run_threaded(adb_handler.get_device_info, on_success=on_success, on_error=on_error)

    # --- Theme Selector ---
    theme_section_frame = ttk.LabelFrame(scrollable_frame, text="Theme Settings")
    theme_section_frame.pack(fill='x', padx=10, pady=5)
    theme_frame = ttk.Frame(theme_section_frame)
    theme_frame.pack(fill='x', padx=5, pady=5)
    ttk.Label(theme_frame, text="Theme").pack(side='left', padx=(0, 10))
    theme_combo = ttk.Combobox(
        theme_frame,
        textvariable=app_config.get('theme'),
        values=sorted(style.theme_names()),
        state="readonly"
    )
    theme_combo.pack(fill='x', expand=True)
    # Disable mouse wheel for theme_combo
    theme_combo.bind("<MouseWheel>", lambda e: (canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"), "break")[1])
    theme_combo.bind("<Button-4>", lambda e: (canvas.yview_scroll(-1, "units"), "break")[1])
    theme_combo.bind("<Button-5>", lambda e: (canvas.yview_scroll(1, "units"), "break")[1])
    
    

    def on_theme_change(event):
        theme_name = app_config.get('theme').get()
        style.theme_use(theme_name)
        app_config.save_config()
        if messagebox.askyesno("Restart Application", "The theme has been changed. To fully apply the new theme, the application needs to be restarted. Do you want to restart now?"):
            restart_app_callback()

    theme_combo.bind("<<ComboboxSelected>>", on_theme_change)


    def update_encoder_lists(v_codec_box, v_enc_box, a_codec_box, a_enc_box):
        def on_success(result):
            nonlocal video_encoders, audio_encoders
            video_encoders, audio_encoders = result

            v_codec_box['values'] = build_codec_options(video_encoders)
            a_codec_box['values'] = build_codec_options(audio_encoders)

            update_video_encoder_options(v_enc_box)
            update_audio_encoder_options(a_enc_box)
        run_threaded(scrcpy_handler.list_encoders, on_success=on_success)

    def build_codec_options(enc_map):
        opts = ["Auto"]
        for codec, entries in sorted(enc_map.items()):
            modes = sorted(list({m for _, m in entries}))
            for mode in modes:
                opts.append(f"{mode.upper()} - {codec}")
        return opts

    def update_video_encoder_options(v_enc_box, *_):
        sel = app_config.get('video_codec').get()
        if sel == "Auto" or not video_encoders:
            v_enc_box['values'] = ["Auto"]
            if app_config.get('video_encoder').get() != "Auto":
                app_config.get('video_encoder').set("Auto")
            return

        m, c = sel.split(" - ")
        encs = [e for e in video_encoders.get(c, []) if e[1] == m.lower()]
        vals = sorted([f"{e} ({mode})" for e, mode in dict.fromkeys(encs)]) or ["Nenhum"]
        v_enc_box['values'] = vals
        if app_config.get('video_encoder').get() not in vals:
            app_config.get('video_encoder').set(vals[0])

    def update_audio_encoder_options(a_enc_box, *_):
        sel = app_config.get('audio_codec').get()
        if sel == "Auto" or not audio_encoders:
            a_enc_box['values'] = ["Auto"]
            if app_config.get('audio_encoder').get() != "Auto":
                app_config.get('audio_encoder').set("Auto")
            return

        m, c = sel.split(" - ")
        encs = [e for e in audio_encoders.get(c, []) if e[1] == m.lower()]
        vals = sorted([f"{e} ({mode})" for e, mode in dict.fromkeys(encs)]) or ["Nenhum"]
        a_enc_box['values'] = vals
        if app_config.get('audio_encoder').get() not in vals:
            app_config.get('audio_encoder').set(vals[0])

    # --- Construção da UI ---

    # General Settings
    general_settings_frame = ttk.LabelFrame(scrollable_frame, text="General Settings")
    general_settings_frame.pack(padx=10, pady=10, fill='x')

    fields = [
        ("Mouse Mode", 'mouse_mode', ["sdk","uhid","aoa"], 'readonly'),
        ("Gamepad Mode", 'gamepad_mode', ["disabled","uhid","aoa"], 'readonly'),
        ("Keyboard Mode", 'keyboard_mode', ["disabled","sdk","uhid","aoa"], 'readonly'),
        ("Mouse Bind", 'mouse_bind', ["bhsn:++++","++++:bhsn"], 'readonly'),
        ("Render Driver", 'render_driver', ["opengles2", "opengles", "opengl", "direct3d", "metal", "software"], 'readonly'),
        ("Max FPS", 'max_fps', ["20","25","30", "45", "60"]),
        ("Virtual Display", 'new_display', ["Disabled", "640x360", "854x480", "1280x720", "1920x1080", "640x360/120", "854x480/120", "1280x720/140", "1920x1080/140"]),
        ("Max Size", 'max_size', ["0","960","1280","1366","1080"]),
        ("Extra Args", 'extraargs', None),
    ]

    resolution_box = None
    for label, var_key, opts, *state_override in fields:
        frm = ttk.Frame(general_settings_frame)
        frm.pack(fill='x', padx=5, pady=2)
        ttk.Label(frm, text=label, width=15, anchor='w').pack(side='left')
        if opts is None:
            box = ttk.Entry(frm, textvariable=app_config.get(var_key))
        else:
            box_state = state_override[0] if state_override else 'normal'
            box = ttk.Combobox(frm, textvariable=app_config.get(var_key), values=opts, state=box_state)

        if var_key == 'max_size': resolution_box = box
        box.pack(side='left', fill='x', expand=True)
        # Disable mouse wheel for Comboboxes
        if isinstance(box, ttk.Combobox):
            box.bind("<MouseWheel>", lambda e: (canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"), "break")[1])
            box.bind("<Button-4>", lambda e: (canvas.yview_scroll(-1, "units"), "break")[1])
            box.bind("<Button-5>", lambda e: (canvas.yview_scroll(1, "units"), "break")[1])
        
        
        

    def update_resolution_state(*_):
        if resolution_box:
            state = 'disabled' if app_config.get('new_display').get() != 'Disabled' else 'normal'
            resolution_box.config(state=state)
    app_config.get('new_display').trace_add('write', update_resolution_state)
    update_resolution_state()

    # Video Settings
    video_settings_frame = ttk.LabelFrame(scrollable_frame, text="Video Settings")
    video_settings_frame.pack(padx=10, pady=10, fill='x')

    video_codec_menu = ttk.Combobox(video_settings_frame, textvariable=app_config.get('video_codec'), state='readonly')
    video_codec_menu.pack(fill='x', pady=2)
    # Disable mouse wheel for video_codec_menu
    video_codec_menu.bind("<MouseWheel>", lambda e: (canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"), "break")[1])
    video_codec_menu.bind("<Button-4>", lambda e: (canvas.yview_scroll(-1, "units"), "break")[1])
    video_codec_menu.bind("<Button-5>", lambda e: (canvas.yview_scroll(1, "units"), "break")[1])
    
    

    video_encoder_menu = ttk.Combobox(video_settings_frame, textvariable=app_config.get('video_encoder'), state='readonly')
    video_encoder_menu.pack(fill='x', pady=2)
    # Disable mouse wheel for video_encoder_menu
    video_encoder_menu.bind("<MouseWheel>", lambda e: (canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"), "break")[1])
    video_encoder_menu.bind("<Button-4>", lambda e: (canvas.yview_scroll(-1, "units"), "break")[1])
    video_encoder_menu.bind("<Button-5>", lambda e: (canvas.yview_scroll(1, "units"), "break")[1])
    
    
    create_slider_with_buttons(video_settings_frame, "Video Bitrate", app_config.get('video_bitrate_slider'), 10, 8000, 10, "K", [1000, 2000, 4000, 8000], button_style="Small.TButton.Font6")
    create_slider(video_settings_frame, "Video Buffer", app_config.get('video_buffer'), 0, 500, 1, "ms")

    # Audio Settings
    audio_settings_frame = ttk.LabelFrame(scrollable_frame, text="Audio Settings")
    audio_settings_frame.pack(padx=10, pady=10, fill='x')

    audio_codec_menu = ttk.Combobox(audio_settings_frame, textvariable=app_config.get('audio_codec'), state='readonly')
    audio_codec_menu.pack(fill='x', pady=2)
    # Disable mouse wheel for audio_codec_menu
    audio_codec_menu.bind("<MouseWheel>", lambda e: (canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"), "break")[1])
    audio_codec_menu.bind("<Button-4>", lambda e: (canvas.yview_scroll(-1, "units"), "break")[1])
    audio_codec_menu.bind("<Button-5>", lambda e: (canvas.yview_scroll(1, "units"), "break")[1])
    
    

    audio_encoder_menu = ttk.Combobox(audio_settings_frame, textvariable=app_config.get('audio_encoder'), state='readonly')
    audio_encoder_menu.pack(fill='x', pady=2)
    # Disable mouse wheel for audio_encoder_menu
    audio_encoder_menu.bind("<MouseWheel>", lambda e: (canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"), "break")[1])
    audio_encoder_menu.bind("<Button-4>", lambda e: (canvas.yview_scroll(-1, "units"), "break")[1])
    audio_encoder_menu.bind("<Button-5>", lambda e: (canvas.yview_scroll(1, "units"), "break")[1])
    
    
    create_slider(audio_settings_frame, "Audio Buffer", app_config.get('audio_buffer'), 5, 500, 1, "ms")

    app_config.get('video_codec').trace_add('write', lambda *args: update_video_encoder_options(video_encoder_menu, *args))
    app_config.get('audio_codec').trace_add('write', lambda *args: update_audio_encoder_options(audio_encoder_menu, *args))

    

    def bind_mouse_wheel_to_children(widget):
        if isinstance(widget, ttk.Combobox):
            return
        widget.bind("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))
        widget.bind("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
        widget.bind("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))
        for child in widget.winfo_children(): bind_mouse_wheel_to_children(child)

    options_frame = ttk.LabelFrame(scrollable_frame, text="Options")
    options_frame.pack(padx=10, pady=10, fill='x')

    # Checkboxes em duas colunas
    checkboxes = [
        ("Fullscreen", app_config.get('fullscreen')),
        ("Turn screen off", app_config.get('turn_screen_off')),
        ("Stay Awake", app_config.get('stay_awake')),
        ("Disable mipmaps", app_config.get('mipmaps')),
        ("No Audio", app_config.get('no_audio')),
        ("No Video", app_config.get('no_video')),
    ]

    for i, (text, var) in enumerate(checkboxes):
        row = i // 2
        col = i % 2
        ttk.Checkbutton(options_frame, text=text, variable=var).grid(row=row, column=col, sticky='w', padx=5, pady=2)

    btn_frame = ttk.Frame(scrollable_frame)
    btn_frame.pack(pady=10, padx=10, fill='x')

    update_device_info()
    update_encoder_lists(video_codec_menu, video_encoder_menu, audio_codec_menu, audio_encoder_menu)
    bind_mouse_wheel_to_children(scrollable_frame)
    
