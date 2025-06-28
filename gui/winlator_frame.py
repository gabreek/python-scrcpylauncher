# FILE: gui/winlator_frame.py
# PURPOSE: Cria e gerencia a aba de controle do Winlator.

import os
import re
import json
import time
import shlex
import tempfile
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
from tkinterdnd2 import DND_FILES
from .widgets import create_scrolling_frame
from utils import adb_handler, scrcpy_handler, exe_icon_extractor
import queue

class WinlatorGameItem:
    """Representa um item de jogo na grade da UI para o Winlator."""
    def __init__(self, parent, game_info, app_config, on_launch, placeholder_icon):
        self.parent = parent
        self.game_info = game_info
        self.app_config = app_config
        self.on_launch = on_launch
        self.game_name = game_info['name']
        self.game_path = game_info['path']
        self.frame = ttk.Frame(parent)
        self.frame.columnconfigure(0, weight=1)
        self.frame.grid_rowconfigure(0, weight=0); self.frame.grid_rowconfigure(1, weight=1); self.frame.grid_rowconfigure(2, weight=0); self.frame.grid_columnconfigure(0, weight=1)
        self.icon_label = ttk.Label(self.frame, image=placeholder_icon, cursor="hand2")
        self.icon_label.image = placeholder_icon
        self.icon_label.bind("<Button-1>", lambda e: self.on_launch(self.game_path, self.game_name))
        self.icon_label.drop_target_register(DND_FILES); self.icon_label.dnd_bind('<<Drop>>', self.on_icon_drop)
        self.name_label = ttk.Label(self.frame, text=self.game_name, wraplength=80, justify='center', font=("Helvetica", 8, "bold"))
        self.name_label.bind("<Button-1>", lambda e: self.on_launch(self.game_path, self.game_name))
        action_frame_container = ttk.Frame(self.frame); action_frame = ttk.Frame(action_frame_container); action_frame.pack()
        save_btn = ttk.Button(action_frame, text=" ⚙️", style="Small.TButton", command=self.save_game_config)
        save_btn.pack(side='left', padx=2, pady=2)
        del_btn = ttk.Button(action_frame, text=" 🗑️", style="Small.TButton", command=self.delete_game_config)
        del_btn.pack(side='left', padx=2, pady=2)
        self.icon_label.grid(row=0, column=0, pady=(5, 2)); self.name_label.grid(row=1, column=0, sticky="nsew", padx=4); action_frame_container.grid(row=2, column=0, pady=(2, 5))

    def on_icon_drop(self, event):
        try: filepath = self.parent.tk.splitlist(event.data)[0]
        except (tk.TclError, IndexError): return
        if not filepath.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.ico')):
            messagebox.showerror("Invalid File", "Please drop a valid image file."); return
        try:
            icon_key = os.path.basename(self.game_path)
            dest_path = os.path.join(self.app_config.ICON_CACHE_DIR, f"{icon_key}.png")
            img = Image.open(filepath).resize((48, 48), Image.LANCZOS); img.save(dest_path, 'PNG')
            self.app_config.save_app_metadata(self.game_path, {'custom_icon': True, 'exe_icon_fetch_failed': False})
            photo = ImageTk.PhotoImage(img); self.set_icon(photo)
        except Exception as e: messagebox.showerror("Erro", f"Ocorreu um erro ao processar o ícone: {e}")

    def set_icon(self, img):
        if self.frame.winfo_exists(): self.icon_label.config(image=img); self.icon_label.image = img

    def get_config_path(self): return os.path.join(self.app_config.WINLATOR_CONFIGS_DIR, f"{os.path.basename(self.game_path)}.json")
    def save_game_config(self):
        with open(self.get_config_path(), 'w') as f: json.dump(self.app_config.get_all_values(), f, indent=2)
        messagebox.showinfo("Saved Configuration", f"Saved configuration for {self.game_name}.")
    def delete_game_config(self):
        if os.path.exists(self.get_config_path()): os.remove(self.get_config_path()); messagebox.showinfo("Configuration Removed", f"Configuration removed for {self.game_name}.")
        else: messagebox.showwarning("Warning", "No settings to remove.")


def create_winlator_tab(notebook, app_config):
    winlator_frame = ttk.Frame(notebook); notebook.add(winlator_frame, text='Winlator')
    all_games, game_items = [], {}; temp_dir = tempfile.gettempdir()
    extraction_queue = queue.Queue()

    NUM_WORKERS = 5

    def icon_extractor_worker():
        while True:
            task = extraction_queue.get()
            try:
                if task is None: break
                path, item, save_path = task
                extract_and_set_icon(path, item, save_path)
            except Exception as e:
                print(f"Erro no trabalhador de extração de ícones: {e}")
            finally:
                extraction_queue.task_done()

    try:
        placeholder_img = Image.open("gui/winlator_placeholder.png").resize((48, 48), Image.LANCZOS)
        placeholder_icon = ImageTk.PhotoImage(placeholder_img)
    except (FileNotFoundError, NameError):
        placeholder_img = Image.new('RGBA', (48, 48), (60, 60, 60, 255)); placeholder_icon = ImageTk.PhotoImage(placeholder_img)

    top_panel = ttk.Frame(winlator_frame); top_panel.pack(fill='x', padx=10, pady=5)



    use_ludashi_check = ttk.Checkbutton(top_panel, text="Use Ludashi pkg", variable=app_config.get('use_ludashi_pkg')); use_ludashi_check.pack(side='left', padx=5)
    refresh_button = ttk.Button(top_panel, text="Refresh Apps", style="Small.TButton"); refresh_button.pack(side='right')
    fetch_icons_button = ttk.Button(top_panel, text="Refresh Icons", style="Small.TButton", command=lambda: prompt_for_icon_update())
    fetch_icons_button.pack(side='right', padx=5)
    scroll_canvas, content_frame = create_scrolling_frame(winlator_frame)

    def bind_mouse_wheel_to_children(widget):
        widget.bind("<MouseWheel>", lambda e: scroll_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))
        widget.bind("<Button-4>", lambda e: scroll_canvas.yview_scroll(-1, "units")); widget.bind("<Button-5>", lambda e: scroll_canvas.yview_scroll(1, "units"))
        for child in widget.winfo_children(): bind_mouse_wheel_to_children(child)

    def run_threaded(target_func, *args, on_success=None, on_error=None, **kwargs):
        def task_wrapper():
            try:
                result = target_func(*args, **kwargs)
                if on_success and winlator_frame.winfo_exists(): winlator_frame.after(0, lambda: on_success(result))
            except Exception as e:
                print(f"Error in thread: {e}")
                if on_error and winlator_frame.winfo_exists():
                    # --- CORREÇÃO: Captura o valor de 'e' na lambda ---
                    winlator_frame.after(0, lambda err=e: on_error(err))
        threading.Thread(target=task_wrapper, daemon=True).start()

    def execute_winlator_flow(shortcut_path, game_name):
        game_specific_config = app_config.get_all_values().copy()
        game_config_path = os.path.join(app_config.WINLATOR_CONFIGS_DIR, f"{os.path.basename(shortcut_path)}.json")

        if os.path.exists(game_config_path):
            with open(game_config_path) as f:
                game_data = json.load(f)
            game_specific_config.update(game_data)

        game_specific_config['start_app'] = ''
        use_ludashi = app_config.get('use_ludashi_pkg').get()
        package_name = "com.ludashi.benchmark" if use_ludashi else "com.winlator"

        icon_key = os.path.basename(shortcut_path)
        icon_path = os.path.join(app_config.ICON_CACHE_DIR, f"{icon_key}.png")
        if not os.path.exists(icon_path):
            icon_path = None

        def on_scrcpy_error(e):
            messagebox.showerror("Scrcpy Error", f"Failed to start scrcpy for game: {e}")

        def on_scrcpy_success(scrcpy_process):
            def get_display_id():
                for line in scrcpy_process.stdout:
                    print(f"[scrcpy] {line.strip()}")
                    if "New display" in line and "id=" in line:
                        return line.strip().split("id=")[1].split(")")[0]
                return None

            def on_display_id_found(display_id):
                if not display_id:
                    messagebox.showerror("Error", "Virtual display not found.")
                    if scrcpy_process: scrcpy_process.kill()
                    return
                time.sleep(1)
                run_threaded(adb_handler.start_winlator_app, shortcut_path, display_id, package_name)

            run_threaded(get_display_id, on_success=on_display_id_found)

        run_threaded(scrcpy_handler.launch_scrcpy,
                     config_values=game_specific_config,
                     on_success=on_scrcpy_success,
                     on_error=on_scrcpy_error,
                     capture_output=True,
                     window_title=game_name,
                     icon_path=icon_path)

    def populate_games_grid():
        for widget in content_frame.winfo_children(): widget.destroy()
        game_items.clear()

        for i in range(4):
            content_frame.grid_columnconfigure(i, weight=1, uniform="winlator_col")

        if not all_games:
            message_label = ttk.Label(content_frame, text="No Winlator shortcut found ."); message_label.grid(row=0, column=0, columnspan=4, pady=10, padx=10)
            return
        for i, game_info in enumerate(all_games):
            row, col = divmod(i, 4)
            item = WinlatorGameItem(content_frame, game_info, app_config, execute_winlator_flow, placeholder_icon); item.frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            game_items[game_info['path']] = item
        winlator_frame.after(10, lambda: bind_mouse_wheel_to_children(content_frame)); winlator_frame.after(50, lambda: content_frame.update_idletasks())
        load_cached_icons()

    def load_cached_icons():
        for path, item in list(game_items.items()):
            icon_key = os.path.basename(path); cached_icon_path = os.path.join(app_config.ICON_CACHE_DIR, f"{icon_key}.png")
            if os.path.exists(cached_icon_path):
                if item.frame.winfo_exists():
                    try: img = Image.open(cached_icon_path).resize((48, 48), Image.LANCZOS); photo = ImageTk.PhotoImage(img); winlator_frame.after(0, item.set_icon, photo)
                    except Exception as e: print(f"Erro ao carregar ícone do cache para {path}: {e}")

    def prompt_for_icon_update():
        missing_icons = []
        for path, item in game_items.items():
            icon_key = os.path.basename(path)
            cached_icon_path = os.path.join(app_config.ICON_CACHE_DIR, f"{icon_key}.png")
            if not os.path.exists(cached_icon_path):
                 metadata = app_config.get_app_metadata(path)
                 if not metadata.get('exe_icon_fetch_failed') and not metadata.get('custom_icon'):
                    missing_icons.append((path, item, cached_icon_path))

        if not missing_icons:
            messagebox.showinfo("Icons", "No icons to extract."); return

        answer = messagebox.askyesno(
            "Search missing icons?",
            f"{len(missing_icons)} games without icons.\n\n"
            "This process will download the .exe files to your phone temporarily and may take several minutes depending on the number and size of the file\n\n"
            "Wish to continue?"
        )
        if answer:
            start_icon_extraction_flow(missing_icons)

    def start_icon_extraction_flow(tasks):
        progress_window = tk.Toplevel(winlator_frame)
        progress_window.title("Processing...")
        progress_window.geometry("300x100")
        progress_window.resizable(False, False)
        progress_window.transient(winlator_frame); progress_window.grab_set()

        total_tasks = len(tasks)
        progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(progress_window, variable=progress_var, maximum=total_tasks)
        progress_bar.pack(pady=10, padx=10, fill='x')

        status_var = tk.StringVar(value=f"Preparing to process 0 of {total_tasks}, please wait...")
        status_label = ttk.Label(progress_window, textvariable=status_var)
        status_label.pack(pady=5)

        for task in tasks:
            extraction_queue.put(task)

        def monitor_queue():
            extraction_queue.join()
            if progress_window.winfo_exists():
                progress_window.after(0, progress_window.destroy)
                winlator_frame.after(100, lambda: messagebox.showinfo("Finished", "Icons extraction finished!."))
                winlator_frame.after(100, populate_games_grid)

        def update_progress():
            if not progress_window.winfo_exists(): return

            processed_count = total_tasks - extraction_queue.qsize()
            progress_var.set(processed_count)
            status_var.set(f"A processar {processed_count} de {total_tasks}...")

            progress_window.after(200, update_progress)

        progress_window.after(100, update_progress)
        threading.Thread(target=monitor_queue, daemon=True).start()

    def extract_and_set_icon(path, item, save_path):
        print(f"\n[Extractor Worker] Processando: {item.game_name}")
        remote_exe_path = adb_handler.get_game_executable_info(path)
        if not remote_exe_path:
            print(f"[Extractor Worker] ERRO: Não foi possível encontrar o caminho do .exe no atalho."); app_config.save_app_metadata(path, {'exe_icon_fetch_failed': True}); return

        local_exe_path = os.path.join(temp_dir, f"{os.path.basename(remote_exe_path)}_{int(time.time()*1000)}")
        try:
            adb_handler.pull_file(remote_exe_path, local_exe_path)
            if not os.path.exists(local_exe_path): raise FileNotFoundError("Falha ao baixar o .exe")

            success = exe_icon_extractor.extract_icon_from_exe(local_exe_path, save_path)
            if success:
                app_config.save_app_metadata(path, {'exe_icon_fetch_failed': False})
                if item.frame.winfo_exists():
                    img = Image.open(save_path).resize((48, 48), Image.LANCZOS); photo = ImageTk.PhotoImage(img)
                    winlator_frame.after(0, item.set_icon, photo)
            else: app_config.save_app_metadata(path, {'exe_icon_fetch_failed': True})
        except Exception as e:
            print(f"[Extractor Worker] ERRO GERAL no processo de extração: {e}"); app_config.save_app_metadata(path, {'exe_icon_fetch_failed': True})
        finally:
            if os.path.exists(local_exe_path): os.remove(local_exe_path)

    def refresh_games_list():
        refresh_button.config(state='disabled')
        for widget in content_frame.winfo_children(): widget.destroy()
        loading_label = ttk.Label(content_frame, text="Searching for games...")
        loading_label.grid(row=0, column=0, columnspan=4, pady=20, padx=10); content_frame.update_idletasks()
        def on_list_success(games_with_names):
            loading_label.destroy(); nonlocal all_games
            all_games = [{'name': name, 'path': path} for name, path in sorted(games_with_names)]
            populate_games_grid(); refresh_button.config(state='normal')
        def on_list_error(e):
            loading_label.destroy(); messagebox.showerror("Error", f"Could not list games: {e}"); refresh_button.config(state='normal')
        run_threaded(adb_handler.list_winlator_shortcuts_with_names, on_success=on_list_success, on_error=on_list_error)

    refresh_button.config(command=refresh_games_list)

    for _ in range(NUM_WORKERS):
        threading.Thread(target=icon_extractor_worker, daemon=True).start()

    refresh_games_list()
