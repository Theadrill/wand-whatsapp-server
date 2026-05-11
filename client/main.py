import asyncio
import websockets
import json
import threading
import customtkinter as ctk
import os
import pystray
from PIL import Image
import sys

# Caminhos de arquivos
BASE_DIR = os.path.dirname(__file__)
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
ICON_PATH = os.path.join(BASE_DIR, "icon_client.ico")

def load_config():
    """Carrega as configurações do arquivo JSON"""
    default_config = {
        "server_hosts": ["localhost"],
        "server_port": 4750,
        "reconnect_delay": 5,
        "toast_width": 350,
        "toast_height": 120
    }
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r') as f:
                return {**default_config, **json.load(f)}
    except Exception as e:
        print(f"[Config] Erro ao carregar config.json: {e}")
    return default_config

# Carrega a configuração globalmente
CONFIG = load_config()

class ToastNotification(ctk.CTkToplevel):
    def __init__(self, master, sender, message):
        super().__init__(master)
        self.title("W.A.N.D. Notification")
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        
        # Truque para cantos arredondados: janela transparente e frame interno arredondado
        transparent_color = "#000001"
        self.attributes("-transparentcolor", transparent_color)
        self.configure(fg_color=transparent_color)
        
        width = CONFIG['toast_width']
        height = CONFIG['toast_height']
        
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = screen_width - width - 20
        y = screen_height - height - 60
        self.geometry(f"{width}x{height}+{x}+{y}")

        # Container Principal Arredondado
        self.container = ctk.CTkFrame(
            self, 
            fg_color="#1EA952", 
            corner_radius=15, 
            border_width=1, 
            border_color="#075E54"
        )
        self.container.pack(fill="both", expand=True, padx=2, pady=2)

        self.container.grid_columnconfigure(0, weight=1)
        
        # Header
        self.header_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=(12, 0))
        self.header_frame.grid_columnconfigure(0, weight=1)

        # Sombra do Nome
        self.lbl_sender_shadow = ctk.CTkLabel(
            self.header_frame, 
            text=sender, 
            font=ctk.CTkFont(family="Segoe UI", weight="bold", size=15), 
            text_color="#075E54"
        )
        self.lbl_sender_shadow.grid(row=0, column=0, sticky="w", padx=(1, 0), pady=(1, 0))

        self.lbl_sender = ctk.CTkLabel(
            self.header_frame, 
            text=sender, 
            font=ctk.CTkFont(family="Segoe UI", weight="bold", size=15), 
            text_color="#FFFFFF"
        )
        self.lbl_sender.grid(row=0, column=0, sticky="w")

        self.btn_close = ctk.CTkButton(
            self.header_frame, 
            text="✕", 
            width=20, 
            height=20, 
            fg_color="transparent", 
            hover_color="#128C7E", 
            text_color="#FFFFFF",
            font=ctk.CTkFont(size=12),
            command=self.destroy
        )
        self.btn_close.grid(row=0, column=1, sticky="e")

        # Sombra da Mensagem
        self.lbl_message_shadow = ctk.CTkLabel(
            self.container, 
            text=message, 
            wraplength=width-40, 
            justify="left", 
            text_color="#075E54",
            font=ctk.CTkFont(family="Segoe UI", size=13)
        )
        self.lbl_message_shadow.grid(row=1, column=0, sticky="w", padx=(16, 0), pady=(6, 21))

        # Mensagem Principal
        self.lbl_message = ctk.CTkLabel(
            self.container, 
            text=message, 
            wraplength=width-40, 
            justify="left", 
            text_color="#F0F2F5",
            font=ctk.CTkFont(family="Segoe UI", size=13)
        )
        self.lbl_message.grid(row=1, column=0, sticky="w", padx=15, pady=(5, 20))

class WANDClient:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.withdraw()
        ctk.set_appearance_mode("dark")
        
        self.current_toast = None
        self.msg_queue = []
        self.tray_icon = None
        self.is_running = True
        self.current_host_idx = 0
        
        self.setup_tray()
        self.check_queue()

    def setup_tray(self):
        try:
            image = Image.open(ICON_PATH)
            menu = (
                pystray.MenuItem("W.A.N.D. Client", lambda: None, enabled=False),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Reiniciar", self.restart_app),
                pystray.MenuItem("Sair", self.quit_app)
            )
            self.tray_icon = pystray.Icon("wand_client", image, "W.A.N.D. Client", menu)
            self.tray_icon.run_detached()
        except Exception as e:
            print(f"[Tray] Erro ao carregar bandeja: {e}")

    def quit_app(self):
        self.is_running = False
        if self.tray_icon:
            self.tray_icon.stop()
        os._exit(0)

    def restart_app(self):
        self.is_running = False
        if self.tray_icon:
            self.tray_icon.stop()
        # Reinicia o processo atual
        os.execv(sys.executable, ['python'] + sys.argv)

    def check_queue(self):
        while self.msg_queue:
            msg_data = self.msg_queue.pop(0)
            if msg_data.get("type") == "message":
                data = msg_data.get("data", {})
                sender = data.get("from", "Desconhecido")
                text = data.get("text", "")
                if self.current_toast and self.current_toast.winfo_exists():
                    self.current_toast.destroy()
                self.current_toast = ToastNotification(self.root, sender, text)
        self.root.after(100, self.check_queue)

    async def listen(self):
        hosts = CONFIG['server_hosts']
        port = CONFIG['server_port']
        
        while self.is_running:
            host = hosts[self.current_host_idx]
            ws_url = f"ws://{host}:{port}"
            
            try:
                print(f"[WS] Tentando conectar em {ws_url}...")
                async with websockets.connect(ws_url) as websocket:
                    print(f"[WS] Conectado com sucesso em {ws_url}")
                    while self.is_running:
                        message = await websocket.recv()
                        data = json.loads(message)
                        self.msg_queue.append(data)
            except Exception as e:
                if self.is_running:
                    # Rotaciona para o próximo host se falhar
                    self.current_host_idx = (self.current_host_idx + 1) % len(hosts)
                    next_host = hosts[self.current_host_idx]
                    print(f"[WS] Falha em {host}. Próximo: {next_host} em {CONFIG['reconnect_delay']}s...")
                    await asyncio.sleep(CONFIG['reconnect_delay'])

    def start_ws_thread(self):
        def run_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.listen())
        
        thread = threading.Thread(target=run_async, daemon=True)
        thread.start()

    def run(self):
        self.start_ws_thread()
        print(f"[System] W.A.N.D. Client iniciado.")
        self.root.mainloop()

if __name__ == "__main__":
    client = WANDClient()
    client.run()
