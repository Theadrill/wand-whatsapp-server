import { WebSocketServer } from 'ws';
import { getHistory } from './database.js';
import { sendMessage, getMyName, formatPhoneNumber } from './whatsapp.js';

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

    ws.on('message', async (message) => {
      try {
        const payload = JSON.parse(message);
        
        if (payload.type === 'get_history') {
          const limit = payload.limit || 50;
          const history = await getHistory(limit);
          
          const myName = getMyName ? getMyName() : 'Você';
          const enrichedHistory = history.map(msg => {
            let contactName = msg.contactName || msg.contactVerifiedName || msg.contactDisplayName || msg.senderName || 'Desconhecido';
            if (contactName === 'Você' && msg.fromMe === 0) {
              contactName = formatPhoneNumber ? formatPhoneNumber(msg.remoteJid) : msg.remoteJid;
            }
            
            const isGroup = msg.remoteJid.endsWith('@g.us');
            const groupSuffix = isGroup ? ' (Grupo)' : '';
            
            let senderName = msg.senderName;
            let receiverName = 'Você';
            
            if (msg.fromMe === 1) {
              senderName = myName;
              receiverName = contactName + groupSuffix;
            } else {
              senderName = contactName;
              if (isGroup) {
                receiverName = contactName + groupSuffix;
              } else {
                receiverName = myName;
              }
            }
            
            return {
              id: msg.id,
              remoteJid: msg.remoteJid,
              senderName,
              receiverName,
              text: msg.text,
              timestamp: msg.timestamp,
              fromMe: msg.fromMe
            };
          });
          
          ws.send(JSON.stringify({ type: 'history', data: enrichedHistory }));
        } else if (payload.type === 'send_message') {
          const { remoteJid, text } = payload;
          try {
            await sendMessage(remoteJid, text);
            console.log(`[WebSocket] Resposta enviada para ${remoteJid}`);
            // Opcional: Notificar sucesso ao cliente
            ws.send(JSON.stringify({ type: 'send_status', status: 'success', remoteJid }));
          } catch (err) {
            console.error('[WebSocket] Erro ao enviar resposta:', err.message);
            ws.send(JSON.stringify({ type: 'send_status', status: 'error', message: err.message }));
          }
        }
      } catch (error) {
        console.error('[WebSocket] Erro ao processar mensagem do cliente:', error.message);
      }
    });

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
