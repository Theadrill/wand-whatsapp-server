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

// Logger configurado para erro para evitar poluição, conforme o projeto de referência
const logger = pino({ level: 'error' });

// Trava de conexão para evitar múltiplas instâncias
let isConnecting = false;

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

    const sock = makeWASocket({
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
      if (m.type === 'notify') {
        for (const msg of m.messages) {
          // Ignora mensagens enviadas por mim mesmo e mensagens sem conteúdo
          // if (msg.key.fromMe) continue;
          if (msg.key.remoteJid === 'status@broadcast') continue;

          let text = msg.message?.conversation || 
                     msg.message?.extendedTextMessage?.text || 
                     msg.message?.imageMessage?.caption || 
                     msg.message?.videoMessage?.caption || 
                     '';

          // Se for uma figurinha, definimos um texto padrão para disparar o Toast
          if (!text && msg.message?.stickerMessage) {
            text = '[Figurinha]';
          }

          if (!text) continue;

          const sender = msg.pushName || msg.key.remoteJid.split('@')[0];
          
          console.log(`[WhatsApp] ${sender}: ${text}`);

          broadcast({
            type: 'message',
            data: {
              from: sender,
              text: text,
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
