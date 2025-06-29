#!/usr/bin/env python3
# FILE: main.py
# PURPOSE: Ponto de entrada principal do aplicativo.
#          Verifica as dependências, inicializa a configuração e a janela principal.

import ttkbootstrap as ttk
from tkinterdnd2 import TkinterDnD
import sys
import os
from utils.dependencies import check_dependencies
from utils import adb_handler
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
    device_id = adb_handler.get_connected_device_id()

    # Usa um ID genérico se nenhum dispositivo estiver conectado
    config_device_id = device_id if device_id else "no_device"

    app_config = AppConfig(root, config_device_id)
    style = ttk.Style(theme=app_config.get('theme').get())

    root.withdraw()
    style.configure("Small.TButton", font=('-size', 8), padding=(2, 1))
    style.configure("Small.TButton.Font6.TButton", font=('-size', 6), padding=(2, 1))

    # --- INÍCIO DA ALTERAÇÃO ---
    # Adiciona um estilo customizado para os Comboboxes com fonte e altura menores.
    style.configure("Custom.TCombobox",
                    font=('-size', 9),
                    padding=(5, 3)) # (espaçamento horizontal, vertical)
    # --- FIM DA ALTERAÇÃO ---

    root.title("yaScrcpy")
    root.geometry("410x650")
    root.resizable(False, False)

    # Passa o device_id real para a MainWindow para que ela possa monitorar
    main_window = MainWindow(root, app_config, style, restart_program)

    root.deiconify()
    root.mainloop()

if __name__ == "__main__":
    main()
