# FILE: gui/main_window.py
# PURPOSE: Define a estrutura principal da interface gráfica (janela e abas).

from tkinter import ttk, messagebox
import threading
from utils import adb_handler
from .scrcpy_frame import create_scrcpy_tab
from .winlator_frame import create_winlator_tab
from .apps_frame import create_apps_tab

class MainWindow:
    """
    Constrói e gerencia a janela principal da aplicação e suas abas.
    """
    def __init__(self, root, app_config, style, restart_app_callback):
        self.root = root
        self.app_config = app_config
        self.restart_app_callback = restart_app_callback
        self.session_manager_window = None
        self.initial_device_id = app_config.get('device_id').get()

        notebook = ttk.Notebook(root)
        notebook.pack(fill='both', expand=True, padx=5, pady=5)

        self.session_manager_button = ttk.Button(root, text="▶", command=self.open_session_manager, style="Small.TButton")
        self.session_manager_button.place(relx=1.0, x=-5, y=5, anchor='ne', width=25, height=25)

        self.update_apps_tab = create_apps_tab(notebook, self.app_config)
        self.update_winlator_tab = create_winlator_tab(notebook, self.app_config)
        self.update_config_tab = create_scrcpy_tab(notebook, self.app_config, style, restart_app_callback)

        self.poll_device_connection()

    def poll_device_connection(self):
        current_device_id = adb_handler.get_connected_device_id()
        initial_id = self.app_config.get('device_id').get()

        if current_device_id != initial_id and not (current_device_id is None and initial_id == 'no_device'):
            new_id = current_device_id if current_device_id else "no_device"
            is_new_config = self.app_config.load_config_for_device(new_id)
            
            self.update_apps_tab(force_refresh=is_new_config)
            self.update_winlator_tab(force_refresh=is_new_config)
            self.update_config_tab(force_encoder_fetch=is_new_config)
            
        self.root.after(5000, self.poll_device_connection)

    def open_session_manager(self):
        from .scrcpy_session_manager_window import ScrcpySessionManagerWindow

        if self.session_manager_window and self.session_manager_window.window.winfo_exists():
            # If window exists, close it
            self.session_manager_window.window.destroy()
            self.session_manager_window = None
        else:
            # Garante que a janela principal tenha uma posição antes de abrir a secundária
            self.root.update_idletasks()
            x = self.root.winfo_x()
            y = self.root.winfo_y()
            width = self.root.winfo_width()
            self.session_manager_window = ScrcpySessionManagerWindow(self.root, x, y, width, self.clear_session_manager_reference)

    def clear_session_manager_reference(self):
        self.session_manager_window = None

