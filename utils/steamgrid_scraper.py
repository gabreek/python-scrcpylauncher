# FILE: utils/steamgrid_scraper.py
# PURPOSE: Faz o scraping de ícones de jogos do SteamGridDB.

import os
import re
import requests
from urllib.parse import quote_plus
from PIL import Image
from io import BytesIO

def get_game_icon(game_name, game_path, app_config, download_if_missing=True):
    """
    Obtém o ícone de um jogo do Winlator, buscando no SteamGridDB.
    Retorna o caminho para o ícone em cache ou None.
    """
    cache_dir = app_config.get_icon_cache_dir()
    # Usa o nome do arquivo .desktop como chave única para o ícone
    icon_key = os.path.basename(game_path)
    icon_path = os.path.join(cache_dir, f"{icon_key}.png")

    # 1. Verifica se o ícone já existe no cache
    if os.path.exists(icon_path):
        return icon_path

    # 2. Verifica metadados para não baixar novamente se já falhou ou se é customizado
    metadata = app_config.get_app_metadata(game_path)
    if not download_if_missing or metadata.get('steamgrid_fetch_failed') or metadata.get('custom_icon'):
        return None

    try:
        # 3. Prepara o termo de busca e o URL
        search_term = quote_plus(game_name)
        search_url = f"https://www.steamgriddb.com/search/grids/512x512,1024x1024/all/all?term={search_term}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        print(f"Buscando ícone para '{game_name}' em: {search_url}")
        response = requests.get(search_url, headers=headers)
        response.raise_for_status()

        # 4. Encontra o URL do primeiro ícone na página usando Regex
        match = re.search(r'<a[^>]+class="grid-item-inner"[^>]*>.*?<img[^>]+src="([^"]+)"', response.text, re.DOTALL)
        if not match:
            print(f"Nenhum ícone encontrado no SteamGridDB para '{game_name}'")
            app_config.save_app_metadata(game_path, {"steamgrid_fetch_failed": True})
            return None

        icon_url = match.group(1)
        print(f"Ícone encontrado: {icon_url}")

        # 5. Baixa a imagem
        icon_response = requests.get(icon_url, stream=True)
        icon_response.raise_for_status()

        # Abre a imagem em memória, redimensiona, e salva como PNG no cache
        with Image.open(BytesIO(icon_response.content)) as img:
            img_resized = img.resize((48, 48), Image.LANCZOS)
            img_resized.save(icon_path, "PNG")

        # 6. Atualiza os metadados para indicar que a busca foi bem-sucedida
        app_config.save_app_metadata(game_path, {"steamgrid_fetch_failed": False})
        return icon_path

    except requests.exceptions.RequestException as e:
        print(f"Falha ao baixar o ícone para '{game_name}': {e}")
        app_config.save_app_metadata(game_path, {"steamgrid_fetch_failed": True})
        return None
    except Exception as e:
        print(f"Ocorreu um erro ao processar o ícone para '{game_name}': {e}")
        app_config.save_app_metadata(game_path, {"steamgrid_fetch_failed": True})
        return None
