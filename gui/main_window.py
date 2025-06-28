# FILE: gui/main_window.py
# PURPOSE: Define a estrutura principal da interface gráfica (janela e abas).

from tkinter import ttk
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
        self.session_manager_window = None # Reference to the ScrcpySessionManagerWindow

        # Cria o Notebook (gerenciador de abas)
        notebook = ttk.Notebook(root)
        notebook.pack(fill='both', expand=True, padx=5, pady=5)

        # Botão para abrir o gerenciador de sessões
        self.session_manager_button = ttk.Button(root, text="▶", command=self.open_session_manager, style="Small.TButton")
        self.session_manager_button.place(relx=1.0, x=-5, y=5, anchor='ne', width=25, height=25)

        # Cria e adiciona as abas, passando as dependências necessárias
        create_apps_tab(notebook, self.app_config)
        create_winlator_tab(notebook, self.app_config)
        create_scrcpy_tab(notebook, self.app_config, style, restart_app_callback)

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

