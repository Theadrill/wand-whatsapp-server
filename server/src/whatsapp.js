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
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Carregamento de configuração
const configPath = path.resolve(__dirname, '../config.json');
let config = { allow_self_messages: false };

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

        // Se não foi um logout manual, tenta reconectar
        if (statusCode !== DisconnectReason.loggedOut) {
          updateTrayStatus(false);
          console.log('[WhatsApp] Tentando reconectar em 5 segundos...');
          setTimeout(() => connectToWhatsApp(), 5000);
        } else {
          console.error('[WhatsApp] Sessão encerrada (Logged Out). Delete a pasta auth_info_baileys e escaneie novamente.');
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

    // ... (restante do código de mensagens)

    sock.ev.on('messages.upsert', async (m) => {
      // Aceita notify (novas) e append (enviadas por mim/sync)
      if (m.type === 'notify' || m.type === 'append') {
        for (const msg of m.messages) {
          const isMe = msg.key.fromMe;
          
          // Log para debug
          if (isMe) {
            console.log(`[WhatsApp] Mensagem própria detectada. allow_self: ${config.allow_self_messages}`);
          }

          // 1. Filtro de mensagens próprias (opcional via config)
          if (isMe && !config.allow_self_messages) continue;

          // 2. Filtros de JID (Status, Grupos bloqueados e Canais/Newsletters)
          const BLACKLIST = [
            '120363404701403742',
            'status@broadcast',
            '@newsletter'
          ];
          if (BLACKLIST.some(id => msg.key.remoteJid.includes(id))) continue;

          // 3. Filtro de Tempo (Evita "ghost messages" do histórico de sincronização)
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

          const sender = msg.pushName || msg.key.remoteJid.split('@')[0];
          
          console.log(`[WhatsApp] ${sender}: ${text} ${stickerBase64 ? '(com preview)' : ''}`);

          broadcast({
            type: 'message',
            data: {
              from: sender,
              text: text,
              sticker: stickerBase64,
              timestamp: Date.now()
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
      sock.logout();
      sock.end();
    } catch (e) {
      console.log('[WhatsApp] Aviso ao fechar socket:', e.message);
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
