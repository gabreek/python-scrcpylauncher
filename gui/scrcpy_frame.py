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

    # Impede que a roda do mouse altere o valor dos Comboboxes em toda a aba.
    # Isso neutraliza o comportamento padrão conflitante do ttkbootstrap.
    scrcpy_frame.bind_class('TCombobox', '<MouseWheel>', lambda e: 'break')
    scrcpy_frame.bind_class('TCombobox', '<Button-4>', lambda e: 'break')
    scrcpy_frame.bind_class('TCombobox', '<Button-5>', lambda e: 'break')

    trace_ids = []

    def update_config_display(force_encoder_fetch=False):
        nonlocal trace_ids
        for var, trace_id in trace_ids:
            var.trace_remove('write', trace_id)
        trace_ids = []

        for widget in scrcpy_frame.winfo_children():
            widget.destroy()

        canvas = tk.Canvas(scrcpy_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(scrcpy_frame, orient='vertical', command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        video_encoders = {}
        audio_encoders = {}

        device_info_frame = ttk.LabelFrame(scrollable_frame, text="Device Status")
        device_info_frame.pack(fill='x', padx=10, pady=5)
        info_label = ttk.Label(device_info_frame, text="Checking device status...")
        info_label.pack(padx=5, pady=5)

        def run_threaded(target_func, *args, on_success=None, on_error=None, **kwargs):
            def task_wrapper():
                try:
                    result = target_func(*args, **kwargs)
                    if on_success and scrcpy_frame.winfo_exists():
                        scrcpy_frame.after(0, lambda: on_success(result))
                except Exception as e:
                    print(f"Error in thread: {e}")
                    if on_error and scrcpy_frame.winfo_exists():
                        scrcpy_frame.after(0, lambda err=e: on_error(err))
            threading.Thread(target=task_wrapper, daemon=True).start()

        def update_device_info_display():
            device_id = app_config.get('device_id').get()
            if device_id == "no_device":
                info_label.config(text="Please connect a device.")
                load_encoders_from_cache()
                return

            def on_success(info):
                commercial_name = info.get("commercial_name", "Unknown Device")
                battery_level = info.get("battery", "?")
                app_config.get('device_commercial_name').set(commercial_name)
                info_label.config(text=f"Connected to {commercial_name} (Battery: {battery_level}%)")

                if force_encoder_fetch or not app_config.has_encoder_cache():
                    fetch_and_update_encoders(force=True)
                else:
                    load_encoders_from_cache()

            def on_error(e):
                info_label.config(text="Device not connected or ADB error.")
                load_encoders_from_cache()

            run_threaded(adb_handler.get_device_info, on_success=on_success, on_error=on_error)

        def fetch_and_update_encoders(force=False):
            device_id = app_config.get('device_id').get()
            if device_id == "no_device":
                return
            info_label.config(text="Fetching encoders...")

            def on_success(result):
                nonlocal video_encoders, audio_encoders
                video_encoders, audio_encoders = result
                app_config.save_encoder_cache(video_encoders, audio_encoders)
                populate_encoder_widgets()
                update_device_info_display()

            def on_error(e):
                messagebox.showerror("Error", f"Could not fetch encoders: {e}")
                update_device_info_display()

            run_threaded(scrcpy_handler.list_encoders, on_success=on_success, on_error=on_error)

        def load_encoders_from_cache():
            nonlocal video_encoders, audio_encoders
            cached_data = app_config.get_encoder_cache()
            video_encoders = cached_data.get('video', {})
            audio_encoders = cached_data.get('audio', {})
            populate_encoder_widgets()

        def populate_encoder_widgets():
            v_codec_box['values'] = build_codec_options(video_encoders)
            a_codec_box['values'] = build_codec_options(audio_encoders)
            update_video_encoder_options()
            update_audio_encoder_options()

        def build_codec_options(enc_map):
            opts = ["Auto"]
            if not isinstance(enc_map, dict): return opts
            for codec, entries in sorted(enc_map.items()):
                modes = sorted(list({m for _, m in entries}))
                for mode in modes:
                    opts.append(f"{mode.upper()} - {codec}")
            return opts

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

        def update_resolution_state(*_):
            if resolution_box and resolution_box.winfo_exists():
                state = 'disabled' if app_config.get('new_display').get() != 'Disabled' else 'normal'
                resolution_box.config(state=state)

        trace_id = app_config.get('new_display').trace_add('write', update_resolution_state)
        trace_ids.append((app_config.get('new_display'), trace_id))
        update_resolution_state()

        video_settings_frame = ttk.LabelFrame(scrollable_frame, text="Video Settings")
        video_settings_frame.pack(padx=10, pady=10, fill='x')

        v_codec_box = ttk.Combobox(video_settings_frame, textvariable=app_config.get('video_codec'), state='readonly', style='Custom.TCombobox', justify='center')
        v_codec_box.pack(fill='x', padx=30, pady=2)

        v_enc_box = ttk.Combobox(video_settings_frame, textvariable=app_config.get('video_encoder'), state='readonly', style='Custom.TCombobox', justify='center')
        v_enc_box.pack(fill='x', padx=30, pady=2)

        create_slider(video_settings_frame, "Video Buffer", app_config.get('video_buffer'), 0, 500, 1, "ms")
        create_slider_with_buttons(video_settings_frame, "Video Bitrate", app_config.get('video_bitrate_slider'), 10, 8000, 10, "K", [1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000], button_style="Small.TButton.Font6")

        audio_settings_frame = ttk.LabelFrame(scrollable_frame, text="Audio Settings")
        audio_settings_frame.pack(padx=10, pady=10, fill='x')

        a_codec_box = ttk.Combobox(audio_settings_frame, textvariable=app_config.get('audio_codec'), state='readonly', style='Custom.TCombobox', justify='center')
        a_codec_box.pack(fill='x', padx=30, pady=2)

        a_enc_box = ttk.Combobox(audio_settings_frame, textvariable=app_config.get('audio_encoder'), state='readonly', style='Custom.TCombobox', justify='center')
        a_enc_box.pack(fill='x', padx=30, pady=2)

        create_slider(audio_settings_frame, "Audio Buffer", app_config.get('audio_buffer'), 5, 500, 1, "ms")

        def update_video_encoder_options(*_):
            sel = app_config.get('video_codec').get()
            if sel == "Auto" or not video_encoders:
                v_enc_box['values'] = ["Auto"]
                if app_config.get('video_encoder').get() != "Auto":
                    app_config.get('video_encoder').set("Auto")
                return
            m, c = sel.split(" - ")
            encs = [e for e in video_encoders.get(c, []) if e[1] == m.lower()]
            unique_encs = dict.fromkeys(map(tuple, encs))
            vals = sorted([f"{e} ({mode})" for e, mode in unique_encs]) or ["Nenhum"]
            v_enc_box['values'] = vals
            if app_config.get('video_encoder').get() not in vals:
                app_config.get('video_encoder').set(vals[0])

        def update_audio_encoder_options(*_):
            sel = app_config.get('audio_codec').get()
            if sel == "Auto" or not audio_encoders:
                a_enc_box['values'] = ["Auto"]
                if app_config.get('audio_encoder').get() != "Auto":
                    app_config.get('audio_encoder').set("Auto")
                return
            m, c = sel.split(" - ")
            encs = [e for e in audio_encoders.get(c, []) if e[1] == m.lower()]
            unique_encs = dict.fromkeys(map(tuple, encs))
            vals = sorted([f"{e} ({mode})" for e, mode in unique_encs]) or ["Nenhum"]
            a_enc_box['values'] = vals
            if app_config.get('audio_encoder').get() not in vals:
                app_config.get('audio_encoder').set(vals[0])

        trace_id_video = app_config.get('video_codec').trace_add('write', update_video_encoder_options)
        trace_ids.append((app_config.get('video_codec'), trace_id_video))

        trace_id_audio = app_config.get('audio_codec').trace_add('write', update_audio_encoder_options)
        trace_ids.append((app_config.get('audio_codec'), trace_id_audio))

        options_frame = ttk.LabelFrame(scrollable_frame, text="Options")
        options_frame.pack(padx=10, pady=10, fill='x')
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

        theme_section_frame = ttk.LabelFrame(scrollable_frame, text="Theme Settings")
        theme_section_frame.pack(fill='x', padx=10, pady=5)
        theme_frame = ttk.Frame(theme_section_frame)
        theme_frame.pack(fill='x', padx=5, pady=5)
        ttk.Label(theme_frame, text="Theme").pack(side='left', padx=(0, 10))
        theme_combo = ttk.Combobox(theme_frame, textvariable=app_config.get('theme'), values=sorted(style.theme_names()), state="readonly")
        theme_combo.pack(fill='x', expand=True)

        # --- INÍCIO DA ALTERAÇÃO ---
        def on_theme_change(event):
            # Salva a configuração do novo tema imediatamente.
            app_config.save_config()

            # Pergunta ao usuário se deseja reiniciar para aplicar o tema.
            # Isso evita a troca de tema em tempo real, que causa o TclError.
            if messagebox.askyesno(
                "Restart Required",
                "The theme will be applied after restarting the application. Do you want to restart now?"
            ):
                restart_app_callback()
        # --- FIM DA ALTERAÇÃO ---
        theme_combo.bind("<<ComboboxSelected>>", on_theme_change)







        def bind_mouse_wheel_to_children(widget):
            # Vincula a roda do mouse para rolar o canvas em todos os widgets.
            widget.bind("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))
            widget.bind("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
            widget.bind("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))
            
            # Aplica recursivamente as vinculações a todos os widgets filhos.
            for child in widget.winfo_children():
                bind_mouse_wheel_to_children(child)
        
        bind_mouse_wheel_to_children(scrollable_frame)


        update_device_info_display()
    update_config_display()
    return update_config_display