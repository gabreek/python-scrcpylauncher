#!/usr/bin/env python3
# FILE: main.py
# PURPOSE: Ponto de entrada principal do aplicativo.
#          Verifica as dependências, inicializa a configuração e a janela principal.

import tkinter as tk
from tkinterdnd2 import TkinterDnD
from utils.dependencies import check_dependencies
from app_config import AppConfig
from gui.main_window import MainWindow

def main():
    """
    Função principal que inicia a aplicação.
    """
    if not check_dependencies():
        return

    root = TkinterDnD.Tk()
    root.title("Scrcpy Launcher")
    root.configure(bg="#2e2e2e")
    root.resizable(False, False)

    app_config = AppConfig()
    MainWindow(root, app_config)
    root.mainloop()

if __name__ == "__main__":
    main()
