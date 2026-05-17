import asyncio
import queue
import threading
import customtkinter as ctk
import sys
import subprocess
from typing import Optional

from config_manager import CONFIG
from ui_components import ToastNotification, HistoryWindow
from network_client import NetworkClient
from tray_manager import TrayManager

class WANDClient:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.withdraw()
        ctk.set_appearance_mode("dark")
        
        self.current_toast: Optional[ToastNotification] = None
        self.history_window: Optional[HistoryWindow] = None
        # queue.Queue é thread-safe: a thread asyncio escreve, a thread Tkinter lê.
        # A lista simples anterior não garantia isso.
        self.msg_queue: queue.Queue = queue.Queue()
        self.is_running: bool = True
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        # Event que sinaliza quando o loop asyncio já foi criado na thread WS.
        # Evita race condition em show_history/send_reply chamados antes da thread iniciar.
        self._loop_ready = threading.Event()
        self._ws_thread: Optional[threading.Thread] = None
        
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

    def _shutdown_async_loop(self) -> None:
        """
        Encerramento gracioso do loop asyncio.
        Cancela todas as tasks pendentes antes de parar o loop,
        evitando sockets órfãos e TimeWait no OS.
        Substitui o os._exit(0) anterior que era uma terminação abrupta.
        """
        if self.loop and self.loop.is_running():
            # Cancela todas as corrotinas agendadas no loop da thread WS
            for task in asyncio.all_tasks(self.loop):
                self.loop.call_soon_threadsafe(task.cancel)
            # Sinaliza o loop para parar após processar os cancelamentos
            self.loop.call_soon_threadsafe(self.loop.stop)

    def quit_app(self) -> None:
        """Encerra a aplicação de forma limpa."""
        self.is_running = False
        self._shutdown_async_loop()
        self.tray.stop()
        
        def force_exit():
            import os
            try:
                self.root.destroy()
            except Exception:
                pass
            os._exit(0)
            
        self.root.after(200, force_exit)  # Dá tempo para o loop encerrar

    def restart_app(self) -> None:
        """Reinicia o processo de forma limpa."""
        self.is_running = False
        self._shutdown_async_loop()
        self.tray.stop()
        # Reinicia o processo atual de forma robusta no Windows
        subprocess.Popen([sys.executable] + sys.argv)
        
        def force_exit():
            import os
            try:
                self.root.destroy()
            except Exception:
                pass
            os._exit(0)
            
        self.root.after(200, force_exit)


    def _dispatch(self, coro) -> bool:
        """
        Despacha uma corrotina para o loop asyncio da thread WS de forma segura.
        Aguarda até 500ms para o loop estar pronto antes de desistir.
        """
        loop_ready = self._loop_ready.wait(timeout=0.5)
        if not loop_ready or not self.loop or not self.loop.is_running():
            print("[DISPATCH] *** Loop asyncio não está pronto. Comando DESCARTADO. ***")
            return False
        asyncio.run_coroutine_threadsafe(coro, self.loop)
        return True

    def show_history(self):
        """Abre ou atualiza a janela de histórico"""
        # Se a janela já existe e está visível na tela, apenas foca e traz para a frente
        if self.history_window and self.history_window.winfo_exists():
            if self.history_window.state() in ("normal", "zoomed"):
                self.history_window.deiconify()
                self.history_window.focus_force()
                self.history_window.lift()
                return

        if not self.history_window or not self.history_window.winfo_exists():
            self.history_window = HistoryWindow(self.root, on_send_callback=self.send_reply)
        
        self.history_window.deiconify()
        self.history_window.focus_force()
        self.history_window.lift()

        # Agenda a requisição de dados apenas ao abrir a janela inicialmente
        self.root.after(50, self._request_history)

    def _request_history(self):
        """Envia o pedido de histórico ao servidor via WebSocket."""
        self._dispatch(
            self.network.send_command("get_history", {"limit": 50})
        )

    def send_reply(self, remote_jid, text):
        """Dispara comando de resposta via websocket"""
        self._dispatch(
            self.network.send_command("send_message", {"remoteJid": remote_jid, "text": text})
        )

    def check_queue(self) -> None:
        """
        Drena a fila de mensagens na thread principal do Tkinter.
        Usa get_nowait() com tratamento de queue.Empty em vez de pop(0).
        Frequência ajustada para 20ms (fluidos 50 FPS).
        """
        try:
            while True:
                msg_data = self.msg_queue.get_nowait()
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

                    # Atualiza a janela de histórico em tempo real se ela estiver aberta
                    if self.history_window and self.history_window.winfo_exists():
                        new_msg = {
                            "remoteJid": data.get("remoteJid", ""),
                            "senderName": sender,
                            "text": text,
                            "timestamp": data.get("timestamp", 0),
                            "fromMe": 1 if sender == "Você" else 0
                        }
                        self.history_window.add_message_to_top(new_msg)

                elif msg_type == "history":
                    history_list = msg_data.get("data", [])
                    if self.history_window and self.history_window.winfo_exists():
                        self.history_window.update_history(history_list)

        except queue.Empty:
            pass

        self.root.after(20, self.check_queue)

    def start_ws_thread(self) -> None:
        """Inicia a thread dedicada ao loop asyncio do WebSocket."""
        def run_async() -> None:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self._loop_ready.set()
            try:
                self.loop.run_until_complete(self.network.listen())
            except Exception as e:
                print(f"[WS THREAD] Loop asyncio encerrado com: {e}")
            finally:
                self._loop_ready.clear()
                self.loop.close()
                print("[WS THREAD] Loop asyncio fechado limpamente.")

        self._ws_thread = threading.Thread(target=run_async, daemon=True)
        self._ws_thread.start()
        print("[System] Thread WebSocket iniciada.")

    def run(self):
        self.start_ws_thread()
        print(f"[System] W.A.N.D. Client iniciado.")
        self.root.mainloop()

if __name__ == "__main__":
    client = WANDClient()
    client.run()