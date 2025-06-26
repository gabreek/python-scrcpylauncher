# FILE: gui/winlator_frame.py
# PURPOSE: Cria e gerencia a aba de controle do Winlator.

import os
import json
import time
import shlex
import threading
import tkinter as tk
from tkinter import ttk
from .widgets import create_scrolling_frame
from utils import adb_handler, scrcpy_handler

def create_winlator_tab(notebook, app_config):
    """
    Cria a aba Winlator com a lista de jogos e botões de controle.
    """
    winlator_frame = ttk.Frame(notebook, style='Dark.TFrame')
    notebook.add(winlator_frame, text='Winlator')

    def save_main_config():
        """Salva a configuração principal do aplicativo."""
        app_config.save_config()
        show_status_message("Settings saved.", 2000)

    # --- Painel superior para opções ---
    options_panel = ttk.Frame(winlator_frame, style='Dark.TFrame')
    options_panel.pack(side='top', fill='x', padx=10, pady=5)

    # CORREÇÃO: Checkbox para o pacote alternativo
    use_ludashi_check = ttk.Checkbutton(
        options_panel,
        text="Use com.ludashi.benchmark package",
        variable=app_config.get('use_ludashi_pkg'),
        command=save_main_config # Salva a config ao clicar
    )
    use_ludashi_check.pack(side='left')

    refresh_button = ttk.Button(
        options_panel,
        text="Refresh Games",
        style="Small.TButton"
    )
    refresh_button.pack(side='right')

    # --- Painel inferior para status ---
    status_panel = ttk.Frame(winlator_frame, style='Dark.TFrame')
    status_panel.pack(side='bottom', fill='x', pady=(0, 5))
    status_label = ttk.Label(status_panel, text="Initializing...", background='#2e2e2e')
    status_label.pack(padx=10)

    # --- Área de rolagem para a lista de jogos ---
    scroll_area = ttk.Frame(winlator_frame, style='Dark.TFrame')
    scroll_area.pack(fill='both', expand=True)
    scroll_canvas, content_frame = create_scrolling_frame(scroll_area)

    indicadores_por_jogo = {}

    # --- Funções de Lógica ---
    def run_threaded(target_func, *args, on_success=None, on_error=None, **kwargs):
        def task_wrapper():
            try:
                result = target_func(*args, **kwargs)
                if on_success:
                    winlator_frame.after(0, lambda: on_success(result))
            except Exception as e:
                print(f"Error in thread: {e}")
                if on_error:
                    winlator_frame.after(0, lambda: on_error(e))
        threading.Thread(target=task_wrapper, daemon=True).start()

    def get_config_path_for_game(shortcut_filename):
        base_name = os.path.basename(shortcut_filename)
        return os.path.join(app_config.WINLATOR_CONFIGS_DIR, f"{base_name}.json")

    def show_status_message(message, duration=3000):
        status_label.config(text=message)
        if duration:
            status_label.after(duration, lambda: status_label.config(text="Ready. Select a game."))

    def save_game_config(shortcut_path):
        config_path = get_config_path_for_game(shortcut_path)
        data = app_config.get_all_values()
        with open(config_path, 'w') as f:
            json.dump(data, f, indent=2)

        if shortcut_path in indicadores_por_jogo:
            indicadores_por_jogo[shortcut_path].config(text="🟢")
        show_status_message(f"Configuration saved for {os.path.basename(shortcut_path)}")

    def delete_game_config(shortcut_path):
        config_path = get_config_path_for_game(shortcut_path)
        if os.path.exists(config_path):
            os.remove(config_path)
            if shortcut_path in indicadores_por_jogo:
                indicadores_por_jogo[shortcut_path].config(text="🔴")
            show_status_message("Configuration removed.")
        else:
            show_status_message("No configuration to delete.")

    def execute_winlator_flow(shortcut_path, game_name):
        game_specific_config = app_config.get_all_values().copy()
        game_config_path = get_config_path_for_game(shortcut_path)

        if os.path.exists(game_config_path):
            with open(game_config_path) as f:
                game_data = json.load(f)
            game_specific_config.update(game_data)

        game_specific_config['start_app'] = ''

        use_ludashi = app_config.get('use_ludashi_pkg').get()
        package_name = "com.ludashi.benchmark" if use_ludashi else "com.winlator"

        show_status_message(f"Starting scrcpy for {game_name}...", duration=0)

        def on_scrcpy_error(e):
            show_status_message("Error starting scrcpy.")
            messagebox.showerror("Scrcpy Error", f"Failed to start scrcpy for game: {e}")

        def on_scrcpy_success(scrcpy_process):
            show_status_message("Waiting for virtual display ID...", duration=0)

            def get_display_id():
                display_id = None
                try:
                    for line in scrcpy_process.stdout:
                        print(f"[scrcpy] {line.strip()}")
                        if "New display" in line and "id=" in line:
                            parts = line.strip().split("id=")
                            if len(parts) > 1:
                                display_id = parts[1].split(")")[0]
                                return display_id
                except Exception as e:
                    print(f"Error reading scrcpy stdout: {e}")
                return display_id

            def on_display_id_found(display_id):
                if not display_id:
                    show_status_message("Virtual display not found.")
                    if scrcpy_process: scrcpy_process.kill()
                    return

                show_status_message(f"Display ID {display_id} found. Starting game...", duration=0)
                time.sleep(1)

                def on_game_started(result):
                    show_status_message(f"{game_name} started. Ready.")

                def on_game_error(e):
                    show_status_message(f"Error starting {game_name}.")
                    messagebox.showerror("Winlator Error", f"Failed to start game: {e}")

                run_threaded(adb_handler.start_winlator_app, shortcut_path, display_id, package_name,
                             on_success=on_game_started, on_error=on_game_error)

            run_threaded(get_display_id, on_success=on_display_id_found)

        run_threaded(scrcpy_handler.launch_scrcpy,
                     config_values=game_specific_config,
                     on_success=on_scrcpy_success,
                     on_error=on_scrcpy_error,
                     capture_output=True,
                     window_title=game_name)

    def populate_games_list(games_with_names):
        for widget in content_frame.winfo_children():
            widget.destroy()

        def bind_mouse_wheel(widget):
            widget.bind("<MouseWheel>", lambda e: scroll_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))
            widget.bind("<Button-4>", lambda e: scroll_canvas.yview_scroll(-1, "units"))
            widget.bind("<Button-5>", lambda e: scroll_canvas.yview_scroll(1, "units"))
            for child in widget.winfo_children():
                bind_mouse_wheel(child)

        if not games_with_names:
            ttk.Label(content_frame, text="No Winlator shortcuts found on device.", style='TLabel', background='#2e2e2e').pack(pady=10)
            show_status_message("Ready. No shortcuts found.")
            return

        for name, path in sorted(games_with_names, key=lambda x: x[0].lower()):
            game_frame = ttk.Frame(content_frame, style='Dark.TFrame')
            game_frame.pack(fill='x', padx=10, pady=4)

            config_exists = os.path.exists(get_config_path_for_game(path))
            indicator_color = "🟢" if config_exists else "🔴"

            indicator_label = ttk.Label(game_frame, text=indicator_color, width=2, background='#2e2e2e')
            indicator_label.pack(side='left', padx=(0, 5))
            indicadores_por_jogo[path] = indicator_label

            btn_container = ttk.Frame(game_frame, style='Dark.TFrame')
            btn_container.pack(side='left', fill='x', expand=True)

            ttk.Button(btn_container, text=name, command=lambda p=path, n=name: execute_winlator_flow(p, n)).pack(fill='x')

            actions_frame = ttk.Frame(btn_container, style='Dark.TFrame')
            actions_frame.pack(fill='x', pady=2)

            ttk.Button(actions_frame, text="💾 Save cfg", style="Small.TButton", width=10, command=lambda p=path: save_game_config(p)).pack(side='left', padx=2)
            ttk.Button(actions_frame, text="🗑️ Del cfg", style="Small.TButton", width=10, command=lambda p=path: delete_game_config(p)).pack(side='left', padx=2)

            bind_mouse_wheel(game_frame)

        show_status_message("Ready. Select a game.")

    def on_list_error(e):
        for widget in content_frame.winfo_children():
            widget.destroy()
        ttk.Label(content_frame, text="Error listing shortcuts.", background='#2e2e2e').pack(pady=10)
        show_status_message(f"Error: {e}")

    def refresh_games_list():
        show_status_message("Refreshing games list...", duration=0)
        run_threaded(adb_handler.list_winlator_shortcuts_with_names, on_success=populate_games_list, on_error=on_list_error)

    # --- Inicialização ---
    refresh_button.config(command=refresh_games_list)
    refresh_games_list() # Chama a função ao iniciar
