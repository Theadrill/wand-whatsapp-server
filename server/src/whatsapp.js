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
import { saveMessage, setChatMutedStatus, isChatMutedInDB } from './database.js';
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
    });
    console.log('[WhatsApp] Contatos locais carregados.');
  }
} catch (e) {
  console.error('[WhatsApp] Erro ao ler contatos locais:', e.message);
}

// Salvar a cada 10s se houver alterações
setInterval(() => {
  try {
    const dataChats = Object.fromEntries(chats);
    fs.writeFileSync(storePath, JSON.stringify(dataChats));

    const dataContacts = Object.fromEntries(contacts);
    fs.writeFileSync(contactsPath, JSON.stringify(dataContacts));
  } catch (e) {
    console.error('[WhatsApp] Erro ao salvar stores locais:', e.message);
  }
}, 10_000);

/**
 * Formata um JID numérico em máscara elegante: +55 (XX) XXXXX-XXXX
 */
function formatPhoneNumber(jid) {
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

/**
 * Resolve o nome do remetente com base na Esteira de Resolução (Fase 3.1)
 */
function resolveSenderName(msg) {
  const isMe = msg.key.fromMe;
  if (isMe) {
    return 'Você';
  }

  const senderJid = msg.key.participant || msg.participant || msg.key.remoteJid;
  if (!senderJid) {
    return 'Desconhecido';
  }

  // 1. Agenda Local (store.contacts/contacts Map)
  const contact = contacts.get(senderJid);
  if (contact) {
    const name = contact.name || contact.verifiedName || contact.displayName;
    if (name) return name;
  }

  // 2. Nome de Perfil (pushName)
  if (msg.pushName) {
    return msg.pushName;
  }

  // 3. Máscara Telefônica
  return formatPhoneNumber(senderJid);
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
      }
    });

    sock.ev.on('contacts.upsert', (newContacts) => {
      for (const contact of newContacts) {
        contacts.set(contact.id, contact);
      }
    });

    sock.ev.on('contacts.update', (updates) => {
      for (const update of updates) {
        const contact = contacts.get(update.id) || {};
        contacts.set(update.id, { ...contact, ...update });
      }
    });

    // ... (restante do código de mensagens)

    sock.ev.on('messages.upsert', async (m) => {
      // Aceita notify (novas) e append (enviadas por mim/sync)
      if (m.type === 'notify' || m.type === 'append') {
        for (const msg of m.messages) {
          const isMe = msg.key.fromMe;

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

          const sender = resolveSenderName(msg);

          console.log(`[WhatsApp] ${sender}: ${text} ${stickerBase64 ? '(com preview)' : ''}`);

          // Salva no Banco de Dados (Persistência)
          await saveMessage({
            remoteJid: msg.key.remoteJid,
            senderName: sender,
            text: text,
            timestamp: Date.now(),
            fromMe: isMe
          });

          broadcast({
            type: 'message',
            data: {
              from: sender,
              text: text,
              sticker: stickerBase64,
              timestamp: Date.now(),
              remoteJid: msg.key.remoteJid
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
  return await sock.sendMessage(remoteJid, { text });
}
