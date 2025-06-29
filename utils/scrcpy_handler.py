# FILE: utils/scrcpy_handler.py
# PURPOSE: Centraliza todos os comandos que interagem com o scrcpy.

import subprocess
import shlex
import psutil
import os
import json
import re
import threading

# Lista global para armazenar as sessões Scrcpy ativas
active_scrcpy_sessions = []

def add_scrcpy_session(pid, app_name, icon_path, command_args, session_type='app'):
    active_scrcpy_sessions.append({'pid': pid, 'app_name': app_name, 'icon_path': icon_path, 'command_args': command_args, 'session_type': session_type})
    print(f"[scrcpy_handler] Added session: PID={pid}, AppName={app_name}, Type={session_type}")

def remove_scrcpy_session(pid):
    global active_scrcpy_sessions
    initial_len = len(active_scrcpy_sessions)
    active_scrcpy_sessions = [s for s in active_scrcpy_sessions if s['pid'] != pid]
    if len(active_scrcpy_sessions) < initial_len:
        print(f"[scrcpy_handler] Removed session: PID={pid}")

def get_active_scrcpy_sessions():
    print(f"[scrcpy_handler] Checking active sessions. Current count: {len(active_scrcpy_sessions)}")
    current_pids = {p.pid for p in psutil.process_iter(['pid', 'name', 'cmdline'])} # Otimização: obter PIDs uma vez
    print(f"[scrcpy_handler] Current PIDs found: {len(current_pids)}")
    valid_sessions = []
    for session in active_scrcpy_sessions:
        print(f"[scrcpy_handler] Processing session PID: {session['pid']}")
        if session['pid'] in current_pids:
            try:
                proc = psutil.Process(session['pid'])
                proc_name = proc.name().lower()
                proc_cmdline = " ".join(proc.cmdline())
                print(f"[scrcpy_handler] PID {session['pid']} - Name: {proc_name}, Cmdline: {proc_cmdline}")
                if proc.is_running() and ('scrcpy' in proc_name or 'scrcpy' in proc_cmdline):
                    valid_sessions.append(session)
                else:
                    print(f"[scrcpy_handler] Invalid session (not scrcpy or not running): PID={session['pid']}, Name={proc_name}, Cmdline={proc_cmdline}")
            except psutil.NoSuchProcess:
                print(f"[scrcpy_handler] Invalid session (no such process): PID={session['pid']}")
        else:
            print(f"[scrcpy_handler] Invalid session (PID not in current processes): PID={session['pid']}")
    active_scrcpy_sessions[:] = valid_sessions # Atualiza a lista global
    print(f"[scrcpy_handler] Valid sessions after check: {len(active_scrcpy_sessions)}")
    return active_scrcpy_sessions

def kill_scrcpy_session(pid):
    try:
        process = psutil.Process(pid)
        process.terminate()
        process.wait(timeout=5) # Espera o processo terminar
        if process.is_running():
            process.kill() # Força o encerramento se não terminar
        remove_scrcpy_session(pid)
        return True
    except psutil.NoSuchProcess:
        remove_scrcpy_session(pid) # Remove se o processo já não existe
        return True
    except Exception as e:
        return False

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
    if config_values.get('stay_awake'): cmd.append('--stay-awake')
    if config_values.get('no_audio'): cmd.append('--no-audio')
    if config_values.get('no_video'): cmd.append('--no-video')

    map_args = {
        'start_app': '--start-app',
        'mouse_mode': '--mouse',
        'gamepad_mode': '--gamepad',
        'keyboard_mode': '--keyboard',
        'mouse_bind': '--mouse-bind',
        'render_driver': '--render-driver',
        'max_fps': '--max-fps',
        'video_bitrate_slider': '--video-bit-rate',
        'audio_buffer': '--audio-buffer',
        'video_buffer': '--video-buffer',
    }
    for key, arg_name in map_args.items():
        val = config_values.get(key)
        if val and str(val) not in ('Auto', 'None', '0', 'disabled', ''):
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
        max_size_val = config_values.get('max_size')
        if max_size_val and max_size_val != '0':
            cmd.append(f"--max-size={max_size_val}")

    extra = config_values.get('extraargs', '').strip()
    if extra:
        cmd.extend(shlex.split(extra))

    return cmd

def launch_scrcpy(config_values, capture_output=False, window_title=None, device_id=None, icon_path=None, session_type='app'):
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
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, startupinfo=startupinfo, env=env)
    else:
        process = subprocess.Popen(cmd, startupinfo=startupinfo, env=env)

    # Adiciona a sessão à lista de sessões ativas
    app_name = window_title or config_values.get('start_app_name') or 'Unknown App'
    add_scrcpy_session(process.pid, app_name, icon_path, cmd, session_type)

    return process

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
