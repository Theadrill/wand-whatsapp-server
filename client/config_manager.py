import os
import json

BASE_DIR = os.path.dirname(__file__)
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
ICON_PATH = os.path.join(BASE_DIR, "icon_client.ico")

def load_config():
    """Carrega as configurações do arquivo JSON"""
    default_config = {
        "server_hosts": ["localhost"],
        "server_port": 4750,
        "reconnect_delay": 5,
        "toast_width": 375,
        "toast_height": 150
    }
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r') as f:
                return {**default_config, **json.load(f)}
    except Exception as e:
        print(f"[Config] Erro ao carregar config.json: {e}")
    return default_config

CONFIG = load_config()
