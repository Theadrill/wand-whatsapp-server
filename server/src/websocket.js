import { WebSocketServer } from 'ws';
import { getHistory, getChats, getChatHistory, getContact, getChatHistoryUnified, getAllContacts } from './database.js';
import { sendMessage, getMyName, formatPhoneNumber, getSock, getContactsMemory } from './whatsapp.js';

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
        } else if (payload.type === 'get_chats') {
          try {
            const rawChats = await getChats();
            const myName = getMyName ? getMyName() : 'Você';
            const sock = getSock ? getSock() : null;
            const contacts = getContactsMemory ? getContactsMemory() : null;
            
            const chatMap = new Map(); // Indexado pelo JID real unificado (PN)

            for (const chat of rawChats) {
              const isGroup = chat.remoteJid.endsWith('@g.us');
              
              // Se for um JID técnico de sincronização contendo ":", ignora totalmente
              if (chat.remoteJid.includes(':')) continue;

              // Determina o JID real unificado (preferencialmente PN)
              let unifiedJid = chat.remoteJid;
              let pnJid = null;
              
              if (chat.remoteJid.endsWith('@lid') && sock && sock.signalRepository && sock.signalRepository.lidMapping) {
                try {
                  pnJid = await sock.signalRepository.lidMapping.getPNForLID(chat.remoteJid);
                  if (pnJid) {
                    unifiedJid = pnJid;
                  }
                } catch (err) {
                  // Silencioso
                }
              }

              // Busca o contato na agenda local usando tanto o JID da conversa quanto o PN resolvido
              let contact = null;
              if (contacts) {
                if (contacts.has(chat.remoteJid)) {
                  contact = contacts.get(chat.remoteJid);
                } else if (pnJid && contacts.has(pnJid)) {
                  contact = contacts.get(pnJid);
                }
              }

              // Se não estiver no cache em memória, busca na tabela contacts do SQLite
              if (!contact) {
                try {
                  contact = await getContact(chat.remoteJid) || (pnJid ? await getContact(pnJid) : null);
                  if (contact && contacts) {
                    contacts.set(contact.jid, contact);
                  }
                } catch (dbErr) {
                  // Silencioso
                }
              }

              let contactName = 'Desconhecido';
              let displayName = null;

              if (contact) {
                contactName = contact.name || contact.verifiedName || contact.displayName || 'Desconhecido';
                displayName = contact.name || contact.verifiedName || contact.displayName;
              }

              // Se o contato não está na agenda, tenta usar os fallbacks de pushName públicos
              if (!displayName) {
                if (isGroup) {
                  displayName = chat.lastSenderName || chat.remoteJid;
                } else {
                  // 1. pushName público de quem enviou a última mensagem recebida
                  if (chat.lastIncomingSenderName && chat.lastIncomingSenderName !== 'Você' && chat.lastIncomingSenderName !== 'Desconhecido') {
                    displayName = chat.lastIncomingSenderName;
                  } 
                  // 2. pushName público geral da última mensagem
                  else if (chat.lastSenderName && chat.lastSenderName !== 'Você' && chat.lastSenderName !== 'Desconhecido') {
                    displayName = chat.lastSenderName;
                  } 
                  // 3. Fallback final: número telefônico formatado
                  else {
                    displayName = formatPhoneNumber ? formatPhoneNumber(unifiedJid) : unifiedJid;
                  }
                }
              }

              if (contactName === 'Desconhecido' && !isGroup) {
                contactName = displayName;
              }

              if (chat.lastFromMe === 1) {
                contactName = myName;
              }

              const chatData = {
                jid: chat.remoteJid,
                name: displayName + (isGroup ? ' (Grupo)' : ''),
                unreadCount: 0,
                lastMessage: {
                  text: chat.lastText,
                  timestamp: chat.lastTimestamp,
                  fromMe: chat.lastFromMe === 1,
                  senderName: chat.lastFromMe === 1 ? myName : contactName
                }
              };

              // Se o JID unificado já existe no mapa, mantém a mensagem mais recente
              if (chatMap.has(unifiedJid)) {
                const existing = chatMap.get(unifiedJid);
                if (chatData.lastMessage.timestamp > existing.lastMessage.timestamp) {
                  chatMap.set(unifiedJid, chatData);
                }
              } else {
                chatMap.set(unifiedJid, chatData);
              }
            }

            const enrichedChats = Array.from(chatMap.values());
            // Ordena pela mensagem mais recente de todas
            enrichedChats.sort((a, b) => b.lastMessage.timestamp - a.lastMessage.timestamp);
            
            ws.send(JSON.stringify({ type: 'chats', data: enrichedChats }));
          } catch (err) {
            console.error('[WebSocket] Erro ao carregar chats:', err.message);
          }
        } else if (payload.type === 'get_chat_history') {
          try {
            const { jid } = payload;
            const limit = payload.limit || 50;
            const sock = getSock ? getSock() : null;

            // Se for LID ou PN, resolve o JID alternativo para unificar o histórico
            let alternateJid = null;
            if (jid.endsWith('@lid') && sock && sock.signalRepository && sock.signalRepository.lidMapping) {
              try {
                alternateJid = await sock.signalRepository.lidMapping.getPNForLID(jid);
              } catch (err) {
                // Silencioso
              }
            } else if (jid.endsWith('@s.whatsapp.net') && sock && sock.signalRepository && sock.signalRepository.lidMapping) {
              try {
                alternateJid = await sock.signalRepository.lidMapping.getLIDForPN(jid);
              } catch (err) {
                // Silencioso
              }
            }

            let history;
            if (alternateJid) {
              history = await getChatHistoryUnified(jid, alternateJid, limit);
            } else {
              history = await getChatHistory(jid, limit);
            }
            
            const myName = getMyName ? getMyName() : 'Você';
            const enrichedMessages = history.map(msg => {
              let contactName = msg.contactName || msg.contactVerifiedName || msg.contactDisplayName || msg.senderName || 'Desconhecido';
              if (contactName === 'Você' && msg.fromMe === 0) {
                contactName = formatPhoneNumber ? formatPhoneNumber(msg.remoteJid) : msg.remoteJid;
              }
              
              let senderName = msg.senderName;
              if (msg.fromMe === 1) {
                senderName = myName;
              }
              
              return {
                id: msg.id,
                remoteJid: msg.remoteJid,
                senderName,
                text: msg.text,
                timestamp: msg.timestamp,
                fromMe: msg.fromMe === 1
              };
            });
            
            enrichedMessages.reverse();
            
            ws.send(JSON.stringify({ 
               type: 'chat_history', 
               data: {
                 jid,
                 messages: enrichedMessages
               } 
            }));
          } catch (err) {
            console.error('[WebSocket] Erro ao buscar historico do chat:', err.message);
          }
        } else if (payload.type === 'send_message') {
          const { remoteJid, text } = payload;
          try {
            await sendMessage(remoteJid, text);
            console.log(`[WebSocket] Resposta enviada para ${remoteJid}`);
            ws.send(JSON.stringify({ type: 'send_status', status: 'success', remoteJid }));
          } catch (err) {
            console.error('[WebSocket] Erro ao enviar resposta:', err.message);
            ws.send(JSON.stringify({ type: 'send_status', status: 'error', message: err.message }));
          }
        } else if (payload.type === 'get_contacts') {
          try {
            const contacts = await getAllContacts();
            
            const cleanContacts = contacts
              .filter(c => c.jid && !c.jid.includes(':'))
              .map(c => {
                const displayName = c.name || c.verifiedName || c.displayName || (formatPhoneNumber ? formatPhoneNumber(c.jid) : c.jid);
                return {
                  jid: c.jid,
                  name: displayName
                };
              });

            ws.send(JSON.stringify({ type: 'contacts', data: cleanContacts }));
          } catch (err) {
            console.error('[WebSocket] Erro ao buscar contatos:', err.message);
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
