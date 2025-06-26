# FILE: app_config.py
# PURPOSE: Centraliza o gerenciamento de configurações, caminhos e variáveis Tkinter.

import os
import json
import tkinter as tk
import platform

class AppConfig:
    """
    Gerencia todas as configurações do aplicativo, incluindo caminhos de arquivos,
    metadados de apps e variáveis Tkinter que guardam o estado da interface.
    """
    def __init__(self):
        if platform.system() == "Windows":
            self.CONFIG_DIR = os.path.join(os.getenv('APPDATA'), 'ScrcpyLauncher')
        else:
            self.CONFIG_DIR = os.path.expanduser("~/.config/scrcpy_launcher")

        self.CONFIG_FILE = os.path.join(self.CONFIG_DIR, 'config.json')
        self.WINLATOR_CONFIGS_DIR = os.path.join(self.CONFIG_DIR, "winlator_game_configs")
        self.APP_LIST_CACHE = os.path.join(self.CONFIG_DIR, 'installed_apps.json')
        self.ICON_CACHE_DIR = os.path.join(self.CONFIG_DIR, 'icon_cache')
        self.APP_METADATA_FILE = os.path.join(self.CONFIG_DIR, 'app_metadata.json')

        # Garante que os diretórios de configuração existam
        os.makedirs(self.WINLATOR_CONFIGS_DIR, exist_ok=True)
        os.makedirs(self.ICON_CACHE_DIR, exist_ok=True)

        # Carrega a configuração salva ou usa um dicionário vazio
        self.config_data = self._load_json(self.CONFIG_FILE)
        self.app_metadata = self._load_json(self.APP_METADATA_FILE)

        # Mapeamento e criação de todas as variáveis Tkinter
        self.vars = {
            'start_app': tk.StringVar(value=self.config_data.get('start_app', '')),
            'start_app_name': tk.StringVar(value=self.config_data.get('start_app_name', 'None')),
            'mouse_mode': tk.StringVar(value=self.config_data.get('mouse_mode', 'sdk')),
            'mouse_bind': tk.StringVar(value=self.config_data.get('mouse_bind', '++++:bhsn')),
            'render_driver': tk.StringVar(value=self.config_data.get('render_driver', 'opengl')),
            'max_fps': tk.StringVar(value=self.config_data.get('max_fps', '60')),
            'resolution': tk.StringVar(value=self.config_data.get('resolution', 'Auto')),
            'display': tk.StringVar(value=self.config_data.get('display', 'Auto')),
            'new_display': tk.StringVar(value=self.config_data.get('new_display', 'Disabled')),
            'video_codec': tk.StringVar(value=self.config_data.get('video_codec', 'Auto')),
            'video_encoder': tk.StringVar(value=self.config_data.get('video_encoder', 'Auto')),
            'audio_codec': tk.StringVar(value=self.config_data.get('audio_codec', 'Auto')),
            'audio_encoder': tk.StringVar(value=self.config_data.get('audio_encoder', 'Auto')),
            'extraargs': tk.StringVar(value=self.config_data.get('extraargs', '')),

            'mipmaps': tk.BooleanVar(value=self.config_data.get('mipmaps', False)),
            'turn_screen_off': tk.BooleanVar(value=self.config_data.get('turn_screen_off', False)),
            'fullscreen': tk.BooleanVar(value=self.config_data.get('fullscreen', False)),
            'use_ludashi_pkg': tk.BooleanVar(value=self.config_data.get('use_ludashi_pkg', False)),

            'video_bitrate_slider': tk.IntVar(value=self.config_data.get('video_bitrate_slider', 3000)),
            'audio_buffer': tk.IntVar(value=self.config_data.get('audio_buffer', 5)),
            'video_buffer': tk.IntVar(value=self.config_data.get('video_buffer', 0)),
        }

    def get(self, key):
        """Retorna a variável Tkinter para uma dada chave."""
        return self.vars.get(key)

    def get_all_values(self):
        """Retorna um dicionário com os valores atuais de todas as variáveis."""
        return {key: var.get() for key, var in self.vars.items()}

    def _load_json(self, file_path):
        """Carrega um arquivo JSON genérico."""
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def _save_json(self, data, file_path):
        """Salva dados em um arquivo JSON genérico."""
        with open(file_path, "w", encoding='utf-8') as f:
            json.dump(data, f, indent=4)

    def save_config(self):
        """Salva o estado atual das variáveis no arquivo de configuração principal."""
        self._save_json(self.get_all_values(), self.CONFIG_FILE)

    def get_app_metadata(self, key):
        """Retorna os metadados para uma chave específica (pkg_name, path, etc.)."""
        return self.app_metadata.get(key, {})

    def save_app_metadata(self, key, data):
        """Salva ou atualiza os metadados para uma chave específica."""
        if key not in self.app_metadata:
            self.app_metadata[key] = {}
        self.app_metadata[key].update(data)
        self._save_json(self.app_metadata, self.APP_METADATA_FILE)
