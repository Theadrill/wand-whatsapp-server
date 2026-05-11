import pystray
from PIL import Image
from config_manager import ICON_PATH

class TrayManager:
    def __init__(self, on_restart, on_quit):
        self.tray_icon = None
        self.on_restart = on_restart
        self.on_quit = on_quit

    def setup_tray(self):
        try:
            image = Image.open(ICON_PATH)
            menu = (
                pystray.MenuItem("W.A.N.D. Client", lambda: None, enabled=False),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Reiniciar", self.on_restart),
                pystray.MenuItem("Sair", self.on_quit)
            )
            self.tray_icon = pystray.Icon("wand_client", image, "W.A.N.D. Client", menu)
            self.tray_icon.run_detached()
        except Exception as e:
            print(f"[Tray] Erro ao carregar bandeja: {e}")

    def stop(self):
        if self.tray_icon:
            self.tray_icon.stop()
