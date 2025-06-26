# FILE: gui/scrcpy_frame.py
# PURPOSE: Cria e gerencia a aba de controle do Scrcpy.

import tkinter as tk
from tkinter import ttk, messagebox
import threading
from .widgets import create_slider, create_slider_with_buttons
from utils import adb_handler, scrcpy_handler

def create_scrcpy_tab(notebook, app_config):
    """
    Cria a aba Scrcpy com todos os seus widgets e lógicas.
    """
    scrcpy_frame = ttk.Frame(notebook, style='Dark.TFrame')
    notebook.add(scrcpy_frame, text='Config')

    app_map = {}
    full_app_list = []
    video_encoders = {}
    audio_encoders = {}

    info_label = ttk.Label(scrcpy_frame, text="Checking device status...", foreground="lightgreen", font=("Arial", 8, "bold"), background='#2e2e2e')
    info_label.pack(padx=10, pady=(5,0))

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

    fields = [
        ("Mouse Mode", 'mouse_mode', ["sdk","uhid","aoa"]),
        ("Render Driver", 'render_driver', ["direct3d", "opengl", "opengles2", "opengles", "metal", "software"]),
        ("Max FPS", 'max_fps', ["20","25","30", "45", "60"]),
        ("Virtual Display", 'new_display', ["Disabled", "640x360", "854x480", "1280x720", "1920x1080", "640x360/120", "854x480/120", "1280x720/140", "1920x1080/140"]),
        ("Resolution", 'resolution', ["Auto","640x360","854x480","1280x720","1920x1080"]),
        ("Extra Args", 'extraargs', None),
    ]

    resolution_box = None
    for label, var_key, opts in fields:
        frm = ttk.Frame(scrcpy_frame, style='Dark.TFrame')
        frm.pack(fill='x', padx=10, pady=2)
        ttk.Label(frm, text=label, width=15, anchor='w', background='#2e2e2e').pack(side='left')
        if opts is None:
            box = ttk.Entry(frm, textvariable=app_config.get(var_key))
        else:
            box = ttk.Combobox(frm, textvariable=app_config.get(var_key), values=opts, state='normal')

        if var_key == 'resolution': resolution_box = box
        box.pack(side='left', fill='x', expand=True)

    def update_resolution_state(*_):
        if resolution_box:
            state = 'disabled' if app_config.get('new_display').get() != 'Disabled' else 'normal'
            resolution_box.config(state=state)
    app_config.get('new_display').trace_add('write', update_resolution_state)
    update_resolution_state()

    video_section_frame = ttk.Frame(scrcpy_frame, style='Dark.TFrame')
    video_section_frame.pack(fill='x', padx=10, pady=(10,0))
    ttk.Label(video_section_frame, text="Video Codec", anchor='center', background='#2e2e2e').pack(fill='x')
    video_codec_menu = ttk.Combobox(video_section_frame, textvariable=app_config.get('video_codec'), state='readonly')
    video_codec_menu.pack(fill='x', pady=2)
    video_encoder_menu = ttk.Combobox(video_section_frame, textvariable=app_config.get('video_encoder'), state='readonly')
    video_encoder_menu.pack(fill='x', pady=2)
    create_slider_with_buttons(video_section_frame, "Video Bitrate", app_config.get('video_bitrate_slider'), 10, 8000, 10, "K", [1000, 2000, 4000, 8000])
    create_slider(video_section_frame, "Video Buffer", app_config.get('video_buffer'), 0, 500, 1, "ms")

    audio_section_frame = ttk.Frame(scrcpy_frame, style='Dark.TFrame')
    audio_section_frame.pack(fill='x', padx=10, pady=(10,0))
    ttk.Label(audio_section_frame, text="Audio Codec", anchor='center', background='#2e2e2e').pack(fill='x')
    audio_codec_menu = ttk.Combobox(audio_section_frame, textvariable=app_config.get('audio_codec'), state='readonly')
    audio_codec_menu.pack(fill='x', pady=2)
    audio_encoder_menu = ttk.Combobox(audio_section_frame, textvariable=app_config.get('audio_encoder'), state='readonly')
    audio_encoder_menu.pack(fill='x', pady=2)
    create_slider(audio_section_frame, "Audio Buffer", app_config.get('audio_buffer'), 5, 500, 1, "ms")

    app_config.get('video_codec').trace_add('write', lambda *args: update_video_encoder_options(video_encoder_menu, *args))
    app_config.get('audio_codec').trace_add('write', lambda *args: update_audio_encoder_options(audio_encoder_menu, *args))

    options_frame = ttk.LabelFrame(scrcpy_frame, text="Options", style='Dark.TLabelframe')
    options_frame.pack(padx=10, pady=10, fill='x')
    ttk.Checkbutton(options_frame, text="Fullscreen", variable=app_config.get('fullscreen')).pack(anchor='w', padx=5)
    ttk.Checkbutton(options_frame, text="Turn screen off", variable=app_config.get('turn_screen_off')).pack(anchor='w', padx=5)
    ttk.Checkbutton(options_frame, text="Disable mipmaps", variable=app_config.get('mipmaps')).pack(anchor='w', padx=5)

    btn_frame = ttk.Frame(scrcpy_frame, style='Dark.TFrame')
    btn_frame.pack(pady=10, padx=10, fill='x')

    ttk.Button(btn_frame, text="Save Current Config as Default", command=app_config.save_config).pack(fill='x')

    update_device_info()
    update_encoder_lists(video_codec_menu, video_encoder_menu, audio_codec_menu, audio_encoder_menu)
