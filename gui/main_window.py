# FILE: gui/main_window.py
# PURPOSE: Define a estrutura principal da interface gráfica (janela e abas).

from tkinter import ttk
from .scrcpy_frame import create_scrcpy_tab
from .winlator_frame import create_winlator_tab
from .apps_frame import create_apps_tab # Nova aba

class MainWindow:
    """
    Constrói e gerencia a janela principal da aplicação e suas abas.
    """
    def __init__(self, root, app_config):
        self.root = root
        self.app_config = app_config


        style = ttk.Style(root)
        style.theme_use("black")

        style.configure('Dark.TFrame', background='#2e2e2e')
        style.configure('Dark.TLabelframe', background='#2e2e2e', bordercolor='#555')
        style.configure('Dark.TLabelframe.Label', background='#2e2e2e', foreground='white')
        style.configure('TNotebook.Tab', padding=[10, 5])

        style.configure('TCombobox',
                        selectbackground='#4a6984',
                        fieldbackground='#3c3c3c',
                        foreground='white')
        style.map('TCombobox',
                  foreground=[('readonly', 'white'), ('disabled', '#a3a3a3')],
                  fieldbackground=[('readonly', '#3c3c3c')])

        style.configure('TEntry',
                        selectbackground='#4a6984',
                        fieldbackground='#3c3c3c',
                        foreground='white')

        style.configure('TCheckbutton', background='#2e2e2e', foreground='white')
        style.map('TCheckbutton',
            background=[('active', '#3c3c3c')],
        )

        style.configure("Small.TButton", font=("TkDefaultFont", 8), padding=(2, 1))

        # Cria o Notebook (gerenciador de abas)
        notebook = ttk.Notebook(root)
        notebook.pack(fill='both', expand=True, padx=5, pady=5)

        # Cria e adiciona as abas, passando as dependências necessárias
        create_apps_tab(notebook, self.app_config) # Adiciona a nova aba de Apps
        create_winlator_tab(notebook, self.app_config)
        create_scrcpy_tab(notebook, self.app_config)

