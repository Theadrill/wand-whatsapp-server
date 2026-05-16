import asyncio
import websockets
import json
from config_manager import CONFIG

class NetworkClient:
    def __init__(self, msg_queue, is_running_callback, status_callback=None):
        self.msg_queue = msg_queue
        self.is_running_callback = is_running_callback
        self.status_callback = status_callback
        self.current_host_idx = 0

    def _update_status(self, status):
        if self.status_callback:
            self.status_callback(status)

    async def listen(self):
        hosts = CONFIG['server_hosts']
        port = CONFIG['server_port']
        
        while self.is_running_callback():
            host = hosts[self.current_host_idx]
            ws_url = f"ws://{host}:{port}"
            
            try:
                print(f"[WS] Tentando conectar em {ws_url}...")
                self._update_status("connecting")
                
                async with websockets.connect(ws_url) as websocket:
                    self.websocket = websocket # Armazena para envio de mensagens
                    print(f"[WS] Conectado com sucesso em {ws_url}")
                    self._update_status("connected")
                    
                    while self.is_running_callback():
                        message = await websocket.recv()
                        data = json.loads(message)
                        self.msg_queue.append(data)
            except Exception as e:
                self.websocket = None
                if self.is_running_callback():
                    self._update_status("failed")
                    # Rotaciona para o próximo host se falhar
                    self.current_host_idx = (self.current_host_idx + 1) % len(hosts)
                    next_host = hosts[self.current_host_idx]
                    print(f"[WS] Falha em {host}. Próximo: {next_host} em {CONFIG['reconnect_delay']}s...")
                    self._update_status("reconnecting")
                    await asyncio.sleep(CONFIG['reconnect_delay'])

    async def send_command(self, cmd_type, payload={}):
        if hasattr(self, 'websocket') and self.websocket:
            try:
                msg = json.dumps({"type": cmd_type, **payload})
                await self.websocket.send(msg)
            except Exception as e:
                print(f"[WS] Erro ao enviar comando {cmd_type}: {e}")
