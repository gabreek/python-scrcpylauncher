#!/usr/bin/env python3
# FILE: main.py
# PURPOSE: Ponto de entrada principal do aplicativo.
#          Verifica as dependências, inicializa a configuração e a janela principal.

import ttkbootstrap as ttk
from tkinterdnd2 import TkinterDnD
import sys
import os
from utils.dependencies import check_dependencies
from app_config import AppConfig
from gui.main_window import MainWindow

def restart_program():
    """
    Restarts the current program.
    """
    python = sys.executable
    os.execl(python, python, *sys.argv)

def main():
    """
    Função principal que inicia a aplicação.
    """
    if not check_dependencies():
        return

    root = TkinterDnD.Tk()
    app_config = AppConfig(root)
    style = ttk.Style(theme=app_config.get('theme').get())
    
    root.withdraw() # Hide the main window until theme is applied
    style.configure("Small.TButton", font=('-size', 8), padding=(2, 1))
    style.configure("Small.TButton.Font6.TButton", font=('-size', 6), padding=(2, 1))

    root.title("yaScrcpy")
    root.geometry("410x650")
    root.resizable(False, False)

    MainWindow(root, app_config, style, restart_program)
    root.deiconify() # Show the main window after everything is set up
    root.mainloop()

if __name__ == "__main__":
    main()
