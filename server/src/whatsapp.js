import makeWASocket, {
  useMultiFileAuthState,
  DisconnectReason,
  fetchLatestBaileysVersion
} from '@whiskeysockets/baileys';
import { Boom } from '@hapi/boom';
import QRCode from 'qrcode';
import pino from 'pino';
import { broadcast } from './websocket.js';
import { updateTrayStatus } from './tray.js';
import { processSticker } from './mediaHandler.js';
import { saveMessage, setChatMutedStatus, isChatMutedInDB, saveContact, getContact } from './database.js';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Carregamento de configuração
const configPath = path.resolve(__dirname, '../config.json');
let config = { allow_self_messages: false, allow_groups_messages: false, filter_muted_chats: true };

try {
  if (fs.existsSync(configPath)) {
    const data = fs.readFileSync(configPath, 'utf8');
    config = JSON.parse(data);
    console.log('[Config] Servidor carregado:', config);
  }
} catch (err) {
  console.error('[Config] Erro ao carregar config.json:', err.message);
}

// Logger configurado para erro para evitar poluição, conforme o projeto de referência
const logger = pino({ level: 'error' });

// Criação de um Store local simples para metadados (já que o makeInMemoryStore não está disponível nesta versão)
const storePath = path.resolve(__dirname, '../baileys_store.json');
const contactsPath = path.resolve(__dirname, '../baileys_contacts.json');
let chats = new Map();
export const lidToPnMap = new Map();
export const pnToLidMap = new Map();
let contacts = new Map();

// Propriedades seguras para persistência (evita salvar o conteúdo das mensagens)
const SAFE_CHAT_PROPS = ['id', 'name', 'muteEndTime', 'unreadCount', 'lastMsgTimestamp'];

function sanitizeChat(chat) {
  const sanitized = {};
  SAFE_CHAT_PROPS.forEach(prop => {
    if (chat[prop] !== undefined) sanitized[prop] = chat[prop];
  });
  return sanitized;
}

/**
 * Verifica se um chat está silenciado de forma segura, tratando Longs, strings e números.
 */
function isChatMuted(chat) {
  if (!chat || chat.muteEndTime === undefined || chat.muteEndTime === null) {
    return false;
  }

  const mute = chat.muteEndTime;
  let muteVal = null;

  if (typeof mute === 'object' && mute !== null && typeof mute.toNumber === 'function') {
    muteVal = mute.toNumber();
  } else if (typeof mute === 'object' && mute !== null) {
    if (mute.low !== undefined) {
      muteVal = mute.low;
    }
  } else {
    muteVal = Number(mute);
  }

  if (isNaN(muteVal)) {
    return false;
  }

  // -1 indica silenciado permanentemente
  if (muteVal === -1) {
    return true;
  }

  // Auto-detecção de segundos vs milissegundos
  const muteMs = muteVal < 100000000000 ? muteVal * 1000 : muteVal;
  return muteMs > Date.now();
}

/**
 * Mescla dois objetos de chat, preservando o status de silenciamento ativo
 * caso o novo objeto traga o silenciamento como nulo ou indefinido (comum em sincronizações de histórico).
 */
function mergeChat(oldChat, newChat) {
  const merged = { ...oldChat, ...newChat };
  if (isChatMuted(oldChat) && !isChatMuted(newChat)) {
    merged.muteEndTime = oldChat.muteEndTime;
  }
  return merged;
}

try {
  if (fs.existsSync(storePath)) {
    const data = JSON.parse(fs.readFileSync(storePath, 'utf-8'));
    // Carrega e sanitiza cada chat para garantir que mensagens antigas não fiquem na memória
    Object.entries(data).forEach(([id, chat]) => {
      const sanitized = sanitizeChat(chat);
      chats.set(id, sanitized);
      
      // Sincroniza status do store local com o banco de dados em segundo plano
      if (isChatMuted(sanitized)) {
        setChatMutedStatus(id, true).catch(err => {
          console.error(`[DB] Erro ao sincronizar silenciamento inicial de ${id}:`, err);
        });
      }
      
      // Sincroniza nome do chat/grupo no banco de dados SQLite
      if (chat.name) {
        saveContact({
          jid: id,
          name: chat.name
        }).catch(() => {});
      }
    });
    console.log('[WhatsApp] Store local carregado e sanitizado.');
  }
} catch (e) {
  console.error('[WhatsApp] Erro ao ler store local:', e.message);
}

try {
  if (fs.existsSync(contactsPath)) {
    const data = JSON.parse(fs.readFileSync(contactsPath, 'utf-8'));
    Object.entries(data).forEach(([id, contact]) => {
      contacts.set(id, contact);
      
      // Sincroniza no SQLite para garantir consistência no banco de dados
      saveContact({
        jid: id,
        name: contact.name,
        verifiedName: contact.verifiedName,
        displayName: contact.displayName
      }).catch(() => {});

      // Se o contato tiver um LID associado, também salva as informações sob o JID do LID!
      if (contact.lid) {
        saveContact({
          jid: contact.lid,
          name: contact.name,
          verifiedName: contact.verifiedName,
          displayName: contact.displayName
        }).catch(() => {});
      }
    });
    console.log('[WhatsApp] Contatos locais carregados.');
  }
} catch (e) {
  console.error('[WhatsApp] Erro ao ler contatos locais:', e.message);
}

// Persiste o store a cada 10s usando operações NÃO-BLOQUEANTES (fs.promises).
// O writeFileSync anterior bloqueava o Event Loop do Node.js durante a serialização
// e a escrita em disco, o que causava latência nas mensagens e nas conexões WS.
const persistStores = async () => {
  try {
    const dataChats = Object.fromEntries(chats);
    await fs.promises.writeFile(storePath, JSON.stringify(dataChats), 'utf-8');

    const dataContacts = Object.fromEntries(contacts);
    await fs.promises.writeFile(contactsPath, JSON.stringify(dataContacts), 'utf-8');
  } catch (e) {
    console.error('[WhatsApp] Erro ao salvar stores locais:', e.message);
  }
};

setInterval(persistStores, 10_000);

/**
 * Formata um JID numérico em máscara elegante: +55 (XX) XXXXX-XXXX
 */
export function formatPhoneNumber(jid) {
  if (!jid) return '';
  const num = jid.split('@')[0];
  if (num.startsWith('55') && (num.length === 12 || num.length === 13)) {
    const ddd = num.substring(2, 4);
    const rest = num.substring(4);
    if (rest.length === 9) {
      return `+55 (${ddd}) ${rest.substring(0, 5)}-${rest.substring(5)}`;
    } else if (rest.length === 8) {
      return `+55 (${ddd}) ${rest.substring(0, 4)}-${rest.substring(4)}`;
    }
  }
  return `+${num}`;
}

export function getMyName() {
  if (sock && sock.user) {
    if (sock.user.name) return sock.user.name;
    
    const selfJid = sock.user.id.split(':')[0] + '@s.whatsapp.net';
    const selfContact = contacts.get(selfJid);
    if (selfContact && (selfContact.name || selfContact.verifiedName || selfContact.displayName)) {
      return selfContact.name || selfContact.verifiedName || selfContact.displayName;
    }
  }
  return 'Você';
}

/**
 * Resolve o nome do remetente com base na Esteira de Resolução e resolução de LID (Fases 3.1 & 3.2)
 */
async function resolveSenderName(msg) {
  const isMe = msg.key.fromMe;
  if (isMe) {
    return 'Você';
  }

  const senderJid = msg.key.participant || msg.participant || msg.key.remoteJid;
  if (!senderJid) {
    return 'Desconhecido';
  }

  // 0. Resolução de LID (@lid): tenta converter o JID do LID para o JID do telefone (PN)
  let pnJid = null;
  if (senderJid.endsWith('@lid')) {
    try {
      if (sock && sock.signalRepository && sock.signalRepository.lidMapping) {
        pnJid = await sock.signalRepository.lidMapping.getPNForLID(senderJid);
      }
    } catch (err) {
      console.warn(`[WhatsApp LID] Falha ao consultar PN JID do LID ${senderJid}:`, err.message);
    }
  }

  // 1. Agenda Local (com fallback de JID para PN ou LID)
  let contact = contacts.get(senderJid) || (pnJid ? contacts.get(pnJid) : null);
  if (!contact) {
    // Busca no SQLite
    contact = await getContact(senderJid) || (pnJid ? await getContact(pnJid) : null);
    if (contact) {
      // Alimenta a memória cache local para futuras consultas rápidas
      contacts.set(contact.jid, {
        id: contact.jid,
        name: contact.name,
        verifiedName: contact.verifiedName,
        displayName: contact.displayName
      });
    }
  }

  if (contact) {
    const name = contact.name || contact.verifiedName || contact.displayName;
    if (name) return name;
  }

  // Proativamente salva pushName no banco de dados e memória caso seja um contato novo
  if (msg.pushName && !contacts.has(senderJid)) {
    const newContact = { id: senderJid, displayName: msg.pushName };
    contacts.set(senderJid, newContact);
    saveContact({
      jid: senderJid,
      displayName: msg.pushName
    }).catch(err => console.error('[WhatsApp DB] Falha ao auto-salvar pushName:', err.message));
  }

  // 2. Nome de Perfil (pushName)
  if (msg.pushName) {
    return msg.pushName;
  }

  // 3. Máscara Telefônica (se resolveu PN JID, usa a máscara dele; caso contrário, do LID)
  const jidToFormat = pnJid || senderJid;
  return formatPhoneNumber(jidToFormat);
}

// Trava de conexão para evitar múltiplas instâncias
let isConnecting = false;
let sock = null;

/**
 * Inicializa a conexão com o WhatsApp
 */
export async function connectToWhatsApp() {
  if (isConnecting) return;
  isConnecting = true;

  try {
    const { state, saveCreds } = await useMultiFileAuthState('auth_info_baileys');
    const { version } = await fetchLatestBaileysVersion();

    console.log(`[WhatsApp] Iniciando conexão (Baileys v${version.join('.')})...`);

    sock = makeWASocket({
      version,
      auth: state,
      logger,
      browser: ['WAND Server', 'Chrome', '121.0.0'], // Identificação robusta
      generateHighQualityLinkPreview: false, // Otimização de performance
      markOnlineOnConnect: false,
    });

    sock.ev.on('creds.update', saveCreds);

    sock.ev.on('connection.update', async (update) => {
      const { connection, lastDisconnect, qr } = update;

      if (qr) {
        console.log('[WhatsApp] QR Code gerado.');
        try {
          const qrBase64 = await QRCode.toDataURL(qr);
          broadcast({ type: 'qrcode', data: qrBase64 });
        } catch (err) {
          console.error('[WhatsApp] Erro ao gerar Base64 do QR:', err);
        }
      }

      if (connection === 'close') {
        isConnecting = false;
        const statusCode = (lastDisconnect?.error instanceof Boom)
          ? lastDisconnect.error.output.statusCode
          : 0;

        console.log(`[WhatsApp] Conexão fechada. Status: ${statusCode}`);

        updateTrayStatus(false);
        broadcast({ type: 'status', data: 'disconnected' });

        // Se não foi um logout manual, tenta reconectar
        if (statusCode !== DisconnectReason.loggedOut) {
          console.log('[WhatsApp] Tentando reconectar em 5 segundos...');
          setTimeout(() => connectToWhatsApp(), 5000);
        } else {
          console.error('[WhatsApp] Sessão encerrada (Logged Out). Clique em "Re-autenticar" na bandeja para escanear novamente.');
        }
      } else if (connection === 'open') {
        isConnecting = false;
        updateTrayStatus(true);
        console.log('[WhatsApp] WAND Server está ONLINE!');
        broadcast({ type: 'status', data: 'connected' });

        // Teste de Envio: Aguarda 10 segundos para garantir sincronização total
        console.log('[WhatsApp] Aguardando 10s para estabilização antes do teste...');
        setTimeout(async () => {
          try {
            if (isConnecting) return; // Segurança extra
            const selfJid = sock.user.id.split(':')[0] + '@s.whatsapp.net';
            await sock.sendMessage(selfJid, {
              text: 'WAND Server: Sistema Online! 🚀\n\nAguardando notificações...'
            });
            console.log('[WhatsApp] Mensagem de teste enviada com sucesso.');
          } catch (err) {
            console.error('[WhatsApp] Erro no teste de envio (pode ser ignorado se o sistema estiver operando):', err.message);
          }
        }, 10000);
      }
    });

    // Rastreador de Chats para verificar status de Mute (com sanitização para privacidade)
    sock.ev.on('messaging-history.set', async (history) => {
      if (history.contacts) {
        for (const contact of history.contacts) {
          contacts.set(contact.id, contact);
          if (contact.lid && contact.id) {
            lidToPnMap.set(contact.lid, contact.id);
            pnToLidMap.set(contact.id, contact.lid);
          }
          await saveContact({
            jid: contact.id,
            name: contact.name,
            verifiedName: contact.verifiedName,
            displayName: contact.displayName
          });
        }
      }
      if (history.chats) {
        for (const chat of history.chats) {
          const oldChat = chats.get(chat.id) || {};
          const merged = mergeChat(oldChat, chat);
          chats.set(chat.id, sanitizeChat(merged));
          
          const isMuted = isChatMuted(merged);
          if (isMuted) {
            console.log(`[WhatsApp Sync] Chat silenciado detectado no HISTÓRICO: ${chat.id}`);
          }
          await setChatMutedStatus(chat.id, isMuted);
          
          if (chat.name) {
            await saveContact({
              jid: chat.id,
              name: chat.name
            }).catch(() => {});
          }
        }
      }
    });

    sock.ev.on('chats.upsert', async (newChats) => {
      for (const chat of newChats) {
        const oldChat = chats.get(chat.id) || {};
        const merged = mergeChat(oldChat, chat);
        chats.set(chat.id, sanitizeChat(merged));
        
        const isMuted = isChatMuted(merged);
        if (isMuted) {
          console.log(`[WhatsApp Sync] Chat silenciado detectado no UPSERT: ${chat.id}`);
        }
        await setChatMutedStatus(chat.id, isMuted);
        
        if (chat.name) {
          await saveContact({
            jid: chat.id,
            name: chat.name
          }).catch(() => {});
        }
      }
    });

    sock.ev.on('chats.update', async (updates) => {
      for (const update of updates) {
        const chat = chats.get(update.id) || {};
        const merged = { ...chat, ...update };
        chats.set(update.id, sanitizeChat(merged));
        
        if (update.muteEndTime !== undefined) {
          const isMuted = isChatMuted(merged);
          console.log(`[WhatsApp Sync] ATUALIZAÇÃO DE SILÊNCIO: Chat ${update.id} teve muteEndTime atualizado para: ${update.muteEndTime}. Silenciado no DB? ${isMuted}`);
          await setChatMutedStatus(update.id, isMuted);
        }
        
        if (merged.name) {
          await saveContact({
            jid: update.id,
            name: merged.name
          }).catch(() => {});
        }
      }
    });

    sock.ev.on('contacts.upsert', async (newContacts) => {
      for (const contact of newContacts) {
        contacts.set(contact.id, contact);
        if (contact.lid && contact.id) {
          lidToPnMap.set(contact.lid, contact.id);
          pnToLidMap.set(contact.id, contact.lid);
        }
        await saveContact({
          jid: contact.id,
          name: contact.name,
          verifiedName: contact.verifiedName,
          displayName: contact.displayName
        });

        // Se o contato tiver um LID associado, salva também sob o JID do LID
        if (contact.lid) {
          await saveContact({
            jid: contact.lid,
            name: contact.name,
            verifiedName: contact.verifiedName,
            displayName: contact.displayName
          });
        }
      }
    });

    sock.ev.on('contacts.update', async (updates) => {
      for (const update of updates) {
        const contact = contacts.get(update.id) || {};
        const merged = { ...contact, ...update };
        contacts.set(update.id, merged);
        if (merged.lid && merged.id) {
          lidToPnMap.set(merged.lid, merged.id);
          pnToLidMap.set(merged.id, merged.lid);
        }
        await saveContact({
          jid: update.id,
          name: merged.name,
          verifiedName: merged.verifiedName,
          displayName: merged.displayName
        });

        // Se o contato tiver um LID associado, atualiza também sob o JID do LID
        if (merged.lid) {
          await saveContact({
            jid: merged.lid,
            name: merged.name,
            verifiedName: merged.verifiedName,
            displayName: merged.displayName
          });
        }
      }
    });

    // ... (restante do código de mensagens)

    sock.ev.on('messages.upsert', async (m) => {
      // Aceita notify (novas) e append (enviadas por mim/sync)
      if (m.type === 'notify' || m.type === 'append') {
        for (const msg of m.messages) {
          const isMe = msg.key.fromMe;

          // Ignora mensagens de sincronização técnica de dispositivos secundários (JIDs contendo ":")
          if (msg.key.remoteJid && msg.key.remoteJid.includes(':')) {
            continue;
          }

          // 0. Filtro de Chats Silenciados (MÁXIMA PRIORIDADE - Executa antes de tudo)
          if (config.filter_muted_chats) {
            const isMuted = await isChatMutedInDB(msg.key.remoteJid);
            if (isMuted) {
              console.log(`[WhatsApp] Ignorando mensagem de chat silenciado (Filtro DB): ${msg.key.remoteJid}`);
              continue;
            }
          }

          // Log para debug
          if (isMe) {
            console.log(`[WhatsApp] Mensagem própria detectada. allow_self: ${config.allow_self_messages}`);
          }

          // 1. Filtro de mensagens próprias (opcional via config)
          if (isMe && !config.allow_self_messages) continue;

          // 2. Filtro de mensagens de grupos (opcional via config)
          const isGroup = msg.key.remoteJid.endsWith('@g.us');
          if (isGroup && !config.allow_groups_messages) {
            console.log(`[WhatsApp] Ignorando mensagem de grupo: ${msg.key.remoteJid}`);
            continue;
          }

          // 3. Filtros de JID (Status, Grupos bloqueados e Canais/Newsletters)
          const BLACKLIST = [
            '120363404701403742',
            'status@broadcast',
            '@newsletter'
          ];
          if (BLACKLIST.some(id => msg.key.remoteJid.includes(id))) continue;

          // 4. Filtro de Tempo (Evita "ghost messages" do histórico de sincronização)
          const now = Math.floor(Date.now() / 1000);
          const msgTime = msg.messageTimestamp;
          if (msgTime && (now - msgTime > 60)) {
            console.log(`[WhatsApp] Ignorando mensagem antiga de sync: ${msg.key.remoteJid}`);
            continue;
          }

          let text = msg.message?.conversation ||
            msg.message?.extendedTextMessage?.text ||
            msg.message?.imageMessage?.caption ||
            msg.message?.videoMessage?.caption ||
            '';

          // Detecta figurinha (inclusive em mensagens temporárias ou view once)
          const stickerMessage = msg.message?.stickerMessage ||
            msg.message?.ephemeralMessage?.message?.stickerMessage ||
            msg.message?.viewOnceMessage?.message?.stickerMessage ||
            msg.message?.viewOnceMessageV2?.message?.stickerMessage;

          let stickerBase64 = null;
          if (stickerMessage) {
            text = '[Figurinha]';
            stickerBase64 = await processSticker(msg, sock.logger);
          }

          if (!text) continue;

          const sender = await resolveSenderName(msg);

          // Determina o JID do remetente e resolve o número de telefone (PN) em caso de @lid
          const senderJid = msg.key.participant || msg.participant || msg.key.remoteJid;
          let pnJidForNumber = null;
          if (senderJid && senderJid.endsWith('@lid')) {
            try {
              if (sock && sock.signalRepository && sock.signalRepository.lidMapping) {
                pnJidForNumber = await sock.signalRepository.lidMapping.getPNForLID(senderJid);
              }
            } catch (err) {
              // Silencioso
            }
          }
          const rawSenderNumber = pnJidForNumber || senderJid || '';
          const senderNumber = formatPhoneNumber(rawSenderNumber);

          console.log(`[WhatsApp] ${sender} (${senderNumber}): ${text} ${stickerBase64 ? '(com preview)' : ''}`);

          // Salva no Banco de Dados (Persistência)
          await saveMessage({
            remoteJid: msg.key.remoteJid,
            senderName: sender,
            text: text,
            timestamp: Date.now(),
            fromMe: isMe
          });

          const myName = getMyName();
          const contactName = await resolveSenderName({ key: { remoteJid: msg.key.remoteJid, fromMe: false } });
          
          const groupSuffix = isGroup ? ' (Grupo)' : '';

          let senderName, receiverName;
          if (isMe) {
            senderName = myName;
            receiverName = contactName + groupSuffix;
          } else {
            senderName = sender;
            if (isGroup) {
              receiverName = contactName + groupSuffix;
            } else {
              receiverName = myName;
            }
          }

          let alternateJid = null;
          if (msg.key.remoteJid.endsWith('@lid') && sock && sock.signalRepository && sock.signalRepository.lidMapping) {
            try {
              alternateJid = await sock.signalRepository.lidMapping.getPNForLID(msg.key.remoteJid);
            } catch (err) {}
          } else if (msg.key.remoteJid.endsWith('@s.whatsapp.net') && sock && sock.signalRepository && sock.signalRepository.lidMapping) {
            try {
              alternateJid = await sock.signalRepository.lidMapping.getLIDForPN(msg.key.remoteJid);
            } catch (err) {}
          }

          broadcast({
            type: 'message',
            data: {
              from: senderName,
              text: text,
              fromMe: isMe,
              sticker: stickerBase64,
              timestamp: Date.now(),
              remoteJid: msg.key.remoteJid,
              alternateJid: alternateJid,
              senderName: senderName,
              receiverName: receiverName,
              senderNumber: senderNumber
            }
          });
        }
      }
    });

  } catch (error) {
    isConnecting = false;
    console.error('[WhatsApp] Erro fatal na conexão:', error);
    setTimeout(() => connectToWhatsApp(), 10000);
  }
}

/**
 * Reseta a sessão atual, forçando um novo QR Code
 */
export async function resetSession() {
  console.log('[WhatsApp] Iniciando reset de sessão...');

  if (sock) {
    try {
      // Se a conexão já estiver fechada (como no erro 401), o logout vai falhar.
      // Tentamos o logout graciosamente, mas ignoramos erros se já estiver desconectado.
      if (sock.ws?.readyState === 1) { // 1 = OPEN
        await sock.logout().catch(() => { });
      }
      sock.end();
    } catch (e) {
      console.log('[WhatsApp] Aviso ao encerrar socket:', e.message);
    }
  }

  // Pequena pausa para garantir que o SO liberou os arquivos
  await new Promise(resolve => setTimeout(resolve, 1000));

  const authPath = path.resolve(__dirname, '../auth_info_baileys');
  if (fs.existsSync(authPath)) {
    try {
      fs.rmSync(authPath, { recursive: true, force: true });
      console.log('[WhatsApp] Pasta de autenticação removida.');
    } catch (err) {
      console.error('[WhatsApp] Erro ao remover pasta de autenticação:', err.message);
      return false;
    }
  }

  isConnecting = false;
  sock = null;
  connectToWhatsApp();
  return true;
}

/**
 * Envia uma mensagem de texto para um JID específico
 */
export async function sendMessage(remoteJid, text) {
  if (!sock) throw new Error('WhatsApp não está conectado');
  console.log(`[WhatsApp] Enviando mensagem fiel ao JID: ${remoteJid}`);
  return await sock.sendMessage(remoteJid, { text });
}

export function getSock() {
  return sock;
}

export function getContactsMemory() {
  return contacts;
}
