# FILE: gui/apps_frame.py
# PURPOSE: Cria e gerencia a nova aba de Apps.

import os
import re
import tkinter as tk
from tkinter import ttk, messagebox
import threading
from PIL import Image, ImageTk
from tkinterdnd2 import DND_FILES
from .widgets import create_scrolling_frame
from utils import adb_handler, scrcpy_handler, icon_scraper

class AppItem:
    """Representa um item de app na grade da UI."""
    def __init__(self, parent, app_info, app_config, on_launch, on_pin_toggle, placeholder_icon):
        self.parent = parent
        self.app_info = app_info
        self.app_config = app_config
        self.on_launch = on_launch
        self.on_pin_toggle = on_pin_toggle
        self.pkg_name = app_info['pkg_name']
        self.app_name = app_info['app_name']
        self.metadata = self.app_config.get_app_metadata(self.pkg_name)
        self.is_pinned = self.metadata.get('pinned', False)

        self.frame = ttk.Frame(parent, width=90, height=110)
        self.frame.pack_propagate(False)
        self.frame.grid_rowconfigure(0, weight=0); self.frame.grid_rowconfigure(1, weight=1); self.frame.grid_rowconfigure(2, weight=0); self.frame.grid_columnconfigure(0, weight=1)

        self.icon_label = ttk.Label(self.frame, image=placeholder_icon, cursor="hand2")
        self.icon_label.image = placeholder_icon
        self.icon_label.bind("<Button-1>", lambda e: self.on_launch(self.pkg_name))
        self.icon_label.drop_target_register(DND_FILES); self.icon_label.dnd_bind('<<Drop>>', self.on_icon_drop)

        self.name_label = ttk.Label(self.frame, text=self.app_name, wraplength=70, justify='center', font=("Helvetica", 8, "bold"))
        self.name_label.bind("<Button-1>", lambda e: self.on_launch(self.pkg_name))

        action_frame = ttk.Frame(self.frame)
        save_btn = ttk.Button(action_frame, text="⚙️", style="Small.TButton", command=self.save_app_config)
        save_btn.pack(side='left', padx=2, pady=2)
        self.pin_char = "⭐" if self.is_pinned else "☆"
        self.pin_button = ttk.Button(action_frame, text=self.pin_char, command=self.toggle_pin, style="Small.TButton")
        self.pin_button.pack(side='left', padx=2, pady=2)

        self.icon_label.grid(row=0, column=0, pady=(5, 2)); self.name_label.grid(row=1, column=0, sticky="nsew", padx=4); action_frame.grid(row=2, column=0, pady=(2, 5))

    def on_icon_drop(self, event):
        try:
            filepath = self.parent.tk.splitlist(event.data)[0]
        except (tk.TclError, IndexError): return
        if not filepath.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.ico')):
            messagebox.showerror("Invalid File", "Please drop a valid image file."); return
        try:
            dest_path = os.path.join(self.app_config.ICON_CACHE_DIR, f"{self.pkg_name}.png")
            img = Image.open(filepath).resize((48, 48), Image.LANCZOS); img.save(dest_path, 'PNG')
            self.app_config.save_app_metadata(self.pkg_name, {'custom_icon': True, 'icon_fetch_failed': True})
            photo = ImageTk.PhotoImage(img); self.set_icon(photo)
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred while processing the icon: {e}")

    def set_icon(self, img):
        if self.frame.winfo_exists():
            self.icon_label.config(image=img); self.icon_label.image = img

    def toggle_pin(self):
        self.is_pinned = not self.is_pinned
        self.app_config.save_app_metadata(self.pkg_name, {'pinned': self.is_pinned})
        self.on_pin_toggle()

    def save_app_config(self):
        current_scrcpy_config = self.app_config.get_all_values()
        self.app_config.save_app_metadata(self.pkg_name, {'config': current_scrcpy_config})
        messagebox.showinfo("Saved Configuration", f"Saved configuration for {self.app_name}.")


def create_apps_tab(notebook, app_config):
    apps_frame = ttk.Frame(notebook); notebook.add(apps_frame, text='Apps')
    all_apps, app_items = {}, {}

    try:
        placeholder_img = Image.open("gui/placeholder.png").resize((48, 48), Image.LANCZOS)
        placeholder_icon = ImageTk.PhotoImage(placeholder_img)
    except (FileNotFoundError, NameError):
        placeholder_img = Image.new('RGBA', (48, 48), (60, 60, 60, 255)); placeholder_icon = ImageTk.PhotoImage(placeholder_img)

    top_panel = ttk.Frame(apps_frame); top_panel.pack(fill='x', padx=10, pady=5)
    search_var = tk.StringVar(); search_entry = ttk.Entry(top_panel, textvariable=search_var); search_entry.pack(fill='x', expand=True, side='left', padx=(0, 5))
    refresh_button = ttk.Button(top_panel, text="Refresh Apps", style="Small.TButton"); refresh_button.pack(side='right')

    scroll_canvas, content_frame = create_scrolling_frame(apps_frame)

    def bind_mouse_wheel_to_children(widget):
        widget.bind("<MouseWheel>", lambda e: scroll_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))
        widget.bind("<Button-4>", lambda e: scroll_canvas.yview_scroll(-1, "units")); widget.bind("<Button-5>", lambda e: scroll_canvas.yview_scroll(1, "units"))
        for child in widget.winfo_children(): bind_mouse_wheel_to_children(child)

    def run_threaded(target_func, *args, on_success=None, on_error=None, **kwargs):
        def task_wrapper():
            try:
                result = target_func(*args, **kwargs)
                if on_success and apps_frame.winfo_exists():
                    apps_frame.after(0, lambda: on_success(result))
            except Exception as e:
                print(f"Error in thread: {e}")
                if on_error and apps_frame.winfo_exists():
                    apps_frame.after(0, lambda err=e: on_error(err))
        threading.Thread(target=task_wrapper, daemon=True).start()

    def launch_app(pkg_name):
        app_data = all_apps.get(pkg_name)
        if not app_data: return
        config_to_use = app_config.get_all_values().copy()
        app_metadata = app_config.get_app_metadata(pkg_name)
        if 'config' in app_metadata: config_to_use.update(app_metadata['config'])
        config_to_use['start_app'] = pkg_name

        # --- NOVO: Procura o ícone do app e passa para o scrcpy ---
        icon_path = os.path.join(app_config.ICON_CACHE_DIR, f"{pkg_name}.png")
        if not os.path.exists(icon_path):
            icon_path = None

        run_threaded(
            scrcpy_handler.launch_scrcpy,
            config_values=config_to_use,
            window_title=app_data['app_name'],
            on_error=lambda e: messagebox.showerror("Scrcpy Error", f"Failed to launch {app_data['app_name']}:\n{e}"),
            icon_path=icon_path # Passa o novo argumento
        )

    def populate_apps_grid(filter_text="", force_icon_download=False):
        for widget in content_frame.winfo_children(): widget.destroy()
        app_items.clear()
        pinned_apps, other_apps = [], []
        safe_filter = re.escape(filter_text)
        sorted_app_list = sorted(all_apps.items(), key=lambda item: item[1]['app_name'].lower())
        for pkg, app_info in sorted_app_list:
            if app_info['app_name']:
                if filter_text and not re.search(safe_filter, app_info['app_name'], re.IGNORECASE): continue
                if app_config.get_app_metadata(pkg).get('pinned', False):
                    pinned_apps.append(app_info)
                else: other_apps.append(app_info)
        def create_grid_section(parent, apps_list, title):
            if not apps_list: return
            ttk.Label(parent, text=title, font=("Arial", 10, "bold")).pack(fill='x', pady=(10, 5), padx=2)
            grid_container = ttk.Frame(parent); grid_container.pack()
            grid_frame = ttk.Frame(grid_container); grid_frame.pack()
            configured_rows = set()
            for i, app_info in enumerate(apps_list):
                row, col = divmod(i, 4)
                if row not in configured_rows:
                    grid_frame.grid_rowconfigure(row, weight=1)
                    configured_rows.add(row)
                item = AppItem(grid_frame, app_info, app_config, launch_app, lambda: populate_apps_grid(search_var.get()), placeholder_icon)
                item.frame.grid(row=row, column=col, padx=2, pady=5, sticky="nsew"); app_items[app_info['pkg_name']] = item
        create_grid_section(content_frame, pinned_apps, "Pinned"); create_grid_section(content_frame, other_apps, "All Apps")
        apps_frame.after(10, lambda: bind_mouse_wheel_to_children(content_frame)); apps_frame.after(50, update_scroll_region)
        run_threaded(load_icons_in_background, force_download=force_icon_download)

    def update_scroll_region():
        content_frame.update_idletasks(); scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"))

    def load_icons_in_background(force_download=False):
        for pkg_name, item in list(app_items.items()):
            icon_path = icon_scraper.get_icon(pkg_name, app_config, download_if_missing=force_download)
            if item.frame.winfo_exists() and icon_path:
                try:
                    img = Image.open(icon_path).resize((48, 48), Image.LANCZOS); photo = ImageTk.PhotoImage(img)
                    apps_frame.after(0, item.set_icon, photo)
                except Exception as e: print(f"Error loading icon for {pkg_name}: {e}")

    def on_search_change(*_):
        apps_frame.after(300, lambda: populate_apps_grid(search_var.get()))

    def refresh_all_apps():
        search_var.set(""); refresh_button.config(state='disabled')
        for widget in content_frame.winfo_children(): widget.destroy()
        loading_label = ttk.Label(content_frame, text="Loading apps..."); loading_label.pack(pady=20)
        def on_list_success(apps):
            loading_label.destroy(); nonlocal all_apps
            all_apps = {pkg: {'pkg_name': pkg, 'app_name': name} for name, pkg in apps.items() if name}
            scrcpy_handler.save_app_list_to_cache(apps, app_config.APP_LIST_CACHE)
            populate_apps_grid(force_icon_download=True); refresh_button.config(state='normal')
        def on_list_error(e):
            loading_label.destroy(); messagebox.showerror("Error", f"Could not list apps: {e}"); refresh_button.config(state='normal')
        run_threaded(scrcpy_handler.list_installed_apps, on_success=on_list_success, on_error=on_list_error)

    def load_from_cache():
        cached_apps = scrcpy_handler.load_cached_apps(app_config.APP_LIST_CACHE)
        nonlocal all_apps
        all_apps = {pkg: {'pkg_name': pkg, 'app_name': name} for name, pkg in cached_apps.items() if name}
        apps_frame.after(100, populate_apps_grid)

    search_entry.bind("<KeyRelease>", on_search_change); refresh_button.config(command=refresh_all_apps); load_from_cache()
