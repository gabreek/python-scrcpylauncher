# FILE: utils/scrcpy_handler.py
# PURPOSE: Centraliza todos os comandos que interagem com o scrcpy.

import subprocess
import shlex
import psutil
import os
import json
import re

def _build_command(config_values, window_title=None, device_id=None):
    """Constrói a lista de argumentos para o comando scrcpy."""
    cmd = ['scrcpy']
    if device_id:
        cmd.append(f"-s={device_id}")

    title = window_title or config_values.get('start_app_name') or 'Android Device'
    if title and title != 'None':
        cmd.append(f"--window-title={title}")

    # --- LÓGICA DO ÍCONE REMOVIDA DAQUI ---
    # O ícone agora é tratado por uma variável de ambiente

    if config_values.get('turn_screen_off'): cmd.append('--turn-screen-off')
    if config_values.get('fullscreen'): cmd.append('--fullscreen')
    if config_values.get('mipmaps'): cmd.append('--no-mipmaps')
    cmd.append('--stay-awake')

    map_args = {
        'start_app': '--start-app',
        'mouse_mode': '--mouse',
        'render_driver': '--render-driver',
        'max_fps': '--max-fps',
        'video_bitrate_slider': '--video-bit-rate',
        'audio_buffer': '--audio-buffer',
        'video_buffer': '--video-buffer',
    }
    for key, arg_name in map_args.items():
        val = config_values.get(key)
        if val and str(val) not in ('Auto', 'None', '0', ''):
            suffix = 'K' if key == 'video_bitrate_slider' else ''
            cmd.append(f"{arg_name}={val}{suffix}")

    if config_values.get('video_codec') != 'Auto':
        codec_val = config_values.get('video_codec')
        encoder_val = config_values.get('video_encoder')
        if codec_val and encoder_val and encoder_val != 'Auto':
            codec = codec_val.split(' - ')[-1]
            encoder = encoder_val.split()[0]
            cmd.append(f"--video-codec={codec}")
            cmd.append(f"--video-encoder={encoder}")

    if config_values.get('audio_codec') != 'Auto':
        codec_val = config_values.get('audio_codec')
        encoder_val = config_values.get('audio_encoder')
        if codec_val and encoder_val and encoder_val != 'Auto':
            codec = codec_val.split(' - ')[-1]
            encoder = encoder_val.split()[0]
            cmd.append(f"--audio-codec={codec}")
            cmd.append(f"--audio-encoder={encoder}")

    new_display_val = config_values.get('new_display')
    if new_display_val and new_display_val != 'Disabled':
        cmd.append(f"--new-display={new_display_val}")
    else:
        resolution_val = config_values.get('resolution')
        if resolution_val and resolution_val != 'Auto':
            resolution_width = resolution_val.split('x')[0]
            cmd.append(f"--max-size={resolution_width}")

    extra = config_values.get('extraargs', '').strip()
    if extra:
        cmd.extend(shlex.split(extra))

    return cmd

def launch_scrcpy(config_values, capture_output=False, window_title=None, device_id=None, icon_path=None):
    """
    Inicia o scrcpy com base na configuração fornecida, definindo o ícone
    através de uma variável de ambiente.
    """
    cmd = _build_command(config_values, window_title, device_id)
    print('Executing Scrcpy Command:', ' '.join(cmd))

    # --- LÓGICA CORRIGIDA PARA O ÍCONE ---
    # Cria uma cópia do ambiente atual para o processo filho
    env = os.environ.copy()
    if icon_path and os.path.exists(icon_path):
        # Define a variável de ambiente SCRCPY_ICON_PATH
        env['SCRCPY_ICON_PATH'] = icon_path
        print(f"Setting SCRCPY_ICON_PATH to: {icon_path}")
    else:
        # Garante que a variável não esteja definida se nenhum ícone for fornecido
        if 'SCRCPY_ICON_PATH' in env:
            del env['SCRCPY_ICON_PATH']

    startupinfo = None
    if os.name == 'nt':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    if capture_output:
        # Passa o ambiente modificado para o subprocesso
        return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, startupinfo=startupinfo, env=env)
    else:
        # Passa o ambiente modificado para o subprocesso
        subprocess.Popen(cmd, startupinfo=startupinfo, env=env)

def kill_scrcpy_processes():
    count = 0
    for proc in psutil.process_iter(['pid', 'name']):
        if 'scrcpy' in proc.info['name'].lower():
            try:
                proc.kill()
                count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    print(f"Killed {count} scrcpy processes.")

def list_installed_apps():
    try:
        output = subprocess.check_output(["scrcpy", "--list-apps"], text=True, stderr=subprocess.DEVNULL)
        apps = {}
        for line in output.splitlines():
            line = line.strip()
            if line.startswith(("-", "*")):
                line = line[1:].strip()
                match = re.match(r"(.+?)\s{2,}([a-zA-Z0-9_.]+)$", line)
                if match:
                    name, pkg = match.groups()
                    apps[name.strip()] = pkg.strip()
        return dict(sorted(apps.items()))
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        raise RuntimeError(f"Could not list apps via scrcpy: {e}")

def save_app_list_to_cache(apps, cache_path):
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, "w", encoding='utf-8') as f:
        json.dump(apps, f, indent=2)

def load_cached_apps(cache_path):
    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding='utf-8') as f:
            try: return json.load(f)
            except json.JSONDecodeError: return {}
    return {}

def list_encoders():
    video_encoders = {}
    audio_encoders = {}
    try:
        output = subprocess.check_output(["scrcpy", "--list-encoders"], text=True, stderr=subprocess.DEVNULL)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return {}, {}
    for line in output.splitlines():
        line = line.strip()
        if "(alias for" in line: continue
        vm = re.match(r"--video-codec=(\w+)\s+--video-encoder='?([\w\.-]+)'?\s+\((hw|sw)\)", line)
        if vm:
            codec, encoder, mode = vm.groups()
            video_encoders.setdefault(codec, [])
            if (encoder, mode) not in video_encoders[codec]:
                video_encoders[codec].append((encoder, mode))
        am = re.match(r"--audio-codec=(\w+)\s+--audio-encoder='?([\w\.-]+)'?\s+\((hw|sw)\)", line)
        if am:
            codec, encoder, mode = am.groups()
            audio_encoders.setdefault(codec, [])
            if (encoder, mode) not in audio_encoders[codec]:
                audio_encoders[codec].append((encoder, mode))
    return video_encoders, audio_encoders
