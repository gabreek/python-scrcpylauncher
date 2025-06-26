# FILE: utils/adb_handler.py
# PURPOSE: Centraliza todos os comandos que interagem com o Android Debug Bridge (adb).

import subprocess
import shlex
import re
import os

def _run_adb_command(command, device_id=None, print_command=False, ignore_errors=False):
    """Helper para executar um comando adb, retornando a saída decodificada."""
    base_cmd = ['adb']
    if device_id:
        base_cmd.extend(['-s', device_id])

    full_cmd = base_cmd + command

    if print_command:
        print('Executing ADB Command:', shlex.join(full_cmd))

    startupinfo = None
    if os.name == 'nt':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    try:
        result = subprocess.check_output(full_cmd, text=True, stderr=subprocess.PIPE, startupinfo=startupinfo)
        return result.strip()
    except subprocess.CalledProcessError as e:
        if not ignore_errors:
            print(f"ADB command failed: {e}")
        return ""

def get_device_info(device_id=None):
    """Obtém o nome do modelo e o nível da bateria do dispositivo."""
    name = _run_adb_command(['shell', 'getprop', 'ro.product.vendor.marketname'], device_id)
    if not name: return "Device not connected or ADB error"
    battery_output = _run_adb_command(['shell', 'dumpsys', 'battery'], device_id, ignore_errors=True)
    level_match = re.search(r'level: (\d+)', battery_output)
    battery_level = level_match.group(1) if level_match else "?"
    return f"Connected to {name} (Battery: {battery_level}%)"

def list_winlator_shortcuts(device_id=None):
    """Lista os caminhos dos atalhos .desktop do Winlator no dispositivo."""
    command = ['shell', 'find', '/storage/emulated/0/Download/Winlator/Frontend/', '-type', 'f', '-name', '*.desktop']
    output = _run_adb_command(command, device_id)
    return output.splitlines() if output else []

def list_winlator_shortcuts_with_names(device_id=None):
    """Retorna uma lista de tuplas (nome, caminho) para os atalhos do Winlator."""
    shortcuts = list_winlator_shortcuts(device_id)
    games_with_names = []
    for path in shortcuts:
        if path:
            basename = os.path.basename(path)
            name = basename.rsplit('.desktop', 1)[0]
            games_with_names.append((name, path))
    return games_with_names

def get_game_executable_info(shortcut_path, device_id=None):
    """Lê o arquivo .desktop para encontrar o caminho do .exe no /sdcard."""
    content = _run_adb_command(['shell', 'cat', shlex.quote(shortcut_path)], device_id)
    if not content:
        return None

    game_dir_part = None
    exe_name = None

    # --- LÓGICA CORRIGIDA ---
    # Tenta encontrar o caminho baseado em 'Path' e 'StartupWMClass'
    for line in content.splitlines():
        if line.lower().startswith('path='):
            # Ex: Path=/.../dosdevices/d:/Games/Alan Wake
            # Captura tudo depois de 'd:'
            match = re.search(r'dosdevices/d:([^"]+)', line, re.IGNORECASE)
            if match:
                game_dir_part = match.group(1).strip()
        elif line.lower().startswith('startupwmclass='):
            # Ex: StartupWMClass=alanwake.exe
            exe_name = line.split('=', 1)[1].strip()

    if game_dir_part and exe_name:
        # Constrói o caminho completo no Android
        full_path_on_sdcard = f"/storage/emulated/0/Download{game_dir_part}/{exe_name}"
        # Garante barras corretas para o shell do Android
        return full_path_on_sdcard.replace('\\', '/')

    # Fallback para o formato antigo com 'Exec='
    for line in content.splitlines():
        if line.lower().startswith('exec='):
            match = re.search(r'wine\s+"([^"]+)"', line, re.IGNORECASE)
            if match:
                exec_path = match.group(1)
                if exec_path.lower().startswith('/home/xuser/.wine/dosdevices/d:'):
                    full_path_on_sdcard = exec_path.replace('/home/xuser/.wine/dosdevices/d:', '/storage/emulated/0/Download')
                    return full_path_on_sdcard.replace('\\', '/')

    return None # Retorna None se nenhum formato for encontrado

def pull_file(remote_path, local_path, device_id=None):
    """Puxa (baixa) um arquivo do dispositivo para o computador local."""
    _run_adb_command(['pull', remote_path, local_path], device_id, print_command=True)

def start_winlator_app(shortcut_path, display_id, package_name, device_id=None):
    """Inicia um aplicativo Winlator em um display virtual específico."""
    file_name = os.path.basename(shortcut_path)
    full_path = f"/storage/emulated/0/Download/Winlator/Frontend/{file_name}"
    quoted_path = shlex.quote(full_path)
    activity_name = ".XServerDisplayActivity"
    component = f"{package_name}/{activity_name}"
    remote_command_str = (
        f"am start --display {display_id} "
        f"-n {component} "
        f"--es shortcut_path {quoted_path} "
        f"--activity-clear-task --activity-clear-top --activity-no-history"
    )
    command = ['shell', remote_command_str]
    _run_adb_command(command, device_id, print_command=True)

def turn_screen_on(device_id=None):
    _run_adb_command(['shell', 'input', 'keyevent', 'KEYCODE_WAKEUP'], device_id)

def turn_screen_off(device_id=None):
    output = _run_adb_command(['shell', 'dumpsys', 'input_method'], device_id)
    if 'mInteractive=true' in output:
        _run_adb_command(['shell', 'input', 'keyevent', 'KEYCODE_POWER'], device_id)
