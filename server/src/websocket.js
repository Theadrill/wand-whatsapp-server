import { WebSocketServer } from 'ws';

let wss;
const clients = new Set();
let lastQRCode = null;
let lastStatus = 'disconnected';

/**
 * Inicializa o servidor WebSocket anexado ao servidor HTTP
 * @param {http.Server} server - Instância do servidor HTTP
 */
export function setupWebSocket(server) {
  wss = new WebSocketServer({ server });

  console.log('[WebSocket] Servidor WS inicializado e anexado ao HTTP');

  wss.on('connection', (ws) => {
    clients.add(ws);
    console.log(`[WebSocket] Novo cliente conectado. Total: ${clients.size}`);

    // Envia o estado atual imediatamente para o novo cliente
    ws.send(JSON.stringify({ type: 'info', message: 'Conectado ao W.A.N.D. Server' }));
    
    if (lastStatus === 'connected') {
      ws.send(JSON.stringify({ type: 'status', data: 'connected' }));
    } else if (lastQRCode) {
      ws.send(JSON.stringify({ type: 'qrcode', data: lastQRCode }));
    }

    ws.on('close', () => {
      clients.delete(ws);
      console.log(`[WebSocket] Cliente desconectado. Total: ${clients.size}`);
    });

    ws.on('error', (error) => {
      console.error('[WebSocket] Erro no cliente:', error.message);
      clients.delete(ws);
    });
  });

  return {
    broadcast
  };
}

/**
 * Envia uma mensagem para todos os clientes conectados e armazena o estado
 * @param {Object} data - Objeto que será convertido em JSON e enviado
 */
export function broadcast(data) {
  // Armazena o estado para novos clientes
  if (data.type === 'qrcode') lastQRCode = data.data;
  if (data.type === 'status') {
    lastStatus = data.data;
    if (data.data === 'connected') lastQRCode = null;
  }

  if (!wss) return;

  const payload = JSON.stringify(data);
  
  clients.forEach((client) => {
    if (client.readyState === 1) { // 1 = OPEN
      client.send(payload);
    }
  });
}
