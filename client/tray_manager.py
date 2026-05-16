import pystray
from PIL import Image
from config_manager import ICON_PATH

class TrayManager:
    def __init__(self, on_restart, on_quit, on_show_history):
        self.tray_icon = None
        self.on_restart = on_restart
        self.on_quit = on_quit
        self.on_show_history = on_show_history

    def setup_tray(self):
        try:
            image = Image.open(ICON_PATH)
            self.tray_icon = pystray.Icon("wand_client", image, "W.A.N.D. Client (Iniciando...)", self._get_menu("Iniciando..."))
            self.tray_icon.run_detached()
        except Exception as e:
            print(f"[Tray] Erro ao carregar bandeja: {e}")

    def _get_menu(self, status):
        return pystray.Menu(
            pystray.MenuItem(f"Status: {status}", lambda: None, enabled=False),
            pystray.MenuItem("Ver Histórico", self.on_show_history, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Reiniciar", self.on_restart),
            pystray.MenuItem("Sair", self.on_quit)
        )

    def update_status(self, status):
        if self.tray_icon:
            # Mapeamento de status para nomes amigáveis
            labels = {
                "connecting": "Conectando ao Server...",
                "connected": "Conectado",
                "failed": "Erro de Conexão",
                "reconnecting": "Tentando reconectar..."
            }
            label = labels.get(status, status)
            self.tray_icon.title = f"W.A.N.D. Client ({label})"
            self.tray_icon.menu = self._get_menu(label)

    def stop(self):
        if self.tray_icon:
            self.tray_icon.stop()
