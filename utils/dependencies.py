#!/usr/bin/env python3
# FILE: utils/dependencies.py
# PURPOSE: Verifica a existência das dependências externas do aplicativo.

import shutil
from tkinter import messagebox

def check_dependencies():

    if not shutil.which("adb"):
        messagebox.showerror(
            "Dependency Missing",
            "Command 'adb' not found. Please install Android Platform Tools and add it to your system's PATH."
        )
        return False
    if not shutil.which("scrcpy"):
        messagebox.showerror(
            "Dependency Missing",
            "Command 'scrcpy' not found. Please install scrcpy and ensure it is in your system's PATH."
        )
        return False
    return True
