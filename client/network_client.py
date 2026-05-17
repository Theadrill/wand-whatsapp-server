import asyncio
import queue
import websockets
import json
from typing import Callable, Optional, Any
from config_manager import CONFIG


class NetworkClient:
    """
    Cliente WebSocket assíncrono.

    A comunicação entre a thread asyncio e a thread principal do Tkinter
    é feita via `queue.Queue`, que é thread-safe por design.
    A lista simples (`[]`) anterior não oferecia essa garantia.
    """

    def __init__(
        self,
        msg_queue: queue.Queue,
        is_running_callback: Callable[[], bool],
        status_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.msg_queue = msg_queue
        self.is_running_callback = is_running_callback
        self.status_callback = status_callback
        self.current_host_idx: int = 0
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None

    def _update_status(self, status: str) -> None:
        if self.status_callback:
            self.status_callback(status)

    async def listen(self) -> None:
        """Loop principal de escuta. Reconecta automaticamente em caso de falha."""
        hosts = CONFIG['server_hosts']
        port = CONFIG['server_port']

        while self.is_running_callback():
            host = hosts[self.current_host_idx]
            ws_url = f"ws://{host}:{port}"

            try:
                print(f"[WS] Tentando conectar em {ws_url}...")
                self._update_status("connecting")

                # Timeout de abertura de 10s para evitar travar em hosts que não respondem
                async with websockets.connect(ws_url, open_timeout=10) as websocket:
                    self.websocket = websocket
                    print(f"[WS] Conectado com sucesso em {ws_url}")
                    self._update_status("connected")

                    while self.is_running_callback():
                        message = await websocket.recv()
                        data = json.loads(message)
                        # put_nowait é seguro aqui pois a Queue não tem maxsize definido
                        self.msg_queue.put_nowait(data)

            except asyncio.CancelledError:
                # Encerramento gracioso solicitado pelo método shutdown()
                print("[WS] Tarefa de escuta cancelada. Encerrando limpamente.")
                self.websocket = None
                raise  # Re-raise obrigatório para propagar o cancelamento

            except Exception as e:
                self.websocket = None
                if self.is_running_callback():
                    self._update_status("failed")
                    self.current_host_idx = (self.current_host_idx + 1) % len(hosts)
                    next_host = hosts[self.current_host_idx]
                    print(f"[WS] Falha em {host}: {e}. Próximo: {next_host} em {CONFIG['reconnect_delay']}s...")
                    self._update_status("reconnecting")
                    await asyncio.sleep(CONFIG['reconnect_delay'])

    async def send_command(self, cmd_type: str, payload: dict = {}) -> None:
        """
        Envia um comando JSON para o servidor via WebSocket.

        ATENÇÃO: Não usar `.open` aqui. Na nova API do websockets (v12+),
        o objeto de conexão é `ClientConnection` — não tem atributo `.open`.
        Verificar com None e capturar exceções é o padrão correto.
        """
        if self.websocket is None:
            print(f"[WS] send_command('{cmd_type}'): websocket é None, ignorando.")
            return
        try:
            msg = json.dumps({"type": cmd_type, **payload})
            await self.websocket.send(msg)
            print(f"[WS] Comando '{cmd_type}' enviado com sucesso.")
        except Exception as e:
            print(f"[WS] Erro ao enviar comando '{cmd_type}': {e}")
