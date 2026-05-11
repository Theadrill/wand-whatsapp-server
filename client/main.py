import asyncio
import threading
import customtkinter as ctk
import os
import sys
import subprocess

from config_manager import CONFIG
from ui_components import ToastNotification
from network_client import NetworkClient
from tray_manager import TrayManager

class WANDClient:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.withdraw()
        ctk.set_appearance_mode("dark")
        
        self.current_toast = None
        self.msg_queue = []
        self.is_running = True
        
        # Inicializa Gerentes
        self.tray = TrayManager(on_restart=self.restart_app, on_quit=self.quit_app)
        self.network = NetworkClient(self.msg_queue, lambda: self.is_running)
        
        self.tray.setup_tray()
        self.check_queue()

    def quit_app(self):
        self.is_running = False
        self.tray.stop()
        os._exit(0)

    def restart_app(self):
        self.is_running = False
        self.tray.stop()
        # Reinicia o processo atual de forma robusta no Windows
        subprocess.Popen([sys.executable] + sys.argv)
        os._exit(0)

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

    def start_ws_thread(self):
        def run_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.network.listen())
        
        thread = threading.Thread(target=run_async, daemon=True)
        thread.start()

    def run(self):
        self.start_ws_thread()
        print(f"[System] W.A.N.D. Client iniciado.")
        self.root.mainloop()

if __name__ == "__main__":
    client = WANDClient()
    client.run()
