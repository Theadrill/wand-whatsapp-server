import asyncio
import threading
import customtkinter as ctk
import os
import sys
import subprocess

from config_manager import CONFIG
from ui_components import ToastNotification, HistoryWindow
from network_client import NetworkClient
from tray_manager import TrayManager

class WANDClient:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.withdraw()
        ctk.set_appearance_mode("dark")
        
        self.current_toast = None
        self.history_window = None
        self.msg_queue = []
        self.is_running = True
        
        # Inicializa Gerentes
        self.tray = TrayManager(
            on_restart=self.restart_app, 
            on_quit=self.quit_app,
            on_show_history=self.show_history
        )
        self.network = NetworkClient(
            self.msg_queue, 
            lambda: self.is_running,
            status_callback=lambda s: self.tray.update_status(s)
        )
        
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

    def show_history(self):
        """Abre ou atualiza a janela de histórico"""
        if not self.history_window or not self.history_window.winfo_exists():
            self.history_window = HistoryWindow(self.root)
        
        self.history_window.deiconify()
        self.history_window.lift()
        # Removido topmost para que a janela não flutue sobre as outras permanentemente
        
        # Solicita histórico atualizado ao servidor
        asyncio.run_coroutine_threadsafe(
            self.network.send_command("get_history", {"limit": 50}),
            self.loop
        )

    def check_queue(self):
        while self.msg_queue:
            msg_data = self.msg_queue.pop(0)
            msg_type = msg_data.get("type")
            
            if msg_type == "message":
                data = msg_data.get("data", {})
                sender = data.get("from", "Desconhecido")
                text = data.get("text", "")
                sticker = data.get("sticker")
                
                if self.current_toast and self.current_toast.winfo_exists():
                    self.current_toast.destroy()
                
                self.current_toast = ToastNotification(self.root, sender, text, sticker)
                self.current_toast.set_click_callback(self.show_history)
            
            elif msg_type == "history":
                history_list = msg_data.get("data", [])
                if self.history_window and self.history_window.winfo_exists():
                    self.history_window.update_history(history_list)

        self.root.after(100, self.check_queue)

    def start_ws_thread(self):
        def run_async():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self.network.listen())
        
        thread = threading.Thread(target=run_async, daemon=True)
        thread.start()

    def run(self):
        self.start_ws_thread()
        print(f"[System] W.A.N.D. Client iniciado.")
        self.root.mainloop()

if __name__ == "__main__":
    client = WANDClient()
    client.run()
