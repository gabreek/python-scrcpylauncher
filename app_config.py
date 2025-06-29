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
    def __init__(self, root, device_id):
        if platform.system() == "Windows":
            self.CONFIG_DIR = os.path.join(os.getenv('APPDATA'), 'ScrcpyLauncher')
        else:
            self.CONFIG_DIR = os.path.expanduser("~/.config/scrcpy_launcher")

        self.ICON_CACHE_DIR = os.path.join(self.CONFIG_DIR, 'icon_cache')
        os.makedirs(self.ICON_CACHE_DIR, exist_ok=True)

        # --- INÍCIO DA ALTERAÇÃO: Lógica de Arquivo Global ---
        self.GLOBAL_CONFIG_FILE = os.path.join(self.CONFIG_DIR, 'global_config.json')
        self.CONFIG_FILE = os.path.join(self.CONFIG_DIR, f'config_{device_id}.json')

        self.global_config_data = self._load_json(self.GLOBAL_CONFIG_FILE)
        self.config_data = self._load_json(self.CONFIG_FILE)

        # Define quais chaves pertencem à configuração global
        self.GLOBAL_KEYS = {'theme'}
        # --- FIM DA ALTERAÇÃO ---

        self.config_data.setdefault('general_config', {})
        self.config_data.setdefault('app_metadata', {})
        self.config_data.setdefault('app_list_cache', {})
        self.config_data.setdefault('winlator_game_configs', {})
        self.config_data.setdefault('encoder_cache', {})

        general_config = self.config_data['general_config']
        self.vars = {
            'device_id': tk.StringVar(master=root, value=device_id),
            # --- INÍCIO DA ALTERAÇÃO: Carrega o tema da config global ---
            'theme': tk.StringVar(master=root, value=self.global_config_data.get('theme', 'superhero')),
            # --- FIM DA ALTERAÇÃO ---
            'device_commercial_name': tk.StringVar(master=root, value=general_config.get('device_commercial_name', 'Unknown Device')),
            'start_app': tk.StringVar(master=root, value=general_config.get('start_app', '')),
            'start_app_name': tk.StringVar(master=root, value=general_config.get('start_app_name', 'None')),
            'mouse_mode': tk.StringVar(master=root, value=general_config.get('mouse_mode', 'sdk')),
            'gamepad_mode': tk.StringVar(master=root, value=general_config.get('gamepad_mode', 'disabled')),
            'keyboard_mode': tk.StringVar(master=root, value=general_config.get('keyboard_mode', 'sdk')),
            'mouse_bind': tk.StringVar(master=root, value=general_config.get('mouse_bind', '++++:bhsn')),
            'render_driver': tk.StringVar(master=root, value=general_config.get('render_driver', 'opengl')),
            'max_fps': tk.StringVar(master=root, value=general_config.get('max_fps', '60')),
            'max_size': tk.StringVar(master=root, value=general_config.get('max_size', '0')),
            'display': tk.StringVar(master=root, value=general_config.get('display', 'Auto')),
            'new_display': tk.StringVar(master=root, value=general_config.get('new_display', 'Disabled')),
            'video_codec': tk.StringVar(master=root, value=general_config.get('video_codec', 'Auto')),
            'video_encoder': tk.StringVar(master=root, value=general_config.get('video_encoder', 'Auto')),
            'audio_codec': tk.StringVar(master=root, value=general_config.get('audio_codec', 'Auto')),
            'audio_encoder': tk.StringVar(master=root, value=general_config.get('audio_encoder', 'Auto')),
            'extraargs': tk.StringVar(master=root, value=general_config.get('extraargs', '')),
            'stay_awake': tk.BooleanVar(master=root, value=general_config.get('stay_awake', False)),

            'mipmaps': tk.BooleanVar(master=root, value=general_config.get('mipmaps', False)),
            'turn_screen_off': tk.BooleanVar(master=root, value=general_config.get('turn_screen_off', False)),
            'fullscreen': tk.BooleanVar(master=root, value=general_config.get('fullscreen', False)),
            'use_ludashi_pkg': tk.BooleanVar(master=root, value=general_config.get('use_ludashi_pkg', False)),
            'no_audio': tk.BooleanVar(master=root, value=general_config.get('no_audio', False)),
            'no_video': tk.BooleanVar(master=root, value=general_config.get('no_video', False)),

            'video_bitrate_slider': tk.IntVar(master=root, value=general_config.get('video_bitrate_slider', 3000)),
            'audio_buffer': tk.IntVar(master=root, value=general_config.get('audio_buffer', 5)),
            'video_buffer': tk.IntVar(master=root, value=general_config.get('video_buffer', 0)),
        }

        for var in self.vars.values():
            if isinstance(var, (tk.StringVar, tk.BooleanVar, tk.IntVar)):
                var.trace_add('write', lambda *args: self.save_config())

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

    # --- INÍCIO DA ALTERAÇÃO: Lógica de Salvamento Global/Dispositivo ---
    def save_config(self):
        """
        Salva o estado atual das variáveis, separando as configurações
        globais das configurações por dispositivo em seus respectivos arquivos.
        """
        all_values = self.get_all_values()

        # Separa as configurações globais das de dispositivo
        global_settings = {key: all_values[key] for key in self.GLOBAL_KEYS if key in all_values}
        device_settings = {key: val for key, val in all_values.items() if key not in self.GLOBAL_KEYS}

        # Salva o arquivo de configuração global
        self.global_config_data = global_settings
        self._save_json(self.global_config_data, self.GLOBAL_CONFIG_FILE)

        # Salva o arquivo de configuração do dispositivo
        self.config_data['general_config'] = device_settings
        self._save_json(self.config_data, self.CONFIG_FILE)
    # --- FIM DA ALTERAÇÃO ---

    def get_app_metadata(self, key):
        """Retorna os metadados para uma chave específica (pkg_name, path, etc.)."""
        return self.config_data['app_metadata'].get(key, {})

    def save_app_metadata(self, key, data):
        """Salva ou atualiza os metadados para uma chave específica."""
        if key not in self.config_data['app_metadata']:
            self.config_data['app_metadata'][key] = {}
        self.config_data['app_metadata'][key].update(data)
        self._save_json(self.config_data, self.CONFIG_FILE)

    def save_app_scrcpy_config(self, pkg_name, config_data):
        """Salva apenas a configuração scrcpy para um app, mantendo outros metadados."""
        if pkg_name not in self.config_data['app_metadata']:
            self.config_data['app_metadata'][pkg_name] = {}
        self.config_data['app_metadata'][pkg_name]['config'] = config_data
        self._save_json(self.config_data, self.CONFIG_FILE)

    def delete_app_scrcpy_config(self, pkg_name):
        """Deleta apenas a configuração scrcpy de um app, mantendo outros metadados."""
        if pkg_name in self.config_data['app_metadata'] and 'config' in self.config_data['app_metadata'][pkg_name]:
            del self.config_data['app_metadata'][pkg_name]['config']
            self._save_json(self.config_data, self.CONFIG_FILE)
            return True
        return False

    def get_app_list_cache(self):
        """Retorna o cache da lista de apps instalados."""
        return self.config_data['app_list_cache']

    def save_app_list_cache(self, apps):
        """Salva o cache da lista de apps instalados."""
        self.config_data['app_list_cache'] = apps
        self._save_json(self.config_data, self.CONFIG_FILE)

    def get_winlator_game_config(self, game_path):
        """Retorna a configuração específica para um jogo Winlator."""
        return self.config_data['winlator_game_configs'].get(game_path, {})

    def save_winlator_game_config(self, game_path, config):
        """Salva ou atualiza a configuração específica para um jogo Winlator."""
        self.config_data['winlator_game_configs'][game_path] = config
        self._save_json(self.config_data, self.CONFIG_FILE)

    def delete_winlator_game_config(self, game_path):
        """Deleta a configuração específica para um jogo Winlator."""
        if game_path in self.config_data['winlator_game_configs']:
            del self.config_data['winlator_game_configs'][game_path]
            self._save_json(self.config_data, self.CONFIG_FILE)

    def get_icon_cache_dir(self):
        """Retorna o diretório de cache de ícones."""
        return self.ICON_CACHE_DIR

    def get_encoder_cache(self):
        """Retorna o cache dos encoders."""
        return self.config_data.get('encoder_cache', {})

    def save_encoder_cache(self, video_encoders, audio_encoders):
        """Salva os encoders no cache."""
        self.config_data['encoder_cache'] = {
            'video': video_encoders,
            'audio': audio_encoders
        }
        self._save_json(self.config_data, self.CONFIG_FILE)

    def has_encoder_cache(self):
        """Verifica se o cache de encoders existe e não está vazio."""
        cache = self.get_encoder_cache()
        return bool(cache.get('video') or cache.get('audio'))

    # --- INÍCIO DA ALTERAÇÃO: Lógica de Carregamento de Dispositivo ---
    def load_config_for_device(self, device_id):
        """Carrega a configuração para um novo device_id e atualiza as vars, ignorando as globais."""
        self.save_config()

        self.CONFIG_FILE = os.path.join(self.CONFIG_DIR, f'config_{device_id}.json')
        self.config_data = self._load_json(self.CONFIG_FILE)
        self.config_data.setdefault('general_config', {})
        self.config_data.setdefault('app_metadata', {})
        self.config_data.setdefault('app_list_cache', {})
        self.config_data.setdefault('winlator_game_configs', {})
        self.config_data.setdefault('encoder_cache', {})

        general_config = self.config_data['general_config']

        for key, var in self.vars.items():
            # Pula a atualização de variáveis globais, pois elas não mudam com o dispositivo
            if key in self.GLOBAL_KEYS:
                continue

            default_value = 'Unknown Device' if key == 'device_commercial_name' else \
                            'no_device' if key == 'device_id' else \
                            'sdk' if key == 'mouse_mode' else \
                            'disabled' if key == 'gamepad_mode' else \
                            'sdk' if key == 'keyboard_mode' else \
                            '++++:bhsn' if key == 'mouse_bind' else \
                            'opengl' if key == 'render_driver' else \
                            '30' if key == 'max_fps' else \
                            '0' if key == 'max_size' else \
                            'Auto' if key in ['display', 'video_codec', 'video_encoder', 'audio_codec', 'audio_encoder'] else \
                            'Disabled' if key == 'new_display' else \
                            '' if key in ['start_app', 'start_app_name', 'extraargs'] else \
                            False if isinstance(var, tk.BooleanVar) else \
                            3000 if key == 'video_bitrate_slider' else \
                            120 if key == 'audio_buffer' else \
                            0 if key == 'video_buffer' else None

            if key == 'device_id':
                var.set(device_id)
            else:
                var.set(general_config.get(key, default_value))

        # Verifica se um novo arquivo de configuração foi criado
        is_new_config = not os.path.exists(self.CONFIG_FILE) or 'general_config' not in self._load_json(self.CONFIG_FILE)
        return is_new_config
    # --- FIM DA ALTERAÇÃO ---
